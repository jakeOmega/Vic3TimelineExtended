# Treaty Articles

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Treaty Articles with Entity Selection

> **Full design document:** `docs/vanilla/treaty_articles_reference.md` — read it when implementing a new treaty article.

Key gotchas:
- **Entity input types that work generically** (no GUI changes): `state`, `country`, `strategic_region`, `goods`, `law_type`, `text`.
- **`company` input** requires mod GUI — already implemented in `gui/right_click_menu.gui`, `gui/treaty_draft_panel.gui`, `gui/treaty_panel.gui`.
- **Loc keys needed:** `<name>`, `<name>_desc`, `<name>_effects_desc`, `<name>_article_short_desc`, plus AI desc keys.
- **Direction convention** (`kind = directed`): source_country makes the concession. Use `scope:article_options` (NOT `scope:article`) in `on_entry_into_force`.
- **Company picker:** `WarGoalDraft.GetTarget.GetCompanies` for punitive articles, `GetHolder.GetCompanies` for player's own entities.
- **Invalid triggers:** `is_owned_by_company` and `company` do NOT exist — use `exists = owning_company` + `owning_company = scope:article.input_company`.
- **One-off articles** (#1407): an article whose work is done at entry into force, with nothing to revert, carries `is_one_time` and not `can_be_renegotiated`, as vanilla's transfers do: `disband_company`, `seize_company`, `return_cultural_property`, `surrender_monument`, `te_cede_colony`, `population_transfer`. The AI withdraws from a treaty of mostly one-offs once its binding period ends, so it stops paying their upkeep, and a renegotiation keeps them locked and doesn't re-run them. `test_treaty_one_time_articles.py` holds the list. The money transfer (vanilla's weekly payment, despite its involvement tag) and the seabed leases stay renegotiable.
- Always guard `scope:article.input_company` with `exists = scope:article.input_company`.

### Emissions Reduction Treaty

- **Article key:** `enforce_emissions_reduction` in `common/treaty_articles/109_enforce_emissions_reduction.txt`, shown as Emissions Reduction so that its war goal reads Enforce Emissions Reduction (until 2026-11-08 the article and its concept, `concept_emissions_reduction_treaty`, were named Enforce Emissions Reduction and the war goal read Enforce Enforce Emissions Reduction). The key stays: script, saves and the `has_emissions_reduction_treaty` variable rest on it.
- **Purpose:** Forces its source country, market leader or member, to maintain seven national greenhouse-gas mitigation policies while the treaty is active.
- **Visibility and targeting:** Only visible once warming is active (`temperature_anomaly_display > 0.1`); signable from 0.5 °C against a source holding the climate journal entry.
- **Technology gate:** the source must have researched every technology the forced policies need (`gw_has_emissions_treaty_technologies`: `clean_energy_technologies`, `pollution_control`, `modern_urban_planning`), checked in `possible` (ROOT is the source) and again in `can_ratify` through `scope:source_country`. The treaty overrides the policies' warming thresholds (it forces Fossil-Fuel Divestment below 1.0 °C) but not their technology gates, so it never installs, say, Renewable Investment in a country that cannot build renewable plants. `test_gw_policy_tech_gates.py` keeps the list equal to the gates of the policies `non_fulfillment` names.
- **Enforcement mechanism:**
  - `on_entry_into_force` applies market-wide mitigation modifiers (`carbon_tax_modifier`, `renewable_investment_modifier`, `emission_standards_modifier`) and country-level mitigation modifiers (`reforestation_subsidies_modifier`, `public_transit_modifier`, `fossil_fuel_divestment_modifier`, `green_building_codes_modifier`) to the source country context.
  - Sets country variable `has_emissions_reduction_treaty` used by GW scripted buttons.
  - `non_fulfillment` freezes the treaty if required mitigation modifiers are removed.
- **Authority and politics:** the article's `source_modifier` carries `country_authority_cost_add = -750`, the sum of the five forced policies that cost authority (emission standards 200, reforestation 100, public transit 150, fossil-fuel divestment 200, green building codes 100). The source cannot repeal them, and charging for them could push it under its authority limit (bureaucracy falls, which can start a bankruptcy cycle) for a choice it no longer has. Climate adaptation costs authority but is not forced, so it keeps its cost. The treaty's own former +300 authority cost is replaced by `interest_group_ig_industrialists_approval_add = -2`. `test_gw_treaty_authority_waiver.py` fails if the waiver and the policy costs drift apart. The article also needs the source to hold `je_global_warming` (the waiver assumes there is something to waive). Market members of a bound leader are not bound: they hold the market-wide policies (emission standards costs 200) but have no variable, no waiver, and cannot repeal.
- **Button lock integration:** Remove-button `possible`/`visible` checks in `common/scripted_buttons/global_warming_buttons.txt` now block rollback when `has_emissions_reduction_treaty` is present (for emissions-reduction policies only).

### Privatization

- **Article key:** `enforce_privatization` in `common/treaty_articles/105_enforce_privatization.txt`, shown as Privatization so that its war goal reads Enforce Privatization (vanilla's `war_goal_enforce_treaty_article` prefixes "Enforce"; until 2026-11-08 it read Enforce Enforce Privatization).
- **Effect:** the source, the conceding country, gets `country_force_privatization_bool` and a +200 authority cost; the demanding target gets +5% prestige.
- **Gates:** the source needs Cooperative Ownership, Agrarianism or Traditionalism and the target Laissez-Faire or Interventionism, both in `possible`, since a war goal checks `possible` and not `can_ratify` (the target's test sat only in `can_ratify` until 2026-11-08).
- **AI:** `proposal_weight` and `wargoal_score_multiplier` are `enforce_privatization_ai_demand_weight`: 0 unless the demander is capitalist and the source's government owns at least `enforce_privatization_ai_min_levels` (10) levels outside the buildings it funds (`enforce_privatization_state_owned_levels`). Past that gate it scales with the source's `gdp_ranking` (`treaty_ai_demand_economy_factor`, shared with the weights below): 1 for the top ten, 0.4 for 11th to 20th, 0.1 below (owner, 2026-11-08: a small economy is a small prize). Before that Britain pressed it on Tahiti, which has nothing to privatize, in a war with France.
- **Tooltip:** vanilla headed the source's modifiers with the war goal holder's name; the mod swaps the two headings for every enforce goal. Play-test: `docs/testing/treaty-war-goal-playtest.md`.

### AI demand weights

Every `can_be_enforced` article tells the AI where a demand buys nothing, through `proposal_weight` (asking for it in a treaty) and `wargoal_score_multiplier` (pressing it as an enforce war goal), or says in its `ai` block why it needs neither: `# REVIEWED YYYY-MM-DD (ai_demand_weight): rationale`. `test_treaty_ai_demand_weights.py` fails on an enforceable article with neither, on one with only one of the two, and on a stale tag. The rule and the scopes: `docs/guides/scripting_best_practices.md`, "proposal_weight and wargoal_score_multiplier". The named weights are in `common/script_values/extra_script_values.txt` ("AI demand weights for enforceable treaty articles") and the input halves in `common/scripted_triggers/te_treaty_ai_demand_triggers.txt`. An article that names an input asks the test of the chosen one (`scope:article.input_company` / `.input_state`, as vanilla's `treaty_port` reads its state) and, with none bound yet, of every input the source could name. Each is 0 where the demand buys nothing. Past its gate it is 1, or, where the prize is the conceder's economy as a whole (Privatization, Forced Disarmament, Free Port Concession, Emissions Reduction), `treaty_ai_demand_economy_factor`: 1 for a top-ten GDP, 0.4 for 11th to 20th, 0.1 below. Players are not bound.

| Article | The AI demands it only where |
|---|---|
| Seize Company | the company owns at least `company_article_ai_min_levels` (5) levels and the receiver has no company of its type |
| Disband Company | the company owns at least 5 levels |
| Minority Protection | a people or faith of the protector is discriminated in the state (culture at least 5% below acceptance 80, or faith at least 10% below medium acceptance) |
| Free Port Concession | the two are in different markets and the state is a port with a yearly GDP of at least `free_port_concession_ai_min_state_gdp` (500,000); scaled by GDP rank |
| Privatization | see above; scaled by GDP rank |
| Religious Mission Rights | at least a tenth of the state is of another faith than the missionary power's |
| Demilitarized Zone | the state holds a Barracks, Naval Administration, Naval Fortification, Naval Logistics Center or Military Base, or borders the demander |
| Forced Disarmament | the source has `forced_disarmament_ai_min_units` (10) battalions or flotillas, or an Arms Industry, Artillery Foundry or Munition Plant; scaled by GDP rank |
| Emissions Reduction | the source emits at least `enforce_emissions_reduction_ai_min_share_pct` (1%) of the world's yearly total and doesn't already run all seven forced policies; scaled by GDP rank |
| Imposed Currency Peg | the source isn't already pegged (`te_mon_is_anchored`) |
| Debt Receivership | the source isn't already under a receivership or a lender-of-last-resort guarantee |
| Nuclear Program Freeze, Nuclear Disarmament | `docs/systems/mod_systems/nuclear.md` |
| Population Transfer | it would move at least 100,000 people (`docs/systems/mod_systems/pops_and_migration.md`) |
| Lease Seabed Claims, Cede Colony | the source has claims to lease, or a colony |

Reviewed exemptions: Money Transfer (vanilla's, which has neither field; money is worth having from anyone), Corporate Concessions (hidden while WIP, and the demander's gain is the same whoever concedes), and Return Cultural Property, Surrender a Monument and Excavation Concession, whose `possible` already makes the demand impossible where it would buy nothing.

The weight holds the zero cases that sit in `can_ratify` and can't move to `possible`: a test that needs the input (Seize's receiver already has the type), or one that `possible`, which can't tell the treaty being renegotiated from another, would trip on renegotiation (one peg at a time, one receivership at a time). A test of who may demand an article does belong in `possible`, read one way round: since 2026-11-08 Minority Protection's protector bloc, Religious Mission Rights' missionary bloc and Excavation Concession's sponsor technology are there as well as in `can_ratify`. Seize Company's receiver test also sits in `company_valid_trigger`, which a war goal's input picker reads, so a war goal can't seize a company whose type the holder already has (the source would lose it and the holder gain nothing).

## Dynamic Treaty Names

- **Purpose:** Gives thematic names to treaties containing mod-specific treaty articles (instead of generic "Treaty of [City]").
- **How it works:** Each entry in `common/dynamic_treaty_names/` has a `trigger` (checked against the treaty's articles via `any_scope_article_option = { has_type = X }`) and a `weight` (higher = more likely). The engine picks one of the matching names at random, weighted by `weight` (vanilla `common/dynamic_treaty_names/readme.md`), so a heavy name is only the likeliest, not guaranteed; the treaty draft's randomize button (`TreatyDraft.RandomizeName`) re-rolls it.
- **Coverage by article type:**
  - Corporate: `seize_company`, `disband_company`, `enforce_privatization`, `corporate_concessions`, `free_port_concession`, `money_transfer`
  - Humanitarian: `minority_protection`, `cultural_exchange`, `religious_mission_rights`
  - Military: `dmz_and_disarmament`
  - Economic: `grid_interconnection` (`grid_interconnection_agreement`: Grid Interconnection Treaty, a Power Pool)
  - Diplomatic/Aid: `education_aid`, `healthcare_aid`, `request_influence`, `extend_influence`, `crisis_resolution`
- **Loc variables:** `$SIGNING_LOCATION$`, `[FIRST_COUNTRY.GetAdjectiveNoFormatting]`, `[SECOND_COUNTRY.GetAdjectiveNoFormatting]`, `[FIRST_COUNTRY.GetNameNoFormatting]`.
- **Files:** `common/dynamic_treaty_names/te_dynamic_treaty_names.txt`, localization in `te_miscellaneous_l_english.yml`.

## Involvement

Every mod treaty article either builds Involvement, the score behind a country's interest tier in a strategic region, or carries a reviewed reason it builds none (2026-11-03). Before then none did.

- **Fields:** `max_target_involvement = N` and `target_involvement_applies_to`, after `cost` / `relations_*`. The side names the **local** party; the other gains up to N in every strategic region where it is local, scaled by its locality (floor 10%, `INTEREST_MIN_INVOLVEMENT_RATIO`). All treaties and pacts together are capped at 5,000 a region (`INTEREST_TREATY_PACT_INVOLVEMENT_CAP`), so no stack of aid articles takes a donor past Pervasive on treaties alone.
- **Side rule:** a directed article names the side its leverage line sits on (the leveraged side is local), or with no leverage line the side that does not pay maintenance. A mutual article takes `mutual`.
- **Values** (each the nearest vanilla analogue's):

| Max | Local side | Articles | Analogue |
|---|---|---|---|
| 2,000 | target | `extend_influence`, `nuclear_basing` | bloc embassy; between military access and treaty port |
| 2,000 | source | `request_influence`, `currency_peg`, `imposed_currency_peg`, `debt_receivership` | bloc embassy; investment rights |
| 1,000 | target | `crisis_resolution`, `education_aid`, `healthcare_aid`, `security_aid`, `development_assistance`, `science_aid`, `science_aid_2`, `nuclear_program_aid`, `nuclear_security_assistance`, `nuclear_guarantee`, `swap_line`, `lender_of_last_resort` | military assistance; guarantee |
| 1,000 | source | `corporate_concessions`, `free_port_concession`, `minority_protection`, `religious_mission_rights` | monopoly; trade privilege |
| 1,000 | mutual | `cultural_exchange_program`, `intelligence_sharing_pact`, `joint_military_exercises`, `grid_interconnection_agreement` | transit rights; military assistance |
| 500 | source | `archaeological_concession`, `excavation_permit` | vanilla's 500 tier |

- **None (22), each tagged `# REVIEWED <date> (involvement): why` on its opening line:** one-off concessions (`money_transfer`, `seize_company`, `disband_company`, `return_cultural_property`, `surrender_monument`, `te_cede_colony`, `population_transfer`, `te_reparations`), as vanilla's transfers build none; imposed restrictions (`enforce_privatization`, `demilitarized_zone`, `forced_disarmament`, `enforce_emissions_reduction`, `nuclear_disarmament`, `nuclear_program_pause`, `join_united_nations`, `nuclear_arms_limitation`), as vanilla's law commitment and no-tariffs articles build none; `suppress_subject_liberty`, whose overlord gains through the subject relation; and the five `te_seabed_lease_*`, whose claims lie in an ocean basin rather than the lessor's regions.
- **Audit:** `treaty_leverage_side_audit` flags a missing maximum or side, a mutual/directed mismatch, the wrong side, a figure outside 1 to 5,000 and a stale tag (`--strict` in CI).
- **Unverified in game:** the side reading. If a tooltip shows the wrong gainer, flip every directed side; play-test list `docs/testing/treaty-involvement-playtest.md`.

## Proposal Checks and the Lens

- **`can_propose` (1.15)** runs on the whole treaty when it is proposed or answered, never when an article is added to a draft, with `can_ratify`'s scopes. A requirement for a partner article in the same treaty sits there, so the player can add the two in either order (#1440): Extensive Modernization Aid's Modernization Aid (in force or in the treaty), Joint Military Exercises' military ties, and the Nuclear Guarantee's ties (an alliance, defensive pact or Guarantee Independence, or a shared bloc; the Budapest offer still skips it). Duplicate, count and outguns checks stay in `can_ratify`. `treaty_evaluation_scope_audit` reads `can_propose` as it reads `can_ratify`.
- **`show_in_lens` (1.15)**: the 31 mod articles with no required input carry the flag and are listed in the diplomatic lens's Treaty Articles tab. Twelve also carry a `show_in_lens` trigger holding the world-wide part of their `visible`, so they leave the lens when their system is off: the five nuclear articles (the Nuclear Weapons rule), the five monetary articles (`te_mon_full_system`), Return Cultural Property (`gm_system_enabled`) and Join the United Nations (`un_founded`). The rest of each `visible` reads the viewer as the source, and the lens viewer need not be the source, so it stays out of the trigger. The flag is ignored on articles with required inputs. No GUI change: the three treaty GUI overrides (`treaty_draft_panel.gui`, `treaty_panel.gui`, `right_click_menu.gui`) are vanilla 1.15.1's files plus the mod's input hunks (#1594), and the lens is vanilla's own panel.

## Cessions and Reparations as Treaties

A state or a sum the mod hands over outside a war goes as a treaty in force at once, binding for two years (#1457): the irredentism cession (`irredentism.2.b`) and UN court compliance (`un_court_comply`) under vanilla's `state_transfer`, colonial reparations (`decolonization_events.6.a`) and a nuclear crisis's reparations (`nd_crisis_concede_reparations`) under the mod's one-off `te_reparations` (`126_reparations.txt`). The helpers are `te_cede_state_by_treaty` and `te_pay_reparations_by_treaty` (`common/scripted_effects/te_treaty_transfer_effects.txt`).

- **The sum is not an input.** The helper records it on the payer (`te_reparations_due`, `te_reparations_due_to`) before it creates the treaty; the article is visible only to that payer toward that payee while the record stands, and its `on_entry_into_force` pays and clears it (`te_reparations_settle`).
- **Never a silent no-op.** Where `can_create_treaty` fails (a capital or a state neither adjacent nor coastal, a giver with one state) or a check from the same country's last transfer is still waiting, the state or money moves directly, now. Otherwise the hidden `te_treaty_transfer.1` / `.2` three days on read the result and make the direct transfer if the treaty didn't. Whether `create_treaty` with `is_draft = no` runs its articles' `on_entry_into_force` is unverified (C21); the checks log `TE_SELF_CHECK OK|BROKEN treaty_state_transfer` and `treaty_reparations` once a game (`docs/testing/vanilla-1-15-playtest.md`).
- **Tooltips** show the transfer as the direct effect did (`show_as_tooltip`); the treaty itself shows only in the diplomacy panel.
