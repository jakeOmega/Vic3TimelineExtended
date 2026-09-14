#!/usr/bin/env python3
"""Regenerate `localization_accessor_vanilla_extras.py` from the live vanilla loc.

Vanilla loc is engine-validated, so every `accessor 'X' is not valid on type 'T'`
flag the localization accessor audit raises against it is a catalog gap. This
folds each one back in as a value-returning accessor, rewrites the extras file
sorted, then re-audits and prints what is left. Re-run after every vanilla
patch (runbook § 4); `test_vanilla_loc_has_minimal_unreviewed_flags` fails
when it is stale.

Residual flags are not folded: they are vanilla typos (one known) or chains
through a type-changing accessor, which belong in `_BUILTIN_ACCESSORS_BY_TYPE`
in `localization_accessor_audit.py` with their real return type.

Usage: python3 scripts/generators/fold_vanilla_loc_accessors.py [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import path_constants  # noqa: E402

EXTRAS = REPO / "localization_accessor_vanilla_extras.py"
FLAG_RE = re.compile(r"accessor '([A-Za-z0-9_]+)' is not valid on type '([a-z_]+)'")


def _audit_vanilla():
    import localization_accessor_audit as audit_mod
    import localization_accessor_vanilla_extras as extras_mod
    importlib.reload(extras_mod)
    importlib.reload(audit_mod)
    loc_dir = os.path.join(path_constants.base_game_path, "game", "localization", "english")
    result = audit_mod.audit(loc_dir, engine_docs_dir=str(REPO / "docs" / "engine"))
    return extras_mod, [f for f in result.flags if not f.exemption]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report gaps without rewriting")
    args = parser.parse_args()

    extras_mod, flags = _audit_vanilla()
    catalog = {t: dict(a) for t, a in extras_mod.VANILLA_EXTRACTED_ACCESSORS.items()}
    added = []
    for flag in flags:
        m = FLAG_RE.search(flag.reason)
        if m and m.group(1) not in catalog.setdefault(m.group(2), {}):
            catalog[m.group(2)][m.group(1)] = "value"
            added.append(f"{m.group(2)}.{m.group(1)}")
    print(f"vanilla unreviewed flags: {len(flags)}; new accessors: {len(added)}")
    if args.dry_run or not added:
        for name in added:
            print(f"  + {name}")
        return 0

    src = EXTRAS.read_text(encoding="utf-8")
    lines = [src[: src.index("VANILLA_EXTRACTED_ACCESSORS = {")] + "VANILLA_EXTRACTED_ACCESSORS = {"]
    for typ in sorted(catalog):
        lines.append(f'    "{typ}": {{')
        lines += [f'        "{acc}": "{ret}",' for acc, ret in sorted(catalog[typ].items())]
        lines.append("    },")
    lines.append("}\n")
    EXTRAS.write_text("\n".join(lines), encoding="utf-8")

    _, residual = _audit_vanilla()
    print(f"rewrote {EXTRAS.name}; residual vanilla flags: {len(residual)}")
    for flag in residual:
        print(f"  {flag.key} | {flag.chain} | {flag.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
