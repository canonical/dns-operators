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


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.parametrize(
    "config, expected_status",
    (
        (
            {},
            ops.ActiveStatus(""),
        ),
        (
            {"log-level": "debug"},
            ops.ActiveStatus(""),
        ),
        (
            {"log-level": "invalid-log-level"},
            ops.BlockedStatus("invalid log level: 'invalid-log-level'"),
        ),
    ),
)
def test_config(context, base_state, database_relation, config, expected_status):
    """
    arrange: prepare some state
    act: run on_config_changed
    assert: status is expected_status
    """
    base_state["relations"] = [database_relation]
    base_state["config"] = config
    state = ops.testing.State(**base_state)

    out = context.run(context.on.config_changed(), state)
    assert out.unit_status == expected_status
