# Nuclear Delivery and Survivability, Phase 1 (Survivability and Display) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship spec phase 1. Survivability becomes a product of its parts in place of the flat ceiling, and precision weapons weaken silos. Every delivery read goes through one trigger per leg, still reading the technologies. Fixed on the way: a landlocked country's submarine reach. Then every value a nuclear decision rests on is shown where the decision is made (§3, §5, owner calls 6–8, 10, 13, 14).

**Architecture:**
- **Two triggers stand for the hardware.** `nd_fields_icbms` and `nd_fields_missile_submarines` answer "does this country have that leg?" for every reader. In phase 1 they read the technologies (submarines also need a coastal state); phase 2 swaps their bodies for the fielded variables and touches nothing else.
- **The ceiling becomes a target.** `nd_survivability_target` is 100 × (1 − the product of five exposure factors) and replaces `nd_survivability_cap` at every reader.
- **Precision weapons as modifiers.** The counterforce ratio and the silo penalty become two modifier types that script reads. The Precision-Guided Munitions technology carries both. Fielded ICBMs carry their share through `nd_icbm_force`, a modifier declared on the entry, which also takes over the technology's +0.5 attack success.
- **Accuracy is per enemy.** Every reader that compares two countries multiplies its exposed share by that enemy's accuracy factor.
- **A world's view of another country.** A small family of `nd_seen_*` values is built from public inputs only. The crisis pressure part, the opening preview and the believed redundancy switch to it, and every new preview of another country reads only it.
- **Display.** Figures the GUI can't compute (it can't take a rival from a variable as a scope) are stored by the two refreshes that already run: `nd_refresh_main_rival` for posture and `nd_plan_refresh` for the planner. Both now also run on every click.

**Tech Stack:** Victoria 3 script, GUI and localization; Python 3.11/3.12 tests.

**Spec:** `docs/superpowers/specs/2026-11-20-nuclear-delivery-and-survivability-design.md` (§3, §5, §6, §8, §9 phase 1). It builds on the crisis rework (`docs/systems/nuclear_crisis_design.md` §0.12–§0.17). Phase 2, the delivery projects, follows in its own plan.

## Global Constraints

- **Two PRs, both `--base main`** (D1): 1a is Tasks 1–4 (the model), 1b is Tasks 5–9 (the display), branched from 1a's tip (`docs/guides/git_workflow.md`, stacked PRs). Use a sparse worktree (no `gfx/`) per branch, and no `POST /reload` from one (`docs/guides/python_tools.md`). A session whose harness assigns its own branch uses that.
- **Engine facts relied on, all probed:**
  - A `scaling_modifiers_while_active` declaration reaches a `modifier:` read 2 to 5 days after its value changes, except tax-rate fields, which never show. Write the value as an inline block, `value = { value = <name> }`. `has_modifier` can't see a declared modifier (`scripting_best_practices.md` § "1.15 journal entries, scaling modifiers and once-only events").
  - A tooltip walk writes nothing, so a body that sets and then reads goes behind a click-only marker (`nd_plan_click` is the pattern).
  - The GUI can't take a scope from a variable (`gui_modding_guide.md` gotchas #11, #15).
  - Script values have no logarithm.
  - `any_*` triggers take no `limit`.
  - A `has_variable` guard never shares a `NOT` with its read; use `?=`.
- **One unprobed fact:** whether a script-only numeric type in a declared modifier reads through `modifier:`, like the Strategic Reserve's declared field, or stays at 0, like a tax rate. Self-check `nd_icbm_force_sum` (D6) measures it, with the existing `scaling_live` check as its control.
- **Conventions:**
  - Op tables stay in step in the `.gui` header, the sgui header and `journal_entry_systems.md` (a CRLF file: edit bytes or with `Edit`, and confirm with `grep -c $'\r$'`).
  - Numbers live in script values; nothing is restated in `.gui` or loc, except D15's article figures, which a test pins.
  - Loc is American English, written through the `event-text` skill. Run `organize_loc.py` after new keys.
  - Each task runs its tests, then `scripts/preflight.py --changed`. Each PR runs the full `scripts/preflight.py` before it opens. The player guide matches the script at the depth of its peers, and its PDF is rebuilt in the same commit.

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| D1 | Phase 1 ships as two PRs: 1a the model (Tasks 1–4), 1b the display (Tasks 5–9) | 1b's previews read 1a's values. Each is reviewable on its own, and 1a changes play (survivability, the precision-weapon penalty, the world's view) before any panel shows it, so 1b should follow promptly |
| D2 | `nd_fields_icbms = { has_technology_researched = ICBMs }`; `nd_fields_missile_submarines = { has_technology_researched = advanced_submarine_technology  any_scope_state = { is_coastal = yes } }` (country scope). The state-scope reach branch becomes `is_coastal = yes` plus `$COUNTRY$ = { nd_fields_missile_submarines = yes }`. The coast is read live, not cached | Phase 2 changes only these bodies. `any_scope_state` stops at the first coastal state, and the readers run at strike time and in the weekly reach rebuild |
| D3 | **What stays on the technologies** (the guard test's allowlist, each with its reason): `nd_taboo_has_programme_standing` (`nuclear_taboo_triggers.txt:170`); `global_tech_spread_script_value` (`extra_script_values.txt:1202`); the AI probe's technology counts (`te_ai_probe_values.txt`); the ship obsolescence and the naval AI strategy (`extra_ship_types.txt:2000`, `edited_default_strategy.txt:417`); the two generated files (covert theft, research commons); `add_technology_researched` in the debug events. **Everything else routes through D2**: the three reach triggers, `nd_reach_refresh` (`nuclear_deterrence_effects.txt:2329`), `nd_reach_limited`, `nd_can_adopt_launch_on_warning` / `_automatic_retaliation`, the survivability parts, `nd_k_ratio` (by D5), the incident unit and the silo explosion (`nuclear_incident_events.txt:1130–1135`, `:1399`), `nuke_attack_line_icbms` (`zzz_extra_custom_loc.txt:118`) and `nd_reach_value` (`nuclear_deterrence_custom_loc.txt:1730`) | Knowledge versus hardware, as the spec's §4.2 and §4.3 draw it. A new read that skips the trigger fails the test |
| D4 | `nd_survivability_target` and the five factors `nd_exposure_factor_bombers` 0.75, `_radar` 0.80, `_icbms` 0.70, `_submarines` 0.50 and `_missile_defense` 0.85. Each factor is 1 when the part isn't held, and the target is 100 × (1 − product). The value `nd_exposed_warheads_ceiling_r2` (and its `_vs_saved`) is renamed `_target_r2`, and `nd_display_survivability_cap` becomes `_target`, with no aliases. **Stored variables keep their names** (`nd_survivors_main_ceiling_bare_r2`), with a comment that "ceiling" means the target since phase 1 | One source per factor for the panel and the mirror. Renaming a stored variable strands the old one in every save for nothing |
| D5 | Two script-read numeric types in `common/modifier_type_definitions/nuclear_program_modifier_types.txt`, shaped like `country_nuclear_weapon_attack_success_add` with `script_only = yes`: `country_nd_k_ratio_add` (decimals 1) and `country_nd_silo_penetration_add` (percent). `nd_k_ratio` becomes `value = 1  add = modifier:country_nd_k_ratio_add`. The Precision-Guided Munitions technology (`era_8.txt:420`) gains `country_nd_k_ratio_add = 0.5` and `country_nd_silo_penetration_add = 0.15` | Owner call 10: the technology's own tooltip and every breakdown name both effects. A figure is a numeric field, never words in a boolean (`.claude/rules/script.md`) |
| D6 | **`nd_icbm_force`** (`nuclear_deterrence_modifiers.txt`): `country_nuclear_weapon_attack_success_add = 0.5`, `country_nd_k_ratio_add = 0.5`. Declared on `je_nuclear_program` with `value = { value = nd_icbm_force_value }` (1 while `nd_fields_icbms`, else 0). The ICBMs technology's own `country_nuclear_weapon_attack_success_add = 0.5` (`era_7.txt:369`) goes. **Self-check `TE_SELF_CHECK OK|BROKEN nd_icbm_force_sum`**, once a game: the first country holding `nd_fields_icbms` with the entry active for 14 days or more, beside `scaling_live` as the control. It prints the country's `modifier:country_nd_k_ratio_add` and `modifier:country_nuclear_weapon_attack_success_add` against what the parts should give. It is OK when both include the force's 0.5. A country that has neither the force nor Precision-Guided Munitions is excluded, so 0 can't pass. **Fallback**, named in the play-test list's Self-checks table: `nd_k_ratio` and `nuclear_strike_attack_rating` read `nd_fields_icbms` directly, and the technology keeps its attack success | Phase 2's fielding has to reach the strike odds and the counterforce ratio through something that follows a variable, carries over to a revolution's winner and nothing has to add or remove. The 2–5 day lag after research is harmless. Whether the type reads is the one unprobed fact |
| D7 | **Accuracy factor per enemy:** `nd_accuracy_mult_saved`, `_issuer` and `_target`, beside the warning penalties (`nuclear_deterrence_values.txt:846–880`). Each is 1 unless we hold `nd_fields_icbms` and that enemy's `modifier:country_nd_silo_penetration_add` is above 0, in which case it is (`nd_exposure_factor_icbms` + the penetration) ÷ `nd_exposure_factor_icbms`. Every `_vs_*` exposure value (`:884–935`) multiplies its exposed share by its scope's factor after the warning penalty, and holds the share at 1 or less. The salvo's counterforce (`:1033–1059`) gets it through `nd_exposed_warheads_vs_saved` | The product makes this exact on the target, and a fair approximation on the lagging stored survivability. One factor per scope, as the warning penalties already are |
| D8 | **The world's view** (country scope, of the country observed): `nd_seen_stockpile` = `nd_shown_public_estimate`; `nd_seen_survivability` = its `nd_survivability_target` (the cautious assumption: as hardened as its technology allows); `nd_seen_effective_survivability` = that × its readiness factor when the observer is in a crisis with it, else × Heightened's 0.9; `nd_seen_launch_credit` = its authority's credit with no safeguards cut. A **single figure** (pressure, the AI) uses these. A **displayed** figure prints a range from these to a force at its floor with the credit cut by 0.15. **Every displayed figure built on these says so** (owner call 14): a short qualifier on the figure ("up to N survive", "at least N destroyed", or "N–M"), and the shared hover `nd_tt_worlds_view` saying what we don't know, what the figure assumes and what the other end assumes. Tasks 5, 7 and 8 test it | Spec §5.2. Assuming the other side is as secure as its technology allows is how a planner would hedge, and it never reads a hidden value |
| D9 | **Owner call 13's switches:** `nd_yp_issuer_exposure_value` (`nuclear_deterrence_values.txt:1515–1527`) reads `nd_seen_survivors_vs_target` on the issuer in place of `nd_survivors_vs_target`. The opening preview's survivable line (`nuclear_crisis_effects.txt:189–196`) reads `$TARGET$ = { nd_seen_survivors_vs_saved >= 3 }`. `nd_redundancy_believed` (`nuclear_deterrence_values.txt:1093`) reads `nd_seen_stockpile` and `nd_redundancy_command_seen`, the command terms with `nd_seen_survivability` in place of the true survivability. A side's own survivors (`nd_yp_answer_survivors_value`) stay true. The other `nd_believed_stockpile` readers are unchanged: their fallback acts only before the estimate is seeded, in an arsenal's first week | A side knows its own forces. The two reads in call 13 are the only ones past the world's view that the audit found |
| D10 | **Per-option strike figures** go on our country, written by `nd_refresh_main_rival`: `nd_lost_main_auth_1`–`_4` (at our readiness, safeguards and authority credit as each option would set them), `nd_lost_main_ready_0`–`_3` (at our authority) and `nd_lost_main_safeguards_up`. This needs new exposure values at readiness 0, 1 and 3 against the saved enemy (only `_r2_vs_saved` exists, `:895`) and `nd_launch_credit_at_authority_2` / `_3` (`nd_launch_credit` reads the authority in force, `:739`). `nd_posture_sgui`'s effect calls `nd_refresh_main_rival` after every posture op (doctrine, readiness, authority, safeguards, hardening, ceiling), behind a click-only marker | The GUI can't take the rival as a scope. Today the refresh runs monthly and in the AI review (`nuclear_deterrence_effects.txt:451`, `:523`, `:3729`), so the figures would lag a click by a month |
| D11 | **Halt chance per authority:** `nd_hold_chance_at_authority_2` / `_3`, each `nd_hold_chance` with the authority's own term in place of the one in force. Central's hover says no launch flies without an order and gives our command redundancy (`nd_redundancy`); Automatic Retaliation's gives its upkeep (already shown). Incident exposure is not shown per authority | Exposure has no authority term (`nuclear_deterrence_values.txt:422–433`). What an authority changes is the halt chance, whether a warning reaches the government, and the cut-off commander's eligibility (`nuclear_deterrence_triggers.txt:2141`) |
| D12 | **Hardening's hover:** this month's step at the level in force and at the next (`nd_survivability_step`, and `nd_survivability_step_at_hardening_up`), and the months to close half the gap at each level, `nd_hardening_half_gap_months_1`–`_3` = 34, 17 and 11, pinned by a test to `round(ln 0.5 ÷ ln(1 − 0.02 × level))`. The floor is printed under the bar (`nd_display_survivability_floor`) | Script values have no logarithm. Half the gap is the honest figure, since the climb never arrives |
| D13 | **Safeguards' hover:** a display modifier `nd_safeguards_level_terms` (never added) carries a level's +12 to the reliability target (a new script-only type, `country_nd_reliability_target_add`) and +5% halt chance (`country_nd_halt_chance_add`, existing). `nd_safeguards_slow_launch` stays beside it. A test holds both figures to `nd_reliability_target` (`:243`) and the halt term (`:534`). The hover adds `nd_lost_main_safeguards_up` | The house pattern for figures in a choice's hover (`nd_authority_terms_*`), with a test because nothing else ties them |
| D14 | **Strike previews**, stored by `nd_plan_refresh` (`nuclear_deterrence_effects.txt:3213`, already run weekly and on every planner op behind `nd_plan_click`) as `nd_plan_pv_*` on our country:<br>• **Cities:** expected landed, expected deaths, and the razed share's lowest and highest over the states picked.<br>• **Forces:** destroyed, flown first and their survivors, each a D8 range.<br>• **Leadership:** the decapitation chance from `nd_redundancy_believed` (by D9) and the warheads expected on the command sites.<br>Expected landed is the sum of `nuclear_strike_success_chance` over the states the mission's picker (`nd_salvo_target`) would mark, with the marks cleared after. If the picker can't run outside the salvo, every warhead takes the capital's odds instead, as the AI does (`nd_ai_capital_hit_share`, `:1184`); the PR says which shipped. Each preview reads the enemy only through D8 values | The formulas exist (`:1033–1088`). The planner's refresh already has the enemy saved |
| D15 | **Basing and Guarantee figures** go in the articles' descriptions (`te_concepts_l_english.yml:2151`, `:2167`) as written numbers: Basing's −10 survivability against the guest for the host's neighbors (`nd_warning_time_penalty`), a third of the guest's accidents in the host, and the cost of ending the treaty; Guarantee's −10/−20 pressure (`nd_yp_protector_value`, `:1539`) and its cost of leaving. A test (`test_nuclear_basing.py`) holds each written number to its script value | A treaty article's description has no country scope to call a script value from (unverified, and not worth a probe for figures that change rarely). A test is the next best tie |
| D16 | **The opening preview's totals** (`nd_crisis_preview`, `nuclear_crisis_effects.txt:100–283`): the starting pressure and danger, built from the parts `nd_crisis_refresh_figures` writes, with the opening stage and publicity as literals (a warning: stage 1, private; an ultimatum: stage 2, public). A part that reads a crisis variable gets an `_at_open` variant taking those literals. Fallback, if a part can't be read before the crisis exists: the preview gives the parts it can, and says the totals appear on the panel at once | The figures exist, but the crisis record doesn't until it opens |
| D17 | **Launch authority is public** (owner, rework spec §14.2): `nd_authority` leaves `TRUE_VARS` (`test_nuclear_layout.py:1201`), with the ruling cited. Nuclear Powers' rows and National Info's public row show it beside the doctrine, with the overview's authority icons (`nd_display_authority_code`) | The leak test and the ruling disagree today. Delivery legs join these rows in phase 2 |
| D18 | **The Reach row** shows while armed (`nd_armed_sgui`), not only while reach is limited (`nd_reach_limited_sgui`, `nuclear_deterrence_sguis.txt:440–446`). `nd_reach_value` gains a first branch for `nd_fields_icbms`, "every country", and its submarine branch reads `nd_fields_missile_submarines` | A player with ICBMs should see that range is no longer a limit, not a row that vanished |

---

## PR 1a: the model

### Task 1: The delivery triggers and the landlocked fix (D2, D3)

**Files:** `common/scripted_triggers/nuclear_deterrence_triggers.txt` (the two new triggers; `nd_state_in_reach_of`, `nd_reaches_country`, `nd_reach_limited`, `nd_can_adopt_launch_on_warning`, `nd_can_adopt_automatic_retaliation`), `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_reach_refresh`), `common/script_values/nuclear_deterrence_values.txt` (the cap's two parts, until Task 2 replaces them), `events/nuclear_incident_events.txt` (`:1130–1135`, `:1399`), `common/customizable_localization/zzz_extra_custom_loc.txt` (`:118`), `nuclear_deterrence_custom_loc.txt` (`:1730`), `scripts/analysis/nuclear_incident_rates.py` (`icbms` now means the trigger), `test_nuclear_delivery.py` (new), `test_nuclear_basing.py` (`:126–129`, the silo kind's prerequisite).

**Interfaces:** produces `nd_fields_icbms = yes` and `nd_fields_missile_submarines = yes` (country scope), read by every later task. Nothing else changes for a country that has a coast.

- [x] Write `TestDeliveryTriggers`: the two bodies per D2, and the state branch asks `is_coastal` and the trigger in that order. Write `TestTechnologyReads`: every `has_technology_researched = ICBMs` or `= advanced_submarine_technology` in `common/`, `events/` and `gui/` is on D3's allowlist, which names each site's reason; `test_landlocked_has_no_submarine_reach` checks that both reach triggers and the survivability part read the submarine trigger. Run: FAIL.
- [x] Implement. Update `test_nuclear_basing.py`'s silo prerequisite to the trigger. Run `test_nuclear_delivery.py`, `test_nuclear_reach.py`, `test_nuclear_basing.py`, `test_nuclear_deterrence.py`, `test_nuclear_incident_risk.py`, then `preflight.py --changed`. PASS.
- [x] Commit `Nuclear delivery: one trigger per leg; no submarine reach without a coast (spec §9 phase 1)`.

### Task 2: Survivability as a product (§3.1–§3.3, D4)

**Files:** `common/script_values/nuclear_deterrence_values.txt` (the factors, `nd_survivability_target`, the floor, the step, `nd_exposed_warheads_target_r2` and its `_vs_saved`, `nd_display_survivability_target`, the display family at `:2315–2348`), `common/scripted_effects/nuclear_deterrence_effects.txt` (`:94`), the rework comment ("The last stretch toward full security…", `:195`), `scripts/analysis/nuclear_survivors.py` (`exposure_factor`, `survivability_target`, the calibration table), `test_nuclear_survivors.py`, `test_nuclear_deterrence.py` (`test_survivability_cap_is_80` → `TestSurvivabilityTarget`), `test_nuclear_layout.py` (`:539–543`).

- [x] Write `TestSurvivabilityTarget`: each factor's value and its held test (the two legs through Task 1's triggers); the target is 100 × (1 − product) and has no `max = 80`; the table in spec §3.1 reproduced by the mirror (25, 40, 58, 79, 82, 64); the floor is 0.3 × target; no reader names `nd_survivability_cap`. Also `test_lost_share_table`: the mirror reproduces §3.3's Central, Delegation and Launch on Warning rows. Run: FAIL.
- [x] Implement. Update the layout test's needles to the new names. Run the nuclear tests, then `preflight.py --changed`. PASS.
- [x] Commit `Nuclear survivability: a product of its parts, with no flat ceiling (spec §3.1)`.

### Task 3: Precision weapons and the ICBM force (§3.4, D5–D7)

**Files:**
- `common/modifier_type_definitions/nuclear_program_modifier_types.txt` (two types);
- `common/technology/technologies/era_8.txt` (Precision-Guided Munitions) and `era_7.txt` (the ICBMs attack success goes);
- `common/static_modifiers/nuclear_deterrence_modifiers.txt` (`nd_icbm_force`);
- `common/journal_entries/je_nuclear_program.txt` (the declaration);
- `common/script_values/nuclear_deterrence_values.txt` (`nd_k_ratio`, `nd_icbm_force_value`, the three accuracy factors, every `_vs_*` exposure value);
- the self-check: a hidden event in `events/nuclear_weapon_events.txt` (next free id) fired from the entry's weekly pulse while `nd_icbm_force_sum` isn't logged;
- loc: the two types' names and `_desc`, `nd_icbm_force`, `nd_icbm_force_desc`;
- `scripts/analysis/nuclear_survivors.py` (`accuracy_mult`);
- `test_nuclear_survivors.py`, `test_nuclear_delivery.py`;
- `docs/testing/nuclear-playtest.md` (the Self-checks row).

- [x] Write `TestPrecisionWeapons`:
  - `nd_k_ratio` is 1 + the modifier and reads no technology;
  - the technology carries both lines and the ICBMs technology no attack success;
  - `nd_icbm_force` carries both 0.5s and is declared with an inline value block reading `nd_fields_icbms`;
  - nothing adds, removes or `has_modifier`s it (`test_journal_entry_shape.py` already fails on those);
  - every `_vs_*` exposure value multiplies by its own scope's factor after the warning penalty, and holds the share at 1 or less;
  - the mirror gives §3.4's 17.9% → 21.7% and 35.7% → 43.4%.

  Write `test_icbm_force_self_check`: one-shot, the 14-day gate, the degenerate exclusion, the `scaling_live` control named in the line, OK and BROKEN forms. Run: FAIL.
- [x] Implement. Run the nuclear tests, then `preflight.py --changed`; `modifier_field_audit --strict` and `loc_coverage_audit --strict` come with it. PASS.
- [x] Commit `Nuclear precision weapons: the counterforce ratio and the silo penalty as modifiers; the ICBM force (spec §3.4)`.

### Task 4: The world's view (§5.2, D8, D9; owner call 13)

**Files:** `common/script_values/nuclear_deterrence_values.txt` (`nd_seen_*`, `nd_seen_survivors_vs_saved` / `_vs_target`, `nd_redundancy_command_seen`, `nd_redundancy_believed`, `nd_yp_issuer_exposure_value`), `common/scripted_effects/nuclear_crisis_effects.txt` (the preview's survivable line), `scripts/analysis/nuclear_survivors.py`, `test_nuclear_survivors.py` (`test_believed_redundancy_reads_the_estimate` and a new `TestWorldsView`), `test_nuclear_deterrence.py` (`PREVIEW_PINS` if the line's text changes).

**Interfaces:** produces the `nd_seen_*` family, which Tasks 7 and 8 read for every figure about another country.

- [x] Write `TestWorldsView`:
  - the `nd_seen_*` values read only public inputs. `nd_shown_public_estimate`, the target and its technology and leg parts, `nd_authority` and readiness inside a crisis are allowed; `nd_survivability`, `nd_safeguards`, `nd_hardening`, `nd_reliability`, the stockpile and readiness outside a crisis are not. The check runs `test_nuclear_layout.py`'s `_true_state` closure over each value;
  - D9's three readers read the seen values;
  - `nd_yp_answer_survivors_value` still reads the true figure;
  - the mirror and the script agree.

  Run: FAIL.
- [x] Implement. Run the nuclear tests, then `preflight.py --changed`. PASS.
- [x] Commit `Nuclear crises: what one side counts of the other is the world's view (spec owner call 13)`.
- [x] **PR 1a.** Full `scripts/preflight.py`. Write design §0.18's first half: what shipped, D1–D9, and what phase 2 consumes (the two triggers and the force). Also `mod_systems/nuclear.md` and chapter 14's survivability paragraph, factor table, range sentence (submarines need a coast) and the precision-weapon lines, with the PDF rebuilt. The PR body has a "Player guide" line naming the chapter. Open it with `--base main`, then run the two-reviewer review, one fix pass, and merge on green CI.

**As built (2026-11-20).** Tasks 1–4 shipped as planned, with two changes. The self-check is a scripted effect called from the entry's weekly pulse (`nd_icbm_force_selfcheck`), not a hidden event: the same once-a-game line with less wiring. D6's fallback is wired as one switch, `nd_icbm_force_declared_reads`, which `nd_k_ratio`, `nuclear_strike_attack_rating` and the attack rating's display read. The design record is `nuclear_crisis_design.md` §0.18.

## PR 1b: the display

### Task 5: Forces (§5.4 Forces, D18)

**Files:** `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (the survivability bar's target line and floor, a Launch credit row after Survivors, the Reach row's gate), `common/scripted_guis/nuclear_deterrence_sguis.txt` (the Reach row's gate), `common/script_values/nuclear_deterrence_values.txt` (`nd_display_exposure_factor_*`, `nd_display_launch_credit`), `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_refresh_main_rival` stores `nd_main_rival_k`, `nd_main_rival_pgm` and `nd_main_rival_accuracy_mult`), `nuclear_deterrence_custom_loc.txt` (`nd_reach_value`), loc (`nd_w_survivability_*`, `nd_w_launch_credit_*`, `nd_w_survivors_tt`, `nd_w_reach_*`), `test_nuclear_layout.py`.

- [x] Write `TestForcesDisplay`:
  - the survivability hover prints one line per factor through `nd_display_exposure_factor_*`, then the exposed share and the target;
  - the bar's line reads the target and the floor is printed;
  - the Launch credit row reads `nd_display_launch_credit`, its hover naming the authority's credit and the safeguards cut;
  - the Survivors hover breaks the rival's reach into its believed warheads × its counterforce ratio with the ratio's parts, plus the silo line while `nd_main_rival_accuracy_mult` is above 1;
  - the Reach row's gate is `nd_armed_sgui` and its "every country" branch comes first;
  - the rival's figures in the Survivors hover carry the qualifier and `nd_tt_worlds_view` (D8).

  The rows fit (`_fits`), and `PrivateTest` and `ObserverTest` pass. Run: FAIL.
- [x] Implement, then the GUI lint, the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear panel: survivability's parts, launch credit, the rival's counterforce ratio (spec §5.4)`.

**As built (2026-11-20).** Four changes from the plan:
- **Where the chain sits.** It is in the target's hover, not the survivability row's: that hover is at 473 of the 500 characters `long_tooltip_audit` allows. The bar's target line has the hover, and so does a new row under the bar, "Target and floor", which prints both figures. A part not held prints "not researched", or what it needs.
- **Reach.** `nd_reach_limited_sgui` is gone. The row shows on `nd_armed_sgui`, and `nd_reach_list_sgui` prints one line with ICBMs. Without ICBMs it prints the list's heading, which moved out of `nd_w_reach_tt`, then the list.
- **The rival's figures.** The refresh stores five values, through `_saved` script values:
  - `nd_main_rival_warheads`: the shown estimate, `nd_seen_stockpile`;
  - `nd_main_rival_k`: the counterforce ratio;
  - `nd_main_rival_pgm`: the ratio's Precision-Guided Munitions part, `nd_k_ratio_tech_part`, the rest of `country_nd_k_ratio_add`;
  - `nd_main_rival_k_force`: the ICBM force's part, `nd_k_ratio_force_part`;
  - `nd_main_rival_accuracy_mult`.

  The reach figure still multiplies `nd_believed_stockpile` (D9). So in the days before a new arsenal's estimate is seeded, the warheads line can read 0 under a reach above it.
- **The qualifier.** "Up to" on the rival's reach is the qualifier, and its hover is `nd_tt_worlds_view`, a nested hover (`#tooltippable;tooltip:`) in plain text. The safeguards cut a level is now one script value, `nd_launch_credit_safeguards_cut`.

### Task 6: Posture, hardening, safeguards and the ceiling (D10–D13)

**Files:** `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_refresh_main_rival`: the `nd_lost_main_*` figures), `common/scripted_guis/nuclear_deterrence_sguis.txt` (`nd_posture_sgui`'s effect: the refresh after each op, behind a click-only marker), `common/script_values/nuclear_deterrence_values.txt` (the readiness 0, 1 and 3 exposure values against the saved enemy, the credit and halt chance per authority, the hardening step at the next level, the half-gap constants, the ceiling's next-size upkeep, a script value of `var:nd_warhead_ceiling` ± 1 mirroring `nd_upkeep_weekly`), `common/script_values/nuclear_taboo_values.txt` (the next-size burden, mirroring `nd_taboo_burden_value`'s arsenal factor, `:608`), `common/static_modifiers/nuclear_deterrence_modifiers.txt` (`nd_safeguards_level_terms`), `common/modifier_type_definitions/nuclear_deterrence_display_types.txt` (`country_nd_reliability_target_add`), the widget (the authority choices, readiness rows, hardening and safeguards steppers, the ceiling stepper), loc, `test_nuclear_deterrence.py`, `test_nuclear_layout.py`.

- [x] Write `TestPostureFigures`:
  - each authority option's hover prints its `nd_lost_main_auth_N` and halt chance, Central's adds `nd_redundancy`, and the readiness rows print `nd_lost_main_ready_N`;
  - the refresh runs after every posture op, behind the marker;
  - the half-gap constants equal the formula;
  - `nd_safeguards_level_terms`'s figures equal the script values;
  - the ceiling's next-size figures equal `nd_taboo_burden_value` and `nd_upkeep_weekly` when ceiling and stockpile are equal;
  - each hover says what it says in figures, not words (no "climbs faster", no "improves over the coming months").

  Run: FAIL.
- [x] Implement, then the GUI lint, `tooltip_walk_variable_audit --strict`, the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear posture: what each choice saves, costs and changes, in figures (spec §5.3)`.

**As built (2026-11-20).** Five changes from the plan:
- **Terms apart from their clamps.** `nd_hold_chance` and `nd_reliability_target` now clamp `nd_hold_chance_unclamped` and `nd_reliability_target_unclamped`, so the figures per authority and per safeguards level reuse the terms and stay exact at the clamps. Each per-level figure is a named value that the display modifiers and the hovers are tested against: `nd_safeguards_reliability_per_level` (12), `nd_safeguards_halt_per_level` (5), `nd_hold_launch_on_warning_cut` (10), `nd_hardening_rate_per_level` (0.02) and `nd_survivability_erosion_rate` (0.01).
- **What the refresh stores.** It also stores `nd_lost_main`, the strike now, which the safeguards line sets beside one level more. Each strike figure is `nd_lost_vs_saved_at_*`, and a test holds each to `nd_lost_vs_saved` with that choice made.
- **Where the figures sit.** Each readiness level's figure is in its own hover, not a new column, so the widget is unchanged. The hardening buttons give this month's step at the next level both up and down.
- **The ceiling's next size.** The figures are at the stepper's own next step (1, 5 or 25 warheads, `nd_taboo_ceiling_lowered_value` and `_raised_value`), not at the ceiling ± 1, and sit in the − and + buttons' hovers.
- **One sentence waits for phase 2.** That a ceiling holds warheads only, not a project, waits for phase 2, which brings the projects.

### Task 7: Strike previews (D14)

**Files:** `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_plan_refresh`: the `nd_plan_pv_*` figures), `common/script_values/nuclear_deterrence_values.txt` (the preview values, ranges per D8), the widget (a preview line under each mission, refreshed by the size stepper's ops 77/78), loc (`nd_w_strike_mission_*_tt` and the preview keys, each labelled an estimate), `test_nuclear_deterrence.py`, `test_nuclear_layout.py`.

- [ ] Write `TestStrikePreview`:
  - each mission's preview is stored on every planner op (72–79) and weekly;
  - the Forces preview prints our counterforce ratio with its parts, and the silo line when the target holds `nd_fields_icbms` and we have the penetration;
  - each range has its low end at or below its high end, and every preview line carries its qualifier ("at least", "up to" or the range) and `nd_tt_worlds_view` (D8);
  - **`test_preview_reads_only_the_worlds_view`**: the preview values reach the enemy only through `nd_seen_*`, `nd_shown_public_estimate`, public technologies and states, by `_true_state` over the enemy-scope reads. `PrivateTest` covers another country's panel, not our own panel's reads of an enemy.

  Run: FAIL.
- [ ] Implement, then record in the commit which expected-landed method shipped (D14). Run the nuclear tests and `preflight.py --changed`. PASS.
- [ ] Commit `Nuclear strikes: the planner previews each mission (spec §5.3)`.

### Task 8: Crisis, events, articles, the public authority (D15–D17)

**Files:**
- `common/scripted_effects/nuclear_crisis_effects.txt`: `nd_crisis_refresh_figures` stores the survivors behind the two pressure parts, and `nd_crisis_preview` gets the opening totals (D16);
- `common/script_values/nuclear_deterrence_values.txt`: the `_at_open` variants;
- the crisis section and the Go public move's hover (`te_miscellaneous_l_english.yml:5580`, `:5671`, with `nd_cd_public_value` and the stage);
- `events/nuclear_incident_events.txt`: `.1.c`'s `custom_tooltip` with `var:nd_survivors_vs_suspect` and a false warning's price, from the values a first use books;
- the disavowal toggle's hover (ops 70/71), with `nd_claim_belief_value` (`:2206`) and the price of a lie found out;
- `te_concepts_l_english.yml:2151`, `:2167` (D15);
- Delivery and Defence (`te_nuclear_sec_delivery`): a counterforce row with its parts;
- the Nuclear Powers rows and National Info's public row (D17);
- `test_nuclear_layout.py` (`TRUE_VARS`), `test_nuclear_basing.py` (D15's pins), `test_nuclear_deterrence.py`.

- [ ] Write the tests:
  - `TestCrisisFigures`: the stored survivors beside both parts, the seen figure for the issuer's with its qualifier and `nd_tt_worlds_view` (D8); Go public's hover names its danger and stage; the preview prints the opening totals or, per D16's fallback, says where they appear;
  - `TestDecisionHovers`: `.1.c` and the disavowal print their figures through `custom_tooltip`s (`silent_variable_audit`);
  - `TestArticleFigures` (D15);
  - `TestPublicAuthority`: `nd_authority` is off `TRUE_VARS` with the ruling's comment; the Powers rows and the public row read it.

  Run: FAIL.
- [ ] Implement, then `organize_loc.py`, the event text through the `event-text` skill, the nuclear tests and `preflight.py --changed`. PASS.
- [ ] Commit `Nuclear decisions: crisis, launch under attack, disavowal and the articles show their figures (spec §5.3)`.

### Task 9: Docs, the play-test list; gate, PR, review

- [ ] Design §0.18's second half: D10–D18, what shipped of D14 and D16, and §5.5's audit as closed. Update `mod_systems/nuclear.md`, `journal_entry_systems.md` (the Forces, Posture and Strike areas and the op table; CRLF), and Help page topics for the chain and launch credit.
- [ ] Chapter 14 at its peers' depth: launch authority (what each saves, the halt chance), the Strike section's previews, opening a crisis (the totals), moves (Go public), claiming a strike was unauthorized (the chance of belief), incidents (launch under attack), the treaty articles. Then rebuild the PDF.
- [ ] Play-test list (`docs/testing/nuclear-playtest.md`): spec §8's items for phase 1 (a posture click moves the Survivors row the same day; a Forces preview against the salvo that follows), the target line after a research, the precision-weapon line appearing when a rival researches it, and the self-check row from Task 3.
- [ ] The spec's status line and the `docs/superpowers/README.md` rows.
- [ ] Full `scripts/preflight.py`. Then PR 1b with `--base main` (retargeted after 1a merges, per `git_workflow.md`), the two-reviewer review, one fix pass, and merge on green CI.

## Review Focus

1. **A landlocked armed country.** No coastal reach, no submarine factor, and the Reach row lists bomber reach only. Tests: Task 1's `test_landlocked_has_no_submarine_reach`, Task 5's reach gate.
2. **The ICBM force reads 0.** Then strike odds and the counterforce ratio drop by 0.5 for every ICBM power at once. The self-check catches it in the first game. Review the fallback's wiring in the PR, so it is a one-line switch.
3. **A rival researches Precision-Guided Munitions mid-crisis.** Its silo penalty reaches the issuer's seen survivors, the answer part and the panel's line the same week, and nothing lags a month. Tests: Task 3's `_vs_*` readers, Task 6's refresh on clicks.
4. **What a player learns about an enemy.** Every new figure about another country is a D8 range or single figure from public inputs, and none of them, nor the Powers rows, prints a true stockpile, survivability or safeguards. Tests: Task 4's `TestWorldsView`, Task 7's `test_preview_reads_only_the_worlds_view`, `PrivateTest`.
5. **A save from before phase 1.** Survivability above the new target settles through the existing step; the stored `ceiling` variables are rewritten at the next refresh; no figure reads an unset variable unguarded (`variable_guard_audit`).
