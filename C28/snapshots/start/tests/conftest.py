"""Shared test helpers."""

import pytest

from support_mcp.knowledge import Knowledge


@pytest.fixture(scope="session")
def knowledge():
    return Knowledge()
