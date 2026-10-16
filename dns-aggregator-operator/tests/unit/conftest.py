# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the dns-aggregator charm unit tests."""

import ops.testing
import pytest

from src.charm import DnsAggregatorCharm


@pytest.fixture(name="context")
def context_fixture():
    """Charm context fixture."""
    yield ops.testing.Context(charm_type=DnsAggregatorCharm)


@pytest.fixture(name="base_state")
def base_state_fixture():
    """Base state fixture."""
    yield {"leader": True, "relations": []}
