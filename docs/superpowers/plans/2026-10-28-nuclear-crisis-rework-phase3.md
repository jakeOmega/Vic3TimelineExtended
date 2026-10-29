# Nuclear Crisis Rework, Phase 3 (The Exchange) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship spec phase 3: a strike planner in the nuclear panel that orders a salvo by mission (Cities, Forces, Leadership), counterforce that destroys the victim's exposed warheads, decapitation of a Central Authorization victim, and the victim's answer sized from what survived (§6).

**Architecture:** One salvo effect, `nd_order_salvo`, fires N warheads in a loop, choosing each target state by mission, and runs the use's consequences once afterwards: counterforce, decapitation, the claim, the UN and taboo record scaled by √(warheads landed), and one victim event. The panel orders it through a confirmation event; the AI orders it from the strategic strike action. Counterforce and decapitation are script values in the shape of phase 1's survivors values, mirrored in Python and tested against the script.

**Tech Stack:** Victoria 3 script and GUI; Python 3.11/3.12 tests.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` (§6, §9's planner line, §10's Strike section, §11). Phases 1 and 2 shipped as #1222 and #1223 (`nuclear_crisis_design.md` §0.12–§0.13).

## Global Constraints

- Worktree `~/src/vic3te-nuclear-p3`, branch `feat/nuclear-rework-p3`, base `19b79ff`. No `POST /reload` from here.
- Owner answers (2026-10-28): a salvo's taboo knock and UN record scale with **√(warheads landed)** (−10, −20 at 4, the −30 ledger floor from 9); the AI's missions are **rule-based** (Forces under Warfighting or Flexible First Use when the enemy could answer; Leadership only against Central Authorization when it can land more warheads on the capital than the redundancy R; Cities otherwise); **K stays** at 1, +0.5 with ICBMs, +0.5 with Precision-Guided Munitions, checked in this phase's calibration.
- Engine facts: an undelayed `trigger_event` runs the event's `immediate` inside the caller; a tooltip walk writes nothing, so a walked body that sets and reads a variable runs behind a click-only marker (`nd_dispatch_strategic_strike`); `while = { count = <script value> }` works; an `ordered_*` iterator's `position` is a literal (no precedent for a script value); no `var:` on the right of `?=`; `te_set_sqrt = { IN OUT }`; the UN helpers' `POINTS` take a script value name.
- `debug_log` strings take no `$PARAM$`; `trigger_event` takes one literal delay (a `random_list` of literal branches).
- GUI: no action button's `visible` from an op-branching `IsShown` (widget gotcha #22); a country's name in the panel through a display sgui and `[SCOPE.sCountry('x').GetName]` (the crisis headline), never `Var().GetCountry` (gotcha #11); the op table kept in step in the widget header, the sgui header and `journal_entry_systems.md` (CRLF: edit bytes).
- Every new loc key American, `#b X#!`; every new static modifier or event has loc; the player guide matches the script.

## Review Focus

1. **A Cities salvo larger than the victim's state count.** Once every state is marked, further warheads strike the top-scoring state again; the loop never stalls or strikes nothing. Test: Task 2's `test_targets_fall_back_once_all_are_marked`.
2. **A Forces salvo against a small or empty arsenal.** Destruction never exceeds the victim's stockpile, and a victim with no exposed warheads loses none. Test: Task 1's `test_counterforce_bounded_by_exposed_and_stockpile`.
3. **A salvo where every warhead misses.** No counterforce, decapitation, claim, or UN or taboo first-use record; the miss events fire once. Test: Task 2's `test_aftermath_only_when_a_warhead_landed`.
4. **The order confirmed after the situation changed.** Peace, a lost arsenal or a decapitation between the button and the confirmation: Launch re-checks every gate and is hidden or does nothing; Stand down is the default. Test: Task 4's `test_confirmation_rechecks_the_order`.
5. **A decapitated victim.** Every ordered launch path is closed until command returns, unordered paths are unaffected, and only Central Authorization can be decapitated. Test: Task 3's `test_command_gates_every_ordered_launch`.

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| H1 | The one-city strike stays `nuke_diplo_action`; the planner orders salvos whose states script chooses by mission | Spec §6.1's fallback; §12's unprobed "state list in the panel" is then not needed |
| H2 | The planner's enemy is `nd_plan_enemy`, the `nd_plan_index`-th country (in `every_country` order) we are at war with or in an open peacetime exchange with (`nd_plan_candidate`); ◀ ▶ move the index; `nd_plan_refresh` (the planner's weekly update, and every planner op) re-picks it, wraps the index and clears the enemy when none qualifies | No variable-list indexing or country selection exists in the panel; a counted pass is plain script |
| H3 | Order → a confirmation event, `nuclear_weapon_events.31` "Launch Order": Launch (re-checks `nd_can_order_salvo`, runs `nd_order_salvo`) or Stand down (`default_option`) | The strike action has a confirmation box; a panel button has none; an expired popup must never launch |
| H4 | **Not through `nd_launch_or_intercept`** (spec §6.1's wording): it saves `nd_incident_launch_<kind>`, which `nd_strike_from_incident` reads as unordered, so a planner salvo would carry a true "unauthorized" claim. The salvo has its own click-marked dispatch | Ruling against the spec's text; cost: one sentence in design §0.14 |
| H5 | Targeting: each warhead marks its state (`nd_salvo_target`, on the state) and takes `position = 0` of the unmarked states by mission — Cities by `nuclear_strike_target_score`; Forces among states with a Military Base or Barracks, else the capital's strategic region, else the capital; Leadership the capital. When none is unmarked, `position = 0` without the mark test. Marks cleared at the end | Literal `position` only; the mark makes "one warhead each" |
| H6 | Damage: Cities and Leadership use `nuclear_industrial_strike`; Forces use `nd_counterforce_strike_damage` (state scope): a quarter of the casualties (2.5% of the state, noted through `te_demog_note_kills`), devastation 25, the aftermath modifier, the same `nd_struck_by`/`nuked_by_country` writes | Spec: "a quarter of a city strike's casualties" |
| H7 | The aftermath runs once, in this order: R snapshot (taken before the loop) → counterforce → decapitation → `nd_record_claim` → first-use or answer bookkeeping → the victim's `.1` → Launch on Warning's fire-first answer → the attacker's events → `nd_record_nuclear_use` last | The claim precedes `.1` (its belief roll reads the count); the crisis stays open for `.1`'s belief roll; R is the command as it stood when the salvo began |
| H8 | Bookkeeping scaled by `var:nd_salvo_sqrt` (`te_set_sqrt` of the landed count): UN order points, dossier points, authority shock, infamy, world relations, and the taboo through a new `nd_taboo_note_use_scaled = { KIND RETALIATION SCALE }` that `nd_taboo_note_use` now calls with `SCALE = 1`. The quiet-years clock moves once per salvo. `nuclear_first_strike` keeps its literal calls | The owner's √; refactoring `nuclear_first_strike` would put a variable read inside the strike action's confirmation-box walk |
| H9 | The salvo settles phase 2's deferred claim items: the victim's `nd_struck_count` is the salvo's landed count, and the AI lies only when one warhead landed (`nd_strike_landed_count_value`, 1 outside a salvo) | `nd_record_claim` now runs after the warheads land; §5.4's "single-warhead strike" and the belief's +20 term then mean what they say |
| H10 | Counterforce (Forces warheads landed only): destroyed = stochastic round of min(exposed(victim), K(attacker) × landed) × (1 − credit(victim)), at most the stockpile. Launch on Warning: the credit's share fires first, up to three, at the attacker (`nuclear_response_strike`, a literal ladder of positions), gated on `nd_retaliation_permitted`, then the victim records the use as `.1.e` does | Spec §6.2; `.1.e`'s gate and record keep a pledge or doctrine from breaking silently |
| H11 | Decapitation (any warhead landed on the capital, victim under Central Authorization): chance = max(0, (L − R)/(L + R)) × 100. On success `nd_decapitated` (13, 20 or 27 days) and `nd_pending_retaliation` = the attacker; the weekly block that sends `.24` also needs `nd_command_intact`, and `.24` reads as "Command Restored" (triggered title and text) while `nd_restored_from_decapitation` is set. `.1` gains option d, "Our command is cut off" (the default while cut off; absorb is hidden then) | Spec §6.3: the answer is delayed, not lost, through `.24`'s path |
| H12 | `nd_command_intact` (not `nd_decapitated`) joins `nd_retaliation_permitted`, both strike actions' `possible`, the three dispatchers' limits, the crisis execute options (`nuclear_crisis.4.g`, `.7.a`), the guarantor's `.22`, `nuclear_incident.1.c`, `.50.c` and `nd_can_order_salvo`. Only a Central country is ever decapitated, and all its launches are ordered, so the dispatchers' check touches no unordered path | One trigger, every ordered path |
| H13 | `.1` for a salvo: a triggered text from the victim's `nd_salvo_seen_by` (= the attacker), `nd_salvo_seen_landed`, `_destroyed`, `_mission` (30 days). `nuclear_first_strike` and `nuclear_response_response_strike` remove `nd_salvo_seen_by` before their `.1` | A single strike after a salvo must not read as the salvo |
| H14 | The AI (in `nuke_diplo_action`'s `accept_effect`, a hidden branch for `is_ai = yes`): `nd_ai_salvo_mission_value` 3 if the victim is under Central Authorization and spare × the capital's hit chance exceeds its believed redundancy; 2 under Warfighting or Flexible First Use against a victim believed armed; else 1, today's strike. Spare = stockpile − max(1, a third, rounded down). Forces size = min(spare, ⌈believed stockpile ÷ K⌉); Leadership size = min(spare, ⌈2R⌉) | The owner's rule; `is_ai` picks how the AI decides, not what a strike does, so the shared-mechanics rule holds |
| H15 | The Strike section is its own panel section after Crisis, shown while armed with an enemy picked (`has_variable = nd_plan_enemy`, cheap in `is_shown`); collapse flag `nd_strike_closed`. Rows: Target (◀ name ▶, ops 72/73), Mission (three choice rows, 74–76), Warheads (stepper, 77/78), Order (79). Every op body runs behind a click-only marker with a custom tooltip | Spec §10; gotcha #22; the walk |
| H16 | Observer records `type=salvo; mission=; size=; landed=`, `type=counterforce; destroyed=; fired_first=`, `type=decapitation; result=yes|no`, counted by the report; a once-a-game `TE_SELF_CHECK OK|BROKEN nd_salvo_targets` (a Cities salvo marked min(size, states) distinct states) | §11; the mark is the one unverified mechanism |

---

### Task 1: Counterforce and decapitation values, the Python mirror and calibration (§6.2, §6.3, §14.5)

**Files:** `common/script_values/nuclear_deterrence_values.txt`, `common/scripted_triggers/nuclear_deterrence_triggers.txt`, `scripts/analysis/nuclear_survivors.py`, `scripts/analysis/nuclear_incident_rates.py` (Posture fields), `test_nuclear_survivors.py`.

**Interfaces:** Produces, in victim scope with the attacker saved as `scope:nd_sv_enemy`: `nd_counterforce_destroyed_raw` (min(`nd_exposed_warheads`, K × `var:nd_salvo_forces_landed`) × (1 − `nd_launch_credit`), min 0), `nd_counterforce_saved_raw` (the same min × `nd_launch_credit`), `nd_decapitation_chance_value` (max(0, (L − R)/(L + R)) × 100, L = `scope:nd_sv_enemy.var:nd_salvo_capital_landed`, R = `scope:nd_sv_enemy.var:nd_salvo_victim_r`), `nd_redundancy_believed` (`nd_redundancy` on `nd_believed_stockpile`). Attacker scope: `nd_salvo_size_value` (`var:nd_salvo_size`, floor, 1 to `nd_stockpile`, at most 25), `nd_strike_landed_count_value` (1, or `var:nd_salvo_landed` when set), the scaled bookkeeping values `nd_salvo_un_order_first`/`_answer`, `nd_salvo_dossier_first`/`_answer`, `nd_salvo_un_shock`, `nd_salvo_infamy`, `nd_salvo_world_relations` (each the single strike's figure × `var:nd_salvo_sqrt`). Triggers: `nd_command_intact`. Python: `counterforce_destroyed(landed, k, exposed, credit)`, `decapitation_chance(landed, redundancy)`; Posture fields `salvo_forces_landed`, `salvo_capital_landed`, `salvo_victim_r`.

- [ ] Write `TestCounterforceScript` (`test_counterforce_matches_mirror` over a grid of landed, survivability, authority and techs; `test_counterforce_bounded_by_exposed_and_stockpile`; `test_saved_share_is_the_credit`), `TestDecapitationScript` (`test_chance_matches_mirror`; `test_thirty_warhead_power_needs_seven` — R 6 with Satellite Communications, 0 at 6, > 0 at 7; `test_three_warhead_state_faces_21_from_two`), `TestSalvoScale` (`test_scaled_values_are_the_single_strike_times_sqrt`), `TestCalibration` (`test_one_warhead_cannot_disarm_a_large_arsenal`: K 2, one landed, 20 unhardened → ≥ 18 left; `test_hardened_great_power_keeps_a_second_strike`: 20 warheads at the ceiling, Heightened, against a 20-warhead rival at K 2 → ≥ 3; `test_unhardened_small_arsenal_can_be_disarmed`: 5 at 0 survivability, 3 landed at K 2 → 0). Run: FAIL.
- [ ] Implement the values, the trigger and the mirror; `main()` prints the calibration table for 5/10/20 warheads at survivability 0/40/72 and K 1/1.5/2. Run: PASS.
- [ ] Commit `Nuclear exchange: counterforce and decapitation values, mirrored and calibrated (spec §6.2, §6.3)`.

### Task 2: The salvo (§6.1, §6.2, §6.3, §14.3)

**Files:** `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_order_salvo`, `nd_salvo_warhead`, `nd_salvo_aftermath`, `nd_salvo_record_use`, `nd_salvo_counterforce`, `nd_salvo_decapitation`; `nd_record_claim`), `common/scripted_effects/extra_effects.txt` (`nd_counterforce_strike_damage`), `common/scripted_effects/nuclear_taboo_effects.txt` (`nd_taboo_note_use_scaled`), `common/scripted_effects/nuclear_observer_effects.txt`, `scripts/analysis/nuclear_observer_report.py`, `test_nuclear_deterrence.py`, `test_nuclear_incident_risk.py`.

**Interfaces:** Consumes Task 1's values. Produces `nd_order_salvo` (attacker scope; `var:nd_salvo_mission` 1–3, `var:nd_salvo_size`, `scope:nd_salvo_victim` saved): the click-only marker (`nd_salvo_click`), the gates of `nd_can_order_salvo = { ENEMY }` (Task 3), then H5–H10 and H16 in H7's order; afterwards no `nd_salvo_*` working variable is left on the attacker and no `nd_salvo_target` on any state. Victim summary `nd_salvo_seen_by/_landed/_destroyed/_mission` (30 days).

- [ ] Write `TestSalvo`: `test_salvo_fenced_by_a_click_marker`; `test_loop_counts_the_size_value` (`while = { count = nd_salvo_size_value`); `test_targets_by_mission` (the three limits, `position = 0`); `test_targets_fall_back_once_all_are_marked`; `test_marks_cleared`; `test_forces_damage_is_a_quarter_and_counted` (`percent = 0.025`, `te_demog_note_kills`); `test_aftermath_order` (index order of the H7 calls); `test_aftermath_only_when_a_warhead_landed`; `test_bookkeeping_scaled_once` (each scaled value named once; `nd_taboo_note_use_scaled` with `SCALE = var:nd_salvo_sqrt`; `nd_taboo_note_use` calls the scaled form with `SCALE = 1`); `test_low_fires_first_with_its_gate_and_record`; `test_decapitation_only_central`; `test_claim_reads_the_landed_count` (`nd_strike_landed_count_value`; the AI lie needs ≤ 1); `test_salvo_working_variables_cleared`. `TestObserverRecords` gains the new record lines; `TestObserverSalvo.test_salvo_counters`. Run: FAIL.
- [ ] Implement. Self-check `nd_salvo_targets` once a game. Run the tests and the audit gate. PASS.
- [ ] Commit `Nuclear exchange: the salvo, counterforce and decapitation (spec §6)`.

### Task 3: The victim's side: decapitation gates, Command Restored and the salvo's text (§6.3, §6.4)

**Files:** `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_retaliation_permitted`, `nd_can_order_salvo`), `common/diplomatic_actions/nuke.txt` (both actions' `possible`), `common/scripted_effects/nuclear_deterrence_effects.txt` (the three dispatchers, the weekly `.24` block), `common/scripted_effects/extra_effects.txt` (`nuclear_first_strike`, `nuclear_response_response_strike`: clear `nd_salvo_seen_by`), `events/nuclear_weapon_events.txt` (`.1` desc and option d, `.24` title and text), `events/nuclear_crisis_events.txt` (`.4.g`, `.7.a`, `.22`), `events/nuclear_incident_events.txt` (`.1.c`, `.50.c`), loc, tests.

**Interfaces:** Consumes `nd_decapitated` and `nd_restored_from_decapitation` (Task 2). Produces `nd_can_order_salvo = { ENEMY }` (custom_tooltip reasons: armed, assembled, `nd_planner_candidate`, doctrine, pledge, war law, command intact, size within the stockpile), used by the panel and `.31`.

- [ ] Write `TestDecapitationGates`: `test_command_gates_every_ordered_launch` (each H12 site names `nd_command_intact`); `test_unordered_paths_untouched` (the commander, system and loose-warhead paths don't); `test_cut_off_option` (`.1.d` shown while cut off, the default then, absorb hidden, `(no_effect_option)` REVIEWED); `test_command_restored_reuses_24`; `test_salvo_text_and_stale_guard`. Run: FAIL.
- [ ] Implement; loc for the new texts and reasons. Run: PASS.
- [ ] Commit `Nuclear exchange: a decapitated command waits to answer (spec §6.3, §6.4)`.

### Task 4: The Strike section and the Launch Order (§6.1, §10)

**Files:** `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (section, header op table), `gui/journal_entry_widgets/nuclear_layout_widget.gui`, `common/scripted_guis/nuclear_deterrence_sguis.txt` (ops 72–79 on `nd_posture_sgui`, display sguis `nd_plan_shown_sgui`, `nd_plan_enemy_sgui`), `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_plan_refresh`, `nd_plan_*` op effects, the weekly call), `common/script_values/nuclear_deterrence_values.txt` (`nd_display_plan_mission`), `events/nuclear_weapon_events.txt` (`.31`), `docs/systems/journal_entry_systems.md` (CRLF), loc, `test_nuclear_deterrence.py`, `test_nuclear_layout.py`.

**Interfaces:** Consumes `nd_can_order_salvo`, `nd_order_salvo`. Produces ops 72/73 (enemy ◀ ▶), 74–76 (mission 1–3), 77/78 (size − +), 79 (order: sends `.31`).

- [ ] Write `TestStrikeSection`: `test_ops_in_step` (gui, sgui, doc); `test_op_bodies_fenced` (each 72–79 effect behind a click marker with a custom tooltip); `test_refresh_picks_by_index_and_wraps`; `test_section_shown_cheaply` (`has_variable = nd_plan_enemy`, no `any_country`); `test_target_named_through_a_display_sgui` (`SCOPE.sCountry('nd_plan_enemy_disp')`, no `Var('nd_plan_enemy').GetCountry`); `test_confirmation_rechecks_the_order` (`.31`: Launch's trigger `nd_can_order_salvo`, Stand down `default_option = yes`). Update `test_nuclear_layout.py`'s section list and flag map. Run: FAIL.
- [ ] Implement; `python3 scripts/analysis/check_gui_lint.py`; label budget. Run: PASS.
- [ ] Commit `Nuclear exchange: the Strike section and the Launch Order (spec §6.1)`.

### Task 5: The AI's missions (§9, §14.4)

**Files:** `common/script_values/nuclear_deterrence_values.txt` (`nd_ai_salvo_mission_value`, `nd_ai_salvo_spare_value`, `nd_ai_salvo_size_value`), `common/diplomatic_actions/nuke.txt` (`accept_effect`), `test_nuclear_deterrence.py`.

**Interfaces:** Consumes `nd_order_salvo`, `nd_redundancy_believed`, `nd_k_ratio`.

- [ ] Write `TestAiSalvo`: `test_mission_rule` (Leadership's Central and capacity terms; Forces' doctrine and belief terms; else 1); `test_spare_keeps_a_reserve`; `test_sizes`; `test_accept_effect_routes_ai_missions` (a hidden `is_ai = yes` branch with mission > 1 calls `nd_order_salvo`; otherwise the single strike stays). Run: FAIL.
- [ ] Implement. Run: PASS.
- [ ] Commit `Nuclear exchange: the AI strikes forces or leadership by rule (spec §9)`.

### Task 6: Docs, guide, play-test list; gate, PR, review

- [ ] Design §0.14 (what shipped, H4's ruling, the calibration table); strike §0.13's two "not built" claim lines that H9 settles; spec status line.
- [ ] Chapter 14: Nuclear strikes (the Strike section, missions, counterforce, decapitation, the √ scaling), Launch authority (credit and decapitation lines), the AI bullets; rebuild the PDF. The authority hovers say Central can be decapitated and the others can't (§10), if they don't already.
- [ ] Play-test list items for the planner, counterforce, Launch on Warning's first fire, decapitation and Command Restored; the `nd_salvo_targets` self-check row.
- [ ] Full gate (suite, CI audits strict, ruff, tabs, loc, spelling, guide lint and check, GUI lint, rosters, BOMs); PR with `--base main`; the two-reviewer final review; one fix pass; merge on green CI.
