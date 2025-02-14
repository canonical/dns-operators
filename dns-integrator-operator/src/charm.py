#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS Integrator Charm."""

import logging
import typing
import hashlib
import uuid

import ops
from charms.bind.v0 import dns_record

logger = logging.getLogger(__name__)


class DnsIntegratorOperatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.dns_record = dns_record.DNSRecordRequires(self)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_config_changed(self, _: ops.ConfigChangedEvent) -> None:
        """Handle changes in configuration by updating the relation databag with the new record requests."""
        self.unit.status = ops.MaintenanceStatus("Configuring charm")
        self._update_relations()
        self.unit.status = ops.ActiveStatus()

    def _update_relations(self) -> None:
        """Update all DNS data for the existing relations."""
        if not self.model.unit.is_leader():
            return
        try:
            for relation in self.model.relations[self.dns_record.relation_name]:
                self.dns_record.update_relation_data(
                    relation, self._get_dns_record_requirer_data()
                )
        except ops.model.ModelError as e:
            logger.error("ERROR while updating relation data: %s", e)

    def _get_dns_record_requirer_data(self) -> dns_record.DNSRecordRequirerData:
        """Get DNS record requirer data."""
        entries = []
        for request in str(self.config["requests"]).split("\n"):
            data = request.split()
            if len(data) != 6:
                continue
            (host_label, domain, ttl, record_class, record_type, record_data) = data
            entry = dns_record.RequirerEntry(
                host_label=host_label,
                domain=domain,
                ttl=int(ttl),
                record_class=record_class,
                record_type=record_type,
                record_data=record_data,
                uuid=self._uuidv4(" ".join(data)),
            )
            entries.append(entry)
        return dns_record.DNSRecordRequirerData(dns_entries=entries)

    def _uuidv4(self, seed: str) -> str:
        """Get stable uuid.

        The goal is to always generate the same UUID for the same record request without
        relying on a database to store them. Without that, the UUID would change anytime
        the config of the charm is changed and all requests would be seen as new ones.

        Args:
            seed: string seed used to create the output

        Returns:
            UUID constructed based on the given seed
        """
        hash = hashlib.sha512(seed.encode())
        hash_num = int.from_bytes(hash.digest(), byteorder='big')
        hash_str = hash.hexdigest()

        # Determine the variant character (8,9,a,b)
        variant_chars = ["8", "9", "a", "b"]
        variant = variant_chars[hash_num % 4]

        # Construct the UUIDv4
        return f"{hash_str[0:8]}-{hash_str[8:12]}-4{hash_str[12:15]}-{variant + hash_str[15:18]}-{hash_str[18:30]}"


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsIntegratorOperatorCharm)  # type: ignore
