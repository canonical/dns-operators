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
CERTS_DIR_PATH = constants.DNS_CONFIG_DIR
PRIVATE_KEY_NAME = "dns-secondary.key"
CERTIFICATE_NAME = "dns-secondary.pem"
STORED_CERTIFICATE_PATH = pathlib.Path(f"{CERTS_DIR_PATH}/{CERTIFICATE_NAME}")
STORED_PRIVATE_KEY_PATH = pathlib.Path(f"{CERTS_DIR_PATH}/{PRIVATE_KEY_NAME}")


def is_certificate_update_required(certificate: Certificate) -> bool:
    """Check certificate.

    Args:
        certificate (Certificate): certificate.

    Returns:
        if update is required.
    """
    return get_existing_certificate() != certificate


def is_private_key_update_required(private_key: PrivateKey) -> bool:
    """Check private key.

    Args:
        private_key (PrivateKey): private key.

    Returns:
        if update is required.
    """
    return get_existing_private_key() != private_key


def get_existing_certificate() -> typing.Optional[Certificate]:
    """Get existing certificate.

    Returns:
        certificate or None.
    """
    return get_stored_certificate() if certificate_is_stored() else None


def get_existing_private_key() -> typing.Optional[PrivateKey]:
    """Get existing private key.

    Returns:
        private key or None.
    """
    return get_stored_private_key() if private_key_is_stored() else None


def get_stored_certificate() -> Certificate:
    """Get stored certificate.

    Returns:
        Certificate stored in machine.
    """
    cert_string = str(STORED_CERTIFICATE_PATH.read_text("utf-8"))
    return Certificate.from_string(cert_string)


def get_stored_private_key() -> PrivateKey:
    """Get stored key.

    Returns:
        Private key stored in machine.
    """
    key_string = str(
        STORED_PRIVATE_KEY_PATH.read_text(
            "utf-8",
        )
    )
    return PrivateKey.from_string(key_string)


def certificate_is_stored() -> bool:
    """Check certificate is stored.

    Returns:
        if is stored or not.
    """
    return STORED_CERTIFICATE_PATH.exists()


def private_key_is_stored() -> bool:
    """Check private key is stored.

    Returns:
        if is stored or not.
    """
    return STORED_PRIVATE_KEY_PATH.exists()


def store_certificate(certificate: Certificate) -> None:
    """Store certificate in workload.

    Args:
        certificate: certificate.
    """
    pathlib.Path(STORED_CERTIFICATE_PATH).write_text(
        str(certificate),
        encoding="utf-8",
    )
    logger.info("Pushed certificate pushed to workload")


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


def delete_certificate() -> None:
    """Delete certificate from workload container."""
    if certificate_is_stored():
        STORED_CERTIFICATE_PATH.unlink(missing_ok=True)
        logger.info("Removed certificate from workload")


def delete_private_key() -> None:
    """Delete private key from workload container."""
    if private_key_is_stored():
        STORED_PRIVATE_KEY_PATH.unlink(missing_ok=True)
        logger.info("Removed private key from workload")
