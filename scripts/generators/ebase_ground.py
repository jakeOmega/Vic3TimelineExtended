"""The Extraplanetary Base's ground types: the reference the generated script matches.

Design: ``docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md``
(§ n below means that document's). Plan:
``docs/superpowers/plans/2026-11-21-extraplanetary-base-ground-types.md``.

A site is its ground type and its grade (§ 6). Each type has one mix: a level's
output of each of the basket's seven goods against the method's output at grade 0,
as a signed fraction. Each mix is normalized so that its mean over the basket,
weighted by value at base prices, is exactly zero; a site's grade is then exactly
its value-weighted mean score, and at base prices every type earns a level's base
profit (§ 6.1).

This module holds no game data of its own beyond the design's constants. The
grades come from ``gen_solar_sites.SITES``. Nothing here reads a file at import.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_solar_sites as gss  # noqa: E402

# --- § 6 and § 7: goods, types, the basket -----------------------------------------

# The basket's seven goods, in this order everywhere (plan, Global Constraints):
# Structural Metals, Tech-Critical Metals, Gold, Conductive Metals, Base Metals,
# Chemical and Industrial Minerals, Glass and Plastics.
GOODS: tuple[str, ...] = ("iron", "tech_metals", "gold", "copper", "lead", "sulfur", "glass")

# Their base prices (the goods files' `cost`; test_ebase_ground holds them in step).
BASE_PRICE: dict[str, int] = {
    "iron": 40, "tech_metals": 80, "gold": 100, "copper": 40, "lead": 40, "sulfur": 50, "glass": 40,
}

# The seven ground types (§ 6.2), in this order everywhere. Mixed is the reference:
# the basket as it comes.
TYPES: tuple[str, ...] = ("mixed", "metallic", "rocky", "carbonaceous", "sulfurous", "hydrocarbon", "icy")

# Each type's composition, a factor of the basket before normalization, in GOODS order
# (§ 6.1: a rounded version of the average of the first draft's rows for its sites).
# mix() normalizes it to a value-weighted mean of exactly zero.
_COMPOSITION_ROWS: dict[str, tuple[float, ...]] = {
    "mixed": (1, 1, 1, 1, 1, 1, 1),
    "metallic": (1.2, 1.1, 1.4, 1.2, 1.0, 0.3, 0.1),
    "rocky": (1.3, 1.0, 0.5, 0.85, 0.85, 1.1, 1.4),
    "carbonaceous": (0.8, 0.9, 0.65, 0.9, 0.9, 2.0, 2.1),
    "sulfurous": (0.8, 0.85, 0.6, 1.0, 1.0, 4.0, 1.2),
    "hydrocarbon": (0.75, 0.85, 0.5, 0.8, 0.8, 1.8, 3.5),
    "icy": (1.0, 0.95, 0.6, 0.9, 0.9, 1.6, 1.8),
}
COMPOSITION: dict[str, dict[str, float]] = {
    t: dict(zip(GOODS, map(float, row), strict=True)) for t, row in _COMPOSITION_ROWS.items()
}

# Each place's ground type (§ 6.3). `near_earth` is the near-Earth asteroids, the one
# place that is no colony (room 10 at grade 0 with Asteroid Mining).
_SITES_BY_TYPE: dict[str, tuple[str, ...]] = {
    "mixed": ("near_earth",),
    "metallic": ("psyche",),
    "rocky": ("vesta", "valles_marineris", "olympus_mons", "hellas_planitia", "mercury", "tranquility",
              "marius_hills", "daedalus", "imbrium"),
    "carbonaceous": ("ceres", "pallas", "hygiea", "himalia", "callisto", "enceladus"),
    "sulfurous": ("amalthea", "io", "europa", "venus"),
    "hydrocarbon": ("titan", "iapetus", "pluto", "makemake", "sedna"),
    "icy": ("utopia_planitia", "arcadia_planitia", "shackleton", "peary", "ganymede", "rhea", "mimas",
            "titania", "oberon", "miranda", "ariel", "triton", "proteus", "eris", "haumea"),
}
GROUND: dict[str, str] = {place: t for t, places in _SITES_BY_TYPE.items() for place in places}

# The 41 places: the near-Earth asteroids (index 0), then the 40 sites in Site.index
# order (1 to 40). A place's position here is its index in the script.
NEAR_EARTH = "near_earth"
PLACES: tuple[str, ...] = (NEAR_EARTH, *(s.key for s in sorted(gss.SITES, key=lambda s: s.index)))

# The basket (§ 7): the Asteroid Mine's outputs a level. The four mining methods share
# its value shares; Regolith Processing's, the Mining Colony's and Self-Replicating
# Miners' are it scaled.
BASKET: dict[str, float] = {
    "iron": 250, "tech_metals": 175, "gold": 50, "copper": 95, "lead": 10, "sulfur": 25, "glass": 70,
}

# Levels past all of the room work at this grade and count as Mixed (§ 8.6).
OVERFLOW_GRADE: float = gss.OVERFLOW_GRADE / 100

_SITE_GRADE: dict[str, float] = {s.key: s.ebase_grade / 100 for s in gss.SITES}


def shares(outputs: dict[str, float]) -> dict[str, float]:
    """Each good's share of the outputs' value at base prices (fractions summing to 1).
    Goods outside the seven are priced from the goods files."""
    values = {g: qty * good_base_price(g) for g, qty in outputs.items()}
    total = sum(values.values())
    return {g: v / total for g, v in values.items()}


def mix(type_: str) -> dict[str, float]:
    """The type's mix (§ 6.1): a level's output of each good against the method's at
    grade 0, a signed fraction. The composition divided by its value-weighted mean over
    the basket, less one, so the mix's own value-weighted mean is exactly zero."""
    composition = COMPOSITION[type_]
    basket = shares(BASKET)
    mean = sum(basket[g] * composition[g] for g in GOODS)
    return {g: composition[g] / mean - 1 for g in GOODS}


def grade(place: str) -> float:
    """The place's grade as a fraction (§ 4): the throughput its levels work at.
    The near-Earth asteroids are 0."""
    return 0.0 if place == NEAR_EARTH else _SITE_GRADE[place]


def score(place: str, good: str) -> float:
    """A level's output of `good` at `place` against the method's at grade 0 (§ 6.1):
    (1 + grade)(1 + mix) - 1."""
    return (1 + grade(place)) * (1 + mix(GROUND[place])[good]) - 1


# --- Prices -----------------------------------------------------------------------

_PRICES: dict[str, float] | None = None


def good_base_price(good: str) -> float:
    """A good's base price: BASE_PRICE for the seven, the goods files for any other
    (the inputs, the Resort Colony's goods), read once on first use, as pm_costs
    prices the cost comments."""
    if good in BASE_PRICE:
        return BASE_PRICE[good]
    global _PRICES
    if _PRICES is None:
        import pm_costs

        _PRICES = pm_costs.load_goods()
    return _PRICES[good]
