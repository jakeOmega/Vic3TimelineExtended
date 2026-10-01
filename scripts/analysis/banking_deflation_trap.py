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
  long headline takes to reach 0%.

Usage:
    python3 scripts/analysis/banking_deflation_trap.py [--runs 200]
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


def run(seed, currency, fin_law, mode, *, noise=True, omo=False, months=120, tune=None):
    """One trapped country; returns (switches, largest change, month at 0%, yearly headline)."""
    sim.TUNE.clear()
    sim.TUNE.update(tune or {})
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
    previous = None
    try:
        for month in range(1, months + 1):
            if not noise:
                st.neutral_walk = st.neutral_error = st.inflation_noise = st.growth_term = 0.0
            st.deficit_pct = 0.0
            sim.monetary_update(cfg, st, rng, 0)
            bought = sim.bank_qe_pressure(cfg, st, 3.0)
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
    return switches, largest, at_zero, yearly


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=int, default=200, help="seeds per row of the noise table")
    args = ap.parse_args()

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
        yearly = run(0, "digital", law, mode, noise=False, omo=omo, tune=tune)[3]
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
        switches = [r[0] for r in results]
        reached = [r[2] for r in results if r[2]]
        median = statistics.median(reached) if reached else float("nan")
        print(f"  {label:34s}{statistics.mean(switches):>17.2f} / {max(switches):<4d}"
              f"{max(r[1] for r in results):>25.2f}{median:>14.0f} ({len(reached)}/{args.runs})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
