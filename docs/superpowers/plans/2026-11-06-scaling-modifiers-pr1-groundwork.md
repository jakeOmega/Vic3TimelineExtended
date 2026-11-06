# Scaling modifiers PR 1 (groundwork) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land §§ 1–3 of the design: `disable_evaluation` on every rule-gated mod journal entry, `fire_only_once` on 32 self-guarded events with a canary, the tooling that reads `scaling_modifiers_while_active` before its first use, and the retirement of `convert_je_outcomes.py`.

**Architecture:** Script edits in `common/journal_entries/`, five event files and one new on-action file. The tree checks move from the converter's test into a new `test_journal_entry_shape.py`, which also holds the prune and scaling-modifier checks. A new `test_once_only_events.py` pins the event conversion. `je_multiplier_scope_audit.py` gains a journal-entry pass.

**Tech Stack:** Paradox script (Victoria 3 1.15), Python 3.11/3.12 unittest/pytest, the repo's `je_multiplier_scope_audit.parse_text` node tree.

**Spec:** `docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md` (§§ 1–3, § 5's `fire_only_once_kept`)

## Global Constraints

- Brace files: tab indentation, exactly one UTF-8 BOM on every `.txt` touched or created; `python3 scripts/format_paradox_tabs.py --check <files>` clean.
- Python: `ruff check .` clean (`/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff`); no PEP 701 f-strings (CI runs 3.11).
- Use `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` for tests; no `POST /reload` from the worktree.
- Old-save removal date for kept guard reads: **after 2026-12-31** (the date the other old-save repairs carry).
- Canary names: marker global `te_fire_only_once_canary_armed`; log line prefix `TE_SELF_CHECK BROKEN fire_only_once_kept`.
- Player guide: no player-facing change (rule-off entries never showed; once-only events already fired once).

## Review Focus

1. **An add site that isn't behind the rule.** With the inactive record pruned, `add_journal_entry` of that type is no longer refused, so a rule-off game would get the entry. Task 2 makes each of the seven add sites read the rule in its own `limit` where it doesn't already.
2. **A save made before this change.** It holds the guard variables but no engine fire record: the events must stay closed there. Task 3's test pins each guard read (and the canary's `OR` form, which falls back to the guard when the marker is absent).
3. **A prune that reads something other than a game rule.** A variable set after the first tick would delete the entry for good. Task 2's `is_rule_test` accepts only `has_game_rule` and named triggers made of nothing else.
4. **A scaling block in a contextless entry.** Its value has no country root; Task 4's audit pass flags country reads there and only there.
5. **A converted key read with `has_modifier` or re-added.** Invisible or doubled; Task 5's misuse test, with `show_as_tooltip` previews and the legacy strip's remove-only lines allowed.

---

### Task 1: Journal entry shape tests replace the converter

**Files:**
- Create: `test_journal_entry_shape.py`
- Delete: `scripts/generators/convert_je_outcomes.py`, `test_convert_je_outcomes.py`
- Modify: `docs/guides/scripting_best_practices.md:1971,2977`, `docs/guides/vanilla_patch_runbook.md:154`, `docs/audits/vanilla_1_15_migration.md:49,212`

**Interfaces:**
- Produces (in `test_journal_entry_shape.py`): `ROOT: Path`; `DROPPED_FIELDS: frozenset[str]`; `load_entries() -> list[tuple[str, Node]]` (repo-relative path, top-level entry node, every `common/journal_entries/*.txt`, parsed with `je_multiplier_scope_audit.parse_text`); `child(node, key) -> Node | None`; `dropped_fields(entry: Node) -> list[str]` (sorted direct child keys in `DROPPED_FIELDS`).

- [ ] **Step 1: Write the tests.** `DROPPED_FIELDS` is the converter's `OLD_FIELDS | UNSUPPORTED` written out as a literal: `complete fail invalid on_complete on_fail on_invalid on_timeout custom_completion_header custom_on_completion_header custom_failure_header custom_on_failure_header event_outcome_completed_desc event_outcome_failed_desc event_outcome_timeout_desc event_outcome_completed_effect_desc event_outcome_failed_effect_desc event_outcome_timeout_effect_desc on_complete_all_involved on_fail_all_involved on_invalid_all_involved on_timeout_all_involved event_outcome_invalidated_desc event_outcome_invalidated_effect_desc`.
  - `test_dropped_fields_fixture`: `parse_text("je_x = {\n\ton_complete = { }\n\ttimeout = 5\n\toutcome = { }\n}\n", "j.txt")` → `dropped_fields(nodes[0]) == ["on_complete"]`.
  - `test_no_entry_keeps_a_field_vanilla_dropped`: `len(load_entries()) > 30`; each entry's `dropped_fields == []` (subTest per file/entry).
  - `test_every_entry_declares_activation_description`: skip keys starting `INJECT:`; `child(entry, "activation_description")` is not None. Keep the converter test's docstring reason.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest test_journal_entry_shape.py -q` → 3 passed.
- [ ] **Step 3: Delete the converter and its test;** `git grep -n convert_je_outcomes` lists only docs.
- [ ] **Step 4: Docs.** `scripting_best_practices.md:1971` names `test_journal_entry_shape.py`; `:2977` says the converter ran once for 1.15 and was retired (#1404; in git history), and keeps the `je_test_helpers.py` sentence. Runbook `:154`: "`test_journal_entry_shape.py` fails on an entry still in the old shape". Migration record `:49`: append "(retired with #1404; its tree checks live in `test_journal_entry_shape.py`)"; `:212`: mark the retirement done.
- [ ] **Step 5: Commit** "Retire convert_je_outcomes.py; its tree checks move to test_journal_entry_shape.py (#1404)".

### Task 2: `disable_evaluation` on rule-gated entries

**Files:**
- Modify: `test_journal_entry_shape.py`; the 15 entry files below; add sites in `common/scripted_effects/{gm_commission_effects,gm_effects,decolonization,nuclear_custody_effects,sr_colony_fleet_effects,sr_site_effects}.txt` as needed; `docs/guides/scripting_best_practices.md` § "1.15 journal entries, scaling modifiers and once-only events (probed)"; `docs/testing/vanilla-1-15-playtest.md` (Journal entries list)

**Interfaces:**
- Consumes: Task 1's `load_entries`, `child`.
- Produces: `load_triggers() -> dict[str, Node]` (top-level nodes of `common/scripted_triggers/*.txt`); `gate_conjuncts(entry: Node, triggers) -> list[Node]` (the direct children of `is_shown_when_inactive`, each followed by the top-level conjuncts of a named trigger it calls as `T = yes` or `T = { ARG = … }`, recursively, cycle-safe); `is_rule_test(node: Node, triggers) -> bool`; `prune_problems(entry: Node, triggers) -> list[str]`.

Rules the functions encode (spec § 1):
- `is_rule_test`: `has_game_rule = <x>`, or `T = yes` where every node of `T`'s body is a rule test or an `AND`/`OR`/`NOT` block of them.
- `prune_problems`: no `disable_evaluation` and some gate conjunct is a rule test → `"rule-gated entry has no disable_evaluation"`. With one: either its only child is `always = yes` and the gate's only child is `always = no`; or every child is `NOT` holding exactly one rule test whose `(key, value)` is among the gate conjuncts. Anything else → one message naming the offending child.

- [ ] **Step 1: Write failing fixture tests** (each builds nodes with `parse_text`, triggers from a fixture string):
  - `test_prune_of_a_gate_rule_is_sound`: gate `has_game_rule = r`, prune `NOT = { has_game_rule = r }` → `[]`.
  - `test_rule_gated_entry_without_prune_is_flagged`: gate `has_game_rule = r` → one problem containing `"no disable_evaluation"`.
  - `test_prune_rule_missing_from_gate_is_flagged`: gate `has_game_rule = r`, prune `NOT = { has_game_rule = s }` → one problem.
  - `test_prune_on_a_variable_is_flagged`: prune `NOT = { has_variable = x }` → one problem; and via a wrapper `w = { has_variable = x }` called `w = yes` (also a gate conjunct) → one problem.
  - `test_rule_pure_wrapper_is_a_rule_test`: `w = { OR = { has_game_rule = a has_game_rule = b } }`, gate `w = yes`, prune `NOT = { w = yes }` → `[]`.
  - `test_gate_read_through_a_parameterised_trigger`: `f = { w = yes has_variable = done_$P$ }`, gate `f = { P = x }`, prune `NOT = { w = yes }` → `[]`; and without a prune → flagged.
  - `test_always_yes_only_for_a_never_shown_entry`: gate `always = no` + prune `always = yes` → `[]`; gate `has_variable = x` + prune `always = yes` → one problem.
  - `test_not_with_two_children_is_flagged`: `NOT = { has_game_rule = r has_game_rule = s }` → one problem.
- [ ] **Step 2: Add the tree test** `test_every_entry_prune_is_sound`: `prune_problems(entry, load_triggers()) == []` for every entry. Run the file: the fixtures fail until Step 3; the tree test fails on 25 rule-gated entries after it.
- [ ] **Step 3: Implement** the four functions in `test_journal_entry_shape.py`. Fixture tests pass; the tree test lists the 25 unpruned entries.
- [ ] **Step 4: Add the prunes**, each right above `is_shown_when_inactive`, preceded by one comment line `# 1.15: with the rule off, drop the inactive record for good (a rule never changes mid-game).`:

  | Prune | Entries (file) |
  |---|---|
  | `NOT = { has_game_rule = social_movements_enabled }` | `je_civil_rights`, `je_post_scarcity`, `je_digital_rights`, `je_mental_health_crisis`, `je_morphological_freedom`, `je_human_augmentation` |
  | `NOT = { has_game_rule = cultural_hegemony_enabled }` | `je_cultural_hegemony` |
  | `NOT = { has_game_rule = covert_warfare_enabled }` | `je_covert_warfare` |
  | `NOT = { has_game_rule = nuclear_weapons_enabled }` | `je_nuclear_program` |
  | `NOT = { has_game_rule = decolonization_enabled }` | `je_colonial_empire` |
  | `NOT = { has_game_rule = united_nations_enabled }` | `je_united_nations` |
  | `NOT = { has_game_rule = heir_education_enabled }` | `je_heir_education` |
  | `NOT = { has_game_rule = custom_religions_allowed }` | `je_create_new_religion` (`timeline_extended_journal_entries.txt`) |
  | `NOT = { has_game_rule = world_war_enabled }` | `je_world_war` (`world_war_je.txt`) |
  | `NOT = { sr_space_race_on = yes }` | the 8 `je_space_race_*` except `moon_base` |
  | `always = yes` | `je_space_race_moon_base` |
  | `NOT = { gm_system_enabled = yes }` | `je_grand_monuments` |
  | `NOT = { te_tax_code_on = yes }` | `je_tax_code` |
  | `NOT = { te_banking_system_on = yes }` | `je_banking_cycle` |

- [ ] **Step 5: Run** the file → all pass; print the pruned set and check it is exactly the 26 entries above.
- [ ] **Step 6: Add sites read the rule.** For each `add_journal_entry` of a pruned type outside debug files (`te_banking_entry_on_actions.txt:68`, `decolonization.txt:1000`, `gm_commission_effects.txt:175`, `gm_effects.txt:748`, `nuclear_custody_effects.txt:375`, `sr_colony_fleet_effects.txt:244`, `sr_site_effects.txt:147`): if its enclosing `limit` (or the effect's own top-level `if`) doesn't already read the rule test from the table, directly or through a trigger that does, add it to that `limit`. Record which you changed in the commit message.
- [ ] **Step 7: Checks.** `python3 scripts/format_paradox_tabs.py --check` on every changed `.txt`; `head -c3` shows one BOM each; `python3 effect_trigger_validity_audit.py --strict` exit 0.
- [ ] **Step 8: Docs.** One bullet in the best-practices § 1.15 section: the mod prunes only on game rules (`test_journal_entry_shape.py` holds it to the gate), and the record's deletion makes `add_journal_entry` succeed, so add sites read the rule. One play-test bullet: in a rule-off game (social movements, say) none of those entries shows; in a rule-on game every entry appears as before and Banking's dormant entry is on every country.
- [ ] **Step 9: Commit** "Journal entries: disable_evaluation on the 25 rule-gated entries and the retired Moon Base (#1404)".

### Task 3: `fire_only_once` on 32 events, with the canary

**Files:**
- Create: `test_once_only_events.py`, `common/on_actions/te_fire_only_once_selfcheck_on_actions.txt`
- Modify: `events/society_technology_events.txt`, `events/te_judiciary_events.txt`, `events/cultural_hegemony_events.txt`, `events/post_scarcity_events.txt`, `events/surveillance_events.txt`, `test_judiciary.py:834-835`, `common/on_actions/te_judiciary_on_actions.txt:179`, `docs/systems/mod_systems/judiciary.md:21`, `docs/systems/mod_systems/social_movements.md:49`, `docs/guides/scripting_best_practices.md` (same § 1.15 section), `docs/testing/vanilla-1-15-playtest.md` (C20 line)

**Interfaces:**
- Produces: `ONCE_ONLY: dict[str, tuple[str, str]]` (event id → (repo-relative file, guard variable)); `CANARY_EVENT = "society_technology_events.1"`; `CANARY_MARKER = "te_fire_only_once_canary_armed"`.

`ONCE_ONLY` holds: `society_technology_events.<n>` → `ste_event_<n>_fired` for n in 1–6, 9, 12, 13, 16, 17, 19–21, 25–31; `te_judiciary_events.30`–`.36` → `te_jud_heard_` + `free_soil`, `otsu`, `freedom_of_contract`, `voided_election`, `necessity`, `house_of_justice`, `new_code`; `cultural_hegemony.8` → `ch_milestone_significant`, `.9` → `ch_milestone_dominant`; `post_scarcity_events.3` → `ai_bureaucracy_debate_happened`; `surveillance_events.4` → `ai_predictive_policing_debate_happened`. 32 entries.

- [ ] **Step 1: Write the failing tests** (event bodies via `je_test_helpers.strip_comments` + `entry_text`, `field`):
  - `test_32_events`: `len(ONCE_ONLY) == 32`.
  - `test_each_event_fires_once`: body has a top-level `fire_only_once = yes`; for every event but the canary, `set_variable = <guard>` appears nowhere in the body, and the trigger still contains `NOT = { has_variable = <guard> }`.
  - `test_guard_variables_have_no_other_reader`: each guard name appears in `common/` and `events/` only inside its own event (comments stripped) — the condition that made it safe to convert.
  - `test_canary_falls_back_to_its_guard_in_old_saves`: the canary's trigger contains `OR = { has_global_variable = te_fire_only_once_canary_armed NOT = { has_variable = ste_event_1_fired } }` (whitespace-normalised) and no bare `NOT = { has_variable = ste_event_1_fired }` outside it.
  - `test_canary_logs_a_second_firing_before_marking`: its `immediate` has an `if` whose `limit` reads both `has_global_variable = te_fire_only_once_canary_armed` and `has_variable = ste_event_1_fired` around a `debug_log` starting `"TE_SELF_CHECK BROKEN fire_only_once_kept`, and that `if` comes before `set_variable = ste_event_1_fired`.
  - `test_canary_is_armed_only_at_game_start`: the new on-action file hooks `on_game_started` to `te_fire_only_once_canary_arm`, whose effect is `set_global_variable = te_fire_only_once_canary_armed`; no other file sets the marker.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest test_once_only_events.py -q` → all but `test_32_events` and `test_guard_variables_have_no_other_reader` fail.
- [ ] **Step 3: Edit the 31 events.** Add `fire_only_once = yes` after `type = country_event`'s block of header fields (beside `duration`/`cooldown`); delete the `set_variable = <guard>` line (and an `immediate` left empty); put `# pre-1.15 saves hold the variable but no fire record; remove after 2026-12-31` on the guard line.
- [ ] **Step 4: The canary.** In `society_technology_events.1`: `fire_only_once = yes`; the guard becomes the `OR` above; `immediate` gets the logging `if` before the existing `set_variable`, logging `"TE_SELF_CHECK BROKEN fire_only_once_kept (society_technology_events.1 fired a second time for one country in a game started after #1404: the engine's fire record didn't survive a save and load or pass to a revolution's winner; put the guard variables back, docs/testing/vanilla-1-15-playtest.md C20)"`. Create the on-action file (BOM, tabs) with a header in the style of `te_decentralized_laws_selfcheck_on_actions.txt`: what it arms, what BROKEN means, the fallback, "delete this file and the canary's `OR` once C20 is answered".
- [ ] **Step 5: Run** the file → all pass. Update `test_judiciary.py:834-835` to assert `fire_only_once = yes` in the event and the guard read in its trigger; run `test_judiciary.py`, `test_legacy_event_integration.py`, `test_automation_policy.py`, `test_cultural_hegemony_layout.py` → pass.
- [ ] **Step 6: Docs and comments.** `te_judiciary_on_actions.txt:179` and `judiciary.md:21` say "once per country (`fire_only_once`)"; `social_movements.md:49` lists the two AI debates as `fire_only_once` (the others keep their real gates, verify each name before writing); best-practices § 1.15 gets the convention (guard read kept for old saves until the removal date, the canary); play-test C20 line names the canary, BROKEN-only, and its fallback.
- [ ] **Step 7: Checks** as Task 2 Step 7, plus `python3 orphaned_event_audit.py --strict` and `python3 event_context_audit.py --strict` exit 0.
- [ ] **Step 8: Commit** "Events: fire_only_once on 32 self-guarded events, with a canary for save/load and revolutions (#1404)".

### Task 4: Audits read `scaling_modifiers_while_active`

**Files:**
- Modify: `je_multiplier_scope_audit.py`, `test_je_multiplier_scope_audit.py`, `test_effect_trigger_validity_audit.py`, `docs/guides/python_tools.md:61`

**Interfaces:**
- Produces: `scan_journal_entries(nodes, comments, definitions, country_triggers, links) -> list[Flag]` in `je_multiplier_scope_audit.py`; `Flag.line` is the `value` line, `Flag.journal_entry` the entry key, `Flag.modifier` the block's `modifier`.

- [ ] **Step 1: Failing tests** in `test_je_multiplier_scope_audit.py` (a `scan_je(text, values="")` helper mirroring `scan`):
  - `test_scaling_value_in_a_country_entry_is_not_flagged`: `je_x = { scaling_modifiers_while_active = { modifier = m value = { value = gdp } } }` → `[]`.
  - `test_scaling_value_in_a_contextless_entry_flags_country_reads`: same with `context = none` → one flag, `read == "gdp"`, `modifier == "m"`, `journal_entry == "je_x"`, `line` = the `value` line.
  - `test_scaling_value_follows_named_values`: contextless, `value = sv`, values `sv = { value = income }` → read `income`, chain `("sv",)`.
  - `test_scaling_value_reviewed_comment_suppresses`: `# REVIEWED 2026-11-06: x` on the value line → the flag carries an exemption.
  - `test_audit_reads_journal_entry_files`: temp mod with only a contextless entry file → `audit(mod_path=…)` finds the flag (the file holds no `add_modifier`).
- [ ] **Step 2: Implement** `scan_journal_entries`, call it from `audit()` for `common/journal_entries/` files, and keep those files when they contain `scaling_modifiers_while_active`. Docstring gains one paragraph (spec § 3's wording: root is the owning country; contextless entries flagged).
- [ ] **Step 3: Validity audit fixture** `test_115_scaling_modifier_block_passes` in `test_effect_trigger_validity_audit.py`: a mod entry with `disable_evaluation`, a block-form `value` (`value`, `if = { limit = { has_variable = v } add = var:v multiply = 2 max = 5 }`, `min = 0`) and a named-value form → no flags.
- [ ] **Step 4: Run** both test files → pass; `python3 je_multiplier_scope_audit.py --strict` exit 0. Update `python_tools.md:61`.
- [ ] **Step 5: Commit** "je_multiplier_scope_audit reads scaling_modifiers_while_active; validity audit pinned on the block (#1403, #1404)".

### Task 5: A declared scaling modifier exists and isn't added or tested by hand

**Files:**
- Modify: `test_journal_entry_shape.py`, `docs/guides/scripting_best_practices.md` (the § 1.15 `has_modifier` bullet gains the test's name)

**Interfaces:**
- Consumes: Task 1's `load_entries`, `child`.
- Produces: `scaling_declarations(entries) -> dict[str, list[tuple[str, int, str]]]` (modifier → (file, line, entry)); `static_modifier_names() -> set[str]` (mod `common/static_modifiers/*.txt` top-level keys with `INJECT:`/`REPLACE:` stripped, ∪ keys of `vanilla_parsed/common/modifiers.json`); `LEGACY_STRIP_FILE = "common/scripted_effects/legacy_modifier_cleanup.txt"`; `misuse_sites(nodes, declared: set[str], rel: str) -> list[tuple[str, int, str, str]]` (file, line, kind, modifier).

`misuse_sites` kinds: `has_modifier = X`; `add_modifier = X` or `add_modifier = { name = X … }` unless an ancestor is `show_as_tooltip`; `remove_modifier = X`; `remove_modifier_if_exists_effect = { MODIFIER = X }`. In `LEGACY_STRIP_FILE` only `add_modifier` counts. GUI: a `gui/**/*.gui` line holding `HasModifier` and a declared name.

- [ ] **Step 1: Failing fixture tests:** `has_modifier = m` flagged; `add_modifier = { name = m multiplier = 2 }` flagged; inside `show_as_tooltip = { add_modifier = { name = m } }` not; `remove_modifier_if_exists_effect = { MODIFIER = m }` flagged; in `LEGACY_STRIP_FILE` `has_modifier`/`remove_modifier` not flagged but `add_modifier` is; `has_modifier = other` not flagged. `scaling_declarations` on a two-block fixture entry returns both modifiers with their lines.
- [ ] **Step 2: Tree tests:** `test_every_scaling_modifier_exists` (each declared name in `static_modifier_names()`; also assert that set holds `base_values` and one mod key such as `nuclear_weapon_program_funding`, so an empty load can't pass); `test_no_scaling_modifier_is_added_or_tested` over `common/**/*.txt`, `events/**/*.txt` and `gui/**/*.gui`. Both pass vacuously until PR 2 declares one.
- [ ] **Step 3: Implement**, run the file → pass.
- [ ] **Step 4: Commit** "Journal entry shape: a scaling modifier must exist and is never added, removed or tested by hand (#1404)".

### Task 6: Gate and PR

- [ ] **Step 1:** `.venv/bin/python -m pytest -q test_journal_entry_shape.py test_once_only_events.py test_je_multiplier_scope_audit.py test_effect_trigger_validity_audit.py test_judiciary.py test_legacy_event_integration.py test_automation_policy.py test_cultural_hegemony_layout.py test_tax_code_bypass.py test_nightly_audit_select.py` → pass; `ruff check .`; `scripts/format_paradox_tabs.py --check` over changed `.txt`; `python3 scripts/analysis/check_post_load_rosters.py`; the `--strict` audits from CI that read events and entries (`effect_trigger_validity`, `je_multiplier_scope`, `orphaned_event`, `event_context`, `je_immediate_reset`, `empty_effect`) with the dummy `VIC3_*` env vars.
- [ ] **Step 2:** Push, open the PR to `main` (body: what each part does and why, the canary, "Player guide: no player-facing change", "Part of #1404; one item of #1403" — no closing keyword), start an independent review in parallel, fold its findings in as commits.
- [ ] **Step 3:** File the issues the design promised: the outcome splits ("split all three"), each § 4.4–4.11 / § 7 prep-doc feature left out, and the side finding (`te_monetary_settle_modifier_home` omits `te_mon_union_banking_union`, `te_mon_union_reserve`, `te_mon_union_seigniorage`).
