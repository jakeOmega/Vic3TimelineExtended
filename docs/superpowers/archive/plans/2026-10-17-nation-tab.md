# The Nation Tab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Nation tab, first in the Timeline Extended window and always open, that shows what the country carries for good: four overview boxes, five sections (Governance, Society, Economy, Science and Space, International), each its score rows and then its list of the country's permanent modifiers. The country panel's modifier list hides what the tab shows and the money carriers the Budget panel itemizes. The Colonial Empire tab moves to the second strip beside the Seabed. Part 2, its own PR: the state view's Wealth section lists the state's inheritance modifiers, which the state panel's rows then hide.

**Architecture:** One registry in `scripts/generators/gen_nation_tab.py` places every static modifier script adds without a duration (695 on 2026-10-17, parameterized names expanded from their callers): a section's list, a row's line, kept in the list (an override), or not on the country at all. The money carriers are the budget breakdown's own sources. The generator writes the name filters (`gui/te_nation_generated.gui`), their `has_modifier` counts (`common/script_values/te_nation_generated_values.txt`) and the country panel's Information tab type (`gui/00_te_country_panel_information.gui`), copied from a committed vanilla fixture with three marked blocks. `test_nation_tab.py` fails while any candidate is unplaced, any registry line is dead, any generated file is stale, or a hidden name shares its display name with a kept one. The tab's layout is a hand-written type library (`gui/te_nation_tab.gui`) whose rows read script values (`te_nation_values.txt`) and whose lists are the player's timed modifiers under the generated filters.

**Tech Stack:** Victoria 3 GUI (`.gui`), Paradox script (`common/`), localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md` (§§ 1–5, 7–8). Phase 1 is Tasks 1–7; phase 2 (spec § 5) is Tasks 8–9, a PR of its own once phase 1 has been play-tested. Phase 3 (the Judiciary's rows) and Nuclear Power's move (§ 6) get their own plans.

## Global Constraints

- **The registry is the one list.** A name reaches the country panel's filter, a section's list, a row's line or a count only through `gen_nation_tab.py`. Never hand-edit its three outputs; change the registry and run `python3 scripts/generators/gen_nation_tab.py`.
- **Exactly one registry line per candidate.** An entry may name a family with one `*` (`sr_first_*`, `sr_probe_*_data`), and an exact name wins over a family. The budget breakdown's sources (`gen_budget_breakdown.SOURCES`) are hidden with no row wherever they land and need no line; a line that matches only them is dead.
- **Misplacing a name is engine-silent but harmless:** a country modifier filed as `NOT_ON_COUNTRY` stays in the country's list (as today), and a journal-entry modifier filed in a section never matches the player's timed modifiers. The owner reviews the registry's judgment calls (Review Focus 5); the test enforces completeness, not judgment.
- **The filter matches display names** (`gui_modding_guide.md` gotcha #40): a hidden name must not share its English text with a modifier the list keeps (`test_no_hidden_name_is_shared`). Resolve a clash by keeping the modifier (`KEEP_IN_LIST`) or renaming one of the two in loc.
- **One `visible` per widget** (gotcha #17): a list item's only `visible` is its generated filter; the list container carries `ignoreinvisible = yes`.
- **Files.** Every `.gui` and brace-based `.txt` has exactly one UTF-8 BOM (the generator writes it; `te_nation_tab.gui` and `te_nation_values.txt` need it added). Tabs for indentation. `docs/guides/gui_modding_guide.md` is CRLF: edit it with `Edit` or a script that reads and writes bytes, and confirm `grep -c $'\r$'` equals `wc -l` afterwards. New loc keys go in `te_miscellaneous_l_english.yml`, then `python3 organize_loc.py` (it sorts them into place; commit whatever it moves).
- **Python runs on 3.11:** no PEP 701 f-strings (`grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`).
- **Tests** in a game-less checkout need `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`. Use `.venv/bin/python`; read results with `grep -E '^(Ran |OK|FAILED)'`. Don't edit a checkout while its full suite runs.
- Never `POST /reload` from a worktree. Per task, run its tests and `ruff`; Task 7 runs everything CI runs.
- **Dry run (2026-10-17).** Tasks 1–3 and 8, Task 4's GUI-guide table and Task 5's chapter text, applied to a scratch worktree of `main` at f6d379c with this plan's code, pass the full suite (7,720 tests), `ruff check .`, every `--strict` audit CI runs, `kill_character_audit --check`, `attitude_key_audit`, the tab check, `organize_loc.py --check`, `check_localization_files.py`, `check_post_load_rosters.py`, `check_gui_lint.py` (no errors; its warnings are the vanilla copy's own methods and `states_panel.gui`'s vanilla flag) and the player guide's style lint. The PDF was not rebuilt (no pandoc or Typst there). A replay of this plan's text on a fresh checkout (its files, diffs and scripts, then `organize_loc.py` and the generator) reproduced the tested files byte for byte, all but Task 4's prose edits. The runs found what the steps now cover: the space race's colonies and discoveries, Grand Monuments' boons and the UN's own conventions already sit on their journal entries; the covert operations' effects on a target share a display name with a timed one, so they stay in the list; `test_nightly_audit_select.py` needs the generated files registered; `test_tax_code_bypass.py` needs every new top-level `.gui` in the GUI guide's table; `test_hidden_state_modifiers.py` needs to learn a card's own list.

## Review Focus

1. **The filter hides only what the tab or the Budget panel shows.** No hidden name shares a kept one's display name. Test: Task 1 `test_no_hidden_name_is_shared`, `test_every_carrier_is_hidden`.
2. **The redefined type is vanilla's** but for three `### MOD: Nation tab` blocks that keep each vanilla line they replace, and the fixture is the installed game's file. Test: Task 1 `test_only_marked_blocks_differ_from_vanilla`, `test_the_fixture_is_the_installed_file` (runs on a machine with the game).
3. **Exactly one tab is shown, Nation unless an open system tab was the last choice**, for every combination of open tabs, strips and stored choice, the developer tax tab included. Test: Task 2 `SelectionTest`, `test_tab_selection_is_exclusive_and_stale_debug_choice_falls_back`.
4. **Every permanent modifier is placed once, and no line is dead.** Test: Task 1 `test_every_candidate_is_placed_once`, `test_every_line_places_a_candidate`.
5. **The registry's judgment calls**, for the owner: covert operations' effects on a target stay in the country's list; the monetary bands, the tax code's interest-group views and the colonial programmes go to Economy; the nuclear taboo to International; `gm_name_carrier_slot` (a transient slot while a monument is being named) stays in the list. Each is one line to move.
6. **The launcher has no rule gate** now that Nation is always open. Test: Task 2 `test_the_button_is_on_the_hud_with_no_rule_gate`.

## Files

| File | Task | What |
|---|---|---|
| `scripts/generators/gen_nation_tab.py` | 1 | Create: the registry, the candidate finder, the three outputs |
| `test_fixtures/vanilla_gui/country_panel.gui` | 1 | Create: vanilla's file, byte for byte |
| `gui/te_nation_generated.gui`, `common/script_values/te_nation_generated_values.txt`, `gui/00_te_country_panel_information.gui` | 1 | Generated |
| `test_nation_tab.py` | 1, 3 | Create |
| `scripts/nightly_audit_select.py`, `docs/auto_generated_files.md` | 1 | Modify: the generated files |
| `gui/te_systems_window.gui`, `common/scripted_guis/te_system_tab_sguis.txt` | 2 | Modify: Nation first, the second strip, the selection, the launcher |
| `test_te_systems_window.py`, `test_tax_code_probes.py`, `docs/testing/tax-code-playtest.md` | 2 | Modify |
| `gui/te_nation_tab.gui`, `common/script_values/te_nation_values.txt` | 3 | Create: the tab's types and its rows' values |
| `localization/english/te_miscellaneous_l_english.yml` | 2, 3 | Modify |
| `docs/guides/gui_modding_guide.md` (CRLF), `docs/guides/gui_style_guide.md`, `docs/systems/mod_systems.md`, `docs/guides/vanilla_patch_runbook.md`, `CLAUDE.md` | 4 | Modify |
| `docs/player_guide/01-introduction.md`, `06-politics.md`, `03-economy.md`, the PDF | 5 | Modify, rebuild |
| `docs/testing/nation-tab-playtest.md` | 6 | Create |
| `gui/states_panel.gui`, `common/script_values/gui_chart_script_values.txt`, `gui/te_demographics_widgets.gui`, `test_hidden_state_modifiers.py` | 8 | Modify (phase 2) |

---

### Task 1: The registry, its generator and the country panel's filtered list

**Files:**
- Create: `test_fixtures/vanilla_gui/country_panel.gui`, `scripts/generators/gen_nation_tab.py`, `test_nation_tab.py`
- Generate: `gui/te_nation_generated.gui`, `common/script_values/te_nation_generated_values.txt`, `gui/00_te_country_panel_information.gui`
- Modify: `scripts/nightly_audit_select.py`, `docs/auto_generated_files.md`

**Interfaces:**
- Produces: templates `te_nation_hidden_filter`, `te_nation_list_<section>` (governance, society, economy, science_and_space, international), `te_nation_row_<row>` (algorithmic_mandate, wealth_concentration, construction_cost, private_construction, global_tech); script values `gui_country_hidden_modifier_count`, `te_nation_list_<section>_count`; the redefined type `country_panel_information_content`.
- Consumes: `gen_budget_breakdown.SOURCES`; `paradox_file_parser.ParadoxFileParser`.

- [ ] **Step 1: Commit vanilla's country panel as a fixture**

Copy `<base_game_path>/game/gui/country_panel.gui` (1.14.5, 4,420 lines, no BOM, LF) to `test_fixtures/vanilla_gui/country_panel.gui` unchanged, as `topbar.gui`'s fixture is. Without a game install, the owner's upload of 2026-10-17 is the same file. Check: `grep -n "type country_panel_information_content" test_fixtures/vanilla_gui/country_panel.gui` prints line 379, and `head -c 3` is `# C`, not a BOM.

- [ ] **Step 2: Write the failing tests** (`test_nation_tab.py`)

```python
"""The Nation tab: its registry, the generated filters and counts, and the
country panel's filtered modifier list (spec
docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md §§ 2-4).

What the engine would never report:

- A permanent modifier the registry doesn't place: the country's list keeps it
  and the tab doesn't show it. Every static modifier script adds without a
  duration must match exactly one registry line.
- A generated file older than the registry: the filter hides a name the tab no
  longer shows, or the tab shows one the list still carries.
- A hidden modifier whose display name another modifier on the country shares:
  the filter matches names (gotcha #40), so it would hide both.
- A redefined vanilla type that differs from vanilla outside its marked blocks.

No game install needed; the fixture check skips without one.
"""
import difflib
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.generators import gen_nation_tab as gen  # noqa: E402

LOC_DIR = ROOT / "localization" / "english"


def _read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _loc():
    keys = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


def _names_in(expression):
    return re.findall(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)", expression)


def _template(text, name):
    m = re.search(rf'^template {name} \{{\n\tvisible = "\[(.*)\]"\n\}}', text, re.M)
    assert m, f"no template {name}"
    return m.group(1)


class RegistryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = gen.candidates()
        cls.placed = gen.classify(cls.candidates)

    def test_the_finder_expands_parameters(self):
        # agdiff_$TECH$ from its callers, a two-level demographic line, a milestone's first
        for name in ("agdiff_nitrogen_fixation", "agdiff_green_revolution", "te_demog_line_births_up",
                     "sr_first_moon_landing", "inh_great_fortunes", "un_regime_naval_curb_modifier"):
            self.assertIn(name, self.candidates)
        # timed only: Forceful Legislation's decaying penalty is no candidate
        self.assertNotIn("forced_law_through_event_consequences_small", self.candidates)
        self.assertGreater(len(self.candidates), 600)

    def test_every_candidate_is_placed_once(self):
        unplaced = sorted(name for name, lines in self.placed.items() if not lines)
        self.assertFalse(unplaced, "permanent modifiers with no registry line in "
                                   f"scripts/generators/gen_nation_tab.py: {unplaced}")
        twice = {name: [line[0] for line in lines] for name, lines in self.placed.items() if len(lines) > 1}
        self.assertFalse(twice, f"permanent modifiers two registry lines match (an exact name wins): {twice}")

    def test_every_line_places_a_candidate(self):
        used = {line[:2] for lines in self.placed.values() for line in lines}
        dead = [entry for entry, kind, _ in gen.registry() if (entry, kind) not in used]
        self.assertFalse(dead, f"registry lines that place no permanent modifier (renamed, timed now, "
                               f"or a budget source): {dead}")

    def test_every_carrier_is_hidden(self):
        carriers = gen.budget_carriers() & set(self.candidates)
        self.assertIn("te_demog_pension_bill", carriers)
        _, _, hidden = gen.resolve(self.candidates)
        self.assertLessEqual(carriers, set(hidden))

    def test_rows_and_lists_are_in_the_tabs_sections(self):
        self.assertEqual(list(gen.SECTIONS), ["governance", "society", "economy", "science_and_space",
                                              "international"])
        for row, (section, _) in gen.ROWS.items():
            self.assertIn(section, gen.SECTIONS, row)

    def test_no_hidden_name_is_shared(self):
        """A modifier the list keeps must not share a hidden one's display
        name: the mod's static modifiers that can sit on the country (timed
        ones, the overrides) against every hidden name."""
        loc = _loc()
        statics = gen.static_modifiers()
        _, _, hidden = gen.resolve(self.candidates)
        hidden = set(hidden)
        elsewhere = {name for name, lines in self.placed.items() if lines and lines[0][1] == "elsewhere"}
        kept = set(statics) - hidden - elsewhere
        texts = {}
        for name in kept:
            texts.setdefault(loc.get(name, name), set()).add(name)
        clashes = {name: sorted(texts[loc.get(name, name)]) for name in sorted(hidden)
                   if loc.get(name, name) in texts}
        self.assertFalse(clashes, f"hidden modifiers whose display name a kept one shares: {clashes}")


class GeneratedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = gen.outputs()

    def test_generated_files_are_current(self):
        for path, text in zip((gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT), self.outputs):
            with self.subTest(path=path.name):
                self.assertEqual(_read(path), text, "stale: run python3 scripts/generators/gen_nation_tab.py")

    def test_one_bom_each(self):
        for path in (gen.GUI_OUT, gen.VALUES_OUT, gen.PANEL_OUT):
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_the_filters_and_counts_name_the_same_modifiers(self):
        gui, values, _ = self.outputs
        counts = {}
        for name, body in re.findall(r"^(\w+) = \{\n(.*?)^\}", values, re.S | re.M):
            counts[name] = re.findall(r"has_modifier = (\w+)", body)
        hidden = _names_in(_template(gui, "te_nation_hidden_filter"))
        self.assertEqual(sorted(hidden), sorted(counts["gui_country_hidden_modifier_count"]))
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                listed = _names_in(_template(gui, f"te_nation_list_{section}"))
                self.assertEqual(sorted(listed), sorted(counts[f"te_nation_list_{section}_count"]))
                self.assertLessEqual(set(listed), set(hidden))

    def test_the_filters_stay_shallow(self):
        # A balanced Or tree: depth grows with log2 of the names, not their count.
        gui, _, _ = self.outputs
        for line in gui.splitlines():
            depth = deepest = 0
            for ch in line:
                depth += ch == "("
                depth -= ch == ")"
                deepest = max(deepest, depth)
            self.assertLessEqual(deepest, 16, line[:80])


class CountryPanelTest(unittest.TestCase):
    """gui/00_te_country_panel_information.gui: vanilla's Information tab type,
    its modifier list filtered, every change in a `### MOD: Nation tab` block
    that keeps the vanilla line it replaces."""

    def test_only_marked_blocks_differ_from_vanilla(self):
        vanilla = _read(gen.VANILLA_PANEL).splitlines()
        start = next(i for i, line in enumerate(vanilla) if line.strip().startswith(f"type {gen.PANEL_TYPE} = "))
        mod = _read(gen.PANEL_OUT).splitlines()
        mod_start = next(i for i, line in enumerate(mod) if line.strip().startswith(f"type {gen.PANEL_TYPE} = "))
        mod = mod[mod_start:-1]
        vanilla = vanilla[start:start + len(mod) + 20]
        ops = difflib.SequenceMatcher(None, vanilla, mod, autojunk=False).get_opcodes()
        hunks = [op for op in ops if op[0] != "equal"]
        self.assertEqual(len(hunks), 3 + 1, hunks)    # three blocks, and the tail past the type
        for tag, i1, i2, j1, j2 in hunks[:-1]:
            with self.subTest(line=j1):
                self.assertIn(tag, ("insert", "replace"))
                block = [line.strip() for line in mod[j1:j2]]
                self.assertTrue(block[0].startswith(gen.MOD_OPEN), block)
                self.assertEqual(block[-1], gen.MOD_CLOSE)
                for old in vanilla[i1:i2]:
                    self.assertIn(gen.VANILLA_LINE + old.strip(), block)
        self.assertEqual(hunks[-1][0], "delete")    # vanilla's lines after the type

    def test_the_list_hides_by_name_and_counts_what_is_left(self):
        panel = _read(gen.PANEL_OUT)
        self.assertIn("using = te_nation_hidden_filter", panel)
        self.assertIn("ignoreinvisible = yes", panel)
        self.assertEqual(panel.count("ScriptValue('gui_country_hidden_modifier_count')"), 2)
        self.assertNotIn('visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"',
                         "\n".join(line for line in panel.splitlines() if "# vanilla:" not in line))

    def test_it_defines_the_constants_it_uses(self):
        panel = _read(gen.PANEL_OUT)
        defined = set(re.findall(r"^(@\w+) = ", panel, re.M))
        used = {m for m in re.findall(r"@panel_width\w*", panel)}
        self.assertLessEqual(used, defined)

    def test_the_file_name_loads_first(self):
        # CMF's naming for type redefinitions (gotcha #30)
        self.assertTrue(gen.PANEL_OUT.name.startswith("00_"))


class FixtureTest(unittest.TestCase):
    def test_the_fixture_is_the_installed_file(self):
        base = os.environ.get("VIC3_BASE_GAME")
        if base is None:
            try:
                import path_constants
                base = path_constants.base_game_path
            except Exception:
                base = None
        game = Path(base) / "game" / "gui" / "country_panel.gui" if base else None
        if game is None or not game.is_file():
            self.skipTest("no Victoria 3 install")
        self.assertEqual(gen.VANILLA_PANEL.read_bytes(), game.read_bytes(),
                         "vanilla changed: replace the fixture and run scripts/generators/gen_nation_tab.py")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_nation_tab 2>&1 | grep -E '^(Ran |OK|FAILED)|Error'`
Expected: an `ImportError` (no `scripts.generators.gen_nation_tab`).

- [ ] **Step 4: Write the generator** (`scripts/generators/gen_nation_tab.py`)

```python
"""Generate the Nation tab's name filters and counts.

Spec: docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md § 4.

A candidate is a static modifier the mod defines that script adds somewhere
without a duration (`add_modifier = { name = X }` with no days, months or
years), parameterized names expanded from their callers. The registry below
says where each one lands and where it shows:

- SECTIONS: a Nation section's list; hidden from the country panel's list.
- ROWS: explained by a Nation row ("what it gives now" on its hover); hidden.
- Money carriers, the budget breakdown's sources (gen_budget_breakdown.SOURCES):
  the Budget panel itemizes them; hidden, with no row.
- KEEP_IN_LIST: overrides, kept in the country's list, each with its reason.
- NOT_ON_COUNTRY: lands on a journal entry, a state, a building, an interest
  group, a movement or a power bloc, never on the country.

An entry may name a family with one `*` (`sr_first_*`, `sr_probe_*_data`),
and an exact name wins over a family. test_nation_tab.py holds every candidate to exactly
one entry and every entry to at least one candidate, so a new permanent
modifier fails the suite until it has a line here.

Run after changing the registry:
    python3 scripts/generators/gen_nation_tab.py
It writes gui/te_nation_generated.gui,
common/script_values/te_nation_generated_values.txt and
gui/00_te_country_panel_information.gui (vanilla's Information tab type, copied
from test_fixtures/vanilla_gui/country_panel.gui with the list's filter added);
never hand-edit them. After a vanilla patch, replace the fixture with the new
vanilla file and run this again.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from paradox_file_parser import ParadoxFileParser  # noqa: E402
from scripts.generators.gen_budget_breakdown import SOURCES as BUDGET_SOURCES  # noqa: E402

GUI_OUT = ROOT / "gui" / "te_nation_generated.gui"
VALUES_OUT = ROOT / "common" / "script_values" / "te_nation_generated_values.txt"
PANEL_OUT = ROOT / "gui" / "00_te_country_panel_information.gui"
VANILLA_PANEL = ROOT / "test_fixtures" / "vanilla_gui" / "country_panel.gui"
PANEL_TYPE = "country_panel_information_content"
MOD_OPEN = "### MOD: Nation tab"
MOD_CLOSE = "### END MOD ###"
VANILLA_LINE = "# vanilla: "
HEADER = "AUTO-GENERATED by scripts/generators/gen_nation_tab.py; do not edit manually."

# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

# Section order is the tab's (owner, 2026-10-17). Each list: the permanent
# rewards, memberships and policies the section shows, by system.
SECTIONS = {
    "governance": (
        # The armed forces' standing from training (barracks doctrine)
        "te_officer_academies_standing", "te_political_commissars_indoctrination",
        # Heir education's focus
        "heir_ed_*",
    ),
    "society": (
        # Inheritance: a dynasty's continuity (event outcome)
        "inh_continuity_of_title",
        # Demographic policies: measures, pensions, the health bill, family limitation
        "te_demog_ms_*", "te_demog_pension_pos_*", "te_demog_health_bill_*",
        "te_demog_family_limitation", "te_demog_lx_gap_politics",
        # Living-standard expectations by strata
        "sol_expectations_*",
        # Civil rights strategies
        "cr_*",
        # Resettlement's politics and the declaration's violation
        "resettlement_*_politics", "resettlement_declaration_violation",
    ),
    "economy": (
        # Agricultural diffusion: arable land and yields a farming technology spreads
        "agdiff_*",
        # The private share of construction
        "te_construction_market_private_share_modifier",
        # The tax code: interest groups' views and reactions, relief
        "te_tax_ig_view_*", "te_tax_light_react_*", "te_tax_light_relief_*", "te_tax_relief_*",
        # Monetary arrangements, inflation and exchange rate bands, while the
        # banking cycle's entry isn't running (on the entry otherwise)
        "te_mon_*", "te_inflation_band_*", "te_fx_*", "te_monetary_rate_paid",
        "te_monetisation_minting", "te_capital_controls_fatigue",
        # Colonial programmes (the Colonial Empire entry's policy dials)
        "colonial_cultural_assimilation_modifier", "colonial_development_investment_modifier",
        "colonial_military_garrison_modifier",
    ),
    "science_and_space": (
        # Space race milestones (first and later), the probe's data, the dividend
        "sr_first_*", "sr_suborbital", "sr_orbital", "sr_moon_landing", "sr_moon_base",
        "sr_mars_landing", "sr_interstellar_probe", "sr_probe", "sr_probe_*_data",
        "sr_commercial_space_dividend",
        # Orbital debris and its clearance
        "te_orbital_debris", "te_debris_*",
        # The Antarctic research station and the Antarctic regime
        "te_antarctic_station_modifier", "un_antarctic_*", "un_regime_antarctic_station_modifier",
        # Seabed policy
        "te_seabed_policy_*", "te_seabed_long_haul",
    ),
    "international": (
        # UN conventions a country is bound by outside the organisation's entry
        "un_asat_moratorium_modifier", "un_cultural_diversity_modifier", "un_icc_member_modifier",
        "un_law_of_sea_modifier", "un_narcotics_control_modifier", "un_nuclear_ban_modifier",
        "un_physical_protection_modifier",
        # Membership and its absence, NPT disarmament
        "un_membership_benefits_modifier", "un_nonmember_pariah_*", "un_npt_disarmament_modifier",
        # Regime terms, embargoes, sanctions, mandates, development grants, observers
        "un_regime_*", "un_arms_embargo_*", "un_sanctions_*", "un_mandate_war_support_modifier",
        "un_dev_fund_*", "un_electoral_observers_modifier",
        # Intelligence sharing and the nuclear taboo
        "intelligence_sharing_defense_shield_modifier", "nd_taboo_*",
        # A colonial subject's overlord in decline
        "colonial_overlord_*",
    ),
}

# Each row's modifiers: what the row's score gives now, on its hover.
ROWS = {
    "algorithmic_mandate": ("governance", ("algorithmic_mandate",)),
    "wealth_concentration": ("society", ("inh_great_fortunes", "inh_dispersed_wealth")),
    "construction_cost": ("economy", ("construction_cost_scaling*",)),
    "private_construction": ("economy", ("too_much_private_construction", "overinvestment_modifier")),
    "global_tech": ("science_and_space", ("global_technological_development",)),
}

# Overrides (owner: case by case). Each kept in the country's list.
KEEP_IN_LIST = {
    "nuclear_power": "spec § 6: moves to the Nuclear Program entry later; the list shows it until then",
    "covert_*": "a foreign operation's effect, while it runs: the list is where a player looks for what is "
                "being done to them, and covert_destabilization_resist shares its name with the timed "
                "covert_destabilization_general",
    "gm_name_carrier_slot": "transient: while a monument's naming box is open",
    "cheaty": "debug",
    "ch_debug_funding_cap": "debug",
    "nuclear_program_debug_pause": "debug",
    "te_debug_*": "debug",
    "te_tp_*": "debug (the developer-only tax probes)",
    "te_demog_fast_*": "debug (the fast demographic clock)",
}

# Where the rest land. Hiding them would cost the filter a comparison each and
# change nothing.
NOT_ON_COUNTRY = {
    "banking_*": "je_banking_cycle", "bubble_inertia_*": "je_banking_cycle",
    "financial_cycle_*": "je_banking_cycle", "cooperative_*": "je_banking_cycle",
    "planning_*": "je_banking_cycle",
    "carbon_removal_modifier": "je_global_warming", "carbon_tax_modifier": "je_global_warming",
    "climate_adaptation_modifier": "je_global_warming", "emission_standards_modifier": "je_global_warming",
    "fossil_fuel_*": "je_global_warming", "green_building_codes_modifier": "je_global_warming",
    "public_transit_modifier": "je_global_warming", "reforestation_subsidies_modifier": "je_global_warming",
    "renewable_investment_modifier": "je_global_warming", "global_warming": "je_global_warming",
    "ch_cultural_*": "je_cultural_hegemony", "ch_global_media_campaign": "je_cultural_hegemony",
    "ch_world_exposition": "je_cultural_hegemony", "cultural_hegemony_*": "je_cultural_hegemony",
    "civil_rights_phase_*": "je_civil_rights",
    "colonial_empire_*": "je_colonial_empire",
    "colonial_crumbling_movement_radicalism": "political movements",
    "colonial_pressure_movement_radicalism": "political movements",
    "intelligence_capacity_defense": "je_covert_warfare",
    "iw_*": "je_covert_warfare",
    "gm_*": "je_grand_monuments, a monument's state or building",
    "nd_doctrine_*": "je_nuclear_program", "nd_readiness_*": "je_nuclear_program",
    "nuclear_weapon_program_funding": "je_nuclear_program",
    "nd_posture_*": "interest groups",
    "sr_colony_*": "je_space_race_solar_colonization", "sr_discovery_*": "je_space_race_solar_colonization",
    "sr_solar_system_trade": "je_space_race_solar_colonization",
    "sr_funding_progress": "the running milestone's entry", "sr_space_program_cost": "the running milestone's entry",
    "un_bloc_vacuum_modifier": "power blocs", "un_sovereignty_*": "interest groups",
    "un_standing_*": "je_united_nations", "un_member_*": "je_united_nations",
    "un_founding_member_modifier": "je_united_nations", "un_headquarters_modifier": "je_united_nations",
    "un_permanent_member_modifier": "je_united_nations", "un_security_council_modifier": "je_united_nations",
    "un_climate_binding_modifier": "je_united_nations", "un_heritage_program_modifier": "je_united_nations",
    "un_nonproliferation_modifier": "je_united_nations", "un_pandemic_cooperation_modifier": "je_united_nations",
    "un_refugee_program_modifier": "je_united_nations", "un_space_partnership_modifier": "je_united_nations",
    "un_human_rights_*": "je_united_nations", "un_peacekeeping_contributor_modifier": "je_united_nations",
    "un_development_*_modifier": "je_united_nations", "un_arms_control_participant_modifier": "je_united_nations",
    "un_champion_order_cost": "je_united_nations", "un_undermine_order_cost": "je_united_nations",
    "un_food_reserve_relief_state_modifier": "states", "un_mission_*_state_modifier": "states",
    "ww_*": "je_world_war",
    "antimatter_facility_progress": "the megaproject's building",
    "consciousness_network_progress": "the megaproject's building",
    "mind_upload_nexus_progress": "the megaproject's building",
    "nanofabrication_center_progress": "the megaproject's building",
    "orbital_battlestation_progress": "the megaproject's building",
    "solar_collector_progress": "the megaproject's building",
    "space_elevator_progress": "the megaproject's building",
    "demilitarized_zone_state_modifier": "states", "free_port_*": "states", "migration_crowding": "states",
    "minority_protection_state_modifier": "states", "pollution_generation_mult_effect": "states",
    "religious_mission_state_modifier": "states", "tourism_*": "states",
    "inh_concentrated_property": "states", "inh_dispersed_property": "states", "inh_land_hunger": "states",
    "inh_forced_heirship_rural": "states", "inh_primogeniture_rural": "states",
    "inh_undivided_farm_rural": "states",
    "te_demog_census_*": "states", "te_demog_line_*": "states", "te_demog_lx_gap_labor": "states",
    "te_demog_primate_city": "states", "te_demog_provincial_neglect": "states",
    "te_reserve_cadre_*": "states",
    "resettlement_*_destination": "states", "resettlement_arrivals": "the destination's buildings",
    "resettlement_transit_deaths": "the destination's buildings", "resettlement_recruits": "states",
    "st_res_*_flow": "the reserve hub's building",
    "te_construction_market_capacity_modifier": "construction sites",
}


# ---------------------------------------------------------------------------
# Candidates: every static modifier script adds without a duration
# ---------------------------------------------------------------------------

_STRING_OR_COMMENT = re.compile(r'"[^"\n]*"|#[^\n]*')
_OPENER = re.compile(r"([\w.:@$-]+)\s*\??=\s*\{|\{|\}")
_ADD = re.compile(r"\badd_modifier\s*=\s*\{")
_NAME = re.compile(r"\bname\s*=\s*([\w$]+)")
_DURATION = re.compile(r"\b(?:days|weeks|months|years)\s*=")
_CALL = re.compile(r"\b(\w+)\s*=\s*\{([^{}]*)\}")
_ARG = re.compile(r"\b([A-Z][A-Z0-9_]*)\s*=\s*([\w$.:]+)")
_PARAM = re.compile(r"\$([A-Z][A-Z0-9_]*)\$")


def _strip_comments(text):
    """Comments blanked; a `#` inside a quoted string is kept."""
    return _STRING_OR_COMMENT.sub(lambda m: m.group(0) if m.group(0)[0] == '"' else "", text)


def _block_end(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


def _top_level(text):
    """[(name, start, end)] of the file's top-level `name = { ... }` blocks."""
    out, depth = [], 0
    for m in _OPENER.finditer(text):
        token = m.group(0)
        if token == "}":
            depth -= 1
        else:
            if depth == 0 and m.group(1):
                out.append((m.group(1), m.start(), _block_end(text, m.end() - 1)))
            depth += 1
    return out


def _enclosing(tops, pos):
    return next((name for name, start, end in tops if start <= pos <= end), None)


class _Script:
    """Every script file under common/ and events/, read once."""

    def __init__(self, root=ROOT):
        self.files = {}
        for sub in ("common", "events"):
            for path in sorted((root / sub).rglob("*.txt")):
                text = _strip_comments(path.read_text(encoding="utf-8-sig"))
                self.files[path.relative_to(root).as_posix()] = (text, _top_level(text))
        # Calls with flat arguments, by callee: [(args, the caller's top-level block)]
        self.calls = {}
        for text, tops in self.files.values():
            for m in _CALL.finditer(text):
                args = dict(_ARG.findall(m.group(2)))
                if args:
                    self.calls.setdefault(m.group(1), []).append((args, _enclosing(tops, m.start())))

    def add_sites(self):
        """[(name template, timed, file, the top-level block it sits in)]."""
        sites = []
        for rel, (text, tops) in self.files.items():
            for m in _ADD.finditer(text):
                body = text[m.end():_block_end(text, m.end() - 1)]
                name = _NAME.search(body)
                if name:
                    sites.append((name.group(1), bool(_DURATION.search(body)), rel, _enclosing(tops, m.start())))
        return sites

    def expand(self, template, effect, depth=0):
        """The names a `$PARAM$` template takes, from the calls of the
        scripted effect it sits in (and theirs, up to four levels)."""
        params = _PARAM.findall(template)
        if not params:
            return {template}
        if depth > 3 or not effect:
            return set()
        names = set()
        for args, caller in self.calls.get(effect, ()):
            name = template
            for param in params:
                if param in args:
                    name = name.replace(f"${param}$", args[param])
            names |= self.expand(name, caller, depth + 1) if "$" in name else {name}
        return names


def static_modifiers(root=ROOT):
    """{name: {field: value}} for every static modifier the mod defines."""
    found = {}
    for path in sorted((root / "common" / "static_modifiers").glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for key, value in parser.data.items():
            block = value[1] if isinstance(value, tuple) else value
            if isinstance(block, dict):
                found[key.split(":")[-1]] = block
    return found


def candidates(root=ROOT):
    """{name: sorted files} for every mod static modifier script adds without a duration."""
    script = _Script(root)
    statics = static_modifiers(root)
    found = {}
    for template, timed, rel, top in script.add_sites():
        if timed:
            continue
        for name in script.expand(template, top):
            if name in statics:
                found.setdefault(name, set()).add(rel)
    return {name: sorted(files) for name, files in sorted(found.items())}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def budget_carriers():
    return {name for side in BUDGET_SOURCES.values() for _, names in side.values() for name in names}


def _matches(entry, name):
    if "*" not in entry:
        return name == entry
    head, tail = entry.split("*", 1)
    return name.startswith(head) and name.endswith(tail) and len(name) >= len(head) + len(tail)


def registry():
    """[(entry, kind, detail)] for every line of the registry."""
    out = []
    for section, entries in SECTIONS.items():
        out += [(entry, "section", section) for entry in entries]
    for row, (section, entries) in ROWS.items():
        out += [(entry, "row", row) for entry in entries]
    out += [(entry, "keep", reason) for entry, reason in KEEP_IN_LIST.items()]
    out += [(entry, "elsewhere", where) for entry, where in NOT_ON_COUNTRY.items()]
    return out


def classify(names):
    """{name: [(entry, kind, detail)]}: the registry lines each name matches.
    A budget carrier matches as ("budget", "budget", side) and nothing else."""
    carriers = budget_carriers()
    lines = registry()
    out = {}
    for name in names:
        if name in carriers:
            out[name] = [(name, "budget", "the Budget panel")]
        else:
            matched = [line for line in lines if _matches(line[0], name)]
            exact = [line for line in matched if line[0] == name]
            out[name] = exact or matched
    return out


def resolve(cands):
    """The exact names for each list, row and the hidden set, from candidates
    that match exactly one registry line."""
    classified = classify(cands)
    lists = {section: [] for section in SECTIONS}
    rows = {row: [] for row in ROWS}
    hidden = []
    for name, lines in sorted(classified.items()):
        if len(lines) != 1:
            continue
        _, kind, detail = lines[0]
        if kind == "section":
            lists[detail].append(name)
        elif kind == "row":
            rows[detail].append(name)
        if kind in ("section", "row", "budget"):
            hidden.append(name)
    return lists, rows, hidden


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _any_of(names):
    """A balanced Or tree of name tests, so the nesting stays shallow (about
    log2 of the count) however long the list grows."""
    if len(names) == 1:
        return f"EqualTo_string(TimedModifier.GetName, Localize('{names[0]}'))"
    mid = len(names) // 2
    return f"Or({_any_of(names[:mid])}, {_any_of(names[mid:])})"


def generated_gui(lists, rows, hidden):
    parts = [
        f"### {HEADER}",
        "### The Nation tab's name filters (gui_modding_guide.md gotcha #40): a timed",
        "### modifier is picked out by its localized name, in any language.",
        "",
        "### The country panel's modifier list leaves these out (gui/00_te_country_panel_information.gui).",
        "template te_nation_hidden_filter {",
        f'\tvisible = "[Not({_any_of(hidden)})]"',
        "}",
    ]
    for section, names in lists.items():
        if names:
            parts += ["", f"### The {section} section's list.", f"template te_nation_list_{section} {{",
                      f'\tvisible = "[{_any_of(names)}]"', "}"]
    for row, names in rows.items():
        if names:
            parts += ["", f"### What the {row} row's score gives now.", f"template te_nation_row_{row} {{",
                      f'\tvisible = "[{_any_of(names)}]"', "}"]
    return "\n".join(parts) + "\n"


def _count(name, names, used_by):
    lines = [f"# Used by: {used_by}", f"{name} = {{", "\tvalue = 0"]
    for modifier in names:
        lines += ["\tif = {", f"\t\tlimit = {{ has_modifier = {modifier} }}", "\t\tadd = 1", "\t}"]
    return lines + ["}"]


def generated_values(lists, rows, hidden):
    parts = [f"# {HEADER}", "# Country scope: how many of the country's modifiers each Nation filter matches.", ""]
    parts += _count("gui_country_hidden_modifier_count", hidden,
                    "Country.MakeScope.ScriptValue('gui_country_hidden_modifier_count') (the country panel's list)")
    for section, names in lists.items():
        if names:
            parts += [""] + _count(f"te_nation_list_{section}_count", names,
                                   f"the Nation tab's {section} list (gui/te_nation_tab.gui)")
    return "\n".join(parts) + "\n"


_EMPTY = 'visible = "[Not(IsDataModelEmpty(Country.GetTimedModifiers))]"'
_SHOWN = ("visible = \"[GreaterThan_int32(GetDataModelSize(Country.GetTimedModifiers), "
          "FixedPointToInt(Country.MakeScope.ScriptValue('gui_country_hidden_modifier_count')))]\"")


def _mod_block(indent, why, vanilla, new):
    lines = [f"{indent}{MOD_OPEN}: {why}"]
    lines += [f"{indent}{VANILLA_LINE}{line.strip()}" for line in vanilla]
    return lines + [f"{indent}{line}" for line in new] + [f"{indent}{MOD_CLOSE}"]


def generated_panel(vanilla_text=None):
    """Vanilla's country_panel_information_content with its modifier list
    filtered: the header and the list shown while a modifier the Nation tab
    doesn't show is left, the items the tab shows hidden
    (te_nation_hidden_filter), and the list ignoring the hidden ones. Raises
    if vanilla moved a line the filter hooks onto."""
    text = VANILLA_PANEL.read_text(encoding="utf-8-sig") if vanilla_text is None else vanilla_text
    lines = text.splitlines()
    head = [line for line in lines if re.match(r"@panel_width\w* = ", line)]
    start = next(i for i, line in enumerate(lines) if line.strip().startswith(f"type {PANEL_TYPE} = "))
    depth, end = 0, None
    for i in range(start, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if depth == 0:
            end = i
            break
    body = lines[start:end + 1]
    timed = next(i for i, line in enumerate(body) if line.strip() == "### TIMED MODIFIERS")
    out, empties, item = body[:timed], 0, False
    for line in body[timed:]:
        indent = line[:len(line) - len(line.lstrip())]
        if line.strip() == _EMPTY:
            empties += 1
            new = [_SHOWN] + (["ignoreinvisible = yes"] if empties == 2 else [])
            why = ("the header shows while a modifier the Nation tab doesn't show is left" if empties == 1
                   else "the list skips what the Nation tab shows")
            out += _mod_block(indent, why, [line], new)
        elif line.strip() == "item = {":
            item = True
            out.append(line)
        elif item and line.strip() == "container = {":
            item = False
            out.append(line)
            out += _mod_block(indent + "\t", "hidden while the Nation tab shows it (gui/te_nation_generated.gui)",
                              [], ["using = te_nation_hidden_filter"])
        else:
            out.append(line)
    if empties != 2 or item or not any("te_nation_hidden_filter" in line for line in out):
        raise ValueError(f"vanilla's {PANEL_TYPE} moved its modifier list: update generated_panel()")
    parts = [
        f"### {HEADER}",
        f"### Vanilla's {PANEL_TYPE} (gui/country_panel.gui, the country panel's Information",
        "### tab), redefined from this file (gui_modding_guide.md gotcha #30). Copied from",
        "### test_fixtures/vanilla_gui/country_panel.gui; only the `### MOD: Nation tab` blocks differ.",
        "",
    ] + head + ["", "types te_country_panel_information", "{"] + out + ["}"]
    return "\n".join(parts) + "\n"


def outputs():
    lists, rows, hidden = resolve(candidates())
    return generated_gui(lists, rows, hidden), generated_values(lists, rows, hidden), generated_panel()


def main():
    gui, values, panel = outputs()
    for path, text in ((GUI_OUT, gui), (VALUES_OUT, values), (PANEL_OUT, panel)):
        path.write_text("\ufeff" + text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Generate, and run the tests**

Run: `.venv/bin/python scripts/generators/gen_nation_tab.py && .venv/bin/python -m unittest test_nation_tab 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: `OK (skipped=1)` (the fixture check skips without a game). On 2026-10-17: 695 candidates; 233 hidden (205 in the lists, 8 under rows, 20 carriers); 42 kept; 420 elsewhere; lists of 5, 38, 92, 29 and 41. If `main` has moved, a new permanent modifier fails `test_every_candidate_is_placed_once` with its name: give it a line, by where it lands (Review Focus 5's rules), and regenerate.

Check the override: `diff <(sed -n 379,1411p test_fixtures/vanilla_gui/country_panel.gui) <(sed '1,/^{$/d' gui/00_te_country_panel_information.gui | sed '$d')` shows exactly the three `### MOD: Nation tab` blocks.

- [ ] **Step 6: Register the generated files**

`scripts/nightly_audit_select.py` (the nightly audit never samples a generated file; `test_nightly_audit_select.py` fails until they are listed):

```diff
diff --git a/scripts/nightly_audit_select.py b/scripts/nightly_audit_select.py
index 1736ea6..91e5e13 100755
--- a/scripts/nightly_audit_select.py
+++ b/scripts/nightly_audit_select.py
@@ -93,6 +93,9 @@ EXCLUDED_REGISTRY_GLOBS = [
     "common/script_values/te_budget_generated_values.txt",
     "common/modifier_type_definitions/te_budget_generated_types.txt",
     "gui/te_budget_generated_charts.gui",
+    "common/script_values/te_nation_generated_values.txt",
+    "gui/te_nation_generated.gui",
+    "gui/00_te_country_panel_information.gui",
     "common/scripted_triggers/te_tax_generated_triggers.txt",
     "common/customizable_localization/te_tax_generated_custom_loc.txt",
     "common/scripted_guis/te_tax_generated_sguis.txt",
```

`docs/auto_generated_files.md`, after the Budget display section:

```diff
diff --git a/docs/auto_generated_files.md b/docs/auto_generated_files.md
index b7222ab..757fdb1 100644
--- a/docs/auto_generated_files.md
+++ b/docs/auto_generated_files.md
@@ -61,6 +61,22 @@ institution and modifier-type snapshots and mod definitions, and writes:
 This generator runs explicitly; it is not a post-load regenerator. The localization
 organizer preserves its BUDGET family and output format.
 
+## Nation tab (explicit regeneration)
+
+Run `python3 scripts/generators/gen_nation_tab.py` after changing its registry
+(`SECTIONS`, `ROWS`, `KEEP_IN_LIST`, `NOT_ON_COUNTRY`), the budget catalogue
+above (its sources are hidden from the country panel's list), or vanilla's
+`country_panel.gui` fixture. `test_nation_tab.py` fails while a permanent
+country modifier has no registry line or a file below is stale. It writes:
+
+| File | Owner script | Input |
+|---|---|---|
+| `gui/te_nation_generated.gui` | `scripts/generators/gen_nation_tab.py` | The registry, resolved against every static modifier script adds without a duration: the country panel's filter and the tab's list and row filters |
+| `common/script_values/te_nation_generated_values.txt` | `scripts/generators/gen_nation_tab.py` | The same names, as `has_modifier` counts (`gui_country_hidden_modifier_count`, `te_nation_list_<section>_count`) |
+| `gui/00_te_country_panel_information.gui` | `scripts/generators/gen_nation_tab.py` | `test_fixtures/vanilla_gui/country_panel.gui` (vanilla, byte for byte): its `country_panel_information_content` type with three `### MOD: Nation tab` blocks |
+
+This generator runs explicitly; it is not a post-load regenerator.
+
 ## Tooling data
 
 | File / glob | Owner script | Input | Notes |
```

- [ ] **Step 7: Check and commit**

Run: `.venv/bin/python -m unittest test_nation_tab test_nightly_audit_select test_budget_breakdown 2>&1 | grep -E '^(Ran |OK|FAILED)'` (OK), `.venv/bin/ruff check scripts/generators/gen_nation_tab.py test_nation_tab.py`, and the 3.11 f-string scan on both.

```bash
git add test_fixtures/vanilla_gui/country_panel.gui scripts/generators/gen_nation_tab.py test_nation_tab.py \
  gui/te_nation_generated.gui common/script_values/te_nation_generated_values.txt \
  gui/00_te_country_panel_information.gui scripts/nightly_audit_select.py docs/auto_generated_files.md
git commit -m "Nation tab: the registry of permanent country modifiers and the country panel's filtered list"
```

---

### Task 2: The Timeline Extended window: Nation first, the Colonial Empire on the second strip

**Files:**
- Modify: `gui/te_systems_window.gui`, `common/scripted_guis/te_system_tab_sguis.txt`, `localization/english/te_miscellaneous_l_english.yml`, `test_te_systems_window.py`, `test_tax_code_probes.py`, `docs/testing/tax-code-playtest.md`

**Interfaces:**
- Produces: templates `te_systems_window_nation_selected` / `_unselected`; the tab key `nation` in `te_systems_window_tab`; the strip `te_systems_window_second_strip` (renamed from `te_systems_window_seabed_strip`); the content block `te_systems_window_nation_tab`, which instances `te_nation_tab_sections` (Task 3). Removes `te_systems_window_none_open`, its textbox and loc key `te_systems_window_none`, and `te_window_launcher_sgui`.

The selection rule, with T the developer tax tab chosen and armed, and V "a system tab last chosen is open":

| Tab | Selected | Unselected half |
|---|---|---|
| Nation | not T and not V | T or V |
| a system tab t | not T and S_t and U_t | R_t and not selected |

- [ ] **Step 1: Update the tests**

`test_te_systems_window.py`:

```diff
diff --git a/test_te_systems_window.py b/test_te_systems_window.py
index 1c3f14e..849a480 100644
--- a/test_te_systems_window.py
+++ b/test_te_systems_window.py
@@ -1,7 +1,7 @@
 """The Timeline Extended window (gui/te_systems_window.gui): the mod's own
-window for the systems with no vanilla home, a tab each for the Space Race, the
-Colonial Empire and Grand Monuments, and the Seabed (Global Commons) on a strip
-of its own, opened from a button under the sidebar
+window. The first strip: Nation (always open), the Space Race and Grand
+Monuments; the second: the Colonial Empire and the Seabed (Global Commons).
+Opened from a button under the sidebar
 (docs/systems/system_panels_feasibility.md §3.1, §3.5, §3.6; style guide rule 9).
 
 These tests hold the registration to the file, the launcher's and the window's
@@ -24,20 +24,21 @@ WIDGETS = os.path.join(REPO, "gui", "journal_entry_widgets")
 LOC_DIR = os.path.join(REPO, "localization", "english")
 ICON_DOC = os.path.join(REPO, "docs", "systems", "te_systems_window_gui_icons.md")
 
-# (tab key, the rule its gates read, its slot on the strip)
-TABS = [("space_race", "has_game_rule = space_race_enabled", "first"),
-        ("colonial_empire", "has_game_rule = decolonization_enabled", "second"),
+# The system tabs: (tab key, the rule its gates read, its slot on its strip).
+# The first strip: Nation (always open, no rule), then these two.
+TABS = [("space_race", "has_game_rule = space_race_enabled", "second"),
         ("grand_monuments", "gm_system_enabled = yes", "third")]
-# The Seabed tab: the first slot of a strip of its own under the three, so
-# their full names keep their width (a fourth on one strip leaves 115 each).
-SEABED = ("seabed", "te_global_commons_enabled = yes", "first")
-SEABED_STRIP = "te_systems_window_seabed_strip"
-ALL_TABS = TABS + [SEABED]
+# The second strip, so the first's full names keep their width (a fourth on
+# one strip leaves 115 each).
+SECOND = [("colonial_empire", "has_game_rule = decolonization_enabled", "first"),
+          ("seabed", "te_global_commons_enabled = yes", "second")]
+SECOND_STRIP = "te_systems_window_second_strip"
+ALL_TABS = TABS + SECOND
 SR = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
       "interstellar_probe", "interstellar_results", "solar_colonization"]   # je_space_race.txt order
 # The systems' full names, and the width a tab's name gets: three tabs share
 # about 540, less tab_text_properties' 10 px margin each side (no icon).
-FULL_NAMES = {"space_race": "Space Race", "colonial_empire": "Colonial Empire",
+FULL_NAMES = {"nation": "Nation", "space_race": "Space Race", "colonial_empire": "Colonial Empire",
               "grand_monuments": "Grand Monuments", "seabed": "Seabed"}
 NAME_WIDTH = 540 / 3 - 2 * 10
 # Tab labels are budgeted at the medium rate, 8.6 units a character plus 10%,
@@ -180,8 +181,8 @@ class RegistrationTest(unittest.TestCase):
 
 
 class LauncherTest(unittest.TestCase):
-    """The button under Map List: for a played country, on the HUD, while any
-    of the three systems' rules is on."""
+    """The button under Map List: for a played country, on the HUD. No rule
+    gates it: the Nation tab is always open."""
 
     @classmethod
     def setUpClass(cls):
@@ -195,15 +196,12 @@ class LauncherTest(unittest.TestCase):
         self.assertIn("position = { 0 825 }", head)
         self.assertIn("size = { 42 40 }", head)
 
-    def test_the_button_is_on_the_hud_and_gated_on_the_rules(self):
+    def test_the_button_is_on_the_hud_with_no_rule_gate(self):
         hud = self.root.index("using = hud_visibility")
         button = _named(self.gui, "te_systems_window_launcher_button")
         self.assertLess(hud, self.root.index(button))
-        self.assertIn(f'visible = "[{_gate("te_window_launcher_sgui")}]"', button)
-        sgui = _txt_block(_read(TAB_SGUIS), "te_window_launcher_sgui")
-        for _, rule, _ in ALL_TABS:
-            self.assertIn(rule, sgui)
-        self.assertIn("OR = {", sgui)
+        self.assertNotIn("te_window_launcher_sgui", self.gui)
+        self.assertNotIn("te_window_launcher_sgui", _read(TAB_SGUIS))
 
     def test_it_opens_and_closes_the_window(self):
         button = _named(self.gui, "te_systems_window_launcher_button")
@@ -324,15 +322,16 @@ class WindowTest(unittest.TestCase):
 
 
 class SelectionTest(unittest.TestCase):
-    """The tab shown: the last one chosen while it is open, otherwise the first
-    open one. Every combination of open tabs and stored choice."""
+    """The tab shown: the last one chosen while it is open, otherwise Nation,
+    which always is. Every combination of open tabs and stored choice."""
 
     @classmethod
     def setUpClass(cls):
         gui = _read(GUI)
-        cls.sel = {t: _template(gui, f"te_systems_window_{t}_selected") for t, _, _ in ALL_TABS}
-        cls.unsel = {t: _template(gui, f"te_systems_window_{t}_unselected") for t, _, _ in ALL_TABS}
-        cls.none = _template(gui, "te_systems_window_none_open")
+        tabs = ["nation"] + [t for t, _, _ in ALL_TABS]
+        cls.sel = {t: _template(gui, f"te_systems_window_{t}_selected") for t in tabs}
+        cls.unsel = {t: _template(gui, f"te_systems_window_{t}_unselected") for t in tabs}
+        cls.gui = gui
 
     def _cases(self):
         order = [t for t, _, _ in ALL_TABS]
@@ -340,31 +339,31 @@ class SelectionTest(unittest.TestCase):
             for on_strip in itertools.product([False, True], repeat=len(order)):
                 if any(o and not s for o, s in zip(opened, on_strip)):
                     continue    # a tab opens only while its rule is on
-                for stored in [None] + order:
+                for stored in [None, "nation"] + order:
                     shown = {f"te_window_{t}_tab_sgui" for t, o in zip(order, opened) if o}
                     shown |= {f"te_window_{t}_tab_unlock_sgui" for t, s in zip(order, on_strip) if s}
                     yield dict(zip(order, opened)), dict(zip(order, on_strip)), stored, shown
 
     def test_exactly_the_right_tab_is_shown(self):
-        order = [t for t, _, _ in ALL_TABS]
         for opened, _, stored, shown in self._cases():
-            if stored and opened[stored]:
-                expected = stored
-            else:
-                expected = next((t for t in order if opened[t]), None)
-            for t in order:
+            expected = stored if stored in opened and opened[stored] else "nation"
+            for t in self.sel:
                 with self.subTest(opened=opened, stored=stored, tab=t):
                     self.assertEqual(_evaluate(self.sel[t], shown, stored), t == expected)
-            self.assertEqual(_evaluate(self.none, shown, stored), expected is None)
 
     def test_a_tab_on_the_strip_shows_one_half(self):
         for opened, on_strip, stored, shown in self._cases():
-            for t in opened:
+            for t in self.sel:
                 with self.subTest(opened=opened, on_strip=on_strip, stored=stored, tab=t):
                     selected = _evaluate(self.sel[t], shown, stored)
                     unselected = _evaluate(self.unsel[t], shown, stored)
                     self.assertFalse(selected and unselected)
-                    self.assertEqual(selected or unselected, on_strip[t])
+                    # Nation is always on the strip
+                    self.assertEqual(selected or unselected, t == "nation" or on_strip[t])
+
+    def test_nothing_is_left_for_an_empty_window(self):
+        self.assertNotIn("te_systems_window_none_open", self.gui)
+        self.assertNotIn("te_systems_window_none", _all_loc())
 
 
 class StripTest(unittest.TestCase):
@@ -384,9 +383,9 @@ class StripTest(unittest.TestCase):
         return text[m.end():_close(text, m.end() - 1)]
 
     def test_each_tab_is_greyed_until_open_and_stores_the_choice(self):
-        seabed_strip = _named(self.gui, SEABED_STRIP)
+        second = _named(self.gui, SECOND_STRIP)
         for tab, _, slot in ALL_TABS:
-            within = seabed_strip if tab == "seabed" else None
+            within = second if (tab, _, slot) in SECOND else None
             with self.subTest(tab=tab):
                 click = self._override(f"{slot}_button_click", within)
                 self.assertIn(f'enabled = "[{_gate(f"te_window_{tab}_tab_sgui")}]"', click)
@@ -402,12 +401,25 @@ class StripTest(unittest.TestCase):
                 for half in (f"{slot}_button", f"{slot}_button_selected"):
                     self.assertIn(f'text = "te_window_tab_{tab}"', self._override(half, within))
 
-    def test_the_seabed_strip_is_up_while_the_rule_is_on(self):
-        strip = _named(self.gui, SEABED_STRIP)
-        self.assertIn(f'visible = "[{_gate("te_window_seabed_tab_unlock_sgui")}]"', strip.split("\n\n")[0])
-        # under the three-tab strip, above the developer strip
-        self.assertLess(self.panel.index('blockoverride "third_button_selected"'), self.panel.index(SEABED_STRIP))
-        self.assertLess(self.panel.index(SEABED_STRIP), self.panel.index("te_tp_tab_sgui"))
+    def test_nation_is_first_and_always_open(self):
+        first = self.panel[self.panel.index("tab_buttons = {"):self.panel.index(SECOND_STRIP)]
+        self.assertLess(first.index('blockoverride "first_button" {\n\t\t\t\t\t\ttext = "te_window_tab_nation"'),
+                        first.index('text = "te_window_tab_space_race"'))
+        click = self._override("first_button_click", first)
+        self.assertNotIn("enabled =", click)
+        self.assertIn("onclick = \"[GetVariableSystem.Set('te_systems_window_tab', 'nation')]\"", click)
+        self.assertIn('tooltip = "te_window_tab_nation_tt"', self._override("first_button_tooltip", first))
+        self.assertIn("using = te_systems_window_nation_selected", self._override("first_button_visibility", first))
+        self.assertIn("using = te_systems_window_nation_unselected",
+                      self._override("first_button_visibility_checked", first))
+
+    def test_the_second_strip_is_up_while_either_rule_is_on(self):
+        strip = _named(self.gui, SECOND_STRIP)
+        gates = ", ".join(_gate(f"te_window_{t}_tab_unlock_sgui") for t, _, _ in SECOND)
+        self.assertIn(f'visible = "[Or( {gates} )]"', strip.split("\n\n")[0])
+        # under the first strip, above the developer strip
+        self.assertLess(self.panel.index('blockoverride "third_button_selected"'), self.panel.index(SECOND_STRIP))
+        self.assertLess(self.panel.index(SECOND_STRIP), self.panel.index("te_tp_tab_sgui"))
 
     def test_the_gates_read_the_rule_and_the_entries(self):
         for tab, rule, _ in ALL_TABS:
@@ -639,10 +651,14 @@ class SeabedTabTest(unittest.TestCase):
         with open(os.path.join(REPO, "gui", "te_seabed_widgets.gui"), "rb") as f:
             self.assertEqual(f.read(3), b"\xef\xbb\xbf")
 
-    def test_the_tabs_order_after_the_monuments(self):
+    def test_the_tabs_content_in_the_strips_order(self):
         gui = _read(GUI)
-        self.assertLess(gui.index('name = "te_systems_window_grand_monuments_tab"'),
-                        gui.index('name = "te_systems_window_seabed_tab"'))
+        at = [gui.index(f'name = "te_systems_window_{t}_tab"')
+              for t in ("nation", "space_race", "grand_monuments", "colonial_empire", "seabed")]
+        self.assertEqual(at, sorted(at))
+        nation = _named(gui, "te_systems_window_nation_tab")
+        self.assertIn("using = te_systems_window_nation_selected", nation.split("\n\n")[0])
+        self.assertIn("te_nation_tab_sections = {}", nation)
 
 
 class LocTest(unittest.TestCase):
```

`test_tax_code_probes.py`:

```diff
diff --git a/test_tax_code_probes.py b/test_tax_code_probes.py
index 9b7fb89..32ab2d1 100644
--- a/test_tax_code_probes.py
+++ b/test_tax_code_probes.py
@@ -45,12 +45,11 @@ class TaxProbeSafetyTest(unittest.TestCase):
             if ".Execute(" in line:
                 self.assertIn("onclick =", line)
 
-    def test_four_tab_selection_is_exclusive_and_stale_debug_choice_falls_back(self):
+    def test_tab_selection_is_exclusive_and_stale_debug_choice_falls_back(self):
         gui = read("gui/te_systems_window.gui")
         normal = ["space_race", "colonial_empire", "grand_monuments"]
-        names = normal + ["tax_probes"]
+        names = ["nation"] + normal + ["tax_probes"]
         expressions = {n: _template(gui, f"te_systems_window_{n}_selected") for n in names}
-        empty = _template(gui, "te_systems_window_none_open")
         for mask in itertools.product((False, True), repeat=4):
             shown = {f"te_window_{n}_tab_sgui" for n, yes in zip(normal, mask[:3]) if yes}
             if mask[3]:
@@ -62,9 +61,8 @@ class TaxProbeSafetyTest(unittest.TestCase):
                 elif stored in normal and mask[normal.index(stored)]:
                     expected = [stored]
                 else:
-                    expected = next(([n] for n, yes in zip(normal, mask[:3]) if yes), [])
+                    expected = ["nation"]    # always open
                 self.assertEqual(selected, expected, (mask, stored))
-                self.assertEqual(_evaluate(empty, shown, stored), not expected)
 
     def test_normal_tabs_remain_clickable_while_debug_tab_is_selected(self):
         gui = read("gui/te_systems_window.gui")
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_te_systems_window test_tax_code_probes 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: FAILED (no `te_systems_window_nation_selected`).

- [ ] **Step 3: Edit the window**

Save this one-off script outside the repository (it is not committed) and run it from the repository root, `python3 /path/to/apply_window.py .`. It edits the header comments, replaces the selection templates, rebuilds the two strips (Nation, Space Race, Grand Monuments; Colonial Empire, Seabed), drops the "nothing open" line, mounts Nation's content first, moves the Colonial Empire's content after Grand Monuments (the strips' order), and removes the launcher's gate. Every anchor is asserted, so a moved line stops it.

```python
"""Plan Task 2, a one-off (not committed): the Timeline Extended window gets
Nation first, the Colonial Empire on the second strip, new selection
templates, Nation's content block and a launcher with no rule gate. Every
anchor is asserted, so a moved line stops it rather than mis-editing it.
Run from the repository root: python3 apply_window.py ."""
import sys
from pathlib import Path

SYSTEMS = ["space_race", "grand_monuments", "colonial_empire", "seabed"]   # strip order after Nation
G = "GetScriptedGui('{}').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
S = "GetVariableSystem.HasValue('te_systems_window_tab', '{}')"
T = "And( {}, {} )".format(S.format("tax_probes"), G.format("te_tp_tab_sgui"))


def chosen_open(t):
    return "And( {}, {} )".format(S.format(t), G.format(f"te_window_{t}_tab_sgui"))


def any_of(terms):
    if len(terms) == 1:
        return terms[0]
    mid = len(terms) // 2
    return "Or( {}, {} )".format(any_of(terms[:mid]), any_of(terms[mid:]))


V = any_of([chosen_open(t) for t in SYSTEMS])
out = {"nation_selected": "And( Not( {} ), Not( {} ) )".format(T, V),
       "nation_unselected": "Or( {}, {} )".format(T, V)}
for t in SYSTEMS:
    sel = "And( Not( {} ), {} )".format(T, chosen_open(t))
    out[f"{t}_selected"] = sel
    out[f"{t}_unselected"] = "And( {}, Not( {} ) )".format(G.format(f"te_window_{t}_tab_unlock_sgui"), sel)
TEMPLATES = "".join(f"template te_systems_window_{name} {{\n\tvisible = \"[{expr}]\"\n}}\n\n" for name, expr in out.items())


root = Path(sys.argv[1])
path = root / "gui" / "te_systems_window.gui"
s = path.read_text(encoding="utf-8-sig")


def sub_once(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)


def cut(start_marker, end_marker):
    """Remove and return s[start:end] between two markers (end exclusive)."""
    global s
    a = s.index(start_marker)
    b = s.index(end_marker, a)
    piece = s[a:b]
    s = s[:a] + s[b:]
    return piece


# 1. The header: Nation, and the strips' order.
sub_once("""### home (docs/systems/system_panels_feasibility.md §9, item 3): one tab each
### for the Space Race, the Colonial Empire and Grand Monuments, and the
### Seabed (Global Commons, on a strip of its own below them). Additive: a""",
"""### home (docs/systems/system_panels_feasibility.md §9, item 3). The first
### strip: Nation (what the country carries for good, always open;
### gui/te_nation_tab.gui), the Space Race and Grand Monuments. The second: the
### Colonial Empire and the Seabed (Global Commons). Additive: a""")
sub_once("""###   te_systems_window_tab = space_race | colonial_empire | grand_monuments
###       | seabed
###       the tab the player last chose. The tab shown is that one while it is
###       open, otherwise the first open tab (the te_systems_window_*_selected""",
"""###   te_systems_window_tab = nation | space_race | grand_monuments
###       | colonial_empire | seabed
###       the tab the player last chose. The tab shown is that one while it is
###       open, otherwise Nation, which always is (the te_systems_window_*_selected""")
sub_once("""###   not observer mode, where GetPlayer is empty); then, for the launcher, a
###   game rule of the three (te_window_launcher_sgui); for the window, its open""",
"""###   not observer mode, where GetPlayer is empty); then, for the window, its open""")

# 2. The selection templates (none_open goes: Nation is always open).
start = s.index("### Which tab is shown.")
end = s.index("template te_systems_window_tax_probes_selected")
s = s[:start] + """### Which tab is shown. U = the tab is open (te_window_<system>_tab_sgui: its
### rule on and an entry running), R = the tab is on the strip
### (te_window_<system>_tab_unlock_sgui: its rule on), S = the player last chose
### it (te_systems_window_tab), T = the developer tax tab is chosen and armed.
### With V = "a system tab last chosen is open" (S and U for one of the four):
###   Nation       not T and not V
###   a system t   not T and S_t and U_t
### so exactly one tab is shown: Nation unless an open system tab was the last
### choice. A system tab's unselected half shows while it is on the strip and
### not shown, Nation's while another tab is. The Seabed tab has no journal
### entry: it is open (te_window_seabed_tab_sgui) once the country has taken
### part in a seabed sharing.
""" + TEMPLATES.rstrip("\n") + "\n\n" + s[end:]

# 3. The first strip: Nation, Space Race, Grand Monuments.
sr_old = s[s.index("\t\t\t\t\t### Space Race\n"):s.index("\t\t\t\t\t### Colonial Empire\n")]
ce = s[s.index("\t\t\t\t\t### Colonial Empire\n"):s.index("\t\t\t\t\t### Grand Monuments\n")]
s = s.replace(ce, "")
sr_new = sr_old.replace('"first_button', '"second_button')
nation = """\t\t\t\t\t### Nation: always open (no journal entry, no game rule), so never
\t\t\t\t\t### greyed and never a checklist (style rule 9's exception).
\t\t\t\t\tblockoverride "first_button" {
\t\t\t\t\t\ttext = "te_window_tab_nation"
\t\t\t\t\t}
\t\t\t\t\tblockoverride "first_button_tooltip" {
\t\t\t\t\t\ttooltip = "te_window_tab_nation_tt"
\t\t\t\t\t}
\t\t\t\t\tblockoverride "first_button_click" {
\t\t\t\t\t\tonclick = "[GetVariableSystem.Set('te_systems_window_tab', 'nation')]"
\t\t\t\t\t}
\t\t\t\t\tblockoverride "first_button_visibility" {
\t\t\t\t\t\tusing = te_systems_window_nation_selected
\t\t\t\t\t}
\t\t\t\t\tblockoverride "first_button_visibility_checked" {
\t\t\t\t\t\tusing = te_systems_window_nation_unselected
\t\t\t\t\t}
\t\t\t\t\tblockoverride "first_button_selected" {
\t\t\t\t\t\ttext = "te_window_tab_nation"
\t\t\t\t\t}

"""
s = s.replace(sr_old, nation + sr_new)

# 4. The second strip: Colonial Empire, Seabed.
strip_start = s.index("\t\t\t\t### Seabed (Global Commons): a strip of its own under the three, so")
strip_body = s.index("\t\t\t\t\tblockoverride \"first_button\" {", strip_start)
seabed_old = s[strip_body:s.index("\n\t\t\t\t}\n", strip_body) + 1]
seabed_new = "\t\t\t\t\t### Seabed\n" + seabed_old.replace('"first_button', '"second_button')
head_old = s[strip_start:strip_body]
head_new = """\t\t\t\t### The second strip: the Colonial Empire and the Seabed (Global Commons),
\t\t\t\t### so the first strip's names keep their width (four tabs on one strip
\t\t\t\t### would leave each name about 115, and "Colonial Empire" and "Grand
\t\t\t\t### Monuments" need 142). Up while either rule is on.
\t\t\t\ttab_buttons = {
\t\t\t\t\tname = "te_systems_window_second_strip"
\t\t\t\t\tvisible = "[Or( GetScriptedGui('te_window_colonial_empire_tab_unlock_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ), GetScriptedGui('te_window_seabed_tab_unlock_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ) )]"
"""
s = s[:strip_start] + head_new + ce.replace('"second_button', '"first_button') + seabed_new + s[strip_body + len(seabed_old):]

# 5. The content: no "nothing open" line; Nation first; Colonial Empire after Grand Monuments.
none = s[s.index("\t\t\t\t### No tab open yet.\n"):s.index("\t\t\t\t### The tabs' content, in the strip's order.")]
s = s.replace(none, "")
ce_content = cut("\t\t\t\t### ------------------------------------------------------------------\n\t\t\t\t### TAB: COLONIAL EMPIRE",
                 "\t\t\t\t### ------------------------------------------------------------------\n\t\t\t\t### TAB: GRAND MONUMENTS")
seabed_at = s.index("\t\t\t\t### ------------------------------------------------------------------\n\t\t\t\t### TAB: SEABED")
s = s[:seabed_at] + ce_content + s[seabed_at:]
sr_at = s.index("\t\t\t\t### ------------------------------------------------------------------\n\t\t\t\t### TAB: SPACE RACE")
s = s[:sr_at] + """\t\t\t\t### ------------------------------------------------------------------
\t\t\t\t### TAB: NATION (spec 2026-10-17-national-modifiers-tab-design.md; the
\t\t\t\t### types are in gui/te_nation_tab.gui). No journal entry and no gate: the
\t\t\t\t### sections read the player's country through GetPlayer, each gated on
\t\t\t\t### its own data.
\t\t\t\tflowcontainer = {
\t\t\t\t\tname = "te_systems_window_nation_tab"
\t\t\t\t\tusing = te_systems_window_nation_selected
\t\t\t\t\tusing = default_fade_in_out
\t\t\t\t\tparentanchor = hcenter
\t\t\t\t\tdirection = vertical
\t\t\t\t\tignoreinvisible = yes
\t\t\t\t\tmargin_top = 10
\t\t\t\t\tmargin_bottom = 15

\t\t\t\t\tte_nation_tab_sections = {}
\t\t\t\t}

""" + s[sr_at:]

# 6. The launcher: no gate beyond the played country (Nation is always open).
sub_once("""\t\t\tvisible = "[GetScriptedGui('te_window_launcher_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"\n""", "")

path.write_text("﻿" + s, encoding="utf-8", newline="\n")
print("ok")
```

Review the result with `git diff gui/te_systems_window.gui`. The developer tax strip's comment ("second strip avoids shrinking…") can stay; it is temporary.

- [ ] **Step 4: The launcher's gate and the loc**

`common/scripted_guis/te_system_tab_sguis.txt`:

```diff
diff --git a/common/scripted_guis/te_system_tab_sguis.txt b/common/scripted_guis/te_system_tab_sguis.txt
index bbcfd3c..b69ae6e 100644
--- a/common/scripted_guis/te_system_tab_sguis.txt
+++ b/common/scripted_guis/te_system_tab_sguis.txt
@@ -294,8 +294,8 @@ te_pops_demog_tab_unlock_sgui = {
 	effect = { }
 }
 # The Timeline Extended window (gui/te_systems_window.gui) uses the same pair
-# per tab, named te_window_<system>_tab_sgui / _tab_unlock_sgui, plus a gate for
-# its launcher and one per Space Race entry (at the foot of this file).
+# per system tab, named te_window_<system>_tab_sgui / _tab_unlock_sgui, plus one
+# per Space Race entry (at the foot of this file). Its Nation tab has none.
 #
 
 # ===========================================================================
@@ -303,24 +303,8 @@ te_pops_demog_tab_unlock_sgui = {
 # vanilla home, one tab each (docs/systems/system_panels_feasibility.md §9).
 # ===========================================================================
 
-# The launcher under the sidebar shows while any of the three systems' game
-# rules is on.
-te_window_launcher_sgui = {
-	scope = country
-	is_shown = {
-		OR = {
-			has_variable = te_tp_armed # TEMPORARY PR 585: developer-only tax tab
-
-			has_game_rule = space_race_enabled
-			has_game_rule = decolonization_enabled
-			gm_system_enabled = yes
-			te_global_commons_enabled = yes
-		}
-	}
-	ai_is_valid = { always = no }
-	is_valid = { always = no }
-	effect = { }
-}
+# The launcher has no gate of its own: the Nation tab is always open, so the
+# window is up for every played country (gui/te_systems_window.gui).
 
 # ---------------------------------------------------------------------------
 # Space Race: the nine je_space_race_* entries (je_space_race.txt). The tab
```

`localization/english/te_miscellaneous_l_english.yml`: replace the launcher's tooltip, delete `te_systems_window_none`, and add the tab's name and tooltip before `te_window_tab_space_race`:

```yaml
 te_systems_window_launcher_tt:0 "#b Timeline Extended#!\nNation: what your country carries for good, in one place. Then a tab each for the Space Race, Grand Monuments, the Colonial Empire and the Seabed, the journal entries' own panels: a change made there shows in the journal too."
 te_window_tab_nation:0 "Nation"
 te_window_tab_nation_tt:0 "What your country carries for good: its standing scores, and the permanent rewards, memberships and policies the country panel's modifier list leaves out."
```

Then run `python3 organize_loc.py`, which sorts the two new keys into place (before the Seabed's), and `python3 organize_loc.py --check`.

`docs/testing/tax-code-playtest.md` (the harness's hooks no longer include the launcher's gate):

```diff
diff --git a/docs/testing/tax-code-playtest.md b/docs/testing/tax-code-playtest.md
index a616760..dc455f5 100644
--- a/docs/testing/tax-code-playtest.md
+++ b/docs/testing/tax-code-playtest.md
@@ -500,7 +500,7 @@ P09b or P09c passed and a customs follow-up kept them, the customs probe's regis
 (`events/te_tax_debug_events.txt`, `te_tax_debug.*`) is not harness and stays.
 
 Its hooks in production files must change with it: the Tax Probes tab in
-`gui/te_systems_window.gui` and `te_window_launcher_sgui` (`te_system_tab_sguis.txt`); the
+`gui/te_systems_window.gui`; the
 `te_tp_observe_controls` calls in `banking_policy_effects.txt` and
 `te_monetary_arrangement_effects.txt`; the `te_tp_lock` test in both gates of
 `common/scripted_guis/te_tax_native_sguis.txt`; `organize_loc.py`'s `DEBUG_TAX` category and its
```

- [ ] **Step 5: Run the tests**

Run: `.venv/bin/python -m unittest test_te_systems_window test_tax_code_probes 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: `OK` (33 and 15 tests on 2026-10-17). `test_the_tabs_content_in_the_strips_order` needs `te_nation_tab_sections = {}`, which the script mounts; the type itself comes in Task 3.

- [ ] **Step 6: Commit**

```bash
git add gui/te_systems_window.gui common/scripted_guis/te_system_tab_sguis.txt \
  localization/english/te_miscellaneous_l_english.yml test_te_systems_window.py test_tax_code_probes.py \
  docs/testing/tax-code-playtest.md
git commit -m "Timeline Extended window: Nation first and always open, the Colonial Empire beside the Seabed"
```

---

### Task 3: The Nation tab's layout

**Files:**
- Create: `gui/te_nation_tab.gui`, `common/script_values/te_nation_values.txt`
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `test_nation_tab.py`

**Interfaces:**
- Produces: `te_nation_tab_sections` (overview, five sections, How the Nation Works); script values `te_nation_override_capacity`, `te_nation_override_bar`, `te_nation_override_tier`, `te_nation_mandate_on`, `te_nation_construction_cost`, `te_nation_private_construction`.
- Consumes: Task 1's templates and counts; `te_inh_concentration_display`, `te_inh_concentration_target`, `algorithmic_mandate_value`, `global_tech_spread_script_value`; `var:prior_construction_scaling`.

Layout (style guide rules 1, 3–5, 8): a 520 column, panels with 480 inside; rows 17, headings 20, the overview 16. Overview boxes, two to a row: Override Capacity (the strongest Forceful Legislation option open; "Capacity: +2.5"), Wealth Concentration ("Concentrating"; "62 → 68"), Construction Cost ("Scaled by wealth"; "+35%"), Global Technology ("Spreading"; "+60 spread"). Each row is "Label: value" with its reason on hover, its own modifiers listed under it ("what it gives now"); then the section's list. Science and Space and International draw only with something to show. Legislative Override Capacity's figure is the engine's breakdown (`GetValueWithBreakdownFor`), on a bar from −6 to +8 with a line at 0, 2 and 4, each line its own hover.

- [ ] **Step 1: Add the layout tests** (append to `test_nation_tab.py`, before `class FixtureTest`)

```python
class TabLayoutTest(unittest.TestCase):
    """gui/te_nation_tab.gui: the sections in the spec's order, each list and
    row line on its generated filter, each list gated on its count, and every
    key the tab prints defined."""

    TAB = ROOT / "gui" / "te_nation_tab.gui"

    @classmethod
    def setUpClass(cls):
        cls.gui = _read(cls.TAB)

    def test_the_window_mounts_the_tab(self):
        window = _read(ROOT / "gui" / "te_systems_window.gui")
        self.assertIn("te_nation_tab_sections = {}", window)
        self.assertTrue(self.TAB.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_sections_in_order(self):
        body = self.gui[self.gui.index("type te_nation_tab_sections"):]
        order = re.findall(r"^\t\t(te_nation_\w+) = \{\}", body, re.M)
        self.assertEqual(order, ["te_nation_overview_panel"]
                         + [f"te_nation_section_{s}" for s in gen.SECTIONS] + ["te_nation_how_panel"])

    def test_every_filter_is_used_once_and_lists_are_gated(self):
        for section in gen.SECTIONS:
            with self.subTest(section=section):
                self.assertEqual(self.gui.count(f"using = te_nation_list_{section}\n"), 1)
                # the list, or the section holding nothing else, shows on its count
                body = self.gui[self.gui.index(f"type te_nation_section_{section} = "):]
                body = body[:body.index("\n\t}\n")]
                self.assertIn(f"ScriptValue('te_nation_list_{section}_count'), '(CFixedPoint)0' )", body)
        for row in gen.ROWS:
            with self.subTest(row=row):
                self.assertEqual(self.gui.count(f"using = te_nation_row_{row}\n"), 1)

    def test_a_list_item_has_one_visible(self):
        # The filter is the item's only `visible` (gotcha #17).
        body = self.gui[self.gui.index("type te_nation_list = "):self.gui.index("type te_nation_target_bar")]
        item = body[body.index("item = {"):]
        self.assertNotIn("visible", item)
        self.assertIn('block "filter" {}', item)
        self.assertIn("ignoreinvisible = yes", body)

    def test_every_key_exists(self):
        loc = _loc()
        keys = set(re.findall(r'\b(?:text|tooltip) = "(te_nation_\w+)"', self.gui))
        # SelectLocalization's keys in the loc ("( 'key'" or ", 'key'"; ScriptValue('x') has no space)
        keys |= set(re.findall(r"[(,] '(te_nation_\w+)'", " ".join(loc.values())))
        self.assertGreater(len(keys), 30)
        missing = sorted(k for k in keys if k not in loc)
        self.assertFalse(missing, missing)

    def test_every_script_value_exists(self):
        values = _read(ROOT / "common" / "script_values" / "te_nation_values.txt")
        values += _read(gen.VALUES_OUT)
        defined = set(re.findall(r"^(\w+) = \{", values, re.M))
        text = self.gui + "\n".join(_loc().values())
        used = set(re.findall(r"ScriptValue\('(te_nation_\w+)'\)", text))
        self.assertTrue(used)
        self.assertLessEqual(used, defined)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_nation_tab 2>&1 | grep -E '^(Ran |OK|FAILED)|Error'`
Expected: FAILED (no `gui/te_nation_tab.gui`).

- [ ] **Step 3: The rows' values** (`common/script_values/te_nation_values.txt`, with a BOM)

```
# The Nation tab's rows (gui/te_nation_tab.gui). Country scope, read through
# GetPlayer.MakeScope. Each is safe before its system has first run. The
# lists' counts are generated (te_nation_generated_values.txt).

# Legislative Override Capacity, the raw modifier sum (its sources:
# concept_legislative_override_capacity).
te_nation_override_capacity = {
	value = modifier:country_legislative_override_capacity_add
}

# Its bar: -6 to +8 as 0 to 1.
te_nation_override_bar = {
	value = te_nation_override_capacity
	add = 6
	divide = 14
	min = 0
	max = 1
}

# The strongest Forceful Legislation option the capacity opens
# (minor_events_timelineextended.2 in events/minor_events.txt): 0 the event
# isn't offered (below 0), 1 expedite, 2 push decisively (at 2), 3 force it
# through (at 4). Authority decides the rest, as the event says.
te_nation_override_tier = {
	value = 0
	if = {
		limit = { te_nation_override_capacity >= 4 }
		value = 3
	}
	else_if = {
		limit = { te_nation_override_capacity >= 2 }
		value = 2
	}
	else_if = {
		limit = { te_nation_override_capacity >= 0 }
		value = 1
	}
}

# 1 under Algorithmic Governance, whose mandate the row shows.
te_nation_mandate_on = {
	value = 0
	if = {
		limit = { has_law = law_type:law_algorithmic_governance }
		value = 1
	}
}

# Construction cost scaling: the multiplier the yearly pulse last applied
# (construction_cost_scaling_on_action, either rule's branch), 0 before it.
te_nation_construction_cost = {
	value = 0
	if = {
		limit = { has_variable = prior_construction_scaling }
		value = var:prior_construction_scaling
	}
}

# 1 while excess private construction or Overinvestment is in force.
te_nation_private_construction = {
	value = 0
	if = {
		limit = {
			OR = {
				has_modifier = too_much_private_construction
				has_modifier = overinvestment_modifier
			}
		}
		value = 1
	}
}
```

- [ ] **Step 4: The tab** (`gui/te_nation_tab.gui`, with a BOM)

```
### The Nation tab of the Timeline Extended window (gui/te_systems_window.gui
### instances te_nation_tab_sections): what the country carries for good, in
### one place. Spec: docs/superpowers/archive/specs/2026-10-17-national-modifiers-tab-design.md
### § 2. An overview of boxes, two to a row; five sections, open, each its
### score rows and then its list; How the Nation Works, collapsed. House
### style: docs/guides/gui_style_guide.md.
###
### DATA. No journal entry and no gate: everything reads the player's country
### through GetPlayer. The rows read script values
### (common/script_values/te_nation_values.txt) and the engine's modifier sums.
### A list is the country's own timed modifiers filtered by name
### (te_nation_list_<section>, and te_nation_row_<row> under a row, both
### generated in gui/te_nation_generated.gui), each with its own tooltip, so
### the engine renders the effects at their current scale. The country panel's
### list hides the same names (gui/00_te_country_panel_information.gui).
###
### WIDTHS. A 520 column, panels with 480 inside. Rows 17, headings 20, the
### overview 16 (te_nation_fontsize_*; rule 3).

template te_nation_fontsize_row {
	fontsize = 17
}

template te_nation_fontsize_heading {
	fontsize = 20
}

template te_nation_fontsize_overview {
	fontsize = 16
	using = tooltip_font
}

types te_nation_widget_types
{
	type te_nation_panel = flowcontainer {
		direction = vertical
		ignoreinvisible = yes
		parentanchor = hcenter
		margin = { 20 8 }
		minimumsize = { 520 -1 }
		spacing = 4

		background = {
			using = entry_bg_fancy_dark
			alpha = 0.5
		}
	}

	### A section's heading, centred over its panel (rule 7).
	type te_nation_header = default_header {
		using = default_list_position
	}

	### A heading inside How the Nation Works, with a faint rule under it.
	type te_nation_subheader = flowcontainer {
		direction = vertical
		ignoreinvisible = yes
		spacing = 1
		margin_top = 6

		textbox = {
			autoresize = yes
			multiline = yes
			maximumsize = { 480 -1 }
			align = left|nobaseline
			using = te_nation_fontsize_heading
			default_format = "#title"
			block "subheader_text" {}
		}
		divider_clean = {
			blockoverride "size" {
				size = { 480 2 }
			}
		}
	}

	type te_nation_note = textbox {
		autoresize = yes
		multiline = yes
		minimumsize = { 480 -1 }
		maximumsize = { 480 -1 }
		align = left|nobaseline
		using = te_nation_fontsize_row
		default_format = "#lore"
	}

	### A row: "Label: value", the detail on hover (rule 3).
	type te_nation_row = textbox {
		autoresize = yes
		multiline = yes
		minimumsize = { 480 -1 }
		maximumsize = { 480 -1 }
		align = left|nobaseline
		using = te_nation_fontsize_row
	}

	### ----------------------------------------------------------------------
	### The overview's box (rule 4; te_banking_ov_cell's shape): the icon in an
	### inset box down the left, and beside it the caption, the word and a
	### figure, in a 154 column at 16. Two to a row: 238 + 4 + 238 = 480.
	### ----------------------------------------------------------------------
	type te_nation_ov_cell = widget {
		size = { 238 70 }

		background = {
			using = entry_bg_simple
		}

		widget = {
			size = { 52 52 }
			position = { 6 0 }
			parentanchor = left|vcenter

			background = {
				using = dark_area
				alpha = 0.3
			}

			icon = {
				size = { 44 44 }
				parentanchor = center
				block "icon" {}
			}
		}
		textbox = {
			position = { 78 2 }
			autoresize = yes
			max_width = 154
			elide = right
			align = left|nobaseline
			using = te_nation_fontsize_overview
			default_format = "#tooltippable"
			block "caption" {}
		}
		textbox = {
			position = { 78 24 }
			autoresize = yes
			max_width = 154
			elide = right
			align = left|nobaseline
			using = te_nation_fontsize_overview
			block "word" {}
		}
		textbox = {
			position = { 78 46 }
			autoresize = yes
			max_width = 154
			elide = right
			align = left|nobaseline
			using = te_nation_fontsize_overview
			block "fig" {}
		}
	}

	### ----------------------------------------------------------------------
	### A list of the country's own modifiers: icon and name, the modifier's
	### own tooltip on hover. block "filter" takes the generated name filter
	### (te_nation_list_<section> or te_nation_row_<row>), the item's only
	### `visible`; the list ignores the items it hides.
	### ----------------------------------------------------------------------
	type te_nation_list = flowcontainer {
		datamodel = "[GetPlayer.GetTimedModifiers]"
		direction = vertical
		ignoreinvisible = yes
		spacing = 4
		margin_top = 2

		item = {
			flowcontainer = {
				block "filter" {}
				spacing = 10
				minimumsize = { 480 -1 }
				tooltip = "[TimedModifier.GetTooltip]"

				icon = {
					texture = "[TimedModifier.GetIcon]"
					size = { 25 25 }
				}
				textbox = {
					text = "[TimedModifier.GetName]"
					autoresize = yes
					align = nobaseline
					parentanchor = vcenter
					using = te_nation_fontsize_row
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### A score heading for its target (rule 5): the solid fill runs to the
	### lower of the two, a translucent segment to the higher. 480 x 14.
	### block "high" and block "low" take the two values; "range" the max.
	### ----------------------------------------------------------------------
	type te_nation_target_bar = widget {
		size = { 480 14 }
		parentanchor = hcenter

		default_progressbar_horizontal = {
			size = { 100% 100% }
			blockoverride "values" {
				value = 0
				min = 0
				max = 1
			}
		}
		widget = {
			size = { 100% 100% }
			alpha = 0.4

			default_progressbar_horizontal = {
				size = { 100% 100% }
				blockoverride "background" {}
				blockoverride "frame" {}
				blockoverride "values" {
					block "high" {}
					min = 0
					max = 100
				}
			}
		}
		default_progressbar_horizontal = {
			size = { 100% 100% }
			blockoverride "background" {}
			blockoverride "frame" {}
			blockoverride "values" {
				block "low" {}
				min = 0
				max = 100
			}
		}
	}

	### ----------------------------------------------------------------------
	### The overview: always shown (rule 1).
	### ----------------------------------------------------------------------
	type te_nation_overview_panel = te_nation_panel {
		flowcontainer = {
			direction = horizontal
			spacing = 4

			te_nation_ov_cell = {
				tooltip = "te_nation_ov_override_tt"
				blockoverride "icon" {
					texture = "gfx/interface/icons/topbar/authority_icon.dds"
				}
				blockoverride "caption" {
					text = "te_nation_ov_override_cap"
				}
				blockoverride "word" {
					text = "te_nation_ov_override_word"
				}
				blockoverride "fig" {
					text = "te_nation_ov_override_fig"
				}
			}
			te_nation_ov_cell = {
				tooltip = "te_nation_ov_wc_tt"
				blockoverride "icon" {
					texture = "gfx/interface/icons/generic_icons/gdp.dds"
				}
				blockoverride "caption" {
					text = "te_nation_ov_wc_cap"
				}
				blockoverride "word" {
					text = "te_nation_ov_wc_word"
				}
				blockoverride "fig" {
					text = "te_nation_ov_wc_fig"
				}
			}
		}
		flowcontainer = {
			direction = horizontal
			spacing = 4

			te_nation_ov_cell = {
				tooltip = "te_nation_ov_construction_tt"
				blockoverride "icon" {
					texture = "gfx/interface/icons/state_status_icons/has_construction.dds"
				}
				blockoverride "caption" {
					text = "te_nation_ov_construction_cap"
				}
				blockoverride "word" {
					text = "te_nation_ov_construction_word"
				}
				blockoverride "fig" {
					text = "te_nation_ov_construction_fig"
				}
			}
			te_nation_ov_cell = {
				tooltip = "te_nation_ov_tech_tt"
				blockoverride "icon" {
					texture = "gfx/interface/icons/generic_icons/literacy.dds"
				}
				blockoverride "caption" {
					text = "te_nation_ov_tech_cap"
				}
				blockoverride "word" {
					text = "te_nation_ov_tech_word"
				}
				blockoverride "fig" {
					text = "te_nation_ov_tech_fig"
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### GOVERNANCE: Legislative Override Capacity, the Algorithmic Mandate, and
	### the list (the armed forces' training, heir education).
	### ----------------------------------------------------------------------
	type te_nation_section_governance = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes

		te_nation_header = {
			blockoverride "text" {
				text = "te_nation_sec_governance"
			}
		}
		te_nation_panel = {
			### Legislative Override Capacity: the value with the engine's
			### breakdown on hover, a bar from -6 to +8 with a line at each
			### Forceful Legislation threshold, and the strongest option open.
			te_nation_row = {
				text = "te_nation_override_row"
			}
			widget = {
				size = { 480 14 }
				parentanchor = hcenter

				default_progressbar_horizontal = {
					size = { 100% 100% }
					blockoverride "values" {
						value = "[FixedPointToFloat( GetPlayer.MakeScope.ScriptValue('te_nation_override_bar') )]"
						min = 0
						max = 1
					}
				}
				### The thresholds at 0, 2 and 4: (t + 6) / 14 of 480.
				icon = {
					size = { 2 18 }
					position = { 205 -2 }
					texture = "gfx/interface/backgrounds/white.dds"
					color = { 0.96 0.90 0.72 0.9 }
					tooltip = "te_nation_override_line_0_tt"
				}
				icon = {
					size = { 2 18 }
					position = { 274 -2 }
					texture = "gfx/interface/backgrounds/white.dds"
					color = { 0.96 0.90 0.72 0.9 }
					tooltip = "te_nation_override_line_2_tt"
				}
				icon = {
					size = { 2 18 }
					position = { 342 -2 }
					texture = "gfx/interface/backgrounds/white.dds"
					color = { 0.96 0.90 0.72 0.9 }
					tooltip = "te_nation_override_line_4_tt"
				}
			}
			te_nation_row = {
				visible = "[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)0' )]"
				text = "te_nation_override_tier_0"
			}
			te_nation_row = {
				visible = "[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)1' )]"
				text = "te_nation_override_tier_1"
			}
			te_nation_row = {
				visible = "[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)2' )]"
				text = "te_nation_override_tier_2"
			}
			te_nation_row = {
				visible = "[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)3' )]"
				text = "te_nation_override_tier_3"
			}

			### The Algorithmic Mandate, under Algorithmic Governance only.
			flowcontainer = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_mandate_on'), '(CFixedPoint)0' )]"
				direction = vertical
				ignoreinvisible = yes
				margin_top = 6

				te_nation_row = {
					text = "te_nation_mandate_row"
					tooltip = "te_nation_mandate_row_tt"
				}
				te_nation_list = {
					blockoverride "filter" {
						using = te_nation_row_algorithmic_mandate
					}
				}
			}

			te_nation_list = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_governance_count'), '(CFixedPoint)0' )]"
				blockoverride "filter" {
					using = te_nation_list_governance
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### SOCIETY: Wealth Concentration, and the list (demographic policies,
	### living-standard expectations, civil rights, resettlement).
	### ----------------------------------------------------------------------
	type te_nation_section_society = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes

		te_nation_header = {
			blockoverride "text" {
				text = "te_nation_sec_society"
			}
		}
		te_nation_panel = {
			te_nation_row = {
				text = "te_nation_wc_row"
				tooltip = "te_nation_wc_row_tt"
			}
			te_nation_target_bar = {
				blockoverride "high" {
					value = "[FixedPointToFloat( Max_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display'), GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target') ) )]"
				}
				blockoverride "low" {
					value = "[FixedPointToFloat( Min_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display'), GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target') ) )]"
				}
			}
			te_nation_list = {
				blockoverride "filter" {
					using = te_nation_row_wealth_concentration
				}
			}
			te_nation_list = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_society_count'), '(CFixedPoint)0' )]"
				blockoverride "filter" {
					using = te_nation_list_society
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### ECONOMY: Construction Cost, Private Construction while in force, and
	### the list (agricultural diffusion, the private share, the tax code's
	### reactions and relief, monetary bands, colonial programmes).
	### ----------------------------------------------------------------------
	type te_nation_section_economy = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes

		te_nation_header = {
			blockoverride "text" {
				text = "te_nation_sec_economy"
			}
		}
		te_nation_panel = {
			te_nation_row = {
				text = "te_nation_construction_row"
				tooltip = "te_nation_construction_row_tt"
			}
			te_nation_list = {
				blockoverride "filter" {
					using = te_nation_row_construction_cost
				}
			}
			flowcontainer = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_private_construction'), '(CFixedPoint)0' )]"
				direction = vertical
				ignoreinvisible = yes
				margin_top = 6

				te_nation_row = {
					text = "te_nation_private_row"
					tooltip = "te_nation_private_row_tt"
				}
				te_nation_list = {
					blockoverride "filter" {
						using = te_nation_row_private_construction
					}
				}
			}
			te_nation_list = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_economy_count'), '(CFixedPoint)0' )]"
				blockoverride "filter" {
					using = te_nation_list_economy
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### SCIENCE AND SPACE: Global Technological Development while above zero,
	### and the list (space race rewards, debris, Antarctica, the seabed).
	### Drawn only with something to show (rule 8).
	### ----------------------------------------------------------------------
	type te_nation_section_science_and_space = flowcontainer {
		visible = "[Or( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('global_tech_spread_script_value'), '(CFixedPoint)0' ), GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_science_and_space_count'), '(CFixedPoint)0' ) )]"
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes

		te_nation_header = {
			blockoverride "text" {
				text = "te_nation_sec_science_and_space"
			}
		}
		te_nation_panel = {
			flowcontainer = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('global_tech_spread_script_value'), '(CFixedPoint)0' )]"
				direction = vertical
				ignoreinvisible = yes

				te_nation_row = {
					text = "te_nation_tech_row"
					tooltip = "te_nation_tech_row_tt"
				}
				te_nation_list = {
					blockoverride "filter" {
						using = te_nation_row_global_tech
					}
				}
			}
			te_nation_list = {
				visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_science_and_space_count'), '(CFixedPoint)0' )]"
				blockoverride "filter" {
					using = te_nation_list_science_and_space
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### INTERNATIONAL: the list only (UN conventions and regime terms,
	### sanctions, intelligence sharing, the nuclear taboo, an overlord in
	### decline). Drawn only with something to show (rule 8).
	### ----------------------------------------------------------------------
	type te_nation_section_international = flowcontainer {
		visible = "[GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_list_international_count'), '(CFixedPoint)0' )]"
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes

		te_nation_header = {
			blockoverride "text" {
				text = "te_nation_sec_international"
			}
		}
		te_nation_panel = {
			te_nation_list = {
				blockoverride "filter" {
					using = te_nation_list_international
				}
			}
		}
	}

	### ----------------------------------------------------------------------
	### How the Nation Works: collapsed (te_nation_how_open).
	### ----------------------------------------------------------------------
	type te_nation_how_panel = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 4

		section_header_button = {
			blockoverride "layout" {
				parentanchor = hcenter
				size = { 520 38 }
			}
			blockoverride "left_text" {
				text = "te_nation_how_header"
			}
			blockoverride "onclick" {
				onclick = "[GetVariableSystem.Toggle('te_nation_how_open')]"
			}
			blockoverride "onclick_showmore" {
				visible = "[Not(GetVariableSystem.Exists('te_nation_how_open'))]"
			}
			blockoverride "onclick_showless" {
				visible = "[GetVariableSystem.Exists('te_nation_how_open')]"
			}
		}

		te_nation_panel = {
			visible = "[GetVariableSystem.Exists('te_nation_how_open')]"

			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_tab"
				}
			}
			te_nation_note = {
				text = "te_nation_how_tab"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_override"
				}
			}
			te_nation_note = {
				text = "te_nation_how_override"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_mandate"
				}
			}
			te_nation_note = {
				text = "te_nation_how_mandate"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_wc"
				}
			}
			te_nation_note = {
				text = "te_nation_how_wc"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_construction"
				}
			}
			te_nation_note = {
				text = "te_nation_how_construction"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_tech"
				}
			}
			te_nation_note = {
				text = "te_nation_how_tech"
			}
			te_nation_subheader = {
				blockoverride "subheader_text" {
					text = "te_nation_how_sub_lists"
				}
			}
			te_nation_note = {
				text = "te_nation_how_lists"
			}
		}
	}

	### The whole tab, in the spec's order (owner, 2026-10-17).
	type te_nation_tab_sections = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 10

		te_nation_overview_panel = {}
		te_nation_section_governance = {}
		te_nation_section_society = {}
		te_nation_section_economy = {}
		te_nation_section_science_and_space = {}
		te_nation_section_international = {}
		te_nation_how_panel = {}
	}
}
```

- [ ] **Step 5: The loc** (`te_miscellaneous_l_english.yml`, after `te_window_tab_nation_tt`)

```yaml
 te_nation_construction_base:0 "Base cost"
 te_nation_construction_row:0 "Construction Cost: #v [GetPlayer.MakeScope.ScriptValue('te_nation_construction_cost')|%0+]#!"
 te_nation_construction_row_tt:0 "Set each year from GDP per capita: nothing for a poor country, rising in a straight line to +1,000% for the richest. It multiplies with the other construction-cost modifiers rather than adding to them."
 te_nation_construction_scaled:0 "Scaled by wealth"
 te_nation_how_construction:0 "A richer country needs more construction for each building and each level of upkeep, so a poor one catches up. The scaling is set each year from GDP per capita and multiplies with the other construction-cost modifiers."
 te_nation_how_header:0 "How the Nation Works"
 te_nation_how_lists:0 "Each section lists the country's permanent modifiers from its systems: hover one for its effects at their current size. Money a system charges or pays is in the Budget panel's Breakdown tab instead."
 te_nation_how_mandate:0 "Under Algorithmic Governance only. Legitimacy follows how living standards compare with what people expect, up to 40 either way."
 te_nation_how_override:0 "Laws, institutions, technologies and power bloc principles add to it, and forcing a law through takes some away for about five years. At 0 the Forceful Legislation event is offered, at 2 its decisive option and the tax code's Force Through, at 4 the strongest. Each point also trims the authority it costs."
 te_nation_how_sub_construction:0 "Construction Cost"
 te_nation_how_sub_lists:0 "The Lists"
 te_nation_how_sub_mandate:0 "The Algorithmic Mandate"
 te_nation_how_sub_override:0 "Legislative Override Capacity"
 te_nation_how_sub_tab:0 "This Tab"
 te_nation_how_sub_tech:0 "Global Technological Development"
 te_nation_how_sub_wc:0 "Wealth Concentration"
 te_nation_how_tab:0 "What your country carries for good, in one place: its standing scores, then the permanent rewards, memberships and policies, by section. The country panel's modifier list leaves these out; the breakdowns in tooltips still name each source. Timed effects stay in that list."
 te_nation_how_tech:0 "Once any great power researches certain modern technologies, every country's technology spread rises, so late starters catch up faster."
 te_nation_how_wc:0 "Each state's score moves toward a target set by the inheritance law, the taxes on wealth and the economic laws. The national score weighs the states by where property is held. High concentration brings Great Family Fortunes; low, Dispersed Wealth."
 te_nation_mandate_row:0 "Algorithmic Mandate: #v [GetPlayer.MakeScope.ScriptValue('algorithmic_mandate_value')|0+]#! legitimacy"
 te_nation_mandate_row_tt:0 "Algorithmic Governance's legitimacy follows living standards against expectations: ahead of them it rises, behind them it falls."
 te_nation_ov_construction_cap:0 "Construction Cost"
 te_nation_ov_construction_fig:0 "#v [GetPlayer.MakeScope.ScriptValue('te_nation_construction_cost')|%0+]#!"
 te_nation_ov_construction_tt:0 "How much more construction a richer country needs for each building and each level of upkeep. The Economy section below has the detail."
 te_nation_ov_construction_word:0 "[SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_construction_cost'), '(CFixedPoint)0' ), 'te_nation_construction_scaled', 'te_nation_construction_base' )]"
 te_nation_ov_override_cap:0 "[concept_legislative_override_capacity]"
 te_nation_ov_override_fig:0 "Capacity: #v [GetPlayer.MakeScope.ScriptValue('te_nation_override_capacity')|1+]#!"
 te_nation_ov_override_tt:0 "The strongest Forceful Legislation option your [concept_legislative_override_capacity] opens. Its sources are on the Governance row below."
 te_nation_ov_override_word:0 "[SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)0' ), SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)1' ), SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_override_tier'), '(CFixedPoint)2' ), 'te_nation_tier_force', 'te_nation_tier_push' ), 'te_nation_tier_expedite' ), 'te_nation_tier_none' )]"
 te_nation_ov_tech_cap:0 "Global Technology"
 te_nation_ov_tech_fig:0 "#v [GetPlayer.MakeScope.ScriptValue('global_tech_spread_script_value')|0+]#! spread"
 te_nation_ov_tech_tt:0 "Technology spread every country gains once a great power has researched certain modern technologies."
 te_nation_ov_tech_word:0 "[SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('global_tech_spread_script_value'), '(CFixedPoint)0' ), 'te_nation_tech_on', 'te_nation_tech_off' )]"
 te_nation_ov_wc_cap:0 "Wealth Concentration"
 te_nation_ov_wc_fig:0 "#v [GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display')|0]#! → [GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target')|0]"
 te_nation_ov_wc_tt:0 "How much of the nation's wealth sits with its richest families, and the score it is heading for. The Society section below says what it gives now."
 te_nation_ov_wc_word:0 "[SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target'), GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display') ), 'te_nation_wc_rising', SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display'), GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target') ), 'te_nation_wc_falling', 'te_nation_wc_steady' ) )]"
 te_nation_override_line_0_tt:0 "At 0: the Forceful Legislation event is offered when a law's enactment begins."
 te_nation_override_line_2_tt:0 "At 2: its Push Decisively option, and the tax code's Force Through."
 te_nation_override_line_4_tt:0 "At 4: its Force It Through option."
 te_nation_override_row:0 "[concept_legislative_override_capacity]: #v [GetPlayer.GetModifier.GetValueWithBreakdownFor('country_legislative_override_capacity_add')]#!"
 te_nation_override_tier_0:0 "Forceful Legislation: Not offered"
 te_nation_override_tier_1:0 "Forceful Legislation: up to Expedite"
 te_nation_override_tier_2:0 "Forceful Legislation: up to Push Decisively"
 te_nation_override_tier_3:0 "Forceful Legislation: up to Force It Through"
 te_nation_private_row:0 "Private Construction: excess in force"
 te_nation_private_row_tt:0 "The investment pool takes in more than the private queue can spend, so the cap on weekly construction rises and construction efficiency falls until the queue catches up."
 te_nation_sec_economy:0 "Economy"
 te_nation_sec_governance:0 "Governance"
 te_nation_sec_international:0 "International"
 te_nation_sec_science_and_space:0 "Science and Space"
 te_nation_sec_society:0 "Society"
 te_nation_tech_off:0 "Not yet"
 te_nation_tech_on:0 "Spreading"
 te_nation_tech_row:0 "Global Technological Development: #v [GetPlayer.MakeScope.ScriptValue('global_tech_spread_script_value')|0+]#! technology spread"
 te_nation_tech_row_tt:0 "+20 for each of several modern technologies (Television, Modern Automotive Technology and others) once any great power has researched it."
 te_nation_tier_expedite:0 "Expedite"
 te_nation_tier_force:0 "Force it through"
 te_nation_tier_none:0 "Not offered"
 te_nation_tier_push:0 "Push decisively"
 te_nation_wc_falling:0 "Dispersing"
 te_nation_wc_rising:0 "Concentrating"
 te_nation_wc_row:0 "Wealth Concentration: #v [GetPlayer.MakeScope.ScriptValue('te_inh_concentration_display')|0]#! → [GetPlayer.MakeScope.ScriptValue('te_inh_concentration_target')|0]"
 te_nation_wc_row_tt:0 "The score moves toward its target each year. The target's terms, and the most and least concentrated states, are in the Demographics tab of the Population panel."
 te_nation_wc_steady:0 "Steady"
```

- [ ] **Step 6: Check and commit**

Add the BOM to the two new files (`python3 -c "import sys,pathlib; [pathlib.Path(p).write_text('﻿'+pathlib.Path(p).read_text(encoding='utf-8'), encoding='utf-8') for p in sys.argv[1:]]" gui/te_nation_tab.gui common/script_values/te_nation_values.txt`), then run:

- `python3 organize_loc.py`, then `python3 organize_loc.py --check` (exit 0) and `python3 scripts/analysis/check_localization_files.py`;
- `.venv/bin/python -m unittest test_nation_tab test_te_systems_window 2>&1 | grep -E '^(Ran |OK|FAILED)'` (OK);
- `python3 scripts/analysis/check_gui_lint.py`: no errors (its "unproven" warnings are the vanilla copy's own data methods);
- `python3 gui_reference_audit.py --strict`, `python3 loc_render_audit.py --strict`, `python3 script_loc_reference_audit.py --strict`, `python3 loc_coverage_audit.py --strict`;
- `python3 scripts/format_paradox_tabs.py --check common/script_values/te_nation_values.txt`.

```bash
git add gui/te_nation_tab.gui common/script_values/te_nation_values.txt \
  localization/english/te_miscellaneous_l_english.yml test_nation_tab.py
git commit -m "Nation tab: the overview, the five sections and How the Nation Works"
```

---

### Task 4: The docs

**Files:** `docs/guides/gui_modding_guide.md` (CRLF), `docs/guides/gui_style_guide.md`, `docs/systems/mod_systems.md`, `docs/guides/vanilla_patch_runbook.md`, `CLAUDE.md`

- [ ] **Step 1: The GUI guide's file table** (`test_tax_code_bypass.py`'s `test_the_overrides_are_registered` fails until every top-level `.gui` is listed and the count line is right)

The file is CRLF: make these three edits with `Edit`, or with a script that reads and writes bytes.

- "Currently 41 GUI files at the top of `gui/`: 27 full-file replacements of vanilla panels plus 14 additive files" becomes "Currently 44 GUI files at the top of `gui/`: 27 full-file replacements of vanilla panels plus 17 additive files".
- First row of the table, before `add_consumption_tax_menu.gui`:
  `| \`00_te_country_panel_information.gui\` | (additive file, redefines vanilla's \`country_panel_information_content\`) | The country panel's Information tab, its MODIFIERS list hiding what the Nation tab shows (\`using = te_nation_hidden_filter\` on the item, \`ignoreinvisible\`, header and list shown on \`gui_country_hidden_modifier_count\`). Generated by \`scripts/generators/gen_nation_tab.py\` from \`test_fixtures/vanilla_gui/country_panel.gui\`; only its three \`### MOD: Nation tab\` blocks differ from vanilla (\`test_nation_tab.py\`). Gotcha #30: which definition wins is a play-test check, and the fallback is a full-file \`country_panel.gui\` |`
- Before `te_seabed_widgets.gui`:
  `| \`te_nation_generated.gui\` | (additive, generated templates) | The Nation tab's name filters: \`te_nation_hidden_filter\` for the country panel's list, \`te_nation_list_<section>\` and \`te_nation_row_<row>\` for the tab; regenerate with \`scripts/generators/gen_nation_tab.py\` |`
  `| \`te_nation_tab.gui\` | (additive, type library) | The Nation tab of the Timeline Extended window: the overview, five sections (each its score rows, then its list of the country's own permanent modifiers) and How the Nation Works, instanced from \`te_systems_window.gui\` |`
- In the `te_systems_window.gui` row, "with a tab each for the Space Race, the Colonial Empire and Grand Monuments (the entries' composers under `GetPlayerJournalEntry`)" becomes "Nation first (always open; `te_nation_tab.gui`), then a tab each for the Space Race and Grand Monuments, and on a second strip the Colonial Empire and the Seabed (the entries' composers under `GetPlayerJournalEntry`)".

Then gotcha #30's "Untested: which of two definitions wins" gains: "The mod's first is `00_te_country_panel_information.gui` (the Nation tab); the play-test answers it." Check: `grep -c $'\r$' docs/guides/gui_modding_guide.md` equals `wc -l`.

- [ ] **Step 2: The style guide's rule 9** (`docs/guides/gui_style_guide.md`)

After the bullet "The tab is **greyed until the system's journal entry is active**…", add: "*(owner, 2026-10-17)* **The Timeline Extended window's Nation tab is the one tab with no system behind it**: always open and first, never greyed, so the window opens there unless an open system tab was the last chosen."

- [ ] **Step 3: The systems doc** (`docs/systems/mod_systems.md`)

A section `## Nation Tab` after the Timeline Extended window's notes: what the tab shows (overview, sections, rows, lists), the registry and its five kinds, the three generated files, how to add a permanent modifier (one registry line, rerun, `test_nation_tab.py`), the country panel's filter and its fallback, and the judgment calls of Review Focus 5. Keep it to the length of its neighbours.

- [ ] **Step 4: The vanilla patch runbook** (`docs/guides/vanilla_patch_runbook.md`)

In § 5, after the at-risk loop: "**A type redefinition is not a same-path override**, so the loop can't see it. `gui/00_te_country_panel_information.gui` redefines one type of vanilla's `country_panel.gui`: when vanilla changed that file, replace `test_fixtures/vanilla_gui/country_panel.gui` with the new one and run `python3 scripts/generators/gen_nation_tab.py`. The generator raises if vanilla moved a line its blocks hook onto, and `test_nation_tab.py` fails while the fixture differs from the installed game."

- [ ] **Step 5: CLAUDE.md** (Editing conventions, one line)

"- **A static modifier script adds without a duration needs a line in `scripts/generators/gen_nation_tab.py`'s registry** (a Nation tab section, a row, `KEEP_IN_LIST` or `NOT_ON_COUNTRY`), then a rerun of the generator; `test_nation_tab.py` names any that has none."

- [ ] **Step 6: Commit**

```bash
git add docs/guides/gui_modding_guide.md docs/guides/gui_style_guide.md docs/systems/mod_systems.md \
  docs/guides/vanilla_patch_runbook.md CLAUDE.md
git commit -m "Nation tab: the GUI guide's table, the style rule's exception, the systems doc and the runbook"
```

---

### Task 5: The player guide

**Files:** `docs/player_guide/01-introduction.md`, `06-politics.md`, `03-economy.md`, `Vic3TimelineExtended_Player_Guide.pdf`

- [ ] **Step 1: A section on the tab** (after "Reading the Budget breakdown")

```diff
diff --git a/docs/player_guide/01-introduction.md b/docs/player_guide/01-introduction.md
index 1127c39..0dcb7c4 100644
--- a/docs/player_guide/01-introduction.md
+++ b/docs/player_guide/01-introduction.md
@@ -137,6 +137,29 @@ list. Expanding a group preserves the chart total, including when costs and
 refunds offset each other inside that group. Open
 How the Breakdown Works at the bottom for the accounting details.
 
+## The Nation tab
+
+The Timeline Extended window opens from the button under the sidebar's Map List,
+on its Nation tab. The tab gathers what your country carries for good, and it is
+open in every game from the first day.
+
+At the top, four boxes: your Legislative Override Capacity with the strongest
+Forceful Legislation option it opens, Wealth Concentration and the score it is
+heading for, Construction Cost, and Global Technology.
+
+Below them are five sections: Governance, Society, Economy, Science and Space,
+and International. Each starts with its scores, then lists the permanent effects
+the mod's systems have given your country, such as agricultural diffusion, space
+race milestones, demographic policies and the UN conventions you are bound by.
+Hover an effect to see what it does at its current size. Legislative Override
+Capacity's figure names every source on hover, and the lines on its bar mark
+where Forceful Legislation's options open, at 0, 2 and 4.
+
+The Modifiers list in the country panel's Information tab leaves these effects
+out, and keeps the timed ones and what events have just done to you. A system's
+weekly costs are in the Budget panel's Breakdown tab. Tooltips that break down a
+figure, such as legitimacy, still name every source.
+
 ## How the guide is organized
 
 The chapters follow the game's own areas rather than the order systems appear.
```

- [ ] **Step 2: Pointers where the guide already covers a row**

`06-politics.md`, Forceful Legislation:

```diff
diff --git a/docs/player_guide/06-politics.md b/docs/player_guide/06-politics.md
index 6085383..42095b8 100644
--- a/docs/player_guide/06-politics.md
+++ b/docs/player_guide/06-politics.md
@@ -411,6 +411,7 @@ When you start enacting any law, the **Forceful Legislation** event offers to
 bypass the legislature, if your authority income covers the cheapest option.
 What it allows depends on your **Legislative Override Capacity**, summed from
 your laws, your institutions and a few technologies and power bloc principles.
+The [Nation tab](01-introduction.md#the-nation-tab) shows it with every source.
 Among the laws, Autocracy and Single-Party State give 3, Algorithmic Governance
 2 and Unitary State 1; Universal Suffrage, Anarchy and Traditional Vassalage
 take away 3, and Guaranteed Liberties, Devolved Administration and Communal
```

`03-economy.md`, Construction Cost Scaling:

```diff
diff --git a/docs/player_guide/03-economy.md b/docs/player_guide/03-economy.md
index f482397..d371e1b 100644
--- a/docs/player_guide/03-economy.md
+++ b/docs/player_guide/03-economy.md
@@ -235,7 +235,9 @@ the same scaling raises the cost of the materials your construction uses
 instead.
 
 This is a catch-up mechanic: a rich country needs more construction for each
-building and each level of upkeep, while a poor country builds cheaply.
+building and each level of upkeep, while a poor country builds cheaply. The
+[Nation tab](01-introduction.md#the-nation-tab) shows the current scaling, and
+below it any excess private construction in force.
 
 ### Excess private construction
 
```

- [ ] **Step 3: Lint, rebuild, commit**

Run `python3 scripts/analysis/check_player_guide_style.py --strict` (0 findings), then `.venv/bin/pip install -r requirements-docs.txt` if pandoc and Typst are missing, `.venv/bin/python scripts/build_player_guide.py`, and `.venv/bin/python scripts/build_player_guide.py --check`.

```bash
git add docs/player_guide/
git commit -m "Player guide: the Nation tab"
```

---

### Task 6: The play-test list

**Files:** Create `docs/testing/nation-tab-playtest.md`

- [ ] **Step 1: Write the list**

Spec § 8's facts, each with what to look at and its fallback:

1. **The redefinition wins.** The country panel's Information tab: MODIFIERS no longer lists Agricultural Diffusion, the space race's milestones, a demographic measure, the Construction Cost Scaling modifier; it still lists a timed one (Forceful Legislation's decaying penalty after forcing a law) and Nuclear Power. The rest of the tab is unchanged. Fallback: a full-file `country_panel.gui` (spec § 3).
2. **The header**: a country whose every modifier is hidden shows no MODIFIERS header.
3. **The lists**: each section lists only its own modifiers (the blockoverride-pasted template), each hover renders the modifier's tooltip at its current scale (Great Family Fortunes matches the country panel's Modifiers tab).
4. **The breakdown**: Legislative Override Capacity's figure lists the laws, institutions and the decaying penalty on hover.
5. **The bar and lines**: the fill sits at (capacity + 6) / 14; each line's hover names its option.
6. **Selection**: the window opens on Nation; choosing Space Race and reopening returns there; with the tax probes armed, the tax tab still selects.
7. **The launcher** shows with every system rule off.
8. **Parsing**: `error.log` has no GUI error for `te_nation_generated.gui` (a 20,000-character `visible`).
9. **Performance**: no stutter with the Information tab open on a late-game country.

- [ ] **Step 2: Commit**

```bash
git add docs/testing/nation-tab-playtest.md
git commit -m "Nation tab: the play-test list"
```

---

### Task 7: Validation

- [ ] **Step 1: Everything CI runs**, with the dummy env:

- `.venv/bin/python -m compileall -q .` and the full suite, `.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/suite.log 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/suite.log`;
- `.venv/bin/ruff check .`;
- the tab check over `common/` and `events/` as `ci.yml` builds it;
- `scripts/analysis/check_localization_files.py`, `organize_loc.py --check`, `scripts/analysis/check_post_load_rosters.py`, `scripts/analysis/check_dds_dimensions.py` (no textures added);
- `scripts/analysis/check_player_guide_style.py --strict`, `scripts/build_player_guide.py --check`;
- the twenty-eight audits in their CI modes (`--strict`; `kill_character_audit --check`; `attitude_key_audit` bare).

- [ ] **Step 2: The PR body** names the play-test list, Review Focus 5's judgment calls for the owner, and "Player guide: 01-introduction (The Nation tab), 06-politics, 03-economy".

---

## Part 2 (phase 2, its own PR): Wealth Concentration in the state view

> Built 2026-10-17 (branch `feat/state-panel-seabed-wealth`) as a tile of its own in the state panel's status
> grid, `te_state_wealth_tile`, gated on `gui_state_wealth_modifier_count`, not in the Demographics subtab's Wealth
> section: that subtab is gone while the Demographics rule is off (its default), and the six run regardless, so
> Task 8's list there would have hidden them from the player. Task 8's test and filter steps were followed.

### Task 8: The state's inheritance modifiers in its Wealth section

**Files:**
- Modify: `gui/states_panel.gui` (both rows' filters), `common/script_values/gui_chart_script_values.txt` (`gui_state_hidden_modifier_count`), `gui/te_demographics_widgets.gui` (`te_state_demog_wealth`), `test_hidden_state_modifiers.py`

The state view's Demographics subtab already has a Wealth section: the Gini, then for a scored state its Wealth Concentration and a bar heading for its target. Under them goes a list of the state's own modifiers from the score (`inh_concentrated_property`, `inh_dispersed_property`, `inh_land_hunger`) and the law (`inh_forced_heirship_rural`, `inh_primogeniture_rural`, `inh_undivided_farm_rural`), each with its tooltip, outside the scored part's gate. The state panel's two rows hide the six, and the condensed view's count counts them.

- [ ] **Step 1: Teach the test the card's own list**

```diff
diff --git a/test_hidden_state_modifiers.py b/test_hidden_state_modifiers.py
index 4dd58b0..fcf7d25 100644
--- a/test_hidden_state_modifiers.py
+++ b/test_hidden_state_modifiers.py
@@ -49,6 +49,16 @@ SHOWN_ON_A_CARD_PREFIXES = (
     "gm_local_",
 )
 
+# State modifiers the state view's Demographics subtab shows by name, in its
+# Wealth section (te_state_demog_wealth, gui/te_demographics_widgets.gui): what
+# wealth concentration and the inheritance law do in the state. By name, not by
+# an `inh_` prefix, which would also catch the country's own inheritance
+# modifiers.
+SHOWN_ON_A_CARD_NAMES = (
+    "inh_concentrated_property", "inh_dispersed_property", "inh_land_hunger",
+    "inh_forced_heirship_rural", "inh_primogeniture_rural", "inh_undivided_farm_rural",
+)
+
 DATAMODEL = 'datamodel = "[State.GetTimedModifiers]"'
 
 
@@ -172,7 +182,7 @@ def _hidden_modifiers():
     ones a card already shows."""
     return {name for name, icons in _static_modifiers().items()
             if any(icon in HIDDEN_ICONS for icon in icons)
-            or name.startswith(SHOWN_ON_A_CARD_PREFIXES)}
+            or name.startswith(SHOWN_ON_A_CARD_PREFIXES) or name in SHOWN_ON_A_CARD_NAMES}
 
 
 def _count_terms():
@@ -190,7 +200,11 @@ def _count_terms():
 
 class HiddenStateModifierTest(unittest.TestCase):
     def setUp(self):
-        self.sites = _sites()
+        # A card's own list picks its modifiers out (`visible = "[Or(...)]"`);
+        # the rows leave the hidden ones out (`visible = "[Not(...)]"`).
+        sites = _sites()
+        self.cards = [s for s in sites if not re.search(r'visible\s*=\s*"\[Not\(', s["item"])]
+        self.sites = [s for s in sites if s not in self.cards]
 
     def test_both_state_panel_rows_are_found(self):
         # The full view's row over the state's picture and the condensed view's box.
@@ -204,6 +218,21 @@ class HiddenStateModifierTest(unittest.TestCase):
             with self.subTest(prefix=prefix):
                 self.assertTrue([name for name in hidden if name.startswith(prefix)])
         self.assertIn("gm_local_tourism", hidden)
+        statics = _static_modifiers()
+        for name in SHOWN_ON_A_CARD_NAMES:
+            self.assertIn(name, statics)
+            self.assertIn(name, hidden)
+
+    def test_card_lists_pick_out_only_card_modifiers(self):
+        # te_state_demog_wealth lists the six by name
+        self.assertTrue(self.cards)
+        for site in self.cards:
+            with self.subTest(site=site["where"]):
+                visible = re.findall(r'visible\s*=\s*"([^"]*)"', site["item"])
+                self.assertEqual(len(visible), 1)
+                named = set(re.findall(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)", visible[0]))
+                self.assertEqual(named, set(SHOWN_ON_A_CARD_NAMES))
+                self.assertRegex(site["own"], r"\bignoreinvisible\s*=\s*yes\b")
 
     def test_every_row_hides_every_hidden_modifier_by_name(self):
         hidden = _hidden_modifiers()
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m unittest test_hidden_state_modifiers 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: FAILED (the six are not in the rows' filters, and there is no card list).

- [ ] **Step 3: Edit the three files**

Save this one-off script outside the repository and run it from the root, `python3 /path/to/apply_state_wealth.py .`. It rebuilds both rows' filters with the six added in sorted order (their right-nested form), appends six terms to the count, and inserts the list after the Wealth section's bar.

```python
"""Phase 2 (plan Task 8): hide the six inheritance state modifiers from the
state panel's rows and show them in the state Demographics subtab's Wealth
section."""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
SIX = ["inh_concentrated_property", "inh_dispersed_property", "inh_land_hunger",
       "inh_forced_heirship_rural", "inh_primogeniture_rural", "inh_undivided_farm_rural"]
TERM = "EqualTo_string(TimedModifier.GetName, Localize('{}'))"


def chain(names):
    """The state panel's right-nested form: Or(a, Or(b, ... Or(y, z)))."""
    out = TERM.format(names[-1])
    for name in reversed(names[:-1]):
        out = f"Or({TERM.format(name)}, {out})"
    return out


# 1. Both state rows' filters gain the six, sorted as the rest are.
path = root / "gui" / "states_panel.gui"
text = path.read_text(encoding="utf-8-sig")
pattern = re.compile(r'visible = "\[Not\((Or\(EqualTo_string\(TimedModifier\.GetName, Localize.*?)\)\]"')
found = 0


def widen(m):
    global found
    found += 1
    names = re.findall(r"Localize\('(\w+)'\)", m.group(1))
    assert not set(SIX) & set(names)
    return f'visible = "[Not({chain(sorted(names + SIX))})]"'


text = pattern.sub(widen, text)
assert found == 2, found
path.write_text("﻿" + text, encoding="utf-8", newline="\n")

# 2. The condensed view's count.
path = root / "common" / "script_values" / "gui_chart_script_values.txt"
text = path.read_text(encoding="utf-8-sig")
start = text.index("gui_state_hidden_modifier_count = {")
end = text.index("\n}\n", start)
terms = "".join(f"\tif = {{\n\t\tlimit = {{ has_modifier = {name} }}\n\t\tadd = 1\n\t}}\n" for name in SIX)
text = text[:end + 1] + terms + text[end + 1:]
path.write_text("﻿" + text, encoding="utf-8", newline="\n")

# 3. The Wealth section shows them: after the scored part, outside its gate
# (the law's three can stand on a state the census hasn't scored).
path = root / "gui" / "te_demographics_widgets.gui"
text = path.read_text(encoding="utf-8-sig")
section = text.index("\ttype te_state_demog_wealth = flowcontainer {")
anchor = text.index("\t\t\t\t\t\ttooltip = \"te_demog_wc_line_tt\"\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n", section)
anchor = text.index("\t\t\t}\n", anchor + len("\t\t\t\t\t\ttooltip = \"te_demog_wc_line_tt\"\n\t\t\t\t\t}\n\t\t\t\t}\n")) + len("\t\t\t}\n")
names = sorted(SIX)
expr = TERM.format(names[-1])
for name in reversed(names[:-1]):
    expr = f"Or({TERM.format(name)}, {expr})"
block = f"""
\t\t\t### What concentration and the inheritance law do in this state (Nation tab
\t\t\t### spec § 5): the state's own modifiers, each its tooltip on hover. The
\t\t\t### state panel's rows hide the same six (states_panel.gui,
\t\t\t### test_hidden_state_modifiers.py's SHOWN_ON_A_CARD_NAMES).
\t\t\tflowcontainer = {{
\t\t\t\tdatamodel = "[State.GetTimedModifiers]"
\t\t\t\tdirection = vertical
\t\t\t\tignoreinvisible = yes
\t\t\t\tspacing = 4
\t\t\t\tmargin_top = 4

\t\t\t\titem = {{
\t\t\t\t\tflowcontainer = {{
\t\t\t\t\t\tvisible = "[{expr}]"
\t\t\t\t\t\tspacing = 10
\t\t\t\t\t\tminimumsize = {{ 480 -1 }}
\t\t\t\t\t\ttooltip = "[TimedModifier.GetTooltip]"

\t\t\t\t\t\ticon = {{
\t\t\t\t\t\t\ttexture = "[TimedModifier.GetIcon]"
\t\t\t\t\t\t\tsize = {{ 25 25 }}
\t\t\t\t\t\t}}
\t\t\t\t\t\ttextbox = {{
\t\t\t\t\t\t\ttext = "[TimedModifier.GetName]"
\t\t\t\t\t\t\tautoresize = yes
\t\t\t\t\t\t\talign = nobaseline
\t\t\t\t\t\t\tparentanchor = vcenter
\t\t\t\t\t\t\tusing = fontsize_medium
\t\t\t\t\t\t}}
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}}
"""
text = text[:anchor] + block + text[anchor:]
path.write_text("﻿" + text, encoding="utf-8", newline="\n")
print("ok")
```

- [ ] **Step 4: Run the tests and checks**

Run: `.venv/bin/python -m unittest test_hidden_state_modifiers test_nation_tab 2>&1 | grep -E '^(Ran |OK|FAILED)'` (OK), the demographics tests (`.venv/bin/python -m unittest $(ls test_demographics*.py | sed 's/\.py$//')`), `python3 scripts/analysis/check_gui_lint.py` (no errors), `python3 gui_reference_audit.py --strict`, and the tab check on `gui_chart_script_values.txt`.

- [ ] **Step 5: Commit**

```bash
git add gui/states_panel.gui common/script_values/gui_chart_script_values.txt gui/te_demographics_widgets.gui \
  test_hidden_state_modifiers.py
git commit -m "State view: the state's inheritance modifiers in its Wealth section, hidden from the rows"
```

### Task 9: Phase 2's docs, guide, play-test and validation

- [ ] `docs/systems/mod_systems.md`: the Wealth section's new list in the Demographics state view notes, and the six in the hidden-modifier notes (the dynamic-modifier pattern's step 6).
- [ ] `docs/player_guide/08-states.md`: one sentence where the state's Demographics subtab is described: "Its Wealth section also lists what concentration and the inheritance law do in that state, which the state's modifier icons no longer repeat." Lint and rebuild as Task 5.
- [ ] `docs/testing/nation-tab-playtest.md`: a scored and an unscored state show their lines; a state carrying Land Hunger shows it in the Wealth section and not among its modifier icons; the condensed view's box fades when the six are all it carries.
- [ ] Task 7's validation, then a PR of its own.
