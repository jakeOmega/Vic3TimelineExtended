# Journal entry map modes: play-test checklist

The first pass at vanilla 1.15's journal entry maps (`docs/systems/mod_systems/journal_map_modes.md`, issue #1404) was
built before anyone had seen one work in game. This list is what the play-test should settle, most important first.
Record each answer here and in `docs/audits/vanilla_1_15_prep.md` § 2 under C6 (or C21), and put each engine fact in
`docs/guides/scripting_best_practices.md` § "Journal Entry Map Modes".

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work", from the full checkout (the branch adds
  `gfx/map/map_modes/te_map_modes.txt`, so a sparse worktree's deploy would also delete textures).
- **Launch with `-debug_mode`**, as for the console's `event` command: the test strip shows only in debug mode. It sits
  on the Demographics tab (Population panel, last tab), above the sections, under a "Map tests" heading. Demographics on
  Full or Display only, which is the default.
- **Logs.** `grep TE_JMAP debug.log` (or `curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_JMAP"`):
  the add, request and close buttons and the entry's activation each write one line, dated, which times check 3.
- **At load**, check `debug.log` for errors naming `te_journal_maps.txt`, `te_journal_map_colors.txt`,
  `te_map_modes.txt` or `je_banking.txt`: a rejected field can drop a whole entry. If the game won't start, delete
  `gfx/map/map_modes/te_map_modes.txt` in the deploy folder first.
- **Look at the art too** (checks 9 and 10): the Demographics maps and the Banking map were drawn to be looked at, and
  the palettes are a first guess.

## The checks

| # | Check | How | What each answer means | If it's the bad answer |
|---|---|---|---|---|
| 1 | Does opening an entry's page paint the map? | Click the map button in the Demographics header (left of "?"): it adds the Map Room. Click it again: it opens the Map Room on Life Expectancy. Then open Banking's page (the Banking tab's map button, or the journal). | The map recolors while the page is open: the engine switches to the entry's map on opening, as assumed. Nothing changes: something else turns it on. | Look for a map mode button on the journal entry page or in the journal list; note what does turn it on. Every button in this branch opens a page, so they all need rewiring. |
| 2 | Several maps on one entry | In the Map Room, click Turmoil, Literacy, then the three Demographics maps. | The map changes at each click: a selector works, and one entry can host many maps. It changes only on reopening the page: it works, but the buttons should reopen the page. | It never changes: `map_color` reads the selector once. Fall back to one entry per map, each hidden until its button (the Map Room's pattern). |
| 3 | The scope probe: can the map read the player's country? | Pick Scope Probe. | **Green**: `scope:journal_entry` and its owner both resolve inside `map_color`, so a map's pick can live on the player's country (safe in multiplayer). **Yellow**: the entry resolves, its owner doesn't. **Blue**: neither; only the global variable got through, and every player shares one pick. White stripes over the player's own states: `map_color_second` and the state's `owner` link work. | Blue: keep the global, and note in the system doc that two players in one game share the Map Room's pick. |
| 4 | Hidden until wanted, by the activation triggers | Close the Map Room (its Close button, or the strip's Close). Then click the strip's Request. Note the in-game date of the `TE_JMAP host requested` and `TE_JMAP host activated` lines. Try once paused, once running. | Same day, even paused: activation is checked at once, and the plain "set a variable" route needs no `add_journal_entry`. Days later: activation runs on a schedule; buttons must use `add_journal_entry`. Never while paused: the same, and say so in the button's tooltip. | Keep `add_journal_entry` on every button (already the Demographics button's route). |
| 5 | Closing hides it again | After Close, how long until the Map Room leaves the journal, and does the map go back to normal? | Leaves at once or within days: `can_deactivate` with the variable removed is a working "remove" (1.15 has no `remove_journal_entry`). Never leaves: deactivation doesn't apply to an entry added by `add_journal_entry`. | The entry needs an outcome that concludes it instead, which leaves it in the concluded tab; or keep it and let Close only clear the pick. |
| 6 | One click: add and open | Close the Map Room; wait until it leaves the journal. Click the strip's Add + Open once. First check that the load logged no `failed reading callback` for `te_map_widgets.gui` (the first build's did: see Results). | The page opens on the first click: the scripted GUI's effect lands before the second `onclick` runs, and the Demographics button can be one button. Only on the second click: as expected; the two-state button stays. | Error or crash: the call with no entry is unsafe; keep it out of player-facing buttons (it already is). A load error at `te_map_widgets.gui:103` again: `.AccessSelf` is the wrong ending too; try `AccessPlayerJournalEntry('je_te_map_host').AccessSelf`. |
| 7 | An entry outside every journal | Click the strip's Hidden Entry. | A page opens and the map turns **magenta**: an entry no country is involved in can host a map and be opened by a button, so a map never needs to show in the journal at all. Nothing opens: `GetPlayerJournalEntry` doesn't find an entry the player isn't involved in (the button stays inert). | The Map Room's hide-until-wanted pattern (checks 4–5) is the way to keep a map out of the journal. |
| 8 | The map with the page closed | (a) Open the Map Room, then close its page: does the map stay? (b) Again with the lens toolbar's lock on (the padlock by the map mode name). (c) With no page open, pick **Journal Entry Map (Test)** from the map mode dropdown. (d) Hover the strip's two hover buttons, with no page open and with the Map Room open. | (a)/(b) The map stays: a journal map can be left up. (c) It paints: the listed copy works, and the colors say whose map it shows (Map Room colors, Banking's phases, or magenta for the hidden world entry), which tells how the engine picks the entry. Nothing painted: it needs a page open. (d) Same, for a hover preview. | If none of (a)–(d) holds, a map exists only while its page is open; say so in each map button's tooltip. |
| 9 | Banking map, and whether a tab opens it | Open the Budget panel's Banking tab: does the map change? Then its header's map button. | The tab alone paints it: any panel showing an entry through `GetPlayerJournalEntry` triggers its map (prep C6). Only the button: as assumed. Look: every country in its phase's color, yellow stripes on the overheating; grey where the cycle hasn't started (early game, most of the world). | — |
| 10 | Look and feel | With each Demographics map up, judge the palette, the grey "no census" states, borders, and the hover text (state name and figure). The same for Banking. | Notes for the next pass: colors to change, a legend wanted (vanilla draws none for journal maps, as far as known), text to add. | — |
| 11 | How water, wasteland, unowned and decentralized land draw | Look at them on any map. | Recorded for the system doc. Unowned land has no `owner`, so Banking leaves it unpainted. | — |
| 12 | How often the map redraws | Pick Refresh Tick, leave the page open, run the game a few weeks. | The shade steps each week: `map_color` is re-evaluated as the game runs, and live data shows live. Steps only on reopening: it is evaluated on opening; stale maps until reopened, which suits yearly census data. | — |
| 13 | Cost | With a Demographics map up, run at top speed for a year and compare with the map off. | No visible slowdown: per-state variable reads are cheap enough. A slowdown: note it; maps may need to read fewer branches. | Fewer branches per map (move each map's ladder first). |
| 14 | A button on a contextless page | Open the hidden entry (the strip's Hidden Entry), click its **Probe: Run a Button Here**, then unpause for a tick. | The map turns green and `debug.log` has `TE_JMAP world button ran` with a scope dump: a button on a page no country is involved in runs, and the dump says what its root is (the player's country, or none). The next pass's Map Room can then be a contextless entry with its own pick buttons. Nothing changes and no line: such a page's buttons don't run. | Picks move to GUI buttons that call scripted GUIs (with the player as root), mounted on the page or beside the map button. |

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
  `GetBuildingType('building_shipyard').Self` takes (`construction_panel.gui`). Check 6 tests that form too.
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
- **Add + Open (check 6): the add takes about a week, and the page never opened.** It never could on this build: its
  open callback was dropped at load (above). But the week answers check 6 whatever the form: an entry `add_journal_entry`
  adds isn't in the journal until about a week later, so no click can add the Map Room and open it. The Demographics
  button stays two-state, and its tooltip now says the Map Room appears within about a week. The log fits: 25 `host
  added` lines, 21 of them in 12 seconds (each logs only while `has_journal_entry` is false), and the entry's
  `immediate` logged twice. For the next pass, check 7 removes the wait: a contextless entry like the hidden one exists
  from the start and opens at the first click, so the Map Room can be one, with no add, close or two-state button.
- The `TE_JMAP` lines printed no date, so checks 4–5 couldn't be timed from the log: at 16:51 four adds were followed by
  the activation 29 seconds later, and at 16:54 21 adds had no activation before the close, but in game days that could
  mean anything. All four lines now print `date=`, so 4–5 need a rerun.

## Not tested here

- Whether `map_color` takes a scope path (`value = owner.color`, prep C21): left out, since a field the engine rejects at
  load can drop the whole entry it sits in. Try it in its own entry once checks 1–2 pass.
- Whether an **inactive but shown** entry (`is_shown_when_inactive` true, `possible` false) paints its map when its page
  is opened (prep C6). Nothing in this branch is shown inactive.
- Multiplayer: two players picking different Map Room maps (only matters if check 3 comes back blue).

## When it's done

- Delete the test pieces: `te_jmap_test_strip` and its mount (`tab_before_gate` in `te_demographics_layout.gui`), the
  `te_jmap_strip_*` loc keys, the Scope Probe and Refresh Tick buttons and branches (selector 6 and 7, their colors and
  tooltips), the world probe button `te_jmap_world_probe` and its green, `je_te_map_hidden_world` (keep it if check 7 makes it the better pattern), and
  `gfx/map/map_modes/te_map_modes.txt` unless check 8(c) makes it worth keeping.
- Retire the Cartographic Survey (`te_map_mode_*`, prep § 4.1).
- Give the player guide its lines: the Demographics and Banking chapters' map buttons, and the Map Room.
