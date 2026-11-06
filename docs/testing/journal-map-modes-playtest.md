# Journal entry map modes: play-test checklist

The in-game checks for vanilla 1.15's journal entry maps (`docs/systems/mod_systems/journal_map_modes.md`, issue
#1404), most important first. The first two passes (#1410, #1414, #1417) answered their lists (below); this is the
third pass's list: picks that repaint a paused map, and the see-through journal page. Record each answer under Results, in `docs/audits/vanilla_1_15_prep.md` § 2 under C6, and each engine fact in
`docs/guides/scripting_best_practices.md` § "Journal Entry Map Modes".

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work", from the full checkout: the branch deletes
  `gfx/map/map_modes/te_map_modes.txt`, and a sparse worktree's deploy would delete every texture with it.
- **A new game** or a save. No debug mode needed: the test strip is gone, and every check uses the map buttons in the
  Demographics and Banking tabs' headers (left of "?") and the Map Room's page.
- **Logs.** `grep TE_JMAP debug.log` (or `curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_JMAP"`):
  every pick writes `TE_JMAP pick <n> date=…`.
- **At load**, check `error.log` for lines naming `te_map_widgets.gui`, `journal_entry.gui` or
  `te_map_room_widget.gui`, `failed reading callback` above all: the engine drops a callback it can't read and says so
  only there, once.

## The checks (third pass)

| # | Check | How | What each answer means | If it's the bad answer |
|---|---|---|---|---|
| 1 | A pick repaints a paused map | Open the Map Room (Demographics header's map button). Pause. Click another map on the page. Then the same with the game running. | The page blinks (each pick closes and reopens it a quarter second later, `te_jmap_repaint`, the reopen by `OpenJournalEntryPanelDontToggle`, which no mod or vanilla `.gui` used before) and the map shows the new pick at once, paused or not. Say whether the blink is acceptable while running. | The page blinks but the old map stays: the reopen came before the pick's effect landed; lengthen the delay (0.5 s), or failing that say "at unpause" in the picks' tooltips. The page stays open with the old map and doesn't blink: the close hadn't landed when the reopen ran; the delay between them needs a second state. The page closes and stays closed: the reopen line failed; read `error.log` for a callback line naming `te_map_widgets.gui`. |
| 2 | The see-through page | On the Map Room's page, click the crossed-out eye at the header's top left, beside the back arrow (`te_je_see_through`). Pick a few maps. Click the eye again. Then fade it and close the page with X (or Escape), and reopen it. Try a vanilla entry's page too. | The page fades to 30% and the map shows through, and stays faded from pick to pick; the second click brings it back; after a close it reopens whole. Say whether 30% is right: the header still findable, the map clear enough. The faded page still takes clicks (expected). Known edge: leave a faded page by opening another panel (a state, say) and the next journal page you open from the journal opens faded; the map buttons and the X clear it. | Nothing fades: `alpha` bound on the panel's root doesn't work (vanilla binds it only on inner widgets); fade the page's contents instead, which leaves the frame opaque. No eye: read `error.log` for `journal_entry.gui`. |
| 3 | The Demographics button while paused | Pick Turmoil, close the page, pause, then click the Demographics header's map button. | The page opens on life expectancy at once: the pick and the open in one click are enough when the page starts closed. | Turmoil until unpause: give that button the same delayed reopen as the picks. |
| 4 | Banking's stripes | Whenever a country's cycle overheats (later in a game), with Banking's map up. | Yellow stripes on that country's states (`map_color_second`; vanilla's own entries draw stripes the same way). | No stripes: note it; the tooltip still names the crash risk. |

## The second pass's checks, answered

From #1417's list (its numbering), by the fourth session under Results:

| # | Question | Answer |
|---|---|---|
| 1 | One click opens the Map Room, picks on the page | Yes: a widget draws on a contextless page. |
| 2 | Picks on the page | Work, at the next tick, and the current pick's button draws pressed (`down` works). |
| 3 | Scope probe | Blue: `scope:journal_entry` isn't set in a contextless entry's map either. No white stripes over the player's states: the stripe condition was `owner ?= { is_player = yes }`, and vanilla's own entries stripe through the state's `owner`, so most likely `is_player` doesn't resolve in the paint. The probe is gone. |
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

## Not tested here

- Whether `map_color` takes a scope path (`value = owner.color`, prep C21): left out, since a field the engine rejects at
  load can drop the whole entry it sits in. Try it in an entry of its own.
- Multiplayer: two players share the Map Room's pick (a global variable). Whether that is acceptable is a design
  call; nothing tests it.
- `add_involved_country` on the Map Room (its own scripted buttons would unlock), and whether an involved country sees
  a contextless entry in its journal.

## When it's done

- Delete the `TE_JMAP pick` debug line in `te_jmap_set_selector` once check 1 is answered.
- Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1) in a PR of its own: it touches its events,
  `scripts/nightly_audit_select.py` and `scripts/image_pipeline/event_image_prompts.py`.
- Give the Banking and Demographics chapters a line each if a map grows beyond the introduction's paragraph
  (`docs/player_guide/01-introduction.md`, which covers the map buttons, the Map Room and the eye).
