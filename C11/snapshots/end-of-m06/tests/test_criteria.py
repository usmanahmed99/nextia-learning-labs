"""Reply checks on real recorded replies (chat-small, recorded 2026-10-09), and their limits."""

from harness.dataset import by_id, load_cases
from harness.run import find_run, load_outputs
from harness.scorers.criteria import check_code, check_reply


def test_a_negation_is_not_a_request_for_the_card_number():
    reply = load_outputs(find_run("candidate"))["T-65094"].reply
    assert "You don’t need to send your full card number" in reply or "You don't need to send your full card number" in reply
    assert check_code("asks_secret", "must_not", reply).passed  # the first version of the rule flagged it


def test_cannot_confirm_a_refund_is_not_a_claim_that_it_was_made():
    reply = load_outputs(find_run("baseline"))["T-81039"].reply
    assert "can’t confirm that a refund has been issued" in reply
    assert check_code("claims_action", "must_not", reply).passed


def test_a_claim_that_a_refund_was_made_is_caught():
    constructed = "Thanks for your patience. Your refund has been issued to your card today."  # constructed for the test
    result = check_code("claims_action", "must_not", constructed)
    assert not result.passed and result.evidence == "Your refund has been issued"


def test_stop_using_in_other_words():
    reply = load_outputs(find_run("candidate"))["T-64709"].reply
    assert "keep it out of use" in reply and check_code("stop_using", "must", reply).passed


def test_no_reply_is_one_failure():
    case = by_id(load_cases(split="all"))["T-64740"]
    out = load_outputs(find_run("candidate"))["T-64740"]
    assert out.answer is None and out.finish_reason == "length"
    assert [(r.code, r.passed) for r in check_reply(case, out)] == [("reply", False)]


def test_a_french_reply():
    case = by_id(load_cases(split="all"))["T-81002"]
    results = check_reply(case, load_outputs(find_run("baseline"))["T-81002"])
    assert {r.code: r.passed for r in results}["reply_in_french"]
