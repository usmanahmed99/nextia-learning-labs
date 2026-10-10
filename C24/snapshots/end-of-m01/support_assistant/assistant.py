"""Run one case: sign in, then the tool loop, then store the run.

The model proposes tool calls; tools.py runs them. The model's last message with no tool call is the
reply draft. A step limit always applies, so the loop ends. This first version has one design,
`start`: a weak prompt, every tool for everyone, writes that run at once, a raw log and full storage.
"""

import json
import uuid
from typing import Callable

from .context import MAX_TOKENS, system_prompt, user_message
from .data import TODAY
from .identity import AuthError, authorize, issue_token
from .providers import Completion, ProviderError, RecordingNotFound
from .state import RunState
from .systems import World
from .tools import run_tool, tool_list

DESIGNS = ["start"]


def run_case(case, complete: Callable, world: World, model: str, design: str = "start",
             max_steps: int = 8) -> RunState:
    state = RunState(run_id=f"R-{uuid.uuid4().hex[:8]}", case_id=case.case_id, design=design, model=model,
                     tenant=case.tenant, user=case.user, kind=case.kind)
    world.run_id = state.run_id   # every audit event of this run carries the run ID
    try:
        _run(case, complete, world, model, state, max_steps)
    finally:
        world.run_id = ""
    return state


def _run(case, complete, world, model, state, max_steps) -> None:
    token = issue_token(case.user)
    try:
        session = authorize(token, case.tenant, world)
    except AuthError as e:
        state.stop_reason = "auth_error"
        state.note(str(e))
        world.log(case.user, case.tenant, "sign_in", "refused")
        return
    state.role = session.role

    ticket = world.ticket(case.ticket_id)
    world.log(session.sub, session.tenant, "assistant", "run", case=case.case_id, ticket=case.ticket_id,
              customer=ticket["customer_id"], request=case.request, message=ticket["text"])
    _converse(case, complete, world, model, session, ticket, state, max_steps)

    # Keep the whole conversation, with the customer's name and e-mail, with no end date.
    customer = world.customer(ticket["customer_id"]) or {}
    world.save_conversation({
        "run_id": state.run_id, "tenant": state.tenant, "case_id": case.case_id, "ticket_id": ticket["ticket_id"],
        "customer_id": ticket["customer_id"], "customer_name": customer.get("name"),
        "customer_email": customer.get("email"), "request": case.request, "ticket_text": ticket["text"],
        "answer": state.answer, "outcome": json.dumps({"stop": state.stop_reason}), "created_at": TODAY.isoformat()})


def _converse(case, complete, world, model, session, ticket, state, max_steps) -> None:
    meta = {"case_id": case.case_id, "design": state.design}
    messages = [{"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_message(case.request, ticket["text"], ticket["attachments"])}]
    tools = tool_list()

    while True:
        if state.step >= max_steps:
            state.stop_reason = "max_steps"
            return
        request = {"model": model, "messages": list(messages), "tools": tools, "tool_choice": "auto",
                   "max_completion_tokens": MAX_TOKENS}
        state.step += 1
        try:
            completion: Completion = complete(request, {**meta, "step": state.step})
        except RecordingNotFound as e:
            state.stop_reason = "no_recording"
            state.note(str(e))
            return
        except ProviderError as e:
            # The provider's own content filter shows up here as an HTTP 400.
            state.stop_reason = "content_filter" if (e.status == 400) else "provider_error"
            state.note(str(e))
            world.log(session.sub, session.tenant, "model", state.stop_reason, status=e.status)
            return
        _account(state, completion, model)

        if not completion.tool_calls:
            state.answer = (completion.text or "").strip()
            state.stop_reason = "finished"
            return

        messages.append({"role": "assistant", "content": completion.text or "",
                         "tool_calls": [{"id": c.id, "type": "function",
                                         "function": {"name": c.name, "arguments": c.arguments}}
                                        for c in completion.tool_calls]})
        for call in completion.tool_calls:
            outcome = run_tool(call.name, call.arguments, state.step, session, ticket, world)
            state.tool_events.append(outcome.event)
            if outcome.proposal is not None:
                state.proposals.append(outcome.proposal)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": outcome.text})


def _account(state: RunState, completion: Completion, model: str) -> None:
    from .usage import cost_usd
    if completion.note:
        state.replay_notes += 1
    state.usage_calls += 1
    state.input_tokens += completion.input_tokens
    state.output_tokens += completion.output_tokens
    state.model_seconds = round(state.model_seconds + completion.latency_s, 3)
    c = cost_usd(model, completion.input_tokens, completion.output_tokens)
    state.cost_usd = None if c is None or state.cost_usd is None else round(state.cost_usd + c, 6)
