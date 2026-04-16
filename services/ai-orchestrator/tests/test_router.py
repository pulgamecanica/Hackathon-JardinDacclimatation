import pytest

from app.llm.base import Message
from app.llm.router import Router, UsageScope, select_model
from app.usage import tracker


def test_select_prefers_stub_when_no_keys_set():
    model, fallback = select_model("planning", UsageScope(session_id="s1"))
    assert model == "stub-chat"
    assert fallback is False


def test_select_forces_fallback_when_cap_exhausted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from app.config import load_model_config
    from app.llm import registry

    load_model_config.cache_clear()
    registry.clear_cache()

    tracker.record(
        session_id=None, group_id="gX", provider="openai", model="gpt-5-mini",
        task_type="chat", prompt_tokens=0, completion_tokens=0,
        cost_usd=100.0, latency_ms=0,
    )
    model, fallback = select_model("chat", UsageScope(group_id="gX"))
    assert fallback is True
    assert model == "stub-chat"


@pytest.mark.asyncio
async def test_router_records_usage_on_success():
    router = Router()
    scope = UsageScope(session_id="sR", group_id=None)
    result = await router.call(
        "chat",
        [Message(role="user", content="bonjour")],
        scope,
    )
    assert result.provider == "stub"
    assert result.text.startswith("[stub:")
    assert tracker.spent_today_usd(group_id=None, session_id="sR") >= 0.0
