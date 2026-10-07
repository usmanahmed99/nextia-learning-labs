import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_billing_ticket(client):
    response = client.post(
        "/v1/classify",
        json={"subject": "Charged twice for March", "body": "Same invoice."},
    )
    assert response.status_code == 200
    assert response.json() == {
        "category": "billing",
        "priority": 1,
        "confidence": 0.9,
        "model_version": "keywords-1.0",
    }


@pytest.mark.parametrize("subject", ["x", "x" * 120])
def test_subject_length_limits_are_accepted(client, subject):
    assert client.post("/v1/classify", json={"subject": subject}).status_code == 200


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"subject": ""}, "subject"),
        ({"subject": "x" * 121}, "subject"),
        ({"body": "no subject"}, "subject"),
        ({"subject": "Hi", "colour": "red"}, "colour"),
    ],
)
def test_invalid_payload_names_the_field(client, payload, field):
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert field in response.json()["error"]["fields"]


def test_malformed_json(client):
    response = client.post(
        "/v1/classify",
        content='{"subject": "x"',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["body"]


def test_unavailable_classifier_gives_503(make_client):
    client = make_client(classifier_mode="unavailable")
    response = client.post("/v1/classify", json={"subject": "Refund"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "classifier_unavailable"
    assert "Traceback" not in response.text


def test_every_response_has_a_request_id(client):
    ok = client.get("/health")
    error = client.post("/v1/classify", json={"subject": ""})
    assert len(ok.headers["X-Request-ID"]) == 12
    assert error.json()["error"]["request_id"] == error.headers["X-Request-ID"]


def test_body_too_large(client):
    response = client.post("/v1/classify", json={"subject": "x", "body": "a" * 20_000})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "body_too_large"


def test_slow_classifier_times_out(make_client):
    client = make_client(classifier_mode="slow", classifier_timeout=0.1)
    response = client.post("/v1/classify", json={"subject": "Refund"})
    assert response.status_code == 503


def test_api_key_is_required_when_set(make_client):
    client = make_client(api_key="test-key")
    assert client.post("/v1/classify", json={"subject": "x"}).status_code == 401
    response = client.post(
        "/v1/classify", json={"subject": "x"}, headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200


def test_ready_and_not_ready(make_client):
    assert make_client().get("/ready").status_code == 200
    not_ready = make_client(classifier_mode="unavailable").get("/ready")
    assert not_ready.status_code == 503
