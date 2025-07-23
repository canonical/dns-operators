# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for the dns secondary module using testing."""

import pytest


@pytest.fixture(scope="function", name="base_state")
def base_state_fixture():
    """State with machine and config file set."""
    yield {
        "leader": True,
    }
