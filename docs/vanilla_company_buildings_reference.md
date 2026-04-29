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

The mod already has:
- **53 flavored company buildings** (modern era: tech, defense, energy, etc.)
- **20 generic company buildings** (for mod-created generic company types)

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
| `company_zaibatsu_sumitomo` | `building_sumitomo_besshi_mine` | Mining/smelting complex | 1836+ |

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

**Not receiving buildings** (too niche or already covered): `company_basic_colonial_plantations_1/2`, `company_basic_silk_and_dye`, `company_basic_wine_and_fruit`, `company_basic_gold_mining`, `company_basic_metal_mining`, `company_basic_mineral_mining`, `company_basic_paper`, `company_basic_home_goods`, `company_basic_forestry`, `company_basic_electrics` (already replaced by mod).

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
- All buildings need localization (building name + desc + PM names + PMG names)
- Vanilla company overrides go in `common/company_types/extra_companies_vanilla_updates.txt`
- `INJECT:` adds fields to existing definitions without replacing them — use this for ALL vanilla company updates
- Each unique company building needs a `state_building_X_max_level_add` modifier_type_definition in `common/modifier_type_definitions/extra_modifier_types.txt`
- **PM modifier scoping rules:** `state_modifiers` only accepts `state_*`, `building_*_throughput_add`, and `goods_output_*_mult`. `unit_*` and `country_*` modifiers must go in `country_modifiers` instead.
- **Non-existent modifiers:** `country_trade_route_quantity_mult` does not exist. Use `state_trade_capacity_add`, `state_trade_quantity_mult`, or `state_trade_advantage_mult`.
