# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

from unittest.mock import patch

import ops
import pytest
import scenario

from src.charm import BindCharm


@pytest.fixture(name="context")
def context_fixture():
    with (
        patch("bind.BindService.start"),
        patch("bind.BindService.stop"),
    ):
        yield ops.testing.Context(
            charm_type=BindCharm,
        )


@pytest.fixture(name="peer_relation")
def peer_Relation_fixture():
    yield scenario.PeerRelation(
        endpoint="bind-peers",
        peers_data={},
    )


@pytest.fixture(name="base_state")
def base_state_fixture(peer_relation):
    input_state = {
        "resources": [
            ops.testing.Resource(
                name="charmed-bind-snap",
                path=None,
            ),
        ],
        "relations": [peer_relation],
    }
    yield input_state
