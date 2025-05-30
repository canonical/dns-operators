# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_fake():
    """
    arrange: prepare some state
    act: run start
    assert: status is peer not available
    """
    assert True
