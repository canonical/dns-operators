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

    def _on_event(self, _: ops.EventBase) -> None:
        """Handle any event by reconciling the whole state of the relations."""
        self.reconcile()

    def reconcile(self) -> None:
        """Forward the DNS record requests upstream and the responses downstream.

        The whole state of every relation is read and republished on each call, so that
        the outcome only depends on the current relation data and never on the event
        that triggered the reconciliation.
        """
        downstream_relations = self.dns_record_provider.relations
        main = (
            self._read_downstream(self.dns_record_provider, downstream_relations[0])
            if downstream_relations
            else None
        )
        downstreams = ([main] if main is not None else []) + [
            self._read_downstream(self.dns_record_provider_mixin, relation)
            for relation in sorted(self.dns_record_provider_mixin.relations, key=lambda r: r.id)
        ]
        upstream_relations = self.dns_record_requirer.relations
        upstream = upstream_relations[0] if upstream_relations else None

        requests: dict[uuid_module.UUID, dns_record.RecordRequest] = {}
        for downstream in downstreams:
            for request in downstream.requests or ():
                requests.setdefault(request.uuid, request)
        aggregated = sorted(requests.values(), key=lambda request: str(request.uuid))

        responses: list[dns_record.RecordRequest]
        domain: str | None
        if upstream is None or upstream.app is None:
            responses, domain = [], None
        else:
            responses = self.dns_record_requirer.get_dns_entries(upstream) or []
            domain = self.dns_record_requirer.get_ddns_domain(upstream)
        dispatched = [response for response in responses if response.uuid in requests]

        if self.unit.is_leader():
            self._publish_upstream(upstream, aggregated, main)
            self._publish_downstream(downstreams, responses, domain, main)

        if upstream is None:
            self.unit.status = ops.BlockedStatus(
                f"Waiting for a {UPSTREAM_RELATION_NAME} integration"
            )
        elif not downstream_relations:
            self.unit.status = ops.BlockedStatus(
                f"Waiting for a {DOWNSTREAM_RELATION_NAME} integration"
            )
        else:
            self.unit.status = ops.ActiveStatus(
                f"Forwarding {len(aggregated)} request{'' if len(aggregated) == 1 else 's'} "
                f"and {len(dispatched)} response{'' if len(dispatched) == 1 else 's'}"
            )

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
        requests: list[dns_record.RecordRequest],
        main: Downstream | None,
    ) -> None:
        """Publish the aggregated record requests and ddns data to the DNS provider.

        Args:
            upstream: the relation with the DNS provider, or None when there is none.
            requests: the aggregated record requests to forward.
            main: the main downstream relation, or None when there is none.
        """
        if upstream is None:
            return

        self.dns_record_requirer.update_dns_entries(requests, upstream)

        addresses = self._ddns_addresses(main)
        if not addresses:
            # here the ddns-addresses will be the address of dns-aggregator
            # but I think that should be okay
            logger.warning("No ddns address to publish to the DNS provider")
            return
        self.dns_record_requirer.update_ddns_addresses(addresses, upstream)

    def _publish_downstream(
        self,
        downstreams: list[Downstream],
        responses: list[dns_record.RecordRequest],
        domain: str | None,
        main: Downstream | None,
    ) -> None:
        """Dispatch the responses of the DNS provider to the downstream relations.

        Args:
            downstreams: the downstream relations and their record requests.
            responses: the responses published by the DNS provider.
            domain: the domain allocated by the DNS provider, or None when there is none.
            main: the main downstream relation, or None when there is none.
        """
        for downstream in downstreams:
            if downstream.requests is None:
                continue
            uuids = downstream.uuids
            responses_for_downstream = [
                response for response in responses if response.uuid in uuids
            ]
            downstream.endpoint.update_dns_entries(
                sorted(responses_for_downstream, key=lambda response: str(response.uuid)),
                downstream.relation,
            )

        if main is not None:
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
