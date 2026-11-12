# Performance fixes play-test checklist

What the next play-test should look at in the changes made for speed (`docs/audits/late_game_performance.md`). In-game
checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline
gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck
through with the commit that fixed it.

## UN tabling gates, formable pressure, arable land (2026-11-12)

The UN AI buttons ask their `possible`'s cheap gates in `visible` (nothing a player sees), the six regional formables
read external pressure from a monthly global variable, and `same_owner_state_region_arable_land_added` names its state
instead of ROOT (#1703).

| Check | Expect | If it fails |
|---|---|---|
| Formable tooltip | In a game past Decolonization, a regional union's formation (African Union, European Union, …) lists "A great power with its capital outside Africa ranks in the world's top three (checked once a month)", the region's name filled in, ticked or crossed | A raw key: the loc key; "Global variable te_formable_pressure_…": the `custom_tooltip` was dropped |
| Monthly refresh | After a month in any game, the console's `read`/script explorer shows `te_formable_pressure_afu` (and the others) set while a non-African great power is in the top three | Never set: `te_formable_on_actions.txt` is not run by the global `on_monthly_pulse` |
| Arable land breakdown | The states panel's arable land hover gives "from modifiers" above 0 for a state whose region had land added (`arable_land_added` set), in a country other than the player's | 0 everywhere but the player's: the saved state scope is not read in the script value |
| Month-start errors | `error.log` has no `extra_script_values.txt` line at a 1st of the month (about 5,700 before) | The value is still read with an ownerless scope |
