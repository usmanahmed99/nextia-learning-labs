"""Versions are part of the design: the pinned SDK must be the installed one and speak our revision."""

from importlib.metadata import version
from pathlib import Path

from mcp_types.version import LATEST_MODERN_VERSION

import support_mcp
from scripts import versions

ROOT = Path(__file__).resolve().parent.parent


def test_the_installed_sdk_is_the_pinned_one():
    assert version("mcp") == support_mcp.SDK_VERSION
    assert f"mcp=={support_mcp.SDK_VERSION}" in (ROOT / "requirements.txt").read_text()


def test_the_sdk_speaks_our_specification_revision():
    assert LATEST_MODERN_VERSION == support_mcp.SPEC_REVISION == "2026-07-28"


def test_the_version_report_names_everything():
    r = versions.report()
    assert r["specification revision (this project)"] == "2026-07-28"
    assert "2025-11-25" in r["older revisions it still accepts (initialize handshake)"]
