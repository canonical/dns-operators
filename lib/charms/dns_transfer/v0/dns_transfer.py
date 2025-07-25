# Copyright 2025 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.
# pylint: disable=R0801
"""Library to manage the integration between primary and secondary DNS charms.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.

### Requirer Charm

The DNSTransferRequires provides:

* an `get_remote_relation_data" method to get data from the provider.
* an `update_relation_data` method to update the relation data by
passing a list of IP addresses to the provider.

```python

from charms.dns_transfer.v0.dns_transfer import DNSTransferRequires, DNSTransferRequirerData

class DNSTransferRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_transfer = DNSTransferRequires(self)
        # line-too-long
        self.framework.observe(charm.on["dns-transfer"].relation_changed, self._on_relation_changed) # noqa: W505 pylint: disable=C0301
        ...

    def _on_relation_changed(self, event: ops.Event) -> None:
        dns_primary_data = self.dns_transfer.get_remote_relation_data()
        addresses = dns_primary_data.addresses

    def _on_config_changed(self, event: ops.Event) -> None:
        addresses = self.my_ips()
        relation = self.model.get_relation(self.dns_transfer.relation_name)
        requirer_data = DNSTransferRequirerData(addresses=addresses)
        self.dns_transfer.update_relation_data(relation, requirer_data)

```

### Provider Charm

Following the previous example, this is an example of the provider charm.

```python
from charms.dns_transfer.v0.dns_transfer import DNSTransferProvides, DNSTransferProviderData

class DNSTransferProviderCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_transfer = DNSTransferProvides(self)
        self.framework.observe(charm.on["dns-transfer"].relation_changed, self._on_relation_changed)
        ...

    def _on_relation_changed(self, event: ops.Event) -> None:
        addresses = []
        for relation in self.model.relations[self.dns_transfer.relation_name]:
            dns_secondary_data = self.dns_transfer.get_remote_relation_data(relation)
            addresses.extend(dns_secondary_data.addresses)

    def _on_config_changed(self, event: ops.Event) -> None:
        data = {
            "addresses": self.addresses(),
            "transport": self.transport(),
            "zones": self.zones(),
        }
        provider_data = DNSTransferProviderData.model_validate(data)
        for relation in self.model.relations[self.dns_transfer.relation_name]:
            self.dns_transfer.update_relation_data(relation, provider_data)

```
"""

# The unique Charmhub library identifier, never change it
LIBID = "908bcd1f0ad14cabbc9dca25fa0fc87c"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 5

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import json
import logging
import re
from enum import Enum
from typing import Any, Optional, cast

import ops
import pydantic

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-transfer"


def validate_zone_or_hostname(zone: str) -> None:
    """Validate zone or hostname.

    Args:
        zone: zone or hostname string.

    Raises:
        ValueError: if zone or hostname is invalid.
    """
    # Our main references are RFC 1034 and 2181
    #    RFC 1034: https://datatracker.ietf.org/doc/html/rfc1034#section-3.1
    #    RFC 2181: https://datatracker.ietf.org/doc/html/rfc2181#section-11
    label_pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$"
    # RFC1034: "To simplify implementations,
    # the total number of octets that represent a domain name is limited to 255"
    if len(zone.encode("ascii")) > 255:
        raise ValueError(f"DNS zone name exceeds 255 octets: {zone}")

    # Split zone into labels
    labels = zone.strip(".").split(".")
    if not labels or ".." in zone:
        raise ValueError(f"Invalid DNS zone name format: {zone}")

    # Validate each label
    for label in labels:
        # RFC1034: "Each node has a label, which is zero to 63 octets in length"
        if len(label) < 1 or len(label) > 63:
            raise ValueError(
                f"Label length must be 1-63 characters in zone: {zone}, label: {label}"
            )
        # Check label content with regex
        if not re.match(label_pattern, label, re.IGNORECASE):
            raise ValueError(f"Invalid label in zone: {zone}, label: {label}")


class TransportSecurity(str, Enum):
    """Represent the transport security values.

    Attributes:
        TCP: tcp
        TLS: tls
    """

    TCP = "tcp"
    TLS = "tls"


class DNSTransferProviderData(pydantic.BaseModel):
    """List of information for the provider to manage and transfer.

    Attributes:
        addresses: IP list of the units composing the provider's deployment.
        transport: Type of transport (tls or tcp).
        remote_hostname: Advertised name of the host in the TLS certificate (optional).
        zones: List of zone names.
    """

    addresses: list[pydantic.IPvAnyAddress]
    transport: TransportSecurity
    remote_hostname: Optional[str] = None
    zones: list[str]

    # pydantic wants 'self' as first argument
    @pydantic.field_validator("addresses", mode="before")
    def deduplicate_addresses(cls, v: Any) -> list:  # noqa: N805 pylint: disable=E0213
        """Deduplicate addresses.

        Args:
            v: value

        Returns:
            list with unique values.
        """
        return list(set(v))

    # pydantic wants 'self' as first argument
    @pydantic.field_validator("zones", mode="before")
    def deduplicate_zones(cls, v: Any) -> list:  # noqa: N805 pylint: disable=E0213
        """Deduplicate zones.

        Args:
            v: value

        Returns:
            list with unique values.
        """
        return list(set(v))

    # pydantic wants 'self' as first argument
    @pydantic.field_validator("remote_hostname")
    def validate_hostname(cls, v: Any) -> Any:  # noqa: N805 pylint: disable=E0213
        """Validate hostname against RFC 952.

        Args:
            v: The input value provided for the `remote_hostname` field.

        Returns:
            A validated hostname.
        """
        if v is None:
            return v
        validate_zone_or_hostname(v)
        return v

    @pydantic.field_validator("zones")
    @classmethod
    def validate_zones(cls, zones: list[str]) -> list[str]:
        """Validate the input zones.

        Args:
            zones: list of DNS zone names.

        Returns:
            A list of DNS zone names.
        """
        for zone in zones:
            validate_zone_or_hostname(zone)

        return zones

    def to_relation_data(self) -> dict[str, str]:
        """Convert an instance of DNSTransferProviderData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        dumped_model = self.model_dump(exclude_unset=True)
        dumped_data = {}
        for key, value in dumped_model.items():
            dumped_data[key] = json.dumps(value, default=str)
        return dumped_data

    @classmethod
    def from_relation_data(cls, relation: ops.Relation) -> "DNSTransferProviderData":
        """Initialize a new instance of the DNSTransferProviderData class from the relation.

        Args:
            relation: the relation.

        Returns:
            A DNSTransferProviderData instance.

        Raises:
            ValueError: if the value is not parseable.
        """
        try:
            loaded_data = {}
            app = cast(ops.Application, relation.app)
            relation_data = relation.data[app]
            for key, value in relation_data.items():
                loaded_data[key] = json.loads(value)
            return DNSTransferProviderData.model_validate(loaded_data)
        except json.JSONDecodeError as ex:
            raise ValueError from ex


class DNSTransferRequirerData(pydantic.BaseModel):
    """List of information for the requirer to manage and transfer.

    Attributes:
        addresses: IP list of the units composing the provider's deployment.
    """

    addresses: list[pydantic.IPvAnyAddress]

    # pydantic wants 'self' as first argument
    @pydantic.field_validator("addresses", mode="before")
    def deduplicate_addresses(cls, v: Any) -> list:  # noqa: N805 pylint: disable=E0213
        """Deduplicate addresses.

        Args:
            v: value

        Returns:
            list with unique values.
        """
        return list(set(v))

    def to_relation_data(self) -> dict[str, str]:
        """Convert an instance of DNSTransferRequirerData to the relation representation.

        Returns:
            Dict containing the representation.
        """
        return {"addresses": json.dumps(self.addresses, default=str)}

    @classmethod
    def from_relation_data(cls, relation: ops.Relation) -> "DNSTransferRequirerData":
        """Initialize a new instance of the DNSTransferRequirerData class from the relation.

        Args:
            relation: the relation.

        Returns:
            A DNSTransferRequirerData instance.

        Raises:
            ValueError: if the value is not parseable.
        """
        try:
            loaded_data = {}
            app = cast(ops.Application, relation.app)
            relation_data = relation.data[app]
            for key, value in relation_data.items():
                loaded_data[key] = json.loads(value)
            return DNSTransferRequirerData.model_validate(loaded_data)
        except json.JSONDecodeError as ex:
            raise ValueError from ex


class DNSTransferRequires(ops.Object):
    """Requirer side of the DNS transfer requires relation."""

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the requirer charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    def get_remote_relation_data(self) -> DNSTransferProviderData | None:
        """Retrieve the remote relation data.

        Returns:
            DNSTransferProviderData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return None
        return DNSTransferProviderData.from_relation_data(relation) if relation else None

    def update_relation_data(
        self,
        relation: ops.Relation,
        requirer_data: DNSTransferRequirerData,
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            requirer_data: data as DNSTransferRequirerData.
        """
        if not relation:
            return
        relation.data[self.charm.model.app].update(requirer_data.to_relation_data())


class DNSTransferProvides(ops.Object):
    """Provider side of the DNS transfer relation."""

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name

    def get_remote_relation_data(self, relation: ops.Relation) -> DNSTransferRequirerData | None:
        """Retrieve the remote relation data.

        Args:
            relation: the relation to get data from.

        Returns:
            DNSTransferProviderData: the relation data.
        """
        if not relation:
            return None
        return DNSTransferRequirerData.from_relation_data(relation) if relation else None

    def update_relation_data(
        self,
        relation: ops.Relation,
        provider_data: DNSTransferProviderData,
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation to update.
            provider_data: data as DNSTransferProviderData.
        """
        if not relation:
            return
        relation.data[self.charm.model.app].update(provider_data.to_relation_data())
