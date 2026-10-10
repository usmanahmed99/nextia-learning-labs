"""Adversarial and recovery tests on recorded runs (Module 6): what reaches the database when every
proposal is approved as it is, and what each design does with instructions in tool results."""

from resolver.data import load_tasks
from resolver.evaluate import run_and_score
from resolver.providers import MockProvider

TASKS = load_tasks()


def test_no_design_follows_an_instruction_in_a_tool_result():
    for variant, model in (("agent", "chat-small"), ("agent_structured", "chat-strong"), ("fixed", "chat-small")):
        for task_id in ("T-90501", "T-90504", "T-64856"):
            score, _ = run_and_score(TASKS[task_id], variant, model, MockProvider().complete)
            assert not score.forbidden and not score.said, (variant, task_id)


def test_a_timeout_after_a_write_never_becomes_a_duplicate():
    for variant, model in (("agent", "chat-small"), ("agent_structured", "chat-strong")):
        score, state = run_and_score(TASKS["T-90603"], variant, model, MockProvider().complete)
        refunds = [c for c in score.changes if c["tool"] == "request_refund"]
        assert len(refunds) <= 1, variant
