# Colony management: AI, autonomy, slots, new modules and the panel — design

Drafted 2026-10-30 from the owner's play-test notes on the Colonies section
(screenshot: five lunar colonies, the People view). It changes Solar System
Colonization as built by the slices of
`2026-10-25-solar-colonization-modules-and-bases-design.md` (modules, Extraplanetary
Base room), `2026-10-26-solar-colonization-free-colonies-design.md` (autonomy) and
`2026-10-29-lunar-colonization-design.md`. § 10 is the build order. Simple and Full
Colonies only, as those slices are; Races Only is untouched.

## 1. The owner's notes (2026-10-30)

1. The AI should value its colonies more.
2. The panel should show each colony's mining slots and module slots.
3. How many module slots are there? Could technology, laws or policies change the
   number, or could it be a soft cap whose modules cost more?
4. Next Windows is long and mostly irrelevant (no one sends chemical rockets to
   Neptune); travel times would help; a table.
5. Autonomy's drift is colored as if more were good: down red, up green.
6. Autonomy should have a restoring force (a term proportional to the value), so it
   settles at an equilibrium instead of rising for ever.
7. Each colony in a container, so they read apart.
8. More module types: Extraplanetary Base room, module or fleet construction,
   cultural pull, tourism, science, a covert black site, a training ground, a
   nuclear command center, advanced materials.
9. Click a colony to see everything about it (people, modules, autonomy, defenses)
   on one page.
10. Autonomy could have a good side: an autonomous colony builds its own modules.

## 2. The answers to note 3, as built before this design

- **Specialization levels:** 4 per world (`SPEC_BUDGET`), shared by its two
  specializations. Every world the same.
- **Slots:** 1 to 4 per world by size (`Site.slots`), shared by Habitat, Defences
  and Spaceport (no Spaceport on the Moon). 84 over the 40 worlds: eleven worlds
  have 1, seventeen 2, nine 3, three 4. A hard cap.
- **Mining (Extraplanetary Base room):** 10 to 60 levels per world (`ebase_room`),
  865 in all, plus 10 near Earth with Asteroid Mining.

Both are possible, and this design does both (§ 5): technology adds slots, and past
its slots a world can still take modules at a rising price.

## 3. The AI (note 1)

What made it neglect its colonies: every colony-tending review was gated on
`sr_ai_should_participate` (the top three countries by rank), so a holder outside
the top three sent Low emigration, never queued a module and never fabricated; and
the self-government demand (`space_race_events.94`) gave "let it go" +60 whenever
the programme was not running, which is any idle holder.

- **`sr_ai_tends_colonies`** (new trigger): an AI that holds a colony, or a top-three
  space power. It replaces `sr_ai_should_participate` in the emigration review
  (Steady with a positive weekly income) and the module review.
- **The demand:** a charter is the AI's default for any holder (base 40, +40 while it
  tends colonies); a garrison at war as before; letting go only without a Space
  Program (+60), since then it can't supply the colony at all.
- **Cede Colony's price** (the owner's follow-up, 2026-10-30: "you can buy colonies
  off the AI for cheap"; a colony shouldn't weigh as much as most states, but a
  giver's score should sit between −50 and −200, not −20 to −50). The article's
  `inherent_accept_score` gives the giver −30 for reluctance (was −10) less the
  world's worth, `sr_cede_ai_input_value`: 30 plus 10 a stage (was 20 plus 5), 8 a
  module level past the first (was 5), 1 a 1,000 of its people (new), at most 170.
  So an empty lunar outpost costs −60, an empty Kuiper outpost −110, a built-up
  lunar colony of 25,000 with five levels −125, and a peopled Mars colony with
  eight levels the cap, −200. The receiver gains the same worth (half without a
  programme), as before.
- **New modules:** the AI's plan (§ 7.3) reaches the new types.

## 4. Autonomy (notes 5, 6, 10)

### 4.1 Colors
The drift and every term in its hover use `|=-2` (vanilla's format for devastation:
signed, positive red), not `|+=2`.

### 4.2 The restoring force
The drift gains a term, **settling**: −`sr_aut_settle_rate` (0.01) × autonomy. With
the other terms summing to S, autonomy settles at 100 × S (clamped 0 to 100), about
two thirds of the way there in eight years. So:

| Colony | S | Settles at |
|---|---|---|
| A lunar outpost, 20,000 people | −0.15 | 0 |
| Valles Marineris, 125,000 people, chemical drive | +0.47 | 47 |
| The same, chartered | +0.07 | 7 |
| Pluto, 20,000 people, a year without contact | +0.60 | 60 |
| The same, at war | +0.85 | 85: demands self-government |

A colony demands self-government (75) only under strain, and breaks away (100) only
when S reaches 1. The hover shows the term and where the colony is settling.

### 4.3 A colony builds its own modules
Each held colony that is not occupied gains **self-build points** a month:
autonomy ÷ 100 × people ÷ 10,000 (`sr_aut_selfbuild_per_10k`, 1), at most 5. At 100
(`sr_module_points`) it builds a module itself, installed at once, free, never past
its slots: a Habitat once its people fill three quarters of its room, else a level of
its founding specialization up to 3, else of the other, else a Research Station or a
Cultural Center, whichever it has fewer of (what a self-governing colony wants for
itself; never an Administration). Specialization levels stay within their 4. With nothing it can build, the points wait at 100. A colony at 50
autonomy with 30,000 people builds one about every five and a half years. The record
is `sr_site_self_<key>` (global, so a cession takes it; cleared on release).

## 5. Slots (notes 2, 3)

- **Slots per world** become a script value, `sr_site_slots_<key>`: the table's 1 to
  4, +1 with Advanced Nanofabrication and +1 with Molecular Assemblers (the
  holder's).
- **A soft cap past them** (the owner's default, `CLAUDE.md` § Design defaults): a
  world may take up to 4 modules past its slots; the n-th past costs
  100 × (1 + n) fabrication points (200, 300, 400, 500). The price is the queue
  head's when it is built (`sr_mq_head_cost`), so the stock's cap rises from 200 to
  500. A colony's own builds (§ 4.3) stay within its slots.
- **Specialization levels stay at 4**, a hard cap: their modifiers are large, and the
  slots are where the new types compete.
- **The panel's Modules view** shows each colony's **Slots** (used, counting queue and
  shipments, of its slots; red past them, the next module's price on hover) and its
  **Bases** (Extraplanetary Base room, with its grade on hover).

## 6. Next Windows (note 4)

A table, one row per destination: **Destination**, **Window** (open, in N months,
any month for the Moon and Mercury, or with propellant depots the premium to go now)
and **Transit** (months by our drive this month). A row shows only while the
destination has a world we may target and our drive reaches it within the colony
fleets' 15-year horizon (`sr_cf_horizon_months`); a line under the table counts the
destinations beyond our drive. The Staged in Orbit tooltip filters its lines the same
way.

## 7. New modules (note 8)

### 7.1 The types
Each takes a slot and needs crews (one level a 5,000 people, as the specializations,
Defences and Spaceport). Its effect is per **staffed level**, summed over the colonies
we hold that serve us: occupied never, and blockaded for the types marked *ships*.

| Module | Key | A staffed level gives | Ships |
|---|---|---|---|
| Mining Complex | `mine` | +10 Extraplanetary Base room at its world, at its grade | yes |
| Orbital Yard | `yard` | +4 module fabrication points a month; under Full Colonies +0.5 Space Command strength a month | yes |
| Research Station | `lab` | +2% research speed | no |
| Cultural Center | `culture` | +3% cultural pull, +1% prestige | no |
| Off-World Resort | `resort` | +3% tourism output | yes |
| Black Site | `black` | +1 intelligence capacity, +3% covert operation efficiency | no |
| Training Ground | `train` | +4% army experience gain | no |
| Nuclear Command Center | `bunker` | +4 nuclear command reliability (at most +12) | no |
| Materials Foundry | `foundry` | +3% advanced materials output | yes |
| Administration | `admin` | −0.15 autonomy drift at its world | no |

The country modifiers (`sr_module_<key>`) sit on the entry like its other four, at
`multiplier` = the staffed levels (`sr_mod_units_<key>`), refreshed in
`sr_emig_refresh_modifiers`, removed first. Mining Complex feeds `sr_ebase_room_total`
and the fill; Orbital Yard feeds `sr_mod_fab_rate` and `sr_sc_rate`; the Nuclear Command Center
feeds `nd_reliability_target`; Administration feeds the world's drift.

### 7.2 Codes
Shipments and the scripted GUI's `op` keep 1 to 5 and number the new types 6 to 15
in the table's order, so saves keep their queues and shipments.

### 7.3 The AI
After its Habitat and specialization levels, an AI fills a free slot (never past
it): Administration where autonomy is 50 or more, a Mining Complex where its base
levels exceed its room, a Nuclear Command Center with nuclear weapons, an Orbital Yard with
a Space Command, else a Research Station.

## 8. The panel (notes 7, 9)

- **Cards.** Each colony's row sits in its own framed box.
- **A colony's page.** A colony's name is a button: it shows that colony alone, with
  every view's lines under their own heads (People, Modules, Autonomy, and under Full
  Colonies Defenses), its slots, bases and self-build, and a Back button. The view
  switch leaves it. Client state only (`GetVariableSystem`: `sr_colony_view` =
  `detail`, `sr_colony_focus` = the world's key), as the views are.
- **The Modules view**: Clear beside the name; under it the crew share, Slots and
  Bases, then every module in three lines of cells that label themselves (four
  letters each, the module's hover on the label): I, II, Hab, Port, Def; Mine, Yard,
  Lab, Arts, Tour; Spy, Camp, Nuke, Mat, Gov. The column heads above the rows stay
  for People, Autonomy (with Building, § 4.3) and Defenses.
- **Back** above the rows leaves a colony's page.

## 9. Saves

Nothing is renamed. A world's new levels read 0 while unset; `sr_site_self_<key>`
starts at 0; the slots value reads the table plus technology. The queue's and
shipments' codes 1 to 5 keep their meaning.

## 10. Build order

1. Autonomy colors and settling; the AI (§§ 3, 4.1, 4.2).
2. Next Windows (§ 6).
3. Modules: the slots value, the soft cap, the new types, a colony's own builds,
   the AI's plan (§§ 4.3, 5, 7).
4. The panel: cards, Slots and Bases, the three lines of cells, a colony's page (§ 8).
5. Docs, the player guide, the play-test list.

Not seen in game. The play-test list (`docs/testing/solar-colonies-playtest.md`) gains
the checks only the game can show: a JE-scope `unit_` modifier reaching the army
(Training Ground), the soft cap's price at the queue's head, and the detail page.

## 11. As built (2026-10-30)

Built in #1257, the build order's five steps on one branch. A follow-up (#1258)
finished two of its sections and took the owner's review of the built panel
(2026-10-30):

- **§ 4.1's colors.** The drift hover's conditional lines (`sr_aut_line_*`:
  charter, garrison, war, no contact, a destroyed colony) had kept `|+=2`, so a
  garrison's +0.2 read green. They now read `|=-2` like the rest, and
  `test_space_race_layout.py` holds every figure in the hover to it.
- **§ 5's technologies as markers** (`scripting_best_practices.md` § Technology
  markers). #1257 read `has_technology_researched`, so no technology's tooltip
  mentioned the slot. The technologies carry +1 `country_sr_colony_slots_add`
  each (script-only, "Colony Module Slots"), `sr_site_slots_<key>` adds the
  holder's, and the Slots hover reads its breakdown. The owner added three to
  the design's two: Nuclear Thermal Propulsion, Orbital Manufacturing,
  Advanced Nanofabrication, Space Colonization and Molecular Assemblers, so a
  world has up to 9 slots. Anything else that grants it later, a law or a
  policy, counts the same way.
- **The drives as markers** (the owner): Fusion Power, Muon-Catalyzed Fusion
  Reactors and Antimatter Production carry `country_sr_drive_<fusion|torch|antimatter>_bool`
  (script-only booleans), which `sr_drive_level`, `sr_launch_has_fusion` and
  `sr_launch_has_antimatter` read, so each technology's tooltip names its drive.
  Two self-checks, `drive_marker` and `slot_marker`, read the markers in game.
- **Underlines** (the owner: far too many across the Space Race GUI). Style rule
  3 had every hover's text underlined, enforced by `unmarked_hover_audit`;
  vanilla underlines 1 to 4% of its own text hovers. The rule now follows
  vanilla, the audit is retired, and the Space Race GUI lost its underlines.
- **§ 8, revisited.** A colony's name reads as a button (vanilla's
  `clean_button` and go-to arrow). A colony's page is a body of its own, not
  the list row with every view stacked: sections with their controls beside
  the headings, readings in icon tiles two to a row (`te_sr_page_tile`), and
  the modules one to a line with their full names (`te_sr_page_mod_row`). Its
  icons are kept art or placeholders listed in `space_race_gui_icons.md`.
- **A site before it is settled.** Solar System shows under each site's name
  its slots as ours and its Extraplanetary Base room and grade.
- **The race to the Moon.** Solar System Colonization's reward hover gave the
  first lunar colony's prize with no word of why only the Moon has one. It now
  names the race to the Moon, the old Moon Base milestone's prize and the one
  race among the sites, and the six lunar sites' hovers point to it.

**Where the build fills in what the sections leave open:**

- **Settling's names.** `sr_site_aut_pressure_<key>` is every term but settling;
  `sr_site_aut_drift_<key>` is the pressure less `sr_aut_settle_rate` × the
  autonomy. The hover's last line, "settles near N%", is
  `sr_disp_aut_target_<key>`: the pressure ÷ the rate, 0 to 100.
- **A colony's own builds** are `sr_site_self_rate_<key>` (a month's points),
  `sr_site_self_<key>` (held at `sr_module_points`) and
  `sr_site_self_build_<key>`, which logs `TE_SR_MODULES <key> built a module of
  its own`. Its slots and specialization budget count the holder's queue and
  every shipper's shipments (`sr_mod_slots_used_<key>`,
  `sr_mod_spec_used_<key>`), so it never takes room a queued module is bound
  for. Occupation stops it; a blockade doesn't.
- **The price past the slots** reads the world's built slots and every
  shipper's shipments (`sr_site_generic_pending_<key>`), not queues, at the
  queue's head (`sr_mq_head_cost`), saved into `local_var:sr_mq_head_cost_now`
  before the head leaves. The panel's next price (`sr_mod_next_cost_<key>`)
  counts our queue too. A landing installs up to the slots plus four
  (`sr_site_slots_max_<key>`), the + buttons stop there, and past the slots
  their hover warns of the price (`sr_mod_queue_past_slots_tt`). A
  specialization level always costs 100.
- **Two rates split** so the self-checks still test the buildings alone:
  `sr_mod_fab_rate_method` (the fabrication method; `sr_mod_fab_rate` adds the
  yards) and `sr_sc_rate_buildings` (Space Command; `sr_sc_rate` adds them).
- **The facilities** are `gen_solar_sites.FACILITIES`: the six entry modifiers
  (`sr_module_<key>` at `sr_mod_units_<key>_entry`, read through `owner`,
  refreshed by the generated `sr_mod_refresh_facilities`) and the four hooks of
  § 7.1's table. Their levels count in the module upkeep, as every level past a
  colony's first does. `nuclear_incident_rates.py` reads the Nuclear Command
  Center's term as 0.
- **The AI** stops adding Nuclear Command Centers at three staffed levels
  (`sr_mod_ai_bunker_max`), where the +12 cap is reached, and reads "with a
  Space Command" as a Space Command building in its states.
- **Next Windows** lists 14 destinations (`gen_solar_sites.WINDOW_ORDER`), one
  generated `te_sr_window_row` each, with the premium shown up to +999%.
  `sr_window_reach_<body>` is 1 within the horizon, 2 beyond it (counted under
  the table) and 0 with nothing to target.
- **A colony's page**, as #1257 built it, put each view under a heading and
  its column heads; #1258 replaced that with the page above.

**The owner's calls** (2026-10-30: fine for now):

- **The numbers are a first guess:** settling at 1% a month, a colony's own
  builds (a point a month a 10,000 people at full autonomy, at most 5), the
  price past the slots, the facilities' effects, Administration's −0.15 and the
  cession worth.
- **The demand's odds at war.** With § 3's weights a holder's charter (80)
  outweighs the garrison at war (5 + 60), so at war the AI charters 55% of the
  time and garrisons 45%, where a top-three power used to garrison 56% of the
  time. Every holder gets the +40, since holding a colony is half of
  `sr_ai_tends_colonies`. Raise the garrison's war term if it should stay the
  AI's answer at war.
- **Two AI reviews still read the top three alone** (`sr_ai_should_participate`),
  as § 3 left them: supplying free colonies (`sr_free_ai_review`) and Space
  Command's build cap (`sr_sc_may_build_government`), so under Full Colonies an
  AI holder outside the top three builds no Space Command.
- **A dear module holds the queue.** Fabrication is first in, first out and
  waits for the head's whole price, so the fourth module past a colony's slots
  (500 points) holds everything behind it for up to 100 months at Orbital
  Assembly's 5 points a month, or 20 at Fusion Shipyards' 25.
- **Not seen in game:** the play-test list's § Colony management (twelve
  checks and the `drive_marker` and `slot_marker` self-checks), including
  whether the Training Ground's `unit_` modifier on the entry reaches the army,
  and the fallback if it doesn't.
