# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helpers for the dns-aggregator charm unit tests."""

import uuid as uuid_module

from charms.dns_record.v0 import dns_record

INTERFACE = "dns_record"


def make_uuid(name):
    """Build a stable uuid out of a name.

    Args:
        name: the name to derive the uuid from.

    Returns:
        the derived uuid.
    """
    return uuid_module.uuid5(uuid_module.NAMESPACE_DNS, name)


def make_request(name, host_label="www", domain="example.com", record_data="10.0.0.1"):
    """Build a record request.

    Args:
        name: the name the uuid of the request is derived from.
        host_label: the host label of the requested record.
        domain: the domain of the requested record.
        record_data: the data of the requested record.

    Returns:
        the record request.
    """
    return dns_record.RecordRequest(
        uuid=make_uuid(name),
        record=dns_record.Record(
            domain=domain,
            host_label=host_label,
            ttl=600,
            record_class=dns_record.RecordClass.IN,
            record_type=dns_record.RecordType.A,
            record_data=record_data,
        ),
    )


def make_response(name, status=dns_record.Status.APPROVED, description="approved"):
    """Build a response to a record request.

    Args:
        name: the name the uuid of the response is derived from.
        status: the status of the response.
        description: the description of the response.

    Returns:
        the response.
    """
    return dns_record.RecordRequest(uuid=make_uuid(name), status=status, description=description)


def _databag(data):
    """Drop the empty fields of an encoded databag.

    Juju removes a relation data field when it is set to an empty value, so an encoded
    databag never holds one.

    Args:
        data: the encoded databag.

    Returns:
        the databag as juju would store it.
    """
    return {key: value for key, value in data.items() if value != ""}


def requirer_databag(dns_entries=(), ddns_addresses=()):
    """Build the application databag published by a dns_record requirer.

    Args:
        dns_entries: the record requests to publish.
        ddns_addresses: the ddns addresses to declare.

    Returns:
        the encoded databag.
    """
    return _databag(
        dns_record.RequirerData(
            dns_entries=list(dns_entries), ddns_addresses=set(ddns_addresses)
        ).model_dump(by_alias=True)
    )


def provider_databag(dns_entries=(), ddns_domain=None):
    """Build the application databag published by a dns_record provider.

    Args:
        dns_entries: the responses to publish.
        ddns_domain: the automatically allocated domain to publish.

    Returns:
        the encoded databag.
    """
    return _databag(
        dns_record.ProviderData(dns_entries=list(dns_entries), ddns_domain=ddns_domain).model_dump(
            by_alias=True
        )
    )


def parse_requirer(databag):
    """Decode an application databag published by a dns_record requirer.

    Args:
        databag: the databag to decode.

    Returns:
        the decoded databag.
    """
    return dns_record.RequirerData.model_validate(dict(databag))


def parse_provider(databag):
    """Decode an application databag published by a dns_record provider.

    Args:
        databag: the databag to decode.

    Returns:
        the decoded databag.
    """
    return dns_record.ProviderData.model_validate(dict(databag))


def uuids(names):
    """Get the uuids derived from a list of names.

    Args:
        names: the names to derive the uuids from.

    Returns:
        the derived uuids.
    """
    return {make_uuid(name) for name in names}


def entry_uuids(dns_entries):
    """Get the uuids of a list of record requests.

    Args:
        dns_entries: the record requests to get the uuids of.

    Returns:
        the uuids of the record requests.
    """
    return {entry.uuid for entry in dns_entries}
