"""MCP server exposing ticket + session tools backed by the Rails API.

Runs on stdio transport. Tools are intentionally agnostic: every operation
works the same whether the session's tickets are simulated or purchased.
"""
from __future__ import annotations

import asyncio
import json

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from src.client import TicketsClient

log = structlog.get_logger()

app: Server = Server("tickets-mcp")

_client_factory = TicketsClient

TOOLS = [
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
                    "visitor_type": {"type": "string", "enum": ["adult", "child", "senior"]},
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
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    log.info("mcp_tool_call", tool=name, args=list(arguments.keys()))
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


async def main() -> None:
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
