# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""This code should be loaded into any-charm which is used for integration tests."""

def install(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        import pip
        pip.main(['install', package])
    finally:
        globals()[package] = importlib.import_module(package)

install("pydantic")

import logging

from any_charm_base import AnyCharmBase
from dns_record import DNSRecordRequires, DNSRecordRequestProcessed

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
        self.framework.observe(self.dns_record.on.dns_record_request_processed, self._handler)

    def _handler(self, events: DNSRecordRequestProcessed) -> None:
        logger.debug(events.msg)
