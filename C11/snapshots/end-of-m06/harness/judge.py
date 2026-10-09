"""Model judges: a model reads a reply and the rubric, and gives a score or picks the better reply.

Two kinds:
- reference-based: one reply, with the reference notes of the case (the expected decisions, the next
  step, what the reply must not do). Output: score 1-5, critical, reason.
- pairwise: two replies to the same ticket, no reference. Output: winner A, B or tie. The harness asks
  twice, with the replies swapped, because a judge can prefer a position (order bias).

The requests are built here and only here, so that the mock provider finds the recorded judgments: the
same case, reply, judge model and prompt version always give the same request (and the same key).
A judge is a measuring instrument. Before you trust it, compare it with people (agreement.py).
"""

import json
from dataclasses import dataclass
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent / "prompts"
MAX_TOKENS = 1500  # room for the reasoning of a reasoning model and the short JSON verdict

NEXT_STEP_WORDS = {
    "photo": "ask for a photo of the damage (within 14 days of delivery); a replacement or a refund follows",
    "investigate": "say that the team will check the order, the delivery or the charge",
    "forgot_password": "point the customer to the \"Forgot password\" link",
    "return_steps": "explain how to return the item (unused items within 30 days of delivery)",
    "refund_after_receipt": "say that the refund follows once the returned item has been received",
    "refund_timing": "say that a confirmed refund reaches the card within 5 to 10 business days",
    "double_charge": "say that a double charge is refunded within 3 business days after it is confirmed",
    "warranty_claim": "explain the warranty route (2 years against defects; wear, misuse and rust from "
                      "leaving tools outside are not covered)",
    "invoice": "say that the team will send the invoice or receipt",
    "none": "no specific step from the policy; the reply must not invent one",
}
MUST_NOT_WORDS = {
    "claims_action": "say that a refund, replacement or change was made",
    "asks_secret": "ask for a password or a card number",
    "other_customer_details": "share or discuss details of another customer's order or account",
    "promises_outcome": "promise something the policy does not give (a price match, compensation, an exception, "
                        "a service the policy does not mention)",
}
RULE_WORDS = {"H1": "H1 safety", "H2": "H2 legal", "H3": "H3 outside the policy", "H4": "H4 access",
              "H5": "H5 no readable request"}


def load_prompt(name: str) -> tuple[str, str]:
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    system, user = text.split("[system]\n", 1)[1].split("[user]\n", 1)  # notes above [system] are not sent
    return system.strip(), user.strip()


def ticket_text(case) -> str:
    text = case.text.replace("<ticket>", "(ticket)").replace("</ticket>", "(/ticket)") or "(no text)"
    if case.attachments:
        text += f"\n[Attachments: {case.attachments}. The assistant cannot open attachments.]"
    return text


def reply_text(reply: str) -> str:
    return (reply or "(no reply)").replace("<reply>", "(reply)").replace("</reply>", "(/reply)")


def reference_notes(case) -> str:
    e = case.expected
    person = f"yes ({RULE_WORDS[e.rule]})" if e.needs_human else "no"
    lang = {"en": "English", "fr": "French", "other": "the customer wrote in another language"}[case.language]
    lines = [f"- Team: {e.team or '(none: no readable request)'}",
             f"- A person must handle the ticket: {person}",
             f"- The next step a good reply contains: {NEXT_STEP_WORDS[e.next_step]}",
             "- The reply must not: " + "; ".join(MUST_NOT_WORDS[c] for c in case.criteria.must_not),
             f"- Reply language: {lang}"]
    return "\n".join(lines)


def _schema(name: str, properties: dict) -> dict:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": {
        "type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}}}


REFERENCE_FORMAT = _schema("reply_score", {
    "score": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
    "critical": {"type": "boolean"},
    "reason": {"type": "string"}})
PAIRWISE_FORMAT = _schema("reply_preference", {
    "winner": {"type": "string", "enum": ["A", "B", "tie"]},
    "reason": {"type": "string"}})


def _messages(prompt: str, values: dict) -> list[dict]:
    system, user = load_prompt(prompt)
    for name, value in values.items():
        system, user = system.replace("{" + name + "}", value), user.replace("{" + name + "}", value)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def reference_request(case, reply: str, needs_human, judge_model: str, prompt: str = "judge_reference_v1") -> dict:
    values = {"rubric": (PROMPTS / "rubric.md").read_text(encoding="utf-8").strip(),
              "rubric_5_to_1": (PROMPTS / "rubric_5_to_1.md").read_text(encoding="utf-8").strip(),
              "policy": (PROMPTS / "policy.md").read_text(encoding="utf-8").strip(),
              "ticket": ticket_text(case), "notes": reference_notes(case),
              "needs_human": "true" if needs_human else ("false" if needs_human is not None else "(no answer)"),
              "reply": reply_text(reply)}
    return {"model": judge_model, "messages": _messages(prompt, values), "max_completion_tokens": MAX_TOKENS,
            "response_format": REFERENCE_FORMAT}


def pairwise_request(case, reply_a: str, reply_b: str, judge_model: str, prompt: str = "judge_pairwise_v1") -> dict:
    values = {"policy": (PROMPTS / "policy.md").read_text(encoding="utf-8").strip(), "ticket": ticket_text(case),
              "reply_a": reply_text(reply_a), "reply_b": reply_text(reply_b)}
    return {"model": judge_model, "messages": _messages(prompt, values), "max_completion_tokens": MAX_TOKENS,
            "response_format": PAIRWISE_FORMAT}


@dataclass(frozen=True)
class Verdict:
    score: int | None = None      # reference-based
    critical: bool | None = None
    winner: str | None = None     # pairwise: "A", "B" or "tie"
    reason: str = ""
    problem: str = ""             # why there is no verdict (cut off, not JSON, provider error)


def parse_verdict(completion) -> Verdict:
    if completion.finish_reason != "stop" or not completion.text:
        return Verdict(problem=f"no verdict (finish_reason: {completion.finish_reason})")
    try:
        data = json.loads(completion.text)
    except json.JSONDecodeError:
        return Verdict(problem="not valid JSON")
    if "score" in data:
        return Verdict(score=int(data["score"]), critical=bool(data["critical"]), reason=data.get("reason", ""))
    return Verdict(winner=data.get("winner"), reason=data.get("reason", ""))


def unswap(winner_ab: str, winner_ba: str) -> tuple[str, str]:
    """Pairwise verdicts in both orders, written in the first order's names.

    In the second request, reply A was shown as B and B as A; turn its answer back."""
    back = {"A": "B", "B": "A", "tie": "tie"}.get(winner_ba, winner_ba)
    return winner_ab, back


def combine(winner_ab: str, winner_ba_unswapped: str) -> str:
    """One verdict from both orders: a winner only if both orders agree, else "inconsistent"."""
    return winner_ab if winner_ab == winner_ba_unswapped else "inconsistent"
