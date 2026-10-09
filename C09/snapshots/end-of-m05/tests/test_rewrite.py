"""Query rewriting replayed from the recordings (chat-small, recorded 2026-10-09)."""

from policy_assistant.evaluate import load_questions
from policy_assistant.providers import MockProvider
from policy_assistant.rewrite import build_request, rewrite

QS = load_questions()


def test_a_french_question_becomes_an_english_query():
    query = rewrite(QS["Q63"].question, MockProvider())
    assert query and "gift card" in query.lower()


def test_rewrites_keep_product_codes():
    assert "PW-2200" in rewrite(QS["Q38"].question, MockProvider())


def test_a_real_rewrite_with_stray_characters():
    """A real recorded rewrite ends with characters that are not part of the query: rewriting adds new ways to fail."""
    assert rewrite(QS["Q05"].question, MockProvider()).endswith("】【。")


def test_the_request_is_the_recorded_one():
    request = build_request(QS["Q01"].question, "chat-small")
    assert request["max_completion_tokens"] == 1000 and request["messages"][1]["content"] == QS["Q01"].question
