# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import typing
from pathlib import Path

import core_fixtures
import jubilant
import pytest
import pytest_asyncio
import yaml


@pytest.fixture(scope="module", name="dns_resolver_directory")
def dns_resolver_directory_fixture():
    """Provide charm metadata."""
    return Path("dns-resolver-operator")


@pytest.fixture(scope="module", name="dns_resolver_metadata")
def dns_resolver_metadata_fixture(dns_resolver_directory):
    """Provide charm metadata."""
    yield yaml.safe_load(
        Path(dns_resolver_directory / "charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_resolver_name")
def fixture_dns_resolver_name(dns_resolver_metadata):
    """Provide charm name from the metadata."""
    yield dns_resolver_metadata["name"]


@pytest.fixture(scope="module", name="dns_resolver_charm_file")
def dns_resolver_charm_file_fixture(
    dns_resolver_metadata: dict[str, typing.Any],
    dns_resolver_directory: Path,
    pytestconfig: pytest.Config,
):
    """Create dns-resolver charm file.

    Args:
        dns_resolver_metadata: dns-resolver metadata
        dns_resolver_directory: path to dns-resolver's directory
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--dns-resolver-charm-file")
    if charm_file:
        yield f"./{charm_file}"
        return
    yield core_fixtures.create_charm_file(dns_resolver_metadata, dns_resolver_directory)


@pytest_asyncio.fixture(scope="module", name="dns_resolver")
async def dns_resolver_fixture(
    juju: jubilant.Juju,
    dns_resolver_charm_file: str,
    dns_resolver_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(dns_resolver_charm_file, dns_resolver_name, resources={})
    juju.wait(lambda status: jubilant.all_blocked(status, dns_resolver_name))
