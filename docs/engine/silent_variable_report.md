# Silent Variable Report

Options of visible mod events that change a variable the UI displays without any tooltip saying so. `change_variable` / `set_variable` render nothing, so the player sees the number move after the click but was never told. Wrap the write in `custom_tooltip = { text = <key> <effects> }` naming the change.

- Events scanned: **797**
- Options scanned: **1974**
- Displayed variables: **370** scope, **158** global
- Silent writes (unreviewed): **0**
- Silent writes (REVIEWED-suppressed): **1**
- Stale `(silent_variable)` tags: **0**

No unreviewed silent writes. ✅

## REVIEWED-suppressed

- `un_events.1` option `un_events.1.a` — events/un_events.txt:78 — global `un_hq_country` (REVIEWED 2026-09-25: the un_headquarters_modifier beside it shows as "UN Headquarters Host")
