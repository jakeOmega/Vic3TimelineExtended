# Nightly audit — technology

For each selected file in `common/technology/`.

## Checks

- **Era / tree placement.** Tech sits in the correct era and tree per the baseline in `docs/audits/mod_only_tech_modifier_baseline.md`. Out-of-band placement needs a same-line `# REVIEWED YYYY-MM-DD: reason`.
- **Prereq chain sanity.** No orphans (tech unreachable from era root), no cycles, no anachronisms (era-N tech requiring era-N+2 prereq). Cross-check against vanilla tech files for similar-era patterns.
- **Unlock references resolve.** All entities named in `unlocking_*` (PMs, buildings, laws, decrees, etc.) exist in the loaded mod or vanilla data. The engine silently ignores unlocks pointing at missing entities.
- **Modifier density.** Modifier density is within the mod's baseline band for the tech's era and tree per the baseline doc. Dense outliers warrant a check.
- **Dynamic-pattern registration.** Any dynamic-pattern modifier the tech unlocks is registered in `common/modifier_type_definitions/`. (`docs/guides/scripting_best_practices.md`)
- **Tone and terminology.** Tech name + description follow the mod's general voice (formal-but-not-archaic, modern terms where the era allows). Late-era techs especially should avoid quaint vocabulary that breaks immersion. (`docs/guides/event_creation_guide.md` § General Tone)
