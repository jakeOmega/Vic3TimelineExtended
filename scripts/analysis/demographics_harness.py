#!/usr/bin/env python3
"""Offline harness for the demographics model (spec §11.1, §12 phase 0).

Usage:
    demographics_harness.py sketch                      # §2.2/§2.3's cases from the model
    demographics_harness.py inputs SAVE [--tag GBR]     # per-country inputs read from a save
    demographics_harness.py gini SAVE [--tag GBR]       # the panel's Gini, the bands' and pop by pop
    demographics_harness.py seed SAVE --tag GBR         # the seeded structure and life figures
    demographics_harness.py natural-change OLD NEW      # §14 Q10: world change vs the SoL curves
    demographics_harness.py replay DEBUG_LOG            # an in-game step against the model
    demographics_harness.py wc SAVE [--tag GBR] [--top 30]  # Wealth Concentration as the game holds it
    demographics_harness.py medicine                    # mortality anchors with the game files' values
    demographics_harness.py adopters SAVE [SAVE ...]    # health-law adopters against peers at their SoL
    demographics_harness.py fertility                   # children per woman with the game files' values
    demographics_harness.py history SAVE... --anchors CSV  # the model against history's e0, IMR and growth
    demographics_harness.py fidelity SAVE [--tag GBR]   # the model against the census's own stored multipliers

SAVE is a plain-text save (debug mode; a binary or zipped one is refused with exit 1).
The model is demographics_model.py with demographics_params.py; the generator writes the
script from the same two files, so a parameter tuned here reaches the game by
`python3 scripts/generators/gen_demographics.py`.

Calibration to world history (§2.3's targets) is not here yet: it needs an observer
run's yearly saves and belongs to phase 2's plan.
"""

import argparse
import dataclasses
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
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
    w = min(max(int(wealth), 1), P.INCOME_WEALTH_CAP)
    return costs[w]


def inputs_for(c, carriers=None, incorporated=True):
    """Model inputs for a save's country (as its incorporated states see them) or for one state
    (demographics_save_inputs.state_inputs; incorporated as the state is).

    The modifier totals come from the game files' carriers (demographics_modifiers) for the
    owner's techs, laws and institution levels. The wealth term is the pop-weighted curve,
    as the game computes it, not the curve at the mean SoL. Crowding (the state's migration penalty
    from migration_crowding) is a state's; a whole country's is 0, so `seed` and `adopters` leave it out.
    """
    carriers = DM.load_carriers() if carriers is None else carriers
    mods = DM.totals(carriers, c.techs, c.laws, c.institutions, incorporated=incorporated)
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share, techs=frozenset(c.techs),
                    laws=frozenset(c.laws), institutions=dict(c.institutions), wealth_tfr=c.wealth_tfr,
                    mods=mods, means_add=c.means_add, crowding=c.crowding)


def cmd_sketch(_args):
    for label, inp in SKETCH.items():
        ring, last = M.run_constant(inp, years=300)
        s = M.structure(ring)
        print(f"{label:28s} TFR {last['tfr']:.2f}  e0 {last['e0']:.1f}  e65 {last['e65']:.1f}  "
              f"IMR {last['q0_per_1000']:.0f}  0-14 {s['young']:.0%}  15-64 {s['working']:.0%}  "
              f"65+ {s['old']:.1%}  growth {last['growth']:+.2%}")
    return 0


def country_pops(sections, tag, costs):
    """[(people, wealth, strata, income)] for one country's pops, from raw pop records."""
    tags = {cid: r.get("definition", "").strip('"') for cid, r in sections["country_manager"].items()}
    owner = {sid: r.get("country") for sid, r in sections["states"].items()}
    out = []
    for r in sections["pops"].values():
        if tags.get(owner.get(r.get("location"))) != tag:
            continue
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        if size <= 0:
            continue
        wealth = S._num(r.get("wealth"), 1)
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
    each pop as its own group and the three strata the census used before 2026-10-10 (all computed)."""
    sections = S.read_sections(args.save)
    costs = buy_package_costs()
    inputs = S.country_inputs(sections)
    tags = args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]
    out = 0
    for t in tags:
        pops = country_pops(sections, t, costs)
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
    ("Rich today", dict(sol=40, literacy=0.99, urban_share=0.8, techs=MED_TODAY,
                        laws={PHI, "law_old_age_pension", "law_dedicated_police", "law_worker_protections"},
                        institutions={HEALTH: 8, "institution_workplace_safety": 5,
                                      "institution_ministry_of_consumer_protection": 4}),
     {"imr": (0, 6), "e0": (77, 84), "e65": (18, 23), "mmr": (0, 15)}),
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
    ("India 1975", dict(sol=9, literacy=0.35, urban_share=0.2, techs=MED_1950 | MEANS_TECHS | {"contraceptive_pill"},
                        laws={CHS}, institutions={HEALTH: 1}), (4.7, 5.8)),
]


def fertility_rows(carriers=None):
    """[(label, children per woman, low, high)] for FERTILITY_SCENARIOS, with the game files' values."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, kw, (lo, hi) in FERTILITY_SCENARIOS:
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


def country_figures(states, carriers):
    """A country's model figures as the census builds them: each state's own rates (its SoL, literacy,
    urban share and incorporation), weighted by its people. The poverty term bends at SoL 9, so the
    rates at the country's mean SoL would hide what its poor and rich states do (#855's review)."""
    figs = [(st.population, model_figures(inputs_for(st, carriers, incorporated=inc))) for _sid, st, inc in states
            if st.population > 0]
    tot = sum(p for p, _ in figs) or 1
    return {k: sum(p * f[k] for p, f in figs) / tot for k in ("e0", "imr", "tfr", "r")}


def history_rows(sections, year, anchors, carriers=None):
    """[(country, tag, people, model figures, anchors)] for each HISTORY_TAGS country in the save, the
    world line (every country of 1M people or more, weighted by people) and the mapped countries that
    have no anchor of any kind."""
    carriers = DM.load_carriers() if carriers is None else carriers
    states = S.state_inputs(sections)
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
        rows.append((country, tag, people[tag], country_figures(states[tag], carriers), hist))
    big = [(people[t], country_figures(sts, carriers)) for t, sts in states.items() if people[t] >= 1e6]
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
    for path in args.save:
        sections = S.read_sections(path)        # a binary or zipped save stops here (NotPlainText, exit 1)
        year = save_year(path) or args.year     # the save's own date first; --year fills in a slice
        if year is None:
            print(f"{path}: no game_date in its meta_data; give the year with --year", file=sys.stderr)
            return 1
        rows, world, bare = history_rows(sections, year, anchors, carriers)
        for country in bare:
            print(f"{country}: no anchors in {args.anchors}", file=sys.stderr)
        print(f"== {Path(path).name} ({year}): world (countries of 1M or more) e0 {world['e0']:.1f}  "
              f"children per woman {world['tfr']:.2f}  growth {world['r']:+.2f}% a year")
        for country, tag, people, got, hist in sorted(rows, key=lambda r: -r[2]):
            e = f"{hist['e0'][1]:.0f} ({hist['e0'][0]})" if hist["e0"] else "-"
            m = f"{hist['imr'][1]:.0f}" if hist["imr"] else "-"
            g = f"{hist['growth']:+.2f}%" if hist["growth"] is not None else "-"
            t = f"{hist['tfr'][1]:.1f}" if hist["tfr"] else "-"
            print(f"{tag:4s} {country:15s} {people / 1e6:6.1f}M  model e0 {got['e0']:4.1f} imr {got['imr']:4.0f} "
                  f"tfr {got['tfr']:.2f} growth {got['r']:+.2f}%   history e0 {e:10s} imr {m:4s} tfr {t:4s} people {g}")
    return 0


HEALTH_LAWS = ("law_charitable_health_system", "law_private_health_insurance", "law_public_health_insurance")


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
FIDELITY_VARS = ("te_dg_sol", "te_dg_lit") + tuple(var for _c, var, _s in FIDELITY_CAUSES)


def fidelity_rows(path, carriers=None, tags=()):
    """[(tag, state id, people, {cause: (census, model)}, (SoL: save, walk), (literacy: save, walk))] for each state
    the census has walked. The model runs on the walk's own SoL and literacy (te_dg_sol, te_dg_lit) with the save's
    techs, laws, institutions and crowding, so a cause that differs is a term the harness doesn't read (the crowding
    term was one, 2026-10-10) or an input that changed after the state's last step (a new tech or law)."""
    carriers = DM.load_carriers() if carriers is None else carriers
    _countries, walked = S.read_variables(path, (), FIDELITY_VARS)
    rows = []
    for tag, states in S.state_inputs(S.read_sections(path)).items():
        if tags and tag not in tags:
            continue
        for sid, st, inc in states:
            got = walked.get(sid, {}).get("vars", {})
            if "te_dg_m_inf" not in got or st.population <= 0:
                continue
            inp = dataclasses.replace(inputs_for(st, carriers, incorporated=inc),
                                      sol=got.get("te_dg_sol", st.sol), literacy=got.get("te_dg_lit", st.literacy))
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
    rows = fidelity_rows(args.save, tags=set(args.tag))
    if not rows:
        which = f" in {', '.join(sorted(args.tag))}" if args.tag else ""
        print(f"{args.save}: no state the census has walked{which} (no te_dg_m_inf)", file=sys.stderr)
        return 1
    people = sum(r[2] for r in rows)
    print(f"{len(rows)} states the census has walked, {people / 1e6:,.1f}M people. A cause is off where the census's "
          f"multiplier is more than {args.tolerance:.0%} from the model's on the walk's own SoL and literacy.")
    print(f"The model has the poverty term at x{P.POVERTY_INFECTION_AT_FLOOR:g} (SoL {P.POVERTY_INFECTION_FLOOR_SOL}); "
          f"a save from a build with another shows it as off below SoL {P.POVERTY_INFECTION_SOL} "
          f"(--poverty-floor 1 for one from before the poverty term).")
    print("Crowding is the continuous term (infection + the state's migration penalty); a save from main's x1.15 switch "
          "shows crowded states' infection as off.")
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
    sub.add_parser("fertility").set_defaults(fn=cmd_fertility)
    p = sub.add_parser("history")
    p.add_argument("save", nargs="+")
    p.add_argument("--anchors", required=True, help="fetch_history_anchors.py's CSV")
    p.add_argument("--year", type=int, help="the saves' year, for a save with no game_date (a slice)")
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser("adopters")
    p.add_argument("saves", nargs="+")
    p.set_defaults(fn=cmd_adopters)
    p = sub.add_parser("fidelity")
    p.add_argument("save")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--tolerance", type=float, default=0.02, help="census / model beyond 1 +/- this is off (0.02)")
    p.add_argument("--poverty-floor", type=float, help="the save's build's poverty term at SoL 5 (1: none, as main)")
    p.set_defaults(fn=cmd_fidelity)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except S.NotPlainText as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
