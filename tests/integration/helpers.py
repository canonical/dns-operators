#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for the integration tests."""

import random
import string
import tempfile

import ops
from pytest_operator.plugin import OpsTest


class ExecutionError(Exception):
    """Exception raised when execution fails.

    Attrs:
        msg (str): Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the ExecutionError exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


def _generate_random_filename(length: int = 24, extension: str = "") -> str:
    """Generate a random filename.

    Args:
        length: length of the generated name
        extension: extension of the generated name

    Returns:
        the generated name
    """
    characters = string.ascii_letters + string.digits
    # Disabling sec checking here since we're not looking
    # to generate something cryptographically secure
    random_string = "".join(random.choice(characters) for _ in range(length))  # nosec
    if extension:
        if "." in extension:
            pieces = extension.split(".")
            last_extension = pieces[-1]
            extension = last_extension
        return f"{random_string}.{extension}"
    return random_string


async def run_command_on_unit(ops_test: OpsTest, unit_name: str, command: str) -> str:
    """Run a command on a specific unit.

    Args:
        ops_test: The ops test framework instance
        unit_name: The name of the unit to run the command on
        command: The command to run

    Returns:
        the command output if it succeeds, otherwise raises an exception.

    Raises:
        ExecutionError: if the command was not successful
    """
    complete_command = ["exec", "--unit", unit_name, "--", *command.split()]
    return_code, stdout, _ = await ops_test.juju(*complete_command)
    if return_code != 0:
        raise ExecutionError(
            f"Expected command {command} to succeed instead it failed: {return_code}"
        )
    return stdout


# pylint: disable=too-many-arguments
async def push_to_workload(
    ops_test: OpsTest,
    unit: ops.model.Unit,
    source: str,
    destination: str,
    user: str = "root",
    group: str = "root",
    mode: str = "644",
) -> None:
    """Push a source file to the workload.

    Args:
        ops_test: The ops test framework instance
        unit: The unit to push the file to
        source: the content of the file
        destination: the path of the file on the unit
        user: the user that owns the file
        group: the group that owns the file
        mode: the mode of the file
    """
    _, temp_path = tempfile.mkstemp()
    with open(temp_path, "w", encoding="utf-8") as fd:
        fd.writelines(source)

    temp_filename_on_workload = _generate_random_filename()
    # unit does have scp_to
    await unit.scp_to(source=temp_path, destination=temp_filename_on_workload)  # type: ignore
    mv_cmd = f"mv /home/ubuntu/{temp_filename_on_workload} {destination}"
    await run_command_on_unit(ops_test, unit.name, mv_cmd)
    chown_cmd = f"chown {user}:{group} {destination}"
    await run_command_on_unit(ops_test, unit.name, chown_cmd)
    chmod_cmd = f"chmod {mode} {destination}"
    await run_command_on_unit(ops_test, unit.name, chmod_cmd)
