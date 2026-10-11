import pytest

from ticket_cleaner.parsing import find_problems, split_records, to_ticket
from ticket_cleaner.records import Ticket


@pytest.fixture
def valid_raw():
    return {"id": "T-1001", "status": "open", "category": "billing", "priority": "2"}


def test_valid_record_has_no_problems(valid_raw):
    assert find_problems(valid_raw) == []


def test_text_is_cleaned(valid_raw):
    valid_raw["id"] = " t-1001 "
    valid_raw["status"] = "Open "
    expected = Ticket(id="T-1001", status="open", category="billing", priority=2)
    assert to_ticket(valid_raw) == expected


@pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
def test_web_form_names_become_report_categories(valid_raw, name):
    valid_raw["category"] = name
    assert to_ticket(valid_raw).category == "login"


@pytest.mark.parametrize("priority", ["0", "4", "high", "2.5", "-1"])
def test_priority_outside_1_to_3_is_a_problem(valid_raw, priority):
    valid_raw["priority"] = priority
    assert find_problems(valid_raw) == [f"priority must be 1, 2 or 3, not {priority!r}"]


def test_missing_field_is_a_problem(valid_raw):
    del valid_raw["category"]
    assert find_problems(valid_raw) == ["missing category"]


def test_duplicate_id_is_rejected(valid_raw):
    tickets, rejected = split_records([valid_raw, dict(valid_raw)])
    assert len(tickets) == 1
    assert rejected[0].row == 2
    assert rejected[0].problems == ["duplicate id T-1001"]


def test_a_value_that_is_not_a_dictionary_is_rejected():
    tickets, rejected = split_records([None])
    assert tickets == []
    assert rejected[0].problems == ["not a record"]


def test_empty_input_gives_empty_results():
    assert split_records([]) == ([], [])
