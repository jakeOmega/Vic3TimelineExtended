#!/usr/bin/env python3
"""Write the demographics script that mirrors scripts/analysis/demographics_model.py.

Usage:
    python3 scripts/generators/gen_demographics.py            # write the two files
    python3 scripts/generators/gen_demographics.py --check    # exit 1 if either is stale

Spec: docs/superpowers/specs/2026-10-08-demographics-design.md; plan:
docs/superpowers/archive/plans/2026-10-08-demographics-phases-0-1.md (Task 6). Inputs:
scripts/analysis/demographics_params.py (every rate, weight and table),
common/defines/extra_defines.txt (the engine's growth curves, through pop_growth.py),
common/buy_packages/00_buy_packages.txt (spending per head by wealth) and the land-reform
laws (vanilla_parsed/common/laws.json and common/laws/, for variants' parents). Not a post-load
regenerator: run it after changing any of those; test_gen_demographics.py fails CI when
the committed files are stale.

What it writes (the hand-written logic is in te_demog_effects.txt / te_demog_values.txt):
    common/scripted_effects/te_demog_generated_effects.txt
        te_demog_sweep, te_demog_seed_sweep     the ring in age order, two guarded passes
        te_demog_enter_group                    a group's death rates, fertility, next start
        te_demog_flush_band, te_demog_flush_class
        te_demog_enter_class                    a migrant class's gain and loss shares (reads te_dg_acls,
                                                te_dg_mig_in/_out, te_dg_pf<c>/pm<c>, var:te_dg_cf<c>/cm<c>;
                                                writes te_dg_mig_gain_f/_m, te_dg_mig_frac_f/_m)
        te_demog_normalize_slots, te_demog_normalize_bands
                                                the seed's raw ring (radix 100,000) to people: each value
                                                x local_var:te_dg_norm_e5, then / 100000 (two steps keep a
                                                small state precise); slots, then bands, class sums, the pool's
                                                sums (phase 2 step 4)
        te_demog_life_table, te_demog_set_growth_factor
        te_demog_old_age_pass                   the old-age threshold (phase 2 step 1), at the life table's end
        te_demog_enter_cal_band, te_demog_enter_bio_band
                                                the sweep's calendar band (the working-age start) and biological
                                                band (capacity, health need), phase 2 step 1
        te_demog_slot_births                    a cohort's births: today's single term while the planned and
                                                unplanned schedules are one, else two terms (phase 2 step 1)
        te_demog_add_bands_to_root, te_demog_reset_country_bands, te_demog_scale_bands
        te_demog_gini_band_init, _add, _store, _load, _zero, _add_state
                                                the Gini's 41 wealth bands: the walk's sums (each pop's
                                                stand-in income computed in its band's leaf), a state's
                                                store (only bands with people, and the layout), the
                                                country's sum (spec 4.1)
        te_demog_gini_from_locals               the Gini over the bands in order, the panel's figure
        te_demog_set_profile                    the migrant profile per class and sex
        te_demog_migrant_rates                  the migrant booking's cap: each class and sex's rate and the flat
                                                rate over everyone (te_dg_mr_f<c>/mr_m<c>, te_dg_mig_flat; 2026-10-12)
        te_demog_band_figures                   total, young, working, old, women 15-49, 20-59 sums, median
        te_demog_project                        the bands twenty years ahead (a display outline)
        te_demog_debug_log_ring_before / _after  (Task 15's replay lines)
        te_demog_practices_seed, _step, _country_init, _country_add, _country_store
                                                each practice's turn of te_demog_practice_effects.txt (Late
                                                Marriage and Birth Spacing; the late-marriage plan)
        te_demog_cause_deaths_estimate          each natural cause's deaths at the step's rates over the bands, the
                                                Causes of Death section's estimate (issue #1029; demographics_model
                                                .band_cause_rates)
    common/script_values/te_demog_generated_values.txt
        per-pop engine curves and wealth TFR; per-state cause multipliers (reads of the
        demographics modifier types: medicine as 1 - access x treatment), women's work share, the means and
        the land-tenure term; the practices' start ladders, erosions, seeds, targets and terms
        (te_demog_pr_*, te_demog_marriage_age); te_demog_k_* constants; the 10-14s' work share and the pops'
        base working-adult ratios (te_demog_child_work, te_demog_pop_base_ratio; phase 2 step 1); phase 2 step 4's
        constants and band sums (consequence_values); per-slot debug shares
    common/static_modifiers/te_demog_line_modifiers_generated.txt, common/script_values/te_demog_line_values_generated.txt,
    common/scripted_effects/te_demog_line_effects_generated.txt
        the moved birth and mortality lines' pairs and their refresh (te_demog_lines_refresh; the engine-lines plan)
    common/static_modifiers/te_demog_workforce_line_modifiers_generated.txt,
    common/script_values/te_demog_workforce_line_values_generated.txt,
    common/scripted_effects/te_demog_workforce_line_effects_generated.txt
        the working-adult pair and its refresh (te_demog_workforce_lines_refresh; phase 2 step 1, Task 6)
    common/script_values/te_demog_spread_values_generated.txt,
    common/scripted_effects/te_demog_spread_effects_generated.txt
        phase 3's spreading machinery: the practices' neighbour walk (te_demog_practices_neighbours), Family
        Limitation's target and church weight, Cultural Hegemony's exposure, and their constants; the hand-written
        logic is te_demog_fl_effects.txt and te_demog_practice_effects.txt
    common/scripted_effects/te_demog_resettle_generated_effects.txt,
    common/script_values/te_demog_resettle_generated_values.txt
        Internal Resettlement's known moves and the US frontier's 1836 seed (gen_demographics_resettle.py, 2026-10-19);
        the hand-written logic is te_demog_resettle_effects.txt
"""

import argparse
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))   # gen_demographics_lx (phase 3)

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_regions as R  # noqa: E402
import pop_growth as G  # noqa: E402

EFFECTS = Path("common/scripted_effects/te_demog_generated_effects.txt")
VALUES = Path("common/script_values/te_demog_generated_values.txt")
# the engine's moved birth and mortality lines (owner, 2026-10-11; the engine-lines plan, Task 4)
LINE_MODIFIERS = Path("common/static_modifiers/te_demog_line_modifiers_generated.txt")
LINE_VALUES = Path("common/script_values/te_demog_line_values_generated.txt")
LINE_EFFECTS = Path("common/scripted_effects/te_demog_line_effects_generated.txt")
WORKFORCE_LINE_MODIFIERS = Path("common/static_modifiers/te_demog_workforce_line_modifiers_generated.txt")
WORKFORCE_LINE_VALUES = Path("common/script_values/te_demog_workforce_line_values_generated.txt")
WORKFORCE_LINE_EFFECTS = Path("common/scripted_effects/te_demog_workforce_line_effects_generated.txt")
# phase 3: the spreading machinery (the practices' neighbour spread, Family Limitation, Cultural Hegemony's drift)
SPREAD_VALUES = Path("common/script_values/te_demog_spread_values_generated.txt")
SPREAD_EFFECTS = Path("common/scripted_effects/te_demog_spread_effects_generated.txt")
BUY_PACKAGES = Path("common/buy_packages/00_buy_packages.txt")
HEADER = ("# AUTO-GENERATED by scripts/generators/gen_demographics.py - do not edit manually.\n"
          "# docs/superpowers/specs/2026-10-08-demographics-design.md; parameters in\n"
          "# scripts/analysis/demographics_params.py.\n")
N = P.RING_YEARS
DEFINES = Path("common/defines/extra_defines.txt")
# The Gini's bands are the income stand-in's pieces: each band's top is a knot, and the last band's
# piece ends at the top wealth level.
assert P.GINI_INCOME_KNOTS[:-1] == P.GINI_BAND_KNOTS, "the Gini's bands are the income stand-in's pieces"
assert P.GINI_INCOME_KNOTS[-1] == P.GINI_TOP_WEALTH > P.GINI_BAND_KNOTS[-1]
# Every tenth of a net reproduction rate across the model's table, M.NRR_TABLE_MIN .. M.NRR_TABLE_MAX.
NRR_STEP = 0.1
NRR_KNOTS = [round(M.NRR_TABLE_MIN + NRR_STEP * i, 1)
             for i in range(round((M.NRR_TABLE_MAX - M.NRR_TABLE_MIN) / NRR_STEP) + 1)]
CAUSES = ("infection", "work", "external", "maternal", "chronic")
assert tuple(P.CAUSE_FACTORS) == CAUSES, "the factor table names the five causes in the census's order"


def lit(x):
    """A script literal: at most five decimals, no trailing zeros."""
    d = Decimal(repr(float(x))).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)
    text = format(d.normalize(), "f")
    return "0" if text in ("-0", "") else text


class Out:
    """Tab-indented text that matches scripts/format_paradox_tabs.py."""

    def __init__(self):
        self.lines = []
        self.depth = 0

    def __call__(self, text=""):
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                self.lines.append("")
                continue
            if line.startswith("}"):
                self.depth -= 1
            self.lines.append("\t" * self.depth + line)
            self.depth += line.count("{") - line.count("}") + (1 if line.startswith("}") else 0)

    def text(self):
        assert self.depth == 0, self.depth
        return "\n".join(self.lines).rstrip("\n") + "\n"


def tree(o, var, lo, hi, leaf):
    """A balanced if/else tree on local_var:<var> over lo..hi; leaf(o, i) writes branch i."""
    if lo == hi:
        leaf(o, lo)
        return
    mid = (lo + hi) // 2
    o("if = {")
    o(f"limit = {{ local_var:{var} <= {mid} }}")
    tree(o, var, lo, mid, leaf)
    o("}")
    o("else = {")
    tree(o, var, mid + 1, hi, leaf)
    o("}")


# ---- effects ------------------------------------------------------------------------

def sweeps(o):
    o("# The yearly step's sweep: pass 1 visits slots open-1 .. 0 (ages 1 .. open), pass 2")
    o("# slots 149 .. open (ages open+1 .. 150), so te_demog_slot sees ages in order.")
    o("te_demog_sweep = {")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_slot_p1 = {{ S = {k} }}")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_slot_p2 = {{ S = {k} }}")
    o("}")
    o("")
    o("# The seed's sweep: ages 0 .. open, then open+1 .. 149.")
    o("te_demog_seed_sweep = {")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_seed_p1 = {{ S = {k} }}")
    for k in range(N - 1, -1, -1):
        o(f"te_demog_seed_p2 = {{ S = {k} }}")
    o("}")
    o("")


def _rate(o, name, terms):
    """A sum of terms, each a local (or a tuple of locals, multiplied) x a literal."""
    terms = [(m if isinstance(m, tuple) else (m,), v) for m, v in terms if v]
    o("set_local_variable = {")
    o(f"name = {name}")

    def term(ms, v):
        o(f"value = local_var:{ms[0]}")
        for m in ms[1:]:
            o(f"multiply = local_var:{m}")
        o(f"multiply = {lit(v)}")

    if not terms:
        o("value = 0")
    else:
        o("value = {")
        (m0, v0), rest = terms[0], terms[1:]
        term(m0, v0)
        for m, v in rest:
            o("add = {")
            term(m, v)
            o("}")
        o("max = 100000")
        o("}")
    o("}")


def enter_group(o):
    o("# THIS = a state. local_var:te_dg_g = the age group (demographics_params.GROUPS); sets")
    o("# te_dg_qf / te_dg_qm (death probability a year per 100,000), te_dg_asfr (share of a")
    o("# lifetime's births at each single age, per 100,000) and te_dg_next_group (the next")
    o("# group's first age) from the cause multipliers te_dg_m_inf, te_dg_m_work_f,")
    o("# te_dg_m_work_m, te_dg_m_ext and te_dg_m_chr and, on infection at the adults' ages, the")
    o("# adults' infection factor te_dg_inf_ad (te_demog_prepare; demographics_model.rates_from_multipliers).")
    o("te_demog_enter_group = {")

    def leaf(o, g):
        inf = ("te_dg_m_inf", "te_dg_inf_ad") if g in M.INFECTION_ADULT_GROUPS else "te_dg_m_inf"
        _rate(o, "te_dg_qf", [(inf, P.INFECTION["f"][g]), ("te_dg_m_work_f", P.WORK_BASE[g]),
                              ("te_dg_m_ext", P.EXTERNAL["f"][g]), ("te_dg_m_chr", P.CHRONIC["f"][g])])
        _rate(o, "te_dg_qm", [(inf, P.INFECTION["m"][g]), ("te_dg_m_work_m", P.WORK_BASE[g]),
                              ("te_dg_m_ext", P.EXTERNAL["m"][g]), ("te_dg_m_chr", P.CHRONIC["m"][g])])
        start = P.GROUPS[g][0]
        o(f"set_local_variable = {{ name = te_dg_asfr value = {lit(M.asfr_planned(start))} }}")
        if P.ASFR_PLANNED_SHAPE is not P.ASFR_UNPLANNED_SHAPE:
            # the unplanned schedule (late-game §3.1); its rate age is the calendar one until phase 3's per-slot lookup
            o(f"set_local_variable = {{ name = te_dg_asfr_un value = {lit(M.asfr_unplanned(start))} }}")
        nxt = P.GROUPS[g + 1][0] if g + 1 < len(P.GROUPS) else 999
        o(f"set_local_variable = {{ name = te_dg_next_group value = {nxt} }}")

    tree(o, "te_dg_g", 0, len(P.GROUPS) - 1, leaf)
    o("}")
    o("")


def bands_and_classes(o):
    o("# THIS = a state. Writes the running band sums into band local_var:te_dg_band.")
    o("te_demog_flush_band = {")
    tree(o, "te_dg_band", 0, P.BANDS - 1, lambda o, b: (
        o(f"set_variable = {{ name = te_dg_bf{b} value = local_var:te_dg_acc_bf }}"),
        o(f"set_variable = {{ name = te_dg_bm{b} value = local_var:te_dg_acc_bm }}")))
    o("}")
    o("")
    o("# THIS = a state. Writes the running class sums into class local_var:te_dg_cls.")
    o("te_demog_flush_class = {")
    tree(o, "te_dg_cls", 0, len(P.MIGRANT_CLASSES) - 1, lambda o, c: (
        o(f"set_variable = {{ name = te_dg_cf{c} value = local_var:te_dg_acc_cf }}"),
        o(f"set_variable = {{ name = te_dg_cm{c} value = local_var:te_dg_acc_cm }}")))
    o("}")
    o("")
    o("# THIS = a state. On entering the migrant class of local_var:te_dg_acls (the class of the")
    o("# RATE age, a - 1): the share of one cohort of the class that arrives (te_dg_mig_gain_f / _m) or")
    o("# departs (te_dg_mig_frac_f / _m): the class and sex's rate from te_demog_migrant_rates")
    o("# (te_dg_mr_f<c> / te_dg_mr_m<c>) plus the flat rate (te_dg_mig_flat), on whichever of")
    o("# te_dg_mig_in and te_dg_mig_out is above 0. Both are zero for a class whose last-year sum is under")
    o("# one person (demographics_model.migrant_rates).")
    o("te_demog_enter_class = {")

    def leaf(o, c):
        for sex, last in (("f", f"te_dg_cf{c}"), ("m", f"te_dg_cm{c}")):
            rate = f"value = {{ value = local_var:te_dg_mr_{sex}{c} add = local_var:te_dg_mig_flat }}"
            o(f"set_local_variable = {{ name = te_dg_mig_gain_{sex} value = 0 }}")
            o(f"set_local_variable = {{ name = te_dg_mig_frac_{sex} value = 0 }}")
            o("if = {")
            o(f"limit = {{ var:{last} >= 1 local_var:te_dg_mig_in > 0 }}")
            o(f"set_local_variable = {{ name = te_dg_mig_gain_{sex} {rate} }}")
            o("}")
            o("else_if = {")
            o(f"limit = {{ var:{last} >= 1 local_var:te_dg_mig_out > 0 }}")
            o(f"set_local_variable = {{ name = te_dg_mig_frac_{sex} {rate} }}")
            o("}")
    tree(o, "te_dg_acls", 0, len(P.MIGRANT_CLASSES) - 1, leaf)
    o("}")
    o("")


def normalizers(o):
    """The seed's raw ring (survivorship radix 100,000) to people, in two multiplies so a small state keeps its digits."""
    two_step = ("change_variable = {{ name = {v} multiply = local_var:te_dg_norm_e5 }}",
                "change_variable = {{ name = {v} divide = 100000 }}")
    o("# THIS = a state, seed only. local_var:te_dg_norm_e5 = population x 100,000 / the raw ring's total.")
    o("# Turns every slot of the raw ring (radix 100,000) into people: x te_dg_norm_e5, then / 100000.")
    o("te_demog_normalize_slots = {")
    for k in range(N):
        for s in ("f", "m"):
            o("if = {")
            o(f"limit = {{ has_variable = te_dg_{s}{k} }}")
            for step in two_step:
                o(step.format(v=f"te_dg_{s}{k}"))
            o("}")
    o("}")
    o("")
    o("# THIS = a state, seed only. The same two steps on the bands, the class sums and the pool's sums (phase 2 step 4).")
    o("te_demog_normalize_bands = {")
    names = [f"te_dg_b{s}{b}" for b in range(P.BANDS) for s in ("f", "m")]
    names += [f"te_dg_c{s}{c}" for c in range(len(P.MIGRANT_CLASSES)) for s in ("f", "m")]
    names += POOL_SUMS
    for name in names:
        for step in two_step:
            o(step.format(v=name))
    o("}")
    o("")


def life_table(o):
    o("# THIS = a state. The life table over the age groups in order (demographics_model.life_table),")
    o("# plus the NRR's survival-weighted fertility sum. Needs te_dg_m_* (te_demog_prepare).")
    o("te_demog_life_table = {")
    o("set_local_variable = { name = te_dg_lf value = 100000 }")
    o("set_local_variable = { name = te_dg_lm value = 100000 }")
    o("set_local_variable = { name = te_dg_pyf value = 0 }")
    o("set_local_variable = { name = te_dg_pym value = 0 }")
    o("set_local_variable = { name = te_dg_nrr_sum value = 0 }")
    for g, (start, width) in enumerate(P.GROUPS):
        o(f"set_local_variable = {{ name = te_dg_g value = {g} }}")
        o("te_demog_enter_group = yes")
        if start >= P.OLD_AGE_FROM:
            # survivors and person-years at the group's start, for the old-age threshold (te_demog_old_age_pass)
            for s in "fm":
                o(f"set_local_variable = {{ name = te_dg_oal{start}{s} value = local_var:te_dg_l{s} }}")
                o(f"set_local_variable = {{ name = te_dg_oapy{start}{s} value = local_var:te_dg_py{s} }}")
        if start == 65:
            o("set_local_variable = { name = te_dg_l65f value = local_var:te_dg_lf }")
            o("set_local_variable = { name = te_dg_l65m value = local_var:te_dg_lm }")
            o("set_local_variable = { name = te_dg_py65f value = local_var:te_dg_pyf }")
            o("set_local_variable = { name = te_dg_py65m value = local_var:te_dg_pym }")
        if g == 0:
            o("set_variable = { name = te_dg_imr value = { value = local_var:te_dg_qf add = local_var:te_dg_qm "
              "divide = 200 } }")
        fertile = 15 <= start <= 45
        o(f"te_demog_lt_group = {{ N = {width} FERTILE = {'yes' if fertile else 'no'} }}")
    # the open last interval (2026-10-20): the survivors at 150 live on at the last group's rates, still in te_dg_q<f|m>
    o("te_demog_lt_finish = { QF = local_var:te_dg_qf QM = local_var:te_dg_qm }")
    o("te_demog_old_age_pass = yes")
    o("}")
    o("")


def cause_deaths_estimate(o):
    """Issue #1029's estimate (demographics_model.cause_deaths_estimate, method a): each natural cause's deaths at the
    step's rates, from the bands at the start of the step, at demographics_model.band_cause_rates' table."""
    r = M.band_cause_rates()
    o("# THIS = a state at its step, after te_demog_on_top_scales and before the sweep writes this count's bands (issue")
    o("# #1029; demographics_model.cause_deaths_estimate): each natural cause's deaths over the year at the step's rates,")
    o("# from the people the sweep takes its dead from, by the band they had at the last count (te_dg_bf<b>, te_dg_bm<b>,")
    o("# whose ages are the rate ages they die at now): the band's people x the cause's yearly deaths per 100,000 there at")
    o("# a multiplier of 1 (demographics_model.band_cause_rates: its age groups' rates, weighted by their person-years at")
    o("# the base rates) x the step's multiplier, work's by sex, and infection's at the adults' ages x te_dg_inf_ad too.")
    o("# Exact in the bands of one age group; approximate in 0-4")
    o("# and 85+. Sets the locals te_dg_ce_inf, te_dg_ce_ext, te_dg_ce_chr and te_dg_ce_work, which")
    o("# te_demog_cause_deaths_store scales to the census's deaths; a state in the late game replaces them with the late")
    o("# sweep's own count, its treated at their biological ages (te_demog_lx_cause_deaths).")
    o("te_demog_cause_deaths_estimate = {")

    def band_sum(terms):
        (v0, x0), rest = terms[0], terms[1:]
        o(f"value = var:{v0}")
        o(f"multiply = {lit(x0)}")
        for v, x in rest:
            o(f"add = {{ value = var:{v} multiply = {lit(x)} }}")

    for cause, short in (("infection", "inf"), ("external", "ext"), ("chronic", "chr")):
        def terms(bands):
            return [(f"te_dg_b{s}{b}", r[cause][s][b]) for b in bands for s in "fm" if r[cause][s][b]]
        o("set_local_variable = {")
        o(f"name = te_dg_ce_{short}")
        o("value = {")
        if cause == "infection":
            band_sum(terms([b for b in range(P.BANDS) if b not in M.INFECTION_ADULT_BANDS]))
            o("add = {")
            band_sum(terms(sorted(M.INFECTION_ADULT_BANDS)))
            o("multiply = local_var:te_dg_inf_ad")
            o("}")
        else:
            band_sum(terms(range(P.BANDS)))
        o(f"multiply = local_var:te_dg_m_{short}")
        o("divide = 100000")
        o("}")
        o("}")
    o("set_local_variable = {")
    o("name = te_dg_ce_work")
    o("value = {")
    band_sum([(f"te_dg_bf{b}", r["work"]["f"][b]) for b in range(P.BANDS) if r["work"]["f"][b]])
    o("multiply = local_var:te_dg_m_work_f")
    o("add = {")
    band_sum([(f"te_dg_bm{b}", r["work"]["m"][b]) for b in range(P.BANDS) if r["work"]["m"][b]])
    o("multiply = local_var:te_dg_m_work_m")
    o("}")
    o("divide = 100000")
    o("}")
    o("}")
    o("}")
    o("")


def old_age_pass(o):
    starts = [s for s, _w in P.GROUPS if s >= P.OLD_AGE_FROM]
    rem = P.OLD_AGE_REMAINING
    o("# THIS = a state, after te_demog_life_table's forward pass (phase 2 step 1; late-game §1.5): the age with")
    o(f"# {rem} years of life left (demographics_model.old_age_threshold), women's and men's averaged, into")
    o("# te_dg_old_age. Remaining life at each group start from OLD_AGE_FROM; linear between starts.")
    o("te_demog_old_age_pass = {")
    for s in "fm":
        for st in starts:
            o(f"set_local_variable = {{ name = te_dg_oae{st}{s} value = {{ value = local_var:te_dg_py{s} "
              f"subtract = local_var:te_dg_oapy{st}{s} divide = {{ value = local_var:te_dg_oal{st}{s} "
              f"min = 0.00001 }} }} }}")
        prev = None
        for st in starts:
            o(f"{'if' if prev is None else 'else_if'} = {{")
            o(f"limit = {{ local_var:te_dg_oae{st}{s} <= {rem} }}")
            if prev is None:
                o(f"set_local_variable = {{ name = te_dg_oa{s} value = {st} }}")
            else:
                o(f"set_local_variable = {{ name = te_dg_oa{s} value = {{ value = local_var:te_dg_oae{prev}{s} "
                  f"subtract = {rem} divide = {{ value = local_var:te_dg_oae{prev}{s} "
                  f"subtract = local_var:te_dg_oae{st}{s} min = 0.00001 }} multiply = {st - prev} add = {prev} }} }}")
            o("}")
            prev = st
        o("else = {")
        o(f"set_local_variable = {{ name = te_dg_oa{s} value = {starts[-1]} }}")
        o("}")
    o("set_variable = { name = te_dg_old_age value = { value = local_var:te_dg_oaf add = local_var:te_dg_oam "
      "multiply = 0.5 } }")
    o("}")
    o("")


def work_bands(o):
    cal = (0, P.CHILD_WORK_AGE, P.WORKING_AGE)
    o("# THIS = a state, in the sweep's age order (phase 2 step 1): the calendar band local_var:te_dg_cal sets")
    o("# te_dg_start, the working-age start's factor (demographics_model.start_factor), and te_dg_next_cal.")
    o("te_demog_enter_cal_band = {")

    def cal_leaf(o, i):
        start = {0: "0", 1: "local_var:te_dg_child_work", 2: "1"}[i]
        o(f"set_local_variable = {{ name = te_dg_start value = {start} }}")
        o(f"set_local_variable = {{ name = te_dg_next_cal value = {cal[i + 1] if i + 1 < len(cal) else 999} }}")

    tree(o, "te_dg_cal", 0, len(cal) - 1, cal_leaf)
    o("}")
    o("")
    o("# THIS = a state: the biological band local_var:te_dg_bio (P.BIO_BANDS) sets te_dg_cap (capacity), te_dg_needw")
    o("# (health need) and te_dg_next_bio. Its age is te_dg_ab, the calendar one until phase 3.")
    o("te_demog_enter_bio_band = {")
    bio = P.BIO_BANDS

    def bio_leaf(o, i):
        a = bio[i]
        # call 3's capacity input (te_dg_wk_capm, te_demog_work_setup) x the table, at most 1
        # (demographics_model.capacity_at)
        o(f"set_local_variable = {{ name = te_dg_cap value = {{ value = {lit(M.band_value(P.CAPACITY, a))} "
          "multiply = local_var:te_dg_wk_capm max = 1 } }")
        o(f"set_local_variable = {{ name = te_dg_needw value = {lit(M.band_value(P.HEALTH_NEED, a))} }}")
        o(f"set_local_variable = {{ name = te_dg_next_bio value = {bio[i + 1] if i + 1 < len(bio) else 999} }}")

    tree(o, "te_dg_bio", 0, len(bio) - 1, bio_leaf)
    o("}")
    o("")


def slot_births(o):
    o("# THIS = a state, in te_demog_age_slot: births from the cohort's women local_var:te_dg_f")
    o("# (demographics_model.slot_births). Planned births follow P.ASFR_PLANNED_SHAPE by calendar age and unplanned")
    o("# P.ASFR_UNPLANNED_SHAPE by biological age (late-game §3.1). While they are one schedule this is one term.")
    o("te_demog_slot_births = {")
    o("set_local_variable = {")
    o("name = te_dg_b")
    if P.ASFR_PLANNED_SHAPE is P.ASFR_UNPLANNED_SHAPE:
        o("value = { value = local_var:te_dg_f multiply = local_var:te_dg_asfr divide = 100000 "
          "multiply = local_var:te_dg_tfr }")
    else:
        o("value = {")
        o("value = local_var:te_dg_asfr")
        o("multiply = local_var:te_dg_sh_pl")
        o("add = { value = local_var:te_dg_asfr_un multiply = local_var:te_dg_sh_un }")
        o("multiply = local_var:te_dg_f")
        o("divide = 100000")
        o("multiply = local_var:te_dg_tfr")
        o("}")
    o("}")
    o("}")
    o("")


def growth_factor(o):
    o("# THIS = a state. local_var:te_dg_nrr -> local_var:te_dg_d = NRR^(-1/29), the stable")
    o("# population's yearly factor (demographics_model.growth_factor), linear between knots.")
    o("te_demog_set_growth_factor = {")
    o("if = {")
    o(f"limit = {{ local_var:te_dg_nrr <= {NRR_KNOTS[0]} }}")
    o(f"set_local_variable = {{ name = te_dg_d value = {lit(M.growth_factor(NRR_KNOTS[0]))} }}")
    o("}")
    o("else_if = {")
    o(f"limit = {{ local_var:te_dg_nrr >= {NRR_KNOTS[-1]} }}")
    o(f"set_local_variable = {{ name = te_dg_d value = {lit(M.growth_factor(NRR_KNOTS[-1]))} }}")
    o("}")
    o("else = {")
    o("set_local_variable = {")
    o("name = te_dg_knot")
    o(f"value = {{ value = local_var:te_dg_nrr subtract = {NRR_KNOTS[0]} multiply = 10 floor = yes }}")
    o("}")

    def leaf(o, i):
        x0, x1 = NRR_KNOTS[i], NRR_KNOTS[i + 1]
        d0, d1 = M.growth_factor(x0), M.growth_factor(x1)
        o("set_local_variable = {")
        o("name = te_dg_d")
        o(f"value = {{ value = local_var:te_dg_nrr subtract = {x0} multiply = {lit((d1 - d0) / (x1 - x0))} "
          f"add = {lit(d0)} }}")
        o("}")
    tree(o, "te_dg_knot", 0, len(NRR_KNOTS) - 2, leaf)
    o("}")
    o("}")
    o("")


def country_bands(o):
    o("# THIS = a state, ROOT = its owner on the yearly country pulse: add the state's bands.")
    o("te_demog_add_bands_to_root = {")
    for b in range(P.BANDS):
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_t value = var:te_dg_b{s}{b} }}")
            o(f"root = {{ change_variable = {{ name = te_dg_cb{s}{b} add = local_var:te_dg_t }} }}")
    o("}")
    o("")
    o("# THIS = a country: zero its band sums before the states add theirs.")
    o("te_demog_reset_country_bands = {")
    for b in range(P.BANDS):
        o(f"set_variable = {{ name = te_dg_cbf{b} value = 0 }}")
        o(f"set_variable = {{ name = te_dg_cbm{b} value = 0 }}")
    o("}")
    o("")
    o("# THIS = a state: multiply the bands and class sums by local_var:te_dg_new_scale.")
    o("te_demog_scale_bands = {")
    for b in range(P.BANDS):
        for s in ("f", "m"):
            o(f"change_variable = {{ name = te_dg_b{s}{b} multiply = local_var:te_dg_new_scale }}")
    for c in range(len(P.MIGRANT_CLASSES)):
        for s in ("f", "m"):
            o(f"change_variable = {{ name = te_dg_c{s}{c} multiply = local_var:te_dg_new_scale }}")
    o("}")
    o("")


def debug_ring(o):
    for when in ("before", "after"):
        o(f"# THIS = a state: the ring as TE_DEMOG_REPLAY {when} lines (demographics_harness.format_replay).")
        o(f"te_demog_debug_log_ring_{when} = {{")
        for first in range(0, N, 10):
            f = ",".join(f"[THIS.ScriptValue('te_demog_dbg_f{k}')|5]" for k in range(first, first + 10))
            m = ",".join(f"[THIS.ScriptValue('te_demog_dbg_m{k}')|5]" for k in range(first, first + 10))
            extra = ""
            if first == 0:
                extra = (" pool_f=[THIS.ScriptValue('te_demog_dbg_pool_f')|5]"
                         " pool_m=[THIS.ScriptValue('te_demog_dbg_pool_m')|5]"
                         " pool_age=[THIS.Var('te_dg_pa').GetValue|5]")
            o(f'debug_log = "TE_DEMOG_REPLAY {when} from={first} f={f} m={m}{extra}"')
        o("}")
        o("")


def profile(o):
    o("# THIS = a state. The migrant profile (demographics_model.migrant_profile): from the kinds'")
    o("# weights te_dg_labour, te_dg_family, te_dg_refugee and labour's women's share")
    o("# te_dg_labour_f, each class's share for women (te_dg_pf<c>) and men (te_dg_pm<c>).")
    o("te_demog_set_profile = {")
    for c in range(len(P.MIGRANT_CLASSES)):
        lw = P.MIGRANT_PROFILE["labour"]["weights"][c]
        fw = P.MIGRANT_PROFILE["family"]["weights"][c]
        rw = P.MIGRANT_PROFILE["refugee"]["weights"][c]
        both = (f"add = {{ value = local_var:te_dg_family multiply = {lit(fw * 0.5)} }} "
                f"add = {{ value = local_var:te_dg_refugee multiply = {lit(rw * 0.5)} }}")
        o(f"set_local_variable = {{ name = te_dg_pf{c} value = {{ value = local_var:te_dg_labour "
          f"multiply = {lit(lw)} multiply = local_var:te_dg_labour_f {both} }} }}")
        o(f"set_local_variable = {{ name = te_dg_pm{c} value = {{ value = 1 subtract = local_var:te_dg_labour_f "
          f"multiply = local_var:te_dg_labour multiply = {lit(lw)} {both} }} }}")
    o("}")
    o("")


def migrant_booking(o):
    """The migrant booking's cap (2026-10-12; docs/testing/demographics-migrant-booking-2026-10-12.md): the twin of
    demographics_model.migrant_rates."""
    o("# THIS = a state, in te_demog_flows after te_demog_set_profile (demographics_model.migrant_rates). Each")
    o("# class and sex takes the profile's share of the year's migrants (te_dg_mig_in or te_dg_mig_out) over")
    o("# its last-year sum, at most te_demog_k_migrant_cap_in or _out of it (te_dg_mr_f<c>, te_dg_mr_m<c>);")
    o("# what the cap and any class under one person leave over is spread over every class and sex with")
    o("# people at one flat rate (te_dg_mig_flat): whole families moving. The rates are unsigned;")
    o("# te_demog_enter_class gives them their direction.")
    o("te_demog_migrant_rates = {")
    o("set_local_variable = { name = te_dg_mig_amt value = { value = local_var:te_dg_mig_in add = local_var:te_dg_mig_out } }")
    o("set_local_variable = { name = te_dg_mig_cap value = te_demog_k_migrant_cap_out }")
    o("if = {")
    o("limit = { local_var:te_dg_mig_in > 0 }")
    o("set_local_variable = { name = te_dg_mig_cap value = te_demog_k_migrant_cap_in }")
    o("}")
    o("set_local_variable = { name = te_dg_mig_left value = 0 }")
    o("set_local_variable = { name = te_dg_mig_all value = 0 }")
    for c in range(len(P.MIGRANT_CLASSES)):
        for sex in "fm":
            last, prof = f"var:te_dg_c{sex}{c}", f"local_var:te_dg_p{sex}{c}"
            want = f"value = local_var:te_dg_mig_amt multiply = {prof}"
            o(f"set_local_variable = {{ name = te_dg_mr_{sex}{c} value = 0 }}")
            o("if = {")
            o(f"limit = {{ {last} >= 1 }}")
            o(f"change_local_variable = {{ name = te_dg_mig_all add = {last} }}")
            o(f"set_local_variable = {{ name = te_dg_mig_take value = {{ {want} "
              f"max = {{ value = {last} multiply = local_var:te_dg_mig_cap }} }} }}")
            o(f"change_local_variable = {{ name = te_dg_mig_left add = {{ {want} "
              "subtract = local_var:te_dg_mig_take } }")
            o(f"set_local_variable = {{ name = te_dg_mr_{sex}{c} value = {{ value = local_var:te_dg_mig_take "
              f"divide = {{ value = {last} min = 1 }} }} }}")
            o("}")
            o("else = {")
            o(f"change_local_variable = {{ name = te_dg_mig_left add = {{ {want} }} }}")
            o("}")
    o("set_local_variable = { name = te_dg_mig_flat value = 0 }")
    o("if = {")
    o("limit = { local_var:te_dg_mig_all >= 1 }")
    o("set_local_variable = { name = te_dg_mig_flat value = { value = local_var:te_dg_mig_left "
      "divide = { value = local_var:te_dg_mig_all min = 1 } } }")
    o("}")
    o("}")
    o("")


def band_figures(o):
    young = range(0, 3)
    working = range(3, 13)
    o("# THIS = a state or a country; $B$ = the band variables' prefix (te_dg_b or te_dg_cb).")
    o("# Sets locals te_dg_total, te_dg_young, te_dg_working, te_dg_old (0-14, 15-64, 65+),")
    o("# te_dg_w1549 (women 15-49), te_dg_w2059 and te_dg_m2059 (20-59), then te_dg_median.")
    o("te_demog_band_figures = {")
    for name in ("total", "young", "working", "old", "w1549", "w2059", "m2059"):
        o(f"set_local_variable = {{ name = te_dg_{name} value = 0 }}")
    for b in range(P.BANDS):
        o(f"set_local_variable = {{ name = te_dg_t value = {{ value = var:$B$f{b} add = var:$B$m{b} }} }}")
        o("change_local_variable = { name = te_dg_total add = local_var:te_dg_t }")
        group = "young" if b in young else "working" if b in working else "old"
        o(f"change_local_variable = {{ name = te_dg_{group} add = local_var:te_dg_t }}")
        if 3 <= b <= 9:
            o(f"change_local_variable = {{ name = te_dg_w1549 add = var:$B$f{b} }}")
        if 4 <= b <= 11:
            o(f"change_local_variable = {{ name = te_dg_w2059 add = var:$B$f{b} }}")
            o(f"change_local_variable = {{ name = te_dg_m2059 add = var:$B$m{b} }}")
    o("# the median: the band where the running sum passes half, interpolated inside it")
    o("set_local_variable = { name = te_dg_half value = { value = local_var:te_dg_total multiply = 0.5 } }")
    o("set_local_variable = { name = te_dg_run value = 0 }")
    o("set_local_variable = { name = te_dg_median value = -1 }")
    for b in range(P.BANDS):
        width = P.BAND_WIDTH if b < P.BANDS - 1 else 15
        o("if = {")
        o("limit = { local_var:te_dg_median < 0 }")
        o(f"set_local_variable = {{ name = te_dg_t value = {{ value = var:$B$f{b} add = var:$B$m{b} }} }}")
        o("set_local_variable = { name = te_dg_run2 value = { value = local_var:te_dg_run add = local_var:te_dg_t } }")
        o("if = {")
        o("limit = { local_var:te_dg_run2 >= local_var:te_dg_half }")
        o(f"set_local_variable = {{ name = te_dg_median value = {{ value = local_var:te_dg_half "
          f"subtract = local_var:te_dg_run divide = {{ value = local_var:te_dg_t min = 0.00001 }} "
          f"multiply = {width} add = {b * P.BAND_WIDTH} }} }}")
        o("}")
        o("change_local_variable = { name = te_dg_run add = local_var:te_dg_t }")
        o("}")
    o("}")
    o("")


def projection(o):
    """Twenty years ahead in four five-year steps on the bands (spec 10's outline)."""
    o("# THIS = a country (the player's). From the country's band sums te_dg_cb* and its average")
    o("# rates (te_dg_m_* locals, local_var:te_dg_tfr): te_dg_pjf<b> / te_dg_pjm<b>, the bands")
    o("# twenty years ahead. Five-year survival per band from its age group; births from women")
    o("# 15-49 at their group's fertility. A display outline, not the model's step.")
    o("te_demog_project = {")
    for b in range(P.BANDS):
        start = b * P.BAND_WIDTH
        g = P.group_of(start) if b > 0 else 1
        o(f"set_local_variable = {{ name = te_dg_g value = {g} }}")
        o("te_demog_enter_group = yes")
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_s{s}{b} value = {{ value = 1 subtract = "
              f"{{ value = local_var:te_dg_q{s} divide = 100000 }} }} }}")
            o(f"set_local_variable = {{ name = te_dg_t value = local_var:te_dg_s{s}{b} }}")
            o(f"while = {{ count = 4 change_local_variable = {{ name = te_dg_s{s}{b} multiply = local_var:te_dg_t }} }}")
        o(f"set_local_variable = {{ name = te_dg_fert{b} value = {{ value = local_var:te_dg_asfr multiply = 5 "
          f"divide = 100000 multiply = local_var:te_dg_tfr }} }}")
        o(f"set_local_variable = {{ name = te_dg_xf{b} value = var:te_dg_cbf{b} }}")
        o(f"set_local_variable = {{ name = te_dg_xm{b} value = var:te_dg_cbm{b} }}")
    last = P.BANDS - 1
    for _step in range(4):
        o("set_local_variable = { name = te_dg_births value = 0 }")
        for b in range(P.BANDS):
            o(f"change_local_variable = {{ name = te_dg_births add = {{ value = local_var:te_dg_xf{b} "
              f"multiply = local_var:te_dg_fert{b} }} }}")
        for s in ("f", "m"):
            o(f"set_local_variable = {{ name = te_dg_x{s}{last} value = {{ value = local_var:te_dg_x{s}{last} "
              f"multiply = local_var:te_dg_s{s}{last} add = {{ value = local_var:te_dg_x{s}{last - 1} "
              f"multiply = local_var:te_dg_s{s}{last - 1} }} }} }}")
            for b in range(last - 1, 0, -1):
                o(f"set_local_variable = {{ name = te_dg_x{s}{b} value = {{ value = local_var:te_dg_x{s}{b - 1} "
                  f"multiply = local_var:te_dg_s{s}{b - 1} }} }}")
        o(f"set_local_variable = {{ name = te_dg_xf0 value = {{ value = local_var:te_dg_births "
          f"multiply = {lit(P.FEMALE_BIRTH_PER_100K / 100000)} multiply = local_var:te_dg_sf0 }} }}")
        o(f"set_local_variable = {{ name = te_dg_xm0 value = {{ value = local_var:te_dg_births "
          f"multiply = {lit(P.MALE_BIRTH_PER_100K / 100000)} multiply = local_var:te_dg_sm0 }} }}")
    for b in range(P.BANDS):
        o(f"set_variable = {{ name = te_dg_pjf{b} value = local_var:te_dg_xf{b} }}")
        o(f"set_variable = {{ name = te_dg_pjm{b} value = local_var:te_dg_xm{b} }}")
    o("}")
    o("")


FIXED_MAX = (2 ** 63 - 1) / 1e5   # the largest value script holds: an i64 in units of 1e-5


def gini_income_pieces(root):
    """[(x0, x1, y0, slope)] per band, in plain spending per head: band k holds wealth x0 < w <= x1 and
    its pops' income is y0 + slope (w - x0); the first band (x0 None) is flat at y0. Checks the top
    level against the defines and that the largest country fits the fixed point (spec 4.1)."""
    costs = buy_package_costs(root)
    levels = re.search(r"^\s*NUM_WEALTH_LEVELS\s*=\s*(\d+)", (root / DEFINES).read_text(encoding="utf-8-sig"), re.M)
    assert levels and int(levels.group(1)) == P.GINI_TOP_WEALTH, "GINI_TOP_WEALTH is the mod's NUM_WEALTH_LEVELS"
    assert max(costs) == P.GINI_TOP_WEALTH, "a buy package for every wealth level"
    top = costs[P.GINI_TOP_WEALTH] / 100
    worst = P.GINI_MAX_PEOPLE / P.GINI_INCOME_UNIT * top
    assert worst < FIXED_MAX / 2, f"{P.GINI_MAX_PEOPLE:g} people at the top level sum to {worst:.3g} units"
    knots = P.GINI_INCOME_KNOTS
    pieces = [(None, knots[0], costs[knots[0]] / 100, 0.0)]
    for x0, x1 in zip(knots, knots[1:]):
        y0, y1 = costs[x0] / 100, costs[x1] / 100
        pieces.append((x0, x1, y0, (y1 - y0) / (x1 - x0)))
    assert len(pieces) == P.GINI_BANDS
    return pieces


def gini_bands(o, pieces):
    """§4.1's Gini over wealth bands: the walk's sums, a state's store, the country's sum, the formula."""
    knots, n = P.GINI_BAND_KNOTS, P.GINI_BANDS
    unit = P.GINI_INCOME_UNIT
    o("# THIS = a state, before its pop walk: the Gini's wealth-band sums (spec 4.1).")
    o("te_demog_gini_band_init = {")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_w_gn{k} value = 0 }}")
        o(f"set_local_variable = {{ name = te_dg_w_gy{k} value = 0 }}")
    o("}")
    o("")

    def leaf(k):
        x0, _x1, y0, slope = pieces[k - 1]
        o(f"change_local_variable = {{ name = te_dg_w_gn{k} add = total_size }}")
        if x0 is None:
            per_head = lit(y0)
        else:
            top = f" max = {P.GINI_TOP_WEALTH}" if k == n else ""
            per_head = f"{{ value = wealth{top} subtract = {x0} multiply = {lit(slope)} add = {lit(y0)} }}"
        o(f"change_local_variable = {{ name = te_dg_w_gy{k} add = {{ value = total_size divide = {unit} "
          f"multiply = {per_head} }} }}")

    def chain(lo, hi):
        if lo == hi:
            leaf(lo)
            return
        mid = (lo + hi) // 2      # bands lo..mid hold wealth up to knots[mid - 1]
        o("if = {")
        o(f"limit = {{ wealth > {knots[mid - 1]} }}")
        chain(mid + 1, hi)
        o("}")
        o("else = {")
        chain(lo, mid)
        o("}")

    o("# THIS = a pop in the walk: its people and its income into its wealth band. The knots are each")
    o(f"# band's top (1, then every fifth level to {knots[-1]}; the last band runs to the top level, "
      f"{P.GINI_TOP_WEALTH}),")
    o("# split in halves, so a pop takes five or six tests. The leaf computes the income: spending per")
    o("# head (buy package / 100), linear across the band, uncapped. It is summed in units of "
      f"{unit:,}:")
    o("# the people divide first (exact), so the largest country at the top level fits the fixed point")
    o("# (i64 x 1e-5); the smallest step is 1 of spending per pop.")
    o("te_demog_gini_band_add = {")
    chain(1, n)
    o("}")
    o("")
    o("# THIS = a state, after its walk: keep the bands that have people, for the country's sum, and")
    o(f"# remove the rest (save size), with the layout they follow (te_dg_gini_layout = {P.GINI_LAYOUT}, the")
    o("# country adds no other). Overwrites or removes every band an older layout stored, and an old")
    o("# save's strata sums (before the wealth bands, 2026-10-10).")
    o("te_demog_gini_band_store = {")
    o(f"set_variable = {{ name = te_dg_gini_layout value = {P.GINI_LAYOUT} }}")
    for k in range(1, n + 1):
        o("if = {")
        o(f"limit = {{ local_var:te_dg_w_gn{k} > 0 }}")
        o(f"set_variable = {{ name = te_dg_gn{k} value = local_var:te_dg_w_gn{k} }}")
        o(f"set_variable = {{ name = te_dg_gy{k} value = local_var:te_dg_w_gy{k} }}")
        o("}")
        o("else_if = {")
        o(f"limit = {{ has_variable = te_dg_gn{k} }}")
        o(f"remove_variable = te_dg_gn{k}")
        o(f"remove_variable = te_dg_gy{k}")
        o("}")
    o("if = {")
    o("limit = { has_variable = te_dg_n_lo }")
    for name in ("n_lo", "n_mi", "n_up", "y_lo", "y_mi", "y_up"):
        o(f"remove_variable = te_dg_{name}")
    o("}")
    o("}")
    o("")
    o("# THIS = a state, after its store: its bands into the formula's locals (0 where none is stored).")
    o("te_demog_gini_band_load = {")
    o("te_demog_gini_band_zero = yes")
    for k in range(1, n + 1):
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_gn{k} }}")
        o(f"set_local_variable = {{ name = te_dg_g_n{k} value = var:te_dg_gn{k} }}")
        o(f"set_local_variable = {{ name = te_dg_g_y{k} value = var:te_dg_gy{k} }}")
        o("}")
    o("}")
    o("")
    o("# THIS = a country before its states add their bands, or a state before it loads its own.")
    o("te_demog_gini_band_zero = {")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_g_n{k} value = 0 }}")
        o(f"set_local_variable = {{ name = te_dg_g_y{k} value = 0 }}")
    o("}")
    o("")
    o("# THIS = a state in its country's loop: add its bands if they follow this layout, and count it in")
    o("# local_var:te_dg_g_states (the caller sets it to 0). A state from an older save (14 bands to 61+,")
    o("# capped income in other units, or strata sums) adds nothing until its own walk stores new ones.")
    o("te_demog_gini_band_add_state = {")
    o("if = {")
    o("limit = { has_variable = te_dg_gini_layout }")
    o("if = {")
    o(f"limit = {{ var:te_dg_gini_layout = {P.GINI_LAYOUT} }}")
    o("change_local_variable = { name = te_dg_g_states add = 1 }")
    for k in range(1, n + 1):
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_gn{k} }}")
        o(f"change_local_variable = {{ name = te_dg_g_n{k} add = var:te_dg_gn{k} }}")
        o(f"change_local_variable = {{ name = te_dg_g_y{k} add = var:te_dg_gy{k} }}")
        o("}")
    o("}")
    o("}")
    o("}")
    o("")
    o("# THIS = a state or a country, with its bands in te_dg_g_n<k> and te_dg_g_y<k> (a country's summed")
    o("# over its states, so its Gini is taken over all their people, not averaged). The bands are in")
    o("# income order, so G = 1 - sum p_k (S_k + S_k-1), with p_k a band's share of people and S_k the")
    o("# running share of income. Values are i64 x 1e-5: each S_k is the income so far over the total, cut")
    o("# once, and the people multiply it before the one division by all people, so no share of a few")
    o("# people is cut to 0. Empty bands are skipped. With no people or no income the computed Gini is 0.")
    o(f"# Writes var:te_dg_gini, the panel's figure: 1 - {lit(P.GINI_SHOWN_EQUALITY)} x (1 - G), the equality the "
      "bands show")
    o("# scaled down for the spread inside them (spec 4.1; owner, 2026-10-10), so it reads like historians'")
    o("# estimates.")
    o("te_demog_gini_from_locals = {")
    o("set_local_variable = { name = te_dg_g_pop value = 0 }")
    o("set_local_variable = { name = te_dg_g_inc value = 0 }")
    for k in range(1, n + 1):
        o(f"change_local_variable = {{ name = te_dg_g_pop add = local_var:te_dg_g_n{k} }}")
        o(f"change_local_variable = {{ name = te_dg_g_inc add = local_var:te_dg_g_y{k} }}")
    o("set_local_variable = { name = te_dg_g_gini value = 0 }")
    o("if = {")
    o("limit = {")
    o("local_var:te_dg_g_pop > 0")
    o("local_var:te_dg_g_inc > 0")
    o("}")
    o("set_local_variable = { name = te_dg_g_c value = 0 }")
    o("set_local_variable = { name = te_dg_g_s value = 0 }")
    o("set_local_variable = { name = te_dg_g_a value = 0 }")
    for k in range(1, n + 1):
        o("if = {")
        o(f"limit = {{ local_var:te_dg_g_n{k} > 0 }}")
        o(f"change_local_variable = {{ name = te_dg_g_c add = local_var:te_dg_g_y{k} }}")
        o("set_local_variable = { name = te_dg_g_s2 value = { value = local_var:te_dg_g_c "
          "divide = { value = local_var:te_dg_g_inc min = 0.00001 } } }")
        o("change_local_variable = { name = te_dg_g_a add = { value = local_var:te_dg_g_s2 "
          f"add = local_var:te_dg_g_s multiply = local_var:te_dg_g_n{k} }} }}")
        o("set_local_variable = { name = te_dg_g_s value = local_var:te_dg_g_s2 }")
        o("}")
    o("set_local_variable = { name = te_dg_g_gini value = { value = 1 subtract = { value = local_var:te_dg_g_a "
      "divide = { value = local_var:te_dg_g_pop min = 1 } } } }")
    o("}")
    o(f"set_variable = {{ name = te_dg_gini value = {{ value = local_var:te_dg_g_gini "
      f"multiply = {lit(P.GINI_SHOWN_EQUALITY)} add = {lit(1 - P.GINI_SHOWN_EQUALITY)} min = 0 max = 1 }} }}")
    o("}")
    o("")


def medicine_effects(o):
    o("# THIS = a state, in te_demog_prepare before its multipliers (a seed or a step): the census's inputs, so")
    o("# te_demog_f_* (and the state subtab's Causes of Death) read what the step used until the next one. The walk's")
    o("# SoL and literacy too: a walk without a step (a second pulse in a year, the console) rewrites te_dg_sol and")
    o("# te_dg_lit, never te_dg_m_*.")
    o("te_demog_cause_inputs_store = {")
    o("set_variable = { name = te_dg_in_sol value = var:te_dg_sol }")
    o("set_variable = { name = te_dg_in_lit value = var:te_dg_lit }")
    for cause, types in P.MORTALITY_TYPES.items():
        adds = " ".join(f"add = modifier:{t}" for t in types)
        o(f"set_variable = {{ name = te_dg_in_{P.CAUSE_SHORT[cause]} value = {{ value = 0 {adds} }} }}")
    import gen_demographics_um as UM     # uploaded minds' call 2: Mind Backups' restore x longevity care
    UM.backup_inputs(o)
    o("# turmoil as the 0-1 share te_demog_crisis reads")
    o("set_variable = { name = te_dg_in_turm value = { value = turmoil min = 0 max = 1 } }")
    o("# crowding: the migration penalty the crowding refresh applied (te_update_migration_crowding_modifier)")
    o("set_variable = { name = te_dg_in_crowd value = 0 }")
    o("if = {")
    o("limit = {")
    o("has_modifier = migration_crowding")
    o("has_variable = migration_crowding_mult_applied")
    o("}")
    o("set_variable = { name = te_dg_in_crowd value = { value = var:migration_crowding_mult_applied "
      f"multiply = {lit(P.MIGRATION_CROWDING_PULL_PER_MULT)} }} }}")
    o("}")
    o("# calibration step 3: the state's malaria trait (te_demog_malaria_level) and its control, 0 to 1")
    o("set_variable = { name = te_dg_in_mal value = te_demog_malaria_level }")
    o(f"set_variable = {{ name = te_dg_in_malc value = {{ value = modifier:{P.MALARIA_CONTROL_TYPE} min = 0 max = 1 }} }}")
    o("# modern safety (2026-10-16): the share of each cause's deaths the era 7-9 technologies prevent")
    for cause, t in P.SAFETY_TYPES.items():
        o(f"set_variable = {{ name = te_dg_in_saf_{P.CAUSE_SHORT[cause]} value = {{ value = modifier:{t} min = 0 "
          f"max = {lit(P.SAFETY_MAX)} }} }}")
    o("}")
    o("")
    pairs = [("te_dg_acc", "te_demog_access_target")]
    pairs += [(f"te_dg_trt_{P.CAUSE_SHORT[c]}", f"te_demog_treatment_target_{c}") for c in P.MEDICINE_CAUSES]
    o("# THIS = a state: the drifted medicine at its targets (te_demog_seed; te_demog_medicine_drift for a state")
    o("# without it: a census from before the Causes of Death plan).")
    o("te_demog_medicine_at_target = {")
    for var, target in pairs:
        o(f"set_variable = {{ name = {var} value = {target} }}")
    o("}")
    o("")
    o("# THIS = a state at the start of its step (te_demog_step_begin): health-care access and each cause's treatment")
    o("# move te_demog_medical_diffusion of the way to today's targets (demographics_model.medicine_drift).")
    o("te_demog_medicine_drift = {")
    o("if = {")
    o("limit = {")
    for var, _target in pairs:
        o(f"has_variable = {var}")
    o("}")
    o("set_local_variable = { name = te_dg_diff value = te_demog_medical_diffusion }")
    for var, target in pairs:
        o(f"te_demog_medicine_drift_one = {{ VAR = {var} TARGET = {target} }}")
    o("}")
    o("else = {")
    o("te_demog_medicine_at_target = yes")
    o("}")
    o("}")
    o("")
    o("# One drifted value: (target - value) x the step's share + value; within te_demog_k_medicine_snap of the target,")
    o("# the target. set_variable's inline block, not change_variable (scripting_best_practices.md).")
    o("te_demog_medicine_drift_one = {")
    o("set_variable = {")
    o("name = $VAR$")
    o("value = {")
    o("value = $TARGET$")
    o("subtract = var:$VAR$")
    o("multiply = local_var:te_dg_diff")
    o("add = var:$VAR$")
    o("}")
    o("}")
    o("# te_dg_med_gap, not te_dg_gap: te_demog_state_census, which calls the step, keeps its own te_dg_gap local")
    o("set_local_variable = { name = te_dg_med_gap value = { value = $TARGET$ subtract = var:$VAR$ } }")
    o("if = {")
    o("limit = {")
    o("local_var:te_dg_med_gap < te_demog_k_medicine_snap")
    o("local_var:te_dg_med_gap > te_demog_k_medicine_snap_neg")
    o("}")
    o("set_variable = { name = $VAR$ value = $TARGET$ }")
    o("}")
    o("}")
    o("")


def render_effects(root=ROOT):
    o = Out()
    o(HEADER.rstrip("\n"))
    o("")
    sweeps(o)
    enter_group(o)
    bands_and_classes(o)
    normalizers(o)
    life_table(o)
    old_age_pass(o)
    work_bands(o)
    slot_births(o)
    growth_factor(o)
    country_bands(o)
    gini_bands(o, gini_income_pieces(root))
    profile(o)
    migrant_booking(o)
    band_figures(o)
    projection(o)
    absorbed_walk(o, root)
    medicine_effects(o)
    practice_loops(o)
    family_policy_effects(o)
    cause_deaths_estimate(o)
    debug_ring(o)
    return o.text()


# ---- values -------------------------------------------------------------------------

def _piecewise_sol(o, name, comment, points, scale=1.0):
    """A per-pop value: total_size x a piecewise-linear function of standard_of_living."""
    o(f"# {comment}")
    o(f"{name} = {{")
    o("value = total_size")
    o("multiply = {")
    o(f"value = {lit(points[0][1] * scale)}")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        slope = (y1 - y0) / (x1 - x0) * scale
        o("if = {")
        o(f"limit = {{ standard_of_living > {lit(x0)} }}")
        o(f"value = {{ value = standard_of_living subtract = {lit(x0)} multiply = {lit(slope)} "
          f"add = {lit(y0 * scale)} }}")
        o("}")
    o("if = {")
    o(f"limit = {{ standard_of_living >= {lit(points[-1][0])} }}")
    o(f"value = {lit(points[-1][1] * scale)}")
    o("}")
    o("}")
    o("}")
    o("")


def engine_curves(o, d):
    b = [(0, G.monthly_birthrate(0, d)), (d.transition_sol, G.monthly_birthrate(d.transition_sol, d)),
         (d.stable_sol, G.monthly_birthrate(d.stable_sol, d))]
    m = [(0, G.monthly_mortality(0, d)), (d.equilibrium_sol, G.monthly_mortality(d.equilibrium_sol, d)),
         (d.max_sol, G.monthly_mortality(d.max_sol, d)), (d.stable_sol, G.monthly_mortality(d.stable_sol, d))]
    _piecewise_sol(o, "te_demog_pop_engine_births",
                   "Pop scope: the engine's births a month x 100,000 at this pop's SoL (extra_defines.txt), x size.",
                   b, 100000)
    _piecewise_sol(o, "te_demog_pop_engine_deaths",
                   "Pop scope: the engine's deaths a month x 100,000 at this pop's SoL, x size.", m, 100000)
    _piecewise_sol(o, "te_demog_pop_wealth_tfr",
                   "Pop scope: children per woman from wealth alone at this pop's SoL (spec 2.3), x size.",
                   [(0, P.WEALTH_TFR_LOW), (P.WEALTH_TFR_LOW_SOL, P.WEALTH_TFR_LOW),
                    (P.WEALTH_TFR_HIGH_SOL, P.WEALTH_TFR_HIGH)])


# ---- the engine's own birth and death multipliers, per pop ----------------------------
# The migration residual is a state's population change less the engine's births and deaths,
# so the census must expect what the engine does. The growth probe (branch
# probe/demographics-growth; docs/testing/demographics-growth-probe-results-2026-10-09.md)
# found the engine builds each pop's multiplier from one total, floored at 0 per pop, and that
# a state's modifier:state_*_mult read holds only the state-wide part:
#   births: + literacy_penalty x the pop's literacy, + the starvation penalties
#   deaths: + its class's state_<type>_mortality_mult, its workplace's building_<type>_ and
#           building_group_<group>[_<type>]_mortality_mult (which carry working_conditions, scaled by the
#           building's building_working_conditions_mult: self-check working_conditions_read, 2026-10-17),
#           the starvation penalties, and non-homeland mortality.
# Both starvation penalties apply x the pop's starvation value, clamp((0.4 - food security) x 2.5, 0, 1): mild's
# up to 0.5, severe's 0.5 to 1 (the famine probe, 2026-10-11; the walk took severe flat until then, and its famine
# deaths ran 1.5-1.7x the engine's). The walk reads both in 0.05 steps of food security.
# Only registered modifier types are read: modifiers.log lists ~1,100 mortality keys, but an
# unregistered one cannot be set by anything and reads as 'none' on every pop. A registered one
# that nothing sets reads 0 (the first launch: no 'Value of wrong type' at the game-start walk).

def _field(body, key):
    v = body.get(key) if isinstance(body, dict) else None
    v = v[-1] if isinstance(v, (list, tuple)) else v
    return v[-1] if isinstance(v, (list, tuple)) else v


def _snapshot(root, name):
    import json
    data = json.loads((root / "vanilla_parsed" / "common" / f"{name}.json").read_text(encoding="utf-8"))
    data = data.get("data", data)
    return {k: (v[1] if isinstance(v, list) and len(v) == 2 and v[0] == "=" else v) for k, v in data.items()}


def _mod_entries(root, sub):
    """{name: (directive, body)} for the mod's common/<sub>/ files; directive is '', 'REPLACE' or 'INJECT'."""
    from paradox_file_parser import ParadoxFileParser
    out = {}
    for path in sorted((root / "common" / sub).glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for name, body in parser.data.items():
            directive, _, key = name.rpartition(":")
            out[key] = (directive, body[1] if isinstance(body, tuple) else body)
    return out


def registered_modifier_types(root):
    return set(_snapshot(root, "modifier_types")) | set(_mod_entries(root, "modifier_type_definitions"))


def static_modifier(root, name):
    """{key: value} of a static modifier's *_mult fields, vanilla's with the mod's REPLACE or INJECT (a plain
    redefinition of a vanilla name is a dropped duplicate)."""
    vanilla = _snapshot(root, "modifiers")
    body = dict(vanilla.get(name, {}))
    directive, mod_body = _mod_entries(root, "static_modifiers").get(name, ("", None))
    if mod_body is not None and (directive == "REPLACE" or (not directive and name not in vanilla)):
        body = dict(mod_body)
    elif mod_body is not None and directive == "INJECT":
        body.update(mod_body)
    return {k: float(_field(body, k)) for k in body if k.endswith("_mult")}


def building_group_parents(root):
    parents = {g: _field(b, "parent_group") for g, b in _snapshot(root, "building_groups").items()}
    for key, (directive, body) in _mod_entries(root, "building_groups").items():
        if directive == "INJECT":
            if _field(body, "parent_group"):
                parents[key] = _field(body, "parent_group")
        elif directive == "REPLACE" or key not in parents:
            parents[key] = _field(body, "parent_group")
    return parents


def _group_gate(group, parents):
    """A building-scope trigger: the building is in the group or any of its descendants."""
    groups, frontier = [group], [group]
    while frontier:
        current = frontier.pop()
        kids = sorted(k for k, p in parents.items() if p == current)
        groups += kids
        frontier += kids
    if len(groups) == 1:
        return f"is_building_group = {group}"
    return "OR = { " + " ".join(f"is_building_group = {g}" for g in groups) + " }"


def _starvation_buckets(severe=False):
    """[(lower food security, scale)], top step first, in STARVATION_BUCKET steps of food security: mild starvation's
    from the starvation threshold down to the severe one, or severe starvation's from there down to 0. The scale is
    the engine's starvation value at each step's middle (demographics_model.starvation_value, always measured from the
    starvation threshold), which both penalties take (the famine probe, 2026-10-11): mild's at most
    STARVATION_MILD_CAP, severe's 0.5 to 1."""
    hi = P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD if severe else P.FOOD_SECURITY_STARVATION_THRESHOLD
    lo = 0.0 if severe else P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD
    cap = P.STARVATION_VALUE_MAX if severe else P.STARVATION_MILD_CAP
    out, top = [], hi
    while top - P.STARVATION_BUCKET >= lo - 1e-9:
        lower = round(top - P.STARVATION_BUCKET, 5)
        out.append((lower, min(M.starvation_value((top + lower) / 2), cap)))
        top = lower
    return out


def _starvation_ladder(o, coefficient, buckets):
    """The food-security steps as an if / else_if chain, the last step an else: coefficient x each step's scale."""
    for i, (lower, scale) in enumerate(buckets):
        if i == len(buckets) - 1:
            o(f"else = {{ add = {lit(coefficient * scale)} }}")
        else:
            o(f"{'if' if i == 0 else 'else_if'} = {{ limit = {{ food_security >= {lit(lower)} }} add = {lit(coefficient * scale)} }}")


def _starvation(o, key, mild, severe):
    """Pop scope: both starvation terms, each penalty x the starvation value read in food-security steps."""
    o("if = {")
    o("limit = { is_in_severe_starvation = yes }")
    _starvation_ladder(o, severe[key], _starvation_buckets(severe=True))
    o("}")
    o("else_if = {")
    o("limit = { is_in_mild_starvation = yes }")
    _starvation_ladder(o, mild[key], _starvation_buckets())
    o("}")


def _mild_starvation(o, key, mild):
    """Pop scope: mild starvation's term, read in food-security steps (severe starvation's is left out)."""
    o("if = {")
    o("limit = {")
    o("is_in_severe_starvation = no")
    o("is_in_mild_starvation = yes")
    o("}")
    _starvation_ladder(o, mild[key], _starvation_buckets())
    o("}")


def absorbed_terms(o, root, literacy, mild):
    """What the census absorbs per pop (phase 2 step 4, owner amendment B), which te_demog_rates_refresh takes out of
    its terms M under Full through the walk's sums: literacy's term and mild starvation's. The laws', technologies'
    and institutions' birth and mortality lines are script-only since 2026-10-11 (the engine-lines plan), so the engine
    never applies them under Full and there is nothing of theirs to net."""
    country_absorbed_terms(o, root)
    o("# Pop scope: the terms the census absorbs per pop: literacy's (literacy_penalty) and mild starvation's")
    o("# (starvation_penalty). Severe starvation stays on top (owner amendment B). The laws', technologies' and")
    o("# institutions' lines are script-only (owner, 2026-10-11), so the census has none of theirs to net.")
    o("te_demog_pop_absorbed_births = {")
    o("value = literacy_rate")
    o(f"multiply = {lit(literacy)}")
    _mild_starvation(o, "state_birth_rate_mult", mild)
    o("}")
    o("te_demog_pop_absorbed_deaths = {")
    o("value = 0")
    _mild_starvation(o, "state_mortality_mult", mild)
    o("add = te_demog_pop_country_absorbed_deaths")
    o("}")
    o("")


def _country_absorbed_gates(root):
    """[(the building group's mortality key, its workplace gate)] for P.COUNTRY_ABSORBED_GROUPS: the key the walk adds
    for a pop employed in the group or a descendant (te_demog_pop_death_mult reads every registered group key for
    every pop type)."""
    reg, parents = registered_modifier_types(root), building_group_parents(root)
    out = []
    for group in P.COUNTRY_ABSORBED_GROUPS:
        key = f"building_group_{group}_mortality_mult"
        assert key in reg and group in parents, f"{key}: not a registered type the walk reads"
        out.append((key, _group_gate(group, parents)))
    return out


def country_absorbed_terms(o, root):
    """Calibration step 3, call 1 (owner, 2026-10-12; the spec's §2.1): the country-scope lines the census absorbs per
    pop under Full, the Landowners' famine reserves today. Each pop employed in a P.COUNTRY_ABSORBED_GROUPS group adds
    its owner's read of the group's mortality key (x P.COUNTRY_ABSORBED_SCALE, the self-check's fallback) to the
    walk's absorbed sum (te_demog_pop_absorbed_deaths), so M nets it: the line only moves deaths between a state's farm
    workers and the rest. The owner's read carries the interest group's power (a powerful group's traits count double),
    the size the walk reads at the workplace. A second value reads what the walk reads for the same keys at the
    workplace, which also holds the building's own lines (executives' traits): the self-check famine_reserves_absorbed
    compares the two on a subsistence farm, which no company owns."""
    gates = _country_absorbed_gates(root)
    farm_only = P.COUNTRY_ABSORBED_FROM_FARM   # the self-check's fallback: the farm's own read, subsistence farms only
    for name, reader, scaled, note in (
            ("te_demog_pop_country_absorbed_deaths", "workplace" if farm_only else "owner", True,
             ("the country-scope lines the census absorbs per pop under",
              "Full (the Landowners' famine reserves): its owner's read of each key where the walk adds that key")),
            ("te_demog_pop_country_line_walk_read", "workplace", False,
             ("what the walk reads for the same keys at the pop's",
              "workplace, which also holds the building's own lines (the self-check famine_reserves_absorbed)"))):
        o(f"# Pop scope (calibration step 3, call 1): {note[0]}")
        o(f"# {note[1]}.")
        o(f"{name} = {{")
        o("value = 0")
        o("if = {")
        o("limit = {")
        o("is_employed = yes")
        o("exists = workplace")
        o("}")
        for key, gate in gates:
            if farm_only and name == "te_demog_pop_country_absorbed_deaths":
                gate = "is_building_group = bg_subsistence_agriculture"
            o("if = {")
            o(f"limit = {{ workplace = {{ {gate} }} }}")
            o(f"add = {reader}.modifier:{key}")
            o("}")
        o("}")
        if scaled and P.COUNTRY_ABSORBED_SCALE != 1.0:
            o(f"multiply = {lit(P.COUNTRY_ABSORBED_SCALE)}")
        o("}")
    o("")


def absorbed_walk(o, root):
    """The walk's replaced sums (phase 2 step 4, owner amendment): each pop's bare curves x the terms absorbed per pop;
    and severe starvation's people and deaths for the Causes of Death section's split (Task 6)."""
    severe = static_modifier(root, "severe_starvation_penalty")
    o("# THIS = a state, before its pop walk (te_demog_walks): the replaced sums, the bare curves the census's")
    o("# term reaches and severe starvation's people and deaths start at 0; under Full only (the refresh and the")
    o("# split read them nowhere else) te_dg_w_rep turns the per-pop sums on.")
    o("te_demog_absorbed_walk_init = {")
    o("set_local_variable = { name = te_dg_w_ebr value = 0 }")
    o("set_local_variable = { name = te_dg_w_edr value = 0 }")
    o("set_local_variable = { name = te_dg_w_eb0m value = 0 }")
    o("set_local_variable = { name = te_dg_w_ed0m value = 0 }")
    o("set_local_variable = { name = te_dg_w_sev value = 0 }")
    o("set_local_variable = { name = te_dg_w_sevd value = 0 }")
    # phase 3 (late-game §4.3, call 14): the bare deaths x wealth the census's wealth slope reaches, and the richest pop
    o("set_local_variable = { name = te_dg_w_edw value = 0 }")
    o("set_local_variable = { name = te_dg_w_wtop value = 0 }")
    o("set_local_variable = { name = te_dg_w_rep value = 0 }")
    o("if = {")
    o("limit = { te_demog_effects_run = yes }")
    o("set_local_variable = { name = te_dg_w_rep value = 1 }")
    o("}")
    o("}")
    o("")
    o("# THIS = a pop in the walk, after its bare curves (te_dg_p_eb, te_dg_p_ed) and multipliers (te_dg_p_mb,")
    o("# te_dg_p_md): its bare births and deaths x what the census absorbs for it, into te_dg_w_ebr and te_dg_w_edr")
    o("# (te_demog_rates_refresh); and its bare curves into te_dg_w_eb0m / _ed0m unless the engine floors its")
    o("# multiplier at 0 (severe starvation's births, in its lower food-security steps or under a low term), which a")
    o("# change in the census's term then doesn't reach (the trapezoid's start rate); and severe starvation's people")
    o("# and deaths (te_dg_w_sev, te_dg_w_sevd: the Causes of Death section's split); the bare deaths x wealth the")
    o("# census's wealth slope reaches and the richest pop's wealth (te_dg_w_edw, te_dg_w_wtop; phase 3). Full only.")
    o("te_demog_absorbed_walk_pop = {")
    o("if = {")
    o("limit = { local_var:te_dg_w_rep > 0 }")
    o("change_local_variable = { name = te_dg_w_ebr add = { value = local_var:te_dg_p_eb multiply = te_demog_pop_absorbed_births } }")
    o("change_local_variable = { name = te_dg_w_edr add = { value = local_var:te_dg_p_ed multiply = te_demog_pop_absorbed_deaths } }")
    o("if = {")
    o("limit = { local_var:te_dg_p_mb > 0 }")
    o("change_local_variable = { name = te_dg_w_eb0m add = local_var:te_dg_p_eb }")
    o("}")
    o("if = {")
    o("limit = { local_var:te_dg_p_md > 0 }")
    o("change_local_variable = { name = te_dg_w_ed0m add = local_var:te_dg_p_ed }")
    o("change_local_variable = { name = te_dg_w_edw add = { value = local_var:te_dg_p_ed multiply = wealth } }")
    o("}")
    o("if = {")
    o("limit = { wealth > local_var:te_dg_w_wtop }")
    o("set_local_variable = { name = te_dg_w_wtop value = wealth }")
    o("}")
    o("# severe starvation's people, and its part of the pop's deaths where the engine doesn't floor them (the Causes")
    o("# of Death section's split, te_demog_on_top_split): the severe ladder te_demog_pop_death_mult holds")
    o("if = {")
    o("limit = { is_in_severe_starvation = yes }")
    o("change_local_variable = { name = te_dg_w_sev add = total_size }")
    o("if = {")
    o("limit = { local_var:te_dg_p_md > 0 }")
    o("change_local_variable = {")
    o("name = te_dg_w_sevd")
    o("add = {")
    o("value = local_var:te_dg_p_ed")
    o("multiply = {")
    o("value = 0")
    _starvation_ladder(o, severe["state_mortality_mult"], _starvation_buckets(severe=True))
    o("}")
    o("}")
    o("}")
    o("}")
    o("}")
    o("}")
    o("}")
    o("")


def engine_rate_terms(o, root):
    reg = registered_modifier_types(root)
    literacy = static_modifier(root, "literacy_penalty")["state_birth_rate_mult"]
    assert literacy == P.LITERACY_BIRTH_PENALTY, "literacy_penalty changed: update LITERACY_BIRTH_PENALTY"
    mild, severe = static_modifier(root, "starvation_penalty"), static_modifier(root, "severe_starvation_penalty")
    absorbed_terms(o, root, literacy, mild)
    conditions = static_modifier(root, "working_conditions")
    parents = building_group_parents(root)
    types = sorted(_snapshot(root, "pop_types"))
    pairs = set()   # (group, pop type or None) for every registered building-group mortality key the walk reads
    for key in sorted(reg):
        m = re.fullmatch(r"building_group_(\w+?)_mortality_mult", key)
        if not m:
            continue
        group, ptype = m.group(1), None
        for t in types:
            if group.endswith("_" + t):
                group, ptype = group[: -len(t) - 1], t
        if group in parents:
            pairs.add((group, ptype))
    # working_conditions reaches the pops through these reads: the engine applies the code static modifier to each
    # building at x (1 + building_working_conditions_mult), Workplace Safety's -0.2 a level taking it to 0 at five
    # (Wallonia's mine read the table's 0.1 in 1836; the growth probe's 1949 capital read 0 under Workplace Safety
    # at five). The walk took the table as constants on top until 2026-10-17, counting it twice.
    unread = sorted(k for k in conditions if k not in reg)
    assert not unread, f"working_conditions rows the walk can't read: {unread}"

    o("# Pop scope: the engine's birth multiplier for this pop: 1 + its state's state_birth_rate_mult")
    o(f"# + {lit(literacy)} x its literacy (literacy_penalty) + the starvation penalties (each x the pop's")
    o("# starvation value, in 0.05 steps of food security), floored at 0.")
    o("# x te_demog_pop_engine_births is its expected births (the growth probe: -0.101 fitted, 1949).")
    o("te_demog_pop_birth_mult = {")
    o("value = 1")
    o("add = state.modifier:state_birth_rate_mult")
    o(f"add = {{ value = literacy_rate multiply = {lit(literacy)} }}")
    _starvation(o, "state_birth_rate_mult", mild, severe)
    o("min = 0")
    o("}")
    o("")
    o("# Pop scope: the engine's mortality multiplier for this pop: 1 + its state's state_mortality_mult")
    o("# + its class's, its workplace's and its workplace's groups' mortality modifiers (the group reads carry")
    o("# working_conditions at the building's scale, so the table is not added again: working_conditions_read)")
    o("# + the starvation penalties (as births') + non-homeland mortality + the state's wealth line x the pop's wealth,")
    o("# floored at 0. The wealth line is state_mortality_wealth_mult, which the engine scales by each pop's own wealth")
    o("# (probe P6, owner, 2026-10-11): Private Health Insurance's outside Full; under Full the census's pair, which")
    o("# carries that line at its rate and the late game's wealth slope (2026-10-20: until then the walk left it out, and")
    o("# the window's deaths, dz and the residual ran high wherever the slope was on). Turmoil's mortality is left out: its")
    o("# scaling is unknown and the probe measured it at about 0.")
    o("te_demog_pop_death_mult = {")
    o("value = 1")
    o("add = state.modifier:state_mortality_mult")
    first = True
    for t in types:
        groups = sorted({g for (g, pt) in pairs if pt in (None, t)})
        own = [f"add = state.modifier:state_{t}_mortality_mult"] if f"state_{t}_mortality_mult" in reg else []
        work = [f"add = workplace.modifier:building_{t}_mortality_mult"] if f"building_{t}_mortality_mult" in reg else []
        gated = []
        for g in groups:
            adds = []
            for pt in (None, t):
                if (g, pt) in pairs:
                    adds.append(f"add = workplace.modifier:building_group_{g}{'_' + pt if pt else ''}_mortality_mult")
            if adds:
                gated.append((g, adds))
        if not (own or work or gated):
            continue
        o(f"{'if' if first else 'else_if'} = {{")
        first = False
        o(f"limit = {{ is_pop_type = {t} }}")
        for line in own:
            o(line)
        if work or gated:
            o("if = {")
            o("limit = {")
            o("is_employed = yes")
            o("exists = workplace")
            o("}")
            for line in work:
                o(line)
            for g, adds in gated:
                o("if = {")
                o(f"limit = {{ workplace = {{ {_group_gate(g, parents)} }} }}")
                for line in adds:
                    o(line)
                o("}")
            o("}")
        o("}")
    _starvation(o, "state_mortality_mult", mild, severe)
    if "state_non_homeland_mortality_mult" in reg:
        o("if = {")
        o("limit = { state = { NOT = { is_homeland_of_country_cultures = owner } } }")
        o("add = state.modifier:state_non_homeland_mortality_mult")
        o("}")
    o("add = { value = state.modifier:state_mortality_wealth_mult multiply = wealth }")
    o("min = 0")
    o("}")
    o("")
    read = set(re.findall(r"modifier:(\w+)", "\n".join(o.lines)))
    unregistered = sorted(read - reg)
    assert not unregistered, f"unregistered modifier types read: {unregistered}"


def buy_package_costs(root):
    import re
    text = (root / BUY_PACKAGES).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"^wealth_(\d+) = \{(.*?)^\}", text, re.S | re.M):
        goods = re.search(r"goods = \{[^\n]*\n(.*?)\n\t\}", m.group(2), re.S)
        out[int(m.group(1))] = sum(float(v) for v in re.findall(r"= ([0-9.]+)", goods.group(1)))
    return out


def _factor_body(o, cause, factor):
    """One factor's body, reading only what the step stored (te_demog_cause_inputs_store, the drifted medicine; the
    step's copies of the walk's SoL and literacy, which a walk without a step rewrites), in
    demographics_model.cause_factors' arithmetic."""
    s = P.CAUSE_SHORT[cause]
    span = P.WEALTH_TFR_HIGH_SOL - P.WEALTH_TFR_LOW_SOL
    if factor == "medicine":
        o("value = 1")
        o(f"subtract = {{ value = var:te_dg_acc multiply = var:te_dg_trt_{s} }}")
    elif factor == "sol":
        at_high = P.SOL_INFECTION_AT_HIGH if cause == "infection" else P.SOL_CHRONIC_AT_HIGH
        o(f"value = var:te_dg_in_sol subtract = {P.WEALTH_TFR_LOW_SOL} divide = {span} min = 0 max = 1")
        o(f"multiply = {lit(at_high - 1)} add = 1")
    elif factor == "poverty":
        o(f"value = {P.POVERTY_INFECTION_SOL} subtract = var:te_dg_in_sol "
          f"divide = {P.POVERTY_INFECTION_SOL - P.POVERTY_INFECTION_FLOOR_SOL} min = 0 max = 1")
        o(f"multiply = {lit(P.POVERTY_INFECTION_AT_FLOOR - 1)} add = 1")
    elif factor == "literacy":
        o(f"value = var:te_dg_in_lit multiply = {lit(-P.LITERACY_INFECTION_WEIGHT)} add = 1")
    elif factor == "crowding":
        o(f"value = var:te_dg_in_crowd multiply = {lit(P.CROWDING_INFECTION_PER_PULL)} add = 1")
    elif factor == "laws":
        o(f"value = 1 add = var:te_dg_in_{s} min = {lit(P.MORTALITY_MULT_FLOOR)}")
    elif factor == "turmoil":
        o(f"value = var:te_dg_in_turm multiply = {lit(P.TURMOIL_EXTERNAL_WEIGHT)} add = 1")
    elif factor == "safety":
        # modern safety: 1 - the share the step stored; a step from before it stored none, so the factor reads 1 until
        # the state's next step
        o("value = 1")
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_in_saf_{s} }}")
        o(f"subtract = var:te_dg_in_saf_{s}")
        o("}")
    elif factor == "malaria":
        # calibration step 3: 1 + the trait's excess x (1 - the control); a step from before it stored neither, so the
        # factor reads 1 until the state's next step
        o("value = 0")
        o("if = {")
        o("limit = {")
        o("has_variable = te_dg_in_mal")
        o("has_variable = te_dg_in_malc")
        o("}")
        for i, level in enumerate(sorted(P.MALARIA_INFECTION, reverse=True)):
            o(f"{'if' if i == 0 else 'else_if'} = {{")
            o(f"limit = {{ var:te_dg_in_mal >= {level} }}")
            o(f"add = {lit(P.MALARIA_INFECTION[level])}")
            o("}")
        o("multiply = { value = 1 subtract = var:te_dg_in_malc }")
        o("}")
        o("add = 1")
    else:
        raise KeyError(factor)


def medicine_target_values(o):
    o("# State scope: where medicine is heading, read live from the census's types (the Causes of Death plan):")
    o("# health-care access (the base plus the health law's lines), each cause's treatment, and the share of the gap")
    o("# a census step closes (demographics_model.medicine_targets, diffusion).")
    o("te_demog_access_target = {")
    o(f"value = modifier:{P.ACCESS_TYPE}")
    o(f"add = {lit(P.BASE_ACCESS)}")
    o("min = 0")
    o("max = 1")
    o("}")
    for cause in P.MEDICINE_CAUSES:
        o(f"te_demog_treatment_target_{cause} = {{")
        o(f"value = modifier:{P.TREATMENT_TYPE[cause]}")
        o("min = 0")
        o(f"max = {lit(P.TREATMENT_CAP[cause])}")
        o("}")
    o("te_demog_medical_diffusion = {")
    o(f"value = modifier:{P.DIFFUSION_TYPE}")
    o(f"add = {lit(P.DIFFUSION_BASE)}")
    o("min = 0")
    o(f"max = {lit(P.DIFFUSION_MAX)}")
    o("}")
    for cause in P.MEDICINE_CAUSES:
        o(f"# State scope: {cause}'s medicine at its targets (the section's arrow).")
        o(f"te_demog_f_{cause}_medicine_target = {{")
        o("value = 1")
        o(f"subtract = {{ value = te_demog_access_target multiply = te_demog_treatment_target_{cause} }}")
        o("}")
    o("")


def malaria_values(o, root):
    """Calibration step 3, call 2 (owner, 2026-10-12; the spec's §2.2): the state's malaria level, which the step stores
    as te_dg_in_mal (P.MALARIA_TRAITS: 1 malaria, 2 severe) beside the control P.MALARIA_CONTROL_TYPE (te_dg_in_malc;
    malaria_prevention's line, not quinine's). The trait is read with has_state_trait, as vanilla reads it beside its own
    quinine test (cultural_community_values.txt), which only makes sense if the trait outlasts the technology that
    disables its modifier. The second value reads the same level from the state regions the map files give the traits:
    the self-check malaria_trait_read's ground truth, and the census's read instead of has_state_trait under
    P.MALARIA_READS_REGION_LIST (its fallback)."""
    by_level = {}
    for region, level in sorted(R.malaria_levels(state_regions=root / "map_data" / "state_regions").items()):
        by_level.setdefault(level, []).append(region)
    by_trait = {level: trait for trait, level in P.MALARIA_TRAITS.items()}
    o("# State scope (calibration step 3): the state's malaria level from its state region's trait in the map files.")
    o("te_demog_malaria_level_listed = {")
    o("value = 0")
    for i, level in enumerate(sorted(by_level, reverse=True)):
        o(f"{'if' if i == 0 else 'else_if'} = {{")
        o("limit = {")
        o("OR = {")
        for region in by_level[level]:
            o(f"state_region = s:{region}")
        o("}")
        o("}")
        o(f"add = {level}")
        o("}")
    o("}")
    o("# State scope (calibration step 3): the malaria level the step stores (te_dg_in_mal).")
    o("te_demog_malaria_level = {")
    if P.MALARIA_READS_REGION_LIST:
        o("value = te_demog_malaria_level_listed")
    else:
        o("value = 0")
        for i, level in enumerate(sorted(by_trait, reverse=True)):
            o(f"{'if' if i == 0 else 'else_if'} = {{")
            o(f"limit = {{ has_state_trait = {by_trait[level]} }}")
            o(f"add = {level}")
            o("}")
    o("}")
    o("")


def multipliers(o):
    medicine_target_values(o)
    for cause, factors in P.CAUSE_FACTORS.items():
        for factor in factors:
            o(f"# State scope: {cause}'s {factor} factor (demographics_model.cause_factors), on the step's stored inputs.")
            o(f"te_demog_f_{cause}_{factor} = {{")
            _factor_body(o, cause, factor)
            o("}")
        if cause == "maternal":
            o("# State scope: maternal deaths per 100,000 births (an MMR, not a multiplier): the base rate")
            o("# times the cause's factors (demographics_model.cause_multipliers, group_rates).")
        else:
            o(f"# State scope: the {cause} cause's multiplier, the product of its factors (demographics_model.cause_multipliers).")
        o(f"te_demog_mult_{cause} = {{")
        o(f"value = te_demog_f_{cause}_{factors[0]}")
        for factor in factors[1:]:
            o(f"multiply = te_demog_f_{cause}_{factor}")
        if cause == "maternal":
            o(f"multiply = {P.MATERNAL_PER_100K_BIRTHS}")
        o("}")
        o("")
        if cause == "infection":
            w = P.INFECTION_ADULT_MEDICINE
            lo, hi = P.INFECTION_ADULT_AGES
            o(f"# State scope: the adults' infection factor (#1045; demographics_model.infection_adult): infection at ages "
              f"{lo}-{hi - 1}")
            o(f"# takes medicine a second time at {lit(w)}, 1 - {lit(w)} x access x treatment, on top of its multiplier.")
            o("te_demog_infection_adult = {")
            o("value = te_demog_f_infection_medicine")
            o(f"multiply = {lit(w)}")
            o(f"add = {lit(1 - w)}")
            o("}")
            o("")
    o("# State scope: women's share of the workforce, the base plus the women's-rights laws' line (modifier-types")
    o("# stage 3; demographics_model.female_work_share), within 0-1.")
    o("te_demog_female_work_share = {")
    o(f"value = {lit(P.FEMALE_WORK_SHARE_DEFAULT)}")
    o(f"add = modifier:{P.FEMALE_WORK_SHARE_TYPE}")
    o("min = 0")
    o("max = 1")
    o("}")
    o("")
    o("# State scope: the share of the gap to desired fertility a population can close (spec 2.3;")
    o("# demographics modifier types, stage 2): traditional methods plus the techs' contraception,")
    o("# at most 1, scaled by literacy, plus the fertility-control shift.")
    o("te_demog_means = {")
    o("value = {")
    o(f"value = modifier:{P.CONTRACEPTION_TYPE}")
    o(f"add = {lit(P.TRADITIONAL_MEANS)}")
    o("min = 0")
    o("max = 1")
    o("}")
    o(f"# access: literacy, plus Sex Education's {P.MEANS_LITERACY_TYPE} (phase 2 step 3b), at most 1")
    o(f"multiply = {{ value = var:te_dg_lit add = modifier:{P.MEANS_LITERACY_TYPE} max = 1 "
      f"multiply = {lit(1 - P.MEANS_ACCESS_BASE)} add = {lit(P.MEANS_ACCESS_BASE)} }}")
    o(f"# laws, history, events and measures: Family Limitation and its kin ({P.MEANS_SHIFT_TYPE})")
    o(f"add = modifier:{P.MEANS_SHIFT_TYPE}")
    o(f"max = {lit(P.MEANS_CAP)}")
    o("min = 0")
    o("}")
    o("")


def constants(o):
    o("# Constants the hand-written script reads (demographics_params.py).")
    k = {
        "female_births_per_100k": P.FEMALE_BIRTH_PER_100K, "male_births_per_100k": P.MALE_BIRTH_PER_100K,
        "education_weight": P.EDUCATION_WEIGHT, "survival_weight": P.SURVIVAL_WEIGHT,
        "urban_weight": P.URBAN_WEIGHT, "war_male_share": P.WAR_DEAD_MALE_SHARE,
        "residual_noise_share": P.RESIDUAL_NOISE_SHARE,
        "labour_female_min": P.LABOUR_FEMALE_SHARE_MIN, "labour_female_max": P.LABOUR_FEMALE_SHARE_MAX,
        "family_base": P.FAMILY_BASE, "family_rights_weight": P.FAMILY_RIGHTS_WEIGHT,
        "full_female_work_share": P.FULL_FEMALE_WORK_SHARE, "chain_step": P.CHAIN_STEP, "chain_cap": P.CHAIN_CAP,
        "crisis_at_war": P.CRISIS_AT_WAR,
        "on_top_scale_min": P.ON_TOP_SCALE_MIN, "on_top_factor_min": P.ON_TOP_FACTOR_MIN,
        "window_start_weight": P.WINDOW_START_WEIGHT,
        "rate_total_floor": P.RATE_TOTAL_FLOOR,
        "rate_bare_min": P.RATE_BARE_MIN,
        "natural_fertility_floor": P.NATURAL_FERTILITY_FLOOR,
        "wealth_line_floor": P.WEALTH_LINE_FLOOR,
        "medicine_snap": P.MEDICINE_SNAP, "medicine_snap_neg": -P.MEDICINE_SNAP,
        "deaths_on_top_high": P.DEATHS_ON_TOP_HIGH, "base_access": P.BASE_ACCESS,
        "maternal_base": P.MATERNAL_PER_100K_BIRTHS,
        "practice_rate": P.PRACTICE_RATE,
        # phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1)
        "child_work_age": P.CHILD_WORK_AGE, "working_age": P.WORKING_AGE,
        "after_pension_share": P.AFTER_PENSION_SHARE, "men_rate": P.MEN_RATE, "women_base": P.WOMEN_BASE,
        "women_lower": P.WOMEN_LOWER, "womens_work_full": P.WOMENS_WORK_FULL,
        "rate_max": P.RATE_MAX, "health_need_1836": P.HEALTH_NEED_1836,
        "need_newborn": M.band_value(P.HEALTH_NEED, 0), "pension_age_standard": P.PENSION_AGE["standard"],
    }
    for name, value in k.items():
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    o("# State scope: the family share's transport term, the transport technologies' line (modifier-types stage 3;")
    o("# demographics_model.migrant_profile).")
    o("te_demog_family_transport = {")
    o(f"value = modifier:{P.FAMILY_MIGRATION_TYPE}")
    o("}")
    o("")


# Phase 2 step 4 (the consequences design §4): the pool's sums, women's then men's (they replaced the 18-40 sums,
# te_dg_f1840 and te_dg_m1840, in te_demog_normalize_bands' order).
POOL_SUMS = ["te_dg_faw", "te_dg_fam"]


def migrant_booking_values(o):
    """The migrant booking's constants (2026-10-12): the cap and the labour kind's balance (demographics_params.py)."""
    o("# The migrant booking (2026-10-12): the cap on each class and sex (te_demog_migrant_rates) and the labour")
    o("# kind's sex split correcting itself (te_demog_labour_balance; demographics_model.labour_balance_weight).")
    # the balance ramps divide by their widths, floored at 1 in the script
    assert P.LABOUR_BALANCE_LOW[0] - P.LABOUR_BALANCE_LOW[1] >= 1
    assert P.LABOUR_BALANCE_HIGH[1] - P.LABOUR_BALANCE_HIGH[0] >= 1
    k = {"migrant_cap_in": P.MIGRANT_CAP_IN, "migrant_cap_out": P.MIGRANT_CAP_OUT,
         "labour_balance_share": P.LABOUR_BALANCE_SHARE,
         "labour_low_start": P.LABOUR_BALANCE_LOW[0], "labour_low_full": P.LABOUR_BALANCE_LOW[1],
         "labour_high_start": P.LABOUR_BALANCE_HIGH[0], "labour_high_full": P.LABOUR_BALANCE_HIGH[1]}
    for name, value in k.items():
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    o("")


def youth_bands():
    """The five-year bands that make up P.YOUTH_AGES (20-29: bands 4 and 5)."""
    lo, hi = P.YOUTH_AGES
    assert lo % P.BAND_WIDTH == 0 and (hi + 1) % P.BAND_WIDTH == 0, "the youth ages must be whole bands"
    return list(range(lo // P.BAND_WIDTH, (hi + 1) // P.BAND_WIDTH))


def consequence_values(o):
    """Phase 2 step 4's constants and band sums (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-
    design.md §4), in a block of their own so step 2's and step 3's additions to the generator stay apart. The hand-
    written values that read them are in te_demog_consequence_values.txt."""
    o("# Phase 2 step 4: conscription, the youth bulge and sex balance (demographics_params.py).")
    k = {
        "pool_from": P.POOL_FROM, "pool_to": P.POOL_TO,
        "conscription_ref": P.CONSCRIPTION_REF, "conscription_min": P.CONSCRIPTION_MIN,
        "youth_from": P.YOUTH_FROM, "youth_span": P.YOUTH_SPAN, "youth_unemployment_full": P.YOUTH_UNEMPLOYMENT_FULL,
        "sex_fewer_from": P.SEX_FEWER_FROM, "sex_fewer_span": P.SEX_FEWER_FROM - P.SEX_FEWER_FULL,
        "sex_births_floor": P.SEX_BIRTHS_FLOOR, "sex_women_rate": P.SEX_WOMEN_RATE,
        "sex_more_from": P.SEX_MORE_FROM, "sex_more_span": P.SEX_MORE_FULL - P.SEX_MORE_FROM,
        # 1 applies each effect, 0 holds it back (P.CONSCRIPTION_EFFECTS, YOUTH_BULGE_EFFECTS, SEX_BALANCE_EFFECTS)
        "conscription_effects": 1 if P.CONSCRIPTION_EFFECTS else 0, "conscription_cut": P.CONSCRIPTION_CUT,
        "youth_effects": 1 if P.YOUTH_BULGE_EFFECTS else 0, "youth_cut": P.YOUTH_CUT,
        "sex_effects": 1 if P.SEX_BALANCE_EFFECTS else 0,
    }
    for name, value in k.items():
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    bands = youth_bands()
    lo, hi = P.YOUTH_AGES
    for scope, prefix, people in (("state", "te_dg_b", "{ value = var:te_dg_people min = 1 }"),
                                  ("country", "te_dg_cb", "{ value = te_demog_country_people min = 1 }")):
        name = "te_demog_youth_share" if scope == "state" else "te_demog_country_youth_share"
        o(f"# {scope.capitalize()} scope: the share of people aged {lo}-{hi} (bands {', '.join(map(str, bands))}), 0 "
          "before a census.")
        o(f"{name} = {{")
        o("value = 0")
        o(f"if = {{ limit = {{ has_variable = {prefix}f{bands[0]} }}")
        o(f"value = var:{prefix}f{bands[0]}")
        for b in bands:
            for sex in ("f", "m"):
                if (b, sex) != (bands[0], "f"):
                    o(f"add = var:{prefix}{sex}{b}")
        o(f"divide = {people}")
        o("}")
        o("}")
    # the census's men by scope, and the country's people (a state has te_dg_people): the bands' sums
    for scope, prefix, whats in (("state", "te_dg_b", (("men", ("m",)),)),
                                 ("country", "te_dg_cb", (("men", ("m",)), ("people", ("f", "m"))))):
        o(f"# {scope.capitalize()} scope: the census's {' and '.join(w for w, _ in whats)} (its bands' sum), 0 before a "
          "census.")
        for what, sexes in whats:
            o(f"te_demog_{scope}_{what} = {{")
            o("value = 0")
            o(f"if = {{ limit = {{ has_variable = {prefix}m0 }}")
            first = True
            for b in range(P.BANDS):
                for sex in sexes:
                    o(f"{'value' if first else 'add'} = var:{prefix}{sex}{b}")
                    first = False
            o("}")
            o("}")
    o("")


def work_values(o):
    o("# State scope (phase 2 step 1): the 10-14s' participation, the childrens'-rights laws' line, within 0-1")
    o(f"# ({P.CHILD_WORK_TYPE}: Child Labor Allowed 0.3, Restricted Child Labor 0.1;")
    o("# demographics_model.child_work_share).")
    o("te_demog_child_work = {")
    o(f"value = modifier:{P.CHILD_WORK_TYPE}")
    o("min = 0")
    o("max = 1")
    o("}")
    o("# Pop scope: the pop's own working-adult ratio (vanilla pop_types; the define for the rest).")
    o("te_demog_pop_base_ratio = {")
    o(f"value = {lit(P.POP_BASE_RATIO_DEFAULT)}")
    for pop_type, ratio in P.POP_BASE_RATIO.items():
        o(f"if = {{ limit = {{ is_pop_type = {pop_type} }} value = {lit(ratio)} }}")
    o("}")
    o("")


def work_step2_values(o):
    """Phase 2 step 2's constants and generated values (te_demog_work_effects.txt, te_demog_work_values.txt): the
    workforce term, the pension setting and the two bills. Kept apart from the other steps' blocks."""
    o("# Phase 2 step 2 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2): the")
    o("# workforce term, the pension setting and the bills (demographics_params.py, its step 2 section).")
    k = {
        "working_adult_base": P.WORKING_ADULT_BASE,
        # the guard: the lowest pop base + W + the lines on top at least WF_POP_RATIO_MIN, so W + the lines on top at
        # least this
        "wf_pop_floor": P.WF_POP_RATIO_MIN - P.POP_BASE_RATIO_MIN,
        "pension_age_early": P.PENSION_AGE["early"], "pension_age_raised": P.PENSION_AGE["raised"],
        "pension_link_offset": P.PENSION_LINK_OFFSET, "pension_link_floor": P.PENSION_LINK_FLOOR,
        "pension_link_step": P.PENSION_LINK_STEP, "pension_link_step_neg": -P.PENSION_LINK_STEP,
        "pension_term_years": P.PENSION_TERM_YEARS,
        "pension_b_per_level": P.PENSION_B_PER_LEVEL,
        "health_need_weight": P.HEALTH_NEED_WEIGHT, "health_need_cap": P.HEALTH_NEED_CAP,
        "work_split_first": P.WORK_SPLIT_AGES[0], "work_split_last": P.WORK_SPLIT_AGES[1],
        "pension_ai_bill_high": P.PENSION_AI_BILL_HIGH, "pension_ai_bill_low": P.PENSION_AI_BILL_LOW,
        "pension_ai_debt": P.PENSION_AI_DEBT,
        "pension_ai_unemployment": P.PENSION_AI_UNEMPLOYMENT,
        "pension_ai_unemployment_low": P.PENSION_AI_UNEMPLOYMENT_LOW,
        **{f"pension_pos_{pos}": i for pos, i in P.PENSION_POSITION_ID.items()},
    }
    for name, value in k.items():
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    o("# Country scope: the health bill's chronic-treatment technologies (demographics_model.health_term).")
    o("te_demog_health_tech_term = {")
    o("value = 0")
    for tech in P.HEALTH_TECHS:
        o(f"if = {{ limit = {{ has_technology_researched = {tech} }} add = {lit(P.HEALTH_TECH_STEP)} }}")
    o("}")
    o("")


def _by_value(table):
    """[(value, [keys])] for a {key: value} table, by value then key: one if per value."""
    out = {}
    for key, value in table.items():
        out.setdefault(value, []).append(key)
    return [(v, sorted(keys)) for v, keys in sorted(out.items())]


def _start_entries(p):
    """The start ladder's two tables with the entries that change nothing left out: a strategic region at 0 (the
    ladder's default), and a state region at its strategic region's value. The fit can set a held share to 0
    (2026-10-12: India's and East Asia's), which would otherwise write a test a state a year for nothing."""
    regions = {r: v for r, v in P.PRACTICE_START_REGION[p].items() if v}
    of = R.strategic_region_of()
    states = {s: v for s, v in P.PRACTICE_START_STATE[p].items() if v != regions.get(of.get(s), 0.0)}
    return regions, states


def practices(o):
    """Late Marriage and Birth Spacing (docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md): each
    practice's start ladder, target and term, from demographics_params.py. The machinery that reads them is
    te_demog_practice_effects.txt."""
    o("# State scope: each practice's start share (the late-marriage spec 3.2, 3.3; demographics_model.practice_start):")
    o("# its strategic region's value, then its state region's, which wins. Geography, not culture. An entry that")
    o("# changes nothing (a 0, a state at its region's value) is left out.")
    for p in P.PRACTICES:
        o(f"te_demog_pr_start_{p} = {{")
        o("value = 0")
        for key, table in zip(("region = sr:", "state_region = s:"), _start_entries(p)):
            for value, names in _by_value(table):
                o("if = {")
                o("limit = {")
                o("OR = {")
                for name in names:
                    o(f"{key}{name}")
                o("}")
                o("}")
                o(f"value = {lit(value)}")
                o("}")
        o("}")
        o("")
    o("# State scope: the means beyond traditional methods as erosion (demographics_model.practice_erosion): the techs'")
    o("# contraception x access by literacy, from 0 at PRACTICE_EROSION_FROM to its weight at FROM + SPAN.")
    o("te_demog_pr_erosion_contraception = {")
    o(f"value = modifier:{P.CONTRACEPTION_TYPE}")
    o(f"multiply = {{ value = var:te_dg_lit multiply = {lit(1 - P.MEANS_ACCESS_BASE)} add = {lit(P.MEANS_ACCESS_BASE)} }}")
    o(f"subtract = {lit(P.PRACTICE_EROSION_FROM)}")
    o(f"divide = {lit(P.PRACTICE_EROSION_SPAN)}")
    o("min = 0")
    o("max = 1")
    o(f"multiply = {lit(P.PRACTICE_EROSION_CONTRACEPTION)}")
    o("}")
    o("")
    o("# State scope: how much of each practice's start its conditions have eroded, 0-1 (demographics_model.")
    o("# practice_erosion): contraception, and for Birth Spacing the health-care access medicine has reached above the")
    o("# base (te_dg_acc, which drifts toward its target since the Causes of Death plan; set before any practice reads")
    o("# it, by te_demog_medicine_at_target at a seed and te_demog_medicine_drift at a step). The seed with no sibling")
    o("# holding a share is the start less it (practice_seed; review I2), and the target adds Late Marriage's drivers")
    o("# to that (practice_target): impartible inheritance on the farms (the laws' line, Primogeniture's and Undivided")
    o(f"# Farm Succession's {P.LM_FARMS_TYPE}, x the agrarian share) and women's paid work. Read after the walk.")
    for p in P.PRACTICES:
        o(f"te_demog_pr_erosion_{p} = {{")
        o("value = te_demog_pr_erosion_contraception")
        if P.PRACTICE_EROSION_ACCESS[p]:
            o(f"add = {{ value = var:te_dg_acc subtract = te_demog_k_base_access divide = {lit(P.PRACTICE_ACCESS_SPAN)} "
              f"min = 0 max = 1 multiply = {lit(P.PRACTICE_EROSION_ACCESS[p])} }}")
        o("max = 1")
        o("}")
        o(f"te_demog_pr_seed_{p} = {{")
        o(f"value = te_demog_pr_erosion_{p}")
        o("multiply = -1")
        o("add = 1")
        o(f"multiply = te_demog_pr_start_{p}")
        o("}")
        o(f"te_demog_pr_target_{p} = {{")
        o(f"value = te_demog_pr_seed_{p}")
        if p == "lm":
            o(f"add = {{ value = var:te_dg_agr_share multiply = modifier:{P.LM_FARMS_TYPE} }}")
            o(f"add = {{ value = var:te_dg_fjob_share multiply = te_demog_female_work_share "
              f"multiply = {lit(P.LM_WOMENS_WORK / P.FULL_FEMALE_WORK_SHARE)} }}")
        o("min = 0")
        o("max = 1")
        o("}")
        o("")
    o("# State or country scope: each practice's term in children per woman, 1 - cut x share; 1 with no share yet")
    o("# (an old save's state before its next census step, whose te_dg_tfr has no practice in it either: plan D7).")
    for p in P.PRACTICES:
        o(f"te_demog_pr_term_{p} = {{")
        o("value = 1")
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_pr_{p} }}")
        o(f"subtract = {{ value = var:te_dg_pr_{p} multiply = {lit(P.PRACTICE_CUT[p])} }}")
        o("}")
        o("}")
    o("te_demog_pr_terms = {")
    o("value = 1")
    for p in P.PRACTICES:
        o(f"multiply = te_demog_pr_term_{p}")
    o("}")
    o("# State or country scope, the panel (spec 5.3): women's mean age at first marriage from the Late Marriage share,")
    o("# and the Birth Spacing share (0 with none).")
    o("te_demog_marriage_age = {")
    o(f"value = {lit(P.MARRIAGE_AGE_AT_ZERO)}")
    o("if = {")
    o("limit = { has_variable = te_dg_pr_lm }")
    o(f"add = {{ value = var:te_dg_pr_lm multiply = {lit(P.MARRIAGE_AGE_SPAN)} }}")
    o("}")
    o("}")
    o("te_demog_pr_share_bs = {")
    o("value = 0")
    o("if = {")
    o("limit = { has_variable = te_dg_pr_bs }")
    o("value = var:te_dg_pr_bs")
    o("}")
    o("}")
    o("")


def practice_loops(o):
    o("# The practices' machinery (te_demog_practice_effects.txt) for each practice in P.PRACTICES. Phase 3's neighbour")
    o("# spread reads te_demog_practices_neighbours' sums (te_demog_spread_effects_generated.txt); Family Limitation is")
    o("# national, not a state practice (te_demog_fl_effects.txt).")
    for name in ("seed", "step", "country_init", "country_add", "country_store"):
        o(f"te_demog_practices_{name} = {{")
        for p in P.PRACTICES:
            o(f"te_demog_practice_{name} = {{ P = {p} }}")
        o("}")
    o("")


# ---- Phase 2 step 3b: the census reads the Family Policy measures and laws ------------------------------------------
# docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §3.5. Sex Education's access sits in
# te_demog_means (multipliers) and Restricted Contraception's maternal deaths in the maternal cause's "laws" factor
# (P.CAUSE_FACTORS); the rest is here.

def family_policy_values(o):
    o("# Phase 2 step 3b (the design §3.5): family policy in the census. State scope.")
    o("# Family policy's factor on desired fertility (demographics_model.policy_term): 1 + the desired type (the measures'")
    o("# and Pro-Natalist Policy's lines), Birth Limit's part relieved by the Rural Exemption's type x the state's")
    o("# agrarian share (Birth Limit's part is negative: the relief raises the factor), at least 0. te_demog_desired")
    o("# multiplies by it; the TFR tooltips show it.")
    o("te_demog_tfr_policy = {")
    o(f"value = modifier:{P.DESIRED_TYPE}")
    o("if = {")
    o(f"limit = {{ modifier:{P.BIRTH_LIMIT_RELIEF_TYPE} > 0 }}")
    o("subtract = {")
    o("value = te_demog_ms_birth_limit_part")
    o(f"multiply = {{ value = modifier:{P.BIRTH_LIMIT_RELIEF_TYPE} max = 1 }}")
    o("multiply = te_demog_agr_share")
    o("}")
    o("}")
    o("add = 1")
    o("min = 0")
    o("}")
    o("# The walk's agrarian share (Peasants and Farmers over people), 0 before a walk.")
    o("te_demog_agr_share = {")
    o("value = 0")
    o("if = { limit = { has_variable = te_dg_agr_share } value = var:te_dg_agr_share }")
    o("}")
    o("# City life's relief (Family Housing): the urban share it leaves, 1 - the type within 0-1 (te_demog_tfr_urban).")
    o("te_demog_urban_relief_left = {")
    o(f"value = 1 subtract = {{ value = modifier:{P.URBAN_RELIEF_TYPE} min = 0 max = 1 }}")
    o("}")
    o("# What the step used (te_demog_family_policy_store, in te_demog_prepare), for the children-per-woman tooltips: the")
    o("# stored policy term and the urban share Family Housing leaves, as te_demog_natural_shown, so a measure switched on")
    o("# between steps shows when the census's figure takes it. The live value for a census state from before the store.")
    o("te_demog_tfr_policy_shown = {")
    o("value = te_demog_tfr_policy")
    o("if = { limit = { has_variable = te_dg_policy } value = var:te_dg_policy }")
    o("}")
    o("te_demog_urban_left_stored = {")
    o("value = te_demog_urban_relief_left")
    o("if = { limit = { has_variable = te_dg_urban_left } value = var:te_dg_urban_left }")
    o("}")
    o("# The sex ratio at birth's add (demographics_model.newborn_split): the type once prenatal sexing exists, else 0.")
    o("te_demog_srb_add = {")
    o("value = 0")
    o(f"if = {{ limit = {{ owner = {{ has_technology_researched = {P.PRENATAL_SEXING_TECH} }} }} "
      f"value = modifier:{P.SRB_TYPE} min = 0 }}")
    o("}")
    o(f"te_demog_k_desired_floor = {{ value = {lit(P.DESIRED_FLOOR)} }}")
    o(f"te_demog_k_desired_cap = {{ value = {lit(P.DESIRED_CAP)} }}")
    o(f"te_demog_k_srb_base = {{ value = {lit(P.SRB_BASE)} }}")
    o("")


def family_policy_effects(o):
    o("# Phase 2 step 3b: THIS = a state, in te_demog_prepare before te_demog_desired: the family policy term and the urban")
    o("# share Family Housing leaves, stored with the step's other terms (te_dg_natural's pattern), so te_demog_tfr_urban")
    o("# and the tooltips read what the step used until the next one.")
    o("te_demog_family_policy_store = {")
    o("set_variable = { name = te_dg_policy value = te_demog_tfr_policy }")
    o("set_variable = { name = te_dg_urban_left value = te_demog_urban_relief_left }")
    o("}")
    o("# Phase 2 step 3b (the design §3.4): the newborns' split in the step (demographics_model.newborn_split). THIS = a")
    o("# state, in te_demog_step_run before the sweep: girls and boys per 100,000 births into locals, the constants")
    o("# unless prenatal sexing and a positive sex-ratio type move it (100 girls to te_demog_k_srb_base + it boys).")
    o("te_demog_newborn_split = {")
    o("set_local_variable = { name = te_dg_nb_f value = te_demog_k_female_births_per_100k }")
    o("set_local_variable = { name = te_dg_nb_m value = te_demog_k_male_births_per_100k }")
    o("set_local_variable = { name = te_dg_nb_srb value = te_demog_srb_add }")
    o("if = {")
    o("limit = { local_var:te_dg_nb_srb > 0 }")
    o("set_local_variable = {")
    o("name = te_dg_nb_f")
    o("value = { value = 10000000 divide = { value = local_var:te_dg_nb_srb add = te_demog_k_srb_base add = 100 min = 100 } }")
    o("}")
    o("set_local_variable = { name = te_dg_nb_m value = { value = 100000 subtract = local_var:te_dg_nb_f } }")
    o("}")
    o("}")
    o("")


def debug_values(o):
    o("# State scope: each slot as per mille of the state's people, for the replay lines (Task 15).")
    o("# One sequential block each, so the scale and the people are not rounded on their own.")
    share = "multiply = var:te_dg_scale multiply = 1000 divide = { value = var:te_dg_people min = 1 }"
    for s in ("f", "m"):
        for k in range(N):
            o(f"te_demog_dbg_{s}{k} = {{ value = 0 if = {{ limit = {{ has_variable = te_dg_{s}{k} }} "
              f"value = var:te_dg_{s}{k} {share} }} }}")
    for s in ("f", "m"):
        o(f"te_demog_dbg_pool_{s} = {{ value = 0 if = {{ limit = {{ has_variable = te_dg_p{s} }} "
          f"value = var:te_dg_p{s} {share} }} }}")
    o("")


def render_values(root):
    o = Out()
    o(HEADER.rstrip("\n"))
    o("")
    engine_curves(o, G.read_defines(root / "common" / "defines" / "extra_defines.txt"))
    engine_rate_terms(o, root)
    malaria_values(o, root)
    multipliers(o)
    practices(o)
    constants(o)
    migrant_booking_values(o)
    work_values(o)
    family_policy_values(o)
    work_step2_values(o)
    consequence_values(o)
    debug_values(o)
    tail_values(o)
    return o.text()


def tail_values(o):
    """The life table's open last interval (2026-10-20; demographics_params.LT_TAIL_RATE_MIN)."""
    o("# The life tables' death rate past 150 is at least this, per 100,000 (te_demog_lt_tail; demographics_model.tail_years).")
    o(f"te_demog_k_lt_tail_rate_min = {{ value = {lit(P.LT_TAIL_RATE_MIN)} }}")
    o("# The Life Expectancy chart's axis: the largest figure its samples hold, at least the first, at most the second, where")
    o("# the panel's figures read over (te_demog_history_e0_axis; the GUI's comparisons hold the same 10,000).")
    o(f"te_demog_k_e0_axis_min = {{ value = {lit(P.E0_AXIS_MIN)} }}")
    o(f"te_demog_k_e0_shown_max = {{ value = {lit(P.E0_SHOWN_MAX)} }}")


LINE_HEADER = ("# The engine's birth and mortality lines on laws, technologies and institutions, moved to script-only types\n"
               "# (owner, 2026-10-11; docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md): a fixed-sign\n"
               "# pair per field (P.ENGINE_LINE_FIELDS), re-applied at the two families' sum while te_demog_lines_apply holds.\n"
               "# A release keeps these files (scripts/release/comment_out_census_inputs.py doesn't read them).")


def _line_fields():
    """[(engine field, short, [the families' types for it])] in P.ENGINE_LINE_FIELDS' order."""
    return [(f, P.ENGINE_LINE_SHORT[f], [P.ENGINE_LINE_TYPES[(fam, f)] for fam in ("absorbed", "ontop")
                                          if (fam, f) in P.ENGINE_LINE_TYPES])
            for f in P.ENGINE_LINE_FIELDS]


def _render_line_modifiers(fields, header):
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    for field, short, _types in fields:
        for sign, unit in (("up", "1"), ("down", "-1")):
            o(f"te_demog_line_{short}_{sign} = {{")
            o("icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds")
            o(f"{field} = {unit}")
            o("}")
    return o.text()


def _render_line_values(fields, header, reader="te_demog_rates_refresh"):
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    o("# State scope. te_demog_line_<short>: the families' sum the engine reads; _applied: the pair in force, signed")
    o(f"# (0 with neither held), which {reader} takes off the state read; _up_mult / _down_mult: the")
    o("# multipliers, from the stored sum (te_dg_ln_<short>), ROOT being the state.")
    for field, short, types in fields:
        o(f"te_demog_line_{short} = {{")
        o(f"value = modifier:{types[0]}")
        for t in types[1:]:
            o(f"add = modifier:{t}")
        o("}")
        o(f"te_demog_line_{short}_applied = {{")
        o("value = 0")
        o("if = {")
        o("limit = {")
        o("OR = {")
        o(f"has_modifier = te_demog_line_{short}_up")
        o(f"has_modifier = te_demog_line_{short}_down")
        o("}")
        o("}")
        o(f"value = var:te_dg_ln_{short}")
        o("}")
        o("}")
        o(f"te_demog_line_{short}_up_mult = {{")
        o(f"value = var:te_dg_ln_{short}")
        o("}")
        o(f"te_demog_line_{short}_down_mult = {{")
        o(f"value = var:te_dg_ln_{short}")
        o("multiply = -1")
        o("}")
    return o.text()


def _line_pair_block(o, short):
    """One field's pair at the families' sum, touched only when the sum changed (or a pair was lost)."""
    o(f"set_local_variable = {{ name = te_dg_ln_new value = te_demog_line_{short} }}")
    o("if = {")
    o("limit = {")
    o("OR = {")
    o(f"NOT = {{ has_variable = te_dg_ln_{short} }}")
    o(f"NOT = {{ var:te_dg_ln_{short} = local_var:te_dg_ln_new }}")
    o("# a pair lost while its sum stayed (a save quirk, a state that copied the variable): put it back")
    o("AND = {")
    o(f"NOT = {{ var:te_dg_ln_{short} = 0 }}")
    o(f"NOT = {{ has_modifier = te_demog_line_{short}_up }}")
    o(f"NOT = {{ has_modifier = te_demog_line_{short}_down }}")
    o("}")
    o("}")
    o("}")
    o(f"te_demog_line_{short}_remove = yes")
    o(f"set_variable = {{ name = te_dg_ln_{short} value = local_var:te_dg_ln_new }}")
    o("if = {")
    o(f"limit = {{ var:te_dg_ln_{short} > 0 }}")
    o(f"add_modifier = {{ name = te_demog_line_{short}_up multiplier = te_demog_line_{short}_up_mult }}")
    o("}")
    o("else_if = {")
    o(f"limit = {{ var:te_dg_ln_{short} < 0 }}")
    o(f"add_modifier = {{ name = te_demog_line_{short}_down multiplier = te_demog_line_{short}_down_mult }}")
    o("}")
    o("}")


def _render_line_effects(fields, header, intro, refresh, gate, clear, clear_note, stale_m):
    """A refresh (each field's pair at the families' sum while `gate` holds, else every pair off), its clear and each
    field's remove. stale_m: #892's refresh first takes off a census term that is no longer the census's."""
    o = Out()
    o(HEADER.rstrip("\n"))
    o(header)
    for line in intro:
        o(line)
    o(f"{refresh} = {{")
    if stale_m:
        o("if = {")
        o("limit = {")
        o("has_variable = te_dg_mb")
        o("OR = {")
        o("NOT = { te_demog_effects_run = yes }")
        o("NOT = { has_variable = te_dg_q_b }")
        o("}")
        o("}")
        o("te_demog_rates_clear = yes")
        o("}")
    o("if = {")
    o(f"limit = {{ {gate} = yes }}")
    for _field, short, _types in fields:
        _line_pair_block(o, short)
    o("}")
    o("else = {")
    o(f"{clear} = yes")
    o("}")
    o("}")
    o("")
    o(clear_note)
    o(f"{clear} = {{")
    for _field, short, _types in fields:
        o(f"te_demog_line_{short}_remove = yes")
        o("if = {")
        o(f"limit = {{ has_variable = te_dg_ln_{short} }}")
        o(f"remove_variable = te_dg_ln_{short}")
        o("}")
    o("}")
    o("")
    for _field, short, _types in fields:
        o(f"te_demog_line_{short}_remove = {{")
        for sign in ("up", "down"):
            o("if = {")
            o(f"limit = {{ has_modifier = te_demog_line_{short}_{sign} }}")
            o(f"remove_modifier = te_demog_line_{short}_{sign}")
            o("}")
        o("}")
    return o.text()


def render_line_modifiers():
    return _render_line_modifiers(_line_fields(), LINE_HEADER)


def render_line_values():
    return _render_line_values(_line_fields(), LINE_HEADER)


def render_line_effects():
    return _render_line_effects(
        _line_fields(), LINE_HEADER,
        ["# THIS = ROOT = a state (its monthly pulse, owner change, incorporation and creation; te_demog_events.4 for a new",
         "# game, a law's activation and a technology): each field's pair at the families' sum while te_demog_lines_apply",
         "# holds, touched only when the sum changed; otherwise (the census sets the state's births and deaths) every pair off.",
         "# First, a census term that is no longer the census's comes off now, not at the state's next yearly step, so it and",
         "# the pairs are never both in force: one a rule switched off Full left, or one from a save made before the moved",
         "# lines (no te_dg_q_b, which this build's step always sets with it)."],
        "te_demog_lines_refresh", "te_demog_lines_apply", "te_demog_lines_clear",
        "# THIS = a state: every pair off, with its stored sum (the census's refresh calls it when it first sets M).",
        stale_m=True)


WORKFORCE_LINE_HEADER = (
    "# Phase 2 step 1 (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §1.7): the\n"
    "# working-adult lines' women's-work and replaced families, re-applied by a fixed-sign pair while\n"
    "# te_demog_workforce_lines_apply holds (not Full, or no te_dg_mw: step 2's term). Their own files, gate and\n"
    "# refresh, so the census's births and deaths term never takes them off. A release keeps them.")


def _workforce_line_fields():
    """[(engine field, short, [the families' types for it])] in P.WORKFORCE_LINE_FIELDS' order."""
    return [(f, P.WORKFORCE_LINE_SHORT[f], [P.WORKFORCE_LINE_TYPES[(fam, f)] for fam in ("womens_work", "replaced")
                                             if (fam, f) in P.WORKFORCE_LINE_TYPES])
            for f in P.WORKFORCE_LINE_FIELDS]


def render_workforce_line_modifiers():
    return _render_line_modifiers(_workforce_line_fields(), WORKFORCE_LINE_HEADER)


def render_workforce_line_values():
    return _render_line_values(_workforce_line_fields(), WORKFORCE_LINE_HEADER, reader="step 2's workforce term")


def render_workforce_line_effects():
    return _render_line_effects(
        _workforce_line_fields(), WORKFORCE_LINE_HEADER,
        ["# THIS = ROOT = a state, beside te_demog_lines_refresh at both its call sites: the working-adult pair at the",
         "# families' sum while te_demog_workforce_lines_apply holds; otherwise (step 2's workforce term in force) off."],
        "te_demog_workforce_lines_refresh", "te_demog_workforce_lines_apply", "te_demog_workforce_lines_clear",
        "# THIS = a state: the working-adult pair off, with its stored sum (step 2's term calls it when it first lands).",
        stale_m=False)


# ---- Phase 3: the spreading machinery ---------------------------------------------------------------------------
# Parent spec section 13 (Family Limitation as a general practice) and section 6's Cultural Hegemony row; the
# late-marriage spec 4.4 (the neighbour spread). Its own two files, so the census's generated files keep their blocks.
SPREAD_HEADER = ("# Phase 3 (docs/superpowers/specs/2026-10-08-demographics-design.md section 13; the late-marriage spec 4.4):\n"
                 "# the practices' neighbour spread, Family Limitation as a national practice and Cultural Hegemony's drift on\n"
                 "# desired fertility. The logic is te_demog_fl_effects.txt and te_demog_practice_effects.txt; the twins are\n"
                 "# demographics_model.practice_drift, fl_target, fl_step, fl_line, ch_target and ch_drift.")


def render_spread_values():
    o = Out()
    o(HEADER.rstrip("\n"))
    o(SPREAD_HEADER)
    o("# Constants (demographics_params' phase 3 block).")
    for name, value in (("practice_spread", P.PRACTICE_SPREAD), ("fl_rate", P.FL_RATE), ("fl_spread", P.FL_SPREAD),
                        ("fl_line_min", P.FL_LINE_MIN), ("fl_history", P.FAMILY_LIMITATION_MEANS),
                        ("ch_rate", P.CH_RATE), ("ch_weight", P.CH_WEIGHT), ("ch_low", 1 - P.CH_CAP),
                        ("ch_high", 1 + P.CH_CAP), ("ch_benchmark_max", P.CH_BENCHMARK_MAX)):
        o(f"te_demog_k_{name} = {{ value = {lit(value)} }}")
    o("")
    o("# Country scope: the church laws' weight on Family Limitation's literacy term, 1 + their line, at least 0")
    o(f"# ({P.FL_LITERACY_TYPE}: State Religion and its two variants -0.5, Total Separation and State")
    o("# Atheism +0.5; demographics_model.fl_church).")
    o("te_demog_fl_church = {")
    o("value = 1")
    o(f"add = modifier:{P.FL_LITERACY_TYPE}")
    o("min = 0")
    o("}")
    o("")
    o("# Country scope, after its census stored te_dg_fl_agr and te_dg_fl_lit (te_demog_fl_country_store): where its")
    o("# Family Limitation rises (demographics_model.fl_target). Smallholders under Forced Heirship, the rural birth cut it")
    o("# folds in (not with Undivided Farm Succession, which switches that cut off), plus literacy above its threshold read")
    o("# through the church law, within 0-1.")
    o("te_demog_fl_target = {")
    o("value = 0")
    o("if = {")
    o("limit = {")
    o("has_law = law_type:law_equal_inheritance")
    o("NOT = { te_inh_has_undivided_farms = yes }")
    o("}")
    o(f"add = {{ value = var:te_dg_fl_agr multiply = {lit(P.FL_HEIRSHIP)} }}")
    o("}")
    o(f"add = {{ value = var:te_dg_fl_lit subtract = {lit(P.FL_LITERACY_FROM)} divide = {lit(P.FL_LITERACY_SPAN)} "
      f"min = 0 max = 1 multiply = {lit(P.FL_LITERACY)} multiply = te_demog_fl_church }}")
    o("min = 0")
    o("max = 1")
    o("}")
    o("")
    o("# Country scope: a country's first share under Full (demographics_model.fl_seed): history's modifier's value where")
    o("# history gave it the modifier (France), else 0.")
    o("te_demog_fl_seed = {")
    o("value = 0")
    o("if = {")
    o("limit = { has_modifier = te_demog_family_limitation }")
    o("value = te_demog_k_fl_history")
    o("}")
    o("}")
    o("")
    o("# Country scope: what modern methods have replaced of the share (demographics_model.fl_line), 0 when")
    o("# FL_ERODES is off: its census states' people-weighted contraception erosion (te_dg_fl_ero).")
    o("te_demog_fl_erosion = {")
    o("value = 0" if not P.FL_ERODES else "value = var:te_dg_fl_ero")
    o("min = 0")
    o("max = 1")
    o("}")
    o("")
    o("# Country scope: te_demog_family_limitation's multiplier, the line (te_dg_fl_line) over the modifier's own value.")
    o("te_demog_fl_mult = {")
    o("value = var:te_dg_fl_line")
    o("divide = { value = te_demog_k_fl_history min = 0.01 }")
    o("}")
    o("")
    o("# Country scope: how far the hegemon's culture reaches it, 0-1 (demographics_model.ch_exposure): its foreign")
    o("# benchmark's multiplier over the benchmark's max, while its Cultural Hegemony journal entry runs (the mass-media")
    o("# era); 0 for the hegemon, which pays no benchmark.")
    o("te_demog_ch_exposure = {")
    o("value = 0")
    o("if = {")
    o("limit = {")
    o("has_journal_entry = je_cultural_hegemony")
    o("has_variable = ch_benchmark_applied")
    o("}")
    o("value = var:ch_benchmark_applied")
    o("divide = { value = te_demog_k_ch_benchmark_max min = 0.01 }")
    o("min = 0")
    o("max = 1")
    o("}")
    o("}")
    o("")
    return o.text()


def render_spread_effects():
    o = Out()
    o(HEADER.rstrip("\n"))
    o(SPREAD_HEADER)
    o("# THIS = a state at its census step (te_demog_step_begin, before te_demog_practices_step): one walk over its")
    o("# neighbouring states with a census, their people (millions) into te_dg_pr_nb_p and each practice's people-weighted")
    o("# sum into te_dg_pr_nb_<P>, which te_demog_practice_step reads (demographics_model.practice_drift's neighbours). The")
    o("# late-marriage spec 4.4: a state closes PRACTICE_SPREAD of the gap to its neighbours' mean each step, both ways.")
    o("te_demog_practices_neighbours = {")
    o("set_local_variable = { name = te_dg_pr_nb_p value = 0 }")
    for p in P.PRACTICES:
        o(f"set_local_variable = {{ name = te_dg_pr_nb_{p} value = 0 }}")
    o("every_neighbouring_state = {")
    o("limit = {")
    for p in P.PRACTICES:
        o(f"has_variable = te_dg_pr_{p}")
    o("}")
    o("change_local_variable = { name = te_dg_pr_nb_p add = { value = state_population divide = 1000000 } }")
    for p in P.PRACTICES:
        o(f"change_local_variable = {{ name = te_dg_pr_nb_{p} add = {{ value = var:te_dg_pr_{p} "
          "multiply = state_population divide = 1000000 } }")
    o("}")
    o("}")
    o("")
    return o.text()


def plan_outputs(root=ROOT):
    # phase 3, the late game: its own two generated files (scripts/generators/gen_demographics_lx.py)
    import gen_demographics_lx as LX
    # Internal Resettlement's known moves and the US frontier's 1836 seed (scripts/generators/gen_demographics_resettle.py)
    import gen_demographics_resettle as RSG
    import gen_demographics_um as UM     # uploaded minds (2026-10-19): its own two generated files
    return {EFFECTS: render_effects(root), VALUES: render_values(root), LINE_MODIFIERS: render_line_modifiers(),
            LINE_VALUES: render_line_values(), LINE_EFFECTS: render_line_effects(),
            WORKFORCE_LINE_MODIFIERS: render_workforce_line_modifiers(),
            WORKFORCE_LINE_VALUES: render_workforce_line_values(),
            WORKFORCE_LINE_EFFECTS: render_workforce_line_effects(),
            SPREAD_VALUES: render_spread_values(), SPREAD_EFFECTS: render_spread_effects(),
            **LX.plan_outputs(), **RSG.plan_outputs(), **UM.plan_outputs()}


def regenerate(root=ROOT, dry_run=False):
    changed = []
    for rel, text in plan_outputs(root).items():
        target = root / rel
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(rel))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a committed file is stale")
    args = ap.parse_args(argv)
    result = regenerate(dry_run=args.check)
    for rel in result["changed_files"]:
        print(("stale: " if args.check else "wrote: ") + rel)
    return 1 if (args.check and result["changed"]) else 0


if __name__ == "__main__":
    sys.exit(main())
