# Buildings panel performance: the USA of 2050

Why the Buildings panel crawls late in a large game, measured on 2026-11-27, and the fix made on the same branch.

**The ask (owner, 2026-11-27):** "In late game (at least in a large country), the buildings panel can be very
slow/laggy (e.g. it can take seconds for a scroll to take effect)."

## Summary

- **How slow.** With the game paused and the sidebar's Buildings panel open, the 2050 USA drew a frame in **341 ms**
  (2.9 frames a second), against 9 ms with nothing open. With Food Industries expanded, 402 ms. A scroll lands a
  frame or more later, so each wheel notch takes a third of a second or more to show, and in one test the list
  ended three rows short of where the same twelve notches took the fixed panel. The full-screen Building Registry,
  grouped by type, took 50 ms.
- **Why.** The panel lists one row per building type the country has (201 for this USA) in a `flowcontainer`, and
  the engine works out every child of a flowcontainer every frame, on screen or not. Nine rows are on screen. Each
  row asks the engine for its productivity span, its buttons' states and, for every production method group,
  whether all its buildings share a method, how many methods are open and whether one is new: questions about the
  country's buildings of that type, 9,525 buildings in all (that the answers are worked out over them is read from
  the stack samples, finding 1).
- **What the mod adds.** Vanilla draws a row's groups in a `fixedgridbox`, which skips items out of view. The mod
  made that strip a horizontal `flowcontainer` in a scroll area (PR #689, `gui_modding_guide.md` gotcha #38),
  because its buildings carry up to seven groups and vanilla's grid ran the fifth one under the row's buttons. That
  strip was 225 of the 341 ms; vanilla's grid, in the same row, about 34. The rest of the row is vanilla's own cost:
  vanilla's row type in this save drew at 141 ms.
- **What it is not.** Script: about 3% of the frame. The strip's `visible` filter for the maintenance groups: it
  costs nothing measurable. The scroll area around the strip: likewise.
- **The fix** (this branch, no change a player sees): the fixed-size top of each row sits in a one-item
  `fixedgridbox`, so a row out of view is skipped, strip and all; the Registry's type headers likewise; the panel's
  list updates at most ten times a second, as vanilla already has the Registry's; and the hidden list vanilla uses
  to fill the rows asks for one building instead of making an empty widget for each of thousands. **341 → 18 ms**
  a frame with the panel open (56 frames a second), 43 frames a second while scrolling, and the Registry 50 → 16.
  Checked in game: rows, scrolling, expanding a type, a filter, the method menu, the Registry's expand and its
  ungrouped view.

## The save and the method

- **Save:** `te_qa_copy_iua2050_20261126.v3` (6 February 2050, the Imperial Union of America, tag `USA`), the
  copy of the owner's save that `late_game_performance_2050.md` used, on the owner's playset, 1.15.2. The USA has
  180 states, 9,525 buildings in them and 201 building types (read from the save: `save_world_report.py`'s
  building records joined with `save_country_probe.py`'s state owners).
- **Sessions:** two `game_qa` sessions (runs `20261127T211539Z` and `20261127T215541Z`), 3840x2160 at UI scale 1.5,
  game paused, `start --as USA --save <copy> --playset current --add-mod <variant>`. The variant held a see-through
  console and the `.gui` files under test, so each could be swapped while the game ran.
- **Opening the panels:** `view panel:building_browser` and `panel:compact_building_browser` open nothing. A scratch
  type shown by `gui-show` whose `state`'s `on_start` calls `InformationPanelBar.OpenCompactBuildingBrowserPanelCycleFilters(
  GetPlayer.Self, '|is_development|is_rural|is_urban' )` (what the sidebar button calls) or
  `InformationPanelBar.OpenBuildingBrowserPanel( GetPlayer.Self )` opened them.
- **A frame's cost:** the frames the script profiler counts between `Script.Profiling.Start` and `Stop` (its reply:
  "Captured … over 18.1 s (55 frames …)"), over about 17 s. Finer than debug mode's FPS counter, which prints whole
  frames a second. Load average under 0.65 for every reading. In the first session the profiler's window stayed open
  over the middle of the screen for all readings after the first two (its close button does not answer a click);
  the second session never opened it, and its figures match the first's (shipped 341 against 331–336).
- **A/B of one part of a row:** the variant's `building_browser_panel.gui` pointed the compact panel's row instance at
  a test type appended to the same file (a copy of the mod's row or vanilla's with one part cut), the panel was
  closed and opened again so the new widgets were built, then measured. The generator, `make_variants.py`, and every
  variant are in the data folder.
- **Where the main thread goes:** `stacksample_deep.py` and `name_rvas.py` from the 2026-11-23 tools, 3,500 samples
  at 5 ms on the main thread with the shipped panel open.
- **Data:** `/mnt/d/vic3te-data/bldg-panel-2026-11-27/` (`results.tsv` holds every reading; `alt/` the variants;
  `apply_fix.py` writes this branch's change; `measure.sh`, `swap.sh`, `swap2.sh`, `scrolltest.sh`, `sample.sh`;
  `runs/compact_mod/` the stack samples; `usa_building_types.txt` the count).

## Findings

### 1. The panel's cost is the rows, every row, every frame

The compact panel, All Buildings, every type collapsed (session 1):

| The row | ms a frame |
|---|---|
| As shipped | 331, 336 (a copy of the type, as a control) |
| The row draws nothing (a 10 x 10 widget) | 16 |
| The row draws nothing, and the hidden list is gone | 8 |
| The row is the type's name only | 17 |

Nothing open: 9 ms (8 to 9 in both sessions; the game draws at most 120 frames a second here). So the rows are about
315 of the 331 ms. Rows the player cannot see are paid for like the nine on screen: the list is a `flowcontainer`.

The main thread ran at 99% of a core. In the stack samples the data system's function-call routine
(`pdx_datasystem/pdx_data_call…`, "No function for call") is on the near stack in 43% of samples, and the
leaves are game-state accessors (functions referencing `NGameState::GameStateAccess` asserts, 40%). Among named
callers are the size text of a filtered type (`FILTERED_BUILDING_TYPE_SIZE_DESC_…`, 2.7%) and the productivity span
(`PRODUCTIVITY_SPAN_FORMAT`, 4.1%). So the time is the GUI asking the engine questions about buildings, not drawing.

### 2. The mod's PM strip is two thirds of it; the container, not the filter or the scroll area

Cutting parts from the mod's row (session 1):

| The row | ms a frame |
|---|---|
| Without its strip of production method groups | 107 |
| Without its productivity span | 324 |
| Without its action buttons (nationalize, subsidize, auto-expand, expand) | 288 |
| Vanilla's row type, its `fixedgridbox` strip included | 141 |
| The mod's strip without its `visible` filter (maintenance groups shown) | 385 |
| Vanilla's `fixedgridbox` strip with the mod's filter | 136 |
| The mod's strip without the scroll area round it | 334 |

The strip costs about 225 ms in the mod's form and about 34 in vanilla's, for the same groups. The seven string
comparisons of the filter, run for every group of every row, are not it (vanilla's grid with the filter: 136 against
141), nor is the scroll area (334 without it). The difference is the container: a `fixedgridbox` leaves out of the
frame what is scrolled out of view, a `flowcontainer` does not. This is inferred from these figures, not from the
engine's code. It fits vanilla's own note at the head of `building_browser_panel.gui`, "The spreadsheet cells are a
fixed size in order to be optimized", and finding 3 tests it directly.

The span and the buttons are vanilla's and modest (about 10 and 45 ms). Vanilla's row with no strip at all would be
about 90 ms in this save, so vanilla's own panel is slow here too (141 ms with its strip), only less so.

### 3. A one-item `fixedgridbox` round a row's top makes an unseen row free

Wrapping the row's top (its 554 x 95 header: icon, name, span, strip, buttons) in a `fixedgridbox` with one item
(`DataModelFirst(<the type's production method groups>, '(int32)1')`, a list that always has one element), and
leaving the expanded list of buildings under it as it was:

| | ms a frame |
|---|---|
| The mod's row, wrapped (session 1) | 59, 61 |
| Vanilla's row, wrapped | 66 |
| The mod's row, wrapped, and the list's `max_update_rate = 10` | 20 |
| The same, and the hidden list asked for its first building only (this branch) | 18 (session 2) |

Once unseen rows are skipped, which strip a row uses no longer matters (59 against 66). The rate limit is
vanilla's own device: the Registry's content has `max_update_rate = 10` and the compact panel's has none. It means
the panel's figures refresh at most ten times a second, which a player does not see.

The hidden list is vanilla's: "Remove this, currently needed to make sure GetBuildingBrowserBuildingTypeItems is
being populated", a `flowcontainer` over `BuildingBrowserPanel.GetSortedAndFilteredBuildings` with an empty widget
per building, about 9,500 here. Asked for its first building only, the list still fills: the rows were there with
the All filter and refilled when the Group filter was set to rural buildings. It saved about 6 ms (29 → 23 ms with
Food Industries expanded).

### 4. Expanded types, scrolling and the Registry

| | Shipped | This branch |
|---|---|---|
| Compact panel, All Buildings (session 2) | 341 | 18 |
| Compact panel, rural buildings | 177 | 19 |
| Compact panel, Food Industries expanded (a row per state; session 1, the fix with the wrapper's one item taken from the type's buildings) | 402 | 23 |
| Compact panel while the wheel scrolls it (frames a second; four times three notches) | about 3 | 43 (session 2), 13 (session 1, wrapper alone) |
| Building Registry, grouped by type | 50 (42 in session 1) | 16 (11 in session 1) |
| Building Registry, a type expanded | | 15 |
| Building Registry, not grouped | | 15 |

The Registry's ungrouped list was already a `fixedgridbox` in vanilla; this branch leaves it alone. Its grouped
view is a `flowcontainer` of types, each a header and the type's buildings (a `fixedgridbox`, already skipped when
out of view), so the headers got the same wrapper as the compact rows, at the Registry's 80-unit header height.

Scrolling the shipped panel, the twelve wheel notches left it three rows short of where the same notches took the
wrapped one: at three frames a second some of the scroll was lost, which is the owner's "seconds for a scroll to
take effect".

### 5. Script is a small part

The script profiler put about 0.6 s of script into an 18 s capture with the shipped compact panel open (3%), and
0.47 s into 17.4 s with the Registry open. The largest single entry was the seabed licence gate,
`can_build_government` in `03_zz_te_mines.txt` (`te_seabed_gate`), at about 13 ms a second; the market site's,
Resource Transition's and other buildings' `can_build_*` blocks followed. Probably the row's expand (+) button,
whose `visible` asks `BuildingType.IsBuildable` and `IsExpandable` (an inference). Not worth a change at this size.

**The profiler's call graph adds up captures.** `Script.Profiling.Start` clears the header (length, frames) but not
the call graph, which kept growing over the session's twenty captures until its `—` button cleared it. The totals
in the first view after many captures were the session's, not the last capture's.

## Changes made on this branch

- `gui/production_methods.gui`, `buildings_production_method_item` (the compact panel's row; also the military
  formation panel's naval administration item): the `### TOP ITEM` widget in a one-item `fixedgridbox`
  (`addcolumn = @panel_width_plus_14`, `addrow = 95`). The expanded list of buildings stays outside it.
- `gui/building_browser_panel.gui`:
  - `compact_building_browser_panel`: `max_update_rate = 10` on the content's list, and the hidden list over
    `DataModelFirst(BuildingBrowserPanel.GetSortedAndFilteredBuildings, '(int32)1')`.
  - `building_browser_building_type_item` (the Registry's grouped rows): the header `container` in a one-item
    `fixedgridbox` (`addcolumn = @spreadsheet_width`, `addrow = @spreadsheet_header_height`).
- `test_buildings_panel_culling.py` fails if a vanilla re-merge drops any of it (a re-merge once dropped the
  strip's scroll area, gotcha #38).

The one item is the building type's first production method group: every building type has one, and nothing in the
wrapped part reads the item's context (the strip's groups come from its own datamodel). The strips keep the mod's
scrolling form, which `test_pm_group_strips.py` holds.

## Open

- **A type's expanded list in the compact panel** is a list of every state's building of that type, each with the
  mod's strip, all worked out every frame. With the fix, Food Industries expanded (about 180 rows) cost 5 to 9 ms
  more than collapsed; not worth a change yet. Its rows vary in height, so the one-item wrapper would need a fixed
  row first.
- **Unpaused play** was not measured: the readings are of a paused game, where the GUI is all the main thread does.
- **Hovers** (the building type's tooltip, the method menu's) were opened and look right but were not timed.
- **A small country, or an early game,** was not measured; the cost follows the number of building types listed and
  the buildings behind each, so it should never have been large there.
