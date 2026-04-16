import json

import httpx
import pytest

from src.client import TicketsClient


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_session_details_hits_correct_path():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET"
        assert req.url.path == "/api/v1/sessions/abc"
        assert req.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"id": "abc", "tickets": []})

    async with httpx.AsyncClient(transport=_mock_transport(handler), base_url="http://api") as http:
        client = TicketsClient(base_url="http://api", api_key="test-key", http=http)
        data = await client.get_session_details("abc")
        assert data == {"id": "abc", "tickets": []}


@pytest.mark.asyncio
async def test_create_simulated_ticket_sends_payload():
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        assert req.url.path == "/api/v1/sessions/s1/tickets/simulated"
        captured["body"] = json.loads(req.content)
        return httpx.Response(201, json={"id": "t1", "purchased": False})

    async with httpx.AsyncClient(transport=_mock_transport(handler), base_url="http://api") as http:
        client = TicketsClient(base_url="http://api", api_key="k", http=http)
        out = await client.create_simulated_ticket("s1", "adult", count=2)

    assert captured["body"] == {"visitor_type": "adult", "count": 2}
    assert out["simulated"] is True
    assert out["status"] == "created"


@pytest.mark.asyncio
async def test_confirm_purchase_locks_tickets():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v1/sessions/s1/confirm_purchase"
        body = json.loads(req.content)
        assert body["ticket_ids"] == ["t1", "t2"]
        assert body["payment_ref"] == "pay_123"
        return httpx.Response(200, json={"confirmed": 2})

    async with httpx.AsyncClient(transport=_mock_transport(handler), base_url="http://api") as http:
        client = TicketsClient(base_url="http://api", api_key="k", http=http)
        out = await client.confirm_purchase("s1", ["t1", "t2"], "pay_123")

    assert out["locked"] is True
    assert out["status"] == "confirmed"
