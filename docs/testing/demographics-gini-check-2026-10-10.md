# Demographics: the census's Gini against the game's own (2026-10-10)

An offline check of the census's income Gini (spec §4.1) against each pop as its own group. It led to the Gini by
wealth band with no map (plan `docs/superpowers/plans/2026-10-10-demographics-gini-wealth-bands.md`).
- **Data:** 14 plain-text saves, run against main 526e370f. The full report, CSVs and scripts are archived at
  `/mnt/d/vic3te-data/gini-check-2026-10-10/` (`report.md`, `country_rows.csv`, `state_rows.csv`, `census_check.csv`).

## The question

Pop income can't be read in script, so the census uses a stand-in: spending per head at the pop's wealth, from the
buy packages, capped at wealth 60 (`te_demog_pop_income`). The owner confirmed the stand-in tracks the engine. In
Britain 1836 aristocrats (wealth 47) earn about 139× laborers (wealth 4) a head in the engine; the stand-in gives 115×.

Before this change the census grouped pops into the three strata, each treated as equal inside, and showed
0.30 + 0.85 × that Gini. Only the 0.85 was measured: it made Britain 1836 read 0.52, a historical estimate. The 0.30 was
chosen as the low end of real-world Ginis. The owner's ruling is that the figure should measure the game, not history.

## Data and method

- **Saves.** The date of each is the `game_date=` line in `meta_data`.
  - An 1836 game (1836.2.1).
  - The gate run's six (1837–1887, one a decade).
  - Five from the fast run (1841–1860). Their populations balloon (Britain 157M by 1860), so they are left out of
    every headline figure.
  - Three from the owner's late game (1949–1953).
- **The reference** is each pop as a group of `workforce + dependents` people at the stand-in income for its wealth.
  The stand-in depends only on wealth, so this equals the Gini over integer wealth levels.
- **The mirror of the census** matches the game. Against the gate run's logged figures the difference is +0.0004
  on average and 96% within 0.02. Against the saves' own variables, states and countries are within 0.002 on average.
  The country figure sums its states' three strata into three national groups and then takes one Gini.

## Findings

| | Shown (old map) | Pop by pop | 14 wealth bands, no map |
|---|---|---|---|
| Britain 1836 | 0.52 | 0.36 | 0.35 |
| Britain 1877 | 0.776 | 0.659 | 0.65 |
| Countries ≥ 1M, mean gap to pop by pop | +0.19 (99% of country-saves above) | | −0.014 (R² 0.98, worst 0.045) |
| States ≥ 100k, mean gap | +0.21 | | −0.008 (R² 0.99) |

- **The old map read high almost everywhere.** The gap was +0.22 in 1836–1860, +0.18 in 1867–1887 and +0.16 in
  1949–1953, almost all of it the 0.30 floor.
- **A refitted line over the strata is loose.** Pop by pop ≈ 0.064 + 1.100 × the strata Gini (R² 0.81). The spread
  inside the lower stratum varies on its own: Japan 1949 had a strata Gini of 0.136 against 0.468 pop by pop.
- **Wealth bands track it.** The 14 bands are the stand-in's knots (1 or less, 2–5, …, 56–60, 61 or more). Income rises
  with wealth, so the bands are already in income order and need no sort. Pop types come next (−0.04 as they are), but
  need sorting.

## The game's Gini by band

| | 1836 | 1887 | 1950 |
|---|---|---|---|
| Median state, by people | 0.16 | 0.24 | 0.28 |
| Countries | Britain 0.35, France 0.19, USA 0.27, China 0.14 | Britain 0.63, Belgium 0.54, France 0.30 | USA 0.58, France 0.55, Japan 0.48, Russia 0.40, China 0.34 |

The most unequal 1% of state-saves reach 0.72–0.79. These figures set Wealth Concentration's inequality term, which the
owner chose on 2026-10-10: +30 × (Gini − 0.15), at most +15. The centre is 1836's median state, and the cap is reached
at 0.65, Britain's industrial peak in these runs.

## Other findings

- **Pops carry `weekly_budget`**, a 13-slot signed weekly money flow. Its positive slots 0–5 sum to an income; the slot
  meanings are inferred, not confirmed. Its pop-by-pop Gini is within 0.02–0.06 of the stand-in's, so a later check could
  use real income.

## Caveats

- Pop by pop is a lower bound: each pop counts as equal inside.
- 1836–1887 is one game and 1949–1953 another, so the fits describe this data, not every game.
- In the late game only two countries and 27 states carry census variables (demographics arrived mid-game), so it
  couldn't be checked against the game's own values there.
