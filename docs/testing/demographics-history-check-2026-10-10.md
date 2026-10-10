# Demographics: the census against history, and the poverty term (2026-10-10)

The first step of phase 2's calibration (parent spec §12; plan
`docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`). Before phase 2 lets the census set the
engine's births and deaths, its rates have to make sense against history. This compares them, country by country,
with history's anchors, and adds the one change the comparison calls for.

## Data and method

- **The model's figures** come from each country's own inputs in a save: SoL, literacy, urban share, techs, laws and
  institution levels (`demographics_harness.inputs_for`). They are the census's steady rates, not the engine's
  population changes.
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

**Before (main 85a23d47):**

| Save | World e0 (countries of 1M or more) | World growth | Children per woman |
|---|---|---|---|
| 1837 | 37.4 | +1.69% a year | 5.95 |
| 1857 | 38.5 | +1.70% | 5.83 |
| 1887 | 39.4 | +1.71% | 5.73 |
| 1949 | 47.5 | +1.42% | 4.59 |

History: world life expectancy about 28.5 in 1820 and 30 in 1870 (Riley). World population grew about 0.4% a year
from 1820 to 1870 and 0.8% from 1870 to 1913 (Maddison), and life expectancy was about 46–48 around 1950.

- **The census gave every country nearly the same rates.** In 1837 life expectancy ran 36.6–39.8 from China to France,
  and growth +1.6% to +1.7% everywhere.
- **The West was about right; everyone else lived too long.** Britain, France and Belgium were within about two years
  of history. In the 1880s and 1890s the model gave India 38 (history 24), Mexico 42 (23), Spain 42 (30), Brazil 41
  (29) and Japan 42 (37).
- **Most of the 1836 world sits where the SoL term was flat.** The game's SoL runs only 6.5–11 across these countries
  in 1837, and infection's SoL term was ×1 at SoL 8 and below. Britain itself starts at SoL 9.0 and literacy 0.21 in
  the save, not the SoL 11 and 0.35 the medicine and fertility scenarios assume. The fit has to use the saves'
  inputs.
- **The game's inputs carry little of history's spread.** The best fit of any SoL and literacy curve leaves about 5.6
  years of error per country, from 7.5. Some misses persist under every fit: Mexico (literacy 0.54 in game), Japan
  (SoL 6.4 but literacy 0.74) and India.

## Levers tried

| Lever | Result |
|---|---|
| A steeper SoL gradient below 9–10 (on the state's mean SoL) | Fixes the world level. The best per-country fit, also raising literacy's weight from 0.3 to 0.5, gave world growth +0.44/+0.60/+0.57%, but put Britain 1900's infant mortality and India 1975's life expectancy out of their bands |
| The same with literacy's weight kept at 0.3 | Every anchor stays in band. This is what the PR builds |
| The poverty term applied pop by pop (each pop's SoL, convex) | No better: about 5.9 years of error against 5.6 |
| A disease-environment term from the malaria traits | Covers only sub-Saharan Africa and Indonesia (none in India, Latin America or China), so it fixes little |
| A higher base level for infection | Gets the world right only by taking the West far below history: ×1.8 gives world growth +0.13 to +0.31% but Britain 24–33 |

The share of people below SoL 10 does separate countries: Britain 0.13, France 0.17, USA 0.30, against Mexico and
Spain 0.80, Brazil 0.83 and Japan 0.94. The state's mean SoL already carries most of that.

## The poverty term

**Infection deaths ×(1 + clamp((9 − SoL) / 4, 0, 1)):** ×1 at SoL 9 and above, rising to ×2 at SoL 5 and below. It
applies on the state's mean SoL, in `demographics_model.poverty_infection` and the generated `te_demog_mult_infection`.

| Option (every anchor in band) | World e0, 1837/1857/1887 | World growth | China 1837 / 1887 | India 1887 | Japan 1887 | Britain 1837 / 1887 |
|---|---|---|---|---|---|---|
| **×2 at SoL 5 (built)** | 30.6 / 31.8 / 32.3 | +1.02 / +1.07 / +1.01% | 28 (+0.8%) / 24 (+0.3%) | 35 (+1.5%) | 31 (+0.8%) | 38 / 45 |
| ×2.25 at SoL 5 | 29.2 / 30.4 / 30.8 | +0.85 / +0.90 / +0.82% | 26 (+0.6%) / 22 (−0.1%) | 35 (+1.4%) | 29 (+0.6%) | 38 / 45 |
| ×2.5 at SoL 5 | 27.8 / 29.0 / 29.5 | +0.67 / +0.73 / +0.63% | 24 (+0.3%) / 19 (−0.5%) | 34 (+1.3%) | 27 (+0.3%) | 38 / 45 |
| ×3 at SoL 4 | 27.3 / 28.5 / 29.0 | +0.60 / +0.66 / +0.55% | 23 (+0.2%) / 18 (−0.6%) | 34 (+1.3%) | 26 (+0.2%) | 38 / 45 |

- **Why ×2 at SoL 5.** World life expectancy is near history's, and China (SoL 6.0 by 1887 in that game) and Japan
  grow as history's did (+0.3% and +0.85%).
- **Why not steeper.** A steeper term brings world growth down to history's 0.4–0.8%, but only by making China, a
  quarter of the world, shrink. Once phase 2 drives the engine, that would be a country losing people every year.
- **What's left.** World growth stays about 1.0% a year. The rest of the gap is India, which grows +1.5% against
  history's +0.8%, the West's fertility, and whatever the engine's own deaths add on top in phase 2: starvation,
  devastation, turmoil. Those are the plan's next steps.
- **1949 is barely touched:** world e0 47.0, growth +1.38% a year, against about 47 and 1.8% in history.
- **The anchors that hold:** every one of the medicine scenarios (`demographics_harness.py medicine`) and the fertility
  scenarios (`fertility`). Those scenarios sit at SoL 9 or above, apart from the agrarian reference at SoL 8.
