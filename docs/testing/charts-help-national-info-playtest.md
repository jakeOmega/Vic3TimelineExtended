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
