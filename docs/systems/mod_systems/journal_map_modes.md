# Journal Entry Map Modes

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

First pass, 2026-11-05 (issue #1404, `docs/audits/vanilla_1_15_prep.md` § 4.1). Built ahead of the in-game checks that
decide how far it can go: `docs/testing/journal-map-modes-playtest.md` lists them, and this file says which parts rest on
an unverified engine fact. Update both as the answers come in.

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
A map of the player's own data, or a map whose look the player picks, needs something every state can read. The mod
writes the pick to the player's country and to a global variable (`te_jmap_selector`,
`common/script_values/te_journal_map_values.txt`) and reads the country through `scope:journal_entry.owner` when that
resolves; whether it does is check 2 of the play-test.

**The engine shows the map itself.** `mm_journal_entry_map_data` (`gfx/map/map_modes/map_modes.txt`) is
`is_visible = no`, "overriden in code", and no vanilla `.gui` names it. The working assumption, not yet seen in game, is
that the map shows while an entry with these blocks has its page open, which is why every "show on the map" button
here opens a page.

**Cheap reads only.** Every value runs once per state, at a rate not yet measured (the refresh-tick map measures it), so
the maps read stored variables and engine figures, never walk pops. Factors are clamped to fixed bounds (life
expectancy 25–80), so a color means the same thing in 1850 and 1950. Colors are named in
`common/named_colors/te_journal_map_colors.txt`, one family per map.

## The Map Room

`je_te_map_host` (`common/journal_entries/te_journal_maps.txt`) is a map with no system of its own: several maps on one
entry, and an entry that sits out of the journal until a button asks for it.

- **Several maps.** `map_color` is an `if` / `else_if` ladder on `te_jmap_selector`: 1 turmoil, 2 literacy, 3 life
  expectancy, 4 fertility, 5 median age (the three Demographics maps read the census's `te_dg_e0`, `te_dg_tfr`,
  `te_dg_median` and show grey before a state's first census), 6 the scope probe, 7 the refresh tick. The entry's
  scripted buttons (`common/scripted_buttons/te_journal_map_buttons.txt`) set it, each marked `selected` while it is the
  pick; the three Demographics buttons show only while the census runs.
- **Out of the journal until wanted.** The country variable `te_jmap_host_on` holds the entry open: its
  `is_shown_when_inactive` and `possible` read it, and `can_deactivate = yes`. A button adds the entry at once
  (`te_jmap_open_host`, `add_journal_entry`, which ignores those triggers), or sets the variable alone and lets the
  engine activate it (`te_jmap_request_host`, the test strip's route, to time it). Close removes the variable; the entry
  goes back to inactive, which hides it. There is no `remove_journal_entry` effect in 1.15, so `can_deactivate` is the
  only way out short of concluding.
- **Not inherited.** `transferable = no`, `can_revolution_inherit = no`: a view, not state. The selector and
  `te_jmap_host_on` are plain variables a revolution's winner inherits, which does no harm (a winner that never opened
  the Map Room is offered the same buttons).
- **The scope probe and the refresh tick** are test maps (check 2 and check 4) and go once answered.

`je_te_map_hidden_world` beside it is a test: a contextless entry (`context = none`) nobody is involved in or can see,
active from the start, painting every state one magenta. It answers whether an entry outside every journal can still
be opened by a button and paint.

## The Banking Map

`je_banking_cycle` (`common/journal_entries/je_banking.txt`) colors each country by its cycle's phase, the panel's own
bands (`banking_cycle_is_*`, `market_triggers.txt`), panic red to frenzy magenta, with yellow stripes where
`banking_cycle_bubble_risk_high` holds (the overview's crash-risk badge). A country whose cycle has not started is grey;
one without the entry is unpainted. The tooltip names the country, the phase word (`banking_dash_phase_word`) and the
cycle value. Every country holds the entry, so this is a world map read from each state's owner.

## Buttons and the Test Strip

`gui/te_map_widgets.gui`:

- `te_jmap_demog_map_button`, in the Demographics tab's header (`te_demog_window_body`, so the Population panel's tab and
  the Timeline Extended window's), left of the "?": Add while the Map Room is out of the journal, Open once it is in, each
  picking life expectancy. A scripted GUI's effect lands after the click, so one click cannot both add the entry and open
  it; the test strip checks that.
- `te_jmap_banking_map_button`, in the Banking tab's header (`te_banking_tab_body`): opens `je_banking_cycle`.
- `te_jmap_test_strip`, on the Demographics tab above its sections, in debug mode only (`InDebugMode`): Add + Open in one
  click, Request (the activation-trigger route), Close, Hidden Entry (`je_te_map_hidden_world`), and two hover previews
  (`SetTempMapModeByKey` on vanilla's mode and on the mod's listed copy). Add + Open names the entry with no datacontext,
  as `GetPlayerJournalEntry('je_te_map_host').AccessSelf`: `GetPlayerJournalEntry` is a promote only, and passed bare as
  an argument it failed at load and lost the button its second click (`gui_modding_guide.md` gotcha #29).
- `gfx/map/map_modes/te_map_modes.txt` defines `mm_te_journal_entry_map`, vanilla's journal entry painting with
  `is_visible = yes`, so it is listed in the lens toolbar's map mode dropdown: the test of a journal map with no page
  open. The game loads with it (first launch, 2026-11-05); nothing else needs it.

## Adding a Map

1. Add `map_color` (and `map_color_second`, `map_tooltip`) to the system's entry, branching on `owner ?= { … }` for a
   per-country map or on the state's own variables for a per-state one. Name the colors in
   `te_journal_map_colors.txt`; put each `lerp` factor in a clamped script value.
2. A system with no entry borrows the Map Room: a new selector number, its branches in all three blocks, a pick button.
3. A "show on the map" button opens the entry's page (`te_jmap_banking_map_button` is the pattern).
4. Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) once one map is seen working in game.
