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
