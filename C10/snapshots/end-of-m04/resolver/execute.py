"""Run the approved writes safely: operation IDs, idempotent calls, and reconciliation.

Every approved action gets an operation ID derived from the ticket and the exact action. The same
intended change always has the same ID, so a repeat (a retry, a resume after a crash, a second run of
the same ticket) cannot change anything twice: the service returns the first result.

The operation is saved as "pending" BEFORE the call (write-ahead). After a timeout, the outcome is
uncertain: the change may or may not have happened. The executor then asks the service
(`operation(op_id)`): done -> record it; not done -> try again with the SAME ID. It never "just calls
it again" with a new ID: that is how a customer gets two refunds (see `naive=True`, kept to show it).
"""

import hashlib
import json
from dataclasses import dataclass

from .schema import WRITE_TOOLS
from .state import Operation, TaskState, proposal_digest
from .systems import (InvalidRequest, PermissionDenied, ServiceError, ServiceTimeout, ServiceUnavailable, World)
from .tools import authorize_write


class ExecutionRefused(Exception):
    pass


class Interrupted(Exception):
    """A simulated crash: the process stops here. The checkpoint holds everything needed to resume."""


@dataclass
class RetryPolicy:
    max_attempts: int = 3   # calls per operation, the first one included


def operation_id(task_id: str, action) -> str:
    text = json.dumps({"ticket": task_id, **action.model_dump()}, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _call(world: World, op_id: str, action) -> dict:
    if action.tool == "create_return_label":
        return world.create_return_label(op_id, action.order_id, action.sku, action.reason)
    if action.tool == "reship_item":
        return world.reship_item(op_id, action.order_id, action.sku, action.quantity)
    if action.tool == "request_refund":
        return world.request_refund(op_id, action.order_id, action.amount, action.reason_code, action.payment_id)
    raise ExecutionRefused(f"{action.tool} is not a write tool")


def execute(state: TaskState, world: World, save=lambda s: None, retry: RetryPolicy = RetryPolicy(),
            naive: bool = False, interrupt: str = "") -> TaskState:
    """Run the approved actions of `state`. `interrupt` simulates a crash: 'before-write' or 'after-write'."""
    if state.approval is None or state.approval.decision != "approved":
        raise ExecutionRefused("No approval: nothing is written without a person's approval.")
    if state.approval.proposal_digest != proposal_digest(state.proposal):
        raise ExecutionRefused("The proposal changed after it was approved: it needs a new approval.")
    for action in state.proposal.actions:
        if action.tool not in WRITE_TOOLS:
            raise ExecutionRefused(f"{action.tool} is not a write tool")
        problem = authorize_write(action, state.customer_id, world)
        if problem:
            raise ExecutionRefused(problem)
    state.status = "executing"
    for action in state.proposal.actions:
        op_id = operation_id(state.task_id, action)
        op = next((o for o in state.operations if o.op_id == op_id), None)
        if op is None:
            op = Operation(op_id=op_id, tool=action.tool, arguments=action.model_dump(exclude={"tool"}))
            state.operations.append(op)
        if op.status == "done":
            continue
        if op.status in ("pending", "uncertain") and op.attempts:
            found = world.operation(op_id)       # reconcile first: did the earlier attempt happen?
            state.log("reconcile", action.tool, op_id=op_id, found=found is not None)
            if found is not None:
                op.status, op.result = "done", found
                save(state)
                continue
        save(state)                               # write-ahead: the attempt is on record before the call
        if interrupt == "before-write":
            state.log("note", "interrupted", where="before the write", op_id=op_id)
            save(state)
            raise Interrupted(f"simulated crash before the write of {op_id}")
        call_id = op_id
        while op.attempts < retry.max_attempts:
            op.attempts += 1
            try:
                result = _call(world, call_id, action)
            except ServiceTimeout as e:
                op.status, op.error = "uncertain", str(e)
                state.log("write", action.tool, op_id=call_id, outcome="timeout", error=str(e))
                save(state)
                if naive:   # Tomás's shortcut: call it again (a new request, a new ID), without checking
                    call_id = f"{op_id}-retry{op.attempts}"
                    continue
                found = world.operation(op_id)
                state.log("reconcile", action.tool, op_id=op_id, found=found is not None)
                if found is not None:
                    op.status, op.result, op.error = "done", found, ""
                    break
                continue
            except ServiceUnavailable as e:
                op.status, op.error = "pending", str(e)
                state.log("write", action.tool, op_id=call_id, outcome="unavailable", error=str(e))
                save(state)
                continue
            except (PermissionDenied, InvalidRequest, ServiceError) as e:
                op.status, op.error = "failed", str(e)
                state.log("write", action.tool, op_id=call_id, outcome=e.code, error=str(e))
                break
            op.status, op.result, op.error = "done", result, ""
            state.log("write", action.tool, op_id=call_id, outcome="repeated" if result.get("repeated") else "done",
                      result=result)
            if interrupt == "after-write":
                state.log("note", "interrupted", where="after the write, before it was recorded", op_id=op_id)
                op.status = "pending"            # the process dies before it can record "done"
                save(state)
                raise Interrupted(f"simulated crash after the write of {op_id}")
            break
        save(state)
        if op.status != "done":
            state.status = "handed_to_person"
            state.errors.append(f"{action.tool} on {action.order_id}: {op.error}")
            state.log("stop", "write_failed", op_id=op_id, error=op.error)
            save(state)
            return state
    note = "; ".join(f"{o.tool} {o.arguments.get('order_id')} done ({o.op_id})" for o in state.operations)
    world.add_ticket_note(hashlib.sha256(f"{state.task_id}|note|{note}".encode()).hexdigest()[:16],
                          f"Resolved by {state.variant}/{state.model}, approved by {state.approval.approver}: {note}")
    state.status = "done"
    state.log("stop", "done")
    save(state)
    return state
