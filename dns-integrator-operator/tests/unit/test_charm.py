# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import json
import logging

import ops
import ops.testing
import pytest
import scenario

from src.charm import DnsIntegratorCharm

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("base_state")
def test_start_without_config_nor_integration(base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is peer not available
    """
    base_state["relations"] = []
    state = ops.testing.State(**base_state)

    context = ops.testing.Context(charm_type=DnsIntegratorCharm)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.BlockedStatus("Waiting for some configuration")


@pytest.mark.usefixtures("base_state")
def test_start_with_config_but_no_integration(base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is peer not available
    """
    base_state["relations"] = []
    base_state["config"] = {
        "requests": "foo example.com 600 A 1.2.3.4",
    }
    state = ops.testing.State(**base_state)

    context = ops.testing.Context(charm_type=DnsIntegratorCharm)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.BlockedStatus("Waiting for integration")


@pytest.mark.usefixtures("base_state")
def test_start_with_config_and_integration(base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is peer not available
    """
    base_state["relations"] = [
        scenario.Relation(
            endpoint="dns-record",
            interface="dns_record",
            remote_app_name="bind",
            local_unit_data={},
            remote_app_data={},
        )
    ]
    base_state["config"] = {
        "requests": "foo example.com 600 A 1.2.3.4",
    }
    state = ops.testing.State(**base_state)

    context = ops.testing.Context(charm_type=DnsIntegratorCharm)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.ActiveStatus()


@pytest.mark.usefixtures("base_state")
def test_config_changed_with_config_and_integration(base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is peer not available
    """
    base_state["relations"] = [
        scenario.Relation(
            endpoint="dns-record",
            interface="dns_record",
            remote_app_name="bind",
            local_unit_data={},
            remote_app_data={},
        )
    ]
    base_state["config"] = {
        "requests": "foo example.com 600 IN A 1.2.3.4",
    }
    base_state["leader"] = True
    state = ops.testing.State(**base_state)

    context = ops.testing.Context(charm_type=DnsIntegratorCharm)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.ActiveStatus()
    for relation in out.relations:
        if relation.endpoint == "dns-record":
            # Mypy doesn't seem to fully understand `RawDataBagContents?`
            requests_data = json.loads(relation.local_app_data.get("dns_entries"))  # type: ignore
            for request in requests_data:
                assert request["host_label"] == "foo"


@pytest.mark.usefixtures("base_state")
def test_config_changed_with_multiple_integrations(base_state):
    """
    arrange: prepare a state with three dns-record integrations
    act: run config-changed
    assert: the requests are published in the databag of every relation
    """
    relations = [
        scenario.Relation(
            endpoint="dns-record",
            interface="dns_record",
            remote_app_name=f"bind-{index}",
            local_unit_data={},
            remote_app_data={},
        )
        for index in range(3)
    ]
    base_state["relations"] = relations
    base_state["config"] = {
        "requests": "foo example.com 600 IN A 1.2.3.4",
    }
    base_state["leader"] = True
    state = ops.testing.State(**base_state)

    context = ops.testing.Context(charm_type=DnsIntegratorCharm)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.ActiveStatus()
    for relation in relations:
        # Mypy doesn't seem to fully understand `RawDataBagContents?`
        requests_data = json.loads(
            out.get_relation(relation.id).local_app_data.get("dns_entries")  # type: ignore
        )
        assert [request["host_label"] for request in requests_data] == ["foo"]
