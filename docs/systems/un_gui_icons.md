# UN GUI: Icons

The UN overview and the General Assembly's session strip draw 43 icons of their own, plus a pie pair. They were vanilla placeholders in the first round of the UN GUI pass (PR #567), and PR #572 replaced them. All of them live in `gfx/interface/icons/un_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/un_overview_widget.gui` (membership, tier, crisis, vacant seat, agencies, pies) or `un_layout_widget.gui` (topics), chosen by a display value's code. No script reads the paths. `UnIconsTest` in `test_un_overview_data.py` holds each code to its file and fails on any placeholder left in either file.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md` § "UN GUI icons"). Their registry entries are the `un_part`, `un_member`, `un_tier` and `un_disc` categories in `icon_prompts.py`. Each entry's `now` field names the vanilla placeholder the icon replaced, which the review sheet shows beside it. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set: simple and easy to recognize at 32–40 px.** At that size vanilla's own painted alert icons blur, and only flat marks (a check, a cross, a plus, the warning "!") still read. So most icons are one bold object, and the states of one thing share an emblem and differ by a mark.

## Overview: membership, crisis, vacant seat

One emblem, a gold laurel wreath around a blue globe, under a mark. Colour means the membership's benefits apply and grey means they don't; the mark names the state. Shown at 36 px (the seat at 66×44).

| Code | State | Shows | File |
|---|---|---|---|
| 0 | No UN | the emblem, faint grey, no mark | `member_no_un.dds` |
| 1 | Cannot join | grey, vanilla's red cross | `member_cannot_join.dds` |
| 2 | Not a member (can join) | grey, vanilla's green plus | `member_can_join.dds` |
| 3 | Member | colour, vanilla's green check | `member.dds` |
| 4 | Permanent member | colour, the green check and a drawn gold star | `member_permanent.dds` |
| 5 | Suspended, seat carried | colour, a drawn pause mark | `member_suspended_carried.dds` |
| 6 | Suspended | grey, a drawn pause mark | `member_suspended.dds` |
| — | Crisis (while open) | colour, vanilla's warning mark | `crisis.dds` |
| — | Vacant permanent seat | UN-blue cloth with the emblem as a pale watermark, in a flag's proportions | `seat_vacant.dds` |

The pause mark is drawn (amber bars on a dark badge) because vanilla's `paused.dds` gold bars vanish on the gold wreath. The vacant seat is drawn stretched: tiling it as a frame (`Corneredtiled`) would stripe the watermark.

## Overview: authority tier

Painted cut-outs, no disc: the silhouette and the metal carry the climb. 36 px.

| Code | Tier | Shows | File |
|---|---|---|---|
| 0 | Moribund | a broken grey marble column, two fallen drums beside it | `tier_moribund.dds` |
| 1 | Contested | two weathered bronze columns of unequal height | `tier_contested.dds` |
| 2 | Established | three bronze columns under a plain stone lintel | `tier_established.dds` |
| 3 | Strong | a silver portico of four columns under a pediment | `tier_strong.dds` |
| 4 | Supranational | a gold temple front of six columns under a pediment | `tier_supranational.dds` |

## Overview: agencies

One drawn disc (UN-blue enamel, a gold rim) under one warm or light symbol each. 36 px, at full colour once founded and 25% opacity until then.

| Agency | Shows | File |
|---|---|---|
| WHO | a gold staff with a green serpent coiled around it | `agency_who.dds` |
| UNESCO | a terracotta Greek amphora | `agency_unesco.dds` |
| ICJ | brass balance scales, level | `agency_icj.dds` |
| UNHRC | a gold dove, wings spread | `agency_unhrc.dds` |
| IAEA | a gold atom around a red nucleus | `agency_iaea.dds` |
| UNEP | a broad green leaf | `agency_unep.dds` |
| UNHCR | a canvas tent, flap open | `agency_unhcr.dds` |
| UNOOSA | a ringed planet | `agency_unoosa.dds` |
| ITLOS | a brass anchor | `agency_itlos.dds` |
| ICC | a judge's gavel on its block | `agency_icc.dds` |
| CPPNM | a brass padlock with a radiation trefoil | `agency_cppnm.dds` |
| CCD | a wooden painter's palette with red, yellow and green paint | `agency_ccd.dds` |
| TPNW | a dark grey aerial bomb wrapped in an iron chain | `agency_tpnw.dds` |
| INCB | a red poppy and its green seed pod | `agency_incb.dds` |

## General Assembly: resolution topics

The session strip, one per `un_disp_res_topic_code`, at 40 px. The same disc as the agencies. A convention topic is its agency's icon under a small parchment-scroll badge, so "a resolution about X" reads apart from "agency X".

| Code | Topic | Shows | File |
|---|---|---|---|
| 0 | Condemnation of aggression | the mandate's crossed swords under vanilla's red cross | `topic_condemn.dds` |
| 1 | International sanctions | a wooden crate bound with an iron chain | `topic_sanctions.dds` |
| 2 | Expulsion of a permanent member | a gold star over a drawn red down arrow | `topic_expulsion.dds` |
| 3 | Authorized military mandate | two crossed steel swords with gold hilts | `topic_mandate.dds` |
| 4 | Peacekeeping deployment | a light-blue helmet | `topic_peacekeepers.dds` |
| 5 | Humanitarian aid | two burlap grain sacks | `topic_aid.dds` |
| 6 | Charter reform | a quill in a dark ceramic inkwell | `topic_reform.dds` |
| 7 | Declaration of Human Rights | UNHRC's dove + the scroll | `topic_human_rights.dds` |
| 8 | International Criminal Court | ICC's gavel + the scroll | `topic_icc.dds` |
| 9 | Non-Proliferation Treaty | IAEA's atom + the scroll | `topic_npt.dds` |
| 10 | Climate accord | UNEP's leaf + the scroll | `topic_climate.dds` |
| 11 | Pandemic response | WHO's staff + the scroll | `topic_pandemic.dds` |
| 12 | Refugee resolution | UNHCR's tent + the scroll | `topic_refugee.dds` |
| 13 | Cultural heritage program | UNESCO's amphora + the scroll | `topic_heritage.dds` |
| 14 | Decolonization resolution | a green flag planted in a mound of earth | `topic_decolonization.dds` |
| 15 | Space cooperation | UNOOSA's planet + the scroll | `topic_space.dds` |
| 16 | Law of the Sea | ITLOS's anchor + the scroll | `topic_law_of_sea.dds` |
| 17 | Physical protection of nuclear material | CPPNM's padlock + the scroll | `topic_physical_protection.dds` |
| 18 | Convention on Cultural Diversity | CCD's palette + the scroll | `topic_cultural_diversity.dds` |
| 19 | Treaty on the Prohibition of Nuclear Weapons | TPNW's chained bomb + the scroll | `topic_nuclear_ban.dds` |
| 20 | Referral to the World Court | brass balance scales, a rolled paper tied with red cord in one pan | `topic_court_referral.dds` |
| 21 | Arms embargo | a brass artillery shell bound in a padlocked chain | `topic_arms_embargo.dds` |
| 22 | Suspension of credentials | a leather diplomatic folder with a gold seal, under vanilla's red cross | `topic_credentials.dds` |
| 23 | Standing UN Force | three light-blue helmets | `topic_standing_force.dds` |
| 24 | Electoral observers | black binoculars on a wooden box | `topic_observer_request.dds` |
| 25 | World Food Reserve | a steel grain silo, a heap of grain at its foot | `topic_food_reserve.dds` |
| 26 | Binding ceasefire | a field cannon with an olive branch in its muzzle | `topic_ceasefire.dds` |
| 27 | World Development Fund | a stack of gold coins with a seedling sprouting from the top | `topic_development_fund.dds` |
| 28 | Supervised referendum | a wooden ballot box, a paper ballot in its slot | `topic_referendum.dds` |
| 29 | Narcotics convention | INCB's poppy + the scroll | `topic_narcotics.dds` |

## Overview: member-share pies

`te_un_ov_pie`, in the Cultural Hegemony pie's format: two 128×128 frames, frame 1 transparent and frame 2 the colour (`docs/guides/gui_modding_guide.md`, "Pie charts of script-held data"). `scripts/image_pipeline/gen_ch_model_pie_textures.py` writes them from its `UN_PIES` colours.

| Role | Colour | File |
|---|---|---|
| Members' share (the fill) | UN blue, `#5b92e5` | `pie_members.dds` |
| The rest (the disc under it) | muted grey, `#8c8474` | `pie_rest.dds` |

## Vanilla art the UN GUI keeps

Used as vanilla uses it, with nothing to replace:
- the trend icons beside each pillar bar (`generic_icons/trend_up.dds`, `trend_down.dds`, `trend_nochange.dds`);
- the target tick on the authority bar and the two-thirds mark on the tally bar (`progressbar/progressbar_marker.dds`), and the invisible bar that carries the tick (`generic_icons/transparent.dds`);
- every progress bar, and the ring around the pies (`round_frame_dec.dds`);
- the Security Council flags themselves (vanilla's `flag`);
- the headquarters row's icon, which is the UN headquarters building's own (`building_icons/building_un_headquarters.dds`).
