# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS transfer library unit tests"""

import json

import ops
from ops import testing

from charms.dns_transfer.v0 import dns_transfer

REQUIRER_METADATA = """
name: dns-transfer-secondary
requires:
  dns-transfer:
    interface: dns-transfer
"""

PROVIDER_METADATA = """
name: dns-transfer-primary
provides:
  dns-transfer:
    interface: dns-transfer
"""


class DNSTransferRequirerCharm(ops.CharmBase):
    """Class for requirer charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_transfer = dns_transfer.DNSTransferRequires(self)
        self.framework.observe(self.on["dns-transfer"].relation_changed, self._record_event)
        self.framework.observe(self.on.config_changed, self._reconcile)

    def _record_event(self, event: ops.EventBase) -> None:
        """Record emitted event in the event list.

        Args:
            event: event.
        """
        # mypy warns us that we can import different types of events doing that.
        # We know mypy, we know.
        self.events.append(event)  # type: ignore # pylint: disable=no-member

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile charm."""
        print("Reconcile")
        # self.dns_transfer.update_relation_data()


class DNSTransferProviderCharm(ops.CharmBase):
    """Class for provider charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_transfer = dns_transfer.DNSTransferProvides(self)
        self.framework.observe(self.on["dns-transfer"].relation_changed, self._record_event)
        self.framework.observe(self.on.config_changed, self._reconcile)

    def _record_event(self, event: ops.EventBase) -> None:
        """Record emitted event in the event list.

        Args:
            event: event.
        """
        # mypy warns us that we can import different types of events doing that.
        # We know mypy, we know.
        self.events.append(event)  # type: ignore # pylint: disable=no-member

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile charm."""
        print("Reconcile")
        # self.dns_transfer.update_relation_data()


def test_requirer_get_relation_data():
    """
    arrange: given a requirer charm.
    act: add the relation data.
    assert: the relation data matches the one provided.
    """
    ctx = testing.Context(
        DNSTransferRequirerCharm,
        meta={
            "name": "dns-transfer-secondary",
            "provides": {"dns-transfer": {"interface": "dns-transfer"}},
        },
    )
    rel = testing.Relation(
        endpoint="dns-transfer",
        interface="dns-transfer",
        remote_app_name="primary",
        remote_app_data={
            "addresses": json.dumps(["10.10.10.10"]),
            "zones": json.dumps(["example.com"]),
            "transport": json.dumps("tls"),
        },
    )
    state = testing.State(relations={rel})

    with ctx(ctx.on.start(), state) as manager:
        assert (
            manager.charm.dns_transfer.get_remote_relation_data()
            == dns_transfer.DNSTransferProviderData(
                addresses=["10.10.10.10"],  # type: ignore[list-item]
                transport="tls",  # type: ignore[arg-type]
                remote_hostname=None,
                zones=["example.com"],
            )
        )
