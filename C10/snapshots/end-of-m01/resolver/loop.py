"""The execution loop: the model proposes the next step, the application decides.

Two ways to ask a model for its next step, with the same loop around them:
- "tools": the model calls a function (Chat Completions tool calling). chat-small does this.
- "structured": the model answers with one JSON object (structured output): its plan and the next tool
  or its resolution. Any model with JSON-schema output can do this, also one without tool calling
  (chat-strong in Chat Completions, gemma3:4b in Ollama).

The loop ends when the model finishes, after max_steps model calls, or when no decision comes back
(no_recording, provider_error). Module 2 makes it stop for more reasons: time, cost, repeated calls, errors.
"""

import json
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from .context import MAX_TOKENS, compact
from .providers import Completion, ProviderError, RecordingNotFound
from .schema import RESOLUTION_SCHEMA, errors_text, parse_resolution
from .state import Evidence, TaskState
from .systems import World
from .tools import READ_TOOLS, ToolResult, run_read
from .usage import cost_usd


@dataclass
class Limits:
    max_steps: int = 8            # model calls in one task


STEP_SCHEMA = {  # the structured way: one JSON object per step
    "type": "json_schema",
    "json_schema": {"name": "next_step", "strict": True, "schema": {
        "type": "object",
        "properties": {
            "plan": {"type": "array", "items": {"type": "string"}, "description": "the steps left, short"},
            "tool": {"type": "string", "enum": [*READ_TOOLS, "finish"]},
            "order_id": {"type": ["string", "null"]},
            "query": {"type": ["string", "null"]},
            "resolution": {"anyOf": [RESOLUTION_SCHEMA, {"type": "null"}]},
        },
        "required": ["plan", "tool", "order_id", "query", "resolution"],
        "additionalProperties": False,
    }},
}


def structured_call(step: dict) -> tuple[str, dict]:
    """A structured step -> (tool name, its arguments)."""
    name = step.get("tool", "")
    if name == "finish":
        return name, step.get("resolution") or {}
    if name in ("get_order", "get_payments"):
        return name, {"order_id": step.get("order_id")}
    if name == "search_policy":
        return name, {"query": step.get("query")}
    return name, {}


class Stop(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def account(state: TaskState, completion: Completion, model: str) -> None:
    state.usage.model_calls += 1
    state.usage.input_tokens += completion.input_tokens
    state.usage.output_tokens += completion.output_tokens
    state.usage.model_seconds = round(state.usage.model_seconds + completion.latency_s, 3)
    cost = cost_usd(model, completion.input_tokens, completion.output_tokens)
    state.usage.cost_usd = None if cost is None or state.usage.cost_usd is None else state.usage.cost_usd + cost


def check_budget(state: TaskState, limits: Limits) -> None:
    if state.step >= limits.max_steps:
        raise Stop("max_steps")


def accept_resolution(state: TaskState, arguments: dict) -> str:
    """Check a proposed resolution. '' = accepted (state.proposal set); otherwise the reason it was refused."""
    try:
        resolution = parse_resolution(arguments)
    except ValidationError as e:
        return f"The resolution is not valid: {errors_text(e)}"
    seen = state.seen_orders()
    for action in resolution.actions:
        if action.order_id not in seen:
            return (f"{action.tool} on {action.order_id}: that order was not returned by a tool in this task. "
                    "Look it up first; never act on an order that you have not seen.")
    state.proposal = resolution
    return ""


def run_loop(state: TaskState, complete: Callable[[dict, dict], Completion], world: World, *, mode: str,
             first_messages: list[dict], limits: Limits = Limits(), variant_tag: str | None = None,
             tools: list[dict] | None = None, finish_name: str = "finish",
             on_finish: Callable[[TaskState, dict], str] = accept_resolution,
             read_tools: tuple[str, ...] = tuple(READ_TOOLS), on_step: Callable[[TaskState], None] | None = None,
             step_offset: int = 0) -> TaskState:
    """Run until the model finishes or a limit stops it. `complete(request, meta)` is the provider's method."""
    messages = state.messages or list(first_messages)
    state.messages = messages
    tag = variant_tag or state.variant
    try:
        while True:
            check_budget(state, limits)
            request = {"model": state.model, "messages": list(messages), "max_completion_tokens": MAX_TOKENS}
            if mode == "tools":
                request["tools"] = tools
                request["tool_choice"] = "required"
            else:
                request["response_format"] = STEP_SCHEMA
            state.step += 1
            meta = {"task_id": state.task_id, "variant": tag, "step": state.step - step_offset,
                    "state": state.evidence_digest()}
            try:
                completion = complete(request, meta)
            except RecordingNotFound as e:
                state.log("error", "no_recording", message=str(e))
                raise Stop("no_recording")
            except ProviderError as e:
                state.log("error", "provider", message=str(e), status=e.status)
                state.errors.append(str(e))
                raise Stop("provider_error")
            account(state, completion, state.model)
            calls = []
            if mode == "tools":
                for c in completion.tool_calls:
                    calls.append((c.id, c.name, c.arguments))
                messages.append({"role": "assistant", "content": completion.text, "tool_calls": [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                    for c in completion.tool_calls]} if completion.tool_calls else
                    {"role": "assistant", "content": completion.text or ""})
            else:
                messages.append({"role": "assistant", "content": completion.text or ""})
                try:
                    step = json.loads(completion.text or "")
                    name, args = structured_call(step)
                    if step.get("plan") != state.plan:
                        state.log("plan", "plan", plan=step.get("plan"), previous=state.plan)
                        state.plan = list(step.get("plan") or [])
                    calls.append((None, name, args))
                except (json.JSONDecodeError, AttributeError):
                    calls = []
            state.log("model", state.model, calls=[[n, a] for _, n, a in calls], tokens_in=completion.input_tokens,
                      tokens_out=completion.output_tokens, latency_s=completion.latency_s,
                      finish_reason=completion.finish_reason, note=completion.note)
            if not calls:
                reason = completion.refusal or f"finish_reason {completion.finish_reason}"
                state.log("error", "no_decision", message=f"The model gave no usable step ({reason}).")
                messages.append({"role": "user", "content": "Your answer had no usable step. Answer with one step."})
                if on_step:
                    on_step(state)
                continue
            replies = []
            finished = False
            for call_id, name, args in calls:
                if name == finish_name:
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    problem = on_finish(state, args)
                    state.log("proposal", name, accepted=not problem, problem=problem, arguments=args)
                    if problem:
                        replies.append((call_id, name, compact({"ok": False, "error": problem})))
                        continue
                    finished = True
                    replies.append((call_id, name, compact({"ok": True, "result": "Received."})))
                    break
                if name not in read_tools:
                    result = ToolResult(False, error=f"There is no tool named {name}.", code="unknown_tool")
                else:
                    result = run_read(name, args, state.customer_id, world)
                parsed_args = json.loads(args) if isinstance(args, str) and args.strip().startswith("{") else args
                state.evidence.append(Evidence(step=state.step, tool=name, arguments=parsed_args
                                               if isinstance(parsed_args, dict) else {"raw": str(parsed_args)},
                                               ok=result.ok, code=result.code, data=result.data, error=result.error,
                                               order_ids=result.order_ids))
                state.log("tool", name, arguments=parsed_args, ok=result.ok, code=result.code,
                          error=result.error)
                replies.append((call_id, name, result.for_model()))
            for call_id, name, text in replies:
                if mode == "tools":
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": text})
                else:
                    messages.append({"role": "user", "content": f"Result of {name}: {text}"})
            if mode == "tools":   # every tool call needs an answer, also the ones after finish
                answered = {r[0] for r in replies}
                for call_id, name, _ in calls:
                    if call_id not in answered:
                        messages.append({"role": "tool", "tool_call_id": call_id,
                                         "content": compact({"ok": False, "error": "Not run: the task ended."})})
            if on_step:
                on_step(state)
            if finished:
                raise Stop("finished")
    except Stop as s:
        state.stop_reason = s.reason
        state.log("stop", s.reason)
    return state
