import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


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
    # The connection pool (Module 3 of the databases course).
    db_pool: bool = True
    db_pool_min: int = 2
    db_pool_max: int = 10
    db_pool_timeout: float = 5.0
    show_query_count: bool = False
    # Object storage for attachments (Module 5).
    storage_connection_string: str | None = field(default=None, repr=False)
    storage_container: str = "attachments"
    storage_public_url: str | None = None
    max_upload_bytes: int = 10 * 1024 * 1024
    upload_url_seconds: int = 600
    download_url_seconds: int = 300
    # The AI provider (the scaling course). Empty URL = no AI work.
    provider_url: str | None = None
    provider_api_key: str | None = field(default=None, repr=False)
    provider_timeout: float = 30.0
    # How a new ticket waits for the provider (Module 2): async, thread or blocking.
    intake_mode: str = "async"
    # The most provider calls in flight from one process (0 = no limit).
    provider_max_concurrency: int = 0
    # The shared cache (Module 3): Valkey. Empty URL = no cache.
    cache_url: str | None = field(default=None, repr=False)
    cache_timeout: float = 0.05
    cache_ttl_seconds: float = 600.0
    cache_stampede_guard: bool = True
    cache_lock_seconds: float = 10.0


def read_secret(name: str) -> str | None:
    """Return the value of NAME, or the contents of the file in NAME_FILE."""
    path = os.environ.get(f"{name}_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except OSError as error:
            raise SettingsError(f"{name}_FILE: cannot read {path}: {error.strerror}") from None
    return os.environ.get(name) or None


def load_env() -> None:
    """Read .env from the current folder. A variable that is already set wins over the file."""
    load_dotenv(Path.cwd() / ".env", override=False)


def flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).lower() == "true"


def load_settings() -> Settings:
    """Read the settings from environment variables (and .env), with safe defaults."""
    load_env()
    origins = os.environ.get("ALLOWED_ORIGINS", "")
    settings = Settings(
        api_key=read_secret("API_KEY"),
        allowed_origins=[o.strip() for o in origins.split(",") if o.strip()],
        classifier_mode=os.environ.get("CLASSIFIER_MODE", "keywords"),
        classifier_timeout=float(os.environ.get("CLASSIFIER_TIMEOUT", "2.0")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        show_docs=flag("SHOW_DOCS", "true"),
        database_url=read_secret("DATABASE_URL"),
        classifier_version=os.environ.get("CLASSIFIER_VERSION", "1.0"),
        db_pool=flag("DB_POOL", "true"),
        db_pool_min=int(os.environ.get("DB_POOL_MIN", "2")),
        db_pool_max=int(os.environ.get("DB_POOL_MAX", "10")),
        db_pool_timeout=float(os.environ.get("DB_POOL_TIMEOUT", "5")),
        show_query_count=flag("SHOW_QUERY_COUNT", "false"),
        storage_connection_string=read_secret("STORAGE_CONNECTION_STRING"),
        storage_container=os.environ.get("STORAGE_CONTAINER", "attachments"),
        storage_public_url=os.environ.get("STORAGE_PUBLIC_URL") or None,
        max_upload_bytes=int(os.environ.get("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))),
        provider_url=os.environ.get("PROVIDER_URL", "http://127.0.0.1:8300/v1") or None,
        provider_api_key=read_secret("PROVIDER_API_KEY"),
        provider_timeout=float(os.environ.get("PROVIDER_TIMEOUT", "30")),
        intake_mode=os.environ.get("INTAKE_MODE", "async"),
        provider_max_concurrency=int(os.environ.get("PROVIDER_MAX_CONCURRENCY", "0")),
        cache_url=read_secret("CACHE_URL"),
        cache_timeout=float(os.environ.get("CACHE_TIMEOUT", "0.05")),
        cache_ttl_seconds=float(os.environ.get("CACHE_TTL_SECONDS", "600")),
        cache_stampede_guard=flag("CACHE_STAMPEDE_GUARD", "true"),
        cache_lock_seconds=float(os.environ.get("CACHE_LOCK_SECONDS", "10")),
    )
    if os.environ.get("REQUIRE_API_KEY", "false").lower() == "true" and not settings.api_key:
        raise SettingsError("REQUIRE_API_KEY is true, but API_KEY is not set")
    if settings.intake_mode not in ("async", "thread", "blocking"):
        raise SettingsError("INTAKE_MODE must be async, thread or blocking")
    if settings.db_pool_min > settings.db_pool_max:
        raise SettingsError("DB_POOL_MIN is larger than DB_POOL_MAX")
    return settings
