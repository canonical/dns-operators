#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import typing

import ops
from charms.dns_authority.v0 import dns_authority

from bind import BindService

logger = logging.getLogger(__name__)


class DnsResolverCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = BindService()
        self.dns_authority = dns_authority.DNSAuthorityRequires(self)

        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on.dns_authority_relation_joined, self._reconcile)
        self.framework.observe(self.on.dns_authority_relation_changed, self._reconcile)
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        if not self.dns_authority.is_related():
            event.add_status(ops.BlockedStatus("Needs to be related with an authority charm"))
            return
        relation_data = self.dns_authority.get_relation_data()
        if not relation_data:
            event.add_status(ops.ActiveStatus("DNS authority relation not ready"))
            logger.warning("DNS authority relation could not be retrieved")
            return
        if not relation_data.addresses or not relation_data.zones:
            event.add_status(ops.ActiveStatus("DNS authority relation not ready"))
            logger.warning("DNS authority relation data has no zones or no addresses")
            return
        event.add_status(
            ops.ActiveStatus(
                (
                    f"{len(relation_data.zones)}"
                    f" zone{'e' if len(relation_data.zones) > 1 else ''},"
                    f" {len(relation_data.addresses)}"
                    f" authority address{'es' if len(relation_data.addresses) > 1 else ''}"
                )
            )
        )

    def _reconcile(self, _: ops.HookEvent) -> None:
        """Reconcile loop."""
        data = self.dns_authority.get_relation_data()
        if data and data.addresses and data.zones:
            self.bind.update_config_and_reload(data.zones, [str(a) for a in data.addresses])

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup()

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        self.bind.start()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        self.bind.setup()


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsResolverCharm)
