#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for the unit tests."""

# Ignore duplicate code from the helpers (they can be in the charm also)
# pylint: disable=duplicate-code

import uuid

from charms.bind.v0 import dns_record

import models

SERVICE_ACCOUNT = "fakeserviceaccount"

RECORDS = {
    "admin.dns.test_42": models.DnsEntry(
        domain="dns.test",
        host_label="admin",
        ttl=600,
        record_class="IN",
        record_type="A",
        record_data="1.1.1.42",
    ),
    "admin.dns.test_41": models.DnsEntry(
        domain="dns.test",
        host_label="admin",
        ttl=600,
        record_class="IN",
        record_type="A",
        record_data="1.1.1.41",
    ),
    "admin.dns2.test_43": models.DnsEntry(
        domain="dns2.test",
        host_label="admin",
        ttl=600,
        record_class="IN",
        record_type="A",
        record_data="1.1.1.43",
    ),
    "admin.dns2.test_41": models.DnsEntry(
        domain="dns2.test",
        host_label="admin",
        ttl=600,
        record_class="IN",
        record_type="A",
        record_data="1.1.1.41",
    ),
    "admin2.dns.test_40": models.DnsEntry(
        domain="dns.test",
        host_label="admin2",
        ttl=600,
        record_class="IN",
        record_type="A",
        record_data="1.1.1.40",
    ),
}

TOPOLOGIES = {
    "3_units_current_not_active": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": ["2.2.2.2", "3.3.3.3"],
        "current_unit_ip": "2.2.2.2",
        "public_ips": [],
        "names": [],
    },
    "4_units_current_not_active": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": ["2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "current_unit_ip": "2.2.2.2",
        "public_ips": [],
        "names": [],
    },
    "5_units_current_active": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"],
        "active_unit_ip": "5.5.5.5",
        "standby_units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "current_unit_ip": "5.5.5.5",
        "public_ips": ["1.2.3.4"],
        "names": ["nameserver.example.com"],
    },
    "single_unit": {
        "units_ip": ["1.1.1.1"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": [],
        "current_unit_ip": "1.1.1.1",
        "public_ips": [],
        "names": [],
    },
    "with_public_ips": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": ["2.2.2.2", "3.3.3.3"],
        "current_unit_ip": "2.2.2.2",
        "public_ips": ["203.0.113.1", "203.0.113.2"],
        "names": [],
    },
    "with_custom_names": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": ["2.2.2.2", "3.3.3.3"],
        "current_unit_ip": "2.2.2.2",
        "public_ips": [],
        "names": ["dns1", "dns2"],
    },
}

ZONES = {
    "simple": {
        "domain": "example.com",
        "entries": [
            {
                "host_label": "sub",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "A",
                "record_data": "1.2.3.4",
                "uuid": "98738708-7046-4a6a-8bc3-4df4b7ebd054",
            }
        ],
    },
    "multiple_records": {
        "domain": "test.org",
        "entries": [
            {
                "host_label": "www",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "A",
                "record_data": "1.2.3.4",
                "uuid": "11111111-1111-1111-1111-111111111111",
            },
            {
                "host_label": "mail",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "AAAA",
                "record_data": "2001:db8::1",
                "uuid": "22222222-2222-2222-2222-222222222222",
            },
            {
                "host_label": "ftp",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "CNAME",
                "record_data": "www",
                "uuid": "33333333-3333-3333-3333-333333333333",
            },
        ],
    },
    "empty": {
        "domain": "empty.com",
        "entries": [],
    },
    "ipv6_mixed": {
        "domain": "ipv6.example",
        "entries": [
            {
                "host_label": "www",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "AAAA",
                "record_data": "2001:db8::1",
                "uuid": "44444444-4444-4444-4444-444444444444",
            },
            {
                "host_label": "mail",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "MX",
                "record_data": "10 mail.ipv6.example.",
                "uuid": "55555555-5555-5555-5555-555555555555",
            },
            {
                "host_label": "txt",
                "ttl": 600,
                "record_class": "IN",
                "record_type": "TXT",
                "record_data": '"v=spf1 include:_spf.google.com ~all"',
                "uuid": "66666666-6666-6666-6666-666666666666",
            },
        ],
    },
}


def dns_record_requirers_data_from_integration_datasets(
    integration_datasets,
) -> list[dns_record.DNSRecordRequirerData]:
    """Create a list of DnsRecordRequirerData given integration_datasets.

    Args:
        integration_datasets: the datasets representing integration data

    Returns:
        A list of DNSRecordRequirerData.
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
            service_account=SERVICE_ACCOUNT,
        )
        record_requirers_data.append(record_requirer_data)

    return record_requirers_data
