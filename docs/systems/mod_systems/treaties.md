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
