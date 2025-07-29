# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging

import ops
import pytest
import scenario
from ops import testing

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
    assert out.unit_status == ops.ActiveStatus()
