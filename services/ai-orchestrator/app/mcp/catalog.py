"""Static ticket catalog for the Jardin d'Acclimatation.

Mirrors the printed price grid (Entrée simple, Admission, Attraction
units, Bundles, Rentals). Bundle prices depend on whether the visit
day is a weekday or a weekend/holiday — `price_for_date` resolves that.

This module is intentionally data-only so both the MCP server and the
AI orchestrator can import it and produce the exact same quotes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date as Date
from typing import Iterable, Literal


Category = Literal[
    "park_entry",        # Entrée simple — single park admission
    "admission",         # Multi-use admission (carnet / annual pass)
    "attraction_unit",   # Single or book attraction tickets
    "attraction_bundle", # Unlimited passes (day-dependent pricing)
    "rental",            # Strollers, wheelchairs
]


@dataclass(frozen=True)
class CatalogItem:
    id: str
    category: Category
    name_fr: str
    description_fr: str
    audience: tuple[str, ...]          # "adult", "small_child", "child", "teen",
                                       # "senior", "rsa", "disabled", "jobseeker",
                                       # "large_family", "group", "any"
    # Pricing — either a single price, or weekday/weekend split:
    price_eur: float | None = None
    price_weekday_eur: float | None = None
    price_weekend_eur: float | None = None
    validity_days: int | None = None   # 1 = same-day; 365 = one year; None = n/a
    notes_fr: str | None = None

    @property
    def is_day_dependent(self) -> bool:
        return self.price_weekday_eur is not None and self.price_weekend_eur is not None

    def price_for_date(self, visit: Date) -> float:
        """Return the price in EUR for a given visit date."""
        if self.is_day_dependent:
            return (
                self.price_weekend_eur  # type: ignore[return-value]
                if is_weekend_or_holiday(visit)
                else self.price_weekday_eur  # type: ignore[return-value]
            )
        if self.price_eur is None:
            raise ValueError(f"CatalogItem {self.id} has no price configured")
        return self.price_eur


# ── French public holidays (subset relevant to 2026) ───────────────────
# Kept local so the catalog is self-contained. "Vacances scolaires Zone C"
# would need a broader dataset — for the hackathon this is enough.
_PUBLIC_HOLIDAYS_2026 = frozenset(
    {
        Date(2026, 1, 1),    # Jour de l'An
        Date(2026, 4, 6),    # Lundi de Pâques
        Date(2026, 5, 1),    # Fête du Travail
        Date(2026, 5, 8),    # Victoire 1945
        Date(2026, 5, 14),   # Ascension
        Date(2026, 5, 25),   # Lundi de Pentecôte
        Date(2026, 7, 14),   # Fête Nationale
        Date(2026, 8, 15),   # Assomption
        Date(2026, 11, 1),   # Toussaint
        Date(2026, 11, 11),  # Armistice
        Date(2026, 12, 25),  # Noël
    }
)


def is_weekend_or_holiday(d: Date) -> bool:
    """True for Saturday, Sunday, or a public holiday."""
    return d.weekday() >= 5 or d in _PUBLIC_HOLIDAYS_2026


# ── Catalog ─────────────────────────────────────────────────────────────
# Prices taken directly from the Jardin d'Acclimatation 2026 price grid
# provided by the client. Keep IDs stable — agents reference them.

CATALOG: tuple[CatalogItem, ...] = (
    # Entrée simple — single park entry, tarified per audience
    CatalogItem(
        id="entry_standard",
        category="park_entry",
        name_fr="Entrée simple — Adulte / Enfant (≥ 80 cm)",
        description_fr="Accès au Jardin, hors attractions. Valable 1 journée.",
        audience=("adult", "child", "teen"),
        price_eur=7.0,
        validity_days=1,
    ),
    CatalogItem(
        id="entry_small_child",
        category="park_entry",
        name_fr="Entrée simple — Jeune enfant (< 80 cm)",
        description_fr="Accès gratuit au Jardin pour les enfants de moins de 80 cm.",
        audience=("small_child",),
        price_eur=0.0,
        validity_days=1,
    ),
    CatalogItem(
        id="entry_rsa",
        category="park_entry",
        name_fr="Entrée simple — RSA",
        description_fr="Gratuit sur présentation d'un justificatif RSA.",
        audience=("rsa",),
        price_eur=0.0,
        validity_days=1,
        notes_fr="Justificatif requis à l'entrée.",
    ),
    CatalogItem(
        id="entry_senior",
        category="park_entry",
        name_fr="Entrée simple — Sénior (60+)",
        description_fr="Tarif réduit pour les visiteurs de 60 ans et plus.",
        audience=("senior",),
        price_eur=5.0,
        validity_days=1,
    ),
    CatalogItem(
        id="entry_large_family",
        category="park_entry",
        name_fr="Entrée simple — Famille nombreuse",
        description_fr="Tarif réduit pour les familles nombreuses.",
        audience=("large_family",),
        price_eur=5.0,
        validity_days=1,
        notes_fr="Carte famille nombreuse requise.",
    ),
    CatalogItem(
        id="entry_disabled",
        category="park_entry",
        name_fr="Entrée simple — Personne en situation de handicap",
        description_fr="Gratuit sur présentation d'un justificatif.",
        audience=("disabled",),
        price_eur=0.0,
        validity_days=1,
    ),
    CatalogItem(
        id="entry_jobseeker",
        category="park_entry",
        name_fr="Entrée simple — Demandeur d'emploi",
        description_fr="Tarif réduit sur présentation d'un justificatif.",
        audience=("jobseeker",),
        price_eur=5.0,
        validity_days=1,
    ),

    # Admission — multi-use park-only tickets
    CatalogItem(
        id="admission_carnet_10",
        category="admission",
        name_fr="Carnet de 10 entrées",
        description_fr="10 entrées au Jardin, utilisables sur 1 an. Accès au parc uniquement, hors attractions.",
        audience=("any", "group"),
        price_eur=63.0,
        validity_days=365,
    ),
    CatalogItem(
        id="admission_annual_pass",
        category="admission",
        name_fr="Abonnement annuel",
        description_fr="12 mois d'entrée illimitée au Jardin, hors attractions. Nominatif.",
        audience=("any",),
        price_eur=52.0,
        validity_days=365,
        notes_fr="Abonnement nominatif. Donne aussi droit au Carnet de 50 tickets d'attractions.",
    ),

    # Attraction tickets — à l'unité ou en carnets
    CatalogItem(
        id="attraction_ticket",
        category="attraction_unit",
        name_fr="Ticket d'attraction à l'unité",
        description_fr="1 ticket pour une attraction, valable le jour de l'achat.",
        audience=("any",),
        price_eur=4.5,
        validity_days=1,
    ),
    CatalogItem(
        id="attraction_carnet_15",
        category="attraction_unit",
        name_fr="Carnet de 15 tickets d'attractions",
        description_fr="15 tickets d'attractions, utilisables sur 1 an.",
        audience=("any",),
        price_eur=55.0,
        validity_days=365,
    ),
    CatalogItem(
        id="attraction_carnet_50",
        category="attraction_unit",
        name_fr="Carnet de 50 tickets d'attractions",
        description_fr="50 tickets d'attractions, utilisables sur 1 an. Réservé aux abonnés du parc.",
        audience=("any",),
        price_eur=120.0,
        validity_days=365,
        notes_fr="Nécessite un Abonnement annuel actif.",
    ),

    # Attraction bundles — day-dependent (weekday vs weekend/holiday)
    CatalogItem(
        id="bundle_unlimited",
        category="attraction_bundle",
        name_fr="Pass Illimité",
        description_fr="Entrée et accès illimité aux attractions pour une journée complète.",
        audience=("any",),
        price_weekday_eur=48.0,
        price_weekend_eur=52.0,
        validity_days=1,
    ),
    CatalogItem(
        id="bundle_tribe",
        category="attraction_bundle",
        name_fr="Pass Tribu",
        description_fr="Entrée et accès illimité aux attractions pour 4 personnes, une journée complète.",
        audience=("any",),
        price_weekday_eur=151.0,
        price_weekend_eur=163.0,
        validity_days=1,
        notes_fr="Valable pour 4 personnes, toute composition.",
    ),
    CatalogItem(
        id="bundle_16h",
        category="attraction_bundle",
        name_fr="Pass 16h00",
        description_fr="Entrée et accès illimité aux attractions à partir de 16h00.",
        audience=("any",),
        price_weekday_eur=27.0,
        price_weekend_eur=29.0,
        validity_days=1,
    ),

    # Rentals
    CatalogItem(
        id="rental_stroller",
        category="rental",
        name_fr="Location de poussette",
        description_fr="Poussette à louer sur place pour la journée.",
        audience=("any",),
        price_eur=17.0,
        validity_days=1,
    ),
    CatalogItem(
        id="rental_wheelchair",
        category="rental",
        name_fr="Location de fauteuil roulant de confort",
        description_fr="Fauteuil roulant de confort à louer sur place pour la journée.",
        audience=("any",),
        price_eur=20.0,
        validity_days=1,
    ),
)

_BY_ID: dict[str, CatalogItem] = {item.id: item for item in CATALOG}


def get_item(item_id: str) -> CatalogItem:
    """Look up a catalog item by its stable id. Raises KeyError if missing."""
    if item_id not in _BY_ID:
        raise KeyError(f"Unknown catalog item: {item_id}")
    return _BY_ID[item_id]


def list_items(category: Category | None = None) -> list[CatalogItem]:
    """Return catalog items, optionally filtered to a single category."""
    if category is None:
        return list(CATALOG)
    return [i for i in CATALOG if i.category == category]


def item_to_dict(item: CatalogItem, visit_date: Date | None = None) -> dict:
    """Serialize a catalog item to a plain dict, resolving price if a date is given."""
    out: dict = {
        "id": item.id,
        "category": item.category,
        "name_fr": item.name_fr,
        "description_fr": item.description_fr,
        "audience": list(item.audience),
        "validity_days": item.validity_days,
        "notes_fr": item.notes_fr,
    }
    if item.is_day_dependent:
        out["price_weekday_eur"] = item.price_weekday_eur
        out["price_weekend_eur"] = item.price_weekend_eur
    else:
        out["price_eur"] = item.price_eur
    if visit_date is not None:
        out["price_for_date_eur"] = round(item.price_for_date(visit_date), 2)
        out["is_weekend_or_holiday"] = is_weekend_or_holiday(visit_date)
    return out


# ── Pack offers ────────────────────────────────────────────────────────
# An offer is a bundle of catalog items with an AI-written name/description
# and a computed total. Offers are NOT persisted here — they live in the
# chat message's metadata and, when the user selects one, are expanded
# into simulated tickets by Rails.


@dataclass(frozen=True)
class PackItem:
    catalog_id: str
    quantity: int = 1


@dataclass
class PackOffer:
    id: str
    name: str
    description: str
    items: list[PackItem]
    lines: list[dict] = field(default_factory=list)
    total_eur: float = 0.0
    currency: str = "EUR"
    recommended: bool = False
    highlight_features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "items": [{"catalog_id": it.catalog_id, "quantity": it.quantity} for it in self.items],
            "lines": self.lines,
            "total_eur": round(self.total_eur, 2),
            "currency": self.currency,
            "recommended": self.recommended,
            "highlight_features": self.highlight_features,
        }


def build_pack_offer(
    *,
    name: str,
    description: str,
    items: Iterable[PackItem | dict],
    visit_date: Date,
    recommended: bool = False,
    highlight_features: Iterable[str] | None = None,
    offer_id: str | None = None,
) -> PackOffer:
    """Assemble a PackOffer from catalog ids + quantities.

    Each line is priced using the catalog (date-sensitive for bundles).
    Raises KeyError if an item id is unknown or quantity <= 0.
    """
    normalized: list[PackItem] = []
    for raw in items:
        if isinstance(raw, dict):
            normalized.append(PackItem(catalog_id=raw["catalog_id"], quantity=int(raw.get("quantity", 1))))
        else:
            normalized.append(raw)

    lines: list[dict] = []
    total = 0.0
    for pi in normalized:
        if pi.quantity <= 0:
            raise ValueError(f"quantity must be > 0 for {pi.catalog_id}")
        item = get_item(pi.catalog_id)
        unit_price = item.price_for_date(visit_date)
        subtotal = round(unit_price * pi.quantity, 2)
        total += subtotal
        lines.append(
            {
                "catalog_id": item.id,
                "name_fr": item.name_fr,
                "quantity": pi.quantity,
                "unit_price_eur": round(unit_price, 2),
                "subtotal_eur": subtotal,
                "category": item.category,
            }
        )

    return PackOffer(
        id=offer_id or f"offer_{uuid.uuid4().hex[:10]}",
        name=name,
        description=description,
        items=normalized,
        lines=lines,
        total_eur=round(total, 2),
        recommended=recommended,
        highlight_features=list(highlight_features or []),
    )
