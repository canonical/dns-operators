# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""App charm business logic."""

import itertools
import json
import logging
import subprocess  # nosec
import uuid

import ops
import pydantic
import requests
from charms.dns_record.v0.dns_record import Record, RecordRequest
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


class GetRequestStatusesError(DnsPolicyCharmError):
    """Exception raised when unable to get the status of the record requests."""


class DdnsAllocationError(DnsPolicyCharmError):
    """Exception raised when unable to allocate automatically allocated domain labels."""


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

    @pydantic.field_validator("allowed_hosts")
    @classmethod
    def always_allow_the_local_hosts(cls, value: list[str]) -> list[str]:
        """Make sure the workload always answers on the local hosts.

        The charm drives the workload through its API on the loopback interface, so
        Django has to accept the local host names whatever the operator configured,
        otherwise every API call is rejected with a "400 Bad Request".

        Args:
            value: the configured allowed hosts.

        Returns:
            the allowed hosts, with the missing local hosts added.
        """
        hosts = [host for host in value if host]
        for host in constants.DNS_POLICY_DEFAULT_ALLOWED_HOSTS:
            if host not in hosts:
                hosts.append(host)
        return hosts

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

    def send_requests(
        self,
        token: str,
        record_requests: dict[int, list[RecordRequest]],
        instance: str | None,
    ) -> None:
        """Send record requests.

        Each record request is sent along with the id of the relation it comes from, as
        its requirer id, and the identifier of this charm installation, as relation ids
        are only unique within a single charm installation.

        Args:
            token: root token for the API
            record_requests: record requests from the relations, by relation id
            instance: identifier of this charm installation, None when not available yet

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
                data=json.dumps(
                    [
                        {
                            **record_request.serialize_as_request(),
                            "requirer_id": str(relation_id),
                            "instance": instance,
                        }
                        for relation_id, relation_requests in record_requests.items()
                        for record_request in relation_requests
                    ]
                ),
            )
            req.raise_for_status()
        except requests.RequestException as e:
            raise ApiError(str(e)) from e

    def allocate_ddns_domains(
        self, token: str, instance: str, relation_ids: list[int], parent: str
    ) -> dict[int, str]:
        """Get the automatically allocated domain of each of the given relations.

        A relation that has no domain under the parent domain yet is allocated a new one.
        The workload guarantees that a domain is unique and never reused.

        Args:
            token: root token for the API
            instance: identifier of this charm installation, which scopes the relation
                ids as those are only unique within a single charm installation
            relation_ids: ids of the relations to get a domain for
            parent: parent domain the domains are allocated under

        Returns:
            The domain allocated to each relation, by relation id.

        Raises:
            ApiError: if the request errors
            DdnsAllocationError: if the workload answered with unusable data
        """
        if not relation_ids:
            return {}
        try:
            req = requests.post(
                f"{constants.DNS_POLICY_DDNS_ALLOCATIONS_ENDPOINT}/",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
                data=json.dumps(
                    [
                        {"instance": instance, "requirer_id": str(relation_id), "parent": parent}
                        for relation_id in relation_ids
                    ]
                ),
            )
            req.raise_for_status()
        except requests.RequestException as e:
            raise ApiError(str(e)) from e

        try:
            domains = {
                int(allocation["requirer_id"]): str(allocation["domain"])
                for allocation in req.json()
                if str(allocation["instance"]) == instance
            }
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise DdnsAllocationError(f"Invalid ddns allocation: {e}") from e
        for relation_id, domain in domains.items():
            host_label, _, domain_parent = domain.partition(".")
            if not host_label or domain_parent != parent:
                raise DdnsAllocationError(
                    f"Invalid ddns allocation {domain!r} for relation {relation_id}: "
                    f"not a domain directly under {parent!r}"
                )
        return domains

    def get_request_statuses(self, token: str) -> dict[uuid.UUID, tuple[str, str]]:
        """Get the status of every record request known to the workload.

        Args:
            token: root token for the API

        Returns:
            The workload status and status reason of each record request, by uuid.

        Raises:
            ApiError: if the request errors
            GetRequestStatusesError: if the workload answered with unusable data
        """
        try:
            req = requests.get(
                f"{constants.DNS_POLICY_ENDPOINTS_BASE}/all/",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=10,
            )
            req.raise_for_status()
        except requests.RequestException as e:
            raise ApiError(str(e)) from e

        try:
            return {
                uuid.UUID(str(rr["uuid"])): (str(rr["status"]), rr.get("status_reason") or "")
                for rr in req.json()
            }
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise GetRequestStatusesError(str(e)) from e

    def get_approved_requests(self, token: str) -> list[RecordRequest]:
        """Get approved record requests.

        Args:
            token: root token for the API

        Returns:
            A list of RecordRequest to update the relations

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
                entry = RecordRequest.model_validate(
                    {
                        "uuid": rr["uuid"],
                        "status": rr["status"],
                        "description": rr.get("status_reason") or "",
                        "record": Record.model_validate(rr),
                    }
                )
                entries.append(entry)
        except (KeyError, TypeError, pydantic.ValidationError) as e:
            raise GetApprovedRecordRequestsError(str(e)) from e
        return entries
