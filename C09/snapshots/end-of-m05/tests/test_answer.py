import json

import pytest

from policy_assistant.answer import AnswerProblem, build_request, parse_answer
from policy_assistant.context import Context
from policy_assistant.providers import Completion, request_key


def completion(text, finish="stop", refusal=None):
    return Completion(text, finish, refusal, "m", 0, 0, 0, 0.0, {})


def test_valid_answer():
    a = parse_answer(completion(json.dumps({"answerable": True, "answer": "30 days.",
                                            "claims": [{"text": "30 days.", "chunk_ids": ["abc"]}]})))
    assert a.answerable and a.cited() == ["abc"] and a.text() == "30 days. 30 days."


@pytest.mark.parametrize("comp, reason", [
    (completion('{"answerable": true, "answer": "30 d', "length"), "cut"),
    (completion(None, refusal="I can't help with that."), "refused"),
    (completion("The return window is 30 days."), "not a valid answer"),
    (completion('{"answerable": true, "answer": "x"}'), "not a valid answer"),       # no claims
])
def test_unusable_answers(comp, reason):
    with pytest.raises(AnswerProblem, match=reason):
        parse_answer(comp)


def test_request_is_stable_and_strict():
    r1 = build_request("Q?", "2026-10-09", Context(), "chat-small")
    r2 = build_request("Q?", "2026-10-09", Context(), "chat-small")
    assert request_key(r1) == request_key(r2)
    assert r1["response_format"]["json_schema"]["strict"] is True
    assert "Question date: 2026-10-09" in r1["messages"][1]["content"]
