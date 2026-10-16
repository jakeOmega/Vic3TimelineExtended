# AI economy play-test checklist

What the next play-test should look at in the AI's budgets and production-method choices. In-game checks do not gate a
merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what
only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the
commit that fixed it.

## How to run

- **The run.** The late game's subsidy bill needs the late technologies, so use the 4× fast run from
  `docs/superpowers/specs/2026-10-12-demographics-fast-mode-revenue.md` §4: a new 1836 game, observed, `event
  te_debug_demog.1` option h on day 1, plain-text yearly autosaves (debug mode), to about calendar 1905. A normal-speed
  observer run reaches the same buildings between 1990 and 2030.
- **Reading a save.** Each record under `building_manager` carries `building=`, `production_methods={ … }`,
  `subsidized=yes` (the chosen flag only), `balance_subsidies=` and, while it retools, a `pm_retooling` timed modifier.
  Compare a building's `production_methods` between two yearly saves (the record id is stable) to count switches. The
  baseline below came from scratch scripts that did exactly that on Fast A's 1911 and 1912 saves
  (`/mnt/d/vic3te-data/vic3te-demog-fast4x-2026-10-10/`).

## Power plants pick their base method by output (#933)

`pmg_base_building_power_plant` takes `ai_selection = most_productive` (`common/production_method_groups/extra_pm_groups.txt`),
as vanilla gives the port and railway base groups. Baseline, Fast A before the change:

| Measure | 1912 save |
|---|---|
| Share of the world's `balance_subsidies` on power plants | 57% (railways 33%, ports 8%) |
| AI power plants carrying `pm_retooling` | 443 of 630 (70%); railways 38%, ports 29% |
| Retooling plants' share of the power-plant subsidy | 92% |
| Plants that changed a method from 1911 to 1912 | 147 of 623; the base group about 70 (both ways), automation about 28, carbon capture about 20 |
| Plants on Early Power Plant | 203 of 630 |
| Bankrupt countries (`declared_bankruptcy`) | 148 of 244 |

| Check | Expect | If it fails |
|---|---|---|
| **Base-group churn.** Diff two consecutive yearly saves late in the run (calendar 1900 on). | Base-group switches mostly upward (to a newly unlocked method) or away from a short input; few back down to Early Power Plant. Base switches well under the baseline's 70 a year. | Downgrades as frequent as before mean the engine isn't reading the INJECTed `ai_selection`: check `debug.log` for the group, then try a `REPLACE:` of the group. |
| **Retooling share.** Count power plants with `pm_retooling` in the 1904 and 1912 saves. | Well under 70%, nearer the railways' and ports' share. | If the base group is quiet but the share stays high, the automation and carbon-capture groups carry the churn: count their switches before choosing a lever. |
| **Subsidy bill.** Power plants' share of `balance_subsidies`, and subsidies as a share of income (the note's §4 slot map). | Power plants' share well under 57%; fewer bankrupt countries than the baseline's. | A bill that stays high with little retooling means the non-retooling plants' losses grew: compare `goods_sales` with `goods_cost` on plants that aren't retooling (baseline: £54.9M against £58.6M). |
| **Oil.** The oil price and the oil shortage on power plants (`input_goods_shortage`). | AI plants move toward Modern Oil-Fired (140 electricity against Modern Coal's 90). Oil may tighten, but plants shouldn't flip between coal and oil every year. | Coal–oil flips driven by oil shortage would want a look at oil supply, not at the group. |

## Experiment: `should_remove` for power plants (#933, draft)

`building_power_plant = should_remove` in the default strategy's INJECT (`common/ai_strategies/edited_default_strategy.txt`,
where it replaces `nice_to_have`) and in three administrative strategies that have no `subsidies` block in vanilla
(`ai_strategy_agricultural_expansion`, `_plantation_economy`, `_placate_population`;
`common/ai_strategies/te_power_plant_subsidy_strategies.txt`). `should_remove` sits beside `must_have` and `nice_to_have`
among the executable's strings; no vanilla strategy uses it. Two things are unread: whether the value does anything, and
whether an INJECT that sets a key vanilla's `subsidies` block already holds replaces vanilla's value. Countries running one
of the three strategies ("clean") answer the first; the other AI countries, which only the default's INJECT reaches,
answer the second.

**Self-check.** Once a game for each group, as soon as its AI countries own 5 power plants and 5 railways, the yearly
pulse logs `TE_SELF_CHECK OK|BROKEN ai_power_plant_should_remove group=clean|other` with the counts and subsidized shares
(`common/scripted_effects/te_ai_subsidy_selfcheck_effects.txt`). OK is under half the group's power plants subsidized while
its railways, still `must_have`, read half or more. The railways are the control: a low railway share means `is_subsidized`
doesn't read the subsidy, and the line says so. No line for a group means it hasn't reached 5 plants yet. In a normal
game that is about the 1890s for the other group and later for the clean one; the 4× fast run gets there sooner.

| Result | Reading | Next |
|---|---|---|
| clean OK, other OK | `should_remove` works and the INJECT replaces vanilla's value. | Run the subsidy checks below. |
| clean OK, other BROKEN | `should_remove` works, but the engine keeps vanilla's `must_have` over the INJECT. | Fallback: put `building_power_plant = should_remove` in every administrative strategy (the four with a `subsidies` block hold no power-plant key either), since a strategy's value overrides the default's. |
| clean BROKEN | The value does nothing or isn't accepted. | Check `error.log` and `debug.log` for the strategy files at load. Revert to `nice_to_have`. |

| Check | Expect | If it fails |
|---|---|---|
| **Load.** Search `error.log` and `debug.log` for `ai_strateg`, `should_remove` and `te_power_plant_subsidy_strategies` after the game loads. | Nothing. | An unknown-value error means the engine rejects `should_remove`: revert to `nice_to_have`. |
| **Subsidies.** In a plain-text save past the self-check, count AI power plants with `subsidized=yes` by group (owner country's strategy). | Clean group near none; the other group near none if its line read OK. Railways and ports unchanged (about 99%). | As the self-check table. |
| **Plants without a subsidy.** The same save: power plants' `staffing` against `previous_staffing`, `cash_reserves`, and the electricity price where plants lost their subsidy. | Retooling or loss-making plants cut wages and shed some staff; electricity's price rises until plants cover their costs. No state left without power. | Plants emptying out and electricity shortages spreading to factories mean the AI needs the subsidy: revert, and lean on the base group's `most_productive` alone. |
| **Budgets.** Subsidies as a share of income and the bankrupt share of people (the fast-mode note's §4), against the section above. | Lower than with `most_productive` alone. | No change means the subsidy flag wasn't the bill: keep `most_productive`, drop the experiment. |
