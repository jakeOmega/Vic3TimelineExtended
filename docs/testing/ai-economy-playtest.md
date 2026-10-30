# AI economy play-test checklist

What the next play-test should look at in the AI's budgets and production-method choices. In-game checks do not gate a
merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what
only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the
commit that fixed it.

## How to run

- **The run.** The late game's subsidy bill needs the late technologies, so use the 4× fast run from
  `docs/superpowers/archive/specs/2026-10-12-demographics-fast-mode-revenue.md` §4: a new 1836 game, observed, `event
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
| ~~**Base-group churn.**~~ (read 2026-10-18, below) Diff two consecutive yearly saves late in the run (calendar 1900 on). | Base-group switches mostly upward (to a newly unlocked method) or away from a short input; few back down to Early Power Plant. Base switches well under the baseline's 70 a year. | Downgrades as frequent as before mean the engine isn't reading the INJECTed `ai_selection`: check `debug.log` for the group, then try a `REPLACE:` of the group. |
| **Retooling share.** Count power plants with `pm_retooling` in the 1904 and 1912 saves. | Well under 70%, nearer the railways' and ports' share. | If the base group is quiet but the share stays high, the automation and carbon-capture groups carry the churn: count their switches before choosing a lever. |
| **Subsidy bill.** Power plants' share of `balance_subsidies`, and subsidies as a share of income (the note's §4 slot map). | Power plants' share well under 57%; fewer bankrupt countries than the baseline's. | A bill that stays high with little retooling means the non-retooling plants' losses grew: compare `goods_sales` with `goods_cost` on plants that aren't retooling (baseline: £54.9M against £58.6M). |
| **Oil.** The oil price and the oil shortage on power plants (`input_goods_shortage`). | AI plants move toward Modern Oil-Fired (140 electricity against Modern Coal's 90). Oil may tighten, but plants shouldn't flip between coal and oil every year. | Coal–oil flips driven by oil shortage would want a look at oil supply, not at the group. |

**Read 2026-10-18** in the owner's EU game, AI countries only (the EU is the player). The saves were 2033.12.21 and
2034.9.13 before the change, and 2036.5.20 to 2051.1.1 with this section's change and the next section's. Plants were
matched by building id. Other changes went into the same game in those years (#1037 and #1040 among them), so the late
budget figures aren't #933's alone. The full figures are in #933's comment of that date, and the binary tokens in
`scripting_best_practices.md` § "A Save's `subsidized=yes` Is Only the Chosen Flag".

| Check | Result |
|---|---|
| Base-group churn | **Passed.** AI base-group switches fell from 54 a year (2033.12 → 2034.9) to 11–16 a year (2045.12 → 2050.12). Downgrades fell from 30 a year to 2–3 a year from 2048. There were 12 a year in 2045–48, mostly Modern Oil-Fired to Modern Coal-Fired or Oil-Fired. AI plants on Early Power Plant fell from 135 of 310 to 39 of 330. |
| Retooling share | **Not met.** 71% of AI plants were retooling in 2034 and 60% in 2048–51, against 39% of railways and 37% of ports (25% and 24% in 2034). The fallback holds: the automation group carries the churn, both ways. World-wide from 2048.4 to 2051.1, 32 plants switched from Power Centralized Control Systems to Power Integrated Smart Systems and 30 switched back. Without a subsidy this churn costs the treasury nothing, but retooling still cuts the plants' output. |
| Subsidy bill | Power plants' share **passed**, by the next section's change: 57% before, 0% after. Bankrupt countries **didn't fall**: 80 of 113 before, 83 of 110 after. See the next section's Budgets. |
| Oil | **Mostly passed.** Most base-group switches go to Modern Oil-Fired. Moves from Modern Oil-Fired back to Modern Coal-Fired were 14 in 2045–48 and 1 in each window after. The oil price and shortage weren't read. |

## The AI doesn't subsidize coal and oil power plants (#933)

`building_power_plant = should_remove` (the coal and oil plant; nuclear, fusion and renewable plants are their own
buildings, which no strategy subsidizes) in every vanilla administrative strategy, by INJECT
(`common/ai_strategies/te_ai_subsidy_strategies.txt`; `test_ai_subsidy_strategies.py` keeps the list
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

No load error named a strategy file in either round. The 19% of the second group still subsidized after 3½ months was
slow stripping: 3 of 313 AI plants were subsidized in 2036.5.20, and none from 2040 on (read 2026-10-18, below).

| Check | Expect | If it fails |
|---|---|---|
| ~~**Subsidies.**~~ (read 2026-10-18, below) A few years after the change, count AI power plants with `subsidized=yes` in a plain-text save (or read big AI countries' power plants in game). | Near none outside countries with no administrative strategy; the 19% left after 3½ months has fallen. Railways and ports unchanged (about 99%). | A share that stays near 19%: find which countries keep the subsidy and what they share (strategy, budget, electricity shortage). |
| ~~**Plants without a subsidy.**~~ (read 2026-10-18, below) The same save: power plants' `staffing` against `previous_staffing`, `cash_reserves`, and the electricity price where plants lost their subsidy. | Retooling or loss-making plants cut wages and shed some staff; electricity's price rises until plants cover their costs. No state left without power. | Plants emptying out and electricity shortages spreading to factories mean the AI needs the subsidy: drop `te_ai_subsidy_strategies.txt` and lean on the base group's `most_productive` alone. |
| **Budgets.** Subsidies as a share of income and the bankrupt share of people (the fast-mode note's §4), against the section above. | Lower than with `most_productive` alone. | No change, with power plants still a large share of the bill, means the subsidy flag wasn't the bill: keep `most_productive`, and reconsider the strategies. No change with their share at 0 means the bill moved to other buildings: rank `balance_subsidies` by building type and country. |

**Read 2026-10-18**, in the same saves as the section above.

| Check | Result |
|---|---|
| Subsidies | **Passed.** AI power plants subsidized: 308 of 310 in 2034.9, 3 of 313 in 2036.5, and none from 2040 (0 of 329 in 2051.1). Their summed `balance_subsidies` is 0 too. Railways stayed 98–100% subsidized and ports 100%. Every AI country but at most one runs an administrative strategy. |
| Plants without a subsidy | **Passed.** The plants shed staff: 957 workers a level in 2034, 259 in 2036 and 124 in 2051. 16,526 levels still stand (20,404 in 2034). Their sales per unit of electricity rose about a fifth (£22.2 to £27.2). AI electricity output fell 23% by 2036.5, but by 2051 it was 56% above 2034, as Renewable Energy Plants' output quadrupled. |
| Budgets | **Failed, though not as the fallback expected: the flag was the bill, and the bill moved.** AI subsidies (summed `balance_subsidies`) went from £90.5M a week in 2034.9, 57% of it on power plants, to £34.9M in 2036.5. They then rose to £94–124M from 2045 to 2049, and stood at £97.8M in 2051, paid on ports, railways and Renewable Energy Plants. Subsidies as a share of income (budget slot 8) went from 48% to 17%, then back to 30–44%. Bankrupt AI countries went from 80 to 81–83. |

Where the bill went in the Budgets result:
- **Ports:** India's cost £1.2M a week in 2034 and £43M by 2048, and India went bankrupt in 2050.
- **Railways:** most is Russia's, bankrupt throughout.
- **Renewable Energy Plants:** £18–29M a week. The mod's Renewable Energy Investment policy in the Global Warming entry forces their subsidy (`renewable_investment_modifier`, held by about 99 of the 110 AI countries).

#933 was closed as done for power plants (owner, 2026-10-18). The displaced bill is #1050.

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

## Construction Cost Scaling: the slack part (#1034 follow-up)

The scaling is now the GDP part (+1,000% at £100 again) times the share of it that applies, which depends on slack, peasants plus unemployed over the workforce: all of it at 3% or less, none at 15% or more, moving a third of the remaining way each year. #1037's +100% cap is gone.

The slack is read over the whole owner country. The economy growth sim's counterfactual (`docs/systems/economy_growth_sim.md`, ministries at +1% a level) expects for the owner's playthrough:
- the EU as a whole at 3.5% slack in 2045, with no labour shortage;
- China at 8%.

France's core, inside a country whose colonies and annexed regions hold most of the slack, lies between two bounds:
- short of labour from 2004, about 31% by 2045, if nobody moves into its new jobs;
- 1.6% slack, if the brake followed the core alone.

Look for both failure modes, especially in a rich core with a poor periphery, and for the price swinging.

| Check | Expect | If it fails |
|---|---|---|
| **The tooltip.** Hover the Nation tab's Construction Cost row, then the figure in its last line. | Each factor shows a number, not a raw `[...]` or a blank. The total is the cost in force and equals the scaling × the other modifiers; the scaling equals 100% + the GDP part × the share that applies. The last line's hover lists every source of `goods_input_construction_mult` (the ministries, global warming, green building codes, this scaling at its combined value), and its total is the tooltip's total less 100%. Before the country's first yearly update under the rule, the slack sentence says it hasn't been counted yet. No `Failed to fetch variable` in `error.log` or `debug.log` while it's open. | A blank or raw figure: the script value it reads (named in the loc key `te_nation_construction_row_tt`); a missing variable means the pulse hasn't run (wait a year) or `te_cc_yearly_update` didn't store it. A breakdown that doesn't render: `GetValueWithBreakdownFor` on `GetPlayer.GetModifier` in a tooltip (proven on a JE and state panel only); fall back to the summed others alone (`te_cc_other_sources`). |
| **The share.** A rich player country with many peasants or unemployed (over 15%), then one near full employment. | Over 15% slack: the share heads for 0 and the scaling toward 100%. Near full employment: the share climbs a third of the remaining way each year toward 100%. The row's figure is the scaling's own effect, not the modifier's combined value. | The share stuck at 0 with low slack: the self-check below, then the walk's counts on a state (`te_unemp_slack_count`, `te_unemp_wf_count`). |
| **Mode 1, too fast.** A strong player game around 2000–2050: peasants plus unemployed, new buildings' staffing, the investment pool. | Slack between about 2% and 10%, with buildings mostly filling. Peasants and unemployed together under 1% while new buildings can't fill and the pool sits unspent is vanilla's failure. | Lower the band so the brake comes on earlier (`construction_cost_slack_none` 0.12, or `construction_cost_slack_full` 0.05), and update the pin in `test_econ_sim_data.py`; rerun the counterfactual. |
| **A rich core with a poor periphery.** A rich country holding poor colonies or annexed regions (the owner's France, then the EU), after about 1990: the core states' unemployed and peasants, its new buildings' staffing, and migration from the periphery. | Migrants from the periphery filling the core's new jobs, so the core keeps some slack while the country's share stays low. | The core runs short of labour (new buildings unstaffed there) while the country's slack stays above 15%: the country-wide read is too loose. The owner kept it on 2026-10-18 pending this check; the next step is to weight each state's slack by its GDP or building levels, or count only incorporated states (`te_country_slack_share`, `te_unemployment_values.txt`). |
| **Mode 2, too slow.** The same game, or an AI great power past £11. | Peasants plus unemployed falling toward a few percent by the 2040s in a rich core, and well below the old 30–50%. | If the slack sits above 15% with the share at 0, the curve isn't the binding lever there: the doc names the next ones (construction-sector labour per point, late cost tiers, the investment share). |
| **The price swinging.** The construction market panel's price per point over a few decades in a rich country. | It follows slack: each year the share closes a third of the gap to its target, so where the GDP part is large a year's move can still be large (from none of it to a third of +1,000% is 1× to 4.3× base). The playthrough's arithmetic moved France's at most about a quarter a year. | Boom and bust in the construction queue: slow the easing (`construction_cost_slack_ease` 0.2) or widen the band (`construction_cost_slack_none` 0.2). |

On an old save, until the country's first yearly pulse under the rule the share is the one that reproduces the scaling in force (`te_cc_slack_factor_carried`): the old modifier's X over today's GDP part. So the construction market's price, goods per point and the Nation tab carry the old scaling until the pulse, which then moves the share a third of the way toward its target. A new game has no old scaling, so it starts from 0.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … construction_slack_read` | any rule: once a game, the first country at its yearly pulse (`te_cc_yearly_update`) that had a reading at an earlier pulse (every state walked at least once), with a walked workforce of at least 100,000 and a stored slack between 2% and 98% | `slack` (the sum over the country's states of their last walks' counts, `te_country_slack_share`) is within 10 points of `fresh` (a walk of every pop in the country now, counted by the same rule, `te_unemp_count_pop`), and `fresh_peasants` is above 0. `peasants` against `fresh_peasants`, `walked_wf` against `fresh_wf` likewise; each state's count is up to a year old. The recount shares the walk's rule, so it can't catch a wrong rule except one that never counts a peasant | The stored counts or their sum aren't what the walk counted, or the peasant branch never matches: the share would follow the wrong slack | Compare `walked_wf` and `fresh_wf`: far apart means states lack their counts (the monthly fill in `te_unemployment_on_actions.txt`) or the `every_scope_state` sum drops them. Then have `te_cc_yearly_update` walk the country's pops itself, as the self-check does (once a year a country, costlier) |

**2026-10-25 (night):** BROKEN by a hair: Orta Zhuz in January 1837, `slack=0.862` against `fresh=0.809` (5.3 points, the bar is 5), `walked_wf=115832` against `fresh_wf=117442`. The states had their counts (the two workforces agree), so the gap is a year's drift in the peasant share, which the check allows for in its counts but not in its bar. `target=0.000 factor=0.000` at GDP per head 0.27. No change; a second game's line decides whether the bar should widen.

**2026-10-25 (late night):** the next new game logged the same line: Orta Zhuz, January 1837, `slack=0.862` against `fresh=0.809`, `walked_wf=115851` against `fresh_wf=117410`. A new game nominates the same country at the same pulse every time, so this is the same case again, not an independent sample: the check would read BROKEN in every new game. The gap is the first year's hiring, which moves peasants into the starting economy's jobs while each state's count waits up to a year for its walk. The bar is now 10 points. The failures it looks for are larger: a dropped state's count parts the two workforces and moves the slack by tens of points, and a peasant branch that never matches reads 0.

No line after a few years means no country with a workforce of 100,000 had between 2% and 98% slack at its pulse; check a large country's `te_cc_slack` with the console.

## Transport goods: Transportation inside a state, Merchant Marine between markets (#1050)

Industry's freight is now local Transportation (× 50/30), Merchant Marine is bought only by Trade Centers (and the engine's port connections and convoys), railway and port infrastructure counts per level, the passenger tiers take inputs worth about 40% of their output, and the AI stops subsidizing railways and ports (`common/ai_strategies/te_ai_subsidy_strategies.txt`). Design: `docs/superpowers/archive/specs/2026-10-21-transport-goods-design.md`; the #1050 baselines and save scripts are in `/mnt/d/vic3te-data/issue1050-2026-10-21/`. The owner's test is "nothing weird" in an observer run; the rows below are what weird would look like. Run into the 2040s, or load a late-game start, so the late tiers and the construction hubs are in play.

| Check | Expect | If it fails |
|---|---|---|
| **Subsidies.** AI railways' and ports' `subsidized` share and the AI's weekly subsidy bill on them, against the #1050 table (£24–55M a week on ports, £27–48M on railways). | Near none subsidized outside countries with no administrative strategy; the bill on the two near zero. Highways and airports are still forced subsidies under the construction-system laws (`common/laws/construction_system_law_injections.txt`) and now make far more Transportation, all of it sold locally: their share of the bill shouldn't grow much. | A share that stays high: find which countries and strategies keep it, as #933's read did. If the total AI subsidy bill hasn't fallen, rank `balance_subsidies` by building type to see where it went. |
| **Transportation prices.** The local price in a sample of AI and player states. | Most states between about half and twice base; not pinned at the floor or the ceiling across a country. | Most states at the floor: railways overbuilt for the new demand (check the passenger tiers' share of output). Most at the ceiling: railways not following demand; take the deferred `REPLACE:building_railway` whose shortfall branch ignores staffing (spec § 3.1). |
| **Market access.** States below 100% market access and states short of infrastructure, over time. | No more than before the change, and not rising once subsidies stop. | Rising: railways or ports emptying out despite per-level infrastructure; check `infrastructure` against `infrastructure_usage` in those states. |
| **Construction hubs.** The states with the largest Construction Sectors: their Transportation price, railway levels, and construction points against a pre-change baseline. | Railways grow beside the hubs; the price is dear while they catch up, then settles. Construction points don't fall. | Hubs short of Transportation with output penalties, or construction points falling: the spec § 2 fallback (`convert_transport_goods.py --construction-good merchant_marine` and `CONSTRUCTION_GOOD = "merchant_marine"`). |
| **Shortage penalties.** Buildings with an input-shortage penalty on Transportation. | Not widespread; mostly in states still building railways. | Widespread and lasting: railway output per level too low for the new demand (raise the base methods' output), or the AI not building railways (see the hubs row). |
| **Railway and port levels.** Where levels grow, and the world's port levels against the #1050 saves. | Railways grow where Transportation is dear. Port levels fall several-fold to match trade's demand; no state piles up levels with a large surplus. | Ports still piling up: something else still buys Merchant Marine (list its consumers in a save). |
| **Retooling.** Passenger-group switching and the `pm_retooling` share on ports and railways. | Not above the #933/#1050 baselines. | Ports flipping between passenger tiers: reconsider `most_productive` on `pmg_water_personal_transport` with the new inputs. |
| **Bankruptcy.** Bankrupt AI countries. | No more than the 80–83 of about 110 in the #1050 saves. | More: rank their deficits by building type. |
