# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bind charm business logic."""

import logging
import os
import pathlib
import shutil
import tempfile
import time
import typing

from charms.bind.v0.dns_record import (
    DNSProviderData,
    DNSRecordProviderData,
    DNSRecordRequirerData,
    RequirerEntry,
    Status,
)
from charms.operator_libs_linux.v2 import snap

import constants
import exceptions

logger = logging.getLogger(__name__)


class ReloadError(exceptions.SnapError):
    """Exception raised when unable to reload the service."""


class StartError(exceptions.SnapError):
    """Exception raised when unable to start the service."""


class StopError(exceptions.SnapError):
    """Exception raised when unable to stop the service."""


class InstallError(exceptions.SnapError):
    """Exception raised when unable to install dependencies for the service."""


class BindService:
    """Bind service class."""

    def reload(self) -> None:
        """Reload the charmed-bind service.

        Raises:
            ReloadError: when encountering a SnapError
        """
        try:
            cache = snap.SnapCache()
            charmed_bind = cache[constants.DNS_SNAP_NAME]
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

    def prepare(self) -> None:
        """Prepare the machine."""
        self._install_snap_package(
            snap_name=constants.DNS_SNAP_NAME,
            snap_channel=constants.SNAP_PACKAGES[constants.DNS_SNAP_NAME]["channel"],
        )

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

        except (snap.SnapError, snap.SnapNotFoundError) as e:
            error_msg = f"An exception occurred when installing {snap_name}. Reason: {e}"
            logger.error(error_msg)
            raise InstallError(error_msg) from e

    def _push(self, path: pathlib.Path, source: str) -> None:
        """Pushes a file to the unit.

        Args:
            path: The path of the file
            source: The contents of the file to be pushed
        """
        with open(path, "w", encoding="utf-8") as write_file:
            write_file.write(source)
            logger.info("Pushed file %s", path)

    def _to_bind_zones(self, rrd: DNSRecordRequirerData) -> typing.Dict[str, str]:
        """Convert DNSRecordRequirerData to zone files.

        Args:
            rrd: The input DNSRecordRequirerData

        Returns:
            A dict of zones names as keys with the zones contents as values
        """
        zones_entries: typing.Dict[str, typing.List[RequirerEntry]] = {}
        for entry in rrd.dns_entries:
            if entry.domain not in zones_entries:
                zones_entries[entry.domain] = []
            zones_entries[entry.domain].append(entry)

        zones_content: typing.Dict[str, str] = {}
        for zone, entries in zones_entries.items():
            content: str = (
                f"$ORIGIN {zone}.\n"
                "$TTL 600\n"
                f"@ IN SOA {zone}. mail.{zone}. ( {int(time.time())} 1d 1h 1h 10m )\n"
                "@ IN NS localhost.\n"
            )
            for entry in entries:
                content += (
                    f"{entry.host_label} "
                    f"{entry.record_class} "
                    f"{entry.record_type} "
                    f"{entry.record_data}\n"
                )
            zones_content[zone] = content
        return zones_content

    def _generate_named_conf_local(self, zones: typing.List[str]) -> str:
        """Generate the content of `named.conf.local`.

        Args:
            zones: A list of all the zones names

        Returns:
            The content of `named.conf.local`
        """
        # It's good practice to include rfc1918
        content: str = f'include "{constants.DNS_CONFIG_DIR}/zones.rfc1918";\n'
        for name in zones:
            content += (
                f'zone "{name}" IN {{'
                "type primary;"
                f'file "{constants.DNS_CONFIG_DIR}/db.{name}";'
                "allow-update { none; };"
                "};\n"
            )
        return content

    def handle_new_relation_data(self, rrd: DNSRecordRequirerData) -> DNSRecordProviderData:
        """Handle new relation data.

        Args:
            rrd: The DNSRecordRequirerData from the relation

        Returns:
            A resulting DNSRecordProviderData to put in the relation databag
        """
        zones = self._to_bind_zones(rrd)
        logger.debug("ZONES: %s", zones)
        tempdir = tempfile.mkdtemp()
        for name, content in zones.items():
            self._push(pathlib.Path(tempdir, f"db.{name}"), content)
        self._push(
            pathlib.Path(tempdir, "named.conf.local"), self._generate_named_conf_local(list(zones))
        )
        for file_name in os.listdir(tempdir):
            shutil.move(
                pathlib.Path(tempdir, file_name), pathlib.Path(constants.DNS_CONFIG_DIR, file_name)
            )
        self.reload()
        shutil.rmtree(tempdir)
        statuses = []
        for entry in rrd.dns_entries:
            statuses.append(DNSProviderData(uuid=entry.uuid, status=Status.APPROVED))
        return DNSRecordProviderData(dns_entries=statuses)
