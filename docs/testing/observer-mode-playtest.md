# The system tabs in observer mode: play-test list

An observer has no `GetPlayer`, so a tab button whose `visible` reads its scripted GUI gate through
`GuiScope.SetRoot( GetPlayer.MakeScope )` logs `untyped trigger [ Scoped object of type 'country' is not valid
(Country  (4294967295)) ]` every frame the panel draws. The Market panel's Climate and Reserve tabs were fixed after
the observer session of 2026-10-25; on 2026-11-02 the same guard, `Not( GetMetaPlayer.IsObserver )` first in an
`And`, went on every other vanilla panel's system tabs (`gui_modding_guide.md`, the gotcha starting "An observer has
no `GetPlayer`"). The change passed the offline gate only: `test_gui_observer_guard.py`, the GUI lint and the audits.
What only the game can show is below. In-game checks don't gate a merge (CLAUDE.md, "In-game checks"); work through
these the next time the game is up.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **Rules.** Leave every system's game rule on (Banking, Tax Code, Cultural Hegemony, Nuclear Weapons, Covert
  Warfare, United Nations, Demographics, Global Warming), so each tab would be on a player's strip.
- **Observe.** Load a save, note the current size of `error.log`, then type `observe` in the console.
- **Logs.** After the checks, search what `error.log` gained, then `debug.log`, for `untyped trigger` and
  `te_system_tab_sguis.txt`. The tab gates' `is_shown` lines are `:48` (Banking), `:98` (Tax Code), `:120` (Cultural
  Hegemony), `:144` (UN), `:169` (Nuclear), `:193` (Covert), `:223` (Climate), `:269` (Reserve) and `:295`
  (Demographics).

| # | Check | Expect | If it fails |
|---|---|---|---|
| 1 | **Budget.** Open the budget panel and leave it open a minute; switch through its tabs. | Vanilla's tabs and Budget Breakdown, no Banking or Tax Code tab. No `te_system_tab_sguis.txt:48` or `:98` line. | A line logged every frame: see the last column of row 7. |
| 2 | **Budget's tax and tariff buttons.** On the budget panel's first tab, hover the tax-level bar, the add-consumption-tax button, and a good's tariff bar. | No `te_tax_native_sguis.txt` line. Those buttons' `enabled` and `tooltip` read `te_tax_native_*_sgui` through `GetPlayer.MakeScope` on vanilla's own buttons, which an observer sees: they are outside the mod's `### MOD:` blocks, so the 2026-11-02 change left them as they were. | A line each frame: guard each `enabled` with `Not( GetMetaPlayer.IsObserver )` first, as the tab buttons are. A line on hover only: the `tooltip`s; guard them the same way. |
| 3 | **Society.** Open the society (culture) panel. | No Cultural Hegemony tab. No `:120` line. | As row 1. |
| 4 | **Military.** Open the military panel. | No Nuclear or Covert tab. No `:169` or `:193` line. | As row 1. |
| 5 | **Diplomacy.** Open the diplomatic overview. | No UN tab; vanilla's five tabs as before. No `:144` line. | As row 1. |
| 6 | **Pops.** Open the pops overview. | No Demographics tab. No `:295` line. | As row 1. |
| 7 | **Market.** Open the market panel, then another country's market. | No Climate or Reserve tab. No `:223` or `:269` line (the 2026-10-25 fix, rechecked beside the others). | A line still logged every frame from a tab button: `And` evaluated its second argument after all (`gui_modding_guide.md` says it seems to skip it, on one case). Record that in the guide, then move the gate behind a container: wrap each mod slot's two halves in the strip types (`te_tab_buttons_six` in `gui/te_system_tab_widgets.gui`, and vanilla's `tab_buttons` for the society, military and pops panels) in a widget whose `visible` is `Not( GetMetaPlayer.IsObserver )`. |
| 8 | **Back as a player.** Type `play <tag>` for a country whose entries run (or reload the save) and open each panel again. | Every tab is on its strip as before, greyed or not as its entry stands: the guard hides tabs from an observer only. | A tab missing after `play` but back on a reload as that country: `GetMetaPlayer.IsObserver` outlives `observe`; note it beside the gotcha. Missing on a reload too: the guard isn't the cause; check the tab's unlock gate. |
