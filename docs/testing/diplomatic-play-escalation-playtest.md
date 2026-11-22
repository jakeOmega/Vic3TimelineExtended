# Diplomatic play escalation play-test checklist

What the next play-test should look at in the mod's extra diplomatic-play escalation. In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the
game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that
fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **A play with extra escalation.** The extra comes from late technologies, the Rules of War laws and a few principles
  (`docs/player_guide/09-diplomacy.md` § "Diplomatic play escalation"). For a quick one, enact Total War (Chemical
  Warfare) and start a play: +25% of the base rate in plays you start.
- **Where to look.** The play's escalation bar in the diplomatic play panel, and its "Escalation paused for N day(s)"
  line after each demand or sway.
- **Logs.** Read `debug.log`, not `error.log`.

## The extra stops while escalation is paused (2026-11-11)

Vanilla pauses a play's escalation for some days after each demand or sway (5 a maneuver, up to 20). The mod's weekly
extra now counts the play's own rise since the last tick as the days it escalated, and adds the week's figure times
those days over 7 (`st_dp_play_apply_weekly_escalation`, `common/scripted_effects/dp_escalation_effects.txt`). It rests
on two engine facts nobody has seen: that a diplomatic play keeps a variable (`te_dp_esc_mark`) from one tick to the
next, and that `escalation >= N` reads in a script value (`te_dp_escalation_now`, a ladder of a hundred comparisons).
Offline, `test_dp_escalation_pause.py` pins the shape and replays the arithmetic.

| Check | Expect | If it fails |
|---|---|---|
| **Self-check.** Run a year with a few plays under way, then search `debug.log` for `TE_SELF_CHECK`. | `TE_SELF_CHECK OK dp_esc_pause now=… mark=… days=… week=…`, once: `days` 7 or near it for a play that escalated all week. | See the Self-checks table. |
| **Paused, no extra.** With Total War, start a play and make demands or sways so the bar reads "Escalation paused" for a week. | The bar doesn't move while paused, the mod's extra included. | A jump of the week's extra on a paused week: the mark isn't kept or the ladder reads wrong (Self-checks). |
| **Unpaused, the extra.** Let a play run a week with no maneuver. | About 7 points from the base game plus the week's extra (+2 a week under Total War's 25%, rounded). | No extra at all on an unpaused week: the ladder reads 0, and the self-check's BROKEN ladder line should say so. |
| **The target's extra.** A play against a country whose laws add defender escalation (Total War) moves faster than one against a country without. | The target's extra lands at the initiator's tick. | None: `every_scope_play_involved` leaves out the target; find it by the play's `target` link instead. |

### Self-checks

| Line | Means | Fallback |
|---|---|---|
| `TE_SELF_CHECK OK dp_esc_pause` | A play kept its mark from the last tick and the ladder read it. | None needed. |
| `TE_SELF_CHECK BROKEN dp_esc_pause ladder` | Twenty ticks on marked plays read escalation 0: the comparator doesn't read in a script value. The game falls back by itself to the flat weekly add of before (`te_dp_esc_flat`). | Read the escalation another way (`escalation > N` in a scripted trigger per point, or the play's war-goal timers), or keep the flat add. |
| `TE_SELF_CHECK BROKEN dp_esc_pause mark` | Twenty ticks found no mark and none ever did: a play keeps no variable, so each tick reads its play as new (at most a week's extra, about the old flat add once a play passes 7). | Keep the mark on the initiator country (one play at a time), or a global variable list keyed by the play. |
