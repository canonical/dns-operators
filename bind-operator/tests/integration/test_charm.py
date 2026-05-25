#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
import time

import dns.resolver
import jubilant
import pytest

import constants
import models
import tests.integration.helpers

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_lifecycle(app: str, juju: jubilant.Juju):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    units = juju.status().get_units(app)
    unit_name = list(units.keys())[0]
    unit_status = units[unit_name]

    assert unit_status.workload_status.current == "active"

    status = await tests.integration.helpers.dig_query(
        juju,
        unit_name,
        f"@127.0.0.1 status.{constants.ZONE_SERVICE_NAME} TXT +short",
        retry=True,
        wait=5,
    )
    assert status == '"ok"'

    await tests.integration.helpers.dispatch_to_unit(juju, unit_name, "stop")
    time.sleep(5)

    service_status = juju.exec("snap services charmed-bind", unit=unit_name).stdout
    logger.info(service_status)
    assert "inactive" in service_status

    # Wait a bit and retest the status.
    # This is done to make sure that bind-reload doesn't restart the service
    time.sleep(70)
    logger.info(service_status)
    assert "inactive" in service_status

    await tests.integration.helpers.dispatch_to_unit(juju, unit_name, "start")
    time.sleep(5)

    service_status = juju.exec("snap services charmed-bind", unit=unit_name).stdout
    logger.info(service_status)
    assert "active" in service_status


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_basic_dns_config(app: str, juju: jubilant.Juju):
    """
    arrange: build, deploy the charm and change its configuration.
    act: request the test domain.
    assert: the output of the dig command is the expected one
    """
    units = juju.status().get_units(app)
    unit_name = list(units.keys())[0]

    test_zone_def = f"""zone "dns.test" IN {{
    type primary;
    file "{constants.DNS_CONFIG_DIR}/db.dns.test";
    allow-update {{ none; }};
}};
    """
    # We need to stop the dispatch-reload-bind timer for this test
    stop_timer_cmd = "sudo systemctl stop dispatch-reload-bind.timer"
    await tests.integration.helpers.run_on_unit(juju, unit_name, stop_timer_cmd)

    await tests.integration.helpers.push_to_unit(
        juju=juju,
        unit_name=unit_name,
        source=test_zone_def,
        destination=f"{constants.DNS_CONFIG_DIR}/named.conf.local",
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
        juju=juju,
        unit_name=unit_name,
        source=test_zone,
        destination=f"{constants.DNS_CONFIG_DIR}/db.dns.test",
    )

    restart_cmd = f"sudo snap restart --reload {constants.DNS_SNAP_NAME}"
    await tests.integration.helpers.run_on_unit(juju, unit_name, restart_cmd)

    assert (
        await tests.integration.helpers.run_on_unit(
            juju, unit_name, "dig @127.0.0.1 dns.test TXT +short"
        )
    ).strip() == '"this-is-a-test"'

    # Restart the timer for the subsequent tests
    start_timer_cmd = "sudo systemctl start dispatch-reload-bind.timer"
    await tests.integration.helpers.run_on_unit(juju, unit_name, start_timer_cmd)


@pytest.mark.parametrize(
    "integration_datasets, status",
    (
        (
            (
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin2",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.43",
                    ),
                    models.DnsEntry(
                        domain="dns2.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.44.44",
                    ),
                ],
            ),
            "active",
        ),
        (
            (
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
                [
                    models.DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="41.41.41.41",
                    ),
                ],
            ),
            "blocked",
        ),
        (
            (
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
                [
                    models.DnsEntry(
                        domain="dns-app-2.test",
                        host_label="somehost",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="41.41.41.41",
                    ),
                ],
                [
                    models.DnsEntry(
                        domain="dns-app-3.test",
                        host_label="somehost",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="40.40.40.40",
                    ),
                ],
            ),
            "active",
        ),
    ),
)
@pytest.mark.asyncio
@pytest.mark.abort_on_fail
# pylint: disable=too-many-locals
async def test_dns_record_relation(
    app: str,
    juju: jubilant.Juju,
    status: str,
    integration_datasets: tuple[list[models.DnsEntry]],
):
    """
    arrange: given deployed bind-operator
    act: integrate any-charm instances to the deployed app
    assert: bind-operator should have the correct status and respond to dig queries
    """
    # Remove previously deployed instances of any-app
    apps = juju.status().apps
    for any_app_number in range(5):
        anyapp_name = f"anyapp-t{any_app_number}"
        if anyapp_name in apps:
            juju.remove_application(anyapp_name)
            juju.wait(jubilant.all_agents_idle)

    # Start by deploying the any-app instances and integrate them with the bind charm
    any_app_number = 0
    for integration_data in integration_datasets:
        anyapp_name = f"anyapp-t{any_app_number}"
        await tests.integration.helpers.generate_anycharm_relation(
            app,
            juju,
            anyapp_name,
            integration_data,
            None,
        )
        any_app_number += 1

    juju.wait(jubilant.all_agents_idle, timeout=30)

    units = juju.status().get_units(app)
    unit_name = list(units.keys())[0]
    await tests.integration.helpers.force_reload_bind(juju, unit_name)
    juju.wait(jubilant.all_agents_idle, timeout=30)

    # Test the status of the bind-operator instance
    unit_status = juju.status().get_units(app)[unit_name]
    assert unit_status.workload_status.current == status

    # Test if the records give the correct results
    # Do that only if we have an active status
    if status == "active":
        for integration_data in integration_datasets:
            for entry in integration_data:
                ips = await tests.integration.helpers.get_unit_ips(juju, app)
                logger.info(ips)
                for ip in ips:
                    # Create a DNS resolver
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [ip]

                    # Perform the DNS query
                    logger.info("%s", f"{entry.host_label}.{entry.domain}")
                    answers = resolver.resolve(
                        f"{entry.host_label}.{entry.domain}", entry.record_type
                    )
                    logger.info("%s", [answer.to_text() for answer in answers])
                    assert str(entry.record_data) in [answer.to_text() for answer in answers]
