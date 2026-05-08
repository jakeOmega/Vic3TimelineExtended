# Strategic Reserve System (SRS)

A national stockpile system that lets countries physically hoard **grain**, **ammunition**, and **oil**. Storing/withdrawing interacts directly with the market through transient hub-building modifiers, so reserve operations shift prices. The player controls a **signed weekly rate** per good plus one shared **step size**: positive rates store goods, negative rates withdraw goods, and stockpiles decay continuously.

This document describes the **current implementation**. See §8 for deviations from the original AI-drafted spec.

---

## 1. Components

| File | Purpose |
|---|---|
| [common/buildings/strategic_reserve.txt](../common/buildings/strategic_reserve.txt) | `building_strategic_reserve_hub` (active) + `building_strategic_reserve_silo` (passive capacity) |
| [common/production_methods/strategic_reserve_pms.txt](../common/production_methods/strategic_reserve_pms.txt) | Per-good idle/store/withdraw PMs + silo capacity PM |
| [common/modifier_type_definitions/st_res_modifier_types.txt](../common/modifier_type_definitions/st_res_modifier_types.txt) | `country_sr_<good>_capacity_add`, `country_sr_<good>_decay_add`, `building_strategic_reserve_hub_throughput_add` |
| [common/static_modifiers/extra_modifiers.txt](../common/static_modifiers/extra_modifiers.txt) | `INJECT:base_values` (decay bases) + `sr_rate_slow` / `sr_rate_fast` static modifiers |
| [common/script_values/st_res_script_values.txt](../common/script_values/st_res_script_values.txt) | Hub level, throughput factor, signed rate cap, weekly deltas, capacity, fill-% |
| [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt) | Init, reset, hub-cache refresh, hub-flow rebuild, weekly bookkeeping, signed-rate controls |
| [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) | Shared step-size button + six per-good increase/decrease rate buttons |
| [common/journal_entries/je_strategic_reserve.txt](../common/journal_entries/je_strategic_reserve.txt) | Player-facing control panel and weekly pulse owner |
| [common/customizable_localization/st_res_custom_loc.txt](../common/customizable_localization/st_res_custom_loc.txt) | Derived mode labels based on signed rates and stockpile bounds |
| [common/technology/technologies/modified.txt](../common/technology/technologies/modified.txt) | `INJECT:` decay reductions for `vacuum_canning`, `bolt_action_rifles`, `fractional_distillation` |
| [localization/english/te_strategic_reserve_l_english.yml](../localization/english/te_strategic_reserve_l_english.yml) | All user-visible strings |

---

## 2. Buildings

### Hub — `building_strategic_reserve_hub`

Capital-only (`possible = { is_capital = yes }`), self-owned, scalable (`has_max_level = yes`), unlocked by `logistics`. Construction cost is `construction_cost_very_high`. Each level provides, per reserve good:

- **+500 capacity** via `country_sr_<good>_capacity_add` (applied in `country_modifiers` → `level_scaled` on every PM of that good's PMG so capacity is mode-independent).
- **10 goods/week of nominal throughput** when storing or withdrawing, applied via `building_modifiers` → `level_scaled` on the active store/withdraw PM. Scaled at runtime by the hub's total throughput multiplier (see §4.3).

### Silo — `building_strategic_reserve_silo`

Passive capacity-only building, buildable in any state, self-owned, expandable, unlocked by `logistics`. Construction cost is `construction_cost_high`. Each level adds **+200 capacity per reserve good** via the single PM `pm_sr_silo_capacity`. Useless without a hub (no mode control), but required for large empires that outgrow the hub's base capacity.

Both buildings use `bg_government`.

---

## 3. Production Methods

### Hub PMs

For each good `X ∈ {grain, ammunition, oil}`, `pmg_sr_X` defines three PMs:

| PM | Capacity (country) | Market interaction (building) |
|---|---|---|
| `pm_sr_X_idle` | `country_sr_X_capacity_add = 500` | none |
| `pm_sr_X_store` | `country_sr_X_capacity_add = 500` | `goods_input_X_add = 10` |
| `pm_sr_X_withdraw` | `country_sr_X_capacity_add = 500` | `goods_output_X_add = 10` |

All values are `level_scaled`. `pmg_sr_ammunition` has `unlocking_technologies = nitroglycerin`; `pmg_sr_oil` requires `oil_rig`. Both are `is_hidden_when_unavailable = yes`.

### Silo PM

`pm_sr_silo_capacity` adds +200 to all three capacity modifiers at `level_scaled`. A level-5 silo therefore adds +1000 capacity per good.

---

## 4. Stockpile Bookkeeping

### 4.1 Country variables

| Variable | Meaning |
|---|---|
| `sr_<good>_stored` | Current amount held (float) |
| `sr_<good>_rate` | Signed configured weekly rate. Positive stores goods; negative withdraws goods. |
| `st_res_adjust_step_tier` | Shared step-size tier: 0 = 1, 1 = 10, 2 = 100, 3 = 1000, 4 = 10000 |
| `st_res_hub_level_cached` | Live hub level cached from building scope |
| `st_res_hub_throughput_cached` | Live hub `modifier:building_throughput_add` cached from building scope |

`st_res_init_effect` defaults stored amounts and signed rates to 0, `st_res_adjust_step_tier` to 1, and the hub caches to 0. `st_res_reset_vars_effect` zeros the same live vars when the JE goes invalid. Display-mode text is derived on demand in [common/customizable_localization/st_res_custom_loc.txt](../common/customizable_localization/st_res_custom_loc.txt), so the live system no longer keeps persistent `sr_<good>_mode` variables.

### 4.2 Weekly update

`st_res_weekly_update_effect` runs from the JE's `on_weekly_pulse`. For each good it:

1. Adds `sr_<good>_weekly_delta`.
2. Clamps to `[0, sr_<good>_capacity]`.
3. Rebuilds the hub's transient flow modifiers so market input/output stays aligned with the stored country vars.

For each good, the weekly delta is:

$$
\Delta_w = \text{flow}_w - \frac{d \cdot S}{4.333}
$$

where
- $d$ = `modifier:country_sr_<good>_decay_add` (monthly decay rate, clamped to $[0,1]$),
- $S$ = current stored amount,
- `flow_w` is zero unless the configured rate points toward a legal action (store while below capacity, withdraw while above zero).

When flow is active, the script values compute it as:

$$
	ext{flow}_w = \min(|r|,\; C) \cdot F
$$

where
- $r$ = `var:sr_<good>_rate` (signed configured weekly rate),
- $C$ = `st_res_weekly_base_rate_cap`,
- $F$ = `st_res_throughput_factor = \max(0.1,\; 1 + \texttt{modifier:building\_throughput\_add})` read from the live hub.

These pieces are split across the per-good script values `sr_<good>_rate_abs`, `sr_<good>_rate_base_applied`, `sr_<good>_effective_rate`, `sr_<good>_weekly_decay`, and `sr_<good>_weekly_delta`.

### 4.3 Shared step size and throughput correction

The JE exposes one shared step-size selector rather than separate mode or tier buttons. `st_res_cycle_step_size_effect` cycles `var:st_res_adjust_step_tier` through these values:

| Tier | Step size |
|---|---|
| 0 | 1 |
| 1 | 10 |
| 2 | 100 |
| 3 | 1000 |
| 4 | 10000 |

Each per-good increase/decrease button adds or subtracts `st_res_adjust_step_value` from that good's signed rate, then immediately refreshes hub flow and clamps stockpiles.

The throughput correction still uses the hub-scope read: `st_res_refresh_hub_cache_effect` bridges the hub's current `modifier:building_throughput_add` into country scope, and `st_res_throughput_factor` multiplies the active base flow so script-side bookkeeping matches the market-facing hub modifiers.

### 4.4 Decay rates (modifier-driven)

Decay rates are **custom country modifier types** (`country_sr_<good>_decay_add`) registered in `sr_modifier_types.txt`. Base values live in `INJECT:base_values` in `extra_modifiers.txt`, so every country has them by default. Techs contribute via `INJECT:<tech>` in `common/technology/technologies/modified.txt`.

| Good | Base (per month) | Tech reduction | Post-tech rate |
|---|---|---|---|
| Grain | 2.0% | `vacuum_canning` → -1.0% | 1.0% |
| Ammunition | 0.2% | `bolt_action_rifles` → -0.1% | 0.1% |
| Oil | 0.5% | `fractional_distillation` → -0.25% | 0.25% |

The weekly decay values divide the monthly rate by `sr_weeks_per_month = 4.333`, and the JE status line can still use `GetValueWithBreakdownFor` so the player sees a hoverable breakdown of every source.

Decay is clamped to `[0, 1]` in the script values, so further tech reductions cannot push it negative.

### 4.5 Hub-flow safeguards

`st_res_rebuild_hub_flow_modifiers_effect` is the bridge from country-owned reserve vars back into the hub building. It computes `sr_<good>_can_store_local` and `sr_<good>_can_withdraw_local` for each good, hops once into the hub's building scope, removes any previous SR flow modifiers for that good, and re-applies the correct combination of:

- `sr_<good>_store_flow`
- `sr_<good>_withdraw_flow`
- `sr_<good>_disable_input_flow`
- `sr_<good>_disable_output_flow`

The building-scoped per-good work is now routed through three explicit wrappers:

- `st_res_rebuild_grain_flow_modifiers_effect`
- `st_res_rebuild_ammunition_flow_modifiers_effect`
- `st_res_rebuild_oil_flow_modifiers_effect`

Each wrapper delegates to the shared helper `st_res_rebuild_good_flow_modifiers_effect = { GOOD = <good> }`, which keeps the concrete good names grep-able while removing the repeated in-building logic.

If a stockpile is full, empty, or configured with no legal effective flow, the disable modifiers keep the hub from consuming or producing that good even when the configured signed rate remains nonzero. This is the live replacement for the old auto-idle pattern: the rate variable stays as configured, but the building-side market flow shuts off whenever stockpile bounds require it.

---

## 5. Journal Entry — Control Panel

`je_strategic_reserve` (group: `je_group_internal_affairs`) is the sole UI surface:

- **Activation:** `possible` = the country has a hub built. `is_shown_when_inactive` requires `logistics`.
- **Status text:** A rate-cap/throughput line, a step-size line, and one line per visible good showing `stored / capacity`, the derived mode label, the configured signed rate, and decay.
- **Step-size button:** `st_res_cycle_step_size_button` cycles the shared adjustment size through 1, 10, 100, 1000, and 10000.
- **Rate buttons:** Each good has its own increase/decrease pair. Grain is always visible; ammunition and oil buttons are gated by `bolt_action_rifles` and `fractional_distillation` respectively.
- **`invalid`:** JE ends if the hub is destroyed.
- **`on_invalid`:** `st_res_reset_vars_effect` zeros all live vars and hub caches, so a rebuilt hub starts clean.

---

## 6. Lifecycle Wiring

Weekly bookkeeping now lives on the JE itself: `je_strategic_reserve` calls `st_res_je_weekly_pulse_effect` from `on_weekly_pulse`, and `st_res_je_immediate_effect` / `st_res_je_invalid_effect` own activation and teardown. There is no separate SR on-action file in the current implementation.

Button presses call country-scoped wrapper effects in [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt). Those wrappers mutate the signed-rate or step-size vars, then immediately call the shared refresh helpers so the hub reflects the change without waiting for the next weekly tick.

---

## 7. AI

The scripted control buttons are currently player-only. All buttons in [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) use `ai_chance = { value = 0 }`, so AI countries do not currently micromanage signed reserve rates or step size through the JE.

---

## 8. Deviations from the Original Spec

| Original spec | Implemented | Why |
|---|---|---|
| Hub + Satellite Depots with complex per-depot logic | Hub (active) + Silo (passive capacity) | Clean separation: hub controls modes + provides base capacity, silo scales capacity up |
| Mode cycling + separate speed tier | Signed per-good weekly rates + one shared step-size selector | Fewer live vars and more direct control over the target reserve flow |
| Weekly pulse | Weekly pulse on the JE itself | Keeps bookkeeping close to the JE lifecycle and the signed-rate controls |
| Flat throughput compensation multiplier | `st_res_throughput_factor` reads `modifier:building_throughput_add` from the hub | Same intent, but the hub-scope read automatically accounts for every contributing source |
| Fixed hard-coded decay rates | Custom modifier types + `INJECT:base_values` + tech INJECTs | Modders, techs, events, and laws can all alter decay now |
| `single_level = yes` | `possible = { is_capital = yes }` + `has_max_level = yes` | `single_level` isn't a real field; capital-only achieves one-per-country |
| Modifier `country_[good]_storage_max_add` | `country_sr_<good>_capacity_add` | The `sr_` prefix avoids colliding with any vanilla modifier name |
| Read `scope:sr_decay_amount` from loc | `GetVariable` / `GetModifier.GetValueWithBreakdownFor` / `custom_localization` | Temporary saved scopes don't persist into `status_desc`; only persistent variables and modifiers work for UI display |

---

## 9. Extending with a New Good

To add e.g. `rubber`:

1. **Modifier types:** add `country_st_res_rubber_capacity_add` and `country_st_res_rubber_decay_add` to `sr_modifier_types.txt`.
2. **Base decay:** add `country_st_res_rubber_decay_add = <rate>` to `INJECT:base_values` in `extra_modifiers.txt`.
3. **PMs:** add `pm_sr_rubber_idle/store/withdraw` and `pmg_sr_rubber` to `strategic_reserve_pms.txt`. Add the PMG to the hub's `production_method_groups`. Extend `pm_sr_silo_capacity` with rubber capacity.
4. **Script values:** add `st_res_rubber_decay_rate`, `st_res_rubber_weekly_decay`, `st_res_rubber_rate_abs`, `st_res_rubber_rate_base_applied`, `st_res_rubber_effective_rate`, `st_res_rubber_weekly_delta`, `st_res_rubber_capacity`, and `st_res_rubber_fill_pct`.
5. **Effects:** extend `st_res_init_effect`, `st_res_reset_vars_effect`, the shared-local setup in `st_res_rebuild_hub_flow_modifiers_effect`, `st_res_clamp_stockpiles_effect`, and `st_res_weekly_update_effect`. Add `sr_rebuild_rubber_flow_modifiers_effect = { st_res_rebuild_good_flow_modifiers_effect = { GOOD = rubber } }`, then call it from the hub rebuild orchestrator. Also add `sr_increase_rubber_rate_effect` and `sr_decrease_rubber_rate_effect`.
6. **Buttons:** add `sr_increase_rubber_rate_button` and `sr_decrease_rubber_rate_button` to `sr_buttons.txt` and reference them from the JE.
7. **Custom loc:** add `st_res_rubber_mode_text` to `sr_custom_loc.txt`.
8. **Tech (optional):** add an `INJECT:<tech>` reducing `country_st_res_rubber_decay_add`.
9. **YAML:** add loc keys (PMs, PMG, modifiers, status line, button name/desc).

---

## 10. Known Limitations / Future Work

- The hub has no animated icon or dedicated art.
- The SR scripted-effects slice now uses `$GOOD$` parameterization for the hub flow rebuild, but the remaining per-good repetition in [common/script_values/st_res_script_values.txt](../common/script_values/st_res_script_values.txt) and [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) is still a future cleanup candidate.
- No event flavor — a short event chain could celebrate reaching capacity or warn of shortages.
- Decay only has single-tech reductions; a second tier (e.g. `vitalism` or `combustion_engine` / later aerospace refining) could halve decay again.
- Silo has no distinctive icon — reuses the government-admin icon.