# Game Rules

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Game Rules

Twenty mod systems can be toggled or set at game setup via `common/game_rules/extra_game_rules.txt`.

| Rule | Flag (enabled) | Default | Systems Gated |
|---|---|---|---|
| `custom_religions_allowed_rule` | `custom_religions_allowed` | **disabled** | Custom religion events, JE visibility |
| `banking_system_rule` | `banking_system_enabled` | enabled | Banking cycle, crash contagion. **Three settings, not two** — see below |
| `global_warming_rule` | `global_warming_enabled` | enabled | CO₂ tracking, GW modifiers |
| `world_war_rule` | `world_war_enabled` | **disabled** | World war escalation, related JEs |
| `cultural_hegemony_rule` | `cultural_hegemony_enabled` | enabled | Cultural pull calculation, hegemony JE, hegemony on-action |
| `covert_warfare_rule` | `covert_warfare_enabled` | enabled | Covert operations command-centre JE (`je_covert_warfare`), all 15 covert diplomatic actions (secure loose material also needs `nuclear_weapons_enabled`) |
| `heir_education_rule` | `heir_education_enabled` | **disabled** | Heir education JE and focus modifiers; aptitude traits for rulers and heirs |
| `united_nations_rule` | `united_nations_enabled` | enabled | UN JE, vote events, international institutions |
| `nuclear_weapons_rule` | `nuclear_weapons_enabled` | enabled | Nuclear program JE, nuclear strike events, disarmament treaty |
| `decolonization_rule` | `decolonization_enabled` | enabled | Decolonization events and colonial collapse absorption |
| `space_race_rule` | `space_race_enabled` | enabled | Space race JE, satellite/moon/interplanetary events |
| `social_movements_rule` | `social_movements_enabled` | enabled | 8 social movement JEs and associated events |
| `universal_aptitude_traits_rule` | `universal_aptitude_traits_enabled` | **disabled** | Assigns admin/diplo/military aptitude traits to ALL adult characters instead of only rulers and heirs — works with Heir Education off too. With both rules off, no aptitude traits at all |
| `free_market_construction_rule` | `free_market_construction_enabled` | enabled | The construction market (§ Construction as a Market Good); `_no_ai_retooling` = the market without the retooling surcharge for AI-owned buildings only, `_no_retooling` = the market without the retooling surcharge, `_no_maintenance` = the market without construction maintenance (§ Market settings without retooling or maintenance); disabled = base-game-style direct construction (§ Free Market Construction off). Read through `te_free_market_construction_on` / `_off`, which test the *disabled* flag so a save from before the rule keeps the market, and `te_building_retooling_waived` (building scope) |
| `internal_resettlement_rule` | `internal_resettlement_enabled` | enabled | Settlement Authority and resettlement programs; `_ai_voluntary` = AI countries run only voluntary programs |
| `grand_monuments_rule` | `grand_monuments_enabled` | enabled | Grand Monument building, dedication ceremony, contests, Monuments JE; checked as `NOT = { has_game_rule = grand_monuments_disabled }` |
| `demographics_rule` | `demographics_full` (default), `demographics_display_only`, `demographics_disabled` | full | The census (cohorts, panel tab and subtab, history, lists), experimental, on (Full) by default since 2026-10-25. Under Full the census sets each state's births and deaths (phase 2 step 4); outside Full nothing changes. Disabled runs no cohorts but leaves the walks, Wealth Concentration and the war shock running. Checked positively through `te_demog_cohorts_run` and `te_demog_effects_run` (§ Demographics), so a save from before the rule reads as Disabled |
| `te_principle_slots_rule` | `te_principle_slots_eight` | eight | Power bloc principle slots from the four slot technologies (`te_pb_tech_principle_slots`, 0 under `te_principle_slots_four`); `MAX_PRINCIPLES` stays 8 and every slot limit reads `te_pb_principle_slot_cap`. The power bloc panel shows slots 5–8 (locked above the count) only when `te_pb_principle_slots_max` is 8. Checked as `NOT = { has_game_rule = te_principle_slots_four }` |
| `te_tax_code_rule` | `te_tax_code_enabled`, `te_tax_code_enabled_customs`, `te_tax_code_light` | **disabled** | The legislated tax code: vanilla taxation laws gated off, `law_te_tax_code` carrier with generated rate amendments (`gen_tax_code.py`); `_enabled_customs` also legislates customs. `_light` keeps the vanilla laws as bounds and sets each rate at once within them. Checked **positively**, as `te_tax_code_on` (any enabled setting) / `te_tax_code_full` / `te_tax_code_light_on` / `te_tax_customs_on` (`common/scripted_triggers/te_tax_triggers.txt`), never `NOT = { ...disabled }` |
| `global_commons_rule` | `global_commons_enabled` | enabled | Seabed licences capping the Deep-Sea Mine (§ Global Commons) and the UN's Law of the Sea and Antarctic Treaty terms built on them; disabled = the mine uncapped. Checked **positively** through `te_global_commons_enabled`: the system arrives with the rule, so a save from before it keeps the uncapped mine until the rule is switched on, when the first recording grandfathers every standing level. Launch windows and debris follow `space_race_rule` |

**`banking_system_rule` has three settings.** `banking_system_enabled`, `banking_system_simplified`
and `banking_system_disabled`. The middle one keeps the Banking Cycle journal entry — the cycle,
its crashes, the prudential and command/cooperative tools, the financial-regulation laws — and
switches off the monetary-policy layer built on top of it (`monetary_policy_design.md`
phases 1–5): no policy-rate dial, no inflation, no exchange rate, no pegs / swap lines /
guarantees / shared currency. Two scripted triggers tell the halves apart, and **nothing reads
the rule directly any more**:

| Trigger | File | True for | Asked by |
|---|---|---|---|
| `te_banking_system_on` | `common/scripted_triggers/banking_policy_triggers.txt` | enabled **and** simplified | the journal entry's `is_shown_when_inactive`, the banking history series |
| `te_mon_full_system` | `common/scripted_triggers/te_monetary_triggers.txt` | enabled only | every step of the monetary layer (see § Banking Cycle → Monetary Policy) |

Both read only a game rule, so they work from any scope — country, journal entry, treaty
article, power-bloc principle, GUI.

**Gating pattern:** Each rule sets a flag checked via `has_game_rule = <flag>`:
- **Journal entries:** `is_shown_when_inactive = { has_game_rule = X_enabled }`
- **On-actions:** Early `return = yes` if `NOT = { has_game_rule = X_enabled }`
- **Diplomatic actions:** `potential = { has_game_rule = X_enabled ... }`
- **Trait assignment (aptitude):** `limit = { te_aptitude_traits_enabled = yes  OR = { has_game_rule = universal_aptitude_traits_enabled  has_role_of_type = ruler  has_role_of_type = heir } }`

**Localization:** Rule names, option labels, and descriptions in `te_game_rules_l_english.yml`. Each rule has 5 keys: `rule_X_rule`, `setting_X_enabled`, `setting_X_enabled_desc`, `setting_X_disabled`, `setting_X_disabled_desc` — 7 for `banking_system_rule`, which adds `setting_banking_system_simplified` and its `_desc`, and for `demographics_rule`, whose three settings are `setting_demographics_full`, `_display_only` and `_disabled` with their `_desc`, and 11 for `free_market_construction_rule`, which adds `setting_free_market_construction_no_ai_retooling`, `_no_retooling` and `_no_maintenance` with their `_desc`.

**Game Concepts:** Both cultural hegemony and information warfare have detailed concept tooltips (8 concepts total) in `te_concepts_l_english.yml` with cross-linked `[concept_X]` references. Concepts: `concept_cultural_hegemony_system`, `concept_cultural_pull`, `concept_cultural_pull_components`, `concept_foreign_cultural_benchmark`, `concept_information_warfare_system`, `concept_digital_sovereignty`, `concept_cyber_operations`, `concept_cyber_detection`.

---
