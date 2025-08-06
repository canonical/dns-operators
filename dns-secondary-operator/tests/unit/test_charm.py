# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests."""

from pathlib import Path
from unittest.mock import MagicMock

from ops import testing
from pytest import MonkeyPatch, raises
from scenario.errors import UncaughtCharmError

import bind
import constants
from charm import STATUS_REQUIRED_INTEGRATION, DnsSecondaryCharm

from .conftest import PRIMARY_ADDRESS, PRIMARY_ZONE, PUBLIC_IPS


def test_config_changed(base_state: dict):
    """
    arrange: prepare dns-secondary charm.
    act: run config_changed.
    assert: status is blocked because there is no integration.
    """
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=DnsSecondaryCharm,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(STATUS_REQUIRED_INTEGRATION)


# pylint: disable=too-many-positional-arguments
def test_config_changed_with_primary(
    base_state: dict,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    dns_transfer_relation,
):
    """
    arrange: prepare dns-secondary charm with ips set in config.
    act: run config_changed.
    assert: status is active, relation data (primary and zone) is set in named.conf.local
        and public ips defined in configuration is set in the dns_transfer relation.
    """
    monkeypatch.setattr(constants, "DNS_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(bind.BindService, "reload", MagicMock())
    monkeypatch.setattr(bind.BindService, "start", MagicMock())
    monkeypatch.setattr(bind.BindService, "setup", MagicMock())
    base_state["relations"].append(dns_transfer_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=DnsSecondaryCharm,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.ActiveStatus("1 zones, 1 primary addresses")
    conf_path = tmp_path / "named.conf.local"
    assert conf_path.exists()
    content = conf_path.read_text()
    assert f"primaries {{ {PRIMARY_ADDRESS}; }}" in content
    assert f'db.{PRIMARY_ZONE}"' in content
    assert out.get_relation(dns_transfer_relation.id).local_app_data == {
        "addresses": f'["{PUBLIC_IPS}"]'
    }


def test_config_changed_with_snap_error(
    base_state: dict,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    dns_transfer_relation,
):
    """
    arrange: prepare dns-secondary charm and mock setup to raise an error.
    act: run config_changed.
    assert: error is raised and start not called.
    """
    monkeypatch.setattr(constants, "DNS_CONFIG_DIR", str(tmp_path))
    error_message = "Failed to setup service"
    error = RuntimeError(error_message)
    monkeypatch.setattr(bind.BindService, "setup", MagicMock(side_effect=error))
    start_mock = MagicMock()
    monkeypatch.setattr(bind.BindService, "start", start_mock)

    base_state["relations"].append(dns_transfer_relation)
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=DnsSecondaryCharm,
    )

    with raises(UncaughtCharmError) as e:
        _ = context.run(context.on.config_changed(), state)

    assert isinstance(e.value.__cause__, RuntimeError)
    assert error_message in str(e.value.__cause__)
    start_mock.assert_not_called()
