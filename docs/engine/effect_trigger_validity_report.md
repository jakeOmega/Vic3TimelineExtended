# Effect / Trigger Name Validity Report

Lowercase LHS keywords in every script-bearing mod directory (`events/` plus the `common/` entity dirs listed in the audit's `SCAN_ROOTS`) that are neither a known engine effect/trigger/scope/control-flow keyword (per the frozen vanilla catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, which Paradox script never uses. The engine silently ignores these until a runtime game-load `Unknown effect/trigger` error.

Flag kinds: **unresolved-helper-call** is an unknown name in call form (`x = yes` / `x = { ... }`) — typically a scripted effect/trigger that was renamed or deleted while a call site survived (#288). **unknown-name** is any other unknown LHS keyword (#295). **call-syntax** is unquoted `f(...)`. Static-modifier block bodies (`modifier = { ... }`, `member_modifier`, …) are skipped here — their names are validated by `modifier_visibility_audit`.

- Roots scanned: **16**, files scanned: **250**, keys checked: **104084**
- Catalog size: **7145** + mod-defined names: **2258**
- Flags (unreviewed): **0**
- Flags (REVIEWED-suppressed): **4**

No unreviewed effect/trigger name issues. ✅

## REVIEWED-suppressed

- `ai_acceptance_max` (unknown-name) — common/diplomatic_plays/te_un_mandate_play.txt:54 (REVIEWED 2026-09-18: diplomatic-play field, not an effect/trigger — vanilla dp_return_state uses it (game/common/diplomatic_plays/00_diplomatic_plays.txt:146). effect_trigger_validity_audit has no schema for this entity type.)
- `second_desc` (unknown-name) — common/scripted_progress_bars/extra_progress_bars.txt:32 (REVIEWED 2026-09-20: scripted-progress-bar field, not an effect/trigger — vanilla 00_great_game_progress_bars.txt:4 uses it; the audit has no schema for this entity type)
- `can_use_obligations` (unresolved-helper-call) — common/diplomatic_actions/un_lobbying.txt:61 (REVIEWED 2026-09-18: diplomatic-action field, not an effect/trigger — vanilla violate_sovereignty uses it (game/common/diplomatic_actions/03_violate_sovereignty.txt:8). effect_trigger_validity_audit has no schema for this entity type.)
- `decline_effect` (unresolved-helper-call) — common/diplomatic_actions/un_lobbying.txt:128 (REVIEWED 2026-09-18: diplomatic-action field, not an effect/trigger — vanilla violate_sovereignty uses it (game/common/diplomatic_actions/03_violate_sovereignty.txt:66). effect_trigger_validity_audit has no schema for this entity type.)
