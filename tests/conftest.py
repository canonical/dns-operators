# Copyright 2026 Canonical Ltd.
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
from postgresql_fixtures import *


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
