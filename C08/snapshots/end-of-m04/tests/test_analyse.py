"""The whole path for one ticket."""
from assistant.analyse import analyse_ticket


def test_normal_ticket_with_an_order_lookup(mock, tickets):
    outcome = analyse_ticket(tickets["T-80008"], mock, "chat-small")
    assert outcome.status == "valid" and outcome.analysis.team == "delivery"
    assert [s.outcome for s in outcome.steps] == ["ok"]


def test_a_blocked_identifier_still_gives_a_checked_answer(mock, tickets):
    outcome = analyse_ticket(tickets["T-80001"], mock, "chat-small")
    assert [s.outcome for s in outcome.steps] == ["refused: other_customer"]
    assert outcome.status == "valid" and outcome.analysis.needs_human is True


def test_invalid_output_is_rejected_not_saved(mock, tickets):
    outcome = analyse_ticket(tickets["T-80002"], mock, "gemma3:4b", prompt="v1", structured=False, tools=False)
    assert outcome.status == "rejected" and [p.code for p in outcome.problems] == ["malformed_json"]


def test_a_provider_error_is_a_failed_outcome_not_a_crash(mock, tickets):
    outcome = analyse_ticket(tickets["T-80008"], mock, "chat-strong")  # real 400: no tools on this deployment
    assert outcome.status == "failed" and "HTTP 400" in outcome.error
