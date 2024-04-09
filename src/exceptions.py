# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Exceptions used by the bind charm."""


class BlockableError(Exception):
    """Exception raised when something fails while interacting with workload.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the SynapseWorkloadError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg
