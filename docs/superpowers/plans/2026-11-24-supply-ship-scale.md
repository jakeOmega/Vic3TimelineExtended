# Supply ships at ten times the size (#1984): scope and plan

Written 2026-11-24 for issue #1984, which offers two fixes for the time controls' ship construction readout. That readout is about half the 2030 week (`docs/audits/late_game_performance.md` § "The USA of 2030"). This plan scopes the first fix, which the owner prefers. In it each supply ship costs ten times as much and every requirement for supply ships is a tenth, from the start of a game.

**Status (2026-11-24).** A quick fix went first, in the PR that added this plan. Naval Convoy Defense (era 6) adds `country_supply_ship_construction_progress_max_add = 20`, which raises a supply ship's weekly cap from 5 to 25, its cost. So a ship is built in one week and a fifth as many are in progress. The add sits on a late technology rather than `base_values`, so the early game keeps vanilla's pace (owner). The readout reads only the player's own queue, and the slowdown is a late-game one. `test_supply_ship_progress_cap.py` holds it to vanilla's type, and `docs/testing/perf-fixes-playtest.md` has its checks. The rest of this plan is the follow-up, if the quick fix's timing shows it isn't enough.

## Verdict

The rescale's script is small: one type, three armor modules and three defines (Stage 2). Two things still need the owner's machine:

1. **It is unproven that either fix moves the readout.** The issue leaves two things open: which call costs it, and whether the cost scales with supply ships or with the fleet. If it scales with warships, neither the quick fix nor the rescale helps.
2. **Running games break.** No trigger or script value reads a country's pool, so script can't divide a save's pool by ten. Stage 4 covers that. The quick fix has no such problem: it changes only how fast a ship is built.

The defines were read from the 1.15.2 files the owner supplied on 2026-11-24 (Stage 2). No define sets a supply ship's cap, limits the queue, counts ships per battalion or per invasion, or sets a starting pool.

## What the readout walks, and why the cost alone won't shorten it

Read from the 1977 save (`late_game_performance.md` § "The step of April 1976"). 59,189 points went to 17,236 supply ships under construction, 11,753 of them part built. That is 5.04 points a part-built ship, which is the type's own cap, `ship_construction_progress_max_add = 5` (vanilla `ship_type_supply_ship`). The other 5,483 entries waited unstarted. So the number in progress is the points allocated over the lower of the cap and the cost. The cost and the cap together set how many weeks a ship takes.

- Today, cost 25 and cap 5: five weeks a ship, points ÷ 5 in progress.
- The quick fix, cost 25 and cap 25: one week a ship, points ÷ 25 in progress, a fifth of today. A cap above the cost buys nothing more.
- Cost 250 and cap 5: 50 weeks a ship, and the same number in progress. A dearer ship alone does nothing for #1984.
- Cost 250 and cap 50: five weeks a ship, points ÷ 50 in progress, a tenth of today.
- Cost 250 and cap 250, with the late technology's add raised to match: one week a ship, points ÷ 250 in progress, a fiftieth of today. This is the most the rescale can do for the readout.

Throughput isn't set by the cap. The yards queue more entries than they can progress (the 5,483 unstarted), so ships a week stay the allocated points over the cost. What decides how many unstarted entries the engine queues hasn't been read.

## Stage 0: time the quick fix, then decide (owner's machine)

**0a. The defines:** read (Stage 2).

**0b. Read the 2030 save.** For the United States, count the entries in `ship_construction_manager > supply_ship_entries_database` against its warships and warship constructions. Record how many entries are started and the supply ship level. If supply ship entries outnumber warships and their constructions by an order of magnitude, that already points to the owner's guess before any timing.

**0c. Time the quick fix** on the same save with `run_variant.sh` and `main` deployed, from the second week (the old entries finish in the first), against 23.4 s (baseline) and 12.4 s (the readout replaced by a constant). If it moves less than expected, split the readout's two calls, each variant an `--add-mod` folder of vanilla's `gui/timemanip.gui` as in the issue:

| Variant | Change | What it settles |
|---|---|---|
| V1 | the readout with `[Country.GetShipConstruction\|0]` replaced by `0` | whether the usage call is the cost |
| V2 | the same with `[Country.GetShipConstructionUsage\|0]` replaced by `0` | whether the total is the cost |

The gate:

- **The week falls to near 12.4 s:** #1984 is fixed. The rescale is then only for its other effects, which the owner wants, and Stages 1–5 can wait.
- **It falls, but not far enough:** the cost follows supply ships in progress. Stages 1–5 cut them to a tenth or a fiftieth of today's (above).
- **It doesn't move:** the cost follows the fleet, or the unstarted entries. Neither the quick fix nor the rescale fixes #1984. Fix it with option 2 (the readout in its tooltip), which needs vanilla's whole `gui/timemanip.gui`; that file isn't in `test_fixtures/vanilla_gui/`.

## Stage 1: the type and its modules (script; buildable offline)

`REPLACE:ship_type_supply_ship` in `common/ship_types/extra_ship_types.txt`. A `REPLACE:` takes on a ship type, which was probed on 2026-11-14 (`scripting_best_practices.md` § "Supply Ships Are One Ship Type"). Restate every vanilla key, from `vanilla_parsed/common/ship_types.json`, with these changes:

| Field | Vanilla | New | Why |
|---|---|---|---|
| `base_construction_cost` | 25 | 250 | ten times the ship |
| `construction_goods` | 130 hardwood, 130 fabric | 1,300, 1,300 | the same bill per unit of capacity |
| `modifier.ship_construction_progress_max_add` | 5 | 50 | five weeks a ship before Naval Convoy Defense, as in vanilla |
| `modifier.ship_supply_capacity_add` | 500 | 5,000 | requirements fall to a tenth. No define counts ships per battalion or invasion, so they are need ÷ capacity (Stage 5 checks) |
| `modifier.ship_hit_points_max_add` | 1,000 | 10,000 | a raid sinks a tenth as many |
| `modifier.ship_crew_max_add` | 300 | 3,000 | only if 0b shows pooled ships draw sailors; otherwise leave it |
| `materiel_goods.goods_input_grain_add` | 1 | 10 | harmless if pooled ships don't use it |
| armor, vulnerability, speed, visibility, detection, readiness | | unchanged | per-ship qualities, not quantities |

The quick fix's add on Naval Convoy Defense goes from 20 to 200, so the cap reaches the new cost and a ship still takes a week. `test_supply_ship_progress_cap.py` then holds it to the mod's type, not vanilla's. Its test that the mod doesn't redefine the type is the one that will fail first.

The three armor modules, `ship_mod_supply_ship_armor_light`, `_medium` and `_high`, each carry `ship_hit_points_max_add` of 150, 375 and 750, to be ×10. A `REPLACE:` on a ship modification is unread. An `INJECT` adding the difference (+1,350, +3,375, +6,750) rests on a modifier block summing, which holds on every entity type read so far but hasn't been read on modifications. The propulsion modules are speeds, so leave them.

**Test:** `test_supply_ship_scale.py` pins each vanilla value above in `vanilla_parsed/`. It asserts the mod's copy is ten times each scaled field and equal on every other key, so a vanilla patch fails it until the copy is re-derived.

## Stage 2: the defines (read from the 1.15.2 files)

Every define that names supply ships, sorted by the rule: a count of ships is divided by ten, a per-ship value is multiplied by ten, a ratio or fraction stays. Three change. They go in `common/defines/extra_defines.txt`, in a new `NMilitary = { }` block and the existing `NAI = { }` block, each with a comment naming the vanilla value.

| Block | Define | Vanilla | Kind | New |
|---|---|---|---|---|
| `NMilitary` | `SUPPLY_SHIP_MAINTENANCE_COST_PER_SHIP` | 1 | money a ship a week | **10** |
| `NAI` | `DISBAND_EXCESS_SUPPLY_SHIPS_MAX_COUNT` | 10 | ships the AI decommissions per update | **1** |
| `NAI` | `RAID_HEAT_GAIN_PER_LOST_SUPPLY_SHIP` | 0.01 | heat a ship lost | **0.1** |
| `NMilitary` | `SUPPLY_SHIP_CONSTRUCTION_MAINTENANCE_FRACTION` | 0.0003 | a fraction of the cost, in points a week | unchanged; it follows the cost |
| `NMilitary` | `SUPPLY_SHIP_MAINTENANCE_STOCKPILE_REMOVAL_FRACTION` | 0.05 | a fraction of the pool | unchanged |
| `NMilitary` | `FLEET_SUPPLY_REPLENISH_SHIP_MULT` | 1.1 | a multiplier | unchanged |
| `NMilitary` | `SUPPLY_SHIP_TYPE` | `ship_type_supply_ship` | the type | unchanged |
| `NBattle` | `SUPPLY_SHIP_WITHDRAW_CHANCE_MULT` | 0.1 | a chance | unchanged |
| `NBattle` | `FLEET_RAID_MAX_SUPPLY_LENGTH_DIVISOR` | 5 | a divisor on the path's length | unchanged |
| `NSeasons` | `COLD_SUPPLY_SHIP_COST_MODERATE_FACTOR`, `_SEVERE_FACTOR` | 0.33, 0.66 | extra ships as a share | unchanged |
| `NAI` | `SUPPLY_SHIP_STRAIN_START_RATIO`, `_MAX_RATIO`, `_MULT_AT_START`, `_MULT_AT_FULL`, `_MULT_AT_MAX` | 0.75, 2.0, 0.99, 0.75, 0.05 | ratios and multipliers | unchanged |
| `NAI` | `SUPPLY_SHIP_ALLOCATION_HIGH_RATIO`, `_LOW_RATIO`, `_VERY_LOW_RATIO` | 0.5, 1.0, 1.5 | ratios of wanted | unchanged |
| `NAI` | `SUPPLY_SHIP_CONSTRUCTION_MAX_INCOME_FRACTION` | 0.1 | a share of income | unchanged |
| `NAI` | `DISBAND_EXCESS_SUPPLY_SHIPS_MIN_RATIO` | 2.0 | a ratio of wanted | unchanged |

Supply in the field rather than ships, so unchanged: `MILITARY_FORMATION_MIN_RESUPPLY_PER_WEEK` (10), `LOGISTICS_CENTER_SUPPLY_PER_LEVEL` (10), `ARMY_RESUPPLY_SURPLUS` and `FLEET_RESUPPLY_SURPLUS`. The `CONVOY_RAIDING_*` defines are the shipping lanes' Merchant Marine. `SUPPLY_SHIP_CONSTRUCTION_MAINTENANCE_FRACTION` explains the 1977 save's 3,177 points for 373,732 ships. At 0.0003 of 25 that is 0.0075 a ship, against 0.0085 read; the rest is probably designs costing above 25 (`SHIP_CONSTRUCTION_COST_MODIFICATION_LEVEL_FACTOR`, 1.05 a level).

## Stage 3: what else reads a count or a cap

- **`naval_battle_size`** (vanilla script value). When the defender is not a fleet, the battle size is `scope:military_formation.num_assigned_supply_ships`, capped at half the raiding admiral's command limit. That makes a raid's battle a tenth the size with each ship ten times as tough. Leave it, and judge it in the play-test, or `REPLACE` the value with ×10 on that branch. **Recommended: leave it.** A fight against fewer, tougher hulls is the intended picture.
- **Additive cap modifiers:** these lose nine tenths of their weight on supply ships, and nothing is needed. Vanilla's `principle_navy_2` and `_3` give +5 each, and Littoral Defense −5 (`extra_laws.txt:5285`). The multipliers (`naval_convoy_defense` +25%, `we_am_propulsion_military` +10%, Auxiliary Fleet's +30% capacity, Underway Replenishment's +40%) are scale-free.
- **Littoral Defense** may have left a country no supply ships before the quick fix. If the country-wide `country_ship_construction_progress_max_add = -5` reaches supply ships, the cap was (5 − 5) × 1.25 = 0. The law needs Naval Convoy Defense, so with the quick fix it is at least 20. The play-test list checks it.
- **GUI:** the top bar, the construction panel's level buttons and the decommission window show counts that are simply smaller, so they need no change. The budget breakdown (`gen_budget_breakdown.py`) reads money, which is unchanged in total.
- **Docs that state the old figures:** `scripting_best_practices.md` § "Supply Ships Are One Ship Type" (25 points, 7,800 a ship, about 13 hardwood and 13 fabric a week) and the Merchant Marine figures for #1813 (156 a ship). The player guide's `13-military.md` § "Ships and ship modifications" says a supply ship is built in a week with Naval Convoy Defense. It gains a sentence that a supply ship carries ten times vanilla's and costs ten times as much.

## Stage 4: running games

Defines and types apply to every loaded save. In a 1.2.x save the existing pool becomes worth ten times its capacity and pays ten times the upkeep. Existing queue entries keep a `construction_left` of 25 or less, so they finish as cheap ten-times ships, a small one-off gain. No trigger or script value reads a country's pool: there is the effect `add_supply_ships`, the trigger `supply_ship_maintenance_fulfillment` and a formation's `num_assigned_supply_ships`, nothing else. So script can't divide an AI's pool.

**Recommended: new games only, with a one-time button for the player.** The GUI can read `Country.GetNumSupplyShips` and pass it with `MakeScopeValue` into a scripted GUI that runs `add_supply_ships` for minus nine tenths. The space race, nuclear and banking widgets already pass values that way. AI countries in an old save keep a large pool. Their own logic lowers their construction level and decommissions what is over twice wanted (`DISBAND_EXCESS_SUPPLY_SHIPS_MIN_RATIO`), one ship an update once Stage 2's count is in. The cost is upkeep, not a crash. Say so in the release notes. Zeroing every pool from a one-time on_action is the other way. It is unread whether `add_supply_ships` clamps at 0, and every army overseas would go unsupplied until the yards rebuild.

For the timing in Stage 5 no migration is needed: the readout follows the entries in the queue, which re-form within a week or two.

## Stage 5: verification

- **Offline:** the Stage 1 test, `scripts/preflight.py`, and a `POST /reload` with its `warnings` read.
- **Timing (owner's machine):** the 2030 save with the branch deployed, timed from week 2, against 23.4 s (baseline), 12.4 s (readout removed) and the quick fix's figure from 0c.
- **Play-test list** (`docs/testing/perf-fixes-playtest.md`, a new section):
  - an 1836 start: the United Kingdom's need, which was 2,050, should read about 205, and its pool and level should be sensible;
  - an overseas army and a naval invasion: the predicted supply ships should be about a tenth of vanilla's, which confirms requirements are need ÷ capacity;
  - a raid on supply lines: losses should be a tenth in count;
  - decommissioning;
  - the readout's tooltip at Very High.

## Effort

| Stage | Who, where | Size |
|---|---|---|
| 0 | owner's machine: one save read and one timed session, two more if it moves less than expected | under an hour |
| 1–3 | one PR, offline | a few hours |
| 4 | the player's button, the same PR or a follow-up | about half a day |
| 5 | owner's machine: one timed session and the play-test list | an hour, then a play-test |
