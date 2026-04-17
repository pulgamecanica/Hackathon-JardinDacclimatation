"""MCP server exposing park-status tools over stdio.

All data is served from `src.fixtures` (in-memory, no DB). The server
is read-only: it never mutates state.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date as Date

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.fixtures import (
    get_attraction,
    get_attraction_status,
    get_park_hours,
    list_attractions,
    list_events,
)

log = structlog.get_logger()

app: Server = Server("park-status-mcp")


_ZONE_ENUM = ["ferme", "centrale", "bois", "sensations", "tour", "spectacle", "atelier"]


TOOLS = [
    Tool(
        name="get_park_hours",
        description=(
            "Return the park's opening hours for a given date. "
            "Weekend and public-holiday hours are extended (10:00–20:00); "
            "weekdays are 11:00–19:00. Last entry is always one hour before closing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
            },
            "required": ["visit_date"],
        },
    ),
    Tool(
        name="list_attractions",
        description=(
            "List the park's attractions with their operational metadata "
            "(zone, minimum height, minimum age, thrill level, average wait, "
            "wheelchair accessibility). Optionally filter by zone."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "zone": {"type": "string", "enum": _ZONE_ENUM},
            },
        },
    ),
    Tool(
        name="get_attraction_status",
        description=(
            "Return the live status of one attraction on a given date: "
            "open/maintenance/closed and an estimated current wait time. "
            "Wait times are deterministic per (attraction, date)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "attraction_id": {"type": "string"},
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
            },
            "required": ["attraction_id", "visit_date"],
        },
    ),
    Tool(
        name="list_events",
        description=(
            "Return the events, shows, and ateliers programmed on a given date. "
            "Some events run only weekends/holidays."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
            },
            "required": ["visit_date"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("mcp_tool_call", tool=name, args=list(arguments.keys()))

    if name == "get_park_hours":
        visit_date = _parse_date(arguments["visit_date"])
        payload = get_park_hours(visit_date).to_dict()
        return [TextContent(type="text", text=json.dumps(payload))]

    if name == "list_attractions":
        zone = arguments.get("zone")
        attractions = list_attractions(zone)
        payload = {"attractions": [a.to_dict() for a in attractions]}
        return [TextContent(type="text", text=json.dumps(payload))]

    if name == "get_attraction_status":
        visit_date = _parse_date(arguments["visit_date"])
        attraction = get_attraction(arguments["attraction_id"])
        status = get_attraction_status(attraction.id, visit_date)
        payload = {
            **status.to_dict(),
            "name_fr": attraction.name_fr,
            "avg_wait_min": attraction.avg_wait_min,
        }
        return [TextContent(type="text", text=json.dumps(payload))]

    if name == "list_events":
        visit_date = _parse_date(arguments["visit_date"])
        events = list_events(visit_date)
        payload = {
            "date": visit_date.isoformat(),
            "events": [e.to_dict(visit_date) for e in events],
        }
        return [TextContent(type="text", text=json.dumps(payload))]

    raise ValueError(f"unknown tool: {name}")


def _parse_date(iso: str) -> Date:
    return Date.fromisoformat(iso)


async def main() -> None:
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
