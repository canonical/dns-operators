#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="module", name="full_deployment")
@pytest.mark.usefixtures(
    "juju", "bind_name", "dns_resolver_name", "bind", "dns_resolver"
)
async def full_deployment_fixture(
    juju: jubilant.Juju,
    bind_name: str,
    dns_resolver_name: str,
    dns_secondary_name: str,
    dns_integrator_name: str,
    bind,  # pylint: disable=unused-argument
    dns_integrator,  # pylint: disable=unused-argument
    dns_resolver,  # pylint: disable=unused-argument
    dns_secondary,  # pylint: disable=unused-argument
):
    """Add necessary integration and configuration for the deployed charms."""
    juju.config(dns_integrator_name, {
        "requests": "canonical juju.test 600 IN A 0.1.2.3"
    })
    juju.integrate(dns_integrator_name, bind_name)
    juju.integrate(dns_resolver_name, bind_name)
    juju.integrate(dns_secondary_name, bind_name)
    juju.wait(lambda status: jubilant.all_active(status,
        bind_name,
        dns_integrator_name,
        dns_resolver_name,
        dns_secondary_name,
    ))


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_active(
    juju: jubilant.Juju,
    dns_resolver_name: str,
    full_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    assert juju.status().apps[dns_resolver_name].is_active
