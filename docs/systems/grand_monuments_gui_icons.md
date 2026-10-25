# Grand Monuments GUI: Icons

The Monuments journal entry's overview and its monument rows draw five icons of their own: the four statuses and Hard Times. They were vanilla placeholders in the first round of the style pass, and PR #586 replaced them. All five live in `gfx/interface/icons/gm_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/grand_monuments_widget.gui`. The status icons appear twice: once in the overview's cells (`te_gm_overview_panel`, one `gm_ov_cell` per status) and once in each monument row (`gm_monument_row`, one `gm_row_status` per `gm_status_code`). The state view's card (`te_state_gm_card` in `gui/te_state_panel_widgets.gui`) draws the row's four the same way, from its own literal lines. Hard Times appears once, on its own line under the cells, only while hard times hold. No script reads the paths. `IconsTest` in `test_grand_monuments_layout.py` holds each code to its file in its `ICONS` table. It fails if the widget uses a texture the table doesn't list, or any vanilla `generic_icons` placeholder. `StateCardTest` holds the card's four to the same table.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`). Their registry entries in `icon_prompts.py` are:

- `gm_part`: the stele, the wreath, the railing, and an obelisk alternative;
- `gm_state`: the four statuses, each built from the stele;
- `gm`: Hard Times.

Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The set.** The four statuses are one stone stele with a blank panel on a plinth, and each status is a mark or a treatment of that same stone. They show at 36 px, in the overview at 25% opacity while a status's count is zero. Hard Times shows at 32 px.

| Code | Status | Shows | File | Replaced |
|---|---|---|---|---|
| 1 | Undedicated | the bare stele, its panel blank | `status_undedicated.dds` | `generic_icons/undecided_icon.dds` |
| 2 | Upheld | the stele with a gold laurel wreath hung on its panel | `status_upheld.dds` | `generic_icons/green_checkmark.dds` |
| 3 | Heritage | the stele aged green (a drawn tint) behind a two-post bronze stanchion | `status_heritage.dds` | `generic_icons/maybe_icon.dds` |
| 4 | Contested | the stele cracked from its top through the plinth, and leaning | `status_contested.dds` | `generic_icons/disapproval_icon.dds` |
| — | Hard Times | a stonemason's steel chisel and wooden mallet crossed in front of an empty wooden bowl | `hard_times.dds` | `generic_icons/warning.dds` |

"Unsettled", the brief state between a change of government and the month's check, shares code 2 and so shows the Upheld icon, with its own word beneath.

**Where the art departs from the brief.**

- **Heritage.** The brief asked for the monument weathered and mossy behind a low railing. The moss is a drawn green tint and the railing a two-post stanchion, because noise-patch moss read as camouflage.
- **Contested.** The brief asked for a rope thrown around its top and a crack down its face. The art drops the rope, which risked reading as a gallows; the stele is cracked and leans, as if being pulled down.
- **Hard Times.** The brief asked for the bowl beside idle tools. The tools lie crossed in front of the bowl; the first subject drew a mortar and pestle.

**Open question.** At 36 px the stele can read as a gravestone. #586 queued an obelisk alternative (`gm_part/obelisk`). If it is adopted, the four status files keep their names, so only the "Shows" column above changes.

**Monument pictures (2026-10-11).** Each monument's row and its state card also show a picture of its style and form, from `gfx/interface/icons/gm_pictures/` (80 files, `<skin>__<form>.dds`, framed like the building icons). They are not status icons: the `gm_picture` type and the `PICTURES` table in `test_grand_monument_registry.py` list them, and the status badge sits over the picture's corner.

**Landmarks on a stand-in picture (art backlog).** A landmark shows its own picture, `gm_pictures/landmark_<key>__<form>.dds` at code 1,000,000 + its `LANDMARKS` row, once one is drawn; until then it shows the stand-in pair named in its row. `PLACEHOLDER_PICTURES` in `test_grand_monument_registry.py` lists these keys, and its test fails if a landmark drawn since is still listed or one with no picture is missing, here or there. To add one: draw the file, add its `PICTURES` row and its `gm_picture` icon, set its code in `gm_state_picture_landmarks`, and take its key out of the tuple and this list.

| Landmark | File to draw | Stand-in until then |
|---|---|---|
| walhalla | `landmark_walhalla__hall_of_fame.dds` | `heritage_gothic__hall_of_fame` |
| bunker_hill_monument | `landmark_bunker_hill_monument__obelisk.dds` | `generic__obelisk` |
| obelisk_of_the_second_of_may | `landmark_obelisk_of_the_second_of_may__obelisk.dds` | `generic__obelisk` |
| muhammad_ali_mosque | `landmark_muhammad_ali_mosque__faith.dds` | `faith_sunni__faith` |
| nelsons_column | `landmark_nelsons_column__column.dds` | `generic__column` |
| washington_monument | `landmark_washington_monument__obelisk.dds` | `generic__obelisk` |
| pyramids_of_giza | `landmark_pyramids_of_giza__pyramid.dds` | `generic__obelisk` |
| petra | `landmark_petra__rock_cut.dds` | `heritage_aramaic__rock_cut` |
| moscow_kremlin | `landmark_moscow_kremlin__tower.dds` | `heritage_slavonic__bell_tower` |
| fasil_ghebbi | `landmark_fasil_ghebbi__hall.dds` | `heritage_gothic__tower` |
| valley_of_the_temples | `landmark_valley_of_the_temples__pantheon.dds` | `heritage_greek__pantheon` |
| borobudur | `landmark_borobudur__gate.dds` | `heritage_sanskrit__gate` |
| old_city_of_sanaa | `landmark_old_city_of_sanaa__hall.dds` | `heritage_arabic__hall` |
| shibam | `landmark_shibam__tower.dds` | `heritage_arabic__hall` |
| amphitheatre_of_el_djem | `landmark_amphitheatre_of_el_djem__forum.dds` | `heritage_latin__stadium` |
| abu_simbel | `landmark_abu_simbel__rock_cut.dds` | `heritage_aramaic__rock_cut` |
| temple_of_seti_abydos | `landmark_temple_of_seti_abydos__colonnade.dds` | `heritage_aramaic__colonnade` |
| pyramids_of_meroe | `landmark_pyramids_of_meroe__pyramid.dds` | `generic__obelisk` |
| windsor_castle | `landmark_windsor_castle__tower.dds` | `heritage_gothic__tower` |
| pont_du_gard | `landmark_pont_du_gard__arch.dds` | `heritage_latin__arch` |
| palais_des_papes | `landmark_palais_des_papes__hall.dds` | `heritage_gothic__tower` |
| mont_saint_michel | `landmark_mont_saint_michel__tower.dds` | `heritage_gothic__tower` |
| chateau_de_chambord | `landmark_chateau_de_chambord__hall.dds` | `generic__hall` |
| jeronimos_monastery | `landmark_jeronimos_monastery__hall.dds` | `faith_catholic__faith` |
| alhambra | `landmark_alhambra__hall.dds` | `heritage_arabic__hall` |
| mezquita_of_cordoba | `landmark_mezquita_of_cordoba__hall.dds` | `faith_sunni__faith` |
| shore_temple | `landmark_shore_temple__pillar.dds` | `faith_hindu__faith` |
| charminar | `landmark_charminar__gate.dds` | `heritage_arabic__gate` |
| gwalior_fort | `landmark_gwalior_fort__gate.dds` | `heritage_sanskrit__gate` |
| meteora | `landmark_meteora__memorial_church.dds` | `faith_orthodox__faith` |
| citadel_of_aleppo | `landmark_citadel_of_aleppo__gate.dds` | `heritage_arabic__gate` |
| naqsh_e_jahan_square | `landmark_naqsh_e_jahan_square__hall.dds` | `heritage_avestan__gate` |
| buddhas_of_bamiyan | `landmark_buddhas_of_bamiyan__statue.dds` | `generic__statue` |
| musalla_of_herat | `landmark_musalla_of_herat__tower.dds` | `faith_sunni__faith` |
| grand_palace_bangkok | `landmark_grand_palace_bangkok__hall.dds` | `faith_theravada__faith` |
| changdeokgung | `landmark_changdeokgung__hall.dds` | `heritage_chinese__hall` |
| bulguksa | `landmark_bulguksa__pagoda.dds` | `heritage_chinese__pagoda` |
| kinkaku_ji | `landmark_kinkaku_ji__pagoda.dds` | `heritage_chinese__pagoda` |
| todai_ji | `landmark_todai_ji__hall.dds` | `faith_mahayana__faith` |
| itsukushima_shrine | `landmark_itsukushima_shrine__gate.dds` | `faith_shinto__faith` |
| potala_palace | `landmark_potala_palace__hall.dds` | `faith_gelugpa__faith` |
| swayambhunath | `landmark_swayambhunath__pagoda.dds` | `faith_mahayana__faith` |
| leshan_giant_buddha | `landmark_leshan_giant_buddha__statue.dds` | `generic__statue` |
| temple_of_confucius | `landmark_temple_of_confucius__hall.dds` | `faith_confucian__faith` |
| yungang_grottoes | `landmark_yungang_grottoes__rock_cut.dds` | `generic__statue` |
| humble_administrators_garden | `landmark_humble_administrators_garden__pagoda.dds` | `heritage_chinese__gardens` |
| longmen_grottoes | `landmark_longmen_grottoes__rock_cut.dds` | `generic__statue` |
| registan | `landmark_registan__gate.dds` | `heritage_avestan__gate` |
| itchan_kala | `landmark_itchan_kala__gate.dds` | `heritage_arabic__gate` |
| mausoleum_of_sultan_sanjar | `landmark_mausoleum_of_sultan_sanjar__mausoleum.dds` | `faith_sunni__faith` |
| kazan_kremlin | `landmark_kazan_kremlin__tower.dds` | `heritage_slavonic__bell_tower` |
| saint_sophia_kiev | `landmark_saint_sophia_kiev__memorial_church.dds` | `heritage_slavonic__memorial_church` |
| diocletians_palace | `landmark_diocletians_palace__colonnade.dds` | `heritage_latin__forum` |
| marksburg | `landmark_marksburg__tower.dds` | `heritage_gothic__tower` |
| aachen_cathedral | `landmark_aachen_cathedral__hall.dds` | `faith_catholic__faith` |
| basilica_of_saint_francis | `landmark_basilica_of_saint_francis__hall.dds` | `faith_catholic__faith` |
| walls_of_tallinn | `landmark_walls_of_tallinn__gate.dds` | `heritage_gothic__tower` |
| ephesus | `landmark_ephesus__colonnade.dds` | `heritage_greek__stoa` |
| tikal | `landmark_tikal__pyramid.dds` | `heritage_mayan__pyramid` |
| chichen_itza | `landmark_chichen_itza__pyramid.dds` | `heritage_mayan__pyramid` |
| teotihuacan | `landmark_teotihuacan__pyramid.dds` | `heritage_nahuatl__pyramid` |
| monte_alban | `landmark_monte_alban__pyramid.dds` | `heritage_nahuatl__pyramid` |
| leptis_magna | `landmark_leptis_magna__forum.dds` | `heritage_latin__forum` |
| cyrene | `landmark_cyrene__pantheon.dds` | `heritage_greek__pantheon` |
| merida_theatre | `landmark_merida_theatre__forum.dds` | `heritage_latin__stadium` |
| chogha_zanbil | `landmark_chogha_zanbil__pyramid.dds` | `heritage_avestan__gate` |
| hattusa | `landmark_hattusa__gate.dds` | `generic__gate` |
| mount_nemrut | `landmark_mount_nemrut__statue.dds` | `generic__statue` |
| mogao_caves | `landmark_mogao_caves__rock_cut.dds` | `faith_mahayana__faith` |
| khajuraho | `landmark_khajuraho__pillar.dds` | `faith_hindu__faith` |
| hampi | `landmark_hampi__pillar.dds` | `heritage_sanskrit__pillar` |
