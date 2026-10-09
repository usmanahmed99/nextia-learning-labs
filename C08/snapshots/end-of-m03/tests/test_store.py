import pytest

from assistant.schema import TicketAnalysis
from assistant.store import InvalidResult, ResultStore
from assistant.validate import Problem, Verdict

GOOD = TicketAnalysis.model_validate({"language": "en", "team": "delivery", "needs_human": False, "reason": "r",
                                      "confidence": "high", "order": None, "reply": "We will check."})


def test_a_rejected_result_never_reaches_the_database(tmp_path):
    store = ResultStore(tmp_path / "results.sqlite")
    for verdict in (Verdict(None, [Problem("malformed_json", "x")]), Verdict(GOOD, [Problem("promise", "x")])):
        with pytest.raises(InvalidResult):
            store.save("T-1", verdict, "v2", "chat-small")
    assert store.count() == 0


def test_a_valid_result_is_saved(tmp_path):
    store = ResultStore(tmp_path / "results.sqlite")
    store.save("T-1", Verdict(GOOD), "v2", "chat-small")
    assert store.count() == 1
