# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS data logic."""

import logging
import pathlib
import re

from charms.bind.v0.dns_record import (
    DNSProviderData,
    DNSRecordProviderData,
    DNSRecordRequirerData,
    RequirerEntry,
    Status,
)

import constants
import exceptions
import models

logger = logging.getLogger(__name__)


class InvalidZoneFileMetadataError(exceptions.BindCharmError):
    """Exception raised when a zonefile has invalid metadata."""


class EmptyZoneFileMetadataError(exceptions.BindCharmError):
    """Exception raised when a zonefile has no metadata."""


class DuplicateMetadataEntryError(exceptions.BindCharmError):
    """Exception raised when a zonefile has metadata with duplicate entries."""


def create_dns_record_provider_data(
    relation_data: list[tuple[DNSRecordRequirerData, DNSRecordProviderData]],
) -> DNSRecordProviderData:
    """Create dns record provider data from relation data.

    The result of this function should be used to update the relation.
    It contains statuses for each DNS record request.

    Args:
        relation_data: input relation data

    Returns:
        A DNSRecordProviderData object with requests' status
    """
    zones = dns_record_relations_data_to_zones(relation_data)
    nonconflicting, conflicting = get_conflicts(zones)
    statuses = []
    for record_requirer_data, _ in relation_data:
        for requirer_entry in record_requirer_data.dns_entries:
            dns_entry = models.create_dns_entry_from_requirer_entry(requirer_entry)
            if dns_entry in nonconflicting:
                statuses.append(DNSProviderData(uuid=requirer_entry.uuid, status=Status.APPROVED))
                continue
            if dns_entry in conflicting:
                statuses.append(DNSProviderData(uuid=requirer_entry.uuid, status=Status.CONFLICT))
                continue
            statuses.append(DNSProviderData(uuid=requirer_entry.uuid, status=Status.UNKNOWN))
    return DNSRecordProviderData(dns_entries=statuses)


def has_a_zone_changed(
    relation_data: list[tuple[DNSRecordRequirerData, DNSRecordProviderData]],
    topology: models.Topology | None,
) -> bool:
    """Check if a zone definition has changed.

    The zone definition is checked from a custom hash constructed from its DNS records.

    Args:
        relation_data: input relation data
        topology: Topology of the current deployment

    Returns:
        True if a zone has changed, False otherwise.
    """
    zones = dns_record_relations_data_to_zones(relation_data)
    logger.debug("Zones: %s", [z.domain for z in zones])
    for zone in zones:
        try:
            zonefile_content = pathlib.Path(
                constants.DNS_CONFIG_DIR, f"db.{zone.domain}"
            ).read_text(encoding="utf-8")
            metadata = _get_zonefile_metadata(zonefile_content)
        except (
            InvalidZoneFileMetadataError,
            EmptyZoneFileMetadataError,
            FileNotFoundError,
        ):
            return True
        if "HASH" in metadata and hash(zone) != int(metadata["HASH"]):
            logger.debug("Config hash has changed !")
            return True

    if topology is not None and topology.is_current_unit_active:
        try:
            named_conf_content = pathlib.Path(
                constants.DNS_CONFIG_DIR, "named.conf.local"
            ).read_text(encoding="utf-8")
        except FileNotFoundError:
            return True
        return (
            _get_secondaries_ip_from_conf(named_conf_content).sort()
            != [str(ip) for ip in topology.standby_units_ip].sort()
        )

    return False


def record_requirer_data_to_zones(
    record_requirer_data: DNSRecordRequirerData,
) -> list[models.Zone]:
    """Convert DNSRecordRequirerData to zone files.

    Args:
        record_requirer_data: The input DNSRecordRequirerData

    Returns:
        A list of zones
    """
    zones_entries: dict[str, list[RequirerEntry]] = {}
    for entry in record_requirer_data.dns_entries:
        if entry.domain not in zones_entries:
            zones_entries[entry.domain] = []
        zones_entries[entry.domain].append(entry)

    zones: list[models.Zone] = []
    for domain, entries in zones_entries.items():
        zone = models.Zone(domain=domain, entries=[])
        for entry in entries:
            zone.entries.add(models.create_dns_entry_from_requirer_entry(entry))
        zones.append(zone)
    return zones


def get_conflicts(zones: list[models.Zone]) -> tuple[set[models.DnsEntry], set[models.DnsEntry]]:
    """Return conflicting and non-conflicting entries.

    Args:
        zones: list of the zones to check

    Returns:
        A tuple containing the non-conflicting and conflicting entries
    """
    entries: set[models.DnsEntry] = {e for z in zones for e in z.entries}
    conflicting_entries: set[models.DnsEntry] = set()
    for entry in entries:
        for e in entries:
            if entry.conflicts(e) and entry != e:
                conflicting_entries.add(entry)

    return (entries - conflicting_entries, conflicting_entries)


def dns_record_relations_data_to_zones(
    relation_data: list[tuple[DNSRecordRequirerData, DNSRecordProviderData]],
) -> list[models.Zone]:
    """Return zones from all the dns_record relations data.

    Args:
        relation_data: input relation data

    Returns:
        The zones from the record_requirer_data
    """
    zones: dict[str, models.Zone] = {}
    for record_requirer_data, _ in relation_data:
        for new_zone in record_requirer_data_to_zones(record_requirer_data):
            if new_zone.domain in zones:
                zones[new_zone.domain].entries.update(new_zone.entries)
            else:
                zones[new_zone.domain] = new_zone
    return list(zones.values())


def _get_secondaries_ip_from_conf(named_conf_content: str) -> list[str]:
    """Get the secondaries IP addresses from the named.conf.local file.

    This is useful to check if we need to regenerate
    the file after a change in the network topology.

    This function is only taking the first line of named.conf.local with a zone-transfer
    into account. It works when the charm is writing the config files but is a bit
    brittle if those are modified by a human.
    TODO: This should be reworked (along with the metadata system) in something more durable
    like an external json file to store that information.

    Args:
        named_conf_content: content of the named.conf.local file

    Returns:
        A list of IPs as strings
    """
    for line in named_conf_content.splitlines():
        if "allow-transfer" in line:
            if match := re.search(r"allow-transfer\s*\{([^}]+)\}", line):
                return [ip.strip() for ip in match.group(1).split(";") if ip.strip() != ""]
    return []


def _get_zonefile_metadata(zonefile_content: str) -> dict[str, str]:
    """Get the metadata of a zonefile.

    Args:
        zonefile_content: The content of the zonefile.

    Returns:
        The hash of the corresponding zonefile.

    Raises:
        InvalidZoneFileMetadataError: when the metadata of the zonefile could not be parsed.
        EmptyZoneFileMetadataError: when the metadata of the zonefile is empty.
        DuplicateMetadataEntryError: when the metadata of the zonefile has duplicate entries.
    """
    # This assumes that the file was generated with the constants.ZONE_HEADER_TEMPLATE template
    metadata = {}
    try:
        lines = zonefile_content.split("\n")
        for line in lines:
            # We only take the $ORIGIN line into account
            if not line.startswith("$ORIGIN"):
                continue
            for token in line.split(";")[1].split():
                k, v = token.split(":")
                if k in metadata:
                    raise DuplicateMetadataEntryError(f"Duplicate metadata entry '{k}'")
                metadata[k] = v
    except (IndexError, ValueError) as err:
        raise InvalidZoneFileMetadataError(err) from err

    if metadata:
        return metadata
    raise EmptyZoneFileMetadataError("No metadata found !")
