# Effect / Trigger Name Validity Report

Lowercase LHS keywords in `events/`, `common/scripted_effects`, `common/scripted_triggers`, `common/on_actions` that are neither a known engine effect/trigger/scope/control-flow keyword (per the frozen vanilla catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, which Paradox script never uses. The engine silently ignores these until a runtime game-load `Unknown effect/trigger` error.

- Files scanned: **105**, keys checked: **66240**
- Catalog size: **6924** + mod-defined names: **1326**
- Flags (unreviewed): **0**
- Flags (REVIEWED-suppressed): **0**

No unreviewed effect/trigger name issues. ✅
