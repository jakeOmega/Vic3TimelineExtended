<!-- Auto-generated from modifiers.log + common/_meta/modifier_patterns.yml (modifiers.log @ 2026-05-29T02:49:10+00:00). Do not hand-edit. Run POST /reload after the engine regenerates the source. -->

# Modifier Patterns

Dynamic-modifier templates parameterized over canonical vocabularies (goods, buildings, IGs, etc.). The catalog in `common/_meta/modifier_patterns.yml` lists patterns we guarantee tracking; the discovery pass below extends that with patterns inferred from engine docs.

## Catalog (34 patterns)

### `building_group_bg_{bg}_employee_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **69**
- Vocab size: 155; missing entries: 86

### `building_group_bg_{bg}_expected_sol_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **0**
- Vocab size: 155; missing entries: 155

### `building_group_bg_{bg}_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **69**
- Vocab size: 155; missing entries: 86

### `building_group_bg_{bg}_tax_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **69**
- Vocab size: 155; missing entries: 86

### `building_group_bg_{bg}_throughput_add`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **70**
- Vocab size: 155; missing entries: 85

### `building_group_bg_{bg}_throughput_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **0**
- Vocab size: 155; missing entries: 155

### `building_group_bg_{bg}_urbanization_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **0**
- Vocab size: 155; missing entries: 155

### `building_group_bg_{bg}_wages_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members in engine docs: **0**
- Vocab size: 155; missing entries: 155

### `building_{building}_employees_add`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `building_{building}_employees_mult`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `building_{building}_max_level_add`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `building_{building}_mortality_mult`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `building_{building}_throughput_add`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **148**
- Vocab size: 1021; missing entries: 873

### `building_{building}_throughput_mult`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `building_{building}_unincorporated_throughput_add`

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **0**
- Vocab size: 1021; missing entries: 1021

### `country_institution_impact_{institution}_mult`

- Placeholder: `institution` (vocab: `institution`)
- Members in engine docs: **11**
- Vocab size: 48; missing entries: 37

### `country_{combat_unit_group}_max_size_mult`

- Placeholder: `combat_unit_group` (vocab: `combat_unit_group`)
- Members in engine docs: **0**
- Vocab size: 12; missing entries: 12
  - Missing values: `aircraft`, `artillery`, `cavalry`, `combat_unit_group_aircraft`, `combat_unit_group_artillery`, `combat_unit_group_cavalry`, `combat_unit_group_infantry`, `combat_unit_group_marines`, `combat_unit_group_tanks`, `infantry`, `marines`, `tanks`

### `country_{culture}_pop_attraction_mult`

_Per-culture migration pull modifier; instantiated for every culture used in modifiers._

- Placeholder: `culture` (vocab: `culture`)
- Members in engine docs: **0**
- Vocab size: 317; missing entries: 317

### `goods_input_{good}_add`

_Extra flat input consumption of a specific good._

- Placeholder: `good` (vocab: `good`)
- Members in engine docs: **64**
- Vocab size: 65; missing entries: 1
  - Missing values: `tourism`

### `goods_input_{good}_mult`

- Placeholder: `good` (vocab: `good`)
- Members in engine docs: **54**
- Vocab size: 65; missing entries: 11
  - Missing values: `advanced_materials`, `consumer_appliances`, `digital_access`, `digital_assets`, `electronic_components`, `launch_capacity`, `magnetic_drive_ships`, `motor_ships`, `robotics`, `tech_metals`, `tourism`

### `goods_output_{good}_add`

_Flat additive to the output of a specific good across the economy._

- Placeholder: `good` (vocab: `good`)
- Members in engine docs: **65**
- Vocab size: 65; missing entries: 0

### `goods_output_{good}_mult`

_Multiplicative bonus to a specific good's output._

- Placeholder: `good` (vocab: `good`)
- Members in engine docs: **65**
- Vocab size: 65; missing entries: 0

### `goods_sales_tax_{good}_add`

- Placeholder: `good` (vocab: `good`)
- Members in engine docs: **0**
- Vocab size: 65; missing entries: 65

### `interest_group_ig_{ig}_approval_add`

- Placeholder: `ig` (vocab: `ig`)
- Members in engine docs: **8**
- Vocab size: 16; missing entries: 8
  - Missing values: `ig_armed_forces`, `ig_devout`, `ig_industrialists`, `ig_intelligentsia`, `ig_landowners`, `ig_petty_bourgeoisie`, `ig_rural_folk`, `ig_trade_unions`

### `interest_group_ig_{ig}_pol_str_mult`

- Placeholder: `ig` (vocab: `ig`)
- Members in engine docs: **8**
- Vocab size: 16; missing entries: 8
  - Missing values: `ig_armed_forces`, `ig_devout`, `ig_industrialists`, `ig_intelligentsia`, `ig_landowners`, `ig_petty_bourgeoisie`, `ig_rural_folk`, `ig_trade_unions`

### `interest_group_ig_{ig}_pop_attraction_mult`

- Placeholder: `ig` (vocab: `ig`)
- Members in engine docs: **8**
- Vocab size: 16; missing entries: 8
  - Missing values: `ig_armed_forces`, `ig_devout`, `ig_industrialists`, `ig_intelligentsia`, `ig_landowners`, `ig_petty_bourgeoisie`, `ig_rural_folk`, `ig_trade_unions`

### `pop_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members in engine docs: **0**
- Vocab size: 15; missing entries: 15
  - Missing values: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `slaves`, `soldiers`

### `pop_{poptype}_political_strength_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members in engine docs: **0**
- Vocab size: 15; missing entries: 15
  - Missing values: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `slaves`, `soldiers`

### `state_building_{building}_max_level_add`

_State-scoped cap on a specific building's level._

- Placeholder: `building` (vocab: `building`)
- Members in engine docs: **300**
- Vocab size: 1021; missing entries: 721

### `state_pop_qualifications_{poptype}_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members in engine docs: **0**
- Vocab size: 15; missing entries: 15
  - Missing values: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `slaves`, `soldiers`

### `state_pop_type_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members in engine docs: **0**
- Vocab size: 15; missing entries: 15
  - Missing values: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`, `engineers`, `farmers`, `laborers`, `machinists`, `officers`, `peasants`, `shopkeepers`, `slaves`, `soldiers`

### `unit_{combat_unit}_defense_add`

- Placeholder: `combat_unit` (vocab: `combat_unit`)
- Members in engine docs: **0**
- Vocab size: 88; missing entries: 88

### `unit_{combat_unit}_morale_loss_mult`

- Placeholder: `combat_unit` (vocab: `combat_unit`)
- Members in engine docs: **0**
- Vocab size: 88; missing entries: 88

### `unit_{combat_unit}_offense_add`

- Placeholder: `combat_unit` (vocab: `combat_unit`)
- Members in engine docs: **3**
- Vocab size: 88; missing entries: 85

## Discovered (not yet in catalog) — 140 patterns

These patterns were auto-detected by matching engine modifiers against loaded vocabulary values. Review and promote desired ones into `common/_meta/modifier_patterns.yml`.

### `building_annual_{building}_progress`

- Placeholder: `building` (vocab: `building`)
- Members: **7**
  - Examples: `antimatter_facility`, `consciousness_network`, `mind_upload_nexus`, `nanofabrication_center`, `orbital_battlestation`, `solar_collector`

### `building_employment_{poptype}_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_employment_{poptype}_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_group_bg_army_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_army_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_army_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_arts_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_arts_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_arts_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_canals_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_canals_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_canals_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_fishing_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_fishing_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_fishing_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_logging_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_logging_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_logging_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_mining_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_mining_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_mining_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_navy_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_navy_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_navy_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **12**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_power_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_power_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_power_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_rubber_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_rubber_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_rubber_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **5**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `machinists`, `shopkeepers`

### `building_group_bg_service_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_service_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_service_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_trade_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_trade_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_trade_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **8**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `engineers`

### `building_group_bg_whaling_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_whaling_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_bg_whaling_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **4**
  - Examples: `aristocrats`, `bureaucrats`, `capitalists`, `shopkeepers`

### `building_group_{bg}_academics_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_academics_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_academics_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_allowed_collectivization_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **14**
  - Examples: `bg_agriculture`, `bg_arts`, `bg_extraction`, `bg_heavy_industry`, `bg_light_industry`, `bg_manufacturing`

### `building_group_{bg}_aristocrats_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_aristocrats_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_aristocrats_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_bureaucrats_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_bureaucrats_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_bureaucrats_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_capitalists_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_capitalists_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_capitalists_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_clergymen_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_clergymen_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_clergymen_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_clerks_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_clerks_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_clerks_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_construction_efficiency_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **9**
  - Examples: `bg_agriculture`, `bg_extraction`, `bg_government`, `bg_heavy_industry`, `bg_infrastructure`, `bg_light_industry`

### `building_group_{bg}_engineers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_engineers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_engineers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **64**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_farmers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_farmers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_farmers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_infrastructure_usage_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **42**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coffee_plantations`, `bg_company_headquarter`, `bg_company_regional_headquarter`

### `building_group_{bg}_laborers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_laborers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_laborers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_machinists_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **61**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_machinists_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **61**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_machinists_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **61**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_officers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_officers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_officers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_peasants_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_peasants_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_peasants_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_self_investment_chance_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_shopkeepers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_shopkeepers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_shopkeepers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **57**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_coal_mining`, `bg_coffee_plantations`, `bg_company_headquarter`

### `building_group_{bg}_slaves_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_slaves_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_slaves_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_soldiers_fertility_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_soldiers_mortality_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_soldiers_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **66**
  - Examples: `bg_agriculture`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`, `bg_coal_mining`, `bg_coffee_plantations`

### `building_group_{bg}_standard_of_living_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_group_{bg}_unincorporated_throughput_add`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `building_total_{building}_progress`

- Placeholder: `building` (vocab: `building`)
- Members: **7**
  - Examples: `antimatter_facility`, `consciousness_network`, `mind_upload_nexus`, `nanofabrication_center`, `orbital_battlestation`, `solar_collector`

### `building_{poptype}_fertility_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_{poptype}_job_attractiveness_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_{poptype}_shares_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_{poptype}_shares_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `building_{poptype}_standard_of_living_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `country_can_impose_same_{law_group}_in_power_bloc_bool`

- Placeholder: `law_group` (vocab: `law_group`)
- Members: **10**
  - Examples: `lawgroup_army_model`, `lawgroup_church_and_state`, `lawgroup_citizenship`, `lawgroup_colonization`, `lawgroup_distribution_of_power`, `lawgroup_education_system`

### `country_disallow_{law}_bool`

- Placeholder: `law` (vocab: `law`)
- Members: **3**
  - Examples: `law_no_colonial_affairs`, `law_no_police`, `law_no_schools`

### `country_enactment_success_chance_{law}_add`

- Placeholder: `law` (vocab: `law`)
- Members: **147**
  - Examples: `law_affirmative_action`, `law_agrarianism`, `law_anarchy`, `law_anti_strike_laws`, `law_appointed_bureaucrats`, `law_autocracy`

### `country_enactment_time_{law}_mult`

- Placeholder: `law` (vocab: `law`)
- Members: **6**
  - Examples: `law_anarchy`, `law_autocracy`, `law_oligarchy`, `law_public_schools`, `law_single_party_state`, `law_technocracy`

### `country_fervor_target_{culture}_add`

- Placeholder: `culture` (vocab: `culture`)
- Members: **316**
  - Examples: `aborigine`, `afar`, `afro_american`, `afro_antillean`, `afro_brazilian`, `afro_caribbean`

### `country_institution_cost_{institution}_mult`

- Placeholder: `institution` (vocab: `institution`)
- Members: **18**
  - Examples: `institution_colonial_affairs`, `institution_health_system`, `institution_home_affairs`, `institution_migration_controls`, `institution_ministry_of_commerce`, `institution_ministry_of_consumer_protection`

### `country_institution_size_change_speed_{institution}_mult`

- Placeholder: `institution` (vocab: `institution`)
- Members: **4**
  - Examples: `institution_colonial_affairs`, `institution_ministry_of_the_environment`, `institution_police`, `institution_schools`

### `country_st_res_{good}_capacity_add`

- Placeholder: `good` (vocab: `good`)
- Members: **7**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `grain`, `oil`, `small_arms`

### `country_st_res_{good}_decay_add`

- Placeholder: `good` (vocab: `good`)
- Members: **7**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `grain`, `oil`, `small_arms`

### `country_{bg}_goods_cost_mult`

- Placeholder: `bg` (vocab: `bg`)
- Members: **3**
  - Examples: `military`, `navy`, `ship_construction`

### `country_{bg}_require_subsidies_bool`

- Placeholder: `bg` (vocab: `bg`)
- Members: **69**
  - Examples: `bg_agriculture`, `bg_army`, `bg_arts`, `bg_banana_plantations`, `bg_bureaucracy`, `bg_canals`

### `country_{building}_require_subsidies_bool`

- Placeholder: `building` (vocab: `building`)
- Members: **117**
  - Examples: `building_airport`, `building_angkor_wat`, `building_argebam`, `building_arms_industry`, `building_art_academy`, `building_artillery_foundry`

### `country_{culture}_cultural_acceptance_add`

- Placeholder: `culture` (vocab: `culture`)
- Members: **316**
  - Examples: `aborigine`, `afar`, `afro_american`, `afro_antillean`, `afro_brazilian`, `afro_caribbean`

### `country_{good}_export_tariffs_rate_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{good}_import_tariffs_rate_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{good}_max_export_tariffs_level_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{good}_max_import_tariffs_level_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{good}_min_export_tariffs_level_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{good}_min_import_tariffs_level_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `country_{institution}_max_investment_add`

- Placeholder: `institution` (vocab: `institution`)
- Members: **24**
  - Examples: `institution_colonial_affairs`, `institution_health_system`, `institution_home_affairs`, `institution_migration_controls`, `institution_ministry_of_commerce`, `institution_ministry_of_consumer_protection`

### `country_{poptype}_pol_str_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `country_{poptype}_voting_power_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `country_{tech}_pb_principles_bool`

- Placeholder: `tech` (vocab: `tech`)
- Members: **22**
  - Examples: `combined_arms`, `containerization`, `decolonization`, `gene_splicing`, `globalization`, `green_revolution`

### `goods_trade_advantage_{good}_mult`

- Placeholder: `good` (vocab: `good`)
- Members: **42**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `power_bloc_invite_acceptance_{country_rank}_add`

- Placeholder: `country_rank` (vocab: `country_rank`)
- Members: **8**
  - Examples: `decentralized_power`, `great_power`, `insignificant_power`, `major_power`, `minor_power`, `unrecognized_major_power`

### `power_bloc_mandate_progress_per_{country_rank}_member_add`

- Placeholder: `country_rank` (vocab: `country_rank`)
- Members: **8**
  - Examples: `decentralized_power`, `great_power`, `insignificant_power`, `major_power`, `minor_power`, `unrecognized_major_power`

### `power_bloc_mandate_progress_per_{country_rank}_member_mult`

- Placeholder: `country_rank` (vocab: `country_rank`)
- Members: **8**
  - Examples: `decentralized_power`, `great_power`, `insignificant_power`, `major_power`, `minor_power`, `unrecognized_major_power`

### `state_buy_orders_{good}_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `state_infrastructure_from_{good}_consumption_add`

- Placeholder: `good` (vocab: `good`)
- Members: **4**
  - Examples: `luxury_clothes`, `luxury_furniture`, `merchant_marine`, `transportation`

### `state_pop_support_movement_{ideology}_add`

- Placeholder: `ideology` (vocab: `ideology`)
- Members: **19**
  - Examples: `anarchist`, `anti_slavery`, `bonapartist`, `carlist`, `communist`, `corporatist`

### `state_pop_support_movement_{ideology}_mult`

- Placeholder: `ideology` (vocab: `ideology`)
- Members: **19**
  - Examples: `anarchist`, `anti_slavery`, `bonapartist`, `carlist`, `communist`, `corporatist`

### `state_sell_orders_{good}_add`

- Placeholder: `good` (vocab: `good`)
- Members: **53**
  - Examples: `aeroplanes`, `ammunition`, `artillery`, `automobiles`, `clippers`, `clothes`

### `state_{culture}_standard_of_living_add`

- Placeholder: `culture` (vocab: `culture`)
- Members: **316**
  - Examples: `aborigine`, `afar`, `afro_american`, `afro_antillean`, `afro_brazilian`, `afro_caribbean`

### `state_{poptype}_dependent_wage_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{poptype}_internal_migration_disallowed_bool`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{poptype}_investment_pool_contribution_add`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{poptype}_investment_pool_efficiency_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{poptype}_mass_migration_disallowed_bool`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{poptype}_mortality_mult`

- Placeholder: `poptype` (vocab: `poptype`)
- Members: **15**
  - Examples: `academics`, `aristocrats`, `bureaucrats`, `capitalists`, `clergymen`, `clerks`

### `state_{religion}_standard_of_living_add`

- Placeholder: `religion` (vocab: `religion`)
- Members: **17**
  - Examples: `animist`, `atheist`, `catholic`, `confucian`, `gelugpa`, `hindu`

### `unit_{combat_unit}_defense_mult`

- Placeholder: `combat_unit` (vocab: `combat_unit`)
- Members: **4**
  - Examples: `combat_unit_type_jet_powered_fighters`, `combat_unit_type_orbital_tactical_vehicles`, `combat_unit_type_orbital_weapons_platforms`, `combat_unit_type_stealth_aircraft`

### `unit_{combat_unit}_offense_mult`

- Placeholder: `combat_unit` (vocab: `combat_unit`)
- Members: **9**
  - Examples: `combat_unit_type_cannon_artillery`, `combat_unit_type_heavy_tank`, `combat_unit_type_jet_powered_fighters`, `combat_unit_type_mobile_artillery`, `combat_unit_type_orbital_tactical_vehicles`, `combat_unit_type_orbital_weapons_platforms`

