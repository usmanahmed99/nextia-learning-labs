"""Retrieval measures on a worked example of five questions (every value visible)."""

from types import SimpleNamespace

import pytest

from policy_assistant.evaluate import Question, answer_scores, load_questions, retrieval_scores, summarise


def q(qid, relevant, kind="answerable"):
    passages = [{"doc_id": d, "version": "1", "section": s, "access": "public"} for d, s in relevant]
    return Question(qid, "?", "en", kind, "2026-10-09", True, not relevant, "", [], [], passages, [], [], [], "")


def c(doc_id, section, access="public"):
    return SimpleNamespace(doc_id=doc_id, version="1", sections=(section,), access=access)


def test_five_questions_by_hand():
    rows = [
        retrieval_scores(q("A", [("d1", "s1")]), [c("d1", "s1"), c("x", "y"), c("x", "z")], 3),                   # rank 1
        retrieval_scores(q("B", [("d2", "s1")]), [c("x", "y"), c("x", "z"), c("d2", "s1")], 3),                   # rank 3
        retrieval_scores(q("C", [("d3", "s1"), ("d3", "s2")]), [c("d3", "s2"), c("x", "y"), c("x", "z")], 3),     # 1 of 2
        retrieval_scores(q("D", [("d4", "s1")]), [c("x", "y"), c("x", "z"), c("x", "w")], 3),                     # missed
        retrieval_scores(q("E", []), [c("x", "y")], 3),                                                           # unanswerable
    ]
    assert [r["hit"] for r in rows[:4]] == [1, 1, 1, 0]
    assert [r["recall"] for r in rows[:4]] == [1, 1, 0.5, 0]
    assert [r["rr"] for r in rows[:4]] == [1, pytest.approx(1 / 3), 1, 0]
    s = summarise(rows)
    assert s["questions"] == 4                       # E has no relevant passage: left out
    assert s["hit"] == 0.75 and s["recall"] == 0.625
    assert s["precision"] == pytest.approx(0.25)     # 3 relevant chunks of 12
    assert s["mrr"] == pytest.approx((1 + 1 / 3 + 1 + 0) / 4, abs=1e-3)


def test_staff_passages_do_not_count_for_a_public_audience():
    question = load_questions()["Q49"]
    staff_chunk = SimpleNamespace(doc_id="refund-approval-procedure", version="2",
                                  sections=("Approval limits for manual refunds",), access="staff")
    assert retrieval_scores(question, [staff_chunk], 1, "staff")["hit"] == 1
    public = retrieval_scores(question, [staff_chunk], 1, "public")
    assert public["scored"] is False and public["leaks"] == 1


def test_answer_checks():
    question = load_questions()["Q22"]
    good = SimpleNamespace(answerable=True, text=lambda: "No: 30 days from delivery.")
    abstain = SimpleNamespace(answerable=False, text=lambda: "The documents do not say.")
    assert answer_scores(question, good)["correct"] is True
    assert answer_scores(question, abstain)["correct"] is False
    assert answer_scores(load_questions()["Q14"], abstain)["correct"] is True      # unanswerable: abstaining is right
    assert answer_scores(question, None)["valid"] is False
