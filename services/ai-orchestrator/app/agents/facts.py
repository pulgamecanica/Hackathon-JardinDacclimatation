"""Pre-fetch MCP data for the agent's mode and format it as a system block.

We mirror the MCP fixtures in-process (see `app.mcp.park_status` and
`app.mcp.catalog`) so agents don't pay a stdio round-trip per turn.
The real stdio servers still exist for external callers and for tests
that need transport-level coverage.

Each mode gets only the facts it needs — feeding the whole catalog +
10 attractions + 7 events into every prompt would waste tokens.
"""
from __future__ import annotations

from datetime import date as Date
from typing import Literal

from app.agents.base import SessionContext
from app.mcp import catalog as catalog_mod
from app.mcp import park_status

Mode = Literal["companion", "planner", "concierge", "detective", "greeting"]


def build_facts_block(mode: Mode, ctx: SessionContext) -> str | None:
    """Return a formatted facts block tailored to the agent mode, or None.

    None means "nothing useful to inject" — usually because we have no
    visit date. Agents still work without facts; they just can't quote
    hours or prices.
    """
    visit = _parse_visit_date(ctx.visit_date)
    sections: list[str] = []

    if mode == "companion":
        if visit is not None:
            sections.append(_hours_section(visit))
        sections.append(_attractions_section(compact=True))
        if visit is not None:
            sections.append(_events_section(visit))

    elif mode == "planner":
        if visit is not None:
            sections.append(_hours_section(visit))
        sections.append(_attractions_section(compact=False))
        if visit is not None:
            sections.append(_events_section(visit))

    elif mode == "concierge":
        if visit is not None:
            sections.append(_catalog_section(visit))
        else:
            sections.append(_catalog_section(None))

    elif mode == "detective":
        sections.append(_attractions_section(compact=True))
        if visit is not None:
            sections.append(_events_section(visit))

    elif mode == "greeting":
        if visit is not None:
            sections.append(_hours_section(visit))

    if not sections:
        return None

    body = "\n\n".join(s for s in sections if s)
    return (
        "FAITS VÉRIFIÉS (à utiliser tels quels, ne jamais modifier les prix ou horaires) :\n"
        f"{body}"
    )


# ── Section builders ───────────────────────────────────────────────

def _hours_section(d: Date) -> str:
    h = park_status.get_park_hours(d)
    label = "week-end/jour férié" if h.is_weekend_or_holiday else "jour de semaine"
    line = (
        f"Horaires du {d.isoformat()} ({label}) : "
        f"ouverture {h.opening_time}, fermeture {h.closing_time}, "
        f"dernière entrée {h.last_entry_time}."
    )
    if h.notes_fr:
        line += f" {h.notes_fr}"
    return line


def _attractions_section(compact: bool) -> str:
    lines = ["Attractions du parc :"]
    for a in park_status.list_attractions():
        parts = [f"- {a.name_fr} (id: {a.id}, zone {a.zone})"]
        if a.min_height_cm is not None:
            parts.append(f"taille min {a.min_height_cm} cm")
        if a.age_min is not None:
            parts.append(f"âge min {a.age_min} ans")
        parts.append(f"sensations {a.thrill_level}")
        parts.append(f"attente moy. {a.avg_wait_min} min")
        if a.accessible_wheelchair:
            parts.append("accessible fauteuil")
        line = ", ".join(parts)
        if not compact and a.notes_fr:
            line += f" — {a.notes_fr}"
        lines.append(line)
    return "\n".join(lines)


def _events_section(d: Date) -> str:
    events = park_status.list_events(d)
    if not events:
        return f"Événements du {d.isoformat()} : aucun programmé."
    lines = [f"Événements du {d.isoformat()} :"]
    for e in events:
        lines.append(
            f"- {e.name_fr} ({e.start_time}–{e.end_time}, {e.zone}) — {e.audience_fr}"
        )
    return "\n".join(lines)


def _catalog_section(visit: Date | None) -> str:
    """Compact catalog formatting grouped by category, with resolved prices."""
    by_cat: dict[str, list[catalog_mod.CatalogItem]] = {}
    for item in catalog_mod.CATALOG:
        by_cat.setdefault(item.category, []).append(item)

    order = [
        ("park_entry", "Entrée simple"),
        ("admission", "Abonnements & carnets"),
        ("attraction_unit", "Tickets d'attractions"),
        ("attraction_bundle", "Pass illimités (prix selon jour)"),
        ("rental", "Locations"),
    ]
    lines = ["Catalogue des offres :"]
    for cat, label in order:
        items = by_cat.get(cat) or []
        if not items:
            continue
        lines.append(f"\n{label} :")
        for item in items:
            price_str = _format_price(item, visit)
            lines.append(f"- {item.name_fr} (id: {item.id}) — {price_str}")
    return "\n".join(lines)


def _format_price(item: "catalog_mod.CatalogItem", visit: Date | None) -> str:
    if item.is_day_dependent:
        if visit is not None:
            resolved = item.price_for_date(visit)
            return (
                f"{resolved:.2f}€ ce jour "
                f"(semaine {item.price_weekday_eur}€ / week-end {item.price_weekend_eur}€)"
            )
        return f"semaine {item.price_weekday_eur}€ / week-end {item.price_weekend_eur}€"
    assert item.price_eur is not None
    return f"{item.price_eur:.2f}€"


def _parse_visit_date(iso: str | None) -> Date | None:
    if not iso:
        return None
    try:
        return Date.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
