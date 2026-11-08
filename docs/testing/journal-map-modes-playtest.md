# Journal entry map modes: play-test checklist

The in-game checks for vanilla 1.15's journal entry maps (`docs/systems/mod_systems/journal_map_modes.md`, issue
#1404), most important first. The first two passes (#1410, #1414, #1417) answered their lists (below), and the fourth
pass's repaint answered check 1 of the third's (sixth session, under Results). This is the sixth pass's list: checks
1–8 are the fifth pass's, still unreported but for check 2's fade, which works (the owner asked for 20% after seeing
30%: seventh session); checks 9–20 are the sixth pass's, the Map Room button in the Timeline Extended window, each
system tab's map button and the eight systems' maps; check 21 is the seventh pass's, its five Map Room
maps; checks 24 and 25 are the ninth pass's nine (2026-11-08). Record each answer under Results, in
`docs/audits/vanilla_1_15_prep.md` § 2 under C6, and each engine fact in `docs/guides/scripting_best_practices.md`
§ "Journal Entry Map Modes".

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work", from the full checkout: a sparse worktree's deploy would
  delete every texture.
- **A new game** or a save. No debug mode needed: the test strip is gone, and every check uses the map buttons in the
  Demographics and Banking tabs' headers (left of "?") and the Map Room's page.
- **Logs.** `grep TE_JMAP debug.log` (or `curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_JMAP"`):
  every pick writes `TE_JMAP pick <n> date=…`, and its reopen `TE_JMAP reopen date=…`.
- **At load**, check `error.log` for lines naming `te_map_widgets.gui`, `journal_entry.gui`,
  `te_map_room_widget.gui` or `te_systems_window.txt`, `failed reading callback` above all: the engine drops a
  callback it can't read and says so only there, once.

## The checks (fifth and sixth passes)

| # | Check | How | What each answer means | If it's the bad answer |
|---|---|---|---|---|
| 1 | A pick repaints, a tenth and a fifth of a second (2026-11-07) | Open the Map Room (Demographics header's map button). Pause. Click another map on the page, a dozen times. Then the same with the game running at top speed. | The page blinks and comes back on the new map every time, paused or not: `te_jmap_repaint` closes the page 0.1 s after the click, and `te_jmap_repaint_open` opens it 0.2 s after that. The fifth pass's 0.05 s each usually worked but sometimes left the page closed (the owner, 2026-11-07); the sixth session's 0.25 s and 0.1 s worked. Each pick logs `TE_JMAP pick` and then `TE_JMAP reopen`. Say whether the blink is acceptable while running. | Reopened on the old map: the scripted GUI's pick hadn't landed when the page closed; set `te_jmap_repaint`'s `duration` back to 0.25 (which worked). Closed and stayed closed, `TE_JMAP reopen` logged: the open ran before the close had landed, so its toggle closed the page; lengthen `te_jmap_repaint_open`'s `duration` to 0.3. Closed with no `TE_JMAP reopen`: read `error.log` for a callback line naming `te_map_widgets.gui`. |
| 2 | The see-through page at 20% | On the Map Room's page, click the crossed-out eye at the header's top left, beside the back arrow (`te_je_see_through`). Pick a few maps. Click the eye again. Then fade it and close the page with X (or Escape), and reopen it. Try a vanilla entry's page too. | The fade works (seventh session); it is now 20%, the owner's pick after 30%. Say whether 20% is right: the header still findable, the map clear enough. The page stays faded from pick to pick; the second click brings it back; after a close it reopens whole. The faded page still takes clicks (expected). Known edge: leave a faded page by opening another panel (a state, say) and the next journal page you open from the journal opens faded; the map buttons and the X clear it. | Too faint to find the header: 0.25 or 0.3 (`gui/journal_entry.gui`, the panel root's `alpha`). |
| 3 | The Demographics button while paused | Pick Turmoil, close the page, pause, then click the Demographics header's map button. | The page opens on life expectancy at once: the pick and the open in one click are enough when the page starts closed. | Turmoil until unpause: give that button the same delayed reopen as the picks. |
| 4 | Banking's stripes | Whenever a country's cycle overheats (later in a game), with Banking's map up. | Yellow stripes on that country's states (`map_color_second`; vanilla's own entries draw stripes the same way). | No stripes: note it; the tooltip still names the crash risk. |
| 5 | The Devastation map | During or after a war with battles on land, pick Devastation. Hover a battle-torn state and open its state panel. | Battle-torn states shade from pale sage toward char: halfway by 20% devastated, the rest more slowly to 100%. The rest of the world is sage. The hover's figure is the state panel's devastation. | All sage while the hover shows devastation above 0: the bare `devastation` read (`te_jmap_devastation_factor`) returns 0 in the paint; try the inline factor vanilla's Forest of Bayonets uses (`factor = { value = this.devastation multiply = 2 }`), and if that paints, give the generator's devastation row `this.devastation` as its input. No figure in the hover: read `debug.log` for `te_jmap_tt_devastation`. |
| 6 | The census maps | A few years in, click each census map (Life Expectancy, Infant Mortality, Leading Cause; Birth Rate, Death Rate, Natural Change; Fertility, Median Age, Aged 65 and Over; Sex Balance, Net Migration), and Urban People, Gini Coefficient and Dynastic Wealth. Hover a state and compare its Demographics panel. Try one in 1836, before the first census year. | Each paints, and its hover reads the panel's figure. In 1836 Birth Rate, Death Rate, Natural Change, Net Migration and Leading Cause show every state grey ("No census figures yet") until its first full year; the rest paint from the start. Say whether each map's curve reads well (each pick's tooltip gives the world's range it is painted on, check 23; `gen_journal_map_scales.py`'s table holds the shapes, and a shape changes every map using it). | A map grey everywhere after the first year: its gate's variable isn't stored as `te_demog_effects.txt`'s header says; note which. A hover with no figure: read `debug.log` for that map's `te_jmap_tt_` key. |
| 7 | Leading Cause's colors | Pick Leading Cause; open a state's Demographics panel. Hover a state whose leading share is near 30% and one near 90% (the hover gives it). | The state's color is its largest slice's in the Causes of Death pie, and the hover names it. The first state is pale and the second full; say whether the paler causes (killed by events, childbirth, war) still read apart at their pale end. A state whose runner-up took at least half the leader's deaths (its hover's second line, "Close behind, in the stripes") is striped in the runner-up's color, and one below half isn't. Late in a game, where chronic illness overtakes infection, many states should stripe. | Colors that don't match the pie: note which; the named colors are `te_jmap_cause_*`. No stripes on any state whose hover has the second line: the Map Room's `map_color_second` doesn't draw (the Banking map's stripes are unseen too); note whether the hover line shows. |
| 8 | The page with thirty-nine maps | Open the Map Room with every rule on, a few years in. | Fourteen rows of buttons (the world's six, the systems' three, the census's five) fit above the description without crowding the page, and every name fits its button ("Population Growth" and "Fighting-Age Men" are the longest, after the seventh pass's "Crowding Penalty"); nothing slower with the page open than before. | Crowded: say so (the rows could fold, or the systems' and the census's go under headings). A name cut off: shorten its `te_jmap_pick_*` loc. Slower: say how much; the ladder is longer now (the systems' branches sit after the census's). |
| 9 | The Timeline Extended window's Map Room button | Open the Timeline Extended window, side panel and then full screen, and click Map Room, left of the Full Screen / Side Panel button. | The Map Room opens on the last pick (`TE_JMAP` lines don't change: no pick runs), and the window closes. | The window stays open over the page: its close (`Clear('com_open_window')`, last) didn't land; move it first. Nothing opens: read `error.log` for a callback naming `te_map_widgets.gui`. |
| 10 | The systems' tab buttons | In each of the eight tabs (Global Warming, also the Market panel's Climate tab; Nuclear Weapons; Covert Warfare; United Nations; Cultural Hegemony; Seabed; Grand Monuments; Colonial Empire), click the map button left of the header's "?". | One click picks the system's map (`TE_JMAP pick 18`…`25`) and opens the Map Room on it, its button pressed. | Opens on the old map while paused: as check 3, give those buttons the delayed reopen the picks use. |
| 11 | Emissions | A few years in, pick Emissions; hover industrial states and compare the Global Warming panel. | Each state shaded by its share of the world's emissions last year, from the world's low to its high now, half the color in the first fifth (the owner's share, not an amount). The hover gives the state's emissions (the panel's K/M) and its share. Green where a state removes more than it emits. Grey until the state's first yearly snapshot and the first January's world total. Say whether the range in the pick's tooltip reads well. | Grey everywhere after a year: `gw_state_emis` isn't written (`gw_snapshot_country_emissions_effect`) or `gw_g_global_emis` is 0; note which (`debug.log` for `te_jmap_tt_gw`). The Global Warming panel's figures changed: the country total now sums the states' snapshots (`gw_country_emis_from_states`); compare a save from before. |
| 12 | Nuclear Weapons | Once a country has tested a bomb, pick Nuclear Weapons; better, as a nuclear power with a Nuclear Guarantee, a basing treaty and a guarantee of independence. | Your country blue; nuclear powers red, their hover the world's estimate; as a nuclear power, the countries hosting your weapons violet, those under your umbrella (your subjects, your Nuclear Guarantees) cyan, those whose independence you guarantee teal; the rest pale. | Your country not blue: the viewer comparison (`te_jmap_owner_is_viewer`: `global_var:te_jmap_viewer` saved as a scope) fails in a paint; try `owner = global_var:te_jmap_viewer`. Red but no viewer colors: the deterrent's triggers don't take a saved viewer scope there; note which. |
| 13 | Agent Networks | With covert operations running in a few countries, pick Agent Networks; compare the Covert Warfare panel's networks. | Each country with your network shaded lilac to violet by its strength, the hover the panel's figure; your own country blue; the rest pale. | None shaded though networks exist: `root.owner` in `te_jmap_net_strength` doesn't resolve in the paint; save the owner as a temporary scope instead. Shaded in the Map Room but not on the Covert Warfare page (check 19), or the reverse: note it. |
| 14 | United Nations | Before and after the UN's founding, pick United Nations. | All grey before the founding ("has not been founded"); after it members blue, permanent members deep blue, the headquarters' state gold, and each state with a mission in its type's color (peacekeeping cyan, aid orange, stabilization red, electoral green); non-members pale. | A mission state not colored: `un_state_mission_type` reads 0 in a paint; note it. Members pale: the `_on` mirrors aren't set yet (an old save gains them at the next monthly pulse). |
| 15 | Political Models | Pick Political Models; open the Cultural Hegemony panel's model chart. | Each country in its model's slice color; the hover names the model, and the leading cultural power says so. A country formed since the last census of models grey. | Colors off the chart: note which (`te_jmap_ch_*`; a test checks them against the pie's). |
| 16 | Ocean Basins | In a new game, after the first month, pick Ocean Basins (the Seabed rule on). | Every coastal state colored by its basin from the first month (the basin sweep no longer waits for Abyssal Plain Mining, and runs again each January for states made since); landlocked states pale. A coastal state made since January (a new colony) hovers "isn't recorded yet" until the next January. A state's own view still shows its basin tile only once you have the technology. | Pale everywhere after a month: the sweep (`te_seabed_global_monthly`) didn't run; read `debug.log`. The seabed's January sharing changed before anyone has the technology: note it (it shouldn't: the yearly pass waits for a claimant). |
| 17 | Grandeur | Pick Grandeur; hover a state with a monument and open the Grand Monuments panel. | Monument states cream to bronze over the world's monuments' range, most of the color in its first third; the hover is the panel's grandeur. The rest pale. | — |
| 18 | Colonies | In the decolonization era, as or beside a colonial empire, pick Colonies; open the Colonial Empire panel's holdings. | Each colony, and each colonial subject's state, in its empire's band's color (red collapsing to green solidified), the hover giving the empire's stability; an empire's other states taupe. The colonies are the panel's. The panel's colony count unchanged. | A colony pale: its mark (`te_jmap_ce_colony`, `colonial_empire_refresh_display`) is missing; note whether the panel lists it. |
| 19 | A system's own page | Open one of the seven entries from the journal (United Nations, say) and fade it. | Its page paints the same map as the Map Room's pick for it, without any pick. | Nothing painted: note which entry (a paint error there drops the map, not the entry). |
| 20 | Multiplayer (if anyone tries it) | Two players. | The maps of "your" country (Nuclear Weapons, Agent Networks) follow the last player to pick or press a map button, as the pick does: each sees that player's deterrent and networks. That is an intelligence leak: another player learns where your agent networks are and how strong, and which countries host your weapons or shelter under your umbrella (never your arsenal's true size: the guarantee band waits for the world to believe you armed). | A design call, not a bug: say whether to keep these two maps out of multiplayer. |
| 21 | The seventh pass's maps (2026-11-06) | A month in, pick Tourism Appeal, Base Comfort, Current Comfort, GDP per Capita and Crowding Penalty in turn. Hover a few states and open their state panels. Try Tourism Appeal and the comfort maps in a new game's first month, and on a save from before this change. | Each paints, and its hover reads the state panel: Tourism Appeal the tourism card's Base Appeal, Current Comfort the Local Climate tile's Comfort row, Crowding Penalty the Migration Crowding tile's Pull Penalty, GDP per Capita a year's GDP over the state's people beside its country's. Base Comfort is redder than Current Comfort wherever the owner has relief technologies, and the same in 1836. In the first month (and for a month on an older save) the three stored maps show grey, "No figure yet". Say whether the curves read well (each fitted to the world since 2026-11-07, check 23): comfort is soft above none, crowding soft from a third of its range, and GDP per capita takes the same share of the color per doubling from the world's low to its high. | Grey after a month: the refresh didn't store its figure (`te_tourism_base_appeal`, `te_climate_base_penalty`); read `debug.log` for `te_update_tourism_modifier` or `te_update_local_climate_modifier`. GDP per Capita or Crowding Penalty one color everywhere: the live read returns 0 in the paint (`gdp_per_capita`, `migration_crowding_pull_pct`); have a refresh store them as tourism's is. No figure in a hover: read `debug.log` for that map's `te_jmap_tt_` key. |
| 22 | Power Grids (2026-11-07) | Once a few countries have Grid Transfer Stations (Electrical Capacitors), pick Power Grids, or click the map button in the Power Grids tab's header; then a month later. Hover a grid's states and open a station's state panel. | Each grid's states in one color, bordering grids in different colors, the hub striped white; a station on no grid grey; states without one pale. The hover names the hub and the grid's stations, as the state panel's tile does. A grid keeps its color from month to month. Map button: `TE_JMAP pick 31`. | All one color: `te_grid_map_color` isn't written (`te_grid_map_color_effect`), or every grid takes 1 because `te_grid_map_color_taken` can't read the local `te_grid_color`; note which. Neighbouring grids alike: the trigger doesn't see the neighbour's color. No stripes on hubs: `te_grid_rec_supply` is gone by paint time; note it. No hub name in the hover: the state reference read (`Var('te_grid_hub').GetState`) fails in a paint's loc. |
| 23 | Maps fitted to the world (2026-11-07) | In a late game (1950 or later) and an early one, pick GDP per Capita, Life Expectancy, Fertility, Turmoil and Natural Change in turn. Hover each pick's button, then a few states. Run a month and look again. | Each map uses its whole palette: the world's poorest (or lowest) states at one end and its richest at the other, so regions differ where the fixed curves put the whole late world in one corner. The pick's tooltip gives the range now (`te_jmap_<map>_lo` / `_hi`), and a pick logs `TE_JMAP pick` as before. Fertility and Natural Change keep cream at replacement and at none where states lie on both sides; where the whole world is below replacement, cream marks the state nearest it. The range follows the world from month to month. Say whether the trim (the 5th lowest and highest) reads well, or whether a few outliers still flatten a map. | Every map on its old colors and the tooltip's range the old ends (25 to 80 years): the range effect didn't store its globals; `ordered_state` with `position = 4` and `check_range_bounds = no` may have run nothing, so read `error.log` for `te_journal_map_ranges_generated.txt`. A map the same color everywhere: its `te_jmap_rng_<map>_*` globals are equal or reversed; note which map. Ranges that never move with the game running: the global `on_monthly_pulse`'s `te_jmap_monthly_ranges` isn't running; note it. |
| 24 | The ninth pass's maps (2026-11-08): City Rank, Company HQs, Armed Forces, War Dead | A few years in, pick each; hover a few states and open their state panels. For Company HQs, open a headquarters building's panel. For War Dead, a year into a land war. Read `debug.log` for `TE_SELF_CHECK` once a month has passed with three headquarters in the world. (The first build, #1514, tested the headquarters by template type and painted every state grey, with no self-check line; 2026-11-08's fix finds them by building group and stores the figures monthly, so a load's first month is grey until a pick of the map.) | **City Rank**: the 20 largest cities amber (20th) to crimson (1st), the hover's rank and Cities bonus the state panel's tourism card's; the rest steel blue, paler with each doubling of the rank; a state past 501st pale, "Not among the world's 501 largest cities". **Company HQs**: a state without a headquarters grey; one with any, ice to navy by their weekly profit summed (the hover gives the count and the figure, which should match the sum of their buildings' panels' profit), red at a loss. `TE_SELF_CHECK OK hq_found states=…`, then `TE_SELF_CHECK OK hq_profit states=… nonzero=…`. **Armed Forces**: each state by its Soldiers and Officers, pale khaki to olive a doubling at a time, the hover the count and its share of the people; a state with none pale. **War Dead**: each state's war and devastation deaths last year, pale rose to dried blood a doubling at a time, the hover its Demographics panel's War, Devastation row; peace pale; the dead fall where the soldiers came from (the census shares them by soldiers). Say whether each reads well, and whether "Armed Forces" and "Company HQs" fit their buttons. `TE_SELF_CHECK BROKEN hq_found`, or every state grey after a month: no building of group `bg_company_headquarter` stands in any state, so the per-company headquarters types are in some other group; read them through the companies instead (`every_country`, `every_company`; the regional ones through `every_scope_regional_hqs`, which reach their buildings and so their states). `TE_SELF_CHECK BROKEN hq_profit`, or every headquarters red: an ownership building's `weekly_profit` doesn't carry its dividends; fall back to its owner's companies' `prosperity` (from `every_company`) on the headquarters states: script can't tell which company a headquarters is, so it would be the country's companies together. City Rank all pale after a month: `state_city_size_rank` isn't set (`city_rank_on_action`); the state panel's tourism card would show "unranked" too. Armed Forces grey everywhere: the yearly walk hasn't run yet (a game's first year), or `te_dg_soldiers` isn't stored. |
| 25 | The ninth pass's second round (2026-11-08): Ownership, Population Growth, Family Planning, Health Care, Fighting-Age Men, and Company HQs' stripes | A few years in, with the census on, pick each; hover a few states and open their Demographics subtabs. Compare a capitalist country, a cooperative one and a command economy for Ownership. For the stripes, find a state with a regional headquarters (a company with an Investment Charter abroad). | **Ownership**: each state in its leading holder's color, private gold, their own workers green, the state red, pale where it barely leads and full where it holds everything; the hover's three shares sum to 100%. In 1836 most of the world is pale gold (55-65% private). **Population Growth**: magenta to cream to teal, the hover the two counts a year apart; grey until a state's second yearly walk. **Family Planning**: the hover's means are the subtab's "Means to plan a family", its marriage age and birth spacing the subtab's. **Health Care**: the subtab's Health Care Access and where it is heading; childbirth deaths the Causes of Death row's. **Fighting-Age Men**: the overview's "Men aged 20 to 39" figures, per state. **Company HQs**: gold stripes over each state with a regional headquarters, and a hover line counting them. Say whether each reads well; whether Ownership needs stripes for its runner-up, as Leading Cause has; and whether Population Growth's jumps from land changing hands spoil it. | Ownership all one pale color: the walk's levels (`te_dg_lv_*`) are 0 or `te_jmap_own_lead` reads 0 in the paint; note the hover. Population Growth grey everywhere after two years: `te_dg_walk_pop_prev` isn't kept. No stripes on Company HQs while a hover counts regional headquarters: the third `map_color_second` branch doesn't draw; note it. |

## The third pass's checks, answered

| # | Question | Answer |
|---|---|---|
| 1 | A pick repaints a paused map (the fourth pass's repainter) | Works: `te_jmap_repainter` closing the page a quarter second after the click and reopening it a tenth later (the owner, sixth session: "0.25 worked"). Check 1 above tries a twentieth. |

## The second pass's checks, answered

From #1417's list (its numbering), by the fourth session under Results:

| # | Question | Answer |
|---|---|---|
| 1 | One click opens the Map Room, picks on the page | Yes: a widget draws on a contextless page. |
| 2 | Picks on the page | Work, at the next tick, and the current pick's button draws pressed (`down` works). |
| 3 | Scope probe | Blue: `scope:journal_entry` isn't set in a contextless entry's map either. No white stripes over the player's states: the stripe condition was `owner ?= { is_player = yes }` (**settled, eighth session:** the Map Room's Leading Cause stripes draw, so it was `is_player`), and vanilla's own entries stripe through the state's `owner`, so most likely `is_player` doesn't resolve in the paint. The probe is gone. |
| 4 | Repaint while paused | (a) Reopening the page repaints. The picks now reopen it themselves (third-pass check 1). |
| 5 | The map with the page closed | Neither: the lens toolbar's lock doesn't keep it (the map went back to political), and the listed copy painted nothing with no page open and the open page's map otherwise. The copy is gone; the see-through page is the answer instead. |
| 6 | Does the Banking tab paint its map | No: only its button (opening the entry's page) does. |
| 7 | An inactive entry's page | Opens from a button and paints its map (magenta). (b), the wait for Potential, is moot. Banking's button lost its `IsActive` gate, which never mattered: the entry is active from the engine's first check. |
| 8 | Look and feel | Good for now. |
| 9 | Water, wasteland, unowned, decentralized | Land no branch paints draws dark grey; water keeps its normal look. |
| 10 | Cost | Somewhat slower, hard to tell; not measured. |

## The first pass's checks, answered

From #1410's list (its numbering), by the first three sessions under Results:

| # | Question | Answer |
|---|---|---|
| 2 | Several maps on one entry | Yes, on a selector: a pick shows at the next tick (paused, at unpause). |
| 3 | Can `map_color` read the player's country? | No: blue. Neither `scope:journal_entry` nor its owner resolved on a country entry, so the pick is a global variable, shared by every player in a multiplayer game. Stripes not yet reported (check 3 above). |
| 4 | Activation timing | An entry with activation triggers activates at the engine's own check, which looks fortnightly: four activations fell on Jan 13 plus a multiple of 14 days, 4–12 days after the click. |
| 5 | Closing (`can_deactivate`, variable removed) | Works: the entry went back to inactive (the adds that followed ran, and it reactivated). |
| 6 | One click: add and open | Moot. `add_journal_entry` was refused every time, and the open callback failed at load in both forms tried. |
| 7 | An entry outside every journal | Works: a contextless entry nobody is involved in opens from a button and paints. The Map Room is now one. |
| 8 (a), (d) | The map with the page closed; hover previews | The map goes with the page; `SetTempMapModeByKey` hovers paint nothing (grey). (b) and (c) are check 5 above. |
| 12 | How often the map redraws | As the game runs: the weekly tick map stepped with the page open. |
| 14 | A scripted button on a contextless page | Locked: "Countries that are not involved in the Journal Entry may not take this action". The Map Room's picks are scripted GUIs instead. |

## Results

### First launch, 2026-11-05 (build 43f4db80e)

The first launch on `main` after #1410: a new game as Britain in debug mode, run to 1837. No map button was clicked (no
`TE_JMAP` line in `debug.log`), so checks 1–13 are all still open. What the load and the 1837.1.1 autosave answered:

- **Everything loads.** No line names `te_journal_maps.txt`, `te_journal_map_colors.txt`, `te_map_modes.txt` or
  `je_banking.txt`, the engine enumerated `gfx/map/map_modes` without complaint, and the game started with the listed
  copy in place. So the "if the game won't start" step is closed; whether the copy shows in the dropdown is still
  check 8(c). Banking's new map fields didn't cost it the entry: `TE_SELF_CHECK OK banking_entry_everywhere`.
- **The strip's Add + Open button had lost its second click at load.** Its `onclick` passed
  `GetPlayerJournalEntry('je_te_map_host')` bare to `OpenJournalEntryPanel`, and the engine logged `Could not find data
  system function 'GetPlayerJournalEntry'` and `failed reading callback, at gui/te_map_widgets.gui:103`. The data-types
  dump lists `GetPlayerJournalEntry` only as a global promote, with no function form, so it can't stand as an argument
  on its own. The button would only have added the entry, and check 6 would have read "two clicks" whatever the engine
  does. It now passes `GetPlayerJournalEntry('je_te_map_host').AccessSelf`, the form vanilla's
  `GetBuildingType('building_shipyard').Self` takes (`construction_panel.gui`). Check 6 tests that form too. (That
  failed at load as well: third session.)
- **The hidden world entry exists.** `je_te_map_hidden_world` is active from 1836.1.1 with no country and an empty
  root: a contextless entry nobody is involved in is created and kept. Whether a button can open it is check 7.
- **The Map Room stays out of the journal while nobody asks.** `je_te_map_host` has an inactive record on all 286
  countries and an active one on none. Checks 4–5 (adding and closing it) are still to run.

### Second session, 2026-11-05 evening (same build)

The owner's report, with `debug.log` from 16:51 to 16:55:

- **Check 2: picks work, at the next tick.** The Map Room's buttons change its map, but only once the game runs: paused,
  the map stays until unpause; running, it changes within a tick, not a week. So one entry can host many maps. The data
  types dump has no map refresh function; what is left to try is closing and reopening the page while paused, and a
  map mode switch away and back (`SetTempMapModeByKey` then `RemoveTempMapMode`) after the pick.
- **Check 7: the hidden entry works.** Hidden Entry opens `je_te_map_hidden_world`'s page and the map turns magenta.
  An entry no country is involved in can host a map and be opened by a button, so a map never needs to show in the
  journal at all.
- **Check 8 (a): the map goes with the page.** Closing the page removes the map. (b), with the lens toolbar's lock, and
  (c), the dropdown copy, are still to try.
- **Check 8 (d): neither hover preview paints a journal map.** Both showed a blank map, grey everywhere.
- **Check 3: blue everywhere.** Neither `scope:journal_entry` nor its owner resolves inside `map_color`; only the
  global variable gets through. So the global pick stays, and two players in one game share the Map Room's pick (system
  doc). Not yet reported: whether the player's own states had white stripes (`map_color_second` and the state's `owner`).
- **Check 12: the refresh tick works.** `map_color` is re-evaluated as the game runs, so a live figure shows live with
  the page left open.
- **Life expectancy errored on hover.** Its tooltip chose between two keys with `SelectLocalization`, and the key named
  there lost `THIS`: 649 lines of `Promote 'THIS' returned nullptr` / `Data error in loc string 'te_jmap_tt_e0_value'`
  and no figure. The choice is now two `map_tooltip` branches (the same trap as `ROOT` and `SCOPE`,
  `gui_modding_guide.md`).
- **Add + Open (check 6): the add takes about a week, and the page never opened.** (Wrong on both causes: see the third
  session. The add was refused, and `.AccessSelf` failed at load too.) It never could on this build: its
  open callback was dropped at load (above). But the week answers check 6 whatever the form: an entry `add_journal_entry`
  adds isn't in the journal until about a week later, so no click can add the Map Room and open it. The Demographics
  button stays two-state, and its tooltip now says the Map Room appears within about a week. The log fits: 25 `host
  added` lines, 21 of them in 12 seconds (each logs only while `has_journal_entry` is false), and the entry's
  `immediate` logged twice. For the next pass, check 7 removes the wait: a contextless entry like the hidden one exists
  from the start and opens at the first click, so the Map Room can be one, with no add, close or two-state button.
- The `TE_JMAP` lines printed no date, so checks 4–5 couldn't be timed from the log: at 16:51 four adds were followed by
  the activation 29 seconds later, and at 16:54 21 adds had no activation before the close, but in game days that could
  mean anything. All four lines now print `date=`, so 4–5 need a rerun.

### Third session, 2026-11-05 evening (build d733ebc76, with #1414)

The owner's report and screenshot, `debug.log` and `error.log` from 17:18 to 17:27, and the 17:29 autosave:

- **Add + Open still had no open.** The load logged `Invalid promote 'GetPlayerJournalEntry'(0) for
  'GetPlayerJournalEntry('je_te_map_host').AccessSelf', requires non const promote` and `failed reading callback, at
  gui/te_map_widgets.gui:103` (`error.1.log`). Inside a callback `GetPlayerJournalEntry` fails ended with
  `.AccessSelf` as well as bare: it is a const promote, and a function that changes the game (`OpenJournalEntryPanel`)
  needs a non-const one. The form proven in game is the entry as the button's `datacontext` and
  `JournalEntry.AccessSelf` in the click (the Hidden Entry and Banking buttons). Gotcha #29 and the GUI lint said
  otherwise; both are corrected.
- **`add_journal_entry` never added the Map Room.** Every add logged `Great Britain already has a journal entry of type
  je_te_map_host` (`journal_entry_manager.cpp:372`, 32 lines). The autosave holds 286 `je_te_map_host` records, one per
  country, only Britain's active: every country holds an inactive copy of a country entry with its own activation
  triggers (`is_shown_when_inactive`, `possible`) from the game's start, vanilla's too (`je_meiji_restoration`: 286).
  Entries vanilla adds by effect define neither and have no copy until added (`je_king_in_parliament`,
  `je_spanish_flu`, `je_iwakura_mission`, `je_sepoy_mutiny`: 0 each; `je_abolish_monarchy`: 3). `has_journal_entry`
  reads active copies only, so the button's guard passed, and the add was refused. The owner saw the copy in the
  journal's Potential section once the button's variable made it shown.
- **So the wait was the activation check, not the add.** Clicks (adds or requests) on Jan 1, Jan 20, Feb 17 and Apr 17
  led to activations on Jan 13, Jan 27, Feb 24 and Apr 21: each Jan 13 plus a multiple of 14 days. The Request and Add
  buttons were the same button.
- **Close works** (first-pass check 5): the Feb 17 and Apr 17 adds ran, which their guard allows only once the entry
  is no longer active, and the entry reactivated after each.
- **Check 14: a contextless page's scripted button is locked.** The screenshot shows Probe: Run a Button Here with
  "Countries that are not involved in the Journal Entry may not take this action" and the padlock; no `TE_JMAP world
  button ran` line. 1.15's `add_involved_country` could unlock it, but an involved country probably sees the entry in
  its journal, so the second pass uses scripted GUIs on a page widget instead.
- **Second pass built on these** (#1417): the Map Room is contextless, its picks are scripted GUIs on its page, the
  Demographics button is one click, and the first pass's host, hidden world entry, add, request, close and hover
  buttons are gone.

### Fourth session, 2026-11-05 night (build ef1e1cce1, #1417)

The owner's report and screenshot, `debug.log` and `error.log` from 20:49 to 21:05 (16 `TE_JMAP pick` lines, six of
them on Jan 1 while paused):

- **Check 1: works.** One click on the Demographics header's map button opens the Map Room with its picks above the
  description, so a widget draws on a contextless page.
- **Check 2: works, at the next tick.** Each pick changes the map once the game runs, and the current pick's button
  draws pressed: `down` bound to a scripted GUI's `IsValid` works (the owner, after the session's report).
- **Check 3: blue everywhere, no stripes.** Blue: `scope:journal_entry` isn't set in a contextless entry's map either.
  No stripes: `map_color_second` drew nothing under `owner ?= { is_player = yes }`. Vanilla's own entries draw stripes
  through the state's `owner` (the Great Game, the Forest of Bayonets), so the likely failure is `is_player` inside the
  paint, which fits a paint with no player or entry in reach. Not separated further: no map needs it, so the probe is
  gone.
- **Check 4 (a): reopening the page repaints.** Paused, after a pick, going to Demographics and clicking Open Map Room
  again showed the new pick. So each pick now closes and reopens the page itself, a quarter second after the click.
- **Check 5: the map exists only while its page is open.** (a) With the lens toolbar's lock on, closing the page sent
  the map back to political. (b) The listed copy, Journal Entry Map (Test), painted nothing (grey) with no page open;
  opening the Map Room or Banking showed that page's map, and closing it went grey again. It adds nothing to vanilla's
  journal map mode, so it is gone. The owner asked whether the page could stay open but transparent: the third pass
  adds the see-through eye (check 2).
- **Check 6: the Banking tab doesn't paint the map.** Only its map button, which opens the entry's page, does. So
  only the journal panel triggers a map: every system shown in a vanilla tab or the Timeline Extended window needs a
  button that opens a page.
- **Check 7: an inactive entry's page opens and paints.** The strip's Open Potential Probe, clicked before anything
  else, opened the inactive `je_te_map_potential_probe` ("Potential Probe (Test)", a Domestic Affairs entry), and the
  map turned magenta at once (screenshot). So `GetPlayerJournalEntry` returns an inactive copy, the panel opens it,
  and its map paints: a map button needn't wait for its entry. Banking's button lost its `IsActive` gate on that
  ground, though it gated nothing a player meets: the entry is active for every country from the engine's first check
  (`possible = { always = yes }`), and the Banking tab waits for that. (b) wasn't answered and is moot: the log's
  `potential probe on` (Jan 4) and `off` (Jan 7) are the toggle, not the day the entry showed in Potential. The
  inactive page listed a long run of countries under Involved Countries, over a hundred flags and running off the
  screen; nothing opens an inactive page now, so it waits for a map that does.
- **Check 8: good for now.**
- **Check 9: land no branch paints draws dark grey, and water keeps its normal look.** A branch that matches paints
  any land: the probe's flat magenta covered all of it in the screenshot.
- **Check 10: somewhat slower, hard to tell.** Not measured; nothing to change yet.
- **Logs.** No load line names a map file. The in-game error counter (2849) was mostly Grand Monuments'
  `gm_arch_country_has_any`, which reads its counts despite a `has_variable` guard in the same `AND` (1,104 lines;
  issue #1418), and vanilla's Indian Famines outcome (270 lines; `docs/vanilla/vanilla_known_bugs.md`).
- **Third pass built on these** (this list): picks reopen the page to repaint, every journal page has a see-through
  eye, Banking's button has no `IsActive` gate, and the scope probe, the Potential probe, the test strip and the listed
  copy are gone.

### Fifth session, 2026-11-05 night (build f0c8135f0, #1420)

The owner's report and `debug.log`/`error.log` from 22:06 to 22:18 (six `TE_JMAP pick` lines, all on Jan 1, 1836):

- **Check 1: the page closed and never reopened.** Every pick closed the Map Room's page, and a quarter second later
  nothing came back, so no map but the one the page opened on could be seen at all: worse than the second pass, whose
  picks showed at unpause. Nothing in either log names `te_map_widgets.gui` or a callback, so the state's two lines
  both read at load. The close ran; the open (`OpenJournalEntryPanelDontToggle`) didn't, or did nothing. Either the
  button, on the page, went with it before the second line ran, or the close landed after the open had found the page
  still open. The logs can't tell them apart, and the fourth pass doesn't need to: the close and the open run from a widget
  outside the page, two states apart, with the plain open (check 1 above).
- Checks 2–4 not reported.

### Sixth session, 2026-11-05 night (#1424)

The owner's report, "0.25 worked": **check 1 works**, the repainter's quarter-second close and its reopen a tenth
later. Not said: whether paused and running both, or how the blink feels while running (check 1 asks again). Checks
2–4 not reported. The fifth pass tries a twentieth of a second for each (check 1 above) and, from the owner's asks, adds
Devastation, Urban People, Gini Coefficient, Dynastic Wealth and eight census maps and drops Literacy, which vanilla's
own literacy map mode shows.

### Seventh session, 2026-11-06 (#1425 merged)

The owner asked for the see-through page at 20% (it was 30%): the fade works, so **check 2's first half is answered**,
`alpha` binds on the side panel's root. The sixth pass makes it 20% and asks again whether that is right. The same
message asked for the systems' maps, each system tab's map button and a Map Room button in the Timeline Extended
window (checks 9–20), and emissions as a share of the world's rather than an amount.

### Eighth session, 2026-11-06 (#1487 merged)

**The Leading Cause stripes draw** (the owner's screenshot, after running on a save from before the build): orange chronic
illness stripes over most of Britain and France, whose pale fill is infection's, and Home Counties' hover reads
"Leading cause of death: Chronic Illness, 38%" and "Close behind, in the stripes: Infection, 38%". So
`map_color_second` draws on a contextless entry, and the fourth session's missing stripes were `is_player`, not the
Map Room. The first look showed none: the save's 893 counted states held no `te_dg_dc_second` until their next yearly
count (the census counts each state in its own month). Check 7's fade question, whether the palest causes read apart,
is still open.

## Not tested here

- Whether `map_color` takes a scope path (`value = owner.color`, prep C21): left out, since a field the engine rejects at
  load can drop the whole entry it sits in. Try it in an entry of its own.
- Multiplayer: two players share the Map Room's pick and the maps' viewer (global variables). Whether that is
  acceptable is a design call (check 20).
- `add_involved_country` on the Map Room (its own scripted buttons would unlock), and whether an involved country sees
  a contextless entry in its journal.

## When it's done

- Delete the `TE_JMAP pick` debug line in `te_jmap_set_selector` and the repainter's `TE_JMAP reopen` line
  (`te_jmap_reopen_log_sgui`) once check 1 settles the repaint's timing.
- Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) in a PR of its own: it touches its events,
  `scripts/nightly_audit_select.py` and `scripts/image_pipeline/event_image_prompts.py`.
- Give the Banking and Demographics chapters a line each if a map grows beyond the introduction's paragraph
  (`docs/player_guide/01-introduction.md`, which covers the map buttons, the Map Room and the eye).
