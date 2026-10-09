"""Pop growth model: birthrate, mortality, and growth rate as functions of Standard of Living.

The curve constants are read from the mod's defines (`common/defines/extra_defines.txt`, the
"Pop Growth Constants" block), so this model follows the engine's curves when they are retuned.

Usage:
    python pop_growth.py              # Print text table of rates at each SoL
    python pop_growth.py --plot       # Show matplotlib chart
    python pop_growth.py --sol 15     # Print rates at a specific SoL
    python pop_growth.py --range 5 25 # Print rates for SoL 5-25

Functions are importable:
    from pop_growth import calculate_birthrate, calculate_mortality
    from pop_growth import read_defines, monthly_birthrate, monthly_mortality  # per-month curves
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

# ── Pop Growth Constants (from the mod's defines) ─────────────────────────────
DEFINES = Path(__file__).resolve().parents[2] / "common" / "defines" / "extra_defines.txt"
_NAMES = {
    "min_birthrate": "min_birthrate", "max_birthrate": "max_birthrate",
    "min_mortality": "min_mortality", "max_mortality": "max_mortality",
    "equilibrium_sol": "pop_growth_equilibrium_sol", "transition_sol": "pop_growth_transition_sol",
    "max_sol": "pop_growth_max_sol", "stable_sol": "pop_growth_stable_sol",
    "transition_birthrate_mult": "transition_birthrate_mult",
    "max_growth_mortality_mult": "max_growth_mortality_mult",
}


@dataclass(frozen=True)
class GrowthDefines:
    min_birthrate: float
    max_birthrate: float
    min_mortality: float
    max_mortality: float
    equilibrium_sol: float
    transition_sol: float
    max_sol: float
    stable_sol: float
    transition_birthrate_mult: float
    max_growth_mortality_mult: float


def read_defines(path=DEFINES):
    """The @-variables of the pop growth block, monthly rates as written."""
    text = Path(path).read_text(encoding="utf-8-sig")
    values = {}
    for field_name, var in _NAMES.items():
        m = re.search(rf"^@{var}\s*=\s*([-0-9.]+)", text, re.MULTILINE)
        if not m:
            raise KeyError(f"@{var} not found in {path}")
        values[field_name] = float(m.group(1))
    return GrowthDefines(**values)


# ── Core Functions ────────────────────────────────────────────────────────────
# The derived slopes and intercepts are the defines file's own formulas
# ("Pop Growth Derived values" in extra_defines.txt).

def _rate_at_equilibrium(d, at_transition):
    return d.equilibrium_sol * ((at_transition - d.max_birthrate) / d.transition_sol) + d.max_birthrate


def monthly_birthrate(sol, d, malnourishment=False):
    """Base birthrate per month at a Standard of Living.

    `malnourishment=True` applies this module's approximation of starvation below the
    equilibrium SoL; the define curve alone is the default.
    """
    at_transition = d.max_birthrate * d.transition_birthrate_mult
    if sol <= d.transition_sol:
        pre_slope = (at_transition - _rate_at_equilibrium(d, at_transition)) / d.transition_sol
        rate = d.max_birthrate + pre_slope * sol
        if malnourishment and sol < d.equilibrium_sol:
            rate *= 1 - 0.1 * (d.equilibrium_sol - sol)
        return rate
    if sol >= d.stable_sol:
        return d.min_birthrate
    slope = (d.min_birthrate - at_transition) / (d.stable_sol - d.transition_sol)
    return d.min_birthrate + slope * (sol - d.stable_sol)


def monthly_mortality(sol, d):
    """Base mortality per month at a Standard of Living."""
    at_transition = d.max_birthrate * d.transition_birthrate_mult
    at_eq = _rate_at_equilibrium(d, at_transition)
    birth_at_max = (d.max_sol - d.transition_sol) * (
        (d.min_birthrate - at_transition) / (d.stable_sol - d.transition_sol)) + at_transition
    mort_at_max = birth_at_max * d.max_growth_mortality_mult
    if sol <= d.equilibrium_sol:
        return d.max_mortality + (at_eq - d.max_mortality) / d.equilibrium_sol * sol
    if sol <= d.max_sol:
        return at_eq + (mort_at_max - at_eq) / (d.max_sol - d.equilibrium_sol) * (sol - d.equilibrium_sol)
    if sol < d.stable_sol:
        return mort_at_max + (d.min_mortality - mort_at_max) / (d.stable_sol - d.max_sol) * (sol - d.max_sol)
    return d.min_mortality


_DEFAULT = read_defines()


def calculate_mortality(sol: float) -> float:
    """Calculate annual mortality rate for a given Standard of Living."""
    return monthly_mortality(sol, _DEFAULT) * 12


def calculate_birthrate(sol: float) -> float:
    """Calculate annual birthrate for a given Standard of Living."""
    return monthly_birthrate(sol, _DEFAULT, malnourishment=True) * 12


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
        ("Equilibrium", _DEFAULT.equilibrium_sol),
        ("Transition", _DEFAULT.transition_sol),
        ("Max Growth", _DEFAULT.max_sol),
        ("Stable", _DEFAULT.stable_sol),
    ]
    print("\nKey Thresholds:")
    print(f"  {'Phase':<14} {'SoL':>4}  {'Birth':>8}  {'Death':>8}  {'Net':>8}")
    for name, sol in thresholds:
        r = rates_at_sol(sol, birth_mult, mort_mult)
        print(f"  {name:<14} {sol:>4g}  {r['birthrate']:>8.5f}  {r['mortality']:>8.5f}  {r['growth_rate']:>+8.5f}")

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

    for name, sol in [("Equil", _DEFAULT.equilibrium_sol), ("Trans", _DEFAULT.transition_sol),
                       ("MaxGr", _DEFAULT.max_sol), ("Stable", _DEFAULT.stable_sol)]:
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
