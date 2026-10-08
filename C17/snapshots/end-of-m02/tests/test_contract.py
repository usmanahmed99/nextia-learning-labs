import pytest
from pydantic import ValidationError

from escalation.contract import FEATURES, TicketIn, to_frame, unknown_categories


def test_a_good_ticket_passes(ticket):
    assert TicketIn(**ticket).priority == 1


@pytest.mark.parametrize(
    "change, field",
    [
        ({"priority": "high"}, "priority"),
        ({"priority": 4}, "priority"),
        ({"created_hour": 24}, "created_hour"),
        ({"word_count": -1}, "word_count"),
        ({"channel": ""}, "channel"),
        ({"team": None}, "team"),
        ({"colour": "red"}, "colour"),
    ],
)
def test_a_bad_value_is_rejected(ticket, change, field):
    with pytest.raises(ValidationError) as error:
        TicketIn(**{**ticket, **change})
    assert field in str(error.value)


def test_null_is_allowed_only_where_the_contract_says(ticket):
    TicketIn(**{**ticket, "order_value": None, "customer_tenure_days": None})
    with pytest.raises(ValidationError):
        TicketIn(**{**ticket, "word_count": None})


def test_a_missing_field_is_not_the_same_as_null(ticket):
    del ticket["order_value"]
    with pytest.raises(ValidationError):
        TicketIn(**ticket)


def test_an_unknown_category_is_a_warning_not_an_error(ticket):
    known = {"channel": ["email"], "team": ["payment"], "segment": ["home"], "region": ["west"]}
    warnings = unknown_categories(TicketIn(**{**ticket, "channel": "social"}), known)
    assert warnings == ["channel: 'social' is a value the model never saw"]


def test_the_frame_has_the_training_columns_in_order(ticket):
    frame = to_frame([TicketIn(**{**ticket, "order_value": None})])
    assert list(frame.columns) == FEATURES
    assert frame["order_value"].isna().all()  # NaN for the imputer, not 0
