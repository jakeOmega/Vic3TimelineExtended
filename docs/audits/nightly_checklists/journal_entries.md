# Nightly audit — journal entries

For each JE file selected, walk every journal entry and apply these checks.

## Checks

- **Building-block completeness.** The JE has the components per the canonical idiom: scripted progress bar or scripted buttons for interaction, parameterized scripted effects/triggers for logic, static modifiers for unit effects, script values for multipliers, on_actions wiring (monthly/yearly pulses), events for state changes, modifier type definitions for any dynamic patterns. Flag missing wiring. (`docs/systems/mod_systems.md` § Building blocks; `CLAUDE.md`)
- **State-scoped scaling lives in state pulses.** Re-applying state-scoped modifiers via `add_modifier { name = X multiplier = <sv> }` must run from `on_yearly_pulse_state`, not law / treaty / building hooks (which have unreliable scope chains for state-targeted script values). (`docs/guides/scripting_best_practices.md`)
- **Payoff visibility.** Completion/failure effects produce a player-visible payoff (notification, modifier, country flag, unlock) and the payoff matches the arc described in the JE's loc strings.
- **Gating.** The JE is gated behind a `game_rule` toggle, an era trigger, or an unlocking condition — never globally always-on without a documented reason. (`README.md` game rules; `docs/systems/mod_systems.md`)
- **Dynamic-pattern registration.** New dynamic-pattern modifiers used inside the JE's modifier applications (`<building>_throughput_add`, `goods_input_<good>_add`, ship axis combos, building/state-building patterns) are registered in `common/modifier_type_definitions/`. The engine silently ignores unregistered patterns. (`docs/guides/scripting_best_practices.md`)
- **INJECT vs redeclare.** If extending a vanilla JE, the file uses `INJECT:X = { ... }` not a top-level redeclaration. Top-level collisions are silently dropped. (`docs/guides/scripting_best_practices.md`)
- **Pulse-driven re-application pattern.** Pulse re-applications use the dynamic-modifier scaling pattern (`add_modifier { name = X multiplier = <sv> }`), not per-tick `add_*` effect spam. (`docs/systems/mod_systems.md`)
- **Modifier-duration units.** `short_modifier_time` / `normal_modifier_time` / `long_modifier_time` / `very_long_modifier_time` are days, not months — flag any usage that implies months were intended (off by 30×). (`docs/guides/scripting_best_practices.md`)
