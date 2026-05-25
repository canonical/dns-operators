# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest
import yaml


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


@pytest.fixture(scope="module", name="bind_metadata")
def bind_metadata_fixture():
    """Provide charm metadata."""
    yield yaml.safe_load(pathlib.Path("../bind-operator/charmcraft.yaml").read_text(encoding="UTF-8"))


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
    bind_directory = pathlib.Path("../bind-operator")
    try:
        subprocess.run(
            ["charmcraft", "pack"],
            capture_output=True,
            check=True,
            cwd=bind_directory,
            text=True,
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = bind_metadata["name"]
    charms = [p.absolute() for p in bind_directory.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    yield str(charms[0])


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
        num_units=0,  # subordinate charm
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


@pytest.fixture(scope="module", name="full_deployment")
def full_deployment_fixture(
    juju: jubilant.Juju,
    bind,
    dns_policy,
    postgresql,
):
    """Add necessary integration for the deployed charms."""
    juju.integrate(dns_policy, postgresql)
    juju.integrate(dns_policy, bind)

    juju.wait(lambda status: jubilant.all_active(status, dns_policy), timeout=600)

    yield {
        bind: bind,
        dns_policy: dns_policy,
        postgresql: postgresql,
    }
