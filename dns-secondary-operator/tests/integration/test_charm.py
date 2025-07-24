#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import ops
import pytest

from charm import STATUS_REQUIRED_INTEGRATION

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_deploy(model, charm_file, app_name, resources):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: charm is in blocked status.
    """
    application = await model.deploy(
        f"{charm_file}", application_name=app_name, resources=resources
    )
    await model.wait_for_idle(apps=[application.name], timeout=300, status="blocked")

    assert application.units[0].workload_status == ops.model.BlockedStatus.name
    status = await model.get_status()
    assert status.applications[app_name]["status"]["info"] == STATUS_REQUIRED_INTEGRATION
