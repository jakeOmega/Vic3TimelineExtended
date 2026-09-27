# UN Vote Lobbying Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI members vote late (month 9, 10 or 11), their leans show as imperfect bands from the start, and any member can move an AI member's vote with an influence campaign (a one-sided pact) or an obligation-paid pledge, in either direction. The AI lobbies too.

**Architecture:** Everything hangs off the existing resolution container (`un_vote_effects.txt`). The global monthly UN pulse fires the hidden `un_vote.4` to every member; for an AI member it draws the per-resolution casting month and misreading once, takes the lean snapshot, casts only when its month has come, and refreshes its row in the chamber. Campaigns are two one-sided pacts, each mirrored by a script container that counts its months; the monthly tick reconciles containers with pacts and writes each member's net lobbying shift, which a new lean term reads. Pledges keep the "Seek a Vote Commitment" action, open it to any member, and add an "against" twin. The chamber gets a Delegations section of 24 row slots in the #453 per-row pattern.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.14), `.gui`, YAML localization, Python `unittest` structural tests, pandoc + Typst for the player guide.

**Spec:** `docs/superpowers/specs/2026-09-27-un-vote-lobbying-design.md`

## Global Constraints

- Casting month 9, 10 or 11, one in three each; misreading −10, 0 or +10, fixed once per resolution.
- Bands: firmly for ≥ +30; leaning for +10 to +29; undecided −9 to +9; leaning against −10 to −29; firmly against ≤ −30.
- Campaign: +3 lean per full month toward its direction, up to 15 per campaign; same-direction campaigns stack to at most 20; opposing campaigns net out.
- Campaign cost: one flat influence cost of 100 (the spec's fallback, since a script-value `cost` is unverifiable without the game: every vanilla pact cost is a literal).
- Pledge: ±100 lean; one pledge per member per resolution (first accepted wins); each country may collect up to two pledges per resolution; a pledge against never prevents a veto, and a pledged-for permanent member never vetoes.
- AI: proposer lobbies for, up to three campaigns at once, only with influence to spare; the resolution's target, its allies and its bloc leader lobby against; the AI never runs campaigns on human members.
- Chamber: up to 24 member rows; order: worked (campaign or pledge), undecided, leaning for, leaning against; firmly decided members summarised.
- "Decide later" on `un_vote.1`, re-fired at month 9 and again at month 11.
- The one-resolution lock, the 14-month lapse, topic cooldowns, the recess, Article 19, suspended representation, the supermajority count and the Charter Reform II override are unchanged.
- Game loc is British English ("favour"), the player guide American ("favor"), as today.

## Settled risks (the spec's "Risks to check before building")

1. **Pact `cost` as a script value:** not verifiable offline, and vanilla has no precedent. Use the flat 100.
2. **Create/end pacts from script:** `create_diplomatic_pact` (country scope, initiator) and `remove_diplomatic_pact` are documented and used by vanilla (`31_power_bloc_force_become_subject.txt`, `01_expel_diplomats.txt`). Script never trusts a hook alone: every create is followed by our own container start (idempotent), and the monthly tick reaps containers whose pact is gone and adopts pacts that have no container (covert-warfare's proven reconcile shape).
3. **Monthly per-AI event:** `un_vote.4` fans out only while a resolution is voting (≤ 12 months at a time); the old code already fired it to every AI member once.
4. **Ordered rows without sorting primitives:** `ordered_in_list` with a literal `position` is a sorting primitive (the mission contributor rows use it). Each AI member's snapshot writes a sort key; the resolution re-assigns `un_deleg_row_0..23` with 24 unrolled `ordered_in_list = { position = N }` calls, so display and buttons read the same slot. *(As built after review: the re-assignment runs once per fan-out, in a hidden `un_vote.7` sent to each human country the next day, not after every AI snapshot; a member that votes drops out of its row at once.)*

## Other decisions the spec leaves to the plan

- **Leans are visible from day 1.** `un_resolution_open` sends `un_vote.4` to every member at once (not only humans), so bands show from the first day a player can lobby. The spec said "from day 30"; the in-game check says "from month 1". Earlier is strictly more information and costs one extra fan-out.
- **The final tally casts in a "last call" event, not in `un_vote.2`.** Casting needs ROOT = the voter (the lean's `relations:root`, `un_vote_can_cast_ballot`, the pledge triggers), and `un_vote.2`'s ROOT is the proposer. A hidden `un_vote.6`, queued at 360 days beside `un_vote.2` (365), marks the resolution `un_res_last_call` and sends `un_vote.4` to every AI member, which then casts regardless of its month. The monthly pulse also sets the mark from month 12, for resolutions opened before this change.
- **Seek Pledge from the chamber** resolves against an AI member at once with `would_accept_diplomatic_action = { actor = ROOT type = … }`, i.e. the engine's own `accept_score`. A human recipient is reached only through the diplomacy panel (rows are AI members only).
- **Per-asker attempt limit:** "one ask per member per resolution, a refusal is an answer" becomes per (asker, recipient): the recipient keeps a list of askers for the resolution (`un_pledge_askers` + `un_pledge_askers_res`).
- **Revolutions (the spec asks the plan to settle this):** the casting month, misreading, pledge state (`un_pledge_to/dir/res`), per-asker pledge count and lobbying shift are country *variables*, so a civil war's winner inherits them and continues the nation's position. The asker list is a variable *list* and is lost, so the winner may be asked once more (harmless). Campaigns are pacts, so they end; their containers are parented to the lobbyist and culled with it, and the monthly reap destroys any whose pact is gone. The resolution's lists reference country objects exactly as `un_res_yes`/`un_res_no` already do, so nothing new is lost there. Every list iteration guards `exists = this`.

## Review Focus

1. A campaign whose member votes, or whose resolution closes, must stop costing influence the same month: the pact is removed in script at those two sites, not only by `requirement_to_maintain`. Test: `un_resolution_record_vote` calls `un_lobby_campaigns_end_on`, `un_resolution_archive` calls `un_lobby_campaigns_close`.
2. A permanent member pledged against, whose lean without the pledge is above its veto line, must not veto; one below it still vetoes. Test: `un_vote_ai_should_veto` reads `un_lean_veto_basis`, never `un_lean_total`, and the snapshot writes basis = total − pledge.
3. An AI member that joins mid-session, or a resolution open when an old save loads, still gets a vote. Test: `un_vote.4` calls `un_vote_ai_draws` before the snapshot, the draw raises the month to at least next month, and the monthly pulse sets `un_res_last_call` from month 12.
4. The row a player clicks must be the row they read. Test: every delegation row passes one op number to all 23 of its bindings, and every sgui switch maps op N to its helper with N.
5. A cancelled campaign must drop its shift before the member next votes, even mid-month (the last call can land mid-month). Test: the pact break hooks call `un_lobby_campaign_end`, which destroys the container and recomputes that member's shift.

---

## File map

| File | Change |
|---|---|
| `common/script_values/un_lobbying_values.txt` | **new**: tuning (steps, caps, bands, AI margins), `un_lean_lobbying`, sort key and helpers |
| `common/script_values/un_dossier_values.txt` | `un_lean_pledge` ±100; `un_vote_lean` adds `un_lean_lobbying` |
| `common/scripted_effects/un_dossier_effects.txt` | draws, snapshot extra vars, cast gate, lean refresh fan-out; remove `un_vote_dispatch_ai_ballots` |
| `common/scripted_triggers/un_dossier_triggers.txt` | veto rule reads `un_lean_veto_basis`; `un_vote_ai_cast_due` |
| `common/scripted_effects/un_vote_effects.txt` | open (fan-out, last call), record_vote (end campaigns, row list), archive (close campaigns), monthly update (tick, AI, refresh, deferred re-fire) |
| `events/un_vote_events.txt` | `un_vote.1` Decide later; `un_vote.4` split; `un_vote.5` snapshot-only; new `un_vote.6` last call |
| `common/diplomatic_actions/un_lobbying.txt` | pledge action opened to any member, `un_secure_commitment_against_action`, two campaign pacts |
| `common/scripted_effects/un_lobby_effects.txt` | pledge both ways, settlement both ways, campaign lifecycle, monthly tick, AI lobbying |
| `common/scripted_triggers/un_lobby_triggers.txt` | pledge and campaign gates |
| `common/scripted_effects/un_vote_cast_effects.txt` | keep/break tooltips per direction |
| `common/scripted_effects/un_chamber_display_effects.txt` | delegation rows, summary, firm list, pledge-against lines, reasons |
| `common/scripted_guis/un_chamber_sguis.txt` | row, summary, list, lobby for/against/stop, pledge for/against sguis |
| `gui/journal_entry_widgets/un_chamber_widget.gui` | Delegations section, 24 generated rows |
| `localization/english/*.yml` | new keys; stale "thirty days"/"sponsor" text fixed |
| `test_un_vote_lobbying.py` | **new**: structural tests |
| `docs/systems/journal_entry_systems.md` (CRLF) | lifecycle and lobbying sections |
| `docs/player_guide/09-united-nations.md` + PDF | when members vote, bands, campaigns, pledges, Decide later, AI |

---

### Task 1: Late, staggered AI ballots and Decide later

**Files:** `un_lobbying_values.txt` (new, timing part), `un_dossier_effects.txt`, `un_dossier_triggers.txt`, `un_vote_effects.txt`, `un_vote_events.txt`, loc, `test_un_vote_lobbying.py`.

**Interfaces — produces:**
- `un_vote_ai_draws = yes` (scope: AI member; needs `scope:un_resolution`) — writes `un_vote_draw_res`, `un_vote_cast_month`, `un_lean_misread` once per resolution.
- `un_vote_ai_cast_due = yes` (trigger, scope: AI member).
- `un_vote_refresh_leans = yes` (scope: any; needs `scope:un_resolution`) — `un_vote.4` to every member.
- Snapshot writes `un_lean_shown` (total + misread) and `un_lean_veto_basis` (total − pledge).
- Resolution vars/lists: `un_res_last_call`, `un_res_deferred`.

- [ ] **Step 1: failing tests** in `test_un_vote_lobbying.py` (`CastingTimingTest`): `un_vote_ai_draws` has a `random_list` setting `un_vote_cast_month` to 9, 10, 11 and one setting `un_lean_misread` to −10, 0, 10; `un_vote.4`'s immediate calls `un_vote_ai_draws`, then `un_lean_snapshot`, then `un_vote_ai_cast` only inside a limit holding `un_vote_ai_cast_due`; `un_vote_dispatch_ai_ballots` is defined nowhere; `un_resolution_open` queues `un_vote.6` with `days` < 365 and no `un_vote.5`; the monthly update sets `un_res_last_call` at `un_res_months >= 12`; `un_vote_ai_should_veto` reads `un_lean_veto_basis` and not `un_lean_total`; `un_vote.1` has an option whose name is `un_vote.1.later`, with `ai_chance = { base = 0 }` and no `un_vote_cast_` call; the monthly update re-fires `un_vote.1` over `un_res_deferred` at months 9 and 11.
- [ ] **Step 2:** run `python3 test_un_vote_lobbying.py` → FAIL.
- [ ] **Step 3: implement.**
  - `un_vote_ai_draws`:
    ```
    un_vote_ai_draws = {
    	if = {
    		limit = { NOT = { var:un_vote_draw_res ?= scope:un_resolution } }
    		set_variable = { name = un_vote_draw_res value = scope:un_resolution }
    		random_list = {
    			1 = { set_variable = { name = un_vote_cast_month value = 9 } }
    			1 = { set_variable = { name = un_vote_cast_month value = 10 } }
    			1 = { set_variable = { name = un_vote_cast_month value = 11 } }
    		}
    		random_list = {
    			1 = { set_variable = { name = un_lean_misread value = -10 } }
    			1 = { set_variable = { name = un_lean_misread value = 0 } }
    			1 = { set_variable = { name = un_lean_misread value = 10 } }
    		}
    		# Drawn after the session began (a late joiner, or a save loaded
    		# mid-vote): no earlier than next month.
    		if = {
    			limit = { var:un_vote_cast_month < un_res_next_month }
    			set_variable = { name = un_vote_cast_month value = un_res_next_month }
    		}
    	}
    }
    ```
  - `un_vote_ai_cast_due`: `OR = { scope:un_resolution ?= { has_variable = un_res_last_call }  AND = { has_variable = un_vote_cast_month  var:un_vote_cast_month <= un_res_months_now } }`.
  - `un_lean_snapshot` adds `un_lean_lobbying` (Task 3's value; 0 until then), `un_lean_shown` (= total + misread, misread 0 for humans) and `un_lean_veto_basis` (= total − pledge).
  - `un_vote_ai_should_veto`: replace `var:un_lean_total` with `var:un_lean_veto_basis` (and `has_variable` guard).
  - `un_vote.4` immediate: scopes as today; `if is_ai → un_vote_ai_draws`; `un_lean_snapshot`; `if is_ai + un_vote_can_cast_ballot + un_vote_ai_cast_due → un_vote_ai_cast`; `if is_ai → un_deleg_refresh_self` (Task 5 stub now: list upkeep only).
  - `un_vote.5`: drop the `un_res_ai_cast` clause; immediate calls `un_vote_refresh_leans`.
  - `un_vote.6` (new, hidden): trigger as `un_vote.5`'s; immediate sets `un_res_last_call` on the resolution and calls `un_vote_refresh_leans`.
  - `un_resolution_open`: `un_vote_refresh_leans` (all members) instead of the human-only refresh; `trigger_event = { id = un_vote.6 days = 360 }`; drop `un_vote.5`.
  - `un_resolutions_monthly_update`: in the voting branch, `if months >= 12 → un_res_last_call`; `un_vote_refresh_leans`; re-fire deferred at months 9 and 11:
    ```
    if = {
    	limit = {
    		has_variable_list = un_res_deferred
    		OR = { var:un_res_months = 9 var:un_res_months = 11 }
    	}
    	every_in_list = {
    		variable = un_res_deferred
    		limit = { exists = this is_ai = no }
    		trigger_event = { id = un_vote.1 }
    	}
    }
    ```
  - `un_vote.1` option D "Decide later": `trigger = { is_ai = no }`; two `custom_tooltip = { text = … }` branches (a reminder is still to come, or none is) wrapping `add_to_variable_list = { name = un_res_deferred target = ROOT }` on the resolution; `ai_chance = { base = 0 }`.
  - Delete `un_vote_dispatch_ai_ballots` and `un_vote_refresh_human_leans`.
  - Loc: `un_vote.1.later`, `un_vote_decide_later_tt`, `un_vote_decide_later_last_tt`.
- [ ] **Step 4:** tests PASS; `python3 empty_effect_audit.py --strict`, `silent_variable_audit.py --strict`, `je_immediate_reset_audit.py --strict`, `prev_scope_audit.py --strict`, `orphaned_event_audit.py --strict`, `event_image_audit.py --strict` green.
- [ ] **Step 5:** commit by path.

### Task 2: Pledges in both directions

**Files:** `un_lobbying.txt`, `un_lobby_effects.txt`, `un_lobby_triggers.txt`, `un_dossier_values.txt` (`un_lean_pledge`), `un_dossier_effects.txt` (reason tally), `un_vote_cast_effects.txt`, `un_chamber_display_effects.txt` (commitment lines), loc, tests.

**Interfaces — produces:**
- `un_lobby_accept_commitment = { LIST = yes|no DIR = 1|-1 }` (ROOT = asker, `scope:target_country` = recipient).
- `un_lobby_record_attempt = yes` (same scopes) — adds the asker to the recipient's `un_pledge_askers`.
- `un_lobby_holds_pending_commitment` (for, unchanged name) and `un_lobby_holds_pending_against` (triggers, voter = ROOT).
- `un_pledge_deal_available = { ASKER = … COUNTRY = … }` (resolution scope).
- Recipient vars: `un_pledge_to`, `un_pledge_dir`, `un_pledge_res`. Asker vars: `un_pledge_count`, `un_pledge_count_res`. Resolution list: `un_res_committed_no`.

- [ ] **Step 1: failing tests** (`PledgeTest`): two actions `un_secure_commitment_action` and `un_secure_commitment_against_action`; neither's `selectable` reads `un_res_proposer`; the against action's accept_score has `UN_LOBBY_ACCEPT_TARGET_ALLY` at +60, `…_BLOC` +30, `…_RIVAL` −25 (the for action keeps −60/−30/+25); `un_lean_pledge` adds 100 under `un_lobby_holds_pending_commitment` and −100 under `un_lobby_holds_pending_against`; `un_lobby_settle_commitment` handles both `un_res_committed_yes` and `un_res_committed_no`; `un_lobby_pledge_cap = 2` is read per asker.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: implement.**
  - Action `selectable`: rule, active resolution voting, member, representation not suspended (the proposer test goes).
  - `possible` clauses (each a `custom_tooltip`): not the target; has not voted; `un_pledge_not_asked_tt` (asker not in recipient's `un_pledge_askers` for this resolution); `un_pledge_not_pledged_tt` (recipient on none of `un_res_committed_yes/no`, `un_res_commit_kept/broken`); `un_pledge_under_cap_tt` (asker's count for this resolution < `un_lobby_pledge_cap`); no obligation owed.
  - AI `evaluation_chance`: for — 0.02 if ROOT is the proposer, +0.03 on a mandate or a binding resolution aimed at its rival; against — 0.02 if ROOT is the target, its ally or its bloc leader on an accusing topic, +0.03 if ROOT is the target. `will_propose` adds "close to the line": the recipient's snapshot is for this resolution and its lean is in [−25, +9] (for) or [−9, +25] (against).
  - `un_lobby_accept_commitment`: re-check `un_pledge_deal_available`; add to `un_res_committed_$LIST$`; bump `un_res_commit_count` / `un_res_commit_pending`; write recipient vars; bump asker count; `set_owes_obligation_to`.
  - `un_lobby_settle_commitment`: `if` on the yes list → settle with kept list `un_res_yes`; `else_if` on the no list → settle with `un_res_no` (a veto is a no, so kept). The other party is the recipient's `un_pledge_to` when `un_pledge_res` is this resolution, else `un_res_proposer` (pledges from before this change).
  - Cast tooltips: `un_vote_cast_yes` shows KEEP for a pending for-pledge, BREAK for a pending against; `un_vote_cast_no` / `un_vote_cast_veto` the reverse.
  - Reasons: `un_res_why_no_pledge` when the pledge term is ≤ −10.
  - Chamber commitment lines: `je_un_chamber_commitment_pending_no`.
  - Loc: new action family (from `loc_coverage_audit`), clause tooltips, `UN_VOTE_COMMITMENT_*` reworded to "the country we pledged it to".
- [ ] **Step 4:** tests + audits green; `loc_coverage_audit` clean for the new keys.
- [ ] **Step 5:** commit.

### Task 3: Lobbying campaigns (pacts, containers, lean term)

**Files:** `un_lobbying.txt`, `un_lobby_effects.txt`, `un_lobby_triggers.txt`, `un_lobbying_values.txt`, `un_dossier_values.txt`, `un_dossier_effects.txt` (reason tally), `un_vote_effects.txt` (record_vote, archive, monthly), loc, tests.

**Interfaces — produces:**
- Pact types `un_lobby_for_action`, `un_lobby_against_action`.
- Container tags `un_lobby_campaign` + `un_lc_for|un_lc_against`; vars `un_lc_lobbyist`, `un_lc_member`, `un_lc_months`, `un_lc_shift`, `un_lc_armed`; resolution list `un_res_campaigns`.
- `un_lobby_campaign_start = { DIR = for|against }` (ROOT/this = lobbyist, `scope:target_country` = member) — idempotent.
- `un_lobby_campaign_end = { DIR = … }` (break hooks; same scopes).
- `un_lobby_campaigns_end_on = { MEMBER = … }`, `un_lobby_campaigns_close = yes`, `un_lobby_campaigns_monthly = yes` (resolution scope).
- Member vars `un_lobby_for_shift`, `un_lobby_against_shift`, `un_lobby_campaigns_on`, `un_lobby_shift_res`; value `un_lean_lobbying`.
- Triggers `un_lobby_campaign_live_ok` (pact maintain; ROOT lobbyist, `scope:target_country` member), `un_lobby_member_lobbyable = yes` (member scope, resolution from `global_var`).

- [ ] **Step 1: failing tests** (`CampaignTest`): both pacts have `cost = 100`, `is_two_sided_pact = no`, a `requirement_to_maintain` using `un_lobby_campaign_live_ok`, `manual_break_effect` and `auto_break_effect` calling `un_lobby_campaign_end` with their own DIR, `ai.evaluation_chance` value 0, `will_break = { always = no }`; potential requires the target `is_ai = yes`; `un_lobby_campaign_step = 3`, `_cap = 15`, `_stack_cap = 20`; `un_vote_lean` adds `un_lean_lobbying`; the snapshot writes it; `un_resolution_record_vote` calls `un_lobby_campaigns_end_on`; `un_resolution_archive` calls `un_lobby_campaigns_close`; the monthly update calls `un_lobby_campaigns_monthly` before `un_vote_refresh_leans`; the reap tests liveness with `first_country = prev` + `second_country = scope:…` (never bare `has_diplomatic_pact`).
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: implement.** Key shapes:
  - Liveness (effect context, per container):
    ```
    var:un_lc_member = { save_temporary_scope_as = un_lc_m }
    if = {
    	limit = {
    		has_tag = un_lc_for
    		var:un_lc_lobbyist ?= {
    			NOT = {
    				any_scope_diplomatic_pact = {
    					is_diplomatic_action_type = un_lobby_for_action
    					first_country = prev
    					second_country = scope:un_lc_m
    				}
    			}
    		}
    	}
    	set_variable = un_lc_dead
    }
    ```
  - Removal loops use `while = { limit = { any_in_list = { … } } random_in_list = { … save_scope_as = x } remove_list_variable … destroy }` so no list is mutated while it is iterated.
  - Monthly tick order: reap → adopt orphan pacts → age (`un_lc_armed` first pulse, then +1 month; shift = min(3 × months, 15)) → reset every country's shift vars → add each live campaign's shift to its member (cap each direction at 20).
  - `un_lean_lobbying = { value = 0  if = { limit = { var:un_lobby_shift_res ?= scope:un_resolution } add = var:un_lobby_for_shift subtract = var:un_lobby_against_shift } }` (vars always both set together).
  - Reasons: `un_res_why_yes_lobbying` / `un_res_why_no_lobbying`.
  - Loc: pact family (`_desc`, `_pact_desc`, `_action_propose_name`, `_action_break_name`, notifications), clause tooltips.
- [ ] **Step 4:** tests + audits green.
- [ ] **Step 5:** commit.

### Task 4: AI lobbying

**Files:** `un_lobby_effects.txt`, `un_lobby_triggers.txt`, `un_lobbying_values.txt`, `un_vote_effects.txt`, tests.

**Interfaces — produces:** `un_lobby_ai_monthly = yes` (resolution scope; `scope:un_resolution` saved).

- [ ] **Step 1: failing tests** (`AiLobbyingTest`): the monthly update calls `un_lobby_ai_monthly` after the campaign tick; the AI picks only `is_ai = yes` members; starts are gated on `influence >= un_lobby_ai_influence_floor` (150) and fewer than `un_lobby_ai_max_campaigns` (3) of its own; it creates the pact with `create_diplomatic_pact` then `un_lobby_campaign_start`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: implement.** Each month, for the proposer (direction for) and, on a resolution that accuses its target, for the target, its allies and its bloc leader (direction against), when AI, a member with a vote: first end its campaigns that are no longer needed (member's true lean already firmly its way, or own influence below 0), then start at most one: the lobbyable AI member it does not already lobby whose true lean is in the band it can win (for: −29 to +9; against: −9 to +29), nearest the line first (`ordered_country`, `order_by = un_lobby_ai_target_order`, `max = 1`).
- [ ] **Step 4:** tests + audits green.
- [ ] **Step 5:** commit.

### Task 5: The chamber's Delegations section

**Files:** `un_chamber_display_effects.txt`, `un_chamber_sguis.txt`, `un_chamber_widget.gui`, `un_dossier_effects.txt` (row upkeep), `un_lobbying_values.txt` (sort key), `un_vote_effects.txt` (list upkeep on vote), loc, `test_un_vote_lobbying.py` (`DelegationRowTest`), a throwaway generator in the scratchpad.

**Interfaces — produces:**
- Resolution list `un_res_delegates`; vars `un_deleg_row_0..23`, `un_res_deleg_firm_for`, `un_res_deleg_firm_against`, `un_res_deleg_more`.
- Member var `un_deleg_key`.
- `un_deleg_refresh_self = yes` (AI member = ROOT, `scope:un_resolution`): key, list upkeep, `un_deleg_reassign_rows`.
- sguis (all `saved_scopes = { op }`, op 0-23): `un_chamber_deleg_row_sgui`, `un_chamber_deleg_for_sgui`, `un_chamber_deleg_against_sgui`, `un_chamber_deleg_stop_sgui`, `un_chamber_deleg_pledge_for_sgui`, `un_chamber_deleg_pledge_against_sgui`; plus `un_chamber_deleg_summary_sgui`, `un_chamber_deleg_firm_list_sgui`.

- [ ] **Step 1: failing tests** (`DelegationRowTest`, the `test_un_chamber_mission_slots.py` shape): 24 `un_chamber_deleg_row` instances with ops 0-23; each passes one op to all 23 of its bindings; every switch of the six row sguis maps op N to its helper with `N = N`; `un_deleg_reassign_rows` assigns `un_deleg_row_N` at `position = N` for N in 0-23.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: implement.**
  - Sort key (displayed band, so the order never leaks the true lean): 4000 worked (campaign or pledge), 3000 undecided, 2000 leaning for, 1000 leaning against, 0 firm; plus a tie-break of 200 − |shown lean|.
  - `un_deleg_reassign_rows` (resolution): clear the 24 vars; unrolled `un_deleg_assign_row = { N = n COUNT = n+1 }` (guard `any_in_list count >= COUNT`, then `ordered_in_list … position = N … save_temporary_scope_as` + `set_variable`); count firm-for / firm-against / overflow.
  - Row text prints at resolution scope only (gotcha #27): name + band (true band when the viewer campaigns on the member, else shown band) + accuracy note + each campaign on it (lobbyist, direction, months, shift) + any pledge.
  - Buttons' `is_valid`: `custom_tooltip` clauses; the viewer-side check is `ROOT = { can_send_diplomatic_action = { target = prev type = … } }` inside `var:un_deleg_row_$N$ ?= { }` — a deliberate `prev` (the row member), with a `# REVIEWED` note.
  - Pledge sgui effect: `would_accept_diplomatic_action` → `un_lobby_accept_commitment`, else `un_lobby_record_attempt`.
  - Widget: collapsible "Delegations" header after the top panel, panel gated on `un_chamber_in_session_sgui`, intro note, summary line (tooltip: firm list), 24 generated rows. Generate rows and the 24-branch switches with a script; the test pins them.
- [ ] **Step 4:** tests + `format_paradox_tabs --check` + audits green; BOM on the `.gui`.
- [ ] **Step 5:** commit.

### Task 6: Docs, player guide, stale-text sweep

- [ ] `git grep -n -i "thirty\|day 30\|30 days" -- localization docs/systems docs/player_guide common/diplomatic_actions` and fix each hit about AI voting or lobbying windows.
- [ ] `docs/systems/journal_entry_systems.md` (CRLF — edit with `Edit`, confirm `grep -c $'\r$'`): lean paragraph, lifecycle, chamber, lobbying section.
- [ ] Headers of `un_lobby_effects.txt`, `un_lobbying.txt`, `un_dossier_effects.txt` rewritten for the new model.
- [ ] `docs/guides/scripting_best_practices.md`: `would_accept_diplomatic_action` resolves a requires-approval action against an AI from a scripted GUI; a ROOT-dependent value can't be cast from another country's event.
- [ ] Player guide `09-united-nations.md`: when members vote, reading leans, campaigns, pledges both ways, Decide later, the AI's lobbying, the Delegations section; rebuild with `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/build_player_guide.py`, then `--check`, and `check_player_guide_style.py --strict`.
- [ ] `organize_loc.py`; nothing lands in `te_unused_l_english.yml`.
- [ ] Full checks: the unittest suite minus `test_reload_post_load` with the main venv, `ruff check .`, the 17 CI audits in their CI modes, `check_localization_files.py`, `check_post_load_rosters.py`, `format_paradox_tabs.py --check`.
- [ ] Commit; fresh reviewer agent on the branch; fix; open the PR (`--base main`), body with the "Player guide" line and the in-game checklist.
