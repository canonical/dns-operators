#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for dns-secondary."""

import logging
import typing

import ops
from charms.dns_transfer.v0 import dns_transfer

import constants
import topology
from bind import BindService

logger = logging.getLogger(__name__)

STATUS_REQUIRED_INTEGRATION = "Needs to be related with a primary charm"


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

        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on["dns-transfer"].relation_joined, self._reconcile)
        self.framework.observe(self.on["dns-transfer"].relation_changed, self._reconcile)
        self.framework.observe(self.topology.on.topology_changed, self._reconcile)
        self.unit.open_port("tcp", constants.DNS_BIND_PORT)  # Bind DNS
        self.unit.open_port("udp", constants.DNS_BIND_PORT)  # Bind DNS

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm."""
        if not self._has_required_integration():
            return

        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup()
        self.bind.start()

        relation = self.model.get_relation(self.dns_transfer.relation_name)
        data = self.dns_transfer.get_remote_relation_data()
        if data and data.addresses and data.zones:
            self.unit.status = ops.MaintenanceStatus("Updating named.conf.local")
            self.bind.write_config_local(data.zones, [str(a) for a in data.addresses])
            self.bind.reload(force_start=True)

        if self.unit.is_leader():
            public_ips = self.topology.dump().public_ips
            if not public_ips:
                logger.debug("Public ips not set, using units ip")
                public_ips = self.topology.dump().units_ip
            requirer_data = dns_transfer.DNSTransferRequirerData(addresses=public_ips)
            self.dns_transfer.update_relation_data(relation, requirer_data)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        if not self._has_required_integration():
            event.add_status(ops.BlockedStatus(STATUS_REQUIRED_INTEGRATION))
        relation_data = self.dns_transfer.get_remote_relation_data()
        if not relation_data:
            event.add_status(ops.ActiveStatus("DNS primary relation not ready"))
            logger.warning("DNS primary relation could not be retrieved")
            return
        if not relation_data.addresses or not relation_data.zones:
            event.add_status(ops.ActiveStatus("DNS primary relation not ready"))
            logger.warning("DNS primary relation data has no zones or no addresses")
            return
        total_zones = len(relation_data.zones)
        total_addresses = len(relation_data.addresses)
        event.add_status(
            ops.ActiveStatus(f"{total_zones} zones, {total_addresses} primary addresses")
        )

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _has_required_integration(self) -> bool:
        """Check if dns_transfer required integration is set.

        Returns:
            true if dns_transfer is set.
        """
        return self.dns_transfer.get_remote_relation_data() is not None


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsSecondaryCharm)
