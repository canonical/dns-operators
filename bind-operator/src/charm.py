#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import pathlib
import time
import typing

import ops
from charms.bind.v0 import dns_record
from charms.dns_authority.v0 import dns_authority

import bind
import constants
import dns_data
import events
import topology

logger = logging.getLogger(__name__)


class BindCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = bind.BindService()
        self.topology = topology.TopologyService(self, constants.PEER)
        self.dns_record = dns_record.DNSRecordProvides(self)
        self.dns_authority = dns_authority.DNSAuthorityProvides(self)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(
            self.on.dns_record_relation_changed, self._on_dns_record_relation_changed
        )
        self.framework.observe(
            self.on.dns_authority_relation_joined, self._on_dns_authority_relation_joined
        )
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on.reload_bind, self._on_reload_bind)
        self.framework.observe(self.topology.on.topology_changed, self._on_topology_changed)
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_topology_changed(self, _: topology.TopologyChangedEvent) -> None:
        """Handle topology changed events."""
        self._reconcile()

    def _on_reload_bind(self, _: events.ReloadBindEvent) -> None:
        """Handle periodic reload bind event."""
        self._reconcile()

    def _on_dns_authority_relation_joined(self, _: ops.RelationChangedEvent) -> None:
        """Handle dns_authority relation changed."""
        self._reconcile()

    def _reconcile(self) -> None:
        """Update dns authority relation."""
        try:
            t = self.topology.dump()
        except topology.TopologyUnavailableError:
            return
        ips = t.standby_units_ip or t.units_ip
        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            return
        zones = dns_data.dns_record_relations_data_to_zones(relation_data)
        if self.unit.is_leader():
            data = dns_authority.DNSAuthorityRelationData(
                addresses=ips, zones=[zone.domain for zone in zones]
            )
            self.dns_authority.update_relation_data(data)

        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            return

        # Load the last valid state
        try:
            last_valid_state = dns_data.load_state(
                pathlib.Path(constants.DNS_CONFIG_DIR, "state.json").read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            # If we can't load the previous state,
            # we assume that we need to regenerate the configuration
            return
        if dns_data.has_changed(relation_data, t, last_valid_state):
            self.bind.update_zonefiles_and_reload(relation_data, t)

    def _on_dns_record_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Handle dns_record relation changed.

        Args:
            event: Event triggering the relation changed handler.

        """
        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            return
        self.unit.status = ops.MaintenanceStatus("Handling new relation requests")
        dns_record_provider_data = dns_data.create_dns_record_provider_data(relation_data)
        relation = self.model.get_relation(self.dns_record.relation_name, event.relation.id)
        if self.unit.is_leader():
            self.dns_record.update_relation_data(relation, dns_record_provider_data)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        try:
            if self.topology.dump().is_current_unit_active:
                event.add_status(ops.ActiveStatus("active"))
            else:
                event.add_status(ops.ActiveStatus())
        except topology.TopologyUnavailableError:
            event.add_status(ops.WaitingStatus("Peer relation is not available"))
        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            event.add_status(ops.BlockedStatus("Non valid DNS requests"))
            return
        self.bind.collect_status(event, relation_data)

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration event."""
        self._reconcile()

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup(self.unit.name)

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        self.bind.start()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        self.bind.setup(self.unit.name)

    def _get_remote_relation_data(self) -> dns_record.DNSRecordProviderData | None:
        """Get the dns_record remote relation data.

        This function is used to get performance statistics on the remote relation data retrieval.

        Returns:
            the dns_record remote relation data
        """
        start_time = time.time_ns()
        relation_data = self.dns_record.get_remote_relation_data()
        logger.debug(
            "Relation data retrieval duration (ms): %s", (time.time_ns() - start_time) / 1e6
        )
        return relation_data


if __name__ == "__main__":  # pragma: nocover
    ops.main(BindCharm)
