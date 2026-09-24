# Strategic Reserve System (SRS)

A national stockpile system that lets countries physically hoard eight goods: **grain**, **ammunition**, **oil**, **small arms**, **artillery**, **aeroplanes**, **tanks** and **chemicals** (script ID `fertilizer`; the mod renames the vanilla good to Chemicals in `localization/english/replace/timeline_extended_override_l_english.yml`, so every player-facing string says *Chemicals* while every script name says `fertilizer`). Storing/withdrawing interacts directly with the market through transient hub-building modifiers, so reserve operations shift prices. The player controls a **signed weekly rate** per good plus one shared **step size**: positive rates store goods, negative rates withdraw goods, and stockpiles decay continuously. Each good can instead be put on a **price-triggered policy** that re-decides its rate every week from a running average of the market price, with either a step or a linear response (§4.6).

This document describes the **current implementation**. See §8 for deviations from the original AI-drafted spec.

---

## 1. Components

| File | Purpose |
|---|---|
| [common/buildings/strategic_reserve.txt](../../common/buildings/strategic_reserve.txt) | `building_strategic_reserve_hub` (active) + `building_strategic_reserve_silo` (passive capacity) |
| [common/production_method_groups/strategic_reserve_pmgs.txt](../../common/production_method_groups/strategic_reserve_pmgs.txt) | `pmg_st_res_hub` + `pmg_st_res_silo_capacity`, one PM each |
| [common/production_methods/strategic_reserve_pms.txt](../../common/production_methods/strategic_reserve_pms.txt) | `pm_st_res_hub_reserve` (per-good capacity + the load-bearing base 1-unit goods I/O) and `pm_st_res_silo_capacity` |
| [common/modifier_type_definitions/st_res_modifier_types.txt](../../common/modifier_type_definitions/st_res_modifier_types.txt) | `country_st_res_<good>_capacity_add`, `country_st_res_<good>_decay_add`, `country_st_res_weekly_rate_cap_add` |
| [common/modifier_type_definitions/mod_entity_modifier_types.txt](../../common/modifier_type_definitions/mod_entity_modifier_types.txt) | The `goods_input_<good>_mult` / `goods_output_<good>_mult` axes vanilla leaves unregistered: `grain` (both), `aeroplanes` (input), `fertilizer` (both). Without them a hub-flow modifier silently no-ops |
| [common/static_modifiers/extra_modifiers.txt](../../common/static_modifiers/extra_modifiers.txt) | `INJECT:base_values` (base decay rates) + the `st_res_<good>_store_flow` / `st_res_<good>_withdraw_flow` hub-flow modifiers and `st_res_sell_profit_modifier` |
| [common/script_values/st_res_script_values.txt](../../common/script_values/st_res_script_values.txt) | Hub level, throughput factor, signed rate cap, weekly deltas, capacity, fill-%, and the per-good policy price values |
| [common/scripted_effects/st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt) | Init, reset, hub-cache refresh, hub-flow rebuild, weekly bookkeeping, signed-rate controls, status derivation, policy evaluation, AI seeding |
| [common/scripted_triggers/st_res_triggers.txt](../../common/scripted_triggers/st_res_triggers.txt) | `st_res_<good>_unlocked_trigger` — the single source of truth for per-good availability (§3) |
| [common/scripted_guis/st_res_scripted_gui.txt](../../common/scripted_guis/st_res_scripted_gui.txt) | `st_res_adjust_<good>_sgui` (row rate controls) and `st_res_policy_<good>_sgui` (policy panel) — thin per-good validation wrappers |
| [common/scripted_buttons/st_res_buttons.txt](../../common/scripted_buttons/st_res_buttons.txt) | The two shared, reserve-wide buttons: step size and reset-all |
| [common/journal_entries/je_strategic_reserve.txt](../../common/journal_entries/je_strategic_reserve.txt) | Summary text, shared buttons, widget wiring and weekly pulse owner |
| [gui/journal_entry_widgets/strategic_reserve_widget.gui](../../gui/journal_entry_widgets/strategic_reserve_widget.gui) | The reserve inventory table — one row per unlocked good |
| [common/customizable_localization/st_res_custom_loc.txt](../../common/customizable_localization/st_res_custom_loc.txt) | `st_res_<good>_mode_text` / `_reason_text` (driven by the bookkeeping status code) and `st_res_<good>_policy_text` / `_policy_reason_text` (driven by the policy status code) |
| [common/technology/technologies/](../../common/technology/technologies/) | Per-good decay adjustments: `INJECT:` blocks in `modified.txt` for vanilla techs, plain `modifier` lines on the mod's own era 6–12 techs (§4.4) |
| [localization/english/](../../localization/english/) | Row cells, row tooltips and flow-modifier names in `te_miscellaneous_l_english.yml`; modifier names in `te_modifiers_l_english.yml`; flow-modifier descriptions in `te_concepts_l_english.yml`; the JE, building and PM descriptions in their category files |

---

## 2. Buildings

### Hub — `building_strategic_reserve_hub`

Capital-only (`possible = { is_capital = yes }`), scalable (`has_max_level = yes`), unlocked by `logistics`. Construction cost is `construction_cost_very_high`. Each level provides:

- **+5 000 capacity per reserve good** via `country_st_res_<good>_capacity_add` (`country_modifiers` → `level_scaled`).
- **+1 000 to the shared weekly flow cap** via `country_st_res_weekly_rate_cap_add`. The cap (`st_res_weekly_base_rate_cap`) is per good, not a pool: every good may move up to that many units a week.

It also carries an `ai_value` (+50 for a great or major power, +150 at war), so AI majors build it — see §7.

### Silo — `building_strategic_reserve_silo`

Passive capacity-only building, buildable in any state, expandable, unlocked by `logistics`. Construction cost is `construction_cost_high`. Each level adds **+1 000 capacity per reserve good** and **+100 to the weekly flow cap** via the single PM `pm_st_res_silo_capacity`. Useless without a hub (it has no controls), but the way to scale a reserve past the hub's own capacity.

Both buildings are in `bg_public_infrastructure`.

---

## 3. Production Methods

### Hub PM

The hub has one PMG, `pmg_st_res_hub`, with one non-interactive PM, `pm_st_res_hub_reserve`. It carries every good's capacity (`level_scaled`) and, for every good, a **base 1-unit** `goods_input_<good>_add` **and** `goods_output_<good>_add` (`workforce_scaled`). That base is load-bearing: `goods_*_add` only registers goods flow when it comes from a PM, so the runtime flow modifiers (`st_res_<good>_store_flow` / `_withdraw_flow`, §4.5) are `_mult` modifiers that scale it. An idle good has both sides multiplied by −1, which cancels the base I/O.

The PM is the same for every good and has no tech gate. Which goods the player sees is decided by `st_res_<good>_unlocked_trigger` in [st_res_triggers.txt](../../common/scripted_triggers/st_res_triggers.txt), the only place an unlock condition may live:

| Good | Script ID | Unlocked by |
|---|---|---|
| Grain | `grain` | always |
| Small arms | `small_arms` | always |
| Artillery | `artillery` | always |
| Ammunition | `ammunition` | `percussion_cap` |
| Oil | `oil` | `fractional_distillation` |
| Chemicals | `fertilizer` | `intensive_agriculture` (the tech that unlocks the Chemical Plant, the good's producer) |
| Aeroplanes | `aeroplanes` | `military_aviation` |
| Tanks | `tanks` | `mobile_armor` |

A locked good still has capacity and its bookkeeping variables, but its rate stays 0 — its row and controls are hidden, and `st_res_policy_evaluate_good_effect` treats it as Manual even if the AI seeding gave it a policy — so the hub never trades it.

### Silo PM

`pm_st_res_silo_capacity` adds +1 000 to every good's capacity modifier and +100 to the weekly flow cap, both `level_scaled`.

---

## 4. Stockpile Bookkeeping

### 4.1 Country variables

| Variable | Meaning |
|---|---|
| `st_res_<good>_stored` | Current amount held (float) |
| `st_res_<good>_rate` | Signed configured weekly rate. Positive stores goods; negative withdraws goods. |
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

`st_res_init_effect` defaults stored amounts and signed rates to 0, `st_res_adjust_step_tier` to 1, and the hub caches to 0. `st_res_reset_vars_effect` zeros the same live vars when the JE goes invalid. Display-mode text is derived on demand in [common/customizable_localization/st_res_custom_loc.txt](../../common/customizable_localization/st_res_custom_loc.txt), so the live system no longer keeps persistent `sr_<good>_mode` variables.

### 4.2 Weekly update

`st_res_weekly_update_effect` runs from the JE's `on_weekly_pulse`. For each good it:

1. Adds `sr_<good>_weekly_delta`.
2. Clamps to `[0, sr_<good>_capacity]`.
3. Rebuilds the hub's transient flow modifiers so market input/output stays aligned with the stored country vars.

For each good, the weekly delta is:

$$
\Delta_w = \text{clamp}\left(r + \frac{d \cdot S}{52},\; -C,\; C\right) - \frac{d \cdot S}{52}
$$

where
- $r$ = `var:st_res_<good>_rate` (signed configured weekly rate),
- $d$ = `modifier:country_st_res_<good>_decay_add` (**annual** decay rate; divided by 52 and clamped to $[0,1]$),
- $S$ = current stored amount,
- $C$ = `st_res_weekly_base_rate_cap` (§2).

The hub therefore buys the week's decay on top of the configured rate, so a rate of 0 holds the stockpile level. The first term is zeroed when the hub is understaffed (occupancy below 100%), leaving only the decay. The pieces are the per-good script values `st_res_<good>_weekly_decay`, `_actual_rate`, `_actual_rate_base_applied` and `_weekly_delta`.

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

The throughput correction still uses the hub-scope read: `st_res_refresh_hub_cache_effect` bridges the hub's current `modifier:building_throughput_add` into country scope, and `st_res_throughput_factor` divides the market-facing flow multiplier (§4.5), so the goods the hub actually buys or sells match the amount the bookkeeping moves.

### 4.4 Decay rates (modifier-driven)

Decay rates are **custom country modifier types** (`country_st_res_<good>_decay_add`) registered in `st_res_modifier_types.txt`. Base values live in `INJECT:base_values` in `extra_modifiers.txt`, so every country has them by default. Techs adjust them via `INJECT:<tech>` in `common/technology/technologies/modified.txt` (vanilla techs) or a plain `modifier` line on the mod's own era 6–12 techs.

| Good | Base (per year) | Tech adjustments | After every adjustment |
|---|---|---|---|
| Grain | 25% | −5 pp each: `canneries`, `vacuum_canning`, `pasteurization`, `flash_freezing`, `lab-grown_food` | 0% |
| Ammunition | 2% | −0.5 pp each: `dynamite`, `modern_chemical_processes`, `military_grade_cybersecurity` | 0.5% |
| Oil | 0.5% | −0.05 pp `fractional_distillation`; −0.1 pp each: `modern_chemical_processes`, `predictive_logistics`, `supply_chain_management`, `advanced_workflow_optimization` | 0.05% |
| Small arms | 1.5% | −0.1 to −0.2 pp from five techs, `semiautomatic_rifle` to `molecular_assemblers` | 0.7% |
| Artillery | 1% | −0.1 to −0.2 pp from four techs, `motorized_artillery` to `programmable_matter` | 0.4% |
| Chemicals (`fertilizer`) | 1.5% | −0.5 pp `modern_chemical_processes` | 1% |
| Aeroplanes | 4% | rises in eras 7–9 (jets, stealth, UAVs), then falls in eras 10–12; ten techs | 2% |
| Tanks | 2.5% | rises in era 9 (composite armor, network-centric warfare), then falls in eras 10–12; eight techs | 1.4% |

Chemicals decay is caking, moisture uptake and container corrosion. `modern_chemical_processes` is the tech that already cuts ammunition and oil decay, so it covers chemicals too. `st_res_<good>_decay_rate` divides the annual rate by 52, and the modifier's `GetValueWithBreakdownFor` gives the player a hoverable breakdown of every source.

Decay is clamped to `[0, 1]` in the script values, so further tech reductions cannot push it negative.

### 4.5 Hub-flow safeguards

`st_res_rebuild_hub_flow_modifiers_effect` is the bridge from country-owned reserve vars back into the hub building. `st_res_startup_good_setup_effect` computes `st_res_<good>_can_store_local` and `st_res_<good>_can_withdraw_local` for each good; the effect then hops once into the hub's building scope, removes that good's previous flow modifiers, and re-applies one of three combinations:

| State | `st_res_<good>_store_flow` | `st_res_<good>_withdraw_flow` |
|---|---|---|
| Storing | × `st_res_<good>_good_mult` | × −1 |
| Withdrawing | × −1 | × `st_res_<good>_good_mult` |
| Idle, full, empty, understaffed or locked | × −1 | × −1 |

The two modifiers are `goods_input_<good>_mult = 1` and `goods_output_<good>_mult = 1` static modifiers, so a multiplier of −1 cancels the PM's base 1-unit I/O (§3). `st_res_<good>_good_mult` is `|flow| / throughput_factor − 1`, so the hub's building throughput bonus does not make it trade more than the bookkeeping books. **Both mult axes must be registered for every good**, or the modifier silently does nothing and the hub keeps trading its base unit (§1, `mod_entity_modifier_types.txt`).

The building-scoped per-good work is routed through one explicit wrapper per good — `st_res_rebuild_<good>_flow_modifiers_effect` for `grain`, `ammunition`, `oil`, `small_arms`, `artillery`, `aeroplanes`, `tanks` and `fertilizer` — each delegating to the shared helper `st_res_rebuild_good_flow_modifiers_effect = { GOOD = <good> }`, which keeps the concrete good names grep-able while removing the repeated in-building logic.

If a stockpile is full, empty, or configured with no legal effective flow, the −1 pair keeps the hub from consuming or producing that good even when the configured signed rate remains nonzero. The rate variable stays as configured; only the building-side market flow shuts off. (The `st_res_grain_disable_*_flow` / `st_res_ammunition_disable_*_flow` static modifiers still in `extra_modifiers.txt` are dead code from the older design; no effect references them.)


### 4.6 Reserve policies (price-triggered automation)

A good can be handed a **policy** instead of a hand-set rate. The weekly pulse then re-decides that good's `st_res_<good>_rate` from a running average of the market price, inside limits the player configures. Policies are opt-in and off by default: every good, in every save, starts on Manual with its rate untouched.

| `st_res_<good>_policy` | Policy | Behaviour |
|---|---|---|
| 0 | Manual | The player drives the rate. Nothing automated runs. |
| 1 | Buy When Cheap | Buys below the purchase threshold. Never sells. |
| 2 | Release When Expensive | Sells above the release threshold. Never buys. |
| 3 | Stabilize Prices | Both sides. |

#### The price signal — and which market it is

`st_res_<good>_price_rel` is the **signed premium against the good's base price on the country's own market** (`this.market.mg:<good>`), as a fraction: `-0.12` means 12% below base.

That is the same market [`st_res_<good>_sale_profit`](../../common/script_values/st_res_script_values.txt) already prices reserve sales at, and the market the hub's goods input/output clears on — the hub is capital-only, and the capital is in the country's market by construction. Player-facing localization therefore calls it the *national market price* rather than a local price. The nuance worth knowing: a building's true clearing price is its **state's** local price, which differs from the market price by local shortage and market access. For a capital state those two track each other closely, and using the market price keeps the policy signal consistent with the sale-revenue bookkeeping that already existed. If a future change ever moves the hub out of the capital, this is the assumption to revisit.

`market_goods_pricier` and `market_goods_cheaper` are readable as script values in `market_goods` scope — vanilla itself does it in `common/treaty_articles/13_goods_transfer.txt` (`value = market_goods_cheaper`). The reads use the `market = { mg:<good> = { add = … } }` **block** form, which is how vanilla reaches a market-goods value from country scope (`common/script_values/00_gfx_route_graphics_values.txt`, `gfx_infantry_mobilization_count`). Do not rewrite them as a `this.market.mg:<good>.<value>` dot chain: no vanilla file reads through `mg:` that way, and a price read that silently returned zero would park every automated lane in *Waiting* forever with no error to show for it. What the engine docs do **not** settle is whether each is clamped at zero or is the signed mirror of the other. `st_res_<good>_price_rel` is therefore built as

```
max(market_goods_pricier, 0) - max(market_goods_cheaper, 0)
```

via `st_res_<good>_price_up` / `_price_down` (`min = 0` after the read is the max-with-zero clamp). That expression yields the same correct signed premium under **either** engine behaviour. Do not simplify it to a bare `market_goods_pricier` read.

> The pre-existing `st_res_<good>_sale_profit` values still read bare `market_goods_pricier`. They are left alone deliberately — changing them would move sale revenue and therefore balance. If `pricier` turns out to be clamped at zero, those values slightly over-state revenue when selling below base price; that is a pre-existing question, not one policies introduce.

#### Price smoothing — the policy acts on a running average

The policies do **not** act on this week's price. Each good keeps a running average of the price signal, `st_res_<good>_price_avg` (percentage points against base price), advanced **once a week** by `st_res_policy_track_price_effect`:

```
avg ← avg + (live − avg) / price_memory        i.e.  A·live + (1−A)·avg,  A = 1 / price_memory
```

`st_res_<good>_price_memory` is therefore the averaging time constant in **weeks**: 1 = the live price (exactly the pre-smoothing behaviour), 4 = one week's spike moves the signal a quarter of the way, and so on. The evaluator, the widget and the tooltips all read the average through the guarded script value `st_res_<good>_price_signal`, which falls back to the live price until the first weekly tick has seeded it. The average is seeded **from the live price**, never from 0 — a cold start at 0 would read as "at base price" for weeks — and `st_res_reset_vars_effect` removes it rather than zeroing it, so a rebuilt hub re-seeds cleanly.

Three properties worth knowing:

- **It advances only on the weekly pulse.** The pulse calls `st_res_policy_tick_good_effect` (advance the average, then evaluate); the policy panel calls `st_res_policy_evaluate_good_effect` directly. A click therefore re-decides the lane against the same signal the last tick used, instead of dragging the average toward today's price once per click.
- **It tracks under every policy, Manual included**, so the average is already warm when the player switches a policy on.
- **Why it exists:** the reserve's own trading moves the price it is reacting to. A step response on the live price buys, pushes the price up through the threshold, stops, watches the price fall back, and buys again. Averaging the price and (below) softening the response are the two halves of stopping that.

#### Hysteresis (step response only)

Each good carries an engagement latch, `st_res_<good>_engaged` (0 idle / 1 engaged buying / 2 engaged releasing). With the **step response** (ramp 0, below) an engaged lane keeps going until the price crosses the **stop** threshold rather than the start threshold:

| | Start | Stop |
|---|---|---|
| Buying | below `buy_thr` | above `buy_thr + st_res_policy_buy_band` |
| Releasing | above `sell_thr` | below `sell_thr - st_res_policy_sell_band` |

With the Standard preset that reads: start buying below −10%, stop above −5%; start releasing above +20%, stop below +10%. A price oscillating around a single trigger therefore cannot flap the lane on and off week after week.

The two engaged regions can never overlap, because every path that writes a threshold keeps `sell_thr - buy_thr >= st_res_policy_min_gap` (= `buy_band + sell_band` = 15). The presets satisfy it by construction and the steppers are gated on it in `is_valid`, not only in GUI.

With a response ramp above 0 the bands are **not applied**: the response is continuous, so there is no on/off edge to debounce (the latch is still written, so the status label and the "engaged" state stay meaningful).

#### Response shape — step or linear ramp

`st_res_<good>_ramp` (percentage points) decides how hard a lane leans once the averaged price is past a threshold:

| Ramp | Response |
|---|---|
| 0 | **Step.** The full maximum weekly flow the moment the signal crosses the threshold, held by the hysteresis band until it recovers. The pre-smoothing behaviour, and the most oscillation-prone member of the family. |
| > 0 | **Linear.** The flow rises from 0 at the threshold to the maximum `ramp` points beyond it: `flow = max_flow × clamp((buy_thr − signal) / ramp, 0, 1)` on the buy side, mirrored on the release side. The reserve leans harder the further the price strays and eases off as it recovers, which is a proportional controller rather than a switch. |

The fraction multiplies `max_flow` **before** the existing caps (room under the target, spare above the floor, the hub's weekly flow cap, the budget), so every other rule applies to a ramped lane exactly as to a stepped one. With the Standard preset that reads: start buying below −10%, full flow at −20%; start releasing above +20%, full flow at +30%.

#### Settings, and where every number is defined

Eight per-good settings. **Presets fill all eight in one click**; the steppers fine-tune them.

| Setting | Variable | Unit | Conservative | Standard | Aggressive | Stepper |
|---|---|---|---|---|---|---|
| Purchase threshold | `st_res_<good>_buy_thr` | pp vs base price | −20 | −10 | −5 | ±5, range −50…0 |
| Release threshold | `st_res_<good>_sell_thr` | pp vs base price | +30 | +20 | +10 | ±5, range 0…+75 |
| Maximum weekly flow | `st_res_<good>_max_flow` | units/week | 100 | 250 | 600 | ±50 (shift ±500, ctrl ±5 000), range 50…the hub's weekly flow cap, never below 2 000 |
| Protected stockpile | `st_res_<good>_floor_pct` | % of capacity | 40 | 20 | 10 | ±5, range 0…100 |
| Target stockpile | `st_res_<good>_ceil_pct` | % of capacity | 60 | 80 | 95 | ±5, range 0…100 |
| Weekly purchase budget | `st_res_<good>_budget` | GBP/week, estimated | 5 000 | 15 000 | 40 000 | ±1 000 (shift ±10 000, ctrl ±100 000), range 1 000…the cost of a week at the flow ceiling, never below 100 000 |
| Price memory | `st_res_<good>_price_memory` | weeks averaged | 8 | 4 | 2 | ±1, range 1…26 |
| Response ramp | `st_res_<good>_ramp` | pp past a threshold | 20 | 10 | 5 | ±5, range 0…50 |

**Every one of these numbers is defined exactly once.** The twenty-four preset values live in the three `st_res_apply_preset_{conservative,standard,aggressive}_base` effects in [st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt); the step sizes, hysteresis bands and absolute bounds live in the `st_res_policy_*` constants at the bottom of [st_res_script_values.txt](../../common/script_values/st_res_script_values.txt). To retune, edit those and nothing else — the sgui gates, the evaluator and the tooltips all read them.

**The two magnitude settings scale with the hub.** The hub's weekly flow cap is 1 000 units plus 100 per Silo level, so a late-game network can move many times what an early one can. Two things follow. (1) Their ceilings are not constants: `st_res_policy_flow_max` is the hub's weekly flow cap rounded up to a step (the evaluator clamps a policy's flow to that cap anyway, so nothing above it could act), and the per-good `st_res_<good>_policy_budget_max` is what a full week at that flow — plus the week's decay replacement, which the budget pays first — costs at today's price, rounded up to a budget step. Each is floored at its old constant (`st_res_policy_flow_max_base` 2 000, `st_res_policy_budget_max_base` 100 000), so an early-game panel is unchanged. The budget ceiling moves with the price: a budget set at the top in a dear week can sit above it in a cheap one, which greys out the up stepper until the price recovers or the player clicks down (the step base clamps, so that click lands on the ceiling). (2) Their steppers take **shift-click for ten steps and ctrl-click for a hundred** (`st_res_policy_shift_mult` / `_ctrl_mult`) — the construction panel's convention, not the banking dashboard's tenth-and-limit one. Every size lands on the same clamp, so an oversized click stops at the bound. The other six steppers keep a single step: their ranges are fixed and short, and four of them have band limits (`_policy_*_limit`) that are only checked one step ahead.

Floor and ceiling are percentages of capacity rather than unit counts, so they keep meaning when the player builds Silos.

**Save migration.** A save from before policies existed gets all eight settings from the Standard preset behind the single `has_variable = st_res_<good>_policy` guard, as before. A save from after policies but before smoothing gets only the two new settings, at their **identity** values (memory 1, ramp 0) behind a second guard, so a policy that was already running keeps behaving exactly as it did until the player touches those settings or applies a preset. Those identity values are not tuning numbers, which is why they may appear outside the preset effects.

#### The budget is an estimate, and it is per week

Reserve purchases are **not** a money effect. The hub buys its input goods through production-method modifiers, so the money leaves the treasury inside the normal building-expense system and there is no cost value to read back. The budget is therefore applied as

```
affordable units = budget / current unit price - this week's decay replacement   (floored at 0)
```

and every player-facing string says "estimated". It is a **per-week cap, not a running pot**: what is not spent this week does not carry over. That keeps it stateless, save-safe, and impossible to desynchronise from the real spend. It also means "budget exhausted mid-week" is not a state that exists — the cap binds once, at the pulse, and shows as *Buying, limited by the weekly budget* or *Paused — this week's purchase budget is spent*.

One interaction to know: the hub buys enough to replace decay even at a configured rate of zero — that is pre-existing maintenance behaviour, not something policies added — so a *Waiting* or *Paused* lane still spends a little. The budget subtracts that decay replacement before deciding how many units it can cover, but it does not gate the replacement itself.

#### Status codes (`st_res_<good>_policy_status`)

| Code | Row explanation |
|---|---|
| 0 | Manual control — you set this good's rate by hand |
| 1 | Buying — price below the purchase threshold |
| 2 | Buying — limited by the weekly budget |
| 3 | Releasing — price above the release threshold |
| 4 | Waiting — the price has not crossed a trigger threshold |
| 5 | Paused — target stockpile reached |
| 6 | Paused — protected stockpile reached |
| 7 | Paused — this week's purchase budget is spent |
| 8 | Paused — hub understaffed |
| 9 | Paused — no Strategic Reserve Hub |

`st_res_policy_evaluate_good_effect` is the **only** writer of this variable and of the engagement latch, exactly as `st_res_set_good_status_effect` is the only writer of `st_res_<good>_last_status`. It is called from **both** branches of the weekly pulse (the no-hub branch takes its code-9 path) and from every policy-panel press, so nothing else ever has to guess a status.

#### How a policy reaches the rate

Automation has exactly one path to a configured rate: `st_res_apply_rate_target_base`. It writes `st_res_<good>_rate` and then applies the same two clamps `st_res_clamp_stockpiles_effect` applies — the hub's signed weekly flow cap, and the remaining storage room / remaining stockpile — which are the same bounds the manual +/− buttons are gated on. Everything downstream therefore applies to an automated lane exactly as to a hand-driven one: the flow cap, hub throughput, staffing, capacity, decay, the per-good tech unlocks, and the cost of the goods themselves. **Automation creates no goods and bypasses no bookkeeping**, and there are no new money effects anywhere in the feature.

Order inside the weekly pulse matters and is deliberate: last week's movement is booked first (`st_res_apply_weekly_good_effect`), then the price average advances and the policy re-decides (`st_res_policy_tick_good_effect`), then the existing shared refresh/clamp tail runs **once**. The evaluator rewrites the rate unconditionally every tick, which is what makes it immune to the auto-clamp having zeroed that rate at a stockpile bound last week.

#### Manual takeover

Two things — and only two — switch a good back to Manual, both of them explicit player actions:

- any of the row's decrease / stop / increase controls (the three rate bases call `st_res_switch_to_manual_base` before touching the rate), and
- the **Reset Reserve Rates** button.

`st_res_clamp_stockpiles_effect` deliberately does **not**. The auto-clamp zeroing a rate at a stockpile bound is bookkeeping, not intent; treating it as intervention would silently cancel a policy the first time a reserve filled up.

---

## 5. Journal Entry — Control Panel

`je_strategic_reserve` (group: `je_group_internal_affairs`) is the sole UI surface. Per-good presentation and control lives in the **reserve inventory widget**, [gui/journal_entry_widgets/strategic_reserve_widget.gui](../../gui/journal_entry_widgets/strategic_reserve_widget.gui), mounted in `custom_widget_container_2` (directly under the summary text, above the shared buttons).

- **Activation:** `possible` = the country has a hub built. `is_shown_when_inactive` requires `logistics`. The widget root is gated on `[JournalEntry.IsActive]` so it does not render — and does not read reserve variables — for a country that has never built a hub.
- **Summary text (`status_desc`):** hub status (no hub / deactivated / active), weekly sales income, and the hub flow cap. Deliberately short, because `status_desc` also renders in the journal *list*, where one block per good was unreadable.
- **Inventory rows:** one per unlocked good — `@good!` icon and name, `stored / capacity`, a fill bar driven by `st_res_<good>_fill_pct`, the configured signed rate, the actual net weekly movement (`st_res_<good>_last_net`), a Storing / Withdrawing / Idle / Blocked label, and decrease / stop / increase controls. The row tooltip breaks down stock, rate setting, active rate, net movement, weekly decay, hub flow cap and hub staffing, then states the reason movement differs from the setting.
- **Row visibility** is `ScriptedGui.IsShown`, delegating to `st_res_<good>_unlocked_trigger` — the unlock conditions are never duplicated in a GUI expression.
- **Row controls** call `st_res_adjust_<good>_sgui` with the action in a `dir` saved scope (`0` decrease, `1` stop, `2` increase). Each branch delegates to the existing `st_res_{increase,decrease,stop}_<good>_rate_effect` helpers, so the rate rules live in script, not in GUI. "Stop" zeroes only that good's rate. All three also switch the good to Manual — see §4.6.
- **Policy lines (3 and 4):** the good's policy, the live national market price against base with the averaged price the policy acts on beside it, and the weekly flow the policy settled on; then the plain-language explanation, straight from `st_res_<good>_policy_reason_text`. A gear button expands the per-good **settings panel**: the four policy buttons, the three presets, and eight +/− steppers.
- **Policy controls** call a second scripted GUI per good, `st_res_policy_<good>_sgui`, parameterized by a single `op` saved scope. One saved scope rather than two keeps the shape vanilla demonstrates (`je_meiji_restoration_get_faction_sgui`), so the op code carries both the action and which setting it acts on:

  | op | action | op | action |
  |---|---|---|---|
  | 0–3 | select policy Manual / Buy When Cheap / Release When Expensive / Stabilize Prices | 24 / 25 | maximum weekly flow − / + |
  | 10 / 11 / 12 | apply Conservative / Standard / Aggressive preset | 26 / 27 | protected stockpile − / + |
  | 20 / 21 | purchase threshold − / + | 28 / 29 | target stockpile − / + |
  | 22 / 23 | release threshold − / + | 30 / 31 | weekly budget − / + |
  | 32 / 33 | price memory (weeks) − / + | 34 / 35 | response ramp (pp) − / + |
  | 44 / 45 | maximum weekly flow − / + ten steps (shift-click) | 50 / 51 | weekly budget − / + ten steps (shift-click) |
  | 64 / 65 | maximum weekly flow − / + a hundred steps (ctrl-click) | 70 / 71 | weekly budget − / + a hundred steps (ctrl-click) |

  A modifier-click op is the plain op + 20 (shift) or + 40 (ctrl). It shares the plain op's `is_valid` branch (`OR` on all three codes), and the widget binds `enabled` to the plain op alone — so a new modifier op that is left out of that `OR` fails closed on the `trigger_else = { always = no }`.

  The table is duplicated in the sgui file header and the widget header; keep all three in sync. `is_valid` carries the whole validation surface, so every disabled control explains itself — including the non-overlap rules, which are never enforced in GUI alone.
- **The expander is presentation-only:** `GetVariableSystem.Toggle('st_res_policy_open_<good>')`, a key no script ever reads. Collapsing a panel cannot change what the reserve does, the state is intentionally not saved, and **policies keep running with the journal entry closed** because the evaluator lives on the weekly pulse.
- **Shared buttons (vanilla-rendered JE buttons):** `st_res_cycle_step_size_button` cycles the adjustment size through 1, 10, 100, 1000, 10000; `st_res_reset_rates_button` zeroes every good's rate. The current step is shown once, in the widget header.
- **`invalid`:** JE ends if the hub is destroyed.
- **`on_invalid`:** `st_res_reset_vars_effect` zeros all live vars and hub caches, so a rebuilt hub starts clean.

> The journal entry binds `scripted_progress_bar` and `scripted_button` declarations at **activation** time. A save whose SR journal entry is already running may still show the pre-widget bars/buttons until the hub is demolished and rebuilt.

---

## 6. Lifecycle Wiring

Weekly bookkeeping now lives on the JE itself: `je_strategic_reserve` calls `st_res_je_weekly_pulse_effect` from `on_weekly_pulse`, and `st_res_je_immediate_effect` / `st_res_je_invalid_effect` own activation and teardown. There is no separate SR on-action file in the current implementation.

Button presses call country-scoped wrapper effects in [common/scripted_effects/st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt). Those wrappers mutate the signed-rate or step-size vars, then immediately call the shared refresh helpers so the hub reflects the change without waiting for the next weekly tick.

---

## 7. AI

**The reserve used to be player-only. It no longer is** — and the reason matters, because the old claim was wrong about the premise rather than the code.

`building_strategic_reserve_hub` carries a real construction desire: [`common/buildings/strategic_reserve.txt:38-54`](../../common/buildings/strategic_reserve.txt) gives it `ai_value` +50 for a great or major power and a further +150 while at war. AI majors therefore **do** build hubs and **do** get this journal entry. What they never had was anything that moved a rate, so an AI reserve sat empty forever: every scripted button carries `ai_chance = { value = 0 }` and both scripted GUIs carry `ai_is_valid = { always = no }`.

Reserve policies close that gap without giving the AI a UI path. `st_res_ai_seed_policies_effect` hands an AI country the **Conservative** preset once — Stabilize Prices for the two civilian goods, grain and chemicals, and Buy When Cheap for every military good, on an 8-week price average with a 20-point ramp, so an AI reserve leans gently rather than flipping — and from then on it runs through `st_res_policy_evaluate_good_effect`, the same evaluator, thresholds, clamps and costs as a human on the same preset. There is no AI-only shortcut anywhere in the feature.

Details worth knowing:

- **One-shot**, marked by `st_res_policy_ai_seeded`, and gated on `is_ai`: it never touches a human player's goods and never re-seeds a country it has already set up. `st_res_reset_vars_effect` clears the marker so a rebuilt hub re-seeds. The marker does **not** protect a country that passes from a human to the AI mid-game — that country has no marker, so the AI seeds its own presets on the next pulse and the player's tuning is lost. That is the intended outcome for a country the player has walked away from, but it is worth knowing it is an overwrite.
- It runs from the JE's `immediate` **and** from the weekly pulse, because `immediate` does not re-run for a journal entry that is already active in a loaded save. The weekly cost for an already-seeded country is one `has_variable` check.
- The scripted GUIs stay `ai_is_valid = { always = no }`. They exist to validate player clicks; the AI reaches the same policies through script.
- The AI presets are **static** — they do not react to war. The Conservative preset's £5 000 weekly budget per good caps AI purchases at about £40 000/week across all eight goods (six on Buy When Cheap, grain and chemicals on Stabilize Prices) for a country wealthy enough to have built a hub in the first place, and a war-reactive variant is a balance decision rather than a correctness one.

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

Reserve policies added a second layer on top of that: a `st_res_policy_<good>_sgui`, `st_res_<good>_policy_text` **and** `st_res_<good>_policy_reason_text` custom loc, the ten policy script values (`_price_up`, `_price_down`, `_price_rel`, `_price_signal`, `_unit_price`, the four `_policy_*_limit` stepper guards and the `_policy_budget_max` stepper ceiling), two more calls in `st_res_weekly_update_effect` (`st_res_policy_tick_good_effect`, **both** branches), one `st_res_ai_seed_good_effect` call, the row's two extra loc keys and its policy-panel blockoverrides (eight value cells). The twelve per-good policy settings need no new init code — they are seeded by the guards already in `st_res_init_good_effect` — and the running price average is seeded by the first weekly tick.

**Worked example: Chemicals (`fertilizer`).** The most recent good, and a complete reference: `git grep -l st_res_fertilizer` lists every file it touches (the goods I/O lines in `pm_st_res_hub_reserve` and the `goods_input_fertilizer_mult` registration sit in files that list shows, just without that prefix). Vanilla registers neither of its mult axes, but the mod already registered `goods_output_fertilizer_mult` for a company and a unique PM, so only the input axis was new — check `mod_entity_modifier_types.txt` as well as vanilla before adding a registration, or the duplicate key is dropped. Its display name comes from the mod's vanilla-loc override, so loc strings name it *Chemicals* and everything else uses `fertilizer`.

---

## 10. Known Limitations / Future Work

- The hub has no animated icon or dedicated art.
- The SR scripted-effects slice is now `$GOOD$`-parameterized for init, reset, the hub flow rebuild, the weekly apply and the status derivation. The remaining per-good repetition is in [common/script_values/st_res_script_values.txt](../../common/script_values/st_res_script_values.txt), [common/scripted_guis/st_res_scripted_gui.txt](../../common/scripted_guis/st_res_scripted_gui.txt) and [common/customizable_localization/st_res_custom_loc.txt](../../common/customizable_localization/st_res_custom_loc.txt) — none of those file types accept `$GOOD$` parameters, so the repetition is structural rather than a cleanup candidate.
- No event flavor — a short event chain could celebrate reaching capacity or warn of shortages.
- The weekly purchase budget is an **estimate** applied as a units cap, not a true spend meter, because reserve purchases go through production-method modifiers rather than a money effect (§4.6). A real meter would need the engine to expose the hub's realised goods expense.
- The policy price signal is the **national market** price, not the hub state's local price (§4.6). They diverge when the capital is badly connected or in local shortage.
- AI policy presets are static and do not react to war.
- The response shape is a single linear ramp (a proportional controller); there is no integral term and no curved response, and the hysteresis bands only apply to the step response.
- Chemicals decay has a single tech reduction (`modern_chemical_processes`, era 6). Every other good gets several, spread across the eras; a late-era chemicals reduction (e.g. on an era 10–12 materials tech) would bring it into line.
- Silo has no distinctive icon — reuses the government-admin icon.