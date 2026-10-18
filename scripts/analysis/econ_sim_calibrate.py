"""Calibration and the hindcast check for the economy growth sim (issue #1034).

WHY THIS EXISTS
---------------
The sim's free parameters (spec 7) are fitted to the owner's France -> EU playthrough,
`econ_series_c480d386.json`, so that a lever sweep starts from an economy that looks
like the game's. The rules are shared: players and the AI differ only in behaviour
(spec 6). So:

  STRUCTURAL   fitted on player_rich only, then shared by every scenario
  BEHAVIOUR    fitted per scenario with the structural values held, plus the
               automation lag for the AI scenarios

`fit` is coordinate descent: each round tries each name at x0.5, x0.8, x1.25 and x2.0 of
its value and keeps the best of those if it lowers the loss. `loss` is the squared error,
weight 1 each, at every save after the start: peasant share, unemployed share, ln GDP per
head, ln population, ln construction points a week, and ln wage (the sim's base-price wage
x price_level against the saves' nominal one).

The saves were played under the construction cost curve of the time (D.HISTORICAL_CURVE,
ruling R37), not the mod's current one, so every run here simulates the history under it:
`historical_md` swaps it into the ModData that `fit`, `starts` and `check` run with. What
`econ_growth_sim.py run` and `sweep` use is the mod's own curve, unchanged.

The hindcast is a manual check, not a unit test: it runs on live mod values, so a PR that
retunes a PM, a cost tier or a cap technology could move it. Run `check` after a mod change
worth re-checking. A miss is a finding about the model, for the owner; the bands are not
to be widened to pass.

USAGE
-----
    PY=.venv/bin/python                         # from the repo root
    $PY scripts/analysis/econ_sim_calibrate.py fit \\
        --scenario player_rich --scenario ai_rich --scenario ai_poor \\
        --out scripts/analysis/econ_sim_params.json
    $PY scripts/analysis/econ_sim_calibrate.py check      # exits 1 on any miss
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# Direct CLI execution starts with scripts/analysis on sys.path.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from scripts.analysis import econ_growth_sim as G  # noqa: E402
from scripts.analysis import econ_sim_data as D  # noqa: E402
from scripts.analysis import econ_sim_scenarios as SC  # noqa: E402

PARAMS = G.PARAMS

STRUCTURAL = ("fill_rate", "wage_step", "wage_decay", "vacancy_target", "wage_floor", "return_rate", "price_level",
              "services_jobs_per_gdp", "demand_gdp_ratio", "g_max", "g_slope", "workforce_share",
              "construction_good_price")
BEHAVIOUR = ("private_invest_share", "gov_invest_share", "queue_per_state")
AI_BEHAVIOUR = BEHAVIOUR + ("automation_lag_years",)
FITTED = ("player_rich", "ai_rich", "ai_poor")  # player_poor and player_union take player_rich's behaviour

STEPS = (0.5, 0.8, 1.25, 2.0)
MAX_ROUNDS = 300                                # the CLI's cap; on this dataset fits converge in 3 to 52 rounds
# Shares and rates a year can't pass 1: the step clamps hiring at the open jobs, and a
# wage decay, return rate or share above 1 would overshoot.
UPPER = {"fill_rate": 1.0, "wage_decay": 1.0, "return_rate": 1.0, "workforce_share": 1.0,
         "vacancy_target": 1.0, "private_invest_share": 1.0, "gov_invest_share": 1.0}
TINY = 1e-9                                     # ln guard: a sim figure at or below 0 scores as ln(TINY)
SIG_FIGS = 6                                    # fitted values are written to this many significant figures

# The hindcast bands (spec 7 step 3, spec 3 goal 4, the owner's factor of 2).
SHARE_BAND = 0.10                               # peasant and unemployed share, player_rich
AI_SHARE_BAND = 0.15                            # ... ai_rich and ai_poor
RATIO_BAND = (0.5, 2.0)                         # population, GDP per head and wage, sim / saves
UNION_BAND = 0.10                               # player_union: the last point's peasant share

FIGURES = ("peasant_share", "unemployed_share", "gdppc", "population", "points_week", "wage")


# --------------------------------------------------------------------------
# The curve the history ran under
# --------------------------------------------------------------------------


def historical_md(md: D.ModData) -> D.ModData:
    """`md` with the construction cost curve of the playthrough (D.HISTORICAL_CURVE), for
    simulating the history; every other number stays the mod's. `md` isn't changed."""
    return dataclasses.replace(md, numbers=dataclasses.replace(md.numbers, curve=D.HISTORICAL_CURVE))


# --------------------------------------------------------------------------
# Targets and loss
# --------------------------------------------------------------------------


def targets(sc: SC.Scenario, dataset: dict) -> list[dict]:
    """Per point of the scenario's series after the start: {year (fractional), peasant_share,
    unemployed_share, gdppc, population, points_week, wage}. People and the wage are the
    point's slice; gdppc and points a week (already scaled to the slice) its owner's."""
    out = []
    for pt in dataset["series"][sc.series]["points"][1:]:
        sl, owner = pt["slice"], pt["owner"]
        wf = sl["workforce"]
        out.append({
            "year": SC.point_year(pt["date"]),
            "peasant_share": sl["peasants"] / wf if wf > 0 else 0.0,
            "unemployed_share": sl["unemployed"] / wf if wf > 0 else 0.0,
            "gdppc": owner["gdppc"],
            "population": sl["population"],
            "points_week": sum(owner["points_weekly"].values()),
            "wage": sl["wage_per_worker"],
        })
    return out


def _figures(r: G.YearRecord) -> dict[str, float]:
    wf = r.workforce
    return {
        "peasant_share": r.peasants / wf if wf > 0 else 0.0,
        "unemployed_share": r.unemployed / wf if wf > 0 else 0.0,
        "gdppc": r.gdppc,
        "population": r.population,
        "points_week": r.points / 52.0,
        "wage": r.wage,                         # base prices
    }


RECORD_AT = 1.0                                 # a YearRecord's stocks are the end of its year: Y sits at Y + 1.0


def sim_at(records: list[G.YearRecord], year: float) -> dict[str, float]:
    """The FIGURES at a fractional `year`, linear between the records either side; flat
    past either end. A record holds its year's end-of-year stocks (`step` leaves them so),
    so record Y sits at Y + RECORD_AT, the first of January of Y + 1, where a save dated
    then would read them. Records are consecutive years, as `run` returns them."""
    at = year - RECORD_AT                       # in record years
    if at <= records[0].year:
        return _figures(records[0])
    if at >= records[-1].year:
        return _figures(records[-1])
    i = int(math.floor(at)) - records[0].year
    a, b = _figures(records[i]), _figures(records[i + 1])
    frac = at - records[i].year
    return {k: a[k] + (b[k] - a[k]) * frac for k in FIGURES}


def _ln(x: float) -> float:
    return math.log(max(x, TINY))


def loss(records: list[G.YearRecord], targets: list[dict], p: G.Params) -> float:
    """Sum over targets of the squared error, weight 1 each, in peasant share, unemployed
    share, ln GDP per head, ln population, ln points a week, and ln(sim wage x price_level)
    against ln observed wage. Records are interpolated to each target's year."""
    total = 0.0
    for t in targets:
        s = sim_at(records, t["year"])
        total += (s["peasant_share"] - t["peasant_share"]) ** 2
        total += (s["unemployed_share"] - t["unemployed_share"]) ** 2
        for key in ("gdppc", "population", "points_week"):
            total += (_ln(s[key]) - _ln(t[key])) ** 2
        total += (_ln(s["wage"] * p.price_level) - _ln(t["wage"])) ** 2
    return total


# --------------------------------------------------------------------------
# Fitting
# --------------------------------------------------------------------------


def fit(sc: SC.Scenario, dataset: dict, md: D.ModData, p0: G.Params, names, rounds: int = 4, log=None) -> G.Params:
    """Coordinate descent from `p0` over `names`. Each round, for each name in turn, tries the
    value at x STEPS (capped at UPPER) and keeps the best candidate if it lowers the loss.
    Stops early after a round that changes nothing. A value of 0 can't move (seed it
    first); None raises ValueError. `p0` isn't changed. `log`, if given, is called with each
    round's (round, loss). The runs use the historical curve (`historical_md`)."""
    md = historical_md(md)
    t = targets(sc, dataset)

    def score(p: G.Params) -> float:
        return loss(G.run(sc, md, p), t, p)

    best_p, best = p0, score(p0)
    for rnd in range(1, rounds + 1):
        start_p = best_p
        for name in names:
            value = getattr(best_p, name)
            if value is None:
                raise ValueError(name + " is None; give it a starting value to fit it")
            trial_p, trial = best_p, best
            for m in STEPS:
                v = min(value * m, UPPER.get(name, math.inf))
                if v == value:
                    continue
                cand = dataclasses.replace(best_p, **{name: v})
                c = score(cand)
                if c < trial:
                    trial_p, trial = cand, c
            best_p, best = trial_p, trial
        if log is not None:
            log(rnd, best)
        if best_p == start_p:                   # converged: every later round would repeat this one
            break
    return best_p


def starts(sc: SC.Scenario, md: D.ModData) -> dict[str, G.Params]:
    """The starting points of player_rich's fit. The loss surface has many local minima (the
    model's floors, caps and mode switches make it rugged), so the fit runs from each and
    keeps the lowest loss.

      defaults             Params(), with services_jobs_per_gdp at the start's demand-bound
                           employees over its GDP net of the demand ratio (a 0 can't move
                           under multiplicative steps)
      gap_in_demand_ratio  the same, with the gap between the start's GDP and a one-year run's
                           carried by demand_gdp_ratio
      gap_in_price_level   ... carried by price_level instead (which also deflates the wage)

    The one-year run uses the historical curve (`historical_md`).
    """
    md = historical_md(md)
    p = G.Params()
    gdp_level = sc.gdp / (1.0 + p.demand_gdp_ratio)
    p = dataclasses.replace(p, services_jobs_per_gdp=sc.employed_demand / gdp_level if gdp_level > 0 else 0.0)
    one = G.run(dataclasses.replace(sc, end_year=sc.start_year), md, p)[0]
    gap = sc.gdp / one.gdp if one.gdp > 0 else 1.0
    return {
        "defaults": p,
        "gap_in_demand_ratio": dataclasses.replace(p, demand_gdp_ratio=(1.0 + p.demand_gdp_ratio) * gap - 1.0),
        "gap_in_price_level": dataclasses.replace(p, price_level=gap),
    }


def _best_fit(sc, dataset, md, candidates: dict[str, G.Params], names, rounds: int, label: str) -> G.Params:
    """`fit` from each candidate start; the lowest loss wins (the first on a tie)."""
    t = targets(sc, dataset)
    best = None
    for start, p0 in candidates.items():
        used = [0]
        p = fit(sc, dataset, md, p0, names, rounds, log=lambda rnd, _value: used.__setitem__(0, rnd))
        value = loss(G.run(sc, md, p), t, p)
        print(f"  {label} from {start}: loss {loss(G.run(sc, md, p0), t, p0):.4f} -> {value:.4f} ({used[0]} rounds)")
        if best is None or value < best[0]:
            best = (value, start, p)
    print(f"  {label}: kept the fit from {best[1]}, loss {best[0]:.4f}")
    return best[2]


def _sig(v: float) -> float:
    return float(f"{v:.{SIG_FIGS}g}")


# --------------------------------------------------------------------------
# The hindcast check
# --------------------------------------------------------------------------


def _miss_lines(name: str, sc: SC.Scenario, records, p: G.Params, dataset: dict) -> list[str]:
    band = AI_SHARE_BAND if sc.kind == "ai" else SHARE_BAND
    lo, hi = RATIO_BAND
    out = []
    points = dataset["series"][sc.series]["points"][1:]
    for pt, t in zip(points, targets(sc, dataset)):
        s = sim_at(records, t["year"])
        where = name + " " + pt["date"]
        for key in ("peasant_share", "unemployed_share"):
            off = s[key] - t[key]
            if abs(off) > band:
                out.append(f"{where} {key}: sim {s[key]:.3f}, saves {t[key]:.3f}, off {off:+.3f} (band {band:.2f})")
        for key, sim_value in (("population", s["population"]), ("gdppc", s["gdppc"]),
                               ("wage", s["wage"] * p.price_level)):
            ratio = sim_value / t[key] if t[key] > 0 else math.nan
            if not lo <= ratio <= hi:
                out.append(f"{where} {key}: sim {sim_value:.4g}, saves {t[key]:.4g}, x{ratio:.2f} "
                           f"(band x{lo:g}-x{hi:g})")
    return out


def check(dataset: dict, md: D.ModData, params_path: Path | str = PARAMS) -> list[str]:
    """The hindcast bands; one line per miss, an empty list for a pass.

    At every target of player_rich, ai_rich and ai_poor: peasant or unemployed share off by
    more than SHARE_BAND (AI_SHARE_BAND for the AI), or population, GDP per head or the
    nominal wage outside RATIO_BAND of the saves'. For player_union: the last point's
    peasant share within UNION_BAND. The runs use the historical curve (`historical_md`).
    """
    md = historical_md(md)
    misses = []
    for name in FITTED:
        sc = SC.scenario(name, dataset, md)
        p = G.params_for(name, params_path)
        misses.extend(_miss_lines(name, sc, G.run(sc, md, p), p, dataset))
    sc = SC.scenario("player_union", dataset, md)
    p = G.params_for("player_union", params_path)
    last_pt, last = dataset["series"]["union"]["points"][-1], targets(sc, dataset)[-1]
    s = sim_at(G.run(sc, md, p), last["year"])
    off = s["peasant_share"] - last["peasant_share"]
    if abs(off) > UNION_BAND:
        misses.append(f"player_union {last_pt['date']} peasant_share: sim {s['peasant_share']:.3f}, "
                      f"saves {last['peasant_share']:.3f}, off {off:+.3f} (band {UNION_BAND:.2f})")
    return misses


# --------------------------------------------------------------------------
# Reports and the CLI
# --------------------------------------------------------------------------


def table(sc: SC.Scenario, records, p: G.Params, dataset: dict) -> str:
    """Saves against the sim at every target, markdown; the wage is nominal (sim x price_level)."""
    head = ("| date | peasants saves / sim | unemployed saves / sim | GDP per head saves / sim "
            "| population (M) saves / sim | points a week saves / sim | wage saves / sim |")
    rows = [head, "|" + "---|" * 7]
    points = dataset["series"][sc.series]["points"][1:]
    for pt, t in zip(points, targets(sc, dataset)):
        s = sim_at(records, t["year"])
        rows.append(
            f"| {pt['date']} | {t['peasant_share']:.3f} / {s['peasant_share']:.3f} "
            f"| {t['unemployed_share']:.3f} / {s['unemployed_share']:.3f} "
            f"| {t['gdppc']:.2f} / {s['gdppc']:.2f} "
            f"| {t['population'] / 1e6:.1f} / {s['population'] / 1e6:.1f} "
            f"| {t['points_week']:.0f} / {s['points_week']:.0f} "
            f"| {t['wage']:.3f} / {s['wage'] * p.price_level:.3f} |")
    return "\n".join(rows)


def _fit_main(args) -> int:
    """player_rich: coordinate descent over STRUCTURAL and BEHAVIOUR together, from each of
    `starts`, to convergence; the lowest loss gives the structural values and player_rich's
    behaviour. Its result is a fixed point of both halves of the brief's order (structural
    with behaviour held, behaviour with structural held), which the 4-round sequential
    order alone doesn't reach. Each other scenario: its behaviour (and, for the AI, the
    automation lag) with the structural values held, from the defaults and from
    player_rich's behaviour, the lowest loss kept."""
    md, ds = historical_md(D.load_mod_data()), SC.load_dataset()
    names = args.scenario or list(FITTED)
    out = Path(args.out)
    existing = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    behaviour = dict(existing.get("behaviour", {}))

    if "player_rich" in names:
        sc = SC.scenario("player_rich", ds, md)
        p = _best_fit(sc, ds, md, starts(sc, md), STRUCTURAL + BEHAVIOUR, args.rounds, "player_rich")
        structural = {n: _sig(getattr(p, n)) for n in STRUCTURAL}
        behaviour["player_rich"] = {n: _sig(getattr(p, n)) for n in BEHAVIOUR}
        stale = sorted(set(behaviour) - set(names))
        if stale:
            print("note: structural values refitted; behaviour not refitted for " + ", ".join(stale))
    elif "structural" in existing:
        structural = existing["structural"]
    else:
        print(f"{out} has no structural values: fit player_rich first", file=sys.stderr)
        return 2

    base = dataclasses.replace(G.Params(), **structural)
    for name in names:
        if name == "player_rich":
            continue
        sc = SC.scenario(name, ds, md)
        fit_names = AI_BEHAVIOUR if sc.kind == "ai" else BEHAVIOUR
        lag = {"automation_lag_years": sc.automation_lag_years} if sc.kind == "ai" else {}
        candidates = {"defaults": dataclasses.replace(base, **lag),
                      "player_rich's behaviour": dataclasses.replace(base, **behaviour.get("player_rich", {}), **lag)}
        p = _best_fit(sc, ds, md, candidates, fit_names, args.rounds, name)
        behaviour[name] = {n: _sig(getattr(p, n)) for n in fit_names}

    out.write_text(json.dumps({"structural": structural, "behaviour": behaviour}, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}\n")
    for name in names:
        sc = SC.scenario(name, ds, md)
        p = G.params_for(name, out)
        records = G.run(sc, md, p)
        print(f"## {name}: loss {loss(records, targets(sc, ds), p):.4f}\n")
        print(table(sc, records, p, ds) + "\n")
    return 0


def _check_main(args) -> int:
    misses = check(SC.load_dataset(), D.load_mod_data(), params_path=args.params)
    for line in misses:
        print(line)
    print(f"{len(misses)} miss(es)" if misses else "hindcast: pass")
    return 1 if misses else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fit", help="fit the parameters and write them")
    f.add_argument("--scenario", action="append", choices=FITTED,
                   help="a scenario to fit (repeatable; default all three). player_rich also refits the structural values")
    f.add_argument("--out", default=str(PARAMS), help="the parameter file to write (default %(default)s)")
    f.add_argument("--rounds", type=int, default=MAX_ROUNDS,
                   help="most coordinate-descent rounds a fit; it stops once a round changes nothing (default %(default)s)")
    c = sub.add_parser("check", help="run the hindcast bands; exit 1 on any miss")
    c.add_argument("--params", default=str(PARAMS), help="the parameter file (default %(default)s)")
    args = ap.parse_args(argv)
    return _fit_main(args) if args.command == "fit" else _check_main(args)


if __name__ == "__main__":
    sys.exit(main())
