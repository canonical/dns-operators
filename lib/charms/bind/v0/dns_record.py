# Copyright 2024 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

"""Library to manage the integration with the Bind charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.

### Requirer Charm

```python

from charms.bind.v0.dns_record import DNSRecordRequires

class DNSRecordRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = DNSRecordRequires(self)
        self.framework.observe(self.dns_record.on.dns_record_data_available, self._handler)
        ...

    def _handler(self, events: DNSRecordDataAvailableEvent) -> None:
        ...

```

As shown above, the library provides a custom event to handle the scenario in
which new DNS data has been added or updated.

### Provider Charm

Following the previous example, this is an example of the provider charm.

```python
from charms.bind.v0.dns_record import DNSRecordProvides

class DNSRecordProviderCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = DNSRecordProvides(self)
        ...

```
The DNSRecordProvides object wraps the list of relations into a `relations` property
and provides an `update_relation_data` method to update the relation data by passing
a `DNSRecordRelationData` data object.

```python
class DNSRecordProviderCharm(ops.CharmBase):
    ...

    def _on_config_changed(self, _) -> None:
        for relation in self.model.relations[self.dns_record.relation_name]:
            self.dns_record.update_relation_data(relation, self._get_dns_record_data())

```
"""

# The unique Charmhub library identifier, never change it
LIBID = "09583c2f9c1d4c0f9a40244cfc20b0c2"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import itertools
import json
import logging
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

import ops
from pydantic import BaseModel, Field, IPvAnyAddress, ValidationError

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns_record"


class Status(str, Enum):
    """Represent the status values.

    Attributes:
        APPROVED: approved
        INVALID_CREDENTIALS: invalid_credentials
        PERMISSION_DENIED: permission_denied
        CONFLICT: conflict
        INVALID_DATA: invalid_data
        FAILURE: failure
        UNKNOWN: unknown
        PENDING: pending
    """

    APPROVED = "approved"
    INVALID_CREDENTIALS = "invalid_credentials"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    INVALID_DATA = "invalid_data"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    PENDING = "pending"


class RecordType(str, Enum):
    """Represent the DNS record types.

    Attributes:
        A: A
        AAAA: AAAA
        CNAME: CNAME
        MX: MX
        DKIM: DKIM
        SPF: SPF
        DMARC: DMARC
        TXT: TXT
        CAA: CAA
        SRV: SRV
        SVCB: SVCB
        HTTPS: HTTPS
        PTR: PTR
        SOA: SOA
        NS: NS
        DS: DS
        DNSKEY: DNSKEY
    """

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    DKIM = "DKIM"
    SPF = "SPF"
    DMARC = "DMARC"
    TXT = "TXT"
    CAA = "CAA"
    SRV = "SRV"
    SVCB = "SVCB"
    HTTPS = "HTTPS"
    PTR = "PTR"
    SOA = "SOA"
    NS = "NS"
    DS = "DS"
    DNSKEY = "DNSKEY"


class RecordClass(str, Enum):
    """Represent the DNS record classes.

    Attributes:
        IN: IN
    """

    IN = "IN"


class DNSProviderData(BaseModel):
    """Represent the DNS provider data.

    Attributes:
        uuid: UUID for the domain request.
        status: status for the domain request.
        description: status description for the domain request.
    """

    uuid: UUID
    status: Status
    description: Optional[str] = None

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSProviderData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        result = {"uuid": str(self.uuid), "status": self.status.value}
        if self.description:
            result["description"] = self.description
        return result

    @classmethod
    def from_relation_data(cls, relation_data: Dict[str, str]) -> "DNSProviderData":
        """Initialize a new instance of the DNSProviderData class from the relation data.

        Args:
            relation_data: the relation data.

        Returns:
            A DNSRecordProviderData instance.
        """
        try:
            status = Status(relation_data.get("status"))
        except ValueError:
            status = Status.UNKNOWN
        return cls(
            uuid=UUID(relation_data.get("uuid")),
            status=status,
            description=relation_data.get("description"),
        )


class DNSRecordProviderData(BaseModel):
    """List of domains for the provider to manage.

    Attributes:
        dns_domains: list of domains to manage.
        dns_entries: list of entries to manage.
    """

    dns_domains: List[DNSProviderData] = Field(min_length=1)
    dns_entries: List[DNSProviderData] = Field(min_length=1)

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSRecordProviderData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        return {
            "dns-domains": json.dumps(
                [
                    domain.to_relation_data()
                    for domain in self.dns_domains  # pylint: disable=not-an-iterable
                ]
            ),
            "dns-entries": json.dumps(
                [
                    entry.to_relation_data()
                    for entry in self.dns_entries  # pylint: disable=not-an-iterable
                ]
            ),
        }

    @classmethod
    def from_relation_data(cls, relation_data: Dict[str, str]) -> "DNSRecordProviderData":
        """Initialize a new instance of the DNSRecordProviderData class from the relation data.

        Args:
            relation_data: the relation data.

        Returns:
            A DNSRecordProviderData instance.
        """
        dns_domains_data = relation_data.get("dns-domains")
        deserialised_dns_domains = json.loads(dns_domains_data) if dns_domains_data else []
        dns_domains = [
            DNSProviderData.from_relation_data(dns_domain)
            for dns_domain in deserialised_dns_domains
        ]
        dns_entries_data = relation_data.get("dns-entries")
        deserialised_dns_entries = json.loads(dns_entries_data) if dns_entries_data else []
        dns_entries = [
            DNSProviderData.from_relation_data(dns_entry) for dns_entry in deserialised_dns_entries
        ]
        return cls(dns_domains=dns_domains, dns_entries=dns_entries)


class RequirerDomain(BaseModel):
    """DNS requirer domains requested.

    Attributes:
        domain: the domain name.
        username: username for authentication.
        password_id: secret password for authentication.
        uuid: UUID for this entry.
    """

    domain: str = Field(min_length=1)
    username: str
    password_id: str
    uuid: UUID

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of RequirerDomain to the relation representation.

        Returns:
            Dict containing the representation.
        """
        return {
            "domain": self.domain,
            "username": self.username,
            "password_id": self.password_id,
            "uuid": str(self.uuid),
        }

    @classmethod
    def from_relation_data(cls, relation_data: Dict[str, str]) -> "RequirerDomain":
        """Initialize a new instance of the RequirerDomain class from the relation data.

        Args:
            relation_data: the relation data.

        Returns:
            A RequirerDomain instance.
        """
        # A validation error will be raised if the values are None
        return cls(
            domain=relation_data.get("domain"),  # type: ignore[arg-type]
            username=relation_data.get("username"),  # type: ignore[arg-type]
            password_id=relation_data.get("password_id"),  # type: ignore[arg-type]
            uuid=UUID(relation_data.get("uuid")),  # type: ignore[arg-type]
        )


class RequirerEntry(BaseModel):
    """DNS requirer entries requested.

    Attributes:
        domain: the domain name.
        host_label: host label.
        ttl: TTL.
        record_class: DNS record class.
        record_type: DNS record type.
        record_data: the record value.
        uuid: UUID for this entry.
    """

    domain: str = Field(min_length=1)
    host_label: str = Field(min_length=1)
    ttl: Optional[int] = None
    record_class: Optional[RecordClass] = None
    record_type: Optional[RecordType] = None
    record_data: IPvAnyAddress
    uuid: UUID

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSRecordRequirerData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        result = {
            "domain": self.domain,
            "host-label": self.host_label,
            "record-data": str(self.record_data),
            "uuid": str(self.uuid),
        }
        if self.ttl:
            result["ttl"] = str(self.ttl)
        if self.record_class:
            result["record-class"] = self.record_class.value
        if self.record_type:
            result["record-type"] = self.record_type.value
        return result

    @classmethod
    def from_relation_data(cls, relation_data: Dict[str, str]) -> "RequirerEntry":
        """Initialize a new instance of the RequirerEntry class from the relation data.

        Args:
            relation_data: the relation data.

        Returns:
            A RequirerEntry instance.
        """
        assert relation_data, "Empty relation data for DNS requirer, please check if relation_data has properly been passed to RequirerEntry."
        # A validation error will be raised if the values are None
        return cls(
            domain=relation_data.get("domain"),  # type: ignore[arg-type]
            host_label=relation_data.get("host-label"),  # type: ignore[arg-type]
            ttl=(
                int(relation_data.get("ttl"))  # type: ignore[arg-type]
                if "ttl" in relation_data
                else None
            ),
            record_class=(
                RecordClass(relation_data.get("record-class"))
                if "record-class" in relation_data
                else None
            ),
            record_type=(
                RecordType(relation_data.get("record-type"))
                if "record-type" in relation_data
                else None
            ),
            record_data=IPvAnyAddress(relation_data.get("record-data")),  # type: ignore[arg-type]
            uuid=UUID(relation_data.get("uuid")),  # type: ignore[arg-type]
        )


class DNSRecordRequirerData(BaseModel):
    """List of domains for the provider to manage.

    Attributes:
        dns_domains: list of domains to manage.
        dns_entries: list of entries to manage.
    """

    dns_domains: List[RequirerDomain] = Field(min_length=1)
    dns_entries: List[RequirerEntry] = Field(min_length=1)

    def to_relation_data(self) -> Dict[str, str]:
        """Convert an instance of DNSRecordRequirerData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        return {
            "dns-domains": json.dumps(
                [
                    domain.to_relation_data()
                    for domain in self.dns_domains  # pylint: disable=not-an-iterable
                ]
            ),
            "dns-entries": json.dumps(
                [
                    entry.to_relation_data()
                    for entry in self.dns_entries  # pylint: disable=not-an-iterable
                ]
            ),
        }

    @classmethod
    def from_relation_data(cls, relation_data: Dict[str, str]) -> "DNSRecordRequirerData":
        """Initialize a new instance of the DNSRecordRequirerData class from the relation data.

        Args:
            relation_data: the relation data.

        Returns:
            A DNSRecordRequirerData instance.
        """
        dns_domains_data = relation_data.get("dns-domains")
        deserialised_dns_domains = json.loads(dns_domains_data) if dns_domains_data else []
        dns_domains = [
            RequirerDomain.from_relation_data(dns_domain)
            for dns_domain in deserialised_dns_domains
        ]
        dns_entries_data = relation_data.get("dns-entries")
        deserialised_dns_entries = json.loads(dns_entries_data) if dns_entries_data else []
        dns_entries = [
            RequirerEntry.from_relation_data(dns_entry) for dns_entry in deserialised_dns_entries
        ]
        return cls(dns_domains=dns_domains, dns_entries=dns_entries)


class DNSRecordRequestProcessed(ops.RelationEvent):
    """DNS event emitted when a new request is processed.

    Attributes:
        dns_record_provider_relation_data: the DNS provider relation data.
        dns_domains: list of processed domains.
        dns_entries: list of processed entries.
    """

    @property
    def dns_record_provider_relation_data(self) -> DNSRecordProviderData:
        """Get a DNSRecordProviderData for the relation data."""
        assert self.relation.app, "DNS record relation data accessed before relation setup."
        return DNSRecordProviderData.from_relation_data(self.relation.data[self.relation.app])

    @property
    def dns_domains(self) -> Optional[List[DNSProviderData]]:
        """Fetch the DNS domains from the relation."""
        return self.dns_record_provider_relation_data.dns_domains

    @property
    def dns_entries(self) -> Optional[List[DNSProviderData]]:
        """Fetch the DNS entries from the relation."""
        return self.dns_record_provider_relation_data.dns_entries


class DNSRecordRequestReceived(ops.RelationEvent):
    """DNS event emitted when a new request is made.

    Attributes:
        dns_record_requirer_relation_data: the DNS requirer relation data.
        dns_domains: list of requested domains.
        dns_entries: list of requested entries.
    """

    @property
    def dns_record_requirer_relation_data(self) -> DNSRecordRequirerData:
        """Get a DNSRecordRequirerData for the relation data."""
        assert self.relation.app
        return DNSRecordRequirerData.from_relation_data(self.relation.data[self.relation.app])

    @property
    def dns_domains(self) -> Optional[List[RequirerDomain]]:
        """Fetch the DNS domains from the relation."""
        return self.dns_record_requirer_relation_data.dns_domains

    @property
    def dns_entries(self) -> Optional[List[RequirerEntry]]:
        """Fetch the DNS entries from the relation."""
        return self.dns_record_requirer_relation_data.dns_entries


class DNSRecordRequiresEvents(ops.CharmEvents):
    """DNS record requirer events.

    This class defines the events that a DNS record requirer can emit.

    Attributes:
        dns_record_request_processed: the DNSRecordRequestProcessed.
    """

    dns_record_request_processed = ops.EventSource(DNSRecordRequestProcessed)


class DNSRecordRequires(ops.Object):
    """Requirer side of the DNS requires relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSRecordRequiresEvents()

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def get_remote_relation_data(self) -> Optional[DNSRecordProviderData]:
        """Retrieve the remote relation data.

        Returns:
            DNSRecordProviderData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        return self._get_remote_relation_data(relation) if relation else None

    def _get_remote_relation_data(self, relation: ops.Relation) -> DNSRecordProviderData:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to retrieve the data from.

        Returns:
            DNSRecordProviderData: the relation data.
        """
        assert relation.app
        relation_data = relation.data[relation.app]
        return DNSRecordProviderData.from_relation_data(relation_data)

    def _is_remote_relation_data_valid(self, relation: ops.Relation) -> bool:
        """Validate the relation data.

        Args:
            relation: the relation to validate.

        Returns:
            true: if the relation data is valid.
        """
        try:
            _ = self._get_remote_relation_data(relation)
            return True
        except ValidationError as ex:
            error_fields = set(
                itertools.chain.from_iterable(error["loc"] for error in ex.errors())
            )
            error_field_str = " ".join(f"{f}" for f in error_fields)
            logger.warning("Error validation the relation data %s", error_field_str)
            return False

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        assert event.relation.app
        relation_data = event.relation.data[event.relation.app]
        if relation_data and self._is_remote_relation_data_valid(event.relation):
            self.on.dns_record_request_processed.emit(
                event.relation, app=event.app, unit=event.unit
            )

    def update_relation_data(
        self, relation: ops.Relation, dns_record_requirer_data: DNSRecordRequirerData
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            dns_record_requirer_data: a DNSRecordRequirerData instance wrapping the data to be
                updated.
        """
        relation_data = dns_record_requirer_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)


class DNSRecordProvidesEvents(ops.CharmEvents):
    """DNS record provider events.

    This class defines the events that a DNS record provider can emit.

    Attributes:
        dns_record_request_received: the DNSRecordRequestReceived.
    """

    dns_record_request_received = ops.EventSource(DNSRecordRequestReceived)


class DNSRecordProvides(ops.Object):
    """Provider side of the DNS record relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSRecordProvidesEvents()

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def get_remote_relation_data(self) -> Optional[DNSRecordRequirerData]:
        """Retrieve the remote relation data.

        Returns:
            DNSRecordRequirerData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        return self._get_remote_relation_data(relation) if relation else None

    def _get_remote_relation_data(self, relation: ops.Relation) -> DNSRecordRequirerData:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to retrieve the data from.

        Returns:
            DNSRecordProviderData: the relation data.
        """
        assert relation.app
        relation_data = relation.data[relation.app]
        return DNSRecordRequirerData.from_relation_data(relation_data)

    def _is_remote_relation_data_valid(self, relation: ops.Relation) -> bool:
        """Validate the relation data.

        Args:
            relation: the relation to validate.

        Returns:
            true: if the relation data is valid.
        """
        try:
            _ = self._get_remote_relation_data(relation)
            return True
        except ValidationError as ex:
            error_fields = set(
                itertools.chain.from_iterable(error["loc"] for error in ex.errors())
            )
            error_field_str = " ".join(f"{f}" for f in error_fields)
            logger.warning("Error validation the relation data %s", error_field_str)
            return False

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        assert event.relation.app
        relation_data = event.relation.data[event.relation.app]
        if relation_data and self._is_remote_relation_data_valid(event.relation):
            self.on.dns_record_request_received.emit(
                event.relation, app=event.app, unit=event.unit
            )

    def update_relation_data(
        self, relation: ops.Relation, dns_record_provider_data: DNSRecordProviderData
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            dns_record_provider_data: a DNSRecordProviderData instance wrapping the data to be
                updated.
        """
        relation_data = dns_record_provider_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)
