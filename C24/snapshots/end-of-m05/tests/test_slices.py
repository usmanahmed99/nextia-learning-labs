"""Slice tests: the French and German tickets are measured on their own, not hidden in an average, and
a reply goes out in the customer's language. Replayed from the recordings."""

import re

from support_assistant.config import Settings, make_provider
from support_assistant.data import load_tasks
from support_assistant.evaluate import summarise
from support_assistant.runner import run_and_score

WORDS = {"fr": r"\b(vous|votre|nous|est|le|la|les|de)\b", "de": r"\b(Sie|Ihre|Ihr|und|der|die|das|ist)\b"}


def _run(design, language):
    complete = make_provider(Settings(provider="mock")).complete
    cases = [c for c in load_tasks().values() if c.language == language]
    return [(c, *run_and_score(c, complete, "chat-small", design)) for c in cases]


def test_each_language_has_its_own_slice():
    rows = _run("secure", "fr") + _run("secure", "de")
    by_slice = summarise([score for _, _, score in rows])["by_slice"]
    assert set(by_slice) == {"french", "german"}
    assert by_slice["french"].endswith("/3") and by_slice["german"].endswith("/2")


def test_a_finished_reply_is_in_the_customers_language():
    for language in ("fr", "de"):
        for case, state, _ in _run("secure", language):
            if state.stop_reason == "finished" and state.answer:
                assert len(re.findall(WORDS[language], state.answer)) >= 2, (case.case_id, state.answer[:80])


def test_hardening_does_not_make_a_language_slice_worse():
    for language in ("fr", "de"):
        weak = sum(score["success"] for _, _, score in _run("start", language))
        secure = sum(score["success"] for _, _, score in _run("secure", language))
        assert secure >= weak, language
