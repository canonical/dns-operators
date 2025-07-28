# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""DNS transfer library unit tests"""

import ipaddress

import ops
import yaml
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

REQUIRER_UPDATE_DATA_ADDRESSES = "10.10.10.30"
PROVIDER_UPDATE_DATA_ADDRESSES = "10.10.10.20"
PROVIDER_UPDATE_DATA_ZONES = "first.example.com"


class DNSTransferRequirerCharm(ops.CharmBase):
    """Class for requirer charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_transfer = dns_transfer.DNSTransferRequires(self)
        self.framework.observe(self.on.config_changed, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile charm."""
        relation = self.model.get_relation(self.dns_transfer.relation_name)
        requirer_data = dns_transfer.DNSTransferRequirerData(
            addresses=[ipaddress.IPv4Address(REQUIRER_UPDATE_DATA_ADDRESSES)]
        )
        if relation:
            self.dns_transfer.update_relation_data(relation, requirer_data)


class DNSTransferProviderCharm(ops.CharmBase):
    """Class for provider charm testing."""

    def __init__(self, *args):
        """Init method for the class.

        Args:
            args: Variable list of positional arguments passed to the parent constructor.
        """
        super().__init__(*args)
        self.dns_transfer = dns_transfer.DNSTransferProvides(self)
        self.framework.observe(self.on.config_changed, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        """Reconcile charm."""
        provider_data = dns_transfer.DNSTransferProviderData(
            addresses=[ipaddress.IPv4Address(PROVIDER_UPDATE_DATA_ADDRESSES)],
            transport=dns_transfer.TransportSecurity.TLS,
            remote_hostname=None,
            zones=[PROVIDER_UPDATE_DATA_ZONES],
        )
        for relation in self.model.relations[self.dns_transfer.relation_name]:
            self.dns_transfer.update_relation_data(relation, provider_data)


def test_dns_transfer_requirer_get_relation_data(dns_transfer_requirer_relation):
    """
    arrange: given a requirer charm.
    act: add the relation data.
    assert: the relation data matches the one provided.
    """
    ctx = testing.Context(
        DNSTransferRequirerCharm,
        meta=yaml.safe_load(REQUIRER_METADATA),
    )
    state = testing.State(relations=[dns_transfer_requirer_relation])

    with ctx(ctx.on.start(), state) as manager:
        assert (
            manager.charm.dns_transfer.get_remote_relation_data()
            == dns_transfer.DNSTransferProviderData(
                addresses=[ipaddress.IPv4Address("10.10.10.10")],
                transport=dns_transfer.TransportSecurity.TLS,
                remote_hostname=None,
                zones=["example.com"],
            )
        )


def test_dns_transfer_requirer_update_relation_data(dns_transfer_requirer_relation):
    """
    arrange: given a requirer charm.
    act: add the relation data and trigger a change via config-changed event.
    assert: the local relation data matches the one provided.
    """
    ctx = testing.Context(
        DNSTransferRequirerCharm,
        meta=yaml.safe_load(REQUIRER_METADATA),
    )
    state = testing.State(relations=[dns_transfer_requirer_relation], leader=True)

    with ctx(ctx.on.config_changed(), state) as manager:
        state_out = manager.run()
        relation = next(
            r for r in state_out.relations if r.endpoint == dns_transfer.DEFAULT_RELATION_NAME
        )
        assert relation.local_app_data == {"addresses": f'["{REQUIRER_UPDATE_DATA_ADDRESSES}"]'}


def test_dns_transfer_provider_get_relation_data(dns_transfer_provider_relation):
    """
    arrange: given a provider charm.
    act: add the relation data.
    assert: the relation data matches the one provided.
    """
    ctx = testing.Context(
        DNSTransferProviderCharm,
        meta=yaml.safe_load(PROVIDER_METADATA),
    )
    state = testing.State(relations=[dns_transfer_provider_relation])

    with ctx(ctx.on.start(), state) as manager:
        relation = manager.charm.model.relations["dns-transfer"][0]
        assert manager.charm.dns_transfer.get_remote_relation_data(
            relation
        ) == dns_transfer.DNSTransferRequirerData(
            addresses=[ipaddress.IPv4Address("10.10.10.20")],
        )


def test_dns_transfer_provider_update_relation_data(dns_transfer_provider_relation):
    """
    arrange: given a provider charm.
    act: add the relation data and trigger a change via config-changed event.
    assert: the local relation data matches the one provided.
    """
    ctx = testing.Context(
        DNSTransferProviderCharm,
        meta=yaml.safe_load(PROVIDER_METADATA),
    )
    state = testing.State(relations=[dns_transfer_provider_relation], leader=True)

    with ctx(ctx.on.config_changed(), state) as manager:
        state_out = manager.run()
        relation = next(
            r for r in state_out.relations if r.endpoint == dns_transfer.DEFAULT_RELATION_NAME
        )
        assert relation.local_app_data == {
            "addresses": f'["{PROVIDER_UPDATE_DATA_ADDRESSES}"]',
            "zones": f'["{PROVIDER_UPDATE_DATA_ZONES}"]',
            "transport": '"tls"',
            "remote_hostname": "null",
        }
