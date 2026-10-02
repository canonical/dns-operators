# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import logging
import pathlib
from unittest.mock import patch

import ops
import pytest
from ops import testing

import constants
from src.charm import BindCharm

logger = logging.getLogger(__name__)


@pytest.fixture(name="context")
def context_fixture(tmp_path_factory):
    """Context fixture.

    Args:
        tmp_path_factory: pytest tmp_path_factory fixture
    """
    bind_operator_test_dir = tmp_path_factory.mktemp("bind_operator_test_dir")

    def _mock_write_file(path: pathlib.Path, content: str):
        """Mock the write_file function.

        Args:
            path: path of the file
            content: content of the file
        """
        new_path = pathlib.Path(bind_operator_test_dir / path.relative_to(path.anchor))
        new_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.write_text(
            content,
            encoding="utf-8",
        )

    with (
        patch("bind.BindService.reload"),
        patch("bind.BindService.setup"),
        patch("bind.BindService.start"),
        patch("bind.BindService.stop"),
        patch("bind.BindService._write_file") as mock_write_file,
    ):
        mock_write_file.side_effect = _mock_write_file
        yield ops.testing.Context(
            charm_type=BindCharm,
        )


@pytest.fixture(name="peer_relation")
def peer_relation_fixture():
    """Peer relation fixture."""
    yield testing.PeerRelation(
        endpoint=constants.PEER,
        # We need to pass a bogus unit id here.
        # This is because the remote_units_ids are inferred from the keys of the data.
        # Without any, the inconsistency checker is going to complain.
        peers_data={1: {}},
    )


@pytest.fixture(name="base_state")
def base_state_fixture(peer_relation):
    """Base state fixture.

    Args:
        peer_relation: peer relation fixture
    """
    input_state = {
        "relations": [peer_relation],
    }
    yield input_state
