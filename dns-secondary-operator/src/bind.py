# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bind charm business logic."""

import logging
import pathlib

from charms.operator_libs_linux.v2 import snap

import constants
import templates

logger = logging.getLogger(__name__)


class BindService:
    """Bind service class."""

    def reload(self, force_start: bool) -> None:
        """Reload the charmed-bind service.

        Args:
            force_start: start the service even if it was inactive
        """
        logger.debug("Reloading charmed bind")
        cache = snap.SnapCache()
        charmed_bind = cache[constants.DNS_SNAP_NAME]
        charmed_bind_service = charmed_bind.services[constants.DNS_SNAP_SERVICE]
        if charmed_bind_service["active"] or force_start:
            charmed_bind.restart(reload=True)

    def start(self) -> None:
        """Start the charmed-bind service."""
        cache = snap.SnapCache()
        charmed_bind = cache[constants.DNS_SNAP_NAME]
        charmed_bind.start()

    def stop(self) -> None:
        """Stop the charmed-bind service."""
        cache = snap.SnapCache()
        charmed_bind = cache[constants.DNS_SNAP_NAME]
        charmed_bind.stop()

    def setup(self) -> None:
        """Prepare the machine."""
        self._install_snap_package(
            snap_name=constants.DNS_SNAP_NAME,
            snap_channel=constants.SNAP_PACKAGES[constants.DNS_SNAP_NAME]["channel"],
        )
        # We need to put the service zone in place so we call
        # the following with an empty relation and topology.
        self.update_config_and_reload()

    def _write_file(self, path: pathlib.Path, content: str) -> None:
        """Write a file to the filesystem.

        This function exists to be easily mocked during unit tests.

        Args:
            path: path to the file
            content: content of the file
        """
        pathlib.Path(path).write_text(
            content,
            encoding="utf-8",
        )

    def update_config_and_reload(
        self, zones: list[str] | None = None, ips: list[str] | None = None
    ) -> None:
        """Update BIND's configuration and reload the service.

        Args:
            zones (list[str] | None): Optional list of DNS zones.
            ips (list[str] | None): Optional list of IP addresses.
        """
        if zones is None:
            zones = []
        if ips is None:
            ips = []

        # Write the named.conf.local file
        self._write_file(
            pathlib.Path(constants.DNS_CONFIG_DIR) / "named.conf.local",
            self._generate_named_conf_local(zones, ips),
        )

        # Write the named.conf.options file
        self._write_file(
            pathlib.Path(constants.DNS_CONFIG_DIR) / "named.conf.options",
            self._generate_named_conf_options(),
        )

        # Reload charmed-bind config (only if already started).
        # When stopped, we assume this was on purpose.
        # We can be here following a regular reload-bind event
        # and we don't want to interfere with another operation.
        self.reload(force_start=False)

    def _install_snap_package(
        self, snap_name: str, snap_channel: str, refresh: bool = False
    ) -> None:
        """Installs snap package.

        Args:
            snap_name: the snap package to install
            snap_channel: the snap package channel
            refresh: whether to refresh the snap if it's already present.
        """
        snap_cache = snap.SnapCache()
        snap_package = snap_cache[snap_name]

        if not snap_package.present or refresh:
            snap_package.ensure(snap.SnapState.Latest, channel=snap_channel)

    def _generate_named_conf_options(self) -> str:
        """Generate the content of `named.conf.options`.

        Returns:
            The content of `named.conf.options`
        """
        content: str = ""
        content += templates.NAMED_CONF_OPTIONS_TEMPLATE.format(
            allow_query="0.0.0.0/0",
        )
        return content

    def _generate_named_conf_local(self, zones: list[str], ips: list[str]) -> str:
        """Generate the content of `named.conf.local`.

        Returns:
            The content of `named.conf.local`
        """
        # It's good practice to include rfc1918
        content: str = f'include "{constants.DNS_CONFIG_DIR}/zones.rfc1918";\n'
        # Include a zone specifically used for some services tests
        primary_ips = "; ".join(ips) + ";"
        content += templates.NAMED_CONF_SECONDARY_ZONE_DEF_TEMPLATE.format(
            name=f"{constants.ZONE_SERVICE_NAME}",
            absolute_path=f"{constants.DNS_CONFIG_DIR}/db.{constants.ZONE_SERVICE_NAME}",
            primary_ips=primary_ips,
        )
        # Configure zone transfer requests to fetch zones from the primary DNS
        for zone in zones:
            if zone.strip() == "":
                continue
            content += templates.NAMED_CONF_SECONDARY_ZONE_DEF_TEMPLATE.format(
                name=f"{zone}",
                absolute_path=f"{constants.DNS_CONFIG_DIR}/db.{zone}",
                primary_ips=primary_ips,
            )
        return content
