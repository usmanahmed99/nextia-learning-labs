"""The simulated provider's web API (OpenAI-compatible paths).

    POST /v1/chat/completions    classify or draft a reply
    POST /v1/embeddings          a vector
    GET  /admin/stats            calls, refusals, requests in flight
    POST /admin/mode             {"mode": "normal" | "slow" | "outage" | "quota"}
    POST /admin/reset            stats to zero, quota full, mode normal

Modes (simulated failures, label them as simulated when you show them):
- normal: times and quota as recorded from the real provider
- slow:   every answer takes SIM_SLOW_FACTOR times longer (default 8)
- outage: every request fails with HTTP 503 after a short wait
- quota:  the quota is 10 times smaller, so most requests get HTTP 429
"""

import asyncio
import math
import os
import random
import time
from collections import Counter

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from simulator import model
from simulator.quota import Quota

MODES = ("normal", "slow", "outage", "quota")


class Settings:
    def __init__(self) -> None:
        self.mode = os.environ.get("SIM_MODE", "normal")
        self.speed = float(os.environ.get("SIM_SPEED", "1.0"))
        self.seed = int(os.environ.get("SIM_SEED", "21"))
        self.slow_factor = float(os.environ.get("SIM_SLOW_FACTOR", "8"))
        self.quota_on = os.environ.get("SIM_QUOTA", "on") != "off"
        if self.mode not in MODES:
            raise SystemExit(f"SIM_MODE must be one of {', '.join(MODES)}")


class ModeIn(BaseModel):
    mode: str


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or Settings()
    app = FastAPI(title="Simulated AI provider", docs_url="/docs")
    state = {
        "mode": s.mode,
        "in_flight": 0,
        "max_in_flight": 0,
        "calls": Counter(),
        "tokens": 0,
        "started": time.time(),
    }
    rng = random.Random(s.seed)
    quotas: dict[str, Quota] = {}

    def make_quotas() -> None:
        quotas.clear()
        if not s.quota_on:
            return
        divide = 10 if state["mode"] == "quota" else 1
        for name, q in model.CALIBRATION["quota"].items():
            quotas[name] = Quota(
                q["rpm"] / divide if q.get("rpm") else None,
                q["tpm"] / divide if q.get("tpm") else None,
                model.CALIBRATION["quota_burst_seconds"],
            )

    make_quotas()

    async def handle(path: str, request: Request) -> JSONResponse:
        body = await request.json()
        name = body.get("model", "")
        task = "embed" if path == "embeddings" else model.chat_task(body)
        headers = {"X-Simulated": "true"}
        state["in_flight"] += 1
        state["max_in_flight"] = max(state["max_in_flight"], state["in_flight"])
        try:
            if name not in model.CALIBRATION["quota"]:
                state["calls"][(task, 404)] += 1
                return JSONResponse(
                    {
                        "error": {
                            "code": "DeploymentNotFound",
                            "message": f"No model named {name!r}.",
                        }
                    },
                    404,
                )
            if state["mode"] == "outage":
                await asyncio.sleep(model.CALIBRATION["outage_ms"] / 1000 * s.speed)
                state["calls"][(task, 503)] += 1
                return JSONResponse(
                    {
                        "error": {
                            "code": "ServiceUnavailable",
                            "message": "The service is unavailable (simulated outage).",
                        }
                    },
                    503,
                    headers=headers,
                )
            quota = quotas.get(name)
            wait = quota.try_take(model.request_tokens(path, body)) if quota else None
            if wait is not None:
                await asyncio.sleep(model.CALIBRATION["refusal_ms"] / 1000 * s.speed)
                state["calls"][(task, 429)] += 1
                return JSONResponse(
                    {
                        "error": {
                            "code": "rate_limit_exceeded",
                            "type": "too_many_requests",
                            "message": f"Your requests to {name} have exceeded the request "
                            "rate limit (simulated).",
                        }
                    },
                    429,
                    headers={
                        **headers,
                        "Retry-After": str(model.CALIBRATION["retry_after_seconds"]),
                        "retry-after-ms": str(max(1, math.ceil(wait * 1000))),
                    },
                )
            ms = model.sample_latency_ms(task, rng)
            if state["mode"] == "slow":
                ms *= s.slow_factor
            await asyncio.sleep(ms / 1000 * s.speed)
            answer = (
                model.embed_answer(body, name)
                if path == "embeddings"
                else model.chat_answer(body, name)
            )
            state["tokens"] += answer["usage"]["total_tokens"]
            state["calls"][(task, 200)] += 1
            return JSONResponse(answer, headers=headers)
        finally:
            state["in_flight"] -= 1

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        return await handle("chat/completions", request)

    @app.post("/v1/embeddings")
    async def embeddings(request: Request):
        return await handle("embeddings", request)

    @app.get("/admin/stats")
    def stats():
        calls = {}
        for (task, status), n in sorted(state["calls"].items()):
            calls.setdefault(task, {})[str(status)] = n
        return {
            "mode": state["mode"],
            "in_flight": state["in_flight"],
            "max_in_flight": state["max_in_flight"],
            "calls": calls,
            "tokens": state["tokens"],
            "simulated": True,
        }

    @app.post("/admin/mode")
    def set_mode(new: ModeIn):
        if new.mode not in MODES:
            return JSONResponse({"error": f"mode must be one of {', '.join(MODES)}"}, 422)
        state["mode"] = new.mode
        make_quotas()
        return {"mode": state["mode"]}

    @app.post("/admin/reset")
    def reset():
        state.update(
            mode=s.mode if s.mode != "quota" else "normal",
            in_flight=state["in_flight"],
            max_in_flight=0,
            calls=Counter(),
            tokens=0,
        )
        make_quotas()
        return {"mode": state["mode"]}

    return app
