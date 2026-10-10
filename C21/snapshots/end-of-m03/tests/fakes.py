"""A fake AI provider for the tests: the simulated provider's answers, with no waiting.

provider = fake_provider()                 # answers like the simulated provider
provider = fake_provider(fail="quota")     # every call: HTTP 429
provider = fake_provider(fail="outage")    # every call: HTTP 503
provider = fake_provider(fail="bad")       # classify answers with text that is not JSON
"""

import asyncio
import json
import time

import httpx

from simulator import model
from ticket_api.provider import Provider


class Calls:
    def __init__(self) -> None:
        self.paths: list[str] = []

    def __len__(self) -> int:
        return len(self.paths)


def handler(fail: str | None, calls: Calls):
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path.rsplit("/v1/", 1)[-1]
        calls.paths.append(path)
        body = json.loads(request.content)
        if fail == "quota":
            return httpx.Response(
                429,
                headers={"Retry-After": "30", "retry-after-ms": "600"},
                json={"error": {"code": "rate_limit_exceeded"}},
            )
        if fail == "outage":
            return httpx.Response(503, json={"error": {"code": "ServiceUnavailable"}})
        if path == "embeddings":
            return httpx.Response(200, json=model.embed_answer(body, body["model"]))
        answer = model.chat_answer(body, body["model"])
        if fail == "bad" and model.chat_task(body) == "classify":
            answer["choices"][0]["message"]["content"] = "billing, I think"
        return httpx.Response(200, json=answer)

    return handle


def fake_provider(fail: str | None = None, delay: float = 0.0, **options) -> Provider:
    calls = Calls()
    handle = handler(fail, calls)

    def sync_handle(request: httpx.Request) -> httpx.Response:
        time.sleep(delay)
        return handle(request)

    async def async_handle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(delay)
        return handle(request)

    provider = Provider(
        "http://fake-provider/v1",
        transport=httpx.MockTransport(sync_handle),
        async_transport=httpx.MockTransport(async_handle),
        **options,
    )
    provider.calls = calls
    return provider
