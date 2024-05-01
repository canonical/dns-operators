# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""This code should be loaded into any-charm which is used for integration tests."""


def install(package):
    """Install."""
    import importlib

    try:
        importlib.import_module(package)
    except ImportError:
        import pip

        pip.main(["install", package])
    finally:
        globals()[package] = importlib.import_module(package)


install("pydantic")

import logging
import uuid

from any_charm_base import AnyCharmBase
from dns_record import (
    DNSRecordRequestProcessed,
    DNSRecordRequirerData,
    DNSRecordRequires,
    RequirerEntry,
)

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
            self.dns_record.on.dns_record_request_processed, self._on_dns_record_request_processed
        )
        # self.framework.observe(
        #     self.dns_record.on.dns_record_relation_changed, self._on_dns_record_relation_changed
        # )
        # self.framework.observe(
        #     self.on.dns_record_relation_changed, self._on_dns_record_relation_changed2
        # )
        self.framework.observe(
            self.on.dns_record_relation_joined, self._on_dns_record_relation_joined
        )

    def _test_record_data(self) -> DNSRecordRequirerData:
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
            service_account="123213123123123123123",
        )
        return dns_record_requirer_data

    def _on_dns_record_relation_joined(self, event) -> None:
        logger.debug("JOINED")
        self.dns_record.update_relation_data(event.relation, self._test_record_data())

    def _on_dns_record_relation_changed2(self, event) -> None:
        logger.debug("CHANGED2")
        self.dns_record.update_relation_data(event.relation, self._test_record_data())

    def _on_dns_record_relation_changed(self, event) -> None:
        logger.debug("CHANGED")
        self.dns_record.update_relation_data(event.relation, self._test_record_data())

    def _on_dns_record_request_processed(self, event: DNSRecordRequestProcessed) -> None:
        logger.debug("PROCESSED")
