# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests fixtures."""

import pathlib
import subprocess  # nosec B404
import typing

import jubilant
import pytest


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
    target_directory: pathlib.Path,
) -> str:
    """Pack the charm and returns the filename.
    Args:
        metadata: charm's metadata
        target_directory: path to the directory of the charmcraft file
    Returns:
        charm file's path
    Raises:
        OSError: if error while packing the charm
    """
    try:
        subprocess.run(
            ["charmcraft", "pack"],
            capture_output=True,
            check=True,
            cwd=target_directory,
            text=True,
        )  # nosec B603, B607
    except subprocess.CalledProcessError as exc:
        raise OSError(f"Error packing charm: {exc}; Stderr:\n{exc.stderr}") from None

    app_name = metadata["name"]
    charm_path = pathlib.Path(target_directory)
    charms = [p.absolute() for p in charm_path.glob(f"{app_name}_*.charm")]
    assert charms, f"{app_name}.charm file not found"
    assert len(charms) == 1, f"{app_name} has more than one .charm file, unsure which to use"
    return str(charms[0])
