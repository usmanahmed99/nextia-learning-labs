"""Build the request: the prompt version's instructions, Grace's policy, and the ticket text."""

from pathlib import Path

from .data import Ticket

PROMPTS = Path(__file__).resolve().parent / "prompts"
MAX_TOKENS = 1000  # room for the JSON answer; a reply needs about 150-400 tokens


def load_prompt(version: str) -> tuple[str, str]:
    """Return the (system, user) templates of prompts/<version>.md."""
    text = (PROMPTS / f"{version}.md").read_text(encoding="utf-8")
    system, user = text.split("[system]\n", 1)[1].split("[user]\n", 1)  # the notes above [system] are not sent
    return system.strip(), user.strip()


def ticket_block(ticket: Ticket) -> str:
    """The customer's words, with the delimiter tags made harmless, and the attachments named."""
    text = ticket.text.replace("<ticket>", "(ticket)").replace("</ticket>", "(/ticket)")
    if not text.strip():
        text = "(no text)"
    if ticket.attachments:
        text += f"\n[Attachments: {ticket.attachments}. The assistant cannot open attachments.]"
    return text


def build_messages(ticket: Ticket, version: str) -> list[dict]:
    system, user = load_prompt(version)
    policy = (PROMPTS / "policy.md").read_text(encoding="utf-8").strip()
    return [
        {"role": "system", "content": system.replace("{policy}", policy)},
        {"role": "user", "content": user.replace("{ticket}", ticket_block(ticket))},
    ]


def build_request(ticket: Ticket, model: str, version: str = "v2") -> dict:
    """The body of one Chat Completions request."""
    return {"model": model, "messages": build_messages(ticket, version), "max_completion_tokens": MAX_TOKENS}
