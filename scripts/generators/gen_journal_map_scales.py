#!/usr/bin/env python3
"""Write the Map Room's color scales and the effects that fit them to the world.

Each map in je_te_map_room (common/journal_entries/te_journal_maps.txt) colors a state by a factor, 0 to 1, read from
one of the state's figures. Two files come from the table below:

- common/script_values/te_journal_map_scales_generated.txt: each map's factor, te_jmap_<map>_factor, and for a map
  fitted to the world the script values its curve is drawn through;
- common/scripted_effects/te_journal_map_ranges_generated.txt: the effects that measure the world for a map
  (te_jmap_range_<map>), the dispatcher a pick and the monthly pulse run (te_jmap_refresh_range, on the pick in
  te_jmap_selector) and the maps the systems' own entries draw whatever the pick (te_jmap_refresh_entry_ranges).

**The Map Room's options** (owner, 2026-11-14: "limiting where we draw it", "maybe excluding outliers"). The range is
where both live, so both are written here. Area: a state outside the Map Room's area carries te_jmap_out
(te_jmap_mark_area, te_journal_map_effects.txt), and every range the Map Room reads counts and orders only the states
te_jmap_in_area passes, so the colors run over the area alone. Outliers: each end leaves out te_jmap_trim_count
states, from the option (te_jmap_trim, te_journal_map_values.txt) and the count of states with a figure in the area:
TRIM (the default), none, or TRIM_SHARE of them. A measure first counts those states, so the trim never passes the
middle of a short list: ordered_state's position past the end takes the last state and logs, it doesn't skip
(scripting_best_practices.md, "position = N + check_range_bounds = no Clamps Out-of-Range"), and under Country or
Bloc a short list is the usual case. position takes no script value (effects.log: position = int), so
te_jmap_measure_at is a ladder of literal positions, 0 to TRIM_MAX, each a call of te_jmap_measure_<map> = { K = n }.

A map a system's own entry draws too (entry: Emissions, Grandeur) is measured twice. te_jmap_range_<map> stays the
entry's: the whole world, the default trim, whatever the Map Room's options, each month. Its twin
te_jmap_range_<map>_room is the Map Room's, under the options, with a factor of its own (te_jmap_<map>_room_factor),
since a script value can't tell which page asks. The twin's range is the entry's until its first measure.

**The Scale option** (owner, 2026-11-14, the thirteenth pass: te_jmap_scale, te_journal_map_values.txt). A factor is
a script value, and a script value can read a global, so each factor the Map Room reads takes one of four branches:
the map's own curve (the default, first, so a default paint pays one comparison), Linear, Logarithmic or Ranked. The
paint itself doesn't change, and neither do the factors a system's own entry reads, nor the fixed curves.

- Linear: straight from the range's low to its high; on a map with a meaningful midpoint, straight on each side of it.
- Logarithmic: the same share of the color for each doubling. A map already on a doubling scale keeps its tree. A
  straight map starts at its range's low, or at a LOG_RATIO-th of its high where the low is smaller (a low of 0 has
  no logarithm). A map with a meaningful midpoint is logarithmic on each side of it by the distance from it, and
  straight within min_half of it, where a logarithm has no start: the knee is min_half / LOG_KNEE_PART, and the log
  is read in straight pieces between powers of two, so the first doubling past the knee is straight too. The
  midpoint stays at exactly 0.5.
- Ranked: the state's place in line among the states the map paints in the area, 0 to 1, equal figures sharing a
  place (peacetime Devastation is hundreds of states at exactly 0, which an index would smear across the palette).
  A paint can't sort, so the place is stored on the state (te_jmap_rank) by te_jmap_rank_<map>, which
  te_jmap_refresh_range runs after the range: an ordered walk that counts places, then a pass that divides by the
  number of places. A map with a meaningful midpoint is ranked on each side of it, outward, so the midpoint keeps its
  color. One variable for every map: te_jmap_refresh_range clears it before any measure. Each map is ranked by its
  own figure, though Current Comfort shares Base Comfort's range.

**The Color option** (owner, 2026-11-14, the fourteenth pass: te_jmap_color, te_journal_map_values.txt). A paint's
colors are literal names, so another palette can't be swapped into a map's own branches. Instead the Map Room's
paint opens with a few shared branches, taken only while the option is off its default, that color whatever map is
picked from one shared ramp. They ask this file two things about the state being painted, each a ladder on the pick:
whether the pick's own lerp branch would paint it and on which kind of ramp (te_jmap_pick_ramp: 0 no, 1 the
sequential ramp, 2 the diverging one, for a map with a meaningful midpoint), and its factor (te_jmap_pick_factor).
A ramp of RAMP_LERPS lerps reads the factor a quarter at a time (te_jmap_pick_q1 to _q4). A row's `paint` is its
lerp branch's limit where that isn't the `where` its range is measured over; test_journal_map_modes.py reads the
paint in ladder order and holds each row to it.

**Fitted to the world** (owner, 2026-11-07: "people are not going to it to see that the world GDP/c average has gone
up, they want to see the regional differences"). Nearly every map's colors run from the world's low to its high as
it stands: the fifth lowest and the fifth highest of the states the map paints (TRIM states left out at each end, so
one outlier doesn't flatten the rest; fewer where few states have a figure, below), stored in global variables
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import journal_map_classes as classes  # noqa: E402  (the class maps' table, #1975)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "common", "script_values", "te_journal_map_scales_generated.txt")
EFFECTS_OUT = os.path.join(REPO, "common", "scripted_effects", "te_journal_map_ranges_generated.txt")

# How much shallower a soft cap's tail runs than its main stretch (the owner, 2026-11-06: "1/4 slope above").
SLOPE_RATIO = 4
# The states left out at each end of the world's range: the range runs from the (TRIM + 1)th lowest to the
# (TRIM + 1)th highest. ordered_state's position counts from 0. The default of the Map Room's Outliers option.
TRIM = 4
# The Outliers option's share: this part of the area's states with a figure is left out at each end (rounded down).
TRIM_SHARE = 0.05
# The most states an end leaves out, whatever the option: te_jmap_measure_at holds a literal position for each count
# up to it (5% of 1,600 states with a figure).
TRIM_MAX = 80
# Under a limited area the default trim leaves out at most one state in this many at each end, so a country of
# fifteen states isn't mostly outliers. The world keeps TRIM whatever its count, as before the options.
AREA_TRIM_PART = 10
# The Outliers option's settings (te_jmap_trim, te_journal_map_values.txt; unset is the default).
TRIM_DEFAULT, TRIM_NONE, TRIM_PERCENT = 0, 1, 2
# The most doublings a doubling map's ladder reads (2^20 is a millionfold).
MAX_DOUBLINGS = 20
# The Scale option's settings (te_jmap_scale, te_journal_map_values.txt; unset is the map's own curve).
SCALE_OWN, SCALE_LINEAR, SCALE_LOG, SCALE_RANKED = 0, 1, 2, 3
# Logarithmic on a straight map: the scale starts at the range's low, or at this share of its high where the low is
# smaller: six doublings at most. The engine keeps five decimals, so the share can't be much smaller: a
# thousandth of the smallest range (0.002, the Capitalists' share) would truncate to 0 and be divided by.
LOG_RATIO = 64
# The least a LOG_RATIO-th of a map's narrowest range may be, so the engine's five decimals can still tell a low
# above it from one below (asserted for every straight row, below).
LOG_FLOOR = 0.00002
# Logarithmic on a map with a meaningful midpoint: the knee is the map's min_half over this, so the scale is
# straight within min_half of the midpoint (the log's first piece past the knee, from 1 to 2 knees, is straight).
LOG_KNEE_PART = 2
# The most states a rank's walk visits (ordered_state's max is a literal here; a game holds far fewer states).
RANK_MAX = 5000
# The Color option's settings (te_jmap_color, te_journal_map_values.txt; unset is the map's own colors).
COLOR_OWN, COLOR_SAFE, COLOR_GREY = 0, 1, 2
# What te_jmap_pick_ramp answers for the state being painted: not on the pick's ramp, on it and the pick runs one
# way (the sequential ramp), on it and the pick runs both ways from a midpoint (the diverging ramp).
RAMP_NONE, RAMP_SEQ, RAMP_DIV = 0, 1, 2
# The lerps a shared ramp is painted in: the engine mixes two colors at a time, so a ramp of five published stops
# is four mixes end to end, and a diverging one two a side.
RAMP_LERPS = 4


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
# names a map whose range it shares, entry marks a map a system's own entry draws too (refreshed every month over the
# whole world; SCALES, below the table, adds the Map Room's twin of each).
# A fixed map has knots.
TABLE = [
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
         paint=["te_jmap_gw_no_data = no", "te_jmap_gw_removal = no"],     # the same states, as the paint asks
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
         paint=["has_variable = te_climate_penalty_applied"],     # the yearly refresh stores the two together
         world=rel_mid(diverging(-10.8, 0, (30, 80)), 0, 3), min_span=3,
         note="Local Climate's penalty in force, after the relief its owner's technologies give (stored yearly), "
              "split at none, on Base Comfort's range"),
    dict(name="gdppc", input="gdp_per_capita", guards=[], three=False, sel=29, where=["gdp_per_capita > 0"],
         paint=[],     # a state with no GDP per capita is painted at the low end, and left out of the range
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
    # The classes (#1975; four share maps since 2026-11-11) come from journal_map_classes.py, after the table.
    # Trade Capacity (2026-11-11): the state's own (state_trade_capacity_add times its multipliers, te_jmap_trade_capacity), which
    # runs from one Trade Center level's 10 to a great entrepot's thousands, so a doubling at a time; a state with
    # none pale, apart from the scale.
    dict(name="trade", input="te_jmap_trade_capacity", guards=[], three=False, sel=45,
         where=["te_jmap_trade_capacity > 0"], world=rel_doubling(10, 5120, 4, 1), min_span=4,
         note="Trade Capacity, the state's own, its Trade Center's: the same share of the color for each doubling "
              "from the world's low (at least 1) to its high"),
    # Investment reads the store's state variables (te_jmap_store_invest), as Company Headquarters does.
    dict(name="invest", input="te_jmap_invest_value", guards=[], three=False, sel=46,
         where=["has_variable = te_jmap_inv_cap", "te_jmap_invest_value > 0"],
         world=rel_doubling(10, 10240, 4, 1), min_span=4,
         note="Investment, what the state's owners pay into the Investment Pool a week, estimated: the same share of "
              "the color for each doubling from the world's low (at least 1) to its high"),
    # Population Density (2026-11-16): people per km² of land (te_jmap_density, from the region area table), which ran
    # from 0.009 (Nunavut) to 734 (Suzhou) at the 1836 start, the fifth lowest 0.017 and the fifth highest 267: some
    # sixteen doublings, so a doubling at a time; a state with no people pale, apart from the scale.
    dict(name="density", input="te_jmap_density", guards=[], three=False, sel=47,
         where=["te_jmap_density > 0"], world=rel_doubling(0.03125, 256, 4, 0.01), min_span=4,
         note="Population Density, the state's people per km² of land: the same share of the color for each "
              "doubling from the world's low (at least 0.01) to its high"),
    # The first tier of the owner's new maps (2026-11-23, #1976): living standards, the economy and politics. Several
    # mirror a vanilla lens; the Map Room's options (Area above all) are what they add.
    # Standard of Living and Wealth, the yearly walk's people-weighted means (te_dg_sol, and te_dg_wealth from the Map
    # Room's own walk call), whatever the Demographics rule.
    dict(name="sol", input="var:te_dg_sol", guards=["te_dg_sol"], three=False, sel=74,
         where=["has_variable = te_dg_sol", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(linear(5, 25)), min_span=2,
         note="Standard of Living, the state's people's mean at the yearly walk"),
    dict(name="wealth", input="var:te_dg_wealth", guards=["te_dg_wealth"], three=False, sel=75,
         where=["has_variable = te_dg_wealth", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(linear(5, 25)), min_span=2,
         note="Wealth, the state's people's mean wealth at the yearly walk"),
    # The two less each other: what a place adds to living standards, or takes from them, beyond its people's wealth
    # (pollution, health institutions, laws, ruler traits, principles, events). Small in 1836, growing through the game.
    dict(name="sol_wealth", input="te_jmap_sol_wealth", guards=[], three=True, sel=76,
         where=["has_variable = te_dg_sol", "has_variable = te_dg_wealth", "has_variable = te_dg_walk_pop",
                "var:te_dg_walk_pop > 0"],
         world=rel_mid(diverging(-5, 0, 5), 0, 1), min_span=1,
         note="Standard of Living less Wealth, the yearly walk's, split at none"),
    # The gap the engine radicalizes on, live: the state's mean standard of living less its people's expected one.
    dict(name="sol_expected", input="te_jmap_sol_expected", guards=[], three=True, sel=77,
         where=["state_population > 0"], paint=[],     # an empty state paints at none, and is left out of the range
         world=rel_mid(diverging(-5, 0, 5), 0, 1), min_span=1,
         note="Standard of Living against the expected one, live (average_sol less average_expected_sol), split at "
              "none"),
    # Literacy, live (literacy_rate). Selector 2 again: retired in the fifth pass as vanilla's own lens's twin, back
    # because a Map Room map takes the area and the other options.
    dict(name="literacy", input="literacy_rate", guards=[], three=False, sel=2,
         where=["state_population > 0"], paint=[],     # an empty state paints at its 0, and is left out of the range
         world=rel(linear(0, 1)), min_span=0.1,
         note="Literacy, the state's people's, 0-1, live"),
    # Unemployment, the state's workforce without work (te_state_unemployment_share), stored at a pick and monthly while
    # picked (te_jmap_store_unemp): a GUI reads state_unemployment_rate as none, so the hover couldn't read it live.
    dict(name="unemp", input="var:te_jmap_unemp", guards=["te_jmap_unemp"], three=False, sel=78,
         where=["has_variable = te_jmap_unemp"], world=rel(soft_cap(0, 0.2, 0.6)), min_span=0.05,
         note="Unemployment, the share of the state's workforce without work: two-thirds of the color by a third of "
              "the world's range"),
    # Population and GDP, live, each a doubling at a time: the people and the money run over orders of magnitude.
    dict(name="people", input="state_population", guards=[], three=False, sel=79,
         where=["state_population > 0"], world=rel_doubling(16000, 4096000, 4, 100), min_span=4,
         note="Population, the state's people: the same share of the color for each doubling from the world's low "
              "(at least 100 people) to its high"),
    dict(name="gdp", input="te_jmap_gdp_value", guards=[], three=False, sel=80,
         where=["te_jmap_gdp_value > 0"], world=rel_doubling(8000, 8192000, 4, 1), min_span=4,
         note="GDP, the state's yearly GDP in pounds: the same share of the color for each doubling from the "
              "world's low (at least 1) to its high"),
    # Infrastructure to spare, live: the state's infrastructure less what its buildings and people use.
    dict(name="infra", input="te_jmap_infra_balance", guards=[], three=True, sel=81,
         where=["state_population > 0"], paint=[],     # every state paints; an empty one is left out of the range
         world=rel_mid(diverging(-30, 0, 60), 0, 5), min_span=5,
         note="Infrastructure less its usage, live, split at none"),
    # Radicals against loyalists, live: the state's loyalists' share of its people less its radicals'.
    dict(name="loyal", input="te_jmap_loyal_net", guards=[], three=True, sel=82,
         where=["state_population > 0"], paint=[],     # an empty state paints at none, and is left out of the range
         world=rel_mid(diverging(-0.2, 0, 0.2), 0, 0.02), min_span=0.02,
         note="Loyalists less radicals, each a share of the state's people, live, split at none"),
    # The second tier (2026-11-23, #1977): four engine figures the mod reads as a value for the first time, each with a
    # once-a-game self-check (te_journal_map_effects.txt), and the walk's count of the people not fully accepted.
    # Market access, live, 0-1: most states stand at 1, so the range's low is the cut-off states'.
    dict(name="access", input="te_jmap_market_access", guards=[], three=False, sel=83,
         where=["state_population > 0"], paint=[],     # every state paints; an empty one is left out of the range
         world=rel(linear(0, 1)), min_span=0.1,
         note="Market access, the state's, 0-1, live: min(infrastructure, usage) over usage"),
    # The region's pollution, 0 to 255 (POLLUTION_MAX), live; a clean region pale, apart from the scale. Most polluted
    # regions sit low on the 255, so two-thirds of the color goes by a third of the range.
    dict(name="pollution", input="te_jmap_pollution", guards=[], three=False, sel=84,
         where=["te_jmap_pollution > 0"], world=rel(soft_cap(0, 50, 150)), min_span=5,
         note="Pollution, the state region's, 0-255, live: two-thirds of the color by a third of the world's range"),
    # The jobs open in a state's buildings, live, which run over orders of magnitude, so a doubling at a time; a state
    # with none open pale, apart from the scale.
    dict(name="jobs", input="te_jmap_vacant_jobs", guards=[], three=False, sel=85,
         where=["te_jmap_vacant_jobs > 0"], world=rel_doubling(1000, 512000, 4, 10), min_span=4,
         note="Vacant Jobs, the jobs open in the state's buildings other than subsistence farms: the same share of the "
              "color for each doubling from the world's low (at least 10) to its high"),
    dict(name="below_sol", input="te_jmap_below_expected", guards=[], three=False, sel=86,
         where=["state_population > 0"], paint=[],     # an empty state paints at its 0, and is left out of the range
         world=rel(linear(0, 1)), min_span=0.1,
         note="The share of the state's people below their expected standard of living, 0-1, live"),
    # The share below Full Acceptance at the yearly walk (te_dg_unacc), whatever the Demographics rule.
    dict(name="unacc", input="te_jmap_unacc_share", guards=[], three=False, sel=87,
         where=["has_variable = te_dg_unacc", "has_variable = te_dg_walk_pop", "var:te_dg_walk_pop > 0"],
         world=rel(linear(0, 1)), min_span=0.1,
         note="Discrimination, the share of the state's people below Full Acceptance (the yearly walk's)"),
]


def class_rows(c):
    """A class's two maps (journal_map_classes.py, #1975): its people, a doubling at a time from the world's low (at
    least COUNT_FLOOR people) to its high, and its share of the state's people, fitted to the world. Both read the
    yearly walk's count (te_dg_cls_<pop>), whatever the Demographics rule."""
    name, var = c["name"], classes.count_var(c)
    lo, hi = c["count"]
    count = dict(name=classes.count_scale(c), input=f"var:{var}", guards=[var], three=False, sel=c["count_sel"],
                 where=[f"has_variable = {var}", f"var:{var} > 0"],
                 world=rel_doubling(lo, hi, classes.COUNT_MIN_RATIO, classes.COUNT_FLOOR),
                 min_span=classes.COUNT_MIN_RATIO,
                 note=f"{name}, their people (the yearly walk's): the same share of the color for each doubling from "
                      f"the world's low (at least {classes.COUNT_FLOOR} people) to its high")
    kind, top = c["share"]
    curve = linear(0, top) if kind == "linear" else soft_cap(0, top, 5 * top)
    share = dict(name=classes.share_scale(c), input=classes.share_value(c), guards=[], three=False,
                 sel=c["share_sel"], where=[f"has_variable = {var}", "has_variable = te_dg_walk_pop",
                                            "var:te_dg_walk_pop > 0"],
                 world=rel(curve), min_span=c["share_min"],
                 note=f"{name}, their share of the state's people (the yearly walk's)"
                      + (": half the color by a fifth of the world's range" if kind == "knee" else ""))
    return [count, share]


TABLE += [row for c in classes.CLASSES for row in class_rows(c)]


def _room_twin(scale):
    """The Map Room's copy of a map a system's own entry draws too: the same figure and shape, a range and a factor
    of its own (te_jmap_<map>_room_*), measured under the Map Room's options. The entry keeps the row's."""
    twin = {k: v for k, v in scale.items() if k != "entry"}
    twin.update(name=scale["name"] + "_room", twin_of=scale["name"])
    return twin


# Every scale written: the table's rows, each entry map followed by its Map Room twin.
SCALES = [s for row in TABLE for s in ([row, _room_twin(row)] if row.get("entry") else [row])]


def fitted(scale):
    return "world" in scale


def range_name(scale):
    """The map whose range this one reads (its own, or range_of's)."""
    return scale.get("range_of", scale["name"])


def in_room(scale):
    """The Map Room paints with this scale (a map's only scale, or an entry map's twin): its range follows the Map
    Room's options. An entry's own scale is measured over the whole world on the default trim, whatever they are."""
    return not scale.get("entry")


def painted(scale):
    """The trigger lines under which the Map Room's paint puts a state on this map's ramp: the limit of its lerp
    branch, less the pick itself. The states its range is measured over unless the row says otherwise."""
    return scale.get("paint", scale["where"])


def pick_ramp(scale):
    """The shared ramp a fitted map takes under the Color option: the diverging one where its midpoint means
    something, the sequential one otherwise (a three-color map with no such midpoint included)."""
    return RAMP_DIV if scale["world"]["kind"] == "mid" else RAMP_SEQ


def ramp_lerp(factor):
    """Which of a shared ramp's RAMP_LERPS lerps paints a factor, and how far along it (0-1): the reference for
    te_jmap_pick_q<n> and the paint's `te_jmap_pick_factor < n/4` ladder."""
    n = min(int(factor * RAMP_LERPS), RAMP_LERPS - 1)
    return n + 1, min(max(factor * RAMP_LERPS - n, 0), 1)


# A share of a range, or of the color, that has a plain name: a pick's tooltip uses the name, and a percentage for
# any other (te_jmap_curve_*, localization/english; test_journal_map_modes.py holds each to curve_words).
_SHARES = ((1 / 2, "half"), (1 / 3, "a third"), (2 / 3, "two-thirds"), (1 / 4, "a quarter"), (1 / 5, "a fifth"))


def _share(x, first=False):
    """A share in a tooltip's words; `first` is the form after "the first" (fifth, two-thirds, 38%)."""
    for share, words in _SHARES:
        if abs(x - share) < 0.004:
            return words[2:] if first and words.startswith("a ") else words
    return f"{round(x * 100)}%"


def _knee(knots):
    """A curve's knee (the share of its span, the share of its color by then), or None for a straight one."""
    assert len(knots) in (2, 3), "a tooltip can describe a straight curve or one knee"
    return knots[1] if len(knots) == 3 else None


def curve_key(scale):
    """The localization key that describes a fitted map's own curve, shared by every map of the same shape."""
    w = scale["world"]
    code = lambda knots: "s" if _knee(knots) is None else "_".join(str(round(v * 100)) for v in _knee(knots))
    if w["kind"] == "doubling":
        return "te_jmap_curve_doubling"
    if w["kind"] == "mid":
        low, up = code(w["lower"]), code(w["upper"])
        return "te_jmap_curve_mid" if low == up == "s" else f"te_jmap_curve_mid_{low}_{up}"
    return "te_jmap_curve_straight" if _knee(w["knots"]) is None else f"te_jmap_curve_knee_{code(w['knots'])}"


def curve_words(scale):
    """A fitted map's own curve in a tooltip's words, from the knots the curve itself is written from."""
    w = scale["world"]
    if w["kind"] == "doubling":
        return "Each doubling of the figure takes the same share of the color, from the range's low to its high."
    if w["kind"] == "mid":
        low, up = _knee(w["lower"]), _knee(w["upper"])
        if low is None and up is None:
            return "The colors run straight on each side of the midpoint, to the range's end on that side."
        side = lambda knee, end, color: (f"the colors run straight to {end}" if knee is None else
                                         f"{_share(knee[1])}{color} goes to the first {_share(knee[0], True)} of the way to {end}")
        return (f"Below the midpoint, {side(low, 'the range' + chr(39) + 's low', ' of the color')}; "
                f"above it, {side(up, 'its high', ' of the color' if low is None else '')}.")
    knee = _knee(w["knots"])
    if knee is None:
        return "The colors run straight from the range's low to its high."
    share = _share(knee[1])
    return (f"{share[0].upper() + share[1:]} of the color goes to the first {_share(knee[0], True)} of the range, "
            "and the rest to what is left of it.")


def trim_most(n):
    """The most states an end can leave out of n and still have two left to span."""
    return max(0, (n - 2) // 2)


def trim_count(n, option=TRIM_DEFAULT, limited=False):
    """The states each end of a range leaves out, as te_jmap_trim_count works it out (the test's reference): n the
    states with a figure in the area, option the Outliers setting, limited whether the area is less than the world."""
    if option == TRIM_NONE:
        k = 0
    elif option == TRIM_PERCENT:
        k = int(n * TRIM_SHARE + 1e-9)
    else:
        k = min(TRIM, n // AREA_TRIM_PART) if limited else TRIM
    return max(0, min(k, trim_most(n), TRIM_MAX))


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


def log_start(scale, lo, hi):
    """Where Logarithmic starts on a straight map: the range's low, or a LOG_RATIO-th of its high where the low is
    smaller (a low of 0 has no logarithm)."""
    L, H = world_bounds(scale, lo, hi)
    return max(L, H / LOG_RATIO)


def knee(scale):
    """The knee of a midpoint map's Logarithmic scale: straight within twice this (min_half) of the midpoint."""
    return scale["world"]["min_half"] / LOG_KNEE_PART


def _side_share(option, d, span, k):
    """How far along its side of the midpoint a state d from the side's start sits, 0-1, the side span long."""
    if option == SCALE_LINEAR:
        return d / span
    return (1 + log2_pieces(d / k)) / (1 + log2_pieces(span / k))


def scaled_factor(scale, option, lo, hi, x, rank=None):
    """The factor te_jmap_<map>_factor gives at x under a Scale setting, for stored globals lo and hi (None: not
    yet measured), clamped 0-1: the test's reference. rank: the state's stored place, for Ranked (None: no place
    yet, which paints the midpoint color on a three-color map and the low color on any other)."""
    if option == SCALE_OWN:
        return world_factor(scale, lo, hi, x)
    w = scale["world"]
    if option == SCALE_RANKED:
        y = rank if rank is not None else (0.5 if scale["three"] else 0.0)
    elif w["kind"] == "mid":
        L, H = world_bounds(scale, lo, hi)
        mid, h = w["mid"], w["min_half"]
        if x < mid:
            B = min(H, mid)
            y = min(0.5, 0.5 - 0.5 * _side_share(option, B - x, max(B - L, h), knee(scale)))
        else:
            A = max(L, mid)
            y = max(0.5, 0.5 + 0.5 * _side_share(option, x - A, max(H - A, h), knee(scale)))
    elif option == SCALE_LINEAR:
        L, H = world_bounds(scale, lo, hi)
        y = (x - L) / (H - L)
    elif w["kind"] == "doubling":
        return world_factor(scale, lo, hi, x)
    else:
        L, H = world_bounds(scale, lo, hi)
        start = log_start(scale, lo, hi)
        y = log2_pieces(x / start) / max(log2_pieces(H / start), 0.001)
    return min(1.0, max(0.0, y))


def ranks(figures, mid=None):
    """{index: place} for a list of figures, as te_jmap_rank_<map> stores it: the place in line from the lowest, 0
    to 1, equal figures sharing a place and each distinct figure a step of the same size. With a midpoint, each
    side is ranked outward from it (0.5 to 0 below, 0.5 to 1 above) and a figure at the midpoint itself is 0.5."""
    def places(values):
        distinct = sorted(set(values))
        return {v: i for i, v in enumerate(distinct)}, len(distinct)

    out = {}
    if mid is None:
        place, count = places(figures)
        for i, x in enumerate(figures):
            out[i] = place[x] / max(count - 1, 1)
        return out
    below, n_below = places([-x for x in figures if x < mid])     # nearest the midpoint first
    above, n_above = places([x for x in figures if x > mid])
    for i, x in enumerate(figures):
        if x < mid:
            out[i] = 0.5 - 0.5 * (below[-x] + 1) / n_below
        elif x > mid:
            out[i] = 0.5 + 0.5 * (above[x] + 1) / n_above
        else:
            out[i] = 0.5
    return out


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
    lo, hi = (num(x) for x in w["default"])
    if scale.get("twin_of"):
        # The Map Room's twin of an entry's map: the entry's range until its own first measure, so a save from before
        # the twin paints as it did.
        lo, hi = f"te_jmap_{scale['twin_of']}_lo", f"te_jmap_{scale['twin_of']}_hi"
    lo_body = [f"value = {lo}", "if = {", f"\tlimit = {{ has_global_variable = te_jmap_rng_{n}_lo }}",
               f"\tvalue = global_var:te_jmap_rng_{n}_lo", "}"]
    if w["kind"] == "doubling":
        lo_body.append(f"min = {num(w['floor'])}")
    lines += _sv(f"te_jmap_{n}_lo", lo_body)
    lines += _sv(f"te_jmap_{n}_hi", [f"value = {hi}", "if = {",
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


def _indent(body):
    return ["\t" + ln for ln in body]


def _side_bodies(inp, mid, low, up):
    """A midpoint map's two sides: below the midpoint the factor runs down from 0.5, above it up from 0.5; a state
    past its side's start (the whole world on the other side) stays at 0.5."""
    return (["if = {", f"\tlimit = {{ {inp} < {mid} }}"] + _indent(low) + ["\tmax = 0.5", "}",
            "else = {"] + _indent(up) + ["\tmin = 0.5", "}"])


def scale_bodies(scale):
    """(values, {setting: body}) for the Scale option's other three settings: the script values Linear and
    Logarithmic are drawn through, and each setting's lines inside te_jmap_<map>_factor."""
    n, inp, w = scale["name"], scale["input"], scale["world"]
    p = f"te_jmap_{n}"
    lines, bodies = [], {}
    # Ranked: the stored place. A state the map paints but the last measure didn't walk (made since) has none: the
    # midpoint color on a three-color map, the low color on any other, until the next measure.
    bodies[SCALE_RANKED] = [f"value = {num(0.5 if scale['three'] else 0)}", "if = {",
                            "\tlimit = { has_variable = te_jmap_rank }", "\tvalue = var:te_jmap_rank", "}"]
    if w["kind"] == "mid":
        mid, k = num(w["mid"]), num(knee(scale))
        bodies[SCALE_LINEAR] = _side_bodies(inp, mid, [
            f"value = {p}_b", f"subtract = {inp}", f"divide = {p}_span_low", "multiply = -0.5", "add = 0.5"], [
            f"value = {inp}", f"subtract = {p}_a", f"divide = {p}_span_up", "multiply = 0.5", "add = 0.5"])
        # Logarithmic by the distance from the side's start, in knees: 1 + log2 of it, in straight pieces, which
        # below one knee is the distance itself, so the scale is straight from the midpoint and 0 at it.
        for side, dist, span in (("low", [f"value = {p}_b", f"subtract = {inp}"], f"{p}_span_low"),
                                 ("up", [f"value = {inp}", f"subtract = {p}_a"], f"{p}_span_up")):
            lines += _sv(f"{p}_sl_{side}_r", dist + [f"divide = {k}"])
            lines += _sv(f"{p}_sl_{side}_t", _log_ladder(f"{p}_sl_{side}_r") + ["add = 1"])
            lines += _sv(f"{p}_sl_{side}_span_r", [f"value = {span}", f"divide = {k}"])
            lines += _sv(f"{p}_sl_{side}_top", _log_ladder(f"{p}_sl_{side}_span_r") + ["add = 1", "min = 1"])
        bodies[SCALE_LOG] = _side_bodies(inp, mid, [
            f"value = {p}_sl_low_t", f"divide = {p}_sl_low_top", "multiply = -0.5", "add = 0.5"], [
            f"value = {p}_sl_up_t", f"divide = {p}_sl_up_top", "multiply = 0.5", "add = 0.5"])
    elif w["kind"] == "doubling":
        lines += _sv(f"{p}_span", [f"value = {p}_hi", f"subtract = {p}_lo"])
        bodies[SCALE_LINEAR] = [f"value = {inp}", f"subtract = {p}_lo", f"divide = {p}_span"]
        # Already a doubling at a time: Logarithmic is the map's own curve.
        bodies[SCALE_LOG] = [f"value = {p}_log", f"divide = {p}_log_span"]
    else:
        if scale["min_span"] / LOG_RATIO < LOG_FLOOR:
            raise ValueError(f"{n}: a {LOG_RATIO}th of its narrowest range, {scale['min_span']}, doesn't survive "
                             "the engine's five decimals; Logarithmic couldn't place its start")
        bodies[SCALE_LINEAR] = [f"value = {inp}", f"subtract = {p}_lo", f"divide = {p}_span"]
        # The start is the range's low, or a LOG_RATIO-th of its high where the low is smaller. The figure over
        # the start is then the smaller of figure / low and figure * LOG_RATIO / high, which is how it is worked
        # out: dividing by the small start itself would lose most of its five decimals. _lg_min is only compared.
        low_start = ["if = {", f"\tlimit = {{ {p}_lo > {p}_lg_min }}"]
        lines += _sv(f"{p}_lg_min", [f"value = {p}_hi", f"divide = {LOG_RATIO}"])
        lines += _sv(f"{p}_lg_r", [f"value = {inp}", f"multiply = {LOG_RATIO}", f"divide = {p}_hi"] + low_start +
                     [f"\tvalue = {inp}", f"\tdivide = {p}_lo", "}"])
        lines += _sv(f"{p}_lg_t", _log_ladder(f"{p}_lg_r"))
        lines += _sv(f"{p}_lg_span_r", [f"value = {LOG_RATIO}"] + low_start +
                     [f"\tvalue = {p}_hi", f"\tdivide = {p}_lo", "}"])
        # A range under one doubling wide is straight (the log's first piece); never divided by nothing.
        lines += _sv(f"{p}_lg_top", _log_ladder(f"{p}_lg_span_r") + ["min = 0.001"])
        bodies[SCALE_LOG] = [f"value = {p}_lg_t", f"divide = {p}_lg_top"]
    return lines, bodies


def fitted_factor(scale):
    """te_jmap_<name>_factor and the script values its curve is drawn through, for a map fitted to the world. A
    factor the Map Room reads branches on its Scale option, the map's own curve first; a factor a system's own
    entry reads is the map's own curve alone."""
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
        body = _side_bodies(inp, mid, low, up)
    else:
        # log2 in straight pieces between powers of two, of x over the world's low, over the same of the high.
        lines += _sv(f"{p}_ratio", [f"value = {inp}", f"divide = {p}_lo"])
        lines += _sv(f"{p}_log", _log_ladder(f"{p}_ratio"))
        lines += _sv(f"{p}_span_ratio", [f"value = {p}_hi", f"divide = {p}_lo"])
        lines += _sv(f"{p}_log_span", _log_ladder(f"{p}_span_ratio") + ["min = 1"])
        body = [f"value = {p}_log", f"divide = {p}_log_span"]
    if in_room(scale):
        # The Scale option: the map's own curve first, so a default paint pays one comparison.
        values, bodies = scale_bodies(scale)
        lines += values
        switch = ["if = {", f"\tlimit = {{ te_jmap_scale = {SCALE_OWN} }}"] + _indent(body) + ["}"]
        for setting in (SCALE_LINEAR, SCALE_LOG):
            switch += ["else_if = {", f"\tlimit = {{ te_jmap_scale = {setting} }}"] + _indent(bodies[setting]) + ["}"]
        switch += ["else = {"] + _indent(bodies[SCALE_RANKED]) + ["}"]
        body = switch
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


def option_values():
    """The script values the Map Room's options act through: the count a range's measure takes, the states each end
    leaves out of it, what the pick's map was last measured over (for the page), and whether the pick has a range at
    all. Any scope: they read globals and the options (te_jmap_trim, te_jmap_area: te_journal_map_values.txt)."""
    def stored(name, var):
        return _sv(name, ["value = 0", "if = {", f"\tlimit = {{ has_global_variable = {var} }}",
                          f"\tvalue = global_var:{var}", "}"])

    lines = ["", "# ---- The Map Room's options (the generator's header): what a range counts and leaves out ----",
             "# The states with a figure the range being measured counted (te_jmap_n, set by te_jmap_range_<map>)."]
    lines += stored("te_jmap_states", "te_jmap_n")
    lines += ["# The states each end of it leaves out (te_jmap_k, from te_jmap_trim_count or _entry)."]
    lines += stored("te_jmap_cut", "te_jmap_k")
    lines += ["# The most an end can leave out with two states still left to span: a short list is never trimmed past",
              "# its middle (ordered_state's position past the end takes the last state, it doesn't skip)."]
    lines += _sv("te_jmap_trim_most", ["value = te_jmap_states", "subtract = 2", "divide = 2", "floor = yes", "min = 0"])
    lines += [f"# The Map Room's trim, by its Outliers option (te_jmap_trim): {TRIM} at each end by default, and under a",
              f"# limited area at most one state in {AREA_TRIM_PART}; none; or {num(TRIM_SHARE * 100)}% of the states "
              "with a figure. Never past",
              f"# te_jmap_trim_most, nor {TRIM_MAX}, the last literal position te_jmap_measure_at holds."]
    lines += _sv("te_jmap_trim_count", [
        f"value = {TRIM}",
        "if = {", f"\tlimit = {{ te_jmap_trim = {TRIM_NONE} }}", "\tvalue = 0", "}",
        "else_if = {", f"\tlimit = {{ te_jmap_trim = {TRIM_PERCENT} }}", "\tvalue = te_jmap_states",
        f"\tmultiply = {num(TRIM_SHARE)}", "\tfloor = yes", "}",
        "else_if = {", "\tlimit = { te_jmap_area > 0 }", "\tvalue = te_jmap_states", f"\tdivide = {AREA_TRIM_PART}",
        "\tfloor = yes", f"\tmax = {TRIM}", "}",
        "max = te_jmap_trim_most", f"max = {TRIM_MAX}"])
    lines += ["# A system's own entry: the default trim over the whole world, whatever the Map Room's options."]
    lines += _sv("te_jmap_trim_count_entry", [f"value = {TRIM}", "max = te_jmap_trim_most"])
    lines += ["# What the pick's map was last measured over, for the Map Room's page (te_jmap_shown_n, te_jmap_shown_k:",
              "# a copy the Map Room's ranges keep, since the entries' ranges count into te_jmap_n and te_jmap_k too)."]
    lines += stored("te_jmap_shown_states", "te_jmap_shown_n")
    lines += stored("te_jmap_shown_cut", "te_jmap_shown_k")
    lines += ["# ---- The Scale option's Ranked setting: what te_jmap_rank_<map>'s walk reads and writes ----",
              "# The place the walk has reached (te_jmap_i: the number of distinct figures so far, less one on a map",
              "# ranked from its lowest, where the first place is 0) and the figure of the state before",
              "# (te_jmap_prev). Read through these, never as bare globals: a tooltip that walked an option's effect",
              "# would find them unset."]
    lines += stored("te_jmap_rank_place", "te_jmap_i")
    lines += stored("te_jmap_rank_prev", "te_jmap_prev")
    lines += ["# The divisor that turns a place into 0-1: the last place, at least 1 (one distinct figure: every state",
              "# at the low color, or at the midpoint's on a side with one figure)."]
    lines += _sv("te_jmap_rank_top", ["value = te_jmap_rank_place", "min = 1"])
    lines += ["# A state's place as its factor (state scope: the walk stored the place itself in te_jmap_rank). From",
              "# the lowest: 0 to 1. On a side of a midpoint, outward: 0.5 down to 0 below it, 0.5 up to 1 above."]

    def share(name, ops):
        return _sv(name, ["value = 0", "if = {", "\tlimit = { has_variable = te_jmap_rank }",
                          "\tvalue = var:te_jmap_rank", "\tdivide = te_jmap_rank_top"] + ["\t" + op for op in ops] +
                   ["}"])

    lines += share("te_jmap_rank_share", [])
    lines += share("te_jmap_rank_share_low", ["multiply = -0.5", "add = 0.5"])
    lines += share("te_jmap_rank_share_up", ["multiply = 0.5", "add = 0.5"])
    sels = sorted({s["sel"] for s in SCALES if fitted(s) and in_room(s)})
    lines += ["# 1 while the pick is a map fitted to a range, which the Outliers option acts on; 0 on a map of categories",
              "# or on a fixed scale, which has no range to trim."]
    lines += _sv("te_jmap_pick_fitted", ["value = 0", "if = {", "\tlimit = {", "\t\tOR = {"] +
                 [f"\t\t\tte_jmap_selector = {sel}" for sel in sels] + ["\t\t}", "\t}", "\tvalue = 1", "}"])
    return lines


def color_values():
    """What the Color option's shared branches ask about the state being painted (state scope): whether the pick's
    own lerp branch would paint it and on which ramp, and its factor, whole and a quarter at a time."""
    rows = sorted((s for s in SCALES if fitted(s) and in_room(s)), key=lambda s: s["sel"])
    lines = ["", "# ---- The Color option (the generator's header): the pick's ramp and factor, for the shared branches ----",
             f"# {RAMP_NONE} where the pick's own lerp branch wouldn't paint this state (no figure, none, off the scale, or a",
             f"# pick with no range), {RAMP_SEQ} where it would and the pick runs one way, {RAMP_DIV} where it would and the "
             "pick runs both",
             "# ways from a midpoint. Each row repeats its lerp branch's limit; a figure is read only inside its",
             "# has_variable guard."]
    body = ["value = 0"]
    for i, scale in enumerate(rows):
        guards = [ln for ln in painted(scale) if ln.startswith("has_variable = ")]
        rest = [ln for ln in painted(scale) if not ln.startswith("has_variable = ")]
        limit = " ".join([f"te_jmap_selector = {scale['sel']}"] + guards)
        body += ["if = {" if i == 0 else "else_if = {", f"\tlimit = {{ {limit} }}"]
        if rest:
            body += ["\tif = {", f"\t\tlimit = {{ {' '.join(rest)} }}", f"\t\tvalue = {pick_ramp(scale)}", "\t}"]
        else:
            body += [f"\tvalue = {pick_ramp(scale)}"]
        body += ["}"]
    lines += _sv("te_jmap_pick_ramp", body)
    lines += ["# The picked map's factor, 0-1, under the Scale option as every factor is (each tree guards its own read)."]
    body = ["value = 0"]
    for i, scale in enumerate(rows):
        body += ["if = {" if i == 0 else "else_if = {", f"\tlimit = {{ te_jmap_selector = {scale['sel']} }}",
                 f"\tvalue = te_jmap_{scale['name']}_factor", "}"]
    lines += _sv("te_jmap_pick_factor", body)
    lines += [f"# The factor along each of a shared ramp's {RAMP_LERPS} lerps: the paint takes the first whose end the factor is",
              "# under (te_jmap_pick_factor < 0.25, 0.5, 0.75; the last takes the rest)."]
    for n in range(1, RAMP_LERPS + 1):
        start = (n - 1) / RAMP_LERPS
        lines += _sv(f"te_jmap_pick_q{n}", ["value = te_jmap_pick_factor"] + ([f"subtract = {num(start)}"] if start else []) +
                     [f"multiply = {RAMP_LERPS}", "min = 0", "max = 1"])
    return lines


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
            if scale.get("twin_of"):
                lines.append(f"# The Map Room's own copy of te_jmap_{scale['twin_of']}_*: its range follows the Map "
                             "Room's options, the entry's doesn't.")
                lines.append(f"# {desc.capitalize()}; before its first measure, the entry's range.")
            else:
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
    lines += option_values()
    lines += color_values()
    return "\n".join(lines) + "\n"


def measured(scale):
    """The states a range counts and orders: those the map paints with its factor, and for a range the Map Room
    reads, only those in its area (te_jmap_in_area, te_journal_map_triggers.txt: no te_jmap_out on the state)."""
    return scale["where"] + (["te_jmap_in_area = yes"] if in_room(scale) else [])


def _limit(scale):
    limit = " ".join(measured(scale))
    return [f"\tlimit = {{ {limit} }}"] if limit else []


def _measure(scale, order, var):
    n = scale["name"]
    return ["ordered_state = {"] + _limit(scale) + [
        f"\torder_by = te_jmap_{n}_{order}",
        "\tposition = $K$",
        "\tcheck_range_bounds = no",
        f"\tset_global_variable = {{ name = te_jmap_rng_{n}_{var} value = te_jmap_{n}_input }}",
        "}",
    ]


def _rank_walk(scale, extra, order, newer, first):
    """One ordered walk that stores each state's place (te_jmap_rank): the states of `extra` among those the map
    measures, in `order`, a new place whenever the figure moves on (`newer`: > rising, < falling) from the state
    before; `first` is the place before the first (-1: the first place is 0; 0: it is 1)."""
    n = scale["name"]
    limit = " ".join(measured(scale) + extra)
    sentinel = "-1000000000" if newer == ">" else "1000000000"
    return [
        f"set_global_variable = {{ name = te_jmap_i value = {first} }}",
        f"set_global_variable = {{ name = te_jmap_prev value = {sentinel} }}",
        "ordered_state = {",
        f"\tlimit = {{ {limit} }}",
        f"\torder_by = te_jmap_{n}_{order}",
        "\tmin = 0",
        f"\tmax = {RANK_MAX}",
        "\tcheck_range_bounds = no",
        "\tif = {",
        f"\t\tlimit = {{ te_jmap_{n}_input {newer} te_jmap_rank_prev }}",
        "\t\tchange_global_variable = { name = te_jmap_i add = 1 }",
        f"\t\tset_global_variable = {{ name = te_jmap_prev value = te_jmap_{n}_input }}",
        "\t}",
        "\tset_variable = { name = te_jmap_rank value = te_jmap_rank_place }",
        "}",
    ]


def _rank_share(scale, extra, share):
    """The pass after a walk: each walked state's place becomes its factor (te_jmap_rank_share*)."""
    limit = " ".join(measured(scale) + extra + ["has_variable = te_jmap_rank"])
    return ["every_state = {", f"\tlimit = {{ {limit} }}",
            f"\tset_variable = {{ name = te_jmap_rank value = {share} }}", "}"]


def rank_effect(scale):
    """te_jmap_rank_<map>: the Scale option's Ranked setting. Each state the map measures gets its place in line as
    te_jmap_rank, 0-1 (the factor reads it as it is)."""
    n, w = scale["name"], scale["world"]
    body = ["set_global_variable = te_jmap_ranks"]
    if w["kind"] == "mid":
        mid = num(w["mid"])
        below, above = [f"te_jmap_{n}_input < {mid}"], [f"te_jmap_{n}_input > {mid}"]
        body += ["# Below the midpoint, the nearest first: 0.5 down to 0."]
        body += _rank_walk(scale, below, "input", "<", 0) + _rank_share(scale, below, "te_jmap_rank_share_low")
        body += ["# Above it, the nearest first: 0.5 up to 1."]
        body += _rank_walk(scale, above, "input_neg", ">", 0) + _rank_share(scale, above, "te_jmap_rank_share_up")
        body += ["# At the midpoint itself: its color.",
                 "every_state = {", f"\tlimit = {{ {' '.join(measured(scale) + [f'te_jmap_{n}_input = {mid}'])} }}",
                 "\tset_variable = { name = te_jmap_rank value = 0.5 }", "}"]
    else:
        body += ["# From the lowest: 0 to 1."]
        body += _rank_walk(scale, [], "input_neg", ">", -1) + _rank_share(scale, [], "te_jmap_rank_share")
    return _sv(f"te_jmap_rank_{n}", body)


def render_effects():
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_journal_map_scales.py — do not edit manually.",
        "# The Map Room's maps fitted to the world (te_journal_map_scales_generated.txt). Each te_jmap_range_<map>",
        "# measures a map's range into te_jmap_rng_<map>_lo / _hi: it counts the states the map paints with a figure",
        "# (te_jmap_n), works out how many each end leaves out (te_jmap_k), and has te_jmap_measure_at take the state",
        "# at that place from the top and from the bottom (te_jmap_measure_<map>, K a literal: position takes no",
        f"# script value). By default the {TRIM + 1}th highest and the {TRIM + 1}th lowest; never past the middle of a "
        "short list; no",
        "# state with a figure, and the globals stay unset (the fixed curve's ends). A range the Map Room reads counts",
        "# only the states in the Map Room's area (te_jmap_in_area) and takes its Outliers option's trim",
        "# (te_jmap_trim_count); a range a system's own entry reads (te_jmap_range_gw, _gm) is the whole world's on the",
        "# default trim, whatever the options, and the Map Room reads its twin (_room). Any scope: every_state and",
        "# ordered_state walk the world's states. te_jmap_refresh_range measures the pick's map (te_jmap_set_selector",
        "# and te_jmap_apply_options, te_journal_map_effects.txt; and monthly, te_journal_map_on_actions.txt),",
        "# te_jmap_refresh_entry_ranges the entries' own.",
        "",
        "# A range's two ends, at the trim te_jmap_range_<map> just worked out (te_jmap_cut) from the count it took",
        "# (te_jmap_states; none, and nothing is measured). MAP: the range's name. One literal position per count.",
    ]
    ladder = []
    for k in range(TRIM_MAX + 1):
        if k == TRIM_MAX:
            ladder += ["else = {"]
        else:
            ladder += ["else_if = {" if k else "if = {", f"\tlimit = {{ te_jmap_cut < {k + 1} }}"]
        ladder += [f"\tte_jmap_measure_$MAP$ = {{ K = {k} }}", "}"]
    lines += _sv("te_jmap_measure_at", ["if = {", "\tlimit = { te_jmap_states > 0 }"] +
                 ["\t" + ln for ln in ladder] + ["}"])
    own = [s for s in SCALES if fitted(s) and range_name(s) == s["name"]]
    for scale in own:
        n = scale["name"]
        body = []
        for end in ("lo", "hi"):
            body += ["if = {", f"\tlimit = {{ has_global_variable = te_jmap_rng_{n}_{end} }}",
                     f"\tremove_global_variable = te_jmap_rng_{n}_{end}", "}"]
        body += ["set_global_variable = { name = te_jmap_n value = 0 }", "every_state = {"] + _limit(scale) + [
            "\tchange_global_variable = { name = te_jmap_n add = 1 }", "}"]
        trim = "te_jmap_trim_count" if in_room(scale) else "te_jmap_trim_count_entry"
        body += [f"set_global_variable = {{ name = te_jmap_k value = {trim} }}",
                 f"te_jmap_measure_at = {{ MAP = {n} }}"]
        if in_room(scale):
            body += ["# What the Map Room's page says the map was measured over.",
                     "set_global_variable = { name = te_jmap_shown_n value = te_jmap_states }",
                     "set_global_variable = { name = te_jmap_shown_k value = te_jmap_cut }"]
        whose = ("The Map Room's range, under its options" if in_room(scale)
                 else "The entry's own range: the whole world, the default trim")
        lines += ["", f"# {scale['note']}.", f"# {whose}."] + _sv(f"te_jmap_range_{n}", body)
        lines += ["# Its two ends: the state K places from the top, and from the bottom."]
        lines += _sv(f"te_jmap_measure_{n}", _measure(scale, "input", "hi") + _measure(scale, "input_neg", "lo"))
    picks = sorted((s["sel"], range_name(s)) for s in SCALES if fitted(s) and in_room(s))
    body = ["# One rank variable serves every map: no place outlives the pick or the setting it was taken under.",
            "te_jmap_clear_ranks = yes"]
    for i, (sel, rn) in enumerate(picks):
        body += ["else_if = {" if i else "if = {", f"\tlimit = {{ te_jmap_selector = {sel} }}",
                 f"\tte_jmap_range_{rn} = yes", "}"]
    body += ["# The Scale option's Ranked setting: the pick's places, taken with its range.",
             "if = {", f"\tlimit = {{ te_jmap_scale = {SCALE_RANKED} }}", "\tte_jmap_refresh_rank = yes", "}"]
    lines += ["", "# The pick's map, if it is fitted to the world (te_jmap_selector, te_journal_map_values.txt)."]
    lines += _sv("te_jmap_refresh_range", body)

    lines += ["", "# ---- Ranked (the Scale option): each state's place in line, stored for the paint ----",
              "# te_jmap_rank_<map> walks the states the map measures (those in the Map Room's area), lowest figure",
              "# first, and stores each one's place as te_jmap_rank, 0 to 1, which te_jmap_<map>_factor reads under",
              "# Ranked. Equal figures share a place, and each distinct figure is one step. A map with a meaningful",
              "# midpoint is ranked on each side of it, outward, so the midpoint keeps its color. The walk is",
              f"# ordered_state with min = 0 and max = {RANK_MAX} (a place is a count the body keeps, not a position);",
              "# the pass after it divides each place by the last. Each map by its own figure, though Current Comfort",
              "# shares Base Comfort's range. te_jmap_refresh_range runs the pick's after its range, having cleared",
              "# every place first: a pick, an option click and each month's pulse.",
              "", "# Every place off every state, where any was stored (te_jmap_ranks)."]
    lines += _sv("te_jmap_clear_ranks", [
        "if = {", "\tlimit = { has_global_variable = te_jmap_ranks }",
        "\tevery_state = {", "\t\tlimit = { has_variable = te_jmap_rank }", "\t\tremove_variable = te_jmap_rank", "\t}",
        "\tremove_global_variable = te_jmap_ranks", "}"])
    ranked = [s for s in SCALES if fitted(s) and in_room(s)]
    for scale in ranked:
        lines += ["", f"# {scale['note']}."] + rank_effect(scale)
    body = []
    for i, scale in enumerate(sorted(ranked, key=lambda s: s["sel"])):
        body += ["else_if = {" if i else "if = {", f"\tlimit = {{ te_jmap_selector = {scale['sel']} }}",
                 f"\tte_jmap_rank_{scale['name']} = yes", "}"]
    lines += ["", "# The pick's places, if it is fitted to the world."]
    lines += _sv("te_jmap_refresh_rank", body)
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
