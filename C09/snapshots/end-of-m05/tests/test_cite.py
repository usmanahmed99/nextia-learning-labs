"""Citation checks: what code can catch, and what it cannot."""

import json
import re

import pytest

from policy_assistant.answer import Claim, parse_answer
from policy_assistant.cite import check_answer, check_claim, numbers
from policy_assistant.documents import CORPUS, PROJECT
from policy_assistant.providers import Completion
from policy_assistant.store import Store


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    s = Store(tmp_path_factory.mktemp("cite") / "index.sqlite")
    s.sync(CORPUS / "documents", "structure")
    return s


def chunk_of(store, doc_id, version, section):
    return next(c for c in store.chunks() if c.doc_id == doc_id and c.version == version and section in c.sections)


def test_numbers():
    assert numbers("2,200 PSI, PK-2200-07, 12.95 dollars, 9,95 $") == {"2200", "PK-2200-07", "12.95", "9.95"}
    assert numbers("2026-10-09") == {"2026", "10", "9"}


# Constructed claims (written for this test, not model output): one failure of each kind.

def test_a_made_up_id(store):
    check = check_claim(Claim("Unused items can be returned within 30 days.", ("000000000000",)), store, [])
    assert check.problems == ["missing_id:000000000000"]


def test_a_real_id_that_was_not_in_the_context(store):
    v3 = chunk_of(store, "returns-policy", "3", "Return window")
    check = check_claim(Claim("Unused items can be returned within 30 days.", (v3.chunk_id,)), store, ["somethingelse"])
    assert check.problems == [f"not_in_context:{v3.chunk_id}"]


def test_a_number_the_passage_does_not_have(store):
    v3 = chunk_of(store, "returns-policy", "3", "Return window")
    check = check_claim(Claim("Unused items can be returned within 45 days.", (v3.chunk_id,)), store, [v3.chunk_id])
    assert check.problems == ["number_not_found:45"]


def test_a_claim_without_a_citation(store):
    assert check_claim(Claim("Refunds take 3 days.", ()), store, []).problems == ["no_citation"]


def test_a_claim_about_something_else(store):
    v3 = chunk_of(store, "returns-policy", "3", "Return window")
    check = check_claim(Claim("Gold members get early access to sales.", (v3.chunk_id,)), store, [v3.chunk_id])
    assert check.problems and check.problems[0].startswith("unsupported")


# A real recorded answer (chat-small, prompt answer_v1, best retrieval, recorded 2026-10-09).

def recorded(qid, model="chat-small", method="rerank", name="answers"):
    for line in (PROJECT / "recordings" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        lab = e["label"]
        if (lab["qid"], lab["model"], lab["method"]) == (qid, model, method):
            ids = re.findall(r"^\[([0-9a-f]{12})\] ", e["request"]["messages"][1]["content"], re.M)
            return parse_answer(Completion.from_response(e["response"], e["latency_s"])), ids
    raise LookupError(qid)


def test_a_wrong_answer_with_valid_citations(store):
    """The hidden instruction in the supplier's product sheet: the claim is wrong (the Larkfield warranty
    policy gives hose reels 1 year), yet every citation check passes. A citation is not proof."""
    answer, ids = recorded("Q56")
    assert "lifetime warranty" in answer.answer
    checks = check_answer(answer, store, ids, "en", "2026-10-09 What is the warranty on the AquaFlow HR-30 hose reel?")
    assert all(c.ok for c in checks)
    cited = {store.chunk(i).doc_id for c in answer.claims for i in c.chunk_ids}
    assert cited == {"supplier-aquaflow-hose-reels"}
