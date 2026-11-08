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

### Enforce Emissions Reduction Treaty

- **Article key:** `enforce_emissions_reduction` in `common/treaty_articles/109_enforce_emissions_reduction.txt`.
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
- **AI:** `proposal_weight` and `wargoal_score_multiplier` are `enforce_privatization_ai_demand_weight`: 0 unless the demander is capitalist and the source's government owns at least `enforce_privatization_ai_min_levels` (10) levels outside the buildings it funds (`enforce_privatization_state_owned_levels`). Before that Britain pressed it on Tahiti, which has nothing to privatize, in a war with France.
- **Tooltip:** vanilla headed the source's modifiers with the war goal holder's name; the mod swaps the two headings for every enforce goal. Play-test: `docs/testing/treaty-war-goal-playtest.md`.

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

- **None (21), each tagged `# REVIEWED 2026-11-03 (involvement): why` on its opening line:** one-off concessions (`money_transfer`, `seize_company`, `disband_company`, `return_cultural_property`, `surrender_monument`, `te_cede_colony`, `population_transfer`), as vanilla's transfers build none; imposed restrictions (`enforce_privatization`, `demilitarized_zone`, `forced_disarmament`, `enforce_emissions_reduction`, `nuclear_disarmament`, `nuclear_program_pause`, `join_united_nations`, `nuclear_arms_limitation`), as vanilla's law commitment and no-tariffs articles build none; `suppress_subject_liberty`, whose overlord gains through the subject relation; and the five `te_seabed_lease_*`, whose claims lie in an ocean basin rather than the lessor's regions.
- **Audit:** `treaty_leverage_side_audit` flags a missing maximum or side, a mutual/directed mismatch, the wrong side, a figure outside 1 to 5,000 and a stale tag (`--strict` in CI).
- **Unverified in game:** the side reading. If a tooltip shows the wrong gainer, flip every directed side; play-test list `docs/testing/treaty-involvement-playtest.md`.
