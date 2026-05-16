# Nightly audit — scripted effects, triggers, buttons, progress bars, rules, GUIs, on_actions

For each selected file in `common/scripted_effects/`, `common/scripted_triggers/`, `common/scripted_buttons/`, `common/scripted_progress_bars/`, `common/scripted_rules/`, `common/scripted_guis/`, `common/on_actions/`.

## Checks

- **Parameterization convention.** Helpers using `$VAR$` placeholders follow the documented invocation pattern in `docs/audits/script_parameterization_audit.md`. Flag bespoke patterns where a helper already exists.
- **`<int>`-typed effects don't use script-value passthrough.** Effects whose engine signature takes `<int>` (`add_escalation`, etc.) silently no-op when given a `<script_value>`. Use `while = { count = <sv>  effect = 1 }` instead. (memory: engine doc int signatures)
- **Quoted scripted-trigger-call operators.** `"X.Y(Z)" >= N` and `"X.Y(Z)" <= N` parse-error. Use `>` or `<` only on continuous-value triggers; don't assume integer tiers. (memory: quoted trigger call comparison operators)
- **`any_*` triggers don't take `limit`.** `any_scope_*` triggers accept their predicate inline, not under `limit = { }`. (`docs/guides/scripting_best_practices.md`)
- **Scope movement discipline.** Scripts that change scope (`every_scope_*`, `random_scope_*`, scope-change keys) either save the prior scope before iterating or rely on `scope:x` captures — they don't assume implicit ROOT / THIS persistence.
- **kill_character guard preservation.** Scripted effects that wrap `kill_character` preserve both guards: `place_character_in_void = 6` upstream of the call site, and `exists = scope:X` at the call site. (Procedural `kill_character_audit` catches missing guards; this verifies the wrapper doesn't strip them.)
- **Read-after-write awareness.** Callers don't read `modifier:X` later in the same effect block expecting an earlier `add_modifier` / `remove_modifier` to be visible. (`docs/guides/scripting_best_practices.md`)
- **Workaround removal priority.** If an engine feature has gone from broken to working (per a recent vanilla patch), obsolete workarounds in helpers should come off *before* wiring the now-working feature into new call sites. (memory: workaround priority)
- **Asymmetric outcomes via shared mechanics.** When designing helpers used across player and AI, prefer shared mechanics with law / IG gates over `is_ai`-branched code. (memory: asymmetric outcomes shared mechanics)
