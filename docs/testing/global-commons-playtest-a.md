# Global Commons play-test: Deep-Sea Mine rebalance and Extraplanetary Base logistics (§ 1)

What the next play-test should look at for spec § 1 (`docs/superpowers/specs/2026-10-16-global-commons-design.md`).
The offline gate is `test_deep_sea_rebalance.py` (orderings at base prices, read from the files); these rows are
what only the game can show.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … logistics_input_cut` | once a game: the first yearly pulse of a country with an Extraplanetary Base of level 3 or more on Tethered Launch or Fusion Tugs (a random one if it has several) | `goods_input_launch_capacity_mult` reads −0.3 per upgrade the building runs (−0.65 to −0.25): the mod-registered type is known to the engine and an `unscaled` building modifier counts once per building | about 0: the type is unknown to the engine (look for `Unknown modifier type` in `debug.log`) or the block isn't summed, so the upgrades do nothing. About −0.3 × `upgrades` × `level`: `unscaled` is read per level, and a large base buys no Launch Capacity. A building switched to an upgrade within a day of its owner's yearly pulse can still read its old sum, 0 (odds about 1 in 365); confirm in the building panel before taking a fallback | for 0, fix the registration in `common/modifier_type_definitions/mod_entity_modifier_types.txt`; for a per-level sum, move the cut to a static modifier on the building applied from a yearly pulse (the Strategic Reserve hub's `goods_input_<good>_mult` pattern) |

## In the building panel

1. Research Muon-Catalyzed Fusion Reactors (era 12) and own an Extraplanetary Base. Its Transport in Space group offers
   Fusion Tugs. Switch to it. The Launch Capacity line of the input tooltip shows −30%, and the input drops by 30%
   (a level on Asteroid Mine buys 120 Launch Capacity a week at full staff and base throughput, 84 with Fusion Tugs).
2. Research Space Elevator. Tethered Launch appears in the Launch to Orbit group without an elevator of your own. With
   both upgrades the input is 40% of the base method's (48 a level on Asteroid Mine, 192 on Mining Colony).
3. AI: in an observer run past 2100, AI Extraplanetary Bases take each upgrade within a few years of its technology and
   don't switch back. A base flipping between the two methods of a group means the default `most_profitable` scores
   them by something other than profit; give the groups `ai_selection = most_productive` and an `ai_value` ladder
   (`pmg_emissions_control`'s pattern).
4. The Deep-Sea Mine's new figures: a level on Deep-Sea Mining at full staff employs 500 machinists, 400 engineers and
   100 academics, and produces 260 Structural Metals, 260 Tech-Critical Metals, 150 Conductive and Base Metals, 50 Gold
   and 50 Chemical and Industrial Minerals a week at base throughput. Its profit tooltip at prices near base reads
   about £22,700 a level a week, against about £7,250 for an Extraplanetary Base on Asteroid Mine in the same market.
5. Saves from before the change: existing Deep-Sea Mines keep their levels and change outputs on load, and lay off
   the half of their staff the new method no longer employs. Existing Extraplanetary Bases start on Chemical
   Launch and Chemical Tugs, the groups' defaults. Watch for a base left with no method in a new group.
