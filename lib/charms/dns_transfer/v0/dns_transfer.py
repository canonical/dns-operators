# Copyright 2025 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.
# pylint: disable=R0801
"""Library to manage the integration with the Bind charm.

This library contains the Requires and Provides classes for handling the integration
between an application and a charm providing the `dns_record` integration.

### Requirer Charm

```python

from charms.dns_transfer.v0.dns_transfer import DNSTransferRequires

class DNSTransferRequirerCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_primary = DNSTransferRequires(self)
        self.framework.observe(self.dns_primary.on.dns_transfer_provider_data_available, self._handler)
        ...

    def _handler(self, event: DNSTransferProviderDataAvailableEvent) -> None:
        addresses = event.addresses
        transport = event.transport
        # or self.dns_primary.get_addresses() / self.dns_primary.get_transport()

```

As shown above, the library provides a custom event to handle the scenario in
which new DNS data has been added or updated.

The DNSTransferRequires provides an `update_relation_data` method to update the relation data by
passing a list of IP addresses to the provider.

### Provider Charm

Following the previous example, this is an example of the provider charm.

```python
from charms.dns_transfer.v0.dns_transfer import DNSTransferProvides

class DNSTransferProviderCharm(ops.CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.dns_secondary = DNSTransferProvides(self)
        self.framework.observe(self.dns_secondaries.on.dns_transfer_requirer_data_available, self._handler)
        ...

    def _handler(self, event: DNSTransferRequirerDataAvailableEvent) -> None:
        addresses = event.addresses
        # or self.dns_secondary.get_addresses()

```
The DNSTransferProvides object wraps the list of relations into a `relations` property
and provides an `update_relation_data` method to update the relation data by passing
parameters with data expected by the requirer.

```python
class DNSTransferProviderCharm(ops.CharmBase):
    ...

    def _on_config_changed(self, _) -> None:
        params = {
            "addresses": ["10.20.30.40", "50.60.70.80"],
            "transport": "tls",
            "remote_hostname": "example.com",
            "zones": ["zone1.com", "zone2.com"],
        }
        for relation in self.model.relations[self.dns_secondary.relation_name]:
            self.dns_secondary.update_relation_data(relation, **params)

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
import ipaddress
import json
import logging
from enum import Enum
from typing import Any, List, Optional, cast

import ops
import pydantic

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "dns-transfer"


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


class DNSTransferRequirerDataAvailableEvent(ops.RelationEvent):
    """DNSTransfer event emitted when relation data has changed by requirer.

    Attrs:
        dns_transfer_relation_data: dns transfer relation data.
        addresses: the ips of the units of the requirer.
    """

    @property
    def dns_transfer_relation_data(self) -> DNSTransferRequirerData:
        """Get a DNSTransferRequirerData for the relation data."""
        assert self.relation.app
        return DNSTransferRequirerData.from_relation_data(self.relation)

    @property
    def addresses(self) -> list[pydantic.IPvAnyAddress]:
        """Get the addresses from the relation data."""
        return self.dns_transfer_relation_data.addresses


class DNSTransferRequiresEvents(ops.CharmEvents):
    """DNS transfer requirer events.

    This class defines the events that a DNS transfer requirer can emit.

    Attributes:
        dns_transfer_requirer_data_available: the DNSTransferRequirerDataAvailable.
    """

    dns_transfer_requirer_data_available = ops.EventSource(DNSTransferRequirerDataAvailableEvent)


class DNSTransferRequires(ops.Object):
    """Requirer side of the DNS transfer requires relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSTransferRequiresEvents()

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

    def get_remote_relation_data(self) -> DNSTransferProviderData | None:
        """Retrieve the remote relation data.

        Returns:
            DNSTransferProviderData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return None
        return DNSTransferProviderData.from_relation_data(relation) if relation else None

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        app = event.relation.app
        if app is None:
            logger.warning(
                "RelationChangedEvent: event.relation.app is not defined. Skipping data processing."
            )
            return

        try:
            _: DNSTransferProviderData = DNSTransferProviderData.from_relation_data(event.relation)
        except ValueError as ex:
            logger.warning("Failed to parse remote relation data: %s", ex)
            return

        self.on.dns_transfer_provider_data_available.emit(
            event.relation, app=event.app, unit=event.unit
        )

    def update_relation_data(
        self,
        relation: ops.Relation,
        *,
        addresses: list[str],
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            addresses: address list e.g. [10.20.30.40, 50.60.70.80].
        """
        addresses_as_ips = [ipaddress.ip_address(addr) for addr in addresses]
        dns_transfer_requirer_data = DNSTransferRequirerData(addresses=addresses_as_ips)
        relation_data = dns_transfer_requirer_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)

    # Public accessors for remote relation data
    def get_addresses(self) -> List[str]:
        """Return a list of IP addresses from the provider, as strings.

        Returns:
            A list of IP address strings, or an empty list if no valid data is found.
        """
        data: DNSTransferProviderData | None = self.get_remote_relation_data()
        return [str(ip) for ip in data.addresses] if data else []

    def get_transport(self) -> Optional[str]:
        """Return the transport protocol used by the provider.

        Returns:
            The transport string ("tcp" or "tls"), or None if unavailable.
        """
        data: DNSTransferProviderData | None = self.get_remote_relation_data()
        return data.transport.value if data else None

    def get_remote_hostname(self) -> Optional[str]:
        """Return the remote hostname advertised in the provider's TLS certificate.

        Returns:
            The remote hostname string, or None if not set.
        """
        data: DNSTransferProviderData | None = self.get_remote_relation_data()
        return data.remote_hostname if data else None

    def get_zones(self) -> List[str]:
        """Return the list of DNS zones managed by the provider.

        Returns:
            A list of zone name strings, or an empty list if no valid data is found.
        """
        data: DNSTransferProviderData | None = self.get_remote_relation_data()
        return data.zones if data else []


class DNSTransferProviderDataAvailableEvent(ops.RelationEvent):
    """DNSTransfer event emitted when relation data has changed by provider.

    Attrs:
        dns_transfer_relation_data: dns transfer relation data.
        addresses: IP list of the units composing the provider's deployment.
        transport: Type of transport (tls or tcp).
        remote_hostname: Advertised name of the host in the TLS certificate (optional).
        zones: List of zone names.
    """

    @property
    def dns_transfer_relation_data(self) -> DNSTransferProviderData:
        """Get a DNSTransferRequirerData for the relation data."""
        assert self.relation.app
        return DNSTransferProviderData.from_relation_data(self.relation)

    @property
    def addresses(self) -> list[pydantic.IPvAnyAddress]:
        """Get the addresses from the relation data."""
        return self.dns_transfer_relation_data.addresses

    @property
    def transport(self) -> TransportSecurity:
        """Get the transport from the relation data."""
        return self.dns_transfer_relation_data.transport

    @property
    def remote_hostname(self) -> Optional[str]:
        """Get the remote hostname from the relation data."""
        return self.dns_transfer_relation_data.remote_hostname

    @property
    def zones(self) -> list[str]:
        """Get the zones from the relation data."""
        return self.dns_transfer_relation_data.zones


class DNSTransferProvidesEvents(ops.CharmEvents):
    """DNS transfer provider events.

    This class defines the events that a DNS transfer provider can emit.

    Attributes:
        dns_transfer_provider_data_available: the DNSTransferProviderData.
    """

    dns_transfer_provider_data_available = ops.EventSource(DNSTransferProviderDataAvailableEvent)


class DNSTransferProvides(ops.Object):
    """Provider side of the DNS transfer relation.

    Attributes:
        on: events the provider can emit.
    """

    on = DNSTransferProvidesEvents()

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

    def get_remote_relation_data(self) -> DNSTransferRequirerData | None:
        """Retrieve the remote relation data.

        Returns:
            DNSTransferProviderData: the relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation:
            return None
        return DNSTransferRequirerData.from_relation_data(relation) if relation else None

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        app = event.relation.app
        if app is None:
            logger.warning(
                "RelationChangedEvent: event.relation.app is not defined. Skipping data processing."
            )
            return

        try:
            _: DNSTransferRequirerData = DNSTransferRequirerData.from_relation_data(event.relation)
        except ValueError as ex:
            logger.warning("Failed to parse remote relation data: %s", ex)
            return

        self.on.dns_transfer_requirer_data_available.emit(
            event.relation, app=event.app, unit=event.unit
        )

    def update_relation_data(
        self,
        relation: ops.Relation,
        *,
        addresses: List[str],
        transport: str = "tls",
        remote_hostname: Optional[str] = None,
        zones: List[str],
    ) -> None:
        """Update the relation data.

        Args:
            relation: the relation to update.
            addresses: list of IP address strings.
            transport: transport protocol string, defaults to "tls".
            remote_hostname: optional TLS hostname string.
            zones: list of DNS zone strings.
        """
        ip_addresses = [ipaddress.ip_address(addr) for addr in addresses]
        transport_val = TransportSecurity(transport)

        dns_record_provider_data = DNSTransferProviderData(
            addresses=ip_addresses,
            transport=transport_val,
            remote_hostname=remote_hostname,
            zones=zones,
        )
        relation_data = dns_record_provider_data.to_relation_data()
        relation.data[self.charm.model.app].update(relation_data)

    # Public accessors for remote relation data
    def get_addresses(self) -> List[str]:
        """Return a list of IP addresses from the provider, as strings.

        Returns:
            A list of address strings, or an empty list if no valid data is found.
        """
        data: DNSTransferRequirerData | None = self.get_remote_relation_data()
        if not data:
            return []
        return [str(ip) for ip in data.addresses]
