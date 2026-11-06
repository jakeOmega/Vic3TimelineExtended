# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Seventh pass, 2026-11-06 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). The first pass (#1410, #1414) was
built ahead of the in-game checks and answered most of them; the second (#1417) rebuilt the Map Room on those answers,
and the third (#1420) added what its play-test asked for: picks that repaint a paused map, and the see-through journal
page. Its picks closed the page for good, so the fourth (#1424) moved their repaint to a widget outside the page, which
worked. The fifth (#1425) tried a shorter repaint, added Devastation, Urban People, the Gini coefficient, Dynastic
Wealth and eight more census maps, and dropped Literacy, which vanilla's own literacy map mode shows. The sixth adds a
map for eight of the mod's systems, each on its own entry and in the Map Room (below), a map button in each of their
tabs and a Map Room button in the Timeline Extended window, and fades the see-through page to 20%. The seventh adds
five maps to the Map Room alone: Tourism Appeal, Base and Current Comfort, GDP per Capita and the Crowding Penalty.
`docs/testing/journal-map-modes-playtest.md` lists what is still open, and this file says which parts rest on an
unverified engine fact. Update both as the answers come in.

## How a Journal Entry Paints the Map

Vanilla 1.15 gives a journal entry three optional blocks (`game/common/journal_entries/journal_entries.md`):

- `map_color` returns a color for a state: a named color (`value = "te_jmap_no_data"`), an RGB triple, or
  `lerp = { min_color max_color factor }` with a 0–1 factor. It takes `if` / `else_if` like a script value (vanilla's
  ACW, Meiji and Hungry Forties entries branch on it), and a branch that matches nothing leaves the state unpainted.
- `map_color_second` is the same, drawn as stripes over the first color (vanilla's Great Game and Forest of Bayonets
  stripe through the state's `owner`). Under `owner ?= { is_player = yes }` it drew nothing (2026-11-05), so a map most
  likely can't single out the player's own states.
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
the maps read stored variables and engine figures, never walk pops. A figure behind a long `state_region` chain is
stored by the refresh that already computes it: tourism's Base Appeal (some 700 branches) and Local Climate's
penalties (eight chains of 680). Each map's color comes from a factor, 0–1, on a
fixed curve (life expectancy 25–80), so a color means the same thing in 1850 and 1950. Colors are named in
`common/named_colors/te_journal_map_colors.txt`, one family per map.

**The curves are generated** (`scripts/generators/gen_journal_map_scales.py` →
`common/script_values/te_journal_map_scales_generated.txt`, `te_jmap_<map>_factor`). A script value takes no arguments
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
  force), both yearly and on one curve and palette, diverging at none: a mild winter's draw green down to −7.2, a cost
  red, soft-capped at 30 to the cap of 80. The census's, from each state's figures (`te_demog_effects.txt`'s header): 3 life
  expectancy, 10 infant mortality, 4 fertility, 5 median age, 14 aged 65 and over and 12 sex balance from a state's first
  seed; 9 births, 8 deaths and 7 natural change per 1,000, 13 net migration and 11 the leading cause of death only once
  the state has stepped a full year (`te_dg_stepped` above 0, as the panel gates them: a seed writes those rates as 0).
  Every map that reads a stored figure shows grey (`te_jmap_no_data`) for a state without one, through one `OR` branch
  that lists them all; the hover has two, "No census figures yet" for the census and walk maps and "No figure yet" for
  tourism and the two comfort maps, whose refreshes run within a month (Local Climate's first application keys on
  `te_climate_base_penalty`, so an older save fills Base Comfort within a month too). Each curve is fixed and historical. Soft caps: turmoil and devastation half the color by 20%,
  all at 100%; deaths per 1,000 70% of it from 5 to 40, all at 100. Diverging: infant mortality 0–50–300 (soft) to
  500, natural change −40 to −15 (soft), 0, +30 (soft) to +45, net migration ±20 (soft) to ±60, sex balance 80–100–130
  from the census's own effect thresholds, Dynastic Wealth 0–50–100. Linear: births 8–50, 65 and over 2–30%, Gini
  0.30–0.80. Each pick's tooltip says where its bends are, since the map has no legend. The leading cause is categorical, in the Causes of Death
  pie's colors (`gen_ch_model_pie_textures.py`; the old code 6 draws as war, as the panel's icon does), and its hover
  is a branch per cause. 2 was literacy, retired because vanilla's literacy map mode shows it: a save holding 2 shows
  the unpainted map and "Pick a map" until the next pick. 18-25 are the systems' maps, each also on its own entry
  (below).
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
  carries the Map Room as its own `datacontext`. A twentieth of a second after the click it closes the page
  (`InformationPanelBar.ClosePanel`), for the scripted GUI's effect to land, and its next state,
  `te_jmap_repaint_open`, opens the page again a twentieth of a second later with the plain `OpenJournalEntryPanel`: the
  page is closed by then, so the toggle opens it. Reopening repainted a paused map (2026-11-05). The third pass ran both
  calls from a state on the pick button itself, `ClosePanel` then `OpenJournalEntryPanelDontToggle`: the page closed
  and stayed closed, with no log line (fifth session). The reopen logs `TE_JMAP reopen` first. It worked with a quarter
  second's close and a tenth's reopen (sixth session); a twentieth each is the fifth pass's test (check 1).
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

Eight of the mod's systems have a map (sixth pass, owner's ask, 2026-11-06), selectors 18-25. Each but the Seabed's is
drawn twice: by the system's own entry, whenever its page is open, and by the Map Room, on a pick. Both ask the same
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
- `te_jmap_<system>_map_button` (gw, nuclear, covert, un, ch, seabed, gm, ce), in each of the eight systems' tab
  headers: one click picks the system's map and opens the Map Room, as the Demographics button does. The Map Room, not
  the system's entry: several entries are held by only some countries or not yet (the nuclear program before its
  technology, covert warfare before its slots, a monument's owner, an empire with colonies), and a button on an entry
  nobody holds has nothing to open. The entry paints the same map when it is opened from the journal.
- `te_jmap_window_button`, in the Timeline Extended window, left of its Full Screen / Side Panel toggle in both frames
  (`te_systems_window_toggle`): opens the Map Room on the last pick, then closes the window, which would cover the page.
  The close comes last, in case a button whose window hides mid-click loses the lines after it.

Every map button clears the see-through flag before it opens a page.
- `te_jmap_pick_row`: the Map Room's picks on its page: the world's maps in a row of three (Turmoil, Devastation,
  Urban People), wealth (GDP per Capita, Gini, Dynastic Wealth), migration attraction (Base Comfort, Current Comfort,
  Crowding Penalty) and Tourism Appeal alone, the systems' eight in rows of three, three and two, then the census's
  eleven three to a row.

The play-test's harness is gone: the debug strip, the scope probe (selector 6), the Potential probe entry and the
listed copy of the journal map mode, each answered (`docs/testing/journal-map-modes-playtest.md`, fourth session).

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; give each `lerp` its factor as a row in `gen_journal_map_scales.py`'s `SCALES` and
   re-run it (`test_journal_map_scales.py` checks the trees and that the map reads no factor the table lacks).
2. A system with no entry borrows the Map Room: a new selector number, its branches in `map_color` and `map_tooltip`, a
   pick scripted GUI and its `te_jmap_pick_button` in `te_jmap_pick_row`, and loc for both. A map that reads a stored
   figure joins `map_color`'s "no data" `OR` and one of `map_tooltip`'s (`test_journal_map_modes.py` checks it). A
   figure behind a long `state_region` chain is stored by the refresh that already computes it, not read live
   (tourism's and Local Climate's are the pattern).
3. A map on both an entry and the Map Room asks shared triggers (`te_journal_map_triggers.txt`) in the same order in
   both, and joins `SYSTEM_MAPS` in `test_journal_map_modes.py`, whose parity test compares them.
4. A "show on the map" button opens a page: the entry's (`te_jmap_banking_map_button`) when every country holds it,
   or the Map Room on the system's pick (`te_jmap_gw_map_button`) when not. A tab showing an entry's content doesn't
   trigger its map.
5. Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) once one map is seen working in game.
