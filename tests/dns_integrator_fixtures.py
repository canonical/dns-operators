# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import typing
from pathlib import Path

import core_fixtures
import jubilant
import pytest
import pytest_asyncio
import yaml


@pytest.fixture(scope="module", name="dns_integrator_directory")
def dns_integrator_directory_fixture():
    """Provide charm metadata."""
    return Path("dns-integrator-operator")


@pytest.fixture(scope="module", name="dns_integrator_metadata")
def dns_integrator_metadata_fixture(dns_integrator_directory):
    """Provide charm metadata."""
    yield yaml.safe_load(
        Path(dns_integrator_directory / "charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_integrator_name")
def fixture_dns_integrator_name(dns_integrator_metadata):
    """Provide charm name from the metadata."""
    yield dns_integrator_metadata["name"]


@pytest.fixture(scope="module", name="dns_integrator_charm_file")
def dns_integrator_charm_file_fixture(
    dns_integrator_metadata: dict[str, typing.Any],
    dns_integrator_directory: Path,
    pytestconfig: pytest.Config,
):
    """Create dns-integrator charm file.

    Args:
        dns_integrator_metadata: dns-integrator metadata
        dns_integrator_directory: path to dns-integrator's directory
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--dns-integrator-charm-file")
    if charm_file:
        yield f"./{charm_file}"
        return
    yield core_fixtures.create_charm_file(
        dns_integrator_metadata, dns_integrator_directory
    )


@pytest_asyncio.fixture(scope="module", name="dns_integrator")
async def dns_integrator_fixture(
    juju: jubilant.Juju,
    dns_integrator_charm_file: str,
    dns_integrator_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(dns_integrator_charm_file, dns_integrator_name, resources={})
    juju.wait(lambda status: jubilant.all_blocked(status, dns_integrator_name))
