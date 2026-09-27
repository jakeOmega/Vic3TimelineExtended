# Vanilla Company Buildings — Reference & Design

## Overview

The mod's **company building system** gives flavored companies a unique building that can only be built when that company is active. Vanilla companies have no unique buildings by default — this is a mod innovation. All buildings documented here are implemented. This document covers:
1. Which high-profile **vanilla flavored companies** have unique buildings
2. Which **vanilla generic companies** have generic buildings
3. How **all vanilla companies** are updated to include mod-exclusive buildings and goods

## Current System Architecture

Each company building follows this pattern:
- **Building group:** `bg_company_buildings`
- **Potential:** Gated by `has_company = company_X` (only buildable when company is active)
- **Ownership:** `ownership_type = self`
- **Cost:** `construction_cost_mega_high`
- **Production methods:** Single PMG with 1-2 PMs
- **Company integration:** Company's `prosperity_modifier` includes `state_building_X_max_level_add = 1`

Counts as of 2026-09-26: `common/buildings/company_buildings.txt` defines **315** company buildings. **11** are retired (`potential = { always = no }`, kept so saves load), leaving **304 active flagships**:
- **270 named flagships** for flavored companies, vanilla and mod alike;
- **34 generic flagships** (`building_generic_*`) for generic company types.

Every one of the 221 base-game companies and all 85 mod companies has a flagship, and no company has more than one. (Two generic flagships are shared by two companies each: the Granary Complex and the Textile Depot.) The retired eleven are `building_generic_mega_factory`, `_exhibition_centre`, `_shipping_terminal`, `_corporate_university`, `_industrial_city`, `_pipeline_terminus`, `_rail_nexus`, `_financial_center`, `_monument_to_industry`, `_spaceport` and `_hq_skyscraper`; the monthly company-building cleanup removes any that still stand.

**Flavored company buildings** have ~2000 employment, significant goods I/O, and strong state modifiers.
**Generic company buildings** have ~10000 employment, weaker modifiers, and simpler goods setups.

## Selection Criteria

Vanilla companies to prioritize for unique buildings:
1. **Iconic real-world companies** that players will recognize
2. **Companies with distinct industrial identities** (not just "another textile company")
3. **Companies from underrepresented regions** (Africa, South America, Middle East)
4. **Companies that span interesting eras** (early industrial → modern)

---

## Part A: Flavored Company Buildings

### Great Britain
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_east_india` | `building_eic_trading_house` | Trade/colonial commerce hub | 1836+ |
| `company_rolls_royce` | `building_rolls_royce_derby_works` | Luxury automotive + aero engines | 1906+ |
| `company_bp` | `building_bp_refinery_complex` | Oil refining megacomplex | 1909+ |
| `company_de_beers` | `building_de_beers_sorting_office` | Diamond sorting/trading center | 1888+ |

### Germany
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_krupp` | `building_krupp_essen_works` | Steel/arms industrial complex | 1836+ |
| `company_siemens` | `building_siemens_erlangen_campus` | Electrical engineering R&D | 1847+ |
| `company_bayer` | `building_bayer_leverkusen_plant` | Chemical/pharmaceutical plant | 1863+ |
| `company_thyssen` | `building_thyssen_steelworks` | Steel production mega-mill | 1867+ |

### United States
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_standard_oil` | `building_standard_oil_refinery` | Oil monopoly refinery complex | 1870+ |
| `company_us_steel` | `building_carnegie_homestead_mill` | Steel production giant — Carnegie Steel | 1875+ |
| `company_ford_motor` | `building_ford_rouge_plant` | Assembly line mega-factory | 1903+ |
| `company_general_electric` | `building_ge_schenectady_works` | Electrical manufacturing | 1892+ |
| `company_dupont` | `building_dupont_experimental_station` | Chemical research complex | 1802+ |
| `company_boeing` | `building_boeing_everett_factory` | Aircraft manufacturing plant | 1916+ |

### France
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_schneider` | `building_schneider_le_creusot` | Arms/steel industrial complex | 1836+ |
| `company_renault` | `building_renault_billancourt_plant` | Automobile factory | 1899+ |
| `company_michelin` | `building_michelin_clermont_ferrand` | Rubber/tire manufacturing | 1889+ |

### Russia
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_nobel_brothers` | `building_nobel_baku_refinery` | Oil extraction/refining | 1876+ |
| `company_putilov` | `building_putilov_works` | Heavy machinery/rail factory | 1836+ |

### Japan
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_mitsubishi` | `building_mitsubishi_nagasaki_shipyard` | Shipbuilding/heavy industry | 1870+ |
| `company_mitsui` | `building_mitsui_trading_house` | Trade/banking conglomerate | 1876+ |
| `company_sumitomo` | `building_sumitomo_besshi_mine` | Mining/smelting complex | 1836+ |

### Italy
| Company | Building | Theme | Era |
|---|---|---|---|
| `company_fiat` | `building_fiat_lingotto_factory` | Automobile manufacturing | 1899+ |
| `company_pirelli` | `building_pirelli_bicocca_plant` | Rubber/cable manufacturing | 1872+ |

### Other Regions
| Company | Building | Theme | Region |
|---|---|---|---|
| `company_tata` | `building_tata_jamshedpur_works` | Steel/industrial conglomerate | India |
| `company_jardine_matheson` | `building_jardine_princeps_house` | Trading/shipping hub | China/HK |

### The Great Wave (DLC 018)
The base game's second expansion adds sixteen flavored companies in `00_companies_ep2.txt`. Sumitomo (above) had its flagship first; the other fifteen got theirs in Phase 9. Each is gated like Sumitomo's, uses the company's own vanilla icon, and gives two workforce-scaled state throughput bonuses to the company's own industries.

| Company | Building | Landmark | State throughput |
|---|---|---|---|
| `company_yasuda` | `building_yasuda_atosanupuri_mine` | Atosanupuri sulfur mine, Hokkaido | sulfur mine +15%, railway +5% |
| `company_tokyo_electric_light_company` | `building_tokyo_electric_asakusa_station` | Asakusa power station, Tokyo | power plant +15%, urban center +5% |
| `company_guthrie` | `building_guthrie_singapore_agency` | Guthrie & Co. head office, Singapore | coffee +10%, tea +10% |
| `company_societe_francaise_charbonnages_du_tonkin` | `building_sfct_hon_gai_collieries` | Hòn Gai collieries, Tonkin | coal mine +15%, port +5% |
| `company_broken_hill_proprietary_company` | `building_bhp_broken_hill_mine` | Broken Hill Line of Lode | lead mine +15%, steel mill +5% |
| `company_ramirez` | `building_ramirez_vila_real_cannery` | Vila Real de Santo António cannery | food industry +15%, fishing wharf +5% |
| `company_oriental_consolidated_mining` | `building_ocmc_unsan_gold_mines` | Unsan gold concession, Korea | gold mine +15%, logging camp +5% |
| `company_siam_electrical_company_limited` | `building_siam_electric_wat_liab_station` | Wat Liab power station, Bangkok | power plant +15%, railway +5% |
| `company_ferranti_ltd` | `building_ferranti_hollinwood_works` | Hollinwood works, Oldham | electrics industry +15%, power plant +5% |
| `company_van_vlissingen_en_dudok_van_heel` | `building_van_vlissingen_oostenburg_works` | Oostenburg works, Amsterdam | motor industry +15%, shipyard +5% |
| `company_maschinenfabrik_oerlikon` | `building_mfo_oerlikon_works` | MFO works, Oerlikon | motor industry +10%, tooling workshop +10% |
| `company_a_markwald_and_company` | `building_markwald_bangkok_rice_mill` | Markwald rice mill, Bangkok | rice farm +15%, port +5% |
| `company_nhm` | `building_nhm_factorij_batavia` | NHM Factorij, Batavia | coffee +15%, sugar +5% |
| `company_white_star_line` | `building_white_star_albion_house` | Albion House, Liverpool | port +15%, shipyard +5% |
| `company_noda_shoyu` | `building_noda_shoyu_goyogura` | Goyōgura brewery, Noda | food industry +15%, rice farm +5% |

---

## Part B: Generic Company Buildings

Vanilla generic companies (from `99_basic_companies.txt`) should receive **weaker generic buildings** — similar in scale to the mod's existing generic buildings (~10000 employment, simpler goods, modest state bonuses). These unlock via the existing `prosperity_modifier` `state_building_X_max_level_add = 1` pattern.

### Generic Buildings by Sector

| Vanilla Company | New Generic Building | Theme | State Modifiers |
|---|---|---|---|
| `company_basic_agriculture_1` | `building_generic_granary_complex` | Grain storage/distribution hub | `building_group_bg_agriculture_throughput_add = 0.05` |
| `company_basic_agriculture_2` | `building_generic_granary_complex` | (shared with agriculture_1) | (same building, different company gate) |
| `company_basic_fabrics` | `building_generic_textile_depot` | Fabric warehousing/dyeing | `building_textile_mill_throughput_add = 0.1` |
| `company_basic_food` | `building_generic_cold_storage` | Food preservation/distribution | `state_birth_rate_mult = 0.03` |
| `company_basic_steel` | `building_generic_foundry_complex` | Steel/iron smelting campus | `building_steel_mill_throughput_add = 0.1` |
| `company_basic_metalworks` | `building_generic_machine_shop` | Tools/precision engineering | `bg_manufacturing_throughput_add = 0.05` |
| `company_basic_chemicals` | `building_generic_chem_works` | Chemical processing campus | `building_chemical_plant_throughput_add = 0.1` |
| `company_basic_oil` | `building_generic_tank_farm` | Oil storage/refining depot | `state_migration_pull_mult = 0.1` |
| `company_basic_munitions` | `building_generic_ordnance_depot` | Munitions storage/testing | `military_goods_cost_mult = -0.05` |
| `company_basic_motors` | `building_generic_motor_works` | Engine/vehicle assembly | `building_motor_industry_throughput_add = 0.1` |
| `company_basic_shipyards` | `building_generic_dry_dock` | Ship repair/construction | `building_shipyard_throughput_add = 0.1` |
| `company_basic_weapons` | `building_generic_arsenal` | Arms depot/proving ground | `unit_offense_mult = 0.05` |
| `company_basic_textiles` | `building_generic_textile_depot` | (shared with fabrics) | (same building) |
| `company_basic_fishing` | `building_generic_fish_market` | Wholesale fish market | `state_standard_of_living_add = 1` |
| `company_basic_home_goods` | `building_generic_furniture_showroom` | Furniture/homewares emporium fronting a fab workshop | `building_furniture_manufactory_throughput_add = 0.1` |
| `company_basic_forestry` | `building_generic_lumber_yard` | Industrial sawmill + timber yard | `building_logging_camp_throughput_add = 0.1` |

**Special case — `company_basic_electrics`:** REPLACE'd in `extra_companies_generic.txt` to a "Telecommunications" generic covering `building_electrics_industry` + `building_electrics_industry_radio` + `building_electrics_industry_appliances`, plus one unique mod building, `building_generic_electronics_lab` (the radios/telephones manufacturing play). A second, `building_generic_hq_skyscraper`, was retired in Phase 9 so that no company has two flagships. Prestige good: `prestige_good_generic_consumer_appliances`. The full definition lives in the REPLACE: block; do NOT scatter additions into `extra_companies_vanilla_updates.txt` — the REPLACE/INJECT merge order is fragile.

All other vanilla generic companies now have at least one unique mod building — Phase 6 added the colonial / mining / silk / wine / paper buildings; Phase 8 added home_goods and forestry.

**Mod generic companies** (`extra_companies_generic.txt`) list their flagship in their own `building_types` and grant its level in their own `prosperity_modifier`, with no INJECT. The last one without a flagship, `company_basic_synthetics` (synthetic dyes and artificial fibers), got `building_generic_dye_fiber_park` in Phase 9: +5% throughput to `building_synthetics_plant` and `building_synthetics_plant_silk`, coal and wood into dye and silk. Its name marks it as the dyes-and-fibers company; `company_basic_autarky`, whose flagship is the National Resource Depository, also displays as "Synthetics".

### Generic Building Design Principles
- **~10000 employment** (level_scaled), split across laborers/machinists/clerks
- **Simple goods I/O:** 1-2 input goods, 1 output good, modest profit margin
- **Weak state modifiers:** +5-10% throughput bonuses (half of flavored building power)
- **No prestige goods output** — these are utilitarian, not prestige buildings
- **Shared buildings OK:** Multiple companies can reference the same generic building (the `has_company` potential gate keeps them exclusive per company)

---

## Part C: Vanilla Company Updates (Mod-Exclusive Buildings & Goods)

Vanilla companies should be updated to reference mod-exclusive buildings in their `building_types` and `extension_building_types`, and mod-exclusive goods as `possible_prestige_goods` where appropriate. This is done via `INJECT:` blocks in `extra_companies_generic.txt` or a new `extra_companies_vanilla_updates.txt`.

### Flavored Company Updates

| Vanilla Company | Add to `building_types` | Add to `extension_building_types` | Add `possible_prestige_goods` |
|---|---|---|---|
| `company_krupp` | — | `building_aerospace_industry` | — |
| `company_standard_oil` | — | `building_synthetics_plant_oil`, `building_highway` | — |
| `company_us_steel` | — | `building_advanced_material_fabricator` | — |
| `company_ford_motor` | `building_automotive_industry` | `building_highway` | — |
| `company_general_electric` | `building_electrics_industry_appliances` | `building_electronic_components_and_semiconductor_industry`, `building_renewable_energy_plant` | `prestige_good_generic_consumer_appliances` |
| `company_boeing` | `building_aerospace_industry` | — | — |
| `company_siemens` | `building_electrics_industry_appliances` | `building_electronic_components_and_semiconductor_industry` | `prestige_good_generic_electronic_components` |
| `company_bayer` | — | `building_synthetics_plant_biomass` | — |
| `company_dupont` | — | `building_synthetics_plant_rubber`, `building_advanced_material_fabricator` | — |
| `company_rolls_royce` | `building_aerospace_industry` | `building_automotive_industry` | — |
| `company_bp` | — | `building_synthetics_plant_oil`, `building_renewable_energy_plant` | — |
| `company_fiat` | `building_automotive_industry` | — | — |
| `company_renault` | `building_automotive_industry` | — | — |
| `company_mitsubishi` | — | `building_aerospace_industry`, `building_electronic_components_and_semiconductor_industry` | — |
| `company_tata` | — | `building_automotive_industry`, `building_software_industry` | — |

### Generic Company Updates

| Vanilla Company | Add to `building_types` | Add to `extension_building_types` | Add `possible_prestige_goods` |
|---|---|---|---|
| `company_basic_oil` | `building_synthetics_plant_oil` | `building_highway` | — |
| `company_basic_steel` | — | `building_advanced_material_fabricator` | — |
| `company_basic_chemicals` | `building_synthetics_plant_biomass` | `building_synthetics_plant_rubber` | — |
| `company_basic_motors` | `building_automotive_industry` | `building_highway` | — |
| `company_basic_munitions` | — | `building_aerospace_industry` | — |
| `company_basic_weapons` | — | `building_aerospace_industry` | — |
| `company_basic_shipyards` | — | `building_steel_mill` | — |
| `company_basic_food` | `building_synthetics_plant_meat` | `building_synthetics_plant_sugar` | — |
| `company_basic_paper` | — | `building_software_industry` | — |
| `company_basic_textiles` | — | `building_synthetics_plant_silk` | — |
| `company_basic_fabrics` | — | `building_synthetics_plant_silk` | — |
| `company_basic_home_goods` | — | `building_electrics_industry_appliances` | `prestige_good_generic_consumer_appliances` |
| `company_basic_forestry` | — | `building_synthetics_plant_wood` | — |
| `company_basic_fishing` | — | `building_tourism_industry` | — |

---

## Implementation Phases

### Phase 1: Industrial Icons (Highest Impact) ← DONE
- **Krupp**, **Standard Oil**, **US Steel** (Carnegie), **East India Company**, **Ford Motor**
- These are the most recognizable and span the full game timeline
- 5 new flavored buildings, each with 1 PMG + 1 PM
- Also: vanilla company `INJECT:` updates for mod-exclusive buildings

### Phase 2: National Champions ← DONE
- Schneider (France), Putilov (Russia), Mitsubishi (Japan), Tata (India), Siemens (Germany)
- Regional diversity, covers major nations
- 5 buildings + company updates

### Phase 3: Specialized Industries ← DONE
- De Beers (diamonds), Nobel (oil), GE (electrical)
- Adds variety to building types beyond steel/manufacturing
- 3 buildings (Boeing/Bayer skipped — not vanilla companies)

### Phase 4: Generic Company Buildings ← DONE
- All generic buildings from Part B
- 12 generic buildings created
- Updated all vanilla generic companies with INJECT blocks + prosperity modifiers

### Phase 5: Remaining Flavored + Full Mod Integration ← DONE
- Mitsui (Japan), FIAT (Italy)
- 2 buildings (Rolls-Royce, BP, Bayer, Thyssen, DuPont, Boeing, Renault, Michelin, Pirelli, Sumitomo, Jardine Matheson skipped — not vanilla companies)
- Applied all Part C updates (mod-exclusive buildings/goods to all vanilla companies) — completed in earlier session

### Phase 8: Generic Home Goods + Forestry ← DONE
- `building_generic_furniture_showroom` (`company_basic_home_goods`) — wood + glass → furniture + services; `building_furniture_manufactory_throughput_add = 0.1`.
- `building_generic_lumber_yard` (`company_basic_forestry`) — hardwood + tools → wood + paper; `building_logging_camp_throughput_add = 0.1`.
- These were the last two `company_basic_*` companies that lacked a unique-building unlock; Phase 8 closes that gap.

### Phase 9: The Great Wave + last gaps ← DONE
- Fifteen Great Wave (DLC 018) companies: one flagship each (table in Part A). Hand-written in Sumitomo's shape; `gen_vanilla_company_buildings.py` re-appends all 164 Phase 7 companies on every run and has no per-company mode.
- `company_basic_synthetics`: `building_generic_dye_fiber_park` (Part B). Registers `building_synthetics_plant_silk_throughput_add`.
- `building_generic_hq_skyscraper` retired, leaving Telecommunications with the Electronics Laboratory alone.

---

## Phase 1 Detailed Specifications

### building_krupp_essen_works
- **Company:** `company_krupp` (Germany, arms/steel)
- **Theme:** Krupp's massive Essen steelworks — the "arsenal of the Empire"
- **State modifiers:** `building_arms_industry_throughput_add = 0.1`, `building_steel_mill_throughput_add = 0.1`
- **Country modifiers:** `unit_kill_rate_add = 0.05`
- **Goods I/O:** Input: 20 steel (1000), 10 tools (500) → Output: 30 arms (2400), 10 artillery (1200). Profit ~2100
- **Employment (2000):** 800 machinists, 600 laborers, 400 engineers, 200 clerks
- **Loc:** "Krupp Essen Works" / "The legendary Krupp steelworks in Essen, producing the finest steel and armaments in the world."

### building_standard_oil_refinery
- **Company:** `company_standard_oil` (USA, oil/rail)
- **Theme:** Standard Oil's monopolistic refinery network
- **State modifiers:** `building_oil_rig_throughput_add = 0.15`, `state_infrastructure_mult = 0.1`
- **Goods I/O:** Input: 30 oil (900) → Output: 30 fuel (1500), 20 fertilizer (600). Profit ~1200
- **Employment (2000):** 600 machinists, 600 laborers, 500 engineers, 300 clerks
- **Loc:** "Standard Oil Refinery" / "A sprawling refinery complex that dominates the petroleum industry, refining crude oil into fuel and chemicals."

### building_carnegie_homestead_mill
- **Company:** `company_us_steel` (USA, steel/iron/coal)
- **Theme:** Carnegie Steel's Homestead Works — birthplace of American steel
- **State modifiers:** `building_steel_mill_throughput_add = 0.15`, `building_railway_throughput_add = 0.05`
- **Goods I/O:** Input: 30 iron (600), 10 coal (300) → Output: 40 steel (2000). Profit ~1100
- **Employment (2000):** 800 laborers, 600 machinists, 400 engineers, 200 clerks
- **Loc:** "Carnegie Homestead Mill" / "The massive Homestead steelworks on the Monongahela River, forging the steel that built America's railways and skyscrapers."

### building_ford_rouge_plant
- **Company:** `company_ford_motor` (USA, motor/automotive)
- **Theme:** Ford's River Rouge Complex — the ultimate vertically integrated factory
- **State modifiers:** `building_motor_industry_throughput_add = 0.1`, `building_automotive_industry_throughput_add = 0.1`, `state_infrastructure_from_population_add = 5`
- **Goods I/O:** Input: 10 steel (500), 10 engines (500) → Output: 20 automobiles (2000). Profit ~1000
- **Employment (2000):** 800 machinists, 600 laborers, 400 engineers, 200 clerks
- **Loc:** "Ford Rouge Plant" / "The River Rouge Complex — the world's largest integrated factory, where raw materials enter one end and finished automobiles emerge from the other."

### building_eic_trading_house
- **Company:** `company_east_india_company` (GBR, colonial trade)
- **Theme:** East India Company's trading house — center of colonial commerce
- **State modifiers:** `state_migration_pull_mult = 0.15`, `state_trade_capacity_add = 5`, `building_port_throughput_add = 0.1`
- **Goods I/O:** Input: 10 tea (375), 10 opium (600) → Output: 50 merchant_marine (2500). Profit ~1525
- **Employment (2000):** 800 clerks, 600 shopkeepers, 400 laborers, 200 officers
- **Loc:** "East India Company Trading House" / "A grand trading house coordinating the vast commercial empire of the East India Company across the subcontinent and beyond."

## Building Design Principles

1. **Throughput focus:** Most buildings should boost throughput for the company's core industry (+10-20%)
2. **Scale matters:** Unique buildings should feel impactful — not just minor stat bumps
3. **Era-appropriate PMs:** Early buildings get basic PMs; late-game buildings can have high-tech PMs
4. **State-level effects:** Some prestige buildings could add SoL or prestige at the state level
5. **Keep it simple:** 1 PMG with 1-2 PMs max per building. Don't over-engineer.
6. **Conservative prestige goods:** Only add `possible_prestige_goods` for companies with a strong thematic link to a mod good. Most vanilla companies should NOT get mod prestige goods.

## Technical Notes

- All buildings need entries in `common/buildings/company_buildings.txt`
- Each company needs a `REPLACE:` or `INJECT:` override in a mod company file
- Each company's `prosperity_modifier` needs `state_building_X_max_level_add = 1`
- All buildings need localization in three files: `te_buildings_l_english.yml` (building + `_desc`), `te_production_methods_l_english.yml` (PM + PMG), and `te_modifiers_l_english.yml` (the `state_building_X_max_level_add` modifier — both the name and `_desc` keys, using the `[GetBuildingType('building_X').GetName] Max Level` pattern). Without modifier loc, the company's prosperity tooltip shows the raw modifier key. See `docs/guides/scripting_best_practices.md` § "Adding a Unique Company Building" for the audit command.
- Vanilla company overrides go in `common/company_types/extra_companies_vanilla_updates.txt`
- `INJECT:` adds fields to existing definitions without replacing them — use this for ALL vanilla company updates
- Each unique company building needs a `state_building_X_max_level_add` modifier_type_definition in `common/modifier_type_definitions/mod_entity_modifier_types.txt` (under the `# === State buildings ===` divider)
- **PM modifier scoping rules:** `state_modifiers` only accepts `state_*`, `building_*_throughput_add`, and `goods_output_*_mult`. `unit_*` and `country_*` modifiers must go in `country_modifiers` instead.
- **Non-existent modifiers:** `country_trade_route_quantity_mult` does not exist. Use `state_trade_capacity_add`, `state_trade_quantity_mult`, or `state_trade_advantage_mult`.
