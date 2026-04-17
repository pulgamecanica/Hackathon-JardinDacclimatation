"""SQLAlchemy engine + session for the usage-tracking DB.

The orchestrator owns the `ai_usage_logs` table; it lives in the same
postgres instance as the Rails API but is managed here.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    url = get_settings().database_url
    if not url:
        # In-memory sqlite for tests / local dev without postgres.
        url = "sqlite:///:memory:"
    # Ensure we use psycopg (v3), not psycopg2
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True, future=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if missing. Call on startup."""
    from app.usage import models  # noqa: F401 — ensure models are registered

    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception:
        # Table/type already exists from a prior run — safe to ignore
        pass
