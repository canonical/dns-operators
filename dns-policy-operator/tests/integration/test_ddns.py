#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests of the automatically allocated domains."""

# The tests of this module share a deployment and run in order, so they take a lot of
# fixtures and keep the state the previous ones left behind.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

import time

import jubilant
import pytest

from tests.integration.helpers import (
    published_ddns_domain,
    requirer_ingress_address,
    resolve,
    wait_for_ddns_domain,
)


@pytest.mark.abort_on_fail
def test_ddns_domain_is_allocated(
    juju: jubilant.Juju,
    dns_integrator_name: str,
    ddns_domain: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and set the ddns-domain configuration.
    act: integrate a requirer on the dns-record-provider endpoint.
    assert: the requirer is handed a domain under the configured suffix.
    """
    domain = wait_for_ddns_domain(juju, f"{dns_integrator_name}/0", published=True)

    assert domain is not None
    _, _, suffix = domain.partition(".")
    assert suffix == ddns_domain


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
    domain = published_ddns_domain(juju, f"{dns_integrator_name}/0")
    assert domain is not None
    address = requirer_ingress_address(juju, f"{dns_policy_name}/0", f"{dns_integrator_name}/0")
    bind_address = juju.status().get_units(bind_name)[f"{bind_name}/0"].public_address

    assert resolve(bind_address, domain) == [address]
    assert resolve(bind_address, f"anything.{domain}") == [address]


@pytest.mark.abort_on_fail
def test_ddns_domain_is_stable(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_integrator_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: reconfigure the charm.
    assert: the requirer keeps the domain it was allocated.
    """
    domain = published_ddns_domain(juju, f"{dns_integrator_name}/0")

    juju.config(dns_policy_name, {"debug": True})
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name),
        error=jubilant.any_error,
    )
    time.sleep(120)  # let the reconciliation timer tick a couple of times

    assert published_ddns_domain(juju, f"{dns_integrator_name}/0") == domain


@pytest.mark.abort_on_fail
@pytest.mark.parametrize("ddns_domain_config", ["not a domain"], indirect=True)
def test_invalid_ddns_domain_blocks_the_charm(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_integrator_name: str,
    ddns_domain: str,
    ddns_domain_config,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: set an invalid ddns-domain configuration.
    assert: the charm blocks and keeps the domain it already allocated.
    """
    domain = published_ddns_domain(juju, f"{dns_integrator_name}/0")
    assert domain is not None and domain.endswith(f".{ddns_domain}")

    juju.wait(lambda status: jubilant.all_blocked(status, dns_policy_name))
    time.sleep(120)  # let the reconciliation timer tick a couple of times

    assert published_ddns_domain(juju, f"{dns_integrator_name}/0") == domain


@pytest.mark.abort_on_fail
@pytest.mark.parametrize("ddns_domain_config", [""], indirect=True)
def test_ddns_domain_is_withdrawn(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_integrator_name: str,
    ddns_domain_config,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer be allocated a domain.
    act: unset the ddns-domain configuration.
    assert: the allocated domain is withdrawn from the requirer.
    """
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name),
        error=jubilant.any_error,
    )

    assert wait_for_ddns_domain(juju, f"{dns_integrator_name}/0", published=False) is None
