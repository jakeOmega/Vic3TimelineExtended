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
- **Crowding is read from the save too:** a state's infection deaths rise by its migration penalty from crowding,
  0.1 × the `migration_crowding` multiplier the save holds (below, "The crowding term"). The first version of this
  check left crowding out; every figure here counts it.
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

**Before (main 85a23d47, with its ×1.15 crowding switch):**

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

**As main has it, a switch.** The census multiplies infection deaths by 1.15 in a state carrying `migration_crowding`
with no Ministry of Urban Planning (the parent spec's "crowding in cities before sanitation"). The first version of
this check left it out, because the harness never read the modifier from a save. The 4x fast-mode run found the gap:
at its first step after 1 January 1837 (census year 1841 in fast mode's log) the census read China 33.6, Britain 34.9
and France 36.2, where the harness gave 36.8, 38.0 and 39.3 on the 1 January save. With each state's crowding read
from the save, the harness gives 33.6, 34.9 and 36.2. The save's own figures sit 0.3–0.7 years higher: some states
had taken their last step before Migration Crowding's first yearly pulse reached them.

Migration Crowding goes on any state above its floor density (10,000 people per unit of arable land), at any
multiplier, so the switch covered 91% of the world's people in the 1837 and 1857 saves: China, India and Japan 100%,
Britain and France 98%, Russia 83–85%, the USA 19–29%. It acted as a near-universal ×1.15, about three years of
life expectancy, and a state crossing the floor by one person jumped.

**Now a function of how crowded the state is (owner, 2026-10-10).** Infection deaths rise by the share migration
attraction falls: 0.1 × the multiplier the crowding refresh applied (`migration_crowding` is
`state_migration_pull_mult` −0.1 a unit), at most +50%. That multiplier is 4.5 r² below ten times the floor density
and linear above it (`migration_crowding_mult`; r is the state's place between the floor and ten times it). The
Ministry of Urban Planning no longer exempts a state: it raises crowding tolerance 10% a level, and Urban Engineering
(Urbanization, Urban Planning, Modern Sewerage, Steel Frame Buildings, Elevator) raises the threshold, so both lower
deaths through the crowding itself.

- **In 1837 most crowding is slight.** The median crowded person's state has a −3.8% migration penalty (r 0.29), and
  nobody lives past r 0.5 except in Britain's densest state (0.60). People-weighted r: China 0.34, Japan 0.32, India
  0.29, Britain 0.23, France 0.12, Russia 0.06, the USA 0.03.
- **So the term is small at first and grows with population.** The world's people-weighted penalty is 0.030 in the
  1837 save, 0.046 in 1857, 0.066 in 1887 and 0.111 in 1949: +3% on infection at the start, near the old ×1.15 by the
  1950s, and more in dense states unless Urban Engineering keeps up.
- **c = 1** (deaths rise by the same share attraction falls) is a choice, not a fit; it needs no fitting and reads
  plainly. c = 2 is in the strength table below.
- **The census reads a stored figure.** `te_update_migration_crowding_modifier` keeps the multiplier it applies in
  `migration_crowding_mult_applied`, and the census reads that: `migration_crowding_mult` reads `ROOT.owner`, and the
  census also runs with ROOT a country (game start, the console). The harness reads the same figure, the modifier's
  multiplier in the save.

## The poverty term

**Infection deaths ×(1 + 0.75 × clamp((9 − SoL) / 4, 0, 1)):** ×1 at SoL 9 and above, rising to ×1.75 at SoL 5 and
below. It applies on the state's mean SoL, in `demographics_model.poverty_infection` and the generated
`te_demog_mult_infection`.

| Crowding c, strength at SoL 5 (state by state) | World e0, 1837/1857/1887 | World growth | China 1837 / 1887 | India 1887 | Japan 1887 | Britain 1837 / 1887 | Denmark 1837 / 1887 | World 1949 |
|---|---|---|---|---|---|---|---|---|
| Main: the ×1.15 switch, no poverty term | 34.5 / 35.6 / 36.6 | +1.43 / +1.46 / +1.48% | 34 (+1.4%) / 35 (+1.5%) | 35 (+1.4%) | 39 (+1.5%) | 35 / 43 | 36 / 38 | 45.3, +1.26% |
| The switch, ×1.5 (this PR's first revision) | 30.6 / 31.7 / 32.3 | +1.04 / +1.08 / +1.06% | 29 (+0.9%) / 27 (+0.7%) | 34 (+1.3%) | 33 (+1.0%) | 34 / 43 | 33 / 36 | 44.7, +1.22% |
| c = 1, no poverty term | 36.7 / 37.5 / 38.0 | +1.63 / +1.62 / +1.59% | 36 (+1.6%) / 35 (+1.5%) | 37 (+1.6%) | 40 (+1.6%) | 37 / 44 | 39 / 40 | 45.8, +1.30% |
| c = 1, ×1.25 | 34.8 / 35.5 / 35.8 | +1.46 / +1.45 / +1.40% | 33 (+1.4%) / 31 (+1.1%) | 36 (+1.5%) | 37 (+1.3%) | 37 / 44 | 37 / 39 | 45.6, +1.28% |
| c = 1, ×1.5 | 33.0 / 33.7 / 33.9 | +1.28 / +1.27 / +1.20% | 31 (+1.1%) / 28 (+0.7%) | 35 (+1.4%) | 34 (+1.1%) | 36 / 44 | 35 / 38 | 45.4, +1.27% |
| **c = 1, ×1.75 (built)** | 31.4 / 32.1 / 32.1 | +1.10 / +1.08 / +0.99% | 29 (+0.9%) / 24 (+0.3%) | 34 (+1.4%) | 31 (+0.8%) | 36 / 44 | 34 / 37 | 45.2, +1.26% |
| c = 1, ×2 | 29.8 / 30.5 / 30.5 | +0.91 / +0.90 / +0.77% | 27 (+0.6%) / 21 (−0.1%) | 34 (+1.3%) | 29 (+0.5%) | 35 / 44 | 33 / 37 | 45.1, +1.24% |
| c = 2, ×1.5 | 32.3 / 32.7 / 32.4 | +1.20 / +1.16 / +1.03% | 30 (+1.0%) / 25 (+0.4%) | 34 (+1.3%) | 32 (+0.9%) | 35 / 43 | 35 / 38 | 44.0, +1.17% |
| c = 2, ×1.75 | 30.6 / 31.0 / 30.7 | +1.01 / +0.96 / +0.80% | 27 (+0.8%) / 22 (−0.1%) | 33 (+1.2%) | 29 (+0.6%) | 35 / 43 | 34 / 37 | 43.8, +1.16% |

History: world life expectancy about 29–31 from 1820 to 1870 and about 47 in 1950; Britain 41 (1838) and 45 (1887);
Denmark 41 and 49; India 24 (1891); Japan 37 (1885). Maddison's China: 381M in 1820, 412M in 1840 and 1850, 358M in
1870 after the Taiping and other rebellions and famine, then 380M in 1890 and 423M in 1910: about +0.4% a year in
peacetime (1820–1840, 1870–1910), +0.3% in the 1880s. Japan's growth about +0.85%.

- **Why ×1.75 with c = 1.** China (SoL 6.0 by 1887 in that game) grows +0.3% a year in 1887, Maddison's peacetime
  pace; history's fall in the 1850s and 1860s came from wars, which the game runs as wars. World life expectancy is
  31–32, a year above history's band. The continuous term gives back the switch's crowding cost wherever crowding is
  slight, so the poverty term that fits moves up a quarter, from ×1.5.
- **Why not steeper.** ×2 brings world growth to +0.8–0.9%, inside history's band, but China shrinks (−0.1% by 1887,
  life expectancy 21). Once phase 2 drives the engine, that would be a quarter of the world losing people every year.
- **c = 2** puts more of the weight on the dense states: at ×1.5 it gives China +0.4% and much the same world as
  c = 1 at ×1.75. c = 1 is kept because it reads plainly (the same share as the migration penalty) and isn't fitted.
- **What it costs the West.** Britain 1837 reads 36 against history's 41 (38 with neither term, 37 with crowding
  alone), and Denmark 34 (41; 39 with neither). Both gain about two years on the switch. Every 1837 life-expectancy
  anchor is Western, so the gain rests on the 1880s non-Western anchors and the world line.
- **What's left.** World growth stays about +1.0–1.1% a year. The rest of the gap is India, which grows +1.4% against
  history's +0.8%, the West's fertility, and whatever the engine's own deaths add on top in phase 2: starvation,
  devastation, turmoil. Those are the plan's next steps.
- **1949 is barely touched:** world e0 45.2, growth +1.26% a year, against about 47 and 1.8% in history.

## The anchors

- **The anchors hold as defined, but barely test the term.** Every one of the medicine scenarios
  (`demographics_harness.py medicine`) and the fertility scenarios (`fertility`) stays in band. But they sit at SoL 9 or
  above (India 1975 exactly at the bend), apart from the agrarian reference at SoL 8 (6.08 children per woman against a
  band of 4.8–6.2). So "in band" says little about the poverty term: the history check is its real test.
- **They leave crowding off.** Stage 1's medicine fit was made without the term. Given every scenario the world's
  mean penalty of 1887 (0.07), India 1975 (45.8 against 46–56) and "medicine, no health system" (47.0 against 48–60)
  fall just under their bands; at 1949's (0.11) today's infant mortality does too (6.2 against 0–6). Britain 1900 stays
  in (44.8 against 44–52). With the old switch four fell out, Britain 1900 among them (43.4).
- **Some mapped countries have no anchors:** Clio Infra has "South Korea" and "North Korea", not Korea; Russia has no
  population series before 1920; Turkey has no life expectancy or infant mortality. `history` names them on stderr.
- **The Netherlands** reads far below history in 1887 (30 against 45), but it shrank in that game.
