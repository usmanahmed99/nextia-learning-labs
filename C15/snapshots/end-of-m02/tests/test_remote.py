import httpx
import pytest

from ticket_cleaner.remote import fetch_rows

URL = "https://tickets.example/api/tickets"


def answer_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=[{"id": "T-2001", "status": "open"}])


def answer_unavailable(request: httpx.Request) -> httpx.Response:
    return httpx.Response(503, text="Service Unavailable")


def test_fetch_rows_returns_the_records():
    client = httpx.Client(transport=httpx.MockTransport(answer_ok))
    assert fetch_rows(URL, client=client) == [{"id": "T-2001", "status": "open"}]


def test_fetch_rows_raises_on_server_error():
    client = httpx.Client(transport=httpx.MockTransport(answer_unavailable))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_rows(URL, client=client)
