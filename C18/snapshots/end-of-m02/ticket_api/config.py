import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    api_key: str | None = field(repr=False)
    allowed_origins: list[str]
    classifier_mode: str
    classifier_timeout: float
    log_level: str
    show_docs: bool


def load_settings() -> Settings:
    """Read the settings from environment variables, with safe defaults."""
    origins = os.environ.get("ALLOWED_ORIGINS", "")
    return Settings(
        api_key=os.environ.get("API_KEY") or None,
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
        classifier_mode=os.environ.get("CLASSIFIER_MODE", "keywords"),
        classifier_timeout=float(os.environ.get("CLASSIFIER_TIMEOUT", "2.0")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        show_docs=os.environ.get("SHOW_DOCS", "true").lower() == "true",
    )
