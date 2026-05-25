# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bind charm business logic."""

import logging
import pathlib
import subprocess  # nosec
import time

from charms.operator_libs_linux.v2 import snap

import constants
import exceptions
import templates

logger = logging.getLogger(__name__)


class SnapError(exceptions.DnsResolverCharmError):
    """Exception raised when an action on the snap fails."""


class ReloadError(SnapError):
    """Exception raised when unable to reload the service."""


class StartError(SnapError):
    """Exception raised when unable to start the service."""


class StopError(SnapError):
    """Exception raised when unable to stop the service."""


class InstallError(SnapError):
    """Exception raised when unable to install dependencies for the service."""


class BindService:
    """Bind service class."""

    def reload(self, force_start: bool) -> None:
        """Reload the charmed-bind service.

        Args:
            force_start: start the service even if it was inactive

        Raises:
            ReloadError: when encountering a SnapError
        """
        logger.debug("Reloading charmed bind")
        try:
            cache = snap.SnapCache()
            charmed_bind = cache[constants.DNS_SNAP_NAME]
            charmed_bind_service = charmed_bind.services[constants.DNS_SNAP_SERVICE]
            if charmed_bind_service["active"] or force_start:
                charmed_bind.restart(reload=True)
        except snap.SnapError as e:
            error_msg = (
                f"An exception occurred when reloading {constants.DNS_SNAP_NAME}. Reason: {e}"
            )
            logger.error(error_msg)
            raise ReloadError(error_msg) from e

    def start(self) -> None:
        """Start the charmed-bind service.

        Raises:
            StartError: when encountering a SnapError
        """
        try:
            cache = snap.SnapCache()
            charmed_bind = cache[constants.DNS_SNAP_NAME]
            charmed_bind.start()
        except snap.SnapError as e:
            error_msg = (
                f"An exception occurred when stopping {constants.DNS_SNAP_NAME}. Reason: {e}"
            )
            logger.error(error_msg)
            raise StartError(error_msg) from e

    def stop(self) -> None:
        """Stop the charmed-bind service.

        Raises:
            StopError: when encountering a SnapError
        """
        try:
            cache = snap.SnapCache()
            charmed_bind = cache[constants.DNS_SNAP_NAME]
            charmed_bind.stop()
        except snap.SnapError as e:
            error_msg = (
                f"An exception occurred when stopping {constants.DNS_SNAP_NAME}. Reason: {e}"
            )
            logger.error(error_msg)
            raise StopError(error_msg) from e

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
        """Update bind's config and reload bind.

        Args:
            zones: zones of the related authority servers
            ips: ips of the related authority servers
        """
        if zones is None:
            zones = []
        if ips is None:
            ips = []
        start_time = time.time_ns()
        logger.debug("Starting update of config")

        # Write the service.test file
        self._write_file(
            pathlib.Path(constants.DNS_CONFIG_DIR) / f"db.{constants.ZONE_SERVICE_NAME}",
            templates.ZONE_SERVICE.format(
                serial=int(time.time() / 60),
            ),
        )

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
        logger.debug("Update and reload duration (ms): %s", (time.time_ns() - start_time) / 1e6)

    def _install_snap_package(
        self, snap_name: str, snap_channel: str, refresh: bool = False
    ) -> None:
        """Installs snap package.

        Args:
            snap_name: the snap package to install
            snap_channel: the snap package channel
            refresh: whether to refresh the snap if it's already present.

        Raises:
            InstallError: when encountering a SnapError or a SnapNotFoundError
        """
        try:
            snap_cache = snap.SnapCache()
            snap_package = snap_cache[snap_name]

            if not snap_package.present or refresh:
                snap_package.ensure(snap.SnapState.Latest, channel=snap_channel)
        except (snap.SnapError, snap.SnapNotFoundError, subprocess.CalledProcessError) as e:
            error_msg = f"An exception occurred when installing {snap_name}. Reason: {e}"
            logger.exception(error_msg)
            raise InstallError(error_msg) from e

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
        content += templates.NAMED_CONF_PRIMARY_ZONE_DEF_TEMPLATE.format(
            name=f"{constants.ZONE_SERVICE_NAME}",
            absolute_path=f"{constants.DNS_CONFIG_DIR}/db.{constants.ZONE_SERVICE_NAME}",
            zone_transfer_ips="",
        )
        # Add zones forwarding requests to our authoritative deployment
        for zone in zones:
            if zone.strip() == "":
                continue
            content += templates.NAMED_CONF_FORWARDER_TEMPLATE.format(
                zone=f"{zone}",
                forwarders_ips=";".join(ips) + ";" if ips else "",
            )
        return content
