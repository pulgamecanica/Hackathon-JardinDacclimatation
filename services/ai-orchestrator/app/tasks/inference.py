"""Async inference tasks. Use for non-streaming chat and retries."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.agents.base import SessionContext
from app.config.settings import get_settings

log = structlog.get_logger()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_chat_async(self, session_id: str, message: str, context: dict[str, Any]):
    """Non-streaming chat path. Runs inference, then calls back to Rails
    to persist the assistant reply."""
    log.info("chat_task_started", task_id=self.request.id, session_id=session_id)

    try:
        orchestrator = _build_orchestrator()
        ctx = SessionContext(session_id=session_id, **_filter_ctx(context))
        result = asyncio.run(_collect(orchestrator.stream_response(message, ctx)))
        _post_reply_to_rails(
            session_id,
            result["response"],
            result["agent_used"],
            suggestions=result["suggestions"],
        )
        return result

    except Exception as exc:
        log.error("chat_task_failed", task_id=self.request.id, error=str(exc))
        if self.request.retries < 3:
            raise self.retry(exc=exc)
        _post_reply_to_rails(
            session_id,
            "Désolé, une erreur est survenue. Veuillez réessayer.",
            "error",
        )
        raise MaxRetriesExceededError(f"Failed after 3 retries: {exc}")


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_greeting_async(self, session_id: str, context: dict[str, Any]):
    """Proactive greeting after the visitor finishes the form.

    Same callback path as `process_chat_async`: the orchestrator generates
    a welcome message and POSTs it to Rails as an assistant chat_message.
    The frontend's existing polling picks it up — no new plumbing needed."""
    log.info("greeting_task_started", task_id=self.request.id, session_id=session_id)

    try:
        orchestrator = _build_orchestrator()
        ctx = SessionContext(session_id=session_id, **_filter_ctx(context))
        result = asyncio.run(_collect(orchestrator.greet(ctx)))
        _post_reply_to_rails(
            session_id,
            result["response"],
            result["agent_used"],
            suggestions=result["suggestions"],
        )
        return result

    except Exception as exc:
        log.error("greeting_task_failed", task_id=self.request.id, error=str(exc))
        if self.request.retries < 2:
            raise self.retry(exc=exc)
        # Greeting failure is non-fatal — skip the welcome rather than
        # leaving the user with an error message.
        log.warning("greeting_skipped", session_id=session_id)
        raise MaxRetriesExceededError(f"Greeting failed after 2 retries: {exc}")


def _build_orchestrator():
    from app.agents.orchestrator import PavoOrchestrator
    from app.llm.router import Router
    from app.mcp.client import MCPClientManager

    return PavoOrchestrator(Router(), MCPClientManager())


def _filter_ctx(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"visit_date", "party", "tickets", "history", "preferences", "group_id", "media"}
    return {k: v for k, v in raw.items() if k in allowed}


async def _collect(stream) -> dict[str, Any]:
    text_parts: list[str] = []
    agent = "unknown"
    suggestions: list[str] = []
    async for raw_chunk in stream:
        payload = raw_chunk.removeprefix("data: ").strip()
        if not payload:
            continue

        chunk = json.loads(payload)
        ctype = chunk.get("type")
        if ctype == "text":
            text_parts.append(chunk.get("content", ""))
        elif ctype == "suggestions":
            suggestions = list(chunk.get("items") or [])
        elif ctype == "metadata":
            agent = chunk.get("agent", "unknown")

    return {
        "response": "".join(text_parts),
        "agent_used": agent,
        "suggestions": suggestions,
    }


def _post_reply_to_rails(
    session_id: str,
    content: str,
    agent: str,
    *,
    suggestions: list[str] | None = None,
) -> None:
    """POST the assistant reply to Rails so it's persisted as a ChatMessage."""
    settings = get_settings()
    url = f"{settings.rails_api_url}/api/v1/sessions/{session_id}/chat_messages/ai_reply"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.internal_api_key:
        headers["Authorization"] = f"Bearer {settings.internal_api_key}"

    body: dict[str, Any] = {"content": content, "agent": agent}
    if suggestions:
        body["suggestions"] = suggestions

    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=10.0)
        resp.raise_for_status()
        log.info("reply_posted_to_rails", session_id=session_id, status=resp.status_code)
    except Exception as exc:
        log.error("reply_post_failed", session_id=session_id, error=str(exc))
