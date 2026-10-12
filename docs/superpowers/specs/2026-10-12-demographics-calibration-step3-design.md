# Demographics calibration step 3: the regional mortality gap (design, draft)

> **Status: work in progress, 2026-10-12.** Diagnosis (a) is done and measured. (b) to (d), the options, the gate and
> the engine checks are drafted; sections marked **TODO (next session)** are open. Part of #894. Parent plan:
> `docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`, "Step 3". Evidence: the overnight observer run
> on main 4002821a, 1836–1901 (`/mnt/d/vic3te-data/vic3te-demog-overnight-2026-10-12/session-notes-2026-10-12/REPORT.md`),
> and this spec's analysis in `.../session-notes-2026-10-12/step3/` (scripts and outputs; `STATUS.md` there).
> **M** = measured from the saves. **I** = inferred.

## Summary

- **India's miss is mostly the census's own weighting of a vanilla line, not a disease environment the game can't
  see.** India's peacetime births less deaths run +12.9 per 1,000 against history's +6 to +9. Of that, 4.6 per 1,000
  is one per-pop line: the Landowners' `ig_trait_famine_reserves` (M).
- That line reaches the census about three times as strong as its face value, from two factors:
  - **the walk reads it at twice its value** (−0.20 on a farm worker, not −0.10), and the engine applies it at that
    size (M; the mechanism is unknown);
  - **it adds on the bare curve**, which the census's term has cut to about 0.6–0.7 of itself, so relative to the
    census's rate it counts ×1/tb, about ×1.5 (M; exact by construction).
- Absorbing it per pop, as mild starvation is, puts India at +8.4 to +8.6, inside its band, with no geographic term
  (M, projected from measured state-years).
- What is left is small, mostly within the run-to-run spread, or a matter of births:
  - Africa +1.1, the Middle East +1.0 and Mexico +0.4 to +1.0 per 1,000 above their bands;
  - SE Asia 2.3 below (0.3 in the previous run);
  - the USA and Canada 4.5 below, mostly births.
- **A broad tropical or terrain term is wrong in kind** (M). It pushes SE Asia, which needs fewer deaths, the same way
  as India. The one geographic input that separates a region needing more deaths is vanilla's malaria traits: Africa,
  63% of its people, and almost nothing elsewhere.

## 1. Diagnosis

### (a) Lines on top, amplified under Full

**The census's weighting (M; the code, `te_demog_rates_refresh`).**
- The engine gives each pop bare × (1 + its state's read + its own lines).
- M is set so a state's events come to target × (1 + the state-level lines on top) + Σ bare_p × (the pop's own lines
  less what the census absorbs). So the state-level lines act on the census's rate (owner, 2026-10-11), and the
  pops' own lines on their bare curves.
- Relative to the census's rate, a pop's own line therefore counts ×1/tb, where tb = target / bare (`te_dg_tb_d`).
- 1 + M equals tb less the absorbed share (`te_dg_rep_d`) and the state lines' term. In peacetime those are near 0,
  so the brief's 1/(1+M) is right in form.
- In East Bengal 1841, M is −0.40, not −0.68: tb 0.605, rep 0, os +0.008, so 1/tb = 1.65 and 1/(1+M) = 1.66.
  - Script: `step3/peek_bic.py`.

**tb by region, peacetime 1837–1900, people-weighted (M):** China 0.74, India 0.67, Japan group 0.67, the Middle East
0.67, SE Asia 0.69, Africa 0.64, E Europe 0.61, Russia 0.62, South America 0.58, Europe 0.58, Mexico 0.57, the USA and
Canada 0.56. Every region's lines on top count ×1.35 to ×1.8 against the census's rate.

**The size of the lines: twice the files' value for the IG trait (M).**
- Each state's per-pop lines were rebuilt from the save's pops, workplaces, production methods and IG traits
  (`step3/extract_lines.py`, `step3/recon_lines.py`). Each pop is weighted by its bare curve, as the walk weights it.
- The walk's own measure is (`te_dg_sp_d` − `te_dg_ss_d`) / the bare curve.

| Family (the files' value) | Walk ÷ files, 1841 (857 states, R² 0.97) | 1891 (825 states, R² 0.79) |
|---|---|---|
| Landowners' `ig_trait_famine_reserves` (agriculture −0.10) | **2.01** | **2.05** |
| `working_conditions` (by workplace group and pop type) | 2.40 | 2.50 |
| Production methods' `building_<type>_mortality_mult` | 0.92 | 0.84 |

- **The engine applies the doubled size, too (M).** If the walk booked −0.20 while the engine applied −0.10, BIC's
  migration residual would read about −4 per 1,000 while the trait is on, and jump by about +3.4 when it goes.
  - It reads +0.0 to +0.5 in peace in 1837–56, while the own lines run −6.5 to −7.5 per 1,000.
  - The trait switched off in 1869–70 (own lines −6.1 → +0.5), and the residual went −1.5 → −2.1, with no jump.
  - Script: `step3/bic_series.py`; output `step3/bic_series.txt`.
- **Why it is doubled is not known (I).** One candidate is a building's read seeing a country modifier both directly
  and through its state. That needs an in-game check (§6, P1).
- **Working conditions' 2.4× (I).** The walk adds the table as constants, and also reads
  `building_group_<g>_<type>_mortality_mult`. The 2026-10-09 growth probe found those reads 0 at the capital in 1949;
  if they read the table elsewhere, the walk counts it twice.
  - The engine may still apply it once. Then the West's +1.1 to +2.2 per 1,000 of own lines are partly booked deaths
    the engine doesn't deliver, and they read as emigration.
  - The saves can't separate that from real emigration. In-game check P2.

**East Bengal 1841, the brief's −31.6% (M).**
- Own lines, bare-weighted: −0.195. That is 2 × the trait's −0.098 (84% peasants, 13% slaves, 98% of its bare curve
  in agriculture).
- Over tb 0.605 that is −0.32 of the census's rate. Over the realized rate it is −0.47.
- So the −31.6% is two factors, ×2.0 (the walk's read, the engine's application) and ×1.65 (1/tb). The second alone
  gives −0.16: the "roughly half" the report found.

**Awadh and Indore (M; the brief's note against the hypothesis).**
- The trait reaches only pops working in agriculture.
  - In 1891, 26% of Awadh's people are in subsistence farms: 37% are laborers with no workplace, and many are in
    opium, banana and cotton plantations.
  - Indore (Malwa) has 39%; Satara (Bombay) 91%.
- Their own lines follow that: −0.017, −0.045 and −0.175 of the bare curve, against −0.024, −0.040 and −0.094 from
  the trait at its face value.
- There is no contradiction. The 1891 figures are `step3/recon_1891_india.json`.

**Own lines and severe starvation, by region, peacetime 1837–1900, per 1,000 a year (M; `step3/ontop_regions_peace.txt`):**

| Region | Births less deaths | Own lines | of which negative | Severe | tb | A: own at the census's rate | C: own absorbed | D: negative absorbed, positive as A |
|---|---|---|---|---|---|---|---|---|
| China | +5.3 | +0.30 | 0 | 0.01 | 0.74 | +5.4 | +5.6 | +5.4 |
| India | **+12.9** | **−4.35** | −4.56 | 0.11 | 0.67 | +11.4 | **+8.6** | **+8.4** |
| Europe (W, N, C, S) | +11.0 | +1.15 | 0 | 0 | 0.58 | +11.5 | +12.1 | +11.5 |
| Africa | +9.1 | +1.11 | 0 | 0 | 0.64 | +9.4 | +10.2 | +9.4 |
| USA, Canada | +12.5 | +1.22 | 0 | 0 | 0.56 | +13.0 | +13.7 | +13.0 |
| E Europe, Balkans | +11.1 | +0.53 | 0 | 0.01 | 0.61 | +11.3 | +11.6 | +11.3 |
| Japan, Korea, Manchuria | +8.0 | +0.56 | 0 | 0.02 | 0.67 | +8.2 | +8.6 | +8.2 |
| Russia, Siberia | +10.6 | +0.52 | 0 | 0.06 | 0.62 | +10.8 | +11.2 | +10.8 |
| Middle East, C Asia | +9.0 | +0.48 | −0.12 | 0.01 | 0.67 | +9.1 | +9.4 | +9.0 |
| South America | +11.9 | +2.21 | 0 | 0.01 | 0.58 | +12.7 | +14.1 | +12.7 |
| SE Asia | +6.7 | +1.44 | −0.08 | 0 | 0.69 | +7.2 | +8.2 | +7.2 |
| Mexico, C America | +13.4 | +1.61 | 0 | 0 | 0.57 | +14.1 | +15.0 | +14.1 |
| World | +8.5 | +0.19 | −0.45 | 0.02 | 0.67 | +8.6 | +8.7 | **+8.3** |

- Over all state-years: India +8.5 → +7.7 (A), +6.0 (C); the world +7.9 → +7.6 (D) (`step3/ontop_regions_all.txt`).
- In this run every negative own line is the trait. Every positive one is working conditions and mine, plantation or
  construction methods.
- Severe starvation is 0.02 per 1,000 in peace and 0.17 over all years. #913 scaled it, and the owner kept it at the
  bare curve's weight (2026-10-11). Option B (severe at the census's rate too) moves no region by more than 0.2.
- The previous run (ec304526) shows the same India line: −2.5 per 1,000 on top in peace, against −3.4 now (REPORT,
  `out/decompA.txt`). It is structural.

**Births on top (M, REPORT `out/decompA.txt`, realized less model, peacetime).**
- Russia −1.19, E Europe −0.50, Mexico +0.93, South America +0.87, Japan +0.80, Africa +0.57, India +0.40; the USA
  +0.04.
- The only per-pop birth lines are literacy's and mild starvation's (both absorbed) and severe starvation's (on top).
  So births on top are state-level lines, already at the census's rate.
- **TODO (next session):** name the carriers by region (Cadet Sons Leave the Land, Forced Heirship's rural cut, the
  Natalism decree, events) in a short table.

### (b) What the model's inputs can't see

**Life expectancy, the census's own life table, peacetime 1837–1900, people-weighted (M; `step3/region_model_new.txt`),
against Clio Infra (`history-anchors-2026-10-10/anchors.csv`; Riley's regional figures for Africa):**

| Region | Model e0 | History | Model SoL | Reading |
|---|---|---|---|---|
| India | 31.0 | 23–25 (India, Bangladesh 1876–1901) | 7.57 | 6–8 years long |
| Mexico, C America | 38.0 | 25–29 (Mexico 1893–1904) | 8.95 | 9–13 years long: Europe's figure |
| South America | 37.0 | 29–33 (Brazil, Chile, Colombia, Argentina) | 8.48 | 4–8 years long |
| Africa | 32.3 | about 26 (Riley; no anchors) | 7.26 | about 6 years long |
| Russia, Siberia | 35.1 | 30.5–32 (1896–1900) | 8.40 | 3–5 years long |
| Japan, Korea, Manchuria | 30.9 | 36–38 (Japan 1865–1900) | 7.22 | 5–7 years short, below India's |
| Europe (W, N, C, S) | 37.8 | 30–42 (Italy, Spain low; Britain, France, Germany 38–42) | 8.71 | about right |
| USA, Canada | 40.2 | 39–45 | 10.10 | about right |
| SE Asia | 30.2 | Sri Lanka 32.6 (1901); no others | 6.99 | no anchor |
| China | 26.9 | no anchor (Riley's Asia about 24–28) | 6.84 | plausible |

- **What a geographic input could separate (M).** Three were checked (`step3/terrain_regions_1841.txt`).
  - **Jungle provinces:** India 0.31 and SE Asia 0.29 of their province share, South America 0.17, the Japan group
    0.12, China 0.10, Mexico 0.07, Africa 0.01. This pushes SE Asia like India: wrong in kind.
  - **Latitude (the tropics):** the same problem for SE Asia. It also hits Mexico and South America, whose growth then
    falls below their bands unless their births rise (I).
  - **Vanilla's malaria traits** (`state_trait_malaria`, `_severe_malaria`): Africa 63% and 10% of people, SE Asia 2%
    (Indonesia), Oceania 29% (severe), nothing else. They are the one input that reaches a region needing more deaths
    and nothing that needs fewer.
- **What no game input separates (I).**
  - Japan's long life against its SoL: its low SoL drives the poverty term, ×1.26 on infection.
  - The Middle East's +1 per 1,000.
  - Russia's and Latin America's high-pressure regime: early marriage, high fertility and high mortality together.
  - SE Asia and Japan differ in the model's inputs mostly by literacy, which is already modelled.

### (c) This game's own trajectory: structure against noise (M; REPORT A, `out/decompA.txt`)

Peacetime births less deaths, this run against the previous one (ec304526), with what moved:

| Region | This / previous | Change | Driver |
|---|---|---|---|
| China | +5.3 / +6.5 | −1.2 | SoL 6.84 against 7.08; 1890s slide to +1.2–1.7 |
| India | +12.9 / +11.7 | +1.2 | Peace share 33% against 42%; 1877–91 under 20% peace |
| USA, Canada | +12.5 / +13.6 | −1.1 | SoL +0.67: fewer model births |
| SE Asia | +6.7 / +8.7 | −2.0 | SoL 6.99 against 7.28: infection ×1.30 against ×1.25 |
| Mexico, C America | +13.4 / +11.6 | +1.8 | SoL +0.66: fewer model deaths |
| Oceania | +6.4 / +10.6 | −4.2 | under 20% peace most intervals: unjudgeable |
| Others | | ±0.1 to ±0.4 | |

- Mean absolute change over the 12 banded regions: about 0.75 per 1,000. The largest: 2.0 (SE Asia).
- Structural, the same side in both runs: India high (+2.7, +3.9), the USA low (−3.4, −4.5), Europe high (+1.1, +1.0;
  Late Marriage's), the Japan group high (+1.8, +2.0; Birth Spacing's), Africa high (+0.8, +1.1), the Middle East
  high (+0.8, +1.0).
- Noise: SE Asia (−0.3, −2.3), Mexico (in, +0.4), South America (−0.5, −0.1).

### (d) Births: the USA (M; `step3/region_model_new.txt`)

- USA and Canada, peacetime: realized CBR 36.2 and CDR 23.7. The model's own: CBR 34.5, children per woman 5.18,
  e0 40.2.
- History: children per woman 6.24 in 1837 (Gapminder), CBR about 45–50 in the 1840s, CDR about 21–23.
- So the USA's 4.5 per 1,000 shortfall is mostly births (about −9 of CBR); its deaths are 1–2 high.
- After (a)'s recommended option, the USA is unchanged: its lines are positive and stay as they are.
- Late Marriage's results doc estimated a global raise of about 1.09 for the USA. That predates this diagnosis and
  must be refitted after (a).
- **TODO (next session):** check whether the census's placing of immigrants (the labour profile, 18–35) is diluting
  the USA's CBR at 15 per 1,000 net immigration. Compare `te_dg_w1549` shares with an anchor.

## 2. Options (recommendation first)

### 2.1 How the census weighs the pops' own lines

**Recommended: absorb the country-scope per-pop lines; keep the building-scope ones as they are for now.**
- **Country scope** means lines on a country's carriers that reach pops through their workplace's or class's keys.
  Today that is only the Landowners' `ig_trait_famine_reserves`.
  - Each pop's part goes into the walk's absorbed sum (`te_demog_pop_absorbed_deaths`), as mild starvation's does.
    M then nets it, and the line only moves deaths between a state's farm workers and the rest.
  - The amount: the country's own read of the key (`owner.modifier:building_group_<g>_mortality_mult`) × k, where k
    is the factor the in-game check P1 measures (2 on this run's evidence).
  - Projected: India +8.4 to +8.6, the world +8.2 to +8.3, every other region unchanged.
- **Building scope** means working conditions, production methods, company prosperity lines and company executives'
  traits. These stay at the bare curve's weight until P2 says whether the walk counts working conditions twice.
  - If it does, fix the walk first, then decide between bare weight and the census's rate (option A: South America
    +0.8, the USA +0.5, Europe +0.5, Mexico +0.7).
- **The cost:** under Full a vanilla IG trait's −10% no longer lowers a state's deaths, and its tooltip still shows it.
  The engine-lines families can't carry it: it is a building-group key on a country carrier, and the trait switches
  with IG approval.
- Alternatives:
  - **A, every own line at the census's rate:** India +11.4, still 2.4 out. One M also moves the neighbours' rates in a
    mixed state (the engine-rates doc's Punjab argument).
  - **C, every own line absorbed:** India +8.6, but South America +14.1, Mexico +15.0 and Europe +12.1. It removes
    player levers (dangerous methods, Workplace Safety's subject).
  - **Leave it:** India +12.9.

### 2.2 A geographic infection term

**Recommended: a small infection factor on vanilla's malaria traits only. No new traits and no table.**
- Shape: infection × (1 + g), g about 0.05–0.10 on `state_trait_malaria`, more on `_severe_malaria`. Africa needs
  about +1.4 on a CDR of 32 (I).
- One more entry in `CAUSE_FACTORS["infection"]` (#916), shown on the Causes of Death hover.
- **Switched off by malaria_prevention (era 4) and the census's infection treatment, not by quinine.** Vanilla's
  traits are colonists' mortality (`state_non_homeland_mortality_mult`), and quinine protected colonists, not the
  people who lived there. Tropical deaths among them fell only with 20th-century medicine (I).
- **Not recommended:** latitude, terrain or a hand-made region table. They push SE Asia the wrong way, and the
  regions they would fix (India) are fixed by 2.1.
- **TODO (next session):** fit g with the harness (§3), and check Oceania's severe-malaria states.

### 2.3 The USA's births

- **TODO (next session).** Draft: refit Late Marriage's raise jointly with 2.1 and 2.2, using the same gate, with
  India's and East Asia's held shares. Report the raise the USA alone needs against what the gate allows.
- A conditions-based fertility input is an owner call (land per person: the frontier finding of Yasuba and
  Easterlin). It would separate the USA, Russia and Latin America from dense India, China and Europe.

### 2.4 The gate and the run-to-run spread

- **Recommended (draft):** widen each region's band by half the measured two-run spread on each side, at least 0.5.
  Judge the world on the saves as #904 does.
- Leave Oceania, and India's 1877–91 intervals (under 20% peace), unjudged.
- Alternative: judge on two runs, with each region inside its band in both. That needs a second normal-speed run per
  candidate (about 8 hours).

## 3. Targets and a gate the harness can check

- Targets: the owner's regional bands (`docs/testing/demographics-late-marriage-2026-10-12.md`, origin/feat/demog-late-marriage).
  - The world at most today's less 1 per 1,000: +7.5 on this run.
  - No country of 20M+ with births below deaths.
  - Every `medicine` and `fertility` anchor in band.
- **What needs building.**
  - `practices-fit`'s projection (`project_regions`) scales a state-year's deaths by the model's band deaths. It can't
    project a change in how lines on top are weighted.
  - **A new subcommand** (working name `ontop-fit`): read each state-year's split of the window's deaths
    (`te_dg_ed`, `_ed_state`, `_ed_sev`, `_ed_target`, `te_dg_tb_d`) beside #904's rows, and apply 2.1's rule by
    family. `step3/ontop_regions.py` is the stand-in.
  - **The malaria factor:** `FitState` needs the state's malaria traits and the owner's malaria_prevention, from
    `demographics_save_inputs`.
- **TODO (next session):** the exact commands, the grid (g × raise × held shares) and the gate's printout.

## 4. Interactions

- **#906 (Late Marriage).** Its projection takes Europe −3.2 and the Japan group −3.8; with 2.1, India is unchanged
  by it. Late Marriage's raise and held shares are refitted after this step (2.3). Its practices' shares don't move.
- **Phase 2 step 1 (workforce and participation).** No interaction with births or deaths. Both regenerate
  `te_demog_generated_values.txt`, so only the merge order matters.
- **#916 (medicine drift).** The malaria factor is a cause factor and does not drift. Medicine's targets don't move.
  The lag costs infection ×1.005–×1.019 (REPORT D2), small next to this step.
- **Disabled and releases.** 2.1 changes only the walk's absorbed sum and M, which exist only under Full. 2.2 is a
  census factor. Under Disabled, births and deaths stay exactly main's, and a release reads `te_demog_effects_run` as
  `always = no`.

## 5. Owner calls (draft)

1. **The Landowners' famine reserves under Full.** Recommended: absorbed per pop (2.1). Alternatives: at the census's
   rate (India +11.4); leave it (+12.9).
2. **A geographic term.** Recommended: malaria traits only (2.2). Alternatives: none (Africa stays about +1 high); a
   tropics or region table (SE Asia goes the wrong way).
3. **The gate's spread.** Recommended: bands widened by half the two-run spread (2.4). Alternative: two runs per
   candidate.
4. **TODO (next session):** the USA's births (2.3), and whether Japan's long life is left as an SoL artefact.

## 6. Engine feasibility and in-game checks

- **P1, the doubled trait.** In 1836 as BIC (or any Indian country with happy Landowners):
  - hover a subsistence-farm peasant pop's mortality and see whether Famine Reserves is listed once or twice;
  - `debug_log` the farm's `modifier:building_group_bg_agriculture_mortality_mult`, East Bengal's state read and
    BIC's country read.
  - This sets k in 2.1.
- **P2, working conditions.** `debug_log` a non-capital mine's `building_group_bg_mining_laborers_mortality_mult`.
  If it reads 0.1, the walk counts the table twice: drop the constants and fix the generator.
- **P3, the malaria traits.** `disabling_technologies` disables the trait's modifier, not the trait. Confirm that
  `has_state_trait` (or the state region's trait check) still reads true afterwards, and that the census can test the
  owner's malaria_prevention itself.
- **TODO (next session):** the modifier types and scope rules for 2.1's country read (it must be read in pop scope
  through `owner`; CLAUDE.md's JE-multiplier scope note does not apply). Check the reads against
  `scripting_best_practices.md`.
