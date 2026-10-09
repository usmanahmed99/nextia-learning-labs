"""The whole path for one ticket. Rate limits and timeouts are SIMULATED (assistant/simulate.py)."""
from assistant.analyse import analyse_ticket
from assistant.retry import RetryPolicy
from assistant.simulate import SimulatedProvider
from assistant.usage import UsageLog


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


def test_a_simulated_rate_limit_is_retried(mock, tickets, tmp_path):
    provider = SimulatedProvider(mock, ["rate_limit:0.01", "timeout"])
    log = UsageLog(tmp_path / "usage.jsonl")
    outcome = analyse_ticket(tickets["T-80008"], provider, "chat-small", log=log)
    assert outcome.status == "valid" and provider.calls == 4  # 2 simulated failures + 2 real recorded steps
    assert len(log.entries()) == 2 and log.entries()[0]["cost_usd"] > 0


def test_a_provider_that_keeps_timing_out_gives_up(mock, tickets):
    provider = SimulatedProvider(mock, ["timeout"] * 10)
    outcome = analyse_ticket(tickets["T-80008"], provider, "chat-small", retry=RetryPolicy(base_s=0.001))
    assert outcome.status == "failed" and "timeout" in outcome.error and provider.calls == 4
