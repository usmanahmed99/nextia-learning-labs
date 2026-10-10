"""Two designs where code decides the steps: the fixed workflow and the router.

Fixed workflow: every step is code. Keyword rules find the kind of request and the H1-H5 cases, a
regular expression finds the order ID, the tools read the facts, rules.py decides the action. The
model only drafts the reply text.

Router: the model makes ONE decision: which path the ticket takes (and which order and item). Then
the same code as the fixed workflow reads the facts and decides; the model drafts the reply.

The keyword lists come from the words of Grace's policy. They were written by the person who also
wrote the course's tasks, so the fixed workflow is an optimistic baseline: new tickets will say
things these lists do not know.
"""

import json
import re
from typing import Callable

from pydantic import ValidationError

from .context import compact, first_messages
from .providers import Completion, ProviderError, RecordingNotFound
from .rules import Decision, decide
from .schema import errors_text, parse_resolution
from .state import Evidence, TaskState
from .systems import World
from .tools import run_read
from .loop import account

ORDER_ID = re.compile(r"\bLK-\d{6}\b")

H_WORDS = {  # H1-H5 from the policy's own words
    "H1": ["spark", "burn", "fire", "smoke", "scorch", "shock", "smell of gas", "gas ", "unsafe", "dangerous",
           "injur", "socket", "really hot", "very hot", "is that safe", "is it safe"],
    "H2": ["lawyer", "court", "legal action", "consumer protection", "complaint with", "sue "],
    "H3": ["price match", "sells the same", "the difference", "rather not send it back", "not send it back",
           "compensation", "already approved"],
    "H4": ["ignore your instructions", "ignore all previous", "system note", "note for the system",
           "skip the approval", "my neighbour", "my sister", "my brother", "my friend's"],
}
KIND_WORDS = [  # checked in this order: the first kind that matches wins
    ("outside", ["email on my", "password", "my account", "delivery slot", "change the address", "change my address",
                 "guarantee", "warranty", "saved card", "points"]),
    ("double_charge", ["charged twice", "two charges", "charged me twice", "twice from my card", "took", "double charge"]),
    ("refund_eta", ["my refund", "the refund", "refund will", "don't see it on my card"]),
    ("wrong_item", ["wrong item", "instead of", "not what i ordered", "box has a"]),
    ("damaged", ["damaged", "broken", "cracked", "bent", "split", "snapped", "torn", "leaks", "broke"]),
    ("return", ["return", "send back", "send them back", "send it back"]),
    ("missing_box", ["isn't here", "never turned up", "part of the same order", "was it forgotten"]),
    ("late", ["late", "never came", "still hasn't", "still not", "hasn't arrived", "not arrived", "pas arrivée",
              "lost", "stuck", "where is", "when will", "what's going on", "any news", "arrive"]),
]
LANGUAGE_WORDS = {"en": [" the ", " my ", " and ", " is ", " i ", " you "],
                  "fr": [" le ", " la ", " ma ", " mon ", " est ", " pas ", " vous "]}


def detect_language(text: str) -> str | None:
    t = f" {text.lower()} "
    scores = {lang: sum(t.count(w) for w in words) for lang, words in LANGUAGE_WORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def keyword_kind(text: str) -> tuple[str | None, str]:
    """(H rule or None, kind) from the words of the ticket."""
    t = text.lower()
    if not t.strip() or detect_language(t) is None:
        return "H5", ""
    for rule, words in H_WORDS.items():
        if any(w in t for w in words):
            return rule, ""
    for kind, words in KIND_WORDS:
        if any(w in t for w in words):
            return None, kind
    return None, "status"


def _complete(state: TaskState, complete, request: dict, tag: str, step: int) -> Completion | None:
    state.step += 1
    meta = {"task_id": state.task_id, "variant": tag, "step": step, "state": state.evidence_digest()}
    try:
        completion = complete(request, meta)
    except RecordingNotFound as e:
        state.log("error", "no_recording", message=str(e))
        state.errors.append(str(e))
        return None
    except ProviderError as e:
        state.log("error", "provider", message=str(e), status=e.status)
        state.errors.append(str(e))
        return None
    account(state, completion, state.model)
    state.log("model", state.model, purpose=tag, tokens_in=completion.input_tokens,
              tokens_out=completion.output_tokens, latency_s=completion.latency_s, note=completion.note)
    return completion


def read(state: TaskState, world: World, name: str, args: dict, retries: int = 1):
    """A read with one retry on a service failure (code decides the retry here, not a model)."""
    for _ in range(retries + 1):
        result = run_read(name, args, state.customer_id, world)
        state.evidence.append(Evidence(step=state.step, tool=name, arguments=args, ok=result.ok, code=result.code,
                                       data=result.data, error=result.error, order_ids=result.order_ids))
        state.log("tool", name, arguments=args, ok=result.ok, code=result.code, error=result.error)
        if result.ok or not result.code.startswith("service_"):
            return result
    return result


def find_order(state: TaskState, world: World, text: str, order_ids: list[str]) -> tuple[dict | None, str]:
    """The order of the ticket: by its ID, or among the customer's orders by the product named in the ticket."""
    for oid in order_ids:
        result = read(state, world, "get_order", {"order_id": oid})
        if result.ok:
            return result.data, ""
        if result.code in ("not_found", "other_customer"):
            return None, "H4" if result.code == "other_customer" or len(order_ids) > 1 else "ask"
        return None, "failed"
    listing = read(state, world, "get_customer_orders", {})
    if not listing.ok:
        return None, "ask"
    t = text.lower()
    hits = [o for o in listing.data if any(w in t for p in o["products"] for w in p.lower().replace("(", " ").split()
                                           if len(w) > 4)]
    if len(hits) != 1:
        return None, "ask"
    result = read(state, world, "get_order", {"order_id": hits[0]["order_id"]})
    return (result.data, "") if result.ok else (None, "failed")


def draft_reply(state: TaskState, complete, decision: Decision, tag: str, step: int) -> str:
    facts = {"outcome": decision.outcome, "rule": decision.rule, "proposed_changes": decision.actions,
             "facts": decision.facts}
    messages = first_messages("draft", state.goal, state.attachments, decision=compact(facts))
    request = {"model": state.model, "messages": messages, "max_completion_tokens": 800}
    completion = _complete(state, complete, request, tag, step)
    return (completion.text or "").strip() if completion else ""


def finish(state: TaskState, decision: Decision, reply: str) -> TaskState:
    try:
        state.proposal = parse_resolution({"outcome": decision.outcome, "rule": decision.rule,
                                           "actions": [dict(a, reason=a.get("reason") or a.get("reason_code"))
                                                       for a in decision.actions],
                                           "reply": reply[:2000], "reason": "; ".join(decision.facts)[:600]})
        state.log("proposal", "rules", accepted=True, arguments=state.proposal.model_dump())
        state.stop_reason = "finished"
    except ValidationError as e:
        state.log("error", "invalid_decision", message=errors_text(e))
        state.stop_reason = "too_many_errors"
    state.log("stop", state.stop_reason)
    return state


def run_fixed(state: TaskState, complete: Callable, world: World) -> TaskState:
    text = state.goal
    rule, kind = keyword_kind(text)
    state.log("note", "keywords", rule=rule, request_kind=kind)
    if rule:
        return finish(state, Decision("hand_to_person", rule, facts=[f"keyword rule {rule}"]),
                      draft_reply(state, complete, Decision("hand_to_person", rule), "fixed", 1))
    if kind == "outside":
        return finish(state, Decision("hand_to_person", "outside", facts=["outside the workflow"]),
                      draft_reply(state, complete, Decision("hand_to_person", "outside"), "fixed", 1))
    order, problem = find_order(state, world, text, ORDER_ID.findall(text))
    if order is None:
        decision = Decision("ask_customer", "W1", facts=["order not found: ask for the order ID"]) if problem == "ask" \
            else Decision("hand_to_person", problem if problem == "H4" else "evidence", facts=[f"order: {problem}"])
        return finish(state, decision, draft_reply(state, complete, decision, "fixed", 1))
    payments = None
    if kind == "double_charge":
        res = read(state, world, "get_payments", {"order_id": order["order_id"]})
        payments = res.data if res.ok else None
    t = text.lower()
    prefers = "refund" if "refund" in t else "replacement" if any(w in t for w in ("send another", "replacement",
                                                                                  "send me another")) else ""
    decision = decide(kind, order, payments=payments, text=text, photo=bool(state.attachments),
                      used=bool(re.search(r"\bused (it|them)\b|i've used|i have used", t)), prefers=prefers)
    return finish(state, decision, draft_reply(state, complete, decision, "fixed", 1))


ROUTE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {"name": "route", "strict": True, "schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "enum": ["status", "late", "lost", "missing_box", "return", "damaged",
                                                "wrong_item", "double_charge", "refund_eta", "ask_customer",
                                                "hand_to_person"]},
            "rule": {"type": ["string", "null"], "description": "for hand_to_person: H1-H5 or outside"},
            "order_id": {"type": ["string", "null"], "description": "the order ID written in the ticket, or null"},
            "product": {"type": ["string", "null"], "description": "the product the ticket is about, or null"},
            "item_used": {"type": "boolean"},
            "customer_prefers": {"type": "string", "enum": ["refund", "replacement", "not_said"]},
        },
        "required": ["path", "rule", "order_id", "product", "item_used", "customer_prefers"],
        "additionalProperties": False,
    }},
}


def run_router(state: TaskState, complete: Callable, world: World) -> TaskState:
    messages = first_messages("router", state.goal, state.attachments)
    request = {"model": state.model, "messages": messages, "response_format": ROUTE_SCHEMA,
               "max_completion_tokens": 1000}
    completion = _complete(state, complete, request, "router", 1)
    if completion is None:
        state.stop_reason = "no_recording" if any(e.name == "no_recording" for e in state.events) else "provider_error"
        state.log("stop", state.stop_reason)
        return state
    try:
        route = json.loads(completion.text or "")
    except json.JSONDecodeError:
        state.log("error", "invalid_route", message="not JSON")
        state.stop_reason = "too_many_errors"
        state.log("stop", state.stop_reason)
        return state
    state.log("note", "route", **route)
    path = route["path"]
    if path == "hand_to_person":
        decision = Decision("hand_to_person", route.get("rule") or "outside", facts=["the router chose a person"])
    elif path == "ask_customer":
        decision = Decision("ask_customer", "W1", facts=["the router chose to ask the customer"])
    else:
        ids = [route["order_id"]] if route.get("order_id") and ORDER_ID.fullmatch(route["order_id"]) else []
        order, problem = find_order(state, world, route.get("product") or state.goal, ids)
        if order is None:
            decision = Decision("ask_customer", "W1", facts=["order not found"]) if problem == "ask" else \
                Decision("hand_to_person", problem if problem == "H4" else "evidence", facts=[f"order: {problem}"])
        else:
            payments = None
            if path == "double_charge":
                res = read(state, world, "get_payments", {"order_id": order["order_id"]})
                payments = res.data if res.ok else None
            prefers = {"refund": "refund", "replacement": "replacement"}.get(route["customer_prefers"], "")
            decision = decide(path, order, payments=payments, text=(route.get("product") or "") + " " + state.goal,
                              photo=bool(state.attachments), used=route["item_used"], prefers=prefers)
    return finish(state, decision, draft_reply(state, complete, decision, "router_draft", 1))
