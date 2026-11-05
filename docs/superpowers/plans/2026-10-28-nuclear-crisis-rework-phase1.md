# Nuclear Crisis Rework, Phase 1 (Values and Triggers) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship spec phase 1: second-strike survivors and their readers, launch-authority payoffs and safeguards, the new chance of a halt, war exposure, the government's launch-under-attack order, crisis stakes, co-belligerent cover and the proliferation fix, all calibrated offline against spec §2.

**Architecture:** Paradox script values carry every formula; scripted triggers and effects read them; `nd_crisis_refresh_figures` stores each new crisis part on both parties, as the shipped parts are. `scripts/analysis/nuclear_incident_rates.py` evaluates the real script values, so calibration is a test that reads the script, not copied numbers.

**Tech Stack:** Victoria 3 Clausewitz script; Python 3.11/3.12 (unittest, pytest-xdist); Typst/pandoc for the player guide PDF.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` (§3, §4, §5.1, §5.3, §8.2–§8.4, §2 calibration). Shipped behaviour: `docs/systems/nuclear_crisis_design.md` §0.

## Global Constraints

- Worktree `~/src/vic3te-nuclear-p1`, branch `feat/nuclear-rework-p1`, base `0559d4082`. Never `POST /reload` from here; run audits with their `--strict` CLIs.
- Owner answers (2026-10-28): §14.1 confirmed (launch under attack in a war **or an Acute crisis** with the suspect, every doctrine but No First Use); §14.2 launch authority is **public** (read it directly); self-merge after independent review.
- Every number below is the spec's first tuning value. Task 7 may move only the levers it names.
- Survivors read **public** belief of the enemy (`nd_believed_stockpile`) and the true own stockpile (`nd_stockpile`).
- `debug_log` strings take no `$PARAM$` (`TestObserverRecords`). Engine unknowns get a `TE_SELF_CHECK OK|BROKEN <name>` line and a row in `docs/testing/nuclear-playtest.md`'s Self-checks table.
- Tabs in `.txt`; one UTF-8 BOM on every changed `.txt`/`.gui`/`.yml`; American spelling in loc and the guide; `#b X#!` loc markup.
- A new crisis part touches seven places: its `_value`, the total, `nd_crisis_refresh_figures`, `nd_crisis_clear_figures`, the breakdown sgui line, its `_line` loc key, and `test_nuclear_deterrence.py`'s store check.

## Review Focus

1. **A country with no arsenal, or no rival.** Survivors and the main rival must be absent, not zero-divided or stale: a disarmed country (`nd_stockpile = 0`) and an armed one with no plausible attacker show no survivors row and keep no `nd_main_rival`. Test: Task 3's `test_main_rival_cleared_without_attacker`.
2. **Recessed or standing down must not push the AI toward Launch on Warning** (the reason `nd_ai_review_posture` reads stored survivability today). The authority choice reads survivors at Heightened with no launch credit. Test: Task 5's `test_authority_reads_bare_heightened_survivors`.
3. **Peacetime callers of `nd_hold_chance` with no suspect** (the cut-off commander, an accident under Automatic Retaliation). The suspect term reads `scope:nd_warning_suspect ?=`; with none it adds nothing. Test: Task 2's `test_hold_chance_suspect_optional`.
4. **A government order outside war is a first use**, recorded and priced as a deliberate one (taboo, UN, pledge), not as an unordered launch. Test: Task 6's `test_order_outside_war_records_first_use`.
5. **Co-belligerent cover must not fire `.20` twice** for a guarantor a treaty or umbrella already reaches, and must lapse when the war ends. Test: Task 8's `test_cobelligerent_branch_skips_treaty_and_umbrella`.

---

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| D1 | Survivors are script values reading a saved `scope:nd_sv_enemy`, in four variants: current readiness with own credit (crisis, panel), Heightened with own credit (AI High Alert), Heightened with no credit (AI authority), technology ceiling at Heightened with no credit (AI: "hardening won't close it") | Script values take no arguments; the AI variants keep the reason the shipped AI reads stored survivability |
| D2 | `nd_main_rival` (a country variable) is the crisis opponent if believed armed, else the plausible attacker with the largest `nd_believed_stockpile` (`ordered_country`). Refreshed monthly for armed countries and at the start of `nd_ai_review_posture` | Spec §3.2 "its most dangerous armed rival"; also the panel row |
| D3 | `nd_crisis_refresh_figures` stores each party's survivors against the other (`nd_survivors_crisis`) before the parts; the parts read the stored numbers | One computation per week, and the breakdown's hover prints the same number |
| D4 | Stakes count goals by type with `play_side_has_war_goal_of_type_against` / `war_side_…`, plus `−10` per target state under `is_target_of_wargoal = <issuer>`. No goal iterator exists and no trigger tells a primary demand from another, so every goal counts. A play where a state-taking type is present but no state counts falls back to −10 per type and logs `TE_SELF_CHECK BROKEN nd_stakes_states` | Spec §8.2; `is_target_of_wargoal` is documented for wars only |
| D5 | The AI's stake gate: a play/war threat is not made when its stakes alone pull predicted pressure under the concession line (40, where `.1`'s yield weights start): unstaked ≥ 40 and staked < 40 | "where the stakes would hold pressure below its own concession line"; other reasons the AI threatens are untouched |
| D6 | Co-belligerent cover gets no `nd_dispute_guarantee_against` branch | A co-belligerent is at war with the attacker, so its crisis classifies as dispute 2 first; the trigger's `NOT has_war_with` would block the branch anyway |
| D7 | Abandoning a co-belligerent: −5 credibility, the beneficiary still hears `.21`, nothing else | "Nothing was promised" |
| D8 | War exposure band 3 test for "a nuclear weapon has landed in the war": either side holds a state with `nuclear_strike_aftermath` or `tactical_nuke_aftermath` | Same read as `nd_war_law_exception` |
| D9 | Restraint-class government (§4.4) = `nd_regime_is_restraint`: no militarist regime, and an interest group in government for which `nd_ig_is_restraint = yes` is the most powerful in government (`ordered_interest_group`, `order_by = ig_clout`) | Mirrors `nd_regime_is_militarist`'s shape |
| D10 | Budget deficit (§4.4) = `net_fixed_income < 0` or `in_default = yes` | `net_fixed_income` is the engine's weekly balance trigger |

---

### Task 1: Risk model covers the Acute crisis, the war-year and the peacetime pair-year

**Files:**
- Modify: `scripts/analysis/nuclear_incident_rates.py`
- Test: `test_nuclear_incident_risk.py`

**Interfaces:**
- Produces: `RiskModel.acute_crisis(p_a, p_b, weeks=8) -> float`, `RiskModel.war_year(p_a, p_b, band) -> float`, `RiskModel.peace_pair_year(p_a, p_b) -> float`, `RiskModel.near_miss_ratio(p) -> float`, and `RiskModel.order_chance(p) -> float` (the AI's share of `nuclear_incident.1.c` given a warning, read from the event's `ai_chance` blocks). `Posture` gains `war_band: int = 0`, `talks: bool = False`, `suspect_readiness: int = 3`, `survivability: float = 50`, `survivors: float = 5`, `ruler: str = "neutral"`, `regime: str = "neutral"`, `second_warning_source: bool = True`.
- `main()` prints spec §2.3's table (five rows, two equal sides each), the war-year for bands 2 and 3, the peacetime pair-year at Heightened, and the near-miss ratio.

- [ ] **Step 1: Write the failing tests** in a new `class TestCrisisAndWarModel(unittest.TestCase)`:
  - `test_acute_table_has_five_rows`: `main()` output (captured) contains the five §2.3 row labels.
  - `test_acute_crisis_is_symmetric`: `acute_crisis(p, p)` equals `1 - (1 - side_week)**16` where `side_week` is the per-side weekly launch chance the model exposes as `launch_chance_week(p)`.
  - `test_order_chance_zero_outside_war_or_acute`: `order_chance(Posture(stage=2))` is 0.0 and `order_chance(Posture(stage=0, war=False))` is 0.0.
  - `test_unknown_trigger_raises`: `RiskModel().condition([("no_such_trigger", "=", "yes")], Posture())` raises `ValueError` (the model must not treat an unhandled key as false).
- [ ] **Step 2: Run** `.venv/bin/python -m pytest test_nuclear_incident_risk.py -k CrisisAndWar -q` (from the main checkout's venv: `../Vic3TimelineExtended/.venv/bin/python`). Expected: FAIL (no such methods).
- [ ] **Step 3: Implement.** `launch_chance_week(p)` = P(incident) × [P(dangerous family) × (1 − hold) + P(warning reaches the government) × `order_chance(p)`]; a warning reaches the government under Central, under Automatic Retaliation, and under Delegation outside a war with the suspect. `condition()` handles every trigger the new values read (`nd_incident_band`, `nd_crisis_talks_open`, the suspect's readiness through `scope:nd_warning_suspect`, `ruler_is_*`, `nd_regime_is_*`, the second-warning techs); any other unknown key raises. Read `.1`'s option weights from `events/nuclear_incident_events.txt` as the module reads `.30`'s draw today.
- [ ] **Step 4: Run** the same command. Expected: PASS. The printed table still shows the shipped figures (Central 0, Delegation sg3 ≈ 1%, LoW sg3 ≈ 5%, LoW sg0 ≈ 64%).
- [ ] **Step 5: Commit** `Nuclear risk model: Acute crisis, war-year and pair-year cases`.

### Task 2: The chance of a halt and war exposure (§4.3, §5.1)

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_hold_chance`, `nd_incident_crisis_weekly_permille`, new `nd_war_danger_band`, `nd_incident_band`)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new `nd_war_band_3_against_any`, `nd_crisis_talks_open`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` + loc: the hold-chance and exposure hovers name the new terms
- Test: `test_nuclear_incident_risk.py`

**Interfaces:**
- Produces: `nd_incident_band` (0–3) = max(`nd_own_danger_band`, `nd_war_danger_band`); `nd_war_danger_band` = 2 at war with any enemy believed armed (`any_enemy_in_war`), 3 when `nd_war_band_3_against_any = yes`; `nd_crisis_talks_open` (either party's record has `nd_crisis_talks = 1`); `nd_hold_ceiling` (97 peace/no crisis, 92 Warning or Confrontation, 85 Acute or war).

- [ ] **Step 1: Write the failing tests** (`class TestHoldAndExposure`):
  - `test_hold_ceiling_by_context`: model `nd_hold_chance` with reliability 98, safeguards 3: 97 at peace, 92 at stage 2, 85 at stage 3, 85 in a war.
  - `test_hold_chance_suspect_terms`: suspect Recessed +20, suspect High Alert −5, talks +10, effective survivability 0 gives −10, 50 gives 0.
  - `test_hold_chance_suspect_optional`: the script text of `nd_hold_chance` reads the suspect only through `scope:nd_warning_suspect ?=`.
  - `test_war_exposure_band`: `nd_incident_crisis_weekly_permille` at war with an armed enemy and no crisis equals the band-2 value; with `war_band=3` the band-3 value; with a crisis at band 1 and a war at band 2, band 2.
- [ ] **Step 2: Run** `pytest test_nuclear_incident_risk.py -k HoldAndExposure -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** `nd_hold_chance` keeps its shipped terms; `max = 97` becomes `max = nd_hold_ceiling`; add the suspect, hotline and own-vulnerability terms (−(50 − `nd_effective_survivability`) ÷ 5, between −10 and 0). `nd_incident_crisis_weekly_permille` reads `nd_incident_band` instead of `nd_own_danger_band`. Band 3: either side's incorporated state under the other's goal (`nd_core_threatened_by` both ways), either side losing (`nd_is_losing_war_to` both ways), or D8.
- [ ] **Step 4: Run** the test command. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear incidents: context ceiling, suspect and hotline terms, war exposure`.

### Task 3: Survivors and the main rival (§3.1, §3.2)

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (cap 95 → 80; new values below)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new `nd_plausible_attacker_of`; `nd_has_plausible_attacker` reuses it)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (new `nd_refresh_main_rival`, called from `nd_monthly_update` and the top of `nd_ai_review_posture`)
- Create: `scripts/analysis/nuclear_survivors.py` (Python mirror)
- Test: `test_nuclear_deterrence.py`, new `test_nuclear_survivors.py`

**Interfaces:**
- Produces (country scope): `nd_k_ratio` (1, +0.5 `ICBMs`, +0.5 `precision_guided_munitions`); `nd_launch_credit` (Delegation 0.25, Launch on Warning 0.6, each −0.05 per safeguards level; else 0); `nd_redundancy` (1 + stockpile ÷ 10, +2 `satellite_communications`, +1 `mainframe_computers`); `nd_counterforce_reach_saved` (`scope:nd_sv_enemy`'s `nd_k_ratio` × `nd_believed_stockpile`).
- Produces (country scope, needs `scope:nd_sv_enemy`): `nd_survivors_vs_saved`, `nd_survivors_r2_vs_saved`, `nd_survivors_bare_r2_vs_saved`, `nd_survivors_ceiling_bare_r2_vs_saved` (D1). Each = stockpile − min(exposed, reach) × (1 − credit), min 0; exposed = stockpile × (1 − survivability ÷ 100) at the variant's readiness and survivability.
- Produces variables: `nd_main_rival` (country), `nd_survivors_main`, `nd_survivors_main_r2`, `nd_survivors_main_bare_r2`, `nd_survivors_main_ceiling_bare_r2`; all removed when there is no rival or no arsenal.
- Produces Python: `survivors(stockpile, survivability, readiness_factor, credit, enemy_k, enemy_believed) -> float`.

- [ ] **Step 1: Write the failing tests.**
  - `test_nuclear_survivors.py::test_formula_cases`: `survivors(10, 50, 1.0, 0, 1.0, 3) == 7`; `survivors(10, 0, 1.0, 0.6, 2.0, 20) == 4`; `survivors(0, 80, 1.0, 0, 1, 5) == 0`.
  - `test_nuclear_survivors.py::test_mirror_matches_script`: evaluate `nd_survivors_vs_saved` through `RiskModel`'s arithmetic on the script text for three postures and compare with `survivors()` (`math.isclose`).
  - `test_nuclear_deterrence.py::test_survivability_cap_is_80`: `nd_survivability_cap` ends `max = 80`.
  - `test_nuclear_deterrence.py::test_main_rival_cleared_without_attacker`: `nd_refresh_main_rival`'s body removes `nd_main_rival` and the four `nd_survivors_main*` variables in its no-rival branch.
- [ ] **Step 2: Run** `pytest test_nuclear_survivors.py test_nuclear_deterrence.py -k "survivors or cap_is_80 or main_rival" -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the values, the trigger refactor, `nd_refresh_main_rival` (D2) and the mirror. Check every guide and doc line that says 95.
- [ ] **Step 4: Run** the test command. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear survivability: survivors against an enemy's arsenal, ceiling 80`.

### Task 4: Survivors' readers in a crisis (§3.3)

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_yp_answer_value`; new `nd_yp_issuer_exposure_value`, `nd_cd_vulnerability_value`; both totals)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_refresh_figures` stores `nd_survivors_crisis` on both parties first (D3), then the two new parts; `nd_crisis_clear_figures`; `nd_crisis_preview`'s answer line)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (two breakdown lines), `localization/english/te_miscellaneous_l_english.yml` (`nd_yp_issuer_exposure_line`, `nd_cd_vulnerability_line`, reworded `nd_yp_answer_line` and preview keys)
- Modify: `events/nuclear_crisis_events.txt` (`.1.c` weight: survivors ≥ 3 instead of effective survivability ≥ 50; `.20.c` weight: the guarantor's survivors against the attacker < 3 instead of < 30)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: Task 3's values and `scope:nd_sv_enemy`.
- Produces: stored parts `nd_yp_issuer_exposure`, `nd_cd_vulnerability`; stored `nd_survivors_crisis` on each party; trigger `nd_vulnerable_to = { ENEMY }` (survivors against `$ENEMY$` under 3) for event weights.

- [ ] **Step 1: Write the failing tests:**
  - `test_new_parts_are_stored_cleared_and_shown`: for `nd_yp_issuer_exposure` and `nd_cd_vulnerability`, each appears in `nd_crisis_refresh_figures` (a store call), `nd_crisis_clear_figures` (a remove), its breakdown sgui (a `nd_crisis_breakdown_line`), its total (`add = <name>_value`), and the loc file (`<name>_line`).
  - `test_answer_has_no_line_at_50`: `nd_yp_answer_value`'s body contains no `>= 50` and no `nd_authority_automatic`.
  - `test_answer_three_quarters_rule`: the body multiplies by 0.75 under `nd_authority_central = yes` when the issuer's `nd_believed_stockpile` exceeds the target's `nd_redundancy`.
  - Extend the existing store-check test's expected part lists with the two names.
- [ ] **Step 2: Run** `pytest test_nuclear_deterrence.py -q -k "parts or answer"`. Expected: FAIL.
- [ ] **Step 3: Implement.** Answer: unarmed +20; armed −25 × min(1, `nd_survivors_crisis` ÷ 3), with the three-quarters rule applied to the survivors first. Issuer exposure (armed target only): −5 × (3 − issuer's `nd_survivors_crisis`) while under 3, else 0. Vulnerability: (50 − effective survivability) ÷ 5 for whichever armed party gives more, between 0 and 10, rounded. The preview computes survivors live (save `scope:nd_sv_enemy`, evaluate `nd_survivors_vs_saved`).
- [ ] **Step 4: Run** the test command, then `python3 scripts/analysis/check_gui_lint.py` and `python3 loc_coverage_audit.py --strict`. Expected: PASS, no errors.
- [ ] **Step 5: Commit** `Nuclear crises: answer and issuer exposure read survivors; vulnerability raises danger`.

### Task 5: Launch-authority payoffs and the AI's posture (§4.1, §4.2, §4.4)

**Files:**
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_ai_review_posture`: readiness block's High Alert test, authority block, investment block)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new `nd_regime_is_restraint` (D9), `nd_in_budget_deficit` (D10), `nd_ai_vulnerable_to_main_rival`, `nd_ai_hardening_cannot_close`)
- Modify: `common/static_modifiers/nuclear_deterrence_modifiers.txt`, `common/modifier_type_definitions/` (display types `country_nd_launch_credit_add` as a percent, `country_nd_decapitation_immune_bool`), and the authority buttons' tooltip loc (credit and decapitation lines)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_survivors_main_r2`, `nd_survivors_main_bare_r2`, `nd_survivors_main_ceiling_bare_r2`, `nd_launch_credit`.
- Produces: the AI's rules. Safeguards start at 1; +1 cautious ruler; +1 `nd_regime_is_restraint`; +1 under authority 2 or 3; −1 militarist regime or Warfighting doctrine; −1 `nd_in_budget_deficit`; clamp 0–3; 0 in default. Authority, when tenure allows: vulnerable (`nd_ai_vulnerable_to_main_rival`: a plausible attacker and bare-Heightened survivors under 3) and `nd_ai_hardening_cannot_close` (ceiling survivors also under 3): Automatic (25%) if available and not militarist, else Launch on Warning (25%) if militarist and available, else Delegation (30%) if available. Not vulnerable and authority ≠ 1: back to Central (50%); a cautious ruler always. Vulnerable but hardening can close it: hardening want +1. High Alert in an Acute crisis: opponent at Heightened or higher, or `nd_survivors_main_r2 < 3` (no `nd_authority_automatic` guard change).

- [ ] **Step 1: Write the failing tests:**
  - `test_authority_reads_bare_heightened_survivors`: the authority block reads `nd_survivors_main_bare_r2` and not `nd_effective_survivability` or `var:nd_survivability`.
  - `test_safeguards_not_automatic`: the investment block contains `ruler_is_cautious`, `nd_regime_is_restraint`, `nd_regime_is_militarist`, `nd_doctrine_warfighting`, `nd_in_budget_deficit` and `clamp_variable = { name = nd_ai_want_safeguards min = 0 max = 3 }`, and no `var:nd_readiness_target = 3` term.
  - `test_back_to_central_without_threat`: the authority block has a branch that calls `nd_set_authority_1` without `ruler_is_cautious` in its limit.
  - `test_authority_modifiers_show_payoff`: `nd_authority_terms_2` carries `country_nd_launch_credit_add = 0.25` and `country_nd_decapitation_immune_bool = yes`; `_3` 0.6 and the bool; `_4` the bool.
- [ ] **Step 2: Run** `pytest test_nuclear_deterrence.py -q -k "authority or safeguards or central"`. Expected: FAIL.
- [ ] **Step 3: Implement.** The safeguards' display modifier shows −5% credit per level only under authority 2 or 3 (apply it from `nd_apply_posture_modifiers` with the level as multiplier). Register both display types (`/modifier-search` against the mod after `--strict` audits; `hidden_modifier_audit` and `modifier_visibility_audit` clean).
- [ ] **Step 4: Run** the test command plus `python3 hidden_modifier_audit.py --strict` and `python3 loc_coverage_audit.py --strict`. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear posture: Delegation and Launch on Warning pay; AI safeguards and authority read survivors`.

### Task 6: The government's launch-under-attack order (§5.3)

**Files:**
- Modify: `events/nuclear_incident_events.txt` (`nuclear_incident.1.c` trigger and `ai_chance`; `.1.a`/`.1.b` weights rescaled ×10)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new `nd_launch_under_attack_permitted = { SUSPECT }`)
- Modify: loc (`nd_tt_launch_under_attack_context`, `nd_tt_launch_under_attack_doctrine`)
- Test: `test_nuclear_incident_risk.py`, `test_nuclear_deterrence.py`

**Interfaces:**
- Produces: `nd_launch_under_attack_permitted`: (war with `$SUSPECT$` or our crisis with it at stage 3) and (`nd_doctrine_nfu = no` or `nd_was_struck_by = { ENEMY = $SUSPECT$ }`); the pledge, Rules of War and assembled-forces lines stay as they are in `.1.c`.
- AI weights: `.1.c` base 2; +3 `nd_vulnerable_to = { ENEMY = scope:nd_warning_suspect }`; +2 aggressive ruler; +2 strain ≥ 50; +2 an Acute crisis with the suspect; ×0.5 cautious ruler; ×0.5 with `recon_satellites` or `satellite_communications`; ×0.5 while talks are open. Task 7 may rescale these.

- [ ] **Step 1: Write the failing tests:**
  - `test_order_needs_war_or_acute`: model `order_chance` > 0 at stage 3 and at war, 0 at stage 2.
  - `test_order_blocked_only_by_nfu`: the `.1.c` trigger no longer calls `nd_doctrine_permits_strike` and calls `nd_launch_under_attack_permitted`.
  - `test_order_outside_war_records_first_use`: follow `nd_launch_or_intercept`'s `KIND = warning` path with `nd_warning_launched = 1` and assert the recorder it reaches counts the launch as deliberate (read the recorder first; if the incident path records it as unordered, the order sets the marker the deliberate path reads, and the test asserts that marker).
- [ ] **Step 2: Run** `pytest test_nuclear_incident_risk.py test_nuclear_deterrence.py -q -k order`. Expected: FAIL.
- [ ] **Step 3: Implement.** Keep the shipped option's greyed-with-reason pattern; the first line names the missing context (war or Acute crisis), as the shipped first line names the missing war. Update the long comment above the option to record the 2026-10-28 ruling.
- [ ] **Step 4: Run** the test command. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear incidents: the government may order a launch under attack in an Acute crisis (owner 2026-10-28)`.

### Task 7: Calibrate against spec §2

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (levers only: the band surcharges 5/50/175, the readiness multipliers 0.6/0.25)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (lever: the family weights in `nd_fire_incident_family`)
- Modify: `events/nuclear_incident_events.txt` (lever: `.1` option weights)
- Test: `test_nuclear_incident_risk.py`

- [ ] **Step 1: Write the failing band tests** (`class TestSpecBands`), each building both sides from `Posture(readiness=3, stage=3, danger=80, reliability=<55+12×sg+5>, survivability=50, survivors=5)` and asserting `acute_crisis` in: Central sg3 [0.02, 0.03]; Central sg0 [0.04, 0.06]; Delegation sg3 [0.03, 0.05]; LoW sg3 [0.08, 0.12]; LoW sg0 [0.20, 0.30]. Also `test_delegation_beats_central_none` (owner call 6: Delegation sg3 ≤ Central sg0 × 1.25); `test_war_year_band2` in [0.08, 0.15] and `test_war_year_band3` in [0.15, 0.30] (both sides Central sg1, High Alert, 52 weeks); `test_peace_pair_year` in [0.0005, 0.0015] (both sides Delegation sg2, Heightened, no crisis); `test_near_misses_several_times_unheld` (`near_miss_ratio` ≥ 3 for LoW sg3 in the Acute case).
- [ ] **Step 2: Run** `pytest test_nuclear_incident_risk.py -k SpecBands -q`. Expected: FAIL on shipped values.
- [ ] **Step 3: Tune** only the levers above, re-running `python3 scripts/analysis/nuclear_incident_rates.py` after each change. Record the before/after table in the commit message.
- [ ] **Step 4: Run** the band tests and the whole of `test_nuclear_incident_risk.py`. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear risk calibrated to the Cold War bands (spec §2.3)`.

### Task 8: Crisis subjects: stakes, co-belligerents, proliferation (§8.2–§8.4)

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (new `nd_yp_stakes_value`, `nd_yield_pressure_unstaked_value`; total)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_dispute_proliferation_by`; new `nd_cobelligerent_cover_against = { AGAINST }`, `nd_cobelligerent_of = { GUARANTOR }`; branches in `nd_has_armed_guarantor_against`, `nd_has_ready_guarantor_against`, `nd_is_guaranteed_by`, `nd_covered_country_struck_by`, `nd_covered_country_struck`; `nd_ai_would_warn` gains the D5 gate)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_notify_guarantors` third loop; `nd_guarantee_act_abandon` co-belligerent branch; store/clear stakes)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_record_nuclear_use` third loop)
- Modify: `events/nuclear_crisis_events.txt` (`.20` and `.21` descs for basis 3), loc, sgui line
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Produces: `nd_guarantee_basis` on the guarantor before `.20` (1 treaty, 2 umbrella, 3 co-belligerent), read by `nd_guarantee_act_abandon` and the descs; stored part `nd_yp_stakes`; `nd_ai_concession_line = 40` in the top block of the values file.
- Stakes weights: annexation or reunification −30 (and no state count); a subjugation type or `regime_change` −20; −10 per target state under a goal (D4); −4 per minor type present (`enforce_treaty_article`, `open_market`, `humiliation`, `contain_threat`, `foreign_investment_rights`, `force_nationalization`, `ban_slavery`, `revoke_claim`, `revoke_all_claims`, the four strait/toll types); min −40.

- [ ] **Step 1: Write the failing tests:**
  - `test_proliferation_needs_unarmed_target`: `nd_dispute_proliferation_by` contains `nd_believed_armed = no` inside a `$TARGET$` block.
  - `test_cobelligerent_branch_in_guarantee_triggers`: the four triggers each name `nd_cobelligerent_cover_against` or `nd_cobelligerent_of`.
  - `test_cobelligerent_branch_skips_treaty_and_umbrella`: in both loops, the co-belligerent `every_cobelligerent_in_war` limit contains `nd_is_guaranteed_by_treaty` and `nd_under_umbrella_of` inside `NOT`.
  - `test_cobelligerent_abandon_costs_five`: `nd_guarantee_act_abandon` has a `var:nd_guarantee_basis = 3` branch with `AMOUNT = -5` and no `nd_guarantee_abandoned` inside it.
  - `test_stakes_part`: the seven-place check of Task 4 for `nd_yp_stakes`; the value contains `min = -40`.
  - Add the new trigger names to `TestUmbrellaCoverage.GUARANTEE_READERS` only if they read `has_type = nuclear_guarantee` (they should not).
- [ ] **Step 2: Run** `pytest test_nuclear_deterrence.py -q -k "proliferation or cobelligerent or stakes or Umbrella"`. Expected: FAIL.
- [ ] **Step 3: Implement**, with the D4 self-check written once per crisis (`nd_stakes_selfcheck_done` on the issuer's record).
- [ ] **Step 4: Run** the test command plus `python3 effect_trigger_validity_audit.py --strict` and `python3 script_argument_audit.py --strict`. Expected: PASS.
- [ ] **Step 5: Commit** `Nuclear crises: stakes weigh on pressure; co-belligerents cover; armed rivals are not proliferators`.

### Task 9: The panel and the observer report

**Files:**
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (Forces: a "Survivors against <rival>: N of M" row while `nd_main_rival` exists, hover with stockpile, exposed, the rival's reach, credit), `common/scripted_guis/nuclear_deterrence_sguis.txt`, `common/customizable_localization/nuclear_deterrence_custom_loc.txt` if an op is needed, loc
- Modify: `scripts/analysis/nuclear_observer_report.py` (uses per Acute crisis, near misses (`launch_held`) against unheld launches, launches by authority)
- Test: `test_nuclear_layout.py`, `test_nuclear_incident_risk.py` (observer fixtures)

- [ ] **Step 1: Write the failing tests:** `test_nuclear_layout.py::test_survivors_row_present` (the row's text key and its `visible` reading `nd_main_rival`); an observer-report test feeding three fixture lines (one Acute crisis, one use, two `launch_held`) and asserting `uses_per_acute_crisis == 1.0` and `near_misses == 2`.
- [ ] **Step 2: Run** `pytest test_nuclear_layout.py test_nuclear_incident_risk.py -q -k "survivors_row or observer"`. Expected: FAIL.
- [ ] **Step 3: Implement**, following `docs/guides/gui_style_guide.md` (brief label, detail on hover) and the Forces section's existing row pattern.
- [ ] **Step 4: Run** the tests and `python3 scripts/analysis/check_gui_lint.py`. Expected: PASS, no errors.
- [ ] **Step 5: Commit** `Nuclear panel: survivors against the main rival; observer report counts uses per crisis and near misses`.

### Task 10: Docs, player guide, play-test list

**Files:**
- Modify: `docs/systems/nuclear_crisis_design.md` §0.2–§0.5 and the status banner; `docs/player_guide/14-nuclear.md` (Survivability, reliability and crew strain; Launch authority; Crisis stages, danger and pressure; Opening a nuclear crisis; Guarantors called in; Nuclear incidents and accidents) and `Vic3TimelineExtended_Player_Guide.pdf`; `docs/testing/nuclear-playtest.md` (checks and the Self-checks table); the spec's status line (phase 1 built); `docs/guides/scripting_best_practices.md` only for an engine lesson learned.

- [ ] **Step 1:** Edit the docs; match the guide's depth (no per-term tables the tooltips show).
- [ ] **Step 2: Run** `.venv/bin/python scripts/build_player_guide.py`, then `python3 scripts/analysis/check_player_guide_style.py --strict`, `python3 scripts/build_player_guide.py --check`, `python3 scripts/analysis/check_loc_spelling.py --check`. Expected: all pass.
- [ ] **Step 3: Commit** `Nuclear rework phase 1: design §0, chapter 14, play-test list`.

### Task 11: Gate, PR, review

- [ ] **Step 1: Run** the gate: `pytest -n auto test_nuclear_*.py test_reload_post_load.py`-free subset of the CI steps that cover changed files: `ruff check .`, `scripts/format_paradox_tabs.py --check` on changed `.txt`, `check_localization_files.py`, `organize_loc.py --check` (run the writer if needed and commit), the strict audits CI runs, `check_post_load_rosters.py`, `test_tax_code_bypass.py`, `test_nightly_audit_select.py`. Expected: all pass.
- [ ] **Step 2:** Push, open the PR (body: summary, owner rulings, self-checks, play-test items, "Player guide: chapter 14 updated", review running), then dispatch two fresh reviewers (script; docs/GUI/Python).
- [ ] **Step 3:** Fix findings as commits; merge on reviewer APPROVE plus my agreement and green CI.

---

## Roadmap after phase 1 (separate plans, each written when its phase starts)

- **Probe batch (runs during phase 1).** One auto-running `te_probe_nuclear_rework.txt`, placed in the deploy folder by hand, fires from the first monthly pulse, builds its own fixtures (an AI–AI play with `war = yes` and one without, each with two goal types) and logs `TE_PROBE` lines for §12 rows 1–8 plus D4's `is_target_of_wargoal` in a play. The owner starts any game and lets it run a month.
- **Phase 2:** §8.1 the Suez concession (from the probe's `remove_war_goal` answers), dispute code 6 with the "Honor" fix, §5.4 the claim, belief and the truth. Open: §14.4's lie rate.
- **Phase 3:** §6 the strike planner, counterforce and decapitation; survivors read §6's losses. Open: §14.3 salvo taboo scaling, §14.4 mission weights, §14.5 K against AI arsenal sizes.
- **Phase 4:** §7 range and basing, dispute codes 7–10, §8.6 trades. Open: §14.6 basing host custody.
