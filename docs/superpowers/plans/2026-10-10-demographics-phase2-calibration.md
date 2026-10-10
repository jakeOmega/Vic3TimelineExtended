# Demographics phase 2: the calibration (plan)

Phase 2 makes the census set the engine's births and deaths (parent spec §12, §2.3–§2.4). Its gate is "population
paths within the harness's tolerance". This plan orders the calibration that has to come first, so that the paths the
engine then follows are the census's and sane. Step 1 is built (this PR); the rest are planned here, each its own PR.

Evidence for step 1: `docs/testing/demographics-history-check-2026-10-10.md`. Owner context (2026-10-10): the system
is unreleased, so the bar for merging is low as long as each step is tested before the next public release; fast mode
(#848) is the in-game loop.

## Targets

- **World:** life expectancy about 29–31 from 1820 to 1870, 34 by 1913 and about 47 by 1950 (Riley). Population
  growth about 0.4% a year 1820–1870 and 0.8% 1870–1913 (Maddison); §2.3's "1900 ≈ 1.5× 1836" is the same thing.
- **Regions:** the West ahead of Asia, Latin America and Africa by about ten years of life expectancy in the 19th
  century. No large country shrinking for decades outside wars, famines and revolutions.
- **The game's own inputs, not history's.** Fit against countries' SoL, literacy, techs and laws as saves hold them.
  The game's 1836 world is more alike than history's (SoL 6.5–11), so country-by-country history is a guide, not a gate.

## Step 1 (built): poverty and the history check

- Infection ×(1 + 0.75 × clamp((9 − SoL) / 4, 0, 1)), state by state, with each state's crowding term as the save
  holds it: world life expectancy 31–32 (from 34.5–36.6), world growth about +1.0–1.1% a year (from 1.45%), China
  +0.3% by 1887, Maddison's peacetime pace. Every medicine and fertility anchor stays in its band as defined, though
  they barely test the term. The West pays: Britain 1837 36 (history 41; 38 with neither term) and Denmark 34 (41; 39).
- `demographics_harness.py history SAVE... --anchors CSV` and `scripts/analysis/fetch_history_anchors.py`.
- **The crowding term.** Main's census multiplies infection by 1.15 in any state carrying `migration_crowding` (unless
  its owner has a Ministry of Urban Planning), a switch that covers 91% of the world's people at any multiplier. The
  first fit left it out (×2 then); the harness now reads it from saves, and with main's switch its figures matched the
  fast-mode run's census at its next step exactly (the continuous term hasn't run in game yet). Owner, 2026-10-10: a
  function of how crowded the state is, not a switch. Infection now rises by the state's migration penalty from
  crowding (0.1 × the multiplier the crowding refresh applied, at most +50%), and the Ministry of Urban Planning works
  through the crowding instead of exempting the state. That is +3% on infection in 1837 on average, +11% by 1949.
- **Owner calls, all approved as built (2026-10-10):**
  - the strength. ×1.75 at SoL 5 is built (with c = 1); ×2 brings world growth to history's band but shrinks China
    by the 1880s in the gate game;
  - c, the share of the migration penalty infection rises by: 1 is built, 2 fits with ×1.5 (the results doc's table);
  - the Ministry of Urban Planning: it used to exempt a state from crowding's deaths entirely, and now lowers them
    through its +10% tolerance a level (a state at China's mean density: +5.2% becomes +4.0% at level 1 and +1.6% at
    level 5);
  - stage 1's medicine fit was made with crowding off. At the world's mean penalty of 1887 (0.07), India 1975 and
    "medicine, no health system" fall 0.2–1 year under their bands; refit them or accept it.

## Step 2: fertility against history

- **Anchors:** Clio Infra has no fertility series. Add Gapminder's children per woman (from 1800, CC BY 4.0) to
  `fetch_history_anchors.py` as a `tfr` measure, and print it in `history`.
- **The harness gap:** read France's Family Limitation from a save (the country's `te_demog_family_limitation`
  modifier), so the model's France in `history`, `seed` and `adopters` matches the game's.
- **Fit:** the wealth curve's ends and the education, survival and urban weights, against the saves' inputs and
  history's children per woman, keeping the `fertility` scenarios in band. The West reads high today (Britain 5.8 in
  1837 against about 4.8–5 in the 1840s).

## Step 3: the gap the game's inputs can't see (India, the tropics)

- India grows +1.3% a year in the model against +0.8% in history, at life expectancy 34 against 24. Nothing in its
  inputs (SoL 8.4, literacy 0.19) separates it from Russia or Spain.
- **To look at, in this order:**
  1. The base game's harvest conditions, `disease_outbreak` among them, which `pharmaceuticals` reduces. If they raise
     the engine's deaths, they already apply on top in phase 2.
  2. The engine's starvation, which phase 2 keeps (step 4).
  3. A disease-environment term from state traits. The malaria traits cover only sub-Saharan Africa and Indonesia;
     a broader one would mean new traits, an owner call.
- **Gate:** India's growth from the census plus the engine's own deaths within about 0.3% a year of history's.

## Step 4: how the census sets the engine's births and deaths

- **The engine adds its terms.** A pop's rate is its bare SoL curve × (1 + the sum of its terms), as the growth probe
  measured (#834). So the census's own modifier M adds to that sum, and the pop's events become
  bare × (1 + T + M). Summed over pops: E = E_T + M × E_bare.
- **The target:** the model's events, plus the terms meant to stay on top, weighted by the bare curve as the engine
  weights them: target = model + Σ bare × K, where K is the kept terms (starvation, devastation, turmoil, pollution,
  events).
- **So M = (model − Σ bare × (1 + T − K)) ÷ E_bare.** In words: the model's events, less what the engine would do
  with every term except the kept ones, over the bare curve's events.
  - The spec's "model ÷ engine − 1" is right only when no other term applies.
  - Using the walk's `te_dg_ed` (which already holds the starvation penalties and every per-pop term) for the
    engine's events would cancel the kept terms too.
  - So the walk needs one more sum: the kept terms' events, Σ bare × K, as its own local. `te_dg_eb` and `te_dg_ed`
    are stored, and the bare curves are the walk's locals `te_dg_w_eb0` and `te_dg_w_ed0`, which fast mode already
    reads.
- **The bare curve's starving slope.** Below SoL 4 the engine's mortality curve climbs steeply
  (`extra_defines.txt`), and M nets the bare curve out. So the model's poverty term, ×1.75 at SoL 5 and below, would
  replace that slope. Either keep the slope by adding it to K (the starving pop's extra over its curve at SoL 5), or
  let the model's term stand in for it.
- **The clamp:** the engine stops births at a total near −1 (probe: −0.9 holds, −3 stops), so M ≥ −0.9 less the
  other terms.
- **Everything the census now models moves into it**, through §8.4's removals:
  - the mod's flat birth and mortality lines on techs and laws (the Pill's −0.10 births, the family-policy laws, the
    medical techs' flat cuts);
  - vanilla Public Health Insurance's −0.05 a level mortality, by an inverse INJECT (the monetary pattern);
  - the augmentation laws, as chronic treatment (modifier-types spec, "Not decided here").
- **Cadence:** yearly from the state pulse, or monthly under fast mode's clock. Rates move within a month of a change
  (probe), so a year's lag is fine.
- **Owner calls:**
  - the list of kept terms (K);
  - whether the engine's starving slope below SoL 4 stays (in K) or the poverty term replaces it;
  - whether starvation's deaths should fall on the young and old (the model's age pattern) or stay flat.

## Step 5: the defines

With M doing the work, the engine's SoL curves only need to sit near the census's typical rates, so M stays small and
the engine-side terms keep their weight. Retune `@max_birthrate`, `@min_birthrate` and the mortality curve ends to the
census's world medians by SoL band (§2.3's table is the starting point).

## Step 6: the base schedules after 1900

- West 1950 reads 60–63 against about 66–69 (the medicine scenarios' band starts at 60 for this reason). Young adults'
  chronic and external base rates are 1836's.
- World growth in 1949 reads +1.4% against history's +1.8%.
- Fit against Clio Infra's life expectancy for 1900–1990 on the late game's saves.

## The gate

1. `demographics_harness.py history` on the gate saves and a 20th-century save:
   - world life expectancy and growth within the targets' bands;
   - no country of 20M people or more shrinking in the model;
   - every `medicine` and `fertility` anchor in band.
2. A fast-mode run with phase 2 on:
   - world population 1836–1900 within ×1.3–×1.7;
   - regional shares moving the right way: Europe up to 1900, Asia's share falling;
   - no country of 20M or more losing people for ten years running outside wars;
   - the census's replay (`demographics_harness.py replay`) exact.
