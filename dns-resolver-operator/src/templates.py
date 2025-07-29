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

NAMED_CONF_PRIMARY_ZONE_DEF_TEMPLATE = (
    'zone "{name}" IN {{ '
    'type primary; file "{absolute_path}"; allow-update {{ none; }}; '
    "also-notify {{ {zone_transfer_ips} }}; "
    "allow-transfer {{ {zone_transfer_ips} }}; }};\n"
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
}};
"""

NAMED_CONF_FORWARDER_TEMPLATE = (
    'zone "{zone}" {{ '
    "type forward;"
    "forward only;"
    "forwarders {{ {forwarders_ips} }}; "
    "}};\n"
)
