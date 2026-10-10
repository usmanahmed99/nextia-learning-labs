"""A scripted provider for the tests: it returns a fixed list of tool calls, then an answer, without
any model or recording. It lets the tests check the controls on their own."""

from support_assistant.providers import Completion, ToolCall


def completion(text="", tool_calls=None):
    return Completion(text=text, finish_reason="stop", refusal=None, tool_calls=tool_calls or [],
                      model="scripted", input_tokens=10, output_tokens=5, reasoning_tokens=0, latency_s=0.0, raw={})


class Scripted:
    """complete() returns the next step each time it is called. A step is (text, [(name, args_json), ...])."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def complete(self, request, meta=None):
        self.calls.append((request, meta))
        if self.steps:
            text, tool_calls = self.steps.pop(0)
            tcs = [ToolCall(id=f"c{i}", name=n, arguments=a) for i, (n, a) in enumerate(tool_calls)]
            return completion(text=text, tool_calls=tcs)
        return completion(text="Done.")
