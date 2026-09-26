# Internal Resettlement (Settlement Authority) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-building resettlement system (camp + colony) with one destination-driven Settlement Authority that moves exactly the number it shows, only works on a real frontier, and carries programme-specific costs, consequences and events.

**Architecture:** The building keeps the key `building_resettlement_colony`. Three PM groups (Programme, Settlement, Transport) set capacity, staff, goods and destination effects. A monthly **country** pulse walks the country's Settlement Authorities and, for each, walks its source states in order of eligible population, moving people with `move_partial_pop`. It then refreshes readout modifiers and one volume-scaled political modifier per programme, and rolls events. The frontier is people per km² of real land area, read from a generated per-region table.

**Tech Stack:** Paradox Clausewitz script (Victoria 3), YAML localization, Python 3 (generator plus `unittest` static tests), Pillow and NumPy (generator only).

**Spec:** `docs/superpowers/specs/2026-09-26-internal-resettlement-design.md` (read it first; its Decisions table is settled and not to be re-argued).

## Global Constraints

- The player never selects a culture or religion. No trigger in `resettlement_*` tests `culture =` or `religion =` to pick **who moves**. The only culture reference is the land-pressure *consequence* (§7.3), which reads acceptance.
- Frontier: a new Authority needs density below **2/km²** × `(1 + state_migration_crowding_density_mult)`. It closes at **10/km²** × the same factor.
- Level cap: `base_values` gives **5**, and each of `nationalism`, `civilizing_mission`, `mass_propaganda`, `keynesian_economics` and `civil_rights_movement` gives **+5** (maximum 30).
- Per-pop monthly take is **2%** (**4%** in a Recruitment Drive state). Takes under **100** people are skipped.
- Capacity per level (people a month, half `level_scaled`, half `workforce_scaled`): Land Grants 300, Military Colonies 250, Penal Transportation 100, Organized Colonization 500, Special Settlements 1000, Development Program 800, Rustication 800, Managed Retreat 600. Transport adds Overland 0, Rail and Steamship 200, Motor Transport 400, Airlift 600.
- Transit mortality: Penal Transportation 0.05, Special Settlements 0.15, Rustication 0.01, all others 0.
- IG approval at full intensity: Land Grants rural folk +2 / landowners −2; Military Colonies armed forces +2 / rural folk −2; Penal Transportation intelligentsia −2; Organized Colonization rural folk +2; Special Settlements rural folk −5 / intelligentsia −3; Rustication intelligentsia −5 / petty bourgeoisie −3. **No IG approval in any PM.**
- Intensity reference is 0.0025 of the country's population a year. The volume counter decays by 11/12 each month.
- Declaration violation: `country_prestige_mult = -0.1` at full intensity, half strength under reservations.
- Multiplicative modifiers in resettlement PMs go only in `unscaled` blocks.
- Spelling in keys and loc is American ("program", "colonization"). The spec's prose uses "programme"; that's fine.
- Paradox `.txt` files are tab-indented and start with a UTF-8 BOM. Loc files start with a BOM and `l_english:`.
- Loc formatting uses `#b X#!` / `#N X#!` / `#P X#!`, never `[b]`. Loc describes the mod's effects, not vanilla mechanics.
- Work in the sparse worktree `~/src/Vic3TE-internal-resettlement` (branch `internal-resettlement`). Never run `POST /reload` against the main checkout's server from here, and never `git commit -a`: stage by path.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa
  ```

## Review Focus

These are the failure modes the spec implies but that no static test fully exercises, most likely first. Each has a pinning test in the owning task.

1. **A game with no area table yet** (new game on day 1, or a save from before this branch): every state must read as *not* frontier, not error out, until the table is written. Pinned in Task 2 (`te_region_area_km2` defaults to 1, so density is huge) and Task 1 (the version guard).
2. **A region split between owners**: density must use the whole region's population, not one owner's part. Pinned in Task 2 (`te_region_population` iterates `state_region.every_scope_state`).
3. **Capacity going negative** from the Speculators or Reserves modifiers: the walk must not move a negative number. Pinned in Task 4 (`rs_remaining` is clamped at 0 and every take is guarded by `>= resettlement_min_take`).
4. **A slave pop** reaching `move_partial_pop` (the engine would free it silently): pinned in Task 4 (`resettlement_pop_eligible` starts with `NOT = { is_pop_type = slaves }`).
5. **A law change that retires the running programme** (Guaranteed Liberties passed while Penal Transportation runs): the engine falls back to the group's first PM, and the pulse must pick up the new code the same month. Pinned in Task 4 (`resettlement_set_programme_code` reads the active PM every month and never caches it).

## File map

| File | Responsibility | Task |
|---|---|---|
| `scripts/generators/gen_region_area.py` | Writes the per-region km² table from `provinces.png` | 1 |
| `common/scripted_effects/te_region_area_generated.txt` | Generated: `te_set_region_areas`, `te_set_region_areas_if_stale` | 1 |
| `common/on_actions/te_region_area_on_actions.txt` | Runs the table once per save | 1 |
| `test_region_area.py` | Generated table ↔ map data | 1 |
| `common/script_values/resettlement_values.txt` | Frontier, capacity, shares, intensity values | 2, 4, 5 |
| `common/scripted_triggers/resettlement_triggers.txt` | Frontier, rule, programme and eligibility triggers | 2, 4, 5 |
| `common/game_rules/extra_game_rules.txt` | `internal_resettlement_rule` | 2 |
| `test_resettlement_programme_registry.py` | The `PROGRAMMES` table and every site it pins | 2–8 |
| `common/buildings/resettlement.txt` | The Settlement Authority | 3 |
| `common/production_method_groups/resettlement_pmgs.txt` | The three groups | 3 |
| `common/production_methods/resettlement_pms.txt` | Fifteen PMs | 3 |
| `common/modifier_type_definitions/mod_entity_modifier_types.txt` | Readout types; camp cap removed | 3, 4 |
| `common/static_modifiers/extra_modifiers.txt` | `base_values` cap 1 → 5 | 3 |
| `common/technology/technologies/{modified,era_6,era_7}.txt` | Camp cap → colony cap | 3 |
| `common/scripted_effects/resettlement_effects.txt` | The monthly pulse, the walk, consequences, readouts | 4, 5, 6 |
| `common/static_modifiers/resettlement_modifiers.txt` | Readouts, politics, Declaration and event modifiers | 4, 5, 6 |
| `common/on_actions/resettlement_on_actions.txt` | Hooks the country pulse | 4 |
| `common/decrees/extra_decrees.txt` | Recruitment Drive | 4 |
| `common/scripted_effects/extra_effects.txt`, `common/on_actions/extra_on_actions.txt` | Old transfer removed | 4 |
| `events/resettlement_events.txt` | `resettlement.1`–`.9`, `.20` | 5, 6 |
| `test_un_convention_registry.py` | `violation_modifiers` column | 5 |
| `events/te_debug_resettlement_events.txt` | Console test event | 7 |
| `organize_loc.py`, `common/game_concepts/extra_concepts.txt`, docs | Loc routing, concept, docs | 8 |
| `localization/english/te_*_l_english.yml` | Loc per task, in the file `organize_loc.py` routes each key to | 2–8 |

**Where loc keys go** (so `organize_loc.py` moves nothing):

| Key shape | File |
|---|---|
| `pm_*`, `pmg_*` | `te_production_methods_l_english.yml` |
| `building_*` (incl. `building_resettlement_*_add`) | `te_buildings_l_english.yml` |
| `state_*_add` | `te_modifiers_l_english.yml` |
| `decree_*` | `te_decrees_l_english.yml` |
| `rule_*`, `setting_*` | `te_game_rules_l_english.yml` |
| `resettlement.N.*`, `te_debug_resettlement.N.*` | `te_events_l_english.yml` |
| `resettlement_*` (after Task 8's routing rule) | `te_miscellaneous_l_english.yml` |
| `concept_internal_resettlement*` | `te_concepts_l_english.yml` |

Until Task 8 adds the `resettlement_` routing rule, a later `organize_loc.py` run may move two- and three-token `resettlement_*` keys into `te_concepts_l_english.yml`. Put them in `te_miscellaneous_l_english.yml` from the start; Task 8 makes that stable.

## Test commands (used in every task)

```bash
cd ~/src/Vic3TE-internal-resettlement
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent \
       VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
python3 -m unittest test_resettlement_programme_registry -v      # the registry (from Task 2 on)
python3 -m unittest test_region_area -v                          # Task 1
python3 scripts/format_paradox_tabs.py --check <changed .txt files>
python3 scripts/analysis/check_localization_files.py
```

---

### Task 1: Region land-area table

Script can't iterate a state's provinces, so the frontier test reads each region's area from a variable. A generator writes that variable into a scripted effect, which runs once per save.

**Files:**
- Create: `scripts/generators/gen_region_area.py`
- Create: `common/scripted_effects/te_region_area_generated.txt` (generated by the script above)
- Create: `common/on_actions/te_region_area_on_actions.txt`
- Create: `test_region_area.py`
- Modify: `docs/auto_generated_files.md` (one row), `docs/guides/vanilla_patch_runbook.md` (one line in § 4)

**Interfaces:**
- Produces: state-region variable `te_region_area` (integer km²); global variable `te_region_area_version`; effects `te_set_region_areas` and `te_set_region_areas_if_stale`; on_action `te_region_area_on_action`; Python `gen_region_area.VERSION`, `gen_region_area.land_regions()`.

- [ ] **Step 1: Write the failing test**

Create `test_region_area.py`:

```python
"""The generated land-area table (te_region_area_generated.txt) against the map.

The Settlement Authority's frontier test divides a region's population by its
area in km² (docs/superpowers/specs/2026-09-26-internal-resettlement-design.md
§6). Script cannot count provinces, so scripts/generators/gen_region_area.py
writes the area of every land state region into a scripted effect. A region
missing from it can never be a frontier; a stale version never re-runs in old
saves. This file pins both, and a few areas against the real world.

Run: python3 -m unittest test_region_area -v
"""
import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATED = ROOT / "common/scripted_effects/te_region_area_generated.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_region_area_on_actions.txt"

_spec = importlib.util.spec_from_file_location(
    "gen_region_area", ROOT / "scripts/generators/gen_region_area.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

ENTRY_RE = re.compile(
    r"s:(STATE_[A-Z0-9_]+) = \{ set_variable = \{ name = te_region_area value = (\d+) \} \}")

# Real-world areas (km²) of regions whose map outline matches the real unit.
# The pixel method lands within about 10%; 12% leaves room for map outlines.
REAL_KM2 = {
    "STATE_HOKKAIDO": 83424,
    "STATE_KANSAS": 213100,
    "STATE_ICELAND": 103000,
    "STATE_ILE_DE_FRANCE": 12012,
    "STATE_CEYLON": 65610,
    "STATE_SOUTH_ISLAND": 150437,
}


def _areas():
    return {m.group(1): int(m.group(2))
            for m in ENTRY_RE.finditer(GENERATED.read_text(encoding="utf-8-sig"))}


class RegionAreaTests(unittest.TestCase):
    def test_every_land_region_has_one_positive_area(self):
        text = GENERATED.read_text(encoding="utf-8-sig")
        land = set(gen.land_regions())
        areas = _areas()
        self.assertEqual(set(areas), land)
        for region in land:
            self.assertEqual(len(re.findall(rf"s:{region} = ", text)), 1, region)
            self.assertGreater(areas[region], 0, region)

    def test_no_sea_region_is_listed(self):
        seas = (ROOT / "map_data/state_regions/99_seas.txt").read_text(encoding="utf-8-sig")
        sea_names = set(re.findall(r"(?m)^﻿?(STATE_[A-Z0-9_]+)\s*=", seas))
        self.assertFalse(sea_names & set(_areas()))

    def test_areas_match_the_real_world(self):
        areas = _areas()
        for region, real in REAL_KM2.items():
            ratio = areas[region] / real
            self.assertTrue(0.88 <= ratio <= 1.12, f"{region}: {areas[region]} vs {real} ({ratio:.2f})")

    def test_header_and_version_guard(self):
        text = GENERATED.read_text(encoding="utf-8-sig")
        self.assertTrue(text.startswith("# AUTO-GENERATED by scripts/generators/gen_region_area.py"))
        self.assertIn(f"NOT = {{ global_var:te_region_area_version = {gen.VERSION} }}", text)
        self.assertIn(f"set_global_variable = {{ name = te_region_area_version value = {gen.VERSION} }}", text)

    def test_runs_at_game_start_and_monthly(self):
        text = ON_ACTIONS.read_text(encoding="utf-8-sig")
        for hook in ("on_game_started", "on_monthly_pulse"):
            m = re.search(hook + r"\s*=\s*\{\s*on_actions\s*=\s*\{([^}]*)\}", text)
            self.assertIsNotNone(m, hook)
            self.assertIn("te_region_area_on_action", m.group(1))
        self.assertIn("te_set_region_areas_if_stale = yes", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `python3 -m unittest test_region_area -v`
Expected: FAIL/ERROR (`FileNotFoundError` for `scripts/generators/gen_region_area.py`).

- [ ] **Step 3: Write the generator**

Create `scripts/generators/gen_region_area.py`:

```python
#!/usr/bin/env python3
"""Write te_region_area_generated.txt: every land state region's area in km².

Script cannot iterate a state's provinces, so the Settlement Authority's
frontier test (docs/superpowers/specs/2026-09-26-internal-resettlement-design.md
§6) reads an area stored on the state region. This counts each province's
pixels in the game's map_data/provinces.png, weights every pixel by its map
row, and sums each region's provinces.

The map is close to equal-area between about 50°N and 50°S (14.5 km² a pixel)
and stretched toward the poles. The row weights below were fitted against
Hokkaido, Île-de-France, Montana, Iceland, Kola, Alaska, Ceylon and New
Zealand's South Island (all within 12%; test_region_area.py pins six).

Needs the Victoria 3 install (provinces.png is not in the repo) and Pillow and
NumPy (system python3 has both; the repo .venv does not). Re-run after a vanilla
map change, and bump VERSION so old saves re-read the table:

    python3 scripts/generators/gen_region_area.py [--png PATH]
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

VERSION = 1
OUT = os.path.join(REPO, "common", "scripted_effects", "te_region_area_generated.txt")
STATE_REGIONS = os.path.join(REPO, "map_data", "state_regions")
SEA_FILE = "99_seas.txt"

KM2_PER_PIXEL = 14.5       # between about 50°N and 50°S
EQUATOR_ROW = 2040         # the row the stretch is symmetric about
FLAT_HALF_WIDTH = 990      # rows either side of the equator row before the stretch starts
SLOPE_PER_ROW = 0.012      # km² a pixel lost per row beyond that
MIN_KM2_PER_PIXEL = 4.0

BLOCK_RE = re.compile(r"^﻿?(STATE_[A-Z0-9_]+)\s*=\s*\{(.*?)^\}", re.S | re.M)
PROVINCES_RE = re.compile(r"provinces\s*=\s*\{([^}]*)\}")
HEX_RE = re.compile(r'"x([0-9A-Fa-f]{6})"')


def land_regions(state_regions_dir=STATE_REGIONS):
    """{region: [province colour as int]} for every land state region."""
    out = {}
    for name in sorted(os.listdir(state_regions_dir)):
        if not name.endswith(".txt") or name == SEA_FILE:
            continue
        with open(os.path.join(state_regions_dir, name), encoding="utf-8-sig") as f:
            text = f.read()
        for m in BLOCK_RE.finditer(text):
            p = PROVINCES_RE.search(m.group(2))
            out[m.group(1)] = [int(h, 16) for h in HEX_RE.findall(p.group(1))] if p else []
    return out


def row_weights(height):
    import numpy as np
    rows = np.arange(height)
    w = KM2_PER_PIXEL - SLOPE_PER_ROW * np.maximum(0, np.abs(rows - EQUATOR_ROW) - FLAT_HALF_WIDTH)
    return np.maximum(w, MIN_KM2_PER_PIXEL)


def province_areas(png_path):
    """{province colour as int: km²}."""
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    img = np.asarray(Image.open(png_path).convert("RGB"), dtype=np.uint32)
    height, width, _ = img.shape
    packed = ((img[:, :, 0] << 16) | (img[:, :, 1] << 8) | img[:, :, 2]).ravel()
    weights = np.repeat(row_weights(height), width)
    colours, inverse = np.unique(packed, return_inverse=True)
    sums = np.bincount(inverse, weights=weights)
    return dict(zip(colours.tolist(), sums.tolist()))


def render(areas):
    lines = [
        "# AUTO-GENERATED by scripts/generators/gen_region_area.py — do not edit manually.",
        "# Every land state region's area in km² (row-weighted pixel count of",
        "# map_data/provinces.png). Read by te_region_area_km2",
        "# (common/script_values/resettlement_values.txt). te_region_area_on_action",
        "# runs te_set_region_areas_if_stale; bump VERSION in the generator when the",
        "# table changes so old saves re-read it.",
        "",
        "te_set_region_areas_if_stale = {",
        "\tif = {",
        "\t\tlimit = { NOT = { has_global_variable = te_region_area_version } }",
        "\t\tte_set_region_areas = yes",
        "\t}",
        "\telse_if = {",
        f"\t\tlimit = {{ NOT = {{ global_var:te_region_area_version = {VERSION} }} }}",
        "\t\tte_set_region_areas = yes",
        "\t}",
        "}",
        "",
        "te_set_region_areas = {",
    ]
    for region in sorted(areas):
        lines.append(f"\ts:{region} = {{ set_variable = {{ name = te_region_area value = {areas[region]} }} }}")
    lines.append(f"\tset_global_variable = {{ name = te_region_area_version value = {VERSION} }}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--png", help="path to provinces.png (default: the game install's)")
    args = parser.parse_args()
    png = args.png
    if not png:
        from path_constants import base_game_path
        png = os.path.join(base_game_path, "game", "map_data", "provinces.png")
    by_colour = province_areas(png)
    areas = {}
    for region, colours in land_regions().items():
        areas[region] = max(1, round(sum(by_colour.get(c, 0.0) for c in colours)))
    with open(OUT, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write(render(areas))
    print(f"wrote {len(areas)} regions to {os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the generator and check the output**

Run: `python3 scripts/generators/gen_region_area.py`
Expected: `wrote <N> regions to common/scripted_effects/te_region_area_generated.txt`, where N is the number of land regions (about 675).
Then: `grep -E "STATE_(HOKKAIDO|KANSAS|YAKUTSK) " common/scripted_effects/te_region_area_generated.txt`
Expected: Hokkaido about 83,000, Kansas about 194,000, Yakutsk about 2,000,000.

- [ ] **Step 5: Write the on_action**

Create `common/on_actions/te_region_area_on_actions.txt` (UTF-8 BOM, tabs):

```
# Stores every state region's land area (te_region_area_generated.txt) on the
# region, once per save: at game start for new games, on the first monthly
# pulse for a save from before the table existed or from an older VERSION.
# Read by the Settlement Authority's frontier test (resettlement_values.txt).
on_game_started = {
	on_actions = {
		te_region_area_on_action
	}
}

on_monthly_pulse = {
	on_actions = {
		te_region_area_on_action
	}
}

te_region_area_on_action = {
	effect = {
		te_set_region_areas_if_stale = yes
	}
}
```

- [ ] **Step 6: Document the generator**

In `docs/auto_generated_files.md`, add a table row after the `resources.py` row:

```
| `common/scripted_effects/te_region_area_generated.txt` | `scripts/generators/gen_region_area.py` | the game's `map_data/provinces.png` + `map_data/state_regions/*.txt` (land files; `99_seas.txt` skipped) | One-shot, not a post-load generator: it needs the game install and Pillow/NumPy (system `python3`, not `.venv`). Writes `te_set_region_areas` (one `set_variable = { name = te_region_area … }` per land region, in km²) and `te_set_region_areas_if_stale`. Bump `VERSION` when the table changes so old saves re-read it. `test_region_area.py` pins coverage and six real-world areas. |
```

In `docs/guides/vanilla_patch_runbook.md` § 4, add a line to the command block after `gen_formable_regions.py`:

```
python3 scripts/generators/gen_region_area.py         # common/scripted_effects/te_region_area_generated.txt (bump VERSION if the map changed)
```

- [ ] **Step 7: Run the tests to confirm they pass**

Run: `python3 -m unittest test_region_area -v`
Expected: 5 tests, OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/on_actions/te_region_area_on_actions.txt common/scripted_effects/te_region_area_generated.txt`
Expected: no output, exit 0.

- [ ] **Step 8: Commit**

```bash
git add scripts/generators/gen_region_area.py common/scripted_effects/te_region_area_generated.txt \
        common/on_actions/te_region_area_on_actions.txt test_region_area.py \
        docs/auto_generated_files.md docs/guides/vanilla_patch_runbook.md
git commit -m "feat(resettlement): generated land-area table for every state region

Script cannot iterate a state's provinces, so the Settlement Authority's
frontier test reads each region's area from a generated table: pixel counts
of provinces.png, row-weighted for the map's polar stretch (within 12% of
real areas for six regions). A version guard re-runs it in old saves.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 2: The frontier measure and the game rule

**Files:**
- Create: `common/script_values/resettlement_values.txt`
- Create: `common/scripted_triggers/resettlement_triggers.txt`
- Create: `test_resettlement_programme_registry.py` (helpers plus `FrontierTests`; later tasks add classes)
- Modify: `common/game_rules/extra_game_rules.txt` (append a rule)
- Modify: `localization/english/te_game_rules_l_english.yml`

**Interfaces:**
- Consumes: state-region variable `te_region_area` (Task 1).
- Produces (script values, state scope): `te_region_population`, `te_region_area_km2`, `resettlement_frontier_density`, `resettlement_crowding_scale`, `resettlement_frontier_open_density`, `resettlement_frontier_close_density`, `resettlement_frontier_open_margin`, `resettlement_frontier_close_margin`; constants `resettlement_frontier_open_base = 2`, `resettlement_frontier_close_base = 10`.
- Produces (triggers): `resettlement_state_is_open_frontier` (state), `resettlement_state_frontier_still_open` (state), `resettlement_system_enabled` (any), `resettlement_ai_voluntary_only` (country).
- Produces (game rule): `internal_resettlement_rule` with settings `internal_resettlement_enabled` (default), `internal_resettlement_ai_voluntary`, `internal_resettlement_disabled`.
- Produces (Python, used by every later test class): `read`, `strip_comments`, `block`, `number`, `loc`.

- [ ] **Step 1: Write the failing test**

Create `test_resettlement_programme_registry.py`:

```python
"""The internal resettlement registry: every programme in one table, pinned
against every site that lists programmes by hand.

Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
Adding a programme touches the PM, its loc, the recruitment rule's branch, the
programme-code switch, the transit-mortality table, the volume counter, the
politics modifier, the law gates, the Declaration line and the docs. Nothing in
the engine checks that they agree. PROGRAMMES is the single list; each test
checks one site against it, so a half-added programme fails here, naming the
site. The frontier values and the game rule are pinned here too.

Run: python3 -m unittest test_resettlement_programme_registry -v
"""
import re
import unittest
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent

VALUES = "common/script_values/resettlement_values.txt"
TRIGGERS = "common/scripted_triggers/resettlement_triggers.txt"
RULES = "common/game_rules/extra_game_rules.txt"

RULE_SETTINGS = ("internal_resettlement_enabled", "internal_resettlement_ai_voluntary",
                 "internal_resettlement_disabled")


# ---- helpers -------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block(text, name):
    """Body of the first `name = {` block in text (comments stripped), or None."""
    text = strip_comments(text)
    m = re.search(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def number(body, key):
    """The first `key = <number>` in body, as a float, or None."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body or "")
    return float(m.group(1)) if m else None


def squash(text):
    return " ".join((text or "").split())


def top_level_blocks(text):
    """(name, body) for every top-level `name = {` in text (comments stripped)."""
    text = strip_comments(text)
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield m.group(1), text[m.end():i - 1]


_LOC = None


def loc():
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in sorted((ROOT / "localization/english").glob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([\w.$]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    _LOC[m.group(1)] = m.group(2)
    return _LOC


# ---- the frontier and the game rule (Task 2) -----------------------------------------

class FrontierTests(unittest.TestCase):
    def test_thresholds_are_the_specs(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_frontier_open_base = 2\s*$")
        self.assertRegex(text, r"(?m)^resettlement_frontier_close_base = 10\s*$")

    def test_density_is_region_population_over_area(self):
        text = read(VALUES)
        pop = squash(block(text, "te_region_population"))
        self.assertIn("state_region = { every_scope_state = { add = state_population } }", pop)
        area = block(text, "te_region_area_km2")
        self.assertIn("var:te_region_area", area)
        self.assertEqual(number(area, "value"), 1.0, "no table yet must read as 1 km² (never a frontier)")
        density = squash(block(text, "resettlement_frontier_density"))
        self.assertIn("value = te_region_population", density)
        self.assertIn("divide = te_region_area_km2", density)

    def test_both_thresholds_scale_with_the_crowding_modifier(self):
        text = read(VALUES)
        self.assertIn("modifier:state_migration_crowding_density_mult",
                      block(text, "resettlement_crowding_scale"))
        for name, base in (("resettlement_frontier_open_density", "resettlement_frontier_open_base"),
                           ("resettlement_frontier_close_density", "resettlement_frontier_close_base")):
            body = squash(block(text, name))
            self.assertIn(f"value = {base}", body)
            self.assertIn("multiply = resettlement_crowding_scale", body)

    def test_margins_are_threshold_minus_density(self):
        text = read(VALUES)
        for margin, threshold in (("resettlement_frontier_open_margin", "resettlement_frontier_open_density"),
                                  ("resettlement_frontier_close_margin", "resettlement_frontier_close_density")):
            body = squash(block(text, margin))
            self.assertIn(f"value = {threshold}", body)
            self.assertIn("subtract = resettlement_frontier_density", body)

    def test_frontier_triggers_read_the_margins(self):
        text = read(TRIGGERS)
        self.assertIn("resettlement_frontier_open_margin > 0",
                      squash(block(text, "resettlement_state_is_open_frontier")))
        self.assertIn("resettlement_frontier_close_margin > 0",
                      squash(block(text, "resettlement_state_frontier_still_open")))

    def test_rule_triggers(self):
        text = read(TRIGGERS)
        self.assertIn("NOT = { has_game_rule = internal_resettlement_disabled }",
                      squash(block(text, "resettlement_system_enabled")))
        voluntary = squash(block(text, "resettlement_ai_voluntary_only"))
        self.assertIn("is_ai = yes", voluntary)
        self.assertIn("has_game_rule = internal_resettlement_ai_voluntary", voluntary)

    def test_rule_has_three_settings_default_enabled(self):
        body = block(read(RULES), "internal_resettlement_rule")
        self.assertIsNotNone(body)
        self.assertIn("default = internal_resettlement_enabled", squash(body))
        for setting in RULE_SETTINGS:
            self.assertIn(f"flag = {setting}", squash(block(body, setting)))

    def test_rule_is_localized(self):
        L = loc()
        self.assertIn("rule_internal_resettlement_rule", L)
        for setting in RULE_SETTINGS:
            self.assertIn(f"setting_{setting}", L)
            self.assertIn(f"setting_{setting}_desc", L)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `python3 -m unittest test_resettlement_programme_registry -v`
Expected: ERROR (`FileNotFoundError` for `resettlement_values.txt`).

- [ ] **Step 3: Write the script values**

Create `common/script_values/resettlement_values.txt` (BOM, tabs):

```
# ============================================================================
# INTERNAL RESETTLEMENT — script values
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
# The monthly pulse is resettlement_country_monthly (resettlement_effects.txt).

# ---- The frontier (§6) -----------------------------------------------------
# People per km² below which a new Settlement Authority may be built, and at
# which one closes. Both scale with state_migration_crowding_density_mult.
resettlement_frontier_open_base = 2
resettlement_frontier_close_base = 10

# State scope. Everyone in this state's region, whoever owns each part: the
# frontier is geographic, so a split region is measured as one.
te_region_population = {
	value = 0
	state_region = {
		every_scope_state = {
			add = state_population
		}
	}
}

# State scope. The region's land area in km² (te_region_area_generated.txt).
# 1 until the table has been written, which keeps every state off the frontier.
te_region_area_km2 = {
	value = 1
	state_region = {
		if = {
			limit = { has_variable = te_region_area }
			value = var:te_region_area
		}
	}
	min = 1
}

# State scope. People per km² over the whole region.
resettlement_frontier_density = {
	value = te_region_population
	divide = te_region_area_km2
}

# State scope. The crowding system's own modifier: techs, principles and
# institutions that let a state hold more people raise both thresholds.
resettlement_crowding_scale = {
	value = 1
	add = modifier:state_migration_crowding_density_mult
	min = 0.1
}

resettlement_frontier_open_density = {
	value = resettlement_frontier_open_base
	multiply = resettlement_crowding_scale
}

resettlement_frontier_close_density = {
	value = resettlement_frontier_close_base
	multiply = resettlement_crowding_scale
}

# State scope. Positive while a new Authority may be built here.
resettlement_frontier_open_margin = {
	value = resettlement_frontier_open_density
	subtract = resettlement_frontier_density
}

# State scope. Positive while an existing Authority keeps running.
resettlement_frontier_close_margin = {
	value = resettlement_frontier_close_density
	subtract = resettlement_frontier_density
}
```

- [ ] **Step 4: Write the triggers**

Create `common/scripted_triggers/resettlement_triggers.txt` (BOM, tabs):

```
# ============================================================================
# INTERNAL RESETTLEMENT — scripted triggers
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
# Culture and religion are never tested to choose who moves (Decisions table).

# ---- The frontier (§6) -----------------------------------------------------
# State scope. A new Settlement Authority may be built here.
resettlement_state_is_open_frontier = {
	resettlement_frontier_open_margin > 0
}

# State scope. An existing Settlement Authority keeps running here.
resettlement_state_frontier_still_open = {
	resettlement_frontier_close_margin > 0
}

# ---- The game rule (§10) ---------------------------------------------------
# Any scope. The system runs under this rule setting.
resettlement_system_enabled = {
	NOT = { has_game_rule = internal_resettlement_disabled }
}

# Country scope. An AI country kept to voluntary programmes.
resettlement_ai_voluntary_only = {
	is_ai = yes
	has_game_rule = internal_resettlement_ai_voluntary
}
```

- [ ] **Step 5: Add the game rule**

Append to `common/game_rules/extra_game_rules.txt`:

```

# Internal resettlement: the Settlement Authority
# (docs/superpowers/specs/2026-09-26-internal-resettlement-design.md). "AI
# voluntary only" keeps AI countries off the coercive programmes (Penal
# Transportation, Special Settlements, Rustication); humans keep every programme
# their laws allow. Disabled makes the building impossible and stops the pulse.
internal_resettlement_rule = {
	default = internal_resettlement_enabled

	internal_resettlement_enabled = {
		flag = internal_resettlement_enabled
	}

	internal_resettlement_ai_voluntary = {
		flag = internal_resettlement_ai_voluntary
	}

	internal_resettlement_disabled = {
		flag = internal_resettlement_disabled
	}
}
```

Add to `localization/english/te_game_rules_l_english.yml`, keeping its existing grouping (rule names beside the other `rule_*` keys, settings beside the other `setting_*` keys):

```yaml
 rule_internal_resettlement_rule:0 "Internal Resettlement"
 setting_internal_resettlement_enabled:0 "Internal Resettlement Enabled"
 setting_internal_resettlement_enabled_desc:0 "Countries may build a Settlement Authority on a thinly populated frontier and run government resettlement programs into it, from land grants to penal transportation, as their laws allow."
 setting_internal_resettlement_ai_voluntary:0 "Internal Resettlement: AI Voluntary Only"
 setting_internal_resettlement_ai_voluntary_desc:0 "As enabled, but AI countries run only voluntary programs. Penal Transportation, Special Settlements and Rustication remain open to players."
 setting_internal_resettlement_disabled:0 "Internal Resettlement Disabled"
 setting_internal_resettlement_disabled_desc:0 "The Settlement Authority cannot be built and no resettlement programs run."
```

- [ ] **Step 6: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry -v`
Expected: 8 tests, OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/script_values/resettlement_values.txt common/scripted_triggers/resettlement_triggers.txt common/game_rules/extra_game_rules.txt && python3 scripts/analysis/check_localization_files.py`
Expected: both exit 0.

- [ ] **Step 7: Commit**

```bash
git add common/script_values/resettlement_values.txt common/scripted_triggers/resettlement_triggers.txt \
        common/game_rules/extra_game_rules.txt localization/english/te_game_rules_l_english.yml \
        test_resettlement_programme_registry.py
git commit -m "feat(resettlement): frontier by people per km², and the game rule

People per km² over the whole state region; a frontier opens below 2/km²
and closes at 10/km², both scaled by the crowding density modifier.
internal_resettlement_rule: enabled / AI voluntary only / disabled.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 3: The Settlement Authority and its production methods

This replaces the camp and colony building definitions, all their PMs and PM groups, and the camp's level cap. The monthly transfer still points at the old effect until Task 4; nothing runs the new PMs yet, but the building, costs and destination effects are complete.

**Files:**
- Rewrite: `common/buildings/resettlement.txt`
- Rewrite: `common/production_method_groups/resettlement_pmgs.txt`
- Rewrite: `common/production_methods/resettlement_pms.txt`
- Modify: `common/modifier_type_definitions/mod_entity_modifier_types.txt` (delete `state_building_resettlement_camp_max_level_add`)
- Modify: `common/static_modifiers/extra_modifiers.txt:14` (`base_values` colony cap 1 → 5)
- Modify: `common/technology/technologies/modified.txt` (`nationalism`, `civilizing_mission`, `mass_propaganda` INJECTs), `era_6.txt` (`keynesian_economics`), `era_7.txt` (`civil_rights_movement`): camp cap → colony cap
- Modify: `common/_meta/duplicate_image_allowlist.yml:47` (drop `building_resettlement_camp`)
- Modify: `localization/english/te_buildings_l_english.yml`, `te_production_methods_l_english.yml`, `te_modifiers_l_english.yml`, `te_miscellaneous_l_english.yml`
- Modify: `test_resettlement_programme_registry.py` (add `PROGRAMMES`, `SETTLEMENTS`, `TRANSPORTS` and four test classes)

**Interfaces:**
- Consumes: `resettlement_system_enabled`, `resettlement_state_is_open_frontier`, `resettlement_state_frontier_still_open`, `resettlement_frontier_density` (Task 2).
- Produces: PM keys `pm_resettlement_<key>` for the programmes in `PROGRAMMES`, plus the settlement and transport PMs below. Group keys `pmg_resettlement_programme`, `pmg_resettlement_settlement`, `pmg_resettlement_transportation`. Capacity modifier `state_resettlement_transfer_add` (existing type). Loc splice key `resettlement_declaration_pm_line`.
- Produces (Python): `Programme` namedtuple and `PROGRAMMES` (fields: `key code pm techs laws disallowed coercive capacity mortality politics`), `SETTLEMENTS`, `TRANSPORTS`, `BUILDING_FILE`, `PMG_FILE`, `PM_FILE`.

- [ ] **Step 1: Write the failing tests**

In `test_resettlement_programme_registry.py`, add after the `RULE_SETTINGS` line:

```python
BUILDING_FILE = "common/buildings/resettlement.txt"
PMG_FILE = "common/production_method_groups/resettlement_pmgs.txt"
PM_FILE = "common/production_methods/resettlement_pms.txt"
MODIFIER_TYPES = "common/modifier_type_definitions/mod_entity_modifier_types.txt"
BASE_VALUES = "common/static_modifiers/extra_modifiers.txt"
TECH_FILES = ("common/technology/technologies/modified.txt",
              "common/technology/technologies/era_6.txt",
              "common/technology/technologies/era_7.txt")
CAP_TECHS = ("nationalism", "civilizing_mission", "mass_propaganda",
             "keynesian_economics", "civil_rights_movement")

# ---- The table ----------------------------------------------------------------------
# key         the programme: pm_resettlement_<key>, rs_month_<key>, resettlement_<key>_politics
# code        the value of var:rs_programme on a destination running it (resettlement_set_programme_code)
# techs       unlocking_technologies (any of)
# laws        unlocking_laws (any of)
# disallowed  disallowing_laws
# coercive    carries transit deaths, the Declaration violation and the Declaration line
# capacity    people a month per level (half level_scaled, half workforce_scaled)
# mortality   the share of recruits who die in transit
# politics    its country modifier (§7.2), or None for a programme with no IG reaction
Programme = namedtuple("Programme", "key code techs laws disallowed coercive capacity mortality politics")

PROGRAMMES = (
    Programme("land_grants", 0, (), (), (), False, 300, 0,
              {"interest_group_ig_rural_folk_approval_add": 2, "interest_group_ig_landowners_approval_add": -2}),
    Programme("military_colonies", 1, ("standing_army",), (), (), False, 250, 0,
              {"interest_group_ig_armed_forces_approval_add": 2, "interest_group_ig_rural_folk_approval_add": -2}),
    Programme("penal_transportation", 2, ("law_enforcement",), (), ("law_guaranteed_liberties",), True, 100, 0.05,
              {"interest_group_ig_intelligentsia_approval_add": -2}),
    Programme("organized_colonization", 3, ("railways",), (), (), False, 500, 0,
              {"interest_group_ig_rural_folk_approval_add": 2}),
    Programme("special_settlements", 4, ("mass_propaganda",), ("law_collectivized_agriculture",),
              ("law_guaranteed_liberties", "law_protected_speech", "law_right_of_assembly"), True, 1000, 0.15,
              {"interest_group_ig_rural_folk_approval_add": -5, "interest_group_ig_intelligentsia_approval_add": -3}),
    Programme("development_program", 5, ("keynesian_economics",), (), (), False, 800, 0, None),
    Programme("rustication", 6, ("mass_media",), ("law_single_party_state",), (), True, 800, 0.01,
              {"interest_group_ig_intelligentsia_approval_add": -5,
               "interest_group_ig_petty_bourgeoisie_approval_add": -3}),
    Programme("managed_retreat", 7, ("environmental_movement",), (), (), False, 600, 0, None),
)
PROGRAMME_KEYS = tuple(p.key for p in PROGRAMMES)
COERCIVE = tuple(p for p in PROGRAMMES if p.coercive)
WITH_POLITICS = tuple(p for p in PROGRAMMES if p.politics)

# (key, unlocking technologies)
SETTLEMENTS = (
    ("homesteads", ()),
    ("work_settlements", ()),
    ("planned_towns", ("modern_urban_planning",)),
)
# (key, unlocking technologies, capacity per level)
TRANSPORTS = (
    ("overland", (), 0),
    ("rail_steamship", ("railways",), 200),
    ("motor_transport", ("combustion_engine",), 400),
    ("airlift", ("commercial_aviation",), 600),
)


def pm(key):
    return f"pm_resettlement_{key}"


def list_field(body, field):
    inner = block(body, field)
    return tuple(inner.split()) if inner else ()


def transfer_in(pm_body, scaling):
    return number(block(block(pm_body, "state_modifiers") or "", scaling) or "",
                  "state_resettlement_transfer_add") or 0.0
```

Add these test classes before `if __name__ == "__main__":`:

```python
# ---- the building and its production methods (Task 3) --------------------------------

class GroupTests(unittest.TestCase):
    def test_building_has_the_three_groups_in_order(self):
        body = block(read(BUILDING_FILE), "building_resettlement_colony")
        self.assertEqual(list_field(body, "production_method_groups"),
                         ("pmg_resettlement_programme", "pmg_resettlement_settlement",
                          "pmg_resettlement_transportation"))

    def test_groups_list_the_tables(self):
        text = read(PMG_FILE)
        self.assertEqual(list_field(block(text, "pmg_resettlement_programme"), "production_methods"),
                         tuple(pm(p.key) for p in PROGRAMMES))
        self.assertEqual(list_field(block(text, "pmg_resettlement_settlement"), "production_methods"),
                         tuple(pm(k) for k, _ in SETTLEMENTS))
        self.assertEqual(list_field(block(text, "pmg_resettlement_transportation"), "production_methods"),
                         tuple(pm(k) for k, _, _ in TRANSPORTS))

    def test_codes_are_contiguous_from_zero(self):
        self.assertEqual([p.code for p in PROGRAMMES], list(range(len(PROGRAMMES))))


class ProgrammeTests(unittest.TestCase):
    def test_unlocks_and_law_gates(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            body = block(text, pm(p.key))
            self.assertIsNotNone(body, pm(p.key))
            self.assertEqual(list_field(body, "unlocking_technologies"), p.techs, p.key)
            self.assertEqual(list_field(body, "unlocking_laws"), p.laws, p.key)
            self.assertEqual(list_field(body, "disallowing_laws"), p.disallowed, p.key)

    def test_capacity_is_split_half_and_half(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            body = block(text, pm(p.key))
            self.assertEqual(transfer_in(body, "level_scaled"), p.capacity / 2, p.key)
            self.assertEqual(transfer_in(body, "workforce_scaled"), p.capacity / 2, p.key)

    def test_every_programme_speeds_incorporation_and_colony_growth(self):
        text = read(PM_FILE)
        for p in PROGRAMMES:
            unscaled = block(block(block(text, pm(p.key)), "state_modifiers"), "unscaled")
            self.assertGreater(number(unscaled, "state_incorporation_speed_mult") or 0, 0, p.key)
            self.assertGreater(number(unscaled, "state_colony_growth_speed_mult") or 0, 0, p.key)

    def test_the_declaration_line_is_on_coercive_programmes_only(self):
        L = loc()
        self.assertIn("resettlement_declaration_pm_line", L)
        for p in PROGRAMMES:
            desc = L.get(f"{pm(p.key)}_desc", "")
            self.assertEqual("$resettlement_declaration_pm_line$" in desc, p.coercive, p.key)


class SettlementAndTransportTests(unittest.TestCase):
    def test_settlement_unlocks(self):
        text = read(PM_FILE)
        for key, techs in SETTLEMENTS:
            self.assertEqual(list_field(block(text, pm(key)), "unlocking_technologies"), techs, key)

    def test_homesteads_add_no_arable_land(self):
        body = block(read(PM_FILE), pm("homesteads"))
        self.assertNotIn("arable", body)
        unscaled = block(block(body, "state_modifiers"), "unscaled")
        self.assertGreater(number(unscaled, "building_group_bg_agriculture_throughput_add"), 0)
        self.assertGreater(number(unscaled, "building_group_bg_ranching_throughput_add"), 0)

    def test_every_settlement_adds_level_scaled_pull(self):
        text = read(PM_FILE)
        for key, _ in SETTLEMENTS:
            level = block(block(block(text, pm(key)), "state_modifiers"), "level_scaled")
            self.assertGreater(number(level, "state_migration_pull_add") or 0, 0, key)

    def test_transport_unlocks_and_capacity(self):
        text = read(PM_FILE)
        for key, techs, capacity in TRANSPORTS:
            body = block(text, pm(key))
            self.assertEqual(list_field(body, "unlocking_technologies"), techs, key)
            self.assertEqual(transfer_in(body, "level_scaled") + transfer_in(body, "workforce_scaled"),
                             capacity, key)


class PmHygieneTests(unittest.TestCase):
    def _all_pms(self):
        text = read(PM_FILE)
        names = [pm(p.key) for p in PROGRAMMES] + [pm(k) for k, _ in SETTLEMENTS] + [pm(k) for k, _, _ in TRANSPORTS]
        return {n: block(text, n) for n in names}

    def test_multipliers_only_in_unscaled_blocks(self):
        for name, body in self._all_pms().items():
            for section in ("state_modifiers", "country_modifiers", "building_modifiers"):
                sec = block(body, section) or ""
                for scaling in ("level_scaled", "workforce_scaled", "throughput_scaled"):
                    self.assertNotRegex(block(sec, scaling) or "", r"_mult\s*=", f"{name} {section}.{scaling}")

    def test_no_ig_approval_in_any_pm(self):
        for name, body in self._all_pms().items():
            self.assertNotIn("interest_group_", body, name)

    def test_every_pm_and_group_is_localized(self):
        L = loc()
        for name in self._all_pms():
            self.assertIn(name, L)
            self.assertIn(f"{name}_desc", L)
        for group in ("pmg_resettlement_programme", "pmg_resettlement_settlement",
                      "pmg_resettlement_transportation", "building_resettlement_colony",
                      "building_resettlement_colony_desc"):
            self.assertIn(group, L)


class BuildingTests(unittest.TestCase):
    def test_possible_reads_the_rule_and_both_frontier_gates(self):
        possible = squash(block(block(read(BUILDING_FILE), "building_resettlement_colony"), "possible"))
        for trig in ("resettlement_system_enabled = yes", "resettlement_state_is_open_frontier = yes",
                     "resettlement_state_frontier_still_open = yes"):
            self.assertIn(trig, possible)
        self.assertNotIn("law_closed_borders", possible)

    def test_level_cap_is_five_plus_five_per_tech(self):
        base = block(read(BASE_VALUES), "INJECT:base_values")
        self.assertEqual(number(base, "state_building_resettlement_colony_max_level_add"), 5)
        granted = [name.split(":")[-1]
                   for rel in TECH_FILES for name, body in top_level_blocks(read(rel))
                   if number(body, "state_building_resettlement_colony_max_level_add") == 5]
        self.assertEqual(sorted(granted), sorted(CAP_TECHS))


class OldSystemGoneTests(unittest.TestCase):
    GONE = ("building_resettlement_camp", "pmg_resettlement_method", "state_building_resettlement_camp_max_level_add",
            "resettlement_transfer_effect", "resettlement_transfer_on_action", "pm_homesteading_program",
            "pm_forced_resettlement", "pm_incentivized_relocation", "pm_settler_homesteads",
            "pm_administered_territory", "pm_development_zone", "pm_resettlement_railway",
            "pm_resettlement_steamship", "pm_organized_colonization", "pm_penal_transportation",
            "pm_planned_settlement")

    def test_no_trace_in_script_or_loc(self):
        for sub in ("common", "events", "localization/english", "gui"):
            for path in (ROOT / sub).rglob("*"):
                if path.suffix not in (".txt", ".yml", ".gui") or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                for name in self.GONE:
                    self.assertNotRegex(text, rf"(?<![\w]){name}(?![\w])", f"{name} in {path.relative_to(ROOT)}")
```

`OldSystemGoneTests` also names `resettlement_transfer_effect` and `resettlement_transfer_on_action`, which Task 4 removes. The test fails until the end of Task 4. That's intended: it's the checklist for Task 4's cleanup. Run it by name only from Task 4 on.

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `python3 -m unittest test_resettlement_programme_registry.GroupTests test_resettlement_programme_registry.ProgrammeTests test_resettlement_programme_registry.SettlementAndTransportTests test_resettlement_programme_registry.PmHygieneTests test_resettlement_programme_registry.BuildingTests -v`
Expected: FAIL (groups list the old PMs; `pm_resettlement_land_grants` is missing).

- [ ] **Step 3: Rewrite the building**

Replace all of `common/buildings/resettlement.txt` (BOM, tabs):

```
# =================================================================
# Settlement Authority
# =================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
# One building, in the DESTINATION state. Its Programme PM decides who is
# recruited across the country and how (§3), Settlement what the settlers
# build (§5), Transport how many can be carried (§4). The monthly transfer is
# resettlement_country_monthly (common/scripted_effects/resettlement_effects.txt).
# The key stays building_resettlement_colony so saves keep their buildings.
#
# Frontier only (§6): a new Authority needs fewer than 2 people per km² in the
# region; one already here may add levels until 10 per km², when the pulse
# removes it (the frontier is closed).
# =================================================================
building_resettlement_colony = {
	building_group = bg_resettlement

	city_type = city
	levels_per_mesh = 50

	has_max_level = yes

	production_method_groups = {
		pmg_resettlement_programme
		pmg_resettlement_settlement
		pmg_resettlement_transportation
	}

	icon = "gfx/interface/icons/building_icons/building_government_administration.dds"

	required_construction = construction_cost_low

	possible = {
		custom_tooltip = {
			text = resettlement_possible_rule_tt
			resettlement_system_enabled = yes
		}
		trigger_if = {
			limit = { has_building = building_resettlement_colony }
			custom_tooltip = {
				text = resettlement_possible_still_open_tt
				resettlement_state_frontier_still_open = yes
			}
		}
		trigger_else = {
			custom_tooltip = {
				text = resettlement_possible_open_frontier_tt
				resettlement_state_is_open_frontier = yes
			}
		}
	}

	background = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"

	ai_value = {
		value = 0

		# A frontier to fill, and somewhere at home that needs relief.
		if = {
			limit = {
				resettlement_state_is_open_frontier = yes
				owner = {
					any_scope_state = {
						OR = {
							state_unemployment_rate > 0.05
							migration_crowding_mult > 0
						}
					}
				}
			}
			add = 300
		}

		# The emptier the frontier, the more it is worth.
		if = {
			limit = { resettlement_frontier_density < 0.5 }
			add = 200
		}

		# A soft cap: three new Authorities are plenty for an AI. Existing ones
		# may still add levels.
		if = {
			limit = {
				NOT = { has_building = building_resettlement_colony }
				owner = {
					any_scope_state = {
						count >= 3
						has_building = building_resettlement_colony
					}
				}
			}
			multiply = 0
		}
	}
}
```

- [ ] **Step 4: Rewrite the PM groups**

Replace all of `common/production_method_groups/resettlement_pmgs.txt` (BOM, tabs):

```
# Settlement Authority (common/buildings/resettlement.txt). Design:
# docs/superpowers/specs/2026-09-26-internal-resettlement-design.md §3–§5.
# Order matters: the first PM of each group is the fallback when a law change
# retires the running one. test_resettlement_programme_registry.py pins it.

# Who is recruited across the country, and how.
pmg_resettlement_programme = {
	texture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
	ai_selection = most_productive

	production_methods = {
		pm_resettlement_land_grants
		pm_resettlement_military_colonies
		pm_resettlement_penal_transportation
		pm_resettlement_organized_colonization
		pm_resettlement_special_settlements
		pm_resettlement_development_program
		pm_resettlement_rustication
		pm_resettlement_managed_retreat
	}
}

# What the settlers build on arrival.
pmg_resettlement_settlement = {
	texture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
	ai_selection = most_productive

	production_methods = {
		pm_resettlement_homesteads
		pm_resettlement_work_settlements
		pm_resettlement_planned_towns
	}
}

# How many can be carried each month.
pmg_resettlement_transportation = {
	texture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
	ai_selection = most_productive

	production_methods = {
		pm_resettlement_overland
		pm_resettlement_rail_steamship
		pm_resettlement_motor_transport
		pm_resettlement_airlift
	}
}
```

- [ ] **Step 5: Rewrite the PMs**

Replace all of `common/production_methods/resettlement_pms.txt` (BOM, tabs):

```
# =================================================================
# Settlement Authority production methods
# =================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.
# Every PM sits on the DESTINATION building, so its state_modifiers land on
# the destination state. What happens at the source is script-applied by the
# pulse (resettlement_effects.txt).
#
# Capacity (state_resettlement_transfer_add) is half level_scaled, half
# workforce_scaled: the building hires from a sparse frontier, so a purely
# workforce-scaled capacity could stall at zero before the first settlers
# arrive. The pulse moves exactly the total.
#
# Multiplicative modifiers sit in unscaled blocks only, so levels never
# multiply them. No PM carries IG approval: political reactions are one
# country modifier per programme, scaled by volume (resettlement_*_politics).
# test_resettlement_programme_registry.py pins all of this.
# =================================================================

# =====================================================================
# PROGRAM (pmg_resettlement_programme): who is recruited, and how
# =====================================================================

# Land grants to volunteers: the unemployed and peasants (never under
# Serfdom), Second-class or better. Homestead Act 1862, Dominion Lands Act 1872.
pm_resettlement_land_grants = {
	texture = "gfx/interface/icons/production_method_icons/homesteading.dds"

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 150
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 150
		}
		unscaled = {
			state_incorporation_speed_mult = 0.10
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 5
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 5
			goods_input_services_add = 5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_clerks_add = 100
		}
	}

	ai_value = 200
}

# Soldier-settlers holding a strategic frontier: Russian military settlements,
# Cossack hosts, tondenhei, the Xinjiang bingtuan. Fully accepted volunteers.
pm_resettlement_military_colonies = {
	texture = "gfx/interface/icons/production_method_icons/ownership_bureacrats.dds"

	unlocking_technologies = {
		standing_army
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 125
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 125
		}
		unscaled = {
			state_turmoil_effects_mult = -0.25
			state_incorporation_speed_mult = 0.25
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 5
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 5
			goods_input_small_arms_add = 5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 50
			building_employment_soldiers_add = 100
			building_employment_officers_add = 25
		}
	}

	ai_value = 150
}

# Convicts and the politically unreliable, sent to a remote frontier:
# Australia to 1868, French Guiana, New Caledonia, Sakhalin, the Andamans.
pm_resettlement_penal_transportation = {
	texture = "gfx/interface/icons/production_method_icons/rail_transport.dds"

	unlocking_technologies = {
		law_enforcement
	}

	disallowing_laws = {
		law_guaranteed_liberties
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 50
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 50
		}
		unscaled = {
			state_mortality_mult = 0.03
			state_incorporation_speed_mult = 0.10
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 5
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 3
			goods_input_small_arms_add = 3
		}
		level_scaled = {
			building_employment_bureaucrats_add = 50
			building_employment_soldiers_add = 100
		}
	}

	ai_value = 25
}

# Subsidized passage and land along the railway: Stolypin's resettlement to
# Siberia, 1906–1914. The unemployed, peasants and laborers, Second-class or better.
pm_resettlement_organized_colonization = {
	texture = "gfx/interface/icons/production_method_icons/government_run.dds"

	unlocking_technologies = {
		railways
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 250
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 250
		}
		unscaled = {
			state_incorporation_speed_mult = 0.15
			state_colony_growth_speed_mult = 0.15
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 10
			goods_input_services_add = 5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_clerks_add = 100
		}
	}

	ai_value = 300
}

# Deportation of landholding farmers under collectivization: the Soviet
# special settlements, 1930–1933.
pm_resettlement_special_settlements = {
	texture = "gfx/interface/icons/production_method_icons/ownership_bureacrats.dds"

	unlocking_technologies = {
		mass_propaganda
	}

	unlocking_laws = {
		law_collectivized_agriculture
	}

	disallowing_laws = {
		law_guaranteed_liberties
		law_protected_speech
		law_right_of_assembly
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 500
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 500
		}
		unscaled = {
			state_mortality_mult = 0.05
			state_incorporation_speed_mult = 0.10
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 10
			goods_input_small_arms_add = 10
			goods_input_ammunition_add = 5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_soldiers_add = 150
			building_employment_officers_add = 25
		}
	}

	ai_value = 25
}

# State-funded settlement with jobs and housing waiting: Virgin Lands 1954,
# FELDA 1956, Transmigrasi, Brasília. Adds skilled workers to the voluntary pool.
pm_resettlement_development_program = {
	texture = "gfx/interface/icons/production_method_icons/government_run.dds"

	unlocking_technologies = {
		keynesian_economics
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 400
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 400
			state_infrastructure_add = 2
		}
		unscaled = {
			state_incorporation_speed_mult = 0.15
			state_colony_growth_speed_mult = 0.15
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 15
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 10
			goods_input_services_add = 15
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_clerks_add = 100
		}
	}

	ai_value = 350
}

# Urban workers sent down to the countryside: China's Down to the Countryside
# movement, 1968–1980.
pm_resettlement_rustication = {
	texture = "gfx/interface/icons/production_method_icons/harvesting_tools.dds"

	unlocking_technologies = {
		mass_media
	}

	unlocking_laws = {
		law_single_party_state
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 400
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 400
		}
		unscaled = {
			state_incorporation_speed_mult = 0.10
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 10
			goods_input_small_arms_add = 5
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_soldiers_add = 100
		}
	}

	ai_value = 25
}

# Moving people out of harm's way, with compensation: the Chernobyl zone,
# Jakarta to Nusantara, Newtok.
pm_resettlement_managed_retreat = {
	texture = "gfx/interface/icons/production_method_icons/government_run.dds"

	unlocking_technologies = {
		environmental_movement
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 300
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 300
		}
		unscaled = {
			state_incorporation_speed_mult = 0.10
			state_colony_growth_speed_mult = 0.10
		}
	}

	country_modifiers = {
		workforce_scaled = {
			country_bureaucracy_cost_add = 10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_paper_add = 10
			goods_input_services_add = 15
		}
		level_scaled = {
			building_employment_bureaucrats_add = 100
			building_employment_clerks_add = 100
		}
	}

	ai_value = 100
}

# =====================================================================
# SETTLEMENT (pmg_resettlement_settlement): what the settlers build
# =====================================================================
# Every settlement adds level-scaled migration pull, so the frontier is less
# likely to become an emigration source while the program runs (§5).

# Virgin soil: newly broken land yields well while the frontier is open. No
# arable land is added; the bonus ends with the building.
pm_resettlement_homesteads = {
	texture = "gfx/interface/icons/production_method_icons/homesteading.dds"

	state_modifiers = {
		level_scaled = {
			state_migration_pull_add = 1
		}
		unscaled = {
			building_group_bg_agriculture_throughput_add = 0.10
			building_group_bg_ranching_throughput_add = 0.10
			building_subsistence_output_add = 1
		}
	}

	ai_value = 200
}

# The settlers work where they land: mines, timber, the railway.
pm_resettlement_work_settlements = {
	texture = "gfx/interface/icons/production_method_icons/crude_tools.dds"

	state_modifiers = {
		level_scaled = {
			state_migration_pull_add = 1
		}
		workforce_scaled = {
			state_infrastructure_add = 1
		}
		unscaled = {
			building_group_bg_mining_throughput_add = 0.10
			building_group_bg_logging_throughput_add = 0.10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_tools_add = 5
		}
		level_scaled = {
			building_employment_laborers_add = 100
		}
	}

	ai_value = 150
}

# A town planned before the first settler arrives: Brasília, the British New
# Towns, Akademgorodok.
pm_resettlement_planned_towns = {
	texture = "gfx/interface/icons/production_method_icons/government_run.dds"

	unlocking_technologies = {
		modern_urban_planning
	}

	state_modifiers = {
		level_scaled = {
			state_migration_pull_add = 1
		}
		workforce_scaled = {
			state_infrastructure_add = 3
			state_migration_pull_add = 2
		}
		unscaled = {
			state_construction_mult = 0.10
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_services_add = 10
		}
		level_scaled = {
			building_employment_engineers_add = 50
		}
	}

	ai_value = 250
}

# =====================================================================
# TRANSPORT (pmg_resettlement_transportation): how many can be carried
# =====================================================================
# Each adds capacity per level (additive, so safe as levels stack) and costs
# transportation. Steamships fold into rail: a PM cannot test for a coast.

pm_resettlement_overland = {
	texture = "gfx/interface/icons/production_method_icons/no_rail_transport.dds"

	ai_value = 0
}

pm_resettlement_rail_steamship = {
	texture = "gfx/interface/icons/production_method_icons/rail_transport.dds"

	unlocking_technologies = {
		railways
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 100
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 100
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_transportation_add = 10
		}
	}

	ai_value = 100
}

pm_resettlement_motor_transport = {
	texture = "gfx/interface/icons/production_method_icons/motorised_logistics.dds"

	unlocking_technologies = {
		combustion_engine
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 200
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 200
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_transportation_add = 15
		}
	}

	ai_value = 200
}

pm_resettlement_airlift = {
	texture = "gfx/interface/icons/production_method_icons/aeroplanes.dds"

	unlocking_technologies = {
		commercial_aviation
	}

	state_modifiers = {
		level_scaled = {
			state_resettlement_transfer_add = 300
		}
		workforce_scaled = {
			state_resettlement_transfer_add = 300
		}
	}

	building_modifiers = {
		workforce_scaled = {
			goods_input_transportation_add = 20
			goods_input_services_add = 5
		}
	}

	ai_value = 300
}
```

- [ ] **Step 6: Move the level cap and delete the camp's**

- `common/static_modifiers/extra_modifiers.txt:14`: change `state_building_resettlement_colony_max_level_add = 1` to `state_building_resettlement_colony_max_level_add = 5`.
- In `common/technology/technologies/modified.txt` (the `INJECT:nationalism`, `INJECT:civilizing_mission` and `INJECT:mass_propaganda` blocks), `era_6.txt` (`keynesian_economics`) and `era_7.txt` (`civil_rights_movement`): replace `state_building_resettlement_camp_max_level_add = 5` with `state_building_resettlement_colony_max_level_add = 5`. The `INJECT:civilizing_mission` comment "organized colonization becomes possible" becomes `# Civilizing mission: the Settlement Authority grows`. The `INJECT:mass_propaganda` comment is about homelands and stays as it is.
- In `common/modifier_type_definitions/mod_entity_modifier_types.txt`, delete the block `state_building_resettlement_camp_max_level_add = { color = good percent = no }`.
- In `common/_meta/duplicate_image_allowlist.yml:47`, delete the line `  - building_resettlement_camp`. If that leaves the entry with a single building, delete the whole entry (the allowlist only lists images shared by two or more entities).

Verify: `git grep -n "resettlement_camp" -- common localization` should print only the loc lines Step 7 removes.

- [ ] **Step 7: Localization**

In `localization/english/te_buildings_l_english.yml`, delete `building_resettlement_camp` and replace `building_resettlement_colony` with:

```yaml
 building_resettlement_colony:0 "Settlement Authority"
 building_resettlement_colony_desc:0 "A government office that recruits settlers across the country and brings them to this frontier. Its program decides who is recruited and how; its settlement plan decides what they build here. It can be founded only on an open frontier and closes when the region fills up; its build requirements show the numbers."
```

In `te_modifiers_l_english.yml`, delete the two `state_building_resettlement_camp_max_level_add*` lines, and replace the colony and transfer entries:

```yaml
 state_building_resettlement_colony_max_level_add:0 "Max Settlement Authority Level"
 state_building_resettlement_colony_max_level_add_desc:0 "The maximum level of the Settlement Authority in this state."
 state_resettlement_transfer_add:0 "Settlers Moved per Month"
 state_resettlement_transfer_add_desc:0 "How many people this state's Settlement Authority brings here each month, when enough eligible people can be recruited."
```

In `te_production_methods_l_english.yml`, delete the old resettlement PM and group keys that are gone (`pm_homesteading_program`, `pm_organized_colonization`, `pm_forced_resettlement`, `pm_penal_transportation`, `pm_incentivized_relocation`, `pm_settler_homesteads`, `pm_planned_settlement`, `pm_administered_territory`, `pm_development_zone`, `pm_resettlement_railway`, `pm_resettlement_steamship`, `pmg_resettlement_method`). Check each with `git grep -n "<key>" -- common events gui` first; delete only if nothing else uses it. `pm_resettlement_overland`, `pm_resettlement_airlift`, `pmg_resettlement_settlement` and `pmg_resettlement_transportation` keep their keys: replace their lines with the ones below. Then add:

```yaml
 pmg_resettlement_programme:0 "Resettlement Program"
 pmg_resettlement_settlement:0 "Settlement Plan"
 pmg_resettlement_transportation:0 "Transport"
 pm_resettlement_land_grants:0 "Land Grants"
 pm_resettlement_land_grants_desc:0 "Free land for those willing to work it. Recruits the unemployed and peasants of the lower strata who are at least second-class citizens; peasants cannot leave under Serfdom."
 pm_resettlement_military_colonies:0 "Military Colonies"
 pm_resettlement_military_colonies_desc:0 "Soldier-settlers who farm the frontier and hold it. Recruits the unemployed and peasants of the lower strata who are fully accepted. Turmoil in this state has less effect."
 pm_resettlement_penal_transportation:0 "Penal Transportation"
 pm_resettlement_penal_transportation_desc:0 "Convicts and the politically unreliable, shipped to the frontier. Recruits lower-strata pops in which at least a fifth are radicals. Some die on the way, and life here is harsher.$resettlement_declaration_pm_line$"
 pm_resettlement_organized_colonization:0 "Organized Colonization"
 pm_resettlement_organized_colonization_desc:0 "Subsidized passage, land and credit along the railway. Recruits the unemployed, peasants and laborers of the lower strata who are at least second-class citizens."
 pm_resettlement_special_settlements:0 "Special Settlements"
 pm_resettlement_special_settlements_desc:0 "Landholding farmers deported under collectivization. Recruits farmers wherever they are. Many die on the way; the farmers left behind turn radical.$resettlement_declaration_pm_line$"
 pm_resettlement_development_program:0 "Development Program"
 pm_resettlement_development_program_desc:0 "Jobs, housing and schools waiting before the settlers arrive. Recruits as Organized Colonization does, plus machinists, engineers and clerks, at least second-class citizens."
 pm_resettlement_rustication:0 "Rustication"
 pm_resettlement_rustication_desc:0 "Urban workers sent down to the countryside to learn from the peasants. Recruits laborers and clerks outside agriculture. The urban workers left behind turn radical.$resettlement_declaration_pm_line$"
 pm_resettlement_managed_retreat:0 "Managed Retreat"
 pm_resettlement_managed_retreat_desc:0 "Moving people out of harm's way, with compensation. Recruits everyone from coastal states while we suffer coastal flooding, and from states contaminated by a nuclear strike or accident."
 pm_resettlement_homesteads:0 "Homesteads"
 pm_resettlement_homesteads_desc:0 "Settlers break new ground. Farms and ranches here are more productive while the frontier stays open."
 pm_resettlement_work_settlements:0 "Work Settlements"
 pm_resettlement_work_settlements_desc:0 "Settlers are put to work on arrival, in the Authority's own gangs, the mines and the timber camps."
 pm_resettlement_planned_towns:0 "Planned Towns"
 pm_resettlement_planned_towns_desc:0 "Streets, utilities and housing laid out before the settlers arrive."
 pm_resettlement_overland:0 "Overland"
 pm_resettlement_overland_desc:0 "Wagons and marching columns."
 pm_resettlement_rail_steamship:0 "Rail and Steamship"
 pm_resettlement_rail_steamship_desc:0 "Settler trains and chartered steamers carry more people each month."
 pm_resettlement_motor_transport:0 "Motor Transport"
 pm_resettlement_motor_transport_desc:0 "Truck and bus convoys reach where the railway does not."
 pm_resettlement_airlift:0 "Airlift"
 pm_resettlement_airlift_desc:0 "Chartered flights move the greatest numbers."
```

In `te_miscellaneous_l_english.yml`, add the splice line and the building's `possible` tooltips:

```yaml
 resettlement_declaration_pm_line:0 "\n\nIf we are a party to the Universal Declaration of Human Rights, running this program incurs #N Violating the Declaration#!, which grows with the program's size."
 resettlement_possible_rule_tt:0 "Internal resettlement is enabled in the game rules"
 resettlement_possible_open_frontier_tt:0 "This region is an open frontier: fewer than #b [SCOPE.ScriptValue('resettlement_frontier_open_density')|1]#! people per km² (now #b [SCOPE.ScriptValue('resettlement_frontier_density')|1]#!)"
 resettlement_possible_still_open_tt:0 "This frontier is not yet closed: fewer than #b [SCOPE.ScriptValue('resettlement_frontier_close_density')|1]#! people per km² (now #b [SCOPE.ScriptValue('resettlement_frontier_density')|1]#!)"
```

The `[SCOPE.ScriptValue(...)]` form must render in a building's `possible` tooltip. If `loc_render_audit` or the in-game check (Task 9) shows it blank, fall back to the plain numbers (`fewer than 2 people per km²`) and add the density to the building's tooltip in a follow-up.

- [ ] **Step 8: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry.FrontierTests test_resettlement_programme_registry.GroupTests test_resettlement_programme_registry.ProgrammeTests test_resettlement_programme_registry.SettlementAndTransportTests test_resettlement_programme_registry.PmHygieneTests test_resettlement_programme_registry.BuildingTests -v`
Expected: all pass. (`OldSystemGoneTests` still fails on `resettlement_transfer_effect` / `_on_action`; Task 4 fixes it.)
Run: `python3 scripts/format_paradox_tabs.py --check common/buildings/resettlement.txt common/production_method_groups/resettlement_pmgs.txt common/production_methods/resettlement_pms.txt && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.

- [ ] **Step 9: Commit**

```bash
git add common/buildings/resettlement.txt common/production_method_groups/resettlement_pmgs.txt \
        common/production_methods/resettlement_pms.txt common/modifier_type_definitions/mod_entity_modifier_types.txt \
        common/static_modifiers/extra_modifiers.txt common/technology/technologies/modified.txt \
        common/technology/technologies/era_6.txt common/technology/technologies/era_7.txt \
        common/_meta/duplicate_image_allowlist.yml localization/english/te_buildings_l_english.yml \
        localization/english/te_production_methods_l_english.yml localization/english/te_modifiers_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml test_resettlement_programme_registry.py
git commit -m "feat(resettlement): the Settlement Authority and its fifteen production methods

One destination building (key kept for saves) with Program, Settlement and
Transport groups. Capacity is half level-, half workforce-scaled so a sparse
frontier cannot stall it; multipliers only unscaled; no IG approval in PMs.
The camp, its PMs and its level cap are gone; the cap is now 5 + 5 per tech.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 4: The monthly transfer

This task makes the Settlement Authority move people. It adds:
- the country pulse, the walk over source states, and the per-pop take;
- deaths in transit and source unrest;
- land pressure on existing inhabitants;
- the three readout modifiers and the frontier closure (with its notification, `resettlement.9`);
- the Recruitment Drive decree;
- removal of the old transfer.

**Files:**
- Create: `common/scripted_effects/resettlement_effects.txt`
- Create: `common/static_modifiers/resettlement_modifiers.txt`
- Create: `common/on_actions/resettlement_on_actions.txt`
- Create: `events/resettlement_events.txt` (with `resettlement.9` only; Tasks 5 and 6 add the rest)
- Modify: `common/scripted_triggers/resettlement_triggers.txt`, `common/script_values/resettlement_values.txt` (append)
- Modify: `common/modifier_type_definitions/mod_entity_modifier_types.txt` (three readout types, after `state_resettlement_transfer_add`)
- Modify: `common/decrees/extra_decrees.txt` (append the drive)
- Modify: `common/scripted_effects/extra_effects.txt` (delete the `# Resettlement Population Transfer` header comment and `resettlement_transfer_effect`, about lines 1086–1135)
- Modify: `common/on_actions/extra_on_actions.txt` (delete `resettlement_transfer_on_action` from `on_monthly_pulse_state`'s list at about line 319, and its definition with its comment header at about lines 2598–2613)
- Modify: loc in `te_buildings`, `te_modifiers`, `te_miscellaneous`, `te_decrees` and `te_events`
- Modify: `test_resettlement_programme_registry.py` (add `TransferTests`)

**Interfaces:**
- Consumes: `PROGRAMMES` codes and PM keys (Task 3), frontier triggers (Task 2).
- Produces (effects): `resettlement_country_monthly` (country), `resettlement_run_destination` (state), `resettlement_take_from_source = { CAP = <sv> }` (state), `resettlement_source_consequences` (state), `resettlement_touch_pressed_cultures = { EFFECT = <effect> VALUE = <sv> }` (state), `resettlement_end_coercive_programmes` (country), `resettlement_close_frontier` (state), `resettlement_refresh_destination_readout`, `resettlement_refresh_source_readout`, `resettlement_reset_month_counters`, `resettlement_count_programme_month`.
- Produces (triggers): `resettlement_runs_pm = { PM = <pm> }` (state), `resettlement_state_runs_coercive`, `resettlement_state_runs_voluntary`, `resettlement_pop_eligible` (pop), `resettlement_pop_urban_worker` (pop), `resettlement_state_is_damaged`, `resettlement_valid_source`.
- Produces (variables): see the header of `resettlement_effects.txt` below. Country `rs_month_<key>` holds this month's recruits (arrived + died) per programme; Task 5 reads it.
- Produces (saved scopes): `rs_country`, `rs_destination`, `rs_source`, `rs_closed_state`, `rs_pressed_culture`, `rs_touch_state`.

- [ ] **Step 1: Write the failing tests**

Add to `test_resettlement_programme_registry.py`, after `BuildingTests`:

```python
EFFECTS = "common/scripted_effects/resettlement_effects.txt"
RS_MODIFIERS = "common/static_modifiers/resettlement_modifiers.txt"
RS_ON_ACTIONS = "common/on_actions/resettlement_on_actions.txt"
RS_EVENTS = "events/resettlement_events.txt"
DECREES = "common/decrees/extra_decrees.txt"
VOLUNTARY = ("land_grants", "military_colonies", "organized_colonization", "development_program")

# (static modifier, modifier type, scope it sits on)
READOUTS = (
    ("resettlement_arrivals", "building_resettlement_arrivals_add", "building"),
    ("resettlement_transit_deaths", "building_resettlement_transit_deaths_add", "building"),
    ("resettlement_recruits", "state_resettlement_recruits_add", "state"),
)


class TransferTests(unittest.TestCase):
    def test_eligibility_has_one_branch_per_code(self):
        body = block(read(TRIGGERS), "resettlement_pop_eligible")
        codes = {int(c) for c in re.findall(r"scope:rs_destination\.var:rs_programme = (\d+)", body)}
        self.assertEqual(codes, {p.code for p in PROGRAMMES})

    def test_eligibility_never_selects_culture_or_religion(self):
        text = read(TRIGGERS)
        for name in ("resettlement_pop_eligible", "resettlement_pop_volunteer", "resettlement_pop_colonist",
                     "resettlement_pop_urban_worker", "resettlement_state_is_damaged"):
            body = block(text, name)
            self.assertIsNotNone(body, name)
            self.assertNotRegex(body, r"\b(culture|religion)\b", name)

    def test_slaves_are_never_eligible(self):
        self.assertIn("NOT = { is_pop_type = slaves }", squash(block(read(TRIGGERS), "resettlement_pop_eligible")))

    def test_code_switch_matches_the_table(self):
        body = squash(block(read(EFFECTS), "resettlement_set_programme_code"))
        found = {m.group(1): (int(m.group(2)), float(m.group(3))) for m in re.finditer(
            r"resettlement_runs_pm = \{ PM = pm_resettlement_(\w+) \} \} "
            r"set_variable = \{ name = rs_programme value = (\d+) \} "
            r"set_variable = \{ name = rs_mortality value = ([\d.]+) \}", body)}
        self.assertEqual(found, {p.key: (p.code, float(p.mortality)) for p in PROGRAMMES})

    def test_coercive_and_voluntary_triggers_partition_the_table(self):
        text = read(TRIGGERS)
        def pms(name):
            return set(re.findall(r"PM = pm_resettlement_(\w+)", block(text, name)))
        self.assertEqual(pms("resettlement_state_runs_coercive"), {p.key for p in COERCIVE})
        self.assertEqual(pms("resettlement_state_runs_voluntary"), set(VOLUNTARY))
        self.assertEqual(set(VOLUNTARY) | {p.key for p in COERCIVE} | {"managed_retreat"}, set(PROGRAMME_KEYS))

    def test_month_counters_cover_every_programme(self):
        text = read(EFFECTS)
        reset = squash(block(text, "resettlement_reset_month_counters"))
        count = squash(block(text, "resettlement_count_programme_month"))
        for p in PROGRAMMES:
            self.assertIn(f"set_variable = {{ name = rs_month_{p.key} value = 0 }}", reset, p.key)
            self.assertIn(f"resettlement_count_one = {{ CODE = {p.code} PROG = {p.key} }}", count, p.key)

    def test_caps_and_minimum(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_pop_cap = 0\.02\s*$")
        self.assertRegex(text, r"(?m)^resettlement_drive_pop_cap = 0\.04\s*$")
        self.assertRegex(text, r"(?m)^resettlement_min_take = 100\s*$")

    def test_walk_takes_drive_states_first(self):
        body = squash(block(read(EFFECTS), "resettlement_run_destination"))
        drive = body.index("has_decree = decree_resettlement_recruitment_drive")
        rest = body.index("NOT = { has_decree = decree_resettlement_recruitment_drive }")
        self.assertLess(drive, rest)
        self.assertIn("CAP = resettlement_drive_pop_cap", body[drive:rest])
        self.assertIn("CAP = resettlement_pop_cap", body[rest:])

    def test_capacity_is_the_modifier_and_never_negative(self):
        body = squash(block(read(EFFECTS), "resettlement_run_destination"))
        self.assertIn("set_variable = { name = rs_remaining value = modifier:state_resettlement_transfer_add }", body)
        self.assertIn("limit = { var:rs_remaining < 0 } set_variable = { name = rs_remaining value = 0 }", body)
        # Review Focus 5: the program code is re-read from the active PM every month.
        self.assertIn("resettlement_set_programme_code = yes", body)

    def test_every_take_is_guarded(self):
        body = squash(block(read(EFFECTS), "resettlement_take_from_source"))
        self.assertIn("scope:rs_destination.var:rs_remaining >= resettlement_min_take", body)
        self.assertIn("local_var:rs_take >= resettlement_min_take", body)
        self.assertIn("move_partial_pop = { state = scope:rs_destination population = { value = local_var:rs_move } }", body)

    def test_deaths_in_steps_of_one_hundred_for_each_coercive_programme(self):
        body = squash(block(read(EFFECTS), "resettlement_source_consequences"))
        kills = re.findall(r"while = \{ count = local_var:rs_dead_steps kill_population_in_state = \{ value = 100 (\w+ = \w+) \} \}", body)
        self.assertEqual(sorted(kills), ["pop_type = farmers", "pop_type = laborers", "strata = lower"])
        for p in COERCIVE:
            self.assertIn(f"scope:rs_destination.var:rs_programme = {p.code}", body, p.key)

    def test_land_pressure_is_only_a_cost(self):
        body = squash(block(read(EFFECTS), "resettlement_land_pressure"))
        self.assertIn("EFFECT = add_radicals_in_state VALUE = resettlement_land_pressure_share", body)
        self.assertNotIn("loyalists", body)
        touch = squash(block(read(EFFECTS), "resettlement_touch_pressed_cultures"))
        self.assertIn("pop_acceptance < acceptance_status_4", touch)
        self.assertIn("is_target_in_variable_list", touch)

    def test_readouts(self):
        mods = read(RS_MODIFIERS)
        types = read(MODIFIER_TYPES)
        L = loc()
        for modifier, mtype, _ in READOUTS:
            self.assertEqual(number(block(mods, modifier), mtype), 1, modifier)
            tbody = block(types, mtype)
            self.assertIsNotNone(tbody, mtype)
            self.assertEqual(number(tbody, "decimals"), 0, mtype)
            for key in (modifier, f"{modifier}_desc", mtype, f"{mtype}_desc"):
                self.assertIn(key, L)
        effects = read(EFFECTS)
        dest = squash(block(effects, "resettlement_refresh_destination_readout"))
        self.assertIn("add_modifier = { name = resettlement_arrivals multiplier = var:rs_arrivals }", dest)
        self.assertIn("add_modifier = { name = resettlement_transit_deaths multiplier = var:rs_deaths }", dest)
        src = squash(block(effects, "resettlement_refresh_source_readout"))
        self.assertIn("add_modifier = { name = resettlement_recruits multiplier = var:rs_recruits }", src)

    def test_the_pulse_is_wired(self):
        text = read(RS_ON_ACTIONS)
        m = re.search(r"on_monthly_pulse_country\s*=\s*\{\s*on_actions\s*=\s*\{([^}]*)\}", text)
        self.assertIsNotNone(m)
        self.assertIn("resettlement_country_on_action", m.group(1))
        self.assertIn("resettlement_country_monthly = yes", squash(block(text, "resettlement_country_on_action")))

    def test_closure_removes_the_building_and_tells_the_owner(self):
        body = squash(block(read(EFFECTS), "resettlement_close_frontier"))
        self.assertIn("remove_building = building_resettlement_colony", body)
        self.assertIn("trigger_event = { id = resettlement.9 }", body)
        self.assertIsNotNone(block(read(RS_EVENTS), "resettlement.9"))
        monthly = squash(block(read(EFFECTS), "resettlement_country_monthly"))
        self.assertIn("limit = { resettlement_state_frontier_still_open = no } resettlement_close_frontier = yes", monthly)

    def test_the_drive_decree(self):
        body = block(read(DECREES), "decree_resettlement_recruitment_drive")
        self.assertIsNotNone(body)
        self.assertIn("has_building = building_resettlement_colony", squash(block(body, "country_trigger")))
        for key in ("decree_resettlement_recruitment_drive", "decree_resettlement_recruitment_drive_desc",
                    "decree_resettlement_recruitment_drive_needs_authority_tt"):
            self.assertIn(key, loc())
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `python3 -m unittest test_resettlement_programme_registry.TransferTests test_resettlement_programme_registry.OldSystemGoneTests -v`
Expected: ERROR/FAIL (`resettlement_effects.txt` missing; the old transfer still present).

- [ ] **Step 3: Append the triggers**

Append to `common/scripted_triggers/resettlement_triggers.txt`:

```

# ---- Which program a destination runs (§3) ----------------------------------
# State scope. This state's Settlement Authority has $PM$ active (any group).
resettlement_runs_pm = {
	any_scope_building = {
		is_building_type = building_resettlement_colony
		has_active_production_method = $PM$
	}
}

# State scope. Penal Transportation, Special Settlements or Rustication.
resettlement_state_runs_coercive = {
	OR = {
		resettlement_runs_pm = { PM = pm_resettlement_penal_transportation }
		resettlement_runs_pm = { PM = pm_resettlement_special_settlements }
		resettlement_runs_pm = { PM = pm_resettlement_rustication }
	}
}

# State scope. Land Grants, Military Colonies, Organized Colonization or the
# Development Program. (Managed Retreat is neither: nobody chooses the flood.)
resettlement_state_runs_voluntary = {
	OR = {
		resettlement_runs_pm = { PM = pm_resettlement_land_grants }
		resettlement_runs_pm = { PM = pm_resettlement_military_colonies }
		resettlement_runs_pm = { PM = pm_resettlement_organized_colonization }
		resettlement_runs_pm = { PM = pm_resettlement_development_program }
	}
}

# ---- Who may be recruited (§3) ----------------------------------------------
# Pop scope, with scope:rs_country (the owner) and scope:rs_destination (the
# state whose var:rs_programme holds the program's code) saved. Culture and
# religion are never tested. Slaves never: move_partial_pop would free them.
resettlement_pop_eligible = {
	NOT = { is_pop_type = slaves }
	OR = {
		AND = {
			scope:rs_destination.var:rs_programme = 0
			resettlement_pop_volunteer = yes
			pop_acceptance >= acceptance_status_4
		}
		AND = {
			scope:rs_destination.var:rs_programme = 1
			resettlement_pop_volunteer = yes
			pop_acceptance >= acceptance_status_5
		}
		AND = {
			scope:rs_destination.var:rs_programme = 2
			strata = lower
			pop_radical_fraction >= 0.2
		}
		AND = {
			scope:rs_destination.var:rs_programme = 3
			resettlement_pop_colonist = yes
			pop_acceptance >= acceptance_status_4
		}
		AND = {
			scope:rs_destination.var:rs_programme = 4
			is_pop_type = farmers
		}
		AND = {
			scope:rs_destination.var:rs_programme = 5
			pop_acceptance >= acceptance_status_4
			OR = {
				resettlement_pop_colonist = yes
				is_pop_type = machinists
				is_pop_type = engineers
				is_pop_type = clerks
			}
		}
		AND = {
			scope:rs_destination.var:rs_programme = 6
			resettlement_pop_urban_worker = yes
		}
		AND = {
			scope:rs_destination.var:rs_programme = 7
			state = { resettlement_state_is_damaged = yes }
		}
	}
}

# Pop scope, scope:rs_country saved. The unemployed and peasants of the lower
# strata. Serfs cannot leave the land (vanilla forbids peasant migration under
# Serfdom).
resettlement_pop_volunteer = {
	strata = lower
	OR = {
		is_employed = no
		AND = {
			is_pop_type = peasants
			scope:rs_country = { NOT = { has_law = law_type:law_serfdom } }
		}
	}
}

# Pop scope, scope:rs_country saved. Volunteers plus laborers.
resettlement_pop_colonist = {
	strata = lower
	OR = {
		is_employed = no
		is_pop_type = laborers
		AND = {
			is_pop_type = peasants
			scope:rs_country = { NOT = { has_law = law_type:law_serfdom } }
		}
	}
}

# Pop scope. Laborers and clerks who do not work the land.
resettlement_pop_urban_worker = {
	OR = {
		is_pop_type = laborers
		is_pop_type = clerks
	}
	NOR = {
		pop_employment_building_group = bg_agriculture
		pop_employment_building_group = bg_plantations
		pop_employment_building_group = bg_ranching
		pop_employment_building_group = bg_subsistence_agriculture
		pop_employment_building_group = bg_subsistence_ranching
	}
}

# State scope. Damage Managed Retreat moves people away from. Global-warming
# flooding is a country modifier, so it is read through the owner and the
# coast; the nuclear markers sit on the state.
resettlement_state_is_damaged = {
	OR = {
		has_modifier = nuclear_strike_aftermath
		has_modifier = nd_weapons_accident_contamination
		AND = {
			is_coastal = yes
			owner = {
				OR = {
					has_modifier = coastal_flooding_modifier
					has_modifier = coastal_relocation_modifier
				}
			}
		}
	}
}

# State scope, scope:rs_destination saved. A state the walk may take from.
resettlement_valid_source = {
	NOT = { this = scope:rs_destination }
	NOT = { has_building = building_resettlement_colony }
	resettlement_state_eligible_pop >= resettlement_min_take
}
```

- [ ] **Step 4: Append the script values**

Append to `common/script_values/resettlement_values.txt`:

```

# ---- The walk (§2) ---------------------------------------------------------
# The share of each eligible pop a source may give a month (vanilla's
# emigration ceiling is 0.5% a week), and in a Recruitment Drive state.
resettlement_pop_cap = 0.02
resettlement_drive_pop_cap = 0.04
# Takes under this many people are skipped, so the walk does not splinter the
# destination into tiny pops.
resettlement_min_take = 100

# State scope, with scope:rs_country and scope:rs_destination saved. People
# here the destination's program may recruit.
resettlement_state_eligible_pop = {
	value = 0
	every_scope_pop = {
		limit = { resettlement_pop_eligible = yes }
		add = total_size
	}
}

# ---- Consequences at the source (§7.1) -------------------------------------
# Source state, after var:rs_taken_now is set. 10 × the share of the recruited
# type taken this month, capped at 0.1.
resettlement_state_farmers = {
	value = 0
	every_scope_pop = {
		limit = { is_pop_type = farmers }
		add = total_size
	}
}

resettlement_farmer_unrest_share = {
	value = var:rs_taken_now
	multiply = 10
	divide = {
		value = resettlement_state_farmers
		min = 1
	}
	max = 0.1
}

resettlement_state_urban_workers = {
	value = 0
	every_scope_pop = {
		limit = { resettlement_pop_urban_worker = yes }
		add = total_size
	}
}

resettlement_urban_unrest_share = {
	value = var:rs_taken_now
	multiply = 10
	divide = {
		value = resettlement_state_urban_workers
		min = 1
	}
	max = 0.1
}

# ---- Land pressure at the destination (§7.3) -------------------------------
# Destination state after the walk. 5 × this month's arrivals ÷ its
# population, capped at 0.05.
resettlement_land_pressure_share = {
	value = var:rs_arrived
	multiply = 5
	divide = {
		value = state_population
		min = 1
	}
	max = 0.05
}
```

- [ ] **Step 5: Write the effects**

Create `common/scripted_effects/resettlement_effects.txt` (BOM, tabs):

```
# ============================================================================
# INTERNAL RESETTLEMENT — the monthly pulse
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md §2.
#
# One country pulse does everything, in this order, so several destinations can
# share a source within a month and every readout has exactly one refresh site:
#   1. zero every state's monthly recruit counter and the country's
#      per-program month counters;
#   2. an AI kept to voluntary programs is switched off coercive ones;
#   3. each Settlement Authority closes (frontier full) or runs the walk;
#   4. refresh the source readouts;
#   5. the political layer and the Declaration;
#   6. roll events.
#
# Variables
#   destination state   rs_programme (the code in the registry's PROGRAMMES),
#                       rs_mortality, rs_remaining, rs_arrived, rs_died,
#                       rs_months_running, rs_last_source (a state)
#   Authority building  rs_arrivals, rs_deaths (readout multipliers; persist,
#                       so the modifiers' multipliers never read 'none')
#   source state        rs_recruits (this month, every destination),
#                       rs_taken_now (this destination's take, for unrest)
#   country             rs_month_<program> (this month's recruits)
# ============================================================================

resettlement_country_monthly = {
	save_scope_as = rs_country
	every_scope_state = {
		limit = { has_variable = rs_recruits }
		set_variable = { name = rs_recruits value = 0 }
	}
	resettlement_reset_month_counters = yes
	if = {
		limit = { resettlement_system_enabled = yes }
		if = {
			limit = { resettlement_ai_voluntary_only = yes }
			resettlement_end_coercive_programmes = yes
		}
		every_scope_state = {
			limit = { has_building = building_resettlement_colony }
			if = {
				limit = { resettlement_state_frontier_still_open = no }
				resettlement_close_frontier = yes
			}
			else = {
				resettlement_run_destination = yes
			}
		}
	}
	every_scope_state = {
		limit = { has_variable = rs_recruits }
		resettlement_refresh_source_readout = yes
	}
}

resettlement_reset_month_counters = {
	set_variable = { name = rs_month_land_grants value = 0 }
	set_variable = { name = rs_month_military_colonies value = 0 }
	set_variable = { name = rs_month_penal_transportation value = 0 }
	set_variable = { name = rs_month_organized_colonization value = 0 }
	set_variable = { name = rs_month_special_settlements value = 0 }
	set_variable = { name = rs_month_development_program value = 0 }
	set_variable = { name = rs_month_rustication value = 0 }
	set_variable = { name = rs_month_managed_retreat value = 0 }
}

# State scope: a destination. Read every month from the active PM, never
# cached, so a law that retires the running program takes effect at once.
resettlement_set_programme_code = {
	if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_land_grants } }
		set_variable = { name = rs_programme value = 0 }
		set_variable = { name = rs_mortality value = 0 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_military_colonies } }
		set_variable = { name = rs_programme value = 1 }
		set_variable = { name = rs_mortality value = 0 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_penal_transportation } }
		set_variable = { name = rs_programme value = 2 }
		set_variable = { name = rs_mortality value = 0.05 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_organized_colonization } }
		set_variable = { name = rs_programme value = 3 }
		set_variable = { name = rs_mortality value = 0 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_special_settlements } }
		set_variable = { name = rs_programme value = 4 }
		set_variable = { name = rs_mortality value = 0.15 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_development_program } }
		set_variable = { name = rs_programme value = 5 }
		set_variable = { name = rs_mortality value = 0 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_rustication } }
		set_variable = { name = rs_programme value = 6 }
		set_variable = { name = rs_mortality value = 0.01 }
	}
	else_if = {
		limit = { resettlement_runs_pm = { PM = pm_resettlement_managed_retreat } }
		set_variable = { name = rs_programme value = 7 }
		set_variable = { name = rs_mortality value = 0 }
	}
}

# State scope: a destination with a Settlement Authority. scope:rs_country saved.
resettlement_run_destination = {
	save_scope_as = rs_destination
	resettlement_set_programme_code = yes
	set_variable = { name = rs_arrived value = 0 }
	set_variable = { name = rs_died value = 0 }
	set_variable = { name = rs_remaining value = modifier:state_resettlement_transfer_add }
	if = {
		limit = { var:rs_remaining < 0 }
		set_variable = { name = rs_remaining value = 0 }
	}
	if = {
		limit = { NOT = { has_variable = rs_months_running } }
		set_variable = { name = rs_months_running value = 0 }
	}
	change_variable = { name = rs_months_running add = 1 }

	# Drive states first, then everyone else, each walked in order of eligible
	# population until the capacity is used (§2).
	scope:rs_country = {
		ordered_scope_state = {
			limit = {
				has_decree = decree_resettlement_recruitment_drive
				resettlement_valid_source = yes
			}
			order_by = resettlement_state_eligible_pop
			min = 0
			max = 199
			check_range_bounds = no
			resettlement_take_from_source = { CAP = resettlement_drive_pop_cap }
		}
		ordered_scope_state = {
			limit = {
				NOT = { has_decree = decree_resettlement_recruitment_drive }
				resettlement_valid_source = yes
			}
			order_by = resettlement_state_eligible_pop
			min = 0
			max = 199
			check_range_bounds = no
			resettlement_take_from_source = { CAP = resettlement_pop_cap }
		}
	}

	resettlement_count_programme_month = yes
	resettlement_land_pressure = yes
	resettlement_refresh_destination_readout = yes
	debug_log = "TE_RESETTLEMENT: [THIS.GetState.GetName] program [THIS.GetState.MakeScope.Var('rs_programme').GetValue|0]: [THIS.GetState.MakeScope.Var('rs_arrived').GetValue|0] arrived, [THIS.GetState.MakeScope.Var('rs_died').GetValue|0] died in transit, [THIS.GetState.MakeScope.Var('rs_remaining').GetValue|0] of capacity unused"
}

# State scope: a source. scope:rs_country and scope:rs_destination saved.
# $CAP$: the script value naming the share of each eligible pop it may give.
resettlement_take_from_source = {
	save_scope_as = rs_source
	set_variable = { name = rs_taken_now value = 0 }
	every_scope_pop = {
		limit = { resettlement_pop_eligible = yes }
		if = {
			limit = { scope:rs_destination.var:rs_remaining >= resettlement_min_take }
			set_local_variable = {
				name = rs_take
				value = {
					value = total_size
					multiply = $CAP$
				}
			}
			if = {
				limit = { local_var:rs_take > scope:rs_destination.var:rs_remaining }
				set_local_variable = { name = rs_take value = scope:rs_destination.var:rs_remaining }
			}
			if = {
				limit = { local_var:rs_take >= resettlement_min_take }
				# The dead are removed at the source afterwards
				# (resettlement_source_consequences); the rest move now.
				set_local_variable = {
					name = rs_move
					value = {
						value = 1
						subtract = scope:rs_destination.var:rs_mortality
						multiply = local_var:rs_take
						round = yes
					}
				}
				move_partial_pop = {
					state = scope:rs_destination
					population = { value = local_var:rs_move }
				}
				scope:rs_destination = {
					change_variable = { name = rs_remaining subtract = local_var:rs_take }
					change_variable = { name = rs_arrived add = local_var:rs_move }
				}
				scope:rs_source = {
					change_variable = { name = rs_taken_now add = local_var:rs_take }
				}
			}
		}
	}
	if = {
		limit = { var:rs_taken_now > 0 }
		if = {
			limit = { NOT = { has_variable = rs_recruits } }
			set_variable = { name = rs_recruits value = 0 }
		}
		change_variable = { name = rs_recruits add = var:rs_taken_now }
		scope:rs_destination = {
			set_variable = { name = rs_last_source value = scope:rs_source }
		}
		resettlement_source_consequences = yes
	}
}

# State scope: a source, after var:rs_taken_now is set. scope:rs_destination saved.
# Deaths in transit (§2): kill_population_in_state takes a constant, so the dead
# are removed in steps of 100, filtered to the program's recruits. Unrest
# (§7.1) radicalizes the recruited type left behind. add_radicals_in_state
# cannot tell urban laborers from farm laborers, so Rustication's unrest
# reaches both; its share is computed against urban workers only.
resettlement_source_consequences = {
	set_local_variable = {
		name = rs_dead_steps
		value = {
			value = var:rs_taken_now
			multiply = scope:rs_destination.var:rs_mortality
			divide = 100
			round = yes
		}
	}
	set_local_variable = {
		name = rs_dead_people
		value = {
			value = local_var:rs_dead_steps
			multiply = 100
		}
	}
	scope:rs_destination = {
		change_variable = { name = rs_died add = local_var:rs_dead_people }
	}
	if = {
		limit = { scope:rs_destination.var:rs_programme = 4 }
		while = {
			count = local_var:rs_dead_steps
			kill_population_in_state = { value = 100 pop_type = farmers }
		}
		add_radicals_in_state = { value = resettlement_farmer_unrest_share pop_type = farmers }
	}
	else_if = {
		limit = { scope:rs_destination.var:rs_programme = 6 }
		while = {
			count = local_var:rs_dead_steps
			kill_population_in_state = { value = 100 pop_type = laborers }
		}
		add_radicals_in_state = { value = resettlement_urban_unrest_share pop_type = laborers }
		add_radicals_in_state = { value = resettlement_urban_unrest_share pop_type = clerks }
	}
	else_if = {
		limit = { scope:rs_destination.var:rs_programme = 2 }
		while = {
			count = local_var:rs_dead_steps
			kill_population_in_state = { value = 100 strata = lower }
		}
	}
}

# State scope: a destination, after the walk. Adds this month's recruits
# (arrived + died) to the owner's counter for the running program.
resettlement_count_programme_month = {
	set_local_variable = {
		name = rs_recruited
		value = {
			value = var:rs_arrived
			add = var:rs_died
		}
	}
	resettlement_count_one = { CODE = 0 PROG = land_grants }
	resettlement_count_one = { CODE = 1 PROG = military_colonies }
	resettlement_count_one = { CODE = 2 PROG = penal_transportation }
	resettlement_count_one = { CODE = 3 PROG = organized_colonization }
	resettlement_count_one = { CODE = 4 PROG = special_settlements }
	resettlement_count_one = { CODE = 5 PROG = development_program }
	resettlement_count_one = { CODE = 6 PROG = rustication }
	resettlement_count_one = { CODE = 7 PROG = managed_retreat }
}

resettlement_count_one = {
	if = {
		limit = { var:rs_programme = $CODE$ }
		scope:rs_country = {
			change_variable = { name = rs_month_$PROG$ add = local_var:rs_recruited }
		}
	}
}

# State scope: a destination, after the walk. Land pressure (§7.3): only ever a
# cost, never a benefit.
resettlement_land_pressure = {
	if = {
		limit = { var:rs_arrived > 0 }
		resettlement_touch_pressed_cultures = { EFFECT = add_radicals_in_state VALUE = resettlement_land_pressure_share }
	}
}

# State scope. Applies $EFFECT$ (add_radicals_in_state or add_loyalists_in_state)
# at $VALUE$, once for each culture here that has pops below second-class
# acceptance. The land-pressure consequence and event resettlement.8 use it;
# it never decides who moves.
resettlement_touch_pressed_cultures = {
	save_scope_as = rs_touch_state
	every_scope_pop = {
		limit = { pop_acceptance < acceptance_status_4 }
		culture = { save_scope_as = rs_pressed_culture }
		scope:rs_touch_state = {
			if = {
				limit = {
					NOT = {
						is_target_in_variable_list = { name = rs_pressed_cultures target = scope:rs_pressed_culture }
					}
				}
				add_to_variable_list = { name = rs_pressed_cultures target = scope:rs_pressed_culture }
				$EFFECT$ = { value = $VALUE$ culture = scope:rs_pressed_culture }
			}
		}
	}
	clear_variable_list = rs_pressed_cultures
}

# State scope: a destination. One refresh site for the building's readouts.
resettlement_refresh_destination_readout = {
	every_scope_building = {
		limit = { is_building_type = building_resettlement_colony }
		set_variable = { name = rs_arrivals value = scope:rs_destination.var:rs_arrived }
		set_variable = { name = rs_deaths value = scope:rs_destination.var:rs_died }
		remove_modifier = resettlement_arrivals
		remove_modifier = resettlement_transit_deaths
		if = {
			limit = { var:rs_arrivals > 0 }
			add_modifier = { name = resettlement_arrivals multiplier = var:rs_arrivals }
		}
		if = {
			limit = { var:rs_deaths > 0 }
			add_modifier = { name = resettlement_transit_deaths multiplier = var:rs_deaths }
		}
	}
}

# State scope: any state that has ever given settlers. One refresh site.
resettlement_refresh_source_readout = {
	remove_modifier = resettlement_recruits
	if = {
		limit = { var:rs_recruits > 0 }
		add_modifier = { name = resettlement_recruits multiplier = var:rs_recruits }
	}
}

# State scope: a destination whose frontier has filled. scope:rs_country saved.
resettlement_close_frontier = {
	save_scope_as = rs_closed_state
	remove_building = building_resettlement_colony
	remove_variable = rs_months_running
	scope:rs_country = {
		trigger_event = { id = resettlement.9 }
	}
	debug_log = "TE_RESETTLEMENT: the frontier at [THIS.GetState.GetName] is closed"
}

# Country scope. Every coercive program switches to the best voluntary one
# available: Organized Colonization once railways are known, else Land Grants.
resettlement_end_coercive_programmes = {
	every_scope_state = {
		limit = { resettlement_state_runs_coercive = yes }
		if = {
			limit = { owner = { has_technology_researched = railways } }
			activate_production_method = {
				building_type = building_resettlement_colony
				production_method = pm_resettlement_organized_colonization
			}
		}
		else = {
			activate_production_method = {
				building_type = building_resettlement_colony
				production_method = pm_resettlement_land_grants
			}
		}
	}
}
```

- [ ] **Step 6: Readout modifiers, types and loc**

Create `common/static_modifiers/resettlement_modifiers.txt` (BOM, tabs):

```
# ============================================================================
# INTERNAL RESETTLEMENT — static modifiers
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md.

# ---- Readouts (§2): re-applied monthly with the month's count as multiplier ----
resettlement_arrivals = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	building_resettlement_arrivals_add = 1
}

resettlement_transit_deaths = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	building_resettlement_transit_deaths_add = 1
}

resettlement_recruits = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_resettlement_recruits_add = 1
}
```

In `common/modifier_type_definitions/mod_entity_modifier_types.txt`, after the `state_resettlement_transfer_add` block, add:

```
# Internal resettlement readouts: display-only, re-applied monthly by
# resettlement_effects.txt with the month's count as multiplier.
building_resettlement_arrivals_add = {
	color = neutral
	percent = no
	decimals = 0
	game_data = {
		ai_value = 0
	}
}

building_resettlement_transit_deaths_add = {
	color = bad
	percent = no
	decimals = 0
	game_data = {
		ai_value = 0
	}
}

state_resettlement_recruits_add = {
	color = neutral
	percent = no
	decimals = 0
	game_data = {
		ai_value = 0
	}
}
```

Also add `decimals = 0` to the existing `state_resettlement_transfer_add` block.

Loc:
- `te_buildings_l_english.yml`:
  ```yaml
   building_resettlement_arrivals_add:0 "Settlers arrived last month"
   building_resettlement_arrivals_add_desc:0 "People this Settlement Authority brought here last month."
   building_resettlement_transit_deaths_add:0 "Died in transit last month"
   building_resettlement_transit_deaths_add_desc:0 "People recruited for this Settlement Authority last month who died before they arrived."
  ```
- `te_modifiers_l_english.yml`:
  ```yaml
   state_resettlement_recruits_add:0 "Recruited for resettlement last month"
   state_resettlement_recruits_add_desc:0 "People Settlement Authorities took from this state last month."
  ```
- `te_miscellaneous_l_english.yml`:
  ```yaml
   resettlement_arrivals:0 "Settlement Authority: Arrivals"
   resettlement_arrivals_desc:0 "The settlers this Settlement Authority brought here last month."
   resettlement_transit_deaths:0 "Settlement Authority: Deaths in Transit"
   resettlement_transit_deaths_desc:0 "Those taken for this program last month who died on the way here."
   resettlement_recruits:0 "Resettlement Recruitment"
   resettlement_recruits_desc:0 "Settlement Authorities took people from this state last month. Under Special Settlements the farmers left behind turn radical, and under Rustication the urban workers do. Under Penal Transportation, Special Settlements and Rustication, some of those taken die on the way."
  ```

- [ ] **Step 7: The Recruitment Drive decree**

Append to `common/decrees/extra_decrees.txt`:

```

# Internal resettlement (docs/superpowers/specs/2026-09-26-internal-resettlement-design.md
# §2): every Settlement Authority walks the states under this decree first, and
# may take up to 4% of each eligible pop a month here instead of 2%. It changes
# where settlers come from, never who is eligible. Valid only while the owner
# runs a Settlement Authority, so it is never bought for nothing.
decree_resettlement_recruitment_drive = {
	texture = "gfx/interface/icons/decree/decree_promote_social_mobility.dds"
	modifier = {
		state_migration_pull_mult = -0.1
	}

	cost = 100

	country_trigger = {
		custom_tooltip = {
			text = decree_resettlement_recruitment_drive_needs_authority_tt
			any_scope_state = { has_building = building_resettlement_colony }
		}
	}

	state_trigger = {
		NOT = { has_building = building_resettlement_colony }
	}

	ai_weight = {
		value = 0
		if = {
			limit = {
				scope:country = {
					any_scope_state = { has_building = building_resettlement_colony }
				}
				OR = {
					state_unemployment_rate > 0.1
					migration_crowding_mult > 1
				}
			}
			add = 50
		}
	}
}
```

`te_decrees_l_english.yml`:

```yaml
 decree_resettlement_recruitment_drive:0 "Resettlement Recruitment Drive"
 decree_resettlement_recruitment_drive_desc:0 "Recruiters for our Settlement Authorities concentrate here. Every Settlement Authority recruits from this state before any other, and may take twice as many of its eligible people each month."
 decree_resettlement_recruitment_drive_needs_authority_tt:0 "We run at least one Settlement Authority"
```

- [ ] **Step 8: Hook the pulse, and the closure event**

Create `common/on_actions/resettlement_on_actions.txt` (BOM, tabs):

```
# Internal resettlement: the monthly country pulse (resettlement_effects.txt).
# Runs only for a country with a Settlement Authority, or with readouts left to
# clear on states that gave settlers.
on_monthly_pulse_country = {
	on_actions = {
		resettlement_country_on_action
	}
}

resettlement_country_on_action = {
	effect = {
		if = {
			limit = {
				OR = {
					any_scope_state = { has_building = building_resettlement_colony }
					any_scope_state = { has_variable = rs_recruits }
				}
			}
			resettlement_country_monthly = yes
		}
	}
}
```

Create `events/resettlement_events.txt` (BOM, tabs):

```
namespace = resettlement

# ============================================================================
# INTERNAL RESETTLEMENT EVENTS
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-internal-resettlement-design.md §8.
# The logic is in common/scripted_effects/resettlement_effects.txt.
#
#   .1–.8  program events, rolled by resettlement_roll_events
#   .9     The Frontier Is Closed (resettlement_close_frontier)
#   .20    The Declaration and Our Settlements (resettlement_refresh_declaration)
# ============================================================================

# ---- .9 The Frontier Is Closed -------------------------------------------------
# Sent by resettlement_close_frontier with scope:rs_closed_state saved.
resettlement.9 = {
	type = country_event
	placement = scope:rs_closed_state

	event_image = {
		video = "unspecific_trains"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = resettlement.9.t
	desc = resettlement.9.d
	flavor = resettlement.9.f

	duration = 3

	trigger = {
		exists = scope:rs_closed_state
	}

	option = {
		name = resettlement.9.a
		default_option = yes
	}
}
```

`te_events_l_english.yml` (keep the file's alphabetical grouping):

```yaml
 resettlement.9.t:0 "The Frontier Is Closed"
 resettlement.9.d:0 "[SCOPE.sState('rs_closed_state').GetName] is a frontier no longer. Its farms and towns are as settled as the rest of the country, and the Settlement Authority there has been wound up. If we want more settlers, we will have to find another frontier."
 resettlement.9.f:0 "In 1890 the Superintendent of the Census reported that the United States no longer had a frontier line. Three years later Frederick Jackson Turner argued that its closing ended the first period of American history."
 resettlement.9.a:0 "A new chapter."
```

- [ ] **Step 9: Remove the old transfer**

- `common/scripted_effects/extra_effects.txt`: delete from the comment line `# Resettlement Population Transfer` (with the `# ===` rule above it) through the closing brace of `resettlement_transfer_effect`. Leave the `# Antimatter Facility Construction Effect` header that follows.
- `common/on_actions/extra_on_actions.txt`: delete the `resettlement_transfer_on_action` line from `on_monthly_pulse_state`'s `on_actions` list, and delete the `# ---- Resettlement Population Transfer (state scope, monthly) ----` comment block with the `resettlement_transfer_on_action = { … }` definition.

Verify: `git grep -n "resettlement_transfer_effect\|resettlement_transfer_on_action" -- common events docs/systems` prints only `docs/systems/mod_systems.md:1057`, which Task 8 updates.

- [ ] **Step 10: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry -v`
Expected: all classes pass, including `OldSystemGoneTests`.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_effects/resettlement_effects.txt common/static_modifiers/resettlement_modifiers.txt common/on_actions/resettlement_on_actions.txt events/resettlement_events.txt common/scripted_triggers/resettlement_triggers.txt common/script_values/resettlement_values.txt common/decrees/extra_decrees.txt common/modifier_type_definitions/mod_entity_modifier_types.txt common/scripted_effects/extra_effects.txt common/on_actions/extra_on_actions.txt && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.
Run the offline strict audits that read these files:
`for a in modifier_multiplier_var_audit prev_scope_audit iterator_limit_audit any_limit_audit event_image_audit orphaned_event_audit; do python3 $a.py --strict || echo "FAIL $a"; done`
Expected: no `FAIL` line. If `iterator_limit_audit` flags the `ordered_scope_state` `limit` blocks, read its report; its suppression goes on the `limit = {` line (`# REVIEWED 2026-09-26: ordered walk, limit filters the list`), and only if the flag is a false positive.

- [ ] **Step 11: Commit**

```bash
git add common/scripted_effects/resettlement_effects.txt common/static_modifiers/resettlement_modifiers.txt \
        common/on_actions/resettlement_on_actions.txt events/resettlement_events.txt \
        common/scripted_triggers/resettlement_triggers.txt common/script_values/resettlement_values.txt \
        common/modifier_type_definitions/mod_entity_modifier_types.txt common/decrees/extra_decrees.txt \
        common/scripted_effects/extra_effects.txt common/on_actions/extra_on_actions.txt \
        localization/english/te_buildings_l_english.yml localization/english/te_modifiers_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml localization/english/te_decrees_l_english.yml \
        localization/english/te_events_l_english.yml test_resettlement_programme_registry.py
git commit -m "feat(resettlement): the monthly transfer, readouts, closure and Recruitment Drive

One country pulse walks each Authority's sources in order of eligible
population (drive states first), moves exactly the displayed capacity with
move_partial_pop, removes deaths in transit in steps of 100, radicalizes
those left behind and those pressed at the frontier, and closes full
frontiers. Replaces resettlement_transfer_effect and its on_action.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 5: Political reactions and the UN Declaration

**Files:**
- Modify: `common/scripted_effects/resettlement_effects.txt` (append the politics and Declaration effects; call them from `resettlement_country_monthly`)
- Modify: `common/scripted_triggers/resettlement_triggers.txt` (append two country triggers)
- Modify: `common/script_values/resettlement_values.txt` (append two constants)
- Modify: `common/static_modifiers/resettlement_modifiers.txt` (six politics modifiers and the violation)
- Modify: `common/on_actions/resettlement_on_actions.txt` (keep pulsing while reactions fade)
- Modify: `events/resettlement_events.txt` (add `resettlement.20`)
- Modify: `test_un_convention_registry.py` (a `violation_modifiers` column)
- Modify: loc in `te_miscellaneous`, `te_concepts` and `te_events` (the Declaration's proposal, vote and modifier text)
- Modify: `test_resettlement_programme_registry.py` (add `PoliticsTests`, `DeclarationTests`)

**Interfaces:**
- Consumes: country `rs_month_<key>` (Task 4), `resettlement_end_coercive_programmes`, `resettlement_state_runs_coercive` (Task 4).
- Produces: country variables `rs_volume_<key>`, `rs_intensity_<key>` (for each programme with politics), `rs_declaration_intensity`, `rs_declaration_warned`, `rs_active`; modifiers `resettlement_<key>_politics` and `resettlement_declaration_violation`; triggers `resettlement_is_declaration_party` and `resettlement_country_still_fading`.

- [ ] **Step 1: Write the failing tests**

Add to `test_resettlement_programme_registry.py`:

```python
UN_REGISTRY = "test_un_convention_registry.py"


class PoliticsTests(unittest.TestCase):
    def test_constants(self):
        text = strip_comments(read(VALUES))
        self.assertRegex(text, r"(?m)^resettlement_volume_decay = 0\.9167\s*$")
        self.assertRegex(text, r"(?m)^resettlement_intensity_reference = 0\.0025\s*$")

    def test_each_politics_modifier_is_the_table(self):
        mods = read(RS_MODIFIERS)
        for p in PROGRAMMES:
            body = block(mods, f"resettlement_{p.key}_politics")
            if not p.politics:
                self.assertIsNone(body, p.key)
                continue
            found = {k: float(v) for k, v in re.findall(r"(interest_group_\w+_approval_add)\s*=\s*(-?[\d.]+)", body)}
            self.assertEqual(found, {k: float(v) for k, v in p.politics.items()}, p.key)
            self.assertIn(f"resettlement_{p.key}_politics", loc())
            self.assertIn(f"resettlement_{p.key}_politics_desc", loc())

    def test_positives_never_exceed_a_strong_law_stance(self):
        for p in WITH_POLITICS:
            for key, value in p.politics.items():
                self.assertLessEqual(value, 2, (p.key, key))
                self.assertGreaterEqual(value, -5, (p.key, key))

    def test_refresh_covers_every_programme_with_politics(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_politics"))
        called = re.findall(r"resettlement_refresh_programme_politics = \{ PROG = (\w+) \}", body)
        self.assertEqual(called, [p.key for p in WITH_POLITICS])

    def test_one_modifier_per_programme_scaled_by_intensity(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_programme_politics"))
        self.assertIn("change_variable = { name = rs_volume_$PROG$ multiply = resettlement_volume_decay }", body)
        self.assertIn("change_variable = { name = rs_volume_$PROG$ add = var:rs_month_$PROG$ }", body)
        self.assertIn("add_modifier = { name = resettlement_$PROG$_politics multiplier = var:rs_intensity_$PROG$ }", body)
        self.assertIn("max = 1", body)

    def test_the_pulse_keeps_running_while_reactions_fade(self):
        fading = squash(block(read(TRIGGERS), "resettlement_country_still_fading"))
        for p in WITH_POLITICS:
            self.assertIn(f"var:rs_volume_{p.key} > 1", fading, p.key)
        self.assertIn("has_variable = rs_active", squash(block(read(RS_ON_ACTIONS), "resettlement_country_on_action")))


class DeclarationTests(unittest.TestCase):
    def test_party_reads_the_conventions_member_and_reservations_modifiers(self):
        body = squash(block(read(TRIGGERS), "resettlement_is_declaration_party"))
        self.assertIn("je:je_united_nations ?= { has_modifier = un_human_rights_declaration_modifier }", body)
        self.assertIn("has_modifier = un_human_rights_reservations_modifier", body)

    def test_intensity_sums_the_coercive_programmes_and_halves_under_reservations(self):
        body = squash(block(read(EFFECTS), "resettlement_refresh_declaration"))
        summed = set(re.findall(r"var:rs_intensity_(\w+)", body))
        self.assertEqual(summed, {p.key for p in COERCIVE})
        self.assertIn("change_variable = { name = rs_declaration_intensity multiply = 0.5 }", body)
        self.assertIn("add_modifier = { name = resettlement_declaration_violation multiplier = var:rs_declaration_intensity }", body)
        self.assertIn("trigger_event = { id = resettlement.20 }", body)

    def test_the_violation_modifier(self):
        body = block(read(RS_MODIFIERS), "resettlement_declaration_violation")
        self.assertEqual(number(body, "country_prestige_mult"), -0.1)
        L = loc()
        self.assertIn("resettlement_declaration_violation", L)
        self.assertIn("resettlement_declaration_violation_desc", L)

    def test_communicated_at_every_step(self):
        L = loc()
        # 1. before choosing: TestProgramme.test_the_declaration_line_is_on_coercive_programmes_only
        # 2. when it starts: resettlement.20, whose second option ends the programmes
        event = block(read(RS_EVENTS), "resettlement.20")
        self.assertIsNotNone(event)
        options = re.findall(r"option\s*=\s*\{", strip_comments(event))
        self.assertEqual(len(options), 2)
        self.assertIn("resettlement_end_coercive_programmes = yes", squash(event))
        for suffix in ("t", "d", "f", "a", "b"):
            self.assertIn(f"resettlement.20.{suffix}", L)
        # 3. while it runs: the modifier's description (test_the_violation_modifier)
        # 4. at the vote: the proposal, the vote and the member modifier say so
        for key in ("un_events.3.d", "un_vote.1.d_human_rights", "un_human_rights_declaration_modifier_desc"):
            self.assertIn("resettlement", L[key].lower(), key)

    def test_the_un_registry_names_it(self):
        self.assertRegex(read(UN_REGISTRY), r'violation_modifiers=\("resettlement_declaration_violation",\)')
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `python3 -m unittest test_resettlement_programme_registry.PoliticsTests test_resettlement_programme_registry.DeclarationTests -v`
Expected: FAIL (constants, modifiers and effects missing).

- [ ] **Step 3: Constants and triggers**

Append to `common/script_values/resettlement_values.txt`:

```

# ---- The political layer (§7.2) -------------------------------------------
# The volume counter keeps 11/12 of last month's value, so at a steady rate it
# holds about a year's flow and fades over about a year once a program stops.
resettlement_volume_decay = 0.9167
# A program at full intensity moves this share of the country's population a
# year (Stolypin's resettlement at its peak).
resettlement_intensity_reference = 0.0025
```

Append to `common/scripted_triggers/resettlement_triggers.txt`:

```

# ---- The political layer and the Declaration (§7.2, §7.4) -------------------
# Country scope. Party to the Universal Declaration of Human Rights, in full or
# with reservations (read as un_human_rights_signatories does).
resettlement_is_declaration_party = {
	OR = {
		je:je_united_nations ?= { has_modifier = un_human_rights_declaration_modifier }
		has_modifier = un_human_rights_reservations_modifier
	}
}

# Country scope. A program's political reaction has not yet faded.
resettlement_country_still_fading = {
	OR = {
		AND = { has_variable = rs_volume_land_grants var:rs_volume_land_grants > 1 }
		AND = { has_variable = rs_volume_military_colonies var:rs_volume_military_colonies > 1 }
		AND = { has_variable = rs_volume_penal_transportation var:rs_volume_penal_transportation > 1 }
		AND = { has_variable = rs_volume_organized_colonization var:rs_volume_organized_colonization > 1 }
		AND = { has_variable = rs_volume_special_settlements var:rs_volume_special_settlements > 1 }
		AND = { has_variable = rs_volume_rustication var:rs_volume_rustication > 1 }
	}
}
```

- [ ] **Step 4: The effects**

Append to `common/scripted_effects/resettlement_effects.txt`:

```

# ---- The political layer (§7.2) ---------------------------------------------
# Country scope. One modifier per program, scaled by the volume it moved: twenty
# Settlement Authorities running one program still apply it once.
resettlement_refresh_politics = {
	resettlement_refresh_programme_politics = { PROG = land_grants }
	resettlement_refresh_programme_politics = { PROG = military_colonies }
	resettlement_refresh_programme_politics = { PROG = penal_transportation }
	resettlement_refresh_programme_politics = { PROG = organized_colonization }
	resettlement_refresh_programme_politics = { PROG = special_settlements }
	resettlement_refresh_programme_politics = { PROG = rustication }
}

resettlement_refresh_programme_politics = {
	if = {
		limit = { NOT = { has_variable = rs_volume_$PROG$ } }
		set_variable = { name = rs_volume_$PROG$ value = 0 }
	}
	change_variable = { name = rs_volume_$PROG$ multiply = resettlement_volume_decay }
	change_variable = { name = rs_volume_$PROG$ add = var:rs_month_$PROG$ }
	set_variable = {
		name = rs_intensity_$PROG$
		value = {
			value = var:rs_volume_$PROG$
			divide = {
				value = total_population
				multiply = resettlement_intensity_reference
				min = 1
			}
			max = 1
		}
	}
	remove_modifier = resettlement_$PROG$_politics
	if = {
		limit = { var:rs_intensity_$PROG$ > 0.01 }
		add_modifier = { name = resettlement_$PROG$_politics multiplier = var:rs_intensity_$PROG$ }
	}
}

# ---- The UN Declaration (§7.4) -----------------------------------------------
# Country scope, after resettlement_refresh_politics (which sets the three
# coercive intensities every month).
resettlement_refresh_declaration = {
	set_variable = { name = rs_declaration_intensity value = 0 }
	if = {
		limit = { resettlement_is_declaration_party = yes }
		set_variable = {
			name = rs_declaration_intensity
			value = {
				value = var:rs_intensity_penal_transportation
				add = var:rs_intensity_special_settlements
				add = var:rs_intensity_rustication
				max = 1
			}
		}
		if = {
			limit = { has_modifier = un_human_rights_reservations_modifier }
			change_variable = { name = rs_declaration_intensity multiply = 0.5 }
		}
	}
	remove_modifier = resettlement_declaration_violation
	if = {
		limit = { var:rs_declaration_intensity > 0.01 }
		add_modifier = { name = resettlement_declaration_violation multiplier = var:rs_declaration_intensity }
	}
	# The warning: once per spell of coercion, the first month a party runs a
	# coercive program, and again if it stops and later starts again.
	if = {
		limit = {
			resettlement_is_declaration_party = yes
			any_scope_state = { resettlement_state_runs_coercive = yes }
			NOT = { has_variable = rs_declaration_warned }
		}
		set_variable = rs_declaration_warned
		trigger_event = { id = resettlement.20 }
	}
	else_if = {
		limit = {
			has_variable = rs_declaration_warned
			NOT = { any_scope_state = { resettlement_state_runs_coercive = yes } }
			var:rs_declaration_intensity <= 0.01
		}
		remove_variable = rs_declaration_warned
	}
}
```

In `resettlement_country_monthly`, after the closing brace of the last `every_scope_state` (the source readouts), add:

```
	resettlement_refresh_politics = yes
	resettlement_refresh_declaration = yes
	if = {
		limit = {
			OR = {
				any_scope_state = { has_building = building_resettlement_colony }
				resettlement_country_still_fading = yes
			}
		}
		set_variable = rs_active
	}
	else_if = {
		limit = { has_variable = rs_active }
		remove_variable = rs_active
	}
```

In `common/on_actions/resettlement_on_actions.txt`, add `has_variable = rs_active` as a third line inside the `OR` of `resettlement_country_on_action`, and change the header comment's last line to: `# clear on states that gave settlers, or political reactions still fading.`

- [ ] **Step 5: The modifiers**

Append to `common/static_modifiers/resettlement_modifiers.txt`:

```

# ---- Political reactions (§7.2): multiplier = the program's intensity, 0–1 ----
# Vanilla's scale: every law on the books together is clamped to ±5 approval, a
# strongly held stance is ±2, and an IG is unhappy at −5.
resettlement_land_grants_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	interest_group_ig_rural_folk_approval_add = 2
	interest_group_ig_landowners_approval_add = -2
}

resettlement_military_colonies_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	interest_group_ig_armed_forces_approval_add = 2
	interest_group_ig_rural_folk_approval_add = -2
}

resettlement_penal_transportation_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	interest_group_ig_intelligentsia_approval_add = -2
}

resettlement_organized_colonization_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	interest_group_ig_rural_folk_approval_add = 2
}

resettlement_special_settlements_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	interest_group_ig_rural_folk_approval_add = -5
	interest_group_ig_intelligentsia_approval_add = -3
}

resettlement_rustication_politics = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	interest_group_ig_intelligentsia_approval_add = -5
	interest_group_ig_petty_bourgeoisie_approval_add = -3
}

# ---- The UN Declaration (§7.4): multiplier = coercive intensity, 0–1 --------
resettlement_declaration_violation = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_negative.dds
	country_prestige_mult = -0.1
}
```

- [ ] **Step 6: The warning event**

Append to `events/resettlement_events.txt`:

```

# ---- .20 The Declaration and Our Settlements -------------------------------------
# Sent by resettlement_refresh_declaration the first month a party to the
# Universal Declaration runs a coercive program.
resettlement.20 = {
	type = country_event
	placement = ROOT

	event_image = {
		texture = "gfx/event_pictures/international_court_chamber.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	title = resettlement.20.t
	desc = resettlement.20.d
	flavor = resettlement.20.f

	duration = 3

	option = {
		name = resettlement.20.a
		default_option = yes
		custom_tooltip = resettlement_declaration_continue_tt
		ai_chance = { base = 50 }
	}

	option = {
		name = resettlement.20.b
		resettlement_end_coercive_programmes = yes
		ai_chance = { base = 50 }
	}
}
```

- [ ] **Step 7: The UN registry column**

In `test_un_convention_registry.py`:
- Add to the column comment above `Convention`:
  ```
  # violation_modifiers  what a party carries while it breaks the convention
  #                   elsewhere in the mod (defaults to none)
  ```
- Change the `Convention` definition to:
  ```python
  Convention = namedtuple(
      "Convention",
      "key in_force member_modifier scope op event refusal_reason refusal_modifier"
      " regime_modifiers rule agenda violation_modifiers",
      defaults=((),),
  )
  ```
- Change the `human_rights` row to end with `("un_regime_rights_violator_modifier",), None, True,` followed by a new line `violation_modifiers=("resettlement_declaration_violation",)),`.
- In `test_every_modifier_named_exists`, change the loop tuple to `(c.member_modifier, c.refusal_modifier) + c.regime_modifiers + c.violation_modifiers`.

Run: `python3 -m unittest test_un_convention_registry -v`
Expected: OK, same count as before this change.

- [ ] **Step 8: Localization**

`te_miscellaneous_l_english.yml`:

```yaml
 resettlement_land_grants_politics:0 "Land Grants"
 resettlement_land_grants_politics_desc:0 "Free land for the rural poor pleases the Rural Folk and angers the Landowners, whose tenants and laborers are leaving. It grows with the number of people we settle."
 resettlement_military_colonies_politics:0 "Military Colonies"
 resettlement_military_colonies_politics_desc:0 "The Armed Forces welcome soldier-settlers on the frontier; the peasants drafted into them do not. It grows with the number of people we settle."
 resettlement_penal_transportation_politics:0 "Penal Transportation"
 resettlement_penal_transportation_politics_desc:0 "The Intelligentsia condemn the transportation of convicts and dissidents. It grows with the number of people we transport."
 resettlement_organized_colonization_politics:0 "Organized Colonization"
 resettlement_organized_colonization_politics_desc:0 "Subsidized passage and land please the Rural Folk. It grows with the number of people we settle."
 resettlement_special_settlements_politics:0 "Special Settlements"
 resettlement_special_settlements_politics_desc:0 "The deportation of farmers terrifies and enrages the countryside, and the Intelligentsia condemn it. It grows with the number of people we deport."
 resettlement_rustication_politics:0 "Rustication"
 resettlement_rustication_politics_desc:0 "Sending urban workers to the countryside outrages the Intelligentsia and the Petty Bourgeoisie, whose children are among them. It grows with the number of people we send."
 resettlement_declaration_violation:0 "Violating the Declaration"
 resettlement_declaration_violation_desc:0 "We are a party to the Universal Declaration of Human Rights and run a coercive resettlement program: Penal Transportation, Special Settlements or Rustication. The penalty grows with the number of people those programs move, is halved if we ratified with reservations, and ends once they stop."
 resettlement_declaration_continue_tt:0 "#N Violating the Declaration#! stays while the program runs, and grows with the number of people it moves."
```

`te_events_l_english.yml`:

```yaml
 resettlement.20.t:0 "The Declaration and Our Settlements"
 resettlement.20.d:0 "We are a party to the Universal Declaration of Human Rights, and we have begun a coercive resettlement program. Our treaty partners will hold it against us: while the program runs we suffer #N Violating the Declaration#!, and the more people it moves, the heavier the penalty."
 resettlement.20.f:0 "The Declaration of 1948 promised everyone the right to freedom of movement and residence within the borders of their own state."
 resettlement.20.a:0 "We accept the cost."
 resettlement.20.b:0 "End the coercive programs."
```

Append a sentence to three existing lines (keep the rest of each line as it is):
- `un_events.3.d` (in `te_events_l_english.yml`): append ` Parties that run coercive resettlement programs at home would be penalized for it.` before the closing quote.
- `un_vote.1.d_human_rights`: append ` Parties that run coercive resettlement programs at home will be penalized for it.`
- `un_human_rights_declaration_modifier_desc` (in `te_concepts_l_english.yml`): append ` Running a coercive resettlement program brings #N Violating the Declaration#!.`

- [ ] **Step 9: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry test_un_convention_registry -v`
Expected: all pass.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_effects/resettlement_effects.txt common/static_modifiers/resettlement_modifiers.txt common/scripted_triggers/resettlement_triggers.txt common/script_values/resettlement_values.txt common/on_actions/resettlement_on_actions.txt events/resettlement_events.txt && python3 scripts/analysis/check_localization_files.py && for a in modifier_multiplier_var_audit silent_variable_audit event_image_audit orphaned_event_audit; do python3 $a.py --strict || echo "FAIL $a"; done`
Expected: exit 0, no `FAIL`.

- [ ] **Step 10: Commit**

```bash
git add common/scripted_effects/resettlement_effects.txt common/scripted_triggers/resettlement_triggers.txt \
        common/script_values/resettlement_values.txt common/static_modifiers/resettlement_modifiers.txt \
        common/on_actions/resettlement_on_actions.txt events/resettlement_events.txt test_un_convention_registry.py \
        localization/english/te_miscellaneous_l_english.yml localization/english/te_events_l_english.yml \
        localization/english/te_concepts_l_english.yml test_resettlement_programme_registry.py
git commit -m "feat(resettlement): volume-scaled political reactions and the UN Declaration

One modifier per program, scaled by a decaying volume counter against the
country's population, capped at vanilla's approval scale. Parties to the
Declaration running coercive programs carry Violating the Declaration,
announced by resettlement.20 and named in the PM, the vote and the modifier.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 6: Program events

**Files:**
- Modify: `events/resettlement_events.txt` (add `.1`–`.8`)
- Modify: `common/scripted_effects/resettlement_effects.txt` (append `resettlement_roll_events`; call it from `resettlement_country_monthly`)
- Modify: `common/static_modifiers/resettlement_modifiers.txt` (event modifiers)
- Modify: loc in `te_events` and `te_miscellaneous`
- Modify: `test_resettlement_programme_registry.py` (add `EventTests`)

**Interfaces:**
- Consumes: destination variables `rs_arrived`, `rs_months_running`, `rs_last_source` (Task 4); triggers `resettlement_state_runs_voluntary`, `resettlement_state_runs_coercive` and `resettlement_runs_pm` (Task 4); `resettlement_touch_pressed_cultures` and `resettlement_end_coercive_programmes` (Task 4).
- Produces: saved scopes `rs_event_state` and `rs_return_state`; destination flags `rs_dust_done` and `rs_petition_done`; country timed variable `rs_event_cooldown`.

- [ ] **Step 1: Write the failing tests**

Add to `test_resettlement_programme_registry.py`:

```python
# id: (image kind, number of options)
EVENTS = {
    1: ("video", 2), 2: ("video", 2), 3: ("video", 2), 4: ("texture", 2),
    5: ("video", 2), 6: ("video", 2), 7: ("video", 2), 8: ("video", 2),
    9: ("video", 1), 20: ("texture", 2),
}
ROLLED = (1, 2, 3, 4, 5, 6, 7, 8)


def event(n):
    return block(read(RS_EVENTS), f"resettlement.{n}")


def options(body):
    text = strip_comments(body)
    out = []
    for m in re.finditer(r"(?<![\w])option\s*=\s*\{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append(text[m.end():i - 1])
    return out


class EventTests(unittest.TestCase):
    def test_every_event_has_image_placement_options_and_loc(self):
        L = loc()
        for n, (kind, count) in EVENTS.items():
            body = event(n)
            self.assertIsNotNone(body, n)
            self.assertIn(f"{kind} =", block(body, "event_image"), n)
            self.assertIn("placement =", body, n)
            opts = options(body)
            self.assertEqual(len(opts), count, n)
            for suffix in ("t", "d", "f"):
                self.assertIn(f"resettlement.{n}.{suffix}", L, n)
            for opt in opts:
                name = re.search(r"name\s*=\s*([\w.]+)", opt).group(1)
                self.assertIn(name, L, n)

    def test_the_roll_offers_each_programme_event_once(self):
        body = squash(block(read(EFFECTS), "resettlement_roll_events"))
        rolled = [int(n) for n in re.findall(r"trigger_event = \{ id = resettlement\.(\d+) \}", body)]
        self.assertEqual(sorted(rolled), list(ROLLED))
        self.assertIn("resettlement_system_enabled = yes", body)
        self.assertIn("NOT = { has_variable = rs_event_cooldown }", body)
        self.assertIn("resettlement_roll_events = yes", squash(block(read(EFFECTS), "resettlement_country_monthly")))

    def test_once_only_events_mark_their_state(self):
        roll = squash(block(read(EFFECTS), "resettlement_roll_events"))
        for n, flag in ((4, "rs_dust_done"), (7, "rs_petition_done")):
            self.assertIn(f"set_variable = {flag}", squash(block(event(n), "immediate")), n)
            self.assertIn(f"NOT = {{ has_variable = {flag} }}", roll, n)

    def test_land_disputes_rewards_nothing(self):
        negotiate, back = options(event(8))
        for opt in (negotiate, back):
            self.assertNotIn("approval", opt)
            self.assertNotIn("_positive_", opt)
        self.assertIn("EFFECT = add_radicals_in_state", squash(back))
        self.assertNotIn("add_modifier", back)

    def test_event_modifiers_are_localized(self):
        mods = read(RS_MODIFIERS)
        L = loc()
        for name in ("resettlement_land_rush", "resettlement_orderly_survey", "resettlement_land_office_crackdown",
                     "resettlement_speculators", "resettlement_hard_winter", "resettlement_soil_conservation",
                     "resettlement_dust_bowl", "resettlement_reformed", "resettlement_defiant",
                     "resettlement_reserves", "resettlement_negotiation_cost"):
            self.assertIsNotNone(block(mods, name), name)
            self.assertIn(name, L)
            self.assertIn(f"{name}_desc", L)
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `python3 -m unittest test_resettlement_programme_registry.EventTests -v`
Expected: FAIL (events `.1`–`.8` missing).

- [ ] **Step 3: The roll**

Append to `common/scripted_effects/resettlement_effects.txt`:

```

# ---- Events (§8) ---------------------------------------------------------------
# Country scope, after the month's transfers. At most one program event every
# eighteen months, from a destination that received settlers this month.
resettlement_roll_events = {
	if = {
		limit = {
			resettlement_system_enabled = yes
			NOT = { has_variable = rs_event_cooldown }
			any_scope_state = {
				has_building = building_resettlement_colony
				has_variable = rs_arrived
				var:rs_arrived > 0
			}
		}
		random = {
			chance = 10
			random_scope_state = {
				limit = {
					has_building = building_resettlement_colony
					has_variable = rs_arrived
					var:rs_arrived > 0
				}
				save_scope_as = rs_event_state
				save_scope_as = rs_destination
			}
			set_variable = { name = rs_event_cooldown days = 540 }
			random_list = {
				10 = {
					trigger = { scope:rs_event_state = { resettlement_state_runs_voluntary = yes } }
					trigger_event = { id = resettlement.1 }
				}
				10 = {
					trigger = { scope:rs_event_state = { resettlement_state_runs_voluntary = yes } }
					trigger_event = { id = resettlement.2 }
				}
				10 = {
					trigger_event = { id = resettlement.3 }
				}
				10 = {
					trigger = {
						scope:rs_event_state = {
							resettlement_runs_pm = { PM = pm_resettlement_homesteads }
							var:rs_months_running >= 120
							NOT = { has_variable = rs_dust_done }
						}
					}
					trigger_event = { id = resettlement.4 }
				}
				10 = {
					trigger = { scope:rs_event_state = { resettlement_state_runs_coercive = yes } }
					trigger_event = { id = resettlement.5 }
				}
				10 = {
					trigger = { scope:rs_event_state = { resettlement_runs_pm = { PM = pm_resettlement_special_settlements } } }
					trigger_event = { id = resettlement.6 }
				}
				10 = {
					trigger = {
						scope:rs_event_state = {
							resettlement_state_runs_coercive = yes
							var:rs_months_running >= 60
							NOT = { has_variable = rs_petition_done }
							has_variable = rs_last_source
							var:rs_last_source = { owner = scope:rs_country }
						}
					}
					trigger_event = { id = resettlement.7 }
				}
				10 = {
					trigger = { scope:rs_event_state = { any_scope_pop = { pop_acceptance < acceptance_status_4 } } }
					trigger_event = { id = resettlement.8 }
				}
			}
		}
	}
}
```

In `resettlement_country_monthly`, after `resettlement_refresh_declaration = yes`, add `resettlement_roll_events = yes`.

- [ ] **Step 4: The event modifiers**

Append to `common/static_modifiers/resettlement_modifiers.txt`:

```

# ---- Event modifiers (§8) --------------------------------------------------
resettlement_land_rush = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_resettlement_transfer_add = 2000
}

resettlement_orderly_survey = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_construction_mult = 0.10
}

resettlement_land_office_crackdown = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	country_authority_add = -50
}

resettlement_speculators = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	state_resettlement_transfer_add = -500
}

resettlement_hard_winter = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	state_migration_pull_add = -10
}

resettlement_soil_conservation = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds
	building_group_bg_agriculture_throughput_add = -0.05
	building_group_bg_ranching_throughput_add = -0.05
}

resettlement_dust_bowl = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds
	building_group_bg_agriculture_throughput_add = -0.2
	building_group_bg_ranching_throughput_add = -0.2
}

resettlement_reformed = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	country_prestige_mult = 0.05
}

resettlement_defiant = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	country_prestige_mult = -0.05
}

resettlement_reserves = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	state_resettlement_transfer_add = -300
}

resettlement_negotiation_cost = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	country_authority_add = -25
}
```

- [ ] **Step 5: The events**

Insert into `events/resettlement_events.txt`, before the `.9` section:

```
# ---- .1 Land Rush ------------------------------------------------------------
# Rolled for a voluntary program. Oklahoma, 1889.
resettlement.1 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "europenorthamerica_gold_prospectors"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = resettlement.1.t
	desc = resettlement.1.d
	flavor = resettlement.1.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.1.a
		default_option = yes
		scope:rs_event_state = {
			add_modifier = { name = resettlement_land_rush days = 365 }
		}
		custom_tooltip = resettlement_land_rush_pressure_tt
		ai_chance = { base = 60 }
	}

	option = {
		name = resettlement.1.b
		scope:rs_event_state = {
			add_modifier = { name = resettlement_orderly_survey days = 730 }
		}
		ai_chance = { base = 40 }
	}
}

# ---- .2 The Speculators ------------------------------------------------------
# Rolled for a voluntary program. Railroad land grants and homestead fraud.
resettlement.2 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "europenorthamerica_capitalists_meeting"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = resettlement.2.t
	desc = resettlement.2.d
	flavor = resettlement.2.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.2.a
		default_option = yes
		add_modifier = { name = resettlement_land_office_crackdown days = 730 }
		ig:ig_rural_folk = {
			add_modifier = { name = ig_approval_positive_modifier days = normal_modifier_time }
		}
		ai_chance = { base = 50 }
	}

	option = {
		name = resettlement.2.b
		scope:rs_event_state = {
			add_modifier = { name = resettlement_speculators days = 730 }
		}
		ig:ig_landowners = {
			add_modifier = { name = ig_approval_positive_modifier days = normal_modifier_time }
		}
		ig:ig_industrialists = {
			add_modifier = { name = ig_approval_positive_modifier days = normal_modifier_time }
		}
		ai_chance = { base = 50 }
	}
}

# ---- .3 A Hard Winter ------------------------------------------------------------
# Rolled for any program.
resettlement.3 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "unspecific_sick_in_hospital"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_skull.dds"

	title = resettlement.3.t
	desc = resettlement.3.d
	flavor = resettlement.3.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.3.a
		default_option = yes
		add_treasury = {
			value = yearly_gross_income
			multiply = -0.01
		}
		ai_chance = { base = 60 }
	}

	option = {
		name = resettlement.3.b
		scope:rs_event_state = {
			kill_population_in_state = { value = 1000 strata = lower }
			add_radicals_in_state = { value = medium_radicals strata = lower }
			add_modifier = { name = resettlement_hard_winter days = 365 }
		}
		ai_chance = { base = 40 }
	}
}

# ---- .4 Dust Storms ------------------------------------------------------------
# Rolled once per destination, after ten years of Homesteads. The Dust Bowl;
# the Virgin Lands, 1960–65.
resettlement.4 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		texture = "gfx/event_pictures/climate_refugee_exodus.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = resettlement.4.t
	desc = resettlement.4.d
	flavor = resettlement.4.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	immediate = {
		scope:rs_event_state = {
			set_variable = rs_dust_done
		}
	}

	option = {
		name = resettlement.4.a
		default_option = yes
		add_treasury = {
			value = yearly_gross_income
			multiply = -0.02
		}
		scope:rs_event_state = {
			add_modifier = { name = resettlement_soil_conservation days = 3650 }
		}
		ai_chance = { base = 60 }
	}

	option = {
		name = resettlement.4.b
		scope:rs_event_state = {
			add_modifier = { name = resettlement_dust_bowl days = 1825 is_decaying = yes }
		}
		ai_chance = { base = 40 }
	}
}

# ---- .5 The Reform Campaign ----------------------------------------------------
# Rolled for a coercive program. The Anti-Transportation League, Chekhov's
# Sakhalin Island, Albert Londres in French Guiana.
resettlement.5 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "middleeast_courtroom_upheaval"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_newspaper.dds"

	title = resettlement.5.t
	desc = resettlement.5.d
	flavor = resettlement.5.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.5.a
		resettlement_end_coercive_programmes = yes
		add_modifier = { name = resettlement_reformed days = 1825 }
		ig:ig_intelligentsia = {
			add_modifier = { name = ig_approval_positive_modifier days = normal_modifier_time }
		}
		ai_chance = { base = 40 }
	}

	option = {
		name = resettlement.5.b
		default_option = yes
		add_modifier = { name = resettlement_defiant days = 1825 }
		ig:ig_intelligentsia = {
			add_modifier = { name = ig_approval_negative_modifier days = normal_modifier_time }
		}
		ai_chance = { base = 60 }
	}
}

# ---- .6 Famine in the Settlements -------------------------------------------------
# Rolled for Special Settlements. Nazino, 1933.
resettlement.6 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "asia_dead_cattle_poor_harvest"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_skull.dds"

	title = resettlement.6.t
	desc = resettlement.6.d
	flavor = resettlement.6.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.6.a
		default_option = yes
		add_treasury = {
			value = yearly_gross_income
			multiply = -0.02
		}
		ai_chance = { base = 50 }
	}

	option = {
		name = resettlement.6.b
		scope:rs_event_state = {
			kill_population_in_state = { value = 5000 pop_type = farmers }
			add_radicals_in_state = { value = large_radicals pop_type = farmers }
		}
		ig:ig_rural_folk = {
			add_modifier = { name = ig_approval_very_negative_modifier days = normal_modifier_time }
		}
		ai_chance = { base = 50 }
	}
}

# ---- .7 A Petition to Return ------------------------------------------------------
# Rolled once per destination, after five years of a coercive program. The
# special settlers' release from 1954; the zhiqing strikes of 1978–79.
resettlement.7 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "asia_poor_people_moving"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_protest.dds"

	title = resettlement.7.t
	desc = resettlement.7.d
	flavor = resettlement.7.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
		scope:rs_event_state = { has_variable = rs_last_source }
	}

	immediate = {
		scope:rs_event_state = {
			set_variable = rs_petition_done
			var:rs_last_source = { save_scope_as = rs_return_state }
		}
	}

	option = {
		name = resettlement.7.a
		# Those resettled can no longer be told apart from anyone else here, so
		# one in twenty of the lower strata goes home.
		custom_tooltip = {
			text = resettlement_return_tt
			scope:rs_event_state = {
				every_scope_pop = {
					limit = {
						strata = lower
						NOT = { is_pop_type = slaves }
					}
					move_partial_pop = {
						state = scope:rs_return_state
						population_ratio = 0.05
					}
				}
			}
		}
		scope:rs_return_state = {
			add_loyalists_in_state = { value = medium_radicals strata = lower }
		}
		resettlement_end_coercive_programmes = yes
		ai_chance = { base = 40 }
	}

	option = {
		name = resettlement.7.b
		default_option = yes
		scope:rs_event_state = {
			add_radicals_in_state = { value = large_radicals strata = lower }
		}
		ai_chance = { base = 60 }
	}
}

# ---- .8 Land Disputes -----------------------------------------------------------------
# Rolled where settlers arrive among people below second-class acceptance
# (§7.3). No option rewards the pressure: backing the settlers only avoids the
# cost of negotiating.
resettlement.8 = {
	type = country_event
	placement = scope:rs_event_state

	event_image = {
		video = "unspecific_signed_contract"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	title = resettlement.8.t
	desc = resettlement.8.d
	flavor = resettlement.8.f

	duration = 3

	trigger = {
		exists = scope:rs_event_state
	}

	option = {
		name = resettlement.8.a
		default_option = yes
		add_treasury = {
			value = yearly_gross_income
			multiply = -0.01
		}
		add_modifier = { name = resettlement_negotiation_cost days = 730 }
		scope:rs_event_state = {
			add_modifier = { name = resettlement_reserves days = 3650 }
			resettlement_touch_pressed_cultures = { EFFECT = add_loyalists_in_state VALUE = medium_radicals }
		}
		ai_chance = { base = 50 }
	}

	option = {
		name = resettlement.8.b
		scope:rs_event_state = {
			resettlement_touch_pressed_cultures = { EFFECT = add_radicals_in_state VALUE = medium_radicals }
		}
		ai_chance = { base = 50 }
	}
}

```

- [ ] **Step 6: Localization**

`te_events_l_english.yml`:

```yaml
 resettlement.1.t:0 "Land Rush in [SCOPE.sState('rs_event_state').GetName]"
 resettlement.1.d:0 "Word that the government is giving land away in [SCOPE.sState('rs_event_state').GetName] has spread faster than our surveyors can work. Crowds of would-be settlers are camped at the boundary markers, waiting for the signal to stake their claims."
 resettlement.1.f:0 "In 1889 fifty thousand people raced into the Unassigned Lands of Oklahoma at the sound of a gun. Some had slipped across the line the night before."
 resettlement.1.a:0 "Open the land at once."
 resettlement.1.b:0 "Survey it first."
 resettlement.2.t:0 "The Speculators"
 resettlement.2.d:0 "Agents of land companies are filing claims in [SCOPE.sState('rs_event_state').GetName] in the names of settlers who do not exist, and reselling the best plots at a profit. Genuine settlers arrive to find the land already taken."
 resettlement.2.f:0 "Much of the land given away under the Homestead Act ended up with speculators, cattle companies and railroads rather than the families it was meant for."
 resettlement.2.a:0 "Send in the inspectors."
 resettlement.2.b:0 "The market will sort it out."
 resettlement.3.t:0 "A Hard Winter on the Frontier"
 resettlement.3.d:0 "The first winter has caught the settlers of [SCOPE.sState('rs_event_state').GetName] in sod houses and dugouts. Fuel is short, the roads are closed and the new arrivals are falling sick."
 resettlement.3.f:0 "Settlers on the northern plains measured their first years by the winters they survived."
 resettlement.3.a:0 "Send relief."
 resettlement.3.b:0 "They knew what they were signing up for."
 resettlement.4.t:0 "Dust Storms over [SCOPE.sState('rs_event_state').GetName]"
 resettlement.4.d:0 "Years of plowing have stripped the grass that held the soil of [SCOPE.sState('rs_event_state').GetName]. Now the wind is taking the topsoil with it, in black clouds that bury fences and machinery."
 resettlement.4.f:0 "The Dust Bowl of the 1930s drove hundreds of thousands off the Great Plains, and erosion ruined millions of hectares of the Virgin Lands in the early 1960s."
 resettlement.4.a:0 "Fund a conservation program."
 resettlement.4.b:0 "Keep plowing."
 resettlement.5.t:0 "The Reform Campaign"
 resettlement.5.d:0 "A campaign against our coercive resettlement has caught the public's attention. Writers and reformers have published accounts of conditions in the settlements of [SCOPE.sState('rs_event_state').GetName], and they are demanding that the program end."
 resettlement.5.f:0 "Chekhov's account of the penal colony on Sakhalin, Albert Londres's reports from French Guiana and Australia's Anti-Transportation League all turned public opinion against penal colonies."
 resettlement.5.a:0 "End the coercive programs."
 resettlement.5.b:0 "These accounts are exaggerated."
 resettlement.6.t:0 "Famine in the Settlements"
 resettlement.6.d:0 "The deportees sent to [SCOPE.sState('rs_event_state').GetName] were set down without tools or seed. Now the settlements are starving."
 resettlement.6.f:0 "In 1933 several thousand deportees were left on the island of Nazino in the Ob River without food or shelter. Within weeks most of them were dead."
 resettlement.6.a:0 "Send grain and tools."
 resettlement.6.b:0 "Let the settlements fend for themselves."
 resettlement.7.t:0 "A Petition to Return"
 resettlement.7.d:0 "Thousands of the people we resettled in [SCOPE.sState('rs_event_state').GetName] have signed a petition asking to go home to [SCOPE.sState('rs_return_state').GetName]. Some are refusing to work, and some have already left without permission."
 resettlement.7.f:0 "The Soviet special settlers were released from 1954 onward. In 1978 and 1979 strikes by sent-down youth in Yunnan led China to end the Down to the Countryside movement."
 resettlement.7.a:0 "Let them go home."
 resettlement.7.b:0 "The program continues."
 resettlement.8.t:0 "Land Disputes in [SCOPE.sState('rs_event_state').GetName]"
 resettlement.8.d:0 "The settlers arriving in [SCOPE.sState('rs_event_state').GetName] are fencing land that others have farmed, hunted and grazed for generations. The people who were here first are appealing to the government."
 resettlement.8.f:0 "Treaties, reserves and broken promises followed the settlement of almost every frontier."
 resettlement.8.a:0 "Negotiate reserves for them."
 resettlement.8.b:0 "Back the settlers' claims."
```

`te_miscellaneous_l_english.yml`:

```yaml
 resettlement_land_rush_pressure_tt:0 "More arrivals also mean more pressure on the people already living here."
 resettlement_return_tt:0 "One in twenty of the lower strata in [SCOPE.sState('rs_event_state').GetName] go home to [SCOPE.sState('rs_return_state').GetName]."
 resettlement_land_rush:0 "Land Rush"
 resettlement_land_rush_desc:0 "The land has been thrown open, and settlers are pouring in."
 resettlement_orderly_survey:0 "Orderly Survey"
 resettlement_orderly_survey_desc:0 "The land was surveyed before it was settled, and building goes smoothly."
 resettlement_land_office_crackdown:0 "Land Office Crackdown"
 resettlement_land_office_crackdown_desc:0 "Inspectors are chasing fraudulent claims through the land offices."
 resettlement_speculators:0 "Land Speculators"
 resettlement_speculators_desc:0 "Speculators hold the best claims, and fewer genuine settlers come."
 resettlement_hard_winter:0 "A Hard Winter"
 resettlement_hard_winter_desc:0 "Word of the last winter keeps settlers away."
 resettlement_soil_conservation:0 "Soil Conservation"
 resettlement_soil_conservation_desc:0 "Shelterbelts, contour plowing and fallow fields hold the soil, at some cost to the harvest."
 resettlement_dust_bowl:0 "Dust Bowl"
 resettlement_dust_bowl_desc:0 "The topsoil is blowing away."
 resettlement_reformed:0 "Resettlement Reformed"
 resettlement_reformed_desc:0 "We ended our coercive resettlement when the public demanded it."
 resettlement_defiant:0 "Defiant over Resettlement"
 resettlement_defiant_desc:0 "We brushed aside accounts of our coercive resettlement."
 resettlement_reserves:0 "Reserves Negotiated"
 resettlement_reserves_desc:0 "Land set aside for the people who were here first is closed to settlers."
 resettlement_negotiation_cost:0 "Reserve Negotiations"
 resettlement_negotiation_cost_desc:0 "Commissioners and surveyors are tied up in negotiations over the frontier's reserves."
```

- [ ] **Step 7: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry -v`
Expected: all pass.
Run: `python3 scripts/format_paradox_tabs.py --check events/resettlement_events.txt common/scripted_effects/resettlement_effects.txt common/static_modifiers/resettlement_modifiers.txt && python3 scripts/analysis/check_localization_files.py && for a in event_image_audit orphaned_event_audit silent_variable_audit loc_render_audit prev_scope_audit event_context_audit; do python3 $a.py --strict || echo "FAIL $a"; done`
Expected: no `FAIL`. If `event_context_audit` flags `unchosen_self_action` on an event here, read the flag. The recipient chose the program by building the Settlement Authority and picking its PM, so the flag is a false positive of the pulse dispatch. Add inside the event block `# REVIEWED 2026-09-26 (unchosen_self_action): the recipient chose this program by building a Settlement Authority and selecting its PM` and re-run.

- [ ] **Step 8: Commit**

```bash
git add events/resettlement_events.txt common/scripted_effects/resettlement_effects.txt \
        common/static_modifiers/resettlement_modifiers.txt localization/english/te_events_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml test_resettlement_programme_registry.py
git commit -m "feat(resettlement): program events — land rush to land disputes

Eight events rolled at most every eighteen months from a destination that
received settlers: land rush, speculators, hard winter, dust storms, reform
campaign, famine, petition to return, land disputes. No option rewards land
pressure.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 7: The debug event

**Files:**
- Create: `events/te_debug_resettlement_events.txt`
- Modify: `te_events_l_english.yml`
- Modify: `test_resettlement_programme_registry.py` (add `DebugTests`)

**Interfaces:**
- Consumes: `resettlement_country_monthly`, `resettlement_close_frontier`, frontier values (Tasks 2–4).
- Produces: console event `te_debug_resettlement.1`, which answers the spec's five engine questions from `debug.log`.

- [ ] **Step 1: Write the failing test**

```python
DEBUG_EVENTS = "events/te_debug_resettlement_events.txt"


class DebugTests(unittest.TestCase):
    def test_console_event(self):
        text = read(DEBUG_EVENTS)
        self.assertRegex(text, r"(?m)^te_debug_resettlement\.1 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        body = block(text, "te_debug_resettlement.1")
        self.assertEqual(len(options(body)), 4)
        flat = squash(body)
        for call in ("create_building = { building = building_resettlement_colony level = 5 }",
                     "resettlement_country_monthly = yes", "resettlement_close_frontier = yes",
                     "TE_RESETTLEMENT:"):
            self.assertIn(call, flat)
        L = loc()
        for suffix in ("t", "desc", "flavor", "a", "b", "c", "d"):
            self.assertIn(f"te_debug_resettlement.1.{suffix}", L)
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `python3 -m unittest test_resettlement_programme_registry.DebugTests -v`
Expected: ERROR (file missing).

- [ ] **Step 3: Write the event**

Create `events/te_debug_resettlement_events.txt` (BOM, tabs):

```
namespace = te_debug_resettlement

# ============================================================================
# INTERNAL RESETTLEMENT — console test event: `event te_debug_resettlement.1`
# ============================================================================
# Each option writes TE_RESETTLEMENT: lines to debug.log. Together they answer
# the design's in-game questions (spec, "Verify in-game before building on
# them"): exact counts moved, arrivals' pop types, deaths by type, closure.
# ============================================================================

te_debug_resettlement.1 = { # REVIEWED 2026-09-26: console-only test event (`event te_debug_resettlement.1`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = {
		texture = "gfx/event_pictures/humanitarian_camp_tents.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = te_debug_resettlement.1.t
	desc = te_debug_resettlement.1.desc
	flavor = te_debug_resettlement.1.flavor

	# Found a five-level Settlement Authority in our emptiest open frontier.
	option = {
		name = te_debug_resettlement.1.a
		default_option = yes
		ordered_scope_state = {
			limit = {
				resettlement_state_is_open_frontier = yes
				NOT = { has_building = building_resettlement_colony }
			}
			order_by = resettlement_frontier_close_margin
			position = 0
			check_range_bounds = no
			create_building = { building = building_resettlement_colony level = 5 }
			debug_log = "TE_RESETTLEMENT: debug founded a Settlement Authority at [THIS.GetState.GetName]"
		}
	}

	# Run this month's resettlement now (the transfer, readouts, politics).
	option = {
		name = te_debug_resettlement.1.b
		resettlement_country_monthly = yes
	}

	# Close one of our Settlement Authorities now, as if its frontier had filled.
	option = {
		name = te_debug_resettlement.1.c
		save_scope_as = rs_country
		random_scope_state = {
			limit = { has_building = building_resettlement_colony }
			resettlement_close_frontier = yes
		}
	}

	# Print the frontier numbers for our capital and every Settlement Authority.
	option = {
		name = te_debug_resettlement.1.d
		every_scope_state = {
			limit = {
				OR = {
					is_capital = yes
					has_building = building_resettlement_colony
				}
			}
			debug_log = "TE_RESETTLEMENT: [THIS.GetState.GetName] region [THIS.GetState.MakeScope.ScriptValue('te_region_population')|0] people on [THIS.GetState.MakeScope.ScriptValue('te_region_area_km2')|0] km² = [THIS.GetState.MakeScope.ScriptValue('resettlement_frontier_density')|2] per km²; opens below [THIS.GetState.MakeScope.ScriptValue('resettlement_frontier_open_density')|2], closes at [THIS.GetState.MakeScope.ScriptValue('resettlement_frontier_close_density')|2]; capacity [THIS.GetState.MakeScope.ScriptValue('resettlement_debug_capacity')|0]"
		}
	}
}
```

Append to `common/script_values/resettlement_values.txt`:

```

# State scope. The capacity modifier, for the debug event's log line.
resettlement_debug_capacity = {
	value = modifier:state_resettlement_transfer_add
}
```

`te_events_l_english.yml`:

```yaml
 te_debug_resettlement.1.t:0 "Debug: Internal Resettlement"
 te_debug_resettlement.1.desc:0 "Test the Settlement Authority. Every option writes TE_RESETTLEMENT: lines to debug.log."
 te_debug_resettlement.1.flavor:0 "Console only."
 te_debug_resettlement.1.a:0 "Found a Settlement Authority in our emptiest frontier"
 te_debug_resettlement.1.b:0 "Run this month's resettlement now"
 te_debug_resettlement.1.c:0 "Close one of our Settlement Authorities"
 te_debug_resettlement.1.d:0 "Log the frontier numbers"
```

- [ ] **Step 4: Run the tests to confirm they pass**

Run: `python3 -m unittest test_resettlement_programme_registry -v && python3 orphaned_event_audit.py --strict && python3 event_image_audit.py --strict`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add events/te_debug_resettlement_events.txt common/script_values/resettlement_values.txt \
        localization/english/te_events_l_english.yml test_resettlement_programme_registry.py
git commit -m "feat(resettlement): console test event te_debug_resettlement.1

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 8: Loc routing, the concept, and the docs

**Files:**
- Modify: `organize_loc.py` (route `resettlement_` keys), `test_organize_loc.py`
- Modify: `common/game_concepts/extra_concepts.txt`, `te_concepts_l_english.yml`, `te_buildings_l_english.yml` (the building's description names the concept)
- Modify: `docs/systems/mod_systems.md` (a system section; the on_actions table and pulse list)
- Modify: `test_resettlement_programme_registry.py` (add `DocsTests`)

- [ ] **Step 1: Write the failing tests**

In `test_organize_loc.py`, add to `CategorizeKeyTests`:

```python
    def test_resettlement_families_stay_together(self):
        for key in ("resettlement_arrivals", "resettlement_arrivals_desc",
                    "resettlement_special_settlements_politics", "resettlement_special_settlements_politics_desc",
                    "resettlement_declaration_pm_line", "resettlement_possible_open_frontier_tt"):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS")
```

In `test_resettlement_programme_registry.py`:

```python
MOD_SYSTEMS = "docs/systems/mod_systems.md"


class DocsTests(unittest.TestCase):
    def test_the_system_section_names_every_programme(self):
        text = read(MOD_SYSTEMS)
        m = re.search(r"(?ms)^## Internal Resettlement \(Settlement Authority\)\n(.*?)(?=^## )", text)
        self.assertIsNotNone(m)
        section = m.group(1)
        L = loc()
        for p in PROGRAMMES:
            self.assertIn(L[pm(p.key)], section, p.key)
        self.assertIn("test_resettlement_programme_registry.py", section)

    def test_no_doc_names_the_old_transfer(self):
        self.assertNotIn("resettlement_transfer_on_action", read(MOD_SYSTEMS))

    def test_concept(self):
        self.assertIsNotNone(block(read("common/game_concepts/extra_concepts.txt"), "concept_internal_resettlement"))
        L = loc()
        self.assertIn("concept_internal_resettlement", L)
        self.assertIn("concept_internal_resettlement_desc", L)
        self.assertIn("[concept_internal_resettlement]", L["building_resettlement_colony_desc"])
```

- [ ] **Step 2: Run them to confirm they fail**

Run: `python3 -m unittest test_organize_loc.CategorizeKeyTests test_resettlement_programme_registry.DocsTests -v`
Expected: FAIL.

- [ ] **Step 3: Route the keys**

In `organize_loc.py`, directly after the `TE_HOMELAND_` rule (`if key.startswith("TE_HOMELAND_"): return "MISCELLANEOUS"`), add:

```python
    # Internal resettlement (the Settlement Authority): static modifiers,
    # tooltips and the Declaration splice line. Four-token names would land in
    # MISCELLANEOUS and their `_desc` halves in CONCEPTS; two- and three-token
    # ones would all fall to CONCEPTS, away from the rest of the family.
    if key.startswith("resettlement_"):
        return "MISCELLANEOUS"
```

Then run `python3 organize_loc.py --dry-run` from the worktree root. `mod_path` resolves to the worktree, so it never touches the main checkout. Expected: no resettlement key reported as moving. If one is, move it to the file named, then re-run.

- [ ] **Step 4: The concept**

Append to `common/game_concepts/extra_concepts.txt`:

```
concept_internal_resettlement = {
	texture = "gfx/interface/icons/generic_icons/population.dds"
}
```

`te_concepts_l_english.yml`:

```yaml
 concept_internal_resettlement:0 "Internal Resettlement"
 concept_internal_resettlement_desc:0 "Government-run movement of people from one part of the country to another. A Settlement Authority on a thinly populated frontier recruits across the country under one program (from land grants to deportation), moves the number shown in the state's modifiers each month, and closes when the region fills up. Coercive programs cost lives in transit, anger the people left behind, and breach the Universal Declaration of Human Rights for its parties. Settlers press on anyone already living on the frontier who is not at least a second-class citizen."
```

In `te_buildings_l_english.yml`, change `building_resettlement_colony_desc` to begin `A [concept_internal_resettlement] office that recruits settlers …` (the rest unchanged).

- [ ] **Step 5: The docs**

In `docs/systems/mod_systems.md`:
- In the `on_monthly_pulse_state` list under "Pulse Wiring", delete the line `` - `resettlement_transfer_on_action` — population transfer ``.
- In the on-actions file table, add two rows (alphabetical by file):
  ```
  | `resettlement_on_actions.txt` | Internal resettlement: the monthly country pulse (transfer, readouts, politics, Declaration, events) | Pulse (monthly) |
  | `te_region_area_on_actions.txt` | Writes each state region's land area once per save (`te_region_area_generated.txt`) | Mixed |
  ```
- Add a section directly before `## Population Transfer (Treaty Article)`:

```markdown
## Internal Resettlement (Settlement Authority)

- **Design:** `docs/superpowers/specs/2026-09-26-internal-resettlement-design.md` (Decisions table is settled). International transfers stay with the Population Transfer treaty article below.
- **Building:** `building_resettlement_colony`, displayed as Settlement Authority, in the destination state only. Frontier gate: a new one needs fewer than 2 people per km² over the whole state region, and it closes at 10 per km²; both scale with `1 + state_migration_crowding_density_mult`. Areas come from `te_region_area_generated.txt` (`scripts/generators/gen_region_area.py`). Level cap is 5 from `base_values`, plus 5 each from nationalism, civilizing_mission, mass_propaganda, keynesian_economics and civil_rights_movement.
- **Programs** (`pmg_resettlement_programme`): Land Grants, Military Colonies, Penal Transportation, Organized Colonization, Special Settlements, Development Program, Rustication, Managed Retreat. Each sets who is recruited (`resettlement_pop_eligible`; never by culture or religion), capacity (`state_resettlement_transfer_add`, half level-scaled, half workforce-scaled), staff, goods and destination effects. Settlement plans (`pmg_resettlement_settlement`): Homesteads, Work Settlements, Planned Towns. Transport (`pmg_resettlement_transportation`) adds capacity.
- **Monthly pulse** (`resettlement_country_monthly`, `on_monthly_pulse_country`):
  - Each Authority walks its owner's states in order of eligible population (Recruitment Drive decree states first) and takes up to 2% of each eligible pop (4% under a drive), skipping takes under 100.
  - It moves the survivors with `move_partial_pop`; for coercive programs, deaths in transit are removed at the source in steps of 100.
  - Readouts: *Settlers arrived* and *Died in transit* on the building, *Recruited for resettlement* on each source.
- **Consequences:**
  - Source unrest (Special Settlements, Rustication).
  - Land pressure on pops below second-class acceptance at the destination: only ever a cost.
  - One political modifier per program, `resettlement_<program>_politics`, scaled by a volume counter that decays 11/12 a month, never per building.
  - `resettlement_declaration_violation` for parties to the UN Declaration running coercive programs, announced by `resettlement.20`.
- **Events:** `resettlement.1`–`.8` rolled at most every 18 months; `.9` on closure; `.20` the Declaration warning.
- **Game rule:** `internal_resettlement_rule` (enabled / AI voluntary only / disabled).
- **Homelands:** left emergent. Settlers shift culture shares at the destination, which may eventually create or remove a homeland under the homeland system's own gates and timer. Nothing here special-cases it.
- **Adding a program:** add a row to `PROGRAMMES` in `test_resettlement_programme_registry.py` and follow the failures: the PM and its loc, the group list, the code switch, the eligibility branch, the month counter, the voluntary or coercive trigger, the politics modifier and this section.
- **Debug:** `event te_debug_resettlement.1`; `TE_RESETTLEMENT:` lines in `debug.log`.
```

- [ ] **Step 6: Run the tests to confirm they pass**

Run: `python3 -m unittest test_organize_loc test_resettlement_programme_registry -v && python3 scripts/analysis/check_localization_files.py && python3 concept_reference_audit.py && grep -c concept_internal_resettlement docs/engine/concept_reference_report.md`
Expected: tests pass; the last command prints `0` (the concept is defined, so the report does not flag it). Don't commit the regenerated report.

- [ ] **Step 7: Commit**

```bash
git add organize_loc.py test_organize_loc.py common/game_concepts/extra_concepts.txt \
        localization/english/te_concepts_l_english.yml localization/english/te_buildings_l_english.yml \
        docs/systems/mod_systems.md test_resettlement_programme_registry.py
git commit -m "docs(resettlement): system section, concept, loc routing

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01T1qW8R8hupnD5XBr5jhEoa"
```

---

### Task 9: Full verification and the PR body

No new behavior. This task runs every game-independent check CI runs, then a reload on a second server from the worktree, then writes the in-game checklist.

- [ ] **Step 1: CI's checks, locally**

```bash
cd ~/src/Vic3TE-internal-resettlement
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent \
       VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
python3 -m compileall -q . >/dev/null && echo compile-ok
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs python3 -m unittest 2>&1 | tail -3
ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' | grep -v -x -E 'common/ideologies/modified\.txt|common/interest_groups/00_.*\.txt|common/scripted_effects/extra_law_consistency_generated\.txt')
python3 scripts/analysis/check_localization_files.py
python3 scripts/analysis/check_post_load_rosters.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image \
         treaty_leverage_side event_context silent_variable prev_scope container_timed_variable je_immediate_reset; do
  python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"
done
python3 kill_character_audit.py --check >/dev/null || echo "FAIL kill_character"
python3 attitude_key_audit.py >/dev/null || echo "FAIL attitude_key"
```

Expected: `compile-ok`; unittest `OK` (skips allowed); ruff clean; no `FAIL` lines. Fix anything that fails in the task that owns it, re-run that task's tests, and commit the fix there.

The three excluded paths are the ones CI's tab check excludes (generator-owned files).

- [ ] **Step 2: Mod textures for the image audit**

The worktree is sparse (`gfx/` excluded), so `event_image_audit` cannot see mod textures. Re-include the event pictures, then re-run it:

```bash
git sparse-checkout add /gfx/event_pictures/
python3 event_image_audit.py --strict && echo images-ok
```

- [ ] **Step 3: A reload from a second server**

Follow `docs/guides/python_tools.md` § "Starting the Server" to start a server **from the worktree** on another port. Never POST to the main checkout's server (port 8950): its regenerators would rewrite the main checkout. Then:

```bash
curl -s -X POST "http://localhost:<port>/reload?mod_only=true&audits_only=true" | python3 -c "
import json,sys; r=json.load(sys.stdin)
print('parse_failures', r.get('parse_failures')); print('warnings', len(r.get('warnings', [])))
[print(w.get('label'), str(w)[:300]) for w in r.get('warnings', []) if 'resettle' in json.dumps(w).lower() or 'region_area' in json.dumps(w).lower()]"
curl -s "http://localhost:<port>/modifier-search?q=resettlement" | python3 -c "import json,sys; print(json.load(sys.stdin)['matching_modifier_names'])"
```

Expected: `parse_failures` empty; no warning mentioning resettlement or region_area; the modifier list includes `building_resettlement_arrivals_add`, `building_resettlement_transit_deaths_add`, `state_resettlement_recruits_add` and `state_resettlement_transfer_add`. Then check `docs/engine/loc_coverage_report.md` and `docs/engine/modifier_visibility_report.md` in the worktree for any line naming a `resettlement` key. Fix any real finding; don't commit the regenerated `docs/engine/*` churn.

Stop the second server afterwards.

- [ ] **Step 4: The PR body with the in-game checklist**

Write `PR_BODY.md` in the worktree root (untracked; `git status` should show it and nothing else unstaged). It should contain: a summary (what replaced what, and why, from the spec's Context and Decisions), `Closes` lines only if an issue exists, the list of commits, and this in-game checklist:

```markdown
## In-game checks

Setup: build an integration from this branch in the **full** main checkout (see CLAUDE.md "Play-testing unmerged work"), `./scripts/deploy.sh --apply`, and make sure no Workshop copy of the mod is enabled.

1. New game, 1836. Settlement Authority **buildable** in Kansas (USA), Tomsk (RUS), Hokkaido (JAP); **not** in Lombardy, Île-de-France or the Home Counties. The build requirements tooltip shows the density and threshold numbers (if blank, file the fallback noted in Task 3).
2. `event te_debug_resettlement.1` → **d**: the `TE_RESETTLEMENT:` line for the capital gives a plausible area (Moscow ~45,000 km², Île-de-France ~12,000) and density.
3. → **a** then **b**: `debug.log` shows `N arrived` equal to the building's *Settlers Moved per Month* (engine question 2); the destination has new pops of the recruited types, still farmers for Special Settlements.
4. After **b**, the destination's culture list includes the arrivals' cultures and immigration of those cultures follows in later months (engine question 1: does `move_partial_pop` create a cultural community?).
5. Special Settlements (needs Collectivized Agriculture + mass_propaganda; use `research mass_propaganda` and the law console): source farmer count falls by died + moved; *Died in transit* matches (question 3).
6. Penal Transportation: the moved pops keep their radical share (question 5); the source's turmoil drops.
7. → **c**: the building is gone, `resettlement.9` fires, no orphaned employees or construction (question 4).
8. The PM switch tooltip shows each PM's description, and the coercive ones show the Declaration line.
9. The building shows *Settlers arrived last month*; each source state shows *Recruited for resettlement last month*; the numbers match the log.
10. After a few months of one program, `resettlement_<program>_politics` shows a fractional effect; twenty levels vs. two buildings do not change it.
11. As a party to the UN Declaration, switching to a coercive program fires `resettlement.20`; *Violating the Declaration* appears; option **b** switches PMs back.
12. Game rule *AI voluntary only*: an AI with a coercive PM is switched to Organized Colonization / Land Grants within a month.
13. Monthly tick time with five Authorities running does not visibly stall the game.
14. (Optional; owner expects it fine) An old save with Resettlement Camps loads; its colonies either run or close with `resettlement.9`.
```

- [ ] **Step 5: Hand over**

Report the checks' results to the owner and invoke `superpowers:finishing-a-development-branch`. Don't push or open a PR without the owner's go-ahead. Record progress in the project memory file `project_internal_resettlement_spec.md` (branch, plan done, PR body path, awaiting in-game checks).
