"""The design where the model chooses the steps: one agent.

One loop. The model chooses which reads to make and when to finish, and proposes the resolution.
With tool calling ("tools") or with one JSON step per call ("structured").
"""

from typing import Callable

from .context import first_messages
from .loop import Limits, run_loop
from .state import TaskState
from .systems import World
from .tools import function_tools


def run_agent(state: TaskState, complete: Callable, world: World, mode: str = "tools",
              limits: Limits = Limits(), on_step=None) -> TaskState:
    prompt = "agent" if mode == "tools" else "agent_structured"
    messages = first_messages(prompt, state.goal, state.attachments)
    return run_loop(state, complete, world, mode=mode, first_messages=messages, limits=limits,
                    tools=function_tools() if mode == "tools" else None, on_step=on_step)
