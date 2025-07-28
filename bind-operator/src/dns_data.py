# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS data logic."""

import collections
import json
import logging
import typing

from charms.bind.v0.dns_record import (
    DNSProviderData,
    DNSRecordProviderData,
    DNSRecordRequirerData,
    RequirerEntry,
    Status,
)

import models
import topology as topology_module

logger = logging.getLogger(__name__)


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


def has_changed(
    relation_data: list[tuple[DNSRecordRequirerData, DNSRecordProviderData]],
    topology: topology_module.Topology | None,
    last_valid_state: dict[str, typing.Any],
) -> bool:
    """Check if the dns data has changed.

    This could be a change in a zone, or a removal/addition of a zone,
    or a change in the topology.
    We use the state.json file to compare the state when
    the last configuration was minted to the current one.

    Args:
        relation_data: input relation data
        topology: Topology of the current deployment
        last_valid_state: The last valid state, deserialized from a state.json file

    Returns:
        True if a zone has changed, False otherwise.
    """
    zones = dns_record_relations_data_to_zones(relation_data)

    if "zones" not in last_valid_state or zones != last_valid_state["zones"]:
        return True

        return True

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
        zone = models.Zone(domain=domain, entries=set())
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
    look_alikes = collections.defaultdict(list)

    for z in zones:
        for e in z.entries:
            look_alikes[f"{e.domain},{e.host_label},{e.record_class},{e.record_type}"].append(e)

    conflicting = set()
    non_conflicting = set()

    for entries in look_alikes.values():
        if len(entries) > 1:
            for e in entries:
                conflicting.add(e)
        else:
            non_conflicting.add(entries[0])

    return (non_conflicting, conflicting)


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



    """Dump the current state.

    We need this cumbersome way of serializing the state because
    we want the zones and the topology.
    Also, a Zone has a set of DNSEntry that is dumped as a dict() when using mode="python".
    See more about this issue here: https://github.com/pydantic/pydantic/issues/4186

    Args:
        zones: list of the zones
        topology: Topology of the current deployment

    Returns:
        The dumped state as a string
    """
    to_dump = {
        "topology": topology.model_dump(mode="json") if topology is not None else None,
        "zones": [zone.model_dump(mode="json") for zone in zones if zone is not None],
    }
    return json.dumps(to_dump)


def load_state(serialized_state: str) -> dict[str, typing.Any]:
    """Load the serialized state.

    The serialized state is assumed to have been produced by dump_state()

    Args:
        serialized_state:json string of the previously dumped state

    Returns:
        The loaded state
    """
    state = json.loads(serialized_state)
    if state["topology"] is not None:
    if state["topology"] is not None:
    state["zones"] = [models.Zone(**zone) for zone in state["zones"]]
    return state
