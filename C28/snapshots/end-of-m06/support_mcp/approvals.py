"""Approve or reject proposed refunds: a person's decision, outside the AI application.

    python -m support_mcp.approvals list [--tenant larkfield]
    python -m support_mcp.approvals approve OP-0001 --user usr-grace
    python -m support_mcp.approvals reject OP-0001 --user usr-grace
    python -m support_mcp.approvals refunds

In a real system this is a page in the help desk where Grace signs in. Here the --user option
stands for that sign-in (a practice shortcut on your own computer).
"""

import argparse
import json
import sys

from support_mcp import writes


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m support_mcp.approvals")
    sub = p.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--tenant")
    for name in ("approve", "reject"):
        s = sub.add_parser(name)
        s.add_argument("operation_id")
        s.add_argument("--user", required=True)
    sub.add_parser("refunds")
    a = p.parse_args(argv)
    if a.cmd == "list":
        items = writes.pending(a.tenant)
        if not items:
            print("No proposals wait for approval.")
        for item in items:
            print(json.dumps(item, ensure_ascii=False))
        return 0
    if a.cmd == "refunds":
        for r in writes.refunds():
            print(f"{r['operation_id']}  {r['tenant']}  {r['ticket_id']}  {r['amount']} USD  (mock: no money moved)")
        return 0
    try:
        out = writes.decide(a.operation_id, a.user, approve=a.cmd == "approve")
    except writes.ApprovalError as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 1
    if out["status"] == "approved":
        print(
            f"{out['operation_id']} approved by {out['decided_by']}: refund of {out['amount']} USD "
            f"for {out['ticket_id']} recorded (mock: no money moved)."
        )
    else:
        print(f"{out['operation_id']} rejected by {out['decided_by']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
