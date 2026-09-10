# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for the automatically allocated domains."""

import ipaddress
import re

from charms.dns_record.v0.dns_record import Record, RecordClass, RecordType

import constants

# Host label of the wildcard record covering the subdomains of an allocated domain
WILDCARD_HOST_LABEL = "*"

# Maximum length of a domain name
DOMAIN_MAX_LENGTH = 253

_LABEL_PATTERN = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


def normalize_domain(domain: str) -> str:
    """Normalize a domain name.

    Args:
        domain: the domain name to normalize.

    Returns:
        the domain name, lowercase and without its surrounding whitespace or its
        trailing dot.
    """
    return domain.strip().rstrip(".").lower()


def fqdn(host_label: str, domain: str) -> str:
    """Build the fully qualified domain name of a record.

    Args:
        host_label: the host label of the record.
        domain: the domain of the record.

    Returns:
        the normalized fully qualified domain name.
    """
    return normalize_domain(f"{host_label.strip().strip('.')}.{domain}")


def is_within(name: str, domain: str) -> bool:
    """Check whether a domain name is a domain or one of its subdomains.

    Args:
        name: the domain name to check.
        domain: the domain to check the name against.

    Returns:
        True when the name is the domain itself or one of its subdomains.
    """
    name = normalize_domain(name)
    domain = normalize_domain(domain)
    if not domain:
        return False
    return name == domain or name.endswith(f".{domain}")


def is_valid_domain(domain: str) -> bool:
    """Check whether a domain name is a valid one.

    Args:
        domain: the domain name to check.

    Returns:
        True when the domain name is a valid domain name.
    """
    domain = normalize_domain(domain)
    if not domain or len(domain) > DOMAIN_MAX_LENGTH:
        return False
    return all(_LABEL_PATTERN.match(label) for label in domain.split("."))


def record_type(address: str) -> RecordType:
    """Get the record type matching an IP address.

    Args:
        address: the IP address of the record.

    Returns:
        RecordType.A for an IPv4 address, RecordType.AAAA for an IPv6 one.

    Raises:
        ValueError: when the address is not a valid IP address.
    """
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError as exc:
        raise ValueError(f"Not an IP address: {address!r}") from exc
    if parsed.version == 6:
        return RecordType.AAAA
    return RecordType.A


def records(domain: str, addresses: list[str]) -> list[Record]:
    """Build the records of an automatically allocated domain.

    The domain itself and a wildcard covering all of its subdomains are pointed at
    every address. The wildcard lets the requirer hand out subdomains of its allocated
    domain, which is what an ingress provider needs.

    Args:
        domain: the automatically allocated domain.
        addresses: the IP addresses the domain resolves to.

    Returns:
        the records to request from the upstream DNS provider.

    Raises:
        ValueError: when the domain has no parent domain.
    """
    host_label, _, parent_domain = normalize_domain(domain).partition(".")
    if not host_label or not parent_domain:
        raise ValueError(f"Not an automatically allocated domain: {domain!r}")

    return [
        Record(
            domain=parent_domain,
            host_label=label,
            ttl=constants.DDNS_RECORD_TTL,
            record_class=RecordClass.IN,
            record_type=record_type(address),
            record_data=address,
        )
        for label in (host_label, f"{WILDCARD_HOST_LABEL}.{host_label}")
        for address in addresses
    ]
