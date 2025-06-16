# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Common data structures used in this charm."""

import hashlib

import pydantic
from charms.bind.v0.dns_record import RecordClass, RecordType, RequirerEntry


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
    record_data: str | pydantic.IPvAnyAddress

    # Validator for record_data
    @classmethod
    @pydantic.field_validator("record_data")
    def validate_record_data(
        cls, value: str | pydantic.IPvAnyAddress, info: pydantic.ValidationInfo
    ) -> str | pydantic.IPvAnyAddress:
        """Validate record_data based on record_type.

        Args:
            value: input value
            info: information about the current model

        Raises:
            ValueError: when the input value could not be validated

        Returns:
            The validated value
        """
        record_type = info.data.get("record_type")
        if record_type in (RecordType.A, RecordType.AAAA):
            if isinstance(value, pydantic.IPvAnyAddress):
                return value
            if isinstance(value, str):
                try:
                    # mypy is confused by the fact that pydantic interfaces
                    # an external class
                    return pydantic.IPv4Address(value)  # type: ignore
                except ValueError:
                    pass

                try:
                    # mypy is confused by the fact that pydantic interfaces
                    # an external class
                    return pydantic.IPv6Address(value)  # type: ignore
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
        return value

    def __hash__(self) -> int:
        """Get a hash of a DnsEntry based on its attributes.

        Returns:
            A hash for the current object.
        """
        h = hashlib.blake2b()
        for data in (getattr(self, k) for k in self.__dict__):
            h.update(str(data).encode())
        return int.from_bytes(h.digest(), byteorder="big")


class Zone(pydantic.BaseModel):
    """Class used to represent a zone.

    Attributes:
        domain: example: "dns.test"
        entries: a list of DnsEntry instances
    """

    domain: str
    entries: set[DnsEntry]

    def __hash__(self) -> int:
        """Get a hash of a Zone based on its DNSEntries.

        Returns:
            A hash for the current object.
        """
        h = hashlib.blake2b()
        # We sort the list of entries to make sure that the elements are always in the same order
        # This is true because `sorted()` is guaranteed to be stable
        # https://docs.python.org/3/library/functions.html#sorted
        for entry_hash in sorted([hash(e) for e in self.entries]):
            h.update(entry_hash.to_bytes((entry_hash.bit_length() + 7) // 8, byteorder="big"))
        return int.from_bytes(h.digest(), byteorder="big")


def create_dns_entry_from_requirer_entry(requirer_entry: RequirerEntry) -> DnsEntry:
    """Create a DnsEntry from a RequirerEntry.

    Args:
        requirer_entry: input RequirerEntry

    Returns:
        A DnsEntry
    """
    return DnsEntry(
        domain=requirer_entry.domain,
        host_label=requirer_entry.host_label,
        record_class=requirer_entry.record_class,
        record_type=requirer_entry.record_type,
        record_data=requirer_entry.record_data,
        ttl=requirer_entry.ttl,
    )


class Topology(pydantic.BaseModel):
    """Class used to represent the current units topology.

    Attributes:
        units_ip: IPs of all the units
        active_unit_ip: IP of the active unit
        standby_units_ip: IPs of the standby units
        current_unit_ip: IP of the current unit
        is_current_unit_active: Is the current unit active ?
    """

    units_ip: list[pydantic.IPvAnyAddress]
    active_unit_ip: pydantic.IPvAnyAddress | None
    standby_units_ip: list[pydantic.IPvAnyAddress]
    current_unit_ip: pydantic.IPvAnyAddress

    @property
    def is_current_unit_active(self) -> bool:
        """Check if the current unit is the active unit.

        Returns:
            True if the current unit is effectively the active unit.
        """
        return self.current_unit_ip == self.active_unit_ip
