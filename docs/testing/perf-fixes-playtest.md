# Performance fixes play-test checklist

What the next play-test should look at in the changes made for speed (`docs/audits/late_game_performance.md`). In-game
checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline
gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck
through with the commit that fixed it.

## UN tabling gates, arable land (2026-11-12)

The UN AI buttons ask their `possible`'s cheap gates in `visible` (nothing a player sees), and
`same_owner_state_region_arable_land_added` names its state instead of ROOT (#1703). The harness run of 2026-11-12
(snapshot `20261112T183036Z`) already saw the arable land value read above 0 for a state of another country and no
month-start errors; the panel itself was not looked at.

| Check | Expect | If it fails |
|---|---|---|
| Arable land breakdown | The states panel's arable land hover gives "from modifiers" above 0 for a state whose region had land added (`arable_land_added` set), in a country other than the player's | 0 everywhere but the player's: the saved state scope is not read in the script value |
| Month-start errors | `error.log` has no `extra_script_values.txt` line at a 1st of the month (about 5,700 before) | The value is still read with an ownerless scope |

## Strategic Reserve: who the AI founds one for (2026-11-12)

The AI's founding tier (`st_res_ai_hub_gdp_tier`) needs 100 million GDP from a minor inside another country's market,
and 10 million from a great or major power or a market leader, as before. For a minor below it the decision's
`ai_chance` and the hub's `ai_value` read 0. Read in an AI observer run from 1836 to about 1930, or in any new game
played that long; a save from before the change keeps its hubs. Each founding through the decision logs
`TE_ST_RES: founded class=… country=TAG date=…` in `debug.log`, with the class it held that day: `major` (by rank),
`leader` or `minor` (the tier held), `player` (a human outside both), or `zero_weight` (an AI whose `ai_chance` read 0).

| Check | Expect | If it fails |
|---|---|---|
| Who founds a hub | Count the `TE_ST_RES: founded` lines by class. No `zero_weight` line, and `minor` lines few. Holders of `je_strategic_reserve` today may include poorer minors without anything being wrong: a country that founded as a major or a market leader and later lost the rank or joined another's market keeps its hub, and so does a secession that took a hub state and won. Fewer holders than the 55 of the game measured; about 25 by 1931 is the fewest to expect, not the most | A `zero_weight` line: the AI took a decision whose `ai_chance` is 0, against vanilla's `000_decisions_help.txt`. Report it before choosing a fix: a gate in `possible` would bind players too |
| Majors and leaders still found | Great and major powers hold a hub within a few years of Logistics, and so does a market leader above 10 million | Fewer than before, or no `class=leader` lines: `gw_is_market_leader` or the decision's `ai_chance` reads wrong |

## Read-once values (2026-11-12, #1731)

`cultural_pull_from_art`, `cultural_pull_total` and `te_climate_heat_raw` save a value with `save_temporary_value_as`
and read it back, and tourism's state refresh stores the base appeal before the output modifier reads it
(`tourism_output_from_stored_appeal`). The harness runs of 2026-11-12 read the script values against the formulas
they replaced, for five countries, and found them equal; no panel was looked at.

| Check | Expect | If it fails |
|---|---|---|
| Cultural Hegemony panel | The art row, its bar and its hover show the same art pull as the overview's breakdown, with no `scope:` error in `error.log` while the panel is open | A 0 or an error naming `ch_art_production` or `ch_pull_raw_now`: the saved value is not read when the GUI evaluates the value; write the share and art pull without the save |
| Local climate hover | The state panel's Comfort hover gives the heat line it gave before (a state with hot summers: above 0) | 0 heat everywhere: `scope:te_climate_heat_excess_now` reads unset in the GUI |
| Tourism output | A state's tourism card total is what it was before the change (the same appeal, city rank and monuments) | A total missing its base appeal: the refresh read `var:te_tourism_base_appeal` before writing it |
