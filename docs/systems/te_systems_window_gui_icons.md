# Timeline Extended Window GUI: Icons

The Timeline Extended window (`gui/te_systems_window.gui`) draws four icons of its own: its launcher under the sidebar, and one on each of its three tabs. The tabs reuse each system's own art from PR #586. The launcher is a placeholder: vanilla's Journal button art, until the mod's own is made.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/te_systems_window.gui`. The launcher's is in its two `sidepanel_button_small`s, the closed one and the lit one, and both draw the same file. Each tab's is in its `*_button_icon` blockoverride in the window's `tab_buttons`, drawn at 24 px left of the tab's name. No script reads the paths. `IconsTest` in `test_te_systems_window.py` holds each place to its file below, and fails on a texture this page doesn't list.

**Replacing the placeholder.** Make the launcher's art with the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md`), write it to the proposed path, then change the two `texture` lines and this page's row together. The sidebar's small buttons are 42 × 40; draw the art for vanilla's small sidebar icons, which the `sidepanel_button_small` frame surrounds.

## The launcher

| Where | Placeholder now | Proposed final path | Art brief |
|---|---|---|---|
| The sidebar button, closed and lit | `gfx/interface/main_hud/journal_btn.dds` (vanilla's Journal button) | `gfx/interface/main_hud/te_systems_window_btn.dds` | A small brass hourglass whose upper bulb holds a blue globe and whose lower bulb a rising rocket, gold line art on the sidebar buttons' dark ground, legible at 32 px |

The placeholder is the sidebar's own art, so the button's size and frame can be judged in game. It is the same picture as the Journal button three slots above it, so replace it before a release.

## The tabs

| Tab | Shows | File | From |
|---|---|---|---|
| Space Race | the rocket rising on a short flame | `gfx/interface/icons/space_race_icons/state_standard.dds` | the Standard approach cell (`space_race_gui_icons.md`) |
| Colonies | the globe, a thin gold tie | `gfx/interface/icons/colonial_empire_icons/band_stable.dds` | the Stable band (`colonial_empire_gui_icons.md`) |
| Monuments | the stele with a gold laurel wreath hung on its panel | `gfx/interface/icons/gm_icons/status_upheld.dds` | the Upheld status (`grand_monuments_gui_icons.md`) |
