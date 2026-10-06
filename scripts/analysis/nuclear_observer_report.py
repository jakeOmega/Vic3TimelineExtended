"""Summarize TE_NUCLEAR records from an observer game's debug.log.

Usage: python3 scripts/analysis/nuclear_observer_report.py /path/to/debug.log
Use --json to export the same counters for comparisons between campaigns.
A log starting halfway through a game is a partial observation, not a lifetime
record. Unresolved numeric templates are reported and excluded from expectations.
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


PREFIX = "TE_NUCLEAR: "


def read_records(lines):
    for line in lines:
        if PREFIX not in line:
            continue
        fields = {}
        for field in line.split(PREFIX, 1)[1].strip().split(";"):
            key, sep, value = field.strip().partition("=")
            if sep:
                fields[key] = value.strip()
        if fields.get("type"):
            yield fields


def summarize(records):
    kinds, families, actions, outcomes = Counter(), Counter(), Counter(), Counter()
    countries, crises, exchanges = set(), set(), set()
    exposure = defaultdict(lambda: {"country_weeks": 0, "expected_incidents": 0.0})
    unresolved = 0
    for r in records:
        kind = r["type"]
        kinds[kind] += 1
        if r.get("country"):
            countries.add(r["country"])
        for name, collection in (("crisis", crises), ("exchange", exchanges)):
            value = r.get(name, "0").replace(",", "")
            if value.isdigit() and int(value) > 0:
                collection.add(value)
        if kind == "incident":
            families[r.get("family", "unknown")] += 1
        elif kind == "action":
            actions[r.get("action", "unknown")] += 1
        elif kind == "crisis_end":
            outcomes[r.get("outcome", "unknown")] += 1
        elif kind == "risk":
            try:
                rate = float(r["incident_weekly_permille"])
                danger = float(r["danger"])
                if not math.isfinite(rate) or not math.isfinite(danger) or not 0 <= rate <= 1000 or not 0 <= danger <= 100:
                    raise ValueError("invalid exposure")
            except (KeyError, ValueError):
                unresolved += 1
                continue
            # Mirror the integer two-stage random, rounding halves upward.
            rolled = math.floor(rate * 10 + .5) / 10000 if rate <= 10 else (
                math.floor(rate + .5) / 1000 if rate <= 100 else math.floor(rate / 10 + .5) / 100)
            band = str(min(3, int(danger) // 25))
            exposure[band]["country_weeks"] += 1
            exposure[band]["expected_incidents"] += rolled
    return {
        "records": sum(kinds.values()), "countries": len(countries),
        "observed_crisis_ids": len(crises), "observed_exchange_ids": len(exchanges),
        "record_types": dict(sorted(kinds.items())),
        "meaningful_incidents": sum(v for k, v in families.items() if k != "routine_mishap"),
        "routine_mishaps": families["routine_mishap"],
        "incident_families": dict(sorted(families.items())),
        "actions": dict(sorted(actions.items())), "crisis_outcomes": dict(sorted(outcomes.items())),
        "exposure_by_danger_band": dict(sorted(exposure.items())), "unresolved_risk_records": unresolved,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("log", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    with args.log.open(encoding="utf-8-sig", errors="replace") as lines:
        report = summarize(read_records(lines))
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"{report['records']} records; {report['countries']} countries; "
          f"{report['observed_crisis_ids']} crisis IDs; {report['observed_exchange_ids']} exchange IDs")
    print(f"Meaningful incidents: {report['meaningful_incidents']}; routine mishaps: {report['routine_mishaps']}")
    for section in ("incident_families", "crisis_outcomes", "actions"):
        print(f"\n{section.replace('_', ' ').title()}:")
        for key, count in report[section].items():
            print(f"  {key}: {count}")
    print("\nExposure (weekly meaningful incident rolls):")
    for band, row in report["exposure_by_danger_band"].items():
        print(f"  band {band}: {row['country_weeks']} country-weeks; "
              f"expected incidents {row['expected_incidents']:.2f}")
    if report["unresolved_risk_records"]:
        print(f"Unresolved or invalid numeric risk records: {report['unresolved_risk_records']}")


if __name__ == "__main__":
    main()
