# Scaling modifiers, pruned entries and once-only events — design

Date: 2026-11-06. Issue #1404, without the journal entry map modes (built
separately, #1410–#1425), the outcome splits and the rest of the prep doc's
§§ 4.4–4.11 and § 7 (each filed as its own issue). The plan behind each item
is `docs/audits/vanilla_1_15_prep.md` §§ 4.2 and 4.11; the engine facts are
`docs/guides/scripting_best_practices.md` § "1.15 journal entries, scaling
modifiers and once-only events (probed)".

## Why

**Maintenance** (owner, 2026-11-06: "If we don't do it, we'll have a lot more
work in the long run"). Today a modifier that follows a number is removed and
re-added with a `multiplier` on a pulse. Each one has a refresh site that can
forget the removal and stack it, a tracker that can disagree with what is on
the country, and, because a revolution's winner inherits variables but no
modifiers, a repair that puts it back after a revolution. Vanilla 1.15's
`scaling_modifiers_while_active` declares the modifier on the journal entry,
with a value the engine re-evaluates: no pulse, no removal, no stacking, and an
inherited entry should carry it by construction, so the repair goes too.

Two side effects the owner counts as gains (2026-11-06):
- The modifier's tooltip names the system's journal entry as its source.
- A modifier held by an entry is not in `Country.GetTimedModifiers`, so it
  leaves the Nation tab's named lists and its section counts; the tab's type
  rows still show it, under the entry, in the engine's breakdown. Global
  Warming's policies and Banking's monetary modifiers already work this way.

## Goals

1. Every modifier a system re-adds with a `multiplier` on a pulse or a button,
   held on its journal entry or on a country that holds the entry, becomes a
   `scaling_modifiers_while_active` block on that entry (§ 4), and its refresh,
   removal, tracker and revolution re-add code goes. About 250 keys in eleven
   systems; § 4 names the few left as they are, with the reason.
2. Flat modifiers in the same systems convert alongside when it is easy: their
   on/off state already lives in a variable (a mirror like the UN's `_on`, or a
   derived one like Banking's phase), or one new variable is needed anyway
   (Cultural Hegemony's programmes, § 4.6).
3. `disable_evaluation` on every entry that can only appear while a game rule
   is on (§ 1).
4. `fire_only_once` on the 32 events that guard themselves with a variable
   nothing else reads, with a canary (§ 2).
5. `scripts/generators/convert_je_outcomes.py` retired (§ 3).
6. The tooling reads the new block before its first use (§ 3).

## Non-goals

- Flat toggled policies that have no variable behind them today (Banking's 38
  tools, Global Warming's other eight policies): a follow-up (owner, 2026-11-06).
- Modifiers on a state, building or interest group: an entry can't hold them.
- Country modifiers with no entry behind them (construction cost, judiciary,
  inheritance, Standard of Living expectations, orbital debris, …).
- Balance changes. A converted modifier gives what it gave, from the same
  numbers, a few days later at most.

## Engine facts this rests on (probed 2026-11-05)

- One block per modifier, repeatable:
  `scaling_modifiers_while_active = { modifier = X value = { value = var:y } }`
  (vanilla `08_tsarpoints.txt`, `00_communism.txt`).
- The value's root is the **owning country**. Country-only reads work. The
  mod's `*_for_je` wrappers (`owner = { … }`) still read correctly there, since
  `owner` takes a country and returns it (`event_targets.log`), but they lose
  their reason to exist.
- The value is re-evaluated on the entry's update; a change reached a
  `modifier:` read 2–5 days later.
- Negative values work. At 0 the modifier is off the entry and reads 0.
- `has_modifier` can't see a scaling modifier, on the entry or the country.
- It applies only while the entry is active.
- Not yet seen: whether an inherited entry re-applies it after a revolution,
  and whether the panel shows a zero row. Both are self-checks (§ 5).

## 1. `disable_evaluation`

For a country-context entry, `disable_evaluation` is checked while the entry is
inactive, before `is_shown_when_inactive` and `possible`. When true the
inactive record is deleted for good and never evaluated again; only
`add_journal_entry` can bring the type back. Vanilla's readme: "keep this to
cheap, permanent identity checks". A game rule never changes mid-game, so its
negation is the safe kind.

Each entry below gets `disable_evaluation = { NOT = { <its rule test> } }`,
the same test that is a top-level conjunct of its `is_shown_when_inactive`:

| Rule test | Entries |
|---|---|
| `has_game_rule = social_movements_enabled` | Civil Rights, Post-Scarcity, Digital Rights, Mental Health, Morphological Freedom, Human Augmentation |
| `has_game_rule = cultural_hegemony_enabled` | Cultural Hegemony |
| `has_game_rule = covert_warfare_enabled` | Covert Warfare |
| `has_game_rule = nuclear_weapons_enabled` | Nuclear Program |
| `has_game_rule = decolonization_enabled` | Colonial Empire |
| `has_game_rule = united_nations_enabled` | United Nations |
| `has_game_rule = heir_education_enabled` | Heir Education (the monarchy test beside it is not permanent and stays out) |
| `has_game_rule = custom_religions_allowed` | Create New Religion |
| `has_game_rule = world_war_enabled` | World War |
| `sr_space_race_on = yes` | the eight live Space Race entries |
| `te_banking_system_on = yes` | Banking (the rule half of `te_banking_entry_expected`; the decentralized and rebel tests beside it are not permanent and stay out) |
| `gm_system_enabled = yes` | Grand Monuments |
| `te_tax_code_on = yes` | Tax Code |

The retired Moon Base (`is_shown_when_inactive` and `possible` both
`always = no`) gets `disable_evaluation = { always = yes }`, which deletes the
inactive record every country holds of it (#1416 counts 286 for each such entry).

Left out, each because a country can still come to qualify: Global Warming
(the rule, or a law any country can enact), State Collapse (decentralized
nations become recognized ones, `decolonization.txt`), Strategic Reserve (a
technology), the five vanilla entries the mod copies (vanilla gives none of
them a prune), and the Map Room's (map modes are out of scope).

Side effect: with the record gone, `add_journal_entry` of the type is no
longer refused (#1416). So every add site of these types reads the same rule in
its own `limit` (`gm_system_enabled`, `te_banking_entry_expected`,
`has_game_rule = nuclear_weapons_enabled`, `sr_space_race_on`, `ce_reentry_due`'s
`decolonization_enabled`, `has_game_rule = united_nations_enabled`); two did not
until PR 1, the commission offer's add (`gm_com_send_offer`) and the UN debug
seat (`te_debug_un_seat_member`).

**Test:** every `disable_evaluation` in a mod entry is `always = yes` or a
`NOT` of rule tests, and each rule test it names is a top-level conjunct of the
same entry's `is_shown_when_inactive`. A rule test is `has_game_rule`, or a
named trigger whose body (followed through further named triggers) reads only
`has_game_rule` under `AND`/`OR`/`NOT`; `sr_space_race_on`,
`gm_system_enabled`, `te_tax_code_on` and `te_banking_system_on` are such
wrappers today. Top-level conjuncts are read through named triggers called as
one (`sr_milestone_followup_is_shown`, `te_banking_entry_expected`). The other
way round, every mod entry with a rule test among those conjuncts carries a
prune, so a new rule-gated entry can't go without one. So a prune
can't drift from the gate it mirrors, and no prune can come to read a variable
set after the first tick, which would delete the entry for good in a game that
later qualifies.

## 2. `fire_only_once`

`fire_only_once = yes` stops a second firing for the same country; a try whose
trigger fails doesn't use it up (probe C20). The 32 events below each set a
variable in `immediate` that only their own trigger reads (`NOT = { has_variable
= X }`), never removed:

- `society_technology_events` .1–.6, .9, .12, .13, .16, .17, .19–.21, .25–.31
  (21, `ste_event_<n>_fired`)
- `te_judiciary_events` .30–.36 (7, `te_jud_heard_*`)
- `cultural_hegemony` .8, .9 (`ch_milestone_significant`, `_dominant`)
- `post_scarcity_events.3`, `surveillance_events.4` (the two AI debates)

Each gets `fire_only_once = yes` and loses its `set_variable`. **The trigger's
guard stays as a read until a removal date** (with the other old-save repairs,
`project_old_save_repair_removals`): a save made before the change holds the
variable but no engine record, and the guard keeps those events from firing a
second time there. In a new game nothing sets the variable, so the guard is
inert. Not converted: `ste_event_8_fired`, `_18_`, `_36_`, `_37_` and
`wonder_asteroid_deflected` are read elsewhere (the on-action dispatcher reads
.8 and .37); the World War, inheritance, UN charter and debug variables are
removed again or read elsewhere.

**The canary.** Unknown: whether the engine's record that an event fired
survives a save and load, and whether a revolution's winner inherits it (it
inherits variables). One event, `society_technology_events.1`, keeps setting its
variable, and its guard is bypassed only in games started after the change (a
global marker set once at game start): `OR = { has_global_variable = <marker>
NOT = { has_variable = ste_event_1_fired } }`. Old saves keep the guard like the
other 31, and new games rely on `fire_only_once` alone. Its `immediate` logs
`TE_SELF_CHECK BROKEN fire_only_once_kept` when the marker is set and the
country already holds the variable, which can only happen if the event fired
twice for one nation. It is the right event to
watch: its other guard is a ten-year modifier its option grants, which expires
and which a revolution's winner loses, so its trigger reopens either way.
Fallback on the play-test list: put the variables back.

## 3. Tooling

- **`je_multiplier_scope_audit`** (#1403) reads `scaling_modifiers_while_active`.
  In a country-context entry the value's root is the owning country, so a
  country read is fine and the audit only parses the block; an `owner = { … }`
  wrapper still works there (the engine's `owner` link takes a country as input
  and returns it, `event_targets.log`), so the mod's `*_for_je` wrappers keep
  reading correctly, and each conversion calls the bare value and deletes the
  wrapper once nothing else calls it. In a contextless entry (`context = none`)
  (its own or its group's: vanilla's `je_group_global_*`) the value has no root
  scope at all, so it flags country reads as it does for `je:` multipliers, and
  `owner`, `root` and bare `var:` reads too. Suppression as today, on the
  `value` line.
- **A scaling modifier must exist.** A test: every `modifier =` in a
  `scaling_modifiers_while_active` names a static modifier the mod or vanilla
  defines.
- **`has_modifier` can't see one.** An audit or test fails on `has_modifier = X`
  (script or GUI `HasModifier`) for any X that a mod entry declares in
  `scaling_modifiers_while_active`, on an `add_modifier`/`remove_modifier`
  of it, and on any other `key = X` that hands it to a helper
  (`un_state_on = { MODIFIER = X }` adds `$MODIFIER$`).
- **The Nation tab** (`gen_nation_tab.py`) registers modifiers script *adds*
  without a duration. A converted key is no longer added, so its registry lines
  (SECTIONS, ROWS, SOURCE_GROUPS, NOT_ON_COUNTRY) go with its conversion and the
  generator reruns; `test_nation_tab.py` already fails on a line that matches no
  candidate. **The Budget panel needs nothing:** it itemizes money modifiers by
  the mirror type each carries (`country_te_budget_<side>_<key>_add`, read with
  `GetModifier.GetValueFor`), which counts a modifier propagated from an entry
  the same as one on the country.
- **`convert_je_outcomes.py` and its fixture tests go.** The two tree checks
  that still matter (no entry keeps a field 1.15 dropped; every entry declares
  `activation_description`) move to `test_journal_entry_shape.py`, which also
  holds §§ 1 and 3's entry checks. The docs that name the converter
  (`scripting_best_practices.md`, `vanilla_patch_runbook.md`, the migration
  record) are updated.

## 4. Scaling modifiers, system by system

Inventoried at `6cfc6c212` (2026-11-06). File:line references are to that
commit; the implementation re-reads each site.

### 4.0 Rules for every conversion

1. **One declaration per key** on the entry that holds it, today's multiplier as
   its `value`, called bare (no `*_for_je` wrapper).
2. **Guard every variable read**: `value = { value = 0 if = { limit = {
   has_variable = X } add = var:X } }`. A declared value is read on the entry's
   own schedule, which can come before the first pulse that writes X (an entry
   active before its first refresh; an old save without a newer variable).
3. **Restate the "off" condition in the value.** Today's add sits behind a gate
   (a law, a threshold, a running cycle); the value is 0 outside it. Thresholds
   that are mechanics stay (Cultural Hegemony's ≥ 1 and ≥ 0.1, the offworld
   population minimum); a dead band that only spared a re-add goes.
4. **Prefer a cached variable to a heavy live value.** The value is evaluated
   about every 4 days per holder (`JOURNAL_ENTRY_UPDATE_ACTIVE`). Read
   `var:ch_total`, never `cultural_pull_total` (a loop over states and
   buildings). A cheap live value (`temperature_anomaly_display`,
   `nd_taboo_burden_value`) is fine and follows its inputs sooner.
5. **Delete** the refresh: the remove/re-add sites, trackers that only drove the
   re-add (`*_mod_on`, `*_cost_cached`, `<mod>_mult`), "missing" checks and any
   revolution repair that re-adds a converted key (it would double it).
6. **Rewrite every `has_modifier` reader** as a test of the value's inputs,
   through a named trigger where there are several (`gw_warming_felt`,
   `ch_trails_hegemon`).
7. **Strip the old copy once.** A save from before the change holds the added
   copy, which would stack with the declaration. Each key gets
   `if = { limit = { has_modifier = X } remove_modifier = X }` in its old scope,
   in `legacy_je_modifier_cleanup_effect` (`legacy_modifier_cleanup.txt`,
   monthly) with a removal date (`project_old_save_repair_removals`).
   `has_modifier` sees only the added copy, so the guard never touches the
   declaration. Lines in that file that *re-add* a key (the 68 colony keys,
   `:342-899`) become remove-only. As built (PR 4, after its review): each
   system's lines are one `legacy_scaling_strip_<system>` effect, which the
   monthly strip calls and the system's entry also runs from its weekly pulse,
   so an old copy stacks with its declaration for days rather than up to a
   month (`test_scaling_strip.py`).
8. **Keep the preview.** A button or event option that adds a modifier today
   shows its effects in the tooltip; one that only sets a variable shows
   nothing (`silent_variable_audit` flags an option that does). Each such site
   gains `show_as_tooltip = { add_modifier = { name = X multiplier = … } }`, the
   pattern `un_vote_cast_yes` uses (`un_vote_cast_effects.txt:59-149`), or a
   `custom_tooltip` naming the change.
9. **Registry and tests.** The key's Nation tab lines go (§ 3), its
   `REVIEWED` tags on deleted lines go (a stale tag fails `--strict`), and the
   tests that pin the add are rewritten to pin the declaration.
10. **Docs.** The system's `docs/systems/mod_systems/` file, the play-test list,
   and the player guide only where it states a source or a timing that changed.

Two behaviour changes are accepted everywhere: a button's effect reaches the
modifier 2–5 days later (the panel's own figures read variables and move at
once), and a GDP-scaled cost follows GDP continuously instead of monthly.

### 4.1 Strategic Reserve (1 key)

`st_res_sell_profit_modifier`, on the country (`st_res_effects.txt:987-1000`).
Value: guarded `var:st_res_sell_profit` (the booked week; not the live
`st_res_total_sale_profit`, which floats with prices). The entry never ends.
Its two modifier lines go; the variable writes stay. Docs:
`strategic_reserve_system.md:18`, `:443`.

### 4.2 Covert Warfare (5 keys, on the entry)

| Key | Value | Notes |
|---|---|---|
| `intelligence_capacity_defense` | `intelligence_capacity_modifier_mult` | off below 1 total |
| `iw_domestic_defense` | `covert_operations_available_slots` | a pact pass; acceptable every 4 days, or cache it in `covert_ops_sync_all` |
| `iw_funding_defense` | `covert_ops_funding_ci_mult` | |
| `covert_operation_funding_cost` | `covert_operation_cost_mult` | 0 at funding 0 |
| `iw_tradecraft_bonus` | `covert_tradecraft_bonus_mult` | |

Goes: the pulse blocks (`je_covert_warfare.txt:183-228`),
`covert_tradecraft_refresh_bonus`, the modifier half of
`covert_refresh_funding_state` (keep it as a shell: `test_covert_priority.py`
needs `covert_apply_priority_change` to call it). Tests:
`test_covert_tradecraft.py` (pins the add). No repair code. No feedback loop:
three keys feed `intelligence_capacity_total`, none its own value.

### 4.3 Global Warming (4 keys)

| Key | Held | Value |
|---|---|---|
| `global_warming` | entry | `{ value = temperature_anomaly_display min = 0 }`: the reading can go negative without aerosols, and a negative value would invert every harm |
| `gw_aerosol_monsoon_modifier` | entry | `gw_aerosol_mask` if `gw_country_in_monsoon_region` |
| `renewable_investment_cost_modifier` | country → entry | `gw_renewable_investment_cost_value` while `gw_policy_renewable_investment_active` |
| `aerosol_injection_cost_modifier` | country → entry | `gw_aerosol_injection_cost_value` while `has_variable = gw_aerosol_injection_policy` |

`global_warming`'s 21 readers (`extra_on_actions.txt:1119`–`:1251`,
`environmentalism_events.txt:285`–`:1234`) become `gw_warming_felt =
{ has_journal_entry = je_global_warming temperature_anomaly_display >= 0.01 }`;
most already test a higher threshold. Goes: the monthly blocks
(`je_global_warming.txt:158-192`), the cost apply/sync/sweep
(`global_warming_effects.txt:54-95`, `:673-691`) and its global-pulse call
(`extra_on_actions.txt:1053`); treaty 109 (`109_enforce_emissions_reduction.txt`)
stops calling the apply. Tests: `test_gw_geoengineering.py`,
`test_country_climate_policies.py` (heavy pins). Policy flats: carbon removal and
aerosol injection already have mirror variables, so they convert too and their
restore effects (`gw_restore_*_policy_effect`) go; the other eight need
variables (follow-up).

### 4.4 Nuclear (3 keys + 7 flats, on the entry)

| Key | Value |
|---|---|
| `nuclear_weapon_program_funding` | `nuclear_program_display_weekly_cost` (guarded funding × step) |
| `nd_upkeep_cost` | `var:nd_upkeep_weekly_cached` while `nd_is_armed` and `nd_is_initialized` (the cache stays: the panel reads it) |
| `nd_taboo_possession_cost` | `nd_taboo_burden_value` (live, O(1)) |
| `nd_doctrine_mod_1`..`_5`, `nd_readiness_mod_2`, `_3` | 1 while armed, initialized and `var:nd_doctrine` / `var:nd_readiness` = N |

The flats convert because their mirror variables exist. Goes:
`nuclear_weapons_program_cost_cached`, the modifier branches of
`nuclear_program_refresh_state_effect`, `nd_upkeep_mod_on`, the doctrine and
readiness trackers and removers, `nd_rebuild_posture_modifiers` with its marker,
the `immediate` tracker resets (`je_nuclear_program.txt:161-168`), the dead
country-scope removals in two treaty articles, and the `(hidden_modifier)`
tags at `nuclear_weapon_effects.txt:23`, `:48`. Tests: `test_nuclear_taboo.py`,
`test_nuclear_deterrence.py` (`TestManagedFamilies`). Every armed country meets
the entry's `possible`, and custody adds it at once.

### 4.5 Colonial Empire (4 keys, country → entry; bands optional)

| Key | Value |
|---|---|
| the three programmes | `colonial_<x>_level_value ÷ colonial_programme_max_level` (levels 0–3 give today's ladder) |
| `colonial_development_investment_expense_modifier` | `colonial_invest_weekly_cost` (live, 0 at level 0) |

Both endings remove the level variables, so nothing carries between runs. Goes:
`colonial_programme_apply_modifier` and its refresh, `decol_sync_programmes` (the
revolution repair) and `colonial_invest_cost_week`. The pre-levels migration
(`decol_migrate_programme(s)`, the `has_modifier` fallbacks in
`colonial_empire_values.txt`) stays until its save window closes. The five band
modifiers convert as 0/1 on `colonial_empire_live_tier` if that value reads the
bar from a country root (a self-check); `colonial_empire_solidified_modifier`
stays the ending's permanent country reward too. Tests:
`test_decolonization_civil_war.py`.

As built (PR 3): each programme's value is a ladder giving today's literals
(0 / 0.333 / 0.667 / 1), not the exact thirds. The pre-levels migration went
after all: 1.15 loads no save from before 2026-11-05 (#1430), levels landed
2026-10-09, and its `has_modifier` fallbacks would have read an old copy as
level 3 beside the declaration. The bands stay on the pulse: Solidified is
also the ending's permanent country reward, so declaring it needs an exception
in the misuse test (the two copies never coexist: the entry ends before the
grant), and declaring only four would leave two bands or none at the 90 edge
for up to a month. Follow-up: #1466.

### 4.6 Cultural Hegemony (5 keys + 4 programmes)

| Key | Held | Value |
|---|---|---|
| `cultural_hegemony_effect` | entry | `var:ch_total` if ≥ 1, max 100 |
| `cultural_hegemony_foreign_benchmark` | country → entry | `var:ch_benchmark_applied`, which the pulse now writes every month (0 below 0.1) |
| `ch_cultural_program_funding` / `_cost` | entry | `ch_program_funding_level_value` / `ch_program_funding_total_cost_mult` under the Ministry of Culture law |
| `ch_world_exposition_cost` | entry | `ch_program_funding_cost_mult` while the exposition runs |
| the four programmes (`ch_world_exposition`, `ch_cultural_institutes_program`, `ch_global_media_campaign`, `ch_cultural_protectionism_program`) | entry | 1 while a new mirror variable is set |

The exposition's cost is added once at enable today and never refreshed, so it
converts with its programme, and the programme needs a mirror variable; the
other three get one too (small, and it closes audit F8 for them). The
benchmark's 23 readers become `ch_trails_hegemon`; the debug harness sets the
variable instead of adding the modifier. Goes: the pulse blocks
(`je_cultural_hegemony.txt:140-166`), `ch_refresh_funding_modifiers`, the three
`_for_je` wrappers. Tests: `test_cultural_hegemony_layout.py`.

As built (PR 3): the mirror variables are `ch_world_exposition_on`,
`ch_cultural_institutes_on`, `ch_global_media_campaign_on` and
`ch_cultural_protectionism_on`, set by the enable effects and removed by the
disable effects and the Ministry-repeal strip; the old-save strip sets each
from an old copy before removing it. The funding pair's gate is
`ch_program_funding_in_force` (the law and a level of at least 1), so a repeal
takes it off within days. A revolution's winner now keeps its programmes (the
variables carry), which closes audit F8 for them.

### 4.7 Banking (10 cycle keys + 23 derived flats; the monetary layer stays)

| Key | Value |
|---|---|
| `financial_cycle_government_fiscal_policy_effect` | `financial_cycle_government_fiscal_policy_effect_size` while the cycle runs (`has_variable = finance_cycle_value`) |
| `bubble_inertia_moderate/high/extreme` and `_coop` (6) | the inertia curve, in its band (> 0.5, ≥ 35, ≥ 65) and economy (market laws / Cooperative Ownership; none under Command Economy); six declarations keep the tier names and icons |
| `planning_treasury_pool_balance` | a new cache `ce_pool_balance_cached`, written monthly and by inject/withdraw, under Command Economy |
| `banking_external_sterilization_charge` / `_import_charge` | new caches written where the charge is applied today, zeroed on every off path, while the tool is on |
| the 18 phase modifiers, the 5 stance bands | 1 in their band of `var:finance_cycle_value` (and law) / at `var:te_mon_stance_band` = N |

The derived flats convert because they need no new state; with them go
`remove_all_banking_phase_modifiers`, the phase half of
`banking_cycle_post_event_refresh`, the stance tracker and the F7 reset in
`immediate`. The prep doc's worry about the planning pool is out of date: it no
longer subtracts its own contribution (`extra_script_values.txt:2412-2417`); the
cache keeps its monthly cadence anyway. `banking_cycle_sim.py`'s note on the
one-pulse lag gets a line. Tests: `test_banking_phase_modifiers.py`,
`test_banking_external_tools.py`.

**Left as they are: the 12 scaled and 14 flat monetary modifiers**
(`te_monetary_rate_paid`, minting, wage dividend, FX, controls fatigue,
arrangements, board and union lines, inflation bands, …). They sit on the
country whenever there is no banking entry, which is every country in a
rule-off game (the rate paid runs under every setting), decentralized nations,
rebels and the first fortnight. An entry-only declaration would have those
countries borrow at 0%; a hybrid keeps the country branch and adds a home gate,
so nothing gets shorter. The 38 tools have no mirror variables (follow-up).

As built (PR 4): 33 declarations, each gated on the cycle latch
(`has_variable = finance_cycle_value`) but the two charges, gated on their
tool (no tool runs on a dormant entry); the phases read the existing
`banking_cycle_is_<phase>` and economy triggers, whose edges equal the deleted
chain. The pool and the two external charges read new caches
(`ce_pool_balance_cached`, `banking_external_*_charge_cached`), written where
the old adds ran; the old-save strip writes each before removing its copy. A
charge now starts and stops on the entry update after Enable or Disable, so a
tool's life nets between one weekly charge short and one over. The five
multipliers old saves' copies name (`*_for_je`, `bubble_inertia_multiplier_script_value`)
stay, uncalled, until the strip goes. No gate reads back one of these costs.

### 4.8 Grand Monuments (36 keys + 15 boons, on the entry)

All of `gm_apply_national_modifiers` (`gm_effects.txt:1138-1182`): 27
`gm_national_*`, 8 signed `gm_ig_approval_<ig>` and `gm_arch_diversion`, each
reading its cached step variable (`gm_s_*`, `gm_vanity_ledger`,
`gm_arch_innovation_units`), guarded. The 15 boons are 1 while their countdown
variable exists. Goes: `gm_remove_national_modifiers`, `gm_add_national(_signed)`,
the boon, trophy and archaeology add/remove helpers. No `has_modifier` readers
and no repair code. The four keys with `state_*` fields (education, Liberty,
Olympic, Heroes) are already on the entry today; whether such a field reaches
the states is the unread `gm_education_reaches_states` self-check, and its
fallback becomes "keep those four as country `add_modifier`s". Not candidates:
`gm_local_*` (state), `gm_upkeep` (building), `gm_name_carrier_slot` (a
company-slot timing). Tests: `test_grand_monument_registry.py`,
`test_grand_monument_archaeology.py`, `test_grand_monument_trophies.py`.

### 4.9 Tax Code, Light setting (21 keys, country → entry)

Relief ×5 (`var:te_tax_light_rl_<key>`) and reactions ×16
(`var:te_tax_lr_mag_<ig>` by the sign of `var:te_tax_lr_<ig>`), generated:
`gen_tax_code.py` stops emitting the adds and emits 21 named values, and the
entry carries 21 short declarations a test holds to the generator's lists. The
entry then carries gameplay, not only display, so it gets a safety net like
Banking's (`te_banking_entry_net`: a monthly `add_journal_entry` for a country
in force without the entry) and its "display-only" header and
`tax_code_schema.md` are reworded. A step's relief lags its tax level by up to 4
days. The view bands stay (the full code shares them).

As built (PR 6): the 21 values are `te_tax_light_relief_<key>_value` and
`te_tax_light_react_<ig>_<pos|neg>_value`, each restating its old add's gate: a
relief while the law levies that tax and its variable is above 0, a reaction's
rounded size on the side of the running reaction's sign once it is a whole
point. The levies test is read at each entry update, not at the sync, so a law
change ends a relief within days. `te_tax_light_gen_apply_reactions` now only
writes the sizes and is `te_tax_light_gen_reaction_sizes`. The net,
`te_tax_light_entry_net` on each country's monthly pulse, goes beyond Banking's
in two ways: it skips decentralized countries (never migrated), and a country
whose inactive copy waits (`add_journal_entry` is refused then, and the engine
activates that copy). The entry already had `should_update_on_player_command =
yes`; whether that update also re-reads its scaling modifiers, so a step's
relief lands at once, is unprobed, and the loc says "within a few days". The
Nation tab loses its 21 rows (the reactions section goes). An older save's
copies go through `legacy_scaling_strip_tax_code`, monthly and from the entry's
weekly pulse.

### 4.10 Space Race (24 + 12 + 80 keys)

- **Milestones** (8 entries × `sr_space_program_cost`, `sr_funding_progress`,
  `sr_funding_throughput`): the existing per-milestone values while
  `sr_milestone_billed_<m>`. Goes: `sr_recalculate_cost`'s clear/apply helpers
  (it shrinks to `sr_refresh_milestone_statuses`), `sr_cost_modifiers_missing`,
  the seven recalculation branches in `space_race_on_actions.txt:85-155` and
  their three caches.
- **Solar colonization entry, 12**: the six population and autonomy modifiers
  (`sr_emig_refresh_modifiers`) and the six facility modules
  (`sr_mod_refresh_facilities`, generated), each with its gate restated.
- **Colony specializations, 80** (`sr_colony_<world>_<spec>`): 1 × `sr_site_mult_<a|b>_<key>`
  while `<mod>_held`, generated by `gen_solar_sites.py` into its own file.
  Goes: the `<mod>_mult` records, `sr_sync_colony_spec_base` with its 80 calls,
  `sr_mod_seen_self_check`; the 68 colony lines in `legacy_modifier_cleanup.txt`
  become remove-only.
- **Flats with mirror variables** (the two approaches per milestone, the 16
  choices, the 40 discoveries, `sr_solar_system_trade`) convert too; with them
  `sr_sync_<m>_entry` and `sr_sync_space_race_entries` go.
- **Left**: `sr_orbital_superiority` and the extraplanetary base's room bonus and
  penalty (carriers without an entry), `sr_commercial_space_dividend` (outlives
  the race), `sr_fleet_upkeep_goods` (a building modifier).

### 4.11 United Nations (48 keys + 5 mirrored flats)

After founding every non-decentralized country holds the active entry
(`un_entry_unlocked` is the founding tech or `global_var:un_founded`;
`can_deactivate = no`; no outcomes), members or not, so sanction and embargo
targets carry their keys too.

| Group | Keys | Value |
|---|---|---|
| Membership benefits | `un_membership_benefits_modifier` | authority ÷ 50 × (1 + alignment), Contested or better and `un_member_draws_benefits` |
| Dues | `un_dues_modifier` (country → entry) | `var:un_dues_cached`; every off path (withholding, unassessed, billed to the overlord, leaving, dissolution) removes the cache |
| Programmes | `un_peacekeeping_contributor_cost`, `un_development_contributor_modifier`, `_cost` | the price or benefit variable while its `_on` mirror is set; pledged-but-not-paying stays a state, read from the mirror |
| Fund | `un_development_patron_modifier`; `un_dev_fund_pool_grant_modifier` / `_treasury_grant_modifier` (country → entry) | `var:un_dev_fund_patron`; `var:un_dev_fund_grant` split by `un_dev_fund_pays_into_pool`, so the hidden `un_economy.1` goes |
| Missions | `un_mission_service_cost`, `un_electoral_observers_modifier` (country → entry) | their cached variables |
| Mandate, seabed | `un_mandate_war_support_modifier`, `te_seabed_royalty_modifier` (country → entry) | `un_enforcement` under `un_teeth_mandate_support_applies`; the royalty cache, zeroed when the country stops paying |
| Conventions | 16 (7 on the entry, 9 on the country) | `un_convention_multiplier` while `<key>_on`; the ×0.01 floor existed only so `has_modifier` survived at Moribund |
| Regime terms | 17 `un_regime_*` (country → entry) | a presence variable per term × `un_enforcement` (adaptation × `un_regime_adaptation_multiplier`, shared intelligence `un_regime_strong_steps`) |
| Embargo, sanctions | `un_arms_embargo_target_modifier` / `_voluntary_modifier`, `un_sanctions_target_modifier` (country → entry) | `un_enforcement` by `var:un_arms_embargo_form` while `un_arms_embargo_months`; a new `un_sanctions_target_on`, migrated once from the modifier |
| Mirrored flats | peacekeeping contributor, human rights champion, arms control participant, champion and undermine order costs | 1 while `_on` (undermine also needs no champion mirror: a merge can deliver both) |

**Regime terms keep their cadence.** The terms are re-read yearly or on a tier
change on purpose: the climate-emitter cut lowers the emission share it is
tested on, and the refugee and space rankings would flicker at their cutoffs.
So `un_regime_refresh_country` stays, writes a presence variable per term
instead of adding, and only the multiplier becomes live.

**The mirror machinery is the hazard.** `un_state_reconcile_*` forgets a mirror
whose modifier `has_modifier` can't see, and `un_state_heal_needed` would report
every converted key missing and re-add it. For each converted key: its lines in
`un_state_restore_all`, the reconcile calls and `un_state_heal_needed` go in the
same commit, `un_state_on` / `un_convention_on` reduce to `un_state_record`, and
`un_regime_reapply_*`, `un_arms_embargo_restore` and the sanctions re-add go. The
mirrors become the truth, so every `has_modifier` reader of a converted key
reads `has_variable = <key>_on` (the conventions alone have about 120, in
Resettlement, Nuclear, the Space Race and the generated Demographics values,
`gen_demographics_lx.py`). `legacy_modifier_cleanup.txt:285-341`, which re-adds
seven conventions on the entry, becomes "strip and set the mirror".

**Stays:** `un_member_modifier` and the flat membership set (264 readers; every
gate above reads it), `un_sanctions_enforcer_modifier` (no mirror; its loss on a
revolution orphans the regime by design), the entry's `immediate`, the heal and
`un_state_rebuild` for the flat set, `un_repair_after_civil_war` and the
headquarters handover. **Left:** `te_antarctic_station_upkeep`, a Global
Commons cost with no UN gate (no entry with the UN rule off). Tests:
`test_un_state_mirror.py`, `test_un_convention_registry.py`,
`test_un_lift_sanctions.py`, `test_un_membership.py`, `test_un_dev_fund_sizes.py`
and others that pin the adds.

## 5. Self-checks and the play-test list

Once-a-game `debug_log` lines (CLAUDE.md, "In-game checks"), each excluding the
degenerate case so OK can't be a false pass:
- **`scaling_live`**: a country with an active Strategic Reserve entry and
  `var:st_res_sell_profit >= 1`, read at the start of a weekly pulse, before the
  week's income is booked again, when the variable still holds what the last
  weekly pulse booked (a panel action or `un_economy.2` rebooks it mid-week,
  and the declaration lags the change) and no added copy from an older save is
  left (`has_modifier` sees only that copy):
  `modifier:country_te_budget_income_reserve_add` (a field only that modifier
  carries) equals the value within 1%. Proves a declaration reaches the
  country's sums from a country-root value.
- **`scaling_inherited`**: at `te_civil_war_on_won` the winner is marked; 30
  days later, if it holds an active `je_covert_warfare` with
  `covert_operation_cost_mult > 1`, `modifier:country_te_budget_expense_covert_add`
  is over 0 (only revolutionaries' wins count: a government that wins keeps its
  own entry; and rebels who ran a Covert Warfare entry of their own during the
  war, marked by a variable from its monthly pulse, are skipped, since theirs
  would declare anyway). An inherited entry arrives with no added modifiers,
  so an absent declaration reads exactly 0. Proves an inherited entry
  re-applies its declarations. PR 2 already relies on it: Covert Warfare's and
  Global Warming's monthly pulses used to re-add their modifiers on an
  inherited entry, and GW's two policy restore effects are deleted.
  Fallback if BROKEN: no effect re-activates or removes an entry in place, so
  the winner's entries end through their `invalid` trigger (a flag set at
  `te_civil_war_on_won`) and are added again (an inherited entry arrives empty
  and re-runs `immediate` anyway, so little is lost), or the systems whose
  repairs were deleted get them back. Per the
  owner's rule (CLAUDE.md, "In-game checks"), this check doesn't hold back a
  merge: PRs 3, 7 and 8, which delete revolution repairs, land on the offline
  gate like the rest.
- **`fire_only_once_kept`** (§ 2): BROKEN only.
- The existing `gm_education_reaches_states` covers entry-held `state_*` fields.

Play-test list (`docs/testing/vanilla-1-15-playtest.md`, C7): a converted
modifier at value 0 shows no zero row in the entry panel or the country's
tooltip (fallback if one shows: hide the scaling-modifier icon strip on the
mod's own entries in `gui/journal_entry.gui`, a GUI-only change); the Budget
panel's rows include entry-held money modifiers (a GUI getter, unprobed); the
tooltip names the entry as the source.

## 6. Delivery

A stack of PRs, each to `main` (CLAUDE.md, "Stacked PRs must target `main`"),
each independently mergeable once the groundwork is in:

| PR | Contents | Keys |
|---|---|---|
| 1 | Groundwork: §§ 1–3, and this doc | — |
| 2 | Strategic Reserve, Covert Warfare, Global Warming, Nuclear; the `scaling_live` and `scaling_inherited` self-checks | 13 + 9 flats |
| 3 | Colonial Empire, Cultural Hegemony | 9 + 9 flats |
| 4 | Banking's cycle | 10 + 23 flats |
| 5 | Grand Monuments | 36 + 15 boons |
| 6 | Tax Code, Light setting | 21 |
| 7 | Space Race | 116 + 73 flats |
| 8 | United Nations | 48 + 5 flats |

Each PR updates its system's doc in `docs/systems/mod_systems/`, the player
guide where a figure or a source it states changes, and the play-test list. The
issue for the outcome splits and one per §§ 4.4–4.11 / § 7 feature are filed
with PR 1.

## 7. Calls made in this design (owner approved all ten, 2026-11-06: "As you suggest is fine")

1. **Banking's monetary layer stays as it is** (§ 4.7). Every country under
   the rule holds the entry, dormant until its cycle starts, and the layer's
   modifiers already sit on it there. But the layer also serves countries no
   entry reaches: every country in a rule-off game (the rate paid replaces
   vanilla's cancelled base rate), decentralized nations, rebels and the first
   fortnight. Converting it means a hybrid that keeps the country branch and
   adds a second path beside it (owner asked, 2026-11-06; held unless the owner
   wants the hybrid in PR 4).
2. **Tax Code Light converts, with a safety net** (§ 4.9): its entry starts to
   carry gameplay, and the net adds it to a country the engine leaves out.
3. **Bubble inertia keeps six declarations**, so the modifier list still names
   the tier and the extreme tier keeps its red flag.
4. **Flats convert where the variable exists or is derived**, plus Cultural
   Hegemony's four programmes, which need a variable each because the
   exposition's cost does.
5. **Regime terms keep their yearly re-read**; only their strength is live.
6. **Left as they are:** `te_antarctic_station_upkeep` (no UN gate),
   `sr_orbital_superiority`, the extraplanetary base's room bonus and penalty,
   `sr_commercial_space_dividend`, `gm_name_carrier_slot`, `un_member_modifier`
   and `un_sanctions_enforcer_modifier`.
7. **Grand Monuments' four `state_*` keys convert with the rest**; if
   `gm_education_reaches_states` reads BROKEN, those four go back to the
   country as plain `add_modifier`s.
8. **Old saves keep their once-guards as reads** (§ 2) until a removal date,
   since a save made before the change has the variables but no engine record.
9. **The repair-deleting PRs don't wait for `scaling_inherited`** (§ 5): it
   is a self-check with a named fallback, like every in-game unknown.
10. **A zero row, if one shows, is hidden in the GUI** (§ 5), not by keeping
    the modifiers off the entry.
