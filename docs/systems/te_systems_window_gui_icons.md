# Timeline Extended Window GUI: Icons

The Timeline Extended window (`gui/te_systems_window.gui`) draws one icon of its own: its launcher under the sidebar, a painted brass hourglass from the icon pipeline (2026-10-07). It replaced a placeholder, vanilla's Journal button art. The window's tabs carry no icon, as vanilla's tabs and the mod's other system tabs don't (owner, 2026-09-30).

**Where it is set.** The icon is a literal `texture = "…"` line in each of the launcher's two `sidepanel_button_small`s, the closed one and the lit one, and both draw the same file. No script reads the path. `IconsTest` in `test_te_systems_window.py` holds both lines to the file below. It fails on any other texture in the window, on a texture this page doesn't list, and on a tab that sets an icon.

**Remaking it.** The art is the icon pipeline's `sidebar_button` category (`scripts/image_pipeline/icon_prompts.py`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`): change the entry, re-render, review, then `write`. The GUI needs no edit unless the file name changes. The sidebar's small buttons are 42 × 40, drawing vanilla's 76 px `main_hud/*_btn.dds` art, which the `sidepanel_button_small` frame surrounds.

## The launcher

| Where | Shows | File |
|---|---|---|
| The sidebar button, closed and lit | A small brass hourglass whose upper bulb holds a blue globe and whose lower bulb a rising silver rocket | `gfx/interface/main_hud/te_systems_window_btn.dds` |

The brief asked for gold line art. Vanilla's sidebar buttons are painted objects on transparency (a book, a globe on its stand, a stack of coins), so the launcher is painted too, at their size: 76 px, the object about three quarters of the side. The rocket is small at 40 px; the hourglass and the globe carry the picture. It replaced vanilla's Journal button art, the same picture as the Journal button three slots above it.
