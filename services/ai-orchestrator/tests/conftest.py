"""Test fixtures: in-memory DB, fresh caches, no real network."""
from __future__ import annotations

import os
import tempfile

import pytest

# Force the stub provider and in-memory sqlite before any app import.
os.environ.setdefault("DATABASE_URL", "")  # triggers sqlite in-memory fallback
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("VLLM_URL", None)

from app.config import get_settings, load_model_config  # noqa: E402
from app.llm import registry as llm_registry  # noqa: E402
from app.usage import db as usage_db  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_state(tmp_path, monkeypatch):
    # Clear LRU caches so settings env changes take effect per-test.
    get_settings.cache_clear()
    load_model_config.cache_clear()
    llm_registry.clear_cache()

    # Each test gets its own sqlite DB file so tables persist across
    # sessions within one test run.
    db_file = tmp_path / "usage.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    get_settings.cache_clear()

    # Rebuild the engine/session bound to the per-test DB.
    usage_db.engine = usage_db._build_engine()
    usage_db.SessionLocal.configure(bind=usage_db.engine)
    usage_db.init_db()

    # Media root under tmp so tests never write to /var.
    media_root = tmp_path / "media"
    media_root.mkdir()
    monkeypatch.setenv("MEDIA_ROOT", str(media_root))
    get_settings.cache_clear()

    yield
