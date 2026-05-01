# Benchmark — iteration 1 (`add-formable-country` skill)

| Eval | Configuration | Pass rate | Tokens | Duration |
|---|---|---|---|---|
| eval-1-greater-bulgaria-minor | with_skill | 12 / 12 = 100% | 68,108 | 176.6 s |
| eval-2-pan-slavic-union-major | with_skill | 15 / 15 = 100% | 85,395 | 289.3 s |

## Summary stats (with_skill)

- Total assertions: **27 / 27 = 100%**.
- Mean tokens: 76,752 (σ ≈ 8,644). Both cases comfortably within a single subagent budget.
- Mean duration: 232.9 s (σ ≈ 56 s).

## Patterns

- **Verification-first behavior** — both subagents grepped vanilla before referencing cultures or states. Eval 1 caught and corrected a fabricated state name from the spec (`STATE_NORTHERN_BULGARIA`); eval 2 verified all 60 states in its custom region (25 of which were spot-checked post-hoc and all verified).
- **Tag selection** — eval 1 explicitly rejected the obvious `BUL` because vanilla owns it; chose `GBL`. The skill's "verify it's unused" instruction worked.
- **Grounded names** — neither subagent produced campy names. Eval 1 used "Tsardom of Bulgaria" (real 1908–1946 monarchy) and "Bulgarian National State" (the actual fascist regime name). Eval 2 used "Empire of All the Russias" (the historic All-Russian imperial title), "Orthodox Slavic Patriarchate", "Pan-Slavic Federation".
- **Judgment calls** — eval 2 elected to define a custom `geographic_region_pan_slavic` rather than use the spec's suggested `geographic_region_europe`. The reasoning ("Vanilla Europe pulls in non-Slavic Western and Northern Europe, which would force unification candidates to control half of Iberia/France/Germany/Britain at the 0.5 fraction — thematically wrong") is the kind of judgment the skill's "ask the user / present 2-3 options" guidance is supposed to surface, but here the subagent just decided and documented the tradeoff. This is acceptable for an eval but in a real session would ideally surface to the user via AskUserQuestion.
- **2nd-axis flavor** — eval 2 correctly used priority 5 + `OR { was_formed_from = RUS, ruler ?= { has_culture = cu:russian } }` for the Russian-led monarchy variant. Mirrors the skill's worked Intermarium example.

## Non-discriminating assertions

Without a baseline run (the user opted for a skill-only 2-case eval), the assertions can't separately measure "did the skill help" vs "would Claude do this anyway". A future run with baselines would clarify this.

## Skill issues found

None blocking. Two minor opportunities flagged for a possible iteration:

1. **The skill says "ask the user via AskUserQuestion if any decision is genuinely flexible"** but the subagents tend to decide and document rather than ask. In an eval context that's correct (no user available); in a real session the skill could be more emphatic about *which* decisions warrant a question vs which to decide-and-document.
2. **`organize_loc.py` description ordering** — eval 2's diff added PSU/PSU_ADJ to the existing set; both subagents got this right. No action.

## Conclusion

The skill produces correct, grounded, copy-paste-ready output for both minor and major formations on the first try. Recommendation: ship as-is, revisit only if a real-world use surfaces a gap.
