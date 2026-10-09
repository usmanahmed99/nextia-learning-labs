"""Show the answer as it arrives, allow cancel, and check only the complete answer.

    python -m assistant.stream T-64704                     replays a recorded stream with its real timing
    python -m assistant.stream T-64704 --cancel-after 20   the agent presses Stop after 20 pieces
    python -m assistant.stream T-64704 --cut-after 40      the connection breaks after 40 pieces (simulated)
"""

import argparse
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

    @property
    def status(self) -> str:
        """How the stream ended: complete, cancelled, interrupted (cut after some pieces) or failed (no piece)."""
        if self.complete:
            return "complete"
        if self.cancelled:
            return "cancelled"
        return "interrupted" if self.pieces else "failed"


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


class CutAfter:
    """Simulated: the connection breaks after `pieces` pieces of a real (or recorded) stream."""

    def __init__(self, inner, pieces: int):
        self.inner, self.pieces = inner, pieces

    def stream(self, request: dict):
        for i, item in enumerate(self.inner.stream(request)):
            if i == self.pieces:
                raise ProviderError("Connection lost (simulated).")
            yield item


def main(argv: list[str] | None = None) -> int:
    from .config import Settings, make_provider
    from .context import build_request
    from .data import load_ticket
    from .orders import OrderBook
    from .schema import response_format
    from .validate import validate

    parser = argparse.ArgumentParser(prog="python -m assistant.stream")
    parser.add_argument("ticket_id", nargs="?", default="T-64704")
    parser.add_argument("--cancel-after", type=int, metavar="N", help="press Stop after N pieces")
    parser.add_argument("--cut-after", type=int, metavar="N", help="break the connection after N pieces (simulated)")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    provider = make_provider(settings)
    if hasattr(provider, "speed"):
        provider.speed = 1.0  # replay the recorded timing
    if args.cut_after is not None:
        provider = CutAfter(provider, args.cut_after)
    try:
        ticket = load_ticket(args.ticket_id)
    except KeyError as error:
        print(error.args[0], file=sys.stderr)
        return 2
    request = build_request(ticket, settings.model, "v2", response_format())
    shown = []

    def show(piece: str) -> None:
        print(piece, end="", flush=True)
        shown.append(piece)

    def stop() -> bool:  # the agent's Stop button, pressed after N pieces
        return args.cancel_after is not None and len(shown) >= args.cancel_after

    start = time.monotonic()
    result = stream_answer(provider, request, show=show, cancel=stop)
    first = f"first after {result.first_piece_s:.2f} s, " if result.pieces else ""
    print(f"\n\n{len(result.pieces)} pieces, {first}all after {time.monotonic() - start:.2f} s")
    if not result.complete:
        reason = f": {result.error}" if result.error else ""
        checked = "not checked: partial text is not data" if result.pieces else "no answer"
        print(f"{result.status}{reason} | {checked}")
        return 1
    verdict = validate(as_completion(result), ticket, OrderBook())
    checked = "valid" if verdict.valid else "rejected: " + ", ".join(p.code for p in verdict.problems)
    print(f"complete | {checked}")
    return 0 if verdict.valid else 1


if __name__ == "__main__":
    sys.exit(main())
