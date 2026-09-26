"""Expected nuclear-incident rates per posture over a decade of peace.

Mirrors the monthly model in common/script_values/nuclear_deterrence_values.txt
(nd_strain_step, nd_reliability_target/step, nd_incident_permille,
nd_hold_chance) and the family weights in nd_fire_incident
(common/scripted_effects/nuclear_deterrence_effects.txt). Re-run after tuning
any of them and refresh the table in docs/systems/nuclear_crisis_design.md
§0.4; the constants below are copied by hand, so a change there that is not
made here silently makes this table wrong.

Assumptions: one country, no crisis (danger band 0), no war, a plausible
attacker exists (so the Unconfirmed Warning is eligible from heightened
readiness), satellite communications researched, and incidents do not feed
back into strain or reliability. The figures are expectations, not samples.
Automatic Retaliation adds no row: its one launch branch (a .30 accident read
as an attack) needs a war or an acute crisis, and this model is peacetime.

Usage:
    python3 scripts/analysis/nuclear_incident_rates.py [--years N]
"""

import argparse

READINESS_NAMES = {0: "Recessed", 1: "Routine", 2: "Heightened", 3: "High alert"}
AUTHORITY_NAMES = {1: "Central", 3: "Launch on warning"}
BASE_PERMILLE = {0: 0.5, 1: 1, 2: 4, 3: 10}  # nd_incident_permille
WEIGHT_MISHAP, WEIGHT_WARNING, WEIGHT_ALERT = 20, 40, 35  # nd_fire_incident


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def simulate(readiness, safeguards, authority, months):
    strain, reliability = 0.0, 60.0  # nd_init_posture
    p_quiet = 1.0
    warnings = launches = 0.0
    permille = 0.0
    for _ in range(months):
        if readiness == 3:
            step = 5
        elif readiness == 2:
            step = -1 if strain > 40 else 1.5
        else:
            step = -6
        strain = clamp(strain + step, 0, 100)
        target = clamp(55 + 12 * safeguards + 5 - 0.4 * strain, 5, 98)
        reliability = clamp(reliability + (target - reliability) * 0.25, 0, 100)
        permille = min(30, BASE_PERMILLE[readiness] * (1 + strain / 100)
                       * (0.5 + (100 - reliability) / 100))
        p = permille / 1000
        p_quiet *= 1 - p
        weights = {"mishap": WEIGHT_MISHAP}
        if readiness >= 2:
            weights["warning"] = WEIGHT_WARNING
        if readiness == 3 or strain >= 60:
            weights["alert"] = WEIGHT_ALERT
        share = weights.get("warning", 0) / sum(weights.values())
        warnings += p * share
        if authority == 3:
            hold = clamp(reliability + 5 * safeguards - 10, 20, 97)
            launches += p * share * (1 - hold / 100)
    return strain, reliability, permille, 1 - p_quiet, warnings, launches


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", type=int, default=10)
    years = parser.parse_args().years
    print(f"| Readiness | Safeguards | Authority | Strain / reliability after {years} y "
          f"| ‰ per month (end) | P(any incident, {years} y) | Warnings | Launch orders not held |")
    print("|---|---|---|---|---|---|---|---|")
    for readiness in (0, 1, 2, 3):
        for safeguards in (0, 3):
            for authority in ((1, 3) if readiness >= 2 else (1,)):
                strain, rel, pm, p_any, warn, launch = simulate(
                    readiness, safeguards, authority, years * 12)
                print(f"| {READINESS_NAMES[readiness]} | {safeguards} | {AUTHORITY_NAMES[authority]} "
                      f"| {strain:.0f} / {rel:.0f} | {pm:.1f} | {p_any:.0%} | {warn:.2f} | {launch:.2f} |")


if __name__ == "__main__":
    main()
