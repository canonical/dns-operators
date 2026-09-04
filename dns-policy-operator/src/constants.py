# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing constants to be used in the charm."""

DNS_SNAP_NAME = "charmed-dns-policy"
DNS_SNAP_SERVICES = ["nginx", "gunicorn"]
SNAP_PACKAGES = {
    DNS_SNAP_NAME: {"channel": "edge"},
}
DNS_CONFIG_DIR = f"/var/snap/{DNS_SNAP_NAME}/common/app"

PEER_RELATION_NAME = "dns-policy-peers"
DATABASE_RELATION_NAME = "database"
DATABASE_NAME = "dnspolicy"
SYSTEMD_SERVICES_PATH = "/etc/systemd/system/"
DNS_POLICY_API_HOST = "127.0.0.1"
DNS_POLICY_API_BASE = f"http://{DNS_POLICY_API_HOST}:8080/api"
DNS_POLICY_ENDPOINTS_BASE = f"{DNS_POLICY_API_BASE}/requests"
DNS_POLICY_DDNS_ALLOCATIONS_ENDPOINT = f"{DNS_POLICY_API_BASE}/ddns/allocations"
DDNS_RECORD_TTL = 600
DDNS_INSTANCE_KEY = "ddns-instance"

RECONCILE_TIMER_INTERVAL = 1  # in minutes
RECONCILE_TIMER_TIMEOUT = "30s"
