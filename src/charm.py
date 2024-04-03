#!/usr/bin/env python3

# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import typing

import ops

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

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration.

        Args:
            _: event triggering the handler.
        """
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(BindCharm)
