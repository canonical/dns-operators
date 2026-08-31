#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests of the automatically allocated domains."""

# The tests of this module share a deployment and run in order, so they take a lot of
# fixtures and keep the state the previous ones left behind.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

import json
import logging
import time
import typing

import dns.exception
import dns.resolver
import jubilant
import pytest

logger = logging.getLogger(__name__)

DDNS_DOMAIN = "ddns.test"
INTEGRATOR_REQUEST = "admin dns.test 600 IN A 42.42.42.42"


def _relation_info(juju: jubilant.Juju, unit: str, endpoint: str) -> dict[str, typing.Any]:
    """Get the relation information of an endpoint of a unit.

    Args:
        juju: the juju client
        unit: the unit to get the relation information of
        endpoint: the endpoint of the relation

    Returns:
        the relation information juju reports for that endpoint
    """
    unit_info = json.loads(juju.cli("show-unit", unit, "--format", "json"))[unit]
    for relation_info in unit_info.get("relation-info", []):
        if relation_info.get("endpoint") == endpoint:
            return relation_info
    return {}


def _published_ddns_domain(juju: jubilant.Juju, dns_policy_unit: str) -> str | None:
    """Get the domain the dns-policy charm published to its requirer.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to read the relation data of

    Returns:
        the automatically allocated domain, or None when none was published
    """
    relation_info = _relation_info(juju, dns_policy_unit, "dns-record-provider")
    domain = relation_info.get("application-data", {}).get("ddns-domain")
    return json.loads(domain) if domain else None


def _requirer_ingress_address(
    juju: jubilant.Juju, dns_policy_unit: str, requirer_unit: str
) -> str:
    """Get the ingress address juju set for a requirer unit.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to read the relation data of
        requirer_unit: the requirer unit to get the ingress address of

    Returns:
        the ingress address of the requirer unit
    """
    relation_info = _relation_info(juju, dns_policy_unit, "dns-record-provider")
    related_units = relation_info.get("related-units", {})
    return related_units[requirer_unit]["data"]["ingress-address"]


def _wait_for_ddns_domain(
    juju: jubilant.Juju, dns_policy_unit: str, published: bool
) -> str | None:
    """Wait for the dns-policy charm to publish, or withdraw, an allocated domain.

    The charm allocates the domains on a timer, so this polls for a couple of ticks.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to read the relation data of
        published: whether to wait for a domain to appear or to disappear

    Returns:
        the automatically allocated domain, or None when none is published
    """
    for _ in range(30):
        domain = _published_ddns_domain(juju, dns_policy_unit)
        if (domain is not None) == published:
            return domain
        time.sleep(10)
    state = "published" if published else "withdrawn"
    pytest.fail(f"The allocated domain of {dns_policy_unit} was not {state}")
    return None


def _resolve(nameserver: str, name: str) -> list[str]:
    """Resolve the A records of a name, retrying while the changes propagate.

    Args:
        nameserver: the address of the nameserver to query
        name: the name to resolve

    Returns:
        the record data of the answers
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    for _ in range(30):
        try:
            answers = resolver.resolve(name, "A")
        except dns.exception.DNSException as exc:
            logger.info("Could not resolve %s yet: %s", name, exc)
        else:
            return [answer.to_text() for answer in answers]
        time.sleep(10)
    pytest.fail(f"Could not resolve {name} from the nameserver {nameserver}")
    return []


def _workload_supports_ddns(juju: jubilant.Juju, dns_policy_unit: str) -> bool:
    """Tell whether the deployed workload exposes the ddns allocation API.

    The charm installs its workload from the snap store, so a charm change reaches the
    integration tests before the workload change it relies on does.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to probe

    Returns:
        whether the workload knows the ddns allocation endpoint
    """
    status_code = juju.ssh(
        dns_policy_unit,
        "curl --silent --output /dev/null --write-out '%{http_code}' "
        "http://localhost:8080/api/ddns/allocations/",
    ).strip()
    logger.info("The ddns allocation endpoint answered with %s", status_code)
    return status_code != "404"


@pytest.fixture(scope="module", name="ddns_deployment")
def ddns_deployment_fixture(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_integrator_name: str,
    full_deployment,  # pylint: disable=unused-argument
    dns_integrator,  # pylint: disable=unused-argument
):
    """Integrate a requirer with the dns-policy charm and enable the ddns feature."""
    if not _workload_supports_ddns(juju, f"{dns_policy_name}/0"):
        pytest.skip("The charmed-dns-policy snap has no ddns allocation API yet")
    juju.config(dns_integrator_name, {"requests": INTEGRATOR_REQUEST})
    juju.config(dns_policy_name, {"ddns-domain": DDNS_DOMAIN})
    juju.integrate(f"{dns_integrator_name}:dns-record", f"{dns_policy_name}:dns-record-provider")
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name, dns_integrator_name),
        error=jubilant.any_error,
        timeout=600,
    )
    yield dns_integrator_name


@pytest.mark.abort_on_fail
def test_ddns_domain_is_allocated(
    juju: jubilant.Juju,
    dns_policy_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and set the ddns-domain configuration.
    act: integrate a requirer on the dns-record-provider endpoint.
    assert: the requirer is handed a domain under the configured suffix.
    """
    domain = _wait_for_ddns_domain(juju, f"{dns_policy_name}/0", published=True)

    assert domain is not None
    _, _, suffix = domain.partition(".")
    assert suffix == DDNS_DOMAIN


@pytest.mark.abort_on_fail
def test_ddns_domain_is_resolvable(
    juju: jubilant.Juju,
    bind_name: str,
    dns_policy_name: str,
    dns_integrator_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: resolve that domain, and one of its subdomains, against the DNS provider.
    assert: both resolve to the address of the requirer.
    """
    domain = _published_ddns_domain(juju, f"{dns_policy_name}/0")
    assert domain is not None
    address = _requirer_ingress_address(juju, f"{dns_policy_name}/0", f"{dns_integrator_name}/0")
    bind_address = juju.status().get_units(bind_name)[f"{bind_name}/0"].public_address

    assert _resolve(bind_address, domain) == [address]
    assert _resolve(bind_address, f"anything.{domain}") == [address]


@pytest.mark.abort_on_fail
def test_ddns_domain_is_stable(
    juju: jubilant.Juju,
    dns_policy_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: reconfigure the charm.
    assert: the requirer keeps the domain it was allocated.
    """
    domain = _published_ddns_domain(juju, f"{dns_policy_name}/0")

    juju.config(dns_policy_name, {"debug": True})
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name),
        error=jubilant.any_error,
    )
    time.sleep(120)  # let the reconciliation timer tick a couple of times

    assert _published_ddns_domain(juju, f"{dns_policy_name}/0") == domain


@pytest.mark.abort_on_fail
def test_invalid_ddns_domain_blocks_the_charm(
    juju: jubilant.Juju,
    dns_policy_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: set an invalid ddns-domain configuration.
    assert: the charm blocks and keeps the domain it already allocated.
    """
    domain = _published_ddns_domain(juju, f"{dns_policy_name}/0")

    juju.config(dns_policy_name, {"ddns-domain": "not a domain"})
    juju.wait(lambda status: jubilant.all_blocked(status, dns_policy_name))
    time.sleep(120)  # let the reconciliation timer tick a couple of times

    assert _published_ddns_domain(juju, f"{dns_policy_name}/0") == domain


@pytest.mark.abort_on_fail
def test_ddns_domain_is_withdrawn(
    juju: jubilant.Juju,
    dns_policy_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: unset the ddns-domain configuration.
    assert: the allocated domain is withdrawn from the requirer.
    """
    juju.config(dns_policy_name, {"ddns-domain": ""})
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name),
        error=jubilant.any_error,
    )

    assert _wait_for_ddns_domain(juju, f"{dns_policy_name}/0", published=False) is None
