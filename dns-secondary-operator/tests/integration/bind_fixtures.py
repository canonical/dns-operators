# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import typing
from pathlib import Path

import jubilant
import pytest
import pytest_asyncio
import yaml

from .core_fixtures import create_charm_file


@pytest.fixture(scope="module", name="bind_directory")
def bind_directory_fixture():
    """Provide charm metadata."""
    return Path("../bind-operator")


@pytest.fixture(scope="module", name="bind_metadata")
def bind_metadata_fixture(bind_directory):
    """Provide charm metadata."""
    yield yaml.safe_load(Path(bind_directory / "charmcraft.yaml").read_text(encoding="UTF-8"))


@pytest.fixture(scope="module", name="bind_name")
def fixture_bind_name(bind_metadata):
    """Provide charm name from the metadata."""
    yield bind_metadata["name"]


@pytest.fixture(scope="module", name="bind_charm_file")
def bind_charm_file_fixture(
    bind_metadata: dict[str, typing.Any],
    bind_directory: Path,
):
    """Create bind charm file.
    Args:
        bind_metadata: bind metadata
        bind_directory: path to bind's directory
    Returns:
        charm file's path
    """
    yield create_charm_file(bind_metadata, bind_directory)


@pytest_asyncio.fixture(scope="module", name="bind")
async def bind_fixture(
    juju: jubilant.Juju,
    bind_charm_file: str,
    bind_name: str,
):
    """Deploy the charm."""
    juju.deploy(bind_charm_file, bind_name, resources={})
    juju.wait(lambda status: jubilant.all_active(status, bind_name))
