"""The reported deflation trap, run through the banking-cycle simulator (§0.12).

A Digital Currency country with its policy rate on the -3% floor, headline
inflation at -6.6%, core -4.2 under a -2.4 cost-push drag, expectations at
-4.9, 0.9pp of wage pressure absorbed by nine National Bank levels, and the
financial cycle held at 50. docs/systems/monetary_policy_design.md §0.12 and
docs/audits/banking_cycle_simulation.md §15 quote both tables this prints:

* headline inflation at the end of each of the first six years, with the
  inflation noise held at zero, before (`--tune pre_bank_qe`) and after;
* the same start with the noise on, over many seeds: how often the bank's own
  purchases switch on or off, the largest one-month change in them, and how
  long headline takes to reach 0%;
* a delegated bank without independence that also monetises the deficit
  (ruling N1): what the bank's purchases add on top of Monetise Deficit. The
  simulator does not model monetisation, so its inflation side is added here
  as te_mon_monetisation_pressure per level; its risk premium and minting are
  not modelled;
* the playtest that raised the cap (§0.12, "The cap"): an independent Digital
  country on Growth, in a Panic, headline on the -10% clamp, expectations at
  -9.1, a currency at 125.3 importing -2.6 points, Open-Market Operations,
  Credit to Electrification and Bail-in on. The cycle RUNS here, and an
  exchange-rate loop the simulator otherwise leaves out is added (CurrencyLoop
  below, after te_monetary_fx_script_values.txt). Core under the pinned
  headline is not shown in game; -8.5 is assumed. The rows compare the cap
  (2.5 before the playtest, 5 after) and the confidence term (two-sided before,
  one-sided for a float after).

* with --ordinary-runs N: ordinary centuries of floating (fiat, digital)
  countries with the same currency loop switched on (cyclical premium 0, world
  inflation 2), the confidence term two-sided against one-sided. The century
  simulator itself holds the exchange rate at par, so this is the only read of
  what the one-sided term does outside a trap.

Usage:
    python3 scripts/analysis/banking_deflation_trap.py [--runs 200] [--playtest-runs 60] [--playtest-only]
                                                       [--ordinary-runs 30]
"""
import argparse
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.analysis import banking_cycle_sim as sim  # noqa: E402

CBI = "law_central_bank_independence"
DELEGATED = "law_universal_banking_light_prudence"
PREVIOUS_CAP = 2.5  # te_mon_bank_qe_cap before the playtest
# Before the same playtest the confidence term also rewarded a floating currency
# for deflating: `two_sided=True` reproduces that.


class CurrencyLoop:
    """te_fx_imported for a floating currency, after te_monetary_fx_script_values.txt.

    target = par + rate term + inflation term + premium term. The rate term is
    4 x clamp(policy - expected - world rate, +-5), its positive side halved by
    Restrict Speculative Inflows; the confidence term -2 x clamp(expected - world
    inflation, 0, 10), one-sided as te_mon_fx_term_confidence is for a float
    (`two_sided=True`: the -10 to 10 it was before); the premium term -1.5 x the
    cyclical premium, held here at the playtest's 4.5. The index closes 1/12 of
    the gap a month, and imports 0.15 x (three-year average - index), the
    average moving 0.0278 of the gap.
    """

    def __init__(self, index, imported, *, premium=4.5, world_inflation=2.0, two_sided=False):
        self.index = index
        self.avg = index + imported / 0.15  # so that it imports `imported` this month
        self.premium = premium
        self.world_inflation = world_inflation
        self.two_sided = two_sided

    def __call__(self, cfg, state, world_rate):
        rate = max(-5.0, min(5.0, state.policy_rate - state.inflation_expected - world_rate))
        if rate > 0 and "restrict_inflows" in state.tools:
            rate *= 0.5
        target = 100 + 4 * rate - 1.5 * max(0.0, self.premium)
        gap = max(-10.0, min(10.0, state.inflation_expected - self.world_inflation))
        target -= 2 * (gap if self.two_sided else max(0.0, gap))
        self.index = max(50.0, min(150.0, self.index + (target - self.index) / 12))
        imported = (self.avg - self.index) * 0.15
        self.avg += (self.index - self.avg) * 0.0278
        return imported


def playtest(seed, *, mode=sim.MODE_GROWTH, cap=None, tools=("omo", "dc_elec", "bail_in"),
             currency_loop=True, two_sided=False, months=120):
    """The playtest's country from its screenshot, cycle running; `cap` overrides te_mon_bank_qe_cap."""
    sv, imported = sim.K.sv, sim.fx_imported
    if cap is not None:
        sim.K.sv = lambda name: cap if name == "te_mon_bank_qe_cap" else sv(name)
    if currency_loop:
        sim.fx_imported = CurrencyLoop(125.3, -2.6, two_sided=two_sided)
    sim.TUNE.clear()
    try:
        cfg = sim.Config(currency="digital", mode=mode, points=8, ai_tools=False, fin_law=CBI,
                         wage_pressure=0.9, bank_level=9)
        st = sim.State(policy_rate=-3.0, policy_rate_target=-3.0, inflation=-10.0,
                       inflation_core=-8.5, inflation_expected=-9.1, neutral_rate=3.0,
                       finance_cycle_value=6.0, bubble_pressure=5.0)
        st.virtual_rate = st.virtual_target = -5.5  # buying at the old cap, as in the screenshot
        st.tools = set(tools)
        st.basket_seeded = True
        rng = random.Random(seed)
        off_clamp = at_zero = None
        peak, late = -100.0, []
        for month in range(1, months + 1):
            sim.advance_exogenous(cfg, st, rng, month)
            st.deficit_pct = 0.0
            sim.cycle_pulse(cfg, st, rng, month)
            sim.monetary_update(cfg, st, rng, month // 12)
            if off_clamp is None and st.inflation > -9.95:
                off_clamp = month
            if at_zero is None and st.inflation >= 0:
                at_zero = month
            if at_zero is not None and month <= at_zero + 36:
                peak = max(peak, st.inflation)
            if month > months - 36:
                late.append(st.inflation)
    finally:
        sim.K.sv, sim.fx_imported = sv, imported
    return dict(off_clamp=off_clamp, at_zero=at_zero, peak=peak if at_zero else None,
                late=statistics.mean(late))


def run(seed, currency, fin_law, mode, *, noise=True, omo=False, months=120, tune=None, monetise=0):
    """One trapped country: switches, largest change, month at 0%, yearly headline and more."""
    sim.TUNE.clear()
    sim.TUNE.update(tune or {})
    pressure_total = sim.pressure_total
    if monetise:
        per_level = sim.K.sv("te_mon_monetisation_pressure")
        sim.pressure_total = lambda cfg, st, wr: pressure_total(cfg, st, wr) + per_level * monetise
    cfg = sim.Config(currency=currency, mode=mode, points=8, fin_law=fin_law,
                     wage_pressure=0.9, bank_level=9)
    floor = sim.target_bounds(cfg, sim.State(), 3.0)[0]
    st = sim.State(policy_rate=floor, policy_rate_target=floor, inflation=-6.6,
                   inflation_core=-4.2, inflation_expected=-4.9, neutral_rate=3.0,
                   basket_index=0.92, basket_avg=1.0)
    st.basket_seeded = True
    if omo:
        st.tools.add("omo")
    rng = random.Random(seed)
    switches, largest, at_zero, yearly = 0, 0.0, None, []
    previous, peak, months_buying = None, -100.0, 0
    try:
        for month in range(1, months + 1):
            if not noise:
                st.neutral_walk = st.neutral_error = st.inflation_noise = st.growth_term = 0.0
            st.deficit_pct = 0.0
            sim.monetary_update(cfg, st, rng, 0)
            bought = sim.bank_qe_pressure(cfg, st, 3.0)
            months_buying += bought > 0
            peak = max(peak, st.inflation)
            if previous is not None:
                largest = max(largest, abs(bought - previous))
                switches += (bought > 0) != (previous > 0)
            previous = bought
            if at_zero is None and st.inflation >= 0:
                at_zero = month
            if month % 12 == 0:
                yearly.append(st.inflation)
    finally:
        sim.TUNE.clear()
        sim.pressure_total = pressure_total
    return dict(switches=switches, largest=largest, at_zero=at_zero, yearly=yearly,
                peak=peak, months_buying=months_buying)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200, help="seeds per row of the noise table")
    ap.add_argument("--playtest-runs", type=int, default=60, help="seeds per row of the playtest table")
    ap.add_argument("--playtest-only", action="store_true", help="print only the playtest table")
    ap.add_argument("--ordinary-runs", type=int, default=0,
                    help="centuries per cell for the ordinary-play table (0 skips it)")
    args = ap.parse_args()
    if not args.playtest_only:
        first_trap(args)
    playtest_table(args)
    if args.ordinary_runs:
        ordinary_table(args)
    return 0


def ordinary_century(cfg, seed, *, two_sided):
    """sim.run_once with the currency loop on; returns the run's headline series and crashes."""
    imported = sim.fx_imported
    sim.fx_imported = CurrencyLoop(100.0, 0.0, premium=0.0, two_sided=two_sided)
    sim.TUNE.clear()
    try:
        state = sim.run_once(cfg, seed)
    finally:
        sim.fx_imported = imported
    return state.inflation_series, len(state.crashes)


def ordinary_table(args) -> None:
    n = args.ordinary_runs
    print(f"\nOrdinary centuries with the currency loop on, {n} per cell: two-sided -> one-sided")
    print(f"  {'':34s}{'mean inflation':>18s}{'months < 0%':>16s}{'months on -10%':>17s}{'crashes / 100y':>18s}")
    for currency in ("fiat", "digital"):
        for label, law, mode in (("independent, price", CBI, sim.MODE_PRICE),
                                 ("delegated, price", DELEGATED, sim.MODE_PRICE),
                                 ("delegated, growth", DELEGATED, sim.MODE_GROWTH)):
            cfg = sim.Config(currency=currency, mode=mode, points=5, fin_law=law)
            cells = []
            for two_sided in (True, False):
                runs = [ordinary_century(cfg, 7 + seed, two_sided=two_sided) for seed in range(n)]
                months = [x for series, _ in runs for x in series]
                cells.append((statistics.mean(months),
                              100 * sum(x < 0 for x in months) / len(months),
                              100 * sum(x <= -9.95 for x in months) / len(months),
                              statistics.mean(c for _, c in runs) * 100 / cfg.years))
            (a1, b1, c1, d1), (a2, b2, c2, d2) = cells
            print(f"  {currency + ', ' + label:34s}{a1:>8.2f} -> {a2:<6.2f}{b1:>7.2f}% -> {b2:<5.2f}%"
                  f"{c1:>7.2f}% -> {c2:<5.2f}%{d1:>8.1f} -> {d2:<6.1f}")


def first_trap(args) -> None:

    print("Headline inflation at the end of each year, no noise, cycle held at 50:")
    print(f"  {'':40s}" + "".join(f"{y:>7d}" for y in range(1, 7)))
    rows = [
        ("independent + OMO, before", CBI, sim.MODE_PRICE, True, {"bank_qe": 0.0}),
        ("independent + OMO, after", CBI, sim.MODE_PRICE, True, {}),
        ("independent, no OMO, before", CBI, sim.MODE_PRICE, False, {"bank_qe": 0.0}),
        ("independent, no OMO, after", CBI, sim.MODE_PRICE, False, {}),
        ("manual dial + OMO, before", DELEGATED, sim.MODE_NOTHING, True, {"bank_qe": 0.0}),
        ("manual dial + OMO, after", DELEGATED, sim.MODE_NOTHING, True, {}),
    ]
    for label, law, mode, omo, tune in rows:
        yearly = run(0, "digital", law, mode, noise=False, omo=omo, tune=tune)["yearly"]
        print(f"  {label:40s}" + "".join(f"{x:+7.1f}" for x in yearly[:6]))

    print(f"\nNoise on, {args.runs} seeds per row, no OMO:")
    print(f"  {'':34s}{'switches (mean / max)':>24s}{'largest 1-month change':>25s}{'median month at 0%':>21s}")
    for label, currency, law, mode in (
        ("independent, digital, price", "digital", CBI, sim.MODE_PRICE),
        ("delegated, digital, price", "digital", DELEGATED, sim.MODE_PRICE),
        ("delegated, fiat, price", "fiat", DELEGATED, sim.MODE_PRICE),
        ("delegated, fiat, growth", "fiat", DELEGATED, sim.MODE_GROWTH),
    ):
        results = [run(seed, currency, law, mode) for seed in range(args.runs)]
        switches = [r["switches"] for r in results]
        reached = [r["at_zero"] for r in results if r["at_zero"]]
        median = statistics.median(reached) if reached else float("nan")
        print(f"  {label:34s}{statistics.mean(switches):>17.2f} / {max(switches):<4d}"
              f"{max(r['largest'] for r in results):>25.2f}{median:>14.0f} ({len(reached)}/{args.runs})")

    print("\nDelegated, no independence, Digital, Price Stability, monetising, noise held at zero:")
    print(f"  {'':22s}{'month at 0%: without / with purchases':>40s}{'peak inflation':>18s}{'months buying':>15s}")
    for level in (0, 1, 3):
        off = run(0, "digital", DELEGATED, sim.MODE_PRICE, noise=False, monetise=level, tune={"bank_qe": 0.0})
        on = run(0, "digital", DELEGATED, sim.MODE_PRICE, noise=False, monetise=level)
        print(f"  Monetise Deficit {level}    {off['at_zero']!s:>20s} / {on['at_zero']!s:<17s}"
              f"{off['peak']:>8.1f} / {on['peak']:<7.1f}{on['months_buying']:>13d}")


def playtest_table(args) -> None:
    n = args.playtest_runs
    print(f"\nThe playtest (Panic, strong currency, headline on -10%), cycle running, {n} seeds, medians:")
    print(f"  {'':52s}{'leaves -10%':>14s}{'reaches 0%':>16s}{'peak after':>12s}{'yrs 8-10':>10s}")
    before = dict(cap=PREVIOUS_CAP, two_sided=True)
    cases = [
        ("Growth, before (cap 2.5, two-sided)", before),
        ("Growth, cap 5 alone (two-sided)", dict(two_sided=True)),
        ("Growth, one-sided alone (cap 2.5)", dict(cap=PREVIOUS_CAP)),
        ("Growth, shipped (cap 5, one-sided)", dict()),
        ("Price Stability, before", dict(before, mode=sim.MODE_PRICE)),
        ("Price Stability, shipped", dict(mode=sim.MODE_PRICE)),
        ("Growth, before, Restrict Inflows for Bail-in", dict(before, tools=("omo", "dc_elec", "restrict_inflows"))),
        ("Growth, before, no currency loop", dict(before, currency_loop=False)),
    ]
    for label, kw in cases:
        results = [playtest(seed, **kw) for seed in range(n)]
        off = [r["off_clamp"] for r in results if r["off_clamp"]]
        zero = [r["at_zero"] for r in results if r["at_zero"]]
        peaks = [r["peak"] for r in results if r["peak"] is not None]

        def med(values):
            return f"{statistics.median(values):.0f}" if values else "never"
        print(f"  {label:52s}{med(off):>6s} ({len(off):>2d}/{n})"
              f"{med(zero):>8s} ({len(zero):>2d}/{n})"
              f"{(statistics.median(peaks) if peaks else float('nan')):>12.1f}"
              f"{statistics.median(r['late'] for r in results):>10.1f}")


if __name__ == "__main__":
    raise SystemExit(main())
