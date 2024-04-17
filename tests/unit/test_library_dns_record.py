# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS record library unit tests"""
import json
import secrets
import uuid
from typing import Dict, List

import ops
import pytest
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

PASSWORD_USER = secrets.token_hex()
PASSWORD_USER_2 = secrets.token_hex()
UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()
UUID4 = uuid.uuid4()


def get_requirer_relation_data(secret_id_password_user: str) -> Dict[str, str]:
    """Retrieve the requirer relation data.

    Args:
        secret_id_password_user: secret corresponding to PASSWORD_USER.

    Returns:
        a dict with the relation data.
    """
    return {
        "service_account": json.dumps(
            {
                "username": "user1",
                "password_id": secret_id_password_user,
            }
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


def get_dns_record_requirer_data(secret_id_password_user: str) -> dns_record.DNSRecordRequirerData:
    """Retrieve a DNSRecordRequirerData instance.

    Args:
        secret_id_password_user: secret corresponding to PASSWORD_USER.

    Returns:
        a DNSRecordRequirerData instance.
    """
    return dns_record.DNSRecordRequirerData(
        service_account=dns_record.ServiceAccount(
            username="user1",
            password=PASSWORD_USER,
            password_id=secret_id_password_user,
        ),
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


def get_password_secret(model: ops.Model) -> str:
    """Store secrets for the passwords and return their IDs.

    Args:
        model: the Juju model.

    Returns:
        a tuple containing the secret IDS created.
    """
    secret = model.app.add_secret(
        {"service-account-password": PASSWORD_USER}, label="service-account"
    )
    assert secret.id
    return secret.id


PROVIDER_RELATION_DATA = {
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
    secret = get_password_secret(harness.model)
    harness.charm.dns_record.update_relation_data(relation, get_dns_record_requirer_data(secret))

    assert relation
    assert relation.data[harness.model.app] == get_requirer_relation_data(secret)


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

    secret = get_password_secret(harness.model)
    harness.add_relation("dns-record", "dns-record", app_data=get_requirer_relation_data(secret))

    events = harness.charm.events
    assert len(events) == 1
    assert events[0].service_account == get_dns_record_requirer_data(secret).service_account
    assert events[0].dns_entries == get_dns_record_requirer_data(secret).dns_entries


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


def test_dns_record_requirer_get_remote_relation_data():
    """
    arrange: given a relation with requirer relation data.
    act: unserialize the relation data.
    assert: the resulting DNSRecordRequirerData is correct.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)
    harness.disable_hooks()
    secret = get_password_secret(harness.model)
    harness.add_relation("dns-record", "dns-record", app_data=get_requirer_relation_data(secret))

    result = harness.charm.dns_record.get_remote_relation_data()
    assert result == get_dns_record_requirer_data(secret)


def test_dns_record_requirer_get_remote_relation_data_throws_exception_when_secret_invalid():
    """
    arrange: given a relation with requirer relation data and an invalid secret.
    act: unserialize the relation data.
    assert: a ValueError is raised.
    """
    harness = Harness(DNSRecordProviderCharm, meta=PROVIDER_METADATA)
    harness.begin()
    harness.set_leader(True)
    harness.disable_hooks()
    secret = harness.model.app.add_secret({"invalid": PASSWORD_USER}, label="service-account")
    assert secret.id
    harness.add_relation(
        "dns-record", "dns-record", app_data=get_requirer_relation_data(secret.id)
    )

    with pytest.raises(ValueError):
        harness.charm.dns_record.get_remote_relation_data()


def test_dns_record_provider_get_remote_relation_data():
    """
    arrange: given a relation with provider relation data.
    act: unserialize the relation data.
    assert: the resulting DNSRecordProviderData is correct.
    """
    harness = Harness(DNSRecordRequirerCharm, meta=REQUIRER_METADATA)
    harness.begin()
    harness.set_leader(True)
    harness.add_relation("dns-record", "dns-record", app_data=PROVIDER_RELATION_DATA)

    result = result = harness.charm.dns_record.get_remote_relation_data()
    assert result == DNS_RECORD_PROVIDER_DATA


def test_status_unknown():
    """
    arrange: do nothing.
    act: instantiate an unrecongnised status.
    assert: the status is set as UNKNOWN.
    """
    status = dns_record.Status("anything")

    assert status == dns_record.Status.UNKNOWN
