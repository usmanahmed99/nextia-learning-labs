import os
from dataclasses import fields, replace

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from idp.app import create_app as create_provider
from idp.store import Store
from idp.tokens import Signer
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


# ---------- the practice identity provider, in the test process ----------
# The provider runs as a test client (no server, no port). The API fetches its discovery
# document and its keys through that client instead of over the network.

ISSUER = "http://localhost:8400"
ALL_SCOPES = "tickets:read tickets:write members:manage"


@pytest.fixture(scope="session")
def idp_store(tmp_path_factory) -> Store:
    store = Store(tmp_path_factory.mktemp("idp"))
    store.secrets = store.init()  # the client secrets, for the API's settings
    return store


@pytest.fixture
def provider(idp_store) -> TestClient:
    return TestClient(create_provider(idp_store, issuer=ISSUER), raise_server_exceptions=False)


@pytest.fixture
def signer(idp_store) -> Signer:
    return Signer(idp_store, ISSUER)


@pytest.fixture
def token_for(signer):
    """token_for("usr-sam") -> an access token from the provider, as after a sign-in."""

    def make(user: str, scope: str = ALL_SCOPES, client_id: str = "help-desk-web", **claims):
        return signer.access_token(user, client_id, scope, **claims)

    return make


@pytest.fixture
def as_user(token_for):
    """as_user("usr-sam") -> the request headers of Sam's access token."""

    def make(user: str, scope: str = ALL_SCOPES) -> dict:
        return {"Authorization": f"Bearer {token_for(user, scope)}"}

    return make


def connect_provider(app, provider: TestClient) -> None:
    """Make the app's token validator fetch the provider's documents from the test client."""
    validator = getattr(app.state, "validator", None)
    if validator is not None:
        validator.provider.fetch = lambda url: provider.get(url.removeprefix(ISSUER)).json()

        def post(url, data, auth=None):
            r = provider.post(url.removeprefix(ISSUER), data=data, auth=auth)
            return r.status_code, r.json()

        validator.provider.post = post


@pytest.fixture
def make_api(db_url, tmp_path, provider, idp_store):
    """Return a function that makes a test client on the small data. The client opens the
    connection pool at the start and closes it at the end, as the real app does."""
    clients = []

    def make(**changes) -> TestClient:
        wanted = {
            "database_url": db_url,
            "show_query_count": True,
            "oidc_issuer": ISSUER,
            "oidc_client_secret": idp_store.secrets["help-desk-web"],
            "session_cookie_secure": False,  # the test client talks plain HTTP
            **changes,
        }
        known = {f.name for f in fields(Settings)}  # the settings of this stage of the project
        settings = replace(TEST_SETTINGS, **{k: v for k, v in wanted.items() if k in known})
        app = create_app(settings)
        connect_provider(app, provider)
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
