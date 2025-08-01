# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import asyncio
import pathlib

import pytest
import pytest_asyncio
import yaml
from pytest_operator.plugin import Model, OpsTest


@pytest.fixture(scope="module", name="dns_resolver_metadata")
def dns_resolver_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../dns-resolver-operator/charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_resolver_name")
def fixture_dns_resolver_name(dns_resolver_metadata):
    """Provide charm name from the metadata."""
    yield dns_resolver_metadata["name"]


@pytest.fixture(scope="module", name="model")
def model_fixture(ops_test: OpsTest) -> Model:
    """Juju model API client."""
    assert ops_test.model
    return ops_test.model


@pytest.fixture(scope="module", name="bind_metadata")
def bind_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../bind-operator/metadata.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="bind_name")
def fixture_bind_name(bind_metadata):
    """Provide charm name from the metadata."""
    yield bind_metadata["name"]


@pytest_asyncio.fixture(scope="module", name="dns_resolver")
async def dns_resolver_fixture(
    ops_test: OpsTest,
    dns_resolver_name: str,
    pytestconfig: pytest.Config,
    model: Model,
):
    """Build the charm and deploys it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield model.applications[dns_resolver_name]
        return

    resources: dict = {}

    if charm := pytestconfig.getoption("--charm-file"):
        application = await model.deploy(
            f"./{charm}",
            application_name=dns_resolver_name,
            resources=resources,
            num_units=1,
        )
    else:
        charm = await ops_test.build_charm(".")
        application = await model.deploy(
            charm, application_name=dns_resolver_name, resources=resources
        )

    yield application


@pytest_asyncio.fixture(scope="module", name="bind")
async def bind_fixture(
    ops_test: OpsTest,
    bind_name: str,
    pytestconfig: pytest.Config,
    model: Model,
):
    """Build the charm and deploys it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield model.applications[bind_name]
        return

    resources: dict = {}

    if charm := pytestconfig.getoption("--bind-charm-file"):
        application = await model.deploy(
            f"../bind-operator/{charm}", application_name=bind_name, resources=resources
        )
    else:
        charm = await ops_test.build_charm("../bind-operator/")
        application = await model.deploy(charm, application_name=bind_name, resources=resources)

    await model.wait_for_idle(apps=[application.name], status="active")

    yield application


@pytest_asyncio.fixture(scope="module", name="full_deployment")
async def full_deployment_fixture(
    model: Model,
    bind,
    dns_resolver,
):
    """Add necessary integration for the deployed charms."""
    await asyncio.gather(
        model.add_relation(dns_resolver.name, bind.name),
    )

    await model.wait_for_idle(apps=[dns_resolver.name], status="active")

    yield {
        bind.name: bind,
        dns_resolver.name: dns_resolver,
    }
