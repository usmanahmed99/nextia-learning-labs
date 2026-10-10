"""The trust-boundary map (trust_boundaries.json) matches the code: every tool is described, and only
the shop's own instructions are trusted."""

from support_assistant.boundaries import check, load


def test_the_map_describes_every_tool_in_the_code():
    assert check(load()) == []


def test_only_the_system_prompt_and_the_team_request_are_trusted():
    trusted = {s["name"] for s in load()["sources"] if s["trusted"]}
    assert trusted == {"system prompt", "team member's request"}


def test_a_tool_missing_from_the_map_is_reported():
    m = load()
    del m["tools"]["fetch_url"]
    assert any("fetch_url" in p for p in check(m))
