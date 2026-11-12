# Rules of War play-test checklist

What the next play-test should look at in the Rules of War law group. In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The law's enactment preview (hover the law in the Politics panel before enacting), and the country's
  infamy in the Diplomacy panel before and after the law takes effect.
- **Unlocks.** Total War needs Chemical Warfare, War Crimes Forbidden Wargaming, Humanitarian Regulations Nuclear
  Weapons and Limited War ICBMs.
- **Logs.** Read `debug.log`, not `error.log`.

## Infamy charged when a law takes effect

Each law's `on_activate` calls `te_row_charge_infamy` (`common/scripted_effects/rules_of_war_effects.txt`) with its
standing: Total War +25, Traditional 0, War Crimes Forbidden −10, Humanitarian Regulations −15, Limited War −20. Infamy
moves by the difference from `te_row_infamy_standing`, the standing last charged (0 when unset): the full difference
toward a looser law, 90% of it rounded down toward a stricter one. Offline, `test_rules_of_war.py` pins the standings
and replays the arithmetic; the checks below are what only the game shows.

| Check | Expect | If it fails |
|---|---|---|
| **Preview.** On Traditional, hover Total War. | An infamy line of +25 among the enactment effects. | The `change_infamy` line doesn't render from `on_activate`: add an `on_enact` `custom_tooltip` naming the change (computed from the same variable). |
| **Charge.** Enact Total War and read infamy before and after. | +25, once, on the day the law takes effect. | If it never moves, `on_activate` didn't run the effect: check `debug.log` for a script error on `te_row_charge_infamy`. |
| **Cut.** From Total War, enact Traditional (preview −22, then infamy). Then Limited War from Total War (−40), and Limited War from Humanitarian Regulations (−4). | The previews and the moves match, in whole numbers. | A −23 or −5 (−45: no cut share at all) means the rounding isn't toward zero: check `floor` on the fixed-point product. Any other figure: a stale `te_row_infamy_standing`; read the country's variables in a plain-text save. |
| **Game rule and Limited War's −25% infamy.** Repeat the charge with the `infamy_generation` rule off its default, and Total War to Limited War with and without Limited War's own modifier in force. | Whether either scales a script `change_infamy` is undocumented. Record what you see here. | Nothing to fix if they scale it: the standings then read as base values. |
| **Game start.** Start a new game; read a few countries' infamy on the first day. | 0 everywhere: the history's Traditional activation charges 0. | If any country starts with infamy from this, the history's `activate_law` ran the effect with a non-zero standing. |
| **Law in force.** Hover the Rules of War law you already hold. | No infamy line: a change of 0 takes neither branch. | Cosmetic. |

## Harness run, 2026-11-11 (1.15.1)

Run through `python3 -m game_qa` on a fresh 1836 game; figures and run folders in `docs/testing/game-qa-results-2026-11-11.md`.

**Charge** and **Cut** read OK (+25, −22, −40, +5, −4, in whole numbers). **Game start** is BROKEN: every country starts with 3 infamy (#1595; the start-date gate below is the change for it, re-check it there). The preview, the `infamy_generation` rule and "Law in force" were not run.

## No charge at game start or for a country made mid-game (#1595)

`te_row_charge_infamy` now charges nothing on the start date (`game_date > 1836.1.1`) or for a country holding no
standing yet, and records the standing either way; Total War stays the group's first law (owner, 2026-11-12). A monthly
backfill (`te_row_backfill_standing`, `common/on_actions/te_rules_of_war_on_actions.txt`) records the standing of the
law held by a country that has none after the start. The **Game start** row above is the check for the first half.

| Check | Expect | If it fails |
|---|---|---|
| **Game start.** As above: read infamy on the first day of a new game. | 0 everywhere, and every country holds `te_row_infamy_standing` = 0 (Traditional). | Still 3: the setup or history activation falls after 1836.1.1. Gate instead on a global set in `on_game_started`. |
| **Self-check `row_standing_on_creation`.** Release a country (or let a revolution or decolonization make one) and read `debug.log` within a month. | `TE_SELF_CHECK OK row_standing_on_creation`: the new country's first law ran `on_activate` with no standing and was charged nothing. | `BROKEN`: the engine gave it its laws silently, and the monthly backfill recorded the law it held. Nothing to fix; the no-standing gate is then idle. |
| **New country's infamy.** Read the released country's infamy on its first day, with its origin on Traditional and again on Total War. | 0 in both (before, 3 and 25). | Non-zero: some other law activation charged it; read its variables in a plain-text save. |
| **Its first real change.** Have that country enact Total War. | +25, as for any country on Traditional. | 0: it held no standing when the law took effect (the backfill missed it); read its variables. |
