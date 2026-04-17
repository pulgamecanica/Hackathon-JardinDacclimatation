"""In-memory fixtures for the Jardin d'Acclimatation park status.

No database. The MCP server and the AI orchestrator both import this
module so they stay in lock-step. Prices live in the tickets catalog;
this module owns *operational* facts: hours, attractions, events.

Determinism matters: the agent may call these tools repeatedly for the
same date and must get the same answer. Wait times are pseudo-random
but seeded by (attraction_id, date), so they're stable per day.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date as Date
from typing import Iterable, Literal


# ── French public holidays (subset relevant to 2026) ───────────────
# Duplicated from the tickets catalog so this module is self-contained.
# If these ever drift, the integration tests in the orchestrator will
# catch mismatched expectations.
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
    return d.weekday() >= 5 or d in _PUBLIC_HOLIDAYS_2026


# ── Park hours ─────────────────────────────────────────────────────
# The Jardin is open every day; hours differ weekday vs weekend/holiday.
# Last entry is 1 hour before closing.

@dataclass(frozen=True)
class ParkHours:
    date: Date
    is_open: bool
    opening_time: str        # "HH:MM"
    closing_time: str        # "HH:MM"
    last_entry_time: str     # "HH:MM"
    is_weekend_or_holiday: bool
    notes_fr: str | None = None

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "is_open": self.is_open,
            "opening_time": self.opening_time,
            "closing_time": self.closing_time,
            "last_entry_time": self.last_entry_time,
            "is_weekend_or_holiday": self.is_weekend_or_holiday,
            "notes_fr": self.notes_fr,
        }


def get_park_hours(d: Date) -> ParkHours:
    """Return opening hours for a given date. The park is always open."""
    weekend = is_weekend_or_holiday(d)
    if weekend:
        opening, closing, last_entry = "10:00", "20:00", "19:00"
        notes = "Horaires étendus — week-end ou jour férié."
    else:
        opening, closing, last_entry = "11:00", "19:00", "18:00"
        notes = None
    return ParkHours(
        date=d,
        is_open=True,
        opening_time=opening,
        closing_time=closing,
        last_entry_time=last_entry,
        is_weekend_or_holiday=weekend,
        notes_fr=notes,
    )


# ── Attractions ────────────────────────────────────────────────────

Zone = Literal["ferme", "centrale", "bois", "sensations", "tour", "spectacle", "atelier"]
Thrill = Literal["calme", "douce", "intense"]


@dataclass(frozen=True)
class Attraction:
    id: str
    name_fr: str
    description_fr: str
    zone: Zone
    min_height_cm: int | None
    age_min: int | None
    thrill_level: Thrill
    avg_wait_min: int
    accessible_wheelchair: bool
    notes_fr: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name_fr": self.name_fr,
            "description_fr": self.description_fr,
            "zone": self.zone,
            "min_height_cm": self.min_height_cm,
            "age_min": self.age_min,
            "thrill_level": self.thrill_level,
            "avg_wait_min": self.avg_wait_min,
            "accessible_wheelchair": self.accessible_wheelchair,
            "notes_fr": self.notes_fr,
        }


ATTRACTIONS: tuple[Attraction, ...] = (
    Attraction(
        id="ferme_aux_animaux",
        name_fr="La Ferme aux Animaux",
        description_fr="Rencontre avec chèvres, moutons, poneys et poules. Parfait pour les tout-petits.",
        zone="ferme",
        min_height_cm=None,
        age_min=None,
        thrill_level="calme",
        avg_wait_min=0,
        accessible_wheelchair=True,
    ),
    Attraction(
        id="grand_carrousel",
        name_fr="Le Grand Carrousel 1900",
        description_fr="Carrousel historique à deux étages, chevaux de bois peints à la main.",
        zone="centrale",
        min_height_cm=None,
        age_min=2,
        thrill_level="calme",
        avg_wait_min=10,
        accessible_wheelchair=False,
        notes_fr="Les enfants de moins de 4 ans doivent être accompagnés.",
    ),
    Attraction(
        id="riviere_enchantee",
        name_fr="La Rivière Enchantée",
        description_fr="Balade en barque à travers des décors féériques. Idéal en famille.",
        zone="bois",
        min_height_cm=None,
        age_min=None,
        thrill_level="douce",
        avg_wait_min=15,
        accessible_wheelchair=False,
    ),
    Attraction(
        id="speed_rockets",
        name_fr="Speed Rockets",
        description_fr="Fusées tournoyantes à sensations — accélérations et vrilles.",
        zone="sensations",
        min_height_cm=120,
        age_min=6,
        thrill_level="intense",
        avg_wait_min=20,
        accessible_wheelchair=False,
    ),
    Attraction(
        id="dragon_chinois",
        name_fr="Le Dragon Chinois",
        description_fr="Montagnes russes familiales serpentant autour d'un dragon géant.",
        zone="sensations",
        min_height_cm=125,
        age_min=7,
        thrill_level="intense",
        avg_wait_min=25,
        accessible_wheelchair=False,
    ),
    Attraction(
        id="kid_coaster",
        name_fr="Kid Coaster",
        description_fr="Mini-coaster conçu pour les jeunes enfants — douces sensations garanties.",
        zone="centrale",
        min_height_cm=105,
        age_min=4,
        thrill_level="douce",
        avg_wait_min=12,
        accessible_wheelchair=False,
    ),
    Attraction(
        id="monorail",
        name_fr="Le Petit Train",
        description_fr="Tour panoramique du Jardin en train sur rail suspendu.",
        zone="tour",
        min_height_cm=None,
        age_min=None,
        thrill_level="calme",
        avg_wait_min=8,
        accessible_wheelchair=True,
    ),
    Attraction(
        id="foret_enchantee",
        name_fr="La Forêt Enchantée",
        description_fr="Parcours à pied jalonné de personnages animés et d'énigmes pour les enfants.",
        zone="bois",
        min_height_cm=None,
        age_min=None,
        thrill_level="calme",
        avg_wait_min=0,
        accessible_wheelchair=True,
    ),
    Attraction(
        id="miroirs_magiques",
        name_fr="Les Miroirs Magiques",
        description_fr="Labyrinthe de miroirs déformants. Surprises garanties.",
        zone="centrale",
        min_height_cm=None,
        age_min=None,
        thrill_level="calme",
        avg_wait_min=5,
        accessible_wheelchair=False,
    ),
    Attraction(
        id="tapis_volant",
        name_fr="Le Tapis Volant",
        description_fr="Envol au-dessus des arbres sur un tapis volant basculant.",
        zone="centrale",
        min_height_cm=95,
        age_min=3,
        thrill_level="douce",
        avg_wait_min=10,
        accessible_wheelchair=False,
    ),
)

_ATTRACTIONS_BY_ID: dict[str, Attraction] = {a.id: a for a in ATTRACTIONS}


def get_attraction(attraction_id: str) -> Attraction:
    if attraction_id not in _ATTRACTIONS_BY_ID:
        raise KeyError(f"Unknown attraction: {attraction_id}")
    return _ATTRACTIONS_BY_ID[attraction_id]


def list_attractions(zone: Zone | None = None) -> list[Attraction]:
    if zone is None:
        return list(ATTRACTIONS)
    return [a for a in ATTRACTIONS if a.zone == zone]


# ── Attraction status (fake but deterministic) ─────────────────────

# Pre-planned maintenance windows. Keeps test expectations stable.
_MAINTENANCE: frozenset[tuple[str, Date]] = frozenset(
    {
        ("dragon_chinois", Date(2026, 4, 20)),  # Monday
        ("speed_rockets", Date(2026, 5, 4)),    # Monday
    }
)


AttractionStatus = Literal["open", "maintenance", "closed"]


@dataclass(frozen=True)
class AttractionStatusSnapshot:
    attraction_id: str
    date: Date
    status: AttractionStatus
    current_wait_min: int
    note_fr: str | None = None

    def to_dict(self) -> dict:
        return {
            "attraction_id": self.attraction_id,
            "date": self.date.isoformat(),
            "status": self.status,
            "current_wait_min": self.current_wait_min,
            "note_fr": self.note_fr,
        }


def get_attraction_status(attraction_id: str, d: Date) -> AttractionStatusSnapshot:
    """Return status + wait time for one attraction on a given date.

    Waits are pseudo-random around the attraction's avg_wait_min, seeded
    by (id, date). Maintenance windows are pre-declared in _MAINTENANCE.
    """
    attraction = get_attraction(attraction_id)

    if (attraction_id, d) in _MAINTENANCE:
        return AttractionStatusSnapshot(
            attraction_id=attraction_id,
            date=d,
            status="maintenance",
            current_wait_min=0,
            note_fr="Fermée pour maintenance planifiée.",
        )

    # Deterministic jitter: ±40% of avg wait, tied to (id, date).
    wait = _jitter_wait(attraction_id, d, attraction.avg_wait_min)
    return AttractionStatusSnapshot(
        attraction_id=attraction_id,
        date=d,
        status="open",
        current_wait_min=wait,
    )


def _jitter_wait(attraction_id: str, d: Date, avg: int) -> int:
    if avg <= 0:
        return 0
    seed = f"{attraction_id}|{d.isoformat()}".encode()
    # Take 4 bytes of a hash → int → map to [-40%, +40%]
    digest = hashlib.sha256(seed).digest()
    n = int.from_bytes(digest[:4], "big")
    bucket = (n % 81) - 40  # -40..+40
    multiplier = 1.0 + bucket / 100.0
    jittered = round(avg * multiplier)
    return max(0, jittered)


# ── Events (shows, ateliers, parades) ─────────────────────────────

@dataclass(frozen=True)
class Event:
    id: str
    name_fr: str
    description_fr: str
    zone: str
    start_time: str          # "HH:MM"
    end_time: str            # "HH:MM"
    audience_fr: str
    weekdays_only: bool = False
    weekends_only: bool = False

    def is_scheduled_on(self, d: Date) -> bool:
        weekend = is_weekend_or_holiday(d)
        if self.weekdays_only and weekend:
            return False
        if self.weekends_only and not weekend:
            return False
        return True

    def to_dict(self, d: Date) -> dict:
        return {
            "id": self.id,
            "name_fr": self.name_fr,
            "description_fr": self.description_fr,
            "zone": self.zone,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "audience_fr": self.audience_fr,
            "date": d.isoformat(),
        }


EVENTS: tuple[Event, ...] = (
    Event(
        id="parade_animaux",
        name_fr="La Parade des Animaux",
        description_fr="Défilé des personnages costumés sur l'allée centrale.",
        zone="allée centrale",
        start_time="15:00",
        end_time="15:45",
        audience_fr="Tout public",
    ),
    Event(
        id="clowns_poetiques_apres_midi",
        name_fr="Les Clowns Poétiques",
        description_fr="Spectacle de clownerie et poésie visuelle.",
        zone="théâtre du Jardin",
        start_time="14:00",
        end_time="14:45",
        audience_fr="Famille, dès 4 ans",
    ),
    Event(
        id="clowns_poetiques_goûter",
        name_fr="Les Clowns Poétiques (séance goûter)",
        description_fr="Seconde représentation du spectacle de clownerie.",
        zone="théâtre du Jardin",
        start_time="16:30",
        end_time="17:15",
        audience_fr="Famille, dès 4 ans",
    ),
    Event(
        id="atelier_masques",
        name_fr="Atelier Masques de printemps",
        description_fr="Atelier créatif — fabrication d'un masque à ramener à la maison.",
        zone="atelier des Créateurs",
        start_time="11:00",
        end_time="12:00",
        audience_fr="Enfants 5-10 ans",
    ),
    Event(
        id="atelier_masques_aprem",
        name_fr="Atelier Masques de printemps (après-midi)",
        description_fr="Seconde session de l'atelier créatif.",
        zone="atelier des Créateurs",
        start_time="14:00",
        end_time="15:00",
        audience_fr="Enfants 5-10 ans",
    ),
    Event(
        id="projection_pavo_etoiles",
        name_fr="Projection — Pavo et les étoiles",
        description_fr="Court métrage d'animation autour de Pavo et ses amis.",
        zone="cinéma du Jardin",
        start_time="17:00",
        end_time="17:30",
        audience_fr="Famille",
    ),
    Event(
        id="concert_jardin_dimanche",
        name_fr="Concert du Jardin",
        description_fr="Musique acoustique en plein air, près du Grand Carrousel.",
        zone="allée centrale",
        start_time="16:00",
        end_time="16:45",
        audience_fr="Tout public",
        weekends_only=True,
    ),
)


def list_events(d: Date) -> list[Event]:
    """Return the day's events (filtered by weekday/weekend scheduling)."""
    return [e for e in EVENTS if e.is_scheduled_on(d)]


def filter_attractions(
    *,
    max_wait_min: int | None = None,
    thrill_level: Thrill | None = None,
    min_height_cm_lt: int | None = None,
    accessible_wheelchair: bool | None = None,
    source: Iterable[Attraction] | None = None,
) -> list[Attraction]:
    """Helper for agents: narrow the attraction list by operational filters.

    Not exposed directly via MCP — agents pre-fetch attractions and filter
    in-process. Kept here so the orchestrator and the MCP server share
    identical filtering semantics.
    """
    pool = list(source) if source is not None else list(ATTRACTIONS)
    if max_wait_min is not None:
        pool = [a for a in pool if a.avg_wait_min <= max_wait_min]
    if thrill_level is not None:
        pool = [a for a in pool if a.thrill_level == thrill_level]
    if min_height_cm_lt is not None:
        pool = [
            a
            for a in pool
            if a.min_height_cm is None or a.min_height_cm < min_height_cm_lt
        ]
    if accessible_wheelchair is not None:
        pool = [a for a in pool if a.accessible_wheelchair == accessible_wheelchair]
    return pool
