#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_active(juju: jubilant.Juju, dns_policy_name: str, full_deployment):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    assert juju.status().apps[dns_policy_name].is_active
