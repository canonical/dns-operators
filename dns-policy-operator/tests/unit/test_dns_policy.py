# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns-policy workload service."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import constants
import dns_policy

INSTANCE = "8ad9f1e2-0c2a-4f8e-9a2b-3b6d5f7c1e40"
PARENT = "example.com"


def _response(payload) -> MagicMock:
    """Build a mocked response of the workload API.

    Args:
        payload: the JSON body of the response.

    Returns:
        the mocked response.
    """
    response = MagicMock()
    response.json.return_value = payload
    return response


def _allocation(relation_id: int, domain: str, instance: str = INSTANCE) -> dict:
    """Build an allocation as returned by the workload API.

    Args:
        relation_id: the id of the relation the domain is allocated to.
        domain: the allocated domain.
        instance: the instance the relation belongs to.

    Returns:
        the allocation.
    """
    return {
        "instance": instance,
        "relation_id": relation_id,
        "domain": domain,
        "created_at": "2026-01-01T00:00:00Z",
    }


def test_allocate_ddns_domains():
    """
    arrange: mock the workload API allocating a domain to each relation
    act: allocate the domains of two relations
    assert: a single POST holds every relation and the domains are returned by relation
    """
    response = _response(
        [_allocation(1, f"c3f9m2q4.{PARENT}"), _allocation(2, f"x2v9p8g7.{PARENT}")]
    )
    with patch("requests.post", return_value=response) as post:
        domains = dns_policy.DnsPolicyService().allocate_ddns_domains(
            "token", INSTANCE, [1, 2], PARENT
        )

    assert domains == {1: f"c3f9m2q4.{PARENT}", 2: f"x2v9p8g7.{PARENT}"}
    post.assert_called_once()
    assert post.call_args[0][0] == f"{constants.DNS_POLICY_DDNS_ALLOCATIONS_ENDPOINT}/"
    assert json.loads(post.call_args[1]["data"]) == [
        {"instance": INSTANCE, "relation_id": 1, "parent": PARENT},
        {"instance": INSTANCE, "relation_id": 2, "parent": PARENT},
    ]


def test_allocate_no_ddns_domains():
    """
    arrange: nothing
    act: allocate the domains of no relation
    assert: the workload API is not called
    """
    with patch("requests.post") as post:
        domains = dns_policy.DnsPolicyService().allocate_ddns_domains(
            "token", INSTANCE, [], PARENT
        )

    assert not domains
    post.assert_not_called()


def test_allocate_ddns_domains_api_error():
    """
    arrange: mock the workload API failing
    act: allocate the domain of a relation
    assert: an ApiError is raised
    """
    with patch("requests.post", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(dns_policy.ApiError):
            dns_policy.DnsPolicyService().allocate_ddns_domains("token", INSTANCE, [1], PARENT)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"detail": "oops"}, id="not-a-list"),
        pytest.param([{"relation_id": 1}], id="missing-fields"),
        pytest.param([_allocation(1, "c3f9m2q4.example.org")], id="other-parent"),
        pytest.param([_allocation(1, f"a.c3f9m2q4.{PARENT}")], id="not-directly-under"),
        pytest.param([_allocation(1, PARENT)], id="parent-itself"),
    ],
)
def test_allocate_ddns_domains_invalid_answer(payload):
    """
    arrange: mock the workload API answering with unusable allocations
    act: allocate the domain of a relation
    assert: a DdnsAllocationError is raised
    """
    with patch("requests.post", return_value=_response(payload)):
        with pytest.raises(dns_policy.DdnsAllocationError):
            dns_policy.DnsPolicyService().allocate_ddns_domains("token", INSTANCE, [1], PARENT)
