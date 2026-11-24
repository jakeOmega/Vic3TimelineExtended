# Supply ships at ten times the size (#1984): scope and plan

Written 2026-11-24 for issue #1984, which offers two fixes for the time controls' ship construction readout. That readout is about half the 2030 week (`docs/audits/late_game_performance.md` § "The USA of 2030"). This plan scopes the first fix, which the owner prefers. In it each supply ship costs ten times as much and every requirement for supply ships is a tenth, from the start of a game. Nothing is built yet.

## Verdict

The script change is small: one type, three armor modules and a few defines. It can't be built well from a container without the game, for four reasons. Each is settled by Stage 0 on the owner's machine.

1. **Most of its reach is in files that aren't in the repo.** The supply ship defines live in vanilla `common/defines/00_defines.txt` and `00_ai.txt`. Neither is in `vanilla_parsed/`, and the session that wrote this couldn't fetch them. Only a few are known by name: `NMilitary|SUPPLY_SHIP_TYPE`, `SUPPLY_SHIP_MAINTENANCE_COST_PER_SHIP` (1), `SUPPLY_SHIP_STRAIN_START_RATIO` (0.75), and the AI's `SUPPLY_SHIP_ALLOCATION_*` and `SUPPLY_SHIP_CONSTRUCTION_MAX_INCOME_FRACTION`. Every define that counts supply ships needs scaling, and none of those is listed yet.
2. **It is unproven that the fix moves the readout.** The issue leaves two things open: which call costs it, and whether the cost scales with supply ships or with the fleet. If it scales with warships, ten-times supply ships don't help.
3. **Making them cost ten times as much would leave the list as long as it is.** The weekly cap per ship sets how many ships are in progress, not the cost. So the cap has to scale too (next section).
4. **Running games break.** No trigger or script value reads a country's pool, so script can't divide a save's pool by ten. Stage 4 covers that.

Once Stage 0 has run, Stages 1–3 are one PR of a few hours. The test that matters is cheap and needs no rescale: Stage 0's variant V3, one line.

## What the readout walks, and why the cost alone won't shorten it

Read from the 1977 save (`late_game_performance.md` § "The step of April 1976"). 59,189 points went to 17,236 supply ships under construction, 11,753 of them part built. That is 5.04 points a part-built ship, which is the type's own cap, `ship_construction_progress_max_add = 5` (vanilla `ship_type_supply_ship`). The other 5,483 entries waited unstarted. So the ships in progress number about the points allocated divided by the cap. The cost only sets how many weeks each ship takes: 25 points at 5 a week is five weeks.

- Cost 250 with the cap at 5: 50 weeks a ship, and the same number in progress. This alone does nothing for #1984.
- Cost 250 with the cap at 50: a tenth as many in progress, still five weeks a ship. This is option 1 as it has to be built.
- Cost 25 with the cap at 25 (V3 below): a fifth as many in progress, one week a ship. Nothing else changes.

Throughput isn't set by the cap. The yards queue more entries than they can progress (the 5,483 unstarted), so ships a week stay the allocated points over the cost. Raising the cap changes only how long a ship takes and how many entries sit in the list. What decides how many unstarted entries the engine queues hasn't been read.

## Stage 0: settle it before building (owner's machine, about an hour)

**0a. List the defines.** From the game's folder:

```
grep -n -i "SUPPLY_SHIP\|SUPPLY_NETWORK\|RAID\|INVASION\|TRANSPORT" game/common/defines/00_defines.txt game/common/defines/00_ai.txt
```

Sort each hit by the rule in Stage 2, and paste the list into this plan.

**0b. Read the 2030 save.** For the United States, count the entries in `ship_construction_manager > supply_ship_entries_database` against its warships and warship constructions. If supply ship entries outnumber warships and their constructions by an order of magnitude, that already points to the owner's guess before any timing. Record the supply ship level as well.

**0c. Three timed variants** on the same save with `run_variant.sh`, each an `--add-mod` folder as in the issue:

| Variant | Change | What it settles |
|---|---|---|
| V1 | `timemanip.gui`'s readout with `[Country.GetShipConstruction\|0]` replaced by `0` | whether the usage call is the cost |
| V2 | the same with `[Country.GetShipConstructionUsage\|0]` replaced by `0` | whether the total is the cost |
| V3 | `common/static_modifiers/zz_v3.txt`: `INJECT:base_values = { country_supply_ship_construction_progress_max_add = 20 }` (cap 5 → 25) | whether the cost scales with supply ships in progress |

Time V3 from its second week, once the old entries are done (at 25 a week each finishes in a week). The gate:

- **V3 cuts the readout's 1.5 s a day by most of a fifth or more:** the cost scales with supply ships in progress. Build Stages 1–5. V3 alone is a one-line fallback with no defines and no migration, if the owner would rather not rescale.
- **V3 leaves it unchanged:** the cost follows the fleet, and option 1 doesn't fix #1984. Fix it with option 2 (the readout in its tooltip). That needs vanilla's whole `gui/timemanip.gui`, which isn't in `test_fixtures/vanilla_gui/` either.

## Stage 1: the type and its modules (script; buildable offline)

`REPLACE:ship_type_supply_ship` in `common/ship_types/extra_ship_types.txt`. A `REPLACE:` takes on a ship type, which was probed on 2026-11-14 (`scripting_best_practices.md` § "Supply Ships Are One Ship Type"). Restate every vanilla key, from `vanilla_parsed/common/ship_types.json`, with these changes:

| Field | Vanilla | New | Why |
|---|---|---|---|
| `base_construction_cost` | 25 | 250 | ten times the ship |
| `construction_goods` | 130 hardwood, 130 fabric | 1,300, 1,300 | the same bill per unit of capacity |
| `modifier.ship_construction_progress_max_add` | 5 | 50 | five weeks a ship, a tenth as many in progress (above) |
| `modifier.ship_supply_capacity_add` | 500 | 5,000 | requirements fall to a tenth, *if* they are need ÷ capacity (Stage 5 checks) |
| `modifier.ship_hit_points_max_add` | 1,000 | 10,000 | a raid sinks a tenth as many |
| `modifier.ship_crew_max_add` | 300 | 3,000 | only if 0b shows pooled ships draw sailors; otherwise leave it |
| `materiel_goods.goods_input_grain_add` | 1 | 10 | harmless if pooled ships don't use it |
| armor, vulnerability, speed, visibility, detection, readiness | | unchanged | per-ship qualities, not quantities |

The three armor modules, `ship_mod_supply_ship_armor_light`, `_medium` and `_high`, each carry `ship_hit_points_max_add` of 150, 375 and 750, to be ×10. A `REPLACE:` on a ship modification is unread. An `INJECT` adding the difference (+1,350, +3,375, +6,750) rests on a modifier block summing, which holds on every entity type read so far but hasn't been read on modifications. The propulsion modules are speeds, so leave them.

**Test:** `test_supply_ship_scale.py` pins each vanilla value above in `vanilla_parsed/`. It asserts the mod's copy is ten times each scaled field and equal on every other key, so a vanilla patch fails it until the copy is re-derived.

## Stage 2: the defines (needs 0a)

These go in `common/defines/extra_defines.txt`, in a new `NMilitary = { }` block (and `NAI` if needed), each with a comment naming the vanilla value. The rule for each hit:

- **A count of supply ships** (sunk or protected per battle, needed per battalion or per invasion, a starting pool, a decommission step, an AI threshold in ships): divide by 10.
- **Per ship** (`SUPPLY_SHIP_MAINTENANCE_COST_PER_SHIP` 1 → 10, any ship-construction maintenance per pooled ship): multiply by 10. Before this, 3,177 points kept 373,732 ships in 1977, about 0.0085 a ship. If that comes from a define, ×10. If it comes from the cost, it follows Stage 1 on its own.
- **A ratio or fraction** (strain, allocation levels, income fraction): unchanged.
- **The type's name** (`SUPPLY_SHIP_TYPE`): unchanged.

## Stage 3: what else reads a count or a cap

- **`naval_battle_size`** (vanilla script value). When the defender is not a fleet, the battle size is `scope:military_formation.num_assigned_supply_ships`, capped at half the raiding admiral's command limit. That makes a raid's battle a tenth the size with each ship ten times as tough. Leave it, and judge it in the play-test, or `REPLACE` the value with ×10 on that branch. **Recommended: leave it.** A fight against fewer, tougher hulls is the intended picture.
- **Additive cap modifiers:** these lose nine tenths of their weight on supply ships, and nothing is needed. Vanilla's `principle_navy_2` and `_3` give +5 each, and Littoral Defense −5 (`extra_laws.txt:5285`). The multipliers (`naval_convoy_defense` +25%, `we_am_propulsion_military` +10%, Auxiliary Fleet's +30% capacity, Underway Replenishment's +40%) are scale-free.
- **A side finding to check now:** under Littoral Defense the supply ship cap may already be zero. If the country-wide `country_ship_construction_progress_max_add = -5` reaches supply ships, a Littoral Defense country's cap is (5 − 5) × 1.25 = 0 today, and it builds none. The law needs `naval_convoy_defense`, so the +25% is always there. To check, read a Littoral Defense country's supply ship queue in a save. Stage 1 makes it (50 − 5) × 1.25 ≈ 56 either way.
- **GUI:** the top bar, the construction panel's level buttons and the decommission window show counts that are simply smaller, so they need no change. The budget breakdown (`gen_budget_breakdown.py`) reads money, which is unchanged in total.
- **Docs that state the old figures:** `scripting_best_practices.md` § "Supply Ships Are One Ship Type" (25 points, 7,800 a ship, about 13 hardwood and 13 fabric a week) and the Merchant Marine figures for #1813 (156 a ship). The player guide's `13-military.md` § "Ships and ship modifications" gets one sentence, that a supply ship carries ten times vanilla's and costs ten times as much. No chapter states a supply ship figure today.

## Stage 4: running games

Defines and types apply to every loaded save. In a 1.2.x save the existing pool becomes worth ten times its capacity and pays ten times the upkeep. Existing queue entries keep a `construction_left` of 25 or less, so they finish as cheap ten-times ships, a small one-off gain. No trigger or script value reads a country's pool: there is the effect `add_supply_ships`, the trigger `supply_ship_maintenance_fulfillment` and a formation's `num_assigned_supply_ships`, nothing else. So script can't divide an AI's pool.

**Recommended: new games only, with a one-time button for the player.** The GUI can read `Country.GetNumSupplyShips` and pass it with `MakeScopeValue` into a scripted GUI that runs `add_supply_ships` for minus nine tenths. The space race, nuclear and banking widgets already pass values that way. AI countries in an old save keep a large pool. Their own logic lowers their construction level, and the cost is upkeep, not a crash. Say so in the release notes. Zeroing every pool from a one-time on_action is the other way. It is unread whether `add_supply_ships` clamps at 0, and every army overseas would go unsupplied until the yards rebuild.

For the timing in Stage 5 no migration is needed: the readout follows the entries in the queue, which re-form within five weeks.

## Stage 5: verification

- **Offline:** the Stage 1 test, `scripts/preflight.py`, and a `POST /reload` with its `warnings` read.
- **Timing (owner's machine):** the 2030 save with the branch deployed, timed from week 6, against 23.4 s (baseline) and 12.4 s (readout removed).
- **Play-test list** (`docs/testing/`, a new section):
  - an 1836 start: the United Kingdom's need, which was 2,050, should read about 205, and its pool and level should be sensible;
  - an overseas army and a naval invasion: the predicted supply ships should be about a tenth of vanilla's, which settles whether requirements are need ÷ capacity or a define;
  - a raid on supply lines: losses should be a tenth in count;
  - decommissioning;
  - a Littoral Defense country's queue;
  - the readout's tooltip at Very High.

## Effort

| Stage | Who, where | Size |
|---|---|---|
| 0 | owner's machine: one grep, one save read, three timed sessions | about an hour |
| 1–3 | one PR, offline once 0a's list is in this plan | a few hours |
| 4 | the player's button, the same PR or a follow-up | about half a day |
| 5 | owner's machine: one timed session and the play-test list | an hour, then a play-test |
