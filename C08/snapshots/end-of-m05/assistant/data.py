"""The course data: Larkfield's tickets (the 69-ticket evaluation set) and where the files are."""

import csv
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TICKETS_CSV = DATA_DIR / "tickets.csv"
ORDERS_DB = DATA_DIR / "orders.sqlite"


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    customer_id: str   # who sent the ticket: the help-desk app knows it, the model does not need it
    text: str
    attachments: str = ""
    team: str = ""                    # the expected team (evaluation only)
    needs_human: bool | None = None   # the expected value (evaluation only)
    style: str = ""


def load_tickets(path: Path = TICKETS_CSV) -> dict[str, Ticket]:
    with path.open(encoding="utf-8", newline="") as f:
        return {
            row["ticket_id"]: Ticket(
                ticket_id=row["ticket_id"],
                customer_id=row["customer_id"],
                text=row["text"],
                attachments=row["attachments"],
                team=row["team"],
                needs_human=row["needs_human"] == "true",
                style=row["style"],
            )
            for row in csv.DictReader(f)
        }


def load_ticket(ticket_id: str) -> Ticket:
    tickets = load_tickets()
    if ticket_id not in tickets:
        raise KeyError(f"No ticket {ticket_id} in {TICKETS_CSV.name}")
    return tickets[ticket_id]
