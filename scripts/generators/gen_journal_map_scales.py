#!/usr/bin/env python3
"""Write the Map Room's color scales and the effects that fit them to the world.

Each map in je_te_map_room (common/journal_entries/te_journal_maps.txt) colors a state by a factor, 0 to 1, read from
one of the state's figures. Two files come from the table below:

- common/script_values/te_journal_map_scales_generated.txt: each map's factor, te_jmap_<map>_factor, and for a map
  fitted to the world the script values its curve is drawn through;
- common/scripted_effects/te_journal_map_ranges_generated.txt: the effects that measure the world for a map
  (te_jmap_range_<map>), the dispatcher a pick and the monthly pulse run (te_jmap_refresh_range, on the pick in
  te_jmap_selector) and the maps the systems' own entries draw whatever the pick (te_jmap_refresh_entry_ranges).

**Fitted to the world** (owner, 2026-11-07: "people are not going to it to see that the world GDP/c average has gone
up, they want to see the regional differences"). Nearly every map's colors run from the world's low to its high as
it stands: the fifth lowest and the fifth highest of the states the map paints (TRIM states left out at each end, so
one outlier doesn't flatten the rest; the extremes where fewer states have a figure), stored in global variables
(te_jmap_rng_<map>_lo / _hi) by te_jmap_range_<map>. A pick measures its map at once, and the monthly pulse measures
the pick's again (te_journal_map_on_actions.txt). A curve keeps its shape on the new span: its knots are fractions of
it. A span is never narrower than the map's min_span, so a world where every state stands alike doesn't paint noise
as contrast. Before the first measure (an older save, a new game's first pick) a map uses its default range, the
fixed curve's ends. Shapes:

- rel(knots): a fixed curve (below) made relative: each knot at the same fraction of the world's span.
- rel_mid(knots, mid, min_half): a three-color map whose midpoint means something (replacement fertility, no natural
  change, even sexes, no comfort penalty, Dynastic Wealth's turn). Below mid the colors run from the world's low to
  mid, above it from mid to the world's high, each side on its own span (at least min_half) and keeping its shape.
  Where the whole world is on one side, that side runs over the world's span alone, from the neutral color at the end
  nearest mid, so the differences still show.
- rel_doubling(min_ratio, floor): the same share of the color per doubling from the world's low to its high (GDP per
  capita, Armed Forces, Company Headquarters, War Dead), the low at least floor and the high at least min_ratio times
  it. A doubling's position is read in straight pieces between powers of two.

Four maps stay on fixed curves: the agent networks (0-100, whose 50 and 75 are intelligence tiers), the paleness of
the leading cause of death and of Ownership's leading holder (a share on a categorical map) and City Rank (a rank is
already a place in the world; its first 20 are tourism's Cities bonus). The fixed shapes:

- linear(lo, hi): straight from lo to hi.
- soft_cap(lo, soft, hard): straight from lo to soft, then SLOPE_RATIO times shallower from soft to hard, so the
  common values get most of the color and the extremes still differ instead of all saturating at one bound.
- diverging(lower, mid, upper): 0.5 at mid, each side to its end; a side is a bound (straight) or a (soft, hard) pair
  (the soft cap's shape, mirrored below).
- doubling(lo, hi): the same share of the color for each doubling from lo to hi.

A script value takes no arguments, and a map paint can run no effect, so a shared shape can't be one script value fed
its input (te_sqrt's way, through var:te_math_in): each map gets its own tree, written here from its table row. Each
reads its figure only inside an `if` on its `has_variable` guards, since a guard in the same AND doesn't stop a read
where the engine also builds a tooltip (issue #1418). A three-color map also gets _lower (the factor doubled) and
_upper (doubled less 1), one per half; map_color splits on factor < 0.5.

Needs nothing but the repo. Re-run after changing a table; test_journal_map_scales.py fails CI when either committed
file is stale:

    python3 scripts/generators/gen_journal_map_scales.py [--check]
"""
import argparse
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "common", "script_values", "te_journal_map_scales_generated.txt")
EFFECTS_OUT = os.path.join(REPO, "common", "scripted_effects", "te_journal_map_ranges_generated.txt")

# How much shallower a soft cap's tail runs than its main stretch (the owner, 2026-11-06: "1/4 slope above").
SLOPE_RATIO = 4
# The states left out at each end of the world's range: the range runs from the (TRIM + 1)th lowest to the
# (TRIM + 1)th highest. ordered_state's position counts from 0.
TRIM = 4
# The most doublings a doubling map's ladder reads (2^20 is a millionfold).
MAX_DOUBLINGS = 20


def linear(lo, hi):
    return [(lo, 0.0), (hi, 1.0)]


def _soft_share(span, tail):
    """The color a soft cap gives its main stretch: span long at slope s, tail long at s / SLOPE_RATIO."""
    return SLOPE_RATIO * span / (SLOPE_RATIO * span + tail)


def soft_cap(lo, soft, hard):
    return [(lo, 0.0), (soft, _soft_share(soft - lo, hard - soft)), (hard, 1.0)]


def _side(mid, end):
    """[(x, p)] from mid outward, p from 0 to 1: end is a bound or a (soft, hard) pair."""
    if isinstance(end, tuple):
        soft, hard = end
        return [(mid, 0.0), (soft, _soft_share(abs(soft - mid), abs(hard - soft))), (hard, 1.0)]
    return [(mid, 0.0), (end, 1.0)]


def diverging(lower, mid, upper):
    below = [(x, 0.5 - 0.5 * p) for x, p in reversed(_side(mid, lower))]
    above = [(x, 0.5 + 0.5 * p) for x, p in _side(mid, upper)[1:]]
    return below + above


def doubling(lo, hi):
    steps = round(math.log2(hi / lo))
    if lo <= 0 or lo * 2 ** steps != hi:
        raise ValueError(f"doubling({lo}, {hi}): hi must be lo times a power of two")
    return [(lo * 2 ** k, k / steps) for k in range(steps + 1)]


# ---- shapes fitted to the world -------------------------------------------------------------------------------------

def rel(knots):
    """A fixed curve made relative: [(t, f)], t the knot's fraction of the span, and the curve's ends as the default."""
    lo, hi = knots[0][0], knots[-1][0]
    return dict(kind="frac", knots=[((x - lo) / (hi - lo), f) for x, f in knots], default=(lo, hi))


def rel_mid(knots, mid, min_half):
    """A fixed diverging curve around mid made relative, each side's knots as fractions of its own span, outward."""
    lo, hi = knots[0][0], knots[-1][0]
    lower = [((mid - x) / (mid - lo), (0.5 - f) / 0.5) for x, f in reversed(knots) if x <= mid]
    upper = [((x - mid) / (hi - mid), (f - 0.5) / 0.5) for x, f in knots if x >= mid]
    return dict(kind="mid", mid=mid, lower=lower, upper=upper, min_half=min_half, default=(lo, hi))


def rel_doubling(lo, hi, min_ratio, floor):
    return dict(kind="doubling", min_ratio=min_ratio, floor=floor, default=(lo, hi))


# name: te_jmap_<name>_factor. input: what the tree reads (a figure, or a script value of the state's).
# guards: variables the input needs (read only once they exist). three: the map has three colors (_lower, _upper).
# A map fitted to the world also has sel (its selector, te_journal_map_values.txt), where (the states it paints with
# its factor, whose figures make its range), world (its shape), min_span (the narrowest range, in the figure's units;
# a doubling's is its min_ratio), and fmt (the pick tooltip's number format, for the doc and the loc test); range_of
# names a map whose range it shares, entry marks a map a system's own entry draws too (refreshed every month).
# A fixed map has knots.
SCALES = [
    dict(name="turmoil", input="turmoil", guards=[], three=False, sel=1, where=[],
         world=rel(soft_cap(0, 0.2, 1)), min_span=0.1,
         note="Turmoil, the radicals' share: half the color by a fifth of the world's range, the rest more slowly"),
    dict(name="devastation", input="devastation", guards=[], three=False, sel=6, where=[],
         world=rel(soft_cap(0, 0.2, 1)), min_span=0.1,
         note="Devastation, a 0-1 share as turmoil is (te_demog_crisis reads it bare): half the color by a fifth of "
              "the world's range"),
    dict(name="urban", input="var:te_dg_urban_share", guards=["te_dg_urban_share"], three=False, sel=15,
         where=["has_variable = te_dg_urban_share"], world=rel(linear(0, 1)), min_span=0.1,
         note="The urban share, the people not at a rural workplace (the yearly walk's)"),
    dict(name="gini", input="var:te_dg_gini", guards=["te_dg_gini"], three=False, sel=16,
         where=["has_variable = te_dg_gini"], world=rel(linear(0.3, 0.8)), min_span=0.1,
         note="The state's shown Gini (the yearly walk's, 0.3-1); Britain in 1836 about 0.55"),
    dict(name="wc", input="var:te_dg_wc", guards=["te_dg_wc"], three=True, sel=17, where=["has_variable = te_dg_wc"],
         world=rel_mid(diverging(0, 50, 100), 50, 10), min_span=10,
         note="Dynastic Wealth, the state's score, split at 50, where its effects turn from dispersed to "
              "concentrated property"),
    dict(name="e0", input="var:te_dg_e0", guards=["te_dg_e0"], three=True, sel=3,
         where=["has_variable = te_dg_e0", "var:te_dg_e0 > 0"], world=rel(linear(25, 80)), min_span=10,
         note="Life expectancy at birth, split at the middle of the world's range"),
    dict(name="imr", input="var:te_dg_imr", guards=["te_dg_imr"], three=True, sel=10,
         where=["has_variable = te_dg_imr", "has_variable = te_dg_e0", "var:te_dg_e0 > 0"],
         world=rel(linear(0, 300)), min_span=20,
         note="Infant mortality per 1,000 births, split at the middle of the world's range; 300 an 1836 state's worst"),
    dict(name="tfr", input="var:te_dg_tfr", guards=["te_dg_tfr"], three=True, sel=4,
         where=["has_variable = te_dg_tfr", "var:te_dg_tfr > 0"],
         world=rel_mid(diverging(1, 2.1, 6.5), 2.1, 0.5), min_span=0.5,
         note="Fertility, children a woman, split at replacement (2.1)"),
    dict(name="median", input="var:te_dg_median", guards=["te_dg_median"], three=True, sel=5,
         where=["has_variable = te_dg_median", "var:te_dg_median > 0"], world=rel(linear(15, 45)), min_span=5,
         note="Median age, split at the middle of the world's range"),
    dict(name="natural", input="te_demog_natural_change", guards=["te_dg_cbr", "te_dg_cdr"], three=True, sel=7,
         where=["has_variable = te_dg_stepped", "var:te_dg_stepped > 0", "has_variable = te_dg_cbr",
                "has_variable = te_dg_cdr"],
         world=rel_mid(diverging((-15, -40), 0, (30, 45)), 0, 5), min_span=5,
         note="Natural change per 1,000 people last year, split at none; famine and war run far below"),
    dict(name="cdr", input="var:te_dg_cdr", guards=["te_dg_cdr"], three=False, sel=8,
         where=["has_variable = te_dg_stepped", "var:te_dg_stepped > 0", "has_variable = te_dg_cdr"],
         world=rel(soft_cap(5, 40, 100)), min_span=5,
         note="Deaths per 1,000 people last year, 70% of the color by 37% of the world's range; famine and war run "
              "far above"),
    dict(name="cbr", input="var:te_dg_cbr", guards=["te_dg_cbr"], three=False, sel=9,
         where=["has_variable = te_dg_stepped", "var:te_dg_stepped > 0", "has_variable = te_dg_cbr"],
         world=rel(linear(8, 50)), min_span=5, note="Births per 1,000 people last year"),
    dict(name="old", input="var:te_dg_old_share", guards=["te_dg_old_share"], three=False, sel=14,
         where=["has_variable = te_dg_old_share", "has_variable = te_dg_median", "var:te_dg_median > 0"],
         world=rel(linear(0.02, 0.3)), min_span=0.05,
         note="The share aged 65 and over (an 1836 state 3-5%, the oldest today near 30%)"),
    dict(name="sex", input="var:te_dg_sex_balance", guards=["te_dg_sex_balance"], three=True, sel=12,
         where=["has_variable = te_dg_sex_balance", "var:te_dg_sex_balance > 0"],
         world=rel_mid(diverging(80, 100, 130), 100, 5), min_span=5,
         note="Sex balance, men per 100 women aged 20-59, split at 100"),
    dict(name="mig", input="var:te_dg_mig_rate", guards=["te_dg_mig_rate"], three=True, sel=13,
         where=["has_variable = te_dg_stepped", "var:te_dg_stepped > 0", "has_variable = te_dg_mig_rate"],
         world=rel_mid(diverging((-20, -60), 0, (20, 60)), 0, 5), min_span=5,
         note="Net migration per 1,000 people last year, split at none"),
    dict(name="cause", input="te_demog_dc_lead_share", guards=["te_dg_dc_total", "te_dg_dc_lead"], three=False,
         knots=linear(0.3, 0.9),
         note="The leading cause of death's share of last year's deaths, its color pale at 30% and full at 90%: with "
              "seven causes the lead takes at least a seventh, and states ran 31-97% in 1838, 1940 and 2020 saves. "
              "Fixed: the map is categorical, and this only fades each cause's color"),
    # The systems' maps, each on its own entry too (te_journal_map_triggers.txt).
    dict(name="gw", input="te_jmap_gw_share", guards=["gw_state_emis"], three=False, sel=18, entry=True,
         where=["has_variable = gw_state_emis", "te_jmap_gw_world > 0", "te_jmap_gw_state_emis >= 0"],
         world=rel(soft_cap(0, 0.01, 0.05)), min_span=0.005,
         note="Global Warming: the state's share of the world's emissions last year (a share, owner 2026-11-06): "
              "half the color by a fifth of the world's range; a thousand-odd states average 0.1%"),
    dict(name="net", input="te_jmap_net_strength", guards=[], three=False, knots=linear(0, 100),
         note="Covert Warfare: the viewer's network in the state's owner, 0-100 (intel tiers at 50 and 75). Fixed: "
              "the tiers are what the map shows"),
    dict(name="gm", input="gm_state_grandeur", guards=[], three=False, sel=24, entry=True,
         where=["te_jmap_gm_monument = yes"], world=rel(soft_cap(0, 75, 225)), min_span=25,
         note="Grand Monuments: the state's grandeur, two-thirds of the color by a third of the world's range"),
    # The Map Room's own again.
    dict(name="tourism", input="var:te_tourism_base_appeal", guards=["te_tourism_base_appeal"], three=False, sel=26,
         where=["has_variable = te_tourism_base_appeal"], world=rel(linear(0.2, 1)), min_span=0.1,
         note="Tourism's Base Appeal, the state panel's row, 0-1 (stored monthly by te_update_tourism_modifier); 0.2 "
              "is the score of a region the table doesn't list"),
    # Local Climate's comfort penalty, in percent of migration attraction: one range for both maps (Base Comfort's,
    # which holds the larger penalties), so a color means the same before and after the owner's technologies.
    # Negative is a mild or sunny winter's bonus, at most 10.8 (7.2 for mildness and 3.6 for sunshine).
    dict(name="comfort_base", input="var:te_climate_base_penalty", guards=["te_climate_base_penalty"], three=True,
         sel=27, where=["has_variable = te_climate_base_penalty"],
         world=rel_mid(diverging(-10.8, 0, (30, 80)), 0, 3), min_span=3,
         note="Local Climate's penalty before any relief, percent of migration attraction (stored yearly), split "
              "at none"),
    dict(name="comfort", input="var:te_climate_penalty_applied", guards=["te_climate_penalty_applied"], three=True,
         sel=28, range_of="comfort_base", where=["has_variable = te_climate_base_penalty"],
         world=rel_mid(diverging(-10.8, 0, (30, 80)), 0, 3), min_span=3,
         note="Local Climate's penalty in force, after the relief its owner's technologies give (stored yearly), "
              "split at none, on Base Comfort's range"),
    dict(name="gdppc", input="gdp_per_capita", guards=[], three=False, sel=29, where=["gdp_per_capita > 0"],
         world=rel_doubling(0.25, 256, 4, 0.01), min_span=4,
         note="GDP per capita, a year's GDP per person in pounds: the same share of the color for each doubling "
              "from the world's low to its high (a rich country about 1 in 1836, 8 in 1917, 60 today)"),
    dict(name="crowding", input="migration_crowding_pull_pct", guards=[], three=False, sel=30, where=[],
         world=rel(soft_cap(0, 0.45, 1.45)), min_span=0.1,
         note="Migration Crowding's cut to migration attraction, 0-1 and past it, as the state panel's tile shows "
              "it: two-thirds of the color by 31% of the world's range"),
    # City Rank (2026-11-08): tourism's city ranking (var:state_city_size_rank, city_rank_on_action: the world's 501
    # largest by city_size, monthly), in two families. Fixed: a rank is already the state's place in the world, and
    # the first 20 are tourism's Cities bonus.
    dict(name="city_top", input="tourism_bonus_from_urban_centers", guards=[], three=False, knots=linear(0.05, 1),
         note="City Rank, the world's 20 largest cities, by the Cities bonus tourism gives them "
              "(tourism_bonus_from_urban_centers): +5% at 20th to +100% at 1st. Fixed: the bonus is what it shows"),
    dict(name="city_rest", input="city_size_rank", guards=[], three=False, knots=doubling(20, 640),
         note="City Rank past 20th: the same share of the color for each doubling of the rank from 20th (the ranking "
              "stops at 501st). Fixed: a rank is already the state's place in the world"),
    # Armed Forces, Company Headquarters and War Dead (2026-11-08): counts and money that run over orders of
    # magnitude, so a doubling at a time, as GDP per capita.
    dict(name="soldiers", input="var:te_dg_soldiers", guards=["te_dg_soldiers"], three=False, sel=33,
         where=["has_variable = te_dg_soldiers", "var:te_dg_soldiers > 0"],
         world=rel_doubling(500, 64000, 4, 100), min_span=4,
         note="Armed Forces, the state's Soldiers and Officers (the yearly walk's): the same share of the color for "
              "each doubling from the world's low (at least 100 people) to its high"),
    # Company Headquarters reads the monthly store's state variables (te_jmap_store_hqs): the engine's per-company
    # headquarters types match no has_building on the template type, so a headquarters is found by its building group.
    dict(name="hq", input="te_jmap_hq_profit", guards=[], three=False, sel=34,
         where=["has_variable = te_jmap_hq_n", "te_jmap_hq_profit > 0"],
         world=rel_doubling(100, 25600, 4, 1), min_span=4,
         note="Company Headquarters, their weekly profit summed: the same share of the color for each doubling from "
              "the world's low (at least 1) to its high; a loss is red, apart from the scale"),
    dict(name="war_dead", input="var:te_dg_dc_war", guards=["te_dg_dc_war"], three=False, sel=35,
         where=["has_variable = te_dg_stepped", "var:te_dg_stepped > 0", "has_variable = te_dg_dc_war",
                "var:te_dg_dc_war > 0"],
         world=rel_doubling(100, 102400, 4, 10), min_span=4,
         note="War Dead, the census's deaths to war and devastation last year: the same share of the color for each "
              "doubling from the world's low (at least 10 people) to its high"),
    # Ownership, Population Growth, Family Planning, Health Care and Fighting-Age Men (2026-11-08, second round).
    dict(name="own", input="te_jmap_own_lead_share", guards=[], three=False, knots=linear(0.4, 1),
         note="Ownership, the leading holder's share of the state's capital levels (private, their own workers', the "
              "state's), its color pale at 40% and full at 100%. Fixed: the map is categorical, and this only fades "
              "each holder's color, as the leading cause's"),
    dict(name="growth", input="te_jmap_pop_growth", guards=[], three=True, sel=37,
         where=["has_variable = te_dg_walk_pop", "has_variable = te_dg_walk_pop_prev",
                "var:te_dg_walk_pop_prev > 0"],
         world=rel_mid(diverging((-20, -80), 0, (40, 100)), 0, 5), min_span=5,
         note="Population Growth, the change in people from one yearly walk to the next per 1,000, split at none; "
              "war, famine and land changing hands run far out"),
    dict(name="means", input="var:te_dg_means", guards=["te_dg_means"], three=False, sel=38,
         where=["has_variable = te_dg_means"], world=rel(linear(0, 1)), min_span=0.1,
         note="Family Planning, the census's means to plan a family, 0-1: the share of the gap to the family size "
              "people want that they can close"),
    dict(name="health", input="var:te_dg_acc", guards=["te_dg_acc"], three=False, sel=39,
         where=["has_variable = te_dg_acc"], world=rel(linear(0.4, 1)), min_span=0.1,
         note="Health Care, the census's health-care access, the share of the people medicine reaches (0.4 from "
              "markets and charity everywhere, to 1)"),
    dict(name="fam", input="te_demog_fam_share", guards=[], three=False, sel=40,
         where=["has_variable = te_dg_fam", "has_variable = te_dg_people"], world=rel(linear(0.08, 0.2)),
         min_span=0.02,
         note="Fighting-Age Men, the census's men aged 20 to 39 (the conscription pool, te_dg_fam) over its people"),
    # The classes and Trade Volume (2026-11-11). Each class's share of the state's people (the yearly walk's, whatever
    # the Demographics rule). Capitalists and Academics gather in a few great cities, so half their color goes by a
    # fifth of the world's range, as turmoil's; Aristocrats and Clergymen spread more evenly, so straight.
    dict(name="capitalists", input="te_jmap_capitalists_share", guards=[], three=False, sel=41,
         where=["has_variable = te_dg_capitalists", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(soft_cap(0, 0.002, 0.01)), min_span=0.002,
         note="Capitalists, their share of the state's people (the yearly walk's): half the color by a fifth of the "
              "world's range"),
    dict(name="aristocrats", input="te_jmap_aristocrats_share", guards=[], three=False, sel=42,
         where=["has_variable = te_dg_aristocrats", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(linear(0, 0.04)), min_span=0.005,
         note="Aristocrats, their share of the state's people (the yearly walk's)"),
    dict(name="clergy", input="te_jmap_clergy_share", guards=[], three=False, sel=43,
         where=["has_variable = te_dg_clergy", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(linear(0, 0.04)), min_span=0.005,
         note="Clergymen, their share of the state's people (the yearly walk's)"),
    dict(name="academics", input="te_jmap_academics_share", guards=[], three=False, sel=44,
         where=["has_variable = te_dg_academics", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(soft_cap(0, 0.002, 0.01)), min_span=0.002,
         note="Academics, their share of the state's people (the yearly walk's): half the color by a fifth of the "
              "world's range"),
    # Trade Volume: the owner's trade with the world market (total_trade_value), which runs over orders of magnitude
    # from a minor's to a great power's, so a doubling at a time; a country with none pale, apart from the scale.
    dict(name="trade", input="te_jmap_trade_value", guards=[], three=False, sel=45,
         where=["te_jmap_trade_value > 0"], world=rel_doubling(100, 102400, 4, 1), min_span=4,
         note="Trade Volume, the state's owner's trade with the world market (the total value of what it buys and "
              "sells there): the same share of the color for each doubling from the world's low to its high"),
]


def fitted(scale):
    return "world" in scale


def range_name(scale):
    """The map whose range this one reads (its own, or range_of's)."""
    return scale.get("range_of", scale["name"])


def num(x):
    """A literal as the engine reads it: five decimals, no trailing zeros."""
    s = f"{x:.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ---- the world's range, as the script values compute it (the test's reference) ---------------------------------------

def world_bounds(scale, lo, hi):
    """(L, H) the trees use for stored globals lo and hi (None: not yet measured, the default)."""
    w = scale["world"]
    if lo is None or hi is None:
        lo, hi = w["default"]
    if w["kind"] == "doubling":
        lo = max(lo, w["floor"])
        return lo, max(hi, lo * w["min_ratio"])
    return lo, max(hi, lo + scale["min_span"])


def _frac_curve(knots, start, span, x, sign=1):
    """The piecewise-linear curve through (start + sign * t * span, f), its end segments carried on."""
    pts = [(start + sign * t * span, f) for t, f in knots]
    if sign < 0:
        pts = list(reversed(pts))
    for (a, fa), (b, fb) in zip(pts, pts[1:]):
        if x < b or (a, fa) == pts[-2]:
            return fa + (x - a) * (fb - fa) / (b - a)
    raise AssertionError


def log2_pieces(r):
    """log2 in straight pieces between powers of two (exact at each), r - 1 below 1."""
    if r < 1:
        return r - 1
    k = 0
    while k < MAX_DOUBLINGS and r >= 2 ** (k + 1):
        k += 1
    return k + r / 2 ** k - 1


def world_factor(scale, lo, hi, x):
    """The factor the tree gives at x for stored globals lo and hi, clamped 0-1."""
    w = scale["world"]
    L, H = world_bounds(scale, lo, hi)
    if w["kind"] == "frac":
        y = _frac_curve(w["knots"], L, H - L, x)
    elif w["kind"] == "mid":
        mid, h = w["mid"], w["min_half"]
        if x < mid:
            B = min(H, mid)
            low = max(B - L, h)
            y = min(0.5, _frac_curve([(t, 0.5 - 0.5 * p) for t, p in w["lower"]], B, low, x, sign=-1))
        else:
            A = max(L, mid)
            up = max(H - A, h)
            y = max(0.5, _frac_curve([(t, 0.5 + 0.5 * p) for t, p in w["upper"]], A, up, x))
    else:
        y = log2_pieces(x / L) / max(log2_pieces(H / L), 1)
    return min(1.0, max(0.0, y))


# ---- writing ------------------------------------------------------------------------------------------------------

def segments(knots):
    """(start, end, value at start, slope's divisor) per segment."""
    return [(a, b, fa, (b - a) / (fb - fa)) for (a, fa), (b, fb) in zip(knots, knots[1:])]


def _leaf(inp, seg):
    a, _b, fa, div = seg
    ops = [f"value = {inp}"]
    if a > 0:
        ops.append(f"subtract = {num(a)}")
    elif a < 0:
        ops.append(f"add = {num(-a)}")
    if num(div) != "1":
        ops.append(f"divide = {num(div)}")
    if fa:
        ops.append(f"add = {num(fa)}")
    return " ".join(ops)


def _ladder(inp, segs, leaf, limit):
    """if / else_if / else over segments, the last carried on: segs[i] taken while limit(i) holds."""
    if len(segs) == 1:
        return [leaf(0)]
    body = []
    for i in range(len(segs)):
        if i == len(segs) - 1:
            body.append("else = {")
        else:
            body.append("else_if = {" if i else "if = {")
            body.append(f"\tlimit = {{ {limit(i)} }}")
        body.append("\t" + leaf(i))
        body.append("}")
    return body


def _guarded(scale, body):
    if scale["guards"]:
        guards = " ".join(f"has_variable = {g}" for g in scale["guards"])
        return ["value = 0", "if = {", f"\tlimit = {{ {guards} }}"] + ["\t" + ln for ln in body] + ["}"]
    return body


def _sv(name, body):
    return [f"{name} = {{"] + ["\t" + ln for ln in body] + ["}"]


def fixed_factor(scale):
    """te_jmap_<name>_factor's lines for a fixed curve: one segment per stretch between knots, the first carried on
    below the first knot and the last past the last, both then clamped to 0-1."""
    inp, segs = scale["input"], segments(scale["knots"])
    body = _ladder(inp, segs, lambda i: _leaf(inp, segs[i]), lambda i: f"{inp} < {num(segs[i][1])}")
    return _sv(f"te_jmap_{scale['name']}_factor", _guarded(scale, body) + ["min = 0", "max = 1"])


def _rel_leaf(inp, start, div, add):
    ops = [f"value = {inp}", f"subtract = {start}", f"divide = {div}"]
    if num(add) != "0":
        ops.append(f"add = {num(add)}")
    return " ".join(ops)


def range_values(scale):
    """The script values that bound a fitted map's range: _lo and _hi (any scope: they read globals), and the state's
    figure as the range's measure reads it (_input, guarded, and _input_neg for the lowest)."""
    n, rn, w = scale["name"], range_name(scale), scale["world"]
    lines = []
    lines += _sv(f"te_jmap_{n}_input", _guarded(scale, [f"value = {scale['input']}"]))
    lines += _sv(f"te_jmap_{n}_input_neg", [f"value = te_jmap_{n}_input", "multiply = -1"])
    if rn != n:
        lines += _sv(f"te_jmap_{n}_lo", [f"value = te_jmap_{rn}_lo"])
        lines += _sv(f"te_jmap_{n}_hi", [f"value = te_jmap_{rn}_hi"])
        return lines
    lo, hi = w["default"]
    lo_body = [f"value = {num(lo)}", "if = {", f"\tlimit = {{ has_global_variable = te_jmap_rng_{n}_lo }}",
               f"\tvalue = global_var:te_jmap_rng_{n}_lo", "}"]
    if w["kind"] == "doubling":
        lo_body.append(f"min = {num(w['floor'])}")
    lines += _sv(f"te_jmap_{n}_lo", lo_body)
    lines += _sv(f"te_jmap_{n}_hi", [f"value = {num(hi)}", "if = {",
                                     f"\tlimit = {{ has_global_variable = te_jmap_rng_{n}_hi }}",
                                     f"\tvalue = global_var:te_jmap_rng_{n}_hi", "}", f"min = te_jmap_{n}_hi_floor"])
    if w["kind"] == "doubling":
        lines += _sv(f"te_jmap_{n}_hi_floor", [f"value = te_jmap_{n}_lo", f"multiply = {num(w['min_ratio'])}"])
    else:
        lines += _sv(f"te_jmap_{n}_hi_floor", [f"value = te_jmap_{n}_lo", f"add = {num(scale['min_span'])}"])
    return lines


def _frac_values(prefix, knots, start, span, sign, fmid=None):
    """Knot positions (prefix_k<i>, i >= 1) and segment divisors (prefix_d<i>) for knots [(t, f)] laid from start along
    span (sign -1: downward). fmid maps a knot's f to the factor (a side's 0.5 +- 0.5 p)."""
    fmid = fmid or (lambda f: f)
    lines = []
    for i, (t, _f) in enumerate(knots[1:-1], 1):
        lines += _sv(f"{prefix}_k{i}", [f"value = {span}", f"multiply = {num(sign * t)}", f"add = {start}"])
    for i, ((ta, fa), (tb, fb)) in enumerate(zip(knots, knots[1:])):
        # Positive on either side: a lower side's figure falls below its knot as its factor does.
        scale = (tb - ta) / abs(fmid(fb) - fmid(fa))
        lines += _sv(f"{prefix}_d{i}", [f"value = {span}", f"multiply = {num(scale)}"])
    return lines


def _frac_ladder(inp, prefix, knots, start, sign, fmid=None):
    fmid = fmid or (lambda f: f)
    starts = [start] + [f"{prefix}_k{i}" for i in range(1, len(knots) - 1)]
    segs = list(zip(knots, knots[1:]))
    cmp = "<" if sign > 0 else ">"
    return _ladder(inp, segs, lambda i: _rel_leaf(inp, starts[i], f"{prefix}_d{i}", fmid(segs[i][0][1])),
                   lambda i: f"{inp} {cmp} {prefix}_k{i + 1}")


def fitted_factor(scale):
    """te_jmap_<name>_factor and the script values its curve is drawn through, for a map fitted to the world."""
    n, inp, w = scale["name"], scale["input"], scale["world"]
    p = f"te_jmap_{n}"
    lines = []
    if w["kind"] == "frac":
        lines += _sv(f"{p}_span", [f"value = {p}_hi", f"subtract = {p}_lo"])
        lines += _frac_values(p, w["knots"], f"{p}_lo", f"{p}_span", 1)
        body = _frac_ladder(inp, p, w["knots"], f"{p}_lo", 1)
    elif w["kind"] == "mid":
        mid, h = num(w["mid"]), num(w["min_half"])
        # The sides' anchors: below mid from the world's low to mid (or to its high, where the whole world is below),
        # above it from mid (or the world's low) to its high, each at least min_half long.
        lines += _sv(f"{p}_b", [f"value = {p}_hi", f"max = {mid}"])
        lines += _sv(f"{p}_a", [f"value = {p}_lo", f"min = {mid}"])
        lines += _sv(f"{p}_span_low", [f"value = {p}_b", f"subtract = {p}_lo", f"min = {h}"])
        lines += _sv(f"{p}_span_up", [f"value = {p}_hi", f"subtract = {p}_a", f"min = {h}"])
        lower = [(t, pp) for t, pp in w["lower"]]
        upper = [(t, pp) for t, pp in w["upper"]]
        fl, fu = (lambda pp: 0.5 - 0.5 * pp), (lambda pp: 0.5 + 0.5 * pp)
        lines += _frac_values(f"{p}_l", lower, f"{p}_b", f"{p}_span_low", -1, fl)
        lines += _frac_values(f"{p}_u", upper, f"{p}_a", f"{p}_span_up", 1, fu)
        low = _frac_ladder(inp, f"{p}_l", lower, f"{p}_b", -1, fl)
        up = _frac_ladder(inp, f"{p}_u", upper, f"{p}_a", 1, fu)
        body = (["if = {", f"\tlimit = {{ {inp} < {mid} }}"] + ["\t" + ln for ln in low] + ["\tmax = 0.5", "}",
                "else = {"] + ["\t" + ln for ln in up] + ["\tmin = 0.5", "}"])
    else:
        # log2 in straight pieces between powers of two, of x over the world's low, over the same of the high.
        lines += _sv(f"{p}_ratio", [f"value = {inp}", f"divide = {p}_lo"])
        lines += _sv(f"{p}_log", _log_ladder(f"{p}_ratio"))
        lines += _sv(f"{p}_span_ratio", [f"value = {p}_hi", f"divide = {p}_lo"])
        lines += _sv(f"{p}_log_span", _log_ladder(f"{p}_span_ratio") + ["min = 1"])
        body = [f"value = {p}_log", f"divide = {p}_log_span"]
    lines += _sv(f"{p}_factor", _guarded(scale, body) + ["min = 0", "max = 1"])
    return lines


def _log_ladder(ratio):
    """k + r / 2^k - 1 on [2^k, 2^(k+1)), r - 1 below 2: log2 exact at each power of two."""
    body = []
    for k in range(MAX_DOUBLINGS + 1):
        if k == MAX_DOUBLINGS:
            body.append("else = {")
        else:
            body.append("else_if = {" if k else "if = {")
            body.append(f"\tlimit = {{ {ratio} < {2 ** (k + 1)} }}")
        ops = [f"value = {ratio}"]
        if k:
            ops.append(f"divide = {2 ** k}")
        if k - 1:
            ops.append(f"add = {k - 1}" if k > 1 else "subtract = 1")
        body.append("\t" + " ".join(ops))
        body.append("}")
    return body


def render():
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_journal_map_scales.py — do not edit manually.",
        "# The Map Room's color scales (common/journal_entries/te_journal_maps.txt): each map's factor, 0-1. Nearly every",
        "# map is fitted to the world as it stands: its curve keeps its shape on the span from the world's low to its",
        "# high (te_jmap_<map>_lo / _hi, stored by te_journal_map_ranges_generated.txt's effects on each pick and each",
        "# month; the fixed curve's ends before the first). Change a shape or a row in the generator and re-run it;",
        "# test_journal_map_scales.py fails when this file is stale. A value reading a figure runs with a STATE as root,",
        "# once per state as the map paints; _lo, _hi and their kin read only globals, from any scope.",
    ]
    for scale in SCALES:
        lines += ["", f"# {scale['note']}."]
        if fitted(scale):
            w = scale["world"]
            lo, hi = w["default"]
            desc = {"frac": "fitted to the world", "mid": f"fitted to the world on each side of {num(w.get('mid', 0))}",
                    "doubling": "a doubling at a time, fitted to the world"}[w["kind"]]
            lines.append(f"# {desc.capitalize()}; before the first measure, {num(lo)} to {num(hi)}.")
            lines += range_values(scale)
            lines += fitted_factor(scale)
        else:
            knots = ", ".join(f"{num(x)} -> {num(y)}" for x, y in scale["knots"])
            lines.append(f"# Fixed. Knots: {knots}.")
            lines += fixed_factor(scale)
        if scale["three"]:
            name = f"te_jmap_{scale['name']}_factor"
            lines += [f"{name}_lower = {{", f"\tvalue = {name}", "\tmultiply = 2", "\tmin = 0", "\tmax = 1", "}"]
            lines += [f"{name}_upper = {{", f"\tvalue = {name}", "\tmultiply = 2", "\tsubtract = 1", "\tmin = 0",
                      "\tmax = 1", "}"]
    return "\n".join(lines) + "\n"


def _measure(n, where, order, position, var):
    limit = " ".join(where)
    return [
        "ordered_state = {",
    ] + ([f"\tlimit = {{ {limit} }}"] if limit else []) + [
        f"\torder_by = te_jmap_{n}_{order}",
        f"\tposition = {position}",
        "\tcheck_range_bounds = no",
        f"\tset_global_variable = {{ name = te_jmap_rng_{n}_{var} value = te_jmap_{n}_input }}",
        "}",
    ]


def render_effects():
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_journal_map_scales.py — do not edit manually.",
        "# The Map Room's maps fitted to the world (te_journal_map_scales_generated.txt): each te_jmap_range_<map>",
        f"# measures the world's range for a map, from the {TRIM + 1}th lowest to the {TRIM + 1}th highest of the states it",
        "# paints with a figure (the lowest and highest where fewer have one; the fixed curve's ends where none has),",
        "# into te_jmap_rng_<map>_lo / _hi. Any scope: ordered_state iterates the world's states. te_jmap_refresh_range",
        "# measures the pick's map (te_jmap_set_selector, te_journal_map_effects.txt; and monthly,",
        "# te_journal_map_on_actions.txt), te_jmap_refresh_entry_ranges the maps a system's own entry draws too.",
    ]
    own = [s for s in SCALES if fitted(s) and range_name(s) == s["name"]]
    for scale in own:
        n, where = scale["name"], scale["where"]
        body = []
        for end in ("lo", "hi"):
            body += ["if = {", f"\tlimit = {{ has_global_variable = te_jmap_rng_{n}_{end} }}",
                     f"\tremove_global_variable = te_jmap_rng_{n}_{end}", "}"]
        body += _measure(n, where, "input", TRIM, "hi")
        body += _measure(n, where, "input_neg", TRIM, "lo")
        body += ["# Fewer states than the trim takes out: the extremes.",
                 "if = {", f"\tlimit = {{ NOT = {{ has_global_variable = te_jmap_rng_{n}_hi }} }}"]
        body += ["\t" + ln for ln in _measure(n, where, "input", 0, "hi") + _measure(n, where, "input_neg", 0, "lo")]
        body += ["}"]
        lines += ["", f"# {scale['note']}."] + _sv(f"te_jmap_range_{n}", body)
    picks = sorted((s["sel"], range_name(s)) for s in SCALES if fitted(s))
    body = []
    for i, (sel, rn) in enumerate(picks):
        body += ["else_if = {" if i else "if = {", f"\tlimit = {{ te_jmap_selector = {sel} }}",
                 f"\tte_jmap_range_{rn} = yes", "}"]
    lines += ["", "# The pick's map, if it is fitted to the world (te_jmap_selector, te_journal_map_values.txt)."]
    lines += _sv("te_jmap_refresh_range", body)
    entries = [s["name"] for s in SCALES if s.get("entry")]
    lines += ["", "# The maps a system's own entry draws whatever the pick (je_global_warming, je_grand_monuments)."]
    lines += _sv("te_jmap_refresh_entry_ranges", [f"te_jmap_range_{n} = yes" for n in entries])
    return "\n".join(lines) + "\n"


def _check(path, text):
    rel = os.path.relpath(path, REPO)
    try:
        with open(path, encoding="utf-8-sig") as f:
            current = f.read()
    except FileNotFoundError:
        current = None
    if current != text:
        print(f"{rel} is stale: run scripts/generators/gen_journal_map_scales.py")
        return 1
    print(f"{rel} is current")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when a committed file is stale; write nothing")
    args = parser.parse_args()
    outputs = [(OUT, render()), (EFFECTS_OUT, render_effects())]
    if args.check:
        return max(_check(path, text) for path, text in outputs)
    for path, text in outputs:
        with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
            f.write(text)
        print(f"wrote {os.path.relpath(path, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
