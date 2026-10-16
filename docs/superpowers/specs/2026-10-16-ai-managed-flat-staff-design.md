# AI-managed production methods: flat human staff

Status: investigation, with a prototype on one method (`pm_ai_managed_fab`). Owner calls are at the end.

## The question

There are ten `pm_ai_managed_*` automation methods: nine unlock with era 12's `artificial_intelligence`, and `pm_ai_managed_power_plant` with Smart Grids (era 11). How do they scale employment, and can they hire a fixed crew per building (unscaled) instead of a per-level workforce, within what Victoria 3's building script allows? If not, what is the closest thing that works?

## How they scale today

Each is an automation-group method. Its only employment lever is a **negative `level_scaled` add**, which subtracts from whatever the building's base method employs per level. The cut is sized to the lowest base method in the building, minus 10 engineers, so a building keeps a nominal 10 engineers a level (never zero) on that base. The goods it adds (robotics, electricity, digital access, …) are `workforce_scaled`.

Per-level employment with the AI method selected, over every valid combination (one method per group, honouring `unlocking_production_methods`; a scratch enumeration over the same parse `pm_employment_audit` uses):

| Bucket | Buildings (method) | Left per level |
|---|---|---|
| Exact | Power Plant and Renewable Energy Plant (`…power_plant`), Arms Industry (`…arms_industry`), Chemical Plant and the eleven Synthetics Plants other than opium (`…chemical_plant`), Explosives Factory (`…explosives_factory`), the Wired and Wireless Telecommunications, Consumer Appliance, Electronic Components and Semiconductor, and Robotics industries (`…fab`) | 10 engineers in every combination |
| Depends on the base | Furniture Manufactory, Textile Mill | 10 engineers + 0 to 2,000 shopkeepers |
| | Motor Industry, Tooling Workshop | 10 engineers + 0 or 250 shopkeepers |
| | Munition Plant | 10 engineers + 0 or 500 shopkeepers |
| | Synthetics Plant (opium) | 10 engineers + 0 or 1,500 laborers |
| | Fusion Plant, Nuclear Plant (`…power_plant`) | 10 engineers + 100 academics |
| Shared cut too small | Artillery Foundry (shares `…arms_industry`) | 260 engineers, 250 machinists, 500 shopkeepers |
| | Hydro Plant (shares `…power_plant`) | 1,410 engineers, 2,000 laborers, 1,100 machinists |

That is 21 buildings in the Exact row and ten with a residual.

So an AI-managed building's staff still grows with its level: 10 a level at best, and up to 110 to 4,510 a level where a richer base method's workforce survives the cut. A 50-level fab employs 500 people, and a 50-level textile mill on a rich base employs up to 100,000.

The other `artificial_intelligence` methods (`pm_ai_governance`, `pm_automated_labs`, `pm_robotic_service_providers`, `pm_self_improving_AI_systems`, `pm_artificial_personalities`, `pm_ai_optimized_operations`, `pm_self_optimizing_production`, `pm_automated_ocean_mine`) are outside this question. They are partial automation of government, universities, urban centres and the like, and keep real workforces by design.

## What the building script allows

1. **A method's modifiers come in three blocks.** `level_scaled` (× level), `workforce_scaled` (× level × the staffed share × throughput) and `unscaled` (once per building). Employment goes in `level_scaled` or `unscaled`; it can't scale with the staffed share of itself.
2. **An automation method can only add or subtract.** It can't replace the base method's workforce. To reach a flat staff it has to cancel the base method's per-level workforce exactly, profession by profession. A cut sized to the lowest base leaves a residual on richer bases (the middle rows above). A cut sized larger goes negative on the lowest, which `pm_employment_audit` fails in CI. That is why the cuts are sized as they are.
3. **`unscaled` employment is a shipped pattern.** The Grand Monument dedication methods hire a caretaker staff of 200 laborers and 50 clerks in `unscaled` (`grand_monument_pms.txt`, since #541). Monuments produce no goods, though. Nothing in the mod or vanilla yet shows a building whose whole workforce is `unscaled` while its goods are `workforce_scaled`, and no play-test has read whether the monuments' staff is counted once a building or once a level. The prototype's staff self-check reads it.
4. **Output still scales with level when the crew is flat.** `workforce_scaled` multiplies by level × the staffed share (`scripting_best_practices.md` § Production Method Modifier Scaling Blocks). A fixed crew, fully hired, is a staffed share of 1, so every level still produces. That is how the engine is documented to behave; the prototype's output self-check reads it.
5. **`building_employment_<pop>_mult` exists** in the engine's modifier list for every profession, and the mod registers several. Vanilla never uses it. It does use the building-group form, `building_group_bg_oil_extraction_employee_mult = 0.5`, in the oil-rush state modifiers. A building's own `_mult = -1` in a method's `unscaled` block could zero a profession whatever the base method. Whether it also cuts the same profession's `unscaled` add is unknown.

## Options

- **A. Keep 10 a level.** Nothing to verify. Staff still scales, and the residual rows stay as they are.
- **B. Exact cancel plus an unscaled crew.** Raise the cut by the 10 engineers, so the per-level workforce nets to zero, and add `unscaled = { building_employment_engineers_add = N }`. This works today for the Exact bucket. The other ten buildings need either a per-base split of the AI method (as `pm_ai_managed_explosives_factory` was split from the chemical-plant method) or a residual left in place. Its engine unknowns are points 3 and 4.
- **C. Cancel by multiplier.** `unscaled = { building_employment_<pop>_mult = -1 }` for each base profession, with the crew in a profession no base method in those buildings employs (academics), since the multiplier may cut an unscaled add of its own profession. One method then fits every base method, with no splits and no residual. It carries two engine unknowns (points 4 and 5), and a staff of academics where engineers read better.

**Recommendation: B**, proven on one method, then rolled out to the Exact bucket. Choose between splitting and C for the other ten only once B's self-checks read OK, since C rests on the same questions.

## The prototype (this branch)

`pm_ai_managed_fab` (the five fab industries in the Exact row; every base method employs 4,500 a level, so the cancel is exact):

- `level_scaled` engineers −1,990 → −2,000: zero a level on every base.
- `unscaled = { building_employment_engineers_add = 1000 }`: 1,000 (owner, 2026-10-16: the game hires small groups unevenly, so a larger crew is safer than the Grand Monument caretakers' 250). It breaks even with today's 10 a level at level 100. The point is not the headcount: with a fixed crew, a building's level is no longer limited by the population available to staff it, so an era 12 economy can build as many levels as it can afford. Buildings past level 100 are common by then (owner, 2026-10-16).
- Self-checks (`common/on_actions/te_aipm_selfcheck_on_actions.txt`), once a game each, on a fab building of level 5 or more on the method:
  - `ai_managed_flat_staff` (point 3) reads its engineer slots. About 1,000 is OK. About 1,000 × level means `unscaled` employment is read per level; 0 means it isn't summed (or the read failed: confirm in the panel).
  - `ai_managed_flat_output` (point 4) waits until such a building is 90% staffed and reads its robotics input per level (4 a level from this method alone, × throughput). 2 to 20 is OK; under 2 means goods don't follow the levels.
  - Fallback for either: restore −1,990 and drop the `unscaled` block. Rows in `docs/testing/ai-managed-flat-staff-playtest.md`.
- The method's generated `# Employment:` line (`pm_costs.py`) reads −4,500, the per-level cut alone; the flat 1,000 isn't in it. `pm_employment_audit` buckets by block and passes: the level bucket nets to 0, the unscaled one is +1,000.

## Rollout to the Exact row

The other four methods behind the Exact row take the same change: `pm_ai_managed_building_arms_industry` (engineers −740 → −750), `pm_ai_managed_chemical_plant` and `pm_ai_managed_explosives_factory` (−1,990 → −2,000) and `pm_ai_managed_power_plant` (−90 → −100), each with the 1,000-engineer `unscaled` crew. All 21 buildings in the Exact row then employ the crew alone. Merge once the fab self-checks read OK; they test the same engine facts.

## The residual buildings (owner, 2026-10-16)

Seven residual buildings are split by base method, so each copy cancels exactly; every copy is hidden when unavailable, so a building shows one AI-managed option, and carries the same crew. In a save, a building already running the old method on a base that the method no longer lists may lose it, and then needs the AI-managed option picked again (unread: the game's handling of a method that became invalid).

| Building | New method | Its bases | Narrowed method keeps |
|---|---|---|---|
| Artillery Foundry | `pm_ai_managed_building_artillery_foundry` | the four artillery bases | `…arms_industry`: the three small-arms bases |
| Motor Industry | `pm_ai_managed_building_motor_industry_turbine` (+250 shopkeepers cut) | Gas Turbine Engines | the three later engines |
| Tooling Workshop | `pm_ai_managed_building_tooling_workshop_handling` (+250 shopkeepers cut) | Material Handling Equipment, Electrochemical Machining | Industrial Robotics, Nanobot Assemblers |
| Munition Plant | `pm_ai_managed_building_munition_plant_shells` (+500 shopkeepers cut) | Explosive Shells | the five later munitions |
| Fusion and Nuclear plants | `pm_ai_managed_power_plant_reactor` (+100 academics cut) | the three fusion bases and the nuclear base | `…power_plant`: the five fossil and two renewable bases |
| Hydro Plant | `pm_ai_managed_power_plant_hydro` | the hydro base | (same) |

`pm_ai_managed_power_plant` had no base list before; it now names its seven bases, so a new power base needs adding there to get AI management.

**Left as they are.** Furniture Manufactory and Textile Mill keep their luxury and branding shopkeepers (up to 1,500 a level from those groups, plus the base's 500) and their 10 engineers a level: the owner chose to keep that staff human. Opium Synthetics on Alkaloid Extraction keeps 1,500 laborers a level on top of the crew; splitting it needs its own automation group or a 43-method base list on the shared chemical method, and a later pharma base clears it.

## Economic side effects to watch

The output a level is unchanged; only the people change. The per-worker figures behave as they do on a heavily automated base today:
- Wages: few, very productive workers. The building's earnings per employee rise, and the AI's construction scoring reads it.
- The engineer qualification pool: 1,000 engineers a fab building, against 10 a level before.
- Dividends: unchanged in total; the owners keep what wages no longer take.

## Owner calls

1. Crew size: settled at 1,000 engineers (owner, 2026-10-16).
2. Roll out B to the other 16 buildings in the Exact row: built as a draft (owner, 2026-10-16), to merge once both self-checks read OK.
3. The ten buildings with a residual: seven split, Furniture, Textile and Opium on Alkaloid Extraction left as they are (owner, 2026-10-16).
