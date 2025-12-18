#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for multiple units."""

import logging

import jubilant
import pytest

import models
import tests.integration.helpers

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_multi_units(
    app: str,
    juju: jubilant.Juju,
):
    """
    arrange: given deployed bind-operator
    act: change the number of units
    assert: there always is an active unit
    """
    # Remove previously deployed instances of any-app
    apps = juju.status().apps
    for any_app_number in range(10):
        anyapp_name = f"anyapp-t{any_app_number}"
        if anyapp_name in apps:
            juju.remove_application(anyapp_name)
            juju.wait(jubilant.all_agents_idle)

    # Start by deploying the any-app instance with the domain to check
    await tests.integration.helpers.generate_anycharm_relation(
        app,
        juju,
        "anyapp-t1",
        [
            models.DnsEntry(
                domain="dns.test",
                host_label="admin",
                ttl=5,
                record_class="IN",
                record_type="A",
                record_data="42.42.42.42",
            ),
        ],
        None,
    )
    juju.wait(jubilant.all_agents_idle)

    # Start by testing that everything is fine
    assert await tests.integration.helpers.check_if_active_unit_exists(app, juju)
    units = juju.status().get_units(app)
    for unit_name in units.keys():
        await tests.integration.helpers.force_reload_bind(juju, unit_name)
        juju.wait(jubilant.all_agents_idle)
        assert (
            await tests.integration.helpers.dig_query(
                juju,
                unit_name,
                "@127.0.0.1 admin.dns.test A +short",
                retry=True,
                wait=5,
            )
            == "42.42.42.42"
        ), "Initial test failed"

    # add a unit and verify that everything goes well
    juju.add_unit(app)
    juju.wait(jubilant.all_agents_idle)
    assert await tests.integration.helpers.check_if_active_unit_exists(app, juju)
    units = juju.status().get_units(app)
    for unit_name in units.keys():
        await tests.integration.helpers.force_reload_bind(juju, unit_name)
        juju.wait(jubilant.all_agents_idle)
        assert (
            await tests.integration.helpers.dig_query(
                juju,
                unit_name,
                "@127.0.0.1 admin.dns.test A +short",
                retry=True,
                wait=5,
            )
            == "42.42.42.42"
        ), "Failed after adding one unit"

    # Change the domain requested by any-app
    anyapp_name = "anyapp-t1"
    anyapp_units = juju.status().get_units(anyapp_name)
    anyapp_unit_name = list(anyapp_units.keys())[0]
    await tests.integration.helpers.change_anycharm_relation(
        juju,
        anyapp_unit_name,
        [
            models.DnsEntry(
                domain="dns.test",
                host_label="admin",
                ttl=5,
                record_class="IN",
                record_type="A",
                record_data="43.43.43.43",
            ),
        ],
    )
    juju.wait(jubilant.all_agents_idle)
    units = juju.status().get_units(app)
    for unit_name in units.keys():
        await tests.integration.helpers.force_reload_bind(juju, unit_name)
        juju.wait(jubilant.all_agents_idle)
        assert (
            await tests.integration.helpers.dig_query(
                juju,
                unit_name,
                "@127.0.0.1 admin.dns.test A +short",
                retry=True,
                wait=5,
            )
            == "43.43.43.43"
        ), "Failed after changing DNS request"

    # remove the active unit and check that we're still all right
    active_unit_name = await tests.integration.helpers.get_active_unit(app, juju)
    assert active_unit_name is not None
    juju.remove_unit(active_unit_name, force=True)
    juju.wait(jubilant.all_agents_idle)
    assert await tests.integration.helpers.check_if_active_unit_exists(app, juju)
    units = juju.status().get_units(app)
    for unit_name in units.keys():
        await tests.integration.helpers.force_reload_bind(juju, unit_name)
        juju.wait(jubilant.all_agents_idle)
        assert (
            await tests.integration.helpers.dig_query(
                juju,
                unit_name,
                "@127.0.0.1 admin.dns.test A +short",
                retry=True,
                wait=5,
            )
            == "43.43.43.43"
        ), "Failed after removing one bind unit"
