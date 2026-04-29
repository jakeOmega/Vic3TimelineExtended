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

### Conventions that already work well here

- Use short, descriptive uppercase placeholder names.
- Document parameters and scope immediately above the shared helper.
- Pass arguments by name at each call site.
- Keep explicit wrappers or unrolled callers when the concrete types are fixed and finite.
- If a repeated block includes a scope bridge, keep the bridge in the outer orchestrator when one shared hop is enough.

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

The big candidates are mostly addressed (see commits leading to and including `Phase 7 refactor: banking law-change cleanup bundles + bloc principle base`). What's left is small or deliberately deferred:

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