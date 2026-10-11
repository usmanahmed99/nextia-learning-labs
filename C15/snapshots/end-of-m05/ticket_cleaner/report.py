from ticket_cleaner.parsing import clean_category
from ticket_cleaner.records import Rejected, Ticket


def filter_by_status(tickets: list[Ticket], status: str = "open") -> list[Ticket]:
    """Return the tickets that have the given status."""
    return [ticket for ticket in tickets if ticket.status == status]


def count_by_category(tickets: list[Ticket]) -> dict[str, int]:
    """Return the number of tickets in each category, sorted by category."""
    counts = {}
    for ticket in tickets:
        counts[ticket.category] = counts.get(ticket.category, 0) + 1
    return dict(sorted(counts.items()))


def average_priority(tickets: list[Ticket]) -> float | None:
    """Return the average priority, or None when there are no tickets."""
    if not tickets:
        return None
    return round(sum(ticket.priority for ticket in tickets) / len(tickets), 1)


def build_summary(
    tickets: list[Ticket],
    rejected: list[Rejected],
    status: str,
    categories: list[str] | None = None,
) -> dict:
    """Return the report as a dictionary that can be saved as JSON.

    With categories, only the tickets in one of them are selected. The names are
    cleaned as the tickets' categories are (clean_category). The "categories"
    key is added only then, so the report without it is unchanged.
    """
    selected = filter_by_status(tickets, status)
    chosen = None
    if categories is not None:
        chosen = sorted({clean_category(name) for name in categories})
        selected = [ticket for ticket in selected if ticket.category in chosen]
    summary = {
        "status": status,
        "valid_records": len(tickets),
        "selected": len(selected),
        "by_category": count_by_category(selected),
        "average_priority": average_priority(selected),
        "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
    }
    if chosen is not None:
        summary["categories"] = chosen
    return summary
