import os
from dataclasses import fields, replace

import psycopg
import pytest
from fakes import fake_provider
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from ticket_api.config import Settings, load_env
from ticket_api.main import create_app

TEST_SETTINGS = Settings(
    api_key=None,
    allowed_origins=[],
    classifier_mode="keywords",
    classifier_timeout=2.0,
    log_level="WARNING",
    show_docs=True,
)


@pytest.fixture
def make_client():
    """Return a function that makes a test client with changed settings."""

    def make(**changes) -> TestClient:
        app = create_app(replace(TEST_SETTINGS, **changes))
        return TestClient(app, raise_server_exceptions=False)

    return make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


# ---------- a real PostgreSQL database for the tests ----------
# The tests use their own database (TEST_DATABASE_URL, whose name must end in
# _test) and delete everything in it. A template database with the migrations
# and the small data is made once per run; each test gets a fresh copy of it.

load_env()
TEST_URL = os.environ.get("TEST_DATABASE_URL")


def _parts(url: str) -> tuple[str, str]:
    base, name = url.rsplit("/", 1)
    return base, name.split("?")[0]


def _admin(url: str) -> psycopg.Connection:
    base, _ = _parts(url)
    return psycopg.connect(f"{base}/postgres", autocommit=True, connect_timeout=3)


@pytest.fixture(scope="session")
def test_url() -> str:
    if not TEST_URL:
        pytest.skip("TEST_DATABASE_URL is not set (see .env.example)")
    _, name = _parts(TEST_URL)
    if not name.endswith("_test"):
        pytest.exit(
            f"TEST_DATABASE_URL names the database {name!r}. Its name must end in _test, "
            "because the tests delete everything in it."
        )
    try:
        _admin(TEST_URL).close()
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not running (with Docker: docker compose up -d db)")
    return TEST_URL


def _recreate(url: str, template: str | None = None) -> None:
    _, name = _parts(url)
    with _admin(url) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {name}" + (f" TEMPLATE {template}" if template else ""))


@pytest.fixture(scope="session")
def template_name(test_url):
    """A database with every migration and the small data (made once per run)."""
    from scripts import load

    base, name = _parts(test_url)
    template = f"{name}_template"
    _recreate(f"{base}/{template}")
    load.load(f"{base}/{template}", "small", quiet=True, files=False)
    yield template
    with _admin(test_url) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {template} WITH (FORCE)")


@pytest.fixture
def db_url(test_url, template_name) -> str:
    """A fresh copy of the small data, for one test."""
    _recreate(test_url, template_name)
    return test_url


@pytest.fixture
def empty_db_url(test_url) -> str:
    """An empty database, for one test."""
    _recreate(test_url)
    return test_url


@pytest.fixture
def conn(db_url):
    with psycopg.connect(db_url, autocommit=True, row_factory=dict_row) as c:
        yield c


@pytest.fixture
def make_api(db_url, tmp_path):
    """Return a function that makes a test client on the small data. The client opens the
    connection pool at the start and closes it at the end, as the real app does.
    provider=fake_provider(...) gives the app a fake AI provider (tests/fakes.py)."""
    clients = []

    def make(provider=None, **changes) -> TestClient:
        wanted = {"database_url": db_url, "show_query_count": True, **changes}
        known = {f.name for f in fields(Settings)}  # the settings of this stage of the project
        settings = replace(TEST_SETTINGS, **{k: v for k, v in wanted.items() if k in known})
        app = create_app(settings, provider=provider or fake_provider())
        c = TestClient(app, raise_server_exceptions=False)
        c.__enter__()
        clients.append(c)
        return c

    yield make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def api(make_api) -> TestClient:
    return make_api()


# ---------- the shared cache (Valkey) for the tests ----------

TEST_CACHE_URL = os.environ.get("TEST_CACHE_URL")


@pytest.fixture
def cache_url() -> str:
    """An empty cache database (TEST_CACHE_URL, database 15 by default), for one test."""
    import redis

    if not TEST_CACHE_URL:
        pytest.skip("TEST_CACHE_URL is not set (see .env.example)")
    try:
        client = redis.Redis.from_url(TEST_CACHE_URL, socket_connect_timeout=1)
        client.flushdb()
        client.close()
    except redis.RedisError:
        pytest.skip("Valkey is not running (with Docker: docker compose up -d cache)")
    return TEST_CACHE_URL
