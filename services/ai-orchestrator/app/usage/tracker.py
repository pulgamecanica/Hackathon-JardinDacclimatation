"""Budget accounting for LLM usage.

Exposes two operations:

- `record(...)`: persist an AiUsageLog row after each LLM call.
- `remaining_usd(group_id, session_id)`: how much budget is left today
  for the given scope (group if present, else session). The router uses
  this to decide whether to downgrade to a cheaper model.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select

from app.config import load_model_config
from app.usage.db import SessionLocal
from app.usage.models import AiUsageLog


def _day_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def record(
    *,
    session_id: Optional[str],
    group_id: Optional[str],
    provider: str,
    model: str,
    task_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    latency_ms: int,
    status: str = "success",
    meta: Optional[dict] = None,
) -> AiUsageLog:
    entry = AiUsageLog(
        session_id=session_id,
        group_id=group_id,
        provider=provider,
        model=model,
        task_type=task_type,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        status=status,
        meta=meta or {},
    )
    with SessionLocal() as db:
        db.add(entry)
        db.commit()
        db.refresh(entry)
    return entry


def spent_today_usd(*, group_id: Optional[str], session_id: Optional[str]) -> float:
    """Sum of cost_usd since UTC midnight for the given scope."""
    if not (group_id or session_id):
        return 0.0

    column = AiUsageLog.group_id if group_id else AiUsageLog.session_id
    value = group_id or session_id

    with SessionLocal() as db:
        result = db.execute(
            select(func.coalesce(func.sum(AiUsageLog.cost_usd), 0.0))
            .where(column == value)
            .where(AiUsageLog.created_at >= _day_start_utc())
        ).scalar_one()
        return float(result or 0.0)


def remaining_usd(*, group_id: Optional[str], session_id: Optional[str]) -> float:
    cap = load_model_config().budget.daily_cap_usd
    return max(0.0, cap - spent_today_usd(group_id=group_id, session_id=session_id))


def cap_exhausted(*, group_id: Optional[str], session_id: Optional[str]) -> bool:
    return remaining_usd(group_id=group_id, session_id=session_id) <= 0.0
