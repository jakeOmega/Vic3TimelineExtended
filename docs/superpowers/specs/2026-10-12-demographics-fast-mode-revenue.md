# Demographics fast mode and AI revenue: should fast mode pay the AI's bills? (design note)

> **Status: decided (owner, 2026-10-12): the recommendation (§5) as written.** No revenue boost; the power-plant
> subsidy burden is pursued as a normal-game balance issue; institutions at K× only after a measurement. No code.
> Originally a design note for the owner's decision. It answers the owner's idea of 2026-10-10:
> fast mode grows population K times as fast, which seemed to outrun the AI's economy (in #894's 4× run, 64% of
> people were in bankrupt countries by 1904), so give fast mode a country-revenue boost, and possibly faster
> bureaucracy or institutions, so that a fast run approximates a normal game. Fast mode is the console test tool in
> `docs/systems/mod_systems.md` § Demographics, "Fast mode" (`event te_debug_demog.1` options h, i and j;
> `common/scripted_effects/te_demog_fast_effects.txt`). Nothing in normal play starts it.

## 1. The question

Fast mode runs births and deaths, research, technology spread and construction at K× (4, 6 or 12). Births and deaths
come from the state modifiers `te_demog_fast_births`/`_deaths`. Research, spread and construction come from the
country modifier `te_demog_fast_speed` (`country_tech_research_speed_mult`, `country_tech_spread_mult`,
`state_construction_mult`, each +1, applied with multiplier K − 1 by `te_demog_fast_refresh_speed`). Wars,
diplomacy, laws, literacy and pop wealth keep the calendar's pace.

The owner's reading: four times the people on a calendar-paced economy leaves the AI unable to pay its way, and its
bankruptcies cut the institutions the census reads (in that run Britain's census life expectancy fell 8 years in one
step after it cut its health institution from level 4 to 1). The proposed cure is more revenue for every country while
fast mode runs.

Fast mode was never meant to be a normal game. The first fast run (12×,
`docs/testing/demographics-fast-run-2026-10-09.md`) reached census year 2124 as an 1860 society with every medical
technology to era 8, fertility still near 5. The aim here is narrower: that the AI's finances, and the institutions the
census reads through them, don't fail in a fast run for a reason a normal game doesn't share. Before choosing a cure,
this note checks the reading against the saves.

## 2. What the saves show

### The runs

| Run | Build | Speed | Saves read |
|---|---|---|---|
| Normal | main at ec304526 (phase 2's normal-speed Full run, `docs/testing/demographics-phase2-engine-rates-2026-10-10.md`) | 1× | `/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/`, 1840–1902 |
| Fast A | main at about 85a23d47 (#894's overnight 4× run, 2026-10-10) | 4× from day 1 | `/mnt/d/vic3te-data/vic3te-demog-fast4x-2026-10-10/`, 1840–1912 |
| Fast B | #869 at f19ee434 (phase 2's fast-mode gate run) | 4× from day 1 | `/mnt/d/vic3te-data/vic3te-demog-p2-gate-full-2026-10-11/`, 1840–1882 (it crashed in 1882) |

The builds differ, so small gaps between runs mean little. At 4×, calendar 1880 is about census year 2010 and calendar
1904 about census 2110.

### Bankruptcy by calendar year

"Bankrupt" is a country carrying vanilla's 10-year `declared_bankruptcy` timed modifier. "In debt" is a country whose
budget has `principal` above 0. Shares are of people in countries with people. SoL is the world's, weighted by people.

| Year | Normal: bankrupt (countries) / in debt / SoL / people | Fast A | Fast B |
|---|---|---|---|
| 1840 | 1% (27) / 58% / 7.85 / 1,062M | 0% (23) / 31% / 7.62 / 1,158M | 0% (20) / 50% / 7.78 / 1,181M |
| 1850 | 3% (56) / 56% / 7.64 / 1,178M | 1% (40) / 48% / 7.17 / 1,461M | 4% (45) / 84% / 6.94 / 1,557M |
| 1860 | 3% (55) / 56% / 7.22 / 1,292M | 2% (43) / 48% / 7.54 / 1,767M | 3% (60) / 51% / 7.61 / 1,887M |
| 1870 | 19% (57) / 43% / 7.86 / 1,410M | 2% (40) / 53% / 8.51 / 2,089M | 4% (55) / 40% / 7.97 / 2,270M |
| 1880 | 4% (48) / 53% / 8.00 / 1,530M | 1% (67) / 68% / 10.15 / 2,639M | 4% (80) / 64% / 9.66 / 2,894M |
| 1890 | 5% (52) / 57% / 7.95 / 1,678M | 6% (97) / 92% / 11.74 / 4,312M | – |
| 1900–02 | 8% (55) / 62% / 7.68 / 1,833M | 40% (118) / 95% / 11.08 / 5,492M (1900) | – |
| 1904 | – | **64% (129 of 243)** / 97% / 11.90 / 5,788M | – |
| 1912 | – | 78% (148) / 97% / 11.68 / 6,931M | – |

Fast A's 1904 row reproduces #894's figure exactly (129 of 243 countries, 64% of people).

**Through calendar 1880, neither fast run has a larger share of people in bankrupt countries than the normal run**
(Fast B's 4% in 1850 against 3% aside), although they hold 1.7 to 1.9 times its people. More of their people are in
debt by 1880 (64–68% against 53%). **Fast A's collapse comes between 1890 and 1904.**

### Who is richer

| Weekly, £ per million people | Normal 1880 | Normal 1902 | Fast A 1870 | Fast A 1880 | Fast A 1890 | Fast A 1904 |
|---|---|---|---|---|---|---|
| Income | 2,847 | 4,039 | 5,290 | 8,095 | 16,222 | 21,672 |
| Expenses | 3,228 | 4,390 | 5,358 | 8,989 | 21,090 | 34,987 |
| Subsidies | 176 | 121 | 384 | 1,082 | 3,080 | 9,355 |
| Interest | 198 | 303 | 194 | 344 | 2,115 | 6,098 |
| Government wages and goods | 1,031 | 1,305 | 1,338 | 2,080 | 2,517 | 4,060 |
| Military wages and goods | 423 | 695 | 705 | 1,418 | 2,109 | 2,396 |
| Construction, net of the investment pool's share | 348 | 305 | 429 | 699 | 709 | 148 |
| **Subsidies as a share of income** | 6% | 3% | 7% | 13% | 19% | **43%** |
| Technologies: leader / median country | 100 / 54 | 121 / 72 | 177 / 132 | 219 / 206 | 249 / 248 | 285 / 284 |

- **Per head, the fast world earns more, not less:** about three times the normal run's income in 1880 and five times
  by 1902–04, and a higher standard of living (10–12 against 7.6–8.0) from 1870 on.
- **What grows is subsidies, then interest.** In Fast A's 1904 bankrupt countries (129 countries, 3.7 billion people)
  subsidies take 55% of income and interest 42%. Government and military wages and goods take a smaller share of
  income than in the normal run (30% in Fast A's 1904, 50% in the normal run's 1902). Net construction is at most
  about a tenth of income, since the investment pool pays most of it.
- **Power plants carry the subsidy bill.** Share of the world's subsidies by building:

  | Save | Subsidies a week | Power plants | Railways | Ports |
  |---|---|---|---|---|
  | Normal 1902 | £0.23M | 0% | 16% | 83% |
  | Fast A 1880 | £2.9M | 16% | 56% | 27% |
  | Fast A 1890 | £13.3M | 50% | 25% | 24% |
  | Fast A 1904 | £59.5M | 77% | 13% | 9% |

- **Every country is at the frontier.** At K× spread the median country holds every technology but one of the
  leader's by 1890. In the normal run it holds about 60% of the leader's count in 1902.

### The normal game reaches the same state later

The 2026-10-06 study of the AI-only observer run (normal speed, an earlier build; it isn't written up in the repo)
found `declared_bankruptcy` on 109 of 230 countries in 1990, 116 of 190 in 2015 and 126 of 179 in 2029. The owner's
reading of run 1's AI budgets in 2015 was 25–50% subsidies, mostly ports. Fast A's 1904 count is 129 of 243.
Run 2's technology leaders held 245 techs in 2015; Fast A's median country held 248 in 1890. The two builds are four
days apart and the mod adds techs often, so the counts match only roughly.

### Where the premise holds

In the mid-century the fast world's people are poorer than the normal run's. Its SoL sits below the normal run's in
1840 and 1850 (1850: 7.17 and 6.94 against 7.64), and phase 2's gate run found mild starvation on 18% of people in
calendar 1857 against 8% at normal speed: "in fast mode the people outgrow the farms"
(`demographics-phase2-engine-rates-2026-10-10.md`). By 1860–1870 the fast runs' SoL is above the normal run's, as K×
construction and research catch up with K× people. Through all of that the government budgets show no strain: the
bankrupt shares stay at or about the normal run's. So population does outrun the economy for a time, but the pops feel
it, not the treasuries, and a revenue boost wouldn't reach them.

### What this says

The fast run's bankruptcies don't come from population outrunning revenue. They come from the mod's late-game AI
insolvency, which a normal game reaches between 1990 and 2030, at calendar 1890–1904. Two of fast mode's speed-ups cause
that. Research at K× brings the late-game buildings, and the late-game subsidy bill that power plants carry, K times
sooner. Spread at K× brings them to every country at once instead of to the leaders first. Once a country is in debt,
interest compounds the deficit.

Two measurement notes. The normal run's 1870 row (19% of people) is a spike: the count of bankrupt countries didn't
move. The observer study counted countries, not people, so it isn't directly comparable with the people-weighted
rows above.

### The institution lead

#894's run also showed the census's health access at a median 0.95 × level × value in the 1901 save, many countries
exactly 0.95 or 1.00. That was put down to vanilla's `DAILY_INSTITUTION_SIZE_CHANGE` (0.0028 a day, which the mod's
tax-obligation code reads as about a level a year), lagging under fast mode. Phase 2 has since found the Impact of
Institutions (`state_institution_impact_add`: Local Vernacular −0.05, Devolution −0.05, obstinance) scaling every
institution line, and the census applies it from #889. Exactly 0.95 is Local Vernacular's figure, so the lag isn't
established. But the mechanism is real: a level takes about a calendar year to grow, which at 4× is four census years,
while the research that unlocks the level runs at census pace.

## 3. Options

Each option would sit beside `te_demog_fast_speed`: one refresh site (`te_demog_fast_refresh_speed`, which runs for
every country at each switch and a day after each clock step), removed at normal speed (option k). Modifier names are
from `~/src/vic3-engine-docs/1.14.5/docs/modifiers.log`. The modifier's multiplier is K − 1 today, so a field that should
scale linearly in K − 1 can go into `te_demog_fast_speed` itself. Anything else needs its own modifier and script
value.

### Option 1: K-scaled taxes

- **What:** `state_tax_collection_mult` ("the final amount of all Taxes collected from Pops") +1 in
  `te_demog_fast_speed`, so taxes run at K×. A smaller share is a variant.
- **Risks:**
  - It pays every country K× from day 1, when the saves show no need: through 1880 the fast runs are as solvent as the
    normal one. The AI spends what it has, on construction, institutions and armies, so the fast world would come out
    richer still, with more power plants to subsidize later.
  - If the engine takes the extra from pops, their wealth and standard of living fall, and the census reads both. That
    would distort the thing fast mode exists to measure. This needs an engine check (E1).
  - It doesn't touch the cause: subsidies grow with the buildings, not with the taxes.
- **Rejected variants:** the flat adds `country_tax_income_add`, `country_minting_add` and `country_expenses_add`, which
  don't scale with a country's size; `country_government_wages_mult` and `country_military_wages_mult`, which move pops'
  incomes.

### Option 2: a grant that closes part of the deficit

- **What:** in the country's clock-step census (`te_demog_country_clock_census`), while K > 1, `add_treasury` of a share
  of the country's deficit over the window, from the script values `net_total_income`, `total_income` and
  `total_expenses` (all in `triggers.log`; their units need a check, E2). A cap keeps it from covering everything.
- **For:** it leaves pops' taxes, wealth and SoL alone; it does nothing for a solvent country, so the early fast game is
  untouched; it scales with the problem.
- **Risks:**
  - A grant that closes the deficit removes the AI's budget constraint, which is the opposite distortion: an AI that
    never has to cut keeps institutions a normal game's AI would drop. A share under 1 limits that, and the share is a
    guess.
  - It hides the late-game insolvency in fast runs while normal games keep it, so the fast run diverges from what it
    approximates.
  - A modifier version (`country_expenses_add` below 0, with a per-country multiplier) would feed back on itself, since
    the modifier is part of `total_expenses`. `add_treasury` doesn't.

### Option 3: put the late game back on the calendar

- **What:** drop `country_tech_spread_mult` from `te_demog_fast_speed`, or run research below K×.
- **For:** it targets the cause: every country reaching the subsidy-heavy buildings at once.
- **Risks:** fast mode runs research at K× so that medicine, contraception and the health laws arrive on the census's
  clock. Without spread at K×, followers' techs fall K times further behind their census years, and the census's
  medicine and means for most of the world's people would lag. That changes what a fast run measures.

### Option 4: institutions at K× (separate, small)

- **What:** `country_institution_size_change_speed_mult` ("how fast you change the size of an institution") +1 in
  `te_demog_fast_speed`, so an institution grows (and shrinks) a level in about a census year, as research does.
- **For:** it's linear in K − 1, so it's one line. It puts the institutions the census reads (health access) on the
  census's clock.
- **Risks:** an AI that cuts an institution loses it K times as fast. That matches census time but deepens a bankrupt
  country's drop. Whether the lag matters at all is unmeasured (§2, the institution lead). Check E3 first: whether the
  modifier scales the daily change both ways.

### Not proposed

- **Bureaucracy** (`country_bureaucracy_mult`, `state_bureaucracy_population_base_cost_factor_mult`): government wages
  and goods take 32% of income in the normal run's 1902 and 16–26% in Fast A's saves from 1880. They aren't what
  bankrupts the fast world.
- **Construction cost** (`country_construction_goods_cost_mult`): net of the investment pool's share, the
  government's construction is at most about a tenth of income and smallest in 1904.

### Engine checks before building any option

- **E1:** does `state_tax_collection_mult` raise what pops pay, or only what the government receives? Apply it to one
  state from the console and compare a pop's taxes and the state's tax line.
- **E2:** what unit `net_total_income` reads in (weekly or the budget's monthly figure), and whether it counts the
  investment pool's construction share.
- **E3:** whether `country_institution_size_change_speed_mult` scales both growth and decline.

## 4. How to judge a change in a fast run

- **The run:** as before, a new 1836 game at 4× from day 1, observed, census log on, plain-text yearly autosaves, to
  about calendar 1905 (census about 2110).
- **The baseline has two halves.** For calendar 1840–1880, the normal run at the same calendar years (the table
  above). For the late period, a normal game at the same technology level, since that is where the late-game
  buildings and their subsidy bill sit. That needs a people-weighted measure from a plain-text save of a normal game
  around 1990–2030. The observer study's saves were binary and counted countries.
- **Measures, from each save's `country_manager` records:**
  - the share of people in countries carrying `declared_bankruptcy`;
  - the share in debt (`budget.principal` > 0) and at or past the limit (`principal` ≥ `credit`);
  - subsidies and interest as shares of income, from `budget.weekly_expenses` and `weekly_income`;
  - world SoL by people;
  - on the census side, life expectancy in countries that cut a health institution.
- **The budget slots.** Each record's named breakdown (`country_building_budget.expenses`) matched them on every
  country of the normal 1902 save:

  | `weekly_expenses` slot | Category |
  |---|---|
  | 1 | Government slaves |
  | 2 | Government goods |
  | 3 | Government wages |
  | 4 | Military slaves |
  | 5 | Military goods |
  | 6 | Military wages |
  | 7 | Construction goods |
  | 8 | Subsidies |
  | 9 | Subventions |
  | 14 | Government share losses |

  Two slots were identified another way. Slot 10 is interest: non-zero only in debtors, and in nearly all of them.
  Slot 11 is diplomatic pacts: it equals the record's `diplomacy_expenses` in Britain's. `weekly_income` slot 7 is the
  investment pool's share of construction: it equals −`weekly_investment_pool_change_from_construction` in every
  country.
- **Bars:**
  - Calendar 1840–1880: within a few points of the normal run, as now.
  - The late period: the bankrupt share of people within about 10 points of the normal game's at the same technology
    level.
  - SoL: no higher than the unchanged fast run's.
- **Follow-up either way:** fold these reads into `demographics_observer_report.py` (a `--budget` report over saves)
  rather than leaving them in scratch scripts.

## 5. Recommendation

**Don't add a revenue boost to fast mode now.** This reverses the boost the owner approved in principle on 2026-10-10,
so the premise's true part comes first: in the mid-century the fast world's people are poorer and hungrier than the
normal run's (§2, "Where the premise holds"). But that strain is on the pops, not the treasuries. The governments'
bankrupt shares stay at or about the normal run's through 1880, and per head the fast world's governments earn more. The
bankruptcies come later, from the mod's late-game AI insolvency: power-plant subsidies, then interest. It arrives early
because research runs at K×, and everywhere at once because spread does. A normal game reaches the same state between
1990 and 2030. A boost would hide in fast runs a problem that normal games keep, so fast runs would approximate normal
games less, not more.

Instead:

1. **Treat the power-plant subsidy bill as the normal game's problem,** the open cause behind the 2026-10-06 insolvency
   study. A fast run is the quickest test bed for it: by calendar 1890 power plants carry half the world's subsidies.
2. **Judge fast runs against a normal game at the same technology level** for anything past about census 2000 (§4),
   and measure that baseline people-weighted from a plain-text save.
3. **Option 4 (institutions at K×) only if a measurement shows the lag.** It's cheap, and it is the one fast-mode
   distortion here that a normal game doesn't share. Compare the census's stored health access with level × value ×
   impact in a fast save first.

If the owner wants fast runs shielded anyway (to study late-game demography before the subsidy problem is fixed),
**Option 2 with a capped share** is the one to build, not Option 1, because it leaves pops' taxes and standard of
living alone and does nothing for solvent countries. Its share, its cap and E2 are then the owner's calls.

## 6. Owner calls

1. Accept the reading in §2 (late-game insolvency on the tech clock; the mid-century strain falls on pops, which a
   revenue boost wouldn't reach), or ask for the people-weighted normal-speed baseline first. Either way, the boost
   approved in principle on 2026-10-10 waits.
2. Whether to pursue the power-plant subsidy burden as a normal-game balance issue.
3. Option 4: measure the institution lag, then decide.
4. If fast runs should be shielded regardless: Option 2, with its share and cap.

**Decided (owner, 2026-10-12): the recommendation.** (1) The reading stands and the boost approved in principle on
2026-10-10 is dropped. (2) The power-plant subsidy burden is pursued as a normal-game balance issue. (3) Institutions at
K× wait for a measurement of the lag. (4) Fast runs are not shielded.
