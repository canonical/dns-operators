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
        """Handle changed configuration."""
        self.unit.status = ops.ActiveStatus()

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        try:
            self.bind.prepare()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        try:
            self.bind.start()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        try:
            self.bind.stop()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        try:
            self.bind.prepare()
            self.unit.status = ops.ActiveStatus()
        except exceptions.BlockableError as e:
            logger.error(e.msg)
            self.unit.status = ops.BlockedStatus(e.msg)


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(BindCharm)
