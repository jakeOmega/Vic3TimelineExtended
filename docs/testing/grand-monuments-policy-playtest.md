# Grand Monuments: the monument policy, upkeep and prestige, play-test checklist

What the next play-test should look at for the policy pass (spec
`docs/superpowers/archive/specs/2026-10-23-gm-policy-prestige-design.md`, plan
`docs/superpowers/archive/plans/2026-10-23-gm-policy-prestige.md`). In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): the PR lands on the offline gate and this is what only the game can show.
A fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work".
- **Start a game in 1836** with the Grand Monuments rule on, as Egypt (seven steps of standing grandeur, no regime
  monuments) or Greece (the Parthenon). Keep a save from a game before this change for the rank comparison.
- **Logs.** Read `debug.log`; grep `TE_SELF_CHECK` and `TE_MONUMENTS`.

## Self-checks

| Line | Means | If BROKEN, take the fallback |
|---|---|---|
| `TE_SELF_CHECK OK/BROKEN gm_education_reaches_states` | Once a game, a month after a country under Public Education with at least one step first had `gm_national_education` on its journal entry: OK when a state of that country reads the education access the modifier gives. The line prints both numbers. | The engine doesn't pass a JE-held modifier's `state_*` field to the states. Add `gm_national_education` to the country instead of the JE (`gm_apply_national_modifiers`), give it its own row in `scripts/generators/gen_nation_tab.py`, and check the three signatures with `state_*` fields (Liberty, the Olympic Ideal, Heroes of the Nation) the same way. |

## Checks

| Check | Expect | If it fails |
|---|---|---|
| **Prestige.** As Egypt on 1 January 1836, hover the Prestige rows in National Effects. | Prestige +70 and Prestige (%) +7%, on seven steps. | The old +25 a step: `gm_national_prestige` or its pair. |
| **Ranks.** Run to 1846 and compare Egypt's and Persia's rank with the older game. | Neither climbs higher than before on monuments alone. | Note both ranks and their prestige. |
| **No upkeep.** Open a finished monument's building. | It uses no construction for maintenance under every policy. | `gm_upkeep`'s multiplier didn't resolve to −1. |
| **The buttons.** Open National Effects. | Four buttons, two to a row: Open to the Public, State Ceremonial, Cultural Promotion, Public Education. Cultural Promotion is greyed as the policy in force on a new game. | |
| **Ceremonial without regime monuments.** As Egypt, choose State Ceremonial. | The Legitimacy and Authority rows appear: a quarter of Egypt's grandeur, about 35, gives about +4 legitimacy. Their hovers name the ceremonies' share, and their bars fill against it. | No row: `gm_g_regime_in` didn't reach the curve. An empty bar beside a bonus: a display still reads `gm_g_regime`. |
| **Open.** As Greece, choose Open to the Public. | The state card's Monuments tourism figure, and Antiquity's tourism, rise by half the next month. | Antiquity's unchanged: the `FACTOR` argument. |
| **Cultural Promotion.** Watch the Cultural Pull row on the default policy. | Half again what it shows under Open, Ancestral Antiquity's too. | |
| **Cultural Hegemony off.** Start a game with that rule off and stay on Cultural Promotion. | The Prestige rows read half again (Egypt +105 and +10.5%); cultural pull rows don't change. | |
| **Public Education.** Choose it. | An Education Access row appears in National Effects, and every state's education access rises by it. Switch away and the row goes. | Read the self-check above. |
| **An older save.** Load a save whose country was on Mothballed, mid-wait. | It reads Cultural Promotion, and the buttons stay greyed for what was left of the wait. | |
| **The AI.** Run ten years and look at a few AI countries' policies. | Low-legitimacy AIs on State Ceremonial, AIs with a Tourism Industry beside a monument on Open, low-literacy AIs on Public Education, the rest on Cultural Promotion. | |

## The panel after the GUI audit (2026-10-27, issue #1210)

The Grand Monuments panel's rework from the GUI and localization audit (`docs/audits/gui_audit/monuments_colonial.md`,
GM-1 to GM-17). Nothing here was seen in game. Check it on the journal entry and on the Grand Monuments tab of the
Timeline Extended window, which compose the same types.

| Check | Expect | If it fails |
|---|---|---|
| **The overview's four cells** (owner, 2026-10-27: Banking's cells, `te_banking_ov_cell`). | Our Monuments, Contested, Sites and Hard Times, two to a row, each icon dimmed at zero; Contested and Sites read red while one waits on us ("2 to decide", "1 to dedicate"), Hard Times red while it holds, with "Pause building" under it. No caption or word ends in "...". | A word elided: shorten its loc (`gm_je_ov_*`); `LabelBudgetTest.test_overview_captions` budgets 16 characters. A blank icon: `gm_ov_icon`'s two icons fill the cell's 44 box. |
| **Awaiting a Decision.** Change the law a monument honours (a crown under a republic). | A section under the Opportunity, only while a monument is contested, with its row and the three choices; Our Monuments no longer lists it. A contested monument beside another lists here too, with its three. | The section stays hidden: `gm_disp_count_contested` is above zero but the datamodel items' `visible` reads the status wrong. |
| **The choices' figures** (GM-4). Hover Pull Down, Rededicate and Keep as Heritage on a contested row. | Pull Down gives legitimacy now (green) and the two groups' approval changes; Rededicate its halved levels and grandeur and the old supporters' loss; Keep as Heritage says the approval does not change now. After Pull Down, Fading Legitimacy's row and the two groups' approval rows move by about the figures shown. | Zeros on every line: `gm_preview_choices` did not run (its marker skips it inside a tooltip walk; the monthly refresh and every choice run it). Figures far off: compare `gm_prev_*` on the state with the ledgers in `debug.log` (`TE_MONUMENTS`). |
| **The policy buttons** (GM-2). Hover each of the four. | The policy's effect as the engine's coloured line (Tourism from Each Monument +50%, and so on), the To History line under it, and no timing; the timing on the Monument Policy heading's hover. The overview's policy line gives the same lines. | A raw `country_gm_monument_*` key or no line: the `script_only` types in `gm_policy_modifier_types.txt` do not render through `GetStaticModifier(...).GetDesc` on a modifier no country carries. Fall back to the policy's own prose line in each `gm_policy_*_effect_tt`. Until 2026-10-29 the types were named `gm_monument_*`, which the engine flagged at load (`Invalid category prefix` in error.log), so a test before that date does not count. |
| **Interest group rows** (GM-13). Hover a group under Interest Group Approval. | Its approval, then the grandeur of the monuments it approves of, those it objects to, the contested ones it resents and its fading record; the heading's hover explains totals once. | All zeros on a save from before the change: the parts are written by the next refresh (`gm_compute_ig`). |
| **Type sizes** (GM-17). Rows 17, headings and titles 20, the overview 16. | Nothing clips: the choice buttons (Keep as Heritage), the status word under a picture (Undedicated), the Short view's Bring It Home, the trophy card's three view buttons. | Widen the cell the budget test names. |
| **Held Abroad rows** (GM-10). Hover "Held by" on a trophy taken from us, at war with its holder and at peace. | At war: occupy its state and carry it off. At peace: the Return Cultural Property article, or wait. | The hover always says peace: `Country.IsAtWarWith( GetPlayer.Self )` does not resolve on `Var('gm_tr_site').GetState.GetOwner`; drop the line and keep the section's own hover. |
| **Carry It Off's infamy** (GM-11) on a trophy on display and on a monument beside another. | The figure on hover matches the infamy gained. | Off by the form's share on a secondary: `gm_mon_disp_take_infamy` reads `gm_mon_tr_start` and `gm_mon_tr_age`. |
| **Archaeology** (GM-14). | Digs Under Way and Open Sites as headings over their rows; an abroad line's hover names its treaty article, the permit's with Foreign Scholarship's lines; How Grand Monuments Work has an Archaeology topic. | — |
