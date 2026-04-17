"""Concrete LLM provider implementations.

`StubProvider` is fully offline and used in tests + local dev (when no API
keys are set). The real providers wrap the official SDKs with the same
`complete(...)` signature.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from app.llm.base import LLMCallResult, Message


def _latency_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class StubProvider:
    """Deterministic, zero-cost provider for local dev and tests."""

    name = "stub"

    async def complete(
        self,
        messages: list[Message],
        *,
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult:
        start = time.perf_counter()
        # Tiny delay so latency metrics aren't always 0.
        await asyncio.sleep(0.005)
        prompt = "\n".join(m.content for m in messages)
        reply = f"[stub:{model_id}] received {len(messages)} message(s); last: {messages[-1].content[:120] if messages else ''}"
        return LLMCallResult(
            text=reply,
            prompt_tokens=max(1, len(prompt) // 4),
            completion_tokens=max(1, len(reply) // 4),
            model=model_id,
            provider=self.name,
            latency_ms=_latency_ms(start),
            raw={"stub": True},
        )


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url

    async def complete(
        self,
        messages: list[Message],
        *,
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult:
        from openai import AsyncOpenAI  # local import keeps test imports cheap

        start = time.perf_counter()
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        # Newer OpenAI models (gpt-5, o-series) reject `max_tokens` (use
        # `max_completion_tokens`) and only accept the default temperature.
        # They are also reasoning models — reasoning tokens count against
        # `max_completion_tokens`, so a small cap can yield empty output.
        # `reasoning_effort="minimal"` keeps reasoning overhead tiny.
        # vLLM / OpenAILikeProvider overrides this to keep legacy params.
        kwargs: dict[str, Any] = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_completion_tokens": max(max_tokens, 4096),
        }
        if model_id.startswith("gpt-5") or model_id.startswith("o"):
            kwargs["reasoning_effort"] = "minimal"
        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        usage: Any = resp.usage
        return LLMCallResult(
            text=choice.message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model=model_id,
            provider=self.name,
            latency_ms=_latency_ms(start),
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )


class OpenAILikeProvider(OpenAIProvider):
    """vLLM or any OpenAI-compatible endpoint (served at ``base_url``)."""

    name = "vllm"

    async def complete(
        self,
        messages: list[Message],
        *,
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult:
        from openai import AsyncOpenAI

        start = time.perf_counter()
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        # vLLM still uses the legacy `max_tokens` field.
        resp = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0]
        usage: Any = resp.usage
        return LLMCallResult(
            text=choice.message.content or "",
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model=model_id,
            provider=self.name,
            latency_ms=_latency_ms(start),
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    async def complete(
        self,
        messages: list[Message],
        *,
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult:
        import anthropic  # local import

        start = time.perf_counter()
        client = anthropic.AsyncAnthropic(api_key=self.api_key)

        # Anthropic splits system from the messages list.
        system_parts = [m.content for m in messages if m.role == "system"]
        turns = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        resp = await client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system="\n\n".join(system_parts) or None,
            messages=turns,
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        return LLMCallResult(
            text=text,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            model=model_id,
            provider=self.name,
            latency_ms=_latency_ms(start),
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )
