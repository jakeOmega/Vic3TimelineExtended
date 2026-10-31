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
  with `scope:op` the slot and `scope:pick` the location. Go stays on the row
  (see the builder's call below).
- **Unavailable rows** are greyed, with the reason (`IsValidTooltip`): no delta-v
  for the leg, still refitting, a closed window, or Earth's launch bar.

**Script:** a new scripted GUI with a `possible` per location, built from the
per-slot, per-location triggers that already exist
(`sr_fl_<n>_may_depart_<loc>`). The step-through `sr_fl_dest_pick_<n>` stays
for the AI and the console until nothing uses it.

**Builder's call:** whether the popup sets the destination only, keeping Go on
the row, or dispatches at once. The owner asked for a destination selector;
dispatching at once saves a click, but a player can't then look before leaving.
Recommend: **pick sets the destination, Go stays on the row**, because a fleet
often waits for its window.

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

## 6. Detach: choose how much of each role

**Today:** `sr_fl_detach` moves half of every role, and half the marines, into
the lowest empty slot.

**The popup:**
- **One row per role** (warships, rapid, siege, carriers, tenders) and marines,
  each with its current strength and five share buttons: none, ¼, ½, ¾, all.
  The default is ½, today's behavior.
- **A footer:** what the new fleet would carry, and Detach.

**State:** a typed number can't reach script (only base-game rename popups take
text, `gui_modding_guide.md:1380`), and a `GetVariableSystem` value can't be
read back as a number. So the shares are **country variables**,
`sr_det_share_<role>`, set by a scripted GUI per button (`scope:op` the slot,
`scope:pick` role × 10 + share). Detach applies them, and opening the popup
resets them to ½. They are game state, so a share click is a command, as every
fleet order already is.

**Script:** `sr_fl_detach` (generated) takes a share per role in place of 0.5,
for each role's `_<role>` and `_<role>_full`, and for the marines. Detaching
nothing, or everything, is refused, with the reason in Detach's tooltip.

**Open question (owner):** should Detach also take an existing fleet at the
same location as its target, not only a new slot? That makes it a general
Transfer and folds Merge into it. It costs one more row of buttons in the popup.

## 7. Posture and target rows

**Replaces:** the step-through posture, target and interdiction-target buttons
on a fleet's row (6b, 6c).

- **Posture:** a row of three or four buttons in the approach selector's shape
  (`te_sr_action_button`). The choices are Station, Stand off, Close in and, where
  offered, Interdict, under Earth's own rules (lunar colonization design § 8:
  Close in at Earth only against a lunar world).
  The current one is lit. Each is enabled where its step allows it today, with the
  reason when it isn't.
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
  variable `sr_ebase_next_grade` that `sr_ebase_fill` records (the grade of the
  first room it leaves unfilled, or −75%). Both change only when a level
  finishes or the room changes.
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
fires `space_race_events.100` once, at departure. For Earth it never fires:
`sr_loc_held_earth` is `always = no`, although six lunar sites sit at Earth.
Nothing in the panel warns of an enemy fleet heading to Earth. The inbound
counts (`sr_loc_inbound_<loc>`) include our own and allied fleets.

**What:**
- **A warning cell in the overview** while any power at war with us has a fleet
  bound for Earth: "Hostile fleet: Earth in N mo", with its strength. The hover
  lists each fleet with its owner.
- **A notice the month one sets out, or a war starts while one is in flight**,
  for a player with a Space Program or a fleet. It fires once per fleet leg, on
  the pattern of `sr_earth_notice_step` (`sr_earth_orbit_effects.txt:192-240`)
  with a noted marker. Departure alone misses a war declared mid-flight.
- **The Earth arm of `.100`:** a lunar colony's holder is alerted like any other
  colony's. Earth holds the lunar sites, so `sr_loc_held_earth` should read the
  six lunar sites.

**Script:** a generated value per location for the hostile inbound (the earliest
landing month and the strength, over the hostile powers' nine slots), in
`gen_space_fleets.py`. The trigger is
`any_in_global_list = { variable = sr_fleet_powers has_war_with = prev sr_fl_any_bound = { CODE = 1 } }`.

**Open question (owner):** a popup event as well as the cell, or only the cell
and an alert-style notification? Recommend the cell plus a one-line notification
event (no options), as the blockade notices are.

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
switches down, and switches back up when building.

**Options:**
1. **Normalize the multiplier by the method (recommended).** Each good's upkeep
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

**Related gap, for the owner:** the upkeep sits only on Space Command buildings.
A country that demolishes or downsizes Space Command after building its fleet
seems to pay little or nothing to keep it. Should a fleet with no Space Command
to keep it lose strength or readiness, or should upkeep then fall on the Space
Program building?

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
| 4 | Detach shares (§ 6) | 2 |
| 5 | The Extraplanetary Base cell and the on-completion refresh (§ 8) | — |
| 6 | The Earth alert (§ 9) | — |
| 7 | Fleet upkeep (§ 10) | the owner's choice |
| 8 | Tabs (§ 11) | — |
| later | The full-page window and the schematic; the widget library's migration | — |

PRs 5, 6 and 8 are independent of the popup and can run in parallel with 2–4.
Every PR updates `docs/player_guide/16-space.md` where players see the change,
and adds its in-game checks to `docs/testing/solar-colonies-playtest.md`.

## 15. Open questions for the owner

1. **Upkeep (§ 10):** option 1, 2 or 3; and what a fleet with no Space Command
   should cost.
2. **Detach (§ 6):** also into an existing fleet (a general Transfer that folds
   Merge in)?
3. **Earth alert (§ 9):** the cell and a notification, or a popup event too?
4. **Destination (§ 4):** the popup sets the destination with Go on the row
   (recommended), or dispatches at once?
