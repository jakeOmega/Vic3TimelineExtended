# Demographics phase 2 step 4: probes and gate results (2026-10-10)

The gate of phase 2 step 4: the census sets the engine's births and deaths
(plan `docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md`, Task 12; PR #869). This records the
offline half, run on this date, and leaves room for the in-game half, which needs the owner.

**Status: the offline gate fails on one country.** The world multiple passes, but `predict` puts China's growth below 0
in the 1887 save. `predict` flags any single save in which a 20M+ country shrinks, a stricter proxy for the gate's
criterion (ten census years running outside wars), which needs the fast run's yearly census lines: the saves are a
decade apart, and China is +0.05% in 1877 and −0.09% in 1887, so the ten-year rule is neither met nor refuted
offline. The flag is a warning sign, not a measured gate miss. Per the plan, the fix is calibration (the calibration plan's steps 1–3, 5–6), not step 4's
arithmetic, so this stops here and reports. The in-game probes and the fast-mode run are still to do.

**Release precondition (owner, 2026-10-10):** steps 4 and 5 ship together. A passing gate would not make step 4
releasable alone, because Display only and Disabled lose the absorbed lines until step 5's equilibrium rates.

## The build, the saves and the tools

- **The build:** branch `feat/demog-phase2-engine-rates` (PR #869), at the commit that adds this file.
- **The saves:** the gate run's six autosaves, 1837 to 1887 a decade apart, in
  `/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`. They come from a normal-speed observer game on a build before
  #855, so their own stored census rates are the old model's.
- **The tool:** `scripts/analysis/demographics_harness.py predict SAVE... --slope` (Task 10).
  - **The census rates:** by default, the current model's stable rates for each state's own inputs (SoL, literacy,
    urban share, crowding, incorporation, the owner's techs, laws and institutions), not the saves' stale ones.
  - **The terms on top:** each pop's starvation (its food security), its class's mortality line, the owner's flat law
    and tech lines and the state's devastation. Terms on top a save doesn't hold (pollution, turmoil, events,
    `low_pop_state`, unemployment, workplace mortality) are left out.
  - **The world multiple:** chains each save's predicted world growth to 1900.
- **The checks around it:** the whole unittest suite, `ruff`, the tab check, `organize_loc --check`,
  `gen_demographics.py --check`, the six audits the plan names, and `demographics_harness.py medicine` and
  `fertility`.

## The offline gate

| Check | Threshold | Result |
|---|---|---|
| World multiple, 1837–1900 | ×1.3–×1.7 | **×1.66, pass** |
| No 20M+ country predicted to shrink | none | **China in the 1887 save: −0.09% a year (fail)**; +0.05% in 1877 |
| Share of people in clamped states | under 1% | 0.0% in every save |
| The unittest suite, `ruff`, tabs, `organize_loc --check`, `gen_demographics.py --check`, the six audits | all clean | 5,903 tests OK (61 skipped); the rest clean |
| Medicine scenarios (`medicine`) | each in its band | all in band; augmentation +2.4 / +1.1 / +1.1 years at Rich today, +0.1 with no health system |
| Fertility scenarios (`fertility`) | each in its band | all in band; the Western women's-rights rows at Britain 1900 3.66, West 1950 2.29, West 1990 1.43 |

**The world, save by save** (% a year; the terms on top in births and deaths per 1,000):

| Save | People | Census | Predicted | On top: births | On top: deaths | Child labour absorbed | Women's rights absorbed | Starving slope absorbed |
|---|---|---|---|---|---|---|---|---|
| 1837 | 1,031M | +0.95 | +0.88 | −0.43 | +0.27 | +0.217 | −0.234 | 0.036 |
| 1847 | 1,133M | +1.07 | +1.02 | −0.36 | +0.20 | +0.212 | −0.234 | 0.069 |
| 1857 | 1,244M | +0.94 | +0.84 | −0.53 | +0.50 | +0.216 | −0.235 | 0.112 |
| 1867 | 1,365M | +0.92 | +0.82 | −0.55 | +0.50 | +0.215 | −0.234 | 0.132 |
| 1877 | 1,458M | +0.86 | +0.66 | −0.98 | +1.04 | +0.214 | −0.234 | 0.157 |
| 1887 | 1,542M | +0.86 | +0.64 | −1.06 | +1.06 | +0.213 | −0.232 | 0.174 |

The last three columns are points of world growth a year, reported and not applied:
- **Child labour's class lines** (owner ruling: absorbed at the census's smaller work term) would have taken about
  0.21–0.22 points a year off world growth had they stayed on top. Absorbing them adds that back.
- **The women's-rights birth lines** (No Women's Rights' +0.05 above all, absorbed in Task 8 once the census's natural
  fertility carries them) would have added about 0.23 points. Absorbing them takes that off. The census was fitted
  without them (step 2), so this moves the engine onto the fit.
- **The starving slope below SoL 4** (owner ruling: the poverty term replaces it) cost 0.04 points in 1837 and 0.17 in
  1887, as the plan's §1 measured (China 0.023 and 0.244).

**Why China shrinks in 1887.** Its census rate is +0.23% a year, already carrying the poverty term. Added on top,
mild starvation takes 1.57 births off and adds 1.60 deaths per 1,000: 23.8% of China's people sit below food security
0.4, and none below 0.2. Austria shows the same mechanism more strongly (18% mild and 7% severe starvation: census
+1.33%, predicted +0.23%) without crossing 0. The question for calibration is whether the poverty term, fitted
without the engine's starvation on top (#855), now counts the same hunger twice in the poorest large states. That is
the owner's call; the plan's rule is that starvation stays on top (§3 (a)).

**Countries of 20M or more in 1887** (% a year): China +0.23 census, −0.09 predicted; British India +1.26, +1.00;
Russia +1.08, +0.92; the USA +1.59, +1.58; Japan +0.71, +0.67; France +0.60, +0.59; Turkey +1.39, +1.07; Britain
+0.90, +0.89; Austria +1.33, +0.23; New Granada +1.42, +1.41; Mexico +1.52, +1.49; Korea +0.62, +0.38. The full
per-save tables are `predict`'s output.

## The probes

| Probe | Question | Answer |
|---|---|---|
| P1 | Are devastation's and pollution's mortality lines inside `modifier:state_mortality_mult`? | **Yes, both (owner, in game, 2026-10-10).** Alentejo: "State Region Devastation +11%", Ministry of Health −2%, total +9%, against option m's logged +0.091. Yorkshire: "Pollution Impact +8%", Ministry of Health −14%, total −5%, against −0.046. The mod's +0.05 pollution line adds to vanilla's (owner). The plan's §1 (E14, E15) records it |
| P2 | Do the absorptions leave no line behind in the law, tech and institution tooltips? | **To do (owner, in game).** Offline, `TestEngineRateLines` holds every line to net zero or to `ENGINE_LINES_ON_TOP` |
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
