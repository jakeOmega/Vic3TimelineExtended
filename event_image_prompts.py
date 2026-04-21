"""
Event image generation prompts for Vic3TimelineExtended.

Each image definition includes:
- prompt: AI image generation description
- style: Style modifier for the generator (appended to prompt)
- events: List of event IDs that use this image

Usage:
    python event_image_prompts.py              # Print summary stats
    python event_image_prompts.py --json       # Output full JSON
    python event_image_prompts.py --validate   # Check for unmapped events

PROMPT WRITING GUIDELINES (FLUX.1-schnell, 4 steps):
=====================================================
These rules are derived from analysis of generated images.

DO:
  - Describe a single coherent physical scene (one room, one landscape, one street)
  - Use period-specific physical props (ledgers, inkwells, gas lamps, microscopes)
  - Specify clear lighting (chiaroscuro, warm lamplight, overcast sky, golden hour)
  - Use simple compositions: 1-3 focal subjects, or a crowd at distance
  - Describe posture and body language instead of facial expressions
  - Use "oil painting" styles — they produce the most consistent results
  - Anchor scenes with concrete architectural details (marble columns, brick walls)
  - Describe colors and materials explicitly (rust-red, chrome, mahogany)

DO NOT:
  - Mention signs, banners, text, writing, slogans, screens with text, chalkboard
    writing, statistics, charts, projections, or any readable content — FLUX
    generates nonsense text that ruins the image
  - Request specific national flags — they render as unrecognizable garbled designs.
    Use "flags" generically or omit them entirely
  - Use abstract/symbolic compositions ("split screen", "portraits facing each
    other", "clock ticking to midnight") — FLUX renders these as surreal collages
  - Describe animals in close-up with humans in protective gear — they merge into
    hybrid creatures. Prefer aerial/distant views for animal scenes
  - Use "every", "on every", "bristling with" for objects — FLUX interprets
    quantities hyper-literally (100+ cameras, etc.). Use "a few", "several", or
    describe ONE prominent example
  - Describe complex spatial relationships (people on both sides of a fence, one
    person passing another) — perspective and depth ordering often fails
  - Describe walking figures alone (anatomical errors like reversed heads, extra
    limbs). Prefer seated, standing, or crowd poses
  - Request holographic displays, data overlays, or floating UI — they render as
    random blobs or infinity symbols
"""

IMAGES = {
    # =========================================================================
    # AUGMENTATION EVENTS
    # =========================================================================
    "augmentation_divide": {
        "prompt": "A split cityscape showing augmented and unaugmented districts.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.1", "augmentation_events.5"],
    },
    "underground_augmentation_clinic": {
        "prompt": "An underground surgical clinic with cybernetic implants.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.2"],
    },
    "anti_augmentation_protest": {
        "prompt": "Night street protest outside a neon-lit clinic, raised hands and a police line in rain.",
        "style": "oil painting, social realism, dramatic evening light",
        "events": ["augmentation_events.3"],
    },
    "augmented_criminal": {
        "prompt": "A shadowy augmented figure on a rooftop at night.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.4"],
    },
    "unaugmented_underclass": {
        "prompt": "Workers queuing outside a factory.",
        "style": "oil painting, social realism, muted tones",
        "events": ["augmentation_events.100"],
    },
    "augmented_harmony": {
        "prompt": "A community workspace with subtle technological enhancements.",
        "style": "oil painting, impressionist, warm optimistic light",
        "events": ["augmentation_events.200"],
    },

    # =========================================================================
    # BANKING CYCLE EVENTS — MARKET ECONOMY
    # =========================================================================
    "stock_exchange_frenzy": {
        "prompt": "A bustling 19th-century stock exchange trading floor.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.1", "banking_cycle_events.5",
            "banking_cycle_events.9", "banking_cycle_events.14",
            "banking_cycle_events.17", "banking_cycle_events.22",
            "banking_cycle_events.33", "banking_cycle_events.35",
            "banking_cycle_events.43",
        ],
    },
    "bank_run_crowd": {
        "prompt": "A panicked crowd at a Victorian bank.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": ["banking_cycle_events.4", "banking_cycle_events.31"],
    },
    "banking_boardroom": {
        "prompt": "A mahogany boardroom with bank executives.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.7", "banking_cycle_events.21",
            "banking_cycle_events.23", "banking_cycle_events.26",
            "banking_cycle_events.36", "banking_cycle_events.40",
        ],
    },
    "central_bank_policy": {
        "prompt": "Officials debating policy in a neoclassical chamber.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": [
            "banking_cycle_events.8", "banking_cycle_events.10",
            "banking_cycle_events.12", "banking_cycle_events.15",
            "banking_cycle_events.16", "banking_cycle_events.19",
            "banking_cycle_events.25", "banking_cycle_events.30",
            "banking_cycle_events.34", "banking_cycle_events.39",
            "banking_cycle_events.45",
        ],
    },
    "financial_distress_street": {
        "prompt": "A distressed businessman on a rain-soaked street.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.3", "banking_cycle_events.6",
            "banking_cycle_events.11", "banking_cycle_events.28",
            "banking_cycle_events.37", "banking_cycle_events.41",
        ],
    },
    "trade_commerce_port": {
        "prompt": "A busy commercial harbor at dawn.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.2", "banking_cycle_events.27",
            "banking_cycle_events.29", "banking_cycle_events.38",
            "banking_cycle_events.42",
        ],
    },
    "financial_fraud_exposed": {
        "prompt": "A man caught with falsified ledgers by lamplight.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.13", "banking_cycle_events.18",
            "banking_cycle_events.20", "banking_cycle_events.24",
            "banking_cycle_events.32", "banking_cycle_events.44",
        ],
    },

    # =========================================================================
    # BANKING CYCLE EVENTS — PLANNED ECONOMY
    # =========================================================================
    "gosplan_factory_hall": {
        "prompt": "A vast Soviet-style factory interior.",
        "style": "oil painting, socialist realism, harsh light",
        "events": [
            "banking_cycle_events.50", "banking_cycle_events.52",
            "banking_cycle_events.57", "banking_cycle_events.101",
            "banking_cycle_events.106",
        ],
    },
    "planning_bureau": {
        "prompt": "A cramped Soviet-era planning office.",
        "style": "oil painting, socialist realism, harsh light",
        "events": [
            "banking_cycle_events.51", "banking_cycle_events.54",
            "banking_cycle_events.56", "banking_cycle_events.104",
            "banking_cycle_events.116",
        ],
    },
    "black_market_underground": {
        "prompt": "A clandestine night market in a back alley.",
        "style": "oil painting, socialist realism, harsh light",
        "events": ["banking_cycle_events.53", "banking_cycle_events.120"],
    },
    "state_bank_reserves": {
        "prompt": "Interior of a state bank vault with gold stacks.",
        "style": "oil painting, socialist realism, harsh light",
        "events": [
            "banking_cycle_events.55", "banking_cycle_events.110",
            "banking_cycle_events.115", "banking_cycle_events.117",
        ],
    },

    # =========================================================================
    # BANKING CYCLE EVENTS — COOPERATIVE ECONOMY
    # =========================================================================
    "cooperative_assembly_hall": {
        "prompt": "Workers voting in a large meeting hall.",
        "style": "oil painting, warm light, community realism",
        "events": [
            "banking_cycle_events.60", "banking_cycle_events.62",
            "banking_cycle_events.66", "banking_cycle_events.67",
            "banking_cycle_events.166",
        ],
    },
    "cooperative_strain": {
        "prompt": "Exhausted worker-owners in a cooperative workshop.",
        "style": "oil painting, warm light, community realism",
        "events": [
            "banking_cycle_events.61", "banking_cycle_events.63",
            "banking_cycle_events.65", "banking_cycle_events.154",
            "banking_cycle_events.156", "banking_cycle_events.160",
            "banking_cycle_events.165",
        ],
    },
    "cooperative_market_success": {
        "prompt": "A busy cooperative marketplace with stalls.",
        "style": "oil painting, warm light, community realism",
        "events": [
            "banking_cycle_events.64", "banking_cycle_events.151",
            "banking_cycle_events.167", "banking_cycle_events.170",
        ],
    },

    # =========================================================================
    # COVERT WARFARE EVENTS
    # =========================================================================
    "espionage_dead_drop": {
        "prompt": "A clandestine briefcase exchange at a train station.",
        "style": "oil painting, chiaroscuro, noir atmosphere",
        "events": ["covert_warfare.1", "covert_warfare.2"],
    },

    # =========================================================================
    # CULTURAL HEGEMONY EVENTS
    # =========================================================================
    "cultural_exhibition_grand": {
        "prompt": "A grand international cultural exhibition in a gallery.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.1", "cultural_hegemony.8", "cultural_hegemony.9"],
    },
    "brain_drain_airport": {
        "prompt": "Professionals at an airport departure gate.",
        "style": "oil painting, social realism, golden hour light",
        "events": ["cultural_hegemony.2"],
    },
    "media_broadcast_global": {
        "prompt": "A television broadcasting control room with monitors.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.3", "cultural_hegemony.10"],
    },
    "cultural_classroom_influence": {
        "prompt": "A classroom studying a foreign nation's culture.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.4", "cultural_hegemony.6"],
    },
    "cultural_backlash_protest": {
        "prompt": "A crowd burning imported goods at night.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["cultural_hegemony.5", "cultural_hegemony.12", "cultural_hegemony.14"],
    },
    "tech_innovation_showcase": {
        "prompt": "A technology lab with engineers and prototypes.",
        "style": "oil painting, contemporary realism, bright clinical light",
        "events": ["cultural_hegemony.7", "cultural_hegemony.16"],
    },
    "fashion_diaspora_influence": {
        "prompt": "An expatriate community market influencing a city.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.11", "cultural_hegemony.13"],
    },
    "cultural_debate_panel": {
        "prompt": "A heated panel discussion in a conference hall.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.15"],
    },

    # =========================================================================
    # DECOLONIZATION EVENTS
    # =========================================================================
    "independence_celebration": {
        "prompt": "A flag-raising at a newly independent nation's palace.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.1", "decolonization_events.5", "decolonization_events.200"],
    },
    "colonial_resistance_fighters": {
        "prompt": "Independence fighters in a jungle camp.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.2", "decolonization_events.7"],
    },
    "colonial_departure": {
        "prompt": "A colonial governor packing steamer trunks on a veranda.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.3", "decolonization_events.19"],
    },
    "partition_border_drawing": {
        "prompt": "Officials drawing borders on a large map.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.4", "decolonization_events.16"],
    },
    "post_colonial_strongman": {
        "prompt": "A military leader addressing a crowd from a balcony.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.6", "decolonization_events.14"],
    },
    "post_colonial_nation_building": {
        "prompt": "Delegates in the first session of a new parliament.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.8", "decolonization_events.9",
            "decolonization_events.11", "decolonization_events.13",
        ],
    },
    "neocolonial_dependency": {
        "prompt": "A leader signing a trade agreement in a European office.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.10", "decolonization_events.15",
            "decolonization_events.18",
        ],
    },
    "cold_war_proxy_competition": {
        "prompt": "Two superpower representatives visiting a new nation.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.12"],
    },
    "post_colonial_tensions": {
        "prompt": "A post-colonial city scene with ethnic tension.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.17", "decolonization_events.20",
            "decolonization_events.21",
        ],
    },
    "failed_state_aftermath": {
        "prompt": "A struggling post-colonial nation's empty market stalls.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.201"],
    },

    # =========================================================================
    # ENVIRONMENTAL EVENTS
    # =========================================================================
    "industrial_smog_victorian": {
        "prompt": "A 19th-century industrial city choked with smog.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.1"],
    },
    "climate_flooding_city": {
        "prompt": "A coastal city partially submerged in floodwater.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.2", "environmentalism_events.15"],
    },
    "drought_devastation": {
        "prompt": "A cracked, parched landscape under a blazing sun.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.3", "environmentalism_events.14"],
    },
    "climate_refugee_exodus": {
        "prompt": "Climate refugees walking along a dusty road.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.4", "environmentalism_events.16"],
    },
    "ecological_collapse_panorama": {
        "prompt": "A panoramic view of ecological collapse.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.5", "environmentalism_events.19", "environmentalism_events.20"],
    },
    "green_sustainable_city": {
        "prompt": "A sustainable city with vertical gardens and solar panels.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmental_events.100", "environmentalism_events.21"],
    },
    "environmental_catastrophe_final": {
        "prompt": "A panorama of environmental ruin and flooded ruins.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.200"],
    },

    # =========================================================================
    # ENVIRONMENTALISM EVENTS
    # =========================================================================
    "factory_pollution_protest": {
        "prompt": "Environmental activists protesting a coal power plant.",
        "style": "oil painting, social realism, industrial backdrop",
        "events": ["environmentalism_events.1", "environmentalism_events.2"],
    },
    "oil_spill_disaster": {
        "prompt": "An oil spill coating a coastline seen from above.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.3"],
    },
    "deforestation_contrast": {
        "prompt": "An aerial view of rainforest next to cleared land.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.4"],
    },
    "anti_nuclear_energy_march": {
        "prompt": "A massive anti-nuclear protest march.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["environmentalism_events.5"],
    },
    "renewable_energy_installation": {
        "prompt": "Workers installing a solar panel farm.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmentalism_events.6", "environmentalism_events.7"],
    },
    "nature_conservation_effort": {
        "prompt": "Volunteers planting trees in a wilderness.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.8"],
    },
    "environmental_policy_hearing": {
        "prompt": "A legislative hearing on environmental policy.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["environmentalism_events.9", "environmentalism_events.10"],
    },
    "climate_research_station": {
        "prompt": "Scientists examining ice cores in a polar research station.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["environmentalism_events.11", "environmentalism_events.12"],
    },
    "water_scarcity_queue": {
        "prompt": "People queueing for municipal water distribution.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.13"],
    },
    "wildfire_inferno": {
        "prompt": "A massive wildfire consuming a hillside.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.17"],
    },
    "green_industry_factory": {
        "prompt": "A modern green factory interior with plants.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmentalism_events.18"],
    },

    # =========================================================================
    # EXTRA LAW EVENTS
    # =========================================================================
    "parliamentary_debate_heated": {
        "prompt": "A grand parliament chamber in heated session.",
        "style": "oil painting, academic art, warm interior light",
        "events": [
            "extra_law_events.1", "extra_law_events.2", "extra_law_events.3",
            "extra_law_events.4", "extra_law_events.5", "extra_law_events.9",
            "extra_law_events.10", "extra_law_events.14", "extra_law_events.15",
            "extra_law_events.20", "extra_law_events.21", "extra_law_events.25",
            "extra_law_events.26", "extra_law_events.27", "extra_law_events.28",
            "extra_law_events.30", "extra_law_events.31", "extra_law_events.32",
            "extra_law_events.35", "extra_law_events.36",
        ],
    },
    "surveillance_cameras_cityscape": {
        "prompt": "An urban street corner dominated by a surveillance camera.",
        "style": "oil painting, contemporary realism, desaturated",
        "events": [
            "extra_law_events.6", "extra_law_events.7",
            "society_technology_events.12",
        ],
    },
    "genetics_laboratory": {
        "prompt": "A state-of-the-art genetics laboratory interior.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["extra_law_events.8"],
    },
    "automation_robots_factory": {
        "prompt": "A factory floor with synchronized robotic arms.",
        "style": "oil painting, contemporary realism, cool blue light",
        "events": ["extra_law_events.11", "extra_law_events.12"],
    },
    "language_reform_classroom": {
        "prompt": "A schoolroom in transition with a teacher and students.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["extra_law_events.13"],
    },
    "digital_privacy_screen": {
        "prompt": "A person at a desk surrounded by screens showing encrypted data.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["extra_law_events.16", "extra_law_events.17"],
    },
    "immigration_checkpoint": {
        "prompt": "Families waiting at an immigration checkpoint.",
        "style": "oil painting, social realism, institutional light",
        "events": ["extra_law_events.18", "extra_law_events.19"],
    },
    "labor_strike_picket": {
        "prompt": "Workers striking outside a factory gate.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "extra_law_events.22", "extra_law_events.23",
            "extra_law_events.29",
        ],
    },
    "media_press_freedom": {
        "prompt": "A printing press being shut down by authorities.",
        "style": "oil painting, dramatic light, press scene",
        "events": ["extra_law_events.24"],
    },
    "drug_policy_hearing": {
        "prompt": "A public hearing on drug policy with experts and citizens.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["extra_law_events.33", "extra_law_events.34"],
    },

    # =========================================================================
    # FEMINIST EVENTS
    # =========================================================================
    "feminist_equal_pay_march": {
        "prompt": "A large group of women marching in solidarity.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.1", "feminist_events.2"],
    },
    "reproductive_rights_debate": {
        "prompt": "A public forum on reproductive rights with testimonies.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.3"],
    },
    "women_in_military": {
        "prompt": "Women soldiers standing at attention with male colleagues.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.4"],
    },
    "anti_feminist_backlash": {
        "prompt": "A counter-protest confronting feminist marchers.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.5"],
    },
    "feminist_struggle_continues": {
        "prompt": "A tired yet determined woman working late at a desk.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.100"],
    },
    "gender_equality_achieved": {
        "prompt": "A boardroom meeting with equal gender representation.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.200"],
    },

    # =========================================================================
    # FMC UPDATE EVENTS (no localization — military/formation updates)
    # =========================================================================
    "military_formation_update": {
        "prompt": "A military command room with officers around a tactical map.",
        "style": "oil painting, dramatic shadows, military interior",
        "events": [
            "fmc_update_events.1", "fmc_update_events.2",
            "fmc_update_events.3", "fmc_update_events.4",
            "fmc_update_events.5", "fmc_update_events.6",
            "fmc_update_events.7",
        ],
    },

    # =========================================================================
    # HEIR EDUCATION EVENTS
    # =========================================================================
    "royal_education_tutoring": {
        "prompt": "A young royal heir being tutored in a palace library.",
        "style": "oil painting, academic art, warm golden light",
        "events": [
            "heir_education_events.1", "heir_education_events.2",
            "heir_education_events.3",
        ],
    },
    "heir_education_outcome": {
        "prompt": "A young ruler taking the throne for the first time.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["heir_education_events.200"],
    },

    # =========================================================================
    # INTERNATIONAL RELATIONS EVENTS
    # =========================================================================
    "arms_race_factories": {
        "prompt": "A massive military-industrial factory producing tanks.",
        "style": "oil painting, dramatic shadows, industrial military",
        "events": ["international_relations_events.1"],
    },
    "proxy_war_map": {
        "prompt": "A Cold War situation room with advisors around a map.",
        "style": "oil painting, chiaroscuro, Cold War atmosphere",
        "events": ["international_relations_events.2"],
    },
    "diplomatic_espionage_scandal": {
        "prompt": "Journalists crowding an embassy during a diplomatic scandal.",
        "style": "oil painting, dramatic light, political tension",
        "events": ["international_relations_events.3", "international_relations_events.103"],
    },
    "nuclear_standoff_tension": {
        "prompt": "A Cold War war room with a glowing strategic map.",
        "style": "oil painting, chiaroscuro, Cold War atmosphere",
        "events": ["international_relations_events.4"],
    },
    "detente_summit_meeting": {
        "prompt": "Two rival heads of state shaking hands across a table in a neutral country's elegant conference room. Flags of both nations and the host. Advisors watching cautiously.",
        "style": "oil painting, dramatic light, political tension",
        "events": ["international_relations_events.5", "international_relations_events.101"],
    },
    "space_rivalry_celebration": {
        "prompt": "A 1960s living room where a family watches a rival nation's rocket launch on a black-and-white television set. The father stands with arms crossed, jaw set. The mother watches with concern. Children sit on the floor, mesmerized. Through the window, a suburban neighborhood at dusk. The sting of being second.",
        "style": "oil painting, social realism, mid-century light",
        "events": ["international_relations_events.6"],
    },
    "trade_war_sanctions": {
        "prompt": "A port with cargo ships being turned away: customs officials stamp DENIED on shipping manifests, crates sit impounded on the docks. Flag-draped containers from the sanctioned nation stack up. The economic warfare of trade embargoes.",
        "style": "oil painting, contemporary realism, industrial port",
        "events": [
            "international_relations_events.7",
            "international_relations_events.102",
            "international_relations_events.104",
        ],
    },
    "cyber_warfare_operations": {
        "prompt": "A military cyber operations center: rows of monitors displaying code, network maps, and intrusion alerts. Uniformed personnel in a dark room lit only by screens. Digital warfare being waged in silence.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["international_relations_events.8"],
    },

    # =========================================================================
    # LGBTQ EVENTS
    # =========================================================================
    "pride_march_colorful": {
        "prompt": "A vibrant pride march through city streets.",
        "style": "oil painting, impressionist, vibrant rainbow light",
        "events": [
            "lgbtq_events.1",
            "society_technology_events.7", "society_technology_events.8",
        ],
    },
    "lgbtq_religious_backlash": {
        "prompt": "Religious leaders delivering a sermon opposing social change.",
        "style": "oil painting, academic art, dramatic pulpit light",
        "events": ["lgbtq_events.2"],
    },
    "hate_crime_vigil": {
        "prompt": "A candlelight vigil mourning victims of a hate crime.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.3"],
    },
    "lgbtq_military_service": {
        "prompt": "A soldier standing at attention in uniform.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.4"],
    },
    "lgbtq_marriage_debate": {
        "prompt": "A packed legislative chamber during a tense vote.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.5"],
    },
    "lgbtq_persecution_dark": {
        "prompt": "A person hiding behind a locked door, fearful.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.100"],
    },
    "lgbtq_full_equality": {
        "prompt": "A same-sex couple signing a marriage certificate.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.200"],
    },

    # =========================================================================
    # MENTAL HEALTH EVENTS
    # =========================================================================
    "workplace_burnout": {
        "prompt": "An office worker slumped at a desk late at night.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.1"],
    },
    "youth_mental_health_crisis": {
        "prompt": "A teenager sitting alone on a school corridor bench.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.2"],
    },
    "addiction_struggle": {
        "prompt": "A support group meeting in a community center.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.3"],
    },
    "ptsd_soldier_returning": {
        "prompt": "A returned soldier sitting on the edge of a bed.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.4"],
    },
    "institutional_abuse_exposed": {
        "prompt": "A journalist spreading documents exposing institutional abuse.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.5"],
    },
    "mental_health_stigma": {
        "prompt": "A person hesitating at the entrance of a mental health clinic.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.100"],
    },
    "mental_health_supported": {
        "prompt": "A modern mental health center with open doors.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.200"],
    },

    # =========================================================================
    # MINISTRY LAW EVENTS
    # =========================================================================
    "ministry_establishment": {
        "prompt": "A new government ministry being inaugurated: officials cutting a ribbon at the entrance of a grand but slightly austere building. Civil servants carry stacks of files inside. A new bureaucratic empire being born.",
        "style": "oil painting, academic art, institutional interior",
        "events": [
            "ministry_law_events.1", "ministry_law_events.2",
            "ministry_law_events.3", "ministry_law_events.4",
            "ministry_law_events.5",
        ],
    },
    "bureaucratic_turf_war": {
        "prompt": "Two senior government ministers confronting each other across a conference table, their respective staff aligned behind them like opposing armies. Files and memoranda stacked as barricades. Bureaucratic warfare in pinstripes.",
        "style": "oil painting, academic art, institutional interior",
        "events": [
            "ministry_law_events.6", "ministry_law_events.7",
            "ministry_law_events.8", "ministry_law_events.9",
            "ministry_law_events.10",
        ],
    },
    "ministry_policy_debate": {
        "prompt": "A ministerial policy meeting: officials around a polished table reviewing thick policy documents, charts projected on a screen, coffee cups and briefing folders. The unglamorous but crucial work of governance.",
        "style": "oil painting, academic art, institutional interior",
        "events": [
            "ministry_law_events.11", "ministry_law_events.12",
            "ministry_law_events.13", "ministry_law_events.14",
            "ministry_law_events.15",
        ],
    },
    "ministry_reform": {
        "prompt": "A government office in transition: old furniture being replaced, new organizational charts going up on walls, civil servants looking uncertain in a changing workplace. Reform as experienced by the people inside the machine.",
        "style": "oil painting, academic art, institutional interior",
        "events": [
            "ministry_law_events.16", "ministry_law_events.17",
            "ministry_law_events.18", "ministry_law_events.19",
        ],
    },

    # =========================================================================
    # MINOR EVENTS
    # =========================================================================
    "victorian_gentleman_duel": {
        "prompt": "Two Victorian gentlemen dueling at dawn.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["minor_events_timelineextended.2"],
    },
    "expedition_explorer": {
        "prompt": "An explorer studying a map in a tent at the wilderness edge.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["minor_events_timelineextended.3"],
    },
    "world_exhibition_fair": {
        "prompt": "A grand World's Fair exhibition hall: soaring cast-iron and glass architecture, elaborate national pavilions, crowds marveling at technological wonders — steam engines, electrical displays, exotic goods. Victorian spectacle at its most ambitious.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["minor_events_timelineextended.7"],
    },
    "foreign_investment_opportunity": {
        "prompt": "A foreign investor and a local businessman shaking hands in a colonial-era trading house. Maps, contracts, and commodity samples spread on the desk between them. Ceiling fan turning slowly. The mechanics of international capital.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["minor_events_timelineextended.8"],
    },
    "minor_event_generic": {
        "prompt": "A 19th-century newspaper office: editors reviewing galley proofs, compositors setting type, a boy running in with a telegram. The smell of ink and the urgency of breaking news in the age before radio.",
        "style": "oil painting, academic art, warm golden light",
        "events": [
            "minor_events_timelineextended.1",
            "minor_events_timelineextended.6",
            "minor_events_timelineextended.100",
        ],
    },

    # =========================================================================
    # MODERN ELECTION EVENTS
    # =========================================================================
    "election_campaign_rally": {
        "prompt": "A candidate addressing a large crowd from a decorated stage.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.1", "modern_election_events.2",
            "modern_election_events.3", "modern_election_events.4",
            "modern_election_events.5",
        ],
    },
    "social_media_campaign": {
        "prompt": "A campaign war room with staff and social media screens.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.6", "modern_election_events.7",
            "modern_election_events.8", "modern_election_events.9",
            "modern_election_events.10",
        ],
    },
    "election_debate_stage": {
        "prompt": "Two candidates at podiums on a debate stage.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.11", "modern_election_events.12",
            "modern_election_events.13", "modern_election_events.14",
            "modern_election_events.15",
        ],
    },
    "voter_registration_queue": {
        "prompt": "Citizens queuing outside a polling station.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.16", "modern_election_events.17",
            "modern_election_events.18",
        ],
    },
    "election_night_results": {
        "prompt": "Campaign staff watching results on a large screen.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.19", "modern_election_events.20",
            "modern_election_events.21", "modern_election_events.22",
        ],
    },
    "political_scandal_expose": {
        "prompt": "A crisis press conference with journalists questioning a politician.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.23", "modern_election_events.24",
            "modern_election_events.25", "modern_election_events.26",
        ],
    },
    "grassroots_canvassing": {
        "prompt": "Volunteers canvassing door-to-door in a neighborhood.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.27", "modern_election_events.28",
            "modern_election_events.29",
        ],
    },
    "election_crisis_contested": {
        "prompt": "Crowd pressing against barricades outside a government counting hall at night.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.30", "modern_election_events.31",
            "modern_election_events.32", "modern_election_events.33",
            "modern_election_events.34", "modern_election_events.35",
        ],
    },

    # =========================================================================
    # MOVEMENT EVENTS
    # =========================================================================
    "civil_rights_peaceful_march": {
        "prompt": "A massive peaceful civil rights march.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.1", "movement_events_te.2",
            "movement_events_te.3", "movement_events_te.4",
        ],
    },
    "economic_boycott_action": {
        "prompt": "A picket line outside a department store.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.5", "movement_events_te.6",
            "movement_events_te.7", "movement_events_te.8",
        ],
    },
    "draft_resistance_protest": {
        "prompt": "Men burning draft cards in a public square.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.9", "movement_events_te.10",
            "movement_events_te.11", "movement_events_te.12",
        ],
    },
    "digital_activism_screens": {
        "prompt": "Activists coordinating a campaign across multiple screens.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["movement_events_te.13", "movement_events_te.14"],
    },
    "transhumanist_demonstration": {
        "prompt": "People with visible cybernetic enhancements marching together.",
        "style": "digital painting, atmospheric, near-future protest",
        "events": ["movement_events_te.15", "movement_events_te.16"],
    },
    "movement_triumph_celebration": {
        "prompt": "A massive public celebration after a movement's victory.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["movement_events_te.100", "movement_events_te.201"],
    },
    "movement_crushed_aftermath": {
        "prompt": "Empty rain-soaked streets after a suppressed movement.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["movement_events_te.200"],
    },

    # =========================================================================
    # NUCLEAR WEAPON EVENTS
    # =========================================================================
    "nuclear_city_destruction": {
        "prompt": "A mushroom cloud rising over a city skyline.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.1"],
    },
    "tactical_nuclear_strike": {
        "prompt": "A tactical nuclear blast on a battlefield.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.2", "nuclear_weapon_events.18"],
    },
    "nuclear_fallout_contamination": {
        "prompt": "An abandoned contaminated exclusion zone with inspectors in hazmat suits.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.3", "nuclear_weapon_events.14",
            "nuclear_weapon_events.15",
        ],
    },
    "nuclear_bunker_life": {
        "prompt": "Families sheltering in a nuclear bunker.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.4"],
    },
    "nuclear_test_mushroom": {
        "prompt": "A nuclear test mushroom cloud over a desert.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.5"],
    },
    "nuclear_proliferation_threat": {
        "prompt": "Analysts reviewing satellite photos of suspected nuclear sites.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.6", "nuclear_weapon_events.7",
            "nuclear_weapon_events.16",
        ],
    },
    "nuclear_false_alarm_panic": {
        "prompt": "A missile warning center in crisis with red alert lights.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.8", "nuclear_weapon_events.17",
            "nuclear_weapon_events.20",
        ],
    },
    "anti_nuclear_movement": {
        "prompt": "A massive anti-nuclear demonstration in a city park.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["nuclear_weapon_events.9", "nuclear_weapon_events.10"],
    },
    "nuclear_diplomacy_talks": {
        "prompt": "Arms control negotiators at a treaty table.",
        "style": "oil painting, academic art, diplomatic interior",
        "events": [
            "nuclear_weapon_events.11", "nuclear_weapon_events.12",
            "nuclear_weapon_events.19", "nuclear_weapon_events.21",
        ],
    },
    "nuclear_defense_shield": {
        "prompt": "A missile defense installation with radar dishes and interceptor rockets.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.13"],
    },
    "nuclear_power_debate": {
        "prompt": "A tense public hearing on nuclear power.",
        "style": "oil painting, academic art, institutional interior",
        "events": ["nuclear_weapon_events.22"],
    },

    # =========================================================================
    # POST-SCARCITY EVENTS
    # =========================================================================
    "post_scarcity_unemployment": {
        "prompt": "A futuristic unemployment office with automated kiosks.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.1"],
    },
    "meaning_crisis_abundance": {
        "prompt": "A person in a luxurious apartment staring emptily at a perfect city.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.2"],
    },
    "ai_governance_system": {
        "prompt": "A government control room where AI systems display policy decisions.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.3"],
    },
    "neo_luddite_protest": {
        "prompt": "Protesters attacking delivery drones and automation equipment.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["post_scarcity_events.4"],
    },
    "art_renaissance_future": {
        "prompt": "A vibrant future art district full of creators and installations.",
        "style": "oil painting, impressionist, vibrant color",
        "events": ["post_scarcity_events.5"],
    },
    "post_scarcity_achieved": {
        "prompt": "A futuristic city where material needs are fully met.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["post_scarcity_events.200"],
    },

    # =========================================================================
    # RELIGIOUS REVIVAL EVENTS
    # =========================================================================
    "megachurch_spectacle": {
        "prompt": "A massive megachurch with a preacher and raised hands.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.1", "religious_revival_events.2"],
    },
    "liberation_theology_activists": {
        "prompt": "A priest organizing community aid in a poor neighborhood.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.3"],
    },
    "religious_culture_war": {
        "prompt": "A polarized town hall meeting over religious and cultural issues.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.4", "religious_revival_events.5"],
    },
    "digital_pulpit_streaming": {
        "prompt": "A religious leader preaching via live stream to viewers on phones.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.6"],
    },
    "religious_political_power": {
        "prompt": "Religious leaders meeting politicians in a government office.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.7"],
    },

    # =========================================================================
    # REPEATABLE EVENTS
    # =========================================================================
    "supply_chain_disruption": {
        "prompt": "A chaotic port with backed-up container ships and empty warehouses.",
        "style": "oil painting, contemporary realism, industrial crisis",
        "events": ["repeatable_events.10"],
    },
    "automation_displacement": {
        "prompt": "A factory floor where robots replace human workers.",
        "style": "oil painting, social realism, industrial contrast",
        "events": ["repeatable_events.20"],
    },
    "media_moral_panic": {
        "prompt": "Television studio with an agitated anchor and anxious viewers gathered in a dim living room.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["repeatable_events.30"],
    },
    "cyber_attack_infrastructure": {
        "prompt": "City infrastructure failing under a cyberattack in a dark control room.",
        "style": "oil painting, contemporary realism, emergency light",
        "events": ["repeatable_events.40"],
    },
    "space_debris_collision": {
        "prompt": "A satellite colliding with space debris, fragmenting in orbit.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["repeatable_events.50"],
    },
    "quantum_materials_lab": {
        "prompt": "Researchers examining a levitating quantum sample in a lab.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["repeatable_events.60"],
    },
    "ai_ethics_debate": {
        "prompt": "An auditorium debate on AI ethics with a robot panelist.",
        "style": "oil painting, contemporary realism, conference light",
        "events": ["repeatable_events.70"],
    },
    "gig_economy_protest": {
        "prompt": "Gig economy workers protesting outside a tech company campus.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["repeatable_events.80"],
    },
    "cultural_festival_revival": {
        "prompt": "A colorful cultural festival reviving traditional arts.",
        "style": "oil painting, impressionist, warm festival light",
        "events": ["repeatable_events.90"],
    },
    "international_development_project": {
        "prompt": "Engineers from multiple countries collaborating on infrastructure.",
        "style": "oil painting, social realism, warm light",
        "events": ["repeatable_events.100"],
    },

    # =========================================================================
    # SECULAR EVENTS
    # =========================================================================
    "religious_scandal_media": {
        "prompt": "A religious scandal breaking across newspapers and screens.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["secular_events.1"],
    },
    "social_moral_panic": {
        "prompt": "A heated community meeting over perceived moral decline.",
        "style": "oil painting, social realism, warm interior light",
        "events": ["secular_events.2", "secular_events.100"],
    },
    "new_age_spirituality_center": {
        "prompt": "A new age center with crystals and meditation cushions.",
        "style": "oil painting, impressionist, warm diffuse light",
        "events": ["secular_events.3"],
    },
    "church_state_separation": {
        "prompt": "A courtroom ruling removing religious symbols from a government building.",
        "style": "oil painting, academic art, institutional gravitas",
        "events": ["secular_events.4", "secular_events.200"],
    },
    "interfaith_dialogue_table": {
        "prompt": "Religious leaders from different faiths meeting around a table.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["secular_events.5"],
    },

    # =========================================================================
    # SOCIAL TENSIONS EVENTS
    # =========================================================================
    "terrorist_attack_aftermath": {
        "prompt": "Emergency responders working amid rubble after an attack.",
        "style": "oil painting, chiaroscuro, somber tones",
        "events": [
            "social_tensions_events.1", "social_tensions_events.2",
            "society_technology_events.11",
        ],
    },
    "corporate_lobbying_legislature": {
        "prompt": "Lobbyists and legislators exchanging briefcases in a legislative corridor.",
        "style": "oil painting, chiaroscuro, institutional power",
        "events": [
            "social_tensions_events.3", "social_tensions_events.9",
            "social_tensions_events.10",
        ],
    },
    "monopoly_corporate_tower": {
        "prompt": "A dominant corporate tower casting a shadow over the city.",
        "style": "oil painting, dramatic shadows, corporate power",
        "events": ["social_tensions_events.4"],
    },
    "police_brutality_protest": {
        "prompt": "Riot police confronting civilian protesters amid tear gas.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.5", "social_tensions_events.6"],
    },
    "wartime_atrocity_evidence": {
        "prompt": "Forensic investigators documenting wartime atrocities in a ruined village.",
        "style": "oil painting, chiaroscuro, somber tones",
        "events": ["social_tensions_events.7", "social_tensions_events.8"],
    },
    "immigration_wave_crowded": {
        "prompt": "Immigrants arriving at a crowded reception center.",
        "style": "oil painting, social realism, empathetic light",
        "events": ["social_tensions_events.11", "social_tensions_events.12"],
    },
    "religious_extremism_clash": {
        "prompt": "Religious extremists clashing with secular counter-protesters.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.13", "social_tensions_events.14"],
    },
    "globalization_protest_march": {
        "prompt": "Protesters demonstrating outside an international summit.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.15", "social_tensions_events.16"],
    },

    # =========================================================================
    # SOCIETY TECHNOLOGY EVENTS
    # =========================================================================
    "women_workforce_revolution": {
        "prompt": "Women entering a factory workforce.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.1", "society_technology_events.2"],
    },
    "contraception_revolution": {
        "prompt": "A 1960s doctor's office: a female patient receiving a prescription.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.3"],
    },
    "social_revolution_sixties": {
        "prompt": "1960s social movement collage: protests and youth culture.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.4"],
    },
    "divorce_reform_court": {
        "prompt": "A family court proceeding with a couple and judge.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.5"],
    },
    "gaming_industry_arcade": {
        "prompt": "A 1980s video game arcade with rows of cabinets.",
        "style": "oil painting, neon glow, pop culture",
        "events": ["society_technology_events.6"],
    },
    "factory_outsourced_closed": {
        "prompt": "A shuttered factory with workers outside.",
        "style": "oil painting, social realism, desolate light",
        "events": ["society_technology_events.9"],
    },
    "anti_globalization_riot": {
        "prompt": "Protesters clashing with police at an international summit.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["society_technology_events.10"],
    },
    "misinformation_spreading": {
        "prompt": "A phone screen showing a viral fabricated news article.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["society_technology_events.13"],
    },
    "election_interference_cyber": {
        "prompt": "Hackers in a dark room targeting election systems.",
        "style": "oil painting, contemporary realism, dark screen light",
        "events": ["society_technology_events.14"],
    },
    "student_protest_campus": {
        "prompt": "A university campus protest: students occupying a building, banners hanging from windows, teach-ins on the lawn. Faculty divided — some joining, some condemning. The perennial engine of youthful idealism challenging institutional complacency.",
        "style": "oil painting, social realism, campus daylight",
        "events": ["society_technology_events.15"],
    },
    "neural_interface_consumer": {
        "prompt": "A patient receiving a small neural implant in a clinical chair.",
        "style": "digital painting, clean light, near-future",
        "events": ["society_technology_events.16", "society_technology_events.20"],
    },
    "augmented_athlete_arena": {
        "prompt": "An augmented athlete sprinting in a futuristic arena.",
        "style": "digital painting, cinematic light, near-future",
        "events": ["society_technology_events.17"],
    },
    "space_habitat_future": {
        "prompt": "Interior of a rotating space habitat with parks and farms.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["society_technology_events.18", "society_technology_events.19"],
    },
    "telepathic_diplomacy_link": {
        "prompt": "Two diplomats connected by neural interfaces in a negotiation.",
        "style": "digital painting, ethereal light, speculative future",
        "events": ["society_technology_events.21"],
    },
    "nuclear_reactor_leak": {
        "prompt": "A nuclear plant incident with warning lights and workers responding.",
        "style": "oil painting, dramatic light, industrial crisis",
        "events": ["society_technology_events.22", "society_technology_events.23"],
    },
    "anti_nuclear_energy_protest": {
        "prompt": "An anti-nuclear protest camp outside a power plant.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["society_technology_events.24"],
    },
    "deepfake_crisis_screen": {
        "prompt": "Officials in a crisis room examining a viral deepfake video.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["society_technology_events.25"],
    },
    "ai_alignment_failure": {
        "prompt": "Engineers scrambling in a server room during an AI failure.",
        "style": "oil painting, contemporary realism, red warning light",
        "events": ["society_technology_events.26"],
    },
    "algorithmic_governance_office": {
        "prompt": "A government office where algorithms render routine decisions.",
        "style": "oil painting, contemporary realism, sterile light",
        "events": ["society_technology_events.27"],
    },
    "genetic_designer_baby_clinic": {
        "prompt": "Prospective parents reviewing an embryo's genetic profile in clinic.",
        "style": "oil painting, cool clinical light, near-future",
        "events": ["society_technology_events.28"],
    },
    "synthetic_food_laboratory": {
        "prompt": "Bioreactors and 3D printers producing synthetic meals.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["society_technology_events.29"],
    },
    "autonomous_vehicle_street": {
        "prompt": "A city street dominated by autonomous vehicles.",
        "style": "oil painting, contemporary realism, urban daylight",
        "events": ["society_technology_events.30", "society_technology_events.31"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Mars (1-5)
    # =========================================================================
    "colony_valles_marineris": {
        "prompt": "A Mars colony in the Valles Marineris canyon.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.1"],
    },
    "colony_olympus_mons": {
        "prompt": "A research station on the slopes of Olympus Mons.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.2"],
    },
    "colony_hellas_planitia": {
        "prompt": "A settlement in Hellas Planitia with greenhouse domes.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.3"],
    },
    "colony_utopia_planitia": {
        "prompt": "An industrial colony on Utopia Planitia with manufacturing domes.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.4"],
    },
    "colony_arcadia_planitia": {
        "prompt": "An agricultural colony exploiting subsurface ice on Arcadia Planitia.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.5"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Asteroid Belt (6-10)
    # =========================================================================
    "colony_ceres": {
        "prompt": "A waystation colony on Ceres, the largest body in the asteroid belt. Domed habitats cluster around the bright spot of Occator Crater. Low gravity means soaring interior spaces. Ships dock at an orbital tether above.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.6"],
    },
    "colony_vesta": {
        "prompt": "Mining habitat carved into Vesta crater walls, with excavators and ore haulers under a black sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.7"],
    },
    "colony_psyche": {
        "prompt": "A colony on the metallic asteroid 16 Psyche — a world made almost entirely of iron and nickel. The landscape gleams like polished metal under the distant sun. Mining lasers cut into the metallic surface.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.8"],
    },
    "colony_pallas": {
        "prompt": "A research station on 2 Pallas, a dark, carbon-rich asteroid. Scientists study ancient organic compounds in pressurized labs built into craters. The surface is dark as charcoal. Solar panels strain to catch weak sunlight.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.9"],
    },
    "colony_hygiea": {
        "prompt": "Remote icy outpost on Hygiea with fuel tanks, drilling rigs, and docked cargo shuttles.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.10"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Jupiter System (11-16)
    # =========================================================================
    "colony_io": {
        "prompt": "A hardened colony on Io, Jupiter's volcanic moon. Active volcanoes erupt sulfur plumes hundreds of kilometers high in the background. The colony sits on a rare stable plain, heavily shielded from Jupiter's intense radiation belts. Yellow-orange sulfur landscape.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.11"],
    },
    "colony_europa": {
        "prompt": "A colony on Europa's cracked ice surface. The ice shell stretches in all directions, fractured into geometric patterns. A drill station penetrates toward the subsurface ocean below.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.12"],
    },
    "colony_ganymede": {
        "prompt": "The largest colony in the Jovian system on Ganymede, the biggest moon in the solar system. A proper city under domes: multi-story buildings, parks, a university. The capital of Jupiter's moons, a beacon of civilization at 5 AU.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.13"],
    },
    "colony_callisto": {
        "prompt": "A sleepy colony on Callisto, Jupiter's outermost major moon. Chosen for its low radiation environment. Comfortable, quiet habitats on an ancient, heavily cratered surface. A retirement colony of the outer system — safe, stable, boring.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.14"],
    },
    "colony_himalia": {
        "prompt": "A tiny research outpost on Himalia, one of Jupiter's irregular moons. A handful of pressurized modules on a dark, potato-shaped rock only 170km across. The most remote manned station in the Jovian system. Jupiter a distant bright disc.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.15"],
    },
    "colony_amalthea": {
        "prompt": "A small orbital research station near Amalthea, Jupiter's inner moon, deep within the radiation belts. The reddish, elongated moon visible through reinforced viewports. Experiments on extreme radiation environments. Not a place for long stays.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.16"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Inner Planets (17-18)
    # =========================================================================
    "colony_venus_cloud": {
        "prompt": "A floating cloud city in Venus's upper atmosphere, suspended by buoyancy at 50km altitude where temperature and pressure are Earth-like. Airship habitats connected by sky-bridges, solar panels above, the impenetrable yellow cloud deck below. A fantasy made real.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.17"],
    },
    "colony_mercury": {
        "prompt": "A colony at Mercury's north pole, built inside permanently shadowed craters. Solar collectors on sunlit ridges beam power down. The colony rides the terminator — the boundary between Mercury's blazing day and frozen night.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.18"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Saturn System (19-23)
    # =========================================================================
    "colony_titan": {
        "prompt": "A colony on Titan, Saturn's largest moon. Through the thick orange haze, domed habitats sit beside a methane lake. Rain falls — not water, but liquid methane.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.19"],
    },
    "colony_enceladus": {
        "prompt": "A research colony near Enceladus's south pole, where geysers of water ice erupt from tiger-stripe fissures into space. Scientists study the plumes for signs of life from the subsurface ocean. Saturn's rings arc across the sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.20"],
    },
    "colony_saturn_icy_moon": {
        "prompt": "A small outpost on one of Saturn's mid-sized icy moons. A cratered, ice-covered landscape stretches under Saturn's magnificent ring system visible edge-on across the sky. Limited facilities, essential science, breathtaking view.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_colony_events.21",
            "space_race_colony_events.22",
            "space_race_colony_events.23",
        ],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Uranus System (24-27)
    # =========================================================================
    "colony_uranus_moon": {
        "prompt": "A remote colony on a moon of Uranus. The pale blue-green ice giant hangs sideways in the sky — its extreme axial tilt making it unique among planets. The icy moon's surface is ancient and cold.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_colony_events.24",
            "space_race_colony_events.25",
            "space_race_colony_events.26",
            "space_race_colony_events.27",
        ],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Neptune System (28-29)
    # =========================================================================
    "colony_triton": {
        "prompt": "A colony on Triton, Neptune's captured moon orbiting retrograde. Nitrogen geysers erupt from the cantaloupe-textured surface. Neptune's deep blue sphere dominates the sky. The coldest inhabited place in the solar system at -235°C.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.28"],
    },
    "colony_neptune_outpost": {
        "prompt": "A tiny automated monitoring station on Proteus, an irregularly shaped moon of Neptune. Solar panels are useless this far out — nuclear reactors power everything. Neptune's blue disc hangs in the sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.29"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Kuiper Belt & Beyond (30-34)
    # =========================================================================
    "colony_pluto_charon": {
        "prompt": "Twin colonies on Pluto and Charon linked by ship traffic across deep darkness and distant starlight.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.30"],
    },
    "colony_deep_kuiper": {
        "prompt": "A deep Kuiper Belt object colony: a small, dark, icy world billions of kilometers from the sun. The colony is entirely enclosed and nuclear-powered. Outside, the surface is so cold that atmospheric gases freeze solid. Stars everywhere, unblinking.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_colony_events.31",
            "space_race_colony_events.32",
            "space_race_colony_events.33",
        ],
    },
    "colony_sedna": {
        "prompt": "The most remote human outpost: a colony on Sedna, which takes 11,000 years to orbit the sun. Currently near perihelion, even the sun is barely a pinpoint.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.34"],
    },

    # =========================================================================
    # SPACE RACE EVENTS — Milestones (1-8)
    # =========================================================================
    "rocket_ascending_sky": {
        "prompt": "A rocket ascending through a blue sky on a pillar of flame, trailing a brilliant white exhaust plume. Spectators on the ground shield their eyes against the light. Countdown clocks at zero. The moment humanity reaches for space.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.1", "space_race_events.30"],
    },
    "orbital_earth_view": {
        "prompt": "An astronaut looking out a spacecraft window at Earth below — the thin blue atmosphere line, swirling white clouds, the curvature of the planet. The profound loneliness and beauty of orbit. Earth as a fragile island in blackness.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.2"],
    },
    "moon_landing_footprint": {
        "prompt": "An astronaut's boot pressing into lunar regolith for the first time. The bootprint is sharp and clear in the grey dust. The lunar module sits nearby, Earth hangs in the black sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.3"],
    },
    "deep_space_probe_encounter": {
        "prompt": "A space probe approaching a distant planet or gas giant, its antenna dish pointed back toward a tiny dot of Earth. The planet fills the frame with swirling storms and moons.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.4", "space_race_events.37", "space_race_events.45"],
    },
    "moon_site_selection": {
        "prompt": "Scientists and engineers gathered around a lunar globe, debating landing site options. Orbital photographs and geological surveys cover the walls. Red pins mark candidate sites. The critical decision of where to plant humanity's flag.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.5", "space_race_events.34"],
    },
    "lunar_base_dome": {
        "prompt": "A permanent lunar base taking shape: inflatable habitat modules connected by pressurized tunnels, a small greenhouse dome, solar panels and communications arrays. Astronauts in suits work outside. Earth visible on the horizon.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.6", "space_race_events.36", "space_race_events.46"],
    },
    "mars_dusty_landing": {
        "prompt": "The first crewed Mars landing: a spacecraft touching down in a cloud of red Martian dust, retro-rockets firing. Through the settling dust, the rust-colored landscape of another world emerges. History being made 225 million kilometers from home.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.7", "space_race_events.33"],
    },
    "interstellar_probe_departure": {
        "prompt": "An interstellar probe being released from a space station, its solar sail unfurling like a silver flower. It begins its years-long journey to another star system.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.8"],
    },
    # =========================================================================
    # INTERSTELLAR PROBE RESULTS — 30 unique outcomes (events 601-630)
    # Cat I: Dead Worlds & Data (601-608)
    # =========================================================================
    "probe_scorched_rock": {
        "prompt": "A barren, airless exoplanet scoured by stellar flares. The surface is cracked basalt under a red dwarf's harsh glare, with no atmosphere — just bare stone baked by radiation. Proxima Centauri looms huge and angry in the sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.601"],
    },
    "probe_tidally_locked": {
        "prompt": "A tidally locked super-Earth viewed from space: one hemisphere blazing white-hot in permanent daylight, the other in absolute darkness.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.602"],
    },
    "probe_carbon_world": {
        "prompt": "An alien world with a surface of gleaming graphite plains and diamond-studded mountain ranges under a dim, carbon-rich star. The terrain sparkles with silicate-diamond conglomerates. A world made of carbon instead of silicates — utterly unlike Earth.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.603"],
    },
    "probe_iron_world": {
        "prompt": "Bare metallic planet with iron ridges and silver plains reflecting a dim alien star.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.604"],
    },
    "probe_asteroid_belts": {
        "prompt": "Dense asteroid field of tumbling rocks lit by distant starlight, stretching endlessly in all directions.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.605"],
    },
    "probe_ice_world": {
        "prompt": "A distant, frozen exoplanet blanketed in exotic nitrogen and carbon monoxide ices, far beyond its star's habitable zone. The surface is smooth and pale, with a tenuous atmosphere that is visibly freezing and falling as snow.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.606"],
    },
    "probe_white_dwarf": {
        "prompt": "The glowing white-hot remnant of a dead star — a white dwarf surrounded by rings of pulverized planetary debris and cooling dust. The shattered remains of worlds that once orbited a living sun.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.607"],
    },
    "probe_superflare": {
        "prompt": "A colossal stellar superflare erupting from a red dwarf star, its plasma arc engulfing the magnetosphere of a nearby planet. The most violent stellar weather event ever recorded at close range — captured by an interstellar probe's instruments.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.608"],
    },

    # Cat II: Astrophysical Wonders (609-615)
    "probe_ringed_planet": {
        "prompt": "A rocky terrestrial planet adorned with a spectacular ring system — the debris of a recently destroyed moon. Backlit by its parent star, the rings shimmer with prismatic beauty.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.609"],
    },
    "probe_volcanic_world": {
        "prompt": "Super-Earth seen from orbit with erupting volcanoes and glowing lava rivers crossing continents.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.610"],
    },
    "probe_magnetic_shield": {
        "prompt": "A small rocky planet orbiting a tempestuous red dwarf, surrounded by brilliant aurora — evidence of an extraordinarily powerful magnetic field deflecting stellar radiation. The magnetosphere glows blue and purple, shielding a thin but precious atmosphere from destruction.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.611"],
    },
    "probe_ocean_world": {
        "prompt": "A planet-wide ocean world seen from orbit — no land, no continents, just a single world-spanning deep blue sea stretching to every horizon under a sky of water vapor clouds.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.612"],
    },
    "probe_geyser_moon": {
        "prompt": "An icy moon orbiting a massive gas giant, venting spectacular geysers of water and ammonia hundreds of kilometers into space. The plumes catch the distant starlight, forming temporary ice crystals that glitter against the gas giant's banded atmosphere.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.613"],
    },
    "probe_hydrocarbon_lakes": {
        "prompt": "A Titan-analog world with thick orange nitrogen-methane atmosphere and dark liquid hydrocarbon lakes reflecting the dim red light of a distant star.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.614"],
    },
    "probe_greenhouse_world": {
        "prompt": "A planet in its star's habitable zone, utterly ruined by runaway greenhouse effect — 450 degrees Celsius under a choking blanket of carbon dioxide. Venus writ large on another world.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.615"],
    },

    # Cat III: Biological Discovery (616-624)
    "probe_biosignatures": {
        "prompt": "A blue-green exoplanet viewed through spectroscopic analysis overlays showing oxygen-methane atmospheric disequilibrium — the unmistakable signature of biological activity. Life confirmed at another star.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.616"],
    },
    "probe_alien_vegetation": {
        "prompt": "False-color imagery from a probe showing an alien continent covered in photosynthetic vegetation — but instead of green, the 'red edge' spectral signature reveals vast plains of dark red and crimson plant-analog organisms harvesting starlight from a red.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.617"],
    },
    "probe_bioluminescence": {
        "prompt": "A tidally locked exoplanet viewed from its night side, with a luminous band of bioluminescent organisms glowing along the terminator — the twilight zone where organisms evolved to create their own light.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.618"],
    },
    "probe_cloud_life": {
        "prompt": "The upper atmosphere of a gas giant, where probe spectroscopy has detected complex organic polymers in impossible ratios — life in the clouds.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.619"],
    },
    "probe_purple_world": {
        "prompt": "An alien world whose continents blaze violet in probe imagery — covered in purple sulfur-metabolizing organisms that blanket the land surface.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.620"],
    },
    "probe_exotic_life": {
        "prompt": "Strange geometric mineral formations near volcanic vents on an alien world, pulsing with thermal gradients — possible non-carbon biochemistry. Life, but not as we know it: silicon-based or sulfur-based organisms that blur the line between geology and biology.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.621"],
    },
    "probe_methane_life": {
        "prompt": "A frigid alien world where liquid methane serves the role of water — and a thriving biosphere has evolved in the cold. Complex organisms breathing, growing, and reproducing at temperatures that would freeze Earth life solid.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.622"],
    },
    "probe_alien_reef": {
        "prompt": "Underwater probe imagery of vast alien reef structures — enormous biological calcium-carbonate formations built by living organisms over geological time.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.623"],
    },
    "probe_alien_mycelium": {
        "prompt": "Overcast planet surface covered by one continuous pale organic mat like giant fungal tissue.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.624"],
    },

    # Cat IV: Intelligence & Tech-signatures (625-630)
    "probe_orbital_debris": {
        "prompt": "A rocky exoplanet surrounded by an unnaturally dense cloud of orbital debris — thousands of artificial objects in decaying orbits. A dead civilization's Kessler syndrome captured by a probe's camera. Satellites, wreckage, and shrapnel choking the sky.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.625"],
    },
    "probe_industrial_atmosphere": {
        "prompt": "Hazy planet wrapped in yellow-gray smog plumes rising from geometric surface industrial complexes.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.626"],
    },
    "probe_nuclear_ruins": {
        "prompt": "Ruined coastal cities on a temperate planet with scorched zones and a faint blue radiation glow.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.627"],
    },
    "probe_radio_signal": {
        "prompt": "A probe's radio antenna array detecting faint, repeating, modulated electromagnetic emissions from a nearby star system — visualized as a signal waveform on the probe's instruments. Not natural. Carrier waves.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.628"],
    },
    "probe_city_lights": {
        "prompt": "High-resolution night-side imagery of an alien planet revealing geometric patterns of artificial light — cities, highways, coastlines traced in the unmistakable signature of electrical illumination. An alien civilization exists, now, at this very moment.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.629"],
    },
    "probe_alien_artifact": {
        "prompt": "At a Lagrange point between two bodies in an alien star system, a probe discovers a small, ancient, manufactured object — an alien artifact of unknown metal alloys, millions of years old.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.630"],
    },

    # =========================================================================
    # SPACE RACE EVENTS — Setbacks & Failures (10-26)
    # =========================================================================
    "launch_pad_explosion": {
        "prompt": "A rocket exploding on the launch pad: a fireball engulfing the launch tower, debris arcing through black smoke. Emergency vehicles racing toward the inferno. Ground crew ducking behind blast shields. The catastrophic price of reaching space.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_events.10", "space_race_events.12",
            "space_race_events.16", "space_race_events.70",
        ],
    },
    "mission_delay_hangar": {
        "prompt": "Engineers in a vast assembly building staring at a partially constructed rocket, clipboards in hand, frustration and determination on their faces. Missing components, redesigned systems, mounting delays. The unglamorous reality of rocket science.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_events.11", "space_race_events.21",
            "space_race_events.22", "space_race_events.25",
            "space_race_events.75",
        ],
    },
    "deep_space_silence": {
        "prompt": "A mission control room where operators stare at screens showing no signal. A flatlined telemetry display. Coffee cups accumulate. The desperate silence when a distant probe stops talking and billions of dollars of hardware become space junk.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.13"],
    },
    "habitat_breach_alarm": {
        "prompt": "An emergency inside a space habitat: red warning lights flash, crew members rush to seal a hull breach with emergency patches. Air visibly venting. The thin membrane between life and vacuum torn open.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.14"],
    },
    "computer_error_cockpit": {
        "prompt": "A spacecraft cockpit flooded with error messages on every screen. The pilot's hands hover over manual controls, training taking over as automated systems fail. Through the viewport, the wrong trajectory is visible. Minutes to decide.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.15", "space_race_events.23"],
    },
    "crew_medical_crisis": {
        "prompt": "A medical emergency in a spacecraft: a crew member collapsed in microgravity, another performing first aid with the ship's medical kit. Limited supplies, no hospital for millions of kilometers. The vulnerability of humans in space.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.17"],
    },
    "program_scandal_newsroom": {
        "prompt": "A newsroom breaking a space program scandal: journalists reviewing leaked documents showing cost overruns, safety shortcuts, or corruption. Headlines being typeset. The moment when the dream of space meets the reality of human institutions.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.18", "space_race_events.73"],
    },
    "sabotage_investigation": {
        "prompt": "Investigators in a rocket assembly building examining a sabotaged component with flashlights and magnifying glasses. Security personnel seal the area. Someone deliberately damaged the spacecraft. Espionage amid the stars.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.19"],
    },
    "rival_space_achievement": {
        "prompt": "A nation's leaders watching a rival country's space achievement broadcast on television screens. Mixed emotions — admiration, envy, urgency, and the sting of being second. The space race as national pride and existential competition.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.20"],
    },
    "budget_hearing_congress": {
        "prompt": "A congressional budget hearing for the space program. An administrator defends the program with models and photographs while skeptical legislators wave cost reports. The perennial battle between the dream of space and the reality of budgets.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.24", "space_race_events.26"],
    },

    # =========================================================================
    # SPACE RACE EVENTS — Technical Challenges (31-55)
    # =========================================================================
    "kessler_debris_field": {
        "prompt": "Earth orbit visualized as a deadly debris field: thousands of fragments from destroyed satellites orbiting at lethal velocity. A functioning satellite narrowly dodges debris. The Kessler Syndrome threatening to lock humanity out of orbit.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.31", "space_race_events.47"],
    },
    "astronaut_candidate_training": {
        "prompt": "Astronaut trainees enduring centrifuge and neutral-buoyancy drills in a bright training complex.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.32"],
    },
    "supply_logistics_planning": {
        "prompt": "Logistics planners surrounded by manifests, launch schedules, and supply chain diagrams for sustaining operations in space. Every kilogram costs thousands to launch. Every overlooked item could end a mission. Spreadsheets as a matter of life and death.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": [
            "space_race_events.35", "space_race_events.41",
            "space_race_events.49", "space_race_events.55",
        ],
    },
    "radiation_hazard_space": {
        "prompt": "A visualization of space radiation: solar particles streaming through a transparent spacecraft, hitting a human figure. Shielding layers partially block the radiation. Dosimeter readings climbing. The invisible enemy of deep space travel.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.40", "space_race_events.44"],
    },
    "mars_communication_room": {
        "prompt": "Mission control waiting for a Mars response: a message sent, twenty minutes of agonizing silence before any reply can arrive. Operators watching clocks, unable to help in real time. The speed of light as a prison wall.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.42"],
    },
    "life_support_biosphere": {
        "prompt": "A closed-loop life support system: plants growing in hydroponic bays, water recyclers humming, algae bioreactors producing oxygen. Engineers monitor every gram of carbon, every liter of water. A miniature Earth, engineered to sustain life indefinitely.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.43"],
    },
    "crew_psychology_isolation": {
        "prompt": "Crew members in a deep-space habitat showing the psychological effects of long isolation: one exercises obsessively, another stares out a viewport, a third reads the same book for the hundredth time. Months from Earth, years from home.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.48"],
    },

    # =========================================================================
    # SPACE RACE EVENTS — Industry & Progress (50-55, 60, 72-76)
    # =========================================================================
    "private_rocket_landing": {
        "prompt": "A private space company's reusable rocket landing on its tail on a drone ship at sea. The company logo prominently displayed. Contrails of steam, perfectly balanced on engine thrust. The commercialization of orbit.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.50"],
    },
    "space_tourism_luxury": {
        "prompt": "Wealthy space tourists floating in a luxury orbital module: champagne in zero-g, Earth visible through panoramic windows. A uniformed crew attends to them. Space travel as the ultimate vacation for the ultra-rich.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.51"],
    },
    "international_station_construction": {
        "prompt": "An international space station under construction: modules from different nations being connected by astronauts from multiple countries. Each nation's flag visible on their module. Cooperation in orbit even as tensions simmer on Earth.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.52", "space_race_events.53"],
    },
    "reentry_fireball": {
        "prompt": "A spacecraft re-entering Earth's atmosphere: surrounded by a sheath of superheated plasma, glowing orange-white against the black of space. The heat shield ablating. The most dangerous phase of any space mission — the burning road home.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.54"],
    },
    "assembly_building_fire": {
        "prompt": "Fire engulfing a rocket assembly building: flames consuming the massive structure, fire trucks surrounding it, personnel evacuating. Months or years of work destroyed in hours. The terrestrial disaster that grounds a space program.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.72"],
    },
    "capsule_seal_failure": {
        "prompt": "A spacecraft capsule on the ground failing pressure testing: engineers in hardhats examining a hairline crack in the hull with instruments.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.71"],
    },
    "engineering_breakthrough_lab": {
        "prompt": "Engineers celebrating a breakthrough in a lab: a new engine design, a lighter material, a more efficient solar cell. Whiteboards covered in equations, prototypes on benches, the eureka moment that suddenly makes the impossible possible.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.74"],
    },
    "program_cancelled_empty": {
        "prompt": "An empty space program facility: lights off, equipment covered in dust sheets, a partially built rocket standing alone in a cavernous assembly hall. The dream abandoned, the budget redirected, the engineers scattered.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.76"],
    },

    # =========================================================================
    # SURVEILLANCE EVENTS
    # =========================================================================
    "whistleblower_documents": {
        "prompt": "A whistleblower in a dimly lit room downloading classified documents onto a USB drive, reflection of screen data visible in their glasses. A decision that will change history — treason or heroism depending on who you ask.",
        "style": "oil painting, chiaroscuro, noir atmosphere",
        "events": ["surveillance_events.1"],
    },
    "data_breach_screens": {
        "prompt": "A cybersecurity operations center in crisis: screens flashing red with breach alerts, data flowing out in real time, analysts scrambling to contain the damage. Personal records of millions exposed. The digital Pandora's box opened.",
        "style": "oil painting, chiaroscuro, noir atmosphere",
        "events": ["surveillance_events.2", "surveillance_events.3"],
    },
    "predictive_policing_ai": {
        "prompt": "A police precinct using predictive algorithms: a wall-mounted screen shows a city map with heat zones of predicted crime. Officers receiving automated patrol assignments. The line between preventing crime and pre-judging citizens.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["surveillance_events.4"],
    },
    "cyber_espionage_network": {
        "prompt": "Dim operations room with analysts at many terminals and a wall of glowing network maps.",
        "style": "oil painting, chiaroscuro, screen glow",
        "events": ["surveillance_events.5"],
    },
    "surveillance_state_complete": {
        "prompt": "A sterile city street where citizens walk in orderly lines through facial recognition scanning gates. A single large surveillance camera dominates the foreground, its red light glowing. A drone hovers above. Buildings are grey and uniform. Everyone walks with eyes down. Total order, zero privacy.",
        "style": "oil painting, contemporary realism, dystopian",
        "events": ["surveillance_events.100"],
    },
    "digital_freedom_secured": {
        "prompt": "Citizens celebrating the passage of digital rights legislation: computer screens showing encrypted communications protected by law, privacy advocates embracing outside a parliament. Digital freedom encoded in law. Bright and hopeful.",
        "style": "oil painting, impressionist, bright hopeful light",
        "events": ["surveillance_events.200"],
    },

    # =========================================================================
    # TREATY ARTICLE EVENTS
    # =========================================================================
    "intelligence_sharing_success": {
        "prompt": "Intelligence officers from allied nations sharing classified briefings in a secure facility. Screens showing coordinated surveillance feeds, maps with shared threat assessments. The intimate trust of intelligence cooperation.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["treaty_article_events.1"],
    },
    "intelligence_dead_drop": {
        "prompt": "A clandestine intelligence exchange: a briefcase left under a park bench at night, a shadowy figure retrieving it while another walks away. Streetlights create pools of light and shadow. The human side of espionage.",
        "style": "oil painting, chiaroscuro, noir atmosphere",
        "events": ["treaty_article_events.2"],
    },
    "cultural_renaissance_shared": {
        "prompt": "A cultural exchange program in full bloom: an art exhibition featuring works from two allied nations side by side. Visitors from both countries mingling, musicians performing fusion compositions. Culture as the bridge between peoples.",
        "style": "oil painting, impressionist, warm gallery light",
        "events": ["treaty_article_events.3", "treaty_article_events.11"],
    },
    "nationalist_backlash_flags": {
        "prompt": "A nationalist protest against foreign cultural influence: demonstrators waving national flags and burning foreign goods. Traditional symbols held up against foreign products. The backlash against cultural integration and perceived loss of identity.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["treaty_article_events.4", "treaty_article_events.12"],
    },
    "military_disarmament_ceremony": {
        "prompt": "A formal military disarmament ceremony: soldiers from a defeated or treaty-bound nation turning in weapons under the supervision of international observers. Weapons stacked in piles. The bitter ritual of enforced peace.",
        "style": "oil painting, academic art, solemn ceremony",
        "events": ["treaty_article_events.5", "treaty_article_events.8"],
    },
    "joint_military_exercises": {
        "prompt": "Joint military exercises between allied nations: troops from different countries training together, their different uniforms and equipment mixing. Camaraderie and professionalism across language barriers. Interoperability as alliance cement.",
        "style": "oil painting, dramatic light, military field",
        "events": ["treaty_article_events.6"],
    },
    "education_initiative_school": {
        "prompt": "A school built through international cooperation: children studying from textbooks provided by a foreign ally, a building dedicated with both nations' flags. Education as the long-term investment in peace between peoples.",
        "style": "oil painting, impressionist, warm hopeful light",
        "events": ["treaty_article_events.7"],
    },
    "foreign_security_advisors": {
        "prompt": "Foreign security advisors embedded with local police or military: foreign officers in different uniforms advising local commanders. Maps and communications equipment. The ambiguous presence of foreign handlers — help or control?",
        "style": "oil painting, social realism, military advisory",
        "events": ["treaty_article_events.9"],
    },
    "population_transfer_displacement": {
        "prompt": "A forced population transfer: families being moved across a border with their possessions loaded on carts and trucks. Officials checking names against lists. The bureaucratic machinery of ethnic engineering. Grief and displacement.",
        "style": "oil painting, social realism, somber light",
        "events": ["treaty_article_events.10"],
    },

    # =========================================================================
    # UN EVENTS
    # =========================================================================
    "un_charter_signing": {
        "prompt": "The founding moment of the United Nations: delegates from many nations signing a charter document at a grand ceremony. Flashbulbs pop, flags of the world line the hall.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.1"],
    },
    "un_assembly_hall_vote": {
        "prompt": "The UN General Assembly in session: a vast hemispherical hall filled with delegates, voting boards lit up, the Secretary-General at the podium. The theater of international diplomacy where every nation has one voice.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": [
            "un_events.2", "un_events.6", "un_events.11",
            "un_events.12", "un_events.13", "un_events.20",
            "un_vote.1", "un_vote.2", "un_vote.3",
        ],
    },
    "human_rights_declaration": {
        "prompt": "The proclamation of universal human rights: a dignified official reading from a historic document at a podium, delegates from every continent listening. The aspiration that all humans are born free and equal, codified in international law.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.3", "un_events.22"],
    },
    "peacekeeping_deployment": {
        "prompt": "UN peacekeepers in distinctive blue helmets and berets deploying in a conflict zone: armored vehicles painted white, soldiers establishing checkpoints, civilians cautiously emerging. Peace kept at gunpoint by neutral third parties.",
        "style": "oil painting, social realism, conflict zone",
        "events": ["un_events.4", "un_events.102"],
    },
    "sanctions_cargo_inspection": {
        "prompt": "International sanctions enforcement: inspectors boarding a cargo ship at port, customs officers examining manifests against a sanctions list. Containers impounded, shipments blocked. Economic warfare conducted through bureaucracy.",
        "style": "oil painting, contemporary realism, industrial port",
        "events": ["un_events.5", "un_events.15"],
    },
    "humanitarian_camp_tents": {
        "prompt": "A large humanitarian refugee camp: rows of white UNHCR tents stretching to the horizon, aid workers distributing food and medicine, children playing amid the displacement. The massive infrastructure of emergency human compassion.",
        "style": "oil painting, social realism, empathetic light",
        "events": ["un_events.7", "un_events.18", "un_events.101", "un_events.103"],
    },
    "international_court_chamber": {
        "prompt": "The International Court of Justice in session: judges in robes at a raised bench, lawyers presenting arguments with maps and documents. The flags of disputing nations on either side. International law rendered in solemn judicial proceedings.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.8"],
    },
    "heritage_site_monument": {
        "prompt": "A UNESCO World Heritage Site being preserved: restoration workers carefully cleaning ancient stonework, archaeologists documenting with modern equipment. The intersection of ancient human achievement and modern conservation science.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.9"],
    },
    "un_crisis_empty_seats": {
        "prompt": "Grand international chamber with many empty desks while a few delegates argue across the floor.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.10"],
    },
    "nuclear_treaty_signing": {
        "prompt": "World leaders signing a nuclear non-proliferation treaty: pens on paper, cameras flashing, the relief of containing the worst weapons ever devised through the fragile mechanism of international agreement.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.14"],
    },
    "pandemic_hospital_ward": {
        "prompt": "A global pandemic response: an overwhelmed hospital ward with patients in rows, medical staff in full protective equipment, supply crates from international aid stacked in corridors. The world fighting a common invisible enemy.",
        "style": "oil painting, clinical light, crisis atmosphere",
        "events": ["un_events.16"],
    },
    "climate_assembly_debate": {
        "prompt": "A UN climate change session: delegates debating amid charts showing rising temperatures, sea levels, and emissions. Small island nation representatives plead for their survival. The geopolitics of a warming planet.",
        "style": "oil painting, academic art, institutional urgency",
        "events": ["un_events.17"],
    },
    "space_cooperation_station": {
        "prompt": "Representatives of multiple space agencies gathered around a model of a jointly built space station. Flags of participating nations, technical drawings, handshakes. Space exploration as the cooperative future of humanity.",
        "style": "digital painting, cinematic light, optimistic sci-fi",
        "events": ["un_events.19"],
    },
    "law_of_sea_maritime": {
        "prompt": "A maritime law conference: legal experts examining nautical charts with drawn boundaries, delegations arguing over exclusive economic zones. Ship models on the table. The carving up of the world's oceans by bureaucratic fiat.",
        "style": "oil painting, academic art, institutional grandeur",
        "events": ["un_events.21"],
    },

    # =========================================================================
    # WONDER EVENTS — Space Elevator (1-7)
    # =========================================================================
    "space_elevator_tether_descending": {
        "prompt": "A space elevator tether descending from the sky: a impossibly thin carbon nanotube cable stretching from ground to geosynchronous orbit, with a climber ascending. The base station is a massive facility.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.1"],
    },
    "space_elevator_structural_alarm": {
        "prompt": "Engineers in the space elevator control room staring at structural stress readings spiking red on their monitors. The tether sways visibly outside the observation deck. Micro-fractures detected. The tallest structure ever built threatening to fail.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.2"],
    },
    "space_elevator_complete": {
        "prompt": "Fully operational space elevator with multiple climbers moving along a tether above a vast coastal spaceport.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.3", "wonder_events.4"],
    },
    "kessler_syndrome_threat": {
        "prompt": "The space elevator threatened by Kessler Syndrome: a visualization of orbital debris threatening to sever the tether. Tracking screens show incoming debris clusters. Emergency deflection systems activating. The elevator's greatest vulnerability.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.5"],
    },
    "space_elevator_generation": {
        "prompt": "Children born and raised in the space elevator's orbital station: a school classroom with Earth visible through the floor-window. The first generation that has never lived on the ground. Gravity is something they study, not experience.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.6"],
    },
    "orbital_sovereignty_dispute": {
        "prompt": "Tense diplomatic meeting around a large orbital model while military officers watch from the edges.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.7"],
    },

    # =========================================================================
    # WONDER EVENTS — Orbital Solar Collector (10-15)
    # =========================================================================
    "orbital_solar_first_light": {
        "prompt": "Orbital mirror array casting a bright energy beam onto a desert receiving station.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.10"],
    },
    "solar_beam_misalignment": {
        "prompt": "An orbital solar beam misaligned: the concentrated sunlight striking off-target, scorching a strip of landscape. Fire and smoke where there should be a receiving station. Engineers frantically adjusting orbital mirrors. A weapon disguised as infrastructure.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.11"],
    },
    "solar_power_surplus": {
        "prompt": "Sunlit industrial region powered by giant rectennas, clean factories, and active desalination basins.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.12", "wonder_events.13"],
    },
    "solar_storm_orbital_threat": {
        "prompt": "A coronal mass ejection heading toward the orbital solar collector: the sun erupting, a wall of charged particles racing toward the fragile orbital infrastructure. Operators initiating emergency shutdown procedures. Nature vs. engineering.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.14"],
    },
    "solar_monopoly_debate": {
        "prompt": "A heated debate about who controls orbital solar power: corporations, governments, and international bodies arguing over the most valuable energy asset ever created. Screens showing power distribution maps. Control of the sun's energy as ultimate power.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.15"],
    },

    # =========================================================================
    # WONDER EVENTS — Orbital Battlestation (20-26)
    # =========================================================================
    "orbital_battlestation_construction": {
        "prompt": "A military orbital platform under construction in Earth orbit: angular, armored, bristling with weapons hardpoints and sensor arrays. Construction crews in military spacecraft work around it. A fortress in the sky. Blue Earth below, black space above.",
        "style": "digital painting, cinematic light, military sci-fi",
        "events": ["wonder_events.20"],
    },
    "orbital_surveillance_earth": {
        "prompt": "Military command deck in orbit viewing Earth below through targeting optics and wide observation windows.",
        "style": "digital painting, cinematic light, military sci-fi",
        "events": ["wonder_events.21"],
    },
    "orbital_peace_deterrence": {
        "prompt": "World leaders in a summit room with a live feed from the orbital battlestation on a large screen. The station's weapons aimed at nothing in particular — the implicit threat sufficient. Peace through the omnipresence of overwhelming force.",
        "style": "oil painting, academic art, diplomatic interior",
        "events": ["wonder_events.22", "wonder_events.25"],
    },
    "orbital_misfire_impact": {
        "prompt": "Fresh impact crater in an urban district with smoke columns and shattered streets.",
        "style": "digital painting, dramatic light, destructive impact",
        "events": ["wonder_events.23"],
    },
    "orbital_arms_race": {
        "prompt": "Earth orbit crowded with competing armed platforms and launch trails rising from multiple continents.",
        "style": "digital painting, cinematic light, military sci-fi",
        "events": ["wonder_events.24"],
    },
    "asteroid_deflection_heroic": {
        "prompt": "Orbital weapon platform firing at an incoming asteroid, fragments veering away from Earth.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.26"],
    },

    # =========================================================================
    # WONDER EVENTS — Antimatter Facility (30-35)
    # =========================================================================
    "antimatter_containment_glow": {
        "prompt": "An antimatter containment facility: a gleaming, impossibly clean chamber with a tiny glowing speck of antimatter suspended in magnetic fields at the center. The most expensive and dangerous substance ever created. Scientists watch through reinforced windows.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.30"],
    },
    "antimatter_containment_breach": {
        "prompt": "An antimatter containment breach: alarms blaring, magnetic field indicators failing, evacuation in progress. The facility glows ominously. If the containment fails completely, the annihilation will leave a crater. Seconds to prevent catastrophe.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.31", "wonder_events.34"],
    },
    "antimatter_weapons_prototype": {
        "prompt": "Secure lab where officials inspect a tiny containment device inside heavy shielding.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.32"],
    },
    "antimatter_diplomacy_power": {
        "prompt": "A diplomatic summit dominated by the nation that controls antimatter: other nations' delegates deferential, the antimatter nation's representatives confident. A single milligram of antimatter has more energy than a nuclear bomb. Ultimate leverage.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.33"],
    },
    "antimatter_propulsion_drive": {
        "prompt": "An antimatter propulsion drive being tested on a prototype spacecraft: the engine producing a brilliant beam of annihilation energy. The ship accelerates at impossible rates. Interstellar travel suddenly within reach. The ultimate engine.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.35"],
    },

    # =========================================================================
    # WORLD WAR EVENTS
    # =========================================================================
    "ideological_confrontation_speech": {
        "prompt": "A powerful leader delivering a fiery ideological speech to a massive rally. Searchlights cross the sky, banners and flags fill the stadium. The crowd roars. The rhetoric that turns disagreement into existential conflict.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.1"],
    },
    "border_skirmish_troops": {
        "prompt": "Infantry trading fire across trenches and barbed wire in cold dawn haze.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.2"],
    },
    "diplomatic_crisis_ultimatum": {
        "prompt": "A diplomatic crisis: an ambassador delivering an ultimatum document to a foreign minister. Both men's hands tremble. Behind them, military aides flip through contingency plans. The last moment before the point of no return.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.3"],
    },
    "world_war_declaration": {
        "prompt": "Leader delivering a wartime broadcast in a formal office while civilians listen on radios.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.5"],
    },
    "home_front_factory": {
        "prompt": "Packed wartime factory with workers assembling shells and engines under bright industrial lamps.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.10"],
    },
    "strategic_bombing_ruins": {
        "prompt": "A city devastated by strategic bombing: entire blocks reduced to rubble, fires still burning, civilians picking through the ruins. A cathedral standing skeletal against a smoke-filled sky. The deliberate destruction of civilization from the air.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.11"],
    },
    "resistance_underground": {
        "prompt": "An underground resistance cell meeting in a basement: radio transmitter, hidden weapons, forged documents spread on a table. Faces lit by a single bulb. Outside, occupation forces patrol. The secret war behind enemy lines.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.12"],
    },
    "war_intervention_decision": {
        "prompt": "A neutral nation's war cabinet debating intervention: generals with maps of fronts, politicians weighing public opinion, intelligence reports of atrocities. The agonizing decision of when — or whether — to enter someone else's war.",
        "style": "oil painting, chiaroscuro, military interior",
        "events": ["world_war_events.20"],
    },
    "war_weariness_homefront": {
        "prompt": "Long ration lines and grieving families in a worn city square during a prolonged war.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.30"],
    },
    "peace_conference_grand": {
        "prompt": "A grand peace conference ending a world war: delegations from exhausted nations gathered in an ornate palace. Maps of redrawn borders, terms of surrender, the exhausted relief of peace mixed with the anxiety of what comes next.",
        "style": "oil painting, academic art, grand diplomatic interior",
        "events": ["world_war_events.100"],
    },
    "regime_change_occupation": {
        "prompt": "Occupation forces overseeing regime change in a defeated nation: new flags being raised, old symbols pulled down, former officials arrested. Citizens watch — some liberated, some defeated. The bitter transformation of a conquered country.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.101"],
    },
    "reconstruction_aid_delivery": {
        "prompt": "Reconstruction aid arriving in a war-devastated city: trucks loaded with building materials, food, and medicine. Aid workers coordinating with local officials. Rubble being cleared, new foundations poured. Recovery from the ashes of war.",
        "style": "oil painting, social realism, hopeful light",
        "events": ["world_war_events.102"],
    },
    "war_crimes_tribunal": {
        "prompt": "Solemn tribunal chamber with defendants in the dock, judges elevated, and observers packed behind.",
        "style": "oil painting, academic art, institutional gravitas",
        "events": ["world_war_events.103"],
    },
    "post_war_order_map": {
        "prompt": "Diplomats redrawing the map of the world after a great war: new borders, new alliances, new spheres of influence sketched on a giant map. Some nations enlarged, others divided, some erased entirely. The tectonic restructuring of geopolitics.",
        "style": "oil painting, academic art, warm strategic light",
        "events": ["world_war_events.104", "world_war_events.105"],
    },

    # =========================================================================
    # TEST EVENT
    # =========================================================================
    "test_placeholder": {
        "prompt": "A generic Victorian-era office scene: desk with papers, inkwell, and a globe. Bookshelves line the walls. Afternoon light through a window.",
        "style": "oil painting, warm afternoon light, Victorian",
        "events": ["test_event.1"],
    },
}


# =============================================================================
# Utility Functions
# =============================================================================

def get_event_image(event_id: str) -> tuple:
    """Look up which image an event uses.

    Returns (image_key, image_dict) or (None, None) if unmapped.
    """
    for key, img in IMAGES.items():
        if event_id in img["events"]:
            return key, img
    return None, None


def get_all_mapped_events() -> set:
    """Return set of all event IDs that have an image mapping."""
    mapped = set()
    for img in IMAGES.values():
        mapped.update(img["events"])
    return mapped


def validate():
    """Check for duplicate event assignments and report stats."""
    seen = {}
    duplicates = []
    for key, img in IMAGES.items():
        for event_id in img["events"]:
            if event_id in seen:
                duplicates.append((event_id, seen[event_id], key))
            else:
                seen[event_id] = key

    total_images = len(IMAGES)
    total_events = len(seen)

    print(f"Total unique images: {total_images}")
    print(f"Total mapped events: {total_events}")
    if duplicates:
        print(f"\nDUPLICATES FOUND ({len(duplicates)}):")
        for event_id, key1, key2 in duplicates:
            print(f"  {event_id} -> {key1} AND {key2}")
    else:
        print("No duplicate event mappings.")

    return duplicates


if __name__ == "__main__":
    import json
    import sys

    if "--validate" in sys.argv:
        validate()
    elif "--json" in sys.argv:
        print(json.dumps(IMAGES, indent=2))
    elif "--list-unmapped" in sys.argv:
        # Compare against events from mod state server if available
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://localhost:8950/events")
            events = json.loads(resp.read())
            server_ids = {e["event_id"] for e in events}
        except Exception:
            server_ids = set()
            print("(mod state server unavailable, showing mapped events only)")

        mapped = get_all_mapped_events()
        if server_ids:
            unmapped = server_ids - mapped
            if unmapped:
                print(f"Unmapped events ({len(unmapped)}):")
                for eid in sorted(unmapped):
                    print(f"  {eid}")
            else:
                print("All server events are mapped!")
        print(f"\nMapped events: {len(mapped)}")
        print(f"Unique images: {len(IMAGES)}")
    else:
        print(f"Usage: python {sys.argv[0]} [--validate | --json | --list-unmapped]")
        print(f"\n  --validate     Check for duplicate event assignments")
        print(f"  --json         Output all image definitions as JSON")
        print(f"  --list-unmapped  Show events not yet mapped to images")



def get_event_image(event_id):
    """Look up which image key an event uses. Returns (key, image_dict) or (None, None)."""
    for key, img in IMAGES.items():
        if event_id in img["events"]:
            return key, img
    return None, None


def get_all_mapped_events():
    """Return set of all event IDs that have an image mapping."""
    mapped = set()
    for img in IMAGES.values():
        mapped.update(img["events"])
    return mapped


def validate(all_event_ids=None):
    """Check for duplicate event assignments and unmapped events."""
    seen = {}
    duplicates = []
    for key, img in IMAGES.items():
        for eid in img["events"]:
            if eid in seen:
                duplicates.append((eid, seen[eid], key))
            seen[eid] = key

    if duplicates:
        print("DUPLICATE EVENT ASSIGNMENTS:")
        for eid, k1, k2 in duplicates:
            print(f"  {eid} -> {k1} AND {k2}")

    if all_event_ids:
        unmapped = set(all_event_ids) - set(seen.keys())
        if unmapped:
            print(f"\nUNMAPPED EVENTS ({len(unmapped)}):")
            for eid in sorted(unmapped):
                print(f"  {eid}")

    print(f"\nTotal images: {len(IMAGES)}")
    print(f"Total mapped events: {len(seen)}")
    if all_event_ids:
        print(f"Total known events: {len(all_event_ids)}")
        print(f"Coverage: {len(seen)}/{len(all_event_ids)} ({100*len(seen)//len(all_event_ids)}%)")

    return len(duplicates) == 0


if __name__ == "__main__":
    import sys
    import json

    if "--json" in sys.argv:
        print(json.dumps(IMAGES, indent=2))
    elif "--validate" in sys.argv:
        try:
            import requests
            r = requests.get("http://localhost:8950/events", timeout=5)
            all_ids = [e["id"] for e in r.json().get("events", [])]
        except Exception:
            all_ids = None
            print("(Could not reach mod state server for full event list)")
        validate(all_ids)
    else:
        print(f"Images defined: {len(IMAGES)}")
        print(f"Events mapped: {len(get_all_mapped_events())}")
        print("\nUse --json for full output, --validate for coverage check")
