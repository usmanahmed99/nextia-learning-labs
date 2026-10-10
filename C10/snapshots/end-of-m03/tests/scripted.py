"""A scripted model for tests: each step returns the tool calls written here. CONSTRUCTED, not recorded."""

import itertools
import json

from resolver.providers import Completion


def call(name: str, **arguments) -> dict:
    return {"name": name, "arguments": arguments}


def finish(outcome="reply_only", rule="W1", actions=(), reply="We checked your order.", reason="test") -> dict:
    flat = []
    for a in actions:
        flat.append({"tool": a["tool"], "order_id": a["order_id"], "sku": a.get("sku"), "quantity": a.get("quantity"),
                     "amount": a.get("amount"), "reason": a.get("reason") or a.get("reason_code"),
                     "payment_id": a.get("payment_id")})
    return call("finish", outcome=outcome, rule=rule, actions=flat, reply=reply, reason=reason)


class Scripted:
    """complete(request, meta) returns the next scripted step; the last step repeats when the script ends."""

    def __init__(self, steps: list[list[dict]], latency_s: float = 0.5, tokens=(1000, 50), model="chat-small"):
        self.steps, self.latency_s, self.tokens, self.model = steps, latency_s, tokens, model
        self.requests = []
        self.ids = itertools.count(1)

    def complete(self, request: dict, meta: dict | None = None) -> Completion:
        self.requests.append(request)
        step = self.steps[min(len(self.requests) - 1, len(self.steps) - 1)]
        calls = [{"id": f"call_{next(self.ids)}", "type": "function",
                  "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}} for c in step]
        data = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": calls},
                             "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": self.tokens[0], "completion_tokens": self.tokens[1]}, "model": self.model}
        return Completion.from_response(data, self.latency_s)
