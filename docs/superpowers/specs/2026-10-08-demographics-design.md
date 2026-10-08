# Demographics: age, sex, wealth and where people live — design (scoping draft)

> **Status: scoping draft, 2026-10-08. Nothing here is decided.** It follows the owner's request to widen the
> Wealth Concentration score from #822 (`2026-10-08-inheritance-laws-design.md` §3) into a demographics system with
> its own panel. It answers what to track, what moves each number, what each number moves and what the player
> controls. §13 lists the questions the owner needs to settle before anything is built; §14 lists the engine
> checks that come first.

## Context

**The request.** A new tab with the country's demographics: wealth concentration, how concentrated the population is
(one metropolis against ten cities, New York against Texas), the age breakdown and perhaps sex. Tracked per state and
updated yearly, since all of it moves slowly. It should be influenced by other systems (war dead are mostly men) and
influence them in turn (under the stricter child-labour laws children don't work, so a fast-growing population has a
lower workforce share). The player should be able to steer it, and the weak Population Control law should become a
real lever. The pillars are realism, fun and balance.

**What the engine gives us.** Pops have no age or sex. The only demographic axes are:
- **workforce and dependents**, set by a working-adult ratio (vanilla's default is a define outside the repo;
  `pop_types` sets aristocrats 0.2 and slaves 0.5). It is moved by `state_working_adult_ratio_add`. Vanilla's
  women's-rights laws add 0.05 to 0.3, and Old Age Pension subtracts 0.01;
- **birth rate and mortality**, from the standard-of-living curve in the defines plus `state_birth_rate_mult` and the
  `*_mortality_mult` family. The mod's defines (`common/defines/extra_defines.txt:79-88`) run births from 5.7% a year
  at SoL 0 down to 0.96% at SoL 35, and deaths down to 1.2%. A state at SoL 35 or above shrinks by 0.24% a year from
  the day it gets there, whatever its history;
- **readable values**: a pop's `total_size`, `wealth`, `standard_of_living` and `literacy_rate`; a state's
  `state_population`, `total_urbanization`, `average_sol`, `state_unemployment_rate`, `gdp` and `modifier:<key>`
  totals; a war's `num_country_dead(<country>)`. Script values can walk pops and states
  (`te_inh_agrarian_share_value`, `country_max_state_population`). A pop's income can't be read in script, and
  migration and births can't either; the GUI alone has `State.GetWeeklyPopNetMigration`.

So age and sex must be **modelled**. The model takes engine readouts as inputs and pushes its results back through
modifiers.

**What the mod already has.**
- **Wealth Concentration** (`te_inh_concentration`, country, 0–100). It drifts 3% a year to a target set by the
  inheritance law and its amendments, and drives `inh_great_fortunes` / `inh_dispersed_wealth`. The player sees it
  only in loc: the law group's description, a concept and the two modifiers. Nothing under `gui/` reads it.
- **Family & Reproductive Policy** (`lawgroup_family_reproductive_policy`, `common/laws/extra_laws.txt:2553-2621`),
  the group the owner called "population controls". It has five laws, only flat birth-rate and workforce modifiers,
  no amendments and no AI weights. Population Control Measures' only benefit, +150 authority, is also what State
  Eugenics Program (another group) gives, and that law adds workforce and births on top (§8.1).
- **Population modifiers spread across many laws and techs.** The Pill, second-wave feminism, Protected Class,
  vaccines, antibiotics and Biological Immortality set flat `state_birth_rate_mult`, `state_mortality_mult` and
  `state_working_adult_ratio_add`. The Natalism Initiative decree gives +50% birth rate for 250 authority, which
  outweighs every law in the group.
- **Where people live.** Migration Crowding (a yearly per-state density penalty); the world city ranking
  (`city_size`, `var:state_city_size_rank`, global monthly); Internal Resettlement (`move_partial_pop` programmes,
  per-region areas in `te_region_area_generated.txt`).
- **Deaths the mod causes.** Nuclear strikes store `nuclear_strike_killed_population` on the state. Violent Hostility
  kills 2–10% of a culture a year. The anti-war movement reads `num_country_casualties`.
- **Panels.** The Society panel's five tab slots are full (four vanilla tabs plus Cultural Hegemony), so a sixth needs
  `te_tab_buttons_six`, as Market, Budget and Diplomacy already use. The state panel's Population tab has three
  170 px subtabs: Statistics, Pops and Characters. The history store draws column charts of stored samples, and a
  map mode can paint any per-state script value (`te_map_mode_script_values.txt`).

**Prior art: the Demography Workshop mod** (`3759720467`, surveyed in `docs/systems/system_panels_feasibility.md` §7).
It gives every state 17 five-year age bands and updates them monthly. Ages feed births, mortality, workforce,
migration, war losses, throughput and welfare costs. It replaces `states_panel.gui` and `budget_panel.gui` and adds
pension, child-benefit and retirement-age controls. Its author lists balance as unfinished. Two age models in one
game would apply their modifiers twice (§11.5).

## Design rules (the pillars, made concrete)

1. **The engine owns how many people there are; the model owns who they are.** The model never fights the engine's
   headcount. It reads the engine's birth and death rates, sorts the people into ages and sexes, and feeds back only
   the corrections that age structure implies (§2.3). Total population can never drift away from what the panel shows.
2. **Track only what changes a decision or explains one.** Every number must either move something (§7) or show the
   player why something moves.
3. **Laws act on inputs and the model produces the consequences.** A law changes fertility, mortality or who works.
   The workforce or pension effect arrives through the model, with the real lag: fewer births today give fewer workers
   in fifteen years. Flat workforce modifiers that stand in for an age effect come off (§8.1). Ones that stand for
   women's or children's work stay.
4. **Slow clocks with visible momentum.** Each number moves over a generation, and the panel shows where it is
   heading. The fun is in seeing a window open twenty years ahead (§9).
5. **Every country starts in equilibrium**, and each effect is a deviation from a stated reference, capped. Nothing
   moves on day one. A save from before the system starts each state at its equilibrium (the #822 pattern).
6. **Every number has a real-world meaning and an anchor value** (UN World Population Prospects for ages and
   fertility; the World Inequality Database, Lindert and Williamson for wealth). The panel uses real units:
   children per woman, years, a Gini coefficient, "the top tenth owns about X%".

## 1. What to track

| Stat | Scope | Source | Shown as |
|---|---|---|---|
| **Age structure**: eight ten-year bands, 0–9 … 60–69 and 70+ | state; the country's is the population-weighted sum | modelled (§2) | population pyramid |
| **Sex**: male share of each band | state | modelled (§3) | the pyramid's two halves |
| Derived figures: median age, dependency ratio, working-age share | state, country | computed from the bands | table, with an arrow for the trend |
| **Fertility**: children per woman | state | the engine's birth rate converted (§2.3) | table |
| **Life expectancy** at birth | state | the engine's mortality converted (§2.3) | table |
| **Net migration** last year | state | the residual left after natural change (§2.4) | table |
| **Income inequality**: a Gini coefficient | state; country | computed from pops each year (§4.1) | table, map mode |
| **Wealth Concentration**: the #822 score, with a widened target | country | modelled stock (§4.2) | bar with its target segment; "top tenth owns ~X%" |
| **Urban pattern**: the largest city's share and the effective number of cities | country | computed from states (§5.1) | label and figures |
| Settlement pattern (one metropolis or several cities) | state | modelled, optional (§5.2) | label |

**Left out:** ages on individual pops, single-year ages, age by culture or religion, and education by age. Each costs
far more than it returns at Victoria's level of detail.

**Why ten-year bands.** Every effect in §7 reads only a few band totals: the fertile ages, the workforce, the elderly
and the young adults. Four bands (0–14, 15–29, 30–64, 65+) would serve the economics. But a pyramid of four blocks
doesn't read as a pyramid, and the dents that wars and baby booms leave can't be seen working up through it. Eight
bands with a male share each make 16 state variables, against Demography's 17 bands updated monthly. The cost is
arithmetic, not pop walks (§11.3). Band models blur echoes: in a test run, a ten-year boom spreads over about thirty
years as it climbs (§2.2). That is a known limit of band models, Demography's included. A dent from a big war stays
visible.

## 2. The age model

### 2.1 The yearly step

Per state, as shares that sum to 1:

- **Births** = children per woman × women aged 15–44 ÷ 30, into the 0–9 band. The male share of births follows the sex
  ratio at birth (§3).
- **Ageing**: a tenth of each band moves up a band each year; 70+ is the last.
- **Deaths**: each band loses its own rate, taken from a model life table at the state's life expectancy (§2.3).
- **Migration and other losses**: the residual from §2.4, given a migrant's age and sex profile.
- Then normalise to shares, and store the population for next year's residual.

### 2.2 Does it behave?

A throwaway Python sketch of the step, run with four bands and with eight, gives these equilibrium structures for
plausible parameters:

| Case | Children per woman | 0–14 | 15–64 | 65+ | Growth a year | Real anchor |
|---|---|---|---|---|---|---|
| 1836 agrarian | 5.2 | 35% | 59% | 5–7% | +0.8 to +1.7% | Western Europe 1830s–1850s: 0–14 about 35%, 65+ 4–6% |
| High fertility, falling mortality (1950s) | 6.0 | 38% | 54% | 8% | +2.6% | developing countries 1950–70: 0–14 40–45% |
| Replacement fertility | 2.0–2.2 | 20% | 60–62% | 19–20% | about 0 | |
| Aged | 1.3 | 12% | 55–56% | 33% | −0.9 to −1.2% | Japan today: 0–14 11%, 65+ 29%, children per woman 1.2 |

A transient matters more than any equilibrium. Drop fertility from 6 to 2 and the working-age share climbs from 54%
to 64% over twenty years and holds there for about thirty. That is the **demographic dividend**: real East Asian
peaks reached 70–74%; the band model underestimates them because it blurs. Cut fertility to 1.3 after that and the
share falls back to 57% by year 100, while 65+ reaches 30%. The dividend and the ageing that follows it are the
system's backbone for gameplay. Both appear without being scripted as events.

### 2.3 Where births and deaths come from

The model doesn't invent its own fertility; it reads the engine's:

- **Birth intensity.** The engine's base rate at the state's SoL comes from the defines' curve, times
  `1 + modifier:state_birth_rate_mult`, minus this system's own correction (below). A Python generator writes the
  curve as a script value from `extra_defines.txt`, so it can't drift from the defines. **Children per woman** = that
  rate × 30 ÷ the share of women aged 15–44 in the equilibrium structure for that SoL. At the mod's curve this gives
  about 7.8 at SoL 0, 6–7 at a typical 1836 SoL and about 1.5 at SoL 35: the real range.
- **Mortality.** The engine's mortality at that SoL, times its modifiers, maps to a life expectancy and a model life
  table for the bands. The same generator emits that table, built from a standard model life-table family (in the
  Coale–Demeny style).
- **Every law, tech, decree and event that already moves births or deaths flows through unchanged.** Forced
  Heirship's rural birth cut, the Pill and Natalism Initiative are all inputs with no extra script, so nothing is
  counted twice.

**The corrections close the loop.** The engine computes births as a rate × population, as if every state had the same
age structure. The model knows it doesn't, and applies two state modifiers from the yearly state pulse:

- `state_birth_rate_mult` += women 15–44 now ÷ women 15–44 in the SoL's equilibrium − 1 (capped ±0.35);
- `state_mortality_mult` += the age-weighted death index now ÷ the equilibrium's − 1 (capped ±0.35).

In equilibrium both are zero, so long-run population totals stay where the mod's balance has them. Away from
equilibrium they produce **momentum**:
- a young population that has just got rich keeps growing for a generation, since it has many parents and few
  elderly;
- an old one shrinks faster;
- a baby boom echoes a generation later.

That replaces "at SoL 35 every state shrinks at once" with history-dependent behaviour.

**Option (larger, for a later phase):** treat the defines' curve as age-standardised rates and drop the equilibrium
reference, so ageing alone produces the decline in rich states. It is more realistic, but it re-tunes world population
for the whole mod and needs its own balance pass against UN totals for 1900, 1950, 2000 and 2050. §13 Q3.

### 2.4 Migration, war dead and other losses

The engine moves and kills people; the model sees only the result. Each year:

1. **War dead.** For every war the owner is in, read `num_country_dead(owner)`, take the change since the last pulse
   and share it out among the owner's states by their share of the country's soldiers (from the yearly pop walk). The
   dead are taken from the 20s and 30s, about 95% of them men. The mod defines a Women in Combat Roles modifier
   (`women_combat_roles_modifier`) that nothing grants yet; whatever grants it should lower that share. The war's
   counter disappears when the war ends, so snapshot it monthly or at war end (§14).
2. **Known kills.** Nuclear strikes already record the dead per state, and are taken from all ages and both sexes.
   Resettlement records its arrivals and departures, which have the profile of its programme. Violent Hostility's kills
   are taken from all ages.
3. **The residual**: the population change, less natural change, less (1) and (2). This is mostly migration.
   - A gain arrives with a migrant's profile: mostly people in their 20s and 30s. Before about 1900 two-thirds are men,
     falling to near half by the mid-20th century.
   - A loss leaves with the same profile.
   - A residual under 0.3% of the population is treated as model error and spread over all bands, so the model's own
     rounding doesn't make states look like migration hubs.

This makes frontier and immigrant states young and male, and emigrant states old and female, with no extra script.
That is what happened in the American West, Argentina, Australia, Ireland and southern Italy.

### 2.5 Starting values and new states

- **1836.** Each state starts at the equilibrium for its SoL and modifiers. A few countries get historical overrides.
  France starts with fertility well below its neighbours': its transition began around 1800, and #822's Forced
  Heirship already pushes it there. The US starts young and male in the frontier states.
- **A state with no variables** (a new state, a split state region, an old save) starts at its equilibrium. A split
  state could copy its sibling's structure instead, since it is the same people.
- **Revolutions.** State variables stay on the states. The country's numbers are recomputed from them, so nothing is
  lost (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").

## 3. Sex

Track the male share of each band. Total population is unchanged; this is only which half of the pyramid people sit
in.

**What moves it:**

| Source | Effect | Anchor |
|---|---|---|
| Sex ratio at birth | 105 boys per 100 girls normally | the biological constant |
| Sex-selective births | up to about 115–120 under birth quotas once prenatal sexing exists (§8.1) | China's sex ratio at birth reached about 118 in the 2000s |
| War dead | about 95% men, from the 20s and 30s | the Soviet Union in 1959: about 0.82 men per woman |
| Migration | before about 1900 two-thirds of migrants are men, later half | California in 1850 was over 90% male |
| Longevity | women outlive men; the gap in the 70+ band widens with life expectancy, from about 2 years to 5–7 | |

**What it moves** (adults 20–59, capped, small on purpose; the evidence on effects is weaker than on causes):

- **Fewer men than women** (after a great war):
  - fewer marriages, so births × the square root of (men ÷ women);
  - more women at work (+ working-adult ratio);
  - support for women's-rights movements. Britain's "surplus women" after 1918 are the example.
- **More men than women** (frontier, migrant-worker or sex-selected populations):
  - births fall on their own, since there are fewer women;
  - radicals and crime rise a little (Hudson and den Boer's *Bare Branches*), which feeds the policing laws.

## 4. Wealth

Two numbers, as economists keep them: a **flow** (how unequal this year's incomes are) and a **stock** (who owns the
capital). The stock is the #822 score with a wider target.

### 4.1 Income inequality (state, computed yearly)

- **The measure.** A Gini coefficient from the state's pops. Pop income can't be read in script, but `wealth` can. A
  generator turns the wealth level into spending per head using the pop-needs curve from `pop_needs_curves`, as a
  proxy for income.
  - **Grouped form:** each stratum's share of people and of income, ordered lower < middle < upper. This needs one pop
    walk if a single walk can fill several sums (§14), or one per stratum.
  - **Or the engine's own figure:** if `wealth_share = { pop_type = X … }` reads as a value, the share of wealth held
    by each pop type comes straight from the engine.
  - The grouped Gini misses inequality within each group, so scale it to the anchors: Britain about 0.5–0.55 in the
    1830s and US about 0.5 in 1870 (Lindert and Williamson); Nordic countries 0.25–0.3 today; the US 0.39 after taxes;
    South Africa about 0.63.
- **The country** figure is the population-weighted Gini over all states' groups, not an average of state Ginis.
- **Effects, light on purpose.** Vanilla already turns wealth into clout, so inequality mainly feeds the stock (§4.2)
  and the panel. Two small effects:
  - relative deprivation: lower-strata radicals rise with the Gini above about 0.45;
  - an input to crime for the policing laws.

### 4.2 Wealth Concentration (country, the widened #822 score)

**Keep `te_inh_concentration`, its 0–100 scale, its 3% yearly drift and its two modifiers.** Widen the target from
"inheritance law" to a sum of terms around 50, of which inheritance is one. The panel shows each term as a bar (style
guide rule 5).

| Term | Proposal | Why |
|---|---|---|
| Inheritance law and amendments | today's targets re-centred on 50: Primogeniture +30, Testation +10, Customary 0, Forced Heirship −25, State Heir and Possession −50; amendments as now | #822 unchanged in effect |
| Income inequality | +0.5 × (country Gini − 0.40) × 100, capped ±15 | fortunes grow from unequal flows: the rich save more |
| Land tenure (vanilla land reform laws) | Serfdom +15, Tenant Farmers +5, Commercialized Agriculture 0, Homesteading −10, Collectivized Agriculture −20 | land was most of the wealth in 1836 |
| Taxes on wealth | Graduated Taxation −5; the tax code's dividend and estate settings when the rule is on | |
| Return on capital against growth (later phase) | from the banking system's policy rate against GDP growth | Piketty's r > g; only where the banking system runs |

**Shocks** jump the score instead of moving its target. They follow Scheidel's four levellers (*The Great Leveler*,
2017):
- **War.** Each year of total mobilisation takes −1, up to −10 a war; capitulation −5. The world wars destroyed much
  of Europe's capital.
- **Revolution.** A left revolution that wins: −20.
- **State failure and money.** A hyperinflation or banking crisis from the monetary system: −5 to −10, since bond
  fortunes vanish.
- **Plague, land reform and nationalisation events:** −5 to −15.
- **Upward:** privatisation waves and financial booms, +5.

**Readout.** Map the score to "the top tenth owns about X%": 0 → 40%, 50 → 65%, 100 → 90%. Europe's top tenth held
85–90% around 1910 and 50–60% around 1970; the US is about 70% today.

**State level.** The stock stays national. The levers are national, and owners hold capital across states, often from
the capital. Each state shows its own income Gini.

## 5. Where people live

### 5.1 The national urban pattern (computed)

- **Urban population per state** = population × the vanilla urbanisation rate (`state_urbanization_rate`).
- **Primacy** = the largest city's share of the country's urban population.
- **Effective number of cities** = 1 ÷ the sum of each state's squared share. It answers "one metropolis or ten
  cities" in a single number.
- **Labels:** Primate (≥ 40%), Dominant (25–40%), Balanced (10–25%), Dispersed (< 10%).
- **Anchors** (the largest metro's share of the whole population; its share of the urban population runs a little
  higher): Seoul's metro holds about half of Korea and Buenos Aires about a third of Argentina; Greater London about
  13% of the UK and the Paris region about 18% of France; Berlin about 4% of Germany.

**Effects** (a choice, not a penalty):

| Pattern | The primate state | The rest |
|---|---|---|
| Primate or dominant | agglomeration: services and Urban Center throughput up, migration pull up; crowding comes from Migration Crowding, which already exists | migration pull down, some regional resentment (turmoil effects) |
| Balanced or dispersed | none | none; it is the baseline |

**Levers:**
- **A Planned Capital decision** (Washington, Canberra, Brasília, Abuja, Astana): money and authority, the capital
  moves, and the new capital state gets a development modifier.
- **Regional development**: Internal Resettlement's Development Program and Planned Towns.
- Railways.

### 5.2 One metropolis or several cities, inside a state (optional)

A Victoria state has one city hub. The engine has no cities below the state, so this could only be modelled: a 0–100
"metropolitan share" per state.
- **Drivers:** being the capital, a port hub, the state's area (the generated region table), and how many industries it
  has.
- **Effects:** agglomeration against congestion, and lower fertility in a metropolis.

It is the most invented number in the list and the hardest for a player to check. The recommendation is to leave it
out until §5.1 has been played (§13 Q6).

## 6. What feeds in

| Source | Into | How |
|---|---|---|
| SoL; every birth and mortality modifier (laws, techs, decrees, events, starvation, devastation, pollution, global warming's heat and disease) | fertility, life expectancy | read from the engine (§2.3), so no new hooks |
| Wars | the 20s and 30s, men | `num_country_dead` shared out by soldiers (§2.4) |
| Migration, mass migration, the migration laws | the 20s and 30s, more men early on | residual (§2.4) |
| Internal Resettlement | its programme's profile (Rustication takes the young, Managed Retreat the old) | its own counters |
| Nuclear strikes, Violent Hostility | all ages | recorded or residual |
| Child-labour, pension and retirement laws | who among the young and old works | participation weights (§7) |
| Ectogenesis (the Youth Center PM) | births depend less on how many women of childbearing age there are | weakens the women-15–44 term of the birth formula in states with the PM |
| Biological Immortality (era 12) | ageing stops | §8.3 |
| Cultural Hegemony (later phase) | fertility drifts a little toward the hegemon's | the "soap-opera effect": Brazil's fertility fell where TV novelas reached (La Ferrara et al., 2012) |
| Inheritance, land tenure, taxes, war, revolution, banking crises | Wealth Concentration | §4.2 |

## 7. What it feeds

All effects are refreshed once a year from the yearly state pulse (country-scoped ones from the country pulse), each
from one site, by the dynamic-modifier pattern. Sizes are starting proposals.

| Effect | Modifier | Rule | Cap |
|---|---|---|---|
| **Workforce** | `state_working_adult_ratio_add` | 0.3 × (effective working share ÷ the reference − 1). The **effective working share** is ages 15–64, plus the 10–14s times their participation (0.3 under Child Labor Allowed, 0.1 under Restricted, 0 under Compulsory Primary School), plus the over-65s times theirs (0.5 with no pension, 0.15 under Old Age Pension, moved by the retirement amendments, §8.2). The **reference** is the same formula on the 1836 structure under the laws in force, so a law adds nothing flat (vanilla's own law effects stay as they are); it sets how much a young or old population costs | ±0.08 |
| **Momentum** | `state_birth_rate_mult`, `state_mortality_mult` | §2.3 | ±0.35 each |
| **The pension and health bill** | `country_institution_cost_institution_social_security_mult` and `_health_system_mult` (institution costs are bureaucracy) | 0.5 × (national 65+ share ÷ 0.07 − 1). Whether pensions also need a money cost is §14's probe | +1.0 |
| **Conscription** | `state_conscription_rate_mult` | men aged 20–39 ÷ the 1836 reference − 1 | ±0.25 |
| **Youth bulge** | radicals from movements, turmoil effects | 20–29 above about 18% of the population (1836's share is about 17%), × the state's unemployment rate | small |
| **Sex ratio** | births, working-adult ratio, movements, radicals | §3 | small |
| **Inequality** | lower-strata radicals; crime | §4.1 | small |
| **Wealth Concentration** | `inh_great_fortunes`, `inh_dispersed_wealth` | as now | as now |
| **Urban pattern** | throughput and migration pull in the primate state; pull and turmoil elsewhere | §5.1 | small |

**What the workforce effect does over a game** (with a pension and compulsory schooling):
- **The dividend window:** +10% in the sketch, and up to +25% at real East Asian peaks. That is +0.03 to +0.07, about
  one tech's worth: the Pill gives +0.05.
- **A Japan-like structure:** about 0, because its elderly replace the children of 1836 as dependents.
- **An extreme one, with 40% over 65:** about −6%.
- **Without a pension:** the old keep working, and the same Japan-like structure gains +13%. The price is the
  dependents' income and the politics.

So in this model ageing is **mainly a fiscal problem, not a labour problem**, which matches the real debate: total
dependency in Japan today is about what it was in 1830s Europe. What changes is that the state now pays for the old,
where families paid for the children. The dividend is the opportunity and the pension bill is the cost.

**The owner's example holds.** A fast-growing population has many 10–14s. Under Compulsory Primary School none of
them work, so its workforce share falls the full amount. Under Child Labor Allowed, a third of them count as workers,
so the drop is smaller.

**Left to the engine:** labour shortages raise wages, and wages pull migrants. Nothing needs adding for that.

**Optional, later:** life-cycle saving. Adults in their 40s and 50s save, and the old spend down, which would move
investment-pool efficiency and the banking system's neutral rate. Also more demand for healthcare (the mod's
`popneed_healthcare`).

## 8. What the player controls

### 8.1 Family & Reproductive Policy, rebuilt

The model gives this group what it lacked: consequences that arrive later. Fewer births today mean fewer dependents
now, a dividend in fifteen years and a pension bill in fifty. More births are the reverse.

| Law | Today | Proposal |
|---|---|---|
| Traditional Family Structure | nothing | Unchanged baseline |
| Pro-Natalist Subsidies | birth +10%, welfare +10%, dependent wage −10%, working-adult −0.05 | Birth +10–15%: real family policy adds about 0.1–0.3 children per woman. **Drop the −0.05**, since the model now produces it. Fix the dependent wage to **+**, because family allowances raise dependents' income. The cost scales with the share of children |
| State-Sponsored Family Planning | birth −5%, working-adult +0.05, education access +0.05 | Birth −10%. Keep the +0.05: it stands for women's work, not age |
| **Population Control Measures** → **Birth Quotas** (`law_population_control_measures`, key kept) | birth −10%, +150 authority, radicals and loyalists from SoL change ×2 | Birth **−30%**: China's fertility fell from 2.7 to under 2 in 1980–2000, partly from policy. +150 authority. Rural and traditional radicals; disliked by most IGs. **The payoff arrives through the model:** fewer dependents at once, a dividend in 15–20 years, crowding and food pressure relieved. **The cost arrives later too:** rapid ageing (China's "4-2-1" families) and, once prenatal sexing exists, a skewed sex ratio at birth and the *Missing Girls* and *Bare Branches* events (§9). Stop the enactment events (.19, .55, .79) from granting it a birth boost |
| Communal Child-Rearing | birth −20%, working-adult +0.1 (yet its Youth Center PM gives +20%) | Pick one direction. Proposal: the law is birth 0, women's work +0.1; the PM keeps +10% |

**Amendments for Birth Quotas:**
- **One-Child Limit:** stricter. Birth −45%, a larger sex skew, more unrest.
- **Rural Exemption:** half the cut in farm states, scaled by the agrarian share as in #822. China's "1.5-child"
  rule of 1984.
- **Sterilisation Campaigns:** an extra −20% for five years, heavy unrest and a legitimacy blow. India's Emergency,
  1975–77, cost the government the next election.

**Coercive pronatalism** (optional; the owner's call on tone): an abortion and contraception ban as an amendment on
Pro-Natalist Subsidies. Romania's Decree 770 (1966) nearly doubled births within a year; they fell most of the way
back within a decade, and maternal deaths rose. Births would spike then decay, female mortality rise, and women and
liberals radicalise. The large cohort it creates would be visible on the pyramid for sixty years. The mod already has
a State Eugenics law, so the tone has precedent, but this is a judgement for the owner (§13 Q7).

**Also:**
- AI weights for every law in the group. Today it has none.
- Natalism Initiative goes from +50% to about +15%. With the model it no longer needs to be large: a small push now
  shows up as a cohort later.
- Population Control currently doesn't unlock Youth Centers. Birth Quotas shouldn't either.

### 8.2 Retirement

Two amendments on vanilla's Old Age Pension, which set the over-65s' participation (§7):
- **Raised Pension Age:** participation 0.15 → 0.3, a smaller bill, trade unions and the old object.
- **Early Retirement:** participation 0.05. It frees jobs for the young and lowers the youth-bulge penalty, as in
  Western Europe in the 1970s and 80s, but the bill rises.

Real anchors: about three-quarters of American men over 65 worked in 1880, about a fifth today. Without any pension
law, participation stays at 0.5: people work until they can't.

### 8.3 Other levers

| Lever | Through |
|---|---|
| Child-labour and schooling laws | the 10–14s' participation (§7): they add nothing flat, since vanilla's own effects (children's earnings in the dependent wage, the mortality cost) stay. They set how much a young population costs in workers |
| Women's-rights laws | vanilla's birth and workforce modifiers, read through (§2.3) |
| Health laws, pharmaceuticals, vaccines | life expectancy, which feeds ageing |
| Migration laws | how large the young adult inflow is |
| Youth Centers | the birth PMs; Ectogenesis |
| Planned Capital, regional development | the urban pattern (§5.1) |
| Taxes, land reform, inheritance | Wealth Concentration (§4.2) |
| **Biological Immortality** (era 12) | Rejuvenation stops ageing out of the 40s–50s, the 60s and 70+ bands empty, and the dependency ratio collapses. With almost no deaths, every birth adds to the population, so crowding returns, and Birth Quotas become the late game's essential law. This gives the group an era-12 role |

## 9. Events and milestones

Each fires from a threshold the model crosses, at most once a generation per country. Candidates for the first wave:

| Event | Trigger | Choice |
|---|---|---|
| **The Demographic Dividend** | the working share passes the reference by 10% | spend it on schools, factories or the treasury |
| **The Baby Boom** | a war of two or more years with mass mobilisation ends | births +15% for ten years, decaying; the cohort echoes |
| **The Lost Generation** | war dead exceed 5% of men in their 20s and 30s | memorials, women into industry, or pensions for widows |
| **The Greying of the Nation** | 65+ passes 20% | raise the pension age, cut benefits, raise contributions, or open the borders |
| **The Youth Bulge** | 20–29 above 20% and unemployment high | jobs, conscription or emigration |
| **Missing Girls** | sex ratio at birth above 110 | ban prenatal sexing, pay families for daughters, or ignore it |
| **Bare Branches** | men aged 20–39 above 110 per 100 women | |
| **The Empty Villages** | a farm state that is old and shrinking | |
| **The Last Generation?** | Biological Immortality | |

## 10. The panel

**The reading of "the population page" is open (§13 Q8).** The proposal is a country view as a sixth tab in the
Society panel, plus a state view as a fourth subtab on the state panel's Population tab (three 170 px subtabs become
four of about 130). The Timeline Extended window is the fallback.

**The country tab** (Society panel, `te_tab_buttons_six`). Available whenever the rule is on; there is no journal entry
to gate it. Style guide rules apply.

- **Overview** (always shown): median age, children per woman, life expectancy, dependency ratio, sex ratio, Gini and
  urban pattern, each as "Label: value" with an arrow for the trend.
- **Pyramid** (open): eight mirrored bars a side, men left and women right. Behind them, a translucent outline of the
  structure twenty years ahead, drawn by running the band model forward from current rates. Twenty steps of arithmetic
  on 16 numbers, for the country only, computed at the yearly pulse. This answers "is my workforce about to shrink?"
  at a glance.
- **Wealth** (open):
  - the Gini;
  - Wealth Concentration as a bar, with its target as the translucent segment and "top tenth owns ~X%";
  - the target's terms as bars (§4.2).
- **Where people live** (open): urban share, primacy, effective number of cities and the three largest cities, from
  the city ranking.
- **States** (open): a row per state with population, median age, children per woman, sex ratio and Gini. Vanilla GUI
  can't sort by script values; the order is a §14 check.
- **History** (open): yearly samples of median age, fertility, Gini and Wealth Concentration in the history store's
  column charts.
- **How Demographics Works** (collapsed).

**The state subtab:** the state's pyramid, its figures, and its sex ratio, net migration and Gini.

**Map mode:** median age, fertility or Gini through the existing map-mode hijack (`te_map_mode_script_values.txt`).

## 11. Balance, AI, performance, rule and compatibility

### 11.1 Balance

Rule 5 (equilibrium starts, deviations from a reference, caps) is the main guard.

- **The decision that matters most is §2.3's: corrections against each SoL's equilibrium.** That keeps today's
  long-run population totals, so the system adds dynamics without re-tuning the world. Check it with an observer run to
  2100, comparing world and great-power populations with and without the system. Use `save_country_probe.py` on saves
  every 25 years.
- The workforce effect stays inside ±0.08, about half of Women's Suffrage's +0.15.

### 11.2 AI

- Weights for Family & Reproductive Policy:
  - Birth Quotas when food security is poor, crowding high or a youth bulge present;
  - Pro-Natalist when the 65+ share is high.
- The AI picks pension-reform event options by its treasury.
- Nothing in the model depends on the AI acting. Its failure modes are the same as the player's doing nothing.

### 11.3 Performance

One yearly state effect:
- **one pop walk** for the Gini sums and the soldier share. It can replace inheritance's agrarian-share walk, so the
  mod walks pops once a year per state, not twice;
- plus a few hundred arithmetic operations on stored variables;
- the GUI reads variables, never pop walks (`scripting_best_practices.md`: GUI and loc re-evaluate every frame).

If the profiler shows a January spike, stagger states over the twelve monthly pulses by state id.

### 11.4 Game rule

**Demographics: Full / Display only / Off.**
- *Display only* runs the model and the panel but applies no modifiers. It is the safe setting beside other demography
  mods.
- Write the checks as `NOT = { has_game_rule = …_off }`, so a save from before the rule keeps the system (Grand
  Monuments' pattern).

### 11.5 Compatibility

- **The Demography mod** models ages too. Running both applies two sets of corrections.
  - If Demography sets something detectable (a global variable or scripted trigger), fall back to *Display only*
    automatically.
  - If not, document it and point players to the rule.
- **`states_panel.gui`** already collides between the two mods (`system_panels_feasibility.md` §7.4). A subtab adds
  nothing new to that collision.
- **CMF** redefines `society_panel`, which already affects the Hegemony tab.

## 12. Phases

| Phase | Contents | Gate |
|---|---|---|
| 0. Probes | §14 | each answered in a test launch |
| 1. Census (display only) | the age and sex model, Gini, urban pattern, both panels, map mode, history, rule | observer run to 2100: the pyramids look right against UN anchors, nothing applied |
| 2. Consequences | §7's workforce, momentum, pension and health bill, conscription, youth bulge; Birth Quotas and its amendments; retirement amendments; the Family & Reproductive Policy fixes; flat age-proxy modifiers removed; AI weights | population totals stay within a few percent of the run without the system |
| 3. Wealth and place | Wealth Concentration's wider target and shocks, the urban-pattern effects and Planned Capital; sex-ratio effects; the event wave; Ectogenesis and Immortality; Cultural Hegemony's fertility drift | |

Phase 1 alone is a playable feature: a census the player reads. Each later phase adds effects to numbers already
seen to be sane.

## 13. Questions for the owner

1. **Bands:** eight ten-year bands (recommended, for the pyramid) or four broad ones (cheaper, same economics)?
2. **Should the model push back on the engine at all** (momentum, workforce), or stay a display with only events
   reading it? The recommendation is to push back from phase 2.
3. **Corrections against each SoL's equilibrium** (recommended; keeps today's totals) or re-tune the defines' curve so
   ageing alone produces the decline in rich states (more realistic; a world re-balance)?
4. **Sex:** a male share per band (recommended; it is what shows war dents and frontier states) or a single adult sex
   ratio?
5. **Wealth:** widen `te_inh_concentration` (one score, inheritance one term among several; recommended) or keep it
   for inheritance and add a second score? Keep the stock national?
6. **New York against Texas:** the computed national pattern only (recommended), or also the modelled per-state
   pattern (§5.2)?
7. **Family policy scope:** Birth Quotas and its three amendments as proposed? Coercive pronatalism in or out?
8. **Where:** the Society panel's sixth tab plus a state subtab, or the Timeline Extended window? Did "the population
   page" mean either of these?
9. **The rule's default:** Full or Display only?
10. **Demography mod players:** detect it and fall back, or only document it?

## 14. Engine checks before building

1. **One walk, several sums.** Does `every_scope_pop = { … }` in an effect accumulate several state variables in one
   pass, through a named script value in pop scope (`change_variable = { add = te_x }` on `PREV`/`state`)? If not, use
   one script-value walk per sum.
2. **`wealth_share`** as a value in state scope (the quoted form). If it works, it replaces the wealth proxy.
3. **`num_country_dead(root)`** as a value; whether war counters survive the war's end; whether battle dead come out
   of the soldiers' home-state pops.
4. **`modifier:state_birth_rate_mult`** on a state includes laws and techs passed down from the country.
5. **Who pays pensions in money** under Old Age Pension: the dependent wage, welfare payments or the state.
   This decides whether §7's money cost needs a modifier at all.
6. **GUI**: whether a list of the country's states can be ordered by a script value; mirrored `progressbar` pyramids;
   a 6-slot Society strip next to CMF.
7. **Cost**: the profiler on a yearly pulse with the walk in every state, in a 1950s and a 2050s save.
