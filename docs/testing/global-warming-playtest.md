# Global Warming panel play-test checklist

What the next play-test should look at in the Global Warming journal entry's panel and the Market panel's Climate
tab. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands
on the offline gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed
item is struck through with the commit that fixed it. The Renewable Investment policy's cost and building group have
their own list, `renewable-investment-playtest.md`.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The journal entry (needs Pollution Control and the entry running), and the Market panel's
  Climate tab on your own market and on another. The console's `event te_debug_gw.1` sets warming and adopts
  policies.
- **Benches.** A market leader and a member of another country's market; a game past its first January, so the
  yearly figures exist.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `TE_SELF_CHECK`.

## The GUI audit wave (2026-10-27)

The audit's findings GW-3 to GW-16 (`docs/audits/gui_audit/climate_reserve_market.md`). Offline,
`test_global_warming_layout.py`, `test_gw_top_emitters.py`, `test_country_climate_policies.py` and
`test_gw_policy_tech_gates.py` hold the layout, the list, the widths and the loc.

### Self-checks

| Line | Where | OK means | If BROKEN |
|---|---|---|---|
| `TE_SELF_CHECK OK\|BROKEN gw_top_emitters_list rows=… expected=… rises=…` | `gw_top_emitters_selfcheck`, once a game, the first time a player's Top Emitters list is built with an emitter in the world (`global_warming_effects.txt`) | The list holds min(5, emitters) capitals, and no country's emissions rise down the list. | `rows` short: an emitter without a capital, or `ordered_country`'s `max` not counting from the top. `rises` above 0: the list does not keep the order it was built in. Fallback: the slot rows from before GW-11 (five `gw_emitter_<n>` variables and a row each, `gw_top_emitter_slot`), from the git history of `global_warming_widget.gui` and `global_warming_effects.txt`. |

### Checks

| Check | Expect | If it fails |
|---|---|---|
| **Top Emitters rows.** Open Top Emitters after the first January. | Five rows, largest first, each with the country's name, flag and figures; a row for your country reads "Our country". | No rows: the datamodel over `GetList('gw_te_top')` drew nothing; check the self-check line, then the variable list in a plain-text save. Rows with no name or zeros: `Scope.GetState` as the item's datacontext failed; the fallback is the slot rows (above). "Our country" missing: `State.GetCountry.IsLocalPlayer`. |
| **Top Emitters hovers.** Hover a row, a heading, and "+N more countries". | The row's figures, cut and market; the heading's note; the next 25 emitters below the five, with a line naming how many are left past them. | A row hover that names the wrong country: the tooltip sees the item's datacontext (gotcha #24). A "+N more" list that starts with the five: `gw_emitters_fifth_emis` not stored. |
| **Overview cells.** Read the first two rows of the overview, then on another market's Climate tab. | Warming (tier icon, word, next threshold), Warming Penalty (standard of living and mortality at today's scale), Market (Leader or Member), and Treaty while one binds you. Text at 16, nothing elided. On another market the Market and Treaty cells are its leader's. | A cell's text cut short: widen it or shorten the key. Wrong figures in the penalty cell: compare with the hover's modifier lines × the multiplier (`gw_disp_penalty_sol`, `_mortality_pct`). |
| **Penalty hover.** Hover Warming Penalty. | The multiplier in force, then every line of the Climate Warming modifier at its 1 °C value; the cell's two figures are those lines times the multiplier. | A cell figure that is not line × multiplier: `gw_disp_penalty_sol` / `_mortality_pct` have drifted from the modifier (`PenaltyCellTest` should have caught it). |
| **Repeal hovers.** Hover Repeal on Carbon Tax and on Renewable Investment. | "Ends:" and the policy's modifier lines (in their adopt colors); Renewable Investment also names its running cost. | Raw `[GetStaticModifier…]` text: the key is wrong. |
| **Adopt hover's cost.** Hover Adopt on Renewable Investment. | The running cost's modifier line under the policy's description. | No line: the cost is applied where the tooltip doesn't show it (`gw_effect_renewable_investment`). |
| **Radicalism line.** With Carbon Tax in force and the Environmental Movement present, hover the policy row's name, then the movement's radicalism. | The policy's modifier list includes Environmental Movement Radicalism −10%; the movement shows one "Climate policies in force" line equal to the sum of the policies in force. | No line in the movement: `modifier:country_environmental_movement_radicalism_add` reads 0 there (a `script_only` country modifier not visible in the movement's scope); fall back to the eight `has_modifier` branches from before GW-3 (git history of `new_ideological_movements.txt`). |
| **Hidden in-force condition.** Hover Adopt and Repeal on any policy. | The first line is a real condition, not "The policy is (not) already in force". | The `hidden_trigger` did not hide it. |
| **Type sizes.** Read the policy rows, the emissions table and Top Emitters at 1080p. | Rows and values at 17, subheadings at 20; nothing ends in "...". | Note the cell and its text; the width tests' budget is wrong for that face. |
| **GW-12's icons (icon batch 7).** Look at the Fossil-Fuel Tariffs and Carbon Removal Support rows. | Fossil-Fuel Tariffs shows a striped barrier gate over a coal wagon, Carbon Removal Support a pale intake tower with a blue hose coiled into a mound of earth, each dimmed while out of force and unlike its neighbors. | A magenta square: the texture path is wrong or the DDS is missing (`docs/systems/global_warming_gui_icons.md`). |

## The AI answers the Environmental Movement (2026-11-15)

The movement's activism now pulls an AI country toward the climate policies its "could adopt" lines count: from 50%
activism (protesting) to 75% (militant), up to 30 points on the one policy the country can carry now and is nearest
to adopting anyway, at most one answer a year (`gw_ai_movement_pressure` in `global_warming_ai_values.txt`).
Offline, `test_gw_ai_movement_pressure.py` holds the wiring and a weekly model of activism and the buttons with no
adopt-repeal cycle. No self-check: the engine facts it rests on are already used elsewhere (a movement's activism
read as a value, `min =` over named script values, a timed variable).

**Bench.** An AI-observer run to about 2017, from `main` before this change (the R2 run of 2026-11-07,
`/mnt/d/vic3te-data/demog-runaway-sign5-2026-11-07/saves/`) and after it. `event te_debug_gw.1` option **l** writes
three `GW_AI_WILL` lines a country to `debug.log`; the third is the movement's.

| Check | Expect | If it fails |
|---|---|---|
| **Holders in 2017.** Count the AI countries holding each of the seven in a 2017 save. | Before (R2, 2017.1.1, 205 AI countries with the entry): Climate Adaptation 23, Reforestation 31, Public Transit 3, Carbon Tax 1, the rest 0. After: more Climate Adaptation, Reforestation and Renewable Investment. A five-year model of the R2 save puts the movement's share at about 22 more countries if every authority and technology gate is open (25 adopt, against 3 on their own will alone), and 9 if only the Carbon Tax is in reach. | None more: read the third line for pressing movements. `pressure` 0 at 50% activism or more: the movement's activism is not read in country scope. `nearest_margin` -1000: no policy passes `gw_ai_can_answer_*` (authority, technology). |
| **Activism falls.** The median activism of AI countries' Environmental Movements, 2017 save. | Before: 0.52, with 27 of 52 movements at 50% or more and 9 at 75% or more. After: lower, and few left at 75%. | Activism unchanged with more holders: the policies' -10% radicalism lines are not reaching the movement (the Radicalism line check above). |
| **No back and forth.** Pick three AI countries that adopted a policy after 50% activism; watch them ten years (the journal entry's policy rows, or the save). | Each keeps what it adopted while the movement is present. | A policy repealed within a few years of its adoption with warming unchanged: check the hold below. Renewable Investment repealed once the country defaults or its debt passes a quarter of the ceiling is expected, where the movement alone held it. |
| **The hold reads the policies' modifier.** The third line for a country holding exactly one of the seven, neither Carbon Removal Support nor Aerosol Injection, with `pressure` between 0 and 0.2. | `unmasked` = `pressure` + 0.8: the policy's −0.10 radicalism and its +0.10 line, both added back. Both values clamp at 0 and 1, so outside that case they can match without anything wrong. | `pressure` + 0.4: `modifier:country_environmental_movement_radicalism_add` reads 0 in country scope, so only the line is added back and the hold is half as strong. Fallback: count the policies' own `has_modifier` (or `gw_policy_*_active`) times 0.10 instead of reading the modifier. |
| **Once a year.** The third line for a country with a pressing movement, the month after an adoption. | `answered_this_year=1` for 365 days, and no second adoption from the movement in that time. | Two adoptions inside a year: `gw_ai_movement_answered` is not set by the button's effect, or a timed variable doesn't expire as written. |
