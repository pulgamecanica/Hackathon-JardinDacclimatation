from app.usage import tracker


def test_record_and_spent_today():
    tracker.record(
        session_id="s1",
        group_id="g1",
        provider="stub",
        model="stub-chat",
        task_type="chat",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.25,
        latency_ms=10,
    )
    assert tracker.spent_today_usd(group_id="g1", session_id=None) == 0.25
    assert tracker.spent_today_usd(group_id=None, session_id="s1") == 0.25


def test_remaining_honors_cap():
    tracker.record(
        session_id=None,
        group_id="g2",
        provider="stub",
        model="stub-chat",
        task_type="chat",
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=4.99,
        latency_ms=0,
    )
    assert tracker.remaining_usd(group_id="g2", session_id=None) > 0
    tracker.record(
        session_id=None,
        group_id="g2",
        provider="stub",
        model="stub-chat",
        task_type="chat",
        prompt_tokens=0,
        completion_tokens=0,
        cost_usd=0.02,
        latency_ms=0,
    )
    assert tracker.cap_exhausted(group_id="g2", session_id=None)
