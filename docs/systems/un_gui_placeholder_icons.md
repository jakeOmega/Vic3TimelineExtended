# UN GUI: Placeholder Icons

Round 1 of the UN GUI pass (`docs/superpowers/specs/2026-09-28-un-gui-pass-design.md`) draws every new icon with a vanilla texture as a placeholder. This is the list of them, where each is set, and what the final art should show.

**How to swap one in.** Every placeholder is a literal `texture = "…"` path in the `.gui` file named in its section. Replacing the art means writing a DDS and changing that one path; no script reads these paths. The proposed paths below put the UN's art in one folder, `gfx/interface/icons/un_icons/`.

**Writing the subjects.** The "Ideal" column is written as a subject for the icon pipeline (`scripts/image_pipeline/icon_prompts.py`): one physical object with its material and colour, no lettering, no flags, no faces, no real emblem. The UN's own motif here is a **laurel wreath around a pale-blue globe**, deliberately not the real UN emblem. Where a set shares a frame or a colour scale, that is said once in the section's lead.

Sizes are the displayed size. Render at the vanilla folder's size and let the GUI scale.

## Overview: membership (32×32)

`gui/journal_entry_widgets/un_overview_widget.gui`, the `MEMBERSHIP` icons, one per `un_disp_member_code`. The label beside each icon names the state, so the art only has to read at a glance. The set shares the laurel-and-globe roundel and changes the mark on it.

| Code | State | Placeholder | Ideal | Proposed path |
|---|---|---|---|---|
| 0 | No UN | `generic_icons/map_list_cross.dds` | a cracked, greyed stone laurel-and-globe roundel, one half fallen away | `un_icons/member_no_un.dds` |
| 1 | Cannot join | `generic_icons/red_cross.dds` | the roundel behind a small closed iron gate, muted red enamel | `un_icons/member_cannot_join.dds` |
| 2 | Not a member (can join) | `generic_icons/checkbox_simple.dds` | the roundel as an empty bronze outline, an open doorway at its centre | `un_icons/member_can_join.dds` |
| 3 | Member | `generic_icons/green_checkmark.dds` | the roundel in pale blue with a green enamel check mark over it: the "green checkbox" | `un_icons/member.dds` |
| 4 | Permanent member | `generic_icons/checkbox_greencheck.dds` | the roundel in pale blue with a green check and a small gold star above it | `un_icons/member_permanent.dds` |
| 5 | Suspended, seat carried | `generic_icons/checkmark.dds` | the roundel in amber, held up from below by a larger bronze hand | `un_icons/member_suspended_carried.dds` |
| 6 | Suspended | `generic_icons/warning.dds` | the roundel in amber with a dark horizontal bar across it | `un_icons/member_suspended.dds` |

## Overview: authority tier (32×32)

Same file, the `TIER` icons, one per `un_disp_tier_code`. One motif in five stages, so the tier reads as a climb: a classical colonnade that gains columns and finer metal.

| Code | Tier | Placeholder | Ideal | Proposed path |
|---|---|---|---|---|
| 0 | Moribund | `alert_icons/revolution.dds` | a single cracked grey stone column, its top broken off | `un_icons/tier_moribund.dds` |
| 1 | Contested | `alert_icons/low_legitimacy.dds` | two weathered bronze columns, one leaning | `un_icons/tier_contested.dds` |
| 2 | Established | `generic_icons/checkmark.dds` | three upright bronze columns under a plain lintel | `un_icons/tier_established.dds` |
| 3 | Strong | `generic_icons/green_checkmark.dds` | a silver portico of four columns with a pediment | `un_icons/tier_strong.dds` |
| 4 | Supranational | `alert_icons/formable_possible.dds` | a gold portico of six columns with a pale-blue globe on the pediment | `un_icons/tier_supranational.dds` |

## Overview: crisis alert (32×32)

Same file, shown only while the UN's crisis is open.

| Placeholder | Ideal | Proposed path |
|---|---|---|
| `alert_icons/critical_supply_network.dds` | the laurel-and-globe roundel split by a jagged red crack, on vanilla's round red alert disc | `un_icons/crisis.dds` |

## Overview: the Security Council's vacant seat (66×44)

Same file, `te_un_ov_vacant_seat`, in place of a flag when a permanent seat is empty.

| Placeholder | Ideal | Proposed path |
|---|---|---|
| `progressbar/progressbar_empty.dds` (a dark frame) | an empty flag frame in vanilla's flag-frame style: a bare pale-blue cloth with a faint laurel outline | `un_icons/seat_vacant.dds` |

## Overview: agencies (36×36)

Same file, `te_un_ov_agency`, eleven icons. The GUI shows each at full colour once founded and at 25% opacity until then, so one texture per agency is enough. The set shares a frame: a pale-blue enamel roundel with a thin gold rim, one symbol on each.

| Agency | Placeholder | Ideal (the symbol on the roundel) | Proposed path |
|---|---|---|---|
| WHO | `institution_icons/health_service.dds` | a bronze staff with a single serpent coiled around it | `un_icons/agency_who.dds` |
| UNESCO | `goods_icons/fine_art.dds` | a small white marble temple façade over an open book | `un_icons/agency_unesco.dds` |
| ICJ | `institution_icons/home_affairs.dds` | brass balance scales, level | `un_icons/agency_icj.dds` |
| UNHRC | `institution_icons/social_security.dds` | two open hands releasing a white dove | `un_icons/agency_unhrc.dds` |
| IAEA | `goods_icons/electricity.dds` | a silver atom: three elliptical orbits around a blue nucleus | `un_icons/agency_iaea.dds` |
| UNEP | `goods_icons/wood.dds` | a green leaf curled around a small pale-blue globe | `un_icons/agency_unep.dds` |
| UNHCR | `institution_icons/colonization.dds` | two cupped hands sheltering a small canvas tent | `un_icons/agency_unhcr.dds` |
| UNOOSA | `goods_icons/aeroplanes.dds` | a small white satellite on an orbit line around a pale-blue globe | `un_icons/agency_unoosa.dds` |
| ITLOS | `goods_icons/merchant_marine.dds` | an iron anchor over blue waves | `un_icons/agency_itlos.dds` |
| ICC | `institution_icons/police.dds` | a dark wooden gavel resting across brass scales | `un_icons/agency_icc.dds` |
| CPPNM | `goods_icons/explosives.dds` | a steel padlock closed over a small silver atom | `un_icons/agency_cppnm.dds` |

## General Assembly: resolution topics (40×40)

`gui/journal_entry_widgets/un_layout_widget.gui`, the session strip, one per `un_disp_res_topic_code`. A convention topic founds or runs an agency, so its icon can be that agency's art with a small **rolled parchment scroll** badge in one corner. That tells "a resolution about X" from "agency X" and costs one badge rather than eleven new pictures.

| Code | Topic | Placeholder | Ideal | Proposed path |
|---|---|---|---|---|
| 0 | Condemnation of aggression | `alert_icons/land_invasion.dds` | a raised wooden gavel over a small cracked bronze shield | `un_icons/topic_condemn.dds` |
| 1 | International sanctions | `alert_icons/blockaded.dds` | a wooden crate bound shut with a heavy iron chain | `un_icons/topic_sanctions.dds` |
| 2 | Expulsion of a permanent member | `alert_icons/is_losing_rank.dds` | an empty carved chair tipped on its side, a gold star falling from it | `un_icons/topic_expulsion.dds` |
| 3 | Authorized military mandate | `goods_icons/artillery.dds` | a steel sword lying under a bronze laurel wreath | `un_icons/topic_mandate.dds` |
| 4 | Peacekeeping deployment | `goods_icons/small_arms.dds` | a pale-blue steel helmet | `un_icons/topic_peacekeepers.dds` |
| 5 | Humanitarian aid | `goods_icons/groceries.dds` | a wooden supply crate with a pale-blue band, sacks of grain beside it | `un_icons/topic_aid.dds` |
| 6 | Charter reform | `alert_icons/reform_government.dds` | a large parchment scroll with a quill pen laid across it | `un_icons/topic_reform.dds` |
| 7 | Universal Declaration of Human Rights | `institution_icons/social_security.dds` | UNHRC's art + the scroll badge | `un_icons/topic_human_rights.dds` |
| 8 | International Criminal Court | `institution_icons/police.dds` | ICC's art + the scroll badge | `un_icons/topic_icc.dds` |
| 9 | Nuclear Non-Proliferation Treaty | `goods_icons/electricity.dds` | IAEA's atom with a broken missile beneath it, + the scroll badge | `un_icons/topic_npt.dds` |
| 10 | Climate accord | `goods_icons/wood.dds` | UNEP's leaf and globe with a small glass thermometer, + the scroll badge | `un_icons/topic_climate.dds` |
| 11 | Global pandemic response | `institution_icons/health_service.dds` | WHO's art + the scroll badge | `un_icons/topic_pandemic.dds` |
| 12 | International refugee resolution | `institution_icons/colonization.dds` | UNHCR's art + the scroll badge | `un_icons/topic_refugee.dds` |
| 13 | Cultural heritage program | `goods_icons/fine_art.dds` | UNESCO's art + the scroll badge | `un_icons/topic_heritage.dds` |
| 14 | Decolonization resolution | `alert_icons/secession.dds` | an iron chain with one broken link | `un_icons/topic_decolonization.dds` |
| 15 | International space cooperation | `goods_icons/aeroplanes.dds` | UNOOSA's art + the scroll badge | `un_icons/topic_space.dds` |
| 16 | Law of the Sea convention | `goods_icons/merchant_marine.dds` | ITLOS's art + the scroll badge | `un_icons/topic_law_of_sea.dds` |
| 17 | Physical protection of nuclear material | `goods_icons/explosives.dds` | CPPNM's art + the scroll badge | `un_icons/topic_physical_protection.dds` |

## Overview: member-share pies (64×64)

Same file, `te_un_ov_pie`. These reuse the Cultural Hegemony pie textures, which are the right format: two 128×128 frames, frame 1 transparent and frame 2 the colour (`docs/guides/gui_modding_guide.md`, "Pie charts of script-held data"). The fill is `ch_pie_liberal.dds` and the background disc `ch_pie_other.dds`. The UN's own pair needs no art, only colours: `scripts/image_pipeline/gen_ch_model_pie_textures.py` makes them from a colour list.

| Role | Placeholder | Ideal | Proposed path |
|---|---|---|---|
| Members' share (fill) | `journal_entry_widgets/ch_model_pie/ch_pie_liberal.dds` | the UN's pale blue | `un_icons/pie_members.dds` |
| The rest (background) | `journal_entry_widgets/ch_model_pie/ch_pie_other.dds` | a muted grey-parchment | `un_icons/pie_rest.dds` |

## Vanilla pieces that are already right

These are vanilla's own textures, used as vanilla uses them, and need no replacement:
- the trend icons beside each pillar bar (`generic_icons/trend_up.dds`, `trend_down.dds`, `trend_nochange.dds`);
- the target tick on the authority bar and the two-thirds mark on the tally bar (`progressbar/progressbar_marker.dds`), and the invisible bar that carries the tick (`generic_icons/transparent.dds`);
- every progress bar (`default_`, `green_`, `bad_`, `white_progressbar_horizontal`, `double_direction_progressbar`);
- the Security Council flags themselves (vanilla's `small_flag`).
