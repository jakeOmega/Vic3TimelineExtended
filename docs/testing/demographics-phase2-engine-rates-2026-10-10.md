# Demographics phase 2 step 4: probes and gate results (2026-10-10)

The gate of phase 2 step 4: the census sets the engine's births and deaths
(plan `docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md`, Task 12; PR #869). This records the
offline half, run on this date, and leaves room for the in-game half, which needs the owner.

**Status: the offline gate passes after the owner's retune (`WEALTH_TFR_LOW` 6.2 → 6.0, 2026-10-10): ×1.66, and no
20M+ country shrinks (China +0.12% in 1887, its lowest).** This is the third run. The first (before the owner's
amendment) passed the multiple at ×1.66 and failed on China at −0.09% in 1887. The second, after the amendment (the
census cancels what it absorbs through M, under Full only, and absorbs mild starvation; #881 took the LGBTQ+ Rights
laws' birth lines away), put the engine within 0.1 per 1,000 of the census in every save, so the multiple became the
census's own: ×1.78, a fail, with China at +0.23%. The owner chose the first of two candidates (below, "The
multiple"). The in-game probes are still to do.

**The fast-mode gate run (2026-10-11, below) passes inside the gate's window, census years 1837–1900:** ×1.63, no
20M+ country shrinking, nothing clamped, Closed Borders at −0.09 per 1,000, every state keeping its census modifiers
(P4). Europe's share stays flat where it should rise. Past 1900, four Indian countries lose people for 12 to 39
census years, and the tools' own exit codes fail on them (below). The replay was not run.

**Release precondition (owner, 2026-10-10, amended):** nothing changes outside Full. Step 4 edits no engine birth or mortality line; step 5's
retune of the global defines is dropped (owner, 2026-10-10).

## The build, the saves and the tools

- **The build:** branch `feat/demog-phase2-engine-rates` (PR #869), at the commit that adds this file.
- **The saves:** the gate run's six autosaves, 1837 to 1887 a decade apart, in
  `/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`. They come from a normal-speed observer game on a build before
  #855, so their own stored census rates are the old model's.
- **The tool:** `scripts/analysis/demographics_harness.py predict SAVE... --slope` (Task 10).
  - **The census rates:** by default, the current model's stable rates for each state's own inputs (SoL, literacy,
    urban share, crowding, incorporation, the owner's techs, laws and institutions), not the saves' stale ones.
  - **The absorbed lines:** the owner's law and tech lines the census absorbs, institution lines × level in
    incorporated states, each pop's class line, literacy and mild starvation: applied, and netted out by M.
  - **The terms on top:** each pop's severe starvation, the owner's on-top law and tech lines and the state's
    devastation. Terms on top a save doesn't hold (pollution, turmoil, events, `low_pop_state`, unemployment, workplace
    mortality, wealth mortality) are left out.
  - **The world multiple:** chains each save's predicted world growth to 1900.
- **The checks around it:** the whole unittest suite, `ruff`, the tab check, `organize_loc --check`,
  `gen_demographics.py --check`, the six audits the plan names, and `demographics_harness.py medicine` and
  `fertility`.

## The offline gate

| Check | Threshold | Result |
|---|---|---|
| World multiple, 1837–1900 | ×1.3–×1.7 | **×1.66, pass** (×1.78 before the retune) |
| No 20M+ country predicted to shrink | none | **pass:** China +0.12% a year in 1887, its lowest (+0.23% before) |
| Share of people in clamped states | under 1% | 0.0% in every save |
| The unittest suite, `ruff`, tabs, `organize_loc --check`, `gen_demographics.py --check`, the CI audits | all clean | see the PR |
| Medicine scenarios (`medicine`) | each in its band | all in band, before and after the retune |
| Fertility scenarios (`fertility`) | each in its band | all in band, before and after (the 1836 agrarian reference 5.87 in [4.8–6.2]) |

**Before and after the retune** (`WEALTH_TFR_LOW` 6.2 → 6.0; predicted world growth and China's, % a year):

| Save | World, 6.2 | World, 6.0 | China, 6.2 | China, 6.0 |
|---|---|---|---|---|
| 1837 | +0.93 | +0.82 | +0.79 | +0.68 |
| 1847 | +1.07 | +0.96 | +0.96 | +0.85 |
| 1857 | +0.94 | +0.83 | +0.60 | +0.49 |
| 1867 | +0.92 | +0.81 | +0.43 | +0.33 |
| 1877 | +0.82 | +0.71 | +0.26 | +0.16 |
| 1887 | +0.83 | +0.73 | +0.23 | +0.12 |
| Multiple to 1900 | ×1.78 | ×1.66 | | |

**The world, save by save, as retuned** (% a year; the terms on top in births and deaths per 1,000; the absorbed groups
in points of world growth a year, what absorbing each adds against leaving it on top; the retune leaves the groups'
figures as they were):

| Save | People | Census | Predicted | On top: births | On top: deaths | Child labour | Women's rights | Health laws | Mild starvation | Starving slope |
|---|---|---|---|---|---|---|---|---|---|---|
| 1837 | 1,031M | +0.85 | +0.82 | −0.09 | +0.17 | +0.217 | −0.234 | −0.004 | +0.020 | 0.036 |
| 1847 | 1,133M | +0.97 | +0.96 | −0.02 | +0.04 | +0.212 | −0.234 | −0.005 | +0.031 | 0.069 |
| 1857 | 1,244M | +0.84 | +0.83 | −0.02 | +0.07 | +0.216 | −0.235 | −0.006 | +0.086 | 0.112 |
| 1867 | 1,365M | +0.82 | +0.81 | −0.00 | +0.02 | +0.215 | −0.234 | −0.013 | +0.096 | 0.132 |
| 1877 | 1,458M | +0.75 | +0.71 | −0.14 | +0.26 | +0.214 | −0.234 | −0.027 | +0.154 | 0.157 |
| 1887 | 1,542M | +0.75 | +0.73 | −0.07 | +0.14 | +0.213 | −0.232 | −0.040 | +0.184 | 0.174 |

- **Child labour's class lines** (owner ruling: absorbed at the census's smaller work term) would take 0.21–0.22 points
  a year off world growth on top.
- **The women's-rights birth lines** (natural fertility carries them) would add about 0.23 points. The census was
  fitted without them (step 2).
- **The health laws' lines** would cut deaths by 0.004–0.040 points of world growth a year on top, rising with the
  Ministry of Health (Britain 0.42 in 1887). The census's access × treatment carries them.
- **Mild starvation** (owner amendment B: the poverty term was fitted without it) would take 0.02 points in 1837 and
  0.18 in 1887 (births −0.91, deaths +0.93 per 1,000 world-wide; China 0.32 points, India 0.25, Austria 0.33).
- **The starving slope below SoL 4** (owner ruling: the poverty term replaces it) cost 0.04 points in 1837 and 0.17 in
  1887, as the plan's §1 measured.
- **What stays on top** is now small: severe starvation, devastation and the late-era lines. Where it shows: Austria 1887
  (census +1.23%, predicted +0.45%; 7% of its people in severe starvation) and Russia 1877 (+1.00%, +0.61%; 3.3% in
  severe starvation, and devastation adding 0.6 deaths per 1,000).
  - **Severe starvation scaled** ("The severe term", below; 2026-10-11). `predict` on the 1887 save with the
    current code: Austria +0.41% with the penalty flat, **+0.72%** scaled by each pop's starvation value (deaths on
    top 5.4 → 3.1 per 1,000); the world +0.693% → +0.700% a year. No other country of 20M or more moves by 0.01 points.

**Countries of 20M or more in 1887, as retuned** (% a year, census and predicted): China +0.12, +0.12; British India
+1.15, +1.15; Russia +0.97, +0.97; the USA +1.49, +1.49; Japan +0.61, +0.61; France +0.50, +0.49; Turkey +1.29,
+1.29; Britain +0.81, +0.80; Austria +1.23, +0.45; New Granada +1.32, +1.32; Mexico +1.42, +1.41; Korea +0.51, +0.51.
The full per-save tables are `predict`'s output.

### The multiple: candidate parameters (owner's decision, 2026-10-10: `WEALTH_TFR_LOW` 6.0)

Before the retune, the census's own rates gave the world +0.95 to +1.07% a year to 1867 and +0.86% after, against history's 0.4% (1820–1870)
and 0.8% (1870–1913, Maddison). Two candidates, each run through `predict` on the same six saves with every other
parameter as built (`demographics_harness.py history` gives the life expectancy and children per woman beside
Clio Infra's and Gapminder's; `medicine` and `fertility` check the step-1 fit's anchor bands). **The trade:** China,
already below Maddison's peacetime +0.3% at +0.23% in 1887, falls further under both, so the owner is weighing the
world band against the China anchor the poverty term was fitted to.

| Change | World multiple | China 1877 / 1887 | Any 20M+ shrinking | Anchor bands (`medicine`, `fertility`) | Evidence and cost |
|---|---|---|---|---|---|
| As built | ×1.78 | +0.26 / +0.23% | none | all in | — |
| **`WEALTH_TFR_LOW` 6.2 → 6.0** (children per woman from wealth at SoL 8 and below): **chosen (owner)** | **×1.66** | +0.16 / +0.12% | none | **all in** | The model's children per woman sit above Gapminder's almost everywhere: 1837 China 6.09 (Gapminder 5.5), Japan 5.75 (4.5), Britain 5.50 (4.8), France 4.45 (3.6); 1887 Japan 5.43 (4.0), the USA 5.60 (4.4), France 4.10 (3.2). At 6.0 each moves 0.1–0.2 toward Gapminder's; India (5.87 against 5.8) and Russia (5.57 against 6.6) move away. Life expectancy doesn't change |
| **`POVERTY_INFECTION_SOL` 9 → 10** (the poverty term starts at SoL 10) | ×1.62 | +0.16 / +0.15% | none | **one out:** India 1975's life expectancy 44.5 against [46–56] | Aims at the gap the history check left: India grows +1.36% against history's +0.84% (its 1887 life expectancy 34 against 24), and goes to 32. But it costs the West: Britain's 1837 life expectancy drops from 35.6 to 33.8 (history 41), already the check's weakest anchor |
| `POVERTY_INFECTION_AT_FLOOR` 1.75 → 1.9 (rejected) | ×1.66 | +0.03 / −0.03% | China, 1887 | not run | the history check's own table: steeper poverty takes China below Maddison's +0.3% first |
| `POVERTY_INFECTION_AT_FLOOR` → 2.0 (rejected) | ×1.58 | −0.13 / −0.20% | China, 1877 and 1887 | not run | the same |

### Private Health Insurance's wealth mortality (owner, 2026-10-10: stays on top for now)

The law's `institution_modifier` carries `state_mortality_wealth_mult` −0.002 a level of the Ministry of Health. The
engine describes it as "an increase or decrease to pop mortality per Wealth", so it scales by each pop's own wealth, and
nothing floors the mortality multiplier above the engine's own 0. At level 5 it is −1% a wealth point, −50% at wealth
50, and the mod raises the institution's levels with techs, up to `MAX_INSTITUTION_INVESTMENT` 9 (−1.8% a point, the
floor at wealth 56). The census leaves it on top: M can't net out a term whose scaling isn't confirmed.

**Measured on the owner's 1949 save** (`french commune_1949_07_20.v3`) with the description's semantics: each pop's
mortality × (1 + wealth × the field + its other terms), in incorporated states. The other terms are taken as 0, so the
shares are of the bare curves' deaths, and the engine's floor caps a pop's loss at its whole bare deaths. The 1954–1976
saves are compressed binary and couldn't be read.
- **Nobody holds it in 1949.** 140 countries (1,401M people) have no health system, 47 Charitable Health System
  (447M), 33 Public Health Insurance (677M), none Private Health Insurance. It removes no deaths in this save.
- **If every country with a Ministry of Health held it at its own level** (79 countries, 884M people in incorporated
  states): 2.7% of the world's bare deaths and 8.1% of those states'.
  - By country: France (level 5, mean wealth 22.7) 20.8%; Uruguay 19.1%, Portugal 17.2%, Spain 16.4% (level 5);
    Prussia (level 4) 10.9%; Britain 7.6% and the USA 5.6% (level 3).
  - The five richest states, all French (mean wealth 26.5–28.0): 23.5% to 25.9% of their deaths.
  - The pops: wealth p10 8, p50 12, p90 27, p99 40, max 78. The largest single term is −0.78 (capitalists at wealth
    78, Colombia, level 5); 454 pops (1.55M people) pass −50%; none reaches the floor at level 5.
- **So it is material wherever a rich country adopts it** (the owner's test: over 5% of a rich state's deaths, or a pop
  past −50%). Nothing is built. Two proposals, for the owner:
  1. **Absorb it per pop in the walk under Full**, as mild starvation is: the generator emits the field (the law's line
     × the Ministry of Health's level, incorporated states) as a state value read once into a local, and
     `te_demog_absorbed_walk_pop` adds wealth × field to the pop's absorbed deaths, so M nets it and the census's
     access × treatment carries the law. Outside Full it stays vanilla's.
  2. **Probe P6 first** (below), to confirm the per-pop semantics before building.

## The fast-mode gate run (2026-10-11)

- **The run:** a new 1836 game on #869 at f19ee434, Demographics on Full (the first autosave's `game_rules` says so),
  observed, census log on (option b), fast mode at 4× from day 1, launched 2026-10-10 at 22:47. Every `debug.log` and
  `error.log` generation and 46 yearly autosaves, 1837 to 1882, are in `/mnt/d/vic3te-data/vic3te-demog-p2-gate-full-2026-10-11/`.
- **It crashed on 1 January 1882,** just after that day's autosave: an access violation with no symbols (crash folder
  `victoria3_01260911_014425`). The last lines are vanilla's Red Army leader errors (`00_communism.txt:185`), logged
  monthly since well before. No census line or census error is near it. The owner is continuing from the 1882 save to
  see whether it happens again.
- **The census clock runs four census years to the calendar's one:** census 1900 is calendar November 1851, census
  2020 is November 1881. So the gate's window is calendar 1837 to 1851. Past it, the census years run ahead of the
  techs, laws and economy the model reads. No anchor is comparable in fast mode, from census 1900 on: Britain's TFR of
  4.65 in census 1900 is calendar 1851's Britain.

| Check | Threshold | Result |
|---|---|---|
| World 1837–1900, census years | ×1.3–×1.7 | **×1.63, pass:** 930M to 1,516M in the logged countries (a million people or more) |
| No 20M+ country losing people ten census years running outside wars | none | **Pass to 1900.** Four countries fail past it (below) |
| Share of people in clamped states | under 1% | 0.00% to 1900, 0.004% to 2020 |
| Closed Borders `mig_raw` median | within ±1 per 1,000 | **−0.09 (−0.13 weighted by people), pass,** over 6,457 country-years (saves 1840, 1845, 1850, 1852) |
| P4: census modifiers through a change of owner | none missing | **Pass.** `predict --check-modifiers` finds none missing on the 1866, 1876 and 1882 saves, after the East India Company broke up and several revolutions. In 1882, 983 states carry `te_dg_mb`, and 983 each carry the births and deaths modifiers |
| The replay exact | exact | **Not run:** the run logged no option a blocks |
| Europe's share rising to 1900, Asia's falling | the right direction | **Partly, accepted.** East Asia 44.1% to 40.0%, Asia as a whole 65.3% to 62.1%, North America 3.1% to 5.5%. Europe stays flat (23.3% to 23.2%); Europe and North America together go from 26.4% to 28.7%, as emigration carried Europe's growth. **Accepted (owner, 2026-10-11):** tuning it would mean tuning migration, beyond the census's scope |
| Errors | none from the census | **None:** 45,869 distinct lines across every generation, 255 outside the two registries, none in a census file |

The regional shares count each save's pops by the continent of their state's strategic region. The continents come from
vanilla's strategic-region files, one per continent, whose "west and south Asia" puts the Middle East with India. The
saves are calendar 1837 and 1852.

**What the engine adds on top, by census decade.** The table is weighted by people over the logged countries. `bz` and
`dz` are the births and deaths the engine adds beyond the census's target, as a share of it. India's countries are
East India, Bengal, Carnatic, Hindustan, Satara, Patiala and Hyderabad.

| Census year | `m_b` | `m_d` | `bz` | `dz` | India's countries' `dz` |
|---|---|---|---|---|---|
| 1840 | −0.296 | −0.367 | +0.004 | −0.017 | −0.251 |
| 1860 | −0.285 | −0.385 | +0.002 | +0.003 | −0.123 |
| 1880 | −0.263 | −0.373 | −0.010 | +0.034 | +0.086 |
| 1900 | −0.269 | −0.387 | −0.016 | +0.053 | +0.113 |
| 1950 | −0.304 | −0.393 | −0.006 | +0.049 | +0.025 |
| 2000 | −0.353 | −0.469 | −0.001 | +0.194 | +0.361 |
| 2020 | −0.405 | −0.445 | −0.001 | +0.238 | +0.641 |

- **Inside the window,** the engine lands within about 5% of the census's deaths and 2% of its births.
- **Past it, the deaths on top climb to +24% of the target.** They are not severe starvation: under 1% of people starve
  severely in this run's saves, as in the normal-speed gate saves. Mild starvation, which the census absorbs, reached
  18% of people in calendar 1857, against 8% at normal speed: in fast mode the people outgrow the farms.
- **What `dz` follows:** life expectancy (r = +0.49 over 21,831 country-years) and Gini (+0.41). Turmoil barely
  registers (+0.06).
- **A likely reading, not proven:** the lines left on top are a share of the engine's bare rate. As the census cuts
  deaths further (M toward −0.6), the same lines become a larger share of a smaller target.

**The four countries that lose people past 1900** all came out of the East India Company's break-up. `--phase2` exited
1 on them because its run check didn't stop at `--to-year`. It does now (owner, 2026-10-11), and the run passes it. `predict` exits 1 on the 1866 save for two of them,
Hindustan (−0.14% a year) and Satara (−0.16%). Its "world multiple 1882–1900 ×1.46" projects calendar 1882 to
calendar 1900, which is not the gate's multiple.

| Country | Longest losing run (census years) | Calendar | People | What drives it |
|---|---|---|---|---|
| Bengal | 1975–1987 (12) | 1870–1873 | 95.2M to 93.1M | Deaths on top: `dz` +0.52 to +0.84, with life expectancy about 44 |
| Carnatic | 1940–1979 (39) | 1861–1871 | 20.6M to 16.9M | The census's own deaths (life expectancy 32 to 38, `dz` about +0.15), and a residual of −1.6M in 1979, which takes in states changing hands |
| Hindustan | 1960–1972 (12) | 1866–1869 | 54.7M to 53.3M | The census's own deaths: life expectancy 21 to 26, infant mortality 370 per 1,000, `dz` under +0.08 |
| Satara | 1980–2002 (22) | 1871–1877 | 22.1M to 19.3M | Emigration (100,000 to 166,000 a year), with deaths at or above births |

These calendar years are the 1860s and 1870s. India's real life expectancy then was in the mid-20s, and its people grew
only slowly through the famines. Hindustan's and Carnatic's figures sit near that. Bengal's are the ones that look wrong.

## Bengal and the lines on top (2026-10-11)

**Why Bengal lost people past census 1900.** No war and no devastation: the census line logs neither, and the saves
agree.

- **Severe starvation:** 4.7% of Bengal's people starved severely in 1872. That was 9.3% in East Bengal and 3.4% in
  Bihar, while every other 20M+ country was near 0%. In 1888, Punjab's share was 30%.
- **Pollution:** the owner's tooltip for West Bengal in about 1888 read:
  - Pollution Impact +32%;
  - "+225% from Poshchim Bongo", the census's and fast mode's terms (the save: −41% and +277%);
  - Bengal's −8%, from the technologies the census absorbs and global warming's line;
  - +5% from child labour (absorbed);
  - a ruthless executive's +10% for some buildings' workers (a workplace line, on top).
- **How the engine weighed them:** it adds every line to its bare curve, which the census had cut to about 59% there.
  So the +32% came to +54% of the census's deaths, and a severely starving pop died at about three times the
  census's rate (taking the penalty flat, as the walk then did; the engine scales it by the pop's starvation value,
  0.5–1, so less: "The severe term", below). Poorer states cut further and amplified more: about 2.5× in East Bengal. Across 875 states in 1872,
  states with no severe starvation ran 9% above the census, those with 0–2% of people starving severely 51% above,
  and those with 2–10% 64% above.

**The change (owner, 2026-10-11).** A state-level line left on top now acts on the census's rate: M also takes off
O_s × (1 − target / bare) (plan §2, "Amended 2026-10-11"). A pop's own line stays at its bare curve's weight. The
owner first agreed to scale severe starvation too, but one state-wide M can't scale a pop's line without moving
its neighbours' rates: in Punjab it would have cut the deaths of the 70% who were eating. So starving pops still
die at a multiple of the census's rate (about three times with the flat penalty assumed here; less at the engine's
scaled one). Taming famines further would be a separate decision: absorbing severe
starvation per pop at a chosen size, as mild starvation is.

**What `predict` says, now with Pollution Impact read from each save's region pollution** (an approximation, about
a quarter high: `P.POLLUTION_HEALTH_MORTALITY`):

| The six normal-speed gate saves, 1837–1887 | Multiple to 1900 | 20M+ countries shrinking |
|---|---|---|
| Before (no pollution in `predict`, lines on top at the bare curve's weight) | ×1.663 | none |
| Pollution, at the bare curve's weight | ×1.628 | none |
| Pollution, acting on the census's rate (this change) | ×1.642 | none |

| Fast-run save, with the census's stored rates | Bengal, before | Bengal, after | Its deaths on top, per 1,000 |
|---|---|---|---|
| 1872 | −0.15% a year | +0.36% | 12.8 → 7.7 |
| 1889 | +0.42% | +0.92% | 7.5 → 3.4 |

Satara still shrinks in the 1872 save, from emigration, which `predict` doesn't model. At normal speed the change moves
the 19th century little; the fast run's Bengal was extreme because fast mode's 4× population meets a calendar-1870s
economy.

## The in-game session (owner, 2026-10-11)

A new 1836 game as Britain on Full, with #885 deployed. A revolt took London, so the capital is the Midlands. The
console's lines are in `debug.log`.

- **P3, the first step (6 January 1838).** M is in force: births −0.3204, deaths −0.4034. The step-to-step scales
  and the target are 0, as a first step's are. The logged inputs reproduce both terms exactly:
  `tb − 1 − rep − os × (1 − tb)` gives 0.6766 − 1 + 0.0178 − 0.0459 × 0.3234 = −0.3204 and 0.6175 − 1 − 0.0154 −
  0.0145 × 0.3825 = −0.4034.
- **P2, the tooltips.** Births match exactly: Census: Births −32.0% and Cadet Sons Leave the Land +4.6% (the
  Midlands' one state-level birth line, on top) make −27.4%. A pop's mortality tooltip lists:
  - Standard of Living (the bare curve);
  - "+5% from Great Britain", its class's child labour line, absorbed per pop;
  - Pollution Impact +0%;
  - Ministry of Health −2%;
  - "−40% from Midlands", the census's term.

  Britain carries no law or technology birth line in 1838. No error from the census code.
- **Impact of Institutions (finding, fixed in the follow-up).** The Ministry of Health's line read "A multiplier of
  0.94": the engine scales an institution's lines by the state's Impact of Institutions (`state_institution_impact_add`:
  Local Vernacular −0.05, obstinance −1.0 × its share). The census cancelled them at full size, so in a fully
  obstinate state at Ministry of Health level 5 it would have taken off 15% the engine never applied. The absorbed
  institution lines now take `te_demog_institution_impact`. The Ministry of War's per-institution country modifier
  (`country_institution_impact_institution_ministry_of_war_mult`, a mod law and a production method) is not handled:
  how it combines with the state's is unverified, and it touches only Mandatory Augmentation's line. The impact's sources:
  Local Vernacular −0.05, Devolution −0.05, Ubiquitous Translation +0.10, the Consciousness Network method +0.10,
  and obstinance −1.0 × its share. The floor at 0 is unverified: full obstinance with Local Vernacular reaches
  −1.05, so the census would differ by at most about 0.5 points if the engine doesn't clamp. Console option l now
  logs `impact=`; the Midlands should read 0.940. The offline tools assume impact 1. `predict`'s growth is
  unaffected, since an absorbed line cancels on both sides. Its absorbed-group points and the clamp's bound are off
  in low-impact states, and so is `fidelity`'s comparison of the census's institution-carried inputs, which the game
  reads already scaled.
- **P3, the second step (29 January 1839).** The terms move little: births −0.3214, deaths −0.4216, following
  the bare curve's 3% rise. Births on top `bz` +0.044 match Cadet Sons' +4.6%. Deaths on top `dz` +0.117:
  - +0.008 is the state-level lines;
  - about 5% of the bare curve is each pop's own lines (workplace mortality for laborers and machinists, severe
    starvation for 0.4% of people), which stay at the bare curve's weight. That is about +8% of the census's rate;
  - about 3% is the base rate moving between yearly steps.

  So P3's "a few per cent" holds for births and for agrarian states, not for an industrial state's deaths.
- **P6.** Private Health Insurance's mortality line is proportional to each pop's wealth (owner). Absorbing it per
  pop under Full can be built.
- **The replay.** Three capitals: the Midlands (2.55M people, children per woman 5.0, infection ×0.38), a poor one
  (0.79M, 5.9, ×1.39) and one between (2.58M, 5.3, ×0.90). The worst slot error is 0.00% in each, against the 0.1%
  tolerance.
- **Option d's benchmark** (the 1887 gate save, 838 states; the rule switched mid-game; one-second timestamps):
  | Setting | Walk, three passes | Step, three passes |
  |---|---|---|
  | Display only (`full=0`) | about 2 s | about 8 s |
  | Full (`full=1`) | about 3 s | about 8 s |

  The absorbed sums cost at most about 0.3 s a world-year, spread over the year's state pulses. Final review 2's m6
  (folding the absorbed terms into the pop multipliers) stays deferred.

## The moved lines (owner, 2026-10-11)

Every birth and mortality line on a law, technology or institution now sits on a script-only type
(`docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md`).
- **Without the census** (rule off, Display only, or Full before a state's first step), the lines reach each state as
  Laws and Institutions.
- **Under Full,** the census models the absorbed family and applies the on-top family at its rate.

`predict` on the six normal-speed gate saves still gives ×1.64, with no 20M+ country shrinking. Its growth doesn't
change, because an absorbed line cancelled on both sides before, and no on-top family line is held between 1837 and 1887.

## The normal-speed Full run (2026-10-11)

- **The run:** a new 1836 game on main at ec304526 (#885's lines on top at the census's rate, #889's Impact of
  Institutions; before #892's moved lines), Demographics on Full, observed, census log on, fast mode off, from 13:11.
  - It crashed at 13:59, when a script-value hot deploy hit it, and the owner resumed from the 1853 save.
  - It ran to 1 January 1901; the gate reads to there, though the archive's last autosave is 1 January 1902.
  - The archive has 66 yearly autosaves and every log generation, in `/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/`.
- **The tools ran from a checkout of that build** (`git worktree add --detach … ec304526`). #892's `predict` would read
  these saves wrongly.

| Check | Threshold | Result |
|---|---|---|
| World 1836–1900, logged countries | ×1.3–×1.7 | **×1.92, fail** (913M to 1,752M). Inflated: the logged countries of a million or more went from 81 to 101 as colonized land came under the census. The saves, which count every state, give **×1.77** (1,031M in 1837 to 1,822M in 1901). That is still above the band |
| No 20M+ country losing people ten years running outside wars | none | **Pass** |
| Share of people in clamped states | under 1% | 0.00% |
| Closed Borders `mig_raw` median | within ±1 per 1,000 | **+0.18 (+0.29 weighted), pass,** over 1,500 country-years (1901 save) |
| P4: census modifiers kept | none missing | **Pass** (1901 save) |
| P3's pollution half: `te_dg_os_d` follows Pollution Impact | close | **Pass.** By the region's pollution (1901 save, states over 200,000 people): 25–50, `os_d` +0.080 against `predict`'s line +0.089 (19 states); 50–100, +0.177 against +0.151 (5 states) |
| India in the 1860s–1880s (item 5) | no collapse | **Pass.** India's states grow from 178M (1837) to 294M (1901), births less deaths +0.90% a year. British India's 1900 census: CBR 41.4, CDR 32.7. No Indian state is in severe starvation in 1901 |
| Errors | none from the census | **None in a census file.** Six lines come from the Demographics tab's scripted GUI evaluated with no country (`te_system_tab_sguis.txt:278`, `:286`, observer mode), which is harmless (#894). The rest is vanilla, plus the known `contagion_crash` lines |

**Where the growth comes from.** Each region's people (every pop, by its state's strategic region) are taken at five-year
saves. Births less deaths is the census's own count (`te_dg_births − te_dg_deaths` over `te_dg_people`, averaged
between saves). "Other" is the rest: net migration, war losses and rounding.

| Region | 1837 | 1901 | × | % a year | births less deaths | other | CBR/CDR 1872 | CBR/CDR 1901 |
|---|---|---|---|---|---|---|---|---|
| China | 353M | 529M | 1.50 | +0.63 | +0.67 | −0.04 | 42.2/34.0 | 43.2/39.8 |
| India | 178M | 294M | 1.65 | +0.79 | +0.90 | −0.11 | 41.3/34.4 | 41.5/33.0 |
| Western, northern, central, southern Europe | 149M | 245M | 1.64 | +0.78 | +1.07 | −0.29 | 37.5/25.9 | 33.1/27.2 |
| Africa | 73M | 127M | 1.73 | +0.85 | +0.79 | +0.06 | 40.2/31.1 | 39.2/31.1 |
| USA, Canada | 19M | 116M | 6.04 | +2.81 | +1.34 | +1.47 | 37.5/24.5 | 36.1/22.4 |
| Eastern Europe, Balkans | 59M | 100M | 1.70 | +0.83 | +1.06 | −0.23 | 40.6/29.8 | 37.6/29.2 |
| Japan, Korea, Manchuria | 64M | 97M | 1.52 | +0.65 | +0.52 | +0.13 | 40.8/38.8 | 38.1/39.1 |
| Russia, Siberia | 35M | 74M | 2.14 | +1.19 | +1.04 | +0.14 | 40.8/31.4 | 39.0/30.3 |
| Middle East, Central Asia | 38M | 72M | 1.90 | +1.01 | +0.84 | +0.17 | 41.4/33.9 | 40.8/31.9 |
| South America | 14M | 58M | 4.19 | +2.24 | +1.07 | +1.17 | 36.4/24.6 | 34.6/23.4 |
| Southeast Asia | 36M | 57M | 1.58 | +0.72 | +0.78 | −0.07 | 42.1/34.3 | 38.7/30.2 |
| Mexico, Central America | 12M | 48M | 3.98 | +2.16 | +1.18 | +0.98 | 40.4/28.0 | 38.7/29.7 |
| **World** | **1,031M** | **1,822M** | **1.77** | **+0.89** | **+0.86** | **+0.03** | 40.6/32.0 | 39.4/32.9 |

**Against history (owner, 2026-10-11: compare fairly, allowing for what the game didn't have).** These are rough
multiples for 1836–1900, interpolated from Maddison's 1820, 1870 and 1913 estimates. Ranges are wide:

| Region | History | Notes |
|---|---|---|
| World | about ×1.45 | Rises to about ×1.6 without the two collapses below |
| China | about ×1.0 | The Taiping (1850–64), Dungan and Nian revolts and the 1876–79 famine. A China that kept its pre-1850 pace makes about ×1.3–1.4. **This run had no Taiping state** |
| India | about ×1.3 | Famines in 1837–38, 1866–70, 1876–78 and 1896–1900 |
| Western Europe | about ×1.6 | |
| Eastern Europe | about ×1.7 | |
| Russian Empire's lands | about ×2.1 | |
| USA and Canada | about ×4.8 | |
| Latin America | about ×2.5 | |
| Africa | about ×1.45 | |
| Japan | about ×1.4 | |

- **Worldwide, the excess is births less deaths, not migration.** It runs +0.86% a year of the world's +0.89%, against
  history's roughly +0.6%.
- **Europe and Russia match history overall.**
- **Most of the excess against a fair target (about ×1.6) is outside Europe:**
  - **China:** +50M against a China without its collapse, and +175M against real China.
  - **India:** about +60M.
  - **Africa and the Middle East:** about +20M each.
  - **The Americas:** about +70M. Their migration ("other") is about twice history's, and Mexico's births less deaths
    (+1.18% a year) is above its history too. Found since: by peacetime rates against history's range, Mexico's births
    less deaths matches; its excess is migration (below, "Peacetime births less deaths, by region"). These figures
    are growth against a ×1.6 world; that section's are births less deaths against the middle of history's range, so
    the two sets differ (India +60M here, +37M there; the Middle East +20M, +11M).
- **Europe's deaths move the wrong way.** Its CDR rises from 25.9 (1872) to 27.2 (1901), where history's fell from
  about 24 to 19.
  - Germany's 1900 census has CDR 33.4 above CBR 31.2 (history: about 22 and 36).
  - In ten German states the engine adds 60–100% more deaths than the census's target (`dz` +0.6 to +1.0), with M at
    −0.55 and nothing on top at state level.
  - None is in severe starvation at the 1901 save. One German state was fully starving in 1891, so a famine during
    1900 is possible, but the cause isn't established (#894). Found since: an in-game famine (below, "Germany's 1900
    deaths").
- **China was in a famine at the end:** 26 states and 273M people at 10% or more severe starvation in the 1901 save.

**Not tuned here.** Changing the gate's measure to the saves, and setting its band for what didn't happen, are #894's
items, and so are the regional rates and Germany's deaths. The fast run's ×1.63 didn't show any of this, because its
census years ran on the 1837–1851 economy.

## #894's analysis of the normal-speed run (2026-10-11)

Two analyses of the run's 66 yearly saves (about 52,000 census state-years), for #894. Scripts and extracts are kept
beside the run's archive (`session-notes-2026-10-11/germany-famine-analysis/` and `regional-rates/`).

### The gate's measure

`demographics_observer_report.py --phase2 --saves SAVE…` now judges the world's multiple from every pop in the
earliest save and the save nearest 1 January after `--to-year`; the census log's figure prints as a second line, not
judged. The band (`--band`) defaults to ×1.40–×1.65: history as it happened (Maddison 2020: ×1.39 from 1836 to 1900, rounded to
the floor's ×1.40; 2010's figures gave ×1.45) up to history without its catastrophes (the owner's estimate, about ×1.6–1.65). On this
run: ×1.77 from the saves (1,031M to 1,822M), ×1.92 from the log. **Fail.**

### Peacetime births less deaths, by region

A state-year is peacetime when its owner is at no war at either save around the step, its devastation is under 5 (of
100), its radicals are under a quarter of its people, and it has no famine record and under 10% of its people in
severe starvation. War dead never enter the census's deaths (they come off after deaths accumulate), so war moves
these rates only through devastation. Per 1,000 a year, 1837–1901:

| Region | Peacetime (share of person-years) | All years | Peacetime CBR/CDR | Growth | Other (migration and the rest) | History, normal years |
|---|---|---|---|---|---|---|
| China | +6.5 (85%) | +6.2 | 42.5/36.0 | +6.3 | +0.1 | +3 to +6 without its collapse |
| India | +11.7 (42%) | +9.6 | 41.4/29.6 | +7.9 | −1.7 | +6 to +9 |
| Western, northern, central, southern Europe | +11.1 (42%) | +10.2 | 37.9/26.8 | +7.8 | −2.5 | +8 to +10 |
| Africa | +8.8 (63%) | +8.0 | 40.9/32.2 | +8.5 | +0.5 | +3 to +8 (very uncertain) |
| USA, Canada | +13.6 (31%) | +13.4 | 38.0/24.5 | +28.1 | +14.7 | +17 to +21 |
| Eastern Europe, Balkans | +11.4 (59%) | +10.5 | 40.5/29.1 | +8.3 | −2.2 | +8 to +12 |
| Japan, Korea, Manchuria | +7.8 (75%) | +4.9 | 41.1/33.3 | +6.5 | +1.7 | +2 to +6 |
| Russia, Siberia | +10.8 (72%) | +10.5 | 40.7/29.8 | +11.9 | +1.4 | +10 to +13 |
| Middle East, Central Asia | +8.8 (75%) | +8.6 | 41.5/32.7 | +10.1 | +1.5 | +4 to +8 |
| South America | +11.5 (62%) | +11.3 | 37.8/26.2 | +22.4 | +11.1 | +12 to +16 |
| Southeast Asia | +8.7 (63%) | +7.5 | 42.0/33.3 | +7.2 | −0.4 | +9 to +13 |
| Mexico, Central America | +11.6 (75%) | +11.1 | 39.6/28.0 | +21.6 | +10.5 | +10 to +13 |
| **World** | **+8.8 (63%)** | **+8.5** | 41.2/32.5 | **+8.9** (×1.77) | +0.4 | |

History's figures are rough: Maddison 2020's populations (checked), and recalled registered rates for Europe, the
USA, India, China and Russia (not re-checked). Africa's and the Middle East's are conjectures.

- **The world's excess is in the peacetime rates.** The game's own crises cost the world 0.3 per 1,000 a year;
  history's catastrophes cost about 2.5. Births less deaths alone put the world about ×1.07 above a fair history.
- **Too high:** China (about +55M by 1901), India (+37M, all of it in 1837–62, when its census life expectancy was
  about 30–33 against history's 24–25; from 1882 it is inside history's range), France (+11 against about +2: its
  children per woman run 5.3–5.7 in 1842–72 against a real 3.8, Family Limitation notwithstanding; about +10M),
  Japan and Korea in the early decades (+10 to +11 against Tokugawa Japan's +2 to +3), and probably Africa (+19M) and
  the Middle East (+11M).
- **Too low:** the USA and Canada (CBR 38 against 40–45, CDR 24.5 against 20–22; about −50M before migration),
  Southeast Asia (−14M), South America (−11M) and Great Britain (+8.5 against about +12.5).
- **Matches:** Eastern Europe, Russia, Mexico's births less deaths. **Western Europe is a little high (+11.1 against
  +8 to +10, about +18M), and its near-match is offsetting errors:** France high, Britain low, Germany's famine
  (below), and no Irish famine.
- **Missing catastrophes:** India's famines (the engine recorded 0.54M famine deaths against history's roughly
  15–20M), the Taiping, Ireland's Great Famine, Persia's 1870–72 famine.
- **Migration** (the engine's, outside the census): about twice history's into the USA, four to five times into South
  America, all of Mexico's excess (+33 per 1,000 a year in 1872–77), and an Indian emigration in 1872–77 (−8).
- **What it means for the census:** the fertility gap Late Marriage and Birth Spacing close (#862: Birth Spacing for
  China, Korea, India and Japan, Late Marriage for north-western Europe) is most of the excess. India's early deaths
  are too low. The Americas' shortfall is births as well as deaths.

### Germany's 1900 deaths: a famine

Germany's census CDR of 33.4 in 1900 (39.7 in 1898, 37.3 in 1899) comes from severe starvation in an in-game famine.

- **The famine (measured).** The engine recorded famines starting on 3 December 1897 in the German–Hungarian market:
  sixteen states, twelve of them German, among them four of the ten states with the largest `dz`. Hannover's record
  counts 2,915 famine deaths by 1898.1.1, 32,173 by 1899.1.1 and 55,390 by 1900.1.1, and is gone by 1901.1.1.
- **Who starved (measured).** Unemployed laborers, 30–42% of the people in Germany's industrial states, at food
  security 0, with no social security law. About 40% of Hannover was in severe starvation on 1 January of 1898,
  1899 and 1900; Brandenburg 25–34% (75–87% starving, mild or severe).
- **Why so many deaths (measured, except where marked).** Severe starvation is a pop's own line, which the census
  leaves at the bare curve's weight (§ Bengal above): with M about −0.55, a severely starving pop dies at about three
  times the census's target (assuming the walk's flat +1.0 severe term; the engine scales it, so 2.2–2.6× at these
  pops' starvation values of 0.55–0.70: "The severe term", below). Splitting `dz` into last year's M against this year's, the model's own CDR drifting, state lines on top
  and pop lines on top reproduces the stored `dz` exactly on all 52,315 state-steps that store one; the pop term is
  84–105% of Germany's excess in 1898–1900, and `dz` correlates with the severe share at 0.78–0.97. The absolute
  famine deaths equal the base game's (by design); only their ratio to the census's lower baseline grows. The walk's
  figure for them, with the flat term, ran 1.5–1.7× the engine's (below).
- **Not merging states.** States 1027–1053 all exist in the 1837 save (1,147 state objects at the start; states made
  later take IDs from 16,777,216). Steps after an owner change and steps after a population jump of over 5% each
  carry 1–2% of the world's excess. Stale M is symmetric noise world-wide (+15.8M against −15.6M).
- **World-wide**, starving steps (7% of state-steps) carry 44% of the world's net excess deaths over the census's
  target in 1872–1901. Without Germany, Europe's census CDR is flat at about 26; history's fell from about 24 to 19.

### The ring over-records famine deaths

Over 1897–1901 the census's natural change for Germany fell 3.6M below its baseline while the engine's population
fell 1.5M below its own baseline (its actual change was −280k, −174k and +80k in 1898–1900); the gap reads as immigration (+933k in 1898). Two causes:

1. **The snapshot (measured).** `dz` is measured on the step's day and applied to the whole year that ends there.
   Hannover steps in early February, so its 1898 step booked a mostly pre-famine year as famine.
2. **The severe term (resolved, 2026-10-11).** The walk assumed severe starvation adds +1.0 × the bare curve, a figure
   never fitted: the growth probe had under 1% of people severely starving. The engine's famine counters came to
   0.53–0.67 of the walk's pop-level term (Hannover 29.3k against 43.6k in 1898). Either the engine applies less, or
   pops move between mild and severe within the year; January snapshots couldn't tell which.

   **The engine applies less.** A monthly-save probe played this run's 1898.1.1 save on to 1899.8.1 (19 monthly
   windows; saves, logs and analysis in `/mnt/d/vic3te-data/vic3te-demog-famine-probe-2026-10-11/`, report
   `analysis/REPORT.md`). The engine applies `severe_starvation_penalty` (+1.0 deaths, −0.9 births) × each pop's
   starvation value, clamp((0.4 − food security) × 2.5, 0, 1), as it does the mild penalty. The save stores that
   value per pop as `food_security={ starvation= }`. Three measurements agree:
   - the famine counter matches the scaled form at 1.007 (flat: 0.650) over 240 clean state-months in 25 states;
   - its ratio to severe's bare deaths follows the severe pops' starvation value, R = 0.012 + 0.985 × SV;
   - the population closes month by month under the scaled form: −4.5k unexplained over 225 severe state-months in
     Germany and Hungary, against +305k flat.

   Severe pops sat at food security 0.08–0.19 (starvation value 0.53–0.79), not 0. Flicker isn't the cause: severe
   pops stay severe 86% of months, people-weighted. The walk now reads severe starvation in 0.05 steps of food security,
   as it reads mild (`mod_systems.md`, "Starvation, per pop"). Applied to this run (first order, from 1 January
   snapshots), that takes 377k, 446k and 391k off Germany's 1898–1900 residuals as run, which brings the two
   full-famine windows to about the pre-famine baseline (−249k a year against about −250k). The +556k left in 1898
   is the onset's timing, which the trapezoid addresses.

The same gap shows in Hungary in 1898 and China in 1901. The fixes were #894's: the trapezoid books each window at
the mean of its two ends' rates (#907), and the monthly-save probe above set the severe term in `gen_demographics.py`.

## The probes

| Probe | Question | Answer |
|---|---|---|
| P1 | Are devastation's and pollution's mortality lines inside `modifier:state_mortality_mult`? | **Yes, both (owner, in game, 2026-10-10).** Alentejo: "State Region Devastation +11%", Ministry of Health −2%, total +9%, against option m's logged +0.091. Yorkshire: "Pollution Impact +8%", Ministry of Health −14%, total −5%, against −0.046. The mod's +0.05 pollution line adds to vanilla's (owner). The plan's §1 (E14, E15) records it |
| P2 | Does M cancel what the census absorbs, under Full only? (Amended: the lines stay in the law, tech and institution tooltips by design, the owner's accepted cost) | **Yes (owner, in game, 2026-10-11; "The in-game session" above).** Births match the tooltip exactly; the Ministry of Health's line shows beside Census: Deaths. It also found the institution-impact gap (#889) |
| P3 | Does the engine hit the target? Is M's fixed point stable? | **Yes (2026-10-11; above).** The logged inputs reproduce M exactly at the first step, and the terms move little at the second. `bz` matches the state-level birth line; `dz` adds each pop's own lines at the bare curve's weight |
| P4 | Does a state keep its census modifiers through a change of owner? | **Yes (fast-mode run, 2026-10-11).** `predict --check-modifiers` finds no state missing its modifiers on the 1866, 1876 and 1882 saves, after the East India Company broke up and several revolutions |
| P5 | Turmoil's scaling (conditional) | **Not needed:** in the fast run, turmoil barely tracks the deaths on top (r = +0.06 with `dz`) |
| P6 | Does Private Health Insurance's `state_mortality_wealth_mult` scale by each pop's own wealth? (Labelled P6 because P5 is turmoil's) | **Yes (owner, in game, 2026-10-11):** the line is proportional to each pop's wealth |

## Still to run (owner)

This list is the canonical checklist; the PR body repeats it.

1. **Done: P2, P3, P6, the replay and option d's benchmark** (2026-10-11, above).
2. **Done: the fast-mode gate run** (2026-10-11, above). It passes inside its window, census 1837–1900.
3. **Done: the replay** (above).
4. **The owner's calls on the fast run (2026-10-11):**
   - Europe's flat share: accepted.
   - `--phase2`'s run check now stops at `--to-year`.
   - Bengal's deaths on top past 1900: answered and changed (above, "Bengal and the lines on top").
5. **Done: India at normal speed** (above, "The normal-speed Full run"): no collapse, 178M to 294M.
6. **Done: P6** (above). Then absorbing Private Health Insurance's wealth mortality per pop under Full (owner, 2026-10-10: on top for now; P6 says it can be built).
7. **The moved lines, in game** (a new game after the build is deployed; not the normal-speed run's save, whose old
   census terms come off at its first monthly pulse). Do each "that day" check on the day of the change, before the
   state's monthly pulse would catch it up; if a line lags a day, the hooks need `trigger_event` with `days = 1`.
   - **Disabled:** on day 1 a pop's mortality tooltip in the capital lists Laws and Institutions at the Ministry of
     Health's value, and laborers' tooltips show child labour's line. A law's tooltip reads as before. Enacting Women in
     the Workplace changes the birth-rate line that day. A conquered state shows its new owner's lines the day it
     changes hands. Researching a technology with a moved line (one of the era 7 to 12 medical ones, by console)
     changes the line that day.
   - **Disabled, Private Health Insurance enacted:** a rich pop's mortality tooltip shows a Laws and Institutions line
     for wealth (the first `add_modifier` to carry `state_mortality_wealth_mult`). Note how many Laws and Institutions
     lines a laborer's mortality tooltip shows (deaths, class, wealth): if the repeated name confuses, the class and
     wealth pairs get a qualifier.
   - **Full → Disabled mid-game** (owner: rules can change mid-game): within a month every state's Census: Births and
     Census: Deaths are gone and Laws and Institutions is back; no state shows both.
   - **Full:** after the capital's first census step, the Laws and Institutions lines are gone. Census: Births and
     Census: Deaths are present, and option n's `q_b`, `q_d` and `w` are 0 in 1837.
   - **Private Health Insurance under Full** (debug: enact it, Ministry of Health level 5): Census: Deaths by Wealth on a
     rich pop's tooltip reads about wealth × −0.005 × the census's share (`tb_d` in option n).
   - **`debug.log`:** no error from `te_demog_line_*`, `te_demog_events.4`, `te_demog_lines_law_on_action` or
     `te_demog_engine_line_injections.txt`; in particular no scope error on a law's enactment.
8. **Done: the normal-speed Full run** (above): the gate fails on the world's multiple (×1.92 logged, ×1.77 from the saves); the rest passes. Follow-ups in #894.
