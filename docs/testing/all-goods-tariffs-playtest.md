# All Goods tariffs play-test checklist

What the next play-test should look at in the Market panel's All Goods rows, which set one import or export level on
every tradeable good at once. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the
play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own section,
newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** Market panel, Trade tab, on your own market: the two All Goods rows sit above the goods list, and
  each good's own import and export bars below them show the level that took. Tick "Show All" to see goods with no
  trade.
- **Benches.** A market owner on Protectionism (every level allowed), one on Free Trade (no tariffs), and a junior
  partner in a customs union. For the treaty check, sign a No Tariffs article on one good with another country, as the
  source.
- **Logs.** Read `debug.log`, not `error.log`.

## The rows (2026-10-17)

The rows are `gui/te_bulk_tariff_widgets.gui`; each button is a scripted GUI
(`common/scripted_guis/te_bulk_tariff_sguis.txt`) that calls `set_<direction>_tariff_level` for each good of the Tax
Code's customs catalog (`te_bulk_tariff_effects.txt`). The engine's per-good buttons check ownership, the trade policy, a
treaty and a cooldown; the script setter is not known to, so the scripted GUIs restate the first three and keep their
own cooldown (`te_bulk_tariff_triggers.txt`). Offline, `test_bulk_tariffs.py` pins the goods list, the 14 scripted GUIs,
the gates and the loc; the checks below are what only the game shows.

| Check | Expect | If it fails |
|---|---|---|
| **Layout.** Open the Trade tab on your own market, then on another market. | Two rows (import, export icons) above the goods, each bar over the goods' own bars; no rows on another market. | Shift the label width (`236` in `te_bulk_tariff_row`) until the bars line up. |
| **Set.** Protectionism: click Imports, Maximum Tariffs. With Show All ticked, read every good's import bar. | Every tradeable good shows Maximum Tariffs, also goods with no trade; services, transportation, electricity and digital access show no change. Tariff income moves next week. | If nothing moved, the script setter ignored the call: check `debug.log` for an error on `set_import_tariff_level`. If some goods moved, a `g:<good>` key failed: same log. |
| **Grace and cooldown.** Within the week click Imports, No Tariffs or Subventions; after the week, hover any import level. Exports stay usable throughout. | The second click works and its tooltip says the 3-month wait is unchanged; after the week the import levels are grayed until 3 months after the first click, with the waiting line crossed. | The timed variables `te_bulk_tariff_cd_import` / `_grace_import` did not set or expire: read the country's variables in a plain-text save. |
| **Per-good cooldown.** Right after a bulk set, hover one good's own import buttons. | Record whether the base game's 3-month cooldown started for it (then its own buttons say when they free up). | Nothing to fix either way; note it in `docs/testing/tax-code-capability-ledger.md` row 15, which asks the same of the setter. |
| **Trade policy.** Free Trade: hover Imports, Maximum Tariffs. Mercantilism: hover Exports, Low Tariffs. | Free Trade: tariff levels grayed, "Our Trade Policy allows Import Tariffs" crossed; subvention levels and None usable. Mercantilism: both usable. | The capital's `modifier:state_tariff_import_add` read is not what the law gives: check it with the console's state modifier view, and compare with the per-good buttons' alpha. |
| **Treaty.** With a No Tariffs article on grain as its source, set Imports to Maximum Tariffs, then to Maximum Subventions. | Grain keeps its level for the tariff, and takes the subvention. | `te_bulk_tariff_barred` did not match the article: check `source_country` against the article's direction in the Diplomacy panel. |
| **Junior partner.** In a customs union as the junior, open the Trade tab. | The rows show, every level grayed, "We are the Market Owner" crossed. | The visibility test is `MarketPanel.GetMarket.IsSame( GetPlayer.GetCapital.GetMarket )`, as for vanilla's buttons. |
| **Tax Code.** Start with *Tax Code and Customs Enabled*. | Every level grayed, "Tariffs are not set by Tax Code bills" crossed. Under *Tax Code Enabled* and *Light Tax Code* the rows work. | The gate is `te_tax_native_tariff_controls_sgui` in `enabled` plus the scripted GUIs' own `te_tax_customs_on` line. |

## The wait says when it ends (2026-10-27)

The GUI audit's MKT-5 (`docs/audits/gui_audit/climate_reserve_market.md`). A bulk set records its day
(`te_bulk_tariff_cd_day_<direction>`, a `game_date` value), and while the row waits each level's hover says about how
many days are left (`te_bulk_tariff_cd_days_left_<direction>`, 91 days less the days since, at least 1). The row's label
is underlined as hoverable. Offline, `test_bulk_tariffs.py` pins the variable, the value and the wait line.

| Check | Expect | If it fails |
|---|---|---|
| **Days left.** Set Imports, wait past the week's grace, then hover an import level on three dates a month apart. | "Imports can be set for all goods again in about N days": about 84 a week after the set, then 30 fewer each month, and the levels free up when it would reach 0. | A figure that doesn't fall: `game_date` stored as a value does not count days; fall back to the fixed "3 months" line. A figure off by a few days from when the levels free up: the timed variable's three months are not 91 days; adjust the 91. |
| **A save from before.** Load a save with a bulk set inside its cooldown from before this change. | The line from before, "…within a week, then not for 3 months" (the day was never recorded), until the next set. | "About 0 days": the `else_if` in `te_bulk_tariff_apply` no longer asks for `te_bulk_tariff_cd_day_<direction>`. |
| **Label.** Hover the Imports and Exports labels. | Underlined, with their tooltips as before. | Not underlined: the `#tooltippable` format in `te_bulk_tariff_widgets.gui`. |
