# Renewable Investment and the Clean Power group: play-test checklist

What the next play-test should look at in the Renewable Investment climate policy and the `bg_clean_power` building
group behind its construction bonus. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the
play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own
section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The Climate panel's policy row for Renewable Investment (needs Clean Energy Technologies and
  0.5 °C of warming; the console's `event te_debug_gw.1` option j adopts all nine policies), the Budget panel's Breakdown tab, and a
  hydro, nuclear, fusion or renewable plant's building panel.
- **Logs.** Read `debug.log`, not `error.log`.

## A fixed running cost and a Clean Power child group (2026-10-20, owner)

Renewable Investment no longer forces subsidies on Renewable Energy Plants. It costs 0.5% of GDP a year
(`renewable_investment_cost_modifier`), gives Renewable Energy Plants +20% throughput and the four clean generators
+25% construction efficiency through their own group `bg_clean_power`, a child of `bg_power`.

| Check | Expect | If it fails |
|---|---|---|
| **Cost line.** Adopt the policy, then open the Budget panel's Breakdown tab. | A Climate Policy row under Programme Costs of about `GDP × 0.005 ÷ 52` a week, matching the sum in the modifier's tooltip. | No row: the budget mirror is missing. A different figure: `gw_renewable_investment_cost_value`. |
| **Repeal.** End the policy. | The row goes at once. | A row that stays until the next month means `gw_effect_remove_renewable_investment` did not remove the cost. |
| **Treaty 109.** Sign Enforce Emissions Reduction as the source. | The row appears (at once, or by the next monthly pulse). | A policy with no cost: `gw_renewable_investment_cost_apply` is not reached in the treaty's `on_entry_into_force`. |
| **No forced subsidies.** Open a Renewable Energy Plant with the policy on. | No "require subsidies" line; the government pays its losses only if the player subsidizes it. | The retired bool still being applied, or a stale save. |
| **Bonus targets.** Hover the policy's modifier, then a Renewable Energy Plant and a coal/oil Power Plant. | The modifier lists Clean Power Construction Efficiency +25% and Renewable Energy Plant throughput +20%. A hydro, nuclear, fusion or renewable plant builds faster; the coal/oil Power Plant does not. | A coal/oil plant also faster means the construction line is still on `bg_power`. No effect on the clean plants means the modifier type or `construction_efficiency_modifier` on the group is not live. |
| **Parent group still reaches the children.** Switch on the banking cycle's Electrification directed-credit sector (`banking_directed_credit_electrification`, `building_group_bg_power_construction_efficiency_add` +10%; needs `rural_electrification`). | A hydro or nuclear plant builds faster as well as the coal/oil plant. | The engine does not pass a parent group's modifier to a child group; every `bg_power` line then needs a `bg_clean_power` twin (`building_group_bg_power_infrastructure_usage_mult`, `building_group_bg_power_throughput_add`, the electrification credit, the vanilla collectivization law line). |
| **Group-level settings unchanged.** Compare a hydro plant's infrastructure usage, economy-of-scale line and auto-expansion with a save from before. | Same as before (2 infrastructure per level; economy of scale as before). | If economy of scale is counted per group, hydro, nuclear, fusion and renewable plants no longer pool with the coal/oil plant in a state: expect a small change, and decide whether it matters. If the new group does not inherit `bg_power`'s other settings (category, auto-expansion, cash reserves), restate them in `bg_clean_power`. |
| **Display.** Open the building browser and a plant's panel. | The four plants list under Clean Power; the modifier line reads "Clean Power Construction Efficiency". | A raw `bg_clean_power` key means the loc is missing. |
