# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Common data structures used in this charm."""

import typing

import pydantic
from charms.bind.v0.dns_record import RecordClass, RecordType


class DnsEntry(pydantic.BaseModel):
    """Class used to represent a DNS entry.

    Attributes:
        domain: example: "dns.test"
        host_label: example: "admin"
        ttl: example: 600
        record_class: example: "IN"
        record_type: example: "A"
        record_data: example: "42.42.42.42"
    """

    domain: str = pydantic.Field(min_length=1)
    host_label: str = pydantic.Field(min_length=1)
    ttl: int
    record_class: RecordClass
    record_type: RecordType
    record_data: pydantic.IPvAnyAddress

    # This works as a primary key in a database
    # Two DnsEntry with the same key will conflict

    def conflicts(self, other: "DnsEntry") -> bool:
        """Check if it conflicts with another DnsEntry.

        Args:
            other: DnsEntry to check conflicts with.

        Returns:
            True if they conflict, False otherwise.
        """
        key_attributes: typing.Set[str] = {"host_label", "record_class", "record_type"}
        return hash(tuple(getattr(self, k) for k in key_attributes)) == hash(
            tuple(getattr(other, k) for k in key_attributes)
        )

    def __hash__(self) -> int:
        """Get a hash of a DnsEntry based on its attributes.

        Returns:
            A hash for the current object.
        """
        return hash(tuple(getattr(self, k) for k in self.__dict__))


class Zone(pydantic.BaseModel):
    """Class used to represent a zone.

    Attributes:
        domain: example: "dns.test"
        entries: a list of DnsEntry instances
    """

    domain: str
    entries: typing.List[DnsEntry]
