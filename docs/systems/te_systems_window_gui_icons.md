# Timeline Extended Window GUI: Icons

The Timeline Extended window (`gui/te_systems_window.gui`) draws one icon of its own: its launcher under the sidebar, a painted brass hourglass from the icon pipeline (2026-10-07). It replaced a placeholder, vanilla's Journal button art. The window's tabs carry no icon, as vanilla's tabs and the mod's other system tabs don't (owner, 2026-09-30).

**Where it is set.** The icon is a literal `texture = "…"` line in each of the launcher's two `sidepanel_button_small`s, the closed one and the lit one, and both draw the same file. No script reads the path. `IconsTest` in `test_te_systems_window.py` holds both lines to the file below. It fails on any other texture in the window, on a texture this page doesn't list, and on a tab that sets an icon.

**Remaking it.** The art is the icon pipeline's `sidebar_button` category (`scripts/image_pipeline/icon_prompts.py`, spec `docs/superpowers/archive/specs/2026-09-26-icon-pipeline-design.md`): change the entry, re-render, review, then `write`. The GUI needs no edit unless the file name changes. The sidebar's small buttons are 42 × 40, drawing vanilla's 76 px `main_hud/*_btn.dds` art, which the `sidepanel_button_small` frame surrounds.

## The launcher

| Where | Shows | File |
|---|---|---|
| The sidebar button, closed and lit | A small brass hourglass whose upper bulb holds a blue globe and whose lower bulb a rising silver rocket | `gfx/interface/main_hud/te_systems_window_btn.dds` |

The brief asked for gold line art. Vanilla's sidebar buttons are painted objects on transparency (a book, a globe on its stand, a stack of coins), so the launcher is painted too, at their size: 76 px, the object about three quarters of the side. The rocket is small at 40 px; the hourglass and the globe carry the picture. It replaced vanilla's Journal button art, the same picture as the Journal button three slots above it.

## Placeholders

<!-- Help pages (charts-help-national-info plan, PR H1) -->
The "?" that opens a system's Help page (style guide rule 1) sits at the right of each system tab's header, in this
window and in the vanilla panels' tabs. Its art is a placeholder (style guide rule 10): vanilla's own gold question
mark, which the base game ships in `button_icons/unused/` and draws nowhere. The plan named the encyclopedia button's
book, but a book reads as opening the encyclopedia. `test_te_help_pages.py`'s `ShellTest` holds the path.

| Where | Today | Final art (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| The "?" in each system tab's header (`te_help_button`, `gui/te_system_tab_widgets.gui`) | `gfx/interface/buttons/button_icons/unused/help.dds`, vanilla's | A question mark on a parchment disc, in the gold line art of vanilla's round-button icons | `gfx/interface/buttons/button_icons/te_help.dds` |
<!-- end Help pages -->

## Candidates for an icon later

| Where | Today | Note |
|---|---|---|
| The width toggle, at the top right of each frame (`te_systems_window_toggle`, 2026-11-02) | A text button: "Full Screen" in the side panel, "Side Panel" full screen | Text until there is art (style guide rule 10, placeholder art is fine). An icon would need two pictures, expand and collapse; the tooltips stay as they are. |

The full-screen frame (`te_fullscreen_block_window`) draws vanilla's own art: its top filler, fades and borders, copied with the type from vanilla's `block_windows.gui`. They are vanilla files, so this page doesn't list them (`IconsTest` holds them to the vanilla type's).

## Placeholders: the history charts' open button (charts PR C2, 2026-11-02)

Every panel history chart has a round button beside its title that opens the chart alone at full size (`te_chart_open_button` in `gui/journal_entry_widgets/te_history_chart.gui`, filled into each chart's panel wrapper by `scripts/generators/gen_te_history_charts.py`). It shows in every host the chart does, the Timeline Extended window and the vanilla panels' tabs alike. Its art is a placeholder, a vanilla button icon (style guide rule 10). `OpenButtonTest` in `test_te_history_charts.py` holds the path in the type to this row.

| Where | Placeholder | Final art (icon pipeline subject) | Proposed path |
|---|---|---|---|
| Beside each history chart's title (`te_chart_open_button`, 24 × 24, `button_icon_round`) | `gfx/interface/buttons/button_icons/areacharts.dds`, vanilla's area-chart toggle from the Population panel | Two arrows pointing out from a corner, one to the top right and one to the bottom left, over a faint small bar chart, in the gold line style of vanilla's round button icons | `gfx/interface/buttons/button_icons/te_chart_open.dds` |
