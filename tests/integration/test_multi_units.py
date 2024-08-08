#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for multiple units."""

import logging

import ops
import pytest
from pytest_operator.plugin import Model, OpsTest

import models
import tests.integration.helpers

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_multi_units(
    app: ops.model.Application,
    ops_test: OpsTest,
    model: Model,
):
    """
    arrange: given deployed bind-operator
    act: change the number of units
    assert: there always is an active unit
    """
    # Remove previously deployed instances of any-app
    for any_app_number in range(10):
        anyapp_name = f"anyapp-t{any_app_number}"
        if anyapp_name in model.applications:
            await model.remove_application(anyapp_name, block_until_done=True)

    # Start by deploying the any-app instance with the domain to check
    await tests.integration.helpers.generate_anycharm_relation(
        app,
        ops_test,
        "anyapp-t1",
        [
            models.DnsEntry(
                domain="dns.test",
                host_label="admin",
                ttl=600,
                record_class="IN",
                record_type="A",
                record_data="42.42.42.42",
            ),
        ],
    )
    await model.wait_for_idle()

    # Define the test that we're going to make multiple times
    async def assert_has_dns_record(unit: ops.model.Unit):
        """Test if the unit exposes the target DNS record.

        Args:
            unit: Unit to test
        """
        result = await tests.integration.helpers.dig_query(
            ops_test,
            unit,
            "@127.0.0.1 admin.dns.test A +short",
            retry=True,
            wait=5,
        )
        assert result == "42.42.42.42", f"Issue with {unit.name}"

    # Start by testing that everything is fine
    assert await tests.integration.helpers.check_if_active_unit_exists(app, ops_test)
    # Application actually does have units
    for unit in app.units:  # type: ignore
        await assert_has_dns_record(unit)

    # add a unit and verify that everything goes well
    assert ops_test.model is not None
    add_unit_cmd = f"add-unit {app.name} --model={ops_test.model.info.name}"
    await ops_test.juju(*(add_unit_cmd.split(" ")))
    await model.wait_for_idle()
    assert await tests.integration.helpers.check_if_active_unit_exists(app, ops_test)
    # Application actually does have units
    for unit in app.units:  # type: ignore
        await assert_has_dns_record(unit)

    # remove the active unit and check that we're still all right
    active_unit = await tests.integration.helpers.get_active_unit(app, ops_test)
    assert active_unit is not None
    remove_unit_cmd = (
        f"remove-unit {active_unit.name} --model={ops_test.model.info.name} --no-prompt"
    )
    await ops_test.juju(*(remove_unit_cmd.split(" ")))
    await model.wait_for_idle()
    assert await tests.integration.helpers.check_if_active_unit_exists(app, ops_test)
    # Application actually does have units
    for unit in app.units:  # type: ignore
        await assert_has_dns_record(unit)
