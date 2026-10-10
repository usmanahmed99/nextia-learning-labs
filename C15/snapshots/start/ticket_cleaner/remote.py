import httpx


def fetch_rows(
    url: str, token: str | None = None, client: httpx.Client | None = None
) -> list[dict]:
    """Download raw records as JSON from a ticket service."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    client = client or httpx.Client(timeout=10.0)
    with client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
