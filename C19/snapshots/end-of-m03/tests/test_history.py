from datetime import datetime, timezone

import pytest

from ticket_api.config import SettingsError, load_settings
from ticket_api.history import HistoryUnavailable


class FakeHistory:
    """Keeps the history in a list, so the tests need no database."""

    def __init__(self, down=False):
        self.rows = []
        self.down = down

    def check(self):
        if self.down:
            raise HistoryUnavailable("down")

    def add(self, request_id, result):
        self.check()
        created_at = datetime.now(timezone.utc)
        self.rows.append({"request_id": request_id, **result, "created_at": created_at})

    def recent(self, limit):
        self.check()
        return list(reversed(self.rows))[:limit]


@pytest.fixture
def history_client(make_client):
    def make(down=False):
        client = make_client()
        client.app.state.history = FakeHistory(down)
        return client

    return make


def test_history_is_off_without_database_url(client):
    response = client.get("/v1/history")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "history_unavailable"


def test_classification_is_recorded_without_the_text(history_client):
    client = history_client()
    response = client.post("/v1/classify", json={"subject": "Parcel lost"})
    items = client.get("/v1/history").json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "shipping"
    assert items[0]["request_id"] == response.headers["X-Request-ID"]
    assert "subject" not in items[0]


def test_history_limit(history_client):
    client = history_client()
    for _ in range(3):
        client.post("/v1/classify", json={"subject": "Refund"})
    assert len(client.get("/v1/history?limit=2").json()["items"]) == 2
    assert client.get("/v1/history?limit=0").status_code == 422


def test_database_down_still_classifies_but_is_not_ready(history_client):
    client = history_client(down=True)
    assert client.post("/v1/classify", json={"subject": "Refund"}).status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.get("/v1/history").status_code == 503


def test_api_key_from_a_file(tmp_path, monkeypatch):
    key_file = tmp_path / "api_key"
    key_file.write_text("from-a-file\n")
    monkeypatch.setenv("API_KEY_FILE", str(key_file))
    assert load_settings().api_key == "from-a-file"


def test_missing_secret_file_stops_the_app(monkeypatch):
    monkeypatch.setenv("API_KEY_FILE", "/no/such/file")
    with pytest.raises(SettingsError):
        load_settings()


def test_required_api_key(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEY_FILE", raising=False)
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    with pytest.raises(SettingsError):
        load_settings()


def test_secrets_are_not_in_the_settings_repr(monkeypatch):
    monkeypatch.setenv("API_KEY", "do-not-print")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:do-not-print@db/x")
    assert "do-not-print" not in repr(load_settings())
