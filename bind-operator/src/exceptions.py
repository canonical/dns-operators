# Copyright 2025 Canonical Ltd.
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
