# Covert Warfare GUI: Placeholder Icons

The Covert Warfare journal entry's overview draws fourteen icons of its own. All of them are vanilla placeholders or the entry's own icon, chosen so the layout can be judged in game before the art exists (`gui_style_guide.md` rule 10). This page lists them for the icon pipeline.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/covert_operations_widget.gui`: the overview's first row (`te_covert_overview_panel`, one `covert_ov_icon_label` per standing code, two for funding, one per Tradecraft tier, one for a recent catch) and the slot icon (`covert_ov_slot`, drawn ten times). No script reads the paths. `IconsTest` in `test_covert_layout.py` holds each placeholder to the path this page lists and fails if the overview uses a texture it doesn't know.

**Swapping one in.** Render it, write it to the proposed path, then change the path in the widget and in `test_covert_layout.py`'s `STANDING_ICONS` / `TRADECRAFT_ICONS` / `OTHER_ICONS`. The slot icon is drawn at 25% opacity while the slot is free, so it must still read when faded, like the UN's agencies.

**Style.** Shown at 36 px (the slot at 26 px), beside the UN's overview icons, so the same rule applies: one bold object, easy to recognise at that size (`un_gui_icons.md`). The five standings are states of one thing, so they share an emblem, a round steel shield with a closed eye on it, and differ by its state, the way the UN's membership icons share the wreath. The five Tradecraft tiers are one agent's rise, so they share an emblem too: a black fedora on a leather dossier, with a gold chevron under it per tier.

| Icon (code) | Where | Placeholder now | Final art should show (icon-pipeline subject) | Proposed path |
|---|---|---|---|---|
| Standing: Fortress (4) | overview, first row | `gfx/interface/icons/generic_icons/green_checkmark.dds` | a round steel shield with a closed eye embossed on it, whole and polished, with a gold rim | `gfx/interface/icons/covert_icons/standing_fortress.dds` |
| Standing: Hardened (3) | overview, first row | `gfx/interface/icons/generic_icons/approval_icon.dds` | the same shield, whole, with a plain silver rim | `gfx/interface/icons/covert_icons/standing_hardened.dds` |
| Standing: Defended (2) | overview, first row | `gfx/interface/icons/generic_icons/undecided_icon.dds` | the same shield in dull iron, dented, the eye still closed | `gfx/interface/icons/covert_icons/standing_defended.dds` |
| Standing: Exposed (1) | overview, first row | `gfx/interface/icons/generic_icons/disapproval_icon.dds` | the same shield cracked across, the eye half open | `gfx/interface/icons/covert_icons/standing_exposed.dds` |
| Standing: Vulnerable (0) | overview, first row | `gfx/interface/icons/generic_icons/red_cross.dds` | the same shield split in two, the eye wide open | `gfx/interface/icons/covert_icons/standing_vulnerable.dds` |
| Funding, level 0 (Dormant) | overview, first row | `gfx/interface/icons/generic_icons/warning.dds` | an open, empty manila envelope with a torn red "classified" band, grey | `gfx/interface/icons/covert_icons/funding_dormant.dds` |
| Funding, levels 1-5 | overview, first row | `gfx/interface/icons/generic_icons/gdp.dds` | a sealed manila envelope with a red "classified" band and a thick stack of banknotes showing at its edge | `gfx/interface/icons/covert_icons/funding.dds` |
| Tradecraft: Untested (0) | overview, first row | `gfx/interface/icons/generic_icons/maybe_icon.dds` | a black fedora resting on a closed leather dossier, no chevron | `gfx/interface/icons/covert_icons/tradecraft_0.dds` |
| Tradecraft: Fledgling (1) | overview, first row | `gfx/interface/icons/generic_icons/population.dds` | the same fedora and dossier, one gold chevron beneath | `gfx/interface/icons/covert_icons/tradecraft_1.dds` |
| Tradecraft: Established (2) | overview, first row | `gfx/interface/politics_view/institution_level_icon.dds` | the same, two gold chevrons | `gfx/interface/icons/covert_icons/tradecraft_2.dds` |
| Tradecraft: Seasoned (3) | overview, first row | `gfx/interface/icons/formation_order_icons/upgrade.dds` | the same, three gold chevrons | `gfx/interface/icons/covert_icons/tradecraft_3.dds` |
| Tradecraft: Veteran (4) | overview, first row | `gfx/interface/icons/generic_icons/most_senior_front_commander.dds` | the same, four gold chevrons and a gold band on the hat | `gfx/interface/icons/covert_icons/tradecraft_4.dds` |
| Spy Caught (while a catch from the last ten years stands) | overview, first row | `gfx/interface/icons/military_icons/navy_icons/detection_navy.dds` | a trench-coated silhouette caught in the white beam of a searchlight | `gfx/interface/icons/covert_icons/spy_caught.dds` |
| Operation slot (lit in use, faded free) | overview, second row, ten times | `gfx/interface/icons/event_icons/je_covert_warfare.dds` | a plain manila case file with a photograph paper-clipped to its cover | `gfx/interface/icons/covert_icons/operation_slot.dds` |

Not placeholders: each operation row's icon is that operation's own diplomatic-action icon (`gfx/interface/icons/diplomatic_action_icons/covert_<type>_action.dds`), and the trend arrows and bar markers are vanilla's (`trend_up` / `trend_down` / `trend_nochange`, `progressbar_marker`), as in the UN's panels.

The Tradecraft icon is picked by `covert_tradecraft_tier` (owner, round 2: one icon per tier), as the standing icon is by `covert_disp_standing_code`.

Each network row leads with its target's flag, vanilla's `flag` widget; that is not a placeholder either.
