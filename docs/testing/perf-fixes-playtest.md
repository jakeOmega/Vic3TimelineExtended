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

## Nation tab rows: the figure in the text, the breakdown in the tooltip (2026-11-20, #1760)

Each generated row of the Timeline Extended window's Nation tab reads `GetFormattedValueFor` in its text and
`GetTooltipFor` under its description in its tooltip, in place of `GetValueWithBreakdownFor` in the text. The harness
session of 2026-11-20 on the USA of 1992 read the frame time with the rows loaded from this branch as a variant, and its
screenshot showed every figure as before (only the underline that marked the number as hoverable is gone); no row's
tooltip was hovered, since no harness verb can hover.

| Check | Expect | If it fails |
|---|---|---|
| A row's figure | "Authority: +120" or "Arable Land: +45%", signed and formatted as before | A bare number, no sign or no percent: `GetFormattedValueFor` formats unlike the breakdown accessor; take the format from `GetValueFor` with a format code instead |
| A row's tooltip | The type's description, a delimiter, then every source with its value and the total, as the old hover on the number gave | The description alone: `GetTooltipFor` returned nothing in a widget tooltip; put the breakdown back in the text for that row only |
| National Info, another country | The same rows and tooltips for the country shown | The player's own figures: `Country` reads the player there |
| Frame time with the tab open | Well below the old figure, paused (on 2026-11-20, vsync off: 19.8 ms open before, 12.0 with this change, about 6 shut, in the full-screen layout; the rest of the tab's cost is open in #1760) | Unchanged: the replace file or the deployed loc did not load |

## Solar and antimatter slot gates (2026-11-23, #1964, #1965)

The Solar Power Receiver's, Antimatter Engine's and Antimatter Warhead Plant's `possible` reads only the slot modifier
(a slot no built level takes); the exact count, which subtracts queued levels and walks the owner's states, is their
`can_build_government`. An existing Engine or Warhead Plant can no longer be expanded without a slot, and each of their
built levels takes a whole slot whether staffed or not. Nothing here has been seen in game. Use a late save with Orbital
Solar Collector or Antimatter Containment Facility levels.

| Check | Expect | If it fails |
|---|---|---|
| Lens, a slot free | The receiver (and the Engine and Warhead Plant) sits in the production lens's Development tab and can be queued | Missing with a slot free: the lens reads something else in `can_build_government`; compare with the Deep-Sea Mine's row in `global-commons-playtest.md`, item 2 |
| Lens, every free slot queued | It leaves the lens | Still offered and a level queues: the queue does not read `can_build_government`; put the count back in `possible` and take the cost |
| No slot free before queued levels | Greyed in the lens and the state's view, the tooltip naming the slot and the free count | Hidden instead: fine, but the tooltip line is not seen; say so |
| The last slot's level finishes | Queue exactly the free slots in one state: every level finishes, none waits | The last level waits at 0 points: the second branch does not hold; read the queue entry's tooltip |
| An existing Engine at 0 free | Its expand button is refused (or the lens hides it) | A level queues: another branch passes; read `possible` and `can_build_government` |
| Understaffed Engine | Right after a level finishes, the state panel's antimatter slot row already counts it as taken | The count rises again while it hires: the PM's `level_scaled` block is not read for country modifiers; move the −1 to `unscaled` |
| AI uptake | AI governments with slots still build receivers and Engines | None queued over ten years with slots free: the AI's planner skips a building whose `can_build_government` holds a walk, or needs `ai_value`; compare with the mine |
| Profile | With slots free, the receiver's `possible` row (`trigger common/buildings/extra_buildings.txt:<its possible line>`) costs well under 0.01 ms a read | Higher: something else in the block walks |

## Supply ships in a week with Naval Convoy Defense (2026-11-24, #1984)

Naval Convoy Defense (era 6) adds 20 to the weekly cap on a supply ship's construction, so with vanilla's 5 it is the
ship's cost, 25: a ship is built in one week, not five, and a fifth as many are in progress. Whether that shortens the
work behind the time controls' ship construction readout is the owner's reading of #1984 and is not measured. Before the
technology nothing changes. Nothing here has been seen in game. Use the 2030 United States save
(`late_game_performance.md` § "The USA of 2030") for the timing, and any save with the technology for the rest.

| Check | Expect | If it fails |
|---|---|---|
| The week, 2030 save, speed 5 | Timed as in #1984 from the second week (the old entries finish in the first): well below 23.4 s, toward 12.4 s (the readout replaced by a constant) | Little change: the readout's cost doesn't follow the supply ships in progress. Run the plan's V1 and V2 (`docs/superpowers/plans/2026-11-24-supply-ship-scale.md` § Stage 0) and take the tooltip route (option 2) |
| The construction panel's supply ship tab | Each ship in progress takes 25 a week (31 with the technology's +25%) and shows one week left | Still 5 a week: the country add doesn't reach the type's cap; put the cap on the type with a `REPLACE:ship_type_supply_ship` (the plan's Stage 1). Two weeks left at 25 a week: a designed ship costs more than 25 (`SHIP_CONSTRUCTION_COST_MODIFICATION_LEVEL_FACTOR`), which still leaves a fifth as many in progress |
| Before the technology | A country without it still takes 5 a week, five weeks a ship | Faster: another source of the add; `test_supply_ship_progress_cap.py` should have caught it |
| Ships a week | The top bar's supply ship count rises at the same rate as before the technology at the same setting | Faster: throughput was limited by the cap after all; the AI's levels and the yards' goods bill will be higher, so note by how much |
| Littoral Defense | A Littoral Defense country (the law needs the technology) builds supply ships at 20–25 a week, where the law's −5 may have left it 0 before | Below 20: the law's −5 and the +25% combine another way; raise the add by 5 |
| Readout tooltip at Very High | Hovering the readout no longer slows the day as it did in 1977 (17 s a day) | Still slow: the tooltip lists every entry, started or not; count the unstarted ones in the save |

## History charts: the 1-year and 5-year ranges build only the bars they show (2026-11-24, `gui/charts-perf`)

Each chart's 1-year and 5-year plots read only the store's newest samples, `DataModelLast( <list>, '(int32)12' )`
(60, and Demographics' and Cultural Hegemony's 5 and 20 years), and keep an age test on each; the 20-year (and 100-year)
plot reads the whole store and tests nothing. Banking's marker pips sit in one holder on `te_hist_mk`. `DataModelLast`
over a script list is proven in game (2026-11-24: the coordinator's session on a copy of the same save, the rows marked
seen below; the fallback was not needed). Measured before, on the owner's
save of December 2032 (20 years stored), the Banking tab in the Full Screen frame, 3840x2160: 75 frames a second with
its History section closed, 16 open at 20 Years, 18 at 5 Years, 23 at 1 Year (`late_game_performance.md`, "The history
charts").

| Check | Expect | If it fails |
|---|---|---|
| ~~Banking, 1 Year~~ (seen 2026-11-24) | Each chart draws 12 wide bars reaching the right edge, the newest month last, the same values as before | Empty plots: `DataModelLast` doesn't take a script list. Fall back to `DataModelSkipFirst( <list>, <the list's size less 12> )` (a count from `GetDataModelSize`), or to the whole list with the age test (the old cost) |
| ~~Banking, 5 Years~~ (seen 2026-11-24) | 60 bars of 8 px, the same as before | Empty, as above; 12 bars or the wrong ones: the count argument reads otherwise |
| ~~Banking, 20 Years (unset)~~ (seen 2026-11-24) | Every stored month, as before | Fewer: the whole-list plot reads the wrong store |
| ~~Frames a second, Banking tab open~~ (seen 2026-11-24: 1 Year 74, 5 Years 47, 20 Years 24, part of the last another branch's) | 1 Year near the closed figure (about 60 or more), 5 Years about 40, 20 Years a little above 16 | No change at 1 and 5 Years: the plots still build every sample; read the datamodel in the deployed `te_history_charts_generated.gui` |
| ~~Marker pips~~ (seen 2026-11-24, on the same charts) | Policy "i" and crash "!" pips on the same months as before, on Banking's charts only | A crash with no "!": a crash recorded without `te_hist_mk`; read the month's container in the save |
| ~~A short store~~ (seen 2026-11-24, a fresh game as Great Britain: it failed, and was fixed the same evening) | A country with fewer samples than the range (a major power newly tracked, or a new save's first year) draws what it has, at the right | It failed worse than the row guessed: `DataModelLast` asked for more than the list holds logged `Trying to reshape data model with negative offset -60` 300 to 430 times a second while Banking's History was open, and the tab took over ten seconds to open. Fixed by a second plot a shorter range, shown while the store holds less than the range (`gen_te_history_charts.plot_layouts`, `Store.holds`); seen again in March 1836 with two samples: two bars at the right edge at 1 Year, 5 Years and 20 Years, no error line |
| Demographics, Cultural Hegemony at 5 and 20 years | The same years as before | Empty: as the first row |
| National Info, another country | Its charts at each range, as for the player | The player's store: the plots read `Country` |
| The default, 5 years (`gui/charts-default-5y`) | After a fresh launch (the key unset), every monthly History section and viewer opens on 5 Years with the 5 Years button greyed, 1 Year and 20 Years clickable; 20 Years then shows every month and is greyed, and the choice holds across tabs until the game closes. Demographics and Cultural Hegemony still open on 100 years | 20 Years shows on a fresh launch: the deployed generated file is the old one. Two buttons greyed, or none: a section's buttons were missed |
| ~~Under five years stored (`gui/charts-default-5y`)~~ (seen 2026-11-24: failed, fixed; the row "A short store" above) | A new game's first years, and a 1-year view in its first year: the plot draws every month stored, at the right, as 20 Years does | As above: the fallback to the whole list with the age test is now the short store's own plot |
