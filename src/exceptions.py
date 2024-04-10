# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions used by the bind charm."""


class BlockableError(Exception):
    """Exception raised when something fails and the charm should be put in a blocked state.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the BlockableError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg
