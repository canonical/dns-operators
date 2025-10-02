# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest
import yaml
from pytest_operator.plugin import Model, OpsTest

# Wildcard imports are used to make all the fixtures
# available in test files
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import
from .bind_fixtures import *  # noqa: F401, F403


@pytest.fixture(scope="module", name="juju")
def juju_fixture(
    request: pytest.FixtureRequest,
) -> typing.Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps jubilant.juju.

    Args:
        request: fixture request

    Returns:
        juju
    """

    def show_debug_log(juju: jubilant.Juju):
        """Show debug log.

        Args:
            juju: Jubilant.juju
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


@pytest.fixture(scope="module", name="metadata")
def fixture_metadata():
    """Provide charm metadata."""
    yield yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))


@pytest.fixture(scope="module", name="app_name")
def fixture_app_name(metadata):
    """Provide app name from the metadata."""
    yield metadata["name"]


@pytest.fixture(scope="module", name="model")
def model_fixture(ops_test: OpsTest) -> Model:
    """Juju model API client."""
    assert ops_test.model
    return ops_test.model


@pytest.fixture(scope="module", name="charm_file")
def charm_file_fixture(metadata: dict[str, typing.Any], pytestconfig: pytest.Config):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm_file = pytestconfig.getoption("--charm-file")
    if charm_file:
        yield charm_file
        return
    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = metadata["name"]
    charm_path = pathlib.Path()
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


@pytest.fixture(scope="module", name="app")
def app_fixture(juju: jubilant.Juju, charm_file, app_name):
    """Deploy secondary charm."""
    juju.deploy(charm=charm_file, app=app_name, resources={})
    juju.wait(jubilant.all_agents_idle, timeout=600)
    juju.wait(jubilant.all_blocked)
    yield app_name  # run the test


@pytest.fixture(scope="module", name="primary")
def primary_fixture(bind, bind_name: str):  # pylint: disable=unused-argument
    """Deploy primary(bind) charm."""
    yield bind_name  # run the test
