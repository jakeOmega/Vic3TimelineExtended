# Grand Monument pictures, forms and styles: design

**Date:** 2026-10-11
**Status:** approved in conversation, section by section; this document is for review
**Builds on:** `2026-09-27-grand-monument-rework-design.md` (§1.1 skins, "new art per skin" deferred to a later phase), `2026-10-05-grand-monuments-v2-design.md` (§3 names and forms), `docs/systems/mod_systems.md` § Grand Monuments.

## Goal

Each Grand Monument shows a picture of what it is, in its Grand Monuments journal entry row and, larger, on the state view's monument card. The picture follows the monument's **skin and form**, so a Roman forum, a Chinese pagoda, a Sunni great mosque and a Greek-style stadium each look like themselves.

Bundled because they touch the same events and tables:

- the form roster is rebalanced: two generic forms go, seven heritage forms are added, and the five civic-progress buildings gain skins;
- the dedication ceremony shows every dedication, the unavailable ones greyed out with their reasons;
- the skin choice shows why each skin is offered.

**Success:** every dedication, skin and form combination a player can reach has its own picture, in both places. A combination with none (an old save's retired form) shows its skin's default. The choice events say what each option needs.

## 1. The model

Every monument is defined by three things:

- **Dedication**: what it is for, chosen at the ceremony (`monument_events.2`): To the Crown, To the Republic, To the Revolution, To the Leader, To the Nation, War Memorial, Grand Shrine, and the five civic-progress buildings.
- **Skin**: its style (`gm_skin`): generic (neoclassical), a heritage skin from the language-reform partition, or a faith's building.
- **Form**: its shape, the noun in its name (`gm_form`).

The two are separate: a War Memorial (dedication) can take the form of a Hall.

Every dedicated monument has all three. Some have no choice of form:

- a faith skin's one form is its building;
- each civic-progress building's one form is the building itself.

An undedicated monument has none of the three yet.

**Player-facing words.** The script says *skin*; players see **style**. The style choice event (`monument_events.11`) is retitled from "A Form for the Monument" to "A Style for the Monument". Its tooltip reads "The monument takes this style…", and for a civic-progress building "…changes its look, not its name or what it does". The form choice (`.24`, "The Form It Takes") keeps its title. The player guide uses dedication, style and form throughout.

## 2. The roster

### 2.1 Which styles and forms each dedication offers

| Dedication | Styles (skins) | Forms |
|---|---|---|
| Crown, Republic, Revolution, Leader, Nation, War Memorial | generic, or the country's heritage skin(s) | generic: §2.2; heritage: §2.3 |
| Grand Shrine | the state religion's faith skin, or generic (mod religions fall back to heritage, as today) | faith: 1, its building; generic: §2.2 |
| Grand Opera House, Botanical Gardens, Grand Observatory, Great Exhibition Hall, Grand Stadium | generic, plus the heritage skins listed for the building (§2.4) | 1: the building |

### 2.2 Generic forms

Column, Arch, Obelisk, Statue, Gate, Hall, plus Mausoleum (offered only for a late ruler's commission, as today).

- **Removed: Tower and Memorial.** Tower survives as the Gothic skin's form. Memorial was generic-only.
- **Existing monuments keep their form and name.** Their picture falls back to the generic default, the Column (§3.3).
- **The defeat commission** (`gm_commission_effects.txt`, `SOURCE = defeat`) asks for Hall instead of Memorial.
- **Column against Obelisk** is decided on the review sheet. The two pictures are briefed to look clearly different: a fluted column carrying a bronze figure, against a plain tapered shaft with a pointed tip. If they still look alike at row size, Obelisk merges into Column, and the commissions that ask for Obelisk ask for Column.

### 2.3 Heritage forms

Added forms are in bold.

| Skin | Forms (default first) |
|---|---|
| Latin | Column, Arch, Forum |
| Greek | Pantheon, Column, Stoa |
| Slavonic | Memorial Church, Column, **Bell Tower** |
| Hebrew | Gate, Court, Pillar, **Menorah** |
| Sanskrit | Pillar, Gate |
| Avestan | Gate, Hall |
| Arabic | Hall, Gate |
| Chinese | Hall, Gate, Pagoda |
| Norse | Rune Stone, Hall |
| Gothic | Hall of Fame, Tower |
| Ge'ez | Stele, **Rock-Hewn Church** |
| Irish | Round Tower, High Cross |
| Nahuatl | Pyramid, **Sun Stone** |
| Mayan | Pyramid, **Stela** |
| Prussian | Hill Shrine, **Sacred Oak** |
| Aramaic | Rock-Cut Monument, **Colonnade** |

The defaults are unchanged (`DEFAULT_FORM` in the registry test). Each added form needs:

- a `gm_state_form_fits_<form>` trigger;
- a `.24` option;
- its `gm_form_<form>` name loc and its branch in `gm_form_name`;
- its row in `FORMS`.

Two of the additions fix a mismatch: the skin's name promised a form that none of its options offered ("Great Menorah", "Memorial Bell Tower"). Pali and Coptic keep reusing the Theravada and Oriental Orthodox faith skins.

### 2.4 Styles for the civic-progress buildings

| Building | Generic, plus |
|---|---|
| Grand Opera House | Greek (an open-air theatre), Chinese (an opera stage pavilion) |
| Botanical Gardens | Chinese (a scholar's garden), Avestan (a Persian charbagh), Arabic (an Andalusian courtyard garden) |
| Grand Observatory | Sanskrit (a Jantar Mantar), Avestan (a Samarkand-style observatory), Chinese (an ancient observatory platform), Mayan (a round Caracol tower) |
| Great Exhibition Hall | none (the glass-and-iron palace is the type) |
| Grand Stadium | Latin (an amphitheatre arena), Greek (a horseshoe stadium), Mayan and Nahuatl (a ball court) |

**Offering a style.** A civic-progress dedication now offers the styles its building lists. The new skin axis, `building`, replaces `none` in `gm_state_dedicate_timeless` for these five. It is offered only when the country has one of the listed heritages. The AI takes the most specific style, as for the other axes.

**The style changes the look only:**

- The form stays the building, so the name is unchanged.
- Where a name falls back to the skin's name (`gm_name_skin_row` / `_evt`, the last branch of the name patterns), a civic-progress building shows its building's name. A Greek stadium is still the Grand Stadium, never "Pantheon".

## 3. Pictures

### 3.1 Inventory: 80 pictures

| Group | Pictures |
|---|---|
| Undedicated: the monument draped in cloth before its unveiling | 1 |
| Generic political forms (§2.2) | 7 |
| Heritage skin and form pairs (§2.3) | 38 |
| Faith buildings (Basilica, Cathedral, Orthodox Cathedral, Great Church, Great Mosque (Sunni), Shrine Mosque, Great Mosque (Ibadi), Great Temple, Pagoda, Great Monastery, Great Stupa, Temple of Confucius, Temple Complex, Grand Shrine, Gurdwara, Sacred Grove) | 16 |
| Civic-progress buildings: 5 generic and 13 styled (§2.4) | 18 |

**Style.** The framed building-icon diorama (256 px, the pipeline's `building` look), as the Grand Monument's own icon is drawn. A new GUI-hosted pipeline category, `gm_picture`, writes `gfx/interface/icons/gm_pictures/<skin>__<form>.dds`; the undedicated picture is `undedicated.dds`. Review is the usual sheets with picks marked, about five of them.

**Archetypes, never holy sites.** A faith or heritage picture shows the tradition's building type, not a specific real sacred site. The Great Temple is a grand synagogue, not the Temple. The Gurdwara is a white-domed gurdwara by a pool, not the Golden Temple. The Shrine Mosque is a golden-domed shrine, not a named one. This follows the v1 spec's rule that a landmark never sits on, or names, a site another faith holds.

### 3.2 The picture number

`gm_picture_code`, a state variable on the monument's state, numbers the picture. Codes come from the `PICTURES` table in `test_grand_monument_registry.py` and are **append-only**: a retired pair keeps its number and is never reused, so a save's stored code never points at the wrong picture.

| Codes | Group |
|---|---|
| 1 | undedicated (draped) |
| 10–19 | generic political forms |
| 100–259 | heritage: one block of ten per skin, in `HERITAGE_SKINS` order |
| 300–315 | faith buildings, in `FAITHS` order |
| 400–449 | civic-progress buildings: a block of ten per building (Opera House, Gardens, Observatory, Exhibition Hall, Stadium), +0 for generic |

### 3.3 Setting it

**The helper.** One helper, `gm_state_update_picture` (state scope), sets the code from `gm_skin`, `gm_form` and the dedication.

- It runs at the end of every effect that sets or clears `gm_skin` or `gm_form`, about a dozen sites in `gm_effects.txt` and `gm_name_effects.txt`.
- It also runs on every monument state in the national refresh (`gm_country_refresh`, beside `gm_state_name_if_unnamed`). That fills in old saves and repairs any drift.

**The rules:**

- Undedicated → 1.
- A pair in the table → its code.
- A pair not in the table (an old save's generic Tower or Memorial) → the code of its skin's default form. For generic that is the Column.
- A civic-progress building on a skin its building doesn't list → that building's generic picture.

### 3.4 Showing it

**One type, used twice.** `gm_picture`, a type in `grand_monuments_widget.gui`, lists every picture once: an `icon` per code, each `visible` on `EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_picture_code'), '(CFixedPoint)<code>' )`. `gm_disp_picture_code` (`gm_values.txt`) only reads the stored code, or gives 1 (draped) while there is none. A raw `Var(…).GetValue` inside a `visible` comparison is unproven in this repo; a script value there is the status icons' proven form. The instance sets its size, and each icon fills it at 100%.

This is the pattern the row's four status icons already use, and each widget reads one stored number. Building the path from script (`Concatenate`) was rejected, because vanilla never builds a texture path that way, so it is unproven in game. Computing the number in a script value was also rejected, because it would run an 80-branch chain per widget per frame.

**The journal entry row.** The picture fills the row's 96 px left column. The status icon shrinks to a badge over its top-left corner, and the status word stays under the picture.

**The state card** (`te_state_gm_card`). The picture shows at about 128 px at the card's left, with the same badge.

**Contested and heritage monuments** keep their picture; the badge tells their status.

### 3.5 Grandeur frames (owner, 2026-10-11)

The picture's frame shows the monument's grandeur step, the same steps its effects use (the first at 5 grandeur, each further one twice as large):

| Step | Grandeur (level) | Frame |
|---|---|---|
| 0 | 1–4 | plain (the picture's own frame) |
| 1 | 5–14 | bronze |
| 2 | 15–34 | bronze, with a silver inner line |
| 3 | 35–74 | silver, with a gold inner line |
| 4 | 75–154 | gold |
| 5+ | 155+ | gold, with four gem studs |

- **Every monument shows its tier**, undedicated ones included, since the frame is about grandeur, not the dedication.
- **What the frames are.** Five overlays, `gm_pictures/frames/frame_tier_<1-5>.dds`, drawn over the picture inside the `gm_picture` type, so the row and the card both get them.
- **How they are made.** A generator recolours the frame band the pictures were composed with: vanilla's building-icon frame, widened by a few pixels so the metal still reads at 96 px. Each tier covers the baked frame exactly.
- **What drives them.** `gm_disp_frame_tier` reads the live level against the step thresholds of `gm_state_disp_next_step`, the state card's own list.

## 4. Events

### 4.1 The ceremony (`monument_events.2`)

**Every dedication shows.** Each dedication option gets `show_as_unavailable = { always = yes }`. All twelve dedications then always show, and the ones the country can't take are greyed out with each failing condition crossed. The commission, AI-weight and Undedicated options are unchanged.

**Conditions players can read.** Every gate is native underneath:

- the technologies: Romanticism, Empiricism, Marketing Research, Television Broadcasting;
- "not State Atheism" and "industry not banned";
- the four government gates, which are lists of laws in `monument_triggers.txt`:

| Dedication | Trigger | Conditions |
|---|---|---|
| To the Crown | `monument_government_is_crowned` | Monarchy, Social Monarchy or Chiefdom |
| To the Republic | `monument_government_is_republican` | Presidential, Parliamentary or Council Republic, or Direct Democracy |
| To the Revolution | `gm_government_is_revolutionary` | Single-Party State or Council Republic |
| To the Leader | `gm_can_raise_leader_monument` | Autocracy or Single-Party State, and not crowned |

A scripted trigger's tooltip expands to its conditions unless it has a loc key of its own, so the law lists should draw as "one of" lines with the laws' names, live. The in-game check confirms they do. If one draws as a raw trigger name instead, it gets a `custom_tooltip` with the sentence in the table.

### 4.2 The style choice (`monument_events.11`)

**Each style says why it is offered.** Every skin option gets `highlighted_option = yes`, so its tooltip shows its own trigger, live. The internal `var:gm_skin_axis` test moves into `hidden_trigger = { }`, so the tooltip shows only the heritage or faith condition: "a primary culture of the Romance language group", or "Jewish state religion, or a primary culture of the Semitic language group". The generic option has no trigger and is not highlighted.

**The civic-progress styles.** There are 13 new options, one per pair in §2.4. Each is worded as the building in that style ("A Greek open-air theatre"), gated on the building's dedication and the heritage, and highlighted the same way.

### 4.3 The form choice (`monument_events.24`)

There are seven new options, one per added form. The generic skin stops offering Tower and Memorial, through their fit triggers. Old monuments are not migrated.

## 5. Testing

**The registry test** (`test_grand_monument_registry.py`). A new `PICTURES` table maps code to (skin, form) or to undedicated. The test fails unless:

- every reachable pair (from `FORMS`, the faith skins and the §2.4 table) has a code;
- every code has its widget in `gm_picture`, its branch in `gm_state_update_picture`, and an entry in the pipeline registry's `gm_picture` category;
- codes are unique and never reused.

`FORMS`, `DEFAULT_FORM` and `BUILDING_FORMS` gain the new rows and lose generic Tower and Memorial. A new `BUILDING_SKINS` table drives the `.11` options and the axis.

**The layout test** (`test_grand_monuments_layout.py`) pins the picture's place in the row and on the card.

**Static checks:** `check_gui_lint.py`, `gui_reference_audit --strict`, `loc_coverage_audit --strict`, `script_argument_audit --strict`, `organize_loc.py --check`, `icon_prompts.py --validate`, and the full unittest suite.

**A debug option** in `te_debug_monuments_events.txt` sets the capital's monument to any skin and form. Every picture can then be checked in game without playing each culture.

## 6. Player guide

`02-timeline.md`, § "Monument names and forms" (and § "Monument dedications" for the greyed options):

- use dedication, style and form;
- say that each monument shows a picture of its style and form;
- say that civic-progress buildings can take a style;
- say that unavailable dedications show greyed out with their reasons;
- name the new forms where the section lists them.

Check `17-reference.md` for a form list. Rebuild the PDF.

## 7. In-game checks

1. The row and card pictures: undedicated (draped), a generic Column, a heritage pair, a faith building, a styled civic building. Use the debug option to sweep the rest.
2. An old save: pictures appear after the first monthly refresh, and a generic Tower or Memorial monument shows the Column.
3. `.2`: every dedication shows; unavailable ones are greyed with readable reasons.
4. `.11`: each highlighted style shows only its heritage or faith condition. A country with a listed heritage gets the style choice for that civic building.
5. A Greek-style Grand Stadium is still named the Grand Stadium.
6. `.24` offers the new forms for their styles and no longer offers Tower or Memorial on the generic style.
7. The defeat commission asks for a Hall.
8. `debug.log` has no new GUI or script errors.

## Out of scope

- **The building panel's icon.** The engine draws one icon per building type.
- **Event pictures per style** (the ceremony and style events' images).
- **Named landmarks** (v1 §1.1, phase 2).
- **More than one form for a faith skin.**
