# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging

import ops
import ops.testing
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start(context, base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is waiting
    """
    base_state["relations"] = []
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.WaitingStatus("Waiting for a database integration.")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
def test_start_with_database(context, base_state, database_relation):
    """
    arrange: prepare some state
    act: run start
    assert: status is active
    """
    base_state["relations"] = [database_relation]
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.ActiveStatus("")
