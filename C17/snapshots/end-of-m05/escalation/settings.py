"""Settings from environment variables. A wrong setting stops the service at start."""

import os
from dataclasses import dataclass, field
from pathlib import Path


class SettingsError(Exception):
    """A required setting is missing or not valid. The service must not start."""


@dataclass(frozen=True)
class Settings:
    model_bundle: Path
    model_sha256: str
    shadow_bundle: Path | None
    shadow_sha256: str | None
    api_key: str | None = field(repr=False)
    log_level: str = "INFO"
    show_docs: bool = True
    max_job_tickets: int = 5000
    max_queued_jobs: int = 4
    extra_ms_per_ticket: float = 0.0


def read_secret(name: str) -> str | None:
    """Return the value of NAME, or the contents of the file in NAME_FILE."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except OSError as error:
            raise SettingsError(f"{name}_FILE: cannot read {path}: {error.strerror}")
    return os.environ.get(name) or None


def load_settings() -> Settings:
    env = os.environ
    sha = env.get("MODEL_SHA256", "").strip().lower()
    if len(sha) != 64:
        raise SettingsError("MODEL_SHA256 must be the 64-character digest of the bundle")
    shadow = env.get("SHADOW_BUNDLE") or None
    shadow_sha = env.get("SHADOW_SHA256", "").strip().lower() or None
    if shadow and (shadow_sha is None or len(shadow_sha) != 64):
        raise SettingsError("SHADOW_BUNDLE is set, so SHADOW_SHA256 must be its digest")
    settings = Settings(
        model_bundle=Path(env.get("MODEL_BUNDLE", "bundles/escalation-1.0.0")),
        model_sha256=sha,
        shadow_bundle=Path(shadow) if shadow else None,
        shadow_sha256=shadow_sha,
        api_key=read_secret("API_KEY"),
        log_level=env.get("LOG_LEVEL", "INFO").upper(),
        show_docs=env.get("SHOW_DOCS", "true").lower() == "true",
        max_job_tickets=int(env.get("MAX_JOB_TICKETS", "5000")),
        max_queued_jobs=int(env.get("MAX_QUEUED_JOBS", "4")),
        extra_ms_per_ticket=float(env.get("EXTRA_MS_PER_TICKET", "0")),
    )
    if env.get("REQUIRE_API_KEY", "false").lower() == "true" and not settings.api_key:
        raise SettingsError("REQUIRE_API_KEY is true, but API_KEY is not set")
    return settings
