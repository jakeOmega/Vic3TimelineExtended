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

## The ship construction box under the date shows the total (2026-11-26, PR #2089)

The box under the date showed "used/total" ship construction, and the game worked the used figure out again after
every tick: about 7 s of every game week on the 2050 save (`docs/audits/late_game_performance_2050.md`, finding 5).
The mod now overrides the box's text (`SHIP_CONSTRUCTION_VALUE_WITHOUT_ICON`) to show the total alone. The timing was
measured through the harness; the look of the box, its tooltip and the Ships tab is what a play-test adds.

| Check | Expect | If it fails |
|---|---|---|
| The box under the date | The ship construction icon and one figure, the total (the first line of its tooltip gives the same figure "in total") | "used/total" as before: the override did not load; look for a second definition of the key in another mod of the playset |
| Its tooltip | Vanilla's, unchanged: the total, then "used/total being used", then the military and supply ship lines | A raw key: `SHIP_CONSTRUCTION_SPEED_BASE_TOOLTIP` is vanilla's and is not overridden, so say what shows |
| Paused ship construction | The base game's paused text in the box, not a figure | A figure: another mod of the playset redefines `SHIP_CONSTRUCTION_VALUE`, whose pause switch is vanilla's and untouched here; name the mod |
| The Construction panel's Ships tab | "used/total" beside the ship icon at the top, live | The total alone: the tab reads vanilla's key; `gui/production_methods.gui` should read `TE_SHIP_CONSTRUCTION_VALUE_PANEL` |
| Speed, a late game at speed 5 | Days pass faster between weekly ticks than before the change (a sub-tick 0.22 s against 0.37 s on the 2050 save) | No change: the cost is in the other figure after a patch; time each with a one-line `replace/` override as finding 5 did |

## The Ships tab: "used/total" abbreviated, and the cost under it (2026-11-27, #2093)

In a late game the Ships tab's "used/total" ran into the weekly cost beside it at five digits a side
("35015/5054£-1.37M", the February 2050 copy). Each figure now switches to the `|K` form at 1,000, and the cost sits
under the figure, both in the body size, as the Construction Site row has done since #2011
(`ship_construction_sector_actions` in `gui/production_methods.gui`; `test_construction_figures.py`).

| Check | Expect | If it fails |
|---|---|---|
| The Construction panel's Ships tab, a late game | The ship icon and "35.0K/50.5K" (or the like) in one line, the cost "-1.37M" under it, the pause button to the right; nothing overlaps | The figures overlap the cost: the row is not the mod's (another mod of the playset overrides `ship_construction_sector_actions`) |
| The same tab, an early game | "12/40" as before, figures under 1,000 printed whole | "0.01K" or the like: the `_N` keys are not picked below 1,000 |
| Hover the figure, then the cost | Vanilla's two tooltips, unchanged (the ship construction breakdown, then the goods expenses breakdown) | Either hover is gone: say which |
| Ship construction paused | The base game's paused text in place of the figure, the paused icon, the resume button glowing | A figure: `TE_SHIP_CONSTRUCTION_VALUE_PANEL`'s pause switch is lost |

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
| ~~A short store~~ (seen 2026-11-24, a fresh game as Great Britain: it failed, and was fixed the same evening) | A country with fewer samples than the range (a major power newly tracked, or a new save's first year) draws what it has, at the right | It failed worse than the row guessed: `DataModelLast` asked for more than the list holds logged `Trying to reshape data model with negative offset -60` 300 to 430 times a second while Banking's History was open, and the tab took over ten seconds to open. Fixed by a second plot a shorter range, shown while the store holds less than the range (`gen_te_history_charts.plot_layouts`, `Store.holds`); seen again in March 1836 with two samples: two bars at the right edge at 1 Year, 5 Years and 20 Years, no error line. On the December 2032 save (a full store) with the fix, 1 Year drew 12 bars and 5 Years 60, no error line, and 5 Years drew about twice 20 Years' frames a second, so the slicing plot is the one shown once the store holds the range (the machine was under load from test runs, so the absolute figures of the rows above were not re-measured) |
| Demographics, Cultural Hegemony at 5 and 20 years | The same years as before | Empty: as the first row |
| National Info, another country | Its charts at each range, as for the player | The player's store: the plots read `Country` |
| The default, 5 years (`gui/charts-default-5y`) | After a fresh launch (the key unset), every monthly History section and viewer opens on 5 Years with the 5 Years button greyed, 1 Year and 20 Years clickable; 20 Years then shows every month and is greyed, and the choice holds across tabs until the game closes. Demographics and Cultural Hegemony still open on 100 years | 20 Years shows on a fresh launch: the deployed generated file is the old one. Two buttons greyed, or none: a section's buttons were missed |
| ~~Under five years stored (`gui/charts-default-5y`)~~ (seen 2026-11-24: failed, fixed; the row "A short store" above) | A new game's first years, and a 1-year view in its first year: the plot draws every month stored, at the right, as 20 Years does | As above: the fallback to the whole list with the age test is now the short store's own plot |

## Batched private investment (2026-11-27)

Once a country's investors place 800 levels at home in a month with the private queue at the engine's 1,000, each level
they queue at home gets a batch of the same building beside it (100 levels a pick at most, to a tenth of its size
queued; 10 and a fiftieth for a local good's), so the engine's weekly investment pass makes far fewer decisions
(`docs/systems/mod_systems/construction.md` § Batched Private Investment; `docs/audits/late_game_performance_2050.md`,
proposal 4). **One harness session has run** (2026-11-27, `20261127T082220Z`: batching forced on for the USA by a
setup, 25 days; `construction.md` § the first run): the rows it answered are struck through below. It ran the first
batch rule (a hundred as the most a building could have queued); the rule as it stands, a country switching on by
itself, ownership, payment and a long game are still to see. Use the
2050 USA copy (`te_qa_copy_iua2050_20261126`) and the report's method (`profile start`, `advance`, `weekest.py`). A
country is watched at its first monthly pulse after the load and batches from the second. The save is of 6 February
2050, so the USA is watched on 1 March, `TE_BI on` prints on 1 April, the weeks to time are April's, and
`batch_invest_month` reads on 1 May: advance about 90 days. The rule (Batched Private Investment) switches between the
two in one save, and switching it off and on re-arms a trip.

**The first batch** queues construction from inside the engine's own construction hook, which nothing in the mod had
done before. `TE_SELF_CHECK START batch_invest_queue` prints just before it. In the session of 2026-11-27 it went
through: 19 batches, 1,448 levels, none refused. If a game ever crashes or hangs in a week with that line the last
`batch_invest` line in `debug.log`, switch the rule off in that save and report.

### Self-checks

In `debug.log`, each after a `TE_SELF_CHECK START` line of the same name. The fallbacks are written out in
`te_batch_investment_effects.txt` above each check.

| Line | When it reads | OK means | BROKEN means, and the fallback |
|---|---|---|---|
| ~~`batch_invest_hook`~~ (OK 2026-11-27: 597 picks seen at home, 1 unseen) | A watched country's monthly pulse. OK once a game; BROKEN once for each country | Ten picks or more seen at home in a month, and the queue's unseen growth no more than twenty times that: the hook runs as investors queue levels | That country's sixth month at the engine's limit, the pool paying, without that: the hook runs after the pass, or not for private levels. The country never batches. Fallback: batch from a weekly pulse over buildings under construction, with the ceiling above 1,000 (the owner's call: it builds more) |
| ~~`batch_invest_queue`~~ (OK 2026-11-27: asked 99, queued 99) | Once a game: START before the first batch of two levels or more, the verdict after | `queued` = `asked` | The effect was refused from the hook (`queued` under `asked`), or queues nothing there (0). Fallback for 0: the weekly pulse, as above |
| `batch_invest_reentry` (NO_VERDICT 2026-11-27, and it will stay so: script's levels do not come back through the hook) | The same batch | The batch's own levels came back through the hook with the level already counted | The hook runs before its level is counted, so each pick is read one call late; fallback: batch the previous call's building. `NO_VERDICT`: none came back while the batch ran; `batch_invest_month` then decides |
| ~~`batch_invest_month`~~ (OK 2026-11-27, forced on: 19 batches, 1,448 levels, `maxq` 1,000) | The end of each country's first whole month of batching | The batches queued more levels than were refused | They did not. `noroom` near `picks_home`: every pick came with the queue at the ceiling, so the hook runs after the pass has filled it (the pulse fallback). Otherwise `small`, `capped`, `unknown`, `short` say why |
| `batch_invest_limit` | Never, if all is well | — | The engine queued a level for a batching country with more than 1,000 queued: it does not count script's levels, the pass is no shorter, and the first batching pass left up to 900 levels too many in the queue (they get built). Batching is off everywhere until the rule is switched off and on. Fallback: hold the queue above the limit instead (the owner's call) |
| `batch_invest_runaway` | Never, if all is well | — | A batch queued more than it asked for. Batching is off everywhere until the rule is switched off and on; report the line |
| `batch_invest_flag` | Never, if all is well | — | A batch ended without clearing its flag; cleared at the pulse. Report the line |

### Checks

| Check | Expect | If it fails |
|---|---|---|
| It switches on (not seen: the session forced it on) | `TE_BI on country=USA` at the second month start after the load, with `placed_home` in the thousands and `maxq` 1000 | No line by the fourth month start: read `batch_invest_hook`. `picks_home` near 0 with a full queue is the hook not seeing picks. `maxq` under 990 with a full queue at the pulse: the last picks of every pass were abroad; lower `te_bi_engine_queue_near` |
| The investment pass (seen 2026-11-27 under the first batch rule: 5.25 s and 8.05 s against 25 s and 20 s; the rule as it stands is untimed) | `HandleAutonomousInvestment` on the weekly ticks after `TE_BI on`: about 2 to 3 s against 22 s (a hundred single levels at 22 ms, and a dozen or two batches). `small` on the month line should be near 0: 315 of 597 picks were `small` under the first rule | No change with `added` in the thousands on the `TE_BI month` line and no `batch_invest_limit`: the pass's cost does not follow its decisions after all; profile it. No change with `added` near 0: read `noroom`, `small`, `capped`, `unknown` |
| The week (seen 2026-11-27 under the first batch rule, on a build without the ship construction box fix: 25.7 s against 40 s over 14 February to 1 March) | Wall time a week about 7 s against 26 s over the report's dates | The pass fell and the week did not: something else grew; profile the tick tasks again |
| Decisions against levels | On `TE_BI month`: `picks_home` + `picks_other` a few hundred a month, `added` several thousand, `short`, `over` and `unknown` 0 | `short` above 0: the effect refuses levels `can_queue_building_levels` passed (a building's `possible`, say); harmless, but say which buildings. `unknown` above 0: investors queued a building the generator left out; add it to `why_not`'s reading |
| The private queue (its length seen 2026-11-27: 1,000 at the pulse, `maxq` 1,000; the panel not looked at) | The Construction panel's private queue holds about 1,000 levels as before, with runs of one building in one state | Over 1,000: read `batch_invest_limit` |
| ~~Whose queue a level abroad is in~~ (read by script 2026-11-27: 4 countries held 805 more queued levels in their states than in their queues, 7 held 999 more in their queues than in their states, 74 the same; the panel not looked at) | The USA's private queue lists its investors' levels in other countries' states, and no other country's investors' levels in the USA's states | Foreign investors' levels sit in the host's queue: a watched host then takes each for its own investors' and batches it. Switch the rule off and report; the hook needs another way to tell them apart |
| Who owns a batch | After a batched building's levels finish, its ownership tooltip gives the new levels to private owners (Financial Districts, Manor Houses, its own workers), as the engine's levels | The government's share rose by the batch: script's private levels are not privately owned. Switch the rule off and report |
| Who pays | The investment pool's weekly spending is about what it was, and the treasury's construction spending did not rise | The treasury pays for the batches: switch the rule off and report |
| Levels finished | The report's counter (levels finished in the USA's states a week, 577 before) is the same or higher: more of the queue is at home | Much lower: batches of expensive buildings wait where single levels of cheap ones finished; read the queue's first entries |
| Investment abroad (2026-11-27: the USA of 2050 places almost none to lose, 1 pick in 598; read it for a country that does) | A batching country's investors still place levels abroad every week (`picks_other` above 0), at roughly a tenth of the rate before | None at all: the reserve's slots are filled at home; raise `te_bi_reserve`. If the owner wants more abroad at 22 ms a level a week, the same |
| Privatization | In a batching country with government-owned levels and a law that lets investors buy them, the government's share of levels still falls, about a ninth as fast as before | It stops: the reserve's decisions all go to building; say so, and whether it matters for the countries that batch |
| Local goods | Transportation and electricity prices in the USA's states do not swing after `TE_BI on`; a Railway grows by at most a fiftieth a week | Swings: lower `te_bi_local_share` or `te_bi_local_batch_max`, to single levels if need be. Swings in states where an industry took a batch: the industries' own draw; lower `te_bi_share` |
| A building's growth | No building has more than a tenth of its levels queued by investors | More: `level_after_queued_constructions` does not count what the batch counts; read one building's queue entries |
| The rule, off | Switched to Batched Investment Disabled from the change-country screen: the next weekly pass takes 22 s again, and no `TE_BI` line follows the next month start | Batches go on: `has_game_rule` reads a save's old setting until reload; say which |
| The rule, on again | `TE_BI on` at the second month start after | No line: the country was not watched again; read its private queue at the pulse |
| A long AI run | An observer run to 2050 with the rule on against one with it off: the twenty largest economies' GDP growth by year about the same | The giants grow slower with it on: batches overshoot (read which buildings stand under-staffed), or the lost investment abroad mattered; lower `te_bi_share` or raise the reserve |

## Buildings panel: rows off screen are skipped (2026-11-27)

The sidebar's Buildings panel and the Building Registry's grouped view put each row's fixed-size top in a one-item
`fixedgridbox`, which the engine leaves out of a frame while it is scrolled out of view, and the panel's list updates
at most ten times a second (`docs/audits/buildings_panel_performance.md`). Seen in the harness on 2026-11-27 (the
2050 USA copy, paused): 341 → 18 ms a frame with the panel open, the rows, a filter, scrolling, the method menu,
expanding a type in both views and the Registry's ungrouped list all as before. Not seen: the rows below.

| Check | Expect | If it fails |
|---|---|---|
| The panel at speed | In a late game of a large country, the Buildings panel scrolls at once with the game running at speed 5 | Still slow: read the frame counter with the panel open and shut, paused and running; the report's method says how |
| The naval administration item | A fleet's Buildings section in the Military Formation panel (`military_formation_panel_buildings_content_fleet`, the same row type) draws its row: icon, name, method strip, buttons | Blank: the one-item list is empty there, or the item's context hides a value the row reads |
| A type with no levels yet | A building type just placed (its first level queued) still shows its row in the Buildings panel | Missing: that type's first production method group is not in the list (not expected: every type has groups) |
| The tutorial highlight | In a new game's tutorial, the step that points at the Buildings panel's rows still highlights them | No highlight: the highlight's widget, inside the wrapper, needs to sit outside it |
