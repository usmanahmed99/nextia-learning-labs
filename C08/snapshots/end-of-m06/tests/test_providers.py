import pytest

from assistant.providers import Completion, MockProvider, RecordingNotFound, request_key


def test_the_key_does_not_depend_on_the_order_of_the_fields():
    a = {"model": "chat-small", "messages": [{"role": "user", "content": "Hi"}], "max_completion_tokens": 10}
    b = {"max_completion_tokens": 10, "messages": [{"role": "user", "content": "Hi"}], "model": "chat-small"}
    assert request_key(a) == request_key(b)


def test_a_different_message_gives_a_different_key():
    a = {"model": "chat-small", "messages": [{"role": "user", "content": "Hi"}]}
    assert request_key(a) != request_key({**a, "messages": [{"role": "user", "content": "Hi!"}]})


def test_the_mock_refuses_a_request_that_was_not_recorded(mock: MockProvider):
    with pytest.raises(RecordingNotFound):
        mock.complete({"model": "chat-small", "messages": [{"role": "user", "content": "Not recorded"}]})


def test_a_response_becomes_a_completion():
    data = {"id": "chatcmpl-1", "model": "m", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3, "completion_tokens_details": {"reasoning_tokens": 1}}}
    c = Completion.from_response(data, 0.5)
    assert (c.text, c.finish_reason, c.input_tokens, c.output_tokens, c.reasoning_tokens) == ("{}", "stop", 12, 3, 1)
    assert c.tool_calls == [] and c.refusal is None
