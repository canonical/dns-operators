#!/usr/bin/env python3
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for the integration tests."""

import json
import logging
import pathlib
import random
import string
import tempfile
import time

import jubilant

import constants
import models

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Exception raised when execution fails.

    Attributes:
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


async def run_on_unit(juju: jubilant.Juju, unit_name: str, command: str) -> str:
    """Run a command on a specific unit.

    Args:
        juju: The jubilant Juju instance
        unit_name: The name of the unit to run the command on
        command: The command to run

    Returns:
        the command output if it succeeds

    Raises:
        ExecutionError: if the command was not successful
    """
    try:
        task = juju.exec(command, unit=unit_name)
        return task.stdout
    except Exception as e:
        raise ExecutionError(f"Command {command} failed: {e}") from e


async def push_to_unit(
    *,
    juju: jubilant.Juju,
    unit_name: str,
    source: str,
    destination: str,
    user: str = "root",
    group: str = "root",
    mode: str = "644",
) -> None:
    """Push a source file to the chosen unit.

    Args:
        juju: The jubilant Juju instance
        unit_name: The name of the unit
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
    juju.scp(temp_path, f"{unit_name}:{temp_filename_on_workload}")

    mv_cmd = f"sudo mv -f /home/ubuntu/{temp_filename_on_workload} {destination}"
    await run_on_unit(juju, unit_name, mv_cmd)
    chown_cmd = f"sudo chown {user}:{group} {destination}"
    await run_on_unit(juju, unit_name, chown_cmd)
    chmod_cmd = f"sudo chmod {mode} {destination}"
    await run_on_unit(juju, unit_name, chmod_cmd)


async def dispatch_to_unit(
    juju: jubilant.Juju,
    unit_name: str,
    hook_name: str,
):
    """Dispatch a hook to the chosen unit.

    Args:
        juju: The jubilant Juju instance
        unit_name: The name of the unit
        hook_name: the hook name
    """
    cmd = f"export JUJU_DISPATCH_PATH=hooks/{hook_name}; ./dispatch"
    juju.exec(cmd, unit=unit_name)


async def generate_anycharm_relation(
    app_name: str,
    juju: jubilant.Juju,
    any_charm_name: str,
    dns_entries: list[models.DnsEntry],
    machine: str | None,
):
    """Deploy any-charm with wanted DNS entries config and integrate to bind app.

    Args:
        app_name: Deployed bind-operator app name
        juju: The jubilant Juju instance
        any_charm_name: Name of the to be deployed any-charm
        dns_entries: List of DNS entries for any-charm
        machine: The machine to deploy the any-charm onto
    """
    any_app_name = any_charm_name
    any_charm_content = pathlib.Path("tests/integration/any_charm.py").read_text(encoding="utf-8")
    dns_record_content = pathlib.Path("lib/charms/bind/v0/dns_record.py").read_text(
        encoding="utf-8"
    )

    any_charm_src_overwrite = {
        "any_charm.py": any_charm_content,
        "dns_record.py": dns_record_content,
    }

    config = {
        "src-overwrite": json.dumps(any_charm_src_overwrite),
        "python-packages": "pydantic==2.7.1\n",
    }

    # We deploy https://charmhub.io/any-charm and inject the any_charm.py behavior
    # See https://github.com/canonical/any-charm on how to use any-charm
    if machine is not None:
        juju.deploy("any-charm", any_app_name, channel="beta", config=config, to=machine)
    else:
        juju.deploy("any-charm", any_app_name, channel="beta", config=config)

    juju.wait(jubilant.all_agents_idle)

    juju.integrate(f"{any_app_name}:require-dns-record", f"{app_name}:dns-record")

    # Get unit name and change relation data
    any_units = juju.status().get_units(any_app_name)
    any_unit_name = list(any_units.keys())[0]
    await change_anycharm_relation(juju, any_unit_name, dns_entries)


async def change_anycharm_relation(
    juju: jubilant.Juju,
    anyapp_unit_name: str,
    dns_entries: list[models.DnsEntry],
):
    """Change the relation of an anyapp_unit with the bind operator.

    Args:
        juju: The jubilant Juju instance
        anyapp_unit_name: anyapp unit name whose relation will change
        dns_entries: List of DNS entries for any-charm
    """
    await push_to_unit(
        juju=juju,
        unit_name=anyapp_unit_name,
        source=json.dumps([e.model_dump(mode="json") for e in dns_entries]),
        destination="/srv/dns_entries.json",
    )

    # fire reload-data event
    model_name = juju.model or juju.status().model.name
    cmd = (
        "JUJU_DISPATCH_PATH=hooks/reload-data "
        f"JUJU_MODEL_NAME={model_name} "
        f"JUJU_UNIT_NAME={anyapp_unit_name} ./dispatch"
    )
    await run_on_unit(juju, anyapp_unit_name, cmd)
    juju.wait(jubilant.all_agents_idle)


async def dig_query(
    juju: jubilant.Juju, unit_name: str, cmd: str, retry: bool = False, wait: int = 5
) -> str:
    """Query a DnsEntry with dig.

    Args:
        juju: The jubilant Juju instance
        unit_name: Unit name to be used to launch the command
        cmd: Dig command to perform
        retry: If the dig request should be retried
        wait: duration in seconds to wait between retries

    Returns: the result of the DNS query
    """
    result: str = ""
    for _ in range(5):
        result = (await run_on_unit(juju, unit_name, f"dig {cmd}")).strip()
        if (result.strip() != "" and "timed out" not in result) or not retry:
            break
        time.sleep(wait)

    return result


async def get_active_unit(app_name: str, juju: jubilant.Juju) -> str | None:
    """Get the current active unit name if it exists.

    Args:
        app_name: Application name to search for an active unit
        juju: The jubilant Juju instance

    Returns:
        The current active unit name if it exists, None otherwise
    """
    units = juju.status().get_units(app_name)
    for unit_name in units:
        # Use juju CLI to get detailed unit info
        output = juju.cli("show-unit", unit_name, "--format", "json")
        data = json.loads(output)
        relations = data[unit_name]["relation-info"]

        peer_relation = None
        for relation in relations:
            if relation["endpoint"] == "bind-peers":
                peer_relation = relation
                break

        if peer_relation is None:
            continue
        if "active-unit" not in peer_relation["application-data"]:
            continue
        if (
            peer_relation["local-unit"]["data"]["ingress-address"]
            == peer_relation["application-data"]["active-unit"]
        ):
            return unit_name
    return None


async def check_if_active_unit_exists(app_name: str, juju: jubilant.Juju) -> bool:
    """Check if an active unit exists and is reachable.

    Args:
        app_name: Application name to search for an active unit
        juju: The jubilant Juju instance

    Returns:
        True if active unit exists and is reachable
    """
    units = juju.status().get_units(app_name)
    if not units:
        return False

    unit_name = list(units.keys())[0]
    output = juju.cli("show-unit", unit_name, "--format", "json")
    data = json.loads(output)
    relations = data[unit_name]["relation-info"]

    peer_relation = None
    for relation in relations:
        if relation["endpoint"] == "bind-peers":
            peer_relation = relation
            break

    if peer_relation is None:
        return False
    if "active-unit" not in peer_relation["application-data"]:
        return False

    active_unit = peer_relation["application-data"]["active-unit"]
    if not active_unit:
        return False

    status = await dig_query(
        juju,
        unit_name,
        f"@{active_unit} status.{constants.ZONE_SERVICE_NAME} TXT +short",
        retry=True,
        wait=5,
    )
    return status == '"ok"'


async def force_reload_bind(juju: jubilant.Juju, unit_name: str):
    """Force reload bind.

    Args:
        juju: The jubilant Juju instance
        unit_name: the bind unit name to force reload
    """
    restart_cmd = f"sudo snap restart --reload {constants.DNS_SNAP_NAME}"
    await run_on_unit(juju, unit_name, restart_cmd)


async def get_unit_ips(juju: jubilant.Juju, app_name: str) -> list[str]:
    """Retrieve unit ip addresses.

    Args:
        juju: The jubilant Juju instance
        app_name: Application name

    Returns:
        list of unit ip addresses.
    """
    units = juju.status().get_units(app_name)
    ip_list = []
    for unit_name in sorted(units.keys(), key=lambda n: int(n.split("/")[-1])):
        ip_list.append(units[unit_name].public_address)
    return ip_list
