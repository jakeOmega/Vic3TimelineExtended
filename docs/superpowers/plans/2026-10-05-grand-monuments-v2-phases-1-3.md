# Grand Monuments v2, phases 1–3 (numbers, commissions and names, policy) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut a Grand Monument level to 1,000 construction, add commissions (world moments, petitions and AI building
through one mechanism) with monument names, and add a national monument policy.

**Architecture:** Everything builds on v1's files (`gm_effects.txt`, `gm_values.txt`, `monument_triggers.txt`,
`monument_events.txt`, the JE and its widget). Commission state is country variables; name records are state
variables beside v1's `gm_skin`; the policy is one country flag read by script values that scale v1's per-step values.
New script goes in new files where it is a new subsystem (`gm_commission_effects.txt`, `gm_commission_triggers.txt`,
`gm_commission_values.txt`, `gm_name_effects.txt`, `gm_policy_*`), and v1's files gain only the hooks.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.14.5), `.gui`, YAML loc, Python `unittest` registry tests.

**Spec:** `docs/superpowers/specs/2026-10-05-grand-monuments-v2-design.md` (v2) on v1's
`docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md`.

## Built as, after review (2026-10-05)

Two independent reviews changed five things this plan prescribes. The code and `mod_systems.md` § Grand Monuments are
the record; read these before reusing a task below.

- **War commissions** come from 1.14.5's `on_won_war` / `on_lost_war` (`scope:war`, `scope:enemy_country`,
  `scope:benefitted_from_wargoal` / `victim_of_wargoal`), gated on `is_warleader = root` and
  `war_duration_months >= 12`. The `on_wargoal_enforced` latches, `on_peace_agreement_signed_war_leader`,
  `monument_events.22` and the monthly war counter of Task 4 were never needed: a capitulation fires no peace agreement.
- **The unveiling** runs from the next refresh (`gm_unveil_pending`), not inside the ceremony's option: it reads the
  production method the dedication has just activated, which may not be visible in the same effect.
- **The policy's factors** scale the step counts after the curve (`gm_policy_scale_steps`), not grandeur before it:
  halving grandeur takes off about one step, not half the effect.
- **The policy's upkeep** is `goods_input_construction_mult` ±0.5 on the monument building (`gm_policy_upkeep_open` /
  `_mothballed`). Throughput does not scale the `level_scaled` maintenance input, so Task 10's throughput modifier did
  nothing.
- **The AI's ceremony** at a monument that can answer an open commission gives every other dedication ×0, not just
  the commission's +100, which lost about one in five.

Smaller fixes from the same reviews: the regime tracker writes nothing on a civil-war side; a counted monument that
drops out lowers the baseline; a petition doesn't rename a named monument; a naming can't be orphaned; the naming sweep
waits a year.

## Phase order (owner, 2026-10-05)

The owner swapped the spec's phases 3 and 4: the policy (§5) is now **phase 3** and the monuments standing in 1836 (§4)
**phase 4**. This plan builds phases 1, 2 and the policy (the spec's old phase 4, the new phase 3) in one branch and one
PR, a commit per phase. Phases 4–6 (1836 monuments, trophies, historical commissions) are not in it.

## Global Constraints

- Construction per level **1,000**; vanity radicals **0.005** of pops per level; vanity legitimacy **−0.3** per ledger
  unit (static modifier and `gm_step_vanity`, pinned equal); Rededicate **500** a level. Curve, steps and ledgers
  unchanged (§1).
- Commission target **5** grandeur; time **60 months**; extension **+36, once**, reward halved (§2.3, §8).
- Rewards through ledgers only: fulfilled IG ledger **+15**, promise ledger **+5**; after extension **+8 / +2.5**;
  declined **−10**; missed **−5**; lapsed nothing. Promise ledger decays **×0.97** a month and applies **linearly**
  (`gm_national_promise`, "A Promise Kept") (§2.4).
- **At most one commission open or on offer.** World moments are dropped, not queued, while one is. Petitions:
  **1/120** a month while eligible, none for **60 months** after any commission closes (§2.5).
- **Owning a monument is never a penalty; not building one can be.** Anniversary events keep all-positive options.
- The petitioning IG is stored as a **flag naming its type**, never an IG scope (civil-war winners have other IGs).
- Policy: Open ×1.5 tourism / anniversaries ×2 / upkeep ×1.5; State Ceremonial regime grandeur ×1.5 / tourism ×0.5;
  Mothballed upkeep ×0.5 / standing ×0.5 / local ×0.5 / no anniversaries; cooldown **60 months**, the first choice
  free (§5).
- Every scripted GUI that changes state has `ai_is_valid = { always = no }`; every option or button that moves a
  number the UI shows says so in a `custom_tooltip` (`silent_variable_audit`).
- Brace files: tabs, exactly one UTF-8 BOM. `gm_*` loc keys route to `te_miscellaneous_l_english.yml`, event keys to
  `te_events_l_english.yml`; run `python3 organize_loc.py` and commit what it moves.
- Name patterns' customizable-localization targets inherit the caller's context (`scripting_best_practices.md`
  § "Keep customizable-localization target keys as plain text"), so every pattern that reads data exists once per
  context: `_row` (`State`, the JE row) and `_evt` (`SCOPE.sState('monument_state')`, events).

## Review Focus

1. **A commission whose fixed state can't host it.** The capital already holds a monument of another dedication; one
   monument per state, so the commission could never be fulfilled. Expected: a fixed-state source falls back to
   "anywhere" when its state holds a monument of another dedication (Task 4 test).
2. **A country without monuments.** Offers, the open commission's monthly tick and the JE must all work for a country
   that owns no monument yet. Expected: `gm_country_on_action` also runs on an open commission, the JE activates on an
   offer or an open commission, and the stop branch of `gm_country_monthly` waits for the commission (Task 5 test).
3. **A civil war during a commission or a founding year.** The revolutionary country must not write its own
   `gm_founded_year` (its value would beat the nation's in the winner), and no offer goes to a side while
   `te_cw_role` is set (Task 4 test).
4. **The progress count after a contest.** A monument counted toward the commission that becomes contested drops out;
   progress is floored at 0 and never negative (Task 5 test).
5. **Rename gates.** A contested or heritage monument keeps its name: Rename and Name It are disabled for status codes
   3 and 4 (Task 8 test).

---

## File map

| File | Responsibility | Tasks |
|---|---|---|
| `docs/superpowers/specs/2026-10-05-grand-monuments-v2-design.md` | phase order swap | 0 |
| `common/script_values/extra_script_values.txt` | `construction_cost_grand_monument` | 1 |
| `gm_effects.txt`, `gm_values.txt`, `gm_modifiers.txt` | §1 numbers; hooks for commissions, names, policy | 1, 3–9 |
| `common/scripted_triggers/gm_commission_triggers.txt` (new) | commission gates, fit, source triggers | 3–5 |
| `common/scripted_effects/gm_commission_effects.txt` (new) | offer, accept, decline, tick, fulfil, miss, lapse, AI | 3–5 |
| `common/script_values/gm_commission_values.txt` (new) | progress, displays | 3–6 |
| `common/on_actions/monument_events_on_actions.txt` | world pulse, war, ruler death, formation hooks | 4 |
| `common/history/extra_history.txt` | founding years | 4 |
| `common/scripted_effects/gm_name_effects.txt` (new) | name records, forms, AI naming | 7 |
| `common/customizable_localization/gm_custom_loc.txt` | name patterns, form nouns, commission words | 6, 7 |
| `events/monument_events.txt` | `.21` offer, `.22` war end, `.24` form, `.25` namesake | 4, 7 |
| `common/scripted_guis/gm_sguis.txt` | extend, rename, policy buttons | 6, 8, 10 |
| `gui/journal_entry_widgets/grand_monuments_widget.gui` | Commission section, name title, rename, policy line + buttons | 6, 8, 10 |
| `common/journal_entries/je_grand_monuments.txt`, `monument_triggers.txt` | JE gates | 5 |
| `common/messages/extra_messages.txt` | commission notices | 5 |
| `common/company_types/gm_name_carrier.txt`, `common/buildings/gm_name_carrier.txt`, PM/PMG (new) | typed names | 9 |
| `common/modifier_type_definitions/mod_entity_modifier_types.txt` | `building_grand_monument_throughput_add` | 10 |
| `events/te_debug_monuments_events.txt` | `.2` commissions and policy | 11 |
| `test_grand_monument_registry.py`, `test_grand_monuments_layout.py` | registries and layout | every task |
| `docs/player_guide/02-timeline.md`, `17-reference.md`, PDF; `docs/systems/mod_systems.md` | docs | 1, 12 |

---

### Task 0: Swap phases 3 and 4 in the spec

**Files:** Modify `docs/superpowers/specs/2026-10-05-grand-monuments-v2-design.md`, `docs/systems/mod_systems.md`.

- [ ] Decisions table "Phasing" row: `Numbers → commissions with names → policy → 1836 monuments → trophies → historical
  commissions (§10; the owner swapped policy ahead of the 1836 monuments on 2026-10-05)`.
- [ ] Headings: `## 4. Monuments standing in 1836 (phase 4)`, `## 5. Monument policy (phase 3)`.
- [ ] §10 table: phase 3 = §5 policy, needs 1; phase 4 = §4 1836 monuments, needs 2; phase 6 needs "2, 4 (`LANDMARKS`)".
- [ ] `mod_systems.md` pointer line: list v2's built and unbuilt parts once Tasks 1–11 land (Task 12 rewrites it).
- [ ] Commit `docs: Grand Monuments v2 — policy becomes phase 3, the 1836 monuments phase 4`.

### Task 1: Phase 1 numbers (§1)

**Files:** `common/script_values/extra_script_values.txt:100`, `gm_effects.txt` (`gm_state_vanity_backlash`),
`gm_values.txt` (`gm_step_vanity`, `gm_state_rededicate_cost`), `gm_modifiers.txt` (`gm_national_vanity`), loc
(`gm_je_how_choices`, `gm_je_how_hard_times`, any other hand-kept 10,000 / 5,000 / 5% / 3 in `gm_*` and
`monument_events.*`), `test_grand_monument_registry.py`, player guide `02-timeline.md`.

- [ ] Tests first: registry pins `construction_cost_grand_monument = 1000`, `add_radicals_in_state = { value = 0.005 }`,
  the vanity pair at −0.3, `multiply = 500` in `gm_state_rededicate_cost`. Run, see them fail.
- [ ] Change the values. Rewrite the comment above `construction_cost_grand_monument` (it argues the construction-sink
  design): a level is a tenth of v1's because the doubling curve, not the price, stops spam (v2 §1).
- [ ] Loc: "for 500 a level"; "turns 0.5% of the state's pops radical and costs 0.3 legitimacy for each such level".
- [ ] `country_legitimacy_base_add` has `decimals = 0`, so one ledger unit (−0.3) renders "−0" on the legitimacy
  breakdown; the JE row (`gm_je_val_vanity`) shows one decimal. Keep the spec's value and record this on the modifier
  (comment) and in the PR body. If `modifier_visibility_audit` flags it, suppress with `# REVIEWED` naming the reason.
- [ ] Player guide: 10,000 → 1,000; Rededicate 5,000 → 500; vanity 5% → 0.5%, 3 → 0.3.
- [ ] Run the registry and layout tests; commit `Grand Monuments v2 phase 1: a level costs 1,000; vanity and
  Rededicate a tenth`.

### Task 2: Phase 2 foundations — the commission record, the promise ledger, the dedication dispatch

**Files:** new `gm_commission_triggers.txt`, `gm_commission_effects.txt`, `gm_commission_values.txt`; `gm_effects.txt`
(ledger lists), `monument_triggers.txt` (`gm_ledgers_idle`), `gm_modifiers.txt`, `gm_values.txt`.

**Interfaces (produced):**
- Country variables: `gm_com_offered` (yes, while the offer event is open), `gm_com_open` (yes), `gm_com_source` (flag:
  `victory` `defeat` `centenary` `ruler_death` `regime` `space` `petition`), `gm_com_ig` (flag, an IG key as in v1's
  `gm_ig_to_flag_on_owner`), `gm_com_dedication` (flag, one of v1's 12 keys), `gm_com_state` (state, optional),
  `gm_com_target` (5), `gm_com_baseline`, `gm_com_months_left`, `gm_com_extended` (yes), `gm_com_namesake` (flag),
  `gm_com_form` (flag), `gm_com_name_year`, `gm_com_name_char` (character), `gm_com_name_enemy_cap` (state),
  `gm_com_occasion` (flag), `gm_com_last_state` (state: the last monument a level or dedication touched),
  `gm_com_cooldown` (timed, 60 months: no petition), `gm_promise_ledger`.
- `gm_promise_ledger` joins `gm_init_ledgers`, `gm_zero_ledgers`, `gm_decay_ledgers` (RATE = 0.97) and
  `gm_ledgers_idle`. `gm_national_promise` (`country_legitimacy_base_add = 1`, multiplier = the ledger) joins
  `gm_apply_national_modifiers` / `gm_remove_national_modifiers`; `gm_step_promise = 1`; `gm_display_promise`.
- `gm_country_ledger_ig_by_flag = { VAR = <country var holding an IG flag> AMOUNT = <n> }` (country scope): adds
  AMOUNT to `gm_ig_ledger_<ig>` for the IG the flag names. Eight `if`s, one per IG, as `gm_state_ledger_ig_one`.
- Trigger `gm_country_can_commission = { KEY = <dedication> }` (country): the dedication's gate as the ceremony's
  option triggers have it (crown → `monument_government_is_crowned`; republic → `monument_government_is_republican`;
  revolution → `gm_government_is_revolutionary`; leader → `gm_can_raise_leader_monument`; religious → no State
  Atheism; artistic, naturalist → romanticism; scientific → empiricism; industrial → marketing_research and no Industry
  Banned; athletic → television_broadcasting; civic, war_memorial → always).
- Trigger `gm_country_com_gate_holds` (country): `gm_country_can_commission` for the flag in `gm_com_dedication`
  (twelve `AND`s in an `OR`).
- Trigger `gm_state_has_dedication_flag = { VAR = <owner var> }` (state): the monument's PM is the one the owner's
  flag names (twelve `AND`s in an `OR`).
- Trigger `gm_state_com_counts` (state): `gm_state_status_fits`, the owner's commission dedication, and the fixed
  state if any (`owner.var:gm_com_state ?= { save_temporary_scope_as = gm_tmp_com_state }` then `this =
  scope:gm_tmp_com_state`).
- Script value `gm_com_fit_grandeur` (country): sum of `gm_state_grandeur` over states with `gm_state_com_counts`;
  `gm_com_progress` = that minus `var:gm_com_baseline`, floored at 0 (guarded reads).
- Effect `gm_com_clear` (country): removes every `gm_com_*` record except `gm_com_cooldown`, `gm_com_last_state` and
  the moment trackers (Task 4).

- [ ] Registry tests: the promise ledger is in all four lists and `gm_national_promise` pairs with `gm_step_promise`;
  `gm_country_can_commission` names every dedication and matches each ceremony option's trigger; the dispatchers name
  all twelve keys and all eight IGs.
- [ ] Write the files; run; commit with Task 3.

### Task 3: The offer, accept, decline (§2.3, §2.4, §2.6) — reviewed

**Files:** `gm_commission_effects.txt`, `events/monument_events.txt` (`.21`), loc.

- `gm_com_send_offer` (country, the record already written): `set_variable = gm_com_offered`, `trigger_event = {
  id = monument_events.21 }`.
- `monument_events.21` (country event, `placement = root`, `event_image` per source: victory/defeat
  `unspecific_military_parade`, others `unspecific_world_fair` — view on the contact sheet first, duration 3).
  `trigger = { has_variable = gm_com_offered }`. `immediate`: `save_scope_as = gm_com_country`; resolve
  `scope:gm_com_ig_scope` from the flag (`ig:ig_<x>`, eight `if`s) for the loc. Description by source
  (`first_valid` of `triggered_desc`). Options:
  - **a, Accept** (`default_option = yes`: an ignored offer opens a commission, whose miss costs less than a
    decline): `custom_tooltip = { text = gm_com_accept_tt gm_com_accept = yes }`. `ai_chance = { base = 10
    modifier = { trigger = { gm_com_ai_declines = yes } factor = 0 } }`.
  - **b, Decline**: `custom_tooltip = { text = gm_com_decline_tt gm_com_decline = yes }`. `ai_chance = { base = 1 }`.
- `gm_com_ai_declines` (country trigger): at war, `gm_country_hard_times`, `construction_queue_government_duration >= 52`
  or `scaled_debt > 0`.
- `gm_com_accept`: remove `gm_com_offered`; set `gm_com_open`, `gm_com_months_left = 60`, `gm_com_baseline =
  gm_com_fit_grandeur`, `gm_active`; `add_journal_entry` if missing (rule on); `if = { limit = { is_ai = yes }
  gm_com_ai_queue = yes }`; `trigger_event = { id = monument_events.20 }`.
- `gm_com_decline`: `gm_country_ledger_ig_by_flag = { VAR = gm_com_ig AMOUNT = -10 }`, `gm_active`, then
  `gm_com_close = yes`.
- `gm_com_close`: `gm_com_clear = yes`; `set_variable = { name = gm_com_cooldown months = 60 }`.
- `gm_com_ai_queue` (country, AI): picks the state, saved as `scope:gm_com_build_state`, in order: `gm_com_state`;
  else `ordered_scope_state` with a fitting monument of the dedication (`gm_state_status_fits` and
  `gm_state_has_dedication_flag = { VAR = gm_com_dedication }`) by `gm_state_grandeur`; else the capital if it has no
  monument; else `ordered_scope_state` by `state_population` among incorporated states without one. Then
  `set_variable = { name = gm_tmp_queued value = 0 }` and `while = { limit = { var:gm_tmp_queued <
  var:gm_com_target } scope:gm_com_build_state = { start_building_construction = building_grand_monument }
  change_variable = { name = gm_tmp_queued add = 1 } }`, then remove `gm_tmp_queued`. (`while` with a limit, not
  `count = var:`: `<int>` arguments no-op on script values.)
- Ceremony (`.2`): each option's `ai_chance` gains `modifier = { trigger = { owner = { gm_com_wants = { KEY = <key> }
  } } add = 100 }` (`gm_com_wants`: `gm_com_open` and the dedication flag); the description gains a
  `gm_com_ceremony_hint` line naming the commission while one is open. Option order is static, so "listed first" is
  this line and the AI's weight (deviation, PR body).

- [ ] Tests: `.21` has two options with tooltips wrapping the effects, `default_option` on Accept, AI declines under the
  four conditions; `gm_com_accept` records the baseline and queues only for the AI with the `while` shape; decline
  writes −10 and starts the cooldown; the ceremony's twelve options carry the commission weight.
- [ ] Implement; run; **review** (fresh reviewer: scopes, the `while`, the AI state pick); commit.

### Task 4: Sources (§2.2, §2.5) — reviewed

**Files:** `gm_commission_effects.txt`, `gm_commission_triggers.txt`, `monument_events_on_actions.txt`,
`events/monument_events.txt` (`.22`), `common/history/extra_history.txt`.

- **The world pass** `gm_com_world_on_action` in `on_monthly_pulse_country`, trigger `gm_system_enabled = yes`,
  every country. Bookkeeping always runs; offers only while `gm_com_can_offer` (no `gm_com_offered`, no `gm_com_open`,
  no `te_cw_role`, `is_revolutionary = no`, the country has at least one incorporated state).
  - `gm_com_track_war`: `is_at_war` → `gm_war_months` +1; else remove it.
  - `gm_com_track_ruler`: `ruler ?= { save_temporary_scope_as = gm_tmp_ruler }`; if `var:gm_ruler` is not that ruler,
    set `gm_ruler` to it and `gm_ruler_months` to 0; else +1.
  - `gm_com_init_founded`: no `gm_founded_year`, no `gm_com_start_country`, no `te_cw_role`, not revolutionary →
    `gm_founded_year = year`. Old saves: if `NOT = { has_global_variable = gm_com_seeded }`, run
    `gm_seed_founding_years` and set `gm_com_start_country` on every country, then the global.
  - `gm_com_track_regime`: `gm_regime_now` flag = revolution (`gm_government_is_revolutionary`, checked first: a
    Council Republic is both), crown, republic, else none. If `gm_regime_last` exists and differs and the new one is
    not none, and `gm_com_can_offer`, and no fitting monument of it (`gm_com_fit_grandeur` read with a temporary
    dedication) → **regime** offer (petitioner: crown → landowners, republic → intelligentsia, revolution →
    trade_unions; namesake year). Then `gm_regime_last = gm_regime_now`.
  - `gm_com_track_space`: for `orbital` and `moon_landing` (the two crewed firsts): `sr_was_first_<m>` and no
    `gm_com_seen_space_<m>` → set the seen flag; offer **space** if `gm_com_can_offer` (Intelligentsia, To the Nation,
    the capital, occasion `space_<m>`).
  - `gm_com_track_centenary` (January only, `month = 0`): `gm_founded_year` and age = `year − founded` is 100 or 200,
    no `gm_com_centenary_<n>` → set it; offer **centenary** if free (Petty Bourgeoisie unless marginal, else the
    strongest IG in government; To the Nation; the capital; occasion `centenary`).
  - `gm_com_try_petition`: free, no `gm_com_cooldown`, `random = { chance = 1 … }` with chance 0.833 (1/120 as a
    percent) → compute `gm_fit_<key>` for the eleven petitionable dedications (all but the Leader, whose approving IG is
    the ruler's), then `random_list` with one entry per (IG, dedication) pair in v1's table, each `trigger`: the IG in
    government, `gm_country_can_commission`, `var:gm_fit_<key> < 5`. Namesake city, anywhere.
- **War**: `on_wargoal_enforced` (ROOT = the enforcer, `scope:target` the loser): ROOT `gm_war_won` (30 days) and
  `gm_war_enemy_cap` = target's capital; target `gm_war_lost` (30 days) and `gm_war_enemy_cap` = ROOT's capital.
  `on_peace_agreement_signed_war_leader` (ROOT = a war leader): `gm_war_months_at_peace` = `gm_war_months` (30 days),
  `trigger_event = { id = monument_events.22 days = 1 }` (hidden; lets both on-actions land in either order). `.22`:
  `gm_war_months_at_peace >= 12` and `gm_com_can_offer` → **victory** if `gm_war_won` (Armed Forces; War Memorial;
  anywhere; occasion victory, enemy capital, the year; form arch), else **defeat** if `gm_war_lost` (Armed Forces, or
  the strongest IG outside government if they are in it; namesake occasion defeat, the year; form memorial).
- **A ruler's death**: `on_character_death` (ROOT = the character): `is_ruler_of_own_country = yes`, owner
  `var:gm_ruler = root` and `gm_ruler_months >= 180`, owner `gm_com_can_offer` → **ruler_death** (the late ruler's IG
  via `interest_group ?= { gm_ig_to_flag_on_owner = { VAR = gm_com_ig } }`, else the strongest IG in government; To the
  Nation; the capital; namesake ruler with `gm_com_name_char = root`; form mausoleum).
- **Formation**: `on_country_formed` (ROOT = the country) sets `gm_founded_year = year`.
- **Fixed state**: `gm_com_fix_state` (country): the capital becomes `gm_com_state` only if it has no monument, an
  undedicated one, or one of the commission's dedication; otherwise the commission is anywhere.
- **Founding years** `gm_seed_founding_years` (scripted effect, called from `extra_history.txt` GLOBAL and the old-save
  branch): `c:USA ?= 1776`, `HAI 1804`, `PRG 1811`, `CHL 1818`, `MEX 1821`, `PEU 1821`, `BRZ 1822`, `BOL 1825`, `URU
  1828`, `BEL 1830`, `GRE 1830`, `ECU 1830`, `VNZ 1830` (tags checked against vanilla history); every country at
  history time also gets `gm_com_start_country`. Deviation (PR body): a country standing in 1836 without a listed
  founding has **no** founding year, so 1936 does not bring a centenary to every 1836 country at once.

- [ ] Tests: the world pass's order and its gates; the four trackers; the war pair and `.22`'s two branches; the
  ruler-death conditions; the petition table matches v1's approve column; the fixed-state fallback; the founding list
  and the civil-war guards.
- [ ] Implement; run; **review** (on-action ROOTs, the civil-war guards, edge detection); commit.

### Task 5: The open commission — tick, progress, fulfil, miss, lapse; the JE gates (§2.3, §2.7) — reviewed

**Files:** `gm_commission_effects.txt`, `gm_effects.txt` hooks, `je_grand_monuments.txt`, `monument_triggers.txt`
(`gm_entry_unlocked`), `monument_events_on_actions.txt` (`gm_country_on_action` gate), `monument_events.txt` (`.1`),
`extra_messages.txt`, loc.

- `gm_country_on_action` runs on a monument, `gm_active` **or `gm_com_open`**. `gm_country_monthly`'s stop branch adds
  `NOT = { has_variable = gm_com_open }`, and it calls `gm_com_monthly` after the refresh.
- `gm_country_refresh` calls `gm_com_check_progress` after `gm_compute_totals` (so after a level, a dedication or a
  month).
- `monument_events.1` and `gm_state_dedicate` set the owner's `gm_com_last_state` to the monument's state.
- `gm_com_check_progress` (country): open and `gm_com_progress >= var:gm_com_target` → `gm_com_fulfil`.
- `gm_com_monthly` (country, open): `gm_com_months_left` −1; **lapse** if a fixed state is no longer ours or
  `gm_country_com_gate_holds = no` (notice, `gm_com_close`); else **miss** at 0 (IG −5, notice, close); AI extension
  when `gm_com_progress * 2 >= target`, `months_left <= 6`, not extended.
- `gm_com_fulfil`: the named state = `gm_com_last_state` if it counts (`gm_state_com_counts`), else the tallest
  counting monument; on it `gm_state_take_commission_name` (Task 7) unless it carries `gm_unveiled_for_com`; IG +15 /
  +8 extended; `gm_promise_ledger` +5 / +2.5; notice; close.
- `gm_com_extend` (scripted GUI and AI): once; `gm_com_extended`, +36 months.
- JE: `is_shown_when_inactive` and `possible` gain `OR = { <monument> has_variable = gm_com_open has_variable =
  gm_com_offered }`; `invalid`'s AND gains `NOT = { has_variable = gm_com_open } NOT = { has_variable =
  gm_com_offered }`; `gm_entry_unlocked` gains the same OR (tooltip loc updated); `gm_country_refresh`'s
  `add_journal_entry` adds on an open commission too.
- Notices: `gm_com_fulfilled_notice` (good), `gm_com_missed_notice`, `gm_com_lapsed_notice` (bad), players only.

- [ ] Tests: the gates agree in all four places; the tick's order (lapse before miss); fulfil names the right state and
  writes the halved rewards after an extension; `gm_com_progress` floors at 0.
- [ ] Implement; run; **review**; commit.

### Task 6: The Commission section in the JE (§2.7)

**Files:** `grand_monuments_widget.gui`, `gm_sguis.txt` (`gm_com_extend_sgui`), `gm_commission_values.txt`
(`gm_disp_com_open`, `gm_disp_com_progress`, `gm_disp_com_target`, `gm_disp_com_frac`, `gm_disp_com_months`,
`gm_disp_com_extended`), `gm_custom_loc.txt` (country: `gm_com_ig_name`, `gm_com_dedication_name`,
`gm_com_form_name`, `gm_com_namesake_word`, `gm_com_where`), `test_grand_monuments_layout.py`.

- `te_gm_sec_commission` between the overview and National Effects in `te_gm_status_sections`, visible while
  `gm_disp_com_open` = 1, flag `gm_commission_closed` (open by default). Lines: "**[IG]** ask for **[dedication]**
  [where]"; "A [form], named for [namesake word]"; a `gm_step_row` bar (`gm_disp_com_frac`, "N / 5 grandeur"); "N
  months left"; **Ask for More Time** (`gm_com_extend_sgui`, valid while not extended; tooltip says +36 months and the
  halved reward).
- National Effects' Fading Legitimacy gains "A Promise Kept" (`gm_display_promise`), and its subheader's gate and
  `gm_disp_national_any` include it.
- How Grand Monuments Work gains "Commissions" (subheader + two notes).

- [ ] Layout tests (order, flag default, gates, label budgets, every key exists); implement; run; commit with Task 5.

### Task 7: Names (§3.1–§3.3)

**Files:** new `gm_name_effects.txt`; `gm_custom_loc.txt`; `monument_events.txt` (`.11` chains on, `.24` form, `.25`
namesake); `gm_effects.txt` (`gm_clear_state`, `gm_state_offer_skins*`, `gm_state_choose_skin`); loc.

**Records on the state:** `gm_namesake` (flag: `city` `state` `ruler` `honours` `year` `occasion`), `gm_form` (flag),
`gm_name_char`, `gm_name_year`, `gm_name_occasion` (flag), `gm_name_enemy_cap` (state); `gm_clear_state` removes all
of them, so a rededicated monument is named again.

**Forms** (the §3.2 draft fixed by dedication and skin):

| Skin / dedication | Forms, first is the default |
|---|---|
| Opera, Gardens, Observatory, Exhibition Hall, Stadium | fixed: `opera_house`, `gardens`, `observatory`, `exhibition_hall`, `stadium` |
| Faith skins | `faith` (the noun is the skin's own name) |
| Generic | `column`, `arch`, `obelisk`, `statue`, `gate`, `hall`, `tower`, `memorial`; `mausoleum` only from a ruler's-death commission |
| Latin | `column`, `arch`, `forum` |
| Greek | `pantheon`, `stoa`, `column` |
| Hebrew | `gate`, `court`, `pillar` |
| Sanskrit | `pillar`, `gate` |
| Ge'ez | `stele` |
| Slavonic | `memorial_church`, `column` |
| Avestan | `gate`, `hall` |
| Arabic | `hall`, `gate` |
| Chinese | `hall`, `gate`, `pagoda` |
| Irish | `round_tower`, `high_cross` |
| Nahuatl, Mayan | `pyramid` |
| Norse | `rune_stone`, `hall` |
| Gothic | `hall_of_fame`, `tower` |
| Prussian | `hill_shrine` |
| Aramaic | `rock_cut` |

**Namesakes and patterns** (`gm_name_<namesake>_<ctx>`, ctx = `row` | `evt`; `F` = the form noun from
`gm_form_name`):

| Namesake | Pattern | Offered |
|---|---|---|
| city | "the [city hub] F" | always |
| state | "the [state] F" | always |
| ruler | "[character first name]'s F" (falls back to `year` when the character no longer exists) | a ruler exists |
| honours | "F of the Crown / Republic / Revolution / Nation / Faith / Fallen" | crown, republic, revolution, civic, religious, war_memorial |
| year | "the F of [year]" | always |
| occasion | victory "the F of the [enemy adjective] War"; defeat "the F to the Fallen of [year]"; centenary "the Centenary F"; space "the [achievement] F" | from a commission |

- `gm_monument_name_row` / `gm_monument_name_evt` (type state, first valid): `gm_name` → `gm_name_custom_<ctx>` (Task
  9); else by `gm_namesake`; else (an old or AI monument with no records) the v1 title, the skin's name.
- `.11` (skin, players) stays; each of its options and the AI path then call `gm_state_offer_forms`: one fitting form
  → set it and go on; more → `.24` (players). `.24`'s options: a default "As the architects proposed" (the
  commission's form if it fits, else the skin's first), then one option per form with its trigger. Then
  `gm_state_offer_namesakes` → `.25` (players; AI: `gm_state_name_for_ai`): default "As proposed" (the commission's
  namesake if one is open for this dedication, else city), then city, state, ruler, honours, year, occasion. Each
  `.25` option sets `gm_unveiled_for_com` when a commission is open for this monument's dedication. Both events end
  with `owner = { trigger_event = { id = monument_events.20 } }`.
- `gm_state_take_commission_name` (state, from fulfilment): copies the owner's `gm_com_namesake`, the form if it fits
  the skin, and the records.
- The name replaces the skin title in `gm_row_title` and in event loc that names a monument (`.2`'s follow-ups,
  `.3`–`.15`, `.16`/`.17`), through `[SCOPE.sState('monument_state').GetCustom('gm_monument_name_evt')]`.

- [ ] Registry: `FORMS` and `NAMESAKES` tables; every form has loc and an option in `.24` gated on its skins; every
  namesake has both pattern keys and a `.25` option; `gm_clear_state` clears every record; `.24`/`.25` have a default
  option and an image.
- [ ] Implement; run; commit.

### Task 8: Rename from the JE row (§3.3)

**Files:** `gm_sguis.txt` (`gm_rename_sgui`), widget (`gm_monument_row`), loc, layout test.

- `gm_rename_sgui` (saved scope `gm_state`): valid while ours and status 2 (upheld) — not contested, heritage or
  undedicated; effect `scope:gm_state = { gm_state_offer_forms = { RENAME = yes } }` (the chain from Task 7, with
  `.24`/`.25` shown even when only one form fits, so the namesake can still change).
- The row gets a **Rename** button under the detail lines, shown while status code 2.

- [ ] Layout test (Review Focus 5); implement; commit with Task 7.

### Task 9: Typed names (§3.5)

**Files (new):** `common/company_types/gm_name_carrier_company_types.txt`, `common/buildings/gm_name_carrier.txt`,
`common/production_method_groups/gm_name_carrier_pmgs.txt`, `common/production_methods/gm_name_carrier_pms.txt`;
`gm_modifiers.txt` (`gm_name_carrier_slot`), `gm_sguis.txt` (start, mark-old, use, cancel), `gm_name_effects.txt`
(`gm_name_carrier_close`), `gm_effects.txt` (sweep in `gm_country_monthly`), `gm_values.txt` (`gm_is_being_named`,
`gm_has_name_old`, `gm_state_has_typed_name`), widget, loc.

- As written in spec §3.5 (code there), adapted: the row's mode 0 offers **Name It** beside Rename and **Clear Name**
  while `gm_name` is set; the title's typed-name textbox toggles on `gm_state_has_typed_name`. `gm_name_custom_row`
  prints `[State.MakeScope.Var('gm_name').GetFlagName]`; `gm_name_custom_evt` the same through
  `SCOPE.sState('monument_state')`.
- Keep the anchor building type forever once released (spec §3.5).
- [ ] Tests: the company's potential reads `gm_naming_active`; `add_company` follows `gm_naming_active`; every sgui is
  AI-invalid; the sweep closes an expired naming; every read of `Var('gm_name_carrier')` sits inside mode 1.
- [ ] Implement; run; commit as its own commit (it can be dropped from the PR without touching the rest).

### Task 10: Phase 3 — the monument policy (§5)

**Files:** new `common/scripted_effects/gm_policy_effects.txt`; `gm_values.txt` (factors), `gm_effects.txt`
(`gm_compute_totals`, `gm_state_monthly`, `gm_clear_state`), `gm_modifiers.txt` (`gm_policy_upkeep`),
`mod_entity_modifier_types.txt`, `monument_events_on_actions.txt` (anniversaries), `gm_sguis.txt`, widget, loc.

- `gm_policy` (country flag: `standard` `open` `ceremonial` `mothballed`; absent reads as standard).
- Factors (script values): `gm_policy_factor_standing` (country; 0.5 mothballed, else 1) multiplies `gm_g_standing`
  before the curve — prestige and cultural pull both halve, since both read standing grandeur (decision, PR body);
  `gm_policy_factor_regime` (1.5 ceremonial) multiplies `gm_g_regime` and `gm_g_leader`; `gm_policy_factor_tourism`
  (state, via owner: 1.5 open, 0.5 ceremonial, 0.5 mothballed) gives the new `gm_local_tourism_steps`;
  `gm_policy_factor_local` (state: 0.5 mothballed) scales `gm_local_steps` for the dedication locals.
- Upkeep: `gm_policy_upkeep` (`building_grand_monument_throughput_add = 0.5`) on the monument's state from
  `gm_state_monthly`, multiplier `gm_policy_upkeep_mult` (+1 open, −1 mothballed); registered as a modifier type
  (`percent = yes`, `decimals = 0`, `color = neutral`); removed in `gm_remove_local_modifiers`.
- Anniversaries: `monument_events_on_action`'s trigger excludes mothballed; the do-nothing weight is halved under
  Open (`modifier = { if = { limit = { … open } multiply = 0.5 } }`), which about doubles the events.
- Buttons: four (Standard, Open to the Public, State Ceremonial, Mothballed), one scripted GUI each, valid while not
  the current policy and no `gm_policy_cooldown`; `gm_policy_set = { P = <p> }` sets the flag, starts the 60-month
  cooldown unless this is the first choice (`gm_policy_chosen` absent → set it, no cooldown), refreshes. Spec says
  three buttons; a fourth returns to Standard (deviation, PR body).
- AI (`gm_country_monthly`, `month = 0`, AI only, no cooldown): Mothballed in hard times or `scaled_debt > 0`; State
  Ceremonial with legitimacy < 40 and `gm_g_regime > 0`; Open with a monument in a state with a Tourism Industry; else
  Standard. Changes only when the pick differs.
- Display: a line under the overview cells ("Monument Policy: [name]", factors on hover); the buttons at the foot of
  National Effects; How Grand Monuments Work gains "Monument policy".
- [ ] Registry `POLICIES` table (button, factors, AI rule, loc); layout tests; implement; run; commit `Grand Monuments
  v2 phase 3: the monument policy`.

### Task 11: Debug

`te_debug_monuments.2`: offer each source (seven options, writing a record as the source would and firing `.21`);
fulfil / miss / lapse the open commission; cycle the policy; print `TE_MONUMENTS:` commission and policy lines.
`gm_debug_log` gains the commission and policy lines.

### Task 12: Docs, audits, whole-branch review, PR

- `mod_systems.md` § Grand Monuments: commissions, names, policy, file list, the deviations; the v2 pointer says what
  is built.
- Player guide `02-timeline.md`: "Commissions", "Monument names", "Monument policy" subsections at the depth of the
  existing ones; `17-reference.md` rows (commission, A Promise Kept, monument policy); rebuild the PDF; style lint.
- Lessons into `scripting_best_practices.md` (one paragraph each, only what was learned).
- `organize_loc.py`; tabs and BOM checks; CI's `--strict` audits; the full unittest suite; `ruff check .`; the
  worktree server's audits (`POST :8951/reload?mod_only=true&audits_only=true`).
- Whole-branch review in two parts (script; docs/GUI); fix; push; PR into `main` with the in-game checklist (§9 items
  1–6 and 8) and the deviations.
