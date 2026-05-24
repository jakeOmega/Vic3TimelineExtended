# Orphaned Event Report

Events defined in `events/` with no self-firing mechanism (`mean_time_to_happen`) that are never referenced by any `trigger_event` / dispatch list across `events/`, `common/`, `gui/`. These are unreachable dead content (the engine reports them as `Event X is orphaned` at game start).

- Events defined: **734** (dispatch-required candidates: **734**)
- Distinct referenced ids seen: **737**
- Orphaned (unreviewed): **0**
- Orphaned (REVIEWED-suppressed): **0**

No unreviewed orphaned events. ✅
