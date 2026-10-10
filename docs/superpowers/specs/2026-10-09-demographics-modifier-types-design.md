# Demographics: the model's law, technology and institution inputs as modifier types — design

Status: the owner accepted all six owner calls as recommended on 2026-10-09. Stage 1 (mortality) is built (plan `docs/superpowers/plans/2026-10-09-demographics-modifier-types-stage1.md`, fit and evidence in `docs/testing/demographics-fast-run-2026-10-09.md`) with the country/state split below. Parent spec: `2026-10-08-demographics-design.md` (§2.3–§2.5,
§4.2, §8.4). Built after fast mode (#848), which is the in-game loop for the recalibration below.

## The rule

Every input to the census that a law, a technology or an institution changes is a registered modifier type the census
reads with `modifier:`. Hard-coded tables in `demographics_params.py` are proof-of-concept only (owner, 2026-10-09). A
modifier type is legible: the law's or technology's tooltip shows its line, and the state's modifier breakdown names
every source (`scripting_best_practices.md`, "script_only" modifiers for a system that depends on a combination of
laws and techs). `country_fertility_means_add` already works this way.

The model keeps reading the state's own conditions directly: standard of living, literacy, urban share, its own life
expectancy, and its constants. Laws and techs don't set those. Crowding stays in the model for now: vanilla's
`migration_crowding` is a state condition. The urban planning institution's all-or-nothing exemption from it is an
institution term, and could become a type in stage 3.

## What changes

| Today (params, or script) | Becomes (provisional name, scope) | Carrier | Stage |
|---|---|---|---|
| `TECH_MULT` infection, maternal, chronic: the medical techs | `country_infection_treatment_add`, `country_maternal_treatment_add`, `country_chronic_treatment_add` | the techs' `modifier` (INJECT on the base game's, in place on the mod's) | 1 |
| `LAW_MULT` health laws; `INSTITUTION_MULT` health system (0.95 a level) | `state_health_care_access_add` | the three health laws' `institution_modifier` (per level) | 1 |
| `LAW_MULT` police (external), child labour (work), Old Age Pension (chronic); `TECH_MULT` combustion engine (external); `INSTITUTION_MULT` workplace safety (work), consumer protection (external) | `country_external_mortality_mult`, `country_work_mortality_mult`, `country_chronic_mortality_mult` (laws and tech); `state_work_mortality_mult`, `state_external_mortality_mult` (institutions) | the laws' and the tech's `modifier`; Workplace Safety on Regulatory Bodies' and Worker Protections' `institution_modifier`, Consumer Protection on its institution's own `modifier` (check b) | 1 |
| `MEANS_TIERS` (vulcanization, the Pill, modern pharmaceuticals) | `country_contraception_add`: the tier, which the model scales by literacy | the techs' `modifier` | 2 |
| `MEANS_LAW_SHIFT` (State-Sponsored Family Planning +0.1) | `country_fertility_means_add` (exists) | the law's `modifier` | 2 |
| `FEMALE_WORK_SHARE` by women's-rights law | `country_female_work_share_add` (the model's 0.1 plus the law's line) | the six laws' `modifier` | 3 |
| `FAMILY_TRANSPORT_TECHS` | `country_family_migration_add` | the three techs' `modifier` | 3 |
| `LAND_TENURE` (× the state's agrarian share) | `country_land_concentration_add` | the land reform laws, each variant with its own line (as the generator expands them today) | 3 |
| Wealth Concentration's law terms, `te_demog_values.txt:208–270`: Graduated Taxation, economic laws; #822's inheritance laws and amendments (`te_inh_law_target`) | `country_wealth_concentration_add` | the laws' `modifier`; amendments too if they can carry one (check e) | 3 |

The tax code's dividend term stays in script: it is a rate, not a law. Women's-rights work share gets its own type:
vanilla's `state_working_adult_ratio_add` on Women in the Workplace is a different quantity.

## Ruling: the country/state split (stage 1, 2026-10-09)

The provisional names put every mortality type in state scope. Built, the types follow their carriers' scope:
- Treatment and the flat law and tech terms are `country_*` types. Techs' and laws' `modifier` blocks carry them, and the census reads them in state scope as `owner.modifier:`, the path `country_fertility_means_add` already proves.
- Only the per-level institution terms are `state_*` types: health-care access, Workplace Safety and Consumer Protection. A law's `institution_modifier` or an institution's own `modifier` carries them, so they reach incorporated states only.

A mod `state_*` type in a country `modifier` block (check a) is never relied on. If it failed, every treatment would read 0 and nothing would log it.

The cost is where the lines show: a tech's on the country's modifier breakdown, access and the institution terms on the state's. Work and external sum one country type and one state type inside one `(1 + total)`, so within a cause sources still add.

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
  - Charitable and Private Health Insurance's pollution line should vanish, since drugs phase 2's +0.1 cancels
    vanilla's −0.1.

  If the blocks don't sum, the fallback is the census's old `institution_investment_level` ladder in script, which
  loses the tooltip line.
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

## Stages

1. **Mortality**: medicine (access × treatment) and the other causes. This replaces `TECH_MULT`, `LAW_MULT` and
   `INSTITUTION_MULT`. The gate run's largest defect is here: Public Health Insurance in the 1860s gives the adopters
   a life expectancy of 54–56 by 1876 while their peers stay around 43.
2. **Fertility**: the contraception tiers and the family-planning law's means.
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

## Not decided here

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
