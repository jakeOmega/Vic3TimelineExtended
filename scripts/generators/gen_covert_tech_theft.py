"""Generate covert technology theft: espionage operations steal technology progress.

Industrial espionage steals production technologies and military espionage
military ones (docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md).
add_technology_progress takes a literal amount only, and script can't read a
technology's era or cost, so this writes one branch per technology with its
amounts already worked out:

* common/scripted_effects/covert_tech_theft_generated.txt:
  covert_tech_grant_era_<N> and covert_tech_steal_<category>
* common/scripted_triggers/covert_tech_theft_generated.txt:
  covert_tech_stealable_<category>
* common/customizable_localization/covert_tech_theft_generated.txt:
  covert_stolen_tech_name

Inputs: technologies (vanilla snapshot + mod), era costs
(common/technology/eras/00_eras.txt), covert_tech_theft_share and the phase and
priority multipliers (common/script_values/covert_warfare_script_values.txt).

Run ``python3 scripts/generators/gen_covert_tech_theft.py [--dry-run | --check]``.
No game install or running server is needed. Full server reloads call
``regenerate``.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from paradox_file_parser import ParadoxFileParser  # noqa: E402

CATEGORIES = ("production", "military")
ERAS_FILE = Path("common/technology/eras/00_eras.txt")


@dataclass(frozen=True)
class Tech:
    key: str
    category: str
    era: int
    index: int


@dataclass(frozen=True)
class Constants:
    share: Decimal
    full: Decimal
    pri2: Decimal
    pri3: Decimal

    def multipliers(self) -> tuple[Decimal, ...]:
        """Establishing priority 1, 2, 3, then fully operational priority 1, 2, 3."""
        one = Decimal(1)
        return (one, self.pri2, self.pri3, self.full, self.full * self.pri2, self.full * self.pri3)


def unwrap(value):
    """Strip the parser's ('=', value) wrappers."""
    while isinstance(value, (tuple, list)) and len(value) == 2 and value[0] == "=":
        value = value[1]
    return value


def load_state(root: Path = ROOT):
    """Technologies and script values: vanilla from the committed snapshot, mod from disk."""
    from mod_state import VANILLA_COMMON_DIRS, ModState
    from vanilla_parsed import load

    kinds = ("Technologies", "Script Values")
    snapshot = load(str(root / "vanilla_parsed"))
    state = ModState(
        {kind: "/nonexistent" for kind in kinds},
        {kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in kinds},
        vanilla_data=snapshot.data,
    )
    if state.parse_failures:
        raise ValueError(f"Cannot generate technology theft from an incomplete parse: {state.parse_failures}")
    return state


def tech_catalog(mod_state) -> list[Tech]:
    """Every stealable technology, sorted by key and numbered from 1.

    Society technologies are left out (no operation steals them), and so is any
    technology defined with can_research = no (vanilla's sericulture).
    """
    techs = mod_state.get_data("Technologies")
    rows = []
    for key in sorted(techs):
        body = unwrap(techs[key])
        category = unwrap(body.get("category"))
        if category not in CATEGORIES or unwrap(body.get("can_research")) == "no":
            continue
        era = int(str(unwrap(body["era"])).removeprefix("era_"))
        rows.append((key, category, era))
    return [Tech(key, category, era, index) for index, (key, category, era) in enumerate(rows, start=1)]


def read_constants(mod_state) -> Constants:
    values = mod_state.get_data("Script Values")

    def number(name: str) -> Decimal:
        return Decimal(str(unwrap(values[name])))

    return Constants(
        share=number("covert_tech_theft_share"),
        full=number("covert_op_phase_full_mult"),
        pri2=number("covert_op_priority_2_effect_mult"),
        pri3=number("covert_op_priority_3_effect_mult"),
    )


def read_era_costs(root: Path = ROOT) -> dict[int, int]:
    parser = ParadoxFileParser()
    parser.parse_file(str(root / ERAS_FILE), apply_directives=False)
    return {
        int(name.removeprefix("era_")): int(unwrap(unwrap(block)["technology_cost"]))
        for name, block in parser.data.items()
    }


def amounts(era_cost: int, constants: Constants) -> list[int]:
    """The six monthly amounts for one era, in Constants.multipliers() order."""
    base = Decimal(era_cost) * constants.share
    return [int((base * mult).quantize(Decimal(1), rounding=ROUND_HALF_UP)) for mult in constants.multipliers()]
