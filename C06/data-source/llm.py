"""Shared call helper for the M02 tests (same patterns as ../run_models.py).

Keys come only from the environment (load ~/.config/nextia/llm.env in your own
shell); they are never printed or written. Returns a dict with the visible text,
token counts as the provider reports them, and the time in seconds.
"""
import base64
import os
import time

import truststore

truststore.inject_into_ssl()  # use the operating system's certificates (some networks inspect TLS)

import httpx


def call(provider: str, model: str, prompt: str, max_tokens: int = 600, temperature: float | None = 0,
         num_ctx: int | None = None, image: bytes | None = None, think: bool | None = False, seed: int | None = None) -> dict:
    started = time.perf_counter()
    out = {"provider": provider, "model": model, "reasoning_tokens": 0, "stop_reason": None}
    if provider == "ollama":
        options = {"num_predict": max_tokens}
        if temperature is not None:
            options["temperature"] = temperature
        if num_ctx:
            options["num_ctx"] = num_ctx
        if seed is not None:
            options["seed"] = seed
        body = {"model": model, "prompt": prompt, "stream": False, "options": options}
        if think is not None:
            body["think"] = think
        if image:
            body["images"] = [base64.b64encode(image).decode()]
        d = httpx.post("http://localhost:11434/api/generate", timeout=1800, json=body).raise_for_status().json()
        out.update(text=d["response"], thinking=d.get("thinking", ""), input_tokens=d.get("prompt_eval_count"),
                   output_tokens=d.get("eval_count"), stop_reason=d.get("done_reason"),
                   load_seconds=round(d.get("load_duration", 0) / 1e9, 2))
    elif provider == "anthropic":
        content = [{"type": "text", "text": prompt}]
        if image:
            content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                           "data": base64.b64encode(image).decode()}})
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=600, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"}, json={
            "model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": content}]})
        if r.status_code >= 400:
            raise SystemExit(f"{r.status_code}: {r.text[:300]}")
        d = r.json()
        out.update(text="".join(b.get("text", "") for b in d["content"] if b.get("type") == "text"),
                   input_tokens=d["usage"]["input_tokens"], output_tokens=d["usage"]["output_tokens"],
                   stop_reason=d.get("stop_reason"))
    elif provider == "gemini":
        parts = [{"text": prompt}]
        if image:
            parts.insert(0, {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image).decode()}})
        cfg = {"maxOutputTokens": max_tokens}
        if temperature is not None:
            cfg["temperature"] = temperature
        r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", timeout=600,
                       headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
                       json={"contents": [{"parts": parts}], "generationConfig": cfg})
        if r.status_code >= 400:
            raise SystemExit(f"{r.status_code}: {r.text[:300]}")
        d = r.json()
        c = d["candidates"][0]
        u = d["usageMetadata"]
        out.update(text="".join(p.get("text", "") for p in c["content"].get("parts", []) if not p.get("thought")),
                   input_tokens=u["promptTokenCount"], output_tokens=u.get("candidatesTokenCount", 0),
                   reasoning_tokens=u.get("thoughtsTokenCount", 0), stop_reason=c.get("finishReason"))
    else:
        raise SystemExit(f"unknown provider {provider}")
    out["seconds"] = round(time.perf_counter() - started, 2)
    return out
