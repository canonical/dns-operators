# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS authority library unit tests."""

# We need to access protected function to test them
# pylint: disable=protected-access

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
                        pydantic.IPvAnyAddress("192.0.2.1"),
                        pydantic.IPvAnyAddress("2001:db8::1"),
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
                        pydantic.IPvAnyAddress("192.0.2.1"),
                        pydantic.IPvAnyAddress("2001:db8::1"),
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
                    "addresses": [pydantic.IPvAnyAddress("10.0.0.1")],
                    "zones": ["example.com.", "another-site.org", "localhost"],
                },
            ),
        ],
        ids=[
            "Standard valid case with IPv4 and IPv6",
            "Uniqueness check for addresses and zones",
            "Valid zones including one with a trailing dot",
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
        "input_data, error_message_snippet",
        [
            (
                {"addresses": ["192.0.2.1"], "zones": ["a" * 64 + ".com"]},
                "Label length must be 1-63 characters",
            ),
            (
                {
                    "addresses": ["192.0.2.1"],
                    "zones": [("a." * 127) + "example"],
                },  # 2*127 + 7 = 261 octets
                "DNS zone name exceeds 255 octets",
            ),
            (
                {"addresses": ["192.0.2.1"], "zones": ["invalid_zone.com"]},
                "Invalid label in zone: invalid_zone.com, label: invalid_zone",
            ),
            (
                {"addresses": ["192.0.2.1"], "zones": ["-bad.com"]},
                "Invalid label in zone: -bad.com, label: -bad",
            ),
            (
                {"addresses": ["192.0.2.1"], "zones": ["bad-.com"]},
                "Invalid label in zone: bad-.com, label: bad-",
            ),
            (
                {"addresses": ["192.0.2.1"], "zones": ["test..com"]},
                "Invalid DNS zone name format: test..com",
            ),
            (
                {"addresses": ["999.999.999.999"], "zones": ["example.com"]},
                "Input should be a valid IPv4 or IPv6 address",
            ),
            (
                {"zones": ["example.com"]},
                "Field required",  # `addresses` can be empty, this tests missing field
            ),
            (
                {"addresses": None, "zones": ["example.com"]},
                "Field required",  # `addresses` can be empty, this tests missing field
            ),
            (
                {"addresses": ["1.2.3.4"]},
                "Field required",  # `addresses` can be empty, this tests missing field
            ),
            (
                {"zones": None, "addresses": ["1.2.3.4"]},
                "Field required",  # `addresses` can be empty, this tests missing field
            ),
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
    def test_dns_authority_relation_data_failure(self, input_data, error_message_snippet):
        """Test that DNSAuthorityRelationData initialization fails with invalid data."""
        with pytest.raises(pydantic.ValidationError):
            dns_authority.DNSAuthorityRelationData(**input_data)

    def test_serialization_and_to_relation_data(self):
        """Test the custom field serializer and the to_relation_data method."""
        addresses = ["192.0.2.1", "2001:db8::1"]
        zones = ["example.com", "test.net"]
        instance = dns_authority.DNSAuthorityRelationData(addresses=addresses, zones=zones)

        # Test the custom `to_relation_data` method
        expected_relation_data = {
            "addresses": json.dumps(addresses),
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
            "addresses": json.dumps(addresses),
            "zones": zones,
        }
        assert len(model_dump["addresses"]) == len(expected_dump["addresses"])
        assert set(model_dump["addresses"]) == set(expected_dump["addresses"])
        assert len(model_dump["zones"]) == len(expected_dump["zones"])
        assert set(model_dump["zones"]) == set(expected_dump["zones"])
