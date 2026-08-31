# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns-policy charm."""

import dataclasses
import json
import logging
import uuid
from unittest.mock import patch

import ops
import ops.testing
import pytest
from charms.dns_record.v0.dns_record import Record, RecordRequest
from scenario.context import _Event  # needed for custom events for now

import dns_policy

logger = logging.getLogger(__name__)


def _record_request(entry):
    """Build the RecordRequest a relation databag entry is parsed into."""
    return RecordRequest.model_validate({**entry, "record": Record.model_validate(entry)})


def _local_app_data(state, endpoint):
    """Get the local application databag of the relation on an endpoint."""
    return next(
        relation.local_app_data for relation in state.relations if relation.endpoint == endpoint
    )


def _published_entries(state):
    """Get the DNS entries published to the upstream DNS provider."""
    return json.loads(_local_app_data(state, "dns-record-requirer").get("dns_entries", "[]"))


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_start(context, base_state):
    """
    arrange: prepare some state
    act: run start
    assert: status is waiting
    """
    base_state["relations"] = []
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.WaitingStatus("Waiting for a database integration.")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
def test_start_with_database(context, base_state, database_relation):
    """
    arrange: prepare some state
    act: run start
    assert: status is active
    """
    base_state["relations"].append(database_relation)
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.ActiveStatus("")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
def test_start_on_a_non_leader_unit(context, base_state, database_relation):
    """
    arrange: prepare some state on a non leader unit
    act: run start
    assert: the charm sets up without trying to manage an application owned secret
    """
    base_state["relations"].append(database_relation)
    base_state["leader"] = False
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.ActiveStatus("")
    assert not out.secrets


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
def test_start_with_invalid_ddns_domain(context, base_state, database_relation):
    """
    arrange: prepare some state with an invalid ddns-domain configuration
    act: run start
    assert: status is blocked
    """
    base_state["relations"].append(database_relation)
    base_state["config"] = {"ddns-domain": "not a domain"}
    state = ops.testing.State(**base_state)

    out = context.run(context.on.start(), state)
    assert out.unit_status == ops.BlockedStatus("Invalid ddns-domain configuration: not a domain")


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("api_root_token")
@pytest.mark.usefixtures("record_request")
# This is a complex state that needs 6 arguments. Sorry pylint !
# pylint: disable=too-many-positional-arguments
def test_reconcile(
    context, base_state, database_relation, requirer_relation, api_root_token, record_request
):
    """
    arrange: prepare some state
    act: run reconcile
    assert: status is active and requests were send to the API
    """
    base_state["relations"].extend([database_relation, requirer_relation])
    state = ops.testing.State(**base_state)

    with (patch("dns_policy.DnsPolicyService.send_requests") as dns_policy_send_requests,):
        reconcile_event = _Event("reconcile")
        out = context.run(reconcile_event, state)
        assert out.unit_status == ops.ActiveStatus("")
        dns_policy_send_requests.assert_called()
        assert dns_policy_send_requests.call_args[0] == (
            api_root_token,
            [_record_request(record_request)],
        )


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
# pylint: disable=too-many-positional-arguments
def test_reconcile_allocates_a_ddns_domain(
    context, base_state, database_relation, requirer_relation, ddns_domain, ddns_label
):
    """
    arrange: prepare some state with the ddns feature enabled
    act: run reconcile
    assert: the allocated domain is published to the requirer and resolved upstream
    """
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests"),
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        allocate_ddns_labels.return_value = {requirer_relation.id: ddns_label}
        out = context.run(_Event("reconcile"), state)

    allocate_ddns_labels.assert_called_once()
    instance = _local_app_data(out, "dns-policy-peers")["ddns-instance"]
    assert allocate_ddns_labels.call_args[0][1] == instance
    assert allocate_ddns_labels.call_args[0][2] == [requirer_relation.id]

    provider_data = _local_app_data(out, "dns-record-provider")
    assert json.loads(provider_data["ddns-domain"]) == f"{ddns_label}.{ddns_domain}"

    published = _published_entries(out)
    assert {
        (entry["host_label"], entry["domain"], entry["record_data"]) for entry in published
    } == {
        (ddns_label, ddns_domain, "10.0.0.1"),
        (f"*.{ddns_label}", ddns_domain, "10.0.0.1"),
    }
    assert {entry["record_type"] for entry in published} == {"A"}


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
# pylint: disable=too-many-positional-arguments
def test_reconcile_prefers_the_declared_ddns_addresses(
    context, base_state, database_relation, requirer_relation, ddns_domain, ddns_label
):
    """
    arrange: prepare some state where the requirer declares its own addresses
    act: run reconcile
    assert: the declared addresses are used instead of the juju ingress-address
    """
    requirer_relation = dataclasses.replace(
        requirer_relation,
        remote_app_data={
            **requirer_relation.remote_app_data,
            "ddns-addresses": json.dumps(["2001:db8::1"]),
        },
    )
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests"),
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        allocate_ddns_labels.return_value = {requirer_relation.id: ddns_label}
        out = context.run(_Event("reconcile"), state)

    published = _published_entries(out)
    assert {entry["record_data"] for entry in published} == {"2001:db8::1"}
    assert {entry["record_type"] for entry in published} == {"AAAA"}


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
@pytest.mark.usefixtures("record_request")
@pytest.mark.usefixtures("ddns_record_request")
# pylint: disable=too-many-positional-arguments
def test_reconcile_rejects_requests_under_the_ddns_domain(
    context,
    base_state,
    database_relation,
    requirer_relation,
    ddns_domain,
    ddns_label,
    record_request,
    ddns_record_request,
):
    """
    arrange: prepare a requirer requesting a record under the ddns domain
    act: run reconcile
    assert: only the request outside of the ddns domain reaches the workload
    """
    requirer_relation = dataclasses.replace(
        requirer_relation,
        remote_app_data={"dns_entries": json.dumps([record_request, ddns_record_request])},
    )
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests") as dns_policy_send_requests,
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        allocate_ddns_labels.return_value = {requirer_relation.id: ddns_label}
        context.run(_Event("reconcile"), state)

    assert dns_policy_send_requests.call_args[0][1] == [_record_request(record_request)]


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
@pytest.mark.usefixtures("ddns_record_request")
# pylint: disable=too-many-positional-arguments
def test_reconcile_withdraws_the_requests_under_the_ddns_domain(
    context,
    base_state,
    database_relation,
    requirer_relation,
    ddns_domain,
    ddns_label,
    ddns_record_request,
):
    """
    arrange: prepare a requirer whose only request is under the ddns domain
    act: run reconcile
    assert: an empty list is submitted, withdrawing the request from the workload
    """
    requirer_relation = dataclasses.replace(
        requirer_relation,
        remote_app_data={"dns_entries": json.dumps([ddns_record_request])},
    )
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests") as dns_policy_send_requests,
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        allocate_ddns_labels.return_value = {requirer_relation.id: ddns_label}
        context.run(_Event("reconcile"), state)

    dns_policy_send_requests.assert_called_once()
    assert dns_policy_send_requests.call_args[0][1] == []


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
# pylint: disable=too-many-positional-arguments
def test_reconcile_skips_an_invalid_ddns_domain(
    context, base_state, database_relation, requirer_relation, ddns_domain, ddns_label
):
    """
    arrange: prepare a relation holding an allocated domain and an invalid configuration
    act: run reconcile
    assert: nothing is reconciled and the allocated domain is left untouched
    """
    allocated = f"{ddns_label}.{ddns_domain}"
    requirer_relation = dataclasses.replace(
        requirer_relation,
        local_app_data={"ddns-domain": json.dumps(allocated)},
    )
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": "not a domain"}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests") as dns_policy_send_requests,
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        out = context.run(_Event("reconcile"), state)

    dns_policy_send_requests.assert_not_called()
    allocate_ddns_labels.assert_not_called()
    assert json.loads(_local_app_data(out, "dns-record-provider")["ddns-domain"]) == allocated


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
# pylint: disable=too-many-positional-arguments
def test_reconcile_withdraws_the_ddns_domain_when_disabled(
    context, base_state, database_relation, requirer_relation, ddns_domain, ddns_label
):
    """
    arrange: prepare a relation holding a previously allocated domain, ddns disabled
    act: run reconcile
    assert: the allocated domain is withdrawn from the relation
    """
    requirer_relation = dataclasses.replace(
        requirer_relation,
        local_app_data={"ddns-domain": json.dumps(f"{ddns_label}.{ddns_domain}")},
    )
    base_state["relations"].extend([database_relation, requirer_relation])
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests"),
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        out = context.run(_Event("reconcile"), state)

    allocate_ddns_labels.assert_not_called()
    assert _local_app_data(out, "dns-record-provider").get("ddns-domain", "") == ""


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
def test_install_generates_the_instance_identifier(context, base_state):
    """
    arrange: prepare some state
    act: run install
    assert: an instance identifier is stored in the peer relation
    """
    state = ops.testing.State(**base_state)

    out = context.run(context.on.install(), state)

    instance = _local_app_data(out, "dns-policy-peers")["ddns-instance"]
    assert uuid.UUID(instance)


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("peer_relation")
@pytest.mark.usefixtures("ddns_domain")
@pytest.mark.usefixtures("ddns_label")
# pylint: disable=too-many-positional-arguments
def test_reconcile_keeps_the_instance_identifier(
    context,
    base_state,
    database_relation,
    requirer_relation,
    peer_relation,
    ddns_domain,
    ddns_label,
):
    """
    arrange: prepare some state with an instance identifier already in the peer relation
    act: run reconcile
    assert: the identifier is reused as is to allocate the domains
    """
    instance = "8ad9f1e2-0c2a-4f8e-9a2b-3b6d5f7c1e40"
    base_state["relations"] = [
        relation for relation in base_state["relations"] if relation is not peer_relation
    ]
    base_state["relations"].extend(
        [
            dataclasses.replace(peer_relation, local_app_data={"ddns-instance": instance}),
            database_relation,
            requirer_relation,
        ]
    )
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests"),
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        allocate_ddns_labels.return_value = {requirer_relation.id: ddns_label}
        out = context.run(_Event("reconcile"), state)

    assert allocate_ddns_labels.call_args[0][1] == instance
    assert _local_app_data(out, "dns-policy-peers")["ddns-instance"] == instance


@pytest.mark.usefixtures("context")
@pytest.mark.usefixtures("base_state")
@pytest.mark.usefixtures("database_relation")
@pytest.mark.usefixtures("requirer_relation")
@pytest.mark.usefixtures("peer_relation")
@pytest.mark.usefixtures("ddns_domain")
# pylint: disable=too-many-positional-arguments
def test_reconcile_without_the_peer_relation(
    context, base_state, database_relation, requirer_relation, peer_relation, ddns_domain
):
    """
    arrange: prepare some state with the ddns feature enabled but no peer relation
    act: run reconcile
    assert: no domain is allocated, as the allocations could not be scoped
    """
    base_state["relations"] = [
        relation for relation in base_state["relations"] if relation is not peer_relation
    ]
    base_state["relations"].extend([database_relation, requirer_relation])
    base_state["config"] = {"ddns-domain": ddns_domain}
    state = ops.testing.State(**base_state)

    with (
        patch("dns_policy.DnsPolicyService.send_requests"),
        patch("dns_policy.DnsPolicyService.allocate_ddns_labels") as allocate_ddns_labels,
    ):
        out = context.run(_Event("reconcile"), state)

    allocate_ddns_labels.assert_not_called()
    assert "ddns-domain" not in _local_app_data(out, "dns-record-provider")


@pytest.mark.parametrize(
    "configured,expected",
    [
        pytest.param("policy.test", ["policy.test", "localhost"], id="added"),
        pytest.param("localhost", ["localhost"], id="already-allowed"),
        pytest.param("", ["localhost"], id="empty"),
        pytest.param("a.test, b.test", ["a.test", "b.test", "localhost"], id="several"),
    ],
)
def test_workload_config_always_allows_the_api_host(configured, expected):
    """
    arrange: prepare an allowed-hosts configuration
    act: build the workload configuration from it
    assert: the host the charm calls the workload API on is always allowed, otherwise
        Django answers every call of the charm with a "400 Bad Request"
    """
    config = dns_policy.DnsPolicyConfig(
        allowed_hosts=[host.strip() for host in configured.split(",")]
    )

    assert config.allowed_hosts == expected
    assert json.loads(config.model_dump()["allowed-hosts"]) == expected
