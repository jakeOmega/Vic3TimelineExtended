# Space Race full screen: Solar System Colonization's tabs side by side

Date: 2026-11-26. A small change; the owner's request, two answers to questions, then work done while they were away.

## Intent

In the era of solar colonization the player spends most of their time on the Space Race, and in the Timeline Extended
window's Full Screen its four tabs (Mission Control, Fleets, Colonies, Solar System) sat in the middle column while
the left and right columns held only read-only figures. The owner's words: "it seems awfully wasteful in the full
screen mode ... In this mode, I think it would make sense to allow this info to be viewable at the same time."

## What the owner decided

- The Solar System, with its schematic, in the left column above Program Effects.
- Fleets in the right column, above Space Powers.
- Colonies in the centre column.
- Mission Control in the left column, directly under the milestone's overview (their pick of three placements: under
  the overview, at the bottom of the left column, or above Colonies in the centre).
- Colonies keeps its five view buttons (People, Modules, Autonomy, Defenses, Bases), one view at a time (their pick
  over stacking every view in each colony's box, or a summary view and Modules).
- The side panel ("the compressed, single column view") and the journal are unchanged.

## Non-goals

- No change to any section's content, the Colonies views, or the side panel's tabs.
- No change for another country in National Info: it sees no live sections, as before.

## Approaches

1. **Split the four tabs into types of their own** (chosen). `te_sr_solar_colonization_status` keeps its button row
   and instances `te_sr_solar_colonization_{mission,fleets,colonies,system}`, each with its tab's `visible`; the
   full-screen composer places the same types with no buttons. One definition of each part, so the hosts can't drift.
2. Instance the whole tabbed status three times full screen, with blockoverrides hiding all but some tabs. Rejected:
   every hidden part would still be built (Colonies three times), and each instance would need a dozen overrides.
3. Copy the tabs' markup into the full-screen composer. Rejected: two copies of about a hundred lines that would drift,
   which `test_space_race_layout.py` exists to stop.

## The design

- Column 1: `te_sr_window_milestones`, its solar-colonization frame's `sr_window_solar_colonization_live` block
  filled with Mission Control (its `sr_mission_debris` block emptied: Orbit shows the debris row once) and the Solar
  System. The frame keeps its header, overview, Program Effects and Open Journal Entry around them.
- Column 2: `te_sr_window_solar_colonization_colonies`, generated (`SR_OWN_COLUMN` in `gen_te_systems_window.py`),
  under the frame's gates (the entry shown for the Country, the player's own, the entry's datacontext on the guard's
  child). The column closes up while it doesn't show.
- Column 3: `te_sr_window_solar_colonization_fleets`, generated the same way, then Space Powers and Orbit.
- Mission Control's debris row: the part has `block "sr_mission_debris"`; the status instance fills it with
  `block "sr_debris" { te_sr_debris_row = {} }`, so the window's frame (which empties `sr_debris`) and the journal
  (which keeps it) behave as before. A distinct name avoids a block overridden by an override of the same name.

## Left to the builder, and what came of it

- Seen in game on the owner's June 2043 save (run `20261126T101355Z`): the layout as designed, the side panel and the
  journal unchanged. Full Screen drew at 15 to 16 frames a second there, against 33 for its old default; most of the
  cost was there before (the overview's Base Room and Resort Room figures, the colony rows) and is issue #2080. Which
  part, if any, starts collapsed full screen is the owner's call.
