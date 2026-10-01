# Timeline Extended Window GUI: Icons

The Timeline Extended window (`gui/te_systems_window.gui`) draws one icon of its own: its launcher under the sidebar. It is a placeholder, vanilla's Journal button art, until the mod's own is made. The window's tabs carry no icon, as vanilla's tabs and the mod's other system tabs don't (owner, 2026-09-30).

**Where it is set.** The icon is a literal `texture = "…"` line in each of the launcher's two `sidepanel_button_small`s, the closed one and the lit one, and both draw the same file. No script reads the path. `IconsTest` in `test_te_systems_window.py` holds both lines to the file below. It fails on any other texture in the window, on a texture this page doesn't list, and on a tab that sets an icon.

**Replacing the placeholder.** Make the launcher's art with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`), write it to the proposed path, then change the two `texture` lines and this page's row together. The sidebar's small buttons are 42 × 40; draw the art for vanilla's small sidebar icons, which the `sidepanel_button_small` frame surrounds.

## The launcher

| Where | Placeholder now | Proposed final path | Art brief |
|---|---|---|---|
| The sidebar button, closed and lit | `gfx/interface/main_hud/journal_btn.dds` (vanilla's Journal button) | `gfx/interface/main_hud/te_systems_window_btn.dds` | A small brass hourglass whose upper bulb holds a blue globe and whose lower bulb a rising rocket, gold line art on the sidebar buttons' dark ground, legible at 32 px |

The placeholder is the sidebar's own art, so the button's size and frame can be judged in game. It is the same picture as the Journal button three slots above it, so replace it before a release.
