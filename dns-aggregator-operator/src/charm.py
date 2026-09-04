#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS aggregator charm."""

import dataclasses
import ipaddress
import logging
import typing
import uuid as uuid_module

import ops
from charms.dns_record.v0 import dns_record

logger = logging.getLogger(__name__)


DOWNSTREAM_RELATION_NAME = "dns-record-provider"
MIXIN_RELATION_NAME = "dns-record-provider-mixin"
UPSTREAM_RELATION_NAME = "dns-record-requirer"

INGRESS_ADDRESS_FIELD = "ingress-address"

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


@dataclasses.dataclass(frozen=True)
class Downstream:
    """A downstream relation and the record requests it published.

    Attributes:
        endpoint: the object handling the endpoint the relation is on.
        relation: the downstream relation.
        requests: the record requests published by the downstream application, or None
            when its relation data could not be read.
        uuids: the uuids of the record requests published by the downstream application.
    """

    endpoint: dns_record.DNSRecordProvides
    relation: ops.Relation
    requests: list[dns_record.RecordRequest] | None

    @property
    def uuids(self) -> set[uuid_module.UUID]:
        """Get the uuids of the record requests published by the downstream application.

        Returns:
            the requested uuids, empty when the relation data could not be read.
        """
        return {request.uuid for request in self.requests or ()}


class DnsAggregatorCharm(ops.CharmBase):
    """Aggregate the DNS record requests of several requirers into a single integration."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.dns_record_provider = dns_record.DNSRecordProvides(self, DOWNSTREAM_RELATION_NAME)
        self.dns_record_provider_mixin = dns_record.DNSRecordProvides(self, MIXIN_RELATION_NAME)
        self.dns_record_requirer = dns_record.DNSRecordRequires(self, UPSTREAM_RELATION_NAME)

        for event in (
            self.on.install,
            self.on.start,
            self.on.upgrade_charm,
            self.on.config_changed,
            self.on.leader_elected,
            self.on.update_status,
            self.on.secret_changed,
        ):
            self.framework.observe(event, self._on_event)
        for relation_name in (
            DOWNSTREAM_RELATION_NAME,
            MIXIN_RELATION_NAME,
            UPSTREAM_RELATION_NAME,
        ):
            endpoint = self.on[relation_name]
            for relation_event in (
                endpoint.relation_created,
                endpoint.relation_joined,
                endpoint.relation_changed,
                endpoint.relation_departed,
                endpoint.relation_broken,
            ):
                self.framework.observe(relation_event, self._on_event)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)

    def _on_event(self, _: ops.EventBase) -> None:
        """Handle any event by reconciling the whole state of the relations."""
        self.reconcile()

    def _on_collect_unit_status(self, _: ops.CollectStatusEvent) -> None:
        """Handle the collect unit status event."""
        downstream_relations = self.dns_record_provider.relations
        if len(downstream_relations) > 1:
            self.unit.status = ops.BlockedStatus(
                f"Got {len(downstream_relations)} {DOWNSTREAM_RELATION_NAME} integrations, "
                "only one is supported"
            )
            return
        if self._upstream_relation() is None:
            self.unit.status = ops.BlockedStatus(
                f"Waiting for a {UPSTREAM_RELATION_NAME} integration"
            )
            return
        if not downstream_relations:
            self.unit.status = ops.BlockedStatus(
                f"Waiting for a {DOWNSTREAM_RELATION_NAME} integration"
            )
            return
        self.unit.status = ops.ActiveStatus()

    def reconcile(self) -> None:
        """Forward the DNS record requests upstream and the responses downstream.

        The whole state of every relation is read and republished on each call, so that
        the outcome only depends on the current relation data and never on the event
        that triggered the reconciliation.
        """
        if not self.unit.is_leader():
            return

        downstream_relations = self.dns_record_provider.relations
        if len(downstream_relations) > 1:
            logger.error(
                "Got %s %s integrations, only one is supported: skipping the reconciliation",
                len(downstream_relations),
                DOWNSTREAM_RELATION_NAME,
            )
            return
        main_relation = downstream_relations[0] if downstream_relations else None
        main = (
            self._read_downstream(self.dns_record_provider, main_relation)
            if main_relation is not None
            else None
        )
        downstreams = ([main] if main is not None else []) + [
            self._read_downstream(self.dns_record_provider_mixin, relation)
            # The mixin relations are ordered by relation id so that the aggregation is
            # stable across reconciliations.
            for relation in sorted(self.dns_record_provider_mixin.relations, key=lambda r: r.id)
        ]
        upstream = self._upstream_relation()

        self._publish_upstream(upstream, downstreams, main)
        self._publish_downstream(upstream, downstreams, main)

    def _upstream_relation(self) -> ops.Relation | None:
        """Get the relation with the upstream DNS provider.

        Returns:
            the upstream relation, or None when there is none. Juju caps the endpoint to
            a single relation, so more than one is reported as an error and ignored.
        """
        relations = self.dns_record_requirer.relations
        if len(relations) > 1:
            logger.error(
                "Got %s %s integrations, only one is supported",
                len(relations),
                UPSTREAM_RELATION_NAME,
            )
            return None
        return relations[0] if relations else None

    @staticmethod
    def _read_downstream(
        endpoint: dns_record.DNSRecordProvides, relation: ops.Relation
    ) -> Downstream:
        """Read the record requests published by a downstream relation.

        Args:
            endpoint: the object handling the endpoint the relation is on.
            relation: the downstream relation to read.

        Returns:
            the downstream relation and its record requests.
        """
        requests = endpoint.get_dns_entries(relation)
        if requests is None:
            logger.warning("Could not read the relation data of relation %s", relation.id)
        return Downstream(endpoint, relation, requests)

    def _publish_upstream(
        self,
        upstream: ops.Relation | None,
        downstreams: list[Downstream],
        main: Downstream | None,
    ) -> None:
        """Publish the aggregated record requests and ddns data to the DNS provider.

        Args:
            upstream: the relation with the DNS provider, or None when there is none.
            downstreams: the downstream relations and their record requests.
            main: the main downstream relation, or None when there is none.
        """
        if upstream is None:
            return

        if any(downstream.requests is None for downstream in downstreams):
            # Publishing a partial list would withdraw the missing requests from the DNS
            # provider, so the previously published ones are left untouched instead.
            logger.warning(
                "Some downstream relation data could not be read, "
                "not publishing a partial list of record requests"
            )
        else:
            requests: dict[uuid_module.UUID, dns_record.RecordRequest] = {}
            for downstream in downstreams:
                for request in downstream.requests or ():
                    requests.setdefault(request.uuid, request)
            self.dns_record_requirer.update_dns_entries(list(requests.values()), upstream)

        if main is not None and main.requests is None:
            # The relation data of the main downstream requirer could not be read, so
            # the addresses it declares are unknown.
            logger.warning(
                "The relation data of the main downstream could not be read, "
                "not publishing its ddns addresses"
            )
            return

        addresses = self._ddns_addresses(main)
        if not addresses:
            # An empty ddns-addresses field tells the DNS provider to fall back to the
            # ingress addresses of its requirer, which is this charm rather than the
            # downstream requirer the allocated domain belongs to. The previously
            # published addresses are left untouched instead.
            logger.warning("No ddns address to publish to the DNS provider")
            return
        self.dns_record_requirer.update_ddns_addresses(addresses, upstream)

    def _publish_downstream(
        self,
        upstream: ops.Relation | None,
        downstreams: list[Downstream],
        main: Downstream | None,
    ) -> None:
        """Dispatch the responses of the DNS provider to the downstream relations.

        Args:
            upstream: the relation with the DNS provider, or None when there is none.
            downstreams: the downstream relations and their record requests.
            main: the main downstream relation, or None when there is none.
        """
        responses = (
            self.dns_record_requirer.get_dns_entries(upstream) if upstream is not None else []
        )
        if responses is None:
            # Withdrawing every response would clear the status of the requests that the
            # DNS provider already answered, so the previously published ones are left
            # untouched instead.
            logger.warning(
                "The relation data of the DNS provider could not be read, "
                "not dispatching its responses"
            )
            return

        for downstream in downstreams:
            if downstream.requests is None:
                # The requested uuids are unknown, so the responses can't be dispatched.
                continue
            uuids = downstream.uuids
            downstream.endpoint.update_dns_entries(
                [response for response in responses if response.uuid in uuids],
                downstream.relation,
            )

        if main is not None:
            domain = (
                self.dns_record_requirer.get_ddns_domain(upstream)
                if upstream is not None
                else None
            )
            self.dns_record_provider.update_ddns_domain(domain, main.relation)

    def _ddns_addresses(self, main: Downstream | None) -> set[IPAddress]:
        """Get the addresses the domain allocated to the main downstream should point at.

        The addresses declared by the downstream requirer are forwarded as they are.
        When it declares none, the ingress addresses juju set on the relation are
        forwarded on its behalf.

        Args:
            main: the main downstream relation, or None when there is none.

        Returns:
            the addresses to declare to the DNS provider.
        """
        if main is None:
            return set()

        declared = self.dns_record_provider.get_ddns_addresses(main.relation)
        if declared:
            return declared

        addresses: set[IPAddress] = set()
        for unit in main.relation.units:
            address = main.relation.data[unit].get(INGRESS_ADDRESS_FIELD, "").strip()
            if not address:
                continue
            try:
                addresses.add(ipaddress.ip_address(address))
            except ValueError:
                logger.warning(
                    "Ignoring the %s %s of %s: not an IP address",
                    INGRESS_ADDRESS_FIELD,
                    address,
                    unit.name,
                )
        return addresses


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsAggregatorCharm)
