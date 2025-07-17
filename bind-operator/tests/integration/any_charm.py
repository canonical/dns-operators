# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=import-error,consider-using-with,no-member,too-few-public-methods

"""This code should be loaded into any-charm which is used for integration tests."""

import json
import logging
import pathlib
import uuid

import ops
from any_charm_base import AnyCharmBase
from dns_record import DNSRecordRequirerData, DNSRecordRequires, RequirerEntry

logger = logging.getLogger(__name__)


class ReloadDataEvent(ops.charm.EventBase):
    """Event representing a reload-data event."""


class AnyCharm(AnyCharmBase):
    """Execute a simple charm to test the relation."""

    def __init__(self, *args, **kwargs):
        """Init function for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
            kwargs: Variable list of positional keyword arguments passed to the parent constructor.
        """
        super().__init__(*args, **kwargs)
        self.on.define_event("reload_data", ReloadDataEvent)
        self.dns_record = DNSRecordRequires(self, "require-dns-record")
        self.framework.observe(self.on.reload_data, self._on_reload_data)

    def _on_reload_data(self, _: ReloadDataEvent) -> None:
        """Handle reload-data events."""
        relation = self.model.get_relation(self.dns_record.relation_name)
        self.dns_record.update_relation_data(relation, self._test_record_data())

    def _test_record_data(self) -> DNSRecordRequirerData:
        """Create test record data.

        Returns:
            test record data
        """
        # We read the dns entries from a known json file
        json_entries = json.loads(
            pathlib.Path("/srv/dns_entries.json").read_text(encoding="utf-8")
        )

        dns_entries = [
            RequirerEntry(
                domain=e["domain"],
                host_label=e["host_label"],
                ttl=e["ttl"],
                record_class=e["record_class"],
                record_type=e["record_type"],
                record_data=e["record_data"],
                uuid=uuid.uuid4(),
            )
            for e in json_entries
        ]

        dns_record_requirer_data = DNSRecordRequirerData(
            dns_entries=dns_entries,
            service_account="fakeserviceaccount",
        )
        return dns_record_requirer_data
