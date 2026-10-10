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

| | 1836–1837 | 1887 | 1953 |
|---|---|---|---|
| Median state, by people | 0.15–0.16 (the 1836 save 0.147, the 1837 save 0.155) | 0.24 | 0.28 |
| Countries | Britain 0.35, France 0.19, USA 0.27, China 0.14 (1836) | Britain 0.63, Belgium 0.54, France 0.30 | USA 0.58, France 0.55, Japan 0.48, Russia 0.40, China 0.34 (the 1949 save: USA 0.55, Japan 0.46, China 0.27) |

Weighted by people, the most unequal 1% of state-saves reach 0.72–0.79; unweighted, the 99th percentile is 0.61–0.63. These figures set Wealth Concentration's inequality term, which the
owner chose on 2026-10-10: +30 × (Gini − 0.15), at most +15. The centre is 1836's median state, and the cap is reached
at 0.65, Britain's industrial peak in these runs.

## The shown figure (owner, 2026-10-10)

The computed figure is the game's own distribution, but a pop counts everyone in it as earning alike, so it sees only
part of the spread historians' estimates hold. The panel shows **1 − X × (1 − the computed Gini)**: the equality the
census sees, scaled down; total inequality stays at 1. X is fitted to the income Ginis of van Zanden et al. (2014,
"The Changing Shape of Global Inequality 1820–2000"; published by Clio Infra,
https://clio-infra.eu/data/IncomeInequality_Compact.xlsx, DataverseNL doi:10.34894/H4HNSX), 1820 and 1850
interpolated to 1836, against the 1836 save's band Gini for 23 countries (tags matched through the base game's loc):

| Weighting | X | Root-mean-square miss |
|---|---|---|
| Each country equally | 0.685 | 0.069 |
| By people | 0.711 | 0.047 |
| The 1837 save instead | 0.677 / 0.713 | 0.070 / 0.055 |

X = 0.7. Wealth Concentration's term reads the shown figure: +40 × (shown − 0.40), the same line as
28 × (computed − 0.143).

| 1836 | Computed | Shown | Estimate |
|---|---|---|---|
| Britain | 0.35 | 0.55 | 0.51 (0.59 in 1820, 0.44 in 1850) |
| France | 0.19 | 0.43 | 0.57 |
| USA | 0.27 | 0.49 | 0.50 |
| China | 0.14 | 0.40 | 0.38 |
| India (East India Company) | 0.16 | 0.41 | 0.36 |
| Netherlands | 0.43 | 0.60 | 0.52 |

- **The estimates are noisy.** Britain's fall from 0.59 to 0.44 between 1820 and 1850, and the US's from 0.57 to 0.44,
  are larger than any year-to-year change the game makes.
- **One X leaves single countries off by up to about 0.15.** France reads too equal, Brazil and the Netherlands too
  unequal: the game's 1836 countries are more alike than history's.
- **After 1836 the game diverges from history.** Its industrial Ginis climb faster: Britain computes to 0.65 by
  1877 (shown 0.76) against an estimate of 0.49 for 1870, and France shows 0.69 by 1953. That is a question for the
  economy's balance, not the measure.

## Other findings

- **Pops carry `weekly_budget`**, a 13-slot signed weekly money flow. Its positive slots 0–5 sum to an income; the slot
  meanings are inferred, not confirmed. Its pop-by-pop Gini is within 0.02–0.06 of the stand-in's, so a later check could
  use real income.

## Caveats

- Pop by pop is a lower bound: each pop counts as equal inside.
- 1836–1887 is one game and 1949–1953 another, so the fits describe this data, not every game.
- In the late game only two countries and 27 states carry census variables (demographics arrived mid-game), so it
  couldn't be checked against the game's own values there.

## High wealth (later on 2026-10-10)

The first wealth-band build held the stand-in flat from wealth 60 and put everyone above it in one band, 61 or more.
The mod's packages keep growing to the top level, 200 (`NUM_WEALTH_LEVELS`): 946 a head at 60, 9,009 at 80, 99,648 at
99, 9.5×10^8 at 200, 1.4–1.9× every five levels. A few rich pops then hold much of a country's income, and a game
whose people mostly sit above 60 reads the 0.30 floor. The build now has 41 bands, five levels wide to 195 and then 196
or more, with the stand-in uncapped (`GINI_TOP_WEALTH`, `GINI_INCOME_KNOTS` in `demographics_params.py`).

- **Data.** The 1836 save, the gate run's 1887, the late game's 1953 (mean wealth 12.5, maximum 84) and a fast-mode
  save with technology far ahead (1912.1.1, `vic3te-demog-fast4x-2026-10-10`, maximum 109). No save has most people
  above 50, so synthetic ones move every pop's wealth: up by 40, 45, 70 or 72 levels (spread kept in levels), or
  stretched 1.5× around the mean and moved to mean 50 or 80 (each level's people spread over the stretched levels).
- **The reference** is each pop as its own group at the packages' own spending at its level, uncapped (the harness's
  `income_proxy`). The census's straight lines between knots stay within 0.007 of it. Countries of 1M people or more,
  shown figures (the computed gap × 0.7):

| Distribution | Mean wealth | Before: mean gap, worst | After: mean gap, worst | Named countries, shown before → after (pop by pop) |
|---|---|---|---|---|
| 1836 | 8.1 | −0.011, −0.032 | −0.011, −0.032 | Britain 0.543 → 0.543 (0.553) |
| 1887 | 7.8 | −0.011, −0.027 | −0.010, −0.026 | Britain 0.739 → 0.739 (0.743) |
| 1953 | 12.5 | −0.016, −0.102 | −0.008, −0.025 | USA 0.708 → 0.718 (0.723); Colombia 0.711 → 0.802 (0.807) |
| Fast run, 1912 | 12.6 | −0.047, −0.230 | −0.004, −0.022 | UNA 0.660 → 0.794 (0.797); Germany 0.652 → 0.766 (0.769) |
| 1953 +40 levels | 52.5 | −0.138, −0.367 | −0.009, −0.027 | USA 0.465 → 0.758 (0.763) |
| 1953 +70 levels | 82.5 | −0.281, −0.538 | −0.011, −0.029 | USA 0.300 → 0.772 (0.779); China 0.300 → 0.599 (0.605) |
| Fast run +40 | 52.6 | −0.209, −0.498 | −0.005, −0.024 | UNA 0.470 → 0.835 (0.839) |
| Fast run +70 | 82.6 | −0.389, −0.580 | −0.007, −0.027 | Germany 0.300 → 0.783 (0.791) |
| 1953 stretched, mean 50 | 50.0 | −0.297, −0.483 | −0.006, −0.027 | |
| 1953 stretched, mean 80 | 80.0 | −0.476, −0.679 | −0.007, −0.027 | |
| 1836 +72 levels | 80.1 | −0.182, −0.375 | −0.012, −0.033 | |

- **The 1836 check holds.** Over the 1836, gate-run and late saves (812 country-saves), computed figure against pop by
  pop: before, both capped, mean −0.016, worst −0.046, R² 0.970; after, both uncapped, −0.016, −0.046, 0.973 (this
  rerun uses the packages' own spending for the reference and has one late save fewer, so it reads −0.016 where the
  table above has −0.014). The 1836 save's figures don't move, so `GINI_SHOWN_EQUALITY` stays 0.7.
- **States** of 100,000 people or more: after, mean −0.002 to −0.010 and worst −0.02 to −0.06 in every case; before,
  worst −0.17 in 1953 and −0.37 in the fast run.
- **Wider bands at the top** (ten levels above 100: 31 bands) do as well while their income still follows five-level
  pieces, but in the leaf a band's income is one line, and a ten-level line overshoots the packages by up to 17%.
- **Fixed point.** Income is summed in units of 100,000: a pop adds people ÷ 100,000 × spending per head, the division
  first (exact for whole people). A country of 4×10^9 people all at wealth 200 sums to 3.8×10^13 units, half the
  ceiling of about 9.2×10^13 (the generator asserts it). The smallest step is 1 of spending per pop, so a state of a
  hundred people in pops of ten reads 0.001 low; the registry interpreter, which now fails any value past the ceiling,
  runs the fast run's whole world (6.9×10^9 people) at wealth 200 in one pop, and a China of 4×10^8, within 10^-5 of
  the model. Real pops from the 1953 and fast-run saves through the generated script match the model's bands to 10^-5.
- **Cost.** Each pop took four tree tests to find its band, then `te_demog_pop_income` made 14 more `wealth` tests and
  evaluated a line per knot below the pop's wealth (2.7–3.6 on average, 14 above 60). It now takes five or six tree tests
  (5.5–5.7 on average) and one line, in the band's leaf. A state stores only the bands it has people in, beside the
  layout marker: 5 to 11 bands on average in these saves, so 12,000–20,000 variables a game against 24,000–32,000
  before (28 a state) and 72,000–95,000 had all 41 been kept. A variable takes about 86 bytes in a plain-text save.
  Per state, the walk sets 82 locals (28 before), and the store, the formula and the country's sum each make one test
  per band.
- **Old saves.** A state from a save before this change has 14 bands in other units and no `te_dg_gini_layout`. The
  country adds only states with the current layout, so until such a state's own pulse its country's Gini is taken over
  the states that have walked since, and with none of them the country keeps its last figure.
