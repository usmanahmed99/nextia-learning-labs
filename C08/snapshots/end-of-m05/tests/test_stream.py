from assistant.context import build_request
from assistant.data import load_tickets
from assistant.orders import OrderBook
from assistant.schema import response_format
from assistant.stream import CutAfter, as_completion, stream_answer
from assistant.validate import validate

import pytest

TICKET = load_tickets()["T-64704"]
REQUEST = build_request(TICKET, "chat-small", "v2", response_format())


def test_a_recorded_stream_arrives_in_pieces_and_is_checked_only_at_the_end(mock):
    shown = []
    result = stream_answer(mock, REQUEST, show=shown.append)
    assert result.complete and result.status == "complete" and len(shown) > 50 and result.first_piece_s > 1.0
    verdict = validate(as_completion(result), TICKET, OrderBook())
    assert verdict.valid and verdict.analysis.needs_human is True


def test_a_cancelled_stream_is_partial_text_not_data(mock):
    count = iter(range(1000))
    result = stream_answer(mock, REQUEST, cancel=lambda: next(count) >= 20)
    assert result.cancelled and not result.complete and len(result.pieces) == 20 and result.status == "cancelled"
    with pytest.raises(ValueError, match="Partial text is not data"):
        as_completion(result)


def test_an_interrupted_stream_keeps_its_partial_text_but_is_not_complete(mock):
    result = stream_answer(CutAfter(mock, 10), REQUEST)  # simulated: the connection breaks after 10 pieces
    assert result.error == "Connection lost (simulated)." and not result.complete and len(result.pieces) == 10
    assert result.status == "interrupted"
    with pytest.raises(ValueError, match="Partial text is not data"):
        as_completion(result)
