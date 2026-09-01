# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests."""

# We need to access protected function to test them
# pylint: disable=protected-access

import ipaddress
import json
import logging
import uuid as uuid_module

import ops
import pydantic
import pytest
from ops import testing

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


def test_relation_data_success():
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

    requests = dns_record.RequirerData.model_validate(relation_data).dns_entries

    assert len(requests) == 2
    assert all(isinstance(req, dns_record.RecordRequest) for req in requests)
    assert requests[0].record is not None
    assert requests[1].record is not None
    assert requests[0].record.domain == "canonical.com"
    assert requests[1].record.domain == "juju.io"
    assert requests[1].record.record_data == "192.0.2.100"


def test_relation_data_merges_split_entries():
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

    requests = dns_record.RequirerData.model_validate(relation_data).dns_entries

    assert len(requests) == 2
    merged_request = next((r for r in requests if str(r.uuid) == uuid), None)
    assert merged_request is not None
    assert merged_request.record is not None
    assert merged_request.record.host_label == "api"
    assert merged_request.record.domain == "launchpad.net"
    assert merged_request.record.ttl == 600
    assert str(merged_request.record.record_data) == "203.0.113.1"


def test_relation_data_skips_invalid_pydantic_record():
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

    requests = dns_record.RequirerData.model_validate(relation_data).dns_entries

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


PROVIDER_METADATA = {
    "name": "dns-record-provider",
    "provides": {"dns-record": {"interface": "dns_record"}},
}
REQUIRER_METADATA = {
    "name": "dns-record-requirer",
    "requires": {"dns-record": {"interface": "dns_record"}},
}

ENTRY_UUID = "a4548e1c-5881-5654-bdc7-abd1b8d53d5d"
ENTRIES = [
    {
        "uuid": ENTRY_UUID,
        "host_label": "admin",
        "domain": "canonical.com",
        "record_type": "A",
        "record_class": "IN",
        "record_data": "204.45.64.14",
        "ttl": "3600",
    }
]
RESPONSES = [{"uuid": ENTRY_UUID, "status": "approved", "description": None}]


class DNSRecordProviderCharm(ops.CharmBase):
    """Minimal charm exercising the provider side of the library."""

    def __init__(self, *args):
        """Construct.

        Args:
            args: arguments passed to the charm.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordProvides(self)


class DNSRecordRequirerCharm(ops.CharmBase):
    """Minimal charm exercising the requirer side of the library."""

    def __init__(self, *args):
        """Construct.

        Args:
            args: arguments passed to the charm.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)


def relation(**kwargs) -> testing.Relation:
    """Build a dns-record relation.

    Args:
        kwargs: extra arguments for the relation.

    Returns:
        the relation.
    """
    return testing.Relation(endpoint="dns-record", interface="dns_record", **kwargs)


def run_provider(*relations: testing.Relation) -> testing.Manager:
    """Start a provider charm integrated with the given relations.

    Args:
        relations: the relations the provider is integrated with.

    Returns:
        the manager of the running charm.
    """
    context = testing.Context(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    state = testing.State(leader=True, relations=set(relations))
    return context(context.on.update_status(), state)


def run_requirer(*relations: testing.Relation) -> testing.Manager:
    """Start a requirer charm integrated with the given relations.

    Args:
        relations: the relations the requirer is integrated with.

    Returns:
        the manager of the running charm.
    """
    context = testing.Context(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    state = testing.State(leader=True, relations=set(relations))
    return context(context.on.update_status(), state)


def test_provider_publishes_ddns_domain():
    """
    arrange: a provider integrated with a single requirer.
    act: publish an automatically allocated domain.
    assert: the domain is published in the provider application databag, along with an
        empty dns_entries field so that requirers running a library version without ddns
        support can still parse the databag.
    """
    rel = relation(remote_app_name="requirer")

    with run_provider(rel) as manager:
        manager.charm.dns_record.update_ddns_domain("1403f42c.example.com")
        out = manager.run()

    assert out.get_relation(rel.id).local_app_data == {
        "ddns-domain": "1403f42c.example.com",
        "dns_entries": json.dumps([]),
    }


def test_provider_publishes_a_different_domain_per_relation():
    """
    arrange: a provider integrated with three requirers.
    act: publish a different allocated domain on each relation.
    assert: each requirer sees only the domain allocated to it.
    """
    relations = [relation(remote_app_name=f"requirer-{index}") for index in range(3)]

    with run_provider(*relations) as manager:
        for rel in manager.charm.dns_record.relations:
            manager.charm.dns_record.update_ddns_domain(f"label-{rel.app.name}.example.com", rel)
        out = manager.run()

    published = {}
    for rel in relations:
        out_relation = out.get_relation(rel.id)
        published[out_relation.remote_app_name] = out_relation.local_app_data["ddns-domain"]

    assert published == {
        "requirer-0": "label-requirer-0.example.com",
        "requirer-1": "label-requirer-1.example.com",
        "requirer-2": "label-requirer-2.example.com",
    }


def test_provider_clears_ddns_domain():
    """
    arrange: a provider that already published an allocated domain next to responses.
    act: publish no domain.
    assert: the field is removed from the databag and the responses are left untouched.
    """
    rel = relation(
        remote_app_name="requirer",
        local_app_data={
            "dns_entries": json.dumps(RESPONSES),
            "ddns-domain": "1403f42c.example.com",
        },
    )

    with run_provider(rel) as manager:
        manager.charm.dns_record.update_ddns_domain(None)
        out = manager.run()

    local_app_data = out.get_relation(rel.id).local_app_data
    assert "ddns-domain" not in local_app_data
    assert json.loads(local_app_data["dns_entries"]) == RESPONSES


@pytest.mark.parametrize(
    "domain",
    ("not a domain", "a" * 64 + ".example.com"),
    ids=("domain with a space", "label longer than 63 characters"),
)
def test_provider_rejects_an_invalid_ddns_domain(domain):
    """
    arrange: a provider integrated with a requirer.
    act: publish an invalid domain.
    assert: pydantic rejects it and nothing is published.

    Args:
        domain: the invalid domain to publish.
    """
    rel = relation(remote_app_name="requirer")

    with run_provider(rel) as manager:
        with pytest.raises(pydantic.ValidationError):
            manager.charm.dns_record.update_ddns_domain(domain)
        out = manager.run()

    assert out.get_relation(rel.id).local_app_data == {}


def test_requirer_reads_the_ddns_domain():
    """
    arrange: a provider that published an allocated domain next to record responses.
    act: read the domain and the entries from the requirer.
    assert: the allocated domain is returned and the responses are still readable.
    """
    rel = relation(
        remote_app_name="provider",
        remote_app_data={
            "dns_entries": json.dumps(ENTRIES),
            "ddns-domain": "1403f42c.example.com",
        },
    )

    with run_requirer(rel) as manager:
        assert manager.charm.dns_record.get_ddns_domain() == "1403f42c.example.com"
        entries = manager.charm.dns_record.get_dns_entries()
        assert entries is not None
        assert [str(entry.uuid) for entry in entries] == [ENTRY_UUID]


def test_requirer_reads_no_ddns_domain_when_absent():
    """
    arrange: a provider that didn't publish an allocated domain.
    act: read the domain from the requirer.
    assert: None is returned and the record responses are still readable.
    """
    rel = relation(
        remote_app_name="provider", remote_app_data={"dns_entries": json.dumps(ENTRIES)}
    )

    with run_requirer(rel) as manager:
        assert manager.charm.dns_record.get_ddns_domain() is None
        assert manager.charm.dns_record.get_dns_entries() != []


@pytest.mark.parametrize(
    "value",
    ("not a domain", "a" * 64 + ".example.com"),
    ids=("domain with a space", "label longer than 63 characters"),
)
def test_requirer_ignores_an_invalid_ddns_domain(value):
    """
    arrange: a provider that published an unusable ddns-domain value.
    act: read the domain from the requirer.
    assert: None is returned instead of raising.

    Args:
        value: the unusable raw value published by the provider.
    """
    rel = relation(remote_app_name="provider", remote_app_data={"ddns-domain": value})

    with run_requirer(rel) as manager:
        assert manager.charm.dns_record.get_ddns_domain() is None


def test_requirer_declares_its_addresses():
    """
    arrange: a requirer integrated with a provider.
    act: declare the addresses the allocated domain should point at.
    assert: the addresses are published in the requirer application databag.
    """
    rel = relation(remote_app_name="provider")

    with run_requirer(rel) as manager:
        manager.charm.dns_record.update_ddns_addresses(["10.0.0.1", "2001:db8::1"])
        out = manager.run()

    assert out.get_relation(rel.id).local_app_data["ddns-addresses"] == "10.0.0.1,2001:db8::1"


@pytest.mark.parametrize(
    "addresses",
    (
        ["10.0.0.2", "10.0.0.1", "2001:db8::1", "192.168.0.1"],
        ["2001:db8::1", "192.168.0.1", "10.0.0.2", "10.0.0.1"],
        [
            ipaddress.IPv4Address("192.168.0.1"),
            ipaddress.IPv6Address("2001:db8::1"),
            ipaddress.IPv4Address("10.0.0.2"),
            ipaddress.IPv4Address("10.0.0.1"),
        ],
    ),
    ids=("sorted as strings", "unsorted", "address objects"),
)
def test_requirer_publishes_sorted_addresses(addresses):
    """
    arrange: a requirer integrated with a provider.
    act: declare the same addresses in different orders and representations.
    assert: equal sets of addresses always produce the same raw databag value.

    Args:
        addresses: the addresses to declare.
    """
    rel = relation(remote_app_name="provider")

    with run_requirer(rel) as manager:
        manager.charm.dns_record.update_ddns_addresses(addresses)
        out = manager.run()

    assert (
        out.get_relation(rel.id).local_app_data["ddns-addresses"]
        == "10.0.0.1,10.0.0.2,192.168.0.1,2001:db8::1"
    )


def test_requirer_clears_its_addresses():
    """
    arrange: a requirer that already declared addresses next to record requests.
    act: declare no address.
    assert: the field is removed from the databag and the requests are left untouched.
    """
    rel = relation(
        remote_app_name="provider",
        local_app_data={
            "dns_entries": json.dumps(ENTRIES),
            "ddns-addresses": "10.0.0.1",
        },
    )

    with run_requirer(rel) as manager:
        manager.charm.dns_record.update_ddns_addresses(None)
        out = manager.run()

    local_app_data = out.get_relation(rel.id).local_app_data
    assert "ddns-addresses" not in local_app_data
    assert json.loads(local_app_data["dns_entries"]) == ENTRIES


def test_requirer_rejects_invalid_addresses():
    """
    arrange: a requirer integrated with a provider.
    act: declare an address that is not an IP address.
    assert: pydantic rejects it and nothing is published.
    """
    rel = relation(remote_app_name="provider")

    with run_requirer(rel) as manager:
        with pytest.raises(pydantic.ValidationError):
            manager.charm.dns_record.update_ddns_addresses(["10.0.0.1", "example.com"])
        out = manager.run()

    assert out.get_relation(rel.id).local_app_data == {}


def test_provider_reads_the_declared_addresses():
    """
    arrange: a requirer that declared its own addresses.
    act: read the addresses from the provider.
    assert: the declared addresses are returned.
    """
    rel = relation(
        remote_app_name="requirer",
        remote_app_data={"ddns-addresses": "10.0.0.1, 2001:db8::1"},
    )

    with run_provider(rel) as manager:
        assert manager.charm.dns_record.get_ddns_addresses() == {
            ipaddress.IPv4Address("10.0.0.1"),
            ipaddress.IPv6Address("2001:db8::1"),
        }


@pytest.mark.parametrize(
    "remote_app_data",
    (
        {"dns_entries": json.dumps(ENTRIES)},
        {"ddns-addresses": "example.com"},
        {"ddns-addresses": json.dumps(["10.0.0.1"])},
    ),
    ids=(
        "no address declared",
        "declared addresses are not IP addresses",
        "declared addresses are JSON encoded",
    ),
)
def test_provider_reads_no_address(remote_app_data):
    """
    arrange: a requirer that declared no or unusable addresses.
    act: read the addresses from the provider.
    assert: an empty set is returned instead of raising.

    Args:
        remote_app_data: the databag published by the requirer.
    """
    rel = relation(remote_app_name="requirer", remote_app_data=remote_app_data)

    with run_provider(rel) as manager:
        assert manager.charm.dns_record.get_ddns_addresses() == set()


def test_provider_handles_each_relation_independently():
    """
    arrange: a provider integrated with two requirers, only one of them requesting a record.
    act: read and answer the requests of that single relation.
    assert: the other relation is left untouched.
    """
    first = relation(
        remote_app_name="requirer-1",
        remote_app_data={
            "dns_entries": json.dumps(ENTRIES),
            "ddns-addresses": "10.0.0.1",
        },
    )
    second = relation(remote_app_name="requirer-2")

    with run_provider(first, second) as manager:
        provider = manager.charm.dns_record
        assert len(provider.relations) == 2
        rel = next(r for r in provider.relations if r.app.name == "requirer-1")
        assert provider.get_ddns_addresses(rel) == {ipaddress.IPv4Address("10.0.0.1")}
        entries = provider.get_dns_entries(rel)
        assert entries is not None
        for entry in entries:
            entry.status = dns_record.Status.APPROVED
        provider.update_dns_entries(entries, rel)
        out = manager.run()

    assert json.loads(out.get_relation(first.id).local_app_data["dns_entries"]) == RESPONSES
    assert out.get_relation(second.id).local_app_data == {}


def test_get_dns_entries_without_dns_entries_field():
    """
    arrange: a provider databag that only contains an allocated domain.
    act: read the entries from the requirer.
    assert: an empty list is returned instead of raising.
    """
    rel = relation(
        remote_app_name="provider",
        remote_app_data={"ddns-domain": "1403f42c.example.com"},
    )

    with run_requirer(rel) as manager:
        assert manager.charm.dns_record.get_dns_entries() == []


def test_undecodable_dns_entries_are_not_read_as_no_entry():
    """
    arrange: a requirer whose dns_entries field is not JSON encoded.
    act: read the entries from the provider.
    assert: None is returned rather than an empty list, so that a corrupted databag is
        not mistaken for a requirer withdrawing all of its requests.
    """
    rel = relation(remote_app_name="requirer", remote_app_data={"dns_entries": "{not json"})

    with run_provider(rel) as manager:
        assert manager.charm.dns_record.get_dns_entries() is None


def test_invalid_ddns_addresses_are_rejected():
    """
    arrange: a requirer whose ddns-addresses field holds something else than IP addresses.
    act: read the addresses and the entries from the provider.
    assert: the databag is rejected as invalid instead of being read as a requirer
        declaring no address.
    """
    rel = relation(
        remote_app_name="requirer",
        remote_app_data={"dns_entries": json.dumps(ENTRIES), "ddns-addresses": "10.0.0.1,nope"},
    )

    with run_provider(rel) as manager:
        assert manager.charm.dns_record.get_ddns_addresses() == set()
        assert manager.charm.dns_record.get_dns_entries() is None


def test_undecodable_unknown_fields_are_ignored():
    """
    arrange: a requirer that published an unknown field that is not JSON encoded.
    act: read the entries from the provider.
    assert: the unknown field is ignored and the known ones are still readable.
    """
    rel = relation(
        remote_app_name="requirer",
        remote_app_data={"dns_entries": json.dumps(ENTRIES), "unknown": "not json"},
    )

    with run_provider(rel) as manager:
        entries = manager.charm.dns_record.get_dns_entries()
        assert entries is not None
        assert [str(entry.uuid) for entry in entries] == [ENTRY_UUID]


def test_undecodable_local_data_is_discarded():
    """
    arrange: a provider whose own databag holds an undecodable dns_entries field.
    act: publish an allocated domain.
    assert: the invalid local data is discarded rather than silently kept.
    """
    rel = relation(remote_app_name="requirer", local_app_data={"dns_entries": "{not json"})

    with run_provider(rel) as manager:
        manager.charm.dns_record.update_ddns_domain("1403f42c.example.com")
        out = manager.run()

    assert out.get_relation(rel.id).local_app_data == {
        "ddns-domain": "1403f42c.example.com",
        "dns_entries": json.dumps([]),
    }


def test_deprecated_relation_data_methods_still_work():
    """
    arrange: a provider integrated with a requirer that requested a record.
    act: read and answer the request through the deprecated methods.
    assert: they behave like their replacement and emit a DeprecationWarning.
    """
    rel = relation(
        remote_app_name="requirer", remote_app_data={"dns_entries": json.dumps(ENTRIES)}
    )

    with run_provider(rel) as manager:
        provider = manager.charm.dns_record
        with pytest.deprecated_call():
            entries = provider.get_relation_data()
        assert entries is not None
        for entry in entries:
            entry.status = dns_record.Status.APPROVED
        with pytest.deprecated_call():
            provider.update_relation_data(entries)
        out = manager.run()

    assert json.loads(out.get_relation(rel.id).local_app_data["dns_entries"]) == RESPONSES
