# Nuclear Crisis Rework, Phase 2 (Concessions and the Dilemma) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship spec phase 2: the Suez-model war concession (§8.1), dispute code 6 for a peacetime nuclear strike with the "Honor" fix (§8.5), and the victim's dilemma: the launcher's claim, the victim's belief and the truth that follows (§5.4).

**Architecture:** The concession and the new dispute live in the crisis effects and triggers beside codes 1–5. The claim is decided at dispatch, before the victim's `nuclear_weapon_events.1`, and recorded on the victim; `.1` reads it, the AI's belief is one `random` roll in `.1`'s `immediate`, and the truth is a delayed event chosen from literal delays.

**Tech Stack:** Victoria 3 script; Python 3.11/3.12 tests.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` (§5.4, §8.1, §8.5 code 6). Phase 1 shipped as #1222 (`nuclear_crisis_design.md` §0.12).

## Global Constraints

- Worktree `~/src/vic3te-nuclear-p2`, branch `feat/nuclear-rework-p2`, base `d216a24`. No `POST /reload` from here.
- Owner answers (2026-10-28): the AI lies after a deliberate first strike with chance 15%, ×2 under an aggressive ruler, ×0.5 at a taboo of 50 or more; a human makes a false claim through a **"Disavow our strikes" posture toggle** set before striking; unordered launches always carry a true claim.
- Probe facts (2026-10-28): `remove_war_goal` removes the AI's own goals and a play's opening goal, in a play or a war; not script-added goals; `who = <side>` reach untested (accept extra removals and say so); in a war the AI can't re-add goals.
- `debug_log` strings take no `$PARAM$`; `trigger_event` takes one literal delay (a `random_list` of literal branches, as `nd_crisis_send_event_in_transit`); a timed country variable for the 24-month record.
- Every new loc key American, `#b X#!`; GUI op tables kept in step in the widget, the sgui and `journal_entry_systems.md` (CRLF: edit bytes).

## Review Focus

1. **A salvo of several warheads.** `.1` fires once per landed warhead; the claim, the belief roll and the truth must happen once per strike, not once per warhead. Test: Task 4's `test_belief_rolled_once_per_claim`.
2. **A claim on an answer or an incident launch the victim already answered.** A retaliation (`nuclear_response_strike`) never carries a claim; a launch the victim's Automatic Retaliation already answered still gets its truth. Test: Task 3's `test_no_claim_on_an_answer`.
3. **The victim or launcher gone before the truth.** The truth event revalidates both; a dead launcher's lie is never exposed and nothing errors. Test: Task 5's `test_truth_revalidates_parties`.
4. **A war concession with the target as aggressor.** No goals against the issuer: only war support falls, and the tooltip says so. Test: Task 1's `test_concession_without_goals_is_war_support_only`.
5. **Code 6 after the record expires mid-crisis.** Revalidation ends the crisis as outcome 10, not a yield. Test: Task 2's `test_code_6_revalidates_on_the_record`.

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| E1 | The war concession reads the war's side from `is_on_defending_side = scope:nd_target` (war scope) and removes, through the war's `diplomatic_play`, each goal type the target's side holds against the other side (issuer or protégé), `who = target` or `who = initiator` | The UN order triggers' side test; `remove_war_goal` addresses a side and a type |
| E2 | Code 6 means **the target** struck us or a country we cover, outside a war, in the last 24 months | The concession is the target's reparations; a grievance belongs to the struck side |
| E3 | The record is `nd_peacetime_struck_by` on the struck country (the striker, `days = 730`), written in `nd_record_nuclear_use` when attacker and victim are not at war | Nothing dated survives an exchange's close |
| E4 | Reparations reuse `nd_loose_compensation_value` (payer the target, claimant the struck country) and pay at once on yielding; custody inspection reuses `nd_loose_open_to_inspection` on the target | Spec: "the `nuclear_loose.6` formula", "secured custody as `nuclear_loose.6` grants" |
| E5 | Claims only on a **first use** (not an answer), strategic only. The record on the victim: `nd_claim_by` (launcher), `nd_claim_true` (1/0), `nd_claim_id` (a global counter), `nd_claim_landed` (warheads landed from that launcher in the strike, timed 30 days) | One claim per strike; warheads counted for the belief's single-warhead term |
| E6 | A truth event follows only a claim. Delays: 180/270/365/455/545 days; with the victim's covert intel tier 1 on the launcher (`sr_has_intel_tier`), 90/180/270 | "Six to eighteen months, sooner with an established network" |
| E7 | AI belief = 40 + relations ÷ 4 + 20 if one warhead landed − 20 if the launcher is our Acute-crisis opponent − 30 × the launcher's `nd_false_claims`, clamped 5–90; rolled once per claim in `.1`'s `immediate` into `nd_claim_believed` | `random = { chance = <script value> }` works (`nd_roll_launch_hold`) |
| E8 | Accepting a claim: hold back (`.1.a`'s effects) and demand reparations; the launcher gets an event: pay (the formula) or refuse (relations −30). The answer-with-one-warhead path keeps its option (`.1.b`) | Spec's "holding back or answering with one warhead" |
| E9 | The posture toggle is two new ops of `nd_posture_sgui` (70 on, 71 off) in the Posture section, a row like the steppers; it applies to deliberate first strikes ordered while on | Owner's choice |

---

### Task 1: The Suez concession (§8.1)

**Files:** `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_concede_war`), loc (`nd_tt_yield_war`), `test_nuclear_deterrence.py`.

**Interfaces:** Produces `nd_crisis_concede_war_goals` (target scope, `scope:nd_crisis_other_side`): per war with the other side, per goal type of `nd_stakes_*`'s type list held by the target's side against the other side, `remove_war_goal` on the war's play for the target's side; then −15 war support (was −35). A once-a-game `TE_SELF_CHECK OK|BROKEN nd_suez_goals`: a type still held after removal is BROKEN.

- [ ] Write `test_concession_drops_goals_and_15_support`, `test_concession_without_goals_is_war_support_only` (the war support line outside any goal test), `test_concession_side_from_defending_side` (`is_on_defending_side = scope:nd_target`, both `who = target` and `who = initiator`), `test_suez_self_check_line`. Run: FAIL.
- [ ] Implement; tooltip: "We drop our war goals against them (and any of the same kind our side holds in this war), and our war support falls by #R 15#!". Run the tests, the audits gate. PASS.
- [ ] Commit `Nuclear crises: the war concession drops the target's goals (Suez model, spec §8.1)`.

### Task 2: Dispute code 6, a peacetime strike, and the Honor fix (§8.5)

**Files:** the crisis effects (classification, revalidation, yield, yield lines, back-down, preview, stakes demander), the triggers (`nd_dispute_peacetime_strike_by`, `nd_has_crisis_dispute_with`, `nd_crisis_issuer_is_defensive`, `nd_ai_would_warn`), `nd_record_nuclear_use`, the custom loc's six dispute texts, loc, tests.

**Interfaces:** Produces `nd_peacetime_struck_by` (victim, `days = 730`), `nd_dispute_peacetime_strike_by = { TARGET }` (issuer scope: the target struck us or a country we cover, the beneficiary saved as `nd_crisis_ben` by the classifier), code 6 classified in the order 2, 1, 3, 6, 4, 5, and the yield `nd_crisis_concede_reparations` (E4).

- [ ] Write `test_code_6_classified_between_guarantee_and_proliferation`, `test_code_6_at_every_site` (the eight crisis-effect sites, the four triggers, the six custom-loc texts each name 6 or the new trigger), `test_record_written_outside_war`, `test_code_6_revalidates_on_the_record`, `test_honor_after_peacetime_strike_opens_a_crisis` (`nd_has_crisis_dispute_with` reaches the new trigger). Run: FAIL.
- [ ] Implement. The AI warns over code 6 as a defensive dispute. Run tests + audits. PASS.
- [ ] Commit `Nuclear crises: a peacetime strike is a dispute (code 6); Honor after one opens a crisis`.

### Task 3: The claim (§5.4)

**Files:** `nd_dispatch_strategic_strike` / `nd_launch_or_intercept` (`nuclear_deterrence_effects.txt`), `nuke.txt`'s strategic strike (`nuclear_first_strike` direct call), new `nd_record_claim` effect, `nd_ai_lies_value` (values: 15, ×2 aggressive, ×0.5 taboo ≥ 50), the posture toggle (`nd_posture_sgui` ops 70/71, widget row, loc, `journal_entry_systems.md` op table), observer records `type=claim`.

**Interfaces:** Produces the E5 record on the victim; `nd_disavow_strikes` (country var) set by the toggle. A claim is made when: the launch is unordered (true); or a deliberate first strike by a human with `nd_disavow_strikes` (false); or by the AI on an armed target with one warhead, rolled `nd_ai_lies_value` (false). Answers never claim.

- [ ] Write `test_no_claim_on_an_answer`, `test_unordered_launch_claims_true`, `test_ai_lie_rate` (the value's 15 / ×2 / ×0.5), `test_toggle_ops_in_step` (widget, sgui, doc), `test_claim_record_once_per_strike` (`nd_claim_id` from a global counter, `nd_claim_landed` incremented per landed warhead). Run: FAIL.
- [ ] Implement. Run tests, GUI lint, audits. PASS.
- [ ] Commit `Nuclear strikes: a launcher may claim the strike was unauthorized (spec §5.4); Disavow our strikes`.

### Task 4: The victim's answer (§5.4)

**Files:** `events/nuclear_weapon_events.txt` (`.1`: claim desc, belief roll in `immediate`, new option "Accept it was unauthorized" between c and g; a new launcher event "Reparations Demanded"), `nd_claim_belief_value`, loc, tests.

**Interfaces:** Consumes Task 3's record. Produces `nd_claim_believed` (victim, per `nd_claim_id`), the reparations demand (E8).

- [ ] Write `test_belief_rolled_once_per_claim` (guarded by `nd_claim_belief_rolled_for = nd_claim_id`), `test_belief_value_terms` (40, ÷4, +20, −20, −30, clamp 5–90), `test_accept_option_gated_on_a_claim` (and not under `nd_auto_answers_strike`), `test_reparations_event_pay_or_refuse`. Run: FAIL.
- [ ] Implement. Run tests + audits. PASS.
- [ ] Commit `Nuclear strikes: the victim weighs the claim; accepting it demands reparations`.

### Task 5: The truth (§5.4)

**Files:** new events (victim: "It Was an Accident" / "It Was No Accident"; launcher: "Our Lie Is Exposed"), `nd_claim_truth_send` (random_list of literal delays, E6), consequences, `nd_false_claims`, reconciliation option, observer records, tests.

- [ ] Write `test_truth_delays_are_literal`, `test_truth_revalidates_parties`, `test_exposed_lie_costs` (−20 credibility, taboo-scaled infamy, −50 relations, `nd_false_claims` +1), `test_rejected_true_claim_offers_reconciliation`. Run: FAIL.
- [ ] Implement. Run tests + audits. PASS.
- [ ] Commit `Nuclear strikes: the truth comes out (spec §5.4)`.

### Task 6: Observer, docs, guide, play-test list; gate, PR, review

- [ ] `nuclear_observer_report.py`: claims made, true and false, believed, exposed (a fixture test).
- [ ] `nuclear_crisis_design.md` §0.13, chapter 14 (Crisis subjects, Moves, What a nuclear strike does, A nuclear exchange before war) + PDF, play-test items and self-check rows, spec status.
- [ ] Gate (full suite, CI audits, lints), push, PR, two fresh reviewers (script; docs/GUI/Python), one fix pass, merge on green CI and agreement.
