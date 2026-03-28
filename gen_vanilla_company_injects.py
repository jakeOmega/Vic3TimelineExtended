"""Generate INJECT blocks for vanilla company updates with mod-exclusive buildings."""

import os

# Each entry: (company_id, building_types_to_add, extension_building_types_to_add, prosperity_modifiers_to_add, comment)
# All fields are lists of strings. Empty list = skip that field.

PHASE1 = [
    # Already implemented - keep at the top
    ("company_krupp", ["building_krupp_essen_works"], ["building_aerospace_industry"],
     ["state_building_krupp_essen_works_max_level_add = 1"],
     "Krupp (Germany) - Adds: Essen Works building, aerospace extension"),
    ("company_standard_oil", ["building_standard_oil_refinery"], ["building_synthetics_plant_oil", "building_highway"],
     ["state_building_standard_oil_refinery_max_level_add = 1"],
     "Standard Oil (USA) - Adds: refinery building, synthetics + highway extensions"),
    ("company_us_steel", ["building_carnegie_homestead_mill"], ["building_advanced_material_fabricator"],
     ["state_building_carnegie_homestead_mill_max_level_add = 1"],
     "US Steel / Carnegie Steel (USA) - Adds: Homestead Mill, advanced materials extension"),
    ("company_ford_motor", ["building_ford_rouge_plant"], ["building_highway"],
     ["state_building_ford_rouge_plant_max_level_add = 1"],
     "Ford Motor (USA) - Adds: Rouge Plant building, highway extension"),
    ("company_east_india_company", ["building_eic_trading_house"], [],
     ["state_building_eic_trading_house_max_level_add = 1"],
     "East India Company (GBR) - Adds: Trading House building"),
]

# Flavored companies grouped by region
FLAVORED = [
    # === GERMANY ===
    ("company_rheinmetall", [], ["building_aerospace_industry"], [],
     "Rheinmetall (Germany) - artillery/munitions → aerospace extension"),
    ("company_schichau", [], ["building_aerospace_industry"], [],
     "Schichau (Germany) - shipbuilding/motors → aerospace extension"),
    ("company_siemens_and_halske", ["building_electrics_industry_appliances"],
     ["building_electronic_components_and_semiconductor_industry", "building_software_industry", "building_network_infrastructure"], [],
     "Siemens (Germany) - electrics pioneer → appliances, semiconductors, software, network infra"),
    ("company_prussian_state_railways", [], ["building_highway"], [],
     "Prussian State Railways (Germany) - railways → highway extension"),
    ("company_basf", [], ["building_synthetics_plant_biomass", "building_advanced_material_fabricator"], [],
     "BASF (Germany) - chemicals → bio-synthetics, advanced materials"),

    # === GREAT BRITAIN ===
    ("company_j_p_coats", [], ["building_synthetics_plant_silk"], [],
     "J&P Coats (GBR) - textiles → synthetic silk extension"),
    ("company_armstrong_whitworth", [], ["building_aerospace_industry"], [],
     "Armstrong Whitworth (GBR) - military shipyard/munitions → aerospace"),
    ("company_bolckow_vaughan", [], ["building_advanced_material_fabricator"], [],
     "Bolckow Vaughan (GBR) - steel → advanced materials extension"),
    ("company_gwr", [], ["building_highway"], [],
     "Great Western Railway (GBR) - railways → highway extension"),

    # === USA ===
    ("company_general_electric", ["building_electrics_industry_appliances"],
     ["building_electronic_components_and_semiconductor_industry", "building_renewable_energy_plant", "building_software_industry"], [],
     "General Electric (USA) - electrics/power → appliances, semiconductors, renewables, software"),
    ("company_united_fruit", [], ["building_synthetics_plant_sugar"], [],
     "United Fruit (USA) - sugar plantations → synthetic sugar extension"),
    ("company_william_cramp", [], ["building_aerospace_industry"], [],
     "William Cramp & Sons (USA) - military shipyard → aerospace extension"),
    ("company_colt_firearms", [], ["building_aerospace_industry"], [],
     "Colt Firearms (USA) - arms → aerospace extension"),

    # === FRANCE ===
    ("company_schneider_creusot", [], ["building_aerospace_industry", "building_highway"], [],
     "Schneider-Creusot (France) - steel/artillery/motor → aerospace, highway"),
    ("company_saint_etienne", [], ["building_aerospace_industry"], [],
     "Saint-Etienne (France) - arms/artillery → aerospace extension"),
    ("company_fcm", [], ["building_aerospace_industry"], [],
     "FCM (France) - shipyard/automotive → aerospace extension"),
    ("company_dmc", [], ["building_synthetics_plant_silk"], [],
     "DMC (France) - textiles → synthetic silk extension"),
    ("company_cgv", [], ["building_tourism_industry"], [],
     "CGV (France) - vineyard/food → tourism extension"),

    # === RUSSIA ===
    ("company_putilov_company", [], ["building_aerospace_industry", "building_highway"], [],
     "Putilov (Russia) - motor/military → aerospace, highway"),
    ("company_branobel", [], ["building_synthetics_plant_oil"], [],
     "Nobel Brothers (Russia) - oil → synthetic oil extension"),
    ("company_izhevsk_arms_plant", [], ["building_aerospace_industry"], [],
     "Izhevsk Arms Plant (Russia) - arms/munitions → aerospace extension"),
    ("company_savva_morozov", [], ["building_synthetics_plant_silk"], [],
     "Savva Morozov (Russia) - textiles → synthetic silk extension"),
    ("company_john_hughes", [], ["building_advanced_material_fabricator"], [],
     "John Hughes (Russia) - steel/coal → advanced materials extension"),

    # === ITALY ===
    ("company_fiat", [], ["building_highway", "building_aerospace_industry"], [],
     "FIAT (Italy) - motor/automotive → highway, aerospace"),
    ("company_ilva", [], ["building_advanced_material_fabricator"], [],
     "ILVA (Italy) - steel → advanced materials extension"),
    ("company_ansaldo", [], ["building_aerospace_industry"], [],
     "Ansaldo (Italy) - artillery/steel/military shipyard → aerospace extension"),
    ("company_ricordi", [], ["building_tourism_industry"], [],
     "Ricordi (Italy) - art/culture → tourism extension"),

    # === JAPAN ===
    ("company_mitsubishi", [], ["building_aerospace_industry", "building_electronic_components_and_semiconductor_industry"], [],
     "Mitsubishi (Japan) - heavy industry → aerospace, semiconductors"),
    ("company_mitsui", [], ["building_software_industry"], [],
     "Mitsui (Japan) - trading conglomerate → software extension"),
    ("company_mantetsu", [], ["building_highway"], [],
     "Mantetsu (Japan) - railways → highway extension"),

    # === AUSTRIA-HUNGARY ===
    ("company_skoda", [], ["building_aerospace_industry", "building_highway"], [],
     "Skoda (Austria-Hungary) - steel/motor/artillery → aerospace, highway"),
    ("company_mav", [], ["building_highway"], [],
     "MAV (Austria-Hungary) - motor/tooling → highway extension"),
    ("company_manfred_weiss", [], ["building_aerospace_industry"], [],
     "Manfred Weiss (Austria-Hungary) - steel/munitions → aerospace extension"),
    ("company_galician_carpathian_oil", [], ["building_synthetics_plant_oil"], [],
     "Galician Carpathian Oil (Austria-Hungary) - oil → synthetic oil extension"),
    ("company_oevg", [], ["building_aerospace_industry"], [],
     "OEVG (Austria-Hungary) - arms/artillery → aerospace extension"),
    ("company_oesterreichisch_alpine_montangesellschaft", [], ["building_advanced_material_fabricator"], [],
     "Oesterreichisch-Alpine (Austria-Hungary) - steel → advanced materials"),

    # === CHINA ===
    ("company_kaiping_mining", [], ["building_highway"], [],
     "Kaiping Mining (China) - coal/railway → highway extension"),
    ("company_hanyang_arsenal", [], ["building_aerospace_industry"], [],
     "Hanyang Arsenal (China) - arms/munitions → aerospace extension"),
    ("company_foochow_arsenal", [], ["building_aerospace_industry"], [],
     "Foochow Arsenal (China) - shipyard/military → aerospace extension"),

    # === INDIA ===
    ("company_tata", [], ["building_automotive_industry", "building_software_industry", "building_advanced_material_fabricator"], [],
     "Tata (India) - steel/textiles → automotive, software, advanced materials"),
    ("company_great_indian_railway", [], ["building_highway"], [],
     "Great Indian Railway (India) - railways → highway extension"),
    ("company_wadia_shipbuilders", [], ["building_aerospace_industry"], [],
     "Wadia Shipbuilders (India) - shipyard → aerospace extension"),
    ("company_calcutta_electric", [], ["building_renewable_energy_plant"], [],
     "Calcutta Electric (India) - power → renewables extension"),
    ("company_bombay_dyeing_company", [], ["building_synthetics_plant_silk"], [],
     "Bombay Dyeing (India) - textiles → synthetic silk extension"),
    ("company_bombay_burmah_trading_corporation", [], ["building_synthetics_plant_rubber"], [],
     "Bombay Burmah (India) - rubber/logging → synthetic rubber extension"),

    # === SCANDINAVIA ===
    ("company_ericsson", [], ["building_electronic_components_and_semiconductor_industry", "building_software_industry", "building_network_infrastructure"], [],
     "Ericsson (Sweden) - electrics → semiconductors, software, network infra"),
    ("company_nokia", ["building_software_industry"],
     ["building_electronic_components_and_semiconductor_industry", "building_network_infrastructure"], [],
     "Nokia (Finland) - paper/electrics → software, semiconductors, network infra"),
    ("company_norsk_hydro", [], ["building_renewable_energy_plant", "building_synthetics_plant_biomass"], [],
     "Norsk Hydro (Norway) - chemicals/power → renewables, bio-synthetics"),
    ("company_gotaverken", [], ["building_aerospace_industry"], [],
     "Gotaverken (Sweden) - shipyard/motor → aerospace extension"),

    # === EUROPE (OTHER) ===
    ("company_philips", ["building_electrics_industry_appliances"],
     ["building_electronic_components_and_semiconductor_industry", "building_software_industry"], [],
     "Philips (Netherlands) - electrics → appliances, semiconductors, software"),
    ("company_franco_belge", [], ["building_highway", "building_automotive_industry"], [],
     "Franco-Belge (Belgium) - motor/railway → highway, automotive"),
    ("company_john_cockerill", [], ["building_advanced_material_fabricator"], [],
     "John Cockerill (Belgium) - steel/tooling → advanced materials"),
    ("company_nederlandse_petroleum", [], ["building_synthetics_plant_oil"], [],
     "Nederlandse Petroleum (Netherlands) - oil → synthetic oil extension"),
    ("company_ursus", [], ["building_highway"], [],
     "Ursus (Poland) - motor/automotive → highway extension"),
    ("company_lilpop", [], ["building_advanced_material_fabricator"], [],
     "Lilpop (Poland) - steel/iron/tooling → advanced materials"),
    ("company_altos_hornos_de_vizcaya", [], ["building_advanced_material_fabricator"], [],
     "Altos Hornos (Spain) - steel → advanced materials extension"),
    ("company_trubia", [], ["building_aerospace_industry"], [],
     "Trubia (Spain) - arms/artillery → aerospace extension"),
    ("company_zastava", [], ["building_aerospace_industry"], [],
     "Zastava (Serbia) - arms/munitions → aerospace extension"),
    ("company_espana_industrial", [], ["building_synthetics_plant_silk"], [],
     "Espana Industrial (Spain) - textiles → synthetic silk extension"),
    ("company_chr_hansens", [], ["building_synthetics_plant_biomass"], [],
     "Chr. Hansen (Denmark) - food/chemicals → bio-synthetics extension"),
    ("company_cfr", [], ["building_highway"], [],
     "CFR (Romania) - railways → highway extension"),
    ("company_romanian_star", [], ["building_synthetics_plant_oil"], [],
     "Romanian Star (Romania) - oil → synthetic oil extension"),

    # === IBERIA ===
    ("company_secn", [], ["building_aerospace_industry"], [],
     "SECN (Spain) - military shipyard → aerospace extension"),
    ("company_hispano_suiza", [], ["building_highway", "building_aerospace_industry"], [],
     "Hispano-Suiza (Spain) - automotive → highway, aerospace"),
    ("company_douro_wine_company", [], ["building_tourism_industry"], [],
     "Douro Wine (Portugal) - vineyard → tourism extension"),
    ("company_pedro_domecq", [], ["building_tourism_industry"], [],
     "Pedro Domecq (Spain) - vineyard → tourism extension"),
    ("company_bacardi", [], ["building_tourism_industry"], [],
     "Bacardi (Cuba/Spain) - food/drinks → tourism extension"),
    ("company_gran_azucarera", [], ["building_synthetics_plant_sugar"], [],
     "Gran Azucarera (Spain) - sugar → synthetic sugar extension"),
    ("company_office_cherifien_des_phosphates", [], ["building_synthetics_plant_biomass"], [],
     "OCP (Morocco) - sulfur/chemical → bio-synthetics extension"),
    ("company_uniao_fabril", [], ["building_synthetics_plant_biomass"], [],
     "Uniao Fabril (Portugal) - chemicals → bio-synthetics extension"),

    # === AFRICA ===
    ("company_misr", [], ["building_synthetics_plant_silk"], [],
     "Misr (Egypt) - textiles → synthetic silk extension"),
    ("company_egyptian_rail", [], ["building_highway"], [],
     "Egyptian Rail (Egypt) - railways → highway extension"),
    ("company_suez_company", [], ["building_tourism_industry"], [],
     "Suez Company (Egypt) - trade/port → tourism extension"),

    # === AMERICAS (NON-USA) ===
    ("company_fundidora_monterrey", [], ["building_advanced_material_fabricator"], [],
     "Fundidora Monterrey (Mexico) - steel → advanced materials extension"),
    ("company_el_aguila", [], ["building_synthetics_plant_oil", "building_highway"], [],
     "El Aguila (Mexico) - oil → synthetic oil, highway"),
    ("company_caribbean_petroleum", [], ["building_synthetics_plant_oil"], [],
     "Caribbean Petroleum (Venezuela) - oil → synthetic oil extension"),
    ("company_la_rosada", [], ["building_aerospace_industry"], [],
     "La Rosada (Argentina) - steel/arms → aerospace extension"),
    ("company_famae", [], ["building_aerospace_industry"], [],
     "FAMAE (Chile) - arms/munitions → aerospace extension"),
    ("company_peruvian_amazon", [], ["building_synthetics_plant_rubber"], [],
     "Peruvian Amazon (Peru) - rubber → synthetic rubber extension"),
    ("company_sao_paulo_railway", [], ["building_highway"], [],
     "Sao Paulo Railway (Brazil) - railways → highway extension"),
    ("company_fundicao_ipanema", [], ["building_advanced_material_fabricator"], [],
     "Fundicao Ipanema (Brazil) - steel → advanced materials extension"),
    ("company_cordoba_railway", [], ["building_highway"], [],
     "Cordoba Railway (Argentina) - railways → highway extension"),
    ("company_electricidad_de_caracas", [], ["building_renewable_energy_plant"], [],
     "Electricidad de Caracas (Venezuela) - power → renewables extension"),
    ("company_eea", [], ["building_renewable_energy_plant"], [],
     "EEA (Argentina) - power → renewables extension"),
    ("company_panama_company", [], ["building_tourism_industry"], [],
     "Panama Company (Panama) - trade/port → tourism extension"),

    # === SOI ===
    ("company_da_afghan_nassaji_sherkat", [], ["building_synthetics_plant_silk"], [],
     "Afghan Nassaji (Afghanistan) - textiles → synthetic silk extension"),
    ("company_iranian_state_railway", [], ["building_highway"], [],
     "Iranian State Railway (Iran) - railways → highway extension"),
    ("company_tashkent_railroad", [], ["building_highway"], [],
     "Tashkent Railroad (Central Asia) - railways → highway extension"),
    ("company_west_ural_petroleum", [], ["building_synthetics_plant_oil"], [],
     "West Ural Petroleum (Russia/CA) - oil → synthetic oil extension"),
    ("company_anglo_persian_oil", [], ["building_synthetics_plant_oil"], [],
     "Anglo-Persian Oil (Iran) - oil → synthetic oil extension"),
    ("company_turkish_petroleum", [], ["building_synthetics_plant_oil"], [],
     "Turkish Petroleum (Ottoman) - oil → synthetic oil extension"),

    # === BRAZIL/COTS MISC ===
    ("company_pernambuco_textiles", [], ["building_synthetics_plant_silk"], [],
     "Pernambuco Textiles (Brazil) - textiles → synthetic silk extension"),
    ("company_ccci", [], ["building_synthetics_plant_rubber"], [],
     "CCCI (Belgium/Congo) - rubber → synthetic rubber extension"),

    # === IP3 ===
    ("company_stabilimento_tecnico_di_fiume", [], ["building_aerospace_industry"], [],
     "Stabilimento Tecnico (Fiume) - motor/military_shipyard → aerospace extension"),
    ("company_getzner_mutter", [], ["building_synthetics_plant_silk"], [],
     "Getzner Mutter (Austria) - textiles → synthetic silk extension"),

    # === ORIENT ===
    ("company_orient_express", [], ["building_highway", "building_tourism_industry"], [],
     "Orient Express (Ottoman) - railways → highway, tourism"),

    # === MP1 MISC ===
    ("company_massey_harris", [], ["building_highway"], [],
     "Massey-Harris (Canada) - motor/tooling → highway extension"),
]

# Generic companies
GENERIC = [
    ("company_basic_oil", ["building_synthetics_plant_oil"], ["building_highway"], [],
     "Generic Oil - adds synthetic oil production, highway extension"),
    ("company_basic_steel", [], ["building_advanced_material_fabricator"], [],
     "Generic Steel - adds advanced materials extension"),
    ("company_basic_chemicals", ["building_synthetics_plant_biomass"], ["building_synthetics_plant_rubber"], [],
     "Generic Chemicals - adds bio-synthetics production, synthetic rubber extension"),
    ("company_basic_motors", [], ["building_highway"], [],
     "Generic Motors - adds highway extension"),
    ("company_basic_munitions", [], ["building_aerospace_industry"], [],
     "Generic Munitions - adds aerospace extension"),
    ("company_basic_weapons", [], ["building_aerospace_industry"], [],
     "Generic Weapons - adds aerospace extension"),
    ("company_basic_textiles", [], ["building_synthetics_plant_silk"], [],
     "Generic Textiles - adds synthetic silk extension"),
    ("company_basic_fabrics", [], ["building_synthetics_plant_silk"], [],
     "Generic Fabrics - adds synthetic silk extension"),
    ("company_basic_food", [], ["building_synthetics_plant_meat", "building_synthetics_plant_sugar"], [],
     "Generic Food - adds synthetic meat/sugar extensions"),
    ("company_basic_paper", [], ["building_software_industry"], [],
     "Generic Paper - adds software industry extension"),
    ("company_basic_home_goods", [], ["building_electrics_industry_appliances"], [],
     "Generic Home Goods - adds appliances extension"),
    ("company_basic_forestry", [], ["building_synthetics_plant_wood"], [],
     "Generic Forestry - adds synthetic wood extension"),
    ("company_basic_fishing", [], ["building_tourism_industry"], [],
     "Generic Fishing - adds tourism extension"),
    ("company_basic_shipyards", [], ["building_aerospace_industry"], [],
     "Generic Shipyards - adds aerospace extension"),
]


def generate_inject_block(company_id, building_types, extension_building_types, prosperity_modifiers, comment):
    lines = []
    lines.append(f"# {comment}")
    lines.append(f"INJECT:{company_id} = {{")
    if building_types:
        lines.append("\tbuilding_types = {")
        for bt in building_types:
            lines.append(f"\t\t{bt}")
        lines.append("\t}")
    if extension_building_types:
        lines.append("\textension_building_types = {")
        for ebt in extension_building_types:
            lines.append(f"\t\t{ebt}")
        lines.append("\t}")
    if prosperity_modifiers:
        lines.append("\tprosperity_modifier = {")
        for pm in prosperity_modifiers:
            lines.append(f"\t\t{pm}")
        lines.append("\t}")
    lines.append("}")
    return "\n".join(lines)


def main():
    output_lines = []
    output_lines.append("# Vanilla Company Updates")
    output_lines.append("# Adds mod-exclusive buildings to vanilla flavored and generic companies via INJECT")
    output_lines.append("# INJECT appends new entries to existing fields without replacing the entire definition")
    output_lines.append("")
    output_lines.append("#" + "=" * 60)
    output_lines.append("# Phase 1: Flavored Company Buildings")
    output_lines.append("#" + "=" * 60)
    output_lines.append("")

    for entry in PHASE1:
        output_lines.append(generate_inject_block(*entry))
        output_lines.append("")

    output_lines.append("#" + "=" * 60)
    output_lines.append("# Flavored Companies: Mod-Exclusive Building Extensions")
    output_lines.append("#" + "=" * 60)
    output_lines.append("")

    for entry in FLAVORED:
        output_lines.append(generate_inject_block(*entry))
        output_lines.append("")

    output_lines.append("#" + "=" * 60)
    output_lines.append("# Generic Companies: Mod-Exclusive Building Extensions")
    output_lines.append("#" + "=" * 60)
    output_lines.append("")

    for entry in GENERIC:
        output_lines.append(generate_inject_block(*entry))
        output_lines.append("")

    content = "\n".join(output_lines)

    mod_root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(mod_root, "common", "company_types", "extra_companies_vanilla_updates.txt")

    import codecs
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write(content)

    # Count entries
    total = len(PHASE1) + len(FLAVORED) + len(GENERIC)
    print(f"Generated {total} INJECT blocks to {out_path}")
    print(f"  Phase 1: {len(PHASE1)}")
    print(f"  Flavored: {len(FLAVORED)}")
    print(f"  Generic: {len(GENERIC)}")


if __name__ == "__main__":
    main()
