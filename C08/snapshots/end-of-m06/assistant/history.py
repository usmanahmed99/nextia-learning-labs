"""Conversation state: the model remembers nothing, so the application keeps and resends the history.

An agent can ask follow-up questions about a ticket ("make the reply shorter"). Each (agent, ticket)
pair has its own conversation, and only the newest turns that fit in the token budget are sent.
"""

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """A rough count: about 4 characters per token for English. Use the provider's usage for exact numbers."""
    return max(1, len(text) // 4)


@dataclass
class Conversation:
    system: str
    budget_tokens: int = 3000
    turns: list[dict] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})

    def messages(self) -> list[dict]:
        """The system message, then the newest turns that fit in the budget (the oldest are cut first)."""
        used = estimate_tokens(self.system)
        kept = []
        for turn in reversed(self.turns):
            cost = estimate_tokens(turn["content"])
            if kept and used + cost > self.budget_tokens:  # the newest turn is always kept
                break
            kept.insert(0, turn)
            used += cost
        return [{"role": "system", "content": self.system}] + kept

    def dropped(self) -> int:
        return len(self.turns) - (len(self.messages()) - 1)


class ConversationStore:
    """One conversation per agent and ticket. Never one shared list for everybody."""

    def __init__(self, system: str, budget_tokens: int = 3000):
        self.system = system
        self.budget_tokens = budget_tokens
        self._conversations: dict[tuple[str, str], Conversation] = {}

    def get(self, agent_id: str, ticket_id: str) -> Conversation:
        key = (agent_id, ticket_id)
        if key not in self._conversations:
            self._conversations[key] = Conversation(self.system, self.budget_tokens)
        return self._conversations[key]
