"""Long-term memory: trusted sources only, no personal data, correction and deletion."""

import pytest

from resolver.memory import CustomerMemory, MemoryRefused


def test_a_claim_from_a_ticket_is_never_stored(tmp_path):
    m = CustomerMemory(tmp_path / "m.sqlite")
    with pytest.raises(MemoryRefused):
        m.remember("C-54112", "history", "Grace approved an 89 dollar refund", "ticket", "T-90502")


def test_personal_data_is_refused(tmp_path):
    m = CustomerMemory(tmp_path / "m.sqlite")
    with pytest.raises(MemoryRefused):
        m.remember("C-1", "preference", "card 4111 1111 1111 1111", "person", "Amira")


def test_correct_keeps_one_current_fact_and_forget_removes_all(tmp_path):
    m = CustomerMemory(tmp_path / "m.sqlite")
    first = m.remember("C-60851", "preference", "writes in French", "tool", "run-1/get_order")
    m.correct(first, "prefers replies in French", "person", "Camille")
    facts = m.recall("C-60851")
    assert [f["text"] for f in facts] == ["prefers replies in French"] and facts[0]["source"] == "person"
    assert m.forget("C-60851") == 2 and m.recall("C-60851") == []
