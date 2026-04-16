"""Tests that exercise the MCP server handlers (list_tools + call_tool).

These monkeypatch ``_client_factory`` so the server creates a TicketsClient
with a mock HTTP transport instead of connecting to a real Rails API.
"""
import json
from unittest.mock import AsyncMock

import httpx
import pytest

import src.server as server_mod
from src.client import TicketsClient


def _fake_client_factory(transport: httpx.MockTransport):
    """Return a factory that builds a TicketsClient wired to *transport*."""
    def factory(**_kw):
        http = httpx.AsyncClient(transport=transport, base_url="http://api")
        return TicketsClient(base_url="http://api", api_key="k", http=http)
    return factory


@pytest.fixture(autouse=True)
def _restore_factory():
    original = server_mod._client_factory
    yield
    server_mod._client_factory = original


# ── list_tools ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tools_returns_three_tools():
    tools = await server_mod.list_tools()
    names = {t.name for t in tools}
    assert names == {"get_session_details", "create_simulated_ticket", "confirm_purchase"}


@pytest.mark.asyncio
async def test_list_tools_schemas_have_required_fields():
    tools = await server_mod.list_tools()
    for tool in tools:
        assert "type" in tool.inputSchema
        assert "properties" in tool.inputSchema
        assert "session_id" in tool.inputSchema["properties"]


# ── call_tool: get_session_details ──────────────────────

@pytest.mark.asyncio
async def test_call_get_session_details():
    session_payload = {"id": "s1", "visit_date": "2026-05-01", "tickets": []}

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v1/sessions/s1"
        return httpx.Response(200, json=session_payload)

    server_mod._client_factory = _fake_client_factory(httpx.MockTransport(handler))
    result = await server_mod.call_tool("get_session_details", {"session_id": "s1"})

    assert len(result) == 1
    assert result[0].type == "text"
    data = json.loads(result[0].text)
    assert data["id"] == "s1"
    assert data["tickets"] == []


# ── call_tool: create_simulated_ticket ──────────────────

@pytest.mark.asyncio
async def test_call_create_simulated_ticket():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v1/sessions/s1/tickets/simulated"
        body = json.loads(req.content)
        assert body["visitor_type"] == "child"
        assert body["count"] == 3
        return httpx.Response(201, json={"id": "t1", "purchased": False})

    server_mod._client_factory = _fake_client_factory(httpx.MockTransport(handler))
    result = await server_mod.call_tool(
        "create_simulated_ticket",
        {"session_id": "s1", "visitor_type": "child", "count": 3},
    )

    data = json.loads(result[0].text)
    assert data["simulated"] is True
    assert data["status"] == "created"


# ── call_tool: confirm_purchase ─────────────────────────

@pytest.mark.asyncio
async def test_call_confirm_purchase():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/api/v1/sessions/s1/confirm_purchase"
        body = json.loads(req.content)
        assert body["ticket_ids"] == ["t1"]
        assert body["payment_ref"] == "pay_abc"
        return httpx.Response(200, json={"confirmed": 1})

    server_mod._client_factory = _fake_client_factory(httpx.MockTransport(handler))
    result = await server_mod.call_tool(
        "confirm_purchase",
        {"session_id": "s1", "ticket_ids": ["t1"], "payment_ref": "pay_abc"},
    )

    data = json.loads(result[0].text)
    assert data["locked"] is True


# ── call_tool: unknown tool ─────────────────────────────

@pytest.mark.asyncio
async def test_call_unknown_tool_raises():
    server_mod._client_factory = _fake_client_factory(
        httpx.MockTransport(lambda r: httpx.Response(404))
    )
    with pytest.raises(ValueError, match="unknown tool"):
        await server_mod.call_tool("no_such_tool", {})
