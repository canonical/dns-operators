# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the dns secondary module using testing."""

import pytest
from ops import testing

from lib.charms.dns_transfer.v0.dns_transfer import DNSTransferProviderData

PRIMARY_ADDRESS = "10.10.10.11"
PRIMARY_ZONE = "test.example.com"


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture():
    """State with machine and config file set."""
    relation = testing.PeerRelation(endpoint="dns-secondary-peers")
    yield {
        "config": {
            "ips": "10.10.10.10",
        },
        "leader": True,
        "relations": [relation],
    }


@pytest.fixture(name="dns_transfer_relation")
def dns_transfer_relation_fixture():
    """Matrix auth relation fixture."""
    data = {
        "addresses": [PRIMARY_ADDRESS],
        "transport": "tls",
        "zones": [PRIMARY_ZONE],
    }
    provider_data = DNSTransferProviderData.model_validate(data)
    yield testing.Relation(
        endpoint="dns-transfer",
        interface="dns_transfer",
        remote_app_name="primary",
        remote_app_data=provider_data.to_relation_data(),
    )
