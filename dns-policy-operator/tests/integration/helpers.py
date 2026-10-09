# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers shared by the integration tests."""

import base64
import json
import logging
import time
import typing

import dns.exception
import dns.resolver
import jubilant
import pytest

logger = logging.getLogger(__name__)

# Name of the workload snap
SNAP_NAME = "charmed-dns-policy"


def get_relation_info(juju: jubilant.Juju, unit: str, endpoint: str) -> dict[str, typing.Any]:
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


def published_ddns_domain(juju: jubilant.Juju, requirer_unit: str) -> str | None:
    """Get the domain the dns-policy charm published to a requirer.

    `juju show-unit` reports the application data of the remote side of each relation,
    so the data dns-policy publishes is read from the requirer unit.

    Args:
        juju: the juju client
        requirer_unit: the requirer unit to read the relation data of

    Returns:
        the automatically allocated domain, or None when none was published
    """
    relation_info = get_relation_info(juju, requirer_unit, "dns-record")
    return relation_info.get("application-data", {}).get("ddns-domain") or None


def requirer_ingress_address(juju: jubilant.Juju, dns_policy_unit: str, requirer_unit: str) -> str:
    """Get the ingress address juju set for a requirer unit.

    Args:
        juju: the juju client
        dns_policy_unit: the dns-policy unit to read the relation data of
        requirer_unit: the requirer unit to get the ingress address of

    Returns:
        the ingress address of the requirer unit
    """
    relation_info = get_relation_info(juju, dns_policy_unit, "dns-record-provider")
    related_units = relation_info.get("related-units", {})
    return related_units[requirer_unit]["data"]["ingress-address"]


def wait_for_ddns_domain(juju: jubilant.Juju, requirer_unit: str, published: bool) -> str | None:
    """Wait for the dns-policy charm to publish, or withdraw, an allocated domain.

    The charm allocates the domains on a timer, so this polls for a couple of ticks.

    Args:
        juju: the juju client
        requirer_unit: the requirer unit to read the relation data of
        published: whether to wait for a domain to appear or to disappear

    Returns:
        the automatically allocated domain, or None when none is published
    """
    for _ in range(30):
        domain = published_ddns_domain(juju, requirer_unit)
        if (domain is not None) == published:
            return domain
        time.sleep(10)
    state = "published" if published else "withdrawn"
    pytest.fail(f"The allocated domain of {requirer_unit} was not {state}")
    return None


def resolve(nameserver: str, name: str, rdtype: str = "A") -> list[str]:
    """Resolve the records of a name, retrying while the changes propagate.

    Args:
        nameserver: the address of the nameserver to query
        name: the name to resolve
        rdtype: the type of the records to resolve

    Returns:
        the record data of the answers
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    for _ in range(30):
        try:
            answers = resolver.resolve(name, rdtype)
        except dns.exception.DNSException as exc:
            logger.info("Could not resolve %s yet: %s", name, exc)
        else:
            return [answer.to_text() for answer in answers]
        time.sleep(10)
    pytest.fail(f"Could not resolve {name} from the nameserver {nameserver}")
    return []


def is_resolvable(nameserver: str, name: str, rdtype: str = "A") -> bool:
    """Check, without retrying, whether a name has records of a type.

    Args:
        nameserver: the address of the nameserver to query
        name: the name to resolve
        rdtype: the type of the records to resolve

    Returns:
        whether the nameserver answers with records
    """
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    try:
        resolver.resolve(name, rdtype)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return False
    return True


def wait_unresolvable(nameserver: str, name: str, rdtype: str = "A") -> None:
    """Wait for a name to have no records of a type anymore.

    Args:
        nameserver: the address of the nameserver to query
        name: the name to resolve
        rdtype: the type of the records to resolve
    """
    for _ in range(30):
        try:
            if not is_resolvable(nameserver, name, rdtype):
                return
        except dns.exception.DNSException as exc:
            logger.info("Could not query %s: %s", name, exc)
        time.sleep(10)
    pytest.fail(f"{name} is still resolvable from the nameserver {nameserver}")


def manage_shell(juju: jubilant.Juju, unit: str, code: str) -> typing.Any:
    """Run python code in the django shell of the workload of a dns-policy unit.

    The code is handed over base64 encoded to be safe from any shell quoting, and is
    expected to print a JSON document as its last line of output.

    Args:
        juju: the juju client
        unit: the dns-policy unit to run the code on
        code: the python code to run

    Returns:
        the JSON document the code printed last
    """
    encoded = base64.b64encode(code.encode()).decode()
    task = juju.exec(
        f'snap run {SNAP_NAME}.manage shell -c "$(echo {encoded} | base64 -d)"', unit=unit
    )
    return json.loads(task.stdout.strip().splitlines()[-1])
