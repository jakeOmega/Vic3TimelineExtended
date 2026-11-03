# Full-screen charts, Help pages and National Info: play-test checklist

What the next play-test should look at for the charts, Help and National Info work (spec
`docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md` § 9). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the
game can show here. Each PR adds its own section, and a fixed item is struck through with the commit that fixed it.

## The panel's charts look as before (PR C1, the chart registry, 2026-11-02)

The 33 history charts are generated now: each section instances its chart's wrapper, `te_hist_<id>` in
`gui/te_history_charts_generated.gui`, where the chart was. Offline, every chart rendered byte for byte as its section's
instance had it, so nothing should look different. Logs: read `debug.log` and search it for `te_hist_` and
`te_history_chart`.

| Check | Expect | If it fails |
|---|---|---|
| **Each history section, both widths.** Banking (the Budget tab and the journal entry), the Strategic Reserve (expand a good's row), Demographics, Cultural Hegemony, Nuclear Weapons (the taboo's history), the United Nations, Global Warming and the Colonial Empire, in the side panel and in full screen. | As before: the same charts in the same order with the same gaps, each centered in its section, its bars, hovers and range buttons working. | A shift or a new gap: the wrapper carries only `parentanchor = hcenter` around the chart. Compare the section with its text before C1 (`git show 855689f14:<file>`). |
| **Banking's paired and hidden charts.** A country on a digital currency and one not; then a game with `banking_system_simplified`. | One policy-rate chart at a time, with no empty gap where the other was; under the simplified system, no inflation or exchange-rate chart and no gap. | A gap: the chart's `visible` must sit on the section's wrapper instance (`te_hist_mon_policy = { visible = … }`), not inside it. |
