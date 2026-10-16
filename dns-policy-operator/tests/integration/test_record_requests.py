#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests of the responses to the record requests."""

# pylint: disable=duplicate-code

import json
import logging
import time
import typing

import dns.exception
import dns.resolver
import jubilant
import pytest

logger = logging.getLogger(__name__)


def _responses(juju: jubilant.Juju, requirer_unit: str) -> list[dict[str, typing.Any]]:
    """Get the responses the dns-policy charm published to a requirer.

    `juju show-unit` reports the application data of the remote side of each relation,
    so the data dns-policy publishes is read from the requirer unit.

    Args:
        juju: the juju client
        requirer_unit: the requirer unit to read the relation data of

    Returns:
        the responses published to the requirer
    """
    unit_info = json.loads(juju.cli("show-unit", requirer_unit, "--format", "json"))
    for relation_info in unit_info[requirer_unit].get("relation-info", []):
        if relation_info.get("endpoint") == "dns-record":
            return json.loads(relation_info.get("application-data", {}).get("dns_entries", "[]"))
    return []


def _wait_for_responses(
    juju: jubilant.Juju,
    requirer_unit: str,
    predicate: typing.Callable[[list[dict[str, typing.Any]]], bool],
) -> list[dict[str, typing.Any]]:
    """Wait for the responses published to a requirer to match a predicate.

    The charm reconciles the requests on a timer, so this polls for a couple of ticks.

    Args:
        juju: the juju client
        requirer_unit: the requirer unit to read the relation data of
        predicate: the condition the responses must meet

    Returns:
        the responses published to the requirer
    """
    responses: list[dict[str, typing.Any]] = []
    for _ in range(30):
        responses = _responses(juju, requirer_unit)
        if predicate(responses):
            return responses
        time.sleep(10)
    pytest.fail(f"Unexpected responses published to {requirer_unit}: {responses}")
    return responses


def _statuses(responses: list[dict[str, typing.Any]]) -> list[tuple[str, str]]:
    """Get the status and description of each response.

    Args:
        responses: the responses to read

    Returns:
        the sorted status and description of the responses
    """
    return sorted((response["status"], response.get("description", "")) for response in responses)


def _set_request_status(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    juju: jubilant.Juju,
    dns_policy_unit: str,
    snap_name: str,
    uuid: str,
    status: str,
    reason: str = "",
) -> None:
    """Review a record request in the workload, as a reviewer would in the dashboard.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to review the request on
        snap_name: the name of the workload snap
        uuid: the uuid of the request to review
        status: the review status to set
        reason: the reason of the review status
    """
    command = f"sudo snap run {snap_name}.manage set_request_status {uuid} {status}"
    if reason:
        command += f" --reason '{reason}'"
    juju.ssh(dns_policy_unit, command)


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


@pytest.mark.abort_on_fail
def test_request_is_pending_until_reviewed(
    juju: jubilant.Juju,
    dns_integrator_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and integrate a requirer requesting a record.
    act: nothing.
    assert: the requirer is told its request is waiting for review.
    """
    responses = _wait_for_responses(juju, f"{dns_integrator_name}/0", lambda r: len(r) == 1)

    assert _statuses(responses) == [("pending", "Waiting for review")]


@pytest.mark.abort_on_fail
def test_denied_request_is_reported(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_policy_snap_name: str,
    dns_integrator_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer request a record.
    act: deny the request in the workload.
    assert: the requirer is told its request is denied, with the reason.
    """
    requirer_unit = f"{dns_integrator_name}/0"
    (response,) = _responses(juju, requirer_unit)

    _set_request_status(
        juju,
        f"{dns_policy_name}/0",
        dns_policy_snap_name,
        response["uuid"],
        "denied",
        "Not allowed",
    )

    responses = _wait_for_responses(
        juju, requirer_unit, lambda r: [x["status"] for x in r] == ["permission_denied"]
    )
    assert _statuses(responses) == [("permission_denied", "Not allowed")]


@pytest.mark.abort_on_fail
def test_approved_request_is_reported(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    juju: jubilant.Juju,
    bind_name: str,
    dns_policy_name: str,
    dns_policy_snap_name: str,
    dns_integrator_name: str,
    integrator_request: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms and let a requirer request a record.
    act: approve the request in the workload.
    assert: the record is resolvable and the requirer is told its request is approved.
    """
    requirer_unit = f"{dns_integrator_name}/0"
    (response,) = _responses(juju, requirer_unit)

    _set_request_status(
        juju, f"{dns_policy_name}/0", dns_policy_snap_name, response["uuid"], "approved"
    )

    responses = _wait_for_responses(
        juju, requirer_unit, lambda r: [x["status"] for x in r] == ["approved"]
    )
    assert [r["uuid"] for r in responses] == [response["uuid"]]
    host_label, domain, *_, address = integrator_request.split()
    bind_address = juju.status().get_units(bind_name)[f"{bind_name}/0"].public_address
    assert _resolve(bind_address, f"{host_label}.{domain}") == [address]


@pytest.mark.abort_on_fail
def test_address_request_under_the_ddns_domain_is_denied(
    juju: jubilant.Juju,
    dns_integrator_name: str,
    integrator_request: str,
    ddns_domain: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """
    arrange: deploy the charms with the ddns feature enabled.
    act: request an A and a TXT record under the ddns domain along with an approved one.
    assert: only the A record under the ddns domain is denied, the TXT record is left to
        the review and the other one stays approved.
    """
    requirer_unit = f"{dns_integrator_name}/0"
    reserved_request = f"admin {ddns_domain} 600 IN A 42.42.42.43"
    txt_request = f"_acme-challenge.admin {ddns_domain} 600 IN TXT challenge"

    juju.config(
        dns_integrator_name,
        {"requests": "\n".join((integrator_request, reserved_request, txt_request))},
    )

    responses = _wait_for_responses(juju, requirer_unit, lambda r: len(r) == 3)
    assert _statuses(responses) == [
        ("approved", ""),
        ("pending", "Waiting for review"),
        ("permission_denied", "Reserved for the automatically allocated domains"),
    ]
