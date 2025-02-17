# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the bind module."""

import logging
import re

import pytest

from src.charm import DnsIntegratorCharm

# pylint: disable=protected-access

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "seed",
    [
        "canonical",
        "test-seed",
        "abcdefg",
        "123456",
        "--__--_-__-",
    ],
)
def test_uuid_format(mock_self, seed):
    """Test generated UUID matches v4 format."""
    uuid = DnsIntegratorCharm._uuidv4(mock_self, seed)
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    assert re.match(pattern, uuid), "UUID does not match v4 format"


def test_deterministic_output(mock_self):
    """Test same seed produces same UUID."""
    uuid1 = DnsIntegratorCharm._uuidv4(mock_self, "stable-seed")
    uuid2 = DnsIntegratorCharm._uuidv4(mock_self, "stable-seed")
    assert uuid1 == uuid2, "Same seed produced different UUIDs"


def test_unique_output(mock_self):
    """Test different seeds produce different UUIDs."""
    uuid1 = DnsIntegratorCharm._uuidv4(mock_self, "seed-1")
    uuid2 = DnsIntegratorCharm._uuidv4(mock_self, "seed-2")
    assert uuid1 != uuid2, "Different seeds produced same UUID"


@pytest.mark.parametrize(
    "seed",
    [
        "",  # Empty string
        " ",  # Whitespace
        "special!@#$%^&*()chars",
        "ñáéíóú",  # Unicode
        "a" * 1000,  # Long string
        42,  # Number (should be converted to string)
        None,  # Should error if passed, but test anyway
    ],
)
def test_edge_cases(mock_self, seed):
    """Test various edge cases for seed input."""
    if isinstance(seed, int):
        seed = str(seed)
    try:
        uuid = DnsIntegratorCharm._uuidv4(mock_self, seed)
        assert len(uuid) == 36, "Invalid UUID length"
    # Allowing all exceptions because we precisely want to test them
    # pylint: disable=broad-exception-caught
    except Exception as e:
        if seed is None:
            assert isinstance(e, TypeError), "Should raise error for None seed"
        else:
            pytest.fail(f"Unexpected error for seed '{seed}': {e}")
