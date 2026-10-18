# Economy growth sim (#1034)

Tools to tune how fast a country's economy changes shape: how fast peasants and the unemployed find jobs, and when labour runs short. They are tuned against one playthrough, the owner's France → EU game, 1867–2045.
- Design: `docs/superpowers/specs/2026-10-17-economy-growth-sim-design.md`.
- Plan: `docs/superpowers/plans/2026-10-17-economy-growth-sim.md`.
- Commands: `docs/guides/python_tools.md` (Balance & Analysis).

The target sits between two failure modes the owner named:
- **Mode 1, too fast (vanilla's tendency):** no peasants or unemployed left, new buildings can't fill, and investment finds nothing to build.
- **Mode 2, too slow (the mod before this change):** a rich country keeps a third of its workforce idle and automation is useless.

Land nearer mode 2 than vanilla does, with neither happening often.

## Findings (2026-10-18)

1. **The current curve explains most of the late stall.** France's core (its 33 states of 1867) never got its slack (peasants plus unemployed) below 26% of the workforce. Slack rose to about 50% after 2011.
   - In those years each construction point cost 4.4–11× its base price under Construction Cost Scaling, and up to 21× with the country's other construction-cost modifiers.
   - The data counterfactual (below) re-prices the points France actually bought: the same money under a curve capped at +100% buys enough to absorb that slack by about 2042.
2. **The early period isn't the curve's doing.** Before 1954 the penalty was under +130%. Even with no penalty at all, France's core would still have held 27% slack in 1917 and 10% in 1954.
   - The owner's "peasants near zero by the 1950s" needs other levers: early construction volume, set by the construction sector's labour per point (about 12× vanilla's), the investment share and the land laws.
3. **Jobs per construction point fell about sevenfold,** from 7 in 1867–1917 to about 1 from 1990 on, as late buildings cost more points and employ fewer people a level. That fall is designed into the PM ladders (spec § 4.3). It's why the same penalty bites harder late.
4. **Other construction-cost modifiers double the curve for this player.** They compound with it: the Ministries of the Environment and of Consumer Protection at +5% a level each, global warming and green building codes added +82% in 1998 and +100% in 2045. Under the +100% cap, a rich player with both ministries still pays about 4× per point.
5. **The curve barely touches poor countries.** AI China's raw penalty stays under +30% until 2004 and peaks at +147%. Its slack, 85% in 1917 falling to 27% in 2045, isn't the curve's. AI Britain stays under +66%. The catch-up problem lies elsewhere.
6. **The structural sim can't reproduce the playthrough yet** (154 hindcast misses). Its fit removes all the slack to match France's wages and GDP. Four things it lacks are named under "The structural sim". Until they're built, its sweep tables show the model's mechanics, not forecasts.
7. **Wages rose 44× (nominal) in France while a third of the workforce sat idle.** The model's premise was "labour scarcity raises wages, and rising wages make automation pay". That doesn't describe this playthrough's aggregate wage. The building-level picture differs: steel and motor workers earned £0.1 a week against £1.75–3.9 of value added each in 2045 (issue #1034). See the open questions.

## Recommendation (shipped in this change)

**Construction Cost Scaling stops at +100%, keeping its slope:** 10 points per £1 of GDP per capita above £1, flat from £11. In the script, `construction_cost_max_mult` 10 → 1 and `construction_cost_ceiling_ratio` 100 → 11.

Against the playthrough's data (the counterfactual below):

| Curve | France's core, 2045 slack | first under 5% | Labour shortage (vacancies over 1%) | Whole EU, 2045 slack | China, 2045 slack |
|---|---|---|---|---|---|
| Before (+1,000% at £100) | 48.7% | never | never | 63.1% | 27.4% |
| **+100% cap (shipped)** | **0% (1.7% vacancies)** | **2042** | **2043, 1.7%** | **13.1%** | **26.9%** |
| +125% cap (ceiling ratio 13.5) | 7.4% | never | never | 21.9% | 27.3% |
| +150% cap (ceiling ratio 16) | 14.4% | never | never | 28.7% | 27.4% |
| +200% cap | 24.2% | never | never | 38.6% | 27.4% |
| No penalty (vanilla) | 0%, 86.7% vacancies | 1959 | 1976 | 0%, 67.5% vacancies | 9.5% |

Why +100%:
- A rich core's slack falls to a few percent by the 2040s, and the labour shortage arrives only at the very end, at 1.7%. That figure is an upper bound: no wage response, no capacity limit.
- The whole union, carrying its annexed poor regions, stays at 13%. That's nearer mode 2 than vanilla, with neither mode lasting long.
- It's a plain rule: construction never costs a rich country more than twice what a poor one pays.

If play shows mode 1, the softer caps are one constant each (the table above, and `docs/testing/ai-economy-playtest.md`).

What the recommendation doesn't rest on:
- The counterfactual is arithmetic on the saves, not a calibrated sim.
- It ignores compounding (more levels → more GDP → more construction) and the services demand a larger economy buys. Both understate a cheaper curve's effect.
- It also ignores migration into new jobs and any floor that holds peasants in place (France's core kept 15–19% peasants from 1986 under collectivized agriculture). Both would slow the absorption.

## Data

### Source

`scripts/analysis/econ_series_c480d386.json` is read from playthrough `c480d386`, the owner's 1.14.5 game. Country
id 4 is the player throughout (FRA, the French Commune, FRA again, then EUN), 1836 to 2045.12. It comes from 23
binary saves: `french republic_1867_08_16`, `french commune_1917_10_02`, `_1954_06_21`, `_1954_06_24`,
`_1955_10_06`, `_1959_06_19`, `_1976_01_01`, `france_1986_12_19`, `france_1990_02_24` and 14 `european union_*`
saves from 1998.12.29 to 2045.12.2. Two plain-text saves of the same game (`french commune_1949_07_20`,
`french commune_tmptst`) are skipped: the reader decodes binary saves only.

`scripts/analysis/econ_save_series.py` builds it. Copy each save into a scratch folder first and read the copy,
never the game's save folder, one save at a time:

```bash
PY="python3 -I scripts/analysis/econ_save_series.py"
# 1867 first: its own state lists fix the three sets.
$PY "<scratch>/french republic_1867_08_16.v3" --country-id 4 \
    --core-from "<scratch>/french republic_1867_08_16.v3" --core-id 4 --core-id 1 --core-id 156 \
    --out "<scratch>/x/french republic_1867_08_16.json"
# Every later save, its sets taken from the 1867 extract:
$PY "<scratch>/<save>.v3" --country-id 4 --core-from "<scratch>/x/french republic_1867_08_16.json" \
    --core-id 4 --core-id 1 --core-id 156 --out "<scratch>/x/<save>.json"
# Merge:
$PY "<scratch>"/x/*.json --dataset scripts/analysis/econ_series_c480d386.json
```

A save from another game version, or a plain-text one, prints `skip <name>: <reason>` and the run carries on. Each
save takes 8 to 16 seconds.

### Series

The series follow fixed sets of states, not country ids, because countries change id: a revolution's winner is a
new country object. Great Britain was id 1 in 1867, 50331659 in 1917 and 16777829 from 1954; China was 156, then
16777873. The successors hold most of the old states (28 of Britain's 36 in 1917, 38 of China's 40), but the tags
come and go. So:

- **FRA**, **GBR**, **CHI**: the states that ids 4, 1 and 156 (France, Great Britain, China) held in the 1867 save:
  33, 36 and 40 states. Each point reads that set's pops and buildings, whoever holds them.
- **owner**: the country whose state list holds the most of the set's people at that save (by population, not
  by number of states), with `owner_share`, its share of the set's people. The owner's country fields come with
  the point. GBR's owners are GBR (1, then 50331659), then England (ENG, 33554444 from 1954, 50332331 from
  1986). CHI's are CHI (156, 16777873), then China (ZHO, the mod's formable; 16777873 from 1976, 50331660 from
  1986, 33554467 from 2023).
- **Stop rule**: a GBR or CHI series ends at the first save whose owner is the player (id 4) or holds under half the
  set's people, and that save is left out. GBR ends after 1990.2.24 (EUN holds 84% of it in 1998); CHI never
  stops. FRA, the player's own set, never stops.
- **union**: the player's own states at each save (233 in 1998, 282 in 2045), with per-state figures, so that
  annexations show as states that appear between points.

Points per series: FRA 23, GBR 9, CHI 23, union 23.

### Format

```
{"playthrough": "c480d386",
 "series": {"FRA" | "GBR" | "CHI": {"core_id": 4 | 1 | 156, "core_states": [state ids],
                                    "points": [POINT, ...]},
            "union": {"points": [POINT + "per_state", ...]}},
 "gdp_yearly": {"FRA" | "GBR" | "CHI" | "union": {"<year>": £/yr}},
 "world": [{"date", "gdp", "population"}]}

POINT = {"date", "owner_id", "owner_tag", "owner_share",
         "slice": {"population", "workforce", "peasants", "employed", "unemployed",
                   "wage_per_worker", "welfare_per_unemployed",
                   "buildings_by_type": {type: {"levels", "staffing", "employees", "goods_sales", "goods_cost",
                                                "pms": {pm: levels}}}},
         "owner": {"gdp", "population", "gdppc", "acquired_techs", "investment_by_type", "land_law",
                   "per_project_cap", "variables": {"prior_construction_scaling", "te_mon_gdp_last_year"},
                   "scale", "points_weekly": {"government", "private"}, "pool_spend_weekly"}}
per_state = {state id: [population, workforce, peasants, unemployed, building levels]}
```

- `slice` is a pop and building scan of the set's states. Population is workforce plus dependents. Peasants are
  the workforce of `peasants` pops. Every other pop's workforce is employed when the pop has a workplace and
  unemployed when it has none, since the game keeps a pop's laid-off part in a pop of its own.
  `wage_per_worker` is non-peasant weekly wages (budget slot 0) over employed workers. `welfare_per_unemployed`
  is weekly welfare (slot 3) over unemployed workers, 0 with none. Building money is weekly £.
- `owner` copies the owner's country record: `gdp` (the newest weekly sample of the GDP trend, at its yearly
  rate), `population` (its `pop_statistics`), `gdppc` = gdp / population, the acquired techs, weekly investment
  by building type, the active land-reform law, `per_project_cap` (the largest base speed among the projects
  progressing that week) and two variables. `points_weekly` (construction points a week, per queue) and
  `pool_spend_weekly` (the investment pool's weekly spend on construction) are country-wide flows, so they are
  scaled to the slice: × `scale` = slice population / owner population. A set split between owners therefore gets
  the owner's per-person rate over all its people (GBR 1954: England holds 66% of it, scale 1.51). The union's
  owner fields are unscaled (`scale` 1).
- `gdp_yearly` is the mean of each calendar year's weekly GDP samples of each point's owner. Each sample is taken
  from the first point at or after it, so from the country that held the set at the next save. Samples are
  placed by date: a trend ring's index counts weeks since its own country was created, so a revolution winner's
  starts at 0. Years no owner's ring covers are missing: GBR 1868–1898, CHI 1868–1909 and 1977.
- `world` sums `gdp` and `population` over every country block of the save, including blocks that hold no
  states: a civil war splits a nation's pops between two blocks (below), and each pop is counted once. In 1867
  that sum is 1,345,278,747 people, against 1,345,356,411 from a scan of every pop.
- Building money, staffing, investment and yearly GDP are kept to 2 decimals. The file is 3.19 MB.

### Verification

Against the figures read by hand from the 1917 and 1998 saves:

| check | expected | dataset |
|---|---|---|
| FRA 1917.10.2 population / workforce | 91.07M / 45.55M | 91,069,639 / 45,552,109 |
| FRA 1917 subsisting / unemployed | 10.87M / 6.00M | 10,873,679 / 6,001,809 |
| FRA 1917 construction points a week | 1,954 | 1,954.44 |
| EUN 1998.12.29 population / subsisting / unemployed | 1,198.0M / 208.3M / 94.1M | 1,198,038,722 / 208,299,472 / 94,133,762 |
| EUN 1998 construction points a week | 22,614 | 22,613.78 |
| FRA 1917 union `wage_per_worker` | ≈ £0.092 | £0.0902 |
| FRA set's workforce ≤ id 4's, every save | | all but 1867 |
| union workforce against id 4's `pop_statistics`, every save | within 1% | all but 1867; at most +0.031% |

- The wage figure differs because the hand count divided by the wages of every pop, peasants included:
  (2,585,561 + 58,897 peasants' + 796) / 28,676,702 = 0.0922. Without the peasants it's 0.0902.
- **1867 catches France mid-revolution.** A second FRA block (id 33555011, flagged revolutionary) holds no states
  but 18,106,296 people and £8.25M of GDP. Id 4's own `pop_statistics` and GDP cover only the loyalist 28.7M of the
  46.8M people in France's 33 states. The scans (`slice`, the union) count all 46.8M, so in 1867 they are 1.6×
  id 4's `pop_statistics`. Every later save agrees to within 0.031%. `gdppc` and the scaled flows are per person,
  so the 1867 point needs no special case.

Decoding notes, for the next playthrough:

- A pop's 0x573b, read as "employed" in the 2026-10-17 save probe (`scripts/pops.py`), is not employment: pops
  with no workplace carry it too. Counting with it gives 1.6M unemployed in FRA 1917 against `pop_statistics`'
  6.0M. The workplace (0x330b) gives 6,003,962.
- `pool_spend_weekly` is the opposite of the budget's 0x33c7 (`weekly_investment_pool_change_from_construction`,
  stored negative). FRA 1917: £1.69M a week, 12.4% of GDP over a year.
- A binary save's meta has no ASCII `version`; the version is the string under token 0x00ee.

### The construction-cost penalty in the series

`prior_construction_scaling` (the cost scaling the mod applied at its last yearly pulse) against the raw curve,
clamp((gdp / population − 1) / 99 × 10, 0, 10), at the union's points:

| date | gdp / population | raw curve | prior_construction_scaling | prior / raw |
|---|---|---|---|---|
| 1917.10.2 | 7.77 | 0.683 | 0.666 | 0.975 |
| 1955.10.6 | 14.83 | 1.397 | 1.400 | 1.002 |
| 1976.1.1 | 25.33 | 2.458 | 4.000 | 1.628 |
| 1998.12.29 | 25.04 | 2.429 | 4.409 | 1.815 |
| 2023.11.26 | 58.77 | 5.835 | 10.938 | 1.875 |
| 2045.12.2 | 155.49 | 10.000 | 20.155 | 2.016 |

The 1998 penalty, 4.41, is 1.8 times the raw curve's 2.43 at GDP per capita 25.0. The gap is the country's other
`goods_input_construction_mult`, as the adjusted multiplier intends: `construction_cost_scaling_adjusted_mult`
multiplies the raw curve by one plus every other source, so they compound instead of adding. In EUN 1998 those
sources are the Ministry of the Environment at level 6 and the Ministry of Consumer Protection at level 8 (0.05 a
level each: +0.70), `global_warming` at multiplier 1.31 (+0.066) and `green_building_codes_modifier` (+0.05).
That gives 1 + 0.816 = 1.816, against 4.409 / 2.429 = 1.815. In EUN 2045.12 the same sources sum to +0.995
(levels 8 and 9, warming at 1.9), against 20.155 / 10 = 2.016 at the curve's cap. The ratio is about 1.0 up to
1955 and 1.6 to 2.0 from 1976 on; the sources were read in the 1998 and 2045.12 saves only. It isn't a different
population: the scan's population equals `pop_statistics` at every point but 1867, and at the cap the curve
doesn't depend on population at all. Nor is it a defect in the adjusted multiplier: both saves hold one
`construction_cost_scaling` modifier, whose stored multiplier equals the variable, and in 1998 it was applied on
the save's own date. A model of the penalty therefore needs the ministries' levels, not only GDP per capita.

## The construction counterfactual (from data)

`scripts/analysis/econ_construction_counterfactual.py` answers the curve question without the structural model.

**Method.** For each interval between a series' saves:
1. It counts the points actually built: each level-bound building type's levels gained, times that type's own `required_construction`.
2. It counts the jobs they created: those levels times the type's staff per staffed level at the interval's end. Dividing gives jobs per point.
3. Under another curve, the same money buys (1 + X_then) / (1 + X_shape) times the points, with the country's other construction-cost modifiers held as they were.
4. The extra jobs, accumulated over the intervals, come out of the observed slack.

Population, the workforce and demand-bound jobs (urban centres, construction sector) stay as observed. Where extra jobs exceed the slack, the excess reads as vacancies, the mode-1 proxy. The baseline `historical` is the curve in force during the playthrough (`econ_sim_data.HISTORICAL_CURVE`), and `current` is the mod's curve now.

**France's core, per interval** (jobs per point, and the penalty X the country paid):

| interval | points built | jobs a point | GDP per head | X raw → with other modifiers |
|---|---:|---:|---|---|
| 1867–1917 | 1.66M | 7.08 | 0.9 → 7.8 | 0 → 0.67 |
| 1917–1954 | 5.93M | 3.90 | 7.8 → 13.7 | 0.68 → 1.21 |
| 1959–1976 | 4.12M | 4.48 | 17.0 → 25.3 | 1.61 → 4.00 |
| 1976–1986 | 4.14M | 2.01 | 25.3 → 25.7 | 2.46 → 4.97 |
| 1990–1998 | 6.30M | 0.85 | 33.7 → 25.0 | 3.31 → 4.41 |
| 2011–2023 | 18.18M | 1.05 | 34.8 → 58.8 | 3.41 → 10.94 |
| 2023–2033 | 8.25M | 2.28 | 58.8 → 82.4 | 5.83 → 13.38 |
| 2036–2045 | 10.27M | 0.78–1.14 | 93 → 150 | 9.31–10 → 16.9–20.2 |

Realised points run at about 72% of the observed weekly rate (rebuilt levels and projects in progress aren't counted), so the counterfactual is conservative by about that much.

**France's core, slack by curve** (counterfactual share of the workforce; "vac" = vacancies):

| date | observed | +100% cap (shipped) | +125% | +150% | +200% | slope ×0.5 | none |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1917 | 36.5% | 36.5% | 36.5% | 36.5% | 36.5% | 33.1% | 27.3% |
| 1954 | 33.3% | 31.8% | 33.2% | 33.3% | 33.3% | 25.6% | 10.3% |
| 1976 | 26.2% | 19.8% | 22.5% | 24.1% | 25.5% | 15.8% | vac 10.6% |
| 1998 | 35.5% | 26.5% | 29.6% | 31.6% | 33.8% | 25.1% | vac 4.8% |
| 2023 | 51.8% | 30.4% | 35.5% | 39.2% | 44.1% | 37.0% | vac 19.0% |
| 2045 | 48.7% | vac 1.7% | 7.4% | 14.4% | 24.2% | 28.1% | vac 86.7% |

The concave shapes the issue suggested make things worse at this playthrough's GDP per head. `log` and `sqrt` rise steeply just above £1: at £25, X is 7.0 (log) and 4.9 (sqrt) against 2.5. They leave France at 66% and 61% slack and cut China's points by 63% and 49%. A world-relative curve (X from GDP per head over the world's) gives France almost nothing to pay, since it sits at 2.2–2.4× the world average, and runs into vacancies from 2033.

`python3 scripts/analysis/econ_construction_counterfactual.py --series FRA,union,GBR,CHI` prints every series and shape, and the per-interval checks.

## The structural sim

`econ_growth_sim.py` steps one country yearly. Its parts:
- **Sectors.** Seven level-bound sectors, each a representative building: wheat farm, coal mine, food industry, steel mill, semiconductors, railway, and `other`. Two demand-bound ones: urban centres and the construction sector.
- **Construction.** It's bought at the cost curve, and its levels follow the playthrough's realised allocation.
- **Automation.** Each sector picks a tier as a best response: the tier that saves most at the current wage, taken once its saving over the current tier repays the five-year retooling charge. That charge is itself multiplied by the cost penalty, and it raises the wage at which a tier is taken to 2.3–2.5× its breakeven at X = 0 and 7–8× at X = 4.
- **Labour.** Hiring draws from the unemployed, then from peasants above the land law's floor. Wages rise with vacancies and are capped by the 0.25 margin. The unemployed return to subsistence only while welfare pays less than it does.
- **Diagnostics.** Mode 1 and mode 2 (thresholds are parameters; mode 2 no longer requires wages at the floor), the turn year (wages reach the first technology-unlocked automation tier's breakeven in sectors holding half the jobs), the first adoption year, and catch-up measures.

Every mod number is read from the files at load.

**Calibration** (`econ_sim_calibrate.py fit`). Structural parameters are fitted on France's core and shared by every scenario, and behaviour per scenario (investment shares, queue, AI lag). The fit runs multi-start coordinate descent to convergence, scoring ln GDP per head, ln population, ln points a week and ln wage plus the two slack shares. The calibration runs use `HISTORICAL_CURVE`.

| scenario | loss | targets |
|---|---|---|
| France's core | 11.0 | 22 |
| AI Britain (to 1990) | 33.9 | 8 |
| AI China | 108.5 | 22 |
| whole union (not fitted) | 77.4 | 22 |

**The hindcast fails: `econ_sim_calibrate.py check` reports 154 misses.**
- The fitted France matches the playthrough's wage path, points a week and GDP per head to 2023, but only with no slack at all: peasants are gone by 1976 and unemployment sits at about 1%, mode 1 from about 1960. The saves hold 15–30% peasants and 3–36% unemployed throughout.
- Some fitted values are compensations, not estimates of the game. The wage floor is driven to about 0, the workforce share is 0.25 against 0.50–0.61 observed, and the construction-good price is 0.60 against 0.91–0.95.

**What the model lacks**, in order of weight. Each is a design choice, so none was added overnight.
1. **A ceiling on demand-bound jobs.** Service jobs follow GDP with no price or profit gate, so they absorb every idle worker. In the saves, France's service employment rose to 79M in 1998 and fell to 41–64M from 2023 while GDP kept rising: the urban-centre price collapse (spec § 4.4). A services price that falls as capacity outruns demand is the missing piece.
2. **Something that holds peasants.** In the sim, peasants leave for any job paying 1.1 × subsistence, while France's core kept 15–19% peasants from 1986 to 2045 under collectivized agriculture, a law with no employment floor.
3. **Population per country.** One growth rule fitted on France gives China 7.4 billion people (×6.25) and Britain 4.5× too many. France's core grew 12.5× (46.8M to 584M), probably through migration into the player's rich core, which the spec makes a non-goal.
4. **Wages that rise without a shortage**, and a price index. The sim's wage rises only with vacancies, while the game's nominal wage rose 44× under 30% unemployment. The SoL-expectations push and price drift would cover it. With one constant price level, the fit can't follow both slack and wages.

Smaller limits:
- The observed per-project cap (278–365 in 2043–45) is above the tech ladder's 140; companies, principles and `too_much_private_construction` aren't in it.
- `price_level` does two jobs.
- The observed value added used for `k_va` is net of maintenance, which `step` subtracts again (about 8% for light industry).
- `other`'s staffing is frozen at its 1867 figure.
- Annexations add people and levels to the union but no new ownership.

Build-time departures from the plan, each on evidence:
- **Allocation is the realised construction.** The plan said to take it from `investment_by_type`, but that is the pool's *inflow* by the building that paid it: company HQs, financial districts and manor houses, none of them buildable. Used as the plan said, China would build nothing for 60 years.
- **k_va is 1.0** where a sector's start value added is negative.
- **The fit is multi-start and converged,** not four sequential rounds.

## First sweep (uncalibrated model, mechanics only)

`econ_growth_sim.py sweep`, run on the fitted parameters. `linear` is the mod's curve as shipped, capped at +100%. `slope:0.5` halves its slope, and `none` removes it. A cap above +100% equals `linear` now.

**Read these rows as the model's mechanics, not the game.**
- The fitted model is labour-bound from about 1960 (mode 1 for 75 years), unlike the playthrough, so curve shapes barely move it.
- The mode-2 years come from the years before it turns.
- The poor types are cap-bound most years: the per-project cap ladder, not the curve, limits them.
- The AI series stop where the game's AI Britain was absorbed (1990), and the AI's schedules are held flat after its last point.

| Setting | Type | Turn year | Adoption year | Peasants < 5% | Peasants + unemployed 1950 / 2000 / 2045 | Years in mode 1 / mode 2 | Binding: money / cap / labour | GDP per capita 2045 | Take-off year | Take-off to < 10% peasants (years) | Growth vs type 1 (x) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| linear | player_rich | 1973 | 1927 | 1960 | 31.3% / 0.8% / 0.5% | 75 / 39 | 0 / 94 / 182 | 93.5 | 1892 | 67 | 1.00 |
| linear | player_poor | — | — | — | 80.4% / 77.0% / 64.3% | 0 / 39 | 2 / 127 / 131 | 10.8 | 1876 | 128 | 1.07 |
| linear | ai_rich | — | — | — | 46.6% / — / — | 0 / 71 | 0 / 100 / 116 | — | 1882 | — | 1.02 |
| linear | ai_poor | 1937 | 1947 | — | 47.8% / 29.7% / 29.3% | 0 / 91 | 1 / 163 / 140 | 13.2 | 1880 | 141 | 1.92 |
| slope:0.5 | player_rich | 1966 | 1925 | 1956 | 18.4% / 0.8% / 0.5% | 79 / 36 | 0 / 97 / 180 | 94.8 | 1892 | 63 | 1.00 |
| slope:0.5 | player_poor | — | — | — | 80.4% / 76.9% / 64.1% | 0 / 39 | 2 / 128 / 131 | 10.9 | 1876 | 128 | 1.06 |
| slope:0.5 | ai_rich | — | — | — | 46.1% / — / — | 0 / 71 | 0 / 101 / 116 | — | 1882 | — | 1.01 |
| slope:0.5 | ai_poor | 1937 | 1947 | — | 47.7% / 29.5% / 29.0% | 0 / 91 | 1 / 163 / 140 | 13.3 | 1880 | 141 | 1.89 |
| none | player_rich | 1958 | 1922 | 1947 | 1.2% / 0.8% / 0.5% | 94 / 24 | 0 / 110 / 182 | 99.8 | 1892 | 52 | 1.00 |
| none | player_poor | — | — | — | 80.4% / 76.9% / 63.9% | 0 / 39 | 2 / 128 / 131 | 10.9 | 1876 | 128 | 1.05 |
| none | ai_rich | — | — | — | 45.7% / — / — | 0 / 71 | 0 / 102 / 116 | — | 1882 | — | 1.01 |
| none | ai_poor | 1937 | 1947 | — | 47.7% / 29.3% / 28.1% | 0 / 91 | 1 / 163 / 139 | 13.5 | 1880 | 141 | 1.86 |

## Open questions for the owner

1. **What sets wages in the engine?**
   - The design assumed labour scarcity raises wages and rising wages make automation pay.
   - The playthrough's aggregate wage rose 44× with a third of the workforce idle, which points to the margin rule and the SoL-expectations push.
   - Yet steel and motor workers in 2045 earned £0.1 a week against £1.75–3.9 of value added each.
   - Which picture is right decides what "the turn" means, and whether the structural sim should model wages from expectations rather than vacancies.
2. **What holds France's last 15–19% of peasants** under collectivized agriculture? If it's a land floor or geography the sim should model, the absorption above is optimistic for peasants.
3. **The early target.** Peasants near zero by the 1950s needs more construction before 1954 than the curve can give, since the penalty was small then. Candidate levers: the construction sector's labour per point (about 12× vanilla's), the investment share, and the late cost tiers (2,000–10,000 points a level).
4. **The ministries' construction penalty** compounds with the curve (+5% a level each, so +70% at levels 6 and 8). Is that intended at this size?
5. **The structural sim's next step.** Build the four missing mechanisms above, then refit, or keep the data counterfactual as the tuning tool for now.

## How to run

```bash
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python   # the venv; standard library only, but run from the repo root
$PY scripts/analysis/econ_construction_counterfactual.py --series FRA,union,GBR,CHI --curves historical,current,capped:1.25,none
$PY scripts/analysis/econ_growth_sim.py sweep --scenarios player_rich,player_poor,ai_rich,ai_poor --curves linear,capped:1.25,slope:0.5,none
$PY scripts/analysis/econ_growth_sim.py run --scenario player_rich --set fill_rate=0.3 --csv /tmp/run.csv
$PY scripts/analysis/econ_sim_calibrate.py check      # after a change to PMs, cost tiers or construction techs
$PY scripts/analysis/econ_sim_calibrate.py fit --out scripts/analysis/econ_sim_params.json
```
