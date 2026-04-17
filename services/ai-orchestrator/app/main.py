"""FastAPI entry point.

Endpoints:
  GET  /health
  POST /chat                 — streaming chat (SSE)
  POST /chat/async           — enqueue via Celery (non-streaming)
  POST /media/upload         — multipart upload; returns media summary
  GET  /session/{id}/status  — inspect context + remaining budget
  GET  /admin/usage          — aggregate usage over a date range
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.agents.base import SessionContext
from app.agents.orchestrator import PavoOrchestrator
from app.config import get_settings
from app.llm.router import Router, UsageScope
from app.mcp.client import MCPClientManager
from app.media.storage import save_upload
from app.tasks.inference import process_chat_async, process_greeting_async
from app.tasks.media import summarize_media
from app.usage import tracker
from app.usage.db import init_db

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.router = Router()
    app.state.mcp = MCPClientManager()
    # MCP server wiring happens here in production; we defer it so the app
    # boots even when MCP binaries aren't on the PATH (tests, local dev).
    app.state.orchestrator = PavoOrchestrator(app.state.router, app.state.mcp)
    log.info("orchestrator_ready")
    yield
    if app.state.mcp.connected:
        await app.state.mcp.disconnect_all()


app = FastAPI(
    title="Pavo AI Orchestrator",
    description="Agentic AI service for Jardin d'Acclimatation companion",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Visit session id from Rails")
    message: str
    context: dict = Field(default_factory=dict)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pavo-ai"}


@app.post("/chat")
async def chat(req: ChatRequest):
    ctx = SessionContext(session_id=req.session_id, **_ctx_fields(req.context))
    orchestrator: PavoOrchestrator = app.state.orchestrator
    return StreamingResponse(
        orchestrator.stream_response(req.message, ctx),
        media_type="text/event-stream",
    )


@app.post("/chat/async")
async def chat_async(req: ChatRequest):
    task = process_chat_async.delay(req.session_id, req.message, req.context)
    return {"task_id": task.id, "status": "queued"}


class GreetRequest(BaseModel):
    session_id: str = Field(..., description="Visit session id from Rails")
    context: dict = Field(default_factory=dict)


@app.post("/chat/greet", status_code=202)
async def chat_greet(req: GreetRequest):
    """Fire a proactive greeting once the visitor finishes the form.

    Returns 202 immediately; the assistant message is delivered back to
    Rails through the same ai_reply callback as regular chat replies."""
    task = process_greeting_async.delay(req.session_id, req.context)
    return {"task_id": task.id, "status": "queued"}


@app.post("/media/upload")
async def media_upload(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    data = await file.read()
    record = save_upload(session_id=session_id, filename=file.filename or "upload", data=data)
    summarize_media.delay(record.to_dict())
    return {
        "media_id": record.id,
        "session_id": record.session_id,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "processing": "queued",
    }


@app.get("/session/{session_id}/status")
async def session_status(session_id: str, group_id: Optional[str] = None):
    scope = UsageScope(session_id=session_id, group_id=group_id)
    return {
        "session_id": session_id,
        "group_id": group_id,
        "remaining_usd": tracker.remaining_usd(group_id=group_id, session_id=session_id),
        "spent_today_usd": tracker.spent_today_usd(group_id=group_id, session_id=session_id),
    }


def _ctx_fields(raw: dict) -> dict:
    allowed = {"visit_date", "party", "tickets", "history", "preferences", "group_id", "media"}
    return {k: v for k, v in raw.items() if k in allowed}
