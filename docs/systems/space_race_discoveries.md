# Rare solar colony discoveries

Twenty one-time follow-up events extend the 34 existing founding events. Each
candidate gets an independent 10% roll when its site is actually claimed in
`sr_establish_colony_effect`, before the normal founding event. This choice is
hidden and does not depend on the specialization selected afterward.

The country keeps a permanent `sr_discovery_<key>_rolled` record even on a failed
roll. Success sets a pending flag and a 365-day survey clock. After that clock
expires, each candidate gets its listed monthly percentage, while the Space Race
rule is enabled and the country holds a colony. A successful roll reserves a
180-day country cooldown before dispatch, so at most one discovery is queued at
a time. Candidates later in the list do not roll during that cooldown. They
remain pending, so discoveries are spaced without discarding other results.
A single unobstructed candidate at 1% takes about 69 eligible monthly rolls for
its median discovery time; at 2% it takes about 35. The survey year and cooldown
months are additional. These percentages balance game rarity; they do not
estimate the probability of extraterrestrial life or geological features.

The event consumes its pending flag immediately and sets a permanent done flag,
preventing repeats while the player considers the choices. Every option records
the choice on the world (`sr_site_disc_<d>`, 1 or 2) through its generated
dispatcher, `sr_site_choose_<outcome>`, and the world's sync marks the holder's
`<outcome>_held`. Pending discoveries and timers are country variables, so they
follow the game's normal revolution inheritance; the choice is the world's, so
a cession or an heir takes it, and a release clears it. No flags are cleared by
milestone cleanup. Colony surveys continue when the expansion program is idle
and after every site has been claimed. Existing saves receive no retroactive
rolls for colonies founded before this change.

The two Europa candidates are independent: detecting vents neither guarantees
nor excludes life. The two living-biology events use reproducible growth and
metabolism with contamination controls. The Hellas event establishes ancient microbial fossils. Chemistry and geology
finds report their own confirmed results without implying an additional life
discovery.

## Choice rewards: site boons

Under Simple and Full Colonies (the default), each option is its world's
**boon** (the owner, 2026-11-25): +100% to one module's effect at that world.
The first option studies the find and boosts the Research Station; the second
puts it to use and boosts the module its text names. The table is
`DISCOVERY_BOONS` in `scripts/generators/gen_solar_sites.py`, and the bonus
`BOON_BONUS` (`sr_site_boon_bonus`, 1).

- **Values** (generated, `common/script_values/sr_sites_generated.txt`):
  `sr_site_boon_<type>_<key>` is 1 plus the bonus for each of the world's
  discoveries whose recorded option names the type, emitted only where a
  discovery there can; `sr_site_<type>_eff_<key>` is the facility's staffed
  levels times it, and `sr_site_hab_share_eff_<key>` the Habitat's share of the
  base room times it. Where no discovery can boost a type, the readers take
  `sr_site_<type>_staffed_<key>` and `sr_site_hab_share_value_<key>` as before
  (`eff_value`, `hab_share_eff`).
- **Readers:** every facility's `sr_mod_units_<type>` (so the entry's
  `sr_module_<type>` modifiers, fabrication and Space Command from Orbital
  Yards, command reliability, the marines' training weight), a world's
  Extraplanetary Base room (Mining Complex), Resort Colony room (Off-World
  Resort) and Resort Draw (Cultural Center), its Terraforming pace, and its room
  for people (Habitat, and the room a dismantled Habitat leaves). The
  Administration is never boosted (its staffed levels are also its authority
  bill), nor Defences and Spaceport (`gen_space_fleets.py` reads their levels).
- **The choice's tooltip** is `<outcome>_tt` under Simple and Full Colonies.
- **Panel:** the colony's page shows a line under each boosted module for each
  discovery boosting it, "<the event's title>: +100%"
  (`je_space_race_widget_mod_boon_<d>`, shown by `sr_disp_site_disc_<d>`), its
  hover the outcome's tooltip: `te_sr_page_boon_line` instances in
  `te_sr_page_mod_row`'s `row_boons` block, measured by
  `test_space_race_labels.py`. The list's Modules view shows nothing extra.
- **AI:** the options keep `ai_chance` 5 each. `sr_mod_ai_plan_<key>` builds an
  Orbital Yard, Cultural Center, Black Site, Training Ground or Materials
  Foundry that a boon there doubles before its fallback Research Station
  (`AI_BOON_ALWAYS`); the other boons work through the needs the plan already
  has.
- **Tests:** `test_space_race_discoveries.py` `BoonTests`.

| Choice | Discoveries | Boon |
|---|---|---|
| Study, preserve or observe (first option) | all twenty | Research Station |
| International scrutiny or cooperation | Europa life, Enceladus life, Hellas fossils | Cultural Center |
| Engineering | Europa vents, Arcadia brines, Ganymede layers, Triton jet | Orbital Yard |
| Materials processing | Titan chemistry, Vesta impactor, Pluto antifreeze | Materials Foundry |
| Extraction | Ceres reservoir, Psyche metal, Mercury archive, Io roof | Mining Complex |
| Habitat construction, shielding or local water | Olympus tubes, Pallas water, Callisto archive, Titania ocean | Habitat |
| Water for a future atmosphere | Utopia glacier | Terraforming |
| Aerostat navigation | Venus waves | Off-World Resort |

Europa's two discoveries can both boost its Research Stations (+200%).

### Under Races Only

Races Only has no modules, so there each option keeps its own modest permanent
modifier (`common/static_modifiers/space_race_discovery_modifiers.txt`), which
the solar colonization entry declares while the holder's `<outcome>_held` is set
and the setting is Races Only (1.15 scaling modifiers, #1404); a revolution's
winner, which inherits the record, keeps it. The option's tooltip shows the
modifier there. The research option gives +1% research speed, or +2% for the
three biological finds. Other options use the following bonuses:

| Choice | Permanent bonus |
|---|---|
| International scrutiny or cooperation | +3% prestige, +0.5 diplomatic reputation |
| Engineering | +1% Launch Capacity output, +0.1 monthly space race progress |
| Materials processing | +2% Advanced Materials output |
| Habitat construction or shielding | +2% Extraplanetary Base throughput |
| Water or propellant development | +1% Extraplanetary Base throughput, +1% Launch Capacity output |

These choices fund different uses of a local finding; none assumes alien
technology, rapid terraforming, or profitable export of bulk material to Earth.

## Event catalog and scientific foundations

The events occur after a permanent colony has had time to survey, excavate,
operate laboratories and develop instruments on the world in question. Every
event reports a confirmed discovery in that fictional future. The choice is
what to do with the finding: preserve it, investigate its history, share it, or
develop its practical uses. Further research concerns those uses and details.

The source notes below describe present-day observations and research models.
Their uncertainty concerns what humanity knows today; it does not qualify the
results reported by the future colony.
Existing colony pictures are reused. Probabilities apply per eligible month.

| ID | Colony | Discovery | Monthly chance | Choices |
|---|---|---|---|---|
| 1 | europa | The Cultures Grew | 1% | Protect the ocean and establish a permanent biology institute. / Share the discovery through an international research consortium. |
| 2 | europa | Chimneys Beneath the Ice | 2% | Keep the vent field undisturbed for chemical research. / Develop instruments for operations in hot, pressurized water. |
| 3 | enceladus | Life in the Ice Grains | 1% | Designate the plume catchment as a protected biological reserve. / Share sealed samples and methods with international laboratories. |
| 4 | titan | An Impact-Born Chemical Laboratory | 2% | Preserve the deposit and reconstruct its chemical history. / Use the reaction pathways to improve industrial synthesis. |
| 5 | hellas_planitia | The Fossils of Hellas | 1% | Protect the fossil beds and establish a paleontology institute. / Open the fossil archive to international research teams. |
| 6 | olympus_mons | Rooms Inside the Volcano | 2% | Survey the tubes as an archive of Martian volcanism. / Fit inspected chambers with sealed habitat modules. |
| 7 | utopia_planitia | The Buried Glacier | 2% | Preserve a continuous core for climate research. / Develop the cleanest ice layers as a water and propellant source. |
| 8 | arcadia_planitia | Salt Water in the Drill | 2% | Isolate the boreholes and study the salt chemistry. / Build purification systems and corrosion-resistant equipment. |
| 9 | ceres | A Reservoir Below Ceres | 2% | Keep the fracture network available for geochemical research. / Extract and purify brine under controlled conditions. |
| 10 | vesta | A Visitor Preserved in Vesta | 2% | Keep the impactor fragments together as a scientific collection. / Use the contrast between deposits to improve mineral sorting. |
| 11 | psyche | A Rich Seam in Psyche | 2% | Study the seam before altering its geological context. / Develop the deposit with selective mining. |
| 12 | pallas | Water Bound in Stone | 2% | Preserve the seam as a record of early water chemistry. / Build thermal extraction equipment for local water supplies. |
| 13 | venus | A Wave That Holds Its Ground | 2% | Build a long-term atmospheric observatory. / Use the wave forecasts to improve aerostat navigation. |
| 14 | mercury | An Archive in Permanent Shadow | 2% | Protect representative layers for volatile and organic chemistry research. / Develop the deposit as a local water and propellant source. |
| 15 | io | The Moving Floor of Io | 2% | Move the installations and monitor the channel from a safe distance. / Develop mobile foundations and continuous subsurface warning systems. |
| 16 | ganymede | Oceans Between Layers | 2% | Publish the mapped ocean structure and chemical profiles. / Develop instruments and pressure vessels for deep-ice operations. |
| 17 | callisto | The Crater Under the Crater | 2% | Keep the layered section intact as an impact chronology. / Use mapped deposits to improve shielding and construction. |
| 18 | titania | Warmth Beneath Titania | 2% | Keep a permanent observatory above the liquid layer. / Apply the deep-ice survey methods to colony engineering. |
| 19 | triton | A Jet Beneath the Landing Field | 2% | Close the field and establish a remote geyser observatory. / Relocate the field and develop pressure monitoring equipment. |
| 20 | pluto | Antifreeze at the Edge of the System | 2% | Map the buried ocean and preserve the fracture samples. / Use the low-temperature chemistry to improve cryogenic systems. |

### 1. The Cultures Grew

Present-day evidence supports an ocean and possible water-rock energy sources. Event 1 establishes living microbes through replicated cultures; event 2 establishes a hydrothermal vent field through direct surveys and sampling. [Europa: ingredients for life](https://science.nasa.gov/mission/europa-clipper/why-europa-ingredients-for-life/).

### 2. Chimneys Beneath the Ice

Present-day evidence supports an ocean and possible water-rock energy sources. Event 1 establishes living microbes through replicated cultures; event 2 establishes a hydrothermal vent field through direct surveys and sampling. [Europa: ingredients for life](https://science.nasa.gov/mission/europa-clipper/why-europa-ingredients-for-life/).

### 3. Life in the Ice Grains

Present-day phosphorus measurements add to evidence for habitable chemistry. The future colony confirms indigenous life through replicated culture experiments and contamination controls. [Cassini: phosphorus in Enceladus' ocean](https://www.nasa.gov/missions/cassini/nasa-cassini-data-reveals-building-block-for-life-in-enceladus-ocean/).

### 4. An Impact-Born Chemical Laboratory

Impact heating can mix organics and liquid water. The future colony identifies preserved reaction products and reproduces their formation in its laboratories. [Impact craters and Titan's chemistry](https://www.nasa.gov/missions/cassini/impact-craters-reveal-details-of-titans-dynamic-surface-weathering/).

### 5. The Fossils of Hellas

Present-day Martian biosignatures remain under investigation. The future Hellas colony confirms mineralized microbial fossils, growth layers and metabolic chemistry through independent laboratory analysis. [Potential Martian biosignatures](https://www.nasa.gov/news-release/nasa-says-mars-rover-discovered-potential-biosignature-last-year/).

### 6. Rooms Inside the Volcano

Lava tubes are plausible settings for subsurface exploration and habitats. The future colony maps a stable network near Olympus Mons and certifies inspected chambers for occupation. [Mars cave exploration mission concept](https://arxiv.org/abs/2105.05281).

### 7. The Buried Glacier

Buried Martian ice is real; unusually clean, thick and accessible layers are the rare local variation. [Mars subsurface ice mapping](https://science.nasa.gov/resource/location-of-large-subsurface-water-ice-deposit-in-utopia-planitia-mars/).

### 8. Salt Water in the Drill

Present-day models constrain near-surface brines. The future colony establishes the composition of a corrosive perchlorate deposit and measures the temporary brine produced by its drilling equipment. [Martian brines and habitability](https://arxiv.org/abs/2012.00100).

### 9. A Reservoir Below Ceres

Dawn data support deep brines near Occator. The future colony maps an accessible branch, samples its chemistry and demonstrates usable yields through trial extraction. [Ceres' buried salty reservoir](https://www.jpl.nasa.gov/news/mystery-solved-bright-areas-on-ceres-come-from-salty-water-below/).

### 10. A Visitor Preserved in Vesta

Carbonaceous impactors explain dark material on Vesta. The future colony recovers buried fragments and establishes their origin and mineral history. [Carbonaceous material delivered to Vesta](https://ntrs.nasa.gov/citations/20120011565).

### 11. A Rich Seam in Psyche

Present-day observations indicate mixed metal and rock on Psyche. The future colony maps and assays a continuous rich seam within that mixture. [Psyche mission overview](https://science.nasa.gov/mission/psyche/mission-overview/).

### 12. Water Bound in Stone

Spectra support hydrated minerals on Pallas. The future colony maps a concentrated seam and demonstrates thermal extraction in an operating pilot plant. [Pallas surface hydration](https://www.lpi.usra.edu/meetings/lpsc1995/pdf/1587.pdf).

### 13. A Wave That Holds Its Ground

Terrain-associated stationary atmospheric gravity waves have been observed. The future colony measures their behavior over an extended survey and establishes forecasts for its aerostat crews. [Stationary waves in Venus' clouds](https://arxiv.org/abs/1707.07796).

### 14. An Archive in Permanent Shadow

Present-day observations support polar ice and a dark covering that may contain organics. The future colony samples an unusually thick deposit and establishes its chemistry and extraction yield. [Mercury polar ice and dark material](https://www.jpl.nasa.gov/news/nasa-spacecraft-finds-new-mercury-water-ice-evidence/).

### 15. The Moving Floor of Io

Io is volcanically active. The future colony directly maps a changing lava channel beneath existing installations and identifies the structures threatened by collapse. [Io overview](https://science.nasa.gov/jupiter/moons/io/).

### 16. Oceans Between Layers

Present-day models allow layered liquid and high-pressure ice. The future colony establishes the layering and salinities through seismic profiles and borehole samples. [Ganymede ocean layers](https://www.jpl.nasa.gov/news/ganymede-may-harbor-club-sandwich-of-oceans-and-ice/).

### 17. The Crater Under the Crater

Callisto has an old, heavily cratered surface. The future colony dates a preserved buried sequence and establishes an impact chronology. [Callisto overview](https://science.nasa.gov/jupiter/moons/callisto/).

### 18. Warmth Beneath Titania

Present-day models allow Titania to retain a liquid layer. The future colony confirms the ocean, measures its salts and ammonia, and establishes its heat supply. [Possible oceans in Uranus' large moons](https://www.jpl.nasa.gov/news/new-study-of-uranus-large-moons-shows-4-may-hold-water/).

### 19. A Jet Beneath the Landing Field

Nitrogen jets are observed, with solar heating beneath translucent ice a proposed mechanism. The future colony measures that mechanism directly and maps the deposit threatening its landing field. [Triton overview](https://science.nasa.gov/neptune/moons/triton/).

### 20. Antifreeze at the Edge of the System

Present-day models consider ocean survival and ammonia chemistry. The future colony confirms an ocean through deep sounding and recovered fluid, and establishes the chemical and thermal conditions sustaining it. [Pluto and Triton ocean evolution](https://ael.gsfc.nasa.gov/600/public-nuggets/Triton-nugget20240401.pdf).
