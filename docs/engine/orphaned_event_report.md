# Orphaned Event Report

Events defined in `events/` with no self-firing mechanism (`mean_time_to_happen`) that are never referenced by any `trigger_event` / dispatch list across `events/`, `common/`, `gui/`. These are unreachable dead content (the engine reports them as `Event X is orphaned` at game start).

- Orphaned (unreviewed): **0**
- Orphaned (REVIEWED-suppressed): **3**

No unreviewed orphaned events. ✅

## REVIEWED-suppressed

- `te_debug_tax.80` — events/te_debug_tax_events.txt (REVIEWED 2026-10-03: console-only customs probe; hidden by design)
- `te_debug_tax.81` — events/te_debug_tax_events.txt (REVIEWED 2026-10-03: console-only customs probe; hidden by design)
- `te_debug_tax.82` — events/te_debug_tax_events.txt (REVIEWED 2026-10-03: console-only customs probe; hidden by design)
