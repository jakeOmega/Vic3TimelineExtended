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
and 10 million from a great or major power or a market leader, as before. Below it the decision's `ai_chance` and the
hub's `ai_value` read 0. Read in an AI observer run from 1836 to about 1930, or in any new game played that long; a
save from before the change keeps its hubs.

| Check | Expect | If it fails |
|---|---|---|
| Who holds a hub | Count the holders of `je_strategic_reserve` by class (great or major power, market leader, other). Few "other" holders, each with a GDP near or above 100 million (it may have shrunk since it founded); at most about 25 holders by 1931, against 55 in the game measured | Many poorer minors found anyway: the AI takes a decision whose `ai_chance` is 0, against vanilla's `000_decisions_help.txt`. Report it before choosing a fix: a gate in `possible` would bind players too |
| Majors and leaders still found | Great and major powers hold a hub within a few years of Logistics, and so does a market leader above 10 million | Fewer than before: `gw_is_market_leader` or the `owner` scope in the hub's `ai_value` reads wrong |
