# Banking panel type sizes: play-test list

A Steam Workshop player found the Banking panel's text too small to read. The
panel went up one step in type (2026-10-13): the overview's small text is now
medium, the rows, values, buttons and notes that were medium are now large, and
subheadings are extra large. Nothing here could be seen in game when it landed
(no game install in the build container); it passed the offline gate only
(`test_banking_layout.py`'s width budget, the GUI lint, the audits). Check these
the next time the game is up. Look at both hosts, the journal entry and the
Budget panel's Banking tab, at 100% UI scale and again at the largest scale you
play at.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | Overview, first row (Cycle Phase, Momentum, Bubble Pressure) | Each caption and word reads in full, with no "..." ("Bubble Pressure" is the widest caption; "Stagnation" the widest phase). The range line under each cell (`-10.0 to -10.0` is the widest shape) is not cut and starts under the icon. Cells of unequal width (146, 146, 176) still sit centred, and the range row lines up with the cells above. | Widen the cell in the instance (`size` and `caption_width`) or drop the word to the small type. |
| 2 | Overview, second row (Policy Stance, Inflation, Budget) | "Hyperinflation" and "Policy Stance" fit their cells (168, 160, 132). | As above. |
| 3 | Active Policies and Available Interventions | Every policy name fits its 320 cell; the longest are "Dividend Restraint Resolution" and "Emergency Resource Allocation". The cost icon and its digit sit apart. "Enable" and "Disable" show in full in the 90-wide buttons. | Shorten the name (a `banking_dash_name_*` key) or widen the button. |
| 4 | Monetary Policy, The Rate | Pair rows put Reference Rate and World Rate, Policy Rate and the Target stepper, Credit Standing and Risk Premium, Inflation and Expected, Price Pressure and Wage Pressure side by side with no overlap and values in line. Price Pressure now comes before Wage Pressure. The Target stepper's buttons are not clipped by the row. | Move the long label to the left cell, or give the row to a full-width reading. |
| 5 | Monetary Policy, dial rows | Delegation reads "Delegated", "Direct" or "By mandate" with Delegate or Take Control beside it, in a row no wider than the block. Mandate, Mandate by Law and Takes Effect In line up with the pair rows' values. The four mandate buttons and the Monetise Deficit stepper are not clipped. | Re-check `banking_dash_mon_value` (136) against the 140 button. |
| 6 | Gold, exchange rate and borrowing rows | "World Rate Gap", "Trade and Prices" and "Monetise Deficit" are not elided. Bank's Gold wraps onto a second line when the figure is long rather than being cut. | Wrap the value (`multiline = yes`) or shorten the label. |
| 7 | Common currency buttons (in a bloc with Monetary Union) | Adopt or Leave Common Currency and Press for Convergence or Stop Pressing stack one above the other, each in full. Recapitalise the Bank is in full. | Widen the button. |
| 8 | History charts | Titles (extra large) and legends (medium) wrap and do not push a chart off centre. The Recording Since line and the marker key read. | The font blocks are in `te_history_chart.gui` (`chart_title_font`, `chart_legend_font`, `marker_legend_font`, `crash_legend_font`); the other systems' charts keep the old sizes, so check one of them is unchanged (UN authority). |
| 9 | How Banking Works | The notes (large) wrap inside the 460 column and the subheadings (extra large) stay on one line or wrap cleanly. | Back the notes off to medium. |
| 10 | Budget tab, read-only readout (a country with a dial but no entry) | The note under the readout and the Policy Rate and World Rate pair read in the large type. | |
| 11 | Panel height | The tab still scrolls to its end, and Open Journal Entry stays below everything else. | |

The journal entry's four bars at the top of the overview (`te_je_scripted_bars`)
and the section header buttons keep the game's own sizes, because other systems
share them. If they now look small beside the rows, scale them in their own
change, not here.
