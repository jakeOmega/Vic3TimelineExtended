"""
Generate unique buildings for all remaining vanilla flavored companies.

For each vanilla flavored company that doesn't already have a unique building,
this script:
1. Reads the vanilla company definition to determine its sector/building_types
2. Generates an appropriate unique building name and themed PM
3. Outputs: building definitions, PMG definitions, PM definitions, INJECT blocks,
   and localization keys

Usage: python gen_vanilla_company_buildings.py
"""

import os
import re
import sys
from pathlib import Path
from mod_state import ModState
from path_constants import base_game_path, mod_path

# Companies that already have unique buildings
ALREADY_HAS_UNIQUE = {
    'company_krupp', 'company_standard_oil', 'company_us_steel', 'company_ford_motor',
    'company_east_india_company', 'company_schneider_creusot', 'company_putilov_company',
    'company_mitsubishi', 'company_tata', 'company_siemens_and_halske',
    'company_de_beers', 'company_branobel', 'company_general_electric',
    'company_mitsui', 'company_fiat',
}

# ─── Company → unique building mapping ───
# Format: company_id → (building_key_suffix, display_name, theme_description)
# The building key will be: building_{suffix}
# PM and PMG will use: pm_{suffix}, pmg_{suffix}

COMPANY_BUILDINGS = {
    # ═══════════════════════════════════════════════
    #  GERMANY
    # ═══════════════════════════════════════════════
    'company_rheinmetall': ('rheinmetall_unterluss_proving_ground', 'Rheinmetall Unterlüss Proving Ground',
        'arms', 'Artillery and weapons testing range in the Lüneburg Heath'),
    'company_schichau': ('schichau_elbing_shipyard', 'Schichau-Werke Elbing',
        'shipyard', 'Shipbuilding and locomotive works on the Baltic'),
    'company_basf': ('basf_ludwigshafen_plant', 'BASF Ludwigshafen Works',
        'chemicals', 'Pioneering chemical synthesis complex on the Rhine'),
    'company_prussian_state_railways': ('prussian_railway_directorate', 'Prussian Railway Directorate',
        'railway', 'Central administration for the largest state railway network in Europe'),
    'company_ingolstadt_electrical_company': ('ingolstadt_power_station', 'Ingolstadt Power Station',
        'power', 'Municipal electricity generating station'),
    'company_konigliche_porzellan_manufaktur_meissen': ('meissen_porcelain_manufactory', 'Meissen Porcelain Manufactory',
        'luxury', 'Europe\'s oldest porcelain factory, famed for crossed swords mark'),

    # ═══════════════════════════════════════════════
    #  GREAT BRITAIN
    # ═══════════════════════════════════════════════
    'company_armstrong_whitworth': ('armstrong_elswick_works', 'Armstrong Elswick Works',
        'arms', 'Massive armaments complex on the Tyne producing warships and artillery'),
    'company_bolckow_vaughan': ('bolckow_eston_ironworks', 'Bolckow Vaughan Eston Ironworks',
        'steel', 'Cleveland ironworks that pioneered basic Bessemer steelmaking'),
    'company_gwr': ('gwr_swindon_works', 'GWR Swindon Works',
        'railway', 'Great Western Railway\'s locomotive manufacturing headquarters'),
    'company_j_p_coats': ('coats_ferguslie_mills', 'J&P Coats Ferguslie Thread Mills',
        'textiles', 'The world\'s largest thread manufacturing complex in Paisley'),
    'company_john_brown': ('john_brown_clydebank_yard', 'John Brown Clydebank Shipyard',
        'shipyard', 'Legendary Clyde shipyard that built the Queen Mary and HMS Hood'),
    'company_maple_and_co': ('maple_tottenham_court_showroom', 'Maple & Co Tottenham Court Road',
        'luxury', 'London\'s premier furniture showroom and workshop'),
    'company_imperial_tobacco': ('imperial_tobacco_wills_factory', 'Imperial Tobacco Wills Factory',
        'tobacco', 'Massive cigarette factory complex in Bristol'),
    'company_hbc': ('hbc_york_factory', 'Hudson\'s Bay York Factory',
        'trading', 'Historic fur trade depot and administrative center on Hudson Bay'),

    # ═══════════════════════════════════════════════
    #  FRANCE
    # ═══════════════════════════════════════════════
    'company_fcm': ('fcm_la_seyne_shipyard', 'FCM La Seyne Shipyard',
        'shipyard', 'Forges et Chantiers de la Méditerranée naval construction yard'),
    'company_saint_etienne': ('saint_etienne_arms_manufactory', 'Saint-Étienne Arms Manufactory',
        'arms', 'State arms factory in France\'s industrial heartland'),
    'company_dmc': ('dmc_mulhouse_mills', 'DMC Mulhouse Thread Mills',
        'textiles', 'Dollfus-Mieg cotton and embroidery thread works in Alsace'),
    'company_cgv': ('cgv_haut_brion_estate', 'CGV Haut-Brion Estate',
        'wine', 'Premier cru Bordeaux winemaking estate and cellars'),
    'company_mines_anzin': ('anzin_colliery', 'Mines d\'Anzin Colliery',
        'mining_coal', 'France\'s largest and oldest coal mining company in the Nord'),
    'company_nicolas_portalis': ('portalis_lyon_silk_house', 'Portalis Lyon Silk House',
        'textiles', 'Lyon silk weaving and finishing workshops'),
    'company_maison_worth': ('worth_rue_de_la_paix_atelier', 'Worth Rue de la Paix Atelier',
        'luxury', 'The birthplace of Parisian haute couture'),

    # ═══════════════════════════════════════════════
    #  RUSSIA
    # ═══════════════════════════════════════════════
    'company_izhevsk_arms_plant': ('izhevsk_arms_factory', 'Izhevsk Arms Factory',
        'arms', 'Imperial arms works in the Urals producing infantry weapons'),
    'company_savva_morozov': ('morozov_orekhovo_zuevo_mills', 'Morozov Orekhovo-Zuevo Mills',
        'textiles', 'Russia\'s largest cotton textile complex near Moscow'),
    'company_john_hughes': ('hughes_yuzovka_steelworks', 'Hughes Yuzovka Steelworks',
        'steel', 'Foundational steelworks of the Donbas industrial region'),
    'company_vodka_monopoly': ('vodka_monopoly_warehouse', 'State Vodka Monopoly Warehouse',
        'distillery', 'Central state liquor storage and distribution facility'),
    'company_moscow_irrigation_company': ('moscow_irrigation_cotton_depot', 'Moscow Irrigation Cotton Depot',
        'textiles', 'Central Asian cotton ginning and distribution center'),
    'company_perskhlopok': ('perskhlopok_cotton_combines', 'Perskhlopok Cotton Combines',
        'textiles', 'Persian cotton processing and spinning mills'),
    'company_persshelk': ('persshelk_silk_reeling_house', 'Persshelk Silk Reeling House',
        'textiles', 'Caucasian silk reeling and weaving facility'),
    'company_united_tobacco_factories': ('united_tobacco_moscow_plant', 'United Tobacco Moscow Plant',
        'tobacco', 'Russia\'s consolidated cigarette manufacturing complex'),
    'company_russian_american_company': ('rac_sitka_trading_post', 'Russian-American Company Sitka Trading Post',
        'trading', 'Fur trade headquarters and supply depot in Russian Alaska'),
    'company_kirgizian_mining_company': ('kirgizian_copper_smelter', 'Kirgizian Copper Smelter',
        'mining_metal', 'Ore smelting works in the Kyrgyz steppe'),
    'company_west_ural_petroleum': ('west_ural_oil_depot', 'West Ural Oil Depot',
        'oil', 'Petroleum storage and pipeline terminal in the Ural region'),

    # ═══════════════════════════════════════════════
    #  USA
    # ═══════════════════════════════════════════════
    'company_united_fruit': ('united_fruit_great_white_fleet_terminal', 'United Fruit Terminal',
        'plantations', 'Banana importing and cold storage terminal on the Gulf Coast'),
    'company_william_cramp': ('cramp_philadelphia_shipyard', 'Cramp Philadelphia Shipyard',
        'shipyard', 'Major naval shipbuilding complex on the Delaware River'),
    'company_colt_firearms': ('colt_hartford_armory', 'Colt Hartford Armory',
        'arms', 'Samuel Colt\'s famous blue-onion-domed arms factory in Connecticut'),
    'company_lee_wilson': ('lee_wilson_plantation_depot', 'Lee Wilson Plantation Depot',
        'plantations', 'Arkansas Delta cotton plantation and timber operation'),

    # ═══════════════════════════════════════════════
    #  ITALY
    # ═══════════════════════════════════════════════
    'company_ansaldo': ('ansaldo_sestri_ponente_works', 'Ansaldo Sestri Ponente Works',
        'arms', 'Genoese heavy industry complex producing warships, locomotives, and artillery'),
    'company_ilva': ('ilva_bagnoli_steelworks', 'ILVA Bagnoli Steelworks',
        'steel', 'Italy\'s premier steelworks overlooking the Bay of Naples'),
    'company_ricordi': ('ricordi_galleria_vittorio_emanuele', 'Ricordi Galleria Publishing House',
        'luxury', 'Music publisher at the heart of Milan\'s cultural life'),
    'company_csfa': ('csfa_sicilian_sulfur_depot', 'CSFA Sicilian Sulfur Depot',
        'mining_mineral', 'Sulfur mining concession and railway in Sicily'),
    'company_mantero_seta': ('mantero_como_silk_mill', 'Mantero Como Silk Mill',
        'textiles', 'Lake Como silk weaving and dyeing workshops'),
    'company_anglo_sicilian_sulphur_company': ('anglo_sicilian_licata_wharf', 'Anglo-Sicilian Licata Wharf',
        'mining_mineral', 'Sulfur export wharf and calcining kilns at Licata'),

    # ═══════════════════════════════════════════════
    #  JAPAN
    # ═══════════════════════════════════════════════
    'company_mantetsu': ('mantetsu_dalian_railway_hub', 'Mantetsu Dalian Railway Hub',
        'railway', 'South Manchuria Railway headquarters and rail junction'),
    'company_kinkozan_sobei': ('kinkozan_kiyomizu_kiln', 'Kinkozan Kiyomizu Kiln',
        'luxury', 'Renowned Kyoto ceramics workshop producing Satsuma ware'),

    # ═══════════════════════════════════════════════
    #  AUSTRIA-HUNGARY
    # ═══════════════════════════════════════════════
    'company_skoda': ('skoda_pilsen_works', 'Škoda Pilsen Works',
        'arms', 'Bohemian heavy engineering and armaments colossus'),
    'company_mav': ('mav_budapest_locomotive_works', 'MÁV Budapest Locomotive Works',
        'railway', 'Hungarian state railway locomotive manufacturing plant'),
    'company_manfred_weiss': ('manfred_weiss_csepel_works', 'Manfred Weiss Csepel Works',
        'arms', 'Budapest munitions and metalworking complex on Csepel Island'),
    'company_galician_carpathian_oil': ('galician_boryslaw_oil_field', 'Galician Borysław Oil Field',
        'oil', 'Pioneering petroleum extraction in the Carpathian foothills'),
    'company_oevg': ('oevg_steyr_arms_works', 'OEVG Steyr Arms Works',
        'arms', 'Austrian state arms factory in Upper Austria'),
    'company_oesterreichisch_alpine_montangesellschaft': ('alpine_donawitz_steelworks', 'Alpine Donawitz Steelworks',
        'steel', 'Styrian steelworks using the revolutionary LD process'),
    'company_getzner_mutter': ('getzner_bludenz_textile_works', 'Getzner Bludenz Textile Works',
        'textiles', 'Vorarlberg cotton and linen weaving mill'),
    'company_elso_budapesti_gozmalom': ('elso_budapesti_steam_mill', 'Első Budapesti Steam Mill',
        'food', 'Budapest\'s premier flour milling complex on the Danube'),
    'company_erste_brunner': ('erste_brunner_maschinenwerk', 'Erste Brünner Maschinenwerk',
        'motors', 'Moravia\'s leading machine tool and locomotive manufacturer'),
    'company_gebruder_thonet': ('thonet_bystrice_bentwood_factory', 'Thonet Bystřice Bentwood Factory',
        'luxury', 'Mass production of the iconic bentwood chair No. 14'),
    'company_ludwig_moser_and_sons': ('moser_karlsbad_glass_works', 'Moser Karlsbad Glass Works',
        'luxury', 'Crystal glassworks patronized by European royal courts'),
    'company_witkowitzer_bergbau_und_huttengewerkschaft': ('witkowitzer_ostrava_ironworks', 'Witkowitzer Ostrava Ironworks',
        'steel', 'Silesian iron and coal conglomerate near Ostrava'),
    'company_jakub_klein': ('klein_galician_paper_mill', 'Klein Galician Paper Mill',
        'paper', 'Paper and timber processing in eastern Galicia'),
    'company_stabilimento_tecnico_di_fiume': ('stf_fiume_torpedo_works', 'STF Fiume Torpedo Works',
        'shipyard', 'Birthplace of the modern self-propelled torpedo'),

    # ═══════════════════════════════════════════════
    #  SCANDINAVIA
    # ═══════════════════════════════════════════════
    'company_ericsson': ('ericsson_telefonplan', 'Ericsson Telefonplan',
        'electrics', 'Stockholm telephone manufacturing campus'),
    'company_nokia': ('nokia_cable_works', 'Nokia Cable Works',
        'electrics', 'Finnish cable and rubber factory transitioning to electronics'),
    'company_norsk_hydro': ('norsk_hydro_rjukan_plant', 'Norsk Hydro Rjukan Plant',
        'chemicals', 'Hydroelectric-powered fertilizer and heavy water plant'),
    'company_gotaverken': ('gotaverken_gothenburg_shipyard', 'Götaverken Gothenburg Shipyard',
        'shipyard', 'Sweden\'s largest shipbuilding yard on the Göta älv'),
    'company_aker_mek': ('aker_oslo_shipyard', 'Aker Oslo Shipyard',
        'shipyard', 'Norway\'s premier shipbuilding and engineering works'),
    'company_lkab': ('lkab_kiruna_mine', 'LKAB Kiruna Iron Mine',
        'mining_metal', 'The world\'s largest underground iron ore mine'),
    'company_chr_hansens': ('chr_hansen_copenhagen_laboratory', 'Chr. Hansen Copenhagen Laboratory',
        'chemicals', 'Pioneering microbiology and food enzyme research lab'),
    'company_ap_moller': ('ap_moller_copenhagen_wharf', 'A.P. Møller Copenhagen Wharf',
        'trading', 'Maersk shipping line headquarters and dockyard'),

    # ═══════════════════════════════════════════════
    #  BENELUX
    # ═══════════════════════════════════════════════
    'company_philips': ('philips_eindhoven_natlab', 'Philips Eindhoven NatLab',
        'electrics', 'Philips Physics Laboratory where revolutionary lighting and electronics were developed'),
    'company_franco_belge': ('franco_belge_raismes_works', 'Franco-Belge Raismes Works',
        'motors', 'Railway locomotive and rolling stock factory near Valenciennes'),
    'company_john_cockerill': ('cockerill_seraing_works', 'Cockerill Seraing Works',
        'steel', 'Integrated steelworks on the Meuse, Belgium\'s industrial cradle'),
    'company_nederlandse_petroleum': ('nederlandse_petroleum_pangkalan_depot', 'NedPetroleum Pangkalan Brandan Depot',
        'oil', 'Oil storage and shipping facility in the Dutch East Indies'),
    'company_ccci': ('ccci_leopoldville_depot', 'CCCI Léopoldville Rubber Depot',
        'plantations', 'Congo rubber collection and export warehouse'),

    # ═══════════════════════════════════════════════
    #  IBERIA
    # ═══════════════════════════════════════════════
    'company_altos_hornos_de_vizcaya': ('altos_hornos_baracaldo_furnaces', 'Altos Hornos Baracaldo Furnaces',
        'steel', 'Basque Country blast furnaces dominating Spanish steel production'),
    'company_trubia': ('trubia_cannon_foundry', 'Trubia Cannon Foundry',
        'arms', 'Royal artillery foundry in Asturias'),
    'company_espana_industrial': ('espana_industrial_sants_mills', 'España Industrial Sants Mills',
        'textiles', 'Barcelona cotton spinning and weaving complex'),
    'company_secn': ('secn_ferrol_shipyard', 'SECN Ferrol Shipyard',
        'shipyard', 'Naval construction yard in Galicia building warships for Spain'),
    'company_hispano_suiza': ('hispano_suiza_barcelona_factory', 'Hispano-Suiza Barcelona Factory',
        'motors', 'Luxury automobile and aero-engine manufacturer'),
    'company_douro_wine_company': ('douro_wine_lodge', 'Douro Wine Lodge',
        'wine', 'Port wine aging cellars in Vila Nova de Gaia'),
    'company_pedro_domecq': ('pedro_domecq_jerez_bodega', 'Pedro Domecq Jerez Bodega',
        'wine', 'Sherry aging cellars in Jerez de la Frontera'),
    'company_gran_azucarera': ('gran_azucarera_aranjuez_refinery', 'Gran Azucarera Aranjuez Refinery',
        'food', 'Spain\'s consolidated sugar refining complex'),
    'company_duro_y_compania': ('duro_la_felguera_steelworks', 'Duro La Felguera Steelworks',
        'steel', 'Asturian coal and iron complex at La Felguera'),
    'company_uniao_fabril': ('uniao_fabril_barreiro_plant', 'União Fabril Barreiro Plant',
        'chemicals', 'Portuguese chemical and cement works across the Tagus from Lisbon'),

    # ═══════════════════════════════════════════════
    #  BALKANS & EASTERN EUROPE
    # ═══════════════════════════════════════════════
    'company_allatini_mills': ('allatini_thessaloniki_flour_mill', 'Allatini Thessaloniki Flour Mill',
        'food', 'Ottoman-era flour mill complex in Thessaloniki'),
    'company_basileiades': ('basileiades_piraeus_works', 'Basileiades Piraeus Works',
        'motors', 'Greek engineering and motor workshop near Athens port'),
    'company_kouppas': ('kouppas_piraeus_foundry', 'Kouppas Piraeus Foundry',
        'motors', 'Greek metalworking and machinery foundry'),
    'company_ralli_brothers': ('ralli_odessa_grain_elevator', 'Ralli Odessa Grain Elevator',
        'trading', 'Greek diaspora grain trading and export warehouse'),
    'company_zastava': ('zastava_kragujevac_arsenal', 'Zastava Kragujevac Arsenal',
        'arms', 'Serbian state arms arsenal in Kragujevac'),
    'company_klanicko_drustvo': ('klanicko_belgrade_slaughterhouse', 'Klanično Belgrade Slaughterhouse',
        'food', 'Belgrade municipal meat processing and cold storage'),
    'company_mate_gavrilovic': ('gavrilovic_petrinja_meatworks', 'Gavrilović Petrinja Meatworks',
        'food', 'Croatian salami and preserved meat factory'),
    'company_cfr': ('cfr_bucharest_railway_works', 'CFR Bucharest Railway Works',
        'railway', 'Romanian state railway locomotive repair shops'),
    'company_romanian_star': ('romanian_star_ploiesti_refinery', 'Romanian Star Ploiești Refinery',
        'oil', 'Petroleum refinery in the heart of Romania\'s oil country'),

    # ═══════════════════════════════════════════════
    #  OTTOMAN EMPIRE & MIDDLE EAST
    # ═══════════════════════════════════════════════
    'company_imperial_arsenal': ('imperial_arsenal_golden_horn', 'Imperial Arsenal Golden Horn',
        'shipyard', 'Ottoman naval arsenal on Istanbul\'s Golden Horn'),
    'company_orient_express': ('orient_express_sirkeci_terminal', 'Orient Express Sirkeci Terminal',
        'railway', 'Legendary terminus of the Orient Express in Constantinople'),
    'company_stt': ('stt_haskoy_shipyard', 'STT Hasköy Shipyard',
        'shipyard', 'Ottoman commercial shipbuilding yard on the Bosphorus'),
    'company_ottoman_tobacco_regie': ('tobacco_regie_cibali_factory', 'Tobacco Régie Cibali Factory',
        'tobacco', 'Ottoman state tobacco monopoly factory in Istanbul'),
    'company_turkish_petroleum': ('turkish_petroleum_kirkuk_depot', 'Turkish Petroleum Kirkuk Depot',
        'oil', 'Oil extraction and pipeline works at Kirkuk'),
    'company_anglo_persian_oil': ('anglo_persian_abadan_refinery', 'Anglo-Persian Abadan Refinery',
        'oil', 'The world\'s largest oil refinery at the head of the Persian Gulf'),
    'company_iranian_state_railway': ('iranian_state_railway_veresk_station', 'Iranian State Railway Veresk Station',
        'railway', 'Engineering marvel on the Trans-Iranian railway across the Alborz'),
    'company_national_iranian_oil': ('nioc_masjed_soleyman_field', 'NIOC Masjed Soleyman Oil Field',
        'oil', 'Site of the Middle East\'s first commercial oil discovery'),
    'company_sherkat_shemali': ('sherkat_shemali_cotton_gin', 'Sherkat-e Shemali Cotton Gin',
        'textiles', 'Northern Iranian cotton ginning and processing works'),
    'company_sherkate_eslamiya': ('sherkate_eslamiya_isfahan_mill', 'Sherkat-e Eslāmiyyeh Isfahan Mill',
        'textiles', 'Isfahan textile weaving and carpet manufacturing complex'),

    # ═══════════════════════════════════════════════
    #  EGYPT & AFRICA
    # ═══════════════════════════════════════════════
    'company_suez_company': ('suez_company_ismailia_hq', 'Suez Company Ismailia Headquarters',
        'trading', 'Administrative center of the Suez Canal Company at Ismailia'),
    'company_egyptian_rail': ('egyptian_rail_cairo_central', 'Egyptian Railway Cairo Central Station',
        'railway', 'Egypt\'s railway hub connecting the Nile Delta'),
    'company_misr': ('misr_mahalla_textile_complex', 'Misr Mahalla Textile Complex',
        'textiles', 'Egypt\'s largest textile factory in the Nile Delta'),
    'company_office_cherifien_des_phosphates': ('ocp_khouribga_mine', 'OCP Khouribga Phosphate Mine',
        'mining_mineral', 'Morocco\'s vast open-pit phosphate mining operation'),
    'company_john_holt': ('john_holt_lagos_trading_house', 'John Holt Lagos Trading House',
        'trading', 'West African trading post and palm oil export depot'),
    'company_mozambique_company': ('mozambique_company_beira_concession', 'Mozambique Company Beira Concession',
        'plantations', 'Charter company headquarters and port in Beira'),
    'company_william_sandford': ('sandford_newcastle_natal_ironworks', 'Sandford Newcastle-Natal Ironworks',
        'steel', 'South African iron smelting works in KwaZulu-Natal'),
    'company_imperial_ethiopian_railways': ('ethiopian_railway_dire_dawa_depot', 'Ethiopian Railway Dire Dawa Depot',
        'railway', 'Addis Ababa-Djibouti railway maintenance depot'),

    # ═══════════════════════════════════════════════
    #  CHINA
    # ═══════════════════════════════════════════════
    'company_kaiping_mining': ('kaiping_tangshan_colliery', 'Kaiping Tangshan Colliery',
        'mining_coal', 'China\'s first modern coal mine with railway connection'),
    'company_hanyang_arsenal': ('hanyang_arsenal_iron_works', 'Hanyang Arsenal Iron Works',
        'arms', 'Hubei arsenal and steelworks, China\'s Self-Strengthening centerpiece'),
    'company_foochow_arsenal': ('foochow_mawei_dockyard', 'Foochow Mawei Dockyard',
        'shipyard', 'Fujian naval dockyard and China\'s first modern shipyard'),
    'company_jiangnan_weaving_bureaus': ('jiangnan_nanjing_brocade_hall', 'Jiangnan Nanjing Brocade Hall',
        'textiles', 'Imperial silk weaving bureau producing cloud brocade'),
    'company_jingdezhen': ('jingdezhen_imperial_kiln', 'Jingdezhen Imperial Kiln',
        'luxury', 'Porcelain capital of the world, supplier to the Imperial court'),
    'company_ong_lung_sheng_tea_company': ('ong_lung_sheng_tea_warehouse', 'Ong Lung Sheng Tea Warehouse',
        'plantations', 'Fujianese tea processing and export warehouse'),
    'company_lanfang_kongsi': ('lanfang_pontianak_kongsi_house', 'Lanfang Pontianak Kongsi House',
        'mining_gold', 'Chinese kongsi gold mining and administrative center in Borneo'),

    # ═══════════════════════════════════════════════
    #  INDIA
    # ═══════════════════════════════════════════════
    'company_great_indian_railway': ('great_indian_railway_jamalpur_works', 'Great Indian Railway Jamalpur Works',
        'railway', 'India\'s first railway locomotive workshop in Bihar'),
    'company_wadia_shipbuilders': ('wadia_bombay_dockyard', 'Wadia Bombay Dockyard',
        'shipyard', 'Parsi-owned shipyard that built vessels for the Royal Navy'),
    'company_calcutta_electric': ('calcutta_electric_victoria_house', 'Calcutta Electric Victoria House',
        'power', 'India\'s first electric power station on the Hooghly'),
    'company_bombay_dyeing_company': ('bombay_dyeing_spring_mills', 'Bombay Dyeing Spring Mills',
        'textiles', 'Mumbai cotton textile spinning and dyeing complex'),
    'company_bombay_burmah_trading_corporation': ('bombay_burmah_rangoon_timber_depot', 'Bombay Burmah Rangoon Timber Depot',
        'plantations', 'Teak extraction and rubber plantation operations in Burma'),
    'company_david_sassoon': ('sassoon_bombay_docks', 'Sassoon Bombay Docks',
        'trading', 'Sassoon family trading house and cotton warehouse in Bombay'),
    'company_assam_company': ('assam_company_nazira_tea_estate', 'Assam Company Nazira Tea Estate',
        'plantations', 'India\'s first commercial tea garden in upper Assam'),
    'company_opium_export_monopoly': ('opium_ghazipur_factory', 'Opium Ghazipur Factory',
        'plantations', 'East India Company\'s opium processing center on the Ganges'),
    'company_bengal_coal_company': ('bengal_coal_raniganj_mine', 'Bengal Coal Raniganj Mine',
        'mining_coal', 'India\'s first commercial coal mine in West Bengal'),
    'company_madura_mills': ('madura_mills_madurai_complex', 'Madura Mills Madurai Complex',
        'textiles', 'South Indian textile spinning and weaving complex'),

    # ═══════════════════════════════════════════════
    #  KOREA
    # ═══════════════════════════════════════════════
    'company_hanseong_jeongi_hoesa': ('hanseong_jeongi_gwanghwamun_station', 'Hanseong Electric Gwanghwamun Station',
        'power', 'Korea\'s first electric power and streetcar company'),
    'company_oriental_development_company': ('oriental_dev_kunsan_granary', 'Oriental Development Kunsan Granary',
        'plantations', 'Japanese colonial agricultural exploitation depot'),
    'company_sunhwaguk': ('sunhwaguk_seoul_tobacco_factory', 'Sunhwaguk Seoul Tobacco Factory',
        'tobacco', 'Korean tobacco and agricultural processing works'),

    # ═══════════════════════════════════════════════
    #  SOUTHEAST ASIA
    # ═══════════════════════════════════════════════
    'company_b_grimm': ('b_grimm_bangkok_warehouse', 'B. Grimm Bangkok Warehouse',
        'trading', 'Siamese general trading and rice export house'),
    'company_nam_dinh': ('nam_dinh_textile_plant', 'Nam Định Textile Plant',
        'textiles', 'French Indochina cotton spinning factory'),
    'company_steel_brothers': ('steel_brothers_syriam_depot', 'Steel Brothers Syriam Depot',
        'oil', 'Burmese oil and rice export center near Rangoon'),
    'company_san_miguel': ('san_miguel_manila_brewery', 'San Miguel Manila Brewery',
        'food', 'Southeast Asia\'s oldest brewery and food conglomerate'),
    'company_ynchausti_y_compania': ('ynchausti_manila_trading_house', 'Ynchausti Manila Trading House',
        'trading', 'Basque-Filipino trading firm in hemp, sugar, and shipping'),

    # ═══════════════════════════════════════════════
    #  CENTRAL ASIA & AFGHANISTAN
    # ═══════════════════════════════════════════════
    'company_da_afghan_nassaji_sherkat': ('afghan_nassaji_kabul_mills', 'Afghan Nassaji Kabul Mills',
        'textiles', 'Afghanistan\'s first modern textile factory'),
    'company_tashkent_railroad': ('tashkent_railroad_workshops', 'Tashkent Railroad Workshops',
        'railway', 'Central Asian railway maintenance and locomotive depot'),

    # ═══════════════════════════════════════════════
    #  MEXICO & CENTRAL AMERICA
    # ═══════════════════════════════════════════════
    'company_fundidora_monterrey': ('fundidora_monterrey_blast_furnace', 'Fundidora Monterrey Blast Furnace',
        'steel', 'Latin America\'s first integrated steel mill'),
    'company_el_aguila': ('el_aguila_tampico_refinery', 'El Águila Tampico Refinery',
        'oil', 'Mexican Eagle Petroleum\'s massive Gulf Coast refinery'),
    'company_panama_company': ('panama_company_culebra_cut', 'Panama Company Culebra Cut',
        'trading', 'Canal zone construction headquarters and transit facilities'),
    'company_bacardi': ('bacardi_santiago_distillery', 'Bacardí Santiago Distillery',
        'distillery', 'Legendary rum distillery founded in Santiago de Cuba'),
    'company_rodriguez_arguelles_y_cia': ('rodriguez_arguelles_havana_tobacco_house', 'Rodríguez Argüelles Havana Tobacco House',
        'tobacco', 'Cuban cigar manufacturing and tobacco curing operation'),

    # ═══════════════════════════════════════════════
    #  SOUTH AMERICA
    # ═══════════════════════════════════════════════
    'company_sao_paulo_railway': ('sao_paulo_railway_paranapiacaba_workshop', 'São Paulo Railway Paranapiacaba Workshop',
        'railway', 'Railway workshops at the Serra do Mar cable incline'),
    'company_fundicao_ipanema': ('fundicao_ipanema_sorocaba_foundry', 'Fundição Ipanema Sorocaba Foundry',
        'steel', 'Brazil\'s pioneering royal ironworks near São Paulo'),
    'company_pernambuco_textiles': ('pernambuco_recife_cotton_mill', 'Pernambuco Recife Cotton Mill',
        'textiles', 'Northeastern Brazilian cotton spinning complex'),
    'company_estaleiro_maua': ('estaleiro_maua_niteroi_dockyard', 'Estaleiro Mauá Niterói Dockyard',
        'shipyard', 'Brazil\'s first steamship building and repair yard'),
    'company_rossi': ('rossi_sao_leopoldo_arms_factory', 'Rossi São Leopoldo Arms Factory',
        'arms', 'Brazilian firearms manufacturer in Rio Grande do Sul'),
    'company_cordoba_railway': ('cordoba_railway_alta_gracia_works', 'Córdoba Railway Alta Gracia Works',
        'railway', 'Argentine railway repair and maintenance shops'),
    'company_la_rosada': ('la_rosada_buenos_aires_arsenal', 'La Rosada Buenos Aires Arsenal',
        'arms', 'Argentine state arms factory and munitions depot'),
    'company_bunge_born': ('bunge_born_buenos_aires_grain_silo', 'Bunge & Born Buenos Aires Grain Silo',
        'food', 'Massive grain elevators at Buenos Aires port'),
    'company_compania_sansinena_de_carnes_congeladas': ('sansinena_avellaneda_frigorífico', 'Sansinena Avellaneda Frigorífico',
        'food', 'Pioneer refrigerated meat packing plant south of Buenos Aires'),
    'company_argentinian_wine': ('argentinian_wine_mendoza_bodega', 'Argentine Wine Mendoza Bodega',
        'wine', 'Malbec winemaking estate in the Andean foothills'),
    'company_eea': ('eea_dock_sud_power_station', 'EEA Dock Sud Power Station',
        'power', 'Buenos Aires metropolitan electricity generating station'),
    'company_kablin': ('kablin_zarate_paper_mill', 'Kablín Zárate Paper Mill',
        'paper', 'Argentine pulp and paper manufacturing plant'),
    'company_sudamericana_de_vapores': ('sudamericana_valparaiso_pier', 'Sudamericana Valparaíso Pier',
        'trading', 'Chilean shipping line\'s main Pacific coast terminal'),
    'company_famae': ('famae_santiago_arsenal', 'FAMAE Santiago Arsenal',
        'arms', 'Chilean state arms and munitions factory'),
    'company_estanifera_llallagua': ('estanifera_llallagua_tin_concentrator', 'Estannífera Llallagua Tin Concentrator',
        'mining_metal', 'Bolivia\'s richest tin mine and concentrating plant'),
    'company_caribbean_petroleum': ('caribbean_petroleum_maracaibo_depot', 'Caribbean Petroleum Maracaibo Depot',
        'oil', 'Venezuelan oil storage and lake drilling operations'),
    'company_electricidad_de_caracas': ('electricidad_caracas_power_house', 'Electricidad de Caracas Power House',
        'power', 'Venezuela\'s first and largest electric utility'),
    'company_peruvian_amazon': ('peruvian_amazon_iquitos_depot', 'Peruvian Amazon Iquitos Rubber Depot',
        'plantations', 'Rubber collection and shipping in the Amazon basin'),

    # ═══════════════════════════════════════════════
    #  CANADA
    # ═══════════════════════════════════════════════
    'company_massey_harris': ('massey_harris_toronto_implement_works', 'Massey-Harris Toronto Implement Works',
        'motors', 'Agricultural machinery manufacturer in Toronto'),

    # ═══════════════════════════════════════════════
    #  DENMARK, POLAND, ETC.
    # ═══════════════════════════════════════════════
    'company_ursus': ('ursus_warsaw_tractor_plant', 'Ursus Warsaw Tractor Plant',
        'motors', 'Poland\'s premier agricultural and military vehicle manufacturer'),
    'company_lilpop': ('lilpop_warsaw_metalworks', 'Lilpop Warsaw Metalworks',
        'steel', 'Rolling stock and steel fabrication in the Polish capital'),

    # ═══════════════════════════════════════════════
    #  PARADOX (Easter Egg)
    # ═══════════════════════════════════════════════
    'company_paradox': ('paradox_kvarnholmen_studio', 'Paradox Kvarnholmen Studio',
        'electrics', 'Grand strategy game development studio on the Stockholm archipelago'),

    # ═══════════════════════════════════════════════
    #  IRELAND
    # ═══════════════════════════════════════════════
    'company_guinness': ('guinness_st_james_gate_brewery', 'Guinness St. James\'s Gate Brewery',
        'distillery', 'World-famous Dublin brewery producing iconic stout since 1759'),

    # ═══════════════════════════════════════════════
    #  REMAINING AFRICAN, ETC.
    # ═══════════════════════════════════════════════
    'company_societe_mokta_el_hadid': ('mokta_el_hadid_beni_saf_mine', 'Mokta el Hadid Beni Saf Mine',
        'mining_metal', 'Algerian iron ore mining and export operation'),
}

assert len(COMPANY_BUILDINGS) == 164, f"Expected 164 companies, got {len(COMPANY_BUILDINGS)}"

# ─── Sector → PM template mapping ───
# Each template defines: state_modifiers, building_modifiers (goods in/out), employment
# The goods/employment are per-workforce-scaled or per-level-scaled
SECTOR_TEMPLATES = {
    'arms': {
        'state_mods': [('building_arms_industry_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('steel', 15), ('tools', 10)],
        'outputs': [('small_arms', 20), ('ammunition', 20)],
        'employment': [('machinists', 800), ('laborers', 600), ('engineers', 400), ('clerks', 200)],
    },
    'steel': {
        'state_mods': [('building_steel_mill_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('iron', 20), ('coal', 15)],
        'outputs': [('steel', 25), ('tools', 10)],
        'employment': [('machinists', 800), ('laborers', 600), ('engineers', 400), ('clerks', 200)],
    },
    'shipyard': {
        'state_mods': [('building_military_shipyard_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('steel', 15), ('engines', 10)],
        'outputs': [('man_o_wars_baseline', 20), ('tools', 15)],
        'employment': [('machinists', 800), ('laborers', 600), ('engineers', 400), ('clerks', 200)],
    },
    'chemicals': {
        'state_mods': [('building_chemical_plant_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('sulfur', 15), ('coal', 10)],
        'outputs': [('explosives', 20), ('fertilizer', 15)],
        'employment': [('machinists', 600), ('laborers', 600), ('engineers', 600), ('clerks', 200)],
    },
    'textiles': {
        'state_mods': [('building_textile_mill_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('fabric', 20), ('dye', 10)],
        'outputs': [('clothes', 25), ('luxury_clothes', 5)],
        'employment': [('machinists', 600), ('laborers', 800), ('clerks', 400), ('shopkeepers', 200)],
    },
    'railway': {
        'state_mods': [('state_infrastructure_add', 10)],
        'country_mods': [],
        'inputs': [('steel', 15), ('engines', 10)],
        'outputs': [('transportation', 30), ('tools', 5)],
        'employment': [('machinists', 600), ('laborers', 600), ('engineers', 400), ('clerks', 400)],
    },
    'oil': {
        'state_mods': [('building_oil_rig_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('oil', 25)],
        'outputs': [('explosives', 20), ('fertilizer', 15)],
        'employment': [('machinists', 600), ('laborers', 800), ('engineers', 400), ('clerks', 200)],
    },
    'food': {
        'state_mods': [('state_standard_of_living_add', 1)],
        'country_mods': [],
        'inputs': [('grain', 20), ('sugar', 10)],
        'outputs': [('groceries', 30), ('meat', 10)],
        'employment': [('laborers', 800), ('shopkeepers', 600), ('clerks', 400), ('farmers', 200)],
    },
    'mining_coal': {
        'state_mods': [('building_coal_mine_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('tools', 15)],
        'outputs': [('coal', 30), ('iron', 10)],
        'employment': [('laborers', 1000), ('machinists', 400), ('engineers', 400), ('clerks', 200)],
    },
    'mining_metal': {
        'state_mods': [('building_iron_mine_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('tools', 15)],
        'outputs': [('iron', 30), ('coal', 10)],
        'employment': [('laborers', 1000), ('machinists', 400), ('engineers', 400), ('clerks', 200)],
    },
    'mining_mineral': {
        'state_mods': [('building_sulfur_mine_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('tools', 15)],
        'outputs': [('sulfur', 30), ('coal', 5)],
        'employment': [('laborers', 1000), ('machinists', 400), ('engineers', 400), ('clerks', 200)],
    },
    'mining_gold': {
        'state_mods': [('building_gold_mine_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('tools', 15)],
        'outputs': [('gold', 5), ('iron', 15)],
        'employment': [('laborers', 1000), ('machinists', 400), ('engineers', 400), ('clerks', 200)],
    },
    'power': {
        'state_mods': [('building_power_plant_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('coal', 15), ('engines', 10)],
        'outputs': [('electricity', 30)],
        'employment': [('machinists', 600), ('engineers', 600), ('laborers', 400), ('clerks', 400)],
    },
    'electrics': {
        'state_mods': [('building_electrics_industry_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('steel', 10), ('glass', 10)],
        'outputs': [('telephones', 20), ('radios', 10)],
        'employment': [('machinists', 600), ('engineers', 600), ('clerks', 400), ('laborers', 400)],
    },
    'motors': {
        'state_mods': [('building_motor_industry_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('steel', 15), ('tools', 10)],
        'outputs': [('engines', 20), ('automobiles', 5)],
        'employment': [('machinists', 800), ('laborers', 600), ('engineers', 400), ('clerks', 200)],
    },
    'trading': {
        'state_mods': [('state_trade_capacity_add', 5)],
        'country_mods': [],
        'inputs': [('fabric', 10), ('paper', 10)],
        'outputs': [('merchant_marine', 30)],
        'employment': [('clerks', 800), ('shopkeepers', 600), ('laborers', 400), ('officers', 200)],
    },
    'luxury': {
        'state_mods': [('state_migration_pull_mult', 0.1)],
        'country_mods': [('country_prestige_mult', 0.05)],
        'inputs': [('glass', 10), ('hardwood', 10)],
        'outputs': [('luxury_furniture', 15), ('porcelain', 10)],
        'employment': [('shopkeepers', 600), ('clerks', 600), ('laborers', 400), ('aristocrats', 400)],
    },
    'plantations': {
        'state_mods': [('state_standard_of_living_add', 1)],
        'country_mods': [],
        'inputs': [('tools', 10)],
        'outputs': [('tea', 15), ('sugar', 15), ('fruit', 10)],
        'employment': [('laborers', 1000), ('farmers', 600), ('clerks', 200), ('shopkeepers', 200)],
    },
    'tobacco': {
        'state_mods': [('building_tobacco_plantation_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('tobacco', 20), ('paper', 10)],
        'outputs': [('luxury_clothes', 10), ('services', 20)],
        'employment': [('laborers', 800), ('shopkeepers', 400), ('clerks', 400), ('farmers', 400)],
    },
    'wine': {
        'state_mods': [('state_migration_pull_mult', 0.1)],
        'country_mods': [('country_prestige_mult', 0.03)],
        'inputs': [('fruit', 15), ('glass', 10)],
        'outputs': [('wine', 25), ('liquor', 10)],
        'employment': [('farmers', 800), ('shopkeepers', 400), ('laborers', 400), ('aristocrats', 400)],
    },
    'distillery': {
        'state_mods': [('state_migration_pull_mult', 0.1)],
        'country_mods': [],
        'inputs': [('grain', 15), ('glass', 10)],
        'outputs': [('liquor', 25), ('services', 10)],
        'employment': [('laborers', 600), ('shopkeepers', 600), ('clerks', 400), ('farmers', 400)],
    },
    'paper': {
        'state_mods': [('building_paper_mill_throughput_add', 0.1)],
        'country_mods': [],
        'inputs': [('wood', 20), ('tools', 5)],
        'outputs': [('paper', 25), ('services', 10)],
        'employment': [('laborers', 800), ('machinists', 600), ('clerks', 400), ('engineers', 200)],
    },
}


# ─── Goods data for cost annotation ───
GOODS_PRICES = {
    'grain': 20, 'fish': 20, 'fabric': 20, 'wood': 20, 'dye': 40,
    'coal': 30, 'iron': 40, 'steel': 50, 'tools': 40, 'engines': 60,
    'oil': 30, 'sulfur': 50, 'glass': 40,
    'paper': 30, 'rubber': 40, 'hardwood': 30,
    'gold': 100, 'sugar': 30, 'tea': 50, 'tobacco': 40, 'fruit': 30,
    'meat': 30, 'clothes': 30, 'luxury_clothes': 130, 'porcelain': 70,
    'luxury_furniture': 110, 'wine': 30, 'liquor': 30,
    'small_arms': 60, 'ammunition': 60, 'artillery': 100,
    'explosives': 50, 'fertilizer': 30,
    'man_o_wars_baseline': 60,
    'transportation': 20, 'electricity': 30,
    'telephones': 60, 'radios': 40,
    'automobiles': 100, 'merchant_marine': 50,
    'services': 30, 'groceries': 30,
}


def generate_pm(building_suffix, display_name, sector, description):
    """Generate a production method definition."""
    template = SECTOR_TEMPLATES[sector]
    pm_name = f"pm_{building_suffix}"

    lines = []
    lines.append(f"# --- {display_name} ---")
    lines.append(f"# Theme: {description}")
    lines.append(f"{pm_name} = {{")
    lines.append(f'\ttexture = "gfx/interface/icons/production_method_icons/base1.dds"')

    # State modifiers
    if template['state_mods']:
        lines.append("\tstate_modifiers = {")
        lines.append("\t\tworkforce_scaled = {")
        for mod_name, mod_val in template['state_mods']:
            if isinstance(mod_val, int):
                lines.append(f"\t\t\t{mod_name} = {mod_val}")
            else:
                lines.append(f"\t\t\t{mod_name} = {mod_val}")
        lines.append("\t\t}")
        lines.append("\t}")

    # Country modifiers
    if template['country_mods']:
        lines.append("\tcountry_modifiers = {")
        lines.append("\t\tworkforce_scaled = {")
        for mod_name, mod_val in template['country_mods']:
            lines.append(f"\t\t\t{mod_name} = {mod_val}")
        lines.append("\t\t}")
        lines.append("\t}")

    # Building modifiers
    lines.append("\tbuilding_modifiers = {")
    lines.append("\t\tworkforce_scaled = {")

    # Calculate costs for comments
    total_input = 0
    total_output = 0

    # Inputs
    lines.append("\t\t\t# Input goods")
    for good, amount in template['inputs']:
        price = GOODS_PRICES.get(good, 30)
        cost = price * amount
        total_input += cost
        lines.append(f"\t\t\tgoods_input_{good}_add = {amount}{' ' * max(1, 45 - len(f'goods_input_{good}_add = {amount}'))}# Price: {price:>4}, Total cost: {cost:>7.1f}")

    # Outputs
    lines.append("\t\t\t# Output goods")
    for good, amount in template['outputs']:
        price = GOODS_PRICES.get(good, 30)
        cost = price * amount
        total_output += cost
        lines.append(f"\t\t\tgoods_output_{good}_add = {amount}{' ' * max(1, 45 - len(f'goods_output_{good}_add = {amount}'))}# Price: {price:>4}, Total cost: {cost:>7.1f}")

    profit = total_output - total_input
    margin = (profit / total_input * 100) if total_input > 0 else 0
    zp_mult = (total_input / total_output) if total_output > 0 else 0

    lines.append(f"\t\t\t# Total input cost: {total_input:.1f}")
    lines.append(f"\t\t\t# Total output cost: {total_output:.1f}")
    lines.append(f"\t\t\t# Profit: {profit:.1f}")
    lines.append(f"\t\t\t# Profit margin: {margin:.2f}%")
    lines.append(f"\t\t\t# Zero profit price multiplier: {zp_mult:.2f}")
    lines.append(f"\t\t\t# Employment: 2000")
    wage_be = profit / 2000 if profit > 0 else 0
    lines.append(f"\t\t\t# Wage breakeven: {wage_be:.2f}")

    lines.append("\t\t}")

    # Employment (level_scaled)
    lines.append("\t\tlevel_scaled = {")
    for pop_type, amount in template['employment']:
        lines.append(f"\t\t\tbuilding_employment_{pop_type}_add = {amount}")
    lines.append("\t\t}")

    lines.append("\t}")
    lines.append("}")
    lines.append("")

    return '\n'.join(lines)


def generate_pmg(building_suffix):
    """Generate a production method group definition."""
    return f"""pmg_{building_suffix} = {{
\ttexture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
\tai_selection = most_productive
\tproduction_methods = {{ pm_{building_suffix} }}
}}"""


def generate_building(building_suffix, company_id, icon_path):
    """Generate a building definition."""
    building_name = f"building_{building_suffix}"
    return f"""{building_name} = {{
\tbuilding_group = bg_company_buildings
\ticon = "{icon_path}"
\texpandable = yes
\tdownsizeable = yes
\thas_max_level = yes
\tunique = no
\tcity_type = city
\tai_nationalization_desire = 0
\tproduction_method_groups = {{
\t\tpmg_{building_suffix}
\t}}
\trequired_construction = construction_cost_mega_high
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
\tpotential = {{
\t\towner = {{
\t\t\thas_company = company_type:{company_id}
\t\t}}
\t\tOR = {{
\t\t\tany_scope_building = {{
\t\t\t\tis_building_type = {building_name}
\t\t\t}}
\t\t\tNOT = {{
\t\t\t\tany_state = {{
\t\t\t\t\tany_scope_building = {{
\t\t\t\t\t\tis_building_type = {building_name}
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
}}"""


def generate_inject(company_id, building_suffix):
    """Generate INJECT block for the company."""
    building_name = f"building_{building_suffix}"
    return f"""# {company_id} → Unique building
INJECT:{company_id} = {{
\tbuilding_types = {{
\t\t{building_name}
\t}}
\tprosperity_modifier = {{
\t\tstate_{building_name}_max_level_add = 1
\t}}
}}"""


def get_company_icon(company_id):
    """Find the icon path for a vanilla company by scanning its definition file."""
    vanilla_company_dir = os.path.join(base_game_path, "game", "common", "company_types")
    for filename in os.listdir(vanilla_company_dir):
        if not filename.endswith('.txt'):
            continue
        filepath = os.path.join(vanilla_company_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except:
            continue
        # Find the company definition
        pattern = re.compile(rf'^{re.escape(company_id)}\s*=\s*\{{', re.MULTILINE)
        match = pattern.search(content)
        if match:
            # Extract icon from the block
            block_start = match.start()
            # Find icon within next ~500 chars
            block = content[block_start:block_start + 1000]
            icon_match = re.search(r'icon\s*=\s*"([^"]+)"', block)
            if icon_match:
                return icon_match.group(1)
    return "gfx/interface/icons/company_icons/basic_icons/company_basic_steel.dds"


def main():
    print(f"Generating unique buildings for {len(COMPANY_BUILDINGS)} vanilla companies...")

    # Collect all outputs
    all_buildings = []
    all_pmgs = []
    all_pms = []
    all_injects = []
    all_loc = []

    for company_id, (suffix, display_name, sector, description) in sorted(COMPANY_BUILDINGS.items()):
        building_key = f"building_{suffix}"
        icon_path = get_company_icon(company_id)

        all_buildings.append(generate_building(suffix, company_id, icon_path))
        all_pmgs.append(generate_pmg(suffix))
        all_pms.append(generate_pm(suffix, display_name, sector, description))
        all_injects.append(generate_inject(company_id, suffix))

        # Localization
        # Clean display name for loc (remove backslash escapes)
        clean_name = display_name.replace("\\'", "'")
        all_loc.append(f' {building_key}:0 "{clean_name}"')

    # Write buildings
    buildings_path = os.path.join(mod_path, "common", "buildings", "company_buildings.txt")
    # Read existing content
    with open(buildings_path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()

    new_section = "\n\n#============================================================\n"
    new_section += "# Phase 7: Remaining Vanilla Flavored Company Buildings\n"
    new_section += "#============================================================\n\n"
    new_section += "\n\n".join(all_buildings)

    with open(buildings_path, 'w', encoding='utf-8-sig') as f:
        f.write(existing.rstrip() + new_section + "\n")
    print(f"  Appended {len(all_buildings)} buildings to company_buildings.txt")

    # Write PMGs
    pmg_path = os.path.join(mod_path, "common", "production_method_groups", "unique_pm_groups.txt")
    with open(pmg_path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()

    new_section = "\n\n#============================================================\n"
    new_section += "# Phase 7: Remaining Vanilla Flavored Company PMGs\n"
    new_section += "#============================================================\n\n"
    new_section += "\n".join(all_pmgs)

    with open(pmg_path, 'w', encoding='utf-8-sig') as f:
        f.write(existing.rstrip() + new_section + "\n")
    print(f"  Appended {len(all_pmgs)} PMGs to unique_pm_groups.txt")

    # Write PMs
    pm_path = os.path.join(mod_path, "common", "production_methods", "unique_pms.txt")
    with open(pm_path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()

    new_section = "\n\n#============================================================\n"
    new_section += "# Phase 7: Remaining Vanilla Flavored Company PMs\n"
    new_section += "#============================================================\n\n"
    new_section += "\n".join(all_pms)

    with open(pm_path, 'w', encoding='utf-8-sig') as f:
        f.write(existing.rstrip() + new_section + "\n")
    print(f"  Appended {len(all_pms)} PMs to unique_pms.txt")

    # Write INJECTs
    inject_path = os.path.join(mod_path, "common", "company_types", "extra_companies_vanilla_updates.txt")
    with open(inject_path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()

    new_section = "\n\n#============================================================\n"
    new_section += "# Phase 7: Remaining Vanilla Flavored Company Unique Buildings\n"
    new_section += "#============================================================\n\n"
    new_section += "\n\n".join(all_injects)

    with open(inject_path, 'w', encoding='utf-8-sig') as f:
        f.write(existing.rstrip() + new_section + "\n")
    print(f"  Appended {len(all_injects)} INJECT blocks to extra_companies_vanilla_updates.txt")

    # Write localization
    loc_path = os.path.join(mod_path, "localization", "english", "te_buildings_l_english.yml")
    with open(loc_path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()

    # Append after existing content
    new_loc = "\n".join(all_loc)
    with open(loc_path, 'w', encoding='utf-8-sig') as f:
        f.write(existing.rstrip() + "\n" + new_loc + "\n")
    print(f"  Appended {len(all_loc)} loc keys to te_buildings_l_english.yml")

    print(f"\nDone! Generated content for {len(COMPANY_BUILDINGS)} companies.")
    print("Next steps: run 'python organize_loc.py' and BOM-verify all modified files.")


if __name__ == '__main__':
    main()
