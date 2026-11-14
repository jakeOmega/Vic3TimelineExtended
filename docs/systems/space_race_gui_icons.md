# Space Race GUI: Icons

The Space Race panels' overview (the GUI style guide pass, September 2026) draws 62 icons of its own, including three pie layers, ten for the kinds of world in Our Colonies, thirteen on a colony's page and the twenty-one pictograms of the fleet cards and Locations. They were vanilla or borrowed placeholders in the first rounds of the pass (`gui_style_guide.md` rule 10), and PR #586 replaced them. All of them live in `gfx/interface/icons/space_race_icons/`. The programme row's seven single-state icons are the journal-entry icons painted in PR #571 (`gfx/interface/icons/event_icons/je_space_race_<m>.dds`), used as they are.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/space_race_widget.gui`, in the type named below, and the states are chosen by a display value's code. No script reads the paths. `SpaceRaceIconsTest` in `test_space_race_layout.py` holds each state to its file, and each tile and module row on a colony's page to its own. It also fails on any placeholder left in the widget, and, once #586's files are in the repo, on any path that does not exist.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries are the `space_part` (the one rocket, the colony's pennant), `space` (the first, the first-to-finish mark, the stage, the ten colony kinds, the warship, the module, and a colony page's crew and seven modules) and `space_state` (the five states, the risk, the four interstellar states, and a colony page's five derived tiles) categories in `icon_prompts.py`. Each entry's `now` field names the placeholder it replaced. The pies are plain discs from `scripts/image_pipeline/gen_ch_model_pie_textures.py`. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's (`un_gui_icons.md`): simple and easy to recognize at 32–40 px. The five state icons and the risk share one emblem, a silver rocket with red fins, and differ by what surrounds it.

## Overview: the milestone's state

Shown at 36 px, one at a time, chosen by `sr_disp_status_<m>` (and Idle by the scripted GUI's `is_shown`). Set in `te_sr_overview_milestone`.

| State | Shows | File |
|---|---|---|
| Idle (colonization not running) | the rocket, greyed | `state_idle.dds` |
| Standard (where every milestone starts) | the rocket rising on a short flame | `state_standard.dds` |
| Safe (the word carries the weekly cost) | the rocket on its pad inside a blue shield | `state_safe.dds` |
| Ambitious (the word carries the weekly cost) | the rocket climbing at a slant on a long flame | `state_ambitious.dds` |
| Shielded (post-setback review; no longer shown since the cooldown went, 2026-10-31) | the rocket under a glass dome, vanilla's clock at its foot | `state_shielded.dds` |

The list asked for an empty launch gantry for Idle; at 36 px the gantries were thin lattices, so Idle is the rocket greyed. It also asked for a white rocket, which loses its body in the cut-out, so the rocket is silver.

## Overview: risk, the first, the stage

| Cell | Shows | File |
|---|---|---|
| Setback risk (lit while a roll is made, 25% otherwise) | the rocket cracked, under vanilla's warning mark | `risk.dds` |
| The first: open (lit) / claimed (25%) | a gold pennant on a staff, planted on a grey crater rim | `first.dds` |
| Colonization's stage | a rust-red ringed planet, a small domed settlement on its upper edge | `stage.dds` |

The risk icon was to be a cracked nozzle; the nozzle alone is a speck at 36 px, so the whole rocket is cracked. The First cell is set in `te_sr_ov_first`, the stage in the solar colonization overview root. The 25% fades are by design: they are the icon's "off" state, not a placeholder.

## Programme row: the first-to-finish mark

| Mark | Shows | File |
|---|---|---|
| We were first (18 px, top right of the entry's icon) | a bold gold pennant on a short staff | `first_mark.dds` |

Set in `te_sr_ov_prog_cell` and `te_sr_ov_prog_cell_interstellar`.

## Programme row: the interstellar icon, four states

The Interstellar Probe and Interstellar Probe: Awaiting Data share one 44 px icon in the programme row (owner's play-test, round 3). Each state is its own icon with its own texture and tooltip (`je_space_race_widget_prog_interstellar_<n>`), shown by one test on `sr_disp_prog_interstellar`, so only one ever shows. The art carries the state, so none is faded. Set in `te_sr_ov_prog_cell_interstellar`.

| Code | State | Shows | File |
|---|---|---|---|
| 0 | Not begun (or another power finished it first) | the #571 probe icon, greyed | `interstellar_not_begun.dds` |
| 1 | Under way | the probe icon, a brass wrench at its corner | `interstellar_under_way.dds` |
| 2 | Launched, awaiting data | the #571 radio-dish icon, vanilla's clock at its corner | `interstellar_awaiting_data.dds` |
| 3 | Data received | the dish icon, vanilla's green check at its corner | `interstellar_data_received.dds` |

The list asked for four new drawings. The art builds them on the #571 journal icons instead, so the row keeps the Space Race's painted disc.

## Colonization: the worlds pie

Three stacked `progresspie` layers in `te_sr_ov_pie` (the recipe in `gui_modding_guide.md`, "Pie charts of script-held data"), each a 256×128 texture drawn as frame 2 of 128. Plain discs from `gen_ch_model_pie_textures.py`, checked for colour-blind contrast on every pair.

| Layer | Colour | File |
|---|---|---|
| The unclaimed rest (the disc) | muted grey `#8c8474` | `pie_unclaimed.dds` |
| Worlds claimed by anyone | rust red `#cf4a2a` | `pie_claimed.dds` |
| Ours, on top | bright gold `#ecc043` | `pie_ours.dds` |

## Colonies: the kind of world

One icon for each of ten kinds of world, not one for each of the 40 worlds. It shows at 24 px, left of the world's name, in `te_sr_colony_row`, which takes the file from a `colony_icon` block override on each of the 40 generated rows (`gen_solar_sites.py`, audit SPC-19). A row shows the icon of the kind its world belongs to. `ColoniesTest` holds every row to its kind.

| Kind | Worlds | Shows | File |
|---|---|---|---|
| The Moon | Shackleton, Peary, Tranquility, Marius Hills, Daedalus, Imbrium | a mid-grey Moon, evenly lit, with dark seas across its face and a few bright craters | `colony_moon.dds` |
| Mars | Valles Marineris, Olympus Mons, Hellas, Utopia, Arcadia | a rust-red planet with canyon scars and a pale polar cap | `colony_mars.dds` |
| Asteroid | Ceres, Vesta, Psyche, Pallas, Hygiea | a lumpy, cratered grey-brown rock | `colony_asteroid.dds` |
| Jovian moon | Io, Europa, Ganymede, Callisto, Himalia, Amalthea | a cratered moon before a banded orange gas giant | `colony_jovian.dds` |
| Venus | Venus | a smooth pale-yellow planet with soft cloud bands | `colony_venus.dds` |
| Mercury | Mercury | a grey planet of cracked rock, shaded on its lower right | `colony_mercury.dds` |
| Saturnian moon | Titan, Enceladus, Rhea, Mimas, Iapetus | a hazy orange planet with a tan ring tilted across its middle | `colony_saturnian.dds` |
| Uranian moon | Titania, Oberon, Miranda, Ariel | an icy grey-blue moon with dark craters | `colony_uranian.dds` |
| Neptunian moon | Triton, Proteus | a pink moon with a dark geyser streak across it | `colony_neptunian.dds` |
| Dwarf planet | Pluto, Eris, Makemake, Haumea, Sedna | a tan-and-brown dwarf planet with a pale heart patch and a tiny moon | `colony_dwarf.dds` |

The kinds group worlds by the body they orbit. Each falls inside one stage (the Moon in stage 0, Mars and the asteroids in stage 1, the Jovian moons and Venus in 2, Mercury and the Saturnian moons in 3, the Uranian and Neptunian moons in 4, the dwarf planets in 5), so no kind's icon sits under two stage headings. A world that is mostly white or pale loses its body in the cut-out, so Venus and the dwarf planet are drawn in colour. The modifiers' own icons (`icon =` on the 80 `sr_colony_*` static modifiers) are not these: they are the shared lightbulb and coins glyphs that say what kind of effect it is.

## Colonization overview and Locations: warships and modules

Where a cell names what a building does (audit SPC-6, SPC-16), it showed that building's icon until icon batch 7 (2026-10-30): Space Command's and the Space Program's. Solar System's inbound column keeps the colony fleets' rocket, so warships on their way wear their own.

| Cell | Shows | File |
|---|---|---|
| Defense and Hostile Fleet (44 px, under Full colonies) and Locations' inbound column (16 px) | a dark grey armed spacecraft with a twin turret on its back | `warship.dds` |
| Modules (44 px) | a silver habitat module in gold foil bands, a docking ring at one end | `module.dds` |

## A colony's page (2026-10-30)

The page a colony's name opens (colony management design § 8, rebuilt on the owner's review of 2026-10-30) shows each reading in a tile with its icon in an inset box at 34 px (`te_sr_page_tile`), and each module on a line with its icon at 24 px (`te_sr_page_mod_row`). Every icon is a literal `texture` line in the page body of `te_sr_colony_row`. The specializations use `module.dds`, the Slots tile too.

**Kept.** Icons that already show the thing: vanilla's population (People), battalions (Marines), construction mark (Building) and level trend (Drift), and the government administration building (Administration); the mod's Extraplanetary Base (Base Room, Mining Complex), Space Command (Orbital Yard), tourism industry (Off-World Resort), covert operation slot (Black Site) and advanced material fabricator (Materials Foundry); and the Mars colony's own icon (`colony_mars.dds`) for Terraforming's module row and Terraformed tile (era 13 spec § 7.11), the red world being made over, until the module has an icon of its own.

**Its own** (icon batch 8, 2026-10-31), each a vanilla or borrowed placeholder until then. Four tiles are the Habitat's dome with something drawn on or around it (`space_state`, derived), so the Autonomy and Defenses sections read as one family; Modules Crewed is the Modules cell's module with vanilla's population mark as its crew badge. `PAGE_ICONS` in `test_space_race_layout.py` holds each to its tile or row.

| Where | Was | Shows | File |
|---|---|---|---|
| Crews tile | `character_trait_icons/engineer.dds` | a colonist in an orange pressure suit with a gold visor, a big wrench in hand, seen from the side | `page_crews.dds` |
| Modules Crewed tile | `generic_icons/employment_not_full.dds` | the silver module with vanilla's population mark at its lower right | `page_crewed.dds` |
| Autonomy tile | `diplomatic_action_icons/liberty_desire.dds` | the Habitat's dome flying a teal flag of its own | `page_autonomy.dds` |
| Autonomy status tile | `ai_strategy_icons/subject_maintain_autonomy.dds` | the Habitat's dome with a red wax seal on a blue ribbon | `page_aut_status.dds` |
| Defenses tile and module | `building_icons/building_naval_fortification.dds` | a grey armored gun turret on a stepped armored base, on moon rock | `module_def.dds` |
| Integrity tile | `state_status_icons/has_devastation.dds` | the Habitat's dome with a crack down it | `page_integrity.dds` |
| Defense status tile | `state_status_icons/colony.dds` | the Habitat's dome with a radar dish beside it | `page_def_status.dds` |
| Habitat | `building_icons/urban_center.dds` | a dome of blue-tinted panes over a band of lit yellow windows | `module_hab.dds` |
| Spaceport | `building_icons/building_port.dds` | a gold lander on four legs on a grey pad ringed in orange | `module_port.dds` |
| Research Station | `building_icons/building_university.dds` | a silver observatory dome, a brass telescope out of its slot | `module_lab.dds` |
| Cultural Center | `building_icons/building_arts_academy.dds` | two gold theater masks, comedy and tragedy, on an amber glass dome | `module_culture.dds` |
| Training Ground | `building_icons/building_barracks.dds` | a marine in a sand-tan pressure suit leaping, rifle raised | `module_train.dds` |
| Nuclear Command Center | `building_icons/building_nuclear_plant.dds` | a steel blast door in a concrete frame, a yellow radiation sign beside it | `module_bunker.dds` |

Three of the briefs changed in review, because at 24 px they were scenes: the amphitheater under a dome was a ring of steps, so Cultural Center shows the theater masks; the twin turrets on a crater rim were specks on a large rock, so Defenses is one turret; two marines drilling were two specks, so Training Ground is one marine (in sand-tan: the first round's olive armor and orange visor drew Halo's Master Chief). The Habitat is the lighter of its candidates, so the drawn crack shows on Integrity.

## Space Fleets: the fleet cards (2026-11-14)

Each fleet in Space Fleets is a card (`te_sr_fleet_row`; owner, 2026-11-14): its ships by role as a row of icons, its readings as bars, and icons on its posture and order buttons. The seventeen icons are **flat line pictograms, drawn, not painted**: `scripts/image_pipeline/gen_space_fleet_pictograms.py` draws each on a 24-unit grid and writes it at 64 px, cream (`#e9e2cf`, the panel's text) except the gold emblem. They are a first set, so the cards could be judged in game with art of their own (`gui_style_guide.md` rule 10). To paint one, give it an entry in `icon_prompts.py` (category `space`) with the subject below, `write` it under the same file name, and drop its entry from the drawing script; the GUI needs no edit. `FleetCardTest` in `test_space_race_layout.py` holds each cell and button to its file, and the script's `--check` to the files as committed.

| Where | Drawn now | To paint | File |
|---|---|---|---|
| A card's emblem (24 px, in the head's inset box) | a shield with two chevrons, gold | a gold shield badge, two silver chevrons on it, a small star above | `fleet.dds` |
| Warships (24 px, lit with any, 30% with none, as every role) | a hull with a bridge | the Locations warship (`warship.dds`), side on | `role_war.dds` |
| Rapid response | a dart | a slim silver interceptor with swept fins and a long blue exhaust | `role_rapid.dds` |
| Siege ships | a low hull under one long gun | a heavy dark-grey gunship, one oversized cannon along its spine | `role_siege.dds` |
| Assault carriers | a flat deck, a craft lifting off it | a broad flat-decked grey ship, two small landers lifting from it | `role_carrier.dds` |
| Tenders | a tank on a boom | a white spherical propellant tank in a girder frame, a docking boom at one end | `role_tender.dds` |
| Station (20 px, over the posture's word) | a world, a ship on its orbit | a planet with one ship parked on a thin orbit ring | `posture_station.dds` |
| Stand off | a world, a screen held off it | a planet with a line of ships held at a distance, an arc between them | `posture_standoff.dds` |
| Close in | four arrows closing on a world | a planet in a red targeting ring, ships diving at it | `posture_closein.dds` |
| Interdict | a barred lane | a freighter stopped by a red barrier across its lane | `posture_interdict.dds` |
| Go (16 px, left of the order's word, as every order) | an arrow | keep the arrow: an order reads best as a sign | `order_go.dds` |
| Transfer | two arrows passing | keep | `order_transfer.dds` |
| Land (marines) | an arrow down to a line | keep | `order_land.dds` |
| Embark (marines) | an arrow up from a line | keep | `order_embark.dds` |
| Seize | a flag planted | keep | `order_seize.dds` |
| Destroy (in Seize's place while the order is to destroy) | a burst | keep | `order_destroy.dds` |
| The transit track's marker (18 px, on the bar at the share of the leg flown) | a filled dart | keep | `track_ship.dds` |

The roll-up and roll-down buttons at the right of a card's head are vanilla's `generic_icons/up_up.dds` (the module queue's move-up, already kept) and `generic_icons/down_down.dds`, in vanilla's round action button.

## Locations and a card's world (2026-11-14)

Locations is a strip (`te_sr_location_cell`, a column per location from Earth outward; owner, 2026-11-14), and a fleet card's head shows the world of where the fleet is, or is bound. Both take a location's icon from `LOCATION_ICONS` in `scripts/generators/gen_space_fleets.py`: the kind-of-world icons above, by the worlds found there, at 30 px in the strip and 24 px on a card.

| Location | Icon | File |
|---|---|---|
| Earth Orbit | **placeholder**: the Earth-orbit production method's embossed Earth and satellite. To paint: a blue-and-white Earth, a thin gold orbit ring around it; proposed `gfx/interface/icons/space_race_icons/location_earth.dds` | `gfx/interface/icons/production_method_icons/pm_earth_orbit.dds` |
| Mercury & Venus | Venus | `colony_venus.dds` |
| Mars | Mars | `colony_mars.dds` |
| Asteroid Belt | the asteroid | `colony_asteroid.dds` |
| Jupiter | the Jovian moon before its giant | `colony_jovian.dds` |
| Saturn | the Saturnian moon's ringed world | `colony_saturnian.dds` |
| Uranus | the Uranian moon | `colony_uranian.dds` |
| Neptune | the Neptunian moon | `colony_neptunian.dds` |
| Kuiper Belt | the dwarf planet | `colony_dwarf.dds` |

Swapping Earth Orbit's in is one path in `LOCATION_ICONS`, one in `te_sr_fleet_row` and `EARTH_ORBIT_PLACEHOLDER` in `test_space_race_layout.py`.

The strip's captions and statuses are icons with their word on hover (`te_sr_location_captions`, `te_sr_location_cell`). Ours is the card's emblem (`fleet.dds`), the warships on their way the warship (`warship.dds`), and a status of ours wears its posture's sign (`posture_standoff.dds` for Blockading, `posture_interdict.dds` for Interdicting). The rest are drawn by the same script as the cards' (`gen_space_fleet_pictograms.py`):

| Where | Drawn now | To paint | File |
|---|---|---|---|
| The others' line (18 px, left of every other power's strength) | the emblem's shield, bare, in grey | a plain steel shield badge | `fleet_other.dds` |
| Battle (20 px) | the burst, red | two crossed red beams over a small explosion | `status_battle.dds` |
| Blockaded, Earth Blockaded | the Stand off sign, red | keep: the enemy's posture in red | `status_blockaded.dds` |
| Interdicted | the Interdict sign, red | keep | `status_interdicted.dds` |

Space Command's four overview cells use art the panel already has: Space Command's building icon (Built a month), the warship (Fleet strength), the colonist with a wrench (`page_crews.dds`, Upkeep) and the Spaceport's lander on its pad (`module_port.dds`, Reserve). The build mix's five buttons wear the cards' role icons.

## Space Fleets: the banner (2026-11-14, placeholders)

A picture heads Space Fleets (`te_sr_fleet_banner`, 480 × 110, cropped to fit; owner, 2026-11-14): a fleet of the day, chosen by the drive our program flies on (`sr_drive_level`), so it changes as the drives do. **The four are placeholders**: event pictures the mod already ships, standing in until the banners are painted. Each is a literal `texture` line in `te_sr_fleet_banner`; swapping one in is that one path. `FleetBannerTest` in `test_space_race_layout.py` holds each drive to its path.

| Drive (`sr_drive_level`) | Placeholder now | The banner should show | Proposed path |
|---|---|---|---|
| Chemical (0) | `gfx/event_pictures/orbital_arms_race.dds` | a line of stubby white chemical-rocket warships in low orbit, Earth's limb below, exhaust plumes short and bright, the look of a 21st-century space program under arms | `gfx/interface/illustrations/space_race/fleet_banner_chemical.dds` |
| Fusion (1) | `gfx/event_pictures/orbital_battlestation_construction.dds` | long truss-built warships with ring radiators and blue-white fusion exhausts leaving an orbital yard | `gfx/interface/illustrations/space_race/fleet_banner_fusion.dds` |
| Fusion torch (2) | `gfx/event_pictures/interstellar_probe_departure.dds` | a squadron under hard burn, each ship a needle ahead of a long white torch plume, Jupiter small behind them | `gfx/interface/illustrations/space_race/fleet_banner_torch.dds` |
| Antimatter (3) | `gfx/event_pictures/antimatter_propulsion_drive.dds` | sleek dark warships with magnetic nozzles throwing violet-white beams, a ringed planet ahead | `gfx/interface/illustrations/space_race/fleet_banner_antimatter.dds` |

The banners are wide and short (about 4.4 to 1), so each scene keeps its ships in the middle band; a tall composition loses them in the crop.

## Kept as they are

The pie's frame (`gfx/interface/backgrounds/round_frame_dec.dds`) is vanilla's decoration, used as vanilla uses it. So are the Rivals rows' band marker (`gfx/interface/progressbar/progressbar_marker.dds`) and the transparent track under it (`generic_icons/transparent.dds`), drawn as the UN's authority bar draws them. The rows have no icons of their own.
