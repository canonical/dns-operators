#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import typing

import ops
from charms.bind.v0.dns_record import DNSRecordProvides

from bind import BindService

logger = logging.getLogger(__name__)


class BindCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = BindService()
        self.dns_record = DNSRecordProvides(self)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(
            self.on.dns_record_relation_changed, self._on_dns_record_relation_changed
        )

    def _on_dns_record_relation_changed(self, _: ops.HookEvent) -> None:
        if not (rrd := self.dns_record.get_remote_relation_data()):
            logger.info(
                "No relation data could be retrieved from %s", self.dns_record.relation_name
            )
            return
        self.unit.status = ops.MaintenanceStatus("Handling new relation requests")
        rpd = self.bind.handle_new_relation_data(rrd[0])
        relation = self.model.get_relation(self.dns_record.relation_name)
        self.dns_record.update_relation_data(relation, rpd)
        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration."""
        self.unit.status = ops.ActiveStatus()

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.prepare()
        self.unit.status = ops.ActiveStatus()

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        self.bind.start()
        self.unit.status = ops.ActiveStatus()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        self.bind.prepare()
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(BindCharm)
