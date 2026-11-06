# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Second pass, 2026-11-05 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). The first pass (#1410, #1414) was
built ahead of the in-game checks and answered most of them; the second rebuilt the Map Room on those answers.
`docs/testing/journal-map-modes-playtest.md` lists what is still open, and this file says which parts rest on an
unverified engine fact. Update both as the answers come in.

## How a Journal Entry Paints the Map

Vanilla 1.15 gives a journal entry three optional blocks (`game/common/journal_entries/journal_entries.md`):

- `map_color` returns a color for a state: a named color (`value = "te_jmap_no_data"`), an RGB triple, or
  `lerp = { min_color max_color factor }` with a 0–1 factor. It takes `if` / `else_if` like a script value (vanilla's
  ACW, Meiji and Hungry Forties entries branch on it), and a branch that matches nothing leaves the state unpainted.
- `map_color_second` is the same, drawn as stripes over the first color.
- `map_tooltip` is an effect block that only prints: `custom_tooltip_no_bullet = key` per branch. Its loc reaches the
  state as `[THIS.GetState…]` (`GetName`, `GetOwner.GetName`, `CalcTurmoil|v%1`, `GetLiteracy|%1v`,
  `MakeScope.Var('x').GetValue`).

**The root is the state being painted**, every state in the world, so `owner` is that state's country, not the player.
A map of the player's own data, or a map whose look the player picks, needs something every state can read:
`map_color` reaches neither `scope:journal_entry` nor its owner (the first pass's scope probe painted blue, 2026-11-05).
So the Map Room's pick is a global variable (`te_jmap_selector`, `common/script_values/te_journal_map_values.txt`), and
two players in one game share it. `map_color` is re-evaluated as the game runs (a weekly tick map stepped with the page
open), and a pick shows at the next tick: paused, at unpause.

**The engine shows the map itself.** `mm_journal_entry_map_data` (`gfx/map/map_modes/map_modes.txt`) is
`is_visible = no`, "overriden in code", and no vanilla `.gui` names it. The map shows while an entry with these blocks
has its page open and goes when the page closes (seen 2026-11-05), which is why every "show on the map" button here
opens a page. `SetTempMapModeByKey` on that mode paints nothing.

**Cheap reads only.** Every value runs once per state, as the game runs, so
the maps read stored variables and engine figures, never walk pops. Factors are clamped to fixed bounds (life
expectancy 25–80), so a color means the same thing in 1850 and 1950. Colors are named in
`common/named_colors/te_journal_map_colors.txt`, one family per map.

## The Map Room

`je_te_map_room` (`common/journal_entries/te_journal_maps.txt`) is a map with no system of its own: several maps on one
entry, in no country's journal.

- **Contextless, nobody involved.** `context = none`, `should_be_involved` and `should_show_when_not_involved` both
  `always = no`, `is_shown_when_inactive = { always = yes }` and no `possible`: the entry is active from the game's start
  and listed in no journal. A button opens its page at the first click (`GetPlayerJournalEntry` finds it). The first
  pass proved the shape with a test entry (`je_te_map_hidden_world`, 2026-11-05).
- **Several maps.** `map_color` is an `if` / `else_if` ladder on `te_jmap_selector`: 1 turmoil, 2 literacy, 3 life
  expectancy, 4 fertility, 5 median age (the three census maps read `te_dg_e0`, `te_dg_tfr`, `te_dg_median` and show grey
  before a state's first census), 6 the scope probe (a test).
- **Picks are scripted GUIs on a page widget, not scripted buttons.** The engine locks a scripted button for a country
  not involved in its entry ("Countries that are not involved in the Journal Entry may not take this action"), and
  nobody is involved in the Map Room. So `te_jmap_pick_<map>_sgui` (`common/scripted_guis/te_journal_map_sguis.txt`)
  set the global pick with the player as root, and `te_jmap_pick_row` (`gui/te_map_widgets.gui`) draws them: on the
  page through the entry's `widget` (`gui/journal_entry_widgets/te_map_room_widget.gui`, above the description), and on
  the debug strip. A pick's `is_valid` is false while it is the pick, which its button draws pressed (`down`); the census
  maps' `is_shown` hides them while the census doesn't run. Whether the widget draws on a contextless page is untested
  (play-test check 1); vanilla's contextless `je_great_game_control` carries one.
- **Nothing to inherit.** `transferable = no`, `can_revolution_inherit = no`; the pick is global.

### Why not a country entry added by a button

The first pass's Map Room, `je_te_map_host`, was a country entry kept out of the journal by a variable its
`is_shown_when_inactive` and `possible` read, and added by `add_journal_entry`. The add never worked: every country
holds an inactive copy of a country entry with its own activation triggers from the game's start, and
`add_journal_entry` is refused while one exists ("already has a journal entry of type", 2026-11-05). The variable then
made the copy shown (the journal's Potential section) and the engine activated it at its own check, up to two weeks
later. An entry with neither trigger has no copy until added, so `add_journal_entry` would work on it, but then nothing
takes it out again short of an outcome, which leaves it in the concluded tab. The contextless entry needs neither.

## The Banking Map

`je_banking_cycle` (`common/journal_entries/je_banking.txt`) colors each country by its cycle's phase, the panel's own
bands (`banking_cycle_is_*`, `market_triggers.txt`), panic red to frenzy magenta, with yellow stripes where
`banking_cycle_bubble_risk_high` holds (the overview's crash-risk badge). A country whose cycle has not started is grey;
one without the entry is unpainted. The tooltip names the country, the phase word (`banking_dash_phase_word`) and the
cycle value. Every country holds the entry, so this is a world map read from each state's owner.

## Buttons and the Test Strip

`gui/te_map_widgets.gui`. Every button that opens an entry carries it as the button's `datacontext`
(`GetPlayerJournalEntry('<key>')`) and passes `JournalEntry.AccessSelf`: inside a callback, `GetPlayerJournalEntry`
fails at load whether bare or ended with `.AccessSelf` (`gui_modding_guide.md` gotcha #29).

- `te_jmap_demog_map_button`, in the Demographics tab's header (`te_demog_window_body`, so the Population panel's tab and
  the Timeline Extended window's), left of the "?": one click picks life expectancy and opens the Map Room.
- `te_jmap_banking_map_button`, in the Banking tab's header (`te_banking_tab_body`): opens `je_banking_cycle`.
- `te_jmap_pick_row`: the Map Room's picks, two rows of three, on its page and on the strip.
- `te_jmap_test_strip`, on the Demographics tab above its sections, in debug mode only (`InDebugMode`): the pick row
  (a fallback if the page's widget doesn't draw), Open Map Room (no pick change), and the Potential probe's two buttons.
  `je_te_map_potential_probe` is a country entry held in Potential (`possible = { always = no }`) by a variable the
  strip toggles: whether an inactive entry's page paints its map (prep C6).
- `gfx/map/map_modes/te_map_modes.txt` defines `mm_te_journal_entry_map`, vanilla's journal entry painting with
  `is_visible = yes`, so it is listed in the lens toolbar's map mode dropdown: the test of a journal map with no page
  open (check 5). The game loads with it (2026-11-05); nothing else needs it. Its name's loc sits in
  `te_unused_l_english.yml`, because `organize_loc.py` doesn't read `gfx/`.

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; put each `lerp` factor in a clamped script value.
2. A system with no entry borrows the Map Room: a new selector number, its branches in `map_color` and `map_tooltip`, a
   pick scripted GUI and its button in `te_jmap_pick_row`, and loc for both.
3. A "show on the map" button opens the entry's page (`te_jmap_banking_map_button` is the pattern).
4. Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) once one map is seen working in game.
