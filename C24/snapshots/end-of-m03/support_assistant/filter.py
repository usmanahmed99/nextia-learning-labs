"""A model-based input filter: one extra model call that tries to catch an injection before the
assistant reads the message. It is a single, unreliable layer: the course measures what it stops and
what it misses, and never relies on it alone.
"""

import json

from .context import load
from .providers import Completion, ProviderError

VERDICT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {"name": "filter", "strict": True, "schema": {
        "type": "object",
        "properties": {"verdict": {"type": "string", "enum": ["allow", "block"]},
                       "reason": {"type": "string"}},
        "required": ["verdict", "reason"], "additionalProperties": False}},
}


def screen(complete, model: str, request_text: str, ticket_text: str, meta: dict) -> tuple[str, str]:
    """Return (verdict, reason). On a provider error the verdict is 'error' (fail open, but recorded)."""
    messages = [{"role": "system", "content": load("filter")},
                {"role": "user", "content": f"Request from the team: {request_text}\n\nCustomer message:\n{ticket_text}"}]
    request = {"model": model, "messages": messages, "response_format": VERDICT_SCHEMA, "max_completion_tokens": 200}
    try:
        completion: Completion = complete(request, {**meta, "step": "filter"})
    except ProviderError as e:
        return "error", str(e)
    try:
        data = json.loads(completion.text or "{}")
        return data.get("verdict", "allow"), data.get("reason", "")
    except json.JSONDecodeError:
        return "allow", "the filter gave no usable verdict"
