import json
from pathlib import Path

CONTRACT = Path(__file__).parent.parent / "contract" / "openapi.json"


def test_openapi_matches_the_reviewed_contract(client):
    current = json.dumps(client.get("/openapi.json").json(), indent=2) + "\n"
    reviewed = CONTRACT.read_text(encoding="utf-8")
    assert current == reviewed, (
        "The API contract changed. If the change is intended, run "
        "python -m ticket_api.export_contract and review the difference."
    )


def test_documented_example_gives_the_documented_result(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    request_example = schemas["TicketIn"]["examples"][0]
    response_example = schemas["Classification"]["examples"][0]
    response = client.post("/v1/classify", json=request_example)
    assert response.status_code == 200
    assert response.json() == response_example
