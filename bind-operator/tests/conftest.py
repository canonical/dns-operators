# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: the parser
    """
    parser.addoption("--charm-file", action="store", default=None)
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="This will skip deployment of the charms. Useful for local testing.",
    )
    parser.addoption("--model", action="store", default=None)
    parser.addoption("--keep-models", action="store_true", default=False)
