"""Pop growth model: birthrate, mortality, and growth rate as functions of Standard of Living.

Usage:
    python pop_growth.py              # Print text table of rates at each SoL
    python pop_growth.py --plot       # Show matplotlib chart
    python pop_growth.py --sol 15     # Print rates at a specific SoL
    python pop_growth.py --range 5 25 # Print rates for SoL 5-25

Functions are importable:
    from pop_growth import calculate_birthrate, calculate_mortality
"""

import argparse
import sys

# ── Pop Growth Constants (from game defines) ──────────────────────────────────
MIN_BIRTHRATE = 0.00080 * 12
MAX_BIRTHRATE = 0.00475 * 12
MIN_MORTALITY = 0.00100 * 12
MAX_MORTALITY = 0.00600 * 12

POP_GROWTH_EQUILIBRIUM_SOL = 4
POP_GROWTH_TRANSITION_SOL = 11
POP_GROWTH_MAX_SOL = 18
POP_GROWTH_STABLE_SOL = 35

TRANSITION_BIRTHRATE_MULT = 1
MAX_GROWTH_MORTALITY_MULT = 0.4

# ── Derived Values ────────────────────────────────────────────────────────────
_birthrate_at_transition = MAX_BIRTHRATE * TRANSITION_BIRTHRATE_MULT
_rate_at_equilibrium = (
    POP_GROWTH_EQUILIBRIUM_SOL
    * ((_birthrate_at_transition - MAX_BIRTHRATE) / POP_GROWTH_TRANSITION_SOL)
    + MAX_BIRTHRATE
)

_mortality_starving_slope = (
    _rate_at_equilibrium - MAX_MORTALITY
) / POP_GROWTH_EQUILIBRIUM_SOL
_birthrate_pretransition_slope = (
    _birthrate_at_transition - _rate_at_equilibrium
) / POP_GROWTH_TRANSITION_SOL

_birthrate_at_growth_max = (POP_GROWTH_MAX_SOL - POP_GROWTH_TRANSITION_SOL) * (
    (MIN_BIRTHRATE - _birthrate_at_transition)
    / (POP_GROWTH_STABLE_SOL - POP_GROWTH_TRANSITION_SOL)
) + _birthrate_at_transition
_mortality_at_growth_max = _birthrate_at_growth_max * MAX_GROWTH_MORTALITY_MULT
_mortality_eq_to_max_slope = (
    _mortality_at_growth_max - _rate_at_equilibrium
) / (POP_GROWTH_MAX_SOL - POP_GROWTH_EQUILIBRIUM_SOL)
_mortality_eq_to_max_intercept = (
    -_mortality_eq_to_max_slope * POP_GROWTH_EQUILIBRIUM_SOL
    + _rate_at_equilibrium
)

_birthrate_transition_slope = (MIN_BIRTHRATE - _birthrate_at_transition) / (
    POP_GROWTH_STABLE_SOL - POP_GROWTH_TRANSITION_SOL
)
_birthrate_transition_intercept = (
    -_birthrate_transition_slope * POP_GROWTH_STABLE_SOL + MIN_BIRTHRATE
)

_mortality_max_to_stable_slope = (MIN_MORTALITY - _mortality_at_growth_max) / (
    POP_GROWTH_STABLE_SOL - POP_GROWTH_MAX_SOL
)
_mortality_max_to_stable_intercept = (
    -_mortality_max_to_stable_slope * POP_GROWTH_STABLE_SOL + MIN_MORTALITY
)


# ── Core Functions ────────────────────────────────────────────────────────────

def calculate_mortality(sol: float) -> float:
    """Calculate annual mortality rate for a given Standard of Living."""
    if sol < POP_GROWTH_EQUILIBRIUM_SOL:
        return sol * _mortality_starving_slope + MAX_MORTALITY
    elif sol < POP_GROWTH_MAX_SOL:
        return sol * _mortality_eq_to_max_slope + _mortality_eq_to_max_intercept
    elif sol < POP_GROWTH_STABLE_SOL:
        return sol * _mortality_max_to_stable_slope + _mortality_max_to_stable_intercept
    else:
        return MIN_MORTALITY


def calculate_birthrate(sol: float) -> float:
    """Calculate annual birthrate for a given Standard of Living."""
    if sol < POP_GROWTH_EQUILIBRIUM_SOL:
        return (sol * _birthrate_pretransition_slope + MAX_BIRTHRATE) * (
            1 - 0.1 * (POP_GROWTH_EQUILIBRIUM_SOL - sol)
        )
    elif sol < POP_GROWTH_TRANSITION_SOL:
        return sol * _birthrate_pretransition_slope + MAX_BIRTHRATE
    elif sol < POP_GROWTH_STABLE_SOL:
        return sol * _birthrate_transition_slope + _birthrate_transition_intercept
    else:
        return MIN_BIRTHRATE


def calculate_growth_rate(sol: float, birth_mult: float = 1.0, mort_mult: float = 1.0) -> float:
    """Calculate net annual growth rate (birthrate - mortality)."""
    return birth_mult * calculate_birthrate(sol) - mort_mult * calculate_mortality(sol)


def rates_at_sol(sol: float, birth_mult: float = 1.0, mort_mult: float = 1.0) -> dict:
    """Return a dict with birthrate, mortality, growth rate, and growth % at a given SoL."""
    b = birth_mult * calculate_birthrate(sol)
    m = mort_mult * calculate_mortality(sol)
    g = b - m
    return {
        "sol": sol,
        "birthrate": b,
        "mortality": m,
        "growth_rate": g,
        "growth_pct": g * 100,
    }


# ── Text Output ───────────────────────────────────────────────────────────────

def print_table(sol_min: int = 1, sol_max: int = 40, birth_mult: float = 1.0, mort_mult: float = 1.0):
    """Print a formatted text table of pop growth rates."""
    print(f"{'SoL':>4}  {'Birthrate':>10}  {'Mortality':>10}  {'Growth':>10}  {'Growth%':>8}")
    print(f"{'---':>4}  {'----------':>10}  {'----------':>10}  {'----------':>10}  {'--------':>8}")
    for sol in range(sol_min, sol_max + 1):
        r = rates_at_sol(sol, birth_mult, mort_mult)
        print(f"{sol:>4}  {r['birthrate']:>10.5f}  {r['mortality']:>10.5f}  {r['growth_rate']:>+10.5f}  {r['growth_pct']:>+7.2f}%")


def print_key_thresholds(birth_mult: float = 1.0, mort_mult: float = 1.0):
    """Print rates at the key SoL thresholds defined in game constants."""
    thresholds = [
        ("Equilibrium", POP_GROWTH_EQUILIBRIUM_SOL),
        ("Transition", POP_GROWTH_TRANSITION_SOL),
        ("Max Growth", POP_GROWTH_MAX_SOL),
        ("Stable", POP_GROWTH_STABLE_SOL),
    ]
    print("\nKey Thresholds:")
    print(f"  {'Phase':<14} {'SoL':>4}  {'Birth':>8}  {'Death':>8}  {'Net':>8}")
    for name, sol in thresholds:
        r = rates_at_sol(sol, birth_mult, mort_mult)
        print(f"  {name:<14} {sol:>4}  {r['birthrate']:>8.5f}  {r['mortality']:>8.5f}  {r['growth_rate']:>+8.5f}")

    # Find peak growth SoL
    best_sol, best_growth = 1, -999
    for s10 in range(10, 400):
        s = s10 / 10.0
        g = calculate_growth_rate(s, birth_mult, mort_mult)
        if g > best_growth:
            best_growth = g
            best_sol = s
    print(f"\n  Peak growth: SoL {best_sol:.1f} -> {best_growth:+.5f}/yr ({best_growth * 100:+.2f}%)")


# ── Plot ──────────────────────────────────────────────────────────────────────

def plot(sol_min: float = 1, sol_max: float = 40, birth_mult: float = 1.0, mort_mult: float = 1.0):
    """Show matplotlib chart of birthrate, mortality, and growth rate."""
    import matplotlib.pyplot as plt
    import numpy as np

    sol_range = np.linspace(sol_min, sol_max, 400)
    birthrates = np.array([birth_mult * calculate_birthrate(s) for s in sol_range])
    mortalities = np.array([mort_mult * calculate_mortality(s) for s in sol_range])
    growth_rates = birthrates - mortalities

    plt.figure(figsize=(12, 8))
    plt.plot(sol_range, birthrates, label="Birthrate", color="blue")
    plt.plot(sol_range, mortalities, label="Mortality", color="red")
    plt.plot(sol_range, growth_rates, label="Growth Rate", color="green")
    plt.axhline(y=0, color="gray", linestyle=":", alpha=0.5)

    for name, sol in [("Equil", POP_GROWTH_EQUILIBRIUM_SOL), ("Trans", POP_GROWTH_TRANSITION_SOL),
                       ("MaxGr", POP_GROWTH_MAX_SOL), ("Stable", POP_GROWTH_STABLE_SOL)]:
        plt.axvline(x=sol, color="gray", linestyle="--", alpha=0.3)
        plt.annotate(name, (sol, plt.ylim()[1] * 0.95), fontsize=8, ha="center")

    plt.title("Pop Growth: Birthrate, Mortality, and Growth Rate vs Standard of Living")
    plt.xlabel("Standard of Living (SoL)")
    plt.ylabel("Rate per Year")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Victoria 3 pop growth rate calculator")
    parser.add_argument("--plot", action="store_true", help="Show matplotlib plot")
    parser.add_argument("--sol", type=float, help="Print rates at a specific SoL")
    parser.add_argument("--range", nargs=2, type=int, metavar=("MIN", "MAX"),
                        help="Print table for SoL range (default: 1-40)")
    parser.add_argument("--birth-mult", type=float, default=1.0, help="Birthrate multiplier")
    parser.add_argument("--mort-mult", type=float, default=1.0, help="Mortality multiplier")
    args = parser.parse_args()

    bm, mm = args.birth_mult, args.mort_mult

    if args.sol is not None:
        r = rates_at_sol(args.sol, bm, mm)
        print(f"SoL {r['sol']:.1f}: birthrate={r['birthrate']:.5f}, mortality={r['mortality']:.5f}, "
              f"growth={r['growth_rate']:+.5f} ({r['growth_pct']:+.2f}%/yr)")
    elif args.plot:
        rng = args.range or [1, 40]
        plot(rng[0], rng[1], bm, mm)
    else:
        rng = args.range or [1, 40]
        print_table(rng[0], rng[1], bm, mm)
        print_key_thresholds(bm, mm)


if __name__ == "__main__":
    main()
