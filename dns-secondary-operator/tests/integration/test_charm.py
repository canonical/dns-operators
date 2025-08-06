#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import jubilant
import pytest


@pytest.fixture(scope="module", name="juju")
def juju_fixture():
    """Juju fixture"""
    with jubilant.temp_model() as juju:
        yield juju


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_deploy(juju: jubilant.Juju, charm_file, app_name, resources):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: charm is in blocked status.
    """
    juju.deploy(charm=charm_file, app=app_name, resources=resources)
    juju.wait(jubilant.all_agents_idle, timeout=600)
    juju.wait(jubilant.all_blocked)
