# Market panel trade additions play-test checklist

What the next play-test should look at in the mod's additions to the Market panel's Trade tab: Exports and Imports by
Value, the Import and Export Partners charts, and the Top Trade Partners table. The All Goods tariff rows have their own
list, `all-goods-tariffs-playtest.md`. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and
the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own
section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** Market panel, Trade tab, on your own market and on another market a month into the game (the
  partner lists are built on the monthly pulse).
- **Logs.** Read `debug.log`, not `error.log`.

## Top Trade Partners as a list (2026-10-27)

The audit's findings MKT-1 to MKT-4 (`docs/audits/gui_audit/climate_reserve_market.md`). `update_market_trade_partners`
(`common/scripted_effects/trade_partner_effects.txt`) builds `te_tp_top_markets` on each market's owner, the five
markets it trades most with, largest first; the table is one datamodel row per item, and each figure is read live
through the charts' `GuiScope` form with the partner passed as `tp_partner_country`. Offline,
`test_market_trade_partners.py` holds the list, the loc and the widths. No self-check line: the list is built by the
same `ordered_market` pass the charts' lists use, and what is unproven is the GUI side.

| Check | Expect | If it fails |
|---|---|---|
| **Rows.** Open the Trade tab on your own market, then on a large trading market. | Up to five rows, largest trade first, each with the partner's name, its yearly trade and that trade as a share of GDP. Fewer rows when fewer markets trade with it; none, and no header, when none do. | No rows on a market with trade: the datamodel over `MarketPanel.GetMarket.GetOwner.MakeScope.GetList('te_tp_top_markets')` drew nothing; read the owner's variable list in a plain-text save. Rows with figures of 0: the `AddScope( 'tp_partner_country', Country.MakeScope )` read failed inside the item; the fallback is the five rank rows from before MKT-1 (git history of `market_panel.gui` and `trade_partner_effects.txt`). |
| **Partner hover.** Hover a row's trade figure. | The underlined figure opens the goods breakdown: first the yearly figure the row shows, then the week's goods at market prices. | The breakdown for the wrong pair: the tooltip's two datacontexts (`[Scope.GetMarket.GetOwner]`, `[MarketPanel.GetMarket]`, gotcha #24). |
| **Units.** Read the Import and Export Partners charts, then hover their headings. | Each partner's figure ends "units/wk"; the headings' hovers say they count units of all goods together, and that Top Trade Partners ranks by value. | A blank figure: the `base_market` read in `te_market_<dir>_partner_units`, which the charts used before. |
| **Labels.** Read every heading and hover on the additions. | English text from loc, no raw keys; the headings and hovers read as before. | A raw key names the missing loc. |
| **Type size.** Read the table at 1080p. | Its text at 17; "Trade / yr" and "% of GDP" fit their columns. | Note the cell and its text. |
