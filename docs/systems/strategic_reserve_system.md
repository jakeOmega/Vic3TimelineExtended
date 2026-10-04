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
| [common/script_values/st_res_script_values.txt](../../common/script_values/st_res_script_values.txt) | Hub level, throughput factor, signed rate cap, weekly deltas, capacity, fill-%, the per-good policy price values, and the panel's display-only values (`st_res_disp_hub_staffed`, `st_res_<good>_disp_status` / `_disp_policy` / `_disp_target` / `_disp_floor`) |
| [common/scripted_effects/st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt) | Init, reset, hub-cache refresh, hub-flow rebuild, weekly bookkeeping, signed-rate controls, status derivation, policy evaluation, AI seeding |
| [common/scripted_triggers/st_res_triggers.txt](../../common/scripted_triggers/st_res_triggers.txt) | `st_res_<good>_unlocked_trigger` — the single source of truth for per-good availability (§3) |
| [common/scripted_guis/st_res_scripted_gui.txt](../../common/scripted_guis/st_res_scripted_gui.txt) | `st_res_adjust_<good>_sgui` (row rate controls) and `st_res_policy_<good>_sgui` (policy panel) — thin per-good validation wrappers — plus `st_res_cycle_step_sgui` and `st_res_reset_rates_sgui`, the panel's two reserve-wide buttons |
| [common/scripted_buttons/st_res_buttons.txt](../../common/scripted_buttons/st_res_buttons.txt) | The two shared, reserve-wide buttons: step size and reset-all. `is_ai = yes` since the panel draws its own (§5); `ai_chance = 0`, so no one presses them |
| [common/scripted_effects/te_history_strategic_reserve_effects.txt](../../common/scripted_effects/te_history_strategic_reserve_effects.txt) | `te_history_record_strategic_reserve_samples`: each unlocked good's fill, monthly, into the shared history store (§5) |
| [common/journal_entries/je_strategic_reserve.txt](../../common/journal_entries/je_strategic_reserve.txt) | The no-hub status line, the AI's two scripted buttons, the panel's three widgets, the weekly pulse and the monthly history sample |
| [gui/journal_entry_widgets/strategic_reserve_widget.gui](../../gui/journal_entry_widgets/strategic_reserve_widget.gui) | The panel (§5): the overview, the inventory table with one row per unlocked good, and How the Strategic Reserve Works, as types composed in one order |
| [common/customizable_localization/st_res_custom_loc.txt](../../common/customizable_localization/st_res_custom_loc.txt) | `st_res_<good>_mode_text` / `_reason_text` (driven by the bookkeeping status code) and `st_res_<good>_policy_text` / `_policy_reason_text` (driven by the policy status code) |
| [common/technology/technologies/](../../common/technology/technologies/) | Per-good decay adjustments: `INJECT:` blocks in `modified.txt` for vanilla techs, plain `modifier` lines on the mod's own era 6–12 techs (§4.4) |
| [localization/english/](../../localization/english/) | Row cells, row tooltips and flow-modifier names in `te_miscellaneous_l_english.yml`; the panel's overview, headings and How the Strategic Reserve Works (`je_strategic_reserve_*`) in `te_journal_entries_l_english.yml`; modifier names in `te_modifiers_l_english.yml`; flow-modifier and concept descriptions in `te_concepts_l_english.yml`; the building and PM descriptions in their category files |

---

## 2. Buildings

### Hub — `building_strategic_reserve_hub`

Capital-only (`possible = { is_capital = yes }`), scalable (`has_max_level = yes`), unlocked by `logistics`. Construction cost is `construction_cost_very_low`, 100 points (it was `construction_cost_very_high`, 800, until 2026-09-26, and `construction_cost_low`, 200, until 2026-10-04): setting up a reserve is nearly free, and scaling it through silos is what costs. Each level provides:

- **+5 000 capacity per reserve good** via `country_st_res_<good>_capacity_add` (`country_modifiers` → `level_scaled`).
- **+1 000 to the shared weekly flow cap** via `country_st_res_weekly_rate_cap_add`. The cap (`st_res_weekly_base_rate_cap`) is per good, not a pool: every good may move up to that many units a week.

**One per country, and permanent.** `possible` also requires that the owner has no hub anywhere else (`st_res_hub_one_per_country_tt`), and the hub is `downsizeable = no`: neither the player nor the AI can downsize or demolish it. Every effect reads "the" hub through `random_scope_building`, so two would be read at random. The one way to lose a hub is to lose its state to another nation: `st_res_on_state_owner_change` (`common/on_actions/st_res_on_actions.txt`) demolishes it at once, so the conqueror never inherits an empty depot it cannot remove, and the loser's journal entry goes invalid (`st_res_je_invalid_effect`), resetting its reserve. This is the same pattern as `building_space_program` and the UN headquarters.

A hand-over between the two sides of a civil war keeps the hub, following the owner ruling that a revolution's winner continues the nation. `on_state_owner_change` gives script only the state and not its previous owner, so the weekly pulse stamps the hub's state with its holder (`st_res_record_hub_holder_effect`, state var `st_res_hub_holder`). `st_res_hub_stays_within_nation` (`st_res_triggers.txt`) then keeps the hub when the new owner is the stamped holder, shares its country definition (a revolution's rebels do), or is linked to it by `te_cw_origin` in either direction (the rebels of a revolution or a secession). Any one test is enough, because which of them holds at the outbreak and at the win depends on an engine order that has not been read in play. A hub less than a week old has no stamp, and counts as captured. `debug.log` records each outcome as a `TE_ST_RES:` line. This does not fix audit F11: the loser still resets its stock when its only hub goes to the rebels.

**The hub follows the capital.** A hub ends up outside the capital when the capital moves, or when its state passes to the other side of a civil war. Since it cannot be demolished, the weekly pulse moves it: `st_res_relocate_hub_to_capital_effect` runs first in `st_res_weekly_update_effect`, before the hub cache is read, in two steps.
1. With no hub in the capital and one elsewhere, it creates a level-1 hub in the capital for free.
2. Once the capital has its hub, it removes every hub outside the capital.

Each step is safe to repeat, so no hub is removed before its replacement is seen. Whether `create_building`'s result is visible to `has_building` later in the same effect is unread; if it is not, step 2 lands a week later, and for that week the country has two hubs. The stock lives on country variables and does not move. The new building hires its 5 000 staff from scratch, so until it is staffed, flow runs below capacity and the entry's status reads as deactivated (`st_res_hub_workforce_cached`); each move costs the reserve some weeks. The `TE_ST_RES:` log line fires when the creation is attempted, not when it succeeds; a refusal shows in `error.log`. `create_building` checks the unlocking technology since 1.13.9, so step 1 also requires `logistics`, or it would fail and log every week. Whether it checks `possible` is unverified, so the effect raises the country variable `st_res_hub_relocating` around the call, and the one-per-country guard accepts it (the `te_cm_placing_site` pattern). Together with the capture rule, this answers both ways a hub strands: a secession that takes the hub state keeps it and moves it to its own capital, and a country's own capital move takes its hub along.

It carries an `ai_value` of 2000 for a great or major power at peace and 1000 at war, plus 10 000 for any country above 10 million GDP (§7).

### Silo — `building_strategic_reserve_silo`

Passive capacity-only building, buildable in any state, expandable, unlocked by `logistics`. Construction cost is `construction_cost_high`. Each level adds **+1 000 capacity per reserve good** and **+100 to the weekly flow cap** via the single PM `pm_st_res_silo_capacity`. Useless without a hub (it has no controls), but the way to scale a reserve past the hub's own capacity. Its `ai_value` is 25 for a country with a hub, and 1025 while any reserve good stands at 75% of capacity or more (`st_res_reserve_filling_up`), so the AI adds storage as its reserve fills (§7).

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
| `st_res_<good>_last_status` | **Display only.** The status/reason code the inventory table renders. Written by `st_res_set_good_status_effect`. |

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
- $d$ = `st_res_<good>_annual_decay_rate`, i.e. `modifier:country_st_res_<good>_decay_add` floored at 0 (the **annual** decay rate; `st_res_<good>_decay_rate` is $d/52$, capped at 1),
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
| Chemicals (`fertilizer`) | 4% | −1 pp each: `improved_fertilizer`, `nitrogen_fixation`; −0.75 pp `modern_chemical_processes`; −0.5 pp `plastic_mass_production`; −0.25 pp `pollution_control`; −0.1 pp `supply_chain_management`; −0.15 pp each: `advanced_nanofabrication`, `molecular_assemblers` | 0.1% |
| Aeroplanes | 4% | rises in eras 7–9 (jets, stealth, UAVs), then falls in eras 10–12; ten techs | 2% |
| Tanks | 2.5% | rises in era 9 (composite armor, network-centric warfare), then falls in eras 10–12; eight techs | 1.4% |

Chemicals decay follows how chemical storage actually changed. In era 2 the stock sits in wooden casks, jute sacks and glass carboys: saltpetre and other hygroscopic salts cake, superphosphate "reverts" (its water-soluble phosphate turns insoluble), bleaching powder loses its chlorine, and carboys break. So 4% sits above ammunition's 2% and far below grain's 25%. The cuts track purer product grades (era 3), Haber-Bosch product in steel tanks and drums (era 4), prilling and anti-caking coatings (era 6), polyethylene sacks and tank liners (era 7), vapour recovery and spill containment (era 7), stock rotation (era 9), and impermeable coatings and on-site re-synthesis (era 12). The 0.1% endpoint sits between oil (0.05%) and ammunition (0.5%). Decay models physical and quality loss only. The real modern cost of holding bulk chemicals is storage rent, which the reserve charges through the hub's construction and staffing.

`st_res_<good>_annual_decay_rate` reads the modifier and floors it at 0, so further tech reductions cannot push decay negative; `st_res_<good>_decay_rate` divides it by 52 (capped at 1) for the weekly tick. The annual value is the single derivation site: an expanded inventory row's Decay cell shows it as *X%/yr* (§5), and the row tooltip adds the modifier's `GetValueWithBreakdownFor`, a hoverable breakdown of every source. The breakdown is the raw modifier, so it would read below 0% if tech ever cut a good past zero, while the row and the bookkeeping stop at 0%. No good does today; grain lands exactly on 0%.

Each good's `st_res_row_<good>_decay` key picks its own decimals to match that good's finest tech step: `%0` for grain (5 pp steps), `%2` for oil and chemicals (0.05–0.25 pp steps), `%1` for the rest. A new tech with a finer step needs the good's `st_res_row_<good>_decay` format widened, or the row rounds it away.

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
| Maximum weekly flow | `st_res_<good>_max_flow` | units/week | 2% of capacity | 5% of capacity | 12% of capacity | ±50 (shift ±500, ctrl ±5 000), range 50…the hub's weekly flow cap, never below 2 000 |
| Protected stockpile | `st_res_<good>_floor_pct` | % of capacity | 0 | 0 | 0 | ±5, range 0…100 |
| Target stockpile | `st_res_<good>_ceil_pct` | % of capacity | 100 | 100 | 100 | ±5, range 0…100 |
| Weekly purchase budget | `st_res_<good>_budget` | GBP/week, estimated | 0.1% of weekly GDP | 0.3% of weekly GDP | 0.8% of weekly GDP | ±1 000 (shift ±10 000, ctrl ±100 000), range 1 000…the cost of a week at the flow ceiling, never below 100 000 |
| Price memory | `st_res_<good>_price_memory` | weeks averaged | 8 | 4 | 2 | ±1, range 1…26 |
| Response ramp | `st_res_<good>_ramp` | pp past a threshold | 20 | 10 | 5 | ±5, range 0…50 |

**Every one of these numbers is defined exactly once.** The eighteen fixed preset values live in the three `st_res_apply_preset_{conservative,standard,aggressive}_base` effects in [st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt). The six magnitude shares are the `st_res_preset_*_flow_pct` / `_budget_pct` script values. The step sizes, hysteresis bands and absolute bounds live in the `st_res_policy_*` constants at the bottom of [st_res_script_values.txt](../../common/script_values/st_res_script_values.txt). To retune, edit those and nothing else — the sgui gates, the evaluator and the tooltips all read them.

**The two magnitude settings scale with the hub.** The hub's weekly flow cap is 1 000 units plus 100 per Silo level, so a late-game network can move many times what an early one can. Two things follow. (1) Their ceilings are not constants: `st_res_policy_flow_max` is the hub's weekly flow cap rounded up to a step (the evaluator clamps a policy's flow to that cap anyway, so nothing above it could act), and the per-good `st_res_<good>_policy_budget_max` is what a full week at that flow — plus the week's decay replacement, which the budget pays first — costs at today's price, rounded up to a budget step. Each is floored at its old constant (`st_res_policy_flow_max_base` 2 000, `st_res_policy_budget_max_base` 100 000), so an early-game panel is unchanged. The budget ceiling moves with the price: a budget set at the top in a dear week can sit above it in a cheap one, which greys out the up stepper until the price recovers or the player clicks down (the step base clamps, so that click lands on the ceiling). (2) Their steppers take **shift-click for ten steps and ctrl-click for a hundred** (`st_res_policy_shift_mult` / `_ctrl_mult`) — the construction panel's convention, not the banking dashboard's tenth-and-limit one. Every size lands on the same clamp, so an oversized click stops at the bound. The other six steppers keep a single step: their ranges are fixed and short, and four of them have band limits (`_policy_*_limit`) that are only checked one step ahead.

Floor and ceiling are percentages of capacity rather than unit counts, so they keep meaning when the player builds Silos.

**Preset flow and budget follow the country** (since 2026-09-26). They used to be fixed: 100 / 250 / 600 units and £5 000 / £15 000 / £40 000 a week per good. Eight goods at £5 000 could come close to a small minor's whole weekly GDP, and were nothing to a late-game great power. So each preset now sets two shares:
- **Flow** is a share of the good's capacity: 2 / 5 / 12% a week. That is exactly what the old numbers were against the hub's 5 000, so a new reserve reads as before, and a Conservative reserve fills in about 50 weeks whatever the country's size. Flow is physical, so it scales with the reserve rather than with GDP; a big country builds more silos.
- **Budget** is a share of weekly GDP (`gdp` is yearly, divided by 52): 0.1 / 0.3 / 0.8% per good. Money scales with the economy. Because the evaluator buys the lowest of flow, affordable units, room and the hub's cap, a small economy is held back by its budget, and a big one by its reserve.

Each result is rounded to the stepper's step and clamped to the stepper's range (`st_res_preset_write_flow_base` / `_budget_base`), so it is always a value the steppers could reach. A preset marks both settings as following it (`st_res_<good>_auto_max_flow` / `_auto_budget`, holding 1 / 2 / 3 for the preset). The weekly pulse rewrites every marked setting from today's capacity and GDP before the policies decide (`st_res_refresh_preset_magnitudes_effect`), so a preset keeps pace as silos go up and the economy grows. A click on the flow or budget stepper removes that setting's marker (`st_res_policy_set_by_hand_base`), and the player's number then stands. The two markers are independent, and no other stepper touches them. New games and reset reserves start on Standard with both markers set. The AI's Conservative is always marked, and its one-time migration marks AI countries seeded before this change. A player's goods in an existing save carry no marker, so the numbers they had are kept.

**The stock band belongs to the player, not the presets** (since 2026-09-26). Every preset uses the whole capacity, floor 0 and ceiling 100; before, they kept 40–60 / 20–80 / 10–95%. A floor the policy can never sell is dead weight, paying its decay replacement every week, and a ceiling below 100 leaves capacity unused. Under Conservative, the AI's preset, only 40–60% of capacity ever moved, and the AI never reached the 75% fill at which silos become worth building to it (§7). Players can still set both with the steppers, and a save keeps any band a player already has.

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

`je_strategic_reserve` (group: `je_group_internal_affairs`) carries the UI, and the Market panel's Reserve tab shows the same panel (below). Its panel is [gui/journal_entry_widgets/strategic_reserve_widget.gui](../../gui/journal_entry_widgets/strategic_reserve_widget.gui), built to the house style ([`gui_style_guide.md`](../guides/gui_style_guide.md)): each section is a type, two composers (`te_st_res_status_sections`, `te_st_res_reference_sections`) set their order, and the entry attaches three named roots.

| Container | Root | Shows | Default |
|---|---|---|---|
| 1, above the status text | `widget_je_strategic_reserve_overview` | The overview | Always shown |
| 2, under the status text | `widget_je_strategic_reserve_inventory` | Reserve Inventory | Open (`st_res_inventory_closed`) |
| 3, under the (empty, for a player) scripted-button grid | `widget_je_strategic_reserve_reference` | How the Strategic Reserve Works | Collapsed (`st_res_how_open`) |

Collapse flags say their default: `_closed` is open until closed, `_open` collapsed until opened. Every label in a fixed-width cell fits it by the round-3 width budget (characters × 10 / 8.6 / 7.3 units for the large / medium / small font, plus 10%), so nothing ends in "...". `test_strategic_reserve_layout.py` holds the order, the flags, the rows and the budget.

- **Activation:** `possible` = the country has a hub built. `is_shown_when_inactive` requires `logistics`. Every root and both composers are gated on `[JournalEntry.IsActive]`, so the panel does not render — and does not read reserve variables — for a country that has never built a hub.
- **Second host:** the Market panel's Reserve tab (`gui/market_panel.gui`, 2026-09-30) instances the same three types under `GetPlayerJournalEntry('je_strategic_reserve')`, then the Open Journal Entry button. The tab is on the strip from Logistics (the entry's `is_shown_when_inactive`) and greyed until the entry runs; its checklist is `st_res_entry_unlocked`, the entry's `possible` as one line. It shows only while the panel shows the player's own market (the one its capital is in, led or joined), where the reserve buys and sells; a panel opened on another market with the tab still selected shows a note and a button to the player's market instead. Gates: `te_market_strategic_reserve_tab_sgui` / `_unlock_sgui` (`common/scripted_guis/te_system_tab_sguis.txt`).
- **Status text (`status_desc`):** only the no-hub line, for the entry shown from Logistics before a hub exists (when the panel draws nothing). While the entry runs the status text is empty: the overview's hub cell says whether the hub is operating or understaffed (owner, 2026-09-29: status text that repeats the overview is removed). The week's sales income and the hub flow cap, once lines here, are overview cells.
- **Overview:** three fixed cells. The hub's own icon, at full colour while it is fully staffed and dimmed below that (`st_res_disp_hub_staffed`), with *Hub Operating* or *Understaffed* beneath (the staffing percentage is on hover); the flow cap (`st_res_weekly_base_rate_cap`), its modifier breakdown on hover; and the week's sales income (`st_res_total_sale_profit`), with what it counts on hover.
- **Inventory:** 496px wide inside a 12px margin, so the panel is the 520px of the sections around it and a good's 496px history chart fits without widening it. First the adjustment step, said once above the rows because it holds for every row's buttons, with **Cycle Step Size** and **Reset Reserve Rates** beside it, labelled *Cycle Step* and *Reset Rates* so they fit, each tooltip opening with the full name: `st_res_cycle_step_sgui` / `st_res_reset_rates_sgui`, whose effects are the scripted buttons' effects in a `hidden_effect` under one `custom_tooltip` line, with the composed tooltip (`IsValidTooltip`, `te_tt_break`, `ExecuteTooltip`). The scripted buttons stay declared, with `is_ai = yes`, because the entry binds its buttons at activation. Then column headings (Good, Stock, Status over both icon columns, Rate), each explained on hover, and one `te_st_res_good_row` per good, a table line of fixed-width cells:
  - **Good:** `@good!` icon and name. Clicking it expands the row (below).
  - **Stock:** a fill bar driven by `st_res_<good>_fill_pct`. A marker stands at the **target stockpile** while the policy can buy (Buy When Cheap, Stabilize Prices) and at the **protected stockpile** while it can sell (Release When Expensive, Stabilize Prices). `st_res_<good>_disp_target` / `_disp_floor` return those settings under those policies and the bar's ends (100 / 0) otherwise, and the row hides a marker at its end — so a Manual good, or a policy using the whole capacity (every preset), shows none.
  - **Status:** an icon per status (owner, 2026-09-30): Idle, Storing, Withdrawing or Blocked. Four icons share the cell, each with one `visible` on one value of `st_res_<good>_disp_status`, which groups the stored `st_res_<good>_last_status` code exactly as the status word `st_res_<good>_mode_text` does; so exactly one is drawn. The word and its reason are on hover. The icons are one supply crate with the state as a mark (`st_res_icons/status_*.dds`, [`strategic_reserve_gui_icons.md`](strategic_reserve_gui_icons.md)).
  - **Policy icon:** a brass governor (`st_res_icons/policy_automated.dds`, [`strategic_reserve_gui_icons.md`](strategic_reserve_gui_icons.md)), lit while an automated policy sets the rate (`st_res_<good>_disp_policy` above 0) and dimmed on Manual. The dimmed icon is always drawn and the lit one covers it, so the row needs one visibility per good. It is an untextured button: a click opens or closes the good's Policy Settings (below) straight from the table line.
  - **Rate:** decrease / stop / increase.
  The row tooltip breaks down stock, rate setting, active rate, net movement, the decay rate with its per-source breakdown, weekly decay, hub flow cap and hub staffing, then states the reason movement differs from the setting, and the policy.
- **Expanding a row** (clicking the good's name toggles `st_res_row_<good>_open`) shows the good's figures as label / value rows: Stored (`stored / capacity (fill%)`), Rate Setting, Last Week (the actual net movement, `st_res_<good>_last_net`), Decay (the annual rate, §4.4, and this week's loss), Market Price (the live premium against base, with the averaged price the policy acts on) and Reserve Policy (its name). Under them is the policy's plain-language explanation, straight from `st_res_<good>_policy_reason_text`; then the good's **fill by month**, a `te_history_chart` with the shared 1 / 5 / 20-year range buttons (below); then a **Policy Settings** subsection, collapsed until opened (`st_res_policy_<good>_open`), holding the settings panel: the four policy buttons, the three presets and eight +/− steppers. Policy Settings shows under an expanded row, or under a collapsed one while it is open (the policy icon opens it from the table line).
- **Fill history:** one series per good, `st_res_<good>` = `st_res_<good>_fill_pct` (0–100), recorded once a month from the entry's `on_monthly_pulse` by `te_history_record_strategic_reserve_samples` for each unlocked good, into the shared store (`docs/systems/mod_systems.md` § "History Store and Charts"; eligibility is the store's own, players and major powers). A share rather than units, so the axis is a fixed 0–100 and matches the row's bar; building Silos therefore lowers the share of an unchanged stock, which the legend says. The chart sits inside the collapsed row, the owner's exception to "history charts open by default", and draws no marker pips (other systems' markers would go unexplained). Cost: variables rather than containers, one per unlocked good per month on the 240 monthly containers a tracked country already keeps. Rows start collapsed; the chevron beside the name is vanilla's outliner pair (`expand_arrow` / `expand_arrow_expanded`, both `alwaystransparent` so chevron and name are one click target).
- **Row visibility** is `ScriptedGui.IsShown`, delegating to `st_res_<good>_unlocked_trigger` — the unlock conditions are never duplicated in a GUI expression.
- **Row controls** call `st_res_adjust_<good>_sgui` with the action in a `dir` saved scope (`0` decrease, `1` stop, `2` increase). Each branch delegates to the existing `st_res_{increase,decrease,stop}_<good>_rate_effect` helpers, so the rate rules live in script, not in GUI. "Stop" zeroes only that good's rate. All three also switch the good to Manual — see §4.6. Their tooltips end with `IsValidTooltip`, so a grayed-out button says why.
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

  The button of the policy in force is disabled, and so is the button of the **preset in force** (since 2026-09-26): each `st_res_apply_preset_*_base` writes `st_res_<good>_preset` (1 Conservative, 2 Standard, 3 Aggressive) and `st_res_policy_set_by_hand_base` removes it on any stepper click, so a preset counts as in force until a setting is changed by hand. Choosing a policy, the row controls and the weekly magnitude refresh change none of a preset's settings and leave it in force. New games and reset reserves start with Standard disabled, and an AI country seeded after this change starts with Conservative disabled when a player takes it over. A save from before the marker has none, so all three stay enabled until the player applies one.
- **Every expander is presentation-only:** the row, its settings and the two collapsible sections toggle `GetVariableSystem` keys no script ever reads. Collapsing any of them cannot change what the reserve does, the state is intentionally not saved, and **policies keep running with the journal entry closed** because the evaluator lives on the weekly pulse.
- **Reserve-wide buttons:** Cycle Step Size cycles the adjustment size through 1, 10, 100, 1000, 10000; Reset Reserve Rates zeroes every good's rate and switches every good to Manual. Both are panel buttons beside the step (above); the journal entry's `st_res_cycle_step_size_button` / `st_res_reset_rates_button` run the same effects for the AI only (`is_ai = yes`, and `ai_chance = 0`).
- **How the Strategic Reserve Works** holds every explanation, one heading per topic: the hub and silos, rates, status, decay, reserve policies, presets and settings, sales income, and fill history. The live sections carry none.
- **Concepts:** Rate Setting, Active, Flow Cap, Adjustment Step and Reserve Policy (`concept_st_res_*` in `common/game_concepts/extra_concepts.txt`).
- **`invalid`:** JE ends if the hub is destroyed.
- **`on_invalid`:** `st_res_reset_vars_effect` zeros all live vars and hub caches, so a rebuilt hub starts clean.

> The journal entry binds `scripted_progress_bar` and `scripted_button` declarations at **activation** time. A save whose SR journal entry is already running may still show the pre-widget bars/buttons until the hub is demolished and rebuilt.

---

## 6. Lifecycle Wiring

Weekly bookkeeping now lives on the JE itself: `je_strategic_reserve` calls `st_res_je_weekly_pulse_effect` from `on_weekly_pulse`, and `st_res_je_immediate_effect` / `st_res_je_invalid_effect` own activation and teardown. The one on-action, in `common/on_actions/st_res_on_actions.txt`, is `on_state_owner_change`, which demolishes a captured hub (§2). The weekly pulse opens by moving a hub that stands outside the capital into it (§2).

Button presses call country-scoped wrapper effects in [common/scripted_effects/st_res_effects.txt](../../common/scripted_effects/st_res_effects.txt). Those wrappers mutate the signed-rate or step-size vars, then immediately call the shared refresh helpers so the hub reflects the change without waiting for the next weekly tick.

---

## 7. AI

**The reserve used to be player-only. It no longer is** — and the reason matters, because the old claim was wrong about the premise rather than the code.

`building_strategic_reserve_hub` carries a real construction desire: [`common/buildings/strategic_reserve.txt`](../../common/buildings/strategic_reserve.txt) gives it an `ai_value` of 2000 for a great or major power at peace and 1000 at war, **plus 10 000 for any country whose yearly GDP is above `st_res_ai_hub_min_gdp` (10 million; [`st_res_script_values.txt`](../../common/script_values/st_res_script_values.txt))**, great power or not. 10 000 is the value vanilla gives its monuments, five times the 2000 tier, so a country that rich with no hub builds one ahead of nearly everything else it could build; the GDP tier does not drop for war, because at 100 construction points (§2) a hub finishes within a build cycle. The `possible` guard allows one hub per country, so the building is only ever evaluated for a country without one and the value needs no "has no hub yet" test. The tier has not been watched in game: the engine's AI weighs `ai_value` against everything else it can build and against its construction capacity, so "very likely" is the intent, not a measured rate. For scale, `GOVERNMENT_BUILDING_BASE_VALUE` (1000) is what a government building with no scripted `ai_value` gets, and 2000 is vanilla's "higher base value" tier (naval administration). Until 2026-09-26 the hub scripted +50, or +200 at war, which the AI read as nearly worthless; peacetime now counts double because a depot begun in a war finishes too late to fill. The silo is worth 1025 while any good is at 75% of capacity or more, and 25 otherwise. A flat value would have the AI build silos without end, since nothing in code tells it how much storage it needs. AI majors **do** build hubs and **do** get this journal entry. What they never had was anything that moved a rate, so an AI reserve sat empty forever: every scripted button carries `ai_chance = { value = 0 }` and both scripted GUIs carry `ai_is_valid = { always = no }`.

Reserve policies close that gap without giving the AI a UI path. `st_res_ai_seed_policies_effect` hands an AI country the **Conservative** preset once, with **Stabilize Prices for every good**, on an 8-week price average with a 20-point ramp, so an AI reserve leans gently rather than flipping. Until 2026-09-26 the six military goods were on Buy When Cheap, which never sells, so an AI reserve never released a round into a war's price spike; stabilizing buys below −20% up to full capacity and releases above +30% down to empty, since no preset sets a stock band any more (§4.6). Saves seeded before then are moved over once: `st_res_policy_ai_stabilized` marks the migration, and `st_res_ai_stabilize_good_effect` switches any good still on Buy When Cheap, widens every good's stock band from the old 40–60% to 0–100%, and leaves the other settings alone. From then on the AI runs through `st_res_policy_evaluate_good_effect`, the same evaluator, thresholds, clamps and costs as a human on the same preset. There is no AI-only shortcut anywhere in the feature.

Details worth knowing:

- **One-shot**, marked by `st_res_policy_ai_seeded`, and gated on `is_ai`: it never touches a human player's goods and never re-seeds a country it has already set up. `st_res_reset_vars_effect` clears both markers so a rebuilt hub re-seeds. The marker does **not** protect a country that passes from a human to the AI mid-game — that country has no marker, so the AI seeds its own presets on the next pulse and the player's tuning is lost. That is the intended outcome for a country the player has walked away from, but it is worth knowing it is an overwrite.
- It runs from the JE's `immediate` **and** from the weekly pulse, because `immediate` does not re-run for a journal entry that is already active in a loaded save. The weekly cost for an already-seeded country is one `has_variable` check.
- The scripted GUIs stay `ai_is_valid = { always = no }`. They exist to validate player clicks; the AI reaches the same policies through script.
- The AI presets are **static**; they do not switch mode for a war. They do not need to for ammunition: a war takes its price to the maximum (`docs/systems/mod_systems.md` § "Wartime Munitions Demand"), well past the +30% release threshold. The Conservative preset's budget, 0.1% of weekly GDP per good (at least £1 000), caps AI purchases at about 0.8% of weekly GDP across all eight goods, and its flow of 2% of capacity a week fills an empty reserve in about a year.

---

## 8. Deviations from the Original Spec

| Original spec | Implemented | Why |
|---|---|---|
| Hub + Satellite Depots with complex per-depot logic | Hub (active) + Silo (passive capacity) | Clean separation: hub controls modes + provides base capacity, silo scales capacity up |
| Mode cycling + separate speed tier | Signed per-good weekly rates + one shared step-size selector | Fewer live vars and more direct control over the target reserve flow |
| Weekly pulse | Weekly pulse on the JE itself | Keeps bookkeeping close to the JE lifecycle and the signed-rate controls |
| Flat throughput compensation multiplier | `st_res_throughput_factor` reads `modifier:building_throughput_add` from the hub | Same intent, but the hub-scope read automatically accounts for every contributing source |
| Fixed hard-coded decay rates | Custom modifier types + `INJECT:base_values` + tech INJECTs | Modders, techs, events, and laws can all alter decay now |
| `single_level = yes` | `possible = { is_capital = yes }` + a no-other-hub guard + `has_max_level = yes`, and the weekly move to the capital | `single_level` isn't a real field. Capital-only alone did not keep it to one per country, because a country that moved its capital could build a second hub |
| Modifier `country_[good]_storage_max_add` | `country_sr_<good>_capacity_add` | The `sr_` prefix avoids colliding with any vanilla modifier name |
| Read `scope:sr_decay_amount` from loc | `GetVariable` / `GetModifier.GetValueWithBreakdownFor` / `custom_localization` | Temporary saved scopes don't persist into `status_desc`; only persistent variables and modifiers work for UI display |

---

## 9. Extending with a New Good

**The authoritative, file-by-file procedure is the `add-strategic-reserve-good` skill** (`.claude/skills/add-strategic-reserve-good/SKILL.md`, with verbatim snippets in `references/per_good_templates.md`). Follow it rather than this section — it is kept in sync with the implementation, including the vanilla mult-axis registration gap that silently breaks a new good.

What the inventory widget added to that procedure, in short: a good now also needs an entry in `st_res_triggers.txt` (its unlock trigger), an `st_res_adjust_<good>_sgui` in `st_res_scripted_gui.txt`, `st_res_<good>_mode_text` **and** `st_res_<good>_reason_text` custom loc, an `st_res_<good>_last_net` script value, a `st_res_stop_<good>_rate_effect` wrapper, one call each added to the per-good lists in `st_res_init_effect` / `st_res_reset_vars_effect` / `st_res_weekly_update_effect` / `st_res_refresh_hub_flow_effect`, and one row instance plus its loc keys in the widget. It no longer needs a scripted progress bar, a pair of scripted buttons or a journal-entry status line.

Reserve policies added a second layer on top of that: a `st_res_policy_<good>_sgui`, `st_res_<good>_policy_text` **and** `st_res_<good>_policy_reason_text` custom loc, the ten policy script values (`_price_up`, `_price_down`, `_price_rel`, `_price_signal`, `_unit_price`, the four `_policy_*_limit` stepper guards and the `_policy_budget_max` stepper ceiling), two more calls in `st_res_weekly_update_effect` (`st_res_policy_tick_good_effect`, **both** branches), one `st_res_ai_seed_good_effect` call, the row's two extra loc keys and its policy-panel blockoverrides (eight value cells). The panel's style-guide pass (2026-09-29/30) added four display values per good (`_disp_status`, `_disp_policy`, `_disp_target`, `_disp_floor`), two more row loc keys (`_last`, `_price`), a history series (one block in `te_history_strategic_reserve_effects.txt`) and its two chart-tooltip keys (`st_res_hist_tt_<good>`, `_row`); `test_strategic_reserve_layout.py` fails until a new good has all of them and its row matches the others. The twelve per-good policy settings need no new init code — they are seeded by the guards already in `st_res_init_good_effect` — and the running price average is seeded by the first weekly tick.

**Worked example: Chemicals (`fertilizer`).** The most recent good, and a complete reference: `git grep -l st_res_fertilizer` lists every file it touches (the goods I/O lines in `pm_st_res_hub_reserve` and the `goods_input_fertilizer_mult` registration sit in files that list shows, just without that prefix). Vanilla registers neither of its mult axes, but the mod already registered `goods_output_fertilizer_mult` for a company and a unique PM, so only the input axis was new — check `mod_entity_modifier_types.txt` as well as vanilla before adding a registration, or the duplicate key is dropped. Its display name comes from the mod's vanilla-loc override, so loc strings name it *Chemicals* and everything else uses `fertilizer`.

---

## 10. Known Limitations / Future Work

- The hub has no animated icon or dedicated art.
- The SR scripted-effects slice is now `$GOOD$`-parameterized for init, reset, the hub flow rebuild, the weekly apply and the status derivation. The remaining per-good repetition is in [common/script_values/st_res_script_values.txt](../../common/script_values/st_res_script_values.txt), [common/scripted_guis/st_res_scripted_gui.txt](../../common/scripted_guis/st_res_scripted_gui.txt) and [common/customizable_localization/st_res_custom_loc.txt](../../common/customizable_localization/st_res_custom_loc.txt) — none of those file types accept `$GOOD$` parameters, so the repetition is structural rather than a cleanup candidate.
- No event flavor — a short event chain could celebrate reaching capacity or warn of shortages.
- The weekly purchase budget is an **estimate** applied as a units cap, not a true spend meter, because reserve purchases go through production-method modifiers rather than a money effect (§4.6). A real meter would need the engine to expose the hub's realised goods expense.
- The policy price signal is the **national market** price, not the hub state's local price (§4.6). They diverge when the capital is badly connected or in local shortage.
- AI policy presets are static and do not switch mode for a war; they release into a war's price spike only through Stabilize Prices' threshold.
- A hub moved to a new capital (§2) is a new building with no staff, so its flow is reduced until it is staffed, and if `create_building`'s result is not visible in the same effect, the country holds two hubs for a week.
- The response shape is a single linear ramp (a proportional controller); there is no integral term and no curved response, and the hysteresis bands only apply to the step response.
- Silo has no distinctive icon — reuses the government-admin icon.