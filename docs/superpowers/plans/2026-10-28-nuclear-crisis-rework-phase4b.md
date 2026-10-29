# Nuclear Crisis Rework, Phase 4b: Four New Disputes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four new crisis disputes from spec §8.5: deployment (7), claims (8), covert operations (9) and orbital weapons (10), each with a concession, its texts and the AI's opening rule.

**Architecture:** Dispute 6 (`git show 08606c453`) is the template. Each code gets a `nd_dispute_<name>` trigger and a branch in every dispute dispatcher. Its concession runs from `nd_crisis_act_yield`, and a timed variable on the target bars a quick undo for ten years. A table-driven test (`test_nuclear_disputes.py`) names every dispatcher and fails on any code that one of them lacks. The fallbacks silently treat a missing code as dispute 5, and that test is what catches it.

**Tech Stack:** Paradox script (Victoria 3 1.14), Python `unittest` tests that read the script.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` §8.5 and §9. Also read `docs/systems/nuclear_crisis_design.md` §0.3 (what shipped) and §0.15 (phase 4a). Survey notes: `.superpowers/sdd/phase4b_notes.md`. Its line numbers predate 4a, so find blocks by name.

## Global Constraints

- Classification order: **2, 1, 3, 6, 4, 7, 8, 9, 10, 5** (spec §8.5).
- AI (spec §9): it opens codes 6–9 defensively, and code 10 only as a great power.
- Every bar and freeze lasts **ten years** (`days = 3650`), the length of the proliferation freeze.
- Tab-indented Paradox files, with exactly one UTF-8 BOM on each `.txt` and loc file. Loc is American English and uses `#v X#!` markup, never `[b]`.
- Stage by path. `journal_entry_systems.md` is CRLF. Never hand-edit generated files. Never `POST /reload` from the worktree.
- Commits end with the two attribution lines, and the PR body with its two.

## Rulings made in this plan

The owner is away and asked for calls to be made and listed at the end. Each of these goes in the ledger at setup.

- **R1. Trades (§8.6) are phase 4c.** They are a different kind of work: outcome 11 across eight sites, panel ops for both roles, an accept event, and AI acceptance the spec leaves open. "Same weights as §8.2" exist only for war goals, the issuer of a freeze-for-freeze is always armed, and stand-down for stand-down is already outcome 3. Cost: a fifth PR.
- **R2. The umbrella is not part of code 7.** Every direct subject of an armed overlord is under its umbrella by default, so an umbrella over a country next to us is geography, not a deployment. A withdrawal also wouldn't hold: the AI's `will_break` restores it at once (`nuclear_umbrella_actions.txt`). Cost: an overlord's cover over a subject next to us is no dispute. The owner can revert this.
- **R3. Code 7's basing clause is "the target is in our `nd_based_near` list."** That is 4a's weekly list of armed guests based in a host that `is_adjacent_to_country` us, so a basing article is a dispute exactly when it cuts our warning time. Cost: the dispute starts up to a week late.
- **R4. A guarantee over a country next to us uses `is_adjacent_to_country`**, not `has_strategic_adjacency`. War-goal adjacency would make a guarantee over anyone we hold a goal against a "deployment."
- **R5. Missile defense covers both production methods of `pmg_military_base_missile_defense`**: the battery and directed-energy point defense, its successor in the same slot.
- **R6. A bar is a timed variable on the target holding the issuer.** It is inherited by a revolution's winner (variables are, modifiers aren't) and needs no Nation tab row.
  - Codes and bars: `nd_crisis_deploy_bar` (7), `nd_crisis_covert_bar` (9), `nd_crisis_orbital_freeze` (10).
  - A second concession to another issuer overwrites the first (one crisis at a time).
  - Cost: the earlier issuer's bar ends early.
- **R7. Native closes.**
  - A war between the two turns codes 7–10 into dispute 2, as dispute 6 does.
  - Code 8 closes with outcome 10 when no claim is left: a claim can't be renewed at will (no vanilla or mod action adds one on a neighbor's land), so it is gone for good.
  - Codes 7, 9 and 10 don't close when the target pulls back on its own. It could start again at once, so, as with the alert dispute, what the issuer demands is the concession and its bar.
  - Cost: a crisis can run on after the deployment, operation or site is gone, and yielding then costs the target only the bar.
- **R8. The AI.**
  - Codes 7, 8 and 9: the AI warns over them only against a rival (`has_diplomatic_pact = { who = $TARGET$ type = rivalry }`), and a cautious ruler not at all.
  - Code 10: only a great power warns over it.
  - All four are damped by the taboo (no exemption) and get no `propose_score` bonus.
  - The reason is that claims and covert operations are common. Without the rival rule an armed AI would threaten over every one.
  - Cost: the AI never threatens a non-rival over them.
- **R9. Codes 7, 8 and 9 count as defensive in `nd_crisis_issuer_is_defensive`; code 10 does not.** A stand-down over a neighbor's deployment, our own land or operations against us achieves the issuer's aim. A demand over someone's battlestation is not defense.
- **R10. The deployment concession withdraws the target from each treaty involved with no break penalties.** That is `withdraw`'s default (engine `effects.log`), and the climb-down is the cost. The tooltip says the whole treaty ends.
- **R11. The covert concession ends the operations the issuer has detected**: the issuer's `iw_known_ops` records naming the target as attacker, hostile types only. Operations it hasn't caught go on. The bar stops new hostile operations against the issuer.
- **R12. Under an Existential doctrine, codes 7–10 are bluffs** (follow-through reason 5). `nd_threat_existential_stake` is unchanged: none of them threatens survival.
- **R13. Codes 7–10 have no stakes part.** Stakes read a play's war goals (§8.2), and these disputes have none.

## Review Focus

1. A split state region: a claim on a region we share with a third country. `remove_claim` drops the target's claim on the whole region, so the tooltip must say so. Test: `test_claims_concession_names_the_whole_region`.
2. The covert concession over a list it changes. It must never `every_in_list` the `iw_ops` it destroys; it goes type by type. Test: `test_covert_concession_goes_type_by_type`.
3. A conceded battery switched back on. The weekly update turns it off again while the bar holds. Test: `test_deploy_bar_switches_batteries_off_weekly`.
4. A yield with nothing left to remove. The self-check must not report OK falsely, so it is scheduled only when the dispute held at the yield. Test: `test_concession_selfcheck_skips_an_empty_yield`.
5. The basing and guarantee articles read the bar through `scope:source_country` in `can_ratify`. Test: `test_articles_refuse_a_barred_guest`.

## Per-code site list

Every code task touches all of these. `test_nuclear_disputes.py` (Task 1) checks each one.

| # | Site | File | What a code adds |
|---|---|---|---|
| a | `nd_dispute_<name> = { TARGET }` | `nuclear_deterrence_triggers.txt`, after `nd_dispute_peacetime_strike_by` | the dispute; issuer scope, `save_temporary_scope_as` first |
| b | `nd_has_crisis_dispute_with` | same | an OR line |
| c | `nd_crisis_classify_dispute` | `nuclear_crisis_effects.txt` | an `else_if` after code 4, in order, before the `else` |
| d | `nd_crisis_revalidate_dispute` | same | an `else_if` on `var:nd_crisis_dispute = N` (R7) |
| e | `nd_crisis_act_yield` | same | an `else_if` that calls `nd_crisis_concession_check_schedule = { CODE = N }` inside an `if` on `nd_dispute_<name>`, then `nd_crisis_concede_<name>` |
| f | `nd_crisis_yield_lines` | same | `nd_crisis_dispute_is = { D = N }` → `nd_tt_yield_<name>` |
| g | `nd_crisis_preview` "about" | same | `nd_dispute_<name>` → `nd_tt_open_over_<name>`, before the alert `else` |
| h | custom loc `nd_crisis_dispute_phrase`, `_dispute_word`, `_demand_text`, `_concession_past` (they and we), `_concession_short`, `_concession_long` | `nuclear_deterrence_custom_loc.txt` | a `text` per block, trigger `nd_crisis_dispute_is = { D = N }` (`_past` keeps its they/we split), keys `<prefix>_N` |
| i | `nd_crisis_issuer_is_defensive` | triggers | `var:nd_crisis_dispute = N` for 7, 8, 9 (R9) |
| j | `nd_ai_would_warn` | triggers | the licence OR (R8) |
| k | `nuclear_crisis.26`, the concession self-check | `events/nuclear_crisis_events.txt` | a branch on `var:nd_cc_code = N` |
| l | prose lists `nd_tt_has_dispute`, `nd_w_crisis_actions_legend` | `te_miscellaneous_l_english.yml` | the dispute named |
| m | loc keys | `te_miscellaneous_l_english.yml` | `nd_tt_yield_<name>`, `nd_tt_open_over_<name>`, `nd_crisis_dispute_phrase_N`, `nd_crisis_dispute_N`, `nd_crisis_demand_N`, `nd_concession_past_they_N`, `nd_concession_past_we_N`, `nd_concession_short_N`, `nd_concession_long_N` |

Names: 7 `deployment`, 8 `claims`, 9 `covert_ops`, 10 `orbital`.

---

### Task 1: The dispatcher table and the concession self-check

**Files:** Create `test_nuclear_disputes.py`. Modify `common/scripted_effects/nuclear_crisis_effects.txt` (new `nd_crisis_concession_check_schedule`) and `events/nuclear_crisis_events.txt` (new hidden `nuclear_crisis.26`).

**Interfaces:**
- Produces:
  - `DISPUTES`: an ordered list of `(code, trigger_name, word)` in classification order. Codes 1–6 are present; 5 is last and is the `else`.
  - `nd_crisis_concession_check_schedule = { CODE = N }`, issuer scope with `scope:nd_target` set. Once a game per code (global `nd_cc_done_N`), it sets `nd_cc_target = scope:nd_target` and `nd_cc_code = N` for 10 days and fires hidden `nuclear_crisis.26` a day later. Each new code's yield branch calls it inside an `if` on its own dispute trigger, before the concession, so a yield with nothing to remove is never checked.
  - `nuclear_crisis.26` (issuer scope, `trigger = { has_variable = nd_cc_target }`) logs `TE_SELF_CHECK OK|BROKEN nd_concession_<N>` with both names, then removes both variables. This is `nuclear_crisis.25`'s pattern.

- [ ] **Step 1: Write the tests.** In `TestDispatchers`:
  - `test_classification_order`: the `value = N` writes in `nd_crisis_classify_dispute` come in `DISPUTES` order, 5 last and inside the `else`.
  - `test_every_dispatcher_names_every_code`: rows c–i of the site list, each checked for every code. Code 5 is exempt where it is the `else`. The yield exempts 1–3, which go through `nd_crisis_concede_play`/`_war`.
  - `test_eligibility_names_every_trigger`: row b.
  - `test_loc_keys_exist`: row m, for codes 6 and up.
  - `test_prose_lists_name_every_dispute`: row l, by each code's word.

  In `TestConcessionCheck`:
  - `test_concession_selfcheck_skips_an_empty_yield`: in the yield, each new code's schedule call sits inside an `if` on its own dispute trigger, before its concession. It is checked per code from Task 2 on.
  - `test_selfcheck_is_once_a_game_per_code`: a global flag per code.
  - `test_selfcheck_line_format`.

  Use `block`, `strip_comments`, `read` and `loc_value` from `test_nuclear_deterrence.py`.
- [ ] **Step 2: Run.** `env -u PYTHONPATH ../Vic3TimelineExtended/.venv/bin/python -m pytest -q -p no:cacheprovider test_nuclear_disputes.py`. Expected: `TestDispatchers` passes on codes 1–6, since it describes what exists. `TestConcessionCheck` FAILS, because the event doesn't exist yet.
- [ ] **Step 3: Implement** the schedule effect and `.26`. `.26` has no branches yet; every code task adds its own.
- [ ] **Step 4: Run** the test file and `test_nuclear_deterrence.py test_nuclear_crisis_pacing.py`, then the audit gate (`bash $SP/gate_audits_p4.sh`). Expected: PASS, `fail=0`.
- [ ] **Step 5: Commit** "Nuclear crises: a dispatcher table test and a concession self-check (phase 4b)".

### Task 2: Code 8, claims

**Files:** the site list, `test_nuclear_disputes.py`.

- `nd_dispute_claims_by = { TARGET }`: `any_scope_state = { is_incorporated = yes state_region = { $TARGET$ = { has_claim = PREV } } }`. The claim sits on the region; this is `extra_on_actions.txt`'s decentralized-claims pattern.
- `nd_crisis_concede_claims`: `scope:nd_issuer = { every_scope_state = { limit = { <the same test against scope:nd_target> } state_region = { remove_claim = scope:nd_target } } }`. There is no bar (R7).
- Revalidate (R7): a war turns it into 2. No claim left → `OUTCOME = 10`.
- AI (R8): `AND = { nd_dispute_claims_by = { TARGET = $TARGET$ } has_diplomatic_pact = { who = $TARGET$ type = rivalry } }`.
- Texts: the word is "Territorial claims". The demand is "renounce its claims on our states". `nd_concession_long_8` and `nd_tt_yield_claims` say that a claim on a region we share goes for the whole region.

- [ ] **Step 1: Tests.**
  - Add `(8, "nd_dispute_claims_by", "claims")` to `DISPUTES`, which turns `TestDispatchers` RED.
  - Add `TestClaims`:
    - `test_trigger_reads_the_region` (`is_incorporated = yes`, `has_claim = PREV`);
    - `test_concession_removes_on_the_region`;
    - `test_claims_concession_names_the_whole_region` (the word "region" in both texts);
    - `test_revalidate_closes_when_no_claim_is_left`;
    - `test_ai_warns_only_against_a_rival`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** rows a–m for code 8.
- [ ] **Step 4: Run** the tests, gate, `organize_loc.py` (then `--check`), `check_localization_files.py` and `check_loc_spelling.py --check`. Expected: PASS and clean.
- [ ] **Step 5: Commit** "Nuclear crises: a claim on our land is a dispute (code 8)".

### Task 3: Code 10, orbital weapons

**Files:** the site list, `common/buildings/extra_buildings.txt` (the site's `possible`), `test_nuclear_disputes.py`.

- `nd_dispute_orbital_by = { TARGET }`: `$TARGET$ = { any_scope_state = { has_building = building_orbital_battlestation_construction_site } }`. The battlestation grants nuclear defense to every state its owner holds (`mod_systems.md`, strike odds), so it weakens deterrence. That answers the spec's "design pass" note. Ledger this as a ruling.
- `nd_crisis_concede_orbital`: in each of the target's states with the site, `remove_building = building_orbital_battlestation_construction_site` and `set_variable = { name = orbital_battlestation_progress_var value = 0 }` (the wonder helper's own completion sequence, `extra_effects.txt`). Then `set_variable = { name = nd_crisis_orbital_freeze value = scope:nd_issuer days = 3650 }` on the target.
- In the site's `possible`: `custom_tooltip = { text = nd_tt_orbital_frozen owner = { NOT = { has_variable = nd_crisis_orbital_freeze } } }`.
- Revalidate (R7): a war turns it into 2. Nothing else.
- AI (R8): `AND = { nd_dispute_orbital_by = { TARGET = $TARGET$ } country_rank >= rank_value:great_power }`. It is not defensive.
- Texts: the word is "Orbital weapons". The demand is "tear down its battlestation site and build none for ten years". Completed battlestation levels stay, and the long text says so.

- [ ] **Step 1: Tests.**
  - Add `(10, "nd_dispute_orbital_by", "orbital")`.
  - Add `TestOrbital`:
    - `test_concession_removes_site_and_progress`;
    - `test_freeze_is_ten_years_and_read_by_the_site`;
    - `test_not_defensive`;
    - `test_ai_great_power_only`;
    - `test_finished_levels_stay` (the long text says completed levels stay).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** rows a–m and the `possible` line.
- [ ] **Step 4: Run** as in Task 2. Expected: PASS and clean.
- [ ] **Step 5: Commit** "Nuclear crises: an orbital battlestation under construction is a dispute (code 10)".

### Task 4: Code 9, covert operations

**Files:** the site list, `common/diplomatic_actions/covert_operations.txt` (the bar on the hostile actions' `possible`), `test_nuclear_disputes.py`.

- `nd_dispute_covert_ops_by = { TARGET }` (R11): `has_variable_list = iw_known_ops any_in_list = { variable = iw_known_ops var:iw_attacker ?= $TARGET$ NOT = { has_tag = iw_known_counterintel_support } }`. A record goes with its operation (`covert_op_destroy`, `covert_op_sync`'s reap), so "recorded" means "running and detected."
- `nd_crisis_concede_covert_ops`, target scope: one `nd_crisis_end_known_op = { TYPE = <short> ACTION = <action> }` per hostile type, 17 calls, in `covert_watch_start`'s order.
  - The helper: `if = { limit = { has_diplomatic_pact = { who = scope:nd_issuer type = $ACTION$ } scope:nd_issuer = { any_in_list = { variable = iw_known_ops var:iw_attacker ?= scope:nd_target has_tag = iw_known_$TYPE$ } } } remove_diplomatic_pact = { country = scope:nd_issuer type = $ACTION$ } covert_op_destroy = { TYPE = $TYPE$ TARGET = scope:nd_issuer } }`.
  - Then `set_variable = { name = nd_crisis_covert_bar value = scope:nd_issuer days = 3650 }`.
- Each of the 17 hostile actions' `possible` gets, after `iw_no_truce_tt`: `custom_tooltip = { text = nd_tt_covert_conceded NOT = { var:nd_crisis_covert_bar ?= scope:target_country } }`. Counterintelligence Support doesn't get it.
- Revalidate (R7): a war turns it into 2. Nothing else.
- AI (R8): the rival-only line, as for code 8.
- Texts: the word is "Covert operations". The demand is "end the operations we have caught and start none against us for ten years". The long text says operations we haven't caught aren't covered.

- [ ] **Step 1: Tests.**
  - Add `(9, "nd_dispute_covert_ops_by", "covert operations")`.
  - Add `TestCovert`:
    - `test_covert_concession_goes_type_by_type`: 17 helper calls, no `every_in_list` in the concession, and the type list equal to the hostile list in `is_hostile_covert_operation_pact`;
    - `test_bar_on_every_hostile_action`;
    - `test_no_bar_on_counterintel_support`;
    - `test_dispute_reads_the_issuers_records`;
    - `test_ai_warns_only_against_a_rival`.
  - Run `test_covert_op_registry.py` and `test_covert_stand_down.py` too.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Run `script_argument_audit.py --strict`.
- [ ] **Step 4: Run** as in Task 2, plus the covert tests. Expected: PASS and clean.
- [ ] **Step 5: Commit** "Nuclear crises: detected covert operations are a dispute (code 9)".

### Task 5: Code 7, deployment

**Files:** the site list, `common/treaty_articles/125_nuclear_basing.txt` and `115_nuclear_guarantee.txt` (`can_ratify`), `common/scripted_effects/nuclear_deterrence_effects.txt` (the weekly battery enforcement), `test_nuclear_disputes.py`.

- `nd_dispute_deployment_by = { TARGET }`, issuer scope, saving `nd_dd_self`. It holds when any of these does:
  - (R3) `is_target_in_variable_list = { name = nd_based_near target = $TARGET$ }`, guarded by `has_variable_list = nd_based_near`.
  - (R4) the target is the source of a `nuclear_guarantee` article whose target is not us and `is_adjacent_to_country = scope:nd_dd_self`. Read it through `$TARGET$ = { any_scope_treaty = { any_scope_article = { … source_country = $TARGET$ … } } }`.
  - (R5) the target has a state with `is_production_method_active = { building_type = building_military_base production_method = pm_missile_defense_battery }` or `pm_directed_energy_point_defense`, and `any_neighbouring_state = { owner = scope:nd_dd_self }`.
- `nd_crisis_concede_deployment`, target scope:
  - Leave every treaty whose `nuclear_basing` article has the target as source and a host adjacent to the issuer (`withdraw = { country = scope:nd_target }`, R10), and every treaty whose `nuclear_guarantee` article is from the target over a country adjacent to the issuer, other than the issuer.
  - In every state with either missile-defense method next to the issuer, `activate_production_method = { building_type = building_military_base production_method = pm_no_missile_defense }`.
  - Set `nd_crisis_deploy_bar = scope:nd_issuer` for 3650 days.
  - Schedule a reach rebuild for the target with `nuclear_weapon_events.32`, as the article hooks do.
- Bar readers:
  - `125_nuclear_basing.txt` `can_ratify`: `custom_tooltip = { text = nd_tt_deploy_barred scope:source_country = { NOT = { var:nd_crisis_deploy_bar ?= { is_adjacent_to_country = scope:target_country } } } }`.
  - `115_nuclear_guarantee.txt` `can_ratify`: the same line.
  - `nd_weekly_update`: `nd_deploy_bar_enforce` switches either method off in the target's states next to `var:nd_crisis_deploy_bar` while it is set.
- Revalidate (R7): a war turns it into 2. Nothing else.
- AI (R8): rival-only.
- Texts:
  - The word is "Forward deployment."
  - The demand is "end its nuclear basing and guarantees next to us, switch off its missile defense on our border, and make none of them again for ten years."
  - The long text and the yield line say that a treaty is left whole and that no break penalty applies.

- [ ] **Step 1: Tests.**
  - Add `(7, "nd_dispute_deployment_by", "deployment")`.
  - Add `TestDeployment`:
    - `test_three_clauses` (the list, the guarantee adjacency, both PMs);
    - `test_no_umbrella_clause` (R2);
    - `test_concession_withdraws_without_penalties` (`withdraw = { country = scope:nd_target }`, no `apply_break_penalties`, "treaty" and "penalt" in the texts);
    - `test_concession_switches_both_methods_off`;
    - `test_articles_refuse_a_barred_guest`;
    - `test_deploy_bar_switches_batteries_off_weekly`;
    - `test_reach_rebuilt_after_the_concession`;
    - `test_ai_warns_only_against_a_rival`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** as in Task 2, plus `test_nuclear_basing.py test_nuclear_reach.py`. Expected: PASS and clean.
- [ ] **Step 5: Commit** "Nuclear crises: forward deployment next to us is a dispute (code 7)".

### Task 6: Docs, the gate, the PR and the review

**Files:**
- `docs/systems/nuclear_crisis_design.md`: a new §0.16, and §0.3's dispute table.
- `docs/player_guide/14-nuclear.md`: the dispute table and the AI paragraph. `17-reference.md` if the glossary names disputes. Rebuild the PDF.
- `docs/testing/nuclear-playtest.md`: items 55 and on, plus a `nd_concession_<N>` self-check row naming each code's fallback.
- `docs/systems/mod_systems.md`: the crisis paragraph.
- `docs/systems/journal_entry_systems.md` (CRLF): the crisis area line.
- The spec's status line: 4b built, trades are 4c.
- `docs/guides/scripting_best_practices.md`: any lesson.

Play-test items to write:
- A claims concession on a split region.
- A covert concession, then a relaunch refused.
- A battery switched back on, then off again within the week.
- A basing withdrawal inside the binding period (refers to item 53).
- A site torn down and a new one refused.
- The AI's warnings: how many of the new codes appear in an observer run.

- [ ] **Step 1:** Write the docs and rebuild the guide (`build_player_guide.py`, then `--check`, and the style lint `--strict`).
- [ ] **Step 2:** The full gate: audits, ruff, tabs `--check`, loc checks, GUI lint, the roster check, and the full suite (`pytest -n auto`).
- [ ] **Step 3:** Commit, push, and open the PR with `--base main`. The body has a "Player guide" line, and the rulings go in a PR comment.
- [ ] **Step 4:** The two-reviewer final review, then one fix pass with each fix tested first, then the full suite.
- [ ] **Step 5:** Merge on green CI. Then the ledger, memory, and the final message.
