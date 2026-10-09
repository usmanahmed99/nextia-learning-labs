"""Settings for the optional live judge, from environment variables (or a .env file).

The key is read here and given only to the provider. It is never printed, logged or saved.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .providers import CappedProvider, MockProvider, OpenAICompatibleProvider

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
    provider: str = "mock"           # "mock" or "openai_compatible"
    judge_model: str = "chat-strong"  # the mock has chat-small and chat-strong
    base_url: str = ""
    api_key: str = field(default="", repr=False)  # repr=False: printing the settings never shows the key
    timeout_s: float = 60.0
    max_calls: int = 20               # the usage cap of a live judge
    max_tokens: int = 60_000

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file()
        env = os.environ
        return cls(provider=env.get("JUDGE_PROVIDER", "mock"), judge_model=env.get("JUDGE_MODEL", "chat-strong"),
                   base_url=env.get("JUDGE_BASE_URL", ""), api_key=env.get("JUDGE_API_KEY", ""),
                   timeout_s=float(env.get("JUDGE_TIMEOUT_S", "60")), max_calls=int(env.get("JUDGE_MAX_CALLS", "20")),
                   max_tokens=int(env.get("JUDGE_MAX_TOKENS", "60000")))


def make_provider(settings: Settings):
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai_compatible":
        if not settings.base_url:
            raise ValueError("Set JUDGE_BASE_URL, for example http://localhost:11434/v1 for Ollama.")
        live = OpenAICompatibleProvider(settings.base_url, settings.api_key, settings.timeout_s)
        return CappedProvider(live, settings.max_calls, settings.max_tokens)
    raise ValueError(f"Unknown JUDGE_PROVIDER {settings.provider!r}: use mock or openai_compatible.")
