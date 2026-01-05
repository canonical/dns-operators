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


@pytest.fixture(scope="module", name="dns_policy_directory")
def dns_policy_directory_fixture():
    """Provide charm metadata."""
    return Path("dns-policy-operator")


@pytest.fixture(scope="module", name="dns_policy_metadata")
def dns_policy_metadata_fixture(dns_policy_directory):
    """Provide charm metadata."""
    yield yaml.safe_load(
        Path(dns_policy_directory / "charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_policy_name")
def fixture_dns_policy_name(dns_policy_metadata):
    """Provide charm name from the metadata."""
    yield dns_policy_metadata["name"]


@pytest.fixture(scope="module", name="dns_policy_charm_file")
def dns_policy_charm_file_fixture(
    dns_policy_metadata: dict[str, typing.Any],
    dns_policy_directory: Path,
    pytestconfig: pytest.Config,
):
    """Create dns-policy charm file.

    Args:
        dns_policy_metadata: dns-policy metadata
        dns_policy_directory: path to dns-policy's directory
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--dns-policy-charm-file")
    if charm_file:
        yield f"./{charm_file}"
        return
    yield core_fixtures.create_charm_file(dns_policy_metadata, dns_policy_directory)


@pytest_asyncio.fixture(scope="module", name="dns_policy")
async def dns_policy_fixture(
    juju: jubilant.Juju,
    dns_policy_charm_file: str,
    dns_policy_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(dns_policy_charm_file, dns_policy_name, resources={})
    juju.wait(lambda status: jubilant.all_active(status, dns_policy_name))
