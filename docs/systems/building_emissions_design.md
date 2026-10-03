# Per-Building Greenhouse-Gas Emissions: Scoping

**Status: scoping, nothing built (2026-10-02).** Follows issue #660 (Resource Transition), which deliberately left emissions accounting unchanged. Asks: make the emissions-control production methods cut CO₂, ideally through a modifier such as `country_emissions_add`, and, if possible, replace the market-wide "sum of coal and oil consumption" with something visible per building. §6 lists the decisions that need the owner.

## 1. How emissions work today

One script value carries the whole system. Everything else reads it.

```
market_greenhouse_gas_emissions_script_value      (common/script_values/extra_script_values.txt)
  = (market oil consumption × 2 + market coal consumption × 2) / 10000
    × gw_emission_multiplier_script_value          (1 + the market leader's modifier:country_greenhouse_gas_emissions_mult, floored at 0)
    + market_carbon_capture_script_value           (negative: synthetic fuel plants, from hard-coded per-level constants)
```

- **Cadence.** The market capital's yearly state pulse (`global_warming_update_on_action`) snapshots it into `var:gw_disp_market_emis` on the leader (`gw_snapshot_market_emissions_effect`) and adds it to `global_var:greenhouse_gas_emissions`; temperature is that total / 10000. The consumption read is the week's, so a market's "annual emissions" are one week's burn × 2 / 10000.
- **Boundary: consumption in the market.** Whatever the market's buildings and pops burn counts, wherever it was mined; imports count, exports don't. Extraction itself emits nothing. This is why #660's laws earn no emissions cut of their own.
- **Who burns.** About 94 PMs take coal and 100 take oil (`/modifier-search?q=goods_input_coal_add`, `…oil_add`), plus 6 ship types (coal), plus pops: vanilla's `popneed_heating` takes coal (up to 80% of the need) and oil (up to 100%). Some oil is feedstock (plastics, polyester, nylon, dyes), which the formula treats as burned.
- **Cuts.** Only the leader's `country_greenhouse_gas_emissions_mult` (the three market-wide policies, the environment ministry −5% per level, the sustainability principle, UN conventions, climate summits) scales the market, and only down to 0. Capture is the only way below 0.
- **Readers.** All downstream figures come from `var:gw_disp_market_emis` or the script value itself: the world total and temperature, Our Market's Emissions, Our Share, Top Emitters and cumulative totals, the History chart, the UN docket's climate shares, treaty 109's market leader. The Emissions Cut pie is `1 − gw_emission_multiplier_script_value`. **So a new accounting has a single seam:** change `market_greenhouse_gas_emissions_script_value` (and the capture value), and every reader follows.

## 2. The emissions-control methods today

`pmg_emissions_control` (`common/production_method_groups/extra_pm_groups.txt`) is **one group shared by four buildings**: Power Plants, Steel Mills, Ports and Automotive Industries (`INJECT:` / `REPLACE:` blocks in `common/buildings/extra_buildings.txt`). Its methods (`common/production_methods/extra_pms.txt`) cut only local pollution:

| Method | Unlock | Effect per level (workforce-scaled) | Inputs per level |
|---|---|---|---|
| No Emissions Control | `law_no_ministry_of_the_environment` (so unavailable once the ministry exists) | none | none |
| Basic Emissions Control | Pollution Control | −10 state pollution | 1 tools, 1 electricity (£70) |
| Advanced Emissions Control | `law_ministry_of_the_environment` | −20 state pollution | 2 tools, 2 electricity (£140) |

Because the no-control method needs *no* ministry, establishing the Ministry of the Environment forces every one of these buildings onto Basic or Advanced. Whatever CO₂ effect the methods get therefore reaches every country with a ministry, AI included.

Fuel burned per level at full staffing by the four buildings' methods (the server's `/production-methods/` data, mod values):

| Building | Fuel methods (coal / oil per level) | Emission units per level (×2) |
|---|---|---|
| Power Plant | early 5 coal; coal-fired 20; oil-fired 25 oil; modern coal 25; modern oil 35 oil | 10–70 |
| Steel Mill | every steelmaking process 30 coal (electric arc included), + automation 5–10 coal | 60–80 |
| Port | industrial 5 coal; modern / container / global / magnetic 10 oil; + passenger 5 | 10–30 |
| Automotive Industry | 5–10 oil, + assembly lines 5 oil | 10–30 |

The spread inside one shared group, 10 to 80 per level, is the main design constraint below.

## 3. Engine facts the designs rest on

- **PM modifier blocks** (`game/common/production_methods/production_methods.md`): `country_modifiers`, `state_modifiers` and `building_modifiers`, each with `workforce_scaled` (scaled by staffing, 0 to the building's level), `level_scaled` and `unscaled`. Workforce scaling follows staffing, not throughput: economy of scale, throughput modifiers and `goods_input_*_mult` (Fossil-Fuel Divestment's −5% coal and oil input, for one) change fuel burned but not a workforce-scaled modifier. Script can't read a building's throughput.
- **A custom modifier type in a PM, read from script, is shipped practice.** Country: `country_cultural_pull_add` (university PMs' `country_modifiers.workforce_scaled`, read as `modifier:country_cultural_pull_add`). State: `state_fortification_level_add` (PM-fed, read in battle conditions). Building: `b:<type>.modifier:building_annual_<wonder>_progress` (`common/scripted_effects/extra_effects.txt`), and `modifier:building_throughput_add` in `st_res_effects.txt`. The `modifier` link takes country, building, state and market scopes (`event_targets.log`).
- **Country modifiers from a PM go to "the country"** (the doc's wording). For government buildings that is the state's owner; for a foreign-owned plant, whether it is the location's owner or the owning country is **unverified**. Building modifiers sit on the building, and script reaches buildings by location (`market → every_scope_country → every_scope_building`, as `market_carbon_capture_script_value` already does yearly).
- **Modifiers add; a custom `_mult` scales nothing by itself.** The engine applies only its own pairs. A custom `building_..._mult` is a number script must apply.
- **`INJECT:` sums nested modifier blocks** (confirmed in game for ranks, techs, laws and static modifiers; `scripting_best_practices.md`), and the mod already INJECTs `building_modifiers` into vanilla PMs (`INJECT:pm_market_stalls`). **It silently fails on a mod-only or `REPLACE`d entity**, and many fuel PMs are one or the other (`pm_coal-fired_plant` and `pm_oil-fired_plant` are `REPLACE`d; the modern plants are mod PMs). A generator needs three cases: INJECT for untouched vanilla PMs, in-place edits for mod and REPLACEd PMs.

## 4. Options

### A. `country_greenhouse_gas_emissions_add` on the control methods (the proposal as given)

Register a country type (named beside the existing `country_greenhouse_gas_emissions_mult`), put a negative value in `country_modifiers.workforce_scaled` of Basic and Advanced, and add Σ over the market's members of `modifier:country_greenhouse_gas_emissions_add` / 10000 to the market figure.

- For: O(1) per country to read, no building sweep; the PM tooltip shows the number; the country's modifier breakdown lists it by source.
- Against: one negative number per level cannot fit a group whose buildings burn 10 to 80 per level (§2). Calibrated to power plants, it over-credits ports and car plants several times over; calibrated to ports, it barely touches a steel mill. Making it fit means **splitting the group per building** (four groups, eight methods), and even then a power plant's credit can't follow its fuel method (early 10 vs modern oil 70) without one method per fuel (`unlocking_production_methods` variants). A flat credit can also exceed the building's own burn, turning a small plant into a carbon sink.
- Also: it sums into the country the modifier lands on; for a foreign-owned building that may not be the market it burns in (§3).

### B. Building-level emissions and a proportional cut (recommended)

Two building modifier types, both visible:

- `building_greenhouse_gas_emissions_add`: every fuel method carries 2 × (its coal + oil input) in `building_modifiers.workforce_scaled`, written by a generator from the method's own `goods_input_coal_add` / `goods_input_oil_add`. A coal-fired plant shows "+40 Greenhouse Gas Emissions" per staffed level in its building and method tooltips.
- `building_greenhouse_gas_emissions_mult`: the control methods carry it unscaled (e.g. Basic −10%, Advanced −40%; §6).

Script, yearly, in the same sweep shape as the capture value: abatement = Σ over the market's buildings with a negative mult of `modifier:building_greenhouse_gas_emissions_add × modifier:building_greenhouse_gas_emissions_mult` / 10000. Then:

```
market emissions = max(0, consumption gross − abatement) × leader multiplier + capture
```

- For: the cut follows each building's actual method and staffing, in every building of the shared group, with no new methods. One `building_..._mult` line per control method. It reaches buildings by location, the market's own boundary. The gross stays consumption-based, so pops' heating, ships, throughput and imports still count exactly as now.
- Against: a yearly building sweep per market (the capture value already does three; one more is negligible at a yearly cadence). Abatement is computed at base throughput, so a plant running above 100% throughput is credited for less than it burns, which is conservative. The player sees a per-building gross that is an approximation of the market total, not its parts; §5 phase 2 says how to make that explicit.
- Bonus: synthetic capture moves onto the same type (negative `building_greenhouse_gas_emissions_add` on `pm_synthetic_oil_1/_2` and `pm_synthetic_coal`, from the generator), retiring the hard-coded `-0.06 / -0.036 / -0.168` constants in `market_carbon_capture_script_value`, which today duplicate the PM files by hand and miss throughput the same way.

### C. Replace the consumption sum with buildings (the "ideally" in the request)

Make the gross Σ of `building_greenhouse_gas_emissions_add` over the market's buildings, read through a state-level mirror (`state_greenhouse_gas_emissions_add` in `state_modifiers`, so the yearly read is per state, not per building), plus a term for what no building carries.

- For: every unit of emissions has a visible source; per-state climate damage, a wanted expansion (`mod_systems.md` § Global Warming: climate damage sits on the country today), gets a natural input.
- Against, and why it is not recommended now:
  - **Pops.** Heating's coal and oil is not a building. It would need its own term, either an estimate from pop needs (no script read gives a pop's coal or oil spending) or the residual market consumption − Σ buildings, which absorbs every error below and can go negative.
  - **Throughput and input modifiers.** Workforce scaling ignores them (§3), so the building sum drifts from real burn: Fossil-Fuel Divestment's −5% input would stop cutting emissions, economy of scale would add burn the figure never sees.
  - **Ships**, six coal-burning types, aren't buildings either.
  - **Feedstock.** Petrochemical methods would need their own factor, a balance decision (they are counted as burned today).
  - **194 methods** to generate and keep in step through every vanilla patch.

  C is worth doing only if measurement (§5, phase 0) shows buildings cover nearly all of a market's burn in practice, or if per-state damage needs per-building sources anyway.

## 5. Recommended plan

| Phase | What | Size |
|---|---|---|
| 0 (optional, for C only) | A `te_debug_gw.1` option that logs, per market: consumption gross, Σ of a script estimate of building fuel (level × occupancy × the active method's input, as the capture value does), and the difference (pops, ships, throughput). One save at 1900, 1950, 2000. | small |
| 1 | Option B for the four control buildings. Register the two building types (`common/modifier_type_definitions/global_warming_modifier_types.txt`; not `script_only`, so they show; `color = bad` on the add, `percent = yes` on the mult). Generator (`gen_pm_emissions.py`, or a mode of `pm_costs.py`, which already rewrites PM files in place) writes the add into the fuel methods of Power Plants, Steel Mills, Ports and Automotive Industries, and the mult into Basic and Advanced. `market_greenhouse_gas_emissions_script_value` subtracts the abatement before the leader multiplier, floored at 0. Snapshot it beside `gw_disp_capture` as `gw_disp_abated` and show it as an overview row ("Abated by Emissions Control"); fold it into the Emissions Cut pie (cut = 1 − net / gross). Move synthetic capture onto the add. Player guide ch. 14 (How emissions become warming; State pollution's control-method table). | medium |
| 2 | The add on every fuel method (the generator's scope widens to all ~194), so every building shows its burn. Display only: the gross stays consumption-based. Optionally a Fossil Transition row "Emissions by Industry" from a state-level mirror. | medium |
| 3 | Option C, if phase 0 supports it. | large |

Phase 1 is what the request needs: the control methods cut CO₂, the cut is visible on each building, nothing downstream changes, and the #660 rule holds (no emissions bonus from laws: the cut comes from a method the building pays for).

**Tests to write with phase 1:** the generator's output equals 2 × inputs for every covered method; each control method carries the mult and nothing else new; `market_greenhouse_gas_emissions_script_value` floors at 0 and applies abatement before the leader multiplier; the capture constants are gone. **In-game checks:** both building types render in the building and method tooltips; `modifier:building_greenhouse_gas_emissions_add` reads the staffed value (half-staffed plant, half the figure); abatement shows in the overview after the first January; a foreign-owned plant's abatement lands in the market it burns in.

## 6. Decisions for the owner

1. **Should Basic Emissions Control cut CO₂ at all?** In fiction, scrubbers and filters (Basic) remove soot and sulfur, not carbon. Proposal: Basic −10% (efficiency upgrades that come with the retrofit), Advanced −40% (carbon capture). Alternative: Basic 0%, and Advanced becomes the capture tier in name. Because the ministry forces one of the two everywhere (§2), Basic's figure is effectively a world-wide cut for every ministry holder, so it should stay small.
2. **Cost.** Advanced costs £140 a week per level, about a tenth of a coal plant level's electricity revenue (50 × £30). Real capture costs an energy penalty of a fifth to a third of output. With a CO₂ cut attached, should Advanced take more electricity per level, scaled per building by the generator?
3. **A third tier?** "Carbon Capture and Storage", tech-gated late (no capture technology exists in the mod; Clean Energy Technologies is the nearest), −70% with a large electricity input, would give late-game fossil plants a path short of retirement, a counterpart to #660's phaseout.
4. **Option A instead?** If O(1) reads and a country-level breakdown matter more than proportionality, A works only with the control group split per building (and ideally per fuel). B keeps one group.
5. **Phase 2/3 appetite:** per-building figures on every fuel method (display), and whether per-building gross (C) is wanted for per-state damage.
6. **Coal vs oil factor.** Both weigh 2 today. A generator makes a per-fuel factor a one-line change (coal is more carbon per unit of energy than oil); keep parity unless there is a balance reason.

## 7. Risks

- **Silent no-ops.** An unregistered building type or a mis-scoped `modifier:` read returns 0 without a log line; a generator INJECT into a REPLACEd PM fails silently (§3). The `modifier_visibility_audit` and `mod_structure_audit` catch two of the three; the test above catches the third.
- **Balance.** Abatement makes the ministry's forced Basic method a world-wide cut. With Basic at −10% on the four buildings (roughly power and steel, the bulk of industrial burn), most markets with a ministry lose a few per cent of emissions by default; check against the AI climate tuning (`global_warming_ai_values.txt`) and the UN climate shares.
- **Two displays of one fact.** If phase 2 shows per-building gross while the market total stays consumption-based, the sum of building figures won't equal the market figure. Say so in the tooltip ("at full throughput; the market total also counts homes and ships").
