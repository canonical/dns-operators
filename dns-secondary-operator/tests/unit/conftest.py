# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the dns secondary module using testing."""

import json
from datetime import timedelta

import pytest
from charms.tls_certificates_interface.v4.tls_certificates import (
    generate_ca,
    generate_certificate,
    generate_csr,
    generate_private_key,
)
from ops import testing

from lib.charms.dns_transfer.v0.dns_transfer import DNSTransferProviderData

PRIMARY_ADDRESS = "10.10.10.11"
PRIMARY_ZONE = "test.example.com"
PUBLIC_IPS = "10.10.10.10"


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture():
    """State with machine and config file set."""
    relation = testing.PeerRelation(endpoint="dns-secondary-peers")
    yield {
        "config": {
            "public-ips": PUBLIC_IPS,
            "remote-hostname": "secondary",
        },
        "leader": True,
        "relations": [relation],
    }


@pytest.fixture(name="dns_transfer_relation")
def dns_transfer_relation_fixture():
    """Matrix auth relation fixture."""
    data = {
        "addresses": [PRIMARY_ADDRESS],
        "transport": "tcp",
        "zones": [PRIMARY_ZONE],
    }
    provider_data = DNSTransferProviderData.model_validate(data)
    yield testing.Relation(
        endpoint="dns-transfer",
        interface="dns_transfer",
        remote_app_name="primary",
        remote_app_data=provider_data.to_relation_data(),
    )


@pytest.fixture(name="dns_transfer_tls_relation")
def dns_transfer_tls_relation_fixture():
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


@pytest.fixture(name="private_key")
def private_key_fixture():
    """Private key."""
    return generate_private_key()


@pytest.fixture(name="csr")
def csr_fixture(private_key):
    """CSR."""
    return generate_csr(private_key=private_key, common_name="secondary")


@pytest.fixture(name="ca")
def ca_fixture(private_key):
    """CA."""
    return generate_ca(
        private_key=private_key,
        common_name="secondary",
        validity=timedelta(hours=1),
    )


@pytest.fixture(name="certificate")
def certificate_fixture(private_key, ca, csr):
    """Certificate."""
    return generate_certificate(
        ca_private_key=private_key,
        csr=csr,
        ca=ca,
        validity=timedelta(hours=1),
    )


@pytest.fixture(name="bind_certificates_relation")
def bind_certificates_relation_fixture(csr, certificate, ca):
    """Bind certificates relation."""
    return testing.Relation(
        "bind-certificates",
        remote_app_data={
            "certificates": json.dumps(
                [
                    {
                        "ca": ca.raw,
                        "certificate_signing_request": csr.raw,
                        "certificate": certificate.raw,
                    }
                ]
            )
        },
        local_unit_data={
            "certificate_signing_requests": json.dumps(
                [{"certificate_signing_request": csr.raw, "ca": False}]
            )
        },
    )
