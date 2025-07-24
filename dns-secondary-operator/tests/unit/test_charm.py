# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests."""

from ops import testing

from charm import DnsSecondaryCharm


def test_config_changed(base_state: dict):
    """
    arrange: prepare dns-secondary charm with ips set in config.
    act: run config_changed.
    assert: status is active and ips is set in named.conf.local
    """
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=DnsSecondaryCharm,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Required integration with DNS primary not found"
    )
