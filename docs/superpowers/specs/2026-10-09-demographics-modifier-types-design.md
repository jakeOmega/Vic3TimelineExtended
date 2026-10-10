# Demographics: the model's law, technology and institution inputs as modifier types — design

Status: the owner accepted all six owner calls as recommended on 2026-10-09. Stage 1 (mortality) is built (plan `docs/superpowers/plans/2026-10-09-demographics-modifier-types-stage1.md`, fit and evidence in `docs/testing/demographics-fast-run-2026-10-09.md`) with the country/state split below. Stage 2 (fertility) is built (plan `docs/superpowers/plans/2026-10-10-demographics-modifier-types-stage2.md`, fit below). Parent spec: `2026-10-08-demographics-design.md` (§2.3–§2.5,
§4.2, §8.4). Built after fast mode (#848), which is the in-game loop for the recalibration below.

## The rule

Every input to the census that a law, a technology or an institution changes is a registered modifier type the census
reads with `modifier:`. Hard-coded tables in `demographics_params.py` are proof-of-concept only (owner, 2026-10-09). A
modifier type is legible: the law's or technology's tooltip shows its line, and the state's modifier breakdown names
every source (`scripting_best_practices.md`, "script_only" modifiers for a system that depends on a combination of
laws and techs). `country_fertility_means_add` already worked this way (now `state_fertility_means_add`, stage 2).

The model keeps reading the state's own conditions directly: standard of living, literacy, urban share, its own life
expectancy, and its constants. Laws and techs don't set those. Crowding stays in the model for now: vanilla's
`migration_crowding` is a state condition. Since 2026-10-10 infection rises by the state's migration penalty from it,
and the urban planning institution acts through crowding tolerance rather than an exemption, so no type is needed.

## What changes

| Today (params, or script) | Becomes (provisional name, scope) | Carrier | Stage |
|---|---|---|---|
| `TECH_MULT` infection, maternal, chronic: the medical techs | `state_infection_treatment_add`, `state_maternal_treatment_add`, `state_chronic_treatment_add` | the techs' `modifier` (INJECT on the base game's, in place on the mod's) | 1 |
| `LAW_MULT` health laws; `INSTITUTION_MULT` health system (0.95 a level) | `state_health_care_access_add` | the three health laws' `institution_modifier` (per level) | 1 |
| `LAW_MULT` police (external), child labour (work), Old Age Pension (chronic); `TECH_MULT` combustion engine (external); `INSTITUTION_MULT` workplace safety (work), consumer protection (external) | `state_external_mortality_mult`, `state_work_mortality_mult`, `state_chronic_mortality_mult` | the laws' and the tech's `modifier`; Workplace Safety on Regulatory Bodies' and Worker Protections' `institution_modifier`, Consumer Protection on its institution's own `modifier` (check b) | 1 |
| `MEANS_TIERS` (vulcanization, the Pill, modern pharmaceuticals) | `state_contraception_add`: added to the traditional 0.4, the sum scaled by literacy | the techs' `modifier`, with feminism added (owner, 2026-10-10) | 2 |
| `MEANS_LAW_SHIFT` (State-Sponsored Family Planning +0.1) | `state_fertility_means_add` (`country_fertility_means_add` renamed) | the law's `modifier`; Family Limitation's static modifier | 2 |
| `FEMALE_WORK_SHARE` by women's-rights law | `country_female_work_share_add` (the model's 0.1 plus the law's line) | the six laws' `modifier` | 3 |
| `FAMILY_TRANSPORT_TECHS` | `country_family_migration_add` | the three techs' `modifier` | 3 |
| `LAND_TENURE` (× the state's agrarian share) | `country_land_concentration_add` | the land reform laws, each variant with its own line (as the generator expands them today) | 3 |
| Wealth Concentration's law terms, `te_demog_values.txt:208–270`: Graduated Taxation, economic laws; #822's inheritance laws and amendments (`te_inh_law_target`) | `country_wealth_concentration_add` | the laws' `modifier`; amendments too if they can carry one (check e) | 3 |

The tax code's dividend term stays in script: it is a rate, not a law. Women's-rights work share gets its own type:
vanilla's `state_working_adult_ratio_add` on Women in the Workplace is a different quantity.

## Ruling: every type in state scope (owner, 2026-10-10)

All seven types are `state_*`, one for each term, and the census reads each with `modifier:` in state scope.
- **Carriers by kind.** A tech's or law's `modifier` carries treatment, and the police, pension and child-labour terms. It reaches every state the country owns, because states inherit country modifiers, the way a law's `state_education_access_add` reaches its states. A law's `institution_modifier` or an institution's own `modifier` carries access, Workplace Safety and Consumer Protection, per investment level and in incorporated states only.
- **The prefix is convention.** The engine doesn't read it.
- **Every source shows in one place:** the state's modifier breakdown.
- **What it replaced.** The first build split the types (`country_*` read through the owner, as a hedge on check a) and was reverted before merge. Option l of the probe confirms that the inherited lines read in the state.

## Decision 1: how the terms combine

Modifier types sum, like the engine's own `(1 + total)`. Today's tables multiply: the six infection techs compound to
×0.19. The owner's ruling on the health laws (2026-10-09) needs medicine to scale with technology *and* with the health
system's level, which one additive type can't express. Recommended:

- **Within a type, sources add.** The model multiplies *types*.
- **Medicine is access × treatment.** For infection, maternal and chronic deaths:
  `1 − access × treatment`, where
  - access = a base (market and charity medicine, which colonies and 1836 also get) + `state_health_care_access_add`,
    capped at 1;
  - treatment = the cause's `state_<cause>_treatment_add`, capped below 1 (the cap calibrated).

  A health system with no medicine to deliver does nothing, and medicine reaches only as far as access. The health
  laws' `institution_modifier` scales with the institution's level and applies only in incorporated states: the
  owner's ruling, done the engine's own way.
- **Every other term is a plain per-cause multiplier**, `1 + state_<cause>_mortality_mult`, floored.
- **Values are recalibrated in the harness, not transcribed.** ×0.9 × 0.85 … does not become −0.1 − 0.15 …. The model
  and its tests change to the new form first. Then the harness fits the values to §2.4's anchors.
- **The means.** Today the highest tier held applies. As a type, the techs' tiers add. The three techs are not on one
  prerequisite chain (vulcanization, the Pill and modern pharmaceuticals are each off the others' chains: crawled
  2026-10-09). So researching them out of order now gives a different means than today's maximum. `MEANS_CAP` still
  bounds it.

Rejected: an exponential sum (`exp(Σ)`). It keeps compounding, but a tooltip's "−10%" would no longer be what the line
does.

## Decision 2: where the values live

**Recommended: the game files.**
- The values sit in INJECT blocks beside the techs, laws and institutions they belong to. That's where a player and a
  modder see them.
- The Python model takes modifier totals, not sets of laws and techs. A resolver builds those totals for a country
  from the parsed mod (`ModState` applies the INJECTs, and runs from the committed `vanilla_parsed/` without a game)
  and from its save's laws, techs, institution levels and incorporated states.
- `demographics_params.py` keeps only the model's constants: the base access, the floors and caps, and the
  standard-of-living and literacy weights.
- The generator stops writing `te_demog_mult_*`'s ladders of `has_technology_researched`. The script reads
  `modifier:` totals.

**Checks:**
- A registry test fails when a type has no carrier or no loc, or when a table entry the stage removed is still read.
- The existing interpreter runs the script against the model with the modifier totals as fixtures.

Rejected: keeping the values in params and having the generator write the INJECT blocks. It keeps tuning in one
Python file. But a modder editing the law can't change the value there, and a second INJECT of
`institution_modifier` on a law `modified_health_system.txt` already injects is unverified.

## Carriers and what each rests on

- **A tech's `modifier` (INJECT).** Proven by `te_monetary_tech_injections.txt`: the finance techs' injected lines
  were read in game on 2026-09-20 (monetary design §17; `scripting_best_practices.md` § INJECT).
- **A law's `institution_modifier` (INJECT).** Used by `common/laws/modified_health_system.txt` (drugs phase 2) on
  the same three health laws, but not yet read in game: `scripting_best_practices.md` confirms summing INJECTs for
  `modifier` blocks on ranks, techs and laws, not for `institution_modifier` (stage 1's review). Vanilla's Public Health
  Insurance block already carries `state_mortality_mult` −0.05 a level. The new line sits beside it and shouldn't
  replace it. The stage-1 probe (`te_debug_demog.1` option l) reads the access line, and two tooltips tell whether
  the blocks sum:
  - Worker Protections should show vanilla's minimum wage line beside the new work line.
  - The three health laws' pollution line should vanish, since drugs phase 2's lines cancel vanilla's (+0.1
    against −0.1 for Charitable and Private, +0.15 against −0.15 for Public).

  If the blocks replace each other instead (last wins), Worker Protections loses its minimum wage line, and the health
  laws show a +10% or +15% pollution-reduction line (the mod's value alone). The access line shows either way, since it
  sits in the mod's block. The probe's `access=` read in the capital is what proves the census can read it. The fallback
  is the census's old `institution_investment_level` ladder in script, which loses the tooltip line. Last-wins would
  also mean drugs phase 2 already dropped vanilla's own health-law lines (Public Health Insurance's
  `state_mortality_mult` −0.05 a level).
- **A law's `modifier` (INJECT).** Used throughout the mod.
- **New types** go in `demographics_modifier_types.txt`:
  - `script_only = yes` (the engine never consumes them; they still render in tooltips);
  - `decimals` set so a per-level 0.02 doesn't render "+0%" (`modifier_visibility_audit`);
  - a name and `_desc` for each (`loc_coverage_audit`).

## Engine checks before building

a. A mod-registered `state_*` type in a tech's country `modifier` reads in state scope through `modifier:`. Vanilla's
   state types flow down this way (`scripting_best_practices.md` § the mask); a mod type is untested.
b. A mod type in a law's `institution_modifier`, and in an institution's own `modifier`, scales with the investment
   level and reads 0 in an unincorporated state.
c. The new lines show in the tech and law tooltips, and the state's modifier breakdown names their sources.
d. A registered type with no source reads 0. Already confirmed in #834.
e. Whether an amendment can carry a `modifier` block, for #822's amendment terms. If not, they stay in script.

A probe in the style of #824 answers a–c and e in one short game.

**Results (2026-10-10, `te_debug_demog.1` option l, a 1955 save at Ministry of Health and Workplace Safety level 5):**
- **a and b pass.** In the capital and in an unincorporated state, the techs' and laws' lines read the same (treatment 0.83 infection and 0.95 maternal; external +0.2). Access read 0.5 in the capital (0.10 × 5) and 0 in the other state; Workplace Safety read −0.5 and 0. The composed figures matched the model: maternal 97.15 and 415.40 a 100,000 births.
- **c passes.** The owner confirmed the tech and health-care lines in game.
- **The logs are clean.** Neither carries an error from the types or the generated values.
- **e is not run;** it belongs to stage 3.

## Stages

1. **Mortality**: medicine (access × treatment) and the other causes. This replaces `TECH_MULT`, `LAW_MULT` and
   `INSTITUTION_MULT`. The gate run's largest defect is here: Public Health Insurance in the 1860s gives the adopters
   a life expectancy of 54–56 by 1876 while their peers stay around 43.
2. **Fertility**: the contraception tiers and the family-planning law's means. Built (2026-10-10); see "Stage 2's fit"
   below.
3. **The rest**: Wealth Concentration's law terms, the female work share, family migration. Wealth Concentration's
   terms already show as bars in the panel, and #842/#843 have just retuned them, so this stage gains the least.

Each stage is one PR: the types, their carriers and loc, the model and resolver, the generator change, tests and
recalibration.

## Gate for each stage

- A fresh 1836 census is unchanged where no carrier applies. Treatment is 0, so medicine's factor is exactly 1.
- Replaying the gate run's 1836–1890 inputs offline, the 1860s–70s Public Health Insurance adopters (BEL, SAR, SWE,
  GBR) sit within about 3 years of their peers' life expectancy at the same standard of living (54–56 against 43
  by 1876 today).
- §2.4's anchors still hold for Britain in 1900 and 1950.
- A fast-mode run (#848) shows the same in game.

## Stage 2's fit (2026-10-10)

The means to plan a family = (0.4 + `state_contraception_add`, at most 1) × (0.3 + 0.7 × literacy) +
`state_fertility_means_add`, at most 0.95. Stage 1's fit brought Britain's 1900 life expectancy from 54.8 to a
historical 46.1, which weakened the child-survival term: Britain 1900 read 4.27 children per woman against about 3.5.
`demographics_harness.py fertility` checks seven scenarios against §2.3's bands. The fit varied the era-3 pair's sum,
the Pill and modern pharmaceuticals in 0.05 steps, with the traditional 0.4 and the desired-fertility weights fixed, so
the 1836 census is unchanged (no country starts with an era-3 tech). Every means tech keeps a line of at least 0.05, so
each shows one in its tooltip. It ranked by distance outside the bands, then by the squared distance to history
(Britain 1900 3.5, the West 1950 2.9 and 1990 1.7, India 1975 5.2).

| Carrier | Contraception |
|---|---|
| `vulcanization` (era 3, the methods) | +0.20 |
| `feminism` (era 3, the will to use them; owner, 2026-10-10) | +0.15 |
| `contraceptive_pill` (era 7) | +0.05 |
| `modern_pharmaceuticals` (era 8) | +0.05 |
| State-Sponsored Family Planning (Fertility Control) | +0.10 |

| Children per woman | Before | After | History |
|---|---|---|---|
| Britain 1900 | 4.27 | 3.85 | about 3.5 |
| West 1950 | 3.07 | 2.55 | 2.5 (Europe) to 3.5 (US) |
| West 1990 | 1.47 | 1.59 | about 1.7 |
| India 1975 | 5.34 | 5.34 | about 5.2 |
| 1836 rows (reference, Britain, France) | 6.03, 5.57, 4.90 | unchanged | about 5.2, 5, 3.8 |

- **The tiers add**, so research order matters. The Pill without vulcanization or feminism gives 0.4 + 0.05.
- **The Pill's line is small.** The West reached 2.5–3 children per woman before it, so the fit puts the transition's
  means on the era-3 pair. What the anchors fix is two sums: the era-3 pair's (0.35) and the Pill's and modern
  pharmaceuticals' (0.05–0.10); how each sum splits is a judgment. With the 0.05 floor, a Pill line of +0.10 fits
  almost as well (West 1990 1.47); without it, the Pill +0.10 and modern pharmaceuticals 0 fit slightly better (West
  1990 1.59), at the cost of a means tech with no line.
- **The 1836 rows stay high.** Lowering them needs the traditional means or the desired-fertility weights, which moves
  every 1836 census: phase 2's calibration (owner, 2026-10-10).

## Not decided here

- **The human augmentation laws (owner, 2026-10-10).** Medical Augmentation Only also links the Ministry of Health, but it gets no access line: access is how many people reach care, and the health law sets that. All four augmentation laws already cut engine mortality: Unrestricted −5% flat; Medical Only, Regulated Market and Mandatory −2% a level of their institutions. When phase 2 moves engine mortality into the census, they become census lines together, as chronic treatment, which reaches only as far as access does. A starting point: Medical Augmentation Only +0.10, Unrestricted and Regulated Market +0.05, with the chronic cap raised from 0.8 to about 0.85. Giving Medical Only alone a line now would make it the census's best choice without anyone deciding so.

- **Phase 2's double counting.** Once the model drives the engine's deaths (§8.4), vanilla's own Public Health
  Insurance mortality cut and the mod's medical techs' flat cuts count twice. §8.4 already removes the mod's. Vanilla's
  would need an inverse INJECT (the monetary pattern). That is phase 2's call.
- **Save compatibility.** A game saved before a stage reads the new modifiers on load, and its rates move once at the
  next step. No migration.

## Owner calls

1. The combination rule: access × treatment for medicine, plain additive per-cause multipliers for the rest.
2. The game files as the source of truth, read by a Python resolver.
3. The means' tiers adding (a different means for out-of-order research), or another rule.
4. A base access for countries and colonies with no health system: the concept now, its value from calibration.
5. Whether #822's inheritance laws and amendments move in stage 3 (they already show in the panel), subject to check e.
6. The type names above (provisional).
