# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_data module."""

import uuid

import pytest
from charms.bind.v0 import dns_record

import dns_data
import models


@pytest.mark.parametrize(
    "integration_datasets, zones_name, nonconflicting, conflicting",
    (
        (
            [
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                ],
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    models.DnsEntry(
                        domain="dns2.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.43",
                    ),
                ],
            ],
            {"dns.test", "dns2.test"},
            {"admin.dns.test", "admin.dns2.test"},
            set(),
        ),
        (
            [
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    models.DnsEntry(
                        domain="dns2.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="41.41.41.41",
                    ),
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin2",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="40.40.40.40",
                    ),
                ],
            ],
            {"dns.test", "dns2.test"},
            {"admin.dns.test", "admin.dns2.test", "admin2.dns.test"},
            set(),
        ),
        (
            [
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="41.41.41.41",
                    ),
                ],
            ],
            {"dns.test"},
            set(),
            {"admin.dns.test"},
        ),
    ),
    ids=(
        "Duplicate entry",
        "No conflicts",
        "Basic conflict",
    ),
)
def test_get_conflicts(integration_datasets, zones_name, nonconflicting, conflicting):
    """
    arrange: prepare some integration datasets
    act: generate conflicting sets of DnsEntries
    assert: that the generate set is what we expected
    """
    record_requirers_data = []
    for requirer in integration_datasets:
        requirer_entries = [
            dns_record.RequirerEntry(
                domain=e.domain,
                host_label=e.host_label,
                ttl=e.ttl,
                record_class=e.record_class,
                record_type=e.record_type,
                record_data=e.record_data,
                uuid=uuid.uuid4(),
            )
            for e in requirer
        ]
        record_requirer_data = dns_record.DNSRecordRequirerData(
            dns_entries=requirer_entries,
            service_account="fakeserviceaccount",
        )
        record_requirers_data.append(record_requirer_data)

    zones = dns_data.dns_record_relations_data_to_zones(  # pylint: disable=protected-access
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data]
    )
    assert zones_name == {zone.domain for zone in zones}

    output = dns_data.get_conflicts(zones)  # pylint: disable=protected-access
    assert nonconflicting == {f"{e.host_label}.{e.domain}" for e in output[0]}
    assert conflicting == {f"{e.host_label}.{e.domain}" for e in output[1]}


@pytest.mark.parametrize(
    "zonefile_content, metadata, error",
    (
        ("", {}, dns_data.EmptyZoneFileMetadataError),
        ("sometext; someothertext", {}, dns_data.EmptyZoneFileMetadataError),
        ("$ORIGIN test.dns.test.; HASH:1234", {"HASH": "1234"}, None),
        (
            "$ORIGIN test.dns.test.; HASH:1234\n$ORIGIN test2.dns.test.; PLOP:plop",
            {"HASH": "1234", "PLOP": "plop"},
            None,
        ),
        (
            "$ORIGIN test.dns.test.; HASH:1234 HASH:4567",
            {},
            dns_data.DuplicateMetadataEntryError,
        ),
        (
            "$ORIGIN test.dns.test.; HASH:1234\n$ORIGIN test2.dns.test.; HASH:4567",
            {},
            dns_data.DuplicateMetadataEntryError,
        ),
        ("$ORIGIN test.dns.test.; HASH::", None, dns_data.InvalidZoneFileMetadataError),
        ("$ORIGIN test.dns.test.;    ", {"HASH": "1234"}, dns_data.EmptyZoneFileMetadataError),
        (
            "\n\nsometext\n\n$ORIGIN test.dns.test.; HASH:1234 PLOP:plop\nsomeothertext",
            {"HASH": "1234", "PLOP": "plop"},
            None,
        ),
    ),
)
def test_get_zonefile_metadata(zonefile_content: str, metadata: dict[str, str], error):
    """
    arrange: nothing
    act: get the metadata from the zonefile_content
    assert: the correct metadata should be found or the correct exception raised
    """
    if error is not None:
        with pytest.raises(error):
            dns_data._get_zonefile_metadata(zonefile_content)  # pylint: disable=protected-access
    else:
        assert metadata == dns_data._get_zonefile_metadata(  # pylint: disable=protected-access
            zonefile_content
        )


@pytest.mark.parametrize(
    "named_conf_content, wanted",
    (
        (
            # pylint: disable=line-too-long
            """
            include "/some/path/zones.rfc1918";
            zone "service.test" IN { type primary; file "/some/path/db.service.test"; allow-update { none; }; allow-transfer {  }; };
            """,
            [],
        ),
        (
            # pylint: disable=line-too-long
            """
            include "/some/path/zones.rfc1918";
            zone "service.test" IN { type primary; file "/some/path/db.service.test"; allow-update { none; }; allow-transfer { 42.42.42.42; }; };
            """,
            ["42.42.42.42"],
        ),
        (
            # pylint: disable=line-too-long
            """
            include "/some/path/zones.rfc1918";
            zone "service.test" IN { type primary; file "/some/path/db.service.test"; allow-update { none; }; allow-transfer { 42.42.42.42; 42.42.42.43; }; };
            """,
            ["42.42.42.42", "42.42.42.43"],
        ),
        (
            # pylint: disable=line-too-long
            """
            include "/some/path/zones.rfc1918";
            zone "service.test" IN { type primary; file "/some/path/db.service.test"; allow-update { none; }; allow-transfer { 42.42.42.42; }; };
            zone "service2.test" IN { type primary; file "/some/path/db.service.test"; allow-update { none; }; allow-transfer { 42.42.42.43; }; };
            """,
            ["42.42.42.42"],
        ),
    ),
)
def test_get_secondaries_ip_from_conf(named_conf_content: str, wanted: list[str]):
    """
    arrange: nothing
    act: get the IPs from named_conf_content
    assert: the correct IPs should be found
    """
    result = dns_data._get_secondaries_ip_from_conf(  # pylint: disable=protected-access
        named_conf_content
    )
    assert wanted == result
