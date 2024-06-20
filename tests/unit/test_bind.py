# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import uuid

import pytest
from charms.bind.v0 import dns_record

import bind
import data_structures


@pytest.mark.parametrize(
    "integration_datasets, nonconflicting, conflicting",
    (
        (
            [
                data_structures.DnsEntry(
                    domain="dns.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.42.42",
                ),
                data_structures.DnsEntry(
                    domain="dns.test",
                    host_label="admin2",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.42.43",
                ),
                data_structures.DnsEntry(
                    domain="dns2.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.44.44",
                ),
            ],
            {1},
            {1, 3},
        ),
        (
            [
                data_structures.DnsEntry(
                    domain="dns.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.42.42",
                ),
                data_structures.DnsEntry(
                    domain="dns-app-2.test",
                    host_label="somehost",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="41.41.41.41",
                ),
                data_structures.DnsEntry(
                    domain="dns-app-3.test",
                    host_label="somehost",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="40.40.40.40",
                ),
            ],
            {0, 1, 2},
            set(),
        ),
        (
            [
                data_structures.DnsEntry(
                    domain="dns.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.42.42",
                ),
                data_structures.DnsEntry(
                    domain="dns.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="41.41.41.41",
                ),
            ],
            set(),
            {0, 1},
        ),
    ),
)
def test_get_conflicts(integration_datasets, nonconflicting, conflicting):
    """
    arrange: prepare some integration dataset
    act: generate conflicting sets of DnsEntries
    assert: that the generate set is what we expected
    """
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
        for e in integration_datasets
    ]
    record_requirer_data = dns_record.DNSRecordRequirerData(
        dns_entries=requirer_entries,
        service_account="fakeserviceaccount",
    )

    bind_service = bind.BindService()

    zones = bind_service._record_requirer_data_to_zones(  # pylint: disable=protected-access
        record_requirer_data
    )
    valid, conflicts = bind_service._get_conflicts(zones)  # pylint: disable=protected-access

    nonconflicting = {e for i, e in enumerate(integration_datasets) if i in nonconflicting}
    conflicting = {e for i, e in enumerate(integration_datasets) if i in conflicting}

    assert nonconflicting == valid
    assert conflicting == conflicts
