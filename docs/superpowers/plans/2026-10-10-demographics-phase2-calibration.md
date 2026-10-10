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

- Infection ×(1 + clamp((9 − SoL) / 4, 0, 1)), state by state: world life expectancy 31–32 (from 37–39), world growth
  about 1.0% a year (from 1.7%), China +0.3% by 1887. Every medicine and fertility anchor stays in its band, though they
  barely test the term. The West pays a little: Britain 1837 36 (history 41), Denmark 33 (41).
- `demographics_harness.py history SAVE... --anchors CSV` and `scripts/analysis/fetch_history_anchors.py`.
- **Owner call:** the strength. ×2 at SoL 5 is built; ×2.25–×3 bring world growth to history's 0.6–0.85% but make China
  shrink by the 1880s in the gate game (the table in the results doc).

## Step 2: fertility against history

**Tooling (built, the second PR).**
- `fetch_history_anchors.py` adds Gapminder's children per woman (open-numbers' `ddf--gapminder--fertility_rate`, from
  1800) as the `tfr` measure, and `history` prints it beside the model's.
- The harness reads France's Family Limitation from a save: a country's timed modifiers, in
  `demographics_save_inputs.STATIC_MEANS_ADD`.

**What it shows** (gate run, state by state, with the poverty term): the model's children per woman run 4.3–6.1;
history's run 3.2–7.1.

| Too high (model − history) | 1837 | 1887 | Too low | 1837 | 1887 |
|---|---|---|---|---|---|
| Denmark | +1.7 | +1.4 | Persia | −1.0 | −1.2 |
| Portugal | +1.4 | +1.4 | Turkey | −0.9 | −1.3 |
| Japan | +1.3 | +1.4 | Mexico | −0.8 | −1.3 |
| France (with Family Limitation) | +1.1 | +1.1 | Peru | – | −1.3 |
| Sweden | +1.1 | +0.8 | Russia | −1.0 | −0.7 |
| Britain | +1.0 | +0.2 | Argentina | −0.9 | −0.4 |

China +0.6 and +0.5, India +0.0 and +0.1, Egypt +0.0 and −0.3. The world average is about right (5.95 and 5.74).

**Why the inputs can't close it.** The spread comes mostly from marriage:
- late marriage and lifelong celibacy in north-western Europe (the "European marriage pattern", west of a line from
  Trieste to St Petersburg);
- Tokugawa Japan's small families;
- early and universal marriage in the Middle East, Russia and Latin America.

The game carries none of this. SoL and literacy don't line up with it either: Japan and Persia share SoL 6.6, and
history has them at 4.5 against 7.1.

**Owner call (design, not fitting):**
- a regional marriage regime, as Family Limitation is for France but general: a starting practice that drifts and
  spreads (§13's proposal);
- or accept the compressed spread and fit only the world level and the wealth curve's ceiling.

Before the owner's call, the fit can still:
- raise the wealth curve's ceiling for the poorest (history's high-fertility societies reach 7, the model 6.2);
- check the education weight against the West's decline after 1870 (Britain 1887 is within 0.2 already).

## Step 3: the gap the game's inputs can't see (India, the tropics)

- India grows +1.5% a year in the model against +0.8% in history, at life expectancy 35 against 24. Nothing in its
  inputs (SoL 8.4, literacy 0.19) separates it from Russia or Spain.
- **To look at, in this order:**
  1. The base game's harvest conditions, `disease_outbreak` among them, which `pharmaceuticals` reduces. If they raise
     the engine's deaths, they already apply on top in phase 2.
  2. The engine's starvation, which phase 2 keeps (step 4).
  3. A disease-environment term from state traits. The malaria traits cover only sub-Saharan Africa and Indonesia;
     a broader one would mean new traits, an owner call.
- **Checked (2026-10-10):** the base game has no disease-environment input to use.
  - `disease_outbreak`'s trigger, `is_vulnerable_to_disease_outbreak`, is `always = yes`, so every state qualifies.
  - The outbreak changes only throughput and peasants' consumption, not deaths.
  - Two harvest conditions add `state_mortality_mult` +0.05 each; the engine keeps those on top in phase 2.
  - The malaria traits are the only geographic disease input, and they cover sub-Saharan Africa and Indonesia only.
- **So the options are:**
  - a new geographic term (the tropics' and the monsoon belt's infection, which quinine, malaria prevention and
    sanitation techs switch off), an owner call;
  - leaving India's gap to the engine's starvation and the wars of phase 2's runs, and measuring what is left.
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
  (`extra_defines.txt`), and M nets the bare curve out. So the model's poverty term, ×2 at SoL 5 and below, would
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
