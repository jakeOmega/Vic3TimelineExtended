# Demographics: age, sex, wealth and where people live — design (scoping draft)

> **Status: scoping draft, 2026-10-08, second round.** It widens the Wealth Concentration score from #822
> (`2026-10-08-inheritance-laws-design.md` §3) into a demographics system with its own panel. It covers what to
> track, what moves each number, what each number moves and what the player controls. The owner settled the first
> round of questions the same day (Decisions, below). §13 lists what is still open and §14 the engine checks that come
> first. Numbers are starting proposals for the calibration harness (§12), not decisions.

## Context

**The request.** A new tab with the country's demographics, tracked per state and updated yearly, since all of it moves
slowly:
- wealth concentration;
- how concentrated the population is (one metropolis against ten cities, New York against Texas);
- the age breakdown and the sex breakdown.

It should be moved by other systems (war dead are mostly men) and move them in turn (under the stricter child-labour
laws children don't work, so a fast-growing population has a lower workforce share). The player should be able to
steer it, and the weak Population Control law should become a real lever. The pillars are realism, fun and balance.

**What the engine gives us.** Pops have no age or sex. The only demographic axes are:
- **Workforce and dependents**, set by a working-adult ratio. Vanilla's default is a define outside the repo;
  `pop_types` sets aristocrats 0.2 and slaves 0.5. It is moved by `state_working_adult_ratio_add`: vanilla's
  women's-rights laws add 0.05 to 0.3, and Old Age Pension subtracts 0.01.
- **Birth rate and mortality**, from the standard-of-living curves in the defines plus `state_birth_rate_mult` and the
  `*_mortality_mult` family. The mod's defines (`common/defines/extra_defines.txt:79-88`) run births from 5.7% a year
  at SoL 0 down to 0.96% at SoL 35, and deaths down to 1.2%. A state at SoL 35 or above shrinks by 0.24% a year from
  the day it gets there, whatever its history.
- **Readable values**:
  - a pop's `total_size`, `wealth`, `standard_of_living` and `literacy_rate`;
  - a state's `state_population`, `total_urbanization`, `average_sol`, `state_unemployment_rate`, `gdp`, `migration_pull`
    and `modifier:<key>` totals;
  - a war's `num_country_dead(<country>)`.
- **Iteration.** Script values can walk pops and states (`te_inh_agrarian_share_value`, `country_max_state_population`).
- **What script can't read:** a pop's income, migration, and births. The GUI alone has
  `State.GetWeeklyPopNetMigration` and the Population panel's `PopsOverviewPanel.GetAverageIncomePoor/Middle/Rich`.

So age and sex must be **modelled**. The model takes engine readouts as inputs and drives the engine through modifiers.

**What the mod already has.**
- **Wealth Concentration** (`te_inh_concentration`, country, 0–100).
  - It drifts 3% a year to a target set by the inheritance law and its amendments.
  - It drives `inh_great_fortunes` / `inh_dispersed_wealth`. Each mixes country-scope clout with state-scope
    investment-pool and radical effects, all applied on the country.
  - The player sees it only in loc. Nothing under `gui/` reads it.
- **Family & Reproductive Policy** (`lawgroup_family_reproductive_policy`, `common/laws/extra_laws.txt:2553-2621`),
  the group the owner called "population controls".
  - Five laws, with only flat birth-rate and workforce modifiers, no amendments and no AI weights.
  - Population Control Measures' only benefit, +150 authority, is also what State Eugenics Program (another group)
    gives, and that law adds workforce and births on top.
- **Flat population modifiers in many places.** The Pill, second-wave feminism, Protected Class, vaccines, antibiotics
  and Biological Immortality set flat `state_birth_rate_mult`, `state_mortality_mult` and
  `state_working_adult_ratio_add`. The Natalism Initiative decree gives +50% births for 250 authority, which outweighs
  every law in the group.
- **Where people live.**
  - Migration Crowding: a yearly per-state density penalty, with `state_migration_crowding_density_mult`.
  - The world city ranking: `city_size`, `var:state_city_size_rank`, global monthly.
  - Internal Resettlement: `move_partial_pop` programmes, Planned Towns, per-region areas in
    `te_region_area_generated.txt`.
- **Deaths the mod causes.** Nuclear strikes store `nuclear_strike_killed_population` on the state. Violent Hostility
  kills 2–10% of a culture a year. The anti-war movement reads `num_country_casualties`.
- **Panels.**
  - The vanilla **Population** panel (`PopsOverviewPanel`; title `POPS_OVERVIEW_TITLE`, tabs "Overview" and
    "Detailed List") shows strata over time, SoL over time, spending and the pop list. The mod doesn't override it yet.
  - The state panel's Population tab has three 170 px subtabs: Statistics, Pops and Characters.
  - The history store draws column charts of stored samples.
  - A map mode can paint any per-state script value (`te_map_mode_script_values.txt`).

**Prior art.** The Demography Workshop mod (`3759720467`, `docs/systems/system_panels_feasibility.md` §7) gives every
state 17 five-year bands, updated monthly. The owner doesn't use it. §11.5 covers players who do.

## Decisions (owner, 2026-10-08)

| Question | Decision |
|---|---|
| Gameplay effects | **Yes.** The system is designed around them; a display-only setting exists only as a game-rule option |
| World population | **Retune it.** The share of women of childbearing age drives the birth rate and the share of old people the death rate. **Wealth, education and technology (birth control) drive fertility** and so long-run growth (§2.3) |
| Sex | **Track the female share of each band**, not the male share. Births then scale with *x*, not 1 − *x*, and the female population follows a steadier path (§3) |
| Wealth Concentration | **One score, kept per state** (§4.2) |
| Coercive pronatalism | **No separate mechanic.** The pro-natalist law's description stays open: "through propaganda, incentives, or even coercion". Players read what a given state does into it (§8.1) |
| Where the country view goes | **The vanilla Population panel**, as a new tab (§10) |
| One metropolis or several cities | **Design it** (§5.2): it interacts both ways with economic pull, infrastructure and Migration Crowding. Not the first priority |
| Game rule | **Yes**: Full / Display only / Off (§11.4) |

## Design rules (the pillars, made concrete)

1. **The engine counts the people; the model says who they are.** Each year the model's band shares are applied to the
   engine's population, so the panel and the engine never disagree on the total. The model sets birth and death rates
   through modifiers (§2.3) and doesn't move people.
2. **Track only what changes a decision or explains one.** Every number either moves something (§7) or shows the
   player why something moves.
3. **Laws act on inputs, and the model produces the consequences.** A law changes fertility, mortality or who works.
   The workforce and pension effects arrive through the model, with the real lag: fewer births today give fewer
   workers in fifteen years.
   - Flat modifiers that stand in for an age, fertility or survival effect move into the model (§8.4).
   - Ones that stand for women's or children's work stay.
4. **Slow clocks with visible momentum.** Each number moves over a generation, and the panel shows where it is heading.
   The fun is in seeing a window open twenty years ahead (§9, §10).
5. **Effects are deviations from a stated reference, and capped.** The reference structure is the 1836 equilibrium.
   Every state starts at the equilibrium of its own 1836 inputs, so nothing jumps on day one. A save from before the
   system starts each state at its equilibrium (the #822 pattern).
6. **Every number has a real meaning and an anchor value.** The sources are UN World Population Prospects (WPP) for
   ages and fertility, and the World Inequality Database (WID) and Lindert and Williamson for wealth. The panel uses
   real units: children per woman, years, a Gini coefficient, "the top tenth owns about X%".

## 1. What to track

| Stat | Scope | Source | Shown as |
|---|---|---|---|
| **Age structure**: eight ten-year bands, 0–9 … 60–69 and 70+ | state; the country's is the population-weighted sum | modelled (§2) | population pyramid |
| **Sex**: female share of each band | state | modelled (§3) | the pyramid's two halves |
| Derived: median age, dependency ratio, working-age share | state, country | from the bands | table, with a trend arrow |
| **Fertility**: children per woman, with its wealth, education and technology terms | state | modelled from engine inputs (§2.3) | table; the terms on hover |
| **Life expectancy** at birth | state | from mortality (§2.3) | table |
| **Net migration** last year | state | the residual after natural change (§2.4) | table |
| **Income inequality**: a Gini coefficient | state; country | computed from pops each year (§4.1) | table, map mode |
| **Wealth Concentration**: the #822 score, now per state | state; country (GDP-weighted) | modelled stock (§4.2) | bar with its target segment; "top tenth owns ~X%"; map mode |
| **National urban pattern**: the largest city's share, the effective number of cities | country | computed from states (§5.1) | label and figures |
| **Settlement pattern**: one metropolis or several cities | state | modelled stock (§5.2) | label, map mode |

**Left out:** ages on individual pops, single-year ages, age by culture or religion, and education by age. Each costs far
more than it returns at Victoria's level of detail.

**Why ten-year bands.** Every effect in §7 reads only a few band totals: the fertile ages, the workforce, the elderly
and the young adults. Four bands (0–14, 15–29, 30–64, 65+) would serve the economics. But a pyramid of four blocks
doesn't read as a pyramid, and the dents that wars and baby booms leave can't be seen working up through it.

- **Cost:** eight bands with a female share each make 16 state variables. The work is arithmetic, not pop walks
  (§11.3).
- **Limit:** band models blur echoes. In a test run, a ten-year boom spreads over about thirty years as it climbs.
  A dent from a big war stays visible.

## 2. The age model

### 2.1 The yearly step

Per state, as shares that sum to 1:

- **Births** = children per woman × women aged 15–44 ÷ 30, into the 0–9 band. Their female share is 100 ÷ (100 + the
  sex ratio at birth): 0.488 normally (§3).
- **Ageing**: a tenth of each band moves up a band each year; 70+ is the last.
- **Deaths**: each band loses its own rate, from a model life table at the state's life expectancy (§2.3).
- **Migration and other losses**: the residual from §2.4, given a migrant's age and sex profile.
- **Then** normalise to shares, and store the population for next year's residual.

### 2.2 Does it behave?

A throwaway Python sketch of the step, run with four bands and with eight, gives these equilibrium structures for
plausible parameters:

| Case | Children per woman | 0–14 | 15–64 | 65+ | Growth a year | Real anchor |
|---|---|---|---|---|---|---|
| 1836 agrarian (the reference) | 5.2 | 35% | 59% | 5–7% | +0.8 to +1.7% | Western Europe 1830s–1850s: 0–14 about 35%, 65+ 4–6% |
| High fertility, falling mortality (1950s) | 6.0 | 38% | 54% | 8% | +2.6% | developing countries 1950–70: 0–14 40–45% |
| Replacement fertility | 2.0–2.2 | 20% | 60–62% | 19–20% | about 0 | |
| Aged | 1.3 | 12% | 55–56% | 33% | −0.9 to −1.2% | Japan today: 0–14 11%, 65+ 29%, children per woman 1.2 |

**The transients carry the gameplay.**
- Drop fertility from 6 to 2 and the working-age share climbs from 54% to 64% over twenty years, then holds for about
  thirty. That is the **demographic dividend**. Real East Asian peaks reached 70–74%; the band model underestimates
  them because it blurs.
- Cut fertility to 1.3 after that and the share falls back to 57% by year 100, while 65+ reaches 30%.

Both appear without being scripted as events.

### 2.3 Births and deaths: the retune

**What changes in the defines.** The SoL curves stop carrying the whole demographic transition. They become the
**wealth** term only, as age-standardised rates (rates for the 1836 reference structure):

| Define | Today (a month) | Proposal (a month) | Meaning |
|---|---|---|---|
| `@max_birthrate` | 0.00475 at SoL 0 | about 0.0038 at SoL 8 or below | about 6.2 children per woman at the reference structure |
| `@min_birthrate` | 0.00080 at SoL 35 | about 0.0021 at SoL 35 and above | about 3.5 children: what wealth alone does |
| `@min_mortality` | 0.00100 | about 0.0003 | the reference structure's death rate at modern health. Age raises it: Japan's crude death rate is 13 per 1,000 because a third of its people are over 60, not because its health is poor |

The rest of the decline comes from the model's terms below. The mod's `pop_needs_curves` and the defines' growth
constants are tuned together in the calibration harness (§12).

**Fertility: wealth, education, technology.** The model works out a *desired* fertility and how much of the gap between
it and natural fertility the population can close. The *means* term is the technology. This is the "supply, demand and
means" view of the fertility transition.

- **Wealth**: the retuned SoL curve, applied by the engine.
- **Education**: desired × (1 − 0.4 × literacy). Literacy is the population-weighted figure from the yearly pop walk.
  Women's schooling is the strongest single predictor of fertility; literacy is the nearest proxy the engine has.
- **Child survival**: desired × (1 − 0.4 × (life expectancy − 30) ÷ 50), clamped. Parents stop insuring against child
  deaths a generation after the deaths stop.
- **Urban life**: desired × (1 − 0.2 × the urbanisation rate). Children cost more and earn less in a city.
- **Technology: the means.** The share of the gap a population can close:

  | Source | Means |
  |---|---|
  | Traditional methods (start) | 0.4 |
  | `vulcanization` (era 3: rubber condoms) | 0.55 |
  | `contraceptive_pill` (era 7) | 0.8 |
  | `modern_pharmaceuticals` (era 8: long-acting methods) | 0.9 |

  - **Access** multiplies the means: 0.3 + 0.7 × literacy.
  - **Laws** shift it: State-Sponsored Family Planning +0.1, Pro-Natalist Policy −0.15, Population Control +0.2.
  - The cap is 0.95.
- **The fertility factor** = 1 − means × (1 − desired). It is applied with the age-structure factor below.

**Age structure** (the owner's two shares):
- **Births** × women aged 15–44 ÷ that share in the 1836 reference.
- **Deaths** × an age-weighted death index ÷ the reference's. The weights are relative death risks, mostly on the old:
  0–9 1.5, 10–19 0.3, 20s 0.5, 30s 0.7, 40s 1.2, 50s 2.5, 60s 6, 70+ 20. Japan's structure today comes out about 3.7×
  the reference. Read from a high-health floor of about 3.5 per 1,000 a year, that gives its 13.

**Applied as** one births modifier (fertility factor × structure factor − 1) and one deaths modifier (structure factor −
1), refreshed yearly from the state pulse. The births modifier is clamped so that, with every other modifier, the total
stays above vanilla's −0.9. Every other birth and mortality modifier stays an input and is read through. That covers
vanilla's laws, events, starvation, devastation and pollution, global warming's heat and disease, and Forced
Heirship's rural cut.

**Sketch results** (the formula above, with plausible inputs):

| Case | Sketch | Real |
|---|---|---|
| Britain 1836 | 5.5 | about 5 |
| France 1836 (historical override: means 0.8, Forced Heirship) | 4.2 | about 3.8 |
| Britain 1900 | 3.9 | about 3.5 |
| The West 1950 (before the Pill) | 3.0 | 2.5 (Europe) to 3.5 (US) |
| The West 1990 | 1.4 | about 1.7 |
| India 1975 | 5.2 | about 5.2 |
| Niger 2020 | 5.0 | about 6.7. High desired fertility in the Sahel is a cultural term the sketch lacks; calibration decides whether to add one |

**Calibration targets for the retune.** Match the shape of world history and the UN's medium projection rather than an
absolute count. The game's own 1836 total sets the scale.
- **World multiples:** 1900 ≈ 1.5× 1836; 1950 ≈ 1.5× 1900; 2000 ≈ 2.4× 1950. The peak is about 10.3 billion in the
  2080s (WPP 2024), without era-12 technologies.
- **Regional shares:** Europe from about 22% of the world in 1850 to under 10% today. Africa from about 9% to 18%
  today, and about 38% by 2100.
- **Great-power ratios** at 1900, 1950 and 2000.

### 2.4 Migration, war dead and other losses

The engine moves and kills people; the model sees only the result. Each year:

1. **War dead.**
   - For every war the owner is in, read `num_country_dead(owner)` and take the change since the last pulse.
   - Share it out among the owner's states by their share of the country's soldiers (from the yearly pop walk).
   - The dead come from the 20s and 30s, about 95% of them men, so those bands' female share rises.
   - The mod defines a Women in Combat Roles modifier (`women_combat_roles_modifier`) that nothing grants yet. Whatever
     grants it should lower that share.
   - The war's counter disappears when the war ends, so snapshot it monthly or at war end (§14).
2. **Known kills.**
   - Nuclear strikes record their dead per state; they come from all ages and both sexes.
   - Resettlement records its arrivals and departures, with its programme's profile.
   - Violent Hostility's kills come from all ages.
3. **The residual**: the population change, less natural change, less (1) and (2). This is mostly migration.
   - A gain arrives with a migrant's profile: mostly people in their 20s and 30s. Before about 1900 a third of them
     are women, rising to about half by the mid-20th century.
   - A loss leaves with the same profile.
   - A residual under 0.3% of the population is treated as model error and spread over all bands. Otherwise the
     model's own rounding would make states look like migration hubs.

This makes frontier and immigrant states young and male, and emigrant states old and female, with no extra script.
That is what happened in the American West, Argentina, Australia, Ireland and southern Italy.

### 2.5 Starting values and new states

- **1836.** Each state starts at the equilibrium of its own inputs, taken from a lookup by fertility and life
  expectancy that a generator writes. Historical overrides:
  - France starts with fertility well below its neighbours'. Its transition began around 1800, and #822's Forced
    Heirship already pushes it there.
  - The US frontier states start young and male.
- **A state with no variables** (a new state, a split state region, an old save) starts at its equilibrium. A split
  state could copy its sibling's structure instead, since it is the same people.
- **Revolutions.** State variables stay on the states. The country's numbers are recomputed from them, so nothing is
  lost (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").

## 3. Sex

**Track the female share of each band.** Births need women, so the birth term is the female share times the band, not
one minus a male share. A war that kills half the young men leaves the female line almost untouched. The female
population, and the births it carries, stays on a steady path, while the male deficit works up the pyramid and out
within a lifetime.

**What moves it:**

| Source | Effect | Anchor |
|---|---|---|
| Sex ratio at birth | 105 boys per 100 girls normally: a female share of 0.488 | the biological constant |
| Sex-selective births | up to about 115–120 boys per 100 girls (female share about 0.46) under Population Control once prenatal sexing exists (§8.1) | China's sex ratio at birth reached about 118 in the 2000s |
| War dead | about 95% men, from the 20s and 30s | the Soviet Union in 1959: about 0.82 men per woman |
| Migration | before about 1900 a third of migrants are women, later half | California in 1850 was over 90% male |
| Longevity | women outlive men; the 70+ band's female share rises with life expectancy, from about 0.53 to 0.6 | |

**What it moves** (adults 20–59, capped, small on purpose; the evidence on effects is weaker than on causes):

- **More women than men** (after a great war):
  - fewer marriages, so births × the square root of (men ÷ women), at most 1;
  - more women at work (+ working-adult ratio);
  - support for women's-rights movements. Britain's "surplus women" after 1918 are the example.
- **Fewer women than men** (frontier, migrant-worker or sex-selected populations):
  - births fall on their own, since there are fewer women;
  - radicals and crime rise a little (Hudson and den Boer's *Bare Branches*), which feeds the policing laws.

## 4. Wealth

Two numbers, as economists keep them: a **flow** (how unequal this year's incomes are) and a **stock** (who owns the
capital). Both are kept per state. The stock is the #822 score.

### 4.1 Income inequality (state, computed yearly)

- **The measure.** A Gini coefficient from the state's pops. Pop income can't be read in script, but `wealth` can. A
  generator turns the wealth level into spending per head using the pop-needs curve from `pop_needs_curves`, as a
  proxy for income.
  - **Grouped form:** each stratum's share of people and of income, ordered lower < middle < upper. This takes one pop
    walk if a single walk can fill several sums (§14), or one walk per stratum.
  - **Or the engine's own figure:** if `wealth_share = { pop_type = X … }` reads as a value, it gives the share of
    wealth each pop type holds directly.
  - **Scaling:** the grouped Gini misses inequality within each group, so scale it to the anchors:
    - Britain about 0.5–0.55 in the 1830s and the US about 0.5 in 1870 (Lindert and Williamson);
    - Nordic countries 0.25–0.3 today, the US 0.39 after taxes, South Africa about 0.63.
- **The country** figure is the population-weighted Gini over all states' groups, not an average of state Ginis. The
  tab can show it beside the engine's own average income per stratum (`PopsOverviewPanel`), which the GUI can read.
- **Effects, light on purpose.** Vanilla already turns wealth into clout. Inequality mainly feeds the stock (§4.2) and
  the panel, plus two small effects:
  - relative deprivation: lower-strata radicals rise with the Gini above about 0.45;
  - an input to crime for the policing laws.

### 4.2 Wealth Concentration (per state, the #822 score)

**One score per state.** It keeps #822's 0–100 scale, its 3% yearly drift and its two modifiers' effects. Each state
drifts toward its own target. The country figure is the states' GDP-weighted average, kept in `te_inh_concentration`
so #822's loc and tooltips keep working. The panel shows the target's terms as bars (style guide rule 5) and a map
mode.

**The target** is a sum of terms around 50:

| Term | Scope | Proposal | Why |
|---|---|---|---|
| Inheritance law and amendments | national | today's targets re-centred on 50: Primogeniture +30, Testation +10, Customary 0, Forced Heirship −25, State Heir and Possession −50; amendments as now | #822 unchanged in effect |
| Taxes on wealth | national | Graduated Taxation −5; the tax code's dividend and estate settings when that rule is on | |
| Income inequality | state | +0.5 × (the state's Gini − 0.40) × 100, capped ±15 | fortunes grow from unequal flows: the rich save more |
| Land tenure (vanilla land reform laws) | national law × the state's agrarian share | Serfdom +15, Tenant Farmers +5, Commercialized Agriculture 0, Homesteading −10, Collectivized Agriculture −20 | land was most of the wealth in 1836, and it matters where the land is |
| Return on capital against growth (later phase) | national | from the banking system's policy rate against GDP growth | Piketty's r > g; only where the banking system runs |

**Shocks** jump the score instead of moving its target. They follow Scheidel's four levellers (*The Great Leveler*,
2017):
- **War** (every state): each year of total mobilisation −1, up to −10 a war; capitulation −5.
- **Devastation and occupation** (the states hit): local capital is destroyed, scaled by devastation.
- **Revolution** (every state, or the rebel states): a left revolution that wins, −20.
- **Money** (every state): a hyperinflation or banking crisis from the monetary system, −5 to −10, since bond fortunes
  vanish.
- **Events** (the states named): land reform, nationalisation and plague, −5 to −15.
- **Upward:** privatisation waves and financial booms, +5.

**The two modifiers split by scope.**
- **The state part** is refreshed from each state's yearly pulse with that state's score: investment-pool efficiency
  and radicals.
- **The country part** is refreshed from the country pulse with the national figure: Aristocrats' and Capitalists'
  clout.
- That is two state modifiers and two country modifiers in place of #822's two. Each keeps one refresh site.

**Migration.** Each state starts at its country's current score, then drifts.

**Readout.** Map the score to "the top tenth owns about X%": 0 → 40%, 50 → 65%, 100 → 90%. For scale, Europe's top
tenth held 85–90% around 1910 and 50–60% around 1970; the US is about 70% today.

## 5. Where people live

### 5.1 The national urban pattern (computed)

- **Urban population per state** = population × the vanilla urbanisation rate (`state_urbanization_rate`).
- **Primacy** = the largest city's share of the country's urban population.
- **Effective number of cities** = 1 ÷ the sum of each state's squared share. It answers "one metropolis or ten
  cities" in a single number.
- **Labels:** Primate (≥ 40%), Dominant (25–40%), Balanced (10–25%), Dispersed (< 10%).
- **Anchors** are the largest metro's share of the whole population; its share of the urban population runs a little
  higher:
  - Seoul's metro holds about half of Korea, and Buenos Aires about a third of Argentina;
  - Greater London about 13% of the UK, and the Paris region about 18% of France;
  - Berlin about 4% of Germany.

**Effects** (a choice, not a penalty):

| Pattern | The primate state | The rest |
|---|---|---|
| Primate or dominant | agglomeration: services and Urban Center throughput up, migration pull up | migration pull down, some regional resentment (turmoil effects) |
| Balanced or dispersed | none | none; it is the baseline |

**Levers:**
- **A Planned Capital decision** (Washington, Canberra, Brasília, Abuja, Astana): money and authority, the capital
  moves, and the new capital state gets a development modifier.
- **Regional development**: Internal Resettlement's Development Program and Planned Towns.
- Railways.

### 5.2 One metropolis or several cities (per state, modelled)

A Victoria state has one city hub and no cities below it, so this is a modelled stock. **Metropolitan share**, 0–100,
is the share of the state's urban population living in its largest city. It drifts 5% a year toward a target. It is
the system's most invented number, so it is built last (§12), with every effect small and every term on hover.

**What sets the target.** "Economic pull" is read here as jobs, wages and industry.

| Term | Direction | Why |
|---|---|---|
| National capital | up | government, finance and the court draw one city: Paris, Moscow |
| Port or financial centre (a Financial District, a port hub) | up | one gateway city: New York, Buenos Aires |
| Area (the generated region table) | down for large states | Texas is large enough for four metros |
| Extraction and farm employment share | down | mines, logging camps and market towns spread people out |
| Urbanisation | up, then down (an inverted U) | concentration rises in early urbanisation and falls once secondary cities mature (Williamson, 1965) |
| Infrastructure surplus over usage | down | rail and roads make secondary cities viable |
| Migration Crowding penalty active | down | congestion spills growth into satellite and secondary cities |
| Ministry of Urban Planning, Planned Towns, Planned Capital | down | green belts, new towns |

**What it moves** (both directions, so each loop settles):

| Effect | Mechanism | The loop it closes |
|---|---|---|
| **Crowding** | a metropolis is denser than the state's average, so `state_migration_crowding_density_mult` rises with the share | crowding then pushes the share down: congestion limits the metropolis |
| **Infrastructure** | a compact city is cheaper to serve, so `state_infrastructure_from_population_mult` rises with the share and falls for a dispersed state | a dispersed state runs short of infrastructure, which slows further dispersal until railways catch up |
| **Agglomeration** | services, finance and Urban Center throughput up with the share | the gains pull more migrants into the metropolis |
| **Fertility** | big-city housing lowers births (the urban term in §2.3, raised by the share) | an older, smaller metropolis over time |
| **Unrest** | one city concentrates its radicals: turmoil effects up a little | the Paris of 1848 |

**Labels:** Metropolis (≥ 60, New York), Leading City (40–60), Several Cities (20–40, Texas), Market Towns (< 20).

## 6. What feeds in

| Source | Into | How |
|---|---|---|
| SoL (wealth) | fertility, mortality | the retuned curves (§2.3) |
| Literacy (education) | desired fertility; access to the means | the yearly pop walk (§2.3) |
| Technology: `vulcanization`, `contraceptive_pill`, `modern_pharmaceuticals` | the means | tech tiers (§2.3) |
| Health laws, vaccines, antibiotics, pharmaceuticals | life expectancy, and through it desired fertility | mortality modifiers, read through |
| Every other birth or mortality modifier (vanilla laws, events, starvation, devastation, pollution, global warming) | fertility, mortality | read through, no new hooks |
| Family & Reproductive Policy | desired fertility, the means, the sex ratio at birth | §8.1 |
| Wars | the 20s and 30s, men | `num_country_dead` shared out by soldiers (§2.4) |
| Migration, mass migration, the migration laws | the 20s and 30s, more men early on | residual (§2.4) |
| Internal Resettlement | its programme's profile (Rustication takes the young, Managed Retreat the old) | its own counters |
| Nuclear strikes, Violent Hostility | all ages | recorded or residual |
| Child-labour, pension and retirement laws | who among the young and old works | participation weights (§7) |
| Ectogenesis (the Youth Center PM) | births depend less on how many women of childbearing age there are | weakens the women-15–44 term in states with the PM |
| Biological Immortality (era 12) | ageing stops | §8.3 |
| Cultural Hegemony (later phase) | desired fertility drifts a little toward the hegemon's | the "soap-opera effect": Brazil's fertility fell where TV novelas reached (La Ferrara et al., 2012) |
| Inheritance, land tenure, taxes, war, devastation, revolution, banking crises | Wealth Concentration | §4.2 |
| Capital, ports, area, industry, infrastructure, crowding, urban planning | settlement pattern | §5.2 |

## 7. What it feeds

All effects are refreshed once a year by the dynamic-modifier pattern, each from one site. State effects run from the
state pulse and country effects from the country pulse. Sizes are starting proposals.

| Effect | Modifier | Rule | Cap |
|---|---|---|---|
| **Workforce** | `state_working_adult_ratio_add` | 0.3 × (effective working share ÷ the reference − 1). The effective working share is defined below | ±0.08 |
| **Births and deaths** | `state_birth_rate_mult`, `state_mortality_mult` | §2.3 | births clamped above −0.9 in total |
| **The pension and health bill** | `country_institution_cost_institution_social_security_mult` and `_health_system_mult` (institution costs are bureaucracy) | 0.5 × (national 65+ share ÷ 0.07 − 1). Whether pensions also need a money cost is §14's probe | +1.0 |
| **Conscription** | `state_conscription_rate_mult` | men aged 20–39 ÷ the 1836 reference − 1 | ±0.25 |
| **Youth bulge** | radicals from movements, turmoil effects | the 20s above about 18% of the population (1836's share is about 17%), × the state's unemployment rate | small |
| **Sex balance** | births, working-adult ratio, movements, radicals | §3 | small |
| **Inequality** | lower-strata radicals; crime | §4.1 | small |
| **Wealth Concentration** | the state and country parts of #822's two modifiers | §4.2 | as now |
| **National urban pattern** | throughput and migration pull in the primate state; pull and turmoil elsewhere | §5.1 | small |
| **Settlement pattern** | crowding density, infrastructure from population, throughput, fertility, turmoil | §5.2 | small |

**The effective working share** has three parts:
- ages 15–64;
- plus the 10–14s times their participation: 0.3 under Child Labor Allowed, 0.1 under Restricted, 0 under Compulsory
  Primary School;
- plus the over-65s times theirs: 0.5 with no pension, 0.15 under Old Age Pension, moved by the retirement
  amendments (§8.2).

**The reference** is the same formula on the 1836 structure under the laws in force. So a law adds nothing flat;
vanilla's own law effects stay as they are. What a law sets is how much a young or old population costs.

**What the workforce effect does over a game** (with a pension and compulsory schooling):
- **The dividend window:** +10% in the sketch, and up to +25% at real East Asian peaks. That is +0.03 to +0.07, about
  one tech's worth: the Pill gives +0.05.
- **A Japan-like structure:** about 0, because its elderly replace the children of 1836 as dependents.
- **An extreme one, with 40% over 65:** about −6%.
- **Without a pension:** the old keep working, and the same Japan-like structure gains +13%. The price is the
  dependents' income and the politics.

So in this model ageing is **mainly a fiscal problem, not a labour problem**, which matches the real debate. Total
dependency in Japan today is about what it was in 1830s Europe; what changes is that the state now pays for the old,
where families paid for the children. The dividend is the opportunity and the pension bill is the cost.

**The owner's example holds.** A fast-growing population has many 10–14s. Under Compulsory Primary School none of them
work, so its workforce share falls the full amount. Under Child Labor Allowed a third of them count as workers, so the
drop is smaller.

**Left to the engine:** labour shortages raise wages, and wages pull migrants. Nothing needs adding for that.

**Optional, later:** life-cycle saving. Adults in their 40s and 50s save and the old spend down, which would move
investment-pool efficiency and the banking system's neutral rate. Ageing could also raise healthcare demand (the mod's
`popneed_healthcare`).

## 8. What the player controls

### 8.1 Family & Reproductive Policy, rebuilt

The model gives this group consequences that arrive later. Fewer births today mean fewer dependents now, a dividend in
fifteen years and a pension bill in fifty. More births are the reverse. Each law now acts on desired fertility and the
means (§2.3), not on a flat birth rate.

| Law | Today | Proposal |
|---|---|---|
| Traditional Family Structure | nothing | Unchanged baseline |
| Pro-Natalist Subsidies → **Pro-Natalist Policy** (`law_pro_natalist_subsidies`, key kept) | birth +10%, welfare +10%, dependent wage −10%, working-adult −0.05 | Desired fertility up by about 10–15%: real family policy adds about 0.1–0.3 children per woman. The means fall by 0.15 (access restricted). Its description becomes: "Through propaganda, incentives, or even coercion, this policy encourages higher birthrates." Players read their state's methods into it. **Drop the −0.05**, since the model now produces it. Fix the dependent wage to **+**, since family allowances raise dependents' income. The cost scales with the share of children |
| State-Sponsored Family Planning | birth −5%, working-adult +0.05, education access +0.05 | The means +0.1. Keep the +0.05, which stands for women's work, not age |
| **Population Control Measures** (name and key kept; its description is already open: "from strict limits … to eugenics programs") | birth −10%, +150 authority, radicals and loyalists from SoL change ×2 | Desired fertility down by about 30% and the means +0.2: China's fertility fell from 2.7 to under 2 in 1980–2000, partly from policy. +150 authority. Rural and traditional radicals; most IGs dislike it. **The payoff arrives through the model:** fewer dependents at once, a dividend in 15–20 years, crowding and food pressure relieved. **The cost arrives later too:** rapid ageing (China's "4-2-1" families) and, once prenatal sexing exists, a skewed sex ratio at birth and the *Missing Girls* and *Bare Branches* events (§9). Stop the enactment events (.19, .55, .79) granting it a birth boost |
| Communal Child-Rearing | birth −20%, working-adult +0.1 (yet its Youth Center PM gives +20%) | Pick one direction. Proposal: the law leaves fertility alone and keeps women's work at +0.1; the PM drops to +10% |

**Amendments for Population Control**, kept as open in wording as the law:
- **One-Child Limit:** stricter. Desired fertility down by about 45%, a larger sex skew, more unrest.
- **Rural Exemption:** half the cut in farm states, scaled by the agrarian share as in #822. China's "1.5-child" rule of
  1984.
- **Crash Campaign:** a further cut for five years, heavy unrest and a legitimacy blow. The wording leaves the methods
  to the player. India's Emergency (1975–77) is the model, and it cost the government the next election.

**Also:**
- AI weights for every law in the group. Today it has none.
- Natalism Initiative goes from +50% to about +15%. With the model it no longer needs to be large: a small push now shows
  up as a cohort later.
- Neither Population Control nor its amendments unlock Youth Centers.

### 8.2 Retirement

Two amendments on vanilla's Old Age Pension set the over-65s' participation (§7):
- **Raised Pension Age:** participation 0.15 → 0.3 and a smaller bill. Trade unions and the old object.
- **Early Retirement:** participation 0.05. It frees jobs for the young and lowers the youth-bulge penalty, as Western
  Europe did in the 1970s and 80s, but the bill rises.

Real anchors: about three-quarters of American men over 65 worked in 1880, and about a fifth do today. Without any
pension law, participation stays at 0.5: people work until they can't.

### 8.3 Other levers

| Lever | Through |
|---|---|
| Schools, literacy, education access | desired fertility and access to the means (§2.3) |
| Child-labour and schooling laws | the 10–14s' participation (§7). Vanilla's own effects (children's earnings in the dependent wage, the mortality cost) stay |
| Women's-rights laws | vanilla's birth and workforce modifiers, read through |
| Health laws, pharmaceuticals, vaccines | life expectancy, which feeds both ageing and desired fertility |
| Migration laws | how large the young-adult inflow is |
| Youth Centers | the birth PMs; Ectogenesis |
| Planned Capital, regional development, urban planning | the urban and settlement patterns (§5) |
| Taxes, land reform, inheritance | Wealth Concentration (§4.2) |
| **Biological Immortality** (era 12) | Rejuvenation stops people ageing out of the 40s and 50s, so the 60s and 70+ bands empty and the dependency ratio collapses. With almost no deaths, every birth adds to the population. Crowding returns, and Population Control becomes the late game's essential law, which gives the group an era-12 role |

### 8.4 Flat modifiers that move into the model

These stand in for an age, fertility or survival effect the model now produces. They come off when phase 2 lands, so
nothing is counted twice:
- the Pill's −10% birth (now a means tier);
- Pro-Natalist's −0.05 working-adult;
- the mod's own birth modifiers on its family-policy laws (now desired fertility and means).

Vanilla's modifiers stay as inputs, as do the mod's modifiers for women's and children's work.

## 9. Events and milestones

Each fires when the model crosses a threshold, at most once a generation per country. Candidates for the first wave:

| Event | Trigger | Choice |
|---|---|---|
| **The Demographic Dividend** | the working share passes the reference by 10% | spend it on schools, factories or the treasury |
| **The Baby Boom** | a war of two or more years with mass mobilisation ends | births +15% for ten years, decaying; the cohort echoes |
| **The Lost Generation** | war dead exceed 5% of men in their 20s and 30s | memorials, women into industry, or pensions for widows |
| **The Greying of the Nation** | 65+ passes 20% | raise the pension age, cut benefits, raise contributions, or open the borders |
| **The Youth Bulge** | the 20s above 20% and unemployment high | jobs, conscription or emigration |
| **Missing Girls** | the sex ratio at birth above 110 | ban prenatal sexing, pay families for daughters, or ignore it |
| **Bare Branches** | men aged 20–39 above 110 per 100 women | |
| **The Empty Villages** | a farm state that is old and shrinking | |
| **The Overspill** | a Metropolis-pattern state with crowding active | new towns, a green belt, or let it sprawl |
| **The Last Generation?** | Biological Immortality | |

## 10. The panel

**Country view: a "Demographics" tab in the vanilla Population panel** (`PopsOverviewPanel`). Its vanilla `.gui` file
is not in the repo; confirm its name on the machine with the game. Adding a tab means the mod overrides that file in
full, which adds one more vanilla file to the 3-way merge on every patch (`gui_modding_guide.md`). Custom tab names
already work (`InformationPanel.SelectTab`, proven by the Banking tab). The tab is available whenever the rule is on;
there is no journal entry to gate it. Style guide rules apply.

- **Overview** (always shown): median age, children per woman, life expectancy, dependency ratio, sex balance, Gini,
  Wealth Concentration and urban pattern. Each reads "Label: value" with a trend arrow.
- **Pyramid** (open): eight mirrored bars a side, men left and women right.
  - Behind them is a translucent outline of the structure twenty years ahead. It is drawn by running the band model
    forward from current rates: twenty steps of arithmetic on 16 numbers, country only, computed at the yearly pulse.
    It answers "is my workforce about to shrink?" at a glance.
  - Hovering children per woman shows its terms: wealth, education, child survival, urban life, means.
- **Wealth** (open):
  - the Gini, beside the engine's average income per stratum;
  - the national Wealth Concentration as a bar, with its target as the translucent segment and "top tenth owns ~X%";
  - the target's terms as bars;
  - the most and least concentrated states.
- **Where people live** (open): urban share, primacy, the effective number of cities and the three largest cities
  from the city ranking. Then the states by settlement pattern.
- **States** (open): a row per state with population, median age, children per woman, sex balance, Gini and Wealth
  Concentration. Vanilla GUI can't sort by script values; the order is a §14 check.
- **History** (open): yearly samples of median age, fertility, Gini and Wealth Concentration in the history store's
  column charts.
- **How Demographics Works** (collapsed).

**State view: a fourth subtab, "Demographics", on the state panel's Population tab.** The three 170 px subtabs become
four of about 130. It shows the state's pyramid, its figures, net migration, Gini, Wealth Concentration and settlement
pattern.

**Map modes:** median age, fertility, Gini, Wealth Concentration and settlement pattern, through the existing map-mode
hijack (`te_map_mode_script_values.txt`).

## 11. Balance, AI, performance, rule and compatibility

### 11.1 Balance

- **The retune is the large change** (§2.3). It moves every country's population path, so it needs the calibration
  harness (§12) before any in-game test. The harness is an offline Python copy of the engine's growth formula and the
  band model. It is driven by SoL, literacy and technology paths read from saves with `save_country_probe.py`, and
  tuned against the targets in §2.3.
- **In-game check:** an observer run to 2100, with population, fertility and ages read every 25 years and compared with
  the harness.
- **The workforce effect** stays inside ±0.08, about half of Women's Suffrage's +0.15.
- **Starting values** are each state's equilibrium, so 1836 is unchanged.

### 11.2 AI

- **Weights for Family & Reproductive Policy:**
  - Population Control when food security is poor, crowding high or a youth bulge present;
  - Pro-Natalist Policy when the 65+ share is high or the population is shrinking.
- **Events:** the AI picks pension-reform options by its treasury.
- **No dependence on the AI.** Nothing in the model needs the AI to act. If it does nothing, it fails the same way a
  player who does nothing would.

### 11.3 Performance

One yearly state effect:
- **one pop walk**, for the Gini sums, literacy, the soldier share and the agrarian share. It replaces inheritance's
  agrarian-share walk, so the mod walks pops once a year per state, not twice;
- **a few hundred arithmetic operations** on stored variables;
- **the GUI reads variables, never pop walks** (`scripting_best_practices.md`: GUI and loc re-evaluate every frame).

If the profiler shows a January spike, stagger states over the twelve monthly pulses by state id.

### 11.4 Game rule

**Demographics: Full / Display only / Off.**
- *Display only* runs the model and the panel without the modifiers. With it, the retuned defines would leave rich
  states growing, so it also needs the old curves. It is probably only useful for testing (§13 Q2).
- *Off* removes the panel and the model.
- Write the checks as `NOT = { has_game_rule = …_off }`, so a save from before the rule keeps the system (Grand
  Monuments' pattern).

### 11.5 Compatibility

- **The Demography mod** models ages too, so running both applies two sets of corrections. Document it and point
  players to the rule; no detection.
- **The Population panel** becomes a new full-file override. Any other mod that replaces it collides.
- **The state panel** already collides with Demography (`system_panels_feasibility.md` §7.4). A subtab adds nothing new.

## 12. Phases

| Phase | Contents | Gate |
|---|---|---|
| 0. Probes and harness | §14; the offline calibration harness (§11.1) with the retuned defines and the fertility terms | the harness meets §2.3's targets |
| 1. Census | the age and sex model, Gini, per-state Wealth Concentration (its targets and shocks), the national urban pattern, both panels, map modes, history, the rule. The model runs on today's defines and applies nothing yet | an observer run to 2100: the pyramids, fertility and Gini look right against the anchors |
| 2. Consequences | the retuned defines with the births and deaths factors; workforce, pension and health bill, conscription, youth bulge; the Family & Reproductive Policy rebuild and its amendments; the retirement amendments; §8.4's removals; Wealth Concentration's modifiers split by scope; AI weights | population paths within the harness's tolerance |
| 3. Place and colour | the settlement pattern (§5.2), the national urban pattern's effects and Planned Capital; sex-balance effects; the event wave; Ectogenesis and Immortality; Cultural Hegemony's fertility drift | |

Phase 1 alone is a playable feature: a census the player reads. Each later phase adds effects to numbers already seen
to be sane.

## 13. Still open

1. **Bands:** eight ten-year bands (recommended, for the pyramid) or four broad ones (cheaper, same economics)?
2. **The rule's default** is Full. Is *Display only* worth keeping, given it would need the old defines (§11.4)?
3. **Calibration target:** follow the UN's medium projection after 2020, with a peak in the 2080s, or let the game
   diverge freely once players change policy? The recommendation is history to 2020, then the projection only as a
   check on a do-nothing AI world.
4. **The renames:** Pro-Natalist Subsidies → Pro-Natalist Policy; Population Control Measures keeps its name. Are the
   three amendments right: One-Child Limit, Rural Exemption, Crash Campaign?
5. **National Wealth Concentration:** weight the states by GDP (recommended: where the wealth is) or by population?
6. **The settlement pattern's labels and size:** is "Metropolis / Leading City / Several Cities / Market Towns" right,
   and should its effects stay small?

## 14. Engine checks before building

1. **One walk, several sums.** Can `every_scope_pop = { … }` in an effect accumulate several state variables in one
   pass, through a named script value in pop scope (`change_variable = { add = te_x }` on `PREV`/`state`)? If not, use
   one script-value walk per sum.
2. **`wealth_share`** as a value in state scope (the quoted form). If it works, it replaces the wealth proxy.
3. **War dead:**
   - `num_country_dead(root)` as a value;
   - whether war counters survive the war's end;
   - whether battle dead come out of the soldiers' home-state pops.
4. **`modifier:state_birth_rate_mult`** on a state includes laws and techs passed down from the country.
5. **Who pays pensions in money** under Old Age Pension: the dependent wage, welfare payments or the state. This decides
   whether §7 needs a money cost.
6. **Births floor:** what the engine does when the total birth multiplier goes below −1. This sets the clamp in §2.3.
7. **GUI:**
   - the Population panel's vanilla file, and whether a third tab fits its strip;
   - whether a list of the country's states can be ordered by a script value;
   - mirrored `progressbar` pyramids.
8. **Cost:** the profiler on a yearly pulse with the walk in every state, in a 1950s and a 2050s save.
