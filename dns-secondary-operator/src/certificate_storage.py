#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Handler for certificate storage."""

import logging
import pathlib
import typing

from charms.tls_certificates_interface.v4.tls_certificates import (
    Certificate,
    PrivateKey,
)

import constants

logger = logging.getLogger(__name__)

STATUS_REQUIRED_INTEGRATION = "Needs to be related with a primary charm"
PRIVATE_KEY_NAME = "dns-secondary.key"
CERTIFICATE_NAME = "dns-secondary.pem"
STORED_CERTIFICATE_PATH = pathlib.Path(f"{constants.DNS_CONFIG_DIR}/{CERTIFICATE_NAME}")
STORED_PRIVATE_KEY_PATH = pathlib.Path(f"{constants.DNS_CONFIG_DIR}/{PRIVATE_KEY_NAME}")


def _get_stored_certificate() -> typing.Optional[Certificate]:
    """Get stored certificate.

    Returns:
        Certificate stored in machine or None.
    """
    if not STORED_CERTIFICATE_PATH.exists():
        return None
    cert_string = str(STORED_CERTIFICATE_PATH.read_text("utf-8"))
    return Certificate.from_string(cert_string)


def _get_stored_private_key() -> typing.Optional[PrivateKey]:
    """Get stored key or None.

    Returns:
        Private key stored in machine or None.
    """
    if not STORED_PRIVATE_KEY_PATH.exists():
        return None
    key_string = str(
        STORED_PRIVATE_KEY_PATH.read_text(
            "utf-8",
        )
    )
    return PrivateKey.from_string(key_string)


def is_certificate_update_required(certificate: Certificate) -> bool:
    """Check certificate.

    Args:
        certificate (Certificate): certificate.

    Returns:
        if update is required.
    """
    return _get_stored_certificate() != certificate


def is_private_key_update_required(private_key: PrivateKey) -> bool:
    """Check private key.

    Args:
        private_key (PrivateKey): private key.

    Returns:
        if update is required.
    """
    return _get_stored_private_key() != private_key


def store_certificate(certificate: Certificate) -> None:
    """Store certificate in workload.

    Args:
        certificate: certificate.
    """
    pathlib.Path(STORED_CERTIFICATE_PATH).write_text(
        str(certificate),
        encoding="utf-8",
    )
    logger.info("Pushed certificate to workload")


def store_private_key(private_key: PrivateKey) -> None:
    """Store private key in workload.

    Args:
        private_key: private key.
    """
    pathlib.Path(STORED_PRIVATE_KEY_PATH).write_text(
        str(private_key),
        encoding="utf-8",
    )
    logger.info("Pushed private key to workload")


def delete_files() -> None:
    """Delete certificate and private key from workload container."""
    STORED_CERTIFICATE_PATH.unlink(missing_ok=True)
    STORED_PRIVATE_KEY_PATH.unlink(missing_ok=True)
    logger.info("Removed certificate and private key from workload")
