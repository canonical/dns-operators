#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-locals

import logging
import time
from dataclasses import dataclass

import dns.exception
import dns.resolver
import jubilant
import pytest
import pytest_asyncio

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="module", name="full_deployment")
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
    apps = juju.status().apps
    if "dns-record" not in apps[dns_integrator_name].relations:
        juju.integrate(f"{dns_integrator_name}:dns-record", bind_name)
    if "dns-transfer" not in apps[dns_secondary_name].relations:
        juju.integrate(f"{dns_secondary_name}:dns-transfer", bind_name)
    if "dns-authority" not in apps[dns_resolver_name].relations:
        juju.integrate(f"{dns_resolver_name}:dns-authority", dns_secondary_name)
    juju.wait(
        lambda status: jubilant.all_active(
            status,
            bind_name,
            dns_resolver_name,
            dns_secondary_name,
        )
    )


@dataclass
class DnsEntry:
    """Container for the test inputs."""

    domain: str
    host_label: str
    ttl: int
    record_class: str
    record_type: str
    record_data: str


def _resolve_expected_record(ip: str, entry: DnsEntry) -> None:
    """Resolve a record and retry while changes propagate to all servers."""
    fqdn = f"{entry.host_label}.{entry.domain}"
    logger.info("%s", fqdn)
    last_error: dns.exception.DNSException | None = None
    for _ in range(24):
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [ip]
        try:
            answers = resolver.resolve(fqdn, entry.record_type)
            answer_texts = [answer.to_text() for answer in answers]
        except dns.exception.DNSException as exc:
            last_error = exc
        else:
            logger.info("%s", answer_texts)
            if str(entry.record_data) in answer_texts:
                return
        time.sleep(5)
    if last_error is not None:
        raise last_error
    pytest.fail(f"Could not resolve {fqdn} as {entry.record_type} from nameserver {ip}")


@pytest.mark.parametrize(
    "integration_datasets",
    (
        (
            (
                [
                    DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                    DnsEntry(
                        domain="dns.test",
                        host_label="admin2",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.43",
                    ),
                    DnsEntry(
                        domain="dns2.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.44.44",
                    ),
                ],
            ),
        ),
        (
            (
                [
                    DnsEntry(
                        domain="dns.test",
                        host_label="admin",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="42.42.42.42",
                    ),
                ],
                [
                    DnsEntry(
                        domain="dns-app-2.test",
                        host_label="somehost",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="41.41.41.41",
                    ),
                ],
                [
                    DnsEntry(
                        domain="dns-app-3.test",
                        host_label="somehost",
                        ttl=600,
                        record_class="IN",
                        record_type="A",
                        record_data="40.40.40.40",
                    ),
                ],
            ),
        ),
    ),
)
@pytest.mark.asyncio
@pytest.mark.abort_on_fail
async def test_active(
    juju: jubilant.Juju,
    bind_name: str,
    dns_integrator_name: str,
    dns_resolver_name: str,
    dns_secondary_name: str,
    full_deployment,  # pylint: disable=unused-argument
    integration_datasets: tuple[list[DnsEntry]],
):
    """
    arrange: build and deploy the charm.
    act: nothing.
    assert: that the charm ends up in an active state.
    """
    assert juju.status().apps[dns_resolver_name].is_active

    bind_units = juju.status().get_units(bind_name)
    bind_ip = bind_units[f"{bind_name}/0"].public_address
    dns_secondary_units = juju.status().get_units(dns_secondary_name)
    dns_secondary_ip = dns_secondary_units[f"{dns_secondary_name}/0"].public_address
    dns_resolver_units = juju.status().get_units(dns_resolver_name)
    dns_resolver_ip = dns_resolver_units[f"{dns_resolver_name}/0"].public_address

    integrator_config = ""
    for integration_data in integration_datasets:
        for entries in integration_data:
            if not isinstance(entries, list):
                entries_list = [entries]
            else:
                entries_list = entries
            for entry in entries_list:
                integrator_config += (
                    f"{entry.host_label} {entry.domain} {entry.ttl}"
                    f" {entry.record_class} {entry.record_type} {entry.record_data}\n"
                )

    juju.config(
        dns_integrator_name,
        {
            "requests": integrator_config,
        },
    )

    juju.wait(
        lambda status: (
            jubilant.all_active(
                status,
                bind_name,
                dns_resolver_name,
                dns_secondary_name,
            )
            and jubilant.all_agents_idle(
                status,
                bind_name,
                dns_resolver_name,
                dns_secondary_name,
                dns_integrator_name,
            )
        ),
        error=jubilant.any_error,
        successes=10,
    )

    # Check that bind and dns-resolver respond correctly
    for ip in [bind_ip, dns_resolver_ip, dns_secondary_ip]:
        for integration_data in integration_datasets:
            for entries in integration_data:
                if not isinstance(entries, list):
                    entries_list = [entries]
                else:
                    entries_list = entries
                for entry in entries_list:
                    _resolve_expected_record(ip, entry)
