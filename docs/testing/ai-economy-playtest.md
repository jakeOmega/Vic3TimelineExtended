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

## Unemployment as a share of the workforce (log triage 2026-10-17)

The engine's `state_unemployment_rate` reads the idle workforce over all the state's people, not over the workforce: in
Mecklenburg-Strelitz in January 1836 it read 0.048 where the pops held 0.195 of their workforce with no workplace
(Demographics' `unemployment_rate_read`, `docs/testing/demographics-playtest.md` § Log triage 2026-10-17). Owner's call:
fix it. Every mod reader outside the Demographics census now reads `te_state_unemployment_share`: the engine's figure,
read live, over the workforce's share of the state's people, which a yearly walk of each state's pops counts
(`common/script_values/te_unemployment_values.txt`; § Unemployment as a Share of the Workforce in `mod_systems.md`).
Their thresholds now mean a share of the workforce, so each bites at about a quarter of the unemployment it did. The
Settlement Authority's was raised from 5% to 10% as well (owner, 2026-10-17). The Demographics census stores the same
conversion at its walk (`te_dg_unemp`), which its youth bulge, event wave, pension AI and panel read (owner, 2026-10-17:
one source); its own count stays beside it (`te_dg_unemp_walk`) for its self-check.

| Reader | Threshold | Effect |
|---|---|---|
| Settlement Authority `ai_value` (`common/buildings/resettlement.txt`) | any of the AI's states above 10% (5% until the owner raised it, 2026-10-17) | +300 on an open frontier |
| Greenest Grass Campaign `ai_weight` (`common/decrees/extra_decrees.txt`) | 10% or more | × 0 |
| Recruitment Drive `ai_weight` (the same file) | above 10% | +50 |
| `migration_attraction_script_value` (`common/script_values/extra_script_values.txt`), the mass-migration destination's order | above 10% | × 0 |
| Demographics, under the census: the youth bulge (full at 20%), the event wave's Youth Bulge, the pension AI (10% and 5%) and the panel's Youth row, through `te_dg_unemp` | their own | the census's stored figure, as before; only its source moved from the walk's count to the conversion |

**How much more often.** The 1898 observer autosave (2026-10-17, Full) holds the engine's figure, as the census stored
it then, and the walk's workforce share for 826 census states. The workforce was still a quarter of the people
(median 0.251, 0.18 to 0.50). Taking the figure over that share:

| | Old reading (the engine's figure) | Share of the workforce |
|---|---|---|
| States above 5% | 14% of states, 43% of people | 40% of states, 69% of people |
| States above 10% | 1% of states, almost no people | 31% of states, 62% of people |
| Countries with a state above 5% | 46 of 203 | 108 of 203 |
| Countries with a state above 10% | 8 of 203 | 88 of 203 |

China's and Bengal's large states carry most of the people: a fifth to a third of their workforce idle.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … unemployment_share_read` | any rule: once a game, the first state at its yearly walk (`te_unemp_share_yearly`) with a workforce of at least 10,000 and at least 2% of it with no workplace | `conv` (`te_state_unemployment_share`, read after the walk) is within a quarter below or a third above `exact` (the walk's workforce with no workplace over its workforce). Equivalently `read` ≈ `per_people`: the engine's figure is the idle workforce over all the state's people, so the conversion is the share the readers mean. `prev_wf_share` is the share readers held before the walk (0.25: none yet) | `conv` about 4 × `exact` (`read` ≈ `exact`): the figure is already per worker, and the conversion counts it four times. Any other ratio: the figure is something else again | about 4 ×: take the division out of `te_state_unemployment_share` (the figure as it is). Otherwise have it read `var:te_unemp_share_exact`, the walk's own count, up to a year old (`te_state_workforce_share`'s `has_variable` pattern), and correct the notes in `scripting_best_practices.md` § The op slots. Either way the census can go back to its own count at once: store `te_dg_unemp` from the walk's `te_dg_unemp_walk` count in `te_demog_work_walk_store` |

No line after a few years means no state with a workforce of 10,000 had 2% of it idle at its yearly walk; compare the
state panel's unemployed in a state with visibly idle workers.

| Check | Expect | If it fails |
|---|---|---|
| **Settlement Authorities.** An observer run with internal resettlement on: how many AI countries with an open frontier found one by 1870, against an earlier run. | More than before: the +300 now holds wherever one of the AI's states has a tenth of its workforce idle, which 1898 shows for 88 of 203 countries (the old 5% read held for 46). Still at most three new ones each. | Authorities in nearly every country with a frontier, or a frontier filled faster than its region can take, mean 10% is still too low a bar: the owner's call (raise it again, or count only states the Authority can recruit from). |
| **Greenest Grass and the Recruitment Drive.** Which states AI countries issue them in (a plain-text save's decrees, or the state panel). | Greenest Grass in fewer states with idle workers than before (its × 0 now bites at a tenth of the workforce); the Recruitment Drive in more of the AI's crowded or idle states. | Greenest Grass almost never issued by an AI with a frontier: 10% bites too often; the owner's call. |
| **Mass migration.** A violence-against-minorities mass migration (`trigger_mass_migration`): where the people land. | A state with under a tenth of its workforce idle. Where every candidate is above it, all score 0 and the pick among them is arbitrary. | Migrants sent into a state with mass unemployment: check `te_state_unemployment_share` there with the console (`te_unemp_wf_share` on the state). |
