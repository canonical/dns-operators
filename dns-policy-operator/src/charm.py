#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS policy charm."""

import datetime
import logging
import typing
import uuid as uuid_module

import ops
from charms.data_platform_libs.v0.data_interfaces import (
    DatabaseCreatedEvent,
    DatabaseEndpointsChangedEvent,
)
from charms.dns_record.v0 import dns_record

import constants
import database
import ddns
import dns_policy
import timer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

# Namespace used to derive the uuid of the records of the automatically allocated
# domains. Those uuids only need to be stable across reconciliations and unique inside
# the relation with the upstream DNS provider, so they are derived from the record
# itself.
DDNS_UUID_NAMESPACE = uuid_module.uuid5(uuid_module.NAMESPACE_DNS, "ddns.dns-policy.charm")


class ReconcileEvent(ops.charm.EventBase):
    """Event representing a periodic reload of the charmed-bind service."""


def _ddns_record_request(record: dns_record.Record) -> dns_record.RecordRequest:
    """Build an approved record request for an automatically allocated domain.

    Args:
        record: the record resolving an automatically allocated domain.

    Returns:
        the record request to submit to the upstream DNS provider.
    """
    return dns_record.RecordRequest(
        uuid=uuid_module.uuid5(
            DDNS_UUID_NAMESPACE,
            " ".join(
                (
                    record.host_label,
                    record.domain,
                    str(record.record_type.value),
                    str(record.record_data),
                )
            ),
        ),
        status=dns_record.Status.APPROVED,
        description="Automatically allocated domain",
        record=record,
    )


class DnsPolicyCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)

        self.on.define_event("reconcile", ReconcileEvent)
        self.dns_policy = dns_policy.DnsPolicyService()
        self._timer = timer.TimerService()
        self._database = database.DatabaseHandler(self, constants.DATABASE_RELATION_NAME)
        self.dns_record_provider = dns_record.DNSRecordProvides(self, "dns-record-provider")
        self.dns_record_requirer = dns_record.DNSRecordRequires(self, "dns-record-requirer")
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        self.framework.observe(
            self._database.database.on.database_created, self._on_database_created
        )
        self.framework.observe(
            self._database.database.on.endpoints_changed, self._on_database_endpoints_changed
        )
        self.framework.observe(self.on.create_reviewer_action, self._on_create_reviewer_action)
        self.framework.observe(self.on.reconcile, self._on_reconcile)
        self.unit.open_port("tcp", 8080)  # dns-policy-app

    def _on_collect_unit_status(self, _: ops.CollectStatusEvent) -> None:
        """Handle collect unit status event."""
        if not self.dns_policy.status():
            self.unit.status = ops.MaintenanceStatus("Workload not yet ready.")
            return
        if not self._database.is_relation_ready():
            self.unit.status = ops.WaitingStatus("Waiting for a database integration.")
            return
        configured_ddns_domain = self._configured_ddns_domain()
        if configured_ddns_domain and not ddns.is_valid_domain(configured_ddns_domain):
            self.unit.status = ops.BlockedStatus(
                f"Invalid ddns-domain configuration: {configured_ddns_domain}"
            )
            return

        self.unit.status = ops.ActiveStatus()

    def _configured_ddns_domain(self) -> str:
        """Get the configured suffix of the automatically allocated domains.

        Returns:
            the normalized `ddns-domain` configuration value, valid or not.
        """
        return ddns.normalize_domain(str(self.config.get("ddns-domain", "")))

    def _ddns_instance(self) -> str | None:
        """Get the identifier of this charm installation, generating it if needed.

        Relation ids are only unique within a single charm installation: they start over
        from scratch in a deployment restored from a backup of the workload database.
        The allocations are therefore scoped to a random identifier, generated once and
        kept in the peer relation for the whole life of the charm, so that a domain
        allocated here can never be handed to the relations of another deployment.

        Returns:
            the identifier of this charm installation, or None when it is not available
            yet.
        """
        relation = self.model.get_relation(constants.PEER_RELATION_NAME)
        if relation is None:
            logger.warning("The peer relation is not ready, no instance identifier available")
            return None

        instance = relation.data[self.app].get(constants.DDNS_INSTANCE_KEY, "")
        if instance:
            return instance
        if not self.unit.is_leader():
            return None

        instance = str(uuid_module.uuid4())
        relation.data[self.app][constants.DDNS_INSTANCE_KEY] = instance
        logger.info("Generated the instance identifier %s", instance)
        return instance

    def _on_reconcile(self, _: ReconcileEvent) -> None:
        """Reconcile incoming requests with the workload."""
        if not self.model.unit.is_leader():
            return

        ddns_domain = self._configured_ddns_domain()
        if ddns_domain and not ddns.is_valid_domain(ddns_domain):
            logger.error("Invalid ddns-domain configuration, skipping the reconciliation")
            return

        relations = self.dns_record_provider.relations
        if not relations:
            logger.debug("Reconciliation: no requirer integrated")
            return

        requests, complete = self._collect_record_requests(relations, ddns_domain)

        token = self.dns_policy.get_api_root_token()
        if complete:
            # This also withdraws from the workload the requests that are gone from the
            # relations, including the ones rejected by the ddns domain reservation.
            self.dns_policy.send_requests(token, requests)
        else:
            logger.warning(
                "Reconciliation: some relation data could not be read, "
                "not submitting a partial list of requests"
            )
        entries: list[dns_record.RecordRequest] = self.dns_policy.get_approved_requests(token)

        if ddns_domain:
            entries.extend(self._reconcile_ddns(token, relations, ddns_domain))
        else:
            self._clear_ddns_domains(relations)

        if not entries:
            logger.debug("Reconciliation: no entry to publish upstream")
            return
        self._publish_upstream(entries)

    def _collect_record_requests(
        self, relations: list[ops.Relation], ddns_domain: str
    ) -> tuple[list[dns_record.RecordRequest], bool]:
        """Collect the record requests of the relations that the policy lets through.

        Args:
            relations: the relations to read the record requests from.
            ddns_domain: the suffix of the automatically allocated domains, empty when
                the feature is disabled.

        Returns:
            the record requests to submit to the workload, and whether every relation
            could be read. An incomplete list must not be submitted, as the workload
            withdraws every request missing from it.
        """
        requests: list[dns_record.RecordRequest] = []
        complete = True
        for relation in relations:
            accepted = self._accepted_record_requests(relation, ddns_domain)
            if accepted is None:
                complete = False
                continue
            requests.extend(accepted)
        return requests, complete

    def _accepted_record_requests(
        self, relation: ops.Relation, ddns_domain: str
    ) -> list[dns_record.RecordRequest] | None:
        """Get the record requests of a relation that the policy lets through.

        While the automatically allocated domain feature is enabled, the ddns domain is
        reserved: any request for it or for one of its subdomains is rejected, so that
        an allocated domain can't be hijacked through a regular record request.

        Args:
            relation: the relation to read the record requests from.
            ddns_domain: the suffix of the automatically allocated domains, empty when
                the feature is disabled.

        Returns:
            the record requests to submit to the workload, or None when the relation
            data could not be read.
        """
        record_requests = self.dns_record_provider.get_dns_entries(relation)
        if record_requests is None:
            return None
        if not ddns_domain:
            return record_requests

        accepted = []
        for record_request in record_requests:
            record = record_request.record
            name = ddns.fqdn(record.host_label, record.domain) if record is not None else ""
            if name and ddns.is_within(name, ddns_domain):
                logger.warning(
                    "Rejecting the request %s of relation %s: %s is reserved for the "
                    "automatically allocated domains",
                    record_request.uuid,
                    relation.id,
                    name,
                )
                continue
            accepted.append(record_request)
        return accepted

    def _clear_ddns_domains(self, relations: list[ops.Relation]) -> None:
        """Withdraw any previously allocated domain from the relations.

        Args:
            relations: the relations to withdraw the allocated domains from.
        """
        for relation in relations:
            self.dns_record_provider.update_ddns_domain(None, relation)

    def _reconcile_ddns(
        self, token: str, relations: list[ops.Relation], ddns_domain: str
    ) -> list[dns_record.RecordRequest]:
        """Allocate, publish and resolve the automatically allocated domains.

        Args:
            token: root token for the workload API.
            relations: the relations to allocate a domain for.
            ddns_domain: the suffix of the automatically allocated domains.

        Returns:
            the record requests resolving the allocated domains, to be submitted to the
            upstream DNS provider.
        """
        instance = self._ddns_instance()
        if instance is None:
            logger.error("No instance identifier available, skipping the domain allocation")
            return []

        labels = self.dns_policy.allocate_ddns_labels(token, instance, [r.id for r in relations])

        record_requests: list[dns_record.RecordRequest] = []
        for relation in relations:
            label = labels.get(relation.id)
            if label is None:
                logger.error("No domain allocated for the relation %s", relation.id)
                continue

            domain = f"{label}.{ddns_domain}"
            self.dns_record_provider.update_ddns_domain(domain, relation)

            addresses = self._ddns_addresses(relation)
            if not addresses:
                logger.warning(
                    "No address to point the domain %s of relation %s at",
                    domain,
                    relation.id,
                )
                continue
            record_requests.extend(
                _ddns_record_request(record) for record in ddns.records(domain, addresses)
            )
        return record_requests

    def _ddns_addresses(self, relation: ops.Relation) -> list[str]:
        """Get the addresses the automatically allocated domain of a relation resolves to.

        The addresses declared by the requirer take precedence over the ingress addresses
        set by juju, as the latter may be private addresses behind a DNAT.

        Args:
            relation: the relation to get the addresses of.

        Returns:
            the IP addresses the allocated domain resolves to.
        """
        declared = self.dns_record_provider.get_ddns_addresses(relation)
        if declared:
            return declared

        addresses: list[str] = []
        for unit in sorted(relation.units, key=lambda unit: unit.name):
            address = relation.data[unit].get("ingress-address", "").strip()
            if not address or address in addresses:
                continue
            try:
                ddns.record_type(address)
            except ValueError:
                logger.warning(
                    "Ignoring the ingress-address %s of %s: not an IP address",
                    address,
                    unit.name,
                )
                continue
            addresses.append(address)
        return addresses

    def _publish_upstream(self, entries: list[dns_record.RecordRequest]) -> None:
        """Publish record requests to the upstream DNS provider.

        Args:
            entries: the record requests to publish.

        Raises:
            TooManyRelatedAppsError: Raised when related to multiple providers
        """
        try:
            relation = self.model.get_relation(self.dns_record_requirer.relation_name)
            if relation is not None:
                self.dns_record_requirer.update_dns_entries(entries, relation)
            else:
                # Logging as error as this should not happen (as we're a subordinate charm)
                logger.error("%s is not ready !", self.dns_record_requirer.relation_name)
        except ops.TooManyRelatedAppsError:
            # Logging as error as this should not happen
            logger.error("Got multiple %s integrations !", self.dns_record_requirer.relation_name)
            raise

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration."""
        self.unit.status = ops.MaintenanceStatus("Configuring workload")
        self.dns_policy.configure(
            dns_policy.DnsPolicyConfig.from_charm(self, self._database.get_relation_data())
        )

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start event."""

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install event."""
        self.unit.status = ops.MaintenanceStatus("Preparing dns-policy-app")
        self._ddns_instance()
        self.dns_policy.setup()
        self._timer.start(
            self.unit.name,
            "reconcile",
            constants.RECONCILE_TIMER_TIMEOUT,
            constants.RECONCILE_TIMER_INTERVAL,
        )
        logger.info(
            "Started reconcile timer at %s, interval of %s",
            datetime.datetime.now(),
            constants.RECONCILE_TIMER_INTERVAL,
        )

    def _on_database_created(self, _: DatabaseCreatedEvent) -> None:
        """Handle database created."""
        self._handle_database_endpoint_changes()

    def _on_database_endpoints_changed(self, _: DatabaseEndpointsChangedEvent) -> None:
        """Handle endpoints change."""
        self._handle_database_endpoint_changes()

    def _handle_database_endpoint_changes(self) -> None:
        """Handle a database endpoint change."""
        self.unit.status = ops.MaintenanceStatus("Preparing database")
        self.dns_policy.configure(
            dns_policy.DnsPolicyConfig.from_charm(self, self._database.get_relation_data())
        )
        self.dns_policy.command("migrate")

    def _on_create_reviewer_action(self, event: ops.charm.ActionEvent) -> None:
        """Handle the create reviewer ActionEvent.

        Args:
            event: Event triggering this action handler.
        """
        try:
            event.set_results(
                {
                    "result": self.dns_policy.command(
                        (
                            f"create_reviewer {event.params['username']} "
                            f"{event.params['email']} --generate_password"
                        ),
                    )
                }
            )
        except dns_policy.CommandError as e:
            logger.error("Create reviewer failed: %s", e)
            event.fail(f"Create reviewer failed: {e}")


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsPolicyCharm)
