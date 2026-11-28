# The Resort Colony as a building of its own: design

Issue #1948. Written 2026-11-21 after the owner's answers to the issue's four
questions and the choice of approach. The Resort Colony
(`pm_space_colony_vacation`) leaves the Extraplanetary Base and becomes the
base method of a new building, the Resort Colony, with room and a draw of its
own at each world. The ground-types design
(`2026-11-05-extraplanetary-base-ground-types-design.md` § 7) already assumes
the method has gone, and this design delivers that.

## 1. Why

From the issue:

- **It works at the mining grade.** A resort level takes base room and works at
  the site's Extraplanetary Base grade, as a mining level does. That makes
  16 Psyche, the richest metal mine (+30%), the best resort, and Titan (−15%) a
  poor one. What draws tourists has nothing to do with ore.
- **The ground types make the mismatch plainer.** The grade now means how rich
  the ground is, and each site's mix of the seven mining goods leaves no place
  for art and tourism.
- **Without it, the base is a pure mine.** The shared basket, the Bases view's
  profit a level and the auto-assign checkbox all read only mining methods, and
  the panel needs no exception for the resort.

## 2. The owner's calls (2026-11-21)

1. **What limits it:** each world's own resort room, plus room from the
   Off-World Resort module (the first option offered, chosen over room that
   follows the colony's people and over room from modules alone).
2. **A world's draw:** a figure set by hand for each world, used as throughput
   the way the grade is, with levels filling the best draw first (chosen over a
   draw from distance alone, and over no draw).
3. **The Off-World Resort module** becomes the resort's facility: each staffed
   level adds resort room at its world, the way a Mining Complex adds base room,
   in place of its +3% tourism output. The building keeps the name Resort
   Colony.
4. **Inputs, era and profit.** In the owner's words: "since we are capping (this
   was originally uncapped, the capping by mining sites was temporary), we can
   probably buff a bit - I'd recommend swapping most (but not all) Advanced
   Materials and some Electronics for luxery good (I'd leave out services - it
   is a local good), and bump the profit per level modestly (e.g. in the low
   40ks)." The era stays Space Colonization.
5. **The approach** (§ 3): "Let's do the twin for now and file an issue when the
   PR is put up, noting that combining (once both PRs are in) may help with
   maintainability in the future."

## 3. Approaches

- **A. A twin of base room (chosen).** The resort gets its own generated fill,
  refresh, pair of country modifiers and build gates, copied from the base's
  pattern but kept separate. It doesn't touch `sr_ebase_fill` or
  `sr_ebase_refresh`, which the ground-types build is rewriting (placement by
  record, the profit checkbox, a blockaded site keeping its levels). So the two
  PRs meet only in the base's method list, the loc, the sites table and the
  Modules view. The cost is about a hundred lines that resemble the base's.
- **B. One shared fill.** Turn the base fill into one generator that serves both
  buildings. Less near-duplicate code, but it rewrites the functions the
  ground-types build is changing, so the PRs would collide. The resort would
  also pick up machinery it has no use for: it makes one basket of goods, so
  best draw first is always the most profitable order, and it needs no
  assignment panel or checkbox.

The owner chose A. When this PR opens, an issue records that merging the two
fills may help maintenance once both PRs have landed (call 5).

## 4. The building

`building_space_resort`, loc **Resort Colony**, on Earth like the base:

- `building_group = bg_exotic`, `city_type = city`, `levels_per_mesh = -1`, the
  base's monuments background, `ownership_type = self`,
  `required_construction = construction_cost_space_mine` (20,000 a level).
- `unlocking_technologies = { space_colonization }`, the method's technology
  today.
- Production method groups: `pmg_base_building_space_resort` (the one method,
  § 5), and the base's three secondary groups, shared rather than copied:
  `pmg_launch_to_orbit_building_space_mine`,
  `pmg_transport_in_space_building_space_mine` and `pmg_maintenance_intensive`.
  The logistics upgrades cut the resort's Launch Capacity bill today, and a
  shared group keeps that. Vanilla shares groups across buildings (for example
  `pmg_canal` across three canals).
- `can_build_government` and `can_build_private`, as the base has (§ 6.4).
- A building icon is needed. My call: make one with the off-repo icon tooling
  and send the owner a review sheet with my pick, as the building-icon batches
  were done. Until the owner picks one, the build may ship a copy of
  `building_tourism_industry.dds` (a sparse worktree can add the copy with
  `git update-index --add --cacheinfo`, as `git_workflow.md` describes).
- Loc: `building_space_resort` and `building_space_resort_desc`, plus a building
  concept if the base has one (the builder checks).

The building has no AI value block, like the base. The engine's own building AI
and private investment decide, within the room gates.

**Companies.** Today every company that lists `building_space_mine` also
covers the resort. My call: **Axiom Space** (`extra_companies_flavored.txt`),
the space-tourism company (prosperity +20% tourism, the Resort Travel prestige
good), adds `building_space_resort` to its `building_types` and keeps
`building_space_mine`. SpaceX, the defence firms that list the base as an
extension (Lockheed Martin, BAE Systems, Roscosmos, Airbus, Dassault) and the
generic aerospace company stay as they are: they launch and mine. They no
longer cover resort levels, a small loss beside giving the tourism company its
building. The company roster tests and audits run on the change.

**The other lists that name the base** take the resort too, for parity:
`te_debris_uses_orbit` (`te_orbital_debris_triggers.txt`),
`is_privately_expandable_building_type` with
`expand_building_private_construction` (`misc_triggers.txt`), `TAIL_BUILDINGS`
in `test_building_list_order.py` (and the definition goes where that test
wants it), the expected list in `test_maintenance_tiers.py`, and
`te_on_building_built` / `te_on_building_expanded` (§ 6.3). Generated lists
that name the base, such as `te_cred_monopoly_ladder_generated.txt`, come from
their generators: rerun them and keep what they write.

## 5. The method

The key stays `pm_space_colony_vacation`, with a new loc name, **Luxury
Resorts** (my call: the building now carries the name Resort Colony). It moves
from `pmg_base_building_space_mine` to `pmg_base_building_space_resort`. Its
icon and crew don't change: 500 shopkeepers, 400 engineers and 100 academics,
unscaled, with `building_job_attractiveness_mult = 5`. Its outputs don't change
either. Its inputs follow call 4:

| Good | Today | New | At base price |
|---|---|---|---|
| Electronic Components | 30 | 15 | 1,200 |
| Wireless Telecommunication Gear | 30 | 30 | 2,400 |
| Digital Access | 10 | 10 | 1,200 |
| Advanced Materials | 2.5 | 0.5 | 2,000 |
| Launch Capacity | 480 | 480 | 96,000 |
| Wine | none | 50 | 2,500 |
| Luxury Furniture | none | 30 | 1,800 |
| Fruit | none | 30 | 900 |
| **Inputs** | £112,000 | | **£108,000** |
| Fine Art (out) | 300 | 300 | 60,000 |
| Tourism (out) | 900 | 900 | 90,000 |
| **Profit a level** | £38,000 | | **£42,000** (38.9% margin) |

*Since 2026-11-25:* the owner found the method still underpowered and doubled its
Tourism, 900 to 1,800 (£180,000), so a level earns £132,000 at base prices
(122% margin). The inputs above are unchanged.

- Four fifths of the Advanced Materials and half the Electronic Components come
  out (£9,200). £5,200 of luxury goods goes in: Wine for the bar, Luxury
  Furniture for the suites and Fruit for the table, each a vanilla `luxury`
  good that is traded, not local. The net, £4,000, is the buff: profit rises
  10.5%, into the low forties as asked.
- `required_input_goods = digital_access` stays.
- The `# Price:` comment lines are `pm_costs` output, rewritten on reload, so
  they need no hand edit. The hand-written note above Regolith Processing
  ("The Extraplanetary Base's five base methods hire a flat crew", line ~17632)
  says four once this one leaves.

## 6. Room and draw

### 6.1 Where the room comes from

The tiers, filled best draw first:

- **Earth orbit:** 10 levels at draw 0 for every country with the building's
  technology. This is the twin of the base's near-Earth room, so a country with
  no colony can still run a few levels without the penalty (the design default
  for soft caps). My call; `ORBIT_RESORT_ROOM = 10`.
- **Each world that serves the country** (`site_serves`: held, not blockaded,
  not occupied, as for bases): its resort room is its row in a new `RESORTS`
  table beside `SITES` (read through `Site.resort_room`, as `SHIPPING` is read,
  so the ground-types build's edits to every `SITES` row don't conflict), plus
  `sr_mod_resort_room` (10) for each staffed Off-World Resort level there (§ 7).
- **Past all of it:** the resort's own `RESORT_OVERFLOW_DRAW`, −75%, set equal
  to the base's `OVERFLOW_GRADE` but kept as its own constant.

**The table's resort room.** As a starting value, each world's resort room is
its room for people in thousands (`room`, 10 to 50): a world that houses more
people can house more guests. That makes 945 levels across the 40 worlds, about
a fifth of base room (4,325), with an average of 24 a world. The figure is
written out, not derived, so a world can be tuned on its own later. It stays
fixed: Habitats and Terraforming raise the room for people but not the room for
guests, and the Off-World Resort module is the way to raise that.

**The module's 10.** A Mining Complex's 50 is about half the average world's
base room (108). Half the average world's resort room (24) is 12, rounded down
to 10. One module level then adds about half a typical world, as it does for
bases.

*Since 2026-11-28:* the owner doubled the resort room from every source: Earth
orbit's room is 20, each world's `RESORTS` room is twice its room for people in
thousands (1,890 levels across the 40 worlds, 20 to 100 a world) and the module
adds 20 a staffed level. The proportions above hold, each figure twice as large.
Against the demand check below, one or two worlds now hold roughly 50 to 200
levels, and all of Mars and the Moon 730, so the market binds sooner. Mars's 100 is three digits, so Solar System's resort cell grew by 9 units to hold
"100 (+25%)", taken from the slots cell, which had room for two digits though a
Habitat cap is 1 to 4.

**Scale against demand** (a rough check, not a fit). In the buy packages
(`00_buy_packages.txt`), a pop at wealth 45 spends £715 a week on tourism per
10,000 working adults. A rich country of 100 million working adults at that
wealth then buys about 71,500 Tourism a week, the output of about 80 resort
levels. A country holding one or two worlds (roughly 25 to 100 levels) can cover
much of its own demand and runs into its room. A country holding all of Mars and
the Moon (365 levels, about 330,000 Tourism) would push down the world price
before its room ran out. So the room binds for most holders and the market binds
for the largest, which seems right.

### 6.2 The draw

A world's draw is how many guests a level there serves: spectacle against the
length of the trip. It acts as throughput, like the grade, so a draw of +30
earns 30% more profit a level at any price. The `RESORTS` table holds it
(`Site.resort_draw`), set by hand. My table, for the owner to review:

| Draw | Worlds | Why |
|---|---|---|
| +30 | Tranquility Base | Apollo 11's landing site, three days from home, Earth overhead |
| +25 | Olympus Mons, Valles Marineris | The tallest volcano and the longest canyon in the solar system |
| +15 | Shackleton Crater, Marius Hills | Near-endless sunlight on the rim, Earth on the horizon; lava tubes to walk through |
| +15 | Venus Cloud Habitat | A city floating in the clouds |
| +15 | Iapetus, Enceladus | The only large moon that sees the rings at an angle; ice geysers under Saturn |
| +10 | Mare Imbrium, Peary Crater | Earth over the grey plains; the north pole's sunlit rim |
| +10 | 4 Vesta | Rheasilvia's central peak, more than twice the height of Everest |
| +10 | Callisto, Titan | Jupiter in the sky outside the radiation belts; flying in thick air over methane lakes |
| +5 | Hellas Planitia, Ceres | The deepest basin and the thickest air on Mars; Occator's bright salt spots |
| +5 | Rhea, Mimas | Saturn filling the sky; Herschel crater |
| 0 | Daedalus Crater | The far side: no Earth in the sky |
| 0 | Utopia Planitia, Arcadia Planitia, 16 Psyche, Europa, Ganymede, Miranda | Plains, bare metal, hard radiation; Verona Rupes, the tallest cliff known, at the edge of the trip |
| −5 | Mercury, 2 Pallas, Io, Amalthea, Triton | The Sun up to three times as large; a dull rock; volcanoes inside the radiation belts; Jupiter close up, inside them; Neptune overhead, years out |
| −10 | 10 Hygiea, Pluto-Charon | A dark rock; the heart's nitrogen plains, Charon overhead, very far out |
| −15 | Himalia, Titania, Oberon, Ariel | Small, dark and far |
| −25 | Proteus, Haumea | A dark rock; a ring and a four-hour day, past Neptune |
| −30 | Eris, Makemake | The edge of the Kuiper Belt |
| −35 | Sedna | Past it |

The draw is a different axis from the grade: Psyche falls from the best base
(+30) to 0, Titan rises from −15 to +10, and the Moon, with grades of 0 to +5,
holds the best resort. A level at its world's draw `D` earns `(1 + D)` times
£42,000 at base prices: £54,600 at Tranquility Base and £27,300 at Sedna.

### 6.3 The refresh

The twin of `sr_ebase_refresh`, in `sr_colony_module_effects.txt`:

- **`sr_resort_refresh`** (country scope). It removes both modifiers first.
  Then, under simple and full colonies (`sr_colonies_contested_enabled`), it
  fills the country's built levels into its room best draw first
  (`sr_resort_fill`, generated in `resort_tiers()` order: `(−draw, 1, index)`,
  with Earth orbit at `(0, 0, 0)`). It stores the average draw as
  `var:sr_resort_draw` and adds `sr_resort_room_bonus` or
  `sr_resort_room_penalty` at its magnitude. It also stores the draw the next
  level would work at, counting queued levels (`sr_resort_next_fill`, into
  `var:sr_resort_next_draw`), for the overview cell.
- **The modifiers** (`space_race_modifiers.txt`): `sr_resort_room_bonus` and
  `sr_resort_room_penalty`, `building_space_resort_throughput_add` ±0.01, with
  the icons the base's pair uses. `building_space_resort_throughput_add` is
  registered in `mod_entity_modifier_types.txt` beside
  `building_space_mine_throughput_add`, with display name
  `$building_space_resort$ [concept_throughput]`. Both modifiers need loc and a
  Nation tab registry line, as the base's pair has (`gen_nation_tab.py`).
- **When it runs:** the monthly country pulse (`space_race_on_actions.txt`,
  where `sr_ebase_refresh` runs) for every country with Space Colonization, and
  the day after a Resort Colony is built or gains a level. For that,
  `te_on_building_built` and `te_on_building_expanded` call
  `sr_resort_hook_fire` for `building_space_resort`. It uses its own pending
  marker and a new hidden event, the twin of `space_race_events.110`, whose
  trigger is `has_technology_researched = space_colonization` with the same
  `# REVIEWED … (delayed_trigger)` reasoning.
- **Values** (`sr_colony_module_values.txt` and the generated values):
  `sr_resort_levels` (levels owned), `sr_resort_queued_levels` (built and
  queued), `sr_resort_room_total`, `sr_site_resort_room_<key>` (the table's
  figure plus `sr_mod_resort_room` × staffed Off-World Resort levels, floored,
  as `sr_site_ebase_room_<key>` adds the Mining Complex's), and
  `sr_mod_resort_room = { value = 10 }`.

### 6.4 The build gates

These are the twins of the base's gates in `sr_colony_module_triggers.txt`:
`sr_resort_has_room` (always true under races only),
`sr_resort_may_build_government` (an AI government builds within the room, a
player's past it) and `sr_resort_may_build_private` (no private investor builds
past the room), with a `sr_resort_room_full_tt` tooltip. Under Races Only the
building is unlimited, gets no modifier, and works at 0, as bases do.

## 7. The Off-World Resort module

- `gen_solar_sites.FACILITIES`: `Facility("resort", "Off-World Resort", "Tour",
  True, False)`. It becomes a hook rather than an entry modifier, as the Mining
  Complex is, and keeps its code (10), its column head and `ships = True`. A
  blockaded world doesn't serve the country, so its room drops out of the fill,
  as base room does.
- The static modifier `sr_module_resort` (+3% tourism output) is deleted. The
  generator stops writing its `scaling_modifiers_while_active` block, and its
  Nation tab registry line goes. Its loc (`sr_module_resort`,
  `sr_module_resort_desc` in `te_concepts_l_english.yml`) goes with it, since
  no hook facility has `sr_module_<key>` loc; the German, Spanish and Russian
  rows go as `i18n/README.md` handles removed keys.
- **The text that promises +3%** is `je_space_race_widget_mod_resort_tt`
  (`te_journal_entries_l_english.yml`) and `sr_mod_queue_resort_tt`
  (`te_miscellaneous_l_english.yml`). Both say +10 Resort Colony room at the
  colony a staffed level instead.
- **Queued only with Space Colonization** (my call). Modules can be fabricated
  from Cislunar Infrastructure (era 10), and today
  `sr_mod_can_queue_resort_<key>` has no technology test, so without a gate a
  player could spend a slot, crews and points on room for a building two eras
  away. The design defaults allow a hard gate for a physical prerequisite, and
  the building is one. The gate follows Terraforming's: a test in the generated
  queue trigger (`has_technology_researched = space_colonization`, or a marker
  bool on the technology as `TERRA_MARKER` is, if its tooltip should show it:
  the builder picks), and its own reason line on the + button. A module built
  in an old save before the technology simply adds room once it arrives.
- **AI** (`sr_mod_ai_plan_<key>`): after the Mining Complex's line, an
  Off-World Resort **once its resort room is full**, built and queued levels
  counted (`sr_resort_queued_levels >= sr_resort_room_total`), with Space
  Colonization. My call. Copying the Mining Complex's test
  (`sr_ebase_levels > sr_ebase_room_total`) would never fire: an AI government
  and every private investor stop at the room, counting queued levels, so built
  levels pass it only when room shrinks. That makes the Mining Complex line
  itself nearly dormant. It is out of scope here and gets its own issue.

## 8. Other throughput on the building

Today the Resort Colony gets everything that raises base throughput, because it
runs on the base. Of the 33 grants of `building_space_mine_throughput_add`:

- **These carry over**, each with a matching line for
  `building_space_resort_throughput_add`, because they belong to the space
  economy as a whole: `sr_commercial_space_dividend` (Commercial Space Industry,
  +5% a point) and `te_orbital_debris` (−0.2% a point, which hits every
  building that launches). The dividend's display value and
  `test_space_race_dividend.py` must account for the second line (the builder
  checks what the test holds).
- **These don't carry over**, because they are about ore: the colony
  specializations (Vesta Mining, Psyche Industrial, Valles Marineris Mining and
  others), the discoveries, `sr_mars_robotic_precursor` and
  `sr_extraplanetary_commercial` (an event's mining option, paired with
  Advanced Materials output).
- **Unchanged:** `sr_space_tourism_boost` and Tranquility Base's Heritage
  specialization already raise Tourism output or the Tourism Industry. Neither
  gains a resort line: the Heritage site already has the best draw, and a second
  bonus would count it twice.

- **The Airport's Spaceport method** (`pm_spaceport`, `extra_pms.txt` ~11601)
  is the 33rd grant: a workforce-scaled state modifier with
  `building_space_mine_throughput_add = 0.01` beside
  `goods_output_tourism_mult = 0.15`. It carries over, with a matching
  `building_space_resort_throughput_add = 0.01`. A spaceport is launch
  infrastructure, and today the resort gets it. Its +15% tourism output an
  Airport level already reaches a Resort Colony in that state and is unchanged.

My calls, all. One observation for the owner, not a change here: in a state
with a large Airport on Spaceport, that tourism output bonus (+150% at ten
levels) outweighs the whole draw range (−35 to +30). So where on Earth a player
builds the Resort Colony can matter more than where in space its levels work.
That is true today for the resort on the base and for the Tourism Industry.
Whether it wants a cap is a question for its own issue.

## 9. What the player sees

- **Overview** (`space_race_widget.gui`): a **Resort Room** cell in the Base
  Room row, beside Base Room, shown with Space Colonization
  (`sr_disp_resort_shown`). It shows levels built and queued against room, red
  past it, and on its third line the draw of the next level. It is the twin of
  `te_banking_ov_cell` for Base Room, with its `_split`, `_past` and `_next`
  display values, and its hover gives the average draw now and the rule. The
  icon is the building's.
- **The Modules view:** each colony's page shows its resort room and draw in a
  Resort Room tile beside Base Room (`module_resorts` and `module_draw` blocks,
  overridden in the generated rows). The colony list row has no width left for
  them (built: staffing, slots and bases fill it). The summary adds "Resort
  Colony levels / room" under base levels / room, and a queued-levels row while
  there are any. The ground-types build is redoing the base cells, so whichever
  PR lands second merges by hand.
- **Solar System:** each site's line gives its resort room and draw after its
  base room and grade (`site_resorts`), so a player can weigh a world before
  founding a colony there.
- **The building:** its throughput breakdown shows the room bonus or penalty by
  name, and the can-build tooltip says when the room is full.
- **Player guide** (call: update in the same PR):
  - `02-timeline.md`: drop the Resort Colony from the base's paragraph. A
    sentence where the era-12 buildings sit gives the Resort Colony, its room and
    its draw.
  - `16-space.md`: the Off-World Resort row (+10 Resort Colony room at the
    colony); a short **Resort Colony room** subsection after Extraplanetary Base
    room, with the tiers, the −75% past the room and the draw table in brief
    (the few best and worst worlds, not all 40); the overview cell's row; the
    Modules view and Solar System rows.
  - `17-reference.md` or an appendix, if it lists buildings or modules.
  - Rebuild the PDF and commit it with the chapters.
- **Docs:** `docs/systems/mod_systems/space_race.md` gets a "Resort Colony
  room" bullet in its modules section, and its facility list updates the
  Off-World Resort.

## 10. Leaving the base

- `pmg_base_building_space_mine` loses `pm_space_colony_vacation`. Its comment
  stays correct.
- **Old saves:** no repair. 1.15 already breaks saves (owner's standing rule).
  What the engine does with a base whose method no longer exists is unverified
  (it most likely picks a method of the group). A play-test item records it.
- **The ground-types build:** its § 7 assumption now holds. It is building in
  `feature/ebase-ground-types`. The files both touch are `extra_pms.txt`,
  `extra_pm_groups.txt` (the base group's list), `gen_solar_sites.py` (the
  `Site` fields and the generated Modules-view cells), the space race widget,
  `te_production_methods_l_english.yml` and `docs/data/balance_snapshot.json`.
  Whichever lands second merges.

## 11. Tests and checks

- `test_solar_sites.py`: every site has a `resort_room` and a `resort_draw`;
  `resort_room` matches `room` for now (a test that says so, so a later tune
  updates it on purpose); the draw is a multiple of 5 within [−35, +30]; the
  generated fill has one tier per world plus Earth orbit, in the order
  `resort_tiers()` gives; `sr_mod_resort_room` is 10; and
  `RESORT_OVERFLOW_DRAW` is −75.
- A method test (beside the base methods' in `test_deep_sea_rebalance.py`, or a
  new `test_resort_colony.py`): profit £42,000 a level and inputs £108,000 at
  base prices, no service and no local good among the inputs added by this
  change (Digital Access, local, stays as the required input), and Advanced
  Materials at a fifth of today's (0.5).
- A building test: `building_space_resort` has the four groups, Space
  Colonization, and both room gates; `pmg_base_building_space_mine` holds only
  the four mining methods; Axiom Space lists the building.
- `test_solar_sites.py` or its kin: the Off-World Resort's queue trigger
  requires Space Colonization at every world, and the AI plan's resort line
  reads queued levels against the room.
- The audits through `scripts/preflight.py`, in particular
  `modifier_field_audit` (the new throughput type), `loc_coverage_audit`,
  `script_argument_audit`, `delayed_event_trigger_audit` (the new hook event),
  `test_nation_tab.py`, `check_gui_lint.py` and `gui_reference_audit.py`.
- Regenerate: `gen_solar_sites.py`, `gen_nation_tab.py`, `organize_loc.py`, the
  balance snapshot, and the player guide PDF.

## 12. In game: the play-test list

No new engine fact rests on this, so it needs no self-check: a building type's
`building_<type>_throughput_add` works for the base, and the fill is the base's.
Items for `docs/testing/solar-colonies-playtest.md`:

- The Resort Colony appears with Space Colonization, builds within the room, and
  refuses an AI government or a private investor past it.
- With Tranquility Base held and its room filled, the building's throughput
  breakdown shows the room bonus at the average draw. A level past the room
  pulls the average toward −75%.
- A staffed Off-World Resort level raises the colony's resort room by 10 within
  a month, and the overview cell and Modules view show it. Before Space
  Colonization, its + button is greyed with the reason line.
- A base still on the Resort Colony in an old save (if one is at hand): note
  which method the engine gives it and that nothing in the log points at the
  missing method.

## 13. Not in scope

- Merging the two fills (the follow-up issue, call 5).
- Any change to the base, its grades, its room or its methods beyond removing
  this one method. The dormant Mining Complex AI line (§ 7) gets its own issue.
- The Airport's tourism bonus against the draw (§ 8).
- Tourism-industry changes on Earth.
- More resort methods (an era-11 hotel was offered and not chosen).

## 14. Left to the builder

- Exact loc wording, following `docs/guides/loc_style_guide.md`; the module's
  new description and the cell hovers in particular.
- Which hand-written per-site hovers, if any, should mention the draw. The 40
  `je_space_race_widget_bases_tt_<site>` hovers are about bases. My lean: leave
  them, and let the Solar System line's figures speak.
- Where exactly the Resort Room cell and the Modules-view figures fit, within
  `gui_style_guide.md`.
