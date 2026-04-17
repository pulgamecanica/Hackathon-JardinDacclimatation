"""Tests for the per-mode facts block injected ahead of the user message."""
from app.agents.base import SessionContext
from app.agents.facts import build_facts_block


def _ctx(**overrides) -> SessionContext:
    base = dict(
        session_id="s1",
        visit_date="2026-04-21",  # Tuesday
        party=[
            {"visitor_type": "adult", "count": 2},
            {"visitor_type": "child", "count": 1},
        ],
    )
    base.update(overrides)
    return SessionContext(**base)


def test_companion_facts_include_hours_attractions_events():
    block = build_facts_block("companion", _ctx())
    assert block is not None
    assert "Horaires du 2026-04-21" in block
    assert "11:00" in block  # weekday opening
    assert "Grand Carrousel" in block
    assert "Événements du 2026-04-21" in block


def test_planner_gets_richer_attraction_detail():
    block = build_facts_block("planner", _ctx())
    assert block is not None
    # Non-compact mode includes the notes_fr on Grand Carrousel.
    assert "accompagnés" in block


def test_concierge_facts_contain_catalog_with_resolved_prices():
    block = build_facts_block("concierge", _ctx())
    assert block is not None
    assert "Catalogue des offres" in block
    assert "entry_standard" in block
    assert "Pass Illimité" in block
    # Weekday bundle price (48€) should resolve for Tuesday.
    assert "48.00€ ce jour" in block or "48€ ce jour" in block


def test_concierge_without_date_still_lists_catalog():
    block = build_facts_block("concierge", _ctx(visit_date=None))
    assert block is not None
    # No "ce jour" resolution when date is missing.
    assert "ce jour" not in block
    assert "semaine" in block  # day-dependent items still shown as range


def test_detective_skips_catalog():
    block = build_facts_block("detective", _ctx())
    assert block is not None
    assert "Catalogue" not in block
    assert "Grand Carrousel" in block


def test_greeting_is_hours_only():
    block = build_facts_block("greeting", _ctx())
    assert block is not None
    assert "Horaires" in block
    assert "Grand Carrousel" not in block


def test_weekend_date_surfaces_holiday_hours():
    block = build_facts_block("companion", _ctx(visit_date="2026-04-18"))  # Saturday
    assert block is not None
    assert "10:00" in block
    assert "week-end" in block


def test_holiday_is_priced_as_weekend():
    block = build_facts_block("concierge", _ctx(visit_date="2026-07-14"))  # Bastille Day
    assert block is not None
    # Weekend bundle price is 52€.
    assert "52" in block


def test_no_visit_date_returns_minimal_block_for_modes_needing_date():
    # Greeting with no date has nothing to inject — returns None.
    assert build_facts_block("greeting", _ctx(visit_date=None)) is None
