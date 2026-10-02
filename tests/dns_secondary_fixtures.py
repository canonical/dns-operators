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


@pytest.fixture(scope="module", name="dns_secondary_directory")
def dns_secondary_directory_fixture():
    """Provide charm metadata."""
    return Path("dns-secondary-operator")


@pytest.fixture(scope="module", name="dns_secondary_metadata")
def dns_secondary_metadata_fixture(dns_secondary_directory):
    """Provide charm metadata."""
    yield yaml.safe_load(
        Path(dns_secondary_directory / "charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_secondary_name")
def fixture_dns_secondary_name(dns_secondary_metadata):
    """Provide charm name from the metadata."""
    yield dns_secondary_metadata["name"]


@pytest.fixture(scope="module", name="dns_secondary_charm_file")
def dns_secondary_charm_file_fixture(
    dns_secondary_metadata: dict[str, typing.Any],
    dns_secondary_directory: Path,
    pytestconfig: pytest.Config,
):
    """Create dns-secondary charm file.

    Args:
        dns_secondary_metadata: dns-secondary metadata
        dns_secondary_directory: path to dns-secondary's directory
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--dns-secondary-charm-file")
    if charm_file:
        yield f"./{charm_file}"
        return
    yield core_fixtures.create_charm_file(
        dns_secondary_metadata, dns_secondary_directory
    )


@pytest_asyncio.fixture(scope="module", name="dns_secondary")
async def dns_secondary_fixture(
    juju: jubilant.Juju,
    dns_secondary_charm_file: str,
    dns_secondary_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(dns_secondary_charm_file, dns_secondary_name, resources={})
    juju.wait(lambda status: jubilant.all_blocked(status, dns_secondary_name))
