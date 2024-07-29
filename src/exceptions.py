# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions used by the bind charm."""


class BindCharmError(Exception):
    """Base exception for the bind charm."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class SnapError(BindCharmError):
    """Exception raised when an action on the snap fails."""


class InvalidZoneFileMetadataError(BindCharmError):
    """Exception raised when a zonefile has invalid metadata."""


class EmptyZoneFileMetadataError(BindCharmError):
    """Exception raised when a zonefile has no metadata."""


class DuplicateMetadataEntryError(BindCharmError):
    """Exception raised when a zonefile has metadata with duplicate entries."""


class PeerRelationUnavailableError(BindCharmError):
    """Exception raised when the peer relation is unavailable."""


class PeerRelationNetworkUnavailableError(BindCharmError):
    """Exception raised when the peer relation network is unavailable."""
