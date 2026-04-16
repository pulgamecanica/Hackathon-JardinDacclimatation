"""Async inference tasks. Use for non-streaming chat and retries."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.agents.base import SessionContext

log = structlog.get_logger()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_chat_async(self, session_id: str, message: str, context: dict[str, Any]):
    """Non-streaming chat path. Returns the final assistant reply."""
    log.info("chat_task_started", task_id=self.request.id, session_id=session_id)

    try:
        # Import lazily — the orchestrator lives in the API process, not the worker,
        # but the classes are importable everywhere.
        from app.agents.orchestrator import PlumeOrchestrator
        from app.llm.router import Router
        from app.mcp.client import MCPClientManager

        # Workers get a fresh router + an empty MCP manager (tool calls are
        # exercised by the streaming path that runs in-process). For heavy
        # tool use we'd want a shared manager — out of scope here.
        orchestrator = PlumeOrchestrator(Router(), MCPClientManager())

        ctx = SessionContext(session_id=session_id, **_filter_ctx(context))
        return asyncio.run(_collect(orchestrator, message, ctx))

    except Exception as exc:
        log.error("chat_task_failed", task_id=self.request.id, error=str(exc))
        if self.request.retries < 3:
            raise self.retry(exc=exc)
        raise MaxRetriesExceededError(f"Failed after 3 retries: {exc}")


def _filter_ctx(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"visit_date", "party", "tickets", "history", "preferences", "group_id", "media"}
    return {k: v for k, v in raw.items() if k in allowed}


async def _collect(orchestrator, message: str, ctx: SessionContext) -> dict[str, Any]:
    text_parts: list[str] = []
    agent = "unknown"
    async for raw_chunk in orchestrator.stream_response(message, ctx):
        # stream_response yields "data: {...}\n\n" — parse the JSON payload.
        payload = raw_chunk.removeprefix("data: ").strip()
        if not payload:
            continue
        import json

        chunk = json.loads(payload)
        if chunk.get("type") == "text":
            text_parts.append(chunk.get("content", ""))
        elif chunk.get("type") == "metadata":
            agent = chunk.get("agent", "unknown")

    return {
        "response": "".join(text_parts),
        "agent_used": agent,
    }
