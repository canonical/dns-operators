#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for dns-secondary."""

import logging
import subprocess  # nosec
import time
import typing

import ops
from charms.dns_transfer.v0 import dns_transfer

import constants
import events
import exceptions
import models
from bind import BindService

logger = logging.getLogger(__name__)


class PeerRelationUnavailableError(exceptions.DnsSecondaryCharmError):
    """Exception raised when the peer relation is unavailable."""


class PeerRelationNetworkUnavailableError(exceptions.DnsSecondaryCharmError):
    """Exception raised when the peer relation network is unavailable."""


class DnsSecondaryCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = BindService()
        self.dns_transfer = dns_transfer.DNSTransferRequires(self)

        self.on.define_event("reload_bind", events.ReloadBindEvent)

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(
            self.on["dns-transfer"].relation_joined, self._on_dns_transfer_relation_joined
        )
        self.framework.observe(
            self.on["dns-transfer"].relation_changed, self._on_dns_transfer_relation_changed
        )
        self.unit.open_port("tcp", 53)  # Bind DNS
        self.unit.open_port("udp", 53)  # Bind DNS

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        if not self._has_required_integration():
            event.add_status(ops.BlockedStatus("Required integration with DNS primary not found"))
        event.add_status(ops.ActiveStatus(""))

    def _on_dns_transfer_relation_joined(self, _: ops.RelationJoinedEvent) -> None:
        """Handle changed relation joined event."""
        self._reconcile()

    def _on_dns_transfer_relation_changed(self, _: ops.RelationChangedEvent) -> None:
        """Handle changed relation changed event."""
        self._reconcile()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changed configuration event."""
        self._reconcile()

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _reconcile(self) -> None:
        """Reconcile the charm."""
        if not self._has_required_integration():
            return
        self.unit.status = ops.MaintenanceStatus("Preparing bind")
        self.bind.setup(self.unit.name)
        self.bind.start()
        relation = self.model.get_relation(self.dns_transfer.relation_name)
        data = self.dns_transfer.get_remote_relation_data()
        self.bind.update_config_and_reload(data.zones, [str(a) for a in data.addresses])
        requirer_addresses = str(self.config["ips"]).split(",")
        requirer_data = dns_transfer.DNSTransferRequirerData(addresses=requirer_addresses)
        self.dns_transfer.update_relation_data(relation, requirer_data)

    def _has_required_integration(self) -> bool:
        """Check if dns_transfer required integration is set.

        Returns:
            true if dns_transfer is set.
        """
        data = self.dns_transfer.get_remote_relation_data()
        if data is None:
            return False
        return True

    def _check_and_may_become_active(self, topology: models.Topology) -> bool:
        """Check the active unit status and may become active if need be.

        Args:
            topology: Topology of the current deployment

        Returns:
            True if the charm is effectively the new active unit.
        """
        relation = self.model.get_relation(constants.PEER)
        assert relation is not None  # nosec
        if not topology.active_unit_ip:
            relation.data[self.app].update({"active-unit": str(topology.current_unit_ip)})
            return True

        status = self._dig_query(
            f"@{topology.active_unit_ip} service.{constants.ZONE_SERVICE_NAME} TXT +short",
            retry=True,
            wait=1,
        )
        if status != "ok":
            relation.data[self.app].update({"active-unit": str(topology.current_unit_ip)})
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

    def _topology(self) -> models.Topology:
        """Create a network topology of the current deployment.

        Returns:
            A topology of the current deployment

        Raises:
            PeerRelationUnavailableError: when the peer relation does not exist
            PeerRelationNetworkUnavailableError: when the network property does not exist
        """
        start_time = time.time_ns()
        relation = self.model.get_relation(constants.PEER)
        binding = self.model.get_binding(constants.PEER)
        if not relation or not binding:
            raise PeerRelationUnavailableError(
                "Peer relation not available when trying to get topology."
            )
        if binding.network is None:
            raise PeerRelationNetworkUnavailableError(
                "Peer relation network not available when trying to get unit IP."
            )

        units_ip: list[str] = [
            unit_data.get("private-address", "")
            for _, unit_data in relation.data.items()
            if unit_data.get("private-address", "") != ""
        ]

        current_unit_ip = str(binding.network.bind_address)
        active_unit_ip = relation.data[self.app].get("active-unit")

        logger.debug("active_unit_ip: %s", active_unit_ip)
        logger.debug("current_unit_ip: %s", current_unit_ip)
        logger.debug("units_ip: %s", units_ip)
        logger.debug("topology retrieval duration (ms): %s", (time.time_ns() - start_time) / 1e6)

        return models.Topology(
            active_unit_ip=active_unit_ip,
            units_ip=units_ip,
            standby_units_ip=[ip for ip in units_ip if ip != active_unit_ip],
            current_unit_ip=current_unit_ip,
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsSecondaryCharm)
