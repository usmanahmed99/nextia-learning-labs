"""Settings from environment variables (and an optional .env file), the provider, and the limits.

The key is read here and given only to the provider. It is never printed, logged or saved.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .loop import Limits
from .providers import MockProvider, OpenAICompatibleProvider

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path | None = None) -> None:
    """Read KEY=value lines from .env into the environment (variables already set win)."""
    path = path or ENV_FILE
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    provider: str = "mock"            # "mock" or "openai_compatible"
    model: str = "chat-small"         # the recordings: chat-small, chat-strong
    base_url: str = ""                # for example http://localhost:11434/v1 for Ollama
    api_key: str = field(default="", repr=False)   # repr=False: printing the settings never shows the key
    timeout_s: float = 60.0
    reasoning_effort: str = ""        # sent only when set (some models need it for tools, others reject it)
    max_steps: int = 8                # the step limit, per task (Module 2 adds time and spending caps)

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file()
        env = os.environ
        return cls(provider=env.get("RESOLVER_PROVIDER", "mock"), model=env.get("RESOLVER_MODEL", "chat-small"),
                   base_url=env.get("RESOLVER_BASE_URL", ""), api_key=env.get("RESOLVER_API_KEY", ""),
                   timeout_s=float(env.get("RESOLVER_TIMEOUT_S", "60")),
                   reasoning_effort=env.get("RESOLVER_REASONING_EFFORT", ""),
                   max_steps=int(env.get("RESOLVER_MAX_STEPS", "8")))

    def limits(self) -> Limits:
        return Limits(max_steps=self.max_steps)


def make_provider(settings: Settings):
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai_compatible":
        if not settings.base_url:
            raise ValueError("Set RESOLVER_BASE_URL, for example http://localhost:11434/v1 for Ollama.")
        return OpenAICompatibleProvider(settings.base_url, settings.api_key, settings.timeout_s,
                                        settings.reasoning_effort)
    raise ValueError(f"Unknown RESOLVER_PROVIDER {settings.provider!r}: use mock or openai_compatible.")


SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-[REDACTED]"),
    (re.compile(r"(?i)(api[-_]?key|authorization)(\"?\s*[:=]\s*\"?)(bearer\s+)?[^\s\",}]+"), r"\1\2[REDACTED]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer [REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
