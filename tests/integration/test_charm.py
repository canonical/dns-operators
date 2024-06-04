#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
import time
import typing

import ops
import pytest
from pytest_operator.plugin import Model, OpsTest

import constants
import tests.integration.helpers

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_lifecycle(app: ops.model.Application, ops_test: OpsTest):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    # Application actually does have units
    unit = app.units[0]  # type: ignore

    # Mypy has difficulty with ActiveStatus
    assert unit.workload_status == ops.model.ActiveStatus.name  # type: ignore

    await tests.integration.helpers.dispatch_to_unit(ops_test, unit, "stop")
    time.sleep(5)
    _, service_status, _ = await ops_test.juju(
        "exec", "--unit", unit.name, "snap services charmed-bind"
    )
    logger.info(service_status)
    assert "inactive" in service_status

    await tests.integration.helpers.dispatch_to_unit(ops_test, unit, "start")
    time.sleep(5)
    _, service_status, _ = await ops_test.juju(
        "exec", "--unit", unit.name, "snap services charmed-bind"
    )
    logger.info(service_status)
    assert "active" in service_status


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_basic_dns_config(app: ops.model.Application, ops_test: OpsTest):
    """
    arrange: build, deploy the charm and change its configuration.
    act: request the test domain.
    assert: the output of the dig command is the expected one
    """
    # Application actually does have units
    unit = app.units[0]  # type: ignore

    test_zone_def = f"""zone "dns.test" IN {{
    type primary;
    file "{constants.DNS_CONFIG_DIR}/db.dns.test";
    allow-update {{ none; }};
}};
    """
    await tests.integration.helpers.push_to_unit(
        ops_test, unit, test_zone_def, f"{constants.DNS_CONFIG_DIR}/named.conf.local"
    )

    test_zone = """$TTL    604800
@       IN      SOA     dns.test. admin.dns.test. (
                              1         ; Serial
                         604800         ; Refresh
                          86400         ; Retry
                        2419200         ; Expire
                         604800 )       ; Negative Cache TTL
;
@       IN      NS      localhost.
@       IN      A       127.0.0.1
@       IN      TXT     "this-is-a-test"
    """
    await tests.integration.helpers.push_to_unit(
        ops_test, unit, test_zone, f"{constants.DNS_CONFIG_DIR}/db.dns.test"
    )

    restart_cmd = f"sudo snap restart --reload {constants.DNS_SNAP_NAME}"
    await tests.integration.helpers.run_on_unit(ops_test, unit.name, restart_cmd)

    assert (
        await tests.integration.helpers.run_on_unit(
            ops_test, f"{app.name}/{0}", "dig @127.0.0.1 dns.test TXT +short"
        )
    ).strip() == '"this-is-a-test"'


@pytest.mark.parametrize(
    "integration_datasets, status",
    (
        (
            (
                [
                    tests.integration.helpers.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    tests.integration.helpers.DnsEntry(
                        domain="dns.test",
                        host_label="admin2",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.43",
                    ),
                    tests.integration.helpers.DnsEntry(
                        domain="dns2.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.44.44",
                    ),
                ],
            ),
            ops.model.ActiveStatus,
        ),
    ),
)
@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_basic_relation(
    app: ops.model.Application,
    ops_test: OpsTest,
    model: Model,
    status: ops.model.StatusBase,
    integration_datasets: typing.Tuple[typing.List[tests.integration.helpers.DnsEntry]],
):
    """
    arrange: given deployed bind-operator
    act: integrate any-charm instances to the deployed app
    assert: bind-operator should have the correct status and respond to dig queries
    """
    # Start by deploying the any-app instances and integrate them with the bind charm
    any_app_number = 0
    for integration_data in integration_datasets:
        await tests.integration.helpers.generate_anycharm_relation(
            app,
            ops_test,
            f"anyapp-t{any_app_number}",
            integration_data,
        )
        any_app_number += 1

    await model.wait_for_idle()

    # Test the status of the bind-operator instance
    # Application actually does have units
    unit = app.units[0]  # type: ignore
    assert unit.workload_status == status.name

    # Test if the records give the correct results
    # Do that only if we have an active status
    if status == ops.model.ActiveStatus:
        for integration_data in integration_datasets:
            for entry in integration_data:

                result = await tests.integration.helpers.dig_query(ops_test, app.name, entry)
                await model.wait_for_idle()

                assert result == entry["record_data"]
