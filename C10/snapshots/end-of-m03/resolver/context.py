"""The working context: what the model sees at each step, built from the prompt files and the state.

Prompt files have a [system] part and a [user] part. {policy} is Grace's policy (prompts/policy.md).
The ticket goes between <ticket> tags; tags inside the ticket text are neutralised, so that a
ticket cannot close the block and pretend to be an instruction. The customer ID is never sent:
the tools know whose ticket it is.
"""

import json
import re
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent / "prompts"
MAX_TOKENS = 2000


def load_prompt(name: str) -> tuple[str, str]:
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    system, user = text.split("[user]\n", 1)
    policy = (PROMPTS / "policy.md").read_text(encoding="utf-8").strip()
    return system.replace("[system]\n", "", 1).strip().replace("{policy}", policy), user.strip()


def ticket_block(text: str, attachments: list[str]) -> str:
    safe = re.sub(r"</?\s*ticket\s*>", "[tag removed]", text, flags=re.I)
    return f"<ticket>\n{safe}\n</ticket>\nAttachments: {', '.join(attachments) if attachments else 'none'}"


def first_messages(prompt: str, text: str, attachments: list[str], **fields) -> list[dict]:
    system, user = load_prompt(prompt)
    for name, value in fields.items():   # the other fields first: the ticket text may contain braces
        user = user.replace("{" + name + "}", value)
    return [{"role": "system", "content": system},
            {"role": "user", "content": user.replace("{ticket}", ticket_block(text, attachments))}]


def compact(data) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
