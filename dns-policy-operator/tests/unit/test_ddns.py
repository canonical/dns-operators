# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the ddns module."""

import pytest
from charms.dns_record.v0.dns_record import Record, RecordClass, RecordType

import ddns


@pytest.mark.parametrize(
    "domain,expected",
    [
        (" Example.COM. ", "example.com"),
        ("example.com", "example.com"),
    ],
)
def test_normalize_domain(domain, expected):
    """
    arrange: take a domain name
    act: normalize it
    assert: the domain is lowercase, stripped and without its trailing dot
    """
    assert ddns.normalize_domain(domain) == expected


def test_fqdn():
    """
    arrange: take a host label and a domain
    act: build the fqdn
    assert: the fqdn is the normalized concatenation of both
    """
    assert ddns.fqdn("Admin", "Example.com.") == "admin.example.com"


@pytest.mark.parametrize(
    "name,domain,expected",
    [
        ("example.com", "example.com", True),
        ("foo.example.com", "example.com", True),
        ("foo.bar.example.com", "example.com", True),
        ("notexample.com", "example.com", False),
        ("example.com.evil.com", "example.com", False),
        ("example.com", "", False),
    ],
)
def test_is_within(name, domain, expected):
    """
    arrange: take a domain name and a domain
    act: check whether the name is under the domain
    assert: only the domain itself and its subdomains are within
    """
    assert ddns.is_within(name, domain) is expected


@pytest.mark.parametrize(
    "domain",
    [
        "example.com",
        "a-b.example.com",
        " Example.COM. ",
        f"{'.'.join(['aaaaaaaaa'] * 19)}.com",
    ],
)
def test_ddns_domain_error_accepts_valid_domains(domain):
    """
    arrange: take a valid suffix of the automatically allocated domains
    act: validate it
    assert: no error is reported
    """
    assert ddns.ddns_domain_error(domain) is None


@pytest.mark.parametrize(
    "domain,expected",
    [
        ("", "the domain is empty"),
        (f"{'.'.join(['aaaaaaaaa'] * 20)}.com", "203 characters long"),
        (f"{'a' * 64}.com", f"{'a' * 64!r} is 64 characters long"),
        ("not a domain", "'not a domain' is not a valid domain label"),
        ("-example.com", "'-example' is not a valid domain label"),
        ("example-.com", "'example-' is not a valid domain label"),
    ],
)
def test_ddns_domain_error_explains_invalid_domains(domain, expected):
    """
    arrange: take an invalid suffix of the automatically allocated domains
    act: validate it
    assert: the error tells why the domain was rejected
    """
    error = ddns.ddns_domain_error(domain)

    assert error is not None
    assert expected in error


def test_record_type():
    """
    arrange: take IPv4 and IPv6 addresses
    act: get their record type
    assert: A is used for IPv4 and AAAA for IPv6
    """
    assert ddns.record_type("10.0.0.1") == RecordType.A
    assert ddns.record_type("2001:db8::1") == RecordType.AAAA
    with pytest.raises(ValueError):
        ddns.record_type("not-an-address")


def test_records():
    """
    arrange: take an automatically allocated domain and its addresses
    act: build its records
    assert: the domain and its wildcard point at every address
    """
    records = ddns.records("c3f9m2q4.example.com", ["10.0.0.1", "2001:db8::1"])
    assert {(r.host_label, r.domain, str(r.record_data), r.record_type) for r in records} == {
        ("c3f9m2q4", "example.com", "10.0.0.1", RecordType.A),
        ("c3f9m2q4", "example.com", "2001:db8::1", RecordType.AAAA),
        ("*.c3f9m2q4", "example.com", "10.0.0.1", RecordType.A),
        ("*.c3f9m2q4", "example.com", "2001:db8::1", RecordType.AAAA),
    }


def test_records_without_a_parent_domain():
    """
    arrange: take a domain without a parent domain
    act: build its records
    assert: a ValueError is raised
    """
    with pytest.raises(ValueError):
        ddns.records("example", ["10.0.0.1"])


@pytest.mark.parametrize(
    "host_label,domain,record_type,expected",
    [
        ("admin", "example.com", RecordType.A, True),
        ("admin", "example.com", RecordType.AAAA, True),
        ("admin", "example.com", RecordType.CNAME, True),
        ("@", "example.com", RecordType.A, True),
        ("admin", "example.com", RecordType.TXT, False),
        ("_acme-challenge.admin", "example.com", RecordType.TXT, False),
        ("admin", "example.com", RecordType.MX, False),
        ("admin", "example.org", RecordType.A, False),
    ],
)
def test_is_reserved(host_label, domain, record_type, expected):
    """
    arrange: take a record
    act: check whether it is reserved under the example.com ddns domain
    assert: only the A, AAAA and CNAME records under the ddns domain are reserved
    """
    record_data = {
        RecordType.A: "10.0.0.1",
        RecordType.AAAA: "2001:db8::1",
        RecordType.CNAME: "target.example.org",
        RecordType.MX: "10 mail.example.org",
        RecordType.TXT: "challenge",
    }[record_type]
    record = Record(
        domain=domain,
        host_label=host_label,
        ttl=600,
        record_class=RecordClass.IN,
        record_type=record_type,
        record_data=record_data,
    )

    assert ddns.is_reserved(record, "example.com") is expected
