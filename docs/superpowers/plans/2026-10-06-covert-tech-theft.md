# Covert Tech Theft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Industrial and military espionage operations steal technology progress from their target each month, replacing the two +15% tech-spread modifiers, with each operation's record shown on its row.

**Architecture:** A regenerator (`scripts/generators/gen_covert_tech_theft.py`) reads every technology's category and era plus the era costs and covert multipliers, and writes per-technology Paradox script with literal amounts (the engine's `add_technology_progress` accepts no script value). A hand-written loop in the covert monthly pass calls the generated per-category steal effect for each established espionage operation. The operation row shows the container's `iw_stolen_total` and a generated custom-loc lookup of `iw_stolen_last`.

**Tech Stack:** Paradox Clausewitz script (`.txt`, `.gui`, `.yml`), Python 3.11+ (`unittest`, `ModState` from `mod_state.py`, `vanilla_parsed` snapshot).

**Spec:** `docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md`

## Global Constraints

- Work in the sparse worktree `~/src/vic3te-covert-tech-theft` on branch `feat/covert-tech-theft`. Never `POST /reload` from it (it regenerates the main checkout).
- Python: use `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` (the worktree has no `.venv`). Code must compile on Python 3.11: no f-string that reuses its own quote inside braces.
- Paradox `.txt`: tab indentation, exactly one UTF-8 BOM (`utf-8-sig`). Run `scripts/format_paradox_tabs.py --check` on every touched `.txt`.
- Localization: add keys to an existing `*_l_english.yml`, then run `organize_loc.py` and commit everything it moved. Use `#b X#!`-style formatting, never `[b]`.
- Amounts: era cost × `covert_tech_theft_share` (0.05) × phase×priority multiplier, rounded half up. Multipliers: establishing 1 / 1.35 / 1.6, fully operational 2 / 2.7 / 3.2 (read from script values, never hard-coded).
- Theft runs only for operations at Establishing or later (`covert_op_is_established`). Each operation steals on its own.
- Pick order: current research if in the category and the target has it; else random tech in the category that the target has, we lack and `can_research`; else nothing.
- Never stage with `git commit -a`; add files by path. End every commit message with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01J2EaUa3ZdcFNgrFLV8zem4
  ```

## Review Focus

1. **The target no longer exists** (annexed, formed into another country) while the operation runs: no theft, no error, no theft from a previous operation's target. Test: Task 3 `test_steal_loop_sets_target_inside_exists_guard` and Task 2 `test_target_reads_are_guarded`.
2. **The target has nothing left to steal:** `random_list` must not run with every entry disabled. Test: Task 2 `test_random_list_behind_stealable_guard`.
3. **A technology with missing prerequisites or `can_research = no`** must never be picked. Test: Task 1 `test_excludes_society_and_unresearchable`, Task 2 `test_every_random_entry_checks_can_research`.
4. **The operator researches something outside the category, or the target lacks it:** falls through to the random pick, never grants the current research. Test: Task 2 `test_ladder_branch_requires_research_and_target`.
5. **An old save or a fresh operation** (container without `iw_stolen_total`) shows "nothing yet", not "0, latest (blank)". Test: Task 4 `test_row_lines_are_complementary`.

---

### Task 1: Theft share constant and generator data layer

**Files:**
- Modify: `common/script_values/covert_warfare_script_values.txt` (after `covert_op_phase_full_mult = 2`, ~line 125; section 4 comment ~line 503; section 5 display values)
- Create: `scripts/generators/gen_covert_tech_theft.py`
- Test: `test_gen_covert_tech_theft.py`

**Interfaces:**
- Produces (used by Tasks 2–4):
  - `gen.ROOT: Path` (repo root of the module's checkout)
  - `gen.CATEGORIES = ("production", "military")`
  - `@dataclass(frozen=True) class Tech: key: str; category: str; era: int; index: int`
  - `@dataclass(frozen=True) class Constants: share, full, pri2, pri3: Decimal` with `multipliers() -> tuple[Decimal, ...]` ordered (est p1, est p2, est p3, full p1, full p2, full p3)
  - `gen.unwrap(value)`, `gen.load_state(root: Path = ROOT) -> ModState`, `gen.tech_catalog(mod_state) -> list[Tech]`, `gen.read_constants(mod_state) -> Constants`, `gen.read_era_costs(root: Path = ROOT) -> dict[int, int]`, `gen.amounts(era_cost: int, constants: Constants) -> list[int]`
  - Script values `covert_tech_theft_share` (0.05) and `covert_tech_theft_share_percent_display` (5)

- [ ] **Step 1: Write the failing tests**

Create `test_gen_covert_tech_theft.py`:

```python
"""gen_covert_tech_theft: amounts, technology catalog, rendered guards, committed output.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_covert_tech_theft as gen  # noqa: E402

LIVE = gen.Constants(share=Decimal("0.05"), full=Decimal("2"), pri2=Decimal("1.35"), pri3=Decimal("1.6"))


class AmountTest(unittest.TestCase):
    def test_era_7_amounts(self):
        self.assertEqual(gen.amounts(65000, LIVE), [3250, 4388, 5200, 6500, 8775, 10400])

    def test_half_rounds_up(self):
        # 17,500 x 0.05 x 2.7 = 2,362.5
        self.assertEqual(gen.amounts(17500, LIVE)[4], 2363)


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.catalog = gen.tech_catalog(cls.state)
        cls.by_key = {tech.key: tech for tech in cls.catalog}

    def test_reads_live_constants(self):
        self.assertEqual(gen.read_constants(self.state), LIVE)

    def test_era_costs(self):
        costs = gen.read_era_costs(ROOT)
        self.assertEqual(sorted(costs), list(range(1, 13)))
        self.assertEqual((costs[1], costs[7], costs[12]), (7500, 65000, 2000000))

    def test_categories_and_eras(self):
        self.assertEqual((self.by_key["railways"].category, self.by_key["railways"].era), ("production", 2))
        self.assertEqual((self.by_key["ICBMs"].category, self.by_key["ICBMs"].era), ("military", 7))
        self.assertEqual({tech.era for tech in self.catalog}, set(range(1, 13)))

    def test_excludes_society_and_unresearchable(self):
        self.assertNotIn("mass_media", self.by_key)  # society: no operation steals it
        self.assertNotIn("sericulture", self.by_key)  # can_research = no

    def test_indices_unique_from_one(self):
        self.assertEqual([tech.index for tech in self.catalog], list(range(1, len(self.catalog) + 1)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'gen_covert_tech_theft'`

- [ ] **Step 3: Add the share constant and its display value**

In `common/script_values/covert_warfare_script_values.txt`, directly after `covert_op_phase_full_mult = 2`, add:

```paradox

# Technology theft (2026-10): an espionage operation's monthly progress at base
# strength, as a share of the stolen technology's era cost. add_technology_progress
# takes no script value, so scripts/generators/gen_covert_tech_theft.py reads this
# and writes the literal amounts: re-run it (or /reload) after changing it.
covert_tech_theft_share = 0.05
```

Replace the section 4 comment

```paradox
# Retired: the check is the trigger covert_op_target_ahead_in_tech
# (covert_warfare_triggers.txt), evaluated per operation. The script value it
# replaced read one saved target, the last in iw_ops.
```

with

```paradox
# Retired: espionage steals technology instead of checking a lead in technology
# count (2026-10). The launch check is covert_tech_stealable_production
# (covert_tech_theft_generated.txt in common/scripted_triggers).
```

In section 5 (display values), directly after the `intelligence_capacity_display = { … }` block, add:

```paradox
# The theft share as a whole percent, for tooltips.
covert_tech_theft_share_percent_display = {
	value = covert_tech_theft_share
	multiply = 100
}
```

- [ ] **Step 4: Write the generator's data layer**

Create `scripts/generators/gen_covert_tech_theft.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py -v`
Expected: 7 tests, OK. If `test_era_costs` fails on the parser's shape, print `ParadoxFileParser().parse_file(...)` data for `era_1` and adjust `read_era_costs`' unwrapping, not the test.

- [ ] **Step 6: Check formatting and commit**

```bash
python3 scripts/format_paradox_tabs.py --check common/script_values/covert_warfare_script_values.txt
git add common/script_values/covert_warfare_script_values.txt scripts/generators/gen_covert_tech_theft.py test_gen_covert_tech_theft.py
git commit -m "Covert tech theft: share constant and generator data layer"   # plus the two attribution lines
```

---

### Task 2: Render the generated script, write it, register the regenerator

**Files:**
- Modify: `scripts/generators/gen_covert_tech_theft.py` (append rendering, `plan_outputs`, `regenerate`, `main`)
- Create (generated): `common/scripted_effects/covert_tech_theft_generated.txt`, `common/scripted_triggers/covert_tech_theft_generated.txt`, `common/customizable_localization/covert_tech_theft_generated.txt`
- Modify: `mod_state_server.py` (`POST_LOAD_REGENERATORS`, ~line 8971)
- Modify: `CLAUDE.md`, `docs/guides/python_tools.md` (~line 34 table), `docs/auto_generated_files.md` (~line 32 table)
- Test: `test_gen_covert_tech_theft.py`

**Interfaces:**
- Consumes: Task 1's `Tech`, `Constants`, `tech_catalog`, `read_constants`, `read_era_costs`, `amounts`, `load_state`.
- Produces:
  - `gen.EFFECTS_OUT`, `gen.TRIGGERS_OUT`, `gen.CUSTOM_LOC_OUT: Path` (repo-relative)
  - `gen.render_grant(era: int, values: list[int]) -> str`, `gen.render_steal(category: str, techs: list[Tech]) -> str`, `gen.render_stealable(category: str, techs: list[Tech]) -> str`, `gen.render_custom_loc(techs: list[Tech]) -> str`
  - `gen.plan_outputs(mod_state, root: Path = ROOT) -> dict[Path, str]`, `gen.regenerate(mod_state=None, *, root=ROOT, dry_run=False) -> dict`
  - Script contract (Task 3 calls these): country scope = operator (ROOT), `scope:iw_op` = operation container, `scope:iw_theft_target` = target country.
    - `covert_tech_steal_production = yes`, `covert_tech_steal_military = yes`
    - `covert_tech_stealable_production = { TARGET = <country scope> }`, `covert_tech_stealable_military = { TARGET = <country scope> }` (evaluated in the would-be operator's scope)
    - Container variables `iw_stolen_total` (sum of progress) and `iw_stolen_last` (the latest `Tech.index`)
    - Custom loc `covert_stolen_tech_name` (`type = container`)

- [ ] **Step 1: Write the failing tests**

Append to `test_gen_covert_tech_theft.py`, above `if __name__ == "__main__":`:

```python
class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.catalog = gen.tech_catalog(cls.state)
        cls.production = [tech for tech in cls.catalog if tech.category == "production"]
        cls.steal = gen.render_steal("production", cls.production)
        cls.outputs = gen.plan_outputs(cls.state, ROOT)

    def test_grant_branches_in_scaled_modifier_order(self):
        text = gen.render_grant(7, [3250, 4388, 5200, 6500, 8775, 10400])
        order = [text.index(f"progress = {amount} ") for amount in (10400, 8775, 6500, 5200, 4388, 3250)]
        self.assertEqual(order, sorted(order))
        self.assertLess(text.index("covert_op_is_fully_operational"), text.index("covert_op_is_established"))
        self.assertEqual(text.count("set_variable = { name = iw_stolen_last value = $IDX$ }"), 6)

    def test_ladder_branch_requires_research_and_target(self):
        ladder = self.steal[: self.steal.index("random_list = {")]
        self.assertEqual(ladder.count("is_researching_technology = "), len(self.production))
        self.assertEqual(
            ladder.count("scope:iw_theft_target ?= { has_technology_researched = "), len(self.production)
        )

    def test_random_list_behind_stealable_guard(self):
        guard = self.steal.index("covert_tech_stealable_production = { TARGET = scope:iw_theft_target }")
        self.assertLess(guard, self.steal.index("random_list = {"))

    def test_every_random_entry_checks_can_research(self):
        entries = self.steal[self.steal.index("random_list = {"):]
        self.assertEqual(entries.count("\t1 = {"), len(self.production))
        self.assertEqual(entries.count("can_research = "), len(self.production))

    def test_target_reads_are_guarded(self):
        for text in self.outputs.values():
            self.assertNotIn("scope:iw_theft_target = {", text)
            self.assertNotIn("$TARGET$ = {", text)

    def test_custom_loc_maps_every_index_to_its_key(self):
        text = self.outputs[gen.CUSTOM_LOC_OUT]
        self.assertIn("type = container", text)
        for tech in self.catalog:
            self.assertIn(f"trigger = {{ var:iw_stolen_last = {tech.index} }}\n\t\tlocalization_key = {tech.key}\n", text)

    def test_committed_outputs_are_current(self):
        for relative, text in self.outputs.items():
            self.assertEqual((ROOT / relative).read_text(encoding="utf-8-sig"), text, str(relative))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py`
Expected: `RenderTest` errors with `AttributeError: module 'gen_covert_tech_theft' has no attribute 'render_steal'`

- [ ] **Step 3: Append the rendering and file writing**

Append to `scripts/generators/gen_covert_tech_theft.py`:

```python
EFFECTS_OUT = Path("common/scripted_effects/covert_tech_theft_generated.txt")
TRIGGERS_OUT = Path("common/scripted_triggers/covert_tech_theft_generated.txt")
CUSTOM_LOC_OUT = Path("common/customizable_localization/covert_tech_theft_generated.txt")
HEADER = (
    "# AUTO-GENERATED by scripts/generators/gen_covert_tech_theft.py - do not edit manually.\n"
    "# Covert technology theft: docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md\n"
)
EFFECTS_PREAMBLE = (
    "# Scope: country (ROOT = the operator). scope:iw_op is the operation's\n"
    "# container and scope:iw_theft_target its target (covert_ops_steal_tech_all\n"
    "# in covert_warfare_effects.txt sets both). Each grant adds the amount for the\n"
    "# operation's phase x priority and records it on the container.\n"
)
TRIGGERS_PREAMBLE = (
    "# Scope: country (the would-be operator). True when $TARGET$ has researched a\n"
    "# technology of the category that we have not and could research now.\n"
)
CUSTOM_LOC_PREAMBLE = (
    "# The latest technology an operation stole, from its container's\n"
    "# iw_stolen_last. A technology's name key is its own key.\n"
)


def _give(amount: int, depth: int) -> list[str]:
    tab = "\t" * depth
    return [
        f"{tab}add_technology_progress = {{ technology = $TECH$ progress = {amount} }}",
        f"{tab}scope:iw_op = {{",
        f"{tab}\tchange_variable = {{ name = iw_stolen_total add = {amount} }}",
        f"{tab}\tset_variable = {{ name = iw_stolen_last value = $IDX$ }}",
        f"{tab}}}",
    ]


def _priority_ladder(p1: int, p2: int, p3: int) -> list[str]:
    return [
        "\t\tif = {",
        "\t\t\tlimit = { scope:iw_op = { covert_op_priority_at_least = { N = 3 } } }",
        *_give(p3, 3),
        "\t\t}",
        "\t\telse_if = {",
        "\t\t\tlimit = { scope:iw_op = { covert_op_priority_at_least = { N = 2 } } }",
        *_give(p2, 3),
        "\t\t}",
        "\t\telse = {",
        *_give(p1, 3),
        "\t\t}",
    ]


def render_grant(era: int, values: list[int]) -> str:
    """covert_tech_grant_era_<era> = { TECH = <key> IDX = <index> }."""
    est1, est2, est3, full1, full2, full3 = values
    lines = [
        f"covert_tech_grant_era_{era} = {{",
        "\tif = {",
        "\t\tlimit = { scope:iw_op = { covert_op_is_fully_operational = yes } }",
        *_priority_ladder(full1, full2, full3),
        "\t}",
        "\telse_if = {",
        "\t\tlimit = { scope:iw_op = { covert_op_is_established = yes } }",
        *_priority_ladder(est1, est2, est3),
        "\t}",
        "}",
    ]
    return "\n".join(lines) + "\n"


def _candidate(tech: Tech, target: str, depth: int) -> list[str]:
    tab = "\t" * depth
    return [
        f"{tab}NOT = {{ has_technology_researched = {tech.key} }}",
        f"{tab}can_research = {tech.key}",
        f"{tab}{target} ?= {{ has_technology_researched = {tech.key} }}",
    ]


def _grant_call(tech: Tech) -> str:
    return f"covert_tech_grant_era_{tech.era} = {{ TECH = {tech.key} IDX = {tech.index} }}"


def render_steal(category: str, techs: list[Tech]) -> str:
    """Current research first, then a random candidate, else nothing."""
    lines = [f"covert_tech_steal_{category} = {{"]
    for position, tech in enumerate(techs):
        lines += [
            f"\t{'if' if position == 0 else 'else_if'} = {{",
            "\t\tlimit = {",
            f"\t\t\tis_researching_technology = {tech.key}",
            f"\t\t\tscope:iw_theft_target ?= {{ has_technology_researched = {tech.key} }}",
            "\t\t}",
            f"\t\t{_grant_call(tech)}",
            "\t}",
        ]
    lines += [
        "\telse_if = {",
        f"\t\tlimit = {{ covert_tech_stealable_{category} = {{ TARGET = scope:iw_theft_target }} }}",
        "\t\trandom_list = {",
    ]
    for tech in techs:
        lines += [
            "\t\t\t1 = {",
            "\t\t\t\ttrigger = {",
            *_candidate(tech, "scope:iw_theft_target", 5),
            "\t\t\t\t}",
            f"\t\t\t\t{_grant_call(tech)}",
            "\t\t\t}",
        ]
    lines += ["\t\t}", "\t}", "}"]
    return "\n".join(lines) + "\n"


def render_stealable(category: str, techs: list[Tech]) -> str:
    lines = [f"covert_tech_stealable_{category} = {{", "\tOR = {"]
    for tech in techs:
        lines += ["\t\tAND = {", *_candidate(tech, "$TARGET$", 3), "\t\t}"]
    lines += ["\t}", "}"]
    return "\n".join(lines) + "\n"


def render_custom_loc(techs: list[Tech]) -> str:
    lines = ["covert_stolen_tech_name = {", "\ttype = container", "\trandom_valid = no"]
    for tech in techs:
        lines += [
            "\ttext = {",
            f"\t\ttrigger = {{ var:iw_stolen_last = {tech.index} }}",
            f"\t\tlocalization_key = {tech.key}",
            "\t}",
        ]
    lines += ["}"]
    return "\n".join(lines) + "\n"


def plan_outputs(mod_state, root: Path = ROOT) -> dict[Path, str]:
    catalog = tech_catalog(mod_state)
    constants = read_constants(mod_state)
    era_costs = read_era_costs(root)
    by_category = {category: [t for t in catalog if t.category == category] for category in CATEGORIES}
    effects = [HEADER + EFFECTS_PREAMBLE]
    effects += [render_grant(era, amounts(era_costs[era], constants)) for era in sorted({t.era for t in catalog})]
    effects += [render_steal(category, by_category[category]) for category in CATEGORIES]
    triggers = [HEADER + TRIGGERS_PREAMBLE]
    triggers += [render_stealable(category, by_category[category]) for category in CATEGORIES]
    return {
        EFFECTS_OUT: "\n".join(effects),
        TRIGGERS_OUT: "\n".join(triggers),
        CUSTOM_LOC_OUT: HEADER + CUSTOM_LOC_PREAMBLE + "\n" + render_custom_loc(catalog),
    }


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Post-load entry point (mod_state_server.POST_LOAD_REGENERATORS) and CLI body.

    Writes a file only when its content changed, with one UTF-8 BOM.
    """
    if mod_state is None:
        mod_state = load_state(root)
    changed = []
    for relative, text in plan_outputs(mod_state, root).items():
        target = root / relative
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(relative))
            if not dry_run:
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if any output is stale")
    args = parser.parse_args()
    result = regenerate(dry_run=args.dry_run or args.check)
    verb = "stale" if args.check else "would write" if args.dry_run else "wrote"
    for path in result["changed_files"]:
        print(f"{verb}: {path}")
    if not result["changed"]:
        print("covert tech theft: current")
    return int(args.check and result["changed"])


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the files and run the tests**

Run:
```bash
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/generators/gen_covert_tech_theft.py
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py -v
python3 scripts/format_paradox_tabs.py --check common/scripted_effects/covert_tech_theft_generated.txt common/scripted_triggers/covert_tech_theft_generated.txt common/customizable_localization/covert_tech_theft_generated.txt
head -c 6 common/scripted_effects/covert_tech_theft_generated.txt | xxd
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/generators/gen_covert_tech_theft.py --check
```
Expected: three `wrote:` lines; 14 tests OK; tab check exit 0; bytes start `efbb bf23` (one BOM then `#`); `--check` prints `covert tech theft: current` and exits 0. If the tab check fails, fix the renderer's indentation (not the generated file) and regenerate.

- [ ] **Step 5: Register the regenerator and document it in the three roster docs**

`mod_state_server.py`, in `POST_LOAD_REGENERATORS`, directly before `("organize_loc", "organize_loc"),`:

```python
    ("gen_covert_tech_theft",         "scripts.generators.gen_covert_tech_theft"),
```

`CLAUDE.md`:
- In the **Regenerators** bullet, insert `` `gen_covert_tech_theft`, `` directly before `` `organize_loc` ``.
- In the mod state server bullet, change "A cold start runs the 13 regenerators" to "A cold start runs the 14 regenerators".

`docs/guides/python_tools.md`, in the § "Auto-run on server reload" table, add a row directly after the `gen_company_building_cleanup` row:

```markdown
| `gen_covert_tech_theft` | `common/scripted_effects/covert_tech_theft_generated.txt`, `common/scripted_triggers/covert_tech_theft_generated.txt`, `common/customizable_localization/covert_tech_theft_generated.txt` — covert espionage's per-technology theft branches, literal amounts per era × phase × priority, the "anything to steal" triggers and the stolen-technology name lookup. |
```

`docs/auto_generated_files.md`, add a row directly after the `company_building_cleanup_effects.txt` row:

```markdown
| `common/scripted_effects/covert_tech_theft_generated.txt`, `common/scripted_triggers/covert_tech_theft_generated.txt`, `common/customizable_localization/covert_tech_theft_generated.txt` | `scripts/generators/gen_covert_tech_theft.py` (`gen_covert_tech_theft`) | Technologies (vanilla snapshot + `common/technology/technologies/`), `common/technology/eras/00_eras.txt`, `covert_tech_theft_share` and the covert phase/priority multipliers in `common/script_values/covert_warfare_script_values.txt` | One theft branch per production and military technology with its literal amounts (`add_technology_progress` takes no script value). Re-runs on every full `/reload`; `test_gen_covert_tech_theft.py` fails CI when the committed files are stale. |
```

Run:
```bash
python3 scripts/analysis/check_post_load_rosters.py
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_post_load_rosters.py
```
Expected: exit 0 and OK.

- [ ] **Step 6: Commit**

```bash
git add scripts/generators/gen_covert_tech_theft.py test_gen_covert_tech_theft.py common/scripted_effects/covert_tech_theft_generated.txt common/scripted_triggers/covert_tech_theft_generated.txt common/customizable_localization/covert_tech_theft_generated.txt mod_state_server.py CLAUDE.md docs/guides/python_tools.md docs/auto_generated_files.md
git commit -m "Covert tech theft: generate per-technology theft script and register the regenerator"   # plus attribution lines
```

---

### Task 3: Wire the theft into the monthly pass and the diplomatic actions

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (~lines 1105–1215)
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (~lines 91–96)
- Modify: `common/static_modifiers/extra_modifiers.txt` (~lines 6635–6645)
- Modify: `common/diplomatic_actions/covert_operations.txt` (industrial espionage ~672–810, military espionage ~855–960)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (new keys; delete two)
- Test: `test_gen_covert_tech_theft.py`

**Interfaces:**
- Consumes: Task 2's `covert_tech_steal_production` / `_military`, `covert_tech_stealable_production` / `_military = { TARGET = … }`, the `scope:iw_op` / `scope:iw_theft_target` contract; Task 1's `covert_tech_theft_share_percent_display`.
- Produces: `covert_ops_steal_tech_all = yes` (country scope, ROOT = operator; caller guarantees `has_variable_list = iw_ops`), used by Task 4's console event.

- [ ] **Step 1: Write the failing tests**

Append to `test_gen_covert_tech_theft.py`, above `if __name__ == "__main__":`:

```python
def _block(path: str, name: str) -> str:
    """The text of top-level block `name` in a Paradox file, comments stripped."""
    import re

    text = re.sub(r"#[^\n]*", "", (ROOT / path).read_text(encoding="utf-8-sig"))
    start = text.index(f"\n{name} = {{") + 1
    depth = 0
    for position in range(start, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[start : position + 1]
    raise AssertionError(f"unclosed block {name}")


class WiringTest(unittest.TestCase):
    EFFECTS = "common/scripted_effects/covert_warfare_effects.txt"
    ACTIONS = "common/diplomatic_actions/covert_operations.txt"

    def test_steal_loop_sets_target_inside_exists_guard(self):
        loop = _block(self.EFFECTS, "covert_ops_steal_tech_all")
        self.assertIn("covert_op_is_established = yes", loop)
        guard = loop.index("var:iw_target ?= {")
        self.assertLess(guard, loop.index("save_scope_as = iw_theft_target"))
        self.assertLess(loop.index("save_scope_as = iw_theft_target"), loop.index("covert_tech_steal_production = yes"))

    def test_monthly_pass_steals_and_drops_spread(self):
        master = _block(self.EFFECTS, "covert_ops_apply_all_phase_effects")
        self.assertIn("covert_ops_steal_tech_all = yes", master)
        self.assertNotIn("MODIFIER = covert_industrial_espionage }", master)
        self.assertNotIn("covert_military_espionage MONTHS", master)

    def test_actions_use_stealable_check(self):
        industrial = _block(self.ACTIONS, "covert_industrial_espionage_action")
        military = _block(self.ACTIONS, "covert_military_espionage_action")
        self.assertEqual(industrial.count("covert_tech_stealable_production = { TARGET = scope:target_country }"), 2)
        self.assertEqual(military.count("covert_tech_stealable_military = { TARGET = scope:target_country }"), 1)
        for block in (industrial, military):
            self.assertNotIn("techs_researched > ROOT.techs_researched", block)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py`
Expected: `WiringTest` errors (`ValueError: substring not found` for `covert_ops_steal_tech_all`).

- [ ] **Step 3: Add the steal loop and replace the spread applies**

In `common/scripted_effects/covert_warfare_effects.txt`, directly before the comment block that opens `# Master effect: apply every operation type's phase-based effects`, add:

```paradox
# Technology theft (2026-10, docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md):
# every established industrial or military espionage operation adds progress to
# a technology its target has and we lack, at the operation's own phase and
# priority. Each operation steals on its own, from its own target. The
# per-technology branches and amounts are generated
# (covert_tech_theft_generated.txt); this only walks the operations. An
# operation whose target no longer exists steals nothing.
# Scope: country (ROOT = operator); the caller guarantees has_variable_list = iw_ops.
covert_ops_steal_tech_all = {
	every_in_list = {
		variable = iw_ops
		limit = {
			OR = {
				has_tag = iw_op_industrial_espionage
				has_tag = iw_op_military_espionage
			}
			covert_op_is_established = yes
		}
		save_scope_as = iw_op
		var:iw_target ?= {
			save_scope_as = iw_theft_target
			ROOT = {
				if = {
					limit = { scope:iw_op = { has_tag = iw_op_industrial_espionage } }
					covert_tech_steal_production = yes
				}
				else = {
					covert_tech_steal_military = yes
				}
			}
		}
	}
}

```

In `covert_ops_apply_all_phase_effects`, replace

```paradox
		# ---- Industrial Espionage: self modifiers (innovation + tech spread) ----
		# Innovation is always applied; tech spread always applies since target must have tech advantage
		covert_op_apply_self_effect = { TYPE = industrial_espionage MODIFIER = covert_espionage_base }
		covert_op_apply_self_effect = { TYPE = industrial_espionage MODIFIER = covert_industrial_espionage }
```

with

```paradox
		# ---- Industrial Espionage: self modifier (innovation); its technology
		#      theft runs in covert_ops_steal_tech_all below ----
		covert_op_apply_self_effect = { TYPE = industrial_espionage MODIFIER = covert_espionage_base }
```

Then replace everything from `		# ---- Military Espionage: self modifiers (unit stats always, tech spread conditional) ----` through the closing `		}` of the `if = { limit = { any_in_list = { variable = iw_ops has_tag = iw_op_military_espionage } } … }` block (the one ending in `covert_op_add_scaled_modifier = { MODIFIER = covert_military_espionage MONTHS = 3 }` and two closing braces) with:

```paradox
		# ---- Military Espionage: self modifier (unit stats); its technology
		#      theft runs in covert_ops_steal_tech_all below ----
		covert_op_apply_self_effect = { TYPE = military_espionage MODIFIER = covert_military_espionage_unit }
		# Weak counter-intel marker on the TARGET (authority -3; see industrial espionage above)
		covert_op_apply_target_effect = { TYPE = military_espionage MODIFIER = covert_military_espionage_detected }

		# ---- Industrial and military espionage: technology theft ----
		covert_ops_steal_tech_all = yes
```

Read the replaced region before editing; keep the existing `covert_military_espionage_unit` and `_detected` lines once each (they sit inside the replaced range today).

- [ ] **Step 4: Remove the retired trigger and mark the retired modifiers**

`common/scripted_triggers/covert_warfare_triggers.txt`: delete the whole block (comment and body):

```paradox
# The operation's target has researched more technologies than the operator.
# Military espionage's tech-spread bonus comes only from such operations.
# Scope: covert operation container; ROOT = operator country
covert_op_target_ahead_in_tech = {
	var:iw_target ?= { techs_researched > ROOT.techs_researched }
}
```

`common/static_modifiers/extra_modifiers.txt`: replace the comment lines above `covert_industrial_espionage = {` and `covert_military_espionage = {` (`# Applied to SELF when …`) with:

```paradox
# RETIRED 2026-10-06 (covert tech theft): no longer applied; espionage steals
# technology instead. Kept defined so a save carrying it (a three-month timed
# modifier) loads cleanly until it runs out. Delete after 2027-01-06.
```

(The same three lines above each of the two modifiers.)

Run `git grep -n "covert_op_target_ahead_in_tech" -- common events gui` — expect no output.

- [ ] **Step 5: Change the two diplomatic actions**

`common/diplomatic_actions/covert_operations.txt`, `covert_industrial_espionage_action`:

1. In `accept_effect`'s `show_as_tooltip`, delete the line `add_modifier = { name = covert_industrial_espionage }`. Directly after the `show_as_tooltip = { … }` block, add:
   ```paradox
   		custom_tooltip = {
   			text = covert_op_tech_theft_preview_production_tt
   		}
   ```
2. In `accept_effect`, change `text = covert_op_self_effect_note_tt` to `text = covert_op_self_effect_note_espionage_tt`.
3. In `possible`, replace
   ```paradox
   		custom_tooltip = {
   			text = iw_target_tech_advantage_tt
   			scope:target_country = {
   				techs_researched > ROOT.techs_researched
   			}
   		}
   ```
   with
   ```paradox
   		custom_tooltip = {
   			text = iw_target_has_stealable_production_tt
   			covert_tech_stealable_production = { TARGET = scope:target_country }
   		}
   ```
4. In `ai = { will_propose = { … } }`, replace
   ```paradox
   			scope:target_country = {
   				techs_researched > ROOT.techs_researched
   			}
   ```
   with
   ```paradox
   			covert_tech_stealable_production = { TARGET = scope:target_country }
   ```

`covert_military_espionage_action`:

1. In `accept_effect`, change `text = covert_military_espionage_extra_tt` to `text = covert_op_tech_theft_preview_military_tt`, and `text = covert_op_self_effect_note_tt` to `text = covert_op_self_effect_note_espionage_tt`.
2. In `will_propose`, replace the same `scope:target_country = { techs_researched > ROOT.techs_researched }` block with
   ```paradox
   			covert_tech_stealable_military = { TARGET = scope:target_country }
   ```

- [ ] **Step 6: Localization**

In `localization/english/te_miscellaneous_l_english.yml`, delete the lines for `iw_target_tech_advantage_tt` and `covert_military_espionage_extra_tt`, and add (anywhere in the file; `organize_loc.py` files them):

```yaml
 covert_op_tech_theft_preview_production_tt:0 "Each month, progress toward a production [concept_technology] the target has researched and we have not: our current research if it is one, otherwise a random one we could research now. At base strength it is #G [GetPlayer.MakeScope.ScriptValue('covert_tech_theft_share_percent_display')|0]%#! of the technology's era cost."
 covert_op_tech_theft_preview_military_tt:0 "Each month, progress toward a military [concept_technology] the target has researched and we have not: our current research if it is one, otherwise a random one we could research now. At base strength it is #G [GetPlayer.MakeScope.ScriptValue('covert_tech_theft_share_percent_display')|0]%#! of the technology's era cost."
 covert_op_self_effect_note_espionage_tt:0 "Our own modifiers come from our strongest operation of this type and do not add up. Stolen [concept_technology] does: each operation steals from its own target."
 iw_target_has_stealable_production_tt:0 "Target must have researched a production [concept_technology] that we have not and could research now"
```

Run:
```bash
git grep -n "iw_target_tech_advantage_tt\|covert_military_espionage_extra_tt" -- common events gui localization
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python organize_loc.py
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python organize_loc.py --check
```
Expected: the grep prints nothing; `--check` reports the files match.

- [ ] **Step 7: Run the tests and the script audits**

```bash
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python
$PY test_gen_covert_tech_theft.py
for a in script_argument iterator_limit prev_scope empty_effect any_limit duplicate_key script_loc_reference loc_render loc_coverage; do $PY ${a}_audit.py --strict >/dev/null 2>&1; echo "$a=$?"; done
python3 scripts/format_paradox_tabs.py --check common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/static_modifiers/extra_modifiers.txt common/diplomatic_actions/covert_operations.txt
```
Expected: tests OK; every audit `=0`; tab check exit 0. On a non-zero audit, rerun it without `>/dev/null` and fix the finding.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/static_modifiers/extra_modifiers.txt common/diplomatic_actions/covert_operations.txt localization/english/ test_gen_covert_tech_theft.py
git commit -m "Covert tech theft: espionage steals technology monthly; drop the spread modifiers; launch on something to steal"   # plus attribution lines
```

---

### Task 4: Operation row line and console event

**Files:**
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui` (after the detection detail line, ~line 660)
- Modify: `events/te_debug_covert_events.txt` (header list line 8; append event)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `localization/english/te_events_l_english.yml`
- Test: `test_gen_covert_tech_theft.py`

**Interfaces:**
- Consumes: container variables `iw_stolen_total` / `iw_stolen_last` and custom loc `covert_stolen_tech_name` (Task 2); `covert_ops_steal_tech_all` (Task 3); `covert_tech_theft_share_percent_display` (Task 1).
- Produces: loc keys `je_iw_op_row_tech_stolen`, `je_iw_op_row_tech_stolen_none`, `je_iw_op_row_tech_stolen_tt`; console event `te_debug_covert.6`.

- [ ] **Step 1: Write the failing test**

Append to `test_gen_covert_tech_theft.py`, above `if __name__ == "__main__":`:

```python
class RowTest(unittest.TestCase):
    def test_row_lines_are_complementary(self):
        gui = (ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui").read_text(encoding="utf-8-sig")
        espionage = "Or( ScriptContainer.HasTag('iw_op_industrial_espionage'), ScriptContainer.HasTag('iw_op_military_espionage') )"
        self.assertIn(f"[And( {espionage}, ScriptContainer.HasVariable('iw_stolen_total') )]", gui)
        self.assertIn(f"[And( {espionage}, Not( ScriptContainer.HasVariable('iw_stolen_total') ) )]", gui)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py RowTest`
Expected: FAIL (`AssertionError: … not found in …`).

- [ ] **Step 3: Add the row lines**

In `gui/journal_entry_widgets/covert_operations_widget.gui`, directly after the block

```
		# ---- This operation's own monthly detection risk; the arithmetic on hover ----
		widget_je_covert_operation_detail = {
			text = "je_iw_op_row_detection"
			tooltip = "je_iw_op_row_detection_tt"
		}
```

add:

```
		# ---- Espionage only: technology stolen so far and the latest
		#      technology (covert tech theft, 2026-10). "Nothing yet" until the
		#      first theft writes iw_stolen_total ----
		widget_je_covert_operation_detail = {
			visible = "[And( Or( ScriptContainer.HasTag('iw_op_industrial_espionage'), ScriptContainer.HasTag('iw_op_military_espionage') ), ScriptContainer.HasVariable('iw_stolen_total') )]"
			text = "je_iw_op_row_tech_stolen"
			tooltip = "je_iw_op_row_tech_stolen_tt"
		}
		widget_je_covert_operation_detail = {
			visible = "[And( Or( ScriptContainer.HasTag('iw_op_industrial_espionage'), ScriptContainer.HasTag('iw_op_military_espionage') ), Not( ScriptContainer.HasVariable('iw_stolen_total') ) )]"
			text = "je_iw_op_row_tech_stolen_none"
			tooltip = "je_iw_op_row_tech_stolen_tt"
		}
```

Add to `localization/english/te_journal_entries_l_english.yml`:

```yaml
 je_iw_op_row_tech_stolen:0 "[concept_technology] stolen: #G [ScriptContainer.GetVariableValue('iw_stolen_total')|0]#! [concept_innovation], latest #v [ScriptContainer.GetCustom('covert_stolen_tech_name')]#!"
 je_iw_op_row_tech_stolen_none:0 "[concept_technology] stolen: nothing yet"
 je_iw_op_row_tech_stolen_tt:0 "Each month from #Y Establishing#! on, this operation adds progress to a [concept_technology] its target has researched and we have not: our current research if it is one, otherwise a random one we could research now. At base strength that is #G [GetPlayer.MakeScope.ScriptValue('covert_tech_theft_share_percent_display')|0]%#! of the technology's era cost, multiplied by phase and priority. Each espionage operation steals on its own."
```

- [ ] **Step 4: Add the console event**

In `events/te_debug_covert_events.txt`, after the header line `#     event te_debug_covert.5     network intelligence (slice 7)` add:

```
#     event te_debug_covert.6     technology theft (one monthly pass)
```

Append at the end of the file:

```paradox

te_debug_covert.6 = { # REVIEWED 2026-10-06: console-only test event (`event te_debug_covert.6`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { texture = "gfx/event_pictures/espionage_dead_drop.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_default.dds"

	title = te_debug_covert.6.t
	desc = te_debug_covert.6.d
	flavor = te_debug_covert.6.f

	# ---- Technology theft: one monthly pass now. Every established
	#      industrial or military espionage row's total and latest technology
	#      change at once.
	option = {
		name = te_debug_covert.6.a
		default_option = yes
		if = {
			limit = { has_variable_list = iw_ops }
			covert_ops_steal_tech_all = yes
		}
	}
}
```

Add to `localization/english/te_events_l_english.yml` (after the `te_debug_covert.5.*` keys):

```yaml
 te_debug_covert.6.a:0 "Run one month of technology theft now"
 te_debug_covert.6.d:0 "Console-only shortcut for technology theft. None of this can happen in normal play. Seed operations first (te_debug_covert.2) so an espionage operation is running.\n\nEvery established industrial or military espionage operation steals once, as at the start of a month: its row's total and latest technology change at once, and the technology gains the progress in the tree."
 te_debug_covert.6.f:0 "Test harness. Hover the technology to see the progress."
 te_debug_covert.6.t:0 "Covert Test Console: Technology Theft"
```

- [ ] **Step 5: Run the checks**

```bash
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python
$PY test_gen_covert_tech_theft.py
$PY organize_loc.py && $PY organize_loc.py --check
python3 scripts/analysis/check_gui_lint.py
for a in orphaned_event event_image event_context empty_effect gui_reference loc_coverage loc_render script_loc_reference; do $PY ${a}_audit.py --strict >/dev/null 2>&1; echo "$a=$?"; done
python3 scripts/format_paradox_tabs.py --check events/te_debug_covert_events.txt
head -c 3 gui/journal_entry_widgets/covert_operations_widget.gui | xxd
```
Expected: tests OK; loc files match; GUI lint no errors (a warning that `ScriptContainer.GetCustom` is unproven markup is expected — note it for the PR's in-game list); audits `=0`; tab check 0; GUI starts `efbb bf`.

- [ ] **Step 6: Commit**

```bash
git add gui/journal_entry_widgets/covert_operations_widget.gui events/te_debug_covert_events.txt localization/english/ test_gen_covert_tech_theft.py
git commit -m "Covert tech theft: row line for stolen technology and console event te_debug_covert.6"   # plus attribution lines
```

---

### Task 5: Docs and player guide

**Files:**
- Modify: `docs/systems/mod_systems.md` (§ Covert Warfare System: files table ~line 2116–2122; new subsection before `### Election Interference & Electoral Confidence`, ~line 2204)
- Modify: `docs/guides/scripting_best_practices.md` (end of `## Tech Tree Authoring`, before `## System-Scope Cheat Sheet`, ~line 3792)
- Modify: `docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md` (share constant location)
- Modify: `docs/player_guide/11-influence.md` (~lines 320–336, ~line 500)
- Modify (built): `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`

**Interfaces:**
- Consumes: the names and numbers from Tasks 1–4.

- [ ] **Step 1: `mod_systems.md`**

In the Covert Warfare files table, add a row after the `covert_warfare_script_values.txt` row:

```markdown
| `common/scripted_effects/covert_tech_theft_generated.txt`, `common/scripted_triggers/covert_tech_theft_generated.txt`, `common/customizable_localization/covert_tech_theft_generated.txt` | Generated by `scripts/generators/gen_covert_tech_theft.py`: per-technology theft branches and amounts, the "anything to steal" triggers, the stolen-technology name lookup (§ Technology theft) |
```

Directly before `### Election Interference & Electoral Confidence`, add:

```markdown
### Technology theft (2026-10)
- **What:** every industrial espionage operation (production technologies) and military espionage operation (military technologies) that is established steals each month on its own, from its own target: `covert_ops_steal_tech_all` (`covert_warfare_effects.txt`, called from `covert_ops_apply_all_phase_effects`). Progress goes to our current research if it is in the category and the target has it, else to a random technology in the category that the target has, we lack and `can_research`, else nowhere. It replaced the +15 % production and military technology-spread modifiers (`covert_industrial_espionage`, `covert_military_espionage`: kept defined but unapplied so saves load cleanly; delete after 2027-01-06). Design: `docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md`.
- **Amount:** `covert_tech_theft_share` (0.05) × the technology's era cost (`common/technology/eras/00_eras.txt`) × the operation's phase × priority multiplier: 5 % at base, 10 % fully operational, 16 % at priority 3. `add_technology_progress` takes a literal only, so `scripts/generators/gen_covert_tech_theft.py` writes the amounts: twelve `covert_tech_grant_era_N`, each branching on phase × priority the way `covert_op_add_scaled_modifier` does.
- **Generated** (rewritten on full `/reload`; `test_gen_covert_tech_theft.py` fails CI when stale): `covert_tech_steal_production` / `_military` (the current-research ladder, then a `random_list` with one gated entry per technology, behind the stealable check), `covert_tech_stealable_production` / `_military = { TARGET = … }` (the steal guard, industrial espionage's `possible`, both `will_propose`), and `covert_stolen_tech_name` (`type = container` custom loc: technology number → its name key). Technologies with `can_research = no` are left out.
- **Record:** each operation's container keeps `iw_stolen_total` (progress stolen) and `iw_stolen_last` (the latest technology's number); the row prints both (`je_iw_op_row_tech_stolen`, "nothing yet" before the first theft). **Unproven:** `type = container` custom loc has no vanilla or mod precedent. If the row's name is blank, use the spec's named contingency (country-typed per-type records).
- **Console:** `event te_debug_covert.6` runs one theft pass now.
```

- [ ] **Step 2: `scripting_best_practices.md`**

Directly before `## System-Scope Cheat Sheet`, add:

```markdown
### Adding Technology Progress From Script

Probed in game on 2026-10-06 (`te_debug_covert.6`–`.10` on the throwaway branch `probe/tech-progress`):

- `add_technology_progress = { technology = X progress = N }` adds `N` research points to `X`, whether or not it is the current research. Vanilla sizes event bonuses at about a third of the era's cost (`common/technology/eras/00_eras.txt`).
- **`progress` takes a literal only.** A script value is `Malformed token` at load and the tooltip reads "gets 0.00 progress". To vary the amount, branch onto literals (covert tech theft's generated `covert_tech_grant_era_N`) or loop a fixed chunk with `while = { count = <script value> }`.
- `technology =` takes a scope: `technology_being_researched` and a saved scope both work. A country variable can hold a technology scope, and loc names it with `.Var('x').GetTechnology.GetName`.
- **There is no `technology:<key>` link** (`Failed to find a valid event target link`). The engine drops that one effect line; the event still opens. Nothing else turns a key into a technology scope either: there is no technology iterator, and `technology_being_researched` is the only source. No trigger reads a technology scope's era, cost or category, so a rule per technology has to be generated from the files (`scripts/generators/gen_covert_tech_theft.py`).
- `[GetTechnology('key').GetName]` renders the name with the technology's full tooltip on hover.
```

- [ ] **Step 3: Spec correction**

In `docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md` § 2, replace the bullet `- the theft share, 5%, as a constant at the top of the generator.` with:

```markdown
- the theft share, `covert_tech_theft_share = 0.05`, in the same script values
  file, so tooltips can print it (`covert_tech_theft_share_percent_display`).
```

- [ ] **Step 4: Player guide chapter 11**

In `docs/player_guide/11-influence.md`:

Replace the Industrial and Military Espionage table rows with:

```markdown
| Industrial Espionage | You: +5 weekly innovation, and [stolen production technology](#stealing-technology). Target: −3 authority | Target has researched a production technology that you could research now |
| Military Espionage | You: +5% unit offense and defense, and [stolen military technology](#stealing-technology). Target: −3 authority | |
```

Replace the sentence

```markdown
If you run several espionage operations of one type, your gains come from the
strongest and don't add up.
```

with

```markdown
If you run several espionage operations of one type, their bonuses come from the
strongest and don't add up. Stolen technology does add up: each operation steals
from its own target.
```

(Re-wrap the paragraph's lines to the file's width; keep the rest of the paragraph unchanged.)

Directly before the paragraph starting `Hover over an operation before launching it`, add:

```markdown
#### Stealing technology

From its sixth month, each Industrial Espionage operation steals production
technology from its target every month, and each Military Espionage operation
steals military technology. The progress goes to your current research if the
target has researched it. Otherwise it goes to a random technology in that tree
that the target has and you could research now. If there is none, nothing is
stolen that month.

Each theft is 5% of the technology's era cost at base strength, 10% once fully
operational and 16% at priority 3. Progress that reaches a technology's cost
completes it. Each operation's row shows how much it has stolen and the latest
technology.
```

Near line 500, in the AI paragraph, replace `espionage goes to countries ahead in technology or in space` with `espionage goes to countries with technology to steal or ahead in space`.

Run: `git grep -n -i "technology spread" -- docs/player_guide/11-influence.md` — expect no line about espionage.

- [ ] **Step 5: Lint and rebuild the PDF**

```bash
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python
python3 scripts/analysis/check_player_guide_style.py --strict docs/player_guide/11-influence.md
$PY scripts/build_player_guide.py
$PY scripts/build_player_guide.py --check
```
Expected: lint clean (fix wording it flags, don't suppress); build writes the PDF; `--check` exit 0. If `####` headings fail the heading-structure rule, make it `### Stealing technology` and keep the anchor `#stealing-technology`.

- [ ] **Step 6: Commit**

```bash
git add docs/systems/mod_systems.md docs/guides/scripting_best_practices.md docs/superpowers/specs/2026-10-06-covert-tech-theft-design.md docs/player_guide/11-influence.md docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf
git commit -m "Covert tech theft: system docs, engine notes and player guide"   # plus attribution lines
```

---

### Task 6: Full verification and pull request

**Files:** none new.

- [ ] **Step 1: Run every CI check locally**

```bash
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python
$PY -m compileall -q . >/dev/null && echo compile=ok
$PY -m unittest discover -s . -p 'test_*.py' 2>&1 | tail -3
$PY -m ruff check . || ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt')
$PY scripts/analysis/check_localization_files.py
$PY organize_loc.py --check
$PY scripts/analysis/check_post_load_rosters.py
$PY scripts/analysis/check_player_guide_style.py --strict
$PY scripts/build_player_guide.py --check
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image treaty_leverage_side treaty_evaluation_scope event_context silent_variable prev_scope container_timed_variable je_immediate_reset empty_effect change_variable_clamp building_scope_variable principle_tier prestige_good_roster amendment_reachability ideology_lawgroup script_argument script_loc_reference loc_coverage pm_employment gui_reference; do $PY ${a}_audit.py --strict >/dev/null 2>&1 || echo "FAIL $a"; done
$PY kill_character_audit.py --check >/dev/null 2>&1 || echo "FAIL kill_character"
$PY attitude_key_audit.py >/dev/null 2>&1 || echo "FAIL attitude_key"
grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" scripts/generators/gen_covert_tech_theft.py test_gen_covert_tech_theft.py
for f in $(git diff --name-only origin/main -- '*.txt' '*.gui'); do printf '%s ' "$f"; head -c 6 "$f" | xxd -p; done | grep -v " efbbbf" | grep -v "efbbbfefbbbf" || true
```
Expected: compile ok; unittest `OK`; ruff clean; no `FAIL` lines; the f-string grep matches nothing that reuses its own quote inside braces; every changed `.txt`/`.gui` starts with exactly one BOM (no `efbbbfefbbbf`).

- [ ] **Step 2: Independent review**

Request a whole-branch review (superpowers:requesting-code-review) against the spec, with the Review Focus list. Fix confirmed findings in a new commit.

- [ ] **Step 3: Push and open the PR (after the owner says to)**

```bash
git push -u origin feat/covert-tech-theft
gh pr create --base main --title "Covert espionage steals technology progress" --body-file <body file>
```

PR body: summary; the spec link; the in-game checklist from spec § 5 (seven items, plus "the GUI lint's unproven `ScriptContainer.GetCustom` renders"); "Player guide: 11-influence.md (espionage rows, Stealing technology, AI targeting); PDF rebuilt"; ending with

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01J2EaUa3ZdcFNgrFLV8zem4
```
