# Standard of Living Expectations

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## SoL Expectations System

**Purpose:** Adds adaptive standard of living expectations that create inertia around SoL changes. When SoL rises suddenly, people's expectations lag behind (contentment bonus). When SoL drops, expectations stay high for a while (dissatisfaction penalty). Expectations converge toward a target (actual SoL + permanent offsets) with a 10-year half-life.

**Mechanic:**
- Country variable `var:sol_expectations_shift` tracks the adaptive shift; `sol_expectations_monthly_update` runs from `on_monthly_pulse_country`.
- Monthly: `gap = (average_sol + target_add) - average_expected_sol` (cached in `var:sol_expectations_gap_cached` before anything is removed), then `shift += gap × rate + country_sol_expectations_shift_add`.
- Rate derived from half-life: `rate = ln(2) / (half_life_years × 12)`, scaled by `1 + country_sol_expectation_adaptation_rate_mult` and clamped to [0.001, 0.1] (default 10y → ~0.00578/month).
- **Clamp:** the shift is then clamped to [floor, ceiling]. The floor is 0 plus `country_sol_expectations_shift_min_add`, so by default the shift never goes negative: the adaptive shift can only raise expectations above vanilla's, and falling SoL lets it decay back toward 0, not below. Welfare laws raise the floor (`law_poor_laws` +1, `law_wage_subsidies` +2, `law_old_age_pension` +3, `law_universal_basic_income` +10, `law_post-scarcity` +15), so expectations can't adapt all the way down to hardship. The ceiling is 50 plus `country_sol_expectations_shift_max_add` (negative values, mostly from events, lower it).
- **Per-strata application:** three static modifiers, `sol_expectations_upper_strata_shift`, `sol_expectations_middle_strata_shift` and `sol_expectations_lower_strata_shift` (each +1 `state_<strata>_strata_expected_sol_add`), are re-applied every month. Each one's multiplier is `sol_expectations_<strata>_shift_value`: `(clamped shift × (1 + country_sol_expectations_offset_mult) + country_sol_expectations_<strata>_offset_add) × (1 + country_sol_expectations_<strata>_offset_mult) + global awareness`. A modifier is only applied when its multiplier is outside ±0.1 (avoids modifier clutter in steady state).
- **Global awareness:** `sol_expectations_global_awareness_value = (global_average_sol − average_sol) × literacy_rate × 0.2`, added to all three strata. Literate populations expect more when the world is richer than they are and less when it is poorer. `global_average_sol` is the population-weighted world mean from `cultural_hegemony_script_values.txt`.
- At equilibrium, while the shift is inside [floor, ceiling]: `average_expected_sol ≈ average_sol + target_add`. Because the gap reads `average_expected_sol` with the strata offsets and the awareness term already applied, the adaptive shift works back against their effect on the national average over time; what persists is the difference between classes. When the floor binds, expected SoL sits above the target.

**Target offset:** `country_sol_expectations_target_add` (script_only) — offsets the convergence target above/below actual SoL. Techs, laws, IG traits, and power bloc principles use this to represent permanent changes in societal expectations. Example: the egalitarianism tech adds `country_sol_expectations_target_add = 0.5`, meaning a society with that tech expects half a point above its actual average SoL.

**Per-strata offsets:** `country_sol_expectations_upper/middle/lower_offset_add` model class-relative comparison (aristocratic vs egalitarian societies): restrictive franchises (autocracy, landed, wealth and census voting) raise the upper-strata offset, universal suffrage and labour-rights laws the lower one; corporate and investment-banking techs raise the upper one, and egalitarianism lowers the middle one. Many event modifiers carry small offsets or ceiling cuts too (`event_modifiers.txt`).

**Vanilla modifier conversion:** All vanilla `state_expected_sol_from_literacy`, `state_expected_sol_mult`, and per-strata `state_*_strata_expected_sol_add` modifiers from techs, laws, and IG traits have been replaced with `country_sol_expectations_target_add` using `INJECT:` directives that cancel the original values with inverse modifiers and add the new target offset. Injection files:
- `common/technology/technologies/sol_expectations_vanilla_injections.txt` — egalitarianism, labor_movement, socialism, political_agitation, mass_propaganda (plus per-strata offsets on investment_banks, corporate_management and others)
- `common/laws/sol_expectations_vanilla_injections.txt` — law_industry_banned, law_women_in_the_fields, the voting and labour-rights offsets, and the welfare floors above
- `common/interest_group_traits/sol_expectations_vanilla_injections.txt` — ig_trait_biedermanner

**NOT converted** (intentionally): Engine-hardcoded code static modifiers (base_values, tax_modifier_*, unincorporated_state) and temporary DLC/event modifiers (expecting_riches_forever, etc.) — these are either unchangeable or correctly handled by the adaptive lag.

**Tuning:**
- `sol_expectations_half_life_years = 10` — script value controlling convergence speed. Change this single value to tune. 10y = ~50% adapted after 10y, ~75% after 20y, ~94% after 40y.

**Modifiers** (`sol_expectations_modifier_types.txt`, all script_only):
- `country_sol_expectation_adaptation_rate_mult` (percent) — scales the adaptation rate. +100% = twice as fast (5-year half-life).
- `country_sol_expectations_shift_add` (decimals=2) — persistent monthly bias added to shift. Positive = expectations rise faster.
- `country_sol_expectations_target_add` (decimals=1) — permanent offset to the convergence target. Positive = people expect more than actual SoL.
- `country_sol_expectations_shift_min_add` / `_shift_max_add` (decimals=1) — raise the floor (default 0) / lower the ceiling (default 50) of the shift.
- `country_sol_expectations_upper/middle/lower_offset_add` (decimals=1) — direct per-strata offsets, not adaptive.
- `country_sol_expectations_offset_mult` (percent) — scales the clamped shift for all three strata before the offsets; `country_sol_expectations_upper/middle/lower_offset_mult` (percent) — scales one stratum's total.

**Utility scripted effects** (in `sol_expectations_effects.txt`):
- `sol_expectations_instant_adjust = { AMOUNT = X }` — instantly add X to the shift
- `sol_expectations_close_gap = { FRACTION = X }` — close X fraction of the remaining gap (0.5 = half, 1.0 = full)
- `sol_expectations_reset = yes` — fully reset expectations to match current target
- `sol_expectations_reapply_modifier = yes` — internal: clamp the shift and re-apply the three strata modifiers (`sol_expectations_apply_strata_shifts`)

All four clamp the shift before re-applying, so an adjustment can't push it past the floor or ceiling.

**Script values** (in `extra_script_values.txt`):
- `sol_expectations_half_life_years` — half-life parameter in years (default 10)
- `sol_expectations_adaptation_rate_value` — derived monthly rate, scaled by modifier, clamped [0.001, 0.1]
- `sol_expectations_gap_value` — (average_sol + target_add) - average_expected_sol
- `sol_expectations_shift_clamped_value` — the shift variable clamped to [floor, ceiling]
- `sol_expectations_global_awareness_value` — the literacy-scaled world comparison
- `sol_expectations_upper_shift_value` / `_middle_shift_value` / `_lower_shift_value` — each stratum's modifier multiplier

**Files:**
- Scripted Effect: `common/scripted_effects/sol_expectations_effects.txt` (`sol_expectations_monthly_update` + utilities)
- On_action: `common/on_actions/sol_expectations_on_actions.txt`
- Static Modifiers: `common/static_modifiers/sol_expectations_modifiers.txt` (the three strata modifiers)
- Modifier Types: `common/modifier_type_definitions/sol_expectations_modifier_types.txt`
- Script Values: `common/script_values/extra_script_values.txt` (search `sol_expectations`)
- Vanilla Injections: `sol_expectations_vanilla_injections.txt` in `technologies/`, `laws/`, `interest_group_traits/`
- Loc: `localization/english/te_modifiers_l_english.yml`

### Interaction with vanilla loyalist/radical generation

> Cross-reference: `docs/vanilla/vanilla_economy_reference.md` § 5.6.

Vanilla generates loyalists when a pop's SoL **rises** and radicals when it **falls** — the channel is the *delta*, not the *level*. The SoL Expectations System above hooks the *expected SoL* side of that channel (delaying when the delta registers) but does **not** replace the delta-driven loyalist/radical flow itself. That continues to run autonomously inside the engine for every pop in every state.

What this means for mod authors:

- When the banking cycle drops country-wide SoL through a panic phase, vanilla automatically converts that into radicals over the following months. Mod systems don't need to call `add_radicals` to model "the bust radicalized people" — the engine is already doing it.
- Conversely, when global-warming pollution pushes SoL down in a polluted state, vanilla autoaments the radical fraction without any explicit hook. Mod-side `add_radicals` calls in events should reflect *additional* sources beyond the SoL channel (e.g. movement supporters losing a key vote, a discriminated minority hit by a specific event).
- The autonomous channel is *generational-decay slow* — loyalists and radicals turn over with the country's death rate, not on a feedback timescale. Sharp short-term shocks register quickly; the country's long-run political alignment shifts slowly.
- High legitimacy (a separate mechanic) generates loyalists too. Mods that flip legitimacy via events get loyalist generation as a side effect.

The risk to be aware of: if a mod system *also* adds loyalists/radicals tied to economic state (e.g. on an event where SoL crashed), it can double-count vanilla's autonomous response. Prefer to model unique additional triggers (a riot, a discriminatory incident, a political win) and let vanilla handle the SoL-delta side.

---
