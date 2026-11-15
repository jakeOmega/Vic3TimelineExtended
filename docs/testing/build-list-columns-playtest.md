# Construction list columns: play-test list

The column that shows productivity in the list of states for a new building shows pollution for a National Park and
crowding for Public Housing (`gui/00_te_build_list_columns.gui`, `docs/systems/mod_systems/state_and_nation_panels.md`
§ Construction List Columns; a Workshop request, 2026-11-15). It passed the offline gate only:
`test_build_list_columns.py`, the GUI lint and the GUI reference audit. In-game checks don't gate a merge (CLAUDE.md,
"In-game checks"); work through these the next time the game is up. They take a few minutes.

## How to run

- **A save:** any mid- or late-game country with Urban Planning (Public Housing) and a polluted state. The France test
  game serves.
- **Where to look:** the construction box (the hammer), pick a building, and read the list of states it opens. The list
  has two layouts, condensed and full; the Condensed / Full button among its filters switches them. Check both.
- **Log:** `gui.log` should have three lines `Type '<name>' already registered at 'gui/00_te_build_list_columns.gui:<n>'`,
  one each for `productivity_or_other_information`, `construction_headers_condensed` and `construction_headers_full`.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | The redefinition wins | The three `gui.log` lines above, naming `map_list_panel.gui` as the file whose definition was dropped. | Vanilla's definition won: the list looks as before. Report it; the only other route is a whole-file copy of `map_list_panel.gui`, which is the owner's call. |
| 2 | National Park | Pick National Park. The column shows each state's pollution impact in red (`12.3%`; `0.0%` where there is none), the same figure as the map's Pollution list, under a pollution icon. Hovering a cell shows vanilla's pollution tooltip (impact, trend, generated pollution); hovering the header names the column and says it can't be sorted. | A blank cell: `State` isn't in the cell's datacontext, so read the figure through `Building.GetState` instead. A raw key: a loc file didn't deploy. |
| 3 | Public Housing | Pick Public Housing. The column shows the crowding pull penalty: `0%` in an uncrowded state, a red percentage in a crowded one that matches the Pull Penalty row of that state's Migration Crowding tile. Hovering a cell lists the penalty, population and threshold; the header has a population icon. | A figure that differs from the tile's: the tile and the cell read the same script value, so look for a datacontext that isn't the listed state. |
| 4 | Zero's color | In check 3, `0%` is not red. | Cosmetic: if `\|%0-` colors zero red, switch the cell to two textboxes (red above zero, plain at zero). |
| 5 | Sorting | Clicking either new header does nothing, and the list keeps its order. Clicking vanilla's other headers still sorts. | A crash or a reordering on click: report it. The headers have no `onclick`, so neither is expected. |
| 6 | Vanilla unchanged | Government Administration still shows Tax under its own header; Trade Center its trade capacity; one factory (a Textile Mill) its productivity under the productivity icon, and sorting by it still works; one military building (Barracks) its units columns. | A building showing two figures in one slot, or none: a `visible` test in the file is wrong; `test_build_list_columns.py` should have caught it, so add the case there. |
| 7 | Frame rate | With Public Housing's list open on a large country (fifty or more states), the game is no slower than with a factory's list open. Each row reads one script value; the hover reads three more. | If it is slower: show the penalty the yearly crowding refresh stored instead (`migration_crowding_mult_applied` × 0.1, a variable read, no script value). |
| 8 | With CMF | Optional, if a playset with the Community Mod Framework is at hand: with it enabled, checks 2 and 3 still hold. CMF redefines the list's row but keeps instancing the cell. | The column shows productivity: CMF's row no longer uses the cell type; note it in the GUI guide's compatibility notes. |
