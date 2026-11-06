# Journal entry map modes: play-test checklist

The in-game checks for vanilla 1.15's journal entry maps (`docs/systems/mod_systems/journal_map_modes.md`, issue
#1404), most important first. The first pass (#1410, #1414) answered most of its list; this is the second pass's list,
for the contextless Map Room and its page of picks. Record each answer under Results, in
`docs/audits/vanilla_1_15_prep.md` § 2 under C6, and each engine fact in `docs/guides/scripting_best_practices.md` §
"Journal Entry Map Modes".

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work", from the full checkout: the branch keeps
  `gfx/map/map_modes/te_map_modes.txt`, so a sparse worktree's deploy would also delete textures.
- **A new game**, or a save: the first pass's `je_te_map_host` and `je_te_map_hidden_world` are gone, and a save that
  holds them may log their records as unknown at load. Note any such line; it is harmless for a test build.
- **Launch with `-debug_mode`** for the test strip, which sits on the Demographics tab (Population panel, last tab),
  above the sections, under a "Map tests" heading. Demographics on Full or Display only, the default. The map button in
  the tab's header (left of "?") needs no debug mode.
- **Logs.** `grep TE_JMAP debug.log` (or `curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_JMAP"`):
  every pick writes `TE_JMAP pick <n> date=…`, and the Potential probe its on and off.
- **At load**, check `error.log` for lines naming `te_map_widgets.gui`, `te_map_room_widget.gui`,
  `te_journal_maps.txt` or `te_journal_map_sguis.txt`, `failed reading callback` above all: the engine drops a callback
  it can't read and says so only there, once.

## The checks (second pass)

| # | Check | How | What each answer means | If it's the bad answer |
|---|---|---|---|---|
| 1 | One click opens the Map Room, with its picks on the page | Click the Demographics header's map button once. | The Map Room's page opens at once and the map turns to life expectancy (paused: at unpause). Two rows of pick buttons sit above the description: a widget draws on a contextless page, and the next pass builds on it. | No page: read `error.log` for a callback line. A page without the buttons: the widget doesn't draw on a contextless page; use the strip's row (the same buttons) for checks 2–4, and the picks move beside the map buttons in the next pass. |
| 2 | Picks on the page | Click Turmoil, Literacy, then the three census maps, with the game running. | The map changes at each click (at the next tick), and the current pick's button draws pressed (`down`, which no mod `.gui` used before). | Buttons do nothing: read `debug.log` for `TE_JMAP pick` lines (none: the scripted GUI didn't run from the page). No pressed state: note it; a label can mark the pick instead. |
| 3 | The scope probe on a contextless entry | Pick Scope Probe (Test). | **Yellow**: `scope:journal_entry` is set in a contextless entry's map. **Blue**: it isn't. Either is fine (the pick is global). **White stripes** over your own states: `map_color_second` and the state's `owner` link work, so a map can mark the player's land. | No stripes: a map can't single out the player's states that way; note it. |
| 4 | Repaint while paused | Pause. Pick another map. Then (a) click the strip's Open Map Room, which reopens the page; (b) if that doesn't repaint, switch the map mode away and back with the lens toolbar. | (a) or (b) repaints: the buttons can do the same after a pick, so a paused player sees their pick at once. | Neither: a pick shows at unpause; say so in the picks' tooltips. |
| 5 | The map with the page closed | (a) With the Map Room open, turn on the lens toolbar's lock (the padlock by the map mode name), then close the page. (b) With no page open, pick **Journal Entry Map (Test)** from the map mode dropdown; then again after opening and closing the Map Room, and after Banking. | (a) The map stays: a journal map can be pinned. (b) It paints, and the colors say whose map it is (the Map Room's pick, or Banking's phases): the listed copy is a way to show a map with no page. Nothing painted: a journal map needs its page. | If neither holds, a map exists only while its page is open; say so in each map button's tooltip, and drop the listed copy. |
| 6 | Banking map, and whether a tab opens it | Open the Budget panel's Banking tab: does the map change by itself? Then the tab header's map button. | The tab alone paints it: any panel showing an entry through `GetPlayerJournalEntry` triggers its map (prep C6). Only the button: as built. Look: every country in its phase's color, yellow stripes on the overheating, grey where the cycle hasn't started. | — |
| 7 | An inactive entry's page (prep C6) | Save first: (a) asks the journal panel for an entry it never lists. (a) Before anything else, click the strip's **Open Potential Probe**: every country holds an inactive copy of a country entry with activation triggers, so the button shows from the start. Does a page open for an entry shown nowhere? (b) Click **Potential Probe**; note the date of `TE_JMAP potential probe on` and the day the entry appears in the journal's Potential section. (c) Open it from the journal (or the strip): does the map turn **magenta**? | (a) A page opens: `GetPlayerJournalEntry` returns an inactive copy and the panel opens it, so a system's map button needn't wait for its entry. (b) The wait for a shown inactive entry (the first pass's activations came up to two weeks after the click). (c) Magenta: an inactive page paints its map, so Banking's map button can show before a country's cycle starts. | (a) A crash or an error: never open an entry the player can't see; note the log line. (c) No magenta: a map needs an active entry; keep Banking's button gated on `IsActive`. |
| 8 | Look and feel | With each map up, judge the palette, the grey "no census" states, borders, and the hover text (state name and figure). The same for Banking. | Notes for the next pass: colors to change, a legend wanted (vanilla draws none for journal maps, as far as known), text to add. | — |
| 9 | How water, wasteland, unowned and decentralized land draw | Look at them on any map. | Recorded for the system doc. Unowned land has no `owner`, so Banking leaves it unpainted. | — |
| 10 | Cost | With a census map up, run at top speed for a year and compare with the map off. | No visible slowdown: per-state variable reads are cheap enough. A slowdown: note it; maps may need fewer branches. | Fewer branches per map. |

## The first pass's checks, answered

From #1410's list (its numbering), by the three sessions under Results:

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
- **Second pass built on these** (this list): the Map Room is contextless, its picks are scripted GUIs on its page, the
  Demographics button is one click, and the first pass's host, hidden world entry, add, request, close and hover
  buttons are gone.

## Not tested here

- Whether `map_color` takes a scope path (`value = owner.color`, prep C21): left out, since a field the engine rejects at
  load can drop the whole entry it sits in. Try it in its own entry once checks 1–2 pass.
- Multiplayer: two players share the Map Room's pick (a global variable). Whether that is acceptable is a design
  call; nothing tests it.
- `add_involved_country` on the Map Room (its own scripted buttons would unlock), and whether an involved country sees
  a contextless entry in its journal.

## When it's done

- Delete the test pieces: `te_jmap_test_strip` and its mount (`tab_before_gate` in `te_demographics_layout.gui`), the
  `te_jmap_strip_*` loc keys, the Scope Probe (selector 6: `te_jmap_pick_scope_probe_sgui`, its button in
  `te_jmap_pick_row`, its branches, colors and tooltips), `je_te_map_potential_probe` with its two scripted GUIs, color
  and loc, the `TE_JMAP pick` debug line in `te_jmap_set_selector`, and `gfx/map/map_modes/te_map_modes.txt` unless
  check 5 (b) makes it worth keeping (its name, `mm_te_journal_entry_map`, sits in `te_unused_l_english.yml`, since
  `organize_loc.py` doesn't read `gfx/`).
- Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1).
- Give the player guide its lines: the Demographics and Banking chapters' map buttons, and the Map Room.
