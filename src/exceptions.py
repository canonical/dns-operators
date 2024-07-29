# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions used by the bind charm."""


class SnapError(Exception):
    """Exception raised when an action on the snap fails.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the SnapError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class InvalidZoneFileMetadataError(Exception):
    """Exception raised when a zonefile has invalid metadata.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the InvalidZoneFileMetadataError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class EmptyZoneFileMetadataError(Exception):
    """Exception raised when a zonefile has no metadata.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the EmptyZoneFileMetadataError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class DuplicateMetadataEntryError(Exception):
    """Exception raised when a zonefile has metadata with duplicate entries.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the DuplicateMetadataEntryError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class PeerRelationUnavailableError(Exception):
    """Exception raised when the peer relation is unavailable.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the PeerRelationUnavailableError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class PeerRelationNetworkUnavailableError(Exception):
    """Exception raised when the peer relation network is unavailable.

    Attributes:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the PeerRelationNetworkUnavailableError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg
