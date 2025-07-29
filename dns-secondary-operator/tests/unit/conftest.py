# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the dns secondary module using testing."""

import pytest
from ops import testing

from lib.charms.dns_transfer.v0.dns_transfer import DNSTransferProviderData


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


@pytest.fixture(name="primary_address")
def primary_address_fixture():
    """Primary address for dns_transfer relation."""
    return "10.10.10.11"


@pytest.fixture(name="primary_zone")
def primary_zone_fixture():
    """Primary zone for dns_transfer relation."""
    return "test.example.com"


@pytest.fixture(name="dns_transfer_relation")
def dns_transfer_relation_fixture(primary_address, primary_zone):
    """Matrix auth relation fixture."""
    data = {
        "addresses": [primary_address],
        "transport": "tls",
        "zones": [primary_zone],
    }
    provider_data = DNSTransferProviderData.model_validate(data)
    yield testing.Relation(
        endpoint="dns-transfer",
        interface="dns_transfer",
        remote_app_name="primary",
        remote_app_data=provider_data.to_relation_data(),
    )
