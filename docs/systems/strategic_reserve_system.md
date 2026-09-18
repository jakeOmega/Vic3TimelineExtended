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
| [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt) | Init, reset, hub-cache refresh, hub-flow rebuild, weekly bookkeeping, signed-rate controls, status derivation |
| [common/scripted_triggers/st_res_triggers.txt](../common/scripted_triggers/st_res_triggers.txt) | `st_res_<good>_unlocked_trigger` — the single source of truth for per-good availability |
| [common/scripted_guis/st_res_scripted_gui.txt](../common/scripted_guis/st_res_scripted_gui.txt) | `st_res_adjust_<good>_sgui` — thin per-good validation wrappers for the widget's row controls |
| [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) | The two shared, reserve-wide buttons: step size and reset-all |
| [common/journal_entries/je_strategic_reserve.txt](../common/journal_entries/je_strategic_reserve.txt) | Summary text, shared buttons, widget wiring and weekly pulse owner |
| [gui/journal_entry_widgets/strategic_reserve_widget.gui](../gui/journal_entry_widgets/strategic_reserve_widget.gui) | The reserve inventory table — one row per unlocked good |
| [common/customizable_localization/st_res_custom_loc.txt](../common/customizable_localization/st_res_custom_loc.txt) | `st_res_<good>_mode_text` / `st_res_<good>_reason_text`, both driven by the bookkeeping status code |
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
| `st_res_<good>_last_delta` | **Display only.** The ACTUAL net movement the last weekly tick applied, measured after the `[0, capacity]` clamp — not recomputed from rates. Written by `st_res_apply_weekly_good_effect`, read through the guarded `st_res_<good>_last_net` script value. |
| `st_res_<good>_last_status` | **Display only.** The status/reason code the inventory widget renders. Written by `st_res_set_good_status_effect`. |

#### Status codes (`st_res_<good>_last_status`)

| Code | Widget label | Meaning |
|---|---|---|
| 0 | Idle | Nothing configured, nothing moving |
| 1 | Storing | Configured intake applied in full |
| 2 | Withdrawing | Configured release applied in full |
| 3 | Storing | Clipped by the hub's weekly flow cap |
| 4 | Withdrawing | Clipped by the hub's weekly flow cap |
| 5 | Blocked | Stockpile at capacity |
| 6 | Blocked | Stockpile empty with a release configured |
| 7 | Blocked | Hub understaffed (occupancy below 100%) |
| 8 | Blocked | No Strategic Reserve Hub |

`st_res_set_good_status_effect` is the **only** place this is derived. It is called from `st_res_refresh_hub_flow_effect`, which is the shared tail of both the weekly pulse and every rate/step button press, so the label reacts to a click immediately instead of lagging a week. `st_res_<good>_mode_text` and `st_res_<good>_reason_text` (customizable localization) map the code to the label and the one-sentence explanation; the GUI never re-derives either.

Both variables are **save-safe**: absent on a save made before the widget existed, `st_res_init_good_effect` seeds them with 0 (no movement / Idle), and the first weekly tick overwrites them with real data.

Two precedence details worth knowing, both consequences of `st_res_clamp_stockpiles_effect` driving the configured rate to 0 once a stockpile hits a bound:
- **Full** accepts `rate >= 0`, not `rate > 0`. Otherwise a full reserve would report *Idle* the tick after the auto-clamp fires.
- **Empty** deliberately keeps `rate < 0`. A stockpile that is empty *and* unconfigured is genuinely idle; the row tooltip still says it is empty.

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

`je_strategic_reserve` (group: `je_group_internal_affairs`) is the sole UI surface. Per-good presentation and control lives in the **reserve inventory widget**, [gui/journal_entry_widgets/strategic_reserve_widget.gui](../gui/journal_entry_widgets/strategic_reserve_widget.gui), mounted in `custom_widget_container_2` (directly under the summary text, above the shared buttons).

- **Activation:** `possible` = the country has a hub built. `is_shown_when_inactive` requires `logistics`. The widget root is gated on `[JournalEntry.IsActive]` so it does not render — and does not read reserve variables — for a country that has never built a hub.
- **Summary text (`status_desc`):** hub status (no hub / deactivated / active), weekly sales income, and the hub flow cap. Deliberately short, because `status_desc` also renders in the journal *list*, where one block per good was unreadable.
- **Inventory rows:** one per unlocked good — `@good!` icon and name, `stored / capacity`, a fill bar driven by `st_res_<good>_fill_pct`, the configured signed rate, the actual net weekly movement (`st_res_<good>_last_net`), a Storing / Withdrawing / Idle / Blocked label, and decrease / stop / increase controls. The row tooltip breaks down stock, rate setting, active rate, net movement, weekly decay, hub flow cap and hub staffing, then states the reason movement differs from the setting.
- **Row visibility** is `ScriptedGui.IsShown`, delegating to `st_res_<good>_unlocked_trigger` — the unlock conditions are never duplicated in a GUI expression.
- **Row controls** call `st_res_adjust_<good>_sgui` with the action in a `dir` saved scope (`0` decrease, `1` stop, `2` increase). Each branch delegates to the existing `st_res_{increase,decrease,stop}_<good>_rate_effect` helpers, so the rate rules live in script, not in GUI. "Stop" zeroes only that good's rate.
- **Shared buttons (vanilla-rendered JE buttons):** `st_res_cycle_step_size_button` cycles the adjustment size through 1, 10, 100, 1000, 10000; `st_res_reset_rates_button` zeroes every good's rate. The current step is shown once, in the widget header.
- **`invalid`:** JE ends if the hub is destroyed.
- **`on_invalid`:** `st_res_reset_vars_effect` zeros all live vars and hub caches, so a rebuilt hub starts clean.

> The journal entry binds `scripted_progress_bar` and `scripted_button` declarations at **activation** time. A save whose SR journal entry is already running may still show the pre-widget bars/buttons until the hub is demolished and rebuilt.

---

## 6. Lifecycle Wiring

Weekly bookkeeping now lives on the JE itself: `je_strategic_reserve` calls `st_res_je_weekly_pulse_effect` from `on_weekly_pulse`, and `st_res_je_immediate_effect` / `st_res_je_invalid_effect` own activation and teardown. There is no separate SR on-action file in the current implementation.

Button presses call country-scoped wrapper effects in [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt). Those wrappers mutate the signed-rate or step-size vars, then immediately call the shared refresh helpers so the hub reflects the change without waiting for the next weekly tick.

---

## 7. AI

The Strategic Reserve is **player-only, and always has been**. Every button in [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) carries `ai_chance = { value = 0 }`, and no on-action, event or decision drives reserve rates — `grep -rn "st_res" common/on_actions/ events/` returns nothing. The AI therefore never touched these controls.

That is why moving the per-good controls out of the journal entry and into the inventory widget's scripted GUIs was safe: there was no AI path to preserve. The scripted GUIs are explicitly `ai_is_valid = { always = no }`, matching the previous behaviour rather than opening a new one.

If AI reserve management is ever wanted, the entry points are the shared effects (`st_res_increase_<good>_rate_effect` and friends) called from an on-action — not the scripted GUIs, which exist only to validate player clicks.

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

**The authoritative, file-by-file procedure is the `add-strategic-reserve-good` skill** (`.claude/skills/add-strategic-reserve-good/SKILL.md`, with verbatim snippets in `references/per_good_templates.md`). Follow it rather than this section — it is kept in sync with the implementation, including the vanilla mult-axis registration gap that silently breaks a new good.

What the inventory widget added to that procedure, in short: a good now also needs an entry in `st_res_triggers.txt` (its unlock trigger), an `st_res_adjust_<good>_sgui` in `st_res_scripted_gui.txt`, `st_res_<good>_mode_text` **and** `st_res_<good>_reason_text` custom loc, an `st_res_<good>_last_net` script value, a `st_res_stop_<good>_rate_effect` wrapper, one call each added to the per-good lists in `st_res_init_effect` / `st_res_reset_vars_effect` / `st_res_weekly_update_effect` / `st_res_refresh_hub_flow_effect`, and one row instance plus its five loc keys in the widget. It no longer needs a scripted progress bar, a pair of scripted buttons or a journal-entry status line.

---

## 10. Known Limitations / Future Work

- The hub has no animated icon or dedicated art.
- The SR scripted-effects slice is now `$GOOD$`-parameterized for init, reset, the hub flow rebuild, the weekly apply and the status derivation. The remaining per-good repetition is in [common/script_values/st_res_script_values.txt](../common/script_values/st_res_script_values.txt), [common/scripted_guis/st_res_scripted_gui.txt](../common/scripted_guis/st_res_scripted_gui.txt) and [common/customizable_localization/st_res_custom_loc.txt](../common/customizable_localization/st_res_custom_loc.txt) — none of those file types accept `$GOOD$` parameters, so the repetition is structural rather than a cleanup candidate.
- No event flavor — a short event chain could celebrate reaching capacity or warn of shortages.
- Decay only has single-tech reductions; a second tier (e.g. `vitalism` or `combustion_engine` / later aerospace refining) could halve decay again.
- Silo has no distinctive icon — reuses the government-admin icon.