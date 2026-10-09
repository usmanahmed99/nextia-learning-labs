"""Settings from environment variables (and an optional .env file), the choice of provider, the prompt files.

The key is read here and given only to the provider. It is never printed, logged or saved.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .providers import MockProvider, OpenAICompatibleProvider

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
PROMPTS = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> tuple[str, str]:
    """prompts/NAME.md -> (system message, user message template). The file has a [system] and a [user] part."""
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    system, user = text.split("[user]\n", 1)
    return system.replace("[system]\n", "", 1).strip(), user.strip()


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
    model: str = "chat-small"         # the recordings were made with chat-small and chat-strong
    base_url: str = ""                # for example http://localhost:11434/v1 for Ollama
    api_key: str = field(default="", repr=False)   # repr=False: printing the settings never shows the key
    timeout_s: float = 60.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_env_file()
        env = os.environ
        return cls(provider=env.get("ASSISTANT_PROVIDER", "mock"), model=env.get("ASSISTANT_MODEL", "chat-small"),
                   base_url=env.get("ASSISTANT_BASE_URL", ""), api_key=env.get("ASSISTANT_API_KEY", ""),
                   timeout_s=float(env.get("ASSISTANT_TIMEOUT_S", "60")))


def make_provider(settings: Settings):
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "openai_compatible":
        if not settings.base_url:
            raise ValueError("Set ASSISTANT_BASE_URL, for example http://localhost:11434/v1 for Ollama.")
        return OpenAICompatibleProvider(settings.base_url, settings.api_key, settings.timeout_s)
    raise ValueError(f"Unknown ASSISTANT_PROVIDER {settings.provider!r}: use mock or openai_compatible.")
