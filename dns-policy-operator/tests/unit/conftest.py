# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import logging
from unittest.mock import Mock, patch

import ops.testing
import pytest
import scenario

from src.charm import DnsPolicyCharm

logger = logging.getLogger(__name__)


@pytest.fixture(name="context")
def context_fixture():
    """Context fixture."""
    with (
        patch("dns_policy.DnsPolicyService.start"),
        patch("dns_policy.DnsPolicyService.stop"),
        patch("dns_policy.DnsPolicyService.setup"),
        patch("dns_policy.DnsPolicyService.status") as dns_policy_status,
        patch("dns_policy.DnsPolicyService.configure"),
    ):
        dns_policy_status.return_value = True
        yield ops.testing.Context(
            charm_type=DnsPolicyCharm,
        )


@pytest.fixture
def mock_self():
    """Create a mock self object since we don't need real instance."""
    return Mock(spec=DnsPolicyCharm)


@pytest.fixture(name="base_state")
def base_state_fixture():
    """Base state fixture."""
    input_state: dict = {"leader": True}
    yield input_state


@pytest.fixture(name="database_relation")
def database_relation_fixture():
    """Database relation data fixture."""
    data = {
        "database": "somedb",
        "endpoints": "1.2.3.4:5432",
        "password": "bar",
        "username": "foo",
    }
    return scenario.Relation(
        endpoint="database",
        interface="database",
        remote_app_name="postgresql",
        remote_app_data=data,
        local_unit_data=data,
    )
