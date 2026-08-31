# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the ddns module."""

import pytest
from charms.dns_record.v0.dns_record import RecordType

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
    "domain,expected",
    [
        ("example.com", True),
        ("a-b.example.com", True),
        ("", False),
        ("not a domain", False),
        ("-example.com", False),
        ("example-.com", False),
        (f"{'a' * 64}.com", False),
    ],
)
def test_is_valid_domain(domain, expected):
    """
    arrange: take a domain name
    act: validate it
    assert: only valid domain names are accepted
    """
    assert ddns.is_valid_domain(domain) is expected


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
