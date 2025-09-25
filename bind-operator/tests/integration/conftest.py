# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404

import pytest
import pytest_asyncio
import yaml
from pytest_operator.plugin import Model, OpsTest


@pytest.fixture(scope="module", name="charmcraft")
def fixture_charmcraft():
    """Provide charmcraft."""
    yield yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))


@pytest.fixture(scope="module", name="app_name")
def fixture_app_name(charmcraft):
    """Provide app name from the charmcraft."""
    yield charmcraft["name"]


@pytest.fixture(scope="module", name="model")
def model_fixture(ops_test: OpsTest) -> Model:
    """Juju model API client."""
    assert ops_test.model
    return ops_test.model


@pytest.fixture(scope="module", name="charm_file")
def charm_file_fixture(app_name, pytestconfig: pytest.Config):
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

    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


@pytest_asyncio.fixture(scope="module", name="app")
async def app_fixture(
    app_name: str,
    pytestconfig: pytest.Config,
    model: Model,
    charm_file: str,
):
    """Build the charm and deploys it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield model.applications[app_name]
        return

    application = await model.deploy(
        f"./{charm_file}", application_name=app_name, resources={}
    )

    await model.wait_for_idle(apps=[application.name], status="active")

    yield application
