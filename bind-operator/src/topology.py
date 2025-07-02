# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Bind charm topology logic."""

import logging
import subprocess
import time

import ops
import pydantic

import constants

logger = logging.getLogger(__name__)

DEFAULT_RELATION_NAME = "bind-topology"


class TopologyError(Exception):
    """Base exception for the topology module."""

    def __init__(self, msg: str):
        """Initialize a new instance of the exception.

        Args:
            msg (str): Explanation of the error.
        """
        self.msg = msg


class PeerRelationUnavailableError(TopologyError):
    """Exception raised when the peer relation is unavailable."""


class PeerRelationNetworkUnavailableError(TopologyError):
    """Exception raised when the peer relation network is unavailable."""


class TopologyUnavailableError(TopologyError):
    """Exception raised when topology could not be retrieved."""


class Topology(pydantic.BaseModel):
    """Class used to represent the current units topology.

    Attributes:
        units_ip: IPs of all the units
        active_unit_ip: IP of the active unit
        standby_units_ip: IPs of the standby units
        current_unit_ip: IP of the current unit
        is_current_unit_active: Is the current unit active ?
    """

    units_ip: list[pydantic.IPvAnyAddress]
    active_unit_ip: pydantic.IPvAnyAddress | None
    standby_units_ip: list[pydantic.IPvAnyAddress]
    current_unit_ip: pydantic.IPvAnyAddress

    @property
    def is_current_unit_active(self) -> bool:
        """Check if the current unit is the active unit.

        Returns:
            True if the current unit is effectively the active unit.
        """
        return self.current_unit_ip == self.active_unit_ip


class TopologyChangedEvent(ops.EventBase):
    """Topology changed event."""


class TopologyEvents(ops.CharmEvents):
    """Topology events.

    This class defines the events that a topology service can emit.

    Attributes:
        topology_changed: the topologyChangedEvent.
    """

    topology_changed = ops.EventSource(TopologyChangedEvent)


class TopologyService(ops.Object):
    """Topology service class.

    Attrs:
        on: custom topology events
    """

    on = TopologyEvents()

    def __init__(self, charm: ops.CharmBase, relation_name: str = DEFAULT_RELATION_NAME) -> None:
        """Construct.

        Args:
            charm: the provider charm.
            relation_name: the relation name.
        """
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on.leader_elected, self._on_leader_elected)
        self.framework.observe(
            charm.on[relation_name].relation_departed, self._on_peer_relation_departed
        )
        self.framework.observe(
            charm.on[relation_name].relation_joined, self._on_peer_relation_joined
        )

    def dump(self) -> Topology:
        """Create a network topology of the current deployment.

        Returns:
            A topology of the current deployment

        Raises:
            TopologyUnavailableError: when the topology could not be created
        """
        start_time = time.time_ns()
        relation = self.model.get_relation(self.relation_name)
        binding = self.model.get_binding(self.relation_name)
        if not relation or not binding:
            raise TopologyUnavailableError(
                "Peer relation not available when trying to get topology."
            )
        if binding.network is None:
            raise TopologyUnavailableError(
                "Peer relation network not available when trying to get unit IP."
            )

        units_ip: list[str] = [
            unit_data.get("private-address", "")
            for _, unit_data in relation.data.items()
            if unit_data.get("private-address", "") != ""
        ]

        current_unit_ip = str(binding.network.bind_address)
        active_unit_ip = relation.data[self.charm.app].get("active-unit")

        logger.debug("active_unit_ip: %s", active_unit_ip)
        logger.debug("current_unit_ip: %s", current_unit_ip)
        logger.debug("units_ip: %s", units_ip)
        logger.debug("topology retrieval duration (ms): %s", (time.time_ns() - start_time) / 1e6)

        try:
            return Topology(
                # pydantic accepts str as IPvAnyAddress
                active_unit_ip=active_unit_ip,  # type: ignore
                units_ip=units_ip,  # type: ignore
                standby_units_ip=[ip for ip in units_ip if ip != active_unit_ip],  # type: ignore
                current_unit_ip=current_unit_ip,  # type: ignore
            )
        except pydantic.ValidationError as e:
            raise TopologyUnavailableError("Error while instantiating model") from e

    def _on_leader_elected(self, _: ops.LeaderElectedEvent) -> None:
        """Handle leader-elected event."""
        # We check that we are still the leader when starting to process this event
        try:
            topology = self.dump()
        except TopologyUnavailableError as err:
            logger.info("Could not retrieve network topology: %s", err)
            return
        if self.charm.unit.is_leader() and not topology.is_current_unit_active:
            self._check_and_may_become_active(topology)
        self.on.topology_changed.emit()

    def _on_peer_relation_joined(self, _: ops.RelationJoinedEvent) -> None:
        """Handle peer relation joined event."""
        try:
            topology = self.dump()
        except TopologyUnavailableError as err:
            logger.info("Could not retrieve network topology: %s", err)
            return
        # If we are not the active unit, there's nothing to do
        if not topology.is_current_unit_active:
            return
        self.on.topology_changed.emit()

    def _on_peer_relation_departed(self, event: ops.RelationDepartedEvent) -> None:
        """Handle the peer relation departed event.

        Args:
            event: Event triggering the relation-departed hook
        """
        # If we are a departing unit, we don't want to interfere with electing a new active one
        if event.departing_unit == self.model.unit:
            return

        try:
            topology = self.dump()
        except TopologyUnavailableError as err:
            logger.info("Could not retrieve network topology: %s", err)
            return

        # We check that we are still the leader when starting to process this event
        if not topology.is_current_unit_active:
            if self.charm.unit.is_leader():
                self._check_and_may_become_active(topology)
        self.on.topology_changed.emit()

    def _check_and_may_become_active(self, topology: Topology) -> bool:
        """Check the active unit status and may become active if need be.

        Args:
            topology: Topology of the current deployment

        Returns:
            True if the charm is effectively the new active unit.
        """
        relation = self.model.get_relation(self.relation_name)
        assert relation is not None  # nosec
        if not topology.active_unit_ip:
            relation.data[self.charm.app].update({"active-unit": str(topology.current_unit_ip)})
            return True

        status = self._dig_query(
            f"@{topology.active_unit_ip} service.{constants.ZONE_SERVICE_NAME} TXT +short",
            retry=True,
            wait=1,
        )
        if status != "ok":
            relation.data[self.charm.app].update({"active-unit": str(topology.current_unit_ip)})
            return True
        return False

    def _dig_query(self, cmd: str, retry: bool = False, wait: int = 5) -> str:
        """Query a DnsEntry with dig.

        This function was created for simplicity's sake. If we need to make more DNS requests
        in the future, we should revisit it by employing a python library.

        Args:
            cmd: The dig command to perform
            retry: If the dig request should be retried
            wait: duration in seconds to wait between retries

        Returns: the result of the DNS query
        """
        result: str = ""
        retry = False
        for _ in range(5):
            try:
                result = str(
                    subprocess.run(
                        ["dig"] + cmd.split(" "),  # nosec
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                ).strip()
            except subprocess.CalledProcessError as exc:
                logger.warning("%s", exc)
                result = ""
            if result != "" or not retry:
                break
            time.sleep(wait)

        return result
