# Demographics fast run and the stage-1 calibration (2026-10-09)

The first fast-mode run (#848) and what it showed about the census's medicine. These are
the findings behind stage 1 of the modifier-types design
(`docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md`, plan
`docs/superpowers/plans/2026-10-09-demographics-modifier-types-stage1.md`).

## The run

- A new 1836 game on main 3d5e5807, observed. The census log was on (`te_debug_demog.1` b) and fast mode was at 12x (option j).
- One census year passes per game month, and every line carried `lag=0`. Census year 2124 came at game 1860.1.1.
- **The game ran to December 1872** (census year 2279).
- **Data:** `/mnt/d/vic3te-data/vic3te-demog-fast-data/`.
  - 24 yearly autosaves, 1837–1860.
  - Every log generation to 19:56, plus the generations from 21:41 to 22:20 (game 1869–1872).
- **Lost:** the archive filled the C: drive at 19:56, because WSL's disk is a file on C:. Logs from 19:56 to 21:41 (census years about 2124–2230) and the saves from 1861 to about 1869 are missing. A 20:05 save copy was cut off at 8 MB and is kept as `*.truncated-disk-full`.
- **The gate run's saves** (normal speed, 1837–1887) are in `/mnt/d/vic3te-data/vic3te-demog-gate-data/`.

**Runtime errors:** none from the demographics code. The only `te_dg_*` lines are the load-time "set but never used" notices.

## What fast mode is

Births, deaths, research and construction run 12 times faster. Standard of living, literacy, laws and pop wealth keep the calendar. So census year 2124 is an 1860 society with every medical technology up to era 8, and that explains the run's shape:

| Census year | World TFR | World e0 | 0–14 | 65+ |
|---|---|---|---|---|
| 1850 | 5.92 | 36.7 | 39.9% | 4.4% |
| 1900 | 5.78 | 43.8 | 40.7% | 4.6% |
| 1950 | 5.65 | 44.3 | 40.6% | 4.3% |
| 2000 | 5.50 | 49.3 | 40.7% | 4.5% |
| 2050 | 5.45 | 58.1 | 42.4% | 4.1% |
| 2124 | 5.05 | 61.9 | 40.6% | 4.9% |

- **Fertility stays near 5 to the end:** GBR 4.40, FRA 3.68. Fertility follows standard of living, literacy and the means, and fast mode speeds none of them except the contraception techs, which literacy holds back.
- **Gini runs away in the rich industrial countries,** as in the gate run: GBR 0.53 in 1837, 0.78 in 2124.
- **Migration passes the gate.** On every third fast save, the Closed Borders check (`demographics_observer_report.py --closed-borders`) gives a `mig_raw` median of −0.41 per 1,000 over 10,922 country-years (weighted −0.39): PASS.

## What it showed about medicine

Laws unlock early through technology: `pharmaceuticals`, era 2, unlocks Public Health Insurance. So the AI adopted the health laws within the run.
- **Adopters by 1860.1.1:** 11 Public Health Insurance (NET 1839.1, BEL 1839.2, SAR 1839.7, D08 and D09 1841, PEU 1844, BTN 1849, GER 1850.5, AFG 1850.11, D60 1851, NEJ 1853) and 43 Charitable. None chose Private Health Insurance.
- **The old tables' gap.** In the census lines, the median e0 of PHI adopters with all eight medical techs ran far ahead of countries with no health system:

| Census year | PHI adopters | No health system |
|---|---|---|
| 1900 | 53.5 | 44.2 |
| 1950 | 53.6 | 44.8 |
| 2000 | 61.6 | 52.5 |
| 2075 | 64.9 | 59.5 |
| 2124 | 67.3 | 62.0 |

- **The two faults** behind it, with the old tables (`TECH_MULT`, `LAW_MULT`, `INSTITUTION_MULT`):
  - **A health law worked without medicine.** Public Health Insurance cut infection 25%, maternal deaths 50% and chronic deaths 25% in 1839, with no medicine to deliver.
  - **Medicine worked without a health system.** Countries with no health law reached IMR 39 (from 135) at 1860-level standard of living. Poor countries with imported medicine and no health system had 100–120 in 1980.

Access × treatment fixes both: treatment comes from the techs, and access from the health law's institution level in incorporated states, on a base of 0.4.

## The calibration

`demographics_harness.py medicine` runs eight scenarios against §2.4's anchors and history and exits 1 if any is out of band. "Old" is main 3d5e5807's tables on the same inputs.

| Scenario | Old: e0 / IMR / e65 / MMR | Now: e0 / IMR / e65 / MMR | Bands |
|---|---|---|---|
| Britain 1836 (Charitable, level 1) | 43.8 / 140 / 12.8 / 570 | 39.8 / 170 / 12.5 / 670 | IMR 150–250, e0 35–43, e65 10–14 |
| Britain 1900 (Charitable, level 4) | 54.8 / 69 / 13.7 / 285 | 46.1 / 125 / – / – | IMR 120–170 (real ~150), e0 44–52 (real ~47) |
| West 1950 (Public, level 5) | 68.5 / 15 / 17.0 / 67 | 62.9 / 28 / 14.6 / 97 | IMR 20–55 (UK 31), e0 60–71, e65 12–16 (UK 13.9), MMR 30–150 (UK ~87) |
| West 1990 (Public, level 6) | 75.3 / 9.3 / 20.6 / 34 | 73.4 / 5.7 / 18.7 / 6.7 | IMR ≤ 12 (UK 7.9), e0 72–80, e65 15–20 |
| Rich today (Public, level 8) | 77.1 / 8.4 / 21.6 / 34 | 77.5 / 5.6 / 21.7 / 6.7 | IMR ≤ 6, e0 77–84, e65 18–23, MMR ≤ 15 |
| India 1975 (Charitable, level 1) | 59.6 / 38 / 13.8 / 114 | 47.0 / 114 / – / – | IMR 110–150 (real ~130), e0 46–56 (real ~50) |
| Medicine to era 8, no health system | 62.9 / 34 / 16.0 / 67 | 48.2 / 111 / – / – | IMR 70–130, e0 48–60 |
| Public Health Insurance at level 3 before antibiotics, gain in e0 | +8.3 | +1.2 | 0.5–3 (the spec's stage-1 gate) |

**Ministry of Health levels.** The top level comes from technology alone. The base game's medical_degrees, pharmaceuticals, quinine, malaria_prevention and antibiotics give the first five; the mod's modern_pharmaceuticals, mrna_therapeutics, telemedicine and personalized_medicine give the next four. A country that invests fully can reach:
- level 1 in 1836;
- 4–5 by 1900;
- 5 by 1950;
- 6 at era 8;
- 8 at era 10;
- 9 at era 11.

The scenarios sit near those tops.

**The fit:**

| Carrier | Infection | Maternal | Chronic |
|---|---|---|---|
| medical_degrees (era 1) | 0.03 | | |
| pharmaceuticals (2) | 0.07 | | |
| modern_nursing (3) | 0.08 | 0.35 | |
| antibiotics (5) | 0.40 | 0.60 | |
| modern_vaccines (6) | 0.25 | | |
| antibiotic_mass_production (7) | 0.11 | | |
| modern_pharmaceuticals (8) | | 0.04 | 0.30 |
| telemedicine (10) | | | 0.20 |
| personalized_medicine (11) | | | 0.20 |
| Cap | 0.95 | 0.99 | 0.80 |

- **Access:** a base of 0.4, plus 0.03 a Ministry of Health level under Charitable, 0.06 under Private and 0.10 under Public, up to 1.
  - Public reaches full access at level 6, era 8's top. West 1990's anchors need that: infant mortality about 8 and maternal deaths about 10 a 100,000 can't be reached at access 0.85.
  - Private reaches 0.94 at level 9, and Charitable 0.67, so their extra levels keep adding access.
  - Levels 7–9 under Public add nothing to access; their other per-level effects (the base game's mortality cut, standard of living) are unchanged.
- **The other terms:**
  - combustion engine +0.3 external;
  - Local, Dedicated and Militarized Police −0.05, −0.1 and −0.1 external;
  - Child Labor Allowed +0.1 work;
  - Workplace Safety −0.1 work a level;
  - Consumer Protection −0.08 external a level;
  - Old Age Pension −0.05 chronic;
  - every plain term floored at 0.2.

  These have no anchor. They copy the old compounding curves near level 5.

**Notes on the fit:**
- **Medicine before antibiotics is small.** It totals 0.18. Britain's infant mortality in 1900 was still about 150, and the model's standard-of-living and literacy terms already bring it to 137 with no medicine at all.
- **Chronic treatment starts at era 8.** §2.4 says most of the gain at 65 came after 1970. Lines on earlier techs push West 1950's e65 past Britain's 13.9; the model gives 14.5 with none.
- **West 1950's e0 band starts at 60, not 64, and the cause is not medicine.** At West 1950's inputs the model's deaths at ages 25–45 are 5.2–8.7 per 1,000 a year, against Britain's 1.2–4.5 in 1950; at 65 and 75 they match. Young adults' chronic and external base schedules don't fall before 1970. They are 1836 rates that phase 2's base-schedule calibration should revisit.
- **Every 1836 country with `medical_degrees` moves a little.** That is most of them. Infection at a base access of 0.4 is ×0.99, where the old table gave ×0.9. Britain's 1836 IMR goes from 140 to 169.

## Health-law adopters (stage 1's gate)

`demographics_harness.py adopters SAVE...` takes each country with a health law in a save. It gives the model's e0 for the country's incorporated states, read from the save's own inputs (the census line has no standard of living, and Public Health Insurance also raises it). It compares that e0 two ways:
- **The law's own effect:** the same country without its health law and Health System level. This is the gate's measure.
- **The gap to peers:** the median of countries with no health law within ±1.5 standard of living and ±0.1 literacy. That gap also carries the peers' other differences (techs, urban share, other laws), and some adopters have no peer close enough (GBR and SAR in 1887).

The values are this fit's; the figures are medians (years, countries).

| Save | Charitable: own effect / peer gap | Public: own effect / peer gap |
|---|---|---|
| gate 1837 | +0.0 / +0.5 (5) | – |
| gate 1847 | +0.0 / +0.3 (10) | – |
| gate 1857 | +0.0 / +0.1 (16) | – |
| gate 1867 | +0.1 / +0.6 (19) | +0.2 / +0.5 (3) |
| gate 1877 | +0.1 / +0.5 (31) | +0.6 / +0.9 (7) |
| gate 1887 | +0.1 / +0.5 (32) | +0.4 / +1.0 (9) |
| fast 1845 (census year ~1944) | +0.1 / +0.2 (9) | +0.4 / +0.5 (8) |
| fast 1850 (~2004) | +0.6 / +1.6 (11) | +2.1 / +4.3 (9) |
| fast 1855 (~2064) | +0.8 / +1.0 (43) | +2.7 / +4.1 (12) |
| fast 1860 (~2124) | +0.8 / +1.1 (42) | +2.9 / +3.1 (11) |

- **The gate passes on both measures.** The spec's gate is "within about 3 years of their peers' life expectancy at the same standard of living": the peer gap.
  - **Peer gap:** the median by save for Public Health Insurance is +0.5 to +1.0. The level-3 adopters range from +0.8 to +2.8; the top is BEL in 1887, against three peers.
  - **The law's own effect:** +0.2 to +0.6 by save. Every level-3 adopter (GBR, SAR, SWE, BEL in 1887) gains +1.1 to +1.2.
  - **Before:** the old tables' census lines had the 1870s adopters at e0 54–56 against peers' 43.
- **The gate's first condition is not met as written.** "A fresh 1836 census is unchanged where no carrier applies" holds for a state with no carrier, which `TestMedicine.test_no_carrier_is_exactly_the_base` pins. But most 1836 countries hold `medical_degrees`, so their census moves: infection ×0.99 at base access, where the old table gave ×0.9.
- **Once medicine exists, access matters a lot.**
  - In the fast run's late saves, Public Health Insurance at level 4 gives 8 to 11 years over the same country with no health law (BEL, NBS, PEU), and PEU at level 5 gives 17; at level 1 it gives 2–4.
  - Universal care against none at the same low income is about Sri Lanka or Kerala against Pakistan in the 1970s, 10–15 years.

## Reproduce

```bash
cd <checkout>
D=/mnt/d/vic3te-data
python3 scripts/analysis/demographics_observer_report.py $D/vic3te-demog-fast-data/logs/debug*.log --top 15
python3 scripts/analysis/demographics_observer_report.py $D/vic3te-demog-fast-data/logs/debug*.log --top 5 \
    --closed-borders <every third fast save>
python3 scripts/analysis/demographics_harness.py medicine
python3 scripts/analysis/demographics_harness.py adopters <saves>   # ~30 s a 400 MB save from D:
```

In zsh, split a list of saves with `${=saves}` or an array, or the report sees one path.
