# Nation tab: play-test list

The Nation tab (spec `docs/superpowers/specs/2026-10-17-national-modifiers-tab-design.md`) passed the offline gate
only: `test_nation_tab.py`, `test_te_systems_window.py`, the GUI lint and the audits. What only the game can show is
below, from the spec's § 8. In-game checks don't gate a merge (CLAUDE.md, "In-game checks"); work through these the
next time the game is up.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **Where to look.** The Timeline Extended window (the button under the sidebar's Map List) and the country panel's
  Information tab, for your own country and for an AI's.
- **A save with something to show.** A mid- or late-game country carries the most: agricultural diffusion, a space
  race milestone, a demographic measure, UN conventions, Construction Cost Scaling. To get a timed modifier, force a
  law through with Forceful Legislation.
- **Logs.** Read `debug.log` first, then `error.log`. Search both for `te_nation_generated.gui`,
  `00_te_country_panel_information.gui` and `te_nation_tab.gui`.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | The redefinition wins | The country panel's Information tab: MODIFIERS no longer lists Agricultural Diffusion, the space race's milestones, a demographic measure or Construction Cost Scaling. It still lists a timed modifier (Forceful Legislation's decaying penalty, after forcing a law) and Nuclear Power. The rest of the tab is unchanged. | Vanilla's definition won (gotcha #30 of `gui_modding_guide.md`): replace the whole `country_panel.gui` instead, as the mod replaces `states_panel.gui` (spec § 3). |
| 2 | The header | A country whose every modifier is hidden shows no MODIFIERS header and no gap. One with a kept modifier shows the header and that modifier only. | `gui_country_hidden_modifier_count` and the filter disagree on a name: `test_the_filters_and_counts_name_the_same_modifiers` should have caught it, so look for a modifier added twice. |
| 3 | The lists | Each section lists only its own modifiers. Hovering one shows its tooltip at its current scale: Great Family Fortunes under Wealth Concentration matches the same modifier in the country panel's Modifiers tab. | A section listing every timed modifier means the blockoverride didn't paste the template: have the generator write one list type per section (spec § 8). A tooltip at unit scale means the in-tab render doesn't scale: a script-value line per effect. |
| 4 | The breakdown | Legislative Override Capacity's figure lists, on hover, the laws, the institutions and (after forcing a law) the decaying penalty. | The hover is all that's lost: the figure still reads. Show `te_nation_override_capacity` in the row instead. |
| 5 | The bar and its lines | The fill sits at (capacity + 6) / 14 of the bar. The lines stand at 0, 2 and 4, and each line's hover names its option. The line under the bar names the strongest option open, "Not offered" below 0. | Move the lines (`position` in `te_nation_section_governance`). |
| 6 | Selection | The window opens on Nation. Choose Space Race, close and reopen: it opens on Space Race. With the tax probes armed, the tax tab still selects. | `test_te_systems_window.py`'s `SelectionTest` holds the templates; a failure here is the engine, not the logic. |
| 7 | The launcher | With every system's game rule off, the button still shows, and the window opens on Nation, the only tab on its strip, with no second strip. | No button: the deployed copy is stale (`te_window_launcher_sgui` is gone). A second strip with no tab on it: its `visible` reads the wrong gates. |
| 8 | Parsing | No GUI parse error for `te_nation_generated.gui`, whose country-panel filter is a single `visible` of about 20,000 characters. | Split the filter: move names to `KEEP_IN_LIST`, or break the template into two `visible`s on nested widgets. |
| 9 | Performance | No stutter with the Information tab open on a late-game country, nor with the Nation tab open. | The filter is 233 comparisons a row: move names to `KEEP_IN_LIST` until it is smooth. |
| 10 | The layout | The overview's four boxes read in full in their 154 columns at 100% UI scale and at the largest you play at ("Wealth Concentration" is the widest caption). Science and Space and International draw nothing when they have nothing to show. How the Nation Works opens and closes. | Shorten a caption (`te_nation_ov_*_cap`), with the full name on hover. |
