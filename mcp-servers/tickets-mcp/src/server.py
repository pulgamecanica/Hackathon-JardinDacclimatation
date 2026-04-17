"""MCP server exposing ticket + session + catalog tools.

Runs on stdio transport. Session tools proxy the Rails API; catalog tools
read the in-process catalog module. All operations are agnostic to
whether tickets are simulated or purchased.
"""
from __future__ import annotations

import asyncio
import json
from datetime import date as Date

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.catalog import (
    build_pack_offer,
    get_item,
    item_to_dict,
    list_items,
)
from src.client import TicketsClient

log = structlog.get_logger()

app: Server = Server("tickets-mcp")

_client_factory = TicketsClient

_CATEGORY_ENUM = [
    "park_entry",
    "admission",
    "attraction_unit",
    "attraction_bundle",
    "rental",
]

TOOLS = [
    # ── Rails-backed session tools ─────────────────────────────
    Tool(
        name="get_session_details",
        description="Fetch a visit session with its tickets (simulated or purchased).",
        inputSchema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    ),
    Tool(
        name="create_simulated_ticket",
        description="Create a draft ticket (purchased=false). Safe to call for planning.",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "visitor_type": {"type": "string", "enum": ["adult", "small_child", "child", "teen"]},
                "count": {"type": "integer", "minimum": 1, "default": 1},
                "date": {"type": "string", "description": "ISO date (optional)"},
            },
            "required": ["session_id", "visitor_type"],
        },
    ),
    Tool(
        name="confirm_purchase",
        description="Convert simulated tickets to purchased (IRREVERSIBLE).",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
                "payment_ref": {"type": "string"},
            },
            "required": ["session_id", "ticket_ids", "payment_ref"],
        },
    ),
    # ── Catalog / pricing tools (local, no network) ────────────
    Tool(
        name="list_ticket_catalog",
        description=(
            "Return the full ticket catalog, optionally filtered by category. "
            "Prices are resolved for `visit_date` when provided (bundle prices "
            "differ between weekdays and weekends/holidays)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": _CATEGORY_ENUM},
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
            },
        },
    ),
    Tool(
        name="quote_ticket",
        description=(
            "Quote the price of a single catalog item on a given date. "
            "Use this before building pack offers so the agent never invents a price."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "catalog_id": {"type": "string"},
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
                "quantity": {"type": "integer", "minimum": 1, "default": 1},
            },
            "required": ["catalog_id", "visit_date"],
        },
    ),
    Tool(
        name="create_pack_offer",
        description=(
            "Assemble a named pack offer from catalog items. The server computes "
            "per-line and total prices from the catalog — the agent only chooses "
            "which items to include and names the pack. The offer is NOT persisted; "
            "the caller surfaces it to the user and, if accepted, materializes it "
            "into simulated tickets via `create_simulated_ticket`."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "visit_date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "catalog_id": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1, "default": 1},
                        },
                        "required": ["catalog_id"],
                    },
                    "minItems": 1,
                },
                "recommended": {"type": "boolean", "default": False},
                "highlight_features": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "description", "visit_date", "items"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("mcp_tool_call", tool=name, args=list(arguments.keys()))

    # Catalog / pricing tools — no Rails round-trip needed.
    if name == "list_ticket_catalog":
        visit_date = _parse_date(arguments.get("visit_date")) if arguments.get("visit_date") else None
        items = list_items(arguments.get("category"))
        payload = {"items": [item_to_dict(i, visit_date) for i in items]}
        return [TextContent(type="text", text=json.dumps(payload))]

    if name == "quote_ticket":
        visit_date = _parse_date(arguments["visit_date"])
        item = get_item(arguments["catalog_id"])
        qty = int(arguments.get("quantity", 1))
        unit = item.price_for_date(visit_date)
        payload = {
            "catalog_id": item.id,
            "visit_date": visit_date.isoformat(),
            "quantity": qty,
            "unit_price_eur": round(unit, 2),
            "total_eur": round(unit * qty, 2),
        }
        return [TextContent(type="text", text=json.dumps(payload))]

    if name == "create_pack_offer":
        visit_date = _parse_date(arguments["visit_date"])
        offer = build_pack_offer(
            name=arguments["name"],
            description=arguments["description"],
            items=arguments["items"],
            visit_date=visit_date,
            recommended=bool(arguments.get("recommended", False)),
            highlight_features=arguments.get("highlight_features") or [],
        )
        return [TextContent(type="text", text=json.dumps(offer.to_dict()))]

    # Rails-backed tools.
    async with _client_factory() as client:
        if name == "get_session_details":
            data = await client.get_session_details(arguments["session_id"])
        elif name == "create_simulated_ticket":
            data = await client.create_simulated_ticket(
                session_id=arguments["session_id"],
                visitor_type=arguments["visitor_type"],
                count=int(arguments.get("count", 1)),
                date=arguments.get("date"),
            )
        elif name == "confirm_purchase":
            data = await client.confirm_purchase(
                session_id=arguments["session_id"],
                ticket_ids=list(arguments["ticket_ids"]),
                payment_ref=arguments["payment_ref"],
            )
        else:
            raise ValueError(f"unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(data))]


def _parse_date(iso: str) -> Date:
    return Date.fromisoformat(iso)


async def main() -> None:
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
