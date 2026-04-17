"""Tests for the programmatic pack-offer builder used by the concierge agent."""
from app.agents.base import SessionContext
from app.agents.packs import suggest_packs


def _ctx(party, visit_date="2026-04-21"):
    return SessionContext(
        session_id="s1",
        visit_date=visit_date,
        party=party,
    )


def test_returns_empty_without_visit_date():
    assert suggest_packs(_ctx([{"type": "adult", "count": 2}], visit_date=None)) == []


def test_returns_empty_when_party_is_empty():
    assert suggest_packs(_ctx([])) == []


def test_couple_of_adults_gets_three_offers():
    offers = suggest_packs(_ctx([{"type": "adult", "count": 2}]))
    assert len(offers) == 3
    names = [o.name for o in offers]
    assert "Pack Essentiel" in names
    assert "Pack Découverte" in names
    assert "Pack Journée Illimitée" in names


def test_pack_essentiel_totals_only_entries():
    offers = suggest_packs(_ctx([{"type": "adult", "count": 2}]))
    essentiel = next(o for o in offers if o.name == "Pack Essentiel")
    # 2 × 7€ = 14€.
    assert essentiel.total_eur == 14.0
    assert len(essentiel.lines) == 1


def test_family_of_four_gets_tribe_bundle():
    offers = suggest_packs(
        _ctx(
            [
                {"type": "adult", "count": 2},
                {"type": "child", "count": 2},
            ]
        )
    )
    illimitee = next(o for o in offers if "Tribu" in o.name)
    assert illimitee.recommended is True
    # Pass Tribu weekday = 151€, no extras needed for 4 payers.
    assert illimitee.total_eur == 151.0
    # One line for the tribe bundle.
    catalog_ids = {line["catalog_id"] for line in illimitee.lines}
    assert "bundle_tribe" in catalog_ids
    assert "bundle_unlimited" not in catalog_ids


def test_family_of_five_adds_an_unlimited_to_the_tribe():
    offers = suggest_packs(
        _ctx(
            [
                {"type": "adult", "count": 2},
                {"type": "child", "count": 3},
            ]
        )
    )
    illimitee = next(o for o in offers if "Tribu" in o.name)
    # 151 (tribe) + 48 (extra unlimited) = 199€.
    assert illimitee.total_eur == 199.0


def test_small_child_adds_stroller_and_free_entry():
    offers = suggest_packs(
        _ctx(
            [
                {"type": "adult", "count": 2},
                {"type": "small_child", "count": 1},
            ]
        )
    )
    essentiel = next(o for o in offers if o.name == "Pack Essentiel")
    catalog_ids = {line["catalog_id"] for line in essentiel.lines}
    assert "entry_small_child" in catalog_ids
    assert "rental_stroller" in catalog_ids
    # 2 × 7€ + 0€ + 17€ = 31€.
    assert essentiel.total_eur == 31.0


def test_weekend_visit_prices_bundle_higher():
    weekday = suggest_packs(_ctx([{"type": "adult", "count": 2}], visit_date="2026-04-21"))
    weekend = suggest_packs(_ctx([{"type": "adult", "count": 2}], visit_date="2026-04-18"))
    w_bundle = next(o for o in weekday if "Illimitée" in o.name)
    s_bundle = next(o for o in weekend if "Illimitée" in o.name)
    assert s_bundle.total_eur > w_bundle.total_eur


def test_only_small_child_produces_essentiel_only():
    offers = suggest_packs(_ctx([{"type": "small_child", "count": 1}]))
    # No payers → no Découverte, no Illimitée; just Essentiel + stroller.
    assert [o.name for o in offers] == ["Pack Essentiel"]
    essentiel = offers[0]
    # 0€ entry + 17€ stroller.
    assert essentiel.total_eur == 17.0


def test_accepts_legacy_visitor_type_key():
    """The MCP session API returns party entries keyed on ``visitor_type``;
    the visit_session jsonb uses ``type``. Both shapes must work."""
    offers = suggest_packs(_ctx([{"visitor_type": "adult", "count": 2}]))
    assert len(offers) == 3


def test_pack_offers_serialize_to_primitive_dicts():
    offers = suggest_packs(_ctx([{"type": "adult", "count": 2}]))
    d = offers[0].to_dict()
    assert set(d) >= {"id", "name", "description", "lines", "total_eur", "currency", "recommended"}
    assert isinstance(d["lines"], list)
    assert d["currency"] == "EUR"
