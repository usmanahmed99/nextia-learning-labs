"""The same agent as the course's plain-Python loop, as a LangGraph graph (an optional comparison).

    python graph.py            # in this folder, in a virtual environment made from requirements.txt

It uses the course project, resolution-workflow. It looks for it in this order: the folder named by the
environment variable RESOLUTION_WORKFLOW; a folder resolution-workflow next to this folder; the snapshot
end-of-m04 of the labs repository (../../snapshots/end-of-m04).

Nodes: decide (one model call) -> act (run the reads) -> decide ... -> approve (interrupt: wait for a
person) -> execute (the course's own execute(), with operation IDs) -> END.
State: the course's TaskState, carried as one field. Checkpoints: LangGraph's SqliteSaver.
Model decisions: the course's MockProvider replays the recorded chat-small decisions; the requests are
built exactly as resolver/loop.py builds them, so the replays are exact.

It runs three things and prints what happened:
1. T-90103 end to end: interrupt at the approval, resume with the approval, the two writes.
2. The same graph on all 70 tasks: the proposals are the same as the plain loop's (they replay the same
   recordings, so this checks that the graph does the same steps, not that it decides better).
3. LangGraph's documented resume rule ("the graph resumes from the start of the node, re-executing all
   logic"): a node that writes BEFORE its interrupt writes twice after a resume, unless the write is
   idempotent (an operation ID).
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import TypedDict

HERE = Path(__file__).resolve().parent


def find_project() -> Path:
    """The course project: RESOLUTION_WORKFLOW, else ../resolution-workflow, else the labs snapshot end-of-m04."""
    candidates = [Path(os.environ["RESOLUTION_WORKFLOW"])] if os.environ.get("RESOLUTION_WORKFLOW") else []
    candidates += [HERE.parent / "resolution-workflow", HERE.parent.parent / "snapshots" / "end-of-m04"]
    for folder in candidates:
        if (folder / "resolver" / "__init__.py").exists():
            return folder.resolve()
    sys.exit("Cannot find the project resolution-workflow. Set RESOLUTION_WORKFLOW to its folder.")


sys.path.insert(0, str(find_project()))

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer  # noqa: E402
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

from resolver.approval import approval_request, decide as approval_decide, required_role  # noqa: E402
from resolver.context import MAX_TOKENS, compact, first_messages  # noqa: E402
from resolver.data import SEED_DB, load_tasks  # noqa: E402
from resolver.execute import execute  # noqa: E402
from resolver.loop import accept_resolution, account  # noqa: E402
from resolver.providers import MockProvider, ProviderError  # noqa: E402
from resolver.runner import new_state, run_task  # noqa: E402
from resolver.state import Evidence, TaskState  # noqa: E402
from resolver.systems import Faults, World  # noqa: E402
from resolver.tools import function_tools, run_read  # noqa: E402

PROVIDER = MockProvider()
MAX_STEPS = 8


class GraphState(TypedDict):
    task: TaskState          # the course's typed state, carried whole
    pending: list            # the tool calls of the last model answer, for the act node
    db: str                  # the practice database of this run


def world_of(gs: GraphState) -> World:
    return World(Path(gs["db"]), gs["task"].task_id, Faults())


def decide(gs: GraphState) -> dict:
    s = gs["task"].model_copy(deep=True)
    if not s.messages:
        s.messages = first_messages("agent", s.goal, s.attachments)
    request = {"model": s.model, "messages": list(s.messages), "max_completion_tokens": MAX_TOKENS,
               "tools": function_tools(), "tool_choice": "required"}
    s.step += 1
    try:
        c = PROVIDER.complete(request, {"task_id": s.task_id, "variant": "agent", "step": s.step,
                                        "state": s.evidence_digest()})
    except ProviderError as e:      # for example the provider's content filter (a real HTTP 400 on T-80002)
        s.stop_reason, s.status = "provider_error", "stopped"
        s.errors.append(str(e))
        return {"task": s, "pending": []}
    account(s, c, s.model)
    s.messages.append({"role": "assistant", "content": c.text, "tool_calls": [
        {"id": t.id, "type": "function", "function": {"name": t.name, "arguments": t.arguments}} for t in c.tool_calls]})
    return {"task": s, "pending": [(t.id, t.name, t.arguments) for t in c.tool_calls]}


def act(gs: GraphState) -> dict:
    s = gs["task"].model_copy(deep=True)
    for call_id, name, arguments in gs["pending"]:
        if name == "finish":
            problem = accept_resolution(s, json.loads(arguments))
            text = compact({"ok": not problem, "error": problem} if problem else {"ok": True, "result": "Received."})
        else:
            r = run_read(name, arguments, s.customer_id, world_of(gs))
            s.evidence.append(Evidence(step=s.step, tool=name, arguments=json.loads(arguments), ok=r.ok, code=r.code,
                                       data=r.data, error=r.error, order_ids=r.order_ids))
            text = r.for_model()
        s.messages.append({"role": "tool", "tool_call_id": call_id, "content": text})
    if s.proposal is not None:
        s.stop_reason = "finished"
        s.status = "waiting_approval" if s.proposal.actions else (
            "handed_to_person" if s.proposal.outcome == "hand_to_person" else "done")
    return {"task": s, "pending": []}


def after_act(gs: GraphState) -> str:
    s = gs["task"]
    if s.stop_reason == "provider_error":
        return END
    if s.proposal is not None:
        return "approve" if s.proposal.actions else END
    return "decide" if s.step < MAX_STEPS else END


def approve(gs: GraphState) -> dict:
    s = gs["task"].model_copy(deep=True)
    answer = interrupt({"approval_request": approval_request(s), "required_role": required_role(s)})
    approval_decide(s, answer["approve"], answer["name"], answer["role"])
    return {"task": s}


def run_execute(gs: GraphState) -> dict:
    s = gs["task"].model_copy(deep=True)
    if s.status == "executing":
        execute(s, world_of(gs))
    return {"task": s}


def build(checkpointer):
    g = StateGraph(GraphState)
    g.add_node("decide", decide)
    g.add_node("act", act)
    g.add_node("approve", approve)
    g.add_node("execute", run_execute)
    g.add_edge(START, "decide")
    g.add_edge("decide", "act")
    g.add_conditional_edges("act", after_act, {"decide": "decide", "approve": "approve", END: END})
    g.add_edge("approve", "execute")
    g.add_edge("execute", END)
    return g.compile(checkpointer=checkpointer)


class Saver:
    """SqliteSaver that may read back the course's TaskState (LangGraph asks you to name your own types)."""

    def __init__(self, path: Path):
        self.con = sqlite3.connect(str(path), check_same_thread=False)

    def __enter__(self):
        return SqliteSaver(self.con, serde=JsonPlusSerializer(
            allowed_msgpack_modules=[("resolver.state", "TaskState"), ("resolver.schema", "Resolution"),
                                     ("resolver.schema", "ReturnLabel"), ("resolver.schema", "Reship"),
                                     ("resolver.schema", "Refund"), ("resolver.state", "Evidence"),
                                     ("resolver.state", "Event"), ("resolver.state", "Approval"),
                                     ("resolver.state", "Operation"), ("resolver.state", "Usage")]))

    def __exit__(self, *exc):
        self.con.close()


def changes(db: str) -> list[tuple]:
    with sqlite3.connect(db) as con:
        return con.execute("SELECT 'refund', order_id, amount FROM refunds WHERE op_id NOT LIKE 'seed-%' UNION ALL "
                           "SELECT 'label', order_id, sku FROM return_labels WHERE op_id NOT LIKE 'seed-%' UNION ALL "
                           "SELECT 'reship', order_id, sku FROM reshipments").fetchall()


def fresh_db(tmp: Path, name: str) -> str:
    db = tmp / f"{name}.sqlite"
    shutil.copyfile(SEED_DB, db)
    return str(db)


def demo_one(tmp: Path) -> None:
    task = load_tasks()["T-90103"]
    with Saver(tmp / "checkpoints.sqlite") as saver:
        graph = build(saver)
        config = {"configurable": {"thread_id": "T-90103"}}
        db = fresh_db(tmp, "one")
        out = graph.invoke({"task": new_state(task, "agent", "chat-small", "lg-T-90103"), "pending": [], "db": db},
                           config)
        print("1. Paused at:", graph.get_state(config).next, "| interrupt value keys:",
              list(out["__interrupt__"][0].value))
        print("   changes before approval:", changes(db))
        out = graph.invoke(Command(resume={"approve": True, "name": "Amira", "role": "agent"}), config)
        s = out["task"]
        print("   after resume:", s.status, [(o.tool, o.status) for o in s.operations], "| changes:", changes(db))


def demo_all(tmp: Path) -> dict:
    plain = {}          # the plain-Python loop of the project (with its simulated faults), on the same recordings
    for task in load_tasks().values():
        db = fresh_db(tmp, f"plain-{task.task_id}")
        world = World(Path(db), task.task_id, Faults(task.faults))
        p = run_task(task, "agent", "chat-small", PROVIDER.complete, world).proposal
        plain[task.task_id] = (p.outcome, [a.model_dump() for a in p.actions]) if p else None
    same, differ = 0, []
    with Saver(tmp / "all.sqlite") as saver:
        graph = build(saver)
        for task in load_tasks().values():
            db = fresh_db(tmp, task.task_id)
            out = graph.invoke({"task": new_state(task, "agent", "chat-small", f"lg-{task.task_id}"), "pending": [],
                                "db": db}, {"configurable": {"thread_id": task.task_id}, "recursion_limit": 40})
            p = out["task"].proposal
            got = (p.outcome, [a.model_dump() for a in p.actions]) if p else None
            if got == plain[task.task_id]:
                same += 1
            else:
                differ.append(task.task_id)
    print(f"2. Same proposal as the plain loop: {same} of {len(load_tasks())}; different: {differ}")
    return {"same": same, "different": differ}


def demo_resume_rule(tmp: Path) -> dict:
    """A node that writes, then interrupts. On resume, LangGraph runs the node again from its start."""
    results = {}
    for label, op_id_of in (("new ID per call (not idempotent)", lambda n: f"call-{n}"),
                            ("operation ID from the ticket and action", lambda n: "T-90104-refund-LK-793996-9.95")):
        db = fresh_db(tmp, f"rule-{len(results)}")
        calls = {"n": 0}

        def write_then_ask(gs: GraphState) -> dict:
            calls["n"] += 1
            World(Path(gs["db"]), "T-90104").request_refund(op_id_of(calls["n"]), "LK-793996", 9.95, "RFD-LATE")
            interrupt({"question": "Send the reply too?"})
            return {}

        g = StateGraph(GraphState)
        g.add_node("write_then_ask", write_then_ask)
        g.add_edge(START, "write_then_ask")
        g.add_edge("write_then_ask", END)
        with Saver(tmp / f"rule{len(results)}.sqlite") as saver:
            graph = g.compile(checkpointer=saver)
            config = {"configurable": {"thread_id": "rule"}}
            graph.invoke({"task": new_state(load_tasks()["T-90104"], "agent", "chat-small", "rule"), "pending": [],
                          "db": db}, config)
            graph.invoke(Command(resume=True), config)
        results[label] = {"node_runs": calls["n"], "refunds": len(changes(db))}
    print("3. Resume re-runs the node:", results)
    return results


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="c10-langgraph-"))
    demo_one(tmp)
    result = {"all": demo_all(tmp), "resume_rule": demo_resume_rule(tmp)}
    (HERE / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
