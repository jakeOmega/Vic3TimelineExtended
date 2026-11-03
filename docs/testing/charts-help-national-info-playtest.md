# Charts, Help pages and National Info: play-test checklist

What the next play-test should look at in the Help pages, the full-screen charts and National Info (spec
`docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md` § 9; plan
`docs/superpowers/plans/2026-11-02-charts-help-national-info.md`). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Logs.** Read `debug.log`, not `error.log`. Search it for `te_popups`, `te_ui_popup` and the type names each
  section gives.

## The Help popup and the "?" (PR H1, 2026-11-02)

Banking's, Grand Monuments' and the Colonial Empire's "How X Works" sections are Help pages now: popups in the
`te_popups` root (`gui/te_popups.gui`, on `layer = popups`), each `te_<key>_help_popup`, shown on the client-side
`te_popup` key (`help_banking`, `help_grand_monuments`, `help_colonial_empire`). The section stays at the foot of the
panel as its header alone, which opens the page; each tab's header has a "?" at its right that does the same. Until
H1, `te_popups` held only the Space Race's pickers, and none of its popups has been seen in game.

| Check | Expect | If it fails |
|---|---|---|
| **1. Above the window, side panel.** Open the Timeline Extended window on Grand Monuments, then Colonial Empire, and click the "?" in each tab's header. | The page opens centered over a dimmed screen, above the window, titled with the section's name ("How Grand Monuments Work"), its topics under their subheadings, scrolling if longer than the popup. | Under the window, or not at all: the popups layer is below the window's. Fallback (spec § 9, item 1): instance each page at window level in each full-screen host, as the Space Race's pickers would need too. |
| **2. Above the window, full screen.** Switch to Full Screen and repeat on Banking. | The page over the full-screen frame, not under it or under the HUD. | As item 1. |
| **3. Above the vanilla side panels and the journal.** Open Banking from the Budget panel's Banking tab, then the Banking Cycle, Monuments and Colonial Empire journal entries, and click How Banking Works (or its system's section) at the foot of each. | The page opens over the Budget panel and over the journal. | As item 1. |
| **4. Above the Census window.** With the Census Data window open, open a page from the Timeline Extended window. | The page over the Census window. | As item 1. |
| **5. Escape and a click outside.** With a page open over the window, press Escape; open it again and click the dimmed area. | Each closes the page and leaves the window (or panel, or journal) under it open. | Escape closes the window too: the popup's close button carries `shortcut = "close_window"` and the window's does as well; note which closes first. |
| **6. The "?" itself.** Look at each tab's header, side panel and full screen, and Banking's with no entry yet (the Monetary Policy readout header, early in a game). | A round button with a gold question mark at the right of the header text, its hover "How this system works: …". Banking's "?" shows on whichever header shows. | Missing or misplaced: `te_help_button` in `gui/te_system_tab_widgets.gui` (`parentanchor = right|vcenter`, `position = { -10 0 }`). A blank disc: vanilla's `button_icons/unused/help.dds` didn't load; use `button_icons/vickypedia.dds`. |
| **7. The link.** The section at the foot of each panel. | Its header alone, with no arrow, the hover "Opens the Help page.", and a click opens the page with the "increment" click (the sound an opening section makes). | An arrow still drawn: `arrow_visible` didn't hide it; hide the two `onclick_showmore` / `onclick_showless` blocks instead (`visible = no` in each), which also hides the arrows but makes every click play "decrement". |
| **8. Banking's monetary topics.** Open How Banking Works under the full Banking System, then in a game on Simplified Banking. | The Rate, the mandates, gold, the exchange rate, the arrangements, borrowing and prices are listed under the full system only. | Shown under Simplified or missing under full: the gate now reads `GetPlayer` (`banking_mon_system_shown`); check `debug.log` for the scripted GUI. |
| **9. The Colonial Empire's figures.** Open How the Colonial Empire Works, with and without the entry running (a country with no colony). | The monthly limit (±1.67: `colonial_stability_drift_cap` is 1.667, shown to two decimals), the projection's months (12) and the Round Table's authority (200) show as numbers, not blanks or `[…]`. | Blank: the three keys read `GetPlayer.MakeScope.ScriptValue(…)`; check the script values (`colonial_stability_drift_cap`, `colonial_empire_projection_months`, `colonial_round_table_authority`) evaluate on a country with no entry. |
| **10. A long page.** Open How Banking Works with the full system on. | All ten topics scroll in the popup, the text at its 460 column, nothing clipped at the right. | Clipped: widen the popup in `te_ui_help_popup` (`popup_size`). Reads badly as one page: the topic list of spec § 5.3. |
| **11. A large UI scale.** On a 1080p screen, set the UI scale to about 1.25 to 1.3 and open How Banking Works. | The popup, 820 tall, fits: its header, title and close button stay on screen. | Off the top: Escape and a click outside still close it. Lower the height in `te_ui_help_popup` (`popup_size`), to about 700, or make it a share of the screen. |

## The panel's charts look as before (PR C1, the chart registry, 2026-11-02)

The 33 history charts are generated now: each section instances its chart's wrapper, `te_hist_<id>` in
`gui/te_history_charts_generated.gui`, where the chart was. Offline, every chart rendered byte for byte as its section's
instance had it, so nothing should look different. Logs: read `debug.log` and search it for `te_hist_` and
`te_history_chart`.

| Check | Expect | If it fails |
|---|---|---|
| **Each history section, both widths.** Banking (the Budget tab and the journal entry), the Strategic Reserve (expand a good's row), Demographics, Cultural Hegemony, Nuclear Weapons (the taboo's history), the United Nations, Global Warming and the Colonial Empire, in the side panel and in full screen. | As before: the same charts in the same order with the same gaps, each centered in its section, its bars, hovers and range buttons working. | A shift or a new gap: the wrapper carries only `parentanchor = hcenter` around the chart. Compare the section with its text before C1 (`git show 855689f14:<file>`). |
| **Banking's paired and hidden charts.** A country on a digital currency and one not; then a game with `banking_system_simplified`. | One policy-rate chart at a time, with no empty gap where the other was; under the simplified system, no inflation or exchange-rate chart and no gap. | A gap: the chart's `visible` must sit on the section's wrapper instance (`te_hist_mon_policy = { visible = … }`), not inside it. |

## The chart viewer (PR C2, 2026-11-02)

Each history chart has a round button beside its title (`te_chart_open_button`, a placeholder icon, vanilla's area-chart
toggle) that opens the chart alone at full size: a popup in the `te_popups` root (`gui/te_popups.gui`, on
`layer = popups`), `te_chart_<id>_popup`, shown on the client-side `te_popup` key, `chart_<id>`. The popups are generated
with the charts (`gen_te_history_charts.py`, into `gui/te_history_charts_generated.gui`). Each holds the chart's range
buttons, the large chart (a 1,200 px plot, bars 336 px tall) and the key its section draws. Until now no popup in
`te_popups` has been seen in game. Logs: search `debug.log` for `te_chart_`, `te_hist_` and `te_history_chart`.

| Check | Expect | If it fails |
|---|---|---|
| **1. The button.** Every history section, in the side panel and full screen: Banking's eight charts, a Strategic Reserve good's row, Demographics' eight, Cultural Hegemony's, the taboo's two, the UN's two, Global Warming's two and the Colonial Empire's two. | A small round button just after each title (where depends on the title's length), its hover "See this chart at full size."; every title whole (at most 456 px beside the button, Demographics' and the Reserve's checked offline). The plot and legend sit where they did before C2: the title's row is now as tall as the taller of the title and the 24 px button, so a title box shorter than 24 px moves every chart down by the difference (Demographics stacks eight). | No button: `chart_open` isn't reached through the wrapper's `blockoverride`. A title cut short: lower `OPEN_GAP`, or shorten the title. The charts moved down: size the button to the title's height (`OPEN_BUTTON`, and the type's `size` block). |
| **2. Above every host.** Open a chart from the Timeline Extended window (side panel, then full screen), from the Budget panel's Banking tab, from a journal entry (the Banking Cycle, the Nuclear Program), from the Population panel's Demographics tab and from the Census Data window's. | The chart centered over a dimmed screen, above the window, the panel or the journal it came from. | Under it, or not at all: the popups layer is below the host's. Fallback (spec § 9, item 1): instance the popups at window level in each full-screen host. |
| **3. Closing.** Escape; the close button; a click on the dimmed area. | Each closes the viewer and leaves the window, panel or journal under it open. | Escape closes the window too: both carry `shortcut = "close_window"`; note which goes first (H1's row 5 asks the same). |
| **4. It fits.** At 1600 × 900, UI scale 1: a monthly chart (1,320 × 580; Banking's 1,320 × 620 with its marker key), a Demographics chart (1,360 × 640) and Cultural Hegemony's (1,360 × 760, with its fifteen-model key). | The whole popup on the screen, no scrollbar, nothing cut at the right, the whole key under the chart. | A scrollbar or a clipped key: raise its row's height in the generator (`CHART_TEXT_H`, `KEYS`). Off the screen: the popup is too tall for 900; drop Cultural Hegemony's key to one column or let it scroll. |
| **5. The bars at 1,200.** A monthly chart at 1 Year, 5 Years and 20 Years; an annual one at 5, 20 and 100 Years. | Monthly bars 100, 20 and 5 px wide, annual ones 240, 60 and 12 px, each a full range reaching the frame's left edge, each hovering with the panel's tooltip. | Bars at the panel's widths: the large wrapper's `plot_layouts` didn't reach the chart. No hover: as on the panel, the tooltip has only the bar's own context (gotcha #24). |
| **6. The two zero lines.** The digital-currency policy-rate chart (a country on Digital Currency) and inflation. | Each line at 0%: 73 px and 90 px above the frame's foot, where a 0% bar ends. | Off: the large `${zero_y:…}` is computed as 6 + fraction × 336; check the bars' box against the frame. |
| **7. The large cycle-value chart's bars.** Open Banking's first chart in the viewer, over a cycle that has passed through several phases. | Every bar in its phase's color with a thin dark cap about 3 px tall, as on the panel; a month near 0 draws a sliver. | A 13 px cap or a 7 px floor in some bands: one `blockoverride "phase_value"` (or `phase_cover_value`) reaches only some of `te_history_bar_cycle_phase`'s six bars. Give each bar a block of its own. |
| **8. A chart's title and legend, each its own width.** A panel chart's title beside its button; then in the viewer, any chart's title and one with a long legend (inflation's). | On the panel, the title stops at 456 px, clear of the button. In the viewer, the legend runs to the plot's width (1,204 px; 1,244 for the annual charts), wrapping only past it, and the title keeps the type's 484, which no title reaches. | A panel title under its button: `chart_title_width` doesn't reach the title's textbox. A large legend stopping at 484 px: `chart_text_width` doesn't reach the legend's. Each textbox has a block of its own. |
| **9. One range.** In the viewer, pick 5 Years; close it. | The panel's charts show 5 Years too, and the viewer opens at the panel's range next time. | They differ: the viewer's row (`te_chart_range_row_<var>`) sets another variable than the section's buttons. |
| **10. Whose chart.** A Demographics chart (it reads the country, not an entry) and a Strategic Reserve good's. | The player's figures, as on the panel. The Reserve's header names the good ("Strategic Reserve: Grain"), the chart's own title "Fill by Month" under it. Demographics' pip key and Banking's marker key under their charts. Wealth Concentration's header is a concept link, the first in a popup's header: it reads as the concept's name. | Empty bars with data on the panel: the popup's `GetPlayer` or `GetPlayerJournalEntry` datacontext didn't reach the chart; `debug.log` names the missing context. |
| **11. A law change under an open viewer.** Open the policy-rate chart, then enact or repeal Digital Currency with the game running. | The viewer keeps drawing the chart it opened with (its axis from 0, or from -3) until closed; the panel switches to the other one. Expected, not a fault (`gen_te_history_charts.py`, "THE GATE AND NOTHING ELSE"). | The viewer blanks or errors: the popup applies more than the tab's gate; `test_te_popups.ChartPopupTest` should have caught it. |
| **12. Another country's Census Data window.** Playing one country, open another's Politics tab, then Census Data, then Demographics. | Its charts show no open button (`visible = "[Country.IsLocalPlayer]"` on the Demographics charts' buttons), since the viewer reads the player; the player's own Census window, Population panel and Timeline Extended window show it. F1 adds the button that opens the other country's chart. | A button on another country's chart: it opens the player's chart under the same title. `OWN_COUNTRY_ONLY` in `gen_te_history_charts.py` didn't reach the button. No button on the player's own: that host supplies no `Country`. |
