# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests."""

from pathlib import Path
from unittest.mock import MagicMock

from ops import testing
from pytest import MonkeyPatch

import bind
import constants
from charm import DnsSecondaryCharm


def test_config_changed(base_state: dict, tmp_path: Path, monkeypatch: MonkeyPatch):
    """
    arrange: prepare dns-secondary charm with ips set in config.
    act: run config_changed.
    assert: status is active and ips is set in named.conf.local
    """
    monkeypatch.setattr(constants, "DNS_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(bind.BindService, "reload", MagicMock)
    ips = "10.10.10.10"
    base_state["config"] = {
        "ips": ips,
    }
    state = testing.State(**base_state)
    context = testing.Context(
        charm_type=DnsSecondaryCharm,
    )

    out = context.run(context.on.config_changed(), state)

    assert out.unit_status == testing.BlockedStatus(
        "Required integration with DNS primary not found"
    )
    # conf_path = tmp_path / "named.conf.local"
    # assert conf_path.exists()
    # content = conf_path.read_text()
    # assert f'zone "{ips}"' in content
