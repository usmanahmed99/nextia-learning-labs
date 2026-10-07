import os
from dataclasses import dataclass, field
from pathlib import Path


class SettingsError(Exception):
    """A required setting is missing or not valid. The app must not start."""


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)
    allowed_origins: list[str]
    classifier_mode: str
    classifier_timeout: float
    log_level: str
    show_docs: bool
    database_url: str | None = field(default=None, repr=False)
    classifier_version: str = "1.0"


def read_secret(name: str) -> str | None:
    """Return the value of NAME, or the contents of the file in NAME_FILE."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except OSError as error:
            raise SettingsError(f"{name}_FILE: cannot read {path}: {error.strerror}") from None
    return os.environ.get(name) or None


def load_settings() -> Settings:
    """Read the settings from environment variables, with safe defaults."""
    origins = os.environ.get("ALLOWED_ORIGINS", "")
    settings = Settings(
        api_key=read_secret("API_KEY"),
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
        classifier_mode=os.environ.get("CLASSIFIER_MODE", "keywords"),
        classifier_timeout=float(os.environ.get("CLASSIFIER_TIMEOUT", "2.0")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        show_docs=os.environ.get("SHOW_DOCS", "true").lower() == "true",
        database_url=read_secret("DATABASE_URL"),
        classifier_version=os.environ.get("CLASSIFIER_VERSION", "1.0"),
    )
    if os.environ.get("REQUIRE_API_KEY", "false").lower() == "true" and not settings.api_key:
        raise SettingsError("REQUIRE_API_KEY is true, but API_KEY is not set")
    return settings
