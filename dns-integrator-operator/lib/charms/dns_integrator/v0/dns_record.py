# Copyright 2026 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

r"""Library to manage the integration with a primary DNS charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.
It is completely backwards compatible with the legacy bind.v0.dns_record library.

### Requirer Charm

```python

from charms.dns_integrator.v0 import dns_record

class DNSRecordRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.framework.observe(self.dns_record.on.relation_joined, self._handler)
        ...

    def _handler(self, events: RelationJoinedEvent) -> None:
        self._update_relations()

    def _update_relations(self) -> None:
        if not self.model.unit.is_leader():
            return
        try:
            self.dns_record.update_relation_data(self._get_dns_record_data())
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise

    def _get_dns_record_data(self) -> list[dns_record.RecordRequest]:
        entries = []
        for request in str(self.config["requests"]).split("\n"):
            try:
                entries.append(self.dns_record.create_record_request(request))
            except dns_record.CreateRecordRequestError:
                logger.error("Invalid entry ignored: '%s'", request)
                continue
        return entries

```

As shown above, the library does not expose any custom event and the user has to rely
on the generic RelationJoined, RelationChanged events to check when DNS data has been changed.

The DNSRecordRequires provides an `update_relation_data` method to update the relation data by
passing a list of RecordRequest, requesting new DNS records.

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
a list of RecordRequest. It is expected that the provider updates the status of
those requests before updating the relation data.

```python
class DNSRecordProviderCharm(ops.CharmBase):
    ...

    def _handler(self, _: RelationChangedEvent) -> None:

        for relation in self.dns_record.relations:
            requests = self.dns_record.get_relation_data(relation)
            for request in requests:
                request.status = Status.APPROVED
            self.dns_record.update_relation_data(requests, relation)

```

Every method taking a `relation` argument accepts `None`, in which case the single
relation on the endpoint is used. A charm integrated with more than one application on
the endpoint must pass the relation explicitly, otherwise `ops.TooManyRelatedAppsError`
is raised. Use the `relations` property to iterate over them.

### Automatically allocated domains

A provider may automatically allocate a domain for each of its requirers. It publishes
the allocated domain in its application databag through the optional `ddns-domain` field:

```python
self.dns_record.set_ddns_domain("1403f42c.example.com", relation)
```

and the requirer reads it with:

```python
domain = self.dns_record.get_ddns_domain()
```

Juju's `ingress-address` is frequently a private address behind DNAT, which the provider
can't turn into a usable record. A requirer that knows the addresses its allocated domain
should point at declares them in its application databag through the optional
`ddns-addresses` field:

```python
self.dns_record.set_ddns_addresses(["10.0.0.1"])
```

and the provider reads them with:

```python
addresses = self.dns_record.get_ddns_addresses(relation)
```

Both fields are optional. A charm that knows nothing about them is unaffected.
"""

# The unique Charmhub library identifier, never change it
LIBID = "35f1741937e6405389841e4dc8c29928"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import collections
import itertools
import json
import logging
import re
import typing
import uuid as uuid_module
from enum import Enum

import ops
import pydantic

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-record"
DEFAULT_SECRET_LABEL = "dns-record"  # nosec

DNS_ENTRIES_FIELD = "dns_entries"
DDNS_DOMAIN_FIELD = "ddns-domain"
DDNS_ADDRESSES_FIELD = "ddns-addresses"

DDNS_DOMAIN_MAX_LENGTH = 253
_DDNS_LABEL_PATTERN = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


class DnsRecordError(Exception):
    """Base exception for the lib."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class CreateRecordRequestError(DnsRecordError):
    """Exception raised creating the record request fails."""


class InvalidDdnsDomainError(DnsRecordError):
    """Exception raised when an automatically allocated domain is not a valid domain name."""


class InvalidDdnsAddressesError(DnsRecordError):
    """Exception raised when the declared automatically allocated domain addresses are invalid."""


def _validate_ddns_domain(domain: str) -> str:
    """Validate an automatically allocated domain.

    Args:
        domain: the domain to validate.

    Returns:
        the validated domain.

    Raises:
        InvalidDdnsDomainError: when the domain is not a valid domain name.
    """
    if not isinstance(domain, str) or not domain or len(domain) > DDNS_DOMAIN_MAX_LENGTH:
        raise InvalidDdnsDomainError(f"Invalid domain: {domain!r}")
    labels = domain.rstrip(".").split(".")
    if not all(_DDNS_LABEL_PATTERN.match(label) for label in labels):
        raise InvalidDdnsDomainError(f"Invalid domain: {domain!r}")
    return domain


def _validate_ddns_addresses(addresses: typing.Iterable[typing.Any]) -> list[str]:
    """Validate the addresses an automatically allocated domain should point at.

    Args:
        addresses: the addresses to validate.

    Returns:
        the validated addresses, as strings.

    Raises:
        InvalidDdnsAddressesError: when one of the addresses is not a valid IP address.
    """
    if isinstance(addresses, (str, bytes)) or not isinstance(addresses, typing.Iterable):
        raise InvalidDdnsAddressesError(f"Invalid addresses: {addresses!r}")
    validated: list[str] = []
    for address in addresses:
        try:
            # mypy is confused by the fact that pydantic interfaces an external class
            validated.append(str(pydantic.networks.IPvAnyAddress(str(address))))  # type: ignore
        except ValueError as exc:
            raise InvalidDdnsAddressesError(f"Invalid IP address: {address!r}") from exc
    return validated


class Status(str, Enum):
    """Represent the status values.

    Attributes:
        APPROVED: approved
        PERMISSION_DENIED: permission_denied
        CONFLICT: conflict
        INVALID_DATA: invalid_data
        FAILURE: failure
        UNKNOWN: unknown
        PENDING: pending
    """

    APPROVED = "approved"
    PERMISSION_DENIED = "permission_denied"
    CONFLICT = "conflict"
    INVALID_DATA = "invalid_data"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    PENDING = "pending"

    @classmethod
    def _missing_(cls, _: object) -> "Status":
        """Handle the enum when the value is missing.

        Returns:
            value: Status.UNKNOWN.
        """
        return cls(cls.UNKNOWN)


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


class Record(pydantic.BaseModel):
    """DNS record.

    Attributes:
        domain: the domain name.
        host_label: host label.
        ttl: TTL.
        record_class: DNS record class.
        record_type: DNS record type.
        record_data: DNS record value (pydantic.IPvAnyAddress for A/AAAA, str otherwise).
    """

    domain: str = pydantic.Field(min_length=1)
    host_label: str = pydantic.Field(min_length=1)
    ttl: int
    record_class: RecordClass = RecordClass.IN
    record_type: RecordType
    record_data: str | pydantic.IPvAnyAddress

    @pydantic.field_serializer(
        "domain",
        "host_label",
        "ttl",
        "record_class",
        "record_type",
        "record_data",
    )
    def serialize_value(self, value: RecordClass | RecordType | str | int | None) -> str | None:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, int):
            return str(value)
        return str(value.value)

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "Record":
        """Validate the model.

        Returns:
            A validated Record model

        Raises:
            ValueError: if there is an issue in the model data
        """
        value = self.record_data
        record_type = self.record_type
        if record_type in (RecordType.A, RecordType.AAAA):
            if isinstance(value, pydantic.networks.IPvAnyAddress):
                return self
            if isinstance(value, str):
                try:
                    # mypy is confused by the fact that pydantic interfaces
                    # an external class
                    pydantic.networks.IPvAnyAddress(value)  # type: ignore
                except ValueError as e:
                    raise ValueError(
                        "record_data must be a valid IP address for record_type A or AAAA"
                    ) from e
            else:
                raise ValueError(
                    "record_data must be a string"
                    "or pydantic.IPvAnyAddress for record_type A or AAAA"
                )
        # For other record types, ensure it's a string
        if not isinstance(value, str):
            raise ValueError("record_data must be a string for non-A/AAAA record types")
        return self


class RecordRequest(pydantic.BaseModel):
    """DNS record requested.

    Attributes:
        uuid: UUID for this request.
        status: status for the domain request.
        description: status description for the domain request.
        record: the actual requested DNS record.
    """

    uuid: uuid_module.UUID
    status: Status | None = None
    description: str | None = None
    record: Record | None = None

    @pydantic.model_validator(mode="after")
    def validate_model(self) -> "RecordRequest":
        """Validate the model.

        Returns:
            A validated RecordRequest model

        Raises:
            ValueError: if there is an issue in the model data
        """
        if self.record is None:
            if self.status is None:
                raise ValueError("A record request must have a status if no record is defined")
        return self

    def serialize_as_response(self) -> dict[str, str]:
        """Serialize the RecordRequest as a response.

        Returns:
            The serialized model as a response to a request.
        """
        return self.model_dump(exclude={"record"})

    def serialize_as_request(self) -> dict[str, str]:
        """Serialize the RecordRequest as a request.

        Returns:
            The serialized model as a request.
        """
        request = self.model_dump(exclude={"status", "description", "record"})
        if self.record:
            record = self.record.model_dump()
            request.update(record)
        return request

    @pydantic.field_serializer("uuid")
    def serialize_uuid(self, value: uuid_module.UUID) -> str:
        """Serialize value.

        Args:
            value: input value

        Returns:
            serialized value
        """
        return str(value)


class DNSRecordBase(ops.Object):
    """Base class for the DNS relation.

    Attributes:
        relations: all the relations on the endpoint handled by this object.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    @property
    def relations(self) -> list[ops.Relation]:
        """Get all the relations on the endpoint handled by this object.

        Returns:
            the list of relations on the endpoint handled by this object.
        """
        return list(self.model.relations[self.relation_name])

    def _get_relation(self, relation: ops.Relation | None = None) -> ops.Relation | None:
        """Resolve the relation to operate on.

        When no relation is given, the single relation on the endpoint is used. Callers
        integrated with more than one application must pass the relation explicitly, as
        `ops.Model.get_relation` raises `ops.TooManyRelatedAppsError` in that case.

        Args:
            relation: the relation to operate on. When None, the single relation on the
                endpoint is used.

        Returns:
            the relation to operate on, or None when there is no relation.
        """
        if relation is not None:
            return relation
        return self.model.get_relation(self.relation_name)

    def _ensure_dns_entries(self, relation: ops.Relation) -> None:
        """Make sure the local application databag always carries a dns_entries field.

        Versions of this library that predate the ddns fields fail to parse a databag
        without a dns_entries field, so it has to be there as soon as anything at all is
        published on the relation.

        Args:
            relation: the relation to write the field to.
        """
        databag = relation.data[self.charm.model.app]
        if DNS_ENTRIES_FIELD not in databag:
            databag[DNS_ENTRIES_FIELD] = json.dumps([])

    def _get_remote_field(self, relation: ops.Relation, field: str) -> typing.Any:
        """Read a JSON encoded field from the remote application databag.

        Args:
            relation: the relation to read the field from.
            field: the name of the field.

        Returns:
            the decoded value, or None when the field is absent or can't be decoded.
        """
        if relation.app is None:
            return None
        raw = relation.data[relation.app].get(field)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Undecodable %s field in relation %s", field, relation.id)
            return None

    def _set_local_field(self, relation: ops.Relation, field: str, value: typing.Any) -> None:
        """Write a JSON encoded field to the local application databag.

        Args:
            relation: the relation to write the field to.
            field: the name of the field.
            value: the value to write. None removes the field from the databag.
        """
        # Juju removes a field from the databag when it is set to an empty string.
        relation.data[self.charm.model.app][field] = "" if value is None else json.dumps(value)

    @staticmethod
    def _load_relation_databag(databag: typing.Mapping[str, str]) -> dict[str, typing.Any]:
        """Decode the JSON encoded fields of a relation databag.

        Fields that are not JSON encoded are ignored, so that a charm using a newer
        version of this library can't break one using an older version.

        Args:
            databag: the relation databag.

        Returns:
            the decoded relation databag.
        """
        data: dict[str, typing.Any] = {}
        for key, value in databag.items():
            try:
                data[key] = json.loads(value)
            except json.JSONDecodeError:
                logger.warning("Ignoring undecodable relation data field %s", key)
        return data

    @staticmethod
    def _handle_relation_data(data: dict[str, typing.Any]) -> list[RecordRequest]:
        """Transform relation data into a list of RecordRequest.

        Args:
            data: relation data

        Returns:
            list of RecordRequest
        """
        # Regroup data for each entry based on the uuid
        entries: dict[str, dict[str, typing.Any]] = collections.defaultdict(dict)
        for entry in data.get(DNS_ENTRIES_FIELD) or []:
            entries[entry["uuid"]] |= entry

        # Create a record for each entry
        for entry in entries.values():
            try:
                # This works based on the fact that pydantic will ignore extra fields in the input
                entry["record"] = Record.model_validate(entry)
            except pydantic.ValidationError:
                # If we could not create a record, this is not an issue, let's just continue
                continue

        # Create a record request for each entry
        rr_entries: list[RecordRequest] = []
        for entry in entries.values():
            try:
                rr = RecordRequest.model_validate(entry)
                rr_entries.append(rr)
            except pydantic.ValidationError:
                # If we could not create a record request,
                # this is not an issue, let's just continue
                continue

        return rr_entries

    def get_relation_data(
        self, relation: ops.Relation | None = None
    ) -> list[RecordRequest] | None:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to read the data from. When None, the single relation
                on the endpoint is used.

        Returns:
            the relation data.
        """
        relation = self._get_relation(relation)
        if not relation or relation.app is None:
            return None
        relation_data: ops.RelationDataContent = relation.data[relation.app]
        return self._handle_relation_data(self._load_relation_databag(relation_data))


class DNSRecordRequires(DNSRecordBase):
    """Requirer side of the DNS requires relation."""

    def __init__(
        self,
        charm: ops.CharmBase,
        relation_name: str = DEFAULT_RELATION_NAME,
        secret_label: str = DEFAULT_SECRET_LABEL,
    ) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
            secret_label: the label used for the secret.
        """
        super().__init__(charm, relation_name)
        self.secret_label = secret_label

        try:
            self.model.get_secret(label=secret_label)
        except ops.SecretNotFoundError:
            charm.app.add_secret({"namespace": str(uuid_module.uuid4())}, label=secret_label)

    @staticmethod
    def _create_record_request(
        namespace: uuid_module.UUID,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            namespace: uuid namespace for the request
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            if isinstance(data, str):
                data = tuple(data.split())
            data = list(itertools.islice(data, 6))
            if len(data) < 6:
                raise CreateRecordRequestError(f"Incorrect input: {data}")
            host_label, domain, ttl, record_class, record_type, record_data = data
            return RecordRequest.model_validate(
                {
                    "uuid": uuid_module.uuid5(
                        namespace,
                        " ".join(
                            (host_label, domain, ttl, record_class, record_type, record_data)
                        ),
                    ),
                    "record": Record.model_validate(
                        {
                            "host_label": host_label,
                            "domain": domain,
                            "ttl": int(ttl),
                            "record_class": record_class,
                            "record_type": record_type,
                            "record_data": record_data,
                        }
                    ),
                    "status": status,
                    "description": description,
                }
            )
        except ValueError as e:
            raise CreateRecordRequestError(f"Incorrect input: {data}") from e

    def create_record_request(
        self,
        data: typing.Iterable[str] | str,
        *,
        status: str = str(Status.UNKNOWN),
        description: str = "",
    ) -> RecordRequest:
        """Create a new RecordRequest.

        Args:
            data: Iterable or string with the information
            status: Optional status
            description: Optional description

        Return:
            A newly created recordRequest

        Raise:
            CreateRecordRequestError: when failing to create the RecordRequest
        """
        try:
            secret: ops.Secret = self.model.get_secret(label=self.secret_label)
            secret_content: dict[str, str] = secret.get_content()
        except ops.SecretNotFoundError as e:
            raise CreateRecordRequestError("Namespace not found !") from e
        return self._create_record_request(
            uuid_module.UUID(secret_content["namespace"]),
            data,
            status=status,
            description=description,
        )

    def update_relation_data(
        self,
        record_requests: list[RecordRequest],
        relation: ops.Relation | None = None,
    ) -> None:
        """Update the relation data.

        Args:
            record_requests: list of RecordRequests
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        relation = self._get_relation(relation)
        if not relation:
            return
        dns_entries: list[dict[str, str]] = [rr.serialize_as_request() for rr in record_requests]
        relation_data: dict[str, str] = {DNS_ENTRIES_FIELD: json.dumps(dns_entries)}
        relation.data[self.charm.model.app].update(relation_data)

    def get_ddns_domain(self, relation: ops.Relation | None = None) -> str | None:
        """Get the domain automatically allocated by the provider, if any.

        Args:
            relation: the relation to read the domain from. When None, the single
                relation on the endpoint is used.

        Returns:
            the automatically allocated domain, or None when the provider didn't
            allocate one or published an invalid one.
        """
        relation = self._get_relation(relation)
        if not relation:
            return None
        domain = self._get_remote_field(relation, DDNS_DOMAIN_FIELD)
        if domain is None:
            return None
        try:
            return _validate_ddns_domain(domain)
        except InvalidDdnsDomainError as exc:
            logger.warning(
                "Invalid %s in relation %s: %s", DDNS_DOMAIN_FIELD, relation.id, exc.msg
            )
            return None

    def set_ddns_addresses(
        self,
        addresses: typing.Iterable[typing.Any] | None,
        relation: ops.Relation | None = None,
    ) -> None:
        """Declare the addresses the automatically allocated domain should point at.

        This overrides the `ingress-address` Juju sets in the unit databag, which is
        often a private address that isn't the one the domain should resolve to.

        Args:
            addresses: the addresses to declare. None or an empty iterable removes the
                declaration and lets the provider fall back to `ingress-address`.
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        relation = self._get_relation(relation)
        if not relation:
            return
        validated = _validate_ddns_addresses(addresses) if addresses is not None else []
        self._ensure_dns_entries(relation)
        self._set_local_field(relation, DDNS_ADDRESSES_FIELD, validated or None)


class DNSRecordProvides(DNSRecordBase):
    """Provider side of the DNS record relation."""

    def update_relation_data(
        self,
        record_requests: list[RecordRequest],
        relation: ops.Relation | None = None,
    ) -> None:
        """Update the relation data.

        Args:
            record_requests: list of RecordRequests
            relation: the relation to update. When None, the single relation on the
                endpoint is used.
        """
        relation = self._get_relation(relation)
        if not relation:
            return
        dns_entries: list[dict[str, str]] = [rr.serialize_as_response() for rr in record_requests]
        relation_data: dict[str, str] = {DNS_ENTRIES_FIELD: json.dumps(dns_entries)}
        relation.data[self.charm.model.app].update(relation_data)

    def set_ddns_domain(
        self,
        domain: str | None,
        relation: ops.Relation | None = None,
    ) -> None:
        """Publish the domain automatically allocated for the requirer of a relation.

        Args:
            domain: the allocated domain. None removes any previously published domain.
            relation: the relation to publish the domain to. When None, the single
                relation on the endpoint is used.
        """
        relation = self._get_relation(relation)
        if not relation:
            return
        validated = _validate_ddns_domain(domain) if domain is not None else None
        self._ensure_dns_entries(relation)
        self._set_local_field(relation, DDNS_DOMAIN_FIELD, validated)

    def get_ddns_addresses(self, relation: ops.Relation | None = None) -> list[str]:
        """Get the addresses the requirer declared its allocated domain should point at.

        Args:
            relation: the relation to read the addresses from. When None, the single
                relation on the endpoint is used.

        Returns:
            the declared addresses, or an empty list when the requirer declared none or
            declared invalid ones.
        """
        relation = self._get_relation(relation)
        if not relation:
            return []
        addresses = self._get_remote_field(relation, DDNS_ADDRESSES_FIELD)
        if not addresses:
            return []
        try:
            return _validate_ddns_addresses(addresses)
        except InvalidDdnsAddressesError as exc:
            logger.warning(
                "Invalid %s in relation %s: %s", DDNS_ADDRESSES_FIELD, relation.id, exc.msg
            )
            return []
