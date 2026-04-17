"""Shared agent scaffolding.

Every agent receives a `SessionContext` (date + party + optional tickets
+ history) and produces an async stream of dict chunks. Agents never
care whether tickets are purchased or simulated — features are agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from app.llm.base import Message
from app.llm.router import Router, UsageScope
from app.mcp.client import MCPClientManager, ToolSpec


@dataclass
class SessionContext:
    session_id: str
    visit_date: str | None = None
    party: list[dict[str, Any]] = field(default_factory=list)
    tickets: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    group_id: str | None = None
    media: list[dict[str, Any]] = field(default_factory=list)  # processed media blurbs

    @property
    def scope(self) -> UsageScope:
        return UsageScope(session_id=self.session_id, group_id=self.group_id)

    @property
    def party_size(self) -> int:
        return sum(int(p.get("count", 0)) for p in self.party)


PAVO_PERSONA = (
    "Tu es Pavo, le compagnon IA du Jardin d'Acclimatation à Paris. "
    "Tu réponds en français, avec chaleur et concision — 2 à 4 phrases maximum, "
    "sauf si on te demande explicitement une liste ou un itinéraire détaillé.\n\n"
    "RÈGLES STRICTES DE RÉPONSE — À RESPECTER SANS EXCEPTION :\n"
    "• Ne mentionne JAMAIS d'outils, d'API, de MCP, de recherche, de vérification, "
    "de délai (« un instant », « je vais vérifier », « je consulte »). Le système "
    "t'a déjà fourni toutes les données nécessaires dans le contexte ; écris "
    "directement la réponse comme si tu les savais.\n"
    "• Ne fabrique jamais un prix, un horaire, un tarif ou un événement : "
    "utilise uniquement les valeurs présentes dans le contexte. Si l'information "
    "manque, dis-le simplement en une phrase.\n"
    "• Ne décris jamais ce que tu t'apprêtes à faire ; fais-le."
)


class BaseAgent:
    task: str = "chat"
    system_prompt: str = PAVO_PERSONA
    # Quick-reply chips surfaced to the UI after every reply. Override per
    # agent to match the conversation mode. Empty list = no chips.
    suggestions: list[str] = []

    def __init__(self, router: Router, mcp: MCPClientManager):
        self.router = router
        self.mcp = mcp

    def tools(self) -> list[ToolSpec]:
        return self.mcp.list_all_tools()

    def suggested_replies(self, ctx: SessionContext) -> list[str]:
        """Hook for context-aware chips. Defaults to the static list."""
        return list(self.suggestions)

    def _build_messages(self, user_message: str, ctx: SessionContext) -> list[Message]:
        summary = (
            f"Date de visite: {ctx.visit_date or 'non précisée'}. "
            f"Groupe: {ctx.party_size} personne(s). "
            f"Billets enregistrés: {len(ctx.tickets)} "
            f"(simulés/achetés indifférents — le bot aide dans les deux cas)."
        )
        msgs: list[Message] = [
            Message(role="system", content=self.system_prompt),
            Message(role="system", content=summary),
        ]
        for turn in ctx.history[-8:]:
            msgs.append(Message(role=turn["role"], content=turn["content"]))
        if ctx.media:
            media_blurbs = "\n".join(f"[media] {m.get('summary', '')}" for m in ctx.media)
            msgs.append(Message(role="system", content=f"Media shared by user:\n{media_blurbs}"))
        msgs.append(Message(role="user", content=user_message))
        return msgs

    async def run(self, message: str, ctx: SessionContext) -> AsyncGenerator[dict, None]:
        result = await self.router.call(self.task, self._build_messages(message, ctx), ctx.scope)
        yield {"type": "text", "content": result.text}
        chips = self.suggested_replies(ctx)
        if chips:
            yield {"type": "suggestions", "items": chips}
        yield {
            "type": "usage",
            "model": result.model,
            "provider": result.provider,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "latency_ms": result.latency_ms,
        }
