# Banking panel type sizes: play-test list

A Steam Workshop player found the Banking panel's text too small to read. The
panel went up one step in type (2026-10-13). The owner's pass of 2026-10-17
settled it: rows, values, buttons and notes at 17, subheadings and chart titles
at 20 (the `banking_dash_fontsize_*` templates), and the overview at 16, as six
boxed cells two to a row, each with its icon in an inset box beside three
lines. The owner saw the overview in game in the Banking tab at 100% UI scale
while that pass was made (rows 1 and 2 below held there). The rest passed the
offline gate only (`test_banking_layout.py`'s width budget, the GUI lint).
Check these the next time the game is up. Look at both hosts, the journal entry
and the Budget panel's Banking tab, at 100% UI scale and again at the largest
scale you play at.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | Overview cells | Each caption, word and third line reads in full in its 154 column, with no "..." ("Bubble Pressure" is the widest caption; "Hyperinflation" and "Stagnation" the widest words; `-10.0 to -10.0` the widest range). The six boxes line up in two columns, and every icon is centred in its inset box. | Shorten the caption, with the full name on hover, before narrowing the gap after the icon (x 78). |
| 2 | Overview, the third lines | A range keeps its own hover breakdown, apart from the cell's tooltip. Budget's "used" plus "free" equals the budget your laws give (Active Policies' costs add up to "used"; while overdrawn, "free" is negative). Policy Stance's Rate and Inflation's "a year" match the Policy Rate and Inflation rows in Monetary Policy. | Used is `banking_display_points_total` less free; a source of points missing from the total shows here first. |
| 2a | Overview, lone row-3 cell (the monetary layer without a dial, so Inflation but no Policy Stance) | The Inflation box sits in the left column, not centred. With neither shown (no monetary layer), the overview ends after Budget with no gap. | Wrap row 3 in a 480-wide widget and anchor the flowcontainer left. |
| 2b | Crash-risk badge (cycle value 90+, or a Boom or Frenzy with momentum Surging or Overheating) | The warning badge sits on the bubble icon's inset box, at its top-right corner. | Move `position = { 46 5 }` in the bubble cell's badge. |
| 2c | Momentum icon | Vanilla's trend arrows are smaller art than the banking set; at 44 the Steady dash may look thin. | New art (icon pipeline), not a size change. |
| 3 | Active Policies and Available Interventions | Every policy name fits its 320 cell; the longest are "Dividend Restraint Resolution" and "Emergency Resource Allocation". The cost icon and its digit sit apart. "Enable" and "Disable" show in full in the 90-wide buttons. | Shorten the name (a `banking_dash_name_*` key) or widen the button. |
| 4 | Monetary Policy, The Rate | Pair rows put Reference Rate and World Rate, Policy Rate and the Target stepper, Credit Standing and Risk Premium, Inflation and Expected, Price Pressure and Wage Pressure side by side with no overlap and values in line. Price Pressure now comes before Wage Pressure. The Target stepper's buttons are not clipped by the row. | Move the long label to the left cell, or give the row to a full-width reading. |
| 5 | Monetary Policy, dial rows | Delegation reads "Delegated", "Direct" or "By mandate" with Delegate or Take Control beside it, in a row no wider than the block. Mandate, Mandate by Law and Takes Effect In line up with the pair rows' values. The four mandate buttons and the Monetise Deficit stepper are not clipped. | Re-check `banking_dash_mon_value` (136) against the 140 button. |
| 6 | Gold, exchange rate and borrowing rows | "World Rate Gap", "Trade and Prices" and "Monetise Deficit" are not elided. Bank's Gold wraps onto a second line when the figure is long rather than being cut. | Wrap the value (`multiline = yes`) or shorten the label. |
| 7 | Common currency buttons (in a bloc with Monetary Union) | Adopt or Leave Common Currency and Press for Convergence or Stop Pressing stack one above the other, each in full. Recapitalise the Bank is in full. | Widen the button. |
| 8 | History charts | Titles (20) and legends (medium) wrap and do not push a chart off centre. The Recording Since line and the marker key read. | The font blocks are in `te_history_chart.gui` (`chart_title_font`, `chart_legend_font`, `marker_legend_font`, `crash_legend_font`); the other systems' charts keep the old sizes, so check one of them is unchanged (UN authority). |
| 9 | How Banking Works | The notes (17) wrap inside the 460 column and the subheadings (20) stay on one line or wrap cleanly. | Change `banking_dash_fontsize_row` or `_heading`. |
| 10 | Budget tab, read-only readout (a country with a dial but no entry) | The note under the readout and the Policy Rate and World Rate pair read in the row type (17). | |
| 11 | Panel height | The tab still scrolls to its end, and Open Journal Entry stays below everything else. | |

The journal entry's four bars at the top of the overview (`te_je_scripted_bars`)
and the section header buttons keep the game's own sizes, because other systems
share them. If they now look small beside the rows, scale them in their own
change, not here.
