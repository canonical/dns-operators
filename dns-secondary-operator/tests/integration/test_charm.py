#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import jubilant
import pytest


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_integration_primary(juju: jubilant.Juju, app, primary):
    """
    arrange: build and deploy the charm. Also, deploy a primary charm.
    act: relate both.
    assert: charm is in active status.
    """
    juju.integrate(f"{app}:dns-transfer", primary)

    juju.wait(jubilant.all_active, timeout=300)
