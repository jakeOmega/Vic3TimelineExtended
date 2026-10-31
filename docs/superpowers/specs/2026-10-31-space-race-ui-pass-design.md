# Space Race UI pass: scoping and design (2026-10-31)

The owner's review of the Solar System Colonization panel on 2026-10-31 asked for a
batch of interface and balance changes. The quick ones shipped in PR #1274: the
post-setback cooldown (the "Shielded" state) is gone, self-government is demanded
at 50, each colony shows its base grade beside Bases, the module queue has its own
box, and Solar System sits near the bottom. This document covers the rest, in the
order they should be built.

System reference: `docs/systems/mod_systems/space_race.md`. Panel house style:
`docs/guides/gui_style_guide.md`. GUI mechanics: `docs/guides/gui_modding_guide.md`.

## 1. Why

- **The panel is cramped.** Everything lives in a journal entry's quarter of the
  screen, so choices are made with step-through buttons, and the information a
  choice needs sits in a different section from the button that makes it. The
  owner: "a lot of the difficulty is in compressing the UI into ~a quarter of the
  screen."
- **A few settings reward switching off and back on.** The cooldown did; the
  Space Command method still does (§ 10). The design default (CLAUDE.md, "Avoid
  micromanagement") is that a limit should not reward toggling.
- **The panel is getting large to maintain.** `space_race_widget.gui` is 7,600
  lines, and a dozen systems each define their own section header, subheader,
  note, value row, panel and overview cell. The owner asked for reusable widgets
  (§ 13).

**Success:** a player picks a fleet's destination, a colony fleet's target or a
split of a fleet in one popup that shows what each choice costs and why one is
unavailable. The Solar Colonization panel fits on one screen per task. No setting
is worth flipping back and forth.

**Anti-goals:**
- New mechanics beyond the upkeep fix (§ 10). This is an interface pass.
- A picker that hides a rule. Every greyed option says why.
- Losing the JE panel's fallback. Everything must still work in the journal
  entry and in the Timeline Extended window's Space Race tab, which share one
  set of types.

## 2. Decided by the owner (2026-10-31)

| Item | Decision |
|---|---|
| Pickers | A popup in the middle of the screen, our own window opened and closed the same way as the Timeline Extended window; closes on Escape or a click outside. Goes on the play-test list. |
| Shielded | Removed with the cooldown (option a). Shipped in #1274. |
| Base cell's lag | Up to a month out of date is acceptable; a refresh when construction finishes would be nice (§ 8). |
| Posture and targets | A row of buttons like the approach selector instead of step-through buttons. |
| Less scrolling | Tabs at the top of the panel are good; a full-page window, like the Census Data window's Demographics tab, would also be fine (§ 11). |
| Solar system schematic | Wanted eventually, not a priority (§ 12). |
| Earth alert | Wanted (§ 9). |
| Order | Quick changes PR first (#1274), then this scoping doc, then the pieces. |
| Fleet upkeep | On a maintenance line no yard method changes (the owner's idea), spread over six goods: electronic components, wired and wireless telecom gear, software, robotics and chemicals (§ 10). |
| No Space Command | Fleets can't move without one (§ 10). |
| Detach | Also into an existing fleet at the same location, so it becomes Transfer and takes in Merge (§ 6). |
| Colony AI | Plans an Administration from autonomy 25 while heading for 45 or more. Shipped in #1274. |

## 3. The popup shell (shared)

**What:** one reusable centred popup that every picker below instances. It is the
first piece of the widget library (§ 13).

**Shape,** from vanilla's `gui/principle_selection_window.gui:1-20` (the mod
already overrides that file):
- A scripted widget in `gui/scripted_widgets/`, gated as
  `te_systems_window.gui:1133-1136` is (played country valid, not observing) and
  on its open key.
- A full-size `window` on `layer = popups` (above the journal and side panels)
  with vanilla's `Background_Full_Dim` backdrop.
- A full-size transparent button behind the body that clears the open key: the
  click-outside close.
- The centred body with `alwaystransparent = no`, so clicks on it don't fall
  through, and a header whose close button carries `shortcut = "close_window"`
  (Escape).
- The body is a type with blocks for the title, a list area (a scrollarea of
  rows) and an optional footer (a Confirm button for § 6).

**State:** the open key is a client-side `GetVariableSystem` value
(`te_popup` = `<picker>_<slot>`), set by the button that opens it. Client-side
means per player and per session, which is right for an open popup. The popup
reads the player's country through `GetPlayer` (it has no `JournalEntry`), so its
scripted GUIs root on `GuiScope.SetRoot( GetPlayer.MakeScope )`, as the Timeline
Extended window's do.

**Which fleet slot the popup is for.** The panel's rows pass their slot as a
literal (`AddScope( 'op', MakeScopeValue( '(CFixedPoint)N' ) )`). A popup has no
row, and nothing in the mod or vanilla reads a `GetVariableSystem` value back as
a number. So the popup body is **generated once per slot** (nine bodies, one
visible, `GetVariableSystem.HasValue( 'te_popup', 'sr_dest_<n>' )`), by
`gen_space_fleets.py` next to the slot rows it already generates. Each body's
rows pass both the slot and the choice: `AddScope( 'op', … ).AddScope( 'pick', … )`.
Chained `AddScope` is proven in this mod (`colonial_empire_widget.gui:820`).
The other route, a country variable set by the opening click, is game state
synced to every player, and it runs into the same-click gotcha
(`gui_modding_guide.md:1408`): the popup would open on the previous slot.

**Untested in game (play-test list):**
- `layer = popups` drawing over the journal panel and over the Timeline Extended
  window.
- Escape closing the popup.
- The popup staying put while the panel behind it scrolls.
- **Fallback:** the same body drawn inline in the panel, opening under the row
  that opened it.

**Doc fix on the way:** `gui_modding_guide.md` (lines 60 and 591) says
`default_popup` is in `gui/shared/defaults.gui`. It is in `gui/block_windows.gui:97`.

## 4. Fleet destination picker

**Replaces:** the step-through destination button and Go on a fleet's row, in
Space Fleets (`te_sr_fleet_row`, the `fl_pick_button` block, `sr_fleet_pick_sgui`).

**The popup:**
- **Title:** the fleet: where it is, its strength, delta-v and supply.
- **Rows:** one per location (`gen_launch_windows.LOCATIONS`, nine: Earth, the
  inner planets, Mars, the asteroids, Jupiter, Saturn, Uranus, Neptune and the
  Kuiper belt). Each row shows:
  - the leg's months;
  - the delta-v the leg needs against what the fleet carries;
  - whether the launch window is open, or the months until it opens;
  - our colonies there, and the strongest hostile strength there and inbound
    (from the location records `sr_loc_*`).
- **Click:** sets the destination: a new scripted GUI, `sr_fleet_set_dest_sgui`,
  with `scope:op` the slot and `scope:pick` the location. **Go stays on the row**
  (my call: the owner asked for a destination selector, and a fleet often picks
  now and leaves later, once it has refitted or its window has opened).
- **Picking is open wherever today's step is** (the fleet at a location, the
  pick not its own location). A row that the fleet couldn't leave for this month
  still shows, with **why** as information: short of delta-v for the leg,
  refitting, below the minimum strength, or Earth's launch bar
  (`sr_fl_<n>_may_depart_<loc>`'s terms). Go keeps the gate, as `can_go` does now.
- **A closed window is never a gate.** It only raises a leg's delta-v (fleets
  design § 6), so it shows inside the delta-v figure. The window column
  ("open", or months to the next) exists only for legs out of Earth
  (`sr_window_months_to_next_<body>`); other legs leave it blank (my call: no new
  generated values for cycle and fixed legs).

**Script:** a new scripted GUI with a `possible` of "at a location, not this
one", and the rows' reasons from the per-slot, per-location triggers that
already exist. The step-through `sr_fl_dest_pick_<n>` stays for the AI and the
console until nothing uses it.

## 5. Colony target picker

**Replaces:** the target buttons on Solar System's rows (`site_target_button`,
`sr_colony_target_sgui`). Solar System becomes a list to read.

**Opens from:** Colony Fleets' target line ("Target: Mars — Valles Marineris",
with Change and Clear). Mission Control is the alternative the owner offered;
Colony Fleets is where the target already shows.

**The popup:**
- **Rows:** the sites the program can target now, grouped under their
  locations. Each row shows:
  - slots and base room with grade (the second line Solar System already draws);
  - the launch window;
  - whether another power has claimed it, or has a fleet inbound.
- **A toggle** for every site, the claimed and unreachable ones greyed with the
  reason (as Solar System's "show every world" toggle works now).

**Script:** none new. The site's `sr_colony_target_sgui` call moves into the
popup's generated rows (`gen_solar_sites.py`). There is one target, not one per
slot, so this popup needs one body.

## 6. Transfer: choose how much of each role, and where it goes

**Today:** `sr_fl_detach` moves half of every role, and half the marines, into
the lowest empty slot.

**The popup:**
- **One row per role** (warships, rapid, siege, carriers, tenders) and marines,
  each with its current strength and five share buttons: none, ¼, ½, ¾, all.
  The default is ½, today's behavior.
- **Where it goes (owner, 2026-10-31: Detach also into an existing fleet):** a
  row of buttons above the shares: a new fleet (the lowest empty slot, today's
  Detach), or each of our other fleets at the same location. With another fleet
  chosen it is a transfer, and "all" on every row is today's Merge, so the
  popup replaces both buttons. Merging into a fleet keeps today's merge rules
  for the drive, the refit and the delta-v and supply shares (`sr_fl_merge`).
- **A footer:** what each fleet would carry afterwards, and Transfer.

**State:** a typed number can't reach script (only base-game rename popups take
text, `gui_modding_guide.md:1380`), and a `GetVariableSystem` value can't be
read back as a number. So the shares are **country variables**,
`sr_det_share_<role>`, set by a scripted GUI per button (`scope:op` the slot,
`scope:pick` role × 10 + share). Transfer applies them, and opening the popup
resets them to ½. They are game state, so a share click is a command, as every
fleet order already is.

**Script:** one generated transfer, `sr_fl_transfer = { N M }`, takes a share per
role in place of 0.5, for each role's `_<role>` and `_<role>_full`, and for the
marines. M is an empty slot (it then takes N's location, posture and drive, as
`sr_fl_detach` does) or a fleet at N's location (the shares then follow
`sr_fl_merge`'s weighting). The target is a fifth `scope:pick` range. All of N
into another fleet clears N, as Merge does. Refused, with the reason in
Transfer's tooltip (my call): a transfer that moves nothing, one that leaves N or
the new fleet below `sr_fl_minimum_strength` (all of N into an existing fleet
excepted), and one that leaves marines in a fleet with no room to carry them.
The AI keeps calling `sr_fl_detach` and `sr_fl_merge`, now thin wrappers.

## 7. Posture and target rows

**Replaces:** the step-through posture, target and interdiction-target buttons
on a fleet's row (6b, 6c).

- **Posture:** a row of three or four buttons in the approach selector's shape
  (`te_sr_action_button`). The choices are Station, Stand off, Close in and, where
  offered, Interdict, under Earth's own rules (lunar colonization design § 8:
  Close in at Earth only against a lunar world).
  The current one is lit. Each is enabled where its step allows it today, with the
  reason when it isn't. Setting a posture directly keeps everything the step's
  effect does on the way (my call): Close in picks a target, and the free-colony
  and interdiction prices are charged as now.
- **Target and interdiction target:** a world list, so they open the popup shell
  (§ 3) with the worlds at the fleet's location.

**Width:** the fleet row is already 478 of 480, so the posture buttons go on a
second line under the orders while the fleet is at a location.
`test_space_race_labels.py` holds the cells.

## 8. Extraplanetary Base cell (the parallel to Seabed's Long-haul)

**What:** a box in the colonization overview, beside the existing Modules box,
in the overview cell shape (`te_banking_ov_cell`, as Seabed's Long-haul cell).
It holds:
- **Caption:** Extraplanetary Bases.
- **Word:** levels and queued levels against the room, "120 (+20) / 400", red
  once past the room.
- **Figure:** "next at +5%", the grade the next level would work at. A level
  past all the room works at −75%.
- **Hover:** the average throughput now (`sr_disp_ebase_grade`), the room by
  colony, and the rule that levels fill the best room first.

**Freshness:**
- **Live, no refresh needed:** built levels (`sr_ebase_levels`), queued levels
  (`sr_ebase_queued_levels`, through `level_after_queued_constructions`) and the
  room (`sr_ebase_room_total`). The cell reads them through `ScriptValue`. Each
  is a loop over the country's buildings, and per-frame cost is unmeasured, so
  measure with the panel open and fall back to the refresh's copy if it
  stutters.
- **From the refresh:** the average grade, and the next level's grade, a new
  variable `sr_ebase_next_grade`: the grade of the first room left unfilled once
  built **and queued** levels have filled the best room (my call, so "next at"
  doesn't overstate while levels are queued), or −75% past all the room. The
  refresh runs the fill a second time with the queued levels for it.
- **The owner's refresh on construction:**
  - The engine has no on_action for queuing a construction.
  - `on_start_expanding_building` fires when work starts. It changes nothing the
    refresh reads, which counts built levels only.
  - The completion hooks are `on_building_built` and `on_building_expanded`, both
    rooted at the building. Since the refresh applies a modifier with a
    `multiplier`, which resolves against ROOT, the hook fires a hidden country
    event on the owner (`limit = { is_building_type = building_space_mine }`,
    `owner = { trigger_event = … }`), whose `immediate` runs `sr_ebase_refresh`
    (the pattern in `scripting_best_practices.md:523-531`).
  - The monthly pulse stays as the backstop. `on_building_built` has missed
    levels that finished on the same day (`scripting_best_practices.md:1551`).
  - Self-check line: `TE_SELF_CHECK OK|BROKEN ebase_on_complete` with the levels
    before and after.

**Also in the Modules view:** the Extraplanetary Base row gains "(+20 queued)".

## 9. Earth alert

**Today:** a fleet bound for a location where an enemy player holds a colony
fires `space_race_events.100` once, at departure. For Earth it never fires, **by
design**: the generator writes `sr_loc_held_earth = { always = no }` "since a
fleet bound for Earth is nearly always one coming home" (`gen_space_fleets.py:597-600`).
Every power's home is Earth, so a hostile fleet returning to refit looks the same
as one coming to blockade. Nothing in the panel warns of either. The inbound
counts (`sr_loc_inbound_<loc>`) include our own and allied fleets.

An alert on every hostile fleet bound for Earth would fire on every homecoming,
so it fires only when an arrival would **change something** (recommended; the
owner's call, § 15): we have no fleet at Earth to meet it, or what is inbound
outmatches our strength there.

**What:**
- **A warning cell in the overview** while an arrival would change something:
  "Hostile fleet: Earth in N mo", with its strength against ours there. The
  hover lists each hostile fleet bound for Earth with its owner, including the
  ones that don't light the cell.
- **A notice when the cell first lights** for a fleet leg (it sets out, a war
  starts while it is in flight, or our own fleet leaves Earth), for a player with
  a Space Program or a fleet. Once per leg, on the pattern of
  `sr_earth_notice_step` (`sr_earth_orbit_effects.txt:192-240`) with a noted
  marker.
- **This notice replaces `.100`'s Earth arm.** `sr_loc_held_earth` stays
  `always = no`, so a lunar colony's holder hears once, not twice.

**Script:** a generated value per location for the hostile inbound (the earliest
landing month and the strength, over the hostile powers' nine slots), in
`gen_space_fleets.py`. The trigger is
`any_in_global_list = { variable = sr_fleet_powers has_war_with = prev sr_fl_any_bound = { CODE = 1 } }`.

**Delivery (owner's call, § 15):** either a popup event with one option and an
image, like the blockade notice `space_race_events.106`, or an optionless
`post_notification`, like Seabed's, the UN's and covert's notices. Recommend
`post_notification`: it doesn't stop play for a warning the cell repeats.

## 10. Fleet upkeep and the Space Command method

**The problem (owner, 2026-10-31):** "the maintenance for your fleet increases
with the Space Command PM. Right now, if you are not building up your fleet, it
makes sense to swap it to the cheapest."

Upkeep is `sr_fleet_upkeep_goods`: +1% of Space Command's Launch Capacity,
Advanced Materials and electricity inputs per 10 points of fleet strength
(`sr_fl_upkeep_apply`). This follows the owner's rule in the fleets design
(§ 5): upkeep is an input multiplier on the building that does the work. The
methods' inputs per level are:

| Method | Launch Capacity | Advanced Materials | electricity |
|---|---|---|---|
| Orbital Shipyards | 500 | 10 | – |
| Fusion Yards | 600 | 15 | – |
| Torch Yards | 600 | 15 | 200 |
| Antimatter Yards | 700 | 20 | 400 |

So the same fleet costs more to keep under a better yard. A player not building
switches down, and switches back up when building. The inputs are also
`workforce_scaled`, per level, so upkeep grows with Space Command's size too:
downsizing to one level after the fleet is built cuts its upkeep in proportion.

**Recommended (owner's idea, 2026-10-31): upkeep on goods the methods don't
change.** None of Space Command's inputs stays the same across its methods today,
so this adds one.
- **The maintenance line:** every yard method carries an identical maintenance
  input, in `unscaled`, of six goods no method otherwise uses (owner,
  2026-10-31): Electronic Components (`electronic_components`), Wired and
  Wireless Telecommunication Gear (`telephones`, `radios`), Software
  (`digital_assets`), Robotics (`robotics`) and Chemicals (`fertilizer`). Spread
  over six goods, one shortage or glut can't make the upkeep very cheap or very
  dear.
- **Upkeep:** `sr_fleet_upkeep_goods` multiplies only those six, each by the same
  k, at `multiplier = units` as now. Launch Capacity, Advanced Materials and
  electricity drop out of upkeep.
- **What it fixes:** upkeep stops depending on the method, so there's nothing to
  gain by switching. It also stops depending on Space Command's levels, since
  `unscaled` goods lines aren't multiplied by level
  (`scripting_best_practices.md:1686-1696`).
- **Balancing:** upkeep for a fleet of strength S is base × k × S ÷ 10 a week,
  one figure set in one place, where k is the multiplier per unit.
- **Size (proposed, the owner's call):** today a unit (10 strength) costs, at full
  staff and per Space Command level, 1% of the method's inputs: 1,400 a week
  under Orbital Shipyards, 1,800 under Fusion Yards, 2,320 under Antimatter Yards
  (Launch Capacity 200, Advanced Materials 4,000, electricity 30). Match **four
  levels of Fusion Yards**, the AI's cap with two colonies (`sr_sc_ai_cap`):
  7,200 a week a unit. The base, about equal in value across the six at their
  base prices, is 840 a week:

  | Good | Base a week | Price | Value |
  |---|---|---|---|
  | Electronic Components | 2 | 80 | 160 |
  | Wired Telecommunication Gear | 2 | 70 | 140 |
  | Wireless Telecommunication Gear | 2 | 80 | 160 |
  | Software | 1 | 100 | 100 |
  | Robotics | 2 | 80 | 160 |
  | Chemicals | 4 | 30 | 120 |

  With k **+900%** a unit, a unit costs 7,560 a week, and a fleet of 300 about
  227,000, wherever it is built. The base itself is a new running cost on every
  Space Command, fleet or not. The building's tooltip shows the upkeep as a large
  percentage on small lines ("+2,700%" for a fleet of 300), so the upkeep's hover
  in the panel gives the goods a week.
- **What stays:** a goods line still runs at the building's occupancy, so an
  understaffed Space Command pays less. A country with no Space Command pays
  nothing, but its fleets can't move (below).
- **Engine work:**
  - A mod-defined good's `goods_input_<good>_mult` needs registering
    (`scripting_best_practices.md:292`). `electronic_components` and `fertilizer`
    have theirs (`mod_entity_modifier_types.txt`); `telephones`, `radios`,
    `digital_assets` and `robotics` don't yet. Validate all six with
    `/modifier-search` after the reload.
  - No method read and no refresh on a method change.
  - A self-check line compares the line's input with base × (1 + k × units) a
    week after the change.

**The other options, kept for the record:**
1. **Normalize the multiplier by the method.** Each good's upkeep
   multiplier is scaled so that a unit of fleet costs what it would under Orbital
   Shipyards: Launch Capacity × 500 ÷ the method's, Advanced Materials × 10 ÷ the
   method's. Electricity is dropped from upkeep, since the cheapest method uses
   none.
   - Keeps the owner's rule (an input multiplier on the building) and uses only
     the good-specific multipliers already proven in game.
   - Needs the method read in building scope (`has_active_production_method`),
     and three static modifiers in place of one.
   - Refreshed monthly, plus from `on_production_method_changed` through the
     same hidden-event dispatch as § 8, so a switch never changes the upkeep for
     a month.
2. **Flat upkeep:** `goods_input_launch_capacity_add` and
   `goods_input_advanced_materials_add` on the building at multiplier = units.
   It reads more simply ("+50 Launch Capacity a 10 strength"). Whether a static
   modifier's input add on a building scales with its levels or staffing is an
   untested engine question. It would need a probe like the 6a `upkeep_inputs`
   one, with option 1 as the fallback.
3. **Better yards make upkeep cheaper.** Normalize as in option 1, then cut 10%
   per method above Orbital Shipyards. A reason to keep the better method, but
   it's a balance change, so it's the owner's call.

**No Space Command, no departures (owner, 2026-10-31: "disable moving fleets").**
The upkeep sits on Space Command, so a country that demolishes it after building
its fleet would keep that fleet for nothing.
- **The rule:** with no Space Command level in a state it controls
  (`sr_state_held_by_owner`), a country's fleets can't depart. A new trigger,
  `sr_sc_operational`, joins every `sr_fl_<n>_may_depart_<loc>`. Downsizing to one
  level no longer helps either, since the maintenance line is `unscaled`.
- **What still runs:** fleets in transit finish their leg; fleets fight where they
  are, change posture, and refit and refill under today's rules (my call: only
  movement stops, as asked).
- **Seen by the player:** the destination popup's rows and Go give the reason, and
  Space Fleets says so once above its rows (style guide rule 6). The AI follows,
  since it reads the same triggers.
- **Occupation:** an occupied Space Command's state also stops departures, which
  matches construction already stopping there (§ 5.1 of the fleets design).

## 11. Less scrolling: tabs now, a full-page window later

**Tabs (next).** A tab row at the top of the colonization status, in the
Colonies view switch's shape (`te_sr_colony_view_button`, a `GetVariableSystem`
key):

| Tab | Holds |
|---|---|
| Mission Control | Today's top block: approach, funding, setbacks, Rivals |
| Fleets | Colony Fleets, and under Full Colonies Space Command and Space Fleets |
| Colonies | Colonies |
| Solar System | Solar System, then How Solar Colonization Works |

The default tab is Mission Control. The overview stays above the tabs. This works
in both hosts with no new engine ground. The key is client-side, so the tab is
remembered per session.

**A full-page window (later, its own project).** What it takes, from the 2026-10-31
research:
- **How the Census Data window got its tab:** a full-file override of vanilla's
  `pop_browser_panel.gui`. That route is not open here: there's no vanilla window
  to extend.
- **Our own window:** a scripted widget like `te_systems_window`, with
  `datacontext = GetPlayerJournalEntry( 'je_space_race_solar_colonization' )`,
  so the `te_sr_*` types draw unchanged. The Timeline Extended window's tab
  already does this.
- **Vanilla's full-screen frame** (`fullscreen_block_window`) hard-wires its
  Close button to `InformationPanelBar.ClosePanel`, outside any block. A mod
  window copies the type under its own name.
- **The top bar:** vanilla full-screens draw on `layer_ingame_hud`, and a mod
  window on `layer_ingame_menu` sits below it. Inferred, not seen: the top bar
  and outliner would draw over a mod full-page, so it sits under the top bar, as
  the Timeline Extended window does.
- **Layout:** two columns (Mission Control and Fleets on the left, Colonies and
  Solar System on the right), with room for the schematic (§ 12).

Recommend building the tabs now and the window as its own project with the
schematic, since most of the window's value is the schematic and the wider
layout.

## 12. Solar system schematic (future)

In the full-page window: the nine locations on a schematic orbit diagram. Each
shows its colonies by holder (ours, allies, at war, neutral, free), fleets
present and inbound with their owner's side, and launch windows. Not a priority
(owner). Not scoped further here.

## 13. Reusable widgets (separate project)

Evidence: about a dozen systems each define their own `*_section_header`,
`*_subheader`, `*_note`, `*_value_row`, `*_panel` and `*_ov_cell`, mostly copied
from the UN chamber's. GUI types are global across files, so one library file
works:
- **The file:** `gui/te_widget_library.gui`, with `te_ui_*` types for the section
  header, subheader, note, value row, inset box, overview cell, stepper, segmented
  buttons and the popup shell (§ 3).
- **Order:** the popup shell is built in the library from the start; the rest
  move over one system per PR, after this pass.
- **Constraint:** tests like `test_space_race_labels.py` read each system's font
  templates and cell widths from its own file, so each move updates its tests.
- **Constraint:** `types` names are global, and the Community Mod Framework
  redefines some vanilla types (`gui_modding_guide.md` gotcha #30), so the
  prefix must be ours.

## 14. Build order

| PR | Contents | Depends on |
|---|---|---|
| 1 | #1274: the quick changes | — |
| 2 | The popup shell (§ 3, in the widget library file) and the colony target picker (§ 5): one body, no slot | — |
| 3 | The destination picker (§ 4) and the posture and target rows (§ 7) | 2 |
| 4 | Transfer (§ 6), replacing Detach and Merge | 2 |
| 5 | The Extraplanetary Base cell and the on-completion refresh (§ 8) | — |
| 6 | The Earth alert (§ 9) | — |
| 7 | Fleet upkeep and no departures without a Space Command (§ 10) | the size (§ 15) |
| 8 | Tabs (§ 11) | — |
| later | The full-page window and the schematic; the widget library's migration | — |

PRs 5, 6 and 8 are independent of the popup and can run in parallel with 2–4.
Every piece branches from `main` once #1274 has merged (the queue box, the
Solar System move and the removed Shielded state are its; my call), so none is
stacked on an open PR.
Every PR updates `docs/player_guide/16-space.md` where players see the change,
and adds its in-game checks to `docs/testing/solar-colonies-playtest.md`.

## 15. Open questions for the owner

1. **Earth alert (§ 9):** alert only when an arrival would change something (no
   fleet of ours at Earth, or outmatched), or on every hostile fleet bound for
   Earth? And `post_notification` or a popup event?
2. **Upkeep size (§ 10):** the four-Fusion-levels match (840 a week of base, +900%
   a unit), or another reference.

Answered 2026-10-31: the upkeep goods (six, § 10), no departures without a Space
Command (§ 10), Transfer into an existing fleet (§ 6), and the AI's Administration
from autonomy 25 while heading for 45 or more (shipped in #1274).
