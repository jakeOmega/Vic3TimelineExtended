# Cultural Hegemony play-test checklist

What the next play-test should look at for the Cultural Hegemony panels after the 2026-10-27 GUI and localization audit
(CH-1 to CH-15, `docs/audits/gui_audit/hegemony_covert.md`). In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): the branch landed on the offline gate, and these are the things only the
game can show. Strike a fixed item through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Console harness:** `event te_debug_ch.1` (Ministry of Culture, a funding cap and three programs running; us at rank
  1; us outside the top ten; an empty slot 5; the Ministry repealed). Each helper rebuilds the board
  (`ch_board_rebuild`), so the table follows at once.
- **Board rows:** the board fills at the first recount after the update (about six months, or the end of a war). On an
  older save, the table is replaced by "The board fills at the next recount." until then.
- **Logs.** Read `debug.log`, not `error.log`. Search `TE_SELF_CHECK` for the self-check below, and `Failed to fetch
  variable` and `Data error in loc string` for anything the panel's new reads get wrong.

## Self-checks

| Line | Means | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK ch_board_rows` | At the first recount with a leader, the board store (`ch_board_store`) holds the leader's row and its capital. | — |
| `TE_SELF_CHECK BROKEN ch_board_rows` | A leader with a capital is ranked, but the store lists no row for it, so the table draws nothing. | Restore the ten fixed rows of before (`ch_board_row_sgui` and `ch_board_row_N`, in git history before CH-2) and keep the head; or write the rows on each player's country instead of a parentless store, as `ch_leaders_display_write` writes the seats. |

## The Top Cultural Powers board (CH-2, CH-7)

| Check | Expect | If it fails |
|---|---|---|
| **The table.** Open the Hegemony tab of the Society panel and the journal entry. | A head (#, Country, Share, Change, Model), then one line per country: rank, a small flag, the name, its share, an arrow and a signed change, and a colored swatch. The columns line up under the head. | A blank flag or name: `ScriptContainer.MakeScope.Var('ch_board_capital').GetState.GetCountry` does not resolve inside this datamodel; compare the covert network rows, which read the same chain. |
| **Hovers.** Hover a flag, a swatch, a row and the Change and Model heads. | The flag names the country and opens it on click. The swatch names the model and its laws. The row lists that country's pull components at the recount, only the ones that are not zero, and they add up to its Raw Score with the Pull Multiplier. The heads explain the column. | An empty row hover: a `ch_board_tt_*` fragment did not render through `SelectLocalization` in a datamodel tooltip (gotcha #24); show every line instead. |
| **Us.** With `te_debug_ch.1` put us at rank 1, then outside the top ten. | The arrow marks our row at rank 1. Outside the top ten no row is marked and "Our Rank: 14 of 168" follows the table. | No arrow: the marker's comparison of `ch_board_rank` with `ch_rank_self_display` failed. |
| **A gone country.** Empty slot 5 with the harness, or annex a ranked country between recounts. | Row 5 is gone and the others keep their places; an annexed country's row reads "A country that no longer exists" within a month, with no flag. | |
| **Change.** Let two recounts pass. | Each country's change is against its own share at the recount before (a newcomer to the top ten shows its own change, not the difference from the previous occupant of its rank). | |

## Overview and breakdown

| Check | Expect | If it fails |
|---|---|---|
| **The programs cell (CH-9).** Look under the share pie and the Leading Powers. | One Banking-style box: the Ministry of Culture icon, "Programs", "2 of 4 Running" and "Funding 2 / 5". Without the law: the icon dimmed and "No Ministry" in red. Hover: each program Running or Idle and the funding cost, or the Ministry requirement. | A box drawn at the wrong size or font: `te_banking_ov_cell` from `banking_dashboard_widget.gui` did not reach this file; copy it under a `te_ch_` name. |
| **Type sizes (CH-15).** Read every section at the new sizes. | Rows and values at 17, subheadings at 20, the overview at 16. Nothing ends in "...", the first row's four cells fit side by side, and a long country name in the board wraps rather than elides. | Widen the cell, then re-budget it in `test_cultural_hegemony_layout.LabelBudgetTest`. |
| **The tier hover (CH-5).** Hover the tier icon. | Its full name and blurb, then "Next: Significant from 10% share" (the next tier and its threshold), or "The highest tier." at Hegemon. | |
| **The breakdown (CH-1, CH-3).** With Prestige and a Pull Multiplier, as a major power below the world average standard of living. | The Pull Multiplier closes the components ("+25%", green), then the rule, then Raw Score alone. The Standard of Living row shows a red negative value, and its hover says "Counted at ×0.50 for our rank". | |
| **The funding level (CH-4).** Hover "2 / 5" beside Program Funding. | Funding Level, the maximum, the Ministry of Culture institution and the two technologies that raise it, and the breakdown of where the cap comes from now. | A blank breakdown: `GetValueWithBreakdownFor` failed here; the sentence above it still says how to raise it. |
| **The history legend (CH-12).** Look under the History chart. | Two columns of short names ("Mixed", "Theocratic"), each with its full name and laws on hover, as in the models legend above. | |
