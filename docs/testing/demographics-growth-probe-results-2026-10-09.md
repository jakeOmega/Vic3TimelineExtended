# Demographics growth probe results — 2026-10-09

**Tester:** Jake, repository owner. **Game:** Victoria 3 1.14.5, debug mode (plain-text autosaves).
**Mod revision:** `main` at `7bbf8c8e` (#833) plus the probe, on the local branch `probe/demographics-growth`
(temporary, not for main; last commit `7f8248d2`). **Other mods:** none.

The census measures migration as a residual: a state's population change less the births and deaths it
expects the engine to produce, less war dead and recorded kills. After #833 made the census step, the
second observer run's 1911–1916 census showed net emigration almost everywhere: the world summed to
−6 to −7 per 1,000 a year, and 399 of 448 country-years were negative. That is impossible for migration,
which nets out worldwide. Countries under Closed Borders (vanilla: "No migration in or out of the country is
permitted") showed the same −6.1 per 1,000, so the census's expected births and deaths had to be wrong.
This probe measured the engine's own. The census fix that uses these results is in the same PR as this file.

## The probe

`event te_debug_growth.1`, option a, on a throwaway game:
- **Migration frozen.** Every country gets `country_migration_restrictiveness_add = 101` (no country admits
  migrants) and `state_migration_quota_mult = -1` (no state sends or takes any).
- **Phases on a Latin square.** Every country of 250,000 people or more gets a group from 0 to 7. Every 28
  days it logs one `TE_PG` line per country, and every third tick each country switches to phase
  (block + group) mod 8. The phases:
  - births off (`state_birth_rate_mult` −5) or deaths off (`state_mortality_mult` −5), or both;
  - births or deaths stepped by +0.5 and +1.0 in cycle 1, and by −0.5 and −0.9 in cycle 2.

  48 ticks, about 3.7 years. The first window after each switch is not measured.
- **What each line holds.** Per country: the population, the curve births and deaths (the census's
  `te_demog_pop_engine_births`/`_deaths`) and their splits. From v5 on (`TE_PG v=5`) it also holds each
  mortality modifier the pop is subject to, read per pop through its state, its workplace and its
  workplace's building groups.
- **The analysis.** `scripts/analysis/demographics_growth_probe.py` (`check`, `report`, `pooled`, `deaths`)
  fits all countries and windows at once. `scripts/analysis/archive_probe_logs.sh` keeps every `debug.log`
  generation during a run. Both stay on the probe branch.

## Runs

| Run | Save | Lines | Ticks | Use |
|---|---|---|---|---|
| 1 | new 1836 game | unversioned, 30-day ticks | 2 | discarded: see "Growth timing" |
| 2 | new 1836 game, Great Britain, observed | `v=2` | 48 (1836.1.1–1839.9.7) | births, deaths, timing |
| 3 | `french commune_1949_07_20` (the owner's France game), observed | `v=2` | 48 (1949.7.20–1953.3.26) | births and deaths, late game |
| 4, 5 | the same 1949 save | `v=3`, `v=4` | 0 | aborted: each flooded `debug.log` at tick 0, about 300,000 errors in run 5 (see "Modifier types") |
| 6 | the same 1949 save | `v=5` | 48 (1949.7.21–1953.3.27) | the deaths terms, read per pop |

Every run held its control: with births and deaths both off, the median change was **exactly 0** per
1,000 a month, so migration was frozen and deaths stop at 0.

## Engine facts settled

**Growth timing.**
- Pop sizes change once a week, on the same weekday in every country.
- A state's large changes come 28 or 35 days apart, with small ones in the weeks between. Each pop takes a
  month's growth on the first weekly growth day after its monthly due date.
- So growth lands **12 times a year**, and the census's ×12 a year is right. Every pooled fit put each
  28-day window at 0.98–1.03 of the curves' month × 12/year.
- A 28-day window holds zero or one update per state, so a single country's window is noisy. Fit all
  countries at once.

**Births = curve × max(0, 1 + total), per pop.** The total is the state's `modifier:state_birth_rate_mult`
(which includes country modifiers: the phase-0 probe's Q5), plus two per-pop code modifiers that the state
read does **not** hold:
- `literacy_penalty`, −0.1 × the pop's literacy. Fitted at −0.107 in 1836, but −0.19 once SoL is
  controlled, because literacy and SoL correlate +0.5 there; at −0.101 in 1949, −0.107 with SoL, where SoL
  itself fits 0. The 1836 spread was the confound; the engine's value is −0.1.
- The starvation penalties: severe −0.9 (fitted −0.86 in 1949); mild −0.7 scaled by
  (0.4 − food security) × 2.5, at most 0.5 (vanilla's comment and defines).

The −0.9 step stays linear in 1949 and bends at the floor in 1836, where literate and starving pops reach 0.

**Deaths = curve × max(0, 1 + total), per pop.** The total is the state's `modifier:state_mortality_mult`
plus terms the state read does not hold, all added inside the one total:

| Term (registered keys only) | Share of curve deaths, 1949 |
|---|---|
| The class's `state_<pop type>_mortality_mult` (child-labor laws: +0.05 for peasants, farmers, laborers and machinists) | +4.1% |
| `working_conditions` by workplace group and pop type (vanilla's table: 0.02–0.2) | +1.0% |
| The workplace's `building_group_<group>[_<pop type>]_mortality_mult`, read | +0.7% |
| The workplace's `building_<pop type>_mortality_mult` (production methods: construction laborers +0.1) | +0.5% |
| Severe starvation (+1.0), mild starvation (+0.6, scaled) | about +0.1–0.3% |
| Non-homeland, turmoil, wealth | about 0 |

Deaths against each candidate (pooled, 945 death windows, steps −0.5 to +1.0, 1949):

| Candidate | Deaths ÷ (candidate × 12/year) |
|---|---|
| Curve × (1 + state read): what the census used | 1.065 |
| + every read + severe starvation | 1.027 |
| + the same, with working conditions from the table | 1.024 |

They add rather than multiply. By step, deaths sit at 1.00–1.04 of the full candidate from −0.9 to +1.0,
while the census's formula drifts from 1.06 at 0 to **1.31** at −0.9: the per-pop terms stay whole while the
state's part shrinks. Runs 2 and 3, without the reads, found +5.6% (1836) and +6.4% (1949) over the census.

**What is left.** About 2% of deaths, with no pattern by SoL, literacy, dependents' share, class share or
country size; small countries account for most of the spread. Dependents are not it: they are readable
(`dependents` works as a pop value), but their share of curve deaths fits a coefficient of about 0.

**Modifier types.**
- `modifiers.log` lists about 1,100 mortality keys, but only **72** are registered in vanilla's and the mod's
  `modifier_type_definitions`.
- An unregistered key fails in a static modifier (`Unknown modifier type` at load). A `modifier:<key>` read
  of it gives `'none'` and logs `Value of wrong type … Got value of type 'none'` on every pop, every time it
  runs. That flooded runs 4 and 5 at tick 0.
- Nothing can set an unregistered key, so it is 0 everywhere. Read registered keys only.
- A registered key that nothing sets reads **0**. The probe's reads all had a 0.00001 carrier behind them,
  so the census fix's first launch settled it: the new census read the same keys for every pop at the start
  of an 1836 game and logged no `Value of wrong type` lines.

**What a building's modifier read sees.** The capital's buildings read 0 for
`building_group_bg_*_laborers_mortality_mult` where the `working_conditions` table gives 0.05–0.1. So the
engine applies working conditions where a building read can't see them, and the census takes them from the
table, by the workplace's group and its ancestors. Building reads of production-method keys
(`building_laborers_mortality_mult`) do work.

## Before the fix, measured three ways

- **Census lines** (run 2's game after #833, 1912–1916): net migration per 1,000 a year was −6.1 under
  Closed Borders (141 of 150 country-years negative), −6.2 under Migration Controls and −5.3 under No
  Migration Controls.
- **Plain-text autosaves:** world growth over the curves without modifiers was 0.81 in 1836 (one month) and
  0.45 in 1917 (three months, war included). Under Closed Borders, the curves alone missed actual growth by a
  median of about −0.4 per 1,000 a year in 1836 and about −1 in 1917.
- **The census's own estimate** missed it by −3.4 (1836) and −6.5 (1917): it multiplied births by the state
  read (×1.05 in 1836, ×1.09 in 1917) and left out every per-pop term.

## Open

- Turmoil (`state_mortality_turmoil_mult`) and wealth (`state_mortality_wealth_mult`) mortality: the scaling
  of "per Turmoil" and "per Wealth" is unknown, and both measured about 0. They are left out of the census
  (the private health insurance institution's −0.002 per wealth level is the main source).
- The remaining ~2% of deaths.
- `WORKING_ADULT_RATIO_SKEW_MAXIMUM = 1000000` in the mod's defines (vanilla 2.0): its effect is not
  measured.
- The mod's `INJECT` on `state_region_pollution_health` adds −3 SoL on top of vanilla's −3 per unit of
  pollution impact; probably unintended.
- The mod's `malnourishment` static modifier (births −0.1 per SoL level below equilibrium) is defined but
  nothing applies it, and vanilla has no such code modifier.
- Resettlement transit deaths and the space-race event kills are not recorded with `te_demog_note_kills`, so
  the census reads them as emigrants.
- `demographics_observer_report.py` keeps one line per tag and year in its country table, so a civil war's
  two same-tag countries show as one (Japan read 6.6 million in 1916).
