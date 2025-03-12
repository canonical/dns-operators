# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""App charm business logic."""

import logging
import pathlib

from charms.operator_libs_linux.v1 import systemd

import constants
import templates

logger = logging.getLogger(__name__)


class TimerError(Exception):
    """Base exception for the bind charm."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class InvalidIntervalError(TimerError):
    """Exception raised when am interval is invalid."""


# Even with only one method, this service could be reused so it makes sense for it to exist
# pylint: disable=too-few-public-methods
class TimerService:
    """Timer service class."""

    def start(self, unit_name: str, event_name: str, timeout: str, interval: int) -> None:
        """Install a timer.

        Syntax of time spans:
            https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html

        Args:
            unit_name: Unit name where to start the timer
            event_name: The event to be fired
            timeout: timeout before killing the command
            interval: interval between each execution in minutes (should be between 1 and 59)

        Raises:
            InvalidIntervalError: if the input interval is invalid
        """
        # Check if interval is correct
        if interval < 1 or interval > 59:
            raise InvalidIntervalError(f"Invalid interval: {interval}")
        (
            pathlib.Path(constants.SYSTEMD_SERVICES_PATH) / f"dispatch-{event_name}.service"
        ).write_text(
            templates.DISPATCH_EVENT_SERVICE.format(
                event=event_name,
                timeout=timeout,
                unit=unit_name,
            ),
            encoding="utf-8",
        )
        (
            pathlib.Path(constants.SYSTEMD_SERVICES_PATH) / f"dispatch-{event_name}.timer"
        ).write_text(
            templates.SYSTEMD_SERVICE_TIMER.format(
                interval=interval, service=f"dispatch-{event_name}"
            ),
            encoding="utf-8",
        )
        systemd.service_enable(f"dispatch-{event_name}.timer")
        systemd.service_start(f"dispatch-{event_name}.timer")
