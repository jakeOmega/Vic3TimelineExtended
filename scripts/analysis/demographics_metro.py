#!/usr/bin/env python3
"""The metropolitan share (spec §5.2): its target, drift, label and effects, as the script's Python twin.

docs/superpowers/specs/2026-10-08-demographics-design.md §5.2: a state's metropolitan share, 0-100, is the share of its
urban people living in its largest city. A Victoria state has one city hub and no cities below it, so the share is a
modelled stock: it starts at its target and moves MT_DRIFT of the way there each year. The script is
common/script_values/te_demog_metro_values.txt and common/scripted_effects/te_demog_metro_effects.txt; the constants are
demographics_params.py's MT_* block, which test_demographics_metro.py pins the script's te_demog_k_mt_* to.

The target is MT_BASE plus eight terms in share points (the owner's list, 2026-10-19), within MT_MIN..MT_MAX:

    capital      +MT_CAPITAL in the national capital
    gateway      +MT_HUB in a World Market Hub, +MT_FINANCE_PER_LEVEL a Financial District level (to MT_FINANCE_MAX)
    area         -MT_AREA_STEP a doubling of the region's area past MT_AREA_FREE km2, MT_AREA_DOUBLINGS at most
    work         -MT_WORK x the rural share (the walk's farm, mine and forest people, Peasants counted rural)
    urban        the inverted U on the owner's national urban share: MT_URBAN_SIZE at half, 0 at 10% and 90%
    infra        -MT_INFRA x the infrastructure surplus over usage, as a share of usage within 0-1
    crowding     -MT_CROWD x Migration Crowding's applied multiplier over its ceiling, within 0-1
    planning     the Ministry of Urban Planning's type, Planned Towns' levels and a Planned Capital, MT_PLAN_MIN..0

    demographics_metro.py                    # the anchors: 1836 and today, the label each reads
"""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_params as P  # noqa: E402

LABELS = ("Metropolis", "Leading City", "Several Cities", "Market Towns")
TERMS = ("capital", "gateway", "area", "work", "urban", "infra", "crowding", "planning")


@dataclass
class Place:
    """What the target reads for one state. urban_share is the state's walk (te_dg_urban_share); national its owner's
    census figure (the state's own when the owner has none yet); infra_surplus the surplus over usage as a share of
    usage (may be negative: a shortfall reads 0); crowding Migration Crowding's applied multiplier (0 when off)."""
    urban_share: float
    national: float
    capital: bool = False
    hub: bool = False
    finance_levels: int = 0
    area: float = 0.0
    infra_surplus: float = 0.0
    crowding: float = 0.0
    ministry_levels: int = 0
    planned_towns_levels: int = 0
    planned_capital: bool = False


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def area_term(area):
    """-MT_AREA_STEP a doubling past MT_AREA_FREE, linear within each doubling (the script's ladder), at most
    MT_AREA_DOUBLINGS doublings."""
    free, step = P.MT_AREA_FREE, P.MT_AREA_STEP
    if area <= free:
        return 0.0
    lo = free
    for k in range(P.MT_AREA_DOUBLINGS):
        hi = lo * 2
        if area <= hi:
            return -step * (k + (area - lo) / lo)
        lo = hi
    return -step * P.MT_AREA_DOUBLINGS


def urban_term(national):
    x = (national - P.MT_URBAN_PEAK) / P.MT_URBAN_WIDTH
    return max(-P.MT_URBAN_SIZE, P.MT_URBAN_SIZE * (1 - x * x))


def terms(pl):
    """Each term in share points, in TERMS order."""
    gateway = (P.MT_HUB if pl.hub else 0) + min(P.MT_FINANCE_MAX, P.MT_FINANCE_PER_LEVEL * pl.finance_levels)
    planning = (P.MT_MINISTRY_PER_LEVEL * pl.ministry_levels + P.MT_PLANNED_TOWNS_PER_LEVEL * pl.planned_towns_levels
                + (P.MT_PLANNED_CAPITAL if pl.planned_capital else 0))
    return {
        "capital": P.MT_CAPITAL if pl.capital else 0.0,
        "gateway": float(gateway),
        "area": area_term(pl.area),
        "work": -P.MT_WORK * (1 - clamp(pl.urban_share, 0.0, 1.0)),
        "urban": urban_term(pl.national),
        "infra": -P.MT_INFRA * clamp(pl.infra_surplus, 0.0, 1.0),
        "crowding": -P.MT_CROWD * clamp(pl.crowding / P.MT_CROWD_CEILING, 0.0, 1.0),
        "planning": clamp(planning, P.MT_PLAN_MIN, 0.0),
    }


def target(pl):
    return clamp(P.MT_BASE + sum(terms(pl).values()), P.MT_MIN, P.MT_MAX)


def step(share, tgt):
    """One year's drift: MT_DRIFT of the way to the target (te_demog_mt_state_update)."""
    return share + P.MT_DRIFT * (tgt - share)


def label(share):
    """0 Metropolis, 1 Leading City, 2 Several Cities, 3 Market Towns (te_demog_mt_label)."""
    for code, floor in enumerate(P.MT_LABELS):
        if share >= floor:
            return code
    return len(P.MT_LABELS)


def concentrated(share):
    """The concentrated side's strength, 0-1: nothing at MT_EFFECT_FROM, full at MT_EFFECT_FULL (te_demog_mt_e_pos)."""
    return clamp((share - P.MT_EFFECT_FROM) / (P.MT_EFFECT_FULL - P.MT_EFFECT_FROM), 0.0, 1.0)


def dispersed(share):
    """The dispersed side's strength, 0-1: nothing at MT_DISPERSED_FROM, full at MT_DISPERSED_FULL
    (te_demog_mt_e_neg)."""
    return clamp((P.MT_DISPERSED_FROM - share) / (P.MT_DISPERSED_FROM - P.MT_DISPERSED_FULL), 0.0, 1.0)


def effects(share):
    """The modifier fields a state carries under Full at this share: the concentrated side's or the dispersed side's
    full sizes x its strength (the two never overlap)."""
    c, d = concentrated(share), dispersed(share)
    if c > 0:
        return {k: v * c for k, v in P.MT_EFFECTS.items()}
    if d > 0:
        return {k: v * d for k, v in P.MT_DISPERSED_EFFECTS.items()}
    return {}


def fertility_scale(share):
    """The census's urban term's scale under Full (te_demog_mt_fertility_scale): 1 + MT_FERTILITY x the concentrated
    side's strength."""
    return 1 + P.MT_FERTILITY * concentrated(share)


# ---- The anchors (my call, 2026-10-19: reasoned from the walk's inputs; no save holds the census with this measure) --
# Each: (name, Place, the label it should read). The inputs are plausible walk figures: Britain's 1836 urban share by
# the walk's rule is about half (the harness's 0.48), an agrarian country's 10-35%, a rich one's today 85-95%.
ANCHORS = [
    ("Ile-de-France 1836 (Paris)", Place(0.60, 0.35, capital=True, area=12296, infra_surplus=0.3), 0),
    ("Home Counties 1836 (London)", Place(0.80, 0.48, capital=True, hub=True, area=20544, infra_surplus=0.3), 0),
    ("Buenos Aires 1836", Place(0.30, 0.25, capital=True, hub=True, area=271699, infra_surplus=0.3), 0),
    ("New York 1836", Place(0.40, 0.30, hub=True, area=128255, infra_surplus=0.3), 1),
    ("Rhineland 1836", Place(0.35, 0.30, area=13620, infra_surplus=0.3), 2),
    ("Brittany 1836", Place(0.25, 0.35, area=27000, infra_surplus=0.3), 2),
    ("An agrarian Russian province 1836", Place(0.10, 0.12, area=25000, infra_surplus=0.5), 3),
    ("Texas 1836", Place(0.10, 0.20, area=536486, infra_surplus=0.5), 3),
    ("Ile-de-France today", Place(0.95, 0.85, capital=True, finance_levels=10, area=12296, infra_surplus=0.5,
                                  crowding=4.5, ministry_levels=5), 0),
    ("New York today", Place(0.95, 0.85, hub=True, finance_levels=10, area=128255, infra_surplus=0.5, crowding=2.0,
                             ministry_levels=5), 0),
    ("Buenos Aires today", Place(0.95, 0.90, capital=True, hub=True, finance_levels=10, area=271699,
                                 infra_surplus=0.5, crowding=4.5, ministry_levels=3), 0),
    ("Texas today", Place(0.95, 0.85, finance_levels=5, area=536486, infra_surplus=0.5), 2),
    ("Rhineland today", Place(0.95, 0.85, finance_levels=5, area=13620, infra_surplus=0.5, crowding=4.5,
                              ministry_levels=5), 2),
    ("Saxony (Prussian) today", Place(0.95, 0.85, finance_levels=3, area=27589, infra_surplus=0.5), 2),
]


def report():
    """Print each anchor's terms, target and label; return 0 when every anchor reads its label."""
    bad = 0
    print(f"{'state':38s} {'target':>6s}  label           " + " ".join(f"{t:>8s}" for t in TERMS))
    for name, pl, want in ANCHORS:
        t = terms(pl)
        tg = target(pl)
        got = label(tg)
        bad |= got != want
        flag = "" if got == want else f"  (wanted {LABELS[want]})"
        print(f"{name:38s} {tg:6.1f}  {LABELS[got]:15s} " + " ".join(f"{t[k]:+8.1f}" for k in TERMS) + flag)
    return bad


if __name__ == "__main__":
    sys.exit(report())
