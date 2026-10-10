from dataclasses import dataclass

STATUSES = {"open", "pending", "closed"}
PRIORITIES = {1, 2, 3}
REQUIRED_FIELDS = ("id", "status", "category", "priority")
# The new web form uses other names for some categories. The report uses ours.
CATEGORY_ALIASES = {
    "sign-in": "login",
    "log-in": "login",
    "invoice": "billing",
    "delivery": "shipping",
}


@dataclass(frozen=True)
class Ticket:
    """One valid support ticket."""

    id: str
    status: str
    category: str
    priority: int

    def is_urgent(self) -> bool:
        """Return True for priority 1, the most urgent level."""
        return self.priority == 1


@dataclass(frozen=True)
class Rejected:
    """An input record that is not a valid ticket, and why."""

    row: int
    problems: list[str]
