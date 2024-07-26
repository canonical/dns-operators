#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for bind."""

import logging
import subprocess  # nosec
import time
import typing

import ops
from charms.bind.v0.dns_record import DNSRecordProvides

import constants
import events
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
        self.bind = BindService()
        self.dns_record = DNSRecordProvides(self)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        self.framework.observe(
            self.on.dns_record_relation_changed, self._on_dns_record_relation_changed
        )
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on.reload_bind, self._on_reload_bind)
        self.framework.observe(self.on.leader_elected, self._on_leader_elected)
        self.framework.observe(
            self.on[constants.PEER].relation_departed, self._on_peer_relation_departed
        )
        self.peer_relation = self.model.get_relation(constants.PEER)

    def _on_reload_bind(self, _: events.ReloadBindEvent) -> None:
        """Handle periodic reload bind event."""
        try:
            relation_data = self.dns_record.get_remote_relation_data()
        except ValueError as err:
            logger.info("Validation error of the relation data: %s", err)
            return
        if self.bind.has_a_zone_changed(relation_data):
            self.bind.update_zonefiles_and_reload(relation_data)

    def _on_dns_record_relation_changed(self, event: ops.RelationChangedEvent) -> None:
        """Handle dns_record relation changed.

        Args:
            event: Event triggering the relation changed handler.

        """
        try:
            relation_data = self.dns_record.get_remote_relation_data()
        except ValueError as err:
            logger.info("Validation error of the relation data: %s", err)
            return
        self.unit.status = ops.MaintenanceStatus("Handling new relation requests")
        dns_record_provider_data = self.bind.create_dns_record_provider_data(relation_data)
        relation = self.model.get_relation(self.dns_record.relation_name, event.relation.id)
        if self.unit.is_leader():
            self.dns_record.update_relation_data(relation, dns_record_provider_data)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        try:
            if self._is_active_unit():
                event.add_status(ops.ActiveStatus("active"))
        except exceptions.PeerRelationUnavailableError:
            event.add_status(ops.BlockedStatus("Peer relation is not available"))
        try:
            relation_requirer_data = self.dns_record.get_remote_relation_data()
        except ValueError as err:
            logger.info("Validation error of the relation data: %s", err)
            event.add_status(ops.BlockedStatus(f"Validation error of the relation data: {err}"))
            return
        self.bind.collect_status(event, relation_requirer_data)

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

    def _on_leader_elected(self, _: ops.LeaderElectedEvent) -> None:
        """Handle leader-elected event."""
        # We check that we are still the leader when starting to process this event
        if self.unit.is_leader():
            self._become_active()

    def _on_peer_relation_departed(self, _: ops.RelationDepartedEvent) -> None:
        """Handle the peer relation departed event."""
        # We check that we are still the leader when starting to process this event
        if self.unit.is_leader():
            self._become_active()

    def _become_active(self) -> bool:
        """Set the current unit as the active unit of the charm.

        Returns:
            True if the charm is effectively the new active unit.
        """
        active_unit_ip = self._active_unit_ip()

        assert self.peer_relation is not None
        if not active_unit_ip:
            self.peer_relation.data[self.app].update({"active-unit": self._unit_ip()})
            return True

        if active_unit_ip != self._unit_ip():
            status = self._dig_query(
                f"@{active_unit_ip} service.{constants.ZONE_SERVICE_NAME} TXT +short",
                retry=True,
                wait=1,
            )
            if status != "ok":
                self.peer_relation.data[self.app].update({"active-unit": self._unit_ip()})
                return True
            return False

        return True

    async def _dig_query(self, cmd: str, retry: bool = False, wait: int = 5) -> str:
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
            result = str(
                subprocess.run(
                    ["dig"] + cmd.split(" "),  # nosec
                    capture_output=True,
                    text=True,
                    check=True,
                )
            ).strip()
            if result != "" or not retry:
                break
            time.sleep(wait)

        return result

    def _is_active_unit(self) -> bool:
        """Check if the charm is the active unit.

        Returns:
            True if the charm is effectively the active unit.
        """
        return self._active_unit_ip() == self._unit_ip()

    def _active_unit_ip(self) -> str:
        """Get current active unit ip.

        Returns:
            The IP of the active unit

        Raises:
            PeerRelationUnavailableError: when the peer relation does not exist
        """
        if not self.peer_relation:
            raise exceptions.PeerRelationUnavailableError(
                "Peer relation not available when trying to get unit IP."
            )
        return self.peer_relation.data[self.app].get("active-unit", "")

    def _unit_ip(self) -> str:
        """Get current unit ip.

        Returns:
            The IP of the current unit

        Raises:
            PeerRelationUnavailableError: when the peer relation does not exist
            PeerRelationNetworkUnavailableError: when the network property does not exist
        """
        if (binding := self.model.get_binding(constants.PEER)) is not None:
            if (network := binding.network) is not None:
                logger.debug(str(network.bind_address))
                return str(network.bind_address)
            raise exceptions.PeerRelationNetworkUnavailableError(
                "Peer relation network not available when trying to get unit IP."
            )
        raise exceptions.PeerRelationUnavailableError(
            "Peer relation not available when trying to get unit IP."
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(BindCharm)
