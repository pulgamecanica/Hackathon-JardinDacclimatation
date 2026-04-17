"""Unit tests for the park-status fixtures module (no MCP, pure data)."""
from datetime import date

import pytest

from src.fixtures import (
    ATTRACTIONS,
    EVENTS,
    filter_attractions,
    get_attraction,
    get_attraction_status,
    get_park_hours,
    is_weekend_or_holiday,
    list_attractions,
    list_events,
)


# ── Calendar ─────────────────────────────────────────────────

def test_weekend_detection_saturday():
    assert is_weekend_or_holiday(date(2026, 4, 18)) is True


def test_weekend_detection_weekday():
    assert is_weekend_or_holiday(date(2026, 4, 21)) is False


def test_weekend_detection_bastille_day():
    # July 14 2026 is a Tuesday but a public holiday.
    assert is_weekend_or_holiday(date(2026, 7, 14)) is True


# ── Park hours ───────────────────────────────────────────────

def test_weekday_hours():
    hours = get_park_hours(date(2026, 4, 21))  # Tuesday
    assert hours.opening_time == "11:00"
    assert hours.closing_time == "19:00"
    assert hours.last_entry_time == "18:00"
    assert hours.is_weekend_or_holiday is False


def test_weekend_hours_are_extended():
    hours = get_park_hours(date(2026, 4, 18))  # Saturday
    assert hours.opening_time == "10:00"
    assert hours.closing_time == "20:00"
    assert hours.is_weekend_or_holiday is True


def test_holiday_hours_match_weekend():
    assert get_park_hours(date(2026, 7, 14)).opening_time == "10:00"


# ── Attractions ──────────────────────────────────────────────

def test_every_attraction_has_unique_id():
    ids = [a.id for a in ATTRACTIONS]
    assert len(ids) == len(set(ids))


def test_list_attractions_no_filter_returns_all():
    assert len(list_attractions()) == len(ATTRACTIONS)


def test_list_attractions_filters_by_zone():
    sensation_ids = {a.id for a in list_attractions("sensations")}
    assert sensation_ids == {"speed_rockets", "dragon_chinois"}


def test_get_attraction_raises_for_unknown():
    with pytest.raises(KeyError):
        get_attraction("does_not_exist")


# ── Attraction status ────────────────────────────────────────

def test_attraction_open_by_default():
    status = get_attraction_status("grand_carrousel", date(2026, 4, 21))
    assert status.status == "open"
    assert status.current_wait_min >= 0


def test_attraction_maintenance_window_honored():
    status = get_attraction_status("dragon_chinois", date(2026, 4, 20))
    assert status.status == "maintenance"
    assert status.current_wait_min == 0
    assert "maintenance" in (status.note_fr or "").lower()


def test_attraction_wait_is_deterministic_per_date():
    """Same date + id → same wait (agents may call twice)."""
    a = get_attraction_status("riviere_enchantee", date(2026, 4, 21))
    b = get_attraction_status("riviere_enchantee", date(2026, 4, 21))
    assert a.current_wait_min == b.current_wait_min


def test_attraction_wait_differs_across_dates():
    """Wait should vary day-to-day — otherwise the jitter isn't working."""
    samples = {
        get_attraction_status("speed_rockets", date(2026, 4, d)).current_wait_min
        for d in range(21, 28)
    }
    assert len(samples) > 1


def test_walking_attraction_has_no_wait():
    status = get_attraction_status("foret_enchantee", date(2026, 4, 21))
    assert status.current_wait_min == 0


# ── Events ───────────────────────────────────────────────────

def test_weekday_events_exclude_weekend_only_items():
    tuesday = list_events(date(2026, 4, 21))
    ids = {e.id for e in tuesday}
    assert "concert_jardin_dimanche" not in ids
    assert "parade_animaux" in ids


def test_weekend_includes_concert():
    saturday = list_events(date(2026, 4, 18))
    ids = {e.id for e in saturday}
    assert "concert_jardin_dimanche" in ids


def test_every_event_has_unique_id():
    ids = [e.id for e in EVENTS]
    assert len(ids) == len(set(ids))


# ── filter_attractions helper ─────────────────────────────────

def test_filter_by_max_wait_drops_long_queues():
    calm = filter_attractions(max_wait_min=10)
    assert all(a.avg_wait_min <= 10 for a in calm)


def test_filter_for_small_children_drops_height_restricted():
    toddler_friendly = filter_attractions(min_height_cm_lt=100)
    ids = {a.id for a in toddler_friendly}
    # Dragon Chinois (125cm) and Speed Rockets (120cm) must be excluded.
    assert "dragon_chinois" not in ids
    assert "speed_rockets" not in ids
    # Ferme (no height) stays.
    assert "ferme_aux_animaux" in ids


def test_filter_for_wheelchair_accessible():
    accessible = filter_attractions(accessible_wheelchair=True)
    ids = {a.id for a in accessible}
    assert "ferme_aux_animaux" in ids
    assert "dragon_chinois" not in ids
