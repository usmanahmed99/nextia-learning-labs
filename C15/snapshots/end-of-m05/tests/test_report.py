import pytest

from ticket_cleaner.records import Rejected, Ticket
from ticket_cleaner.report import average_priority, build_summary, count_by_category


@pytest.fixture
def tickets():
    return [
        Ticket(id="T-1", status="open", category="login", priority=1),
        Ticket(id="T-2", status="open", category="billing", priority=1),
        Ticket(id="T-3", status="closed", category="billing", priority=2),
    ]


def test_average_priority_of_no_tickets_is_none():
    assert average_priority([]) is None


def test_average_priority_is_rounded_to_one_decimal(tickets):
    assert average_priority(tickets) == 1.3


def test_categories_are_in_alphabetical_order(tickets):
    assert list(count_by_category(tickets)) == ["billing", "login"]


def test_summary_for_a_status_with_no_tickets(tickets):
    summary = build_summary(tickets, [], status="pending")
    assert summary["selected"] == 0
    assert summary["by_category"] == {}
    assert summary["average_priority"] is None


def test_whole_file_counts_do_not_depend_on_the_status(tickets):
    rejected = [Rejected(row=4, problems=["missing id"])]
    for status in ("open", "pending", "closed"):
        summary = build_summary(tickets, rejected, status=status)
        assert summary["valid_records"] == 3
        assert summary["rejected"] == [{"row": 4, "problems": ["missing id"]}]


def test_one_category(tickets):
    summary = build_summary(tickets, [], status="open", categories=["billing"])
    assert summary["selected"] == 1
    assert summary["by_category"] == {"billing": 1}
    assert summary["average_priority"] == 1.0


def test_a_ticket_in_any_chosen_category_counts(tickets):
    summary = build_summary(tickets, [], "open", categories=["billing", "login"])
    assert summary["selected"] == 2
    assert summary["by_category"] == {"billing": 1, "login": 1}


def test_category_name_ignores_capital_letters_and_spaces(tickets):
    summary = build_summary(tickets, [], "open", categories=[" Billing "])
    assert summary["by_category"] == {"billing": 1}
    assert summary["categories"] == ["billing"]


def test_unknown_category_selects_nothing(tickets):
    summary = build_summary(tickets, [], "open", categories=["garden"])
    assert summary["selected"] == 0
    assert summary["by_category"] == {}
    assert summary["average_priority"] is None


def test_categories_key_only_with_the_option(tickets):
    assert "categories" not in build_summary(tickets, [], "open")
    summary = build_summary(tickets, [], "open", categories=["login", "Billing"])
    assert summary["categories"] == ["billing", "login"]


def test_categories_do_not_change_the_whole_file_counts(tickets):
    rejected = [Rejected(row=4, problems=["missing id"])]
    summary = build_summary(tickets, rejected, "open", categories=["login"])
    assert summary["valid_records"] == 3
    assert summary["rejected"] == [{"row": 4, "problems": ["missing id"]}]


def test_web_form_names_work_in_the_category_option(tickets):
    summary = build_summary(tickets, [], "open", categories=["Sign-in"])
    assert summary["by_category"] == {"login": 1}
    assert summary["categories"] == ["login"]
