#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import pathlib
import string
import subprocess  # nosec
import time
import typing

import ops
from charms.bind.v0 import dns_record
from charms.dns_authority.v0 import dns_authority
from charms.dns_transfer.v0.dns_transfer import (
    DNSTransferProviderData,
    DNSTransferProvides,
    TransportSecurity,
)

import constants
import dns_data
import events
import topology
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
        self.dns_record = dns_record.DNSRecordProvides(self)
        self.dns_authority = dns_authority.DNSAuthorityProvides(self)
        self.dns_transfer = DNSTransferProvides(self)
        self.topology = topology.TopologyObserver(self, constants.PEER)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(self.on.dns_record_relation_changed, self._reconcile)
        self.framework.observe(self.on.dns_authority_relation_joined, self._reconcile)
        self.framework.observe(self.on.dns_transfer_relation_changed, self._reconcile)
        self.framework.observe(self.topology.on.topology_changed, self._reconcile)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on.reload_bind, self._reconcile)
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        try:
            t = self.topology.current()
            if t.is_current_unit_active:
                event.add_status(ops.ActiveStatus("active"))
            else:
                event.add_status(ops.ActiveStatus())
        except topology.TopologyUnavailableError:
            event.add_status(ops.WaitingStatus("Topology is not available"))
        config_validation = self._validate_config()
        if not config_validation[0]:
            event.add_status(ops.BlockedStatus(config_validation[1]))
            return
        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            event.add_status(ops.BlockedStatus("Non valid DNS requests"))
            return
        self.bind.collect_status(event, relation_data)

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup(self.unit.name, self.config)

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        self.bind.start()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        self.bind.setup(self.unit.name, self.config)

    def _check_and_may_become_active(self, t: topology.Topology) -> bool:
        """Check the active unit status and may become active if need be.

        Args:
            t: Topology of the current deployment

        Returns:
            True if the charm is effectively the new active unit.
        """
        relation = self.model.get_relation(constants.PEER)
        assert relation is not None  # nosec
        if not t.active_unit_ip:
            relation.data[self.app].update({"active-unit": str(t.current_unit_ip)})
            return True

        status = self._dig_query(
            f"@{t.active_unit_ip} service.{constants.ZONE_SERVICE_NAME} TXT +short",
            retry=True,
            wait=1,
        )
        if status != "ok":
            relation.data[self.app].update({"active-unit": str(t.current_unit_ip)})
            return True
        return False

    def _dig_query(self, cmd: str, retry: bool = False, wait: int = 5) -> str:
        """Query a DnsEntry with dig.

        This function was created for simplicity's sake. If we need to make more DNS requests
        in the future, we should revisit it by employing a python library.

        Args:
            cmd: The dig command to perform
            retry: If the dig request should be retried
            wait: duration in seconds to wait between retries

        Returns: the result of the DNS query
        """
        result: str = ""
        retry = False
        for _ in range(5):
            try:
                result = str(
                    subprocess.run(
                        ["dig"] + cmd.split(" "),  # nosec
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                ).strip()
            except subprocess.CalledProcessError as exc:
                logger.warning("%s", exc)
                result = ""
            if result != "" or not retry:
                break
            time.sleep(wait)

        return result

    def _get_remote_relation_data(self) -> dns_record.DNSRecordProviderData | None:
        """Get the dns_record remote relation data.

        This function is used to get performance statistics on the remote relation data retrieval.

        Returns:
            the dns_record remote relation data
        """
        start_time = time.time_ns()
        relation_data = self.dns_record.get_remote_relation_data()
        logger.debug(
            "Relation data retrieval duration (ms): %s", (time.time_ns() - start_time) / 1e6
        )
        return relation_data

    def _validate_config(self) -> tuple[bool, str]:
        """Check config.

        Returns:
            A tuple expressing if the config is valid and an error message if not.
        """
        mailbox_config = str(self.config.get("mailbox", "")).strip()
        if mailbox_config == "":
            return (False, "Mailbox should not be empty")

        # The list of metacharacters considered here is stronger than the RFC
        # We have chosen that list to simplify the logic for now.
        # https://www.ietf.org/rfc/rfc2142.txt
        metacharacters: str = string.punctuation + string.whitespace
        for char in metacharacters:
            if char in mailbox_config:
                return (False, f"Mailbox should not contain '{char}'")

        return (True, "")

    def _reconcile(self, _: ops.HookEvent) -> None:  # noqa: C901
        """Reconciles."""
        # Retrieve the current topology of units
        try:
            t = self.topology.current()
        except topology.TopologyUnavailableError as err:
            logger.info("Could not retrieve network topology: %s", err)
            return

        # If we're the leader and not active, check that the active unit is doing well
        if self.unit.is_leader() and not t.is_current_unit_active:
            self._check_and_may_become_active(t)

        # verify config before continuing
        if not self._validate_config()[0]:
            return

        try:
            relation_data = self.dns_record.get_remote_relation_data()
        except KeyError as err:
            # If we can't get the relation data, we stop here the reconcile loop
            # If the issue comes from the fact that the controller is not joinable,
            # better is to continue with the current state rather than crashing later.
            logger.info("Relation error: %s", err)
            return

        # Update our workload configuration based on relation data and topology
        try:
            # Load the last valid state
            last_valid_state = dns_data.load_state(
                pathlib.Path(constants.DNS_CONFIG_DIR, "state.json").read_text(encoding="utf-8")
            )
        except FileNotFoundError:
            # If we can't load the previous state,
            # we assume that we need to regenerate the configuration
            last_valid_state = {}

        secondary_transfer_ips = []
        for relation in self.model.relations[self.dns_transfer.relation_name]:
            dns_secondary_data = self.dns_transfer.get_remote_relation_data(relation)
            secondary_transfer_ips.extend(dns_secondary_data.addresses)

        if dns_data.has_changed(relation_data, t, last_valid_state):
            self.bind.update_zonefiles_and_reload(
                relation_data, t, self.config, secondary_transfer_ips
            )

        if self.unit.is_leader():
            # Update dns_record relation's data
            dns_record_provider_data = dns_data.create_dns_record_provider_data(relation_data)
            self.dns_record.update_remote_relation_data(dns_record_provider_data)

            # Update dns_record authority's data
            ips = t.standby_units_ip or t.units_ip
            zones = dns_data.dns_record_relations_data_to_zones(relation_data)
            data = dns_authority.DNSAuthorityRelationData(
                addresses=ips, zones=[zone.domain for zone in zones]
            )
            self.dns_authority.update_relation_data(data)

            # Update dns_transfer relation's data
            data = {
                "addresses": t.standby_units_ip or t.units_ip,
                "transport": TransportSecurity.TCP,
                "zones": [zone.domain for zone in zones],
            }
            provider_data = DNSTransferProviderData.model_validate(data)
            for relation in self.model.relations[self.dns_transfer.relation_name]:
                self.dns_transfer.update_relation_data(relation, provider_data)


if __name__ == "__main__":  # pragma: nocover
    ops.main(BindCharm)
