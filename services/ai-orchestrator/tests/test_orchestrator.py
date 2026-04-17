import pytest

from app.agents.base import SessionContext
from app.agents.orchestrator import PavoOrchestrator
from app.llm.router import Router
from app.mcp.client import MCPClientManager


def _ctx() -> SessionContext:
    return SessionContext(
        session_id="s1",
        visit_date="2026-05-01",
        party=[{"type": "adult", "count": 2}, {"type": "child", "count": 1}],
        tickets=[],
    )


@pytest.mark.asyncio
async def test_intent_keyword_routing():
    orch = PavoOrchestrator(Router(), MCPClientManager())
    ctx = _ctx()

    assert await orch.classify_intent("Je veux acheter des billets", ctx) == "concierge"
    assert await orch.classify_intent("Planifier ma journée au parc", ctx) == "planner"
    assert await orch.classify_intent("Y a-t-il des secrets cachés ?", ctx) == "detective"


@pytest.mark.asyncio
async def test_stream_response_yields_text_and_metadata():
    orch = PavoOrchestrator(Router(), MCPClientManager())
    ctx = _ctx()

    chunks = []
    async for raw in orch.stream_response("Planifier notre visite", ctx):
        chunks.append(raw)

    joined = "".join(chunks)
    assert "data:" in joined
    assert "metadata" in joined
    assert "planner" in joined


@pytest.mark.asyncio
async def test_agent_works_without_tickets():
    orch = PavoOrchestrator(Router(), MCPClientManager())
    ctx = _ctx()
    assert ctx.tickets == []

    frames = [c async for c in orch.stream_response("On arrive à 10h", ctx)]
    assert any("stub:" in f for f in frames)
