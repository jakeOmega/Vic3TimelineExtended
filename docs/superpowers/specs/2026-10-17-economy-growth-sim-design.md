# Economy growth sim: design (#1034)

Status: for the owner's review, 2026-10-17 (builder check done, owner answers in).

## 1. Intent

The owner's EU game shows the mod's late economy growing too slowly in the
wrong way. In 2045 a third of the people are still subsistence peasants and 45%
of the rest of the workforce has no job, even though the country is rich. The
owner wants a **reusable tuning tool**: a fast, approximate Python model of one
country's economy, stepped yearly. You change a parameter, in the mod or on the
command line, and see what happens to the shape of the economy. It is not a
one-off study.

The owner names two failure modes. The tool's job is to land between them:

- **Mode 1, too fast (where vanilla tends).** The economy is bound by
  population. Peasants plus unemployed are well under 1% of the workforce. New
  buildings struggle to fill even when the player builds the most productive
  ones. Private investment finds nothing to build. With no slack, there is no
  room to move people from low-productivity jobs into higher-productivity ones.
- **Mode 2, too slow (where the mod is now).** Even a very successful country
  keeps many peasants and unemployed. Automation is useless, and more
  population is a burden.

The owner wants to land **closer to mode 2 than vanilla does**, with neither
mode happening often. The goal balances realism, fun and balance; real history
is a guide, not the only consideration.

## 2. Targets (owner, 2026-10-17)

- **Labour scarcity is a gradient that shows up in wages.** A well-run rich
  country should first run short of workers somewhere between about **1860 and
  1920**. Buildings then compete for workers, wages rise, and the first
  automation tiers pay. The mod's automation PMs are designed for this: each
  tier pays once wages pass the `# Wage breakeven:` written on it, and the
  first ones (steam donkey and its peers) are cheap and historically early.
  This happens while peasants still exist.
- **Peasants close to zero in a rich country by about the 1950s.** Peasants
  are people outside the money economy; the rural people of the modern era are
  farmers or other classes.
- **Unemployment is not a target on its own.** A rich modern country that
  takes the automation ladder ends with a few percent unemployed, and could
  have none by not taking it.
- **Player economies first, AI economies too.**
- **Poor starts follow real catch-up growth** (owner, 2026-10-17): the Asian
  tigers, China and the like. Peasants are people outside the national market
  economy, not everyone who farms, so the share should fall faster than
  historical farm employment did. My reading of history, for the owner to
  correct:
  - South Korea's farm share of jobs fell from about 63% in 1963 to 18% in
    1990, and Taiwan's from about 50% in 1960 to 13% in 1990. China's fell
    from about 70% in 1978 to about 25% by 2020, while far more of its
    farmers joined the market economy.
  - In those take-offs, GDP per head grew 6–9% a year while the rich frontier
    grew about 2%.
  - **So the target:** once a poor country takes off (it has the techs, the
    laws and the investment), its peasant share halves about every 15 years
    or faster. It goes from over half to under 10% within about 35 years of
    take-off, and its GDP per capita grows several times faster than the rich
    country's meanwhile.
  - The same applies to a poor region joined to a rich country, counted from
    when it joins: for example, the EU's Balkans should be under 10% peasants
    about 35 years after joining.
  - The AI may be slower than a player but should show the same shape. A
    curve that leaves a poor country flat is failing its catch-up purpose, as
    stated in the script's own header.
- **Qualifications don't bind** past the first couple of decades. The sim
  assumes a qualified workforce throughout.

## 3. Goals, non-goals, anti-goals

**Goals**

1. A sim in `scripts/analysis/` that reports, per country type and lever
   setting, the yearly path of:
   - peasants, unemployed and employed;
   - jobs and building levels by sector;
   - the wage index and which automation tiers pay;
   - investment, construction points and their cost;
   - GDP per capita and the construction cost penalty;
   - which constraint binds and whether the year is in mode 1 or mode 2.
2. Every mod number it uses is read from the mod files at import, as
   `banking_cycle_sim.py` does with `ModConstants`. A renamed or deleted
   constant fails loudly. Retuning the mod retunes the sim without editing it.
3. Any lever can be overridden on the command line and swept, and a sweep
   prints the summary table in § 9.
4. It is calibrated loosely against the owner's continuous playthrough
   (§ 7): it should look right, not fit exactly.
5. A repo tool that extracts that calibration series from saves, so the next
   playthrough can be read the same way.

**Non-goals**

- A goods market. VA is priced at base `cost`, except services, the
  construction good, and one calibrated price-level factor (§ 5.6).
- Trade, per-state geography, migration, the per-pop budget, qualifications.
- The engine's hiring gates (margin ≥ 0.25, < 50% staffed to raise wages,
  profit pauses) and the SoL-expectations wage push, ported rule by rule. The
  sim uses one fitted wage rule and one fitted fill parameter instead. The
  research found the rules (§ 4.2) but not enough of their combined effect to
  port them faithfully.
- Changing any mod script. This issue builds the tool and runs the first
  sweep. The cost-curve change is a follow-up the owner picks from the table.

**Anti-goals** (would make it a failure even if it runs)

- A model so detailed it needs the game, takes minutes per run, or can't be
  read in an afternoon.
- Hard-coded mod numbers that drift silently from the script.
- A sweep that promises a result the binding constraint won't allow, such as
  a cheaper cost curve "fixing" a year where the per-project cap or labour
  binds.

## 4. What the research found

These are the mechanics the model must reflect. File references are relative
to the repo unless they start with `V/` (vanilla 1.14.5 `game/common`).

### 4.1 Construction (market rule, the default)

- `free_market_construction_rule` defaults to the market
  (`common/game_rules/extra_game_rules.txt:226`). Construction Sector buildings
  are ordinary private industry that sell a **construction good** (base price
  1000). `te_construction_market_site` turns one good into one construction
  point. The treasury pays for the government queue, and the investment pool
  pays for the private queue.
- **The cost scaling means more goods per point.** A point needs
  `1 + X` goods, where `X = construction_cost_scaling_mult`, combined
  multiplicatively with other `goods_input_construction_mult` sources. The same
  money therefore buys about `1/(1+X)` the points. The saves confirm the price
  per point: FRA 1917 paid £1,584 a point at X = 0.666; EUN 1998 paid £4,925 at
  X = 4.41. Both match `1000 × (1+X) × p`, with the market price `p` at 0.91–0.95.
- **The same `X` also multiplies every building's maintenance.** Buildings
  burn 0.05–0.2 construction goods a level each week, by tier, on 74 building
  types (`docs/systems/mod_systems.md` § Maintenance tiers). `X` also
  multiplies **retooling**: `pm_retooling` is `goods_input_construction_mult =
  10` on the building for 260 weeks
  (`common/static_modifiers/extra_modifiers.txt:408`,
  `common/defines/extra_defines.txt:7`). So a rich country pays more to switch
  to automation, and pays it for five years.
- **Cost per level.** Vanilla tiers run from 100 to 800 points. The mod adds
  `super_high` 2,000, `mega_high` 5,000 and `extreme` 10,000
  (`common/script_values/extra_script_values.txt:89-100`). Late buildings use
  them: semiconductors and the fabricator cost 10,000, network infrastructure
  and robotics 5,000, renewables 2,000.
- **Construction labour.** The mod's Construction Sector employs 4,570–7,000 a
  level for 1–16 goods a week (`common/production_methods/extra_pms.txt:16315-16630`),
  about 12× more labour per point than vanilla. In EUN 1998, 11,000 sector
  levels employed 50.5M people, 8% of the workforce.
- **Per-project weekly cap** (`country_max_weekly_construction_progress_add`):
  base 10, raised by techs, principles and companies (EUN: 115 in 1998, 440 in
  2045). In both probed saves, points per week were about equal to the cap ×
  active projects, but the queue was 5–10× longer than the active set, so money
  bound, not the cap.
- **Private investment.** The pool settles at about 24 weeks of inflow
  (`common/script_values/te_construction_market_target_values.txt:12-21`).
  Private construction spend was 12.4% of GDP in FRA 1917 and 13.4% in EUN 1998.
  Vanilla's free `country_gdp_construction` points are removed
  (`extra_modifiers.txt:218`).

### 4.2 Labour (vanilla rules; the mod overrides none of these defines)

- A pop switches jobs for a **10% higher wage** (`MIN_RAISE_TO_HIRE`). Peasants
  leave subsistence for any job that beats their in-kind income by that
  margin. Subsistence takes back only the unemployed, and only at a **30%**
  premium (`V/buildings/12_subsistence.txt`, `hires_unemployed_only = yes`).
- **Land laws cap how low peasants can go.** Serfdom and Manorialism keep an
  employment floor of 0.5. Only laws with no floor (Tenant Farmers onward)
  allow near-zero peasants (`V/laws/00_land_reform.txt`).
- **Wages.** A building raises its base wage, by up to 10% a week, for
  unfilled jobs only while it is under 50% staffed, or when its workers sit
  below 0.9× the wealth their expected SoL calls for. Either way it needs a
  margin of at least 0.25. It cuts wages at a margin of 0.15 or below. The
  mod's SoL Expectations system moves expected SoL toward actual SoL
  (10-year half-life), so wages can climb without a labour shortage.
- **Welfare** pays up to a fraction of the normal wage. UBI makes that 1.0 per
  Social Security level, and post-scarcity 5.0. Peasants get none (vanilla
  welfare tops up wages only).
- **Population.** The mod's birth and death curve peaks at SoL 18 (+2.6% a
  year) and turns negative at SoL 35 and up (−0.24%), before modifiers
  (`common/defines/extra_defines.txt:79-147`).

### 4.3 Output per worker over the eras

The second hypothesis is built into the PM ladder. From early to late game,
VA per level rises 10–50×. Staff per level falls from about 5,000 to about
2,000, and to 10 (or 0 plus a fixed crew of 1,000 per building) under full
automation. Tech throughput modifiers are small. Economy of scale adds 1% a
level up to a cap that techs raise from 20 to about 260
(`economy_of_scale`, `building_economy_of_scale_level_cap_add`). Automation
breakevens run from £0.06 to £0.4 a worker a week, and £1–1.4 for the
fab and power tiers. The `# Employment:` and `# Wage breakeven:` comments
count only the PM's first `level_scaled` block (`pm_costs.py:96-105, 221`),
so they ignore the fixed crew.

### 4.4 Which jobs are missing (EUN 2045)

From the save, non-subsistence buildings employ 341M against a capacity of
503M. Urban centres hold 141M of the 162M vacancies (197,000 levels, 41%
staffed). The owner's in-game read (2026-10-17): urban centres hire until the
services price falls too far to pay (Bavaria's services at £5.0, −83%). The
same happens to Construction Sectors. Other buildings sit near full
employment. The urban-centre vacancies are a symptom: a stronger rest of the
economy would buy more services and hold their price up. Urban centres are
`buildable = no`; their levels come from urbanization.

## 5. The model

One country, stepped yearly, from a start year (1836 or a save date) to an
end year (default 2050).

### 5.1 State

- **Population and workforce**, with the workforce split into peasants,
  unemployed and employed. Owner (2026-10-17): Demographics on is the ideal,
  but a simplified model is fine, and populations within about a factor of 2
  of the game's are good enough. So the population model is a yearly growth
  rate as a function of income per head and era, fitted to the calibration
  game's population path, which ran with Demographics on. The workforce share
  of the population is fitted the same way. No cohort model. Reusing
  `demographics_model.py` is an option if the fit fails the factor-of-2 test.
- **Subsistence capacity**: the peasant slots arable land holds, with the land
  law's floor and reserved share.
- **Sectors**, each with: levels; the PM tier in use and the tier the
  country could use; employment per level; VA per level at base prices;
  construction cost per level; maintenance tier; economy-of-scale group.
  A sector is one representative building or a small weighted basket.
  Default set (builder's call to refine): farming, mining, light industry,
  heavy industry, high-tech, power and infrastructure, plus the two
  demand-bound ones below.
- **Wage index**: one number per country, in £ per worker per week.
- **Construction**: the pool, government construction spend, points bought,
  and the queue by sector.
- **Tech**: the era reached, from a per-scenario era-arrival table. It gates
  PM tiers, cost tiers, economy-of-scale caps and the per-project cap.

### 5.2 Two kinds of sector

- **Level-bound** (most sectors). Jobs = levels × staff per level, and they
  fill unless the workforce is exhausted. New jobs come only from
  construction.
- **Demand-bound** (urban centres, Construction Sector). Jobs follow spending,
  not capacity. Service jobs follow the income of the rest of the economy.
  Construction-sector jobs follow points bought × labour per point, from the
  sector's current PM.

### 5.3 Each year

1. **Tech.** Advance the era. This unlocks PM tiers and cost tiers for new
   levels and raises the economy-of-scale and per-project caps.
2. **Automation.** For each sector, take the next tier when the wage index
   has passed its breakeven by enough that the saved wages repay the
   retooling charge (maintenance × 10 × (1+X) for 260 weeks) within a payback
   horizon. The player takes it promptly; the AI lags, per the scenario.
   Taking a tier lowers staff per level and raises VA per level.
3. **Income.** VA = Σ levels × VA per level × throughput (economy of scale and
   era throughput) × price level. GDP per capita feeds the cost curve, giving
   X for this year.
4. **Investment.** Private pool inflow is a share of VA (fitted; about 13% of
   GDP in the probes). Government construction is a share of VA too, also
   fitted.
5. **Construction.** Points = spend ÷ (1000 × p × (1+X)), capped at the
   per-project cap × queued levels. Spend on maintenance comes first.
   Allocation across sectors follows the scenario's era-based shares, taken
   from the saves' investment by building type. The model doesn't optimise
   allocation, since that would need a goods market.
6. **Jobs and hiring.** Level-bound jobs plus demand-bound jobs make up the
   jobs. They fill from the unemployed first, then from peasants, up to a
   fitted fill rate a year. Peasants go only to jobs paying 10% over
   subsistence income, and never below the land law's floor.
7. **Wages.** If level-bound jobs go unfilled, the wage index rises; if
   workers sit idle, it drifts to the floor. The floor is the welfare
   fraction of the normal wage, or subsistence for peasants. The rule is a
   simple fitted step, not the engine's weekly rules.
8. **Diagnose** (§ 5.5).

### 5.4 Which constraint binds

Every year the sim names the tightest of four constraints:

- **Money**: spend ÷ price per point;
- **The cap**: the per-project cap × queue;
- **Labour**: unfilled level-bound jobs above a threshold;
- **Demand**: demand-bound sectors' price floor (reported, not acted on).

A lever that loosens one constraint can't help in a year another binds. The
sweep table reports binding years per constraint, so the owner can see that.

### 5.5 Mode classification (thresholds are parameters)

- **Mode 1**: peasants + unemployed < 1% of the workforce, and labour binds.
  The draft's third condition, investment going unspent, isn't modelled: the
  sim spends all investment up to the cap (build-time ruling R28).
- **Mode 2**: the country is rich (GDP per capita ≥ a threshold, or the year is
  past the target turn), and peasants + unemployed > 10% of the workforce. The
  draft also required the wage index to sit at the floor. The calibration
  series showed mode-2 slack alongside wages that rose 44× (build-time ruling
  R34), so that condition is dropped.
- Otherwise healthy.

**The turn year** (my call) is the first year the wage index passes the
tier-1 breakeven of the sectors holding half of the level-bound jobs. Tier 1
is the first tier of each sector's main automation group: steam donkey for
mines, mechanized looms for textiles, watertube boilers for motor industry,
and so on. Side groups such as mine rail transport (breakeven 0.03) don't
count. The sim computes every breakeven itself from the PM blocks: vanilla's
from `vanilla_parsed/`, which carries no cost comments, and the mod's from its
files. The computed breakevens include fixed crews, which the `pm_costs.py`
comments leave out (§ 4.3).

### 5.6 Price level

Base-price VA doesn't match the saves' nominal GDP; prices drift, partly
through the mod's monetary system. One price-level factor per scenario is
fitted to the series' GDP, and services get their own price, which falls
when service capacity outruns demand. The construction good's price `p` is
read from the saves (0.91–0.95 of base in the probes) and held constant by
default.

## 6. Country types

v1 runs four types, all starting in 1867 from the calibration game's
`french republic_1867.v3`, which holds every country (my call, made while
planning). The AI countries in that game appear in every later save, so the
AI types get calibration series of their own.

1. **Player, rich start.** France (country id 4), on its core states.
   Allocation shares and era arrival come from the same playthrough.
2. **Player, large poor start.** China's 1867 state, run with player
   behaviour: type 1's era-arrival table (a lag parameter defaults to 0,
   since a player pulls tech along) and type 1's allocation shares.
3. **AI, rich start.** AI Great Britain in the same game, with its own era
   arrival, allocation and series. Automation lags.
4. **AI, poor start.** AI China in the same game, likewise.

The observer runs (leaders 202 techs in 1972, 219 in 1988, 245 in 2015)
remain a cross-check on AI tech pace.

Players and AI differ only in tech pace, automation lag and investment
allocation. They don't differ in any rule.

## 7. Calibration and validation

**The data.** Playthrough `c480d386` is one continuous 1.14.5 game, 1836 to
2045.12. The player is country id 4 throughout: FRA, then the French Commune,
then FRA, then EUN. About 25 saves (1867, 1917, 1949, 1954–1976, 1986, 1990,
1998–2045) each carry:

- `pop_statistics`: salaried, subsisting and unemployed workforce, by
  profession;
- the budget: investment pool, pool spend on construction, investment by
  building type, and `base_wage`;
- active construction queues, with speed and the cap;
- buildings, with levels, staffing and PMs;
- the variables, including `prior_construction_scaling`.

Each save also holds the engine's **weekly** GDP history for the past 100
years, so GDP is weekly from 1836.

**Territory changes** (my call). The country grows from 91M people as FRA in
1917 to 1.2B as EUN in 1998. In 2045, peasants are 20% of Western Europe's
people but 51% of Eastern Europe's and 67% of the Balkans'. Much of the 36%
headline comes from annexing poor regions. So the hindcast runs on France's
core: the states the country held in 1867, a constant territory. It reads
those states' pops and buildings, not the country totals. The whole union
is a second check, with annexations entered as outside events that add
people, peasants and levels. Western Europe's 20% is still far from the
target, so the problem doesn't go away on the core.

**Population in the series** (my call). The calibration game runs the
`demographics_full` rule. The late-births bug fixed by #964 zeroed births in
late-game states before 2026-10-16, which covers the saves from about 2011 to
2036. It touched under-fives and the cohorts reaching working age after about
2025, a small share of the workforce, so the hindcast uses the workforce as
recorded and checks how sensitive the result is to it. The token map and probe scripts are in
`~/src/vic3te-save-analysis-2026-10-17/series_probe/`. AI comparisons use the
observer runs and `Baseline.v3` (2062).

**Steps**

1. **Read the series.** Per save: GDP per capita, `prior_construction_scaling`
   against the formula's raw value, peasant share, unemployment, levels and
   jobs by sector, points per week, pool spend and the price per point. The
   1998 penalty, 4.41, is about 1.8× the raw formula's 2.4 at GDP per capita
   25. Reconcile that first: other multipliers, a different population, or a
   bug in the adjusted multiplier.
2. **Fit** the free parameters for type 1: investment shares, fill rate, wage
   step, price level, service demand. Fit them to the series' peasant share,
   unemployment, points per week and GDP per capita.
3. **Validate by hindcast.** Run type 1 from the 1867 save with the game's
   own settings. The peasant and unemployment paths should look like the
   saves': same shape, and turning points within about a decade.
4. **Spot-check AI** types against the observer runs and the 2062 baseline
   (rich AI GDP per capita 18–27, penalty +170–260%).

## 8. Levers

All are overridable; each defaults to the mod's current value.

- **Construction cost curve shape** (the first lever, owner's choice). Today
  it is linear in GDP per capita: 0 at 1× reference (1), +1000% at 100×
  (`construction_cost_scaling_mult`). Shapes to try: a lower ceiling or cap;
  concave (log or square root); relative to the world's GDP per capita (from
  all countries' GDP rings); none (vanilla). For the world-relative shape, the
  world path is fixed, taken from the calibration game (my call). Changing the
  curve for every country would move the world path too, which needs several
  coupled countries; the doc states that limit.
- Cost tiers of late buildings (2,000–10,000).
- The per-project cap ladder.
- Construction-sector labour per point.
- Employment per level for late PMs, and the automation breakevens.
- Throughput and economy-of-scale caps by era.
- Investment pool contributions.
- Maintenance rates and the retooling charge.

## 9. Output

A sweep prints one row per lever setting × country type:

| Setting | Type | Turn year | Peasants < 5% | Peasants + unemployed 1950 / 2000 / 2045 | Years in mode 1 / mode 2 | Binding: money / cap / labour | GDP per capita 2045 |
|---|---|---|---|---|---|---|---|

For the poor types (2 and 4), and for the union's annexed regions in the
whole-union check, three more columns test catch-up (§ 2):
- the take-off year;
- years from take-off to under 10% peasants;
- GDP per capita growth over the take-off against type 1's over the same
  years.

A single run can also write its yearly path as CSV. The first deliverable
sweep covers the cost-curve shapes for all four types, with a short written
read of which shapes land in the target band.

## 10. Deliverables

- `scripts/analysis/econ_growth_sim.py`: the sim, with its CLI and sweep.
- `scripts/analysis/econ_save_series.py`: the series extractor. It lifts the
  fixed-point tokenizer and token map into the repo; output is one JSON
  record per save.
- A small committed calibration dataset, the extracted country-level series
  for `c480d386` (JSON, no save content beyond those numbers).
- `test_econ_growth_sim.py`. It checks that the constants are read from the
  mod, that the price per point and the cost curve match the script's
  formulas, that the 1917 and 1998 probe values reproduce, and that the
  hindcast stays inside its band. It needs no game.
- A doc, `docs/systems/economy_growth_sim.md`, with the model, the
  calibration, the first sweep's table and its read, plus a line in
  `docs/guides/python_tools.md` and `docs/README.md`.
- Player guide: no player-facing change in this issue.

## 11. Doc errors the research found

These ship with this work or a follow-up:

- `docs/vanilla/vanilla_economy_reference.md`:
  - :109 calls `min_raise_to_hire` a hiring-rate cap; it is a wage premium.
  - :233 cites `law_government_wages_*`, which doesn't exist.
  - :347 calls the free construction a flat +10. It was 2–10 by GDP, and the
    mod removes it.
  - :417 gives capitalists' pool contribution as about 20%; it is 30% in 1.14.
- The observer baselines README cites `current_gdp`, which is frozen at 1949
  because the GDP Growth Rate mod left the playset. Use the weekly GDP ring or
  `te_mon_gdp_last_year`.
- `docs/vanilla/vanilla_pops_reference.md:277,284` frames proportional hiring
  as "90%"; it is a 0.1 gap in fill ratio between professions.

## 12. Decisions

**The owner's** (2026-10-17): the targets in § 2, including the catch-up
model for poor starts; the two failure modes and landing nearer mode 2 than
vanilla; most levers in scope with vanilla values allowed; the cost-curve
shape first; player economies first; qualifications not modelled; urban
centres and Construction Sectors are limited by demand (§ 4.4); a simplified
population model within a factor of 2.

**Mine, for the owner to check:**
- the yearly step and the sector set (§ 5.1);
- fitted wage and fill rules in place of the engine's weekly rules (§ 3, § 5.3);
- allocation from the saves' investment shares, not optimised (§ 5.3);
- the mode thresholds (§ 5.5) and the turn-year definition, with breakevens
  computed from PM blocks (§ 5.5);
- calibrating on France's core states, with the union as a second check (§ 7);
- using the recorded workforce despite the late-births bug (§ 7);
- type 2 sharing type 1's tech pace (§ 6);
- a fixed world path for the world-relative curve (§ 8);
- no script change in this issue; the curve change is a follow-up (§ 3).
