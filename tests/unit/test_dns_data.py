# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_data module."""

import json

import pytest

import dns_data
import tests.unit.helpers


@pytest.mark.parametrize(
    "integration_datasets, zones_name, nonconflicting, conflicting",
    (
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_43"],
                ],
            ],
            {"dns.test", "dns2.test"},
            {"admin.dns.test", "admin.dns2.test"},
            set(),
        ),
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_41"],
                    tests.unit.helpers.RECORDS["admin2.dns.test_40"],
                ],
            ],
            {"dns.test", "dns2.test"},
            {"admin.dns.test", "admin.dns2.test", "admin2.dns.test"},
            set(),
        ),
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns.test_41"],
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
    record_requirers_data = tests.unit.helpers.dns_record_requirers_data_from_integration_datasets(
        integration_datasets
    )

    zones = dns_data.dns_record_relations_data_to_zones(  # pylint: disable=protected-access
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data]
    )

    assert zones_name == {zone.domain for zone in zones}

    output = dns_data.get_conflicts(zones)  # pylint: disable=protected-access
    assert nonconflicting == {f"{e.host_label}.{e.domain}" for e in output[0]}
    assert conflicting == {f"{e.host_label}.{e.domain}" for e in output[1]}


@pytest.mark.parametrize(
    "integration_datasets_before, integration_datasets_after, expected_has_changed",
    (
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_43"],
                ],
            ],
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_43"],
                ],
            ],
            False,
        ),
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_43"],
                ],
            ],
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
            ],
            True,
        ),
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
            ],
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                    tests.unit.helpers.RECORDS["admin.dns2.test_43"],
                ],
            ],
            True,
        ),
    ),
    ids=(
        "Removed duplicate entry",
        "Removed entry",
        "Added entry",
    ),
)
def test_has_changed(
    integration_datasets_before, integration_datasets_after, expected_has_changed
):
    """
    arrange: prepare some integration datasets
    act: Serialize the 'before' dataset
    assert: check if the comparison of the before dataset with the after is what we expected
    """
    record_requirers_data_before = (
        tests.unit.helpers.dns_record_requirers_data_from_integration_datasets(
            integration_datasets_before
        )
    )
    zones = dns_data.dns_record_relations_data_to_zones(
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data_before]
    )
    serialized_zones = json.dumps({"topology": "", "zones":[z.model_dump(mode="json") for z in zones]})

    record_requirers_data_after = (
        tests.unit.helpers.dns_record_requirers_data_from_integration_datasets(
            integration_datasets_after
        )
    )

    assert expected_has_changed == dns_data.has_changed(
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data_after],
        None,
        json.loads(serialized_zones),
    )
