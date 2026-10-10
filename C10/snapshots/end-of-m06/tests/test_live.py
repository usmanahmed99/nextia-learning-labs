"""An opt-in live test: one task with your own provider (`RESOLVER_PROVIDER=openai_compatible`).

    PYTEST_LIVE=1 python -m pytest -m live

It needs a model with JSON-schema output (any) or tool calling (for --variant agent). The usage cap in
config.py (8 steps, US$0.05 per task by default) applies.
"""

import os

import pytest

from resolver.config import Settings, make_provider
from resolver.data import load_task
from resolver.runner import run_task


@pytest.mark.live
def test_one_live_task(world):
    settings = Settings.from_env()
    if settings.provider == "mock" or os.environ.get("PYTEST_LIVE") != "1":
        pytest.skip("set RESOLVER_PROVIDER=openai_compatible and PYTEST_LIVE=1")
    task = load_task("T-80008")
    state = run_task(task, "agent_structured", settings.model, make_provider(settings).complete, world(task.task_id),
                     settings.limits())
    assert state.stop_reason in ("finished", "max_steps", "time", "cost", "too_many_errors")
    assert state.step <= settings.max_steps
