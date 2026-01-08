# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest
import pytest_asyncio
import yaml


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

    model = request.config.getoption("--model", default=None)
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = request.config.getoption("--keep-models", default=False)
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


@pytest.fixture(scope="module", name="charm_file")
def charm_file_fixture(app_name, pytestconfig: pytest.Config):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm_file = pytestconfig.getoption("--charm-file", default=None)
    if charm_file:
        yield charm_file
        return
    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


@pytest_asyncio.fixture(scope="module", name="app")
async def app_fixture(
    juju: jubilant.Juju,
    app_name: str,
    pytestconfig: pytest.Config,
    charm_file: str,
):
    """Build the charm and deploys it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield app_name
        return

    juju.deploy(charm_file, app_name, resources={})
    juju.wait(lambda status: jubilant.all_active(status, app_name))

    yield app_name
