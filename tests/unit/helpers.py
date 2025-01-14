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
    },
    "4_units_current_not_active": {
        "units_ip": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "active_unit_ip": "1.1.1.1",
        "standby_units_ip": ["2.2.2.2", "3.3.3.3", "4.4.4.4"],
        "current_unit_ip": "2.2.2.2",
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
