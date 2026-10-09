from assistant.context import build_request
from assistant.data import load_tickets
from assistant.orders import OrderBook
from assistant.providers import ProviderError
from assistant.schema import response_format
from assistant.stream import as_completion, stream_answer
from assistant.validate import validate

import pytest

TICKET = load_tickets()["T-64704"]
REQUEST = build_request(TICKET, "chat-small", "v2", response_format())


def test_a_recorded_stream_arrives_in_pieces_and_is_checked_only_at_the_end(mock):
    shown = []
    result = stream_answer(mock, REQUEST, show=shown.append)
    assert result.complete and len(shown) > 50 and result.first_piece_s > 1.0
    verdict = validate(as_completion(result), TICKET, OrderBook())
    assert verdict.valid and verdict.analysis.needs_human is True


def test_a_cancelled_stream_is_partial_text_not_data(mock):
    count = iter(range(1000))
    result = stream_answer(mock, REQUEST, cancel=lambda: next(count) >= 20)
    assert result.cancelled and not result.complete and len(result.pieces) == 20
    with pytest.raises(ValueError, match="Partial text is not data"):
        as_completion(result)


def test_an_interrupted_stream_keeps_its_partial_text_but_is_not_complete(mock):
    class Interrupted:  # simulated: the connection breaks after 10 pieces
        def stream(self, request):
            for i, piece in enumerate(mock.stream(request)):
                if i == 10:
                    raise ProviderError("Connection lost (simulated).")
                yield piece

    result = stream_answer(Interrupted(), REQUEST)
    assert result.error and not result.complete and len(result.pieces) == 10
