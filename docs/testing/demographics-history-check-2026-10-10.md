# Demographics: the census against history, and the poverty term (2026-10-10)

The first step of phase 2's calibration (parent spec §12; plan
`docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`). Before phase 2 lets the census set the
engine's births and deaths, its rates have to make sense against history. This compares them, country by country,
with history's anchors, and adds the one change the comparison calls for.

## Data and method

- **The model's figures** come from each state's own inputs in a save: SoL, literacy, urban share and incorporation,
  with the owner's techs, laws and institution levels. A country's figure is its states' weighted by people, as the
  census builds it (`demographics_save_inputs.state_inputs`, `demographics_harness.country_figures`). The poverty
  term bends at SoL 9, and Western countries have states on both sides of it, so the country's mean SoL would hide
  what its poor and rich states do. The fit itself was found on country means, then re-run state by state (the
  tables below). They are the census's steady rates, not the engine's population changes.
- **Crowding is read from the save too:** a state carrying `migration_crowding` has its infection deaths ×1.15 in
  the census, as in game. The first version of this check left it out (below, "The crowding term"); every figure
  here counts it.
- **The saves** are the gate run's at 1837, 1857 and 1887 (a normal-speed observer game from 1836) and the owner's
  late game at 1949.
- **History's anchors** are from Clio Infra (https://clio-infra.eu): life expectancy at birth, infant mortality, and
  total population (Maddison's), giving growth between the benchmarks around a save's year.
  `scripts/analysis/fetch_history_anchors.py` writes them to a CSV outside the repo; the copy used here is
  `/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv`.
- **The tool:** `demographics_harness.py history SAVE... --anchors CSV`. Countries are matched to tags through
  `HISTORY_TAGS`, each checked against the base game's localization.
- **Caveats:**
  - Population growth includes migration: the USA, Argentina and Brazil gain, while Britain, Ireland and Italy lose.
  - Italy is Sardinia-Piedmont until Italy forms in game, and India is the East India Company.
  - In the harness, France's Family Limitation isn't read from a save, so the model's France has too many children.
  - History's life expectancy before 1900 is mostly Western Europe's.

## What the comparison found

**Before (main 85a23d47, crowding counted):**

| Save | World e0 (countries of 1M or more) | World growth | Children per woman |
|---|---|---|---|
| 1837 | 34.5 | +1.43% a year | 5.97 |
| 1857 | 35.6 | +1.46% | 5.85 |
| 1887 | 36.6 | +1.48% | 5.75 |
| 1949 | 45.3 | +1.26% | 4.62 |

History: world life expectancy about 28.5 in 1820 and 30 in 1870 (Riley). World population grew about 0.4% a year
from 1820 to 1870 and 0.8% from 1870 to 1913 (Maddison), and life expectancy was about 46–48 around 1950.

- **The census gave every country nearly the same rates.** In 1837 life expectancy ran about 34–39 in every large
  country, from Korea and China to the USA, and growth +1.4% to +1.7% everywhere.
- **The West ran a little short; everyone else lived too long.** Britain, France and Belgium were within about one to
  six years of history. In the 1880s and 1890s the model gave India 35 (history 24), Mexico 40 (23), Spain 39 (30),
  Brazil 40 (29) and Japan 39 (37).
- **Most of the 1836 world sits where the SoL term was flat.** The game's SoL runs only 6.5–11 across these countries
  in 1837, and infection's SoL term was ×1 at SoL 8 and below. Britain itself starts at SoL 9.0 and literacy 0.21 in
  the save, not the SoL 11 and 0.35 the medicine and fertility scenarios assume. The fit has to use the saves'
  inputs.
- **The game's inputs carry little of history's spread.** The best fit of any SoL and literacy curve leaves about 5.6
  years of error per country, from 7.5. Some misses persist under every fit: Mexico (literacy 0.54 in game), Japan
  (SoL 6.4 but literacy 0.74) and India.

## Levers tried

Found before crowding was counted: each lever's levels sit about three years higher than they would now, but the
comparisons between them hold.

| Lever | Result |
|---|---|
| A steeper SoL gradient below 9–10 (on the state's mean SoL) | Fixes the world level. The best per-country fit, also raising literacy's weight from 0.3 to 0.5, gave world growth +0.44/+0.60/+0.57%, but put Britain 1900's infant mortality and India 1975's life expectancy out of their bands |
| The same with literacy's weight kept at 0.3 | Every anchor stays in band. This is what the PR builds |
| The poverty term applied pop by pop (each pop's SoL, convex) | No better: about 5.9 years of error against 5.6 |
| A disease-environment term from the malaria traits | Covers only sub-Saharan Africa and Indonesia (none in India, Latin America or China), so it fixes little |
| A higher base level for infection | Gets the world right only by taking the West far below history: ×1.8 gives world growth +0.13 to +0.31% but Britain 24–33 |

The share of people below SoL 10 does separate countries: Britain 0.13, France 0.17, USA 0.30, against Mexico and
Spain 0.80, Brazil 0.83 and Japan 0.94. The state's mean SoL already carries most of that.

## The crowding term

The census multiplies infection deaths by 1.15 in a state carrying `migration_crowding` with no Ministry of Urban
Planning (`te_demog_mult_infection`; the parent spec's "crowding in cities before sanitation"). The first version of
this check left it out, because the harness never read the modifier from a save. The 4x fast-mode run found the gap:
on 1 January 1837 its census read China 33.6, Britain 34.9 and France 36.2, where the harness gave 36.8, 38.0 and 39.3
for the same save. With each state's crowding read from the save, the harness gives the census's figures exactly.

- **It covers nearly everyone.** Migration Crowding goes on any state above its floor density (10,000 people per unit
  of arable land), at any multiplier, and the census's term is all or nothing. 91% of the world's people lived in such
  states in the 1837 and 1857 saves: China, India and Japan 100%, Britain and France 98%, Russia 83–85%, the USA
  19–29%. In 1837 three-quarters of them were in states under 20% urban, and 30% in states whose crowding multiplier
  was under 0.1.
- **So it acts as a near-universal ×1.15 on infection,** about three years of life expectancy, rather than a city
  penalty. It lowered world life expectancy from 37.5 to 34.5 in 1837 and growth from +1.69% to +1.43%.

## The poverty term

**Infection deaths ×(1 + 0.5 × clamp((9 − SoL) / 4, 0, 1)):** ×1 at SoL 9 and above, rising to ×1.5 at SoL 5 and
below. It applies on the state's mean SoL, in `demographics_model.poverty_infection` and the generated
`te_demog_mult_infection`.

| Strength at SoL 5 (state by state, crowding counted) | World e0, 1837/1857/1887 | World growth | China 1837 / 1887 | India 1887 | Japan 1887 | Britain 1837 / 1887 | Denmark 1837 / 1887 | World 1949 |
|---|---|---|---|---|---|---|---|---|
| None (before) | 34.5 / 35.6 / 36.6 | +1.43 / +1.46 / +1.48% | 34 (+1.4%) / 35 (+1.5%) | 35 (+1.4%) | 39 (+1.5%) | 35 / 43 | 36 / 38 | 45.3, +1.26% |
| ×1.25 | 32.5 / 33.6 / 34.4 | +1.24 / +1.27 / +1.28% | 31 (+1.2%) / 31 (+1.1%) | 34 (+1.4%) | 36 (+1.2%) | 34 / 43 | 34 / 37 | 45.1, +1.25% |
| **×1.5 (built)** | 30.6 / 31.7 / 32.4 | +1.04 / +1.08 / +1.06% | 29 (+0.9%) / 27 (+0.7%) | 34 (+1.3%) | 33 (+1.0%) | 34 / 43 | 33 / 36 | 44.9, +1.23% |
| ×1.75 | 28.9 / 30.0 / 30.6 | +0.84 / +0.87 / +0.84% | 26 (+0.6%) / 24 (+0.2%) | 33 (+1.2%) | 30 (+0.7%) | 33 / 43 | 31 / 35 | 44.7, +1.22% |
| ×2 | 27.4 / 28.5 / 29.0 | +0.63 / +0.67 / +0.62% | 24 (+0.3%) / 21 (−0.2%) | 32 (+1.1%) | 28 (+0.4%) | 33 / 43 | 30 / 34 | 44.6, +1.20% |

History: world life expectancy about 29–31 from 1820 to 1870 and about 47 in 1950; Britain 41 (1838) and 45 (1887);
Denmark 41 and 49; India 24 (1891); Japan 37 (1885); China's growth about +0.3% and Japan's +0.85%.

- **Why ×1.5.** World life expectancy is in history's band (30.6 in 1837, 31.7 in 1857), and China (SoL 6.0 by 1887
  in that game) still grows, +0.7%. These are the world figures the first fit reached at ×2 without crowding
  (30.6 / 31.7 / 32.1, +1.0% a year).
- **Why not steeper.** ×1.75 brings world growth to +0.85% and ×2 to +0.63%, inside history's band, but China slows to
  +0.2% at ×1.75 and shrinks at ×2 (−0.2% by 1887, life expectancy 21). Once phase 2 drives the engine, that would be a
  quarter of the world losing people every year. Japan falls to 28–30 against history's 37.
- **What it costs the West.** Mostly crowding, not poverty. Britain 1837 reads 34 against history's 41 (36 with
  neither term), and Denmark, the one smaller Western country with anchors at all three dates, 33 (41). Every 1837
  life-expectancy anchor is Western, so the gain rests on the 1880s non-Western anchors and the world line.
- **What's left.** World growth stays about 1.05% a year. The rest of the gap is India, which grows +1.3% against
  history's +0.8%, the West's fertility, and whatever the engine's own deaths add on top in phase 2: starvation,
  devastation, turmoil. Those are the plan's next steps.
- **1949 is barely touched:** world e0 44.9, growth +1.23% a year, against about 47 and 1.8% in history. Crowding
  costs about two of those years.

### If crowding meant cities (owner call)

The term as built is a near-universal one. Two narrower readings, each with the poverty strength refitted:

| Crowding counted where | Poverty strength | World e0, 1837/1857/1887 | World growth | China 1887 | Britain 1837 / 1887 |
|---|---|---|---|---|---|
| Any multiplier (built) | ×1.5 | 30.6 / 31.7 / 32.4 | +1.04 / +1.08 / +1.06% | 27 (+0.7%) | 34 / 43 |
| Multiplier 0.1 or more | ×1.5 | 31.5 / 32.5 / 33.0 | +1.12 / +1.15 / +1.11% | 27 (+0.7%) | 35 / 44 |
| Multiplier 0.1 or more | ×1.75 | 29.8 / 30.8 / 31.2 | +0.92 / +0.95 / +0.89% | 24 (+0.2%) | 35 / 44 |
| Urban share 0.2 or more | ×1.75 | 31.4 / 31.2 / 31.2 | +1.11 / +1.00 / +0.90% | 24 (+0.2%) | 34 / 43 |
| Urban share 0.2 or more | ×2 | 29.8 / 29.7 / 29.6 | +0.92 / +0.80 / +0.67% | 21 (−0.2%) | 34 / 43 |

- Narrowing crowding gives back about one year of world life expectancy, so the poverty strength that fits moves up
  by about a quarter.
- The urban gate uses the harness's urban share, which runs above the census's own (`te_dg_urban_share`: one of
  Britain's states reads 0.50 in the harness and 0.36 in game), so the census would gate fewer states than this table.
- China's states pass the urban gate by 1887 in this table, so China's figure is the same as with crowding as built.

## The anchors

- **The anchors hold as defined, but barely test the term.** Every one of the medicine scenarios
  (`demographics_harness.py medicine`) and the fertility scenarios (`fertility`) stays in band. But they sit at SoL 9 or
  above (India 1975 exactly at the bend), apart from the agrarian reference at SoL 8 (6.08 children per woman against a
  band of 4.8–6.2). So "in band" says little about the poverty term: the history check is its real test.
- **They leave crowding off.** With it on, as the game would give 1900 Britain or 1975 India, four anchors fall out
  of band: Britain 1900's life expectancy (43.4 against 44–52), India 1975's (44.5 against 46–56), "medicine, no health
  system" (45.8 against 48–60) and today's infant mortality (6.4 against 0–6). Stage 1's medicine fit was made without
  the term too. If crowding stays as built, stage 1 needs refitting; if it becomes a city term, most of those
  scenarios' people would fall outside it.
- **Some mapped countries have no anchors:** Clio Infra has "South Korea" and "North Korea", not Korea; Russia has no
  population series before 1920; Turkey has no life expectancy or infant mortality. `history` names them on stderr.
- **The Netherlands** reads far below history in 1887 (30 against 45), but it shrank in that game.
