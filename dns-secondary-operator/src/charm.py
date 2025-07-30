#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for dns-secondary."""

import logging
import typing

import ops
from charms.dns_transfer.v0 import dns_transfer

import constants
import events
import exceptions
import topology
from bind import BindService

logger = logging.getLogger(__name__)

STATUS_REQUIRED_INTEGRATION = "Required integration with DNS primary not found"


class PeerRelationUnavailableError(exceptions.DnsSecondaryCharmError):
    """Exception raised when the peer relation is unavailable."""


class PeerRelationNetworkUnavailableError(exceptions.DnsSecondaryCharmError):
    """Exception raised when the peer relation network is unavailable."""


class DnsSecondaryCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = BindService()
        self.topology = topology.TopologyObserver(self, constants.PEER)
        self.dns_transfer = dns_transfer.DNSTransferRequires(self)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(
            self.on["dns-transfer"].relation_joined, self._on_dns_transfer_relation_joined
        )
        self.framework.observe(
            self.on["dns-transfer"].relation_changed, self._on_dns_transfer_relation_changed
        )
        self.framework.observe(self.topology.on.topology_changed, self._on_topology_changed)
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        if not self._has_required_integration():
            event.add_status(ops.BlockedStatus(STATUS_REQUIRED_INTEGRATION))
        event.add_status(ops.ActiveStatus(""))

    def _on_dns_transfer_relation_joined(self, _: ops.RelationJoinedEvent) -> None:
        """Handle changed relation joined event."""
        self._reconcile()

    def _on_dns_transfer_relation_changed(self, _: ops.RelationChangedEvent) -> None:
        """Handle changed relation changed event."""
        self._reconcile()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration event."""
        self._reconcile()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_topology_changed(self, _: topology.TopologyChangedEvent) -> None:
        """Handle topology changed events."""
        self._reconcile()

    def _reconcile(self) -> None:
        """Reconcile the charm."""
        if not self._has_required_integration():
            return

        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup(self.unit.name)
        self.bind.start()

        relation = self.model.get_relation(self.dns_transfer.relation_name)
        data = self.dns_transfer.get_remote_relation_data()
        self.bind.update_config_and_reload(data.zones, [str(a) for a in data.addresses])

        if self.unit.is_leader():
            requirer_addresses = str(self.config["ips"]).split(",")
            requirer_data = dns_transfer.DNSTransferRequirerData(addresses=requirer_addresses)
            self.dns_transfer.update_relation_data(relation, requirer_data)

    def _has_required_integration(self) -> bool:
        """Check if dns_transfer required integration is set.

        Returns:
            true if dns_transfer is set.
        """
        data = self.dns_transfer.get_remote_relation_data()
        if data is None:
            return False
        return True


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsSecondaryCharm)
