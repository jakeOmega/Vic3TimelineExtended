# Script Parameterization Audit

This note records the repo's established `$PLACEHOLDER$` substitution pattern for scripted effects, triggers, and values, along with the current high-value candidates for further cleanup. The goal is to make future refactors smaller and safer, not to encourage broad rewrites for their own sake.

## Established Repo Pattern

The repo already uses parameterized helpers in several systems:

| File | Symbol | Parameters | Notes |
|---|---|---|---|
| [common/scripted_effects/covert_warfare_effects.txt](../common/scripted_effects/covert_warfare_effects.txt) | `covert_op_track_targets` | `$TYPE$`, `$ACTION$`, `$DEFENSE_MOD$` | Main reference pattern: one shared helper called repeatedly with named args |
| [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt) | `st_res_rebuild_good_flow_modifiers_effect` | `$GOOD$` | Building-scoped helper behind explicit grain/ammunition/oil wrappers |
| [common/scripted_triggers/covert_warfare_triggers.txt](../common/scripted_triggers/covert_warfare_triggers.txt) | `covert_ops_type_below_cap` | `$TYPE$` | Same placeholder style in trigger form |
| [common/scripted_effects/cultural_hegemony_effects.txt](../common/scripted_effects/cultural_hegemony_effects.txt) | `ch_apply_primary_or_fallback_movement_pressure` | `$PRIMARY$`, `$FALLBACK_1$`, `$FALLBACK_2$`, `$MODIFIER$`, `$FALLBACK_MODIFIER$`, `$MONTHS$`, `$DECAYING$` | Example of a more complex multi-parameter helper |
| [common/scripted_effects/fmc_build_effects.txt](../common/scripted_effects/fmc_build_effects.txt) | `fmc_replace_building`, `set_specified_building_level`, related helpers | `$OLD_TYPE$`, `$NEW_TYPE$`, `$SPEC_TYPE$`, `$SPEC_LEVEL$`, `$ADD_LEVEL$` | Building-type substitution pattern |
| [common/scripted_effects/trade_partner_effects.txt](../common/scripted_effects/trade_partner_effects.txt) | `store_trade_partner_data` | `$RANK$` | Rank-indexed helper |
| [common/scripted_effects/space_race_effects.txt](../common/scripted_effects/space_race_effects.txt) | `sr_complete_milestone_effect_base`, `sr_apply_milestone_reward_base`, `sr_cleanup_milestone_variables_effect`, `sr_monthly_progress_update_effect` | `$MILESTONE$`, `$RISK$` | Drives 7 milestone JEs from a single base each. Concrete `sr_complete_<X>_effect` / `sr_apply_<X>_reward` wrappers preserved as named entry points for events/. |
| [common/scripted_effects/extra_effects.txt](../common/scripted_effects/extra_effects.txt) | `generic_wonder_construction_base` | `$WONDER$`, `$MAX_LEVEL$` | One 19-branch level-up chain handles 7 wonders (different caps); each branch guarded by `b:building_$WONDER$.level < $MAX_LEVEL$`. See `scripting_best_practices.md` § "Numeric placeholder substitution into trigger guards". |
| [common/scripted_effects/heir_education_effects.txt](../common/scripted_effects/heir_education_effects.txt) | `heir_ed_gain_base` | `$VAR$`, `$TRAIT$` | Drives 7 of 8 heir-education focus gains (conservative stays inline — only negative-add case). |
| [common/scripted_triggers/misc_triggers.txt](../common/scripted_triggers/misc_triggers.txt) | `is_industrial_production_allowed`, `is_extraction_industry_allowed`, `is_great_or_major_power`, `no_duplicate_treaty_article` | (none / `$ARTICLE_TYPE$`) | Pure-condition triggers replacing 33+10+20 inline copies. See `scripting_best_practices.md` § "Industry-Ban Triggers for New Buildings". |
| [common/scripted_triggers/space_race_triggers.txt](../common/scripted_triggers/space_race_triggers.txt) | `sr_milestone_followup_is_shown` | `$PREREQ$`, `$TECH$` | JE `is_shown_when_inactive` composer for prereq-gated milestones. |
| [common/scripted_effects/extra_effects.txt](../common/scripted_effects/extra_effects.txt) | `remove_modifier_if_exists_effect` | `$MODIFIER$` | Idiomatic conditional removal — useful primitive for cleanup helpers. |
| [common/scripted_effects/extra_effects.txt](../common/scripted_effects/extra_effects.txt) | `remove_banking_planning_modifiers_effect`, `remove_banking_cooperative_modifiers_effect`, `remove_banking_market_modifiers_effect` | (none — single-hop refactor) | Collapsed 30 per-modifier `je:je_banking_cycle = { remove_modifier = X }` calls into one scope hop per helper. Names preserved; behavior identical (`remove_modifier` is idempotent). |
| [common/scripted_effects/space_race_effects.txt](../common/scripted_effects/space_race_effects.txt) | `sr_apply_safety_review_to_milestone_base`, `sr_apply_progress_loss_base`, `sr_clear_failed_flag_base`, `sr_boost_active_milestone_base` | `$MILESTONE$`, `$MULT$` | Five 8-iteration helpers (`sr_temporary_safety_review_effect`, `sr_apply_ambitious_failure_progress_loss`, `sr_apply_safe_setback_progress_loss`, `sr_clear_failed_milestone_flags`, `sr_boost_active_milestones`) collapsed via Style B inline orchestrators. ~200 lines saved. |
| [common/scripted_effects/space_race_effects.txt](../common/scripted_effects/space_race_effects.txt) | `sr_clear_milestone_cost_modifiers_base`, `sr_apply_milestone_cost_modifiers_base` | `$MILESTONE$` | `sr_recalculate_cost` two-loop refactor; `?=` operator preserved on the clear base so inactive JEs silently no-op. ~67 lines saved. |
| [common/scripted_effects/space_race_effects.txt](../common/scripted_effects/space_race_effects.txt) | `sr_cleanup_milestone_if_inactive_base` | `$MILESTONE$` | `sr_cleanup_inactive_space_race_milestones` standard-8-token refactor; `interstellar_results` stays inline (different 2-var set). ~145 lines saved. |
| [common/scripted_effects/banking_cycle_effects.txt](../common/scripted_effects/banking_cycle_effects.txt) | `apply_banking_crash_softening_option_effect` | `$TT_KEY$`, `$CYCLE_ADD$`, `$MOMENTUM_ADD$`, `$COST_SCALE$`, `$INTERVENTION$`, `$RADICALS$` | 10 of 12 options of `minor_events_timelineextended.6` collapsed; `option_a` and `capital_controls` stay inline (don't fit the shape). $RADICALS$ interpolates into `add_radicals { value = $RADICALS$_radicals }`. ~143 lines saved. |
| [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt) | `st_res_increase_rate_base`, `st_res_decrease_rate_base` | `$GOOD$` | 14 per-good rate-adjustment effects collapse to single-line wrappers around two bases. Two bases (instead of one with `$DIRECTION$` substituting an operator keyword) keeps substitution purely value-based. Wrapper names preserved because `st_res_buttons.txt` references them; buttons themselves stay as concrete UI declarations (codebase has no parameterized scripted_button precedent). ~60 lines saved. |
| [common/scripted_effects/extra_effects.txt](../common/scripted_effects/extra_effects.txt) | `gw_fire_warming_threshold_event`, `gw_fire_cooling_threshold_event` | `$THRESHOLD$`, `$FLAG$`, `$EVENT_ID$`, `$PREREQ$` (cooling only) | 9 inline `if temp threshold + every_country trigger_event` blocks in `extra_on_actions.txt` on_monthly_pulse collapsed to 9 single-line helper calls listing the (threshold, flag, event-id, prereq) tuple per row. Float text-substitution into trigger guards (`temperature_anomaly_display >= $THRESHOLD$`) follows established precedent. ~73 lines saved. |
| [common/scripted_effects/agricultural_diffusion_effects.txt](../common/scripted_effects/agricultural_diffusion_effects.txt) | `agdiff_dispatch_if_first`, `agdiff_backfill_one_tech` | `$TECH$` | Style A: 5 inline `if has_technology_researched + NOT world_first guard + agdiff_on_<TECH>_researched = yes` blocks in `agricultural_diffusion_on_action` (extra_on_actions.txt) and 5 inline `has_global_variable + has_modifier` blocks in `agdiff_backfill_diffusion_for_country` collapsed to single-line helper calls. Per-tech `agdiff_on_<TECH>_researched` wrappers preserved (documented greppability choice). Demonstrates `$TECH$` substitution on the **LHS of an effect call** (`agdiff_on_$TECH$_researched = yes`) — first use of this in the codebase, confirmed parses cleanly. Closes #122. ~30 lines saved. |

### Conventions that already work well here

- Use short, descriptive uppercase placeholder names.
- Document parameters and scope immediately above the shared helper.
- Pass arguments by name at each call site.
- Keep explicit wrappers or unrolled callers when the concrete types are fixed and finite.
- If a repeated block includes a scope bridge, keep the bridge in the outer orchestrator when one shared hop is enough.
- **Style A (per-instance wrappers) vs Style B (inline orchestrator)** — choose based on caller surface. Style A: keep concrete `helper_<X>` wrappers when external code (buttons, events, JEs) references per-instance names, e.g. `st_res_increase_grain_rate_effect` is called by name from `st_res_buttons.txt`, and `sr_complete_suborbital_effect` is called by name from `events/space_race_events.txt`. Style B: skip wrappers and inline the iteration in the orchestrator when only the orchestrator itself is the external entry point, e.g. `sr_recalculate_cost`, `sr_cleanup_inactive_space_race_milestones`, `sr_temporary_safety_review_effect`. Mixing both in the same file is fine — pick per helper based on the calling code.

## Strategic Reserve Implementation

`st_res_rebuild_hub_flow_modifiers_effect` in [common/scripted_effects/st_res_effects.txt](../common/scripted_effects/st_res_effects.txt) now uses this pattern.

### Current shape

1. Country scope computes shared locals for grain, ammunition, and oil.
2. The effect performs a single `random_scope_building` hop into `building_strategic_reserve_hub`.
3. Inside building scope, the orchestrator now calls three explicit wrappers:
   - `st_res_rebuild_grain_flow_modifiers_effect`
   - `st_res_rebuild_ammunition_flow_modifiers_effect`
   - `st_res_rebuild_oil_flow_modifiers_effect`
4. Each wrapper delegates to `st_res_rebuild_good_flow_modifiers_effect = { GOOD = <good> }`.

### Why this shape is the right one here

1. The shared local-variable setup stays in `st_res_rebuild_hub_flow_modifiers_effect`.
2. The single building-scope hop stays where it was.
3. The concrete good wrappers remain grep-able and make the supported goods explicit.
4. The repeated branch logic lives in one behavior-locked helper instead of three copies.

### Behavior that must stay locked

- Exact modifier names: `sr_<good>_store_flow`, `sr_<good>_withdraw_flow`, `sr_<good>_disable_input_flow`, `sr_<good>_disable_output_flow`
- Exact `if / else_if / else` ordering
- Exact thresholds and guards
- Exact single-hop country-scope to building-scope structure

## Remaining Good Candidates

The big candidates are mostly addressed (see commits leading to and including the `Phase 1..5 refactor` series finishing in `Phase 5 refactor: extract apply_banking_crash_softening_option_effect helper`, and the earlier `Phase 7 refactor: banking law-change cleanup bundles + bloc principle base`). What's left is small or deliberately deferred:

| File | Candidate | Why it fits | Risk |
|---|---|---|---|
| [common/script_values/st_res_script_values.txt](../common/script_values/st_res_script_values.txt) | Per-good weekly delta and capacity values | Grain/ammunition/oil blocks share the same skeleton | Medium: many JE/status references depend on the existing names |
| [common/scripted_buttons/st_res_buttons.txt](../common/scripted_buttons/st_res_buttons.txt) | Per-good increase/decrease rate buttons | Thin wrappers around per-good effect names | Low |
| [common/scripted_triggers/wonder_triggers.txt](../common/scripted_triggers/wonder_triggers.txt) | Repeated continent/building checks | Placeholder-friendly, but not as high leverage as SR | Medium |
| [common/scripted_effects/legacy_modifier_cleanup.txt](../common/scripted_effects/legacy_modifier_cleanup.txt) | 207 inline `if has_modifier remove_modifier` patterns | Could use `remove_modifier_if_exists_effect` | **Skip**: temporary save-migration code, slated for deletion once no pre-migration saves exist |
| [common/buildings/wonders.txt](../common/buildings/wonders.txt), synthetics plants in `extra_buildings.txt` | Repeated building boilerplate | 46 wonders + 11 synthetics share scaffolding | **Skip**: pure data, intentionally grep-friendly; would belong to a generator if scaled further |

## Refactor Guidance

- Prefer one behavior-locked slice at a time.
- Validate the narrowest affected system immediately after the first edit.
- Do not batch SR scripted-effects, SR script values, and SR buttons into one giant refactor unless there is a strong reason and a good validation path.
- When the game engine is the real validator, preserve grep-able concrete names at the wrapper layer even if the shared logic becomes parameterized.