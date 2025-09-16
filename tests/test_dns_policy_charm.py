#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

import logging

import jubilant
import ops
import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="module", name="full_deployment")
async def full_deployment_fixture(
    juju: jubilant.Juju,
    bind_name: str,
    dns_policy_name: str,
    postgresql_name: str,
    bind,  # pylint: disable=unused-argument
    dns_resolver,  # pylint: disable=unused-argument
    postgresql,  # pylint: disable=unused-argument
):
    """Add necessary integration for the deployed charms."""
    juju.integrate(dns_policy_name, postgresql_name)
    juju.integrate(dns_policy_name, bind_name)
    juju.wait(lambda status: jubilant.all_active(status, dns_policy_name))


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_active(
    full_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    unit = full_deployment["dns-policy"].units[0]
    assert unit.workload_status == ops.model.ActiveStatus.name
