#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm for dns-secondary."""

import logging
import socket
import typing

import ops
import pydantic
from charms.dns_transfer.v0 import dns_transfer
from charms.tls_certificates_interface.v4.tls_certificates import (
    CertificateRequestAttributes,
    Mode,
    TLSCertificatesRequiresV4,
)

import certificate_storage
import constants
import topology
from bind import BindService

logger = logging.getLogger(__name__)

STATUS_REQUIRED_INTEGRATION = "Needs to be related with a primary charm"
CERTIFICATES_RELATION_NAME = "bind-certificates"


class DnsSecondaryCharm(ops.CharmBase):
    """Charm the service.

    Attrs:
        remote_hostname: remote-hostname config.
    """

    def __init__(self, *args: typing.Any):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.bind = BindService()
        self.topology = topology.TopologyObserver(self, constants.PEER)
        self.dns_transfer = dns_transfer.DNSTransferRequires(self)
        self.certificates = TLSCertificatesRequiresV4(
            charm=self,
            relationship_name=CERTIFICATES_RELATION_NAME,
            certificate_requests=[self._get_certificate_request_attributes()],
            mode=Mode.UNIT,
        )

        self.framework.observe(self.on.config_changed, self._reconcile)
        self.framework.observe(self.on.stop, self._on_stop)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_status)
        self.framework.observe(self.on["dns-transfer"].relation_changed, self._reconcile)
        self.framework.observe(self.topology.on.topology_changed, self._reconcile)
        self.framework.observe(self.certificates.on.certificate_available, self._reconcile)
        self.framework.observe(
            self.on[CERTIFICATES_RELATION_NAME].relation_departed,
            self._on_certificates_relation_departed,
        )
        self.unit.open_port("tcp", constants.DNS_BIND_PORT)  # Bind DNS
        self.unit.open_port("udp", constants.DNS_BIND_PORT)  # Bind DNS

    @property
    def remote_hostname(self) -> str:
        """Remote hostname or unit hostname if not set."""
        unit_hostname = socket.gethostname()
        return str(self.config.get("remote-hostname", unit_hostname))

    def _reconcile(self, _: ops.EventBase) -> None:  # noqa: C901
        """Reconcile the charm."""
        if not self._has_required_integration():
            return

        self.unit.status = ops.MaintenanceStatus("Preparing bind")

        self.bind.setup()

        enable_tls = False
        if self._relation_created(CERTIFICATES_RELATION_NAME):
            self._check_and_update_certificate()
            if self._certificate_is_available():
                enable_tls = True

        self.bind.write_config_options(enable_tls=enable_tls)
        self.bind.start()

        relation = self.model.get_relation(self.dns_transfer.relation_name)
        data = None
        try:
            data = self.dns_transfer.get_remote_relation_data()
        except pydantic.ValidationError as e:
            logger.exception("failed to get dns_transfer data: %s", str(e))
        if data and data.addresses and data.zones:
            self.unit.status = ops.MaintenanceStatus("Updating named.conf.local")
            if not enable_tls and data.transport == dns_transfer.TransportSecurity.TLS:
                logger.error(
                    "Certificate not ready, transport: TLS, named.conf.local will not be updated"
                )
                return
            if enable_tls and data.transport == dns_transfer.TransportSecurity.TCP:
                logger.info("TLS available but provider transport is tcp")
                enable_tls = False
            self.bind.write_config_local(
                data.zones, [str(a) for a in data.addresses], enable_tls=enable_tls
            )
            self.bind.reload(force_start=True)

        if self.unit.is_leader():
            public_ips = self.topology.dump().public_ips
            if not public_ips:
                logger.debug("Public ips not set, using units ip")
                public_ips = self.topology.dump().units_ip
            requirer_data = dns_transfer.DNSTransferRequirerData(addresses=public_ips)
            self.dns_transfer.update_relation_data(relation, requirer_data)

    def _on_collect_status(self, event: ops.CollectStatusEvent) -> None:
        """Handle collect status event.

        Args:
            event: Event triggering the collect-status hook
        """
        if not self._has_required_integration():
            event.add_status(ops.BlockedStatus(STATUS_REQUIRED_INTEGRATION))

        relation_data = None
        try:
            relation_data = self.dns_transfer.get_remote_relation_data()
        except pydantic.ValidationError:
            event.add_status(ops.ActiveStatus("DNS primary relation not ready"))
            logger.warning("DNS primary relation data has no valid data")
            return
        if not relation_data:
            event.add_status(ops.ActiveStatus("DNS primary relation not ready"))
            logger.warning("DNS primary relation could not be retrieved")
            return

        if self._relation_created(CERTIFICATES_RELATION_NAME):
            if not self.remote_hostname:
                event.add_status(ops.BlockedStatus("Remote hostname is required"))
            elif not self._certificate_is_available():
                if relation_data.transport == dns_transfer.TransportSecurity.TLS:
                    event.add_status(
                        ops.BlockedStatus(
                            "Certificate not ready, transport: TLS. Check the certificate"
                        )
                    )
                else:
                    event.add_status(
                        ops.ActiveStatus(
                            "Certificate not ready, transport: TCP. No action required"
                        )
                    )

        total_zones = len(relation_data.zones)
        total_addresses = len(relation_data.addresses)
        event.add_status(
            ops.ActiveStatus(f"{total_zones} zones, {total_addresses} primary addresses")
        )

    def _on_stop(self, _: ops.StopEvent) -> None:
        """Handle stop."""
        self.bind.stop()

    def _on_certificates_relation_departed(self, event: ops.EventBase) -> None:
        """Handle certificates relation departed.

        Args:
            event: relation departed event.
        """
        self._reconcile(event)
        certificate_storage.delete_files()

    def _has_required_integration(self) -> bool:
        """Check if dns_transfer required integration is set.

        Returns:
            true if dns_transfer is set.
        """
        data = None
        try:
            data = self.dns_transfer.get_remote_relation_data()
        except pydantic.ValidationError:
            return False
        return data is not None

    def _relation_created(self, relation_name: str) -> bool:
        """Check if relation is created.

        Args:
            relation_name (str): relation name.

        Returns:
            if relation is created.
        """
        return bool(self.model.relations.get(relation_name))

    # TLS helpers
    def _certificate_is_available(self) -> bool:
        """Check certificate.

        Returns:
            if certificate is available.
        """
        cert, key = self.certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        return bool(cert and key)

    def _get_certificate_request_attributes(self) -> CertificateRequestAttributes:
        """Get CSR attributes.

        Returns:
            CertificateRequestAttributes: attributes as expected by tls library.
        """
        return CertificateRequestAttributes(common_name=self.remote_hostname)

    def _check_and_update_certificate(self) -> bool:
        """Check if the certificate or private key needs an update and perform the update.

        This method retrieves the currently assigned certificate and private key associated with
        the charm's TLS relation. It checks whether the certificate or private key has changed
        or needs to be updated. If an update is necessary, the new certificate or private key is
        stored.

        Returns:
            bool: True if either the certificate or the private key was updated, False otherwise.
        """
        provider_certificate, private_key = self.certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        if not provider_certificate or not private_key:
            logger.debug("Certificate or private key is not available")
            return False
        if certificate_update_required := certificate_storage.is_certificate_update_required(
            provider_certificate
        ):
            certificate_storage.store_certificate(certificate=provider_certificate)
        if private_key_update_required := certificate_storage.is_private_key_update_required(
            private_key
        ):
            certificate_storage.store_private_key(private_key=private_key)
        return certificate_update_required or private_key_update_required


if __name__ == "__main__":  # pragma: nocover
    ops.main(DnsSecondaryCharm)
