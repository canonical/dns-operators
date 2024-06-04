#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
import time
import typing

import ops
import pytest
from pytest_operator.plugin import OpsTest

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
    "any_charm_name, relation_data",
    (
        (
            "any-app",
            [
                tests.integration.helpers.DnsEntry(
                    domain="dns.test",
                    host_label="admin",
                    ttl=600,
                    record_class="IN",
                    record_type="A",
                    record_data="42.42.42.42",
                )
            ],
        ),
    ),
)
@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_basic_relation(
    app: ops.model.Application,
    ops_test: OpsTest,
    any_charm_name: str,
    relation_data: typing.List[tests.integration.helpers.DnsEntry],
):
    """
    arrange: given deployed app, deploy any-charm that can relate to it
    act: relate any-charm to the deployed app
    assert: after waiting a bit, we should be able to query bind for the test record
    """
    await tests.integration.helpers.generate_anycharm_relation(
        app,
        ops_test,
        any_charm_name,
        relation_data,
    )

    assert (
        await tests.integration.helpers.run_on_unit(
            ops_test, f"{app.name}/{0}", "dig @127.0.0.1 admin.dns.test A +short"
        )
    ).strip() == "42.42.42.42"
