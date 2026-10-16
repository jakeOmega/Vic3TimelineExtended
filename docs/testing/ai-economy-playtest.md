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

## The AI doesn't subsidize coal and oil power plants (#933)

`building_power_plant = should_remove` (the coal and oil plant; nuclear, fusion and renewable plants are their own
buildings, which no strategy subsidizes) in every vanilla administrative strategy, by INJECT
(`common/ai_strategies/te_power_plant_subsidy_strategies.txt`; `test_power_plant_subsidy_strategies.py` keeps the list
complete). A strategy's value overrides the default's. The default strategy's own INJECT (`edited_default_strategy.txt`)
is inert: an INJECT can't change a key vanilla's `subsidies` block already holds, though it adds a new one
(`scripting_best_practices.md`). AI countries running no administrative strategy keep the default's `must_have`.

**How it was read.** A once-a-game self-check, removed once it had answered, logged the subsidized share of AI power plants
and railways (the `must_have` control) by the country's administrative strategy, in the owner's European Union game loaded
at 2034.9.13 and run to 2035.1.1 (2026-10-16):

| Round | Strategies with `should_remove` | Power plants subsidized | Railways subsidized |
|---|---|---|---|
| 1 | The three with no vanilla `subsidies` block | Those three: 1% of 54. The other four, reached only by the default's INJECT: 99% of 256 | 98% |
| 2 | All seven | The three: 1% of 54. The other four (a second `subsidies` block): 19% of 257 | 98% |

No load error named a strategy file in either round. Still open: why 19% of the second group's plants stayed subsidized
after 3½ months (slow stripping, or a case where the AI keeps one), and how unsubsidized plants fare.

| Check | Expect | If it fails |
|---|---|---|
| **Subsidies.** A few years after the change, count AI power plants with `subsidized=yes` in a plain-text save (or read big AI countries' power plants in game). | Near none outside countries with no administrative strategy; the 19% left after 3½ months has fallen. Railways and ports unchanged (about 99%). | A share that stays near 19%: find which countries keep the subsidy and what they share (strategy, budget, electricity shortage). |
| **Plants without a subsidy.** The same save: power plants' `staffing` against `previous_staffing`, `cash_reserves`, and the electricity price where plants lost their subsidy. | Retooling or loss-making plants cut wages and shed some staff; electricity's price rises until plants cover their costs. No state left without power. | Plants emptying out and electricity shortages spreading to factories mean the AI needs the subsidy: drop `te_power_plant_subsidy_strategies.txt` and lean on the base group's `most_productive` alone. |
| **Budgets.** Subsidies as a share of income and the bankrupt share of people (the fast-mode note's §4), against the section above. | Lower than with `most_productive` alone. | No change means the subsidy flag wasn't the bill: keep `most_productive`, and reconsider the strategies. |
