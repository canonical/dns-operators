# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

# Wildcard imports are used to make all the fixtures
# available in test files
# pylint: disable=wildcard-import
# pylint: disable=unused-wildcard-import

from bind_fixtures import *
from core_fixtures import *
from dns_integrator_fixtures import *
from dns_policy_fixtures import *
from dns_resolver_fixtures import *
from dns_secondary_fixtures import *


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--bind-charm-file", action="store", default=None)
    parser.addoption("--dns-integrator-charm-file", action="store", default=None)
    parser.addoption("--dns-policy-charm-file", action="store", default=None)
    parser.addoption("--dns-resolver-charm-file", action="store", default=None)
    parser.addoption("--dns-secondary-charm-file", action="store", default=None)
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="This will skip deployment of the charms. Useful for local testing.",
    )


# @pytest_asyncio.fixture(scope="module", name="postgresql")
# async def postgresql_fixture(
#     ops_test: OpsTest,
#     model: Model,
# ):
#     """Deploy the postgresql charm."""
#     postgres_app = await model.deploy(
#         "postgresql",
#         channel="14/stable",
#         config={"profile": "testing"},
#     )
#     async with ops_test.fast_forward():
#         await model.wait_for_idle(apps=[postgres_app.name], status="active")
#
#     yield postgres_app
#     use_existing = pytestconfig.getoption("--use-existing", default=False)
#     if use_existing:
#         return
#
#     juju.deploy("postgresql", "postgresql", channel="14/stable", resources={})
#     juju.wait(lambda status: jubilant.all_active(status, bind_name))
