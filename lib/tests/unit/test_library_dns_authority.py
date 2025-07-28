# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS authority library unit tests."""

# We need to access protected function to test them
# pylint: disable=protected-access

import ipaddress
import json
import logging

import pydantic
import pytest

from charms.dns_authority.v0 import dns_authority

logger = logging.getLogger(__name__)


class TestDNSAuthorityRelationData:
    """Pytest tests for the DNSAuthorityRelationData Pydantic model."""

    @pytest.mark.parametrize(
        "input_data, expected_data",
        [
            (
                {
                    "addresses": ["192.0.2.1", "2001:db8::1"],
                    "zones": ["example.com", "test.net"],
                },
                {
                    "addresses": [
                        ipaddress.IPv4Address("192.0.2.1"),
                        ipaddress.IPv6Address("2001:db8::1"),
                    ],
                    "zones": ["example.com", "test.net"],
                },
            ),
            (
                {
                    "addresses": ["192.0.2.1", "192.0.2.1", "2001:db8::1"],
                    "zones": ["example.com", "test.net", "example.com"],
                },
                {
                    "addresses": [
                        ipaddress.IPv4Address("192.0.2.1"),
                        ipaddress.IPv6Address("2001:db8::1"),
                    ],
                    "zones": ["example.com", "test.net"],
                },
            ),
            (
                {
                    "addresses": ["10.0.0.1"],
                    "zones": ["example.com.", "another-site.org", "localhost"],
                },
                {
                    "addresses": [ipaddress.IPv4Address("10.0.0.1")],
                    "zones": ["example.com.", "another-site.org", "localhost"],
                },
            ),
            (
                {
                    "addresses": ["10.0.0.1"],
                    "zones": [
                        "xn--q9j988ogll.example",
                    ],
                },
                {
                    "addresses": [ipaddress.IPv4Address("10.0.0.1")],
                    "zones": [
                        "xn--q9j988ogll.example",
                    ],
                },
            ),
        ],
        ids=[
            "Standard valid case with IPv4 and IPv6",
            "Uniqueness check for addresses and zones",
            "Valid zones including one with a trailing dot",
            "Valid zones using punycode",
        ],
    )
    def test_dns_authority_relation_data_success(self, input_data, expected_data):
        """Test successful creation of DNSAuthorityRelationData with valid inputs."""
        instance = dns_authority.DNSAuthorityRelationData(**input_data)

        assert len(instance.addresses) == len(expected_data["addresses"])
        assert set(instance.addresses) == set(expected_data["addresses"])
        assert len(instance.zones) == len(expected_data["zones"])
        assert set(instance.zones) == set(expected_data["zones"])

    @pytest.mark.parametrize(
        "input_data",
        [
            {"addresses": ["192.0.2.1"], "zones": ["a" * 64 + ".com"]},
            {
                "addresses": ["192.0.2.1"],
                "zones": [("a." * 127) + "example"],
            },  # 2*127 + 7 = 261 octets
            {"addresses": ["192.0.2.1"], "zones": ["invalid_zone.com"]},
            {"addresses": ["192.0.2.1"], "zones": ["-bad.com"]},
            {"addresses": ["192.0.2.1"], "zones": ["bad-.com"]},
            {"addresses": ["192.0.2.1"], "zones": ["test..com"]},
            {"addresses": ["999.999.999.999"], "zones": ["example.com"]},
            {"zones": ["example.com"]},
            {"addresses": None, "zones": ["example.com"]},
            {"addresses": ["1.2.3.4"]},
            {"zones": None, "addresses": ["1.2.3.4"]},
        ],
        ids=[
            "Label too long",
            "Zone name too long (over 255 octets)",
            "Label with invalid character (_)",
            "Label starting with hyphen",
            "Label ending with hyphen",
            "Zone with empty label (..)",
            "Invalid IP address format",
            "Missing 'addresses' field",
            "'addresses' field set to None",
            "Missing 'zones' field",
            "'zones' field set to None",
        ],
    )
    def test_dns_authority_relation_data_failure(self, input_data):
        """Test that DNSAuthorityRelationData initialization fails with invalid data."""
        with pytest.raises(pydantic.ValidationError):
            dns_authority.DNSAuthorityRelationData(**input_data)

    def test_serialization_and_to_relation_data(self):
        """Test the custom field serializer and the to_relation_data method."""
        addresses: list[pydantic.IPvAnyAddress] = [
            ipaddress.IPv4Address("192.0.2.1"),
            ipaddress.IPv6Address("2001:db8::1"),
        ]
        zones = ["example.com", "test.net"]
        instance = dns_authority.DNSAuthorityRelationData(addresses=addresses, zones=zones)

        # Test the custom `to_relation_data` method
        expected_relation_data = {
            "addresses": json.dumps([str(a) for a in addresses]),
            "zones": json.dumps(zones),
        }
        relation_data = instance.to_relation_data()
        assert len(relation_data["addresses"]) == len(expected_relation_data["addresses"])
        assert set(relation_data["addresses"]) == set(expected_relation_data["addresses"])
        assert len(relation_data["zones"]) == len(expected_relation_data["zones"])
        assert set(relation_data["zones"]) == set(expected_relation_data["zones"])

        # Test the `@field_serializer` for 'addresses' via model_dump
        model_dump = instance.model_dump()
        expected_dump = {
            "addresses": json.dumps([str(a) for a in addresses]),
            "zones": zones,
        }
        assert len(model_dump["addresses"]) == len(expected_dump["addresses"])
        assert set(model_dump["addresses"]) == set(expected_dump["addresses"])
        assert len(model_dump["zones"]) == len(expected_dump["zones"])
        assert set(model_dump["zones"]) == set(expected_dump["zones"])
