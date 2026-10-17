# Demographics calibration step 3: the regional mortality gap (design)

> **Status: owner calls 1–3 approved as recommended (owner, 2026-10-12) and built on this branch (PR #930); call 4
> (the USA's births, Japan's long life) stays open for the owner.** What was built and the fit are in §2.1, §2.2, §2.4
> and §3; the engine facts it rests on are once-a-game self-checks (§6), per the owner's process of 2026-10-12. Part of
> #894. Parent plan:
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
    size (M). The Landowners are powerful wherever the trait is on, and a powerful group's traits count double
    (`POWERFUL_IG_TRAIT_BONUS`; M, §1(a));
  - **it adds on the bare curve**, which the census's term has cut to about 0.6–0.7 of itself, so relative to the
    census's rate it counts ×1/tb, about ×1.5 (M; exact by construction).
- Absorbing it per pop, as mild starvation is, puts India at +8.3, inside its band, with no geographic term
  (M, projected from measured state-years; `ontop-fit`, §3).
- What is left is small, mostly within the run-to-run spread, or a matter of births:
  - Africa +1.1, the Middle East +1.0 and Mexico +0.4 to +1.0 per 1,000 above their bands;
  - SE Asia 2.3 below (0.3 in the previous run);
  - the USA and Canada 4.5 below, mostly births.
- **A broad tropical or terrain term is wrong in kind** (M). It pushes SE Asia, which needs fewer deaths, the same way
  as India. The one geographic input that separates a region needing more deaths is vanilla's malaria traits: Africa,
  63% of its people, and almost nothing elsewhere.
- **Built (owner calls 1–3, 2026-10-12):** the trait absorbed per pop under Full (§2.1), a malaria factor on
  infection, 0.08 on the mild trait and 0.13 on the severe one, ended by Malaria Prevention (§2.2), and the gate's
  bands widened by half the two-run spread (§2.4). On this run's saves the gate goes from 6 items failing to 3: India,
  Africa and the world come inside; the USA (call 4, open), the Middle East (+0.35 out) and SE Asia (1.4 below, inside
  on the previous run) stay out (§3).

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
- **Why it is doubled (M, 2026-10-12): the interest group's power.** The 1.13.9 defines double a powerful group's
  trait modifiers and halve a marginal one's (`POWERFUL_IG_TRAIT_BONUS = 1`, `MARGINAL_IG_TRAIT_PENALTY = 0.5`;
  `docs/vanilla/vanilla_politics_reference.md`, as #932 corrected it).
  - Every country with Famine Reserves on had powerful Landowners: 48 countries, 160.8M people working farms, in
    1841, and 17 countries, 14.6M, in 1891, at clout 0.29 to 0.88 against the powerful threshold of 0.20. None was
    influential or marginal, so every state in the regression read the trait at ×2.
  - So the doubling is the trait's own size in these countries (M). A trait is a country modifier, which the engine
    scales by the group's power, and a building reads its country's modifier once. That the country's own read of the
    key (`modifier:building_group_bg_agriculture_mortality_mult`) returns the same ×2 size is inferred (I): nothing in
    the mod has read a `building_group_*` key at country scope before. The census absorbs that read (§2.1), and the
    once-a-game self-check `famine_reserves_absorbed` settles it in game, arming on the walk's side so a country read
    of 0 logs BROKEN (§6, P1).
  - Scripts: `step3/ig_clout.py` (each IG's clout and traits from a save), `step3/ig_power_check.py` (the trait's
    countries by clout, with their farm workers); outputs `step3/ig_power_1841.txt`, `step3/ig_power_1891.txt`.
  - The earlier candidate, a building's read seeing a country modifier both directly and through its state, would
    have read ×4 at powerful Landowners.
- **Working conditions' 2.4× (I).** The walk adds the table as constants, and also reads
  `building_group_<g>_<type>_mortality_mult`. The 2026-10-09 growth probe found those reads 0 at the capital in 1949;
  if they read the table elsewhere, the walk counts it twice.
  - **Settled 2026-10-17 (P2 BROKEN):** a Walloon mine read 0.100 in January 1836. The table applies to each building
    × (1 + `building_working_conditions_mult`), and the 1949 capital's 0 was France's Workplace Safety at five. The
    constants are gone (`engine_rate_terms`); §2.1's choice for building-scope lines (bare weight or the census's rate)
    is still open, and the walk keeps bare weight.
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
- **Open (with call 4):** name the carriers by region (Cadet Sons Leave the Land, Forced Heirship's rural cut, the
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
- **Open (with call 4):** check whether the census's placing of immigrants (the labour profile, 18–35) is diluting
  the USA's CBR at 15 per 1,000 net immigration. Compare `te_dg_w1549` shares with an anchor.

## 2. Options (recommendation first)

### 2.1 How the census weighs the pops' own lines

**Decided (owner call 1, 2026-10-12) and built: absorb the country-scope per-pop lines; keep the building-scope ones
as they are for now.**
- **Country scope** means lines on a country's carriers that reach pops through their workplace's or class's keys.
  Today that is only the Landowners' `ig_trait_famine_reserves`: no law, technology, institution, decree or static
  modifier in the base game or the mod carries `building_group_bg_agriculture_mortality_mult`, and the executives'
  traits that do are `executive_modifier`s, on their company's buildings.
  - Each pop's part goes into the walk's absorbed sum (`te_demog_pop_absorbed_deaths`), as mild starvation's does.
    M then nets it, and the line only moves deaths between a state's farm workers and the rest.
  - **The amount: the country's own read of the key** (`owner.modifier:building_group_bg_agriculture_mortality_mult`,
    `te_demog_pop_country_absorbed_deaths`), for a pop employed in an agriculture building (the walk's gate:
    `bg_agriculture`, `bg_staple_crops`, `bg_subsistence_agriculture`). k is 1, not 2: the country's read already
    carries the group's power (§1(a)), so a powerful group's −0.10 reads −0.20 there, as at the farm. That read, a
    `building_group_*` key at country scope, is inferred until the self-check `famine_reserves_absorbed` logs OK
    (§6, P1). Its fallbacks: the scale `P.COUNTRY_ABSORBED_SCALE` (1) if the two reads differ by a ratio, and
    `P.COUNTRY_ABSORBED_FROM_FARM` if the country's read is 0 (below). The groups are `P.COUNTRY_ABSORBED_GROUPS`.
  - `owner` is a pop's link to its country (`docs/engine/event_targets_summary.txt`), so the read works in the walk's
    pop scope; the JE-multiplier scope note in CLAUDE.md is about modifier multipliers and doesn't apply.
  - Under Display only and Disabled nothing changes: the walk's absorbed sums run only under Full
    (`te_dg_w_rep`, set from `te_demog_effects_run`), and only Full's refresh reads them.
  - Projected (§3): India +8.3 (from +12.8 with Late Marriage), every other region within 0.1 of its figure.
- **Building scope** means working conditions, production methods, company prosperity lines and company executives'
  traits. These stay at the bare curve's weight until P2 says whether the walk counts working conditions twice.
  - If it does, fix the walk first, then decide between bare weight and the census's rate (option A: South America
    +0.8, the USA +0.5, Europe +0.5, Mexico +0.7).
- **The cost:** under Full a vanilla IG trait's −10% (−20% while powerful) no longer lowers a state's deaths, and its
  tooltip still shows it. The player guide says so (chapter 8, Causes of Death); the Causes of Death section's "other
  effects on some of its people" no longer counts it, since the split subtracts the absorbed sum.
  The engine-lines families can't carry it: it is a building-group key on a country carrier, and the trait switches
  with IG approval.
- Alternatives:
  - **A, every own line at the census's rate:** India +11.4, still 2.4 out. One M also moves the neighbours' rates in a
    mixed state (the engine-rates doc's Punjab argument).
  - **C, every own line absorbed:** India +8.6, but South America +14.1, Mexico +15.0 and Europe +12.1. It removes
    player levers (dangerous methods, Workplace Safety's subject).
  - **Leave it:** India +12.9.

### 2.2 A geographic infection term

**Decided (owner call 2, 2026-10-12) and built: a small infection factor on vanilla's malaria traits only. No new
traits and no table.**
- Shape: infection × (1 + g × (1 − c)): **g 0.08 on `state_trait_malaria`, 0.13 on `_severe_malaria`** (the mild
  one × vanilla's own ratio for colonists, 0.25 to 0.15, to 0.01; `P.MALARIA_INFECTION`). c is the census type
  `state_malaria_control_add`, 0 to 1.
- The last entry in `CAUSE_FACTORS["infection"]` (#916): `te_demog_f_infection_malaria`. The Causes of Death hover
  shows "Malaria: ×1.08 (until Malaria Prevention)" only where the factor isn't ×1.
- **Switched off by Malaria Prevention (era 4) and the census's infection treatment, not by quinine.** Vanilla's
  traits are colonists' mortality (`state_non_homeland_mortality_mult`), and quinine protected colonists, not the
  people who lived there. Tropical deaths among them fell only with 20th-century medicine (I).
  - **How (a choice the spec left open):** Malaria Prevention carries `state_malaria_control_add = 1`
    (`te_demog_tech_injections.txt`), as every other technology reaches the causes through a census type rather than
    a tech test in the script (`test_gen_demographics`' rule). Its tooltip shows "Malaria Control +100%", and a
    release comments the line out with the census's other inputs.
  - The infection treatment needs no term of its own: the medicine factor, 1 − access × treatment, multiplies the
    whole infection rate, malaria's excess included, so full treatment ends it with the rest.
- **The inputs.** The step stores the trait's level (`te_dg_in_mal`: 0, 1 or 2, from `has_state_trait`;
  `te_demog_malaria_level`) and the control (`te_dg_in_malc`) with its other inputs (`te_demog_cause_inputs_store`).
  A state whose last step predates this build reads ×1 until its next step. The harness takes the level from the map
  files (`demographics_regions.malaria_levels`, through `demographics_save_inputs.state_inputs`) and the control from
  the owner's techs, or both from a save that stored them.
- **Where it reaches** (the map files): 75 state regions, 49 with the mild trait and 26 severe. Africa 62 (24 in West
  Africa, 17 in East Africa, 15 in Equatorial Africa, 5 in Southern Africa, Equatoria in the Nile basin); the
  Indonesia strategic region 3 (Celebes mild, Western and Eastern New Guinea severe); Oceania 10, all severe (the
  Pacific islands from Micronesia to Tonga).
- **The fit (§3): g 0.08** is the smallest on a 0.02 grid that brings Africa inside history's band: +9.05 → +7.89.
  - It was fitted to history's band, not the widened one: at the widened top (+8.50) g 0.04 would do (+8.47), with no
    margin for the run-to-run spread the widening is for.
  - The model's life expectancy in Africa goes from 32.7 to 31.5 (history about 26, Riley).
- **Oceania's severe-malaria states** (all ten of its trait regions): Oceania +6.42 → +6.24, its life expectancy
  37.1 → 36.7. Oceania has no band and stays unjudged (under 20% peace most intervals). Southeast Asia moves −0.03
  (+6.64 → +6.61), from Indonesia's three regions: the wrong way, but small.
- **A known limitation: vanilla's trait isn't a malaria map everywhere.** Seven of Oceania's ten trait regions are
  east of the malaria line and historically malaria-free (Fiji, Tonga, Tahiti, Kanak, Nauru, East and West
  Micronesia), and Namaqualand and Hereroland are arid. There the trait is vanilla's colonisation gate. The effect is
  tiny (Oceania −0.18 per 1,000, unjudged; the two arid regions are thinly peopled), and the owner's rule is no
  hand-made region tables, so the factor reads the trait as it is.
- **Not recommended:** latitude, terrain or a hand-made region table. They push SE Asia the wrong way, and the
  regions they would fix (India) are fixed by 2.1.

### 2.3 The USA's births

- **Open: owner call 4.** Nothing in this step changes the USA's births or Japan's life expectancy.
- **What the fit shows (§3).** After calls 1–3 the USA and Canada read +12.46 per 1,000, 4.0 below the widened band
  (+16.45; history +17 to +21). Their own lines are all positive (+1.22) and untouched by 2.1, and they have no
  malaria, so the gap is as before, mostly births (§1(d)). The Japan group reads +4.08, inside its band, at a model
  life expectancy of 30.0 (history 36–38 for Japan 1865–1900); this step doesn't move it.
- Draft, for the owner: refit Late Marriage's raise jointly with 2.1 and 2.2, using the same gate, with
  India's and East Asia's held shares. Report the raise the USA alone needs against what the gate allows.
- A conditions-based fertility input is an owner call (land per person: the frontier finding of Yasuba and
  Easterlin). It would separate the USA, Russia and Latin America from dense India, China and Europe.

### 2.4 The gate and the run-to-run spread

- **Decided (owner call 3, 2026-10-12) and built:** widen each region's band by half the measured two-run spread on
  each side, at least 0.5. Judge the world on the saves as #904 does.
  - The spread, per 1,000 a year, peacetime 1837–1900, ec304526 against 4002821a (`demographics_regions.TWO_RUN_SPREAD`,
    measured by `ontop-fit --spread-rows`): China 1.14, India 1.15, Europe 0.08, Africa 0.27, the USA and Canada 1.10,
    Eastern Europe 0.30, the Japan group 0.18, Russia 0.18, the Middle East 0.13, South America 0.35, Southeast Asia
    1.93, Mexico 1.84 (Oceania 4.22, unjudged).
  - So the widening (`demographics_regions.widening`) is 0.5 on each side everywhere but China 0.57, India 0.58, the
    USA 0.55, Southeast Asia 0.97 and Mexico 0.92. Both `practices-fit` and `ontop-fit` judge on the widened bands;
    `region_gate` without `widen` still judges on history's.
- Leave Oceania, and India's 1877–91 intervals (under 20% peace), unjudged.
- Alternative: judge on two runs, with each region inside its band in both. That needs a second normal-speed run per
  candidate (about 8 hours).

## 3. Targets and a gate the harness can check

- Targets: the owner's regional bands (`docs/testing/demographics-late-marriage-2026-10-12.md`, origin/feat/demog-late-marriage).
  - The world at most today's less 1 per 1,000: +7.5 on this run.
  - No country of 20M+ with births below deaths.
  - Every `medicine` and `fertility` anchor in band.
- **What needed building** (built, below).
  - `practices-fit`'s projection (`project_regions`) scales a state-year's deaths by the model's band deaths. It can't
    project a change in how lines on top are weighted.
  - **A new subcommand** (working name `ontop-fit`): read each state-year's split of the window's deaths
    (`te_dg_ed`, `_ed_state`, `_ed_sev`, `_ed_target`, `te_dg_tb_d`) beside #904's rows, and apply 2.1's rule by
    family. `step3/ontop_regions.py` is the stand-in.
  - **The malaria factor:** `FitState` needs the state's malaria traits and the owner's malaria_prevention, from
    `demographics_save_inputs`.
- **Built: `demographics_harness.py ontop-fit`** (`demographics_ontop.py`). For each peacetime state-year (#904's
  rows, 1837–1900):
  - the split comes from the 1 January save that closes its step: the pops' own lines are `te_dg_ed` less
    `te_dg_ed_state` and `te_dg_ed_sev`, as shares of `te_dg_ed`, scaled onto the row's deaths;
  - **call 1:** the net negative own lines (in this run, the trait) leave the deaths; the net positive ones stay.
    That is an upper bound on the projected rate in a mixed state: positive lines on its other pops hide part of the
    trait, which the build absorbs whole. India's true figure is a little lower, about +8.1 against +8.34 (the review
    of #930's estimate), still inside its band;
  - **call 2:** the rest of the deaths less severe starvation's (the census's rate with the state-level lines) are
    scaled by the model's expected deaths at the state's census bands with the factor over without
    (`FitState.deaths`, as `practices-fit` scales them), today's figures at g 0, since the run had no factor;
  - births take Late Marriage and Birth Spacing at main's decided point (s 1.00, cuts 0.10 and 0.20, India's held
    share 0, East Asia's 0.06), so "before" is main;
  - the grid is g alone (0 to 0.16 by 0.02); the raise and held shares are call 4's (§2.3).
- **The commands** (the overnight run of 2026-10-12, main 4002821a; `D=/mnt/d/vic3te-data/vic3te-demog-overnight-2026-10-12`,
  `N=$D/session-notes-2026-10-12`):

  ```
  demographics_harness.py ontop-fit $D/saves/<the 1837, 1847, ..., 1897, 1901 autosaves> --peacetime $N/rows.json \
    --splits $N/data/*.json \
    --spread-rows /mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/session-notes-2026-10-11/regional-rates/rows.json
  ```

  About 3 minutes and 1 GB. Output: `$N/step3/ontop_fit.txt`. It reproduces the stand-in's India (+12.90 → +8.34;
  `ontop_regions.py`'s rule D gave +8.4).
- **The grid** (Africa against history's +3 to +8):

  | g (mild / severe) | Africa | Oceania | SE Asia | World | Failing (widened) |
  |---|---|---|---|---|---|
  | 0 | +9.05 | +6.42 | +6.64 | +7.24 | 4 |
  | 0.04 / 0.07 | +8.47 | +6.32 | +6.63 | +7.20 | 3 |
  | **0.08 / 0.13** | **+7.89** | +6.24 | +6.61 | +7.16 | 3 |
  | 0.12 / 0.20 | +7.31 | +6.14 | +6.60 | +7.12 | 3 |
  | 0.16 / 0.27 | +6.72 | +6.04 | +6.58 | +7.08 | 3 |

- **Every region, before and after** (peacetime births less deaths, per 1,000 a year, 1837–1900; "before" is main,
  "after" is calls 1–3 at g 0.08):

  | Region | Measured | Before | Call 1 alone | After | History | Widened (call 3) | Before / after |
  |---|---|---|---|---|---|---|---|
  | China | +5.31 | +4.80 | +4.80 | +4.80 | +3 to +6 | +2.43 to +6.57 | in / in |
  | India | +12.90 | +12.90 | +8.34 | +8.34 | +6 to +9 | +5.42 to +9.58 | **out** / in |
  | Europe (W, N, C, S) | +10.99 | +7.91 | +7.91 | +7.91 | +8 to +10 | +7.50 to +10.50 | in / in |
  | Africa | +9.05 | +9.05 | +9.05 | +7.89 | +3 to +8 | +2.50 to +8.50 | **out** / in |
  | USA, Canada | +12.46 | +12.46 | +12.46 | +12.46 | +17 to +21 | +16.45 to +21.55 | **out** / **out** |
  | E Europe, Balkans | +11.06 | +10.50 | +10.50 | +10.50 | +8 to +12 | +7.50 to +12.50 | in / in |
  | Japan, Korea, Manchuria | +8.00 | +4.08 | +4.08 | +4.08 | +2 to +6 | +1.50 to +6.50 | in / in |
  | Russia, Siberia | +10.65 | +10.65 | +10.65 | +10.65 | +10 to +13 | +9.50 to +13.50 | in / in |
  | Middle East, C Asia | +8.97 | +8.97 | +8.85 | +8.85 | +4 to +8 | +3.50 to +8.50 | **out** / **out** |
  | South America | +11.87 | +11.87 | +11.87 | +11.87 | +12 to +16 | +11.50 to +16.50 | in / in |
  | SE Asia | +6.73 | +6.73 | +6.64 | +6.61 | +9 to +13 | +8.03 to +13.97 | **out** / **out** |
  | Mexico, C America | +13.43 | +13.43 | +13.43 | +13.43 | +10 to +13 | +9.08 to +13.92 | in / in |
  | Oceania | +6.42 | +6.42 | +6.42 | +6.24 | – | – | unjudged |
  | **World** | +8.53 | +7.70 | +7.24 | +7.16 | at most +7.53 | | **out** / in |

  - "Before" differs a little from the overnight report's Late Marriage projection (REPORT G: India +12.8, Europe
    +7.8, the Japan group +4.2, the world +7.9). That projection ran with no East Asian Birth Spacing; this one uses
    main's decided share, 0.06 (China +5.31 → +4.80 is its trace).
  - The 6 failing before are on the widened bands. On history's bands Europe (+7.91 against at least +8) would be a
    seventh: call 3's widening alone brings it in, the late-marriage fit's "fail by rounding".
  - No country of 20M or more has births below deaths, before or after.
  - **The gate after: 3 failing** (6 before). The USA is call 4's (§2.3). The Middle East is 0.35 above its widened
    band, the +1 per 1,000 no game input separates (§1(b)). Southeast Asia is 1.42 below: in the previous run it
    read +8.66, inside the widened band; its spread is the largest of the judged regions.
  - The model's life expectancy moves only in Africa (32.7 → 31.5) and Oceania (37.1 → 36.7); call 1 changes the
    engine's deaths, not the census's own rates.
  - India's 1877–91 intervals are not left out: the peacetime filter already drops war and famine state-years, and
    India is inside its band either way.
  - Every `medicine` and `fertility` scenario is unchanged: none has malaria.

## 4. Interactions

- **#906 (Late Marriage).** Its projection takes Europe −3.2 and the Japan group −3.8; with 2.1, India is unchanged
  by it. Late Marriage's raise and held shares are refitted after this step (2.3). Its practices' shares don't move.
- **Phase 2 step 1 (workforce and participation).** No interaction with births or deaths. Both regenerate
  `te_demog_generated_values.txt`, so only the merge order matters.
- **#916 (medicine drift).** The malaria factor is a cause factor and does not drift. Medicine's targets don't move.
  The lag costs infection ×1.005–×1.019 (REPORT D2), small next to this step.
- **Disabled, Display only and releases (checked on the build).** 2.1 changes only the walk's absorbed sum and M,
  which exist only under Full: `te_demog_absorbed_walk_pop` sums nothing unless `te_dg_w_rep` is set, which
  `te_demog_effects_run` (Full) sets, and only Full's refresh reads the sums. 2.2 is a census factor: under Display only
  it moves the census's own figures (the Demographics subtab's life expectancy and the hover), not births and deaths,
  as every cause factor does; under Disabled the census doesn't run. So births and deaths change only under Full. A
  release reads `te_demog_effects_run` as `always = no`, comments Malaria Prevention's census line out with the other
  census inputs (`comment_out_census_inputs.py` takes every line of a type in `demographics_modifier_types.txt`) and
  turns the self-checks off (`te_debug_demog_selfchecks_run`).

## 5. Owner calls

Calls 1–3 approved as recommended (owner, 2026-10-12); call 4 open.

1. **The Landowners' famine reserves under Full.** **Approved: absorbed per pop (2.1).** Alternatives were: at the
   census's rate (India +11.4); leave it (+12.9).
2. **A geographic term.** **Approved: malaria traits only (2.2).** Alternatives were: none (Africa stays about +1
   high); a tropics or region table (SE Asia goes the wrong way).
3. **The gate's spread.** **Approved: bands widened by half the two-run spread, at least 0.5 (2.4).** The alternative
   was two runs per candidate.
4. **Open (owner):** the USA's births (2.3), and whether Japan's long life is left as an SoL artefact. Nothing in this
   step changes either; §3 gives what the fit shows.

## 6. Engine feasibility and in-game checks

Per the owner's process (2026-10-12), none of these gates the merge. Each engine fact the build rests on is a
once-a-game `TE_SELF_CHECK OK|BROKEN <name> …` line in `debug.log` with a named fallback (the Self-checks table of
`docs/testing/demographics-playtest.md`), and what only a player can see is that file's "Calibration step 3" section.
All three run in a development build under any rule (`te_debug_demog_selfchecks_run`; a release turns them off), from
the country monthly pulse (`te_debug_demog_step3_selfchecks`), and each excludes the degenerate case so an OK can't be
a false pass.

- **P1, the doubled trait: the self-check `famine_reserves_absorbed`** (`te_debug_demog.40`).
  - Arms on the side the saves measured (`te_debug_demog_fr_armed`): the first month a country's Landowners are
    powerful (`is_powerful`, the engine's own test with its cutoff) and its capital has a subsistence-farm pop whose
    farm reads the line (`te_demog_pop_country_line_walk_read` below 0). The census's own read is left out of the
    arming (review of #930): had it armed on that read, a country read of 0 (call 1 silently doing nothing) would
    have kept the check silent too.
  - A week later (a day may come before the engine re-sums a country's modifiers) one such pop in the capital, whose
    building no company owns (so no executive's trait is in its read), logs what the census absorbs for it
    (`te_demog_pop_country_absorbed_deaths`) and what the walk reads at the farm, and its owner's read. No before-read
    is needed: the check changes nothing.
  - OK: equal (both about −0.2). BROKEN with absorbed 0: the country's read of a `building_group_*` key is 0, so under
    Full call 1 absorbs nothing; fallback `P.COUNTRY_ABSORBED_FROM_FARM`, which absorbs the farm's own read on
    subsistence farms only (no building-scope line there; commercial farms' workers keep the trait on top). BROKEN
    otherwise: the walk reads `ratio` × the absorbed amount; fallback `P.COUNTRY_ABSORBED_SCALE` = the ratio. The
    Landowners losing their power or no such pop in the week re-arms it. No line in a game's first weeks is expected
    (it arms at the first monthly pulse and logs a week later).
  - The saves already settle it (M, §1(a)); the check confirms it in game. The farm pop's mortality hover, listing
    Famine Reserves once at −20%, is a play-test item.
- **P2, working conditions: the self-check `working_conditions_read`** (`te_debug_demog.41`).
  - A week after the first country with a mine outside its capital, one such mine's
    `building_group_bg_mining_laborers_mortality_mult`.
  - OK: under 0.05 (about 0, the growth probe's capital reading), so the walk's constant is the only copy. BROKEN:
    about 0.1, so the walk counts the table twice. Fallback: drop the constants from `te_demog_pop_death_mult`, then
    redo 2.1's choice for building-scope lines.
  - **Read 2026-10-17: BROKEN, `read=0.100` at a Walloon mine.** The constants are gone (§1's "Working conditions'
    2.4×" has why); the check now tests the read against the table at the building's scale. 2.1's choice is open.
- **P3, the malaria traits: the self-check `malaria_trait_read`** (inline, no event).
  - `disabling_technologies` disables the trait's modifier, not the trait. **Preferred reading, built:**
    `has_state_trait` still reads the trait afterwards. Vanilla assumes the same: `cultural_community_values.txt`
    tests `has_state_trait = state_trait_malaria` together with the owner not having Quinine, a pair that would be
    pointless if the trait stopped reading at Quinine.
  - The first month a country with Quinine owns a state the map files give the mild trait
    (`te_demog_malaria_level_listed`, generated from `map_data/state_regions`), it logs whether `has_state_trait`
    reads it there. OK: it does. BROKEN: it doesn't, so the factor would end at Quinine. Fallback:
    `P.MALARIA_READS_REGION_LIST = True`, which makes `te_demog_malaria_level` read the generated list instead.
  - The census doesn't test the owner's Malaria Prevention itself: the technology carries the census type
    `state_malaria_control_add` (§2.2), read in state scope like the other census types.
- **The scope of 2.1's country read (answered).** `owner` is a pop's link to its country
  (`docs/engine/event_targets_summary.txt`), and `modifier:` reads a country's modifier, so
  `owner.modifier:building_group_bg_agriculture_mortality_mult` works in the walk's pop scope. The key is a registered
  type (the generator asserts it). CLAUDE.md's JE-multiplier scope note is about modifier multipliers resolving
  against ROOT and doesn't apply to a read.
