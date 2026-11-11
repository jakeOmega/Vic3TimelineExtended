# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Tenth pass, 2026-11-11 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). The first pass (#1410, #1414) was
built ahead of the in-game checks and answered most of them; the second (#1417) rebuilt the Map Room on those answers,
and the third (#1420) added what its play-test asked for: picks that repaint a paused map, and the see-through journal
page. Its picks closed the page for good, so the fourth (#1424) moved their repaint to a widget outside the page, which
worked. The fifth (#1425) tried a shorter repaint, added Devastation, Urban People, the Gini coefficient, Dynastic
Wealth and eight more census maps, and dropped Literacy, which vanilla's own literacy map mode shows. The sixth adds a
map for eight of the mod's systems, each on its own entry and in the Map Room (below), a map button in each of their
tabs and a Map Room button in the Timeline Extended window, and fades the see-through page to 20%. The seventh adds
five maps to the Map Room alone: Tourism Appeal, Base and Current Comfort, GDP per Capita and the Crowding Penalty.
The eighth (2026-11-07) fits nearly every map's colors to the world's range as it stands, adds a Power Grids map, and
lengthens the repaint's two waits. The ninth (2026-11-08, the owner's ask) adds nine: City Rank, Company HQs (with
stripes for regional headquarters), Armed Forces and War Dead, then Ownership, Population Growth, Family Planning,
Health Care and Fighting-Age Men. The tenth (2026-11-11, the owner's ask) adds five, Capitalists, Aristocrats, Clergymen,
Academics and Trade Volume, and puts the picks in seven collapsible categories (§ Buttons).
`docs/testing/journal-map-modes-playtest.md` lists what is still open, and this file says which parts rest on an
unverified engine fact. Update both as the answers come in.

## How a Journal Entry Paints the Map

Vanilla 1.15 gives a journal entry three optional blocks (`game/common/journal_entries/journal_entries.md`):

- `map_color` returns a color for a state: a named color (`value = "te_jmap_no_data"`), an RGB triple, or
  `lerp = { min_color max_color factor }` with a 0–1 factor. It takes `if` / `else_if` like a script value (vanilla's
  ACW, Meiji and Hungry Forties entries branch on it), and a branch that matches nothing leaves the state unpainted.
- `map_color_second` is the same, drawn as stripes over the first color (vanilla's Great Game and Forest of Bayonets
  stripe through the state's `owner`). It draws on a contextless entry too (the Map Room's Leading Cause, seen
  2026-11-06), so the nothing it drew under `owner ?= { is_player = yes }` (2026-11-05) was `is_player`: a map can't
  single out the player's own states.
- `map_tooltip` is an effect block that only prints: `custom_tooltip_no_bullet = key` per branch. Its loc reaches the
  state as `[THIS.GetState…]` (`GetName`, `GetOwner.GetName`, `CalcTurmoil|v%1`, `GetLiteracy|%1v`,
  `MakeScope.Var('x').GetValue`).

**The root is the state being painted**, every state in the world, so `owner` is that state's country, not the player.
A map of the player's own data, or a map whose look the player picks, needs something every state can read:
`map_color` reaches neither `scope:journal_entry` nor its owner (the first pass's scope probe painted blue, 2026-11-05).
A contextless entry's `scope:journal_entry` isn't set there either. So the Map Room's pick is a global variable
(`te_jmap_selector`, `common/script_values/te_journal_map_values.txt`), and two players in one game share it.
`map_color` is re-evaluated as the game runs (a weekly tick map stepped with the page open), and a new value shows at
the next tick, or at once when the page opens again (paused too). Land no branch paints draws dark grey; water keeps
its normal look.

**The engine shows the map itself, and only while the entry's page is open.** `mm_journal_entry_map_data`
(`gfx/map/map_modes/map_modes.txt`) is `is_visible = no`, "overriden in code", and no vanilla `.gui` names it. Seen
2026-11-05: the map goes when the page closes, the lens toolbar's lock doesn't keep it, a listed copy of the mode
paints nothing with no page open, `SetTempMapModeByKey` on it paints nothing, and a tab showing the entry's content
(Banking's, in the Budget panel) doesn't trigger it. So every "show on the map" button here opens a page, and every
journal page has a see-through eye (below) to look past it. An inactive entry's page opens from a button and paints
too.

**Cheap reads only.** Every value runs once per state, as the game runs, so
the maps read stored variables and engine figures, never walk pops. Company HQs reads state variables the global
monthly pulse stores from a walk of each state's buildings (`te_jmap_store_hqs`), so the paint walks none. A figure behind a long `state_region` chain is
stored by the refresh that already computes it: tourism's Base Appeal (some 700 branches) and Local Climate's
penalties (eight chains of 680). Each map's color comes from a factor, 0–1, on a curve fitted to the world as it
stands (below). Colors are named in `common/named_colors/te_journal_map_colors.txt`, one family per map.

**Fitted to the world** (eighth pass, 2026-11-07, the owner: "people are not going to it to see that the world GDP/c
average has gone up, they want to see the regional differences"). Until then each curve was fixed and historical (life
expectancy 25–80), so a color meant the same in 1850 and 1950, and a 1950 world sat in one corner of the palette. Now
every map but two runs its colors from the world's low to its high: the fifth lowest and fifth highest of the states it
paints (`TRIM` = 4 left out at each end, so one outlier doesn't flatten the rest; the extremes where fewer have a
figure), which `te_jmap_range_<map>` measures with `ordered_state` into `te_jmap_rng_<map>_lo` / `_hi`
(`common/scripted_effects/te_journal_map_ranges_generated.txt`). A pick measures its map before the page reopens
(`te_jmap_set_selector` calls `te_jmap_refresh_range`), and the global monthly pulse measures the pick's map again
and the two the systems' entries draw (Emissions, Grandeur: `te_jmap_refresh_entry_ranges`;
`te_journal_map_on_actions.txt`), so an observer's game measures too. Before the first measure a map paints on the
old fixed curve's ends. Each curve keeps its shape on the new span, its knots now fractions of it (turmoil still half
its color in the first fifth), and no span is narrower than the map's `min_span` (turmoil 10 points, life expectancy 10
years), so a world where every state stands alike doesn't paint noise as contrast. A map whose midpoint means
something (replacement fertility 2.1, no natural change, no net migration, even sexes, no comfort penalty, Dynastic
Wealth's 50) keeps it: below it the colors run from the world's low to it, above it to the world's high, each side on
its own span (at least `min_half`), and where the whole world is on one side, that side runs over the world's span from
the neutral color at its end nearest the midpoint. Life expectancy, infant mortality and median age split at their
range's middle. GDP per capita keeps a doubling scale, from the world's low (at least £0.01) to its high (at least four
times it). Each fitted pick's tooltip prints its range now (`GetPlayer.MakeScope.ScriptValue('te_jmap_<map>_lo')`).
Comfort's two maps share Base Comfort's range (`range_of`), so they still compare. Four stay fixed: Agent Networks
(0–100, its tiers at 50 and 75 are what it shows), the paleness of the leading cause and of Ownership's leading holder
(a share on a categorical map) and City Rank (a rank is already a place in the world, and its first 20 are tourism's
Cities bonus). Population Growth keeps its midpoint at none, as Natural Change does. Armed Forces, Company HQs,
War Dead and Trade Volume take GDP per capita's doubling scale, since their counts run over orders of magnitude.
Comfort's and Emissions' green removal, the census's "no data" grey and the categorical maps are unchanged.

**The curves are generated** (`scripts/generators/gen_journal_map_scales.py` →
`common/script_values/te_journal_map_scales_generated.txt`, `te_jmap_<map>_factor`, and the range effects above). A
fitted map's row names its selector, the states it paints (`where`, which `test_journal_map_scales.py` compares with
the Map Room's branch) and its shape: `rel`, `rel_mid` or `rel_doubling` over one of the fixed shapes. A script value takes no arguments
and a paint runs no effect, so one shared curve can't be fed each map's figure (`te_sqrt`'s input is a variable an
effect sets); the generator writes each map's tree from a table row instead, using one of four shapes: linear, a soft
cap (straight to a soft bound, then `SLOPE_RATIO`, 4, times shallower to a hard one, so the common values get most of
the color and the extremes still differ), diverging (0.5 at a midpoint, each side straight or soft-capped) and doubling
(the same share of the color per doubling, a logarithmic scale in straight pieces, for GDP per capita's hundredfold
range). Changing a shape changes every map using it. Each tree reads its figure only inside an `if` on its `has_variable` guards (a
guard in the same `AND` doesn't stop the read where the engine builds a tooltip, #1418). A three-color map's
`map_color` splits at `factor < 0.5`, so its midpoint lives only in the table, and reads `_lower` and `_upper`, the
factor doubled and doubled less 1.

## The Map Room

`je_te_map_room` (`common/journal_entries/te_journal_maps.txt`) is a map with no system of its own: several maps on one
entry, in no country's journal.

- **Contextless, nobody involved.** `context = none`, `should_be_involved` and `should_show_when_not_involved` both
  `always = no`, `is_shown_when_inactive = { always = yes }` and no `possible`: the entry is active from the game's start
  and listed in no journal. A button opens its page at the first click (`GetPlayerJournalEntry` finds it). The first
  pass proved the shape with a test entry (`je_te_map_hidden_world`, 2026-11-05).
- **Several maps.** `map_color` is an `if` / `else_if` ladder on `te_jmap_selector`
  (`common/script_values/te_journal_map_values.txt` lists the numbers). The world's: 1 turmoil, 6 devastation (both the
  engine's own figures, soft-capped at 20%), and from the yearly walk, which runs whatever the Demographics rule, 15
  urban people (`te_dg_urban_share`), 16 the Gini coefficient (`te_dg_gini`, 0.30–0.80) and 17 Dynastic Wealth
  (`te_dg_wc`, 0–50–100, diverging where its effects turn from dispersed to concentrated property); 29 GDP per capita
  (`gdp_per_capita`, the state's `gdp` over its people, a tenth of the color per doubling from £0.25 to £256: a rich
  country stands near £1 in 1836, £8 in 1917, £60 in 2023) and 30 the Crowding Penalty (`migration_crowding_pull_pct`,
  live, as the state panel's tile reads it, soft-capped at 45%, the 10× knee, to 145%), both engine figures; and two
  figures a refresh stores for the map: 26 tourism's Base Appeal (`te_tourism_base_appeal`, the state panel's row, which
  `te_update_tourism_modifier` stores monthly, 20%–100%) and Local Climate's comfort, 27 Base Comfort before any
  technology's relief (`te_climate_base_penalty`, stored by `te_update_local_climate_modifier` from
  `te_climate_penalty_raw`) and 28 Current Comfort after the owner's (`te_climate_penalty_applied`, the penalty in
  force), both yearly and on one curve and palette, diverging at none: a mild or sunny winter's draw green down to −10.8, a cost
  red, soft-capped at 30 to the cap of 80. The census's, from each state's figures (`te_demog_effects.txt`'s header): 3 life
  expectancy, 10 infant mortality, 4 fertility, 5 median age, 14 aged 65 and over and 12 sex balance from a state's first
  seed; 9 births, 8 deaths and 7 natural change per 1,000, 13 net migration and 11 the leading cause of death only once
  the state has stepped a full year (`te_dg_stepped` above 0, as the panel gates them: a seed writes those rates as 0).
  Every map that reads a stored figure shows grey (`te_jmap_no_data`) for a state without one, through one `OR` branch
  that lists them all; the hover has two, "No census figures yet" for the census and walk maps and "No figure yet" for
  tourism and the two comfort maps, whose refreshes run within a month (Local Climate's first application keys on
  `te_climate_base_penalty`, so an older save fills Base Comfort within a month too). Each curve is fitted to the
  world (above), on the shape of the fixed curve it had until 2026-11-07, whose ends are its range before the first
  measure. Soft caps: turmoil and devastation half the color in the first fifth of the range; deaths per 1,000 70% of
  it in the first 37%; emissions half in the first fifth, grandeur two-thirds in the first third, crowding two-thirds
  in the first 31%. Around a midpoint: natural change and net migration soft on each side, comfort soft above none, sex
  balance, fertility and Dynastic Wealth straight. Linear: births, 65 and over, Gini, urban people, tourism, and life
  expectancy, infant mortality and median age split at the range's middle. Each pick's tooltip gives the range now,
  since the map has no legend. The leading cause is categorical, in the Causes of Death
  pie's colors (`gen_ch_model_pie_textures.py`; the old code 6 draws as war, as the panel's icon does), each faded to
  a pale end of its own hue (`te_jmap_cause_<cause>_pale`) by the cause's share of last year's deaths
  (`te_jmap_cause_factor` on `te_demog_dc_lead_share`, linear from 30% to 90%; states ran 31–97% in 1838, 1940 and
  2020 saves), so a state where a cause barely leads reads apart from one where it takes nearly all. Where the
  runner-up took at least half the leader's deaths (owner, 2026-11-06), the map stripes it over the leader in its own
  pie color: the Map Room's only `map_color_second`, a branch per cause on `te_dg_dc_second` (the census stores the
  next largest slice's code beside `te_dg_dc_lead`, `te_demog_cause_deaths_total`) and `te_jmap_cause_second_ratio`
  (`te_demog_dc_second_share` over `te_demog_dc_lead_share`) at 0.5. A state whose last count came before the
  runner-up was stored has no stripes until its next. Its hover is a branch per cause, and a second line per cause
  names the runner-up where it is striped (a branch, not a `SelectLocalization`, for the reason `map_tooltip`'s header
  gives). The colors aren't mixed: a `lerp` mixes two fixed colors, so a blend of the top two would need a branch per
  pair, and a mixed hue reads as another cause (infection's blue and war's red make a purple near killed by events'
  lavender). 2 was literacy, retired because vanilla's literacy map mode shows it: a save holding 2 shows
  the unpainted map and "Pick a map" until the next pick. 18-25 are the systems' maps, each also on its own entry
  (below).
- **The ninth pass's four** (2026-11-08, the owner's ask). 32 **City Rank**, tourism's ranking of the world's cities
  (`var:state_city_size_rank`, which `city_rank_on_action` sets on the 501 largest by `city_size` each month): the 20
  whose cities earn tourism's Cities bonus by that bonus (`tourism_bonus_from_urban_centers`, +5% at 20th to +100% at
  1st), amber to crimson, the rest steel blue paling a doubling of the rank at a time (`te_jmap_city_rest_factor`), and
  a state the ranking misses pale (`te_jmap_none`). The ranking now clears every rank before it ranks, so a state that
  falls past 501st has none instead of keeping its last for good (it did until this pass; only the map and
  Demographics' Largest Urban States read past 20th). 33 **Armed Forces**, the yearly walk's Soldiers and Officers
  (`te_dg_soldiers`, whatever the Demographics rule), and 35 **War Dead**, the census's war and devastation deaths last
  year (`te_dg_dc_war`, once stepped, as the Causes of Death row): each a doubling at a time, a zero pale and no figure
  grey, on one row of the page because the census shares a country's war dead out to its states by their soldiers
  (`te_demog_share_war_dead`), so the dead show where the soldiers came from, not where they fell. 34 **Company HQs**:
  a state without a company headquarters grey (`te_jmap_no_data`, the owner's spec), one with any by their weekly
  profit summed (`te_jmap_hq_profit`), a doubling at a time, red at a loss or none. Script can't read a company's
  profit (`te_company_effects.txt`), and no link leads from a state or a building to a company, but each company has its
  own headquarters building (its production method follows the company's category), and an ownership building's profit
  is what the levels it owns pay it less its wages: the company's earnings coming home. A headquarters is found by its
  building group (`bg_company_headquarter`, `bg_company_regional_headquarter`), never its type: the engine makes a
  building type per company type (`building_company_basic_fabrics`, `building_regional_company_hbc` ...) from the two
  templates, so `has_building = building_company_headquarter` matches no state, and the first build (#1514) painted
  every state grey (2026-11-08; `test_company_hq_building_tests.py` now fails on a test by template type). The global
  monthly pulse, and a pick of the map, store each state's count, profit and regional count as state variables
  (`te_jmap_store_hqs`: `te_jmap_hq_n`, `te_jmap_hq_wp`, `te_jmap_rhq_n`, removed where none is left), which the
  paint, the hover and the range read through `te_jmap_hq_profit`, `te_jmap_hq_count` and `te_jmap_rhq_count`; so the
  figures are up to a month old, and a load's first month is grey until a pick. Two once-a-game checks, from the global
  monthly pulse after the store: `TE_SELF_CHECK OK|BROKEN hq_found` (`te_jmap_hq_found_selfcheck`, once three countries
  have a company: BROKEN when the store found no headquarters) and `TE_SELF_CHECK OK|BROKEN hq_profit`
  (`te_jmap_hq_selfcheck`, once three states hold one: BROKEN when every headquarters reads exactly 0). hq_found arms on
  companies, not on what the store finds, so a store that finds nothing speaks; the first build's hq_profit armed on
  the same broken test it measured and never spoke. Play-test check 24 names both fallbacks. A state with a regional
  headquarters is striped gold over its color (grey where it holds no headquarters of its own), the Map Room's third
  `map_color_second` branch, and its hover adds a line counting them (`te_jmap_rhq_count`).
- **The ninth pass's second round** (2026-11-08, the owner's pick from the eighth's suggestions). 36 **Ownership**: who
  holds the state's capital, the yearly walk's building levels (`te_dg_lv_priv`, `_self`, `_ctry`: ownership buildings,
  subsistence farms and government buildings left out), whatever the rule. The leading holder's color (private gold,
  their own workers green, the state red; `te_jmap_own_lead`, a tie to the first) fades to a pale end of its hue by its
  share (`te_jmap_own_factor`, fixed, 40% to 100%), as Leading Cause does; under one level of capital
  (`te_demog_wc_capital_levels`, Dynastic Wealth's own test) pale. No stripes. 37 **Population Growth**: the people at
  one yearly walk against the last (`te_jmap_pop_growth`, per 1,000, from `te_dg_walk_pop_prev`, kept every game),
  diverging at none; it counts land too, so a state that took or gave up provinces jumps. The census's three, gated on
  it: 38 **Family Planning**, its means to plan a family (`te_dg_means`: traditional methods and technology's
  contraception, as far as literacy spreads them, plus Family Limitation's line), the hover adding the older ways
  (Late Marriage's age at marriage, `te_demog_marriage_age`, and Birth Spacing's share): those erode as the means
  spread, so the means are the transition's map; 39 **Health Care**, health-care access (`te_dg_acc`), the hover adding
  where it is heading (`te_demog_access_target`) and the mothers who die in childbirth (`te_dg_m_mat`); 40
  **Fighting-Age Men**, the conscription pool (`te_dg_fam`, men of calendar age 20 or more and biological age 39 or
  less) over the people (`te_demog_fam_share`, what the conscription term reads), the hover adding its share of the
  men.
- **The tenth pass's five** (2026-11-11, the owner's ask). 41 **Capitalists**, 42 **Aristocrats**, 43 **Clergymen**
  and 44 **Academics**: each class's share of the state's people (`te_jmap_<class>_share`), from counts the yearly walk
  stores whatever the Demographics rule (`te_dg_capitalists`, `te_dg_aristocrats`, `te_dg_clergy`, `te_dg_academics`),
  as Armed Forces' soldiers. They are counted by three calls of the Map Room's own in the walk (`te_jmap_class_walk_init`,
  `_pop`, `_store`, `te_journal_map_effects.txt`), not in the census's helpers, which set nothing outside the census
  (`test_demographics_registry.py`, `TestWorkWalk`); `test_demographics_golden.py` leaves the three lines out of the
  walk it pins. Capitalists and Academics gather in a few great cities, so half their color goes by a fifth of the
  world's range; Aristocrats and Clergymen run straight. 45 **Trade Volume**: the state's owner's trade with the world
  market (`te_jmap_trade_value`, `total_trade_value`, the figure vanilla's Free Trade entry `je_liberalism_2` reads), a
  doubling at a time, a country that trades nothing pale. Script has no state's share of its owner's trade, so every
  state of a country paints alike; a state with a Trade Center stripes orange (the Map Room's fourth `map_color_second`
  branch, `has_building = building_trade_center`, a plain type unlike the headquarters), and its hover gives the
  Trade Center's levels (`te_jmap_trade_center_levels`).
- **Picks are scripted GUIs on a page widget, not scripted buttons.** The engine locks a scripted button for a country
  not involved in its entry ("Countries that are not involved in the Journal Entry may not take this action"), and
  nobody is involved in the Map Room. So `te_jmap_pick_<map>_sgui` (`common/scripted_guis/te_journal_map_sguis.txt`)
  set the global pick with the player as root, and `te_jmap_pick_row` (`gui/te_map_widgets.gui`) draws them on the page
  through the entry's `widget` (`gui/journal_entry_widgets/te_map_room_widget.gui`, above the description; a widget
  draws on a contextless page, 2026-11-05). A pick's `is_valid` is false while it is the pick, which its button draws
  pressed (`down`, seen working 2026-11-05); the census maps' `is_shown` hides them while the census doesn't run.
- **A pick repaints at once.** Each pick button (`te_jmap_pick_button`) runs its scripted GUI, then fires
  `te_jmap_repaint` with `PdxGuiTriggerAllAnimations`. That state sits on `te_jmap_repainter`, a zero-size scripted
  widget outside the page (`gui/te_map_widgets.gui`, registered in `gui/scripted_widgets/te_systems_window.txt`), which
  carries the Map Room as its own `datacontext`. A tenth of a second after the click it closes the page
  (`InformationPanelBar.ClosePanel`), for the scripted GUI's effect to land, and its next state,
  `te_jmap_repaint_open`, opens the page again a fifth of a second later with the plain `OpenJournalEntryPanel`: the
  page is closed by then, so the toggle opens it. Reopening repainted a paused map (2026-11-05). The third pass ran both
  calls from a state on the pick button itself, `ClosePanel` then `OpenJournalEntryPanelDontToggle`: the page closed
  and stayed closed, with no log line (fifth session). The reopen logs `TE_JMAP reopen` first. It worked with a quarter
  second's close and a tenth's reopen (sixth session); the fifth pass's twentieth each sometimes left the page closed
  (the owner, 2026-11-07), so the close now waits a tenth and the reopen a fifth (check 1).
- **Nothing to inherit.** `transferable = no`, `can_revolution_inherit = no`; the pick is global.

### Why not a country entry added by a button

The first pass's Map Room, `je_te_map_host`, was a country entry kept out of the journal by a variable its
`is_shown_when_inactive` and `possible` read, and added by `add_journal_entry`. The add never worked: every country
holds an inactive copy of a country entry with its own activation triggers from the game's start, and
`add_journal_entry` is refused while one exists ("already has a journal entry of type", 2026-11-05). The variable then
made the copy shown (the journal's Potential section) and the engine activated it at its own check, up to two weeks
later. An entry with neither trigger has no copy until added, so `add_journal_entry` would work on it, but then nothing
takes it out again short of an outcome, which leaves it in the concluded tab. The contextless entry needs neither.

## The See-Through Page

`gui/journal_entry.gui` (the mod's copy of vanilla's panel) puts a crossed-out eye (`visibility.dds`) in the header's
top-left button slot, which vanilla leaves empty on this panel, on every journal page. It toggles a GUI flag,
`GetVariableSystem` key `te_je_see_through`, and the panel's root binds `alpha` to it: 0.2 while set (the owner's pick
after seeing 0.3, 2026-11-06), so the page's map shows through. The flag outlives a reopen, so the Map Room stays faded from pick to pick; the header's close and
back buttons clear it (vanilla's own lines first; Escape runs the close), and so do the two map buttons before they open
a page. Clearing on `_show` would unfade the page at every pick, since a pick's reopen fires it. Leave a faded page by
opening another panel and the next journal page opened from the journal is faded too. The faded page still takes clicks: the window's frame is a `clickthrough_blocker` in no block the panel
can override, and a fold that hid the content would leave the same full-height frame. On every page because the GUI
can't tell which entries carry a map, and vanilla's own map entries gain from it too. `alpha` on a side panel's root
works (the owner saw the page fade, 2026-11-06).

## The Systems' Maps

Eight of the mod's systems have a map (sixth pass, owner's ask, 2026-11-06), selectors 18-25, and the Power Grids a
ninth (31, 2026-11-07). Each but the Seabed's and the Power Grids' is drawn twice: by the system's own entry, whenever its page is open, and by the Map Room, on a pick. Both ask the same
state-scope triggers in the same order (`common/scripted_triggers/te_journal_map_triggers.txt`, one per color band), so
the two pages paint alike; `test_journal_map_modes.py`'s parity test compares the entry's ladder with the Map Room's
branches for its selector. Each map ends in a branch that takes every state left, so none needs the "no data" `OR`.
Each pick shows while its system's rule is on.

| # | Map | Entry | Reads |
|---|---|---|---|
| 18 | Emissions | `je_global_warming` | The state's share of the world's emissions last year: its yearly snapshot `gw_state_emis` over `gw_g_global_emis` (`te_jmap_gw_share`). A share, not an amount (owner), so a color means the same in 1850 and 2000; soft-capped, half the color by 1%, all at 5%. Net removal green, no snapshot yet grey |
| 19 | Nuclear Weapons | `je_nuclear_program` | The viewer's own country, then the countries hosting its weapons (`nd_hosts_weapons_of`), under its umbrella (`nd_is_guaranteed_by_treaty`, `nd_under_umbrella_of`), and those whose independence it guarantees while the world believes it armed (vanilla's `guarantee_independence` article, gated on the viewer's `nd_believed_armed`, never `nd_is_armed`: in multiplayer another player can see the viewer's map); every other nuclear power as the world sees it (`nd_believed_armed`, the public estimate in the hover: nuclear.md's privacy rule) |
| 20 | Agent Networks | `je_covert_warfare` | The viewer's network in each country, 0-100 (`te_jmap_net_strength`: the viewer's `iw_nets` containers, `iw_net_strength`) |
| 21 | United Nations | `je_united_nations` | Grey before the founding (`un_founded`); a mission's state in its type's color (`un_state_mission_type`), over the headquarters (`building_un_headquarters`), permanent members and members (the `_on` mirrors) |
| 22 | Political Models | `je_cultural_hegemony` | The owner's `ch_model_census`, in the model pie's colors (`gen_ch_model_pie_textures.py`, checked by a test); the hover names it through `ch_country_model_text` and marks the leading power |
| 23 | Ocean Basins | none | The state's `te_seabed_basin`, set for every coastal state in the first month and again each January for states made since (until 2026-11-06 only once a country had Abyssal Plain Mining); a coastal state still without one hovers as not yet recorded (`te_jmap_seabed_unrecorded`) |
| 24 | Grandeur | `je_grand_monuments` | `gm_state_grandeur`, straight to 75 (the panel's top frame), then soft to 225 |
| 25 | Colonies | `je_colonial_empire` | Each colony (`te_jmap_ce_colony`, below) and each colonial subject's state by its empire's band (`colonial_empire_tier`, the monthly snapshot of the band ladder); an empire's other states taupe |
| 31 | Power Grids | none | Each station's state on a grid this month (`te_grid_hub`) in its grid's color, one of twelve (`te_grid_map_color`, `te_jmap_grid_<n>`), the hub striped white (`te_grid_rec_supply`, the record only a hub holds; the Map Room's second `map_color_second` branch); a station on no grid grey (`te_grid_flow` without a hub); the hover names the hub and the grid's stations (`te_grid_region_size_disp`). No game rule, as the Power Grids tab has none (owner's ask, 2026-11-07) |

**The viewer.** A paint can't reach the player (`is_player` drew nothing under `owner`, 2026-11-05), so the maps of
"your" country (19, 20) are drawn for `global_var:te_jmap_viewer`: every pick and map button sets it to the player's
country (`te_jmap_note_viewer`, `te_journal_map_effects.txt`), and so does a player's monthly pulse
(`te_journal_map_on_actions.txt`), so an entry's page opened from the journal has one too. Like the pick, it is one for
every player in a multiplayer game: there the last player to pick sees their own deterrent and networks, and another
player looking at those maps sees the same viewer's, a known limit. Whether `global_var:` holding a country compares
in a paint (`this = scope:…` after `save_temporary_scope_as`) is unverified (play-test).

**What the systems keep for the maps.** A paint can't walk pops, so two systems now store a figure where they already
computed it:
- Global Warming: `gw_snapshot_country_emissions_effect`, at each capital's yearly pulse, writes each state's
  `gw_state_greenhouse_gas_emissions` to `gw_state_emis` first and sums them into `gw_disp_country_emis`
  (`gw_country_emis_from_states`), the same total as before with one walk of the pops.
- Colonial Empire: `colonial_empire_refresh_display` marks each colony with its owner (`te_jmap_ce_colony`, 62 days,
  so the marks go when the entry stops refreshing them) and counts `colonial_empire_colony_count` from the marks: one
  colony test per state, as before.
- Power Grids: `te_grid_map_color_effect` (`power_grid_effects.txt`, last in `te_grid_balance_region_effect`, after the
  record) colors each grid as the monthly run balances it, a greedy coloring: the hub's color from last month unless a
  state bordering a member, on another grid, holds it (`te_grid_map_color_taken`), else the first of the twelve none
  does; every member stores it as `te_grid_map_color`, which `te_grid_idle_station_effect` and
  `te_grid_clear_state_effect` remove. A grid keeps its color while its hub does; one whose hub moves takes the new
  hub's last color, usually the same grid's. A neighbour not yet balanced this run is read at last month's color, and
  grids joined only by cable aren't neighbours. Twelve colors run out only around a grid with twelve differently
  colored neighbours, which then keeps its own.

## The Banking Map

`je_banking_cycle` (`common/journal_entries/je_banking.txt`) colors each country by its cycle's phase, the panel's own
bands (`banking_cycle_is_*`, `market_triggers.txt`), panic red to frenzy magenta, with yellow stripes where
`banking_cycle_bubble_risk_high` holds (the overview's crash-risk badge). A country whose cycle has not started is grey;
one without the entry is unpainted. The tooltip names the country, the phase word (`banking_dash_phase_word`) and the
cycle value. Every country holds the entry, active from the engine's first check (`possible = { always = yes }`), so
this is a world map read from each state's owner, and its button needs no `IsActive` gate. The stripes are unconfirmed
in game, since nothing overheats early on.

## Buttons

`gui/te_map_widgets.gui`. Every button that opens an entry carries it as the button's `datacontext`
(`GetPlayerJournalEntry('<key>')`) and passes `JournalEntry.AccessSelf`: inside a callback, `GetPlayerJournalEntry`
fails at load whether bare or ended with `.AccessSelf` (`gui_modding_guide.md` gotcha #29).

- `te_jmap_demog_map_button`, in the Demographics tab's header (`te_demog_window_body`, so the Population panel's tab and
  the Timeline Extended window's), left of the "?": one click picks life expectancy and opens the Map Room.
- `te_jmap_banking_map_button`, in the Banking tab's header (`te_banking_tab_body`): opens `je_banking_cycle`.
- `te_jmap_<system>_map_button` (gw, nuclear, covert, un, ch, seabed, gm, ce, grid), in each system's tab
  headers (the Power Grids tab's since 2026-11-07): one click picks the system's map and opens the Map Room, as the Demographics button does. The Map Room, not
  the system's entry: several entries are held by only some countries or not yet (the nuclear program before its
  technology, covert warfare before its slots, a monument's owner, an empire with colonies), and a button on an entry
  nobody holds has nothing to open. The entry paints the same map when it is opened from the journal.
- `te_jmap_window_button`, in the Timeline Extended window, left of its Full Screen / Side Panel toggle in both frames
  (`te_systems_window_toggle`): opens the Map Room on the last pick, then closes the window, which would cover the page.
  The close comes last, in case a button whose window hides mid-click loses the lines after it.

Every map button clears the see-through flag before it opens a page.
- `te_jmap_pick_row`: the Map Room's picks on its page, in seven categories (2026-11-11, the owner's ask), each a
  collapsible section: a header (`te_jmap_category_header`, the Demographics tab's `section_header_button` at 470 wide)
  over its rows (`te_jmap_category`), shown while the category's client-side flag `te_jmap_cat_<key>_open` is set. Every
  category starts collapsed, a long list (`gui_style_guide.md` § Sections), and the flags outlive a pick's reopen, as the
  see-through flag does, so a category opened stays open from map to map. Society (Turmoil, Devastation, Urban People);
  Classes (Aristocrats, Clergymen; Capitalists, Academics); Economy (GDP per Capita, Gini, Dynastic Wealth; Ownership,
  Company HQs, Trade Volume); Migration and Cities (Base Comfort, Current Comfort, Crowding Penalty; Tourism Appeal, City
  Rank); Military (Armed Forces, and Fighting-Age Men and War Dead while the census runs); Systems (the systems' nine in
  rows of three, Grandeur, Colonies and Power Grids last); Census (its maps three to a row, Population Growth, the walk's,
  beside Net Migration, and a last row of Health Care and Family Planning). `test_journal_map_modes.py`'s
  `CategoriesTest` holds every pick to one category.

The play-test's harness is gone: the debug strip, the scope probe (selector 6), the Potential probe entry and the
listed copy of the journal map mode, each answered (`docs/testing/journal-map-modes-playtest.md`, fourth session).

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; give each `lerp` its factor as a row in `gen_journal_map_scales.py`'s `SCALES` and
   re-run it (`test_journal_map_scales.py` checks the trees and that the map reads no factor the table lacks). Fit it
   to the world unless its numbers mean something fixed (a row with `sel`, `where` and a `rel*` shape: the range
   effect, the dispatcher's branch and the trees come with it), give its pick's tooltip the range
   (`te_jmap_<map>_lo` / `_hi`), and mark it `entry` if a system's own entry draws it.
2. A system with no entry borrows the Map Room: a new selector number, its branches in `map_color` and `map_tooltip`, a
   pick scripted GUI and its `te_jmap_pick_button` in one of `te_jmap_pick_row`'s categories, and loc for both. A map that reads a stored
   figure joins `map_color`'s "no data" `OR` and one of `map_tooltip`'s (`test_journal_map_modes.py` checks it). A
   figure behind a long `state_region` chain is stored by the refresh that already computes it, not read live
   (tourism's and Local Climate's are the pattern).
3. A map on both an entry and the Map Room asks shared triggers (`te_journal_map_triggers.txt`) in the same order in
   both, and joins `SYSTEM_MAPS` in `test_journal_map_modes.py`, whose parity test compares them.
4. A "show on the map" button opens a page: the entry's (`te_jmap_banking_map_button`) when every country holds it,
   or the Map Room on the system's pick (`te_jmap_gw_map_button`) when not. A tab showing an entry's content doesn't
   trigger its map.
5. Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) once one map is seen working in game.
