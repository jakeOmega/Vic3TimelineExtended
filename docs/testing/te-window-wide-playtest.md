# Timeline Extended window, wide mode: play-test checklist

What the next play-test should look at in the Timeline Extended window's full-screen mode (spec
`docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md` § 10). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the
game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that
fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The sidebar button under Map List opens the window. Its "Full Screen" button, at the top right
  above the tabs, switches it to the full-screen frame; "Side Panel" switches back.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `te_systems_window` and `te_fullscreen_block_window`.

## The side panel looks as before (PR A, the registry, 2026-11-02)

The strip, the selection templates and the tabs' mounts are generated now, and each tab's content is a body type. The
offline checks found the widget tree unchanged, so nothing should look different.

| Check | Expect | If it fails |
|---|---|---|
| **Each tab, side panel.** Open the window and visit Nation, Space Race, Grand Monuments, Colonial Empire and Seabed. | As before 2026-11-02: one strip of five, the same headers, sections, spacing and Open Journal Entry buttons, each tab's content centered in the panel. | A shift or a changed gap: compare the tab's body type with `te_systems_window.gui` before the registry (`git show 8e44d921a:gui/te_systems_window.gui`). |
| **The Space Race with several milestones running.** | Each running milestone under its own header, then Space Powers and Orbit, then How the Space Race Works. | A missing milestone or header: check `te_sr_window_milestones` in `gui/te_systems_window_generated.gui`. |

## The full-screen frame and the toggle (PR B, 2026-11-02)

The frame is vanilla's `fullscreen_block_window` with Back and Close changed. It sits at the window root's origin, as
vanilla's full-screen panels do, and draws its own top filler under the top bar. The window's layer
(`layer_ingame_menu`) is below the HUD's, so the HUD draws over it. Until the wide layouts land (PR D), each tab shows
its single 520 column centered in a 1,620 wide column.

| Check | Expect | If it fails |
|---|---|---|
| **1. The top bar and the outliner.** Switch to Full Screen. | The real top bar draws over the frame's top filler, with no second top-bar band below it, and the frame's title and buttons sit below the top bar. The outliner on the right draws over the frame's right edge. | A second band, or the title hidden under the top bar: inset the wide frame under the top bar (a `margin_widget` with `margin_top = 85`, the plan's first idea). The outliner covering content: widen the frame's `content_margin_right` block to leave its column free, or raise the window's layer. |
| **2. The sidebar and the launcher.** In full screen, hover and click the sidebar's buttons and the window's launcher. | The sidebar draws over the frame's left edge and stays usable; the launcher closes the window. | The sidebar hidden or unclickable: the frame's `clickthrough_blocker` covers it; leave its column free with the content's left margin. |
| **3. Width.** At 1600 × 900, then at a larger UI scale. | The content scrolls sideways where it is wider than the screen, and nothing clips. Until PR D, the sideways scroll bar can show with a single 520 column centered: that is expected. | Clipping: the frame's scroll area isn't scrolling sideways; compare with the Census Data window, which uses the same `fullscreen_scrollarea`. |
| **4. Closing it.** In full screen, press Escape; reopen, click Back; reopen, click Close; reopen, open the Budget panel; reopen, open the ledger. | Each closes the window. Reopening it shows the full-screen frame again (the width is remembered for the session). | One doesn't close it: Back and Close clear `com_open_window` (`test_te_fullscreen_frame.py`); a panel or the ledger opening clears it from the launcher's root. |
| **5. The toggle keeps the tab.** Choose Grand Monuments, switch to Full Screen, then back. | Grand Monuments stays chosen in both frames. | The tab resets: something writes `te_systems_window_tab` on the switch (`test_the_toggle_keeps_the_tab`). |
| **6. Sound.** Switch to Full Screen with the game running. | The world's sound drops, as in vanilla's full-screen panels (the frame's `snapshot:/Dynamic/mute_world_80`), and returns on Side Panel or close. | The sound stays down after closing: the snapshot isn't released by the frame's `_hide`; note it. |
