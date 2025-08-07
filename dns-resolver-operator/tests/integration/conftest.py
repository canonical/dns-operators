# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest
import pytest_asyncio
import yaml


@pytest.fixture(scope="module", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> typing.Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps jubilant.juju.

    Args:
        request: fixture request

    Returns:
        juju
    """

    def show_debug_log(juju: jubilant.Juju):
        """Show debug log.

        Args:
            juju: Jubilant.juju
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


def create_charm_file(
    metadata: dict[str, typing.Any],
) -> str:
    """Pack the charm and returns the filename, or --charm-file if set.

    Args:
        metadata: charm's metadata

    Returns:
        charm file's path

    Raises:
        OSError: if error while packing the charm
    """
    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = metadata["name"]
    charm_path = pathlib.Path(__file__).parent.parent.parent
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    return str(charms[0])


@pytest.fixture(scope="module", name="dns_resolver_charm_file")
def dns_resolver_charm_file_fixture(
    dns_resolver_metadata: dict[str, typing.Any], pytestconfig: pytest.Config
):
    """Create dns-resolver charm file.

    Args:
        dns_resolver_metadata: dns-resolver metadata
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--charm-file")
    if charm_file:
        yield f"./{charm_file}"
        return
    yield create_charm_file(dns_resolver_metadata)


@pytest.fixture(scope="module", name="bind_charm_file")
def bind_charm_file_fixture(bind_metadata: dict[str, typing.Any], pytestconfig: pytest.Config):
    """Create bind charm file.

    Args:
        bind_metadata: bind metadata
        pytestconfig: pytest config options

    Returns:
        charm file's path
    """
    charm_file = pytestconfig.getoption("--bind-charm-file")
    if charm_file:
        yield charm_file
        return
    yield create_charm_file(bind_metadata)


@pytest.fixture(scope="module", name="dns_resolver_metadata")
def dns_resolver_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../dns-resolver-operator/charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_resolver_name")
def fixture_dns_resolver_name(dns_resolver_metadata):
    """Provide charm name from the metadata."""
    yield dns_resolver_metadata["name"]


@pytest.fixture(scope="module", name="bind_metadata")
def bind_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../bind-operator/metadata.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="bind_name")
def fixture_bind_name(bind_metadata):
    """Provide charm name from the metadata."""
    yield bind_metadata["name"]


@pytest_asyncio.fixture(scope="module", name="dns_resolver")
async def dns_resolver_fixture(
    juju: jubilant.Juju,
    dns_resolver_charm_file: str,
    dns_resolver_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(
        dns_resolver_charm_file,
        dns_resolver_name,
        resources={},
        num_units=1,
    )


@pytest_asyncio.fixture(scope="module", name="bind")
async def bind_fixture(
    juju: jubilant.Juju,
    bind_charm_file: str,
    bind_name: str,
    pytestconfig: pytest.Config,
):
    """Deploy the charm."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        return

    juju.deploy(bind_charm_file, bind_name, resources={})
    juju.wait(lambda status: jubilant.all_active(status, bind_name))


@pytest_asyncio.fixture(scope="module", name="full_deployment")
async def full_deployment_fixture(
    juju: jubilant.Juju,
    bind_name: str,
    dns_resolver_name: str,
    bind,  # pylint: disable=unused-argument
    dns_resolver,  # pylint: disable=unused-argument
):
    """Add necessary integration for the deployed charms."""
    juju.integrate(dns_resolver_name, bind_name)
    juju.wait(lambda status: jubilant.all_active(status, dns_resolver_name))
