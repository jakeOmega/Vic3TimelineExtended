#!/usr/bin/env python3
"""
icon_prompts.py - FLUX prompt registry for the mod's UI icons.

The icon counterpart of event_image_prompts.py. `CATEGORIES` holds what makes
each category look like its vanilla folder (size, layout, style template);
`ICONS` holds, per category, one subject phrase per entity and its review
state. `generate_icons.py` renders, composes, writes and wires from here.

Each ICONS entry is {"subject": <phrase>, "seed": <state>}:
    seed None     not reviewed yet; renders candidates, writes nothing
    seed <int>    this candidate is the icon: its DDS is written and the
                  entity's icon line points at it
    seed "keep"   the borrowed vanilla icon fits; never rendered or rewired
or {"use": "gfx/interface/icons/.../x.dds"}: a different existing icon fits
better than the borrowed one (vanilla's crossed-out guarantee for withdrawing
one); never rendered, and `wire` points the entity at it.
A subject describes one physical object, with its material and colour. FLUX
fills in whatever a subject leaves open, and review kept catching the same
defaults (September 2026, ~350 icons):
- Unnamed colours drift to real-world defaults: "paper banknotes" drew US
  dollars. No screens with text, no currency, flags or faces.
- Words that imply writing get written: "voting card" drew VOTE, "holy book"
  HOLY, "payment-plan tag" Payment, a share certificate its title. Name the
  object, not its purpose ("a small green wooden block").
- Vehicles and aircraft come with insignia: a red star, a US Army star,
  roundels, red crosses on a bomber. Choose an unmarked candidate; saying "no
  markings" does not stop them.
- Avoid a large white or cream surface: renders are on a white background and
  the cutout cannot tell them apart (a white tray and a cream certificate lost
  patches, which showed as dark holes on the game's UI).
- FLUX will not break, fold or furl on request ("a rifle snapped in two", "a
  furled umbrella"); change the image (a helmet full of poppies).
- Anything hung from a crossbeam reads as a gallows (a pole with a hanging
  bulb, a marionette on its frame).
- In the plinth layout, "on a stand" or "on a base" adds a second pedestal.
- Printed and branded objects bring their print: a circuit board its
  silkscreen, a controller PlayStation symbols, a sci-fi rifle a maker's
  logo, a sun a play-button triangle. Etched lines or plain buttons work.
- A "blank screen" renders pale, and the cutout empties it, leaving the
  device hollow. Give the screen a dark or coloured glow (a heartbeat line).
- Glows and halos around an object turn into grey blobs after the cutout.
- An unqualified object gets its usual context: a helmet comes with a
  soldier wearing it (write "an empty helmet"), and a "globe" is a plain
  green ball (name the Earth's continents and oceans).
When both candidates miss, change the subject. When the idea is right and the
renders are weak, `generate_icons.py --seeds 4` adds two more candidates and
keeps the first two.

Design, inventory and decisions: docs/superpowers/specs/2026-09-26-icon-pipeline-design.md.

Usage:
    python3 icon_prompts.py --validate   # registry vs the mod's files; exit 1 on errors
"""

from __future__ import annotations

KEEP = "keep"

# Style = what makes a category look like its vanilla folder. Subject = the one
# per-entity phrase a human (or an LLM draft from loc) has to write.
# Painterly, not photographic: FLUX.1-schnell drifts to product photography unless
# the prompt names the medium ("hand-painted game icon", brush strokes). Small
# categories (100 px) also need one compact object, or it downsizes to specks.
PAINTED = ("stylized hand-painted video game icon, painterly digital art with visible "
           "brush strokes, soft 3D shading, warm muted palette, blank unmarked surfaces, "
           "three-quarter view from slightly above, centered, isolated on a plain white background")
SILHOUETTE = ("a solid black silhouette of {subject}, simple flat pictogram stencil, "
              "bold clean shapes, no outline, on a plain white background")

# folder/size/mode/fill/style drive rendering and composing. A category that
# `generate_icons.py` produces also names where its entities live
# (`entity_dir`) and the field holding the icon path (`field`); its icons are
# written to gfx/interface/icons/<folder>/<key>.dds.
CATEGORIES = {
    "technology": dict(
        folder="invention_icons", size=256, mode="cutout", fill=0.92,
        entity_dir="common/technology/technologies", field="texture",
        style="{subject}, one chunky readable object, " + PAINTED),
    "treaty_article": dict(
        folder="diplomatic_treaties_articles_icons", size=100, mode="cutout", fill=0.98,
        entity_dir="common/treaty_articles", field="icon",
        style=("{subject}, one compact bold object group filling the frame, simple chunky "
               "silhouette, one strong accent color, " + PAINTED)),
    # The figure stands on the slab lifted from vanilla (icon_render.plinth_template).
    # Asking FLUX for the pedestal drew one detached from its figure.
    # The lens toolbar ignores `texture`: the engine loads
    # lens_toolbar_icons/<key>.dds for every action without show_in_lens = no,
    # and vanilla's is a byte-identical copy of the action icon. `write` keeps
    # that copy (see generate_icons.sync_lens_copies).
    "diplomatic_action": dict(
        folder="diplomatic_action_icons", size=100, mode="plinth", fill=0.8,
        entity_dir="common/diplomatic_actions", field="texture", lens_folder="lens_toolbar_icons",
        style=("{subject}, a compact miniature sculpture, simple chunky silhouette, " + PAINTED)),
    "building": dict(
        folder="building_icons", size=256, mode="framed",
        style=("aerial three-quarter view of {subject}, detailed painted illustration "
               "of a miniature diorama, warm golden afternoon light, muted earthy "
               "palette, surrounding landscape, the building fills the center of the image")),
    "ideology": dict(
        folder="ideology_icons", size=220, mode="emboss_medallion", fill=0.60,
        color=(255, 228, 175), centre_lift=1.25, style=SILHOUETTE),
    "mobilization_option": dict(
        folder="mobilization_options", size=208, mode="emboss", fill=0.86,
        color=(240, 140, 90), style=SILHOUETTE),
    "decree": dict(
        folder="decree", size=158, mode="medallion", fill=0.78, centre_lift=2.1,
        grade_folder="invention_icons",
        style="{subject}, one chunky compact object, bright warm lighting, " + PAINTED),
}


def prompt_for(cat: str, subject: str) -> str:
    return CATEGORIES[cat]["style"].format(subject=subject) + ", no text, no writing, no letters"


def icon_path(cat: str, key: str) -> str:
    """The mod path an accepted icon is written to and wired as."""
    return f"gfx/interface/icons/{CATEGORIES[cat]['folder']}/{key}.dds"


ICONS: dict[str, dict[str, dict]] = {
    "technology": {
        # Mod-added techs that borrowed a vanilla icon (135 of them the
        # mass_communication newspapers), by era then category.
        # era 6
        "bombing_aircraft": {"subject": "a large twin-engine propeller bomber with a glazed glass nose, painted plain olive drab with no markings", "seed": 0},
        "combined_arms": {"subject": "a small olive-green tank, a field gun and a propeller fighter plane grouped together as models on one round base", "seed": 1},
        "cryptography": {"subject": "a wooden-cased rotor cipher machine with a keyboard and three brass rotor wheels", "seed": 1},
        "motorized_artillery": {"subject": "a field howitzer mounted on the back of an olive-green military truck", "seed": 0},
        "naval_convoy_defense": {"subject": "a grey destroyer warship escorting a rust-red cargo freighter, as a tabletop model on a patch of sea", "seed": 1},
        "naval_fire_control_systems": {"subject": "a grey naval rangefinder director with a long horizontal optical arm and brass eyepieces", "seed": 0},
        "nuclear_weapons": {"subject": "a squat dark grey aerial atomic bomb with a boxy tail fin", "seed": 1},
        "radar": {"subject": "a curved steel-mesh radar dish antenna on a lattice tower base", "seed": 1},
        "rocketry": {"subject": "a slender plain grey liquid-fuel rocket with four fins, standing upright on a small launch stand", "seed": 0},
        "semiautomatic_rifle": {"subject": "a semi-automatic infantry rifle with a walnut stock, lying diagonally", "seed": 1},
        "sonar": {"subject": "a grey steel sonar console with a round glowing green scope showing a sweep line and one bright blip, headphones hanging from its side", "seed": 1},
        "aluminum_mass_production": {"subject": "a neat stack of shiny silver aluminium ingots", "seed": 0},
        "bergius_process": {"subject": "a tall riveted steel high-pressure reactor vessel with pipes, beside a heap of black coal", "seed": 1},
        "fluorescent_lamps": {"subject": "a long glowing white fluorescent tube lamp in a metal ceiling fixture", "seed": 0},
        "isoprene": {"subject": "a glass laboratory flask of clear liquid beside a coil of black synthetic rubber hose", "seed": 0},
        "modern_automotive_technology": {"subject": "a rounded 1930s sedan car in dark green with chrome bumpers", "seed": 1},
        "modern_chemical_processes": {"subject": "a compact model of gleaming steel chemical reaction columns connected by pipes", "seed": 1},
        "modern_materials": {"subject": "a spool of shiny white nylon thread beside a translucent green fibreglass panel", "seed": 0},
        "modern_skyscrapers": {"subject": "a model of a slender steel-framed skyscraper with rows of windows and a mast on top", "seed": 1},
        "modern_tools": {"subject": "a small orange forklift truck lifting a wooden pallet", "seed": 1},
        "personal_appliances": {"subject": "a rounded white enamel refrigerator with a chrome handle", "seed": 0},
        "stainless_steel_mass_production": {"subject": "a gleaming stainless steel cooking pot on a stack of polished steel plates", "seed": 1},
        "television": {"subject": "a wooden-cabinet 1940s television set with a small rounded screen showing only a soft grey glow", "seed": 1},
        "advanced_agricultural_statistics": {"subject": "a sheaf of golden wheat standing upright beside a clipboard with a hand-drawn rising bar chart", "seed": 0},
        "animation": {"subject": "a stack of transparent animation cels, each showing a red ball at a different height, with a pencil beside them", "seed": 1},
        "art_deco_architecture": {"subject": "an ornate cream stone Art Deco building facade with gold sunburst motifs and stepped setbacks", "seed": 0},
        "commercial_aviation": {"subject": "a silver twin-engine propeller airliner with a rounded fuselage and a row of windows", "seed": 0},
        "computing_machines": {"subject": "a grey early computer cabinet with rows of glowing vacuum tubes and toggle switches", "seed": 0},
        "consumer_credit": {"subject": "a shiny new wooden radio set with a small blank paper tag tied to its handle with string", "seed": 1},
        "intergovernmental_organizations": {"subject": "a round wooden conference table with empty chairs placed evenly around it", "seed": 1},
        "keynesian_economics": {"subject": "a workman's shovel leaning on a small stack of plain cream-coloured government bonds tied with red ribbon", "seed": 0},
        "marketing_research": {"subject": "a clipboard with a tick-box questionnaire and a pencil, beside a small wicker shopping basket", "seed": 0},
        "mass_media": {"subject": "a large chrome studio microphone on a stand beside a wooden radio set", "seed": 1},
        "modern_management_techniques": {"subject": "a chrome stopwatch lying on a clipboard with a flowchart", "seed": 0},
        "modern_vaccines": {"subject": "a glass syringe beside a small brown glass vaccine vial with a grey rubber stopper", "seed": 1},
        "public_works_programs": {"subject": "a miniature concrete arch dam with water pouring through its spillway", "seed": 1},
        "rural_electrification": {"subject": "a single tall wooden utility pole with glass insulators on its crossarm, its wire running to a small farmhouse with a lit window", "seed": 0},
        # era 7
        "ICBMs": {"subject": "a tall light grey intercontinental ballistic missile with a black nose cone, standing upright in an open concrete silo", "seed": 0},
        "advanced_military_aircraft": {"subject": "a silver swept-wing jet fighter plane", "seed": 1},
        "advanced_submarine_technology": {"subject": "a sleek black nuclear submarine, as a tabletop model", "seed": 1},
        "anti_sub_warfare": {"subject": "a grey naval depth-charge barrel beside a slim homing torpedo", "seed": 0},
        "guided_missiles": {"subject": "a slender light grey guided missile with red-tipped fins on a launch rail", "seed": 0},
        "inertial_navigation_systems": {"subject": "a brass gyroscope: a spinning steel disc inside three nested brass rings set at right angles to each other", "seed": 0},
        "jet_engine_technology": {"subject": "a polished metal jet engine with its fan blades visible in the intake", "seed": 1},
        "nuclear_energy": {"subject": "a bundle of uranium fuel rods in a steel frame, glowing faint blue", "seed": 1},
        "recon_satellites": {"subject": "a boxy gold-foil-wrapped reconnaissance satellite with a large camera lens and solar panel wings", "seed": 1},
        "satellite_communications": {"subject": "a round communications satellite with a large silver dish antenna and blue solar panel wings", "seed": 1},
        "space_exploration": {"subject": "a small silver space capsule with round portholes and a dark heat shield", "seed": 3},
        "tactical_nuclear_weapons": {"subject": "a compact olive-green nuclear artillery shell with a yellow band around it", "seed": 0},
        "green_revolution": {"subject": "a bundle of short-stalked golden wheat heavy with grain, tied with twine", "seed": 0},
        "integrated_circuits": {"subject": "a small black integrated circuit chip with two rows of silver pins", "seed": 1},
        "laser_technology": {"subject": "a metal laser tube emitting a thin bright red beam", "seed": 0},
        "mainframe_computers": {"subject": "a tall grey mainframe computer cabinet with two spinning tape reels", "seed": 1},
        "photocopiers": {"subject": "a boxy beige office photocopier with a blank sheet of paper coming out of its tray", "seed": 1},
        "plastic_mass_production": {"subject": "a bright red plastic bucket full of colourful plastic bottles and containers", "seed": 0},
        "prefabricated_construction": {"subject": "a small yellow crane lowering a grey concrete wall panel with a window opening onto a half-built boxy building", "seed": 2},
        "transistors": {"subject": "a single large vintage transistor with a black casing and three metal legs", "seed": 0},
        "anti_war_movement": {"subject": "a wooden protest placard painted with a white dove", "seed": 1},
        "antibiotic_mass_production": {"subject": "a glass petri dish of blue-green penicillin mould beside a brown medicine bottle", "seed": 0},
        "civil_rights_movement": {"subject": "two hands, one dark brown and one pale, gripping each other in a firm handshake", "seed": 2},
        "contraceptive_pill": {"subject": "a round pastel-blue pill dispenser holding a ring of small white pills", "seed": 1},
        "modern_urban_planning": {"subject": "an architect's scale model of a planned city block with tidy streets, green parks and pale stone buildings", "seed": 1},
        "pollution_control": {"subject": "a squat brick factory chimney capped with a big round green air filter, a sprig of green leaves at its base", "seed": 0},
        "pop_culture": {"subject": "a colourful jukebox with glowing coloured tubes", "seed": 1},
        "second_wave_feminism": {"subject": "a bold purple Venus symbol, a ring with a short cross beneath it, a small raised fist inside the ring", "seed": 3},
        "television_broadcasting": {"subject": "a heavy black studio television camera on a wheeled pedestal", "seed": 0},
        # era 8
        "advanced_materials_armor": {"subject": "a thick slab of layered composite armour plate with blocky reactive armour tiles bolted on", "seed": 1},
        "infrared_night_vision": {"subject": "a pair of olive-green military night-vision goggles with glowing green lenses", "seed": 1},
        "precision_guided_munitions": {"subject": "a dark grey laser-guided bomb with a pointed black seeker head and small steering fins at both ends", "seed": 0},
        "predictive_logistics": {"subject": "a stack of olive-green military supply crates on a pallet with a small glowing blue data tablet on top", "seed": 1},
        "stealth_technology": {"subject": "an angular black stealth aircraft built of flat faceted panels", "seed": 1},
        "supersonic_aircraft": {"subject": "a silver delta-wing supersonic jet with a needle nose", "seed": 1},
        "advanced_assembly_lines": {"subject": "a short conveyor belt carrying identical small metal parts under a hydraulic press", "seed": 1},
        "barcodes_and_scanners": {"subject": "a black handheld barcode scanner casting a red laser line across a cardboard box", "seed": 1},
        "cellular_networks": {"subject": "the top of a grey mobile phone mast, three tall grey rectangular antenna panels clamped around a steel pole with thick black cables", "seed": 1},
        "computer_aided_design": {"subject": "a glowing blue wireframe model of a machine gear floating above a drafting table", "seed": 0},
        "computer_networks": {"subject": "a beige network hub box with many blue cables plugged into it", "seed": 0},
        "fiber_optics": {"subject": "a thick fan of glass fibre-optic strands spraying out of a black cable end like a brush, every tip glowing bright blue", "seed": 0},
        "gene_splicing": {"subject": "a glowing DNA double helix being cut by a small pair of steel scissors", "seed": 0},
        "microprocessor": {"subject": "a square computer processor chip with gold contact pins, seen from above at an angle", "seed": 1},
        "personal_computers": {"subject": "a beige 1980s personal computer with a boxy monitor and keyboard, its screen dark and blank", "seed": 1},
        "robotics": {"subject": "an orange six-axis industrial robot arm on a round grey floor base, a welding torch fixed to the end of the arm", "seed": 0},
        "containerization": {"subject": "a stack of three steel shipping containers in red, blue and rust orange", "seed": 1},
        "environmental_movement": {"subject": "a small blue-and-green Earth globe showing its continents and oceans, with a young green sapling sprouting from its top", "seed": 0},
        "modern_pharmaceuticals": {"subject": "a brown glass pharmacy bottle spilling colourful capsules and tablets", "seed": 1},
        "sexual_revolution": {"subject": "an open round pastel pink contraceptive pill compact holding a ring of small pale yellow tablets", "seed": 0},
        "video_games": {"subject": "a chunky grey game controller with a directional pad and round red buttons", "seed": 1},
        # era 9
        "advanced_body_armor": {"subject": "an olive-green modern ballistic vest with ceramic plate pouches", "seed": 1},
        "automated_surveillance": {"subject": "a grey pan-and-tilt security camera mounted on a metal pole", "seed": 1},
        "military_grade_cybersecurity": {"subject": "a heavy olive-green armoured steel padlock with a glowing green keyhole and thin green circuit lines etched into its body", "seed": 3},
        "missile_defense_systems": {"subject": "a truck-mounted anti-missile launcher with four upright box launch tubes", "seed": 3},
        "network_centric_warfare": {"subject": "a glowing blue holographic map table with small military unit markers linked by lines of light", "seed": 1},
        "rapid_deployment_forces": {"subject": "an open military parachute canopy carrying a small olive-green supply crate", "seed": 1},
        "unmanned_aerial_vehicles": {"subject": "a slender grey military drone with long straight wings and a bulbous camera nose", "seed": 1},
        "biotechnology": {"subject": "a glass test tube holding a glowing green seedling with its roots in liquid", "seed": 1},
        "clean_energy_technologies": {"subject": "a pale grey three-bladed wind turbine standing beside a tilted blue solar panel", "seed": 1},
        "cloud_computing": {"subject": "a soft blue-grey cloud floating above a black rack of server units with blinking lights", "seed": 1},
        "digital_telecommunications": {"subject": "a grey metal telephone switching cabinet with rows of small green indicator lights and thick bundles of blue cables plugged into its front", "seed": 1},
        "e-commerce": {"subject": "a cardboard delivery parcel resting on a closed silver laptop", "seed": 0},
        "early_nanotechnology": {"subject": "a tiny glowing hexagonal carbon nanotube held in steel tweezers", "seed": 0},
        "hydraulic_fracturing": {"subject": "a cutaway block of layered brown and grey rock with a steel well pipe running down its middle, bright blue fluid spreading sideways into cracks in one rock layer", "seed": 0},
        "supply_chain_management": {"subject": "a length of heavy steel chain with small cardboard parcels hanging from its links", "seed": 1},
        "wireless_internet": {"subject": "a black wireless router with two antennas radiating glowing curved signal arcs", "seed": 1},
        "world_wide_web": {"subject": "a spider web of glowing blue light strands with a small globe at its centre", "seed": 1},
        "LGBTQ_rights_movement": {"subject": "a rainbow-striped silk ribbon looped into an awareness ribbon", "seed": 1},
        "advanced_workflow_optimization": {"subject": "interlocking brass gears with a chrome stopwatch set into the largest gear", "seed": 1},
        "cybersecurity": {"subject": "a blue shield emblem with a keyhole, made of glowing circuit-board lines", "seed": 1},
        "digital_education": {"subject": "a black graduation mortarboard cap resting on a dark grey tablet computer with a glowing blue screen", "seed": 1},
        "digital_entertainment": {"subject": "a pair of chunky black over-ear headphones beside a sleek black game controller with plain round red buttons", "seed": 0},
        "globalization": {"subject": "a small globe ringed by a cargo ship and a jet airliner circling it", "seed": 0},
        "knowledge_economy": {"subject": "a stack of books with a glowing light bulb on top", "seed": 1},
        "social_justice_movements": {"subject": "a brass scale of justice with two perfectly level pans", "seed": 0},
        "social_media": {"subject": "a black smartphone with a glowing blue screen, colourful speech bubbles and heart symbols floating up from it", "seed": 0},
        "terrorism_and_anti_terrorism": {"subject": "an empty matte black tactical helmet with night-vision goggles on its front mount, resting on top of a dark grey ballistic shield lying flat", "seed": 1},
        "virtual_reality": {"subject": "a dark grey virtual reality headset with black padding and a strap", "seed": 1},
        # era 10
        "cyber_warfare": {"subject": "a black computer server rack cracked open with red glowing light pouring out", "seed": 1},
        "directed_energy_defenses": {"subject": "a turret-mounted laser cannon on a grey armoured base, firing a thin bright beam upward", "seed": 0},
        "electronic_warfare": {"subject": "an olive-green military jammer box with antennas sending out jagged zigzag waves", "seed": 2},
        "hypersonic_weapons": {"subject": "a sleek black arrowhead-shaped hypersonic glide vehicle trailing a streak of glowing plasma", "seed": 0},
        "jadc2": {"subject": "a glowing holographic globe surrounded by small models of a ship, a jet, a tank and a satellite linked by lines of light", "seed": 1},
        "reusable_rocketry": {"subject": "a tall slim grey cylindrical rocket booster with a flat top, standing upright on four thin splayed landing legs, a small flame and smoke at its base", "seed": 0},
        "additive_manufacturing": {"subject": "a desktop 3D printer printing an orange plastic gear layer by layer", "seed": 1},
        "advanced_structural_engineering": {"subject": "a short thick steel I-beam welded to a black woven carbon-fibre plate, a bright orange glowing weld seam along the joint with a few sparks", "seed": 3},
        "electric_vehicles": {"subject": "a sleek dark blue electric car plugged into a green charging post by a thick cable", "seed": 1},
        "generative_ai": {"subject": "a silver robotic hand holding a paintbrush over a small canvas of colourful strokes", "seed": 3},
        "internet_of_things": {"subject": "a round grey smart home hub surrounded by a thermostat, a light bulb and a small sensor linked by glowing lines", "seed": 0},
        "machine_learning": {"subject": "a small silver robot sitting and reading an open book", "seed": 0},
        "decline_of_organized_religion": {"subject": "an empty dusty wooden pew with a cobweb and a single unlit candle", "seed": 3},
        "mental_health_awareness": {"subject": "a small potted plant sprouting fresh green leaves, with a green awareness ribbon tied around the pot", "seed": 1},
        "mrna_therapeutics": {"subject": "a small glass vaccine vial with a glowing pink ribbon of RNA curling around it", "seed": 1},
        "telemedicine": {"subject": "a stethoscope draped over a dark grey tablet computer whose dark screen shows one glowing blue heartbeat line", "seed": 1},
        "universal_basic_income": {"subject": "an open hand holding a small brown paper pay envelope with a few plain gold coins spilling out of it", "seed": 0},
        # era 11
        "asteroid_mining": {"subject": "a grey asteroid chunk with a small drilling rig on top and glinting veins of metal ore", "seed": 1},
        "augmented_reality_warfare": {"subject": "a military helmet with a glowing transparent visor display", "seed": 0},
        "bioenhanced_soldiers": {"subject": "a glowing green serum injector beside an olive-green military helmet", "seed": 1},
        "directed_energy_weapons": {"subject": "a futuristic rifle-shaped energy weapon with glowing blue coils", "seed": 2},
        "fusion_power": {"subject": "a doughnut-shaped tokamak fusion reactor with a glowing pink plasma ring inside", "seed": 0},
        "quantum_communications": {"subject": "two glowing deep violet crystal orbs linked by a bright twisting beam of cyan light", "seed": 1},
        "space_militarization": {"subject": "a dark grey armed military satellite with folded solar wings and a small missile rack", "seed": 1},
        "swarm_technology": {"subject": "a tight cluster of small black quadcopter drones flying in formation", "seed": 0},
        "abyssal_plain_mining": {"subject": "a yellow deep-sea mining crawler with a vacuum nozzle, on dark seabed strewn with black nodules", "seed": 1},
        "autonomous_vehicles": {"subject": "a small silver self-driving car with a black sensor dome on its roof", "seed": 1},
        "genetic_engineering": {"subject": "a glowing DNA double helix inside a laboratory glass vial", "seed": 1},
        "modern_material_science": {"subject": "a sheet of shimmering iridescent hexagonal graphene draped over a steel block", "seed": 1},
        "quantum_computing": {"subject": "a golden chandelier-like quantum computer with tiers of copper tubes and cables", "seed": 1},
        "smart_grids": {"subject": "an electricity pylon with glowing blue data pulses running along its cables", "seed": 1},
        "synthetic_biology": {"subject": "a glowing green engineered cell in a petri dish with a pipette above it", "seed": 0},
        "biohacking_and_human_augmentation": {"subject": "a sleek chrome prosthetic arm with glowing blue joints", "seed": 1},
        "brain_computer_interfaces": {"subject": "a model of a human brain with a small circuit chip and fine wires attached", "seed": 1},
        "lab-grown_food": {"subject": "a round petri dish holding a pink cultured meat steak", "seed": 0},
        "personalized_medicine": {"subject": "a single capsule pill with a DNA helix pattern on its shell", "seed": 1},
        "universal_digital_identity": {"subject": "a plain pale blue identity card with a glowing blue fingerprint and a gold chip", "seed": 1},
        # era 12
        "antimatter_production": {"subject": "a glowing magnetic containment bottle with a bright violet sphere suspended inside", "seed": 1},
        "compact_fusion_reactors": {"subject": "a compact barrel-sized cylindrical fusion reactor core glowing blue-white at its centre", "seed": 1},
        "fusion_batteries": {"subject": "a chunky cylindrical battery cell with a glowing sun-like core behind a glass window", "seed": 3},
        "orbital_weapon_platforms": {"subject": "a large armed space station with a long cannon barrel and solar panel wings", "seed": 1},
        "space_based_solar_power": {"subject": "a vast orbiting solar panel array sending a thin red energy beam downward", "seed": 0},
        "space_elevator": {"subject": "a small blue-and-green Earth globe with a thin glowing cable rising from its equator up to a small grey space station above it, a cylindrical climber pod partway along the cable", "seed": 0},
        "advanced_nanofabrication": {"subject": "a tiny precise crystal lattice being built by a glowing needle-tipped robotic arm", "seed": 0},
        "artificial_intelligence": {"subject": "a silver humanoid robot head with a glowing blue brain visible under a glass dome", "seed": 1},
        "molecular_assemblers": {"subject": "a cluster of coloured atom spheres being snapped together by tiny robotic arms", "seed": 0},
        "orbital_manufacturing": {"subject": "a space station module with a robotic arm assembling a glowing crystal", "seed": 1},
        "programmable_matter": {"subject": "a shimmering silver liquid-metal blob reshaping itself into a cube and a sphere", "seed": 1},
        "quantum_materials": {"subject": "a glowing iridescent crystal block levitating above a superconducting disc", "seed": 1},
        "biological_immortality": {"subject": "a glass hourglass with a green sprouting sprig growing inside it", "seed": 1},
        "mind_backups": {"subject": "a glowing crystal data cube with the faint shape of a brain inside", "seed": 1},
        "neural_lace": {"subject": "a delicate glowing silver mesh net shaped like a human brain", "seed": 1},
        "post-scarcity_economy": {"subject": "an overflowing cornucopia horn spilling fruit, bread and gleaming gadgets", "seed": 1},
        "space_colonization": {"subject": "a domed habitat colony on a red rocky planet surface", "seed": 0},
        "telepathic_communities": {"subject": "two glowing translucent human heads facing each other, linked by a ribbon of light", "seed": 1},
    },
    "treaty_article": {
        # Mod-added treaty articles on a borrowed icon (18 on offer_embassy).
        "nuclear_security_assistance": {"subject": "a nuclear warhead locked inside a steel cage with a big padlock", "seed": 1},
        "nuclear_arms_limitation": {"subject": "a brass balance scale with one short grey missile standing on each pan", "seed": 1},
        "request_influence": {"subject": "a small figure bowing and offering up a silver key with both hands", "seed": 0},
        "crisis_resolution": {"subject": "a cracked stone pillar bound with a bandage and propped up by a wooden brace", "seed": 0},
        "extend_influence": {"subject": "a bronze hand pushing a black chess pawn forward on a small chessboard", "seed": 3},
        "education_aid": {"subject": "a stack of schoolbooks with a red apple on top", "seed": 1},
        "healthcare_aid": {"subject": "a black leather doctor's bag with a stethoscope draped over it", "seed": 1},
        "security_aid": {"subject": "a steel riot shield and a black police baton crossed together", "seed": 1},
        "development_assistance": {"subject": "a small brick schoolhouse under construction with wooden scaffolding", "seed": 0},
        "science_aid": {"subject": "a brass microscope standing on a wooden crate", "seed": 0},
        "science_aid_2": {"subject": "a brass microscope, a glass flask and a steel gear packed together in an open wooden crate", "seed": 1},
        "suppress_subject_liberty": {"subject": "a chess pawn bound with a heavy iron chain and padlock", "seed": 0},
        "nuclear_disarmament": {"subject": "a nuclear missile warhead cracked open, with a large steel wrench resting across it", "seed": 1},
        "nuclear_program_aid": {"subject": "a lead-lined steel case of glowing green uranium pellets", "seed": 1},
        "intelligence_sharing_pact": {"subject": "a manila dossier folder sealed with red wax, a brass magnifying glass lying on top", "seed": 1},
        "joint_military_exercises": {"subject": "two crossed rifles with two different-coloured steel helmets hung on them", "seed": 0},
        "join_united_nations": {"subject": "a small pale blue globe on a brass stand, wreathed in two olive branches", "seed": 1},
        "nuclear_program_pause": {"subject": "a nuclear warhead frozen inside a block of blue ice", "seed": 1},
        "disband_company": {"subject": "a small brick factory model cracked cleanly into two halves", "seed": 0},
        "seize_company": {"subject": "a hand grabbing a small brick factory model by its chimney", "seed": 1},
        "minority_protection": {"subject": "three small figures huddled together beneath a large raised steel shield", "seed": 1},
        "free_port_concession": {"subject": "an open brass padlock hanging from a ship's anchor", "seed": 1},
        "corporate_concessions": {"subject": "a brown leather briefcase with a gold key resting on top", "seed": 0},
        "enforce_privatization": {"subject": "a small brick factory model with a blank price tag tied to its chimney", "seed": 1},
        "religious_mission_rights": {"subject": "a closed brown leather book with a brass clasp and a plain unmarked cover, a wooden walking staff leaning against it", "seed": 0},
        "demilitarized_zone": {"subject": "an upturned steel army helmet with red poppies growing out of it", "seed": 1},
        "forced_disarmament": {"subject": "a heap of rifles and steel helmets bound together by a padlocked chain", "seed": 0},
        "cultural_exchange_program": {"subject": "two hands passing a small painted vase between them", "seed": 1},
        "enforce_emissions_reduction": {"subject": "a factory chimney with a big green cork stopper in its top", "seed": 0},
        "nuclear_guarantee": {"subject": "a large open steel umbrella with a yellow-and-black radiation trefoil painted on its canopy", "seed": 0},
        "population_transfer": {"subject": "a heap of worn suitcases and cloth bundles tied with rope", "seed": 1},
    },
    "diplomatic_action": {
        # Mod-added diplomatic actions on a borrowed icon. Three have a better
        # vanilla match than the one they borrowed.
        "voluntary_union": {"subject": "two bronze hands clasped in a handshake above a small white classical government building", "seed": 1},
        "voluntary_union_decentralized": {"subject": "an open bronze palm holding three small thatched village huts", "seed": 1},
        "irr_seek_war_blessing": {"subject": "a kneeling bronze figure presenting a sword across both open palms", "seed": 1},
        # The Nuclear Guarantee article's umbrella, furled.
        "nd_withdraw_umbrella_action": {"subject": "a closed, tightly furled steel umbrella with a yellow-and-black radiation trefoil on its fabric, lying on its side", "seed": 0},
        # The covert operations (pacts) had no icon at all; a black glove or mask marks the series.
        "covert_election_interference_action": {"subject": "a black-gloved hand slipping a folded paper ballot into a wooden ballot box", "seed": 0},
        "covert_financial_subversion_action": {"subject": "a black-gloved hand pulling a coin from the bottom of a teetering stack of gold coins", "seed": 1},
        "covert_infrastructure_sabotage_action": {"subject": "a bundle of dynamite sticks with a lit fuse strapped to a small steel bridge", "seed": 1},
        "covert_comms_disruption_action": {"subject": "an old black telephone with its cord snipped by a pair of red-handled pliers", "seed": 1},
        "covert_industrial_espionage_action": {"subject": "a black-gloved hand pulling a rolled blue blueprint out of a small brick factory's window", "seed": 2},
        "covert_military_espionage_action": {"subject": "a small brass spy camera photographing a folded military map with pins in it", "seed": 1},
        "covert_influence_campaign_action": {"subject": "a brass microphone draped with a black domino mask", "seed": 0},
        "covert_ideological_subversion_action": {"subject": "a stone pillar cracked through by a creeping black vine", "seed": 0},
        "covert_destabilization_action": {"subject": "a tower of wooden blocks toppling over, nudged by a black-gloved finger", "seed": 1},
        "covert_regime_change_action": {"subject": "a black-gloved hand lifting a small golden crown off a red cushion", "seed": 1},
        "covert_nuclear_sabotage_action": {"subject": "a pair of wire cutters snipping a red wire on a grey nuclear warhead marked with a yellow-and-black radiation trefoil", "seed": 1},
        "covert_space_espionage_action": {"subject": "a grey rocket standing on its launch pad with a small brass spy camera on a tripod aimed at it", "seed": 1},
        "covert_cultivate_assets_action": {"subject": "two hands in shadow exchanging a sealed brown envelope", "seed": 3},
        "covert_secure_material_action": {"subject": "a black-gloved hand gripping the handle of a lead-lined steel case marked with a radiation trefoil", "seed": 2},
        # Other actions that had no icon.
        "decolonize_diplo_action": {"subject": "an open brass birdcage with a small bird flying out of its door", "seed": 1},
        "annex_subject_peaceful": {"subject": "two small stone houses joined under a single shared roof", "seed": 1},
        "diplomatic_alignment": {"subject": "two bronze arrows side by side pointing upward, bound together with a red ribbon", "seed": 1},
        "humanitarian_aid": {"subject": "a wooden supply crate with a loaf of bread and a rolled brown blanket on top", "seed": 0},
        "nd_nuclear_warning_action": {"subject": "a brown envelope closed with a black wax seal stamped with a radiation trefoil", "seed": 0},
        "nd_nuclear_ultimatum_action": {"subject": "a bronze megaphone with a yellow-and-black radiation trefoil on its bell", "seed": 0},
        "nd_repudiate_pledge_action": {"subject": "a brown parchment scroll with a radiation trefoil, torn in two", "seed": 0},
        "nuke_diplo_action": {"subject": "a small bronze mushroom cloud rising over a cluster of factory chimneys", "seed": 1},
        "tactical_nuke_diplo_action": {"subject": "a small bronze mushroom cloud rising over a battlefield trench with a field gun", "seed": 1},
        "un_secure_commitment_action": {"subject": "two hands shaking above a small green wooden block", "seed": 1},
        "un_secure_commitment_against_action": {"subject": "two hands shaking above a small plain red square tile", "seed": 0},
        "un_lobby_for_action": {"subject": "a hand dropping a green voting card into a pale blue ballot box", "seed": 0},
        "un_lobby_against_action": {"subject": "a hand dropping a red voting card into a pale blue ballot box", "seed": 0},
        "colonial_culture_change": {"use": "gfx/interface/icons/diplomatic_action_icons/change_culture.dds"},  # culture change; the borrowed crest was religion's
        "force_cultural_acceptance": {"use": "gfx/interface/icons/diplomatic_action_icons/force_culture.dds"},  # the culture crest; the borrowed one was religion's
        "force_cultural_adoption": {"use": "gfx/interface/icons/diplomatic_action_icons/force_culture.dds"},  # the culture crest; the borrowed one was religion's
    },
}


def check(mod_root: str | None = None, on_disk: set[str] | None = None) -> dict:
    """Compare ICONS with the mod's entity files.

    Errors:
      unknown     a key with no plain top-level definition in its entity_dir
      bad_entry   an empty subject, a seed that is not None, an int or "keep",
                  or a "use" that is not a gfx/ .dds path
      missing_dds an accepted seed whose DDS is not committed (or on disk)
    Information:
      states      how many entries are unreviewed / accepted / kept / reused
    `on_disk` defaults to the icon paths git tracks, so it works in a sparse
    worktree.
    """
    import os
    import re
    import subprocess

    mod_root = mod_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if on_disk is None:
        out = subprocess.run(["git", "-C", mod_root, "ls-files", "--", "gfx/interface/icons"],
                             capture_output=True, text=True, check=True).stdout
        on_disk = set(out.splitlines())
    report: dict = {"unknown": [], "bad_entry": [], "missing_dds": [], "states": {}}
    for cat, entries in ICONS.items():
        spec = CATEGORIES[cat]
        defined: set[str] = set()
        for dirpath, _dirs, files in os.walk(os.path.join(mod_root, spec["entity_dir"])):
            for fname in files:
                if fname.endswith(".txt"):
                    with open(os.path.join(dirpath, fname), encoding="utf-8-sig", errors="replace") as fh:
                        defined |= set(re.findall(r"^([A-Za-z0-9_\-]+)\s*=\s*\{", fh.read(), re.M))
        states = {"unreviewed": 0, "accepted": 0, "kept": 0, "reused": 0}
        for key, entry in entries.items():
            if key not in defined:
                report["unknown"].append((cat, key))
            if "use" in entry:
                use = entry["use"]
                if isinstance(use, str) and use.startswith("gfx/") and use.endswith(".dds"):
                    states["reused"] += 1
                else:
                    report["bad_entry"].append((cat, key))
                continue
            seed = entry.get("seed")
            if not entry.get("subject") or not (seed is None or seed == KEEP
                                                or (isinstance(seed, int) and seed >= 0)):
                report["bad_entry"].append((cat, key))
                continue
            if seed is None:
                states["unreviewed"] += 1
            elif seed == KEEP:
                states["kept"] += 1
            else:
                states["accepted"] += 1
                if icon_path(cat, key) not in on_disk:
                    report["missing_dds"].append((cat, key))
        report["states"][cat] = states
    return report


def validate() -> bool:
    r = check()
    for title in ("unknown", "bad_entry", "missing_dds"):
        if r[title]:
            print(f"{title.upper()} ({len(r[title])}):")
            for cat, key in r[title]:
                print(f"  {cat}/{key}")
    for cat, states in r["states"].items():
        print(f"{cat}: " + ", ".join(f"{n} {s}" for s, n in states.items()))
    errors = len(r["unknown"]) + len(r["bad_entry"]) + len(r["missing_dds"])
    print(f"Errors: {errors}")
    return errors == 0


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        sys.exit(0 if validate() else 1)
    for cat, entries in ICONS.items():
        print(f"{cat}: {len(entries)} icons")
