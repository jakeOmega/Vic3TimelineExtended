#!/usr/bin/env python3
"""Offline harness for the demographics model (spec §11.1, §12 phase 0).

Usage:
    demographics_harness.py sketch                      # §2.2/§2.3's cases from the model
    demographics_harness.py inputs SAVE [--tag GBR]     # per-country inputs read from a save
    demographics_harness.py gini SAVE [--tag GBR] [--shift N]   # the panel's Gini, the bands' and pop by pop
    demographics_harness.py seed SAVE --tag GBR         # the seeded structure and life figures
    demographics_harness.py natural-change OLD NEW      # §14 Q10: world change vs the SoL curves
    demographics_harness.py replay DEBUG_LOG            # an in-game step against the model
    demographics_harness.py wc SAVE [--tag GBR] [--top 30]  # Wealth Concentration as the game holds it
    demographics_harness.py medicine                    # mortality anchors with the game files' values
    demographics_harness.py lag                         # years of e0 behind the target while medicine spreads
    demographics_harness.py adopters SAVE [SAVE ...]    # health-law adopters against peers at their SoL
    demographics_harness.py fertility                   # children per woman with the game files' values
    demographics_harness.py workforce                   # phase 2 step 1: participation, need, the old-age threshold
    demographics_harness.py consequences [SAVE...] [--sex-effects]  # phase 2 step 4: conscription, youth, sex balance
    demographics_harness.py history SAVE... --anchors CSV  # the model against history's e0, IMR and growth
    demographics_harness.py fidelity SAVE [--tag GBR]   # the model against the census's own stored multipliers
    demographics_harness.py predict SAVE... [--census-rates] [--slope] [--to-year 1900] [--check-modifiers] [--json]
                                                        # the engine's growth once the census sets its rates

SAVE is a plain-text save (debug mode; a binary or zipped one is refused with exit 1).
The model is demographics_model.py with demographics_params.py; the generator writes the
script from the same two files, so a parameter tuned here reaches the game by
`python3 scripts/generators/gen_demographics.py`.

Calibration to world history (§2.3's targets) is not here yet: it needs an observer
run's yearly saves and belongs to phase 2's plan.
"""

import argparse
import collections
import dataclasses
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_regions as R  # noqa: E402
import demographics_save_inputs as S  # noqa: E402
import pop_growth as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BUY_PACKAGES = ROOT / "common" / "buy_packages" / "00_buy_packages.txt"

SKETCH = {
    "1836 agrarian (reference)": M.Inputs(sol=8, literacy=0.2, urban_share=0.1),
    "Britain 1836": M.Inputs(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"})),
    "France 1836 (Family Limitation)": M.Inputs(sol=11, literacy=0.3, urban_share=0.15,
                                                means_add=P.FAMILY_LIMITATION_MEANS),
}


def buy_package_costs(path=BUY_PACKAGES):
    """{wealth: weekly spending per 10,000 working adults} from the committed buy packages."""
    text = Path(path).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"^wealth_(\d+) = \{(.*?)^\}", text, re.S | re.M):
        goods = re.search(r"goods = \{[^\n]*\n(.*?)\n\t\}", m.group(2), re.S)
        out[int(m.group(1))] = sum(float(v) for v in re.findall(r"= ([0-9.]+)", goods.group(1)))
    return out


def income_proxy(wealth, costs):
    """Spending per head at a pop's wealth, the package's own figure at each level (no line between
    knots), uncapped up to the top level: each pop as its own group, the Gini's reference."""
    w = min(max(int(wealth), 1), P.GINI_TOP_WEALTH)
    return costs[w]


def inputs_for(c, carriers=None, incorporated=True, practices=None):
    """Model inputs for a save's country (as its incorporated states see them) or for one state
    (demographics_save_inputs.state_inputs; incorporated as the state is).

    The modifier totals come from the game files' carriers (demographics_modifiers) for the
    owner's techs, laws and institution levels. The wealth term is the pop-weighted curve,
    as the game computes it, not the curve at the mean SoL. Crowding (the state's migration penalty
    from migration_crowding) is a state's; a whole country's is 0, so `seed` and `adopters` leave it out.
    practices: {practice: share} (Late Marriage lm, Birth Spacing bs; the late-marriage plan), none by default.
    """
    carriers = DM.load_carriers() if carriers is None else carriers
    mods = DM.totals(carriers, c.techs, c.laws, c.institutions, incorporated=incorporated)
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share, techs=frozenset(c.techs),
                    laws=frozenset(c.laws), institutions=dict(c.institutions), wealth_tfr=c.wealth_tfr,
                    mods=mods, means_add=c.means_add, crowding=c.crowding, practices=dict(practices or {}))


def cmd_sketch(_args):
    for label, inp in SKETCH.items():
        ring, last = M.run_constant(inp, years=300)
        s = M.structure(ring)
        print(f"{label:28s} TFR {last['tfr']:.2f}  e0 {last['e0']:.1f}  e65 {last['e65']:.1f}  "
              f"IMR {last['q0_per_1000']:.0f}  0-14 {s['young']:.0%}  15-64 {s['working']:.0%}  "
              f"65+ {s['old']:.1%}  growth {last['growth']:+.2%}")
    return 0


def country_pops(sections, tag, costs, shift=0):
    """[(people, wealth, strata, income)] for one country's pops, from raw pop records; `shift` adds
    that many wealth levels to every pop (between 0 and the top level), a synthetic late game."""
    tags = {cid: r.get("definition", "").strip('"') for cid, r in sections["country_manager"].items()}
    owner = {sid: r.get("country") for sid, r in sections["states"].items()}
    out = []
    for r in sections["pops"].values():
        if tags.get(owner.get(r.get("location"))) != tag:
            continue
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        if size <= 0:
            continue
        wealth = min(max(S._num(r.get("wealth"), 1) + shift, 0), P.GINI_TOP_WEALTH)
        strata = S.STRATA_OF_CLASS.get(r.get("social_class"), "lower")
        out.append((size, wealth, strata, size * income_proxy(wealth, costs)))
    return out


def grouped_by(pops, key):
    """[(people, income)] summed over the pops sharing key(pop)."""
    acc = {}
    for pop in pops:
        n, y = acc.get(key(pop), (0.0, 0.0))
        acc[key(pop)] = (n + pop[0], y + pop[3])
    return list(acc.values())


def cmd_gini(args):
    """The panel's Gini per country (§4.1: 1 - X (1 - the wealth bands' Gini)), then the bands' own figure,
    each pop as its own group and the three strata the census used before 2026-10-10 (all computed).
    --shift N makes every pop N wealth levels richer: a late game no save has yet."""
    sections = S.read_sections(args.save)
    costs = buy_package_costs()
    inputs = S.country_inputs(sections)
    tags = args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]
    if args.shift:
        print(f"every pop {args.shift:+d} wealth levels (between 0 and {P.GINI_TOP_WEALTH})")
    out = 0
    for t in tags:
        pops = country_pops(sections, t, costs, shift=args.shift)
        if not pops:
            print(f"no pops for {t} in {args.save}", file=sys.stderr)
            out = 1
            continue
        bands = M.grouped_gini(grouped_by(pops, lambda p: M.wealth_band(p[1])))
        each = M.grouped_gini([(p[0], p[3]) for p in pops])
        strata = M.grouped_gini(grouped_by(pops, lambda p: p[2]))
        print(f"{t:4s} shown {M.shown_gini(bands):.3f}  bands {bands:.3f}  pop by pop {each:.3f}  strata {strata:.3f}")
    return out


def cmd_inputs(args):
    return S.main(["summary", args.save] + [x for t in args.tag for x in ("--tag", t)])


def cmd_seed(args):
    c = S.country_inputs(S.read_sections(args.save)).get(args.tag)
    if c is None:
        print(f"no country {args.tag}", file=sys.stderr)
        return 1
    inp = inputs_for(c)
    ring = M.seed(inp, 1836, c.population)
    qf, qm, _ = M.group_rates(inp)
    f, m = M.life_table(qf), M.life_table(qm)
    fert = M.fertility(inp, (f["e0"] + m["e0"]) / 2)
    s = M.structure(ring)
    print(f"{args.tag}: pop {c.population:,.0f} SoL {c.sol:.1f} literacy {c.literacy:.2f} urban {c.urban_share:.2f}")
    print(f"  TFR {fert['tfr']:.2f} (wealth {fert['wealth']:.2f} x factor {fert['factor']:.2f}; means {fert['means']:.2f})")
    print(f"  e0 women {f['e0']:.1f} men {m['e0']:.1f}; IMR {(qf[0] + qm[0]) / 200:.0f} per 1000")
    print(f"  0-14 {s['young']:.0%} 15-64 {s['working']:.0%} 65+ {s['old']:.1%} median {s['median']:.1f}")
    return 0


def cmd_natural_change(args):
    """World population change between two saves against the defines' curves (no modifiers)."""
    d = G.read_defines()
    old, new = S.read_sections(args.old, ("pops",)), S.read_sections(args.new, ("pops",))
    total_old = total_new = expected = 0.0
    for r in old["pops"].values():
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        sol = S._num(r.get("previous_quality_of_life"))
        total_old += size
        expected += size * (G.monthly_birthrate(sol, d) - G.monthly_mortality(sol, d))
    for r in new["pops"].values():
        total_new += S._num(r.get("workforce")) + S._num(r.get("dependents"))
    months = args.months
    print(f"world {total_old:,.0f} -> {total_new:,.0f}: change {total_new - total_old:+,.0f} over {months} month(s)")
    print(f"expected from the curves without modifiers: {expected * months:+,.0f} "
          f"(ratio {((total_new - total_old) / (expected * months)) if expected else 0:.2f})")
    return 0


_REPLAY = re.compile(r"TE_DEMOG_REPLAY (\w+) (.*)$")
DEFAULT_TOLERANCE = 0.001   # a fraction of the slot; a correct step's noise measured 0.01% at 2 million people
PRINT_STEP = 1e-5           # per mille: _fmt prints each slot to five decimals
BEFORE_SUM_TOLERANCE = 0.01  # the before-state's slots and pool must sum to 1000 per mille within this
HEAD_PEOPLE = ("pop_last", "pop", "war", "kills", "mig")
HEAD_RATES = ("tfr", "mmr", "m_inf", "m_ext", "m_chr", "m_work_f", "m_work_m")


def _fmt(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") if x else "0"


def _grouped(x):
    """millions_thousands_units: the demographics probe's register form for a people count, which the
    console's lines keep (te_debug_demog_values.txt). The debug log itself prints a large number in
    full with |0 (the probe's own line: raw=123456789); the groups stay because both sides use them."""
    sign = "-" if x < 0 else ""
    n = int(round(abs(x)))
    return f"{sign}{n // 1_000_000}_{n // 1000 % 1000}_{n % 1000}"


def _group_part(text):
    """One group of a grouped number: an int, or a float when the units part carries a fraction."""
    if not text:
        return 0
    return float(text) if "." in text else int(text)


def _ungroup(text):
    """The number a grouped one stands for; a fractional units part (`0_0_500.5`) is kept."""
    sign = -1 if text.startswith("-") else 1
    parts = [_group_part(p) for p in text.lstrip("-").split("_")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return sign * (parts[0] * 1_000_000 + parts[1] * 1000 + parts[2])


def _per_mille(ring):
    total = ring.people() or 1.0
    k = 1000.0 * ring.scale / total
    return [x * k for x in ring.f], [x * k for x in ring.m], (ring.pool_f * k, ring.pool_m * k)


def format_replay(state, year, ring_before, head, ring_after):
    """The TE_DEMOG_REPLAY lines one in-game step logs (te_debug_demog.1 option a).

    People counts print as millions_thousands_units groups (_grouped: the probe's register
    convention, kept because the script and this parser both use it; the debug log does not
    abbreviate large numbers, it printed raw=123456789 in full) and every slot as per mille of
    the state's people.
    head: pop (engine, now), war, kills, mig (signed), tfr, mmr, m_inf, m_ext, m_chr,
    m_work_f, m_work_m, profile (10 shares: classes 0-4 women, then men). pop_last is the
    ring's people before the step. Then fifteen `before` and fifteen `after` lines of ten
    slots each; the slot-0 line also carries the pool and its mean age.
    """
    n = len(P.MIGRANT_CLASSES)
    h = dict(head, pop_last=ring_before.people())
    prof = ",".join(_fmt(head["profile"][(c, s)]) for s in ("f", "m") for c in range(n))
    lines = [f"TE_DEMOG_REPLAY head state={state} year={year} "
             + " ".join(f"{k}={_grouped(h[k])}" for k in HEAD_PEOPLE) + " "
             + " ".join(f"{k}={_fmt(h[k])}" for k in HEAD_RATES) + f" profile={prof}"]
    for when, ring in (("before", ring_before), ("after", ring_after)):
        f, m, (pf, pm) = _per_mille(ring)
        for first in range(0, P.RING_YEARS, 10):
            extra = f" pool_f={_fmt(pf)} pool_m={_fmt(pm)} pool_age={_fmt(ring.pool_age)}" if first == 0 else ""
            lines.append(f"TE_DEMOG_REPLAY {when} from={first} f={','.join(_fmt(x) for x in f[first:first + 10])}"
                         f" m={','.join(_fmt(x) for x in m[first:first + 10])}{extra}")
    return lines


def parse_replay(lines):
    """[{'head': {...}, 'before': {...}, 'after': {...}, 'errors': [...]}] from TE_DEMOG_REPLAY lines.

    A line that can't be read doesn't stop the parse: it is noted in the block's `errors`,
    and check_block reports the block as malformed.
    """
    blocks, cur = [], None
    for line in lines:
        hit = _REPLAY.search(line)
        if not hit:
            continue
        kind, rest = hit.group(1), hit.group(2)
        fields = dict(kv.split("=", 1) for kv in rest.split() if "=" in kv)
        if kind == "head":
            cur = {"head": fields, "before": {"f": {}, "m": {}}, "after": {"f": {}, "m": {}}, "errors": []}
            blocks.append(cur)
        elif cur is not None and kind in ("before", "after"):
            try:
                first = int(fields["from"])
                for sex in ("f", "m"):
                    for i, v in enumerate(fields[sex].split(",")):
                        cur[kind][sex][first + i] = float(v or 0)
                if "pool_f" in fields:
                    cur[kind]["pool"] = (float(fields["pool_f"] or 0), float(fields["pool_m"] or 0),
                                         float(fields["pool_age"] or 150))
            except (KeyError, ValueError) as e:
                cur["errors"].append(f"unreadable {kind} line (from={fields.get('from', '?')}): {type(e).__name__} {e}")
    return blocks


def check_block(b):
    """None for a block replay_block can run; otherwise why not, as `malformed: …` or `incomplete: …`.

    A complete block has every head field, all RING_YEARS slots of each sex in both `before`
    and `after`, and the pool (slot-0 line) in both. replay_block compares only the slots it
    is given, so without this a log cut short would pass. A complete block's before-state
    (both sexes' slots plus the pool) must also sum to 1000 per mille within
    BEFORE_SUM_TOLERANCE: replay_block scales whatever it is given to the state's population,
    so a before-state that is short of 1000 would otherwise replay as if it were whole.
    """
    if b.get("errors"):
        return "malformed: " + b["errors"][0]
    h = b["head"]
    missing = [k for k in ("year",) + HEAD_PEOPLE + HEAD_RATES + ("profile",) if k not in h]
    if missing:
        return "malformed: head lacks " + ", ".join(missing)
    try:
        int(h["year"])
        for k in HEAD_PEOPLE:
            _ungroup(h[k])
        for k in HEAD_RATES:
            float(h[k])
        shares = [float(x) for x in h["profile"].split(",")]
    except ValueError as e:
        return f"malformed: head value unreadable ({e})"
    want = 2 * len(P.MIGRANT_CLASSES)
    if len(shares) != want:
        return f"malformed: profile has {len(shares)} shares, expected {want}"
    gaps = []
    for when in ("before", "after"):
        for sex, who in (("f", "women"), ("m", "men")):
            slots = b[when][sex]
            if any(not 0 <= k < P.RING_YEARS for k in slots):
                return f"malformed: {when} {who} has a slot outside 0-{P.RING_YEARS - 1}"
            if len(slots) < P.RING_YEARS:
                gaps.append(f"{when} {who} {len(slots)} of {P.RING_YEARS} slots")
        if "pool" not in b[when]:
            gaps.append(f"{when} pool missing")
    if gaps:
        return "incomplete: " + "; ".join(gaps)
    total = sum(sum(b["before"][sex].values()) for sex in ("f", "m")) + b["before"]["pool"][0] + b["before"]["pool"][1]
    if abs(total - 1000.0) > 1000.0 * BEFORE_SUM_TOLERANCE:
        return f"malformed: before-state sums to {total:.0f}\u2030"
    return None


def replay_block(b):
    """Step the model from a logged before-state; the worst relative error over the slots that hold a person.

    A slot is compared when either side holds at least one person (its per mille times the
    state's people after the step). The game drops a cohort under half a person, so a smaller
    one reads 0 on one side and a few thousandths on the other, which a per-mille cutoff
    would compare as 100% off in a state of a few thousand people. The log prints each slot to
    PRINT_STEP per mille and the before-state arrives rounded the same way, so a difference up
    to one PRINT_STEP is the log's resolution and is not counted: without that, a correct step
    shows 0.5% at a slot of 1.5 people in a 2-million-person state.
    """
    h = b["head"]
    year = int(h["year"])
    pop_last = _ungroup(h["pop_last"])
    ring = M.Ring(year=year - 1)
    for k in range(P.RING_YEARS):
        ring.f[k] = b["before"]["f"].get(k, 0.0) * pop_last / 1000.0
        ring.m[k] = b["before"]["m"].get(k, 0.0) * pop_last / 1000.0
    pf, pm, page = b["before"].get("pool", (0.0, 0.0, 150.0))
    ring.pool_f, ring.pool_m, ring.pool_age = pf * pop_last / 1000.0, pm * pop_last / 1000.0, page
    M._refresh_denominators(ring)
    ring.total = ring.people()
    mult = {"infection": float(h["m_inf"]), "external": float(h["m_ext"]), "chronic": float(h["m_chr"])}
    qf, qm = M.rates_from_multipliers(mult, float(h["m_work_f"]), float(h["m_work_m"]))
    shares = [float(x) for x in h["profile"].split(",")]
    n = len(P.MIGRANT_CLASSES)
    prof = {(c, "f"): shares[c] for c in range(n)} | {(c, "m"): shares[n + c] for c in range(n)}
    M.step(ring, M.Inputs(), year, engine_pop=_ungroup(h["pop"]), war_dead=_ungroup(h["war"]),
           kills=_ungroup(h["kills"]), migration=_ungroup(h["mig"]),
           rates=(qf, qm, float(h["mmr"]), float(h["tfr"]), prof))
    mine_f, mine_m, _pool = _per_mille(ring)
    people_per_mille = ring.people() / 1000.0
    worst = 0.0
    for sex, mine in (("f", mine_f), ("m", mine_m)):
        for k, logged in b["after"][sex].items():
            big = max(mine[k], logged)
            if big * people_per_mille < 1.0:
                continue
            worst = max(worst, max(0.0, abs(mine[k] - logged) - PRINT_STEP) / big)
    return worst


def cmd_replay(args):
    """Step the model from each logged before-state and compare it with the logged after-state.

    Exit 1 if any block is malformed or incomplete (a missing line, a before-state that does not
    sum to 1000 per mille) or has a slot off by more than --tolerance, a fraction of that slot
    (default DEFAULT_TOLERANCE, 0.1%: a correct step measured 0.01% at a 2-million-person state,
    a step without maternal deaths 0.16%).

    What stays below detection: the order of deaths and flows within the step (the pre-/post-death
    ordering), and flows under about 1% of the cohorts they touch, move a slot by less than the
    tolerance. The script's registry tests are the check on those lines, not this. The default
    may need resetting from the first real in-game log. A state of a few thousand people reads a
    systematic offset (about 0.1% at 3,000) if the script scales the survivors back up to the
    state's population after dropping its sub-half-person cohorts; raise --tolerance for those.
    """
    lines = Path(args.log).read_text(encoding="utf-8", errors="replace").splitlines()
    blocks = parse_replay(lines)
    if not blocks:
        print("no TE_DEMOG_REPLAY blocks", file=sys.stderr)
        return 1
    bad = 0
    for b in blocks:
        label = f"{b['head'].get('state', '?')} {b['head'].get('year', '?')}"
        problem, worst = check_block(b), 0.0
        if problem is None:
            try:
                worst = replay_block(b)
            except (ArithmeticError, KeyError, IndexError, TypeError, ValueError) as e:
                problem = f"malformed: {type(e).__name__} {e}"
        if problem:
            bad += 1
            print(f"{label}: MISMATCH ({problem})")
            continue
        flag = "OK" if worst <= args.tolerance else "MISMATCH"
        bad += flag != "OK"
        print(f"{label}: worst slot error {worst:.2%} {flag}")
    return 1 if bad else 0


WC_COUNTRY_VARS = ("te_inh_concentration", "te_dg_wc_target", "te_dg_wc_t_law", "te_dg_wc_t_land", "te_dg_wc_t_own",
                   "te_dg_wc_t_ineq", "te_dg_wc_t_tax", "te_dg_wc_t_econ", "te_inh_great_fortunes_mult",
                   "te_inh_dispersed_mult")
WC_STATE_VARS = ("te_dg_wc", "te_dg_walk_pop")
INHERITANCE_LAWS = ("law_primogeniture", "law_free_testation", "law_partible", "law_equal_inheritance",
                    "law_state_universal_heir", "law_non_inheritable_usage_rights")


def wc_rows(countries, states):
    """[(tag, people, country vars, state scores, inheritance law)] for every country with a national
    figure, the most people first."""
    scores, people = {}, {}
    for st in states.values():
        if "te_dg_wc" in st["vars"]:
            scores.setdefault(st["owner"], []).append(st["vars"]["te_dg_wc"])
            people[st["owner"]] = people.get(st["owner"], 0.0) + st["vars"].get("te_dg_walk_pop", 0.0)
    rows = []
    for cid, c in countries.items():
        if "te_inh_concentration" not in c["vars"]:
            continue
        law = next((x for x in INHERITANCE_LAWS if x in c["laws"]), "-")
        rows.append((c["tag"] or cid, people.get(cid, 0.0), c["vars"], scores.get(cid, []), law))
    return sorted(rows, key=lambda r: -r[1])


def cmd_wc(args):
    """Each country's national figure, the target's terms and modifier multipliers, and its states'
    range, read from the save's script variables (spec 4.2). A balance pass's in-game check."""
    rows = wc_rows(*S.read_variables(args.save, WC_COUNTRY_VARS, WC_STATE_VARS))
    if args.tag:
        rows = [r for r in rows if r[0] in args.tag]
    terms = ("law", "land", "own", "ineq", "tax", "econ")
    print(f"{'tag':5s} {'M ppl':>6s} {'WC':>5s} {'target':>6s} " + " ".join(f"{t:>5s}" for t in terms)
          + "    GF    DW  states>50  range   inheritance")
    for tag, ppl, v, wcs, law in rows[:args.top]:
        print(f"{tag:5s} {ppl / 1e6:6.1f} {v['te_inh_concentration']:5.1f} {v.get('te_dg_wc_target', 0):6.1f} "
              + " ".join(f"{v.get('te_dg_wc_t_' + t, 0):+5.1f}" for t in terms)
              + f" {v.get('te_inh_great_fortunes_mult', 0):5.2f} {v.get('te_inh_dispersed_mult', 0):5.2f}"
              f"  {sum(w > 50 for w in wcs):4d}/{len(wcs):<4d} {min(wcs, default=0):3.0f}-{max(wcs, default=0):<3.0f}"
              f" {law.replace('law_', '')}")
    by_law = {}
    for tag, ppl, v, wcs, law in rows:
        by_law.setdefault(law, []).append((ppl, v["te_inh_concentration"]))
    for law, xs in sorted(by_law.items(), key=lambda kv: -len(kv[1])):
        weight = sum(p for p, _ in xs)
        mean = sum(p * w for p, w in xs) / weight if weight else 0.0
        median = sorted(w for _, w in xs)[len(xs) // 2]
        print(f"{law.replace('law_', ''):32s} countries {len(xs):3d}  above 50 {sum(w > 50 for _, w in xs):3d}  "
              f"median {median:5.1f}  weighted by people {mean:5.1f}")
    return 0


# ---- medicine: mortality anchors (modifier-types design, stage 1) -----------------------
# The medical techs by when the West held them (eras: medical_degrees 1, pharmaceuticals 2,
# modern_nursing 3, antibiotics 5, modern_vaccines 6, antibiotic_mass_production 7,
# modern_pharmaceuticals 8, telemedicine 10).
MED_1836 = frozenset({"medical_degrees"})
MED_1900 = MED_1836 | {"pharmaceuticals", "modern_nursing"}
MED_1950 = MED_1900 | {"antibiotics", "modern_vaccines", "combustion_engine"}
MED_1990 = MED_1950 | {"antibiotic_mass_production", "modern_pharmaceuticals"}
MED_TODAY = MED_1990 | {"telemedicine"}
CHS, PHI = "law_charitable_health_system", "law_public_health_insurance"
HEALTH = "institution_health_system"

# The Ministry of Health's top level comes from technology alone (medical_degrees, pharmaceuticals,
# quinine, malaria_prevention, antibiotics in the base game; modern_pharmaceuticals, mrna_therapeutics,
# telemedicine, personalized_medicine in the mod): 1 in 1836, 4-5 by 1900, 5 by 1950, 6 at era 8, 8 at
# era 10 and 9 at era 11. The scenarios put a country that invests fully near its era's top.
RICH_TODAY = dict(sol=40, literacy=0.99, urban_share=0.8, techs=MED_TODAY,
                  laws=frozenset({PHI, "law_old_age_pension", "law_dedicated_police", "law_worker_protections"}),
                  institutions={HEALTH: 8, "institution_workplace_safety": 5,
                                "institution_ministry_of_consumer_protection": 4})
# (label, inputs, {figure: (low, high)}): §2.4's anchors and the history behind them. Figures:
# e0 and e65 in years, imr per 1,000 births, mmr maternal deaths per 100,000 births.
MEDICINE_SCENARIOS = [
    ("Britain 1836", dict(sol=11, literacy=0.35, urban_share=0.3, techs=MED_1836, laws={CHS},
                          institutions={HEALTH: 1}),
     {"imr": (150, 250), "e0": (35, 43), "e65": (10, 14), "mmr": (400, 1000)}),
    ("Britain 1900", dict(sol=16, literacy=0.75, urban_share=0.6, techs=MED_1900, laws={CHS},
                          institutions={HEALTH: 4}),
     {"imr": (120, 170), "e0": (44, 52)}),
    ("West 1950", dict(sol=25, literacy=0.95, urban_share=0.65, techs=MED_1950,
                       laws={PHI, "law_dedicated_police", "law_regulatory_bodies"},
                       institutions={HEALTH: 5, "institution_workplace_safety": 2}),
     # e0 from 60: the model's deaths at 20-50 run three to four times Britain's in 1950 (the
     # base schedules, phase 2's calibration; e65 already meets Britain's 13.9), not medicine
     {"imr": (20, 55), "e0": (60, 71), "e65": (12, 16), "mmr": (30, 150)}),
    ("West 1990", dict(sol=38, literacy=0.98, urban_share=0.75, techs=MED_1990,
                       laws={PHI, "law_old_age_pension", "law_dedicated_police", "law_worker_protections"},
                       institutions={HEALTH: 6, "institution_workplace_safety": 4,
                                     "institution_ministry_of_consumer_protection": 3}),
     {"imr": (0, 12), "e0": (72, 80), "e65": (15, 20), "mmr": (0, 25)}),
    ("Rich today", RICH_TODAY, {"imr": (0, 6), "e0": (77, 84), "e65": (18, 23), "mmr": (0, 15)}),
    ("India 1975", dict(sol=9, literacy=0.35, urban_share=0.2, techs=MED_1950, laws={CHS},
                        institutions={HEALTH: 1}),
     {"imr": (110, 150), "e0": (46, 56)}),
    ("Medicine, no health system", dict(sol=10, literacy=0.3, urban_share=0.15, techs=MED_1990),
     {"imr": (70, 130), "e0": (48, 60)}),
]
# (label, with the law, without it, (low, high) for the gain in e0): a health law before modern
# medicine, at the same SoL and literacy (the spec's stage-1 gate: within about 3 years).
MEDICINE_GAPS = [
    ("Public Health Insurance before antibiotics", dict(sol=12, literacy=0.4, techs=MED_1900, laws={PHI},
                                                         institutions={HEALTH: 3}),
     dict(sol=12, literacy=0.4, techs=MED_1900), (0.5, 3.0)),
    # Augmentation as chronic treatment (phase 2 step 4). The old engine lines on Rich today's inputs: Medical
    # Only's -2% a level at Ministry of Health level 8 gave about +2.8 years, Unrestricted's flat -5% about +0.8,
    # Regulated Market's -2% a level at Consumer Protection level 4 about +1.4 (model, every cause scaled). The
    # bands keep the new lines near those sizes and catch a per-level line (+0.10 a level is +14 years).
    ("Medical Augmentation Only, Rich today", dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_medical_augmentation_only"}),
     RICH_TODAY, (1.5, 3.5)),
    ("Unrestricted Augmentation, Rich today", dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_unrestricted_augmentation"}),
     RICH_TODAY, (0.5, 2.0)),
    ("Regulated Augmentation Market, Rich today",
     dict(RICH_TODAY, laws=RICH_TODAY["laws"] | {"law_regulated_augmentation_market"}), RICH_TODAY, (0.5, 2.0)),
    # Augmentation reaches only as far as health-care access does (owner, 2026-10-10): with no health system the same
    # law gives a fraction of Rich today's gain, where its old flat -5% mortality reached every state alike.
    ("Unrestricted Augmentation, no health system",
     dict(sol=10, literacy=0.3, urban_share=0.15, techs=MED_1990, laws={"law_unrestricted_augmentation"}),
     dict(sol=10, literacy=0.3, urban_share=0.15, techs=MED_1990), (0.0, 0.4)),
]


def life(inp):
    """{e0, e65, imr, mmr}: both sexes' mean, infant deaths per 1,000, maternal per 100,000 births."""
    qf, qm, mmr = M.group_rates(inp)
    f, m = M.life_table(qf), M.life_table(qm)
    return {"e0": (f["e0"] + m["e0"]) / 2, "e65": (f["e65"] + m["e65"]) / 2,
            "imr": (qf[0] + qm[0]) / 200, "mmr": mmr}


def scenario_inputs(carriers, techs=frozenset(), laws=frozenset(), institutions=None, **kw):
    institutions = institutions or {}
    return M.Inputs(techs=frozenset(techs), laws=frozenset(laws), institutions=dict(institutions),
                    mods=DM.totals(carriers, techs, laws, institutions), **kw)


def medicine_rows(carriers=None):
    """[(label, {figure: (value, low, high)})] for MEDICINE_SCENARIOS, then the gaps as 'gap' rows."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, kw, targets in MEDICINE_SCENARIOS:
        got = life(scenario_inputs(carriers, **kw))
        rows.append((label, {k: (got[k], lo, hi) for k, (lo, hi) in targets.items()}))
    for label, with_law, without, (lo, hi) in MEDICINE_GAPS:
        gap = life(scenario_inputs(carriers, **with_law))["e0"] - life(scenario_inputs(carriers, **without))["e0"]
        rows.append((label, {"gap": (gap, lo, hi)}))
    return rows


def cmd_medicine(_args):
    out = 0
    for label, figures in medicine_rows():
        parts = []
        for k, (v, lo, hi) in figures.items():
            ok = lo <= v <= hi
            out |= not ok
            parts.append(f"{k} {v:6.1f} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}")
        print(f"{label:44s} " + "  ".join(parts))
    return out


# ---- lag: how far life expectancy trails its target while medicine spreads (the Causes of Death plan) -------------
# (label, before, after): a state's inputs before a change and after it, the communication techs of the era included
# (they set the spread's rate). At year 0 the change has just happened; each year is one census step.
COMMS_1870 = frozenset({"electric_telegraph"})
COMMS_1950 = COMMS_1870 | {"radio"}
COMMS_TODAY = COMMS_1950 | {"intergovernmental_organizations", "world_wide_web"}
LAG_SCENARIOS = [
    ("1840s: Charitable Health System, Ministry of Health 1 to 3",
     dict(sol=10, literacy=0.25, techs=MED_1836, laws={CHS}, institutions={HEALTH: 1}),
     dict(sol=10, literacy=0.25, techs=MED_1836, laws={CHS}, institutions={HEALTH: 3})),
    ("1870s: Modern Nursing arrives",
     dict(sol=13, literacy=0.5, techs=MED_1836 | {"pharmaceuticals"} | COMMS_1870, laws={CHS}, institutions={HEALTH: 3}),
     dict(sol=13, literacy=0.5, techs=MED_1900 | COMMS_1870, laws={CHS}, institutions={HEALTH: 3})),
    ("1900s: Public Health Insurance at 3, before antibiotics",
     dict(sol=16, literacy=0.75, techs=MED_1900 | COMMS_1870, laws={CHS}, institutions={HEALTH: 3}),
     dict(sol=16, literacy=0.75, techs=MED_1900 | COMMS_1870, laws={PHI}, institutions={HEALTH: 3})),
    # the motor age on both sides: MED_1950 holds combustion_engine, whose accident line is no medicine and doesn't drift
    ("1940s: antibiotics and vaccines arrive",
     dict(sol=22, literacy=0.9, techs=MED_1900 | {"combustion_engine"} | COMMS_1950, laws={PHI}, institutions={HEALTH: 5}),
     dict(sol=22, literacy=0.9, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={HEALTH: 5})),
    ("1950s: a colony incorporated into that health system",
     dict(sol=12, literacy=0.4, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={}),
     dict(sol=12, literacy=0.4, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={HEALTH: 5})),
    ("Today: Telemedicine arrives",
     dict(sol=40, literacy=0.99, techs=MED_1990 | COMMS_TODAY, laws={PHI}, institutions={HEALTH: 8}),
     dict(sol=40, literacy=0.99, techs=MED_TODAY | COMMS_TODAY, laws={PHI}, institutions={HEALTH: 8})),
]
LAG_YEARS = (0, 1, 2, 3, 5, 10, 15, 20)


def lag_rows(carriers=None):
    """[(label, rate, e0 before, e0 at the target, {year: years of e0 behind the target})] for LAG_SCENARIOS: medicine
    starts at the before-inputs' targets and drifts at the after-inputs' rate (demographics_model.medicine_drift);
    SoL, literacy and everything else are the after-inputs' from year 0."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, before, after in LAG_SCENARIOS:
        inp0, inp1 = scenario_inputs(carriers, **before), scenario_inputs(carriers, **after)
        target = life(inp1)["e0"]
        med, behind = M.medicine_targets(inp0), {}
        for year in range(max(LAG_YEARS) + 1):
            if year in LAG_YEARS:
                behind[year] = target - life(dataclasses.replace(inp1, medicine=med))["e0"]
            med = M.medicine_drift(med, inp1)
        rows.append((label, M.diffusion(inp1), life(inp0)["e0"], target, behind))
    return rows


def cmd_lag(_args):
    print("Years of life expectancy behind the target after a change, at the spread's rate (the share of the gap a "
          "census step closes):")
    print(f"{'':56s} rate  e0 before  target  " + "  ".join(f"{y:>4d}y" for y in LAG_YEARS))
    for label, rate, before, target, behind in lag_rows():
        print(f"{label:56s} {rate:4.2f}  {before:9.1f}  {target:6.1f}  "
              + "  ".join(f"{behind[y]:5.2f}" for y in LAG_YEARS))
    return 0


# ---- workforce: phase 2 step 1's participation figures -------------------------------------------------------
# The participation figures at the starting values, on the census's own stable structures (the design §1.8's sketch,
# docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md). (name, Inputs keywords, the lower
# strata's share.) No amendment or IG trait is in these rows: DM.load_carriers walks laws, technologies and
# institutions only (step 2's late-save fit reads those from the save).
_RICH_TECHS = frozenset({"medical_degrees", "modern_nursing", "antibiotics", "modern_vaccines",
                         "antibiotic_mass_production", "contraceptive_pill", "modern_pharmaceuticals",
                         "vulcanization", "feminism", "second_wave_feminism", "personal_appliances"})
WORKFORCE_SCENARIOS = [
    ("1836 farming", dict(sol=8, literacy=0.1, urban_share=0.05,
                          laws=frozenset({"law_no_womens_rights", "law_child_labor_allowed"})), 0.85),
    ("1836 Women in the Fields", dict(sol=8, literacy=0.1, urban_share=0.05,
                                      laws=frozenset({"law_women_in_the_fields", "law_child_labor_allowed"})), 0.85),
    ("Rich, Protected Class, pension at 65", dict(
        sol=40, literacy=0.98, urban_share=0.8, techs=_RICH_TECHS,
        laws=frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                        "law_public_health_insurance"}),
        institutions={"institution_health_system": 5, "institution_social_security": 5}), 0.4),
    ("Rich, plus call 3's laws", dict(
        sol=40, literacy=0.98, urban_share=0.8, techs=_RICH_TECHS,
        laws=frozenset({"law_protected_class", "law_compulsory_primary_school", "law_old_age_pension",
                        "law_public_health_insurance", "law_pro_capital_ministry_of_labor",
                        "law_rehabilitation_focused_criminal_justice"}),
        institutions={"institution_health_system": 5, "institution_social_security": 5,
                      "institution_ministry_of_labor": 5}), 0.4),
]


def workforce_rows():
    """[{name, tfr, women, wa_share, at_work, pensioners, need, target, old_age}] for WORKFORCE_SCENARIOS: each
    scenario's stable structure (300 years at constant inputs), its old-age threshold and its figures."""
    carriers, lines = DM.load_carriers(), DM.workforce_line_carriers()
    rows = []
    for name, kw, low in WORKFORCE_SCENARIOS:
        inp = M.Inputs(low_share=low, **kw)
        inp.mods = {**DM.totals(carriers, inp.techs, inp.laws, inp.institutions),
                    **DM.totals(lines, inp.techs, inp.laws, inp.institutions,
                                types=tuple(P.WORKFORCE_LINE_TYPES.values()))}
        ring, last = M.run_constant(inp, years=300)
        qf, qm, _ = M.group_rates(inp)
        old = M.old_age(qf, qm)
        fig = M.work_figures(ring, inp, old)
        rows.append({"name": name, "tfr": last["tfr"], "women": M.women_rate(inp), **fig,
                     "target": M.wf_target(fig), "old_age": old})
    return rows


def cmd_workforce(_args):
    print(f"{'scenario':40s} {'tfr':>5s} {'women':>6s} {'wa':>6s} {'at work':>8s} {'target':>7s} "
          f"{'pens':>6s} {'need':>6s} {'old age':>8s}")
    for r in workforce_rows():
        print(f"{r['name']:40s} {r['tfr']:5.2f} {r['women']:6.2f} {r['wa_share']:6.3f} {r['at_work']:8.3f} "
              f"{r['target']:7.3f} {r['pensioners']:6.3f} {r['need']:6.3f} {r['old_age']:8.1f}")
    return 0


# ---- consequences: phase 2 step 4's bands (docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md
# §4 and §5) ----------------------------------------------------------------------------------------------------------
# The census's own bands from a save made under Full or Display only (te_dg_b<s><b>), with its people and sex balance.
CENSUS_BAND_VARS = (tuple(f"te_dg_b{s}{b}" for s in "fm" for b in range(P.BANDS))
                    + ("te_dg_people", "te_dg_sex_balance"))
# The model's stable structures (300 years at constant inputs): the 1836 references and today's rich row.
CONSEQ_SCENARIOS = [
    ("1836 agrarian (reference)", dict(sol=8, literacy=0.2, urban_share=0.1), 0.85),
    ("Britain 1836", dict(sol=11, literacy=0.35, urban_share=0.3, laws=frozenset({"law_no_womens_rights"})), 0.8),
    ("India 1975", dict(sol=9, literacy=0.35, urban_share=0.2, techs=MED_1950, laws=frozenset({CHS}),
                        institutions={HEALTH: 1}), 0.85),
] + [(name, kw, low) for name, kw, low in WORKFORCE_SCENARIOS if name.startswith("Rich, Protected")]
# Transitions from the 1836 agrarian stable structure: medicine arrives at year 0 with fertility still high, which
# falls from the year given (the youth bulge's "1950s high-fertility state"; the pool's young state).
CONSEQ_TRANSITIONS = [
    ("1950s medicine, fertility falls slowly from year 15",
     dict(sol=9, literacy=0.3, urban_share=0.15, techs=MED_1950, laws=frozenset({CHS}), institutions={HEALTH: 3}),
     dict(sol=14, literacy=0.6, urban_share=0.35, techs=MED_1950 | {"contraceptive_pill", "vulcanization", "feminism"},
          laws=frozenset({CHS}), institutions={HEALTH: 4}), 15),
    ("1950s medicine, fertility falls fast from year 20",
     dict(sol=12, literacy=0.4, urban_share=0.2, techs=MED_1990, laws=frozenset({PHI}), institutions={HEALTH: 5}),
     dict(sol=30, literacy=0.95, urban_share=0.7, techs=MED_1990 | {"contraceptive_pill", "vulcanization", "feminism"},
          laws=frozenset({PHI}), institutions={HEALTH: 6}), 20),
]
# The sex-balance anchors (the design §4.4): the Soviet Union of 1959 and a frontier state.
SEX_ANCHORS = [("Soviet Union 1959", 82.0, {"births": (0.89, 0.93), "women": (0.07, 0.1)}),
               ("frontier state", 150.0, {"more": (1.0, 1.0)})]
# §5's bands for step 4
BANDS_1836_TERM = 0.05            # the 1836 world's term within +-0.05
BAND_RICH_TERM = (-0.32, -0.18)   # today's rich structure about -0.25
BAND_PEACE_SEX = 0.02             # under 2% of states at either sex-balance effect in a peacetime save
BAND_YOUTH_HALF = 0.05            # under 5% of states above y = 0.5


def census_figures(path):
    """{state id: {owner, people, men, fam, youth, sex_balance}} from a save's census bands (a save made under Full or
    Display only; a state without bands is left out). The pool by bands: before phase 3 its ages are bands 4 to 7."""
    lo, hi = P.POOL_FROM // P.BAND_WIDTH, (P.POOL_TO + 1) // P.BAND_WIDTH
    assert P.POOL_FROM % P.BAND_WIDTH == 0 and (P.POOL_TO + 1) % P.BAND_WIDTH == 0
    ylo, yhi = P.YOUTH_AGES[0] // P.BAND_WIDTH, (P.YOUTH_AGES[1] + 1) // P.BAND_WIDTH
    _countries, states = S.read_variables(path, (), CENSUS_BAND_VARS)
    out = {}
    for sid, st in states.items():
        v = st["vars"]
        if "te_dg_bm0" not in v:
            continue
        people = sum(v.get(f"te_dg_b{s}{b}", 0.0) for s in "fm" for b in range(P.BANDS))
        if people <= 0:
            continue
        out[sid] = {"owner": st["owner"], "people": people,
                    "men": sum(v.get(f"te_dg_bm{b}", 0.0) for b in range(P.BANDS)),
                    "fam": sum(v.get(f"te_dg_bm{b}", 0.0) for b in range(lo, hi)),
                    "youth": sum(v.get(f"te_dg_b{s}{b}", 0.0) for s in "fm" for b in range(ylo, yhi)) / people,
                    "sex_balance": v.get("te_dg_sex_balance")}
    return out


def save_consequences(path, unemployment=True):
    """{year, states, people, pool_share, term_world, term_weighted, big_terms, fewer, more, either, y_any, y_half}: a
    save's census against step 4's bands; with unemployment, each state's from its pops (S.state_unemployment)."""
    figs = census_figures(path)
    idle = S.state_unemployment(S.read_sections(path, wanted=("pops",))) if unemployment else {}
    people = sum(f["people"] for f in figs.values()) or 1.0
    pool = sum(f["fam"] for f in figs.values())
    terms = [(M.conscription_term(f["fam"], f["people"]), f["people"]) for f in figs.values()]
    n = len(figs) or 1
    fewer = sum(1 for f in figs.values() if M.sex_fewer_men(f["sex_balance"]) > 0)
    more = sum(1 for f in figs.values() if M.sex_more_men(f["sex_balance"]) > 0)
    ys = []
    for sid, f in figs.items():
        total, none = idle.get(sid, (0.0, 0.0))
        ys.append(M.youth_bulge(f["youth"], none / total if total else 0.0))
    return {"year": save_year(path), "states": len(figs), "people": people, "pool_share": pool / people,
            "term_world": M.conscription_term(pool, people),
            "term_weighted": sum(t * w for t, w in terms) / people,
            "big_terms": sum(w for t, w in terms if abs(t) > BANDS_1836_TERM) / people,
            "fewer": fewer / n, "more": more / n, "either": (fewer + more) / n,
            "y_any": sum(1 for y in ys if y > 0) / n, "y_half": sum(1 for y in ys if y > 0.5) / n,
            "youth_max": max((f["youth"] for f in figs.values()), default=0.0)}


def consequence_scenarios(carriers=None):
    """[{name, tfr, pool_share, pool_men, term, youth, sex_balance}] on the model's stable structures."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for name, kw, low in CONSEQ_SCENARIOS:
        inp = scenario_inputs(carriers, low_share=low, **kw)
        ring, last = M.run_constant(inp, years=300)
        f = M.consequence_figures(ring)
        rows.append({"name": name, "tfr": last["tfr"], "pool_share": f["pool_share"], "pool_men": f["pool_men_share"],
                     "term": f["term"], "youth": f["youth"], "sex_balance": f["sex_balance"]})
    return rows


def consequence_transitions(carriers=None, years=80, unemployment=0.2):
    """[{name, peak_youth, peak_year, y, peak_term, term_year}]: each transition's highest share aged 20-29, the youth
    bulge there at `unemployment`, and its highest conscription term."""
    carriers = DM.load_carriers() if carriers is None else carriers
    base = scenario_inputs(carriers, sol=8, literacy=0.2, urban_share=0.1)
    rows = []
    for name, early, late, fall in CONSEQ_TRANSITIONS:
        ring, _ = M.run_constant(base, years=300)
        y0 = ring.year
        inp_early, inp_late = scenario_inputs(carriers, **early), scenario_inputs(carriers, **late)
        peak, term = (0.0, 0), (-9.0, 0)
        for t in range(1, years + 1):
            M.step(ring, inp_early if t < fall else inp_late, y0 + t)
            f = M.consequence_figures(ring)
            if f["youth"] > peak[0]:
                peak = (f["youth"], t)
            if f["term"] > term[0]:
                term = (f["term"], t)
        rows.append({"name": name, "peak_youth": peak[0], "peak_year": peak[1],
                     "y": M.youth_bulge(peak[0], unemployment), "peak_term": term[0], "term_year": term[1]})
    return rows


def sex_anchor_rows():
    """[(name, balance, {births, women, fewer, more}, bands)] for SEX_ANCHORS."""
    return [(name, b, {"births": M.sex_births(b), "women": M.sex_women_add(b), "fewer": M.sex_fewer_men(b),
                       "more": M.sex_more_men(b)}, bands) for name, b, bands in SEX_ANCHORS]


def _band(value, lo, hi):
    return "ok" if lo - 1e-9 <= value <= hi + 1e-9 else "OUT"


def cmd_consequences(args):
    """The bands. The sex balance's effects are held back (P.SEX_BALANCE_EFFECTS off): --sex-effects judges its band and
    anchors as if they were on, for the follow-up on the census's migrant profile."""
    kept = P.SEX_BALANCE_EFFECTS
    P.SEX_BALANCE_EFFECTS = kept or args.sex_effects
    try:
        return _consequences(args)
    finally:
        P.SEX_BALANCE_EFFECTS = kept


def _consequences(args):
    out = 0
    sex_on = P.SEX_BALANCE_EFFECTS
    print("Phase 2 step 4 (the consequences design §5): CONSCRIPTION_REF "
          f"{P.CONSCRIPTION_REF}, youth {P.YOUTH_FROM}/{P.YOUTH_SPAN}/{P.YOUTH_UNEMPLOYMENT_FULL}, sex balance from "
          f"{P.SEX_FEWER_FROM:.0f} (full {P.SEX_FEWER_FULL:.0f}) and {P.SEX_MORE_FROM:.0f} (full {P.SEX_MORE_FULL:.0f})")
    print("\nThe model's stable structures:")
    for r in consequence_scenarios():
        print(f"  {r['name']:42s} tfr {r['tfr']:4.2f}  pool {r['pool_share']:.4f} of people, {r['pool_men']:.3f} of men  "
              f"T {r['term']:+.3f}  20-29 {r['youth']:.3f}  men/100 women {r['sex_balance']:5.1f}")
        if r["name"].startswith("Rich"):
            verdict = _band(r["term"], *BAND_RICH_TERM)
            print(f"    today's rich structure: T {r['term']:+.3f} against {BAND_RICH_TERM} (about -0.25): {verdict}")
            out |= verdict != "ok"
    print("\nTransitions from the 1836 stable structure (youth bulge at 20% unemployment):")
    for r in consequence_transitions():
        print(f"  {r['name']:52s} peak 20-29 {r['peak_youth']:.3f} (year {r['peak_year']}), y {r['y']:.2f}; "
              f"peak T {r['peak_term']:+.3f} (year {r['term_year']})")
    print("\nSex balance anchors:" if sex_on else
          "\nSex balance: its effects are held back (demographics_params.SEX_BALANCE_EFFECTS); --sex-effects judges them")
    for name, b, got, bands in (sex_anchor_rows() if sex_on else ()):
        checks = "  ".join(f"{k} {got[k]:.3f} [{lo}-{hi}] {_band(got[k], lo, hi)}" for k, (lo, hi) in bands.items())
        out |= any(_band(got[k], lo, hi) != "ok" for k, (lo, hi) in bands.items())
        print(f"  {name:20s} {b:5.1f} men per 100 women: {checks}")
    for i, path in enumerate(args.saves):
        r = save_consequences(path, unemployment=not args.no_unemployment)
        print(f"\n{path} ({r['year']}): {r['states']} census states, {r['people'] / 1e6:.0f}M people")
        if r["states"] == 0:
            print("  no census bands (not a Full or Display only save)")
            continue
        print(f"  pool {r['pool_share']:.4f} of people: world T {r['term_world']:+.3f}, people-weighted states' T "
              f"{r['term_weighted']:+.3f}, people in states past +-{BANDS_1836_TERM}: {r['big_terms']:.1%}")
        if i == 0:
            verdict = _band(r["term_world"], -BANDS_1836_TERM, BANDS_1836_TERM)
            print(f"  the first save's world term within +-{BANDS_1836_TERM} (1836 world 0 +- 0.05): {verdict}")
            out |= verdict != "ok"
        if sex_on:
            print(f"  sex balance: {r['fewer']:.1%} of states below {P.SEX_FEWER_FROM:.0f}, {r['more']:.1%} at "
                  f"{P.SEX_MORE_FROM:.0f} or more ({r['either']:.1%} at either; band under {BAND_PEACE_SEX:.0%} in "
                  f"peace: {'ok' if r['either'] < BAND_PEACE_SEX else 'OUT'})")
        print(f"  youth: highest share aged 20-29 {r['youth_max']:.3f}; states with a bulge {r['y_any']:.1%}, above "
              f"y = 0.5 {r['y_half']:.1%} (band under {BAND_YOUTH_HALF:.0%}: "
              f"{'ok' if r['y_half'] < BAND_YOUTH_HALF else 'OUT'})")
    return out


# ---- fertility: children per woman (modifier-types design, stage 2) -----------------------------
# (label, inputs, (low, high)): §2.3's sketch table and history. The 1836 rows hold no means tech, so
# only the traditional means and literacy reach them; France's engine cut from Forced Heirship is
# not in the model, so its band is wide.
MEANS_TECHS = {"vulcanization", "feminism"}
FERTILITY_SCENARIOS = [
    ("1836 agrarian (reference)", dict(sol=8, literacy=0.2, urban_share=0.1), (4.8, 6.2)),
    ("Britain 1836", dict(sol=11, literacy=0.35, urban_share=0.3, techs=MED_1836, laws={CHS},
                          institutions={HEALTH: 1}), (4.5, 5.8)),
    ("France 1836 (Family Limitation)", dict(sol=11, literacy=0.3, urban_share=0.15, techs=MED_1836,
                                             means_add=P.FAMILY_LIMITATION_MEANS), (3.4, 5.0)),
    ("Britain 1900", dict(sol=16, literacy=0.75, urban_share=0.6, techs=MED_1900 | MEANS_TECHS, laws={CHS},
                          institutions={HEALTH: 4}), (3.2, 4.0)),
    ("West 1950", dict(sol=25, literacy=0.95, urban_share=0.65, techs=MED_1950 | MEANS_TECHS, laws={PHI},
                       institutions={HEALTH: 5}), (2.3, 3.5)),
    ("West 1990", dict(sol=38, literacy=0.98, urban_share=0.75,
                       techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"}, laws={PHI},
                       institutions={HEALTH: 6}), (1.4, 2.0)),
    # The women's-rights term (phase 2 step 4, Task 7): Western scenarios with the law their countries held, banded
    # by Gapminder's Western range that year (the tfr anchors, 2026-10-10): 1900 France 2.80 to Germany 4.93; 1950
    # Austria 1.87 to the Netherlands 3.10; 1990 Italy 1.30 to Sweden 2.14.
    ("1836 agrarian, No Women's Rights", dict(sol=8, literacy=0.2, urban_share=0.1,
                                              laws={"law_no_womens_rights"}), (4.8, 6.2)),
    ("Britain 1900, Women Own Property", dict(sol=16, literacy=0.75, urban_share=0.6, techs=MED_1900 | MEANS_TECHS,
                                              laws={CHS, "law_women_own_property"}, institutions={HEALTH: 4}),
     (2.8, 4.9)),
    ("West 1950, Women's Suffrage", dict(sol=25, literacy=0.95, urban_share=0.65, techs=MED_1950 | MEANS_TECHS,
                                         laws={PHI, "law_womens_suffrage"}, institutions={HEALTH: 5}), (1.9, 3.1)),
    ("West 1990, Women's Suffrage", dict(sol=38, literacy=0.98, urban_share=0.75,
                                         techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"},
                                         laws={PHI, "law_womens_suffrage"}, institutions={HEALTH: 6}), (1.3, 2.2)),
    ("India 1975", dict(sol=9, literacy=0.35, urban_share=0.2, techs=MED_1950 | MEANS_TECHS | {"contraceptive_pill"},
                        laws={CHS}, institutions={HEALTH: 1}), (4.7, 5.8)),
]


# The children-per-woman scenarios with the practices' shares (the late-marriage spec 5.1 item 4: the shares the drift
# gives each), and review I3's two for the 20th century where Birth Spacing has eroded and only the raise is left
# (bands from Gapminder in the anchors: East Asia 1990 Japan 1.56, Korea 1.58, Taiwan 1.81, China 2.35; Latin America
# 1970 Chile 4.02 to Mexico 6.83, Argentina's 3.07 left out). practices-fit judges candidates against them; Task 6
# makes them the fertility command's once the raise is applied.
_SCENARIO_PRACTICES = {
    "1836 agrarian (reference)": {"lm": 0.5}, "1836 agrarian, No Women's Rights": {"lm": 0.5},
    "Britain 1836": {"lm": 1.0}, "France 1836 (Family Limitation)": {"lm": 1.0},
    "Britain 1900": {"lm": 0.75}, "Britain 1900, Women Own Property": {"lm": 0.75},
    "West 1950": {"lm": 0.5}, "West 1950, Women's Suffrage": {"lm": 0.5},
    "West 1990": {"lm": 0.45}, "West 1990, Women's Suffrage": {"lm": 0.45},
    "India 1975": {"bs": 0.0},   # the drift's equilibrium from India's held start: 0 since the fit (2026-10-12)
}
_SCENARIO_BANDS = {"Britain 1836": (4.3, 5.5)}   # re-centred on history's 4.8-5.0 (spec 5.1)
PRACTICE_SCENARIOS = [(label, dict(kw, practices=_SCENARIO_PRACTICES[label]), _SCENARIO_BANDS.get(label, band))
                      for label, kw, band in FERTILITY_SCENARIOS] + [
    ("East Asia 1990", dict(sol=28, literacy=0.97, urban_share=0.7,
                            techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"}, laws={PHI},
                            institutions={HEALTH: 5}, practices={"lm": 0.1, "bs": 0.05}), (1.4, 2.4)),
    ("Latin America 1970", dict(sol=12, literacy=0.72, urban_share=0.55, techs=MED_1950 | MEANS_TECHS, laws={CHS},
                                institutions={HEALTH: 2}), (4.0, 6.8)),
]
# The fertility command judges the scenarios with their shares (the late-marriage plan, Task 6).
FERTILITY_SCENARIOS = PRACTICE_SCENARIOS


def fertility_rows(carriers=None, scenarios=None):
    """[(label, children per woman, low, high)] for `scenarios` (default FERTILITY_SCENARIOS), with the game files'
    values."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, kw, (lo, hi) in scenarios or FERTILITY_SCENARIOS:
        inp = scenario_inputs(carriers, **kw)
        rows.append((label, M.fertility(inp, life(inp)["e0"])["tfr"], lo, hi))
    return rows


def cmd_fertility(_args):
    out = 0
    for label, tfr, lo, hi in fertility_rows():
        ok = lo <= tfr <= hi
        out |= not ok
        print(f"{label:34s} children per woman {tfr:4.2f} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}")
    return out



# ---- history: the model against history's anchors (phase 2 calibration) -----------------------
# The anchors are a CSV `measure,country,year,value` (scripts/analysis/fetch_history_anchors.py
# writes it from Clio Infra; the data stay outside the repo). Countries are matched to the game's
# tags through HISTORY_TAGS, each country's tags in order of preference: the first one in the save
# is used (Italy is Sardinia-Piedmont until it forms; India is the East India Company, then India).
HISTORY_TAGS = {
    "United Kingdom": ("GBR",), "France": ("FRA",), "United States": ("USA",), "China": ("CHI",),
    "India": ("BHT", "BIC"), "Japan": ("JAP",), "Russia": ("RUS",), "Germany": ("GER", "PRU"),
    "Austria": ("AUS",), "Spain": ("SPA",), "Turkey": ("TUR",), "Egypt": ("EGY",), "Mexico": ("MEX",),
    "Brazil": ("BRZ",), "Sweden": ("SWE",), "Netherlands": ("NET",), "Belgium": ("BEL",),
    "Portugal": ("POR",), "Denmark": ("DEN",), "Iran": ("PER",), "Korea": ("KOR",), "Italy": ("ITA", "SAR"),
    "Argentina": ("ARG",), "Chile": ("CHL",), "Peru": ("PEU",),
}


def read_anchors(path):
    """{measure: {country: {year: value}}} from fetch_history_anchors.py's CSV."""
    import csv
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["measure"], {}).setdefault(r["country"], {})[int(r["year"])] = float(r["value"])
    return out


def nearest(series, year, span):
    """(year, value) of the anchor closest to `year` within `span` years, or None."""
    best = None
    for y, v in series.items():
        if abs(y - year) <= span and (best is None or abs(y - year) < abs(best[0] - year)):
            best = (y, v)
    return best


def growth_around(series, year, span=30):
    """% a year between the nearest benchmarks before and after `year` (at most `span` years each way)."""
    before = [y for y in series if year - span <= y <= year]
    after = [y for y in series if year < y <= year + span]
    if not before or not after:
        return None
    y0, y1 = max(before), min(after)
    if series[y0] <= 0 or series[y1] <= 0:
        return None
    return 100 * math.log(series[y1] / series[y0]) / (y1 - y0)


def save_year(path):
    """The save's year, from `game_date=` in its meta_data block (plain-text saves), or None.
    A bare `date=` is not read: an ironman save's meta_data has `date=1.1.1`."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for _ in range(40):
            m = re.match(r"\s*game_date=\"?(\d+)\.", fh.readline())
            if m:
                return int(m.group(1))
    return None


def model_figures(inp):
    """{e0, imr, tfr, r}: the model's steady rates for a country's inputs (r in % a year)."""
    qf, qm, _ = M.group_rates(inp)
    e0 = (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2
    tfr = M.fertility(inp, e0)["tfr"]
    r = 100 * math.log(max(M.nrr(tfr, qf), 1e-9)) / 29
    return {"e0": e0, "imr": (qf[0] + qm[0]) / 200, "tfr": tfr, "r": r}


def country_figures(states, carriers, stored=None, shares=None, incorporated_only=False):
    """A country's model figures as the census builds them: each state's own rates (its SoL, literacy,
    urban share and incorporation; with `stored`, {state id: {variable: value}}, the census's own inputs from the
    save, so medicine as it had spread), weighted by its people. The poverty term bends at SoL 9, so the
    rates at the country's mean SoL would hide what its poor and rich states do (#855's review). shares:
    {state id: {practice: share}} (the late-marriage plan); incorporated_only leaves a country's colonies out
    (spec 5.1 item 3)."""
    stored, shares = stored or {}, shares or {}
    figs = [(st.population, model_figures(census_inputs(inputs_for(st, carriers, incorporated=inc,
                                                                   practices=shares.get(sid)),
                                                        stored.get(sid, {}))))
            for sid, st, inc in states if st.population > 0 and (inc or not incorporated_only)]
    tot = sum(p for p, _ in figs) or 1
    return {k: sum(p * f[k] for p, f in figs) / tot for k in ("e0", "imr", "tfr", "r")}


def history_rows(sections, year, anchors, carriers=None, stored=None, shares=None, incorporated_only=False,
                 practices=True, saved=None):
    """[(country, tag, people, model figures, anchors)] for each HISTORY_TAGS country in the save, the
    world line (every country of 1M people or more, weighted by people) and the mapped countries that
    have no anchor of any kind. The practices (the late-marriage plan, Task 3): every state takes its seed, as the
    census gives it with no sibling holding a share (its start less what its conditions have eroded), and `shares`
    ({state id: {practice: share}}, a replay's year) overrides the states it holds, over `saved` (the save's own
    te_dg_pr_*, saved_shares; Stop B, M2), which overrides the seed; practices=False is the model without them. incorporated_only: each country's figure from its incorporated states (the world line keeps every
    state)."""
    carriers = DM.load_carriers() if carriers is None else carriers
    states = S.state_inputs(sections)
    if not practices:
        shares = {}
    else:
        regions, sr = R.strategic_region_of(), S.state_regions(sections)

        def seed(sid, st, inc):
            reg = sr.get(sid, "")
            inp = inputs_for(st, carriers, incorporated=inc)
            return {p: M.practice_seed(p, inp, M.practice_start(p, reg, regions.get(reg, "")), [])
                    for p in P.PRACTICES}

        shares = {**{sid: seed(sid, st, inc) for sts in states.values() for sid, st, inc in sts}, **(saved or {}),
                  **(shares or {})}
    people = {tag: sum(st.population for _sid, st, _inc in sts) for tag, sts in states.items()}
    rows, bare = [], []
    for country, tags in HISTORY_TAGS.items():
        tag = next((t for t in tags if people.get(t, 0) > 0), None)
        if tag is None:
            continue
        if not any(country in anchors.get(m, {}) for m in ("e0", "imr", "population", "tfr")):
            bare.append(country)
        hist = {"e0": nearest(anchors.get("e0", {}).get(country, {}), year, 15),
                "imr": nearest(anchors.get("imr", {}).get(country, {}), year, 15),
                "tfr": nearest(anchors.get("tfr", {}).get(country, {}), year, 5),
                "growth": growth_around(anchors.get("population", {}).get(country, {}), year)}
        rows.append((country, tag, people[tag], country_figures(states[tag], carriers, stored, shares, incorporated_only),
                     hist))
    big = [(people[t], country_figures(sts, carriers, stored, shares)) for t, sts in states.items()
           if people[t] >= 1e6]
    tot = sum(p for p, _ in big) or 1
    world = {k: sum(p * f[k] for p, f in big) / tot for k in ("e0", "imr", "tfr", "r")}
    return rows, world, bare


def cmd_history(args):
    try:
        anchors = read_anchors(args.anchors)
    except OSError as e:
        print(f"cannot read the anchors {args.anchors}: {e} (scripts/analysis/fetch_history_anchors.py writes them)",
              file=sys.stderr)
        return 1
    carriers = DM.load_carriers()
    shares_by_year = {}
    if args.shares:
        import demographics_practices as DP   # it imports this module
        shares_by_year = DP.read_shares(args.shares)
    only = "; countries: incorporated states only" if args.incorporated_only else ""
    for path in args.save:
        sections = S.read_sections(path)        # a binary or zipped save stops here (NotPlainText, exit 1)
        year = save_year(path) or args.year     # the save's own date first; --year fills in a slice
        if year is None:
            print(f"{path}: no game_date in its meta_data; give the year with --year", file=sys.stderr)
            return 1
        _countries, walked = S.read_variables(path, (), CENSUS_INPUT_VARS + PRACTICE_VARS)
        stored = {sid: rec["vars"] for sid, rec in walked.items()}
        saved = saved_shares(stored)
        rows, world, bare = history_rows(sections, year, anchors, carriers, stored, shares=shares_by_year.get(year),
                                         incorporated_only=args.incorporated_only, practices=not args.no_practices,
                                         saved=saved)
        for country in bare:
            print(f"{country}: no anchors in {args.anchors}", file=sys.stderr)
        print(f"== {Path(path).name} ({year}): world (countries of 1M or more) e0 {world['e0']:.1f}  "
              f"children per woman {world['tfr']:.2f}  growth {world['r']:+.2f}% a year{only}")
        own = sum(1 for v in stored.values() if all(k in v for k in CENSUS_INPUT_VARS))
        print(f"   {own} states on the census's own inputs (medicine as it had spread); {len(saved)} with its own "
              "practice shares")
        for country, tag, people, got, hist in sorted(rows, key=lambda r: -r[2]):
            e = f"{hist['e0'][1]:.0f} ({hist['e0'][0]})" if hist["e0"] else "-"
            m = f"{hist['imr'][1]:.0f}" if hist["imr"] else "-"
            g = f"{hist['growth']:+.2f}%" if hist["growth"] is not None else "-"
            t = f"{hist['tfr'][1]:.1f}" if hist["tfr"] else "-"
            print(f"{tag:4s} {country:15s} {people / 1e6:6.1f}M  model e0 {got['e0']:4.1f} imr {got['imr']:4.0f} "
                  f"tfr {got['tfr']:.2f} growth {got['r']:+.2f}%   history e0 {e:10s} imr {m:4s} tfr {t:4s} people {g}")
    return 0


# ---- Late Marriage and Birth Spacing (docs/superpowers/plans/2026-10-11-demographics-late-marriage.md) ----------
# demographics_practices imports this module, so the commands import it inside.
def cmd_practices_replay(args):
    import demographics_practices as DP
    carriers = DM.load_carriers()
    loaded = sorted(((save_year(p) or args.year, DP.practice_states(p, carriers)) for p in args.save),
                    key=lambda pair: pair[0])
    result = DP.replay(loaded)
    for year, recs in sorted(result.items()):
        west = DP._mean(recs.values(), "lm", lambda r: r["strategic_region"] in DP.WEST)
        parts = [f"West's Late Marriage {west:.2f}" if west is not None else "no Western state"]
        for label, keep in DP.EAST_ASIA_BS:
            got = DP._mean(recs.values(), "bs", keep)
            parts.append(f"{label}'s Birth Spacing {got:.2f}" if got is not None else f"no {label}")
        print(f"{year}: " + "; ".join(parts))
    print("largest moves from the start (practice, state region, start -> share, target):")
    for move, p, _sid, sr, start, share, target in DP.replay_moves(result):
        print(f"  {move:.2f}  {p} {sr:28s} {start:.2f} -> {share:.2f}  target {target:.2f}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({str(y): r for y, r in result.items()}, fh, indent=1, sort_keys=True)
    fails = DP.replay_gate(result)
    for line in fails:
        print("GATE " + line)
    return 1 if fails else 0


def cmd_practices_fit(args):
    import demographics_practices as DP
    try:
        anchors = read_anchors(args.anchors)
    except OSError as e:
        print(f"cannot read the anchors {args.anchors}: {e}", file=sys.stderr)
        return 1
    rows = DP.peacetime_span(json.loads(Path(args.peacetime).read_text(encoding="utf-8"))["rows"])
    carriers = DM.load_carriers()
    shares_by_year = DP.read_shares(args.shares) if args.shares else {}
    saves = {path: DP.read_save(path) for path in args.save}   # parse each save once
    fit_years = {int(y) for y in args.fit_years.split(",")}

    def load(carriers):
        out = {}
        for path in args.save:
            year = save_year(path) or args.year
            states = DP.practice_states(path, carriers, save=saves[path])
            # the seed, under the save's own shares (Stop B, M2), under the replay's: a state the replay lacks takes its own
            shares = {**DP.table_shares(states), **DP.saved_shares(states), **shares_by_year.get(year, {})}
            out[year] = DP.fit_states(path, carriers, shares, save=saves[path])
        return out

    def scenarios_out(carriers, s, cl, cb):
        """PRACTICE_SCENARIOS and the medicine scenarios out of band at this point (review I1): the curve x s and the
        cuts patched, since the scenarios read them from P."""
        with DP.patch_params(WEALTH_TFR_LOW=P.WEALTH_TFR_LOW * s, WEALTH_TFR_HIGH=P.WEALTH_TFR_HIGH * s,
                             PRACTICE_CUT={"lm": cl, "bs": cb}):
            fert = [r[0] for r in fertility_rows(carriers=carriers, scenarios=PRACTICE_SCENARIOS)
                    if not r[2] <= r[1] <= r[3]]
        med = [f"{label} {k}" for label, figures in medicine_rows(carriers=carriers)
               for k, (v, lo, hi) in figures.items() if not lo <= v <= hi]
        return fert, med

    def show(proj, fails):
        for label, (measured, projected) in sorted(proj["groups"].items()):
            band = dict((l, b) for l, _r, b in R.REPORT_REGIONS).get(label)
            b = f"{band[0]:+g} to {band[1]:+g}" if band else "-"
            print(f"  {label:28s} measured {measured:+5.1f}  projected {projected:+5.1f}  history {b}")
        print(f"  {'World':28s} measured {proj['world'][0]:+5.1f}  projected {proj['world'][1]:+5.1f}")
        for line in fails:
            print("  GATE " + line)

    today = load(carriers)
    grid = ([float(x) for x in args.s.split(",")], [float(x) for x in args.lm.split(",")],
            [float(x) for x in args.bs.split(",")])
    def china(res):
        """China's children per woman in the fit years, flagged below about 5 (owner, 2026-10-11; D13)."""
        got = {y: m for (c, y), (m, _h) in res["countries"].items() if c == "China" and y in fit_years}
        return " / ".join(f"{v:.2f}{' LOW' if v < 5.0 else ''}" for _y, v in sorted(got.items()))

    print("s     cut_lm cut_bs error  world tfr        india east  China tfr     high group  gate (today's mortality)")
    for s, cl, cb, res in DP.fit_table(today, anchors, *grid, years=fit_years):
        east, _rate = DP.east_for_china(rows, today, today, s, cl, cb)
        res = DP.evaluate(today, anchors, s, cl, cb, east=east, years=fit_years)
        tfr = " / ".join(f"{v:.2f}" for _y, v in sorted(res["world_tfr"].items()) if v)
        hi = f"{res['high'][0]:.2f}-{res['high'][1]:.2f}" if res["high"] else "-"
        fails = DP.region_gate(DP.project_regions(rows, today, today, s, cl, cb, east=east))
        print(f"{s:.2f}  {cl:.2f}   {cb:.2f}   {res['error']:.3f}  {tfr:16s} {res['held']:.2f}  {east:.2f}  "
              f"{china(res):12s}  {hi:10s}  {len(fails)} failing")
    if not args.at:
        return 0
    s, cl, cb, *rest = (float(x) for x in args.at.split(","))
    held = rest[0] if rest else None
    east = rest[1] if len(rest) > 1 else DP.east_for_china(rows, today, today, s, cl, cb, held)[0]
    res = DP.evaluate(today, anchors, s, cl, cb, held=held, east=east, years=fit_years)
    print(f"held shares: India {res['held']:.2f}, China, Manchuria and Korea {east:.2f}; China's children per woman "
          f"{china(res)}")
    for (country, year), (model, hist) in sorted(res["countries"].items()):
        if year not in fit_years:
            continue
        tag = " (half)" if country in DP.FLAT_GUESSES else ""
        tag += " (dropped)" if (country, year) in DP.DROPPED else ""
        off = " OFF" if hist is not None and abs(model - hist) > 0.5 else ""
        h = f"{hist:.2f}" if hist is not None else "-"
        print(f"{country:15s} {year}  model {model:.2f}  history {h}{tag}{off}")
    proj = DP.project_regions(rows, today, today, s, cl, cb, held, east)
    show(proj, DP.region_gate(proj))
    print(f"Western life expectancy: {DP.mortality_report(today)}; scenarios out of band: "
          f"{scenarios_out(carriers, s, cl, cb)}")
    if args.mortality:
        for floor in (1.5, 1.75, 2.0, 2.25):
            for sol in (8, 9, 10):
                for scale in (0.9, 1.0, 1.1, 1.2, 1.3):
                    with DP.patch_params(infection_scale=scale, POVERTY_INFECTION_AT_FLOOR=floor,
                                         POVERTY_INFECTION_SOL=sol):
                        point = load(carriers)
                        out = scenarios_out(carriers, s, cl, cb)
                    e_pt = rest[1] if len(rest) > 1 else DP.east_for_china(rows, today, point, s, cl, cb, held)[0]
                    proj = DP.project_regions(rows, today, point, s, cl, cb, held, e_pt)
                    fails = DP.region_gate(proj)
                    e0 = DP.mortality_report(point)
                    cn = china(DP.evaluate(point, anchors, s, cl, cb, held=held, east=e_pt, years=fit_years))
                    print(f"floor {floor:.2f} sol {sol} infection x{scale:.2f}: {len(fails)} failing; East Asia's "
                          f"share {e_pt:.2f}, China {cn}; Western e0 {e0}; scenarios out of band {out}")
                    show(proj, fails)
    if args.means:
        for vulc in (0.10, 0.15, 0.20, 0.25, 0.30):
            for fem in (0.10, 0.15, 0.20, 0.25, 0.30):
                patched = [dataclasses.replace(c, value=vulc) if c.key == "vulcanization"
                           and c.type == P.CONTRACEPTION_TYPE else
                           dataclasses.replace(c, value=fem) if c.key == "feminism"
                           and c.type == P.CONTRACEPTION_TYPE else c for c in carriers]
                res = DP.evaluate(load(patched), anchors, s, cl, cb, held=held, east=east, years=fit_years)
                gb = {y: m for (c, y), (m, _h) in res["countries"].items() if c == "United Kingdom"}
                print(f"vulcanization {vulc:.2f} feminism {fem:.2f}: Britain {gb}; scenarios out of band "
                      f"{scenarios_out(patched, s, cl, cb)}")
    return 0


HEALTH_LAWS = ("law_charitable_health_system", "law_private_health_insurance", "law_public_health_insurance")


# ---- predict: the engine's growth once the census sets its rates (phase 2 step 4, plan Task 10) -------------
Pop = collections.namedtuple("Pop", "size sol literacy food_security on_top_d absorbed_d wealth",
                             defaults=(0.0, 0.0, 0.0))
Pop.__doc__ = """One pop for predict: on_top_d is its class's mortality line on top; absorbed_d its class's absorbed line
(child labour: script-only since 2026-10-11, so under Full it is reported, never applied); wealth its wealth level, for
Private Health Insurance's wealth line."""
CHILD_LABOUR_LAWS = ("law_child_labor_allowed", "law_restricted_child_labor")
# the women's-rights laws whose birth lines the census's natural fertility carries (Tasks 7-8; the mod's
# Protected Class among them)
WOMENS_RIGHTS_LAWS = ("law_no_womens_rights", "law_women_in_the_fields", "law_women_in_the_workplace",
                      "law_womens_suffrage", "law_protected_class")
# predict's report groups for the absorbed state lines (owner amendment A, 2026-10-10): each carrier in one
ABSORBED_GROUPS = (("womens_rights", WOMENS_RIGHTS_LAWS), ("health", HEALTH_LAWS))
ABSORBED_REPORT = ("child_labour", "womens_rights", "health", "other_lines", "mild")


def absorbed_group(key):
    return next((g for g, keys in ABSORBED_GROUPS if key in keys), "other_lines")


def predict_state(pops, cbr, cdr, d, on_top_b=0.0, on_top_d=0.0, added_b=0.0, added_d=0.0, wealth=0.0, groups=None):
    """The engine's births and deaths a year in one state once the census sets them (phase 2 step 4, plan §2; the
    engine-lines plan, 2026-10-11).

    pops: [Pop]; cbr, cdr: the census's own rates per 1,000 a year. on_top_b, on_top_d: the engine's state-level lines
    left on top (devastation's +1.0 x share and Pollution Impact, inside the read per probe P1), which M scales to the
    census's rate. added_b, added_d: the moved lines' on-top family (family-policy laws, late techs), script-only, which
    the census adds at its rate. wealth: the on-top family's wealth line a wealth level (Private Health Insurance), which
    the census applies per pop at its share of the bare curve, at least P.WEALTH_LINE_FLOOR (owner, option b). groups:
    {group: (births, deaths)} of the absorbed family's lines, reported at the bare curves (what they would have done on
    top), never applied: under Full they are script-only and the census models them.

    Each pop gets bare x max(0, 1 + M + every term the engine still applies): literacy's -0.1 and mild starvation's,
    which M nets out, and severe starvation's, which stay. Both starvation penalties apply x the pop's starvation value
    (the famine probe, 2026-10-11, for severe). Terms on top a save doesn't hold are left out: turmoil, events,
    low_pop_state, unemployment, workplace mortality. The script reads both starvation terms in 0.05 steps of food
    security; this takes each pop's exact starvation value from its food security (demographics_model.starvation_value,
    which equals the save's food_security={ starvation= }). Reported: the starving slope below SoL 4 (absorbed: owner,
    2026-10-10) and each absorbed group's events at the bare curves."""
    people = sum(p.size for p in pops)
    bare = [(p, p.size * G.monthly_birthrate(p.sol, d) * 12, p.size * G.monthly_mortality(p.sol, d) * 12)
            for p in pops]
    bare_b, bare_d = sum(b for _, b, _ in bare), sum(x for _, _, x in bare)
    slope = sum(p.size * (G.monthly_mortality(p.sol, d) - G.monthly_mortality(max(p.sol, d.equilibrium_sol), d))
                for p in pops) * 12
    terms = []
    for p, b, x in bare:
        sb, sd = M.starvation_terms(p.food_security)
        severe = p.food_security < P.FOOD_SECURITY_SEVERE_STARVATION_THRESHOLD
        mild_b, mild_d = (0.0, 0.0) if severe else (sb, sd)
        terms.append((p, b, x, sb - mild_b, sd - mild_d, mild_b, mild_d))
    rep_b = sum(b * (P.LITERACY_BIRTH_PENALTY * p.literacy + mb) for p, b, _x, _sb, _sd, mb, _md in terms)
    rep_d = sum(x * md for p, _b, x, _sb, _sd, _mb, md in terms)
    target_b, target_d = cbr / 1000 * people, cdr / 1000 * people
    m_b, cb = M.rate_term(target_b, bare_b, absorbed=rep_b, other=on_top_b, on_top=on_top_b, added=added_b)
    m_d, cd = M.rate_term(target_d, bare_d, absorbed=rep_d, other=on_top_d, on_top=on_top_d, added=added_d)
    wealth_line = max(wealth, P.WEALTH_LINE_FLOOR) * target_d / bare_d if bare_d > 0 and wealth else 0.0
    births = deaths = 0.0
    for p, b, x, sev_b, sev_d, mb, md in terms:
        births += b * max(0.0, 1 + m_b + on_top_b + P.LITERACY_BIRTH_PENALTY * p.literacy + mb + sev_b)
        deaths += x * max(0.0, 1 + m_d + on_top_d + p.on_top_d + md + sev_d + wealth_line * p.wealth)
    out = {"people": people, "births": births, "deaths": deaths, "target_births": target_b,
           "target_deaths": target_d, "on_top_births": births - target_b, "on_top_deaths": deaths - target_d,
           "m_b": m_b, "m_d": m_d, "clamped": cb or cd, "slope_deaths": slope,
           "absorbed_child_labour_births": 0.0,
           "absorbed_child_labour_deaths": sum(x * p.absorbed_d for p, _b, x, *_ in terms),
           "absorbed_mild_births": sum(b * mb for _p, b, _x, _sb, _sd, mb, _md in terms),
           "absorbed_mild_deaths": sum(x * md for _p, _b, x, _sb, _sd, _mb, md in terms)}
    for g in ABSORBED_REPORT[1:-1]:
        gb, gd = (groups or {}).get(g, (0.0, 0.0))
        out[f"absorbed_{g}_births"], out[f"absorbed_{g}_deaths"] = bare_b * gb, bare_d * gd
    return out


def pollution_mortality(pollution):
    """Pollution Impact's mortality line at a region's pollution (0 to POLLUTION_MAX): an approximation of the
    engine's (P.POLLUTION_HEALTH_MORTALITY)."""
    return P.POLLUTION_HEALTH_MORTALITY * pollution / P.POLLUTION_MAX


def predicted_multiple(points, to_year):
    """[(year, growth % a year)] -> the multiple from the first year to to_year, each save's rate held until
    the next save's year (the last one's after it)."""
    points = sorted(points)
    total = 0.0
    for (y0, g), nxt in zip(points, points[1:] + [(to_year, None)]):
        total += g / 100 * (min(nxt[0], to_year) - y0)
    return math.exp(total)


PREDICT_SUMS = ("people", "births", "deaths", "target_births", "target_deaths", "slope_deaths", "clamped_people",
                *(f"absorbed_{g}_{k}" for g in ABSORBED_REPORT for k in ("births", "deaths")))


def _predict_figures(t):
    """A country's or the world's sums as rates: % a year, the terms on top per 1,000, shares. Each absorbed group's
    points are what absorbing it adds to growth a year, against leaving it on top."""
    n = t["people"] or 1.0
    out = {"people": t["people"],
           "census_growth": 100 * (t["target_births"] - t["target_deaths"]) / n,
           "growth": 100 * (t["births"] - t["deaths"]) / n,
           "on_top_births_per_1000": 1000 * (t["births"] - t["target_births"]) / n,
           "on_top_deaths_per_1000": 1000 * (t["deaths"] - t["target_deaths"]) / n,
           "clamped_share": t["clamped_people"] / n,
           "slope_points": 100 * t["slope_deaths"] / n,
           "mild_births_per_1000": 1000 * t["absorbed_mild_births"] / n,
           "mild_deaths_per_1000": 1000 * t["absorbed_mild_deaths"] / n}
    for g in ABSORBED_REPORT:
        name = "mild_starvation" if g == "mild" else g
        out[f"{name}_points"] = 100 * (t[f"absorbed_{g}_deaths"] - t[f"absorbed_{g}_births"]) / n
    return out


def predict_save(path, line_carriers, carriers, d, census_rates=False, check_modifiers=False):
    """{tag: sums} and the world's for one save, plus the states --check-modifiers flags. line_carriers: the moved lines
    (DM.line_carriers), each state's families summed from its owner's laws, techs and institutions."""
    sections = S.read_sections(path)
    states = S.state_inputs(sections)
    countries = S.country_inputs(sections)
    tags = {cid: rec.get("definition", "").strip('"') for cid, rec in sections["country_manager"].items()}
    owner = {sid: tags.get(rec.get("country")) for sid, rec in sections["states"].items()}
    pollution = S.state_pollution(sections)
    svars = {}
    if census_rates or check_modifiers:
        _c, st_vars = S.read_variables(path, (), ("te_dg_cbr_model", "te_dg_cdr_model", "te_dg_cbr", "te_dg_cdr",
                                                  "te_dg_mb", "te_dg_md"))
        svars = {sid: rec["vars"] for sid, rec in st_vars.items()}
    types = set(P.ENGINE_LINE_TYPES.values())
    absorbed_b = P.ENGINE_LINE_TYPES[("absorbed", "state_birth_rate_mult")]
    absorbed_d = P.ENGINE_LINE_TYPES[("absorbed", "state_mortality_mult")]
    by_group = {g: [c for c in line_carriers if c.type in (absorbed_b, absorbed_d) and absorbed_group(c.key) == g]
                for g in ABSORBED_REPORT[1:-1]}
    pops = {}
    for rec in sections["pops"].values():
        size = S._num(rec.get("workforce")) + S._num(rec.get("dependents"))
        sid = rec.get("location")
        if size <= 0 or owner.get(sid) not in countries:
            continue
        pops.setdefault(sid, []).append((rec.get("type"), Pop(size, S._num(rec.get("previous_quality_of_life")),
                                                               S._num(rec.get("num_literate")) / size,
                                                               S._num(rec.get("food_security"), 1.0),
                                                               wealth=S._num(rec.get("wealth")))))
    sums = {}
    for tag, sts in states.items():
        c = countries[tag]
        for sid, st, inc in sts:
            if sid not in pops:
                continue
            fam = DM.totals(line_carriers, c.techs, c.laws, c.institutions, incorporated=inc, types=types)
            groups = {}
            for g, cs in by_group.items():
                t = DM.totals(cs, c.techs, c.laws, c.institutions, incorporated=inc, types={absorbed_b, absorbed_d})
                groups[g] = (t[absorbed_b], t[absorbed_d])
            state_pops = [p._replace(absorbed_d=fam.get(P.ENGINE_LINE_TYPES.get(
                ("absorbed", f"state_{ptype}_mortality_mult"), ""), 0.0)) for ptype, p in pops[sid]]
            v = svars.get(sid, {})
            if census_rates and ("te_dg_cbr_model" in v or "te_dg_cbr" in v):
                cbr = v.get("te_dg_cbr_model", v.get("te_dg_cbr"))
                cdr = v.get("te_dg_cdr_model", v.get("te_dg_cdr"))
            else:
                cbr, cdr = M.model_crude_rates(inputs_for(st, carriers, incorporated=inc))
            devastation = S._num(sections["states"].get(sid, {}).get("devastation")) / 100
            out = predict_state(state_pops, cbr, cdr, d, on_top_b=0.0,
                                on_top_d=devastation + pollution_mortality(pollution.get(sid, 0.0)),
                                added_b=fam[P.ENGINE_LINE_TYPES[("ontop", "state_birth_rate_mult")]],
                                added_d=fam[P.ENGINE_LINE_TYPES[("ontop", "state_mortality_mult")]],
                                wealth=fam[P.ENGINE_LINE_TYPES[("ontop", "state_mortality_wealth_mult")]],
                                groups=groups)
            out["clamped_people"] = out["people"] if out["clamped"] else 0.0
            for t in (tag, None):
                acc = sums.setdefault(t, dict.fromkeys(PREDICT_SUMS, 0.0))
                for k in PREDICT_SUMS:
                    acc[k] += out[k]
    flagged = []
    if check_modifiers:
        for sid, v in svars.items():
            mods = {name for name, _mult in sections["states"].get(sid, {}).get("timed_modifiers", ())}
            for kind, var in (("births", "te_dg_mb"), ("deaths", "te_dg_md")):
                m = v.get(var, 0.0)
                want = f"te_demog_census_{kind}_{'up' if m > 0 else 'down'}"
                if m and want not in mods:
                    flagged.append((sid, owner.get(sid), var, m))
    return sums, flagged


def cmd_predict(args):
    line_carriers = DM.line_carriers()
    carriers, d = DM.load_carriers(), G.read_defines()
    points, failed, report = [], False, {}
    for path in args.save:
        year = save_year(path) or args.year     # the save's own date first; --year fills in a slice
        if year is None:
            print(f"{path}: no game_date in its meta_data; give the year with --year", file=sys.stderr)
            return 1
        sums, flagged = predict_save(path, line_carriers, carriers, d, args.census_rates, args.check_modifiers)
        world = _predict_figures(sums[None])
        points.append((year, world["growth"]))
        big = {tag: _predict_figures(t) for tag, t in sums.items() if tag is not None and t["people"] >= 20e6}
        shrinking = sorted(tag for tag, f in big.items() if f["growth"] < 0)
        failed |= bool(shrinking)
        report[Path(path).name] = {"year": year, "world": world, "countries": big, "shrinking": shrinking,
                                   "modifiers_missing": flagged}
        if args.json:
            continue
        print(f"== {Path(path).name} ({year}): world {world['people'] / 1e6:.0f}M  census {world['census_growth']:+.2f}% "
              f"a year, predicted {world['growth']:+.2f}%  on top: births {world['on_top_births_per_1000']:+.2f}, "
              f"deaths {world['on_top_deaths_per_1000']:+.2f} per 1,000  clamped {world['clamped_share']:.1%}")
        print(f"   absorbed, in points of world growth a year against leaving them on top: child labour's class lines "
              f"{world['child_labour_points']:+.3f}, women's rights' birth lines {world['womens_rights_points']:+.3f}, "
              f"the health laws {world['health_points']:+.3f}, the other lines {world['other_lines_points']:+.3f}, "
              f"mild starvation {world['mild_starvation_points']:+.3f} (births {world['mild_births_per_1000']:+.2f}, "
              f"deaths {world['mild_deaths_per_1000']:+.2f} per 1,000)")
        if args.slope:
            print(f"   the starving slope below SoL 4 (absorbed): {world['slope_points']:.3f} points of world growth")
        for tag, f in sorted(big.items(), key=lambda kv: -kv[1]["people"]):
            extra = f"  slope {f['slope_points']:.3f}" if args.slope else ""
            print(f"{tag:4s} {f['people'] / 1e6:6.1f}M  census {f['census_growth']:+.2f}%  predicted {f['growth']:+.2f}%  "
                  f"child labour {f['child_labour_points']:+.3f}  women's rights {f['womens_rights_points']:+.3f}  "
                  f"health {f['health_points']:+.3f}  mild starvation {f['mild_starvation_points']:+.3f}"
                  f"{extra}{'  SHRINKS' if f['growth'] < 0 else ''}")
        for sid, tag, var, m in flagged:
            print(f"   state {sid} ({tag}): {var} = {m:+.4f} but no matching te_demog_census_* modifier (probe P4)")
    multiple = predicted_multiple(points, args.to_year)
    ok = 1.3 <= multiple <= 1.7
    failed |= not ok
    if args.json:
        print(json.dumps({"saves": report, "multiple": multiple, "in_band": ok}, indent=2))
    else:
        print(f"predicted world multiple {points[0][0] if points else '-'}-{args.to_year}: x{multiple:.2f} "
              f"[x1.3-x1.7] {'PASS' if ok else 'FAIL'}")
    return 1 if failed else 0


def without_health_law(c):
    """A copy of a save's country with no health law and no Health System level."""
    return dataclasses.replace(c, laws=set(c.laws) - set(HEALTH_LAWS),
                               institutions={k: v for k, v in c.institutions.items() if k != HEALTH})


def adopter_rows(inputs, carriers, sol_band=1.5, lit_band=0.1):
    """One row per country with a health law: (law, tag, sol, literacy, incorporated share, health level,
    e0, e0 without the law and its level, peers' median e0 or None, peer count). Peers are countries
    with no health law within the SoL and literacy bands; e0 is the model's for incorporated states."""
    e0 = {t: life(inputs_for(c, carriers))["e0"] for t, c in inputs.items() if c.population > 0}
    none = [t for t, c in inputs.items() if t in e0 and not (c.laws & set(HEALTH_LAWS))]
    rows = []
    for tag, c in inputs.items():
        held = c.laws & set(HEALTH_LAWS)
        if tag not in e0 or not held:
            continue
        own = life(inputs_for(without_health_law(c), carriers))["e0"]
        peers = [e0[t] for t in none if abs(inputs[t].sol - c.sol) <= sol_band
                 and abs(inputs[t].literacy - c.literacy) <= lit_band]
        median = statistics.median(peers) if peers else None
        rows.append((min(held), tag, c.sol, c.literacy, c.incorporated_share, c.institutions.get(HEALTH, 0),
                     e0[tag], own, median, len(peers)))
    return sorted(rows)


def cmd_adopters(args):
    carriers = DM.load_carriers()
    for path in args.saves:
        inputs = S.country_inputs(S.read_sections(path))
        print(path)
        effects, gaps = {}, {}
        for law, tag, sol, lit, inc, level, e0, own, median, n in adopter_rows(inputs, carriers):
            gap = "-" if median is None else f"{e0 - median:+5.1f}"
            print(f"  {law:32s} {tag:4s} SoL {sol:5.1f} lit {lit:4.2f} incorporated {inc:4.2f} level {level}  "
                  f"e0 {e0:5.1f}  law's effect {e0 - own:+5.1f}  "
                  f"peers {'-' if median is None else f'{median:5.1f}'} (n={n}) gap {gap}")
            effects.setdefault(law, []).append(e0 - own)
            if median is not None:
                gaps.setdefault(law, []).append(e0 - median)
        for law in sorted(effects):
            g = gaps.get(law, [])
            print(f"  {law}: the law's own effect, median {statistics.median(effects[law]):+.1f} years over "
                  f"{len(effects[law])} countries; the gap to peers, median "
                  f"{'-' if not g else f'{statistics.median(g):+.1f}'} over {len(g)}")
    return 0


# ---- fidelity: the harness against the census's own figures ------------------------------------------------
# (cause, the census's state variable, its scale): each state's walk stores its cause multipliers, maternal as
# deaths per 100,000 births (te_demog_effects.txt).
FIDELITY_CAUSES = (("infection", "te_dg_m_inf", 1.0), ("chronic", "te_dg_m_chr", 1.0),
                   ("external", "te_dg_m_ext", 1.0), ("work", "te_dg_m_work", 1.0),
                   ("maternal", "te_dg_m_mat", P.MATERNAL_PER_100K_BIRTHS))
# The step's own inputs (the Causes of Death plan): with them the model runs on what the census used, so a mismatch is
# the script against the model; a census from before them is read from the save's techs, laws and modifiers.
CENSUS_INPUT_VARS = ("te_dg_acc", "te_dg_trt_inf", "te_dg_trt_mat", "te_dg_trt_chr", "te_dg_in_ext",
                     "te_dg_in_work", "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd")
# The step's own SoL and literacy (#916): a walk without a step rewrites te_dg_sol and te_dg_lit, never te_dg_m_*.
# Read on their own, not in CENSUS_INPUT_VARS: that check is all or nothing, and a census from before #916's last
# fix, which holds the nine without these two, would lose its drifted medicine.
STEP_SOL_VARS = ("te_dg_in_sol", "te_dg_in_lit")
# The practices' shares a census state holds (te_demog_practice_effects.txt; Stop B, M2): history and practices-fit start
# from them where a save has them, under a replay's (--shares) and over the seed.
PRACTICE_VARS = tuple(f"te_dg_pr_{p}" for p in P.PRACTICES)


def saved_shares(walked):
    """{state id: {practice: share}} for the states whose variables ({state id: {variable: value}}) hold every
    practice's share."""
    return {sid: {p: got[f"te_dg_pr_{p}"] for p in P.PRACTICES} for sid, got in walked.items()
            if all(f"te_dg_pr_{p}" in got for p in P.PRACTICES)}


FIDELITY_VARS = (("te_dg_sol", "te_dg_lit") + STEP_SOL_VARS + tuple(var for _c, var, _s in FIDELITY_CAUSES)
                 + CENSUS_INPUT_VARS)


def census_inputs(inp, got):
    """`inp` with the step's stored inputs, when the save holds them all; `inp` itself otherwise."""
    if not all(v in got for v in CENSUS_INPUT_VARS):
        return inp
    medicine = {"access": got["te_dg_acc"]}
    medicine.update({c: got[f"te_dg_trt_{P.CAUSE_SHORT[c]}"] for c in P.MEDICINE_CAUSES})
    mods = dict(inp.mods)
    for cause, types in P.MORTALITY_TYPES.items():
        for t in types:
            mods[t] = 0.0
        mods[types[0]] = got[f"te_dg_in_{P.CAUSE_SHORT[cause]}"]
    return dataclasses.replace(inp, medicine=medicine, turmoil=got["te_dg_in_turm"], crowding=got["te_dg_in_crowd"],
                               mods=mods)


def fidelity_rows(path, carriers=None, tags=(), counts=None):
    """[(tag, state id, people, {cause: (census, model)}, (SoL: save, walk), (literacy: save, walk))] for each state
    the census has walked. The model runs on the SoL and literacy the step used (te_dg_in_sol, te_dg_in_lit; for a
    census from before them, the walk's te_dg_sol and te_dg_lit, which a walk without a step rewrites) and, where
    the save holds them, the step's own stored inputs (census_inputs: the drifted medicine, turmoil, crowding and
    the plain types' sums); otherwise on the save's techs, laws, institutions and crowding. So a cause that differs
    is the script against the model, a term the harness doesn't read (the crowding term was one, 2026-10-10) or, for
    a census from before the stored inputs, an input that changed after the state's last step (a new tech or law).
    counts, if given, gets {"stored": states read on their own inputs, "save": states read from the save, "spreading":
    states whose stored medicine is more than P.MEDICINE_SNAP from the targets the save's lines give}."""
    carriers = DM.load_carriers() if carriers is None else carriers
    _countries, walked = S.read_variables(path, (), FIDELITY_VARS)
    if counts is not None:
        counts.update(stored=0, save=0, spreading=0)
    rows = []
    for tag, states in S.state_inputs(S.read_sections(path)).items():
        if tags and tag not in tags:
            continue
        for sid, st, inc in states:
            got = walked.get(sid, {}).get("vars", {})
            if "te_dg_m_inf" not in got or st.population <= 0:
                continue
            inp = dataclasses.replace(inputs_for(st, carriers, incorporated=inc),
                                      sol=got.get("te_dg_in_sol", got.get("te_dg_sol", st.sol)),
                                      literacy=got.get("te_dg_in_lit", got.get("te_dg_lit", st.literacy)))
            own = census_inputs(inp, got)
            if counts is not None:
                counts["stored" if own is not inp else "save"] += 1
                if own is not inp:
                    targets = M.medicine_targets(inp)
                    counts["spreading"] += any(abs(own.medicine[k] - targets[k]) > P.MEDICINE_SNAP for k in targets)
            inp = own
            model = M.cause_multipliers(inp)
            pairs = {cause: (got[var] / scale, model[cause]) for cause, var, scale in FIDELITY_CAUSES if var in got}
            rows.append((tag, sid, st.population, pairs, (st.sol, got.get("te_dg_sol")),
                         (st.literacy, got.get("te_dg_lit"))))
    return rows


def _num_or_dash(v, spec):
    return "-" if v is None else format(v, spec)


def cmd_fidelity(args):
    kept = P.POVERTY_INFECTION_AT_FLOOR
    if args.poverty_floor is not None:
        P.POVERTY_INFECTION_AT_FLOOR = args.poverty_floor
    try:
        return _fidelity(args)
    finally:
        P.POVERTY_INFECTION_AT_FLOOR = kept


def _fidelity(args):
    counts = {}
    rows = fidelity_rows(args.save, tags=set(args.tag), counts=counts)
    if not rows:
        which = f" in {', '.join(sorted(args.tag))}" if args.tag else ""
        print(f"{args.save}: no state the census has walked{which} (no te_dg_m_inf)", file=sys.stderr)
        return 1
    people = sum(r[2] for r in rows)
    print(f"{len(rows)} states the census has walked, {people / 1e6:,.1f}M people. A cause is off where the census's "
          f"multiplier is more than {args.tolerance:.0%} from the model's on the step's own SoL and literacy "
          "(the walk's, for a census from before the step stored them).")
    print(f"The model has the poverty term at x{P.POVERTY_INFECTION_AT_FLOOR:g} (SoL {P.POVERTY_INFECTION_FLOOR_SOL}); "
          f"a save from a build with another shows it as off below SoL {P.POVERTY_INFECTION_SOL} "
          f"(--poverty-floor 1 for one from before the poverty term).")
    print("Crowding is the continuous term (infection + the state's migration penalty); a save from main's x1.15 switch "
          "shows crowded states' infection as off.")
    print(f"{counts['stored']} states read on the census's stored inputs (medicine as it had spread, turmoil); "
          f"{counts['save']} from the save's techs and laws; medicine still spreading in {counts['spreading']}.")
    out = 0
    for cause, _var, _scale in FIDELITY_CAUSES:
        ratios = [(g / m if m else math.inf, r) for r in rows for c, (g, m) in r[3].items() if c == cause]
        off = [(x, r) for x, r in ratios if abs(x - 1) > args.tolerance]
        share = sum(r[2] for _x, r in off) / people
        worst = max(off, key=lambda xr: abs(xr[0] - 1), default=None)
        tail = f"; worst {worst[1][0]} state {worst[1][1]}, census / model {worst[0]:.3f}" if worst else ""
        print(f"  {cause:10s} off in {len(off)} of {len(ratios)} states ({share:.0%} of people){tail}")
        out |= bool(off)
    sol = sorted(abs(s - w) for r in rows for s, w in [r[4]] if w is not None)
    lit = sorted(abs(s - w) for r in rows for s, w in [r[5]] if w is not None)
    if sol and lit:
        print(f"  the save's pops against the walk: SoL median difference {statistics.median(sol):.2f} "
              f"(largest {sol[-1]:.2f}), literacy {statistics.median(lit):.3f} (largest {lit[-1]:.3f})")
    if args.tag:
        for tag, sid, pop, pairs, (s_sol, w_sol), (s_lit, w_lit) in rows:
            print(f"  {tag} {sid:>5} {pop / 1e6:6.2f}M  SoL {s_sol:5.2f}/{_num_or_dash(w_sol, '5.2f')}  "
                  f"literacy {s_lit:.3f}/{_num_or_dash(w_lit, '.3f')}  "
                  + "  ".join(f"{c} {g:.3f}/{m:.3f}" for c, (g, m) in pairs.items()))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sketch").set_defaults(fn=cmd_sketch)
    p = sub.add_parser("inputs")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(fn=cmd_inputs)
    p = sub.add_parser("gini")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--shift", type=int, default=0, help="add this many wealth levels to every pop")
    p.set_defaults(fn=cmd_gini)
    p = sub.add_parser("seed")
    p.add_argument("save")
    p.add_argument("--tag", required=True)
    p.set_defaults(fn=cmd_seed)
    p = sub.add_parser("natural-change")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--months", type=int, default=1)
    p.set_defaults(fn=cmd_natural_change)
    p = sub.add_parser("replay")
    p.add_argument("log")
    p.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    p.set_defaults(fn=cmd_replay)
    p = sub.add_parser("wc")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--top", type=int, default=30)
    p.set_defaults(fn=cmd_wc)
    sub.add_parser("medicine").set_defaults(fn=cmd_medicine)
    sub.add_parser("lag").set_defaults(fn=cmd_lag)
    p = sub.add_parser("consequences", help="phase 2 step 4: conscription, the youth bulge and sex balance against "
                                            "the design's §5 bands (saves: the 1836 one first)")
    p.add_argument("saves", nargs="*", help="plain-text saves made under Full or Display only")
    p.add_argument("--no-unemployment", action="store_true", help="skip the pops pass (the youth bulge reads 0)")
    p.add_argument("--sex-effects", action="store_true",
                   help="judge the sex balance's band and anchors as if its held-back effects were on")
    p.set_defaults(fn=cmd_consequences)
    sub.add_parser("fertility").set_defaults(fn=cmd_fertility)
    sub.add_parser("workforce", help="phase 2 step 1: the participation figures at the starting values (the design "
                                     "§1.8)").set_defaults(fn=cmd_workforce)
    p = sub.add_parser("history")
    p.add_argument("save", nargs="+")
    p.add_argument("--anchors", required=True, help="fetch_history_anchors.py's CSV")
    p.add_argument("--year", type=int, help="the saves' year, for a save with no game_date (a slice)")
    p.add_argument("--shares", help="practices-replay's --out file: each save's year selects its shares; a state or a "
                                    "year it doesn't hold takes its seed")
    p.add_argument("--incorporated-only", action="store_true",
                   help="each country's figure from its incorporated states (the world line keeps every state)")
    p.add_argument("--no-practices", action="store_true", help="the model without Late Marriage and Birth Spacing")
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser("practices-replay", help="Late Marriage's and Birth Spacing's drift through a run's saves")
    p.add_argument("save", nargs="+")
    p.add_argument("--out", help="write {year: {state id: record}} here (history --shares, practices-fit --shares)")
    p.add_argument("--year", type=int, help="the saves' year, for a save with no game_date (a slice)")
    p.set_defaults(fn=cmd_practices_replay)
    p = sub.add_parser("practices-fit", help="the practices' joint fit, #904's peacetime rates projected, the gate")
    p.add_argument("save", nargs="+")
    p.add_argument("--anchors", required=True, help="fetch_history_anchors.py's CSV")
    p.add_argument("--peacetime", required=True, help="#904's state-years: regional-rates/analyze.py --json's file")
    p.add_argument("--shares", help="practices-replay's --out file (a state or year it lacks takes its seed)")
    p.add_argument("--s", default="1.00,1.05,1.10,1.15,1.20", help="the wealth curve's raises to try")
    p.add_argument("--lm", default="0.20,0.25,0.30,0.35,0.40", help="Late Marriage's cuts to try")
    p.add_argument("--bs", default="0.25,0.30,0.35,0.40,0.45", help="Birth Spacing's cuts to try")
    p.add_argument("--fit-years", default="1837,1887", help="the saves' years the children-per-woman error reads")
    p.add_argument("--at", help="S,LM,BS[,HELD[,EAST]]: one point in detail (HELD India's share, EAST East Asia's)")
    p.add_argument("--mortality", action="store_true", help="with --at: the poverty term and base infection grid")
    p.add_argument("--means", action="store_true", help="with --at: the era-3 means pair's grid")
    p.add_argument("--year", type=int, help="the saves' year, for a save with no game_date (a slice)")
    p.set_defaults(fn=cmd_practices_fit)
    p = sub.add_parser("adopters")
    p.add_argument("saves", nargs="+")
    p.set_defaults(fn=cmd_adopters)
    p = sub.add_parser("fidelity")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--tolerance", type=float, default=0.02, help="census / model beyond 1 +/- this is off (0.02)")
    p.add_argument("--poverty-floor", type=float, help="the save's build's poverty term at SoL 5 (1: none, as main)")
    p.set_defaults(fn=cmd_fidelity)
    p = sub.add_parser("predict")
    p.add_argument("save", nargs="+")
    p.add_argument("--census-rates", action="store_true",
                   help="the save's own stored census rates (a save from the build under test), not the model's")
    p.add_argument("--slope", action="store_true", help="also print what the absorbed starving slope cost")
    p.add_argument("--to-year", type=int, default=1900, help="the gate's end year (default 1900)")
    p.add_argument("--check-modifiers", action="store_true",
                   help="probe P4: states whose census term has no matching te_demog_census_* modifier")
    p.add_argument("--json", action="store_true")
    p.add_argument("--year", type=int, help="the saves' year, for a save with no game_date (a slice)")
    p.set_defaults(fn=cmd_predict)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except S.NotPlainText as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
