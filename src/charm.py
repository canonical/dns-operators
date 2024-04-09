#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import typing

import ops

import exceptions
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
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.bind = BindService()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration.

        Args:
            _: event triggering the handler.
        """
        self.unit.status = ops.ActiveStatus()

    def _on_install(self, event: ops.InstallEvent) -> None:
        """Handle install.

        Args:
            event: Event triggering the install handler.
        """
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        try:
            self.bind.prepare()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_start(self, event: ops.StartEvent) -> None:
        """Handle start.

        Args:
            event: Event triggering the start handler.
        """
        try:
            self.bind.start()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_stop(self, event: ops.StopEvent) -> None:
        """Handle stop.

        Args:
            event: Event triggering the stop handler.
        """
        try:
            self.bind.stop()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_upgrade_charm(self, event: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm.

        Args:
            event: Event triggering the upgrade-charm handler.
        """
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        try:
            self.bind.prepare()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(BindCharm)
