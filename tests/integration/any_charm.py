# Copyright 2024 Canonical Ltd.
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


class AnyCharm(AnyCharmBase):
    """Execute a simple charm to test the relation."""

    def __init__(self, *args, **kwargs):
        """Init function for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
            kwargs: Variable list of positional keyword arguments passed to the parent constructor.
        """
        super().__init__(*args, **kwargs)
        self.dns_record = DNSRecordRequires(self)
        self.framework.observe(
            self.on.dns_record_relation_joined, self._on_dns_record_relation_joined
        )

    def _test_record_data(self) -> DNSRecordRequirerData:
        """Create test record data.

        Returns:
            test record data
        """
        # We read the dns entries from a known json file
        # It's okay to write to /tmp for these tests, so # nosec is used
        json_entries = json.loads(
            pathlib.Path("/tmp/dns_entries.json").read_text(encoding="utf-8")  # nosec
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

    def _on_dns_record_relation_joined(self, event: ops.RelationEvent) -> None:
        """Handle dns_record relation joined.

        Args:
            event: dns_record relation joined event
        """
        self.dns_record.update_relation_data(event.relation, self._test_record_data())
