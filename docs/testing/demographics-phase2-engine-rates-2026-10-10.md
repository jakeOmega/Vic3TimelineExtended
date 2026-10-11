# Demographics phase 2 step 4: probes and gate results (2026-10-10)

The gate of phase 2 step 4: the census sets the engine's births and deaths
(plan `docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md`, Task 12; PR #869). This records the
offline half, run on this date, and leaves room for the in-game half, which needs the owner.

**Status: the offline gate fails on the world multiple (×1.78 against ×1.3–×1.7); no 20M+ country shrinks.** This is
the second run, after the owner's amendment of 2026-10-10 (the census cancels what it absorbs through M, under Full only,
and absorbs mild starvation; #881 took the LGBTQ+ Rights laws' birth lines away). With mild starvation absorbed, the
engine runs within 0.1 per 1,000 of the census in every save, so the multiple is now the census's own: its rates alone
chain to ×1.80. China no longer shrinks (+0.23% in 1887, +0.26% in 1877). Per the plan, the fix is calibration, and a
retune is the owner's call, so this stops here and reports candidate parameters (below, "The multiple"). The first
run (before the amendment) passed the multiple at ×1.66 and failed on China at −0.09% in 1887. The in-game probes and
the fast-mode run are still to do.

**Release precondition (owner, 2026-10-10, amended):** nothing changes outside Full. Step 4 edits no carrier; step 5's
retune of the global defines would change every game, so it can't ship while the rule defaults to Disabled (an open
question).

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
| World multiple, 1837–1900 | ×1.3–×1.7 | **×1.78, fail** (the census's own rates: ×1.80) |
| No 20M+ country predicted to shrink | none | **pass:** China +0.23% a year in 1887, its lowest |
| Share of people in clamped states | under 1% | 0.0% in every save |
| The unittest suite, `ruff`, tabs, `organize_loc --check`, `gen_demographics.py --check`, the CI audits | all clean | see the PR |
| Medicine scenarios (`medicine`) | each in its band | all in band |
| Fertility scenarios (`fertility`) | each in its band | all in band |

**The world, save by save** (% a year; the terms on top in births and deaths per 1,000; the absorbed groups in points of
world growth a year, what absorbing each adds against leaving it on top):

| Save | People | Census | Predicted | On top: births | On top: deaths | Child labour | Women's rights | Health laws | Mild starvation | Starving slope |
|---|---|---|---|---|---|---|---|---|---|---|
| 1837 | 1,031M | +0.95 | +0.93 | −0.09 | +0.17 | +0.217 | −0.234 | −0.004 | +0.020 | 0.036 |
| 1847 | 1,133M | +1.07 | +1.07 | −0.02 | +0.04 | +0.212 | −0.234 | −0.005 | +0.031 | 0.069 |
| 1857 | 1,244M | +0.94 | +0.94 | −0.02 | +0.07 | +0.216 | −0.235 | −0.006 | +0.086 | 0.112 |
| 1867 | 1,365M | +0.92 | +0.92 | −0.00 | +0.02 | +0.215 | −0.234 | −0.013 | +0.096 | 0.132 |
| 1877 | 1,458M | +0.86 | +0.82 | −0.14 | +0.26 | +0.214 | −0.234 | −0.027 | +0.154 | 0.157 |
| 1887 | 1,542M | +0.86 | +0.83 | −0.08 | +0.14 | +0.213 | −0.232 | −0.040 | +0.184 | 0.174 |

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
- **What stays on top** is now small: severe starvation (Austria: 7% of its people, census +1.33%, predicted +0.55%),
  devastation, and the late-era lines.

**Countries of 20M or more in 1887** (% a year, census and predicted): China +0.23, +0.23; British India +1.26,
+1.26; Russia +1.08, +1.08; the USA +1.59, +1.59; Japan +0.71, +0.71; France +0.60, +0.59; Turkey +1.39, +1.39;
Britain +0.90, +0.89; Austria +1.33, +0.55; New Granada +1.42, +1.42; Mexico +1.52, +1.52; Korea +0.62, +0.62. The full
per-save tables are `predict`'s output.

### The multiple: candidate parameters (the owner's call; nothing retuned)

The census's own rates give the world +0.95 to +1.07% a year to 1867 and +0.86% after, against history's 0.4% (1820–1870)
and 0.8% (1870–1913, Maddison). Two candidates, each run through `predict` on the same six saves with every other
parameter as built (`demographics_harness.py history` gives the life expectancy and children per woman beside
Clio Infra's and Gapminder's):

| Change | World multiple | China 1877 / 1887 | Any 20M+ shrinking | Evidence and cost |
|---|---|---|---|---|
| As built | ×1.78 | +0.26 / +0.23% | none | — |
| **`WEALTH_TFR_LOW` 6.2 → 6.0** (children per woman from wealth at SoL 8 and below) | **×1.66** | +0.16 / +0.12% | none | The model's children per woman sit above Gapminder's almost everywhere: 1837 China 6.09 (Gapminder 5.5), Japan 5.75 (4.5), Britain 5.50 (4.8), France 4.45 (3.6); 1887 Japan 5.43 (4.0), the USA 5.60 (4.4), France 4.10 (3.2). At 6.0 each moves 0.1–0.2 toward Gapminder's; India (5.87 against 5.8) and Russia (5.57 against 6.6) move away. Life expectancy doesn't change |
| **`POVERTY_INFECTION_SOL` 9 → 10** (the poverty term starts at SoL 10) | ×1.62 | +0.16 / +0.15% | none | Aims at the gap the history check left: India grows +1.36% against history's +0.84% (its 1887 life expectancy 34 against 24), and goes to 32. But it costs the West: Britain's 1837 life expectancy drops from 35.6 to 33.8 (history 41), already the check's weakest anchor |
| `POVERTY_INFECTION_AT_FLOOR` 1.75 → 1.9 (rejected) | ×1.66 | +0.03 / −0.03% | China, 1887 | the history check's own table: steeper poverty takes China below Maddison's +0.3% first |
| `POVERTY_INFECTION_AT_FLOOR` → 2.0 (rejected) | ×1.58 | −0.13 / −0.20% | China, 1877 and 1887 | the same |

## The probes

| Probe | Question | Answer |
|---|---|---|
| P1 | Are devastation's and pollution's mortality lines inside `modifier:state_mortality_mult`? | **Yes, both (owner, in game, 2026-10-10).** Alentejo: "State Region Devastation +11%", Ministry of Health −2%, total +9%, against option m's logged +0.091. Yorkshire: "Pollution Impact +8%", Ministry of Health −14%, total −5%, against −0.046. The mod's +0.05 pollution line adds to vanilla's (owner). The plan's §1 (E14, E15) records it |
| P2 | Does M cancel what the census absorbs, under Full only? (Amended: the lines stay in the law, tech and institution tooltips by design, the owner's accepted cost) | **To do (owner, in game):** option n on the capital under Full. `rep_b` and `rep_d` are the absorbed share of the bare curves: with No Women's Rights about +0.05 − 0.1 × literacy, and with Charitable Health System at Ministry of Health level N about −0.03 × N in deaths. The capital's birth and mortality tooltips list the laws' lines beside Census: Births / Deaths. `debug.log` carries no error from `te_demog_absorbed_*` (the generated `institution_investment_level` ladders, `has_technology_researched`, `is_in_mild_starvation` in pop scope). Offline, `TestEngineRateLines` pins every line to main and `TestAbsorbedScript` runs the script against `DM.totals` |
| P3 | Does the engine hit the target? Is M's fixed point stable? | **To do (owner, in game):** option n on the capital twice. After its second yearly pulse (the first step): `mb`, `md` and `applied_*`. After its third (the second step, the first that measures the engine against a target): `bz`, `dz` and `eb_target`, which are all 0 at the second |
| P4 | Does a state keep its census modifiers through a change of owner? | **To do:** `predict SAVE --check-modifiers` on a fast-run save taken after a war or a civil war |
| P5 | Turmoil's scaling (conditional) | Only if the fast run shows a residual tied to turmoil |

## Still to run (owner)

This list is the canonical checklist; the PR body repeats it.

1. **P2 and P3** on a throwaway save, deployed per CLAUDE.md "Play-testing unmerged work".
2. **The fast-mode gate run:** a new 1836 game, observed, census log on (option b), fast mode at 4× (option h) on day
   1, to census year 1950 or later; every `debug.log` generation archived and yearly autosaves on D:.
3. **Then:** `demographics_observer_report.py LOGS... --phase2` and `--closed-borders SAVES...`; `demographics_harness.py
   replay` on option a's blocks from three states at different SoL; `predict --census-rates` on the run's saves, and
   `--check-modifiers` on one after a war.
4. **The in-game gate:** the world 1836–1900 within ×1.3–×1.7; no 20M+ country losing people ten census years running
   outside wars; the replay exact; the Closed Borders `mig_raw` median within ±1 per 1,000; the clamped share under 1%;
   Europe's share rising to 1900 and Asia's falling.
5. **For this doc:** the census line's `bz` and `dz` by country and decade, which measure the size of the births and
   deaths added on top.
