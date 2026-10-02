#!/usr/bin/env python3
"""Print candidate tax contributors/mutation sites; no game install or writes.

Textual inventory, NOT an engine coverage/feasibility test. Includes the committed
vanilla common JSON snapshot, which does not include vanilla GUI or events.
Usage: python3 scripts/analysis/inventory_tax_probe_sources.py > /tmp/tax-sources.md
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TOKEN = re.compile(
    r"\b(?:tax_(?:income|dividends|land|per_capita|consumption)_add|"
    r"country_tax_income_add|country_consumption_tax_cost_mult|state_tax_\w+|"
    r"building_group_\w+_tax_mult|state_tariff_\w+|"
    r"country_\w+_(?:tariffs_rate|tariffs_level)_add|"
    r"(?:add|remove)_taxed_goods|set_(?:tax_level|import_tariff_level|export_tariff_level)|"
    r"Set(?:TaxLevel|ImportTariffs|ExportTariffs|ImportSubventions|ExportSubventions)\w*|"
    r"(?:Add|Remove|ToggleAdd)ConsumptionTax\w*)\b"
)


def inventory(root=ROOT):
    """Yield deterministic source/line/token tuples; ignore comments in mod files."""
    for folder in ("common", "events", "gui", "vanilla_parsed/common"):
        for path in sorted((root / folder).rglob("*")):
            if not path.is_file() or path.suffix not in {".txt", ".gui", ".json"}:
                continue
            if "te_debug_tax" in path.name:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                for token in sorted(set(TOKEN.findall(line))):
                    yield path.relative_to(root).as_posix(), number, token


def main():
    print("# Tax contributor / mutation candidates\n")
    print("Textual matches only; inspect scopes/callers and installed vanilla GUI/events.\n")
    print("| Source | Line | Candidate |\n|---|---:|---|")
    for path, line, token in inventory():
        print(f"| `{path}` | {line} | `{token}` |")


if __name__ == "__main__":
    main()
