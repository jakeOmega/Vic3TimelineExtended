# Nightly audit — localization

For each selected `.yml` file under `localization/english/`. Skip what `loc_coverage_audit`, `concept_reference_audit`, and `localization_accessor_audit` already cover — focus on tone, alignment, and syntax that procedural audits miss.

**Before you start auditing this file**: list the entity-type prefixes you find in its keys (`event_`, `je_`, `law_`, `building_`, `pm_`, `decree_`, etc.). In the run wrap-up, note whether the docs the selector pre-loaded for this file were the right ones, what else you ended up needing, and any prefixes the heuristic didn't predict. This data refines the loc heuristic over time.

## Checks

- **Tone matches the style guide.** Formal but not archaic; modern terminology preferred where the era allows; sardonic / wry register; show-don't-tell. (`docs/guides/event_creation_guide.md` § General Tone and Voice)
- **Bold/italic syntax.** Uses `#b X#!` / `#i X#!` only — never `[b]X[/b]` brackets. Bracket form emits per-render data-system errors and causes synchronous-log-spam-driven lag. (memory: vic3 loc syntax)
- **Scope reference syntax.** Uses typed form `[SCOPE.sCountry('x').GetName]` — not `[scope:x.GetName]`. (`docs/guides/event_creation_guide.md` § Localization Scope References)
- **Accessor-chain semantics.** `[X.Y.Z]` accessor chains return what the surrounding sentence implies. (Catalog correctness is covered by `localization_accessor_audit`; this is the *semantic* check that the chain produces the intended result, not just that it parses.)
- **Mechanical-narrative alignment.** Descriptions don't claim effects the script doesn't produce, and don't omit a major effect the script does produce. Cross-read the description against the source event / law / modifier.
- **Flavor text form distribution.** For event `.f` keys: dialogue-dominant, 3–8 sentences / 50–150 words, anchored in a perspective. Anti-patterns: two-line reportage, subject-less observation, formulaic repetition across a chain. (`docs/guides/event_creation_guide.md` § Flavor Text)
- **No color codes in descriptions.** No `#R`, `#G`, etc. baked into descriptions; flavor text uses `#bold` / `#italic` / `\n` sparingly. (`docs/guides/event_creation_guide.md` § General Tone)
- **Concept link sanity.** `[concept_X]` references point at concepts whose meaning matches the sentence. (Presence is covered by `concept_reference_audit`; this is the semantic match.)
