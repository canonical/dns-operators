#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

# Ignore too many args warning. I NEED THEM OKAY ?!
# pylint: disable=too-many-arguments

import asyncio
import logging
import time

import jubilant
import pytest

import models
import tests.integration.helpers

logger = logging.getLogger(__name__)


async def deploy_any_charm(
    *,
    app_name: str,
    juju: jubilant.Juju,
    any_app_number: int,
    machines: list[str] | None,
    entries: list[models.DnsEntry],
):
    """Deploy any charm and integrate it to the bind-operator.

    Args:
        app_name: Deployed bind-operator app name
        juju: The jubilant Juju instance
        any_app_number: Number of the to be deployed any-charm
        machines: The machines to deploy the any-charm onto
        entries: List of DNS entries for any-charm
    """
    anyapp_name = f"anyapp-t{any_app_number}"
    if machines is not None:
        machine = machines[any_app_number % len(machines)]
    else:
        machine = None
    logger.info("Deploying %s on %s", anyapp_name, machine)
    apps = juju.status().apps
    if anyapp_name in apps:
        return
    await tests.integration.helpers.generate_anycharm_relation(
        app_name,
        juju,
        anyapp_name,
        entries,
        machine=machine,
    )


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
@pytest.mark.skip(reason="Scaling test")
async def test_lots_of_applications(
    app: str,
    juju: jubilant.Juju,
):
    """
    arrange: build and deploy the charm.
    act: deploy a lot of applications and integrate them to the bind operator
    assert:
    """
    batch_number = 10
    machines_number = 20
    status = juju.status()
    machines_available = (
        sum(1 for machine in status.machines.values() if machine.juju_status.current == "running")
        - 1
    )
    while machines_available < machines_number:
        juju.cli("add-machine")
        status = juju.status()
        machines_available = (
            sum(
                1
                for machine in status.machines.values()
                if machine.juju_status.current == "running"
            )
            - 1
        )
        print("Available machines:", machines_available)
        time.sleep(10)

    for i in range(int(2000 / batch_number)):

        status = juju.status()
        # we collect the machines but leave out machine "0"
        # that should be in use by the bind-operator
        machines = [x for x in status.machines.keys() if x != "0"]
        print("Available machines:", machines)

        await asyncio.gather(
            *[
                deploy_any_charm(
                    app_name=app,
                    juju=juju,
                    any_app_number=i * batch_number + x,
                    machines=machines,
                    entries=[
                        models.DnsEntry(
                            domain="dns.test",
                            host_label=f"admin{i * batch_number + x}",
                            ttl=5,
                            record_class="IN",
                            record_type="A",
                            record_data=(
                                "1.1."
                                f"{int((i * batch_number + x) / 255) + 1}."
                                f"{(i * batch_number + x) % 255 + 1}"
                            ),
                        ),
                    ],
                )
                for x in range(batch_number)
            ]
        )


@pytest.mark.asyncio
@pytest.mark.abort_on_fail
@pytest.mark.skip(reason="Scaling test")
async def test_lots_of_record_requests(
    app: str,
    juju: jubilant.Juju,
):
    """
    arrange: build and deploy the charm.
    act: deploy a lot of applications and integrate them to the bind operator
    assert:
    """
    application_number = 10
    entries_per_application = 10000

    for any_app_number in range(application_number):

        entries = []

        for entry_number in range(entries_per_application):
            entries.append(
                models.DnsEntry(
                    domain="dns.test",
                    host_label=f"admin{any_app_number}-{entry_number}",
                    ttl=5,
                    record_class="IN",
                    record_type="A",
                    record_data=f"1.1.{int(entry_number / 255) + 1}.{entry_number % 255 + 1}",
                )
            )

        await deploy_any_charm(
            app_name=app,
            juju=juju,
            any_app_number=any_app_number,
            machines=None,
            entries=entries,
        )
