# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for the domain names."""

import re

from django.core.exceptions import ValidationError

DOMAIN_MAX_LENGTH = 253
# Underscores are allowed, as in the `_acme-challenge` service labels
_DOMAIN_LABEL_PATTERN = re.compile(r"^(?!-)[a-z0-9_-]{1,63}(?<!-)$")


def normalize_domain(domain):
    """Normalize a domain name."""
    return str(domain).strip().strip(".").lower()


def fqdn(host_label, domain):
    """Build the fully qualified domain name of a record."""
    host_label = normalize_domain(host_label)
    domain = normalize_domain(domain)
    if host_label in ("", "@"):
        return domain
    if not domain:
        return host_label
    return f"{host_label}.{domain}"


def is_within(name, domain):
    """Check whether a domain name is a domain or one of its subdomains."""
    return name == domain or name.endswith(f".{domain}")


def validate_domain(value):
    """Validate a domain name.

    Raises:
        ValidationError: when the value is not a valid domain name.
    """
    domain = normalize_domain(value)
    if not domain:
        raise ValidationError("The domain is empty")
    if len(domain) > DOMAIN_MAX_LENGTH:
        raise ValidationError(
            f"The domain is {len(domain)} characters long, "
            f"it must be at most {DOMAIN_MAX_LENGTH} characters"
        )
    for label in domain.split("."):
        if not _DOMAIN_LABEL_PATTERN.match(label):
            raise ValidationError(f"The domain label {label!r} is not a valid domain label")
