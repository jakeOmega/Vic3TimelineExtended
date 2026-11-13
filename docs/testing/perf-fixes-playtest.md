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
| Cultural Hegemony board after a recount | After `event te_debug_ch.1`, option Recount now: each board row's score equals that country's share, its change equals the share minus last recount's, and no country keeps `ch_board_share_now` | A 0 score or change: the saved share was not read back |

## Sub-tick rendering: a switch to try in your own play (2026-11-13)

Not a change to the mod. The engine draws frames while a tick is being worked out, and a console switch or a launch
option stops it doing so (`docs/audits/late_game_performance.md`, "Sub-tick rendering, on and off in one session"). In
the harness the days ran a quarter to 30% faster with it off (five pairs within a session, and whole runs), the average
frame went from 10 to 11–13 ms and the longest wait for a frame from about 40 ms to 145–180 ms. The owner's own play of
the same months ran slower than the harness (1.9 s a day against 1.3–1.55), so what the switch saves there has to be
read there.

| Check | Expect | If it fails |
|---|---|---|
| Speed with the switch off | In a late game at speed 5, type `gamestatetick.renderframeifneeded` in the console (it answers "Disabled"; typing it again answers "Enabled"; the setting lasts until the game closes). Days pass visibly faster, and `dedicated_server.log`'s tick stamps show fewer seconds per game day than before the switch | No difference: in real play the day is spent elsewhere than in frames drawn mid-tick; note the seconds per day either way |
| What the screen does | The map and panels stay usable while the game runs: a brief hitch a few times a game week, no frozen screen | Long freezes: leave the switch on and say so; the harness's window never showed one |
| The launch option | With `-disable_renderframeifneeded` in the game's launch options the switch should start off, so that typing it once answers "Enabled". Untried: the harness runs that carried the option never typed the switch, and all ran with `-debug_mode` | It answers "Disabled": either the option was not read, or the option and the switch are separate settings; say which the speed suggests |

## The Timeline Extended window's Nation tab (2026-11-13)

Not a change yet. With the window open on its Nation tab the harness drew frames of 19 ms against 10, paused or
running, and its July ran about half again as long as with the window closed (2.18–2.25 s a day against 1.39–1.50;
`docs/audits/late_game_performance.md`, "The mod's own window"; the fix is #1760). The owner's own log of that game
ran July at 2.07 s a day and August at 1.60. Until it is fixed, the check is whether the window is what slowed July.

| Check | Expect | If it fails |
|---|---|---|
| Window open against closed, paused | In a late game, paused, with the FPS counter showing (debug mode): opening the Timeline Extended window on Nation roughly halves the frame rate, and closing it brings it back | No difference: the cost is specific to the harness's setup; say what was on screen in July 1931 |
| Other tabs | The same look on the tabs kept open most (Banking, Demographics, the United Nations) | A tab as slow as Nation: add it to #1760 |
| Running | At speed 5, days pass visibly slower with the window open on Nation than with it closed | Slower paused but not running: sub-tick rendering was off, or the day is spent elsewhere |
