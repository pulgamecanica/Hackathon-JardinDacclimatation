"""Thin Rails API client used by the MCP tools.

Kept separate from ``server.py`` so it can be unit tested without an MCP
transport. The HTTP client is injected by tests via ``TicketsClient(http=...)``.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


class TicketsClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        http: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or os.getenv("RAILS_API_URL", "http://api:3000")).rstrip("/")
        self.api_key = api_key or os.getenv("INTERNAL_API_KEY", "")
        self._http = http
        self._owns_http = http is None

    async def __aenter__(self) -> "TicketsClient":
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_session_details(self, session_id: str) -> dict[str, Any]:
        assert self._http is not None
        r = await self._http.get(
            f"{self.base_url}/api/v1/sessions/{session_id}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    async def create_simulated_ticket(
        self,
        session_id: str,
        visitor_type: str,
        count: int = 1,
        date: str | None = None,
    ) -> dict[str, Any]:
        assert self._http is not None
        payload: dict[str, Any] = {"visitor_type": visitor_type, "count": count}
        if date:
            payload["date"] = date
        r = await self._http.post(
            f"{self.base_url}/api/v1/sessions/{session_id}/tickets/simulated",
            json=payload,
            headers=self._headers(),
        )
        r.raise_for_status()
        return {"status": "created", "simulated": True, "data": r.json()}

    async def confirm_purchase(
        self,
        session_id: str,
        ticket_ids: list[str],
        payment_ref: str,
    ) -> dict[str, Any]:
        assert self._http is not None
        r = await self._http.post(
            f"{self.base_url}/api/v1/sessions/{session_id}/confirm_purchase",
            json={"ticket_ids": ticket_ids, "payment_ref": payment_ref},
            headers=self._headers(),
        )
        r.raise_for_status()
        return {"status": "confirmed", "locked": True, "data": r.json()}
