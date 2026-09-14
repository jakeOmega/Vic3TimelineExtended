# Effect / Trigger Name Validity Report

Lowercase LHS keywords in the mod's script that are neither a known engine effect/trigger/scope/control-flow keyword (per the frozen vanilla catalog) nor a mod-defined name — plus `funcname(...)` call-syntax, which Paradox script never uses. The engine silently ignores these until a runtime game-load `Unknown effect/trigger` error.

Roots scanned:

- `events/` — whole file
- `common/scripted_effects/` — whole file
- `common/scripted_triggers/` — whole file
- `common/on_actions/` — whole file
- `common/script_values/` — whole file
- `common/diplomatic_actions/` — script blocks only: `accept_effect`, `accept_score`, `auto_break_effect`, `evaluation_chance`, `junior_accept_score`, `manual_break_effect`, `monthly_effect`, `possible`, `potential`, `propose_score`, `requirement_to_maintain`, `second_state_trigger`, `selectable`, `show_about_to_break_warning`, `will_break`, `will_propose`, `will_select_as_second_state`
- `common/journal_entries/` — script blocks only: `can_deactivate`, `can_revolution_inherit`, `complete`, `current_value`, `custom_completion_header`, `custom_failure_header`, `custom_on_completion_header`, `custom_on_failure_header`, `event_outcome_activated_effect_desc`, `event_outcome_completed_effect_desc`, `event_outcome_failed_effect_desc`, `fail`, `goal_add_value`, `immediate`, `invalid`, `is_shown_when_inactive`, `on_complete`, `on_fail`, `on_invalid`, `on_monthly_pulse`, `on_timeout`, `on_weekly_pulse`, `on_yearly_pulse`, `possible`, `progress_desc`, `should_be_pinned_by_default_uninvolved_or_context`, `status_desc`, `weight`
- `common/scripted_buttons/` — script blocks only: `ai_chance`, `effect`, `possible`, `visible`
- `common/decisions/` — script blocks only: `ai_chance`, `is_shown`, `possible`, `when_taken`
- `common/laws/` — script blocks only: `ai_enact_weight_modifier`, `ai_impose_chance`, `ai_will_do`, `can_enact`, `can_impose`, `is_visible`, `on_activate`, `on_deactivate`, `on_enact`
- `common/diplomatic_plays/` — script blocks only: `on_war_begins`, `on_war_end`, `on_weekly_pulse`, `possible`, `selectable_in_lens`
- `common/treaty_articles/` — script blocks only: `can_ratify`, `company_valid_trigger`, `conditions`, `cost`, `evaluation_chance`, `infamy`, `inherent_accept_score`, `maneuvers`, `on_break`, `on_entry_into_force`, `on_withdrawal`, `possible`, `quantity_input_value`, `quantity_max_value`, `quantity_min_value`, `requirement_to_maintain`, `state_valid_trigger`, `visible`
- `common/power_bloc_principles/` — script blocks only: `ai_weight`, `possible`, `visible`

- Files scanned: **186**, keys checked: **89946**
- Catalog size: **7145** + mod-defined names: **2008** + event targets: **336**
- Flags (unreviewed): **2**
- Flags (REVIEWED-suppressed): **0**

## Unreviewed

- `modulo` (unknown-name) — common/script_values/te_construction_market_pulse_values.txt:19 — `modulo = 7`
- `round_to` (unknown-name) — common/script_values/te_construction_market_ai_values.txt:71 — `round_to = 1`

Fix the keyword, or add an inline `# REVIEWED YYYY-MM-DD: rationale` on the line if it is a false positive (e.g. a lowercase scripted-effect parameter).
