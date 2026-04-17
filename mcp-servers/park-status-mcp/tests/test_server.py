"""Tests for the MCP server handlers (list_tools + call_tool)."""
import json

import pytest

import src.server as server_mod


@pytest.mark.asyncio
async def test_list_tools_returns_all_tools():
    tools = await server_mod.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "get_park_hours",
        "list_attractions",
        "get_attraction_status",
        "list_events",
    }


@pytest.mark.asyncio
async def test_tool_schemas_are_objects_with_properties():
    tools = await server_mod.list_tools()
    for tool in tools:
        assert tool.inputSchema["type"] == "object"
        assert "properties" in tool.inputSchema


# ── get_park_hours ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_get_park_hours_weekday():
    result = await server_mod.call_tool("get_park_hours", {"visit_date": "2026-04-21"})
    data = json.loads(result[0].text)
    assert data["opening_time"] == "11:00"
    assert data["closing_time"] == "19:00"
    assert data["is_weekend_or_holiday"] is False


@pytest.mark.asyncio
async def test_call_get_park_hours_weekend():
    result = await server_mod.call_tool("get_park_hours", {"visit_date": "2026-04-18"})
    data = json.loads(result[0].text)
    assert data["opening_time"] == "10:00"
    assert data["is_weekend_or_holiday"] is True


# ── list_attractions ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_list_attractions_all():
    result = await server_mod.call_tool("list_attractions", {})
    data = json.loads(result[0].text)
    assert len(data["attractions"]) == 10


@pytest.mark.asyncio
async def test_call_list_attractions_filtered_by_zone():
    result = await server_mod.call_tool("list_attractions", {"zone": "bois"})
    data = json.loads(result[0].text)
    ids = {a["id"] for a in data["attractions"]}
    assert ids == {"riviere_enchantee", "foret_enchantee"}


# ── get_attraction_status ────────────────────────────────────

@pytest.mark.asyncio
async def test_call_get_attraction_status_open():
    result = await server_mod.call_tool(
        "get_attraction_status",
        {"attraction_id": "grand_carrousel", "visit_date": "2026-04-21"},
    )
    data = json.loads(result[0].text)
    assert data["status"] == "open"
    assert data["name_fr"] == "Le Grand Carrousel 1900"
    assert data["current_wait_min"] >= 0


@pytest.mark.asyncio
async def test_call_get_attraction_status_maintenance():
    result = await server_mod.call_tool(
        "get_attraction_status",
        {"attraction_id": "dragon_chinois", "visit_date": "2026-04-20"},
    )
    data = json.loads(result[0].text)
    assert data["status"] == "maintenance"


@pytest.mark.asyncio
async def test_call_get_attraction_status_unknown_raises():
    with pytest.raises(KeyError):
        await server_mod.call_tool(
            "get_attraction_status",
            {"attraction_id": "nope", "visit_date": "2026-04-21"},
        )


# ── list_events ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_list_events_weekday():
    result = await server_mod.call_tool("list_events", {"visit_date": "2026-04-21"})
    data = json.loads(result[0].text)
    ids = {e["id"] for e in data["events"]}
    assert "parade_animaux" in ids
    assert "concert_jardin_dimanche" not in ids


@pytest.mark.asyncio
async def test_call_list_events_weekend_includes_concert():
    result = await server_mod.call_tool("list_events", {"visit_date": "2026-04-18"})
    data = json.loads(result[0].text)
    ids = {e["id"] for e in data["events"]}
    assert "concert_jardin_dimanche" in ids


# ── unknown tool ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_unknown_tool_raises():
    with pytest.raises(ValueError, match="unknown tool"):
        await server_mod.call_tool("not_a_tool", {})
