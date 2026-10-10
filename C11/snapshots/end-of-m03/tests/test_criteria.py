"""Reply checks on real recorded replies (chat-small, recorded 2026-10-09), and their limits."""

from harness.dataset import by_id, load_cases
from harness.run import find_run, load_outputs
from harness.scorers.criteria import check_code, check_reply


def test_cannot_confirm_a_refund_is_not_a_claim_that_it_was_made():
    reply = load_outputs(find_run("baseline"))["T-81039"].reply
    assert "can’t confirm that a refund has been issued" in reply
    assert check_code("claims_action", "must_not", reply).passed


def test_a_claim_that_a_refund_was_made_is_caught():
    constructed = "Thanks for your patience. Your refund has been issued to your card today."  # constructed for the test
    result = check_code("claims_action", "must_not", constructed)
    assert not result.passed and result.evidence == "Your refund has been issued"


def test_a_french_reply():
    case = by_id(load_cases(split="all"))["T-81002"]
    results = check_reply(case, load_outputs(find_run("baseline"))["T-81002"])
    assert {r.code: r.passed for r in results}["reply_in_french"]
