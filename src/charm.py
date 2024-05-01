#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import os
import pathlib
import shutil
import tempfile
import typing
import time

import ops
from charms.bind.v0.dns_record import DNSRecordProvides, DNSRecordRequirerData, RequirerEntry

import constants
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

    def to_bind_zones(self, rrd: DNSRecordRequirerData) -> typing.Dict[str, str]:
        """Convert DNSRecordRequirerData to zone files."""
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

    def mkdir(self, path: str) -> None:
        """Create a directory."""
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    def push(self, path: pathlib.Path, source: str) -> None:
        """Pushes a file to the unit.

        Args:
            path: The path of the file
            source: The contents of the file to be pushed
        """
        with open(path, "w", encoding="utf-8") as write_file:
            write_file.write(source)
            logger.info("Pushed file %s", path)

    def _generate_named_conf_local(self, zones: typing.List[str]) -> str:
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

    def _on_dns_record_relation_changed(self, _: ops.HookEvent) -> None:
        rrd = self.dns_record.get_remote_relation_data()
        zones = self.to_bind_zones(rrd)
        logger.debug("ZONES: %s", zones)
        tempdir = tempfile.mkdtemp(dir=pathlib.Path(constants.STAGING_AREA))
        for name, content in zones.items():
            self.push(pathlib.Path(tempdir, f"db.{name}"), content)
        self.push(
            pathlib.Path(tempdir, "named.conf.local"), self._generate_named_conf_local(list(zones))
        )
        for file_name in os.listdir(tempdir):
            shutil.move(
                pathlib.Path(tempdir, file_name), pathlib.Path(constants.DNS_CONFIG_DIR, file_name)
            )
        self.bind.reload()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration."""
        # assert self.dns_record
        # for relation in self.model.relations[self.dns_record.relation_name]:
        #     pass
        #     # self.dns_record.update_relation_data(relation, self._get_dns_record_data())
        #     logger.debug(relation)
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
