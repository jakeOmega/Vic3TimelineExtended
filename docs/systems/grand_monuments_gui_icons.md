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

None at the moment: every landmark has its own picture.
