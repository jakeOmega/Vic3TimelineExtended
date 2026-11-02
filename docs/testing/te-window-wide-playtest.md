# Timeline Extended window, wide mode: play-test checklist

What the next play-test should look at in the Timeline Extended window's full-screen mode (spec
`docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md` § 10). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the
game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that
fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The sidebar button under Map List opens the window. Its "Full Screen" button, at the top right
  above the tabs, switches it to the full-screen frame; "Side Panel", at the top left above the tabs there, switches
  back.
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
(`layer_ingame_menu`) is below the HUD's, so the HUD draws over it. Vanilla hides much of the HUD while its own
full-screen panels are open (the `fullscreen_hide` and `half_and_fullscreen_hide` templates in `block_windows.gui`,
which read `InformationPanelBar.IsPanelOpen`); a scripted window never trips them, so those parts stay up over this
frame. Until the wide layouts land (PR D), each tab shows its single 520 column centered in a 1,620 wide column.

| Check | Expect | If it fails |
|---|---|---|
| **1. The top bar.** Switch to Full Screen. | The real top bar draws over the frame's top filler, with no second top-bar band below it, and the frame's title, Back and Close sit below the top bar. | A second band, or the title hidden under the top bar: inset the wide frame under the top bar (a `margin_widget` with `margin_top = 85`, the plan's first idea) **and** drop the frame's 78 px top filler in the generator's `FRAME_CHANGES` (it isn't in a block, so an inset alone draws it as a second band at 85). |
| **2. The HUD over the frame.** In full screen with the outliner open, then while paused. | Expected, and to judge: the outliner over the frame's right 360 px from just under the top bar; the construction info box under the top bar's right end, over most of Close; the pause button (screen center, 340 above the middle) over the strips' middle at 1080p; the lens toolbar and the notifications along the bottom. Note what each hides and whether it gets in the way. | The outliner over content: widen the frame's `content_margin_right` block (about 410 keeps its column free; the 1,620 column then scrolls sideways at 1080p). Close covered: move it left of the construction box with the frame's `close_button_position` block (`position = { -420 15 }`). To hide the HUD as vanilla does, redefine vanilla's three templates in a `00_` file so they also read `te_systems_window_wide`: untested for templates, and the owner's compat call. |
| **3. Side Panel stays reachable.** In full screen, with the outliner open, click Side Panel. | It sits at the left above the tabs, clear of the outliner, and returns the window to the side panel. | Covered: by what (the top bar's dropdowns on hover are expected); move it with the toggle's `toggle_lead` / `toggle_trail` blocks. |
| **4. The sidebar and the launcher.** In full screen, hover and click the sidebar's buttons and the window's launcher. | The sidebar, on the HUD layer, draws over the frame's left edge and stays usable; the launcher closes the window. | The sidebar hidden or unclickable: the frame's root carries vanilla's `clickthrough_blocker` across the whole screen, so a content margin can't free it; drop that line in `FRAME_CHANGES` (the content vbox keeps its own blocker). |
| **5. Width.** At 1600 × 900, then at a larger UI scale. | The content scrolls sideways where it is wider than the screen, and nothing clips. Until PR D, the sideways scroll bar can show with a single 520 column centered: that is expected. | Clipping: the frame's scroll area isn't scrolling sideways; compare with the Census Data window, which uses the same `fullscreen_scrollarea`. |
| **6. Closing it.** In full screen, press Escape; reopen, click Back; reopen, click Close (if check 2 leaves it reachable); reopen, open the Budget panel; reopen, open the ledger. | Each closes the window. Reopening it shows the full-screen frame again (the width is remembered for the session). | One doesn't close it: Back and Close clear `com_open_window` (`test_te_fullscreen_frame.py`); a panel or the ledger opening clears it from the launcher's root. |
| **7. The toggle keeps the tab.** Choose Grand Monuments, switch to Full Screen, then back. | Grand Monuments stays chosen in both frames. | The tab resets: something writes `te_systems_window_tab` on the switch (`test_the_toggle_keeps_the_tab`). |
| **8. Sound.** Switch to Full Screen with the game running. | The world's sound drops, as in vanilla's full-screen panels (the frame's `snapshot:/Dynamic/mute_world_80`), and returns on Side Panel or close. | The sound stays down after closing: the snapshot isn't released by the frame's `_hide`; note it. |

## The ten mirrored tabs (PR C, 2026-11-02)

The window now also shows the ten system tabs that live in vanilla panels, on two more strips: Banking, Tax Code,
Budget Breakdown, Strategic Reserve and Global Warming, then Demographics, Cultural Hegemony, United Nations, Nuclear
Weapons and Covert Warfare. Each host's tab and the window's mount the same body type, so their content should match.
The hosts should look as before, but for three columns now fixed at 520.

| Check | Expect | If it fails |
|---|---|---|
| **1. Each mirrored tab matches its host.** Open each of the ten in the window, then its host tab (Budget, Market, Population, Society, Diplomacy, Military). | The same headers, sections, order and Open Journal Entry button in both. Collapsing a section in one collapses it in the other (the flags are shared). | A difference: the host's outer flowcontainer kept something the body should hold; compare the host's `### MOD:` block with its `te_<system>_tab_body`. |
| **2. The hosts look as before.** Visit each host tab. | As before 2026-11-02, but Banking, Cultural Hegemony and the UN now sit in a fixed 520 column, centered (style guide rule 8). On the player's own market the Reserve tab may lose a gap above its panels: its other-market note now takes no space while hidden. | A shift elsewhere: compare the host with `git show 8c8ad6f1a:<host file>`. |
| **3. The strips.** Open the window in the side panel, then full screen. | Three strips of five, stacked, then side by side. "Demographics", "Strategic Reserve", "Cultural Hegemony" and "Budget Breakdown" wrap or shrink but don't elide. Each grayed tab's tooltip lists its checklist under the window's name for it. | A name elided: shorten it in `te_window_tab_<key>` (the owner's call); a wrong tooltip: the registry's row in `gen_te_systems_window.py`. |
| **4. Banking without its entry.** In the game's first fortnight, before Banking's entry starts, choose Banking. | The Monetary Policy readout under its header, with the note saying what opens the rest, as in Budget. | Nothing shown: the window's open gate is `te_budget_banking_tab_sgui` or the readout's (`test_banking_opens_on_either_branch_and_never_off_the_strip`). |
| **5. Global Warming shows your own market.** Open the Market panel on another market's Climate tab, then the window's Global Warming tab. | The window shows your own market (the journal's view); the Market panel still shows the other market's emissions and its leader's policies. | The window shows another market: the window overrode `te_gw_tab_market_view`; it should use the body's default. |
| **6. Tax Code's footer.** Start a draft on the window's Tax Code tab, in the side panel and in full screen; later, with a bill under debate. | The draft summary (Review, Discard, Introduce), or the bill's (Pass, Force Through, Withdraw), stays at the window's foot while the content scrolls, as in Budget, and only on the Tax Code tab. In full screen it is Budget's 554 band, centered. | Missing: `te_systems_window_tax_footer`'s gates. Too narrow in full screen: give the wide frame a vbox footer with an expanding divider. It is 554 in both frames because a flowcontainer can't stretch, and a fixed 1,620 would overflow a 1600-wide screen. |
| **7. Demographics.** Choose Demographics in the window after the first census, then read `debug.log`. | The Population tab's sections, without a header (as in the Population panel) and without the strata incomes (as in the Census Data window); no `PopsOverviewPanel` errors. | Errors: something the window draws reads the Population panel (`test_the_te_window_draws_nothing_that_reads_the_population_panel`). |
| **8. Another market.** Open the Market panel on another market, then its Strategic Reserve and Climate tabs. | The Reserve tab shows the note that the reserve is your own market's (with its button to open yours), not your reserve. Climate shows that market's emissions and its leader's policies. | The Reserve or Climate shows your own market: the Market panel's blockoverrides didn't reach the blocks declared inside the body's `tab_content` override (`te_st_res_tab_elsewhere`, `te_st_res_tab_gate`, `te_gw_tab_market_view`). Move the own-market gate onto the host's outer flowcontainer, or give Market its own body type. |
| **9. Load and frame rate.** Time a load before and after this PR, open the window's Demographics tab for the first time, and watch the frame rate with the window closed. | No longer load, no stall on first open beyond the Population tab's, and no frame-rate drop with the window closed. The window is a scripted widget made at startup, so its ten new tabs exist even while it is closed. | A slower load or a drop: the heaviest tabs (Demographics, the UN, Budget Breakdown) can mount only while chosen. |

## The column types (PR D0, 2026-11-02)

`te_ui_columns_three` and `te_ui_columns_two` (`gui/te_widget_library.gui`) hold the full-screen layouts' fixed 520
columns. The Census Data window's Demographics tab is the first layout on them; its widget tree should be unchanged.

| Check | Expect | If it fails |
|---|---|---|
| **1. The Census Data window.** Open Population, then Census Data, then its Demographics tab, before and after the first census. | Before: the pending line alone. After: the tab's sections in three columns of 520, 30 apart, centered, as before 2026-11-02. | No columns or a different layout: a blockoverride inside the type's nested columns didn't reach them; put the three flowcontainers back in `te_demog_browser_sections` (`git show 3d01f0d09:gui/te_demographics_layout.gui`). |

## The wide layouts: PR D2 (2026-11-02)

Banking, Tax Code, Strategic Reserve, Global Warming and Demographics now lay their sections out in columns of 520 in
full screen, read down each column and then across, in the side panel's order. The side panel is unchanged. Each
column's sections were balanced by GUI line count, a poor proxy for height, so these checks settle them. For each, the
fallback is the same: move a section to the next or previous column in its `te_<system>_wide_sections`, keeping the
order (the system's layout test pins the order, not the split).

| Check | Expect | If it fails |
|---|---|---|
| **1. Banking.** Open Banking in full screen with the cycle running, then for a country with the monetary readout only. | Three columns: the overview and Active Policies; Monetary Policy and Available Interventions; the history charts and How Banking Works. Nothing is cut off. With the readout only, the readout and its note alone, as in the side panel. | Uneven or cut off: move a section between columns in `te_banking_wide_sections` (`test_banking_layout.WideTest`). |
| **2. Tax Code, full code.** Open Tax Code in full screen under the legislated code, with a bill under debate and a draft open. | Three columns: the overview, the bill, passed bills and promises; the Enacted Code, the workbench and the review; the history and How Tax Legislation Works. The draft or bill summary stays in the footer. Nothing is cut off. | Uneven or cut off: move a section in `te_tax_wide_sections`, keeping the order (`test_tax_code_layout.WideTest`). |
| **3. Tax Code, Light code.** The same under the Light code. | The overview and the light section; How the Light Tax Code Works; and an empty third column, which keeps its 520, so the content sits in the left two thirds. Expected: note whether it reads well. | If the empty column looks wrong, raise it with the owner: the alternative is the plan's first design, the Light code in its own two-column row under the light gate (the controller ruled on one row, 2026-11-02). |
| **4. Strategic Reserve.** Open Strategic Reserve in full screen. | Two columns: the overview and the inventory; How the Strategic Reserve Works. Nothing is cut off. | Cut off or uneven: move a section in `te_st_res_wide_sections` (`test_strategic_reserve_layout.WideTest`). |
| **5. Global Warming.** Open Global Warming in full screen, after opening the Market panel on another market's Climate tab. | Three columns: the overview and Mitigation Policies; Top Emitters and the Fossil Transition; History and How Global Warming Works. Your own market's figures. With the Global Warming rule off, the Fossil Transition alone, in the middle column. Nothing is cut off. | Another market's figures: the wide layout should replace the whole `te_gw_tab_layout`. Uneven or cut off: move a section in `te_gw_wide_sections` (`test_global_warming_layout.WideTest`). |
| **6. Demographics.** Open Demographics in full screen after the first census, then read `debug.log`. | The Census Data window's three columns, for your country: the overview, Causes of Death and the pyramid; Work and Retirement, Longevity, Family Policy and History; Wealth (without the strata incomes), Where People Live, States and How Demographics Works. No `PopsOverviewPanel` errors. Nothing is cut off. | Errors or another country's figures: `te_demog_browser_sections` reads the Country in context, which the window body sets to the player. Uneven or cut off: move a section in `te_demog_browser_sections`, which moves it in the Census Data window too (`test_demographics_layout.OrderTest`). |
