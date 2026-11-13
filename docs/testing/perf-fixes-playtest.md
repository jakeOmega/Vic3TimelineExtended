# Performance fixes play-test checklist

What the next play-test should look at in the changes made for speed (`docs/audits/late_game_performance.md`). In-game
checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline
gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck
through with the commit that fixed it.

## UN tabling gates, arable land (2026-11-12)

The UN AI buttons ask their `possible`'s cheap gates in `visible` (nothing a player sees), and
`same_owner_state_region_arable_land_added` names its state instead of ROOT (#1703). The harness run of 2026-11-12
(snapshot `20261112T183036Z`) already saw the arable land value read above 0 for a state of another country and no
month-start errors; the panel itself was not looked at.

| Check | Expect | If it fails |
|---|---|---|
| Arable land breakdown | The states panel's arable land hover gives "from modifiers" above 0 for a state whose region had land added (`arable_land_added` set), in a country other than the player's | 0 everywhere but the player's: the saved state scope is not read in the script value |
| Month-start errors | `error.log` has no `extra_script_values.txt` line at a 1st of the month (about 5,700 before) | The value is still read with an ownerless scope |
