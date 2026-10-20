#!/usr/bin/env python3
"""Phase 3's event wave: its thresholds, the script's figures as Python twins, and the fit.

docs/superpowers/specs/2026-10-08-demographics-design.md §9 names the ten events and their triggers; the script is
events/te_demog_wave_events.txt with common/script_values/te_demog_wave_values.txt (the thresholds, pinned here by
test_demographics_wave.py) and te_demog_wave_triggers.txt. §9 gives no bands, so this module states its own, as the
phase 2 harness does for its steps, and reports each honestly:

1. The 1836 reference structures (the agrarian reference, Britain 1836, a high-fertility 1975 structure) cross no
   threshold: no event greets a new game.
2. A fast demographic transition (1950s medicine, fertility falling from year 20) opens the Demographic Dividend and,
   at 20% unemployment, the Youth Bulge within its first forty years; the slow transition (fertility above four) does
   neither.
3. The Greying fires for today's oldest structures and not for today's average rich one (65+ at 18%, under the
   parent's 20%); without a pension law it reads the share past the old-age threshold at the bar fitted here: that
   share when 65+ first passes a fifth in the fast transition (greying_old_bar).
4. In the plain-text saves of an observer run (1900, 1904), each yearly event is due in a minority of census
   countries (BAND_SAVE_SHARE); the share and the countries are reported.

    demographics_wave.py [SAVE ...]          # the report (demographics_harness.py events is the same)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_save_inputs as S  # noqa: E402

# ---- The thresholds (te_demog_wave_values.txt; test_demographics_wave.py pins each) -------------------------------
DIVIDEND_REF = 0.566          # the 1836 agrarian reference structure's share aged 15-64 (dividend_reference)
DIVIDEND_RISE = 1.1           # §9: "passes the reference by 10%"
DIVIDEND_BAR = 0.623          # DIVIDEND_REF x DIVIDEND_RISE, rounded
GREYING_PENSIONERS = 0.2      # §9's "65+ passes 20%", read through the pension age (late-game §2.2)
GREYING_OLD = 0.14            # without a pension law: the share past the old-age threshold (greying_old_bar)
YOUTH_SHARE = 0.2             # §9: ages 20-29 above 20%
YOUTH_UNEMPLOYMENT = 0.1      # "and unemployment high": half of the youth bulge's full unemployment (P.YOUTH_UNEMPLOYMENT_FULL)
GIRLS_SRB = 110               # §9: the sex ratio at birth at 110 (Birth Limit's) or more
BRANCHES = 110                # §9: 110 men per 100 women (the census's 20-59 figure)
VILLAGES_FARM = 0.25          # a farm state: a quarter of its people Peasants or Farmers
VILLAGES_MEDIAN = 40          # old: a median age above a rich country's today (Rich today: 39)
VILLAGES_SHRINK = -0.005      # shrinking: half a percent a year
CROWDING = 4.5                # Migration Crowding's ceiling (the multiplier at ten times the reference density)
LOST_SHARE = 0.05             # §9: war dead above 5% of the men of fighting age
WAR_MEN = 0.95                # the census's share of war dead who are men (te_demog_flows)
BOOM_YEARS = 2                # §9: a war of two or more years
BOOM_DEAD = 0.01              # "with mass mobilisation": its dead a hundredth of the men of fighting age

OLD_BANDS = range(8, P.BANDS)     # the bands the share past the old-age threshold reads: 40-44 (OLD_AGE_FROM) and up
BAND_SAVE_SHARE = 0.25            # band 4: each yearly event due in under a quarter of a save's census countries
SAVE_MIN_PEOPLE = 1_000_000       # the census log's floor: smaller countries are listed apart

# The scenarios: the phase 2 step 4 structures (demographics_harness.CONSEQ_SCENARIOS) and Rich today.
REFERENCE_1836 = ("1836 agrarian (reference)", "Britain 1836", "India 1975")


def old_past_share(women, men, old_age):
    """The share of people past the old-age threshold from the five-year bands (te_demog_wave_old_past_share): each band
    from 40-44 counts the part of it past the threshold, people spread evenly, and 85+ counts as 85-89."""
    people = sum(women) + sum(men)
    if people <= 0:
        return 0.0
    past = 0.0
    for b in OLD_BANDS:
        frac = min(1.0, max(0.0, (P.BAND_WIDTH * (b + 1) - old_age) / P.BAND_WIDTH))
        past += (women[b] + men[b]) * frac
    return past / people


def ring_bands(ring):
    """(women, men) by five-year band, 85+ last, from a ring after its step."""
    women, men = [0.0] * P.BANDS, [0.0] * P.BANDS
    for a, f, m in ring.by_age():
        b = min(a // P.BAND_WIDTH, P.BANDS - 1)
        women[b] += f
        men[b] += m
    return women, men


def figures(ring, inp):
    """The wave's figures for a ring: working, old (65+), old_age, past_old, youth, sex_balance, median."""
    qf, qm, _ = M.group_rates(inp)
    old_age = M.old_age(qf, qm)
    s = M.structure(ring)
    women, men = ring_bands(ring)
    return {"working": s["working"], "old": s["old"], "old_age": old_age,
            "past_old": old_past_share(women, men, old_age), "youth": M.youth_share(ring),
            "sex_balance": s["men_per_100_women"], "median": s["median"]}


def due(fig, unemployment=0.2, pension=True):
    """The events a structure's figures would make due: dividend, greying, youth, branches. The Greying reads 65+ (the
    Standard pension age) with a pension law and the share past the old-age threshold without one."""
    out = []
    if fig["working"] >= DIVIDEND_BAR:
        out.append("dividend")
    if (fig["old"] >= GREYING_PENSIONERS) if pension else (fig["past_old"] >= GREYING_OLD):
        out.append("greying")
    if fig["youth"] > YOUTH_SHARE and unemployment >= YOUTH_UNEMPLOYMENT:
        out.append("youth")
    if fig["sex_balance"] >= BRANCHES:
        out.append("branches")
    return out


def scenario_rows(carriers=None):
    """[(name, tfr, figures)] for the step 4 structures (300 years at constant inputs) and Rich today."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for name, kw, low in H.CONSEQ_SCENARIOS:
        inp = H.scenario_inputs(carriers, low_share=low, **kw)
        ring, last = M.run_constant(inp, years=300)
        rows.append((name, last["tfr"], figures(ring, inp)))
    inp, ring, last = H.rich_today(carriers)
    rows.append(("Rich today (2020-like structure)", last["tfr"], figures(ring, inp)))
    return rows


def dividend_reference(carriers=None):
    """The 1836 agrarian reference structure's working-age share (design rule 5's reference)."""
    for name, _tfr, fig in scenario_rows(carriers):
        if name.startswith("1836 agrarian"):
            return fig["working"]
    raise LookupError("no 1836 agrarian scenario")


def transition_rows(carriers=None, years=120):
    """[(name, {event: first year due or None}, {figure: peak}, greying_bar)] for the step 4 transitions at 20%
    unemployment. greying_bar is the share past the old-age threshold in the year 65+ first reaches GREYING_PENSIONERS."""
    carriers = DM.load_carriers() if carriers is None else carriers
    base = H.scenario_inputs(carriers, sol=8, literacy=0.2, urban_share=0.1)
    rows = []
    for name, early, late, fall in H.CONSEQ_TRANSITIONS:
        ring, _ = M.run_constant(base, years=300)
        y0 = ring.year
        inp_early, inp_late = H.scenario_inputs(carriers, **early), H.scenario_inputs(carriers, **late)
        first = {"dividend": None, "youth": None, "greying": None, "greying_no_pension": None}
        peak = {"working": 0.0, "youth": 0.0, "old": 0.0}
        bar = None
        for t in range(1, years + 1):
            inp = inp_early if t < fall else inp_late
            M.step(ring, inp, y0 + t)
            fig = figures(ring, inp)
            for k in peak:
                peak[k] = max(peak[k], fig[k])
            for ev in due(fig):
                if first.get(ev) is None:
                    first[ev] = t
            if first["greying_no_pension"] is None and "greying" in due(fig, pension=False):
                first["greying_no_pension"] = t
            if bar is None and fig["old"] >= GREYING_PENSIONERS:
                bar = fig["past_old"]
        rows.append((name, first, peak, bar))
    return rows


def greying_old_bar(carriers=None):
    """The fitted bar without a pension law: the share past the old-age threshold in the year 65+ first passes a fifth
    in the fast transition (the one that ages), rounded to two decimals."""
    bars = [bar for _n, _f, _p, bar in transition_rows(carriers) if bar is not None]
    if not bars:
        raise LookupError("no transition reaches 65+ at a fifth")
    return round(bars[-1], 2)


# ---- A save's census countries ------------------------------------------------------------------------------------
COUNTRY_VARS = (("te_dg_census_year", "te_dg_stepped", "te_dg_working_share", "te_dg_old_share", "te_dg_old_age",
                 "te_dg_pensioners", "te_dg_sex_balance", "te_dg_urban_label", "te_dg_young_share")
                + tuple(f"te_dg_cb{s}{b}" for s in "fm" for b in range(P.BANDS)))
STATE_VARS = ("te_dg_people", "te_dg_urban", "migration_crowding_mult_applied", "te_dg_agr_share", "te_dg_median",
              "te_dg_walk_pop", "te_dg_walk_pop_prev", "te_dg_mt", "te_dg_year")


def save_rows(path, unemployment=True):
    """{tag: {people, due: [events], figures}} for a save's census countries (a save made under Full or Display only):
    the yearly events' conditions as the dispatcher reads them (te_demog_wave_triggers.txt), Missing Girls and the war's
    two left out (they need the live sex ratio at birth and the war tracker, which a save holds only in a war)."""
    countries, states = S.read_variables(path, COUNTRY_VARS, STATE_VARS)
    idle = S.state_unemployment(S.read_sections(path, wanted=("pops",))) if unemployment else {}
    by_owner = {}
    for sid, st in states.items():
        by_owner.setdefault(st["owner"], []).append((sid, st["vars"]))
    out = {}
    for cid, c in countries.items():
        v = c["vars"]
        if "te_dg_census_year" not in v or "te_dg_cbm0" not in v:
            continue
        women = [v.get(f"te_dg_cbf{b}", 0.0) for b in range(P.BANDS)]
        men = [v.get(f"te_dg_cbm{b}", 0.0) for b in range(P.BANDS)]
        people = sum(women) + sum(men)
        if people <= 0:
            continue
        ylo, yhi = P.YOUTH_AGES[0] // P.BAND_WIDTH, (P.YOUTH_AGES[1] + 1) // P.BAND_WIDTH
        youth = sum(women[b] + men[b] for b in range(ylo, yhi)) / people
        old_age = v.get("te_dg_old_age", 0.0)
        past_old = old_past_share(women, men, old_age) if old_age else 0.0
        pension = "law_old_age_pension" in c["laws"] and "te_dg_pensioners" in v
        greying = v.get("te_dg_pensioners", 0.0) if pension else past_old
        bar = GREYING_PENSIONERS if pension else GREYING_OLD
        own = by_owner.get(cid, [])
        pop = sum(sv.get("te_dg_people", 0.0) for _sid, sv in own) or 1.0
        idle_people = 0.0
        for sid, sv in own:
            total, none = idle.get(sid, (0.0, 0.0))
            idle_people += (none / total if total else 0.0) * sv.get("te_dg_people", 0.0)
        unemp = idle_people / pop
        due_now = []
        if v.get("te_dg_working_share", 0.0) >= DIVIDEND_BAR:
            due_now.append("dividend")
        if greying >= bar:
            due_now.append("greying")
        if youth > YOUTH_SHARE and unemp >= YOUTH_UNEMPLOYMENT:
            due_now.append("youth")
        if v.get("te_dg_sex_balance", 0.0) >= BRANCHES:
            due_now.append("branches")
        villages = [sid for sid, sv in own if sv.get("te_dg_agr_share", 0.0) >= VILLAGES_FARM
                    and sv.get("te_dg_median", 0.0) >= VILLAGES_MEDIAN and sv.get("te_dg_walk_pop_prev", 0.0) > 0
                    and (sv["te_dg_walk_pop"] - sv["te_dg_walk_pop_prev"]) / sv["te_dg_walk_pop_prev"]
                    <= VILLAGES_SHRINK]
        if villages:
            due_now.append("villages")
        # a Metropolis on its metropolitan share at Migration Crowding's ceiling (te_demog_wave_overspill_state)
        if any(sv.get("te_dg_mt", 0.0) >= P.MT_LABELS[0] and sv.get("migration_crowding_mult_applied", 0.0) >= CROWDING
               for _sid, sv in own if "te_dg_year" in sv):
            due_now.append("overspill")
        out[c["tag"] or cid] = {"people": people, "due": due_now,
                                "figures": {"working": v.get("te_dg_working_share", 0.0), "greying": greying,
                                            "pension": pension, "youth": youth, "unemployment": unemp,
                                            "sex_balance": v.get("te_dg_sex_balance", 0.0),
                                            "villages": len(villages)}}
    return out


def _band(ok):
    return "ok" if ok else "OUT"


def report(saves=(), unemployment=True):
    """Print the fit; return 0 when bands 1-3 hold (band 4 is reported, as the step 4 harness reports its saves)."""
    out = 0
    carriers = DM.load_carriers()
    print("The event wave's thresholds (te_demog_wave_values.txt): Dividend working share >= "
          f"{DIVIDEND_BAR} ({DIVIDEND_RISE} x {DIVIDEND_REF}); Greying pensioners >= {GREYING_PENSIONERS} "
          f"(no pension law: past the old-age threshold >= {GREYING_OLD}); Youth 20-29 > {YOUTH_SHARE} with "
          f"unemployment >= {YOUTH_UNEMPLOYMENT}; Bare Branches >= {BRANCHES} men per 100 women")
    rows = scenario_rows(carriers)
    print("\nThe model's structures:")
    for name, tfr, fig in rows:
        ev = due(fig) + (["greying (no pension law)"] if "greying" in due(fig, pension=False) else [])
        print(f"  {name:42s} tfr {tfr:4.2f}  15-64 {fig['working']:.3f}  65+ {fig['old']:.3f}  old age from "
              f"{fig['old_age']:4.1f}  past it {fig['past_old']:.3f}  20-29 {fig['youth']:.3f}  men/100 women "
              f"{fig['sex_balance']:5.1f}  due: {', '.join(ev) or 'none'}")
    ref = dividend_reference(carriers)
    ok = abs(ref - DIVIDEND_REF) < 0.0015
    out |= not ok
    print(f"\nThe Dividend's reference (the 1836 agrarian 15-64 share): {ref:.4f} against {DIVIDEND_REF}: {_band(ok)}")
    quiet = [n for n, _t, fig in rows if n in REFERENCE_1836 and (due(fig) or due(fig, pension=False))]
    out |= bool(quiet)
    print(f"Band 1, nothing due in the 1836 reference structures: {_band(not quiet)}"
          + (f" ({', '.join(quiet)})" if quiet else ""))
    trans = transition_rows(carriers)
    print("\nTransitions from the 1836 structure (20% unemployment):")
    for name, first, peak, bar in trans:
        print(f"  {name}: peaks 15-64 {peak['working']:.3f}, 20-29 {peak['youth']:.3f}, 65+ {peak['old']:.3f}; "
              "first due: " + ", ".join(f"{k} {'year ' + str(v) if v else 'never'}" for k, v in first.items())
              + (f"; past the old-age threshold when 65+ reaches {GREYING_PENSIONERS}: {bar:.3f}" if bar else ""))
    slow, fast = trans[0], trans[-1]
    ok2 = (fast[1]["dividend"] is not None and fast[1]["dividend"] <= 40 and fast[1]["youth"] is not None
           and fast[1]["youth"] <= 40 and slow[1]["dividend"] is None and slow[1]["youth"] is None)
    out |= not ok2
    print(f"Band 2, the fast transition opens the Dividend and the Youth Bulge within forty years and the slow one "
          f"neither: {_band(ok2)}")
    rich = {n: fig for n, _t, fig in rows}
    rich_stable = next(fig for n, fig in rich.items() if n.startswith("Rich, Protected"))
    rich_today = rich["Rich today (2020-like structure)"]
    bar = greying_old_bar(carriers)
    ok3 = ("greying" in due(rich_stable) and "greying" not in due(rich_today) and abs(bar - GREYING_OLD) < 0.005
           and "greying" in due(rich_stable, pension=False) and "greying" not in due(rich_today, pension=False))
    out |= not ok3
    print(f"Band 3, the Greying fires for the aged structure and not for today's average rich one, with and without a "
          f"pension law; the fitted bar without one {bar:.2f} against {GREYING_OLD}: {_band(ok3)}")
    for path in saves:
        rows = save_rows(path, unemployment=unemployment)
        year = H.save_year(path)
        big = {t: r for t, r in rows.items() if r["people"] >= SAVE_MIN_PEOPLE}
        print(f"\n{path} ({year}): {len(rows)} census countries, {len(big)} of a million people or more")
        if not big:
            continue
        for ev in ("dividend", "greying", "youth", "branches", "villages", "overspill"):
            tags = sorted(t for t, r in big.items() if ev in r["due"])
            share = len(tags) / len(big)
            print(f"  {ev:10s} due in {len(tags):3d} ({share:5.1%}) [band 4: under {BAND_SAVE_SHARE:.0%}: "
                  f"{_band(share < BAND_SAVE_SHARE)}]  {' '.join(tags[:24])}{' ...' if len(tags) > 24 else ''}")
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("saves", nargs="*", help="plain-text saves made under Full or Display only")
    ap.add_argument("--no-unemployment", action="store_true", help="skip the pops' unemployment (faster)")
    args = ap.parse_args(argv)
    return report(args.saves, unemployment=not args.no_unemployment)


if __name__ == "__main__":
    sys.exit(main())
