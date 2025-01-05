#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Custom events for the charm."""

import ops


class ReloadBindEvent(ops.charm.EventBase):
    """Event representing a periodic reload of the charmed-bind service."""
