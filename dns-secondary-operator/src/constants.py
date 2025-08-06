# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing constants to be used in the charm."""

DNS_BIND_PORT = 53
DNS_SNAP_NAME = "charmed-bind"
DNS_CONFIG_DIR = f"/var/snap/{DNS_SNAP_NAME}/common/bind"
DNS_SNAP_SERVICE = "named"
PEER = "dns-secondary-peers"
SNAP_PACKAGES = {
    DNS_SNAP_NAME: {"channel": "edge"},
}
SYSTEMD_SERVICES_PATH = "/etc/systemd/system/"
ZONE_SERVICE_NAME = "service.test"
