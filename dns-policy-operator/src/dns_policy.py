# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""App charm business logic."""

import itertools
import json
import logging
import subprocess  # nosec

import ops
import pydantic
import requests
from charms.bind.v0.dns_record import RequirerEntry
from charms.operator_libs_linux.v2 import snap

import constants

logger = logging.getLogger(__name__)


class DnsPolicyCharmError(Exception):
    """Base exception for the bind charm."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class ConfigInvalidError(DnsPolicyCharmError):
    """Exception raised when a config value for the dns policy is invalid."""


class ApiError(DnsPolicyCharmError):
    """Exception raised when an API request to the workload fails."""


class CommandError(DnsPolicyCharmError):
    """Exception raised when a command fails."""


class SnapError(DnsPolicyCharmError):
    """Exception raised when an action on the snap fails."""


class StatusError(SnapError):
    """Exception raised when unable to get the status the service."""


class InstallError(SnapError):
    """Exception raised when unable to install dependencies for the service."""


class ConfigureError(SnapError):
    """Exception raised when unable to configure the service."""


class RootTokenError(DnsPolicyCharmError):
    """Exception raised when unable to get a valid root token."""


class GetApprovedRecordRequestsError(DnsPolicyCharmError):
    """Exception raised when unable to get approved record requests."""


class DnsPolicyConfig(pydantic.BaseModel):
    """Configuration for the DnsPolicy workload.

    This is used to translate information from the current charm state into valid configuration
    for the dns-policy workload app.

    Attrs:
        debug: transmitted to the workload as a string
        allowed_hosts: sent as a json string to the workload
        database_host: host of the db
        database_port: port of the db
        database_name: name of the db
        database_password: password of the db
        database_user: user of the db
    """

    debug: bool = False
    allowed_hosts: list[str] = pydantic.Field(default_factory=list)
    database_host: str = ""
    database_port: int = 0
    database_name: str = ""
    database_password: str = ""
    database_user: str = ""

    @pydantic.model_serializer
    def ser_model(self) -> dict[str, str]:
        """Make sure to serialize to a dict[str, str].

        Returns:
            The serialized dict representing this model
        """
        return {
            "debug": "true" if self.debug else "false",
            "allowed-hosts": json.dumps(self.allowed_hosts),
            "database-host": self.database_host,
            "database-port": str(self.database_port) if self.database_port else "",
            "database-name": self.database_name,
            "database-password": self.database_password,
            "database-user": self.database_user,
        }

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, database_relation_data: dict[str, str]
    ) -> "DnsPolicyConfig":
        """Initialize a new instance of the DnsPolicyConfig class from the associated charm.

        Args:
            charm: The charm instance associated with this state.
            database_relation_data: Relation data from the database.

        Returns: An instance of the DnsPolicyConfig object.

        Raises:
            ConfigInvalidError: For any validation error in the charm config data.
        """
        try:
            database_port = int(database_relation_data["POSTGRES_PORT"])
        except ValueError:
            database_port = 0
        config = {
            "debug": charm.config["debug"],
            "allowed_hosts": [e.strip() for e in str(charm.config["allowed-hosts"]).split(",")],
            "database_host": database_relation_data["POSTGRES_HOST"],
            "database_port": database_port,
            "database_name": database_relation_data["POSTGRES_DB"],
            "database_password": database_relation_data["POSTGRES_PASSWORD"],
            "database_user": database_relation_data["POSTGRES_USER"],
        }

        logger.debug("Init DnsPolicyConfig with: %s", config)

        try:
            validated_dns_policy_config = DnsPolicyConfig.model_validate(config)
        except pydantic.ValidationError as e:
            error_fields = set(itertools.chain.from_iterable(error["loc"] for error in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise ConfigInvalidError(f"invalid configuration: {error_field_str}") from e

        return validated_dns_policy_config


class DnsPolicyService:
    """DnsPolicy service class."""

    def status(self) -> bool:
        """Get the status of the snap service.

        Raises:
            StatusError: If the status could not be retrieved

        Returns:
            true if the service is active
        """
        try:
            cache = snap.SnapCache()
            dns_policy = cache[constants.DNS_SNAP_NAME]
            for service in constants.DNS_SNAP_SERVICES:
                dns_policy_service = dns_policy.services[service]
                if not dns_policy_service["active"]:
                    return False
            return True

        except snap.SnapError as e:
            error_msg = (
                f"An exception occurred when retrieving the status of {constants.DNS_SNAP_NAME}. "
                f"Reason: {e}"
            )
            logger.error(error_msg)
            raise StatusError(error_msg) from e

    def setup(self) -> None:
        """Prepare the machine."""
        # Check if the snap is already installed
        cache = snap.SnapCache()
        if constants.DNS_SNAP_NAME in cache:
            return
        self._install_snap_package(
            snap_name=constants.DNS_SNAP_NAME,
            snap_channel=constants.SNAP_PACKAGES[constants.DNS_SNAP_NAME]["channel"],
        )

    def _install_snap_package(
        self, snap_name: str, snap_channel: str, refresh: bool = False
    ) -> None:
        """Installs snap package.

        Args:
            snap_name: the snap package to install
            snap_channel: the snap package channel
            refresh: whether to refresh the snap if it's already present.

        Raises:
            InstallError: when encountering a SnapError or a SnapNotFoundError
        """
        try:
            snap_cache = snap.SnapCache()
            snap_package = snap_cache[snap_name]

            if not snap_package.present or refresh:
                snap_package.ensure(snap.SnapState.Latest, channel=snap_channel)
        except (snap.SnapError, snap.SnapNotFoundError, subprocess.CalledProcessError) as e:
            error_msg = f"An exception occurred when installing {snap_name}. Reason: {e}"
            logger.exception(error_msg)
            raise InstallError(error_msg) from e

    def configure(self, config: DnsPolicyConfig) -> None:
        """Configure the dns-policy service.

        Args:
            config: dict of configuration values

        Raises:
            ConfigureError: when encountering a SnapError
        """
        try:
            cache = snap.SnapCache()
            charmed_bind = cache[constants.DNS_SNAP_NAME]
            logger.debug("Configure dns-policy-app: %s", config.model_dump())
            charmed_bind.set(config.model_dump())
        except snap.SnapError as e:
            error_msg = (
                f"An exception occurred when configuring {constants.DNS_SNAP_NAME}. Reason: {e}"
            )
            logger.error(error_msg)
            raise ConfigureError(error_msg) from e

    def command(self, cmd: str) -> str:
        """Run manage command of the dns-policy service.

        Args:
            cmd: command to execute by django's manage script

        Raises:
            CommandError: if the command call errors

        Returns:
            The resulting output of the command's execution
        """
        try:
            # We ignore security issues with this subprocess call
            # as it can only be done from the operator of the charm
            return subprocess.check_output(
                ["sudo", "snap", "run", f"{constants.DNS_SNAP_NAME}.manage"] + cmd.split(),
            ).decode(  # nosec
                "utf-8"
            )
        except subprocess.SubprocessError as e:
            raise CommandError(str(e)) from e

    def get_api_root_token(self) -> str:
        """Get API root token.

        Raises:
            RootTokenError: if the root token could not be retrieved

        Returns:
            the API root token
        """
        try:
            res = self.command("get_root_token")
            tokens = json.loads(res)
        except json.decoder.JSONDecodeError as e:
            raise RootTokenError(str(e)) from e
        if not isinstance(tokens, dict) or "access" not in tokens or tokens["access"] == "":
            raise RootTokenError("Invalid root token!")
        return tokens["access"]

    def send_requests(self, token: str, record_requests: list[RequirerEntry]) -> None:
        """Send record requests.

        Args:
            token: root token for the API
            record_requests: list of record requests from the relations

        Raises:
            ApiError: if the request errors
        """
        try:
            req = requests.post(
                f"{constants.DNS_POLICY_ENDPOINTS_BASE}/",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
                data=json.dumps([x.model_dump() for x in record_requests]),
            )
            req.raise_for_status()
        except requests.RequestException as e:
            raise ApiError(str(e)) from e

    def get_approved_requests(self, token: str) -> list[RequirerEntry]:
        """Get approved record requests.

        Args:
            token: root token for the API

        Returns:
            A list of RequirerEntry to update the relations

        Raises:
            ApiError: if the request errors
            GetApprovedRecordRequestsError: if the requests errors
        """
        try:
            req = requests.get(
                f"{constants.DNS_POLICY_ENDPOINTS_BASE}/approved/",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
            )
        except requests.RequestException as e:
            raise ApiError(str(e)) from e

        try:
            entries = []
            data = req.json()

            if "code" in data and data["code"] == "token_not_valid":
                raise GetApprovedRecordRequestsError(str(data))

            for rr in data:
                # The record_class is always "IN"
                rr["record_class"] = "IN"
                entry = RequirerEntry.model_validate(rr)
                entries.append(entry)
        except pydantic.ValidationError as e:
            raise GetApprovedRecordRequestsError(str(e)) from e
        return entries
