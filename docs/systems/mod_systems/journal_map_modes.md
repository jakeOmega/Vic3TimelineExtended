# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Fifteenth pass, 2026-11-16 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). The first pass (#1410, #1414) was
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
Academics and Trade Volume, and puts the picks in seven collapsible categories (§ Buttons). The eleventh (the same
day, the owner's ask) turns Trade Volume into Trade Capacity, each state's own, and adds Investment. The twelfth
(2026-11-14, the owner's ask: "a section below the mode selection where you can change some aspects of the plotting")
gives the Map Room two options, Area and Outliers (§ The Map Room's Options). The thirteenth (the same day, the
owner's pick of the assessment that followed: "I'll go with your recommendation", and of the eight maps that run both
ways from a midpoint, "What about symlog?") adds a third, Scale: the map's own curve, Linear, Logarithmic or Ranked
(§ The Map Room's Options, Scale). The fourteenth (the same day, the second half of that pick) adds the last the
owner named, Color: the map's own colors, colorblind-safe ramps or greyscale, and rewrites the 35 fitted picks'
tooltips so that each is true under every scale and color (§ The Map Room's Options, Color). The fifteenth
(2026-11-16, the owner's ask: "a population density map mode") adds Population Density, people per km² of land.
The sixteenth (2026-11-23, #1974, the first of four the owner asked for: "I'd like the modes to be grouped more by
theme than by game system or effect") regroups the picks by theme in eight groups and generates them, with their
scripted GUIs, from one table (§ Buttons), and retires the Cartographic Survey. The seventeenth (the same day, #1975,
the second) maps every pop type by its people and by its share of the people, with a Count/Share switch in Map Options,
all from one table of classes (§ The Class Maps). The eighteenth (the same day, #1976, the third) adds ten maps of
living standards, the economy and politics, Literacy among them on its old selector (§ The Map Room, "The eighteenth
pass's ten"). The nineteenth (the same day, #1977, the last of the four) adds five: four engine figures the mod reads
as a value for the first time, each with a once-a-game self-check, and a count of the yearly walk (§ The Map Room,
"The nineteenth pass's five"). The twentieth (2026-11-26, the owner's ask: "what states are reachable by bomber, by
sub, and by ICBM") adds Nuclear Reach (§ The Map Room, "The twentieth pass's one").
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
paints (`TRIM` = 4 left out at each end, so one outlier doesn't flatten the rest), which `te_jmap_range_<map>`
measures with `ordered_state` into `te_jmap_rng_<map>_lo` / `_hi`
(`common/scripted_effects/te_journal_map_ranges_generated.txt`). Since the twelfth pass the measure first counts the
states it will order and takes the trim from the count, and the Map Room's own ranges follow its options (§ The Map
Room's Options): under the defaults a range is what it was wherever ten states or more have a figure. A pick measures
its map before the page reopens (`te_jmap_set_selector` calls `te_jmap_refresh_range`), and the global monthly pulse
measures the pick's map again and the two the systems' entries draw (Emissions, Grandeur:
`te_jmap_refresh_entry_ranges`; `te_journal_map_on_actions.txt`), so an observer's game measures too. Before the
first measure a map paints on the old fixed curve's ends. Each curve keeps its shape on the new span, its knots now fractions of it (turmoil still half
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
War Dead, Trade Capacity, Investment, Population Density, every class's count (#1975), Population and GDP (#1976)
and Vacant Jobs (#1977)
take GDP per capita's doubling scale, since their counts run over orders of magnitude.
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
  lavender). 2 was literacy, retired in the fifth pass because vanilla's literacy map mode shows it, and is Literacy
  again since the eighteenth (below). 18-25 are the systems' maps, each also on its own entry
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
  and 44 **Academics**: each class's share of the state's people, from counts the yearly walk stores whatever the
  Demographics rule, as Armed Forces' soldiers. Since the seventeenth pass (#1975) the four are the share maps of a
  family of thirty, every pop type by its people and by its share, generated from one table (§ The Class Maps), and
  keep their selectors. Capitalists and Academics gather in a few great cities, so half their color goes by a fifth of
  the world's range; Aristocrats and Clergymen run straight.
- **The eleventh pass's two** (2026-11-11, the owner's ask). 45 **Trade Capacity**: the state's own Trade Capacity
  (`te_jmap_trade_capacity`: `modifier:state_trade_capacity_add`, which a Trade Center's `pm_trade_center` gives its
  state, 10 a level fully staffed, with a company flagship's or a treaty port's on top, times 1 plus
  `modifier:state_trade_capacity_mult`, the trade laws', principles' and companies'), read live, a doubling at a time, a
  state with none pale. The tenth pass's Trade Volume painted the owner's `total_trade_value` here, every state of a
  country alike, and striped the Trade Centers; the owner asked for the state's Trade Center instead, so the stripes
  are gone and the owner's trade is the hover's second line (`te_jmap_trade_value`), its third the Trade Center's
  levels (`te_jmap_trade_center_levels`, `has_building = building_trade_center`, a plain type unlike the
  headquarters). A state's trade itself isn't readable cheaply: `state_trade` compares one good's units at a time.
  Unverified (play-test check 28): that the state's read of the multiplier carries its country's lines, and that it
  carries what the building's throughput adds. 46 **Investment**: what the state's owners pay into their country's
  Investment Pool a week, estimated (`te_jmap_invest_value`). The engine takes a share of the dividends the state's
  owners are paid (`state_<pop type>_investment_pool_contribution_add`, raised by `_efficiency_mult`); script reads
  neither a pop's dividends nor a building's shares, so the estimate is the weekly profit of the buildings the owners
  sit in, in profit only, found by building group as the headquarters are, times the share their leading owners
  reinvest, read in the state: capitalists' for Financial Districts and company headquarters
  (`bg_financial_districts`, `bg_company_headquarter`; `te_jmap_invest_rate_cap`), aristocrats' for Manor Houses
  (`bg_manor_houses`; `te_jmap_invest_rate_ari`). Left out, and said in the pick's tooltip: levels their own workers
  own and the government's reinvested dividends, whose shares script can't split; the clergy's and bureaucrats' Manor
  Houses count at the aristocrats' share, and a regional headquarters pays its company's home. A doubling at a time, a
  state that pays nothing pale. `te_jmap_store_invest` stores the two sides as state variables (`te_jmap_inv_cap`,
  `te_jmap_inv_ari`, removed where both are 0) at a pick of the map and from the global monthly pulse while it is the
  pick (`te_jmap_monthly_invest`), so the world's buildings aren't walked for a map nobody is looking at; the paint,
  the hover and the range read them through `te_jmap_invest_cap`, `_ari` and `_value`. One once-a-game check after
  the monthly store: `TE_SELF_CHECK OK|BROKEN invest_rate` (`te_jmap_invest_selfcheck`, once three states hold an
  owners' building in profit: BROKEN when none stores a contribution, so the state's read of the reinvested share
  doesn't carry its country's base). It rests on the Company HQs map's unverified fact too, that an owners' building
  books its dividends as `weekly_profit` (`hq_profit`). Play-test check 28 names the fallbacks.
- **The fifteenth pass's one** (2026-11-16, the owner's ask). 47 **Population Density**: the state's people per km²
  of land (`te_jmap_density`), read live, as GDP per capita is: `state_population` over the state's land
  (`te_jmap_density_area`), its region's area from the area table (`te_region_area`, which
  `te_region_area_generated.txt` stores on each region at the game's start, the row-weighted pixels of the
  game's `provinces.png`, read through `te_region_area_km2`) times its share of the region's provinces
  (`num_provinces` over `state_region.num_provinces`), so a region split between owners shares its land by
  province: script can't reach a province's own size, and a region's provinces run near one size. A doubling at
  a time, pale lemon to deep wine; a state with no people, or none before the table is written, pale. At the
  1836 start the regions ran from 0.009 (Nunavut) to 734 (Suzhou), median 10, the fifth lowest 0.017 and the
  fifth highest 267: some sixteen doublings, so the scale's floor is 0.01 and its default 0.03125 to 256. The
  hover gives whole people per km² from 10 and hundredths below it, a branch each (a `SelectLocalization` would
  lose `THIS`), then the people and the km². Not the Crowding Penalty's density (`state_population_density`,
  people over arable land and Urban Engineering, which the engine's crowding reads): this is the land itself.
  Play-test check 32.
- **The eighteenth pass's ten** (2026-11-23, #1976, the owner's first tier: "Several of these mirror vanilla lenses.
  They earn a place because a Map Room map already has what vanilla's don't: Map Options' Area ..., Outliers, Scale
  and Color"). Each reads a figure the mod reads as a value elsewhere, is fitted to the world, and has its range in its
  pick's tooltip. **Living Conditions**: 74 **Standard of Living** and 75 **Wealth**, the yearly walk's people-weighted
  means (`te_dg_sol`, already stored, and `te_dg_wealth`, a new sum in the Map Room's own walk calls, `te_jmap_walk_*`:
  each pop's `wealth` times its people over the people), straight, whatever the Demographics rule; 76 **SoL vs
  Wealth**, the two less each other (`te_jmap_sol_wealth`), what a place adds to living standards or takes from them
  beyond its people's wealth (pollution, health institutions, laws, ruler traits, principles, events), diverging at
  none, small in 1836 and growing; 77 **SoL vs Expected**, `average_sol` less `average_expected_sol`, live
  (`te_jmap_sol_expected`), the gap the engine radicalizes on, diverging at none; and 2 **Literacy**, `literacy_rate`,
  live, back on its old selector: the Area option is a reason to have it beside vanilla's lens. **Economy**: 78
  **Unemployment**, the share of the workforce without work (`te_state_unemployment_share`, the mod's one reading of
  the engine's per-person figure), two-thirds of the color by a third of the range; 80 **GDP** (`gdp`) a doubling at a
  time, a state with none pale; 81 **Infrastructure**, `infrastructure` less `infrastructure_usage`, live
  (`te_jmap_infra_balance`), diverging at none: below it a shortfall, which costs market access. **Population**: 79
  **Population** (`state_population`), a doubling at a time, a state with no people pale. **Politics**: 82
  **Radicals vs Loyalists**, `loyalist_fraction` less `radical_fraction` (`te_jmap_loyal_net`), diverging at none;
  its button reads "Radicals/Loyalists", which fits the button's 150 where the full name, three letters longer than
  any other pick's, may not. Unemployment is the one stored figure: a GUI reads `state_unemployment_rate` as none,
  even through a script value (`scripting_best_practices.md`, "The op slots accept ..."), so the hover couldn't read
  it, and the paint, drawn beside the GUI, might not either; `te_jmap_store_unemp` stores it as `te_jmap_unemp` from
  an effect at a pick of the map and from the global monthly pulse while it is the pick (`te_jmap_monthly_unemp`), as
  Investment's figures are, so it can be a month old. The live maps paint every state and leave a state with no
  people out of their range (the row's `paint`, as GDP per Capita's), and their hovers read the state's own data
  functions where vanilla has one (`GetExpectedStandardOfLivingAll`, `GetLiteracy`, `GetPopulationSize`,
  `GetInfrastructureBalance`, `GetNumLoyalists`, `GetNumUnemployedWorkingAdults`), so a hover that read a script value
  as none would still show the engine's figure. Living Conditions now has maps every player sees, so its header no
  longer hides with the census. Unverified (play-test check 34): every live read in a paint, and the hovers.
- **The nineteenth pass's five** (2026-11-23, #1977, the owner's second tier). Four read an engine figure the mod
  never read as a value before, live, through a script value each (`te_journal_map_values.txt`), so the paint, the
  range, the hover and the self-check read one name; each is fitted to the world, with its range in its pick's
  tooltip. **Economy**: 83 **Market Access** (`te_jmap_market_access`: `market_access`, 0-1, min(infrastructure,
  usage) over usage, `vanilla_states_reference.md` § 4.3), straight, crimson at the range's low and pale sage at full
  access, so the cut-off states stand out, every state painted and an empty one left out of the range; it sits beside
  Infrastructure, whose shortfall is what lowers it. 85 **Vacant Jobs** (`te_jmap_vacant_jobs`: `available_jobs`,
  the jobs open in buildings other than subsistence farms), a doubling at a time, a state with none open pale, beside
  Unemployment. **Land and Environment**: 84 **Pollution** (`te_jmap_pollution`: `state_region.pollution_amount`,
  the region's, 0 to 255, so a region's states alike; not the pollution impact the state panel shows, which follows
  it), two-thirds of the color by a third of the range, a clean region pale, beside Emissions. **Living Conditions**:
  86 **Below Expected SoL** (`te_jmap_below_expected`: `population_below_expected_sol`, 0-1, the share vanilla's
  alert prints), straight, beside SoL vs Expected. The hovers read the state's data functions where vanilla has one
  (`GetMarketAccess`, `GetStateRegion.GetPollutionImpact`, `GetPopulationRatioBelowExpectedStandardOfLiving`,
  `GetNumUnemployedWorkingAdults`). **Politics**: 87 **Discrimination** (`te_jmap_unacc_share`), the share of the
  people below Full Acceptance (`pop_acceptance < acceptance_status_5`, 80), a new count in the Map Room's own walk
  calls (`te_dg_unacc`, `te_jmap_walk_pop`), whatever the Demographics rule, straight; "Politics or Living
  Conditions", the owner said, and it sits by Radicals vs Loyalists, since acceptance moves radicalism and turmoil.
  It reads nothing new to the mod (`pop_acceptance` is civil rights' and the culture merges' per-pop read), so it has
  no self-check; the four engine figures each have one, once a game from the global monthly pulse whatever the pick
  (`te_jmap_access_selfcheck`, `_pollution_`, `_jobs_`, `_below_sol_`), each armed on three states holding a fact read
  another way, so a read of none everywhere can't pass: `TE_SELF_CHECK OK|BROKEN market_access` (states short of
  infrastructure read between 0 and 1, none above 1), `pollution_amount` (the value agrees with its trigger form,
  vanilla's and the tourism buildings' `state_region = { pollution_amount > N }`, at 0 and 10, none above 255),
  `available_jobs` (states with a building under 90% staffed read above 0, and the value agrees with its trigger
  form) and `below_expected_sol` (states living a point below what their people expect read above 0, none above 1).
  The play-test list's Self-checks table names each fallback. Not buildable: Migration Attraction, since state-scope
  `migration_pull` reads the country's figure (why the Cartographic Survey was switched off). Unverified (play-test
  check 35): the four reads in a paint, the hovers and the five maps' look.
- **The twentieth pass's one** (2026-11-26, the owner's ask). 90 **Nuclear Reach**, in Military and Security beside
  Nuclear Weapons, while the nuclear weapons rule is on: where the viewer's weapons can strike, by the cheapest leg
  that reaches each state (`te_jmap_reach_*`, `te_journal_map_triggers.txt`). The viewer's own states blue
  (`te_jmap_reach_you`, the "your" maps' blue); then its bombers' reach, orange: the state's owner on the viewer's
  list, or strategically adjacent to the viewer now, read live as a strike reads it (`nd_state_in_reach_of`), so a war
  begun since the list was built counts at once; then a coast only its missile submarines reach, bluish green; then
  what only its ICBMs reach, reddish purple; the rest pale (`te_jmap_none`). A coast in bomber reach that the
  submarines reach too takes the submarines' green as stripes (the Map Room's fourth `map_color_second` branch), and
  the hover's second line says so; a state out of reach has a second line naming the leg that would reach it
  (submarines, for a coast while the viewer holds one of its own; otherwise only ICBMs). The three are Okabe and Ito's
  colors for color-blind readers (#E69F00, #009E73, #CC79A7), so they stay apart with no L, M or S cones; the map is
  categorical, so Outliers, Scale and Color are greyed on it. **The bombers' reach is the deterrent's own rule, built
  by its own helpers into a list of the map's.** `nd_reach_reset`, `nd_reach_build`, `nd_reach_add_from` and
  `nd_reach_add` (`nuclear_deterrence_effects.txt`) take the list's name (`LIST`), the deterrent's `nd_reach` and the
  map's `te_jmap_rch`, each with its own counters (`$LIST$_count` …), so the panel's `nd_reach_count` is untouched
  and no strike reads the map's list (`test_nuclear_reach.py` holds both). The deterrent builds `nd_reach` only for an
  armed country without ICBMs; the map builds `te_jmap_rch` for any viewer, so it shows the bombers' reach beside the
  missiles' and, before the first warhead, where the bombers would fly (the pick's tooltip says so). The other two legs
  are flags on the viewer (`te_jmap_rch_subs`, `te_jmap_rch_icbms`, from `nd_fields_missile_submarines` and
  `nd_fields_icbms`, public facts: nuclear.md), with its own coast (`te_jmap_rch_coast`), so a paint reads a list and
  three flags, and never the submarines' trigger, which walks the viewer's states for a coast. **The store follows the
  viewer.** `te_jmap_store_reach` runs from `te_jmap_note_viewer` while 90 is the pick, on the country just noted: at
  the pick (after the selector is set), at an option click, at the Timeline Extended window's Map Room button and at the
  viewer's own monthly pulse, so the list is a month old at most and is never another country's. Nothing it reads is
  private: no `nd_is_armed`, no arsenal (in multiplayer another player can see the viewer's map), and an unarmed
  viewer's map looks like an armed one's. The walk is the deterrent's weekly one, once, for one country. Unverified
  (play-test check 36): the live adjacency in a paint, the stripes on small coasts and the four colors' look.
- **Picks are scripted GUIs on a page widget, not scripted buttons.** The engine locks a scripted button for a country
  not involved in its entry ("Countries that are not involved in the Journal Entry may not take this action"), and
  nobody is involved in the Map Room. So `te_jmap_pick_<map>_sgui`
  (`common/scripted_guis/te_journal_map_picks_generated.txt`) set the global pick with the player as root, and
  `te_jmap_pick_row` (`gui/journal_entry_widgets/te_map_room_picks_generated.gui`, both written by
  `scripts/generators/gen_journal_map_picks.py`) draws them on the page through the entry's `widget` (`gui/journal_entry_widgets/te_map_room_widget.gui`, above the description; a widget
  draws on a contextless page, 2026-11-05). A pick's `is_valid` is false while it is the pick, which its button draws
  pressed (`down`, seen working 2026-11-05); the census maps' `is_shown` hides them while the census doesn't run, and
  a system's map's while its rule is off.
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
- **Two options** (2026-11-14), below the picks on the page and global as the pick is: the area the maps are drawn
  and measured over, and the outliers a fitted map's range leaves out. A state outside the area is greyed by
  `map_color`'s first branch, before any selector, and the Map Room reads its own ranges for the two fitted maps a
  system's entry also draws. § The Map Room's Options has both.

### Why not a country entry added by a button

The first pass's Map Room, `je_te_map_host`, was a country entry kept out of the journal by a variable its
`is_shown_when_inactive` and `possible` read, and added by `add_journal_entry`. The add never worked: every country
holds an inactive copy of a country entry with its own activation triggers from the game's start, and
`add_journal_entry` is refused while one exists ("already has a journal entry of type", 2026-11-05). The variable then
made the copy shown (the journal's Potential section) and the engine activated it at its own check, up to two weeks
later. An entry with neither trigger has no copy until added, so `add_journal_entry` would work on it, but then nothing
takes it out again short of an outcome, which leaves it in the concluded tab. The contextless entry needs neither.

## The Map Room's Options

Twelfth pass (2026-11-14). The owner: "a section below the mode selection where you can change some aspects of the
plotting - for example, if it is on a linear or (different kinds of) nonlinear scale, the color, maybe excluding
outliers, maybe limiting where we draw it (e.g. if Europe in 1900 is much richer than Africa, but you want to see the
variation within Europe, you could limit it to Europe - or maybe to your country, your power bloc, etc?)". Two of the
four were built that day, the two that live in a range's measurement: **Area**, where the maps are drawn and
measured, and **Outliers**, how many states each end of a fitted map's range leaves out. **Scale** followed in the
thirteenth pass (below). The colors are not built: a paint names its two colors outright, so a palette is more
branches in the paint, not a branch in a factor.

The options are global variables, as the pick is and for the same reason (`te_jmap_opt_area`, `te_jmap_opt_cont`,
`te_jmap_opt_trim`, `te_jmap_opt_scale`, read through the root-free `te_jmap_area`, `te_jmap_continent`,
`te_jmap_trim` and `te_jmap_scale`, `te_journal_map_values.txt`): every player in a multiplayer game shares them, a
save keeps them, and unset is the default, the world, four states left out at each end and each map's own curve,
which is what the Map Room showed before it had options.

- **Area.** 0 the world, 1 a continent, 2 the viewer's market, 3 its power bloc, 4 its country. A state outside the
  area is painted slate (`te_jmap_outside`, darker and bluer than the "no data" grey), hovers as "Outside the area the
  maps are limited to", carries no stripes and no second hover line, and is left out of the range, so the colors run
  over the states inside: limit GDP per Capita to Europe and Europe's poorest state takes the palette's low end. The
  area greys every map, the categorical ones too; only a fitted map has a range for it to narrow.
- **One stored mark, read first.** A paint may run once per state per frame, so it asks one thing: whether the state
  carries `te_jmap_out`. That is `map_color`'s and `map_tooltip`'s first branch, before any selector (the stripes and
  the hover's second line ask `te_jmap_in_area`, the same test, in each of their branches, since a first branch there
  would have to name a color to stripe with). Under the world no state carries the mark, so the cost of the options
  to a default Map Room is one `has_variable` per state, and a save from before them paints as it did.
  `test_journal_map_modes.py` (`OptionsTest`) fails on a paint that names a continent, a market, a power bloc or an
  option.
- **What the area is, the marking effect asks.** `te_jmap_mark_area` (`te_journal_map_effects.txt`) walks the world's
  states once and marks those `te_jmap_state_in_area` (`te_journal_map_triggers.txt`) fails: a continent's strategic
  regions, the state's market against the viewer's, its owner against the viewer and the viewer's power bloc
  (`is_in_same_power_bloc`, which takes a member's subjects with it), or its owner against the viewer. It runs at
  each option click and each pick, after the viewer is noted and before the range is measured, and each month from
  the global pulse before the month's ranges. So **a later change shows within a month, and at once at the next
  pick**: a state that changes hands, a market that splits, a country that joins or leaves the bloc. A state made
  since the last marking has no mark and counts as inside until then. Under the world nothing is walked: the global
  `te_jmap_marks` records that some state may still carry a mark to clear.
- **An area that loses its anchor goes back to the world.** Where `te_jmap_area_holds` fails at a marking (the viewer
  left its power bloc, or holds no state), the option is set back to the world and `TE_JMAP area reset` is logged: a
  map greyed everywhere reads as broken. The Power Bloc button is greyed for a country in no bloc, with that as its
  tooltip.
- **The continents** are six lists of strategic regions (`te_jmap_in_continent_<name>`, by `region = sr:…`), every
  land region in exactly one; `AreaTest` holds every state region of `map_data/state_regions` to one continent,
  against `vanilla_parsed/` with the mod's own strategic regions over it. Vanilla's geographic regions don't divide
  the world (its `north_america` and `south_america` both leave out `region_central_america`, and its `asia` holds
  Oceania), so the lists are the mod's, and where a border falls is vanilla's regions' doing: the Middle East, the
  Caucasus south of the main ridge (`region_greater_persia`), Siberia and New Guinea (`region_indonesia`) are in
  Asia; Russia west of the Urals, Iceland and Greenland (`region_northern_europe`) in Europe; Egypt and Sinai in
  Africa; Mexico, Central America and the Caribbean (`region_central_america`) in North America; Hawaii in Oceania.
  Each continent button's tooltip lists its regions by vanilla's names. The first pick of Continent takes the
  player's capital's (`te_jmap_default_continent`); later picks keep the last one chosen.
- **The viewer.** The market, the bloc and the country are `global_var:te_jmap_viewer`'s, the "your" maps' viewer
  (§ The Systems' Maps): the player who last clicked a pick, an option or a map button. In a single-player game that is
  the player, through a change of country too. In multiplayer the area is one for everybody, as the pick is, and it
  follows the player who last clicked.
- **Outliers.** 0, the default: four states at each end (`TRIM`), and under a limited area at most a tenth of the
  area's states with a figure (`AREA_TRIM_PART`), so a country of fifteen states keeps thirteen in range where four
  at each end would leave seven. 1: none, the lowest state to the highest. 2: a twentieth of the states with a figure
  at each end (`TRIM_SHARE`), rounded down. The states left out take the colors' limits, as before. The Outliers
  buttons are greyed, with the reason, while the pick has no range (`te_jmap_pick_fitted`, generated: the categorical
  maps and the fixed scales); the setting is kept for the next pick that has one.
- **A measure counts first.** `te_jmap_range_<map>` counts the states it will order (`te_jmap_n`: the map's `where`,
  and for the Map Room's ranges `te_jmap_in_area`), works out the trim from the count and the option
  (`te_jmap_trim_count` into `te_jmap_k`), and has `te_jmap_measure_at` take the state at that place from each end.
  `position` takes no script value (`effects.log`: `position = int`), so `te_jmap_measure_at` is a ladder of literal
  positions, 0 to `TRIM_MAX` (80: 5% of 1,600 states), each a call of `te_jmap_measure_<map> = { K = n }`. The trim
  never passes the middle (`te_jmap_trim_most`: two states are always left to span), and where no state has a figure
  nothing is measured and the fixed curve's ends serve. The count matters twice, both worked out from the script and
  neither seen in game. With five to eight figures the eighth pass's two ends crossed (the fifth highest of eight is
  below the fifth lowest), so the stored low was above the stored high; the high then floored at the low plus the
  map's narrowest span, and the range ran for that one span up from the fifth lowest state: every state at five
  figures, and most at eight, took the low color. With fewer than five, "the extremes where fewer have a figure"
  rested on a fallback that runs only if a `position` past the end takes nothing, where the lesson says it takes the
  last state and logs (`scripting_best_practices.md`, "`position = N` + `check_range_bounds = no` Clamps
  Out-of-Range"; seen on `ordered_scope_state`, unverified on `ordered_state`). A world map has hundreds of figures,
  so only the sparse ones were exposed (Grandeur's and Company HQs' in a game's first decades), and nobody reported
  it; under Country or Bloc a short list is the usual case. `test_journal_map_scales.py` (`RangeRunTest`) runs the
  generated effects over made-up states against a plain sort, taking the last state for a position past the end as
  the engine does.
- **The Map Room only.** Seven maps are also drawn by their system's own entry, and two of those are fitted:
  Emissions and Grandeur. An entry's paint never reads the mark, so its page greys nothing. Its range is kept apart
  too: `te_jmap_range_gw` and `te_jmap_range_gm` stay the entries', the whole world on the default trim whatever the
  options, each month; the Map Room reads a twin of each (`te_jmap_range_gw_room`, `te_jmap_gw_room_factor`, the
  generator's `_room_twin`), measured under the options, since a script value can't tell which page asks. A twin's
  range is the entry's until its own first measure, so a save from before paints the same. The parity test compares
  the two pages' ladders with the twin's name folded back. The other five entry maps are categorical. The options
  don't reach an entry's range; the count does, since all the ranges are written by one generator: an entry's range
  with under ten figures (a world with few monuments) no longer takes its ends past the middle, so that page and the
  Map Room's still agree under the default options.
- **A change repaints at once.** Each option button (`te_jmap_option_button`) runs its scripted GUI and then fires
  `te_jmap_repaint`, the picks' own state on `te_jmap_repainter`, unchanged: the option's effect has marked the area
  and measured the pick's range before the page reopens, so a paused map repaints on them.
- **What the page says.** The Map Options header names the options in force at its right, closed or open
  (`te_jmap_options_now`); while any is off its default a line under the page's heading says so too
  (`te_jmap_options_in_use`, on `te_jmap_options_set`), since a map limited to one continent looks broken to someone
  who forgot they set it. The open section ends on what the map on the page was measured over: the area by name, the
  states with a figure and the states each end left out (`te_jmap_shown_states`, `te_jmap_shown_cut`, a copy the Map
  Room's ranges keep, since the entries' ranges count into `te_jmap_n` and `te_jmap_k` too). Each fitted pick's
  tooltip names the area in place of "the world" and ends on what the range leaves out (`$te_jmap_measured_area$`,
  `$te_jmap_measured_trim$`); the figures in it are the map's last measure, which for a map that is not the pick may
  be older than the options. The words come from four custom localizations
  (`common/customizable_localization/te_journal_map_custom_loc.txt`), a market's, a bloc's and a country's names
  from the viewer's scopes.
- **Seen in game** (the owner, 2026-11-14, `main` at `5e1a5deb4`; play-test list, ninth session): asked to limit the
  maps to a continent, the market, the power bloc and the country, the owner saw the states outside turn slate and
  the colors stretch over what is left ("All looks good"; the answer doesn't say which of the four were tried).
- **Unverified** (play-test check 29): the rest of the above, the hovers, the tooltips, the Outliers settings and a
  system's own page among it. Script can tell success from failure in two places, neither read yet, each a
  once-a-game line from the global monthly pulse: `TE_SELF_CHECK OK|BROKEN area_mark` (`te_jmap_area_selfcheck`, the
  first month an area is set: BROKEN when the marking put every state on one side, or the viewer's own capital
  outside its market, bloc or country) and `TE_SELF_CHECK OK|BROKEN range_count` (`te_jmap_range_selfcheck`, the
  first month under the default options: GDP per capita's range through the count and the ladder against
  `position = 4` taken outright). The check names each fallback.

### Scale

Thirteenth pass (2026-11-14). `te_jmap_scale`: 0 the map's own curve (the default), 1 Linear, 2 Logarithmic, 3
Ranked.

- **A branch in the factor, not in the paint.** A factor is a script value, and a script value can read a global
  (the trees already read the range's two), so each `te_jmap_<map>_factor` the Map Room reads takes one of four
  branches on `te_jmap_scale`. The map's own curve is the first, so a default paint pays one comparison, and
  `map_color` is untouched. The factors a system's own entry reads (`te_jmap_gw_factor`, `te_jmap_gm_factor`) and
  the five fixed curves have no branch: the Scale buttons other than Map Default are greyed, with the reason, while the
  pick has no range (`te_jmap_pick_fitted`), and an entry's page is the map's own curve whatever is set. The
  generated values file went from 3,567 lines to 11,562: a logarithm is a ladder of twenty straight pieces, and
  Logarithmic needs two for a straight map and four for a midpoint map (two a side). In a paint, one evaluation of
  a factor under Logarithmic runs two of them (a midpoint map only its side's), as GDP per Capita's own curve
  always has. A three-color map's `map_color` evaluates its factor twice a state under every scale, once in the
  `< 0.5` split and once in `_lower` or `_upper`: so the fifteen three-color maps (the twelve midpoint maps, Life
  Expectancy, Infant Mortality, Median Age) read four ladders a state under Logarithmic and the other maps two.
- **Linear**: straight from the range's low to its high; on a map with a meaningful midpoint, straight on each side
  of it, to the range's end on that side, so the midpoint stays the neutral color.
- **Logarithmic**: the same share of the color for each doubling. A map already on a doubling scale (GDP per
  Capita, Armed Forces, Company HQs, War Dead, Trade Capacity, Investment, Population Density, the class counts,
  Population, GDP, Vacant Jobs) keeps its tree: Logarithmic is its own
  curve, and its tooltip says so. A straight map starts at its range's low, or at a 64th of its high where the low
  is smaller (`LOG_RATIO`: a low of 0 has no logarithm, and the engine's five decimals can't hold a smaller share
  of the Capitalists' 0.2% range), so it spans six doublings at most; the figure over the start is worked out as
  the smaller of figure / low and figure × 64 / high, never by dividing by the small start. Where the range is
  under one doubling wide (Gini's 0.43 to 0.60, say) Logarithmic is Linear: the log is read in straight pieces
  between powers of two.
- **Logarithmic around a midpoint** (the owner: "What about symlog?"). The maps that run both ways from a
  midpoint (Fertility, Natural Change, Net Migration, Sex Balance, Population Growth, the two comfort maps, Dynastic
  Wealth; and since #1976 SoL vs Wealth, SoL vs Expected, Infrastructure and Radicals vs Loyalists) are logarithmic on each side of it by the distance from it, and straight within `min_half` of it, where a
  logarithm has no start: the knee is `min_half` / 2 (`LOG_KNEE_PART`), the side's share is 1 + log2 of the
  distance in knees over the same of the side's span, and since the first piece of the log, from one knee to two,
  is straight, the scale is straight from the midpoint to `min_half`. Each doubling of the distance past that takes
  half the color the straight band does. The midpoint is exactly 0.5 in the engine's fixed point, as `map_color`'s
  split needs. `min_half` because it is already the map's own measure of the smallest difference worth showing: no
  side is ever spread over less. How much that bends a map depends on how many doublings lie between `min_half` and
  the side's end: on the default ranges 2.3 for Dynastic Wealth, 3 or more for Natural Change, Net Migration and
  Population Growth, 2 and 2.6 for Sex Balance, 4.7 for a comfort penalty; Fertility below replacement (1.1) and a
  comfort draw (1.8) stay close to Linear. No text calls it by name: the tooltips say what it does.
- **Ranked**: each state's place in line among the states the map measures (those it paints with a figure, in the
  Map Room's area), 0 to 1. A paint can't sort, so the place is stored on the state (`te_jmap_rank`) and the
  factor's Ranked branch reads it, guarded. `te_jmap_rank_<map>` (generated, one per fitted pick) walks the states
  lowest figure first (`ordered_state`, `min = 0`, `max = 5000`), keeping the place as a count: it steps only when
  the figure moves on from the state before, so **equal figures share a place** and each distinct figure is one
  even step. Peacetime Devastation is hundreds of states at exactly 0; an index would smear them across the
  palette in whatever order the engine walks them. A second pass divides each place by the last. A midpoint map is
  ranked on each side of the midpoint, outward (0.5 down to 0 below, 0.5 up to 1 above, a state at the midpoint
  itself 0.5), so cream stays at replacement and not at the median state. Each map is ranked by its own figure:
  Current Comfort shares Base Comfort's range, not its order.
- **One rank variable for every map.** `te_jmap_refresh_range` clears every stored place first
  (`te_jmap_clear_ranks`, which walks nothing unless `te_jmap_ranks` says some are stored), measures the pick's
  range, then, under Ranked, runs the pick's `te_jmap_rank_<map>` (`te_jmap_refresh_rank`). So no place outlives
  the pick or the setting it was taken under, and a range's own effect stores none (the once-a-game range check
  measures GDP per capita whatever the pick). A state the map paints but the last measure didn't walk (made since)
  has no place and paints the low color, or the midpoint's on a three-color map, until the next.
- **How old a Ranked map can be.** Places are taken where the range is: at a pick, at an option click and from the
  global monthly pulse. A month at most, the age the range already had. What changes is that a Ranked map of a live
  figure (Turmoil, Devastation, GDP per Capita, Crowding Penalty, Trade Capacity) stops moving between measures,
  where the other three scales still repaint it as the game runs. The open section says so in place of the
  measured-over line (`te_jmap_options_measured_ranked`), and so do the Ranked button's tooltip and every pick's
  tooltip under Ranked.
- **Outliers under Ranked** has nothing to act on (a place is no outlier's to move), so its three buttons are greyed
  with that reason (`te_jmap_trim_ranked_tt`); the range is still measured, and the tooltip prints it as "not read
  by this scale".
- **No tooltip describes a curve that isn't in force.** A fitted pick's tooltip gives the scale a line of its own
  (§ Color, "The tooltips", has the whole form since the fourteenth pass): under Map Default the map's own curve
  in words, under any other scale the scale in force and what it does. What the scale does comes from one of three
  custom localizations, named in each pick's key since a custom localization can't know which button is hovered:
  a straight map (`te_jmap_scale_text`), a doubling map (`_doubling`: Logarithmic "is this map's default") and a
  midpoint map (`_mid`). The range's line is led by "The range now, over" (`te_jmap_scaled_range_lead`; "Not read
  by this scale, …" under Ranked) and the area (`$te_jmap_measured_area$`).
- **On the page**: a Scale row under Outliers in Map Options (Map Default, Linear, Logarithmic, Ranked; the
  first is the map's own curve, labelled "Map's Own" until 2026-11-14, when the owner said of it "I might call it
  map default or similar, it sounds odd as is"). The header and the line at the top of the page name the scale
  only while it is off its default (§ Color, "The header and the line").
- **Seen in game** (the owner, 2026-11-14, `main` at `5e1a5deb4`; play-test list, ninth session): asked to switch
  GDP per Capita through the four scales, the owner saw each repaint, paused too, and Linear push most states toward
  the low color; and under Logarithmic the midpoint stay cream on Fertility or Net Migration ("All looks good"). So
  a factor's branch on `te_jmap_scale` is taken in a paint.
- **Unverified** (play-test check 30): the rest, how Ranked spreads its colors and the tooltips under a scale among
  it. Script can tell success from failure in one place, not read yet:
  `TE_SELF_CHECK OK|BROKEN rank_walk` (`te_jmap_rank_selfcheck`), once a game from the global monthly pulse whatever
  the Scale option, so a game answers it before anyone picks Ranked: it walks the states with a GDP per capita
  lowest first, as a rank's walk does, and is BROKEN when the walk visits fewer than a count of them or takes any
  out of order. The mod walks other ordered lists from `min` to `max` (`ordered_scope_state`, `ordered_in_list`),
  never `ordered_state`, and never thousands long. `test_journal_map_scales.py` runs every committed factor under
  Linear and Logarithmic against the generator's reference, in floats and in the engine's five decimals
  (`ScaleTest`), and the rank effects over made-up states, ties and midpoints included, against a plain sort
  (`RankRunTest`).

### Color

Fourteenth pass (2026-11-14). `te_jmap_color`: 0 the map's own colors (the default, labelled Map Default as the
scale's is, from the same key), 1 Colorblind-Safe, 2 Grayscale (internally `grey`). Nothing here has been seen in
the game (play-test check 31).

- **Shared branches, not a branch a map.** A `lerp`'s colors are literal names, so another palette can't be
  swapped into a map's own branch, and a branch per map per palette would more than double the paint. Eleven
  branches open `map_color` instead, after the area's slate and before any map's own, each taken only while the
  option is off its default and asks for it first, so a default paint pays one comparison a branch if a limit
  stops at its first false line (an assumption: see Cost). They color whatever fitted map is
  picked from one ramp, and ask the generated values file two things about the state: `te_jmap_pick_ramp` (0 the
  pick's own lerp wouldn't paint it, 1 it would and the pick runs one way, 2 it would and the pick runs both ways
  from a midpoint) and `te_jmap_pick_factor`, the picked map's factor, under the Scale option as every factor is.
  Each row of `te_jmap_pick_ramp` repeats the limit of that map's own lerp branch (the table's `where`, or `paint`
  on the three rows where the two differ: GDP per Capita paints a state with no figure at its low end, Current
  Comfort is guarded by its own variable, and Emissions' lerp is what its two flat branches leave).
  `ColorTest` reads the paint in ladder order and holds each row to it. A state the ramp doesn't take falls
  through to its map's own branches.
- **Five stops, four lerps.** The engine mixes two colors at a time, so a ramp of five published stops is four
  lerps end to end, the factor read a quarter at a time (`te_jmap_pick_q1` to `_q4`; the paint takes the first
  lerp whose end the factor is under). Five because the published five-class schemes are designed as five, and
  four straight mixes between them follow the scheme closely; three stops would flatten the middle of the ramp
  and nine would put eight comparisons in front of every state. Nothing records whether the engine's `lerp` mixes
  in RGB or in hue, saturation and value, so every stop pair is checked under both (`ColorTest`), and the
  diverging ramp's near-white middle is written twice, once with each side's hue, so that a mix in hue could not
  sweep through the hues between.
- **Colorblind-Safe**: ColorBrewer 2.0's five-class sequential YlOrBr (Brewer, Harrower and the Pennsylvania
  State University, colorbrewer2.org, which marks it colorblind safe), pale yellow at the low end to brown at the
  high, on every map that runs one way, the three-color ones with no meaningful midpoint among them (Life
  Expectancy, Infant Mortality, Median Age). On the midpoint maps, ColorBrewer's five-class diverging PuOr:
  orange below the midpoint, near white at it, purple above, two lerps a side, so the midpoint keeps a color of
  its own at exactly factor 0.5. Checked in CIELAB under normal vision and with no L, M or S cones (Machado,
  Oliveira and Fernandes 2009, severity 1): lightness never turns along either ramp, so both keep their order in
  grey (the diverging one as distance from the midpoint); neighbouring stops are at least 17 apart; the two sides
  of the midpoint at least 19 apart the same distance out; the sequential ramp at least 40 from slate and from the
  "no data" grey, the diverging one at least 18 and 10 (both with no S cones; over 30 for every other eye).
- **Below the scale.** Two maps paint a state apart from their scale: Company Headquarters at a loss (its own
  red) and Emissions where a state removes more than it emits (its own green). The red sits within 5 of the
  sequential ramp for an eye with no S cones and within 13 with no M, so under Colorblind-Safe both take one color
  off the ramp instead (`te_jmap_pick_below`, `te_jmap_cb_below`: the first color of Tableau's Color Blind 10,
  a blue at least 50 from every color of the ramp). "None" (pale) and "no data" keep their colors there.
- **Grayscale**: ColorBrewer's nine-class Greys from its second class to its sixth, light at the low end to dark
  at the high, one lerp. A grey for "no data" would be a grey on the ramp, and so would the pale "none", so a
  lightness band can't keep them apart. Instead every state of a fitted map that the ramp doesn't take (no
  figure, none, a loss, a removal) is the "no data" grey with light stripes (`map_color_second`'s first branch,
  `te_jmap_grey_stripe`): grey is a figure, striped is not on the scale, slate is outside the area. The ramp's
  dark end is 25 lighter than slate. The regional headquarters' gold stripes stand down under Grayscale, so a
  stripe says one thing (this pass's own choice, not an ask; the hover's line, which said "in the stripes", now
  says "Regional headquarters here"). **A midpoint is not marked under Grayscale**: the ramp runs one way, and the midpoint
  sits at the middle grey, as the tooltip says. It is the one place the option loses the midpoint; marking it
  would take a second pattern or a step in the ramp (check 31 names the fallback).
- **Where it doesn't apply.** A map of categories or on a fixed scale keeps its colors: the two buttons are greyed
  there with the reason (`te_jmap_color_no_range_tt`), and Map Default stays. A system's own entry reads neither
  the option nor the shared values, so its page keeps its own colors, as it keeps its own curve.
- **The tooltips.** Each fitted pick's tooltip (35 in this pass, 77 since #1977; `te_jmap_pick_<map>_desc`, one key again; the
  thirteenth pass's `_scaled` twins are gone) is four lines, each true whatever is set: what the map shows, with
  no word of a curve, a color or a range (`PickTooltipTest` holds it to that); the range now; the scale, the
  map's own curve under Map Default (`te_jmap_curve_<shape>`, eleven keys shared by the maps of a shape) and the
  scale in force otherwise; the colors, the map's own under Map Default (`te_jmap_pick_<map>_colors`) and the
  palette in force otherwise. The line chooses for itself (`SelectLocalization` on the option, inside the key).
  The own curve's words come from the generator (`curve_key`, `curve_words`), from the knots the curve itself is
  written from, and the test holds each key to them and each knee to the factor it describes; the first rewrite
  found two maps (Capitalists, Academics) whose tooltips had never mentioned their knee. Every map now says which
  color is its low end and which its high. What the palette in force says depends on what the map can show
  besides its ramp, so there are five custom localizations (`te_jmap_color_text`, `_none`, `_hq`, `_gw`, `_mid`),
  as the scale has three.
- **The header and the line.** Four options don't fit beside the header's title, so the header's summary
  (`te_jmap_options_now`) and the line at the top of the page (`te_jmap_options_in_use`) name only the options
  off their defaults, in the rows' order; with none set the header reads "All defaults" and the line is hidden.
  Each option is a part that is empty at its default (`te_jmap_now_area`, `_trim`, `_scale`, `_color`; the
  line's `te_jmap_set_scale` and `_color` differ only in using the full names), led by a comma where an option
  before it is set, so the two lines read the same triggers and can't disagree about what is set. The header
  takes the short names "Log", "Colorblind" and "Gray". At its longest, "North America, Keep All, Ranked,
  Colorblind", it is 43 characters, about 302 px in the page's font where the header leaves about 296 beside its
  title at full size and 338 with the title at its smallest. `ColorTest` runs both lines over all sixteen
  combinations. A custom localization's text here reads another's two levels down; the
  precedent in the mod, the Grand Monuments' trophy names, goes one (check 31 has the fallback).
- **Cost.** A default paint: eleven more comparisons a state, each a read of one global, assuming a limit stops
  at its first false line; if it reads every line, each of the eleven also works out the pick's ramp or factor.
  Nothing has measured which. Off the default: the
  shared branches work `te_jmap_pick_ramp` and the factor out up to four times a state, each a ladder on the
  pick (35 rows at most then, 77 since #1977) before the map's own factor. The owner's frame reading (below) saw no cost in the
  default paint; this has not been read.

### A stored factor, weighed and not built

2026-11-14. The assessment that led to the Scale option offered a second design (its option B): store each state's
factor, 0 to 1, on the state at each measure, and have every paint read that one number, as Ranked's does, in place
of working the factor out as the map paints. Its one advantage was speed with the page open. Its price was a rebuilt
paint and live maps that move only when measured.

The owner read the game's debug frame counter on `main` at `5e1a5deb4` in four situations (the page closed; GDP per
Capita on the map's own curve; the same map on Ranked; a three-color map such as Fertility on Logarithmic; each
paused, then running at speed 5): "Paused: closed - ~100; GDP/c on Map's own - same; ranked - same; fertility [left
blank]; unpaused - same" (the bracket marks a line that came back with no figure). So the open page does not pull
the frame rate down, and the live factor, two twenty-piece ladders a state, reads as the stored one does. With no
cost a player can see, a stored factor has nothing to give back, and it is not pursued.

The caveat: this is a counter read by eye, not frame times, and if the game holds its frames near 100 a second a
saving beneath that would not show. It says nothing of a three-color map under Logarithmic, which works four
ladders out for each state, or of the length of a game day. A harness measurement meant to settle those never got
its page open (play-test list, ninth session). If the page is ever felt to be slow, measure before rebuilding: the
paint's 138 branches tried in order are as likely a cost as any factor, and a stored factor would not shorten them.

## The Class Maps

Seventeenth pass (2026-11-23, #1975, the second of the owner's four Map Room changes: "All 15 pop types", "colored by
headcount, not share", "A Count/Share switch in Map Options"). Until then four classes had a map each, their share
of the state's people (the tenth pass).

- **Every pop type, two maps each.** The fifteen pop types vanilla defines (`common/pop_types`), each by its people
  (the count: 48 to 62) and by its share of the state's people (the share: 41 to 44 kept, so a save holding one shows
  it, and 63 to 73), and the mod's one, Spacers (2026-11-24, space forces personnel: 88 and 89, a short last row in
  Map Options). `test_every_pop_type_has_two_maps` checks vanilla's against `vanilla_parsed/` and the mod's against
  `common/pop_types`.
- **The count is the default** (the owner's reasoning: headcounts don't just repeat the population map; a developed
  country has few peasants, an urban state few farmers, an automated late economy fewer laborers). It runs on the
  doubling scale Armed Forces uses (`rel_doubling`), from the world's low (at least 10 people, `COUNT_FLOOR`) to its
  high (at least four times it), and a state with none of the class is pale (`te_jmap_none`), as Armed Forces'. The
  share keeps the fitted curve the four had: straight, or half the color by a fifth of the range for a class that
  gathers in a few places (Capitalists, Academics, Engineers, Machinists). A class's two maps share its colors and its
  hover: the people, then their share.
- **The figures.** The yearly walk counts every class into `te_dg_cls_<pop>`, whatever the Demographics rule, in one
  `is_pop_type` ladder a pop (`te_jmap_class_walk_pop`, the classes with the most pops asked first). The Map Room's
  three calls in the walk are `te_jmap_walk_init`, `_pop` and `_store` (`te_journal_map_effects.txt`; they were
  `te_jmap_class_walk_*` until this pass, a name the generated part took), not the census's helpers, which set nothing
  outside the census (`test_demographics_registry.py`, `TestWorkWalk`); `test_demographics_golden.py` leaves them out
  of the walk it pins. The tenth pass's `te_dg_capitalists`, `te_dg_aristocrats`, `te_dg_clergy` and
  `te_dg_academics` are renamed with the rest, since `te_dg_soldiers` already meant Soldiers and Officers (Armed
  Forces keeps it). A save from before holds the old four, which nothing reads, and shows a class map grey ("No
  census figures yet") in each state until its next yearly walk.
- **The Count/Share switch.** A global option, as the others are (`te_jmap_opt_class`, read through
  `te_jmap_class_mode`: 0 the count, the default, 1 the share), on a Classes row at the end of Map Options. Each class
  has two pick buttons side by side in its row, one per selector, each shown under one setting (the pick's `is_shown`
  asks `te_jmap_class_mode`), so the switch decides which of a class's two maps its button picks: the buttons carry
  the class's name either way. Its two buttons are greyed off a class map (`te_jmap_pick_class`, generated), with
  "Only the class maps are drawn two ways" as the reason. On one, a click sets the option and moves the map on the
  page to the same class's other map (`te_jmap_class_flip`, generated: `te_jmap_set_selector` with the other number,
  which measures its range and notes the viewer), then fires the picks' repaint. Ranges, Scale, Color and Ranked are
  keyed on the selector, so each of the thirty maps has its range, its rank effect and its ramp row from the curve
  generator, and they needed no change.
- **What the page says.** The Classes group's header names the setting at its right ("By Count" or "By Share",
  `te_jmap_classes_now`), beside the buttons it governs. The options' header and the line at the top of the page
  leave it out: it governs the class maps alone, and at its longest the header's summary already fills the room
  beside its title (§ Color, "The header and the line").
- **One table.** `scripts/generators/journal_map_classes.py`'s `CLASSES` names each class once: its two selectors,
  what draws it (the picks' first line), its count's default range, its share's shape, its colors and its place in the
  walk; `ROWS` its place on the page, three to a row by theme (property, learning and the state, industry, the land,
  offices and the army). Each class's colors are its pop type's hue in vanilla's pop charts (`common/pop_types`'
  `color`), from nearly white to deep, so the map matches the state panel's pop chart; the tenth pass's four took
  new colors with the rest. `gen_journal_map_classes.py` writes the share values (`te_jmap_share_<pop>`), the walk's
  counts, the switch's flip, the colors and the loc (`te_jmap_pick_class_*`, `te_jmap_tt_class_*`: `organize_loc.py`'s
  `JOURNAL_MAPS_GENERATED`), and splices the family's paint, hover and "no data" branches into `je_te_map_room`'s
  `map_color` and `map_tooltip` between the BEGIN and END marker lines it owns; the rest of that file stays
  hand-written. `gen_journal_map_scales.py` builds each map's curve row from it (`class_rows`), and
  `gen_journal_map_picks.py` its two picks (one slot of a row, `SLOTS`). `test_journal_map_classes.py` holds the
  generator, `ClassMapsTest` what the family paints and walks.
- **Cost, not measured.** The family's 45 paint branches (a count's lerp and its pale none, a share's lerp) and its
  "no data" branch come last in the ladder (151 branches before this pass, 193 after it, 216 since #1977), so no
  other map pays for them; a class map pays for the 169 branches above them and up to 44 of its own family's. The generated values file went from 12,202 lines to 19,080 (each
  fitted map's three other scales), and the Color option's shared branches read a ladder of 62 fitted picks where
  they read 36. Play-test check 33 asks for the frame counter on a class map, and names the fallback.
- **Unverified** (play-test check 33): the colors, the buttons' labels once Share is set, the switch's move and the
  frame rate.

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
ninth (31, 2026-11-07) and a tenth, Grid Flows (91, 2026-11-27). Each but the Seabed's and the Power Grids' is drawn twice: by the system's own entry, whenever its page is open, and by the Map Room, on a pick. Both ask the same
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
| 91 | Grid Flows | none | Each station's state by what its station does this month, as the Power Grids tab's Stations table reads it (`te_jmap_grid_mode`: `te_grid_mode_disp` behind `has_building`, since the mode reads 4 where there is no station): sending blue, receiving orange, idle on a grid pale, on no grid the Power Grids map's grey (`te_jmap_grid_send`, `_receive`, `_idle`, `_offline`); the hover gives the flow, or why the station moves nothing (`te_jmap_tt_grid_why`, the idle reason read through `THIS`). Beside Power Grids under Economy; no game rule either. The owner's ask for an import/export map (2026-11-27), where vanilla's goods map already shows Electricity's price |

**The viewer.** A paint can't reach the player (`is_player` drew nothing under `owner`, 2026-11-05), so the maps of
"your" country (19, 20) are drawn for `global_var:te_jmap_viewer`: every pick and map button sets it to the player's
country (`te_jmap_note_viewer`, `te_journal_map_effects.txt`). A player's monthly pulse (`te_journal_map_on_actions.txt`)
sets it only when there is no viewer, the viewer is no longer a player (it left, or its player changed country), or the
player is the viewer already (which rebuilds the Nuclear Reach store each month), so an entry's page opened from the
journal has one too, and the pulse never takes the view from one player to give it to another (#1809). Like the pick,
it is one for every player in a multiplayer game: there the player who last clicked sees their own deterrent and
networks, and another player looking at those maps sees the same viewer's until they click, a known limit. Whether `global_var:` holding a country compares
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
- `te_jmap_pick_row`: the Map Room's picks on its page, generated (`gen_journal_map_picks.py`: `MAPS`, each map's pick
  key, selector and gate, and `GROUPS`, its place), in eight groups by theme (2026-11-23, #1974; seven by game system
  from 2026-11-11), each a collapsible section: a header (`te_jmap_category_header`, the Demographics tab's
  `section_header_button` at 470 wide) over its rows (`te_jmap_category`), shown while the group's client-side flag
  `te_jmap_cat_<key>_open` is set. Every group starts collapsed, a long list (`gui_style_guide.md` § Sections), and the
  flags outlive a pick's reopen, as the see-through flag does, so a group opened stays open from map to map. Population
  (Population, Population Density, Urban People; Population Growth, Net Migration, Crowding Penalty; City Rank);
  Families and Ages (Births, Deaths, Natural Change; Fertility, Family Planning, Median Age; Aged 65 and Over, Sex
  Balance); Living Conditions (Standard of Living, Wealth, SoL vs Wealth; SoL vs Expected, Below Expected SoL, Literacy; Life Expectancy,
  Infant Mortality, Leading Cause; Health Care); Classes (every pop type since #1975, five rows of three by theme,
  each class's two picks in one place: § The Class Maps); Economy (GDP, GDP per Capita; Unemployment, Vacant Jobs; Gini,
  Dynastic Wealth, Ownership; Company HQs, Investment, Trade Capacity; Infrastructure, Market Access; Power Grids, Grid Flows);
  Politics (Turmoil, Radicals vs Loyalists, Discrimination; Political Models, United Nations, Colonies); Military and Security (Armed
  Forces, Fighting-Age Men, War Dead; Devastation, Nuclear Weapons, Nuclear Reach; Agent Networks); Land and Environment (Base Comfort,
  Current Comfort, Tourism Appeal; Pollution, Emissions; Ocean Basins, Grandeur). Each button keeps its own gate, so a census map
  hides while the census doesn't run and a system's map while its rule is off. A group whose every map is gated hides
  with them, header and all (`te_jmap_cat_<key>_sgui`, generated where a group has no map every player sees: today
  Families and Ages, and Living Conditions too until #1976 gave it maps of its own), and a row whose maps share a gate hides with it, so a closed census leaves
  no empty row's spacing. Until #1974 the Census header stayed with nothing under it. `test_journal_map_modes.py`'s
  `CategoriesTest` holds every pick to one group; `test_journal_map_picks.py` holds the generator.
- `te_jmap_options`: the Map Room's options (2026-11-14, § The Map Room's Options), one more collapsible section in
  the picks' form, mounted below `te_jmap_pick_row` on the page (`te_map_room_widget.gui`) and closed at first
  (`te_jmap_options_open`), with the options in force at the header's right. Open: an Area row of five buttons
  (World, Continent, Market, Power Bloc, Country, each as wide as its label, 450 in all inside the header's 470);
  under Continent, two rows of three continents; an Outliers row (Keep All, Trim 4 Each End, Trim 5%); since the
  thirteenth pass a Scale row (Map Default, Linear, Logarithmic, Ranked, 112 each) and since the fourteenth a
  Color row (Map Default, Colorblind-Safe, Grayscale, 150 each); and a line saying what the map on
  the page was measured over, or under Ranked how old its places can be. Each is a `te_jmap_option_button` on a
  scripted GUI (`te_jmap_area_*_sgui`, `te_jmap_continent_*_sgui`, `te_jmap_trim_*_sgui`, `te_jmap_scale_*_sgui`,
  `te_jmap_color_*_sgui`),
  then the picks' repaint. Unlike a pick, an option draws pressed from its script value (`down` on `te_jmap_area`,
  `te_jmap_continent`, `te_jmap_trim`, `te_jmap_scale`), not from `is_valid`, which is kept for what greys it
  (`enabled`): Power Bloc with no bloc; Outliers on a map with no range or under Ranked; Linear, Logarithmic and
  Ranked on a map with no range; each with its reason in the tooltip (`SelectLocalization` on the same `IsValid`,
  nested where there are two reasons). A click on the option already in force measures and repaints again. `OptionsTest` holds each button to
  its scripted GUI, its number and the repaint.

- **The class maps' Classes row** (#1975), last in Map Options: Count and Share (150 each), on the class maps'
  switch (`te_jmap_classes_count_sgui`, `te_jmap_classes_share_sgui`, `te_jmap_set_class_mode`), pressed from
  `te_jmap_class_mode` and greyed off a class map (§ The Class Maps).

The play-test's harness is gone: the debug strip, the scope probe (selector 6), the Potential probe entry and the
listed copy of the journal map mode, each answered (`docs/testing/journal-map-modes-playtest.md`, fourth session).

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; give each `lerp` its factor as a row in `gen_journal_map_scales.py`'s `TABLE` and
   re-run it (`test_journal_map_scales.py` checks the trees and that the map reads no factor the table lacks). Fit it
   to the world unless its numbers mean something fixed (a row with `sel`, `where` and a `rel*` shape: the range
   effect, the dispatcher's branch and the trees come with it, and so do the Map Room's options: the range keeps to
   its area and takes its trim, the factor branches on the scale, and a rank effect stores its places). Give its
   pick's tooltip its four lines (§ Color, "The tooltips"): what it shows, with no word of a curve, a color or
   a range; the range (`$te_jmap_scaled_lead$ $te_jmap_measured_area$:`, `te_jmap_<map>_lo` / `_hi`, then
   `$te_jmap_measured_trim$`); the scale's line, choosing between `te_jmap_curve_<shape>` (the generator's
   `curve_key`; a new shape needs its key, with `curve_words`' text) and `te_jmap_scale_in_force` or its
   `_doubling` or `_mid` form; and the colors' line, choosing between a new `te_jmap_pick_<map>_colors` (which
   color is its low end, which its high, and anything it paints apart from its scale) and `te_jmap_color_in_force`
   or its `_none`, `_hq`, `_gw` or `_mid` form (`PickTooltipTest`). The Color option needs nothing else from a
   fitted row: `te_jmap_pick_ramp` and `te_jmap_pick_factor` gain its branch from the table (give the row `paint`
   if its lerp branch isn't limited by its `where`), and a color it paints flat that is neither "none" nor "no
   data" must join `te_jmap_pick_below` (`ColorTest` fails until it does). Mark it
   `entry` if a system's own entry draws it: the entry then reads `te_jmap_<map>_factor`, on the whole world's range,
   and the Map Room its twin, `te_jmap_<map>_room_factor` (and `te_jmap_<map>_room_lo` / `_hi` in the tooltip).
2. A pop type the game adds is a row in `journal_map_classes.py`'s `CLASSES` and a place in its `ROWS`, then the three
   generators (`gen_journal_map_classes.py`, `gen_journal_map_scales.py`, `gen_journal_map_picks.py`) and
   `organize_loc.py`: its two maps, picks, colors and loc come with it (§ The Class Maps).
3. A system with no entry borrows the Map Room: a new selector number, its branches in `map_color` and `map_tooltip`, a
   row in `gen_journal_map_picks.py`'s `MAPS` (its key, selector and gate) and a place in one of its `GROUPS`, then a
   rerun, which writes its pick's scripted GUI and button; and loc for both (`te_jmap_pick_<key>`, `_desc`). A map that reads a stored
   figure joins `map_color`'s "no data" `OR` and one of `map_tooltip`'s (`test_journal_map_modes.py` checks it). A
   figure behind a long `state_region` chain is stored by the refresh that already computes it, not read live
   (tourism's and Local Climate's are the pattern). The Area option needs nothing from a new map: `map_color`'s and
   `map_tooltip`'s first branches grey a state outside the area before any selector is read. A new stripe or second
   hover line asks `te_jmap_in_area = yes` after its selector.
4. A map on both an entry and the Map Room asks shared triggers (`te_journal_map_triggers.txt`) in the same order in
   both, and joins `SYSTEM_MAPS` in `test_journal_map_modes.py`, whose parity test compares them.
5. A "show on the map" button opens a page: the entry's (`te_jmap_banking_map_button`) when every country holds it,
   or the Map Room on the system's pick (`te_jmap_gw_map_button`) when not. A tab showing an entry's content doesn't
   trigger its map.
