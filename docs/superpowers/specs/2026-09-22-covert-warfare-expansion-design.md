# Covert Warfare expansion — design menu and build order

## Context

The covert warfare system (`je_covert_warfare`, nine pact-based operations, funding ladder,
single monthly detection roll) has no state that outlives an operation, treats every caught
operation as equally hostile (+2/+1 infamy, −15/−30 relations, regardless of type or phase),
and gives the player only one agency-level lever (funding). The user wants: persistent
per-target networks, graduated blowback on exposure, per-operation resource allocation with
diminishing returns, an agency experience score with unlocks, new operation types, and
(later) intelligence the network reveals. Decisions taken in the design conversation:

- "Passive gathering" = **per-target network presence first**; information reveal is a
  later tier the network unlocks.
- Whole menu designed now, **built in slices as separate PRs**.
- Exposure severity = **type tier × phase**, with third-party notification on the severe tier.
- **No doctrine/posture choice**; the agency-level progression is the experience score.
- Experience feeds **efficiency-class bonuses + unlocks** (per-type cap, the new severe ops).
- New operation types: **regime change**, **nuclear programme sabotage**, **space programme
  espionage** (media/cultural influence declined), and (added 2026-09-23) **cultivate
  assets**, a network-only operation.

Findings from exploration that shape the design:

- Detection today is one country-level roll per month that burns a *random* operation;
  `docs/systems/mod_systems.md` lists this as a known mis-weighting to fix only as a deliberate
  balance change. Per-op networks and per-op priority both require the roll to move
  per-operation, so this expansion makes that change (slice 1).
- `covert_ops_detected_infamy = 5` in `covert_warfare_script_values.txt` is declared and never
  referenced; the event uses literals. `covert_influence_campaign_action` is the only covert
  action without `is_hostile = yes`.
- Covert efficiency saturates: `covert_operation_detection_chance` multiplies by
  `max(0.2, 1 − efficiency_mult)`, and techs alone grant +1.35 by era 12 (~+0.65 by
  `cyber_warfare`). More efficiency is inert late-game, so experience must feed other levers.
- Registered but never granted: `country_intelligence_capacity_mult`,
  `country_covert_defense_military_add`. `law_secret_police` carries no covert modifier.
- House idiom for an accumulating score with diminishing gains and unscaled losses:
  `un_standing_gain` / `un_standing_loss` (`common/script_values/un_standing_values.txt`,
  `common/scripted_effects/un_standing_effects.txt`), tiers at 20/40/60/80.
- Operation state already lives in script containers (`iw_op` + `iw_op_<TYPE>`, `iw_ops` list);
  the burn path already carries a per-type code 0–8 into `iw_last_exposed_type`.
- `intelligence_sharing_defense_shield` recovers "base" defense by subtracting its own prior
  contribution; any new *dynamically refreshed* `country_covert_defense_*` source needs the same
  prior-subtraction or double-counts yearly.

## Slices and build order

| # | Slice | PR size | Depends on |
|---|---|---|---|
| 1 | Per-operation detection roll | small | — |
| 2 | Graduated exposure (tier × phase, third-party notice) | small | 1 |
| 3 | Per-operation priority (diminishing returns) — built on branch covert-per-op-priority | medium | 1 |
| 4 | Persistent per-target networks — built on branch covert-per-target-networks | medium | 1, 3 |
| 5 | Agency experience ("Tradecraft") + unlocks | medium | 2, 3, 4 |
| 6 | Four new operation types | medium-large | 2, 4, 5 |
| 7 | Network-revealed intelligence in the widget | small-medium | 4 |

Each slice: its own branch off `main`, `POST /reload?mod_only=true&audits_only=true` clean
(all 18 audits), `docs/systems/mod_systems.md` § Covert Warfare updated in the same PR,
loc added to `localization/english/te_miscellaneous_l_english.yml` (where the covert keys
live today; `organize_loc` files them — add a `startswith` rule if a new prefix has 4+ tokens).
Slices that touch the widget (3, 4, 5, 7) also update
`docs/systems/journal_entry_systems.md` § Covert Warfare — **that file is CRLF**: edit with
`Edit`/`sed` only, and confirm with `grep -c $'\r$'` afterwards.

**On approval**: (1) commit this document as the spec at
`docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md`; (2) branch
`covert-per-op-roll` off `main`; (3) invoke `writing-plans` for slice 1 only — each later slice
gets its own plan once the previous one has merged and the harness checks have run.

## Slice 1 — Per-operation detection roll

Today's roll is `random_list { 1 = { modifier add = c } 99 }`, which is P = (1+c)/(100+c), not
c% (10% at c=10, 24% at c=30, 34% at the 50 cap), and it burns a *random* pact.

- New effect `covert_ops_roll_detection_all` (country scope, last in the pulse, gated on funding
  ≥ 1 and `has_variable_list = iw_ops`): `every_in_list iw_ops` → `random = { chance =
  covert_op_roll_chance add_to_temporary_list = iw_detected_ops }`; then `random_in_list = {
  list = iw_detected_ops save_scope_as = iw_burned_op }`; `if exists → trigger_event
  covert_warfare.1`. **At most one burn per month, chosen at random among successes** (order-free,
  P(any) = 1 − Π(1 − cᵢ)). `random = { chance = <sv> }` is proven in
  `space_race_effects.txt:33`; the displayed `iw_detect` becomes the honest per-op figure and is
  already refreshed at the top of the same pulse by `covert_ops_sync_all`.
- `covert_op_roll_chance = { value = var:iw_detect multiply = covert_ops_detection_multi_op_scale
  min = 0 max = 100 }` (container scope). `covert_ops_detection_multi_op_scale = 1` in Section 1
  is the knob if N-op detection lands too hot (0.6 puts 3 ops near today's 18%).
- `covert_op_sync` gains a `CODE` param and writes `iw_type_code` (0–8, same codes as
  `covert_last_exposed_type_name`) on every op; backfills old saves monthly.
- `covert_warfare.1`: `trigger` = `exists = scope:iw_burned_op`; `immediate` saves the target
  as `detected_by_country` and copies `iw_type_code` to a ROOT var `iw_burned_type_code` via
  `scope:iw_burned_op = { ROOT = { set_variable … PREV.var:iw_type_code } }` (event loc can't
  reach containers, best-practices rule 10); `after` branches on that var into the existing nine
  `covert_op_burn` lines. Do not read the container in `after` (event lasts 3 days; stand-down may
  destroy it). Delete `random_scope_diplomatic_pact` and the "restore target_max_ic" block in
  the JE pulse (dead once the country roll goes).
- Debug harness `te_debug_covert.2` gets an option that sets one op's `iw_detect = 100` and
  calls the roll effect; expect `covert_warfare.1` naming that target.

Balance (c = 10% each, quantify in the PR): 1 op 10%→10%; 2 ops 10%→19%; 3 ops 10%→27%;
5 ops 10%→41% per month. Slice 4's network term and funding pull the per-op figure back down.

## Slice 2 — Graduated exposure

**Tier per type** is a pure function of the type code, so it is one script value
`covert_type_tier` branching on a code (no stored `iw_tier`, no extra parameter to backfill);
a new type is one branch there:

| Tier | Types | Fiction |
|---|---|---|
| 1 mild | industrial_espionage, military_espionage, space_program_espionage (new), cultivate_assets (new) | "everyone spies" |
| 2 moderate | election_interference, financial_subversion, influence_campaign | meddling |
| 3 severe | ideological_subversion, destabilization, regime_change (new), nuclear_sabotage (new) | attacking the state |
| war | infrastructure_sabotage, comms_disruption | already at war: infamy only, no relations/third-party effect |

**Phase factor**: preparatory ×0.5, establishing ×1.0, fully operational ×1.5.

**Blowback table.** The options fire on the player's click, days after `immediate`, and the
container may be gone by then (same hazard slice 1 avoids in `after`), and event loc cannot
reach a container anyway. So `immediate` copies `iw_burned_type_code` **and** `iw_burned_phase`
onto ROOT, and the script values `covert_exposure_infamy` / `covert_exposure_relations` read
only those ROOT vars (tier via `covert_type_tier`). Every base lives in Section 1 of
`covert_warfare_script_values.txt`, replacing the literals in `covert_warfare.1`;
`covert_ops_detected_infamy` is retired.

| Tier | base infamy | base relations | third parties |
|---|---|---|---|
| mild | 1 | −10 | none |
| moderate | 2 | −20 | none |
| severe | 4 | −40 | target's treaty allies and power-bloc members: −10 relations with operator, `post_notification` |
| war | 1 | 0 | none |

Anchored to today (+2 infamy, −15/−30 relations on every burn): moderate × establishing ≈
today; mild-preparatory drops to 0.5 infamy; severe-fully-operational is 6 infamy, 3× today,
which is the intended spread. Infamy `max = 25` per the `te_force_become_subject` guardrail.
Existing option structure stays: **Acknowledge** = full infamy, relations ×0.5; **Deny** =
infamy ×0.5, full relations hit, target gets `covert_op_heightened_vigilance_modifier`.
`covert_influence_campaign_action` gets `is_hostile = yes` (it is tier 2).

Defender side (`covert_warfare.2`): unchanged options, but `desc` names the tier via the
existing `iw_last_exposed_type` custom loc. **Third parties get no event**: inside the
severe-tier branch of both options, `every_country = { limit = { NOT this = ROOT;
is_in_same_power_bloc = scope:detected_by_country OR has_treaty_alliance_with = { TARGET =
scope:detected_by_country } } change_relations = { country = ROOT value = … } }` wrapped in a
`custom_tooltip` so the option previews it, plus `post_notification` on each — the
decolonization-events precedent (`decolonization_events.txt:1786`). Both audience triggers
have mod precedent in `un_vote_events.txt`.

`change_relations = { country = X value = <script_value> }` is already used by the mod
(`un_vote_effects.txt:527`), and `change_infamy = { value = { … } }` blocks are vanilla idiom,
so both blowback numbers can be script values.

## Slice 3 — Per-operation priority

Implementation plan: docs/superpowers/plans/2026-09-22-covert-per-op-priority.md. Election-interference confidence is not priority-scaled (see the plan).

- `iw_priority` 1–3 on the op (missing ⇒ 1; `covert_op_sync` backfills).
- Constants: `covert_op_priority_max 3`, effect ×1.35 / ×1.6, cost ×1.6 / ×2.4 (cost outruns
  effect = diminishing returns), `covert_op_priority_detect_add 2` per level above 1,
  `covert_op_phase_full_mult 2` (replaces the hard-coded `multiplier = 2`).
- **Application**: `add_modifier { multiplier = … }` resolves against ROOT and re-evaluates per
  tick, so a container-scope SV cannot be the multiplier. Helper
  `covert_op_add_scaled_modifier { MODIFIER MONTHS }` branches phase × priority into six
  **constant** SVs `covert_op_mult_p{2,3}_pri{1,2,3}`; replace every apply site
  (`covert_op_apply_target_effect`, `covert_op_apply_self_effect`, infra state, destab
  separatist/general, military espionage). Self-side "best phase" becomes `ordered_in_list …
  order_by = covert_op_effect_mult position = 0` (container-SV `order_by` proven by
  `te_history_sample_order`).
- **Cost**: country var `iw_priority_cost_sum` = Σ per-op cost weight, recomputed by
  `covert_refresh_priority_cost` on every priority change and in the pulse;
  `covert_operation_cost_mult` and both `cost_at_next_*` read it instead of
  `covert_operations_active`.
- **Detection**: stage `iw_priority_staging` in `covert_op_refresh_detection`; chance adds
  `(priority − 1) × covert_op_priority_detect_add`.
- **Stepper**: `covert_priority_up_sgui` / `_down_sgui`, `scope = country`, `saved_scopes = {
  iw_op }`, row passes `AddScope('iw_op', ScriptContainer.MakeScope)`; `is_valid` fail-closed
  (`exists = scope:iw_op`, `has_tag = iw_op`, bounds). Effect `covert_effect_priority_step {
  DELTA }` = change/clamp, refresh cost, `covert_refresh_funding_state` (re-stages detection),
  `covert_ops_apply_all_phase_effects`. Row markup mirrors `covert_cc_funding_stepper`.
  Priority 3 requires Tradecraft ≥ Established once slice 5 lands. Fallback if the container does
  not arrive through `AddScope`: per-type handlers via `iw_target_capital` (stand-down shape).
- **AI**: one `is_player = no` block in the pulse next to funding: in default/bankrupt → 1;
  great power and `has_war_with = var:iw_target` → 3; rivalry with target → 2; else 1; then
  `covert_refresh_priority_cost`. The AI branch steps through the same
  `covert_possible_priority_up` trigger the stepper uses, so the Tradecraft gate on priority 3
  binds the AI too (shared mechanics, no `is_ai` fork).

Open engine checks (harness first, fail-closed either way): container through `AddScope` into
sgui `saved_scopes`; `random_in_list = { list = <temporary> }`. `ordered_*` sorts descending
(documented in `scripting_best_practices.md`), so `position = 0` on the raw effect multiplier
is the best op — no negation.

## Slice 4 — Persistent per-target networks

**Container** tagged `iw_net`, parent operator, listed in `iw_nets`; vars `iw_target`,
`iw_target_capital` (display chain as ops), `iw_net_strength` 0–100, `iw_net_ops` (display),
`iw_net_trend` (1 growing / 2 decaying / 0 dormant, display).

**Effects** (new section of `covert_warfare_effects.txt`):
- `covert_net_create { TARGET }`, `covert_net_gain { AMOUNT }` (× `covert_net_gain_scale`,
  UN idiom), `covert_net_loss { AMOUNT }` (unscaled), both clamped 0–100.
- `covert_nets_sync` (pulse position: right after `covert_ops_sync_all`): (1) ensure a net exists
  for every op target — hop through a saved country scope, never `scope:<container>.var:` chains;
  (2) tick: count ops against the target with `any_in_list count >= N` for N = 1..3 into
  `iw_net_ops`, gain if ≥ 1 else decay; (3) reap nets whose target no longer exists or whose
  strength hit 0 with no ops (temporary list → `remove_list_variable` → `destroy_container`).
- `covert_op_create`: look up the net (`random_in_list iw_nets limit target`) and store
  `iw_net_head_start = covert_net_head_start_value` on the op, fixed at creation.
- `covert_op_refresh_detection`: also stage `iw_net_strength_staging` on the operator (0 if none).
- `covert_op_burn`: `covert_net_loss { AMOUNT = covert_net_burn_loss }` on that target's net.

**Consumers**: `covert_op_effective_duration = iw_duration + iw_net_head_start` (container SV);
`covert_op_is_established` / `_fully_operational` compare it against 6 / 12 (thresholds stay in
exactly those two triggers), and `covert_op_refresh_phase` subtracts the same SV.
`covert_operation_detection_chance` subtracts `iw_net_strength_staging × covert_net_detect_factor`
after the funding terms (floor `min = 1` stays).

**No "maintain presence" pact** (revisited 2026-09-23: slice 6 adds one, *D. Cultivate assets*). A tenth pact would show in the outliner naming the target and
drags the net into pact reconciliation. Instead decay halves at funding ≥ 3 — funding is
already the paid lever and the AI already manages it. Read the operator's funding by staging
it on the net during the tick (don't rely on `parent` from container scope in a script value).

**Constants** (Section 1): `covert_net_max 100`, `covert_net_dr_divisor 50`,
`covert_net_dr_floor 0.1`, `covert_net_gain_base 2`, `covert_net_extra_op_factor 0.5`
(2 ops ×1.5, 3 ops ×2, cap 3), `covert_net_decay_base 1.5`,
`covert_net_maintain_funding_level 3`, `covert_net_maintain_decay_mult 0.5`,
`covert_net_burn_loss 25`, `covert_net_detect_factor 0.05` (−5 pts at 100),
`covert_net_head_start_per_point 0.05`, `covert_net_head_start_max 5` (a full network puts a
new op one month from Establishing; phase 1 is never skipped).

Projection (months to reach strength; linear below 50, diminishing above):

| Strength | 1 op | 2 ops | 3 ops |
|---|---|---|---|
| 25 | 12.5 | 8.3 | 6.3 |
| 50 | 25 | 16.7 | 12.5 |
| 75 | 42 | 28 | 21 |
| 90 | 65 | 44 | 33 |

Decay from 50 with no ops: 33 months (67 at funding ≥ 3). A burn (−25) costs ~12 months of
single-op rebuilding.

**Widget**: third widget `widget_je_covert_networks` on `custom_widget_container_3`,
`datamodel = GetList('iw_nets')`, rows = target name, strength, trend. Loc `je_iw_net_*`.

**As built (plan `docs/superpowers/plans/2026-09-22-covert-per-target-networks.md`).**
Departures from the text above: the monthly pass is called from the JE pulse right after
`covert_ops_sync_all`, not inside it (that effect also runs on every funding / priority click),
so detection reads last month's strength; operations per network are counted by accumulation
rather than `any_in_list count >= N` (no vanilla precedent); the funding-halved decay branches
on the operator in the effect instead of staging funding onto the network; the head start is
rounded to whole months; the detection floor is `covert_ops_detection_floor` (0.1, from slice 2),
not `min = 1`; the network is also created at operation creation, after the head-start lookup;
`iw_net_trend` 0 means "holding at full strength"; the loc lives in
`te_journal_entries_l_english.yml` beside the other `je_iw_*` keys.

## Slice 5 — Agency experience ("Tradecraft")

Country variable `iw_tradecraft` 0–100, seeded 0. Shape copied from `un_standing`:

- **Gain**: monthly, per operation at establishing phase or better, `covert_tradecraft_gain_per_op`
  (default 1.0), counting at most `covert_tradecraft_ops_counted` (4) operations, scaled by
  `(100 − x) / 50` clamped [0.1, 1].
- **Loss**: on each burn, unscaled, by tier: mild 3, moderate 6, severe 9, war 3.
- **Decay**: `covert_tradecraft_decay` (0.25/month) while no operation is running.
- Effects `covert_tradecraft_gain` / `covert_tradecraft_loss` with `REASON` codes and a
  `iw_tradecraft_last_reason` for the tooltip, mirroring `un_standing_gain`.

Net of the burn drain (expected loss per op-month = detection × loss; at most one burn a
month): at 10% per-op detection a moderate op nets +0.4/month, a severe one +0.1, a mild one
+0.7; at 5% detection +0.7 / +0.55 / +0.85. (The first draft had gain 0.5 and losses 5/10/15,
which nets to zero or below at 10% detection — Established would never have been reached.)

Because gains diminish and losses do not, the score settles where
`N × 1.0 × (100 − x)/50 = p × L`: two moderate ops at 10% detection equilibrate near 85, one
near 70. Veteran (80) therefore needs a larger agency or lower detection; Seasoned (60) is
reachable with a single long-running op.

Projection, moderate ops at 10% detection (net +0.4/op-month below 50):

| ops running | months to 25 | to 50 | to 60 |
|---|---|---|---|
| 1 | 63 | 125 | ~165 |
| 2 | 31 | 63 | ~85 |
| 4 | 16 | 31 | ~45 |

Tiers 20/40/60/80 (Fledgling / Established / Seasoned / Veteran / Storied), exposed as
scripted triggers `covert_tradecraft_tier_N`, applied through one static modifier
`iw_tradecraft_bonus` refreshed monthly with `multiplier = tier`:

- `country_intelligence_capacity_mult` +0.05 per tier (the unused registered type).
- Network growth ×(1 + 0.15 per tier) (slice 4 consumer).
- **Unlocks**: Established (40) → priority 3 available (slice 3); Seasoned (60) → the two new
  severe operations (regime change, nuclear sabotage) become `possible`; Veteran (80) → +1
  per-type cap (`covert_ops_max_per_type`). Existing operations are never gated, so old saves
  lose nothing. Exposed as scripted triggers so each gate is one `custom_tooltip` line.
- Tradecraft only accrues while the JE is active (its pulse is the only clock), the same
  limitation the existing detection roll has when the JE deactivates — documented, not fixed.

Widget: one row in `widget_je_covert_command_centre` (score, tier name, last reason tooltip),
same pattern as the funding ladder rows.

**As built (plan `docs/superpowers/plans/2026-09-22-covert-tradecraft.md`).**
Departures from the text above: the tier bands are Untested (0–19) / Fledgling (20–39) /
Established (40–59) / Seasoned (60–79) / Veteran (80+) — "Storied" was dropped, because the
unlock lines bind Established = 40, Seasoned = 60, Veteran = 80 and the name list did not
fit them; the tier triggers are `covert_tradecraft_tier_1`..`_4` plus three named unlock
triggers (`covert_tradecraft_unlocks_priority_3` / `_severe_ops` / `_extra_per_type`);
reason codes are 1 (operations maturing) and 20–23 (burn by tier) / 24 (idle decay); the
burn loss runs in `covert_warfare.1`'s `after`, before the type code is cleaned up;
networks grow at last month's tier (they tick earlier in the pulse); the Seasoned unlock is
a trigger only until slice 6 consumes it; funding level 2, formerly named "Tradecraft", is
renamed "Professional" so the word means only this score. **The equilibrium and
projection above were wrong at 10% detection**: they assume every operation-month earns,
but detection rolls from month 0 and a burned operation is relaunched preparatory; as first
built, one moderate op at 10% averaged ~31. At the user's call (2026-09-23) a preparatory
operation now earns half (`covert_tradecraft_prep_gain_fraction = 0.5`). Simulated long-run
averages at 10% (network head start 0 / 5): one moderate op 57 / 69, two 62 / 72, one
severe 25 / 44; at 5% one moderate op 82 / 85. Table: `covert_warfare_script_values.txt`
§ TRADECRAFT.

## Slice 6 — Four new operation types

**Per-type enumeration sites** (each new type = one row/branch in each; make the tier table
one-row-per-type first; verified against the code on 2026-09-22 during slice 2): the diplomatic
action in `covert_operations.txt`; `covert_ops_sync_all` (TYPE / ACTION / DEFENSE_MOD / CODE
row); one of the four `covert_code_tier_mild` / `_moderate` / `_severe` / `_war` triggers — the
actual shipped form; no single `covert_type_tier` branch exists in the codebase, despite this
list once naming one; `is_covert_operation_pact` OR list (`covert_warfare_triggers.txt`); the
`covert_warfare.1` `after` code branch; the `covert_warfare.2` trigger OR list;
`covert_last_exposed_type_name` and its sibling `covert_burned_type_name` — two separate
blocks, not one — code (9, 10, 11, 12) in `covert_warfare_custom_loc.txt`; a stand-down sgui
handler; the block in `covert_ops_apply_all_phase_effects`; static modifiers; loc (`iw_*_tt`,
action name/desc); and the operations widget's own per-type row and stand-down-button blocks
in `gui/journal_entry_widgets/covert_operations_widget.gui`, gated on
`ScriptContainer.HasTag('iw_op_<type>')`. A structural test that pins every one of these lists
against the operation-code set is a plausible candidate pre-task for this slice (rough
estimate: comparable to slice 2's brace-matching test work, roughly half a day to a day) — a
recommendation for the repository owner to weigh, not a decision made here.

**A. Regime change** (`covert_regime_change_action`, code 9, tier severe, defense
ideological). Fiction: bankroll the colonels.
- `possible`: rivalry with target (like destabilization), target not ROOT's subject, tradecraft
  ≥ Seasoned. `requirement_to_maintain`: rivalry persists.
- Target modifier `covert_regime_change` (phase/priority helper): `country_coup_resistance_add
  = -1` (vanilla `country_coup_resistance` = legitimacy/10 + 1 + add, so −1/−2 is a third to a
  half of a mid-legitimacy government's resistance), `country_legitimacy_base_add = -5`,
  `political_movement_radicalism_add = 0.05`.
- Fully operational and the target has `je_ip4_coup` running: monthly
  `je:je_ip4_coup ?= { add_progress = { value = covert_regime_change_coup_push name =
  je_ip4_coup_progress_bar } }` (vanilla coup events nudge by ±15; use 5). Guard the whole
  coup branch with `has_dlc_feature = ep2_content`; without the DLC the op is pressure-only.
- AI `will_propose`: rivalry + (antagonistic or domineering) + `ruler_is_aggressive` weighted;
  `evaluation_chance` 0.02 like destabilization.

**B. Nuclear programme sabotage** (`covert_nuclear_sabotage_action`, code 10, tier severe,
defense military). Fiction: Stuxnet.
- New scripted trigger `nuclear_program_is_proliferating` in `nuke_triggers.txt` = the inline
  idiom from `nuclear_weapon_events.18` (`has_variable = nuclear_weapon_program_progress` +
  `has_variable = nuclear_weapons_program_funding` + funding ≥ 1); `possible` and
  `requirement_to_maintain` use it, plus tradecraft ≥ Seasoned. A nuclear power's stockpile
  programme also qualifies (its progress runs ×10, so a mult debuff scales where the event's
  flat −10 did not).
- Target modifier `covert_nuclear_sabotage`: `country_nuclear_program_progress_mult = -0.25`
  (×2 fully operational = −0.5; `percent = no`, decimals 2 — check `modifier_visibility_audit`).
- AI `will_propose`: target proliferating, ROOT has `nuclear_power` or is a great power, rival or
  antagonistic; `propose_score` +10 if target progress ≥ 75 (`nuclear_program_nearing_completion`
  read from `je_nuclear_program.txt:233`).

**C. Space programme espionage** (`covert_space_espionage_action`, code 11, tier mild, defense
economic). Fiction: the other side's rocket plans.
- New scripted trigger `sr_target_ahead_of_root` in `space_race_triggers` (or
  `covert_warfare_triggers.txt`): OR over the 8 milestones of target `has_variable =
  sr_completed_<M>` and ROOT `NOT`. Milestone flags are public (world-first modifiers exist),
  so this is not the progress-omniscience the space docs forbid. `possible` /
  `requirement_to_maintain` use it (the tech-gap analogue of industrial espionage).
- Self modifier `covert_space_espionage`: `country_space_race_progress_mult = 0.10` (×2 = 0.20),
  `country_space_race_risk_mult = -0.10`. Target marker `covert_space_espionage_detected`
  (same shape as the two existing `_detected` markers, for `covert_warfare.2`).
- AI `will_propose`: target ahead, ROOT has `sr_active_milestone`; `propose_score` 10, +5 GP.

**D. Cultivate assets** (`covert_cultivate_assets_action`, code 12, tier mild, defense
ideological: the work is recruiting sympathisers, which the ideological counterintelligence
axis already covers). Fiction: dinners, favours and a slow list of names. Added 2026-09-23 at
the user's request; a network-only operation was rejected during slice 4 (see there), and this
revisits that call on purpose: the outliner line is accepted, since every other operation
shows there too.
- **No effect on the target at all**: no target modifier, no self modifier, no
  `covert_ops_apply_all_phase_effects` block. Its only product is the network.
- **No `_detected` marker either.** The two existing markers carry a small debuff
  (`country_authority_add = -3`), which would break "no effect". Instead the
  `covert_warfare.2` trigger gains an OR branch on `iw_last_exposed_type = 12`
  (`covert_op_burn` sets it on the target just before firing the event), so a burn is still
  announced to the defender.
- **Network gain ×1.5**: `covert_nets_sync` step 2 also marks each network that has a
  cultivate-assets operation against its target (`iw_net_cultivating` 0/1, zeroed with
  `iw_net_ops`); `covert_net_tick_gain` multiplies by `covert_net_cultivate_mult = 1.5` when
  the flag is set. That multiplier stacks with the normal extra-operation factor (it still
  counts as an operation in `iw_net_ops`) and with Tradecraft's growth multiplier. Decay,
  burn loss and head start are unchanged.
- **Tradecraft at the preparatory rate, always**: in `covert_tradecraft_monthly` it counts
  `covert_tradecraft_prep_gain_fraction` whatever its phase (a `has_tag =
  iw_op_cultivate_assets` branch ahead of the established check), so a cheap, near-riskless
  operation cannot be farmed for experience.
- **Exposure**: mild tier × phase like the espionage pair (0.5–1.5 infamy, −5 to −15
  relations, Tradecraft −3, network −25). It rolls detection like any operation.
- `possible`: the usual covert gates (funding ≥ 1, a free slot, per-type cap, valid target, no
  duplicate against the same target); no rivalry or war requirement. Not usable on ROOT's own
  subjects. `requirement_to_maintain`: funding ≥ 1 and the target still valid.
- **AI** `will_propose`: rivalry with the target, or antagonistic, and no network or one below
  50 against it; `propose_score` 5, +5 when ROOT already runs another operation there
  (feed the network the other operation benefits from); `evaluation_chance` 0.05.
- Constant in Section 1: `covert_net_cultivate_mult = 1.5`. Projection: alone against a
  target it reaches strength 50 in ~17 months (vs 25 for a normal operation) and 75 in ~28
  (vs 42).
- Slice 7 synergy: it is the natural way to reach the strength-50 / 75 intelligence reveals.

## Slice 7 — Network-revealed intelligence (later)

At network strength ≥ 50 the operation/network row shows the target's intelligence capacity
and tech count; at ≥ 75 it shows how many operations the target runs against **you**. Gated
behind a strong network so the "defender never sees undetected ops" rule is broken only by
having penetrated their service. Display-only; no new mechanics. Designed after slice 4 lands.

## Verification (all slices)

- `POST /reload?mod_only=true&audits_only=true` → `warnings` empty; check
  `docs/engine/loc_coverage_report.md`, `modifier_visibility_report.md`,
  `modifier_multiplier_var_report.md`.
- `ruff check .`, `python3 -m unittest discover -s . -p 'test_*.py'` (from main checkout only).
- In-game: `event te_debug_covert.1` / `.2` harness (`events/te_debug_covert_events.txt`);
  extend it per slice (force a burn, set network strength, set tradecraft) and read
  `debug.log` via the `log-triage` skill after a test session.
- Balance: state the per-month total detection probability before/after slice 1 in the PR.
