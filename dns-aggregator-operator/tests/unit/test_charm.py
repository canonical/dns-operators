# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the dns-aggregator charm."""

import logging

import ops
import ops.testing
import pytest
from charms.dns_record.v0 import dns_record

from src.charm import DOWNSTREAM_RELATION_NAME, MIXIN_RELATION_NAME, UPSTREAM_RELATION_NAME
from tests.unit.helpers import (
    INTERFACE,
    entry_uuids,
    make_request,
    make_response,
    make_uuid,
    parse_provider,
    parse_requirer,
    provider_databag,
    requirer_databag,
    uuids,
)

logger = logging.getLogger(__name__)


def downstream_relation(dns_entries=(), ddns_addresses=(), units=None, endpoint=None):
    """Build a downstream relation.

    Args:
        dns_entries: the record requests published by the downstream requirer.
        ddns_addresses: the ddns addresses declared by the downstream requirer.
        units: the unit databags of the downstream requirer, by unit number.
        endpoint: the endpoint of the relation.

    Returns:
        the relation.
    """
    return ops.testing.Relation(
        endpoint=endpoint or DOWNSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="requirer",
        remote_app_data=requirer_databag(dns_entries, ddns_addresses),
        remote_units_data=units if units is not None else {0: {}},
    )


def mixin_relation(dns_entries=(), ddns_addresses=(), remote_app_name="mixin"):
    """Build a mixin downstream relation.

    Args:
        dns_entries: the record requests published by the mixin requirer.
        ddns_addresses: the ddns addresses declared by the mixin requirer.
        remote_app_name: the name of the mixin requirer application.

    Returns:
        the relation.
    """
    return ops.testing.Relation(
        endpoint=MIXIN_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name=remote_app_name,
        remote_app_data=requirer_databag(dns_entries, ddns_addresses),
        remote_units_data={0: {}},
    )


def upstream_relation(dns_entries=(), ddns_domain=None):
    """Build the upstream relation.

    Args:
        dns_entries: the responses published by the DNS provider.
        ddns_domain: the domain allocated by the DNS provider.

    Returns:
        the relation.
    """
    return ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data=provider_databag(dns_entries, ddns_domain),
        remote_units_data={0: {}},
    )


def reconcile(context, base_state, relations):
    """Run an event triggering a reconciliation.

    Args:
        context: the charm context.
        base_state: the base state of the charm.
        relations: the relations of the charm.

    Returns:
        the resulting state of the charm.
    """
    base_state["relations"] = relations
    state = ops.testing.State(**base_state)
    return context.run(context.on.update_status(), state)


@pytest.mark.usefixtures("context", "base_state")
def test_blocked_without_any_integration(context, base_state):
    """
    arrange: no integration at all
    act: run an event
    assert: the charm waits for the upstream integration
    """
    out = reconcile(context, base_state, [])

    assert out.unit_status == ops.BlockedStatus(
        f"Waiting for a {UPSTREAM_RELATION_NAME} integration"
    )


@pytest.mark.usefixtures("context", "base_state")
def test_blocked_without_downstream_integration(context, base_state):
    """
    arrange: only the upstream integration
    act: run an event
    assert: the charm waits for the downstream integration
    """
    out = reconcile(context, base_state, [upstream_relation()])

    assert out.unit_status == ops.BlockedStatus(
        f"Waiting for a {DOWNSTREAM_RELATION_NAME} integration"
    )


@pytest.mark.usefixtures("context", "base_state")
def test_active_with_both_integrations(context, base_state):
    """
    arrange: the upstream and the downstream integrations
    act: run an event
    assert: the charm is active
    """
    out = reconcile(context, base_state, [upstream_relation(), downstream_relation()])

    assert out.unit_status == ops.ActiveStatus()


@pytest.mark.usefixtures("context", "base_state")
def test_requests_are_aggregated_upstream(context, base_state):
    """
    arrange: a downstream and two mixin integrations, each requesting a record
    act: run an event
    assert: every request is forwarded upstream
    """
    upstream = upstream_relation()
    relations = [
        upstream,
        downstream_relation([make_request("main")]),
        mixin_relation([make_request("mixin-1")], remote_app_name="mixin-1"),
        mixin_relation([make_request("mixin-2")], remote_app_name="mixin-2"),
    ]

    out = reconcile(context, base_state, relations)

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert entry_uuids(published.dns_entries) == uuids(["main", "mixin-1", "mixin-2"])
    assert all(entry.record is not None for entry in published.dns_entries)


@pytest.mark.usefixtures("context", "base_state")
def test_duplicated_requests_are_forwarded_once(context, base_state):
    """
    arrange: a downstream and a mixin integration requesting the very same record
    act: run an event
    assert: the request is forwarded upstream a single time
    """
    upstream = upstream_relation()
    relations = [
        upstream,
        downstream_relation([make_request("shared")]),
        mixin_relation([make_request("shared")]),
    ]

    out = reconcile(context, base_state, relations)

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert [entry.uuid for entry in published.dns_entries] == [make_uuid("shared")]


@pytest.mark.usefixtures("context", "base_state")
def test_requests_are_withdrawn_when_downstream_goes_away(context, base_state):
    """
    arrange: an upstream integration still holding requests, without any downstream
    act: run an event
    assert: the requests are withdrawn from the upstream integration
    """
    upstream = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data=provider_databag(),
        local_app_data=requirer_databag([make_request("gone")]),
    )

    out = reconcile(context, base_state, [upstream])

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert published.dns_entries == []


@pytest.mark.usefixtures("context", "base_state")
def test_responses_are_dispatched_by_uuid(context, base_state):
    """
    arrange: a downstream and a mixin integration, both answered upstream
    act: run an event
    assert: each downstream only gets the responses to the requests it made
    """
    upstream = upstream_relation(
        [
            make_response("main", description="main approved"),
            make_response("mixin", description="mixin approved"),
            make_response("other", description="unrelated"),
        ]
    )
    downstream = downstream_relation([make_request("main")])
    mixin = mixin_relation([make_request("mixin")])

    out = reconcile(context, base_state, [upstream, downstream, mixin])

    downstream_entries = parse_provider(out.get_relation(downstream.id).local_app_data).dns_entries
    assert [(entry.uuid, entry.description) for entry in downstream_entries] == [
        (make_uuid("main"), "main approved")
    ]
    mixin_entries = parse_provider(out.get_relation(mixin.id).local_app_data).dns_entries
    assert [(entry.uuid, entry.description) for entry in mixin_entries] == [
        (make_uuid("mixin"), "mixin approved")
    ]


@pytest.mark.usefixtures("context", "base_state")
def test_responses_are_withdrawn_when_upstream_goes_away(context, base_state):
    """
    arrange: a downstream integration holding a response, without any upstream
    act: run an event
    assert: the response is withdrawn from the downstream integration
    """
    downstream = ops.testing.Relation(
        endpoint=DOWNSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="requirer",
        remote_app_data=requirer_databag([make_request("main")]),
        local_app_data=provider_databag([make_response("main")], ddns_domain="a.example.com"),
    )

    out = reconcile(context, base_state, [downstream])

    published = parse_provider(out.get_relation(downstream.id).local_app_data)
    assert published.dns_entries == []
    assert published.ddns_domain is None


@pytest.mark.usefixtures("context", "base_state")
def test_declared_ddns_addresses_are_forwarded(context, base_state):
    """
    arrange: a downstream integration declaring its ddns addresses
    act: run an event
    assert: the declared addresses are forwarded upstream as they are
    """
    upstream = upstream_relation()
    downstream = downstream_relation(
        ddns_addresses=["10.1.1.1", "fd00::1"],
        units={0: {"ingress-address": "192.0.2.1"}},
    )

    out = reconcile(context, base_state, [upstream, downstream])

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert {str(address) for address in published.ddns_addresses} == {"10.1.1.1", "fd00::1"}


@pytest.mark.usefixtures("context", "base_state")
def test_ddns_addresses_fall_back_to_ingress_addresses(context, base_state):
    """
    arrange: a downstream integration declaring no ddns address
    act: run an event
    assert: the ingress addresses of its units are forwarded upstream instead
    """
    upstream = upstream_relation()
    downstream = downstream_relation(
        units={
            0: {"ingress-address": "192.0.2.1"},
            1: {"ingress-address": "192.0.2.2"},
            2: {"ingress-address": "192.0.2.1"},
            3: {"ingress-address": "not-an-address"},
            4: {},
        }
    )

    out = reconcile(context, base_state, [upstream, downstream])

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert {str(address) for address in published.ddns_addresses} == {"192.0.2.1", "192.0.2.2"}


@pytest.mark.usefixtures("context", "base_state")
def test_ddns_addresses_are_kept_when_none_can_be_derived(context, base_state):
    """
    arrange: a downstream integration declaring no ddns address and having no unit yet
    act: run an event
    assert: the addresses already published upstream are left untouched
    """
    upstream = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data=provider_databag(),
        local_app_data=requirer_databag(ddns_addresses=["203.0.113.9"]),
    )
    downstream = downstream_relation(units={})

    out = reconcile(context, base_state, [upstream, downstream])

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert {str(address) for address in published.ddns_addresses} == {"203.0.113.9"}


@pytest.mark.usefixtures("context", "base_state")
def test_mixin_ddns_data_is_ignored(context, base_state):
    """
    arrange: a mixin integration declaring ddns addresses, without any main downstream
    act: run an event
    assert: no ddns address is forwarded upstream and no domain is published to the mixin
    """
    upstream = upstream_relation(ddns_domain="allocated.example.com")
    mixin = mixin_relation(
        [make_request("mixin")],
        ddns_addresses=["10.2.2.2"],
    )

    out = reconcile(context, base_state, [upstream, mixin])

    assert parse_requirer(out.get_relation(upstream.id).local_app_data).ddns_addresses == set()
    assert parse_provider(out.get_relation(mixin.id).local_app_data).ddns_domain is None


@pytest.mark.usefixtures("context", "base_state")
def test_ddns_domain_is_forwarded_downstream(context, base_state):
    """
    arrange: an upstream integration allocating a domain
    act: run an event
    assert: the domain is published to the main downstream only
    """
    upstream = upstream_relation(ddns_domain="allocated.example.com")
    downstream = downstream_relation()
    mixin = mixin_relation()

    out = reconcile(context, base_state, [upstream, downstream, mixin])

    downstream_data = parse_provider(out.get_relation(downstream.id).local_app_data)
    assert downstream_data.ddns_domain == "allocated.example.com"
    assert parse_provider(out.get_relation(mixin.id).local_app_data).ddns_domain is None


@pytest.mark.usefixtures("context", "base_state")
def test_several_downstream_integrations_are_rejected(context, base_state):
    """
    arrange: two integrations on the main downstream endpoint
    act: run an event
    assert: the charm is blocked and nothing is forwarded at all
    """
    upstream = upstream_relation([make_response("first")])
    first = downstream_relation([make_request("first")])
    second = ops.testing.Relation(
        endpoint=DOWNSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="other-requirer",
        remote_app_data=requirer_databag([make_request("second")]),
    )

    out = reconcile(context, base_state, [upstream, first, second])

    assert out.unit_status == ops.BlockedStatus(
        f"Got 2 {DOWNSTREAM_RELATION_NAME} integrations, only one is supported"
    )
    assert out.get_relation(upstream.id).local_app_data == {}
    assert out.get_relation(first.id).local_app_data == {}
    assert out.get_relation(second.id).local_app_data == {}


@pytest.mark.usefixtures("context", "base_state")
def test_several_upstream_integrations_are_rejected(context, base_state):
    """
    arrange: two integrations on the upstream endpoint
    act: run an event
    assert: the charm is blocked and nothing is forwarded at all
    """
    first = upstream_relation()
    second = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="other-provider",
        remote_app_data=provider_databag([make_response("main")]),
    )
    downstream = downstream_relation([make_request("main")])

    out = reconcile(context, base_state, [first, second, downstream])

    assert out.unit_status == ops.BlockedStatus(
        f"Waiting for a {UPSTREAM_RELATION_NAME} integration"
    )
    assert out.get_relation(first.id).local_app_data == {}
    assert out.get_relation(second.id).local_app_data == {}
    assert parse_provider(out.get_relation(downstream.id).local_app_data).dns_entries == []


@pytest.mark.usefixtures("context", "base_state")
def test_non_leader_does_not_publish(context, base_state):
    """
    arrange: a follower unit with both integrations
    act: run an event
    assert: nothing is published
    """
    base_state["leader"] = False
    upstream = upstream_relation([make_response("main")])
    downstream = downstream_relation([make_request("main")])

    out = reconcile(context, base_state, [upstream, downstream])

    assert out.get_relation(upstream.id).local_app_data == {}
    assert out.get_relation(downstream.id).local_app_data == {}


@pytest.mark.usefixtures("context", "base_state")
def test_unreadable_downstream_does_not_withdraw_requests(context, base_state):
    """
    arrange: a mixin integration publishing invalid data, next to a valid downstream one
    act: run an event
    assert: the requests already published upstream are left untouched
    """
    published = requirer_databag([make_request("main"), make_request("mixin")])
    upstream = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data=provider_databag(),
        local_app_data=published,
    )
    downstream = downstream_relation([make_request("main")])
    mixin = ops.testing.Relation(
        endpoint=MIXIN_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="mixin",
        remote_app_data={"ddns-addresses": "not-an-address"},
    )

    out = reconcile(context, base_state, [upstream, downstream, mixin])

    assert parse_requirer(out.get_relation(upstream.id).local_app_data).dns_entries != []
    assert entry_uuids(
        parse_requirer(out.get_relation(upstream.id).local_app_data).dns_entries
    ) == uuids(["main", "mixin"])
    assert out.get_relation(mixin.id).local_app_data == {}


@pytest.mark.usefixtures("context", "base_state")
def test_unreadable_main_downstream_does_not_repoint_ddns_addresses(context, base_state):
    """
    arrange: a main downstream integration whose relation data cannot be read
    act: run an event
    assert: the ddns addresses already published upstream are left untouched
    """
    upstream = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data=provider_databag(),
        local_app_data=requirer_databag(ddns_addresses=["203.0.113.9"]),
    )
    downstream = ops.testing.Relation(
        endpoint=DOWNSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="requirer",
        remote_app_data={"ddns-addresses": "not-an-address"},
        remote_units_data={0: {"ingress-address": "192.0.2.1"}},
    )

    out = reconcile(context, base_state, [upstream, downstream])

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert {str(address) for address in published.ddns_addresses} == {"203.0.113.9"}


@pytest.mark.usefixtures("context", "base_state")
def test_unreadable_upstream_does_not_withdraw_responses(context, base_state):
    """
    arrange: an upstream integration publishing invalid data
    act: run an event
    assert: the responses and the domain already published downstream are left untouched
    """
    upstream = ops.testing.Relation(
        endpoint=UPSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="provider",
        remote_app_data={"ddns-domain": "not a domain!"},
    )
    downstream = ops.testing.Relation(
        endpoint=DOWNSTREAM_RELATION_NAME,
        interface=INTERFACE,
        remote_app_name="requirer",
        remote_app_data=requirer_databag([make_request("main")]),
        local_app_data=provider_databag([make_response("main")], ddns_domain="a.example.com"),
    )

    out = reconcile(context, base_state, [upstream, downstream])

    published = parse_provider(out.get_relation(downstream.id).local_app_data)
    assert entry_uuids(published.dns_entries) == uuids(["main"])
    assert published.ddns_domain == "a.example.com"


@pytest.mark.usefixtures("context", "base_state")
def test_reconciliation_is_event_independent(context, base_state):
    """
    arrange: a downstream and an upstream integration
    act: run several unrelated events
    assert: they all produce the very same relation data
    """
    upstream = upstream_relation([make_response("main")])
    downstream = downstream_relation([make_request("main")])
    base_state["relations"] = [upstream, downstream]
    state = ops.testing.State(**base_state)

    events = (
        context.on.install(),
        context.on.start(),
        context.on.config_changed(),
        context.on.leader_elected(),
        context.on.update_status(),
        context.on.relation_changed(downstream),
        context.on.relation_changed(upstream),
    )
    outputs = [context.run(event, state) for event in events]

    expected = (
        outputs[0].get_relation(upstream.id).local_app_data,
        outputs[0].get_relation(downstream.id).local_app_data,
    )
    assert expected[0] != {}
    assert expected[1] != {}
    for out in outputs[1:]:
        assert (
            out.get_relation(upstream.id).local_app_data,
            out.get_relation(downstream.id).local_app_data,
        ) == expected


@pytest.mark.usefixtures("context", "base_state")
def test_pending_requests_get_no_response(context, base_state):
    """
    arrange: a downstream integration whose request has not been answered upstream
    act: run an event
    assert: no response is published to the downstream integration
    """
    upstream = upstream_relation([make_response("other")])
    downstream = downstream_relation([make_request("main")])

    out = reconcile(context, base_state, [upstream, downstream])

    assert parse_provider(out.get_relation(downstream.id).local_app_data).dns_entries == []


@pytest.mark.usefixtures("context", "base_state")
def test_downstream_relation_broken(context, base_state):
    """
    arrange: a downstream integration being removed
    act: run the relation broken event
    assert: its requests are withdrawn from the upstream integration
    """
    upstream = upstream_relation()
    downstream = downstream_relation([make_request("main")])
    mixin = mixin_relation([make_request("mixin")])
    base_state["relations"] = [upstream, downstream, mixin]
    state = ops.testing.State(**base_state)

    out = context.run(context.on.relation_broken(downstream), state)

    published = parse_requirer(out.get_relation(upstream.id).local_app_data)
    assert entry_uuids(published.dns_entries) == uuids(["mixin"])


@pytest.mark.usefixtures("context", "base_state")
def test_rejected_response_is_dispatched(context, base_state):
    """
    arrange: an upstream integration rejecting a downstream request
    act: run an event
    assert: the rejection is published to the downstream integration
    """
    upstream = upstream_relation(
        [
            make_response(
                "main",
                status=dns_record.Status.PERMISSION_DENIED,
                description="not allowed",
            )
        ]
    )
    downstream = downstream_relation([make_request("main")])

    out = reconcile(context, base_state, [upstream, downstream])

    entries = parse_provider(out.get_relation(downstream.id).local_app_data).dns_entries
    assert len(entries) == 1
    assert entries[0].status == dns_record.Status.PERMISSION_DENIED
    assert entries[0].description == "not allowed"
