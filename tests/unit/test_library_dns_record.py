# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests"""
import secrets
import uuid

import ops
from charms.bind.v0 import dns_record

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

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()
UUID4 = uuid.uuid4()
REQUIRER_RELATION_DATA = {
    "dns-domains": [
        {
            "uuid": UUID1,
            "domain": "cloud.canonical.com",
            "username": "user1",
            "password": secrets.token_hex(),
        },
        {
            "uuid": UUID2,
            "domain": "staging.ubuntu.com",
            "username": "user2",
            "password": secrets.token_hex(),
        },
    ],
    "dns-entries": [
        {
            "uuid": UUID3,
            "domain": "cloud.canonical.com",
            "host_label": "admin",
            "ttl": 600,
            "record_class": "IN",
            "record_type": "A",
            "record_data": "91.189.91.48",
        },
        {
            "uuid": UUID4,
            "domain": "staging.canonical.com",
            "host_label": "www",
            "record_data": "91.189.91.47",
        },
    ],
}

PROVIDER_RELATION_DATA = {
    "dns-domains": [
        {
            "uuid": UUID1,
            "status": "failure",
            "status_description": "incorrect username and password",
        },
        {
            "uuid": UUID2,
            "status": "approved",
        },
    ],
    "dns-entries": [
        {
            "uuid": UUID3,
            "status": "failure",
            "status_description": "incorrect username & password",
        },
        {
            "uuid": UUID4,
            "host_label": "www",
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
