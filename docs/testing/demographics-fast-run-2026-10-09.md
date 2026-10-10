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
| Britain 1836 (Charitable, level 1) | 43.8 / 140 / 12.8 / 570 | 39.8 / 169 / 12.5 / 670 | IMR 150–250, e0 35–43, e65 10–14 |
| Britain 1900 (Charitable, level 2) | 53.5 / 77 / 13.6 / 285 | 45.9 / 126 / – / – | IMR 120–170 (real ~150), e0 44–52 (real ~47) |
| West 1950 (Public, level 3) | 68.2 / 17 / 16.9 / 67 | 62.1 / 32 / 14.5 / 129 | IMR 20–55 (UK 31), e0 60–71, e65 12–16 (UK 13.9), MMR 30–150 (UK ~87) |
| West 1990 (Public, level 4) | 75.0 / 10 / 20.5 / 34 | 73.4 / 5.7 / 18.7 / 6.7 | IMR ≤ 12 (UK 7.9), e0 72–80, e65 15–20 |
| Rich today (Public, level 5) | 76.8 / 9.7 / 21.5 / 34 | 77.5 / 5.6 / 21.7 / 6.7 | IMR ≤ 6, e0 77–84, e65 18–23, MMR ≤ 15 |
| India 1975 (Charitable, level 1) | 59.6 / 38 / 13.8 / 114 | 47.2 / 113 / – / – | IMR 110–150 (real ~130), e0 46–56 (real ~50) |
| Medicine to era 8, no health system | 62.9 / 34 / 16.0 / 67 | 48.2 / 111 / – / – | IMR 70–130, e0 48–60 |
| Public Health Insurance before antibiotics, gain in e0 | +8.3 | +1.8 | 0.5–3 (the spec's stage-1 gate) |

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

- **Access:** a base of 0.4, plus 0.04 a Health System level under Charitable, 0.10 under Private and 0.15 under Public, up to 1.
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

## Health-law adopters against their peers (stage 1's gate)

`demographics_harness.py adopters SAVE...` takes each country with a health law in a save and compares the model's e0 for its incorporated states with the median of countries with no health law within ±1.5 standard of living and ±0.1 literacy. The figures come from the save's own inputs, not the census lines, because Public Health Insurance also raises standard of living. The values are this fit's.

| Save | Charitable: median gain (countries) | Public: median gain (countries) |
|---|---|---|
| gate 1837 | +0.5 (5) | – |
| gate 1847 | +0.3 (10) | – |
| gate 1857 | +0.1 (16) | – |
| gate 1867 | +0.5 (19) | +0.6 (3) |
| gate 1877 | +0.6 (31) | +1.2 (6) |
| gate 1887 | +0.6 (32) | +1.2 (7; largest BEL +3.4 at level 3) |
| fast 1845 (census ~1937) | +0.2 (9) | +0.8 (8) |
| fast 1850 (census ~1997) | +2.1 (11) | +6.0 (9) |
| fast 1855 (census ~2057) | +1.3 (43) | +7.9 (12) |
| fast 1860 (census ~2117) | +1.4 (42) | +4.4 (11) |

- **The gate passes.** The 1860s–80s adopters of the normal-speed run gain 0.6–1.2 years at their standard of living. The old tables' census lines gave e0 54–56 against peers' 43.
- **Once medicine exists, access matters a lot.** In the fast run's late saves, Public Health Insurance at level 4 gives 15–17 years over no system (BEL, PEU, NBS); at level 1 it gives 3–4. Universal care against none at the same low income is about Sri Lanka or Kerala against Pakistan in the 1970s, 10–15 years. Whether the full gap should be that large is an owner call (the PR body).

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
