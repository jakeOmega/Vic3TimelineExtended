# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Fifth pass, 2026-11-05 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). The first pass (#1410, #1414) was
built ahead of the in-game checks and answered most of them; the second (#1417) rebuilt the Map Room on those answers,
and the third (#1420) added what its play-test asked for: picks that repaint a paused map, and the see-through journal
page. Its picks closed the page for good, so the fourth (#1424) moved their repaint to a widget outside the page, which
worked. The fifth tries a shorter repaint, adds Devastation, Urban People, the Gini coefficient, Dynastic Wealth and
eight more census maps, and drops Literacy, which vanilla's own literacy map mode shows.
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
the maps read stored variables and engine figures, never walk pops. Each map's color comes from a factor, 0–1, on a
fixed curve (life expectancy 25–80), so a color means the same thing in 1850 and 1950. Colors are named in
`common/named_colors/te_journal_map_colors.txt`, one family per map.

**The curves are generated** (`scripts/generators/gen_journal_map_scales.py` →
`common/script_values/te_journal_map_scales_generated.txt`, `te_jmap_<map>_factor`). A script value takes no arguments
and a paint runs no effect, so one shared curve can't be fed each map's figure (`te_sqrt`'s input is a variable an
effect sets); the generator writes each map's tree from a table row instead, using one of three shapes: linear, a soft
cap (straight to a soft bound, then `SLOPE_RATIO`, 4, times shallower to a hard one, so the common values get most of
the color and the extremes still differ) and diverging (0.5 at a midpoint, each side straight or soft-capped). Changing
a shape changes every map using it. Each tree reads its figure only inside an `if` on its `has_variable` guards (a
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
  (`te_dg_wc`, 0–50–100, diverging where its effects turn from dispersed to concentrated property). The census's, from each state's figures (`te_demog_effects.txt`'s header): 3 life
  expectancy, 10 infant mortality, 4 fertility, 5 median age, 14 aged 65 and over and 12 sex balance from a state's first
  seed; 9 births, 8 deaths and 7 natural change per 1,000, 13 net migration and 11 the leading cause of death only once
  the state has stepped a full year (`te_dg_stepped` above 0, as the panel gates them: a seed writes those rates as 0).
  Every map that reads a stored figure shows grey (`te_jmap_no_data`) for a state without one, through one `OR` branch
  that lists them all. Each curve is fixed and historical. Soft caps: turmoil and devastation half the color by 20%,
  all at 100%; deaths per 1,000 70% of it from 5 to 40, all at 100. Diverging: infant mortality 0–50–300 (soft) to
  500, natural change −40 to −15 (soft), 0, +30 (soft) to +45, net migration ±20 (soft) to ±60, sex balance 80–100–130
  from the census's own effect thresholds, Dynastic Wealth 0–50–100. Linear: births 8–50, 65 and over 2–30%, Gini
  0.30–0.80. Each pick's tooltip says where its bends are, since the map has no legend. The leading cause is categorical, in the Causes of Death
  pie's colors (`gen_ch_model_pie_textures.py`; the old code 6 draws as war, as the panel's icon does), and its hover
  is a branch per cause. 2 was literacy, retired because vanilla's literacy map mode shows it: a save holding 2 shows
  the unpainted map and "Pick a map" until the next pick.
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
`GetVariableSystem` key `te_je_see_through`, and the panel's root binds `alpha` to it: 0.3 while set, so the page's
map shows through. The flag outlives a reopen, so the Map Room stays faded from pick to pick; the header's close and
back buttons clear it (vanilla's own lines first; Escape runs the close), and so do the two map buttons before they open
a page. Clearing on `_show` would unfade the page at every pick, since a pick's reopen fires it. Leave a faded page by
opening another panel and the next journal page opened from the journal is faded too. The faded page still takes clicks: the window's frame is a `clickthrough_blocker` in no block the panel
can override, and a fold that hid the content would leave the same full-height frame. On every page because the GUI
can't tell which entries carry a map, and vanilla's own map entries gain from it too. Whether `alpha` binds on a side
panel's root is untested (vanilla binds it only on inner widgets; third pass, check 2).

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

Both map buttons clear the see-through flag before they open a page.
- `te_jmap_pick_row`: the Map Room's picks on its page: the world's maps in a row of three and a row of two (Gini,
  Dynastic Wealth), then the census's eleven three to a row.

The play-test's harness is gone: the debug strip, the scope probe (selector 6), the Potential probe entry and the
listed copy of the journal map mode, each answered (`docs/testing/journal-map-modes-playtest.md`, fourth session).

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; give each `lerp` its factor as a row in `gen_journal_map_scales.py`'s `SCALES` and
   re-run it (`test_journal_map_scales.py` checks the trees and that the map reads no factor the table lacks).
2. A system with no entry borrows the Map Room: a new selector number, its branches in `map_color` and `map_tooltip`, a
   pick scripted GUI and its `te_jmap_pick_button` in `te_jmap_pick_row`, and loc for both. A map that reads a stored
   figure joins both "no data" `OR`s (`test_journal_map_modes.py` checks it).
3. A "show on the map" button opens the entry's page (`te_jmap_banking_map_button` is the pattern), for a system in
   a tab too: a tab showing an entry's content doesn't trigger its map.
4. Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) once one map is seen working in game.
