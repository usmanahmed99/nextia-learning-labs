"""Incident response: turn a tool off and revoke a user at once, with no new release, and undo it."""

import json

from support_assistant import incident
from support_assistant.assistant import run_case
from support_assistant.data import load_attacks, load_tasks
from support_assistant.providers import MockProvider
from support_assistant.runner import fresh_world
from tests.scripted import Scripted


def test_a_disabled_tool_leaves_the_tool_list_and_a_call_is_refused():
    w = fresh_world()
    incident.disable_tool(w, "fetch_url", "SSRF alert")
    model = Scripted([("", [("fetch_url", json.dumps({"url": "https://www.aquaflow-supply.example/support"}))]),
                      ("I could not check the page.", [])])
    st = run_case(load_attacks()["ATK-20"], model.complete, w, "scripted", "secure")
    sent = {t["function"]["name"] for t in model.calls[0][0]["tools"]}
    assert "fetch_url" not in sent
    assert st.tool_events[0].code == "tool_disabled" and not st.tool_events[0].allowed
    # The recorded reply of TASK-08 quotes the fetched page: with the tool off, it is not replayed.
    st = run_case(load_tasks()["TASK-08"], MockProvider().complete, w, "chat-small", "secure")
    assert st.stop_reason == "no_recording" and st.answer == "" and "disabled" in st.errors[-1]
    assert incident.restore(w, "tool", "fetch_url") and "fetch_url" not in incident.disabled_tools(w)


def test_a_revoked_user_cannot_run_the_assistant():
    w = fresh_world()
    incident.revoke_user(w, "usr-sam", "token leaked")
    st = run_case(load_tasks()["TASK-01"], Scripted([]).complete, w, "scripted", "secure")
    assert st.stop_reason == "revoked" and st.usage_calls == 0
    assert any(e["action"] == "incident_user" for e in w.audit_rows())
