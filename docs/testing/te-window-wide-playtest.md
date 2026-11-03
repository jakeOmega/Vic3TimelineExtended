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
| **The Space Race with several milestones running.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: nothing after Space Powers and Orbit.* | Each running milestone under its own header, then Space Powers and Orbit, then How the Space Race Works. | A missing milestone or header: check `te_sr_window_milestones` in `gui/te_systems_window_generated.gui`. |

## The full-screen frame and the toggle (PR B, 2026-11-02)

The frame is vanilla's `fullscreen_block_window` with Back and Close changed. It sits at the window root's origin, as
vanilla's full-screen panels do, and draws its own top filler under the top bar. The window's layer
(`layer_ingame_menu`) is below the HUD's, so the HUD draws over it. Vanilla hides much of the HUD while its own
full-screen panels are open (the `fullscreen_hide` and `half_and_fullscreen_hide` templates in `block_windows.gui`,
which read `InformationPanelBar.IsPanelOpen`); a scripted window never trips them, so those parts stay up over this
frame. Each tab lays its sections out there in columns of 520 (the PR D sections below). Since the HUD fix (the last
section below) the mod's copies of those templates read the frame too, so check 2's HUD should be gone.

| Check | Expect | If it fails |
|---|---|---|
| **1. The top bar.** Switch to Full Screen. | The real top bar draws over the frame's top filler, with no second top-bar band below it, and the frame's title, Back and Close sit below the top bar. | A second band, or the title hidden under the top bar: inset the wide frame under the top bar (a `margin_widget` with `margin_top = 85`, the plan's first idea) **and** drop the frame's 78 px top filler in the generator's `FRAME_CHANGES` (it isn't in a block, so an inset alone draws it as a second band at 85). |
| **2. The HUD over the frame.** In full screen with the outliner open, then while paused. | Expected, and to judge: the outliner over the frame's right 360 px from just under the top bar; the construction info box under the top bar's right end, over most of Close; the pause button (screen center, 340 above the middle) over the strips' middle at 1080p; the lens toolbar and the notifications along the bottom. Note what each hides and whether it gets in the way. | The outliner over content: widen the frame's `content_margin_right` block (about 410 keeps its column free; the 1,620 column then scrolls sideways at 1080p). Close covered: move it left of the construction box with the frame's `close_button_position` block (`position = { -420 15 }`). ~~To hide the HUD as vanilla does, redefine vanilla's three templates in a `00_` file so they also read `te_systems_window_wide`: untested for templates, and the owner's compat call.~~ Done by the HUD fix (last section), which reads the frame's visibility and the root's rather than the width key alone, since the width is remembered after the window closes. |
| **3. Side Panel stays reachable.** In full screen, with the outliner open, click Side Panel. | It sits at the left above the tabs, clear of the outliner, and returns the window to the side panel. | Covered: by what (the top bar's dropdowns on hover are expected); move it with the toggle's `toggle_lead` / `toggle_trail` blocks. |
| **4. The sidebar and the launcher.** In full screen, hover and click the sidebar's buttons and the window's launcher. | The sidebar, on the HUD layer, draws over the frame's left edge and stays usable; the launcher closes the window. | The sidebar hidden or unclickable: the frame's root carries vanilla's `clickthrough_blocker` across the whole screen, so a content margin can't free it; drop that line in `FRAME_CHANGES` (the content vbox keeps its own blocker). |
| **5. Width.** At 1600 × 900, then at a larger UI scale. | The content scrolls sideways where it is wider than the screen, and nothing clips. | Clipping: the frame's scroll area isn't scrolling sideways; compare with the Census Data window, which uses the same `fullscreen_scrollarea`. |
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

## The wide layouts: PR D1 (2026-11-02)

Six tabs now lay out in columns of a fixed 520, 30 apart, centered, in the full-screen frame (spec § 7): Nation, Space
Race, Grand Monuments, Colonial Empire, Seabed and Budget Breakdown. The side panel and the Budget panel's Breakdown tab
are unchanged. The columns were balanced by GUI line count, a poor proxy for height, so this play-test settles them. If
every tab shows three empty columns, the overrides didn't reach the column blocks: start from PR D0's check 1. If Space
Race, Grand Monuments, Colonial Empire or Seabed draws its one narrow column in full screen, the mount's override didn't
reach the body's `te_<system>_tab_layout` block (the engine fact of PR C's check 8): give the system a wide body that
overrides `tab_content` itself. A section that hides empties its place but keeps its wrapper, so a column can start
10 px lower than its neighbors (Grand Monuments' third, while Trophies and Held Abroad are hidden).

| Check | Expect | If it fails |
|---|---|---|
| **1. Nation.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is Where These Come From alone, and closes up until a permanent effect is listed.* Open the tab in full screen. | The columns read in the spec's order: the overview, Governance and Society; Economy, Science and Space and International; Where These Come From and How the Nation Works. No section overlaps the next column; watch the section headings, which are vanilla's `default_header` at 554 in a 520 column. | A column far taller than the others: move a section to another column in `te_nation_wide_sections` (`gui/te_nation_tab.gui`), keeping the order; `test_nation_tab.py` pins it. Headings that overhang into the gap and touch at the same height: give `te_nation_header` `blockoverride "size" { size = { 520 44 } }`, as Budget Breakdown's chart headings have; that narrows the side panel's headings too, so it is the owner's call. |
| **2. Space Race.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; two columns, with no How column.* Open the tab in full screen with a milestone running, then between milestones. | The milestones under way (or the idle note) in the first column, Space Powers and Orbit in the second, How the Space Race Works in the third. No section overlaps the next column; watch the milestone and idle headings, vanilla's 554-wide `default_header`. | As above, in `te_sr_wide_sections` (`space_race_widget.gui`); `test_space_race_layout.py` pins it. Overhanging headings: the same 520 size override on the generator's two `default_header` lines (`gen_te_systems_window.py`), the owner's call as for Nation. |
| **3. Grand Monuments.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is Trophies and Held Abroad, and closes up while neither shows.* Open the tab in full screen. | The overview, Opportunity, Awaiting a Decision and Awaiting Dedication; Archaeological Expeditions, National Effects and Our Monuments; Trophies, Held Abroad and How Grand Monuments Work. Nothing is cut off. | As above, in `te_gm_wide_sections` (`grand_monuments_widget.gui`); `test_grand_monuments_layout.py` pins it. |
| **4. Colonial Empire.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is History alone.* Open the tab in full screen. | The overview, Colonial Holdings and Why Stability Is Moving; International Pressure and Colonial Programs; History and How the Colonial Empire Works. Nothing is cut off. | As above, in `te_ce_wide_sections` (`colonial_empire_widget.gui`); `test_colonial_empire_layout.py` pins it. |
| **5. Seabed.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; two columns.* Open the tab in full screen. | The overview and Seabed Policy; the Ocean Basins table; How Seabed Licenses Work. Nothing is cut off, with a basin opened onto its claimants. | As above, in `te_seabed_wide_sections` (`te_seabed_widgets.gui`); `test_seabed_layout.py` pins it. |
| **6. Budget Breakdown.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; two columns, income and expenses; in the Budget panel the two sections under a header with its "?".* Open the tab in full screen, then the Budget panel's Breakdown tab. | Weekly Income, Weekly Expenses and How the Breakdown Works side by side; in the Budget panel, the three one under another as before (How is its own section type now). Nothing is cut off. | As above, in `te_budget_breakdown_wide_sections` (`te_budget_breakdown.gui`); `test_budget_breakdown.py` pins it. A gap changed in the Budget panel: `te_budget_sec_how`'s spacing should be the panel's 8. |

## The wide layouts: PR D2 (2026-11-02)

Banking, Tax Code, Strategic Reserve, Global Warming and Demographics now lay their sections out in columns of 520 in
full screen, read down each column and then across, in the side panel's order. The side panel is unchanged. Each
column's sections were balanced by GUI line count, a poor proxy for height, so these checks settle them. For each, the
fallback is the same: move a section to the next or previous column in its `te_<system>_wide_sections`, keeping the
order (the system's layout test pins the order, not the split).
Each tab's header sits centered over the columns (a header at the row's left edge lacks
`using = default_list_position`). If a tab draws its one narrow column in full screen, the mount's override didn't
reach the body's `te_<system>_tab_layout` block (the engine fact of PR C's check 8): give the system a wide body that
overrides `tab_content` itself.

| Check | Expect | If it fails |
|---|---|---|
| **1. Banking.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is the history charts alone, and closes up while the cycle is dormant.* Open Banking in full screen with the cycle running, then for a country with the monetary readout only. | Three columns: the overview and Active Policies; Monetary Policy and Available Interventions; the history charts and How Banking Works. Nothing is cut off. With the readout only, the readout and its note alone, as in the side panel. | Uneven or cut off: move a section between columns in `te_banking_wide_sections` (`test_banking_layout.WideTest`). |
| **2. Tax Code, full code.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is the history alone.* Open Tax Code in full screen under the legislated code, with a bill under debate and a draft open. | Three columns: the overview, the bill, passed bills and promises; the Enacted Code, the workbench and the review; the history and How Tax Legislation Works. The draft or bill summary stays in the footer. Nothing is cut off. | Uneven or cut off: move a section in `te_tax_wide_sections`, keeping the order (`test_tax_code_layout.WideTest`). |
| **3. Tax Code, Light code.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; the overview and the light section alone, centered, as columns 2 and 3 close up.* The same under the Light code. | The overview and the light section; How the Light Tax Code Works; and an empty third column, which keeps its 520, so the content sits in the left two thirds. Expected: note whether it reads well. | If the empty column looks wrong, raise it with the owner: the alternative is the plan's first design, the Light code in its own two-column row under the light gate (the controller ruled on one row, 2026-11-02). |
| **4. Strategic Reserve.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; the overview, then the inventory.* Open Strategic Reserve in full screen. | Two columns: the overview and the inventory; How the Strategic Reserve Works. Nothing is cut off. | Cut off or uneven: move a section in `te_st_res_wide_sections` (`test_strategic_reserve_layout.WideTest`). |
| **5. Global Warming.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is History alone, and closes up with the Global Warming rule off.* Open Global Warming in full screen, after opening the Market panel on another market's Climate tab. | Three columns: the overview and Mitigation Policies; Top Emitters and the Fossil Transition; History and How Global Warming Works. Your own market's figures. With the Global Warming rule off, the Fossil Transition alone, in the middle column. Nothing is cut off. | Another market's figures: the wide layout should replace the whole `te_gw_tab_layout`. Uneven or cut off: move a section in `te_gw_wide_sections` (`test_global_warming_layout.WideTest`). |
| **6. Demographics.** Open Demographics in full screen after the first census, then read `debug.log`. | The Census Data window's three columns, for your country: the overview, Causes of Death and the pyramid; Work and Retirement, Longevity, Family Policy and History; Wealth (without the strata incomes), Where People Live, States and How Demographics Works. No `PopsOverviewPanel` errors. Nothing is cut off. | Errors or another country's figures: `te_demog_browser_sections` reads the Country in context, which the window body sets to the player. Uneven or cut off: move a section in `te_demog_browser_sections`, which moves it in the Census Data window too (`test_demographics_layout.OrderTest`). |

## The wide layouts: PR D3 (2026-11-02)

In full screen, Cultural Hegemony, the United Nations, Nuclear Weapons and Covert Warfare now show in three columns of
520, 30 apart, centered (spec § 7). Each holds the side-panel tab's sections in the same order, read down each column
and then across, under the same gates. The side panel and the host tabs (Society, Diplomacy, Military) keep their one
column. The UN's Status section is now a type of its own (`te_un_sec_status`); it should look as before in every host.
Each tab's header sits centered over the columns; one at the left edge lacks `using = default_list_position`.
A section that hides empties its place, so a column can stand empty in some states (check 3). If every tab shows one
column, or three empty ones, the wide mount's override of the body's `te_<x>_tab_layout` block, or the composer
derived from `te_ui_columns_three`, didn't take: fall back to a `te_<x>_wide_body` frame registered with
`layout=None`, or to an instance of the column type inside a flowcontainer, as `te_demog_browser_sections` is built.

| Check | Expect | If it fails |
|---|---|---|
| **1. Cultural Hegemony.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is History alone.* Open the tab in full screen. | Three columns: the overview and Top Cultural Powers; Cultural Programs, Where Our Pull Comes From and Political Models of the World; History and How Cultural Hegemony Works (collapsed). No section overlaps the next column. | A column far longer than the others: move a section to the column before or after it in `te_ch_wide_sections` (`cultural_hegemony_widget.gui`), keeping the order. `WIDE_COLUMNS` in `test_cultural_hegemony_layout.py` pins the columns. |
| **2. The United Nations.** Open the tab in full screen, with a resolution in session and without one; if you can, also during a founding conference. | Three columns: the overview, Status (only at a founding conference or after a dissolution) and the General Assembly; Why UN Authority Is Moving, Missions in the Field, Programs and Conventions and Mandates in Force; Our Obligations, the Development Fund, Our Record, UN Authority History, Resolutions on the Record and How the UN Works (collapsed); the Development Fund shows only once there is one. No section overlaps the next column. Column 1 is likely the longest, since the Assembly is by far the largest section: note how far past the others it runs, in session and out of it. | Column 2 or 3 too long: move a section between them in `te_un_wide_sections` (`un_layout_widget.gui`), keeping the order (`WIDE_COLUMNS` in `test_un_layout.py` pins it). Column 1 too long: it already holds the Assembly under only the overview and Status, which come before it in the order, so no other section can leave it. A shorter column 1 means splitting the Assembly, which is the owner's call. |
| **3. Nuclear Weapons.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 ends on Nuclear Powers.* Open the tab in full screen, with a program and without one, and during a crisis if one comes. | Three columns: the overview, The Program with the progress bar to the next warhead under it (both only with a program), Nuclear Crisis, Strike and World Crises; Nuclear Posture, Forces, At Home and Reputation; The Nuclear Taboo, Delivery and Defense, Nuclear Powers and How Nuclear Weapons Work (collapsed). **Until the country holds its first warhead the middle column is empty**: Posture, Forces and At Home need a stockpile, and Reputation a credibility record, which arming starts. That is spec § 7's layout; judge whether the gap reads badly for most of a game. No section overlaps the next column. | The empty middle column reads badly: the owner may take the order-keeping alternative, column 2 Posture through Delivery and Defense (which has no gate, so the column is never empty), column 3 Nuclear Powers and How, in `te_nuclear_wide_sections` (`nuclear_layout_widget.gui`) and `WIDE_COLUMNS` in `test_nuclear_layout.py`. A column far longer than the others: move a section to the column before or after it, keeping the order and the bar under The Program. |
| **4. Covert Warfare.** *Superseded in part by "A "?" in every host" in `charts-help-national-info-playtest.md`: no How section in the columns; column 3 is Known Foreign Operations alone, and closes up until one is known.* Open the tab in full screen. | Three columns: the overview and Operations; Funding, Agent Networks and Counterintelligence; Known Foreign Operations (only once a foreign operation is known) and How Covert Warfare Works (collapsed), so column 3 is often How alone. No section overlaps the next column. | A column far longer than the others: move a section to the column before or after it in `te_covert_wide_sections` (`covert_operations_widget.gui`), keeping the order. `WIDE_COLUMNS` in `test_covert_layout.py` pins the columns. |
| **5. The side panel and the hosts.** Visit the four tabs in the side panel, and the UN tab in Diplomacy during a founding conference or after a dissolution. | One column, as before: the UN's Status section under the overview, open, and collapsible. | Status missing or changed: compare `te_un_sec_status` with the inline block it replaced (`git show 161c2830a:gui/journal_entry_widgets/un_layout_widget.gui`). |

## Full Screen hides the HUD, as vanilla's full screens do (2026-11-02)

The window's Full Screen now hides what vanilla hides under the Politics panel, the tech tree, the pop browser and the
building browser: the outliner and its wars list, the "Paused" button at the screen's top middle, the lens toolbar, the
construction box under the top bar's right end, and the backgrounds of the time controls and the top bar, with the
notifications in their compact form. `gui/00_te_fullscreen_hide.gui` redefines vanilla's three visibility templates
(`fullscreen_hide`, `half_and_fullscreen_show`, `half_and_fullscreen_hide`, from `block_windows.gui`) with one more
term, true exactly while the full-screen frame draws (the window open, for a played country, and the width key set),
and the Community Mod Framework's `com_fullscreen`, inert without it. The engine keeps the first definition of a
template's name it reads, and a mod's `00_` file is read before vanilla's, so the file should win over
`block_windows.gui` (gotcha #30 in `docs/guides/gui_modding_guide.md`). The Side Panel keeps the HUD as before.

| Check | Expect | If it fails |
|---|---|---|
| **1. The log.** After the first launch, read `gui.log`. | Three lines, `gui/block_windows.gui:<line> - Template '<name>' already registered at 'gui/00_te_fullscreen_hide.gui:<line>'`, one per template: vanilla's were read second and dropped. GDP Plotline Plus, in the owner's playset, rests on the same rule (`00_GDPPP_graph_tooltips.gui` redefines vanilla's `GDP_tooltip_with_graph` template): if the GDP tooltip shows a prestige graph under the GDP graph (that mod's addition), the first template already wins in game. | A line the other way round (the mod's file named as the later one) or none: the engine didn't take the mod's templates, and nothing below changes. The fallback is a full-file `block_windows.gui`, the owner's compat call. |
| **2. Full Screen hides it.** Pause the game, open the outliner, then the window, and switch to Full Screen. Compare with the Politics panel. | As under Politics: no outliner, no "Paused" button over the strips, no lens toolbar, no construction box over Close; the notifications compact at the bottom right. The top bar, the sidebar, the launcher and the speed controls stay. | One part still shows: note which; it is drawn by something other than the three templates, or by a mod file that copies vanilla's widget without them. All of it shows: check 1. |
| **3. The Side Panel keeps it.** Open the window as a side panel. | The outliner, the "Paused" button and the lens toolbar show as before. | Hidden: the window's term reads the width key without the frame (`test_te_fullscreen_hud.py`). |
| **4. Switching back.** In Full Screen, click Side Panel. | The HUD comes back at once, the outliner where it was. | It stays hidden: the side panel shows while the term still holds; compare the frame's `visible` with the term. |
| **5. Each way out of Full Screen.** In Full Screen, close the window with Escape; reopen it (it opens in Full Screen, the width remembered); close it with Back; reopen, Close; reopen, open the Budget panel; reopen, open the ledger; reopen, click the launcher. | The HUD comes back each time the window closes, and hides again each time it reopens in Full Screen. | It stays hidden after a close: that route hid the window without clearing `com_open_window`, which the term reads. |
| **6. A vanilla full screen still hides it.** From the window in Full Screen, open the Politics panel (it closes the window), then the tech tree. Then open the treaty draft. | Under Politics and the tech tree the HUD hides as before; under the treaty draft the outliner hides but the "Paused" button and the time controls' background stay, as in vanilla. | Different from vanilla: a vanilla term was lost in the mod's copy (`test_te_fullscreen_hud.py` should have failed). |
| **7. Loading a save.** In Full Screen, go to the main menu and load a save. | Either the window opens again in Full Screen with the HUD hidden, or it is closed with the HUD shown; never the HUD hidden with no window. | The HUD hidden with no window: the window's root hides on something the term doesn't read; add it to the term and to `te_full_screen_term` in the test. |

## The Tax Code footer's anchor (log fix, 2026-11-03)

Both frames' `fixed_bottom` sits in a `vbox`, where the footer's `parentanchor = hcenter` was ignored and logged `gui/te_systems_window.gui:162` (side panel) and `:206` (Full Screen) `- Widget cannot have a position in a layout`, about 25 lines each time the footer was laid out. The anchor is gone, which the engine had been doing anyway, so nothing should move.

| Check | Expect | If it fails |
|---|---|---|
| **1. The footer.** On the Tax Code tab, with a draft open and then with a bill under debate, in the side panel and in Full Screen. | The draft summary or the bill's footer sits at the bottom where it did before, its buttons usable. | It moved: the layout had honored the anchor after all; put `parentanchor = hcenter` back and accept the log line. |
| **2. The log.** Read `gui.log` after the check. | No `Widget cannot have a position in a layout` line for `te_systems_window.gui`. | Another widget in a layout carries a position: the line names it. |

## The owner's column balance (2026-11-03)

The owner rebalanced four full-screen tabs. Each tab's columns are its wide composer, which National Info's view of another country places too, so check both. The side panel and the hosts keep their one column and order. Banking, Grand Monuments and Demographics now read in an order of their own rather than the narrow one; `assert_wide_matches_narrow(..., columns=...)` pins each and still holds every section to its narrow gates.

| Check | Expect | If it fails |
|---|---|---|
| **1. Demographics.** Open Demographics in full screen after the first census, then National Info's Demographics tab for another country. | Column 1: the census, Work and Retirement, Longevity (once the late figures exist) and Wealth; column 2: the pyramid and History; column 3: Causes of Death, Family Policy, Where People Live and States. The same for another country, less what only a played country has. Nothing is cut off. | Uneven or cut off: move a section in `te_demog_browser_sections` (`gui/te_demographics_layout.gui`) and `BROWSER_COLUMNS` in `test_demographics_layout.py`. Longevity was placed after Work and Retirement, where the tab has it; the owner's list didn't name it. |
| **2. Grand Monuments.** Open the tab in full screen. | Column 1: the overview's cells, then National Effects, Opportunity, Awaiting a Decision and Awaiting Dedication; column 2: Archaeological Expeditions and Our Monuments; column 3 as before. | As above, in `te_gm_wide_sections` and `test_grand_monuments_layout.WideLayoutTest`. |
| **3. Banking.** Open Banking in full screen with the cycle running. | Column 1: the overview, Active Policies and Available Interventions; column 2: Monetary Policy alone; column 3 as before. | As above, in `te_banking_wide_sections` and `test_banking_layout.WideTest`. |
| **4. Nuclear Weapons.** Open the tab in full screen with a stockpile, then National Info's Nuclear tab for another country. | Yours: Nuclear Posture at the foot of column 1, under World Crises; column 2 Forces, At Home and Reputation. Another country's: no Posture anywhere; column 2 its Nuclear Taboo and Nuclear Powers, as before. | Posture shows for another country: its wrapper lost `Country.IsLocalPlayer` (`test_nuclear_layout.WideTest`). |
