# Per-Building Greenhouse-Gas Emissions and Carbon Capture: Design

**Status: phases 0–2 implemented; owner confirmed initial engine checks; generated production capture pending regression/balance review (2026-10-03).** Follows issue #660 (Resource Transition), which deliberately left emissions accounting unchanged. The request: make the emissions-control production methods cut CO₂, ideally through a modifier such as `country_emissions_add`, and, if possible, replace the market-wide "sum of coal and oil consumption" with something visible per building. The scoping draft (2026-10-02, PR #663) put six questions to the owner, and two versions of this design put eleven more. §4 records all three rounds of answers, and §5–§7 the design that follows from them. The owner confirmed the initial engine probe checks; §0 records production implementation and the broader coverage requested afterward. Every design question is settled; §10 lists what waits for later.

## 0. Implementation checkpoint

- **Phase 0:** an opt-in, handwritten power-plant probe lives in
  [`../testing/carbon_capture_probe/`](../testing/carbon_capture_probe/README.md).
  It includes instructions, a console event, a state-modifier read, a market
  state sweep, and a historical evidence table. Normal deployments exclude it.
  Its scripts parse offline. The owner's first logs confirm nonzero state
  reads. The owner subsequently confirmed the gating/fallback and mandate checks,
  reported the displayed/logged totals look right, and approved the atmospheric
  removal/policy checks.
- **Factors:** `greenhouse_gas_factors.txt` owns coal (2), oil (1.74) and
  display scale (1000). The generator derives fuel emissions and synthetic
  credits directly from merged recipes; unused per-level compatibility values
  are removed. Synthetic credits enter net industry before policy cuts; DAC
  alone writes atmospheric removal. The capture dashboard row counts DAC only.
- **Steel:** Electric Arc Process uses a delta INJECT; the two mod substitution
  methods are edited in place. Merged recipes read 10 coal and 50/170
  electricity, with unchanged goods cost at base prices.
- **Display:** amount readers and treaty 109's text scale January snapshots by
  1000 and use `|K`; the emissions map reads the raw snapshot. Neither UI path
  runs the annual household sweeps. Synthetic-fuel export credits can make a
  producing market negative while combustion is counted in the importing market;
  only DAC contributes atmospheric removal.
  Separate raw snapshot readers feed shares and temperature; stored snapshots,
  history, AI, thresholds and the console's live world-total calculation keep
  internal units. Chapter 14 and its PDF describe the new figures.
- **Building display (owner's follow-up):** 18 fuel methods across power,
  steel and chemicals now add `building_greenhouse_gas_emissions_add` in their
  workforce-scaled blocks. This includes fuel burned by automation. Vanilla
  methods use generated INJECTs; mod-owned/REPLACEd recipes carry a generated
  field in place. The updated probe subtracts capture from this same visible
  modifier and hides the state credit. Production capture tiers remain pending.
- **Phase 2:** source-capture tiers are generated from every building's PM groups.
  The owner's successful probe checks cleared A′. Coverage expands to 74 building
  types, 71 source groups and 351 tier variants, with explicit feedstock/mobile/
  synthetic-credit exceptions. Process and automation get separate controls,
  avoiding combinatorial gates and covering steel boilers too. See the generated
  `carbon_capture_coverage.md` for the full inventory and exceptions.
  Source capture contributes negative state industrial emissions, counted once
  in the location's market and mirrored as negative building emissions. Managed Fossil Phaseout now requires the era-10
  technology and disallows no capture/Tier I; the existing law-consistency walk
  repairs a held phaseout law without its required technology. Three existing
  shield icons distinguish tiers. Generated production regression remains pending.
- **Fuel netted out of output (2026-10-04):** a recipe-derived figure misses fuel
  that the recipe never lists. Vanilla's Coal Mine takes the coal its machinery
  burns off its *output* instead of listing it as an input, so its Atmospheric
  Engine Pump, Condensing Engine Pump and Steam Donkey showed no emissions while
  the same methods in iron, lead, sulfur and gold mines (10, 15 and 4 coal) did.
  The evidence is in the numbers: the Coal Mine's gross output is 1.25× the Iron
  Mine's (picks and shovels 25/20; every explosive 15/12 to 250/200), its pumps
  come out exactly net of that coal (40 = 1.25×40 − 10; 60 = 1.25×60 − 15), and
  its Steam Donkey outputs −3 coal. `pm_emissions.NETTED_FUEL` names the three
  methods and their burn (10, 15 and 3, the Steam Donkey's being vanilla's own
  −3 rather than the iron mine's 4). Both `recipe_emissions` and the capture
  catalog (`pm_carbon_capture.fuel_recipe`) add it, so the three methods now carry
  the state emissions line the market sum reads and gain capture controls like
  the other mines'. Graphite
  Mines reuse the same groups. A vanilla change that adds an explicit coal input
  to one of them fails the generator instead of counting the coal twice. **A new
  fuel-producing building should list its own fuel burn as an input** (whaling
  stations do, taking oil to make oil); the generator can't see fuel it isn't
  told about. Oil rigs' combustion derricks have no oil input and no sibling to
  show a netted amount, so they are unchanged.
- **Atmospheric removal:** Carbon Conversion Works now unlock with the new
  era-10 Carbon Capture and Storage technology, after Clean Energy Technologies.
  Direct Air Capture is their default PM; Synthetic Coal keeps an era-11
  Genetic Engineering gate. The new PM produces no goods, consumes electricity
  and equipment, and contributes negative workforce-scaled building emissions mirrored as a
  `state_atmospheric_carbon_capture_add` value read once by the market sum. Its capacity is independently configured in coal
  equivalents rather than inferred from nonexistent goods output.
- **Carbon Removal Support:** a ninth climate policy, national, available at
  0.5 °C with Carbon Capture and Storage. Requires subsidies for these works,
  adds 5% throughput, costs 100 Authority and gives the Environmental Movement
  a 5-percentage-point radicalism reduction. Removal still comes from staffed
  buildings; the policy has no direct market emissions multiplier. Its country
  flag survives revolution and rebuilds the journal-entry modifier monthly.

- **Building-driven climate and households (owner follow-up):** annual emissions
  now use generated state mirrors of building fuel emissions minus source
  capture and synthetic output credits, after industrial policy cuts. Atmospheric offsets are separate and
  keep their full credit. Households add a population/average-wealth heating
  estimate from generated buy-package interpolation. Green Building Codes,
  Renewable Investment and Fossil-Fuel Divestment cut this footprint by
  60/25/15%, stacking to zero. The owner clarified that near-zero target is
  households, not all industry. Standalone military fuel and fuel-specific
  input-multiplier adjustments remain outside the custom building mirror.

Resume instructions and validation results are in
[`building_emissions_handoff.md`](building_emissions_handoff.md). Section 1
records the pre-implementation baseline; §5–§9 retain historical design sketches superseded where §0 differs.

### Review corrections and current accounting

Synthetic fuel output credits reduce net industrial emissions before policy cuts;
only removal-only DAC keeps an atmospheric offset afterward. Its capacity is
210 coal-equivalent units (−42 display units per level), at the existing 1,200
electricity and equipment inputs. The household estimate discounts peasants
using their merged consumption coefficient and derives fossil shares from
weighted heating-good market supply, avoiding oil emissions before oil is sold.
State average wealth and baseline dependent needs remain approximations.
Green Building Codes/Renewable Investment/Fossil-Fuel Divestment still stack
60/25/15% to eliminate households. Fuel-input discounts have economic effects
but do not automatically scale custom recipe emissions; standalone military and
ship fuel remains outside the mirror. These limitations are player-facing.

Expanded in-game checks remain required: foreign-owned buildings under phaseout
when the owner lacks CCS, technology tooltip/tree rendering of 114 variants per
tier, mandate electricity prices and repeal/re-enactment churn, and
household/removal January totals. The game rule off still leaves the method
tooltips' emissions lines and costly capture mandates.

### One emissions line (2026-10-04)

The owner's play-test settled the state-line visibility check: a screenshot
listed Greenhouse Gas Emissions (`building_greenhouse_gas_emissions_add`) and
Industrial Greenhouse Gas Emissions (`state_greenhouse_gas_emissions_add`)
together at the same +6.25. The game lists a method's state modifiers alongside
its building ones, and `script_only = yes` hides neither. Vanilla's
modifier types use no field that would hide one (they use only `color`,
`decimals`, `percent`, `boolean`, `script_only`, `prefix`, `suffix`,
`difference_sign` and `game_data`). The building-scoped copy is retired: the
generator strips it (`OBSOLETE_MODIFIERS` in `pm_emissions.py`), its type and
loc are gone, and the state line, renamed Greenhouse Gas Emissions, is the only
display. Direct Air Capture now shows only Atmospheric Carbon Removal. The
accounting reads the same state lines as before. The figure no longer appears
in a building's own modifier list. Whether the state's modifier breakdown lists
it building by building has not been checked in game. Sections 5–9 still
describe the building-scoped display; §0 supersedes them.

## 1. How emissions work today

> Historical design discussion; accounting and implementation status are superseded by §0.

One script value carries the whole system. Everything else reads it.

```
market_greenhouse_gas_emissions_script_value      (common/script_values/extra_script_values.txt)
  = (market oil consumption × 2 + market coal consumption × 2) / 10000
    × gw_emission_multiplier_script_value          (1 + the state owner's modifier:country_greenhouse_gas_emissions_mult, floored at 0)
    + market_carbon_capture_script_value           (negative: synthetic fuel plants, from hard-coded per-level constants)
```

- **Cadence.** Each country's capital's yearly state pulse snapshots `country_greenhouse_gas_emissions_script_value` into `gw_disp_country_emis`, adds it once to the world total and to `gw_disp_country_emis_cum`. Separately, each market capital snapshots the market sum for market overview, maps and UN shares. Both use the same state formula; market membership cannot change a country's cumulative total. Existing country totals start at the next January; no allocation of old market totals.
- **Boundary: consumption in the market.** Whatever the market's buildings and pops burn counts, wherever it was mined; imports count, exports don't. Extraction itself emits nothing. This is why #660's laws earn no emissions cut of their own.
- **Who burns.** About 94 PMs take coal and 100 take oil (`/modifier-search?q=goods_input_coal_add`, `…oil_add`), plus 6 ship types (coal), plus pops: vanilla's `popneed_heating` takes coal (up to 80% of the need) and oil (up to 100%). Some oil is feedstock (plastics, polyester, nylon, dyes), which the formula treats as burned.
- **Cuts.** Each state's owner supplies `country_greenhouse_gas_emissions_mult` (national climate policies, environment ministry, sustainability principle, conventions and summits), floored at zero. Capture retains its own credit. The nine existing climate policies are national; fossil-fuel tariffs alone are market-leader only and add native tariff-rate modifiers, without an emissions multiplier.
- **Synthetic capture.** `market_carbon_capture_script_value` credits Synthetic Fuel Works and Carbon Conversion Works for their *output* (`-0.036` = 180 oil × 2 / 10000 a level, `-0.06` for 300 oil, `-0.168` for 840 coal). On the coal-to-liquids method (180 coal → 180 oil) the credit cancels the plant's own coal, so the carbon counts once, where the fuel is finally burned; the grain and air-capture methods go below zero. The constants copy the PM files and the factor 2 by hand. The panel shows them as "Carbon Captured".
- **Readers.** Market overview, map, History market-share chart and UN shares read `gw_disp_market_emis`. Country Top Emitters and cumulative totals read `gw_disp_country_emis` / `gw_disp_country_emis_cum`. World warming accumulates the latter annual snapshot once per country. The industrial-cut pie reads that displayed country's national multiplier; treaty 109 can bind market members.

## 2. The emissions-control methods today

`pmg_emissions_control` (`common/production_method_groups/extra_pm_groups.txt`) is **one group shared by four buildings**: Power Plants, Steel Mills, Ports and Automotive Industries (`INJECT:` / `REPLACE:` blocks in `common/buildings/extra_buildings.txt`). Its methods (`common/production_methods/extra_pms.txt`) cut only local pollution:

| Method | Unlock | Effect per level (workforce-scaled) | Inputs per level |
|---|---|---|---|
| No Emissions Control | `law_no_ministry_of_the_environment` (so unavailable once the ministry exists) | none | none |
| Basic Emissions Control | Pollution Control | −10 state pollution | 1 tools, 1 electricity (£70) |
| Advanced Emissions Control | `law_ministry_of_the_environment` | −20 state pollution | 2 tools, 2 electricity (£140) |

Because the no-control method needs *no* ministry, establishing the Ministry of the Environment forces every one of these buildings onto Basic or Advanced. Chemical Plants have their own group on the same pattern, `pmg_industrial_synthesis_scrubbing` (No Synthesis Scrubbing / Basic Fume Scrubbers / Closed-Loop Synthesis, the last gated on two of its own fuel methods).

Fuel burned per level at full staffing (mod values, `/production-methods/`):

| Building | Fuel methods (coal / oil per level) |
|---|---|
| Power Plant | Early 5 coal (+5 wood); Coal-Fired 20; Oil-Fired 25 oil; Modern Coal-Fired 25; Modern Oil-Fired 35 oil |
| Steel Mill | every furnace 30 coal, Electric Arc and both substitution processes included; Microgravity Alloying none. Automation boilers +5 or +10 coal |
| Port | Industrial 5 coal; Modern, Container, Global and Magnetic Drive 10 oil; passenger ships +5 |
| Automotive Industry | 5–10 oil, + assembly lines 5 oil |
| Chemical Plant | Nitrogen Fixation 20 oil; Catalytic Cracking 120; Polymerization 160; Automated Reactors 180; Flow Chemistry 220; the first two fertilizer methods and Molecular Foundry none |

## 3. Engine facts the design rests on

- **PM modifier blocks** (`game/common/production_methods/production_methods.md`): `country_modifiers`, `state_modifiers` and `building_modifiers`, each with `workforce_scaled`, `level_scaled` and `unscaled`. Workforce-scaled modifiers follow staffing and throughput (owner correction, consistent with `scripting_best_practices.md`'s scaling table). The earlier claim that throughput was ignored was incorrect. Fuel-specific `goods_input_*_mult` is separate; whether it also adjusts a custom emissions value is not established. The probe records staffing and throughput together.
- **A custom modifier type in a PM, read from script, is shipped practice for countries and buildings.** Country: `country_cultural_pull_add` (university PMs' `country_modifiers.workforce_scaled`, read as `modifier:country_cultural_pull_add`). Building: `b:<type>.modifier:building_annual_<wonder>_progress` (`common/scripted_effects/extra_effects.txt`), and `modifier:building_throughput_add` in `st_res_effects.txt`. State: `state_fortification_level_add` (a mod type, fed by `pm_earthwork_fortifications`' `state_modifiers.workforce_scaled`) has been read by script since 2026-04, in the `weight` of `common/battle_conditions/extra_battle_conditions.txt` (`modifier:state_fortification_level_add >= 1`). A weight's effect is invisible in play, so that the read returns the staffed value is unconfirmed (phase 0, check 1). The `modifier` link takes country, building, state and market scopes (`event_targets.log`).
- **Country modifiers from a PM go to "the country"** (the doc's wording). For government buildings that is the state's owner; for a foreign-owned plant, whether it is the location's owner or the owning country is **unverified**. State modifiers go to the building's state, which is always in the market where its fuel is burned.
- **Hidden, method-gated methods are the mod's practice, not vanilla's.** `is_hidden_when_unavailable = yes` hides a method whose unlock fails; vanilla uses it for technology- and principle-locked variants (`pm_vacuum_canning_principle_3`), and the field is missing from `production_methods.md`. Vanilla gates only five methods on other methods (`pm_bone_china`, `pm_precision_tools` and three more) and never hides those. The mod pairs the two fields in 16 methods: `pm_rail_transport_mine_infrastructure_4` and `pm_construction_principle_2` since 2024, `pm_maintenance_mechanized_mine` and the monument dedications since 2026-09. `unlocking_production_methods` is an **any-of** over methods in the same building's current selection, so a method can follow one group's choice but never two groups' at once.
- **A gated method is dropped when its gate goes.** Vanilla moves a building off a method whose `unlocking_production_methods` no longer holds, provided another method in the group fits (`mod_systems.md` § Maintenance tiers, written for the mine maintenance swap and marked unverified in game there). Which method it lands on (the default, or the first that fits) is undocumented (phase 0, check 3). A law does the same: establishing the ministry moves every building off `pm_no_emissions_control` (§2).
- **`replacement_if_valid = <pm>`** is a single key: the method swaps itself for the named one as soon as that one is valid (vanilla's train and principle variants). It can't carry a choice across a swap in another group.
- **Every method change pays retooling.** The mod's `pm_retooling` override sets `goods_input_construction_mult = 10` while it lasts (`common/static_modifiers/extra_modifiers.txt`).
- **Five decimals.** Script-value literals take at most five decimals (`scripting_best_practices.md`); the engine's fixed point is ×1e5.
- **Negative outputs and same-good loops are shipped.** `pm_tank_production` outputs −20 automobiles from a second group of the same building; Basic Emissions Control on a power plant takes electricity, the plant's own output.
- **The AI picks methods by profit.** `ai_weight` is documented ("base AI weight, default 1.0") and used nowhere in vanilla, so how it weighs against profit is unknown. A method that only costs is never picked voluntarily.
- **Modifiers add; a custom `_mult` scales nothing by itself.** The engine applies only its own pairs. A custom `building_..._mult` is a number script must apply.
- **`INJECT:` sums nested modifier blocks** (confirmed in game for ranks, techs, laws and static modifiers; `scripting_best_practices.md`), and the mod already INJECTs `building_modifiers` into vanilla PMs (`INJECT:pm_market_stalls`). **It silently fails on a mod-only or `REPLACE`d entity**, and many fuel PMs are one or the other (`pm_coal-fired_plant` and `pm_oil-fired_plant` are `REPLACE`d; the modern plants are mod PMs). The fuel-emissions generator therefore amends these definitions in place and INJECTs only into untouched vanilla methods.

## 4. Owner decisions (2026-10-03)

| # | Question | Answer | Where |
|---|---|---|---|
| 1 | Should Basic Emissions Control cut CO₂? | No. CO₂ control gets tiers of its own (25/50%? 25/50/75%? the draft's 40/70%?). | §5.1, §5.3 |
| 2 | Cost | Rough realism at base prices; rebalance base methods if needed. | §5.5, §7 |
| 3 | A third tier? | Yes. | §5.3 |
| 4 | Option A instead? | A is more transparent to players; B has advantages. Could a script generate several reduction methods, each gated by the coal- or oil-burning method? | §5 (yes), §8 |
| 5 | Phase 2/3 appetite | Unsure, given 4. | §9 |
| 6 | Coal vs oil factor | Evaluate it. A unit of coal or oil is an unspecified amount, so infer relative unit size from power plants' electricity per unit. | §6 |

Second round, on this design's first version (2026-10-03):

| Question | Answer | Where |
|---|---|---|
| Tier rates | **25/50/75%** (over the recommended 30/60/90). | §5.3 |
| Tier II technology | A new era-10 technology, Carbon Capture and Storage. | §5.3 |
| Coverage | Power Plants, Steel Mills and Chemical Plants to start; expect to expand. | §5.2 |
| Cost realism | Keep it, though capture-equipped power plants lose money at base prices. | §5.5 |
| Mandate | Managed Fossil Phaseout requires at least the middle tier (50%). | §5.6 |
| Steel furnaces | Yes, 30 → 10 coal; INJECT the vanilla method rather than REPLACE it, so unrelated vanilla changes carry through. | §7 |
| Separate "Captured at Source" panel row | No need. | §5.4 |
| Reference date for the factor calibration | Asked what it meant; explained in §6. | §6, §10 |
| What per-level figure | Asked; explained in §5.4. It is now an in-game check, not a decision. | §5.4 |

Third round (2026-10-03):

| Question | Answer | Where |
|---|---|---|
| Factor calibration | Slower late warming is fine: coal stays at 2, oil becomes 1.74, nothing is renormalised. | §6 |
| Display figure | Scaling the emission units up 1000× is fine if it helps. Adopted, as a display-only scale. | §5.4 |
| Phaseout's technology | (a): Managed Fossil Phaseout's technology becomes Carbon Capture and Storage. | §5.6 |
| Panel | Capture shows only as a lower emissions figure; no row, no tooltip and no pie change. | §5.4 |

Follow-up after the first engine logs (2026-10-03):

- The visible modifier must show **net greenhouse gas emissions per building**:
  fuel methods add emissions and capture methods subtract from the same value.
  The state capture credit becomes script-only accounting data.
- Workforce scaling includes throughput; remove the former approximation claim.
- Household coal/oil use is small enough to omit if that simplifies a future
  building-based total. Alternatively, estimate household use from population
  and average wealth using a hardcoded curve derived from buy packages, with
  appropriate climate policies reducing it. This is a future accounting option;
  the original consumption formula included households directly; the current estimate is described below.

## 5. Design: generated carbon-capture methods (A′)

**Answer to question 4: yes, it is feasible.** A generator writes, for each covered building, one capture method per tier per fuel class. Each method is gated on that fuel class's methods and hidden otherwise. The player sees "No Carbon Capture" and the researched tiers for the fuel the building burns now. Each tier states the absolute cut it makes in this building and pays a cost sized to that fuel. That is option A without its flaw: one flat credit had to fit buildings burning 10 to 80 units a level, and now every method is sized to one burn.

### 5.1 Shape

- **A new group per covered building, `pmg_carbon_capture_<building>`**, next to the unchanged `pmg_emissions_control`. Basic and Advanced stay pollution-only (answer 1). Separating them keeps the ministry's forced pollution choice apart from the capture choice, and keeps the per-fuel variants out of a group four buildings share. In fiction, amine capture needs the flue gas desulphurised first. The any-of gate can't also require Advanced Emissions Control, so that pre-treatment is part of the capture cost.
- **Methods in each group:**
  - `pm_no_carbon_capture_<building>`: the default, free. Disallowed under the mandate (§5.6), as is every Tier I variant.
  - `pm_carbon_capture_na_<building>`: hidden, free, unlocked by the fuel-group methods that burn nothing (Microgravity Alloying; Artificial and Improved Fertilizers, Molecular Foundry). Under the mandate the group then always has a valid method. Power plants need none: every power-plant method burns.
  - `pm_carbon_capture_<tier>_<building>_<class>`: hidden; `unlocking_production_methods` = the methods of one fuel class; `unlocking_technologies` = the tier's technology; carries the cut and the cost.
- **A fuel class** is the set of methods in the building's fuel group with the same coal and oil input. Grouping keeps the tier through a swap between equal burns. After the steel change (§7), Blister, Bessemer and Open Hearth burn 30 coal and Electric Arc and the two substitution processes 10. That is two classes, so an upgrade within either keeps the tier.
- **Example** (Modern Coal-Fired Plant, Tier II, at the current factor 2; figures from §5.5):

```
pm_carbon_capture_2_power_plant_coal25 = {	# AUTO-GENERATED by gen_carbon_capture_pms.py
	texture = "gfx/interface/icons/production_method_icons/carbon_capture_2.dds"
	is_hidden_when_unavailable = yes
	unlocking_technologies = { carbon_capture_and_storage }
	unlocking_production_methods = { pm_modern_coal-fired_plant }
	state_modifiers = {
		workforce_scaled = {
			state_carbon_capture_add = 2.5	# 50% × 25 coal × f_coal / 10 (display units, §5.4)
		}
	}
	building_modifiers = {
		workforce_scaled = {
			building_greenhouse_gas_emissions_add = -2.5 # subtract from the fuel method's +5.0
			goods_output_electricity_add = -12	# rounded design-anchor energy penalty
			goods_input_engines_add = 5
			goods_input_steel_add = 6
			goods_input_fertilizer_add = 7	# solvent make-up ("Chemicals")
		}
	}
}
```

- **Counts.** Power Plant 5 fuel classes, Steel Mill 2, Chemical Plant 5: 36 tier methods, plus 3 "No Carbon Capture" and 2 not-applicable. The groups hold 16, 8 and 17 methods; the player sees at most four.

### 5.2 Which buildings

Capture works on large single stacks, so coverage follows where fuel is burned in one place, not where the most fuel goes. Top of the burn ranking (the most coal + oil per level any method combination burns, mod values):

| Building | Burn / level | Covered | Why |
|---|---|---|---|
| Chemical Plant | up to 220 oil | yes, concentrated class | ammonia and process streams are the cheapest capture there is |
| Synthetic Fuel Works | 180 coal | no | its output is already credited (§1); capturing its stack too would count the carbon twice |
| Synthetic Rubber Works, dyes | 50–100 oil | no | feedstock that ends up in the product |
| Motor Industry | 50 oil or 20 coal | no (config) | small stacks |
| Highway | 50 oil | no | vehicle exhaust |
| Steel Mill | 30 coal, 10 in the electric furnaces after §7 (+10 automation) | yes, flue-gas class | blast-furnace and process gases; no method without coal until Microgravity Alloying |
| Power Plant | 5–35 | yes, flue-gas class | the textbook case |
| Shipyard, Glassworks, Artillery Foundry | 30–35 | no (config) | candidates for wider coverage |
| Port, Automotive Industry | 10–15 | no | ships and assembly lines; they keep pollution control only |
| Company buildings (company steelworks, refineries, power stations) | 10–60 | no | their own PM groups, capped at a level or two |

Coverage is one config table in the generator (building, fuel group, cost class); adding a building is a row. The owner expects to expand it after the first three. The "no (config)" rows are the obvious next candidates, and a company building needs a row naming its own PM group.

### 5.3 Tiers and technologies

| Tier | Name (draft) | Captures | Real anchor | Technology |
|---|---|---|---|---|
| I | Partial Carbon Capture | 25% | a slipstream: Petra Nova (Texas, 2017) captured 90% of a 240 MW slipstream of a coal unit some 2.5 times that size, about a third of the unit's CO₂ | Clean Energy Technologies (era 9), which also unlocks Renewable Energy Plants and Managed Fossil Phaseout |
| II | Carbon Capture and Storage | 50% | first-generation amine on the whole flue, as operated rather than as designed (Boundary Dam 3, 2014, the first power unit captured end to end, was designed for 90%) | era-10 Carbon Capture and Storage (prerequisite Clean Energy Technologies), also used by atmospheric removal |
| III | Advanced Carbon Capture | 75% | second-generation solvents and sorbents, short of the 90%+ they reach on a slipstream (Petra Nova's three-year demonstration ran at 92% of its slipstream) | Modern Material Science (era 11: metal-organic framework sorbents) |

The rates are the owner's (25/50/75 over the recommended 30/60/90): read them as a whole plant's capture as operated, not a capture unit's design rate.

**The energy penalty turns headline rates into lower net cuts**, and the game models it for free. A power plant with capture sells less electricity, and the market makes the shortfall up elsewhere. On a fossil grid that shortfall is burned without capture:

| Plant (fossil grid) | Tier I | Tier II | Tier III |
|---|---|---|---|
| Modern Coal-Fired: capture − penalty = net | 25 − 7 = 18% | 50 − 13 = 37% | 75 − 14 = 61% |
| Coal-Fired | 25 − 11 = 14% | 50 − 18 = 32% | 75 − 20 = 55% |
| Modern Oil-Fired | 25 − 6 = 19% | 50 − 10 = 40% | 75 − 11 = 64% |

On a clean grid, net is the headline. Each tier costs less per tonne than the one before (technology learning, §5.5), so a higher tier is never the worse deal per tonne. Tier III costs about what Tier II does a level and captures half as much again.

### 5.4 Accounting and display

> Historical design discussion; accounting and implementation status are superseded by §0.

- **Visible net emissions:** `building_greenhouse_gas_emissions_add` is building-scoped, `color = bad`, `percent = no`, `decimals = 2`. Every fuel method in a covered building's groups contributes `(coal × factor + oil × factor) / 10` in `building_modifiers.workforce_scaled`. Capture variants contribute the negative cut in the same block. The building therefore shows the sum after capture. The generator derives gross values from merged recipes and shared factors, including automation fuel.
- **Hidden accounting credit:** `state_carbon_capture_add` (`common/modifier_type_definitions/global_warming_modifier_types.txt`; `color = good`; `decimals = 2`; `script_only = yes`). It is state-scoped. A state modifier from a method lands on the building's state, so the cut counts in the market where the fuel burns, whoever owns the building; for country modifiers that is unverified (§3).
- **Display units, 1000× (owner, third round).** Today a capture figure in the panel's units is tiny: one level of a Modern Coal-Fired Plant at Tier II captures 0.0025, against a market shown as, say, 45.3/yr. So every *displayed* emission amount is multiplied by 1000, and the modifier is written in the same units:
  - Gross emissions and capture are fuel × factor / 10 per level, rounded to two decimals by the generator. Modern Coal-Fired adds +5.00 Greenhouse Gas Emissions and Tier II subtracts −2.50, so the building shows 2.50 net per staffed level at base throughput. A 20-level plant at those conditions shows 50 net. The hidden state credit has the same positive captured amount for the market subtraction.
  - The scale is display-only. `global_var:greenhouse_gas_emissions`, the per-market snapshots, temperature, thresholds, the AI values and saves keep their units. Seven display values gain a `multiply = 1000`: `gw_market_emis_display`, `gw_global_emis_display`, `gw_disp_own_emis`, `gw_disp_own_cum`, `gw_disp_captured`, `market_greenhouse_gas_emissions_script_value_display` (treaty 109's text) and the Top Emitters rows. Shares, percentages and temperature are ratios and stay. `gw_emis_world_tt`'s "Every 1,000 a year" becomes "Every million a year".
  - The scaled figures render with the `|K` format (12.3K, 4.2M; `gui_modding_guide.md` § Format Specifiers), which the mod already uses 28 times (`je_colonial_empire_territory_gdp`, for one). That replaces today's `|1` and `|0` on those values, so the panel cells stay as narrow as now.
- **Script:**

```
gross    = (coal consumption × f_coal + oil consumption × f_oil) / 10000
captured = Σ over the market's states of modifier:state_carbon_capture_add / 1000
net      = max(0, gross − captured) × leader multiplier + synthetic capture
```

  `captured` is a yearly sweep, `market → every_scope_country → every_scope_state`, O(states). Verify it reaches exactly the market's states; treaty ports are the edge case.
- **Panel: nothing new (owner).** Capture shows only as a lower emissions figure: Our Market's Emissions, the world total and every reader of the market figure already have it subtracted. The "Carbon Captured" row stays the synthetic plants' alone, and its tooltip stays true: stack capture can't take a market below zero. The Emissions Cut pie stays the policies' cut.
- **Each variant's generated description names its burn**: "Captures 50% of the carbon from this plant's 25 coal a week, per level." The loc is generated before `organize_loc` runs, as `gen_un_button_descs.py` does.
- **Gross and capture follow staffing and throughput.** Both use workforce-scaled blocks; do not apply occupancy again when reading their modifiers. Fuel-specific input reductions need separate verification. The market floor at 0 catches any capture-credit overshoot.

### 5.5 Cost (answer 2)

**Method.** Take real per-tonne costs by sector and tier, then convert them to game units through the power plant.

- **Electricity is the anchor.** One unit at the £30 base price stands for one MWh at about $65 (coal power's cost), so £1 ≈ $2.17. The power plant is a fair anchor: coal is 28–40% of the Coal-Fired and Modern Coal-Fired plants' output value in game, against about a third of a real coal plant's cost. Fuel is not: game oil costs 1.33 × coal for 1.12 × its energy, where real oil costs several times coal per unit of energy. So costs are pinned to electricity, not to fuel prices.
- **CO₂ per fuel unit** (§6): one coal ≈ 3.07 t-units, one oil ≈ 2.64.

Per-tonne anchors (real, approximate):

| Class | Tier I | Tier II | Tier III | Basis |
|---|---|---|---|---|
| Flue gas (power, steel) | $90/t, 0.35 MWh/t | $65/t, 0.30 MWh/t | $45/t, 0.22 MWh/t | IEA levelised capture cost by sector: power roughly $50–100/t. Retrofit studies: 90% capture costs a coal plant about 9 points of efficiency, a fifth to a quarter of output. The first projects (Petra Nova, Boundary Dam) cost more; the US DOE's target for the 2030s is about $30/t. |
| Concentrated (chemicals) | $35/t, 0.12 MWh/t | $25/t, 0.12 MWh/t | $20/t, 0.10 MWh/t | IEA: $15–25/t for ammonia, gas processing and ethanol. The stream is nearly pure, so compression is the only energy. |

Cost per fuel unit captured: electricity for the energy share, and goods at base prices for the rest (capital, operation, transport and storage):

| Class | Tier | Per coal unit | Per oil unit |
|---|---|---|---|
| Flue gas | I | 1.07 electricity + £95 | 0.92 + £82 |
| Flue gas | II | 0.92 + £64 | 0.79 + £55 |
| Flue gas | III | 0.67 + £43 | 0.58 + £37 |
| Concentrated | I | — | 0.32 + £33 |
| Concentrated | II | — | 0.32 + £21 |
| Concentrated | III | — | 0.26 + £16 |

Per level (power plants lose output; other buildings buy electricity):

| Building, method | Tier I | Tier II | Tier III |
|---|---|---|---|
| Power: Modern Coal-Fired (25 coal → 90; £2,700) | −7 electricity, £595 goods: 29% of revenue | −11, £805: 43% | −13, £814: 44% |
| Power: Coal-Fired (20 coal → 50; £1,500) | −5, £476: 42% | −9, £644: 61% | −10, £651: 64% |
| Power: Modern Oil-Fired (35 oil → 140; £4,200) | −8, £717: 23% | −14, £970: 33% | −15, £981: 34% |
| Steel Mill, electric furnaces after §7 (10 coal; £7,500–15,000) | +3 electricity, £238: 2–4% | +5, £322: 3–6% | +5, £326: 3–6% |
| Steel Mill, early furnaces (30 coal; £3,250–6,000) | +8, £714: 16–29% | +14, £965: 23–42% | +15, £977: 24–44% |
| Chemical Plant, Flow Chemistry (220 oil; £33,000) | +17, £1,822: 7% | +35, £2,304: 10% | +44, £2,713: 12% |

Against the real world: coal power with 90% capture costs about 55–75% more per MWh; here Tier III captures 75% for 44% more, the same per tonne. A Petra Nova-style slipstream adds about 40% for a third of the CO₂; Tier I adds 29% for a quarter. Ammonia capture adds 5–10% to the product; this design adds 7–12%, a little higher because the game counts all the chemical oil as burned. Capture adds 10–15% to steel. This design adds 3–6% to the electric furnaces, which burn little after §7, and more to the early furnaces, which are obsolete by era 9.

**Goods for the non-energy part** (generator constants, rounded to whole units):
- Flue gas: 40% engines (blowers, compressors, pumps), 35% steel (columns, pipelines, wells), 25% chemicals (the `fertilizer` good, for solvent make-up).
- Concentrated: 60% engines, 40% steel.
- Not the construction good: the mod scales it by up to ×11 with GDP per capita, so capture's cost would differ wildly between countries.

**The consequence, plainly.** A Modern Coal-Fired Plant's goods margin is £1,250 a level, 46% of its revenue, and its 1,000 workers come out of that: its own annotation gives a wage breakeven of 1.25 a worker. Tier I cuts that to 0.45, Tier II to 0.10 and Tier III to 0.06, and the mandate's floor is Tier II (§5.6). So a mandated plant runs at a loss at base prices until electricity prices rise or the state subsidises it. With capture it spends £24–29 of goods per electricity, against £13 for a Renewable Energy Plant (unlocked by the same technology as Tier I) and £8 for its advanced method (era 11). No one will fit capture to a power plant for profit. That matches the real world, where capture survives on mandates and credits (the US 45Q credit pays $85 a tonne stored). Steel and chemicals feel it far less (3–12% on their era-9 methods), and have no clean method until eras 11–12, so that is where capture earns its place. The owner keeps these costs (second round, §4).

### 5.6 Adoption

- **Players** fit a tier any time after its technology. Vanilla building subsidies play the part of 45Q.
- **AI** never fits capture voluntarily (§3). **Mandate at Tier II (owner):** `law_managed_fossil_phaseout` goes in the `disallowing_laws` of every `pm_no_carbon_capture_*` and every Tier I variant. The engine then moves each covered building onto a valid method, as the ministry does for pollution control. The AI will take Tier II, the cheapest method left.
  - **Invariant: no one can hold the phaseout without Tier II's technology**, or a mandated building has no valid method in its group, and what the engine does then is unknown. The phaseout's technology today is Clean Energy Technologies (era 9), Tier I's. Two ways to keep the invariant:
    - **Chosen (owner, third round):** the phaseout's technology becomes Carbon Capture and Storage, which requires Clean Energy Technologies. That keeps #660's one technology per law and moves the law an era later, to era 10, about the 2010s, when real coal phaseouts began (the UK's was announced in 2015). The phaseout's description and the player guide's Resource Transition section name the new technology.
    - **Rejected:** keeping Clean Energy Technologies and adding `has_technology_researched = carbon_capture_and_storage` to `can_enact`. `can_enact` is checked only at enactment, so a country already holding the law would strand its buildings.
    - **Old saves:** a country that enacted the phaseout under Clean Energy Technologies and lacks the new technology hits the stranded case. Check what `gen_law_consistency` does with a held law whose technology is missing; if it does nothing, it gains that case and drops the law back to the moratorium.
  - The not-applicable method stays outside the mandate, so a building on a method that burns nothing always has a valid one.
  - In fiction, whatever a phaseout keeps burning, it captures.
  - The Fossil Expansion Moratorium can't carry the mandate: it needs only Environmental Movement (era 8), before any tier exists.

### 5.7 Known limits

1. **A fuel swap to another class resets the tier.** Vanilla drops the variant and the building lands on another method (§3). Capture arrives in era 9, after the last power-plant fuel upgrade (the modern plants, era 7) and after steel's move from 30-coal to 10-coal furnaces (Electric Arc, era 4). So in practice it bites the Chemical Plant: Automated Reactors (era 8) to Flow Chemistry (era 9). Under the mandate, the building lands on a valid tier rather than on "No Carbon Capture" (phase 0, check 3). A generator knob can bucket nearby classes, crediting each bucket at its lowest burn, to trade precision for fewer resets.
2. **Only the fuel group drives the variant** (any-of, §3). Steel's automation boilers (5–10 coal) and the like are not captured.
3. **Hidden until researched.** A tier the country lacks can't be previewed in the building; the technology's tooltip shows it. That tooltip may list the same name once per fuel class (12 times for Tier I). If it does, name variants by fuel: "Partial Carbon Capture (Coal)".
4. **41 generated methods** to keep in step with vanilla. The regenerator does that on every reload.

## 6. Coal vs oil factor (answer 6)

Electricity per unit of fuel (power plant, mod values):

| Pair | Coal | Oil | Oil ÷ coal |
|---|---|---|---|
| Coal-Fired (Steam Turbine, era 4) / Oil-Fired (Oil Turbine, era 5) | 20 → 50: 2.5 | 25 → 80: 3.2 | 1.28 |
| Modern Coal-Fired / Modern Oil-Fired (both Modern Urban Planning, era 7) | 25 → 90: 3.6 | 35 → 140: 4.0 | 1.11 |

The modern pair shares a technology, so it separates fuel from plant vintage. The first pair also contains an era of progress: the coal ladder gains 44% over three eras (2.5 → 3.6), 13% an era, and dividing that out of 1.28 leaves 1.13. **Both pairs agree that an oil unit holds about 1.12 times a coal unit's energy**, assuming equal plant efficiency within an era.

Carbon per unit of energy (IPCC 2006 defaults): bituminous coal 94.6 kg CO₂/GJ, crude oil 73.3 (residual fuel oil 77.4, diesel 74.1, natural gas 56.1). Per unit, oil ÷ coal = 1.11–1.13 × 0.775 = **0.86–0.88. Use 0.87.** At a 40%-efficient modern plant, one coal unit is 9 thermal MWh-units, or 3.07 t-units of CO₂; one oil unit is 2.64.

- **Caveats.** If "oil" also stands for natural gas (the mod has no gas good) and the modern oil plant is in fact a combined cycle (about 55% efficient against coal's 40%), the ratio falls to about 0.5–0.6. 0.87 assumes liquid fuel. Feedstock oil still counts as burned.
- **Calibration: none (owner, third round).** With coal at 2 and oil at 1.74, the same world burning the same fuel emits less, mostly late in the game when oil dominates, so warming arrives later than today. The owner accepts that: no renormalisation, so nothing needs measuring. (Renormalising would have raised both weights to hold the temperature at a chosen year.)
- **One source.** Two script values, `gw_emission_factor_coal` and `gw_emission_factor_oil`, read by the market formula and by the generator, which also writes the capture values and the three synthetic constants from them.
- **A balance change to flag.** With synthetic oil credited at the oil factor, a coal-to-liquids plant (180 coal → 180 oil) stops netting to zero. At 2 / 1.74 it keeps 360 − 313 = 47 raw units a level, about 13% of its coal's carbon. Real coal-to-liquids plants are among the largest point sources there are.

## 7. Base methods (answer 2: "rebalance if needed")

- **Power plants: fine as the anchor** (§5.5). Oil plants' fuel share (33–42% of output value) is below real oil-fired generation's because game oil is cheap; that is a global price question, not this design's.
- **Steel: rebalance agreed (owner, second round).** Every furnace burns 30 coal today, Electric Arc and both substitution processes included. A real electric arc furnace uses a tenth or less of the blast-furnace route's carbon, and running on scrap and power is how steel actually decarbonises.
  - **Change:** Electric Arc, Aluminum Substitution and Chromium Substitution go from 30 to 10 coal and take 20 more electricity a level (Electric Arc 30 → 50, the substitutions 150 → 170). That is £600 of coal swapped for £600 of power, so profit is unchanged.
  - **How:** `pm_electric_arc_process` is vanilla and untouched by the mod, so it takes an `INJECT:` carrying only the deltas (`goods_input_coal_add = -20`, `goods_input_electricity_add = 20` in `building_modifiers.workforce_scaled`). A vanilla change to anything else in the method then carries through with no re-diff. The mod has relied on the same shape, a delta INJECTed onto a key the PM already holds, since 2026-01: `INJECT:pm_market_stalls` adds −1,000 laborers to vanilla's 3,500, and a last-wins merge would show as negative employment. `paradox_file_parser._inject_value` sums numbers the same way, so the generator reads the merged 10 coal. `pm_aluminum_substitution` and `pm_chromium_substitution` are the mod's own methods, so they are edited in place (an INJECT would be dropped, §3). Tell in game: the arc furnace's tooltip shows 10 coal and 50 electricity.
  - **Effects:** late steel emits a third as much, the case for steel capture narrows, and coal demand falls; watch coal mines' profitability. Steel has two fuel classes (30 and 10), but the upgrade between them (era 4) comes long before capture (§5.7).
- **Chemical Plant:** all its oil counts as burned, though much of it is feedstock (§1). Left as it is: capture fractions apply to the formula's own count.
- **Pollution control** (Basic £70, Advanced £140 a level, flat across four buildings) is out of scope by answer 1. Real scrubbers and NOx control cost a coal plant roughly a tenth to a fifth of its output's value, so Advanced is cheap on a power plant and dear on a port. The same generator could size it per building later.

## 8. Alternatives considered

> Historical design discussion; accounting and implementation status are superseded by §0.

### B. Building-level gross and a percentage cut (the draft's recommendation)

The fuel methods carry a generated `building_greenhouse_gas_emissions_add` (2 × their coal and oil, written into vanilla, mod and `REPLACE`d PMs by three different routes, §3). The tier methods carry `building_carbon_capture_mult` (−25/−50/−75%), and a yearly building sweep multiplies the two. B's cost can follow fuel too: put the energy penalty on the tier method as `goods_output_electricity_mult` (power) or as an electricity input, and the non-energy part as one figure per building and tier. With that, the real differences are:

| | A′ (this design) | B |
|---|---|---|
| What the method shows | the absolute cut in this building | a percentage; the building shows its gross |
| Across a fuel swap | the tier resets (rarely, §5.7) | the tier is kept |
| Non-energy cost | sized to the burn | one figure per building and tier |
| Methods | 41 generated, new only | 3 per building, plus adds on every fuel method of the covered buildings |
| Script read | per state, one modifier | per building, add × mult |

**B is the fallback** if the hidden variants misbehave in phase 0 (check 3), or if the tier reset proves a nuisance in play.

### C. Replace the consumption sum with buildings

Make the market's gross Σ of a per-building add, read through a state mirror. Every unit of emissions would then have a visible source, and per-state climate damage would get an input. It is parked for the scoping's reasons, which still stand:

- Pops' heating is not a building; the owner accepts omission or a population/wealth estimate derived from buy packages with policy reductions.
- Workforce scaling includes throughput; fuel-specific input modifiers still need verification before claiming an exact match to consumption.
- Ships are not buildings.
- Feedstock needs its own factor.
- About 194 methods would have to be kept in step.

## 9. Plan

> Historical design discussion; accounting and implementation status are superseded by §0.

| Phase | What | Size |
|---|---|---|
| 0 | **Engine checks**, on a test branch with one hand-written variant: (1) `modifier:state_carbon_capture_add` read from a script value in state scope returns the staffed value (a half-staffed plant gives half); (2) whether the PM tooltip shows the state modifier per level or per building, and at which `decimals`; (3) where a building lands when a fuel swap invalidates its variant, with and without the mandate law, and that a law-disallowed "No Carbon Capture" swaps by itself. | small |
| 1 | **Factors, steel and display units:** the two script values (2 and 1.74), the market formula and regenerated synthetic constants; the steel furnace change (§7); the 1000× display scale (§5.4). The first two move world emissions, so they land and get judged before capture adds its own shift. Player guide ch. 14 for the new figures. | small |
| 2 | **Capture (A′):** the modifier type; `gen_carbon_capture_pms.py` (config: buildings, fuel group, cost class; tiers; goods mix) writing methods, groups and loc; the groups added to the three buildings; the Carbon Capture and Storage technology and its tech-tree place; three tier icons; the market formula; the Tier II mandate and the phaseout's technology (§5.6); player guide ch. 14 (How emissions become warming; the control-method table; Resource Transition's law requirements). | medium–large |
| display checkpoint | **Owner's follow-up:** visible gross fuel contributions and negative capture contributions form net emissions per building. Implemented for the three covered buildings (18 fuel methods); probe capture uses the same visible modifier. | small |
| later | Building-sum market accounting (C), household omission or a buy-package/wealth estimate, and emissions display across all fuel-burning buildings. Current market consumption remains authoritative. | — |

**Phase 2 hygiene:**
- The new regenerator goes in `POST_LOAD_REGENERATORS` and the two docs rosters, or `check_post_load_rosters.py` fails CI.
- Its output carries the AUTO-GENERATED header and comes out tab-formatted.
- It gets an ownership row in `docs/auto_generated_files.md`.
- It runs before `organize_loc`.

**Tests (phase 2):**
- Every fuel method of a covered building has exactly one variant per tier or unlocks the not-applicable method.
- Each variant's capture = tier × (coal × f_coal + oil × f_oil) / 10 to two decimals, with the factors read from the script values, and the market formula divides the sum by 1000.
- Costs match §5.5 within rounding.
- Every "No Carbon Capture" and every Tier I variant carries the mandate law, no not-applicable method does, and Managed Fossil Phaseout can't be held without Tier II's technology.
- The arc furnace merges to 10 coal and 50 electricity, and the substitution processes read 10 coal.
- The market formula floors at 0 and subtracts capture before the leader multiplier.
- No hard-coded synthetic constant remains.

**In-game checks:**
- The group shows only the current fuel's researched tiers.
- A new building and an old save's building both start on "No Carbon Capture".
- The mandate moves AI buildings onto Tier II.
- The method tooltip's capture line: per level or for the building.
- How the technology tooltip lists the variants.
- The negative electricity output under throughput modifiers.
- A foreign-owned plant's capture counts in the market where it burns.
- Whose law the mandate's `disallowing_laws` reads on a foreign-owned building: the owner's or the location's. That decides how far the mandate reaches.

## 10. Open items

None: every design question is settled (§4).

Later, not now: which buildings to cover after the first three (§5.2).

## 11. Risks

- **Silent zeros.** An unregistered type, a `modifier:` read in the wrong scope, or an unlock list naming another building's methods returns 0 or hides a method without a log line. `modifier_visibility_audit` and `mod_structure_audit` catch the first; phase 0 and the tests catch the rest.
- **Balance.** The mandate is a cost on every Managed Fossil Phaseout holder's power, steel and chemicals. Check it against the AI climate tuning (`global_warming_ai_values.txt`, `resource_transition_values.txt`), since the AI may now resist the phaseout harder, and against the UN climate shares.
- **The factor change moves every reader.** World emissions, temperature pacing, treaty 109's leader and the UN shares all shift with f_oil (§6); phase 1 lands on its own so the shift can be judged before capture adds a second one.
