# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns-policy workload service."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
import requests
from charms.dns_record.v0.dns_record import Record, RecordClass, RecordRequest, RecordType

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


def _allocation(requirer_id: str, domain: str, instance: str = INSTANCE) -> dict:
    """Build an allocation as returned by the workload API.

    Args:
        requirer_id: the id of the relation the domain is allocated to.
        domain: the allocated domain.
        instance: the instance the relation belongs to.

    Returns:
        the allocation.
    """
    return {
        "instance": instance,
        "requirer_id": requirer_id,
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
        [_allocation("1", f"c3f9m2q4.{PARENT}"), _allocation("2", f"x2v9p8g7.{PARENT}")]
    )
    with patch("requests.post", return_value=response) as post:
        domains = dns_policy.DnsPolicyService().allocate_ddns_domains(
            "token", INSTANCE, [1, 2], PARENT
        )

    assert domains == {1: f"c3f9m2q4.{PARENT}", 2: f"x2v9p8g7.{PARENT}"}
    post.assert_called_once()
    assert post.call_args[0][0] == f"{constants.DNS_POLICY_DDNS_ALLOCATIONS_ENDPOINT}/"
    assert json.loads(post.call_args[1]["data"]) == [
        {"instance": INSTANCE, "requirer_id": "1", "parent": PARENT},
        {"instance": INSTANCE, "requirer_id": "2", "parent": PARENT},
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
        pytest.param([{"requirer_id": "1"}], id="missing-fields"),
        pytest.param([_allocation("1", "c3f9m2q4.example.org")], id="other-parent"),
        pytest.param([_allocation("1", f"a.c3f9m2q4.{PARENT}")], id="not-directly-under"),
        pytest.param([_allocation("1", PARENT)], id="parent-itself"),
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


def test_send_requests_with_the_requirer_id():
    """
    arrange: prepare the record requests of two relations
    act: send them to the workload
    assert: each record request is sent with the id of its relation as requirer id
    """
    first = RecordRequest(
        uuid=uuid.UUID("497dcba3-ecbf-4587-a2dd-5eb0665e6880"),
        record=Record(
            domain="example.com",
            host_label="admin",
            ttl=600,
            record_class=RecordClass.IN,
            record_type=RecordType.A,
            record_data="10.0.0.1",
        ),
    )
    second = first.model_copy(update={"uuid": uuid.UUID("0c2a4f8e-9a2b-4b6d-8f7c-1e408ad9f1e2")})
    with patch("requests.post") as post:
        dns_policy.DnsPolicyService().send_requests("token", {1: [first], 2: [second]})

    post.assert_called_once()
    assert post.call_args[0][0] == f"{constants.DNS_POLICY_ENDPOINTS_BASE}/"
    sent = json.loads(post.call_args[1]["data"])
    assert [(entry["uuid"], entry["requirer_id"]) for entry in sent] == [
        (str(first.uuid), "1"),
        (str(second.uuid), "2"),
    ]
    assert sent[0]["host_label"] == "admin"


def test_get_request_statuses():
    """
    arrange: mock the workload API listing the record requests
    act: get the status of the record requests
    assert: the status and reason of each record request are returned by uuid
    """
    first = "497dcba3-ecbf-4587-a2dd-5eb0665e6880"
    second = "0c2a4f8e-9a2b-4b6d-8f7c-1e408ad9f1e2"
    response = _response(
        [
            {"uuid": first, "status": "approved", "status_reason": None},
            {"uuid": second, "status": "denied", "status_reason": "Not allowed"},
        ]
    )
    with patch("requests.get", return_value=response) as get:
        statuses = dns_policy.DnsPolicyService().get_request_statuses("token")

    assert get.call_args[0][0] == f"{constants.DNS_POLICY_ENDPOINTS_BASE}/all/"
    assert statuses == {
        uuid.UUID(first): ("approved", ""),
        uuid.UUID(second): ("denied", "Not allowed"),
    }


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"code": "token_not_valid"}, id="not-a-list"),
        pytest.param([{"status": "approved"}], id="missing-uuid"),
        pytest.param([{"uuid": "not-a-uuid", "status": "approved"}], id="invalid-uuid"),
    ],
)
def test_get_request_statuses_invalid_answer(payload):
    """
    arrange: mock the workload API answering with unusable data
    act: get the status of the record requests
    assert: a GetRequestStatusesError is raised
    """
    with patch("requests.get", return_value=_response(payload)):
        with pytest.raises(dns_policy.GetRequestStatusesError):
            dns_policy.DnsPolicyService().get_request_statuses("token")
