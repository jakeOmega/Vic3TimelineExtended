# Nuclear Crisis Rework, Phase 4c: Trades — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Either side of a nuclear crisis over deployment, claims, covert operations or orbital weapons (disputes 7–10) can offer the matching concession of its own, and an accepted trade closes the crisis as outcome 11, "Trade".

**Architecture:** A trade offer is a proposal of talks with terms: it sets the issuer's `nd_crisis_talks = 1` and sends `nuclear_crisis.8` to the other side, as `nd_crisis_act_propose_talks` sends `.3`. Accepting re-checks that both sides still hold the same kind of grievance against each other, runs the existing concession for the target, swaps `scope:nd_issuer`/`scope:nd_target`, runs it again for the issuer, swaps back, and closes with `OUTCOME = 11`. The AI accepts on the spec's rule (pressure 40 for a target; danger 40 for an issuer) when a single size number, `nd_trade_balance_value`, says it gives no more than it gets.

**Tech Stack:** Paradox script (Victoria 3), Python unittest (text-level tests), the mod's offline audits.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` §8.6 (and §8.2 for the weights). What shipped before: `docs/systems/nuclear_crisis_design.md` §0.3, §0.16.

## Global Constraints

- Spec §8.6: "At the deadline, or under Our Moves, either side can offer a matching concession … Accepting closes the crisis as a new outcome, 11, 'Trade': +5 credibility each and no climb-down. The AI accepts at pressure 40 or more when what it gives is no larger than what it gets, on the same weights as §8.2."
- §8.2 weights: annexation 30, subjugation 20, a state transfer 10, a treaty, market, strait or minor goal 4.
- Every `nd_change_credibility` sits next to its `nd_tt_credibility_up|down_N` line (`TestOutcomeNotice`).
- Every use of a scope saved inside an effect file is guarded by `exists` (tooltip passes re-walk effects).
- Loc and guide text are American English; loc keys are filed by `organize_loc.py`; one BOM per `.txt`/`.yml`.
- `docs/systems/journal_entry_systems.md` is CRLF: edit it byte-safe and confirm `grep -c $'\r$'` equals `wc -l` afterwards.
- New `nuclear_guarantee` readers join `TestUmbrellaCoverage.GUARANTEE_READERS`.
- Commits: thematic, staged by path, ending with the session's `Co-Authored-By` and `Claude-Session` lines.

## Rulings carried into the plan (ledger them at Task 1)

- **R1 Which disputes trade.** Same-code mirrors only: 7, 8, 9, 10. The trade holds when the issuer's dispute against the target still holds *and* the target holds the same code against the issuer (`nd_dispute_<what>_by` both ways). Code 5's stand-down for a stand-down is outcome 3, already built. Codes 1–3 and 6 have no matching concession. §8.6's "a freeze for a freeze" is read as code 10 (both sides' battlestation freeze); code 4's freeze cannot mirror, since the target of a proliferation dispute is unarmed and the issuer armed. A code-4 trade would be an added branch later. Cost if wrong: the owner wanted a cross-code or code-4 freeze, which is new work rather than a redesign.
- **R2 The offer is talks.** It reuses `nd_crisis_talks` (pressure pauses, danger −15, the deadline still fires) and `nd_crisis_act_refuse_talks` for the refusal, so every existing reader of "talks under way" counts a pending trade too. `nd_tt_talks_pending` is reworded to cover both. Cost if wrong: the panel says talks are under way for up to three days while a trade awaits an answer.
- **R3 Default answer: refuse.** `.8`'s timeout picks refuse. A concession takes an affirmative click. (`.3` defaults to accept a stand-down, which gives nothing away.)
- **R4 The AI's rules.** An AI target accepts at `nd_yield_pressure >= nd_ai_concession_line` (40), and an AI issuer at `nd_crisis_danger >= nd_ai_trade_danger_line` (40, new). Both also need `nd_trade_balance_value` on their side (target ≤ 0, issuer ≥ 0) and no alliance lost in their own half. The alternative for the issuer, accepting while the target's pressure is under 40 (the threat is not biting), was not taken: pressure starts near 30, so a human target could trade out in the first week. Cost if wrong: AI issuers trade later than the owner wants.
- **R5 Who offers among the AI.** An AI offers only as the issuer, at its deadline (`.4.h`). An AI target never offers. In an AI-against-AI crisis a trade can arise only at the issuer's deadline. Cost if wrong: fewer AI trades than the spec's "either side" suggests.
- **R6 Size.** One number, `nd_trade_balance_value` = what the target gives − what the issuer gives, on §8.2's scale: dispute 7, a basing or guarantee treaty 10 (like a state) and a missile-defense state 4 (a lesser goal); 8, a claimed incorporated state 10; 9, a detected operation 4; 10, an active battlestation site 10. Within codes 8–10 only the counts matter. Cost if wrong: the AI misjudges a mixed code-7 trade.
- **R7 Outcome 11's consequences.** +5 credibility each, no climb-down, no pledge, no stand-down, no taboo ledger points, the usual cooldown for the issuer. The bars the concessions set (deployment, covert, orbital freeze) bind both sides for ten years. Cost if wrong: the owner wanted a modifier or lobby reaction like outcome 3's.

## Review Focus

1. An offer accepted after one half has lapsed (the issuer withdrew its basing in the meantime): it must lapse, never run one-sided. Task 2, `test_accept_rechecks_both_halves`.
2. The swap undone before the close: `nd_crisis_close` reads `scope:nd_issuer` as the record holder, so a stale swap would close the crisis against the wrong party. Task 2, `test_swap_is_undone_before_close`.
3. A trade offered while a stand-down awaits an answer, and the reverse: one proposal at a time. Task 2, `test_one_proposal_at_a_time`.
4. An AI trading away an alliance in its own half, on either side (a withdrawal leaves the whole treaty). Task 3, `test_ai_keeps_an_ally_either_side`.
5. A future dispute code with no trade decision: every code in `DISPUTES` is either in `TRADES` or in `NO_TRADE`. Task 2, `test_every_dispute_decides_on_trades`.

---

### Task 1: Outcome 11 at the close

**Files:**
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (header OUTCOMES comment; `nd_crisis_apply_outcome_side`)
- Modify: `common/scripted_effects/nuclear_observer_effects.txt` (`nd_log_crisis_end`)
- Modify: `events/nuclear_crisis_events.txt` (`nuclear_crisis.6` title and desc chains)
- Modify: `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (`nd_crisis_last_outcome_word`)
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Create: `test_nuclear_trades.py`

**Interfaces:**
- Produces: outcome code 11 accepted by `nd_crisis_close = { OUTCOME = 11 }`; loc keys `nuclear_crisis.6.t_trade`, `nuclear_crisis.6.d_trade`, `nd_last_outcome_trade`.

- [ ] **Step 1: Write the failing tests** — `test_nuclear_trades.py`, class `TestOutcomeEleven`, with an `OUTCOMES` table (1–11, as the effects header lists them):
  - `test_log_names_every_outcome`: `nd_log_crisis_end` holds `outcome=N;` for N in 1..11.
  - `test_trade_pays_five_each`: the `nd_crisis_apply_outcome_side` branch whose limit is `var:nd_crisis_pending_outcome = 11` holds `text = nd_tt_credibility_up_5` and `AMOUNT = 5`, no `var:nd_crisis_pending_role` test and no `nd_crisis_climbdown`.
  - `test_notice_titles_and_describes_a_trade`: `.6`'s title holds `O = 11` → `nuclear_crisis.6.t_trade`, and its desc `O = 11` → `nuclear_crisis.6.d_trade`, both before the `always = yes` fallback.
  - `test_last_word_names_a_trade`: `nd_crisis_last_outcome_word` has a text with `var:nd_crisis_last_outcome = 11` → `nd_last_outcome_trade`, before the fallback.
  - `test_header_lists_eleven`: the header comment lists `11 a trade`.
  - `test_outcome_loc_exists`: the three keys are defined.
- [ ] **Step 2: Run** `python3 -m pytest -q test_nuclear_trades.py` — Expected: 6 failed.
- [ ] **Step 3: Implement.** The `apply_outcome_side` branch sits after outcome 3's. Loc:
  - `.6.t_trade`: "A Bargain Struck".
  - `.6.d_trade`: both names, each side gave up the same kind of thing the other demanded, and neither is seen to have backed down.
  - `nd_last_outcome_trade`: "Each side gave up the same."
  - The log line copies outcome 10's with `outcome=11`.
- [ ] **Step 4: Run** the same — Expected: 6 passed; `test_nuclear_deterrence.py -k "Outcome"` passes.
- [ ] **Step 5: Commit** "Nuclear crisis: outcome 11, a trade, at the close".

### Task 2: Offering and accepting a trade

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt`, `common/scripted_effects/nuclear_crisis_effects.txt`, `events/nuclear_crisis_events.txt` (new `.8`, `.27`), loc files, `test_nuclear_trades.py`, `test_nuclear_disputes.py`

**Interfaces:**
- Consumes: Task 1's outcome 11; the existing `nd_dispute_{deployment,claims,covert_ops,orbital}_by = { TARGET }` and `nd_crisis_concede_{deployment,claims,covert_ops,orbital}`.
- Produces:
  - `nd_crisis_dispute_tradeable` (either party; codes 7–10).
  - `nd_crisis_trade_holds = { ISSUER TARGET }` (both directions hold).
  - `nd_crisis_trade_holds_for_us` (country scope; saves temporary scopes `nd_tr_issuer`/`nd_tr_target` from the record).
  - `nd_can_offer_trade` (country scope, custom_tooltip clauses: in crisis, `nd_tt_talks_pending`, `nd_tt_trade_kind`, `nd_tt_trade_matching`).
  - `nd_crisis_act_offer_trade` and `nd_crisis_act_accept_trade` (either party).
  - `nd_crisis_trade_lines` (per-code line).
  - `nd_crisis_swap_parties`.
  - `nd_crisis_trade_halves = { CODE WHAT }`.
  - `nd_crisis_trade_check_schedule = { CODE }`.
  - Events `nuclear_crisis.8` (the offer) and `.27` (the self-check).

- [ ] **Step 1: Write the failing tests** (`TestTradeOffer`, `TestTradeAccept`, `TestTradeSelfCheck`):
  - `test_holds_reads_both_directions`: for each `(code, what)` in `TRADES = {7: "deployment", 8: "claims", 9: "covert_ops", 10: "orbital"}`, `nd_crisis_trade_holds` holds `$ISSUER$ = { nd_dispute_<what>_by = { TARGET = $TARGET$ } }` and `$TARGET$ = { nd_dispute_<what>_by = { TARGET = $ISSUER$ } }` next to the code test.
  - `test_one_proposal_at_a_time`: `nd_can_offer_trade` carries the `nd_tt_talks_pending` clause with `nd_can_propose_talks`'s body, and `nd_crisis_act_offer_trade` sets `nd_crisis_talks value = 1` and sends `nuclear_crisis.8` through `nd_crisis_send_event`.
  - `test_accept_rechecks_both_halves`: in `nd_crisis_act_accept_trade`'s hidden effect, the branch that calls `nd_crisis_trade_halves` has `nd_crisis_trade_holds = { ISSUER = scope:nd_issuer TARGET = scope:nd_target }` in its limit. Its else branch sets `nd_crisis_talks value = 0`, and calls neither halves nor `nd_crisis_close`. The visible part shows `nd_tt_trade_lapsed` when the trade no longer holds.
  - `test_swap_is_undone_before_close`: `nd_crisis_trade_halves` calls `nd_crisis_swap_parties = yes` exactly twice, with exactly one `nd_crisis_concede_$WHAT$ = yes` between them and one before the first, and no `nd_crisis_close`. In `nd_crisis_act_accept_trade`, `nd_crisis_close = { OUTCOME = 11 }` comes after every `nd_crisis_trade_halves` call. `nd_crisis_swap_parties` is exactly the three saves, issuer→`nd_crisis_swap`, target→`nd_issuer`, `nd_crisis_swap`→`nd_target`.
  - `test_dispatch_names_every_trade`: the accept's dispatch has `var:nd_crisis_dispute = N` → `nd_crisis_trade_halves = { CODE = N WHAT = <what> }` for each of `TRADES`; `nd_crisis_trade_lines` has `D = N` → `nd_tt_trade_<what>`.
  - `test_offer_event`: `.8` has `trigger = { nd_crisis_event_matches = yes }`, `.8.a` → `ACT = accept_trade`, `.8.b` → `ACT = refuse_talks` with `default_option = yes` (R3), and an `event_image`.
  - `test_self_check_both_halves`: `.27` reads `var:nd_tc_other`. For each code it logs `TE_SELF_CHECK BROKEN nd_trade_N` when either direction still holds and `TE_SELF_CHECK OK nd_trade_N` otherwise, and it removes its variables last. `nd_crisis_trade_check_schedule` is once a game per code (`nd_tc_done_$CODE$`), and `nd_crisis_trade_halves` calls it before the first concession.
  - In `test_nuclear_disputes.py`: `test_every_dispute_decides_on_trades`. `TRADES` (imported from `test_nuclear_trades`) ∪ `NO_TRADE = {1, 2, 3, 4, 5, 6}` equals the codes in `DISPUTES`, and the two sets are disjoint.
- [ ] **Step 2: Run** `python3 -m pytest -q test_nuclear_trades.py test_nuclear_disputes.py` — Expected: the new tests fail, Task 1's pass.
- [ ] **Step 3: Implement.**
  - **Triggers.** `nd_crisis_trade_holds` checks the code with `has_variable = nd_crisis_dispute var:nd_crisis_dispute = N` on `$ISSUER$`, starting with `exists = $ISSUER$ exists = $TARGET$`. `nd_crisis_trade_holds_for_us` takes the precedent `var:x ?= { save_temporary_scope_as = y }` (`zz_te_war_support_injections.txt:177`).
  - **Offer act.** Copy `nd_crisis_act_propose_talks` with `nuclear_crisis.8`. Its visible lines are `nd_tt_act_trade`, `nd_crisis_trade_lines`, `nd_tt_trade_cred` and `nd_tt_talks_meanwhile`.
  - **Accept act.** The visible part shows `nd_tt_act_accept_trade` + lines + `nd_tt_trade_cred` when the trade holds, else `nd_tt_trade_lapsed`. The hidden part is `nd_crisis_save_parties`, then the guarded dispatch inside `scope:nd_issuer = { }`, then `nd_crisis_close = { OUTCOME = 11 }`. Its else is guarded on the owner and sets talks and pressure weeks to 0, as the refusal does.
  - **Halves.** `nd_crisis_trade_halves` runs: the check schedule, `scope:nd_issuer = { nd_crisis_concede_$WHAT$ = yes }`, the swap, the same call again, the swap.
  - **The `.27` event.** It mirrors `.26`, with a helper `nd_crisis_trade_check_log = { CODE WHAT }` (precedent for `$X$` in a log string: `decolonization_war_effects.txt:605`).
  - **Loc.** `nd_tt_trade_<what>` is the mutual form of each `nd_tt_yield_<what>` ("Each side leaves …"). `nd_tt_trade_kind` reads "The crisis is over deployment, claims, covert operations or orbital weapons". `nd_tt_trade_matching` reads "They hold the same against us, so each side has the same to give". `nd_tt_talks_pending` becomes "No proposal, to stand down or to trade, is already waiting for an answer". `.8` gets a title, a description, a flavor text and two options.
  - **Docs.** Add `nd_crisis_trade_holds`, plus any new reader of `has_type = nuclear_guarantee`, to `GUARANTEE_READERS`.
- [ ] **Step 4: Run** `python3 -m pytest -q test_nuclear_trades.py test_nuclear_disputes.py test_nuclear_deterrence.py` — Expected: all pass.
- [ ] **Step 5: Commit** "Nuclear crisis: offer and accept a trade (outcome 11)".

### Task 3: The AI's side of a trade

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt`, `common/scripted_triggers/nuclear_deterrence_triggers.txt`, `events/nuclear_crisis_events.txt` (`.8` weights, new `.4.h`), loc, `test_nuclear_trades.py`, `test_nuclear_deterrence.py` (registry)

**Interfaces:**
- Consumes: Task 2's `nd_crisis_trade_holds`, `nd_can_offer_trade`, `ACT = offer_trade`.
- Produces: `nd_trade_balance_value` (parties saved; target gives − issuer gives); `nd_ai_trade_danger_line = 40`; `nd_trade_costs_us_an_alliance` (either party); `nd_ai_accepts_trade` (the receiver).

- [ ] **Step 1: Write the failing tests** (`TestTradeAI`):
  - `test_balance_weights`: `nd_trade_balance_value` per code adds within `scope:nd_target = { }` and subtracts within `scope:nd_issuer = { }`, with 10 and 4 for code 7, 10 for 8, 4 for 9 and 10 for 10 (R6), and code 10 skips a paused site.
  - `test_ai_accepts_on_the_spec_rule`: `nd_ai_accepts_trade` holds a target branch (`THIS = scope:nd_target`, `var:nd_yield_pressure >= nd_ai_concession_line`, `nd_trade_balance_value <= 0`) and an issuer branch (`THIS = scope:nd_issuer`, `var:nd_crisis_danger >= nd_ai_trade_danger_line`, `nd_trade_balance_value >= 0`), plus `nd_crisis_trade_holds` and `NOT = { nd_trade_costs_us_an_alliance = yes }`.
  - `test_ai_keeps_an_ally_either_side`: `nd_trade_costs_us_an_alliance` names `nd_concession_costs_an_alliance` for the target and, for the issuer, an article test with `source_country = scope:nd_issuer` next to `scope:nd_target` together with `has_type = alliance`/`defensive_pact`.
  - `test_answer_weights`: `.8.a` takes `factor = 0` unless `nd_ai_accepts_trade`, and `.8.b` takes `factor = 0` when it holds.
  - `test_deadline_offer`: `.4.h` has `trigger = { nd_can_offer_trade = yes }` and `ACT = offer_trade`, and its `ai_chance` takes `factor = 0` on `nd_trade_balance_value < 0` and on `nd_trade_costs_us_an_alliance`.
- [ ] **Step 2: Run** `python3 -m pytest -q test_nuclear_trades.py -k AI` — Expected: 5 failed.
- [ ] **Step 3: Implement.** `.4.h` weights: base 2, +3 at danger ≥ `nd_ai_trade_danger_line`, +2 cautious, and the two zeros. `.8.a` and `.8.b`: base 1 each with the opposite zero. Register the new `nuclear_guarantee` readers. Loc `.4.h` reads "Offer a trade: theirs for ours."
- [ ] **Step 4: Run** `python3 -m pytest -q test_nuclear_trades.py test_nuclear_deterrence.py test_nuclear_crisis_pacing.py` — Expected: all pass.
- [ ] **Step 5: Commit** "Nuclear crisis: the AI offers a trade at its deadline and accepts on the spec's rule".

### Task 4: The panel

**Files:**
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (op 6; display handler `nd_crisis_tradeable_sgui`), `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (a choice row, an outcome row, the op comment), loc, `docs/systems/journal_entry_systems.md` (CRLF: op table row 6, the display-handler count and list)

**Interfaces:**
- Consumes: Task 2's `nd_can_offer_trade`, `nd_crisis_act_offer_trade`, `nd_crisis_dispute_tradeable`.
- Produces: op 6 of `nd_crisis_action_sgui`.

- [ ] **Step 1: Write the failing tests** (`TestTradePanel`):
  - `test_op_six`: `nd_crisis_action_sgui` maps op 6 to `nd_can_offer_trade` and `nd_crisis_act_offer_trade`.
  - `test_rows_shown_only_for_a_tradeable_dispute`: the choice row (`nd_w_crisis_act_trade`) and the outcome row (`nd_w_crisis_trade_label`) are both `visible` on `nd_crisis_tradeable_sgui`, whose `is_shown` is `nd_crisis_dispute_tradeable = yes`.
  - `test_legend_names_trades`: `nd_w_crisis_actions_legend` mentions a trade.
  - The existing `TestPanelOps` and `LabelBudgetTest` then cover the drawn op and the label widths (18 characters for the outcome label, 20 for the effect, 11 for the credibility and button text).
- [ ] **Step 2: Run** `python3 -m pytest -q test_nuclear_trades.py -k Panel test_nuclear_deterrence.py -k PanelOps test_nuclear_layout.py` — Expected: the new tests fail.
- [ ] **Step 3: Implement.**
  - **Loc.** `nd_w_crisis_act_trade`: "Offer a trade". `nd_w_crisis_act_trade_btn`: "Offer". `nd_w_crisis_trade_label`: "Trade". `nd_w_crisis_trade_effect`: "Each gives the same". `nd_w_crisis_cred_trade`: "$nd_crisis_cred_up_5$". `nd_w_crisis_trade_tt`: a tooltip header plus one sentence.
  - **JE doc** (CRLF edit, checked afterwards): the op table gets `| | 6 | offer a trade (either side) |`, and the display handlers become twenty-one with `nd_crisis_tradeable_sgui`.
- [ ] **Step 4: Run** the same plus `python3 scripts/analysis/check_gui_lint.py` — Expected: all pass; lint clean.
- [ ] **Step 5: Commit** "Nuclear panel: offer a trade under Our Moves, and the Trade outcome".

### Task 5: Docs, guide and play-test list

**Files:**
- Modify:
  - `docs/systems/nuclear_crisis_design.md` (§0.3's outcomes table gains row 11; new §0.17 for trades, with R1–R7)
  - `docs/player_guide/14-nuclear.md` (Moves during a crisis; the outcomes) and the PDF
  - `docs/testing/nuclear-playtest.md` (items for the trade per code, the lapse, the AI's deadline offer; Self-checks row `nd_trade_<N>`)
  - `docs/systems/mod_systems/nuclear.md` (the crisis paragraph)
  - the spec's status line

- [ ] **Step 1: Write the failing test** `TestTradeDocs`:
  - the design doc has `### 0.17` and an outcomes row for 11;
  - the guide's chapter mentions "trade" in its moves section;
  - the play-test list has `nd_trade_`.
- [ ] **Step 2: Run** — Expected: fail.
- [ ] **Step 3: Write the docs.** Rebuild the PDF with `.venv/bin/python scripts/build_player_guide.py`.
- [ ] **Step 4: Run the gate:**
  - the full suite (dummy `VIC3_*`), ruff, the tab check on changed `.txt`, `organize_loc.py` then `--check`;
  - the localization, spelling and player-guide style lints, and `build_player_guide.py --check`;
  - `check_gui_lint.py`, `check_post_load_rosters.py`, and `bash $SP/gate_audits_p4.sh`.

  Expected: all green, "audits done, fail=0".
- [ ] **Step 5: Commit** "Nuclear crisis trades: design §0.17, guide, play-test list".
