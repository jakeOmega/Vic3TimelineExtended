# Nightly audit findings — 2026-05-27

15 targets audited (2499 lines budgeted). 2 issues filed, 1 comment added to an
existing issue, 0 auto-fix PRs (no clean intent-free fix met the auto-fix bar).

## Findings

1. **`common/strategic_regions/zzz_modified_strategic_regions.txt`** — `STATE_BAJA_CALIFORNIA`
   double-assigned to two strategic regions (mod adds it to `region_pacific_coast`
   while vanilla `region_central_america` still lists it). → **Issue filed.**

2. **`events/covert_warfare_events.txt`** — `covert_warfare.2` (defender-notification)
   trigger gates on 5 target modifiers, but ideological-subversion and destabilization
   ops apply `covert_ideological_subversion_resist` / `covert_destabilization_resist`
   (not in the OR), so a target hit only by those ops never gets the alert. → **Issue filed.**

3. **`events/nuclear_weapon_events.txt`** — `.1`/`.11` are `type = country_event` fired
   from state scope (`scope:target_state = { trigger_event … }`). Option triggers use
   `owner = { var:nuclear_weapon_stockpile }` (state→owner) but the `ai_chance` modifiers
   read `var:nuclear_weapon_stockpile` bare — one of the two is in the wrong scope. Same
   ROOT-type ambiguity as #153. → **Commented on #153** (not a new issue).

No findings: world_war_events, ship_modifications (clean vanilla-matched boilerplate;
all three `ship_battle_against_ship_type_*` axis combos registered), te_formable_formation_events,
te_formation_overrides, te_construction_market_global, te_map_modes_effects (dormant feature,
correctly gated), combined_arms_triggers (no-marines-group already tracked in #155),
te_state_traits + te_political_movements loc.

The three single-line targets (`extra_charters.txt`, `extra_rules.txt`, `extra_traits.txt`)
are **BOM-only empty stubs** — no content to audit; audit_count bumped for accounting.

## Loc-file self-instrumentation

| File | Prefixes found | Pre-loaded docs right? | Notes |
|---|---|---|---|
| `te_state_traits_l_english.yml` | `state_trait_` (+ `_desc`) | Yes (localization checklist) | Single clean prefix; encyclopedic flavor, tone on-style. `vanilla_states_reference.md` was relevant context for what state traits do, but the loc itself needed no extra doc. Heuristic predicted `state_trait_` correctly. |
| `te_political_movements_l_english.yml` | `movement_` (base, `_name`, and `_<crushed>_modifier` + `_desc`) | Yes | The `movement_crushed_*_modifier` sub-family (modifier loc nested under the `movement_` prefix) wasn't an obvious prediction — a movement loc file also carries modifier-description keys for movement-outcome modifiers. Noted: `movement_environmental` / base entries lack a `_name` key that `movement_anti_war`/`_civil_rights`/`_transhumanist` have (loc_coverage territory, not flagged here). |

Both loc files were small (47 / 22 lines) and fully on-tone; no tone/syntax findings.
