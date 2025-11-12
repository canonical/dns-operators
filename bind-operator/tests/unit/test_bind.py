# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_data module."""

# pylint: disable=too-many-positional-arguments

import logging
from unittest import mock

import pytest

import bind
import models
import tests.unit.helpers
from lib.charms.topology.v0 import topology as topology_module

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "zones_data, config_data, topology_data, secondary_ips, mailbox, expected",
    (
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.CONFIGS["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "testmail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["simple_case"],
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
                tests.unit.helpers.ZONES["multiple_records"],
            ],
            tests.unit.helpers.CONFIGS["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["multiple_zones"],
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.CONFIGS["single_unit"],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["single_unit"],
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.CONFIGS["with_public_ips"],
            tests.unit.helpers.TOPOLOGIES["with_public_ips"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["with_public_ips"],
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.CONFIGS["with_custom_names"],
            tests.unit.helpers.TOPOLOGIES["with_custom_names"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["with_custom_names"],
        ),
        (
            [
                tests.unit.helpers.ZONES["empty"],
            ],
            tests.unit.helpers.CONFIGS["single_unit"],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["empty_zone"],
        ),
        (
            [
                tests.unit.helpers.ZONES["ipv6_mixed"],
            ],
            tests.unit.helpers.CONFIGS["single_unit"],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            tests.unit.helpers.SECONDARY_IPS["none"],
            "mail",
            tests.unit.helpers.EXPECTED_ZONE_FILES["ipv6_mixed"],
        ),
    ),
    ids=(
        "Test simple case",
        "Test with multiple zones",
        "Test with single unit topology (no standby units)",
        "Test with public IPs configured",
        "Test with custom names configured",
        "Test with empty zone (no DNS entries)",
        "Test with IPv6 and mixed record types",
    ),
)
@mock.patch("time.time", mock.MagicMock(return_value=1234567890))
def test_zone_file_content(
    zones_data, config_data, topology_data, secondary_ips, mailbox, expected
):
    """
    arrange: prepare some zones and network topology
    act: create zone file content
    assert: it should be correct
    """
    zones = []
    for zone_data in zones_data:
        zone = models.Zone(domain=zone_data["domain"], entries=set())
        for entry_data in zone_data["entries"]:
            entry_data["domain"] = zone_data["domain"]
            zone.entries.add(models.DnsEntry(**entry_data))
        zones.append(zone)
    topology = topology_module.Topology(**topology_data) if topology_data is not None else None
    config = {"mailbox": mailbox}
    if "names" in config_data:
        config["names"] = ",".join(config_data["names"])
    if "public-ips" in config_data:
        config["public-ips"] = ",".join(config_data["public-ips"])

    # pylint: disable=protected-access
    file_content = bind.BindService._zones_to_files_content(zones, topology, config, secondary_ips)
    assert file_content == expected
