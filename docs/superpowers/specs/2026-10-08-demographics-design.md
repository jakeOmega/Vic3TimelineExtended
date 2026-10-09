# Demographics: age, sex, wealth and where people live — design (scoping draft)

> **Status: scoping draft, 2026-10-08, third round.** It widens the Wealth Concentration score from #822
> (`2026-10-08-inheritance-laws-design.md` §3) into a demographics system with its own panel. It covers what to
> track, what moves each number, what each number moves and what the player controls. The owner has answered two
> rounds of questions (Decisions, below). §13 lists what is still open. §14's engine checks were run in game on
> 2026-10-08; each answer is written into the section that uses it, with the evidence in
> `docs/testing/demographics-probe-results-2026-10-08.md`.
> The plan for phases 0 and 1 is `docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md`. Its research
> corrected the places where this draft assumed something the code doesn't have (rule names, map modes, sorted lists,
> cohort storage, urban population, land tenure and France's start); each is fixed in place.
> Phase 0 (the model, its harness and these corrections) is built in PR 1 (#828); phase 1 (the census, both panels,
> per-state Wealth Concentration and the rule) is built in PR 2 (branch `demographics-phase1`). It applies nothing to
> population yet: what waits for phases 2 and 3 is listed in `docs/systems/mod_systems.md` § Demographics.
> Numbers are starting proposals for the calibration harness (§12), not decisions.

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
- **Workforce and dependents**, set by a working-adult ratio. Vanilla's default is 0.25 (`WORKING_ADULT_RATIO_BASE`);
  `pop_types` sets aristocrats 0.2 and slaves 0.5. It is moved by `state_working_adult_ratio_add`: vanilla's
  women's-rights laws add 0.05 to 0.3, and Old Age Pension subtracts 0.01 per level of its institution.
- **Birth rate and mortality**, from the standard-of-living curves in the defines plus `state_birth_rate_mult` and the
  `*_mortality_mult` family. The mod's defines (`common/defines/extra_defines.txt:79-88`) run births from 5.7% a year
  at SoL 0 down to 0.96% at SoL 35, and deaths down to 1.2%. Modifiers scale those base rates: a −50% mortality
  modifier halves deaths to 0.6%, so the state grows. Absent modifiers, a state at SoL 35 or above shrinks by 0.24% a
  year. Either way, its rates depend only on its SoL and modifiers today, not on its history.
- **Readable values**:
  - a pop's `total_size`, `wealth`, `standard_of_living` and `literacy_rate`;
  - a state's `state_population`, `total_urbanization`, `average_sol`, `state_unemployment_rate`, `gdp`, `migration_pull`
    and `modifier:<key>` totals;
  - a building's `private_ownership_fraction`, `self_ownership_fraction` and `country_ownership_fraction`, as bareword
    fields (`multiply = private_ownership_fraction`), and `"fraction_of_levels_owned_by_country(<country>)"`;
  - a war's `"num_country_dead(<country>)"`, `"num_country_wounded(<country>)"` and `num_dead`, while the war lasts
    (§2.5);
  - the year (`add = year`).
- **Iteration.** Script values can walk pops and states (`te_inh_agrarian_share_value`, `country_max_state_population`).
  One effect walk fills any number of sums: local variables, the state's variables through `PREV`, and named pop-scope
  script values read as `PREV.<value>` all match separate walks exactly.
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
- **Mortality the mod already touches.** The Ministry of Consumer Protection (`institution_ministry_of_consumer_protection`,
  −1% mortality), the pharmaceutical companies and the drugs system (`mod_systems.md` § Drugs).
- **Panels.**
  - The vanilla **Population** panel (`gui/pops_overview.gui`, `PopsOverviewPanel`; title `POPS_OVERVIEW_TITLE`) has
    four tabs: Overview, Charts, Detailed List and National Cast. It shows strata over time, SoL over time, spending and
    the pop list. The mod doesn't override it yet.
  - The state panel's Population tab has three 170 px subtabs: Statistics, Pops and Characters.
  - The history store draws column charts of stored samples.
  - The mod's map-mode mechanism (`te_map_mode_script_values.txt`) repurposes vanilla's Migration Attraction map mode
    to paint a per-state script value, but it is switched off. State-scope `migration_pull` returns the country's
    value, so the map shows no gradient (`common/decisions/extra_decisions.txt:96-108`). The six map modes in §10 wait
    for a working per-state source.

**Prior art.** The Demography Workshop mod (`3759720467`, `docs/systems/system_panels_feasibility.md` §7) gives every
state 17 five-year bands, updated monthly. The owner doesn't use it. §11.5 covers players who do.

## Decisions (owner, 2026-10-08)

| Question | Decision |
|---|---|
| Gameplay effects | **Yes.** The system is designed around them; a display-only setting exists only as a game-rule option |
| World population | **Retune it.** The share of women of childbearing age drives the birth rate and the share of old people the death rate. **Wealth, education and technology (birth control) drive fertility** and so long-run growth (§2.3) |
| Calibration | **History to 2020; after that the UN projection is only a check** on a world where the AI does nothing special (§2.3) |
| Death by age | **Depends on technology, healthcare, consumer safety and the like**, each acting on the ages it really affects: consumer safety on the young, for example (§2.4) |
| Age resolution | **Birth cohorts**, which age exactly with a yearly update. **One-year cohorts if a benchmark shows them cheap, otherwise five-year** (§1, §14 Q9) |
| Sex | **Track women and men directly**, not one sex as a share of the other. Births then scale with *x*, not 1 − *x*, and the female population follows a steadier path (§3) |
| Wealth Concentration | **One score, kept per state**: how much of the state's property belongs to a few great fortunes rather than many owners. The national figure is weighted by ownership levels: owner buildings, self-owned buildings and a share of bureaucrats for state property (§4.2) |
| Migration profile | **Organic, not by date**: from the destination's jobs, transport technology, women's rights at the origin and destination, and crises at the origin (§2.5) |
| Late-era display | **A toggle between calendar and biological age** on the pyramid from era 11 (§1) |
| Cohort ring | **To about age 150 from 1836**, provisional; empty slots are skipped until people live that long (§1) |
| State property in the national Wealth Concentration | **The country's state-owned levels × the state's share of its bureaucrats × 0.1** (§4.2) |
| Coercive pronatalism | **No separate mechanic.** The pro-natalist law's description stays open: "through propaganda, incentives, or even coercion". Players read what a given state does into it (§8.1) |
| Population measures | **GUI buttons, not amendments**: a measure is a policy choice made within a law, not a new legal framework. **The catalogue in §8.1 stands, national only for now**; decree versions may come later (§8.1) |
| Pension age | **A three-way setting** (Early, Standard, Raised) under Old Age Pension, not amendments (§8.2) |
| Settlement pattern | **Labels and effect sizes as proposed** (§5.2) |
| Where the country view goes | **The vanilla Population panel**, as a new tab (§10) |
| One metropolis or several cities | **Design it** (§5.2): it interacts both ways with economic pull, infrastructure and Migration Crowding. Not the first priority |
| Game rule | **Yes**: Full / Display only / Disabled. Display only is kept because it costs almost nothing once Disabled works (§11.4) |

## Design rules (the pillars, made concrete)

1. **The engine counts the people; the model says who they are.** Each year the model's cohorts are scaled to the
   engine's population, so the panel and the engine never disagree on the total. The model sets birth and death rates
   through modifiers (§2.3, §2.4) and doesn't move people.
2. **Track only what changes a decision or explains one.** Every number either moves something (§7) or shows the
   player why something moves.
3. **Laws act on inputs, and the model produces the consequences.** A law or measure changes fertility, mortality or
   who works. The workforce and pension effects arrive through the model, with the real lag: fewer births today give
   fewer workers in fifteen years.
   - Flat modifiers that stand in for an age, fertility or survival effect move into the model (§8.4).
   - Ones that stand for women's or children's work stay.
4. **Slow clocks with visible momentum.** Each number moves over a generation, and the panel shows where it is heading.
   The fun is in seeing a window open twenty years ahead (§9, §10).
5. **Effects are deviations from a stated reference, and capped.** The reference structure is the 1836 equilibrium.
   Every state starts at the equilibrium of its own 1836 inputs, so nothing jumps on day one. A save from before the
   system starts each state at its equilibrium (the #822 pattern).
6. **Every number has a real meaning and an anchor value.** The sources are UN World Population Prospects (WPP) for
   ages, fertility and mortality, and the World Inequality Database (WID) and Lindert and Williamson for wealth. The
   panel uses real units: children per woman, years, a Gini coefficient.

## 1. What to track

| Stat | Scope | Source | Shown as |
|---|---|---|---|
| **Age and sex**: birth cohorts (one or five years wide, §1) reaching about age 150, each holding its women and its men | state; the country's is the sum | modelled (§2) | population pyramid, men left and women right |
| Derived: median age, dependency ratio, working-age share, sex balance | state, country | from the cohorts | table, with a trend arrow |
| **Fertility**: children per woman, with its wealth, education and technology terms | state | modelled from engine inputs (§2.3) | table; the terms on hover |
| **Mortality**: life expectancy at birth and at 65, infant mortality, with the five causes' terms | state | modelled from engine inputs (§2.4) | table; the terms on hover |
| **Net migration** last year | state | the residual after natural change (§2.5) | table |
| **Income inequality**: a Gini coefficient | state; country | computed from pops each year (§4.1) | table; map mode (blocked, §10) |
| **Wealth Concentration**: the #822 score, now per state | state; country | modelled stock (§4.2) | bar with its target segment; map mode (blocked, §10) |
| **National urban pattern**: the largest city's share, the effective number of cities | country | computed from states (§5.1) | label and figures |
| **Settlement pattern**: one metropolis or several cities | state | modelled stock (§5.2) | label; map mode (blocked, §10) |

**Left out:** ages on individual pops, age by culture or religion, and education by age. Each costs far more than it
returns at Victoria's level of detail.

### How ages advance with a yearly update (the owner's question)

**The trouble with bands.** A band W years wide, updated yearly, can only pass on 1/W of its people each year, picked
as if they were spread evenly across the band. Someone who entered last year is as likely to move on as someone about
to leave. The band works like a mixing tank: some people pass through in a year and others stay for twice the band's
width, so a group born together spreads out as it climbs. Smaller bands help but don't fix it. A sketch tracked one
group born in the same five years, with nobody dying:

| Scheme | Spread after 10 years | After 30 | After 50 |
|---|---|---|---|
| Ten-year bands, 1/10 moves up yearly | ±9.5 years | ±16 | ±21 |
| Five-year bands, 1/5 moves up yearly | ±6.3 | ±11 | ±14 |
| **Five-year birth cohorts** | ±1.4 (the five birth years) | ±1.4 | ±1.4 |

**Birth cohorts don't move, so they don't spread.** Each state keeps a ring of slots: the people born in 1835–39,
1840–44 and so on. A cohort's age is the year minus its birth years. Nobody is moved between slots. Each year:
- births go into the open cohort;
- every cohort loses its own deaths, at its age's rates for women and for men (§2.4);
- migrants and war dead come out of the cohorts at the right ages (§2.5);
- the whole ring is scaled to the engine's population.

Every five years the open cohort closes and a new one opens. The ring runs to about age 150 from 1836 (owner,
provisional). The oldest cohort, at about 150, folds into a "150 and over" pool, and its slot is reused. The pool also
keeps the mean age of its members, so its death rate stays right however long people live. Before the late eras,
slots above about 95 hold nobody and are skipped.

**Cost.** To age 150, five-year cohorts take about 30 slots, each holding women and men: about 60 variables a state.
One-year cohorts take about 150 slots and 300 variables. Until lifespans pass 95, only about 20 or 100 of those slots
are occupied, and the empty ones are skipped. Either way the work is arithmetic, not pop walks (§11.3), once a year;
the Demography mod updates 17 bands monthly. The slots are calls of one scripted effect with `$SLOT$`, written by a
generator (the mod's idiom for repeated script). The slot for a cohort is (first birth year ÷ the width) mod the
number of slots. The year reads as a value (`add = year`), so no counter is needed.

**Display.** The pyramid draws fixed five-year age bands: 0–4, 5–9 … 85+, with the top band moving up as lifespans
grow. Each cohort straddles two of them in most
years, so its people are split between the two in proportion. That happens in the display only; the model never
splits a cohort.

**Cohort width is a generator parameter (owner, 2026-10-08: measure, then choose).**
- **One-year cohorts** (about 150 slots, 300 variables a state) give single-year ages: a pyramid with no display split,
  and booms and wars visible to the year. The owner would like them if they are cheap, but not at a real slowdown.
- **Five-year cohorts** (about 30 slots) age exactly too, and nothing in §7 needs a finer age.
- **Only the generator changes between them.** It writes one call of the slot effect per slot, a ring of N slots and
  rate lookups by age. The script logic is the same for any width W: births go into the open cohort, which closes
  every W years.
- **The benchmark** (§14 Q9) picks W. It times the yearly cohort step in every state, with 30 slots and with 150, in a
  1950s and a 2050s save.
- **Decision rule:** one-year cohorts if the extra time per year, spread over the twelve monthly pulses (§11.3), is
  negligible against a month's tick. Otherwise five-year.
- **The late eras:** from era 11, biological age adds one variable a slot.
- **Result (2026-10-08, 1836, 887 states).** One run of the step across every state took:
  - about 0.1 s with five-year cohorts (20 of 30 slots occupied);
  - 0.75 s with one-year cohorts (100 of 150 occupied), 1.0 s with all 150 occupied.

  A game month took 11–16 s of wall-clock time. The engine spreads the yearly state pulse over the year (§11.3), so the
  one-year step costs about 1 ms per state on that state's own day. **By the decision rule, one-year cohorts.** Each
  variable adds 60–85 bytes to a plain-text save: the full one-year ring added 16.9 MB to a 197 MB 1836 save, and 100
  occupied slots would add 11–15 MB. The cost scales with states and occupied slots, not pops; a re-run in a late-game
  save (`event te_debug_demog.1` on the probe branch) would confirm it there.

### Ages past 95 and the late eras (the owner's question)

In eras 11 and 12, lifespans can run well past 100. **The proposal is not to add calendar slots but to add biological
age.** From the moment rejuvenation works, what sets someone's risk of death, chance of a child and ability to work is
how old their body is, not the year they were born.

- **Biological age.** Until `personalized_medicine` (era 11), biological age equals calendar age and costs nothing.
  When that technology arrives, each cohort and the pool get a second variable, a biological age, starting at their
  calendar age.
- **How it advances.** It gains a year each year normally, about half a year with era-11 medicine, and nothing under
  `biological_immortality`, which can also wind it back towards about 35.
- **What reads it.** Every age-specific rate reads biological age: the five causes of death, fertility, and the
  workforce rule's 15–64 and over-65 parts (§7).
- **What happens.**
  - The top slots fill with people who are calendar-old and biologically middle-aged. The calendar pyramid turns into
    a column, the late game's striking image.
  - The panel adds "Over 100" and the mean biological age.
  - From era 11 a toggle on the pyramid switches it between calendar age and biological age (owner, 2026-10-08). It is
    a client-side GUI value (`GetVariableSystem`), so it needs no script. In biological age, each cohort's bar sits at
    the band of its biological age.
  - Old age stops making people dependents, so the pension question fades. Deaths fall towards external causes only,
    so births decide growth, and Population Control becomes essential (§8.3).
- **Option: access.** Rejuvenation could reach the upper strata first, scaled by SoL and the health system, so lifespan
  becomes another form of inequality for Wealth Concentration to read. This is one switch on the ageing rate per
  stratum share.

**Why the ring is long from the start rather than extended in era 10 or 11.**
- **Remapping.** A cohort's slot is (first birth year ÷ 5) mod the ring's size. Changing the size mid-game remaps every
  cohort, so slots can't be switched on later without a migration step.
- **Little gain.** Calendar detail past 95 changes no effect once rates read biological age. It only refines the
  pyramid's top.
- **So the ring runs to about 150 from 1836** (owner, provisional). The extra slots sit empty, and are skipped, until
  someone lives that long. The benchmark (§14 Q9) found them cheap: an empty slot costs one variable check.

## 2. The age model

### 2.1 The yearly step

Per state, on the yearly state pulse (the engine fires it on a different day for each state, §11.3):

1. **Births** = the age-specific fertility of each cohort of women aged 15–49 (peaking at 25–29), scaled to the
   state's children per woman (§2.3), into the open cohort. 105 boys are born for every 100 girls (§3).
2. **Deaths**: each cohort's women and men lose their rates, the sum of the five causes at their age (§2.4).
3. **War dead, known kills and migration** come out of, or go into, the cohorts at the right ages (§2.5).
4. **Scale** the ring to the engine's population, and store the population for next year's residual.
5. **Refresh** the births and deaths modifiers and the effects in §7.

### 2.2 Does it behave?

A throwaway Python sketch of the step, run with four bands and with eight, gives these equilibrium structures for
plausible parameters (cohorts give the same equilibria and sharper transients):

| Case | Children per woman | 0–14 | 15–64 | 65+ | Growth a year | Real anchor |
|---|---|---|---|---|---|---|
| 1836 agrarian (the reference) | 5.2 | 35% | 59% | 5–7% | +0.8 to +1.7% | Western Europe 1830s–1850s: 0–14 about 35%, 65+ 4–6% |
| High fertility, falling mortality (1950s) | 6.0 | 38% | 54% | 8% | +2.6% | developing countries 1950–70: 0–14 40–45% |
| Replacement fertility | 2.0–2.2 | 20% | 60–62% | 19–20% | about 0 | |
| Aged | 1.3 | 12% | 55–56% | 33% | −0.9 to −1.2% | Japan today: 0–14 11%, 65+ 29%, children per woman 1.2 |

**The transients carry the gameplay.**
- Drop fertility from 6 to 2 and the working-age share climbs from 54% to 64% over twenty years, then holds for about
  thirty. That is the **demographic dividend**. Real East Asian peaks reached 70–74%; the band sketch underestimates
  them because it blurs, and cohorts should come closer.
- Cut fertility to 1.3 after that and the share falls back to 57% by year 100, while 65+ reaches 30%.

Both appear without being scripted as events.

### 2.3 Fertility: the retune

**What changes in the defines.** The SoL curves stop carrying the whole demographic transition. They become the
**wealth** term only, as age-standardised rates (rates for the 1836 reference structure):

| Define | Today (a month) | Proposal (a month) | Meaning |
|---|---|---|---|
| `@max_birthrate` | 0.00475 at SoL 0 | about 0.0038 at SoL 8 or below | about 6.2 children per woman at the reference structure |
| `@min_birthrate` | 0.00080 at SoL 35 | about 0.0021 at SoL 35 and above | about 3.5 children: what wealth alone does |
| `@min_mortality`, `@max_mortality` | 0.00100, 0.00600 | set by the harness (§2.4) | the wealth (nutrition) part of mortality only; the model's causes do the rest |

The mod's `pop_needs_curves` and the defines' growth constants are tuned together in the calibration harness (§12).

**Desired fertility and the means.** The model works out a *desired* fertility and how much of the gap between it and
natural fertility the population can close. The *means* term is the technology. This is the "supply, demand and
means" view of the fertility transition.

- **Wealth**: the retuned SoL curve, applied by the engine.
- **Education**: desired × (1 − 0.4 × literacy). Literacy is the population-weighted figure from the yearly pop walk.
  Women's schooling is the strongest single predictor of fertility; literacy is the nearest proxy the engine has.
- **Child survival**: desired × (1 − 0.4 × (life expectancy − 30) ÷ 50), clamped. Parents stop insuring against child
  deaths a generation after the deaths stop. Life expectancy comes from §2.4.
- **Urban life**: desired × (1 − 0.2 × the urbanisation rate). Children cost more and earn less in a city.
- **Technology: the means.** The share of the gap a population can close:

  | Source | Means |
  |---|---|
  | Traditional methods (start) | 0.4 |
  | `vulcanization` (era 3: rubber condoms) | 0.55 |
  | `contraceptive_pill` (era 7) | 0.8 |
  | `modern_pharmaceuticals` (era 8: long-acting methods) | 0.9 |

  - **Access** multiplies the means: 0.3 + 0.7 × literacy.
  - **Laws and measures** shift it (§8.1). The cap is 0.95.
- **The fertility factor** = 1 − means × (1 − desired).

**Age structure.** Births come from the cohorts of women aged 15–49 (§2.1), so the share of women of childbearing age
moves the birth rate by construction.

**Applied as** one births modifier, refreshed yearly from the state pulse: the model's births ÷ the engine's births
before the modifier − 1. Every other birth modifier stays an input and is read through. That covers vanilla's laws,
events, starvation, and Forced Heirship's rural cut.
- **Reading the rest.** A state's `modifier:state_birth_rate_mult` includes the country's modifiers (a test modifier on
  the country showed in every state's read), so the model reads the total at state scope and takes out its own term.
- **The clamp.** At −0.9 Qing's births fell to about a tenth, as 1 + the total says. At −3 they stopped; they never
  turn negative (Qing lost what its deaths alone would take). Where between −0.9 and −3 they reach zero wasn't
  measured, presumably at −1. The clamp keeps the total at −0.9 or above, a safe margin.
- **The engine's births before the modifier** are taken to be each pop's SoL curve × its size × (1 + the other
  modifiers). Qing's births, worked out on that model, came to 0.44% a month against the curve's 0.475% for low-SoL
  pops: consistent, not proof. The world-wide check across all SoL bands is the harness's first step (§12).
- **Changes show within a month, not at once.** Adding a birth modifier showed in full in the first month; the switch
  from −0.9 to −3 and the removal each took part of a month to show fully.

**Sketch results** (the formula above, with plausible inputs):

| Case | Sketch | Real |
|---|---|---|
| Britain 1836 | 5.5 | about 5 |
| France 1836 (Family Limitation, §2.6). The sketch leaves out Forced Heirship's birth cut, which the engine applies on top | 4.9 | about 3.8 |
| Britain 1900 | 3.9 | about 3.5 |
| The West 1950 (before the Pill) | 3.0 | 2.5 (Europe) to 3.5 (US) |
| The West 1990 | 1.4 | about 1.7 |
| India 1975 | 5.2 | about 5.2 |
| Niger 2020 | 5.0 | about 6.7. High desired fertility in the Sahel is a cultural term the sketch lacks; calibration decides whether to add one |

**Calibration targets.** Match the shape of world history to 2020. The game's own 1836 total sets the scale.
- **World multiples:** 1900 ≈ 1.5× 1836; 1950 ≈ 1.5× 1900; 2000 ≈ 2.4× 1950.
- **Regional shares:** Europe from about 22% of the world in 1850 to under 10% today; Africa from about 9% to 18%.
- **Great-power ratios** at 1900, 1950 and 2000.
- **After 2020**, the UN's medium projection (a peak of about 10.3 billion in the 2080s, WPP 2024) is only a check on a
  world where the AI does nothing special. Players and era-12 technologies are free to diverge from it.

**Where today's defines start** (probe, early 1836): the world grows about 1% a year, above the 0.6% a year that
"1900 ≈ 1.5× 1836" implies. Great Britain shrinks by 0.06–0.09% a month, most likely through emigration, so the
harness has to carry migration.

### 2.4 Mortality by age

**Five causes, each on the ages it really affects.** This is the epidemiological transition: infection first, then
accidents and violence, then the chronic diseases of old age (Omran, 1971). Each cause is a rate schedule over age,
for women and for men. A cohort's death rate is the sum of the five at its age. Life expectancy at birth and at 65,
and infant mortality, are computed from the rates for the panel and for fertility's child-survival term.

| Cause | Ages | Lowered by | Raised by | Anchors |
|---|---|---|---|---|
| **Infection and malnutrition** | mostly under 5; also 5–14 and the old | SoL (nutrition: the engine's curve); mothers' literacy; the health system law and institution; `medical_degrees`, `pharmaceuticals`, `modern_nursing`, `antibiotics`, `modern_vaccines`, `antibiotic_mass_production` | crowding in cities before sanitation (Migration Crowding active and no urban planning); starvation and devastation (engine, read through); tropical disease and heat (global warming) | infant mortality about 150–250 per 1,000 births in 1836 Europe, about 50 in 1950, under 5 today |
| **External causes: work** (industrial and mining accidents) | 15–64, split between the sexes by their share of the workforce | the Workplace Safety institution | child labour (engine); mining and heavy-industry employment | |
| **External causes: other** (violence, traffic, everyday accidents) | 15–44; men about three times women | the Ministry of Consumer Protection (move its flat −1% here); policing; road-safety techs | turmoil (`state_mortality_turmoil_mult`, read through); motor vehicles from about era 5 | |
| **Maternal** | women 15–44, per birth | the health system; `modern_nursing`, `antibiotics` | high fertility (more births); restricted contraception (§8.1) | about 1 death in 100–200 births in the 19th century; about 1 in 10,000 in rich countries today |
| **Chronic and old age** | rising from 40, doubling about every 8 years; men higher | the health system law (public insurance most); `modern_pharmaceuticals`, `personalized_medicine`, `telemedicine`; pensions (old-age poverty); `biological_immortality` (halts the rise, §8.3) | pollution (engine, read through); drugs and alcohol (the drugs system); heat waves (global warming) | life expectancy at 65: about 10 years in 1900 and about 20 today, most of the gain since 1970 |

**Work deaths follow the workforce.** Work accidents are split between women and men by each sex's share of the
workforce, which the women's-rights laws set: lowest under No Women's Rights, higher on farms under Women in the
Fields, and close to men's share under Women in the Workplace, Women's Suffrage and Protected Class. So Workplace
Safety protects women more as they enter work, and a country that brings women into mines and factories without it
sees their deaths rise. The other external causes stay mostly men's.

**Applied as** one deaths modifier, refreshed yearly from the state pulse: the model's deaths ÷ the engine's deaths
before the modifier − 1. The engine's own mortality modifiers (starvation, devastation, pollution, turmoil, vanilla's
health laws, events) stay as they are and multiply on top. The model only places them by age: starvation and disease
fall on the young and old, devastation on everyone, pollution on chronic causes. The share of old people therefore
drives the death rate, as the owner asked. An aged state with excellent health still has a high crude death rate:
Japan's is 13 per 1,000 because a third of its people are over 60, not because its health is poor.

**Why split by cause.** Each cause has its own levers, so the player sees them separately:
- schools and vaccines save children;
- workplace safety saves workers, women as well as men once women's-rights laws bring women into work;
- consumer protection and policing save young men;
- hospitals and pharmaceuticals add years at the end.

That makes the health and safety institutions matter beyond their flat percentages. It also gives the late game
something to buy: once children stop dying, the only gains left are at old ages, and those make the population older.

### 2.5 Migration, war dead and other losses

The engine moves and kills people; the model sees only the result. Each year:

1. **War dead.**
   - For every war the owner is in, read `num_country_dead(owner)` and take the change since the last pulse.
   - Share it out among the owner's states by their share of the country's soldiers (from the yearly pop walk).
   - The dead come from the men of the cohorts aged 18–40, about 95% of them men.
   - The mod defines a Women in Combat Roles modifier (`women_combat_roles_modifier`) that nothing grants yet. Whatever
     grants it should lower that share.
   - The counters can't be relied on at the war's end: on `on_war_end` the war scope still exists, but every counter
     printed 0 (seven wars in the probe). That line had no control value, and ROOT there is a diplomatic play, so a
     value that fails to print under that ROOT would look the same. Either way each war's `num_country_dead` is
     snapshotted on the owner's monthly pulse, and the yearly step takes the change. The dead of a war's last
     part-month are lost.
   - Read the dead, not the casualties: casualties = dead + wounded.
2. **Known kills.**
   - Nuclear strikes record their dead per state; they come from all ages and both sexes.
   - Resettlement records its arrivals and departures, with its programme's profile.
   - Violent Hostility's kills come from all ages.
3. **The residual**: the population change, less natural change, less (1) and (2). This is mostly migration.
   - Natural change here is the engine's: each pop's growth curves × the multiplier the engine applies to it. That
     multiplier is the state's modifier read plus per-pop terms the read leaves out: literacy and starvation for births;
     class, workplace, working conditions and starvation for deaths. Each is floored at 0 per pop
     (`docs/testing/demographics-growth-probe-results-2026-10-09.md`). With the state read alone, every country
     read about 0.6% a year as emigrants.
   - A gain arrives with the destination's migrant profile, and a loss leaves with the origin's (below).
   - The profile is worked out each year from the state and its country, not from the calendar.
   - A residual under 0.3% of the population is treated as model error and spread over all cohorts. Otherwise the
     model's own rounding would make states look like migration hubs.

**The migrant profile.** The model sees only each state's net change, not where its migrants came from. So a state's
arrivals take the profile of the state they arrive in, and its departures the profile of the state they leave. Each
profile mixes three kinds of migrant:

| Kind | Ages | Women's share | Its weight rises with |
|---|---|---|---|
| **Labour migrants** | 18–35 | set by the jobs at the destination (below) | the destination's job openings; the cost of the move being high |
| **Families** | parents with children; few over 60 | about half | cheaper transport (`paddle_steamer`, `railways`, `combustion_engine` and the mod's aviation techs); women's rights at the origin, since women can move on their own account; the time a migration has been running (chain migration: the men send for their families) |
| **Refugees** | everyone | about half | war, devastation, turmoil and Violent Hostility at the origin |

**Labour migrants' women's share follows the destination's jobs.**
- Mines, logging, plantations, construction, railways and the army draw men.
- Textiles, light industry and services draw women, as far as the destination's women's-rights laws let women work
  (the same workforce share as work deaths, §2.4).
- The weights come from the destination's employment by building group, read in the yearly pop walk.

**What it produces.**
- A frontier mining state fills with young men.
- A textile town draws young women: Lowell's mill girls, Lancashire.
- Cheaper steamships turn a male stream into a family one.
- A civil war sends out whole families.
- The places left behind grow older and, where the men left, more female, as Ireland and southern Italy did.

None of it is scripted by date.

### 2.6 Starting values and new states

- **1836.** Each state starts at the equilibrium of its own inputs, taken from a lookup by fertility and life
  expectancy that a generator writes. Historical overrides:
  - France starts with fertility well below its neighbours'. Its transition began around 1800. The head start is a
    modifier, Family Limitation (`country_fertility_means_add`, +0.6), which France starts with and other countries can
    be given. #822's Forced Heirship already pushes the same way.
  - The US frontier states start young and male.
- **A state with no variables** (a new state, a split state region, an old save) starts at its equilibrium. A split
  state could copy its sibling's cohorts instead, since it is the same people.
- **Revolutions.** State variables stay on the states. The country's numbers are recomputed from them, so nothing is
  lost (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").

## 3. Sex

**Each cohort stores its women and its men as numbers of people.** The engine keeps script values in units of 1e-5,
and a one-year cohort of the very old is a share near that, so its deaths would round away. Births come from the
women's counts, war dead and most external deaths from the men's, maternal deaths from the women's. Nothing is
computed as one minus another. A war that kills half the young men leaves the women's counts, and the births they
carry, on their steady path, while the men's deficit works up the pyramid and out within a lifetime. The female share
shown in the panel is derived.

**What moves the balance:**

| Source | Effect | Anchor |
|---|---|---|
| Sex ratio at birth | 105 boys per 100 girls normally | the biological constant |
| Sex-selective births | up to about 115–120 boys per 100 girls under a birth limit once prenatal sexing exists (§8.1) | China's sex ratio at birth reached about 118 in the 2000s |
| War dead | about 95% men, aged 18–40 | the Soviet Union in 1959: about 0.82 men per woman |
| Migration | labour migrants to mines and frontiers are mostly men, to mills and services more often women; families and refugees are balanced (§2.5) | California in 1850 was over 90% male; Lowell's mill workers were mostly young women |
| Mortality | men die more from external and chronic causes, women from maternal causes; women outlive men by about 2 years at a life expectancy of 35 and 5–7 at 75 | |

**What it moves** (adults 20–59, capped, small on purpose; the evidence on effects is weaker than on causes):

- **More women than men** (after a great war):
  - fewer marriages, so births × the square root of (men ÷ women), at most 1;
  - more women at work (+ working-adult ratio);
  - support for women's-rights movements. Britain's "surplus women" after 1918 are the example.
- **Fewer women than men** (frontier, migrant-worker or sex-selected populations):
  - births fall on their own, since there are fewer women;
  - radicals and crime rise a little (Hudson and den Boer's *Bare Branches*), which feeds the policing laws.

## 4. Wealth

Two numbers: a **flow** (how unequal this year's incomes are) and a **stock** (who owns the property). Both are kept per
state. The stock is the #822 score.

### 4.1 Income inequality (state, computed yearly)

- **The measure.** A Gini coefficient from the state's pops. Pop income can't be read in script, but `wealth` can. A
  generator turns the wealth level into spending per head using the pop-needs curve from `pop_needs_curves`, as a
  proxy for income.
  - **Grouped form:** each stratum's share of people and of income, ordered lower < middle < upper. One pop walk fills
    all the sums (§14 Q1).
  - **Not the engine's `wealth_share`:** it has no value form (rejected at load), and it measures political strength
    from wealth, not wealth. Britain's aristocrats pass `value > 0.2` while holding 2.8% of the country's pop wealth ×
    size.
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

**What it represents (owner, 2026-10-08).** The engine already has inequality *between* classes: each stratum's pops
carry their own wealth, and §4.1's Gini measures it. A score that restated it would double-count. What pops can't
show is how property is held *within* the owning classes. A state's capitalists are one pop, whether its factories
belong to three dynasties or to ten thousand shareholders.

**How much of the state's property belongs to a few great fortunes rather than to many owners.** The form it
takes depends on the state:
- **On the land:** great estates against smallholdings. Prussia's Junker east and Andalusia's latifundia sit at the top;
  Württemberg's divided farms and America's homesteads at the bottom.
- **In industry and finance:** dynastic family firms and trusts against dispersed shareholders, cooperatives and the
  state.

It is grounded in readouts the engine has:
- the land tenure law, weighted by the state's agrarian share;
- the state's building levels in private hands against self-owned (cooperative) and state-owned levels
  (`private_ownership_fraction`, `self_ownership_fraction`, `country_ownership_fraction`), summed over its buildings
  once a year. The fractions read as values, but **the walk must skip buildings that aren't capital in this sense**.
  Manor Houses and Financial Districts read self-owned (they own themselves), Subsistence Farms read private, and
  government buildings such as the Construction Sector read state-owned. Britain's three largest buildings in 1836
  were a Manor House (173 levels), a Financial District (159) and a Subsistence Farm (140);
- foreign ownership, for absentee fortunes: 1 − `"fraction_of_levels_owned_by_country(<owner>)"`. That value counts
  the owner country and its investors, and includes self-owned and state-owned levels.

**Alternatives:**
- **(B) the top tenth's share of all wealth.** This overlaps the Gini.
- **(C) a purely political oligarchy index.** This loses the economics.

**The score.** One score per state. It keeps #822's 0–100 scale, its 3% yearly drift and its two modifiers' effects.
Each state drifts toward its own target. The country figure, kept in `te_inh_concentration` so #822's loc and
tooltips keep working, is the states' average weighted by **ownership levels** (owner, 2026-10-08). That is where the
property is held:
- each level of a Financial District, Manor House or company headquarters (`building_financial_district`,
  `building_manor_house`, `building_company_headquarter`, `building_company_regional_headquarter`) counts 1;
- each level of a self-owned building counts 1, leaving out the ownership buildings above, which read self-owned
  too;
- **state-owned property** goes where the government's administrators are (owner, 2026-10-08). The country's total
  state-owned levels × the state's share of the country's bureaucrats × 0.1. A capital with half the country's
  bureaucrats gets 0.05 × the country's state-owned levels.
  - The 0.1 keeps the average leaning to private and cooperative property in a mixed economy.
  - In a command economy, where nearly everything is state-owned, these weights are nearly all there is, so the
    average still works.
  - The state-owned levels come from the building walk (`country_ownership_fraction` × levels, summed over the
    country), and the bureaucrats from the pop walk.

The panel shows the target's terms as bars (style guide rule 5), and will show a map mode when one works (blocked, §10).

**The target** is a sum of terms around 50:

| Term | Scope | Proposal | Why |
|---|---|---|---|
| Inheritance law and amendments | national | today's targets re-centred on 50: Primogeniture +30, Testation +10, Customary 0, Forced Heirship −25, State Heir and Possession −50; amendments as now | how fortunes pass between generations; #822 unchanged in effect |
| Land tenure (vanilla land reform laws) | national law × the state's agrarian share | Values sit on vanilla's five base laws: Serfdom +15, Tenant Farmers +5, Commercialized Agriculture 0, Peasant Proprietorship −10, Collectivized Agriculture −20. The four variants (`parent =`) take their parent's value: Manorialism Serfdom's; Latifundias and Expanded Latifundias Tenant Farmers'; Homesteading Peasant Proprietorship's | land was most of the wealth in 1836, and it matters where the land is |
| Ownership | state | the share of the state's building levels in private hands, against cooperative and state levels: 40 × (share − 0.65), capped ±20 (§13) | who holds the capital |
| Income inequality | state | +0.5 × (the state's Gini − 0.40) × 100, capped ±15 | fortunes grow from unequal flows: the rich save more |
| Taxes on wealth | national | Graduated Taxation −5; the tax code's dividend and estate settings when that rule is on | |
| Economic laws (owner, 2026-10-09) | national | Laissez-Faire +10, Extraction Economy +5, Interventionism −5; Guilds and Chartered Monopolies and Freedom of Contract +5, Antitrust Enforcement (`law_trust_busting`) and Regulated Utilities −5; others 0; capped ±15 | how freely capital compounds and combines: top-decile wealth shares rose to about 1910 under laissez-faire and fell to the 1970s under regulation, which the other terms alone ran backwards |
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

**What it moves.** None of these effects repeats what pop wealth already does:

| Effect | Scope | Meaning |
|---|---|---|
| Aristocrats' and Capitalists' clout | country, from the national figure | political capture: a few great fortunes buy more influence than the same wealth spread wide |
| Investment-pool efficiency: owners' when high, Farmers' and Shopkeepers' when low | state | who does the saving and investing |
| Qualifications and education access, lower when high | state | social mobility |
| Radicals, higher when high | state | visible inequality |
| In farm states: migration out of the countryside, higher when high | state | land hunger pushes the young off the land (southern Italy's emigrants), which feeds the age model |

The first two are #822's effects, split by scope. That makes two state modifiers and two country modifiers in place of
#822's two, each with one refresh site.

**Built (phase 2, 2026-10-09).** Three state modifiers, not two: a multiplier is one variable, and the farm-state
migration needs the score and the agrarian share, so it is its own modifier.
- Country, from the national figure: `inh_great_fortunes` (Aristocrats and Capitalists +20% clout at full) and
  `inh_dispersed_wealth` (Aristocrats −20%), refreshed by `te_demog_wc_national` as before.
- State, from the state's own score: `inh_concentrated_property` ((score − 50)/50: Aristocrats' and Capitalists'
  investment pool +10%, radicals +10%, qualifications −10%, education access −0.05), `inh_dispersed_property`
  ((50 − score)/50: Farmers' and Shopkeepers' investment pool +10%) and `inh_land_hunger` ((score − 50)/50 × the
  agrarian share: migration quota +20%). One refresh effect, `te_inh_refresh_wc_state_effects`, on the state's yearly
  pulse after its drift and at game start through a hidden state event, so the multiplier resolves against the state.
  A shift or shock made from country scope reaches them at the state's next pulse.
- All five run under every Demographics rule setting (owner): Wealth Concentration is #822's, and the inheritance laws'
  worth should not depend on the census rule.

**Migration.** Each state starts at its country's current score, then drifts.

## 5. Where people live

### 5.1 The national urban pattern (computed)

- **Urban population per state.** The engine has no per-state urbanisation rate (`total_urbanization` is points, not a
  share). Urban population is the pop walk's people whose workplace isn't in a rural building group. Pops with no
  workplace count as rural if they are Peasants, otherwise urban.
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

**Labels** (owner, 2026-10-08): Metropolis (≥ 60, New York), Leading City (40–60), Several Cities (20–40, Texas),
Market Towns (< 20).

## 6. What feeds in

| Source | Into | How |
|---|---|---|
| SoL (wealth) | fertility; infection and malnutrition deaths | the retuned curves (§2.3, §2.4) |
| Literacy (education) | desired fertility; access to the means; child deaths | the yearly pop walk (§2.3, §2.4) |
| Contraception technology: `vulcanization`, `contraceptive_pill`, `modern_pharmaceuticals` | the means | tech tiers (§2.3) |
| Medical technology, health laws and institutions | the five causes of death, each at its own ages | §2.4 |
| Workplace Safety; women's-rights laws | work deaths, split between the sexes by their share of the workforce | §2.4 |
| Ministry of Consumer Protection, policing | other external deaths: young adults, mostly men | §2.4 |
| Pensions | old-age deaths; who among the old works | §2.4, §7 |
| Drugs and alcohol, pollution, heat | chronic and old-age deaths | §2.4 |
| Every other birth or mortality modifier (vanilla laws, events, starvation, devastation) | fertility, mortality | read through, placed by age |
| Family & Reproductive Policy and its measures | desired fertility, the means, the sex ratio at birth, maternal deaths | §8.1 |
| Wars | men aged 18–40; refugees from war zones | `num_country_dead` shared out by soldiers; the refugee share of the migrant profile (§2.5) |
| Migration, mass migration, the migration laws | by the migrant profile: labour, families or refugees (§2.5) | residual, profiled by jobs, transport technology, women's rights and crises |
| Internal Resettlement | its programme's profile (Rustication takes the young, Managed Retreat the old) | its own counters |
| Nuclear strikes, Violent Hostility | all ages | recorded or residual |
| Child-labour, pension and retirement settings | who among the young and old works | participation weights (§7) |
| Ectogenesis (the Youth Center PM) | births depend less on how many women of childbearing age there are | weakens the women's-cohort term in states with the PM |
| Biological Immortality (era 12) | ageing stops | §8.3 |
| Cultural Hegemony (later phase) | desired fertility drifts a little toward the hegemon's | the "soap-opera effect": Brazil's fertility fell where TV novelas reached (La Ferrara et al., 2012) |
| Inheritance, land tenure, ownership, taxes, war, devastation, revolution, banking crises | Wealth Concentration | §4.2 |
| Capital, ports, area, industry, infrastructure, crowding, urban planning | settlement pattern | §5.2 |

## 7. What it feeds

All effects are refreshed once a year by the dynamic-modifier pattern, each from one site. State effects run from the
state pulse and country effects from the country pulse. Sizes are starting proposals.

| Effect | Modifier | Rule | Cap |
|---|---|---|---|
| **Workforce** | `state_working_adult_ratio_add` | 0.3 × (effective working share ÷ the reference − 1). The effective working share is defined below | ±0.08 |
| **Births and deaths** | `state_birth_rate_mult`, `state_mortality_mult` | §2.3, §2.4 | births clamped above −0.9 in total |
| **The pension and health bill** | `country_institution_cost_institution_social_security_mult` and `_health_system_mult` (institution costs are bureaucracy) | 0.5 × (national 65+ share ÷ 0.07 − 1). Pensions also need a money cost: vanilla's charges the treasury nothing for the old (§14 Q6, open in §13) | +1.0 |
| **Conscription** | `state_conscription_rate_mult` | men aged 20–39 ÷ the 1836 reference − 1 | ±0.25 |
| **Youth bulge** | radicals from movements, turmoil effects | ages 20–29 above about 18% of the population (1836's share is about 17%), × the state's unemployment rate | small |
| **Sex balance** | births, working-adult ratio, movements, radicals | §3 | small |
| **Inequality** | lower-strata radicals; crime | §4.1 | small |
| **Wealth Concentration** | clout, investment pools, mobility, radicals, rural migration | §4.2 | as now |
| **National urban pattern** | throughput and migration pull in the primate state; pull and turmoil elsewhere | §5.1 | small |
| **Settlement pattern** | crowding density, infrastructure from population, throughput, fertility, turmoil | §5.2 | small |

**The effective working share** has three parts:
- ages 15–64;
- plus the 10–14s times their participation: 0.3 under Child Labor Allowed, 0.1 under Restricted, 0 under Compulsory
  Primary School;
- plus the over-65s times theirs: 0.5 with no pension, falling towards 0.15 as Old Age Pension's institution rises,
  moved by the pension-age setting
  (§8.2).

**How fast it bites.** The mod sets `WORKING_ADULT_RATIO_SKEW_MAXIMUM = 1000000` (`extra_defines.txt:67`; vanilla
2.0). That define caps how hard a pop's actual ratio is pulled back to its target, the dial this effect moves. Whether
the mod's value makes a change take hold at once is unmeasured (§14 Q11).

**The reference** is the same formula on the 1836 structure under the laws in force. So a law adds nothing flat;
vanilla's own law effects stay as they are. What a law sets is how much a young or old population costs.

**What the workforce effect does over a game** (with a pension and compulsory schooling):
- **The dividend window:** +10% in the sketch, and up to +25% at real East Asian peaks. That is +0.03 to +0.07, about
  one tech's worth: the Pill gives +0.05.
- **A Japan-like structure:** about 0, because its elderly replace the children of 1836 as dependents.
- **An extreme one, with 40% over 65:** about −6%.
- **Without a pension:** the old keep working, and the same Japan-like structure gains +13%. The price is the
  dependents' income, old-age deaths (§2.4) and the politics.

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

### 8.1 Family & Reproductive Policy: laws set the frame, measures are buttons

**The split.** A law says what the state may do about families and how the interest groups see it. A **measure** is
what the government does within that law this decade: switched on and off from the Demographics tab, with a running
cost.

Measures are buttons rather than amendments for four reasons:
- a measure is a policy choice made within a law, not a new legal framework;
- the player can change course without an enactment;
- each measure carries its own cost and minimum term, visible in one place;
- the mod's rule that every amendment needs a scripted way in (petitions, debate events) isn't needed.

**How a measure works:**
- **Switching.** A scripted GUI button in the tab switches it on or off. The button is greyed, with the reason, when
  the law doesn't allow the measure or its minimum term hasn't run (style guide rule 6).
- **Cost.** An upkeep while it is on: money (`country_expenses_add`, scaled by population or by the share of children),
  authority or bureaucracy.
- **Minimum term.** Five years, since demographic policy works on a generation.
- **Ramp.** The effect builds over the first few years, through the drift the model already has.
- **Politics.** IG approval and radicals while it is on.
- **Wording.** Descriptions stay as open as the laws': what a measure aims at, not how hard it pushes.
- **AI.** A yearly country pulse chooses measures by weight (§11.2).
- **Leaving the law.** A measure the new law doesn't allow switches off, with a notice.

**The laws:**

| Law | Today | Proposal |
|---|---|---|
| Traditional Family Structure | nothing | Unchanged baseline. Allows Honours for Large Families |
| Pro-Natalist Subsidies → **Pro-Natalist Policy** (`law_pro_natalist_subsidies`, key kept) | birth +10%, welfare +10%, dependent wage −10%, working-adult −0.05 | Desired fertility up by about 5% from the law itself; the rest comes from its measures. Its description becomes: "Through propaganda, incentives, or even coercion, this policy encourages higher birthrates." **Drop the −0.05**, since the model now produces it. Fix the dependent wage to **+**, since family allowances raise dependents' income |
| State-Sponsored Family Planning | birth −5%, working-adult +0.05, education access +0.05 | The means +0.1. Keep the +0.05, which stands for women's work, not age |
| **Population Control Measures** (name and key kept; its description is already open: "from strict limits … to eugenics programs") | birth −10%, +150 authority, radicals and loyalists from SoL change ×2 | +150 authority; most IGs dislike it. Its force comes from its measures. **The payoff arrives through the model:** fewer dependents at once, a dividend in 15–20 years, crowding and food pressure relieved. **The cost arrives later:** rapid ageing (China's "4-2-1" families) and, with Birth Limit and prenatal sexing, a skewed sex ratio at birth. Stop the enactment events (.19, .55, .79) granting it a birth boost |
| Communal Child-Rearing | birth −20%, working-adult +0.1 (yet its Youth Center PM gives +20%) | Pick one direction. Proposal: the law leaves fertility alone and keeps women's work at +0.1; the PM drops to +10%. Allows Child Allowance and Parental Leave |

**The measures** (starting catalogue):

| Measure | Laws that allow it | Effect | Upkeep | Anchor |
|---|---|---|---|---|
| **Child Allowance** | Pro-Natalist, Communal | desired +5–10% | money × the share of children | France's allocations familiales (1932) |
| **Family Housing** | Pro-Natalist, Family Planning | cancels part of the urban and crowding terms | money × urban population | |
| **Honours for Large Families** | Traditional, Pro-Natalist | desired +3% | authority | the Soviet "Mother Heroine" (1944) |
| **Restricted Contraception** | Pro-Natalist | the means −0.2; maternal deaths up; women and liberals radicalise | authority | Romania's Decree 770 (1966): births nearly doubled within a year, then fell most of the way back |
| **Parental Leave** | Family Planning, Communal | desired +5%; women's work kept (+ working-adult) | money × women in work | the Nordic model |
| **Free Contraception** | Family Planning, Population Control | the means +0.1 | money | |
| **Sex Education** | Family Planning, Population Control | access as if literacy were 0.2 higher | bureaucracy | |
| **Later, Longer, Fewer** | Family Planning, Population Control | desired −10% | authority | China's campaign of 1971–79 halved fertility before the one-child policy |
| **Birth Limit** | Population Control | desired −30% (two children) or −45% (one); the sex ratio at birth rises once prenatal sexing exists; rural and traditional radicals | authority | China's one-child policy (1980) |
| **Rural Exemption** | Population Control, with Birth Limit | halves Birth Limit in farm states, by the agrarian share as in #822; less unrest | none | China's "1.5-child" rule (1984) |
| **Crash Campaign** | Population Control | a further cut, for five years at most; heavy unrest and a legitimacy blow. The wording leaves the methods to the player | authority | India's Emergency (1975–77), which cost the government the next election |

**Also:**
- **AI weights** for every law in the group. Today it has none.
- **Natalism Initiative** goes from +50% to about +15%. With the model it no longer needs to be large: a small push now
  shows up as a cohort later. A per-state measure like this one stays a decree.
- **Scope:** measures are national for now (owner, 2026-10-08). Decree versions for single states, such as a regional
  Birth Limit or Child Allowance, can come later.
- **Youth Centers** stay as they are: no measure or Population Control unlocks them.

### 8.2 Retirement

Like the measures, the pension age is a setting, not an amendment. Under Old Age Pension the tab offers three
positions, each with a five-year minimum term:

| Setting | Over-65s' participation | Effect |
|---|---|---|
| **Early Retirement** | 0.05 | frees jobs for the young and lowers the youth-bulge penalty, as Western Europe did in the 1970s and 80s; a larger bill |
| **Standard** | 0.15 | the default |
| **Raised Pension Age** | 0.3 | a smaller bill; trade unions and the old object |

Real anchors: about three-quarters of American men over 65 worked in 1880, and about a fifth do today. Without any
pension law, participation stays at 0.5: people work until they can't.

### 8.3 Other levers

| Lever | Through |
|---|---|
| Schools, literacy, education access | desired fertility, access to the means and child deaths (§2.3, §2.4) |
| Health laws and institutions, medical technology | each cause of death at its own ages (§2.4) |
| Workplace Safety, Ministry of Consumer Protection, policing | working-age and young adults' deaths; women's-rights laws decide how much of the work risk falls on women (§2.4) |
| Child-labour and schooling laws | the 10–14s' participation (§7). Vanilla's own effects (children's earnings in the dependent wage, the mortality cost) stay |
| Women's-rights laws | vanilla's birth and workforce modifiers, read through |
| Migration laws | how large the young-adult inflow is |
| Youth Centers | the birth PMs; Ectogenesis |
| Planned Capital, regional development, urban planning | the urban and settlement patterns (§5) |
| Taxes, land reform, inheritance, ownership laws | Wealth Concentration (§4.2) |
| **Biological Immortality** (era 12) | It stops biological ageing and can wind it back (§1, "Ages past 95"), so people stop becoming dependents and the dependency ratio collapses. With almost no deaths, every birth adds to the population. Crowding returns, and Population Control and its Birth Limit become the late game's essential policy, which gives the group an era-12 role |

### 8.4 Flat modifiers that move into the model

These stand in for an age, fertility or survival effect the model now produces. They come off when phase 2 lands, so
nothing is counted twice:
- the Pill's −10% birth (now a means tier);
- Pro-Natalist's −0.05 working-adult;
- the mod's own birth modifiers on its family-policy laws (now desired fertility, the means and measures);
- the Ministry of Consumer Protection's flat −1% mortality (now external causes);
- the mod's medical techs' flat mortality cuts (now the cause each one acts on).

Vanilla's modifiers stay as inputs, as do the mod's modifiers for women's and children's work.

The model's own law, technology and institution terms (its cause multipliers, means tiers and Wealth Concentration law
terms) become registered modifier types the census reads, so each shows on its law or technology: owner, 2026-10-09;
design in `2026-10-09-demographics-modifier-types-design.md`.

## 9. Events and milestones

Each fires when the model crosses a threshold, at most once a generation per country. Candidates for the first wave:

| Event | Trigger | Choice |
|---|---|---|
| **The Demographic Dividend** | the working share passes the reference by 10% | spend it on schools, factories or the treasury |
| **The Baby Boom** | a war of two or more years with mass mobilisation ends | births +15% for ten years, decaying; the cohort echoes |
| **The Lost Generation** | war dead exceed 5% of men aged 18–40 | memorials, women into industry, or pensions for widows |
| **The Greying of the Nation** | 65+ passes 20% | raise the pension age, cut benefits, raise contributions, or open the borders |
| **The Youth Bulge** | ages 20–29 above 20% and unemployment high | jobs, conscription or emigration |
| **Missing Girls** | the sex ratio at birth above 110 | ban prenatal sexing, pay families for daughters, or ignore it |
| **Bare Branches** | men aged 20–39 above 110 per 100 women | |
| **The Empty Villages** | a farm state that is old and shrinking | |
| **The Overspill** | a Metropolis-pattern state with crowding active | new towns, a green belt, or let it sprawl |
| **The Last Generation?** | Biological Immortality | |

## 10. The panel

**Country view: a "Demographics" tab in the vanilla Population panel** (`PopsOverviewPanel`, `gui/pops_overview.gui`,
2,820 lines). Adding a tab means the mod overrides that file in full, which adds one more vanilla file to the 3-way
merge on every patch (`gui_modding_guide.md`). Custom tab names already work (`InformationPanel.SelectTab`, proven by
the Banking tab). The tab is available whenever the rule is on; there is no journal entry to gate it. Style guide rules
apply.
- **The strip.** Vanilla has four tabs (Overview, Charts, Detailed List, National Cast), so Demographics is the fifth
  and last slot of `tab_buttons`, set with `fifth_button*` blockoverrides. At five slots "Demographics", "National
  Cast" and a selected "Detailed List" shrink towards the 12-point minimum; nothing is cut off.
- **Two quirks.** The sidebar's Population button cycles only the first three tabs, so it never lands on Demographics;
  links open it with `OpenPanelTab('pops_overview', '<tab>')`. The Pop Browser button in the footer shows under every
  tab.

- **Overview** (always shown): median age, children per woman, life expectancy, dependency ratio, sex balance, Gini,
  Wealth Concentration and urban pattern. Each reads "Label: value" with a trend arrow.
- **Pyramid** (open): five-year bars, men left and women right (§1's display split).
  - The men's bars grow leftwards through vanilla's "reverse hack" (`gui/shared/progressbars.gui`): a `progressbar`
    with `min = -N`, `max = 0`, swapped textures and the negated share. Vanilla has no mirrored progressbar.
  - Behind them is a translucent outline of the structure twenty years ahead. It is drawn by running the cohort model
    forward from current rates, country only, at the yearly pulse. It answers "is my workforce about to shrink?" at a
    glance.
  - Hovering children per woman shows its terms: wealth, education, child survival, urban life, means.
  - Hovering life expectancy shows the five causes.
  - From era 11, a toggle switches the pyramid between calendar and biological age (§1).
- **Family Policy** (open): the law in force, the measures as buttons (on, off or greyed, each with its upkeep and
  remaining term), and the pension-age setting under Old Age Pension.
- **Wealth** (open):
  - the Gini, beside the engine's average income per stratum;
  - the national Wealth Concentration as a bar, with its target as the translucent segment;
  - the target's terms as bars;
  - the most and least concentrated states.
- **Where people live** (open): urban share, primacy, the effective number of cities and the three largest cities
  from the city ranking. Then the states by settlement pattern.
- **States** (open): a row per state with population, median age, children per woman, sex balance, Gini and Wealth
  Concentration. No GUI sort takes a script value, so the yearly step stores the states as a variable list in the
  order wanted (`ordered_scope_state` by a script value), drawn with `GetList`, as the trade-partner lists do
  (`common/scripted_effects/trade_partner_effects.txt:147-182`); `gm_states` is unsorted.
- **History** (open): yearly samples of median age, fertility, life expectancy, Gini and Wealth Concentration in the
  history store's column charts.
- **How Demographics Works** (collapsed).

**State view: a fourth subtab, "Demographics", on the state panel's Population tab.** The three 170 px subtabs become
four of about 130. It shows the state's pyramid, its figures, net migration, Gini, Wealth Concentration and settlement
pattern.

**Map modes (blocked):** median age, fertility, life expectancy, Gini, Wealth Concentration and settlement pattern. The
only map-mode mechanism is the hijack of Migration Attraction (`te_map_mode_script_values.txt`), and it is switched off
because state-scope `migration_pull` returns the country's value (`common/decisions/extra_decisions.txt:96-108`). The
six wait for a working per-state source and belong to no phase until one exists.

## 11. Balance, AI, performance, rule and compatibility

### 11.1 Balance

- **The retune is the large change** (§2.3, §2.4). It moves every country's population path, so it needs the
  calibration harness (§12) before any in-game test. The harness is an offline Python copy of the engine's growth
  formula and the cohort model. It is driven by SoL, literacy, technology and law paths read from saves with
  `save_country_probe.py`, and tuned against the targets in §2.3.
- **In-game check:** an observer run to 2100, with population, fertility, life expectancy and ages read every 25 years
  and compared with the harness.
- **The workforce effect** stays inside ±0.08, about half of Women's Suffrage's +0.15.
- **Starting values** are each state's equilibrium, so 1836 is unchanged.
- **Measures** are tuned so a full pro-natalist package moves fertility by about 0.2–0.4 children, the real range.
  Coercive measures can do more, briefly, at a political price.

### 11.2 AI

- **Weights for Family & Reproductive Policy:**
  - Population Control when food security is poor, crowding high or a youth bulge present;
  - Pro-Natalist Policy when the 65+ share is high or the population is shrinking.
- **Measures:** a yearly country pulse switches them by the same conditions and the treasury.
- **Events:** the AI picks pension-reform options by its treasury.
- **No dependence on the AI.** Nothing in the model needs the AI to act. If it does nothing, it fails the same way a
  player who does nothing would.

### 11.3 Performance

One yearly state effect:
- **one pop walk**, for the Gini sums, literacy, the soldier share and the agrarian share. It replaces inheritance's
  agrarian-share walk, so the mod walks pops once a year per state, not twice;
- **one building walk**, for the ownership shares (§4.2);
- **arithmetic on the occupied cohort slots** (§1: about 20 or 100 before the late eras);
- **the GUI reads variables, never walks** (`scripting_best_practices.md`: GUI and loc re-evaluate every frame).

**No stagger is needed.** The engine already fires the yearly state pulse on a different day for each state (Britain's
26 states on 26 days from March to January), so the work is spread over the year. Measured in 1836 across all 887
states: the one-year cohort step 0.75–1.0 s in total, the pop walk and the building walk under 0.1 s each (§1).

### 11.4 Game rule

**Demographics: Full / Display only / Disabled.**

The retuned defines can't be switched by a game rule. Without the model's fertility and mortality terms, rich states
would keep about 3.5 children per woman and grow without limit. So **Disabled** still applies the fertility and
mortality terms, but against the *equilibrium* structure for the state's rates, taken from the same lookup that seeds
1836 (§2.6), not against tracked cohorts. Long-run population behaves as in Full, without the momentum. With Disabled
in place, **Display only** costs almost nothing: it runs the cohorts and the panel but applies Disabled's modifiers.

| Setting | Cohorts and panel | Births and deaths modifiers | Workforce, pension, youth and other effects; measures |
|---|---|---|---|
| Full | yes | from the cohorts | yes |
| Display only | yes | from the equilibrium | no |
| Disabled | no | from the equilibrium | no |

The rule's settings are `demographics_full` (Full, the default), `demographics_display_only` (Display only) and
`demographics_disabled` (Disabled). Write the checks as `NOT = { has_game_rule = demographics_disabled }`, so a save
from before the rule keeps the system (Grand Monuments' pattern).

### 11.5 Compatibility

- **The Demography mod** models ages too, so running both applies two sets of corrections. Document it and point
  players to the rule; no detection.
- **The Population panel** becomes a new full-file override. Any other mod that replaces it collides.
- **The state panel** already collides with Demography (`system_panels_feasibility.md` §7.4). A subtab adds nothing new.

## 12. Phases

| Phase | Contents | Gate |
|---|---|---|
| 0. Probes and harness | §14's remaining checks (most ran on 2026-10-08); the offline calibration harness (§11.1) with the retuned defines, the fertility terms and the five causes of death, first checked against the engine's monthly change world-wide (§14 Q10) | the harness meets §2.3's targets |
| 1. Census | the cohort model, Gini, per-state Wealth Concentration (its targets and shocks), the national urban pattern, both panels, history, the rule. Internal Resettlement's moves stay in the migration residual until phase 3. The model runs on today's defines and applies nothing yet | an observer run to 2100: the pyramids, fertility, life expectancy and Gini look right against the anchors |
| 2. Consequences | the model's law, technology and institution inputs as modifier types (`2026-10-09-demographics-modifier-types-design.md`, before the rest); the retuned defines with the births and deaths modifiers; workforce, pension and health bill, conscription, youth bulge; the Family & Reproductive Policy laws and measures; the pension-age setting; §8.4's removals; Wealth Concentration's effects split by scope (built, §4.2); AI weights | population paths within the harness's tolerance |
| 3. Place and colour | the settlement pattern (§5.2), the national urban pattern's effects and Planned Capital; sex-balance effects; the event wave; Ectogenesis and Immortality; Cultural Hegemony's fertility drift | |

Map modes (§10) wait for a per-state source, since the hijack is switched off, and belong to no phase until one works.

Phase 1 alone is a playable feature: a census the player reads. Each later phase adds effects to numbers already seen
to be sane.

## 13. Still open

- **Cohort width, at the cost as built:** the benchmark found one-year cohorts cheap (§1), so the rule gives one-year
  cohorts. The plan builds them with about 345 variables a state, about 26 MB of an 1836 plain-text save; the 11–15 MB
  counted the cohorts alone. For the owner to confirm at that figure.
- **The ownership coefficient (§4.2): settled 2026-10-09.** 40 × (the private share of capital levels − 0.65),
  capped ±20. #833's centre of 0.9 assumed almost all 1836 capital was private; read from an 1836 save, large
  countries' capital is 55–65% private (self-owned farms, mines and workshops), so 0.9 held almost every country 10–17
  points down all game (72 of 285 countries at the −20 cap in 1836; −11 to −20 in a 2062 observer save). The owner
  re-centred it on the measured share and added the economic-laws term. A state-owned Construction Sector counts as
  state capital (the mod's `bg_construction` is not government-funded); left as it is (owner).
- **The ring to about age 150:** cheap. Filling the top 50 of 150 slots added about 0.25 s a world-year, and an empty
  slot costs one variable check.
- **The pensions' money cost (§7).** Vanilla's Old Age Pension charges the treasury nothing for the old (§14 Q6).
  Proposal: an expense modifier (`country_expenses_add`) refreshed yearly with a multiplier from the national 65+
  population, the mod's "Expense Scaling with GDP" pattern (`scripting_best_practices.md`), sized in the harness. The
  owner decides whether ageing costs money as well as bureaucracy.
- **Fertility without ageing (§1, "Ages past 95").** Fertility reads biological age, and Immortality holds it near 35,
  so an immortal woman takes the age-35 rate every year for good and her lifetime births have no limit (the owner's
  question, 2026-10-09). A cap per woman, or a term that falls as a cohort's children reach the family size it
  wants, would bound it. Phase 3's to design.

## 14. Engine checks (run 2026-10-08)

A probe answered these in a fresh 1836 game as Britain. The evidence is in
`docs/testing/demographics-probe-results-2026-10-08.md`; the probe itself is on the local branch `probe/demographics`.
The sections above already use the answers.

1. **One walk, several sums: yes.** Local variables, the state's variables through `PREV`, and named pop-scope script
   values read as `PREV.<value>` all match separate walks. The same holds for a building walk.
2. **Ownership reads: yes, as values,** weighted by levels. The ownership buildings read self-owned, Subsistence Farms
   private and government buildings state-owned, so the walk filters them (§4.2).
3. **`wealth_share`: no.** It has no value form, and it measures political strength, not wealth (§4.1).
4. **War dead:**
   - `"num_country_dead(<country>)"` reads as a value in war scope, as do `num_country_wounded`,
     `num_country_casualties` and `num_dead`;
   - the counters printed 0 at `on_war_end` (unconfirmed: that line had no control value), so they are snapshotted
     monthly (§2.5);
   - **still open:** whether battle dead come out of the soldiers' home-state pops. A comparison of two saves around a
     battle settles it.
5. **State modifier reads include the country's: yes** (§2.3).
6. **Who pays pensions in money: nobody, for the old** (from the game files). Old Age Pension's welfare payments are a
   treasury expense, but they go to workforce pops paid below a fraction of the normal wage
   (`concept_welfare_payments_desc`). Its +20% dependents income per level has no payer and no budget line. So §7 needs
   its own money cost (§13).
7. **Births floor:** births ran at about a tenth at −0.9 and stopped at −3; they never go negative. The point between
   where they reach zero wasn't measured (§2.3).
8. **GUI** (from the game files):
   - the panel is `gui/pops_overview.gui`, with four tabs; Demographics fits as the fifth (§10);
   - scripted GUI buttons already work in vanilla panels outside the journal (the system tabs);
   - no GUI sort takes a script value, so the states are ordered in script (§10);
   - left-growing bars come from vanilla's reverse hack, not a mirror property (§10).
9. **Cost: cheap.** One-year cohorts take about 1 s per world-year in 1836, five-year about 0.1 s. The engine spreads
   the yearly state pulse over the year, and each variable takes 60–85 bytes of a plain-text save (§1, §11.3). **Still
   open:** a re-run in a late-game save.
10. **New, still open: does the engine's monthly change follow the SoL curves world-wide?** The probe's own check
    failed: script-value literals allow at most five decimal places, and longer ones read as 0. Qing's births are
    consistent with the curve. The harness checks the rest before anything is tuned (§12).
11. **New, still open: `WORKING_ADULT_RATIO_SKEW_MAXIMUM`.** The mod sets it to 1,000,000 (vanilla 2.0). A save
    comparison of a pop's workforce share before and after a ratio modifier changes shows how fast §7's workforce effect
    takes hold.
