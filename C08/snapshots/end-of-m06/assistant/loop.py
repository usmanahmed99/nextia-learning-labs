"""The tool loop: the model proposes calls, the application decides, and the loop always ends."""

import json
import time
from dataclasses import dataclass, field
from typing import Callable

from .orders import OrderBook
from .providers import Completion
from .tools import run_tool


@dataclass
class Limits:
    max_steps: int = 4            # model calls in one loop
    max_seconds: float = 60.0     # wall-clock time for the whole loop
    max_result_chars: int = 2000  # a tool result longer than this is cut before the model sees it


@dataclass
class Step:
    name: str
    arguments: str
    outcome: str  # "ok", "refused: <code>" or "stopped: repeated call"


@dataclass
class LoopResult:
    completion: Completion | None          # the final answer, or None when the loop was stopped
    completions: list[Completion] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    looked_up: dict[str, dict] = field(default_factory=dict)  # orders that the application really returned
    stopped: str = ""                       # "", "max_steps", "repeated_call" or "time"


def run_tool_loop(complete: Callable[[dict], Completion], request: dict, customer_id: str, book: OrderBook,
                  limits: Limits = Limits(), clock: Callable[[], float] = time.monotonic) -> LoopResult:
    result = LoopResult(None)
    messages = list(request["messages"])
    seen = set()
    start = clock()
    for _ in range(limits.max_steps):
        completion = complete({**request, "messages": list(messages)})  # a copy: the list grows below
        result.completions.append(completion)
        if not completion.tool_calls:
            result.completion = completion
            return result
        messages.append({"role": "assistant", "content": completion.text, "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
            for c in completion.tool_calls]})
        for call in completion.tool_calls:
            signature = (call.name, call.arguments.replace(" ", ""))
            if signature in seen:
                result.steps.append(Step(call.name, call.arguments, "stopped: repeated call"))
                result.stopped = "repeated_call"
                return result
            seen.add(signature)
            output, outcome = run_tool(call.name, call.arguments, customer_id, book)
            result.steps.append(Step(call.name, call.arguments, outcome))
            if output["ok"]:
                result.looked_up[output["order"]["order_id"]] = output["order"]
            text = json.dumps(output, ensure_ascii=False)[:limits.max_result_chars]
            messages.append({"role": "tool", "tool_call_id": call.id, "content": text})
        if clock() - start > limits.max_seconds:
            result.stopped = "time"
            return result
    result.stopped = "max_steps"
    return result
