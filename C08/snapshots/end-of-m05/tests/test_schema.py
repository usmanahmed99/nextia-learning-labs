import pytest
from pydantic import ValidationError

from assistant.schema import TicketAnalysis, response_format

GOOD = {"language": "en", "team": "delivery", "needs_human": False, "reason": "Late order.", "confidence": "high",
        "order": {"order_id": "LK-581106", "status": None}, "reply": "We are checking your order."}


def test_a_good_answer_passes():
    assert TicketAnalysis.model_validate(GOOD).team == "delivery"


@pytest.mark.parametrize("change", [
    {"team": "shipping"},                                   # not one of the five teams
    {"needs_human": "maybe"},                               # not a boolean
    {"order": {"order_id": "LK-55190", "status": None}},    # not LK- and 6 digits
    {"order": {"order_id": "LK-581106", "status": "lost"}},  # not a known status
    {"reply": ""},                                          # empty reply
    {"extra": "field"},                                     # a field the contract does not have
])
def test_impossible_answers_are_rejected(change):
    with pytest.raises(ValidationError):
        TicketAnalysis.model_validate({**GOOD, **change})


def test_a_missing_field_is_rejected():
    answer = dict(GOOD)
    del answer["needs_human"]
    with pytest.raises(ValidationError):
        TicketAnalysis.model_validate(answer)


def test_the_schema_sent_to_the_provider_is_strict():
    rf = response_format()
    schema = rf["json_schema"]["schema"]
    assert rf["json_schema"]["strict"] is True
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])  # strict mode: every field is required
