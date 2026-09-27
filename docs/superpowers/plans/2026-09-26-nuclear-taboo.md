# The Nuclear Taboo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A world "nuclear taboo" score (0–100). It moves toward an equilibrium set by the state of the world, is knocked down by use and eroded by threats, and scales every nuclear cost, up to making possession itself a burden. It feeds the AI, and it comes with unilateral disarmament, arsenal reduction and (phase 2) arms control.

**Architecture:** This copies UN authority's equilibrium model (`common/script_values/un_authority_values.txt`):
- named target parts are snapshotted into globals by one world-level monthly step (a global `on_monthly_pulse`, never the UN's);
- the score closes a fraction of the gap each month;
- acts write a decaying ledger, and a nuclear use also shocks the score at once.

Everything that must run with ROOT = a country (modifiers with `multiplier = root.var:…`, the exits, the history samples) runs from `je_nuclear_program`'s own monthly pulse. From the taboo's birth that entry is active for every country.

**Tech Stack:** Victoria 3 Paradox script (`common/`, `events/`, `gui/`, `localization/`); Python 3.11/3.12 `unittest` static checks; a Python simulator under `scripts/analysis/`.

**Spec:** `docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md` (read it first; this plan argues from it). Background: `docs/systems/nuclear_crisis_design.md` §0, `docs/systems/mod_systems.md` § Nuclear Weapons, `docs/guides/scripting_best_practices.md` § "`add_modifier { multiplier = var:X }` Resolves Against ROOT".

**Where:** the sparse worktree `/home/jakef/src/Vic3TE-nuclear-taboo`, branch `nuclear-taboo`. Run every command from there. Never `/reload` the main server from here; the final task starts a second server on port 8951 from the worktree.

## Global Constraints

- The nuclear system must work with the UN, covert-warfare and world-war systems disabled. Nothing here may run only when `un_founded` is set, except the Phase 2 UN part.
- Everything is gated on the game rule `nuclear_weapons_enabled`.
- Brace-based Paradox files use **tab** indentation. Run `python3 scripts/format_paradox_tabs.py <files>` on every `.txt`/`.gui` you create or edit, never on `.yml`/`.py`/`.md`.
- Every **new** file under `common/`, `events/`, `gui/` and every `.yml` starts with a UTF-8 BOM (`\xef\xbb\xbf`). New `.yml` files are not needed: add keys to the existing files named in each task.
- Loc keys use the format ` key:0 "text"` (one leading space). Use `#v … #!`, `#R … #!`, `#G … #!`, `#bold … #!`, `#lore … #!`, `#tooltip_header … #!`. **Never** `[b]…[/b]`.
- Every new loc-bearing key for static modifiers, the decision, event options, tooltips and panel breakdown lines starts with **`nd_taboo_`**. Task 1 adds an `organize_loc.py` rule filing that family whole in MISCELLANEOUS. Keys for widget rows in `nuclear_program_widget.gui` start with `je_nuclear_program_widget_taboo_` (JOURNAL_ENTRIES, like their neighbours). Event text keys are `nuclear_taboo.N.t/.d/.f` (EVENTS). No new key may contain the substrings `event`, `diplo`, `_subject_` or `pact`, or end in `_add` or `_mult`: `organize_loc.py` routes those elsewhere.
- **ROOT rule:** an `add_modifier` with `multiplier = root.var:X` runs only where ROOT is the modified country: the entry's pulses, a country event, a decision or a scripted GUI. It never runs from the global pulse (ROOT is none there, and the engine silently uses 1.0).
- **Multiplier variables are never removed** (`modifier_multiplier_var_audit`): `nd_taboo_burden_cached`, `nd_taboo_renounce_mult`, `nd_taboo_civil_defence_cost_cached`.
- **Single writers:** only the effects in `common/scripted_effects/nuclear_taboo_effects.txt` write `global_var:nd_taboo`, `global_var:nd_taboo_ledger`, `global_var:nd_taboo_quiet_years` or the part snapshots. Every writer is a no-op before the taboo is born (`has_global_variable = nd_taboo`).
- **The band events' options never write the global score** (the UN redesign's lesson: 200 countries nudging one number). They are country-local. An option that enacts a real system action (adopting No First Use, beginning to dismantle) carries that action's own effect. The Assembly's verdict (Task 13) is the one event option that moves the score by design: it is the world's act.
- Any option or effect that changes a number the UI shows prints it in a `custom_tooltip` (`silent_variable_audit`).
- `debug_log` strings: plain text, or `[SCOPE.ScriptValue('x')|N]` only. **No `$PARAM$` inside a `debug_log` string** (`scripting_best_practices.md` § "Runtime Debugging with `debug_log`").
- Python: f-strings must not reuse their own quote inside `{}` (CI runs 3.11). Check with `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`.
- `docs/systems/journal_entry_systems.md` is **CRLF**. Edit it with the Edit tool only, then confirm `grep -c $'\r$' docs/systems/journal_entry_systems.md` still equals `wc -l docs/systems/journal_entry_systems.md`.
- Never `git commit -a`; stage by path. Every commit command below ends its message with the literal slot `<attribution lines>`: replace it with the attribution lines your session supplies (`Co-Authored-By: <your model> <noreply@anthropic.com>` and the `Claude-Session:` line), never commit the slot itself.
- **Anchors.** Every "replace X with Y" shows the target's text as it stands, indented with tabs. If an anchor fails to match, read the region and match its real whitespace; never loosen an anchor until it matches somewhere else.
- Tuning numbers are first values, from the spec. The one that is structurally required is that drift alone (base 20 + tradition cap 35) tops out at **55**.

## Review Focus

These are the five inputs most likely to bite a player that no happy-path test exercises. Each has its pinning test in the task named.

1. **The Budapest path books one renunciation, not two.** `nd_bp_accept` may put a `nuclear_disarmament` article in force (whose `on_entry_into_force` notes the renunciation) and then zero the stockpile itself. `nd_taboo_note_renunciation` must refuse a country already renounced and unarmed. *Test in Task 7:* `test_renunciation_is_idempotent_and_read_before_zeroing`.
2. **A save that is already in the nuclear age** wakes at its equilibrium, not at 20 with no tradition. The clock is seeded from the world's first device when nothing was ever used. *Test in Task 1:* `test_existing_world_is_seeded_from_the_first_device`; *sim test in Task 2:* `test_seeded_quiet_world_starts_near_its_target`.
3. **Retaliation is told from first use without reading a role-named scope that callers swap.** `nuclear_response_*` always pass the literal `RETALIATION = yes`. `nuclear_first_strike` and `nd_tactical_strike_resolve` test `nd_was_struck_by`, which needs a war (every dispatch is inside one). *Tests in Task 3:* `test_response_strikes_are_retaliation_by_construction`, `test_first_strikes_ask_whether_they_answer_a_strike`, `test_dispatch_is_always_at_war`.
4. **A ceiling lifted or raised while the programme is held** must release the hold at once, not a month later. *Test in Task 7:* `test_every_ceiling_change_refreshes_the_hold`.
5. **A score sitting on a band boundary** must not fire the band event every month. The hysteresis is ±2, and each boundary-and-direction fires at most once in ten years. *Tests in Task 2* (`test_band_events_do_not_flap`) *and Task 10* (`test_band_check_uses_hysteresis_and_cooldown`).

## Deviations from the spec (decided while planning; say so in the PR)

- **Static-modifier names** carry the `nd_taboo_` loc prefix: `nd_taboo_renounced` (spec: `nd_renounced_modifier`), `nd_taboo_programme_held` (`nd_programme_held_modifier`), `nd_taboo_renunciation_prestige` (`nd_renunciation_prestige`), `nd_taboo_civil_defence` (`nd_civil_defence_modifier`). This lets `organize_loc.py` file each name with its `_desc`.
- **The possession cost is added once and its multiplier re-read live.** The engine re-evaluates `multiplier = root.var:X` on later ticks, which is exactly how `nd_upkeep_cost` works, so the monthly refresh only updates `nd_taboo_burden_cached` and adds or removes the modifier at the 0 boundary. The spec said "removed and re-added each month". It also uses `has_modifier` rather than a tracker variable, because it has one caller per month and self-heals after a revolution.
- **No chart markers.** The history store's pips are shared by every system on the month's container. The UN and global-warming charts hide them (`blockoverride "marker_pips" {}`) for this reason. The panel shows the year of the last use instead.
- **Tactical first use** costs world-reaction relations at 0.4× the strategic figure (−0.16 × taboo), the infamy ratio. The spec gave the strategic figure only.
- **Retaliation through the strike actions** now costs no infamy (it cost 25 through `nuclear_first_strike` before). The spec's table: "Retaliation's infamy: none — it is licensed."
- **The strike confirmation** gains a line naming the infamy, because `nuclear_first_strike` hides its `change_infamy` inside a custom tooltip. It sits in the actions' `accept_effect`, where `scope:target_country` exists in the preview.
- **The leaderboard** (`update_nuclear_powers_ranking`, an `ordered_country` sweep) moves from every active country's weekly pulse to the world's monthly step. Otherwise making the entry active for everyone would run it about 200 times a week.
- **The world-reaction relations are applied at the detonation sites** (`nuclear_first_strike`'s success branch, `nd_tactical_strike_resolve`'s), not in `nd_record_nuclear_use` as the spec's §4.1 put it. So they follow a successful detonation only, beside the infamy they accompany. `nd_record_nuclear_use` runs before the dice and cannot tell strategic from tactical.
- **The entry-close fallbacks are kept, not re-keyed.** Spec §6.1 said every `NOT = { has_journal_entry = je_nuclear_program }` branch in `nd_country_monthly_cleanup` is re-keyed on `nd_is_armed` or removed. The plan keeps both: the domestic-stance clean-up and the custody-record refresh for a country without the entry. They remain right for a world where the entry never activated (the rule off, before the first warhead). The unarmed case they used to cover is handled by the entry's own pulses, which Task 5's tests pin, and the test whitelists exactly those two branches. The weekly disarmament block, which the rule missed because it isn't keyed on `has_journal_entry`, is fixed in Task 5.
- **Phase 2 walk-outs are booked for every party whose lowest treaty ceiling rose.** The monthly check cannot tell who withdrew, and the end of an arms-control regime erodes the norm whoever ended it. It is not booked when the partner no longer exists.

## File map

| File | Status | Responsibility |
|---|---|---|
| `common/script_values/nuclear_taboo_values.txt` | new | every constant (the simulator parses them), the parts, the target and step, costs, possession, AI factors, display values |
| `common/scripted_effects/nuclear_taboo_effects.txt` | new | birth, seed, world step, snapshot, the writers, use/renunciation notes, the country half, exits, AI arsenal review, band events, option bodies, history, debug setter |
| `common/scripted_triggers/nuclear_taboo_triggers.txt` | new | dismantling/held/former-state tests, gates, AI judgements, band due/cooldown |
| `common/on_actions/nuclear_taboo_on_actions.txt` | new | the global monthly pulse |
| `common/static_modifiers/nuclear_taboo_modifiers.txt` | new | the six taboo modifiers |
| `events/nuclear_taboo_events.txt` | new | `nuclear_taboo.1`–`.8` (band crossings), `.20` (the last warhead) |
| `common/treaty_articles/117_nuclear_arms_limitation.txt` | new (phase 2) | the arms-control article |
| `test_nuclear_taboo.py` | new | static consistency checks + simulator tests |
| `scripts/analysis/nuclear_taboo_sim.py` | new | the monthly model, scenarios, band events |
| `organize_loc.py` | edit | file `nd_taboo_*` whole |
| `common/scripted_effects/nuclear_weapon_effects.txt` | edit | birth at the first warhead; status codes 4/5 |
| `common/journal_entries/je_nuclear_program.txt` | edit | leaderboard off the weekly pulse; the country monthly call; comments |
| `common/scripted_effects/extra_effects.txt` | edit | strike detonation sites: use notes, scaled infamy, world reaction |
| `common/scripted_effects/nuclear_deterrence_effects.txt` | edit | tactical resolve, doctrine wrappers, pledges, law binding, readiness hold, AI review hook |
| `common/scripted_effects/nuclear_crisis_effects.txt` | edit | crisis open/go-public ledger, preview infamy, stand-down, the pressure part |
| `common/script_values/nuclear_deterrence_values.txt` | edit | `nd_yp_taboo_value`, `nd_ig_term_possession_value` |
| `common/scripted_triggers/nuclear_deterrence_triggers.txt` | edit | readiness gate, AI use and ultimatum gates |
| `common/scripted_triggers/nuke_triggers.txt` | edit | the entry applies to everyone once the taboo exists |
| `common/scripted_effects/nuclear_custody_effects.txt` | edit | renunciation at `nd_cw_dismantle_as`, `nd_bp_accept` |
| `common/scripted_effects/nuclear_loose_effects.txt` | edit | terror detonation ledger |
| `common/treaty_articles/extra_treaty_articles.txt` | edit | disarmament article: renunciation, AI acceptance |
| `common/diplomatic_actions/nuke.txt` | edit | strike confirmation lines; AI evaluation factor |
| `common/script_values/extra_script_values.txt` | edit | desired stockpile × taboo |
| `common/scripted_buttons/nuclear_program_buttons.txt` | edit | proliferation restraint |
| `common/decisions/extra_decisions.txt` | edit | Resume the Nuclear Programme |
| `common/script_values/zz_te_war_support_injections.txt` | edit | civil defence halves the nuclear shadow |
| `common/scripted_guis/nuclear_deterrence_sguis.txt`, `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` | edit | ops 60–64 and the Arsenal rows |
| `common/scripted_guis/nuclear_program_sguis.txt`, `gui/journal_entry_widgets/nuclear_program_widget.gui` | edit | the taboo panel, breakdown, chart |
| `common/customizable_localization/nuclear_program_custom_loc.txt` | edit | status line, band name, heading, burden hint, rate note |
| `events/te_debug_nuclear_events.txt` | edit | `te_debug_nuclear.3` |
| `events/un_vote_events.txt`, `common/scripted_effects/un_docket_effects.txt` | edit (phase 2) | the Assembly's verdict |
| `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml`, `te_journal_entries_l_english.yml`, `te_concepts_l_english.yml` | edit | loc |
| `test_nuclear_deterrence.py` | edit | pressure parts, IG vars, go-public pin |
| `docs/systems/nuclear_crisis_design.md`, `docs/systems/mod_systems.md`, `docs/systems/journal_entry_systems.md`, `docs/README.md` | edit | what shipped |

Run a single test file with `python3 -m unittest test_nuclear_taboo -v`. It needs no Victoria 3 install.

---

## Phase 1

### Task 1: The score core

**Files:**
- Create: `common/script_values/nuclear_taboo_values.txt`
- Create: `common/scripted_effects/nuclear_taboo_effects.txt`
- Create: `common/on_actions/nuclear_taboo_on_actions.txt`
- Create: `common/scripted_triggers/nuclear_taboo_triggers.txt`
- Create: `test_nuclear_taboo.py`
- Modify: `common/scripted_effects/nuclear_weapon_effects.txt` (the first-warhead branch)
- Modify: `common/journal_entries/je_nuclear_program.txt` (weekly pulse)
- Modify: `organize_loc.py` (`categorize_key`)

**Interfaces:**
- Produces globals: `nd_taboo`, `nd_taboo_target`, `nd_taboo_ledger`, `nd_taboo_quiet_years`, `nd_taboo_band`, `nd_tb_base`, `nd_tb_tradition`, `nd_tb_postures`, `nd_tb_restraint`, `nd_tb_ledger`.
- Produces script values (any scope unless noted):
  - `nd_taboo_value`: the score, or 20 before birth;
  - `nd_taboo_rank_weight`: country;
  - `nd_taboo_stance_value`: country;
  - `nd_taboo_part_{tradition,postures,restraint}_value`, `nd_taboo_target_sum`, `nd_taboo_step_value`;
  - `nd_taboo_band_value` (1..5);
  - `nd_taboo_line_{fragile,established,strong,absolute}` (30/50/70/90);
  - `nd_disp_taboo`, `nd_disp_taboo_target`, `nd_disp_tb_{base,tradition,postures,restraint,ledger}`, `nd_disp_taboo_quiet_years`.
- Produces effects:
  - `nd_taboo_birth` (any scope, idempotent);
  - `nd_taboo_seed_existing_world`;
  - `nd_taboo_snapshot`;
  - `nd_taboo_monthly_update` (global);
  - `nd_taboo_ledger_add = { POINTS = <number | script value | var:X | global_var:X> }` (any scope);
  - `nd_taboo_ledger_add_weighted = { POINTS = … }` (the acting country's scope);
  - `nd_taboo_shock = { POINTS = … }` (any scope).
- Produces trigger: `nd_taboo_is_former_nuclear_state` (country), in `common/scripted_triggers/nuclear_taboo_triggers.txt`. Create that file here with a header and this one trigger.

- [ ] **Step 1: Write the failing tests**

Create `test_nuclear_taboo.py`:

```python
"""The nuclear taboo: the tables and single-writer rules that must agree.

The taboo (docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md) is one
world score moved by a monthly step and by writers scattered across the
nuclear files. Nothing in the engine checks that the parts the step snapshots
are the parts the target sums, that only the writers touch the score, or that
every path that gives an arsenal up books the renunciation once. Each test
pins one of those rules.

Run: python3 -m unittest test_nuclear_taboo -v
"""

import re
import sys
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, read, strip_comments

ROOT = Path(__file__).resolve().parent
TABOO_VALUES = ROOT / "common/script_values/nuclear_taboo_values.txt"
TABOO_EFFECTS = ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"
TABOO_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_taboo_triggers.txt"
TABOO_ON_ACTIONS = ROOT / "common/on_actions/nuclear_taboo_on_actions.txt"
WEAPON_EFFECTS = ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"

# The target's parts, in the order nd_taboo_target_sum adds them.
PARTS = ["base", "tradition", "postures", "restraint", "ledger"]
NEW_FILES = [TABOO_VALUES, TABOO_EFFECTS, TABOO_TRIGGERS, TABOO_ON_ACTIONS]


def script_files():
    for folder in ("common", "events"):
        yield from (ROOT / folder).rglob("*.txt")


class TestScoreCore(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.effects = strip_comments(read(TABOO_EFFECTS))
        self.on_actions = strip_comments(read(TABOO_ON_ACTIONS))

    def test_new_files_start_with_a_bom(self):
        for path in NEW_FILES:
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name)

    def test_snapshot_writes_every_part(self):
        body = block(self.effects, "nd_taboo_snapshot")
        for part in PARTS:
            self.assertIn(f"name = nd_tb_{part} value", body, part)
        self.assertIn("name = nd_taboo_target value = nd_taboo_target_sum", body)

    def test_target_sums_exactly_the_parts(self):
        body = block(self.values, "nd_taboo_target_sum")
        self.assertEqual(re.findall(r"(?:value|add) = global_var:nd_tb_(\w+)", body), PARTS)
        self.assertIn("min = 0", body)
        self.assertIn("max = 100", body)

    def test_drift_alone_tops_out_at_55(self):
        base = float(re.search(r"(?m)^nd_taboo_base = ([\d.]+)", self.values).group(1))
        cap = float(re.search(r"(?m)^nd_taboo_tradition_cap = ([\d.]+)", self.values).group(1))
        self.assertEqual(base + cap, 55)

    def test_only_the_writers_touch_the_score(self):
        writes = re.compile(r"name = (?:nd_taboo|nd_taboo_ledger|nd_taboo_quiet_years|nd_tb_\w+)\b"
                            r"(?= (?:value|add|subtract|multiply))")
        for path in script_files():
            if path == TABOO_EFFECTS:
                continue
            text = strip_comments(read(path))
            self.assertNotRegex(text, writes, path.relative_to(ROOT).as_posix())

    def test_every_writer_waits_for_the_birth(self):
        for name in ("nd_taboo_ledger_add", "nd_taboo_ledger_add_weighted", "nd_taboo_shock"):
            body = block(self.effects, name)
            self.assertIn("has_global_variable = nd_taboo", body, name)

    def test_world_step_runs_from_the_global_pulse_under_the_rule(self):
        pulse = block(self.on_actions, "on_monthly_pulse")
        self.assertIn("nd_taboo_monthly_on_action", pulse)
        body = block(self.on_actions, "nd_taboo_monthly_on_action")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", body)
        self.assertIn("nd_taboo_monthly_update = yes", body)
        self.assertNotIn("un_founded", self.on_actions)

    def test_world_step_applies_no_rooted_modifier(self):
        body = block(self.effects, "nd_taboo_monthly_update")
        self.assertNotIn("add_modifier", body)
        self.assertNotIn("root.var", body)

    def test_birth_is_called_at_the_first_warhead(self):
        text = strip_comments(read(WEAPON_EFFECTS))
        i = text.index("set_global_variable = { name = world_first_nuclear_weapon value = yes }")
        self.assertIn("nd_taboo_birth = yes", text[i:i + 200])

    def test_existing_world_is_seeded_from_the_first_device(self):
        body = block(self.effects, "nd_taboo_seed_existing_world")
        self.assertIn("has_global_variable = world_first_nuclear_weapon", body)
        self.assertIn("world_first_nuclear_weapon_used", body)
        self.assertIn("var:nuclear_program_first_device_year", body)
        self.assertIn("name = nd_taboo value = global_var:nd_taboo_target", body)
        update = block(self.effects, "nd_taboo_monthly_update")
        self.assertLess(update.index("nd_taboo_seed_existing_world = yes"), update.index("nd_taboo_snapshot = yes"))

    def test_leaderboard_runs_once_for_the_world(self):
        self.assertNotIn("update_nuclear_powers_ranking", strip_comments(read(JE)))
        self.assertIn("update_nuclear_powers_ranking = yes", block(self.effects, "nd_taboo_monthly_update"))

    def test_new_loc_family_is_filed_whole(self):
        sys.path.insert(0, str(ROOT))
        import organize_loc
        for key in ("nd_taboo_possession_cost", "nd_taboo_possession_cost_desc",
                    "nd_taboo_resume_programme_desc", "nd_taboo_tt_opt_cut", "nd_taboo_bd_ledger"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest test_nuclear_taboo -v`
Expected: errors (`FileNotFoundError` for `nuclear_taboo_values.txt`) and a failing `test_new_loc_family_is_filed_whole`.

- [ ] **Step 3: Create `common/script_values/nuclear_taboo_values.txt`**

Write the file with a leading BOM. The `﻿` before the first `#` in the block below stands for the three BOM bytes. If your editor drops it, prepend it afterwards with `printf '\xef\xbb\xbf' | cat - f > f.new && mv f.new f`.

```
﻿# ============================================================================
# THE NUCLEAR TABOO — script values
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md; what
# shipped: docs/systems/nuclear_crisis_design.md §0.11.
#
# One world score, global_var:nd_taboo (0-100): how unthinkable nuclear weapons
# are. It is born at 20 with the world's first warhead (nd_taboo_birth) and
# moves every month toward a TARGET, the sum of named parts that
# nd_taboo_monthly_update snapshots into globals (the UN authority model,
# un_authority_values.txt):
#
#   base         20          constant
#   tradition    0 .. +35    years without use (global_var:nd_taboo_quiet_years)
#   postures     -10 .. +10  the armed countries' doctrines, a rank-weighted average
#   restraint    0 .. +15    non-use pledges, former nuclear states
#   ledger       -30 .. +10  the decaying record of acts (global_var:nd_taboo_ledger)
#
# Drift alone tops out at 55 (base + full tradition); the rest needs
# cooperation. A use also knocks the score down at once (nd_taboo_note_use).
#
# THE TUNING BLOCK is parsed by scripts/analysis/nuclear_taboo_sim.py: keep
# every constant on one line as `name = number`.
#
# Scope: the parts and the reading values evaluate in any scope (they sweep
# every_country and read globals). nd_taboo_rank_weight, nd_taboo_stance_value
# and everything under POSSESSION are country-scoped.
# ============================================================================

# ---- TUNING ------------------------------------------------------------------
nd_taboo_birth_value = 20
nd_taboo_base = 20
nd_taboo_tradition_per_year = 1
nd_taboo_tradition_cap = 35
nd_taboo_approach_months = 36
nd_taboo_max_step = 1
nd_taboo_max_step_down = -1
nd_taboo_ledger_decay = 0.9857
nd_taboo_ledger_min = -30
nd_taboo_ledger_max = 10
nd_taboo_postures_span = 10
nd_taboo_postures_floor = -10
nd_taboo_restraint_cap = 15
nd_taboo_pledge_point = 1
nd_taboo_pledge_cap = 5
nd_taboo_renounced_point = 3
nd_taboo_renounced_cap = 10
nd_taboo_weight_great = 1
nd_taboo_weight_major = 0.5
nd_taboo_weight_minor = 0.25
nd_taboo_weight_other = 0.1
nd_taboo_line_fragile = 30
nd_taboo_line_established = 50
nd_taboo_line_strong = 70
nd_taboo_line_absolute = 90

# ---- READING THE SCORE ---------------------------------------------------------

# The score; the birth value before the first warhead, so no reader ever reads
# a missing global.
nd_taboo_value = {
	value = nd_taboo_birth_value
	if = {
		limit = { has_global_variable = nd_taboo }
		value = global_var:nd_taboo
	}
}

# The band the score falls in: 1 Normalised, 2 Fragile, 3 Established,
# 4 Strong, 5 Absolute.
nd_taboo_band_value = {
	value = 1
	if = {
		limit = { nd_taboo_value >= nd_taboo_line_fragile }
		value = 2
	}
	if = {
		limit = { nd_taboo_value >= nd_taboo_line_established }
		value = 3
	}
	if = {
		limit = { nd_taboo_value >= nd_taboo_line_strong }
		value = 4
	}
	if = {
		limit = { nd_taboo_value >= nd_taboo_line_absolute }
		value = 5
	}
}

# ---- WEIGHTS -------------------------------------------------------------------

# How much this country's threats, doctrines and pledges count, from its rank.
# Read when the act happens, so it needs no UN (un_actor_weight reads a share
# only the UN's monthly update caches, and is 0 in a world without one).
# Scope: country
nd_taboo_rank_weight = {
	value = nd_taboo_weight_other
	if = {
		limit = { country_rank >= rank_value:great_power }
		value = nd_taboo_weight_great
	}
	else_if = {
		limit = { country_rank >= rank_value:major_power }
		value = nd_taboo_weight_major
	}
	else_if = {
		limit = { country_rank >= rank_value:minor_power }
		value = nd_taboo_weight_minor
	}
}

# An armed country's stance, -1 .. +1: its doctrine (No First Use +1,
# Existential 0, Flexible -1/3, Compellence -2/3, Warfighting -1), +1/4 while
# Recessed, -1/4 at High Alert.
# Scope: country
nd_taboo_stance_value = {
	value = 0
	if = {
		limit = { has_variable = nd_doctrine }
		if = {
			limit = { var:nd_doctrine = 1 }
			value = 1
		}
		else_if = {
			limit = { var:nd_doctrine = 3 }
			value = -0.33
		}
		else_if = {
			limit = { var:nd_doctrine = 4 }
			value = -0.67
		}
		else_if = {
			limit = { var:nd_doctrine = 5 }
			value = -1
		}
	}
	if = {
		limit = { has_variable = nd_readiness }
		if = {
			limit = { var:nd_readiness = 0 }
			add = 0.25
		}
		else_if = {
			limit = { var:nd_readiness = 3 }
			add = -0.25
		}
	}
	min = -1
	max = 1
}

# How many non-use pledges this country holds (one list entry per partner).
# Scope: country
nd_taboo_pledge_count_value = {
	value = 0
	if = {
		limit = { has_variable_list = nd_nonuse_pledges }
		every_in_list = {
			variable = nd_nonuse_pledges
			add = 1
		}
	}
}

# ---- THE PARTS (the monthly update snapshots them) ----------------------------

nd_taboo_part_tradition_value = {
	value = 0
	if = {
		limit = { has_global_variable = nd_taboo_quiet_years }
		add = global_var:nd_taboo_quiet_years
		multiply = nd_taboo_tradition_per_year
	}
	min = 0
	max = nd_taboo_tradition_cap
}

nd_taboo_armed_weight_sum = {
	value = 0
	every_country = {
		limit = { nd_is_armed = yes }
		add = nd_taboo_rank_weight
	}
}

nd_taboo_armed_stance_sum = {
	value = 0
	every_country = {
		limit = { nd_is_armed = yes }
		add = {
			value = nd_taboo_rank_weight
			multiply = nd_taboo_stance_value
		}
	}
}

# An average, so one micro-state's No First Use cannot swamp the world.
nd_taboo_part_postures_value = {
	value = 0
	if = {
		limit = {
			any_country = { nd_is_armed = yes }
		}
		value = nd_taboo_armed_stance_sum
		divide = nd_taboo_armed_weight_sum
		multiply = nd_taboo_postures_span
	}
	min = nd_taboo_postures_floor
	max = nd_taboo_postures_span
}

# Each pledge is held by both partners, so the pairs are half the entries.
nd_taboo_pledge_entries_value = {
	value = 0
	every_country = {
		limit = { has_variable_list = nd_nonuse_pledges }
		add = nd_taboo_pledge_count_value
	}
}

nd_taboo_renounced_weight_value = {
	value = 0
	every_country = {
		limit = { nd_taboo_is_former_nuclear_state = yes }
		add = nd_taboo_rank_weight
	}
}

nd_taboo_part_restraint_value = {
	value = 0
	add = {
		value = nd_taboo_pledge_entries_value
		divide = 2
		multiply = nd_taboo_pledge_point
		max = nd_taboo_pledge_cap
	}
	add = {
		value = nd_taboo_renounced_weight_value
		multiply = nd_taboo_renounced_point
		max = nd_taboo_renounced_cap
	}
	min = 0
	max = nd_taboo_restraint_cap
}

# ---- THE TARGET AND THE STEP ---------------------------------------------------

# The equilibrium, from the snapshots the monthly update has just written.
nd_taboo_target_sum = {
	value = global_var:nd_tb_base
	add = global_var:nd_tb_tradition
	add = global_var:nd_tb_postures
	add = global_var:nd_tb_restraint
	add = global_var:nd_tb_ledger
	min = 0
	max = 100
}

# This month's move toward the target: a 36th of the gap, at most one point.
nd_taboo_step_value = {
	value = global_var:nd_taboo_target
	subtract = global_var:nd_taboo
	divide = nd_taboo_approach_months
	min = nd_taboo_max_step_down
	max = nd_taboo_max_step
}

nd_taboo_years_per_month = {
	value = 1
	divide = 12
}

# ---- DISPLAY (reads of the snapshots; the panel re-renders every frame) --------

nd_disp_taboo = {
	value = nd_taboo_value
}

nd_disp_taboo_target = {
	value = nd_taboo_birth_value
	if = {
		limit = { has_global_variable = nd_taboo_target }
		value = global_var:nd_taboo_target
	}
}

nd_disp_taboo_quiet_years = {
	value = 0
	if = {
		limit = { has_global_variable = nd_taboo_quiet_years }
		value = global_var:nd_taboo_quiet_years
	}
}

nd_disp_tb_base = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_base }
		value = global_var:nd_tb_base
	}
}

nd_disp_tb_tradition = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_tradition }
		value = global_var:nd_tb_tradition
	}
}

nd_disp_tb_postures = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_postures }
		value = global_var:nd_tb_postures
	}
}

nd_disp_tb_restraint = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_restraint }
		value = global_var:nd_tb_restraint
	}
}

nd_disp_tb_ledger = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_ledger }
		value = global_var:nd_tb_ledger
	}
}
```

- [ ] **Step 4: Create `common/scripted_triggers/nuclear_taboo_triggers.txt`** (BOM first)

```
﻿# ============================================================================
# THE NUCLEAR TABOO — scripted triggers
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md; values and
# thresholds in common/script_values/nuclear_taboo_values.txt.
# ============================================================================

# A former nuclear state: it gave an arsenal up (nd_taboo_note_renunciation set
# the year) and holds no warheads now. Counted by the restraint part.
# Scope: country
nd_taboo_is_former_nuclear_state = {
	has_variable = nd_renounced
	nd_is_armed = no
}
```

- [ ] **Step 5: Create `common/scripted_effects/nuclear_taboo_effects.txt`** (BOM first)

```
﻿# ============================================================================
# THE NUCLEAR TABOO — effects
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md; the
# numbers are in common/script_values/nuclear_taboo_values.txt.
#
# SINGLE WRITERS. Only the effects in this file write global_var:nd_taboo,
# nd_taboo_ledger, nd_taboo_quiet_years and the nd_tb_* snapshots
# (test_nuclear_taboo.py checks). Everything else calls a writer below. Every
# writer is a no-op before the taboo is born.
#
# TWO HALVES. nd_taboo_monthly_update is the world's step, from the global
# monthly pulse (nuclear_taboo_on_actions.txt): ROOT is none there, so it never
# applies a modifier. nd_taboo_country_monthly is each country's half, from
# je_nuclear_program's monthly pulse with ROOT = the country — the possession
# cost, the exits and the history samples live there.
# ============================================================================

# ----------------------------------------------------------------------------
# BIRTH
# ----------------------------------------------------------------------------

# The world's first warhead (nuclear_program_weekly_progress, the branch that
# sets world_first_nuclear_weapon). Idempotent. Scope: any.
nd_taboo_birth = {
	if = {
		limit = { NOT = { has_global_variable = nd_taboo } }
		set_global_variable = { name = nd_taboo_quiet_years value = 0 }
		set_global_variable = { name = nd_taboo_ledger value = 0 }
		nd_taboo_snapshot = yes
		set_global_variable = { name = nd_taboo value = nd_taboo_birth_value }
		set_global_variable = { name = nd_taboo_band value = nd_taboo_band_value }
		debug_log = "TE_TABOO: born with the world's first warhead"
	}
}

# A save in which warheads already exist when the taboo arrives. The tradition
# clock is the years since the world's first device when no weapon has ever
# been used, 0 otherwise; the score starts at the target that clock implies,
# not at 20. Scope: any.
nd_taboo_seed_existing_world = {
	if = {
		limit = {
			has_global_variable = world_first_nuclear_weapon
			NOT = { has_global_variable = nd_taboo }
		}
		set_global_variable = { name = nd_taboo_quiet_years value = 0 }
		set_global_variable = { name = nd_taboo_ledger value = 0 }
		if = {
			limit = {
				NOT = { has_global_variable = world_first_nuclear_weapon_used }
			}
			random_country = {
				limit = {
					has_variable = is_world_first_nuclear_power
					has_variable = nuclear_program_first_device_year
				}
				set_global_variable = {
					name = nd_taboo_quiet_years
					value = {
						value = year
						subtract = var:nuclear_program_first_device_year
						min = 0
					}
				}
			}
		}
		nd_taboo_snapshot = yes
		set_global_variable = { name = nd_taboo value = global_var:nd_taboo_target }
		set_global_variable = { name = nd_taboo_band value = nd_taboo_band_value }
		debug_log = "TE_TABOO: seeded a world already in the nuclear age"
	}
}

# ----------------------------------------------------------------------------
# THE WORLD'S MONTHLY STEP
# ----------------------------------------------------------------------------

# Every part, then the target. Scope: any.
nd_taboo_snapshot = {
	set_global_variable = { name = nd_tb_base value = nd_taboo_base }
	set_global_variable = { name = nd_tb_tradition value = nd_taboo_part_tradition_value }
	set_global_variable = { name = nd_tb_postures value = nd_taboo_part_postures_value }
	set_global_variable = { name = nd_tb_restraint value = nd_taboo_part_restraint_value }
	set_global_variable = { name = nd_tb_ledger value = global_var:nd_taboo_ledger }
	set_global_variable = { name = nd_taboo_target value = nd_taboo_target_sum }
}

# From nd_taboo_monthly_on_action (global scope). Advances the clock, fades the
# ledger, snapshots the parts and steps the score toward the target.
nd_taboo_monthly_update = {
	# The nuclear powers' leaderboard, once for the world. It ran from every
	# active country's weekly pulse, which the entry being active for every
	# country (nuke_triggers.txt) would have made ~200 sweeps a week.
	update_nuclear_powers_ranking = yes
	nd_taboo_seed_existing_world = yes
	if = {
		limit = { has_global_variable = nd_taboo }
		change_global_variable = { name = nd_taboo_quiet_years add = nd_taboo_years_per_month }
		set_global_variable = {
			name = nd_taboo_ledger
			value = {
				value = global_var:nd_taboo_ledger
				multiply = nd_taboo_ledger_decay
			}
		}
		nd_taboo_snapshot = yes
		set_global_variable = {
			name = nd_taboo
			value = {
				value = global_var:nd_taboo
				add = nd_taboo_step_value
				min = 0
				max = 100
			}
		}
		debug_log = "TE_TABOO: score [SCOPE.ScriptValue('nd_disp_taboo')|1] target [SCOPE.ScriptValue('nd_disp_taboo_target')|1] base [SCOPE.ScriptValue('nd_disp_tb_base')|1] tradition [SCOPE.ScriptValue('nd_disp_tb_tradition')|1] postures [SCOPE.ScriptValue('nd_disp_tb_postures')|1] restraint [SCOPE.ScriptValue('nd_disp_tb_restraint')|1] ledger [SCOPE.ScriptValue('nd_disp_tb_ledger')|1] quiet years [SCOPE.ScriptValue('nd_disp_taboo_quiet_years')|1]"
	}
}

# ----------------------------------------------------------------------------
# WRITERS — everything outside this file moves the taboo through these
# ----------------------------------------------------------------------------

# An unweighted ledger entry. POINTS: a number, a script value, var:X or
# global_var:X, signed. Scope: any.
nd_taboo_ledger_add = {
	if = {
		limit = { has_global_variable = nd_taboo }
		set_global_variable = { name = nd_tb_stage value = $POINTS$ }
		nd_taboo_ledger_commit = yes
	}
}

# A ledger entry weighted by the acting country's rank (nd_taboo_rank_weight).
# Scope: the acting country.
nd_taboo_ledger_add_weighted = {
	if = {
		limit = { has_global_variable = nd_taboo }
		set_global_variable = {
			name = nd_tb_stage
			value = {
				value = nd_taboo_rank_weight
				multiply = $POINTS$
			}
		}
		nd_taboo_ledger_commit = yes
	}
}

# Adds the staged amount to the ledger, held inside -30 .. +10. Only writers
# in this file call it.
nd_taboo_ledger_commit = {
	set_global_variable = {
		name = nd_taboo_ledger
		value = {
			value = global_var:nd_taboo_ledger
			add = global_var:nd_tb_stage
			min = nd_taboo_ledger_min
			max = nd_taboo_ledger_max
		}
	}
	remove_global_variable = nd_tb_stage
}

# An immediate move of the score, held inside 0 .. 100. Scope: any.
nd_taboo_shock = {
	if = {
		limit = { has_global_variable = nd_taboo }
		set_global_variable = {
			name = nd_taboo
			value = {
				value = global_var:nd_taboo
				add = $POINTS$
				min = 0
				max = 100
			}
		}
	}
}
```

`nd_taboo_country_monthly`, the country half, is created by Task 6 together with its first line and its call from the entry. An empty shell here would trip `empty_effect_audit`.

- [ ] **Step 6: Create `common/on_actions/nuclear_taboo_on_actions.txt`** (BOM first)

```
﻿# ============================================================================
# THE NUCLEAR TABOO — the world's monthly step
# ============================================================================
# Global scope (no ROOT): the step runs once for the world, never once per
# country, and never from the UN's pulse (un_global_authority_on_action runs
# only once the UN is founded; the nuclear system must work with the UN
# disabled). Nothing here applies a modifier with `multiplier = root.var:…`;
# the per-country half runs from je_nuclear_program's monthly pulse
# (nd_taboo_country_monthly, nuclear_taboo_effects.txt).
# The engine unions same-name on_action declarations across files.
# ============================================================================

on_monthly_pulse = {
	on_actions = {
		nd_taboo_monthly_on_action
	}
}

nd_taboo_monthly_on_action = {
	effect = {
		if = {
			limit = { has_game_rule = nuclear_weapons_enabled }
			nd_taboo_monthly_update = yes
		}
	}
}
```

- [ ] **Step 7: Birth at the first warhead**

In `common/scripted_effects/nuclear_weapon_effects.txt`, replace

```
			set_global_variable = { name = world_first_nuclear_weapon value = yes }
			trigger_event = { id = nuclear_weapon_events.10 }
```

with

```
			set_global_variable = { name = world_first_nuclear_weapon value = yes }
			# The nuclear taboo is born with the world's first warhead
			# (nuclear_taboo_effects.txt); idempotent, so every later
			# first device passes through harmlessly.
			nd_taboo_birth = yes
			trigger_event = { id = nuclear_weapon_events.10 }
```

- [ ] **Step 8: Take the leaderboard off the weekly pulse**

In `common/journal_entries/je_nuclear_program.txt`, delete these three lines from `on_weekly_pulse` (the call now runs in `nd_taboo_monthly_update`):

```
			# Update global nuclear powers leaderboard
			update_nuclear_powers_ranking = yes

```

- [ ] **Step 9: File the `nd_taboo_` family whole in `organize_loc.py`**

In `categorize_key`, insert immediately after the `TE_HOMELAND_` rule:

```python
    # The nuclear taboo (docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md).
    # Every loc-bearing key it adds — static modifiers, the decision, event
    # options, tooltips, the panel's breakdown lines — carries the nd_taboo_
    # prefix. Four-token bases (`nd_taboo_possession_cost`) would otherwise land
    # in MISCELLANEOUS while their `_desc` fell to CONCEPTS.
    if key.startswith("nd_taboo_"):
        return "MISCELLANEOUS"
```

- [ ] **Step 10: Format and run the tests**

Run:
```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/on_actions/nuclear_taboo_on_actions.txt common/scripted_effects/nuclear_weapon_effects.txt common/journal_entries/je_nuclear_program.txt
python3 -m unittest test_nuclear_taboo -v
python3 -m unittest test_nuclear_deterrence
ruff check test_nuclear_taboo.py organize_loc.py
```
Expected: every `test_nuclear_taboo` test passes, `test_nuclear_deterrence` still passes, and ruff is clean.

- [ ] **Step 11: Commit**

```bash
git add test_nuclear_taboo.py organize_loc.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/on_actions/nuclear_taboo_on_actions.txt common/scripted_effects/nuclear_weapon_effects.txt common/journal_entries/je_nuclear_program.txt
git commit -m "Nuclear taboo: the score, its parts and the world's monthly step

<attribution lines>"
```

---

### Task 2: The simulator

**Files:**
- Create: `scripts/analysis/nuclear_taboo_sim.py`
- Modify: `test_nuclear_taboo.py` (add `TestSimulator`)

**Interfaces:**
- Consumes: the `nd_taboo_*` constants in `nuclear_taboo_values.txt`, as `name = number` lines.
- Produces:
  - `load_constants(path) -> dict[str, float]`;
  - `Scenario` (a dataclass);
  - `simulate(scenario, constants, years) -> list[tuple[float, float]]`, the monthly (score, target) pairs;
  - `band_events(scores, constants, cooldown_months) -> list[tuple[int, str]]`, a list of (month, "up N" | "down N");
  - `SCENARIOS` (a dict).

- [ ] **Step 1: Write the failing tests** (append to `test_nuclear_taboo.py`, above the `if __name__` line)

```python
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))


class TestSimulator(unittest.TestCase):
    def setUp(self):
        import nuclear_taboo_sim as sim
        self.sim = sim
        self.c = sim.load_constants(TABOO_VALUES)

    def test_constants_come_from_the_script_file(self):
        for name in ("nd_taboo_base", "nd_taboo_tradition_cap", "nd_taboo_approach_months",
                     "nd_taboo_ledger_decay", "nd_taboo_shock_strategic", "nd_taboo_ledger_strategic",
                     "nd_taboo_clock_keep_first_use", "nd_taboo_band_hysteresis"):
            self.assertIn(name, self.c, name)

    def test_quiet_world_plateaus_at_55(self):
        series = self.sim.simulate(self.sim.SCENARIOS["quiet"], self.c, years=100)
        score, target = series[-1]
        self.assertAlmostEqual(target, 55, delta=0.01)
        self.assertAlmostEqual(score, 55, delta=0.5)

    def test_one_use_roughly_halves_a_mature_taboo(self):
        series = self.sim.simulate(self.sim.SCENARIOS["use_year_40"], self.c, years=41)
        before = series[40 * 12 - 1][1]
        after = series[40 * 12 + 1][1]
        self.assertGreater(before - after, 20)
        self.assertLess(before - after, 35)

    def test_seeded_quiet_world_starts_near_its_target(self):
        scenario = self.sim.SCENARIOS["seeded_40_years"]
        score, target = self.sim.simulate(scenario, self.c, years=1)[0]
        self.assertAlmostEqual(score, target, delta=1.1)
        self.assertGreater(score, 50)

    def test_band_events_do_not_flap(self):
        flapping = [50 + (1 if m % 2 else -1) for m in range(240)]
        events = self.sim.band_events(flapping, self.c, cooldown_months=120)
        self.assertLessEqual(len(events), 1)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestSimulator -v`
Expected: `ModuleNotFoundError: No module named 'nuclear_taboo_sim'`.

- [ ] **Step 3: Add the constants the simulator needs to the TUNING block**

In `nuclear_taboo_values.txt`, append these lines to the TUNING block, after `nd_taboo_line_absolute = 90`. Task 3 uses most of them; adding them now keeps the block in one place.

```
nd_taboo_shock_strategic = -15
nd_taboo_ledger_strategic = -10
nd_taboo_shock_tactical = -6
nd_taboo_ledger_tactical = -4
nd_taboo_retaliation_factor = 0.5
nd_taboo_clock_keep_first_use = 0.5
nd_taboo_clock_keep_retaliation = 0.75
nd_taboo_band_hysteresis = 2
nd_taboo_event_cooldown_years = 10
```

- [ ] **Step 4: Create `scripts/analysis/nuclear_taboo_sim.py`**

```python
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
```

The table shows `score (target)` at each checkpoint.

- [ ] **Step 5: Run the tests and the script**

Run:
```bash
python3 -m unittest test_nuclear_taboo -v
python3 scripts/analysis/nuclear_taboo_sim.py
ruff check scripts/analysis/nuclear_taboo_sim.py test_nuclear_taboo.py
```
Expected: all tests pass; the script prints a 6-row table whose "quiet" row reads `55 (55)` at year 100; ruff is clean.

- [ ] **Step 6: Commit**

```bash
git add scripts/analysis/nuclear_taboo_sim.py test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt
git commit -m "Nuclear taboo: a simulator reading the script's own constants

<attribution lines>"
```

---

### Task 3: What moves it: uses, threats, doctrines, pledges, stand-downs, terror

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING)
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (add `nd_taboo_note_use`)
- Modify: `common/scripted_effects/extra_effects.txt` (`nuclear_first_strike`, `nuclear_response_strike`, `nuclear_response_response_strike`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_tactical_strike_resolve`, `nd_set_doctrine_1`, `nd_set_doctrine`, `nd_break_pledge_effects`, `nd_weekly_update`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_open`, `nd_crisis_act_go_public`, `nd_crisis_close`)
- Modify: `common/scripted_effects/nuclear_loose_effects.txt` (the detonation)
- Test: `test_nuclear_taboo.py` (`TestActs`)

**Interfaces:**
- Consumes: `nd_taboo_ledger_add`, `nd_taboo_ledger_add_weighted`, `nd_taboo_shock` (Task 1).
- Produces:
  - `nd_taboo_note_use = { KIND = strategic|tactical RETALIATION = yes|no }` (any scope), which sets `global_var:nd_taboo_last_use_year`;
  - `nd_bind_doctrine_1` (country), the law's binding with no ledger credit.

- [ ] **Step 1: Write the failing tests** (append to `test_nuclear_taboo.py` above `if __name__`, next to the other path constants add the ones shown)

```python
EXTRA_EFFECTS = ROOT / "common/scripted_effects/extra_effects.txt"
DETERRENCE_EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
LOOSE_EFFECTS = ROOT / "common/scripted_effects/nuclear_loose_effects.txt"


class TestActs(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.extra = strip_comments(read(EXTRA_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.loose = strip_comments(read(LOOSE_EFFECTS))

    def test_note_use_scales_and_cuts_the_clock(self):
        body = block(self.taboo, "nd_taboo_note_use")
        for needle in ("value = nd_taboo_shock_$KIND$", "value = nd_taboo_ledger_$KIND$",
                       "always = $RETALIATION$", "multiply = nd_taboo_clock_keep_retaliation",
                       "multiply = nd_taboo_clock_keep_first_use",
                       "nd_taboo_shock = { POINTS = global_var:nd_tb_use_shock }",
                       "nd_taboo_ledger_add = { POINTS = global_var:nd_tb_use_ledger }",
                       "name = nd_taboo_last_use_year value = year"):
            self.assertIn(needle, body)

    def test_response_strikes_are_retaliation_by_construction(self):
        for name in ("nuclear_response_strike", "nuclear_response_response_strike"):
            body = block(self.extra, name)
            self.assertIn("nd_taboo_note_use = { KIND = strategic RETALIATION = yes }", body, name)
            self.assertNotIn("RETALIATION = no", body, name)
            self.assertNotIn("nd_was_struck_by", body, name)

    def test_first_strikes_ask_whether_they_answer_a_strike(self):
        for text, name, kind in ((self.extra, "nuclear_first_strike", "strategic"),
                                 (self.det, "nd_tactical_strike_resolve", "tactical")):
            body = block(text, name)
            self.assertIn("nd_was_struck_by = { ENEMY = scope:target_country }", body, name)
            self.assertIn(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = yes }}", body, name)
            self.assertIn(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = no }}", body, name)

    def test_dispatch_is_always_at_war(self):
        # nd_was_struck_by opens with has_war_with; every detonation site is
        # reached inside a war, or the retaliation branch could never be taken.
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("has_war_with = scope:nd_strike_victim", block(self.det, name), name)

    def test_terror_is_not_a_use(self):
        self.assertIn("nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_terror }", self.loose)
        self.assertNotIn("nd_taboo_note_use", self.loose)

    def test_threats_wear_it_down(self):
        body = block(self.crisis, "nd_crisis_open")
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_ultimatum }", body)
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_warning }", body)
        self.assertIn("nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_go_public }",
                      block(self.crisis, "nd_crisis_act_go_public"))

    def test_doctrine_credit_is_the_governments_not_the_laws(self):
        weekly = block(self.det, "nd_weekly_update")
        self.assertIn("nd_bind_doctrine_1 = yes", weekly)
        self.assertNotIn("nd_set_doctrine_1 = yes", weekly)
        shared = "nd_set_doctrine = { D = 1 OFFENSIVE = no LEAVES_NFU = no }"
        self.assertIn(shared, block(self.det, "nd_set_doctrine_1"))
        self.assertIn(shared, block(self.det, "nd_bind_doctrine_1"))
        self.assertIn("POINTS = nd_taboo_ledger_nfu", block(self.det, "nd_set_doctrine_1"))
        self.assertNotIn("nd_taboo_ledger", block(self.det, "nd_bind_doctrine_1"))
        self.assertIn("POINTS = nd_taboo_ledger_offensive_doctrine", block(self.det, "nd_set_doctrine"))
        self.assertIn("POINTS = nd_taboo_ledger_repudiation", block(self.det, "nd_break_pledge_effects"))

    def test_reciprocal_standdown_strengthens_it(self):
        body = block(self.crisis, "nd_crisis_close")
        self.assertIn("var:nd_crisis_outcome_now = 3", body)
        self.assertIn("nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_standdown }", body)

    def test_every_ledger_constant_is_defined(self):
        values = strip_comments(read(TABOO_VALUES))
        used = set()
        for path in script_files():
            used |= set(re.findall(r"POINTS = (nd_taboo_\w+)", strip_comments(read(path))))
        self.assertTrue(used)
        for name in used:
            self.assertRegex(values, rf"(?m)^{name} = ", name)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestActs -v`
Expected: `AssertionError: nd_taboo_note_use not found` and the missing-needle failures.

- [ ] **Step 3: Add the ledger constants** (append to the TUNING block of `nuclear_taboo_values.txt`)

```
nd_taboo_ledger_ultimatum = -1
nd_taboo_ledger_warning = -0.3
nd_taboo_ledger_go_public = -0.7
nd_taboo_ledger_offensive_doctrine = -1
nd_taboo_ledger_repudiation = -1.5
nd_taboo_ledger_nfu = 0.5
nd_taboo_ledger_standdown = 0.5
nd_taboo_ledger_terror = 2
```

- [ ] **Step 4: Add `nd_taboo_note_use` to `nuclear_taboo_effects.txt`** (after `nd_taboo_shock`)

```
# A detonation by a state (a loose warhead's is not one: the terror plot books
# nd_taboo_ledger_terror instead). KIND = strategic | tactical. RETALIATION =
# yes | no, a literal from the caller: the response strikes pass yes by
# construction, the first-strike effects ask nd_was_struck_by — never a role
# read from a scope the strike effects swap (scripting_best_practices.md § A
# Shared Script Value Must Not Read a Scope Named for a Role Its Callers
# Swap). A first use halves the tradition of non-use; an answer counts half
# and cuts it by a quarter. Scope: any.
nd_taboo_note_use = {
	if = {
		limit = { has_global_variable = nd_taboo }
		set_global_variable = { name = nd_tb_use_shock value = nd_taboo_shock_$KIND$ }
		set_global_variable = { name = nd_tb_use_ledger value = nd_taboo_ledger_$KIND$ }
		if = {
			limit = { always = $RETALIATION$ }
			change_global_variable = { name = nd_tb_use_shock multiply = nd_taboo_retaliation_factor }
			change_global_variable = { name = nd_tb_use_ledger multiply = nd_taboo_retaliation_factor }
			change_global_variable = { name = nd_taboo_quiet_years multiply = nd_taboo_clock_keep_retaliation }
		}
		else = {
			change_global_variable = { name = nd_taboo_quiet_years multiply = nd_taboo_clock_keep_first_use }
		}
		nd_taboo_shock = { POINTS = global_var:nd_tb_use_shock }
		nd_taboo_ledger_add = { POINTS = global_var:nd_tb_use_ledger }
		set_global_variable = { name = nd_taboo_last_use_year value = year }
		remove_global_variable = nd_tb_use_shock
		remove_global_variable = nd_tb_use_ledger
		debug_log = "TE_TABOO: a nuclear weapon was used; score now [SCOPE.ScriptValue('nd_disp_taboo')|1]"
	}
}
```

- [ ] **Step 5: The strategic detonations** (`common/scripted_effects/extra_effects.txt`)

In `nuclear_first_strike`, replace

```
					un_regime_icc_note_crime = { CRIME = 1 }
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.1 popup = yes }
					}
```

with

```
					un_regime_icc_note_crime = { CRIME = 1 }
					# ...and a blow to the nuclear taboo (nuclear_taboo_effects.txt).
					# An answer to a strike on us or on a country we cover counts
					# half; every caller is at war with the target, which
					# nd_was_struck_by needs.
					if = {
						limit = { nd_was_struck_by = { ENEMY = scope:target_country } }
						nd_taboo_note_use = { KIND = strategic RETALIATION = yes }
					}
					else = {
						nd_taboo_note_use = { KIND = strategic RETALIATION = no }
					}
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.1 popup = yes }
					}
```

In `nuclear_response_strike`, replace

```
					un_dossier_record = { RECORD = nuclear POINTS = un_dos_points_retaliation }
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.11 popup = yes }
```

with

```
					un_dossier_record = { RECORD = nuclear POINTS = un_dos_points_retaliation }
					# Retaliation by construction: half a first use's blow to the
					# nuclear taboo (nuclear_taboo_effects.txt).
					nd_taboo_note_use = { KIND = strategic RETALIATION = yes }
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.11 popup = yes }
```

In `nuclear_response_response_strike`, replace

```
					un_dossier_record = { RECORD = nuclear POINTS = un_dos_points_retaliation }
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.1 popup = yes }
```

with

```
					un_dossier_record = { RECORD = nuclear POINTS = un_dos_points_retaliation }
					# An answer to an answer: still retaliation for the nuclear
					# taboo (nuclear_taboo_effects.txt).
					nd_taboo_note_use = { KIND = strategic RETALIATION = yes }
					scope:target_state = {
						nuclear_industrial_strike = yes
						trigger_event = { id = nuclear_weapon_events.1 popup = yes }
```

- [ ] **Step 6: The tactical detonation** (`nuclear_deterrence_effects.txt`, `nd_tactical_strike_resolve`)

Replace

```
			modifier = nuclear_strike_success_chance
			change_infamy = 10
			scope:target_state = {
				nuclear_tactical_strike = yes
			}
```

with

```
			modifier = nuclear_strike_success_chance
			change_infamy = 10
			# The nuclear taboo (nuclear_taboo_effects.txt); this country is
			# the attacker and at war with the target.
			if = {
				limit = { nd_was_struck_by = { ENEMY = scope:target_country } }
				nd_taboo_note_use = { KIND = tactical RETALIATION = yes }
			}
			else = {
				nd_taboo_note_use = { KIND = tactical RETALIATION = no }
			}
			scope:target_state = {
				nuclear_tactical_strike = yes
			}
```

(Task 4 moves `change_infamy = 10` into the first-use branch and scales it.)

- [ ] **Step 7: Terror** (`common/scripted_effects/nuclear_loose_effects.txt`)

Replace

```
			scope:nd_loose_state = {
				nuclear_industrial_strike = yes
			}
```

with

```
			scope:nd_loose_state = {
				nuclear_industrial_strike = yes
			}
			# The nuclear taboo: no government chose this, so it is not a use;
			# the world tightens up after a horror no one can answer.
			nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_terror }
```

- [ ] **Step 8: Threats** (`common/scripted_effects/nuclear_crisis_effects.txt`)

In `nd_crisis_open`, replace

```
			# ---- the crisis's figures, before anyone weighs them ------------
			nd_crisis_refresh_figures = yes
```

with

```
			# ---- a threat wears the nuclear taboo down, by our rank ---------
			if = {
				limit = { always = $PUBLIC$ }
				nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_ultimatum }
			}
			else = {
				nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_warning }
			}
			# ---- the crisis's figures, before anyone weighs them ------------
			nd_crisis_refresh_figures = yes
```

In `nd_crisis_act_go_public`, replace

```
	custom_tooltip = nd_tt_go_public_terms
	hidden_effect = {
		nd_crisis_save_parties = yes
```

with

```
	custom_tooltip = nd_tt_go_public_terms
	hidden_effect = {
		nd_crisis_save_parties = yes
		# A private warning made public: the rest of an ultimatum's toll on
		# the nuclear taboo.
		nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_go_public }
```

- [ ] **Step 9: Stand-downs** (`nd_crisis_close`)

Replace

```
		scope:nd_issuer = {
			set_variable = { name = nd_crisis_outcome_now value = $OUTCOME$ }
		}
```

with

```
		scope:nd_issuer = {
			set_variable = { name = nd_crisis_outcome_now value = $OUTCOME$ }
		}
		# Both sides stepping back strengthens the nuclear taboo.
		if = {
			limit = { scope:nd_issuer = { var:nd_crisis_outcome_now = 3 } }
			nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_standdown }
		}
```

- [ ] **Step 10: Doctrines and pledges** (`nuclear_deterrence_effects.txt`)

Replace the one-line wrapper

```
nd_set_doctrine_1 = { nd_set_doctrine = { D = 1 OFFENSIVE = no LEAVES_NFU = no } }
```

with

```
# The government's own pledge strengthens the nuclear taboo (weighted by our
# rank); the law holding us to it does not — nd_bind_doctrine_1 below.
nd_set_doctrine_1 = {
	nd_set_doctrine = { D = 1 OFFENSIVE = no LEAVES_NFU = no }
	hidden_effect = {
		nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_nfu }
	}
}
```

and add, directly after the `nd_set_doctrine_5` wrapper line:

```
# The No-First-Strike amendment holding an armed country at doctrine 1
# (nd_weekly_update): the law's act, not the government's, so the nuclear
# taboo is not credited.
nd_bind_doctrine_1 = { nd_set_doctrine = { D = 1 OFFENSIVE = no LEAVES_NFU = no } }
```

In `nd_weekly_update`, replace

```
		nd_set_doctrine_1 = yes
		set_variable = { name = nd_doctrine_months value = var:nd_doctrine_months_before_law }
```

with

```
		nd_bind_doctrine_1 = yes
		set_variable = { name = nd_doctrine_months value = var:nd_doctrine_months_before_law }
```

In `nd_set_doctrine`, replace

```
		custom_tooltip = nd_tt_doctrine_alarms_rivals
		hidden_effect = {
```

with

```
		custom_tooltip = nd_tt_doctrine_alarms_rivals
		hidden_effect = {
			# ...and wears the nuclear taboo down, by our rank.
			nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_offensive_doctrine }
```

In `nd_break_pledge_effects`, replace

```
	change_infamy = $INFAMY$
	add_modifier = {
		name = nd_pledge_broken_mod
```

with

```
	change_infamy = $INFAMY$
	# A broken promise wears the nuclear taboo down, by the breaker's rank.
	hidden_effect = {
		nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_repudiation }
	}
	add_modifier = {
		name = nd_pledge_broken_mod
```

- [ ] **Step 11: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_effects/extra_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_effects/nuclear_loose_effects.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 empty_effect_audit.py --strict && python3 prev_scope_audit.py --strict
git add test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_effects/extra_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_effects/nuclear_loose_effects.txt
git commit -m "Nuclear taboo: uses, threats, doctrines, pledges, stand-downs and terror move it

<attribution lines>"
```
Expected: all tests pass; both audits exit 0.

---

### Task 4: What it costs: scaled infamy, the world's reaction, threat pressure

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt`
- Modify: `common/scripted_effects/extra_effects.txt` (`nuclear_first_strike`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_tactical_strike_resolve`, `nd_set_doctrine`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_preview`, `nd_crisis_act_go_public`, `nd_crisis_refresh_figures`, `nd_crisis_clear_figures`)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_yp_taboo_value`, `nd_yield_pressure_value`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (`nd_crisis_pressure_breakdown_sgui`)
- Modify: `common/diplomatic_actions/nuke.txt` (both `accept_effect`s)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Modify: `test_nuclear_deterrence.py` (`PRESSURE_PARTS`, `ACT_LINES`)
- Test: `test_nuclear_taboo.py` (`TestCosts`)

**Interfaces:**
- Consumes: `nd_taboo_value`, `nd_taboo_note_use`.
- Produces script values: `nd_taboo_infamy_strategic`, `nd_taboo_infamy_tactical`, `nd_taboo_infamy_threat`, `nd_taboo_world_relations_strategic`, `nd_taboo_world_relations_tactical` (all ≥ 0 except the relations, which are ≤ 0), and `nd_yp_taboo_value` (target scope, `scope:nd_issuer` saved).

- [ ] **Step 1: Write the failing tests**

In `test_nuclear_deterrence.py`:
- append `"nd_yp_taboo"` to the end of `PRESSURE_PARTS`;
- in `ACT_LINES`, change `"nd_crisis_act_go_public": ["change_infamy = 5", …]` to `"nd_crisis_act_go_public": ["change_infamy = nd_taboo_infamy_threat", "change_relations", "nd_tt_go_public_terms"]`.

In `test_nuclear_taboo.py`, change the import line to `from test_nuclear_deterrence import block, loc_keys, read, strip_comments` (ruff's F401 fails on a helper imported before it is used), then append:

```python
NUKE_ACTIONS = ROOT / "common/diplomatic_actions/nuke.txt"
DETERRENCE_VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"


def constant(text, name):
    return float(re.search(rf"(?m)^{name} = (-?[\d.]+)", text).group(1))


class TestCosts(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.extra = strip_comments(read(EXTRA_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))

    def test_old_costs_are_the_value_at_taboo_25(self):
        self.assertEqual(25 * constant(self.values, "nd_taboo_infamy_strategic_per_point"), 25)
        self.assertEqual(25 * constant(self.values, "nd_taboo_infamy_tactical_per_point"), 10)
        self.assertAlmostEqual(50 * constant(self.values, "nd_taboo_infamy_threat_per_point"), 5)

    def test_first_use_pays_before_the_taboo_falls(self):
        for text, name, kind in ((self.extra, "nuclear_first_strike", "strategic"),
                                 (self.det, "nd_tactical_strike_resolve", "tactical")):
            body = block(text, name)
            self.assertNotRegex(body, r"change_infamy = (25|10)\b", name)
            pay = body.index(f"change_infamy = nd_taboo_infamy_{kind}")
            relations = body.index(f"value = nd_taboo_world_relations_{kind}")
            shock = body.index(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = no }}")
            self.assertLess(pay, shock, name)
            self.assertLess(relations, shock, name)
            answer = body.index(f"nd_taboo_note_use = {{ KIND = {kind} RETALIATION = yes }}")
            self.assertNotIn("change_infamy", body[answer - 200:answer], name)

    def test_threats_and_doctrines_pay_by_the_taboo(self):
        for text, name in ((self.crisis, "nd_crisis_preview"), (self.crisis, "nd_crisis_act_go_public"),
                           (self.det, "nd_set_doctrine")):
            body = block(text, name)
            self.assertIn("change_infamy = nd_taboo_infamy_threat", body, name)
            self.assertNotIn("change_infamy = 5", body, name)

    def test_strike_confirmations_name_the_cost(self):
        text = strip_comments(read(NUKE_ACTIONS))
        effects = re.findall(r"accept_effect = \{", text)
        self.assertEqual(len(effects), 2)
        self.assertIn("custom_tooltip = nd_taboo_tt_strike_first_use", text)
        self.assertIn("custom_tooltip = nd_taboo_tt_tactical_first_use", text)
        self.assertEqual(text.count("custom_tooltip = nd_taboo_tt_strike_answer"), 2)

    def test_pressure_part_reads_the_taboo(self):
        body = block(strip_comments(read(DETERRENCE_VALUES)), "nd_yp_taboo_value")
        for needle in ("value = nd_taboo_yp_midpoint", "subtract = nd_taboo_value",
                       "multiply = nd_taboo_yp_per_point", "var:nd_crisis_public = 1",
                       "multiply = nd_taboo_yp_public_discount"):
            self.assertIn(needle, body)

    def test_cost_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_tt_strike_first_use", "nd_taboo_tt_tactical_first_use",
                    "nd_taboo_tt_strike_answer", "nd_yp_taboo_line"):
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestCosts test_nuclear_deterrence -v 2>&1 | tail -30`
Expected: failures in `TestCosts`, and in `test_nuclear_deterrence` (`TestCrisisFigures` and `TestActLines`, since `nd_yp_taboo` and the new needle don't exist yet).

- [ ] **Step 3: Constants and cost values** (`nuclear_taboo_values.txt`)

Append to the TUNING block:

```
nd_taboo_infamy_strategic_per_point = 1
nd_taboo_infamy_tactical_per_point = 0.4
nd_taboo_infamy_threat_per_point = 0.1
nd_taboo_world_relations_per_point = -0.4
nd_taboo_world_relations_tactical_share = 0.4
nd_taboo_yp_midpoint = 50
nd_taboo_yp_per_point = 0.16
nd_taboo_yp_public_discount = 0.5
```

Append after the WEIGHTS section:

```
# ---- WHAT IT COSTS (spec §4) ---------------------------------------------------
# The fixed numbers these replace (25, 10 and 5 infamy) are their value at a
# taboo of 25 (50 for a threat); at 0 a nuclear act costs no infamy at all.

nd_taboo_infamy_strategic = {
	value = nd_taboo_value
	multiply = nd_taboo_infamy_strategic_per_point
}

nd_taboo_infamy_tactical = {
	value = nd_taboo_value
	multiply = nd_taboo_infamy_tactical_per_point
}

# A public ultimatum, going public, an offensive doctrine.
nd_taboo_infamy_threat = {
	value = nd_taboo_value
	multiply = nd_taboo_infamy_threat_per_point
}

# Every country but the victim, after a first use. Negative.
nd_taboo_world_relations_strategic = {
	value = nd_taboo_value
	multiply = nd_taboo_world_relations_per_point
	round = yes
}

nd_taboo_world_relations_tactical = {
	value = nd_taboo_world_relations_strategic
	multiply = nd_taboo_world_relations_tactical_share
	round = yes
}
```

- [ ] **Step 4: The strategic strike pays first**

In `extra_effects.txt` `nuclear_first_strike`, delete the line `change_infamy = 25` (and the blank line after `text = industrial_nuke_succeeds_desc` stays). Then replace the Task 3 block

```
					else = {
						nd_taboo_note_use = { KIND = strategic RETALIATION = no }
					}
```

with

```
					else = {
						# First use pays in infamy and the world's goodwill in
						# proportion to the taboo, before the taboo falls
						# (nuclear_taboo_values.txt). An answer pays neither.
						change_infamy = nd_taboo_infamy_strategic
						every_country = {
							limit = {
								NOT = { THIS = scope:attacking_country }
								NOT = { THIS = scope:target_country }
							}
							change_relations = { country = scope:attacking_country value = nd_taboo_world_relations_strategic }
						}
						nd_taboo_note_use = { KIND = strategic RETALIATION = no }
					}
```

- [ ] **Step 5: The tactical strike pays first**

In `nd_tactical_strike_resolve`, delete `change_infamy = 10` and replace

```
			else = {
				nd_taboo_note_use = { KIND = tactical RETALIATION = no }
			}
```

with

```
			else = {
				change_infamy = nd_taboo_infamy_tactical
				# Hidden: an every_* renders every member in the action's
				# preview, whose own line (nd_taboo_tt_tactical_first_use)
				# already names the figure.
				hidden_effect = {
					every_country = {
						limit = {
							NOT = { THIS = scope:attacking_country }
							NOT = { THIS = scope:target_country }
						}
						change_relations = { country = scope:attacking_country value = nd_taboo_world_relations_tactical }
					}
				}
				nd_taboo_note_use = { KIND = tactical RETALIATION = no }
			}
```

`nd_tactical_strike_resolve` runs in the attacker's scope with `scope:attacking_country` saved by both callers (`nuke.txt`'s accept_effect and `nd_dispatch_tactical_strike`). Unlike `nuclear_first_strike`'s success branch, its branch is not wrapped in a custom tooltip, hence the explicit `hidden_effect`.

- [ ] **Step 6: Threats and doctrines pay by the taboo**

Make three replacements. Each `change_infamy = 5` named here is the only one in its block.
- In `nd_crisis_preview`: `limit = { always = $PUBLIC$ }` followed by `change_infamy = 5` becomes `change_infamy = nd_taboo_infamy_threat`.
- In `nd_crisis_act_go_public`: `custom_tooltip = nd_tt_act_go_public` followed by `change_infamy = 5` becomes `change_infamy = nd_taboo_infamy_threat`.
- In `nd_set_doctrine`: `limit = { always = $OFFENSIVE$ }` followed by `change_infamy = 5` becomes `change_infamy = nd_taboo_infamy_threat`.

- [ ] **Step 7: The strike confirmations** (`common/diplomatic_actions/nuke.txt`)

In the **strategic** action's `accept_effect`, replace

```
	accept_effect = {
		save_scope_as = attacking_country
		if = {
			limit = { exists = scope:second_state }
			scope:second_state = {
				save_scope_as = target_state
				nuclear_first_strike = yes
```

with

```
	accept_effect = {
		save_scope_as = attacking_country
		# What success will cost, before the dice (the nuclear taboo,
		# nuclear_taboo_values.txt). Here, not in nuclear_first_strike, whose
		# success branch is one custom text and whose saved scopes do not exist
		# in this preview.
		if = {
			limit = { nd_was_struck_by = { ENEMY = scope:target_country } }
			custom_tooltip = nd_taboo_tt_strike_answer
		}
		else = {
			custom_tooltip = nd_taboo_tt_strike_first_use
		}
		if = {
			limit = { exists = scope:second_state }
			scope:second_state = {
				save_scope_as = target_state
				nuclear_first_strike = yes
```

In the **tactical** action's `accept_effect`, replace

```
	accept_effect = {
		save_scope_as = attacking_country
		if = {
			limit = { exists = scope:second_state }
			scope:second_state = {
				save_scope_as = target_state
			}
```

with

```
	accept_effect = {
		save_scope_as = attacking_country
		# What success will cost (the nuclear taboo, nuclear_taboo_values.txt).
		if = {
			limit = { nd_was_struck_by = { ENEMY = scope:target_country } }
			custom_tooltip = nd_taboo_tt_strike_answer
		}
		else = {
			custom_tooltip = nd_taboo_tt_tactical_first_use
		}
		if = {
			limit = { exists = scope:second_state }
			scope:second_state = {
				save_scope_as = target_state
			}
```

- [ ] **Step 8: The pressure part** (`common/script_values/nuclear_deterrence_values.txt`)

Insert immediately above the line `nd_yield_pressure_value = {`:

```
# The nuclear taboo (nuclear_taboo_values.txt): +8 at taboo 0, where threats
# are believed, down to -8 at 100, where nobody believes a government would do
# it. The doubt is halved for a public ultimatum: issuing one spends reputation
# (the taboo-scaled infamy), and that price is itself the signal. Target scope,
# scope:nd_issuer saved.
nd_yp_taboo_value = {
	value = nd_taboo_yp_midpoint
	subtract = nd_taboo_value
	multiply = nd_taboo_yp_per_point
	if = {
		limit = {
			nd_taboo_value > nd_taboo_yp_midpoint
			scope:nd_issuer ?= {
				has_variable = nd_crisis_public
				var:nd_crisis_public = 1
			}
		}
		multiply = nd_taboo_yp_public_discount
	}
	round = yes
}

```

In `nd_yield_pressure_value`, replace `add = nd_yp_follow_through_value` with:

```
	add = nd_yp_follow_through_value
	add = nd_yp_taboo_value
```

- [ ] **Step 9: Store, clear and print the part** (`nuclear_crisis_effects.txt`, `nuclear_deterrence_sguis.txt`)

In `nd_crisis_refresh_figures`, replace

```
		nd_crisis_store_yp = { C = nd_yp_follow_through V = nd_yp_follow_through_value }
```

with

```
		nd_crisis_store_yp = { C = nd_yp_follow_through V = nd_yp_follow_through_value }
		nd_crisis_store_yp = { C = nd_yp_taboo V = nd_yp_taboo_value }
```

In `nd_crisis_clear_figures`, replace

```
	if = {
		limit = { has_variable = nd_yp_follow_through }
		remove_variable = nd_yp_follow_through
	}
```

with

```
	if = {
		limit = { has_variable = nd_yp_follow_through }
		remove_variable = nd_yp_follow_through
	}
	if = {
		limit = { has_variable = nd_yp_taboo }
		remove_variable = nd_yp_taboo
	}
```

In `nd_crisis_pressure_breakdown_sgui`, replace

```
		nd_crisis_breakdown_line = { C = nd_yp_follow_through KEY = nd_yp_follow_through_line }
```

with

```
		nd_crisis_breakdown_line = { C = nd_yp_follow_through KEY = nd_yp_follow_through_line }
		nd_crisis_breakdown_line = { C = nd_yp_taboo KEY = nd_yp_taboo_line }
```

- [ ] **Step 10: Loc** (`localization/english/te_miscellaneous_l_english.yml`)

Add these lines, keeping the file's alphabetical order where you insert them (the next reload's `organize_loc` re-sorts anyway):

```
 nd_taboo_tt_strike_answer:0 "An answer to a nuclear strike: #G no#! [concept_infamy]. The nuclear taboo, now #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_value')|0]#!, still falls — by half what a first use would cost it."
 nd_taboo_tt_strike_first_use:0 "If it gets through: #R +[GetPlayer.MakeScope.ScriptValue('nd_taboo_infamy_strategic')|0]#! [concept_infamy], and relations #R [GetPlayer.MakeScope.ScriptValue('nd_taboo_world_relations_strategic')|0]#! with every country but theirs. The nuclear taboo stands at #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_value')|0]#!: the higher it stands, the more the world recoils."
 nd_taboo_tt_tactical_first_use:0 "If it gets through: #R +[GetPlayer.MakeScope.ScriptValue('nd_taboo_infamy_tactical')|0]#! [concept_infamy], and relations #R [GetPlayer.MakeScope.ScriptValue('nd_taboo_world_relations_tactical')|0]#! with every country but theirs. The nuclear taboo stands at #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_value')|0]#!: the higher it stands, the more the world recoils."
 nd_yp_taboo_line:0 "#v [THIS.Var('nd_yp_taboo').GetValue|+0]#!  The nuclear taboo: how far the world believes anyone would really do it"
```

- [ ] **Step 11: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/extra_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_crisis_effects.txt common/script_values/nuclear_deterrence_values.txt common/scripted_guis/nuclear_deterrence_sguis.txt common/diplomatic_actions/nuke.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 scripts/analysis/check_localization_files.py && python3 loc_render_audit.py --strict
git add test_nuclear_taboo.py test_nuclear_deterrence.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/extra_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_crisis_effects.txt common/script_values/nuclear_deterrence_values.txt common/scripted_guis/nuclear_deterrence_sguis.txt common/diplomatic_actions/nuke.txt localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: use, threat and doctrine costs scale with it; a twelfth pressure part

<attribution lines>"
```

---

### Task 5: The entry is every country's once the taboo exists

**Files:**
- Modify: `common/scripted_triggers/nuke_triggers.txt` (`nuclear_program_entry_applies`)
- Modify: `common/journal_entries/je_nuclear_program.txt` (the weekly disarmament clean-up's guard; comments)
- Modify: `common/customizable_localization/nuclear_program_custom_loc.txt` (`nd_taboo_status_line`, `nd_taboo_band_name`)
- Modify: `localization/english/te_journal_entries_l_english.yml` (`je_nuclear_program_status_line`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestEveryoneActive`)

**Interfaces:**
- Consumes: `nd_taboo_value`, `nd_taboo_line_*` (Task 1).
- Produces custom loc:
  - `nd_taboo_status_line` (status line only; accessor-free);
  - `nd_taboo_band_name` (accessor-free, usable anywhere): one of `nd_taboo_band_1`…`_5`.

- [ ] **Step 1: Write the failing tests** (change the import line to `from test_nuclear_deterrence import block, loc_keys, loc_value, read, strip_comments`, then append to `test_nuclear_taboo.py`)

```python
NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
PROGRAM_CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_program_custom_loc.txt"


def enclosing_block(text, index):
    """Name of the top-level `name = {` block that contains index."""
    names = list(re.finditer(r"(?m)^(\w+) = \{", text[:index]))
    return names[-1].group(1) if names else None


class TestEveryoneActive(unittest.TestCase):
    def setUp(self):
        self.det = strip_comments(read(DETERRENCE_EFFECTS))

    def test_entry_applies_to_everyone_once_the_taboo_exists(self):
        body = block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_entry_applies")
        self.assertIn("has_global_variable = nd_taboo", body)
        self.assertIn("NOT = { is_country_type = decentralized }", body)

    def test_unarmed_cleanup_runs_from_the_entrys_own_pulses(self):
        monthly = block(self.det, "nd_monthly_update")
        unarmed = monthly[monthly.index("else = {"):]
        self.assertIn("nd_apply_posture_modifiers = yes", unarmed)
        self.assertIn("nd_clear_domestic_stance = yes", unarmed)
        self.assertIn("remove_modifier = nd_upkeep_cost", block(self.det, "nd_apply_posture_modifiers"))
        weekly = block(strip_comments(read(JE)), "on_weekly_pulse")
        self.assertIn("has_variable = nd_arsenal_record", weekly)
        # A disarmed country now keeps the entry, so its weekly clean-up runs
        # every week: taking off a modifier it no longer has would log each time.
        self.assertRegex(weekly, r"limit = \{ has_modifier = nuclear_power \}\s*remove_modifier = nuclear_power")
        self.assertNotRegex(weekly, r"value = 0\s*\}\s*remove_modifier = nuclear_power")

    def test_nothing_else_waits_for_the_entry_to_close(self):
        # With the entry active for every country, a branch that acts only
        # once the entry is gone never runs for a disarmed country. These are
        # the known ones: the two clean-up fallbacks for a world where the
        # entry never activated (the rule off, before the first warhead), and
        # custody adding a missing entry.
        allowed = {("nuclear_deterrence_effects.txt", "nd_country_monthly_cleanup"),
                   ("nuclear_custody_effects.txt", "nd_custody_after_arrival")}
        found = set()
        for path in (ROOT / "common").rglob("nuclear_*.txt"):
            text = strip_comments(read(path))
            for m in re.finditer(r"NOT = \{ has_journal_entry = je_nuclear_program \}", text):
                found.add((path.name, enclosing_block(text, m.start())))
        self.assertEqual(found, allowed)

    def test_status_line_opens_with_the_taboo(self):
        self.assertTrue(loc_value("je_nuclear_program_status_line").startswith(
            "[ROOT.GetCountry.GetCustom('nd_taboo_status_line')]"))

    def test_status_line_targets_are_accessor_free(self):
        body = block(strip_comments(read(PROGRAM_CUSTOM_LOC)), "nd_taboo_status_line")
        keys = re.findall(r"localization_key = (\w+)", body)
        self.assertEqual(keys, ["nuke_line_empty"] + [f"nd_taboo_status_{n}" for n in range(1, 6)])
        for key in keys[1:]:
            value = loc_value(key)
            for accessor in ("GetCountry", "ROOT", "JournalEntry", "GetPlayer"):
                self.assertNotIn(accessor, value, key)

    def test_band_names_exist(self):
        keys = loc_keys()
        for n in range(1, 6):
            self.assertIn(f"nd_taboo_band_{n}", keys)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestEveryoneActive -v`
Expected: failures in the entry, status-line and band-name tests, and in the clean-up test's new `has_modifier = nuclear_power` guard assertion. The "nothing else waits" test already passes; it pins existing behaviour.

- [ ] **Step 3: The entry applies to everyone** (`nuke_triggers.txt`)

Replace the body of `nuclear_program_entry_applies` with:

```
nuclear_program_entry_applies = {
	has_game_rule = nuclear_weapons_enabled
	OR = {
		nuclear_program_has_programme = yes
		nd_is_armed = yes
		nd_in_crisis = yes
		# Once the nuclear taboo exists (nuclear_taboo_effects.txt) the entry
		# is every country's: its panel and status line speak to the countries
		# without the bomb as much as to those with it. Every pulse effect is a
		# cheap no-op for a country that is neither armed, building nor in a
		# crisis (nuclear_deterrence_effects.txt's header).
		AND = {
			has_global_variable = nd_taboo
			NOT = { is_country_type = decentralized }
		}
	}
}
```

Also update its comment header's first sentence to: `# Country scope: the body of je_nuclear_program's \`possible\` — everyone the entry applies to: a country with a programme, one that holds warheads, one party to a nuclear crisis, and — once the nuclear taboo exists — every country.`

- [ ] **Step 4: The entry's weekly disarmament clean-up, and its comments** (`je_nuclear_program.txt`)

The weekly pulse's disarmament block ran at most once while disarmament closed the entry. Now a treaty-disarmed, NPT-bound or renounced country keeps the entry and runs it every week, and an unguarded `remove_modifier` on a modifier it no longer has logs each time. Replace

```
				set_variable = {
					name = nuclear_weapon_program_progress
					value = 0
				}
				remove_modifier = nuclear_power
			}
```

with

```
				set_variable = {
					name = nuclear_weapon_program_progress
					value = 0
				}
				# Guarded: the entry no longer closes on disarmament, so this
				# runs every week for a disarmed country.
				if = {
					limit = { has_modifier = nuclear_power }
					remove_modifier = nuclear_power
				}
			}
```

Then update the comments:

Replace the comment above `possible`:

```
	# Body single-sourced in common/scripted_triggers/nuke_triggers.txt. With
	# can_deactivate = yes the entry drops back to inactive the moment this goes
	# false — a disarmament settlement or the UN's NPT modifier landing on a
	# country that is not in a crisis, before the weekly pulse can run — and the
	# status line, which asks the same triggers, explains why.
```

with

```
	# Body single-sourced in common/scripted_triggers/nuke_triggers.txt. Once
	# the nuclear taboo exists it holds for every non-decentralized country, so
	# the entry no longer closes when a country disarms: whatever a disarmed
	# country must shed (posture modifiers, upkeep, the taboo's possession cost,
	# interest-group bands) comes off because it is not armed, from the entry's
	# own pulses. Before the first warhead (and with the rule off) can_deactivate
	# still lets a disarmed country's entry close, and the status line explains
	# why.
```

and the comment above `status_desc`:

```
	# One line (two while armed or in a crisis). Unlike the widgets, status_desc
	# is rendered by gui/journal_entry.gui:188 with no IsActive gate, so this is
	# the only surface that can speak for a *deactivated* entry — the state a
	# disarmament settlement puts it into — and for an inactive one shown to a
	# country with the science but not the standing.
```

with

```
	# The nuclear taboo first, then the programme's line (two while armed or in
	# a crisis). Unlike the widgets, status_desc is rendered by
	# gui/journal_entry.gui:188 with no IsActive gate, so it also speaks for an
	# inactive entry shown before the first warhead to a country with the
	# science but not the standing.
```

- [ ] **Step 5: The custom loc** (`nuclear_program_custom_loc.txt`)

Insert directly after the `nuclear_program_status_line` block (still inside the status-line section, before the "WIDGET-ONLY BLOCKS" divider):

```

# The nuclear taboo, first on the status line (nuclear_taboo_values.txt). Once
# it exists the entry is active for every country, and for most of them the
# taboo is the whole story. Accessor-free: the score is a global, read in the
# targets with GetGlobalVariable, which needs no country root; the bands are
# the live score's (nd_taboo_line_*), not the last one announced.
nd_taboo_status_line = {
	type = country
	random_valid = no

	text = {
		trigger = { NOT = { has_global_variable = nd_taboo } }
		localization_key = nuke_line_empty
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_fragile }
		localization_key = nd_taboo_status_1
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_established }
		localization_key = nd_taboo_status_2
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_strong }
		localization_key = nd_taboo_status_3
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_absolute }
		localization_key = nd_taboo_status_4
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_status_5
	}
}

# The band's name alone, for the widget and events. Accessor-free, so it is
# safe from a status line, a widget and an event alike.
nd_taboo_band_name = {
	type = country
	random_valid = no

	text = {
		trigger = { nd_taboo_value < nd_taboo_line_fragile }
		localization_key = nd_taboo_band_1
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_established }
		localization_key = nd_taboo_band_2
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_strong }
		localization_key = nd_taboo_band_3
	}
	text = {
		trigger = { nd_taboo_value < nd_taboo_line_absolute }
		localization_key = nd_taboo_band_4
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_band_5
	}
}
```

- [ ] **Step 6: Loc**

In `te_journal_entries_l_english.yml`, replace the value of `je_nuclear_program_status_line` with:

```
 je_nuclear_program_status_line:0 "[ROOT.GetCountry.GetCustom('nd_taboo_status_line')][ROOT.GetCountry.GetCustom('nuclear_program_status_line')] Warheads held: #N [ROOT.GetCountry.MakeScope.ScriptValue('nuclear_program_display_stockpile')|0]#!.[ROOT.GetCountry.GetCustom('nd_status_line')]"
```

In `te_miscellaneous_l_english.yml`, add:

```
 nd_taboo_band_1:0 "Normalised"
 nd_taboo_band_2:0 "Fragile"
 nd_taboo_band_3:0 "Established"
 nd_taboo_band_4:0 "Strong"
 nd_taboo_band_5:0 "Absolute"
 nd_taboo_status_1:0 "The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, #bold $nd_taboo_band_1$#!: the bomb is treated as one weapon among others.\n"
 nd_taboo_status_2:0 "The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, #bold $nd_taboo_band_2$#!: the bomb is feared, but its use is still argued for.\n"
 nd_taboo_status_3:0 "The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, #bold $nd_taboo_band_3$#!: using the bomb is widely held to be wrong.\n"
 nd_taboo_status_4:0 "The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, #bold $nd_taboo_band_4$#!: the bomb is seen as unusable, and even holding one draws censure.\n"
 nd_taboo_status_5:0 "The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, #bold $nd_taboo_band_5$#!: the bomb is beyond the pale, and holding one marks a state apart.\n"
```

- [ ] **Step 7: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/nuke_triggers.txt common/journal_entries/je_nuclear_program.txt common/customizable_localization/nuclear_program_custom_loc.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 scripts/analysis/check_localization_files.py && python3 loc_render_audit.py --strict
git add test_nuclear_taboo.py common/scripted_triggers/nuke_triggers.txt common/journal_entries/je_nuclear_program.txt common/customizable_localization/nuclear_program_custom_loc.txt localization/english/te_journal_entries_l_english.yml localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: the entry is every country's once the taboo exists; the status line opens with it

<attribution lines>"
```

---

### Task 6: Possession: the bomb's prestige and domestic burden

**Files:**
- Create: `common/static_modifiers/nuclear_taboo_modifiers.txt`
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING + POSSESSION)
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_country_monthly`, `nd_taboo_refresh_possession`)
- Modify: `common/journal_entries/je_nuclear_program.txt` (`on_monthly_pulse`)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_ig_term_possession_value`, `nd_ig_stance_value`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_ig_store_opinion`, `nd_ig_clear_opinion`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Modify: `test_nuclear_deterrence.py` (`IG_VARS`)
- Test: `test_nuclear_taboo.py` (`TestPossession`)

**Interfaces:**
- Produces:
  - script values (country): `nd_taboo_factor_value` (any scope), `nd_taboo_arsenal_factor_value`, `nd_taboo_burden_value` (0–1), `nd_disp_taboo_burden_pct`, `nd_disp_taboo_prestige_cost_pct`, `nd_disp_taboo_leverage_cost_pct`;
  - constants `nd_taboo_burden_step_mild`, `nd_taboo_burden_step_full`;
  - effects `nd_taboo_country_monthly`, `nd_taboo_refresh_possession` (ROOT = the country);
  - variable `nd_taboo_burden_cached` (never removed).

- [ ] **Step 1: Write the failing tests**

In `test_nuclear_deterrence.py`, change `IG_VARS` to end `…, "nd_ig_term_business", "nd_ig_term_possession", "nd_ig_stance"]`. Append to `test_nuclear_taboo.py`:

```python
TABOO_MODIFIERS = ROOT / "common/static_modifiers/nuclear_taboo_modifiers.txt"


class TestPossession(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.effects = strip_comments(read(TABOO_EFFECTS))

    def test_modifier_matches_its_display_constants(self):
        body = block(strip_comments(read(TABOO_MODIFIERS)), "nd_taboo_possession_cost")
        prestige = constant(self.values, "nd_taboo_possession_prestige_pct") / 100
        leverage = constant(self.values, "nd_taboo_possession_leverage_pct") / 100
        self.assertIn(f"country_prestige_mult = {prestige:g}", body)
        self.assertIn(f"country_leverage_generation_mult = {leverage:g}", body)

    def test_burden_is_a_product_zero_below_the_floor(self):
        burden = block(self.values, "nd_taboo_burden_value")
        self.assertIn("value = nd_taboo_factor_value", burden)
        self.assertIn("multiply = nd_taboo_arsenal_factor_value", burden)
        self.assertIn("nd_is_armed = yes", burden)
        factor = block(self.values, "nd_taboo_factor_value")
        self.assertIn("subtract = nd_taboo_burden_floor", factor)
        self.assertIn("min = 0", factor)

    def test_refresh_runs_with_the_country_as_root(self):
        body = block(self.effects, "nd_taboo_refresh_possession")
        self.assertIn("multiplier = root.var:nd_taboo_burden_cached", body)
        self.assertIn("je:je_nuclear_program ?=", body)
        self.assertNotIn("remove_variable = nd_taboo_burden_cached", self.effects)
        self.assertEqual(block(self.effects, "nd_taboo_country_monthly").count("nd_taboo_refresh_possession = yes"), 1)
        self.assertNotIn("nd_taboo_refresh_possession", block(self.effects, "nd_taboo_monthly_update"))
        self.assertIn("nd_taboo_country_monthly = yes", block(strip_comments(read(JE)), "on_monthly_pulse"))

    def test_restraint_groups_weigh_the_arsenal(self):
        dv = strip_comments(read(DETERRENCE_VALUES))
        term = block(dv, "nd_ig_term_possession_value")
        for needle in ("nd_ig_class_restraint = yes", "nd_taboo_burden_value >= nd_taboo_burden_step_full",
                       "nd_taboo_burden_value >= nd_taboo_burden_step_mild"):
            self.assertIn(needle, term)
        self.assertNotIn("nd_ig_posture_judged", term)
        self.assertIn("add = nd_ig_term_possession_value", block(dv, "nd_ig_stance_value"))
        self.assertIn("THIS.Var('nd_ig_term_possession').GetValue", loc_value("nd_home_terms_restraint"))

    def test_modifier_has_loc(self):
        keys = loc_keys()
        self.assertIn("nd_taboo_possession_cost", keys)
        self.assertIn("nd_taboo_possession_cost_desc", keys)
```

Add `NEW_FILES.append(TABOO_MODIFIERS)` directly below the `TABOO_MODIFIERS` constant, so the BOM test covers it.

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestPossession test_nuclear_deterrence.TestInterestGroupOpinion -v`
Expected: `FileNotFoundError` for the modifiers file, and `nd_ig_term_possession` missing.

- [ ] **Step 3: Constants and values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_burden_floor = 40
nd_taboo_burden_span = 60
nd_taboo_arsenal_saturation = 50
nd_taboo_arsenal_floor_factor = 0.2
nd_taboo_arsenal_span_factor = 0.8
nd_taboo_burden_step_mild = 0.333
nd_taboo_burden_step_full = 0.667
nd_taboo_possession_prestige_pct = -45
nd_taboo_possession_leverage_pct = -25
```

Append a section:

```
# ---- POSSESSION (spec §4.4) — country scope unless noted ----------------------
# One number drives both costs: the taboo's weight (0 below 40, 1 at 100) times
# the arsenal's size (0.2 for a token force, 1 from fifty warheads, the count
# the upkeep's custody term stops at). A minimal deterrent in a world that
# holds the bomb in horror still costs a quarter of a big arsenal.

# Scope: any
nd_taboo_factor_value = {
	value = nd_taboo_value
	subtract = nd_taboo_burden_floor
	divide = nd_taboo_burden_span
	min = 0
	max = 1
}

nd_taboo_arsenal_factor_value = {
	value = nd_stockpile
	max = nd_taboo_arsenal_saturation
	divide = nd_taboo_arsenal_saturation
	multiply = nd_taboo_arsenal_span_factor
	add = nd_taboo_arsenal_floor_factor
}

nd_taboo_burden_value = {
	value = 0
	if = {
		limit = { nd_is_armed = yes }
		value = nd_taboo_factor_value
		multiply = nd_taboo_arsenal_factor_value
	}
}

nd_disp_taboo_burden_pct = {
	value = nd_taboo_burden_value
	multiply = 100
	round = yes
}

# What the burden costs now, in the percentages nd_taboo_possession_cost shows
# (its fields are these constants / 100; test_nuclear_taboo.py pins them).
nd_disp_taboo_prestige_cost_pct = {
	value = nd_taboo_burden_value
	multiply = nd_taboo_possession_prestige_pct
	round = yes
}

nd_disp_taboo_leverage_cost_pct = {
	value = nd_taboo_burden_value
	multiply = nd_taboo_possession_leverage_pct
	round = yes
}
```

- [ ] **Step 4: Create `common/static_modifiers/nuclear_taboo_modifiers.txt`** (BOM first)

```
﻿# ============================================================================
# THE NUCLEAR TABOO — static modifiers
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md. Writers:
#   nd_taboo_possession_cost   nd_taboo_refresh_possession (je_nuclear_program
#                              scope, multiplier = root.var:nd_taboo_burden_cached)
# ============================================================================

# The bomb's standing, turned against its holder as the world comes to hold it
# in horror: per unit of burden (0-1). nuclear_power's +30 % prestige and +25 %
# leverage generation are left as they are; at a full burden this takes a
# fifty-warhead arsenal to -15 % prestige and no leverage bonus. Its fields are
# nd_taboo_possession_prestige_pct and _leverage_pct / 100.
nd_taboo_possession_cost = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_negative.dds
	country_prestige_mult = -0.45
	country_leverage_generation_mult = -0.25
}
```

- [ ] **Step 5: The country half and the refresh** (`nuclear_taboo_effects.txt`, append)

```
# ----------------------------------------------------------------------------
# THE COUNTRY HALF — je_nuclear_program's monthly pulse, ROOT = this country
# ----------------------------------------------------------------------------
# Every per-country piece of the taboo that applies a modifier or must run
# with ROOT = the country. Each refresh below is called exactly once here: a
# second call in the same block would read a modifier the first had just
# added or removed as still absent or present.
nd_taboo_country_monthly = {
	if = {
		limit = { has_global_variable = nd_taboo }
		nd_taboo_refresh_possession = yes
	}
}

# The possession cost on the entry (je_nuclear_program, the upkeep's scope).
# The engine re-reads a modifier's multiplier on later ticks, so the modifier
# is put on once and the cache updated each month — nd_apply_posture_modifiers'
# upkeep pattern. The cache is never removed (modifier_multiplier_var_audit);
# ROOT must be this country, which is why this runs only from the entry's
# pulse. It comes off when the burden is 0 — below a taboo of 40, or unarmed:
# the entry no longer closes on disarmament.
nd_taboo_refresh_possession = {
	set_variable = { name = nd_taboo_burden_cached value = nd_taboo_burden_value }
	if = {
		limit = { var:nd_taboo_burden_cached > 0 }
		je:je_nuclear_program ?= {
			if = {
				limit = { NOT = { has_modifier = nd_taboo_possession_cost } }
				add_modifier = {
					name = nd_taboo_possession_cost
					multiplier = root.var:nd_taboo_burden_cached
				}
			}
		}
	}
	else = {
		je:je_nuclear_program ?= {
			if = {
				limit = { has_modifier = nd_taboo_possession_cost }
				remove_modifier = nd_taboo_possession_cost
			}
		}
	}
}
```

- [ ] **Step 6: Call it from the entry** (`je_nuclear_program.txt`)

Replace

```
	on_monthly_pulse = {
		effect = {
			nd_monthly_update = yes
			nd_crisis_target_watchdog = yes
		}
	}
```

with

```
	on_monthly_pulse = {
		effect = {
			nd_monthly_update = yes
			nd_crisis_target_watchdog = yes
			# The nuclear taboo's country half: the possession cost, the exits
			# and the history samples (nuclear_taboo_effects.txt). ROOT = this
			# country, which the possession cost's multiplier needs.
			nd_taboo_country_monthly = yes
		}
	}
```

- [ ] **Step 7: The restraint groups' term** (`nuclear_deterrence_values.txt`)

Insert directly above the comment `# The capped total the approval band is read from…` (the one above `nd_ig_stance_value`):

```
# The nuclear taboo (nuclear_taboo_values.txt §4.4): restraint groups object to
# the arsenal itself once the world holds the bomb in horror, and more to a big
# one. Not tenure-gated — holding warheads is not a posture choice.
nd_ig_term_possession_value = {
	value = 0
	if = {
		limit = { nd_ig_class_restraint = yes }
		owner = {
			if = {
				limit = { nd_taboo_burden_value >= nd_taboo_burden_step_full }
				add = -2
			}
			else_if = {
				limit = { nd_taboo_burden_value >= nd_taboo_burden_step_mild }
				add = -1
			}
		}
	}
}

```

In `nd_ig_stance_value`, replace `add = nd_ig_term_business_value` with

```
	add = nd_ig_term_business_value
	add = nd_ig_term_possession_value
```

- [ ] **Step 8: Store and clear it** (`nuclear_deterrence_effects.txt`)

In `nd_ig_store_opinion`, replace

```
	set_variable = { name = nd_ig_term_business value = nd_ig_term_business_value }
```

with

```
	set_variable = { name = nd_ig_term_business value = nd_ig_term_business_value }
	set_variable = { name = nd_ig_term_possession value = nd_ig_term_possession_value }
```

In `nd_ig_clear_opinion`, replace

```
	if = {
		limit = { has_variable = nd_ig_term_business }
		remove_variable = nd_ig_term_business
	}
```

with

```
	if = {
		limit = { has_variable = nd_ig_term_business }
		remove_variable = nd_ig_term_business
	}
	if = {
		limit = { has_variable = nd_ig_term_possession }
		remove_variable = nd_ig_term_possession
	}
```

- [ ] **Step 9: Loc** (`te_miscellaneous_l_english.yml`)

Replace the value of `nd_home_terms_restraint` with:

```
 nd_home_terms_restraint:0 "#lore       doctrine [THIS.Var('nd_ig_term_doctrine').GetValue|+0] · readiness [THIS.Var('nd_ig_term_readiness').GetValue|+0] · launch authority [THIS.Var('nd_ig_term_authority').GetValue|+0] · the arsenal itself [THIS.Var('nd_ig_term_possession').GetValue|+0]#!"
```

Add:

```
 nd_taboo_possession_cost:0 "The Burden of the Bomb"
 nd_taboo_possession_cost_desc:0 "The world holds nuclear weapons in horror, and it holds that horror against those who keep them. The weight grows with the nuclear taboo above 40 and with our arsenal up to fifty warheads: a small deterrent is tolerated far more than a large one."
```

- [ ] **Step 10: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py common/static_modifiers/nuclear_taboo_modifiers.txt common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/journal_entries/je_nuclear_program.txt common/script_values/nuclear_deterrence_values.txt common/scripted_effects/nuclear_deterrence_effects.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 modifier_multiplier_var_audit.py --strict && python3 je_immediate_reset_audit.py --strict
git add test_nuclear_taboo.py test_nuclear_deterrence.py common/static_modifiers/nuclear_taboo_modifiers.txt common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/journal_entries/je_nuclear_program.txt common/script_values/nuclear_deterrence_values.txt common/scripted_effects/nuclear_deterrence_effects.txt localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: holding the bomb costs prestige, leverage and restraint groups' approval

<attribution lines>"
```

---

### Task 7: The unilateral exits: dismantle, reduce, resume

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING + EXITS)
- Modify: `common/scripted_triggers/nuclear_taboo_triggers.txt`
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (EXITS; `nd_taboo_country_monthly`)
- Modify: `common/static_modifiers/nuclear_taboo_modifiers.txt`
- Create: `events/nuclear_taboo_events.txt` (namespace + `.20`)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_can_set_readiness`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_weekly_update`)
- Modify: `common/scripted_effects/nuclear_custody_effects.txt` (`nd_cw_dismantle_as`, `nd_bp_accept`)
- Modify: `common/treaty_articles/extra_treaty_articles.txt` (`nuclear_disarmament`'s `on_entry_into_force`)
- Modify: `common/scripted_effects/nuclear_weapon_effects.txt` (`nuclear_program_refresh_state_effect`)
- Modify: `common/customizable_localization/nuclear_program_custom_loc.txt` (status line, rate note, and the widget-only `nd_taboo_arsenal_status`, `nd_taboo_ceiling_value`, `nd_taboo_burden_hint`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (ops 60–64, header table)
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (the Arsenal rows, header table)
- Modify: `common/decisions/extra_decisions.txt`
- Modify: `docs/systems/journal_entry_systems.md` (**CRLF**: op table rows)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestExits`)

**Interfaces:**
- Consumes: `nd_taboo_ledger_add`, `nd_taboo_ledger_add_weighted`, `nd_taboo_ledger_commit`, `nd_taboo_country_monthly`, `nd_taboo_infamy_threat`, `nd_set_readiness_target_0`, `nd_ledger_refresh`, `nd_snap_public_estimate`, `nd_apply_posture_modifiers`, `nd_in_civil_war`.
- Produces:
  - triggers (country): `nd_taboo_is_dismantling`, `nd_taboo_programme_should_be_held`, `nd_taboo_can_dismantle`, `nd_taboo_can_lower_ceiling`, `nd_taboo_can_raise_ceiling`, `nd_taboo_can_halt`, `nd_taboo_ai_would_resume`;
  - effects (country, ROOT = it):
    - `nd_taboo_note_renunciation = { WARHEADS = <value> }`;
    - `nd_taboo_refresh_held`;
    - `nd_taboo_ceiling_lower`, `nd_taboo_ceiling_raise`, `nd_taboo_ceiling_lift`;
    - `nd_taboo_dismantle_begin` / `nd_taboo_dismantle_stop` (cores, no refresh) and `nd_taboo_dismantle_start` / `nd_taboo_dismantle_halt` (wrappers that refresh the hold), `nd_taboo_dismantle_step`, `nd_taboo_dismantle_complete`;
    - `nd_taboo_retire_step`, `nd_taboo_renunciation_rewards`, `nd_taboo_resume`;
  - variables `nd_warhead_ceiling`, `nd_dismantle_months_left`, `nd_dismantle_per_month`, `nd_dismantle_start_stock`, `nd_renounced` (the year), `nd_renounced_locked` (a flag), and `nd_taboo_renounce_mult` (never removed);
  - static modifiers `nd_taboo_renounced`, `nd_taboo_programme_held`, `nd_taboo_renunciation_prestige`;
  - event `nuclear_taboo.20`;
  - decision `nd_taboo_resume_programme`;
  - posture ops 60–64.

- [ ] **Step 1: Write the failing tests**

Change the import line to `from test_nuclear_deterrence import block, loc_keys, loc_value, read, sgui_ops, strip_comments`, then append:

```python
TABOO_EVENTS = ROOT / "events/nuclear_taboo_events.txt"
NEW_FILES.append(TABOO_EVENTS)
DETERRENCE_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
DETERRENCE_SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
CUSTODY_EFFECTS = ROOT / "common/scripted_effects/nuclear_custody_effects.txt"
TREATY_ARTICLES = ROOT / "common/treaty_articles/extra_treaty_articles.txt"
DECISIONS = ROOT / "common/decisions/extra_decisions.txt"

ZEROING = "name = nuclear_weapon_stockpile value = 0"


class TestExits(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.triggers = strip_comments(read(TABOO_TRIGGERS))
        self.custody = strip_comments(read(CUSTODY_EFFECTS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))

    def test_renunciation_is_idempotent_and_read_before_zeroing(self):
        body = block(self.taboo, "nd_taboo_note_renunciation")
        self.assertRegex(body, r"NOT = \{\s*AND = \{\s*has_variable = nd_renounced\s*nd_is_armed = no\s*\}\s*\}")
        self.assertIn("$WARHEADS$ > 0", body)
        self.assertIn("name = nd_renounced value = year", body)
        call = "nd_taboo_note_renunciation = { WARHEADS = nd_stockpile }"
        for name in ("nd_bp_accept", "nd_cw_dismantle_as"):
            b = block(self.custody, name)
            self.assertLess(b.index(call), b.index(ZEROING), name)
        on_entry = block(block(strip_comments(read(TREATY_ARTICLES)), "nuclear_disarmament"), "on_entry_into_force")
        self.assertLess(on_entry.index(call), on_entry.index(ZEROING))
        complete = block(self.taboo, "nd_taboo_dismantle_complete")
        self.assertLess(complete.index("nd_taboo_note_renunciation = { WARHEADS = var:nd_dismantle_start_stock }"),
                        complete.index(ZEROING))

    def test_every_ceiling_change_refreshes_the_hold(self):
        for name in ("nd_taboo_ceiling_lower", "nd_taboo_ceiling_raise", "nd_taboo_ceiling_lift",
                     "nd_taboo_dismantle_start", "nd_taboo_dismantle_halt"):
            self.assertIn("nd_taboo_refresh_held = yes", block(self.taboo, name), name)
        refresh = block(self.taboo, "nd_taboo_refresh_held")
        self.assertIn("nd_taboo_programme_should_be_held = yes", refresh)
        self.assertIn("remove_modifier = nd_taboo_programme_held", refresh)
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertEqual(monthly.count("nd_taboo_refresh_held = yes"), 1)
        self.assertNotIn("nd_taboo_refresh_held", block(self.taboo, "nd_taboo_dismantle_complete"))
        self.assertNotIn("nd_taboo_refresh_possession", block(self.taboo, "nd_taboo_dismantle_complete"))

    def test_exits_go_through_the_custody_ledger(self):
        for name in ("nd_taboo_dismantle_step", "nd_taboo_retire_step", "nd_taboo_dismantle_complete"):
            body = block(self.taboo, name)
            self.assertIn("nd_ledger_refresh = yes", body, name)
            self.assertNotIn("loose", body, name)

    def test_panel_ops(self):
        sguis = strip_comments(read(DETERRENCE_SGUIS))
        for part in ("is_valid", "effect"):
            ops = sgui_ops(sguis, "nd_posture_sgui", part)
            for op in range(60, 65):
                self.assertIn(op, ops, f"{part} lacks op {op}")

    def test_readiness_stays_in_storage_while_dismantling(self):
        gate = block(strip_comments(read(DETERRENCE_TRIGGERS)), "nd_can_set_readiness")
        self.assertRegex(gate, r"OR = \{\s*nd_taboo_is_dismantling = no\s*var:nd_readiness_target > \$R\$\s*\}")
        self.assertIn("nd_taboo_is_dismantling = yes", block(self.det, "nd_weekly_update"))

    def test_renounced_state_is_rebuilt_from_its_variable(self):
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertIn("has_variable = nd_renounced_locked", monthly)
        self.assertIn("add_modifier = { name = nd_taboo_renounced }", monthly)
        mods = strip_comments(read(TABOO_MODIFIERS))
        self.assertIn("country_nuclear_disarmament_bool = yes", block(mods, "nd_taboo_renounced"))
        self.assertIn("country_nuclear_program_pause_bool = yes", block(mods, "nd_taboo_programme_held"))

    def test_breakout_is_booked_once(self):
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertIn("POINTS = nd_taboo_ledger_breakout", monthly)
        self.assertIn("remove_variable = nd_renounced", monthly)

    def test_resume_decision(self):
        body = block(strip_comments(read(DECISIONS)), "nd_taboo_resume_programme")
        self.assertIn("has_modifier = nd_taboo_renounced", body)
        self.assertIn("nd_taboo_resume = yes", body)
        self.assertIn("nd_taboo_ai_would_resume = yes", body)

    def test_programme_status_reports_the_hold(self):
        body = block(strip_comments(read(WEAPON_EFFECTS)), "nuclear_program_refresh_state_effect")
        five = body.index("name = nuclear_program_last_status value = 5")
        four = body.index("name = nuclear_program_last_status value = 4")
        three = body.index("name = nuclear_program_last_status value = 3")
        self.assertLess(five, four)
        self.assertLess(four, three)

    def test_last_warhead_event(self):
        events = strip_comments(read(TABOO_EVENTS))
        body = block(events, "nuclear_taboo.20")
        self.assertIn("nd_taboo_renunciation_rewards = yes", body)
        self.assertIn("name = nd_taboo_renounce_mult value = nd_taboo_renounce_mult_value", block(body, "immediate"))
        self.assertIn("trigger_event = { id = nuclear_taboo.20 }", block(self.taboo, "nd_taboo_dismantle_complete"))

    def test_exit_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_renounced", "nd_taboo_renounced_desc", "nd_taboo_programme_held",
                    "nd_taboo_programme_held_desc", "nd_taboo_renunciation_prestige",
                    "nd_taboo_renunciation_prestige_desc", "nd_taboo_resume_programme",
                    "nd_taboo_resume_programme_desc", "nuclear_taboo.20.t", "nuclear_taboo.20.d",
                    "nuclear_taboo.20.f", "nuclear_taboo.20.a", "nuclear_program_status_held",
                    "nuclear_program_status_dismantling", "nuclear_program_rate_note_held"):
            self.assertIn(key, keys, key)
        for text in (read(TABOO_EFFECTS), read(TABOO_TRIGGERS)):
            for key in re.findall(r"text = (nd_taboo_tt_\w+)", text):
                self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestExits -v`
Expected: errors for the missing events file and the missing effects.

- [ ] **Step 3: Constants and values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_ledger_renounce_base = 1
nd_taboo_ledger_renounce_per_warhead = 0.1
nd_taboo_ledger_renounce_cap = 6
nd_taboo_ledger_retire_per_warhead = 0.05
nd_taboo_ledger_breakout = -2
nd_taboo_ledger_halt = -1
nd_taboo_dismantle_base_months = 12
nd_taboo_dismantle_free_warheads = 20
nd_taboo_dismantle_warheads_per_month = 10
nd_taboo_dismantle_max_months = 36
nd_taboo_retire_share = 0.1
nd_taboo_ceiling_step_small = 1
nd_taboo_ceiling_step_medium = 5
nd_taboo_ceiling_step_large = 25
nd_taboo_ceiling_medium_from = 10
nd_taboo_ceiling_large_from = 50
nd_taboo_halt_credibility = 10
nd_taboo_renounce_relations_per_point = 0.2
nd_taboo_resume_relations_per_point = -0.2
```

Append a section:

```
# ---- EXITS (spec §5) — country scope --------------------------------------------

# The ceiling in force, or the stock when there is none (the stepper steps
# from here).
nd_taboo_ceiling_now_value = {
	value = nd_stockpile
	if = {
		limit = { has_variable = nd_warhead_ceiling }
		value = var:nd_warhead_ceiling
	}
}

# 1 warhead at a time up to 10, 5 up to 50, then 25.
nd_taboo_ceiling_step_value = {
	value = nd_taboo_ceiling_step_small
	if = {
		limit = { nd_taboo_ceiling_now_value > nd_taboo_ceiling_medium_from }
		value = nd_taboo_ceiling_step_medium
	}
	if = {
		limit = { nd_taboo_ceiling_now_value > nd_taboo_ceiling_large_from }
		value = nd_taboo_ceiling_step_large
	}
}

nd_taboo_ceiling_lowered_value = {
	value = nd_taboo_ceiling_now_value
	subtract = nd_taboo_ceiling_step_value
	min = 1
}

nd_taboo_ceiling_raised_value = {
	value = nd_taboo_ceiling_now_value
	add = nd_taboo_ceiling_step_value
}

nd_taboo_half_arsenal_value = {
	value = nd_stockpile
	divide = 2
	floor = yes
	min = 1
}

# 12 months, +1 per 10 warheads above 20, at most 36.
nd_taboo_dismantle_months_value = {
	value = nd_stockpile
	subtract = nd_taboo_dismantle_free_warheads
	min = 0
	divide = nd_taboo_dismantle_warheads_per_month
	floor = yes
	add = nd_taboo_dismantle_base_months
	max = nd_taboo_dismantle_max_months
}

nd_taboo_dismantle_per_month_value = {
	value = nd_stockpile
	divide = nd_taboo_dismantle_months_value
	ceiling = yes
	min = 1
}

# A tenth of the excess over the ceiling, at least one.
nd_taboo_retire_this_month_value = {
	value = 0
	if = {
		limit = {
			has_variable = nd_warhead_ceiling
			nd_stockpile > var:nd_warhead_ceiling
		}
		value = nd_stockpile
		subtract = var:nd_warhead_ceiling
		multiply = nd_taboo_retire_share
		ceiling = yes
		min = 1
	}
}

# Scope: any
nd_taboo_renounce_mult_value = {
	value = nd_taboo_value
	divide = 100
}

nd_taboo_renounce_relations_value = {
	value = nd_taboo_value
	multiply = nd_taboo_renounce_relations_per_point
	round = yes
}

nd_taboo_resume_relations_value = {
	value = nd_taboo_value
	multiply = nd_taboo_resume_relations_per_point
	round = yes
}

nd_disp_warhead_ceiling = {
	value = 0
	if = {
		limit = { has_variable = nd_warhead_ceiling }
		value = var:nd_warhead_ceiling
	}
}

nd_disp_dismantle_months_left = {
	value = 0
	if = {
		limit = { has_variable = nd_dismantle_months_left }
		value = var:nd_dismantle_months_left
	}
}

nd_disp_dismantle_per_month = {
	value = 0
	if = {
		limit = { has_variable = nd_dismantle_per_month }
		value = var:nd_dismantle_per_month
	}
}

# The largest arsenal at which the burden would fall below the domestic step
# it is on now (for the ceiling's hint): solves factor x (0.2 + 0.8 w / 50) <
# step for w. 0 when there is no step to lose; below 1 when only dismantling
# gets there.
nd_disp_taboo_step_down_warheads = {
	value = 0
	if = {
		limit = {
			nd_taboo_factor_value > 0
			nd_taboo_burden_value >= nd_taboo_burden_step_full
		}
		value = nd_taboo_burden_step_full
	}
	else_if = {
		limit = {
			nd_taboo_factor_value > 0
			nd_taboo_burden_value >= nd_taboo_burden_step_mild
		}
		value = nd_taboo_burden_step_mild
	}
	if = {
		limit = { nd_taboo_burden_value >= nd_taboo_burden_step_mild }
		divide = nd_taboo_factor_value
		subtract = nd_taboo_arsenal_floor_factor
		divide = nd_taboo_arsenal_span_factor
		multiply = nd_taboo_arsenal_saturation
		ceiling = yes
		subtract = 1
		min = -1
	}
}
```

- [ ] **Step 4: Triggers** (append to `nuclear_taboo_triggers.txt`)

```

# ---- EXITS (spec §5) — country scope --------------------------------------------

nd_taboo_is_dismantling = {
	has_variable = nd_dismantle_months_left
}

# The programme builds nothing while dismantling, or at or above our ceiling
# (nd_taboo_programme_held carries the programme-pause flag).
nd_taboo_programme_should_be_held = {
	OR = {
		nd_taboo_is_dismantling = yes
		AND = {
			has_variable = nd_warhead_ceiling
			nd_stockpile >= var:nd_warhead_ceiling
		}
	}
}

nd_taboo_can_dismantle = {
	custom_tooltip = {
		text = nd_tt_need_arsenal
		nd_is_armed = yes
	}
	custom_tooltip = {
		text = nd_taboo_tt_already_dismantling
		nd_taboo_is_dismantling = no
	}
	custom_tooltip = {
		text = nd_taboo_tt_need_peace
		is_at_war = no
	}
	custom_tooltip = {
		text = nd_taboo_tt_need_no_crisis
		nd_in_crisis = no
	}
	custom_tooltip = {
		text = nd_taboo_tt_need_no_civil_war
		nd_in_civil_war = no
	}
}

nd_taboo_can_lower_ceiling = {
	custom_tooltip = {
		text = nd_tt_need_arsenal
		nd_is_armed = yes
	}
	custom_tooltip = {
		text = nd_taboo_tt_dismantling_owns_it
		nd_taboo_is_dismantling = no
	}
	custom_tooltip = {
		text = nd_taboo_tt_ceiling_at_floor
		nd_taboo_ceiling_now_value > 1
	}
}

# Raising and lifting: there must be a ceiling to move.
nd_taboo_can_raise_ceiling = {
	custom_tooltip = {
		text = nd_taboo_tt_no_ceiling
		has_variable = nd_warhead_ceiling
	}
	custom_tooltip = {
		text = nd_taboo_tt_dismantling_owns_it
		nd_taboo_is_dismantling = no
	}
}

nd_taboo_can_halt = {
	custom_tooltip = {
		text = nd_taboo_tt_not_dismantling
		nd_taboo_is_dismantling = yes
	}
}

# The AI takes the bomb up again when an armed country threatens it — at war
# with it, or an antagonistic armed rival — in a world that no longer holds the
# bomb in much horror (below 50).
nd_taboo_ai_would_resume = {
	nd_taboo_value < nd_taboo_line_established
	save_temporary_scope_as = nd_tb_self
	any_country = {
		nd_believed_armed = yes
		OR = {
			has_war_with = scope:nd_tb_self
			AND = {
				has_diplomatic_pact = { who = scope:nd_tb_self type = rivalry }
				has_attitude = { who = scope:nd_tb_self attitude = antagonistic }
			}
		}
	}
}
```

- [ ] **Step 5: Static modifiers** (append to `nuclear_taboo_modifiers.txt`, and add these three writers to its header table)

```

# We renounced the bomb (Dismantle the Arsenal). The disarmament flag makes
# every gate built for a treaty-disarmed country apply: no programme, not
# armed, the NPT's enforcement treats us as non-nuclear. Mirrored by the flag
# variable nd_renounced_locked and rebuilt from it (nd_taboo_country_monthly).
nd_taboo_renounced = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	country_nuclear_disarmament_bool = yes
}

# The programme held: at or above our arsenal ceiling, or while dismantling.
# The programme-pause article's flag: funding zeroed, no increase allowed.
nd_taboo_programme_held = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	country_nuclear_program_pause_bool = yes
}

# A renunciation the world honours: 20 years, decaying, multiplier = the taboo
# / 100 when the last warhead went (root.var:nd_taboo_renounce_mult).
nd_taboo_renunciation_prestige = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_prestige_mult = 0.2
}
```

Header lines to add:

```
#   nd_taboo_renounced               nd_taboo_dismantle_complete, rebuilt by
#                                    nd_taboo_country_monthly; off: nd_taboo_resume
#   nd_taboo_programme_held          nd_taboo_refresh_held (country scope)
#   nd_taboo_renunciation_prestige   nd_taboo_renunciation_rewards (nuclear_taboo.20)
```

- [ ] **Step 6: Effects** (append to `nuclear_taboo_effects.txt`, above the COUNTRY HALF section)

```
# ----------------------------------------------------------------------------
# EXITS (spec §5) — country scope, ROOT = the country
# ----------------------------------------------------------------------------

# An arsenal given up, by any path: Dismantle the Arsenal on completion, the
# nuclear_disarmament article, the Budapest path (nd_bp_accept), the civil-war
# dismantles (nd_cw_dismantle_as). Call it BEFORE the stockpile is zeroed, with
# WARHEADS = the count given up. Idempotent: a country already renounced and
# unarmed is not counted again — the Budapest path can put a disarmament
# article in force (whose on_entry_into_force calls this) and then zero the
# stockpile itself. Marks a former nuclear state (nd_renounced = the year) for
# the restraint part; a breakout clears it (nd_taboo_country_monthly).
nd_taboo_note_renunciation = {
	if = {
		limit = {
			has_global_variable = nd_taboo
			$WARHEADS$ > 0
			NOT = {
				AND = {
					has_variable = nd_renounced
					nd_is_armed = no
				}
			}
		}
		set_global_variable = {
			name = nd_tb_stage
			value = {
				value = $WARHEADS$
				multiply = nd_taboo_ledger_renounce_per_warhead
				add = nd_taboo_ledger_renounce_base
				max = nd_taboo_ledger_renounce_cap
			}
		}
		nd_taboo_ledger_commit = yes
		set_variable = { name = nd_renounced value = year }
		debug_log = "TE_TABOO: an arsenal was given up"
	}
}

# Puts the programme hold on or takes it off. Decides from has_modifier, so
# call it at most once per effect block: the monthly half calls it last, and
# each panel action once.
nd_taboo_refresh_held = {
	if = {
		limit = { nd_taboo_programme_should_be_held = yes }
		if = {
			limit = { NOT = { has_modifier = nd_taboo_programme_held } }
			add_modifier = { name = nd_taboo_programme_held }
		}
	}
	else_if = {
		limit = { has_modifier = nd_taboo_programme_held }
		remove_modifier = nd_taboo_programme_held
	}
}

# ---- Reduce the Arsenal: the posture panel's ops 60 / 61 / 62 ----

nd_taboo_ceiling_lower = {
	custom_tooltip = {
		text = nd_taboo_tt_ceiling_lower
		set_variable = { name = nd_warhead_ceiling value = nd_taboo_ceiling_lowered_value }
	}
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

nd_taboo_ceiling_raise = {
	custom_tooltip = {
		text = nd_taboo_tt_ceiling_raise
		set_variable = { name = nd_warhead_ceiling value = nd_taboo_ceiling_raised_value }
	}
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

nd_taboo_ceiling_lift = {
	custom_tooltip = {
		text = nd_taboo_tt_ceiling_lift
		remove_variable = nd_warhead_ceiling
	}
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

# Warheads above the ceiling, a tenth of the excess a month, through the
# custody ledger; each strengthens the taboo a little.
nd_taboo_retire_step = {
	set_variable = { name = nd_tb_retire value = nd_taboo_retire_this_month_value }
	change_variable = { name = nuclear_weapon_stockpile subtract = var:nd_tb_retire }
	set_variable = {
		name = nd_tb_retire_points
		value = {
			value = var:nd_tb_retire
			multiply = nd_taboo_ledger_retire_per_warhead
		}
	}
	nd_taboo_ledger_add = { POINTS = var:nd_tb_retire_points }
	nd_ledger_refresh = yes
	remove_variable = nd_tb_retire
	remove_variable = nd_tb_retire_points
}

# ---- Dismantle the Arsenal: op 63, band-event options, and the AI ----
# 12 months + 1 per 10 warheads above 20 (at most 36), evenly; readiness goes
# to Recessed and is held there (nd_weekly_update, nd_can_set_readiness); the
# programme is held. Each action is a core and a wrapper: the panel and the
# event options call the wrapper, which refreshes the hold at once; the AI's
# arsenal review calls the core, because it runs inside the monthly half,
# which refreshes the hold once after it (a second refresh in one block would
# misread the modifier).
nd_taboo_dismantle_begin = {
	custom_tooltip = {
		text = nd_taboo_tt_dismantle_start
		set_variable = { name = nd_dismantle_start_stock value = nd_stockpile }
		set_variable = { name = nd_dismantle_months_left value = nd_taboo_dismantle_months_value }
		set_variable = { name = nd_dismantle_per_month value = nd_taboo_dismantle_per_month_value }
	}
	if = {
		limit = {
			has_variable = nd_readiness_target
			var:nd_readiness_target > 0
		}
		nd_set_readiness_target_0 = yes
	}
	hidden_effect = {
		debug_log = "TE_TABOO: dismantling begun"
	}
}

nd_taboo_dismantle_start = {
	nd_taboo_dismantle_begin = yes
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

# Op 64: what is retired stays gone; a public reversal.
nd_taboo_dismantle_stop = {
	custom_tooltip = {
		text = nd_taboo_tt_halt
		remove_variable = nd_dismantle_months_left
		remove_variable = nd_dismantle_per_month
		change_variable = { name = nd_credibility subtract = nd_taboo_halt_credibility }
		clamp_variable = { name = nd_credibility min = 0 max = 100 }
	}
	hidden_effect = {
		nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_halt }
		debug_log = "TE_TABOO: dismantling halted"
	}
}

nd_taboo_dismantle_halt = {
	nd_taboo_dismantle_stop = yes
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

# One month of dismantling (nd_taboo_country_monthly).
nd_taboo_dismantle_step = {
	set_variable = { name = nd_tb_retire value = var:nd_dismantle_per_month }
	if = {
		limit = { var:nd_tb_retire > nd_stockpile }
		set_variable = { name = nd_tb_retire value = nd_stockpile }
	}
	change_variable = { name = nuclear_weapon_stockpile subtract = var:nd_tb_retire }
	change_variable = { name = nd_dismantle_months_left subtract = 1 }
	nd_ledger_refresh = yes
	remove_variable = nd_tb_retire
	if = {
		limit = {
			OR = {
				var:nd_dismantle_months_left <= 0
				nd_stockpile <= 0
			}
		}
		nd_taboo_dismantle_complete = yes
	}
}

# The last warhead gone. Only nd_taboo_dismantle_step calls it, from the
# monthly half, which refreshes the hold and the possession cost once after it
# — so this must not.
nd_taboo_dismantle_complete = {
	nd_taboo_note_renunciation = { WARHEADS = var:nd_dismantle_start_stock }
	set_variable = { name = nuclear_weapon_stockpile value = 0 }
	set_variable = nd_renounced_locked
	add_modifier = { name = nd_taboo_renounced }
	if = {
		limit = { has_modifier = nuclear_power }
		remove_modifier = nuclear_power
	}
	remove_variable = nd_dismantle_months_left
	remove_variable = nd_dismantle_per_month
	if = {
		limit = { has_variable = nd_warhead_ceiling }
		remove_variable = nd_warhead_ceiling
	}
	nd_snap_public_estimate = yes
	nd_apply_posture_modifiers = yes
	nd_ledger_refresh = yes
	trigger_event = { id = nuclear_taboo.20 }
	debug_log = "TE_TABOO: an arsenal was dismantled"
}

# nuclear_taboo.20's option: what the world gives a country that gave the bomb
# up of its own accord — more the more it has come to fear the weapon.
# nd_taboo_renounce_mult is set by the event's immediate, so the option's
# preview shows the right prestige.
nd_taboo_renunciation_rewards = {
	add_modifier = {
		name = nd_taboo_renunciation_prestige
		years = 20
		is_decaying = yes
		multiplier = root.var:nd_taboo_renounce_mult
	}
	custom_tooltip = {
		text = nd_taboo_tt_renounce_relations
		every_country = {
			limit = { NOT = { this = ROOT } }
			change_relations = { country = ROOT value = nd_taboo_renounce_relations_value }
		}
	}
	every_interest_group = {
		limit = { nd_ig_is_restraint = yes }
		add_modifier = {
			name = ig_approval_positive_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
	every_interest_group = {
		limit = { nd_ig_is_hawk = yes }
		add_modifier = {
			name = ig_approval_negative_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
}

# Resume the Nuclear Programme (the decision). The breakout itself is booked
# when the country is armed again (nd_taboo_country_monthly).
nd_taboo_resume = {
	remove_modifier = nd_taboo_renounced
	if = {
		limit = { has_variable = nd_renounced_locked }
		remove_variable = nd_renounced_locked
	}
	if = {
		limit = { has_modifier = nd_taboo_renunciation_prestige }
		remove_modifier = nd_taboo_renunciation_prestige
	}
	change_infamy = nd_taboo_infamy_threat
	custom_tooltip = {
		text = nd_taboo_tt_resume_relations
		every_country = {
			limit = { NOT = { this = ROOT } }
			change_relations = { country = ROOT value = nd_taboo_resume_relations_value }
		}
	}
}
```

Then replace the whole `nd_taboo_country_monthly` block (from Task 6) with:

```
nd_taboo_country_monthly = {
	if = {
		limit = { has_global_variable = nd_taboo }
		# ---- a former nuclear state armed again, by any route: a breakout ----
		if = {
			limit = {
				has_variable = nd_renounced
				nd_is_armed = yes
			}
			nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_breakout }
			remove_variable = nd_renounced
			debug_log = "TE_TABOO: a former nuclear state is armed again"
		}
		# ---- the renunciation outlives a revolution: the winner keeps our
		# variables but none of our modifiers (scripting_best_practices.md §
		# What a Civil War's Winner Inherits) ----
		if = {
			limit = {
				has_variable = nd_renounced_locked
				NOT = { has_modifier = nd_taboo_renounced }
			}
			add_modifier = { name = nd_taboo_renounced }
		}
		# ---- dismantling, or warheads above the ceiling ----
		if = {
			limit = { nd_taboo_is_dismantling = yes }
			nd_taboo_dismantle_step = yes
		}
		else_if = {
			limit = {
				has_variable = nd_warhead_ceiling
				nd_stockpile > var:nd_warhead_ceiling
			}
			nd_taboo_retire_step = yes
		}
		nd_taboo_refresh_held = yes
		nd_taboo_refresh_possession = yes
	}
}
```

- [ ] **Step 7: Create `events/nuclear_taboo_events.txt`** (BOM first)

```
﻿# ============================================================================
# THE NUCLEAR TABOO — events
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md.
#   .1-.4   the taboo hardens through 30 / 50 / 70 / 90 (nd_taboo_band_check)
#   .5-.8   it erodes through 90 / 70 / 50 / 30
#   .20     the last warhead taken apart (nd_taboo_dismantle_complete)
# The band events' options are country-local: none moves the world's score.
# ============================================================================
namespace = nuclear_taboo

# The last warhead taken apart. Its option pays the renunciation's rewards, so
# the tooltip shows them; the prestige multiplier is set here first.
nuclear_taboo.20 = {
	type = country_event
	placement = root

	event_image = { texture = "gfx/event_pictures/nuclear_treaty_signing.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = nuclear_taboo.20.t
	desc = nuclear_taboo.20.d
	flavor = nuclear_taboo.20.f

	duration = 3

	trigger = {
		has_variable = nd_renounced_locked
	}

	immediate = {
		set_variable = { name = nd_taboo_renounce_mult value = nd_taboo_renounce_mult_value }
	}

	option = {
		name = nuclear_taboo.20.a
		default_option = yes
		nd_taboo_renunciation_rewards = yes
	}
}
```

- [ ] **Step 8: Hold readiness at Recessed while dismantling**

In `nuclear_deterrence_triggers.txt`, replace the end of `nd_can_set_readiness`

```
	custom_tooltip = {
		text = nd_tt_readiness_withdrawn
		OR = {
			nd_readiness_withdrawn = no
			var:nd_readiness_target > $R$
		}
	}
}
```

with

```
	custom_tooltip = {
		text = nd_tt_readiness_withdrawn
		OR = {
			nd_readiness_withdrawn = no
			var:nd_readiness_target > $R$
		}
	}
	# Being dismantled (nuclear_taboo_effects.txt): in storage until the last
	# warhead is gone. Lowering is never blocked.
	custom_tooltip = {
		text = nd_taboo_tt_readiness_dismantling
		OR = {
			nd_taboo_is_dismantling = no
			var:nd_readiness_target > $R$
		}
	}
}
```

In `nd_weekly_update`, replace

```
		set_variable = { name = nd_readiness_target value = 0 }
	}
	# ---- readiness transition: one step every nd_readiness_step_weeks ------
```

with

```
		set_variable = { name = nd_readiness_target value = 0 }
	}
	# ---- being dismantled (nuclear_taboo_effects.txt): in storage until the
	# last warhead is gone; any other path that raised the target is put back.
	if = {
		limit = {
			nd_taboo_is_dismantling = yes
			has_variable = nd_readiness_target
			var:nd_readiness_target > 0
		}
		set_variable = { name = nd_readiness_target value = 0 }
	}
	# ---- readiness transition: one step every nd_readiness_step_weeks ------
```

- [ ] **Step 9: Every other path that gives an arsenal up books the renunciation**

`nuclear_custody_effects.txt`, `nd_cw_dismantle_as`: replace

```
nd_cw_dismantle_as = {
	custom_tooltip = {
		text = $TT$
		set_variable = { name = nuclear_weapon_stockpile value = 0 }
```

with

```
nd_cw_dismantle_as = {
	# The nuclear taboo: an arsenal given up (read before it is zeroed).
	hidden_effect = {
		nd_taboo_note_renunciation = { WARHEADS = nd_stockpile }
	}
	custom_tooltip = {
		text = $TT$
		set_variable = { name = nuclear_weapon_stockpile value = 0 }
```

`nd_bp_accept`: replace

```
		if = {
			limit = { nd_stockpile > 0 }
			set_variable = { name = nuclear_weapon_stockpile value = 0 }
		}
```

with

```
		# The nuclear taboo: an arsenal given up. Idempotent, so the lead's
		# disarmament article, if it went into force above, has already
		# counted it.
		nd_taboo_note_renunciation = { WARHEADS = nd_stockpile }
		if = {
			limit = { nd_stockpile > 0 }
			set_variable = { name = nuclear_weapon_stockpile value = 0 }
		}
```

`extra_treaty_articles.txt`, `nuclear_disarmament`'s `on_entry_into_force`: replace

```
			else_if = {
				limit = { has_variable = te_nuclear_disarmament_ended_program }
				remove_variable = te_nuclear_disarmament_ended_program
			}
			set_variable = { name = nuclear_weapon_stockpile value = 0 }
```

with

```
			else_if = {
				limit = { has_variable = te_nuclear_disarmament_ended_program }
				remove_variable = te_nuclear_disarmament_ended_program
			}
			# The nuclear taboo: an arsenal given up (read before it is zeroed).
			nd_taboo_note_renunciation = { WARHEADS = nd_stockpile }
			set_variable = { name = nuclear_weapon_stockpile value = 0 }
```

- [ ] **Step 10: The programme reports the hold** (`nuclear_weapon_effects.txt`, `nuclear_program_refresh_state_effect`)

Replace

```
	if = {
		limit = { modifier:country_nuclear_program_pause_bool = yes }
		set_variable = { name = nuclear_program_last_status value = 3 }
	}
```

with

```
	# 5 and 4 before 3: the taboo's hold carries the same pause flag.
	if = {
		limit = { nd_taboo_is_dismantling = yes }
		set_variable = { name = nuclear_program_last_status value = 5 }
	}
	else_if = {
		limit = { has_modifier = nd_taboo_programme_held }
		set_variable = { name = nuclear_program_last_status value = 4 }
	}
	else_if = {
		limit = { modifier:country_nuclear_program_pause_bool = yes }
		set_variable = { name = nuclear_program_last_status value = 3 }
	}
```

In `nuclear_program_custom_loc.txt`:
- extend the header's status table with `#   4 held at our arsenal ceiling 5 being dismantled`;
- in `nuclear_program_status_line`, insert these two branches directly before the `var:nuclear_program_last_status = 3` branch:

```
	text = {
		trigger = {
			has_variable = nuclear_program_last_status
			var:nuclear_program_last_status = 5
		}
		localization_key = nuclear_program_status_dismantling
	}
	text = {
		trigger = {
			has_variable = nuclear_program_last_status
			var:nuclear_program_last_status = 4
		}
		localization_key = nuclear_program_status_held
	}
```

- in `nuclear_program_rate_note`, insert as its first branch:

```
	text = {
		trigger = { has_modifier = nd_taboo_programme_held }
		localization_key = nuclear_program_rate_note_held
	}
```

- [ ] **Step 11: The panel's custom loc** (append to the end of `nuclear_program_custom_loc.txt`, in its WIDGET-ONLY section, where targets may use `JournalEntry.GetCountry`. The deterrence file's blocks are accessor-free by its header's rule.)

```

# ---- The arsenal: a ceiling, or dismantling it (the nuclear taboo) -----------

nd_taboo_arsenal_status = {
	type = country
	random_valid = no

	text = {
		trigger = { nd_taboo_is_dismantling = yes }
		localization_key = nd_taboo_arsenal_dismantling
	}
	text = {
		trigger = { has_variable = nd_warhead_ceiling }
		localization_key = nd_taboo_arsenal_ceiling
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_arsenal_free
	}
}

nd_taboo_ceiling_value = {
	type = country
	random_valid = no

	text = {
		trigger = { has_variable = nd_warhead_ceiling }
		localization_key = nd_taboo_ceiling_set
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_ceiling_none
	}
}

# Where the burden would ease a domestic step (nd_disp_taboo_step_down_warheads).
nd_taboo_burden_hint = {
	type = country
	random_valid = no

	text = {
		trigger = { nd_taboo_burden_value < nd_taboo_burden_step_mild }
		localization_key = nuke_line_empty
	}
	text = {
		trigger = { nd_disp_taboo_step_down_warheads >= 1 }
		localization_key = nd_taboo_burden_hint_cut
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_burden_hint_only_dismantling
	}
}
```

- [ ] **Step 12: The panel ops** (`nuclear_deterrence_sguis.txt`)

In `nd_posture_sgui`'s `is_valid`, replace

```
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 51 }
			nd_can_step_investment_up = { VAR = nd_hardening }
		}
```

with

```
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 51 }
			nd_can_step_investment_up = { VAR = nd_hardening }
		}
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 60 }
			nd_taboo_can_lower_ceiling = yes
		}
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 61 }
			nd_taboo_can_raise_ceiling = yes
		}
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 62 }
			nd_taboo_can_raise_ceiling = yes
		}
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 63 }
			nd_taboo_can_dismantle = yes
		}
		trigger_else_if = {
			limit = { exists = scope:op  scope:op = 64 }
			nd_taboo_can_halt = yes
		}
```

In its `effect`, replace

```
			nd_step_investment = { VAR = nd_hardening OP = add }
		}
```

with

```
			nd_step_investment = { VAR = nd_hardening OP = add }
		}
		else_if = {
			limit = { exists = scope:op  scope:op = 60 }
			nd_taboo_ceiling_lower = yes
		}
		else_if = {
			limit = { exists = scope:op  scope:op = 61 }
			nd_taboo_ceiling_raise = yes
		}
		else_if = {
			limit = { exists = scope:op  scope:op = 62 }
			nd_taboo_ceiling_lift = yes
		}
		else_if = {
			limit = { exists = scope:op  scope:op = 63 }
			nd_taboo_dismantle_start = yes
		}
		else_if = {
			limit = { exists = scope:op  scope:op = 64 }
			nd_taboo_dismantle_halt = yes
		}
```

In the file header's `nd_posture_sgui — op table`, add after the `50 / 51` line:

```
#   60 / 61 arsenal ceiling down / up     -> nd_taboo_ceiling_lower / _raise
#   62      lift the ceiling              -> nd_taboo_ceiling_lift
#   63      dismantle the arsenal         -> nd_taboo_dismantle_start
#   64      halt the dismantling          -> nd_taboo_dismantle_halt
```

- [ ] **Step 13: The panel rows** (`gui/journal_entry_widgets/nuclear_deterrence_widget.gui`)

In the header's op table, replace `###                           50/51 hardening -/+` with:

```
###                           50/51 hardening -/+
###                           60/61 arsenal ceiling -/+  62 lift it
###                           63 dismantle the arsenal  64 halt it
```

In the Capabilities panel, the hardening stepper row ends with the `(CFixedPoint)51` plus button. Replace the three closing lines that follow its last `tooltip = …(CFixedPoint)51…` line

```
			}
		}
	}

	### ---- At home (collapsed) --------------------------------------------------
```

with

```
			}
		}

		### ---- The arsenal: a ceiling, or dismantling it (the nuclear taboo,
		### nuclear_taboo_effects.txt) ----------------------------------------
		nd_row = {
			blockoverride "row_label" {
				text = "nd_taboo_w_status_label"
			}
			blockoverride "row_value" {
				text = "nd_taboo_w_status_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_taboo_w_status_tt"
			}
		}
		nd_stepper_row = {
			datacontext = "[GetScriptedGui('nd_posture_sgui')]"
			textbox = {
				text = "nd_taboo_w_ceiling_label"
				size = { 200 24 }
				align = left|nobaseline
				using = fontsize_medium
				parentanchor = vcenter
				elide = right
				alwaystransparent = yes
			}
			button_icon_minus_action = {
				size = { 24 24 }
				parentanchor = vcenter
				enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)60' ) ).End )]"
				onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)60' ) ).End )]"
				tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)60' ) ).End ), Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)60' ) ).End ) ) )]"
			}
			textbox = {
				text = "nd_taboo_w_ceiling_value"
				tooltip = "nd_taboo_w_ceiling_tt"
				size = { 216 24 }
				align = center|nobaseline
				using = fontsize_medium
				parentanchor = vcenter
				elide = right
			}
			button_icon_plus_action = {
				size = { 24 24 }
				parentanchor = vcenter
				enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)61' ) ).End )]"
				onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)61' ) ).End )]"
				tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)61' ) ).End ), Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)61' ) ).End ) ) )]"
			}
		}
		nd_choice_row = {
			datacontext = "[GetScriptedGui('nd_posture_sgui')]"
			textbox = {
				size = { 360 30 }
				align = left|nobaseline
				using = fontsize_medium
				parentanchor = vcenter
				elide = right
				text = "nd_taboo_w_lift_label"
				tooltip = "nd_taboo_w_lift_tt"
			}
			button = {
				using = default_button_action
				size = { 110 30 }
				parentanchor = vcenter
				text = "nd_taboo_w_btn_lift"
				enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)62' ) ).End )]"
				onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)62' ) ).End )]"
				tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)62' ) ).End ), Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)62' ) ).End ) ) )]"
			}
		}
		nd_choice_row = {
			datacontext = "[GetScriptedGui('nd_posture_sgui')]"
			textbox = {
				size = { 360 30 }
				align = left|nobaseline
				using = fontsize_medium
				parentanchor = vcenter
				elide = right
				text = "nd_taboo_w_dismantle_label"
				tooltip = "nd_taboo_w_dismantle_tt"
			}
			button = {
				using = default_button_action
				size = { 110 30 }
				parentanchor = vcenter
				text = "nd_taboo_w_btn_dismantle"
				enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)63' ) ).End )]"
				onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)63' ) ).End )]"
				tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)63' ) ).End ), Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)63' ) ).End ) ) )]"
			}
		}
		nd_choice_row = {
			datacontext = "[GetScriptedGui('nd_posture_sgui')]"
			textbox = {
				size = { 360 30 }
				align = left|nobaseline
				using = fontsize_medium
				parentanchor = vcenter
				elide = right
				text = "nd_taboo_w_halt_label"
				tooltip = "nd_taboo_w_halt_tt"
			}
			button = {
				using = default_button_action
				size = { 110 30 }
				parentanchor = vcenter
				text = "nd_taboo_w_btn_halt"
				enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)64' ) ).End )]"
				onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)64' ) ).End )]"
				tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)64' ) ).End ), Concatenate( Localize( 'te_tt_break' ), ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)64' ) ).End ) ) )]"
			}
		}
	}

	### ---- At home (collapsed) --------------------------------------------------
```

- [ ] **Step 14: The op table in `docs/systems/journal_entry_systems.md`** (CRLF)

Run exactly:

```bash
python3 - <<'EOF'
p = "docs/systems/journal_entry_systems.md"
b = open(p, "rb").read()
old = b"| | 50 / 51 | hardening down / up |\r\n"
new = old + (b"| | 60 / 61 | arsenal ceiling down / up (the nuclear taboo) |\r\n"
             b"| | 62 | lift the arsenal ceiling |\r\n"
             b"| | 63 | dismantle the arsenal |\r\n"
             b"| | 64 | halt the dismantling |\r\n")
assert b.count(old) == 1
open(p, "wb").write(b.replace(old, new))
EOF
test "$(grep -c $'\r$' docs/systems/journal_entry_systems.md)" = "$(wc -l < docs/systems/journal_entry_systems.md)" && echo CRLF-OK
```

Expected: `CRLF-OK`.

- [ ] **Step 15: The decision** (append to `common/decisions/extra_decisions.txt`)

```

# ============================================================================
# Resume the Nuclear Programme (the nuclear taboo, nuclear_taboo_effects.txt)
# A country that dismantled its arsenal (nd_taboo_renounced) may take the bomb
# up again. The breakout — a ledger entry against the taboo — is booked when
# it is armed again, whatever the route (nd_taboo_country_monthly).
# ============================================================================
nd_taboo_resume_programme = {
	is_shown = {
		has_modifier = nd_taboo_renounced
	}

	possible = {
		has_game_rule = nuclear_weapons_enabled
	}

	when_taken = {
		nd_taboo_resume = yes
	}

	ai_chance = {
		value = 0
		if = {
			limit = { nd_taboo_ai_would_resume = yes }
			add = 100
		}
	}
}
```

- [ ] **Step 16: Loc**

`te_events_l_english.yml`:

```
 nuclear_taboo.20.t:0 "The Last Warhead"
 nuclear_taboo.20.d:0 "The last of our warheads has been taken apart, under the eyes of foreign inspectors and our own cameras. #v [ROOT.GetCountry.MakeScope.Var('nd_dismantle_start_stock').GetValue|0]#! weapons — years of work and a fortune — are gone by our own decision. Few states have ever given up the bomb of their own accord, and the world's regard for it will follow how much the world has come to fear the weapon: the nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.20.f:0 "\"We built it because we feared our neighbours. We have taken it apart because we came to fear it more.\""
 nuclear_taboo.20.a:0 "A burden we are glad to set down"
```

`te_miscellaneous_l_english.yml`:

```
 nd_taboo_arsenal_ceiling:0 "Held to #v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_warhead_ceiling')|0]#! warheads"
 nd_taboo_arsenal_dismantling:0 "#R Being dismantled#!: #v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_dismantle_months_left')|0]#! months, #v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_dismantle_per_month')|0]#! a month"
 nd_taboo_arsenal_free:0 "No ceiling"
 nd_taboo_burden_hint_cut:0 "\n\nOur restraint groups would ease at #v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_taboo_step_down_warheads')|0]#! warheads or fewer."
 nd_taboo_burden_hint_only_dismantling:0 "\n\nOnly giving up the arsenal would ease our restraint groups now."
 nd_taboo_ceiling_none:0 "#v None#!"
 nd_taboo_ceiling_set:0 "#v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_warhead_ceiling')|0]#! warheads"
 nd_taboo_programme_held:0 "Programme Held"
 nd_taboo_programme_held_desc:0 "We are at the arsenal ceiling we set, or taking our arsenal apart: the programme builds nothing and cannot be funded."
 nd_taboo_renounced:0 "Renounced the Bomb"
 nd_taboo_renounced_desc:0 "We took our own nuclear arsenal apart. We have no programme and are counted as a non-nuclear state; taking the bomb up again is a decision, and the world would see it as a breakout."
 nd_taboo_renunciation_prestige:0 "The Bomb Renounced"
 nd_taboo_renunciation_prestige_desc:0 "The world honours a state that gave up the bomb of its own accord — the more, the more it has come to fear the weapon."
 nd_taboo_resume_programme:0 "Resume the Nuclear Programme"
 nd_taboo_resume_programme_desc:0 "We gave up the bomb. We can take it up again — at a price in the world's regard that grows with the nuclear taboo, and the day we are armed again the world will call it a breakout."
 nd_taboo_tt_already_dismantling:0 "We are already taking our arsenal apart"
 nd_taboo_tt_ceiling_at_floor:0 "The ceiling cannot go below one warhead; to go further, dismantle the arsenal"
 nd_taboo_tt_ceiling_lift:0 "Lift our arsenal ceiling: the programme may build again"
 nd_taboo_tt_ceiling_lower:0 "Hold our arsenal to #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_ceiling_lowered_value')|0]#! warheads; those above it are taken apart, a tenth of the excess a month, and each strengthens the nuclear taboo a little"
 nd_taboo_tt_ceiling_raise:0 "Allow up to #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_ceiling_raised_value')|0]#! warheads"
 nd_taboo_tt_dismantle_start:0 "Take our #v [GetPlayer.MakeScope.ScriptValue('nd_stockpile')|0]#! warheads apart over #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_dismantle_months_value')|0]#! months. Until the last is gone they stay in storage, the programme builds nothing, and we can halt at a price. When it is done we renounce the bomb: the world's regard grows with the nuclear taboo, and taking it up again would be a breakout"
 nd_taboo_tt_dismantling_owns_it:0 "While we dismantle the arsenal, the dismantling sets its size"
 nd_taboo_tt_halt:0 "Halt the dismantling: what is taken apart stays gone. Our credibility falls by #R 10#!, and the nuclear taboo weakens"
 nd_taboo_tt_need_no_civil_war:0 "Not while we are fighting a civil war"
 nd_taboo_tt_need_no_crisis:0 "Not while we are in a nuclear crisis"
 nd_taboo_tt_need_peace:0 "Not while we are at war"
 nd_taboo_tt_no_ceiling:0 "We have set no arsenal ceiling"
 nd_taboo_tt_not_dismantling:0 "We are not dismantling our arsenal"
 nd_taboo_tt_readiness_dismantling:0 "Our warheads stay in storage until the last is taken apart"
 nd_taboo_tt_renounce_relations:0 "Relations improve by #G [GetPlayer.MakeScope.ScriptValue('nd_taboo_renounce_relations_value')|0]#! with every country"
 nd_taboo_tt_resume_relations:0 "Relations worsen by #R [GetPlayer.MakeScope.ScriptValue('nd_taboo_resume_relations_value')|0]#! with every country"
 nd_taboo_w_btn_dismantle:0 "Begin"
 nd_taboo_w_btn_halt:0 "Halt"
 nd_taboo_w_btn_lift:0 "Lift"
 nd_taboo_w_ceiling_label:0 "Arsenal ceiling"
 nd_taboo_w_ceiling_tt:0 "#tooltip_header Arsenal Ceiling#!\n$TOOLTIP_DELIMITER$\nThe most warheads we will hold. Those above it are taken apart, a tenth of the excess a month, and the programme builds nothing while we are at or above it. Every warhead retired strengthens the nuclear taboo a little. Raising or lifting the ceiling costs nothing.[JournalEntry.GetCountry.GetCustom('nd_taboo_burden_hint')]"
 nd_taboo_w_ceiling_value:0 "[JournalEntry.GetCountry.GetCustom('nd_taboo_ceiling_value')]"
 nd_taboo_w_dismantle_label:0 "Dismantle the arsenal"
 nd_taboo_w_dismantle_tt:0 "#tooltip_header Dismantle the Arsenal#!\n$TOOLTIP_DELIMITER$\nTake every warhead apart and renounce the bomb, as South Africa did in 1989. It takes a year, and longer for a large arsenal. The world's regard for it grows with the nuclear taboo."
 nd_taboo_w_halt_label:0 "Halt the dismantling"
 nd_taboo_w_halt_tt:0 "#tooltip_header Halt the Dismantling#!\n$TOOLTIP_DELIMITER$\nStop taking the arsenal apart. What is gone stays gone, and a reversal made in public costs credibility."
 nd_taboo_w_lift_label:0 "Lift the arsenal ceiling"
 nd_taboo_w_lift_tt:0 "#tooltip_header Lift the Ceiling#!\n$TOOLTIP_DELIMITER$\nNo limit on our arsenal but what the programme can build."
 nd_taboo_w_status_label:0 "Arsenal"
 nd_taboo_w_status_tt:0 "#tooltip_header Arsenal#!\n$TOOLTIP_DELIMITER$\nWhether we hold our arsenal to a ceiling, or are taking it apart. A smaller arsenal is cheaper to hold in a world that fears the bomb.[JournalEntry.GetCountry.GetCustom('nd_taboo_burden_hint')]"
 nd_taboo_w_status_value:0 "[JournalEntry.GetCountry.GetCustom('nd_taboo_arsenal_status')]"
 nuclear_program_rate_note_held:0 "\n#v Development is held while we are at our arsenal ceiling, or taking the arsenal apart.#!"
 nuclear_program_status_dismantling:0 "#R Our arsenal is being dismantled#! — the programme builds nothing."
 nuclear_program_status_held:0 "#v Development is held#! at the arsenal ceiling we set."
```

`nd_tt_need_arsenal` already exists (the posture panel uses it).

- [ ] **Step 17: Format, test, audit, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/static_modifiers/nuclear_taboo_modifiers.txt events/nuclear_taboo_events.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_custody_effects.txt common/treaty_articles/extra_treaty_articles.txt common/scripted_effects/nuclear_weapon_effects.txt common/customizable_localization/nuclear_program_custom_loc.txt common/scripted_guis/nuclear_deterrence_sguis.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui common/decisions/extra_decisions.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 scripts/analysis/check_localization_files.py
for a in orphaned_event_audit event_image_audit event_context_audit silent_variable_audit empty_effect_audit modifier_multiplier_var_audit iterator_limit_audit prev_scope_audit loc_render_audit; do python3 $a.py --strict || echo "FAILED: $a"; done
```

Expected: tests pass and no `FAILED:` line. **If `event_context_audit` flags `nuclear_taboo.20` for `unchosen_self_action`**, add inside the event body (not on its opening line): `# REVIEWED 2026-09-26 (unchosen_self_action): the country chose Dismantle the Arsenal months before; this reports its completion`, then re-run. Don't add the tag unless the flag appears: a tag with no flag fails `--strict`.

```bash
git add test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/static_modifiers/nuclear_taboo_modifiers.txt events/nuclear_taboo_events.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt common/scripted_effects/nuclear_custody_effects.txt common/treaty_articles/extra_treaty_articles.txt common/scripted_effects/nuclear_weapon_effects.txt common/customizable_localization/nuclear_program_custom_loc.txt common/scripted_guis/nuclear_deterrence_sguis.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui common/decisions/extra_decisions.txt docs/systems/journal_entry_systems.md localization/english/te_miscellaneous_l_english.yml localization/english/te_events_l_english.yml
git commit -m "Nuclear taboo: dismantle the arsenal, hold it to a ceiling, or take the bomb up again

<attribution lines>"
```

---

### Task 8: The AI

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING + AI)
- Modify: `common/scripted_triggers/nuclear_taboo_triggers.txt`
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_ai_review_arsenal`; `nd_taboo_country_monthly`)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_ai_nuclear_use_justified`, `nd_ai_would_issue_ultimatum`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_ai_review_posture`)
- Modify: `common/diplomatic_actions/nuke.txt` (both `evaluation_chance`s)
- Modify: `common/script_values/extra_script_values.txt` (`nuclear_ai_desired_stockpile`)
- Modify: `common/scripted_buttons/nuclear_program_buttons.txt` (`increase_funding_nuclear_program`'s `ai_chance`)
- Modify: `common/treaty_articles/extra_treaty_articles.txt` (`nuclear_disarmament`'s `inherent_accept_score`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestAI`)

**Interfaces:**
- Consumes: `nd_taboo_value`, `nd_taboo_burden_value`, `nd_taboo_can_dismantle`, `nd_taboo_dismantle_begin` / `_stop` (cores), `nd_taboo_is_dismantling`.
- Produces:
  - values `nd_taboo_ai_use_factor`, `nd_taboo_ai_arsenal_factor`, `nd_taboo_ai_nfu_weight`, `nd_taboo_ai_reduce_line_value` (country), `nd_taboo_ai_accept_burden_value`, `nd_taboo_ai_accept_taboo_value`;
  - triggers `nd_taboo_ai_restrains_programme`, `nd_taboo_ai_would_dismantle`, `nd_taboo_ai_would_halt`;
  - effect `nd_taboo_ai_review_arsenal`;
  - flag `nd_taboo_ai_arsenal_due`.

- [ ] **Step 1: Write the failing tests** (append to `test_nuclear_taboo.py`)

```python
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
PROGRAM_BUTTONS = ROOT / "common/scripted_buttons/nuclear_program_buttons.txt"


class TestAI(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.dtrig = strip_comments(read(DETERRENCE_TRIGGERS))
        self.det = strip_comments(read(DETERRENCE_EFFECTS))

    def test_factor_endpoints_match_the_spec(self):
        c = lambda n: constant(self.values, n)  # noqa: E731
        self.assertEqual(1 + c("nd_taboo_ai_use_boost"), 2)
        self.assertAlmostEqual(1 - c("nd_taboo_ai_use_cut"), 0.3)
        self.assertEqual(c("nd_taboo_ai_use_pivot") + c("nd_taboo_ai_use_span_high"), 100)
        self.assertAlmostEqual(1 + c("nd_taboo_ai_arsenal_boost"), 1.3)
        self.assertAlmostEqual(1 - c("nd_taboo_ai_arsenal_cut"), 0.5)
        self.assertEqual(c("nd_taboo_ai_arsenal_pivot") + c("nd_taboo_ai_arsenal_span_high"), 100)

    def test_use_is_gated_by_the_taboo(self):
        body = block(self.dtrig, "nd_ai_nuclear_use_justified")
        self.assertRegex(body, r"OR = \{\s*nd_taboo_value < nd_taboo_ai_survival_only_line\s*"
                               r"nd_enemy_threatens_existence = \{ ENEMY = \$ENEMY\$ \}\s*\}")
        self.assertRegex(body, r"ruler_is_cautious = no\s*nd_enemy_threatens_existence = \{ ENEMY = \$ENEMY\$ \}"
                               r"\s*nd_taboo_value < nd_taboo_ai_loosen_line")
        text = strip_comments(read(NUKE_ACTIONS))
        self.assertEqual(text.count("multiply = nd_taboo_ai_use_factor"), 2)

    def test_coercion_is_gated_by_the_taboo(self):
        body = block(self.dtrig, "nd_ai_would_issue_ultimatum")
        self.assertIn("nd_taboo_value < nd_taboo_ai_coercion_line", body)
        self.assertIn("nd_dispute_guarantee_against = { TARGET = $TARGET$ }", body)

    def test_doctrine_weights_read_the_taboo(self):
        body = block(self.det, "nd_ai_review_posture")
        self.assertIn("add = nd_taboo_ai_nfu_weight", body)
        self.assertIn("add = nd_taboo_ai_flexible_penalty", body)
        self.assertEqual(body.count("add = nd_taboo_ai_offensive_bonus"), 2)
        self.assertEqual(body.count("multiply = nd_taboo_ai_offensive_damping"), 2)

    def test_arsenal_and_programme_read_the_taboo(self):
        self.assertIn("multiply = nd_taboo_ai_arsenal_factor",
                      block(strip_comments(read(EXTRA_VALUES)), "nuclear_ai_desired_stockpile"))
        self.assertIn("nd_taboo_ai_restrains_programme = yes",
                      block(strip_comments(read(PROGRAM_BUTTONS)), "increase_funding_nuclear_program"))
        accept = block(block(strip_comments(read(TREATY_ARTICLES)), "nuclear_disarmament"), "inherent_accept_score")
        self.assertIn("value = nd_taboo_ai_accept_burden_value", accept)
        self.assertIn("value = nd_taboo_ai_accept_taboo_value", accept)

    def test_arsenal_review_runs_before_the_one_refresh(self):
        self.assertIn("set_variable = nd_taboo_ai_arsenal_due", block(self.det, "nd_ai_review_posture"))
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertLess(monthly.index("nd_taboo_ai_review_arsenal = yes"), monthly.index("nd_taboo_refresh_held = yes"))
        review = block(self.taboo, "nd_taboo_ai_review_arsenal")
        self.assertNotIn("nd_taboo_refresh_held", review)
        self.assertIn("nd_taboo_dismantle_begin = yes", review)
        self.assertIn("nd_taboo_dismantle_stop = yes", review)
        self.assertIn("chance = 20", review)

    def test_ai_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_ai_accept_burden", "nd_taboo_ai_accept_taboo"):
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestAI -v`
Expected: the constant lookups fail (`AttributeError: 'NoneType' object has no attribute 'group'`), and the needles are missing.

- [ ] **Step 3: Constants and values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_ai_survival_only_line = 70
nd_taboo_ai_loosen_line = 30
nd_taboo_ai_use_pivot = 35
nd_taboo_ai_use_boost = 1
nd_taboo_ai_use_span_high = 65
nd_taboo_ai_use_cut = 0.7
nd_taboo_ai_coercion_line = 70
nd_taboo_ai_nfu_weight_per_point = 0.3
nd_taboo_ai_flexible_penalty = -5
nd_taboo_ai_offensive_bonus = 10
nd_taboo_ai_offensive_damping = 0.25
nd_taboo_ai_arsenal_pivot = 40
nd_taboo_ai_arsenal_boost = 0.3
nd_taboo_ai_arsenal_span_high = 60
nd_taboo_ai_arsenal_cut = 0.5
nd_taboo_ai_programme_restraint_line = 70
nd_taboo_ai_programme_restraint_factor = 0.25
nd_taboo_ai_reduce_margin = 1.5
nd_taboo_ai_dismantle_burden = 0.3
nd_taboo_ai_dismantle_line = 70
nd_taboo_ai_accept_burden_weight = 60
nd_taboo_ai_accept_taboo_weight = 0.6
```

Append a section:

```
# ---- THE AI (spec §8) ------------------------------------------------------------
# "If you've created a world in which using nukes is normal, you should not be
# surprised when the AI uses them against you."

# How readily the AI considers a strike (the actions' evaluation_chance): x2 at
# taboo 0, x1 at 35, x0.3 at 100, linear between.
nd_taboo_ai_use_factor = {
	value = 1
	if = {
		limit = { nd_taboo_value < nd_taboo_ai_use_pivot }
		value = nd_taboo_ai_use_pivot
		subtract = nd_taboo_value
		divide = nd_taboo_ai_use_pivot
		multiply = nd_taboo_ai_use_boost
		add = 1
	}
	else = {
		value = nd_taboo_value
		subtract = nd_taboo_ai_use_pivot
		divide = nd_taboo_ai_use_span_high
		multiply = nd_taboo_ai_use_cut
		multiply = -1
		add = 1
	}
}

# The AI's wanted arsenal (nuclear_ai_desired_stockpile) x1.3 at taboo 0, x1 at
# 40, x0.5 at 100.
nd_taboo_ai_arsenal_factor = {
	value = 1
	if = {
		limit = { nd_taboo_value < nd_taboo_ai_arsenal_pivot }
		value = nd_taboo_ai_arsenal_pivot
		subtract = nd_taboo_value
		divide = nd_taboo_ai_arsenal_pivot
		multiply = nd_taboo_ai_arsenal_boost
		add = 1
	}
	else = {
		value = nd_taboo_value
		subtract = nd_taboo_ai_arsenal_pivot
		divide = nd_taboo_ai_arsenal_span_high
		multiply = nd_taboo_ai_arsenal_cut
		multiply = -1
		add = 1
	}
}

# No First Use's extra weight in the AI's doctrine review: up to +15 above 50.
nd_taboo_ai_nfu_weight = {
	value = nd_taboo_value
	subtract = nd_taboo_line_established
	multiply = nd_taboo_ai_nfu_weight_per_point
	min = 0
}

# Above this the AI trims its arsenal back to what it wants. Scope: country
nd_taboo_ai_reduce_line_value = {
	value = nuclear_ai_desired_stockpile
	multiply = nd_taboo_ai_reduce_margin
}

# The disarmament article's acceptance terms for the country asked to give
# its arsenal up. Scope: country
nd_taboo_ai_accept_burden_value = {
	value = nd_taboo_burden_value
	multiply = nd_taboo_ai_accept_burden_weight
	round = yes
}

nd_taboo_ai_accept_taboo_value = {
	value = nd_taboo_value
	subtract = nd_taboo_line_established
	multiply = nd_taboo_ai_accept_taboo_weight
	min = 0
	round = yes
}
```

- [ ] **Step 4: Triggers** (append to `nuclear_taboo_triggers.txt`)

```

# ---- THE AI (spec §8) — country scope ------------------------------------------

# A norm-bound world does not start or grow a programme lightly: at 70 or
# more, for a country nobody threatens and not at war.
nd_taboo_ai_restrains_programme = {
	nd_taboo_value >= nd_taboo_ai_programme_restraint_line
	is_at_war = no
	nd_has_plausible_attacker = no
}

# When the AI gives the bomb up (then 20 % a review, nd_taboo_ai_review_arsenal).
nd_taboo_ai_would_dismantle = {
	OR = {
		nd_taboo_burden_value >= nd_taboo_ai_dismantle_burden
		nd_taboo_value >= nd_taboo_ai_dismantle_line
	}
	nd_taboo_can_dismantle = yes
	nd_has_plausible_attacker = no
	OR = {
		nd_is_guaranteed = yes
		country_rank < rank_value:great_power
	}
	nd_regime_is_militarist = no
	ruler_is_aggressive = no
}

# Only an armed enemy that threatens our existence stops a dismantling.
nd_taboo_ai_would_halt = {
	save_temporary_scope_as = nd_tb_self
	any_country = {
		has_war_with = scope:nd_tb_self
		nd_believed_armed = yes
		save_temporary_scope_as = nd_tb_enemy
		scope:nd_tb_self = {
			nd_enemy_threatens_existence = { ENEMY = scope:nd_tb_enemy }
		}
	}
}
```

- [ ] **Step 5: The arsenal review** (`nuclear_taboo_effects.txt`, append in the EXITS section)

```
# The AI's arsenal (spec §5.4), flagged every sixth month by
# nd_ai_review_posture and run from nd_taboo_country_monthly before its one
# refresh of the hold, so it calls the cores and never refreshes itself.
nd_taboo_ai_review_arsenal = {
	if = {
		limit = { nd_taboo_is_dismantling = yes }
		if = {
			limit = { nd_taboo_ai_would_halt = yes }
			nd_taboo_dismantle_stop = yes
		}
	}
	else_if = {
		limit = { nd_taboo_ai_would_dismantle = yes }
		random = {
			chance = 20
			nd_taboo_dismantle_begin = yes
		}
	}
	else_if = {
		limit = {
			nd_taboo_burden_value > 0
			nd_stockpile > nd_taboo_ai_reduce_line_value
		}
		set_variable = { name = nd_warhead_ceiling value = nuclear_ai_desired_stockpile }
	}
	else_if = {
		limit = {
			has_variable = nd_warhead_ceiling
			var:nd_warhead_ceiling < nuclear_ai_desired_stockpile
		}
		remove_variable = nd_warhead_ceiling
	}
}
```

In `nd_taboo_country_monthly`, replace

```
		# ---- dismantling, or warheads above the ceiling ----
```

with

```
		# ---- the AI's arsenal review, flagged by its six-monthly posture
		# review (nd_ai_review_posture) and run here, before the one refresh
		# of the hold below ----
		if = {
			limit = { has_variable = nd_taboo_ai_arsenal_due }
			remove_variable = nd_taboo_ai_arsenal_due
			if = {
				limit = { is_ai = yes }
				nd_taboo_ai_review_arsenal = yes
			}
		}
		# ---- dismantling, or warheads above the ceiling ----
```

- [ ] **Step 6: Flag it from the posture review** (`nuclear_deterrence_effects.txt`, the end of `nd_ai_review_posture`)

Replace

```
	set_variable = { name = nd_hardening value = var:nd_ai_want_hardening }
	nd_apply_posture_modifiers = yes
}
```

with

```
	set_variable = { name = nd_hardening value = var:nd_ai_want_hardening }
	nd_apply_posture_modifiers = yes
	# ---- arsenal size and disarmament (the nuclear taboo) -------------------
	# Decided by nd_taboo_ai_review_arsenal from the entry's monthly taboo
	# half, later in this same pulse, which refreshes the programme hold once
	# after it.
	set_variable = nd_taboo_ai_arsenal_due
}
```

- [ ] **Step 7: Use, coercion and doctrine**

In `nuclear_deterrence_triggers.txt` `nd_ai_nuclear_use_justified`, replace

```
			NOT = { has_variable = nd_first_use_cooldown }
			OR = {
				# National survival.
```

with

```
			NOT = { has_variable = nd_first_use_cooldown }
			# The nuclear taboo (nuclear_taboo_values.txt): at 70 or more,
			# first use only for national survival, whatever the doctrine.
			OR = {
				nd_taboo_value < nd_taboo_ai_survival_only_line
				nd_enemy_threatens_existence = { ENEMY = $ENEMY$ }
			}
			OR = {
				# National survival.
```

and replace

```
			# A cautious ruler only for survival.
			OR = {
				ruler_is_cautious = no
				nd_enemy_threatens_existence = { ENEMY = $ENEMY$ }
			}
```

with

```
			# A cautious ruler only for survival — unless the world treats
			# the bomb as an ordinary weapon (the nuclear taboo below 30).
			OR = {
				ruler_is_cautious = no
				nd_enemy_threatens_existence = { ENEMY = $ENEMY$ }
				nd_taboo_value < nd_taboo_ai_loosen_line
			}
```

In `nd_ai_would_issue_ultimatum`, replace its last two lines

```
	has_variable = nd_credibility
	var:nd_credibility >= 40
}
```

with

```
	has_variable = nd_credibility
	var:nd_credibility >= 40
	# The nuclear taboo: at 70 or more, no coercive ultimatum; one in defence
	# of a guaranteed country, our survival or our core still goes out.
	OR = {
		nd_taboo_value < nd_taboo_ai_coercion_line
		nd_dispute_guarantee_against = { TARGET = $TARGET$ }
		nd_enemy_threatens_existence = { ENEMY = $TARGET$ }
		nd_core_threatened_by = { ENEMY = $TARGET$ }
	}
}
```

In `common/diplomatic_actions/nuke.txt`, in the **strategic** action's `evaluation_chance`, replace

```
				multiply = 0.25 # very reluctant but not impossible in existential situations
			}
			max = 1
```

with

```
				multiply = 0.25 # very reluctant but not impossible in existential situations
			}
			# The nuclear taboo: x2 in a world that treats the bomb as ordinary,
			# x0.3 where it is unthinkable (nuclear_taboo_values.txt).
			multiply = nd_taboo_ai_use_factor
			max = 1
```

and in the **tactical** action's, replace

```
				multiply = 0.25 # reluctant but not impossible
			}
			max = 1
```

with

```
				multiply = 0.25 # reluctant but not impossible
			}
			# The nuclear taboo (nuclear_taboo_values.txt).
			multiply = nd_taboo_ai_use_factor
			max = 1
```

In `nd_ai_review_posture`'s doctrine `random_list` (`nuclear_deterrence_effects.txt`):

- No First Use: replace

```
					if = {
						limit = { country_is_democratic = yes }
						add = 10
					}
```

with

```
					if = {
						limit = { country_is_democratic = yes }
						add = 10
					}
					# The nuclear taboo: up to +15 above 50.
					add = nd_taboo_ai_nfu_weight
```

- Flexible first use: replace

```
					if = {
						limit = { ruler_is_cautious = yes }
						add = -10
					}
```

with

```
					if = {
						limit = { ruler_is_cautious = yes }
						add = -10
					}
					if = {
						limit = { nd_taboo_value >= nd_taboo_ai_survival_only_line }
						add = nd_taboo_ai_flexible_penalty
					}
```

- Compellence: replace

```
					if = {
						limit = { ruler_is_aggressive = yes }
						add = 10
					}
					if = {
						limit = { ruler_is_cautious = yes }
						multiply = 0
					}
```

with

```
					if = {
						limit = { ruler_is_aggressive = yes }
						add = 10
					}
					# The nuclear taboo: tempting where the bomb is ordinary,
					# damped where it is unthinkable.
					if = {
						limit = { nd_taboo_value < nd_taboo_ai_loosen_line }
						add = nd_taboo_ai_offensive_bonus
					}
					if = {
						limit = { nd_taboo_value >= nd_taboo_ai_survival_only_line }
						multiply = nd_taboo_ai_offensive_damping
					}
					if = {
						limit = { ruler_is_cautious = yes }
						multiply = 0
					}
```

- Warfighting: replace

```
						if = {
							limit = { country_is_fascist = yes }
							add = 10
						}
					}
					if = {
						limit = { ruler_is_cautious = yes }
						multiply = 0
					}
```

with

```
						if = {
							limit = { country_is_fascist = yes }
							add = 10
						}
					}
					if = {
						limit = { nd_taboo_value < nd_taboo_ai_loosen_line }
						add = nd_taboo_ai_offensive_bonus
					}
					if = {
						limit = { nd_taboo_value >= nd_taboo_ai_survival_only_line }
						multiply = nd_taboo_ai_offensive_damping
					}
					if = {
						limit = { ruler_is_cautious = yes }
						multiply = 0
					}
```

- [ ] **Step 8: Arsenal size, proliferation, the disarmament article**

`extra_script_values.txt`, in `nuclear_ai_desired_stockpile`, insert directly above its `min = 1` line:

```
	# The nuclear taboo: bigger arsenals where the bomb is ordinary, smaller
	# where it is unthinkable (nuclear_taboo_values.txt).
	multiply = nd_taboo_ai_arsenal_factor

```

`nuclear_program_buttons.txt`, in `increase_funding_nuclear_program`'s `ai_chance`, replace

```
		if = {
			limit = { var:nuclear_weapon_stockpile >= nuclear_ai_desired_stockpile }
			add = -45
		}
	}
```

with

```
		if = {
			limit = { var:nuclear_weapon_stockpile >= nuclear_ai_desired_stockpile }
			add = -45
		}
		# The nuclear taboo: a norm-bound world does not start or grow a
		# programme lightly (nuclear_taboo_triggers.txt).
		if = {
			limit = { nd_taboo_ai_restrains_programme = yes }
			multiply = nd_taboo_ai_programme_restraint_factor
		}
	}
```

`extra_treaty_articles.txt`, `nuclear_disarmament`'s `inherent_accept_score`, SOURCE side: replace

```
					add = {
						desc = "AI_GOOD_RELATIONS_WITH_GP"
						value = 25
					}
				}
```

with

```
					add = {
						desc = "AI_GOOD_RELATIONS_WITH_GP"
						value = 25
					}
				}
				# The nuclear taboo: a world that holds the bomb in horror makes
				# giving it up easier, the more so the more it costs us to keep.
				if = {
					limit = { nd_taboo_burden_value > 0 }
					add = {
						desc = "nd_taboo_ai_accept_burden"
						value = nd_taboo_ai_accept_burden_value
					}
				}
				if = {
					limit = { nd_taboo_value > nd_taboo_line_established }
					add = {
						desc = "nd_taboo_ai_accept_taboo"
						value = nd_taboo_ai_accept_taboo_value
					}
				}
```

- [ ] **Step 9: Loc** (`te_miscellaneous_l_english.yml`)

```
 nd_taboo_ai_accept_burden:0 "The burden of our arsenal"
 nd_taboo_ai_accept_taboo:0 "The world's horror of the bomb"
```

- [ ] **Step 10: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt common/diplomatic_actions/nuke.txt common/script_values/extra_script_values.txt common/scripted_buttons/nuclear_program_buttons.txt common/treaty_articles/extra_treaty_articles.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 attitude_key_audit.py && python3 iterator_limit_audit.py --strict
git add test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt common/diplomatic_actions/nuke.txt common/script_values/extra_script_values.txt common/scripted_buttons/nuclear_program_buttons.txt common/treaty_articles/extra_treaty_articles.txt localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: the AI uses, threatens, builds and disarms by it

<attribution lines>"
```

---

### Task 9: The taboo panel, its breakdown and its chart

**Files:**
- Modify: `gui/journal_entry_widgets/nuclear_program_widget.gui` (`widget_je_nuclear_balance`)
- Modify: `common/scripted_guis/nuclear_program_sguis.txt`
- Modify: `common/customizable_localization/nuclear_program_custom_loc.txt` (`nd_taboo_heading`, `nd_taboo_last_use`)
- Modify: `common/script_values/nuclear_taboo_values.txt` (`nd_taboo_gap_value`)
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_record_history`; `nd_taboo_country_monthly`)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestPanel`)

**Interfaces:**
- Consumes: the snapshots and `nd_disp_*` (Task 1), the costs (Task 4), the burden (Task 6), `nd_taboo_band_name` (Task 5), `nd_armed_sgui` (existing).
- Produces:
  - display sguis `nd_taboo_exists_sgui` and `nd_taboo_breakdown_sgui`;
  - history metrics `te_hist_v_nd_taboo` and `te_hist_v_nd_taboo_tgt`.

- [ ] **Step 1: Write the failing tests** (append)

```python
PROGRAM_SGUIS = ROOT / "common/scripted_guis/nuclear_program_sguis.txt"
PROGRAM_GUI = ROOT / "gui/journal_entry_widgets/nuclear_program_widget.gui"


class TestPanel(unittest.TestCase):
    def setUp(self):
        self.sguis = strip_comments(read(PROGRAM_SGUIS))
        self.gui = read(PROGRAM_GUI)

    def test_handlers_are_display_only_and_drawn(self):
        for name in ("nd_taboo_exists_sgui", "nd_taboo_breakdown_sgui"):
            body = block(self.sguis, name)
            self.assertIn("is_valid = { always = no }", body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)
            self.assertIn(name, self.gui, name)

    def test_breakdown_prints_every_part_and_the_target(self):
        body = block(self.sguis, "nd_taboo_breakdown_sgui")
        for part in PARTS:
            self.assertIn(f"custom_tooltip_no_bullet = nd_taboo_bd_{part}", body, part)
            self.assertIn(f"GetGlobalVariable('nd_tb_{part}')", loc_value(f"nd_taboo_bd_{part}"), part)
        self.assertIn("custom_tooltip_no_bullet = nd_taboo_bd_target", body)

    def test_chart_records_and_draws_both_series(self):
        record = block(strip_comments(read(TABOO_EFFECTS)), "nd_taboo_record_history")
        self.assertIn("te_history_record_sample = { METRIC = nd_taboo VALUE = global_var:nd_taboo }", record)
        self.assertIn("te_history_record_sample = { METRIC = nd_taboo_tgt VALUE = global_var:nd_taboo_target }", record)
        self.assertIn("nd_taboo_record_history = yes", block(strip_comments(read(TABOO_EFFECTS)), "nd_taboo_country_monthly"))
        for metric in ("nd_taboo", "nd_taboo_tgt"):
            self.assertIn(f"ScriptContainer.HasVariable( 'te_hist_v_{metric}' )", self.gui, metric)
        section = self.gui[self.gui.index("nd_taboo_hist_open"):]
        self.assertGreaterEqual(section.count('blockoverride "marker_pips" {}'), 2)

    def test_custom_loc_targets_have_loc(self):
        keys = loc_keys()
        custom = strip_comments(read(PROGRAM_CUSTOM_LOC))
        targets = re.findall(r"localization_key = ((?:nd_taboo|nuclear_program)_\w+)", custom)
        self.assertTrue(targets)
        for key in targets:
            self.assertIn(key, keys, key)

    def test_every_panel_key_has_loc(self):
        keys = loc_keys()
        drawn = set(re.findall(r'(?:text|tooltip) = "((?:je_nuclear_program_widget_taboo|nd_taboo)_\w+)"', self.gui))
        drawn |= set(re.findall(r"Localize\( '((?:je_nuclear_program_widget_taboo|nd_taboo)_\w+)' \)", self.gui))
        self.assertTrue(drawn)
        for key in drawn:
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestPanel -v`
Expected: `nd_taboo_exists_sgui not found`, and similar.

- [ ] **Step 3: The value and the history** (`nuclear_taboo_values.txt`, `nuclear_taboo_effects.txt`)

Append to the DISPLAY section of the values file:

```
# Target less score: where the taboo is heading.
nd_taboo_gap_value = {
	value = nd_disp_taboo_target
	subtract = nd_taboo_value
}
```

Append to the effects file (after `nd_taboo_refresh_possession`):

```
# Two monthly series for the panel's chart, stored per tracked country for the
# reason the UN authority and global-warming series are (te_history_chart
# reads the country's own list; te_history_global_warming_effects.txt). No
# markers: the store's pips are shared with other systems and would go
# unexplained. te_history_record_sample gates on te_history_country_is_tracked
# itself. Scope: country (nd_taboo_country_monthly).
nd_taboo_record_history = {
	if = {
		limit = {
			has_global_variable = nd_taboo
			has_global_variable = nd_taboo_target
		}
		te_history_record_sample = { METRIC = nd_taboo VALUE = global_var:nd_taboo }
		te_history_record_sample = { METRIC = nd_taboo_tgt VALUE = global_var:nd_taboo_target }
	}
}
```

In `nd_taboo_country_monthly`, replace

```
		nd_taboo_refresh_held = yes
		nd_taboo_refresh_possession = yes
```

with

```
		nd_taboo_refresh_held = yes
		nd_taboo_refresh_possession = yes
		nd_taboo_record_history = yes
```

- [ ] **Step 4: The sguis** (append to `nuclear_program_sguis.txt`; add both names to its header's list of display handlers)

```

# ---- The nuclear taboo (nuclear_taboo_values.txt) — display only -----------------

# Whether the taboo exists yet: the panel section is drawn from the first
# warhead on.
nd_taboo_exists_sgui = {
	scope = country
	is_shown = {
		has_global_variable = nd_taboo
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = { }
}

# The target, part by part, from the snapshots the world's monthly step wrote.
# The lines add up to the target line.
nd_taboo_breakdown_sgui = {
	scope = country
	is_shown = {
		has_global_variable = nd_taboo_target
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = {
		if = {
			limit = { has_global_variable = nd_taboo_target }
			custom_tooltip_no_bullet = nd_taboo_bd_base
			custom_tooltip_no_bullet = nd_taboo_bd_tradition
			custom_tooltip_no_bullet = nd_taboo_bd_postures
			custom_tooltip_no_bullet = nd_taboo_bd_restraint
			custom_tooltip_no_bullet = nd_taboo_bd_ledger
			custom_tooltip_no_bullet = nd_taboo_bd_target
		}
	}
}
```

- [ ] **Step 5: The custom loc** (append to `nuclear_program_custom_loc.txt`'s widget-only section)

```

# Where the taboo is heading (nd_taboo_gap_value).
nd_taboo_heading = {
	type = country
	random_valid = no

	text = {
		trigger = { nd_taboo_gap_value > 1 }
		localization_key = nd_taboo_heading_up
	}
	text = {
		trigger = { nd_taboo_gap_value < -1 }
		localization_key = nd_taboo_heading_down
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_heading_steady
	}
}

# When a nuclear weapon was last used in anger.
nd_taboo_last_use = {
	type = country
	random_valid = no

	text = {
		trigger = { has_global_variable = nd_taboo_last_use_year }
		localization_key = nd_taboo_last_use_year_known
	}
	text = {
		trigger = { has_global_variable = world_first_nuclear_weapon_used }
		localization_key = nd_taboo_last_use_before
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_taboo_last_use_never
	}
}
```

- [ ] **Step 6: The panel** (`nuclear_program_widget.gui`)

In the header comment of `widget_je_nuclear_balance`, change "Two collapsed sections" to "The nuclear taboo (open), then two collapsed sections". Then replace

```
	visible = "[JournalEntry.IsActive]"

	### ---- What we can deliver, and what we can stop ------------------------
```

with

```
	visible = "[JournalEntry.IsActive]"

	### ---- The nuclear taboo (open) ------------------------------------------
	### The world's score, where it is heading and why, and what it costs us
	### now (nuclear_taboo_values.txt). Drawn from the first warhead on, for
	### every country — the entry is active for all of them by then.
	nuclear_program_section_header = {
		visible = "[GetScriptedGui('nd_taboo_exists_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
		blockoverride "left_text" {
			text = "je_nuclear_program_widget_taboo_header"
		}
		blockoverride "onclick" {
			onclick = "[GetVariableSystem.Toggle('nd_taboo_panel_closed')]"
		}
		# Open by default: Exists means *collapsed* for this section.
		blockoverride "onclick_showmore" {
			visible = "[GetVariableSystem.Exists('nd_taboo_panel_closed')]"
		}
		blockoverride "onclick_showless" {
			visible = "[Not(GetVariableSystem.Exists('nd_taboo_panel_closed'))]"
		}
	}

	nuclear_program_panel = {
		visible = "[And( GetScriptedGui('nd_taboo_exists_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), Not(GetVariableSystem.Exists('nd_taboo_panel_closed')) )]"

		nuclear_program_row = {
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_score_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_score_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "[Concatenate( Localize( 'je_nuclear_program_widget_taboo_score_tt' ), GetScriptedGui('nd_taboo_breakdown_sgui').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ) )]"
			}
		}

		nuclear_program_row = {
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_heading_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_heading_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "[Concatenate( Localize( 'je_nuclear_program_widget_taboo_score_tt' ), GetScriptedGui('nd_taboo_breakdown_sgui').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ) )]"
			}
		}

		nuclear_program_row = {
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_strategic_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_strategic_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "je_nuclear_program_widget_taboo_costs_tt"
			}
		}

		nuclear_program_row = {
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_tactical_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_tactical_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "je_nuclear_program_widget_taboo_costs_tt"
			}
		}

		nuclear_program_row = {
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_threat_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_threat_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "je_nuclear_program_widget_taboo_costs_tt"
			}
		}

		nuclear_program_row = {
			visible = "[GetScriptedGui('nd_armed_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			blockoverride "row_label" {
				text = "je_nuclear_program_widget_taboo_burden_label"
			}
			blockoverride "row_value" {
				text = "je_nuclear_program_widget_taboo_burden_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "je_nuclear_program_widget_taboo_burden_tt"
			}
		}

		nuclear_program_text = {
			text = "je_nuclear_program_widget_taboo_note"
			default_format = "#lore"
		}

		### The taboo's history (closed by default) — the shared chart types
		### and range variable (te_history_chart.gui), as the UN chart uses.
		nuclear_program_section_header = {
			blockoverride "left_text" {
				text = "je_nuclear_program_widget_taboo_history_header"
			}
			blockoverride "onclick" {
				onclick = "[GetVariableSystem.Toggle('nd_taboo_hist_open')]"
			}
			blockoverride "onclick_showmore" {
				visible = "[Not(GetVariableSystem.Exists('nd_taboo_hist_open'))]"
			}
			blockoverride "onclick_showless" {
				visible = "[GetVariableSystem.Exists('nd_taboo_hist_open')]"
			}
		}

		flowcontainer = {
			direction = vertical
			parentanchor = hcenter
			ignoreinvisible = yes
			spacing = 2
			visible = "[GetVariableSystem.Exists('nd_taboo_hist_open')]"

			flowcontainer = {
				direction = horizontal
				ignoreinvisible = yes
				parentanchor = hcenter
				spacing = 4
				margin = { 4 4 }

				te_history_range_button = {
					blockoverride "range_text" {
						text = "te_hist_range_1y"
					}
					blockoverride "range_enabled" {
						enabled = "[Not(GetVariableSystem.HasValue( 'te_hist_range', '1' ))]"
					}
					blockoverride "range_onclick" {
						onclick = "[GetVariableSystem.Set( 'te_hist_range', '1' )]"
					}
				}
				te_history_range_button = {
					blockoverride "range_text" {
						text = "te_hist_range_5y"
					}
					blockoverride "range_enabled" {
						enabled = "[Not(GetVariableSystem.HasValue( 'te_hist_range', '5' ))]"
					}
					blockoverride "range_onclick" {
						onclick = "[GetVariableSystem.Set( 'te_hist_range', '5' )]"
					}
				}
				te_history_range_button = {
					blockoverride "range_text" {
						text = "te_hist_range_20y"
					}
					blockoverride "range_enabled" {
						enabled = "[Or( GetVariableSystem.HasValue( 'te_hist_range', '1' ), GetVariableSystem.HasValue( 'te_hist_range', '5' ) )]"
					}
					blockoverride "range_onclick" {
						onclick = "[GetVariableSystem.Set( 'te_hist_range', '20' )]"
					}
				}
			}

			textbox = {
				visible = "[Not( IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('te_hist') ) )]"
				parentanchor = hcenter
				autoresize = yes
				multiline = yes
				max_width = 480
				align = hcenter|nobaseline
				text = "te_hist_since"
			}

			te_history_chart = {
				blockoverride "chart_title" {
					text = "nd_taboo_hist_title"
				}
				blockoverride "chart_legend" {
					text = "nd_taboo_hist_legend"
				}
				# The store's marker pips belong to other systems.
				blockoverride "marker_pips" {}
				blockoverride "bar_tooltip" {
					tooltip = "nd_taboo_hist_tt"
				}
				blockoverride "bar_body" {
					te_history_bar_unsigned = {
						visible = "[ScriptContainer.HasVariable( 'te_hist_v_nd_taboo' )]"
						blockoverride "values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)2', ScriptContainer.GetVariableValue( 'te_hist_v_nd_taboo' ) ) )]"
						}
						blockoverride "cover_values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)0', Subtract_CFixedPoint( ScriptContainer.GetVariableValue( 'te_hist_v_nd_taboo' ), '(CFixedPoint)4' ) ) )]"
						}
						blockoverride "color" {
							color = { 0.80 0.45 0.25 1.0 }
						}
					}
				}
			}

			te_history_chart = {
				blockoverride "chart_title" {
					text = "nd_taboo_hist_target_title"
				}
				blockoverride "chart_legend" {
					text = "nd_taboo_hist_target_legend"
				}
				# The store's marker pips belong to other systems.
				blockoverride "marker_pips" {}
				blockoverride "bar_tooltip" {
					tooltip = "nd_taboo_hist_target_tt"
				}
				blockoverride "bar_body" {
					te_history_bar_unsigned = {
						visible = "[ScriptContainer.HasVariable( 'te_hist_v_nd_taboo_tgt' )]"
						blockoverride "values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)2', ScriptContainer.GetVariableValue( 'te_hist_v_nd_taboo_tgt' ) ) )]"
						}
						blockoverride "cover_values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)0', Subtract_CFixedPoint( ScriptContainer.GetVariableValue( 'te_hist_v_nd_taboo_tgt' ), '(CFixedPoint)4' ) ) )]"
						}
						blockoverride "color" {
							color = { 0.55 0.55 0.70 1.0 }
						}
					}
				}
			}
		}
	}

	### ---- What we can deliver, and what we can stop ------------------------
```

- [ ] **Step 7: Loc**

`te_journal_entries_l_english.yml`:

```
 je_nuclear_program_widget_taboo_burden_label:0 "Burden of our arsenal"
 je_nuclear_program_widget_taboo_burden_tt:0 "#tooltip_header The Burden of the Bomb#!\n$TOOLTIP_DELIMITER$\nThe world holds nuclear weapons in horror, and holds it against those who keep them: from a taboo of 40 up, the larger our arsenal (up to fifty warheads), the heavier the burden. It turns the bomb's prestige against us, takes away the leverage it brought, and sets our restraint-minded interest groups against the arsenal itself. Hold the arsenal to a ceiling, or give it up, to lighten it."
 je_nuclear_program_widget_taboo_burden_value:0 "#v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_taboo_burden_pct')|0]%#! · prestige #R [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_taboo_prestige_cost_pct')|0]%#! · leverage #R [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_taboo_leverage_cost_pct')|0]%#!"
 je_nuclear_program_widget_taboo_costs_tt:0 "#tooltip_header What the Taboo Costs#!\n$TOOLTIP_DELIMITER$\nWhat a nuclear act costs us today. Every figure moves with the taboo: at zero, nothing; at its height, a first use makes a state a pariah. An answer to a strike on us, or on a country we protect, costs no infamy."
 je_nuclear_program_widget_taboo_header:0 "The Nuclear Taboo"
 je_nuclear_program_widget_taboo_heading_label:0 "Heading toward"
 je_nuclear_program_widget_taboo_heading_value:0 "#v [GetGlobalVariable('nd_taboo_target').GetValue|0]#! [JournalEntry.GetCountry.GetCustom('nd_taboo_heading')]"
 je_nuclear_program_widget_taboo_history_header:0 "The Taboo Over Time"
 je_nuclear_program_widget_taboo_note:0 "[JournalEntry.GetCountry.GetCustom('nd_taboo_last_use')]"
 je_nuclear_program_widget_taboo_score_label:0 "Nuclear taboo"
 je_nuclear_program_widget_taboo_score_tt:0 "#tooltip_header The Nuclear Taboo#!\n$TOOLTIP_DELIMITER$\nHow unthinkable the world finds nuclear weapons. It moves each month toward where the world's state puts it:\n"
 je_nuclear_program_widget_taboo_score_value:0 "#v [GetGlobalVariable('nd_taboo').GetValue|0]#! — [JournalEntry.GetCountry.GetCustom('nd_taboo_band_name')]"
 je_nuclear_program_widget_taboo_strategic_label:0 "First use on a city"
 je_nuclear_program_widget_taboo_strategic_value:0 "#R +[JournalEntry.GetCountry.MakeScope.ScriptValue('nd_taboo_infamy_strategic')|0]#! infamy · relations #R [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_taboo_world_relations_strategic')|0]#!"
 je_nuclear_program_widget_taboo_tactical_label:0 "First use on a battlefield"
 je_nuclear_program_widget_taboo_tactical_value:0 "#R +[JournalEntry.GetCountry.MakeScope.ScriptValue('nd_taboo_infamy_tactical')|0]#! infamy · relations #R [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_taboo_world_relations_tactical')|0]#!"
 je_nuclear_program_widget_taboo_threat_label:0 "A public ultimatum"
 je_nuclear_program_widget_taboo_threat_value:0 "#R +[JournalEntry.GetCountry.MakeScope.ScriptValue('nd_taboo_infamy_threat')|0]#! infamy"
```

`te_miscellaneous_l_english.yml`:

```
 nd_taboo_bd_base:0 "#v [GetGlobalVariable('nd_tb_base').GetValue|+0]#!  Where every nuclear age begins"
 nd_taboo_bd_ledger:0 "#v [GetGlobalVariable('nd_tb_ledger').GetValue|+1]#!  What the world has done lately — uses, threats, renunciations — fading over four years"
 nd_taboo_bd_postures:0 "#v [GetGlobalVariable('nd_tb_postures').GetValue|+1]#!  The nuclear powers' doctrines: No First Use and warheads in storage raise it, compellence and warfighting lower it"
 nd_taboo_bd_restraint:0 "#v [GetGlobalVariable('nd_tb_restraint').GetValue|+1]#!  Restraint: non-use pledges, and states that gave the bomb up"
 nd_taboo_bd_target:0 "#v = [GetGlobalVariable('nd_taboo_target').GetValue|1]#!  Drift alone reaches 55 at most; beyond that takes cooperation"
 nd_taboo_bd_tradition:0 "#v [GetGlobalVariable('nd_tb_tradition').GetValue|+1]#!  The tradition of non-use: #v [GetGlobalVariable('nd_taboo_quiet_years').GetValue|0]#! years' worth, full at #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_tradition_cap')|0]#!"
 nd_taboo_heading_down:0 "#R (falling)#!"
 nd_taboo_heading_steady:0 "(steady)"
 nd_taboo_heading_up:0 "#G (rising)#!"
 nd_taboo_hist_legend:0 "#lore 0-100, sampled monthly#!"
 nd_taboo_hist_target_legend:0 "#lore where the world's state was pulling it, 0-100#!"
 nd_taboo_hist_target_title:0 "Where the Taboo Was Heading"
 nd_taboo_hist_target_tt:0 "$te_hist_tt_date$\n[SelectLocalization( ScriptContainer.HasVariable('te_hist_v_nd_taboo_tgt'), 'nd_taboo_hist_target_tt_row', 'te_hist_tt_missing' )]"
 nd_taboo_hist_target_tt_row:0 "$nd_taboo_hist_target_title$: #v [ScriptContainer.GetVariableValue('te_hist_v_nd_taboo_tgt')|1]#!"
 nd_taboo_hist_title:0 "The Nuclear Taboo"
 nd_taboo_hist_tt:0 "$te_hist_tt_date$\n[SelectLocalization( ScriptContainer.HasVariable('te_hist_v_nd_taboo'), 'nd_taboo_hist_tt_row', 'te_hist_tt_missing' )]"
 nd_taboo_hist_tt_row:0 "$nd_taboo_hist_title$: #v [ScriptContainer.GetVariableValue('te_hist_v_nd_taboo')|1]#!"
 nd_taboo_last_use_before:0 "Nuclear weapons have been used in war."
 nd_taboo_last_use_never:0 "No nuclear weapon has ever been used in war."
 nd_taboo_last_use_year_known:0 "The last nuclear weapon used in war fell in #v [GetGlobalVariable('nd_taboo_last_use_year').GetValue|0]#!."
```

- [ ] **Step 8: Format, test, commit**

```bash
python3 scripts/format_paradox_tabs.py gui/journal_entry_widgets/nuclear_program_widget.gui common/scripted_guis/nuclear_program_sguis.txt common/customizable_localization/nuclear_program_custom_loc.txt common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 scripts/analysis/check_localization_files.py && python3 loc_render_audit.py --strict
git add test_nuclear_taboo.py gui/journal_entry_widgets/nuclear_program_widget.gui common/scripted_guis/nuclear_program_sguis.txt common/customizable_localization/nuclear_program_custom_loc.txt common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt localization/english/te_journal_entries_l_english.yml localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: the panel — score, why, what it costs, and its history

<attribution lines>"
```

---

### Task 10: Band events and civil defence

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING + BANDS)
- Modify: `common/scripted_triggers/nuclear_taboo_triggers.txt`
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (band check/fire, option bodies; `nd_taboo_monthly_update`)
- Modify: `common/static_modifiers/nuclear_taboo_modifiers.txt` (`nd_taboo_norm_champion`, `nd_taboo_civil_defence`)
- Modify: `events/nuclear_taboo_events.txt` (`.1`–`.8`)
- Modify: `common/script_values/zz_te_war_support_injections.txt`
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestBandEvents`)

**Interfaces:**
- Consumes: `nd_taboo_band` (global), `nd_taboo_line_*`, `nd_taboo_band_hysteresis`, `nd_taboo_event_cooldown_years`, `nd_taboo_dismantle_start`, `nd_set_doctrine_1`, `nuclear_program_effect_increase_funding`, `nd_taboo_refresh_held`.
- Produces:
  - effects `nd_taboo_band_check` (global), `nd_taboo_fire_band_event = { N EVENT }`, and the `nd_taboo_opt_*` bodies (country, ROOT = it);
  - globals `nd_taboo_ev_<N>_year`;
  - variable `nd_taboo_civil_defence_cost_cached` (never removed);
  - static modifiers `nd_taboo_norm_champion` and `nd_taboo_civil_defence`.

- [ ] **Step 1: Write the failing tests** (append)

```python
WAR_SUPPORT = ROOT / "common/script_values/zz_te_war_support_injections.txt"
HARDENING = [1, 2, 3, 4]
ERODING = [5, 6, 7, 8]


class TestBandEvents(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.values = strip_comments(read(TABOO_VALUES))
        self.events = strip_comments(read(TABOO_EVENTS))

    def test_band_check_uses_hysteresis_and_cooldown(self):
        self.assertIn("add = nd_taboo_band_hysteresis", block(self.values, "nd_taboo_up_threshold_value"))
        self.assertIn("subtract = nd_taboo_band_hysteresis", block(self.values, "nd_taboo_down_threshold_value"))
        self.assertIn("subtract = nd_taboo_event_cooldown_years", block(self.values, "nd_taboo_cooldown_cutoff_year"))
        trig = strip_comments(read(TABOO_TRIGGERS))
        self.assertIn("nd_taboo_value >= nd_taboo_up_threshold_value", block(trig, "nd_taboo_band_up_due"))
        self.assertIn("nd_taboo_value <= nd_taboo_down_threshold_value", block(trig, "nd_taboo_band_down_due"))
        self.assertIn("nd_taboo_cooldown_cutoff_year", block(trig, "nd_taboo_event_ready"))
        update = block(self.taboo, "nd_taboo_monthly_update")
        self.assertLess(update.index("add = nd_taboo_step_value"), update.index("nd_taboo_band_check = yes"))

    def test_every_band_event_is_fired_once_per_crossing(self):
        fired = re.findall(r"nd_taboo_fire_band_event = \{ N = (\d) EVENT = nuclear_taboo\.(\d) \}", self.taboo)
        self.assertEqual(sorted((int(n), int(e)) for n, e in fired), [(n, n) for n in range(1, 9)])

    def test_every_event_serves_armed_and_unarmed(self):
        for n in HARDENING + ERODING:
            body = block(self.events, f"nuclear_taboo.{n}")
            self.assertIn("nd_is_armed = yes", body, n)
            self.assertIn("nd_is_armed = no", body, n)
            self.assertIn("event_image", body, n)

    def test_options_never_write_the_score(self):
        for needle in ("nd_taboo_ledger_add", "nd_taboo_shock", "nd_taboo_note_use", "name = nd_taboo "):
            self.assertNotIn(needle, self.events, needle)
        for name in ("nd_taboo_opt_cut_arsenal", "nd_taboo_opt_stand_firm", "nd_taboo_opt_hold_line",
                     "nd_taboo_opt_champion", "nd_taboo_opt_keep_quiet", "nd_taboo_opt_seek_protector",
                     "nd_taboo_opt_modernise", "nd_taboo_opt_shelters"):
            body = block(self.taboo, name)
            for needle in ("nd_taboo_ledger_add", "nd_taboo_shock"):
                self.assertNotIn(needle, body, name)

    def test_cut_refreshes_the_hold(self):
        self.assertIn("nd_taboo_refresh_held = yes", block(self.taboo, "nd_taboo_opt_cut_arsenal"))

    def test_civil_defence(self):
        ws = strip_comments(read(WAR_SUPPORT))
        self.assertIn("has_modifier = nd_taboo_civil_defence", ws)
        self.assertIn('desc = "WAR_SUPPORT_TE_CIVIL_DEFENCE"', ws)
        self.assertIn("multiplier = root.var:nd_taboo_civil_defence_cost_cached", block(self.taboo, "nd_taboo_opt_shelters"))
        self.assertNotIn("remove_variable = nd_taboo_civil_defence_cost_cached", self.taboo + self.events)
        for n in ERODING:
            immediate = block(block(self.events, f"nuclear_taboo.{n}"), "immediate")
            self.assertIn("name = nd_taboo_civil_defence_cost_cached", immediate, n)

    def test_option_numbers_match_their_constants(self):
        for key, name in (("nd_taboo_tt_protector", "nd_taboo_protector_relations"),
                          ("nd_taboo_tt_quiet_relations", "nd_taboo_quiet_relations"),
                          ("nd_taboo_tt_modernise", "nd_taboo_modernise_reliability"),
                          ("nd_taboo_tt_modernise", "nd_taboo_modernise_survivability")):
            n = abs(int(constant(self.values, name)))
            self.assertIn(str(n), loc_value(key), key)

    def test_event_keys_have_loc(self):
        keys = loc_keys()
        for n in HARDENING + ERODING:
            for suffix in ("t", "d", "f"):
                self.assertIn(f"nuclear_taboo.{n}.{suffix}", keys)
        for key in set(re.findall(r"name = (nd_taboo_opt_\w+)", self.events)):
            self.assertIn(key, keys, key)
        for key in ("nd_taboo_norm_champion", "nd_taboo_norm_champion_desc", "nd_taboo_civil_defence",
                    "nd_taboo_civil_defence_desc", "WAR_SUPPORT_TE_CIVIL_DEFENCE"):
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestBandEvents -v`
Expected: failures and errors across the class.

- [ ] **Step 3: Constants and values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_civil_defence_units = 5
nd_taboo_protector_relations = 15
nd_taboo_champion_relations = -5
nd_taboo_quiet_relations = 5
nd_taboo_modernise_reliability = 10
nd_taboo_modernise_survivability = 5
```

Append a section:

```
# ---- BAND EVENTS (spec §6.3) — any scope ------------------------------------------
# global_var:nd_taboo_band is the band last announced (1..5). The next band up
# is announced at 2 above its line, the next down at 2 below the current
# band's line.

nd_taboo_upper_line_value = {
	value = 1000
	if = {
		limit = { global_var:nd_taboo_band = 1 }
		value = nd_taboo_line_fragile
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 2 }
		value = nd_taboo_line_established
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 3 }
		value = nd_taboo_line_strong
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 4 }
		value = nd_taboo_line_absolute
	}
}

nd_taboo_lower_line_value = {
	value = -1000
	if = {
		limit = { global_var:nd_taboo_band = 2 }
		value = nd_taboo_line_fragile
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 3 }
		value = nd_taboo_line_established
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 4 }
		value = nd_taboo_line_strong
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 5 }
		value = nd_taboo_line_absolute
	}
}

nd_taboo_up_threshold_value = {
	value = nd_taboo_upper_line_value
	add = nd_taboo_band_hysteresis
}

nd_taboo_down_threshold_value = {
	value = nd_taboo_lower_line_value
	subtract = nd_taboo_band_hysteresis
}

# An event last fired in this year or earlier may fire again.
nd_taboo_cooldown_cutoff_year = {
	value = year
	subtract = nd_taboo_event_cooldown_years
}

# Shelters and civil defence: 5 of the posture upkeep's units (1/100,000 of
# GDP a week). Scope: country
nd_taboo_civil_defence_weekly_value = {
	value = gdp
	divide = 100000
	multiply = nd_taboo_civil_defence_units
}
```

- [ ] **Step 4: Triggers** (append to `nuclear_taboo_triggers.txt`)

```

# ---- BAND EVENTS (spec §6.3) -----------------------------------------------------

nd_taboo_band_up_due = {
	has_global_variable = nd_taboo_band
	nd_taboo_value >= nd_taboo_up_threshold_value
}

nd_taboo_band_down_due = {
	has_global_variable = nd_taboo_band
	nd_taboo_value <= nd_taboo_down_threshold_value
}

# N = 1..8: this boundary-and-direction has not fired in ten years.
nd_taboo_event_ready = {
	OR = {
		NOT = { has_global_variable = nd_taboo_ev_$N$_year }
		global_var:nd_taboo_ev_$N$_year <= nd_taboo_cooldown_cutoff_year
	}
}

# A candidate protector for a band event's unarmed recipient (ROOT): armed,
# and on good terms with us.
nd_taboo_friendly_armed_power = {
	NOT = { this = root }
	nd_is_armed = yes
	relations:root >= relations_threshold:amicable
}
```

- [ ] **Step 5: Effects** (`nuclear_taboo_effects.txt`)

In `nd_taboo_monthly_update`, insert `nd_taboo_band_check = yes` on its own line directly above the `debug_log = "TE_TABOO: score …"` line (after the step). Then append a section:

```
# ----------------------------------------------------------------------------
# BAND EVENTS (spec §6.3) — the world's step calls the check; global scope
# ----------------------------------------------------------------------------

# One band a month, up or down; the band moves even when the event is on
# cooldown.
nd_taboo_band_check = {
	if = {
		limit = { nd_taboo_band_up_due = yes }
		change_global_variable = { name = nd_taboo_band add = 1 }
		nd_taboo_fire_band_up = yes
	}
	else_if = {
		limit = { nd_taboo_band_down_due = yes }
		change_global_variable = { name = nd_taboo_band subtract = 1 }
		nd_taboo_fire_band_down = yes
	}
}

# The band has just risen to 2..5: through 30 / 50 / 70 / 90.
nd_taboo_fire_band_up = {
	if = {
		limit = { global_var:nd_taboo_band = 2 }
		nd_taboo_fire_band_event = { N = 1 EVENT = nuclear_taboo.1 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 3 }
		nd_taboo_fire_band_event = { N = 2 EVENT = nuclear_taboo.2 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 4 }
		nd_taboo_fire_band_event = { N = 3 EVENT = nuclear_taboo.3 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 5 }
		nd_taboo_fire_band_event = { N = 4 EVENT = nuclear_taboo.4 }
	}
}

# The band has just fallen to 4..1: through 90 / 70 / 50 / 30.
nd_taboo_fire_band_down = {
	if = {
		limit = { global_var:nd_taboo_band = 4 }
		nd_taboo_fire_band_event = { N = 5 EVENT = nuclear_taboo.5 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 3 }
		nd_taboo_fire_band_event = { N = 6 EVENT = nuclear_taboo.6 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 2 }
		nd_taboo_fire_band_event = { N = 7 EVENT = nuclear_taboo.7 }
	}
	else_if = {
		limit = { global_var:nd_taboo_band = 1 }
		nd_taboo_fire_band_event = { N = 8 EVENT = nuclear_taboo.8 }
	}
}

# To every country, as global warming's thresholds are (gw_fire_warming_threshold_event).
nd_taboo_fire_band_event = {
	if = {
		limit = { nd_taboo_event_ready = { N = $N$ } }
		set_global_variable = { name = nd_taboo_ev_$N$_year value = year }
		every_country = {
			limit = { NOT = { is_country_type = decentralized } }
			trigger_event = { id = $EVENT$ }
		}
		debug_log = "TE_TABOO: a band event fired"
	}
}

# ---- The band events' option bodies — country scope, ROOT = the recipient.
# Country-local: none writes the world's score. Two enact a real system action
# (nd_set_doctrine_1, nd_taboo_dismantle_start), which carries its own effect.

nd_taboo_opt_cut_arsenal = {
	custom_tooltip = {
		text = nd_taboo_tt_opt_cut
		set_variable = { name = nd_warhead_ceiling value = nd_taboo_half_arsenal_value }
	}
	hidden_effect = {
		nd_taboo_refresh_held = yes
	}
}

nd_taboo_opt_stand_firm = {
	every_interest_group = {
		limit = { nd_ig_is_hawk = yes }
		add_modifier = {
			name = ig_approval_positive_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
	every_interest_group = {
		limit = { nd_ig_is_restraint = yes }
		add_modifier = {
			name = ig_approval_negative_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
}

nd_taboo_opt_hold_line = {
	every_interest_group = {
		limit = { nd_ig_is_restraint = yes }
		add_modifier = {
			name = ig_approval_positive_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
	every_interest_group = {
		limit = { nd_ig_is_hawk = yes }
		add_modifier = {
			name = ig_approval_negative_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
}

nd_taboo_opt_champion = {
	add_modifier = {
		name = nd_taboo_norm_champion
		years = 10
		is_decaying = yes
	}
	custom_tooltip = {
		text = nd_taboo_tt_champion_relations
		every_country = {
			limit = {
				NOT = { this = ROOT }
				nd_is_armed = yes
				country_rank >= rank_value:great_power
			}
			change_relations = { country = ROOT value = nd_taboo_champion_relations }
		}
	}
}

nd_taboo_opt_keep_quiet = {
	custom_tooltip = {
		text = nd_taboo_tt_quiet_relations
		every_country = {
			limit = {
				NOT = { this = ROOT }
				nd_is_armed = yes
				country_rank >= rank_value:great_power
			}
			change_relations = { country = ROOT value = nd_taboo_quiet_relations }
		}
	}
}

nd_taboo_opt_seek_protector = {
	custom_tooltip = {
		text = nd_taboo_tt_protector
		random_country = {
			limit = { nd_taboo_friendly_armed_power = yes }
			change_relations = { country = ROOT value = nd_taboo_protector_relations }
		}
	}
}

nd_taboo_opt_modernise = {
	custom_tooltip = {
		text = nd_taboo_tt_modernise
		change_variable = { name = nd_reliability add = nd_taboo_modernise_reliability }
		clamp_variable = { name = nd_reliability min = 0 max = 100 }
		change_variable = { name = nd_survivability add = nd_taboo_modernise_survivability }
		clamp_variable = { name = nd_survivability min = 0 max = 100 }
	}
	every_interest_group = {
		limit = { nd_ig_is_restraint = yes }
		add_modifier = {
			name = ig_approval_negative_modifier
			days = normal_modifier_time
			is_decaying = yes
		}
	}
}

# The eroding events' immediate caches the weekly cost first, so the option's
# preview shows it; the cache is never removed (modifier_multiplier_var_audit).
nd_taboo_opt_shelters = {
	add_modifier = {
		name = nd_taboo_civil_defence
		years = 10
		multiplier = root.var:nd_taboo_civil_defence_cost_cached
	}
	custom_tooltip = nd_taboo_tt_shelters_war_support
}
```

- [ ] **Step 6: Static modifiers** (append to `nuclear_taboo_modifiers.txt`, and add both to its header table)

```

# A band event's "Champion the norm abroad": 10 years, decaying.
nd_taboo_norm_champion = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_prestige_mult = 0.05
}

# A band event's "Build shelters and civil defence": 10 years, costing 5 of
# the posture upkeep's units a week (multiplier = root.var:
# nd_taboo_civil_defence_cost_cached); while it holds, an enemy's arsenal
# drains our war support half as fast (zz_te_war_support_injections.txt).
nd_taboo_civil_defence = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_expenses_add = 1
}
```

Header lines:

```
#   nd_taboo_norm_champion           nd_taboo_opt_champion (nuclear_taboo.1-.4)
#   nd_taboo_civil_defence           nd_taboo_opt_shelters (nuclear_taboo.5-.8),
#                                    multiplier = root.var:nd_taboo_civil_defence_cost_cached
```

- [ ] **Step 7: Civil defence halves the nuclear shadow** (`zz_te_war_support_injections.txt`)

Replace

```
		add = {
			value = -0.25
			desc = "WAR_SUPPORT_TE_NUCLEAR_SHADOW"
		}
```

with

```
		add = {
			value = -0.25
			desc = "WAR_SUPPORT_TE_NUCLEAR_SHADOW"
		}
		# Shelters and civil defence (the nuclear taboo's band events,
		# nd_taboo_civil_defence) halve it.
		if = {
			limit = { has_modifier = nd_taboo_civil_defence }
			add = {
				value = 0.125
				desc = "WAR_SUPPORT_TE_CIVIL_DEFENCE"
			}
		}
```

- [ ] **Step 8: The events** (append to `events/nuclear_taboo_events.txt`, above `.20`)

The four hardening events share one option set, and the four eroding events share another. Every block is written out below.

```
# ---- The taboo hardens (nd_taboo_fire_band_up) ------------------------------

nuclear_taboo.1 = {
	type = country_event
	placement = root

	event_image = { texture = "gfx/event_pictures/anti_nuclear_movement.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = nuclear_taboo.1.t
	desc = nuclear_taboo.1.d
	flavor = nuclear_taboo.1.f

	duration = 3

	trigger = {
		has_game_rule = nuclear_weapons_enabled
	}

	option = {
		name = nd_taboo_opt_cut
		trigger = {
			nd_is_armed = yes
			nd_taboo_is_dismantling = no
			nd_stockpile > 1
		}
		nd_taboo_opt_cut_arsenal = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { nd_taboo_burden_value >= nd_taboo_burden_step_mild }
				add = 3
			}
		}
	}
	option = {
		name = nd_taboo_opt_dismantle
		trigger = {
			nd_is_armed = yes
			nd_taboo_can_dismantle = yes
		}
		nd_taboo_dismantle_start = yes
		ai_chance = {
			base = 0
			modifier = {
				trigger = { nd_taboo_ai_would_dismantle = yes }
				add = 2
			}
		}
	}
	option = {
		name = nd_taboo_opt_nfu
		trigger = {
			nd_is_armed = yes
			nd_doctrine_nfu = no
			nd_can_set_doctrine = { D = 1 }
		}
		nd_set_doctrine_1 = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { ruler_is_cautious = yes }
				add = 2
			}
			modifier = {
				trigger = { nd_regime_is_militarist = yes }
				factor = 0
			}
		}
	}
	option = {
		name = nd_taboo_opt_firm
		trigger = { nd_is_armed = yes }
		nd_taboo_opt_stand_firm = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { nd_regime_is_militarist = yes }
				add = 3
			}
		}
	}
	option = {
		name = nd_taboo_opt_champion
		trigger = { nd_is_armed = no }
		nd_taboo_opt_champion = yes
		ai_chance = {
			base = 2
			modifier = {
				trigger = { nd_is_guaranteed = yes }
				add = -1
			}
		}
	}
	option = {
		name = nd_taboo_opt_quiet
		default_option = yes
		trigger = { nd_is_armed = no }
		nd_taboo_opt_keep_quiet = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { nd_is_guaranteed = yes }
				add = 2
			}
		}
	}
}
```

Write `nuclear_taboo.2`, `.3` and `.4` as the same block, with only these lines changed:

| Event | `event_image` texture | title/desc/flavor keys |
|---|---|---|
| `.2` | `gfx/event_pictures/nuclear_diplomacy_talks.dds` | `nuclear_taboo.2.t/.d/.f` |
| `.3` | `gfx/event_pictures/nuclear_treaty_signing.dds` | `nuclear_taboo.3.t/.d/.f` |
| `.4` | `gfx/event_pictures/nuclear_defense_shield.dds` | `nuclear_taboo.4.t/.d/.f` |

(The option blocks are character-for-character identical. Copy `.1`'s body and change those four lines. `test_every_event_serves_armed_and_unarmed` checks each one.)

```
# ---- The taboo erodes (nd_taboo_fire_band_down) ------------------------------

nuclear_taboo.5 = {
	type = country_event
	placement = root

	event_image = { texture = "gfx/event_pictures/nuclear_standoff_tension.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = nuclear_taboo.5.t
	desc = nuclear_taboo.5.d
	flavor = nuclear_taboo.5.f

	duration = 3

	trigger = {
		has_game_rule = nuclear_weapons_enabled
	}

	immediate = {
		set_variable = { name = nd_taboo_civil_defence_cost_cached value = nd_taboo_civil_defence_weekly_value }
	}

	option = {
		name = nd_taboo_opt_protector
		trigger = {
			nd_is_armed = no
			any_country = { nd_taboo_friendly_armed_power = yes }
		}
		nd_taboo_opt_seek_protector = yes
		ai_chance = {
			base = 2
		}
	}
	option = {
		name = nd_taboo_opt_programme
		trigger = {
			nd_is_armed = no
			nuclear_program_possible_increase_funding = yes
		}
		nuclear_program_effect_increase_funding = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { nd_has_plausible_attacker = yes }
				add = 2
			}
		}
	}
	option = {
		name = nd_taboo_opt_shelters
		default_option = yes
		trigger = { nd_is_armed = no }
		nd_taboo_opt_shelters = yes
		ai_chance = {
			base = 1
		}
	}
	option = {
		name = nd_taboo_opt_modernise
		trigger = {
			nd_is_armed = yes
			nd_is_initialized = yes
		}
		nd_taboo_opt_modernise = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { nd_regime_is_militarist = yes }
				add = 2
			}
		}
	}
	option = {
		name = nd_taboo_opt_hold
		trigger = { nd_is_armed = yes }
		nd_taboo_opt_hold_line = yes
		ai_chance = {
			base = 1
			modifier = {
				trigger = { ruler_is_cautious = yes }
				add = 2
			}
		}
	}
}
```

Write `nuclear_taboo.6`, `.7` and `.8` as the same block, with only these lines changed:

| Event | `event_image` texture | title/desc/flavor keys |
|---|---|---|
| `.6` | `gfx/event_pictures/nuclear_test_mushroom.dds` | `nuclear_taboo.6.t/.d/.f` |
| `.7` | `gfx/event_pictures/mushroom_cloud_distant.dds` | `nuclear_taboo.7.t/.d/.f` |
| `.8` | `gfx/event_pictures/nuclear_bunker_life.dds` | `nuclear_taboo.8.t/.d/.f` |

Also update the file header's event list if it needs it; it already names `.1`–`.8`.

- [ ] **Step 9: Loc**

`te_events_l_english.yml`:

```
 nuclear_taboo.1.d:0 "For years the bomb was argued over like any other weapon: its yield, its range, its price. That is changing. The photographs of what it does have gone around the world, scientists sign open letters, and in parliaments the word \"unthinkable\" is heard as often as \"decisive\". The nuclear taboo has risen to #v [GetGlobalVariable('nd_taboo').GetValue|0]#!: not yet a rule, but no longer nothing."
 nuclear_taboo.1.f:0 "\"It is not a weapon. It is the end of weapons.\""
 nuclear_taboo.1.t:0 "Something Different About This Weapon"
 nuclear_taboo.2.d:0 "A consensus has settled over the world's chancelleries: using the bomb would be a crime, not a choice. Governments that hold it now take care to say they never would. The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, and a government that crossed the line would pay for it in every capital."
 nuclear_taboo.2.f:0 "\"We keep it so that no one will ever use it. Including us.\""
 nuclear_taboo.2.t:0 "A Line the World Will Not Cross"
 nuclear_taboo.3.d:0 "In the world's eyes the bomb has become a weapon that cannot be used. Holding one now draws questions at home and censure abroad, and the larger the arsenal, the sharper both become. The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.3.f:0 "\"There is no cause on earth for which I would do this. I say that to our enemies and to our own generals.\""
 nuclear_taboo.3.t:0 "The Unusable Weapon"
 nuclear_taboo.4.d:0 "Using the bomb is now spoken of the way the world speaks of slavery or genocide: as something civilised states do not do. To hold one at all sets a state apart. The nuclear taboo stands at #v [GetGlobalVariable('nd_taboo').GetValue|0]#!, higher than it has ever been."
 nuclear_taboo.4.f:0 "\"The question is no longer when these weapons might be used, but why anyone still keeps them.\""
 nuclear_taboo.4.t:0 "Beyond the Pale"
 nuclear_taboo.5.d:0 "The consensus that the bomb could never be used has cracked. Voices once kept to the fringes argue that deterrence means nothing if no one believes it, and some governments have begun to listen. The nuclear taboo has fallen to #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.5.f:0 "\"A weapon no one would ever use is not a deterrent. It is a museum piece.\""
 nuclear_taboo.5.t:0 "The First Crack"
 nuclear_taboo.6.d:0 "Generals write openly about limited nuclear war, and politicians no longer apologise for their threats. The weapon everyone agreed could not be used is being discussed as though it could. The nuclear taboo has fallen to #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.6.f:0 "\"We have to think about the unthinkable, because our enemies are thinking about it.\""
 nuclear_taboo.6.t:0 "Talk of the Unthinkable"
 nuclear_taboo.7.d:0 "The line against the bomb is fraying. Threats are traded openly, arsenals are praised rather than excused, and a use that once seemed impossible now seems merely terrible. The nuclear taboo has fallen to #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.7.f:0 "\"It is a bigger bomb. That is all it has ever been.\""
 nuclear_taboo.7.t:0 "The Taboo Frays"
 nuclear_taboo.8.d:0 "In the world's eyes the bomb has become one more weapon: fearsome, expensive and usable. Those who hold it are envied rather than censured, and those who do not are left to wonder how long they can afford not to. The nuclear taboo has fallen to #v [GetGlobalVariable('nd_taboo').GetValue|0]#!."
 nuclear_taboo.8.f:0 "\"The only nations that fear the bomb are the ones without it.\""
 nuclear_taboo.8.t:0 "Just Another Weapon"
```

`te_miscellaneous_l_english.yml`:

```
 WAR_SUPPORT_TE_CIVIL_DEFENCE:0 "Shelters and civil defence"
 nd_taboo_civil_defence:0 "Civil Defence"
 nd_taboo_civil_defence_desc:0 "Shelters, sirens and drills. For ten years an enemy's arsenal drains our war support half as fast."
 nd_taboo_norm_champion:0 "Champion of the Taboo"
 nd_taboo_norm_champion_desc:0 "We speak for the world's horror of the bomb, and the world listens."
 nd_taboo_opt_champion:0 "Champion the norm abroad"
 nd_taboo_opt_cut:0 "Cut our arsenal in half"
 nd_taboo_opt_dismantle:0 "Take our arsenal apart"
 nd_taboo_opt_firm:0 "Our deterrent is not negotiable"
 nd_taboo_opt_hold:0 "Say publicly that nothing has changed"
 nd_taboo_opt_modernise:0 "Modernise the arsenal"
 nd_taboo_opt_nfu:0 "Pledge never to use it first"
 nd_taboo_opt_programme:0 "Put more into our own programme"
 nd_taboo_opt_protector:0 "Seek the shelter of a friendly nuclear power"
 nd_taboo_opt_quiet:0 "Keep out of the powers' quarrel"
 nd_taboo_opt_shelters:0 "Build shelters and civil defence"
 nd_taboo_tt_champion_relations:0 "The great powers that hold nuclear weapons take it as a lecture: relations #R -5#! with each"
 nd_taboo_tt_modernise:0 "Reliability #G +10#!, survivability #G +5#!"
 nd_taboo_tt_opt_cut:0 "Hold our arsenal to #v [GetPlayer.MakeScope.ScriptValue('nd_taboo_half_arsenal_value')|0]#! warheads: those above it are taken apart, a tenth of the excess a month"
 nd_taboo_tt_protector:0 "Relations #G +15#! with a friendly nuclear power"
 nd_taboo_tt_quiet_relations:0 "The great powers that hold nuclear weapons appreciate our silence: relations #G +5#! with each"
 nd_taboo_tt_shelters_war_support:0 "For ten years, an enemy's arsenal drains our war support half as fast"
```

- [ ] **Step 10: Format, test, audit, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/static_modifiers/nuclear_taboo_modifiers.txt events/nuclear_taboo_events.txt common/script_values/zz_te_war_support_injections.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
for a in orphaned_event_audit event_image_audit event_context_audit silent_variable_audit empty_effect_audit modifier_multiplier_var_audit iterator_limit_audit; do python3 $a.py --strict || echo "FAILED: $a"; done
python3 scripts/analysis/check_localization_files.py && python3 loc_render_audit.py --strict
git add test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt common/static_modifiers/nuclear_taboo_modifiers.txt events/nuclear_taboo_events.txt common/script_values/zz_te_war_support_injections.txt localization/english/te_events_l_english.yml localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: every country hears when it hardens or erodes, and chooses how to answer

<attribution lines>"
```

If `event_context_audit` flags a band event, read the flag. `system_ungated` shouldn't fire, because the file is the nuclear system's own; `unchosen_self_action` shouldn't either, because the options are the recipient's choice. Fix the text if it is right. Tag it `# REVIEWED 2026-09-26 (<check>): <why>` inside the event only if the flag is a false positive.

---

### Task 11: Console harness, docs, and Phase 1 verification

**Files:**
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_debug_set`, `nd_taboo_debug_age_clock`)
- Modify: `events/te_debug_nuclear_events.txt` (`te_debug_nuclear.3`; header)
- Modify: `docs/systems/nuclear_crisis_design.md` (status banner, §0.11)
- Modify: `docs/systems/mod_systems.md` (Nuclear Weapons: the taboo; "Disarmament deactivates the entry")
- Modify: `docs/systems/journal_entry_systems.md` (**CRLF**; Nuclear Programme Widget, Nuclear Deterrence Widget areas)
- Modify: `docs/README.md` (the `nuclear_crisis_design.md` row)
- Modify: `docs/guides/scripting_best_practices.md` (one note)
- Modify: `localization/english/te_events_l_english.yml`

- [ ] **Step 1: The console harness**

Append to `nuclear_taboo_effects.txt`, in the WRITERS section:

```
# Console only (te_debug_nuclear.3). Births the taboo if it is not yet, then
# sets the score and its band. Scope: any.
nd_taboo_debug_set = {
	nd_taboo_birth = yes
	set_global_variable = { name = nd_taboo value = $VALUE$ }
	set_global_variable = { name = nd_taboo_band value = nd_taboo_band_value }
}

# Console only: ten more years without use.
nd_taboo_debug_age_clock = {
	if = {
		limit = { has_global_variable = nd_taboo }
		change_global_variable = { name = nd_taboo_quiet_years add = 10 }
	}
}
```

Append to `events/te_debug_nuclear_events.txt`, and add `te_debug_nuclear.3   the nuclear taboo: set it, age it, step it, renounce` to its header list:

```

te_debug_nuclear.3 = { # REVIEWED 2026-09-26: console-only test event (`event te_debug_nuclear.3`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { texture = "gfx/event_pictures/mushroom_cloud.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/mushroom_cloud.dds"

	title = te_debug_nuclear.3.t
	desc = te_debug_nuclear.3.desc
	flavor = te_debug_nuclear.3.f

	# The taboo at its birth value (born now if it was not).
	option = {
		name = te_debug_nuclear.3.a
		default_option = yes
		custom_tooltip = {
			text = te_debug_nuclear.3.tt_20
			nd_taboo_debug_set = { VALUE = 20 }
		}
	}
	# High enough for the possession burden, the AI's survival-only gate and a
	# Strong band event.
	option = {
		name = te_debug_nuclear.3.b
		custom_tooltip = {
			text = te_debug_nuclear.3.tt_85
			nd_taboo_debug_set = { VALUE = 85 }
		}
	}
	option = {
		name = te_debug_nuclear.3.c
		custom_tooltip = {
			text = te_debug_nuclear.3.tt_age
			nd_taboo_debug_age_clock = yes
		}
	}
	# The world's monthly step now (the one console exception to its
	# call-site contract); read the TE_TABOO: line in debug.log.
	option = {
		name = te_debug_nuclear.3.d
		custom_tooltip = {
			text = te_debug_nuclear.3.tt_step
			nd_taboo_monthly_update = yes
		}
	}
	# WARHEADS must be a value a trigger can compare (the effect's limit is
	# `$WARHEADS$ > 0`), so the count goes through a variable, not a literal.
	option = {
		name = te_debug_nuclear.3.e
		hidden_effect = {
			set_variable = { name = nd_taboo_debug_warheads value = 10 }
		}
		custom_tooltip = {
			text = te_debug_nuclear.3.tt_renounce
			nd_taboo_note_renunciation = { WARHEADS = var:nd_taboo_debug_warheads }
		}
	}
}
```

`te_events_l_english.yml`:

```
 te_debug_nuclear.3.a:0 "Taboo to 20"
 te_debug_nuclear.3.b:0 "Taboo to 85"
 te_debug_nuclear.3.c:0 "Ten more years without use"
 te_debug_nuclear.3.d:0 "Run the world's monthly step"
 te_debug_nuclear.3.desc:0 "Console harness for the nuclear taboo. Set the score, age the tradition of non-use, run the monthly step, or note a renunciation of ten warheads by us. The step logs a TE_TABOO: line."
 te_debug_nuclear.3.e:0 "Note a renunciation of 10 warheads"
 te_debug_nuclear.3.f:0 "Debug"
 te_debug_nuclear.3.t:0 "Debug: the Nuclear Taboo"
 te_debug_nuclear.3.tt_20:0 "The nuclear taboo is set to 20"
 te_debug_nuclear.3.tt_85:0 "The nuclear taboo is set to 85"
 te_debug_nuclear.3.tt_age:0 "Ten years are added to the tradition of non-use"
 te_debug_nuclear.3.tt_renounce:0 "We are noted as having given up ten warheads"
 te_debug_nuclear.3.tt_step:0 "The world's monthly taboo step runs now"
```

`test_only_the_writers_touch_the_score` still passes, because the debug event calls writers in the effects file.

- [ ] **Step 2: The simulator's table**

Run: `python3 scripts/analysis/nuclear_taboo_sim.py`. Keep its output for §0.11.

- [ ] **Step 3: `docs/systems/nuclear_crisis_design.md`**

Add to the status banner block, after the last `> **2026-09-26 (later):**` line:

```
> **2026-09-26 (taboo):** a world **nuclear taboo** (§0.11), per `docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md`: one score that scales every nuclear cost, makes possession a burden, feeds the AI, and adds unilateral dismantling and reduction. Phase 2 (arms control, the UN's terms, the Assembly's verdict) and phase 3 (a Prohibition convention) follow.
```

Insert a new section directly before `## 1. Intent and owner requirements`, built from the pieces below in this order:

```
### 0.11 The nuclear taboo

One world score, `global_var:nd_taboo` (0-100), for how unthinkable nuclear weapons are: born at 20 with the first warhead, moved each month toward a target of named parts, knocked down by use and worn by threats, and scaling every nuclear cost up to making possession itself a burden. The design, with every owner ruling, is `docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md`; `mod_systems.md` § Nuclear Weapons has the summary. Built 2026-09-26; nothing here has run in a game yet.
```

1. **Where it lives:** a table with the heading `#### Where it lives`, one row per file in this plan's File map (file | responsibility).
2. **Deviations from the spec:** under `#### Deviations from the spec`, this plan's Deviations list verbatim.
3. **Known roughnesses:** under `#### Known roughnesses`:
   - `nuclear_power`'s leverage *resistance* is not offset, only its generation (a burden on influence, not on standing firm);
   - the civil-defence and renunciation-prestige modifiers are modifiers only, so a revolution's winner loses them (the renunciation itself is rebuilt from `nd_renounced_locked`);
   - the taboo is global, with no regional or ideological layer.
4. **Expected curves:** under `#### Expected curves`, the simulator's table from Step 2, then the line: `Re-run with python3 scripts/analysis/nuclear_taboo_sim.py after any retune; every constant is read from nuclear_taboo_values.txt.`
5. **In-game checklist:** under `#### In-game checklist`, numbered from 1:
   1. A new game reaching its first warhead logs `TE_TABOO: born`, and the panel shows 20, Normalised.
   2. An existing save already in the nuclear age wakes at its target, not 20: `TE_TABOO: seeded`.
   3. Every country's journal shows Nuclear Weapons after the first warhead, and the monthly pulse does not visibly slow the game (compare month-ticks before and after the first warhead).
   4. The status line opens with the taboo sentence, and its number matches the panel.
   5. The breakdown tooltip's lines add up to the target line.
   6. A strategic first strike's confirmation names the infamy and relations; the strike charges exactly them. A licensed retaliation says no infamy and charges none.
   7. `TE_TABOO:` after a strike shows the shock, and the target falls by the ledger and the halved tradition.
   8. The prestige tooltip lists The Burden of the Bomb at the burden the panel shows; restraint groups' At Home terms show "the arsenal itself".
   9. The ceiling stepper lowers the ceiling, warheads retire monthly, the programme reads "held", and lifting the ceiling releases it the same click.
   10. Dismantling a small arsenal completes, fires "The Last Warhead", applies the prestige and relations, and the entry stays active with the Resume decision shown.
   11. `event te_debug_nuclear.3` option b (85) then d (step) fires the Strong band event to every country, once; running d again does not fire it again.
   12. An AI great power in a high-taboo world with no rival trims its arsenal to a ceiling within a year.
   13. Civil defence halves the "Enemy nuclear arsenal" war-support line.
   14. An eroding band event offers an unarmed country with an amicable armed neighbour "Seek the shelter of a friendly nuclear power" (the option's `relations:root >= relations_threshold:amicable` is a form the mod had not used in a trigger before; if the option never appears, suspect the syntax before concluding no friendly power exists).
   15. A treaty-disarmed or renounced country's weekly pulse logs no `remove_modifier` error for `nuclear_power`.

- [ ] **Step 4: `docs/systems/mod_systems.md`**

In the Nuclear Weapons section:

(a) Replace the paragraph that begins `**Disarmament deactivates the entry**` with:

```
**Disarmament no longer deactivates the entry once the nuclear taboo exists.** From the world's first warhead the entry is active for every non-decentralized country (`nuclear_program_entry_applies`), so everything a disarmed country must shed — posture modifiers, upkeep, the taboo's possession cost, interest-group bands — comes off because it is not armed, from the entry's own pulses (`nd_monthly_update`'s unarmed branch, `nd_apply_posture_modifiers`, `nd_taboo_refresh_possession`). Before the first warhead, and with the rule off, `can_deactivate = yes` still lets a disarmed country's entry close. The `nuclear_disarmament` article still zeroes the variables itself in `on_entry_into_force`, and the status line still says "our programme has been dismantled".
```

(b) After the **Loose warheads** paragraph, add:

```
**The nuclear taboo** (`nuclear_taboo_*` files; design `docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md`, shipped `nuclear_crisis_design.md` §0.11). One world score, `global_var:nd_taboo` (0–100), born at 20 with the first warhead and moved monthly toward a target of named parts:
- **base** 20;
- **tradition** of non-use, +1 a year, capped at 35;
- the armed countries' **postures**, a rank-weighted average, ±10;
- **restraint**: pledges and former nuclear states, up to +15;
- a decaying **ledger** of acts, −30…+10.

Drift alone tops out at 55.

The step runs once for the world from a global `on_monthly_pulse`, never the UN's. Uses shock it at once. Threats, doctrines, pledges, stand-downs, renunciations and terror write the ledger, all through the writers in `nuclear_taboo_effects.txt`.

It scales:
- use infamy (taboo; 0.4 × taboo tactical) and world relations;
- ultimatum and offensive-doctrine infamy (0.1 × taboo);
- a twelfth yield-pressure part (`nd_yp_taboo`);
- a possession burden (taboo factor × arsenal factor) that costs prestige and leverage (`nd_taboo_possession_cost`, on the entry) and restraint groups' approval.

The AI reads it for use, coercion, doctrine, arsenal size and proliferation.

Countries can hold the arsenal to a ceiling or dismantle it (posture ops 60–64), and a renounced country can resume (a decision; re-arming books a breakout). Crossing 30/50/70/90 fires `nuclear_taboo.1`–`.8` to every country, with country-local options. The per-country half (possession, exits, history) runs from the entry's monthly pulse as `nd_taboo_country_monthly`, with ROOT = the country. The nuclear-powers leaderboard now updates once a month from the world's step.
```

- [ ] **Step 5: `docs/systems/journal_entry_systems.md`** (CRLF, bytes-level)

Run exactly (it adds one paragraph to each widget section, with CRLF endings):

```bash
python3 - <<'EOF'
p = "docs/systems/journal_entry_systems.md"
b = open(p, "rb").read()
anchor1 = b"### Nuclear Deterrence Widget (journal-entry widget)\r\n"
add1 = (b"**The nuclear taboo panel** (since 2026-09-26) opens `widget_je_nuclear_balance`, open by default and drawn from the first warhead on: the score and band, where it is heading, "
        b"a breakdown of the target (`nd_taboo_breakdown_sgui`, from the monthly snapshots), what a first use, a battlefield use and a public ultimatum cost now, "
        b"the possession burden while armed, when a weapon was last used, and a collapsed history chart of score and target (`te_hist_v_nd_taboo`, `te_hist_v_nd_taboo_tgt`). "
        b"Display handlers `nd_taboo_exists_sgui` and `nd_taboo_breakdown_sgui` in `nuclear_program_sguis.txt`.\r\n\r\n")
assert b.count(anchor1) == 1
b = b.replace(anchor1, add1 + anchor1)
anchor2 = b"Op table (repeated in the sgui header and the `.gui` header"
add2 = (b"**Arsenal rows** (the nuclear taboo, since 2026-09-26), at the foot of Capabilities: the arsenal's state (a ceiling, being dismantled, or free), "
        b"the ceiling stepper (ops 60/61) with a hint of the size at which restraint groups would ease, Lift the ceiling (62), Dismantle the arsenal (63) and Halt the dismantling (64).\r\n\r\n")
assert b.count(anchor2) == 1
b = b.replace(anchor2, add2 + anchor2)
open(p, "wb").write(b)
EOF
test "$(grep -c $'\r$' docs/systems/journal_entry_systems.md)" = "$(wc -l < docs/systems/journal_entry_systems.md)" && echo CRLF-OK
```

Expected: `CRLF-OK`.

- [ ] **Step 6: `docs/README.md` and `scripting_best_practices.md`**

In `docs/README.md`, in the `systems/nuclear_crisis_design.md` row's description, after "alternate-history AI;", add: " the nuclear taboo (§0.11);".

Append to `docs/guides/scripting_best_practices.md`, under its journal-entry section (search for `## JE Auto-Activation`; add after that section's last paragraph):

```
**Making an entry active for every country turns its per-country pulse sweeps quadratic.** A pulse effect that iterates every country (`ordered_country`, `every_country`) and runs from each active country's pulse costs n² once n is every country. `update_nuclear_powers_ranking` ran from `je_nuclear_program`'s weekly pulse while ~10 countries held the entry. When the nuclear taboo made the entry every country's (2026-09-26), it moved to the world's monthly step, a global `on_monthly_pulse`. Before widening an entry's `possible`, move every world-level sweep in its pulses to a global pulse, and check that each remaining pulse effect is a cheap no-op for the new members.
```

- [ ] **Step 7: Phase 1 verification — the game-independent checks**

Run from the worktree:

```bash
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
python3 -m compileall -q .
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs python3 -m unittest 2>&1 | tail -5
ruff check .
git diff --name-only origin/main -- ':(glob)**/*.txt' ':(glob)**/*.gui' | grep -v -e '^common/ideologies/modified.txt$' -e '^common/interest_groups/00_' -e '^common/scripted_effects/extra_law_consistency_generated.txt$' | xargs python3 scripts/format_paradox_tabs.py --check
python3 scripts/analysis/check_localization_files.py
python3 scripts/analysis/check_post_load_rosters.py
python3 attitude_key_audit.py
python3 kill_character_audit.py --check
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image treaty_leverage_side event_context silent_variable prev_scope container_timed_variable je_immediate_reset empty_effect; do python3 ${a}_audit.py --strict >/dev/null || echo "FAILED: $a"; done
grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" test_nuclear_taboo.py scripts/analysis/nuclear_taboo_sim.py organize_loc.py
```

Expected: `OK` from unittest, ruff clean, no tab-check failures, no `FAILED:` lines, and no f-string hits.

- [ ] **Step 8: Phase 1 verification — reload the worktree on a second server**

```bash
cp /home/jakef/src/Vic3TimelineExtended/paths.local.json .
```

Then start the server as a **background** task (the tool's `run_in_background`, not `&`), from the worktree:

```bash
VIC3_SKIP_DIGESTS_FETCH=1 /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -c "import mod_state_server as m; m.PORT=8951; m.main()"
```

When `curl -s http://127.0.0.1:8951/status` reports `"ready": true`:

```bash
curl -s -X POST http://127.0.0.1:8951/reload | python3 -c "import json,sys; r=json.load(sys.stdin); print(json.dumps({k: r.get(k) for k in ('warnings','generators_wrote_files','reparsed_after_generators','parse_failures')}, indent=1))"
grep -n "nd_taboo\|nuclear_taboo" docs/engine/loc_coverage_report.md docs/engine/modifier_visibility_report.md docs/engine/effect_trigger_validity_report.md docs/engine/script_loc_reference_report.md docs/engine/localization_accessor_report.md docs/engine/concept_reference_report.md docs/engine/event_magnitude_report.md | head -40
```

Every warning that names a `nd_taboo`, `nuclear_taboo`, `nd_yp_taboo` or `nd_ig_term_possession` key, effect or file is this branch's to fix before continuing. Warnings about other systems are pre-existing; note any that appear new.

Stop the server by its PID file (see `docs/guides/python_tools.md` § "Starting the Server"; never `pkill -f`). Then sort `git status`:
- `docs/engine/*` is regenerated output: `git checkout -- docs/engine/`;
- `localization/` moves from `organize_loc` (the new keys filed) are this branch's: stage them;
- anything else under `common/` that the branch did not cause is vanilla drift: discard it.

- [ ] **Step 9: Commit**

```bash
git add common/scripted_effects/nuclear_taboo_effects.txt events/te_debug_nuclear_events.txt localization/ docs/systems/nuclear_crisis_design.md docs/systems/mod_systems.md docs/systems/journal_entry_systems.md docs/README.md docs/guides/scripting_best_practices.md
git status --short
git commit -m "Nuclear taboo: console harness, docs, and the phase 1 checklist

<attribution lines>"
```

---

## Phase 2

Start Phase 2 only after Phase 1's Task 11 is committed and its checks are clean.

### Task 12: The arms-control article, and walking out

**Files:**
- Create: `common/treaty_articles/117_nuclear_arms_limitation.txt`
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING, the restraint part, the effective ceiling, the article's AI values)
- Modify: `common/scripted_triggers/nuclear_taboo_triggers.txt` (`nd_taboo_has_ceiling`; `nd_taboo_programme_should_be_held`)
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_refresh_treaty_ceiling`; `nd_taboo_country_monthly`)
- Modify: `localization/english/te_concepts_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`TestArmsControl`)

**Interfaces:**
- Consumes: `nd_taboo_ledger_add_weighted`, `nd_taboo_rank_weight`, `nd_taboo_retire_step`, `nd_taboo_refresh_held`.
- Produces:
  - variables `nd_treaty_ceiling` and `nd_treaty_ceiling_partner` (country);
  - values `nd_taboo_effective_ceiling_value` (0 = none) and `nd_taboo_arms_control_weight_value`;
  - trigger `nd_taboo_has_ceiling`;
  - the article `nuclear_arms_limitation` (mutual, `quantity` input = the most warheads either party may hold).

- [ ] **Step 1: Write the failing tests** (append)

```python
ARMS_ARTICLE = ROOT / "common/treaty_articles/117_nuclear_arms_limitation.txt"


class TestArmsControl(unittest.TestCase):
    def setUp(self):
        self.taboo = strip_comments(read(TABOO_EFFECTS))
        self.values = strip_comments(read(TABOO_VALUES))

    def test_article_shape(self):
        self.assertTrue(ARMS_ARTICLE.read_bytes().startswith(b"\xef\xbb\xbf"))
        body = block(strip_comments(read(ARMS_ARTICLE)), "nuclear_arms_limitation")
        self.assertIn("kind = mutual", body)
        self.assertRegex(body, r"required_inputs = \{\s*quantity\s*\}")
        self.assertNotIn("country_treaty_leverage_generation_add", body)
        self.assertIn("quantity_input_value", body)

    def test_only_a_treaty_can_make_an_exit_free(self):
        body = block(self.taboo, "nd_taboo_refresh_treaty_ceiling")
        self.assertIn("has_type = nuclear_arms_limitation", body)
        self.assertIn("scope:nd_tb_article.input_quantity", body)
        self.assertIn("var:nd_tb_new_ceiling > var:nd_treaty_ceiling", body)
        self.assertIn("exists = var:nd_treaty_ceiling_partner", body)
        self.assertIn("POINTS = nd_taboo_ledger_walkout", body)
        # The unilateral ceiling never shields a walk-out.
        self.assertNotIn("nd_warhead_ceiling", body)

    def test_the_lowest_ceiling_binds(self):
        eff = block(self.values, "nd_taboo_effective_ceiling_value")
        self.assertIn("var:nd_treaty_ceiling < var:nd_warhead_ceiling", eff)
        held = block(strip_comments(read(TABOO_TRIGGERS)), "nd_taboo_programme_should_be_held")
        self.assertIn("nd_stockpile >= nd_taboo_effective_ceiling_value", held)
        self.assertIn("subtract = nd_taboo_effective_ceiling_value", block(self.values, "nd_taboo_retire_this_month_value"))
        monthly = block(self.taboo, "nd_taboo_country_monthly")
        self.assertLess(monthly.index("nd_taboo_refresh_treaty_ceiling = yes"), monthly.index("nd_taboo_refresh_held = yes"))
        self.assertIn("nd_stockpile > nd_taboo_effective_ceiling_value", monthly)

    def test_bound_countries_count_once_in_restraint(self):
        self.assertIn("has_variable = nd_treaty_ceiling", block(self.values, "nd_taboo_arms_control_weight_value"))
        self.assertIn("value = nd_taboo_arms_control_weight_value", block(self.values, "nd_taboo_part_restraint_value"))

    def test_article_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nuclear_arms_limitation", "nuclear_arms_limitation_desc",
                    "nuclear_arms_limitation_effects_desc", "nuclear_arms_limitation_article_short_desc",
                    "nd_taboo_arms_party_tt", "nd_taboo_arms_quantity_tt", "nd_taboo_ai_arms_base",
                    "nd_taboo_ai_arms_militarist"):
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo.TestArmsControl -v`
Expected: errors (the article file is missing; `nd_taboo_refresh_treaty_ceiling not found`).

- [ ] **Step 3: Values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_arms_control_point = 2
nd_taboo_ledger_walkout = -1
nd_taboo_arms_quantity_max = 500
nd_taboo_arms_ai_share = 0.75
nd_taboo_arms_ai_base = -25
nd_taboo_arms_ai_burden_weight = 50
nd_taboo_arms_ai_taboo_weight = 0.5
nd_taboo_arms_ai_militarist = -50
```

Add after `nd_taboo_renounced_weight_value`:

```
# Countries an arms-limitation treaty binds (nd_treaty_ceiling), rank-weighted,
# each once however many treaties it has.
nd_taboo_arms_control_weight_value = {
	value = 0
	every_country = {
		limit = { has_variable = nd_treaty_ceiling }
		add = nd_taboo_rank_weight
	}
}
```

In `nd_taboo_part_restraint_value`, add a third term before `min = 0`:

```
	add = {
		value = nd_taboo_arms_control_weight_value
		multiply = nd_taboo_arms_control_point
	}
```

In the EXITS section, add:

```
# The ceiling that binds: the lower of our own (nd_warhead_ceiling) and the
# lowest a treaty sets us (nd_treaty_ceiling); 0 when neither exists.
nd_taboo_effective_ceiling_value = {
	value = 0
	if = {
		limit = { has_variable = nd_warhead_ceiling }
		value = var:nd_warhead_ceiling
	}
	if = {
		limit = {
			has_variable = nd_treaty_ceiling
			OR = {
				NOT = { has_variable = nd_warhead_ceiling }
				var:nd_treaty_ceiling < var:nd_warhead_ceiling
			}
		}
		value = var:nd_treaty_ceiling
	}
}
```

Replace `nd_taboo_retire_this_month_value` with:

```
# A tenth of the excess over the ceiling that binds, at least one.
nd_taboo_retire_this_month_value = {
	value = 0
	if = {
		limit = {
			nd_taboo_has_ceiling = yes
			nd_stockpile > nd_taboo_effective_ceiling_value
		}
		value = nd_stockpile
		subtract = nd_taboo_effective_ceiling_value
		multiply = nd_taboo_retire_share
		ceiling = yes
		min = 1
	}
}
```

Add the article's AI values:

```
# nuclear_arms_limitation's AI (spec §7.1). Scope: the evaluating country.
nd_taboo_ai_arms_burden_value = {
	value = nd_taboo_burden_value
	multiply = nd_taboo_arms_ai_burden_weight
	round = yes
}

nd_taboo_ai_arms_taboo_value = {
	value = nd_taboo_value
	subtract = nd_taboo_line_established
	multiply = nd_taboo_arms_ai_taboo_weight
	min = 0
	round = yes
}
```

- [ ] **Step 4: Triggers** (`nuclear_taboo_triggers.txt`)

Add:

```
# Our own ceiling or a treaty's binds us.
nd_taboo_has_ceiling = {
	OR = {
		has_variable = nd_warhead_ceiling
		has_variable = nd_treaty_ceiling
	}
}
```

Replace `nd_taboo_programme_should_be_held` with:

```
# The programme builds nothing while dismantling, or at or above the ceiling
# that binds us — our own or a treaty's (nd_taboo_programme_held carries the
# programme-pause flag).
nd_taboo_programme_should_be_held = {
	OR = {
		nd_taboo_is_dismantling = yes
		AND = {
			nd_taboo_has_ceiling = yes
			nd_stockpile >= nd_taboo_effective_ceiling_value
		}
	}
}
```

- [ ] **Step 5: The treaty ceiling and walk-outs** (`nuclear_taboo_effects.txt`, EXITS section)

```
# The lowest ceiling an arms-limitation treaty in force sets us, and the
# partner holding it (spec §7.1). Leaving costs only when this rises or
# vanishes — our treaty obligations loosened — and not when the partner no
# longer exists (a lapse nobody chose). The unilateral ceiling never enters:
# only another treaty can make an exit free, so a country cannot hide behind a
# ceiling of its own, leave, then lift it. Both parties' ceilings rise when a
# treaty ends, so both are booked: the regime's end erodes the norm whoever
# ended it. Scope: country (nd_taboo_country_monthly).
nd_taboo_refresh_treaty_ceiling = {
	save_scope_as = nd_tb_self
	set_variable = { name = nd_tb_new_ceiling value = -1 }
	every_scope_treaty = {
		every_scope_article = {
			limit = {
				has_type = nuclear_arms_limitation
				exists = input_quantity
			}
			save_scope_as = nd_tb_article
			scope:nd_tb_self = {
				if = {
					limit = {
						OR = {
							var:nd_tb_new_ceiling < 0
							var:nd_tb_new_ceiling > scope:nd_tb_article.input_quantity
						}
					}
					set_variable = { name = nd_tb_new_ceiling value = scope:nd_tb_article.input_quantity }
					scope:nd_tb_article = {
						first_country = { save_scope_as = nd_tb_first }
						second_country = { save_scope_as = nd_tb_second }
					}
					if = {
						limit = {
							scope:nd_tb_first = { this = scope:nd_tb_self }
						}
						set_variable = { name = nd_tb_new_partner value = scope:nd_tb_second }
					}
					else = {
						set_variable = { name = nd_tb_new_partner value = scope:nd_tb_first }
					}
				}
			}
		}
	}
	if = {
		limit = {
			has_variable = nd_treaty_ceiling
			OR = {
				var:nd_tb_new_ceiling < 0
				var:nd_tb_new_ceiling > var:nd_treaty_ceiling
			}
			exists = var:nd_treaty_ceiling_partner
		}
		nd_taboo_ledger_add_weighted = { POINTS = nd_taboo_ledger_walkout }
		debug_log = "TE_TABOO: an arms-control treaty was left"
	}
	if = {
		limit = { var:nd_tb_new_ceiling >= 0 }
		set_variable = { name = nd_treaty_ceiling value = var:nd_tb_new_ceiling }
		set_variable = { name = nd_treaty_ceiling_partner value = var:nd_tb_new_partner }
	}
	else = {
		if = {
			limit = { has_variable = nd_treaty_ceiling }
			remove_variable = nd_treaty_ceiling
		}
		if = {
			limit = { has_variable = nd_treaty_ceiling_partner }
			remove_variable = nd_treaty_ceiling_partner
		}
	}
	remove_variable = nd_tb_new_ceiling
	if = {
		limit = { has_variable = nd_tb_new_partner }
		remove_variable = nd_tb_new_partner
	}
}
```

In `nd_taboo_country_monthly`, replace

```
		# ---- dismantling, or warheads above the ceiling ----
		if = {
			limit = { nd_taboo_is_dismantling = yes }
			nd_taboo_dismantle_step = yes
		}
		else_if = {
			limit = {
				has_variable = nd_warhead_ceiling
				nd_stockpile > var:nd_warhead_ceiling
			}
			nd_taboo_retire_step = yes
		}
```

with

```
		# ---- the ceiling an arms-control treaty sets us, and walk-outs ----
		nd_taboo_refresh_treaty_ceiling = yes
		# ---- dismantling, or warheads above the ceiling that binds ----
		if = {
			limit = { nd_taboo_is_dismantling = yes }
			nd_taboo_dismantle_step = yes
		}
		else_if = {
			limit = {
				nd_taboo_has_ceiling = yes
				nd_stockpile > nd_taboo_effective_ceiling_value
			}
			nd_taboo_retire_step = yes
		}
```

- [ ] **Step 6: Create `common/treaty_articles/117_nuclear_arms_limitation.txt`** (BOM first)

```
﻿# ============================================================================
# TREATY ARTICLE: nuclear_arms_limitation (the nuclear taboo, phase 2)
# ============================================================================
# Design: docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md §7.1.
# Mutual: while it is in force each party holds at most `quantity` warheads.
# The ceiling is read monthly by nd_taboo_refresh_treaty_ceiling
# (nuclear_taboo_effects.txt): warheads above it retire, a tenth of the excess
# a month, and the programme is held at it, so no breach is possible. Leaving
# it books a walk-out against the taboo unless another treaty holds the same
# or a lower ceiling. No leverage either way: it binds both alike.
# ============================================================================
nuclear_arms_limitation = {
	icon = "gfx/interface/icons/diplomatic_treaties_articles_icons/offer_embassy.dds"
	kind = mutual
	cost = 50

	flags = {
		can_be_renegotiated
	}

	usage_limit = once_per_treaty

	required_inputs = {
		quantity
	}

	quantity_min_value = {
		value = 1
	}
	quantity_max_value = {
		value = nd_taboo_arms_quantity_max
	}

	visible = {
		has_game_rule = nuclear_weapons_enabled
		has_technology_researched = nuclear_weapons
	}

	possible = {
		has_game_rule = nuclear_weapons_enabled
		custom_tooltip = {
			text = nd_taboo_arms_party_tt
			OR = {
				nd_is_armed = yes
				nuclear_program_has_programme = yes
			}
		}
	}

	requirement_to_maintain = {
		trigger = {
			custom_tooltip = {
				text = nd_taboo_arms_quantity_tt
				scope:article ?= {
					exists = input_quantity
					input_quantity > 0
				}
			}
		}
	}

	ai = {
		treaty_categories = { military }
		article_ai_usage = { offer request }

		# Armed, facing an armed partner, in a world that fears the bomb or
		# where our arsenal weighs on us.
		evaluation_chance = {
			value = 0
			if = {
				limit = {
					nd_is_armed = yes
					exists = scope:other_country
					scope:other_country = { nd_is_armed = yes }
					OR = {
						nd_taboo_value >= nd_taboo_line_established
						nd_taboo_burden_value > 0
					}
				}
				add = 0.1
			}
		}

		# Three quarters of the larger arsenal: it binds the larger party
		# first, and leaves parity within reach.
		quantity_input_value = {
			value = var:nuclear_weapon_stockpile
			if = {
				limit = {
					exists = scope:other_country
					scope:other_country.var:nuclear_weapon_stockpile > var:nuclear_weapon_stockpile
				}
				value = scope:other_country.var:nuclear_weapon_stockpile
			}
			multiply = nd_taboo_arms_ai_share
			ceiling = yes
			min = 1
		}

		inherent_accept_score = {
			value = 0
			add = {
				desc = "nd_taboo_ai_arms_base"
				value = nd_taboo_arms_ai_base
			}
			if = {
				limit = { nd_taboo_burden_value > 0 }
				add = {
					desc = "nd_taboo_ai_accept_burden"
					value = nd_taboo_ai_arms_burden_value
				}
			}
			if = {
				limit = { nd_taboo_value > nd_taboo_line_established }
				add = {
					desc = "nd_taboo_ai_accept_taboo"
					value = nd_taboo_ai_arms_taboo_value
				}
			}
			if = {
				limit = { nd_regime_is_militarist = yes }
				add = {
					desc = "nd_taboo_ai_arms_militarist"
					value = nd_taboo_arms_ai_militarist
				}
			}
		}
	}
}
```

- [ ] **Step 7: Loc**

`te_concepts_l_english.yml` (next to `nuclear_security_assistance`):

```
 nuclear_arms_limitation:0 "Nuclear Arms Limitation"
 nuclear_arms_limitation_article_short_desc:0 "Both parties hold their nuclear arsenals to an agreed ceiling"
 nuclear_arms_limitation_desc:0 "A ceiling on nuclear arsenals, the same for both parties, verified and kept."
 nuclear_arms_limitation_effects_desc:0 "• Neither party holds more warheads than the agreed ceiling: those above it are taken apart, a tenth of the excess a month, and neither programme builds past it.\n• Every country such a treaty binds strengthens the nuclear taboo.\n• Leaving it weakens the taboo, unless another treaty already holds the party to the same ceiling or a lower one."
```

`te_miscellaneous_l_english.yml`:

```
 nd_taboo_ai_arms_base:0 "An arms-control commitment"
 nd_taboo_ai_arms_militarist:0 "Our government would never accept limits on the bomb"
 nd_taboo_arms_party_tt:0 "We hold nuclear weapons or run a programme to build them"
 nd_taboo_arms_quantity_tt:0 "A ceiling of at least one warhead is set"
```

- [ ] **Step 8: Format, test, audit, commit**

```bash
python3 scripts/format_paradox_tabs.py common/treaty_articles/117_nuclear_arms_limitation.txt common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence
python3 treaty_leverage_side_audit.py --strict && python3 duplicate_key_audit.py --strict && python3 prev_scope_audit.py --strict
git add test_nuclear_taboo.py common/treaty_articles/117_nuclear_arms_limitation.txt common/script_values/nuclear_taboo_values.txt common/scripted_triggers/nuclear_taboo_triggers.txt common/scripted_effects/nuclear_taboo_effects.txt localization/english/te_concepts_l_english.yml localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: an arms-control article; leaving it costs only when it loosens the obligations

<attribution lines>"
```

---

### Task 13: The UN's part and the Assembly's verdict

**Files:**
- Modify: `common/script_values/nuclear_taboo_values.txt` (TUNING, `nd_taboo_part_un_value`, the target sum, `nd_disp_tb_un`)
- Modify: `common/scripted_effects/nuclear_taboo_effects.txt` (snapshot, the log line, `nd_taboo_verdict`)
- Modify: `common/scripted_guis/nuclear_program_sguis.txt` (breakdown line)
- Modify: `common/scripted_effects/un_docket_effects.txt` (the nuclear take-up)
- Modify: `events/un_vote_events.txt` (`un_vote.2`'s option: three branches)
- Modify: `scripts/analysis/nuclear_taboo_sim.py` (a cooperative scenario)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_taboo.py` (`PARTS`, `TestUN`)

**Interfaces:**
- Consumes: `global_var:un_founded`, `global_var:un_authority`, `global_var:un_agency_iaea`, `global_var:un_agency_cppnm`, `scope:un_vote_target`, `scope:un_resolution`.
- Produces:
  - part `nd_tb_un` (0…+15);
  - effect `nd_taboo_verdict = { PASSED = yes|no }` (any scope; prints its tooltip);
  - variable `nd_taboo_verdict_pending` (country, 730 days).

- [ ] **Step 1: Write the failing tests**

Change `PARTS` in `test_nuclear_taboo.py` to `["base", "tradition", "postures", "restraint", "un", "ledger"]`, then append:

```python
UN_DOCKET = ROOT / "common/scripted_effects/un_docket_effects.txt"
UN_VOTE_EVENTS = ROOT / "events/un_vote_events.txt"


class TestUN(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.taboo = strip_comments(read(TABOO_EFFECTS))

    def test_un_part_needs_a_un_and_reads_the_two_conventions(self):
        body = block(self.values, "nd_taboo_part_un_value")
        for needle in ("has_global_variable = un_founded", "has_global_variable = un_agency_iaea",
                       "has_global_variable = un_agency_cppnm", "global_var:un_authority",
                       "max = nd_taboo_un_cap"):
            self.assertIn(needle, body)

    def test_verdict_waits_on_a_nuclear_grievance(self):
        docket = strip_comments(read(UN_DOCKET))
        i = docket.index("un_docket_take_up_grievance = { KIND = nuclear CAUSE = 1 FOUND = scope:un_dkt_found_nuclear }")
        self.assertIn("name = nd_taboo_verdict_pending value = 1 days = 730", docket[i:i + 400])

    def test_every_condemnation_outcome_books_the_verdict(self):
        option = block(strip_comments(read(UN_VOTE_EVENTS)), "un_vote.2")
        self.assertEqual(option.count("nd_taboo_verdict = { PASSED = yes }"), 1)
        self.assertEqual(option.count("nd_taboo_verdict = { PASSED = no }"), 2)
        self.assertEqual(option.count("remove_variable = nd_taboo_verdict_pending"), 3)

    def test_verdict_prints_what_it_does(self):
        body = block(self.taboo, "nd_taboo_verdict")
        self.assertEqual(body.count("custom_tooltip = {"), 2)
        self.assertIn("text = nd_taboo_tt_verdict_passed", body)
        self.assertIn("text = nd_taboo_tt_verdict_failed", body)

    def test_cooperation_reaches_past_drift(self):
        import nuclear_taboo_sim as sim
        c = sim.load_constants(TABOO_VALUES)
        score, target = sim.simulate(sim.SCENARIOS["cooperative"], c, years=100)[-1]
        self.assertGreater(target, 80)

    def test_un_keys_have_loc(self):
        keys = loc_keys()
        for key in ("nd_taboo_bd_un", "nd_taboo_tt_verdict_passed", "nd_taboo_tt_verdict_failed"):
            self.assertIn(key, keys, key)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest test_nuclear_taboo -v 2>&1 | tail -40`
Expected: `TestScoreCore` (the snapshot and target need `un`), `TestPanel` (the breakdown needs `un`) and `TestUN` fail.

- [ ] **Step 3: Values** (`nuclear_taboo_values.txt`)

Append to TUNING:

```
nd_taboo_un_npt_weight = 8
nd_taboo_un_cppnm_weight = 4
nd_taboo_un_cap = 15
nd_taboo_ledger_verdict_passed = 3
nd_taboo_shock_verdict_passed = 2
nd_taboo_ledger_verdict_failed = -3
```

After `nd_taboo_part_restraint_value`, add:

```
# The UN's conventions (spec §7.2): the NPT (the IAEA) and the Physical
# Protection convention (CPPNM), each in proportion to UN authority. 0 with no
# UN: the taboo never needs one.
nd_taboo_part_un_value = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_founded
			has_global_variable = un_authority
		}
		if = {
			limit = { has_global_variable = un_agency_iaea }
			add = {
				value = global_var:un_authority
				divide = 100
				multiply = nd_taboo_un_npt_weight
			}
		}
		if = {
			limit = { has_global_variable = un_agency_cppnm }
			add = {
				value = global_var:un_authority
				divide = 100
				multiply = nd_taboo_un_cppnm_weight
			}
		}
	}
	min = 0
	max = nd_taboo_un_cap
}
```

In `nd_taboo_target_sum`, replace `add = global_var:nd_tb_restraint` with

```
	add = global_var:nd_tb_restraint
	add = global_var:nd_tb_un
```

In DISPLAY, add:

```
nd_disp_tb_un = {
	value = 0
	if = {
		limit = { has_global_variable = nd_tb_un }
		value = global_var:nd_tb_un
	}
}
```

Update the file header's parts table with the line `#   un           0 .. +15    the NPT and CPPNM in force, x UN authority (phase 2)`.

- [ ] **Step 4: Effects** (`nuclear_taboo_effects.txt`)

In `nd_taboo_snapshot`, replace

```
	set_global_variable = { name = nd_tb_restraint value = nd_taboo_part_restraint_value }
```

with

```
	set_global_variable = { name = nd_tb_restraint value = nd_taboo_part_restraint_value }
	set_global_variable = { name = nd_tb_un value = nd_taboo_part_un_value }
```

In `nd_taboo_monthly_update`'s `debug_log` string, insert ` un [SCOPE.ScriptValue('nd_disp_tb_un')|1]` after the restraint figure.

Append in the WRITERS section:

```
# The Assembly's verdict on a nuclear use (spec §7.3), from un_vote.2's option
# on a condemnation of a country the docket took up for a nuclear strike
# (nd_taboo_verdict_pending). PASSED = yes: the world said no. PASSED = no —
# failed, or vetoed down to a rebuke: impunity. Scope: any.
nd_taboo_verdict = {
	if = {
		limit = { always = $PASSED$ }
		custom_tooltip = {
			text = nd_taboo_tt_verdict_passed
			nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_verdict_passed }
			nd_taboo_shock = { POINTS = nd_taboo_shock_verdict_passed }
		}
	}
	else = {
		custom_tooltip = {
			text = nd_taboo_tt_verdict_failed
			nd_taboo_ledger_add = { POINTS = nd_taboo_ledger_verdict_failed }
		}
	}
}
```

- [ ] **Step 5: The breakdown line** (`nuclear_program_sguis.txt`, `nd_taboo_breakdown_sgui`)

Replace `custom_tooltip_no_bullet = nd_taboo_bd_restraint` with

```
			custom_tooltip_no_bullet = nd_taboo_bd_restraint
			custom_tooltip_no_bullet = nd_taboo_bd_un
```

- [ ] **Step 6: The docket marks the culprit** (`un_docket_effects.txt`)

Replace

```
		un_docket_take_up_grievance = { KIND = nuclear CAUSE = 1 FOUND = scope:un_dkt_found_nuclear }
```

with

```
		un_docket_take_up_grievance = { KIND = nuclear CAUSE = 1 FOUND = scope:un_dkt_found_nuclear }
		# The nuclear taboo awaits the Assembly's verdict on this use
		# (un_vote.2 books it, nd_taboo_verdict). Two years: an appeal waits
		# for a free floor, and the vote itself takes one.
		scope:un_dkt_found_nuclear ?= {
			set_variable = { name = nd_taboo_verdict_pending value = 1 days = 730 }
		}
```

- [ ] **Step 7: The three outcomes** (`un_vote_events.txt`, `un_vote.2`'s option)

Passed, binding: replace

```
				custom_tooltip = un_vote_condemn_passed_tt
				un_ledger_entry = { PILLAR = credibility POINTS = 1 REASON = 1 }
```

with

```
				custom_tooltip = un_vote_condemn_passed_tt
				un_ledger_entry = { PILLAR = credibility POINTS = 1 REASON = 1 }
				# The nuclear taboo: condemning a nuclear use reaffirms it.
				if = {
					limit = { scope:un_vote_target ?= { has_variable = nd_taboo_verdict_pending } }
					nd_taboo_verdict = { PASSED = yes }
					scope:un_vote_target = { remove_variable = nd_taboo_verdict_pending }
				}
```

Vetoed down to a rebuke: replace

```
				custom_tooltip = un_vote_condemn_passed_vetoed_tt
				un_ledger_entry = { PILLAR = credibility POINTS = 0.5 REASON = 2 }
```

with

```
				custom_tooltip = un_vote_condemn_passed_vetoed_tt
				un_ledger_entry = { PILLAR = credibility POINTS = 0.5 REASON = 2 }
				# The nuclear taboo: a veto shielding a nuclear use is impunity.
				if = {
					limit = { scope:un_vote_target ?= { has_variable = nd_taboo_verdict_pending } }
					nd_taboo_verdict = { PASSED = no }
					scope:un_vote_target = { remove_variable = nd_taboo_verdict_pending }
				}
```

Failed: replace

```
			custom_tooltip = un_vote_failed_tt
			un_ledger_entry = { PILLAR = credibility POINTS = -1 REASON = 3 }
```

with

```
			custom_tooltip = un_vote_failed_tt
			un_ledger_entry = { PILLAR = credibility POINTS = -1 REASON = 3 }
			# The nuclear taboo: failing to condemn a nuclear use is impunity.
			if = {
				limit = {
					scope:un_resolution ?= { has_tag = un_topic_condemn }
					scope:un_vote_target ?= { has_variable = nd_taboo_verdict_pending }
				}
				nd_taboo_verdict = { PASSED = no }
				scope:un_vote_target = { remove_variable = nd_taboo_verdict_pending }
			}
```

- [ ] **Step 8: The simulator** (`scripts/analysis/nuclear_taboo_sim.py`)

Add to `SCENARIOS`:

```python
    "cooperative": Scenario("No First Use, pledges, arms control, and the NPT and CPPNM at UN authority 80",
                            postures=8, restraint=12, un=9.6),
```

- [ ] **Step 9: Loc** (`te_miscellaneous_l_english.yml`)

```
 nd_taboo_bd_un:0 "#v [GetGlobalVariable('nd_tb_un').GetValue|+1]#!  The United Nations: the Non-Proliferation Treaty and the Physical Protection convention, as strong as the organisation's authority"
 nd_taboo_tt_verdict_failed:0 "The nuclear taboo #R weakens#!: the world let a nuclear use pass"
 nd_taboo_tt_verdict_passed:0 "The nuclear taboo #G strengthens#!: the world said no"
```

- [ ] **Step 10: Format, test, audit, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_guis/nuclear_program_sguis.txt common/scripted_effects/un_docket_effects.txt events/un_vote_events.txt
python3 -m unittest test_nuclear_taboo test_nuclear_deterrence test_un_convention_registry
python3 container_timed_variable_audit.py --strict && python3 silent_variable_audit.py --strict
python3 scripts/analysis/nuclear_taboo_sim.py
git add test_nuclear_taboo.py common/script_values/nuclear_taboo_values.txt common/scripted_effects/nuclear_taboo_effects.txt common/scripted_guis/nuclear_program_sguis.txt common/scripted_effects/un_docket_effects.txt events/un_vote_events.txt scripts/analysis/nuclear_taboo_sim.py localization/english/te_miscellaneous_l_english.yml
git commit -m "Nuclear taboo: the UN's conventions lift it; the Assembly's verdict on a use moves it

<attribution lines>"
```

---

### Task 14: Phase 2 docs and verification

**Files:**
- Modify: `docs/systems/nuclear_crisis_design.md` (§0.11: phase 2, the table, the checklist)
- Modify: `docs/systems/mod_systems.md` (the taboo paragraph)

- [ ] **Step 1: Docs**

In `nuclear_crisis_design.md` §0.11:
- add `common/treaty_articles/117_nuclear_arms_limitation.txt` to the file table;
- replace the simulator table with a fresh run of `python3 scripts/analysis/nuclear_taboo_sim.py`, which now has the cooperative row;
- add these checklist items, continuing the numbering:
  - The arms-control article asks for a ceiling. In force, warheads above it retire and the programme reads "held". Leaving it with no other treaty logs `TE_TABOO: an arms-control treaty was left` for both parties; leaving it while a stricter one stands logs nothing.
  - A nuclear strike taken up by the docket and condemned moves the taboo up (the vote's result tooltip says so); a vetoed or failed condemnation moves it down.
  - The breakdown shows the UN line only once the UN exists and a convention is in force.

In the status banner line added in Task 11, change "Phase 2 (…) and phase 3 (…) follow." to "Phase 2 (arms control, the UN's terms, the Assembly's verdict) is built; phase 3 (a Prohibition convention) follows."

In `mod_systems.md`'s taboo paragraph, add after the band-events sentence:

```
Phase 2: the mutual article `nuclear_arms_limitation` (a `quantity` ceiling for both parties; the lowest treaty ceiling, `nd_treaty_ceiling`, joins the unilateral one, and leaving costs a rank-weighted ledger entry only when a country's lowest treaty ceiling rises and its partner still exists), a UN part (the NPT and CPPNM in force × UN authority, up to +15), and the Assembly's verdict on a condemned nuclear use (`un_vote.2`: passed +3 on the ledger and +2 at once; failed or vetoed −3).
```

- [ ] **Step 2: Verify**

Repeat Task 11's Step 7 (game-independent checks) and Step 8 (the second server's reload). Everything clean, and every warning that names a taboo key resolved.

- [ ] **Step 3: Commit**

```bash
git add docs/systems/nuclear_crisis_design.md docs/systems/mod_systems.md localization/
git status --short
git commit -m "Nuclear taboo: phase 2 docs and checklist

<attribution lines>"
```

- [ ] **Step 4: Hand off**

Push the branch and open a PR against **main** (`gh pr create --base main`). Take the body from:
- the goal above;
- the Deviations list above;
- the owner calls in the spec;
- the §0.11 checklist, as "in-game checks outstanding".

Write the body to a file first (`gh pr create --body-file`). Add the session's PR attribution line.

