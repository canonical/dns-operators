# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

# pylint: disable=import-error,consider-using-with,no-member,too-few-public-methods

"""This code should be loaded into any-charm which is used for integration tests."""

import logging
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
        dns_entry = RequirerEntry(
            domain="dns.test",
            host_label="admin",
            ttl=600,
            record_class="IN",
            record_type="A",
            record_data="42.42.42.42",
            uuid=uuid.uuid4(),
        )
        dns_record_requirer_data = DNSRecordRequirerData(
            dns_entries=[dns_entry],
            service_account="fakeserviceaccount",
        )
        return dns_record_requirer_data

    def _on_dns_record_relation_joined(self, event: ops.HookEvent) -> None:
        """Handle dns_record relation joined.

        Args:
            event: dns_record relation joined event
        """
        self.dns_record.update_relation_data(event.relation, self._test_record_data())
