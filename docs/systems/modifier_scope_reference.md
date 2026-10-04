# Modifier Scope Reference: Which Mod Modifiers Are State-Level

A planning map of the mod's own modifier types by the scope they work at: which are already state-level, which country-level ones could move to states, and which must stay national and why. Read it before designing a mechanic that should vary between a country's states: it tells you whether a lever already exists and what a move would cost.

**Snapshot: 2026-09-26.** Counts and grant sources drift as content lands. Re-check a row before building on it: `/modifier-grants/<name>?scope=mod` lists grant sites (it does not scan production methods, institutions or treaty articles yet, #327 / #334, so also `git grep -n '^\s*<name>\s*='`), and `git grep -n 'modifier:<name>'` lists readers. Watch for parameterized reads, such as `modifier:building_annual_$WONDER$_progress`, which a literal grep misses.

**Scope of the survey.** About 180 modifier types the mod invented, from the topical files in `common/modifier_type_definitions/`. The ~600 entries in `mod_entity_modifier_types.txt` that only register a vanilla pattern for mod content (`state_building_<b>_max_level_add`, `goods_output_<good>_add`, `country_institution_<i>_*`, …) are listed only where they matter: the engine decides their scope, not the mod.

---

## 1. How a modifier works at state level

A `state_*` type does not need state-level sources. The mask is what the engine reports from `/engine-docs/origin/<name>` as `"mask": "state"`. A **country** that holds such a modifier (a law, technology, principle, institution or a static modifier added to the country) applies it to **every state it owns** (`docs/guides/scripting_best_practices.md` § "A `state_`-Masked Key Works Inside a Modifier a COUNTRY Holds"). So moving a mod-invented mechanic from country to state level is:

1. **Register `state_X`** in place of `country_X`.
2. **Leave the national grants alone.** Laws, techs and principles keep working and now reach every state.
3. **Read `modifier:state_X` from state scope**, normally a state pulse (`on_monthly_pulse_state` / `on_yearly_pulse_state`). There ROOT is the state, which matters for any `add_modifier` multiplier (§ "`add_modifier { multiplier = var:X }` Resolves Against ROOT").
4. **Move grants that should be local.** A production method's `country_modifiers` grant must move to its `state_modifiers` block to vary by state. Decrees, and buildings' `state_modifiers`, are the usual per-state sources.

The homeland system is the working precedent. `state_homeland_*` is granted by laws, amendments, techs and principles, and read per state in `common/script_values/extra_script_values.txt` (`modifier:state_homeland_change_speed_mult`).

**Unverified:** whether a *country*-scope read of a `state_*` type (`modifier:state_X` from a country) returns the value its country modifiers contribute. Displays that sit on a country panel should read through `capital` or a chosen state until that is tested.

---

## 2. Already state-level

### 2a. Varies by state today

At least one source is a decree or a building's `state_modifiers`.

| Modifier | Per-state sources | Reader |
|---|---|---|
| `state_migration_crowding_density_mult` | 3 production methods' `state_modifiers` (plus national techs, principles, an institution) | `migration_crowding` script values (`extra_script_values.txt`) |
| `state_fortification_level_add` | production methods only | `extra_battle_conditions.txt` |
| `state_resettlement_transfer_add` | production methods only (`resettlement_pms.txt`) | resettlement transfer (`extra_effects.txt`) |
| `state_pollution_generation_mult` | 1 decree; the rest are event static modifiers | `institution_ministry_of_the_environment_pollution_generation` |
| `state_homeland_change_speed_mult` | 1 decree; the rest are laws, techs, principles | homeland script values |
| `state_war_support_monthly_add` | 1 decree, 1 law | `war_propaganda_support_script_value` |
| `state_yearly_cultural_acceptance_add` | 1 decree, plus principles and the cultural exchange treaty | `state_yearly_cultural_acceptance_add_on_action` (`extra_on_actions.txt`) |
| `state_violence_against_minorities_bool` | 1 decree, 1 law | `violent_hostility_on_action` (`extra_on_actions.txt`) |
| `state_monthly_loyalists_add` | the Consciousness Network's social-control production method (`state_modifiers`), plus the Ministry of Thought Control institution | `thought_control_loyalists_update` (`extra_effects.txt`), from `on_monthly_pulse_state`, incorporated states only |
| `state_nuclear_weapon_defense_chance_add` | the military base's Missile Defense production methods (plus national techs, the NPT guarantee, the orbital battlestation) | `nuclear_strike_success_chance` from `scope:target_state`; strike planners rank states by `nuclear_strike_target_score`; the journal entry's figure reads the capital |

### 2b. State-typed, but only national grants

These are the same in every state of a country today. **They are the cheapest per-state levers to add**: the type needs no change, only a grant site (a decree, a building's `state_modifiers`, a state event modifier).

| Modifier | Grants today |
|---|---|
| `state_homeland_creation_threshold_add` | laws, amendments, techs, principles, `base_values`, language-reform static modifiers |
| `state_homeland_removal_threshold_add` | the same set |
| `state_arable_land_mult` | techs, principles, the agricultural-diffusion modifiers (added to countries) |
| `state_min_cultural_acceptance_delta_add` | laws, principles |
| `state_war_support_monthly_add_religion` | the Sacred Civics principles. Each state pays its population share of the modifier × Devout clout (`war_propaganda_support_script_value`). |

The comments in `homelands_modifier_types.txt` say the thresholds are "modified by … decrees (per-state), buildings". No such grant exists yet.

### 2c. Vanilla patterns registered for mod content

Already state-level, with scope fixed by the engine: about 260 `state_building_<b>_max_level_add`, `state_pop_support_movement_{civil_rights,anti_war,transhumanist}_mult`, ten `state_harvest_condition_*` and seven `state_custom_religion_*_standard_of_living_add`.

---

## 3. Country-level, could move to states

Loyalists, nuclear defence and religious war support moved to state level on 2026-09-26 (#493, §2). The owner kept SoL expectations national for now, the one row left.

| Modifier(s) | Effort | Why it works | What has to change |
|---|---|---|---|
| SoL expectations: `country_sol_expectation_adaptation_rate_mult`, `country_sol_expectations_{shift,target,shift_min,shift_max}_add`, `…_{upper,middle,lower}_offset_add`, `…_offset_mult`, `…_{upper,middle,lower}_offset_mult` (12; the four `_offset_mult` types have no grants yet) | Moderate | Every input `sol_expectations_monthly_update` reads is valid at state scope (`average_sol`, `average_expected_sol`, `literacy_rate`), and the static modifiers it applies already use `state_*_strata_expected_sol_add`. | Move the update from the monthly country pulse to the monthly state pulse, with a per-state shift variable. **Cost:** three remove/add-modifier pairs per state per month, world-wide, the heaviest per-state monthly write load in the mod (pollution and tourism already use that pulse). **State lifecycle:** a state is a (region, owner) pair that can be split or merged (`scripting_best_practices.md`, "Variables can hold `state_region` scopes"), so the shift resets when a state changes hands. That's arguably right for conquered land, but choose it on purpose. The adjust / close-gap / reset helpers in `sol_expectations_effects.txt` have no callers outside that file today, so only the pulse hook (`sol_expectations_on_actions.txt`) moves. The ~180 law and tech grants keep working. **Old saves:** countries hold the three `sol_expectations_*_strata_shift` modifiers and the `sol_expectations_shift` variable. If states add the same modifiers, the country copies still reach every state and the shift counts twice, so a one-time country-pulse migration has to seed the states and remove the country copies. **Global term:** `sol_expectations_global_awareness_value` reads `global_average_sol`, which loops over every country on each read. Cache it in a global variable once a month before reading it per state. |

---

## 4. Must stay country-level

Reasons:

- **No state meaning:** a relationship between countries, or an action a country takes.
- **Single national quantity:** feeds one number per country (a journal-entry bar, a country variable, a stockpile); per state it would be N copies and an aggregation.
- **No state breakdown of the input:** the formula's input exists only at country or market level.
- **Power-bloc scope:** a `power_bloc_*` type cannot be carried by a state.
- **Engine-defined:** the mod registers a vanilla pattern; the engine fixes the scope.

| Family | Reason |
|---|---|
| Banking cycle and monetary policy (~25: intervention points, directed-credit sectors, momentum / crash / bubble / finance value, weekly investment pool, the five `country_banking_lock_*_bool`, `country_can_create_unbacked_money_bool`, credit standing, risk premium, inflation and wage pressure, anchoring, policy-rate drift and floor, standing floor, forecast error) | Single national quantity: the cycle, rates and premium are country variables; the investment pool is vanilla country-level. |
| Strategic reserve (17: eight `_capacity_add`, eight `_decay_add`, `country_st_res_weekly_rate_cap_add`) | Single national quantity: one stockpile. |
| Space race (four knobs, six `country_sr_*_program_bool`) | Single national quantity: one journal entry and bar. |
| Nuclear program (aid, disarmament, pause flags; progress mult; attack success) | Single national quantity: a national programme and delivery capability. Defence chance is state-level (§2b). |
| Colonial stability (`country_colonial_stability_drift_add`, three `_effectiveness_add`) | Single national quantity: all four feed one bar, and the garrison / investment / assimilation policies are country-wide toggles. Per-colony stability would be a redesign. |
| Covert warfare (intelligence capacity add and mult, operation efficiency, operation slots, three `country_covert_defense_*_add`) | Single national quantity: capacity is a national pool built from national literacy and GDP. Operations target a country and pick a random state only after they succeed; defence could move only if operations targeted a chosen state. |
| Cultural hegemony (pull add and mult, art mult, programme funding, `country_ideology_resistance_mult`) | No state meaning: pull runs between countries, and the art input is `country_fine_art_production`. (`country_ideology_resistance_mult` scales the foreign benchmark from #489 on.) |
| `country_greenhouse_gas_emissions_mult` | National industrial policy: `gw_emission_multiplier_script_value` reads the state owner country's modifier and scales only its states' net building emissions. Household cuts follow the state owner, source capture follows the building, and `state_pollution_generation_mult` remains a separate channel. |
| `country_solar_receiver_max_level_add`, `country_antimatter_facility_max_level_add` | Single national quantity, by design: a national slot pool (collector levels anywhere feed receivers anywhere). Per-state caps exist as `state_building_<b>_max_level_add`. |
| Diplomatic-play escalation (6), subjugation strength (7), UN (`country_un_membership_obligation_bool`, `country_un_institutional_alignment`), `country_leverage_threshold_change_add`, `country_economic_dependence_leverage_gain_mult` | No state meaning. |
| `country_legislative_override_capacity_add`, `country_combined_arms_bonus_enabled_bool`, `country_can_use_biotech_companies_bool` | No state meaning (politics, army formations, companies). |
| Technology gates: 44 `country_*_pb_principles_bool`, nine `country_can_use_*_bool`, `country_can_join_united_nations_bool`, the decolonization and civil-rights markers (read by `tech_marker_grants_on_action` from #489 on) | No state meaning: they gate country buttons, principles and one-shot grants. |
| `power_bloc_*` (21 once #489 drops `power_bloc_principle_groups_max_add`) | Power-bloc scope. |
| `country_institution_<i>_*`, `country_enactment_success_chance_law_*`, `country_can_impose_same_lawgroup_*`, `country_building_<b>_require_subsidies_bool`, `country_ship_type_*_construction_efficiency_add`, the `country_loan_interest_rate_add` REPLACE | Engine-defined. |

Building-scope types (`building_annual_*_progress`, read by `generic_wonder_construction_base`; the `building_total_*_progress` display mirrors of the wonder progress variable) are outside this survey.
