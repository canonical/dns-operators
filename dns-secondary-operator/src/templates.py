# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""File containing templates used in the charm."""

import constants

# Let's disable too long lines for templates
# pylint: disable=line-too-long

ZONE_SERVICE = f"""$ORIGIN {constants.ZONE_SERVICE_NAME}.
$TTL 600
@ IN SOA {constants.ZONE_SERVICE_NAME}. mail.{constants.ZONE_SERVICE_NAME}. ( {{serial}} 1d 1h 1h 10m )
@ IN NS localhost.
status IN TXT "ok"
"""

ZONE_APEX_TEMPLATE = """$ORIGIN {zone}.
$TTL 600
@ IN SOA {zone}. mail.{zone}. ( {serial} 1d 1h 1h 10m )
"""

ZONE_APEX_NS_TEMPLATE = "@ IN NS ns{number}.\nns{number} IN A {ip}\n"

ZONE_RECORD_TEMPLATE = "{host_label} {record_class} {record_type} {record_data}\n"

NAMED_CONF_PRIMARY_ZONE_DEF_TEMPLATE = (
    'zone "{name}" IN {{ '
    'type primary; file "{absolute_path}"; allow-update {{ none; }}; '
    "also-notify {{ {zone_transfer_ips} }}; "
    "allow-transfer {{ {zone_transfer_ips} }}; }};\n"
)

NAMED_CONF_SECONDARY_ZONE_DEF_TEMPLATE = (
    'zone "{name}" IN {{ '
    'type secondary; file "{absolute_path}"; '
    "masterfile-format text; "
    "masterfile-style full; "
    "primaries {{ {primary_ips} }}; }};\n"
)

NAMED_CONF_OPTIONS_TEMPLATE = """
options {{
    dnssec-validation no;
    allow-query {{ {allow_query}; }};
    recursion yes;
    allow-recursion {{ {allow_query}; }};
    allow-query-cache {{ {allow_query}; }};
    allow-transfer {{ none; }};
    notify no;
    forwarders {{}};
    {{ {listen_tls} }}
}};
"""

NAMED_CONF_TLS_TEMPATE = """
tls xot {{
    key-file "{{ {key_file} }}";
    cert-file "{{ {cert_file} }}";
    protocols { TLSv1.3; };
    session-tickets no;
}};
"""

NAMED_CONF_LISTEN_TLS = """
    listen-on port 443 tls xot http local-http-server {any;};
    listen-on-v6 port 443 tls xot http local-http-server {any;};
"""

NAMED_CONF_FORWARDER_TEMPLATE = (
    'zone "{zone}" {{ '
    "type forward;"
    "forward only;"
    "forwarders {{ {forwarders_ips} }}; "
    "}};\n"
)

DISPATCH_EVENT_SERVICE = """[Unit]
Description=Dispatch the {event} event on {unit}

[Service]
Type=oneshot
ExecStart=/usr/bin/timeout {timeout} /usr/bin/bash -c '/usr/bin/juju-exec "{unit}" "JUJU_DISPATCH_PATH={event} ./dispatch"'

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_SERVICE_TIMER = """[Unit]
Description=Run {service} weekly
Requires={service}.service

[Timer]
Unit={service}.service
OnCalendar=*-*-* *:0/{interval}
Persistent=true

[Install]
WantedBy=timers.target
"""
