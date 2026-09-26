# Civil-war audit: Vic3TimelineExtended vs. the verified revolution-merge behaviour

**Status (2026-09-26): F1–F7 are fixed, and F13's pointer half with them** (#460–#465, one PR, branch
`fix/civil-war-inheritance`), under the owner's ruling that **a revolution's winner continues the nation**.
That PR also added `je_immediate_reset_audit`, which flags the E3 bug class in every journal entry. F8–F12
and F14–F16 are open. Only F3's copy depends on reading the dead loser at `on_civil_war_won`: its
`TE_CW_PROBE` lines in `debug.log` settle that on the first rebel win. This report was added in #459. The engine rules the findings rest on are summarised in
`docs/guides/scripting_best_practices.md` § "What a Civil War's Winner Inherits".

Read-only audit (no repo edits, no reload). Evidence: the three German-revolution saves
(`german_civil_war_ongoing.v3`, `_rebel_win.v3`, `_after2w.v3`; loser = GER id 5, rebel/winner = GER id
16777306) and the repo at `7aeeab1a`. Line numbers are as of that commit.

**Reproduce** with `scripts/analysis/save_country_probe.py`: variables, modifiers, journal entries and
their modifiers, and the MERGE summary (`--diff <before> <after> --tag GER`). Variable lists, script
containers and third-country references were read with ad-hoc decoders that were not kept. E1, E3, E4
and F4 were re-checked independently against the saves before this report was committed.

Cross-cutting fix site: the mod hooks neither `on_civil_war_won` nor `on_revolution_end`
(`git grep on_civil_war_won -- common` finds nothing). `on_civil_war_won` has ROOT = winner and runs after
the merge (verified), so one "post-revolution repair" effect there can re-derive trackers, re-apply
permanent rewards and re-seed stocks. Fix directions below assume that hook unless stated.

**The loser is still present at `on_civil_war_won`**, which makes a lossless repair plausible. The win save
was taken after vanilla's `on_civil_war_won` had already run: the winner's inherited `anti_monarchist_revolution` had
been consumed, and `abolishing_monarchy_var` had been reset from the rebel's 19 to 0, which is exactly what
that hook does. Yet the loser (id 5) is still in the database with
all 438 variables, 39 modifiers, its 240-container `te_hist` list and its JE records, modifiers included. It
was deleted within the next two weeks.

Candidate mechanism:
1. At `on_revolution_start` (ROOT = parent, scope:target = rebel), run
   `scope:target = { set_variable = { name = te_parent_object value = ROOT } }`. That variable exists only on
   the rebel, so it survives the merge as the winner's own value.
2. At `on_civil_war_won`, use `var:te_parent_object ?= { ... }` to read the loser's stocks (`te_bank_gold`,
   `st_res_*`), its JE modifier set (`je:je_banking_cycle = { has_modifier = ... }`), its country modifiers,
   its lists (`every_in_list`) and its completion state, and copy them onto ROOT.

**Unverified, and cheap to test:** whether a dead-but-undeleted country object resolves through a stored
scope variable (`exists`, `has_modifier`, `var:` reads). A debug event printing `var:te_parent_object.var:te_bank_gold`
from `on_civil_war_won` would settle it. Hints that it does: third-country pointers to id 5 still exist at +2w,
and vanilla's `on_secession_end` comment says "owned by a dead country at this point".
Loyalist wins are unverified too. Presumably the original keeps its own JEs and modifiers, so most findings
would not apply there, except the dangling references to the dead rebel object (F13-F14).

**Open item: interest-group and state modifiers.** Not tested. The winner's interest groups are different
objects from the loser's, so IG modifiers the mod applies (`un_sovereignty_resentment/_welcome_ig_modifier`,
event-granted IG approval modifiers) are presumably lost like country modifiers. The UN ones are re-applied
by `un_regime_refresh_country` on the next epoch/rejoin; one-off event IG modifiers are not. Whether state
objects survive the ownership change (and keep their modifiers) is also unknown. Confirming either needs a
decoder for the IG and state blocks in the win save, which this audit did not build.

---------------------------------------------------------------------------------------------------

## 0. New engine facts from the saves (these answer the brief's open items)

E1. **Inherited JEs (`can_revolution_inherit = yes`, and the unset default) lose ALL their modifiers.**
    The winner gets a NEW JE record (new id, owner = winner, active = 1). The start date and the
    scripted-progress-bar values are copied from the loser's record. The modifier list is EMPTY.
    Save proof (`je_mods.py german_civil_war_rebel_win`): the loser's `je_banking_cycle` carried 10
    modifiers (banking_export_credit_facility, banking_stance_band_1, banking_capital_controls_out,
    te_mon_stance_politics_loose, te_mon_board_seigniorage, te_monetary_rate_paid, te_inflation_band_hyper,
    te_fx_weak, financial_cycle_government_fiscal_policy_effect, financial_cycle_phase_panic) and the winner's
    copy carried none, with identical bars (6.594 / 2.629 / 2.0 / 0). Same pattern for je_united_nations
    (12 modifiers -> 0), je_covert_warfare (3 -> 0), je_global_warming (8 -> 0), and the inactive-but-started
    je_space_race_orbital (2 -> 0).
    **This contradicts the repo's documented model in both halves** ("the entry and its modifiers move to
    the successor tag while the country variables do not"): `docs/guides/scripting_best_practices.md:3953`,
    `docs/systems/monetary_policy_design.md:290`, `docs/systems/mod_systems.md:411`,
    `common/scripted_effects/banking_cycle_effects.txt:2271-2277`,
    `common/scripted_effects/civil_rights_effects.txt:15-19`, `common/script_values/te_monetary_script_values.txt:24`,
    `common/scripted_effects/te_monetary_effects.txt:2038`. All of them need correcting.
E2. **The unset default is `can_revolution_inherit = yes`.** Vanilla je_strike, je_communism_2,
    je_liberalism_1 and je_skyscraper_construction don't set the key, and all four were inherited active.
    (The vanilla `journal_entries.md:405` also says "Revolutions also get all variables from the defeated
    parent country".) So je_strategic_reserve (unset) is inherited too.
E3. **`immediate` re-runs on an inherited JE, apparently after the variable merge.** `finance_cycle_value`
    went 6.594 -> 50 and `finance_cycle_momentum` went 2.629 -> 0 on the winner in the win save. The only writer
    of 50/0 in the mod is `je_banking.txt:145-146` (in `immediate`, with no guard), and the rebel had no banking
    record before the win. The has_variable-guarded `covert_tradecraft_init` (`je_covert_warfare.txt:111-121`)
    left the inherited `iw_tradecraft = 62.904` intact, which fits `immediate` running after the merge. The
    bars kept the loser's values rather than immediate's 50/0, so bar values are restored after `immediate` runs.
    (That ordering is the most economical reading of the data, not directly observed.)
E4. **Variable LISTS are not inherited at all**, not even when the winner has no list of that name.
    The loser's `te_hist` list (240 containers) is missing from the winner in both later saves, while the
    scalar pointers into it (`te_hist_cur`, `te_hist_cur_i`, `te_hist_now_i`, `te_hist_since_*`) were
    inherited. The loser's `te_tp_*_markets` lists were not merged either.
E5. **Completed JEs are forgotten.** The winner got fresh inactive records for JEs the loser had
    completed: je_civil_rights (loser held `civil_rights_triumph_gradualist_modifier` + `cr_*` vars),
    je_space_race_suborbital (`sr_completed_suborbital`), je_communism_1 (`communism_1_done`), je_fascism_1,
    je_kaiserforum, je_german_unification_idea. Any of these whose `possible` still holds re-activates
    (je_civil_rights did, see F4).
E6. **References to the dead loser persist two weeks after the win** (`h3_raw.py german_civil_war_after2w`):
    5x `te_mon_anchor`, 1x `te_mon_receiver`, 1x `te_mon_swap_provider` on third countries; 3x covert
    `iw_target`; UN resolution records (`un_res_proposer`, `un_res_mandate_beneficiary`, `un_res_cooldown`, ...);
    and one UN mission's `un_msn_host`. Only STG's `te_mon_anchor`/`te_basket_market_owner` and the global
    `nuke_rank_*` were repointed at the winner. In the decoded global-variable block (an ad hoc token walk over the first 256 KB), nothing pointed at
    GER except `nuke_rank_*` (recomputed) and vanilla's `german_confederation_country_list`.

---------------------------------------------------------------------------------------------------

## Findings, most severe first

### F1. Agricultural-diffusion arable-land bonuses are lost permanently (H1: re-apply not hooked). HIGH (#460)
- **FIXED (#460).** The backfill now also runs on `scope:target` at `on_revolution_start` / `on_secession_start`, on the winner at `on_civil_war_won`, and at the overlord- and company-subject release hooks. The first-mover reward is restored from a new grant-month record (`agdiff_first_mover_month`), not from the permanent `is_world_first_<tech>`, at the strength it had decayed to. Rewards granted before the fix have no record and are not restored. `first_<tech>_country` is re-pointed from the dead loser.
- `common/scripted_effects/agricultural_diffusion_effects.txt:125-141` (`agdiff_backfill_one_tech` /
  `agdiff_backfill_diffusion_for_country`) is stateless and correct: it adds `agdiff_<tech>` when
  `world_first_<tech>` is set and the modifier is missing. But it is wired only into `on_country_formed` and
  two release hooks (`common/on_actions/extra_on_actions.txt:3107-3156`). Nothing calls it on
  `on_civil_war_won` or `on_revolution_start`.
- What the player sees: five permanent country modifiers vanish with the loser. Together they are +130%
  `state_arable_land_mult` (+0.15 / +0.15 / +0.60 / +0.15 / +0.25; `extra_modifiers.txt:7318-7351`). Nothing
  re-adds them, so the new regime's farms lose their Green-Revolution capacity for the rest of the game. The
  same goes for `agdiff_first_mover_prestige` if the loser was first (its `is_world_first_<tech>` variable is
  inherited, but the modifier never comes back). The rebel also lacks the bonuses for the whole war (H5).
- Evidence: SAVE-CONFIRMED. The loser held all 5 `agdiff_*`; the winner has none at the win or at +2w.
- Fix: call `agdiff_backfill_diffusion_for_country` from `on_civil_war_won` and, for scope:target, from
  `on_revolution_start`/`on_secession_start`. Re-add the first-mover modifier from `is_world_first_<tech>`.
  (`on_country_released_as_overlord_subject` / `_company_subject` are missing from the release hooks too.)

### F2. UN membership, seat, programmes and HQ-host status are silently dropped (H1: the state is JE modifiers). HIGH (#461)
- Membership is `un_member_modifier` on the JE (`common/scripted_effects/un_ladder_effects.txt:618-621`).
  The permanent seat is `un_permanent_member_modifier` on the JE
  (`common/scripted_triggers/un_permanent_member_triggers.txt:15-17`). Programmes (`un_champion_order_cost`,
  `un_development_contributor_*`, peacekeeping) are JE modifiers toggled by buttons
  (`common/scripted_buttons/un_buttons.txt:630-690, 841-907`). E1 wipes all of them. The only automatic
  rejoin needs a treaty obligation (`je_united_nations.txt:333-343`). Otherwise the AI clicks
  `un_join_button`, and a player has to.
- What the player sees:
  - After the win, Germany is out of the UN: no benefits, no vote, and its programmes have ended.
  - A non-member's pulse deletes the programme duration counters (`un_standing_effects.txt:153-173,
    276-284`). The 337 months of champion/development credit are gone.
  - A permanent member loses its veto seat. `un_seat_monthly_update` then refills the seat by prestige.
  - The regime modifiers are gated by the inherited `un_regime_stamp` (`un_regime_effects.txt:84-111`), so
    they come back only on a rejoin or the next epoch.
  - If the loser hosted the UN headquarters, `global_var:un_hq_country` still names the loser. While the loser
    lingers, the winner counts as "not host", so `un_hq_enforce_single_building`
    (`un_hq_effects.txt:92-110`) demolishes the HQ in German territory. Once the loser is deleted,
    `un_hq_monthly_update` (`:151-165`) moves the HQ to another member.
- Evidence: SAVE-CONFIRMED for membership and programmes. The winner's JE had 0 modifiers at the win. By +2w
  the winner had rejoined via the button or a treaty obligation (membership and conventions back), but the champion and development
  programmes were gone and both month counters deleted. Seat and HQ are CODE-INFERRED (GER held neither;
  `un_hq_country` = country 88 in all three saves).
- Fix: mirror each UN state modifier with a country variable (`un_member`, `un_permanent_seat`,
  `un_prog_<x>`) and rebuild the JE modifiers from those variables in the repair hook. Also re-point
  `un_hq_country` to ROOT when it names a dead same-tag object.

### F3. The central bank's gold and the whole monetary state are replaced by the rebel's (H2). HIGH (#462)
- **FIXED (#462), pending the probe.** The audit's preferred option, with the pointer renamed `te_cw_parent` (system-neutral; contract at the foot of `te_monetary_on_actions.txt`). On a rebel win `te_monetary_inherit_central_bank` adds the two vaults and their hot money, and copies the loser's inflation, peg and FX state and the player's mandate, delegation and regime. It copies no tracker, and re-adds the peg's timed modifiers from their month counters. It logs `TE_CW_PROBE monetary 1/2` and `2/2`.
- `common/on_actions/te_monetary_on_actions.txt:222-262` initialises the rebel at `on_revolution_start`
  (dispatching `te_monetary_internal.1`, `events/te_monetary_events.txt:56-63`). Under winner precedence,
  the rebel's value then beats the nation's on every `te_*` variable. The vault `te_bank_gold` is seeded
  once per country (`te_monetary_effects.txt:2771-2775`, `te_bank_gold_seeded`) from that country's OWN
  limit (`te_monetary_script_values.txt:2918-2923`) and is never re-seeded.
- What the player sees:
  - Germany's vault drops from 111.5M to 2.8M (3.6M at +2w); `te_gold_hot_money` drops from 32.4M to 2.8M.
  - Inflation falls from 54.6% (band 6, hyperinflation) to 5.1%; `te_fx_index` goes from 61 to 100.
  - `te_peg_suspended_months` 35 -> 0 and `te_mon_hyper_cooldown` 22 -> 0.
  - The player's chosen central-bank mandate `te_mon_mandate` changes from 2 (growth) to 3 (peg defence).
  - In short, the revolution cures hyperinflation and empties the vault at a stroke. The timed
    `te_mon_peg_suspension`/`te_mon_peg_credibility_lost` modifiers (country modifiers,
    `events/te_peg_events.txt:123-130`) are lost as well.
- Evidence: SAVE-CONFIRMED (`var_table.txt`, BOTH-diff rows).
- Fix: in fiction, the side that takes the capital takes the central bank. Options:
  - Preferred: in the repair hook, copy the loser's `te_bank_gold`, `te_gold_hot_money`, inflation and
    peg state onto ROOT through `var:te_parent_object`, which is still readable if the check above passes.
  - Fallback: don't seed the rebel's vault or regime state at `on_revolution_start` (give it just enough to
    price its loans), so the loser-only values win the merge.

### F4. Completed JEs re-arm: the civil-rights movement restarts from scratch (H4 via E5). HIGH (#463)
- **FIXED (#463).** `civil_rights_resolved` is set at `on_complete` / `on_fail` and blocks the entry. The outcome modifiers (all twelve are 10-year decaying) are recorded and rebuilt at `on_civil_war_won` for the time they had left. An inherited active run keeps its counters (`cr_run_in_progress`), and the six button policies are mirrored in `cr_policy_*` and rebuilt. Correction to the sweep below: a *completed* `je_human_augmentation` / `je_mental_health` doesn't just re-arm, it completes again at once and replays its outcome event, because their `possible` is technology-only. Both now carry a resolved variable, set at timeout too.
- `common/journal_entries/je_civil_rights.txt:5-19` has no completed/failed guard
  (`possible = has_active_civil_rights_movement`). Its `immediate` (`:40-63`) zeroes all six
  `cr_*_months`, removes `cr_tier_*_seen` and sets the bar to 30.
- What the player sees: Germany had already won its civil-rights struggle; the reward
  `civil_rights_triumph_gradualist_modifier` is itself a country modifier and was lost. Two weeks after the
  revolution the entry is active again at 30%. Its path counters are wiped, the tier notices re-arm (the
  tier-25 flag had already been re-set), and the completion rewards can be earned a second time.
- Evidence: SAVE-CONFIRMED. The winner got a fresh [0] record at the win. At +2w it is active, with
  `cr_*_months` 0/0/0/0/0/1, `cr_tier_50/75/90_seen` gone, `cr_tier_25_seen` re-set, and
  `civil_rights_phase_growing_modifier` on it.
- Fix: set a `civil_rights_resolved` country variable in on_complete/on_fail (variables survive the merge)
  and require its absence in `is_shown_when_inactive`/`possible`. je_colonial_empire already does this with
  `colonial_empire_completed` (`je_colonial_empire.txt:23-30`). The same audit applies to every mod JE that
  can complete or fail. Checked: space race and colonial empire are guarded by variables; heir education by
  the heir; digital rights and post-scarcity are guarded by their target law. Human augmentation and mental
  health can re-run after a timeout/fail (low).

### F5. Space-race rewards are lost for good, and an active milestone's progress is reset (H1 + H4). HIGH (#464)
- **FIXED (#464).** Milestone rewards come back at `on_civil_war_won`. Probe results are recorded and re-added. Choice, approach and colony-specialisation modifiers (the 68 `sr_colony_*` and `sr_solar_system_trade`, which this report missed) are rebuilt from their variables by the entries' `immediate` and a monthly self-heal. The milestone `immediate` sets are guarded, with the goal pinned by `goal_add_value`. Also fixed, all missed above: `je_space_race_interstellar_results` restarting its 132-month transit, the choice events firing a second time, and a finished solar colonization re-opening.
- Rewards: `common/scripted_effects/space_race_effects.txt:404-412` adds `sr_first_<m>` / `sr_<m>` as
  permanent COUNTRY modifiers on completion. The inherited `sr_completed_<m>` then blocks the JE forever
  (`je_space_race.txt:29-34`).
  - Choice rewards are JE modifiers (`events/space_race_events.txt:4285`:
    `je:je_space_race_orbital = { add_modifier = sr_choice_orbital_military }`), gated by variables such as
    `sr_orbital_military`, so they can't be re-chosen.
  - The interstellar probe results (`sr_probe_*_data`, `events/probe_result_events.txt:1018+`) are
    permanent country modifiers too.
- Active milestone (via E3): an in-progress `je_space_race_<m>` is inherited, but its `immediate` re-runs
  and resets `sr_progress_<m> = 0` and `sr_funding_<m> = 1` with no guard (`je_space_race.txt:39`, `:162`,
  `:287`, `:413`, `:537`, `:663`, `:794`, `:1038`). That is the same warhead-progress reset the nuclear
  entry suffers, but on entries that ARE inheritable. The approach modifiers (JE) are lost while
  `sr_safe_<m>` stays set. The cost/funding modifiers are re-derived statelessly (`:541-554`), so those are fine.
- What the player sees: Germany was first to sub-orbital flight (`sr_first_suborbital`: +2% prestige, +25
  innovation cap, +10% cultural pull). After the win the modifier is gone and never comes back. A milestone
  at 90% drops to 0% the day the revolution succeeds.
- Evidence: rewards SAVE-CONFIRMED. The loser held `sr_first_suborbital`; the winner doesn't at +2w. The
  loser's orbital record carried `sr_choice_orbital_military` + `sr_safe_approach`; the winner's copy
  carries neither. The progress reset is CODE-INFERRED (the saves have no active milestone).
- Fix: in the repair hook, re-add `sr_first_<m>`/`sr_<m>` from `sr_completed_<m>` + `sr_was_first_<m>`, and
  re-add the choice and probe modifiers from their variables. Guard the milestone `immediate` sets behind
  has_variable.

### F6. The banking cycle resets to 50 because `immediate` re-runs (H4 via E3). HIGH (#465)
- **FIXED (#465).** The three cycle variables are seeded only when absent, and the bars are drawn from them.
- `common/journal_entries/je_banking.txt:143-156`: `immediate` sets `finance_cycle_value = 50`,
  `finance_cycle_momentum = 0`, `bubble_pressure = 0` and the four bars, all with no guard.
- What the player sees: loyal Germany was in a deep panic (cycle 6.6, momentum +2.6). The day the rebels win,
  the cycle jumps to 50 ("stable"), while the bar still shows 6.6 until the next pulse. A revolution silently
  cures a panic (or deflates a boom), and bubble pressure is wiped.
- Evidence: SAVE-CONFIRMED (win save: 6.594 -> 50.0 and 2.629 -> 0.0; the only writer is `:145-146`).
- Fix: guard the three variable sets behind `NOT = { has_variable = finance_cycle_value }` and set the bars
  from the variables. The monetary variable contract already bans unguarded initialisation in this
  `immediate` (`mod_systems.md:411`); these cycle variables predate that rule.

### F7. The banking stance band is never re-added because its swap trusts the stored `_applied` tracker (H1). MEDIUM (#465)
- **FIXED (#465).** `immediate` sets `te_mon_stance_band_applied` to 0, and a 0 tracker makes the swap clear all five bands before adding. A one-time migration (`banking_stance_band_healed`) heals saves already hit.
- `common/scripted_effects/banking_cycle_effects.txt:2280-2316` (`banking_cycle_apply_stance_band`) swaps only
  when `te_mon_stance_band_applied != te_mon_stance_band`. The first-run sweep at `:2281-2289` was written
  for revolutions, but it fires only when the tracker is ABSENT. Its premise (comment `:2271-2277`) is false
  (E1).
- What the player sees: the loser had band 1 applied, and `te_mon_stance_band_applied = 1` was inherited.
  The winner's band is also 1, so no swap runs. `banking_stance_band_1` (+0.04 investment-pool contribution,
  and the JE's "Monetary Stance" line) stays missing until the band changes. (Removing an absent
  modifier logs an error at country scope. At journal-entry scope the monthly phase sweep suggests it
  is silent: the 2026-09-25 logs have none for it.)
- Evidence: SAVE-CONFIRMED. At +2w the banking JE has no `banking_stance_band_*`; tracker = 1, band = 1.
- Fix: run the sweep when the JE carries none of the five bands, instead of keying it on a missing tracker.
  Or zero the tracker in the repair hook.
- Checked and fine: the other JE-homed monetary modifiers. `te_monetary_settle_modifier_home`
  (`te_monetary_effects.txt:414-489`) saw the home change 0 -> 1, stripped everything, zeroed its five
  trackers and re-applied. The rest re-add on a missing modifier. Confirmed at +2w (band/stance/rate/carry
  modifiers are on the winner's JE). The "canary" at `:426-445` would also catch a lost JE whose home didn't
  change.

### F8. Button-toggled policies whose only state is a JE modifier are switched off (E1). MEDIUM
- Banking tools: `banking_policy_effects.txt:12-140`; the `banking_tool_*_active` checks are
  `has_modifier` on the JE (`market_triggers.txt:60-95`). The same applies to:
  - Command-economy and cooperative tools.
  - Global-warming policies (`global_warming_effects.txt:13-160`).
  - Cultural-hegemony programmes (`cultural_hegemony_effects.txt:167-230`).
  - UN programmes (F2).
  - The event-chosen world-war JE modifiers (`world_war_je.txt:289-297`).
- What the player sees: every policy the player paid to activate is off after the win. The emergency-liquidity
  refund on disable (`banking_policy_effects.txt:139`) can no longer be collected. Market-wide policies
  (carbon tax, renewables) come back only if the market leader re-applies them. There is no stored tracker,
  so the state is at least consistent.
- Evidence: SAVE-CONFIRMED. The loser had banking_export_credit_facility and banking_capital_controls_out; the
  winner has neither at +2w. The loser had green_building_codes_modifier and public_transit_modifier; the
  winner lacks both at +2w (the other GW policies were re-applied by the AI/market).
- Fix: decide whether "new regime, clean slate" is the intended fiction. If not, mirror each toggle in a
  country variable and rebuild the modifiers from those variables in the repair hook. Either way, document
  the choice. The cultural-hegemony funding level is already variable-driven and survives
  (`ch_refresh_funding_modifiers`, `:128-136`).

### F9. History charts are wiped: the sample list isn't inherited and the containers die with the loser (E4). MEDIUM
- `common/scripted_effects/te_history_effects.txt:1-110`: samples are containers parented to the recording
  country ("the engine culls the containers when the country stops existing"), indexed by the country list
  `te_hist`.
- What the player sees: every history chart (banking, monetary, global warming, UN, cultural hegemony,
  colonial) is empty after the win, and the 240 retained months are gone. A sample recorded in the month of
  the win lands in `te_hist_cur`, the loser's container, and is lost too.
- Evidence: SAVE-CONFIRMED. The loser's `te_hist` held 240 containers; the winner has no `te_hist` list at
  the win or at +2w; the loser's containers are gone from the +2w save.
- Fix: the engine won't merge the list, but the loser and its containers still exist at `on_civil_war_won`.
  If `var:te_parent_object` resolves (see the cross-cutting note), the repair hook can copy each sample's
  variables into containers parented to ROOT, iterating the loser's `te_hist`, and rebuild ROOT's list. The
  structural alternative is to parent samples to something that outlives the country object (a global
  container keyed by tag). At minimum, clear `te_hist_cur`/`te_hist_cur_i` in the repair hook and document
  the loss.

### F10. Own covert operations restart at month 0 and networks are lost (E4 + container parent). MEDIUM
- `common/scripted_effects/covert_warfare_effects.txt:4-64`: ops and networks are containers parented to the
  operator and listed in the operator's `iw_ops` / `iw_nets`. Neither list is inherited, and the containers
  are culled with the loser. `covert_op_sync` (`:887-935`) gives any pact without a container "one at
  month 0".
- What the player sees: if the loser's covert pacts carry over to the winner (engine behaviour unverified),
  every running operation drops back to the preparatory phase. The per-target networks built up over years
  are gone either way. Tradecraft (`iw_tradecraft`, a scalar) survives.
- Evidence: CODE-INFERRED for pact carry-over. The lists/containers mechanism is SAVE-CONFIRMED via E4 (GER
  ran no operations in these saves). Foreign operators' containers targeting the dead loser are guarded with
  `?=` and reaped (`:676-691`, `is_country_alive`), which is safe.
- Fix: in the repair hook, copy `iw_duration` and network strength from the loser's containers
  (`var:te_parent_object`, if readable) onto the re-created ones. Or accept it as the new regime's service
  starting over, and document the choice.

### F11. Strategic-reserve stocks are dropped when the rebels held a hub (H2). MEDIUM
- `je_strategic_reserve` is inherited (E2). Its init is guarded (`st_res_effects.txt:40-104`). But if a
  Strategic Reserve Hub sits in a rebel-held state, the rebel's own JE activates (`possible` = owns a hub)
  and seeds `st_res_<good>_stored = 0`. Winner precedence then keeps the zeros. Separately, when the loser
  loses its only hub at war start, `invalid` -> `st_res_reset_vars_effect` (`:130-140`) zeroes its stocks.
- What the player sees: a nation's stockpiled grain, ammunition, oil and so on vanishes when the rebels take
  the depot and then win.
- Evidence: CODE-INFERRED (no reserve in the saves).
- Fix: at `on_revolution_start`, move `st_res_*` stocks to the rebel if it holds the hub state (in fiction,
  the rebels seized it). Otherwise don't initialise the rebel's reserve until the war ends.

### F12. Homeland projects reset whenever a state's owner object changes. LOW-MEDIUM
- `common/scripted_triggers/homeland_triggers.txt:46-55, 68-77`: a project is valid only while
  `var:te_homeland_state.owner = var:te_homeland_owner`, a stored country object. States pass to the rebel
  object at war start and to the winner object at the win. Both events invalidate every project in those
  states, and `homeland_effects.txt:47-60` finishes them; a new project starts at 0.
- What the player sees: years of homeland creation/removal progress in Germany restart after any civil war,
  even though the nation is the same.
- Evidence: CODE-INFERRED (no GER-owned projects in the saves: `te_homeland_owner` never names id 5 or
  16777306).
- Fix: compare by tag (`owner = { has_tag = ... }`) or treat a same-tag owner as unchanged. If that's
  intended conquest semantics, document it.

### F13. Monetary arrangement pointers keep naming the dead loser (H3). LOW
- **Pointer half FIXED (#462).** `te_mon_cw_repoint_to_winner` repoints `te_mon_anchor` / `te_mon_swap_provider` / `te_mon_lolr_guarantor` / `te_mon_receiver` on third countries to the winner, and flags them for discovery. It rests on the same loser read as F3.
- `te_mon_anchor` / `te_mon_receiver` / `te_mon_swap_provider` on third countries (E6: D42, E17, NEJ, SOK, UNL,
  POR). Every read is guarded with `exists = var:te_mon_anchor` or `?=`
  (`te_monetary_arrangement_effects.txt:60-66, 260-275`; `te_monetary_arrangement_triggers.txt:24-32`), and
  discovery rewrites the pointer when the treaty's target differs (`:455-466`).
- What the player sees: countries pegged to Germany keep last month's anchor figures until their next
  flagged or yearly discovery. A swap line drawn from the old Germany is settled to a provider that no longer
  exists.
- Evidence: SAVE-CONFIRMED that the pointers persist at +2w. The impact is CODE-INFERRED.
- Fix: repair hook sets `te_mon_arr_scan = 1` on every country whose pointer is dead, so discovery runs next
  pulse.

### F14. UN missions and records that name the loser (H3). LOW
- `un_mission_monthly` (`un_mission_effects.txt:607-650`) closes a mission as "lapsed" when the host object is
  gone or no longer owns the state. A UN peacekeeping mission sent INTO the German civil war therefore lapses
  when the rebels win, instead of succeeding. Resolution records (`un_res_proposer` / `_target` /
  `_mandate_beneficiary` / `_vetoer`) naming the loser are history only. All reads use `?=`.
- Evidence: SAVE-CONFIRMED for the persisting references; the outcome is CODE-INFERRED.
- Fix: optional. Treat a same-tag host as unchanged in the lapse test.

### F15. Other country variable LISTS that are silently not inherited (E4). LOW
- `nd_nonuse_pledges` / `nd_defied_us` (`nuclear_crisis_effects.txt:1585, 1805-1815`): the winner forgets
  pledges and defiance records. The counterparties still list the dead loser in their own lists, which
  become one-sided. `un_embargo_by` (`un_teeth_effects.txt:80, 212`) is on the sanctions target: a sanctioned
  loser's enforcer list is dropped. That's arguably fine, since the sanctions modifier is a country modifier
  and is lost too.
- Evidence: CODE-INFERRED (lists absent in these saves).

### F16. Regime continuity (H6): what a new regime inherits or loses wholesale. LOW, for design review
- Inherited verbatim from the old regime (LOYAL-ONLY variables): the nuclear posture and doctrine (`nd_*`),
  covert funding and tradecraft, cultural-hegemony funding level, UN standing and lean, one-time event flags
  (good: stops re-fires), banking cooldowns, and the civil-rights path months (then wiped by F4).
- Replaced by the rebel's own: every monetary choice (mandate, delegation, regime; F3).
- Lost: every toggled policy (F8).
- The mix isn't principled. Pick one rule per system: "a regime keeps the state's institutions" versus
  "a new regime chooses afresh".
- **Ruled 2026-09-26: the winner continues the nation.** It keeps the institutions and the player's
  choices. F1–F7 follow that rule; the open findings should too.

---------------------------------------------------------------------------------------------------

## Checked and judged SAFE (with reason)

- **Monetary modifier management** (`te_monetary_effects.txt:361-520`, step 9/9b): home-change strip and
  re-apply, plus re-add on a missing modifier. Verified at +2w. (The STOCKS problem is F3.)
- **Construction market**: hooks `on_revolution_start`/`on_secession_start`
  (`te_construction_market_on_actions.txt:241-290`). `te_cm_capacity_mult` was recomputed from 0.87 to 74.4
  by +2w.
- **Cultural hegemony**: `ch_monthly_country_update` (`cultural_hegemony_effects.txt:11-55`) recomputes every
  `ch_*` value statelessly from buildings and pops. `cultural_hegemony_foreign_benchmark` was re-applied by
  +2w. The funding modifiers are rebuilt from the variable. (Programmes: F8.)
- **Global warming**: the `global_warming` modifier and emission displays are re-derived each pulse; the JE's
  `immediate` is empty. (Policies: F8.)
- **Covert warfare, defensive side**: the `intelligence_capacity_defense` / `iw_domestic_defense` /
  `iw_tradecraft_bonus` JE modifiers were re-applied by +2w. `iw_funding_level` and `iw_tradecraft` are
  guarded scalars and survive. Foreign ops against the dead loser are `?=`-guarded and reaped.
- **UN dues, membership benefits, NPT, conventions** once membership is restored: single stateless refresh
  sites (`je_united_nations.txt:360-455`, `un_dues_country_monthly_update`). Back at +2w.
- **Space race cost/funding modifiers**: stripped and re-applied from `sr_active_<m>`
  (`space_race_effects.txt:533-554`).
- **Strategic reserve init**: every variable is guarded (`st_res_effects.txt:40-104`), so the E3 re-run of
  `immediate` is harmless. (Stock loss: F11.)
- **je_colonial_empire, je_space_race_\***: re-entry is blocked by inherited completion
  variables (`colonial_empire_completed`, `sr_completed_<m>`). **Correction (#463's sweep):**
  `je_world_war` removes `ww_fully_resolved` in `on_complete` / `on_fail`, so it does *not* block
  re-entry on a winner, and a failed `je_digital_rights` re-arms and fails again at once. Both are open. je_heir_education is
  blocked by the heir's own variable. je_digital_rights and je_post_scarcity are blocked by their target
  law.
- **Nuclear** (beyond the brief's four known items): `je_nuclear_program.txt:106-160` correctly zeroes the
  posture trackers on a fresh entry, and the doctrine/upkeep modifiers came back by +2w. The readiness reset
  (2 -> 1, `nd_readiness_months` 17 -> 0) comes from `nd_init_posture` on the fresh entry, so it's the known
  item. Only the lists (F15) are new.
- **Global variables**: the only mod globals naming GER were `nuke_rank_*` (recomputed to the winner by +2w).
  `un_hq_country` is guarded with `exists` (but see F2 for the host case).
- **H5, uninitialised rebels**: game-start-only initialisation exists only for monetary and construction
  market, and both hook `on_revolution_start`. Every other country-wide pulse (GW displays, UN power share
  and dossier, trade partners, CH) initialises lazily; the rebel carried all of them during the war. The
  exception is F1 (agdiff).
- **One-time event flags**: event-id flags (`lobby_events.11`, `exiles_events.3`, ...) are variables and
  inherited, so events don't re-fire.

## Doc corrections (done in the PR that added this report)
The "the JE and its modifiers move, variables don't" claim is corrected at:
- `docs/guides/scripting_best_practices.md` (the banking worked case, plus the new section);
- `docs/systems/monetary_policy_design.md` (items 12 and 32);
- `common/scripted_effects/banking_cycle_effects.txt`, `civil_rights_effects.txt` and
  `te_monetary_effects.txt`;
- `common/journal_entries/je_nuclear_program.txt`.

`docs/systems/mod_systems.md:411` and `common/script_values/te_monetary_script_values.txt:24` were left
as they are. They say only that `je_banking.txt`'s `immediate` resets unguarded on an inheritable entry,
which E3 confirms.
