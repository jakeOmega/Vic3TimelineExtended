# Legislated Tax Code: AI Legislation and Release Validation (packages 6–7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI countries legislate their tax code through the player's own commands, and the release carries what the owner needs to validate it in game: a runbook, setup events, a save report, a ledger evidence matrix and the Tax Code player-guide chapter.

**Architecture:**
- **Where the AI runs.** The monthly processor (`te_tax.1`) updates two fiscal streaks for every migrated country. For an AI country with something due, it raises the hidden country event `te_tax.8` on a per-country bucket day.
- **What the step does.** `te_tax.8` runs `te_tax_ai_step`, which manages held packages, promises and the open bill, or starts one bounded template bill. It calls only `te_tax_cmd_*` effects behind their `te_tax_can_*` triggers.
- **Validation tooling.** Package 7 adds read-only tooling (save report, tag index), console setup events and documentation.

**Tech Stack:** Victoria 3 1.14.5 Paradox script, Python 3.11/3.12 `unittest` structural tests, `scripts/generators/gen_tax_code.py`, pandoc + Typst for the guide PDF.

**Spec:** [docs/superpowers/specs/2026-10-03-tax-code-ai-and-release-design.md](../specs/2026-10-03-tax-code-ai-and-release-design.md) (approved by the owner on 2026-10-03, rulings folded in). The parent design remains authoritative: [2026-09-29-legislated-tax-code-design.md](../specs/2026-09-29-legislated-tax-code-design.md). The existing system: `docs/systems/tax_code_schema.md` (read the sections a task names; the file is long). The previous task plan, Tasks 1–17: [2026-10-02-legislated-tax-code-tasks.md](2026-10-02-legislated-tax-code-tasks.md).

**Research** (git-ignored, in the worktree under `.superpowers/sdd/2026-10-02-legislated-tax-code-tasks/research/`):
- `G_ai_legislation.md`: the command surface, fiscal reads, promise delivery, house AI patterns, performance, civil war.
- `H_validation_docs.md`: the save tooling, the 37 deduplicated play-test items, deferred minors, the guide outline with a loc-name table, docs gaps, the probe harness.
- `C_customs_ai_surfaces.md` and `E_politics_obligations.md`, for background.

## Global Constraints

- **Worktree:** `/home/jakef/src/vic3te-tax-code`, branch `claude/legislated-tax-code`, a sparse checkout with no `gfx/`.
  - Never `POST` to the mod state server on :8950, which serves the main checkout.
  - There is no `.venv` in the worktree. Where the venv is needed, use `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.
  - The controller pushes the branch after each completed task (owner, 2026-10-02). Implementers do not push.
- **Rule gate.** Every new hook, event, effect entry point and AI path checks `te_tax_code_on = yes`, written positively. With the rule disabled the game behaves exactly as on `main`. Customs legislation additionally needs `te_tax_customs_on = yes`.
- **Prefix.**
  - `te_tax_ai_` for the AI layer's variables, scripted effects, triggers and values;
  - event `te_tax.8` (the AI step);
  - the console namespace `te_tax_debug`;
  - new generated names keep `te_tax_gen_`.
- **One legal path.** The AI calls `te_tax_cmd_<c>` only inside `if = { limit = { te_tax_can_<c> = <same args> } }`. It never calls a native setter: `add_amendment`, `set_tax_level`, `add_taxed_goods`, `remove_taxed_goods`, `set_*_tariff_level`. `te_tax_sync_collection` stays the only writer.
  - **The one owner-approved exception:** `set_institution_investment_level` enacts a kind-1 promise for an AI country the native AI failed (Task 19).
  - **`is_ai`** may appear only in the AI files (`te_tax_ai_*`, `te_tax.8`), in log gating (`limit = { is_ai = no }` around a `debug_log`) and where it already appears.
- **Canonical-state rule (civil wars).** Every `te_tax_ai_*` token is a schema token:
  - listed in the schema table of `docs/systems/tax_code_schema.md`;
  - initialised by `te_tax_init_country` (guarded writes; schema version 2);
  - never `remove_variable`d;
  - copied at the outbreak by the generated copy;
  - reset by `te_tax_ai_reset_bill_state`, which the outbreak calls on the rebels and which runs at the win repair and at release.
  
  `test_tax_code_civil_war.py` and `test_tax_code_state.py` parse the schema table, so a token missing from it fails them.
- **Vanilla sources.** The installed 1.14.5 game, `/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game`, is authoritative; `~/src/vic3/game` is an older 1.13.9 copy. `vanilla_parsed/` is 1.14.5. Engine docs are in `/home/jakef/src/vic3-engine-docs/1.14.5/docs/`.
- **Engine rules that bite here:**
  - `add_modifier`, amendment changes and other engine-state changes are not visible later in the same effect block; variables are.
  - `multiplier =` resolves against ROOT (force-through needs ROOT = the country, true in `te_tax.8`).
  - `any_*` triggers take no `limit`.
  - The quoted trigger-call form rejects `>=` and `<=`.
  - `debug_log` reads `THIS`, not ROOT, and **cannot print a `$PARAM$`**. To log a slot's values, use a generated per-slot effect that prints the existing `te_tax_view_o<o>_*` script values with `[SCOPE.ScriptValue('…')|0]`. A `$N$` inside an effect *name* is fine (`te_tax_gen_x_$N$ = yes`).
  - `set_variable` and `change_variable` render nothing in tooltips.
  - `trigger_event = { id days }` takes a literal `days`, so a computed delay is a literal `if` chain.
  - `possible` is not a law field.
- **Generated files** carry `# AUTO-GENERATED by scripts/generators/gen_tax_code.py — do not edit manually`. Change them only by editing and re-running the generator: `python3 scripts/generators/gen_tax_code.py`, then confirm with `--check`. Every generated path is listed in `docs/auto_generated_files.md`. New generated content goes into the existing generated files, so no new path is needed.
- **File format.**
  - Brace `.txt` and `.gui` files are UTF-8 **with BOM** and tab-indented (`python3 scripts/format_paradox_tabs.py <files>`).
  - Loc files are UTF-8 with BOM, with an `l_english:` header. New keys go in `localization/english/te_tax_l_english.yml`; then run `python3 organize_loc.py` and commit what it changes.
  - **CRLF docs:** `docs/systems/journal_entry_systems.md`, `docs/guides/gui_modding_guide.md` and `docs/vanilla/treaty_articles_reference.md`. Edit them with the Edit tool or `sed`, never a Python rewrite, and confirm with `grep -c $'\r$' <file>` against `wc -l <file>`.
- **Testing.** Structural tests go in `test_tax_code_*.py` at the repo root and run with the dummy env:
  `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent python3 -m unittest <modules> -v`.
  Reuse the helpers in `test_tax_code_state.py` (`read`, `block`, `close`, `schema_tokens`, `KEYS`), `test_tax_code_rule.py` (`load`) and `test_tax_code_scheduler.py` (`closure`, `effects`).
  
  Before each commit, run with the same env:
  - `ruff check .`
  - `python3 scripts/format_paradox_tabs.py --check <changed .txt>`
  - `python3 organize_loc.py --check`
  - `python3 scripts/analysis/check_localization_files.py`
  - `python3 scripts/generators/gen_tax_code.py --check`
  - every strict audit in `.github/workflows/ci.yml`, with the exact commands copied from it (it now includes `je_multiplier_scope_audit --strict`)
  - the full suite: `python3 -m unittest discover -s . -p 'test_*.py'`
  
  The suite takes about 4 minutes; run it once, at the end of the task.
- **Commits.** Thematic, staged by path, never `git commit -a`. Each message ends with:
  ```
  Co-Authored-By: <your model> <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XQHDYfpKLJ77xwyxNQ8MHp
  ```
  Write your report file (the path your dispatch names, in `.superpowers/sdd/2026-10-03-tax-code-ai-and-release-tasks/`) before returning.
- **Player guide** edits happen in Task 28 only.
- **Lessons learned** that apply generally go into `docs/guides/scripting_best_practices.md` in the same task, one paragraph each (CLAUDE.md "Recording lessons learned").

## Review Focus

1. **The AI acting where it must not.** That means a rule-off game; a player country, including a tag switch between dispatch and `te_tax.8`; a country not migrated, without the carrier, or decentralized. Expected: nothing changes, and `te_tax.8`'s `trigger` re-checks `is_ai` and the code. *Pinned in Task 18.*
2. **Loops and log floods.** That means introduce and withdraw every month, an offer chain past its cap, a `no_viable` line every month, or a legitimacy retry that repeats. Expected: cooldowns bound each, and `no_viable` logs once per episode. *Pinned in Tasks 20 and 21.*
3. **Civil war and release.** A loser's open-bill marker, cooldown or offer count must never govern the winner. Rebels below legitimacy 25 log once and stop. *Pinned in Task 18 (tokens, reset) and Task 20 (episode marker).*
4. **Enactment and renegotiation.** These run only for AI countries and only on a promise at risk. Only kind 1 is enacted, never above the promised target, never for a pending or bound promise. The deadline log fires exactly once per promise. *Pinned in Task 19.*
5. **Rule-off regressions through shared files.** The AI-strategy hook leaves rule-off institution scores unchanged, and nothing outside the probe harness applies the per-good tariff registrations. *Pinned in Task 19 (hook) and Task 23 (registrations).*

---

## Package 6: AI legislation

### Task 18: AI state, fiscal signals and the dispatch

**Goal:** Every migrated country carries the AI tokens. The processor keeps the fiscal streaks and raises `te_tax.8` for an AI country on its bucket day when something is due. `te_tax.8` runs a step that, for now, only logs its signals. The commands' own `debug_log` lines become player-only.

**Files:**
- Create: `common/scripted_effects/te_tax_ai_effects.txt`, `common/scripted_triggers/te_tax_ai_triggers.txt`, `common/script_values/te_tax_ai_values.txt`, `test_tax_code_ai.py`.
- Modify:
  - `common/scripted_effects/te_tax_state_effects.txt` (init: AI tokens, schema 2);
  - `scripts/generators/gen_tax_code.py` (per-instrument AI tokens `te_tax_ai_last_<key>` / `te_tax_ai_dir_<key>` in `te_tax_gen_init_instruments`, and the copy list);
  - `common/scripted_effects/te_tax_schedule_effects.txt` (rule 1b);
  - `events/te_tax_internal_events.txt` (`te_tax.8`);
  - `common/scripted_effects/te_tax_civil_war_effects.txt` (reset calls);
  - the command `debug_log` sites in `te_tax_bill_effects.txt`, `te_tax_offer_effects.txt`, `te_tax_obligation_effects.txt` and generated bill effects;
  - `docs/systems/tax_code_schema.md` (schema rows, processor rule 1b, a new "AI legislation" section stub);
  - `test_tax_code_state.py` / `test_tax_code_civil_war.py` only where a pinned count or override list must change.

**Interfaces:**
- Consumes: `te_tax_record_fiscal_month` and its `te_tax_fisc_deficit` / `_surplus` variables, through `te_tax_fisc_rec_deficit` and `te_tax_fisc_rec_surplus`; `te_tax_code_in_force`; `te_tax_bill_active`; `te_tax_copy_token`; `te_history_month_index`.
- Produces, used by Tasks 19–22:
  - **Tokens:** `te_tax_ai_phase` (sentinel −1; drawn 0–11 by the first processor run that finds it negative), `te_tax_ai_def_streak` 0, `te_tax_ai_sur_streak` 0, `te_tax_ai_next_month` −1, `te_tax_ai_tpl` 0, `te_tax_ai_bill_month` −1, `te_tax_ai_noviable` 0, `te_tax_ai_offer_month` −1, `te_tax_ai_offer_count` 0, `te_tax_ai_retry` 0, and per instrument `te_tax_ai_last_<key>` −1 and `te_tax_ai_dir_<key>` 0.
  - **Values** (`te_tax_ai_values.txt`, country scope): every tunable of spec §2.14 under its exact name, plus `te_tax_ai_ratio` = `income / max(1, total_expenses)`, `te_tax_ai_debt` = `principal / credit` (0 when `credit <= 0`), `te_tax_ai_reserves` = `scaled_gold_reserves`, `te_tax_ai_cut_ratio_now` (`_cut_ratio`, or `_cut_ratio_debt` when debt is significant), `te_tax_ai_phase_draw` (a random integer 0–11; find the stored-random precedent in the UN AI, research G §6, and use its exact form) and `te_tax_ai_bucket` (`te_tax_ai_phase` modulo 4).
  - **Triggers** (`te_tax_ai_triggers.txt`):
    - `te_tax_ai_can_act`: rule on, `te_tax_code_in_force`, `is_ai = yes`, `has_law = law_type:law_te_tax_code`.
    - `te_tax_ai_emergency`: `in_default`, or debt ≥ `_emergency_debt`, or `taking_loans = yes` and `weeks_until_bankruptcy < te_tax_ai_emergency_weeks`.
    - `te_tax_ai_raise_need`, `te_tax_ai_cut_need`, exactly as in spec §2.3.
    - `te_tax_ai_kind4_in_force`: a fiscal-balance promise in state 7, 2 or 3.
    - `te_tax_ai_initiative_due`: `(te_history_month_index − te_tax_ai_phase)` modulo `te_tax_ai_cadence_months` = 0. Use a script value with `modulo`, then compare it with `= 0`.
    - `te_tax_ai_has_management`: a bill open, a held package, or an obligation slot in state 2 or 3.
    - `te_tax_ai_step_due`: can act, and initiative due, emergency or management.
  - **Effects:**
    - `te_tax_ai_update_streaks` (all countries);
    - `te_tax_ai_dispatch` (AI only);
    - `te_tax_ai_step` (stub; Tasks 19–21 fill it);
    - `te_tax_ai_reset_bill_state`: `te_tax_ai_tpl` 0, `_bill_month` −1, `_offer_month` −1, `_offer_count` 0, `_retry` 0, `_noviable` 0;
    - the log effects. `debug_log` cannot print a parameter, so write one small effect per verb, `te_tax_ai_log_<verb>`, each a single `debug_log` line `TE_TAX ai_<verb> tpl=… R=… D=… G=… def=… sur=…` plus the month, date and country stamp the other lines use. Verbs: `step`, `introduced`, `passed`, `forced`, `accepted`, `released`, `rescheduled`, `renegotiated`, and `waiting_legitimacy_native_level`. Withdrawal and no-viable get one effect per reason: `te_tax_ai_log_withdrawn_<reason>` and `te_tax_ai_log_no_viable_<reason>`, for `support`, `legitimacy`, `slots`, `authority`, `patience` and `draft`. `obl_enacted` (per slot, generated) comes in Task 19, and `year` in Task 22.

- [ ] **Step 1: Write the failing tests** in `test_tax_code_ai.py`:

```python
# -*- coding: utf-8 -*-
"""The tax code's AI layer (plan 2026-10-03, Tasks 18-22). Structural tests."""
import re
import unittest

from test_tax_code_scheduler import closure, effects
from test_tax_code_state import KEYS, block, read, schema_tokens

AI_EFFECTS = "common/scripted_effects/te_tax_ai_effects.txt"
AI_TRIGGERS = "common/scripted_triggers/te_tax_ai_triggers.txt"
AI_VALUES = "common/script_values/te_tax_ai_values.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
EVENTS = "events/te_tax_internal_events.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
AI_TOKENS = {
    "te_tax_ai_phase": "-1", "te_tax_ai_def_streak": "0", "te_tax_ai_sur_streak": "0",
    "te_tax_ai_next_month": "-1", "te_tax_ai_tpl": "0", "te_tax_ai_bill_month": "-1",
    "te_tax_ai_noviable": "0", "te_tax_ai_offer_month": "-1", "te_tax_ai_offer_count": "0",
    "te_tax_ai_retry": "0",
}
NATIVE_SETTERS = ("add_amendment", "remove_amendment", "set_tax_level", "add_taxed_goods",
                  "remove_taxed_goods", "set_import_tariff_level", "set_export_tariff_level")


class AiTokenTest(unittest.TestCase):
    def test_every_ai_token_is_in_the_schema_table_with_its_sentinel(self):
        country, _ = schema_tokens()
        for name, sentinel in AI_TOKENS.items():
            self.assertIn(name, country)
        for key in KEYS:
            self.assertIn(f"te_tax_ai_last_{key}", country)
            self.assertIn(f"te_tax_ai_dir_{key}", country)

    def test_schema_version_two_is_written_after_the_ai_rows(self):
        init = block(read(STATE), "te_tax_init_country")
        self.assertIn("te_tax_ai_phase", init)
        self.assertRegex(init, r"te_tax_schema value = 2")

    def test_reset_runs_at_outbreak_repair_and_release(self):
        text = read(CIVIL_WAR)
        for name in ("te_tax_copy_code", "te_tax_repair_after_civil_war", "te_tax_init_released_country"):
            self.assertIn("te_tax_ai_reset_bill_state = yes", block(text, name), name)

    def test_the_reset_zeroes_the_bill_state_and_keeps_streaks(self):
        reset = block(read(AI_EFFECTS), "te_tax_ai_reset_bill_state")
        for name in ("te_tax_ai_tpl", "te_tax_ai_bill_month", "te_tax_ai_offer_count", "te_tax_ai_retry", "te_tax_ai_noviable"):
            self.assertIn(f"name = {name}", reset)
        self.assertNotIn("te_tax_ai_def_streak", reset)


class AiDispatchTest(unittest.TestCase):
    def test_rule_1b_follows_the_fiscal_record_and_precedes_transitions(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        record = body.index("te_tax_record_fiscal_month = yes")
        streaks = body.index("te_tax_ai_update_streaks = yes")
        dispatch = body.index("te_tax_ai_dispatch = yes")
        sunset = body.index("te_tax_gen_sunset_wage = yes")
        self.assertLess(record, streaks)
        self.assertLess(streaks, dispatch)
        self.assertLess(dispatch, sunset)

    def test_dispatch_is_ai_only_and_uses_literal_bucket_days(self):
        dispatch = block(read(AI_EFFECTS), "te_tax_ai_dispatch")
        self.assertIn("is_ai = yes", dispatch)
        self.assertIn("te_tax_ai_step_due = yes", dispatch)
        days = set(re.findall(r"id = te_tax\.8 days = (\d+)", dispatch))
        self.assertEqual(days, {"1", "5", "12", "19", "26"})

    def test_the_step_event_rechecks_rule_and_ai(self):
        events = read(EVENTS)
        event = block(events, "te_tax.8")
        self.assertIn("hidden = yes", event)
        self.assertIn("te_tax_ai_can_act = yes", event)
        self.assertIn("te_tax_ai_step = yes", event)

    def test_te_tax_8_is_raised_only_by_the_dispatch_the_chain_and_the_console(self):
        hits = []
        for path in ("common/scripted_effects", "events"):
            for f in sorted((__import__("pathlib").Path(__file__).parent / path).glob("*.txt")):
                if "te_tax.8" in f.read_text(encoding="utf-8-sig"):
                    hits.append(f.name)
        self.assertEqual(sorted(hits), sorted({"te_tax_ai_effects.txt", "te_tax_internal_events.txt", "te_tax_debug_events.txt"} & set(hits)) )
        self.assertNotIn("te_tax_bill_effects.txt", hits)


class AiGateTest(unittest.TestCase):
    def test_every_ai_trigger_and_effect_entry_starts_from_the_rule(self):
        self.assertIn("te_tax_code_on = yes", block(read(AI_TRIGGERS), "te_tax_ai_can_act"))
        self.assertIn("te_tax_code_on = yes", block(read(AI_EFFECTS), "te_tax_ai_update_streaks"))

    def test_no_native_setter_in_the_ai_layer(self):
        text = read(AI_EFFECTS)
        for setter in NATIVE_SETTERS:
            self.assertNotRegex(text, rf"\b{setter}\b", setter)
```

  Add one more test that pins the log gating. Every `debug_log` in `te_tax_bill_effects.txt` and `te_tax_offer_effects.txt` must sit inside an `if = { limit = { is_ai = no } … }`, unless its enclosing effect is also called from the processor, the watchdog, `te_tax.4`–`te_tax.7` or the civil-war effects. Compute that set with `closure()` from those roots and keep it as an allowlist in the test, with a one-line reason per entry. Make the assertion textual: for each `debug_log =` offset, the nearest preceding unclosed `limit = {` in the same block contains `is_ai = no`.

- [ ] **Step 2: Run them and confirm they fail:** `python3 -m unittest test_tax_code_ai -v`. Expected: errors, because `te_tax_ai_effects.txt` does not exist.
- [ ] **Step 3: Implement.**
  - **Tokens in init.** Add the AI tokens to `te_tax_init_country`, as guarded writes after the customs block. Then bump the version: change the last line to `if = { limit = { NOT = { has_variable = te_tax_schema } } set_variable = { name = te_tax_schema value = 2 } } else_if = { limit = { var:te_tax_schema < 2 } set_variable = { name = te_tax_schema value = 2 } }`.
  - **Per-instrument tokens** come from `gen_tax_code.py`: add `("te_tax_ai_last_", -1)` and `("te_tax_ai_dir_", 0)` per instrument wherever `VERSION_TOKENS`-style lists feed `te_tax_gen_init_instruments` and `te_tax_gen_copy_code`. Regenerate.
  - **The streaks:**

```
# The fiscal streaks the AI's need tests read (plan Task 18; spec §2.3). Every
# migrated country, after the fiscal record of the 1st (te_tax_record_fiscal_month).
te_tax_ai_update_streaks = {
	if = {
		limit = { te_tax_code_on = yes has_variable = te_tax_schema }
		if = {
			limit = { te_tax_fisc_rec_deficit = yes }
			change_variable = { name = te_tax_ai_def_streak add = 1 }
		}
		else = {
			set_variable = { name = te_tax_ai_def_streak value = 0 }
		}
		if = {
			limit = {
				te_tax_fisc_rec_surplus = yes
				te_tax_ai_ratio >= te_tax_ai_cut_ratio_now
			}
			change_variable = { name = te_tax_ai_sur_streak add = 1 }
		}
		else = {
			set_variable = { name = te_tax_ai_sur_streak value = 0 }
		}
		if = {
			limit = { var:te_tax_ai_phase < 0 }
			# Drawn once; find the stored-random precedent in the UN AI (research G §6) and use its exact form.
			set_variable = { name = te_tax_ai_phase value = te_tax_ai_phase_draw }
		}
	}
}
```

  - **The dispatch** is an AI-only `if` with `te_tax_ai_step_due = yes`. With `te_tax_ai_retry = 1` it raises `te_tax.8` with `days = 1` and sets `_retry` back to 0. Otherwise it raises it with days 5, 12, 19 or 26, from `te_tax_ai_phase` modulo 4 (a script value `te_tax_ai_bucket`) in a literal `if`/`else_if` chain.
  - **`te_tax.8`:** a hidden country event, `trigger = { te_tax_ai_can_act = yes }`, `immediate = { te_tax_ai_step = yes }`.
  - **The step stub:** logs `te_tax_ai_log_step` for now. Tasks 19–21 replace the body.
  - **The reset** is called from the three civil-war sites: after the copy on the rebels, in the repair's in-force branch, and in the release's copy branch.
  - **Log gating:** wrap the command `debug_log` lines per Step 1's rule.
- [ ] **Step 4: Docs.**
  - Add the schema rows: the AI rows go in a new "AI legislation" sub-table under Schema, with meaning and sentinel.
  - Add processor rule 1b to "Processor rules".
  - Add an "AI legislation" section stub in `tax_code_schema.md`: dispatch, buckets, `te_tax.8`, the reset sites. Tasks 19–22 extend it.
- [ ] **Step 5: Run the tests and the checks** in Global Constraints. The new tests pass, and nothing else changes except deliberately updated pinned counts, each named in the report.
- [ ] **Step 6: Commit.** `git add` the paths above. Message: `"Tax code AI: state tokens, fiscal streaks, dispatch to te_tax.8"`.

---

### Task 19: Held packages, promises, the deadline log and the institution hook

**Goal:**
- The AI step resolves held packages.
- It enacts a kind-1 promise the native AI is about to miss, and renegotiates a kind-2 or kind-4 promise that would breach.
- Every country logs met or unmet when a promise's delivery phase ends.
- AI countries owing an institution promise weight that institution higher.

**Files:**
- Modify:
  - `common/scripted_effects/te_tax_ai_effects.txt` (`te_tax_ai_manage_packages`, `te_tax_ai_manage_promises`, and both called from `te_tax_ai_step`);
  - `scripts/generators/gen_tax_code.py`:
    - `te_tax_gen_ai_enact_<o>` per obligation slot: a branch per arg (1 schools, 2 health, 3 social security) and per target level 1 to 9, the mod's `MAX_INSTITUTION_INVESTMENT`, `common/defines/extra_defines.txt:21`;
    - `te_tax_gen_obl_log_met_<o>` / `_unmet_<o>` / `te_tax_gen_ai_log_enacted_<o>` per slot;
  - `common/scripted_effects/te_tax_obligation_effects.txt` (`te_tax_obl_check_one` calls the log effects);
  - `common/scripted_triggers/te_tax_ai_triggers.txt` (`te_tax_ai_owes_institution = { ARG }`, `te_tax_ai_promise_at_risk = { N }`);
  - `common/ai_strategies/edited_default_strategy.txt` (the institution hook);
  - `docs/systems/tax_code_schema.md` ("Obligations and the AI", "AI legislation");
  - `test_tax_code_ai.py`, `test_tax_code_obligations.py`.

**Interfaces:**
- Consumes:
  - from Task 18: `te_tax_ai_can_act`, `te_tax_ai_values.txt` (`te_tax_ai_enact_lead_months`, `te_tax_ai_promise_institution_score`) and `te_tax_ai_log_*`;
  - existing: `te_tax_can_package_reschedule = { SLOT }`, `te_tax_cmd_package_reschedule = { SLOT }`, `te_tax_can_package_release = { SLOT }`, `te_tax_cmd_package_release = { SLOT }`, `te_tax_can_obl_renegotiate = { N }`, `te_tax_cmd_obl_renegotiate = { N }`, `te_tax_obl_delivered = { N }`, `te_tax_obl_holds = { N }`, `te_tax_obl_inst_level_<arg>`, and the views `te_tax_view_o<o>_kind`, `_arg`, `_target`, `_baseline`, `_deadline`, `_state`.
- Produces: `te_tax_ai_manage_packages`, `te_tax_ai_manage_promises`, `te_tax_ai_owes_institution = { ARG }`, `te_tax_ai_promise_at_risk = { N }`, and the log tags `obl_deadline` and `ai_obl_enacted`.

**Rules (spec §2.4 steps 1–2, §2.8):**
- **Held packages.**
  - For each slot `a`, then `b`: state 2 → release.
  - State 3 → reschedule if `te_tax_can_package_reschedule = { SLOT = x }` holds, else release.
  - Log `ai_released` or `ai_rescheduled`.
- **At risk** (`te_tax_ai_promise_at_risk = { N }`): `te_tax_o$N$_on = 1`, and either
  - state 2, `var:te_tax_o$N$_deadline <= now + te_tax_ai_enact_lead_months`, and `NOT = { te_tax_obl_delivered = { N = $N$ } }`; or
  - state 3 and `NOT = { te_tax_obl_holds = { N = $N$ } }`.
- **Handling.** At most one at-risk promise per step, slots in order 1–4.
  - **Kind 1:** run `te_tax_gen_ai_enact_$N$ = yes`, which sets the arg's institution to `var:te_tax_o$N$_target` through the literal branch, inside `has_institution = <x>`, then `te_tax_gen_ai_log_enacted_$N$ = yes`.
  - **Kinds 2 and 4:** `if = { limit = { te_tax_can_obl_renegotiate = { N = $N$ } } te_tax_cmd_obl_renegotiate = { N = $N$ } te_tax_ai_log_renegotiated = yes }`.
  - Never a state 1 (pending) or 7 (bound) slot.
- **Deadline log, every country.**
  - In `te_tax_obl_check_one`'s delivering branch: when `te_tax_obl_delivered` holds, call `te_tax_gen_obl_log_met_$N$ = yes` before `te_tax_obl_begin_maintenance`.
  - When the deadline breach branch fires, call `te_tax_gen_obl_log_unmet_$N$ = yes` before `te_tax_obl_breach`.
  - The line is `TE_TAX obl_deadline result=met|unmet slot=<o> kind=… arg=… target=… baseline=… deadline=… ai=[yes/no]`. The per-slot effect prints the views, and `ai` comes from an `is_ai` branch with two literal lines.
- **Institution hook.** In the existing `INJECT:ai_strategy_default`:

```
		institution_schools = {
			value = 10
			if = {
				limit = { te_tax_ai_owes_institution = { ARG = 1 } }
				add = te_tax_ai_promise_institution_score
			}
		}
		institution_health_system = {
			value = 10
			if = {
				limit = { te_tax_ai_owes_institution = { ARG = 2 } }
				add = te_tax_ai_promise_institution_score
			}
		}
```

  `te_tax_ai_owes_institution` starts with `te_tax_code_on = yes`. It then ORs the four slots: `has_variable = te_tax_o<o>_on`, `var:te_tax_o<o>_on = 1`, `var:te_tax_o<o>_kind = 1`, `var:te_tax_o<o>_arg = $ARG$`, and state 7, 2 or 3. The political agenda strategies are **not** touched (spec §2.8).

- [ ] **Step 1: Write the failing tests** (append to `test_tax_code_ai.py`):

```python
OBLIGATIONS = "common/scripted_effects/te_tax_obligation_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
STRATEGY = "common/ai_strategies/edited_default_strategy.txt"


class AiPromiseTest(unittest.TestCase):
    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.gen = read(GEN_EFFECTS)

    def test_held_packages_release_conflicts_and_reschedule_missed_when_valid(self):
        body = block(self.ai, "te_tax_ai_manage_packages")
        for slot in ("a", "b"):
            self.assertIn(f"te_tax_can_package_release = {{ SLOT = {slot} }}", body)
            self.assertIn(f"te_tax_can_package_reschedule = {{ SLOT = {slot} }}", body)

    def test_enactment_is_kind_1_only_and_never_pending_or_bound(self):
        body = block(self.ai, "te_tax_ai_manage_promises")
        self.assertIn("te_tax_ai_promise_at_risk", body)
        risk = block(read(AI_TRIGGERS), "te_tax_ai_promise_at_risk")
        self.assertNotRegex(risk, r"_state = [17]\b")
        for o in (1, 2, 3, 4):
            enact = block(self.gen, f"te_tax_gen_ai_enact_{o}")
            self.assertIn("set_institution_investment_level", enact)
            self.assertIn(f"var:te_tax_o{o}_kind = 1", enact)

    def test_enactment_targets_exactly_the_promised_level(self):
        enact = block(self.gen, "te_tax_gen_ai_enact_1")
        for level in range(1, 10):
            self.assertIn(f"var:te_tax_o1_target = {level}", enact)
            self.assertIn(f"level = {level}", enact)

    def test_balance_promises_are_renegotiated_through_the_command(self):
        body = block(self.ai, "te_tax_ai_manage_promises")
        self.assertIn("te_tax_can_obl_renegotiate", body)
        self.assertIn("te_tax_cmd_obl_renegotiate", body)

    def test_enactment_appears_only_in_the_ai_layer(self):
        import pathlib
        for f in pathlib.Path(__file__).parent.glob("common/**/*.txt"):
            text = f.read_text(encoding="utf-8-sig")
            if "set_institution_investment_level" in text and "te_tax" in f.name:
                self.assertIn(f.name, {"te_tax_generated_effects.txt"}, f.name)


class DeadlineLogTest(unittest.TestCase):
    def test_met_and_unmet_lines_once_per_promise(self):
        check = block(read(OBLIGATIONS), "te_tax_obl_check_one")
        self.assertEqual(check.count("te_tax_gen_obl_log_met_$N$ = yes"), 1)
        self.assertEqual(check.count("te_tax_gen_obl_log_unmet_$N$ = yes"), 1)
        self.assertLess(check.index("te_tax_gen_obl_log_met_$N$"), check.index("te_tax_obl_begin_maintenance"))

    def test_the_log_line_prints_views_not_params(self):
        gen = read(GEN_EFFECTS)
        for o in (1, 2, 3, 4):
            line = block(gen, f"te_tax_gen_obl_log_unmet_{o}")
            self.assertIn("TE_TAX obl_deadline result=unmet", line)
            self.assertIn(f"te_tax_view_o{o}_kind", line)
            self.assertNotIn("$", line)


class InstitutionHookTest(unittest.TestCase):
    def test_hook_on_schools_and_health_only_and_rule_gated(self):
        text = read(STRATEGY)
        self.assertIn("te_tax_ai_owes_institution = { ARG = 1 }", text)
        self.assertIn("te_tax_ai_owes_institution = { ARG = 2 }", text)
        owes = block(read(AI_TRIGGERS), "te_tax_ai_owes_institution")
        self.assertIn("te_tax_code_on = yes", owes)
        for o in (1, 2, 3, 4):
            self.assertIn(f"var:te_tax_o{o}_kind = 1", owes)

    def test_no_political_strategy_is_injected(self):
        import pathlib
        for f in pathlib.Path(__file__).parent.glob("common/ai_strategies/*.txt"):
            self.assertNotRegex(f.read_text(encoding="utf-8-sig"), r"(INJECT|REPLACE):ai_strategy_\w+_agenda")
```

- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement** per the rules above. The generator emits the per-slot effects; regenerate and run `--check`. The step's body becomes:

```
te_tax_ai_step = {
	if = {
		limit = { te_tax_ai_can_act = yes }
		te_tax_ai_manage_packages = yes
		te_tax_ai_manage_promises = yes
		# Task 20: the open bill. Task 21: the initiative.
	}
}
```

- [ ] **Step 4: Docs.**
  - Schema "Obligations and the AI": replace the stub sentence with the enactment, renegotiation, deadline log and hook. State the P16 dependency: if `set_institution_investment_level` sets a target rather than the level, raise `te_tax_ai_enact_lead_months`.
  - Capability ledger: add a row "AI promise delivery (default-strategy boost; enactment fallback)" with status `static-only` and the play-test.
- [ ] **Step 5: Run the tests and all checks.**
- [ ] **Step 6: Commit:** `"Tax code AI: held packages, promise enactment and renegotiation, deadline log, institution boost"`.

---

### Task 20: The open bill: pass, offers, force-through, withdrawal

**Goal:** An AI country with a bill under debate passes it as soon as it can. Otherwise it buys support with offers in a bounded chain, forces it through only in an emergency, and withdraws it when it cannot pass. Every action leaves one summary log line, and cooldowns stop it repeating.

**Files:**
- Modify:
  - `common/scripted_effects/te_tax_ai_effects.txt` (`te_tax_ai_manage_bill`, `te_tax_ai_accept_best_offer`, `te_tax_ai_withdraw = { REASON }` as one effect per reason, `te_tax_ai_after_pass`);
  - `scripts/generators/gen_tax_code.py`:
    - `te_tax_gen_ai_accept_offer`: per group in clout order, the acceptance policy below;
    - `te_tax_gen_ai_record_marks`: per instrument, sets `te_tax_ai_last_<key>` = now and `te_tax_ai_dir_<key>` = +1 or −1 from the sign of `te_tax_bl_dstep_<key>` for each instrument the bill changes;
  - `common/scripted_triggers/te_tax_ai_triggers.txt` (`te_tax_ai_bill_hopeless`, `te_tax_ai_blocked_by_native_level`, `te_tax_ai_offer_acceptable_<ig>` generated or hand-written);
  - `common/scripted_effects/te_tax_schedule_effects.txt`: no change; the retry flag is read by Task 18's dispatch;
  - schema doc "AI legislation";
  - `test_tax_code_ai.py`.

**Interfaces:**
- Consumes:
  - from Task 18: tokens and values, `te_tax_ai_emergency`, `te_tax_ai_reset_bill_state`, `te_tax_ai_log_*`;
  - existing: `te_tax_can_pass` / `te_tax_cmd_pass`, `te_tax_can_force_through` / `te_tax_cmd_force_through`, `te_tax_can_withdraw` / `te_tax_cmd_withdraw`, `te_tax_can_accept_offer = { IG }` / `te_tax_cmd_accept_offer = { IG }`, `te_tax_committed_share`, `te_tax_passage_share`, `te_tax_view_open_share`, `te_tax_off_<ig>_kind` / `_arg`, `te_tax_sup_<ig>`, `te_tax_dl_revenue`, `te_tax_bl_due`, `bureaucracy`, `approaching_bureaucracy_shortage`.
- Produces: `te_tax_ai_manage_bill`, `te_tax_ai_bill_hopeless`, `te_tax_gen_ai_record_marks`, and the reasons `support`, `legitimacy`, `legitimacy_native_level`, `slots`, `authority` and `patience`.

**Rules (spec §2.4 step 3, §2.7):**
1. If `te_tax_can_pass = yes`:
   - run `te_tax_gen_ai_record_marks`;
   - set `te_tax_ai_next_month` = `var:te_tax_bl_due + te_tax_ai_cooldown_months`;
   - run `te_tax_cmd_pass`, then `te_tax_ai_log_passed`;
   - run `te_tax_ai_reset_bill_state`.
2. Else if `te_tax_ai_blocked_by_native_level`: every pass line holds except legitimacy, and `NOT = { tax_level = medium }`. Then set `te_tax_ai_retry = 1` and log `ai_waiting reason=legitimacy_native_level`, once while `_retry` stays 1. Task 18's dispatch raises the step with `days = 1` on the next 1st.
3. Else, if the offer budget allows (`te_tax_ai_offer_month` ≠ now resets `_offer_count` to 0; `_offer_count < te_tax_ai_max_offers`), and `te_tax_committed_share <= te_tax_passage_share`: run `te_tax_gen_ai_accept_offer`.
   - It accepts the first acceptable offer in this order: persuadable groups (`te_tax_com_<ig> = 0`, `te_tax_sup_<ig> >= 0`) by `ig_clout`, largest first, then opposed groups. The clout order uses a generated if-chain over the eight groups' clout, ranked by a pairwise-comparison script value per group.
   - If one is accepted: `_offer_count` +1, `_offer_month` = now, log `ai_accepted`, and `trigger_event = { id = te_tax.8 days = 1 }`.
   - An offer is **acceptable** when all of these hold:
     - `te_tax_can_accept_offer = { IG = x }`;
     - for a clause (kinds 1–3): the bill still raises revenue (`te_tax_dl_revenue > 0`) while the AI template is a raise (1, 2, 3 or 6), or is still a cut while it is T5. Agricultural relief (kind 2) is only accepted outside an emergency;
     - for a promise (kind 10 + k): k = 1 with `bureaucracy >= 0` and `approaching_bureaucracy_shortage = no`; k = 2 with `bureaucracy > 0` and no approaching shortage; k = 4 with `te_tax_dl_revenue > 0` and no emergency.
4. Else, if `te_tax_ai_emergency = yes` and `te_tax_can_force_through = yes`: run `te_tax_gen_ai_record_marks`, set the cooldown as in rule 1, run `te_tax_cmd_force_through`, log `ai_forced`, and run the reset.
5. Else, if `te_tax_ai_bill_hopeless`, or `te_tax_now - var:te_tax_ai_bill_month >= te_tax_ai_bill_patience`, withdraw with the matching reason.
   - **Hopeless** means `te_tax_view_open_share <= te_tax_passage_share`, no offer that could still be accepted this month, and not (emergency and committed share ≥ `te_tax_force_share`).
   - **The withdraw effect:** `te_tax_cmd_withdraw` inside its trigger; `te_tax_ai_next_month` = now + `te_tax_ai_fail_cooldown_months`; log `ai_withdrawn reason=<r>`. Log `ai_no_viable reason=<r>` only if `te_tax_ai_noviable = 0`, then set it to 1. Then the reset, but keep `_noviable`: it is reset only when a bill passes or the need ends (Task 21). So call the reset first and set `_noviable` after it.
   - **The reason:** `legitimacy` when legitimacy is below the passage line; `slots` when no slot is free; `authority` when force-through failed only on authority or override capacity; else `support`.

- [ ] **Step 1: Write the failing tests:**

```python
class AiBillTest(unittest.TestCase):
    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.manage = block(self.ai, "te_tax_ai_manage_bill")

    def test_order_pass_retry_offer_force_withdraw(self):
        order = [self.manage.index(s) for s in (
            "te_tax_can_pass = yes", "te_tax_ai_blocked_by_native_level = yes",
            "te_tax_gen_ai_accept_offer = yes", "te_tax_can_force_through = yes", "te_tax_ai_bill_hopeless = yes")]
        self.assertEqual(order, sorted(order))

    def test_force_through_only_in_an_emergency(self):
        force = self.manage[self.manage.index("te_tax_can_force_through = yes") - 200:]
        self.assertIn("te_tax_ai_emergency = yes", force[:400])

    def test_offer_chain_is_capped_and_re_raises_tomorrow(self):
        self.assertIn("te_tax_ai_offer_count < te_tax_ai_max_offers", self.manage.replace("var:", ""))
        self.assertIn("id = te_tax.8 days = 1", self.ai)

    def test_every_command_runs_behind_its_own_trigger(self):
        for cmd in ("pass", "force_through", "withdraw"):
            for m in re.finditer(rf"te_tax_cmd_{cmd} = yes", self.ai):
                before = self.ai[max(0, m.start() - 300):m.start()]
                self.assertIn(f"te_tax_can_{cmd} = yes", before, cmd)

    def test_no_viable_logs_once_per_episode(self):
        withdraw = self.ai[self.ai.index("ai_no_viable"):][:0] or self.ai
        self.assertRegex(withdraw, r"var:te_tax_ai_noviable = 0")

    def test_the_reset_follows_pass_force_and_withdraw(self):
        for label in ("ai_passed", "ai_forced", "ai_withdrawn"):
            self.assertIn("te_tax_ai_reset_bill_state = yes", self.ai)

    def test_passing_records_the_reverse_window_marks(self):
        gen = read("common/scripted_effects/te_tax_generated_effects.txt")
        marks = block(gen, "te_tax_gen_ai_record_marks")
        for key in KEYS:
            self.assertIn(f"te_tax_ai_last_{key}", marks)
            self.assertIn(f"te_tax_ai_dir_{key}", marks)
```

  Tighten `test_no_viable_logs_once_per_episode` when implementing: find the `ai_no_viable` log call and assert that the `limit` guarding it reads `var:te_tax_ai_noviable = 0` and that the same branch sets it to 1.

- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** Add `if = { limit = { te_tax_bill_active = yes } te_tax_ai_manage_bill = yes }` to `te_tax_ai_step` after the promises.
- [ ] **Step 4: Docs.** Schema "AI legislation": the bill rules, the reasons, the cooldowns, the offer policy table. Ledger: a row "AI passage loop" (`static-only`, play-test S13).
- [ ] **Step 5: Run the tests and all checks.**
- [ ] **Step 6: Commit:** `"Tax code AI: pass, bounded offer chain, emergency force-through, withdrawal with reasons"`.

---

### Task 21: The initiative: pre-score and templates

**Goal:** An AI country with an initiative due, or an emergency, and no bill open, builds exactly one template bill with the draft commands, introduces it, and in the same execution keeps it or withdraws it with a reason.

**Files:**
- Modify:
  - `scripts/generators/gen_tax_code.py`:
    - `te_tax_ai_cost_<key>` per instrument, the pre-score;
    - `te_tax_ai_excluded_<key>` triggers;
    - `te_tax_gen_ai_pick_raise` / `_pick_cut`, which set `te_tax_ai_pick` (1–5, 0 none) and `te_tax_ai_pick2` (the second cheapest, for two-instrument templates);
    - `te_tax_gen_ai_step_inst = { INST DIR }`, one branch per instrument code calling `te_tax_cmd_draft_step = { KEY = <key> DIR = <dir> }` behind its trigger;
    - `te_tax_gen_ai_tax_luxury`: the catalog's `luxury`-category goods in a fixed order; taxes the first one or two untaxed through `te_tax_cmd_draft_good`.
  - `common/scripted_effects/te_tax_ai_effects.txt` (`te_tax_ai_initiative`, `te_tax_ai_build_t1`, `_t2`, `_t3`, `_t5`, `_t6`, `te_tax_ai_introduce_and_judge`);
  - `common/scripted_triggers/te_tax_ai_triggers.txt` (`te_tax_ai_initiative_ready`, `te_tax_ai_template_<n>_applies`);
  - `common/script_values/te_tax_ai_values.txt` (`te_tax_ai_taxed_goods`, the number of catalog goods the enacted code taxes; reuse `te_tax_view_goods_count` if it fits);
  - schema doc "AI legislation" (the templates table, the pre-score formula);
  - `test_tax_code_ai.py`.

**Interfaces:**
- Consumes:
  - from Tasks 18 and 20: tokens, needs, emergency, `te_tax_ai_bill_hopeless`, the withdraw effects, the marks;
  - existing: `te_tax_can_draft_new` / `te_tax_cmd_draft_new`, `te_tax_can_draft_step = { KEY DIR }` / `te_tax_cmd_draft_step`, `te_tax_can_draft_sunset = { KEY DIR }` / `te_tax_cmd_draft_sunset`, `te_tax_can_draft_due = { DIR }` / `te_tax_cmd_draft_due`, `te_tax_can_draft_good = { GOOD }` / `te_tax_cmd_draft_good`, `te_tax_can_draft_discard` / `te_tax_cmd_draft_discard`, `te_tax_can_introduce` / `te_tax_cmd_introduce`;
  - from the generator: `EXPOSURE`, `LEVEL_STEPS`, `INSTRUMENTS` (steps, max), `PROGRESSIVE_KEYS`, `IGS`, `GOODS_CATEGORY_WEIGHT`, `consumption_catalog()`, `goods_definitions()`; the support values `te_tax_ideo_p_<ig>`; the committed-share clout pattern (`ig:ig_<ig> ?= { … ig_clout … }`, `ig_counts_as_marginal = no`).
- Produces: `te_tax_ai_initiative`, `te_tax_ai_cost_<key>`, `te_tax_ai_pick` / `te_tax_ai_pick2`, and the template codes 1 (T1), 2 (T2), 3 (T3), 5 (T5) and 6 (T6) stored in `te_tax_ai_tpl`.

**Rules (spec §2.4 step 4, §2.5, §2.6):**
- **Ready** (`te_tax_ai_initiative_ready`):
  - no bill;
  - either `te_tax_ai_emergency`, or all of: `te_tax_ai_initiative_due`; `var:te_tax_ai_next_month < 0` or `<= te_tax_now` (not on cooldown); no awaiting package (`te_tax_pa_state` and `te_tax_pb_state` ≠ 1 while `_on`).
- **Need ended.** When neither a raise nor a cut need holds, and no emergency, set `te_tax_ai_noviable = 0`.
- **Template choice, first that applies:**
  - T2 on an emergency;
  - T3 when `is_at_war = yes` and the raise need holds;
  - T6 when the raise need holds, `te_tax_en_cons >= 1` and `te_tax_ai_taxed_goods < te_tax_ai_max_goods`;
  - T1 when the raise need holds;
  - T5 when the cut need holds;
  - otherwise nothing.
- **Pre-score.** For a +1 step on instrument k:

  `te_tax_ai_cost_<k>` = Σ over the IGS present and not marginal: `ig_clout` × (10 × s_k × exposure(ig, k) − 5 × `te_tax_ideo_p_<ig>` × sign_k × s_k)

  where s_k = step ÷ level step (wage 0.5, div 0.5, land 1/6, head 1/3, cons 1), and sign_k = +1 for wage and div, −1 otherwise. The generator writes the constants.
- **Excluded for a raise** (`te_tax_ai_excluded_raise_<k>`):
  - the index is at `te_tax_max_<k>`;
  - Traditionalism forbids wage or dividends (reuse the condition `te_tax_draft_ready` uses);
  - k = cons and no catalog good is taxed;
  - `te_tax_ai_dir_<k> = -1` and `te_tax_ai_last_<k> >= now − te_tax_ai_reverse_months`.
- **Excluded for a cut:** the index is 0, or `te_tax_ai_dir_<k> = 1` within the window.
- **Picking.** The raise pick is the lowest cost not excluded; the cut pick is the highest cost not excluded. Ties go to `INSTRUMENTS` order.
- **Templates:**
  - **T1:** +1 on the pick; with a second pick, +1 on it too.
  - **T2:** +2 on the pick (two DIR 1 steps); then `te_tax_cmd_draft_due = { DIR = 0 }` once, so the bill is due at now + 2.
  - **T3:** +2 on the pick; then `te_tax_cmd_draft_sunset = { KEY DIR = 1 }` three times (0 → 6 → 12 → 24 = `te_tax_ai_levy_sunset`).
  - **T5:** −1 (DIR 0) on the cut pick.
  - **T6:** tax up to two untaxed luxury goods.
  
  Every command runs behind its own trigger.
- **Introduce and judge.**
  - Discard a stale draft first. Then `te_tax_cmd_draft_new`, build, and `te_tax_cmd_introduce`.
  - If the bill is now open: set `te_tax_ai_tpl` and `te_tax_ai_bill_month` = now and log `ai_introduced`. If `te_tax_ai_bill_hopeless`, withdraw (Task 20's effect, reason by the same rule).
  - If introduction was refused, discard the draft and log `ai_no_viable reason=draft`, once per episode, with the same marker.

- [ ] **Step 1: Write the failing tests:**

```python
from scripts.generators import gen_tax_code as gen


class AiInitiativeTest(unittest.TestCase):
    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.values = read("common/script_values/te_tax_generated_support_values.txt") + read(AI_VALUES)

    def test_template_order_is_emergency_war_goods_raise_cut(self):
        body = block(self.ai, "te_tax_ai_initiative")
        order = [body.index(f"te_tax_ai_build_t{n} = yes") for n in (2, 3, 6, 1, 5)]
        self.assertEqual(order, sorted(order))

    def test_pre_score_constants_follow_exposure_and_level_steps(self):
        for key in KEYS:
            cost = block(self.values, f"te_tax_ai_cost_{key}")
            for ig in gen.IGS:
                self.assertIn(f"ig:ig_{ig}", cost)
            self.assertIn("ig_counts_as_marginal = no", cost)

    def test_templates_use_only_draft_commands_behind_triggers(self):
        for cmd in ("draft_new", "draft_due", "draft_sunset", "draft_good", "draft_discard", "introduce"):
            for m in re.finditer(rf"te_tax_cmd_{cmd}\b", self.ai):
                self.assertIn(f"te_tax_can_{cmd}", self.ai[max(0, m.start() - 300):m.start()], cmd)

    def test_no_template_touches_customs_or_relief(self):
        for name in ("te_tax_cmd_draft_customs", "te_tax_cmd_draft_relief", "te_tax_cmd_draft_relief_state"):
            self.assertNotIn(name, self.ai)

    def test_one_bill_per_initiative_and_judged_in_the_same_execution(self):
        judge = block(self.ai, "te_tax_ai_introduce_and_judge")
        self.assertEqual(judge.count("te_tax_cmd_introduce = yes"), 1)
        self.assertLess(judge.index("te_tax_cmd_introduce = yes"), judge.index("te_tax_ai_bill_hopeless = yes"))

    def test_reverse_window_excludes_recent_opposite_moves(self):
        triggers = read("common/scripted_triggers/te_tax_generated_triggers.txt") + read(AI_TRIGGERS)
        for key in KEYS:
            excl = block(triggers, f"te_tax_ai_excluded_raise_{key}")
            self.assertIn(f"te_tax_ai_dir_{key}", excl)
            self.assertIn("te_tax_ai_reverse_months", excl)
```

  Also add a generator unit test: `gen.ai_step_levels()` (a helper you add) returns wage 0.5, div 0.5, land 1/6, head 1/3 and cons 1, as `Decimal`s, from `INSTRUMENTS` and `LEVEL_STEPS`.
- [ ] **Step 2: Run them and confirm they fail.**
- [ ] **Step 3: Implement.** Add `else_if = { limit = { te_tax_ai_initiative_ready = yes } te_tax_ai_initiative = yes }` after the bill branch in `te_tax_ai_step`.
- [ ] **Step 4: Docs.** In the schema's "AI legislation": the templates, the pre-score, the exclusions, the tunables table with the days-to-threshold table copied from spec §2.14. Ledger: the row "AI pre-score vs real support" (`static-only`).
- [ ] **Step 5: Run the tests and all checks**, including `gen_tax_code.py --check`.
- [ ] **Step 6: Commit:** `"Tax code AI: pre-score and template bills, introduced and judged in one step"`.

---

### Task 22: AI console options and yearly drift summary

**Goal:** A tester can watch the AI legislate in one session, and the owner's observer run gets a yearly drift summary per AI country.

**Files:**
- Modify:
  - `events/te_tax_debug_events.txt`: new console events `te_tax_debug.2` (run the AI step now on the player's country, ROOT = it, ignoring `is_ai`: call the step's managers and initiative directly behind `te_tax_code_in_force`), `te_tax_debug.3` (print the AI signals and the five pre-scores), `te_tax_debug.4` (set `te_tax_ai_def_streak` to `te_tax_ai_need_months` and clear the cooldown). Each has `# REVIEWED 2026-10-03: console-only test event` on its opening line, like `te_tax_debug.1`.
  - `common/scripted_effects/te_tax_ai_effects.txt` (`te_tax_ai_log_year`), called from `te_tax_process_month` when the month index modulo 12 is 0 and `is_ai = yes`: `TE_TAX ai_year drift_level=… drift_goods=… drift_amend=… tpl=… def=… sur=…`.
  - `common/scripted_effects/te_tax_schedule_effects.txt` (the call).
  - `docs/testing/tax-code-probes.md` (a short "AI console" section).
  - `test_tax_code_ai.py`.

**Interfaces:** consumes everything from Tasks 18–21. Produces the console ids that the runbook (Task 27) cites: `te_tax_debug.2`, `.3` and `.4`.

- [ ] **Step 1: Failing tests.**
  - Each console event is `hidden = no`, or a `type = country_event` with options, as `te_tax_debug.1` is built; check that one and match it.
  - Each is never raised by script (grep: no `te_tax_debug.[234]` outside the events file and the docs).
  - `te_tax_debug.2` calls `te_tax_ai_manage_packages`, `te_tax_ai_manage_promises`, `te_tax_ai_manage_bill` and `te_tax_ai_initiative`, behind `te_tax_code_in_force = yes`.
  - The yearly log is gated `is_ai = yes`, and on January (`te_history_month_index` modulo 12 = 0).
- [ ] **Step 2: Confirm they fail.** **Step 3: Implement.** **Step 4: Docs.** **Step 5: Run all checks.**
- [ ] **Step 6: Commit:** `"Tax code AI: console options and the yearly drift summary"`.

---

### Task 23: Customs probe: register the per-good tariff families and extend P09

**Goal:** The owner can test, in one session, whether the per-good tariff modifiers work once registered, and which of the two mechanisms holds (spec §2.9): the lock (min = max level) or the carrier (maxima cancelled plus a per-good rate). No production path applies these modifiers.

**Files:**
- Create: `common/modifier_type_definitions/te_tax_probe_modifier_types.txt`. It registers the six families for `grain` (staple) and `iron` (industrial): `country_<g>_import_tariffs_rate_add`, `country_<g>_export_tariffs_rate_add`, `country_<g>_max_import_tariffs_level_add`, `country_<g>_min_import_tariffs_level_add`, `country_<g>_max_export_tariffs_level_add`, `country_<g>_min_export_tariffs_level_add`.
  - Copy the shape and fields of the nearest vanilla tariff registration, `state_tariff_import_add` in the installed game's `common/modifier_type_definitions/00_modifier_types.txt:562-580`.
  - Rate keys: `percent = yes`.
  - Level keys: `decimals = 0`, no percent.
  - Colours: copy what the vanilla tariff entries use.
- Modify:
  - `common/static_modifiers/te_debug_tax_modifiers.txt`: add `te_tp_lock_grain_low` (min +X, max −Y so min = max = the low-tariffs level, with the arithmetic from the level range −3..3 written in a comment) and `te_tp_cancel_max` (`state_tariff_import_add = -0.5`, `state_tariff_export_add = -0.5`, `state_subvention_import_add = -0.5`, `state_subvention_export_add = -0.5`);
  - the probe's apply and remove options for P09 in `common/scripted_effects/te_debug_tax_effects.txt` and its event: add options "P09b lock grain at low" and "P09c cancel maxima + grain rate", each removable, behind the harness's existing arm gate;
  - `docs/testing/tax-code-probes.md` (P09b and P09c: setup, what to observe — the Budget's grain tariff buttons enabled or greyed, the market goods panel's tariff line, the Budget tariff income line, whether an AI market owner's grain level moves within 3 months, and the `debug.log` "Unknown modifier type" line gone — and the decision rule for lock or carrier);
  - `docs/testing/tax-code-capability-ledger.md` row 14: "re-test pending: registration added (2026-10-03)";
  - the loc file, if the loc-coverage audit asks for the new types' names; vanilla's dynamic names may already cover them, so check with `python3 loc_coverage_audit.py` before adding any;
  - `test_tax_code_probes.py`.

**Interfaces:** consumes the harness (`te_debug_tax*`, the arm gate `te_tp_lock` and the namespace). Produces probe ids P09b and P09c for the runbook (Task 27).

- [ ] **Step 1: Failing tests** (`test_tax_code_probes.py`):
  - the registration file names exactly the 12 keys above;
  - no file outside `te_debug_tax*` and the registration file names any of them (scan `common/`, `events/` and `gui/`);
  - the two new probe modifiers are applied only from the harness effects, behind its arm gate.
- [ ] **Step 2: Confirm they fail.** **Step 3: Implement.** **Step 4: Docs.**
- [ ] **Step 5: Run all checks.** `duplicate_key_audit --strict` must pass, since a registration may collide with a vanilla key: grep the installed game's `modifier_type_definitions` first.
- [ ] **Step 6: Commit:** `"Tax code customs probe: register per-good tariff families, P09b lock and P09c carrier"`.

---

## Package 7: Release validation and documentation

### Task 24: Tax code save report

**Goal:** `scripts/analysis/tax_code_save_report.py` prints a country's tax code from a save, binary or plain text, and `--diff` compares two saves group by group.

**Files:**
- Create: `scripts/analysis/tax_code_save_report.py`, `test_tax_code_save_report.py`, `test_fixtures/tax_code_save/plain_small.v3` (a hand-written plain-text excerpt, a few KB, holding two countries with `te_tax_*` variables, a variable list and a law with amendments, in the save's text syntax; copy the syntax from research H §1's notes).
- Modify: `scripts/analysis/save_country_probe.py` (a `read_lists()` for variable lists in binary saves, if research H §1 shows it is missing; and a clear message for a plain-text save instead of "ironman or corrupt"), `docs/guides/python_tools.md` (a row).

**Interfaces:** reads the schema groups from `docs/systems/tax_code_schema.md`'s tables at runtime, so a new token is reported without a code change. The history kind names come from `scripts/generators/gen_tax_code.py` `HISTORY_KIND_KEYS` plus the schema's kind list. The output groups are: enacted code, packages, draft and bill, obligations and trust, AI state, drift counters, history.

**Design:**
- **Text saves:** a streaming line scanner. It finds the `country_manager` → `database` → `<id>` blocks, and in each a `variables` block. It never parses the whole file and never holds it in memory beyond one country.
- **Binary saves:** go through `save_country_probe`'s existing decoder.
- **CLI:** `--country <TAG|name|id>`, `--diff A B`. The diff verdict per group is `same`, `changed` (lists names), or `missing on A/B`.

- [ ] **Step 1: Failing tests** against the fixture:
  - the enacted rates print as index and rate;
  - a package slot prints with its due month as year.month;
  - the history ring prints newest first with kind names;
  - `--diff` of the fixture against a copy with one changed token reports exactly that group as `changed`;
  - a plain-text save is never reported as "ironman or corrupt".
- [ ] **Step 2: Confirm they fail.** **Step 3: Implement.** **Step 4: The `python_tools.md` row.** **Step 5: `ruff check .` and the tests.**
- [ ] **Step 6: Commit:** `"Tax code save report: text and binary saves, per-group diff"`.

This task touches no Paradox file, so it can run in a separate worktree in parallel with Tasks 18–23. The controller merges it in.

---

### Task 25: Console setup events and the debug-tag index

**Goal:** The scenarios that need months of play become runnable from the console, and every `TE_TAX` log tag is documented and pinned by a test.

**Files:**
- Modify:
  - `events/te_tax_debug_events.txt`, with new console events `te_tax_debug.5` onwards:
    - S2, a package with a 1-month sunset due next month (it writes a bill record and runs `te_tax_store_package`, so a play-tester can watch January expiry and February replacement);
    - S3, a forced missed package (sets `te_tax_last_month` so the next dispatch skips; documents the console date jump);
    - S5, an external-version bump on wage (forces a held conflict);
    - naming a relief state on the console's selected state;
  - `docs/systems/tax_code_schema.md` § "Debug lines" (the full tag table: tag, what writes it, player-only or every country, which play-test reads it);
  - `test_tax_code_ai.py` (or a new `test_tax_code_log_tags.py`).

**Interfaces:** consumes the existing effects (`te_tax_store_package`, `te_tax_history_push`, the bill record fields). Produces the console ids the runbook cites.

- [ ] **Step 1: Failing test.** Collect every `TE_TAX <tag>` from `debug_log` strings in `common/` and `events/` (regex `"TE_TAX (\w+)`), then assert that the set equals the tags listed in the schema doc's Debug lines table.
- [ ] **Step 2: Confirm it fails.** **Step 3: Implement the events and the table.** Each event is console-only, gated `te_tax_code_in_force = yes`, with the `REVIEWED` orphan comment.
- [ ] **Step 4: Run all checks.**
- [ ] **Step 5: Commit:** `"Tax code: console setup events for the long scenarios; debug-tag index"`.

---

### Task 26: Deferred minors and system docs

**Goal:** The cheap open minors from research H §3 are fixed, and every system doc a later agent would look in names the tax code.

**Files** (all listed in research H §3 and §5):
- Fixes:
  - `localization/english/te_tax_l_english.yml`: the How text and the commencement concept say collections can change on the 2nd when another sync ran on the 1st; history kind-18 wording; the locked tab's `$je_tax_code$` splice; "Customs Levels";
  - the stale research citations in `docs/testing/tax-code-capability-ledger.md` and `docs/systems/tax_code_schema.md`;
  - `scripts/generators/gen_tax_code.py`'s docstring, and `docs/auto_generated_files.md`'s row (it imports `organize_loc` and `path_constants`; name every generated effect family including the AI ones).
- Docs:
  - `docs/systems/journal_entry_systems.md` (CRLF): a Tax Code section;
  - `docs/guides/gui_modding_guide.md` (CRLF): the right-click-menu and Budget gate rows;
  - the schema doc's Files table rows for every tax file, including the AI files;
  - `docs/README.md`: a `docs/testing/` index line;
  - `docs/systems/mod_systems.md`: the on-actions row and an AI line;
  - the root `README.md`: the rule bullet.
- Tests: whichever existing test pins a changed loc string.

- [ ] **Step 1:** List the minors to fix in the task report, each with research H's id and a code reference confirming it is still open.
- [ ] **Step 2:** Fix each one; run `organize_loc.py`, the loc checks and the tests that pin the strings.
- [ ] **Step 3:** Write the docs. For the two CRLF files, after editing, check that `grep -c $'\r$' <file>` equals `wc -l <file>`.
- [ ] **Step 4:** Run all checks.
- [ ] **Step 5: Commit:** `"Tax code: deferred minors; system docs name the tax code"`.

---

### Task 27: Evidence matrix, known limitations and the play-test runbook

**Goal:** The owner can play-test everything from one runbook, and the ledger shows, per release scenario, which checks give the evidence. No runtime gate is marked passed.

**Files:**
- Create: `docs/testing/tax-code-playtest.md`.
- Modify: `docs/testing/tax-code-capability-ledger.md` (the evidence matrix, the reconciled open-probe list, "Known limitations"), `docs/superpowers/plans/2026-09-30-legislated-tax-code.md` (§9 and §10 checkboxes: tick only what static work completed, each with a pointer; leave every runtime exit unticked), and `docs/superpowers/plans/2026-10-02-legislated-tax-code-tasks.md` (mark Task 17 as superseded by Tasks 25–27, and Task 16 as deferred to #674).

**Content:**
- **Runbook.**
  - Checks PT-01 onwards: research H's 37 deduplicated items, plus the AI checks:
    - S13a, an AI country in deficit legislates a T1 within about 8 months (watch `ai_introduced`, `ai_passed`; `te_tax_debug.4` shortcuts the streak);
    - S13b, an emergency T2;
    - S13c, offers accepted and the chain capped;
    - S13d, a withdrawal with a reason and one `ai_no_viable`;
    - S13e, a held package released or rescheduled;
    - S13f, the promise lines `obl_deadline` and `ai_obl_enacted`, and whether the AI's boosted institution grew;
    - S13g, rebels log once;
    - S13h, the ten-year observer run reading the `ai_year` lines;
    - P09b and P09c, the customs probe.
  - Each check gives: its setup (console ids), the steps, the expected `TE_TAX` tags, a save-report command where relevant, a result cell, and the scenario row it serves.
  - The runbook opens with the highest-risk order from the PR's 15 items.
  - It includes the script-profiler recipe: copy it from `git show 6815868c -- docs/guides/scripting_best_practices.md` (perf branch) and cite the commit.
- **Evidence matrix:** rows S1–S13 from package plan §10, each with its PT ids, an empty result cell and an evidence cell.
- **Known limitations:** research H §3's limitation items, plus the PR's parked ones, plus the AI ones:
  - AI customs is native plus adoption until P09b/c;
  - the promise boost reaches only countries whose political strategy does not score the institution, with enactment covering the rest;
  - enactment timing depends on P16.

- [ ] **Step 1:** Write the runbook and the ledger sections.
- [ ] **Step 2:** Check that every PT id in the matrix exists in the runbook and every runbook check maps to a row; write a small `grep` loop and quote its empty output in the report.
- [ ] **Step 3:** Run `check_post_load_rosters.py`, and a link check: `grep -o '](\.\./[^)]*)' docs/testing/*.md`, each path tested with `test -e`.
- [ ] **Step 4: Commit:** `"Tax code: play-test runbook, evidence matrix and known limitations"`.

---

### Task 28: Player guide chapter: Taxation (experimental)

**Goal:** Players can learn the tax code from the guide. The chapter prints as chapter 5, after Banking, and says what the rule does, how to legislate, how interest groups and promises work, what the AI does, and what is experimental.

**Files:**
- Create: `docs/player_guide/04-tax-code.md`. It sorts after `04-banking.md`; issue #682 renumbers the files later.
- Modify:
  - `docs/player_guide/README.md`: the index lists it as 5 and renumbers the later entries in the list only;
  - `01-introduction.md`: the rules row, linking the chapter;
  - `16-reference.md`: the system and rule rows;
  - `05-politics.md`: where it describes taxation laws, one sentence each that under the rule the tax code replaces them, linking the chapter;
  - `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`, rebuilt.

**Content:**
- Research H §4b's outline, filled with what was built. The AI section covers, in player terms:
  - when AI countries raise or cut;
  - that they negotiate with the same offers;
  - that they keep promises or renegotiate them;
  - that a promise they miss is enacted for them;
  - that their tariffs stay native under the customs option for now.
- **Names:** every UI name is quoted from loc, using research H §4c's key → text table; verify each against `localization/english/` before writing.
- **No carbon levy.** Customs is described as the experimental rule option. Nothing deferred is described as available.
- **Style:** follow `docs/player_guide/STYLE.md`, and run `python3 scripts/analysis/check_player_guide_style.py --strict`.
- **No screenshots:** the agents cannot take them. Add a commented placeholder line where one would help; check that the style lint allows HTML comments.

- [ ] **Step 1:** Write the chapter and the cross-file updates.
- [ ] **Step 2:** Run the style lint (strict) and fix every finding.
- [ ] **Step 3:** Rebuild: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/build_player_guide.py`, then `--check`.
- [ ] **Step 4:** Read the built chapter's text back (`pdftotext` on the chapter's pages, if available) and confirm the numbering shows chapter 5.
- [ ] **Step 5: Commit** the chapter and the PDF together: `"Player guide: Taxation (experimental) chapter"`.

---

### Task 29: Release gate (controller)

- [ ] Merge `origin/main`, and resolve a PDF conflict by rebuilding.
- [ ] Run every `ci.yml` step, `gen_tax_code.py --check` and the GUI lint on the tax GUI files.
- [ ] Have an independent whole-branch review run on Tasks 18–28's range: two parallel reviewers, script and docs, as at Task 17's time. Then one fix wave and a scoped re-review.
- [ ] Rewrite the PR #680 body with:
  - the summary of packages 1–7;
  - a "Player guide" line naming the chapter;
  - links to the runbook and the matrix;
  - the known limitations;
  - the owner questions, with question 1 restated for the AI's promise handling;
  - the test plan.
  
  Use `gh api -X PATCH` with a body file and verify it.
- [ ] Mark #680 ready for review. Merge only on the owner's word.
- [ ] Update the project memory and the SDD ledger.
