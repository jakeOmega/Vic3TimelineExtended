# Effect / Trigger Name Validity Report

Lowercase LHS keywords in every script-bearing mod directory (`events/` plus the `common/` entity dirs listed in the audit's `SCAN_ROOTS`) that are neither a known engine effect/trigger/scope/control-flow keyword (per the frozen vanilla catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, which Paradox script never uses. The engine silently ignores these until a runtime game-load `Unknown effect/trigger` error.

Flag kinds: **unresolved-helper-call** is an unknown name in call form (`x = yes` / `x = { ... }`) — typically a scripted effect/trigger that was renamed or deleted while a call site survived (#288). **unknown-name** is any other unknown LHS keyword (#295). **call-syntax** is unquoted `f(...)`. Static-modifier block bodies (`modifier = { ... }`, `member_modifier`, …) are skipped here — their names are validated by `modifier_visibility_audit`.

- Roots scanned: **16**, files scanned: **192**, keys checked: **95127**
- Catalog size: **7145** + mod-defined names: **1200**
- Flags (unreviewed): **0**
- Flags (REVIEWED-suppressed): **0**

No unreviewed effect/trigger name issues. ✅
