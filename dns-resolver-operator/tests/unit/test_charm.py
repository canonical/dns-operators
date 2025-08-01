# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import json
import logging
import pathlib

import ops
import pytest
import scenario
from ops import testing
from scenario.context import _Event  # needed for custom events for now

import constants

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start_without_relation(context, base_state):
    """
    arrange: prepare some state
    act: run event hook
    assert: status is correct
    """
    base_state["relations"] = []
    state = testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.BlockedStatus("Needs to be related with an authority charm")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start_with_relation_without_data(context, base_state):
    """
    arrange: prepare some state
    act: run event hook
    assert: status is correct
    """
    dns_authority_relation = scenario.Relation(
        endpoint="dns-authority",
        remote_app_data={},
    )
    base_state["relations"] = [dns_authority_relation]
    state = testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.WaitingStatus("DNS authority relation is not ready")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start_with_relation_with_empty_data(context, base_state):
    """
    arrange: prepare some state
    act: run event hook
    assert: status is correct
    """
    dns_authority_relation = scenario.Relation(
        endpoint="dns-authority",
        remote_app_data={"zones": "[]", "addresses": "[]"},
    )
    base_state["relations"] = [dns_authority_relation]
    state = testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.WaitingStatus("DNS authority relation is empty")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("write_dir")
def test_relaton_changed_with_relation_with_some_data(context, base_state, write_dir):
    """
    arrange: prepare some state
    act: run event hook
    assert: status is correct
    """
    zones = ["example.com"]
    addresses = ["1.2.3.4"]
    dns_authority_relation = scenario.Relation(
        endpoint="dns-authority",
        remote_app_data={
            "zones": json.dumps(zones),
            "addresses": json.dumps(addresses),
        },
    )
    base_state["relations"] = [dns_authority_relation]
    state = testing.State(**base_state)
    dns_authority_relation_changed_event = _Event(
        "dns_authority_relation_changed", relation=dns_authority_relation
    )
    out = context.run(dns_authority_relation_changed_event, state)
    assert out.unit_status == ops.ActiveStatus()
    conf_path = pathlib.Path(constants.DNS_CONFIG_DIR) / "named.conf.local"
    real_conf_path = pathlib.Path(write_dir / conf_path.relative_to(conf_path.anchor))
    assert real_conf_path.exists()
    content = real_conf_path.read_text(encoding="utf-8")
    for zone in zones:
        assert (
            f'zone "{zone}" {{ '
            f"type forward;forward only;forwarders {{ {";".join(addresses)}; }}; "
            f"}};" in content
        )
