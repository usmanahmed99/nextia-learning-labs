import os
from dataclasses import dataclass, field

DEFAULT_URL = "https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C02/data/tickets.json"


@dataclass(frozen=True)
class Settings:
    tickets_url: str
    api_token: str | None = field(repr=False)
    log_level: str


def load_settings() -> Settings:
    """Read the settings from environment variables, with safe defaults."""
    return Settings(
        tickets_url=os.environ.get("TICKETS_URL", DEFAULT_URL),
        api_token=os.environ.get("TICKETS_API_TOKEN") or None,
        log_level=os.environ.get("LOG_LEVEL", "WARNING").upper(),
    )
