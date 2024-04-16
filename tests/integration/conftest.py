# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

from pathlib import Path

import pytest_asyncio
import yaml
from pytest import Config, fixture
from pytest_operator.plugin import Model, OpsTest


@fixture(scope="module", name="metadata")
def fixture_metadata():
    """Provide charm metadata."""
    yield yaml.safe_load(Path("./metadata.yaml").read_text(encoding="UTF-8"))


@fixture(scope="module", name="app_name")
def fixture_app_name(metadata):
    """Provide app name from the metadata."""
    yield metadata["name"]


@fixture(scope="module", name="model")
def model_fixture(ops_test: OpsTest) -> Model:
    """Juju model API client."""
    assert ops_test.model
    return ops_test.model


@pytest_asyncio.fixture(scope="module", name="app")
async def app_fixture(
    ops_test: OpsTest,
    app_name: str,
    pytestconfig: Config,
    model: Model,
):
    """Build the charm and deploys it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield model.applications[app_name]
        return

    if charm := pytestconfig.getoption("--charm-file"):
        application = await model.deploy(f"./{charm}", application_name=app_name)
    else:
        charm = await ops_test.build_charm(".")
        application = await model.deploy(charm, application_name=app_name)

    await model.wait_for_idle(apps=[application.name], status="active")

    yield application
