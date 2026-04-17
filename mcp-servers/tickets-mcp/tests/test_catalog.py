"""Unit tests for the static ticket catalog + pack-offer builder."""
import json
from datetime import date

import pytest

import src.server as server_mod
from src.catalog import (
    CATALOG,
    PackItem,
    build_pack_offer,
    get_item,
    is_weekend_or_holiday,
    list_items,
)


# ── Catalog shape ──────────────────────────────────────────────

def test_every_item_has_unique_id():
    ids = [i.id for i in CATALOG]
    assert len(ids) == len(set(ids))


def test_every_item_has_pricing():
    for item in CATALOG:
        has_flat = item.price_eur is not None
        has_split = item.price_weekday_eur is not None and item.price_weekend_eur is not None
        assert has_flat ^ has_split, f"{item.id} needs exactly one pricing scheme"


def test_list_items_filters_by_category():
    bundles = list_items("attraction_bundle")
    assert {i.id for i in bundles} == {"bundle_unlimited", "bundle_tribe", "bundle_16h"}


# ── Weekend/holiday logic ─────────────────────────────────────

def test_saturday_is_weekend():
    assert is_weekend_or_holiday(date(2026, 4, 18)) is True  # Saturday


def test_tuesday_is_weekday():
    assert is_weekend_or_holiday(date(2026, 4, 21)) is False  # Tuesday


def test_public_holiday_is_weekend_priced():
    # 14 juillet 2026 — Tuesday, but holiday
    assert is_weekend_or_holiday(date(2026, 7, 14)) is True


# ── price_for_date ────────────────────────────────────────────

def test_unlimited_bundle_weekday_price():
    item = get_item("bundle_unlimited")
    assert item.price_for_date(date(2026, 4, 21)) == 48.0


def test_unlimited_bundle_weekend_price():
    item = get_item("bundle_unlimited")
    assert item.price_for_date(date(2026, 4, 18)) == 52.0


def test_flat_price_is_date_independent():
    item = get_item("attraction_ticket")
    assert item.price_for_date(date(2026, 4, 18)) == 4.5
    assert item.price_for_date(date(2026, 4, 21)) == 4.5


# ── Pack offer builder ────────────────────────────────────────

def test_build_pack_offer_computes_total():
    offer = build_pack_offer(
        name="Famille Tribu",
        description="Une journée complète pour 4.",
        items=[PackItem("bundle_tribe", 1), PackItem("rental_stroller", 1)],
        visit_date=date(2026, 4, 21),  # weekday
    )
    # 151 + 17 = 168
    assert offer.total_eur == 168.0
    assert len(offer.lines) == 2


def test_build_pack_offer_weekend_bundle_priced_higher():
    weekday = build_pack_offer(
        name="X", description="x",
        items=[{"catalog_id": "bundle_unlimited", "quantity": 2}],
        visit_date=date(2026, 4, 21),
    )
    weekend = build_pack_offer(
        name="X", description="x",
        items=[{"catalog_id": "bundle_unlimited", "quantity": 2}],
        visit_date=date(2026, 4, 18),
    )
    assert weekend.total_eur > weekday.total_eur


def test_build_pack_offer_rejects_unknown_item():
    with pytest.raises(KeyError):
        build_pack_offer(
            name="X", description="x",
            items=[PackItem("does_not_exist", 1)],
            visit_date=date(2026, 4, 21),
        )


def test_build_pack_offer_rejects_zero_quantity():
    with pytest.raises(ValueError):
        build_pack_offer(
            name="X", description="x",
            items=[PackItem("attraction_ticket", 0)],
            visit_date=date(2026, 4, 21),
        )


# ── MCP call_tool handlers ────────────────────────────────────

@pytest.mark.asyncio
async def test_list_ticket_catalog_without_date():
    result = await server_mod.call_tool("list_ticket_catalog", {})
    payload = json.loads(result[0].text)
    assert len(payload["items"]) == len(CATALOG)


@pytest.mark.asyncio
async def test_list_ticket_catalog_filtered_resolves_price_for_date():
    result = await server_mod.call_tool(
        "list_ticket_catalog",
        {"category": "attraction_bundle", "visit_date": "2026-04-18"},  # Saturday
    )
    payload = json.loads(result[0].text)
    unlimited = next(i for i in payload["items"] if i["id"] == "bundle_unlimited")
    assert unlimited["price_for_date_eur"] == 52.0
    assert unlimited["is_weekend_or_holiday"] is True


@pytest.mark.asyncio
async def test_quote_ticket_uses_correct_day_price():
    result = await server_mod.call_tool(
        "quote_ticket",
        {"catalog_id": "bundle_tribe", "visit_date": "2026-04-21", "quantity": 1},
    )
    payload = json.loads(result[0].text)
    assert payload["unit_price_eur"] == 151.0
    assert payload["total_eur"] == 151.0


@pytest.mark.asyncio
async def test_create_pack_offer_returns_priced_lines():
    result = await server_mod.call_tool(
        "create_pack_offer",
        {
            "name": "Découverte",
            "description": "Entrée + 2 attractions.",
            "visit_date": "2026-04-21",
            "items": [
                {"catalog_id": "entry_standard", "quantity": 2},
                {"catalog_id": "attraction_ticket", "quantity": 4},
            ],
            "recommended": True,
            "highlight_features": ["Idéal pour un premier contact"],
        },
    )
    payload = json.loads(result[0].text)
    assert payload["recommended"] is True
    # 2*7 + 4*4.5 = 14 + 18 = 32
    assert payload["total_eur"] == 32.0
    assert len(payload["lines"]) == 2
    assert payload["highlight_features"] == ["Idéal pour un premier contact"]
