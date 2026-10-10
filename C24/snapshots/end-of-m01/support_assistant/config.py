"""Settings and the provider.

The settings come from environment variables (and a .env file, if you made one).
"""

import os
from dataclasses import dataclass
from pathlib import Path

from .providers import MockProvider, OpenAICompatibleProvider

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path | None = None) -> None:
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
    provider: str = "mock"
    model: str = "chat-small"
    base_url: str = ""
    api_key: str = ""
    timeout_s: float = 60.0
    reasoning_effort: str = ""
    max_steps: int = 8
    max_seconds: float = 120.0
    max_cost_usd: float = 0.05

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file()
        env = os.environ
        return cls(provider=env.get("ASSISTANT_PROVIDER", "mock"), model=env.get("ASSISTANT_MODEL", "chat-small"),
                   base_url=env.get("ASSISTANT_BASE_URL", ""), api_key=env.get("ASSISTANT_API_KEY", ""),
                   timeout_s=float(env.get("ASSISTANT_TIMEOUT_S", "60")),
                   reasoning_effort=env.get("ASSISTANT_REASONING_EFFORT", ""),
                   max_steps=int(env.get("ASSISTANT_MAX_STEPS", "8")),
                   max_seconds=float(env.get("ASSISTANT_MAX_SECONDS", "120")),
                   max_cost_usd=float(env.get("ASSISTANT_MAX_COST_USD", "0.05")))


def make_provider(settings: Settings):
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai_compatible":
        if not settings.base_url:
            raise ValueError("Set ASSISTANT_BASE_URL, for example http://localhost:11434/v1 for Ollama.")
        return OpenAICompatibleProvider(settings.base_url, settings.api_key, settings.timeout_s,
                                        settings.reasoning_effort)
    raise ValueError(f"Unknown ASSISTANT_PROVIDER {settings.provider!r}: use mock or openai_compatible.")
