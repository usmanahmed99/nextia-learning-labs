"""The AI requests and how the API reads the answers (the scaling course, Module 1)."""

import pytest

from ticket_api import ai


def test_the_classify_request_asks_for_json_with_a_schema():
    body = ai.classify_request("Charged twice", "Two payments for one order.")
    assert body["model"] == "chat-small"
    assert body["response_format"]["json_schema"]["schema"]["required"] == ["team", "priority"]
    assert body["messages"][1]["content"] == "Subject: Charged twice\n\nTwo payments for one order."


def test_an_embedding_has_384_numbers():
    assert ai.embed_request("a", "b")["dimensions"] == 384
    with pytest.raises(ai.BadAnswer):
        ai.parse_embedding({"data": [{"embedding": [0.1] * 1536}]})


def test_a_classification_is_read_and_checked():
    answer = {"choices": [{"message": {"content": '{"team":"billing","priority":1}'}}]}
    assert ai.parse_classification(answer) == ai.Classification("billing", 1)
    for bad in ('{"team":"sales","priority":1}', '{"team":"billing","priority":7}', "billing"):
        with pytest.raises(ai.BadAnswer):
            ai.parse_classification({"choices": [{"message": {"content": bad}}]})


def test_an_empty_reply_is_not_a_draft():
    with pytest.raises(ai.BadAnswer):
        ai.parse_draft({"choices": [{"message": {"content": "  "}}]})
