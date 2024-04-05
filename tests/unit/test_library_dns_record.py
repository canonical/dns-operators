# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests"""
import json
import secrets
import uuid

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
    "dns-domains": [
        {
            "uuid": str(UUID1),
            "domain": "cloud.canonical.com",
            "username": "user1",
            "password": PASSWORD_USER_1,
        },
        {
            "uuid": str(UUID2),
            "domain": "staging.ubuntu.com",
            "username": "user2",
            "password": PASSWORD_USER_2,
        },
    ],
    "dns-entries": [
        {
            "uuid": str(UUID3),
            "domain": "cloud.canonical.com",
            "host-label": "admin",
            "ttl": "600",
            "record-class": "IN",
            "record-type": "A",
            "record-data": "91.189.91.48",
        },
        {
            "uuid": str(UUID4),
            "domain": "staging.canonical.com",
            "host-label": "www",
            "record-data": "91.189.91.47",
        },
    ],
}

PROVIDER_RELATION_DATA = {
    "dns-domains": [
        {
            "uuid": str(UUID1),
            "status": "failure",
            "description": "incorrect username and password",
        },
        {
            "uuid": str(UUID2),
            "status": "approved",
        },
    ],
    "dns-entries": [
        {
            "uuid": str(UUID3),
            "status": "failure",
            "description": "incorrect username and password",
        },
        {
            "uuid": str(UUID4),
            "status": "approved",
        },
    ],
}


class DNSRecordRequirerCharm(ops.CharmBase):
    """Class for requirer charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.events = []
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
        self.events = []
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

    dns_domains = [
        dns_record.RequirerDomain(
            domain="cloud.canonical.com",
            username="user1",
            password=PASSWORD_USER_1,
            uuid=UUID1,
        ),
        dns_record.RequirerDomain(
            domain="staging.ubuntu.com",
            username="user2",
            password=PASSWORD_USER_2,
            uuid=UUID2,
        ),
    ]
    dns_entries = [
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
            domain="staging.canonical.com",
            host_label="www",
            record_data=IPvAnyAddress("91.189.91.47"),
        ),
    ]
    relation_data = dns_record.DNSRecordRequirerData(
        dns_domains=dns_domains,
        dns_entries=dns_entries,
    )
    harness.charm.dns_record.update_relation_data(relation, relation_data)

    assert relation
    data = relation.data[harness.model.app]
    assert json.loads(data["dns-domains"]) == REQUIRER_RELATION_DATA["dns-domains"]
    assert json.loads(data["dns-entries"]) == REQUIRER_RELATION_DATA["dns-entries"]


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
    dns_domains = [
        dns_record.DNSProviderData(
            uuid=UUID1,
            status=dns_record.Status.FAILURE,
            description="incorrect username and password",
        ),
        dns_record.DNSProviderData(
            uuid=UUID2,
            status=dns_record.Status.APPROVED,
        ),
    ]
    dns_entries = [
        dns_record.DNSProviderData(
            uuid=UUID3,
            status=dns_record.Status.FAILURE,
            description="incorrect username and password",
        ),
        dns_record.DNSProviderData(
            uuid=UUID4,
            status=dns_record.Status.APPROVED,
        ),
    ]
    relation_data = dns_record.DNSRecordProviderData(
        dns_domains=dns_domains,
        dns_entries=dns_entries,
    )
    harness.charm.dns_record.update_relation_data(relation, relation_data)

    assert relation
    data = relation.data[harness.model.app]
    assert json.loads(data["dns-domains"]) == PROVIDER_RELATION_DATA["dns-domains"]
    assert json.loads(data["dns-entries"]) == PROVIDER_RELATION_DATA["dns-entries"]
