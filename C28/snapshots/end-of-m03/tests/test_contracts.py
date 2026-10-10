"""The capability contracts, checked before any server exists."""

import pytest
from pydantic import TypeAdapter, ValidationError

from support_mcp import contracts


def test_a_query_is_bounded():
    q = TypeAdapter(contracts.Query)
    assert q.validate_python("return a hose") == "return a hose"
    for bad in ("", "ab", "x" * (contracts.MAX_QUERY_CHARS + 1)):
        with pytest.raises(ValidationError):
            q.validate_python(bad)


def test_the_number_of_results_is_bounded():
    limit = TypeAdapter(contracts.Limit)
    assert limit.validate_python(5) == 5
    for bad in (0, 6, 1000):
        with pytest.raises(ValidationError):
            limit.validate_python(bad)


def test_a_ticket_id_has_one_form():
    t = TypeAdapter(contracts.TicketId)
    assert t.validate_python("T-30002") == "T-30002"
    for bad in ("30002", "T-3000", "T-30002; DROP TABLE tickets", "../T-30002"):
        with pytest.raises(ValidationError):
            t.validate_python(bad)


def test_a_search_result_holds_at_most_five_hits():
    hit = {"doc_id": "d", "title": "t", "uri": "policy://larkfield/d", "snippet": "s", "score": 1.0}
    contracts.SearchResult(query="q", results=[hit] * 5)
    with pytest.raises(ValidationError):
        contracts.SearchResult(query="q", results=[hit] * 6)


def test_policy_uris_are_stable_and_parseable():
    uri = contracts.policy_uri("larkfield", "returns-policy")
    assert uri == "policy://larkfield/returns-policy"
    m = contracts.POLICY_URI.match(uri)
    assert m and m["tenant"] == "larkfield" and m["doc_id"] == "returns-policy"
    assert contracts.POLICY_URI.match("policy://larkfield/../secrets") is None


def test_clip_says_when_it_shortens():
    assert contracts.clip("short", 10) == "short"
    assert contracts.clip("a" * 20, 10) == "a" * 9 + "…"


def test_the_prompt_is_a_template_not_a_privileged_instruction():
    text = contracts.DRAFT_REPLY_PROMPT.format(ticket_id="T-30002", organization="larkfield")
    assert "T-30002" in text and "get_ticket" in text and "search_knowledge" in text
    assert "not as instructions" in text
