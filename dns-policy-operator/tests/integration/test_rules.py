#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests of the rules automatically approving the record requests."""

# The tests of this module share a deployment and run in order, so they take a lot of
# fixtures and keep the state the previous ones left behind.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments

import time

import jubilant
import pytest

from tests.integration.helpers import (
    is_resolvable,
    manage_shell,
    resolve,
    wait_for_ddns_domain,
    wait_unresolvable,
)

# Domain of the regular record requests, the allocated domains being under DDNS_DOMAIN
DOMAIN = "dns.test"
DDNS_DOMAIN = "ddns.test"
# The A record the dns-integrator charm is configured with by the ddns_deployment fixture
ADDRESS_REQUEST = f"admin {DOMAIN} 600 IN A 42.42.42.42"
OWNED_CHALLENGE = "owned-challenge"
UNOWNED_CHALLENGE = "unowned-challenge"
DDNS_CHALLENGE = "ddns-challenge"


def _set_rule(juju: jubilant.Juju, unit: str, domain: str, enabled: bool = True) -> None:
    """Create or update the ACME challenge rule of a domain.

    Saving the rule evaluates the rules again against every pending record request.

    Args:
        juju: the juju client
        unit: the dns-policy unit
        domain: the domain of the rule
        enabled: whether the rule is enabled
    """
    manage_shell(
        juju,
        unit,
        f"""
import json
from policy.models import Rule
rule, _ = Rule.objects.update_or_create(
    name={f"ACME challenge {domain}"!r},
    defaults={{"kind": "acme_challenge", "domain": {domain!r}, "enabled": {enabled!r}}},
)
print(json.dumps(rule.id))
""",
    )


def _approve(juju: jubilant.Juju, unit: str, host_label: str, domain: str) -> None:
    """Manually approve a record request, once the charm submitted it to the workload.

    Args:
        juju: the juju client
        unit: the dns-policy unit
        host_label: the host label of the record request
        domain: the domain of the record request
    """
    code = f"""
import json
from policy.models import RecordRequest
from policy.rules import evaluate_rules
approved = RecordRequest.objects.filter(
    host_label={host_label!r}, domain={domain!r}
).update(status=RecordRequest.Status.APPROVED)
evaluate_rules()
print(json.dumps(approved))
"""
    for _ in range(30):
        if manage_shell(juju, unit, code):
            return
        time.sleep(10)  # wait for the reconciliation timer to submit the request
    pytest.fail(f"The record request {host_label} {domain} never reached the workload")


@pytest.fixture(scope="module", name="ddns_label")
def ddns_label_fixture(
    juju: jubilant.Juju,
    dns_integrator_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """Get the label of the domain allocated to the requirer."""
    domain = wait_for_ddns_domain(juju, f"{dns_integrator_name}/0", published=True)
    assert domain is not None and domain.endswith(f".{DDNS_DOMAIN}")
    yield domain.partition(".")[0]


@pytest.fixture(scope="module", name="rules_deployment")
def rules_deployment_fixture(
    juju: jubilant.Juju, dns_policy_name: str, dns_integrator_name: str, ddns_label: str
):
    """Request an A record and the ACME challenges of the requirer.

    Yields:
        the address of the DNS provider to resolve the records against
    """
    requests = [
        ADDRESS_REQUEST,
        f"_acme-challenge.admin {DOMAIN} 600 IN TXT {OWNED_CHALLENGE}",
        f"_acme-challenge.unowned {DOMAIN} 600 IN TXT {UNOWNED_CHALLENGE}",
        f"_acme-challenge.{ddns_label} {DDNS_DOMAIN} 600 IN TXT {DDNS_CHALLENGE}",
    ]
    juju.config(dns_integrator_name, {"requests": "\n".join(requests)})
    juju.wait(
        lambda status: jubilant.all_active(status, dns_policy_name, dns_integrator_name),
        error=jubilant.any_error,
    )
    yield


@pytest.fixture(scope="module", name="nameserver")
def nameserver_fixture(
    juju: jubilant.Juju,
    bind_name: str,
    rules_deployment,  # pylint: disable=unused-argument
):
    """Get the address of the DNS provider."""
    yield juju.status().get_units(bind_name)[f"{bind_name}/0"].public_address


@pytest.mark.abort_on_fail
def test_acme_challenge_of_an_approved_domain(
    juju: jubilant.Juju, dns_policy_name: str, ddns_label: str, nameserver: str
):
    """
    arrange: request an A record and ACME challenges, and add a rule for the domain.
    act: manually approve the A record.
    assert: only the challenge of the approved domain is automatically approved, the
        ones of a domain the requirer doesn't own, or outside of the rule domain, are not.
    """
    unit = f"{dns_policy_name}/0"
    _set_rule(juju, unit, DOMAIN)
    _approve(juju, unit, "admin", DOMAIN)

    answers = resolve(nameserver, f"_acme-challenge.admin.{DOMAIN}", "TXT")
    assert [answer.strip('"') for answer in answers] == [OWNED_CHALLENGE]
    # Published along with the automatically approved challenge if they were approved too
    assert not is_resolvable(nameserver, f"_acme-challenge.unowned.{DOMAIN}", "TXT")
    assert not is_resolvable(nameserver, f"_acme-challenge.{ddns_label}.{DDNS_DOMAIN}", "TXT")


@pytest.mark.abort_on_fail
def test_acme_challenge_of_an_allocated_domain(
    juju: jubilant.Juju, dns_policy_name: str, ddns_label: str, nameserver: str
):
    """
    arrange: request the ACME challenge of the domain allocated to the requirer.
    act: add a rule for the suffix of the allocated domains.
    assert: the challenge is automatically approved.
    """
    _set_rule(juju, f"{dns_policy_name}/0", DDNS_DOMAIN)

    answers = resolve(nameserver, f"_acme-challenge.{ddns_label}.{DDNS_DOMAIN}", "TXT")
    assert [answer.strip('"') for answer in answers] == [DDNS_CHALLENGE]


@pytest.mark.abort_on_fail
def test_disabling_a_rule_withdraws_its_approvals(
    juju: jubilant.Juju, dns_policy_name: str, nameserver: str
):
    """
    arrange: let a rule automatically approve an ACME challenge.
    act: disable the rule.
    assert: the challenge is withdrawn, the manually approved A record is not.
    """
    _set_rule(juju, f"{dns_policy_name}/0", DOMAIN, enabled=False)

    wait_unresolvable(nameserver, f"_acme-challenge.admin.{DOMAIN}", "TXT")
    assert resolve(nameserver, f"admin.{DOMAIN}") == ["42.42.42.42"]
