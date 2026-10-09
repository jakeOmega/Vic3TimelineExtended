#!/usr/bin/env python3
"""Offline harness for the demographics model (spec §11.1, §12 phase 0).

Usage:
    demographics_harness.py sketch                      # §2.2/§2.3's cases from the model
    demographics_harness.py inputs SAVE [--tag GBR]     # per-country inputs read from a save
    demographics_harness.py gini SAVE [--anchor-tag GBR --anchor 0.52]
    demographics_harness.py seed SAVE --tag GBR         # the seeded structure and life figures
    demographics_harness.py natural-change OLD NEW      # §14 Q10: world change vs the SoL curves
    demographics_harness.py replay DEBUG_LOG            # an in-game step against the model
    demographics_harness.py wc SAVE [--tag GBR] [--top 30]  # Wealth Concentration as the game holds it

SAVE is a plain-text save (debug mode; a binary or zipped one is refused with exit 1).
The model is demographics_model.py with demographics_params.py; the generator writes the
script from the same two files, so a parameter tuned here reaches the game by
`python3 scripts/generators/gen_demographics.py`.

Calibration to world history (§2.3's targets) is not here yet: it needs an observer
run's yearly saves and belongs to phase 2's plan.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_model as M  # noqa: E402
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


def inputs_for(c):
    """Model inputs for a save's country.

    No institutions or modifiers: the reader doesn't read them. The wealth term is the
    pop-weighted curve, as the game computes it, not the curve at the mean SoL.
    """
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share,
                    techs=frozenset(c.techs), laws=frozenset(c.laws), wealth_tfr=c.wealth_tfr)


def cmd_sketch(_args):
    for label, inp in SKETCH.items():
        ring, last = M.run_constant(inp, years=300)
        s = M.structure(ring)
        print(f"{label:28s} TFR {last['tfr']:.2f}  e0 {last['e0']:.1f}  e65 {last['e65']:.1f}  "
              f"IMR {last['q0_per_1000']:.0f}  0-14 {s['young']:.0%}  15-64 {s['working']:.0%}  "
              f"65+ {s['old']:.1%}  growth {last['growth']:+.2%}")
    return 0


def country_groups(sections, tag, costs):
    """[(people, income)] by strata for one country, from raw pop records."""
    tags = {cid: r.get("definition", "").strip('"') for cid, r in sections["country_manager"].items()}
    owner = {sid: r.get("country") for sid, r in sections["states"].items()}
    acc = {}
    for r in sections["pops"].values():
        if tags.get(owner.get(r.get("location"))) != tag:
            continue
        size = S._num(r.get("workforce")) + S._num(r.get("dependents"))
        if size <= 0:
            continue
        strata = S.STRATA_OF_CLASS.get(r.get("social_class"), "lower")
        n, y = acc.get(strata, (0.0, 0.0))
        acc[strata] = (n + size, y + size * income_proxy(S._num(r.get("wealth"), 1), costs))
    return list(acc.values())


def cmd_gini(args):
    sections = S.read_sections(args.save)
    costs = buy_package_costs()
    inputs = S.country_inputs(sections)
    tags = args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]
    groups = {t: country_groups(sections, t, costs) for t in set(tags) | {args.anchor_tag}}
    if not groups[args.anchor_tag]:
        print(f"no pops for anchor tag {args.anchor_tag} in {args.save}", file=sys.stderr)
        return 1
    grouped = {t: M.grouped_gini(g) for t, g in groups.items()}
    anchor = grouped[args.anchor_tag]
    if anchor <= 0:
        print(f"anchor tag {args.anchor_tag} has a grouped Gini of 0 (one stratum or equal incomes): "
              "no scale reaches the anchor", file=sys.stderr)
        return 1
    scale = (args.anchor - P.GINI_FLOOR) / anchor
    print(f"GINI_SCALE for {args.anchor_tag} = {args.anchor}: {scale:.2f} (params: {P.GINI_SCALE})")
    for t in tags:
        shown = M.clamp(P.GINI_FLOOR + scale * grouped[t], 0, 0.9)
        print(f"{t} grouped {grouped[t]:.3f} shown {shown:.2f}")
    return 0


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
    p.add_argument("--anchor-tag", default="GBR")
    p.add_argument("--anchor", type=float, default=0.52)
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
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except S.NotPlainText as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
