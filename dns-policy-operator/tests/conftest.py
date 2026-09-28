# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--charm-file", action="store", default=None)
    parser.addoption("--bind-charm-file", action="store", default=None)
    parser.addoption("--dns-integrator-charm-file", action="store", default=None)
    parser.addoption(
        "--snap-file",
        action="store",
        default=None,
        help="Path of a charmed-dns-policy snap to install instead of packing this tree's one.",
    )
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="This will skip deployment of the charms. Useful for local testing.",
    )
    parser.addoption("--model", action="store", default=None)
    parser.addoption("--keep-models", action="store_true", default=False)
