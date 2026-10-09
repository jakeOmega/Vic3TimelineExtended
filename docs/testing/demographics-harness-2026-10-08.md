# Demographics harness results — 2026-10-08

**Tool:** `scripts/analysis/demographics_harness.py`, run from `demographics_model.py` and `demographics_params.py`.
**Mod revision:** branch `demographics-phase0` at `a4e41d62` plus the harness commit. **Game files:** none; the harness
reads a plain-text save and the committed `common/buy_packages/00_buy_packages.txt`.
**Save:** `great britain_temptst.v3`, Victoria 3 1.14.5, 1 January 1836, Great Britain, debug-mode plain text. Every
country in it is at its 1836 start.

It runs [the demographics design](../superpowers/specs/2026-10-08-demographics-design.md)'s phase 0 checks that need no
game: the §2.2/§2.3 sketch, the §4.1 Gini anchor and a country seeded from a save. `natural-change` and `replay` are
built and wait for their input (below).

**Read the numbers with these limits:**
- **One save, 1836 only.** The inputs are each country's start: SoL, literacy, urban share, laws and technology. No
  institutions are read, so a country's Family Limitation and similar measures are not in the seeded figures.
- **Seeded figures are the model's equilibrium for those inputs,** not a measurement of the save's own age structure
  (a pop record carries no age).
- **The Q10 natural-change check has not run.** It needs two plain-text saves a month apart, which the owner makes
  (the plan's Owner checks, item 1). Until then the model has not been checked against the engine's monthly change.
- **Calibration to world history (§2.3's targets) is not here.** It needs an observer run's yearly saves and is phase 2's
  prerequisite.

## `sketch`

```
python3 scripts/analysis/demographics_harness.py sketch
```

```
1836 agrarian (reference)    TFR 6.03  e0 37.4  e65 12.2  IMR 189  0-14 40%  15-64 55%  65+ 4.5%  growth +1.65%
Britain 1836                 TFR 5.57  e0 39.6  e65 12.5  IMR 172  0-14 39%  15-64 56%  65+ 5.0%  growth +1.56%
France 1836 (Family Limitation) TFR 4.91  e0 39.2  e65 12.5  IMR 175  0-14 36%  15-64 58%  65+ 6.1%  growth +1.09%
```

This holds each case's inputs constant for 300 years and prints the equilibrium. §2.3's sketch table gives Britain 1836
at 5.5 children per woman (real: about 5) and France at 4.9 (real: about 3.8, because the sketch leaves out Forced
Heirship's birth cut); the model reproduces both (5.57, 4.91). The inputs for each case are in `SKETCH` in the script.
The agrarian reference is not close to §2.2's table, which has 5.2 children, 0–14 at 35% and 65+ at 5–7%: the model
gives 6.0, 40% and 4.5%, because §2.3 sets the wealth term at 6.2 for SoL 8 or below and that case has little
schooling or city life to lower it. Its growth of +1.65% is at the top of §2.2's +0.8 to +1.7%. Whether that
reference is too young is a calibration question for phase 2, not something this run settles. IMR is infant deaths per
1,000 births; e0 and e65 are the women's and men's average.

## `gini`

```
python3 scripts/analysis/demographics_harness.py gini "$S" --tag GBR --tag FRA --tag PRU --tag USA --tag CHI
```

```
GINI_SCALE for GBR = 0.52: 0.85 (params: 0.85)
GBR grouped 0.260 shown 0.52
FRA grouped 0.117 shown 0.40
PRU grouped 0.153 shown 0.43
USA grouped 0.193 shown 0.46
CHI grouped 0.123 shown 0.40
```

This is §4.1's Gini. Each pop's income is the buy package at its wealth (capped at wealth 60, as
`INCOME_WEALTH_CAP` says), summed per stratum and per country; the grouped Gini over lower, middle and upper strata
is then scaled so Great Britain reads 0.52, inside §4.1's 0.5–0.55 anchor for the 1830s. The scale that does it is 0.85,
which is what `GINI_SCALE` already holds, so no parameter changes. The other four are not anchored (§4.1 has no 1836
figure for them); they show the spread the one constant gives: France and China lowest at 0.40, Prussia 0.43 and the
US 0.46, with Britain highest. §4.1 notes the grouped form misses inequality within each stratum, which is why a
floor of 0.30 and a scale stand in for it.

## `seed GBR`

```
python3 scripts/analysis/demographics_harness.py seed "$S" --tag GBR
```

```
GBR: pop 25,951,647 SoL 8.4 literacy 0.19 urban 0.48
  TFR 5.91 (wealth 6.16 x factor 0.96; means 0.17)
  e0 women 42.9 men 38.7; IMR 161 per 1000
  0-14 41% 15-64 55% 65+ 4.2% median 19.4
```

This is §2.3's fertility formula and §2.4's life table at Britain's own start inputs, then the state's equilibrium
structure that §2.6 uses as a starting value. The save has Britain at SoL 8.4, literacy 0.19 and an urban share of
0.48, not the sketch's 11, 0.35 and 0.3. The lower SoL raises the wealth term from the sketch's 5.90 to 6.16, so
fertility is 5.91 against the sketch's 5.57. Means are 0.17: the traditional 0.4 times access, 0.3 + 0.7 × 0.19.
Life expectancy at birth is 42.9 for women and 38.7 for men. The two averaged, 40.8, sit above the sketch's 39.6.
Changing one sketch input at a time to the save's value: its technology adds 2.2 years (`medical_degrees` is the only
one of its 53 that the model reads for mortality; the sketch holds none), its laws add 1.0 (Charitable Health System
alone adds 1.1), and its lower SoL and literacy take about 2.1 off. Nothing here checks the age structure against the
engine; only the §14 Q10 saves can.

## `seed CHI`

```
python3 scripts/analysis/demographics_harness.py seed "$S" --tag CHI
```

```
CHI: pop 366,405,617 SoL 8.2 literacy 0.13 urban 0.10
  TFR 6.06 (wealth 6.18 x factor 0.98; means 0.16)
  e0 women 39.3 men 34.5; IMR 192 per 1000
  0-14 41% 15-64 55% 65+ 4.3% median 19.5
```

The same checks for the largest country. Lower literacy and a mostly rural population leave the fertility factor near
1, so TFR is 6.06, about the wealth term itself. Mortality is higher than Britain's (infant mortality 192 per 1,000,
life expectancy 39.3 and 34.5), and SoL is not the reason: the two countries' SoL differ by 0.2, and giving China
Britain's moves its average life expectancy from 36.9 to 37.0. Technology and laws are. With Britain's technology
(`medical_degrees`) China reaches 39.2 and infant mortality 173; with Britain's laws (Charitable Health System alone
adds 1.1), 38.1 and 183; with Britain's literacy, 37.3 and 189; with SoL, literacy, technology and laws all Britain's,
40.8 and 161, which is Britain's own. The age
structure is close to Britain's (41% / 55% / 4.3%).

## `inputs`

```
python3 scripts/analysis/demographics_harness.py inputs "$S" --tag GBR --tag CHI
```

```
GBR pop=25,951,647 states=26 sol=8.4 literacy=0.19 urban=0.48 laws=59 techs=53
CHI pop=366,405,617 states=43 sol=8.2 literacy=0.13 urban=0.10 laws=59 techs=24
```

This is the reader behind `gini` and `seed`: each country's start inputs, as `demographics_save_inputs.py` reads them
from the save's pops, states, laws and technology sections. SoL is the people-weighted figure over the country's
pops, literacy is literate over workforce, and urban share is the people outside peasant, farmer and slave pops. These two lines are what the two `seed` runs above start from.

## Not yet run

- **`natural-change OLD NEW`** (§14 Q10) compares the world's population change between two saves with what the
  defines' SoL curves predict from the old save's pops, and prints the ratio. It needs two plain-text saves a month
  apart. The owner makes them.
- **`replay DEBUG_LOG`** steps the model from a before-state that the game logged and compares it with the logged
  after-state. Its input is the `TE_DEMOG_REPLAY` lines that Task 15's debug option writes; the format is
  `format_replay` in the script and is covered by `test_demographics_harness.py`.
