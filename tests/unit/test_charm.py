# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging
from unittest.mock import patch

import ops
import pytest
import scenario
from scenario.context import _Event  # needed for custom events for now

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start_wo_peer_relation(context, base_state):
    base_state["relations"] = []
    state = ops.testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.testing.WaitingStatus("Peer relation is not available")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start(context, base_state):
    state = ops.testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_stop(context, base_state):
    state = ops.testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_install(context, base_state):
    state = ops.testing.State(**base_state)
    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_config_changed(context, base_state):
    state = ops.testing.State(**base_state)
    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_leader_elected_changed_while_leader_no_active_unit(context, base_state):
    base_state["leader"] = True
    state = ops.testing.State(**base_state)
    out = context.run(context.on.leader_elected(), state)
    assert out.unit_status == ops.testing.ActiveStatus("active")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_leader_elected_changed_while_leader_not_active_dig_timeout(context, base_state):
    base_state["leader"] = True
    databag = {"active-unit": "1.2.99.4"}
    peer_relation = scenario.PeerRelation(
        endpoint="bind-peers",
        local_app_data=databag,
    )
    base_state["relations"][0] = peer_relation
    with patch("src.charm.BindCharm._dig_query") as dig_query:
        dig_query.return_value = ""
        state = ops.testing.State(**base_state)
        out = context.run(context.on.leader_elected(), state)
        assert out.unit_status == ops.testing.ActiveStatus("active")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_leader_elected_changed_while_leader_not_active_dig_ok(context, base_state):
    base_state["leader"] = True
    databag = {"active-unit": "1.2.99.4"}
    peer_relation = scenario.PeerRelation(
        endpoint="bind-peers",
        local_app_data=databag,
    )
    base_state["relations"][0] = peer_relation
    with patch("src.charm.BindCharm._dig_query") as dig_query:
        dig_query.return_value = "ok"
        state = ops.testing.State(**base_state)
        out = context.run(context.on.leader_elected(), state)
        assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_leader_elected_changed_while_not_leader(context, base_state):
    base_state["leader"] = False
    state = ops.testing.State(**base_state)
    out = context.run(context.on.leader_elected(), state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("peer_relation")
def test_peer_relation_departed_while_leader(context, base_state, peer_relation):
    base_state["leader"] = True
    state = ops.testing.State(**base_state)
    peer_relation_departed_event = _Event(
        f"{peer_relation.endpoint}_relation_departed", relation=peer_relation
    )
    out = context.run(peer_relation_departed_event, state)
    assert out.unit_status == ops.testing.ActiveStatus("active")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("peer_relation")
def test_peer_relation_departed_while_not_leader(context, base_state, peer_relation):
    base_state["leader"] = False
    state = ops.testing.State(**base_state)
    peer_relation_departed_event = _Event(
        f"{peer_relation.endpoint}_relation_departed", relation=peer_relation
    )
    out = context.run(peer_relation_departed_event, state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("peer_relation")
def test_peer_relation_joined(context, base_state, peer_relation):
    state = ops.testing.State(**base_state)
    peer_relation_joined_event = _Event(
        f"{peer_relation.endpoint}_relation_joined", relation=peer_relation
    )
    out = context.run(peer_relation_joined_event, state)
    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_reload_bind(context, base_state):
    state = ops.testing.State(**base_state)
    reload_bind_event = _Event("reload_bind")
    out = context.run(reload_bind_event, state)
    assert out.unit_status == ops.testing.ActiveStatus()
