import time


def test_score_one_ticket(client, ticket):
    response = client.post("/v1/score", json=ticket)
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "1.0.0"
    assert 0 <= body["score"] <= 1
    assert body["flag"] == (body["score"] >= body["threshold"])
    assert "model;dur=" in response.headers["Server-Timing"]


def test_a_contract_error_has_the_error_shape(client, ticket):
    response = client.post("/v1/score", json={**ticket, "priority": "high", "created_hour": 24})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_ticket"
    assert error["fields"] == ["created_hour", "priority"]
    assert client.get("/v1/monitor").json()["contract_errors"] == {"created_hour": 1, "priority": 1}


def test_an_unknown_category_is_scored_with_a_warning(client, ticket):
    body = client.post("/v1/score", json={**ticket, "channel": "social"}).json()
    assert body["warnings"] == ["channel: 'social' is a value the model never saw"]
    assert client.get("/v1/monitor").json()["unknown_categories"] == {"channel": 1}


def test_the_model_endpoint_names_the_bundle(client):
    body = client.get("/v1/model").json()
    assert body["model_version"] == "1.0.0"
    assert len(body["bundle_sha256"]) == 64


def test_ready_names_the_model(client):
    assert client.get("/ready").json() == {"status": "ready", "model_version": "1.0.0"}


def test_a_job_is_accepted_then_done(client, ticket):
    response = client.post("/v1/jobs", json={"tickets": [ticket] * 3})
    assert response.status_code == 202
    location = response.headers["Location"]
    for _ in range(50):
        body = client.get(location).json()
        if body["status"] == "done":
            break
        time.sleep(0.02)
    assert body["status"] == "done"
    assert len(body["results"]) == 3


def test_an_unknown_job_is_404(client):
    assert client.get("/v1/jobs/nothere").json()["error"]["code"] == "job_not_found"


def test_a_key_is_required_when_set(monkeypatch, ticket):
    from fastapi.testclient import TestClient

    from escalation.main import create_app

    monkeypatch.setenv("API_KEY", "test-key")
    with TestClient(create_app()) as client:
        assert client.post("/v1/score", json=ticket).status_code == 401
        assert client.post("/v1/score", json=ticket, headers={"X-API-Key": "test-key"}).status_code == 200
