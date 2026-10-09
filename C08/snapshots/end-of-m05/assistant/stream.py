"""Show the answer as it arrives, allow cancel, and check only the complete answer.

    python -m assistant.stream T-64704      (replays a recorded stream with its real timing)
"""

import sys
import time
from dataclasses import dataclass, field
from typing import Callable

from .providers import Completion, ProviderError


@dataclass
class StreamResult:
    text: str = ""
    complete: bool = False   # True only when the stream ended normally
    cancelled: bool = False
    error: str = ""
    pieces: list[tuple[float, str]] = field(default_factory=list)

    @property
    def first_piece_s(self) -> float | None:
        return self.pieces[0][0] if self.pieces else None


def stream_answer(provider, request: dict, show: Callable[[str], None] = lambda piece: None,
                  cancel: Callable[[], bool] = lambda: False) -> StreamResult:
    result = StreamResult()
    try:
        for at, piece in provider.stream(request):
            if cancel():
                result.cancelled = True
                return result
            result.pieces.append((at, piece))
            result.text += piece
            show(piece)
    except ProviderError as error:
        result.error = str(error)  # what arrived before the error stays partial text
        return result
    result.complete = True
    return result


def as_completion(result: StreamResult) -> Completion:
    """Only a complete stream becomes a Completion that validate() may check."""
    if not result.complete:
        raise ValueError("Partial text is not data: the stream did not finish.")
    data = {"choices": [{"message": {"content": result.text}, "finish_reason": "stop"}]}
    return Completion.from_response(data, result.pieces[-1][0] if result.pieces else 0.0)


def main(ticket_id: str) -> None:
    from .config import Settings, make_provider
    from .context import build_request
    from .data import load_ticket
    from .schema import response_format

    settings = Settings.from_env()
    provider = make_provider(settings)
    if hasattr(provider, "speed"):
        provider.speed = 1.0  # replay the recorded timing
    request = build_request(load_ticket(ticket_id), settings.model, "v2", response_format())
    start = time.monotonic()
    result = stream_answer(provider, request, show=lambda piece: print(piece, end="", flush=True))
    print(f"\n\n{len(result.pieces)} pieces, first after {result.first_piece_s:.2f} s, "
          f"all after {time.monotonic() - start:.2f} s, complete: {result.complete}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "T-64704")
