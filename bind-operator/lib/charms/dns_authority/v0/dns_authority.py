# Copyright 2025 Canonical Ltd.
# Licensed under the Apache2.0. See LICENSE file in charm source for details.

"""Library to manage the integration with an authoritative DNS charm."""

# The unique Charmhub library identifier, never change it
LIBID = "b2697d5736cdc98807860010f911d65d"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

PYDEPS = ["pydantic>=2"]

# pylint: disable=wrong-import-position
import json
import re
import typing

import ops
import pydantic

DEFAULT_RELATION_NAME = "dns-authority"


class DNSAuthorityRelationData(pydantic.BaseModel):
    """Pydantic model representing the DNS authority relation data.

    Attrs:
        addresses: list of IP addresses of the DNS authority servers
        zones: list of DNS zone names uplon which the servers have authority
    """

    addresses: list[pydantic.IPvAnyAddress]
    zones: list[str]

    @pydantic.root_validator(pre=True)
    @classmethod
    def ensure_uniqueness(cls, values: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Ensure addresses and zones are unique.

        Args:
            values: input values for the model

        Returns:
            validated values
        """
        if "addresses" in values:
            values["addresses"] = list(set(values["addresses"]))
        if "zones" in values:
            values["zones"] = list(set(values["zones"]))
        return values

    @pydantic.field_validator("zones")
    @classmethod
    def validate_zones(cls, zones: list[str]) -> list[str]:
        """Validate the input zones.

        Args:
            zones: list of DNS zone names

        Returns:
            A list of DNS zone names

        Raises:
            ValueError: if the input has an invalid DNS zone name

        Our main references are RFC 1034 and 2181
        RFC 1034: https://datatracker.ietf.org/doc/html/rfc1034#section-3.1
        RFC 2181: https://datatracker.ietf.org/doc/html/rfc2181#section-11
        """
        # rfc2181: "Any binary string whatever can be used as the label of any resource record",
        # But we still want to reduce the available space.
        # A common regex for a label is the following:
        label_pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$"

        for zone in zones:
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

        return zones

    @pydantic.field_serializer("addresses")
    def serialize_record_data(self, addresses: list[pydantic.IPvAnyAddress]) -> str:
        """Serialize record data.

        Args:
            addresses: input value

        Returns:
            serialized value
        """
        return json.dumps([str(x) for x in addresses])

    def to_relation_data(self) -> dict[str, str]:
        """Convert an instance of DNSAuthorityDataAvailableEvent to the relation representation.

        Returns:
            Dict containing the representation.
        """
        result = {
            "addresses": json.dumps([str(x) for x in self.addresses]),
            "zones": json.dumps(self.zones),
        }
        return result

    @classmethod
    def from_relation_data(
        cls, relation_data: ops.RelationDataContent
    ) -> "DNSAuthorityRelationData":
        """Get a DNSAuthorityRelationData wrapping the relation data.

        Arguments:
            relation_data: the relation data.

        Returns: a DNSAuthorityRelationData instance with the relation data.
        """
        return cls(
            zones=json.loads(relation_data.get("zones", "[]")),
            addresses=json.loads(relation_data.get("addresses", "[]")),
        )


class DNSAuthorityDataAvailableEvent(ops.RelationEvent):
    """DNSAuthority event emitted when relation data has changed.

    Attrs:
        dns_authority_relation_data: the DNS authority relation data
        zones: the zones upon which the provider has authority
        addresses: the ips of the units of the provider
    """

    @property
    def dns_authority_relation_data(self) -> DNSAuthorityRelationData:
        """Get a DNSAuthorityRelationData for the relation data."""
        assert self.relation.app
        return DNSAuthorityRelationData.from_relation_data(self.relation.data[self.relation.app])

    @property
    def zones(self) -> list[str]:
        """Get the zones from the relation data."""
        return self.dns_authority_relation_data.zones

    @property
    def addresses(self) -> list[pydantic.IPvAnyAddress]:
        """Get the addresses from the relation data."""
        return self.dns_authority_relation_data.addresses


class DNSAuthorityRequiresEvents(ops.CharmEvents):
    """DNSAuthority events.

    This class defines the events that a DNSAuthority requirer can emit.

    Attrs:
        dns_authority_data_available: the DNSAuthorityDataAvailableEvent.
    """

    dns_authority_data_available = ops.EventSource(DNSAuthorityDataAvailableEvent)


class DNSAuthorityRequires(ops.Object):
    """Requirer side of the DNSAuthority relation.

    Attrs:
        on: events the provider can emit.
    """

    on = DNSAuthorityRequiresEvents()

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

    def _on_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Event emitted when the relation has changed.

        Args:
            event: event triggering this handler.
        """
        assert event.relation.app
        if event.relation.data[event.relation.app]:
            self.on.dns_authority_data_available.emit(
                event.relation, app=event.app, unit=event.unit
            )

    def get_relation_data(self) -> DNSAuthorityRelationData | None:
        """Retrieve the relation data.

        Returns:
            The relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation or not relation.app or not relation.data[relation.app]:
            return None
        return DNSAuthorityRelationData.from_relation_data(relation.data[relation.app])


class DNSAuthorityProvides(ops.Object):
    """Provider side of the DNSAuthority relation.

    Attrs:
        charm: the provider charm
        relation_name: the relation name
        relations: the list of relation instances associated with the relation name
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
        """The list of Relation instances associated with this relation_name.

        Returns:
            List of relations to this charm.
        """
        return list(self.model.relations[self.relation_name])

    def update_relation_data(self, relation: ops.Relation, data: DNSAuthorityRelationData) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            data: a DNSAuthorityRelationData instance wrapping the data to be updated.
        """
        relation.data[self.charm.model.app].update(data.to_relation_data())
