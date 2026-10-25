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
