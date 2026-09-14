# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import contextlib
import os
import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest
import yaml

# Name of the workload snap, as packed from the charmed-dns-policy directory
SNAP_NAME = "charmed-dns-policy"

# Suffix the automatically allocated domains are tested with
DDNS_DOMAIN = "ddns.test"

# Record request the dns-integrator charm is configured with
INTEGRATOR_REQUEST = "admin dns.test 600 IN A 42.42.42.42"


def _pack_charm(directory: pathlib.Path, app_name: str) -> str:
    """Pack the charm of a directory and return the path of the packed charm.

    Args:
        directory: directory of the charm to pack
        app_name: name of the charm to pack

    Returns:
        the path of the packed charm

    Raises:
        OSError: if the charm could not be packed
    """
    for stale_charm in directory.glob(f"{app_name}_*.charm"):
        stale_charm.unlink()

    try:
        subprocess.run(
            ["charmcraft", "pack"],
            capture_output=True,
            check=True,
            cwd=directory,
            text=True,
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    charms = [p.absolute() for p in directory.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    return str(charms[0])


def _pack_snap(directory: pathlib.Path) -> str:
    """Pack the workload snap of a directory and return the path of the packed snap.

    Args:
        directory: directory of the snap to pack

    Returns:
        the path of the packed snap

    Raises:
        OSError: if the snap could not be packed
    """
    for stale_snap in directory.glob("*.snap"):
        stale_snap.unlink()

    try:
        subprocess.run(
            ["snapcraft", "pack"],
            capture_output=True,
            check=True,
            cwd=directory,
            env={**os.environ, "SNAPCRAFT_BUILD_ENVIRONMENT": "lxd"},
            text=True,
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing snap: {exc}; Stderr:\n{exc.stderr}") from None

    snaps = [p.absolute() for p in directory.glob("*.snap")]
    assert snaps, "snap file not found"
    assert len(snaps) == 1, "more than one .snap file, unsure which to use"
    return str(snaps[0])


def _sideload_snap(juju: jubilant.Juju, unit: str, snap_file: str) -> None:
    """Replace the workload snap of a unit by a local one.

    The charm installs its workload from the snap store, so testing the snap of this
    tree means installing it over the one the charm pulled, then migrating the database
    the new revision may have added tables to.

    Args:
        juju: the juju client
        unit: the dns-policy unit to install the snap on
        snap_file: the path of the snap to install
    """
    remote_path = f"/tmp/{pathlib.Path(snap_file).name}"  # nosec B108
    juju.scp(snap_file, f"{unit}:{remote_path}")
    juju.ssh(unit, f"sudo snap install --dangerous {remote_path}")
    juju.ssh(unit, f"sudo snap run {SNAP_NAME}.manage migrate")


@contextlib.contextmanager
def _configured_ddns_domain(
    juju: jubilant.Juju, dns_policy_app: str, domain: str
) -> typing.Iterator[str]:
    """Set the ddns-domain configuration for the duration of the context.

    Args:
        juju: the juju client
        dns_policy_app: the dns-policy application to configure
        domain: the suffix of the automatically allocated domains to configure

    Yields:
        the configured suffix
    """
    config = juju.config(dns_policy_app)
    assert config is not None
    original = config.get("ddns-domain", "")

    juju.config(dns_policy_app, {"ddns-domain": domain})
    try:
        yield domain
    finally:
        juju.config(dns_policy_app, {"ddns-domain": original})


@pytest.fixture(scope="module", name="juju")
def juju_fixture(
    request: pytest.FixtureRequest,
) -> typing.Generator[jubilant.Juju, None, None]:
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

    model = request.config.getoption("--model", default=None)
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = request.config.getoption("--keep-models", default=False)
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


@pytest.fixture(scope="module", name="dns_policy_metadata")
def dns_policy_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(pathlib.Path("./charmcraft.yaml").read_text(encoding="UTF-8"))


@pytest.fixture(scope="module", name="dns_policy_name")
def fixture_dns_policy_name(dns_policy_metadata):
    """Provide charm name from the metadata."""
    yield dns_policy_metadata["name"]


@pytest.fixture(scope="module", name="dns_integrator_metadata")
def dns_integrator_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../dns-integrator-operator/charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="dns_integrator_name")
def fixture_dns_integrator_name(dns_integrator_metadata):
    """Provide charm name from the metadata."""
    yield dns_integrator_metadata["name"]


@pytest.fixture(scope="module", name="bind_metadata")
def bind_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(
        pathlib.Path("../bind-operator/charmcraft.yaml").read_text(encoding="UTF-8")
    )


@pytest.fixture(scope="module", name="bind_name")
def fixture_bind_name(bind_metadata):
    """Provide charm name from the metadata."""
    yield bind_metadata["name"]


@pytest.fixture(scope="module", name="dns_policy_charm_file")
def dns_policy_charm_file_fixture(
    dns_policy_metadata: dict[str, typing.Any],
    pytestconfig: pytest.Config,
):
    """Pytest fixture that packs the charm and returns the filename, or --charm-file if set."""
    charm_file = pytestconfig.getoption("--charm-file", default=None)
    if charm_file:
        yield f"./{charm_file}"
        return
    try:
        subprocess.run(
            ["charmcraft", "pack"], check=True, capture_output=True, text=True
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = dns_policy_metadata["name"]
    charm_path = pathlib.Path()
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


@pytest.fixture(scope="module", name="bind_charm_file")
def bind_charm_file_fixture(
    bind_metadata: dict[str, typing.Any],
    pytestconfig: pytest.Config,
):
    """Pytest fixture that packs the bind charm and returns the filename."""
    charm_file = pytestconfig.getoption("--bind-charm-file", default=None)
    if charm_file:
        yield f"../bind-operator/{charm_file}"
        return
    yield _pack_charm(pathlib.Path("../bind-operator"), bind_metadata["name"])


@pytest.fixture(scope="module", name="dns_integrator_charm_file")
def dns_integrator_charm_file_fixture(
    dns_integrator_metadata: dict[str, typing.Any],
    pytestconfig: pytest.Config,
):
    """Pytest fixture that packs the dns-integrator charm and returns the filename."""
    charm_file = pytestconfig.getoption("--dns-integrator-charm-file", default=None)
    if charm_file:
        yield f"../dns-integrator-operator/{charm_file}"
        return
    yield _pack_charm(pathlib.Path("../dns-integrator-operator"), dns_integrator_metadata["name"])


@pytest.fixture(scope="module", name="dns_policy_snap_file")
def dns_policy_snap_file_fixture(pytestconfig: pytest.Config):
    """Pack the workload snap of this tree and return its path, or --snap-file if set."""
    snap_file = pytestconfig.getoption("--snap-file", default=None)
    if snap_file:
        yield str(pathlib.Path(snap_file).absolute())
        return
    yield _pack_snap(pathlib.Path("../charmed-dns-policy"))


@pytest.fixture(scope="module", name="dns_policy")
def dns_policy_fixture(
    juju: jubilant.Juju,
    dns_policy_charm_file: str,
    dns_policy_name: str,
    pytestconfig: pytest.Config,
):
    """Build the charm and deploy it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield dns_policy_name
        return

    juju.deploy(
        dns_policy_charm_file,
        dns_policy_name,
        resources={},
    )

    yield dns_policy_name


@pytest.fixture(scope="module", name="postgresql")
def postgresql_fixture(
    juju: jubilant.Juju,
):
    """Deploy the postgresql charm."""
    juju.deploy(
        "postgresql",
        channel="14/stable",
        config={"profile": "testing"},
    )
    juju.wait(lambda status: jubilant.all_active(status, "postgresql"), timeout=600)

    yield "postgresql"


@pytest.fixture(scope="module", name="bind")
def bind_fixture(
    juju: jubilant.Juju,
    bind_charm_file: str,
    bind_name: str,
    pytestconfig: pytest.Config,
):
    """Build the charm and deploy it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield bind_name
        return

    juju.deploy(bind_charm_file, bind_name, resources={})
    juju.wait(lambda status: jubilant.all_active(status, bind_name))

    yield bind_name


@pytest.fixture(scope="module", name="dns_integrator")
def dns_integrator_fixture(
    juju: jubilant.Juju,
    dns_integrator_charm_file: str,
    dns_integrator_name: str,
    pytestconfig: pytest.Config,
):
    """Build the dns-integrator charm and deploy it."""
    use_existing = pytestconfig.getoption("--use-existing", default=False)
    if use_existing:
        yield dns_integrator_name
        return

    juju.deploy(dns_integrator_charm_file, dns_integrator_name, resources={})

    yield dns_integrator_name


@pytest.fixture(scope="module", name="full_deployment")
def full_deployment_fixture(
    juju: jubilant.Juju,
    bind,
    dns_policy,
    postgresql,
    dns_policy_snap_file: str,
):
    """Add necessary integration for the deployed charms."""
    juju.integrate(dns_policy, postgresql)
    juju.integrate(dns_policy, bind)

    juju.wait(lambda status: jubilant.all_active(status, dns_policy), timeout=600)

    _sideload_snap(juju, f"{dns_policy}/0", dns_policy_snap_file)
    juju.wait(lambda status: jubilant.all_active(status, dns_policy), timeout=600)

    yield {
        bind: bind,
        dns_policy: dns_policy,
        postgresql: postgresql,
    }


@pytest.fixture(scope="module", name="ddns_domain")
def ddns_domain_fixture():
    """Provide the suffix the automatically allocated domains are tested with."""
    yield DDNS_DOMAIN


@pytest.fixture(scope="module", name="ddns_deployment")
def ddns_deployment_fixture(
    juju: jubilant.Juju,
    dns_policy_name: str,
    dns_integrator_name: str,
    full_deployment,  # pylint: disable=unused-argument
    dns_integrator,  # pylint: disable=unused-argument
):
    """Integrate a requirer with the dns-policy charm, with the ddns feature enabled."""
    with _configured_ddns_domain(juju, dns_policy_name, DDNS_DOMAIN):
        juju.config(dns_integrator_name, {"requests": INTEGRATOR_REQUEST})
        juju.integrate(
            f"{dns_integrator_name}:dns-record", f"{dns_policy_name}:dns-record-provider"
        )
        juju.wait(
            lambda status: jubilant.all_active(status, dns_policy_name, dns_integrator_name),
            error=jubilant.any_error,
            timeout=600,
        )
        yield dns_integrator_name


@pytest.fixture(name="ddns_domain_config")
def ddns_domain_config_fixture(
    request: pytest.FixtureRequest,
    juju: jubilant.Juju,
    dns_policy_name: str,
    ddns_deployment,  # pylint: disable=unused-argument
):
    """Set the ddns-domain configuration of a test, and restore it afterwards.

    The suffix the deployment was set up with is configured by default. Tests needing
    another one pass it through an indirect parametrization of this fixture.

    Yields:
        the configured suffix of the automatically allocated domains
    """
    domain = getattr(request, "param", DDNS_DOMAIN)
    with _configured_ddns_domain(juju, dns_policy_name, domain) as configured:
        yield configured
