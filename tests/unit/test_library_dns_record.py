# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests"""
import json
import secrets
import uuid
from typing import List

import ops
from charms.bind.v0 import dns_record
from ops.testing import Harness
from pydantic import IPvAnyAddress

REQUIRER_METADATA = """
name: dns-record-consumer
requires:
  dns-record:
    interface: dns-record
"""

PROVIDER_METADATA = """
name: dns-record-producer
provides:
  dns-record:
    interface: dns-record
"""

PASSWORD_USER_1 = secrets.token_hex()
PASSWORD_USER_2 = secrets.token_hex()
UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()
UUID4 = uuid.uuid4()
REQUIRER_RELATION_DATA = {
    "dns_domains": json.dumps(
        [
            {
                "domain": "cloud.canonical.com",
                "username": "user1",
                "password_id": PASSWORD_USER_1,
                "uuid": str(UUID1),
            },
            {
                "domain": "ubuntu.com",
                "username": "user2",
                "password_id": PASSWORD_USER_2,
                "uuid": str(UUID2),
            },
        ]
    ),
    "dns_entries": json.dumps(
        [
            {
                "domain": "cloud.canonical.com",
                "host_label": "admin",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "A",
                "record_data": "91.189.91.48",
                "uuid": str(UUID3),
            },
            {
                "domain": "staging.ubuntu.com",
                "host_label": "www",
                "record_data": "91.189.91.47",
                "uuid": str(UUID4),
            },
        ]
    ),
}
DNS_RECORD_REQUIRER_DATA = dns_record.DNSRecordRequirerData(
    dns_domains=[
        dns_record.RequirerDomain(
            domain="cloud.canonical.com",
            username="user1",
            password_id=PASSWORD_USER_1,
            uuid=UUID1,
        ),
        dns_record.RequirerDomain(
            domain="ubuntu.com",
            username="user2",
            password_id=PASSWORD_USER_2,
            uuid=UUID2,
        ),
    ],
    dns_entries=[
        dns_record.RequirerEntry(
            uuid=UUID3,
            domain="cloud.canonical.com",
            host_label="admin",
            ttl=600,
            record_class=dns_record.RecordClass.IN,
            record_type=dns_record.RecordType.A,
            record_data=IPvAnyAddress("91.189.91.48"),
        ),
        dns_record.RequirerEntry(
            uuid=UUID4,
            domain="staging.ubuntu.com",
            host_label="www",
            record_data=IPvAnyAddress("91.189.91.47"),
        ),
    ],
)
PROVIDER_RELATION_DATA = {
    "dns_domains": json.dumps(
        [
            {
                "uuid": str(UUID1),
                "status": "invalid_credentials",
                "description": "invalid_credentials",
            },
            {
                "uuid": str(UUID2),
                "status": "approved",
            },
        ]
    ),
    "dns_entries": json.dumps(
        [
            {
                "uuid": str(UUID3),
                "status": "invalid_credentials",
                "description": "invalid_credentials",
            },
            {
                "uuid": str(UUID4),
                "status": "approved",
            },
        ]
    ),
}
DNS_RECORD_PROVIDER_DATA = dns_record.DNSRecordProviderData(
    dns_domains=[
        dns_record.DNSProviderData(
            uuid=UUID1,
            status=dns_record.Status.INVALID_CREDENTIALS,
            description="invalid_credentials",
        ),
        dns_record.DNSProviderData(
            uuid=UUID2,
            status=dns_record.Status.APPROVED,
        ),
    ],
    dns_entries=[
        dns_record.DNSProviderData(
            uuid=UUID3,
            status=dns_record.Status.INVALID_CREDENTIALS,
            description="invalid_credentials",
        ),
        dns_record.DNSProviderData(
            uuid=UUID4,
            status=dns_record.Status.APPROVED,
        ),
    ],
)


class DNSRecordRequirerCharm(ops.CharmBase):
    """Class for requirer charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.events: List[dns_record.DNSRecordRequestProcessed] = []
        self.framework.observe(self.dns_record.on.dns_record_request_processed, self._record_event)

    def _record_event(self, event: ops.EventBase) -> None:
        """Record emitted event in the event list.

        Args:
            event: event.
        """
        self.events.append(event)


class DNSRecordProviderCharm(ops.CharmBase):
    """Class for requirer charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordProvides(self)
        self.events: List[dns_record.DNSRecordRequestReceived] = []
        self.framework.observe(self.dns_record.on.dns_record_request_received, self._record_event)

    def _record_event(self, event: ops.EventBase) -> None:
        """Record emitted event in the event list.

        Args:
            event: event.
        """
        self.events.append(event)


def test_dns_record_requirer_update_relation_data():
    """
    arrange: given a requirer charm.
    act: modify the relation data.
    assert: the relation data matches the one provided.
    """
    harness = Harness(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record")
    relation = harness.model.get_relation("dns-record")
    harness.charm.dns_record.update_relation_data(relation, DNS_RECORD_REQUIRER_DATA)

    assert relation
    assert relation.data[harness.model.app] == REQUIRER_RELATION_DATA


def test_dns_record_requirer_emmits_event():
    """
    arrange: given a requirer charm.
    act: update the remote relation databag with valid values.
    assert: a DNSRecordRequestProcessed is emitted.
    """
    harness = Harness(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data=PROVIDER_RELATION_DATA)

    events = harness.charm.events
    assert len(events) == 1
    assert events[0].dns_domains == DNS_RECORD_PROVIDER_DATA.dns_domains
    assert events[0].dns_entries == DNS_RECORD_PROVIDER_DATA.dns_entries


def test_dns_record_requirer_doesnt_emmit_event_when_relation_data_invalid():
    """
    arrange: given a requirer charm.
    act: update the remote relation databag with invalid values.
    assert: no DNSRecordRequestProcessed is emitted.
    """
    harness = Harness(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data={})

    assert len(harness.charm.events) == 0


def test_dns_record_requirer_doesnt_emmit_event_when_relation_data_unparsable():
    """
    arrange: given a requirer charm.
    act: update the remote relation databag with unparsable values.
    assert: no DNSRecordRequestProcessed is emitted.
    """
    harness = Harness(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data={"invalid": "unparsable"})

    assert len(harness.charm.events) == 0


def test_dns_record_provider_update_relation_data():
    """
    arrange: given a provider charm.
    act: modify the relation data.
    assert: the relation data matches the one provided.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record")
    relation = harness.model.get_relation("dns-record")
    harness.charm.dns_record.update_relation_data(relation, DNS_RECORD_PROVIDER_DATA)

    assert relation
    assert relation.data[harness.model.app] == PROVIDER_RELATION_DATA


def test_dns_record_provider_emmits_event():
    """
    arrange: given a provider charm.
    act: update the remote relation databag with valid values.
    assert: a DNSRecordRequestReceived is emitted.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data=REQUIRER_RELATION_DATA)

    events = harness.charm.events
    assert len(events) == 1
    assert events[0].dns_domains == DNS_RECORD_REQUIRER_DATA.dns_domains
    assert events[0].dns_entries == DNS_RECORD_REQUIRER_DATA.dns_entries


def test_dns_record_provider_doesnt_emmit_event_when_relation_data_sematically_invalid():
    """
    arrange: given a provider charm.
    act: update the remote relation databag with semantically invalid values.
    assert: no DNSRecordRequestReceived is emitted.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)

    invalid_data = {
        "dns_domains": REQUIRER_RELATION_DATA["dns_domains"],
        "dns_entries": json.dumps(
            [
                {
                    "domain": "cloud.canonical.com",
                    "host_label": "admin",
                    "ttl": 600,
                    "record_class": "IN",
                    "record_type": "A",
                    "record_data": "91.189.91.48",
                    "uuid": str(UUID3),
                },
                {
                    "domain": "staging.invalid.com",
                    "host_label": "www",
                    "record_data": "91.189.91.47",
                    "uuid": str(UUID4),
                },
            ]
        ),
    }
    harness.add_relation("dns-record", "dns-record", app_data=invalid_data)

    assert len(harness.charm.events) == 0


def test_dns_record_provider_doesnt_emmit_event_when_relation_data_invalid():
    """
    arrange: given a provider charm.
    act: update the remote relation databag with invalid values.
    assert: no DNSRecordRequestReceived is emitted.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data={"invalid": "{}"})

    assert len(harness.charm.events) == 0


def test_dns_record_provider_doesnt_emmit_event_when_relation_data_unparsable():
    """
    arrange: given a provider charm.
    act: update the remote relation databag with unparsable values.
    assert: no DNSRecordRequestReceived is emitted.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)

    harness.add_relation("dns-record", "dns-record", app_data={"invalid": "unparsable"})

    assert len(harness.charm.events) == 0


def test_dns_record_requirer_data_from_relation_data():
    """
    arrange: given a relation with requirer relation data.
    act: unserialize the relation data.
    assert: the resulting DNSRecordRequirerData is correct.
    """
    result = dns_record.DNSRecordRequirerData.from_relation_data(REQUIRER_RELATION_DATA)

    assert result == DNS_RECORD_REQUIRER_DATA


def test_dns_record_provider_data_from_relation_data():
    """
    arrange: given a relation with provider relation data.
    act: unserialize the relation data.
    assert: the resulting DNSRecordProviderData is correct.
    """
    result = dns_record.DNSRecordProviderData.from_relation_data(PROVIDER_RELATION_DATA)

    assert result == DNS_RECORD_PROVIDER_DATA


def test_status_unknown():
    """
    arrange: do nothing.
    act: instantiate an unrecongnised status.
    assert: the status is set as UNKNOWN.
    """
    status = dns_record.Status("anything")

    assert status == dns_record.Status.UNKNOWN
