import json

from assistant.providers import Completion
from assistant.usage import Budget, UsageLog, cost_usd, over_budget, summarise


def completion(tokens_in=2000, tokens_out=400, latency=1.0):
    data = {"id": "chatcmpl-x", "model": "m", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out}}
    return Completion.from_response(data, latency)


def test_cost_comes_from_the_price_table():
    assert cost_usd("chat-small", 1_000_000, 1_000_000) == 0.60
    assert cost_usd("chat-strong", 2000, 400) == 0.008
    assert cost_usd("a-model-we-have-no-price-for", 10, 10) is None


def test_the_log_has_numbers_but_no_ticket_text_and_no_secrets(tmp_path):
    log = UsageLog(tmp_path / "usage.jsonl")
    log.record(completion(), "chat-small", "T-80008", "v2", note="retry after Bearer abcdefgh12345678")
    line = (tmp_path / "usage.jsonl").read_text()
    entry = json.loads(line)
    assert entry["input_tokens"] == 2000 and entry["cost_usd"] == 0.0004 and entry["request_id"] == "chatcmpl-x"
    assert "abcdefgh12345678" not in line and "shed" not in line


def test_summary_and_budget():
    entries = [{"input_tokens": 2000, "output_tokens": 400, "latency_s": s, "cost_usd": 0.0004} for s in range(1, 21)]
    s = summarise(entries)
    assert s["calls"] == 20 and s["latency_median_s"] == 10.5 and s["latency_p95_s"] == 20
    assert over_budget(entries[:1], Budget()) == []
    assert over_budget(entries[:5], Budget(max_tokens_per_ticket=8000)) == ["12000 tokens > 8000"]
