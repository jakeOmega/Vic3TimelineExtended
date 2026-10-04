"""Regenerate carbon-accounting data from production-method recipes.

Writes recipe-derived synthetic credits, covered buildings' fuel emissions and direct
air capture's removal modifier, plus source-capture methods, groups, building
membership, localization, a coverage report and the household heating curve.
PM display values are derived
from merged recipes or the independent removal-capacity parameter and shared
factors/display scale, so their coefficients are never maintained by hand.

Run ``python3 gen_carbon_capture_pms.py [--dry-run | --check]``. No game install
or running server is required. Full server reloads call ``regenerate``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pm_emissions
import pm_carbon_capture
import household_emissions

ROOT = Path(__file__).resolve().parent
unwrap = pm_emissions.unwrap


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False):
    if mod_state is None:
        mod_state = pm_emissions.load_state(root)
    outputs, fuel_methods = pm_emissions.plan_outputs(mod_state, root)
    capture_outputs, capture_counts = pm_carbon_capture.plan_outputs(mod_state, root)
    outputs.update(capture_outputs)
    outputs.update(household_emissions.plan_outputs(mod_state))
    changed_files = []
    for relative, text in outputs.items():
        target = root / relative
        expected = text.encode("utf-8" if relative.suffix == ".md" else "utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed_files.append(str(relative))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed_files), "output": str(pm_emissions.OUTPUT),
            "changed_files": changed_files, "fuel_methods": fuel_methods, **capture_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = regenerate(root=args.root, dry_run=args.dry_run or args.check)
    print(f"{result['output']}: {'changed' if result['changed'] else 'current'}")
    print(f"{result['fuel_methods']} fuel methods; {len(result['changed_files'])} files need updating")
    print(f"{result['capture_buildings']} capture buildings; {result['capture_groups']} groups; "
          f"{result['capture_variants']} tier variants")
    return int(args.check and result["changed"])


if __name__ == "__main__":
    raise SystemExit(main())
