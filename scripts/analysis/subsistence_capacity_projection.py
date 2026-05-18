"""Subsistence capacity vs. population projection for issue #114.

Models how an unindustrialized country's peasant population fares under the
mod's arable-land curve (current vs. proposed + agricultural diffusion).
Couples pop_growth.py birth/death curves with starvation feedback when
population outgrows subsistence capacity.

Usage:
    python subsistence_capacity_projection.py                 # default India-shape, all scenarios
    python subsistence_capacity_projection.py --plot          # matplotlib charts
    python subsistence_capacity_projection.py --country brazil
    python subsistence_capacity_projection.py --start-pop 80 --industrial-abs 0.005

The "capacity" of a country is treated abstractly as a multiple of starting
population. Year 0 is set so capacity = 1.0 × starting pop (i.e., the country
is at saturation; any growth that isn't absorbed by industrialization spills
into unemployment / starvation). The arable_land_mult curve scales capacity
directly. Industrial absorption is a per-year compound growth rate that
expands non-subsistence employment, soaking up surplus population without
hitting the starvation wall.

This is a coarse projection, NOT an engine simulator. It validates that the
new curve avoids the population-collapse death spiral that motivates the
issue; precise targets require an in-game run.
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import Optional

# Reuse the existing pop_growth model
sys.path.insert(0, sys.path[0] or ".")
from pop_growth import calculate_birthrate, calculate_mortality


# ── Arable land curve definitions ───────────────────────────────────────────
# (research_year, mult_added) tuples.
#
# CURRENT curve = pre-fix values:
#   intensive_agriculture +0.05, improved_fertilizer +0.05, nitrogen_fixation
#   +0.05, modern_chemical_processes +0.20, green_revolution +0.65,
#   gene_splicing +0.10, biotechnology +0.20.
#
# PROPOSED curve = post-fix values from issue #114 plan.

CURRENT_LOCAL_TECH = [
    (1850, 0.05),  # intensive_agriculture (era 2)
    (1875, 0.05),  # improved_fertilizer (era 3)
    (1905, 0.05),  # nitrogen_fixation (era 4)
    (1935, 0.20),  # modern_chemical_processes (era 6)
    (1960, 0.65),  # green_revolution (era 7)
    (1980, 0.10),  # gene_splicing (era 8)
    (2000, 0.20),  # biotechnology (era 9)
]

PROPOSED_LOCAL_TECH = [
    (1850, 0.10),
    (1875, 0.15),
    (1905, 0.30),
    (1935, 0.30),
    (1960, 1.20),
    (1980, 0.30),
    (2000, 0.50),
]

# Diffusion bonuses (per agdiff_<tech> static modifier value).
# Earliest possible activation = same year the first researcher unlocks; we
# assume a leading nation (USA / UK / Germany / Japan) hits each tech at the
# era's onset year.
DIFFUSION_BONUSES = {
    1905: 0.15,  # agdiff_nitrogen_fixation
    1935: 0.15,  # agdiff_modern_chemical_processes
    1960: 0.60,  # agdiff_green_revolution
    1980: 0.15,  # agdiff_gene_splicing
    2000: 0.25,  # agdiff_biotechnology
}

# Power bloc rural principles (top tier eventually available)
PRINCIPLE_BONUS_BY_YEAR = {
    1880: 0.05,
    1910: 0.10,
    1940: 0.15,
    1970: 0.20,
    2000: 0.25,
}


def cumulative_local_bonus(year: int, schedule: list[tuple[int, float]],
                            researches: bool) -> float:
    """Sum of tech bonuses the country has earned by `year`."""
    if not researches:
        return 0.0
    return sum(amount for y, amount in schedule if y <= year)


def cumulative_diffusion_bonus(year: int) -> float:
    """Sum of diffusion bonuses available to every country."""
    return sum(amount for y, amount in DIFFUSION_BONUSES.items() if y <= year)


def principle_bonus(year: int, has_principles: bool) -> float:
    if not has_principles:
        return 0.0
    bonus = 0.0
    for y, amount in PRINCIPLE_BONUS_BY_YEAR.items():
        if y <= year:
            bonus = amount  # principles don't stack; latest tier replaces
    return bonus


@dataclass
class Scenario:
    name: str
    local_schedule: list[tuple[int, float]]
    diffusion_active: bool
    researches: bool
    has_principles: bool = False

    def total_mult(self, year: int) -> float:
        return (
            cumulative_local_bonus(year, self.local_schedule, self.researches)
            + (cumulative_diffusion_bonus(year) if self.diffusion_active else 0.0)
            + principle_bonus(year, self.has_principles)
        )


@dataclass
class CountryProfile:
    name: str
    start_year: int
    end_year: int
    start_pop_millions: float
    # Fraction of pop that starts in non-subsistence jobs (urban, industrial)
    starting_industrial_fraction: float
    # Per-year compound growth of non-subsistence jobs (industrialization rate).
    # 0.0 = no industrialization (e.g., stuck colonial economy).
    # 0.015 = ~1.5%/yr (Brazil-shape, modest industrialization).
    # 0.025 = ~2.5%/yr (India post-1947, slow but real).
    industrial_growth_rate: float
    # SoL when capacity == pop (full subsistence). Drops with overcapacity.
    sol_at_saturation: float = 8.0
    # SoL gained per 1.0 of (capacity - pop) headroom.
    sol_headroom_factor: float = 4.0
    # When pop exceeds capacity, starving fraction triggers
    # vanilla starvation_penalty (-0.7 birth, +0.6 mortality on that fraction).
    starvation_birth_mult: float = 0.30
    starvation_mortality_mult: float = 1.60


def project(country: CountryProfile, scenario: Scenario) -> dict:
    years = list(range(country.start_year, country.end_year + 1))
    pop = [country.start_pop_millions]
    sol_trace = [country.sol_at_saturation]
    capacity_trace = [1.0]  # multiplier on starting pop

    starting_subsistence = country.start_pop_millions * (
        1.0 - country.starting_industrial_fraction
    )
    starting_industrial = country.start_pop_millions * country.starting_industrial_fraction

    for i, year in enumerate(years[1:], start=1):
        # Capacity in "starting subsistence units"
        subsistence_capacity = starting_subsistence * (1.0 + scenario.total_mult(year))
        industrial_jobs = starting_industrial * (
            (1.0 + country.industrial_growth_rate) ** (year - country.start_year)
        )
        total_capacity = subsistence_capacity + industrial_jobs
        capacity_trace.append(total_capacity / country.start_pop_millions)

        prev_pop = pop[-1]
        # Compute SoL: high when capacity >> pop, low when pop > capacity
        if prev_pop <= total_capacity:
            headroom = (total_capacity - prev_pop) / max(prev_pop, 1.0)
            sol = country.sol_at_saturation + country.sol_headroom_factor * headroom
            # Clamp SoL to a sane range
            sol = max(2.0, min(18.0, sol))
            birthrate = calculate_birthrate(sol)
            mortality = calculate_mortality(sol)
        else:
            # Over capacity → starving fraction
            starving_frac = (prev_pop - total_capacity) / prev_pop
            fed_frac = 1.0 - starving_frac
            sol = country.sol_at_saturation * 0.5  # SoL collapses
            base_b = calculate_birthrate(sol)
            base_m = calculate_mortality(sol)
            birthrate = (
                fed_frac * base_b
                + starving_frac * base_b * country.starvation_birth_mult
            )
            mortality = (
                fed_frac * base_m
                + starving_frac * base_m * country.starvation_mortality_mult
            )

        net_growth = birthrate - mortality
        new_pop = prev_pop * (1.0 + net_growth)
        pop.append(new_pop)
        sol_trace.append(sol)

    return {
        "years": years,
        "pop": pop,
        "sol": sol_trace,
        "capacity": capacity_trace,
    }


# ── Country profiles ────────────────────────────────────────────────────────

COUNTRIES = {
    "india": CountryProfile(
        name="India-like",
        start_year=1836,
        end_year=2030,
        start_pop_millions=200.0,
        starting_industrial_fraction=0.05,  # very rural
        industrial_growth_rate=0.020,  # post-independence catch-up
    ),
    "brazil": CountryProfile(
        name="Brazil-like",
        start_year=1836,
        end_year=2030,
        start_pop_millions=8.0,
        starting_industrial_fraction=0.10,
        industrial_growth_rate=0.025,
    ),
    "nigeria": CountryProfile(
        name="Nigeria-like",
        start_year=1836,
        end_year=2030,
        start_pop_millions=15.0,
        starting_industrial_fraction=0.03,
        industrial_growth_rate=0.010,  # weak industrial absorption
    ),
}


def build_scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="(a) Current curve, no research",
            local_schedule=CURRENT_LOCAL_TECH,
            diffusion_active=False,
            researches=False,
        ),
        Scenario(
            name="(b) Proposed curve, no research",
            local_schedule=PROPOSED_LOCAL_TECH,
            diffusion_active=False,
            researches=False,
        ),
        Scenario(
            name="(c) Proposed + diffusion, no own research",
            local_schedule=PROPOSED_LOCAL_TECH,
            diffusion_active=True,
            researches=False,
        ),
        Scenario(
            name="(d) Proposed + diffusion + own research + principles",
            local_schedule=PROPOSED_LOCAL_TECH,
            diffusion_active=True,
            researches=True,
            has_principles=True,
        ),
    ]


def print_table(country: CountryProfile, scenarios: list[Scenario]):
    checkpoints = [1836, 1900, 1936, 1965, 2000, 2030]
    print(f"\n=== {country.name} (start pop {country.start_pop_millions}M, "
          f"industrial growth {country.industrial_growth_rate * 100:.1f}%/yr) ===\n")
    header = f"{'Year':>6}  " + "  ".join(f"{s.name[:36]:>36}" for s in scenarios)
    print(header)
    print(f"{'----':>6}  " + "  ".join(f"{'pop(M) /  SoL  / capX':>36}" for _ in scenarios))
    results = [project(country, s) for s in scenarios]
    for cp in checkpoints:
        if cp > country.end_year:
            continue
        row = f"{cp:>6}  "
        for r in results:
            idx = cp - country.start_year
            if idx < 0 or idx >= len(r["years"]):
                row += f"{'-':>36}  "
                continue
            cell = f"{r['pop'][idx]:>6.0f}M / {r['sol'][idx]:>5.1f} / {r['capacity'][idx]:>5.2f}x"
            row += f"{cell:>36}  "
        print(row)


def plot(country: CountryProfile, scenarios: list[Scenario]):
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    for scenario in scenarios:
        result = project(country, scenario)
        ax1.plot(result["years"], result["pop"], label=scenario.name)
        ax2.plot(result["years"], result["sol"], label=scenario.name)
    ax1.set_title(f"{country.name} — Population (M)")
    ax1.set_ylabel("Population (millions)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax2.set_title(f"{country.name} — SoL proxy")
    ax2.set_ylabel("SoL")
    ax2.set_xlabel("Year")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Subsistence capacity / pop trajectory projection for issue #114"
    )
    parser.add_argument("--country", choices=list(COUNTRIES.keys()), default=None,
                        help="Project a single country (default: all three)")
    parser.add_argument("--plot", action="store_true", help="Show matplotlib chart")
    parser.add_argument("--start-pop", type=float, default=None,
                        help="Override starting pop (millions)")
    parser.add_argument("--industrial-abs", type=float, default=None,
                        help="Override industrial growth rate (per year, e.g. 0.020)")
    args = parser.parse_args()

    scenarios = build_scenarios()
    countries = (
        [COUNTRIES[args.country]] if args.country else list(COUNTRIES.values())
    )
    for c in countries:
        if args.start_pop is not None:
            c.start_pop_millions = args.start_pop
        if args.industrial_abs is not None:
            c.industrial_growth_rate = args.industrial_abs
        print_table(c, scenarios)
        if args.plot:
            plot(c, scenarios)


if __name__ == "__main__":
    main()
