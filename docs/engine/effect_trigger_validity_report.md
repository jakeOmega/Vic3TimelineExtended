# Effect / Trigger Name Validity Report

Lowercase LHS keywords in every script-bearing mod directory (`events/` plus the `common/` entity dirs listed in the audit's `SCAN_ROOTS`) that are neither a known engine effect/trigger/scope/control-flow keyword (per the frozen vanilla catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, which Paradox script never uses. The engine silently ignores these until a runtime game-load `Unknown effect/trigger` error.

Flag kinds: **unresolved-helper-call** is an unknown name in call form (`x = yes` / `x = { ... }`) — typically a scripted effect/trigger that was renamed or deleted while a call site survived (#288). **unknown-name** is any other unknown LHS keyword (#295). **call-syntax** is unquoted `f(...)`. Static-modifier block bodies (`modifier = { ... }`, `member_modifier`, …) are skipped here — their names are validated by `modifier_visibility_audit`.

**effect-in-trigger** is a known effect where the engine reads triggers — a scripted trigger's body, a `limit`, `trigger`, `possible`, `is_shown`, `can_*` or other trigger block (#1142). The engine logs `Unknown trigger type` at load and drops the line; a scope saved there takes `save_temporary_scope_as`, not `save_scope_as`. **trigger-in-effect** is the mirror image: a trigger in an `immediate`, `option`, `effect`, `on_*` or scripted effect body. Both read the effect-only and trigger-only names in `docs/engine/effect_trigger_context_keys.txt` and the mod's own scripted effects and triggers.

- Catalog size: **7536**
- Context catalog: **3657** effect-only, **2595** trigger-only names
- Flags (unreviewed): **0**
- Flags (REVIEWED-suppressed): **4**

No unreviewed effect/trigger name issues. ✅

## REVIEWED-suppressed

- `activate_production_methods` (unresolved-helper-call) — common/decisions/extra_decisions.txt (REVIEWED 2026-10-05: a create_building parameter (effects.log 1.14.5 § create_building), not an effect)
- `activate_production_methods` (unresolved-helper-call) — common/scripted_effects/gm_effects.txt (REVIEWED 2026-10-18: a create_building parameter (effects.log 1.14.5 § create_building), as the landmarks use it)
- `activate_production_methods` (unresolved-helper-call) — common/scripted_effects/gm_landmark_effects.txt (REVIEWED 2026-10-11: a create_building parameter (effects.log 1.14.5 § create_building), not an effect)
- `war` (unresolved-helper-call) — common/scripted_effects/nuclear_exchange_effects.txt (REVIEWED 2026-10-05: create_diplomatic_play parameter, effects.log 1.14.5 section create_diplomatic_play)
