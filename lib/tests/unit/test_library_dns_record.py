# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests."""

# We need to access protected function to test them
# pylint: disable=protected-access

import logging
import uuid as uuid_module

import pydantic
import pytest

from charms.dns_record.v0 import dns_record

logger = logging.getLogger(__name__)


def test_record_serialization():
    """Test the serialization of a Record model to a dictionary."""
    record = dns_record.Record(
        domain="example.com",
        host_label="www",
        ttl=3600,
        record_class=dns_record.RecordClass.IN,
        record_type=dns_record.RecordType.AAAA,
        record_data="2001:db8::1",
    )
    serialized_data = record.model_dump()
    expected_data = {
        "domain": "example.com",
        "host_label": "www",
        "ttl": "3600",
        "record_class": "IN",
        "record_type": "AAAA",
        "record_data": "2001:db8::1",
    }
    assert serialized_data == expected_data


class TestRecordRequestModel:
    """Unit tests for the RecordRequest pydantic model."""

    @pytest.fixture
    def record_and_uuid(self):
        """Fixture to provide a Record instance and a UUID."""
        record_data = {
            "domain": "test.com",
            "host_label": "app",
            "ttl": 600,
            "record_class": dns_record.RecordClass.IN,
            "record_type": dns_record.RecordType.A,
            "record_data": "10.0.0.1",
        }
        return dns_record.Record.model_validate(record_data), uuid_module.uuid4()

    def test_record_request_validation_success(self, record_and_uuid):
        """Test successful validation of a RecordRequest."""
        record, request_uuid = record_and_uuid
        data = {
            "uuid": request_uuid,
            "status": dns_record.Status.PENDING,
            "description": "Awaiting approval",
            "record": record,
        }
        try:
            req = dns_record.RecordRequest.model_validate(data)
            assert req.uuid == request_uuid
            assert req.status == dns_record.Status.PENDING
            assert req.description == "Awaiting approval"
            assert req.record == record
        except pydantic.ValidationError as e:
            pytest.fail(f"Validation failed unexpectedly: {e}")

    def test_serialize_as_response(self, record_and_uuid):
        """Test the serialize_as_response method."""
        record, request_uuid = record_and_uuid
        request = dns_record.RecordRequest(
            uuid=request_uuid,
            status=dns_record.Status.APPROVED,
            description="Record created.",
            record=record,
        )
        response_data = request.serialize_as_response()
        expected_data = {
            "uuid": str(request_uuid),
            "status": "approved",
            "description": "Record created.",
        }
        assert response_data == expected_data

    def test_serialize_as_request(self, record_and_uuid):
        """Test the serialize_as_request method."""
        record, request_uuid = record_and_uuid
        request = dns_record.RecordRequest(
            uuid=request_uuid, status=dns_record.Status.PENDING, description="", record=record
        )
        request_data = request.serialize_as_request()
        expected_record_dump = {
            "domain": "test.com",
            "host_label": "app",
            "ttl": "600",
            "record_class": "IN",
            "record_type": "A",
            "record_data": "10.0.0.1",
        }
        expected_data = {"uuid": str(request_uuid), **expected_record_dump}
        assert request_data == expected_data

    def test_serialize_as_request_no_record(self, record_and_uuid):
        """Test serialize_as_request when the record is None."""
        _, request_uuid = record_and_uuid
        request = dns_record.RecordRequest(
            uuid=request_uuid,
            status=dns_record.Status.FAILURE,
            description="Failed to parse",
            record=None,
        )
        request_data = request.serialize_as_request()
        expected_data = {"uuid": str(request_uuid)}
        assert request_data == expected_data

    def test_uuid_serializer(self, record_and_uuid):
        """Test the custom UUID serializer."""
        _, request_uuid = record_and_uuid
        request = dns_record.RecordRequest(
            uuid=request_uuid, status=dns_record.Status.PENDING, record=None
        )
        dumped_model = request.model_dump()
        assert dumped_model["uuid"] == str(request_uuid)
        assert isinstance(dumped_model["uuid"], str)


class TestCreateRecordRequest:
    """Pytest tests for the _create_record_request staticmethod."""

    @pytest.fixture
    def namespace(self) -> uuid_module.UUID:
        """Provide a consistent UUID namespace for testing."""
        return uuid_module.UUID("12345678-1234-5678-1234-567812345678")

    @pytest.mark.parametrize(
        "input_data, expected_record",
        [
            (
                "www example.com 3600 IN A 192.0.2.1",
                {
                    "host_label": "www",
                    "domain": "example.com",
                    "ttl": 3600,
                    "record_type": dns_record.RecordType.A,
                    "record_data_str": "192.0.2.1",
                },
            ),
            (
                ["mail", "example.com", "86400", "IN", "CNAME", "web.example.com"],
                {
                    "host_label": "mail",
                    "domain": "example.com",
                    "ttl": 86400,
                    "record_type": dns_record.RecordType.CNAME,
                    "record_data_str": "web.example.com",
                },
            ),
            (
                ("ipv6", "test.net", "300", "IN", "AAAA", "2001:db8::1", "extra"),
                {
                    "host_label": "ipv6",
                    "domain": "test.net",
                    "ttl": 300,
                    "record_type": dns_record.RecordType.AAAA,
                    "record_data_str": "2001:db8::1",
                },
            ),
        ],
        ids=(
            "Standard A record from a string",
            "CNAME record from a list",
            "AAAA record from a tuple with extra data (should be ignored)",
        ),
    )
    def test_create_record_request_success(self, namespace, input_data, expected_record):
        """Test successful creation of a RecordRequest with various valid inputs."""
        request = dns_record.DNSRecordRequires._create_record_request(namespace, input_data)

        assert isinstance(request, dns_record.RecordRequest)
        assert isinstance(request.record, dns_record.Record)
        assert request.record.host_label == expected_record["host_label"]
        assert request.record.domain == expected_record["domain"]
        assert request.record.ttl == expected_record["ttl"]
        assert request.record.record_type == expected_record["record_type"]
        assert str(request.record.record_data) == expected_record["record_data_str"]

        # Verify the UUID is deterministic based on the first 6 elements
        if isinstance(input_data, str):
            uuid_src_tuple = tuple(input_data.split()[:6])
        else:
            uuid_src_tuple = tuple(input_data[:6])
        uuid_name = " ".join(uuid_src_tuple)
        expected_uuid = uuid_module.uuid5(namespace, uuid_name)
        assert request.uuid == expected_uuid

        assert request.status == dns_record.Status.UNKNOWN

    @pytest.mark.parametrize(
        "input_data, error_message_snippet",
        [
            ("www example.com 3600 IN A", "Incorrect input"),
            ("www example.com 3600 IN A not-a-valid-ip", "Incorrect input"),
            ("www example.com not-an-int IN A 192.0.2.1", "Incorrect input"),
            ("www example.com 3600 IN FAKE 192.0.2.1", "Incorrect input"),
        ],
        ids=(
            "Not enough fields",
            "Invalid IP address for an A record",
            "Invalid TTL (not an integer)",
            "Invalid record type",
        ),
    )
    def test_create_record_request_failure(self, namespace, input_data, error_message_snippet):
        """Test that _create_record_request fails correctly with invalid or insufficient data."""
        with pytest.raises(dns_record.CreateRecordRequestError) as excinfo:
            dns_record.DNSRecordRequires._create_record_request(namespace, input_data)

        assert error_message_snippet in str(excinfo.value)

    def test_create_record_request_with_custom_status_and_description(self, namespace):
        """Test creating a request with a non-default status and description."""
        data = "test example.com 60 IN TXT 'hello world'"

        request = dns_record.DNSRecordRequires._create_record_request(
            namespace,
            data,
            status=dns_record.Status.PENDING,
            description="Awaiting manual approval",
        )

        assert request.status == dns_record.Status.PENDING
        assert request.description == "Awaiting manual approval"


def test_handle_relation_data_success():
    """Test successful parsing of valid relation data."""
    relation_data = {
        "dns_entries": [
            {
                "uuid": "a4548e1c-5881-5654-bdc7-abd1b8d53d5d",
                "domain": "canonical.com",
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
            },
            {
                "uuid": "094fee39-f750-57a5-b5ac-585cc8532a92",
                "domain": "juju.io",
                "host_label": "docs",
                "ttl": "300",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "192.0.2.100",
            },
        ]
    }

    requests = dns_record.DNSRecordBase._handle_relation_data(relation_data)

    assert len(requests) == 2
    assert all(isinstance(req, dns_record.RecordRequest) for req in requests)
    assert requests[0].record is not None
    assert requests[1].record is not None
    assert requests[0].record.domain == "canonical.com"
    assert requests[1].record.domain == "juju.io"
    assert requests[1].record.record_data == "192.0.2.100"


def test_handle_relation_data_merges_split_entries():
    """Test that data for the same UUID is merged correctly before validation."""
    uuid = "f9065256-4206-5c05-91c1-2bc145d38e35"
    relation_data = {
        "dns_entries": [
            {"uuid": uuid, "host_label": "api", "domain": "launchpad.net"},
            {
                "uuid": uuid,
                "ttl": "600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "203.0.113.1",
            },
            # A second, complete record to ensure we process more than one.
            {
                "uuid": "a4548e1c-5881-5654-bdc7-abd1b8d53d5d",
                "domain": "canonical.com",
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
            },
        ]
    }

    requests = dns_record.DNSRecordBase._handle_relation_data(relation_data)

    assert len(requests) == 2
    merged_request = next((r for r in requests if str(r.uuid) == uuid), None)
    assert merged_request is not None
    assert merged_request.record is not None
    assert merged_request.record.host_label == "api"
    assert merged_request.record.domain == "launchpad.net"
    assert merged_request.record.ttl == 600
    assert str(merged_request.record.record_data) == "203.0.113.1"


def test_handle_relation_data_skips_invalid_pydantic_record():
    """Test that a record that is invalid after merging is skipped."""
    relation_data = {
        "dns_entries": [
            {
                "uuid": "a4548e1c-5881-5654-bdc7-abd1b8d53d5d",
                # domain is missing
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
                # status is also missing, this entry should be ignored completely
            },
            {
                "uuid": "9b15fb85-a9e7-4c5e-a144-7889e647f697",
                # domain is missing
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
                "status": "unknown",
                # since status is here, this will count as an entry without an associated record
            },
            {
                # valid record
                "uuid": "094fee39-f750-57a5-b5ac-585cc8532a92",
                "domain": "juju.io",
                "host_label": "docs",
                "ttl": "300",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "192.0.2.100",
                # a valid record without a status field is acceptable
            },
        ]
    }

    requests = dns_record.DNSRecordBase._handle_relation_data(relation_data)

    assert len(requests) == 2
    assert {str(r.uuid) for r in requests} == {
        "094fee39-f750-57a5-b5ac-585cc8532a92",
        "9b15fb85-a9e7-4c5e-a144-7889e647f697",
    }


@pytest.mark.parametrize(
    "data, valid",
    (
        [
            {
                "domain": "example.com",
                "host_label": "www",
                "ttl": 3600,
                "record_class": "IN",
                "record_type": "A",
                "record_data": "192.168.1.1",
            },
            True,
        ],
        [
            {
                "domain": "example.com",
                "host_label": "www",
                "ttl": 3600,
                "record_class": "IN",
                "record_type": "AAAA",
                "record_data": "2001:db8::1",
            },
            True,
        ],
        [
            {
                "domain": "example.com",
                "host_label": "mail",
                "ttl": 86400,
                "record_class": "IN",
                "record_type": "CNAME",
                "record_data": "web.example.com",
            },
            True,
        ],
        [
            {
                "domain": "example.com",
                "host_label": "www",
                "ttl": 3600,
                "record_type": "A",
                "record_data": "not-an-ip",
            },
            False,
        ],
        [
            {
                "domain": "example.com",
                "host_label": "www",
                "ttl": 3600,
                "record_type": "CNAME",
                "record_data": 12345,  # Invalid data type
            },
            False,
        ],
        [
            {
                "domain": "",
                "host_label": "www",
                "ttl": 3600,
                "record_type": "A",
                "record_data": "192.168.1.1",
            },
            False,
        ],
        [
            {
                "uuid": "a4548e1c-5881-5654-bdc7-abd1b8d53d5d",
                # domain is missing
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
            },
            False,
        ],
        [
            {
                "uuid": "a4548e1c-5881-5654-bdc7-abd1b8d53d5d",
                "domain": "foo",
                "host_label": "admin",
                "ttl": "3600",
                "record_class": "IN",
                "record_type": "A",
                "record_data": "204.45.64.14",
            },
            True,
        ],
    ),
    ids=(
        "Test successful validation of an A record with a string IP",
        "Test successful validation of an AAAA record with a pydantic IPv6Address.",
        "Test successful validation of a CNAME record.",
        "Test validation failure for an A record with an invalid IP.",
        "Test validation failure for a non-A/AAAA record with non-string data.",
        "Test validation failure for a record with an empty domain.",
        "Test validation failure with uuid and missing domain.",
        "Test successful validation with uuid.",
    ),
)
def test_validate_record(data: dict, valid: bool):
    """Validate records.

    Args:
        data: input test data
        valid: is the test data expected to be valid
    """
    if valid:
        try:
            record = dns_record.Record.model_validate(data)
            assert record.domain == data["domain"]
            assert record.host_label == data["host_label"]
            assert str(record.ttl) == str(data["ttl"])
            assert record.record_class == dns_record.RecordClass.IN
            assert record.record_type == dns_record.RecordType(data["record_type"])
            assert str(record.record_data) == data["record_data"]
        except pydantic.ValidationError as e:
            pytest.fail(f"Validation failed unexpectedly: {e}")
    else:
        with pytest.raises(pydantic.ValidationError):
            dns_record.Record.model_validate(data)
