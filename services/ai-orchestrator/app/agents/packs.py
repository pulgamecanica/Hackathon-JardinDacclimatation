"""Programmatic pack-offer builder for the concierge agent.

The LLM is not trusted to invent prices, so pack contents are chosen
*in code* from the party composition and the visit date. The catalog
computes every line price — the agent only gets to write the name and
description, and explain the offers to the user.

We expose 2–3 stable shapes:

* **Essentiel** — park-entry only, for people who just want to walk around.
* **Découverte** — park-entry + a carnet of 15 attraction tickets.
* **Journée illimitée** — bundle pass (Pass Tribu for 4 payers, otherwise
  Pass Illimité × payers). Marked as `recommended`.

A stroller rental is auto-added whenever the party includes a small child,
regardless of the pack chosen.
"""
from __future__ import annotations

from datetime import date as Date
from typing import Iterable

from app.agents.base import SessionContext
from app.mcp.catalog import PackItem, PackOffer, build_pack_offer


# Visitor-type buckets. Anything that pays the standard 7€ entry counts
# as a "payer"; small_child is free; rsa/disabled get their own entry_ id.
_PAYING_TYPES = {"adult", "child", "teen"}
_FREE_ENTRY_TYPES = {"small_child", "disabled", "rsa"}
_REDUCED_ENTRY_TYPES = {"senior", "large_family", "jobseeker"}

_ENTRY_ID_BY_TYPE: dict[str, str] = {
    "adult": "entry_standard",
    "child": "entry_standard",
    "teen": "entry_standard",
    "small_child": "entry_small_child",
    "disabled": "entry_disabled",
    "rsa": "entry_rsa",
    "senior": "entry_senior",
    "large_family": "entry_large_family",
    "jobseeker": "entry_jobseeker",
}


def suggest_packs(ctx: SessionContext) -> list[PackOffer]:
    """Return 0–3 priced pack offers tailored to the party + visit date.

    Empty list when we don't have enough context (no visit date or empty
    party). The caller should handle that gracefully — the agent can still
    reply with free-form text.
    """
    visit = _parse_visit_date(ctx.visit_date)
    if visit is None:
        return []

    counts = _count_by_type(ctx.party)
    total_people = sum(counts.values())
    if total_people == 0:
        return []

    # Entry lines are shared by Essentiel and Découverte.
    entry_lines = _entry_lines(counts)
    needs_stroller = counts.get("small_child", 0) > 0

    offers: list[PackOffer] = []

    # Pack 1 — Essentiel (entries only + optional stroller)
    essentiel_items = list(entry_lines)
    if needs_stroller:
        essentiel_items.append(PackItem("rental_stroller", 1))
    if essentiel_items:
        offers.append(
            build_pack_offer(
                name="Pack Essentiel",
                description=(
                    "Accès au Jardin pour profiter des allées, de la ferme et des spectacles gratuits. "
                    "Idéal pour une première visite sans attractions."
                ),
                items=essentiel_items,
                visit_date=visit,
                highlight_features=[
                    "Entrée au Jardin pour tout le groupe",
                    "Ferme aux animaux et parcours nature",
                    "Spectacles gratuits du jour",
                ]
                + (["Poussette incluse"] if needs_stroller else []),
            )
        )

    # Pack 2 — Découverte (entries + carnet de 15 attractions)
    payers = _payer_count(counts)
    if payers > 0:
        carnets = _carnets_for_payers(payers)
        decouverte_items = list(entry_lines) + [PackItem("attraction_carnet_15", carnets)]
        if needs_stroller:
            decouverte_items.append(PackItem("rental_stroller", 1))
        offers.append(
            build_pack_offer(
                name="Pack Découverte",
                description=(
                    "Entrées + un carnet de 15 tickets d'attractions pour goûter aux manèges "
                    "sans s'engager sur la journée. Parfait pour une sortie à son rythme."
                ),
                items=decouverte_items,
                visit_date=visit,
                highlight_features=[
                    f"{carnets * 15} tickets d'attractions",
                    "Valables 1 an — le surplus reste utilisable",
                    "Entrée au Jardin incluse",
                ],
            )
        )

    # Pack 3 — Journée illimitée (recommended)
    unlimited = _unlimited_pack(counts, visit, needs_stroller)
    if unlimited is not None:
        offers.append(unlimited)

    return offers


# ── helpers ────────────────────────────────────────────────────────

def _parse_visit_date(iso: str | None) -> Date | None:
    if not iso:
        return None
    try:
        return Date.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _count_by_type(party: Iterable[dict]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for p in party:
        vt = (p.get("visitor_type") or "").strip()
        if not vt:
            continue
        totals[vt] = totals.get(vt, 0) + int(p.get("count", 0) or 0)
    return {k: v for k, v in totals.items() if v > 0}


def _payer_count(counts: dict[str, int]) -> int:
    return sum(c for vt, c in counts.items() if vt in _PAYING_TYPES)


def _entry_lines(counts: dict[str, int]) -> list[PackItem]:
    """Group visitor counts onto their matching entry catalog id."""
    by_catalog: dict[str, int] = {}
    for vt, c in counts.items():
        cat_id = _ENTRY_ID_BY_TYPE.get(vt)
        if cat_id is None:
            continue
        by_catalog[cat_id] = by_catalog.get(cat_id, 0) + c
    return [PackItem(cat_id, qty) for cat_id, qty in by_catalog.items() if qty > 0]


def _carnets_for_payers(payers: int) -> int:
    """Rule of thumb: 1 carnet of 15 per 2 payers, minimum 1."""
    return max(1, (payers + 1) // 2)


def _unlimited_pack(
    counts: dict[str, int],
    visit: Date,
    needs_stroller: bool,
) -> PackOffer | None:
    payers = _payer_count(counts)
    if payers == 0:
        return None

    items: list[PackItem] = []
    # Small children join free — no extra ticket.
    # Tribu pass covers any 4 people; buy 1 Tribu + extra Illimité per 5th+.
    if payers >= 4:
        items.append(PackItem("bundle_tribe", 1))
        extras = payers - 4
        if extras > 0:
            items.append(PackItem("bundle_unlimited", extras))
        name = "Pack Famille Tribu"
        description = (
            "Entrée + attractions illimitées pour 4 personnes (Pass Tribu), idéal en famille. "
            "Le meilleur rapport qualité-prix pour une journée complète."
        )
    else:
        items.append(PackItem("bundle_unlimited", payers))
        name = "Pack Journée Illimitée"
        description = (
            "Pass illimité pour chaque participant : entrée + toutes les attractions de la journée. "
            "Aucun ticket à gérer, on profite à fond."
        )

    # Free visitors (small_child / disabled / rsa) still need their park entry ticket.
    for vt, c in counts.items():
        if vt in _FREE_ENTRY_TYPES:
            items.append(PackItem(_ENTRY_ID_BY_TYPE[vt], c))

    if needs_stroller:
        items.append(PackItem("rental_stroller", 1))

    highlights = [
        "Attractions illimitées toute la journée",
        "Idéal pour les fans de manèges",
    ]
    if payers >= 4:
        highlights.insert(0, "Formule Tribu — 4 personnes pour un prix groupé")
    if needs_stroller:
        highlights.append("Poussette incluse")

    return build_pack_offer(
        name=name,
        description=description,
        items=items,
        visit_date=visit,
        recommended=True,
        highlight_features=highlights,
    )
