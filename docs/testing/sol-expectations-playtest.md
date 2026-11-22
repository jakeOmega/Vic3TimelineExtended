# SoL Expectations play-test checklist

What the next play-test should look at in SoL Expectations (`docs/systems/mod_systems/sol_expectations.md`). In-game
checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline
gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck
through with the commit that fixed it.

## Each class's shift read once (#1724)

`sol_expectations_apply_strata_shifts` stores each class's shift in `sol_expectations_<class>_shift_applied`, and the
three strata modifiers take `multiplier = var:…` from it, where they took the script value before.

| Check | Expect | If it fails |
|---|---|---|
| **The modifiers' size.** A country a few years in with a sizeable shift (`read "var:sol_expectations_shift"` above 1): its modifiers list, or a state panel's expected SoL breakdown per stratum. | Each strata modifier's expected SoL equals its class's `var:sol_expectations_<class>_shift_applied` (to rounding), not 1. | Exactly 1 for every class: the multiplier read the variable against the wrong ROOT (`scripting_best_practices.md`, "`add_modifier { multiplier = var:X }` Resolves Against ROOT"); the monthly country pulse should be the only caller. |
