#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import pathlib
import subprocess  # nosec
import time
import typing

import ops
from charms.bind.v0 import dns_record

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
        self.topology = topology.TopologyObserver(self, constants.PEER)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(
            self.on.dns_record_relation_changed, self._on_dns_record_relation_changed
        )
        self.framework.observe(self.topology.on.topology_changed, self._on_topology_changed)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on.reload_bind, self._on_reload_bind)
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_topology_changed(self, _: topology.TopologyChangedEvent) -> None:
        """Handle topology changed events."""
        self._reconcile()

    def _on_reload_bind(self, _: events.ReloadBindEvent) -> None:
        """Handle periodic reload bind event.

        Reloading is used to take new configuration into account.

        """
        self._reconcile()

    def _on_dns_record_relation_changed(self, _: ops.RelationChangedEvent) -> None:
        """Handle dns_record relation changed."""
        # Checking if we are the leader is also done in reconcile
        # but doing it here avoids some unnecessary computations of reconcile for this case
        if self.unit.is_leader():
            self._reconcile()

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
        relation_data = self._get_remote_relation_data()
        if relation_data is None:
            event.add_status(ops.BlockedStatus("Non valid DNS requests"))
            return
        self.bind.collect_status(event, relation_data)

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration event."""

    def _on_install(self, _: ops.InstallEvent) -> None:
        """Handle install."""
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup(self.unit.name)

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start."""
        self.bind.start()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_upgrade_charm(self, _: ops.UpgradeCharmEvent) -> None:
        """Handle upgrade-charm."""
        self.unit.status = ops.MaintenanceStatus("Upgrading dependencies")
        self.bind.setup(self.unit.name)

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

    def _reconcile(self) -> None:  # noqa: C901
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
        if dns_data.has_changed(relation_data, t, last_valid_state):
            self.bind.update_zonefiles_and_reload(relation_data, t)

        # Update dns_record relation's data if we are the leader
        if self.unit.is_leader():
            dns_record_provider_data = dns_data.create_dns_record_provider_data(relation_data)
            self.dns_record.update_remote_relation_data(dns_record_provider_data)


if __name__ == "__main__":  # pragma: nocover
    ops.main(BindCharm)
