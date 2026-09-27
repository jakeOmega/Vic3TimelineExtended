"""The nuclear taboo's monthly model, run over a century.

Mirrors nd_taboo_monthly_update and nd_taboo_note_use
(common/scripted_effects/nuclear_taboo_effects.txt) and the band check
(nd_taboo_band_check). Every constant is read from
common/script_values/nuclear_taboo_values.txt, so a retune there changes the
table here; the scenarios are the only numbers this file owns. Re-run after
tuning and refresh the table in docs/systems/nuclear_crisis_design.md §0.11.

The postures, restraint and UN parts are fixed per scenario (they follow
decisions this model does not make); the tradition clock, the ledger and the
shocks are simulated.

Usage:
    python3 scripts/analysis/nuclear_taboo_sim.py [--years N]
"""

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

VALUES = Path(__file__).resolve().parents[2] / "common/script_values/nuclear_taboo_values.txt"
LINE = re.compile(r"^(nd_taboo_\w+) = (-?[\d.]+)\s*(?:#.*)?$")
BAND_LINES = ("nd_taboo_line_fragile", "nd_taboo_line_established",
              "nd_taboo_line_strong", "nd_taboo_line_absolute")


def load_constants(path=VALUES):
    constants = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        m = LINE.match(line)
        if m:
            constants[m.group(1)] = float(m.group(2))
    return constants


@dataclass
class Scenario:
    description: str
    postures: float = 0.0
    restraint: float = 0.0
    un: float = 0.0
    # month -> ("strategic" | "tactical", retaliation?)
    uses: dict = field(default_factory=dict)
    # month -> ledger points (renunciations, threats, ...)
    ledger_entries: dict = field(default_factory=dict)
    seed_quiet_years: float | None = None


def _step(c, score, target):
    step = (target - score) / c["nd_taboo_approach_months"]
    return max(c["nd_taboo_max_step_down"], min(c["nd_taboo_max_step"], step))


def _target(c, quiet_years, ledger, s):
    tradition = min(c["nd_taboo_tradition_cap"], max(0.0, quiet_years * c["nd_taboo_tradition_per_year"]))
    return max(0.0, min(100.0, c["nd_taboo_base"] + tradition + s.postures + s.restraint + s.un + ledger))


def simulate(scenario, constants, years=100):
    c = constants
    quiet = scenario.seed_quiet_years or 0.0
    ledger = 0.0
    if scenario.seed_quiet_years is None:
        score = c["nd_taboo_birth_value"]
    else:
        score = _target(c, quiet, ledger, scenario)
    series = []
    for month in range(years * 12):
        for kind, retaliation in ([scenario.uses[month]] if month in scenario.uses else []):
            factor = c["nd_taboo_retaliation_factor"] if retaliation else 1.0
            quiet *= c["nd_taboo_clock_keep_retaliation"] if retaliation else c["nd_taboo_clock_keep_first_use"]
            score = max(0.0, min(100.0, score + c[f"nd_taboo_shock_{kind}"] * factor))
            ledger = max(c["nd_taboo_ledger_min"],
                         min(c["nd_taboo_ledger_max"], ledger + c[f"nd_taboo_ledger_{kind}"] * factor))
        if month in scenario.ledger_entries:
            ledger = max(c["nd_taboo_ledger_min"],
                         min(c["nd_taboo_ledger_max"], ledger + scenario.ledger_entries[month]))
        quiet += 1 / 12
        ledger *= c["nd_taboo_ledger_decay"]
        target = _target(c, quiet, ledger, scenario)
        score = max(0.0, min(100.0, score + _step(c, score, target)))
        series.append((score, target))
    return series


def band_of(c, score):
    return 1 + sum(score >= c[name] for name in BAND_LINES)


def band_events(scores, constants, cooldown_months):
    """(month, 'up N' | 'down N') for each band event the check would fire.

    N is the boundary crossed (1 = 30 ... 4 = 90). The band moves one step a
    month once the score is `nd_taboo_band_hysteresis` past the boundary; the
    event fires only if that boundary and direction has been quiet for
    `cooldown_months`."""
    c = constants
    h = c["nd_taboo_band_hysteresis"]
    lines = [c[name] for name in BAND_LINES]
    band = band_of(c, scores[0])
    last = {}
    events = []
    for month, score in enumerate(scores):
        key = None
        if band < 5 and score >= lines[band - 1] + h:
            band += 1
            key = f"up {band - 1}"
        elif band > 1 and score <= lines[band - 2] - h:
            band -= 1
            key = f"down {band}"
        if key and month - last.get(key, -10**9) >= cooldown_months:
            last[key] = month
            events.append((month, key))
    return events


SCENARIOS = {
    "quiet": Scenario("No use, no threats, no treaties"),
    "use_year_10": Scenario("A strategic first use in year 10", uses={120: ("strategic", False)}),
    "use_year_40": Scenario("A strategic first use in year 40", uses={480: ("strategic", False)}),
    "nfu_world": Scenario("Armed powers under No First Use, pledges, a renunciation in year 20",
                          postures=10, restraint=8, ledger_entries={240: 4}),
    "normalised": Scenario("Warfighting doctrines and a strategic first use every 8 years",
                           postures=-10, uses={m: ("strategic", False) for m in range(96, 1200, 96)}),
    "seeded_40_years": Scenario("A save seeded 40 years after the first device, no use", seed_quiet_years=40),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", type=int, default=100)
    years = parser.parse_args().years
    c = load_constants()
    checkpoints = [y for y in (1, 10, 20, 35, 50, 75, 100) if y <= years]
    print("| Scenario | " + " | ".join(f"year {y}" for y in checkpoints) + " | band events |")
    print("|---|" + "---|" * (len(checkpoints) + 1))
    cooldown = int(c["nd_taboo_event_cooldown_years"] * 12)
    for name, scenario in SCENARIOS.items():
        series = simulate(scenario, c, years)
        cells = [f"{series[y * 12 - 1][0]:.0f} ({series[y * 12 - 1][1]:.0f})" for y in checkpoints]
        events = band_events([s for s, _ in series], c, cooldown)
        print(f"| {scenario.description} | " + " | ".join(cells) + f" | {len(events)} |")


if __name__ == "__main__":
    main()
