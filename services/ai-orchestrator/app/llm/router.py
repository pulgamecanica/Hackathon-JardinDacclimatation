"""Task + budget aware model router.

Agents never hardcode a model; they call ``Router.call(task, messages, scope)``
and get back an LLMCallResult plus a persisted usage record. When the
daily cap for the scope is exhausted, the router downgrades to the
cheapest available fallback (typically ``stub-chat``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog

from app.config import load_model_config
from app.llm.base import LLMCallResult, Message
from app.llm.registry import provider_for, provider_is_configured
from app.usage import tracker

log = structlog.get_logger()


@dataclass
class UsageScope:
    session_id: Optional[str] = None
    group_id: Optional[str] = None


def _cost_usd(model_key: str, prompt_tokens: int, completion_tokens: int) -> float:
    entry = load_model_config().models[model_key]
    p_rate, c_rate = entry.cost_per_1k
    return (prompt_tokens / 1000.0) * p_rate + (completion_tokens / 1000.0) * c_rate

# Here it's relecting the model and capping per group_id/session_id, which is a common pattern. But it could be extended
def select_model(task: str, scope: UsageScope) -> tuple[str, bool]:
    """Return (model_key, is_fallback) for the given task and scope."""
    cfg = load_model_config()
    chain = cfg.task_chain(task)

    # Cap exhausted → last entry (cheapest fallback).
    if tracker.cap_exhausted(group_id=scope.group_id, session_id=scope.session_id):
        return chain[-1], True

    # Pick the first configured provider in the chain.
    for model_key in chain:
        provider_name = cfg.models[model_key].provider
        if provider_is_configured(provider_name):
            return model_key, False

    # Nothing configured — fall back to the last entry regardless.
    return chain[-1], True


class Router:
    """Calls the selected LLM and records usage. One-shot per call."""

    async def call(
        self,
        task: str,
        messages: list[Message],
        scope: UsageScope,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult:
        model_key, fallback = select_model(task, scope)
        cfg = load_model_config()
        entry = cfg.models[model_key]
        model_id = entry.model_id or model_key
        provider = provider_for(model_key)

        status = "fallback" if fallback else "success"
        try:
            result = await provider.complete(
                messages,
                model_id=model_id,
                max_tokens=min(max_tokens, entry.max_tokens),
                temperature=temperature,
            )
        except Exception as e:
            log.error("llm_call_failed", task=task, model=model_key, error=str(e))
            tracker.record(
                session_id=scope.session_id,
                group_id=scope.group_id,
                provider=cfg.models[model_key].provider,
                model=model_key,
                task_type=task,
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
                status="error",
                meta={"error": str(e)},
            )
            raise

        cost = _cost_usd(model_key, result.prompt_tokens, result.completion_tokens)
        tracker.record(
            session_id=scope.session_id,
            group_id=scope.group_id,
            provider=result.provider,
            model=model_key,
            task_type=task,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=cost,
            latency_ms=result.latency_ms,
            status=status,
        )
        return result
