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

## The shift's ceiling raised from 50 to 200 (#2147)

`sol_expectations_shift_clamped_value` caps the shift at 200, the mod's top wealth level, where it capped it at 50. An
old save's shift was stored clamped at 50 and climbs from there at the usual rate. Best read in the owner's
all-technology USA save (`te_qa_copy_iua2050_20261126.v3`, lower strata SoL 124, middle 131, upper 133) and one of its
subjects (ARA or CST, SoL about 70), ten in-game years apart.

| Check | Expect | If it fails |
|---|---|---|
| **The shift climbs.** `read "var:sol_expectations_shift"` and `read "var:sol_expectations_gap_cached"` on load, after a year and after ten. | The shift starts at 50 and rises, by roughly 5 a year at first, and the cached gap shrinks (about half of it in ten years). No jump on load. Algorithmic Governance's mandate stays at +40 until the gap is under 8, decades from a USA-sized gap. | The shift stays at 50: the ceiling still binds; check `modifier:country_sol_expectations_shift_max_add` and the clamp in `extra_script_values.txt`. |
| **Wages.** The USA's normal wage and the wages of a few large buildings (a services building, a factory) on load and after ten years, against a copy of the save run the same ten years on the old ceiling. | Wages no higher than on the old ceiling while SoL holds or grows: buildings aim at 0.67 of expected SoL (`BUILDING_WAGES_EXPECTED_SOL_TARGET_FACTOR`), which stays below what pops have. | Wages run clearly above the old ceiling's, or buildings go unprofitable chasing them: the target reads expected SoL some other way. Fall back to a lower ceiling, or to one raised in steps with era 12 and 13 technology (#2147's other options). |
