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
preventing repeats while the player considers the choices. Every option grants
its own modest permanent journal-entry modifier through the existing
`sr_grant_colony_modifier` ledger. Monthly entry synchronization restores missing
rewards after a revolution, using the same inherited country records as ordinary
colony specializations. Pending discoveries and timers are country variables,
so they follow the game's normal revolution inheritance. No flags are cleared
by milestone cleanup. Colony surveys continue when the expansion program is
idle and after all 34 sites have been claimed. Existing saves receive no
retroactive rolls for colonies founded before this change.

The two Europa candidates are independent: detecting vents neither guarantees
nor excludes life. The two living-biology events use reproducible growth and
metabolism with contamination controls. Martian evidence remains a candidate
biosignature. Other organic finds explicitly do not establish biology.

## Choice rewards

Each event has separate permanent modifiers for its two options, so discoveries
stack with earlier colony specializations and with other discoveries. The
research option gives +1% research speed, or +2% for the three biological finds.
Other options use the following bonuses:

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

All descriptions are fictional future colony findings. The links distinguish
observations and research models from the extrapolations used for each event.
Existing colony pictures are reused. Probabilities apply per eligible month.

| ID | Colony | Discovery | Monthly chance | Choices |
|---|---|---|---|---|
| 1 | europa | A Second Living World | 1% | Protect the ocean and establish a permanent biology institute. / Publish the evidence through an international research consortium. |
| 2 | europa | Chimneys Beneath the Ice | 2% | Keep the vent field undisturbed for chemical research. / Develop instruments for operations in hot, pressurized water. |
| 3 | enceladus | Life in the Ice Grains | 1% | Designate the plume catchment as a protected biological reserve. / Share sealed samples and methods with international laboratories. |
| 4 | titan | An Impact-Born Chemical Laboratory | 2% | Preserve the deposit and reconstruct its chemical history. / Use the reaction pathways to improve industrial synthesis. |
| 5 | hellas_planitia | An Ancient Martian Biosignature | 1% | Protect the excavation and fund further tests of the biological interpretation. / Open the archive to international teams for independent scrutiny. |
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
| 16 | ganymede | Oceans Between Layers | 2% | Publish a model of the layered ocean and its chemical limits. / Develop instruments and pressure vessels for deep-ice operations. |
| 17 | callisto | The Crater Under the Crater | 2% | Keep the layered section intact as an impact chronology. / Use mapped deposits to improve shielding and construction. |
| 18 | titania | Warmth Beneath Titania | 2% | Keep a permanent observatory above the liquid layer. / Apply the deep-ice survey methods to colony engineering. |
| 19 | triton | A Jet Beneath the Landing Field | 2% | Close the field and establish a remote geyser observatory. / Relocate the field and develop pressure monitoring equipment. |
| 20 | pluto | Antifreeze at the Edge of the System | 2% | Map the buried ocean and preserve the fracture samples. / Use the low-temperature chemistry to improve cryogenic systems. |

### 1. A Second Living World

An ocean and possible water-rock energy sources make microbes and hydrothermal activity plausible; neither has been detected. The event's cultures and probes are fictional future results. [Europa: ingredients for life](https://science.nasa.gov/mission/europa-clipper/why-europa-ingredients-for-life/).

### 2. Chimneys Beneath the Ice

An ocean and possible water-rock energy sources make microbes and hydrothermal activity plausible; neither has been detected. The event's cultures and probes are fictional future results. [Europa: ingredients for life](https://science.nasa.gov/mission/europa-clipper/why-europa-ingredients-for-life/).

### 3. Life in the Ice Grains

Phosphorus adds to evidence for habitable chemistry. Living organisms are an extrapolation, requiring reproducible metabolism, reproduction, and contamination controls. [Cassini: phosphorus in Enceladus' ocean](https://www.nasa.gov/missions/cassini/nasa-cassini-data-reveals-building-block-for-life-in-enceladus-ocean/).

### 4. An Impact-Born Chemical Laboratory

Impact heating can mix organics and liquid water. Preserved reaction products are plausible; the event claims no life. [Impact craters and Titan's chemistry](https://www.nasa.gov/missions/cassini/impact-craters-reveal-details-of-titans-dynamic-surface-weathering/).

### 5. An Ancient Martian Biosignature

Potential biosignatures require exclusion of abiotic explanations. Hellas deposits and stronger converging evidence are fictional, and the event leaves confirmation open. [Potential Martian biosignatures](https://www.nasa.gov/news-release/nasa-says-mars-rover-discovered-potential-biosignature-last-year/).

### 6. Rooms Inside the Volcano

Lava tubes could shelter subsurface exploration and habitats. An extensive stable network near Olympus Mons remains a fictional local discovery. [Mars cave exploration mission concept](https://arxiv.org/abs/2105.05281).

### 7. The Buried Glacier

Buried Martian ice is real; unusually clean, thick and accessible layers are the rare local variation. [Mars subsurface ice mapping](https://science.nasa.gov/resource/location-of-large-subsurface-water-ice-deposit-in-utopia-planitia-mars/).

### 8. Salt Water in the Drill

Models severely constrain near-surface brines. Drilling heat melts salty ice temporarily in this event; no persistent natural liquid or inhabited aquifer is asserted. [Martian brines and habitability](https://arxiv.org/abs/2012.00100).

### 9. A Reservoir Below Ceres

Dawn data support deep brines near Occator. The accessible branch and useful yields are extrapolations, with no claim of biology. [Ceres' buried salty reservoir](https://www.jpl.nasa.gov/news/mystery-solved-bright-areas-on-ceres-come-from-salty-water-below/).

### 10. A Visitor Preserved in Vesta

Carbonaceous impactors explain dark material on Vesta. The preserved buried fragments are a plausible local variation; organics do not establish life. [Carbonaceous material delivered to Vesta](https://ntrs.nasa.gov/citations/20120011565).

### 11. A Rich Seam in Psyche

Psyche may mix substantial metal and rock. A continuous rich seam is speculative, and the event avoids treating a bare metallic core as established. [Psyche mission overview](https://science.nasa.gov/mission/psyche/mission-overview/).

### 12. Water Bound in Stone

Spectra support hydrated minerals on Pallas. A concentrated seam and viable thermal extraction are fictional local and engineering outcomes. [Pallas surface hydration](https://www.lpi.usra.edu/meetings/lpsc1995/pdf/1587.pdf).

### 13. A Wave That Holds Its Ground

Terrain-associated stationary atmospheric gravity waves have been observed. Better forecasts for an aerostat colony are an engineering extrapolation. [Stationary waves in Venus' clouds](https://arxiv.org/abs/1707.07796).

### 14. An Archive in Permanent Shadow

Ice and a possibly organic dark covering occur in permanently shadowed craters. The unusually thick and useful deposit is the rare variation. [Mercury polar ice and dark material](https://www.jpl.nasa.gov/news/nasa-spacecraft-finds-new-mercury-water-ice-evidence/).

### 15. The Moving Floor of Io

Io is volcanically active. A changing lava channel beneath a colony is a plausible local hazard; adaptive infrastructure is speculative engineering. [Io overview](https://science.nasa.gov/jupiter/moons/io/).

### 16. Oceans Between Layers

Layered liquid and high-pressure ice are modeled possibilities. The event supplies future measurements and emphasizes restricted rock-water exchange. [Ganymede ocean layers](https://www.jpl.nasa.gov/news/ganymede-may-harbor-club-sandwich-of-oceans-and-ice/).

### 17. The Crater Under the Crater

Callisto has an old, heavily cratered surface. A well-preserved, datable buried sequence is the rare local discovery. [Callisto overview](https://science.nasa.gov/jupiter/moons/callisto/).

### 18. Warmth Beneath Titania

Models allow Titania to retain a liquid layer. Its detection is fictional; chemistry, rock contact and biology remain unconfirmed. [Possible oceans in Uranus' large moons](https://www.jpl.nasa.gov/news/new-study-of-uranus-large-moons-shows-4-may-hold-water/).

### 19. A Jet Beneath the Landing Field

Nitrogen jets are observed, with solar heating beneath translucent ice a proposed mechanism. The landing-field hazard is fictional. [Triton overview](https://science.nasa.gov/neptune/moons/triton/).

### 20. Antifreeze at the Edge of the System

Models consider ocean survival and ammonia chemistry. Future cores and seismic evidence are extrapolations; no organisms are inferred. [Pluto and Triton ocean evolution](https://ael.gsfc.nasa.gov/600/public-nuggets/Triton-nugget20240401.pdf).
