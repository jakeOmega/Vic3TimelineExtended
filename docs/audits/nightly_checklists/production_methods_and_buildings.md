# Nightly audit — production methods, buildings, goods, PMGs, pop needs

For each selected file in `common/production_methods*/`, `common/buildings/`, `common/building_groups/`, `common/goods/`, `common/prestige_goods/`, `common/buy_packages/`, `common/pop_needs/`.

## Checks

- **Balance-band conformance.** New PMs fall within the per-building balance bands in `docs/audits/pm_building_balance_review.md`. Outside-band values are justified in a same-line `# REVIEWED YYYY-MM-DD: reason` comment.
- **Workforce / level-scaled flat-adds projected.** Inside `workforce_scaled` or `level_scaled` blocks, multiply the value by ~100 levels and check the projection is sane. If projection is unbounded, switch to a `_mult` or share-based form. (memory: workforce-scaled flat-adds)
- **Dynamic-pattern registration.** New dynamic-pattern modifiers used in PMs / buildings (`<building>_throughput_add`, `goods_input_<good>_add`, ship axis combos) are registered in `common/modifier_type_definitions/`. (`docs/guides/scripting_best_practices.md`)
- **PM id-based loc keys.** PMs use the default id-based loc key, not `PMG name = "UPPERCASE_LOC_KEY"` overrides — the override pattern breaks the loc-finding convention. (`docs/audits/open_issues.md` L6)
- **INJECT vs redeclare for vanilla extensions.** Files extending vanilla buildings, PMGs, or goods use `INJECT:X = { ... }` rather than redeclaring. (`docs/guides/scripting_best_practices.md`)
- **Silently inert modifier keys.** Modifier keys like `_max_*_add` may be capped by a define already; profession × investment-pool keys only fire on dividend-income pops. Verify any such field actually fires in this configuration before trusting it. (memory: silently inert modifiers)
- **Residual `_add` + `_mult` rounding.** When combining a flat add with a multiplicative bonus that produces small residuals: use `round = yes` not `floor = yes`. `floor` silently kills small bonuses. (memory: round over floor for residuals)
- **Append-anchored at the outer brace.** When the file contains REPLACE: / INJECT: blocks that append to a PM or building, confirm the closing brace count matches the outer entity — a nested append inside the wrong PM still balances. (memory: paradox anchor outer brace)
