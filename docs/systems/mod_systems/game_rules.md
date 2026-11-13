# Game Rules

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Game Rules

Twenty-one mod systems can be toggled or set at game setup via `common/game_rules/extra_game_rules.txt`; a rule can also be changed mid-game, from the change-country screen.

| Rule | Flag (enabled) | Default | Systems Gated |
|---|---|---|---|
| `custom_religions_allowed_rule` | `custom_religions_allowed` | **disabled** | Custom religion events, JE visibility |
| `banking_system_rule` | `banking_system_enabled` | enabled | Banking cycle, crash contagion. **Three settings, not two** — see below |
| `global_warming_rule` | `global_warming_enabled` | enabled | CO₂ tracking, GW modifiers |
| `world_war_rule` | `world_war_enabled` | **disabled** | World war escalation, related JEs |
| `cultural_hegemony_rule` | `cultural_hegemony_enabled` | enabled | Cultural pull calculation, hegemony JE, hegemony on-action |
| `covert_warfare_rule` | `covert_warfare_enabled` (late unlock, default), `covert_warfare_early_unlock` | late unlock | Covert operations command-centre JE (`je_covert_warfare`), all 18 covert diplomatic actions (secure loose material also needs `nuclear_weapons_enabled`). **Three settings**, read through `te_covert_warfare_on` / `te_covert_warfare_early` (§ Early and late unlock) |
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
| `demographics_rule` | `demographics_full` (default), `demographics_display_only`, `demographics_disabled` | full | The census (cohorts, panel tab and subtab, history, lists), experimental, on (Full) by default since 2026-10-25. Under Full the census sets each state's births and deaths (phase 2 step 4); outside Full nothing changes. Disabled runs no cohorts but leaves the walks, Dynastic Wealth and the war shock running. Checked positively through `te_demog_cohorts_run` and `te_demog_effects_run` (§ Demographics), so a save from before the rule reads as Disabled |
| `te_principle_slots_rule` | `te_principle_slots_eight` | eight | Power bloc principle slots from the four slot technologies (`te_pb_tech_principle_slots`, 0 under `te_principle_slots_four`); `MAX_PRINCIPLES` stays 8 and every slot limit reads `te_pb_principle_slot_cap`. The power bloc panel shows slots 5–8 (locked above the count) only when `te_pb_principle_slots_max` is 8. Checked as `NOT = { has_game_rule = te_principle_slots_four }` |
| `te_tax_code_rule` | `te_tax_code_enabled`, `te_tax_code_enabled_customs`, `te_tax_code_light` | **disabled** | The legislated tax code: vanilla taxation laws gated off, `law_te_tax_code` carrier with generated rate amendments (`gen_tax_code.py`); `_enabled_customs` also legislates customs. `_light` keeps the vanilla laws as bounds and sets each rate at once within them. Checked **positively**, as `te_tax_code_on` (any enabled setting) / `te_tax_code_full` / `te_tax_code_light_on` / `te_tax_customs_on` (`common/scripted_triggers/te_tax_triggers.txt`), never `NOT = { ...disabled }` |
| `global_commons_rule` | `global_commons_enabled` | enabled | Seabed licences capping the Deep-Sea Mine (§ Global Commons) and the UN's Law of the Sea and Antarctic Treaty terms built on them; disabled = the mine uncapped. Checked **positively** through `te_global_commons_enabled`: the system arrives with the rule, so a save from before it keeps the uncapped mine until the rule is switched on, when the first recording grandfathers every standing level. Launch windows and debris follow `space_race_rule` |
| `culture_merges_rule` | `culture_merges_enabled` | **disabled** | Culture merges (§ Culture Merges): the yearly census, the 32 merge journal entries and start buttons, conversion, the switch, the monthly primary-culture upkeep and the formation hook. Checked as `te_cm_system_enabled` = `has_game_rule = culture_merges_enabled`, so a save with no stored value stays off: one begun before the rule existed has no object for the 21 new result cultures (#1518). Off by default until most running games began with them. Switched off mid-game, every merge pauses where it stands and no variable is reset; switched back on, each resumes (the yearly net re-adds a candidate's or a running starter's pruned entry). Converted pops keep their culture, and the speed sources (Public Schools, the Ministry of Culture, Radio, Film, Mass Propaganda) keep their other effects. The injected Russification outcome has no rule gate |

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

**Early and late unlock** (2026-11-13, Steam Workshop feedback). A rule whose system opens at an era 6 or 7
technology can have a third setting that opens it at an earlier, historically fitting one, with the parts that only
make sense later kept behind their own technology. The late setting is the system as it was and keeps its old
setting name and flag (`<system>_enabled`), so a save made before keeps it; the new setting is
`<system>_early_unlock`. Every setting has one flag, named after it: whether `has_game_rule` reads a second flag on a
setting is unverified (vanilla's own reads name a setting, `allow_monument_effects`, whose flags are all
`disable_pm_*`), so no setting borrows another's name. Script reads these rules only through two triggers per
system in `common/scripted_triggers/te_rule_setting_triggers.txt`, `te_<system>_on` (either unlock) and
`te_<system>_early`; `test_rule_unlock_settings.py` fails on a bare `has_game_rule = <system>_enabled` anywhere else,
which would now mean the late setting alone. The early settings are new and not play-tested
(`docs/testing/early-unlock-rules-playtest.md`); each default stays as it was.

| Rule | Late unlock (as before) | Early unlock | Kept behind the late gate under early | Early to late mid-game |
|---|---|---|---|---|
| `covert_warfare_rule` | `mainframe_computers`, `computer_networks`, `cyber_warfare`, `quantum_computing` or the Ministry of Intelligence and Security law (`covert_warfare_slot_source`) | also `central_archives` (era 2, the technology vanilla's Secret Police law needs) | funding above Professional (`covert_agency_limited`, `covert_agency_funding_cap`); the operations keep their own gates, which leave espionage, wartime sabotage, cultivate assets and counterintelligence support | an entry opened early (`iw_opened_early`) and still short of the late gate ends through its invalid outcome with the rule-off teardown, and `covert_warfare_monthly_country` adds it back at the late gate (`iw_reopen_at_gate`) |

**Gating pattern:** Each rule sets a flag checked via `has_game_rule = <flag>`:
- **Journal entries:** `is_shown_when_inactive = { has_game_rule = X_enabled }`, `disable_evaluation = { NOT = { has_game_rule = X_enabled } }`, and an invalid outcome on the rule off (below)
- **On-actions:** Early `return = yes` if `NOT = { has_game_rule = X_enabled }`
- **Diplomatic actions:** `potential = { has_game_rule = X_enabled ... }`
- **Trait assignment (aptitude):** `limit = { te_aptitude_traits_enabled = yes  OR = { has_game_rule = universal_aptitude_traits_enabled  has_role_of_type = ruler  has_role_of_type = heir } }`

**Switched off mid-game** (2026-11-08). `disable_evaluation` prunes only inactive records, so every rule-pruned entry also ends on its rule, through its one hidden invalid outcome (the rule folded in with `OR` where it had one) or, for the Nuclear Program, by deactivating; each system clears what it left outside the entry. Inventory and in-game checks: `docs/testing/rules-off-midgame-playtest.md`; the rule: `scripting_best_practices.md`, the `disable_evaluation` bullet.

| System | What else goes | Back when switched on |
|---|---|---|
| Banking | the cycle's three variables (`te_banking_cycle_stop_for_rule`) | yes (`te_banking_entry_net`) |
| Banking, Full to Simplified | the entry stays; the monetary layer's managed modifiers, its economic state (back to step 0's seeds) and the External & Currency tools (`te_monetary_settle_rule_switch`); the monetary treaty articles end with no breach penalty (pegs on the anchor's dial, swap lines, lenders of last resort and receiverships on `requirement_to_maintain { te_mon_full_system = yes }`), a drawn swap line is settled and the backstop roles cleared; monetary-union principles stay | the layer starts again from neutral; ended treaties must be signed again |
| Social movements (6) | Civil Rights' path modifiers (`cr_je_cleanup_effect`) | no |
| Heir Education | counters and focus modifiers (`heir_education_cleanup_effect`) | no |
| Custom Religion | nothing (the builder's counters are its own) | no |
| Grand Monuments | the states' local modifiers, not the upkeep exemption (`gm_state_rule_off_on_action`); the two cultural-pull values and the state cards read the rule | yes (`gm_country_refresh`) |
| Cultural Hegemony | programs shut down, the hegemon's pressure off our movements | no |
| World War | its variables and latches on every country (`ww_stop_for_rule`, `world_war_events_on_action`) | no |
| Colonial Empire | `colonial_empire_je_cleanup_effect`; a stance lies dormant (`decol_stance_*_counts` read the rule) | yes (`ce_reentry_monthly`) |
| Covert Warfare | funding to 0 (every operation's pact breaks), the networks (`covert_stop_for_rule`) | no |
| Covert Warfare, Early to Late | an entry opened early and short of the late gate: the same teardown; one past it stays | yes, at the late gate (`iw_reopen_at_gate`) |
| Covert Warfare, Late to Early | nothing; an entry not yet open opens at Central Archives, with the budget cap | — |
| Nuclear Program | deactivates; `nuclear_power`, the taboo marker and an open crisis go (`nd_country_monthly_cleanup`); `nd_is_armed` and `nd_believed_armed` read the rule | no |
| Space Race (7 milestones) | running variables, no loss mark (`sr_stop_for_rule_base`); debris and Space Command modifiers | yes (`sr_reentry_monthly`) |
| Interstellar results | outlives the rule: the transit pauses | stays |
| United Nations | the organisation, quietly (`un_stop_for_rule`: no dissolution record or event) | no |
| Legislated Tax Code | the carrier gives way to the equivalent vanilla law; bands, relief, markers (`te_tax_rule_off_net`) | the code migrates again; the light code's entry net re-adds it |
| Culture merges (32) | outlive the rule: they pause (R19) | stay |

**Localization:** Rule names, option labels, and descriptions in `te_game_rules_l_english.yml`. Each rule has 5 keys: `rule_X_rule`, `setting_X_enabled`, `setting_X_enabled_desc`, `setting_X_disabled`, `setting_X_disabled_desc` — 7 for `banking_system_rule`, which adds `setting_banking_system_simplified` and its `_desc`, and for `demographics_rule`, whose three settings are `setting_demographics_full`, `_display_only` and `_disabled` with their `_desc`, 7 for each rule with an early and a late unlock (§ Early and late unlock), which adds `setting_<system>_early_unlock` and its `_desc`, and 11 for `free_market_construction_rule`, which adds `setting_free_market_construction_no_ai_retooling`, `_no_retooling` and `_no_maintenance` with their `_desc`.

**Game Concepts:** Both cultural hegemony and information warfare have detailed concept tooltips (8 concepts total) in `te_concepts_l_english.yml` with cross-linked `[concept_X]` references. Concepts: `concept_cultural_hegemony_system`, `concept_cultural_pull`, `concept_cultural_pull_components`, `concept_foreign_cultural_benchmark`, `concept_information_warfare_system`, `concept_digital_sovereignty`, `concept_cyber_operations`, `concept_cyber_detection`.

---
