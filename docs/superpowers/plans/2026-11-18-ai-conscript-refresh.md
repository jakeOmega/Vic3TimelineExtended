# AI Conscript Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Once a year, clear an AI country's conscription centres that hold conscripts three or more eras out of date, so the AI rebuilds them in its formations' current default types.

**Architecture:** A yearly country on_action runs one scripted effect for AI countries at peace. A combat-unit trigger encodes the stale rule, one OR line per old type, and a test derives the expected lines from the unit-type and technology data. A once-a-game self-check follows the first cleared state for three months.

**Tech Stack:** Paradox script (`common/`), Python `unittest` tests reading `vanilla_parsed/` and the mod's files.

**Spec:** `docs/superpowers/specs/2026-11-18-ai-conscript-refresh-design.md`

## Global Constraints

- AI countries only (`is_ai = yes`), no game rule.
- Peace: `is_at_war = no`, `is_diplomatic_play_committed_participant = no`, `is_diplomatic_play_undecided_participant = no`, no formation `is_mobilized = yes`.
- Stale: three or more eras behind a same-group type the country has unlocked; Irregular Infantry is era 0. Land groups only (infantry, cavalry, artillery, tanks, marines, aircraft).
- A cleared state is not cleared again for five years (`set_variable = { name = te_ai_conscript_cleared years = 5 }`).
- Files: one UTF-8 BOM, tabs.

## Review Focus

1. A state whose conscription centre serves a formation that is mobilizing while the country is still "at peace" (a play's mobilization phase): the play and mobilization gates must both hold.
2. The sampled state changing owner, or its country dying, before the verdict: NO_VERDICT and re-arm, never a false OK or BROKEN.
3. A unit type the mod adds later: the data-derived test fails and names the missing trigger line.
4. The same centre rebuilt stale (the AI's default is itself stale): the five-year mark stops yearly churn, and the self-check says BROKEN (rebuilt stale).
5. A country with no conscription centre, or one with only modern conscripts: the pass does nothing.

---

### Task 1: The stale rule (trigger + data-derived test)

**Files:**
- Create: `common/scripted_triggers/te_ai_conscript_refresh_triggers.txt`
- Test: `test_ai_conscript_refresh.py`

**Interfaces:**
- Produces: `te_ai_conscript_unit_stale` (combat-unit scope: `OR = { AND = { has_unit_type = unit_type:combat_unit_type_<T> owner = { OR = { has_technology_researched = <tech> ... } } } ... }`); `te_ai_conscript_centre_stale` (state scope: has the building, and its `b:building_conscription_center` has `any_combat_unit = { te_ai_conscript_unit_stale = yes }`); `te_ai_conscript_refresh_may` (country scope: the Global Constraints' AI and peace tests).

- [ ] Test `test_stale_rule_matches_the_unit_and_technology_data`: build `{type: set(techs)}` from `vanilla_parsed/common/combat_unit_types.json` overlaid with `common/combat_unit_types/*.txt` (a plain or `REPLACE:` block replaces group and techs; `INJECT:` keeps them) and tech eras from `vanilla_parsed/common/technologies.json` overlaid with `common/technology/technologies/*.txt`; assert it equals the trigger's parsed lines. Plus spot checks: irregular ⊇ {trench_works}, lancers ⊇ {mobile_armor}, shrapnel ⊇ {motorized_artillery}, and trench_infantry not stale at mobile_armor.
- [ ] Test `test_the_pass_runs_only_for_an_ai_at_peace`: the may-trigger's text holds each Global Constraints peace part.
- [ ] Write the triggers; run `python3 -m pytest test_ai_conscript_refresh.py -q` → PASS.

### Task 2: The pass and its wiring (effect + on_action)

**Files:**
- Create: `common/scripted_effects/te_ai_conscript_refresh_effects.txt`, `common/on_actions/te_ai_conscript_refresh_on_actions.txt`
- Test: `test_ai_conscript_refresh.py`

**Interfaces:**
- Consumes: Task 1's three triggers.
- Produces: `te_ai_conscript_refresh_effect` (country scope); on_action `te_ai_conscript_refresh_on_action` under `on_yearly_pulse_country`.

- [ ] Tests: the yearly country pulse runs the on_action with `trigger = { is_ai = yes }`; the effect's `every_scope_state` limit holds `te_ai_conscript_centre_stale = yes` and `NOT = { has_variable = te_ai_conscript_cleared }`, and its body samples the self-check before `remove_building = building_conscription_center`, then sets `te_ai_conscript_cleared` for `years = 5`; the whole body sits inside `te_ai_conscript_refresh_may = yes`.
- [ ] Write the effect and the on_action; tests PASS.

### Task 3: The self-check

**Files:**
- Modify: `common/scripted_effects/te_ai_conscript_refresh_effects.txt` (`te_ai_conscript_refresh_sample`, state scope), `common/on_actions/te_ai_conscript_refresh_on_actions.txt` (`te_ai_conscript_refresh_selfcheck` under `on_monthly_pulse`)
- Create: `common/script_values/te_ai_conscript_refresh_values.txt` (the `_g` readers of the globals for the log line)

**Interfaces:**
- Globals: `te_ai_conscript_sc_state`, `te_ai_conscript_sc_country`, `te_ai_conscript_sc_months`, `te_ai_conscript_sc_before`, `te_ai_conscript_sc_before_stale`, `te_ai_conscript_sc_after`, `te_ai_conscript_sc_after_stale`, `te_ai_conscript_sc_done`.

- [ ] Tests: the sample runs only when neither `te_ai_conscript_sc_state` nor `te_ai_conscript_sc_done` is set, and counts before the removal; the verdict waits three months; OK needs a centre with at least one battalion and none stale; BROKEN prints which (`no_centre` or `stale`); a state gone or changed owner, or a country gone, logs NO_VERDICT and re-arms; a START line comes first.
- [ ] Write it; tests PASS.

### Task 4: Docs and the gate

**Files:**
- Modify: `docs/systems/mod_systems/ai.md` (a `##` section), `docs/systems/mod_systems.md` (its index row), `docs/testing/ai-economy-playtest.md` (the self-check row and the checks).

- [ ] Write them; run `python3 -m pytest test_ai_conscript_refresh.py test_mod_systems_index.py -q`, `.venv/bin/python scripts/preflight.py --changed`; all PASS.
- [ ] Commit, push, open the PR into `main` (body: Closes nothing, Refs #1877; the player-guide line), then a whole-branch break-it review.
