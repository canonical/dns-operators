# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import json
import logging
from unittest.mock import patch

import ops.testing
import pytest
import scenario

from src.charm import DnsPolicyCharm

logger = logging.getLogger(__name__)
TEST_SECRET = "bar"  # nosec B105
DDNS_DOMAIN = "example.com"
DDNS_LABEL = "c3f9m2q4"


@pytest.fixture(name="api_root_token")
def api_root_token_fixture():
    """API root token fixture."""
    yield "SomeTestApiRootToken"


@pytest.fixture(name="ddns_label")
def ddns_label_fixture():
    """Automatically allocated label fixture."""
    yield DDNS_LABEL


@pytest.fixture(name="ddns_domain")
def ddns_domain_fixture():
    """Automatically allocated domain suffix fixture."""
    yield DDNS_DOMAIN


@pytest.fixture(name="context")
def context_fixture(api_root_token):
    """Context fixture."""
    with (
        patch("timer.TimerService.start"),
        patch("dns_policy.DnsPolicyService.setup"),
        patch("dns_policy.DnsPolicyService.status") as dns_policy_status,
        patch("dns_policy.DnsPolicyService.configure"),
        patch("dns_policy.DnsPolicyService.get_approved_requests") as get_approved_requests,
        patch("dns_policy.DnsPolicyService.get_api_root_token") as dns_policy_get_api_root_token,
    ):
        dns_policy_status.return_value = True
        dns_policy_get_api_root_token.return_value = api_root_token
        get_approved_requests.return_value = []
        yield ops.testing.Context(
            charm_type=DnsPolicyCharm,
        )


@pytest.fixture(name="peer_relation")
def peer_relation_fixture():
    """Peer relation fixture."""
    return scenario.PeerRelation(
        endpoint="dns-policy-peers",
        interface="dns_policy_peers",
    )


@pytest.fixture(name="base_state")
def base_state_fixture(peer_relation):
    """Base state fixture."""
    input_state: dict = {"leader": True}
    input_state["relations"] = [
        scenario.SubordinateRelation(
            endpoint="dns-record-requirer",
            interface="dns_record",
            remote_app_name="bind",
            remote_app_data={},
            local_unit_data={},
        ),
        peer_relation,
    ]
    yield input_state


@pytest.fixture(name="database_relation")
def database_relation_fixture():
    """Database relation data fixture."""
    data = {
        "database": "somedb",
        "endpoints": "1.2.3.4:5432",
        "password": TEST_SECRET,
        "username": "foo",
    }
    return scenario.Relation(
        endpoint="database",
        interface="database",
        remote_app_name="postgresql",
        remote_app_data=data,
        local_unit_data=data,
    )


@pytest.fixture(name="record_request")
def record_request_fixture():
    """Record request fixture."""
    yield {
        "domain": "canonical.com",
        "host_label": "admin",
        "ttl": "3600",
        "record_class": "IN",
        "record_type": "A",
        "record_data": "204.45.64.14",
        "uuid": "2c210a7c-55fe-52e1-a14b-2268bd8f4669",
    }


@pytest.fixture(name="ddns_record_request")
def ddns_record_request_fixture():
    """Record request conflicting with the automatically allocated domains."""
    yield {
        "domain": DDNS_DOMAIN,
        "host_label": "admin",
        "ttl": "3600",
        "record_class": "IN",
        "record_type": "A",
        "record_data": "204.45.64.15",
        "uuid": "3c210a7c-55fe-52e1-a14b-2268bd8f4669",
    }


@pytest.fixture(name="requirer_relation")
def requirer_relation_fixture(record_request):
    """Requirer relation data fixture."""
    data = {"dns_entries": json.dumps([record_request])}
    return scenario.Relation(
        endpoint="dns-record-provider",
        interface="dns_record",
        remote_app_name="dns-integrator",
        remote_app_data=data,
        local_unit_data={},
        remote_units_data={0: {"ingress-address": "10.0.0.1"}},
    )
