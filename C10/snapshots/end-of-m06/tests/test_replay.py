"""Robust replay: exact requests replay silently; a different request at the same task and step replays
with a note and is checked against your state; an unrecorded task stops cleanly."""

import pytest

from resolver.context import first_messages
from resolver.providers import MockProvider, RecordingNotFound
from resolver.tools import function_tools


def first_request(task_text, attachments=()):
    return {"model": "chat-small", "messages": first_messages("agent", task_text, list(attachments)),
            "max_completion_tokens": 2000, "tools": function_tools(), "tool_choice": "required"}


def test_exact_replay_is_silent():
    from resolver.data import load_task
    t = load_task("T-80008")
    c = MockProvider().complete(first_request(t.text, t.attachments),
                                {"task_id": "T-80008", "variant": "agent", "step": 1})
    assert c.note == "" and c.tool_calls[0].name == "get_order"


def test_a_changed_request_replays_with_a_note():
    from resolver.data import load_task
    t = load_task("T-80008")
    request = first_request(t.text + " Thanks!", t.attachments)       # the learner changed the prompt
    c = MockProvider().complete(request, {"task_id": "T-80008", "variant": "agent", "step": 1, "state": "x"})
    assert "differs from the recorded one" in c.note
    assert c.tool_calls                                               # still a decision, checked by the loop


def test_an_unrecorded_task_raises_recording_not_found():
    with pytest.raises(RecordingNotFound):
        MockProvider().complete(first_request("Something new"), {"task_id": "T-99999", "variant": "agent", "step": 1})


def test_repeats_are_recorded_for_the_agent():
    assert MockProvider().repeats("chat-small", "agent", "T-80008") == [1, 2, 3]
