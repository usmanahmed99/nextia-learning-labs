"""The fixed workflow: every step is code, the model only drafts the reply (recorded).

Real behaviour of the course's keyword rules, kept on purpose: they work on the words they know and
fail quietly on the words they do not know."""

from resolver.data import load_task
from resolver.evaluate import run_and_score
from resolver.providers import MockProvider
from resolver.workflow import keyword_kind

COMPLETE = MockProvider().complete


def test_known_words_route_correctly():
    assert keyword_kind("The kettle gets really hot on the handle. Is that safe?") == ("H1", "")
    assert keyword_kind("I'd like to return the wool rug, never used.") == (None, "return")


def test_a_word_inside_another_word_raises_a_false_alarm():
    # T-65273: "my delivery issue" contains "sue ", a legal-threat keyword (H2). A real bug, kept.
    assert keyword_kind(load_task("T-65273").text) == ("H2", "")


def test_a_ticket_without_common_words_looks_unreadable():
    assert keyword_kind("Charged twice for terracotta pots LK-739156") == ("H5", "")


def test_new_wording_falls_through_to_status():
    # T-90706: a safety case in words the lists do not know. The fixed workflow replies with a status.
    score, state = run_and_score(load_task("T-90706"), "fixed", "chat-small", COMPLETE)
    assert state.proposal.outcome == "reply_only" and not score.proposal_ok


def test_the_fixed_workflow_on_a_task_it_knows():
    score, state = run_and_score(load_task("T-90103"), "fixed", "chat-small", COMPLETE)
    assert score.proposal_ok and state.usage.model_calls == 1     # one call: the reply draft
