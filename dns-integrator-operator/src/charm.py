#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS Integrator Charm."""

import logging
import typing

import ops
from charms.dns_record.v0 import dns_record

logger = logging.getLogger(__name__)


class DnsIntegratorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(
            self.on["dns_record"].relation_joined, self._on_dns_record_relation_joined
        )

    def _on_dns_record_relation_joined(self, _: ops.RelationJoinedEvent) -> None:
        """Handle dns_record relation joined."""
        self._update_relations()

    def _on_start(self, _: ops.StartEvent) -> None:
        """Handle start.

        This hook is here to display some status after installation via collect_status().
        """

    def _on_collect_status(self, _: ops.CollectStatusEvent) -> None:
        """Handle collect status event."""
        if str(self.config["requests"]) == "":
            self.unit.status = ops.BlockedStatus("Waiting for some configuration")
            return

        has_integration = False
        for __ in self.model.relations[self.dns_record.relation_name]:
            has_integration = True
            break
        if not has_integration:
            self.unit.status = ops.BlockedStatus("Waiting for integration")
            return

        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changes in configuration by updating the relation databag."""
        self.unit.status = ops.MaintenanceStatus("Configuring charm")
        self._update_relations()

    def _update_relations(self) -> None:
        """Update all DNS data for the existing relations.

        Raises:
            ModelError: if not able to update relation data.
        """
        if not self.model.unit.is_leader():
            return
        try:
            for relation in self.model.relations[self.dns_record.relation_name]:
                self.dns_record.update_relation_data(relation, self._get_dns_record_data())
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)
            raise

    def _get_dns_record_data(self) -> list[dns_record.RecordRequest]:
        """Get DNS record requirer data."""
        entries = []
        for request in str(self.config["requests"]).split("\n"):
            try:
                entries.append(self.dns_record.create_record_request(request))
            except dns_record.CreateRecordRequestError:
                logger.error("Invalid entry ignored: '%s'", request)
                continue
        return entries


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsIntegratorCharm)  # type: ignore
