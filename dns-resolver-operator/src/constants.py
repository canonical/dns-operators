# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing constants to be used in the charm."""

DNS_SNAP_NAME = "charmed-bind"
DNS_SNAP_SERVICE = "named"
SNAP_PACKAGES = {
    DNS_SNAP_NAME: {"channel": "edge"},
}
DNS_CONFIG_DIR = f"/var/snap/{DNS_SNAP_NAME}/common/bind"

ZONE_SERVICE_NAME = "service.test"
