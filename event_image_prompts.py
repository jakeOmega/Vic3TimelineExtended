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
        "prompt": "A split cityscape viewed from above: one half gleaming with chrome and neon where citizens sport visible cybernetic enhancements, the other half decaying and dim where unmodified people crowd narrow streets. Rain-slicked roads reflect the contrast.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.1", "augmentation_events.5"],
    },
    "underground_augmentation_clinic": {
        "prompt": "A grimy underground surgical clinic with flickering fluorescent lights. A patient lies on a makeshift operating table surrounded by cybernetic implants, improvised medical tools, and tangled cables. A masked surgeon works by lamplight.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.2"],
    },
    "anti_augmentation_protest": {
        "prompt": "Religious protesters holding candles and raised fists outside a gleaming augmentation clinic at dusk. Mix of traditional robes and modern clothing. Tension between the warm candlelight and the clinic's cold blue glow. No visible text or writing.",
        "style": "oil painting, social realism, dramatic evening light",
        "events": ["augmentation_events.3"],
    },
    "augmented_criminal": {
        "prompt": "A shadowy figure with a glowing cybernetic eye implant and a mechanical arm crouches on a rain-soaked rooftop, overlooking a neon-lit city at night. Police searchlights sweep the streets below.",
        "style": "digital painting, atmospheric, cyberpunk mood",
        "events": ["augmentation_events.4"],
    },
    "unaugmented_underclass": {
        "prompt": "A group of tired, ordinary-looking workers in worn clothing standing in a long queue outside a factory gate in an industrial district. Through the open gate, gleaming augmented workers with chrome implants on their arms and temples walk past without looking at them. Grey overcast sky, puddles on concrete.",
        "style": "oil painting, social realism, muted tones",
        "events": ["augmentation_events.100"],
    },
    "augmented_harmony": {
        "prompt": "A diverse group of people in a bright, modern community workspace. Some have subtle technological enhancements — faint neural implant traces on temples, an elegant prosthetic arm — while others are unmodified.",
        "style": "oil painting, impressionist, warm optimistic light",
        "events": ["augmentation_events.200"],
    },

    # =========================================================================
    # BANKING CYCLE EVENTS — MARKET ECONOMY
    # =========================================================================
    "stock_exchange_frenzy": {
        "prompt": "A bustling 19th-century stock exchange trading floor. Men in top hats and frock coats shout and wave papers frantically. Ticker tape machines whir, spilling ribbon across the floor. An enormous chalkboard displays rapidly changing prices.",
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
        "prompt": "A panicked crowd of Victorian-era depositors surging toward the iron-barred doors of a grand stone bank. Women clutch purses, men push forward desperately, a few bank clerks try to maintain order behind the counter.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": ["banking_cycle_events.4", "banking_cycle_events.31"],
    },
    "banking_boardroom": {
        "prompt": "A mahogany-paneled boardroom with industrial-era bank executives in dark suits seated around a long polished table. Stacks of ledgers, inkwells, and documents. Gas lamps cast warm pools of light.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.7", "banking_cycle_events.21",
            "banking_cycle_events.23", "banking_cycle_events.26",
            "banking_cycle_events.36", "banking_cycle_events.40",
        ],
    },
    "central_bank_policy": {
        "prompt": "An ornate neoclassical government chamber with officials debating around a horseshoe table. Financial charts and gold reserves reports hang on the walls. High ceilings, marble columns, an atmosphere of institutional gravity and monetary power.",
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
        "prompt": "A distressed businessman in a bowler hat clutches a crumpled document on a rain-soaked city street, face etched with despair. Other anxious figures hurry past. Horse-drawn carriages and early gas lamps.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.3", "banking_cycle_events.6",
            "banking_cycle_events.11", "banking_cycle_events.28",
            "banking_cycle_events.37", "banking_cycle_events.41",
        ],
    },
    "trade_commerce_port": {
        "prompt": "A busy commercial harbor at dawn. Merchant vessels — a mix of sail and steam — cluster at the wharves. Dockworkers unload crates while men with ledgers and top hats oversee operations.",
        "style": "oil painting, chiaroscuro, 19th-century realism",
        "events": [
            "banking_cycle_events.2", "banking_cycle_events.27",
            "banking_cycle_events.29", "banking_cycle_events.38",
            "banking_cycle_events.42",
        ],
    },
    "financial_fraud_exposed": {
        "prompt": "A man hunched over a desk covered in falsified ledgers and dual record books, caught in the act by lamplight. Shadowy figures of investigators appear in the doorway behind him. Stacks of coins, scattered banknotes, an open safe.",
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
        "prompt": "A vast Soviet-style factory interior with massive industrial machines, propaganda murals on concrete walls, and workers in uniforms operating heavy equipment under harsh fluorescent lights. A socialist realist mural of heroic laborers dominates one wall.",
        "style": "oil painting, socialist realism, harsh light",
        "events": [
            "banking_cycle_events.50", "banking_cycle_events.52",
            "banking_cycle_events.57", "banking_cycle_events.101",
            "banking_cycle_events.106",
        ],
    },
    "planning_bureau": {
        "prompt": "A cramped Soviet-era government office. Bureaucrats in ill-fitting suits sit at wooden desks piled high with production reports and statistical tables. A large wall map bristles with colored pins marking factory locations. Portraits of leaders hang above.",
        "style": "oil painting, socialist realism, harsh light",
        "events": [
            "banking_cycle_events.51", "banking_cycle_events.54",
            "banking_cycle_events.56", "banking_cycle_events.104",
            "banking_cycle_events.116",
        ],
    },
    "black_market_underground": {
        "prompt": "A clandestine market in a dim back alley at night. People exchange goods furtively behind makeshift curtains, a lookout watches the corner. Mix of consumer goods and industrial materials laid out on blankets. Shadows, suspicion, survival.",
        "style": "oil painting, socialist realism, harsh light",
        "events": ["banking_cycle_events.53", "banking_cycle_events.120"],
    },
    "state_bank_reserves": {
        "prompt": "Interior of a state bank vault. Massive vault doors stand open, revealing stacks of gold bars and currency bundles. A uniformed commissar reviews records while guards stand at attention. Cold institutional lighting, concrete and steel.",
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
        "prompt": "A large meeting hall filled with worker-owners voting by show of hands. Simple but dignified space with wooden benches. A speaker at a lectern gestures passionately. Raised hands fill the room. Warm community atmosphere, democratic energy.",
        "style": "oil painting, warm light, community realism",
        "events": [
            "banking_cycle_events.60", "banking_cycle_events.62",
            "banking_cycle_events.66", "banking_cycle_events.67",
            "banking_cycle_events.166",
        ],
    },
    "cooperative_strain": {
        "prompt": "Exhausted worker-owners slumped over their workstations in a cooperative workshop at the end of a long shift. Account books and production schedules litter every surface. Late evening light through industrial windows.",
        "style": "oil painting, warm light, community realism",
        "events": [
            "banking_cycle_events.61", "banking_cycle_events.63",
            "banking_cycle_events.65", "banking_cycle_events.154",
            "banking_cycle_events.156", "banking_cycle_events.160",
            "banking_cycle_events.165",
        ],
    },
    "cooperative_market_success": {
        "prompt": "A busy cooperative marketplace. Producers sell directly from colorful stalls bearing the twin-pines cooperative logo. Worker-members interact with customers warmly. A community bulletin board shows meeting times and dividend announcements. Sunlit, lively.",
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
        "prompt": "A lone figure in a trench coat passes a briefcase to another in a dimly lit train station at night. Fog drifts across the platform, distant signal lights glow red. Reflections on wet concrete.",
        "style": "oil painting, chiaroscuro, noir atmosphere",
        "events": ["covert_warfare.1", "covert_warfare.2"],
    },

    # =========================================================================
    # CULTURAL HEGEMONY EVENTS
    # =========================================================================
    "cultural_exhibition_grand": {
        "prompt": "A grand international cultural exhibition in an elegant gallery. National art, sculptures, and film projections are admired by well-dressed foreign visitors. Crystal chandeliers, polished marble floors, cultural prestige made tangible.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.1", "cultural_hegemony.8", "cultural_hegemony.9"],
    },
    "brain_drain_airport": {
        "prompt": "Talented professionals — scientists in lab coats, engineers with blueprints, artists carrying portfolios — at an airport departure gate, looking back wistfully through terminal windows at the skyline of home receding in the distance.",
        "style": "oil painting, social realism, golden hour light",
        "events": ["cultural_hegemony.2"],
    },
    "media_broadcast_global": {
        "prompt": "A television broadcasting center with cameras, banks of monitors, and a global coverage map glowing on the wall. Screens show programming being beamed to every continent. The control room hums with the machinery of cultural influence.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.3", "cultural_hegemony.10"],
    },
    "cultural_classroom_influence": {
        "prompt": "A classroom in a foreign country where students eagerly study another nation's language and culture. The teaching nation's cultural artifacts — books, films, music CDs — decorate the walls alongside enthusiastic student projects.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.4", "cultural_hegemony.6"],
    },
    "cultural_backlash_protest": {
        "prompt": "An angry crowd gathered around a bonfire in a city square at night, throwing imported goods and cultural products into the flames. Fists raised in the firelight. A mix of traditional robes and modern clothing. Tension and defiance on every face.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["cultural_hegemony.5", "cultural_hegemony.12", "cultural_hegemony.14"],
    },
    "tech_innovation_showcase": {
        "prompt": "A cutting-edge technology laboratory and demonstration floor. Engineers and scientists work on advanced prototypes — robots, computing systems, medical devices — while international observers take notes. National and corporate flags on display. Innovation as power projection.",
        "style": "oil painting, contemporary realism, bright clinical light",
        "events": ["cultural_hegemony.7", "cultural_hegemony.16"],
    },
    "fashion_diaspora_influence": {
        "prompt": "A vibrant expatriate community in a foreign city: ethnic restaurants with steaming cuisine, a bustling cultural center, market stalls with traditional goods and spices. Cultural identity thriving abroad, influencing the host city's character.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.11", "cultural_hegemony.13"],
    },
    "cultural_debate_panel": {
        "prompt": "A heated panel discussion in a modern conference hall. Diverse speakers at a long table with microphones, one standing to make a point while others lean in to argue. The packed audience is visibly divided, some applauding, others frowning. Harsh overhead lights.",
        "style": "oil painting, impressionist, warm light",
        "events": ["cultural_hegemony.15"],
    },

    # =========================================================================
    # DECOLONIZATION EVENTS
    # =========================================================================
    "independence_celebration": {
        "prompt": "A newly independent nation's flag being raised for the first time at a government palace. Jubilant crowds fill the square, a military honor guard stands at attention, dignitaries in a mix of traditional and Western dress look on.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.1", "decolonization_events.5", "decolonization_events.200"],
    },
    "colonial_resistance_fighters": {
        "prompt": "Independence fighters meeting in secrecy in a jungle camp: maps spread on a rough table, weapons stacked against trees, determined faces lit by a single lantern. The struggle for self-determination in its most urgent form.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.2", "decolonization_events.7"],
    },
    "colonial_departure": {
        "prompt": "A colonial governor's household packing steamer trunks on the veranda of a colonial mansion. Local servants watch from the background. A lowered colonial flag lies folded on a chair. An era visibly ending under a tropical sky.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.3", "decolonization_events.19"],
    },
    "partition_border_drawing": {
        "prompt": "Officials in a map room drawing borders on a large map of a colonized territory with rulers and pencils. The lines cut through communities and geographic features.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.4", "decolonization_events.16"],
    },
    "post_colonial_strongman": {
        "prompt": "A military figure in a decorated uniform addressing a crowd from a wrought-iron balcony, flanked by soldiers. A newly independent flag flies overhead. Below, the crowd is a mix of genuine supporters and fearful faces.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.6", "decolonization_events.14"],
    },
    "post_colonial_nation_building": {
        "prompt": "The first session of a newly independent parliament. Delegates in a mix of traditional dress and Western suits sit in a grand but slightly worn colonial-era chamber. A new constitution displayed under glass.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.8", "decolonization_events.9",
            "decolonization_events.11", "decolonization_events.13",
        ],
    },
    "neocolonial_dependency": {
        "prompt": "A newly independent nation's leader signing a trade agreement with the former colonial power in a European capital office.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.10", "decolonization_events.15",
            "decolonization_events.18",
        ],
    },
    "cold_war_proxy_competition": {
        "prompt": "Two superpower representatives visiting a newly independent nation simultaneously — one arriving from the east, one from the west, each with crates of aid and advisors. The small nation's leader stands in the middle, calculating.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.12"],
    },
    "post_colonial_tensions": {
        "prompt": "A post-colonial city scene showing ethnic tension: overturned market stalls, smoke rising from a distant neighbourhood, soldiers at a checkpoint. The fractured legacy of colonial divide-and-rule policies made visible in urban conflict.",
        "style": "oil painting, social realism, warm golden light",
        "events": [
            "decolonization_events.17", "decolonization_events.20",
            "decolonization_events.21",
        ],
    },
    "failed_state_aftermath": {
        "prompt": "A struggling post-colonial nation: empty market stalls with rusted corrugated roofs, crumbling concrete buildings with faded independence slogans, a potholed road stretching into the distance.",
        "style": "oil painting, social realism, warm golden light",
        "events": ["decolonization_events.201"],
    },

    # =========================================================================
    # ENVIRONMENTAL EVENTS
    # =========================================================================
    "industrial_smog_victorian": {
        "prompt": "A 19th-century industrial city choked with thick yellow smog pouring from dozens of factory chimneys. Soot-blackened brick buildings, a river running dark with chemical waste. Workers trudge through grimy streets, barely visible through the haze.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.1"],
    },
    "climate_flooding_city": {
        "prompt": "A modern coastal city partially submerged in grey-brown floodwater. Skyscrapers rise from the murk, boats navigate what were once streets, people wave from rooftops awaiting rescue. A dramatic storm sky overhead.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.2", "environmentalism_events.15"],
    },
    "drought_devastation": {
        "prompt": "A vast landscape of cracked, parched earth stretching to a shimmering heat-haze horizon under a blazing sun. Skeletal dead trees stand alone. An abandoned stone farmhouse with a collapsed roof. Dust devils swirl in the distance. Everything is bleached and desiccated.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.3", "environmentalism_events.14"],
    },
    "climate_refugee_exodus": {
        "prompt": "A long column of climate refugees walking along a dusty road carrying their possessions — bundles, children, water jugs. Behind them, a devastated landscape: either flooded coastline or scorched farmland. Modern clothing. Exhaustion, desperation, but forward motion.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.4", "environmentalism_events.16"],
    },
    "ecological_collapse_panorama": {
        "prompt": "A panoramic view of ecological collapse: dead fish float in a polluted lake, withered forests stand skeletal against a smoggy sky, industrial facilities loom in the background still pumping smoke. A world choking on its own output.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.5", "environmentalism_events.19", "environmentalism_events.20"],
    },
    "green_sustainable_city": {
        "prompt": "A thriving sustainable city of the future: buildings covered in vertical gardens and solar panels, wind turbines spinning on the skyline, clean rivers flowing through parks, electric vehicles and bicycles on tree-lined streets. Blue sky, abundant greenery.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmental_events.100", "environmentalism_events.21"],
    },
    "environmental_catastrophe_final": {
        "prompt": "A devastating panorama showing the end result of unchecked environmental destruction: flooded coastal ruins, scorched inland deserts, abandoned cities overgrown with desperate vegetation. The last light of a polluted sunset over a wounded world.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmental_events.200"],
    },

    # =========================================================================
    # ENVIRONMENTALISM EVENTS
    # =========================================================================
    "factory_pollution_protest": {
        "prompt": "A crowd of environmental activists wearing gas masks and raising fists outside the iron gates of a massive coal-burning power plant. Black smoke billows from smokestacks behind them. Riot police in helmets form a line between the crowd and the gates. Gritty industrial backdrop.",
        "style": "oil painting, social realism, industrial backdrop",
        "events": ["environmentalism_events.1", "environmentalism_events.2"],
    },
    "oil_spill_disaster": {
        "prompt": "A coastline devastated by an oil spill seen from above. Thick black crude oil washes over a sandy beach in dark ribbons, staining the surf line. Orange containment booms snake through the water. An oil tanker lists on the horizon trailing a dark slick. Overcast grey sky.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.3"],
    },
    "deforestation_contrast": {
        "prompt": "An aerial view showing the stark boundary between lush tropical rainforest and freshly cleared, burned land. Logging trucks and heavy equipment carve roads into the devastation. Wisps of smoke rise from smoldering stumps.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.4"],
    },
    "anti_nuclear_energy_march": {
        "prompt": "A massive anti-nuclear protest march filling city streets. Thousands carry radiation hazard symbols and sunflowers. Families with children march alongside activists. A distant nuclear power plant's cooling towers visible on the horizon.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["environmentalism_events.5"],
    },
    "renewable_energy_installation": {
        "prompt": "A wide ground-level view of a solar panel farm being constructed on open land. Workers in hard hats and high-visibility vests carry and bolt panels into metal frames. Wind turbines spin on a ridge behind them against a blue sky with scattered clouds. Clean, optimistic, industrial progress.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmentalism_events.6", "environmentalism_events.7"],
    },
    "nature_conservation_effort": {
        "prompt": "Park rangers and volunteers planting trees and marking protected boundaries in a pristine wilderness. Wildlife — deer, birds — visible in the middle distance. A clear river runs through the scene.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.8"],
    },
    "environmental_policy_hearing": {
        "prompt": "A tense legislative hearing on environmental policy. Environmental advocates with charts of rising temperatures face off against industry representatives with economic projections. Committee members behind a raised bench listen gravely.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["environmentalism_events.9", "environmentalism_events.10"],
    },
    "climate_research_station": {
        "prompt": "Climate scientists in a polar research station examining ice core samples under bright laboratory lights. Screens behind them display alarming temperature trend graphs and satellite imagery of shrinking ice caps. The contrast between clinical precision and existential urgency.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["environmentalism_events.11", "environmentalism_events.12"],
    },
    "water_scarcity_queue": {
        "prompt": "A long queue of people with buckets and containers waiting at a municipal water distribution point. Armed guards oversee rationing. An empty reservoir stretches out behind them under a hazy sky. A modern urban setting experiencing resource scarcity.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.13"],
    },
    "wildfire_inferno": {
        "prompt": "A massive wildfire consuming a forested hillside, flames leaping between trees. Nearby suburban homes threatened by the advancing fire. Firefighters in protective gear battle the blaze with hoses. Thick smoke fills an orange-red sky.",
        "style": "oil painting, landscape, dramatic sky",
        "events": ["environmentalism_events.17"],
    },
    "green_industry_factory": {
        "prompt": "A modern green factory interior: clean automated production lines, living walls of plants along the corridors, solar panels visible through skylights, electric delivery vehicles loading at the dock. Proof that industry and sustainability coexist.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["environmentalism_events.18"],
    },

    # =========================================================================
    # EXTRA LAW EVENTS
    # =========================================================================
    "parliamentary_debate_heated": {
        "prompt": "A grand parliament chamber in heated session. Representatives stand, gesture passionately, some jeer from their benches. The Speaker pounds a gavel. Gas lamps and early electric lights illuminate oak paneling and green leather benches.",
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
        "prompt": "A grey urban street corner with a prominent surveillance camera mounted on a pole in the foreground, its red recording light glowing. Citizens walk past on the sidewalk below, hunched and uneasy. The buildings are concrete and glass, austere. An oppressive, watched atmosphere. Overcast sky.",
        "style": "oil painting, contemporary realism, desaturated",
        "events": [
            "extra_law_events.6", "extra_law_events.7",
            "society_technology_events.12",
        ],
    },
    "genetics_laboratory": {
        "prompt": "A state-of-the-art genetics laboratory interior. Scientists in white coats work with pipettes, microscopes, and centrifuges at stainless steel benches. Rows of glass vials and petri dishes glow under cold fluorescent lights. Clinical, sterile, precision-focused.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["extra_law_events.8"],
    },
    "automation_robots_factory": {
        "prompt": "A modern factory floor where robotic arms perform precise assembly work in perfect synchronization. A few human supervisors monitor from behind glass partitions. The contrast between tireless machine efficiency and concerned human redundancy.",
        "style": "oil painting, contemporary realism, cool blue light",
        "events": ["extra_law_events.11", "extra_law_events.12"],
    },
    "language_reform_classroom": {
        "prompt": "A schoolroom in transition: old textbooks piled on the teacher's desk, a teacher gesturing toward a clean chalkboard while children sit attentively at wooden desks. Morning sunlight streaming through tall windows. The quiet moment of cultural change.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["extra_law_events.13"],
    },
    "digital_privacy_screen": {
        "prompt": "A person at a desk surrounded by multiple computer screens showing encrypted data, VPN connections, digital lock icons, and privacy shields. The blue glow of cybersecurity in a dark room. The tension between digital freedom and digital control.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["extra_law_events.16", "extra_law_events.17"],
    },
    "immigration_checkpoint": {
        "prompt": "An immigration checkpoint: families with documents and suitcases wait in long queues while border officers examine papers behind windows. Some applicants turned away, others waved through. Bureaucratic but deeply human.",
        "style": "oil painting, social realism, institutional light",
        "events": ["extra_law_events.18", "extra_law_events.19"],
    },
    "labor_strike_picket": {
        "prompt": "Workers on strike outside a factory gate. Fists raised high in solidarity, faces set with determination. Smoke rises from a brazier where strikers warm their hands. Police watch from across the street. Industrial brickwork background.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "extra_law_events.22", "extra_law_events.23",
            "extra_law_events.29",
        ],
    },
    "media_press_freedom": {
        "prompt": "A printing press being shut down by uniformed authorities. Loose papers scattered across the floor, journalists protesting with raised fists. The stark conflict between press freedom and government censorship. Ink-stained hands and broken machinery.",
        "style": "oil painting, dramatic light, press scene",
        "events": ["extra_law_events.24"],
    },
    "drug_policy_hearing": {
        "prompt": "A public hearing on drug policy: medical experts with charts, law enforcement in uniform, and affected citizens testifying at microphones. Evidence displays, policy documents, a complex and emotionally charged social debate.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["extra_law_events.33", "extra_law_events.34"],
    },

    # =========================================================================
    # FEMINIST EVENTS
    # =========================================================================
    "feminist_equal_pay_march": {
        "prompt": "A large group of women marching arm-in-arm through city streets with determination on their faces. A diverse group — factory workers in coveralls, office employees in blouses, professionals in suits — united in solidarity. Bystanders watch from the sidewalks, some cheering, some hostile.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.1", "feminist_events.2"],
    },
    "reproductive_rights_debate": {
        "prompt": "A tense public forum on reproductive rights. Women testifying at microphones, legislators listening from a raised bench, protesters visible through the committee room windows. Medical charts and legal documents on display.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.3"],
    },
    "women_in_military": {
        "prompt": "Women soldiers in uniform standing at attention alongside male colleagues at a military parade ground. Some onlookers approve, others look uncertain. The integration of women into military service made visible.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.4"],
    },
    "anti_feminist_backlash": {
        "prompt": "A counter-protest against feminist reforms: conservative demonstrators confronting feminist marchers, angry faces on both sides. Police form a barrier between the groups. Tension, anger, and the culture war made physical.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.5"],
    },
    "feminist_struggle_continues": {
        "prompt": "A tired but determined woman at a desk late at night, surrounded by papers and policy documents. Through the window, city lights.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.100"],
    },
    "gender_equality_achieved": {
        "prompt": "A boardroom meeting with equal representation of men and women in leadership positions. Natural, unremarkable — equality as the new normal. Modern glass-walled office, city view, professional collaboration.",
        "style": "oil painting, social realism, warm light",
        "events": ["feminist_events.200"],
    },

    # =========================================================================
    # FMC UPDATE EVENTS (no localization — military/formation updates)
    # =========================================================================
    "military_formation_update": {
        "prompt": "A military command room with officers gathered around a large tactical map table. Unit markers and formation diagrams spread across the surface. Uniformed staff update positions with pointer sticks. Serious, professional, wartime planning.",
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
        "prompt": "A young royal heir being tutored in a grand palace library. An elderly scholar with spectacles points to a globe while the young student takes notes at an ornate desk.",
        "style": "oil painting, academic art, warm golden light",
        "events": [
            "heir_education_events.1", "heir_education_events.2",
            "heir_education_events.3",
        ],
    },
    "heir_education_outcome": {
        "prompt": "A young ruler taking the throne for the first time, well-prepared by years of education. Courtiers bow, advisors stand ready, the weight of responsibility visible but manageable. Grand throne room, regal but human.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["heir_education_events.200"],
    },

    # =========================================================================
    # INTERNATIONAL RELATIONS EVENTS
    # =========================================================================
    "arms_race_factories": {
        "prompt": "A massive military-industrial complex: factories churning out tanks and artillery pieces on parallel assembly lines. Workers and engineers move urgently. Production charts on the walls climb steeply. A nation arming itself at breakneck speed.",
        "style": "oil painting, dramatic shadows, industrial military",
        "events": ["international_relations_events.1"],
    },
    "proxy_war_map": {
        "prompt": "A Cold War era situation room: military advisors lean over a map of a distant country, pushing miniature flags and unit markers. Cables from the field pile up on a desk.",
        "style": "oil painting, chiaroscuro, Cold War atmosphere",
        "events": ["international_relations_events.2"],
    },
    "diplomatic_espionage_scandal": {
        "prompt": "A diplomatic scandal breaking: journalists crowd outside an embassy as a disgraced diplomat is escorted to a waiting car. Flashbulbs pop, reporters shout questions. The carefully maintained facade of international relations cracking in public.",
        "style": "oil painting, dramatic light, political tension",
        "events": ["international_relations_events.3", "international_relations_events.103"],
    },
    "nuclear_standoff_tension": {
        "prompt": "A tense Cold War-era war room: generals and politicians hunched over a glowing strategic map table showing missile trajectories. Red telephones and radar screens cast harsh light on grim faces. The room is underground, concrete walls, a sense of impending doom.",
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
        "prompt": "A vibrant pride march through city streets: rainbow flags, colorful costumes, people of all ages celebrating. Some marchers hold signs demanding rights, others dance. The atmosphere is joyful but purposeful — celebration as protest.",
        "style": "oil painting, impressionist, vibrant rainbow light",
        "events": [
            "lgbtq_events.1",
            "society_technology_events.7", "society_technology_events.8",
        ],
    },
    "lgbtq_religious_backlash": {
        "prompt": "Religious leaders in vestments delivering a sermon against social change from an ornate pulpit. The packed congregation below is a mix of fervent agreement and quiet discomfort. Stained glass casts colored light across the scene.",
        "style": "oil painting, academic art, dramatic pulpit light",
        "events": ["lgbtq_events.2"],
    },
    "hate_crime_vigil": {
        "prompt": "A candlelight vigil in a public square at night. Hundreds of people hold candles and flowers, mourning victims of a hate crime. A makeshift memorial of photographs and messages. Grief, solidarity, and quiet determination.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.3"],
    },
    "lgbtq_military_service": {
        "prompt": "A soldier standing at attention in uniform, their identity visible but their professionalism unquestioned. Fellow service members stand alongside. The tension between institutional conformity and personal identity, resolved in competence.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.4"],
    },
    "lgbtq_marriage_debate": {
        "prompt": "A packed legislative chamber during a tense vote. Legislators at their desks, some standing to speak, some conferring urgently. The public gallery above is packed shoulder-to-shoulder, faces strained with emotion — hope, anger, anxiety. The weight of history in a wood-paneled room.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.5"],
    },
    "lgbtq_persecution_dark": {
        "prompt": "A person hiding in shadow behind a locked door, listening fearfully to footsteps outside. The door is scratched and battered. A small rainbow pin hidden in a pocket. Persecution and the cost of being forced into hiding.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.100"],
    },
    "lgbtq_full_equality": {
        "prompt": "A same-sex couple signing their marriage certificate at a government office, surrounded by friends and family. No fanfare, no protest — just the quiet normalcy of equal treatment under the law. Warm natural light.",
        "style": "oil painting, social realism, warm light",
        "events": ["lgbtq_events.200"],
    },

    # =========================================================================
    # MENTAL HEALTH EVENTS
    # =========================================================================
    "workplace_burnout": {
        "prompt": "An office worker slumped at a desk covered in papers at 3 AM, coffee cups stacked, the glow of a computer screen the only light. Their reflection in the dark window shows exhaustion. The modern epidemic of burnout.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.1"],
    },
    "youth_mental_health_crisis": {
        "prompt": "A teenager sitting alone on a bench in a school corridor, slumped forward with head in hands. Backpack on the floor beside them. The corridor stretches empty in both directions, fluorescent lights humming. A closed office door nearby. Loneliness and isolation in an institutional setting.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.2"],
    },
    "addiction_struggle": {
        "prompt": "A support group meeting in a community center: people sitting in a circle of folding chairs, one person speaking while others listen with recognition and empathy. Harsh fluorescent lights, institutional room, but genuine human connection.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.3"],
    },
    "ptsd_soldier_returning": {
        "prompt": "A returned soldier sitting on the edge of a bed in a quiet room, staring at nothing. Military uniform draped over a chair. Through the window, a peaceful neighborhood. The invisible wounds that follow warriors home.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.4"],
    },
    "institutional_abuse_exposed": {
        "prompt": "An investigative journalist spreading documents across a desk, photographs and records exposing institutional abuse. Headlines being written, sources being protected. The machinery of accountability and the courage to reveal.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.5"],
    },
    "mental_health_stigma": {
        "prompt": "A person standing at the threshold of a mental health clinic, hesitating to enter. Passersby on the street glance with judgment. The invisible barrier of stigma made visible in body language and architecture.",
        "style": "oil painting, intimate realism, empathetic light",
        "events": ["mental_health_events.100"],
    },
    "mental_health_supported": {
        "prompt": "A bright, modern mental health center: welcoming reception, comfortable therapy rooms visible through open doors, a garden courtyard. People entering without hesitation. Mental healthcare integrated into daily life.",
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
        "prompt": "Two Victorian gentlemen facing each other at dawn in a misty field, pistols raised. Seconds stand by with cases. A doctor waits with his bag. The anachronistic ritual of honor about to be settled.",
        "style": "oil painting, academic art, warm golden light",
        "events": ["minor_events_timelineextended.2"],
    },
    "expedition_explorer": {
        "prompt": "An adventurous explorer studying a map in a tent on the edge of an uncharted wilderness. Equipment, journals, compass, and a lantern. The tent flap opens onto vast, unknown terrain — mountains, jungle, or steppe.",
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
        "prompt": "A political candidate addressing a large crowd from a stage decorated with bunting and colorful streamers. Supporters pack the venue, hands raised in enthusiasm, confetti drifting down. Bright stage lights cut through the atmosphere. A mix of genuine passion and political theater.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.1", "modern_election_events.2",
            "modern_election_events.3", "modern_election_events.4",
            "modern_election_events.5",
        ],
    },
    "social_media_campaign": {
        "prompt": "A modern campaign war room: young staffers at laptops, multiple screens showing social media feeds, trending hashtags, and engagement metrics. A whiteboard covered in strategy. Digital campaigning replacing shoe leather.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.6", "modern_election_events.7",
            "modern_election_events.8", "modern_election_events.9",
            "modern_election_events.10",
        ],
    },
    "election_debate_stage": {
        "prompt": "Two political candidates at podiums on a televised debate stage. Split-screen monitors, audience in tiered seating, moderator at a central desk. The theatrical confrontation of democratic contest under harsh studio lights.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.11", "modern_election_events.12",
            "modern_election_events.13", "modern_election_events.14",
            "modern_election_events.15",
        ],
    },
    "voter_registration_queue": {
        "prompt": "Citizens queuing outside a polling station on election day. A mix of ages and backgrounds, some with 'I Voted' stickers, others bringing children. Poll workers at tables check IDs. The mundane heroism of participatory democracy.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.16", "modern_election_events.17",
            "modern_election_events.18",
        ],
    },
    "election_night_results": {
        "prompt": "An election night campaign headquarters: a large room full of campaign staff clutching phones and drinks, watching a large wall-mounted screen with rapt attention. Some people embrace in celebration, others stare in disbelief. Paper cups and crumpled napkins everywhere. The raw emotion of a political verdict.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.19", "modern_election_events.20",
            "modern_election_events.21", "modern_election_events.22",
        ],
    },
    "political_scandal_expose": {
        "prompt": "A press conference in crisis: a politician sweating under camera lights, journalists shouting questions, aides whispering urgently. Documents and photographs displayed on easels. The scandal breaking in real time.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.23", "modern_election_events.24",
            "modern_election_events.25", "modern_election_events.26",
        ],
    },
    "grassroots_canvassing": {
        "prompt": "Campaign volunteers going door-to-door in a residential neighborhood: clipboard in hand, campaign literature, earnest conversations on front porches. Lawn signs in competing party colors. Ground-level democracy.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "modern_election_events.27", "modern_election_events.28",
            "modern_election_events.29",
        ],
    },
    "election_crisis_contested": {
        "prompt": "A chaotic scene outside a government vote-counting center at night. Rival groups of citizens confront each other, separated by police in riot gear. Legal officials with briefcases push through the crowd toward the building entrance. Floodlights, tension, democracy under strain.",
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
        "prompt": "A massive peaceful civil rights march through a wide city avenue. Tens of thousands of people of diverse backgrounds walk together, arms linked, filling the street from building to building. Determination and solidarity on every face. The sheer scale of collective moral purpose.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.1", "movement_events_te.2",
            "movement_events_te.3", "movement_events_te.4",
        ],
    },
    "economic_boycott_action": {
        "prompt": "A picket line outside a large department store. Determined people stand shoulder to shoulder blocking the entrance, arms linked. Through the shop windows, empty shelves are visible. A few passersby hesitate, some turning away. Tension between economic disruption and moral conviction.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.5", "movement_events_te.6",
            "movement_events_te.7", "movement_events_te.8",
        ],
    },
    "draft_resistance_protest": {
        "prompt": "Young men burning draft cards in a public square while a crowd watches — some cheering, some horrified. Police approach from the edges. A bonfire of conscription notices. The moral crisis of compulsory military service.",
        "style": "oil painting, social realism, dramatic light",
        "events": [
            "movement_events_te.9", "movement_events_te.10",
            "movement_events_te.11", "movement_events_te.12",
        ],
    },
    "digital_activism_screens": {
        "prompt": "Activists coordinating a digital campaign: multiple screens showing social media posts going viral, encrypted messaging apps, real-time protest coordination maps. The revolution will be live-streamed.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["movement_events_te.13", "movement_events_te.14"],
    },
    "transhumanist_demonstration": {
        "prompt": "A crowd of people with visible cybernetic enhancements — chrome arms, temple implants, glowing eye augments — marching alongside unmodified allies through a near-future city street. Arms raised in solidarity. Rain-slicked pavement reflects neon shopfronts.",
        "style": "digital painting, atmospheric, near-future protest",
        "events": ["movement_events_te.15", "movement_events_te.16"],
    },
    "movement_triumph_celebration": {
        "prompt": "A massive celebration after a movement achieves its goals: crowds pouring into a public square, embracing, weeping with joy. A monument or legislative building in the background. The cathartic moment of victory after years of struggle.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["movement_events_te.100", "movement_events_te.201"],
    },
    "movement_crushed_aftermath": {
        "prompt": "The aftermath of a crushed social movement: empty rain-soaked streets where marchers once gathered. Scattered debris — shoes, umbrellas, trampled flowers — litters the pavement. A lone figure walks away into the distance past a line of riot police. The silence after suppression.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["movement_events_te.200"],
    },

    # =========================================================================
    # NUCLEAR WEAPON EVENTS
    # =========================================================================
    "nuclear_city_destruction": {
        "prompt": "A mushroom cloud rising over a city skyline. The shockwave ripples outward, buildings silhouetted against the blinding flash. The most terrifying image in human history rendered in devastating clarity.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.1"],
    },
    "tactical_nuclear_strike": {
        "prompt": "A tactical nuclear detonation on a battlefield: a smaller but devastating mushroom cloud rising from a military target. Fortifications vaporized, vehicles overturned by the blast wave. Soldiers in the distance shield their eyes.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.2", "nuclear_weapon_events.18"],
    },
    "nuclear_fallout_contamination": {
        "prompt": "A contaminated exclusion zone after nuclear exposure: abandoned rusting vehicles on a cracked road, dead brown vegetation, empty concrete apartment buildings with dark windows. Inspectors in bright yellow hazmat suits walk through the eerie stillness with detection instruments. An invisible poison permeating everything.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.3", "nuclear_weapon_events.14",
            "nuclear_weapon_events.15",
        ],
    },
    "nuclear_bunker_life": {
        "prompt": "Families sheltering in a nuclear bunker: bunk beds, canned food supplies, a crackling radio providing updates. Children playing with makeshift toys. The claustrophobic normality of life underground while the world above is poisoned.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.4"],
    },
    "nuclear_test_mushroom": {
        "prompt": "A nuclear weapons test in a remote desert. A mushroom cloud rises into a clear blue sky, dwarfing the observation bunkers in the foreground. Scientists watch through darkened goggles. The terrible beauty of atomic physics unleashed.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.5"],
    },
    "nuclear_proliferation_threat": {
        "prompt": "A darkened intelligence briefing room: satellite photographs of suspected nuclear facilities spread across a light table. Analysts point to cooling towers and centrifuge halls. The anxious geometry of proliferation detection.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.6", "nuclear_weapon_events.7",
            "nuclear_weapon_events.16",
        ],
    },
    "nuclear_false_alarm_panic": {
        "prompt": "A missile warning center in crisis: officers rushing to stations, red alert lights flashing, radar screens showing incoming tracks. A commander reaches for the phone to the head of state.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": [
            "nuclear_weapon_events.8", "nuclear_weapon_events.17",
            "nuclear_weapon_events.20",
        ],
    },
    "anti_nuclear_movement": {
        "prompt": "A massive anti-nuclear weapons demonstration filling a city park: hundreds of thousands of people crowded together, some holding sunflowers, others with candles. Speakers on a distant stage address the vast crowd. The sheer scale of collective refusal, a sea of humanity united against annihilation.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["nuclear_weapon_events.9", "nuclear_weapon_events.10"],
    },
    "nuclear_diplomacy_talks": {
        "prompt": "Arms control negotiators seated across a long table in a Geneva-style conference room. Flags of nuclear powers, thick treaty documents, translators with headphones. The painstaking, vital work of preventing extinction through bureaucracy.",
        "style": "oil painting, academic art, diplomatic interior",
        "events": [
            "nuclear_weapon_events.11", "nuclear_weapon_events.12",
            "nuclear_weapon_events.19", "nuclear_weapon_events.21",
        ],
    },
    "nuclear_defense_shield": {
        "prompt": "A missile defense installation: radar dishes aimed at the sky, interceptor rockets on launch rails, screens tracking trajectories. The technological promise — or illusion — of a shield against nuclear annihilation.",
        "style": "oil painting, dramatic light, apocalyptic tone",
        "events": ["nuclear_weapon_events.13"],
    },
    "nuclear_power_debate": {
        "prompt": "A tense public hearing in an institutional chamber. On one side of the aisle, nuclear industry executives in hard hats and suits. On the other, anxious citizens and environmental activists. Scientists testify at the front table. The room is packed and divided. Wood paneling, institutional gravitas.",
        "style": "oil painting, academic art, institutional interior",
        "events": ["nuclear_weapon_events.22"],
    },

    # =========================================================================
    # POST-SCARCITY EVENTS
    # =========================================================================
    "post_scarcity_unemployment": {
        "prompt": "A futuristic unemployment office: sleek architecture, but the faces are desperate. Automated kiosks replace human clerks. Outside the windows, robot-operated factories hum along perfectly without human workers. Abundance without purpose.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.1"],
    },
    "meaning_crisis_abundance": {
        "prompt": "A person sitting on a designer couch in a luxurious modern apartment filled with every material comfort — gourmet food on a table, entertainment devices, designer furniture — staring out a floor-to-ceiling window at a gleaming perfect city with a hollow, empty expression. Abundance without purpose.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.2"],
    },
    "ai_governance_system": {
        "prompt": "A gleaming government building where AI systems displayed on wall-sized screens process policy decisions. A few human overseers sit at consoles, monitoring but rarely intervening. The question of whether machines can govern better than people.",
        "style": "digital painting, clean light, speculative future",
        "events": ["post_scarcity_events.3"],
    },
    "neo_luddite_protest": {
        "prompt": "Protesters smashing delivery drones and automation equipment in a public square. Traditional tools held as symbols — hammers, brooms, hand tools. A bonfire of circuit boards. The human rebellion against machines that made humans obsolete.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["post_scarcity_events.4"],
    },
    "art_renaissance_future": {
        "prompt": "A vibrant future art district: people freed from work creating murals, sculptures, music, and immersive art installations. Studios in converted factories, public galleries, streets alive with creative expression. What happens when everyone has time to create.",
        "style": "oil painting, impressionist, vibrant color",
        "events": ["post_scarcity_events.5"],
    },
    "post_scarcity_achieved": {
        "prompt": "A city of the far future where material needs are fully met: clean energy, automated production, lush public spaces, people engaged in art, science, community, and exploration. Not a utopia without problems, but one without want.",
        "style": "oil painting, impressionist, bright natural light",
        "events": ["post_scarcity_events.200"],
    },

    # =========================================================================
    # RELIGIOUS REVIVAL EVENTS
    # =========================================================================
    "megachurch_spectacle": {
        "prompt": "A massive modern megachurch interior: stadium-style seating, LED screens broadcasting the charismatic preacher, a rock-concert worship band on stage. Thousands of congregants, hands raised. Religion as mass entertainment and genuine fervor.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.1", "religious_revival_events.2"],
    },
    "liberation_theology_activists": {
        "prompt": "A priest in simple vestments organizing community support in a poor neighborhood: distributing food, mediating disputes, teaching children. Religious symbols alongside political pamphlets. Faith as social revolution.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.3"],
    },
    "religious_culture_war": {
        "prompt": "A polarized town hall meeting: on one side, conservative citizens in traditional dress standing and gesturing angrily, on the other, progressive activists shouting back. Between them, a bewildered family with children tries to navigate the hostile atmosphere. Wood-paneled community hall, harsh fluorescent lights.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.4", "religious_revival_events.5"],
    },
    "digital_pulpit_streaming": {
        "prompt": "A religious leader preaching via live stream: ring light, webcam, chat scrolling with prayers and emoji. Followers watching on phones and laptops in bedrooms and kitchens. Faith adapting to the digital age.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.6"],
    },
    "religious_political_power": {
        "prompt": "Religious leaders meeting with politicians in a government office. Holy books next to policy documents, clerical vestments next to business suits. The blurred line between spiritual authority and political power.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["religious_revival_events.7"],
    },

    # =========================================================================
    # REPEATABLE EVENTS
    # =========================================================================
    "supply_chain_disruption": {
        "prompt": "A port in chaos: container ships backed up at anchor, empty shelves in a warehouse, frustrated logistics managers studying disrupted shipping routes on a wall map. The fragile web of global supply chains, fraying.",
        "style": "oil painting, contemporary realism, industrial crisis",
        "events": ["repeatable_events.10"],
    },
    "automation_displacement": {
        "prompt": "A factory floor divided: on one side, gleaming new robotic assemblers; on the other, workers in hard hats carrying personal belongings out in cardboard boxes. The human cost of automation displayed without sentiment.",
        "style": "oil painting, social realism, industrial contrast",
        "events": ["repeatable_events.20"],
    },
    "media_moral_panic": {
        "prompt": "A sensationalist news broadcast: anchors presenting hysteria-inducing graphics, alarmed faces in audience cutaways, scrolling headlines of doom. Behind the scenes, producers checking ratings that spike with fear.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["repeatable_events.30"],
    },
    "cyber_attack_infrastructure": {
        "prompt": "A city's infrastructure failing from cyberattack: traffic lights malfunctioning, hospital backup generators kicking in, power grid operators frantically working in a dark control room lit by emergency lighting. Digital warfare hitting physical reality.",
        "style": "oil painting, contemporary realism, emergency light",
        "events": ["repeatable_events.40"],
    },
    "space_debris_collision": {
        "prompt": "A satellite in Earth orbit struck by space debris, fragmenting in a silent, glittering explosion. The debris field expands, threatening other satellites. Below, Earth's surface is oblivious. Kessler syndrome beginning.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["repeatable_events.50"],
    },
    "quantum_materials_lab": {
        "prompt": "A materials science laboratory: researchers examining a small sample suspended in magnetic levitation, quantum interference patterns displayed on screens. The sample glows faintly. A breakthrough in matter itself.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["repeatable_events.60"],
    },
    "ai_ethics_debate": {
        "prompt": "A packed auditorium hosting an AI ethics debate. On stage: a humanoid robot sits alongside human panelists. The audience is divided — some fascinated, some afraid, some holding protest signs. The question of machine consciousness.",
        "style": "oil painting, contemporary realism, conference light",
        "events": ["repeatable_events.70"],
    },
    "gig_economy_protest": {
        "prompt": "Gig economy workers — delivery riders on battered bicycles, ride-share drivers leaning against worn-out cars — gathered in a crowd outside a sleek glass-and-steel tech company headquarters. Their weathered vehicles and tired faces contrast with the pristine corporate campus behind them. Raised fists, frustration.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["repeatable_events.80"],
    },
    "cultural_festival_revival": {
        "prompt": "A vibrant cultural revival festival: traditional dances, music, crafts, and food from an endangered culture being celebrated and taught to younger generations. Elders and youth together. Colorful costumes, lanterns, community.",
        "style": "oil painting, impressionist, warm festival light",
        "events": ["repeatable_events.90"],
    },
    "international_development_project": {
        "prompt": "An international development project underway: engineers from multiple countries collaborating on infrastructure — a bridge, dam, or hospital. Hard hats, blueprints, heavy machinery. Construction as international cooperation.",
        "style": "oil painting, social realism, warm light",
        "events": ["repeatable_events.100"],
    },

    # =========================================================================
    # SECULAR EVENTS
    # =========================================================================
    "religious_scandal_media": {
        "prompt": "A religious institution's scandal breaking in the media: newspapers and screens showing revelations of corruption or abuse. A grand religious building in the background, its moral authority crumbling. Shocked parishioners reading the news.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["secular_events.1"],
    },
    "social_moral_panic": {
        "prompt": "A community meeting erupting over moral issues: conservative citizens waving pamphlets about social decay, others pushing back. A town hall setting with raised voices and pointing fingers. Small-town social conflict over changing times.",
        "style": "oil painting, social realism, warm interior light",
        "events": ["secular_events.2", "secular_events.100"],
    },
    "new_age_spirituality_center": {
        "prompt": "A new age spiritual center: crystals, meditation cushions, yoga mats, incense, eclectic religious symbols from many traditions blended together. Seekers in comfortable clothing exploring personal spirituality. Warm, diffuse lighting.",
        "style": "oil painting, impressionist, warm diffuse light",
        "events": ["secular_events.3"],
    },
    "church_state_separation": {
        "prompt": "A courtroom where a judge rules on church-state separation: religious symbols being removed from a government building visible through windows. Lawyers for both sides, spectators divided. The legal architecture of secularism.",
        "style": "oil painting, academic art, institutional gravitas",
        "events": ["secular_events.4", "secular_events.200"],
    },
    "interfaith_dialogue_table": {
        "prompt": "Religious leaders from different faiths seated around a round table: a rabbi, imam, priest, Buddhist monk, Hindu pandit, and others. Each in their traditional vestments. Sharing tea, finding common ground despite theological differences.",
        "style": "oil painting, academic art, warm interior light",
        "events": ["secular_events.5"],
    },

    # =========================================================================
    # SOCIAL TENSIONS EVENTS
    # =========================================================================
    "terrorist_attack_aftermath": {
        "prompt": "The aftermath of a terrorist attack on a city street: emergency responders working amid rubble, ambulances with lights flashing, a shattered storefront. Shocked bystanders, some helping, some frozen. The moment after the blast.",
        "style": "oil painting, chiaroscuro, somber tones",
        "events": [
            "social_tensions_events.1", "social_tensions_events.2",
            "society_technology_events.11",
        ],
    },
    "corporate_lobbying_legislature": {
        "prompt": "Corporate lobbyists in expensive suits walking the corridors of a legislature, briefcases of campaign contributions in hand. Legislators receiving them in offices. The revolving door between corporate money and public policy.",
        "style": "oil painting, chiaroscuro, institutional power",
        "events": [
            "social_tensions_events.3", "social_tensions_events.9",
            "social_tensions_events.10",
        ],
    },
    "monopoly_corporate_tower": {
        "prompt": "A single massive corporate tower dominating a city skyline, casting shadow over smaller buildings. Its logo visible on everything — stores, vehicles, screens. The visual weight of monopoly power crushing competition.",
        "style": "oil painting, dramatic shadows, corporate power",
        "events": ["social_tensions_events.4"],
    },
    "police_brutality_protest": {
        "prompt": "A tense confrontation between riot police with shields and batons and civilian protesters. Tear gas drifts through the scene. Some protesters kneel peacefully, others flee. The fault line between order and justice.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.5", "social_tensions_events.6"],
    },
    "wartime_atrocity_evidence": {
        "prompt": "A war crimes investigation: forensic experts examining evidence in a ruined village. Photographs pinned to a board, witness testimonies recorded, graves marked with flags. The meticulous documentation of horror for future justice.",
        "style": "oil painting, chiaroscuro, somber tones",
        "events": ["social_tensions_events.7", "social_tensions_events.8"],
    },
    "immigration_wave_crowded": {
        "prompt": "Immigrants arriving at a crowded reception center: families with suitcases, officials processing documents, children looking around with wide eyes. A mix of hope, exhaustion, and the bureaucracy of displacement.",
        "style": "oil painting, social realism, empathetic light",
        "events": ["social_tensions_events.11", "social_tensions_events.12"],
    },
    "religious_extremism_clash": {
        "prompt": "A clash between religious fundamentalists and secular counter-protesters. Competing signs and slogans, police separating the groups. A city divided along fault lines of faith, identity, and modernity.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.13", "social_tensions_events.14"],
    },
    "globalization_protest_march": {
        "prompt": "An anti-globalization protest outside an international economic summit. Diverse protesters — unions, environmentalists, anarchists — march behind a banner. Riot police guard the conference venue. Broken windows and tear gas in the air.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["social_tensions_events.15", "social_tensions_events.16"],
    },

    # =========================================================================
    # SOCIETY TECHNOLOGY EVENTS
    # =========================================================================
    "women_workforce_revolution": {
        "prompt": "Women entering the industrial workforce for the first time: rolling up sleeves in a factory, replacing men gone to war. Determination on their faces, propaganda posters encouraging their work visible on the walls. A revolution born of necessity.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.1", "society_technology_events.2"],
    },
    "contraception_revolution": {
        "prompt": "A 1960s doctor's office: a female patient receiving a prescription while a medical pamphlet about family planning sits on the desk. Outside, society is visibly changing — women in professional attire walking confidently. Medical revolution enabling social revolution.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.3"],
    },
    "social_revolution_sixties": {
        "prompt": "A collage of 1960s social revolution: love-ins, rock concerts, protests, miniskirts, long hair, freedom riders. The explosion of personal liberation and cultural upheaval. Tie-dye meets tear gas.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.4"],
    },
    "divorce_reform_court": {
        "prompt": "A family court proceeding: a couple sitting separately with their lawyers, a judge reviewing papers. Through the courtroom window, the changing world. The legal architecture of personal freedom meeting personal pain.",
        "style": "oil painting, social realism, warm light",
        "events": ["society_technology_events.5"],
    },
    "gaming_industry_arcade": {
        "prompt": "A 1980s video game arcade alive with neon: rows of cabinet machines, teenagers with quarters, the glow of CRT screens. Pac-Man, Space Invaders, the birth of a billion-dollar industry in a darkened room full of bleeps and bloops.",
        "style": "oil painting, neon glow, pop culture",
        "events": ["society_technology_events.6"],
    },
    "factory_outsourced_closed": {
        "prompt": "A shuttered factory in a small town: padlocked gates, weeded parking lot, a faded company sign. Workers standing outside, lunch pails in hand, staring at the notice. A community's livelihood shipped overseas.",
        "style": "oil painting, social realism, desolate light",
        "events": ["society_technology_events.9"],
    },
    "anti_globalization_riot": {
        "prompt": "Anti-globalization riots during an international summit: masked protesters hurling objects, police in full riot gear, burning barricades, shattered windows of multinational banks. Raw anger at a system perceived as unjust.",
        "style": "oil painting, social realism, dramatic firelight",
        "events": ["society_technology_events.10"],
    },
    "misinformation_spreading": {
        "prompt": "A visualization of misinformation spreading: a person's phone screen showing a fabricated news article going viral, shares multiplying exponentially on a social media feed. Real and fake stories indistinguishable. Truth drowning in noise.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["society_technology_events.13"],
    },
    "election_interference_cyber": {
        "prompt": "A covert foreign election interference operation: hackers in a state-sponsored facility targeting another nation's election systems. Multiple screens showing voter databases, social media bots, and phishing campaigns. Digital subversion of democracy.",
        "style": "oil painting, contemporary realism, dark screen light",
        "events": ["society_technology_events.14"],
    },
    "student_protest_campus": {
        "prompt": "A university campus protest: students occupying a building, banners hanging from windows, teach-ins on the lawn. Faculty divided — some joining, some condemning. The perennial engine of youthful idealism challenging institutional complacency.",
        "style": "oil painting, social realism, campus daylight",
        "events": ["society_technology_events.15"],
    },
    "neural_interface_consumer": {
        "prompt": "A person reclining in a sleek medical chair in a clean, minimalist clinic. A technician in white applies a small neural implant device behind the patient's ear. The clinic is bright, sterile, with smooth white surfaces and soft blue accent lighting. Technology merging with the human brain.",
        "style": "digital painting, clean light, near-future",
        "events": ["society_technology_events.16", "society_technology_events.20"],
    },
    "augmented_athlete_arena": {
        "prompt": "An augmented athlete with visible cybernetic leg enhancements sprinting around a futuristic sports arena track, leaving other runners far behind. The packed crowd in the stadium rises to their feet. Some spectators cheer wildly, others sit with arms crossed in disapproval.",
        "style": "digital painting, cinematic light, near-future",
        "events": ["society_technology_events.17"],
    },
    "space_habitat_future": {
        "prompt": "A rotating space habitat interior: curved landscape of farmland, buildings, and parks wrapping up and over the viewer's head. Sunlight streams through mirrors. Humanity living permanently among the stars, Earth visible through a viewport.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["society_technology_events.18", "society_technology_events.19"],
    },
    "telepathic_diplomacy_link": {
        "prompt": "Two diplomats seated across a polished table in a futuristic conference room, eyes closed in intense concentration. Glowing neural interface devices on their temples pulse with soft blue light. Faint luminous tendrils of energy arc between them through the air. Aides watch in awe from the edges of the room.",
        "style": "digital painting, ethereal light, speculative future",
        "events": ["society_technology_events.21"],
    },
    "nuclear_reactor_leak": {
        "prompt": "A nuclear power plant incident: warning lights flashing, coolant steam venting from a reactor building, workers in radiation suits rushing to containment. Nearby residents watch anxiously. The terror of invisible danger.",
        "style": "oil painting, dramatic light, industrial crisis",
        "events": ["society_technology_events.22", "society_technology_events.23"],
    },
    "anti_nuclear_energy_protest": {
        "prompt": "An anti-nuclear energy protest camp outside a power plant: tents, banners, families with children demanding plant closure. The cooling towers loom behind them. A grassroots campaign against institutional power and perceived invisible threat.",
        "style": "oil painting, social realism, dramatic light",
        "events": ["society_technology_events.24"],
    },
    "deepfake_crisis_screen": {
        "prompt": "A crisis room where officials watch a deepfake video of a world leader making inflammatory statements. Analysts try to prove it's fake while the video goes viral on screens behind them. Reality itself becoming unreliable.",
        "style": "oil painting, contemporary realism, cool screen light",
        "events": ["society_technology_events.25"],
    },
    "ai_alignment_failure": {
        "prompt": "A server room where an AI system has gone off-script: screens displaying unexpected outputs, engineers frantically trying to intervene, warning indicators everywhere. The moment when artificial intelligence stops following its intended purpose.",
        "style": "oil painting, contemporary realism, red warning light",
        "events": ["society_technology_events.26"],
    },
    "algorithmic_governance_office": {
        "prompt": "A government office where algorithms make routine decisions: screens display approval/denial verdicts for benefits, permits, and licenses. A few human operators monitor but rarely override. Citizens receive automated notifications.",
        "style": "oil painting, contemporary realism, sterile light",
        "events": ["society_technology_events.27"],
    },
    "genetic_designer_baby_clinic": {
        "prompt": "A fertility clinic of the future: prospective parents reviewing their embryo's genetic profile on a screen, selecting traits from a menu. A clinician explains options. The commodification of human genetics in a sterile, branded environment.",
        "style": "oil painting, cool clinical light, near-future",
        "events": ["society_technology_events.28"],
    },
    "synthetic_food_laboratory": {
        "prompt": "A synthetic food laboratory: bioreactors growing cultured meat, 3D food printers producing meals, taste testers comparing lab-grown products to traditional food. Clean and efficient, but somehow unsettling. The future of eating.",
        "style": "oil painting, cool clinical light, scientific",
        "events": ["society_technology_events.29"],
    },
    "autonomous_vehicle_street": {
        "prompt": "A city street navigated entirely by autonomous vehicles: sensor-equipped cars, delivery drones overhead, pedestrians walking confidently through traffic that always stops. A single confused driver in a manual car, an anachronism.",
        "style": "oil painting, contemporary realism, urban daylight",
        "events": ["society_technology_events.30", "society_technology_events.31"],
    },

    # =========================================================================
    # SPACE RACE COLONY EVENTS — Mars (1-5)
    # =========================================================================
    "colony_valles_marineris": {
        "prompt": "A colony nestled in the vast Valles Marineris canyon system on Mars. Pressurized habitat domes cling to the rust-red canyon walls, connected by enclosed walkways. The canyon stretches into hazy distance, 7km deep. Rovers traverse the canyon floor.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.1"],
    },
    "colony_olympus_mons": {
        "prompt": "A research station perched on the slopes of Olympus Mons, the tallest volcano in the solar system. The caldera is visible above, shield slopes extend beyond the curved Martian horizon.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.2"],
    },
    "colony_hellas_planitia": {
        "prompt": "A settlement in the Hellas Planitia impact basin, the lowest point on Mars. Thick atmosphere at the basin floor creates warmer conditions. Greenhouse domes and outdoor-suited workers in ruddy light. Ancient impact walls ring the distant horizon.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.3"],
    },
    "colony_utopia_planitia": {
        "prompt": "A sprawling industrial colony on the flat plains of Utopia Planitia, Mars. Manufacturing domes, landing pads with supply rockets, solar panel fields stretching to the horizon. The workhorse colony — functional, not beautiful. Dust devils in the distance.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_colony_events.4"],
    },
    "colony_arcadia_planitia": {
        "prompt": "An agricultural colony on Arcadia Planitia exploiting subsurface ice. Water extraction towers dot the landscape, feeding massive greenhouse complexes glowing green from within. The breadbasket of Mars, built on frozen water.",
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
        "prompt": "A mining colony carved into the giant asteroid 4 Vesta, nestled in the massive Rheasilvia impact basin. Mining equipment extracts iron and magnesium from exposed mantle material. Sharp cliffs and rubble fields under a black sky.",
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
        "prompt": "A fuel depot colony on 10 Hygiea, an icy body in the outer asteroid belt. Water ice is mined and cracked into hydrogen fuel. Tanker ships orbit above. A remote, cold outpost servicing the deep-space trade routes.",
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
        "prompt": "A binary colony spanning Pluto and Charon, connected by a space elevator between the tidally locked worlds. Pluto's heart-shaped nitrogen glacier glows faintly. Charon's red polar cap is visible. The sun is just a very bright star.",
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
        "prompt": "A small, impossibly dense planet of exposed iron-nickel core — the naked heart of a world that lost its mantle in a primordial collision. The surface is metallic, gleaming dull silver under an alien sun.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.604"],
    },
    "probe_asteroid_belts": {
        "prompt": "A vast, intricate asteroid belt viewed from within — thousands of tumbling rocks of all sizes, caught in gravitational resonance patterns. No planets, just an endless field of debris orbiting a distant star.",
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
        "prompt": "A massive tectonically hyperactive super-Earth seen from orbit: continent-sized lava flows, volcanic mountains the height of Olympus Mons erupting simultaneously, tectonic plates visibly shifting. A world of fire and geological fury three times Earth's mass.",
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
        "prompt": "Aerial probe imagery of a humid, overcast exoplanet where all visible land is covered by a single interconnected mat of non-photosynthetic alien life — one planetary-scale organism, a mycelial network that wraps the entire globe.",
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
        "prompt": "Spectroscopic data overlays showing artificial gases — chlorofluorocarbons and sulfur hexafluoride — in an alien planet's atmosphere. Gases that do not occur in nature. Industrial civilization confirmed. The smoking gun of alien industry, detected across light-years of space.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["space_race_events.626"],
    },
    "probe_nuclear_ruins": {
        "prompt": "A habitable world — temperate, oceanic, oxygen-rich — but with radiation levels orders of magnitude above natural. A civilization that destroyed itself with nuclear weapons, the scars still glowing in the probe's radiation sensors. Fission products everywhere.",
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
        "prompt": "Astronaut candidates in training: centrifuge runs, underwater EVA simulations, classroom sessions on orbital mechanics. Diverse candidates being tested to their physical and mental limits. Only the best will fly.",
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
        "prompt": "A state-sponsored cyber espionage operation: hackers in a government facility, multiple screens showing infiltrated foreign networks, stolen data flowing in. National flags visible. Espionage without spies, theft without touching.",
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
        "prompt": "The UN in crisis: a Security Council chamber with several seats conspicuously empty, remaining delegates arguing, the Secretary-General looking grave. The international order fraying when nations refuse to participate.",
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
        "prompt": "The completed space elevator in full operation: passenger and cargo pods ascending and descending the impossibly long tether. At the top, a orbital station gleams. At the bottom, a new spaceport city has grown around the base.",
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
        "prompt": "A diplomatic confrontation over the space elevator: national delegations arguing around a model of the elevator, each claiming regulatory authority. Military vessels orbit nearby. Who owns the road to space?",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.7"],
    },

    # =========================================================================
    # WONDER EVENTS — Orbital Solar Collector (10-15)
    # =========================================================================
    "orbital_solar_first_light": {
        "prompt": "An orbital solar collector focusing its first beam of concentrated sunlight toward a ground receiving station. The beam is visible as a pillar of light from space to ground. The moment unlimited clean energy becomes real.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.10"],
    },
    "solar_beam_misalignment": {
        "prompt": "An orbital solar beam misaligned: the concentrated sunlight striking off-target, scorching a strip of landscape. Fire and smoke where there should be a receiving station. Engineers frantically adjusting orbital mirrors. A weapon disguised as infrastructure.",
        "style": "digital painting, cinematic light, hard sci-fi",
        "events": ["wonder_events.11"],
    },
    "solar_power_surplus": {
        "prompt": "A world transformed by unlimited orbital solar power: electric grids at zero cost, factories running on free energy, desalination plants providing unlimited fresh water. The greatest energy revolution since fire, beamed from space.",
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
        "prompt": "The view from an orbital battlestation looking down at Earth: high-resolution targeting displays overlaying the surface, individual vehicles and buildings resolvable, military operators monitoring potential targets. God's-eye view weaponized.",
        "style": "digital painting, cinematic light, military sci-fi",
        "events": ["wonder_events.21"],
    },
    "orbital_peace_deterrence": {
        "prompt": "World leaders in a summit room with a live feed from the orbital battlestation on a large screen. The station's weapons aimed at nothing in particular — the implicit threat sufficient. Peace through the omnipresence of overwhelming force.",
        "style": "oil painting, academic art, diplomatic interior",
        "events": ["wonder_events.22", "wonder_events.25"],
    },
    "orbital_misfire_impact": {
        "prompt": "A kinetic weapon fired from orbit striking the ground: a devastating impact crater where a city block stood. Smoke and debris. An orbital weapons system that 'malfunctioned' — or was it deliberate?",
        "style": "digital painting, dramatic light, destructive impact",
        "events": ["wonder_events.23"],
    },
    "orbital_arms_race": {
        "prompt": "Multiple nations launching orbital weapons platforms: a visualization of Earth orbit filling with competing military stations, each nation racing to dominate the ultimate high ground. The Cold War's worst nightmare realized in orbit.",
        "style": "digital painting, cinematic light, military sci-fi",
        "events": ["wonder_events.24"],
    },
    "asteroid_deflection_heroic": {
        "prompt": "The orbital battlestation repurposed for asteroid deflection: weapons systems targeting an incoming asteroid, the beam or projectile striking the threat. The weapon of war becoming humanity's shield against cosmic impact. Redemption through service.",
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
        "prompt": "Scientists and military officials in a secure facility examining the first antimatter weapon prototype: a small, unassuming device that could destroy a city. The scale of destructive power miniaturized to the absurd. Nuclear weapons made obsolete.",
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
        "prompt": "Soldiers exchanging fire across a disputed border: foxholes, barbed wire, tracers in the dawn light. A contested no-man's-land between opposing trenches. The spark that could ignite a world war, or be forgotten by tomorrow.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.2"],
    },
    "diplomatic_crisis_ultimatum": {
        "prompt": "A diplomatic crisis: an ambassador delivering an ultimatum document to a foreign minister. Both men's hands tremble. Behind them, military aides flip through contingency plans. The last moment before the point of no return.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.3"],
    },
    "world_war_declaration": {
        "prompt": "A head of state addressing the nation from behind a desk, declaring war. Radio/television microphones cluster on the desk. The flag behind them. Citizens gathered around radio sets in homes and public squares. The moment everything changes.",
        "style": "oil painting, dramatic shadows, military painting",
        "events": ["world_war_events.5"],
    },
    "home_front_factory": {
        "prompt": "A wartime home front factory: assembly lines running at full capacity producing munitions, vehicles, and supplies. Posters demanding sacrifice and production. Workers pulling double shifts. Women filling roles vacated by men at the front.",
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
        "prompt": "A war-weary home front: rationing queues, casualty lists posted on bulletin boards, families reading dreaded telegrams. Gold star mothers. The slow grinding down of civilian morale as the war stretches on year after year.",
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
        "prompt": "A war crimes tribunal: former leaders in the dock, prosecutors presenting evidence of atrocities, judges in robes. Translators with headphones. The machinery of international justice processing the architects of horror.",
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
