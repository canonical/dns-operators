# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_data module."""

import logging
from unittest import mock

import pytest
from charms.topology.v0 import topology as topology_module

import bind
import models
import tests.unit.helpers

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "zones_data, topology_data, mailbox, expected",
    (
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            "testmail",
            {
                "example.com": (
                    "$ORIGIN example.com.\n"
                    "$TTL 600\n"
                    "@ IN SOA example.com. testmail.example.com. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 2.2.2.2\n"
                    "@ IN NS ns\n"
                    "ns IN A 3.3.3.3\n"
                    "sub IN A 1.2.3.4\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
                tests.unit.helpers.ZONES["multiple_records"],
            ],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            "mail",
            {
                "example.com": (
                    "$ORIGIN example.com.\n"
                    "$TTL 600\n"
                    "@ IN SOA example.com. mail.example.com. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 2.2.2.2\n"
                    "@ IN NS ns\n"
                    "ns IN A 3.3.3.3\n"
                    "sub IN A 1.2.3.4\n"
                ),
                "test.org": (
                    "$ORIGIN test.org.\n"
                    "$TTL 600\n"
                    "@ IN SOA test.org. mail.test.org. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 2.2.2.2\n"
                    "@ IN NS ns\n"
                    "ns IN A 3.3.3.3\n"
                    "ftp IN CNAME www\n"
                    "mail IN AAAA 2001:db8::1\n"
                    "www IN A 1.2.3.4\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            "mail",
            {
                "example.com": (
                    "$ORIGIN example.com.\n"
                    "$TTL 600\n"
                    "@ IN SOA example.com. mail.example.com. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 1.1.1.1\n"
                    "sub IN A 1.2.3.4\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.TOPOLOGIES["with_public_ips"],
            "mail",
            {
                "example.com": (
                    "$ORIGIN example.com.\n"
                    "$TTL 600\n"
                    "@ IN SOA example.com. mail.example.com. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 203.0.113.1\n"
                    "@ IN NS ns\n"
                    "ns IN A 203.0.113.2\n"
                    "sub IN A 1.2.3.4\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["simple"],
            ],
            tests.unit.helpers.TOPOLOGIES["with_custom_names"],
            "mail",
            {
                "example.com": (
                    "$ORIGIN example.com.\n"
                    "$TTL 600\n"
                    "@ IN SOA example.com. mail.example.com. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS dns1\n"
                    "dns1 IN A 2.2.2.2\n"
                    "@ IN NS dns1\n"
                    "dns1 IN A 3.3.3.3\n"
                    "@ IN NS dns2\n"
                    "dns2 IN A 2.2.2.2\n"
                    "@ IN NS dns2\n"
                    "dns2 IN A 3.3.3.3\n"
                    "sub IN A 1.2.3.4\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["empty"],
            ],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            "mail",
            {
                "empty.test": (
                    "$ORIGIN empty.test.\n"
                    "$TTL 600\n"
                    "@ IN SOA empty.test. mail.empty.test. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 1.1.1.1\n"
                ),
            },
        ),
        (
            [
                tests.unit.helpers.ZONES["ipv6_mixed"],
            ],
            tests.unit.helpers.TOPOLOGIES["single_unit"],
            "mail",
            {
                "ipv6.example": (
                    "$ORIGIN ipv6.example.\n"
                    "$TTL 600\n"
                    "@ IN SOA ipv6.example. mail.ipv6.example. ( 20576131 1d 1h 1h 10m )\n"
                    "@ IN NS ns\n"
                    "ns IN A 1.1.1.1\n"
                    "mail IN MX 10 mail.ipv6.example.\n"
                    'txt IN TXT "v=spf1 include:_spf.google.com ~all"\n'
                    "www IN AAAA 2001:db8::1\n"
                ),
            },
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
def test_zone_file_content(zones_data, topology_data, mailbox, expected):
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

    # pylint: disable=protected-access
    file_content = bind.BindService._zones_to_files_content(zones, topology, {"mailbox": mailbox})
    assert file_content == expected
