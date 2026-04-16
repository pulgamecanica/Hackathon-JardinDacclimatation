"""Top-level orchestrator: classify intent, dispatch to a sub-agent.

Agnostic-features rule: the orchestrator never branches on whether the
user has purchased tickets. The calendar-seeded context (date + party) is
enough to do real planning; purchased tickets are just additional data.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator, Literal

import structlog

from app.agents.base import BaseAgent, SessionContext
from app.llm.base import Message
from app.llm.router import Router
from app.mcp.client import MCPClientManager

log = structlog.get_logger()

Intent = Literal["planner", "companion", "concierge", "detective"]

# Should normalize the keywords so there are more matches as well as supporting various languages.
_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    "concierge": ("acheter", "ticket", "billet", "payer", "réserv", "achat"),
    "planner": ("plan", "itinéraire", "route", "optimiser", "par où", "journée"),
    "detective": ("secret", "badge", "récompense", "découvrir", "caché"),
}



class PlumeOrchestrator:
    def __init__(self, router: Router, mcp: MCPClientManager):
        self.router = router
        self.mcp = mcp
        from app.agents.planner import PlanningAgent
        from app.agents.companion import CompanionAgent
        from app.agents.concierge import ConciergeAgent
        from app.agents.discovery import DiscoveryAgent

        self.agents: dict[Intent, BaseAgent] = {
            "planner": PlanningAgent(router, mcp),
            "companion": CompanionAgent(router, mcp),
            "concierge": ConciergeAgent(router, mcp),
            "detective": DiscoveryAgent(router, mcp),
        }

    async def classify_intent(self, message: str, ctx: SessionContext) -> Intent:
        """Fast heuristic classifier; falls through to the LLM only when unclear."""
        m = message.lower()
        for intent, kws in _KEYWORDS.items():
            if any(kw in m for kw in kws):
                return intent

        # Use the cheap classification model via the router.
        prompt = (
            "Classify the user's intent among: planner, companion, concierge, detective. "
            "Reply with a single word.\n"
            f"Message: {message}"
        )
        result = await self.router.call(
            "intent_classification",
            [Message(role="user", content=prompt)],
            ctx.scope,
            max_tokens=8,
            temperature=0.0,
        )
        word = (result.text or "").strip().lower().split()[:1]
        choice: Intent = "companion"
        if word and word[0] in self.agents:
            choice = word[0]  # type: ignore[assignment]
        return choice

    async def stream_response(
        self, message: str, ctx: SessionContext
    ) -> AsyncGenerator[str, None]:
        intent = await self.classify_intent(message, ctx)
        agent = self.agents[intent]

        tools_used: list[str] = []
        async for chunk in agent.run(message, ctx):
            if chunk.get("type") == "tool_call":
                tools_used.append(chunk.get("tool", ""))
            yield f"data: {json.dumps(chunk)}\n\n"

        yield f"data: {json.dumps({'type': 'metadata', 'agent': intent, 'tools': tools_used})}\n\n"
