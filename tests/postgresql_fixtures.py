# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import jubilant
import pytest
import pytest_asyncio


@pytest.fixture(scope="module", name="postgresql_name")
def fixture_postgresql_name():
    """Provide postgresql charm name."""
    yield "postgresql"


@pytest.fixture(scope="module", name="postgresql_channel")
def fixture_postgresql_channel():
    """Provide postgresql channel."""
    yield "14/stable"


@pytest_asyncio.fixture(scope="module", name="postgresql")
async def postgresql_fixture(
    juju: jubilant.Juju,
    postgresql_name: str,
    postgresql_channel: str,
    pytestconfig: pytest.Config,
):
    """Deploy the postgresql charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy("postgresql", postgresql_name, channel=postgresql_channel, resources={})
    juju.wait(lambda status: jubilant.all_active(status, postgresql_name))
