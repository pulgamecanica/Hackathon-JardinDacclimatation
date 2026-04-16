"""Thin MCP client manager.

Wraps the official `mcp` SDK so the rest of the app can ask for tools and
call them without knowing about transport details. Tool descriptions are
exposed in a provider-agnostic shape — agents format them into prompts or
wrap them as LlamaIndex FunctionTools themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class ToolSpec:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    url: str | None = None  # for http transport


class MCPClientManager:
    """Manages connections to one or more MCP servers."""

    def __init__(self) -> None:
        self._sessions: dict[str, Any] = {}
        self._tools: dict[str, list[ToolSpec]] = {}
        self._connected = False

    async def connect_all(self, configs: list[MCPServerConfig]) -> None:
        """Open a session per configured server and cache tool lists.

        The real implementation uses `mcp.ClientSession` + stdio/http
        transports; for unit tests we monkeypatch this whole manager.
        """
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        for cfg in configs:
            if cfg.transport != "stdio":
                log.warning("mcp_unsupported_transport", name=cfg.name, transport=cfg.transport)
                continue
            params = StdioServerParameters(command=cfg.command or "python", args=cfg.args)
            # Open and immediately initialize the session. The streams stay
            # alive via the cached context manager exit — we stash the cm.
            cm = stdio_client(params)
            read, write = await cm.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()

            tool_list = await session.list_tools()
            self._sessions[cfg.name] = (session, cm)
            self._tools[cfg.name] = [
                ToolSpec(
                    server=cfg.name,
                    name=t.name,
                    description=t.description or "",
                    input_schema=t.inputSchema or {},
                )
                for t in tool_list.tools
            ]
            log.info("mcp_connected", server=cfg.name, tool_count=len(self._tools[cfg.name]))

        self._connected = True

    async def disconnect_all(self) -> None:
        for name, (session, cm) in list(self._sessions.items()):
            try:
                await session.__aexit__(None, None, None)
                await cm.__aexit__(None, None, None)
            except Exception as e:  # pragma: no cover - best effort
                log.warning("mcp_disconnect_error", server=name, error=str(e))
        self._sessions.clear()
        self._tools.clear()
        self._connected = False

    def list_all_tools(self) -> list[ToolSpec]:
        out: list[ToolSpec] = []
        for tools in self._tools.values():
            out.extend(tools)
        return out

    async def call_tool(self, server: str, name: str, arguments: dict[str, Any]) -> str:
        if server not in self._sessions:
            raise KeyError(f"MCP server not connected: {server}")
        session, _ = self._sessions[server]
        result = await session.call_tool(name, arguments)
        # Collect text content blocks; binary content is ignored here.
        text_parts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
        return "\n".join(text_parts)

    @property
    def connected(self) -> bool:
        return self._connected
