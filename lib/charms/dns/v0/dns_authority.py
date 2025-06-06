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

import json

# pylint: disable=wrong-import-position
import re

import ops
import pydantic

DEFAULT_RELATION_NAME = "dns-authority"


class DnsAuthorityRelationData(pydantic.BaseModel):
    authoritative_ips: list[pydantic.IPv4Address | pydantic.IPv6Address]
    authoritative_zones: list[str]

    @pydantic.field_validator("authoritative_zones")
    @classmethod
    def validate_zones(cls, zones: list[str]) -> list[str]:
        """Validate the input zones.

        Args:
            zones: list of DNS zone names

        Returns:
            A list of DNS zone names

        Raises:
            ValueError if the input has an invalid DNS zone name

        Our main references are RFC 1034 and 2181
        RFC 1034, section 3.1: https://datatracker.ietf.org/doc/html/rfc1034#section-3.1
        RFC 2181, section 11: https://datatracker.ietf.org/doc/html/rfc2181#section-11
        """
        # rfc2181 says: "Any binary string whatever can be used as the label of any resource record",
        # but we still want to reduce the available space. A common regex for a label is the following:
        label_pattern = r"^[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$"

        for zone in zones:
            # RFC1034: "To simplify implementations, the total number of octets that represent a domain name is limited to 255"
            if len(zone.encode("ascii")) > 255:
                raise ValueError(f"DNS zone name exceeds 255 octets: {zone}")

            # Split zone into labels
            labels = zone.encode("ascii").strip(".").split(".")
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

    def to_relation_data(self) -> dict[str, str]:
        """Convert an instance of DnsAuthorityDataAvailableEvent to the relation representation.

        Returns:
            Dict containing the representation.
        """
        result = {
            "authoritative_ips": json.dumps(self.authoritative_ips),
            "authoritative_zones": json.dumps(self.authoritative_zones),
        }
        return result

    @classmethod
    def from_relation_data(
        cls, relation_data: ops.RelationDataContent
    ) -> "DnsAuthorityRelationData":
        """Get a DnsAuthorityRelationData wrapping the relation data.

        Arguments:
            relation_data: the relation data.

        Returns: a DnsAuthorityRelationData instance with the relation data.
        """
        return cls(
            authority_zones=json.loads(relation_data.get("authority_zones", "[]")),
            authority_ips=json.loads(relation_data.get("authority_ips", "[]")),
        )


class DnsAuthorityDataAvailableEvent(ops.RelationEvent):
    """DnsAuthority event emitted when relation data has changed.

    Attrs:
        dns_authority_relation_data: the DNS authority relation data
        authoritative_zones: the zones upon which the provider has authority
        authoritative_ips: the ips of the units of the provider
    """

    @property
    def dns_authority_relation_data(self) -> DnsAuthorityRelationData:
        """Get a DnsAuthorityRelationData for the relation data."""
        assert self.relation.app
        return DnsAuthorityRelationData.from_relation_data(self.relation.data[self.relation.app])

    @property
    def authority_zones(self) -> str:
        return self.dns_authority_relation_data.authority_zones

    @property
    def authority_ips(self) -> str:
        return self.dns_authority_relation_data.authority_ips


class DnsAuthorityRequiresEvents(ops.CharmEvents):
    """DnsAuthority events.

    This class defines the events that a DnsAuthority requirer can emit.

    Attrs:
        dns_authority_data_available: the DnsAuthorityDataAvailableEvent.
    """

    dns_authority_data_available = ops.EventSource(DnsAuthorityDataAvailableEvent)


class DnsAuthorityRequires(ops.Object):
    """Requirer side of the DnsAuthority relation.

    Attrs:
        on: events the provider can emit.
    """

    on = DnsAuthorityRequiresEvents()

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

    def get_relation_data(self) -> DnsAuthorityRelationData | None:
        """Retrieve the relation data.

        Returns:
            The relation data.
        """
        relation = self.model.get_relation(self.relation_name)
        if not relation or not relation.app or not relation.data[relation.app]:
            return None
        return DnsAuthorityRelationData.from_relation_data(relation.data[relation.app])


class DnsAuthorityProvides(ops.Object):
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

    def update_relation_data(self, relation: ops.Relation, data: DnsAuthorityRelationData) -> None:
        """Update the relation data.

        Args:
            relation: the relation for which to update the data.
            data: a DnsAuthorityRelationData instance wrapping the data to be updated.
        """
        relation.data[self.charm.model.app].update(data.to_relation_data())
