# Grand Monuments: buried sites and the archaeology loop — design (MVP)

**Date:** 2026-10-14
**Status:** asked for by the owner on 2026-10-14 ("execute issue 939", reading the design in its comment, skipping the fantasy
finds and their game rule). The same day: "do not reduce max innovation with excavation", and "simplify initially to get an MVP
out. The main goal should be the mechanisms for creating these monuments (not necessarily all the consequences) and at least
some (ideally all) of the monuments themselves. Things like the IG reactions, the PMs, etc. can be deferred." Picks and calls
marked *(design)* are this spec's, open to the owner's review on the PR.
**Builds on:** the landmarks spec (`2026-10-12-grand-monuments-landmarks-design.md`), the trophies spec
(`2026-10-12-grand-monument-trophies-design.md`), the loot spec (`2026-10-12-grand-monument-loot-and-1836-trophies-design.md`)
and several monuments in one state (`2026-10-13-multiple-monuments-per-state-design.md`).
**Issue:** #939. Its comment is a design from a Gemini conversation; this spec keeps its shape and cuts it to what the owner asked
for first (§ Deferred).

## Context

The loot spec left the Pergamon Altar, Priam's Treasure, the Ishtar Gate, Nineveh's reliefs and the rest out of the landmarks of
1836, because they lay buried then. They are uncovered during the game, and then stand as landmarks that can be looted like any
other. This change adds the **buried site**, the **dig** that unearths it, and 35 sites.

## What a site is

A buried site is a LANDMARKS row with `buried=True` (rows 52–86): a landmark that is never seeded at the start and has no owner of
its own. Its owner is whoever digs it. It carries everything a landmark carries (its name, line of history, name in running text,
picture branch, debug line, and for 24 of them the name of the piece a looter would carry off), so once unearthed it is a landmark
in every respect.

Each site is also a **script container** tagged `gm_site`, parentless, in the global list `gm_arch_sites`, made once from the
monthly pass (`gm_arch_seed_sites`, so a save from before this change has them too). It holds the monument it will become under
the records a returned trophy carries (`gm_tr_landmark`, `gm_tr_skin`, `gm_tr_form`, `gm_tr_levels`, `gm_tr_dedication`,
`gm_tr_namesake`, `gm_tr_share`, `gm_tr_origin_region`), so the trophy names, parts and pictures serve it unchanged, and four of
its own:

| Record | Meaning |
|---|---|
| `gm_site_tech`, `gm_site_vector` | what opens it: a technology, and `survey` or `incidental` |
| `gm_site_status` | 1 buried, 2 known, 3 being dug, 4 unearthed |
| `gm_site_sponsor`, `gm_site_method` | who digs it, and how |
| `gm_site_progress` | 0 to 100, kept when a dig is suspended |

The ground is a **state region**, not a state, so a split state that merges (#936) does not lose a site: a dig finds the sponsor's
part of the region each month.

## Discovery

Both vectors need the country that holds the ground to have the site's technology (`gm_arch_has_gate_for`: one branch for
each of the 22 technologies the table uses).

- **Survey.** Open as soon as its owner has the technology: the scholars know where to look (Troy, Mycenae, Knossos, Babylon,
  Nineveh, the Valley of the Kings, Machu Picchu).
- **Incidental.** Nobody knew to look. Each month a site whose ground belongs to a country with the technology has a 1% chance
  (`gm_arch_find_chance`) of being turned up by a plough, a railway cutting or a hiker. The player gets
  *Something Under the Spade* (`arch_events.1`); the AI finds it in its list at its next review.

Several countries may hold parts of one region; any owner with the technology can dig. *(design: the issue's comment makes the
tech gate "any country has it", which would show a site to an owner who cannot dig it.)*

### The sites

The years are the issue's; each site's technology stands for its period. Each has its own picture (codes 1,000,052–1,000,086, drawn
2026-10-16: the site as it stands once dug, a portable find where it was found). All use the To the Nation (civic) dedication until the antiquity and archive dedications exist.

| Key | Name | State | Technology | Vector | Form | Levels |
|---|---|---|---|---|---|---|
| `nineveh_library` | Library of Ashurbanipal (Nineveh, Nimrud) | Mosul | Romanticism | survey | hall | 10 |
| `winged_victory_of_samothrace` | Winged Victory of Samothrace | Western Thrace | Romanticism | survey | statue | 5 |
| `vindolanda_tablets` | Vindolanda | Yorkshire | Empiricism | incidental | hall | 5 |
| `troy_hisarlik` | Troy | Hüdavendigâr | Empiricism | survey | gate | 10 |
| `mycenae_grave_circle` | Mycenae | Peloponnese | Empiricism | survey | mausoleum | 10 |
| `pergamon_altar` | Pergamon Altar | Aydin | Empiricism | survey | pantheon | 10 |
| `deir_el_bahari_cache` | Deir el-Bahari | Upper Egypt | Empiricism | incidental | rock-cut | 5 |
| `ishtar_gate_babylon` | Ishtar Gate of Babylon | Baghdad | Civilizing Mission | survey | gate | 10 |
| `palace_of_knossos` | Palace of Knossos | Crete | Pan-nationalism | survey | hall | 10 |
| `antikythera_mechanism` | Antikythera Mechanism | Peloponnese | Steam Donkey | incidental | statue | 5 |
| `oseberg_ship` | Oseberg Ship | Eastern Norway | Pan-nationalism | incidental | statue | 5 |
| `machu_picchu` | Machu Picchu | Ica | Mass Propaganda | survey | gate | 15 |
| `bust_of_nefertiti` | Bust of Nefertiti (Amarna) | Middle Egypt | Mass Propaganda | survey | statue | 5 |
| `mohenjo_daro` | Mohenjo-daro | Sindh | Modern Materials | incidental | forum | 10 |
| `tomb_of_tutankhamun` | Tomb of Tutankhamun | Upper Egypt | Mass Media | survey | mausoleum | 15 |
| `royal_cemetery_at_ur` | Royal Cemetery at Ur | Basra | Mass Media | survey | mausoleum | 10 |
| `sanxingdui_pits` | Sanxingdui | Sichuan | Public Works Programs | incidental | hall | 10 |
| `sutton_hoo` | Sutton Hoo | East Anglia | Combined Arms | incidental | mausoleum | 5 |
| `lascaux_caves` | Lascaux | Aquitaine | Public Works Programs | incidental | rock-cut | 10 |
| `nag_hammadi_library` | Nag Hammadi Library | Upper Egypt | Nuclear Energy | incidental | stele | 5 |
| `dead_sea_scrolls` | Dead Sea Scrolls | Palestine | Jet Engine Technology | incidental | stele | 10 |
| `tomb_of_pakal` | Temple of the Inscriptions | Chiapas | Television Broadcasting | survey | pyramid | 10 |
| `mawangdui_tombs` | Mawangdui Tombs | Hunan | Modern Pharmaceuticals | incidental | mausoleum | 10 |
| `terracotta_army` | Terracotta Army | Xian | Containerization | incidental | mausoleum | 15 |
| `tomb_of_philip_ii` | Royal Tombs of Vergina | Macedonia | Microprocessor | survey | mausoleum | 10 |
| `tomb_of_marquis_yi` | Tomb of Marquis Yi | Eastern Hubei | Barcodes and Scanners | incidental | hall | 10 |
| `royal_tombs_of_sipan` | Royal Tombs of Sipán | Cajamarca | Personal Computers | incidental | pyramid | 10 |
| `otzi_the_iceman` | Ötzi the Iceman | South Tyrol | World Wide Web | incidental | statue | 5 |
| `caral_supe` | Caral | Lima | Digital Telecommunications | survey | pyramid | 10 |
| `gobekli_tepe` | Göbekli Tepe | Diyarbakir | E-commerce | survey | colonnade | 15 |
| `olympia` | Olympia | Peloponnese | Empiricism | survey | pantheon | 10 |
| `delphi` | Delphi | Attica | Civilizing Mission | survey | stoa | 10 |
| `sidon_necropolis` | Royal Necropolis of Sidon | Lebanon | Empiricism | survey | mausoleum | 5 |
| `villa_of_the_papyri` | Villa of the Papyri (speculative) | Campania | Microprocessor | survey | hall | 10 |
| `tomb_of_alexander` | Tomb of Alexander the Great (speculative) | Lower Egypt | Mainframe Computers | survey | mausoleum | 15 |

Thirty are the comment's historical sites; Olympia, Delphi and Sidon are named in the issue but not in the comment, and the last
two are its speculative finds S3 and S4, which need no parent dig and so are plain sites. *(design)* The states are the comment's,
checked against `map_data/state_regions` (Terracotta Army is in `STATE_XIAN`, there being no Shaanxi). Machu Picchu in Ica, Vindolanda
in Yorkshire and Delphi in Attica cannot be placed more exactly without province names. Where a state already has a monument
(Upper Egypt, Peloponnese, Attica, Aydin, Baghdad, Lebanon), the finished dig stands beside it.

## The dig

A country that holds the ground and has the technology opens a site from the **Archaeological Expeditions** section of the Grand
Monuments journal entry (or the Timeline Extended tab), by one of three methods, each needing its own technology:

| Method | Needs | Progress a month | Weekly innovation | Weekly cost (× base) | Risk and bonus |
|---|---|---|---|---|---|
| Antiquarian and Dynamite | Romanticism | 4% (25 months) | −5 | 1 | 35% chance Stratigraphic Destruction: half the levels (at least 3) |
| Systematic Stratigraphy | Empiricism | 2.5% (40 months) | −15 | 2.5 | the monument whole |
| Forensic and Remote Sensing | Computer Networks | 3.5% (29 months) | −30 | 5 | +2 levels |

There is no slot cap. Two costs bound how many a country can run:

- **Innovation.** Each dig diverts weekly innovation (`gm_arch_diversion`, `country_weekly_innovation_add`). The innovation cap
  is not touched *(owner, 2026-10-14)*.
- **Treasury.** A share of GDP a week, `gdp × 0.0002` with a floor of 100, times the method's multiple (`gm_arch_expense`,
  `country_expenses_add`). It has a category of its own in the Budget Breakdown, Archaeological Digs under Programme Costs
  (`gen_budget_breakdown.py`'s `SOURCES`, which `test_budget_breakdown.py` requires of every recurring monetary modifier).

Both ride on `je:je_grand_monuments` as the trophies' national modifiers do, with the units the pass sums
(`gm_arch_innovation_units`, `gm_arch_cost_units`) as their multipliers.

*(Superseded 2026-10-16: the treasury cost is gone and innovation is the only cost, 5 / 20 / 100 a week by method; see the
rework spec § 1.)*

A dig can be **suspended**; the progress is kept and the site is open again. A dig whose sponsor loses every part of the ground
is suspended the same way, so conquering the state hands the site to the conqueror (with its progress).

### Finishing

At 100% the dig is finished after the monthly walk over the list (a container is not taken off a list inside its own walk). The
site stands in the sponsor's part of the ground through the machinery a trophy's return uses:

- **No monument there:** `gm_state_tr_receive` builds the state's monument from the site's records, as a returning trophy with
  nothing standing is rebuilt (landmark, skin, form, name, civic dedication through `gm_restore_pm`, `gm_seen`); the container is
  then destroyed.
- **A monument there:** the building takes the levels (`gm_state_tr_add_levels`) and the *same container* is retagged
  `gm_monument` and moved to `gm_monuments` and the state's and owner's lists, as a landmark seeded beside another is
  (`gm_arch_stand_beside`).

A player gets *An Excavation Is Finished* (`arch_events.2`), or *Stratigraphic Destruction* (`arch_events.3`). Events cannot reach
a container's custom localization, so the name travels as the country's `gm_arch_last` and `gm_arch_site_name`.

### The AI

Once a month an AI at peace and out of default, with a site open to it and fewer than two digs, begins the grandest one with an
8% chance, by the best method it has (`gm_arch_ai_decide`). The cost and the innovation are its brakes, as for a player.

## What this reuses

Nothing about placing a monument, naming it, looting it or returning it is new: a site that has been dug is a landmark in
`LANDMARKS`, and `gm_tr_landmark_name`, `gm_tr_landmark_desc` and `gm_tr_part_name` already serve its container.

## Deferred

From the issue's design, not built (owner, 2026-10-14: the mechanisms and the monuments first):

- **Foreign digs**: the `archaeological_concession` treaty article, its influence upkeep, the partage split (the host keeps the
  ruin, the sponsor takes the portable masterpiece as a trophy) and the Host's change of heart. Only the holder of the ground digs.
  *(Built by `2026-10-16-grand-monument-archaeology-rework-design.md` § 3, which also replaced the GDP-share cost: digs now cost innovation alone, 5 / 20 / 100 a week, and `gm_arch_expense` is a retired stub.)*
- **Political brakes**: the interest groups' stances, Hard Times backlash (*Gold for the Dead, Crumbs for the Living*), the
  Starved-of-Specialists slowdown.
- **The two dedications** (Ancestral Antiquity, Epigraphic and Prehistoric Archive) and their production methods. Every site is
  To the Nation for now.
- **Speculative breakthroughs** S1, S2, S5, S6, S7 (decipherments, the Amber Room, the Mercury Palace, the Rongorongo tablet) and S8
  (Genghis Khan's tomb); S3 and S4 are sites.
- **Special-site events**: Lascaux's sickness, the dam rescue, the language-reform tie-in; the Ötzi global-warming trigger.
- **The easter eggs** and their game rule, skipped on the owner's instruction.
- **The finds' pictures, drawn ahead (2026-10-16).** S5, S6, S8 and E1–E6 would each place a monument, so each has a
  `gm_picture` subject and a picked seed, rendered and reviewed but not committed: a picture needs its `LANDMARKS` row
  (the registry test ties every `gm_picture` entry to a `PICTURES` code). When a row is added, give its entry this subject
  and seed (the key's form is a guess until then; S6 would be a second picture for the Terracotta Army) and render that seed
  alone. S1, S2 and S7 only grant modifiers.

| Find | Key | Seed | Subject |
|---|---|---|---|
| S8 | `landmark_tomb_of_genghis_khan__mausoleum` | 1 | the sacred mountain Burkhan Khaldun in Mongolia: a broad mountain of dark larch forest rising above a wide grassy steppe valley, on its bare summit stone cairns hung with blue silk scarves, below them on a high meadow an excavated burial precinct of low earthen walls around an opened timber burial chamber, white felt tents and horses on the steppe |
| S5 | `landmark_amber_room__hall` | 2 | the Catherine Palace at Tsarskoye Selo: a very long Baroque palace with a sky-blue facade, white columns and gilded statues of men holding up its upper floor, five gilded onion domes on its chapel at one end, a formal garden in front, the roof cut away over one room whose walls are panelled entirely in carved golden-orange amber and gilded mirrors |
| S6 | `landmark_terracotta_army_mercury_palace__mausoleum` | 1 | the opened burial mound of the First Emperor of China: a great earthen mound planted with trees, cut away to show beneath it an underground palace hall of bronze and black lacquer, a model landscape of rivers and seas of shining silver liquid mercury on its floor, a ceiling painted with stars, rows of grey clay soldiers in trenches outside the mound |
| E1 | `landmark_submerged_citadel__colonnade` | 1 | a submerged ancient citadel on the floor of a shallow turquoise sea beside a rocky volcanic Atlantic island: concentric rings of dressed-stone harbour walls and water channels around a central island of ruined temples and colonnades of red, white and black stone, seen through the clear water, a small research ship anchored above |
| E2 | `landmark_deep_stratum_anomaly__hall` | 1 | a vast open-pit coal mine cut in terraced steps into the earth, giant excavators and floodlights on its benches, in one deep layer of the pit wall a thin glittering seam of black glassy material and silvery lattice fragments exposed under a white scientists' tent |
| E3 | `landmark_polar_monolith__pyramid` | 1 | a deep canyon melted into a vast white ice sheet, at its bottom a huge smooth black stone structure with perfectly straight edges and stepped geometric terraces emerging from the blue ice, a research station of red huts and a white radar dome on the ice above |
| E4 | `landmark_lunar_artifact__stele` | 0 | an excavation pit dug into the grey cratered surface of the Moon beside a small lunar base of white modules, at the bottom of the pit a tall perfectly smooth black rectangular slab standing upright, astronauts in white spacesuits and a lunar lander around it, the blue Earth in the black sky |
| E5 | `landmark_sealed_reliquary__rock_cut` | 0 | a sealed chamber cut deep into the rock beneath a green highland hill, the hillside cut away to show inside a gilded wooden chest with two golden winged figures facing each other on its lid, on a stone platform lit by oil lamps, archaeologists at the narrow entrance tunnel, round thatched houses and terraced fields on the hills |
| E6 | `landmark_sunken_terraces_of_ryukyu__pyramid` | 1 | huge flat stepped rock terraces and straight-sided stone platforms under clear turquoise water at the foot of a green subtropical island cliff, divers swimming over the steps, a small fishing harbour and a lighthouse on the headland |

## Tests, debug, docs

- `test_grand_monument_archaeology.py`: `ARCH_SITES` (technology and vector for each buried row, in `LANDMARKS` order), one
  seeding call per row, a branch per technology in the gate, the dig's rates and the brakes, the placing, the national hooks, the
  scripted GUIs, the events and the panel.
- `test_grand_monument_registry.py`: `Landmark` gains `buried`. `test_grand_monument_trophies.py`: `LANDMARK_PARTS` gains the 24 pieces.
- **Debug:** `event te_debug_monuments.7`. a seeds the sites and turns up every incidental one; b digs the grandest open site by the best
  method; c takes our digs to 99% and runs the pass; d logs the sites.
- **Docs:** `mod_systems.md` § Grand Monuments; the player guide's `02-timeline.md`; `docs/testing/grand-monuments-archaeology-playtest.md`.

## In-game checks

On `docs/testing/grand-monuments-archaeology-playtest.md`.
