from ticket_cleaner.records import (
    CATEGORY_ALIASES,
    PRIORITIES,
    REQUIRED_FIELDS,
    STATUSES,
    Rejected,
    Ticket,
)


def clean_text(value: object) -> str:
    """Return the value as text with no outer spaces, in small letters."""
    if value is None:
        return ""
    return str(value).strip().lower()


def clean_category(value: object) -> str:
    """Return the category, with the web form's names changed to the report's names."""
    text = str(value).strip()
    return CATEGORY_ALIASES.get(text.lower(), text)


def find_problems(raw: dict) -> list[str]:
    """Return a list of problems with one raw record. An empty list means valid."""
    if not isinstance(raw, dict):
        return ["not a record"]
    problems = []
    for field in REQUIRED_FIELDS:
        if clean_text(raw.get(field)) == "":
            problems.append(f"missing {field}")

    status = clean_text(raw.get("status"))
    if status and status not in STATUSES:
        problems.append(f"unknown status {status!r}")

    priority = clean_text(raw.get("priority"))
    if priority and not (priority.isdigit() and int(priority) in PRIORITIES):
        problems.append(f"priority must be 1, 2 or 3, not {priority!r}")
    return problems


def to_ticket(raw: dict) -> Ticket:
    """Make a Ticket from a raw record that has no problems."""
    return Ticket(
        id=clean_text(raw["id"]).upper(),
        status=clean_text(raw["status"]),
        category=clean_category(raw["category"]),
        priority=int(clean_text(raw["priority"])),
    )


def split_records(rows: list[dict]) -> tuple[list[Ticket], list[Rejected]]:
    """Separate valid tickets from rejected records. Nothing is dropped silently."""
    tickets = []
    rejected = []
    seen_ids = set()
    for row_number, raw in enumerate(rows, start=1):
        problems = find_problems(raw)
        if not problems:
            ticket = to_ticket(raw)
            if ticket.id in seen_ids:
                problems.append(f"duplicate id {ticket.id}")
        if problems:
            rejected.append(Rejected(row=row_number, problems=problems))
        else:
            tickets.append(ticket)
            seen_ids.add(ticket.id)
    return tickets, rejected
