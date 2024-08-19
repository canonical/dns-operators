# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns_data module."""

import json

import pytest

import dns_data
import models
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
    (
        "integration_datasets_before, "
        "integration_datasets_after, "
        "topology_data_before, "
        "topology_data_after, "
        "expected_has_changed"
    ),
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
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
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
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
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
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            True,
        ),
        (
            [
                [
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
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
            tests.unit.helpers.TOPOLOGIES["4_units_current_not_active"],
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
                ],
            ],
            None,
            None,
            False,
        ),
    ),
    ids=(
        "Removed duplicate entry",
        "Removed entry",
        "Added entry",
        "Simple topology change",
        "No topology",
    ),
)
def test_has_changed(
    integration_datasets_before,
    integration_datasets_after,
    topology_data_before,
    topology_data_after,
    expected_has_changed,
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
    topology_before = (
        models.Topology(**topology_data_before) if topology_data_before is not None else None
    )
    serialized_state = dns_data.dump_state(zones, topology_before)

    record_requirers_data_after = (
        tests.unit.helpers.dns_record_requirers_data_from_integration_datasets(
            integration_datasets_after
        )
    )

    assert expected_has_changed == dns_data.has_changed(
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data_after],
        models.Topology(**topology_data_after) if topology_data_after is not None else None,
        dns_data.load_state(serialized_state),
    )


@pytest.mark.parametrize(
    "integration_datasets, topology_data",
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
            tests.unit.helpers.TOPOLOGIES["3_units_current_not_active"],
        ),
        (
            [
                [
                    tests.unit.helpers.RECORDS["admin.dns.test_42"],
                ],
            ],
            None,
        ),
        (
            [
                [],
            ],
            None,
        ),
    ),
)
def test_load_dump_state(integration_datasets, topology_data):
    """
    arrange: prepare some integration datasets and network topology
    act: create state
    assert: it should be intact after dumpig/reloading
    """
    record_requirers_data = tests.unit.helpers.dns_record_requirers_data_from_integration_datasets(
        integration_datasets
    )
    zones = dns_data.dns_record_relations_data_to_zones(  # pylint: disable=protected-access
        [(record_requirer_data, None) for record_requirer_data in record_requirers_data]
    )
    topology = models.Topology(**topology_data) if topology_data is not None else None

    serialized = dns_data.dump_state(zones, topology)
    state = dns_data.load_state(serialized)

    assert state == {"zones": zones, "topology": topology}
