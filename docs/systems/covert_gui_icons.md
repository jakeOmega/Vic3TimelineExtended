# Covert Warfare GUI: Icons

The Covert Warfare journal entry's overview draws fourteen icons of its own. They were vanilla placeholders during the style-guide pass, and PR #586 replaced them. All of them live in `gfx/interface/icons/covert_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/covert_operations_widget.gui`:
- the overview's first row (`te_covert_overview_panel`): one `covert_ov_icon_label` per standing code, two for funding, one per Tradecraft tier and one for a recent catch;
- the slot icon (`covert_ov_slot`), drawn ten times.

No script reads the paths. `IconsTest` in `test_covert_layout.py` holds each code to its file, checks that this page records every file, and fails on any placeholder left in the widget.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries are the `covert_part` and `covert` categories in `icon_prompts.py` (PR #586), and each entry's `now` field names the placeholder the icon replaced. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** is the UN's: one bold object, easy to recognise at 36 px (the slot at 26 px) (`un_gui_icons.md`). The states of one thing share an emblem and differ by a mark.

## Overview: intelligence standing

The five states share one emblem: a round steel shield with an eye on it. The metal and the damage carry the standing, and the eye opens as exposure grows. Picked by `covert_disp_standing_code`, at 36 px.

FLUX would not dent or break a shield, or shut an eye (eight seeds), so the cracks, the split and a steel eyelid are drawn. The eyelid is drawn before the metal's tint, so it takes the shield's metal and cracks with it. This departs from the original list, which asked for a dented shield for Defended.

| Code | Standing | Shows | File |
|---|---|---|---|
| 4 | Fortress | the shield with a gold rim, polished, the eye shut under its lid | `standing_fortress.dds` |
| 3 | Hardened | the same shield in silver, the eye shut | `standing_hardened.dds` |
| 2 | Defended | the same shield in dull iron, the eye shut | `standing_defended.dds` |
| 1 | Exposed | the iron shield cracked across, the eye half open | `standing_exposed.dds` |
| 0 | Vulnerable | the iron shield split in two, the eye wide open | `standing_vulnerable.dds` |

## Overview: funding, Tradecraft and a recent catch

At 36 px. Funding picks its icon by whether `covert_funding_level_display` is 0, and Tradecraft by `covert_tradecraft_tier`.

**Tradecraft departs from the original list.** The list asked for gold chevrons under the hat, and a gold hat band for Veteran. Instead the chevrons sit on a dark cloth patch beside the hat and dossier, as insignia do: gold on the orange dossier did not read at 36 px. There is no hat band, since four chevrons already mark the top rank.

| Icon | Shows | File |
|---|---|---|
| Funding, level 0 (Dormant) | an open, empty manila envelope, greyed, a torn red paper band hanging from it | `funding_dormant.dds` |
| Funding, levels 1-5 | a sealed tan manila envelope with a red paper band, green banknotes showing at its edge | `funding.dds` |
| Tradecraft: Untested (0) | a black fedora on a closed orange-brown leather dossier | `tradecraft_0.dds` |
| Tradecraft: Fledgling (1) | the fedora and dossier, one gold chevron on a dark cloth patch | `tradecraft_1.dds` |
| Tradecraft: Established (2) | the same, two chevrons | `tradecraft_2.dds` |
| Tradecraft: Seasoned (3) | the same, three chevrons | `tradecraft_3.dds` |
| Tradecraft: Veteran (4) | the same, four chevrons | `tradecraft_4.dds` |
| Spy Caught (while a catch from the last ten years stands) | a stylized cartoon spy in a tan trench coat and black fedora, both hands raised high, his face in the hat's shadow (the list asked for a figure in a searchlight's beam, but a beam cuts out as a grey blob) | `spy_caught.dds` |

## Overview: operation slots

| Icon | Shows | File |
|---|---|---|
| Operation slot (lit in use, at 25% opacity while free) | a closed tan manila case file with a small photograph paper-clipped to its cover | `operation_slot.dds` |

## Not from this set

- **Operation rows:** each row's icon is that operation's own diplomatic-action icon (`gfx/interface/icons/diplomatic_action_icons/covert_<type>_action.dds`).
- **Network rows:** each row leads with the target's flag, vanilla's `flag` widget.
- **Arrows and markers:** the trend arrows and the Tradecraft bar's marker are vanilla's (`trend_up` / `trend_down` / `trend_nochange`, `progressbar_marker`), as in the UN's panels.
- **The Funding Levels table:** its tint is a flat colour on `white.dds`, not an icon.
