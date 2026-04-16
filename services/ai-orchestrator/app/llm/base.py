"""LLM provider abstraction.

Every provider implements `complete(messages, **kwargs) -> LLMCallResult`.
The router / agents consume only this interface so swapping a model or
provider is a YAML edit — not a code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str


@dataclass
class LLMCallResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str
    latency_ms: int
    raw: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str

    async def complete(
        self,
        messages: list[Message],
        *,
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> LLMCallResult: ...
