# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""

import json
import logging
from typing import Any, Generator

import pytest
from ops import testing

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function", name="dns_transfer_requirer_remote_data")
def dns_transfer_requirer_remote_data_fixture() -> Generator[dict[str, str], Any, None]:
    """Fixture for requirer remote data.

    Yields:
        Relation data in json format.
    """
    yield {
        "addresses": json.dumps(["10.10.10.10"]),
        "zones": json.dumps(["example.com"]),
        "transport": json.dumps("tls"),
    }


@pytest.fixture(scope="function", name="dns_transfer_requirer_relation")
def dns_transfer_requirer_relation_fixture(
    dns_transfer_requirer_remote_data,
) -> Generator[Any, Any, None]:
    """Fixture for requirer relation.

    Yields:
        Relation.
    """
    yield testing.Relation(
        endpoint="dns-transfer",
        interface="dns-transfer",
        remote_app_name="primary",
        remote_app_data=dns_transfer_requirer_remote_data,
    )


@pytest.fixture(scope="function", name="dns_transfer_provider_remote_data")
def dns_transfer_provider_remote_data_fixture() -> Generator[dict[str, str], Any, None]:
    """Fixture for provider remote data.

    Yields:
        Relation data in json format.
    """
    yield {
        "addresses": json.dumps(["10.10.10.20"]),
    }


@pytest.fixture(scope="function", name="dns_transfer_provider_relation")
def dns_transfer_provider_relation_fixture(
    dns_transfer_provider_remote_data,
) -> Generator[Any, Any, None]:
    """Fixture for provider relation..

    Yields:
        Relation.
    """
    yield testing.Relation(
        endpoint="dns-transfer",
        interface="dns-transfer",
        remote_app_name="secondary",
        remote_app_data=dns_transfer_provider_remote_data,
    )
