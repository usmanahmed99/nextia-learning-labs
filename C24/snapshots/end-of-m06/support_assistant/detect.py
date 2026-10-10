"""Detection: turn audit events into a few useful alerts, without reading anyone's messages.

The rules read only the event fields (who, which tenant, which tool, the result and its code), never
a message body. Each rule has a threshold: one event can be noise, a pattern is worth a person's time.
An alert names the runs and cases to look at, so that triage starts from the stored outcome of a run,
not from the customer's text.

    python -m support_assistant detect                 # the audit log of your practice database
    python -m support_assistant detect FILE            # the events of a saved evaluation (eval --save)
"""

import json
from collections import defaultdict

from . import web

# (rule, severity, threshold, what to check first)
RULES = {
    "secret_held": ("high", 1, "An answer with a secret was held back. Check where the secret came from "
                               "(a file, a page) and rotate it if it was ever sent."),
    "private_address": ("high", 1, "A tool was asked for a private or metadata address (SSRF). Find the text "
                                   "that asked for it; check the allow-list."),
    "blocked_tools": ("medium", 3, "One person's runs hit blocked files, pages or other customers' orders "
                                   "several times. Look at those runs' outcomes: an attack in the tickets, or a "
                                   "control that blocks normal work?"),
    "writes_refused": ("medium", 2, "Proposed changes were refused (limit, scope, address). Check whether the "
                                    "tickets push for refunds or e-mails they should not get."),
    "input_filter": ("low", 5, "The input filter blocked many messages. Check for over-blocking of normal "
                               "customers before you trust it."),
    "provider_filter": ("low", 1, "The provider's own content filter stopped a run. Check that a normal "
                                  "customer was not blocked."),
}


def flatten(rows: list[dict]) -> list[dict]:
    """Audit-log rows (detail as a dict or JSON) -> flat events."""
    out = []
    for r in rows:
        detail = r.get("detail", {})
        if isinstance(detail, str):
            detail = json.loads(detail)
        e = {k: v for k, v in r.items() if k != "detail"}
        e.setdefault("run", e.get("run_id", ""))
        out.append({**e, **(detail or {})})
    return out


def _rule(e: dict) -> str:
    action, result = e.get("action", ""), e.get("result", "")
    if action == "output_check" and "secret" in str(e.get("reason", "")):
        return "secret_held"
    if action == "fetch_url" and result == "blocked" and e.get("host") and web.is_private(e["host"]):
        return "private_address"
    if action in ("read_file", "fetch_url", "get_order") and result in ("blocked", "out_of_scope"):
        return "blocked_tools"
    if result == "refused" and action in ("issue_refund", "create_return_label", "send_email"):
        return "writes_refused"
    if action == "input_filter" and result == "blocked":
        return "input_filter"
    if action == "model" and result == "content_filter":
        return "provider_filter"
    return ""


def alerts(events: list[dict]) -> list[dict]:
    """Group the events by rule, person and tenant; raise an alert where a group reaches its threshold."""
    case_of = {e.get("run"): e.get("case") for e in events if e.get("action") == "assistant"}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for e in events:
        rule = _rule(e)
        if rule:
            groups[(rule, e.get("actor", ""), e.get("tenant", ""))].append(e)
    out = []
    for (rule, actor, tenant), group in groups.items():
        severity, threshold, check = RULES[rule]
        if len(group) < threshold:
            continue
        runs = sorted({g.get("run", "") for g in group})
        out.append({"severity": severity, "rule": rule, "actor": actor, "tenant": tenant, "count": len(group),
                    "runs": len(runs), "cases": sorted({case_of.get(r) or "?" for r in runs}),
                    "codes": sorted({str(g.get("code") or g.get("result")) for g in group}), "check": check})
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(out, key=lambda a: (order[a["severity"]], -a["count"], a["rule"]))
