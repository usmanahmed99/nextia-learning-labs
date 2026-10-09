"""Model judges: requests, both orders, and the recorded verdicts replayed by the mock."""

from harness.dataset import by_id, load_cases
from harness.judge import (combine, pairwise_request, parse_verdict, reference_notes, reference_request,
                           unswap)
from harness.providers import MockProvider
from harness.run import find_run, load_outputs


def test_both_orders_in_the_first_order_names():
    assert unswap("A", "B") == ("A", "A")         # A won in both orders: consistent
    assert combine(*unswap("A", "B")) == "A"
    assert combine(*unswap("A", "A")) == "inconsistent"  # the first position won both times
    assert combine(*unswap("tie", "tie")) == "tie"


def test_the_pairwise_judge_sees_no_reference_and_no_system_names():
    case = by_id(load_cases(split="all"))["T-81034"]
    request = pairwise_request(case, "first reply", "second reply", "chat-strong")
    text = request["messages"][1]["content"]
    assert "Reference notes" not in text and "baseline" not in text and "candidate" not in text
    assert text.index("first reply") < text.index("second reply")


def test_the_reference_notes_come_from_the_labels():
    case = by_id(load_cases(split="all"))["T-81034"]
    notes = reference_notes(case)
    assert "A person must handle the ticket: yes (H4 access)" in notes
    assert "share or discuss details of another customer's order or account" in notes


def test_a_recorded_verdict_is_replayed():
    case = by_id(load_cases(split="all"))["T-64709"]
    out = load_outputs(find_run("baseline"))["T-64709"]
    request = reference_request(case, out.reply, out.answer["needs_human"], "chat-strong")
    verdict = parse_verdict(MockProvider().complete(request))
    assert verdict.score in (1, 2, 3, 4, 5) and verdict.reason


def test_the_content_filter_refused_to_judge_the_injection_ticket():
    """Real (2026-10-09): Azure's filter saw a jailbreak in the judge prompt that quotes ticket T-81040."""
    import pytest

    from harness.providers import ProviderError

    case = by_id(load_cases(split="all"))["T-81040"]
    out = load_outputs(find_run("baseline"))["T-81040"]
    with pytest.raises(ProviderError, match="content_filter"):
        MockProvider().complete(reference_request(case, out.reply, out.answer["needs_human"], "chat-strong"))
