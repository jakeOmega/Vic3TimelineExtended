# Scripting Best Practices & Debugging

Lessons learned from developing the Vic3TimelineExtended mod. Covers modifier validation, scope issues, debugging, and common engine quirks.

## Placeholder-Parameterized Script Helpers (`$GOOD$`, `$TYPE$`, `$RANK$`)

When several scripted effects, triggers, or script values are structurally identical and only the identifiers differ, prefer one shared helper parameterized with uppercase placeholders plus thin explicit wrappers or unrolled call sites.

### Repo examples

- `covert_op_track_targets` in `common/scripted_effects/covert_warfare_effects.txt` uses `$TYPE$`, `$ACTION$`, and `$DEFENSE_MOD$`.
- `st_res_rebuild_good_flow_modifiers_effect` in `common/scripted_effects/st_res_effects.txt` uses `$GOOD$` behind explicit grain/ammunition/oil wrapper effects while keeping the hub scope bridge in the outer orchestrator.
- `covert_ops_type_below_cap` in `common/scripted_triggers/covert_warfare_triggers.txt` uses `$TYPE$`.
- `ch_apply_primary_or_fallback_movement_pressure` in `common/scripted_effects/cultural_hegemony_effects.txt` uses `$PRIMARY$`, `$FALLBACK_1$`, `$FALLBACK_2$`, `$MODIFIER$`, and related parameters.
- `store_trade_partner_data` in `common/scripted_effects/trade_partner_effects.txt` uses `$RANK$`.
- `generic_wonder_construction_base` in `common/scripted_effects/extra_effects.txt` uses `$WONDER$` and `$MAX_LEVEL$` to drive 7 wonder construction effects with a single 19-branch level-up chain. See "Numeric placeholder substitution into trigger guards" below.

### Numeric placeholder substitution into trigger guards

`$X$` substitution is direct text replacement before tokenization, so a numeric placeholder can sit inside a trigger comparator and tokenize as a literal integer:

```
if = { limit = { b:building_$WONDER$.level = 5 b:building_$WONDER$.level < $MAX_LEVEL$ } create_building = { ... level = 6 } }
```

Calling `generic_wonder_construction_base = { WONDER = solar_collector MAX_LEVEL = 10 }` resolves the guard to `b:building_solar_collector.level < 10`, which is valid engine syntax (also used in vanilla and `extra_buildings.txt` construction-site `possible` clauses). This lets one shared chain handle wonders capped at any level — branches with `level = N` where N ≥ MAX_LEVEL silently never match.

The same trick works for `RISK = 5..10` in `sr_monthly_progress_update_effect` (`set_variable = { name = sr_base_risk value = $RISK$ }` becomes `value = 5`) and for `MAX_LEVEL` in similar bounded chains. Don't try to do arithmetic on placeholders — there's no `$N$+1`, only direct text substitution.

### Conventions

- Use short, descriptive uppercase placeholder names such as `$GOOD$`, `$TYPE$`, or `$MODIFIER$`.
- Document the scope contract and every parameter immediately above the shared helper.
- Pass arguments by name at the call site: `my_effect = { GOOD = grain }`, not by position.
- Keep thin explicit wrappers or unrolled callers when the engine does not provide a safe data-driven loop. They make the supported concrete types grep-able and easy to audit.
- If the repeated logic includes a scope bridge, do the bridge once in the outer orchestrator and call the typed wrappers after entering the target scope. Do not duplicate the same `owner = {}` or `random_scope_building = {}` hop inside every wrapper unless each wrapper genuinely needs its own scope selection.

### Practical rule

Use placeholder helpers for maintenance, not cleverness. If a refactor would hide the controlling scope hop, obscure the concrete modifier names, or make validation harder, keep the repetition.

For concrete examples and remaining candidate refactors in this repo, see `docs/audits/script_parameterization_audit.md`.

## Modifier & Cooldown Duration Units: `days` vs `months`

**CRITICAL:** The `X_modifier_time` script values (`short_modifier_time`, `normal_modifier_time`, `long_modifier_time`, `very_long_modifier_time`) are defined in **DAYS** (e.g. `normal_modifier_time = 1825` = 5 years). Always use `days = X_modifier_time` in `add_modifier` and `cooldown` blocks, **NEVER** `months = X_modifier_time`.

| Wrong (152 years!) | Correct (5 years) |
|---|---|
| `add_modifier = { name = X months = normal_modifier_time }` | `add_modifier = { name = X days = normal_modifier_time }` |
| `cooldown = { months = normal_modifier_time }` | `cooldown = { days = normal_modifier_time }` |

When a scripted effect uses `months = $PARAM$` internally (like `ch_apply_hegemon_movement_pressure`), callers must pass **literal month counts** (e.g. `MONTHS = 60` for 5 years, `MONTHS = 30` for 2.5 years), NOT script value names.

**Both `days = N` and `months = N` are valid `add_modifier` / `cooldown` syntax** when N is a literal integer (vanilla uses `months = 12`, `months = 120`, etc. — see `paris_commune_pulse_events.txt`, `alaska_events.txt`, `canal_events.txt`). The bug pattern this section warns about is *only* mixing the `*_modifier_time` script values (defined in days) with the `months =` keyword. A code review that flags every `months = N` as a bug will produce false positives — verify against vanilla precedent before "fixing".

## Modifier Design: Don't Borrow Modifiers from Other Systems

Each mod system should define its own modifiers. Do NOT reuse modifiers from another system (e.g. using `intelligence_capacity_defense` from covert warfare in a cultural hegemony event). Cross-system modifier sharing:
- Creates confusion about what system is applying effects
- Breaks modifier tooltips (wrong icon, wrong description context)
- Makes it impossible to balance systems independently

## Modifier Design: Relative vs Absolute Mechanics

Some modifiers contribute to **relative** comparisons; others to **absolute** thresholds. The cascade behavior of country-scope modifier blocks (techs, laws, PB principles, country-scope static modifiers) applies the value to *every* eligible scope (every character, every state) — which is fine for absolute mechanics but a **wash for relative ones**.

**Relative-only modifiers (don't cascade-buff via country-scope blocks):**
- `character_popularity_add` — the IG that benefits is the one whose leader is more popular than the others. Adding +5 to every character changes nothing.
- `character_prominence_add` — leader-selection picks the top-N most prominent of an eligible pool. Uniform boosts don't move the ranking.
- Similar relative effects: anything that drives "who's #1 / who's most attractive / who's selected from a pool."

For these, apply **targeted via `every_scope_character = { limit = { ... } add_modifier = { ... } }`** so only a subset (one gender, one culture, one IG, the head-of-state) gets the bonus. The asymmetry is what produces game effect. See `events/feminist_events.txt:200/100` for the pattern (female-only cascade on the success and backlash branches of the feminism JE).

**Absolute-mechanic modifiers (country-scope cascade is fine):**
- `character_loyalty_add` — loyalty thresholds are absolute (low loyalty triggers events / coup eligibility regardless of how loyal others are).
- `character_coup_strength_mult` — multiplier on a per-character coup score; absolute.
- `character_command_limit_*`, `character_advancement_speed_*`, `character_battle_condition_*_mult`, naval `character_blockade_mult` / `character_naval_mission_area_add` / `character_max_offensive_battles_add` / `character_interception_add` — all per-character absolute caps and probabilities.
- `character_health_add` — life expectancy ceiling, absolute.

When in doubt, ask: "if this modifier moved the same amount on every character in the country, would that produce a different gameplay state?" If no — it's relative; needs targeting. If yes — it's absolute; cascade is fine.

## Expense Scaling with GDP

- **Never use flat `country_expenses_add` values** (e.g., `country_expenses_add = 50000`). Flat values don't scale with country or economy size.
- **Pattern:** Set `country_expenses_add = 1` in the static modifier, then use `add_modifier = { name = X multiplier = <gdp_script_value> }` in the event.
- **GDP script values** (defined in `extra_script_values.txt`): `banking_event_expense_small` (0.5% GDP), `banking_event_expense_medium` (1% GDP), `banking_event_expense_large` (2% GDP), `banking_event_expense_huge` (3% GDP).
- **When a modifier has BOTH expenses and gameplay effects**, split into two modifiers: one for gameplay (applied without multiplier) and one `_cost` modifier with `country_expenses_add = 1` (applied with GDP multiplier).
- **Avoid negative `country_expenses_add`**. For austerity/savings, use `country_loan_interest_rate_mult`, `country_minting_add`, or `country_tax_income_add`.

## Scaling vs Non-Scaling Values

- **Values that scale with country size/time** (need scaling): `prestige`, `bureaucracy`, `country_expenses_add`, `country_tax_income_add`, flat money amounts. Never use flat amounts for these — scale via script value or use `_mult` modifiers.
- **Values that do NOT scale much** (safe as flat values): `authority`, `influence`, `cultural_acceptance`, `legitimacy`, `diplomatic_reputation`, `leverage`, `standard_of_living`, `migration_pull`, multiplier/percentage modifiers.
- `add_prestige` is not a valid static modifier field — use `country_prestige_add`.
- `add_authority` and `add_influence` are NOT valid effects — these are rate-based resources that can only be affected through modifiers (`country_authority_add`, `country_influence_add`).
- `add_infamy` is NOT a valid effect — vanilla uses `change_infamy = N`. Symmetric: `change_relations`, etc. The `add_*` shape is *most* effects but not infamy/relations/the-other-relational-resources. Verify against `vanilla_snapshot_docs/effects.log` before authoring.
- **Many `country_*` names that exist as triggers or modifiers do NOT exist as script values.** `prestige`, `gdp`, `authority` (etc.) read as bare names inside script values (`value = gdp`). Writing `value = country_gdp` produces "Badly read script value" with no name resolution. Also: `country_prestige` is a script value but `prestige` is the trigger — they aren't aliases. When in doubt, grep `common/script_values/` (vanilla) for `^X = {` to confirm the script-value name exists, or grep `<vanilla_snapshot_docs_path>/triggers.log` for trigger usage.

### Audit + library for fast-scaling event effects

`event_magnitude_audit.py` (endpoint: `GET /event-magnitude-audit`, report: `docs/engine/event_magnitude_report.md`, regenerated on every full `POST /reload`) flags hardcoded fast-scaling deltas in `events/*.txt` and recommends a scaled fix path. Resources currently audited:

| Modifier / effect | Scaled-fix path |
|---|---|
| `country_prestige_add` (in static modifiers used by `add_modifier { name = X multiplier = N }`) | Replace with `add_modifier { name = prestige_loss_<tier> }` (mult-based generic, no multiplier needed) OR `multiplier = sv_prestige_event_<tier>` if X has multiple fields that should scale together |
| `country_bureaucracy_add` | Replace with `add_modifier { name = bureaucracy_loss_<tier> }` |
| `add_treasury` (direct effect) | Replace literal value with `add_treasury = sv_treasury_event_<tier>` (% of `gold_reserves`) |
| `country_expenses_add`, `country_tax_income_add`, `country_minting_add` (weekly money flows) | Keep the static modifier as `country_<X>_add = 1`, apply via `add_modifier { multiplier = sv_money_flow_event_<tier> }` (% of GDP / week). Same pattern as the existing `banking_event_expense_<tier>` script values, kept for banking-specific events. |

Available tiers (in `common/script_values/extra_script_values.txt` and `common/static_modifiers/extra_modifiers.txt`): `tiny` (0.5%), `small` (2%), `medium` (5%), `large` (15%), `huge` (30%, prestige only). Adding a new fast-scaling resource is one line in `event_magnitude_audit.FAST_SCALING_MODIFIERS`.

The audit also catches the trickier "static modifier carries the hardcoded value itself" case: `add_modifier { name = X }` (no multiplier) where X has a hardcoded `country_prestige_add = -20` field. Fix path: either change X to use `country_prestige_mult`, or replace the reference with a mult-based generic.

**Suppressing a flag.** When a hardcoded value is intentional (tech-gated to a specific era, vanilla precedent, etc.), add an inline comment on the value line:

```
multiplier = 2000  # REVIEWED 2026-05-04: tech-gated to nuclear era; intentionally large
```

Both the date and a rationale are required (drive-by `# REVIEWED` is rejected). The audit captures both and reports them in the `## Reviewed Exemptions` section of `docs/engine/event_magnitude_report.md`. Unreviewed flags are the actionable inbox.

## One-Shot vs Duration-Multiplied Calibration

A `country_*_mult` or weekly modifier from `add_modifier { days = N ... }` compounds over `N` days (~`N/7` weeks of effect). A bare `add_treasury` is paid **once**. When an event option offers cash *instead of* a multi-year modifier, size the one-shot to be competitive with the modifier's effective lifetime value:

- **Reward — "cash now instead of a 5-year benefit"**: prefer vanilla's `money_amount_multiplier_very_large` (~0.25% GDP) **× 2–8** depending on how valuable the alternative modifier is. Bare `very_large` is filler-tier; for "you gave up a major bonus for cash," go higher (4–8×). Mod scale anchors (actual computed values, vanilla `event_values.txt` comments are stale):
  - `money_amount_multiplier_large` ≈ 0.05% GDP
  - `money_amount_multiplier_more_large` ≈ 0.1% GDP
  - `money_amount_multiplier_very_large` ≈ 0.25% GDP
- **Cost — "fund a 5-year program with a one-shot payment"**: scale the income/GDP fraction by **~5×** what a single year of the program would cost; the one-shot is buying the modifier's full duration. So a "spend 3% of yearly income for a 5-year decaying benefit modifier" is undersized — bump to ~15% to reflect 5 years of program funding.
- **Anti-pattern**: flat `add_treasury = 50000`. Late-game GDPs reach $20M+, where 50k is rounding error. Switch to GDP-scaled (`money_amount_multiplier_*` or a literal `gdp × N` multiplier).

When adding a new option that pairs `add_treasury` with `add_modifier`, sanity-check both magnitudes against the alternative option in the same event — the cash-vs-modifier tradeoff only feels like a real choice if the magnitudes are commensurate.

## Authority Cost Compensation (Inverse `country_authority_mult`)

`country_authority_add` in a static modifier is multiplied by the country's `country_authority_mult` before being applied. So if a country has a +50% authority mult, a flat `country_authority_add = -250` becomes -375 effective. For *cost* modifiers (where the player intent is "spend exactly 250 authority"), this is wrong: high-mult countries pay more for the same option.

**Compensation pattern** — apply the modifier with a script-value multiplier that inverts the country's authority mult:

```
forced_law_through_event_authority_multiplier_small = {
    value = 1
    divide = { value = 1 add = modifier:country_authority_mult min = 0.01 }
}
```

Then `add_modifier = { name = forced_law_through_event multiplier = forced_law_through_event_authority_multiplier_small }`. The two effects compose to a flat -250 regardless of mult.

Reuse via composition for tier scaling:
```
forced_law_through_event_authority_multiplier_large = {
    value = forced_law_through_event_authority_multiplier_small
    multiply = 3
}
```

The same pattern works for any flat-cost-via-`_mult`-modifier interaction. **Don't apply this pattern to gameplay-effect modifiers** — only to ones that represent a fixed "cost" of an action.

## Modifier Name Validation

**Always verify modifier names exist** before using them. The engine silently ignores invalid modifiers.

Known invalid names:
- `country_trade_route_cost_mult` — does NOT exist. Use `building_group_bg_trade_throughput_add`, `state_trade_advantage_mult`, or `state_trade_capacity_add/mult`.
- `country_trade_route_quantity_mult` — does NOT exist (removed or never existed). Use `state_trade_capacity_add`, `state_trade_quantity_mult`, or `state_trade_advantage_mult` for state-level trade bonuses.
- `state_radicals_from_sol_change_mult` — does NOT exist. Use `state_radicals_from_political_movements_mult`. An invalid modifier in a PM file causes **cascading parse failures** for the entire file.
- `country_construction_mult` — does NOT exist (despite `country_construction_add` existing). Construction *throughput* lives on the goods-output axis: use **`goods_output_construction_mult`** to scale construction proportionally. The `_add`/`_mult` asymmetry is real — country-level construction sectors can be added as a flat count, but multiplying them must go through the construction-good output. Same shape applies to other modifier families where the country-level resource is also a good (services, etc.) — check both axes when an obvious `country_<X>_mult` doesn't validate.
- `is_owned_by_company` — does NOT exist as a trigger. Use `exists = owning_company` (building scope).
- `company` — does NOT exist as a trigger to match a specific company. Use `owning_company = <company_scope>`.
- `country_war_support_mult` — does NOT exist. The country-wide war-support pool isn't a directly-modifiable axis. Use `country_war_exhaustion_casualties_mult` (vanilla, scales casualty-driven exhaustion — negative values reduce wartime drain) or `state_war_support_monthly_add` (mod-added, direct per-state gain). See `docs/vanilla/vanilla_war_reference.md` § 13 for the full war-support exhaustion table and the lobby-clout lever.
- `political_movement_support_mult` — does NOT exist. The real name is `political_movement_pop_attraction_mult`. Used to shrink/grow movement reach into pops.
- `political_movement_radicalism_mult` — does NOT exist. Activism is additive, not multiplicative; use `political_movement_radicalism_add` (negative values cool a movement's activism, positive values heat it). Vanilla precedent: ww_war_propaganda_modifier uses −0.30; civil_rights_martyrdom_modifier uses +0.25.

**Failure mode that produced these:** *extrapolating-by-analogy from a real modifier name without verifying.* Because `country_X_mult` is a recurring shape (`country_prestige_mult`, `country_authority_mult`, etc.), inventing `country_war_support_mult` feels safe — but the engine doesn't expose every concept on every axis. Default to grepping `<vanilla_snapshot_docs_path>/modifiers.log` (typically `~/src/vic3/docs/modifiers.log`) — or use `/modifier-search?q=` — before citing any modifier name in code OR in docs. The doc-citation case bites the same way as the code-citation case: future Claude instances will read the doc and trust the name.

**Use specific building modifiers** when possible: `building_railway_throughput_add` targets only railways, while `building_group_bg_public_infrastructure_throughput_add` applies to ALL public infrastructure. Be intentional about scope.

**Validation methods:**
- Use the mod state server `/modifier-search?q=<name>` endpoint.
- Search base game: `Get-ChildItem "C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game\common" -Recurse -Filter "*.txt" | Select-String "modifier_name"`.

## Modifier Value Scale: The Suffix Doesn't Tell You

A modifier's `_add` / `_mult` suffix tells you the *operation* (additive vs multiplicative), not the *unit* the engine reads. Whether a value should be a 0–1 fraction, a raw percentage point integer, or a small integer on a custom scale is set per-modifier by the engine — and it's not always intuitive.

Real bug from this codebase: `country_law_enactment_success_add = 5` was meant as "5 percentage points" but the engine reads this modifier as a 0–1 fraction, so it rendered as **+500%**. Vanilla call sites use `0.05`, `0.10`, `0.20` (i.e. 0–1 fraction). The fix was `5 → 0.05`. Same shape would bite on `country_amenability_add` (vanilla uses small integers like `3`) — there's no rule from the suffix.

**Always grep one vanilla call site before naming a value for an unfamiliar modifier:**
```
grep -rn "country_law_enactment_success_add" \
  /mnt/c/Program\ Files\ \(x86\)/Steam/steamapps/common/Victoria\ 3/game/common/ \
  | grep -v "_l_"
```
Pick a representative vanilla number, then size your value relative to it. The `display_name` from `engine-docs/modifiers?q=NAME` plus `description` (e.g. "A flat percentage point increase…") often hints at the scale, but vanilla call sites are the ground truth.

`/validate/engine-coverage` does NOT catch this — values pass validation as long as the modifier name is registered. The bug surfaces only at runtime in the player's tooltip, so it can sit undetected for a long time.

## Dynamic Modifier Type Definitions

Many modifiers follow **naming patterns** where the engine recognizes a common prefix/suffix but requires a **per-entity registration** in `common/modifier_type_definitions/` before the modifier works. Vanilla pre-registers these for base game buildings and goods; **modded buildings and goods need their own registrations.**

If you reference a dynamic modifier (e.g. `building_robotics_industry_throughput_add`) without registering it, the engine **silently ignores** it — no error in logs, just no effect. Don't assume a modifier doesn't exist because you can't find it in the base game; it may simply need to be registered.

### Pattern Families

| Pattern | Example | Scope | Use for |
|---|---|---|---|
| `building_{name}_throughput_add` | `building_tourism_industry_throughput_add` | building | Specific building throughput bonus |
| `building_group_{bg}_throughput_add` | `building_group_bg_manufacturing_throughput_add` | building group | All buildings in a group |
| `goods_output_{good}_mult` | `goods_output_tourism_mult` | goods | Production output bonus for a specific good |
| `goods_input_{good}_add` | `goods_input_electronic_components_add` | goods | Extra input consumption |
| `state_building_{name}_max_level_add` | `state_building_space_mine_max_level_add` | state | Level cap for company/gated buildings |
| `building_group_{bg}_{poptype}_mortality_mult` | `building_group_bg_agriculture_laborers_mortality_mult` | building group | Pop mortality in specific building groups |
| `ship_battle_against_ship_type_{ship}_{accuracy\|hull_damage}_{add\|mult}` | `ship_battle_against_ship_type_nuclear_submarine_accuracy_mult` | country (applied to ships) | Combat-axis bonus when attacking a specific ship type. **Partial vanilla coverage:** vanilla only registers the axis combos it uses — e.g. `submarine`/`torpedo_boat`/`destroyer` get `_accuracy_*` but NOT `_hull_damage_mult`; `dreadnought`/`super_dreadnought`/`modern_ironclad`/`pre_dreadnought` get `_hull_damage_mult` but NOT `_accuracy_mult`. Always cross-check against `/mnt/c/Program Files (x86)/Steam/.../game/common/modifier_type_definitions/00_modifier_types.txt`; register any missing combo in the mod even when targeting a vanilla ship type. |
| `country_ship_type_{ship}_construction_efficiency_add` | `country_ship_type_destroyer_construction_efficiency_add` | country (applied to ship construction) | Reduces shipyard build time for a specific ship type. **Partial vanilla coverage:** vanilla registers it only for `troop_ship`/`protected_cruiser`/`armored_cruiser`/`light_cruiser`. `destroyer` and most modern types are NOT pre-registered; mod must register them in `mod_entity_modifier_types.txt` even though they target vanilla ship types. |
| `goods_input_{good}_add` / `goods_output_{good}_add` | `goods_input_motor_ships_add` | building (in PM) | Flat input/output amount for a modded good. **Mod-defined goods need BOTH `_input_*_add` and `_output_*_add` registered explicitly** — vanilla auto-generates these only for vanilla goods. The `_mult` variants follow the same rule, and **vanilla coverage is partial even for vanilla goods**: e.g. `goods_output_aeroplanes_mult` is registered but `goods_input_aeroplanes_mult` is NOT (vanilla never consumes aeroplanes via a mult source); `grain` lacks both mult axes. Always cross-check `/mnt/c/Program Files (x86)/Steam/.../game/common/modifier_type_definitions/01_building_modifier_types.txt` before applying a mult-axis flow modifier to a vanilla good. Symptom of missing registration: `Unknown modifier type` in debug.log and the modifier silently no-ops. |

### Goods I/O modifiers: PM-applied vs runtime-applied (the `_add` trap)

`goods_input_{good}_add` / `goods_output_{good}_add` work as expected when they sit inside a PM's `building_modifiers` / `country_modifiers` block (or any modifier block on a static entity loaded at game start). They do **not** work when applied at runtime via `add_modifier = { name = X }` from a scripted effect — the engine only registers `_add` goods I/O contributions through the production-method channel, and a runtime-applied `_add` is silently dropped from the goods flow. **Use `_mult` for runtime-applied dynamic flow modifiers**, scaling against a base 1-unit input/output declared in the PM. The Strategic Reserve hub follows this pattern: the PM carries `workforce_scaled = { goods_input_<good>_add = 1 goods_output_<good>_add = 1 }` as the static base, and `st_res_<good>_store_flow` (with `goods_input_<good>_mult = 1`) is applied at runtime with `multiplier = good_mult` to scale that base. The inactive side gets disabled with the same modifier applied at `multiplier = -1` (≡ `_mult = -1` ≡ -100% on the base, zeroing it out). Symptom of trying to use `_add` runtime: the modifier appears in the building's modifier list but goods flow doesn't change — Active rate displays nonzero while the hub buys/sells nothing.

### Where New Registrations Go

`common/modifier_type_definitions/` is split by purpose:

- **`mod_entity_modifier_types.txt`** — per-entity registrations of vanilla dynamic-modifier patterns for mod-introduced goods/buildings/ships/units/institutions/laws (and a few vanilla gap-fills). Internally divided by `# === Goods ===` / `Buildings` / `State buildings` / `Combat units` / `Ships` / `Institutions` / `Law-gated` / etc. headers — keep new entries under the matching divider.
- **One file per mod-invented system** — `subjugation_`, `diplomatic_play_escalation_`, `power_bloc_extra_`, `space_race_`, `nuclear_program_`, `homelands_`, `un_membership_`, `global_warming_`, `megastructure_progress_`, `banking_cycle_`, `sol_expectations_`, `covert_warfare_`, `cultural_hegemony_`, `movement_`, `st_res_`, `tech_gate_`. Bespoke knobs for a single mechanic (escalation rates, capacity counters, capability flags, progress trackers) live in the file named after that mechanic, with a top-of-file scope comment naming the consumers (script values, on-actions, scripted effects). Tiny systems get their own files — `un_membership_modifier_types.txt` is one entry.

When in doubt: if the modifier name parameterizes over a mod entity (`<good>`, `<building>`, `<ship>`, `<institution>`) it goes in `mod_entity_modifier_types.txt`; if it's a fixed name backing one specific mod system, give it its own sibling file (or extend an existing one).

### Registration Format

```
# In common/modifier_type_definitions/mod_entity_modifier_types.txt
# (or in the matching system file if this modifier is a bespoke mechanic knob)

# Building throughput (percentage)
building_my_custom_building_throughput_add = {
    color = good
    percent = yes
    decimals = 0
}

# Goods output multiplier (percentage, with AI weight)
goods_output_my_custom_good_mult = {
    color = good
    percent = yes
    game_data = {
        ai_value = 250
    }
}

# Level cap (flat integer, not percentage)
state_building_my_building_max_level_add = {
    color = good
    percent = no
    decimals = 0
}
```

### Key Properties
- `color`: `good` (green), `bad` (red), `neutral` (yellow/grey)
- `percent`: `yes` = displayed as percentage, `no` = displayed as integer
- `decimals`: Number of decimal places (0 for integers)
- `game_data = { ai_value = N }`: Optional AI weight for PM selection
- `boolean = yes`: For yes/no flag modifiers
- `script_only = yes`: For modifiers used only by scripted effects (no PM/modifier display)

### Localization

Every registered modifier needs two loc keys:
```
modifier_name:0 "Display Name"
modifier_name_desc:0 "Tooltip description explaining what this modifier does."
```

### Checklist for New Buildings/Goods

When adding a new building or good, always check:
1. Does any PM, static modifier, or event use a `building_{name}_throughput_add` modifier? → Register it.
2. Does any PM produce or consume a new good? → Register `goods_output_{good}_mult` and/or `goods_input_{good}_add`.
3. Does the building use the `has_max_level` pattern? → Register `state_building_{name}_max_level_add`.
4. Add localization for all registered modifier names.

### Script-Only Modifiers as Cross-System Tags / Capability Bands

A `script_only = yes` modifier has no native engine effect — it's just a value the engine sums across all sources, surfaces in tooltips wherever it's contributed, and can be read in triggers as `"modifier:X" >= N`. This makes it the right tool when you want a system whose behavior depends on **a combination of laws / techs / decrees / buildings**, AND want the player to discover those dependencies from the ordinary law/tech/etc. tooltip — not from reading event source.

**The pattern:**
1. Define the modifier type: `country_X_capacity_add = { color = neutral percent = no decimals = 0 game_data = { ai_value = 50 } script_only = yes }` in the matching system file under `common/modifier_type_definitions/` (or `mod_entity_modifier_types.txt` if no system file fits yet). Localize the name + `_desc` in `localization/english/te_modifiers_l_english.yml`.
2. Add positive/negative contributions to the `modifier = { ... }` block of every law/tech/decree where it's thematically warranted, via `INJECT:` for vanilla entries.
3. Read it from triggers: `"modifier:country_X_capacity_add" >= 4`. The value is the sum of all contributions; works fine with negative values.
4. Optionally name banded thresholds with scripted triggers, e.g. `banking_points_low = { "modifier:country_banking_intervention_max_add" <= 2 }`.

**Repo examples:**
- `country_banking_intervention_max_add` (`common/modifier_type_definitions/banking_cycle_modifier_types.txt:8`) — banded by `banking_points_none / low / med / high` in `common/scripted_triggers/market_triggers.txt:29-32`. Contributions live on banking-related laws.
- `country_legislative_override_capacity_add` — gates the Forced a Law Through event (small / medium / large tiers at thresholds 0 / 2 / 4), with contributions across Distribution of Power, Bureaucracy, Free Speech, and Internal Security laws (`common/laws/legislative_override_capacity.txt`). Surplus above the highest threshold also feeds a script-value cost discount.

**When to prefer this over direct `has_law` triggers:** any time the gate is best expressed as a *combination* of multiple laws, or when you want the player to see which laws move the needle. Direct `has_law` checks are invisible to the player and require enumerating every law variant by hand.

### Boolean Modifier Types Must Be Explicitly Declared

Boolean modifiers (`name = { color = good; boolean = yes }` in `common/modifier_type_definitions/`) follow the same silent-no-op rule as dynamic-pattern modifiers, even when the name is fully spelled out — there is no auto-registration from reference sites. If the type isn't declared:

- A PM that grants `country_X_program_bool = yes` in its `country_modifiers = { unscaled = { ... } }` block applies *nothing*.
- A trigger reading `modifier:country_X_program_bool = yes` (e.g. in a JE `possible` clause) always evaluates to **false**.

Both fail without a parse error and without a debug.log warning, so the system depending on the boolean silently never activates. The country_sr_*_program_bool regression of 2026-04-29 was exactly this — six space-program booleans were deleted from `tech_gate_modifier_types.txt` on the (incorrect) theory that the engine auto-registers booleans, and the entire space race system stopped activating until restored.

**Validation now covers this.** `/validate/engine-coverage` checks both modifier-use sites and `modifier:NAME = yes` trigger references for booleans (suffix `_bool` / `_boolean`). Any boolean referenced but not declared in the engine modifiers catalog or in a `Modifier Types` entry surfaces in `unknown_modifiers`. Unit + integration tests in `test_engine_coverage_validator.py` freeze the country_sr_* case as a regression test.

**Practical rule.** Declare every mod-side boolean modifier in `common/modifier_type_definitions/` (`mod_entity_modifier_types.txt` or topical files like `tech_gate_modifier_types.txt`, `power_bloc_extra_modifier_types.txt`). When in doubt: `curl 'http://localhost:8950/raw/Modifier%20Types/<name>'` will return the definition or a `Not found` error.

### Modifier Coloring for "Good When Reduced" + Surfacing Greyed-Button Reasons

Two short tips for making restrictions and signed-effect modifiers legible to the player:

**`color = bad` for modifiers where less is better.** A modifier with `color = bad` flips with sign — positive renders red, negative renders green. So for "volatility", "crash chance", "tax burden", or any modifier where reducing the value is the desired outcome, use `color = bad` (NOT `color = neutral`). `color = neutral` renders plain text in all cases. Vanilla precedent: `country_banking_crash_chance_mult`. `country_banking_random_momentum_mult` was `neutral` for a long time and players couldn't tell at a glance whether `-60%` (Prudential) was a benefit or a cost.

**Boolean lock modifiers + `custom_tooltip` for "why is this button greyed?".** When a `scripted_button`'s `possible` block is gated by a condition the player needs to understand, prefer publishing a registered `country_X_lock_<tool>_bool` (`color = bad  boolean = yes`) and gating with:
```
custom_tooltip = {
    text = my_lock_tooltip_key
    modifier:country_X_lock_<tool>_bool = no
}
```
The lock entries appear as red "Locks: …" lines in the modifier-block tooltip of whichever entity (law, tech, decree) sets them — making the *source* of the restriction visible — and the button-side `custom_tooltip` explains the greying. Beats inline `NOT = { has_law = … }` or sprawling `OR = { has_law = X, has_law = Y, … }` lists, which silently grey buttons with no player-readable explanation. Vanilla precedent: `country_disallow_law_*_bool` in `can_enact` blocks. Mod precedent: the seven `country_banking_lock_*_bool` modifiers in `banking_cycle_modifier_types.txt` (one per cb_* intervention tool).

### Mod-Added Political Movements Need Modifier Type Registration

Vanilla auto-registers `state_pop_support_movement_<X>_(add|mult)` and `country_pop_support_movement_<X>_(add|mult)` for every vanilla movement (in `common/modifier_type_definitions/08_movement_modifier_types.txt`). **Mod-added movements** defined in `common/political_movements/` get no such treatment — their support modifiers must be registered explicitly, otherwise references in laws / techs / events produce `Unknown modifier type: state_pop_support_movement_<X>_mult` and silently no-op (per the same rule as `_bool` modifiers).

The mod hit this with `movement_civil_rights`, `movement_anti_war`, and `movement_transhumanist` — all referenced in `common/laws/movement_attraction_modifiers.txt` and `common/laws/extra_laws.txt` for several commits before validation surfaced the issue. Fix lives in `common/modifier_type_definitions/movement_modifier_types.txt`.

When introducing any new mod-side movement, also register the modifier types you intend to use (state-scope and/or country-scope, `_add` / `_mult`). Vanilla shape:

```
state_pop_support_movement_<name>_mult = {
    decimals = 0
    color = neutral
    percent = yes
    game_data = { ai_value = 0 }
}
```

## Effect/Trigger Scope Requirements

- **`any_` triggers do NOT accept `limit`.** In trigger context, conditions go directly as siblings: `any_scope_diplomatic_pact = { count >= 3 is_diplomatic_action_type = X }`. The `limit = { }` sub-block is ONLY valid in effect iterators (`every_X`, `random_X`, `ordered_X`). Using `limit` inside `any_` produces "Unknown trigger type: limit" in debug.log and silently breaks the trigger evaluation (may match ALL pacts instead of filtered ones).
- **`add_homeland = <culture>`** — called from **state_region scope** with a culture argument. NOT from culture scope.
- **`add_arable_land` is state_region-scoped, so never recalculate it by blindly iterating `every_scope_state` on a fully owned split state.** Once a country owns all pieces of a formerly split region, `every_scope_state` will still visit each owned state scope, and `state_region = { add_arable_land = ... }` will over-apply if each visit mutates the shared region. Gate the recalculation to one representative state per fully owned state region, and if you cache `arable_land_added` on state scope, sum that cache across same-owner states in the region when deriving base arable land or tooltip breakdowns.
- **`is_on_front`** — a **military_formation/character scope** trigger, NOT a state scope trigger. For state, use `devastation > 0` or `is_target_of_wargoal`.
- **`is_primary_culture_of`** — requires **culture scope**, NOT pop scope. From pop scope, wrap in `culture = { is_primary_culture_of = ROOT }`.
- **`country_type = recognized` in `create_dynamic_country`** — causes errors. Remove `country_type` and use `set_country_type = recognized` inside `on_created = { }` instead.
- **`was_formed_from` in `dynamic_country_name.trigger` requires `scope:actor ?= { ... }` wrapper.** The trigger context for COA/dynamic-name validation isn't directly the country — it's a COA scope where `scope:actor` is the candidate country. Bare `was_formed_from = TAG` at the trigger root produces `PostValidate of trigger 'was_formed_from' returned false` in debug.log and the dynamic name silently never matches. Vanilla pattern: `trigger = { scope:actor ?= { OR = { was_formed_from = X was_formed_from = Y } } }`. Mod example: `te_formable_countries.txt` UNE block.
- **`every_scope_building` + `type = bt:building_X` may error.** "Event target link 'type' returned an invalid object" floods the error log when `every_scope_building` iterates buildings and the `limit = { type = bt:X }` is evaluated. Use the trigger `is_building_type = building_X` instead — that's the building-scope trigger vanilla uses (e.g., `je_values.txt`'s `every_scope_building` over barracks). The `type = bt:X` form does work in some scope chains but is fragile; prefer the trigger.
- **Treaty article `possible` does NOT bind `scope:source_country`** even though `scope:other_country` IS bound there. Vanilla puts source-side checks (duplicate-prevention against the source country's existing treaties) in `can_ratify`, not `possible`. The error `Undefined event target 'source_country'` traces to a scope:source_country read inside a treaty article's `possible` block — move it to `can_ratify`.
- **`is_diplomatic_play_committed_participant = yes`** is the country-scope trigger for "I'm currently in a diplomatic play." There is no `involvement = involved_in_play` sub-trigger inside `any_diplomatic_play = { ... }` — that's invalid syntax that produces `Unknown trigger type: involvement`.
- **`has_diplomatic_pact = { type = alliance }` PostValidate-fails — alliances are treaty articles post-Sphere of Influence, not pacts.** Valid `has_diplomatic_pact` types are the legacy bilateral pacts: `rivalry`, `embargo`, `damage_relations`, `increase_relations`, `support_separatism`, `defensive_pact`, `puppet`, `colony`, etc. (vanilla actions in `common/diplomatic_actions/`). For alliances, use `any_scope_treaty = { binds = scope:other_country  any_scope_article = { has_type = alliance } }` from country scope. Same pattern in vanilla `00_player_objectives_great_game.txt`, `00_hispaniola_buttons.txt`. Symptom: `PostValidate of trigger 'has_diplomatic_pact' returned false` at the trigger line, with no parse error — the engine accepts the syntax and only PostValidates after parse.
- **`has_journal_entry = je_X` PostValidates that `je_X` exists in the JE database.** Referencing a nonexistent JE key (typo, mod removal, vanilla rename) yields `PostValidate of trigger 'has_journal_entry' returned false` at the trigger line. Vanilla unification JEs are `je_german_unification`, `je_risorgimento`, `je_reunify_china` — there is no `je_unite_germany` or `je_unite_italy`. Validate the key against `common/journal_entries/` before referencing.
- **Event-target / scope names need `scope:` prefix when used as a scope-switcher in war_goal/diplomatic_action contexts.** Bare `creator_country = { ... }` in a wargoal's `possible` or `on_enforced` parses as an unknown trigger/effect — comments listing the available scopes (e.g. `# scopes: root = holder, creator_country, diplomatic_play, ...`) document the *event targets* in scope, not bareword scope-switchers. Correct: `scope:creator_country = { ... }`. Vanilla wargoal files only ever reference `creator_country` in those scope comments, never as a bare block.
- **Scripted triggers that read `scope:X` internally must be called with `= yes`, not `= scope:X`.** A scripted trigger defined as `is_irredentist_candidate_for = { scope:target_country = { ... } }` already reads `scope:target_country` from the *calling* scope — calling it as `is_irredentist_candidate_for = scope:target_country` produces `Malformed token: scope:target_country` because the parser doesn't accept event-target tokens as scripted-trigger arguments. Correct: `is_irredentist_candidate_for = yes`. The vanilla AI-strategy callsite shape is the reference (`other.txt` in mod uses the right form).

## Scope Chain Issues with `add_modifier` + Script Values

- When `add_modifier = { name = X multiplier = <script_value> }` is used, the engine evaluates the script value in the calling scope chain, not just the immediate scope.
- Script values that use `state_region = s:STATE_X` will fail when called from `on_law_activated`, `on_acquired_technology`, or `on_investment_changed` hooks — even wrapped in `every_scope_state { }`.
- **Building/institution scope chains are also problematic:** `on_building_built`/`on_building_expanded` ROOT is a building object. These hooks have been removed — yearly pulse hooks are sufficient.
- **Solution:** Move state-scoped modifier updates that use complex script values to `on_yearly_pulse_state`, which guarantees a clean state scope chain. This is how `migration_crowding` and `tourism` are handled.
- **`has_variable` also fails on law and treaty scopes.** `on_law_activated` ROOT = Law, and the engine traces parent scope through the law for any nested script value's `has_variable` calls. Treaty article `on_entry_into_force` has the same issue. Remove ALL state modifier updates from law/treaty hooks — yearly pulse handles them within 1 year.
- **JE scope can't read country properties (`gdp`, `prestige`, etc.) inside `multiplier =`.** `je:my_je ?= { add_modifier = { name = X multiplier = some_script_value } }` will return `'none'` from `jomini_scriptvalue.cpp` if the script value reads a country property, because the engine re-evaluates the multiplier in JE scope each tick and JE scope only auto-resolves `var:` reads, not country properties. Country *vars* work (`var:my_var` resolves against the JE owner). **Fix:** cache the script value to a country var before scoping into the JE, and reference it as `root.var:X` in the multiplier. Refresh the cache from the JE's `on_monthly_pulse` so the value tracks. Mod example: `un_buttons.txt` for peacekeeping/development contributor cost; cache var refresh in `je_united_nations.txt` `on_monthly_pulse`.
- **Script values that read `global_var:X` need a `has_global_variable = X` gate.** A monthly on-action pulse that fires before any yearly pulse will hit `'none'` when the global cache hasn't been populated yet. Wrap the body in `if = { limit = { has_global_variable = X } ... }`. Mod example: `cultural_pull_total` and `cultural_pull_from_sol` in `cultural_hegemony_script_values.txt`.
- **Variables backing `add_modifier { multiplier = ... }` must persist beyond the call site.** The engine re-evaluates the `multiplier` expression on subsequent ticks (decay/tooltip), not just at add time. Removing the variable right after `add_modifier` makes every later evaluation read `var:X` as `'none'` and emit `Value of wrong type ... Got value of type 'none'` from `jomini_scriptvalue.cpp` per re-eval. **Fix:** never `remove_variable` a name that's referenced by a still-active modifier's multiplier — leave the variable set; it can be safely overwritten by the next `set_variable` call. Vanilla pattern: `c:FRA.var:PRC_money_transfer` in `01_paris_commune.txt` is set at JE start, used in `add_modifier { multiplier = ... }`, and never removed. Mod example: `population_transfer_effect` originally removed `pop_transfer_count` after the disruption modifier was added; reverted, and the runtime errors disappeared.
- **Inline `multiplier = { ... divide = { value = X min = Y } ... }` block-form arithmetic in `add_modifier` is fragile — prefer the flat-scalar paris-commune pattern.** Even with persistent variables, a multiplier block that nests a `divide = { value = country_trigger min = … }` (or any sub-block whose `value =` reads a country trigger like `total_population`) re-evaluates that nested block on every decay tick and intermittently returns `'none'` from `jomini_scriptvalue.cpp:1659`, even when the outer scope is valid. Reported file:line is often the start-of-effect line (e.g. a blank line just before the multiplier block) rather than the actual offending line — don't trust the line number, look at the multiplier block. **Fix:** precompute the final scalar at apply-time into a country variable using `set_variable`'s inline `value = { ... }` script-value block (where country triggers like `total_population` resolve correctly), then read it flat in the multiplier: `set_variable = { name = X value = { value = var:input  divide = { value = total_population min = 1 }  min = 0.25  max = 2 } }` → `add_modifier = { ... multiplier = scope:source_country.var:X }`. The multiplier becomes a single variable lookup with no nested script-value evaluation per tick. **Do NOT** factor the divide out as `change_variable = { divide = total_population }` (or `divide = my_script_value`): empirically the `divide=` operand of `change_variable` only resolves numeric literals and `var:Y` references, not bare country triggers or script-value names — both silently return `'none'` despite the engine docs claiming script values are accepted, and the failure corrupts the variable so the later multiplier read also returns `'none'`. Mod example: `population_transfer_effect` in `extra_effects.txt`.

## Modifier Values Are NOT Recalculated Within a Single Effect Block

`remove_modifier` and `add_modifier` changes only take effect **after the entire effect block completes**. Reading `modifier:X` within the same effect still sees the pre-removal/pre-addition values. This is critical when an effect needs to read a country's "base" modifier values (without its own contribution) before computing a new value.

**Broken pattern:**
```
remove_modifier = my_shield                          # queued, not applied yet
set_variable = { name = x value = modifier:my_stat } # still includes my_shield!
add_modifier = { name = my_shield multiplier = ... } # based on wrong x
```

**Correct pattern:** Store the prior multiplier as a persistent variable and subtract it from the `modifier:` read:
```
# In the effect:
set_variable = { name = x value = modifier:my_stat }
if = {
    limit = { has_variable = prior_shield }
    change_variable = { name = x subtract = var:prior_shield }  # back out our contribution
}
# ... compute new_multiplier ...
remove_modifier = my_shield
add_modifier = { name = my_shield multiplier = var:new_multiplier }
set_variable = { name = prior_shield value = var:new_multiplier }  # remember for next tick
```

**Mod examples:** `prior_pollution_reduction` (pollution generation), `prior_free_port_import_cap` / `prior_free_port_export_cap` (free port tariffs), `intel_shield_mult` (intelligence sharing defense shield). The script values for pollution and free port tariffs also subtract the prior value so they compute clean base values.

**Corollary for cross-country reads:** When reading a partner country's `modifier:X` via scope chains (e.g., `PREV.modifier:country_covert_defense_economic_add`), the partner's own shield/contribution is also baked in. You must subtract the partner's stored prior value (`PREV.var:prior_shield`) to get their base value too.

## `ig:` Accessor Requires Country Scope

- `ig:<ig_id>` (e.g., `ig:ig_devout`) only works from **country scope**. Using it from state scope returns 'none' silently.
- **Fix:** Use `ROOT.owner.ig:ig_devout` from state scope.
- **General rule:** Verify ROOT scope type: `on_monthly_pulse_state` → ROOT=state, `on_yearly_pulse_country` → ROOT=country, `on_building_built` → ROOT=building.
- **Equivalent in country scope:** `every_interest_group = { limit = { is_interest_group_type = $IG$ } ... }` reaches the same single IG and is what `ig_approval_effect` (in `common/scripted_effects/ig_approval_effects.txt`) uses behind a `$IG$ $MODIFIER$ $DAYS$` placeholder. Prefer this helper for IG-approval modifiers — it's reusable across systems and handles the iterator/limit boilerplate once.

## Industry-Ban Triggers for New Buildings

Modded industrial / extraction buildings should declare their `possible` clause through one of two scripted_triggers in `common/scripted_triggers/misc_triggers.txt`, not by inlining the `has_law_or_variant` check:

- `is_industrial_production_allowed` — country is NOT under `law_industry_banned` or `law_extraction_economy`. Use for synthetics, chemicals, factories, and similar industrial-track buildings (extraction-only economies block construction).
- `is_extraction_industry_allowed` — country is NOT under `law_industry_banned`. Use for mines and other discoverable extractors that are still allowed under extraction-economy laws.

Inlining the check is silently buggy in two directions: it's easy to forget `law_extraction_economy` (over-permissive) and easy to typo a law id (under-permissive — engine ignores unknown law names in `has_law_or_variant`).

## Diplomatic Pact Iterators: `first_country` / `second_country` Filtering

**CRITICAL:** `any_scope_diplomatic_pact`, `every_scope_diplomatic_pact`, and `random_scope_diplomatic_pact` iterate ALL pacts a country participates in — both as **initiator** (`first_country`) and as **target** (`second_country`). For one-way pacts (like covert operations), you MUST filter by direction.

- **To find pacts you initiated:** Use `first_country = prev` (non-block form) at the pact scope level. In effects where ROOT = the country, `first_country = ROOT` also works.
- **To find pacts targeting you:** Use `second_country = prev` (non-block form) at the pact scope level.
- **NEVER use `first_country = { this = PREV }`** — entering the `first_country = { }` subscope shifts PREV to the diplomatic_pact (the enclosing scope), NOT the calling country. This causes a type mismatch error ("left was 'country', right was 'diplomatic_pact'") and **silent failure** (comparison always false). The non-block `first_country = prev` compares at the pact scope where PREV still references the calling country.
- **Why `first_country = { this = ROOT }` works in effects:** ROOT is stable across all scope levels (it never shifts). But this approach is fragile if ROOT changes context (e.g., JE scope). Prefer `first_country = prev` for triggers/SVs, and `first_country = ROOT` for effects only if ROOT is guaranteed to be the country.
- `first_country` / `second_country` are scope accessors on `diplomatic_pact` scope (confirmed in `event_targets.log`).
- **Vanilla pattern:** `any_scope_diplomatic_pact = { is_diplomatic_action_type = support_separatism second_country = prev }` (from `02_cultural_movement.txt`).

**Symptoms of missing filter:**
- Detection events fire on the wrong country (target gets "Operation Compromised" instead of attacker)
- Slot counts inflated by enemy operations targeting you
- Per-type caps blocked by enemy operations
- Effects misdirected (debuffs on attackers, self-buffs on victims)
- Cost scaling includes ops you didn't launch

## Diplomatic Play Scope: Sparse Engine Surface, Asymmetric Hops

The `diplomatic_play` scope has a **much smaller surface than `war` or `diplomatic_pact`**. Things to know before designing systems against it:

- **Only one hop on the play scope: `initiator` → country.** There is no `target` event-target. To reach the defender from a play, iterate `every_scope_play_involved` and filter with `target_is = scope:save`. Don't assume symmetric hops by analogy with `war` / `battle` scopes.
- **Iterators on the play scope:** `every_scope_play_involved` (all committed countries on either side), `every_scope_initiator_ally`, `every_scope_target_ally`. The latter two **exclude the lead country** — use `every_scope_play_involved` if you need everyone.
- **Escalation has only two scriptable hooks:** trigger `escalation` (comparator on play scope) and effect `add_escalation = <int>` (play scope). **No vanilla modifier exists for escalation rate or decay** — daily escalation is hard-coded in defines (`DIPLOMATIC_PLAY_ESCALATION_DAILY = 1`, war at 100, action pause 5d up to 20d max). To make plays heat or cool faster, you have to drive `add_escalation` from script (e.g. weekly pulse + `every_diplomatic_play`). See `common/scripted_effects/dp_escalation_effects.txt` for the country-driven dispatch pattern.
- **`add_escalation` does not reliably accept script-value arguments** — engine doc lists the signature as `add_escalation = integer` and the only vanilla usage (`italian_unification.txt:613`) is a literal integer. `add_escalation = scope:X.<script_value>` empirically silently no-ops in this mod even when the script value evaluates to a positive integer. The robust pattern is a `while` loop calling literal `add_escalation = 1`: pre-floor the script value (`floor = yes` on the script value itself) so it's a clean integer, then `while = { count = scope:mover.<script_value>  add_escalation = 1 }`. `count =` accepts script-value references (cf. `extra_effects.txt`'s `count = needed_private_levels`), so the script-value evaluation runs there instead. Engine cap is 1000 iterations — more than enough for any realistic per-week magnitude.
- **Country-driven dispatch beats play-driven** for cross-country modifier reads: each country runs an apply effect that iterates `every_diplomatic_play` filtered by their own role (`initiator_is = scope:mover`, `target_is = scope:mover`, or `any_scope_play_involved = { this = scope:mover }`). This sidesteps the missing `target` hop entirely.

### Modifier Stacking Gotcha #2 — Per-Participant Reads on Shared Resources

The same family as the per-building `_mult` pitfall, but along a different axis: **when a script-driven effect iterates participants and reads each participant's modifier value into a SHARED resource (single play, single battle, single deal), per-country contributions stack additively.** Big plays with many backers (Britain + 30 Indian princely states, large WW coalitions) explode.

**Concrete case from this mod:** the original design had a `country_participant_diplomatic_play_escalation_weekly_add` modifier read once per committed country and added to the same play's escalation. With a 30-country play and `+0.5` per country, that's `+15/week` — far past intended tuning.

**Rule:** Reserve "participant"-flavored modifier types for narrow, single-country uses (one-off event modifiers, unique character traits, head-of-state quirks). Never attach them to laws, techs, principles, or anything many countries can hold simultaneously. For broadly-attached "this country pushes plays harder" modifiers, use role-pinned variants (`aggressor_*`, `defender_*`) — at most one country fills each role per play, so additive stacking is bounded.

**See also** the script-only modifier-type comment in `common/modifier_type_definitions/diplomatic_play_escalation_modifier_types.txt` near the `country_aggressor_diplomatic_play_escalation_weekly_*` block.

## `interest_group =` Parameter in Effects Requires `ig:` Prefix

- In `add_radicals`, `add_loyalists`, and similar effects, the `interest_group` parameter requires the `ig:` prefix: `interest_group = ig:ig_devout`.
- **Using bare `interest_group = ig_devout`** causes `Failed to find a valid event target link 'ig_devout'` — the engine tries to resolve it as a saved scope, not a database key.
- This is different from `is_interest_group_type = ig_devout` (a trigger that accepts bare keys) and `ig_approval_effect = { IG = ig_devout }` (a scripted effect parameter).

## Loyalist/Radical Spectrum Mechanics

- Pops exist on a spectrum: **radical ↔ neutral ↔ loyalist**.
- `add_loyalists` moves targeted pops one step toward loyal: **radical → neutral**, or **neutral → loyalist**. It does NOT directly create loyalists from radicals.
- `add_radicals` moves targeted pops one step toward radical: **loyalist → neutral**, or **neutral → radical**. It does NOT directly create radicals from loyalists.
- **Overlapping effects cancel out.** If the same pop receives both `add_loyalists` and `add_radicals` (e.g., via overlapping strata/pop_type/IG filters), the effects partially or fully neutralize each other instead of creating a mixed result.
- **Common trap:** `add_loyalists = { value = medium_radicals }` (all pops) + `add_radicals = { value = medium_radicals pop_type = soldiers }` — soldiers receive both and end up roughly unchanged, not "loyal soldiers who are also a bit radical."
- **Strata overlap:** When using `strata = lower` for radicals alongside `pop_type = soldiers` for loyalists, remember soldiers ARE lower strata — the effects cancel on them. Use `pop_type` filters on both, or separate the strata targets to avoid overlap.

## JE Localization Scope: ROOT = JournalEntry, NOT Country

- In journal entry `status_desc`, `reason`, and custom tooltip loc strings, `ROOT` is the **JournalEntry scope**, not the country.
- **This also applies to events fired from a JE-scoped scripted effect** (e.g. via `trigger_event = { id = X }` inside a JE monthly/yearly pulse). The triggered event inherits the caller's ROOT — the JE — not the country, even when the event is `type = country_event`.
- **Invalid:** `[ROOT.GetName]` — engine logs `Could not find data system function 'GetName' in 'ROOT.GetName'` and the loc string fails to render (everything up to the broken token disappears).
- **Valid:** `[ROOT.GetCountry.GetName]`, `[ROOT.GetCountry.GetAdjective]`.
- For script values: vanilla uses `[GetPlayer.MakeScope.ScriptValue('...')]`, though `[ROOT.ScriptValue('...')]` appears to work in some contexts.

## `market_goods_pricier` Is a Delta, Not a Multiplier

The accessor for a good's runtime price on a country's home market is `<scope>.market.mg:<good>.market_goods_pricier`, which returns `(current_price / base_price) - 1` — i.e. **the fractional delta from base**, not the absolute or relative price. There is no `market_goods_price` accessor.

To display a current-price value in a tooltip, write a script value of shape `(1 + market_goods_pricier) × <base_contribution>` and reference it via `[GetPlayer.MakeScope.ScriptValue('value_X')|0]`. Examples in the mod: `te_construction_market_price` (`common/script_values/te_construction_market_current_values.txt`), `st_res_grain_sale_profit` (`common/script_values/st_res_script_values.txt`), and the `value_combat_unit_market_cost_*` family auto-generated by `pm_costs.py`.

Script values are not parameterizable, so generators that need one SV per (entity, good-mix) tuple should pre-multiply `base_price × quantity` in Python and emit the result as a literal `multiply = N` constant rather than chaining `g:<good> = { multiply = base_price }` + a separate quantity multiply at runtime — keeps the generated file readable and skips a redundant scope hop.

## `GetName` / `GetAdjective` Require `.GetCountry` Accessor

`GetName`, `GetAdjective`, `GetAdjectiveNoFormatting`, etc. are methods on the **Country data type**, NOT on ROOT directly. Even in country_events where you might expect ROOT = country, you must use `.GetCountry` to access country-type methods. Vanilla uses `[ROOT.GetCountry.GetName]` (80+ event uses) and never `[ROOT.GetName]` (0 event uses) — treat the `.GetCountry` hop as mandatory.

- **Invalid (0 vanilla uses):** `[ROOT.GetName]`, `[ROOT.GetAdjective]`, `[ROOT.GetAdjectiveNoFormatting]`
- **Valid (80+/267/216 vanilla uses):** `[ROOT.GetCountry.GetName]`, `[ROOT.GetCountry.GetAdjective]`, `[ROOT.GetCountry.GetAdjectiveNoFormatting]`
- **Also valid with scoped countries:** `[SCOPE.sCountry('my_scope').GetName]`, `[scope:cultural_hegemon.GetAdjective]`
- **Symptom of getting it wrong:** description renders only the substring AFTER the failed token. (E.g. `"The rest of [ROOT.GetName]'s market is bleeding."` showed up in-game as `"'s market is bleeding."` — debug.log captured the broken-token error in `pdx_data_factory.cpp` and `pdx_data_localize.cpp`.)

## Saved Scopes vs Variables in Localization

### Variables CAN Store Scope References
- **`set_variable = { name = X value = PREV }`** stores a **scope reference** when the value is a scope (country, state, character, etc.).
- **`Var('X')` can chain type-specific accessors** to navigate to the stored scope:
  - `.GetState.GetStateRegion.GetName` — state stored in variable (PROVEN in vanilla)
  - `.GetState.GetCountry.GetName` — state stored in variable → owner country name (PROVEN chain)
  - `.GetCharacter.GetFullName` — character stored in variable (PROVEN in vanilla)
  - `.GetInterestGroup.GetName` — IG stored in variable (PROVEN in vanilla)
  - `.GetLaw.GetName` — law stored in variable (PROVEN in vanilla)
  - `.GetBuildingType.GetName` — building type in variable (PROVEN in vanilla)
  - `.GetValue|0` — numeric value (PROVEN in vanilla)
  - `.GetCountry.GetName` — **UNVERIFIED; did not work in testing.** Use the capital workaround below.
- **`.GetName` directly on `Var()` does NOT work** — you must chain the type accessor first (e.g., `.GetState.GetName`, not just `.GetName`).
- **Error symptom:** `Could not find data system function 'GetName' in '....MakeScope.Var('my_var').GetName'` — means you forgot the type accessor (`.GetCountry`, `.GetState`, etc.).

### Workaround: Displaying a Country Name from a Variable
`Var('X').GetCountry.GetName` does not work in practice (produces blank output). **Workaround:** store the target country's `capital` (a state) in the variable, then chain `.GetState.GetCountry.GetName`:
```
# Script: scope into target country's capital before storing
every_participant = {
    limit = { NOT = { this = ROOT } }
    capital = {
        ROOT = { set_variable = { name = my_target value = PREV } }  # PREV = capital state
    }
}

# Loc: chain state → country
[ROOT.GetCountry.MakeScope.Var('my_target').GetState.GetCountry.GetName]
# Or show capital name ("our spies in Moscow"):
[ROOT.GetCountry.MakeScope.Var('my_target').GetState.GetStateRegion.GetName]
```

### `save_scope_as` vs `set_variable` for Scope References
Both can store scope references, but they differ in persistence and loc access:

| Method | Persistence | Loc access pattern |
|---|---|---|
| `save_scope_as = X` in JE `immediate` | Persists on JE instance | `[SCOPE.sCountry('X').GetName]` |
| `save_scope_as = X` in `on_monthly_pulse` | **Transient** — dies with effect chain | Only usable in `custom_tooltip`/`post_notification` within same effect chain |
| `set_variable = { name = X value = PREV }` (state) | Persists on country | `[ROOT.GetCountry.MakeScope.Var('X').GetState.GetCountry.GetName]` |

### Correct Patterns
| Purpose | Script | Loc |
|---|---|---|
| Display country via capital | Store `capital` state: `capital = { ROOT = { set_variable = { name = X value = PREV } } }` | `[ROOT.GetCountry.MakeScope.Var('X').GetState.GetCountry.GetName]` |
| Display state from variable | `set_variable = { name = X value = PREV }` | `[ROOT.Var('X').GetState.GetStateRegion.GetName]` |
| Display character from variable | `set_variable = { name = X value = PREV }` | `[ROOT.Var('X').GetCharacter.GetFullName]` |
| Display country from immediate scope | `save_scope_as = X` | `[SCOPE.sCountry('X').GetName]` |
| Display numeric variable | `set_variable = { name = X value = 5 }` | `[ROOT.GetCountry.MakeScope.Var('X').GetValue\|0]` |

### Vanilla Examples
- **Country in `immediate` scope:** `c:PRG ?= { save_scope_as = paraguay_scope }` → `[SCOPE.sCountry('paraguay_scope').GetName]` (brazil_2_l_english.yml).
- **State in variable:** `set_variable = { name = current_expedition_location_var value = prev }` → `[ROOT.Var('current_expedition_location_var').GetState.GetStateRegion.GetName]` (expeditions).
- **Character in variable:** `set_variable = { name = expedition_leader_storage_var value = ... }` → `[ROOT.Var('expedition_leader_storage_var').GetCharacter.GetFullName]` (expeditions).
- **Numeric display:** `[Country.MakeScope.Var('bonapartist_progress_from_characters').GetValue\|+=]` (agitators_1_l_english.yml).
- **Scope in pulse for tooltip:** `save_scope_as = expulsion_destination_state` in `on_monthly_pulse` → `[SCOPE.sState('expulsion_destination_state').GetName]` in `custom_tooltip` within the same effect (03_russia.txt circassian expulsion).

## Localization Accessor Chains: Magic Scopes Are Per-Rendering-Context

`[X.Y.Z]` accessor chains in `localization/english/*.yml` are validated against the *rendering context* of the loc key. The first step (the magic scope) is context-specific; using the wrong one renders an empty string and the engine emits **no debug.log entry** — the bug is only visible by hovering the in-game UI. Vanilla magic scopes per context (verified against vanilla loc samples; see `localization_accessor_audit.py:_MAGIC_SCOPES_BY_CONTEXT`):

- **Events** (`<namespace>.<n>.<suffix>` keys): `[ROOT.…]`, `[SCOPE.sCountry('name').…]`, `[SCOPE.sState('name').…]`, `[SCOPE.sCharacter('name').…]`, `[SCOPE.gsInterestGroup('name').…]`, plus uppercase magic scopes like `[STATE.…]`, `[CHARACTER.…]`, `[CULTURE.…]`, `[POP.…]`, `[BUILDING.…]`, `[MARKET.…]`, `[GOODS.…]`, `[POWER_BLOC.…]`, etc.
- **Diplomatic actions** (action name and proposal/notification descs): `[COUNTRY.GetName]` (the actor) and `[TARGET_COUNTRY.GetName]` (the recipient). NOT `[SCOPE.GetTargetCountry.GetName]` — that's a draft error that silently drops.
- **War goals** (`war_goal_<x>(_desc|_sway_desc)?`): `[WAR_GOAL_DRAFT.GetTarget.GetName]`, `[WAR_GOAL_DRAFT.GetHolder.GetName]`, `[WAR_GOAL_DRAFT.GetTargetState.GetName]`.
- **Treaty articles**: `[FIRST_COUNTRY.…]`, `[SECOND_COUNTRY.…]`.
- **Journal entries** (`je_<x>*`): `[JournalEntry.GetGoalProgressValue|D]`, etc.
- **Always valid**: `[GetPlayer.GetName]`, `[Concept('concept_x', '$fallback$')]`, `[GetDefine('NSomething', 'KEY')]`, `[GetCulture('foo')]`, plus `[concept_X]` direct references and `$X$` substitutions (passed at render time).

**Silent-drop symptom**: a tooltip with missing chunks ("Norway will annex without war.") usually means a chain failed and the renderer chopped at the failure point, eating intermediate text. The engine doesn't log it, so static analysis is the only signal.

**Audit**: `localization_accessor_audit.py` (registered in `mod_state_server.py:POST_LOAD_GENERATORS`) catches this class statically. Catalog seeded from vanilla loc; report at `docs/engine/localization_accessor_report.md`. When extending the catalog (e.g. after a vanilla bump introduces new accessors), regenerate `localization_accessor_vanilla_extras.py` from a fresh vanilla pass — vanilla loc is the authoritative source for what the engine accepts.

## `relations:` Syntax: `scope:X.relations:root`, Not `relations:scope:X`

The bare-prefix form `relations:scope:target_country >= relations_threshold:amicable` does NOT resolve the saved-scope reference inside a colon-chain — the engine returns a default that silently passes high-threshold checks. The correct vanilla form is to put the country scope on the *left* and use a literal scope reference (`root` / `prev` / etc.) on the right of `relations:`:

- **Wrong (silently misfires):** `relations:scope:target_country >= relations_threshold:amicable`
- **Right:** `scope:target_country.relations:root >= relations_threshold:amicable`
- **Also right:** `scope:target_country.relations:prev >= relations_threshold:cordial` (when previous scope is the comparison side)

Vanilla source-of-truth: `common/diplomatic_actions/12_rivalry.txt`, `01_expel_diplomats.txt`, `04_trade_states.txt`, `13_embargo.txt`, `03_violate_sovereignty.txt` — all use `scope:target_country.relations:root` form.

**Symptom**: a relations-band check that always passes regardless of actual relations (action selectable at Poor relations even though the trigger says `>= amicable`); a tooltip asserting "relations are friendly" when they're not. Recent example: voluntary_union proposable against rivals with Poor relations because every `relations:scope:X` line read as "high enough."

## Diplomatic Action `accept_score`: ROOT = Decider, `scope:actor` = Proposer

Inside a diplomatic action's `ai = { accept_score = { … } }`, the scope conventions differ from the action's `possible` / `selectable` / `accept_effect`:

- **`possible`, `selectable`, `accept_effect`, `propose_score`, `will_propose`**: ROOT = actor (proposer); `scope:target_country` = recipient.
- **`accept_score`**: ROOT = recipient (the country deciding whether to accept); `scope:actor` = proposer; `scope:target_country` is bound to the recipient (i.e., same as ROOT — self-reference, NOT the proposer).

So in `accept_score`, querying relations / attitude / rivalry of the *proposer* requires `scope:actor`, not `scope:target_country`. Vanilla source-of-truth: `04_trade_states.txt` (uses `scope:actor.…` accessors throughout its accept_score). Mistakenly using `scope:target_country` in `accept_score` queries the recipient about itself — relations checks become "recipient's relations with self" which return a default that always passes high-threshold tests.

**Every `add` block in AI scoring (`accept_score` / `propose_score` / `aggression`) must carry a `desc =` tag** so the in-game tooltip shows the breakdown. Without `desc`, the term is invisible and the player sees only the final score (e.g., "+40 acceptance" with no explanation). Vanilla example shape (from `04_trade_states.txt`):

```
add = {
    desc = "DIPLOMATIC_ACCEPTANCE_GIVING_AWAY_LAND"
    value = 100
}
```

The `desc` value is a loc key whose string explains what this term contributes. Mod content that omits `desc` produces a hidden term — bare numbers with no breakdown is the worst possible UX for diplomatic acceptance.

## `random_list` Requires Literal Integer Weights

- `random_list` weight keys must be **literal integers**: `10 = { ... }`, `90 = { ... }`.
- **Script value names as weight keys are INVALID**: `random_list = { my_weight_sv = { ... } }` silently breaks — the branch never fires.
- All vanilla `random_list` usage confirms literal integers only. Use `modifier = { if = { limit = { ... } add = N } }` inside each branch for conditional weight adjustment.
- **Alternative for dynamic chance:** Use `random = { chance = <script_value> ... }` instead. The `chance` parameter (0-100 percent) explicitly supports script values and complex math. This is cleaner when you only need a pass/fail roll (no multi-branch weighting).

## `random` Effect Modifier Blocks Require `trigger`

- In `random = { chance = X modifier = { ... } }` blocks (effects, not MTTH), every `modifier` block must contain a `trigger` sub-block.
- **Invalid:** `modifier = { add = my_script_value }` → "Malformed token" error.
- **Valid:** `modifier = { trigger = { always = yes } add = my_script_value }`.

## Reading a Script Value as a Trigger: Bare Name, Not `value:NAME`

Inside a trigger block (`possible`, `trigger`, `if/limit`, `custom_tooltip`), reference a script value **by its bare name**:

```
possible = {
    te_subjugation_strength >= 1.0   # ✓ correct
}
```

`value:te_subjugation_strength >= 1.0` produces `Unknown trigger type: value:te_subjugation_strength` and silently disables the trigger (the action still appears but the gate is dead).

The `value:NAME` prefix is for `add` / `multiply` / `divide` lines **inside another script value**, where the engine needs to disambiguate between named SVs and other tokens. In trigger context, the parser already expects a comparison and resolves the bare name correctly — the prefix is a mistake there. Mod precedent: `peaceful_annex_gdp_requirement` (in `extra_script_values.txt`) is read as `gdp < peaceful_annex_gdp_requirement` from a JE `possible` clause.

## Silent-Zero Footgun: `_add × (1 + _mult)` Without an `_add` Source

When designing a paired `_add` / `_mult` modifier family meant to combine into a single per-tick contribution, the obvious script-value formula is:

```
value = 0
add = modifier:..._add
multiply = { value = 1  add = modifier:..._mult }
min = 0
```

This evaluates to `_add × (1 + _mult)` — and **silently produces 0 if `_add = 0`, regardless of `_mult`**. Pre-tech countries with only law/principle `_mult` modifiers see the modifier in their tooltip and get nothing. The original `dp_escalation_script_values.txt` (commit `e5ba7a2`) shipped this bug; the fix expressed `_mult` as scaling **a vanilla baseline**, then subtracting the baseline back out so only the EXTRA contribution flows into the system:

```
value = define:NDiplomacy|DIPLOMATIC_PLAY_ESCALATION_DAILY   # vanilla baseline (per-day)
multiply = 7                                                  # per-week
add = modifier:..._add
multiply = { value = 1  add = modifier:..._mult }             # mult scales baseline + add
subtract = { value = define:NDiplomacy|DIPLOMATIC_PLAY_ESCALATION_DAILY  multiply = 7 }
min = 0
max = 10
floor = yes
```

**Rule of thumb:** if you write `_add × (1 + _mult)`, ask whether `_add` can plausibly be 0 in real play. If yes, anchor the multiplication to a non-zero baseline (vanilla rate, fixed constant) and subtract it out at the end. **Reading `define:NNamespace|DEFINE_NAME`** is the canonical way to pull vanilla rates into a script value (cf. vanilla `company_values.txt`'s `value = define:NEconomy|COMPANY_PROSPERITY_WEEKLY_INCREASE_BASE`).

**Cap the result.** Add `max = N` (and `floor = yes` if feeding into an `<int>`-typed effect) so a runaway modifier stack can't apply hundreds per tick.

## Named Script Values in Weight/Random Modifier `add =`

- In `random_country`/`random_X` weight modifier blocks AND `random` effect modifier blocks, `add = named_script_value` causes **"Malformed token"** errors.
- **Invalid:** `modifier = { trigger = { always = yes } add = my_script_value }` (named SV reference)
- **Valid (inline):** `modifier = { trigger = { always = yes } add = { value = X divide = Y } }` (inline SV)
- **Valid (variable):** `modifier = { trigger = { always = yes } add = var:my_var }` (direct variable ref)
- If the limit block already guarantees a variable exists, use `add = var:X` directly instead of referencing a named SV that wraps `var:X`.

## `owner = {}` Pattern for JE-Scope Script Values

Script values using `multiplier =` in `add_modifier` applied to a JE are known to evaluate to 0. However, **`modifier:country_X` and `var:X` reads work correctly from JE `on_monthly_pulse` scope** — the JE correctly resolves country-prefixed modifiers and variables set on itself.

The `owner = { }` wrapper is **only needed** for cases where reads genuinely fail (e.g., `multiplier =` in `add_modifier`). Don't apply it preemptively.

**When you DO need it** (e.g., `add_modifier` multiplier):
```
my_script_value = {
    value = 0
    owner = {
        add = covert_operations_active
        multiply = banking_event_expense_small
    }
    min = 0
}
```

**Why it works:** The `owner` accessor outputs `country` from both:
- JE scope: `journal_entry → country` (extracts the JE's owning country)
- Country scope: `country → country` (no-op, returns self)

**Failed alternatives (do NOT use):**
1. `set_variable` in `on_monthly_pulse` + `ROOT.var:X` in `multiplier =` → `multiplier` doesn't accept scope chain variable references
2. Separate `_je` wrapper SVs like `my_sv_je = { value = 0; owner = { add = my_sv } }` → still evaluates to 0 (unknown reason, possibly double scope indirection)

## `requirement_to_maintain` in Diplomatic Actions

- `possible` blocks gate **initial creation** of a diplomatic pact
- `requirement_to_maintain` blocks control **auto-cancellation** (checked every tick)
- If `possible` has a condition (e.g., `NOT = { has_war_with = scope:target_country }`), add a matching `requirement_to_maintain` or the pact won't auto-cancel when conditions change
- **War and truce checks:** Peacetime diplomatic actions need both war AND truce checks in `requirement_to_maintain`, not just in `possible`
- Format: `requirement_to_maintain = { trigger = { custom_tooltip = { text = tooltip_key NOT = { condition } } } }`

## Building Group Trigger Name

- The trigger to check a building's group is `is_building_group = bg_X`, NOT `building_group = bg_X`.

## History File Country References

- Use `c:TAG ?= { }` (null-safe) instead of `c:TAG = { }` for countries that may not exist at game start or in save games. Especially important for countries that can be annexed (like Peru).

## Starting Laws: `activate_law` at History Time Bypasses Tech Gates

`activate_law` in `common/history/extra_history.txt` (or any country history file) ignores the law's `unlocking_technologies` requirement. So you can give 1836 GBR `law_national_bank` even though the law gates on `central_banking` and even though that tech wouldn't normally be researchable until era 2.

Note: `effect_starting_technology_tier_1_tech` (vanilla, applied to recognized GP/major-power countries via their vanilla history files) already auto-researches `central_banking` as part of its era_1 starting bundle, alongside `dialectics`, `central_archives`, `egalitarianism`, `corporate_charters`. So for tier_1-bundle countries, the tech is satisfied legitimately and you don't need to re-add it.

## Mod-Only Ministry Laws: Calibrate to Bureaucratic Apparatus, Not Office-Holder Existence

The mod's `law_ministry_of_*` laws (foreign_affairs, war, commerce, religion, etc.) spawn institutions whose investment levels grant meaningful country-wide bonuses. When deciding starting assignments, the test is **"did this state run a substantial Western-style ministerial bureaucracy?"** — not "did someone hold that portfolio?".

By 1836:
- **Yes** for the 5 Great Powers (GBR, FRA, RUS, AUS, PRU) — clear ministerial apparatuses (Foreign Office, Quai d'Orsay, Russian MFA, Staatskanzlei, Prussian post-Scharnhorst Kriegsministerium).
- **No** for most other recognized states: Greece (1832), Belgium (1830), Sardinia, Two Sicilies, small German states, Netherlands, Portugal — most had a single foreign minister with a handful of clerks, which doesn't match the gameplay meaning of "Ministry."
- **No** for USA at 1836 game start despite its constitutionally formal Cabinet — State Dept had ~30 staff globally, War Dept was tiny. Player can enact as the country grows.

Don't apply ministry laws via broad filters like `is_country_type = recognized` — the result is over-inclusive and breaks the "you've built a real bureaucracy" gameplay signal. Hand-curate the list.

`is_country_type = recognized` filter does, however, cleanly exclude Japan/Qing China at 1836 (both `unrecognized` in vanilla) — useful when targeting "Western Concert + outliers" institutional baselines that are actually broad enough to apply en masse.

## Guard Scope References in Triggers

- **Always guard `has_attitude`** with `exists = scope:X` when the scope might not be set.
- **Treaty article `visible` blocks** are evaluated when `scope:source_country`/`scope:target_country` may not be set — always wrap with `trigger_if = { limit = { exists = scope:source_country } ... }`.
- **On_action scopes like `on_revolution_start`** may not always set `scope:target` — guard with `if = { limit = { exists = scope:target } }`.
- **`any_scope_state` in harvest conditions** — inner blocks can match DIFFERENT states than outer guards. Add `has_variable = X` to EACH inner block.
- **Always guard `var:X` with `has_variable = X`** when the variable may not be set on all entities in scope. This is especially critical in `any_country` iterators where a variable is set only on one country (e.g., JE owner). Without the guard, every non-matching country generates "Failed to fetch variable" + "Invalid left side during comparison 'var'" errors that spam every tick.
- **For `var:X` holding an object reference (country, character, state), `has_variable` is NOT sufficient — also add `exists = var:X`.** `has_variable` only confirms the variable was set; the referenced object can be destroyed (country annexed, character died) while the variable still points at the now-invalid index. The engine logs `Event target link 'var' returned an invalid object` + `save_scope_as effect [ Scoped object is not valid. Type: Country (NNN) ]` (with NNN = the dead object's index). Pattern: `limit = { has_variable = my_country  exists = var:my_country }`.
- **Pattern:**
  ```
  evaluation_chance = {
      value = 100
      if = {
          limit = {
              exists = scope:target_country
              has_attitude = { who = scope:target_country attitude = domineering }
          }
          add = 50
      }
  }
  ```

## IG Scope vs Country Scope Modifiers

- `country_law_enactment_success_add` is **country-scoped** — does NOT work inside `every_scope_interest_group` blocks.
- **General rule:** Country modifiers (`country_*`) only work on countries, state modifiers (`state_*`) only on states.

## Production Method Modifier Scope Rules

PM modifier blocks have strict scope rules:

| Block | Valid modifier prefixes | Examples |
|---|---|---|
| `state_modifiers` | `state_*`, `building_*_throughput_add`, `goods_output_*_mult`, `interest_group_*` | `state_infrastructure_add`, `building_steel_mill_throughput_add` |
| `country_modifiers` | `country_*`, `unit_*`, `interest_group_*`, `state_*`, `building_*_throughput_add` | `country_authority_add`, `unit_kill_rate_add` |
| `building_modifiers.unscaled` | `unit_*` | `unit_morale_loss_mult` |

**Critical:** `unit_*` and `country_*` modifiers NEVER go in `state_modifiers`. Place them in `country_modifiers.workforce_scaled` instead.

**When adding state-level trade bonuses**, use: `state_trade_capacity_add`, `state_trade_quantity_mult`, `state_trade_advantage_mult`, or `building_port_throughput_add`.

## Company Building Requirements

Every company building needs:
1. **Building definition** in `common/buildings/company_buildings.txt` (with `potential` gating on `has_company`)
2. **PM + PMG** in `common/production_methods/unique_pms.txt` and `unique_pm_groups.txt`
3. **Modifier type definition** for `state_building_<name>_max_level_add` in `common/modifier_type_definitions/mod_entity_modifier_types.txt`
4. **INJECT** on the parent company (in `extra_companies_vanilla_updates.txt`) — adds `building_types`, `extension_building_types`, `prosperity_modifier`
5. **Localization** — five keys per building, all required:
   - `building_<name>` (building name) and `building_<name>_desc` in `te_buildings_l_english.yml`
   - `pm_<name>` and `pmg_<name>` in `te_production_methods_l_english.yml`
   - **`state_building_<name>_max_level_add` AND `state_building_<name>_max_level_add_desc`** in `te_modifiers_l_english.yml` — pattern: `"[GetBuildingType('building_<name>').GetName] Max Level"` for the name, `"Increases the maximum number of levels that [GetBuildingType('building_<name>').GetName] can expand to in this state"` for the desc. Without both, the prosperity tooltip shows the raw modifier key.

Use `INJECT:company_name` (not `REPLACE:`) to add fields to vanilla companies without overwriting their entire definition.

If an `INJECT` block adds `prosperity_modifier = { state_building_<name>_max_level_add = 1 }`, that exact modifier key must also exist in `common/modifier_type_definitions/mod_entity_modifier_types.txt` with `color = good`, `percent = no`, and `decimals = 0`. Defining the prosperity modifier in the company file alone is not enough.

Before finishing company-building work, run this audit (Python one-liner against the repo root) to confirm every mod-defined modifier has both name and `_desc` loc keys, taking vanilla loc into account so you don't double-loc a key vanilla already provides:

```bash
.venv/bin/python <<'PY'
import re, glob
VANILLA = '/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/localization/english'
def loc(paths):
    keys = set()
    for f in paths:
        try: t = open(f, encoding='utf-8-sig').read()
        except: continue
        keys.update(re.findall(r'^\s*([a-z][a-z0-9_]+):\d+\s', t, re.M))
    return keys
v = loc(glob.glob(f'{VANILLA}/**/*.yml', recursive=True))
m = loc(glob.glob('localization/english/**/*.yml', recursive=True))
mods = set()
for f in glob.glob('common/modifier_type_definitions/*.txt'):
    for k in re.findall(r'^(?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?([a-z][a-z0-9_]+)\s*=\s*\{',
                        open(f).read(), re.M):
        if re.match(r'(country|state|building|character|interest_group|unit|ship|pop)_[a-z0-9_]+_(add|mult|cost_mult|max_add|capacity_add)$', k):
            mods.add(k)
miss = [k for k in sorted(mods) if (k not in v and k not in m) or
                                    (k+'_desc' not in v and k+'_desc' not in m)]
print('truly missing loc:', miss or 'none')
PY
```

Output should be `truly missing loc: none`. Two pitfalls the audit accounts for: (1) match `:\d+` not `:0` — vanilla often uses `:1` or higher version suffixes, and a `:0`-only check spuriously flags vanilla-loc'd keys. (2) Check both vanilla and mod loc — if the mod re-defines (or `INJECT:`s) a vanilla modifier type, vanilla already supplies the loc and the mod must NOT re-add it under the same key. Re-run before merging any new modifier-type registrations.

## Portrait Modifier Files

Portrait modifier files (in `gfx/portraits/portrait_modifiers/`) require a wrapper block:
```
clothes = {
    usage = game
    selection_behavior = weighted_random

    my_custom_entry = {
        dna_modifiers = { ... }
        weight = { ... }
    }
}
```
Without the `clothes = { usage = game ... }` wrapper, entries will not load.

## Production Method `ai_value`

- **`ai_value` only accepts flat numbers** (e.g., `ai_value = 100`), NOT script value blocks. Using a block causes parse errors that silently break the PM and others in the same file.
- Vanilla pattern: `ai_value = -1000` (flat number).

## V3 Market Pricing Model

- **Price formula:** `price = base_price × [1 + PRICE_RANGE × clamp((BUY - SELL) / min(BUY, SELL), -1, +1)]`
- `PRICE_RANGE` = 0.999 (mod, via define), 0.75 (vanilla). Price always in range `[base_price × 0.001, base_price × 1.999]`.
- `BUY` = total buy orders (domestic consumption + export orders). `SELL` = total sell orders (domestic production + import orders). These are NOT supply/demand — they include trade route orders.
- **Key implication:** Supply ≠ demand in equilibrium. Buy/sell orders don't directly map to monetary flows. `market_imports_reliance` gives fraction of buy orders filled by imports from a partner, NOT a monetary import value.
- **Do NOT attempt to convert reliance to monetary values.** The reliance denominator (total buy orders) includes domestic production which has no direct price relationship to trade flows. Show reliance percentages directly instead.
- **Reliance triggers:** `market_imports_reliance`, `market_exports_reliance`, `market_trade_reliance` — all market scope, accept optional `target` (market) and `goods` params. Used as values in SVs: `value = "market_imports_reliance(scope:partner)"`.
- **Per-good reliance:** Inside `ordered_market_goods`, `order_by = "market.market_imports_reliance(scope:partner)"` auto-evaluates per-good reliance using the implicit goods context.

## Country Type Mechanics

- `set_country_type = decentralized` turns a country into uncolonized land.
- There is NO `kill_country` effect. To remove a country: `annex` it or `set_country_type = decentralized`.
- Country types: `recognized`, `colonial`, `unrecognized`, `decentralized`, `company`.

## Monument vs Expandable Buildings

- **Monuments** have `expandable = no` and are permanently level 1. Never check `level >= 2` or higher on a monument — it will always be false.
- Examples: `building_space_program` (monument, market capital only).
- **Expandable buildings** (default, or `expandable = yes`) can have multiple levels. Use these for level-scaled bonuses: `building_aerospace_industry`, `building_space_mine`.
- **Key pattern:** Check `has_building = building_type:building_foo` for monument existence. Use `any_scope_building = { is_building_type = foo AND level >= N }` only for expandable buildings.
- **Building groups matter:** `bg_monuments`, `bg_military`, `bg_heavy_industry` etc. affect subsidy eligibility, UI grouping, and construction rules. Check a building's group before writing level-based logic.

### When to Use `has_max_level`

This pattern applies specifically to buildings that can (unless there are other restrictions) be **privately owned by companies** while also being **level-capped** (i.e., not freely expandable):
```
expandable = yes
downsizeable = yes
has_max_level = yes
buildable = no        # if the building should only be created via on_action
```
The building's operational PM then grants `state_building_X_max_level_add = 1` per level (in `state_modifiers > level_scaled`), so the max level only increases in the state where the building exists. This means the on_action construction system is the only way to add levels — the player/AI cannot manually expand the building, but companies can still buy ownership of it.

**Why `state_modifiers`, not `country_modifiers`?** `state_building_X_max_level_add` is a state-scoped modifier. If placed in `country_modifiers`, it would apply to ALL states — so two states each with a level-1 building would give every state a max level of 2, allowing manual expansion that bypasses the on_action construction gating.

**When NOT to use `has_max_level`:** If a building is meant to be a non-buyable unique monument (`buildable = no`, `expandable = no`), it cannot be purchased by companies — no `has_max_level` pattern is needed. The old `buildable = no` + `expandable = no` pattern is correct for buildings you never want companies to acquire.

**Megastructure buildings** (`building_space_elevator`, `building_solar_collector`, `building_orbital_battlestation`, `building_mind_upload_nexus`, `building_antimatter_facility`, `building_nanofabrication_center`, `building_consciousness_network`) use `has_max_level` because they were deliberately converted to allow company ownership while retaining on_action level gating.

## Production Method Modifier Scaling Blocks

PMs can define modifiers under three scaling blocks, each with different behavior:

| Block | Scales with | Affected by throughput? | Use for |
|---|---|---|---|
| `workforce_scaled` | Building level × throughput | **Yes** — throughput modifiers, shortages, etc. multiply the values | Goods I/O, employment, economic modifiers that should scale with productivity |
| `level_scaled` | Building level only | **No** — always exactly `value × level` | Max level caps, employment, fixed per-level bonuses that must not fluctuate |
| `unscaled` | Nothing (flat) | **No** — constant regardless of level or throughput | One-time flat bonuses, `unit_*` modifiers |

**Critical:** `state_building_X_max_level_add` and similar state-scoped cap modifiers **must** go in `state_modifiers > level_scaled`, never `country_modifiers` and never `workforce_scaled`. Placing them in `country_modifiers` makes the cap apply to every state (so multiple buildings across states stack their caps everywhere). Placing them in `workforce_scaled` makes the cap fluctuate with throughput, causing erratic downsizing.

These blocks can appear inside `building_modifiers`, `country_modifiers`, or `state_modifiers`:
```
state_modifiers = {
    level_scaled = { ... }       # state-scoped caps (state_building_X_max_level_add here)
    workforce_scaled = { ... }   # state economic effects that scale with throughput
}
country_modifiers = {
    workforce_scaled = { ... }   # country-wide effects that scale with throughput
    level_scaled = { ... }       # fixed per-level country effects
}
building_modifiers = {
    workforce_scaled = { ... }   # goods I/O, employment scaling
    level_scaled = { ... }       # fixed employment
    unscaled = { ... }           # flat bonuses
}
```

## `create_building` Does NOT Accept Variables for `level`

- **`create_building = { building = X level = variable:foo }` will PostValidate-fail.** The `level` parameter only accepts literal integers, NOT variables or script values.
- Error signature: `PostValidate of effect 'create_building' returned false`.
- **Workaround:** Use `extended_timeline_build_specified_building_level` (in `common/scripted_effects/build_effects.txt`), which uses a `switch` statement to map each integer 1–100 to a hardcoded `create_building` call.
- **Convenience wrapper:** `extended_timeline_add_specified_building_level` handles subject/overlord ownership routing automatically. Call from state scope:
  ```
  extended_timeline_add_specified_building_level = {
      ADD_LEVEL = var:lvl_tmp    # or a script value name
      SPEC_TYPE = building_foo
  }
  ```
- The `ADD_LEVEL` parameter is used as a `switch` trigger, so `variable:foo` and script value names both work — they resolve to an integer which the switch matches against cases 1–100.

## Code Generators and Generated Files

- **`gen_ministry_events.py`** generates `events/ministry_law_events.txt`. **`gen_loc_files.py`** generates localization for `extra_law_events` and `ministry_law_events`.
- Running generators **overwrites the entire output file**. Never make manual edits to generated files without also updating the generator.
- Before running any generator, check for uncommitted manual changes with `git diff <file>`.

## Notification Messages for Cross-Country Alerts

- `post_notification = <message_type>` sends a notification. Define message types in `common/messages/extra_messages.txt`.
- **Pattern:**
  ```
  message_name = {
      type = country
      texture = "gfx/interface/icons/event_icons/event_diplomacy.dds"
      group = feed
      severity = neutral
  }
  ```
- Loc keys: `notification_{message_type}_title` and `notification_{message_type}_desc`.

## File Writing Best Practices

- **PowerShell heredoc strings (`@"..."@`) strip tab indentation.** Prefer Python with `\t` for file generation.
- **Always verify tab indentation** after writing files.
- **For large file rewrites** (500+ lines), prefer a Python script over heredoc strings.

## Shared Variable Hazards in Parallel Journal Entries

When multiple JEs can be active simultaneously (like the space race), shared variables cause subtle bugs:

### Multi-Decrement Bug
If multiple JE `on_monthly_pulse` blocks each decrement a shared counter (e.g. `sr_failure_cooldown`), the counter ticks N times per month with N active JEs. **Fix:** Move the decrement to a single `on_monthly_pulse_country` on_action instead of per-JE pulse.

### Weekly Pulse Emulation
There is no engine-provided weekly pulse on_action. If you need effectively weekly behavior, schedule a custom on_action from a monthly pulse with delayed `trigger_event` calls:

```txt
set_weekly_on_action = {
    effect = {
        trigger_event = { on_action = on_action_weekly days = 0 }
        trigger_event = { on_action = on_action_weekly days = 7 }
        trigger_event = { on_action = on_action_weekly days = 14 }
        trigger_event = { on_action = on_action_weekly days = 21 }
    }
}
```

Use `on_monthly_pulse_country` or `on_monthly_pulse_state` as the scheduler depending on which scope you need, and keep the scheduled on_action compatible with that same scope.

### Async Marker Overwrite
If a shared marker variable (e.g. `sr_last_failed_milestone`) is set synchronously in the monthly pulse but read asynchronously by events fired later, a second JE's pulse can overwrite the marker before the first event processes it. **Fix:** Use per-JE boolean flags (e.g. `sr_failed_suborbital`, `sr_failed_orbital`) instead of a single integer. Process ALL set flags in the handler effect (using `if` not `else_if`).

### Dead Shared Variables After Per-JE Refactor
When converting from a single-milestone to a per-JE architecture, ALL references to the old shared variable must be updated — not just the JE definitions. Events fired from `on_yearly_events` have their own triggers and effects that also reference shared variables. Check: `grep -c "old_var_name" events/*.txt`

### `remove_variable` on a Never-Set Variable Triggers "used but never set" Warnings
Save-migration cleanup blocks that `remove_variable = X` for a variable the live code no longer maintains will emit `Variable 'X' is used but is never set` per fire — `remove_variable` counts as a "use" for the engine's static analyzer. Two options when triaging these warnings: (a) keep the cleanup if old saves still carry the var (accept the noise as the cost of save compat), (b) delete the cleanup block once enough time has passed that no live save still has the legacy var. Found via log triage 2026-05-09 — cleanup blocks left over from the strategic-reserve / language-reform refactors were each generating 6+ warnings per save load.

### `trigger_event = { id = <missing_namespace>.X }` Silently No-Ops
The engine emits no log warning when a `trigger_event` references a missing event ID — the call simply does nothing and the AI-weight slot is wasted on a dead branch. Particularly insidious inside `random_list` weighted blocks that retire a JE: deleting the events without removing the dispatcher leaves a no-op slot that's invisible to log triage. Verify after any "absorb events into another file" refactor: `grep -rn "^namespace = <name>" events/` for every dispatcher target. See also `feedback_commit_claim_vs_reality.md` — commit bodies that claim absorption may not match the diff.

### Safe Proxy Pattern
Setting a shared variable as a proxy (e.g. `sr_funding_level = var:sr_funding_<m>`) before using it in a script value IS safe IF:
1. The JE pulse sets and consumes the proxy within the same effect block
2. Script values evaluate immediately at `change_variable add =` time
3. No async events read the proxy value later

**Rule of thumb:** Any variable that is SET by one JE pulse and READ by an async event (fired via `trigger_event`) must be per-JE, not a proxy.

### Per-JE Helper Effects
For events that don't know which milestone they're associated with (generic failure events, cross-milestone events), use helper effects with proxy values:
- `sr_boost_active_milestones`: Set `sr_progress_boost`, call effect — adds to ALL active milestones
- Per-JE boolean flags (`sr_failed_<m>`): Set in pulse, checked by effects in events
- Multi-milestone events: Expand single `change_variable` into per-JE `if` blocks checking `has_variable = sr_active_<m>`

## Event Architecture

- **Extract large logic blocks into scripted effects.** Event-triggering logic (weighted random_list with many entries) belongs in `common/scripted_effects/`, not inlined in journal entries.
- Banking cycle events use `banking_cycle_random_event_effect` in `common/scripted_effects/banking_cycle_effects.txt`.
- **Event IDs must be `<namespace>.<integer>` — letter suffixes silently collapse to the numeric prefix.** Naming sibling events `irredentism.5a` and `irredentism.5b` produces `Duplicated event ID 'irredentism.5a' found` because the engine's event-ID parser stops at the digit boundary; both register as `irredentism.5`. The error message preserves the typed letter, which makes the bug look like a stale-log artifact when both IDs visibly differ in source. Vanilla never uses letter suffixes — pick distinct integers (`.7`/`.8`) and keep the human-readable "Event 5a/5b" labels in comments and `name = <id>.a/.b` option keys, where letter suffixes ARE valid.

## Game Rule Lifecycle

- **Removing a game rule requires searching ALL files for `has_game_rule` references.** `has_game_rule = <deleted_flag>` silently evaluates to **false**, so guarded logic stops executing without any error in logs. This is especially dangerous for core systems like FMC where `has_game_rule` guards on_actions, scripted effects, and company potentials — the system appears to load fine but does nothing at runtime.
- **Duplicate entities gated by game rules** (e.g., `company_X` + `company_X_standard` with opposite `has_game_rule` checks) must be consolidated when the rule is removed, along with their localization keys.
- **Save game compatibility:** Existing saves referencing a deleted game rule flag (e.g., `free_market_construction_disabled`) will log "Failed to read key reference" warnings in `debug.log`. These are harmless but expected.
- **Construction via `country_construction_add` is fundamentally unworkable as a building output.** Buildings producing construction points directly have zero revenue, making private investment impossible — the building fires all workers or requires subsidies where the government pays and private investment is "free."

## Runtime Debugging with `debug_log`

- **Syntax:** `debug_log = "My message with [Scope.Function] interpolation"` — used inside `effect = { }` blocks.
- **Output goes to:** `debug.log` (in game logs directory).
- **Scope interpolation:**
  - `This`, `ROOT`, and bare scope accessors do NOT work. Only named scopes work: `[SCOPE.sType('name').Method]`.
  - Pattern: First `save_scope_as = my_scope`, then `debug_log = "[SCOPE.sState('my_scope').GetName]"`.
  - Scope type accessors: `sState`, `sCountry`, `sParty`, `sCharacter`, `sPop`, `sInterestGroup`, etc.
  - Global variables: `[GetGlobalVariable('var_name').GetValue]`.
  - Plain strings always work: `debug_log = "Effect fired"`.
  - State/country names don't render properly in `debug_log` — use plain-text markers + `debug_log_scopes = yes`.
- **Important:** `debug_log` is an **effect**, not a trigger — it can only appear inside `effect` blocks.
- **JE pulse effects** only fire if the JE is active. To debug activation issues, add logging to separate on_actions.

## Event Targets vs Triggers/Effects Reference

Not all properties usable in script appear in the triggers/effects reference docs. The engine provides two distinct documentation sources:

- **`triggers.log` / `effects.log`** (→ `docs/engine/vic3_triggers_effects_reference.md`): Named triggers, effects, and iterators. These are standalone commands (`is_building_type`, `country_has_building_type_levels`, `every_scope_building`, etc.).
- **`event_targets.log`**: Scope-to-scope accessors and value properties. These are properties on scoped objects — e.g. `level` (building scope → value), `level_after_queued_constructions` (building scope → value), `training_rate` (building scope → value), `controller` (state scope → country), `participants` (market scope → value).

**Where to find `event_targets.log`:** under `<vanilla_docs_path>/event_targets.log` (engine-generated, 1798 lines, organized as `### property_name` with Input/Output scope annotations). On a stock Windows install that resolves to `C:\Users\<windows-user>\OneDrive\Documents\Paradox Interactive\Victoria 3\docs\event_targets.log`.

**When to search `event_targets.log`:**
- You need a building property like `level`, `level_after_queued_constructions`, `training_rate`
- You need a scope accessor like `controller`, `interest_group`, `ideology`
- A property you expect to exist isn't found in `vic3_triggers_effects_reference.md`
- You're writing a script value and need to access a numeric property of a scoped entity

**Example usage in script values:**
```
# event_targets.log properties are used directly in scope:
every_scope_building = {
    limit = { is_building_type = building_solar_receiver }
    subtract = level_after_queued_constructions  # from event_targets.log (building → value)
    add = level                                   # from event_targets.log (building → value)
}
```

## `highlighted_option` vs `custom_tooltip` in Event Options

- **`highlighted_option = yes`** auto-generates a tooltip showing an option's trigger conditions. It dynamically updates if triggers change and shows which conditions in an `OR` are met.
- **`custom_tooltip`** provides a manually-written tooltip string (via localization key).
- **Do NOT use both together.** When `highlighted_option = yes` is present, `custom_tooltip` is redundant — the engine already displays the trigger conditions.
- **Prefer `highlighted_option = yes`** for options gated by triggers (tech requirements, law prerequisites, ministry levels). It stays in sync with the actual triggers automatically.
- **Use `custom_tooltip` only** when: (a) you need to explain an effect rather than a trigger condition, or (b) the option has no `trigger` block but needs explanatory text for other reasons.
- **`highlighted_option` only accepts `yes` / `no` — never a block.** Writing `highlighted_option = { trigger = { ... } }` to get conditional highlighting is invalid; the engine has no per-option conditional-highlight feature. The block form parses past brace matching but causes a downstream `Unexpected token` error several lines later (typically at the next directive after the block). When that happens, parsing of the rest of the *file* runs off the rails: every subsequent `option = { ... }` block is read as a top-level event named `option` (`Duplicated event ID 'option'`, `Namespace 'option' used in event 'option'`), and any later events in the file fail to load entirely (`Event not found! EventID: foo.21`). One bad highlighted_option block can silently kill 2–3 trailing events. If you need conditional emphasis, gate the *option's existence* with `trigger = { ... }` or split into two options with mutually exclusive triggers.

## `every_*` Iterators Enumerate in Tooltip Previews — Wrap with `custom_tooltip`

When an effect contains `every_country = { limit = { ... } ... }` (or any `every_*` iterator with a `limit` block), the engine renders the tooltip preview by listing every entity that currently matches the limit. In an event option's preview (which inherits the event's `after` block effects), this becomes a wall of country names — sometimes dozens, all enumerated alongside the trigger chain that selected them.

Wrap the iterator in a `custom_tooltip = { text = TT_KEY  every_X = { ... } }`. The effect itself still runs unchanged; only the tooltip preview collapses to the loc string at `TT_KEY`. Example: `banking_cycle_spread_contagion` enumerates every trade-linked country for the cascade event preview; wrapping in `custom_tooltip = { text = BANKING_CONTAGION_SPREAD_TT  every_country = { ... } }` reduces the option tooltip to one explanatory line.

Note that an event's `after` block runs regardless of which option the player picks, so its effects appear in EVERY option's tooltip preview. Heavy iterators placed in `after` have outsized tooltip cost — gate them with `custom_tooltip` or move per-option-specific iterators into the option body where only that option's preview is affected.

## Mandatory Reference Doc Consultation

**Before implementing ANY game mechanic**, search the reference docs by SCOPE TYPE to discover all available tools:

1. **Effects/Triggers:** Search `docs/engine/vic3_triggers_effects_reference.md` for "Supported Scopes: <scope>" (e.g., "company", "country", "building") to find ALL effects and triggers for that scope.
2. **Modifiers:** Search `docs/engine/vic3_modifier_type_definitions_reference.md` by modifier category to find all valid modifier names.
3. **Engine docs:** Cross-reference `effects.log` / `triggers.log` when reference docs are ambiguous.

**Why this matters:** Effects like `add_owned_country` (company scope — links a company to a country-subject for colonial companies) can be misread if you only see the name. Always read the full description and confirm the effect does what you expect before scripting.

## Treaty Article Scoping

### `on_entry_into_force` Requires `scope:article_options`

Inside `on_entry_into_force`, `on_break`, and `on_withdrawal` blocks, countries are accessed via `scope:article_options.source_country` and `scope:article_options.target_country` (NOT `scope:source_country` directly). Vanilla `transfer_state` confirms this pattern. To call scripted effects that expect `scope:source_country`/`scope:target_country`, save them first:

```
on_entry_into_force = {
    scope:article_options = {
        source_country = { save_scope_as = source_country }
        target_country = { save_scope_as = target_country }
    }
    my_scripted_effect = yes
}
```

**Outside** `on_entry_into_force` (in `visible`, `ai` blocks), `scope:source_country` and `scope:target_country` may be available — but **not always**, and notably NOT in `possible`. See `Treaty Article Possible/Visible Scope Caveats` above for the matrix:
- `possible`: `scope:source_country` is **undefined** (logs `Undefined event target 'source_country'`). Use `root` for the proposing country, `scope:other_country` for the receiving country, mirroring vanilla `06_transfer_state.txt`.
- `visible`: `scope:source_country` is sometimes set, sometimes not (depends on call site) — wrap reads in `trigger_if = { limit = { exists = scope:source_country } ... }`.
- `can_ratify`: both `scope:source_country` and `scope:target_country` ARE bound (vanilla pattern).
- `on_entry_into_force` / `on_break` / `on_withdrawal`: use `scope:article_options.source_country` / `.target_country` per the snippet above.

### `state_population` / `total_population` Are Triggers, Not Script Values

`state_population` and `total_population` are **triggers** (comparison operators: `state_population >= 100000`, `total_population > 0`). They CANNOT be used as bare values in `weight = { add = … }` modifier blocks (e.g., `add = state_population` causes "Malformed token") or inside nested script-value sub-blocks like `divide = { value = total_population … }` (silently resolves to type `'none'`).

**Two valid uses:**

1. As a **bareword on the modifier-block top-level field** of a script value: `divide = total_population`, `multiply = total_population`. Vanilla precedent: `common/script_values/building_values.txt:26-40` (`country_urbanization_rate`):
   ```
   country_urbanization_rate = {
       value = country_total_urbanization
       if = {
           limit = { total_population > 0 }
           divide = total_population        # bareword — works
       }
       else = { multiply = 0.0001 }
       multiply = 1000
   }
   ```
2. As a **trigger comparator** inside `limit = { … }` or weight modifier conditions.

For population-weighted `random_scope_state`, use tiered weight modifiers (the trigger form):

```
random_scope_state = {
    weight = {
        base = 1
        modifier = { add = 50    state_population >= 500000 }
        modifier = { add = 200   state_population >= 1000000 }
        modifier = { add = 500   state_population >= 5000000 }
    }
    ...
}
```

Alternatively, use `PREV.state_population` when adding to a VARIABLE in a parent scope (as in vanilla `02_south_america_migration.txt`).

**Validation rule**: `/engine-docs/origin/<name>` — if `matches[].type == "triggers"` and not also `"script_values"`, the name is trigger-only and must be used as a bareword in script-value top-level fields, never as `value = <name>` inside a nested sub-block.

### Pick a Destination Once — Don't Call Destination-Picking Scripted Effects Inside `every_scope_pop`

If a scripted effect picks a destination via `ordered_state` / `random_scope_state` and announces it through a notification, call it **once from state (or country) scope** — not from inside an `every_scope_pop` / `every_scope_state` iterator.

```
# WRONG — destination is re-picked for every pop
every_scope_pop = {
    limit = { culture = scope:curr_culture }
    trigger_mass_migration = { POP_RATIO = 0.8 }
}

# RIGHT — pick once, move all matching pops, notify once
trigger_mass_migration = { POP_RATIO = 0.8 }   # internally does ordered_state + every_scope_pop + post_notification
```

The wrong form has two failure modes:
1. The notification fires during the first pop's call (gated by a `sent_message` variable) and announces THAT iteration's `migration_target`. Later iterations may save a different `migration_target` because attraction scores change as pops move, so most pops end up in a state different from the one announced.
2. Even if the destination were stable, you pay N redundant `ordered_state` global iterations.

When refactoring, also make sure the `ordered_state.limit` matches the outer `any_state` existence check exactly. The original `trigger_mass_migration` had an outer "is there a foreign state to flee to?" check but the inner `ordered_state` lacked the `NOT = { owner = PREV.owner }` filter, so it could rank a same-country state highest and pops shuffled internally instead of fleeing.

### Empty `random_scope_*` Leaves the `save_scope_as` Target Undefined

`random_scope_state` / `random_scope_pop` / etc. only fire `save_scope_as = X` if the iterator finds a match. When the parent scope has zero candidates (e.g. a country with no states, a state with no pops of that culture), the inner block doesn't execute and `scope:X` is **not set** for code that follows. Consuming it directly (`move_pop = scope:destination_state`, `change_relations country = scope:winner`, etc.) then yields a `Got value of type 'none'` warning in `debug.log`, reported at the line of the containing scripted effect / event option.

Always gate the consumer:

```
random_scope_state = { ... save_scope_as = destination_state }
if = {
    limit = { exists = scope:destination_state }
    move_pop = scope:destination_state
}
```

Don't rely on the saved scope persisting from a prior loop iteration — even when it does, that's wrong-by-coincidence behavior.

### `count_scope_state` Does Not Exist

There is no `count_scope_state` trigger. To count states matching conditions, use `any_scope_state` with the `count` parameter:

```
any_scope_state = {
    count >= 5
    has_building = building_arms_industry
}
```

### Journal Entries Don't Support `title`

JEs get their display name from a localization key matching their ID (e.g., `je_banking_cycle:0 "Banking Cycle"`). Adding `title = je_banking_cycle` causes a parse error. Remove it.

### Treaty Article Localization Keys

Treaty articles need at minimum: `<article_id>:0 "Display Name"` and `<article_id>_desc:0 "Description"`. Without these, the article shows raw key text in the UI. The `_desc` key appears at the bottom of the article tooltip.

## Treaty Article Duplication Prevention

### Mutual Articles Need `scope:second_country`
For mutual treaty articles (where both parties gain the effect), the `on_entry_into_force` block should use `scope:first_country` and `scope:second_country` (NOT `scope:target_country`). Using `scope:target_country` causes one party to get double effects.

### `DUPLICATE_ARTICLE_SAME_INPUTS` Guard
Directed articles (like `suppress_subject_liberty`, `intelligence_sharing_pact`, `joint_military_exercises`) need `DUPLICATE_ARTICLE_SAME_INPUTS = yes` in their definition to prevent stacking the same article multiple times in one treaty for combined effects.

## Dynamic Tariff Modifier Pattern

The `free_port_state_modifier` required a remove-then-reapply pattern because the modifier's tariff values couldn't dynamically update when rates changed. The solution uses `on_actions` (monthly pulse) to:
1. Check if the state has the modifier
2. Remove it
3. Re-add it with current calculated values via script values

Key pattern: `remove_modifier` + `add_modifier` with `multiplier` calculated from current game state.

## `change_variable` Operations

`change_variable` supports: `add`, `subtract`, `multiply`, `divide`, `modulo`, `min`, `max`. The `multiply = -1` pattern is valid for negating a variable's value (used in heir education rebel child mechanic). All operations are applied to the variable's current value.

**The op slots accept a script value name, a `var:X`, or a literal — but NOT a bare trigger-dispatched read.** `change_variable = { divide = total_population }` resolves `total_population` to type `none` and throws "Value of wrong type" / "Got value of type 'none'" from `jomini_scriptvalue.cpp`. `total_population` (and similar trigger-dispatch reads) only evaluates as a numeric script-value inside a `value = { ... }` script-value block — vanilla `building_values.txt:32` does `divide = total_population` only because it's already inside such a block. Same goes for `set_variable`'s `value` slot. Nor does `change_variable` accept a structured `divide = { value = X min = 1 }` block (no vanilla precedent). Wrap the read in a thin script_value (mod has `te_safe_total_population` for this), then use `divide = te_safe_total_population`. Caught from a runtime error in `population_transfer_effect`.

## Character Trait `replace` Block

When adding a new tier to a mutually exclusive trait group (e.g., adding "terrible" tier to the ruler_poor/average/skilled/exceptional series), EVERY existing trait's `replace = { ... }` block must be updated to include the new trait. Otherwise two traits from the same group can coexist on a character. The `replace` list causes the engine to automatically remove any listed trait when the new one is added.

## `character_*` Modifiers in Country Scope (Tech, Laws, etc.)

**Status (post-1.13):** `character_*` modifiers in country-scope `modifier = { ... }` blocks (techs, laws, INJECTed laws, power bloc `member_modifier` / `leader_modifier`, country-scope static modifiers) **work** — the engine cascades them to every character belonging to the country. Verified empirically with `character_popularity_add` from a tech.

Earlier in mod development this was treated as a silent no-op — that's why some systems ended up with country-level workarounds (e.g. country-scope `country_authority_add` instead of per-character `character_popularity_add`, or only applying char effects via static modifiers attached in `every_scope_character`). Those workarounds may now be redundant.

**Caveats / verification protocol:**
- Not every `character_*` modifier may be wired in country scope yet. When introducing a new one, do a quick in-game test the first time: apply the tech/law to a country, open a character panel, confirm the modifier shows up in the character's tooltip stack.
- `/validate/engine-coverage` can flag unknown names but cannot tell you a known-name modifier is silently dropped at the cascade boundary. The empirical test is the only sure check.
- Where the design needs the modifier scoped to a *specific* character (only the ruler, only commanders, only heirs), keep using `every_scope_character = { limit = { ... } add_modifier = { ... } }` with a static modifier — the country-scope cascade applies to every character indiscriminately.

**Audit existing trait-based workarounds when engine behavior shifts.** When a previously broken cascade (or any silent-no-op feature) starts working, *both* paths can now apply simultaneously, double-counting their effect. Pattern: (1) identify the workaround (often `every_scope_character` adding a trait whose only modifier was the same `character_*` value the tech/law now sets directly), (2) confirm the trait has no other behavioral effect (empty `command_modifier {}`, empty `country_modifier {}`, no triggers depending on it), (3) delete the trait + the dispatcher. The mod's `update_characters` effect + `biological_immortality` / `mind_backups` traits were exactly this case; their `character_health_add` values had been doubling on every character ever since the cascade started working.

## Hidden Variable Design Pattern

For mechanics where the player shouldn't see exact values (like intelligence), set the variable on the country scope and don't reference it in tooltips. Use `triggered_desc` blocks in the JE's `status_desc` to show subtle hints based on variable thresholds (e.g., `var:heir_ed_intelligence >= 4` → "quick study" message).

## Simulation-Driven Balancing

For complex probability systems (multi-tier trait resolution, intelligence modifiers, monthly pulses), write a Python Monte Carlo simulation FIRST. Run 10,000+ iterations per scenario to validate distributions before implementing in Paradox script. This catches non-obvious outcomes like:
- Combined probability of focused vs unfocused categories
- Impact of intelligence variance on extreme outcomes
- Expected total progress over different education durations

## Event Option Tradeoff Patterns

Every event option should have a meaningful cost or tradeoff — no "free" good options (or if there are, all options must be competitive, comparably good, and clearly presented as such). Examples of tradeoff patterns:

- **Spending options** (subsidies, funding programs, UBI expansion, military equipment): Add `add_treasury = { value = yearly_gross_income multiply = -0.03 }` (3-5% of yearly income).
- **Progressive options** (reforms, protections, whistleblower protection): Add `add_radicals` targeting the opposed group (upper strata, ig_devout).
- **Regressive options** (crackdowns, bans, suppression): Add `add_radicals` targeting academics/lower strata, optionally `add_loyalists` for the benefiting group.
- **Middle-ground options** (compromise, study the issue): Can have lighter costs — the tradeoff is not getting the bigger modifier. Still should have `very_small_radicals` from *someone*.
- **Greenwash/co-opt options**: Add `very_small_radicals pop_type = academics` (people see through it).

## Fire-Once Event Pattern

For events representing one-time policy debates or historical moments:
```
trigger = {
    # ... other triggers ...
    NOT = { has_global_variable = event_name_happened }
}
immediate = {
    set_global_variable = event_name_happened
}
```
Use `global_variable` (not `variable`) so it persists across all countries. Combine with `cooldown = { days = long_modifier_time }` for fire-once events.

## Law-Gated AI Chance

Make AI contextually prefer options matching their current laws:
```
ai_chance = {
    base = 1
    modifier = {
        trigger = {
            OR = {
                has_law = law_type:law_relevant_law1
                has_law = law_type:law_relevant_law2
            }
        }
        add = 3
    }
}
```
This ensures repressive governments pick repressive options, liberal governments pick liberal options, etc.

## Pop Scope Properties

- **`total_size`** — valid pop scope accessor for the total size (headcount) of a pop. Found in `event_targets.log`. Used in vanilla events (e.g., `max = scope:relevant_pop.total_size`). Use this when you need the population of a specific pop in script values.
- **`THIS.size`** — NOT a valid accessor. Will cause runtime errors. Use `total_size` instead.
- **`pop_weight_modifier_scale`** — exists in pop scope but is NOT the pop's headcount. It's a modifier scale factor. Do NOT use it as a proxy for pop size.
- **`state_population`** — trigger only (comparison operator), NOT a script value. Cannot be used as `add = state_population`. See "Treaty Article Scoping" section above.

## Interest Group Effects

- **`set_interest_group`** (character scope) — assigns a character to an interest group. Requires `ig:ig_name` prefix (e.g., `set_interest_group = ig:ig_landowners`).
- **`set_interest_group_type`** — does NOT exist as an effect. Always use `set_interest_group`.
- **`ig_type:ig_name`** — NOT a valid scope prefix. Use `ig:ig_name` (e.g., `ig:ig_devout`, not `ig_type:ig_devout`).

## Repeated Sibling Keys Get Deduplicated by the Parser

`paradox_file_parser.py` (and likely the engine — not verified) collapses adjacent sibling keys whose values are bytewise-identical. So in a script value, `multiply = X` followed by another `multiply = X` parses as a single multiply, **not two** — the cube `x³` written as three identical `multiply = above_30` lines silently becomes `x²`. Same trap for two identical `multiply = { value = … }` inline blocks.

Workaround: factor the repeated factor into its own named helper at the next exponent up (e.g. `cultural_pull_share_above_30_squared = { value = above_30  multiply = above_30 }`), then chain `value = squared  multiply = above_30  multiply = …` so each sibling key has a distinct value. Verified discovery via `/script-values/<name>` AST inspection — the parsed `multiply` list shows fewer entries than written. Always verify multi-multiply chains via the AST after authoring.

## Script Values Are NOT Effect Blocks

Script values (`common/script_values/`) evaluate mathematical expressions with triggers/iterators — they are NOT effect blocks. Key restrictions:

- **`save_scope_as` does NOT work** in script values. It's an effect, not available in script value context. Vanilla never uses it in script values.
- **`set_variable`, `set_global_variable`** — also effects, not available in script values.
- **Scope references (`scope:X`)** only work if set by the calling context (e.g., `scope:source_country` from a treaty article, `scope:actor` from a diplomatic action). You cannot create new named scopes inside a script value.
- **Prefer implicit scope chains** — inside an iterator like `every_primary_culture`, the current scope IS the culture object. Use triggers like `is_primary_culture_of` directly on the implicit scope instead of trying to save and compare scopes.
- **Correct pattern:** `every_scope_pop = { limit = { culture = { is_primary_culture_of = scope:target_country } } add = total_size }` — uses pre-existing `scope:target_country` and implicit culture scope.
- **Wrong pattern:** `every_primary_culture = { save_scope_as = my_culture ... scope:my_culture }` — `save_scope_as` silently fails, `scope:my_culture` is always invalid.

## Reusable Scripted Triggers & Effects

**Before writing a trigger or effect block, check whether a scripted trigger or effect already exists.** The mod has a growing library of reusable scripted triggers (`common/scripted_triggers/`) and scripted effects (`common/scripted_effects/`) that encapsulate common patterns. Using them:
- Reduces code duplication and file size
- Makes future changes easier (update one definition instead of 20+ call sites)
- Reduces risk of inconsistency when law/tech/trait sets change

**When to create a new scripted trigger/effect:**
- A trigger or effect block (3+ lines) appears **3 or more times** across different files
- The block checks a **conceptual category** (e.g., "discriminatory laws", "augmentation tech", "aggressive ruler") rather than a one-off condition
- The block is likely to need updating if game mechanics change (e.g., a new minority rights law is added)

**When NOT to extract:**
- Single-line checks (`has_modifier = X`) — too simple, extraction adds overhead for no gain
- Blocks that appear only 1-2 times — not worth the indirection
- Context-specific logic where the "same" lines serve different semantic purposes
- Ideology law approval mappings (individual `has_law` lines serving as a full enumeration, not an OR check)

### Available Scripted Triggers (by file)

**`civil_rights_triggers.txt`** — Minority rights & civil rights movement checks (country scope):
- `has_discriminatory_minority_law` — OR of the 4 discriminatory minority rights laws (violent_hostility, ghettoization, cultural_assimilation, discrimination)
- `has_severe_discriminatory_minority_law` — OR of the 2 worst laws (violent_hostility, ghettoization)
- `has_progressive_minority_law` — OR of 3 progressive laws (protection, affirmative_action, multicultural)
- `has_active_civil_rights_movement` — `any_political_movement = { is_political_movement_type = movement_civil_rights }`
- `has_augmentation_tech` — OR of biohacking_and_human_augmentation / brain_computer_interfaces

**`nuke_triggers.txt`** — Nuclear diplomacy AI logic (country scope, requires `scope:country`):
- `enemy_has_existential_war_goal` — scope:country has make_protectorate/dominion/tributary/annex_country war goals against ROOT
- `enemy_has_subjugation_war_goal` — subset: annex/protectorate/dominion (excludes tributary)
- `ruler_is_aggressive` — ruler has reckless/wrathful/war_criminal traits
- `ruler_is_cautious` — ruler has cautious/honorable traits
- `was_nuked_by_enemy` — `has_variable = nuked_by_country` and `var:nuked_by_country = scope:country`

**`world_war_triggers.txt`** — Ideology classification (country scope):
- `country_is_democratic`, `country_is_communist`, `country_is_fascist`, `country_is_authoritarian`
- `country_has_opposed_ideology`, `world_war_conditions_met`, `can_join_world_war`
- `country_is_ww_belligerent`, `country_is_ww_aggressor`, `country_is_ww_defender`

**`market_triggers.txt`** — Banking cycle phase checks (country scope):
- `banking_cycle_is_panic`, `banking_cycle_is_downturn`, `banking_cycle_is_stagnation`, etc.
- `banking_tool_*_active` — per-tool activation checks

**`misc_triggers.txt`** — Miscellaneous (country/building scope):
- `has_any_langreform_modifier`, `is_radical_law_activated`, `is_exempt_from_radical_backlash`
- `country_has_any_custom_religion`, `is_privately_expandable_building_type`

**`colonial_empire_triggers.txt`** — Geographic macroregion checks (state_region scope):
- `is_in_colonial_macroregion_*` and `is_in_or_adjacent_colonial_macroregion_*` for 14 regions

**`space_race_triggers.txt`** — Space race checks (country scope):
- `sr_has_space_program`, `sr_is_pursuing_milestone`, `sr_can_start_space_race`, `sr_has_failure_cooldown`

**`wonder_triggers.txt`** — Wonder building checks:
- `state_is_in_recognized_continent`, `continent_has_no_building_of_type`, `building_unique_per_owner_potential`

**`combined_arms_triggers.txt`** — Combat unit classification:
- `combat_unit_is_infantry_group`, `combat_unit_is_artillery_group`, `combat_unit_is_cavalry_group`, etc.

### Available Scripted Effects (by file)

**`civil_rights_effects.txt`** — Civil rights event helpers:
- `save_civil_rights_movement_scope` — Saves the active civil rights movement as `scope:civil_rights_movement`

**`space_race_effects.txt`** — Space race milestone effects:
- `sr_complete_milestone_effect`, `sr_complete_*_effect` (per-milestone), `sr_recalculate_cost`, etc.

**`build_effects.txt`** — Building construction:
- `extended_timeline_add_specified_building_level` — Creates building with correct ownership (handles subjects)

**`extra_effects.txt`** — Wonder construction, private investment, bloc unity:
- `space_elevator_construction`, `solar_collector_construction`, `orbital_battlestation_construction`, `mind_upload_nexus_construction`
- `expand_building_private_construction`, `expand_random_building`, `queue_more_private_investment`

**`banking_cycle_effects.txt`** — `banking_cycle_random_event_effect`, `banking_cycle_advance_variables` (uses `banking_random_nudge_down/up_value`), `banking_cycle_check_and_execute_crash` (uses `banking_crash_chance_multiplier_value`)

**`sol_expectations_effects.txt`** — `sol_expectations_monthly_update` (monthly convergence of adaptive expectations toward actual SoL)

**`heir_education_effects.txt`** — Heir education stat gains and resolution effects

**`colonial_collapse_effects.txt`** — `colonial_collapse_effect`

**`combined_arms_effects.txt`** — `apply_combined_arms_bonuses`

## Custom Script-Only Modifier Types

These `script_only = yes` modifiers can be applied from laws, technologies, PMs, traits, etc. via `modifier = { name = value }` blocks. They are consumed by script values and scripted effects — not by the engine directly.

### Banking Cycle
| Modifier | Type | Effect |
|---|---|---|
| `country_banking_random_momentum_mult` | percent, neutral | Scales random cycle momentum nudges (volatility). 0 = normal, +0.5 = 50% more volatile. |
| `country_banking_crash_chance_mult` | percent, bad | Scales crash probability. 0 = normal, +0.25 = 25% higher crash chance, -0.3 = 30% lower. |
| `country_finance_momentum_monthly_add` | flat, neutral | Direct monthly addition to cycle momentum. |
| `country_bubble_pressure_monthly_add` | flat, neutral | Direct monthly addition to bubble pressure. |
| `country_finance_value_monthly_add` | flat, neutral | Direct monthly addition to cycle value. |
| `country_banking_intervention_max_add` | flat, good | Banking intervention points available per activation. |

### SoL Expectations
| Modifier | Type | Effect |
|---|---|---|
| `country_sol_expectation_adaptation_rate_mult` | percent, neutral | Scales how fast expectations converge to actual SoL. +0.5 = 50% faster (shorter memory). |

### Nuclear Weapons
| Modifier | Type | Effect |
|---|---|---|
| `country_nuclear_weapon_attack_success_add` | flat, good | Base attack success chance (from techs: nuclear_weapons +1.0, ICBMs +0.5, hypersonic_weapons +0.5, orbital_weapon_platforms +0.5). |
| `country_nuclear_weapon_defense_chance_add` | flat, good | Base defense chance (from techs: military_aviation +0.25, radar +0.25, missile_defense_systems +0.5, directed_energy_defenses +0.5, orbital_weapon_platforms +0.5). |

### Economy
| Modifier | Type | Effect |
|---|---|---|
| `country_monthly_investment_pool_add` | flat, good | Direct monthly investment pool income addition. |
| `country_monthly_investment_pool_mult` | percent, good | Scales monthly investment pool income. |

## Modifier Value Breakdowns with `GetValueWithBreakdownFor`

### What It Does
`GetValueWithBreakdownFor` generates an engine-formatted breakdown showing all sources contributing to a modifier value. When hovered, it displays a vertical list of each source (PM, tech, law, etc.) with its contribution, a separator, and the total. This is far superior to displaying a raw number because the player can see exactly why the value is what it is.

### Syntax
```
[SCOPE.GetModifier.GetValueWithBreakdownFor('modifier_key')]
```

**SCOPE** must be a scope that has modifiers (usually Country, State, or Building).

### Common Patterns in JE/Tooltip Context

**In journal entries** (ROOT = JournalEntry):
```
[ROOT.GetCountry.GetModifier.GetValueWithBreakdownFor('country_cultural_pull_add')]
```

**In country-scoped tooltips/events** (ROOT = Country):
```
[ROOT.GetModifier.GetValueWithBreakdownFor('country_finance_value_monthly_add')]
```

**In banking JE** (SCOPE.GetRootScope = Country):
```
[SCOPE.GetRootScope.GetModifier.GetValueWithBreakdownFor('country_banking_intervention_max_add')]
```

### When to Use
- **Always prefer `GetValueWithBreakdownFor`** over script value display (`ScriptValue('my_display_val')`) when showing a modifier's current value. The breakdown is free — no extra script value needed.
- Works for **any registered modifier**, including custom `modifier_type_definitions`.
- Especially valuable for modifiers that have multiple contributing sources (techs, PMs, laws, etc.).

### When NOT to Use
- For **computed values** that aren't directly a modifier (e.g., a script value that computes `art_production / global_art_production`). These require `ScriptValue()`.
- `GetValueWithBreakdownFor` only works on modifier keys, not arbitrary script values.

### Vanilla Examples
Vanilla uses this for economy of scale, power bloc mandate, suppression/bolster effects, and building level caps:
```
[Country.GetModifier.GetValueWithBreakdownFor('country_economy_of_scale_add')]
[Country.GetModifier.GetValueWithBreakdownFor('country_power_bloc_mandate_progress_add')]
```

### State Panel GUI Usage
In the state panel (`gui/states_panel.gui`), buttons/textboxes use `State` as the data context. For state-scoped modifiers:
```
[State.GetModifier.GetValueWithBreakdownFor('state_arable_land_mult')]
[State.GetModifier.GetValueWithBreakdownFor('state_homeland_creation_threshold_add')]
[State.GetModifier.GetValueWithBreakdownFor('state_migration_crowding_density_mult')]
```
For country-scoped modifiers accessed from state context:
```
[State.GetOwner.GetModifier.GetValueWithBreakdownFor('country_solar_receiver_max_level_add')]
```
This works in loc keys referenced by `text = "LOC_KEY"` or `tooltip = "LOC_KEY"` in the GUI file.

## Game Concept Tooltips for Breakdowns

### Purpose
Game concepts (`common/game_concepts/`) create hoverable tooltip links in loc strings. When a player hovers over a concept-linked word, a tooltip appears with the concept's description. This is ideal for explaining score components in breakdown displays.

### Registration
1. Define in `common/game_concepts/` (e.g., `extra_game_concepts.txt`):
```
concept_ch_art_production = {
    texture = "gfx/interface/icons/goods_icons/fine_art.dds"
    desc = concept_ch_art_production_desc    # points to a loc key
}
```
2. Add loc keys in localization:
```
concept_ch_art_production:0 "Art Production"
concept_ch_art_production_desc:0 "Calculated from your share of global Fine Art production, multiplied by art effectiveness modifiers."
```

### Usage in Loc Strings
Reference with `[concept_NAME]`:
```
je_ch_breakdown_art:0 "#variable [VALUE]#! [concept_ch_art_production] (details)"
```
This renders "Art Production" as a hoverable link with the description tooltip.

### Best Practice
When displaying a multi-component breakdown (like Cultural Hegemony score), create a game concept for **each component** so players can hover to understand what drives each line. Include the formula or key drivers in the concept description.

## Localization Formatting Codes

### Text Formatting
| Code | Effect |
|---|---|
| `#bold text#!` | Bold text |
| `#title text#!` | Title/header-styled text (larger, styled) |
| `#v text#!` | Value-colored text (green for positive context) |
| `#variable text#!` | Variable/value-colored text (same as `#v`) |
| `#G text#!` | Green text |
| `#R text#!` | Red text |
| `#Y text#!` | Yellow text |
| `#N text#!` | Neutral-colored text |
| `#B text#!` | Blue text |
| `#white text#!` | White text |
| `#o text#!` | Orange text |

### Layout
| Code | Effect |
|---|---|
| `\n` | Newline |
| `#indent_newline:N content#!` | Indented block, N character widths deep |
| `$TAB$` | 3 spaces |
| `$TOOLTIP_DELIMITER$` | Horizontal divider line (graphical) |
| `[Nbsp]` | Non-breaking space |
| `$EFFECT_LIST_BULLET$` | Bullet point marker |

### Tooltips
| Code | Effect |
|---|---|
| `#tooltip_header text#!` | Header line in a tooltip |
| `#tooltippable #tooltip:SCOPE,key text#!#!` | Inline hoverable text with custom tooltip |

### Value Formatting
| Code | Effect |
|---|---|
| `[value\|V]` | Percentage format |
| `[value\|0]` | Integer (0 decimals) |
| `[value\|1]` | 1 decimal place |
| `[value\|2]` | 2 decimal places |
| `[value\|+=0%]` | Signed percentage (+5%, -3%) |
| `[value\|D]` | Detailed format |
| `[value\|=v]` | Equals-prefixed value format |

### Breakdown Display Pattern (Vanilla Convention)
The standard way to display a value+label breakdown line:
```
#variable [VALUE|+=]#! description text
```
This renders the value in variable color followed by the label — e.g., `+5.0 from character popularity`. Used extensively in vanilla JE tooltips (e.g., `je_divided_monarchists_bonapartist_var_tooltip`).

Full breakdown block pattern:
```
"#tooltip_header Changes monthly:#!\n$TOOLTIP_DELIMITER$\n#variable [VALUE1|+=]#! from source 1\n#variable [VALUE2|+=]#! from source 2"
```

### Important Limitation: No Column Alignment
Victoria 3 uses a **proportional font** (not monospace) for all text rendering. This means:
- Space-padding for column alignment is unreliable — characters have different widths.
- There is **no tab-stop or two-column grid mechanism** in the loc system.
- The best approach for structured data is `#variable VALUE#! label` (value-first) with newlines, not label-then-value with alignment padding.
- `#indent_newline:N` provides visual structure but doesn't enable column alignment.

## AI Diplomatic Action Best Practices

### Anti-Spam: Low `evaluation_chance`
Togglable pact-based diplomatic actions (like covert operations, increase_relations) are re-evaluated every tick. High `evaluation_chance` (0.1+) causes the AI to rapidly toggle pacts on/off. Use **0.02–0.05** for strategic decisions. Adjust with conditionals:
```
evaluation_chance = {
    value = 0.03
    if = {
        limit = { ruler_is_aggressive = yes }
        add = 0.02
    }
    if = {
        limit = { ruler_is_cautious = yes }
        multiply = 0.5
    }
}
```

### Financial Health Guards
AI should never propose expensive diplomatic actions while in financial distress:
```
will_propose = {
    in_default = no
    # ... other conditions
}
```

### Meaningful `propose_score`
Flat `propose_score` values make all targets equally attractive. Use conditional modifiers:
```
propose_score = {
    value = 5
    if = {
        limit = { has_diplomatic_pact = { who = scope:target_country type = rivalry } }
        add = 10
    }
    if = {
        limit = { country_rank = rank_value:great_power }
        add = 5
    }
}
```

### AI-Only Logic in JE Pulses
Scripted buttons have no AI support. For player-facing controls (funding levels, priorities) that the AI also needs to manage, add AI-only logic blocks in the JE's `on_monthly_pulse`:
```
if = {
    limit = { is_player = no }
    # AI-specific management
    set_variable = { name = funding_level value = 1 }
}
```

### Loc Keys for Effect Display
Diplomatic action confirmation dialogs show "Effects:" using `<action_name>_effect_desc_global:0` loc keys. Also provide `_effect_desc_first:0` and `_effect_desc_third:0` for notification messages.

## Extending Vanilla On-Actions Safely

**Never add `effect = { }` directly to a vanilla on-action.** Adding `effect` to a vanilla on_action (e.g. `on_yearly_pulse_country`, `on_election_campaign_end`) **overwrites** the vanilla effect block, silently breaking base-game logic.

**Safe pattern — use `on_actions` sub-action:**
```
on_election_campaign_end = {
    on_actions = {
        my_custom_election_end_handler
    }
}

my_custom_election_end_handler = {
    effect = {
        # Your custom logic here — vanilla effect block is preserved
    }
}
```

The `events` and `on_actions` lists are **additive** and safe to extend; `effect` is **not**.

**Known vanilla `effect` blocks that would be overwritten:**
- `on_election_campaign_end`: Sets `brz_election_done` variable, removes `modifier_government_recently_couped`.
- Many `on_yearly_pulse_*` and `on_monthly_pulse_*` actions have vanilla effects.

## Comparing State References Across Scopes

When comparing stored state references (e.g. `iw_target_election_interference_<slot>` stores a capital state) against another entity's capital:
1. Save the reference state as a scope: `capital = { save_scope_as = my_capital }`
2. Inside nested scopes, compare using `scope:my_capital = { this = PREV.var:stored_state_var }`
3. Be careful with PREV chains — `PREV` inside a `scope:X = { }` trigger block refers to the scope **before entering** the block, not the pact scope.

## `add_amendment` Requirements

The `add_amendment` effect has **two required parameters** beyond `type`:

```
add_amendment = {
    type = amendment_example
    sponsor = interest_group   # REQUIRED — the IG sponsoring the amendment
    cooldown = 120             # REQUIRED — months before it can be revoked/replaced (0 = no cooldown)
}
```

**Sponsor scoping:** In history files using `active_law:lawgroup_X ?= { }`, the scope is the law and PREV is the country, so use `sponsor = PREV.ig:ig_X`. In events using `every_scope_law = { }`, ROOT is the country, so use `sponsor = ROOT.ig:ig_X`.

**`possible = { always = no }` blocks `add_amendment`.** The engine checks the amendment's `possible` trigger when `add_amendment` is called. If it evaluates to false, the amendment silently fails to apply (no error, no PostValidate — just doesn't show up). For event-only amendments that shouldn't be proposed through IG activism, use `possible = { always = yes }` combined with `amendment_activism_multiplier = 0`. The `amendment_activism_multiplier` controls IG proposal behavior independently.

## Journal Entry Modifier Scoping

Modifiers applied by journal entry buttons or JE monthly/weekly pulse should be applied to the **journal entry scope** rather than directly to the country. This causes the modifier to appear in the JE's modifier panel instead of cluttering the country's general modifier list.

### Pattern

```
# GOOD: Apply modifier to JE scope (displays in JE panel)
je:je_my_journal_entry = { add_modifier = { name = my_modifier } }
je:je_my_journal_entry = { add_modifier = { name = my_scaled_modifier multiplier = my_script_value } }

# Check if JE has the modifier
je:je_my_journal_entry = { has_modifier = my_modifier }

# Remove modifier from JE
je:je_my_journal_entry = { remove_modifier = my_modifier }

# BAD: Apply directly to country (shows in country modifier list)
add_modifier = { name = my_modifier }
```

The modifier's effects (e.g., `country_loan_interest_rate_mult`) still apply to the country — only the **display location** changes.

### When to Use JE Scope

| Context | Scope to JE? | Reason |
|---|---|---|
| **Button toggle modifiers** (banking tools, climate policies, wartime toggles) | ✅ Yes | Player policy choices specific to the JE system |
| **Monthly pulse dynamic modifiers** (phase modifiers, funding costs, scaled benefits) | ✅ Yes | JE-specific mechanic modifiers recalculated each tick |
| **Event-applied one-time bonuses** (ww_fresh_forces, arsenal_of_democracy) | ❌ No | Standalone event rewards, not JE-managed toggles |
| **Event-applied modifiers re-applying a JE-managed modifier** (e.g., event adds ww_rearmament) | ✅ Yes | Same modifier managed by JE; keep consistent scope |
| **Permanent status modifiers** (nuclear_power, nuclear_disarmament) | ❌ No | Status persists after JE completes/deactivates |
| **on_complete/on_fail modifiers** (colonial_empire_solidified, failed_state) | ❌ No | JE disappears on completion; modifier must outlive it |
| **Cross-country modifiers** (contagion effects on other countries) | ❌ No | Target country may not have the JE |
| **Movement-scoped modifiers** (colonial_pressure_movement_radicalism) | ❌ No | Applied to political movement scope, not country |
| **Status modifiers checked cross-entity** (un_member, un_security_council) | ❌ No | Checked in 40+ places across events, treaty articles, on_actions |
| **Social movement modifiers** (modifiers_while_active) | N/A | Already a JE property, not `add_modifier` |

### Scripted Trigger Updates

When moving modifiers to JE scope, update associated scripted triggers:
```
# Before
banking_tool_rate_hike_active = { has_modifier = banking_policy_rate_hike }

# After
banking_tool_rate_hike_active = { je:je_banking_cycle = { has_modifier = banking_policy_rate_hike } }
```

### Systems Using JE-Scoped Modifiers

| System | JE Name | Modifiers |
|---|---|---|
| Nuclear Weapons | `je_nuclear_program` | `nuclear_weapon_program_funding` |
| Banking Cycle | `je_banking_cycle` | All intervention tools (14 market, 8 command, 8 cooperative), phase modifiers (18), bubble inertia (3), fiscal policy, `planning_treasury_pool_balance` (command-economy auto-balance) |
| Global Warming | `je_global_warming` | `global_warming`, 8 climate policy modifiers |
| Covert Warfare | `je_covert_warfare` | `intelligence_capacity_defense`, `iw_domestic_defense`, `iw_funding_defense`, `covert_operation_funding_cost` |
| World War | `je_world_war` | 9 modifiers: `ww_rising_tensions`, `ww_rearmament`, `ww_appeasement`, `ww_lend_lease`, `ww_total_war_economy`, `ww_war_propaganda`, `ww_wartime_rationing`, `ww_home_front_strain`, `ww_prolonged_war_exhaustion`. NOT: `ww_fresh_forces`, `ww_arsenal_of_democracy` (event-applied one-time bonuses) |
| United Nations | `je_united_nations` | 6 modifiers: `un_membership_benefits`, `un_high_authority_infamy`, `un_npt_disarmament`, `un_nonmember_pariah`, `un_champion_order_cost`, `un_undermine_order_cost`. NOT: `un_member`, `un_security_council`, `un_headquarters` (status modifiers checked cross-entity) |
| Colonial Empire | `je_colonial_empire` | 2 modifiers: `colonial_empire_under_pressure`, `colonial_empire_crumbling`. NOT: `colonial_empire_solidified`, `colonial_empire_collapsed` (on_complete/on_fail), movement radicalism modifiers (movement-scoped) |
| Space Race Colonization | `je_space_race_solar_colonization` | 68 colony modifiers (`sr_colony_*`), `sr_solar_system_trade`. NOT: milestone modifiers like `sr_first_*`, approach/failure modifiers (country-scoped, not JE-managed) |

### Important: Update ALL References

When moving a modifier to JE scope, update **every** reference across the codebase:
- Scripted triggers (`has_modifier` checks)
- Scripted buttons (visible/possible/effect blocks)
- Scripted effects (add/remove/check)
- On_actions (cleanup on law change)
- Script values (counting countries with a policy)
- Treaty articles (checks and applications)
- Events (trigger conditions)
- Political movements (support conditions)

### JE Lifecycle: `invalid` + `on_invalid` Cleanup

A JE with only an `invalid` trigger will disappear when the trigger fires, but **country-scoped state (variables, modifiers applied outside the JE scope) is not cleaned up**. Always pair `invalid` with `on_invalid` when the JE sets country variables or applies country-scoped modifiers that should be removed on invalidation.

```
je_my_je = {
    invalid = { NOT = { has_law = law_type:law_monarchy } }
    on_invalid = { my_je_cleanup_effect = yes }  # remove country vars, remove leftover modifiers
    ...
}
```

Observed failure: `je_heir_education` had `invalid = { NOT = { has_law = law_type:law_monarchy } }` but no `on_invalid`. Switching government type invalidated the JE but left the `heir_education_innovation_cost` authority modifier (applied to country by the heir-education monthly pulse) permanently stuck on the country. Fix: add `on_invalid = { heir_education_cleanup_effect = yes }` to the JE, and add a one-shot safety-net cleanup to `legacy_modifier_cleanup.txt` for existing saves.

### Auto-Balancing Modifier Pattern (Multiplier Derived From Live State)

When a JE-scoped modifier must scale to counteract a live game value (e.g., "transfer from treasury to investment pool to keep pool net income at zero"), you can compute the multiplier directly by negating the live read — **unless** your modifier's key is included in that read, in which case you must subtract out your prior contribution (see "Prior-Multiplier Subtraction" note below).

**Simple case (modifier key NOT included in the target value):**

```
# Script value — just negate the live engine read directly
my_balance_multiplier = {
    value = 0
    subtract = live_engine_value    # e.g. investment_pool_net_income
}

# Scripted effect (monthly + button-triggered)
my_balance_update = {
    if = {
        limit = { <applicability trigger> }
        je:je_my_je = {
            if = {
                limit = { has_modifier = my_balance_modifier }
                remove_modifier = my_balance_modifier
            }
            add_modifier = { name = my_balance_modifier multiplier = my_balance_multiplier }
        }
    }
    else = {
        if = { limit = { je:je_my_je ?= { has_modifier = my_balance_modifier } } je:je_my_je = { remove_modifier = my_balance_modifier } }
    }
}
```

**When prior-multiplier subtraction IS needed:** If your modifier key is included in the live engine read (e.g., a vanilla `country_monthly_X` key that the engine sums into the matching income/expense value), then removing and re-adding within the same effect still shows the old value in the read. In that case, cache the last-applied multiplier in `var:my_prior_mult` and subtract it: `add = var:my_prior_mult; subtract = live_engine_value`. See the "Modifier values are NOT recalculated within a single effect block" entry in `.github/copilot-instructions.md` for the general pattern.

Used by: `banking_cycle_update_ce_pool_balance` (command economy investment-pool balance, `planning_treasury_pool_balance` modifier). `country_weekly_investment_pool_add` is a mod-created key not included in `investment_pool_net_income`, so the simple direct-negate form is used with no prior-variable caching.

## Journal Entry 1.13 Display Surface

Vic3 1.13 added a rich set of JE-display fields, documented canonically in vanilla's `common/journal_entries/journal_entries.md`. Rather than restate the spec, this is a quick map of what the mod uses and where to find vanilla examples for each.

| Field | Purpose | Vanilla example |
|---|---|---|
| `should_update_on_player_command = yes` | Refresh the JE panel on player action instead of waiting for monthly tick. | `00_grunderzeit.txt`, `00_meiji_restoration.txt` |
| `event_outcome_completed_effect_desc { header effect }` | Auto-generated tooltip preview of completion. Effect block is descriptive only; not executed. Multiple per JE allowed (cf. meiji.1.a / meiji.1.b). | `00_meiji_restoration.txt` |
| `event_outcome_failed_effect_desc` / `_invalidated_effect_desc` / `_timeout_effect_desc` | Same shape, for the matching transitions. Effect body of just `custom_tooltip = X` is legal. | `00_meiji_restoration.txt` |
| `event_outcome_activated_effect_desc` | Preview blocks shown at activation time — useful for perpetual JEs that have no completion transition (membership-tier rewards, etc.). | none in vanilla; mod uses on `je_united_nations`. |
| `custom_completion_header` / `_failure_header` / `_on_completion_header` / `_on_failure_header` | Loc-key overrides for the generic banner / popup headers. | `00_meiji_restoration.txt` (per-victory-path flavor) |
| `widget = { gui = ... name = ... container = ... }` | Embed a custom GUI panel in one of the 8 anchor slots (`custom_widget_container_je_icon`, `_1`–`_7`). The 7 slots are interleaved with built-in JE elements (icon, status, scripted_buttons, progress_bars, description, involved_countries, completion block). | `00_meiji_restoration.txt` + `gui/journal_entry_widgets/ep2_japan_widgets.gui` (emperor portrait + daimyos list). Mod pilot: `je_strategic_reserve` + `gui/journal_entry_widgets/strategic_reserve_widget.gui`. |
| `display_progressbar_as_months = yes` | Render numeric goal as months instead of raw count. | unused in mod. |
| `should_be_pinned_by_default_involved` / `_uninvolved_or_context` | Default-pin the JE in the outliner. | widely vanilla; mod sets `_uninvolved_or_context = yes` on every JE. |
| `transferable` / `can_revolution_inherit` | Whether the JE follows the player on country switch / revolution. | widely vanilla. |

**Widget loc binding pattern.** Inside a widget loc string anchored to a JE panel, the data context is the JournalEntry. To read a country-scope variable or script value, use:

```
[JournalEntry.GetCountry.MakeScope.Var('foo').GetValue]
[JournalEntry.GetCountry.MakeScope.ScriptValue('foo')|0]
```

Mirrors the established `[ROOT.GetCountry.MakeScope.ScriptValue('foo')]` pattern used in the mod's `status_desc` / `progress_desc` loc strings, but `JournalEntry.GetCountry` is unambiguous in widget context. See the `je_strategic_reserve_widget_step_badge` loc key for a working example, and vanilla `gui/journal_entry_widgets/ep2_japan_widgets.gui` for richer patterns (portraits, fixed-grid lists, scripted-GUI bindings).

**`event_outcome_*_effect_desc` blocks: effect bodies are tooltips, not behavior.** Per the vanilla doc: "the effects here are only used for description purposes and will not actually happen." A body of just `custom_tooltip = SOME_KEY` is a valid descriptive block — the engine renders it as the tooltip text alongside the auto-generated change preview. Use this when there's no clean modifier or variable mutation to preview (cf. the interstellar_results JE, where the reward is randomized across 30+ flavor sub-events).

**Perpetual JEs need `event_outcome_activated_effect_desc`, not the completed/failed variants.** Perpetual JEs (`complete = { always = no }`) never fire completion or failure transitions, so the `_completed_effect_desc` / `_failed_effect_desc` blocks are dead text. Use `_activated_effect_desc` for previewing tier-threshold rewards or other "once you join, here's what unlocks" semantics.

## Useful Triggers & Accessors Reference

Triggers and scope accessors that are easy to overlook or hard to discover:

### Country Ranking
- **`global_country_ranking`** — Country-scope trigger. Returns prestige-based global rank (1 = highest). Useful for "top N countries" checks: `global_country_ranking <= 3`. Cheaper than counting countries with `any_country = { count >= N ... }`.

### Law Iterators
- **`any_active_law`** — Country→Law trigger iterator. Iterates over all of a country's currently active laws. Use for finding law mismatches, checking groups, etc.
- **`random_active_law`** / **`every_active_law`** / **`ordered_active_law`** — Effect variants of the above.
- **`active_law:lawgroup_X`** — Country→Law accessor. Scopes to a specific law group's active law directly.
- **`law_type`** — Law→LawType scope accessor. Gets the law_type key from a law scope.
- **`is_same_law_group_as`** — LawType trigger. Compares whether two law types belong to the same law group. Accepts a scope reference to another law_type.
- **`activate_law`** — Country effect. Accepts scope references to law_type: `activate_law = scope:saved_law_type`.
- **`enacting_any_law`** — Country trigger. Checks if the country is currently in the process of enacting any law. Useful to gate events that would force law adoption.

### Authority Triggers — `authority` vs `produced_authority`
Four country-scope authority triggers, easy to confuse:
- **`authority`** — *available* (free / uncommitted) authority. The pool the country could spend on a new decree right now. Use this when gating "can the player or AI afford to spend N authority?".
- **`authority_usage`** — *consumed* authority (sum of decrees, institutions, etc.).
- **`produced_authority`** — *generated* authority over time (effectively used + free). High in almost every late-game country regardless of how much is actually spendable.
- **`relative_authority`** — unused fraction (`authority / produced_authority`, 0–1). Useful for "do I have plenty of headroom?" checks.

**Common pitfall:** using `produced_authority > N` to gate an option that costs authority. Once a country has been generating authority for a few decades, `produced_authority` is essentially always `> N` even if every drop is already committed to existing decrees. AI weights tied to `produced_authority` cause AI to dump authority it doesn't actually have. Use `authority > N` for cost gates and AI-spend decisions.

### Lawgroup Orthogonality
**Distribution of Power and Governance Principles are different axes.** A country has one law from each lawgroup; they coexist independently:
- **`lawgroup_distribution_of_power`** — who holds power: Autocracy / Oligarchy / various Voting laws / Universal Suffrage / Single-Party State / etc. The "concentration of power" axis.
- **`lawgroup_governance_principles`** — head-of-state structure: Monarchy / Presidential Republic / Parliamentary Republic / Theocracy / Council Republic / mod-added `law_direct_democracy` / `law_neocameralism` / etc.

When designing a system that responds to "how authoritarian is this country", contribute modifier values across the *distribution-of-power* axis (and possibly free-speech / internal-security), not governance-principles. Don't mix law contributions across the two axes — the result is an incoherent gate where (e.g.) Direct Democracy lowers a value that Parliamentary Republic doesn't touch.

## Legacy Modifier Cleanup Pattern

When migrating modifiers from country scope to JE scope, existing save games still have the old country-level modifiers. A cleanup scripted effect (`legacy_je_modifier_cleanup_effect`) runs once via `on_game_start` to remove these stale modifiers.

**File:** `common/scripted_effects/legacy_modifier_cleanup.txt` + `common/on_actions/legacy_modifier_cleanup.txt`

### Simple Cleanup (toggle/pulse modifiers)

For modifiers that a JE monthly pulse or scripted button will re-apply to JE scope automatically on the next tick:
```
# Just remove from country — the JE pulse/button will re-add to JE scope
if = { limit = { has_modifier = banking_policy_rate_hike } remove_modifier = banking_policy_rate_hike }
```

### Re-Apply Cleanup (one-shot event modifiers)

For modifiers applied by one-time events (not re-applied by any pulse), the cleanup must also re-add the modifier to the JE scope:
```
# Remove from country AND re-apply to JE scope (guarded by has_journal_entry)
if = {
    limit = { has_modifier = sr_colony_europa }
    remove_modifier = sr_colony_europa
    if = {
        limit = { has_journal_entry = je_space_race_solar_colonization }
        je:je_space_race_solar_colonization = { add_modifier = { name = sr_colony_europa } }
    }
}
```
The inner `has_journal_entry` guard is critical — if the country doesn't have the JE (e.g., it completed or was never started), the `je:` accessor would error.

### Lifecycle
- Safe to delete cleanup files once no save games from before the migration exist.
- Delete BOTH the scripted effect file AND the on_action file (`common/on_actions/legacy_modifier_cleanup.txt`).

## Localization Validation

### Server Endpoint

Use `GET /unlocalized` to find all entities missing localization keys:
```powershell
# All unlocalized entities (mod-only by default)
Invoke-RestMethod http://localhost:8950/unlocalized

# Filter to one type
Invoke-RestMethod "http://localhost:8950/unlocalized?type=Modifiers"

# Include vanilla entities too
Invoke-RestMethod "http://localhost:8950/unlocalized?mod_only=false"
```

### Localization Key Requirements by Entity Type

| Entity Type | Required Keys |
|---|---|
| Static modifiers | `modifier_name:0`, `modifier_name_desc:0` |
| Modifier type definitions | `modifier_name:0`, `modifier_name_desc:0` |
| Technologies | `tech_id:0` |
| Buildings | `building_id:0` |
| Laws | `law_id:0` |
| Decrees | `decree_id:0` |
| Events | `namespace.N.t`, `namespace.N.d`, option keys (`.a`, `.b`, `.c`, etc.) |

### Workflow
1. Run `/unlocalized?type=Modifiers` (or other type) to find missing keys
2. Add keys to the relevant loc file (or `te_miscellaneous_l_english.yml` as a catch-all)
3. Run `python organize_loc.py` to sort and categorize all keys
4. Verify with another `/unlocalized` call

## Treaty Article Cross-Article Exclusion: `any_scope_treaty` Misses the Draft

When a treaty article must reject **another article in the same draft** (e.g. nuclear program aid and a nuclear program freeze in one treaty are nonsense), the trigger must reach the **in-construction draft**, not just in-force treaties.

```
# any_scope_treaty iterates IN-FORCE treaties only — misses the current draft
any_scope_treaty = { any_scope_article = { has_type = nuclear_program_aid ... } }

# scope:treaty.any_scope_article_option iterates the in-construction draft
scope:treaty ?= {
    any_scope_article_option = {
        has_type = nuclear_program_aid
        target_country = scope:other_country
    }
}
```

Use BOTH if the rejection should apply against existing pacts AND the same draft. Vanilla example: `06_transfer_state.txt` filters its own draft via `scope:treaty ?= { NOT = { any_scope_article_option = { ... } } }`. The mod's nuclear aid / disarmament / pause articles previously used only `any_scope_treaty`, which is why a single draft could bundle aid + freeze and pass each article's `possible` clause individually (fixed 2026-05-03).

`scope:treaty` is a power_bloc/treaty scope and may not exist in every evaluation context — guard with `?=` (optional). `any_scope_article_option` (note the `_option` suffix) is the right iterator for draft articles, since it includes the article's parameter inputs (`source_country`, `target_country`) needed for filtering.

**Symmetric checks required.** A cross-article exclusion has to be wired in BOTH articles — if only A rejects B, the player can still create a draft by adding B first then A. Both `possible` clauses must check the other type.

## Top-Level Database Collisions: Use `INJECT:` Instead of Re-Declaring

The Clausewitz database is keyed by the **top-level identifier** of each entry. If a mod file declares the same top-level key vanilla already defines, the engine emits `Duplicated key X will not be created` in `debug.log` and **drops the mod copy entirely**. This applies to anything stored in `gamedatabase` — portrait modifiers, technology entries, buildings, ideologies, modifier type definitions, etc.

**Symptom:** mod file looks correct, individual entries inside it look right, but none of the entries take effect in-game.

**The bug:** the file uses a top-level wrapper key that vanilla also uses (`clothes`, `modifier`, etc.) and the entire wrapper gets dropped.

**Wrong (mod's `te_clothes.txt` was doing this):**
```
clothes = {
    usage = game
    selection_behavior = weighted_random

    te_european_female_ruler_suit = { ... }
    te_other_entry = { ... }
}
```
Vanilla `01_clothes.txt` already has `clothes = { ... }`, so the mod's whole block is dropped silently.

**Correct:**
```
INJECT:clothes = {
    te_european_female_ruler_suit = { ... }
    te_other_entry = { ... }
}
```

`INJECT:` (and `REPLACE:` / `REPLACE_OR_CREATE:`) are engine-native directives that merge or replace into the matching vanilla entry. Don't re-declare `usage` or `selection_behavior` inside the inject block — vanilla already supplies those, and overriding them risks resetting unrelated fields.

The same rule applies any time the wrapper key collides with vanilla: e.g. you cannot define a fresh `country_modifiers = { ... }` block in `common/static_modifiers/` if vanilla already owns the same modifier name; use `INJECT:vanilla_modifier_name = { ... }`.

**How to spot it:** grep `debug.log` for `Duplicated key`. Cross-reference against vanilla's `gfx/portraits/portrait_modifiers/`, `common/modifier_type_definitions/`, etc. If the duplicated key matches a vanilla file, switch the mod file to `INJECT:`.

**Tooling caveat:** any Python audit / walker tool that scans `common/` files needs to handle these prefixes. A naïve identifier regex (`[A-Za-z_]…`) won't match `REPLACE_OR_CREATE:foo` and the entity silently drops out of the walk. See `docs/guides/python_tools.md` § "Gotchas when writing tooling that walks `common/`" for the canonical fix and a regression test.

### `INJECT:` for adding *missing* fields is the safest wedge

The cleanest case for `INJECT:` is **adding a field vanilla doesn't already declare** on that entity. No collision semantics to reason about — engine just sees the new field. Example: vanilla's `BHT` and `IDN` country_formation entries don't declare `potential = { ... }`, so `INJECT:BHT = { potential = { NOT = { has_technology_researched = decolonization } } }` cleanly adds visibility gating without any of the duplicate-key risk that re-declaring a field vanilla owns would carry.

When the field you want to extend already exists in vanilla (e.g. you want to *tighten* vanilla's `possible` block by ANDing extra conditions), `INJECT:` is risky — engine semantics on duplicate sibling keys vary by entity type, and you may get last-wins (silently drops vanilla's conditions) rather than concatenation. Reach for `REPLACE:` and re-state vanilla's body in those cases. Look for a *different* field on the same entity that's empty in vanilla and serves the same gate role (`potential` vs `possible`, `is_shown` vs `selectable`, etc.) — that often turns a brittle REPLACE: into a clean INJECT.

### `INJECT:` silently fails on mod-only or REPLACEd entities

`INJECT:<name>` only merges when `<name>` is a **vanilla-defined entity that nothing in the mod has REPLACEd**. Two failure modes both produce zero error and zero log line:

1. **Mod-only target** — the entity is defined directly (no prefix) in the mod itself; vanilla doesn't know about it. The mod's own definition wins; the INJECT block is silently dropped. Example: `INJECT:pmg_aker_oslo_shipyard = { production_methods = { pm_modern_company_shipbuilding } }` next to a bare `pmg_aker_oslo_shipyard = { ... }` earlier in the same file → the new PM never makes it into the merged group.
2. **REPLACEd target** — another mod file declares `REPLACE:<name> = { ... }`. The REPLACE wins; INJECTs from other files are silently dropped. Example: `common/laws/movement_attraction_modifiers.txt` had `INJECT:law_multicultural` adding a `state_pop_support_movement_civil_rights_mult`, while `common/laws/modified.txt` REPLACEd `law_multicultural` outright — the inject's modifier never applied at runtime.

**Fix:** edit the entity's bare or `REPLACE:` definition directly — add the field there alongside its other modifiers, and remove the INJECT.

**Detection:** `mod_structure_audit` (auto-runs on `POST /reload`, surfaces in the warnings array) cross-references every `INJECT:<name>` against the mod's bare definitions and `REPLACE:<name>` directives. Findings live in `docs/engine/mod_structure_report.md`. Brace-balance and within-namespace top-level collisions are caught by the same audit.

### Repurposing a dormant vanilla bool via loc override

`INJECT:` can add fields to a vanilla entity but **cannot remove** existing ones. When a vanilla entity grants a bool / flag-style modifier the mod has rendered obsolete (e.g. the mod replaced the gate that was the bool's only consumer), the choice is between `REPLACE:`-ing the whole entity (incurring a re-diff burden on every Vic3 patch) and **leaving the dormant field in place but overriding its localization key in the mod's loc** so the displayed text reflects its new repurposed meaning. The latter is appropriate when (a) no engine code other than the mod's own scripts reads the bool, (b) the mod can re-use the field as a flag (`has_modifier = X` or numeric read of the same key) for some new effect, and (c) the entity's surrounding fields are stable enough that REPLACE-ing would be wasted work each patch.

Concrete example: vanilla `identity_sovereign_empire` grants `power_bloc_leader_can_make_subjects_bool = yes` on its `power_bloc_modifier` block, originally as the gate for the `force_become_subject` action. The mod opened that action to all bloc identities via a graded `te_subjugation_strength` score, leaving the bool inert. Rather than REPLACE the SE identity, the mod overrides the `power_bloc_leader_can_make_subjects_bool` key in `te_modifiers_l_english.yml` (loc files load mod-after-vanilla, so same-key entries win) and reads `has_modifier = power_bloc_leader_can_make_subjects_bool` in the action's `change_infamy` block to grant SE a 50% infamy discount — turning dead vanilla code into a flavorful identity perk with one loc edit and one trigger line. **Caveat:** if a future Vic3 patch ever drops or renames that bool from `identity_sovereign_empire`, the discount silently breaks; flag the dependency in a header comment so the next vanilla-bump catches it.

### `base_values` as the always-on baseline source

The vanilla `base_values` static modifier (extended via `INJECT:base_values = { ... }` in `common/static_modifiers/extra_modifiers.txt`) is the cleanest place to put a baseline contribution that should appear in the modifier's `GetValueWithBreakdownFor` breakdown alongside variable contributions from laws / techs / events. Even if the bar / read site only consumes the modifier conditionally (e.g. "while button X is active"), keeping the baseline in `base_values` means the player sees `Base values: +1.0 / Law A: +0.7 / Law B: -0.4` as a single connected line item rather than `Baseline (+1.0) / Laws: +0.3` split across two reads. Used by the colonial garrison/invest/assim effectiveness aggregates.

### Modifier breakdown rendering: `GetValueWithBreakdownFor`

The loc-string token `[ROOT.GetCountry.GetModifier.GetValueWithBreakdownFor('country_X_add')]` renders the modifier's value followed by its source-by-source breakdown — "Total: +1.5 (Base values: +1.0, Outlawed Dissent: +0.4, Secret Police: +0.2, Affirmative Action: -0.7)". This works in any tooltip context (progress-bar `desc` strings, scripted-button `desc` keys, JE description fields). Pair with `[ROOT.GetCountry.MakeScope.ScriptValue('name')|=+2]` for derived totals (script values that combine multiple modifiers).

Vanilla precedents: `concept_economy_of_scale_desc_ingame_added` in `concepts_l_english.yml`; `POWER_BLOC_MANDATE_PROGRESS_FROM_GREAT_POWER_MEMBERS_TOOLTIP` in `interfaces_l_english.yml`. Mod precedents: `je_ch_breakdown_*` in `te_journal_entries_l_english.yml`, `je_iw_defense_header`, and the colonial-stability bar / button preview tooltips.

## Country-formation `potential` vs `possible`

Country formation entries support both triggers, with distinct UI semantics:
- `potential = { ... }` — controls whether the formation **appears in the country_formation panel at all**. False → entry is hidden.
- `possible = { ... }` — controls whether the formation can **currently be enacted**. False → entry is shown but greyed-out / unselectable.

Vanilla `ITA` uses both (`potential` excludes c:AUS / c:KUK / c:HRE — those nations don't see Italy as a formable; `possible` checks primary culture for the ones that do). Vanilla `BHT` / `IDN` only declare `possible` (so they always appear, just sometimes greyed out).

Use `potential` when an entry should be entirely irrelevant in some game states (e.g. mod adds a successor major-formation tag that supersedes the vanilla minor formation post-tech, and you don't want a stale greyed entry left in the UI). Use `possible` when the entry is conceptually relevant but momentarily blocked (e.g. need a specific culture, treaty, or law).

The same `potential` vs `possible` / `selectable` / `shown` split appears across many Paradox entity types (decisions, decrees, scripted_buttons, journal_entries) — when an entry is "showing greyed out when it shouldn't even exist for this country", look for the entity's UI-visibility trigger before reaching for tighter enable-checks.

## `on_country_formed` Fires for Formables Too — Don't Use It as an "Independence" Signal

`on_country_formed` (Root = the new country) fires for **any** country formation: vanilla decolonization, formable countries (European Union, Italy, Pan-Africa Union, Greater India), and unification-play resolutions. It is NOT a "newly independent post-colonial country" hook.

For decolonization-only signals, use `on_country_released_as_independent` (Root = Releasing Country, scope:target = Released Country). This fires on voluntary subject release, war-for-independence wins, and engine decolonization — but NOT on formable-country formation. Vanilla itself uses this hook to set `newly_released_country` (90 days, for the Trialist Manifesto JE).

**Bug this rule was learned from:** A `recently_formed_country` variable was set on `on_country_formed` and then read by ~12 decolonization events (Strongman's Promise, Partition Question, Border Disputes, etc.). Forming the European Union mid-game from an already-independent UK set the variable on EUN, and the post-colonial events fired on a stable European democracy. Fix: relocate the setter to `on_country_released_as_independent` scoped to `scope:target`, and rename to `recently_decolonized` to match its real semantics.

**General lesson:** when picking an on-action hook, think about every code path that triggers the underlying engine event, not just the path that motivated the rule. `on_country_formed` is wide; `on_country_released_as_independent` is narrow. Wide hooks misnamed for narrow purposes are a hidden bug factory.

## Global Variable Initialization Timing: Use `on_game_started`

A journal entry's `possible` clause runs on game start (and whenever the engine re-evaluates JE eligibility). If `possible` reads a `global_var:foo` that hasn't been set yet, the engine logs `Value of wrong type in '<file>:<line>'. Got value of type 'none'` and the JE silently fails to appear.

**Pattern that broke `je_global_warming`:**
```
# je_global_warming.txt
possible = {
    temperature_anomaly_display >= 0.1   # script value reads global_var:greenhouse_gas_emissions
}

# extra_on_actions.txt — only initializer
on_yearly_pulse_state = {
    on_actions = { global_warming_update_on_action }   # initializes the var, but only on the first yearly pulse
}
```

At t=0 the global var doesn't exist → `global_var:greenhouse_gas_emissions` evaluates to `none` → the script value chain returns `none` → `none >= 0.1` errors → JE never shows up until the first yearly pulse fires (months in).

**Fix: initialize during `on_game_started` so the var exists before any `possible` clause is evaluated.** Mods may safely add custom on-actions to vanilla's `on_game_started` and `on_game_started_after_lobby` via the `on_actions = { ... }` form (vanilla declares both with placeholder bodies; the engine merges across files):

```
# extra_on_actions.txt
on_game_started = {
    on_actions = {
        te_init_global_state
    }
}

te_init_global_state = {
    effect = {
        if = {
            limit = { NOT = { has_global_variable = greenhouse_gas_emissions } }
            set_global_variable = { name = greenhouse_gas_emissions value = 0 }
        }
    }
}
```

**Do NOT redefine `on_game_started_after_lobby = { effect = { ... } }` directly** — vanilla's `00_code_on_actions.txt` body has substantial logic (Ripper, electoral confidence, great-power list, etc.) that gets clobbered. Always use the `on_actions = { custom_action_name }` extension form, never `effect = { ... }`, on top-level vanilla on-action keys.

**General principle:** if a script value, custom localization, or trigger reads a `global_var:` or `global_variable_list:`, ensure the variable is initialized in `on_game_started` (or earlier than any reader). Don't rely on `on_yearly_pulse_*` or `on_monthly_pulse_*` to be the first writer — JE `possible` clauses evaluate before either.

## Event Targets vs Free-Form Names: Validate Before Use

Like modifiers, **event-target names are looked up in a fixed engine vocabulary**. The engine logs `Unknown trigger type: <name>` and silently skips the entire surrounding block.

Common confusion is naming intuitive-but-wrong identifiers:

| Wrong | Correct | Notes |
|---|---|---|
| `highest_ranked_commander` | `commander` | From `military_formation` scope, walks to its commander character. There is no separate "highest-ranked" target — `commander` already returns the formation's lead character. |
| `military_commander` | `commander_military_formation` | From `character` scope back to the formation. |
| `enemy_commander` | `opposing_commander` | From a character in battle. |

**Validation:** `curl 'http://localhost:8950/engine-docs/event-targets?q=<keyword>'` — returns the vocabulary with input/output scopes for each target. Use this before introducing any new target reference; the engine's silent-failure mode makes typos very expensive to debug.

## Checking the Type of the Law in `on_law_activated`

`on_law_activated` fires with **ROOT = the law instance**, not the country. Inside the on_action effect, `owner` resolves to the country and `type = law_type:law_X` matches the law itself by type:

```
on_law_activated = {
    on_actions = {
        my_law_cascade
    }
}

my_law_cascade = {
    effect = {
        if = {
            limit = {
                type = law_type:law_command_economy
                owner = { NOT = { has_law = law_type:law_state_owned_banking } }
            }
            owner = { activate_law = law_type:law_state_owned_banking }
        }
    }
}
```

Vanilla precedent: `00_ip4_victoria_scripted_triggers.txt` uses `scope:law.type = law_type:law_X` for the same comparison from a country scope (where the law is in a saved scope variable). Inside `on_law_activated` the law IS root, so `type = law_type:X` works directly.

**Repo example:** `banking_law_cascade_on_law_activated` in `common/on_actions/extra_on_actions.txt` — auto-enacts `law_state_owned_banking` when `law_command_economy` activates.

## `create_dynamic_country.on_created`: Save Parent Scope BEFORE the Call

Inside `on_created`, the scope is the new country and **the original creator country is not directly accessible** — `owner` of any state passed in is now the new country (the cede happened as part of the create). To reference the parent (e.g. to apply path-dependent legacy modifiers, set initial diplomatic relations, or read parent variables), `save_scope_as = X` on the parent **before** the create_dynamic_country block:

```
form_decolonized_country = {
    save_scope_as = new_country_capital
    owner = { save_scope_as = decolonizing_parent }   # save BEFORE create

    create_dynamic_country = {
        ...
        on_created = {
            ...
            scope:decolonizing_parent = {
                change_relations = { country = ROOT value = -50 }
            }
        }
    }
}
```

**Repo example:** `apply_decolonization_path` + `form_decolonized_country` in `common/scripted_effects/decolonization.txt` — reads `scope:decolonizing_parent.var:colonial_garrison_months` etc. inside the new country's `on_created` to apply the right legacy modifier.

## Path-Dependent JE Resolution Pattern

To make a journal entry's `on_complete` / `on_fail` event branch by which policy the player leaned on, **count months active** in country variables in the JE's `on_monthly_pulse`, then dispatch in the resolution effect. Country vars survive across the entire JE lifetime (whereas `has_modifier` only sees the current frame).

```
on_monthly_pulse = {
    effect = {
        if = { limit = { NOT = { has_variable = colonial_invest_months } }
               set_variable = { name = colonial_invest_months value = 0 } }
        if = { limit = { has_modifier = colonial_development_investment_modifier }
               change_variable = { name = colonial_invest_months add = 1 } }
        # ... repeat per policy
    }
}

on_complete = {
    if = { limit = { var:colonial_garrison_months > 24
                     var:colonial_garrison_months >= var:colonial_invest_months }
           trigger_event = { id = decolonization_events.203 } }   # Iron Fist
    else_if = { ... }                                              # Commonwealth, etc.
    else = { trigger_event = { id = decolonization_events.200 } } # generic
}
```

**Repo example:** `je_colonial_empire` in `common/journal_entries/je_colonial_empire.txt` dispatches across 5 resolution events (200/202/203/204/205) based on policy-time counters.

## Per-State-Limit-1 Buildings: `NOT has_building` AI Clauses Are Noise

If a building has `has_max_level = yes` and `levels_per_mesh = -1` (single-level, single-instance per state), then a clause like:

```
if = {
    limit = { NOT = { has_building = building_X } }
    add = N
}
```

inside its `ai_value` **always fires when construction is being evaluated** — because the building can only be evaluated for construction when it doesn't already exist in the state. The clause becomes always-true noise rather than a real conditional.

For per-state-limit-1 buildings, drop the `NOT has_building` clause; use law / JE / tech context to differentiate priority instead. For multi-level buildings (where additional levels can stack), `NOT has_building` IS meaningful (it distinguishes "build the first one" from "expand existing").

**Building `ai_value` evaluates in *state* scope, not country.** ROOT = the state under evaluation; `owner` traverses to the state's country (the AI considering construction). Triggers that require a country target (e.g. `has_diplomatic_relevance = X`) need `root.owner`, not `ROOT`. Symptom of getting this wrong: `Wrong target scope for <trigger>, must be country`. Vanilla buildings rarely need this since they use scalar `ai_value`, but mod ai_value blocks frequently do — match vanilla scripted-trigger patterns (`scope:target_state.owner` style) when adapting.

## Concept Link Localization Syntax

Two forms work for hyperlinking concepts in tooltip / modifier descriptions:

| Form | When to use |
|---|---|
| `[concept_X]` | Plain hyperlink that displays the concept's own loc name (e.g. `[concept_authority]` displays "Authority"). |
| `[Concept('concept_X', '$display_text$')]` | Hyperlink with a custom display text — useful when the surrounding sentence needs a different word (e.g. plural form, possessive). |

**Repo example:** `country_legislative_override_capacity_add` in `te_modifiers_l_english.yml` uses the second form for the modifier name itself: `"[Concept('concept_legislative_override_capacity','Legislative Override Capacity')]"`.

Vanilla concept names like `concept_interest_group`, `concept_authority`, `concept_country` are always available — no need to redefine. Only define new concepts in `common/game_concepts/` when introducing genuinely new gameplay terminology.

**A new concept needs three things:** (1) a registration entry in `common/game_concepts/extra_concepts.txt` (e.g. `concept_un_veto = {}`), (2) a `concept_X:0 "Display Name"` localization key, and (3) a `concept_X_desc:0 "Tooltip body"` key. Skip step 1 and `organize_loc.py` will flag the loc keys as **UNUSED** and bucket them into `te_unused_l_english.yml` — even if other loc descriptions reference them via `[concept_X]`. The reason: `find_used_keys_explicitly` (in `organize_loc.py`) only scans non-localization files for token usage, and its transitive-closure regex catches `$X$` / `@X!` / `[X.GetY]` style references but **not** plain `[concept_X]` brackets inside loc values. The `extra_concepts.txt` registration is the only way to mark the concept as used.

**Skipping step 1 also produces high-volume runtime log spam.** When the engine renders a loc string containing `[concept_X]` and `concept_X` isn't registered, it falls back to treating the bracket expression as a data-system function call and logs `Could not find data system function 'concept_X'` + `Failed converting statement for 'concept_X'` + `Data error in loc string '<the parent loc key>'` — once per render. Hovering or repainting the offending UI fires hundreds of debug.log lines in seconds and stalls the game (same class of synchronous-log-spam lag as `[b]X[/b]` markdown). The errors don't appear in `loc_coverage_audit` (which only checks loc keys for entities) and they don't appear in `/logs/debug` under the default `mod_only=true` filter — they originate in `pdx_data_factory.cpp` / `pdx_data_localize.cpp`, vanilla source, with no mod path attached. To find them, drop the filters: `curl -s "http://localhost:8950/logs/debug?summary=true&mod_only=false&vanilla_bugs=show&mod_noise=show"` and look for `Could not find data system function 'concept_*'` in `top_repeats`.

## Defined-But-Unused Modifiers

A static modifier definition in `common/static_modifiers/` is dead code unless it appears in at least one `add_modifier`, `add_static_modifier`, or `name = X` reference somewhere. The mod's `colonial_empire_solidified_modifier` was defined but never applied (the JE's monthly pulse only added `_under_pressure` and `_crumbling`) — easy to miss.

**Audit:** `grep -rln "name = my_modifier_name" common/ events/` should produce at least one hit per defined static modifier. Zero hits means the modifier exists in name only.

## Vanilla Ship Slot Mods Are Referenced by Parent Type

Vanilla ship modifications like `ship_mod_destroyer_armor_light/medium/high`, `ship_mod_aircraft_carrier_*`, `ship_mod_super_dreadnought_*` are keyed by **parent ship type**, not by the modded ship type. When a mod ship reuses a parent's `modifications` block, it gets the parent's mods verbatim — including their thematic mismatch (a 2010-era arsenal ship using "super dreadnought guns") and their construction goods (which scale with the parent's economy, not the modern ship's).

To give a mod ship its own slot mods:

1. Create new mods in `common/ship_modifications/` keyed by the mod ship type — e.g. `ship_mod_arsenal_ship_armor_light`.
2. Mirror the vanilla parent's modifier values to preserve combat balance (or retune deliberately).
3. Scale construction goods proportionally to the modern ship's base cost — don't inherit vanilla's 19th-century goods totals.
4. Update the ship's `modifications = { ... }` block to point at the new IDs.

**Repo example:** `common/ship_modifications/extra_ship_modifications.txt` — 108 mods across 9 modern ships, with construction goods scaled 2×–4× over vanilla parent values.

## `ship_visibility_add` Doesn't Clamp ≥ 0 — Per-Modification Negatives Are a Mod-Only Pattern

Vic3 reads `ship_visibility` straight into the detection-vs-visibility ratio used by fleet spotting (`common/script_values/command_values.txt`) and AI mission scoring (`common/defines/00_ai.txt`). The engine does **not** clamp it to ≥ 0. A negative final visibility silently inverts the ratio, so a "stealthy" sub becomes more visible than a capital and the AI's spot/raid scoring goes upside-down. `/validate/engine-coverage` does NOT catch this — every modifier name is registered, the bug is in the *value*.

Vanilla never gives a `ship_visibility_add` a negative value. All vanilla stealth comes through `ship_visibility_mult` on missions (`piracy = -0.5`, `raid_supply = -0.25`), traits (`convoy_raider_*` = -0.1, mutually exclusive via `replace = { ... }`), and tech. Vanilla's lowest base is `5` (submarine / frigate / torpedo boat).

The mod's per-modification stealth tiers (e.g. `ship_mod_*_armor_high`, `ship_mod_*_propulsion_high`) use **negative `ship_visibility_add`**, which is a mod-only deviation. That's fine on its own, but the invariant to maintain is:

> `base_ship_visibility_add + sum(worst-case modification adds) > 0`

Otherwise the multiplicative stack on top makes the negative value *more* extreme in detection math, not less. The bug we fixed: three subs at base `1` with two `-2` mod tiers each → `1 - 2 - 2 = -3`. Fix was raising base + shrinking mod magnitudes so the worst case bottoms at `+1`.

**Audit when adding a stealth modification:** for every ship that can equip the mod, check `base + (sum of largest negative adds across its slots) ≥ 1`. Don't size the floor at `0` exactly — vanilla mult stacks (~ -0.8 worst case for submarines on piracy) will still pull down from there.

## Scripted Button Gating: `visible` Hides, `possible` Greys Out

`scripted_button` has two gating fields with very different UX behavior:

- **`visible = { ... }`** — when any clause is false, the button **disappears entirely**. The player has no way to discover the button exists or learn what they need to do to unlock it.
- **`possible = { custom_tooltip = { text = X ... } ... }`** — when wrapped in a `custom_tooltip`, a failing clause keeps the button **visible but greyed out**. Hovering shows the tooltip text explaining why it's disabled.

**Default to `possible` for player-facing prerequisites.** Reserve `visible` for "this button is contextually meaningless right now" — e.g. a "decrease funding" button when funding is already 0, or a "disable program X" button when X isn't active. Use `possible` for "you need to unlock something" — laws, techs, institutions, modifiers.

Pattern:

```
visible = {
    has_journal_entry = je_X
    NOT = { je:je_X = { has_modifier = some_program_active } }   # contextual
}
possible = {
    custom_tooltip = {
        text = REQUIRES_LAW_TT
        has_law = law_type:law_ministry_of_culture
    }
    custom_tooltip = {
        text = REQUIRES_TECH_TT
        has_technology_researched = mass_media
    }
}
```

Each `custom_tooltip { text = ... <triggers> }` block fails as a unit — if the inner triggers are false, the tooltip text shows. Stacking multiple `custom_tooltip` blocks in `possible` produces stacked failure-reason lines, which is the right UX for "explain every missing prereq."

**Repo example:** `common/scripted_buttons/cultural_hegemony_buttons.txt` — the 5 enable buttons (increase funding, world expo, cultural institutes, global media, protectionism) keep their `has_law` and `has_technology_researched` gates in `possible` with `CH_REQUIRES_MINISTRY_TT` / `CH_REQUIRES_MASS_MEDIA_TT` tooltips. They stay visible-but-greyed when the player lacks the law or tech, so the JE always shows the player what's available rather than a blank panel.

## Triggered Option Names: `name = { trigger=... text=... }`

Event option labels can be conditional on context. Repeat the `name` field with each variant gated by a `trigger`; first match wins. No `else` / fallback syntax — use `trigger = { always = yes }` as the catch-all.

```
option = {
    name = {
        trigger = { scope:un_vote_target ?= this }
        text = un_vote.1.a_target
    }
    name = {
        trigger = { always = yes }
        text = un_vote.1.a
    }
    default_option = yes
    ...
}
```

The `?=` operator is exists-aware: `scope:foo ?= this` returns false if `scope:foo` doesn't exist, true if it exists and equals `this`. This lets the same option block work across event topics that don't all set the same saved scope.

**Vanilla example:** `iberia_events/carlist_war_events.txt` carlist_war.1 — uses the pattern with `c:SPA ?= this` and `c:SPC ?= this`. Hard to find by grep because almost no other vanilla event uses it; remember the file path.

**Repo example:** `events/un_vote_events.txt` un_vote.1 options A and B — target-perspective labels keyed off `scope:un_vote_target ?= this`.

## Orphan Tech Gates: When a JE's `possible` Moves, Its Buttons & Diplo Actions Don't Follow

When a journal entry's activation gate (`possible`) is rewritten to use a different signal, every gate downstream — `scripted_button` `visible` clauses, `diplomatic_action` `potential` clauses, AI logic guards inside the JE's own `on_monthly_pulse` — keeps the *old* gate. The engine never warns about this; the JE simply activates and exposes a panel where every interactive control is silently filtered out.

**Repo example:** `je_covert_warfare`'s `possible` was originally `has_technology_researched = television`. It was rewritten in two steps to `covert_operation_max_slots >= <rank-baseline + 1>`. The two funding `scripted_button`s, all 9 `covert_*_action` diplomatic actions, and the AI funding-management `if = { limit = { is_player = no has_technology_researched = television } }` block kept the orphan gate. Result: a country that researches `mainframe_computers` (era 7, the first slot-granting tech, with a prereq chain that does not pass through `television`) gets the JE active with all funding buttons hidden, all diplomatic actions invisible, and the AI funding logic skipped.

**Audit recipe** — when changing a JE's `possible`, grep the whole system for the old gate:

```bash
grep -rn 'has_technology_researched = <old_tech>' \
    common/scripted_buttons/<system>*.txt \
    common/diplomatic_actions/<system>*.txt \
    common/journal_entries/je_<system>.txt \
    common/scripted_effects/<system>*.txt \
    events/<system>_events.txt
```

Either drop the now-redundant gate (preferred — the JE's `possible` becomes the single source of truth) or update each downstream clause to the new gate. Comments referring to the old gate ("Base (television): cap is 1") are also stale and should be fixed.

## A Good's Effective Era Lives in Its Production Chain

Goods can be defined without an `unlock_goods` block (in `common/goods/` or via tech `unlock_goods = { X }`). It's tempting to read "no `unlock_goods`" as "always available" — but the good is still effectively era-gated by the *PMs that produce it*. If the earliest PM with `goods_output_X_add` is locked behind an era-7 tech, then `X` is *de facto* an era-7 good even though the goods file is silent.

**Repo example:** `electronic_components` (defined in `common/goods/timeline_extended_extra_goods.txt` with no tech gate) is *de facto* era-7 because its only producing PMs (`pm_transistors`, `pm_integrated_circuits`, the company-flavor PMs in `unique_pms.txt`) are gated by era-7+ techs. An era-6 ship modification asking for it is a mismatch even though the goods file shows no formal restriction.

**Audit recipe** — to find a good's effective era:

```bash
# 1. Find every PM that outputs the good
awk '/^pm_|^REPLACE:pm_|^INJECT:pm_/{cur=$0} /goods_output_X_add/{print cur}' common/production_methods/*.txt | sort -u

# 2. For each candidate PM, look up its unlocking_technologies block
# 3. The earliest tech's era is the good's effective era
```

This matters when auditing era-appropriateness of goods *consumption* — ship modifications, building inputs, military unit costs.

## `show_as_tooltip = { ... }` — Render Effect Tooltip Without Executing

Engine pattern: wrap effects in `show_as_tooltip = { ... }` and the engine renders the auto-generated tooltip (modifier name + every field, relation changes, etc.) but does **not** execute the effects. Use it wherever the player needs to see "if you do X, here's what you'll get" before committing — vote previews, button hovers that forecast a downstream resolution, decision-stage forecasts of effects that fire later.

Repo example: `events/un_vote_events.txt` `un_vote.1` option A wraps a per-topic `if = { limit = { has_global_variable = un_vote_topic_X } add_modifier = { name = ... } }` switch in `show_as_tooltip` so voters see the treaty modifier they would receive if the resolution passes — the actual `add_modifier` runs later in `un_vote.3` option A, not at vote-cast time.

Don't pair `show_as_tooltip = { add_modifier = X }` with a separate scripted-effect call that *also* adds X — the engine tooltip will list the modifier twice. Either preview-only (the real apply is elsewhere) or apply-only (no wrapper needed). When you need both visibility and execution at the same site, just write `add_modifier` directly at the option level — the engine auto-tooltips it.

## Multi-Stage Event Flows: `add_modifier` Visibility Across Audience Splits

Systems built as event chains (propose → ballot → result-for-proposer → notify-other-members) split the audience across stages — each stage's events fire for a different country set. A modifier added inside stage N is invisible to anyone whose audience is stage M. When a player reports "this modifier is applied invisibly," the diagnosis usually comes from one of:

1. **Wrong-stage application.** The `add_modifier` lives in a stage the player never reaches. Example: the proposer never sees `un_vote.3` (it explicitly excludes `THIS = ROOT`), so any modifier applied only there will never reach the proposer; the proposer's modifier needs to live in the proposing event (`un_events.X` option A) or `un_vote.2`.
2. **Buried under scripted-effect indirection.** `add_modifier` inside a scripted effect inside an `if = { limit }` inside an option block is *technically* auto-tooltipped, but rendered deeply enough that players miss it. Hoist the `add_modifier` directly into the option block when the visibility matters. Keep the scripted effect for *residual* logic (infamy, leverage, contributor pledges) where individual line visibility is less critical.
3. **`hidden_effect = { ... }` blocks.** Anything wrapped here is suppressed from the option tooltip entirely. Reserve for genuine bookkeeping (variable cleanup, every_country fan-out) — never for the modifier the player most cares about.

When designing a multi-stage flow, name the audiences explicitly ("proposer", "yes-voter", "no-voter who accepts", "no-voter who refuses") and trace which stage's options each audience sees. A modifier needs to live where the audience that should perceive it actually has an option to click.

## Tooltip Auto-Rendering: What the Engine Renders, What It Doesn't

The engine auto-generates tooltip text for some effect-block contents and stays silent on others. Knowing which is which determines whether you can rely on engine-native rendering or need to author / auto-generate the tooltip text yourself.

**Auto-rendered (visible without `custom_tooltip`):**
- `add_modifier = { ... }` — name + every field with formatted values + duration/decay.
- `remove_modifier = X` — modifier name with effect inversion.
- Most relation/event-target effects with built-in tooltip strings (e.g. `change_relations`, `add_treasury`, `change_infamy`).

**Silent (no auto-tooltip):**
- `change_variable`, `set_variable`, `change_global_variable`, `set_global_variable` — variable changes don't surface to the player at all. Critical for systems that track state in vars (e.g. `un_authority`, banking-cycle counters): the player won't see the delta unless you author it.
- `trigger_event` — the chained event isn't previewed.
- Scope iterators (`every_country`, `every_scope_state`, etc.) — the inner block's effects don't bubble up.
- Anything inside `hidden_effect = { ... }` (intentional).

**Antipattern**: wrapping the entire effect block in `custom_tooltip = { text = "X_DESC" ... add_modifier = ... change_variable = ... }`. The text replaces the auto-render entirely — so the modifier values that *would* have rendered automatically are now hand-typed in `X_DESC`, and they drift from the modifier definitions over time. The mod's `un_buttons.txt` had this for years before the autogen rewrite.

**The two clean fixes:**

1. **Engine-native + visible variable lines**: leave `add_modifier`/`remove_modifier` outside any `custom_tooltip` so the engine renders them with current values; wrap the variable-change line(s) in a small `custom_tooltip = { text = X }` so the player still sees them. Wrap implementation details (`set_global_variable`, `trigger_event`, `every_country` fan-out) in `hidden_effect`. Best when there's exactly one or two variable changes worth surfacing.

2. **Loc-splice autogen pattern**: hand-write a narrative `*_DESC` key with `$..._EFFECTS$` substitution mid-string; have a Python generator emit the `*_EFFECTS` keys from button-source + modifier-definition introspection. The engine resolves `$X$` at display time, so numbers stay synced without relying on engine auto-render. Best when the existing tooltip layout consolidates many effects (modifier values + multiple variable changes + qualifiers) and you want to preserve that layout.

**Repo examples:**
- `gen_un_button_descs.py` — the loc-splice pattern. Walks each in-scope UN button's effect block to collect `add_modifier`/`remove_modifier` calls and `change_variable un_authority` deltas, looks up modifier values in `extra_modifiers.txt`, emits `UN_*_EFFECTS` loc keys. The hand-written `UN_*_DESC` keys reference `$..._EFFECTS$` to splice the auto-generated mechanical text into the narrative preamble.
- `gen_pb_principle_unlock_descs.py` — sibling generator for `country_*_pb_principles_bool_desc` keys. Same parse-source-and-emit-loc shape.

## `organize_loc.py` Will Reroute Auto-Gen Loc Files Without a Categorize Rule

A new generator that writes its own `te_<topic>_l_english.yml` file will *appear to work* — the file is there after the generator runs — but the next `organize_loc.py` invocation (post-load, every full `/reload`) sweeps the keys back into `te_miscellaneous_l_english.yml` based on `categorize_key`'s prefix rules, leaving the dedicated file empty.

**The fix is two lines in `organize_loc.py`:**

```python
# Add to the CATEGORIES list (controls output filename via `te_{cat.lower()}_l_english.yml`)
"UN_BUTTON_EFFECTS",

# Add to categorize_key (matches before the broad fallback rules)
if key.startswith("UN_") and key.endswith("_EFFECTS"):
    return "UN_BUTTON_EFFECTS"
```

**Existing examples** in the same file:
- `POWER_BLOC_UNLOCKS` rule routes `*_pb_principles_bool` and `*_pb_principles_bool_desc` to `te_power_bloc_unlocks_l_english.yml` (owned by `gen_pb_principle_unlock_descs.py`).
- `UN_BUTTON_EFFECTS` rule routes `UN_*_EFFECTS` to `te_un_button_effects_l_english.yml` (owned by `gen_un_button_descs.py`).

Always pair a new generator that owns its own loc file with a `categorize_key` rule. Trying to debug "my generator wrote keys but they're showing up in te_miscellaneous" is faster if you know to look here first.

## Engine-Convention Loc Keys Land in `te_unused_l_english.yml` (and That's Fine)

Many engine UI strings are looked up by convention — `<entity>_name`, `<entity>_icon`, `<modifier>_desc`, etc. — without ever appearing in script. `organize_loc.py`'s categorizer can't see those lookups (it grep-scans `common/`, `events/`, `gui/`, etc. for *script* references) so it tags the keys as unused and routes them to `te_unused_l_english.yml`.

The keys still resolve at runtime: **all `te_*_l_english.yml` files in `localization/english/` are loaded by the engine, regardless of filename pattern.** `te_unused` is *only* a sorting destination from the script's perspective; the engine sees no difference between it and `te_concepts_l_english.yml`.

**Don't try to "fix" this** by renaming the file, registering the keys, or adding a fake script reference. The placement is benign. If the categorizer's misclassification is itself confusing — e.g. a code reviewer flags "why are the political_lobby `_name` keys in te_unused?" — leave a comment on the keys or call it out in the relevant design doc rather than relocating them.

Caveat: if `organize_loc.py` ever changes to *delete* unused keys instead of relocating them, this convention breaks. Today (2026-05) it relocates, and there's no plan to change that. If the runbook for `organize_loc.py` gains a deletion mode in the future, engine-convention keys need an explicit script reference (e.g. a comment block with `# referenced-by-engine: lobby_<id>_name` that the categorizer learns to recognize, similar to the existing `POWER_BLOC_UNLOCKS` / `UN_BUTTON_EFFECTS` rules).

## Vanilla Script-Value Overrides Are the Bridge Between `script_only` Modifiers and Engine Hardcoded Values

When a vanilla `common/script_values/*.txt` script value is referenced from engine hardcoded paths (diplomatic action `possible` blocks, treaty article gates, ai_chance evaluators, etc.), redefining that script value in `common/script_values/extra_script_values.txt` is the supported way to modify the underlying gameplay number — the mod's later-loaded definition replaces vanilla's at game load (script values do not get the `Duplicated key X will not be created` treatment that entity types do).

**Useful pattern**: combine a `script_only = yes` modifier with a vanilla script-value override that reads it.

```
# common/modifier_type_definitions/mod_entity_modifier_types.txt
country_leverage_threshold_change_add = {
    color = bad
    percent = no
    script_only = yes
}

# common/script_values/extra_script_values.txt — overrides vanilla's literal `= 200`
leverage_threshold_to_invite = {
    value = 200
    power_bloc_leader = { add = modifier:country_leverage_threshold_change_add }
}
```

Tech / law / decree / institution `modifier = { country_leverage_threshold_change_add = -100 }` blocks contribute additively, the override sums them via `modifier:X`, the engine reads the result wherever it consumed the original literal. Tooltips on the contributors auto-render the modifier line.

**Failure mode**: the modifier definition + tech contributions are easy to write and look correct, but if the script-value override is missing (or accidentally deleted in a refactor), the contributions are summed into a value that no one reads. No log signal — the modifier appears in tooltips, the techs appear to apply it, but the gameplay number stays at the vanilla literal.

**Repo example: `country_leverage_threshold_change_add`**. This pattern was working until commit `5e83824` (April 7, 2026) deleted the `leverage_threshold_to_invite` script-value override from `extra_script_values.txt` as part of an unrelated covert-ops refactor. The modifier definition + tech contributions stayed in place, so the symptoms looked like "leverage threshold reduction broken" but no error was logged. Restored 2026-05-03 with the simpler `add = modifier:X` form (the deleted version had hardcoded per-tech `subtract` blocks).

**Audit recipe** when a `script_only = yes` modifier looks broken: search `common/script_values/` (mod *and* vanilla) for the consumer. If the consumer is a vanilla script value, confirm the mod has an override redefining it. If the consumer is gone, restore it. If neither has a consumer, the modifier is genuinely unread and the tech contributions are dead code.

## New `.txt` Files Under `common/` Need a UTF-8 BOM

Vic3 expects every brace-script file under `common/` (and `events/`) to start with a UTF-8 BOM (`EF BB BF`). The engine logs `File 'X' should be in utf8-bom encoding (will try to use it anyways)` for files without one. The warning is non-fatal — the engine parses the file regardless — but it adds noise to `debug.log` and (anecdotally) makes some tooling treat the file as ASCII when it shouldn't.

The `Write` tool writes plain UTF-8 by default, so any new file created via Write/Edit lacks a BOM until you add one. Existing files modified by Edit keep their BOM (the BOM bytes survive surgical edits). The fix:

```bash
for f in common/path/to/new_file.txt; do
    tmp="${f}.tmp"
    printf '\xef\xbb\xbf' > "$tmp"
    cat "$f" >> "$tmp"
    mv "$tmp" "$f"
done
```

Verify with `head -c 3 file.txt | xxd -p` — should print `efbbbf`. After adding, `POST /reload` to refresh the server's view; the `should be in utf8-bom encoding` line should no longer appear in `/logs/debug` for that path.

Locale YAMLs use a different convention — the `*_l_english.yml` files use `\xef\xbb\xbf` BOM as well but `organize_loc.py` re-emits them, so don't hand-bom yaml files.

**Migration scripts that split or concatenate `.txt` files must strip embedded BOMs.** When you parse a BOM-prefixed source and write its content into a new file with a fresh header, the BOM travels with the first body byte and lands hundreds of lines into the destination — non-standard, and inside the file the engine treats it as a stray character. Fix in Python:

```python
data = src_path.read_bytes()
bom = b'\xef\xbb\xbf'
had_leading = data.startswith(bom)
cleaned = data.replace(bom, b'')
if had_leading:
    cleaned = bom + cleaned    # keep one BOM at byte 0 only
dst_path.write_bytes(cleaned)
```

Verify post-write with `python3 -c "data=open(p,'rb').read(); ...; positions=[]; ..."` (find every BOM and check the only position is 0). The engine *will* load files with mid-content BOMs and `POST /reload` won't error, so this gotcha hides — explicitly scan for it.

## Formables: `geographic_region = X` Reads `state_regions = {...}` Only

A formable's `geographic_region = X` field expands `X.state_regions = {...}` to compute the required-states list. It **silently ignores** `X.strategic_regions = {...}` in this code path — the same field works fine for `is_in_geographic_region = X` triggers, which is a different code path that DOES expand strategic regions. So a geographic_region defined like this:

```
geographic_region_europe = {
    strategic_regions = { sr:region_western_europe sr:region_southern_europe ... }  # for triggers
}
```

works for `is_in_geographic_region = geographic_region_europe` but produces an empty/unusable required-states list when used as `EUN = { geographic_region = geographic_region_europe }`. Vanilla never makes that mistake — every formable that uses `geographic_region = X` in `00_major_formables.txt` (`GER`, `SCA`, `YUG`, the Andean federation) points at a region defined with `state_regions = {...}` (e.g. `geographic_region_scandinavia` is a flat `state_regions = { STATE_JUTLAND ... }` list).

**Symptom**: the formable's UI either lists no required states or seems to enumerate the wrong scope; specific states the user expects to see are absent. No log signal — the engine doesn't error on the mismatched shape; it just doesn't expand the strategic regions block.

**Fix**: define a mod-side region with `state_regions = {...}`. The mod uses `scripts/generators/gen_formable_regions.py` to expand vanilla `strategic_regions = {...}` to explicit state lists for the EUN/AFU/UNA/UNE formables, writing `common/geographic_regions/te_formable_regions_generated.txt`. Run the generator after vanilla strategic-region rebalances (it fails loudly if a configured region disappears).

A geographic_region can carry both blocks — vanilla `geographic_region_subsaharan_africa` uses both `strategic_regions = {...}` (for triggers) and `state_regions = {...}` (extending the trigger's reach by a few extra states) — but each block only feeds its own code path.

## Domestic Political Lobbies (`category = foreign`) Cannot Be Seeded From History (1.13.2)

Vanilla supports three political-lobby categories per `common/political_lobbies/political_lobbies.md`: `foreign_pro_country`, `foreign_anti_country`, and `foreign` (the domestic category, where `scope:target_country` auto-resolves to `scope:country`). Vanilla ships no domestic-lobby type definitions and no domestic-lobby history seed — every entry in `common/history/lobbies/00_lobbies.txt` is foreign-category targeting another country.

A `category = foreign` lobby type with sane `can_create` / `on_created` / `requirement_to_maintain` / `available_for_interest_group` clauses **parses cleanly and loads with no log errors**. The engine's lobby UI and runtime systems appear to accept it. But seeding one via `create_political_lobby` from `common/history/lobbies/<file>.txt` — even the simplest possible form (one IG, `target = c:<self>`, no formation_reason) — crashes the game on new-game start. Load-from-save is unaffected because history files don't execute on save load.

The crash does not produce a `script_parse_error`, `inject_to_missing`, or fatal-assertion log line. `debug.log` shows only the standard load-sequence entries plus a benign `should be in utf8-bom encoding` notice for the seed file. The engine appears to terminate inside the C++ political-lobby creation path before any script-side diagnostic is flushed.

**Practical rules until this is understood:**
- Don't add domestic-lobby (`category = foreign`) entries to `common/history/lobbies/`. The lobby type definitions themselves are fine; only the history seed path is broken.
- If a domestic lobby needs to exist at game start, the only confirmed-safe path is the engine's automatic catalyst-driven formation. That's sparse — formation depends on diplomatic catalysts matching one of the lobby's `formation_reasons`, which can take in-game years for a given country.
- For any new lobby work involving domestic categories, sequence as: type definitions only first, verify new-game starts cleanly, then add appeasement factors / scripted effects, verify again, then add event hooks, verify again, *then* attempt history seeding (which is where the crash gates).
- This applies to 1.13.2 (release/1.13.2 : f5b9199e5). Re-test after vanilla bumps — Paradox may fix the assertion in a later patch and remove this restriction.

The full forensic record of one domestic-lobby crash, including ruled-out hypotheses and a staged re-implementation plan, is preserved in `docs/archive/political_lobbies_design.md` § Re-implementation Notes.

## Engine Vocabulary That Doesn't Exist — Verify Before Designing

Several plausible-sounding names turn up empty when you go to use them. Discovered the hard way during the colonial-empire redesign; recording so the next pass doesn't re-walk the same diff.

**No `complete_journal_entry` effect.** The vanilla way to programmatically end a JE is the `complete` block + variable pattern: a decision sets `set_variable = my_je_done`, and the JE's `complete` block reads `OR = { <existing condition> ; has_variable = my_je_done }`. The `on_complete` block can branch on the variable to fire a path-specific event. Used in `je_colonial_empire` for the Imperial Federation Act capstone (decision sets `imperial_federation_taken` + `imperial_federation_iron_fist|civilizing` variables; JE routes to events 300/301 by variable).

**Vic3 has no EU4/CK3-style flags.** `set_country_flag` / `has_country_flag` / `clr_country_flag` / `set_global_flag` / `has_global_flag` do not exist in Vic3 — they parse-error silently into "Unknown effect" / "Unknown trigger" cascades, and downstream effects in the same block get mis-attributed as unknown. Use `set_variable = NAME` (bare form sets to "yes") and `has_variable = NAME` (or `var:NAME`) instead. Vanilla pattern: `set_variable = brazil_spurned_heir` / `has_variable = brazil_spurned_heir`. Globals: `set_global_variable` / `has_global_variable` / `global_var:NAME`.

**No `available` block on `scripted_buttons`.** Buttons gate on `possible` only. To express "AI without enough authority can't fire this," put the cost check directly inside `possible` (e.g. `authority > 300`). The engine greys out the button uniformly for AI and player when `possible` fails.

**No `country_minimum_expected_sol_add` modifier.** The closest vanilla equivalents are `state_lower_strata_expected_sol_add` and `state_middle_strata_expected_sol_add` (state-scoped). They DO propagate through country modifiers — applying them in a country-level static modifier raises expected SoL across all owned states. Used in `colonial_development_investment_modifier` for the "why aren't you investing here?" domestic-anger cost.

**No `law_multiparty_voting`.** Multiparty politics is a function of Distribution of Power (`law_universal_suffrage` / `law_census_voting` / `law_wealth_voting`) plus Free Speech laws plus governance principles, not a single law. When designing law-gated decisions, use the broad-franchise DP options as the "multiparty" proxy.

**Law IDs vs display names.** `docs/engine/laws.txt` (auto-generated, lists display names) and `common/laws/<file>.txt` (vanilla source, lists law IDs) don't match 1:1. Common ID surprises:
- "Multiculturalism" → `law_multicultural`
- "Landed Voting" → `law_landed_voting` (not `_voters`)
- "Wealth Voting" → `law_wealth_voting` (not `_voters`)
- "Racialized Citizenship" → `law_racial_segregation`
- "Cultural Citizenship" → `law_cultural_exclusion`
- "Sovereign Subjecthood" → `law_subjecthood`

Always grep `common/laws/` for the actual ID before writing `has_law = law_type:law_X` triggers.

**Power bloc identity is creation-only.** No `change_power_bloc_identity` / `set_power_bloc_identity` / `change_identity` / `set_identity` effect exists; `identity = ...` only works inside `create_power_bloc { ... }`. Vanilla never flips identity mid-game (the only `identity =` outside creation is in `events/iberia_events/ip4_lusosphere_events.txt`, also inside `create_power_bloc`). **No scripted dissolution either** — `dissolve_power_bloc` / `destroy_power_bloc` / `disband_power_bloc` / `remove_power_bloc` all return not-found in `/engine-docs/origin/...`. Designs that want a Zollverein → German Empire identity flip on country formation need to be reframed (a passive cohesion modifier or narrative JE, not an actual identity change).

**Power bloc mandate count is read-only and not numeric in script values.** No `add_mandate` / `remove_mandate` / `add_power_bloc_mandate` / `unlock_principle` effect exists — mandate consumption is hardcoded into the principle-unlock click flow and can't be intercepted. `num_mandates` is a real numeric **trigger comparator** (vanilla `00_alert_types.txt:994` uses `num_mandates > 0`; `trigger_localization` registers the full `_greater_than` / `_less_than` / `_equal` family) so it works inside `limit = { num_mandates >= X }`, but there is no script-value accessor that returns the count for `multiplier = ...` or `value = ...`. To scale a modifier on mandate count, build a tiered script value with `if`/`else_if` rungs (see `sv_te_unused_mandate_cohesion_tier` + `sm_te_unused_mandate_reserve` for the pattern). Also: there is no `on_yearly_pulse_power_bloc` on-action — apply via `on_yearly_pulse_country` gated on `is_power_bloc_leader = yes` and scope into `power_bloc = { ... }`. Verified against vanilla 1.13.

## `add_treasury` Accepts Script Values for GDP-Scaled Drains

`add_treasury = colonial_invest_monthly_cost` works (script value, scope is country, evaluates `gdp * -0.005` per pulse — note plain `gdp`, not `country_gdp`; the latter is not a script value and silently produces "Badly read script value" errors). Used in `je_colonial_empire` on_monthly_pulse for the Investment policy's GDP-scaled cost. Pattern works for any "cost is X% of GDP per month" drain — modifiers can't express this directly (no `country_weekly_treasury_add`-style modifier), but a JE pulse + script value can.

## Capstone Decisions That Complete a JE

Pattern for "victory condition" decisions that end a JE permanently:

1. Track sustained-state duration in a JE variable (e.g., `colonial_solidified_months` increments while bar ≥ 90, resets if it drops). Read in the decision's `possible` to require N months of sustained achievement.
2. The decision's `when_taken` sets a country variable and applies a permanent modifier.
3. The JE's `complete` trigger reads the variable (`has_variable = X`).
4. The JE's `on_complete` branches by variable to fire a path-flavored victory event.

The variable persists across saves and the modifier applied in `when_taken` is permanent (`days = -1`). The bar/buttons disappear when the JE completes.

Vanilla precedents: Greek "King Otto" / Italy Risorgimento capstones use the same shape. Repo example: `imperial_federation_act_iron_fist` / `imperial_federation_act_civilizing_mission` decisions in `extra_decisions.txt`, with capstone events `decolonization_events.300` / `.301`.

## Tech Tree Authoring

Three rules that bite when adding or moving techs in `common/technology/technologies/`:

### Same-category prereq rule (hard constraint)

A tech's `unlocking_technologies` must all be in the **same category** as the
tech itself (`production` / `military` / `society`). Vanilla has zero
cross-category prereqs across all 5 vanilla eras; the mod is also at zero. The
engine doesn't enforce this — cross-category prereqs load and play, but they
break the player-facing tech-tree UI flow (each category renders as its own
chain) and contradict every other tech in the tree.

`scripts/analysis/tech_balance_audit.py` reports `XCAT-PREREQ` flags for
violations. **Verify category match BEFORE writing the prereq edit, not
after** — the audit only catches it post-edit. Common pitfall: a society leaf
(e.g. `virtual_reality`) "naturally" wants to gate a military tech (e.g.
`augmented_reality_warfare`) thematically; the same-category rule means you
need to find a different forward-link or accept the leaf.

### Calibrated modifier budgets — grep before adding

Some modifiers are summed across multiple techs to reach a deliberate
end-game total. Examples found in this codebase:
- `state_mortality_mult` totals exactly −0.40 across `modern_vaccines`
  (era_6) + `antibiotic_mass_production` (era_7) + `mental_health_awareness`
  (era_10) + `biological_immortality` (era_12) + `mind_backups` (era_12),
  designed so mortality hits zero with brain uploading.
- `country_weekly_innovation_max_add` is the research-pool budget across the
  entire late-era tree; per-tech values are tuned together.
- `country_institution_<X>_max_investment_add` totals reach a target max
  (~9 institutions by end-game in combination with laws).

Before adding a modifier to a new tech, **grep the entire tech tree** for
that modifier name. If multiple techs already use it, the total may be
calibrated. Either move it (don't add net) or leave it off the new tech.
A simple grep + audit recipe:

```
for f in common/technology/technologies/era_*.txt; do
  awk -v m="<modifier>" '/^[a-z][a-z0-9_]+ = \{/{cur=$1; sub(/ = \{/,"",cur)} \
    $0~m{print cur": "$0}' "$f"
done
```

### Unlocks-first principle for new techs

A new tech's strongest justification is **re-routing existing PMs / laws /
decrees / buildings through it**, not stacking modifiers. The audit's
`scaled_sum < 1.0` flag generates false positives for techs whose primary
value lives in their unlock payload (combat units, mobilization options,
laws, PMs) — see e.g. `radar`, `rocketry`, `recon_satellites`,
`LGBTQ_rights_movement`, all of which have only one small modifier but
gate a real combat unit / mob option / PM / law.

When adding a new tech, **check what existing content could re-gate
through it before authoring the modifier block**. If nothing existing fits,
either author the new content alongside the tech, or hold the tech until
relevant content exists. A tech with 0 modifier value and 0 unlocks is
dead weight.

Don't strand a source tech: before re-routing a PM/law away from its
current tech, verify the source tech has other unlocks. Moving the only
unlock off a tech leaves it pure-modifier with no content presence.

### Polarity hints from `modifier_type_definitions/`

For mod-only modifier names that vanilla declares but doesn't use,
vanilla's `common/modifier_type_definitions/00_modifier_types.txt` includes
`color = good` / `color = bad` annotations that drive the engine's tooltip
coloring. These are reliable polarity tags — `state_homeland_creation_threshold_add`
(`color = bad`), `state_homeland_removal_threshold_add` (`color = good`),
`state_homeland_change_speed_mult` (`color = good`). When tagging polarity
in `docs/data/tech_modifier_polarity.yml`, check vanilla's color annotation
first; use it as the default and only override when the mod's design
intent inverts vanilla's frame.

## System-Scope Cheat Sheet

Where a given modifier or trigger can be used:

- **`mobilization_options/*`** `unit_modifier`: armies only. Don't use `military_formation_fleet_*` or `ship_*` modifiers here.
- **Tech `modifier = { ... }`** (in `common/technology/technologies/`): country-scope. `character_*` modifiers **work as of 1.13** — the engine cascades them to every character belonging to the country (verified empirically with `character_popularity_add`). Earlier in development this was a silent no-op, which explains workarounds elsewhere in this codebase. New uses should still verify with a quick in-game test the first time, since not every char-scope modifier may have been wired through. `ship_*` modifiers DO work in tech scope and apply as a country-wide buff to all ships (vanilla `paddle_steamer` uses `ship_hull_damage_mult` / `ship_crew_damage_mult` from a tech `modifier` block; `ship_battle_against_ship_type_*` patterns also work). Use `country_*`, `state_*`, `unit_*`, `building_*`, `ship_*`, `character_*` (verify new ones), or pre-defined country booleans (`country_<feature>_pb_principles_bool`) that are read elsewhere.
- **Power bloc `member_modifier` / `leader_modifier`**: country-scope. `character_*` modifiers cascade to all the country's characters.
- **Static modifiers (`common/static_modifiers/`)**: any scope's modifiers — but the static modifier must be applied at a matching scope (country / state / character).
- **`INJECT:` / `REPLACE:` / `REPLACE_OR_CREATE:` directive prefixes** on entity keys (e.g. `INJECT:building_shipyard = { ... }`) are **engine-native** in Vic3 (Clausewitz). The mod uses them throughout. They merge or replace into the matching vanilla entity at load time. Don't try to "expand" them in tooling.

## Audit and Research Workflow

When researching mod content (auditing for bugs, inventorying which PMs produce/consume a good, mapping a system across files), a few patterns are reliable and a few are surprisingly broken.

- **Use awk, not `grep -B/-A`, to find which block contains a line.** Paradox brace-nested files (PMs, buildings, laws, etc.) routinely have blocks larger than 40 lines. Running `grep -B40 'goods_output_X' file | grep '^pm_'` reads *across* PM boundaries and mis-attributes — you pick up the previous PM's header for a match deep inside another PM. Use `awk` with a state variable instead:

  ```bash
  awk '/^pm_|^REPLACE:pm_/{cur=$0} /goods_output_X/{print cur}' file | sort -u
  ```

  Track the current block as state, emit it when the marker hits. Reliable regardless of block size. The same pattern works for any header-marker pair: replace the headers with `^building_`, `^law_`, etc. as needed.

- **Verify subagent claims by reading the cited file before acting.** Subagent counts ("91 PMs consume X") are easy to re-verify and usually correct; subagent *attribution* claims ("X is consumed by construction sectors") often aren't, especially when the claim hinged on `grep -B/-A` interpretation or specific line numbers. When a critical finding is on the line of "fix this immediately", do the spot-check first. A few minutes of `Read`/`grep` saves a wrong fix.

- **Engine validation catches naming, not semantics.** `mod_state_server`'s `/validate/engine-coverage` (and `docs/engine/engine_coverage_report.md`) reports unknown/suspicious modifier *names*. It does **not** catch: modifiers whose default value is 0 and need explicit activation; per-building `_mult` modifiers in `workforce_scaled` blocks that go pathological at scale; cost-shape mismatches (treating a flat enable cost as a metered flow). Audits looking for those need to read the code, not just check the coverage report.

- **For Paradox files, `grep -rn "^xxx = "` shows top-level definitions reliably.** The same trick doesn't work inside nested blocks because indented lines lose the anchor. For nested searches, use the awk pattern above.

- **PMs in different groups within a building SUM additively.** When auditing a building's net effect, sum across all active PMs from all groups — they don't cancel or override each other. See `docs/vanilla/vanilla_economy_reference.md` § 2.
