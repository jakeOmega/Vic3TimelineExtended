# Grand Monument Pictures, Forms and Styles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Grand Monument shows a picture of its skin and form in its journal entry row and, larger, on the state card. The form roster is rebalanced, the five civic-progress buildings gain styles, the ceremony shows every dedication greyed or not, and the style choice shows why each style is offered.

**Architecture:**
- **The picture number.** A state variable, `gm_picture_code`, numbers the picture. One helper (`gm_state_update_picture`) sets it from `gm_skin` and `gm_form` wherever those change, and the monthly refresh repeats it. The GUI's `gm_picture` type holds one icon per code, each `visible` on the display value `gm_disp_picture_code`.
- **The art.** 80 framed diorama pictures from the FLUX icon pipeline, in a new GUI-hosted category.
- **The checks.** Every table that lists forms, skins or pictures by hand is pinned by `test_grand_monument_registry.py`.

**Tech Stack:**
- Paradox script: scripted effects and triggers, events, customizable localization, `.gui`;
- Python unittest;
- the FLUX icon pipeline (`scripts/image_pipeline/`, `.venv-img`).

**Spec:** `docs/superpowers/archive/specs/2026-10-11-grand-monument-pictures-design.md`

## Global Constraints

- Work in `~/src/vic3te-gm-pictures` (branch `feat/gm-pictures`, sparse checkout: everything except `gfx/` plus `gfx/interface/icons/`). Never `POST /reload` the :8950 server from here: it regenerates the main checkout.
- Brace-based `.txt` and `.gui` files use **tab** indentation and keep their single UTF-8 BOM. Check with `head -c3 <file> | xxd`: it must print `efbb bf` once.
- Run tests with the main checkout's venv: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest <module>`. Read the result with `grep -E '^(Ran |OK|FAILED)'`, never `| tail`.
- Loc keys: add them to the file named in the step, then run `python3 organize_loc.py` and commit whatever it moves.
- **Player-facing words:** dedication, **style** (the script's *skin*), form. `monument_events.11` is titled "A Style for the Monument".
- **Picture codes are append-only.** Never renumber or reuse a code. The table is in Task 6.
- Picture files: `gfx/interface/icons/gm_pictures/<skin>__<form>.dds` (faith: `faith_<religion>__faith.dds`; undedicated: `undedicated.dds`). 256 px, framed building-icon diorama.
- Faith and heritage pictures show archetypes, never a specific real holy site.
- Commit messages end with the attribution trailer. The commit commands below pass it as `-m "$TRAILER"`; define it in the same shell command (shell state does not persist between commands):
  ```bash
  TRAILER=$'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_0196REfdbxSAMwkz1HQW3YL6'
  ```
- Never `git commit -a`. Stage by path.

## Review Focus

1. **An old save before its first refresh.** A monument with no `gm_picture_code` shows the draped picture. Its real picture appears at the next monthly refresh, never a blank. Task 6 pins `gm_disp_picture_code`'s default of 1.
2. **An old monument on a retired form** (generic Tower or Memorial). It shows the generic Column. Task 6 pins that the skin defaults come before the pairs.
3. **A demolished or rebuilt monument.** It goes back to the draped picture, not the old one. Task 6 pins `gm_clear_state` removing `gm_picture_code`.
4. **An expired style event** (`.11` has no default option, so the first valid option is taken). A civic-progress building takes its most specific listed heritage, never "Keep to the plain classical style" ahead of it. Task 3 pins the option order.
5. **Rename** (`gm_rename_sgui` → `.24` → a new form). The picture follows the new form. Task 6 pins the update call in `gm_state_choose_form`.

## Execution Order

The art is the long pole: about 1.5 GPU hours, then the owner's review. It needs only Task 1 and the subjects, so it runs while the script work goes on:

1. Task 1.
2. Task 9, Steps 3–5: register the 80 subjects, then start the render. Wait for any other FLUX process to exit first (`nvidia-smi`); two never share the 10 GB card. The subjects' keys are spelled out in Task 9's table, so they don't wait for `PICTURES`. Leave Task 9's test out until Task 6 has defined `PICTURES`.
3. Tasks 2–8 while it renders.
4. Task 9's test, Steps 6–7 (review and write), then Tasks 10–11.

---

### Task 1: Pipeline: framed GUI-hosted category with a borrowed frame

The `framed` mode lifts its frame from the vanilla folder named by `folder`, and there is no vanilla `gm_pictures` folder. Add a `template_folder` key, then define the `gm_picture` category (entries come in Task 9).

**Files:**
- Modify: `scripts/image_pipeline/icon_render.py` (`Composer.compose`, the `vanilla_template` call near line 1760)
- Modify: `scripts/image_pipeline/icon_prompts.py` (a `BUILDING_STYLE` constant used by `"building"`; a new `"gm_picture"` category after `"building"`; an empty `"gm_picture": {}` in `ICONS`)
- Test: `test_icon_pipeline.py`

**Interfaces:**
- Produces: `CATEGORIES["gm_picture"]` with `folder="gm_pictures"`, `size=256`, `mode="framed"`, `template_folder="building_icons"`, `neighbours="building_icons"`, `gui=("gui/journal_entry_widgets/grand_monuments_widget.gui", "gui/te_state_panel_widgets.gui")`, `style=BUILDING_STYLE`. Task 9 fills `ICONS["gm_picture"]`.

- [ ] **Step 1: Write the failing test** (append to `test_icon_pipeline.py`)

```python
class TemplateFolderTests(unittest.TestCase):
    """A framed category with no vanilla folder of its own borrows another's frame."""

    def test_framed_template_comes_from_template_folder(self):
        try:
            import icon_render
        except ImportError:
            self.skipTest("Pillow/numpy are not installed")
        seen = []
        saved = icon_render.vanilla_template
        icon_render.vanilla_template = lambda folder, size: seen.append((folder, size)) or ("t", "s")
        saved_framed = icon_render.compose_framed
        icon_render.compose_framed = lambda raw, spec, tmpl: tmpl
        try:
            from PIL import Image
            c = icon_render.Composer()
            out = c.compose(Image.new("RGB", (8, 8)), "gm_picture",
                            {"mode": "framed", "folder": "gm_pictures", "template_folder": "building_icons",
                             "size": 256})
        finally:
            icon_render.vanilla_template = saved
            icon_render.compose_framed = saved_framed
        self.assertEqual(seen, [("building_icons", 256)])
        self.assertEqual(out, ("t", "s"))

    def test_gm_picture_category(self):
        spec = ip.CATEGORIES["gm_picture"]
        self.assertEqual((spec["folder"], spec["size"], spec["mode"]), ("gm_pictures", 256, "framed"))
        self.assertEqual(spec["template_folder"], "building_icons")
        self.assertEqual(spec["style"], ip.CATEGORIES["building"]["style"])
        self.assertIn("gui/journal_entry_widgets/grand_monuments_widget.gui", spec["gui"])
```

- [ ] **Step 2: Run it to see it fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_icon_pipeline.TemplateFolderTests 2>&1 | grep -E '^(Ran |OK|FAILED)|Error'`
Expected: FAILED (`KeyError: 'gm_picture'`, and the template folder is `gm_pictures`)

- [ ] **Step 3: Implement**

In `icon_render.py`, `Composer.compose`, replace

```python
        if mode in ("framed", "medallion", "emboss_medallion") and cat not in self._tmpl:
            self._tmpl[cat] = vanilla_template(spec["folder"], spec["size"])
```

with

```python
        if mode in ("framed", "medallion", "emboss_medallion") and cat not in self._tmpl:
            # A category with no vanilla folder of its own (the Grand Monument
            # pictures) borrows another folder's frame.
            self._tmpl[cat] = vanilla_template(spec.get("template_folder", spec["folder"]), spec["size"])
```

In `icon_prompts.py`:

- Above `CATEGORIES = {`, add:

```python
# The framed diorama of vanilla's building icons, also the Grand Monument pictures'.
BUILDING_STYLE = ("aerial three-quarter view of {subject}, detailed painted illustration "
                  "of a miniature diorama, warm golden afternoon light, muted earthy "
                  "palette, surrounding landscape, the building fills the center of the image")
```

- In `"building": dict(...)`, replace its inline `style=(...)` with `style=BUILDING_STYLE`. The text is identical, so cached renders stay valid.
- After the `"building"` category, add:

```python
    # Grand Monument pictures (spec 2026-10-11): one per style and form, shown in
    # the journal entry's monument rows and on the state card through the
    # gm_picture type, so GUI-hosted (keys are file names, written to
    # gm_pictures/<key>.dds). Framed like the building icons, whose frame and
    # neighbours they borrow: there is no vanilla gm_pictures folder.
    "gm_picture": dict(
        folder="gm_pictures", size=256, mode="framed", template_folder="building_icons",
        neighbours="building_icons",
        gui=("gui/journal_entry_widgets/grand_monuments_widget.gui", "gui/te_state_panel_widgets.gui"),
        style=BUILDING_STYLE),
```

- At the end of `ICONS` (before its closing `}`), add `"gm_picture": {},` with the comment `# Grand Monument pictures: Task 9 of the 2026-10-11 plan.` (Icon batch 5, on its own branch, also appends categories there; whichever lands second resolves a trivial conflict by keeping both.)

- [ ] **Step 4: Run the pipeline tests and the registry check**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_icon_pipeline 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 scripts/image_pipeline/icon_prompts.py --validate | tail -1` → `Errors: 0`

- [ ] **Step 5: Commit**

```bash
git add scripts/image_pipeline/icon_render.py scripts/image_pipeline/icon_prompts.py test_icon_pipeline.py
git commit -m "Icon pipeline: framed GUI-hosted categories borrow a frame (template_folder); gm_picture category" -m "$TRAILER"
```

---

### Task 2: The form roster

Retire generic Tower and Memorial, and add seven heritage forms. The defeat commission asks for a Hall.

**Files:**
- Modify: `test_grand_monument_registry.py` (`FORMS`, a new `RETIRED_FORMS`, `COMMISSION_SOURCES`, `NameTests`)
- Modify: `common/scripted_triggers/gm_name_triggers.txt` (`gm_state_form_fits_tower`, delete `gm_state_form_fits_memorial`, seven new `gm_state_form_fits_<form>`, `gm_state_has_form_choice`, `gm_state_com_form_fits`, `gm_state_current_form_fits`)
- Modify: `common/scripted_effects/gm_commission_effects.txt:802` (`FORM = memorial` → `FORM = hall`)
- Modify: `events/monument_events.txt` (`monument_events.24`: delete the `memorial` option; add seven options)
- Modify: `common/customizable_localization/gm_custom_loc.txt` (`gm_form_name`: seven branches before `gm_form_opera_house`'s; keep `memorial`'s)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_form_<new>`), `localization/english/te_events_l_english.yml` (`monument_events.24.<new>`)

**Interfaces:**
- Produces: forms `menorah`, `bell_tower`, `rock_hewn_church`, `sun_stone`, `stela`, `sacred_oak`, `colonnade` (the flag names Task 6's picture table uses).

- [ ] **Step 1: Update the tables (the failing tests)**

In `test_grand_monument_registry.py`, replace `FORMS = {...}` with:

```python
FORMS = {
    "column": ("generic", "heritage_latin", "heritage_greek", "heritage_slavonic"),
    "arch": ("generic", "heritage_latin"),
    "obelisk": ("generic",), "statue": ("generic",), "mausoleum": ("generic",),
    "gate": ("generic", "heritage_hebrew", "heritage_sanskrit", "heritage_avestan", "heritage_arabic",
             "heritage_chinese"),
    "hall": ("generic", "heritage_avestan", "heritage_arabic", "heritage_chinese", "heritage_norse"),
    # Generic dropped the tower (spec 2026-10-11 §2.2); the Gothic skin keeps it.
    "tower": ("heritage_gothic",),
    "forum": ("heritage_latin",), "pantheon": ("heritage_greek",), "stoa": ("heritage_greek",),
    "court": ("heritage_hebrew",), "pillar": ("heritage_hebrew", "heritage_sanskrit"),
    "stele": ("heritage_geez",), "memorial_church": ("heritage_slavonic",), "pagoda": ("heritage_chinese",),
    "round_tower": ("heritage_irish",), "high_cross": ("heritage_irish",),
    "pyramid": ("heritage_nahuatl", "heritage_mayan"), "rune_stone": ("heritage_norse",),
    "hall_of_fame": ("heritage_gothic",), "hill_shrine": ("heritage_prussian",), "rock_cut": ("heritage_aramaic",),
    # Added 2026-10-11 (§2.3).
    "menorah": ("heritage_hebrew",), "bell_tower": ("heritage_slavonic",),
    "rock_hewn_church": ("heritage_geez",), "sun_stone": ("heritage_nahuatl",), "stela": ("heritage_mayan",),
    "sacred_oak": ("heritage_prussian",), "colonnade": ("heritage_aramaic",),
}
# Forms no skin offers any more. An old monument keeps one, so its noun and its
# gm_form_name branch stay; its fit trigger and .24 option go.
RETIRED_FORMS = ("memorial",)
```

In `COMMISSION_SOURCES`, change the defeat row to `Source("defeat", "war_memorial", "occasion", "hall", False),`.

Add to `NameTests`:

```python
    def test_retired_forms_keep_their_noun_only(self):
        L = loc()
        names = squash(block(self.custom, "gm_form_name"))
        ev = squash(raw_block_at(self.events, r"(?m)^monument_events\.24\s*=\s*\{"))
        com = squash(block(self.t, "gm_state_com_form_fits"))
        for form in RETIRED_FORMS:
            self.assertIn(f"gm_form_{form}", L, form)
            self.assertIn(f"var:gm_form = flag:{form} }} localization_key = gm_form_{form}", names, form)
            self.assertIsNone(block(self.t, f"gm_state_form_fits_{form}"), form)
            self.assertNotIn(f"monument_events.24.{form} ", ev + " ", form)
            self.assertNotIn(f"flag:{form} ", com, form)

    def test_current_form_check_knows_every_form(self):
        # gm_state_unveil keeps a commission's form only while it fits: a form
        # missing here reads as not fitting, and the unveiling resets it.
        cur = squash(block(self.t, "gm_state_current_form_fits"))
        for form in list(FORMS) + list(BUILDING_FORMS.values()) + ["faith"]:
            self.assertIn(f"var:gm_form = flag:{form} gm_state_form_fits_{form} = yes", cur, form)
        for form in RETIRED_FORMS:
            self.assertNotIn(f"flag:{form} ", cur, form)
        # No call to a fit trigger that no longer exists.
        for rel in (NAME_TRIGGERS, NAME_EFFECTS, EVENTS, EFFECTS):
            for form in RETIRED_FORMS:
                self.assertNotIn(f"gm_state_form_fits_{form} ", strip_comments(read(rel)), (rel, form))

    def test_commission_forms_fit_some_skin(self):
        com = squash(block(self.t, "gm_state_com_form_fits"))
        for s in COMMISSION_SOURCES:
            if s.form != "default":
                self.assertIn(f"var:gm_com_form = flag:{s.form} }} gm_state_form_fits_{s.form} = yes", com, s.key)
```

- [ ] **Step 2: Run them to see them fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)|^(FAIL|ERROR):'`
Expected: FAILED. The failures include `test_form_triggers_match_the_table` (tower lists generic; the new forms have no trigger), `test_every_form_has_its_noun_and_option`, `test_form_choice_lists_the_skins_with_two_or_more`, `test_retired_forms_keep_their_noun_only` and the commission source tests.

- [ ] **Step 3: Triggers** (`gm_name_triggers.txt`)

Replace `gm_state_form_fits_tower`'s body:

```
gm_state_form_fits_tower = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_gothic GENERIC = no }
}
```

Delete the whole `gm_state_form_fits_memorial = { ... }` block. Then remove every reference to it (`git grep -n "form_fits_memorial "` lists them; `memorial_church` is a different form):
- in `gm_state_com_form_fits`, delete `AND = { owner = { var:gm_com_form = flag:memorial } gm_state_form_fits_memorial = yes }`;
- in `gm_state_current_form_fits`, delete `AND = { var:gm_form = flag:memorial gm_state_form_fits_memorial = yes }`;
- the `.24` option is deleted in Step 5.

In `gm_state_current_form_fits`, after the `rock_cut` line, add one line per new form:

```
		AND = { var:gm_form = flag:menorah gm_state_form_fits_menorah = yes }
		AND = { var:gm_form = flag:bell_tower gm_state_form_fits_bell_tower = yes }
		AND = { var:gm_form = flag:rock_hewn_church gm_state_form_fits_rock_hewn_church = yes }
		AND = { var:gm_form = flag:sun_stone gm_state_form_fits_sun_stone = yes }
		AND = { var:gm_form = flag:stela gm_state_form_fits_stela = yes }
		AND = { var:gm_form = flag:sacred_oak gm_state_form_fits_sacred_oak = yes }
		AND = { var:gm_form = flag:colonnade gm_state_form_fits_colonnade = yes }
```

`gm_state_com_form_fits` and `gm_state_current_form_fits` keep their `tower` lines: the trigger still exists, for the Gothic style.

After `gm_state_form_fits_rock_cut`, add:

```
# Added 2026-10-11 (spec §2.3): a second form for the one-form heritage skins,
# and the forms the Hebrew and Slavonic skins' names promised.
gm_state_form_fits_menorah = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_hebrew GENERIC = no }
}

gm_state_form_fits_bell_tower = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_slavonic GENERIC = no }
}

gm_state_form_fits_rock_hewn_church = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_geez GENERIC = no }
}

gm_state_form_fits_sun_stone = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_nahuatl GENERIC = no }
}

gm_state_form_fits_stela = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_mayan GENERIC = no }
}

gm_state_form_fits_sacred_oak = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_prussian GENERIC = no }
}

gm_state_form_fits_colonnade = {
	gm_state_takes_monument_forms = yes
	gm_state_skin_is = { SKIN = heritage_aramaic GENERIC = no }
}
```

In `gm_state_has_form_choice`'s `OR`, append (after `heritage_gothic`):

```
		gm_state_skin_is = { SKIN = heritage_geez GENERIC = no }
		gm_state_skin_is = { SKIN = heritage_nahuatl GENERIC = no }
		gm_state_skin_is = { SKIN = heritage_mayan GENERIC = no }
		gm_state_skin_is = { SKIN = heritage_prussian GENERIC = no }
		gm_state_skin_is = { SKIN = heritage_aramaic GENERIC = no }
```

- [ ] **Step 4: Commission** (`gm_commission_effects.txt:802`)

Change `FORM = memorial` to `FORM = hall`. Then grep the commission's loc for wording that names the form: `grep -n "gm_com.*defeat" localization/english/*.yml`. Change only a line that says the *form* "memorial". "War Memorial" is the dedication and stays.

- [ ] **Step 5: Event options** (`monument_events.24`)

Delete the `option = { name = monument_events.24.memorial ... }` block. After the last heritage option (`rock_cut`), add one block per new form, in the order menorah, bell_tower, rock_hewn_church, sun_stone, stela, sacred_oak, colonnade. Each has exactly this shape (shown for `menorah`):

```
	option = {
		name = monument_events.24.menorah
		trigger = {
			gm_state_form_fits_menorah = yes
			has_variable = gm_form
			NOT = { var:gm_form = flag:menorah }
			owner = scope:monument_owner
		}
		gm_state_choose_form = { FORM = menorah }
		hidden_effect = { trigger_event = { id = monument_events.25 } }
	}
```

- [ ] **Step 6: Names** (`gm_form_name` in `gm_custom_loc.txt`)

Before the `flag:opera_house` branch, add seven branches of this shape (shown for `menorah`):

```
	text = {
		trigger = { has_variable = gm_form var:gm_form = flag:menorah }
		localization_key = gm_form_menorah
	}
```

Leave `flag:memorial`'s branch in place.

- [ ] **Step 7: Loc**

`te_miscellaneous_l_english.yml`, beside the other `gm_form_*`:

```
 gm_form_menorah:0 "Menorah"
 gm_form_bell_tower:0 "Bell Tower"
 gm_form_rock_hewn_church:0 "Rock-Hewn Church"
 gm_form_sun_stone:0 "Sun Stone"
 gm_form_stela:0 "Stela"
 gm_form_sacred_oak:0 "Sacred Oak"
 gm_form_colonnade:0 "Colonnade"
```

`te_events_l_english.yml`, beside the other `monument_events.24.*` (the option names repeat the noun, as `monument_events.24.rock_cut` does):

```
 monument_events.24.menorah:0 "Menorah"
 monument_events.24.bell_tower:0 "Bell Tower"
 monument_events.24.rock_hewn_church:0 "Rock-Hewn Church"
 monument_events.24.sun_stone:0 "Sun Stone"
 monument_events.24.stela:0 "Stela"
 monument_events.24.sacred_oak:0 "Sacred Oak"
 monument_events.24.colonnade:0 "Colonnade"
```

Delete `monument_events.24.memorial`. Keep `gm_form_memorial`.

- [ ] **Step 8: Run the tests**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 organize_loc.py && git status --short localization/`. Stage whatever it moved.
Run: `python3 script_argument_audit.py --strict; python3 loc_coverage_audit.py --strict; python3 empty_effect_audit.py --strict` → each exits 0 (prefix `VIC3_*` dummies if they complain: `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`).

- [ ] **Step 9: Commit**

```bash
git add test_grand_monument_registry.py common/scripted_triggers/gm_name_triggers.txt common/scripted_effects/gm_commission_effects.txt events/monument_events.txt common/customizable_localization/gm_custom_loc.txt localization/english/
git commit -m "Grand Monuments: generic drops Tower and Memorial; seven heritage forms; the defeat commission asks for a Hall" -m "$TRAILER"
```

---

### Task 3: Styles for the civic-progress buildings

**Files:**
- Modify: `test_grand_monument_registry.py` (a new `BUILDING_SKINS` table, `wrapper_call`, `SkinTests`)
- Modify: `events/monument_events.txt` (the five `AXIS = none` calls at lines ~401–515 → `AXIS = building_<key>`; `.11`: 13 new options before `generic`)
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_state_offer_skins_building_<key>` ×5, `gm_state_offer_building_skins`, `gm_state_default_building_skin_<key>` ×5, `gm_state_choose_building_skin`, `gm_state_set_default_skin`)
- Modify: `common/customizable_localization/gm_custom_loc.txt` (`gm_skin_name`: five building branches first)
- Modify: `localization/english/te_events_l_english.yml` (13 option names), `localization/english/te_miscellaneous_l_english.yml` (`gm_skin_choice_building_tt`)

**Interfaces:**
- Consumes: `gm_state_try_heritage_skin = { H = <heritage> }` (exists), `gm_state_unveil` (exists).
- Note: `hidden_trigger` is a valid engine key (`docs/engine/effect_trigger_valid_keys.txt`), but this is the mod's first use in an event option's trigger, and vanilla's events have none. The in-game check (Task 11) confirms the axis line stays hidden.
- Produces: the skin-axis flag `flag:building`; `gm_state_choose_building_skin = { SKIN = <skin> }`; style pairs (building form, `heritage_<h>`) that Task 6's picture table uses.

- [ ] **Step 1: The table and the failing tests**

Add after `BUILDING_FORMS`:

```python
# The heritage styles each civic-progress building offers beyond generic (spec
# 2026-10-11 §2.4), in the revival partition's order (HERITAGES): the first is
# the most specific, so it is the AI's pick and comes first in .11.
BUILDING_SKINS = {
    "artistic": ("chinese", "greek"),
    "naturalist": ("avestan", "arabic", "chinese"),
    "scientific": ("sanskrit", "avestan", "chinese", "mayan"),
    "industrial": (),
    "athletic": ("latin", "greek", "nahuatl", "mayan"),
}
```

Check the order against `HERITAGES` (latin, hebrew, sanskrit, geez, slavonic, pali, avestan, arabic, chinese, greek, irish, coptic, nahuatl, norse, gothic, mayan, …). Each tuple must be a subsequence of it. Add `self.assertEqual(list(v), [h for h in HERITAGES if h in v])` in the test below.

Change `wrapper_call`'s last two lines to:

```python
    axis = "heritage" if d.key in HERITAGE_SKINNED else f"building_{d.key}"
    return f"gm_state_dedicate_timeless = {{ KEY = {d.key} AXIS = {axis} }}"
```

In `SkinTests.test_an_option_per_skin_generic_last`, change `expected` to put the building options between the heritage options and `generic`:

```python
        building = [f"building_{k}_{h}" for k, hs in BUILDING_SKINS.items() for h in hs]
        expected = ([f"landmark_{k}" for k, _ in LANDMARKS] + [f"faith_{f}" for f in FAITHS]
                    + [f"heritage_{h}" for h in heritages_in_option_order] + building + ["generic"])
```

Add to `SkinTests`:

```python
    def test_building_styles(self):
        e = read(EFFECTS)
        bodies = dict(self._options())
        L = loc()
        for key, heritages in BUILDING_SKINS.items():
            self.assertEqual(list(heritages), [h for h in HERITAGES if h in heritages], key)
            offer = squash(block(e, f"gm_state_offer_skins_building_{key}"))
            if not heritages:
                # The Exhibition Hall offers no style: its axis is none in effect.
                self.assertEqual(offer, "gm_state_offer_skins_none = yes", key)
                continue
            self.assertEqual(offer, f"gm_state_offer_building_skins = {{ KEY = {key} }}")
            default = squash(block(e, f"gm_state_default_building_skin_{key}"))
            # Reverse partition order: a later try wins, so the most specific is last.
            self.assertEqual(default, " ".join(f"gm_state_try_heritage_skin = {{ H = {h} }}"
                                               for h in reversed(heritages)), key)
            for h in heritages:
                body = bodies[f"building_{key}_{h}"]
                self.assertIn("highlighted_option = yes", body)
                self.assertIn(f"hidden_trigger = {{ var:gm_skin_axis = flag:building "
                              f"gm_state_has_pm = {{ PM = pm_monument_{key} }} }} "
                              f"owner = {{ te_heritage_{h} = yes }}", body)
                self.assertIn(f"gm_state_choose_building_skin = {{ SKIN = heritage_{h} }}", body)
                self.assertIn(f"monument_events.11.building_{key}_{h}", L)
        shared = squash(block(e, "gm_state_offer_building_skins"))
        self.assertIn("gm_state_default_building_skin_$KEY$ = yes", shared)
        self.assertIn("set_variable = { name = gm_skin_axis value = flag:building } "
                      "trigger_event = { id = monument_events.11 }", shared)
        choose = squash(block(e, "gm_state_choose_building_skin"))
        self.assertIn("text = gm_skin_choice_building_tt", choose)
        self.assertIn("gm_state_unveil = yes", choose)
        self.assertIn("gm_skin_choice_building_tt", L)

    def test_a_building_keeps_its_name_in_any_style(self):
        names = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        first = names.split("text = {")[1:6]
        for (key, form), branch in zip(BUILDING_FORMS.items(), first):
            self.assertIn(f"var:gm_form = flag:{form} }} localization_key = pm_monument_{key}", branch)
```

The Exhibition Hall (`industrial`) lists no heritage, so it has no `gm_state_default_building_skin_industrial`: an empty effect would fail `empty_effect_audit`. Its offer effect calls `gm_state_offer_skins_none` instead, which the test's first branch pins.

- [ ] **Step 2: Run them to see them fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry.SkinTests test_grand_monument_registry.CeremonyTests 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: FAILED (no building options or effects; the wrapper calls still say `AXIS = none`).

- [ ] **Step 3: Effects** (`gm_effects.txt`, after `gm_state_offer_skins_heritage`)

```
# The civic-progress buildings (spec 2026-10-11 §2.4): a style changes only the
# look. Each building offers the heritages its own tradition has, most specific
# last (a later try wins, as in gm_state_default_heritage_skin). The Exhibition
# Hall offers none.
gm_state_offer_skins_building_artistic = { gm_state_offer_building_skins = { KEY = artistic } }
gm_state_offer_skins_building_naturalist = { gm_state_offer_building_skins = { KEY = naturalist } }
gm_state_offer_skins_building_scientific = { gm_state_offer_building_skins = { KEY = scientific } }
gm_state_offer_skins_building_industrial = { gm_state_offer_skins_none = yes }
gm_state_offer_skins_building_athletic = { gm_state_offer_building_skins = { KEY = athletic } }

gm_state_offer_building_skins = {
	gm_state_default_building_skin_$KEY$ = yes
	if = {
		limit = {
			NOT = { var:gm_skin = flag:generic }
			owner = { is_ai = no }
		}
		set_variable = { name = gm_skin_axis value = flag:building }
		trigger_event = { id = monument_events.11 }
	}
}

gm_state_default_building_skin_artistic = {
	gm_state_try_heritage_skin = { H = greek }
	gm_state_try_heritage_skin = { H = chinese }
}

gm_state_default_building_skin_naturalist = {
	gm_state_try_heritage_skin = { H = chinese }
	gm_state_try_heritage_skin = { H = arabic }
	gm_state_try_heritage_skin = { H = avestan }
}

gm_state_default_building_skin_scientific = {
	gm_state_try_heritage_skin = { H = mayan }
	gm_state_try_heritage_skin = { H = chinese }
	gm_state_try_heritage_skin = { H = avestan }
	gm_state_try_heritage_skin = { H = sanskrit }
}

gm_state_default_building_skin_athletic = {
	gm_state_try_heritage_skin = { H = mayan }
	gm_state_try_heritage_skin = { H = nahuatl }
	gm_state_try_heritage_skin = { H = greek }
	gm_state_try_heritage_skin = { H = latin }
}

# State scope, a civic-progress option of monument_events.11.
gm_state_choose_building_skin = {
	custom_tooltip = {
		text = gm_skin_choice_building_tt
		set_variable = { name = gm_skin value = flag:$SKIN$ }
		gm_remove_state_var = { VAR = gm_skin_axis }
	}
	hidden_effect = { gm_state_unveil = yes }
}
```

`gm_state_offer_skins` still sets `gm_skin = flag:generic` before calling `gm_state_offer_skins_$AXIS$`, and still handles the unveiling and `monument_events.20` itself. Do not repeat either here. The first `gm_state_default_building_skin_<key>` call runs with `gm_skin` already generic.

Do **not** add a building branch to `gm_state_set_default_skin`: an old civic building keeps the generic style it has (spec §2.4 restyles new dedications only).

- [ ] **Step 4: The ceremony calls**

In `monument_events.2`, change the five `gm_state_dedicate_timeless = { KEY = <k> AXIS = none }` to `AXIS = building_<k>` (artistic, naturalist, scientific, industrial, athletic).

- [ ] **Step 5: `.11` options**

After the last `heritage_*` option and before `monument_events.11.generic`, add 13 options in `BUILDING_SKINS` order (artistic: chinese, greek; naturalist: avestan, arabic, chinese; scientific: sanskrit, avestan, chinese, mayan; athletic: latin, greek, nahuatl, mayan), each of this shape:

```
	option = {
		name = monument_events.11.building_athletic_latin
		highlighted_option = yes
		trigger = {
			hidden_trigger = {
				var:gm_skin_axis = flag:building
				gm_state_has_pm = { PM = pm_monument_athletic }
			}
			owner = { te_heritage_latin = yes }
		}
		gm_state_choose_building_skin = { SKIN = heritage_latin }
	}
```

- [ ] **Step 6: Names**

At the top of `gm_skin_name` (before the first faith branch), add five branches in `BUILDING_FORMS` order (artistic/opera_house, naturalist/gardens, scientific/observatory, industrial/exhibition_hall, athletic/stadium):

```
	# A civic-progress building keeps its building's name in any style (spec 2026-10-11 §2.4).
	text = {
		trigger = { has_variable = gm_form var:gm_form = flag:opera_house }
		localization_key = pm_monument_artistic
	}
```

- [ ] **Step 7: Loc**

`te_events_l_english.yml`, beside the other `monument_events.11.*`:

```
 monument_events.11.building_artistic_chinese:0 "Raise it as a Chinese opera stage"
 monument_events.11.building_artistic_greek:0 "Raise it as a Greek open-air theatre"
 monument_events.11.building_naturalist_avestan:0 "Lay it out as a Persian garden"
 monument_events.11.building_naturalist_arabic:0 "Lay it out as an Andalusian courtyard garden"
 monument_events.11.building_naturalist_chinese:0 "Lay it out as a Chinese scholar's garden"
 monument_events.11.building_scientific_sanskrit:0 "Raise it as a Jantar Mantar"
 monument_events.11.building_scientific_avestan:0 "Raise it as a Persian observatory"
 monument_events.11.building_scientific_chinese:0 "Raise it as a Chinese observatory platform"
 monument_events.11.building_scientific_mayan:0 "Raise it as a Maya round tower"
 monument_events.11.building_athletic_latin:0 "Raise it as a Roman amphitheatre"
 monument_events.11.building_athletic_greek:0 "Raise it as a Greek stadium"
 monument_events.11.building_athletic_nahuatl:0 "Raise it as an Aztec ball court"
 monument_events.11.building_athletic_mayan:0 "Raise it as a Maya ball court"
```

`te_miscellaneous_l_english.yml`, beside `gm_skin_choice_tt`:

```
 gm_skin_choice_building_tt:0 "The building takes this style. The style changes its look, not its name or what it does."
```

- [ ] **Step 8: Run the tests**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 organize_loc.py` and stage what it moved. Then `python3 script_argument_audit.py --strict; python3 empty_effect_audit.py --strict; python3 loc_coverage_audit.py --strict` → exit 0.

- [ ] **Step 9: Commit**

```bash
git add test_grand_monument_registry.py events/monument_events.txt common/scripted_effects/gm_effects.txt common/customizable_localization/gm_custom_loc.txt localization/english/
git commit -m "Grand Monuments: styles for the civic-progress buildings (look only; the name stays the building's)" -m "$TRAILER"
```

---

### Task 4: The style choice says why (`.11`), and is called a style

**Files:**
- Modify: `events/monument_events.txt` (`.11`: every faith and heritage option gets `highlighted_option = yes` and its axis test in `hidden_trigger`)
- Modify: `localization/english/te_events_l_english.yml` (`monument_events.11.t`, `.d`), `localization/english/te_miscellaneous_l_english.yml` (`gm_skin_choice_tt`)
- Modify: `test_grand_monument_registry.py` (`SkinTests.test_an_option_per_skin_generic_last`'s two `assertIn`s)

- [ ] **Step 1: Update the expected strings (failing)**

In `test_an_option_per_skin_generic_last`, replace the two trigger assertions with:

```python
            self.assertIn(f"highlighted_option = yes trigger = {{ hidden_trigger = {{ var:gm_skin_axis = flag:faith }} "
                          f"owner = {{ religion = rel:{f} }} }}", bodies[f"faith_{f}"])
```

```python
            self.assertIn(f"highlighted_option = yes trigger = {{ hidden_trigger = {{ var:gm_skin_axis = flag:heritage }} "
                          f"owner = {{ te_heritage_{h} = yes }} }}", bodies[f"heritage_{h}"])
```

and add after the loops:

```python
        self.assertNotIn("highlighted_option", bodies["generic"])
        L = loc()
        self.assertEqual(L["monument_events.11.t"], "A Style for the Monument")
        self.assertIn("style", L["gm_skin_choice_tt"])
```

- [ ] **Step 2: Run it to see it fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry.SkinTests 2>&1 | grep -E '^(Ran |OK|FAILED)'` → FAILED

- [ ] **Step 3: Implement**

Every `faith_*` and `heritage_*` option of `.11` becomes, for example:

```
	option = {
		name = monument_events.11.faith_catholic
		highlighted_option = yes
		trigger = {
			hidden_trigger = { var:gm_skin_axis = flag:faith }
			owner = { religion = rel:catholic }
		}
		gm_state_choose_skin = { SKIN = faith_catholic }
	}
```

The heritage options take `flag:heritage` the same way. The `owner = { ... }` condition is unchanged, as is everything else in each option. The `landmark_*` options (none today) and `generic` are unchanged.

Loc:

```
 monument_events.11.t:0 "A Style for the Monument"
 monument_events.11.d:0 "The dedication is settled; the style is not. The architects have drawn it several ways, each borrowing from a tradition we claim as our own."
 gm_skin_choice_tt:0 "The monument takes this style. The style changes its name and look, not what it does."
```

`.11.f` keeps its text.

- [ ] **Step 4: Run the tests**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 event_context_audit.py --strict` → exit 0 (the `hidden_trigger` is a plain trigger block).

- [ ] **Step 5: Commit**

```bash
git add events/monument_events.txt localization/english/ test_grand_monument_registry.py
git commit -m "Grand Monuments: the style choice shows each style's condition and is called a style" -m "$TRAILER"
```

---

### Task 5: Every dedication shows at the ceremony (`.2`)

**Files:**
- Modify: `events/monument_events.txt` (`.2`: each dedication option that has a `trigger` gets `show_as_unavailable = { always = yes }` right after its trigger)
- Modify: `test_grand_monument_registry.py` (`CeremonyTests`)

- [ ] **Step 1: The failing test** (add to `CeremonyTests`)

```python
    def test_unavailable_dedications_show_greyed(self):
        options = ceremony_options()
        for d in DEDICATIONS:
            body = squash(strip_comments(options[CEREMONY_OPTION[d.key]]))
            if "trigger = {" in body.split("ai_chance")[0]:
                self.assertIn("show_as_unavailable = { always = yes }", body, d.key)
        self.assertNotIn("show_as_unavailable", squash(options["a"]), "leaving it undedicated is always open")
```

(`ceremony_options()` returns each option's body by its letter; the dedication's gate is the option's first `trigger`, before `ai_chance`.)

- [ ] **Step 2: Run it to see it fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry.CeremonyTests 2>&1 | grep -E '^(Ran |OK|FAILED)'` → FAILED

- [ ] **Step 3: Implement**

In each `.2` option whose top-level `trigger = { ... }` gates the dedication (`.2.l`, `.b`, `.n`, `.o`, `.c`, `.g`, `.h`, `.i`, `.j`, `.k`), insert after the trigger's closing brace:

```
		show_as_unavailable = { always = yes }
```

The gates expand to native lines (laws, technologies). If an in-game check (Task 11) shows one drawing as a raw trigger name, wrap that option's gate as `custom_tooltip = { text = gm_ceremony_gate_<key>_tt <the gate> }`, add the loc (sentence from spec §4.1's table), and amend this test.

- [ ] **Step 4: Run the tests**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK

- [ ] **Step 5: Commit**

```bash
git add events/monument_events.txt test_grand_monument_registry.py
git commit -m "Grand Monuments: the ceremony shows every dedication, the unavailable ones greyed with their reasons" -m "$TRAILER"
```

---

### Task 6: The picture number

**Files:**
- Create: `common/scripted_effects/gm_picture_effects.txt` (BOM, tabs)
- Modify: `common/script_values/gm_values.txt` (`gm_disp_picture_code`)
- Modify: `common/scripted_effects/gm_name_effects.txt` (calls at the end of `gm_state_set_default_form`, `gm_state_choose_form`'s `custom_tooltip`, `gm_state_take_commission_name`)
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_clear_state` removes the code; `gm_country_refresh`'s state loop calls the helper after `gm_state_name_if_unnamed = yes`)
- Modify: `test_grand_monument_registry.py` (new `PICTURES` table and `PictureTests`)

**Interfaces:**
- Consumes: forms from Task 2, `BUILDING_SKINS` from Task 3.
- Produces:
  - `gm_state_update_picture` (state scope, no arguments);
  - state variable `gm_picture_code`;
  - script value `gm_disp_picture_code` (state scope);
  - `PICTURES`: code → file key, used by Tasks 7–9.

**The table** (append-only; the file key is `<skin>__<form>`):

| Codes | Pictures |
|---|---|
| 1 | `undedicated` |
| 10–16 | `generic__column` 10, `__arch` 11, `__obelisk` 12, `__statue` 13, `__gate` 14, `__hall` 15, `__mausoleum` 16 |
| 100– | heritage, a block of ten per skin in `HERITAGE_SKINS` order, the skin's default form at +0, then its other forms as listed: latin 100 column, 101 arch, 102 forum · hebrew 110 gate, 111 court, 112 pillar, 113 menorah · sanskrit 120 pillar, 121 gate · geez 130 stele, 131 rock_hewn_church · slavonic 140 memorial_church, 141 column, 142 bell_tower · avestan 150 gate, 151 hall · arabic 160 hall, 161 gate · chinese 170 hall, 171 gate, 172 pagoda · greek 180 pantheon, 181 column, 182 stoa · irish 190 round_tower, 191 high_cross · nahuatl 200 pyramid, 201 sun_stone · norse 210 rune_stone, 211 hall · gothic 220 hall_of_fame, 221 tower · mayan 230 pyramid, 231 stela · prussian 240 hill_shrine, 241 sacred_oak · aramaic 250 rock_cut, 251 colonnade |
| 300–315 | `faith_<r>__faith` in `FAITHS` order |
| 400– | buildings, a block of ten per building in `BUILDING_FORMS` order, `generic__<form>` at +0 then `heritage_<h>__<form>` in `BUILDING_SKINS` order: 400 opera_house, 401 chinese, 402 greek · 410 gardens, 411 avestan, 412 arabic, 413 chinese · 420 observatory, 421 sanskrit, 422 avestan, 423 chinese, 424 mayan · 430 exhibition_hall · 440 stadium, 441 latin, 442 greek, 443 nahuatl, 444 mayan |

- [ ] **Step 1: The table and the failing tests** (append to `test_grand_monument_registry.py`)

```python
# ==== Pictures (spec 2026-10-11 §3) =====================================================
PICTURE_EFFECTS = "common/scripted_effects/gm_picture_effects.txt"
# A heritage skin's forms in picture order: its default first, then the rest
# as FORMS lists them (dict order).
def _skin_forms(skin):
    rest = [f for f, skins in FORMS.items() if skin in skins and f != DEFAULT_FORM[skin]]
    return [DEFAULT_FORM[skin]] + rest

def _pictures():
    out = {1: ("undedicated", None, None)}
    for i, form in enumerate(("column", "arch", "obelisk", "statue", "gate", "hall", "mausoleum")):
        out[10 + i] = ("generic", form, None)
    for b, h in enumerate(HERITAGE_SKINS):
        for i, form in enumerate(_skin_forms(f"heritage_{h}")):
            out[100 + 10 * b + i] = (f"heritage_{h}", form, None)
    for i, f in enumerate(FAITHS):
        out[300 + i] = (f"faith_{f}", "faith", None)
    for b, (key, form) in enumerate(BUILDING_FORMS.items()):
        out[400 + 10 * b] = ("generic", form, key)
        for i, h in enumerate(BUILDING_SKINS[key]):
            out[400 + 10 * b + 1 + i] = (f"heritage_{h}", form, key)
    return out

PICTURES = _pictures()   # code -> (skin, form, building key or None)

def picture_key(code):
    skin, form, _ = PICTURES[code]
    return "undedicated" if skin == "undedicated" else f"{skin}__{form}"


class PictureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = read(PICTURE_EFFECTS)
        cls.body = squash(block(cls.e, "gm_state_update_picture"))

    def test_the_table(self):
        self.assertEqual(len(PICTURES), 80)
        # Every reachable pair has a picture.
        pairs = {(s, f) for code, (s, f, _) in PICTURES.items() if code != 1}
        for form, skins in FORMS.items():
            for skin in skins:
                self.assertIn((skin, form), pairs, (skin, form))
        # Fixed codes that must never move (append-only).
        self.assertEqual(picture_key(10), "generic__column")
        self.assertEqual(picture_key(102), "heritage_latin__forum")
        self.assertEqual(picture_key(300), "faith_catholic__faith")
        self.assertEqual(picture_key(444), "heritage_mayan__stadium")

    def test_helper_sets_every_code_in_order(self):
        b = self.body
        self.assertTrue(b.startswith("set_variable = { name = gm_picture_code value = 1 }"))
        skins_start = b.index("gm_state_picture_skin =")
        pairs_start = b.index("gm_state_picture_pair =")
        buildings_start = b.index("gm_state_picture_building =")
        self.assertLess(skins_start, pairs_start, "skin defaults first: an unknown pair falls back to them")
        self.assertLess(pairs_start, buildings_start, "a building's lines last: its form outranks its skin")
        for code, (skin, form, key) in PICTURES.items():
            if code == 1:
                continue
            generic = "yes" if skin == "generic" else "no"
            if key is not None and skin == "generic":
                self.assertIn(f"gm_state_picture_building = {{ FORM = {form} CODE = {code} }}", b, code)
            elif key is not None:
                self.assertIn(f"gm_state_picture_building_skin = {{ FORM = {form} SKIN = {skin} CODE = {code} }}", b, code)
            elif form == "faith":
                self.assertIn(f"gm_state_picture_skin = {{ SKIN = {skin} GENERIC = no CODE = {code} }}", b, code)
            else:
                self.assertIn(f"gm_state_picture_pair = {{ SKIN = {skin} GENERIC = {generic} FORM = {form} CODE = {code} }}", b, code)
        for skin, default in DEFAULT_FORM.items():
            code = next(c for c, (s, f, k) in PICTURES.items() if s == skin and f == default and k is None)
            self.assertIn(f"gm_state_picture_skin = {{ SKIN = {skin} GENERIC = {'yes' if skin == 'generic' else 'no'} "
                          f"CODE = {code} }}", b, skin)

    def test_called_wherever_skin_or_form_changes(self):
        names = read(NAME_EFFECTS)
        for effect in ("gm_state_set_default_form", "gm_state_take_commission_name", "gm_state_unveil"):
            self.assertTrue(squash(block(names, effect)).endswith("gm_state_update_picture = yes"), effect)
        self.assertIn("set_variable = { name = gm_form value = flag:$FORM$ } gm_state_update_picture = yes",
                      squash(block(names, "gm_state_choose_form")))
        e = read(EFFECTS)
        self.assertIn("gm_state_name_if_unnamed = yes gm_state_update_picture = yes", squash(block(e, "gm_country_refresh")))
        self.assertIn("gm_remove_state_var = { VAR = gm_picture_code }", squash(block(e, "gm_clear_state")))

    def test_display_value_defaults_to_the_draped_picture(self):
        v = squash(block(read(VALUES), "gm_disp_picture_code"))
        self.assertEqual(v, "value = 1 if = { limit = { has_variable = gm_picture_code } value = var:gm_picture_code }")
```

- [ ] **Step 2: Run it to see it fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry.PictureTests 2>&1 | grep -E '^(Ran |OK|FAILED|ERROR)'`
Expected: FAILED/ERROR (the effects file does not exist).

- [ ] **Step 3: The effects file**

Generate the body from the table so the 80 lines can't drift, with a one-off script (scratchpad, not committed):

```python
import sys; sys.path.insert(0, ".")
import test_grand_monument_registry as t
P = t.PICTURES
lines = ["\tset_variable = { name = gm_picture_code value = 1 }",
         "\tif = {", "\t\tlimit = {", "\t\t\tgm_state_is_dedicated = yes", "\t\t\thas_variable = gm_form", "\t\t}",
         "\t\t# A skin's default form: the picture of a pair with none of its own (a retired form)."]
for skin, default in t.DEFAULT_FORM.items():
    code = next(c for c, (s, f, k) in P.items() if s == skin and f == default and k is None)
    lines.append(f"\t\tgm_state_picture_skin = {{ SKIN = {skin} GENERIC = {'yes' if skin == 'generic' else 'no'} CODE = {code} }}")
lines.append("\t\t# A faith's building.")
for c, (s, f, k) in P.items():
    if f == "faith":
        lines.append(f"\t\tgm_state_picture_skin = {{ SKIN = {s} GENERIC = no CODE = {c} }}")
lines.append("\t\t# Every style and form.")
for c, (s, f, k) in P.items():
    if c != 1 and k is None and f != "faith":
        lines.append(f"\t\tgm_state_picture_pair = {{ SKIN = {s} GENERIC = {'yes' if s == 'generic' else 'no'} FORM = {f} CODE = {c} }}")
lines.append("\t\t# The civic-progress buildings: the building, then its styles.")
for c, (s, f, k) in P.items():
    if k is not None and s == "generic":
        lines.append(f"\t\tgm_state_picture_building = {{ FORM = {f} CODE = {c} }}")
    elif k is not None:
        lines.append(f"\t\tgm_state_picture_building_skin = {{ FORM = {f} SKIN = {s} CODE = {c} }}")
lines.append("\t}")
print("\n".join(lines))
```

`gm_picture_effects.txt` (write with a BOM; tabs):

```
# ============================================================================
# GRAND MONUMENTS — the monument's picture (spec 2026-10-11 §3)
# ============================================================================
# State scope. gm_picture_code numbers the picture the journal entry's row and
# the state card show (the gm_picture type in grand_monuments_widget.gui), from
# the state's gm_skin and gm_form. Codes are append-only:
# test_grand_monument_registry.py's PICTURES table is the list, and a retired
# pair keeps its number. Set wherever the skin or form changes and on every
# refresh; gm_clear_state removes it, so a rebuilt monument shows the draped
# picture (1) again.

gm_state_update_picture = {
<the generated body>
}

# A skin alone: its default form's picture, or a faith's building.
gm_state_picture_skin = {
	if = {
		limit = { gm_state_skin_is = { SKIN = $SKIN$ GENERIC = $GENERIC$ } }
		set_variable = { name = gm_picture_code value = $CODE$ }
	}
}

gm_state_picture_pair = {
	if = {
		limit = {
			gm_state_skin_is = { SKIN = $SKIN$ GENERIC = $GENERIC$ }
			var:gm_form = flag:$FORM$
		}
		set_variable = { name = gm_picture_code value = $CODE$ }
	}
}

# A civic-progress building in the generic style, or a style its building
# doesn't list.
gm_state_picture_building = {
	if = {
		limit = { var:gm_form = flag:$FORM$ }
		set_variable = { name = gm_picture_code value = $CODE$ }
	}
}

gm_state_picture_building_skin = {
	if = {
		limit = {
			var:gm_form = flag:$FORM$
			has_variable = gm_skin
			var:gm_skin = flag:$SKIN$
		}
		set_variable = { name = gm_picture_code value = $CODE$ }
	}
}
```

- [ ] **Step 4: The display value** (`gm_values.txt`, after `gm_state_has_typed_name`)

```
# The monument's picture (gm_picture_effects.txt), for the gm_picture type: the
# stored code, or the draped picture until the refresh has set one.
gm_disp_picture_code = {
	value = 1
	if = {
		limit = { has_variable = gm_picture_code }
		value = var:gm_picture_code
	}
}
```

- [ ] **Step 5: The calls**

- `gm_name_effects.txt`:
  - `gm_state_set_default_form`: add `gm_state_update_picture = yes` as its last line.
  - `gm_state_take_commission_name`: the same.
  - `gm_state_unveil`: the same. A style chosen in `.11` reaches `gm_state_unveil`, which skips `gm_state_set_default_form` when a commission's name is kept.
  - `gm_state_choose_form`: inside the `custom_tooltip`, after `set_variable = { name = gm_form value = flag:$FORM$ }`, add `gm_state_update_picture = yes`.
- `gm_effects.txt`:
  - in `gm_clear_state`, after `gm_remove_state_var = { VAR = gm_form }`, add `gm_remove_state_var = { VAR = gm_picture_code }`;
  - in `gm_country_refresh`'s `every_scope_state`, after `gm_state_name_if_unnamed = yes`, add `gm_state_update_picture = yes`.

Skin changes need no call of their own: every skin choice ends in `gm_state_unveil`, and the refresh covers a skin set any other way.

- [ ] **Step 6: Run the tests and audits**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 script_argument_audit.py --strict; python3 silent_variable_audit.py --strict; python3 je_immediate_reset_audit.py --strict; python3 empty_effect_audit.py --strict` → exit 0
Run: `head -c3 common/scripted_effects/gm_picture_effects.txt | xxd` → `efbb bf`

- [ ] **Step 7: Commit**

```bash
git add common/scripted_effects/gm_picture_effects.txt common/script_values/gm_values.txt common/scripted_effects/gm_name_effects.txt common/scripted_effects/gm_effects.txt test_grand_monument_registry.py
git commit -m "Grand Monuments: gm_picture_code, set wherever the style or form changes and on every refresh" -m "$TRAILER"
```

---

### Task 7: The pictures in the row and on the state card

**Files:**
- Modify: `gui/journal_entry_widgets/grand_monuments_widget.gui` (new `gm_picture` type; `gm_row_status` becomes a badge over the picture; the row's left column)
- Modify: `gui/te_state_panel_widgets.gui` (`te_state_gm_card`: the picture at 128 px; the text column 404 → 372, its textboxes 374 → 342; `te_state_gm_row` label 290 → 258)
- Modify: `test_grand_monuments_layout.py`, `test_grand_monument_registry.py` (`PictureTests`)

**Interfaces:**
- Consumes: `gm_disp_picture_code` and `PICTURES`/`picture_key` (Task 6).
- Produces: `type gm_picture = widget`: one `icon` per code, `size = { 100% 100% }`.

- [ ] **Step 1: Failing tests**

`PictureTests` (registry test):

```python
    def test_widget_has_every_picture(self):
        gui = read("gui/journal_entry_widgets/grand_monuments_widget.gui")
        # A GUI type header has no `=` before its brace: `type gm_picture = widget {`.
        raw = raw_block_at(gui, r"(?m)^\ttype gm_picture = widget \{")
        self.assertIsNotNone(raw)
        body = squash(strip_comments(raw))
        for code in PICTURES:
            self.assertIn(f"visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_picture_code'), "
                          f"'(CFixedPoint){code}' )]\" size = {{ 100% 100% }} "
                          f"texture = \"gfx/interface/icons/gm_pictures/{picture_key(code)}.dds\"", body, code)
        self.assertEqual(body.count("icon = {"), len(PICTURES))
```

`test_grand_monuments_layout.py` (new test class):

```python
class PictureLayoutTests(unittest.TestCase):
    """The monument's picture (spec 2026-10-11 §3.4): 96 px in the row, 128 px on the state card."""

    def test_row_and_card_show_the_picture(self):
        gui = open(GUI, encoding="utf-8-sig").read()
        row = gui[gui.index("type gm_monument_row"):]
        row = row[:row.index("\n\ttype ")] if "\n\ttype " in row else row
        self.assertRegex(row, r"gm_picture = \{\s*size = \{ 96 96 \}")
        card_src = open(os.path.join(REPO, "gui", "te_state_panel_widgets.gui"), encoding="utf-8-sig").read()
        card = card_src[card_src.index("type te_state_gm_card"):]
        self.assertRegex(card, r"gm_picture = \{\s*size = \{ 128 128 \}")
        self.assertRegex(card, r"minimumsize = \{ 372 -1 \}")
```

- [ ] **Step 2: Run them to see them fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monuments_layout test_grand_monument_registry.PictureTests 2>&1 | grep -E '^(Ran |OK|FAILED)'` → FAILED

- [ ] **Step 3: The `gm_picture` type**

Generate the icons with a one-off script (scratchpad):

```python
import sys; sys.path.insert(0, ".")
import test_grand_monument_registry as t
for code in t.PICTURES:
    print("\t\ticon = {")
    print(f"\t\t\tvisible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_disp_picture_code'), '(CFixedPoint){code}' )]\"")
    print("\t\t\tsize = { 100% 100% }")
    print(f"\t\t\ttexture = \"gfx/interface/icons/gm_pictures/{t.picture_key(code)}.dds\"")
    print("\t\t}")
```

In `grand_monuments_widget.gui`, before `type gm_row_status`, add:

```
	### A monument's picture (spec 2026-10-11 §3.4): one icon per picture code
	### (gm_picture_effects.txt; the PICTURES table in
	### test_grand_monument_registry.py), shown on gm_disp_picture_code. The
	### instance sets the size; every icon fills it. In the row and on the
	### state card (te_state_panel_widgets.gui).
	type gm_picture = widget {
<the generated icons>
	}
```

- [ ] **Step 4: The status badge**

Change `type gm_row_status`:
- `size = { 96 58 }` becomes `block "status_size" { size = { 96 116 } }`;
- its `icon` becomes a 28 px badge at the top-left over the picture: `size = { 28 28 }`, `parentanchor = top|left`, `position = { 2 2 }` (keeping `block "status_texture" {}`);
- the textbox keeps `parentanchor = bottom|hcenter`.

- [ ] **Step 5: The row**

In `type gm_monument_row`, wrap the four `gm_row_status` instances in a widget that also holds the picture:

```
			widget = {
				size = { 96 116 }

				gm_picture = {
					size = { 96 96 }
					parentanchor = top|hcenter
				}
				<the four gm_row_status instances, unchanged>
			}
```

The text column stays at 376 (96 + 8 + 376 = 480).

- [ ] **Step 6: The state card**

In `te_state_gm_card`, wrap its four `gm_row_status` instances the same way, at 128:

```
				widget = {
					size = { 128 148 }

					gm_picture = {
						size = { 128 128 }
						parentanchor = top|hcenter
					}
					<the four gm_row_status instances, each with blockoverride "status_size" { size = { 128 148 } }>
				}
```

- the text column: `minimumsize = { 404 -1 }` → `{ 372 -1 }`;
- its two title textboxes: `374` → `342` (`minimumsize` and `maximumsize`);
- in `type te_state_gm_row`: `size = { 290 22 }` → `{ 258 22 }` and `max_width = 290` → `258`.

The card is then 10 + 128 + 10 + 372 + 10 = 530.

- [ ] **Step 7: Run the tests and the GUI checks**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_grand_monuments_layout test_grand_monument_registry 2>&1 | grep -E '^(Ran |OK|FAILED)'` → OK
Run: `python3 scripts/analysis/check_gui_lint.py` → no errors (a warning about new markup is fine; note it for the in-game check).
Run: `python3 gui_reference_audit.py --strict` → exit 0.

- [ ] **Step 8: Commit**

```bash
git add gui/journal_entry_widgets/grand_monuments_widget.gui gui/te_state_panel_widgets.gui test_grand_monuments_layout.py test_grand_monument_registry.py
git commit -m "Grand Monuments: the monument's picture in its row (96 px) and on the state card (128 px)" -m "$TRAILER"
```

---

### Task 8: A debug sweep through every picture

**Files:**
- Modify: `events/te_debug_monuments_events.txt` (new `te_debug_monuments.4`)
- Modify: `common/scripted_effects/gm_picture_effects.txt` (`gm_debug_next_picture`, generated from the table)
- Modify: `localization/english/te_events_l_english.yml` (the event's loc, beside `te_debug_monuments.3`'s)
- Modify: `test_grand_monument_registry.py` (`DebugTests`)

- [ ] **Step 1: The failing test** (add to `DebugTests`)

```python
    def test_picture_sweep(self):
        nxt = squash(block(read(PICTURE_EFFECTS), "gm_debug_next_picture"))
        codes = sorted(PICTURES)
        for a, b in zip(codes, codes[1:] + codes[:1]):
            self.assertIn(f"var:gm_picture_code = {a} }} set_variable = {{ name = gm_picture_code value = {b} }}", nxt)
        ev = squash(raw_block_at(read(DEBUG_EVENTS), r"(?m)^te_debug_monuments\.4\s*=\s*\{"))
        self.assertIn("gm_debug_next_picture = yes", ev)
        self.assertIn("gm_state_update_picture = yes", ev)
```

- [ ] **Step 2: Run it to see it fail** → FAILED

- [ ] **Step 3: Implement**

Generate `gm_debug_next_picture`'s chain (scratchpad script):

```python
import sys; sys.path.insert(0, ".")
import test_grand_monument_registry as t
codes = sorted(t.PICTURES)
print("gm_debug_next_picture = {")
for i, (a, b) in enumerate(zip(codes, codes[1:] + codes[:1])):
    kw = "if" if i == 0 else "else_if"
    print(f"\t{kw} = {{\n\t\tlimit = {{ var:gm_picture_code = {a} }}\n\t\tset_variable = {{ name = gm_picture_code value = {b} }}\n\t}}")
print("\telse = {\n\t\tset_variable = { name = gm_picture_code value = 1 }\n\t}\n}")
```

Append it to `gm_picture_effects.txt` under the comment `# Debug (te_debug_monuments.4): the next picture in code order. The refresh puts the real one back.`

Add after `te_debug_monuments.3` (the opening-line REVIEWED comment is what keeps `orphaned_event_audit` quiet; use the date you write it):

```
te_debug_monuments.4 = { # REVIEWED 2026-10-11: console-only test event (`event te_debug_monuments.4`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { video = "unspecific_world_fair" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = te_debug_monuments.4.t
	desc = te_debug_monuments.4.desc
	flavor = te_debug_monuments.4.flavor

	# Our tallest monument: its picture steps through every code
	# (gm_debug_next_picture); the refresh, or option c, puts the real one back.
	immediate = {
		ordered_scope_state = {
			limit = { has_building = building_grand_monument }
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = gm_dbg_m1
		}
	}

	option = {
		name = te_debug_monuments.4.a
		trigger = { exists = scope:gm_dbg_m1 }
		scope:gm_dbg_m1 = { gm_debug_next_picture = yes }
		trigger_event = { id = te_debug_monuments.4 }
	}

	option = {
		name = te_debug_monuments.4.b
		trigger = { exists = scope:gm_dbg_m1 }
		scope:gm_dbg_m1 = {
			while = {
				count = 10
				gm_debug_next_picture = yes
			}
		}
		trigger_event = { id = te_debug_monuments.4 }
	}

	option = {
		name = te_debug_monuments.4.c
		default_option = yes
		scope:gm_dbg_m1 ?= { gm_state_update_picture = yes }
	}
}
```

Loc (`te_events_l_english.yml`, beside `te_debug_monuments.3.*`):

```
 te_debug_monuments.4.t:0 "Debug: Monument Pictures"
 te_debug_monuments.4.desc:0 "Step the picture of the monument in [SCOPE.sState('gm_dbg_m1').GetName] through every picture code. It shows code [SCOPE.sState('gm_dbg_m1').MakeScope.Var('gm_picture_code').GetValue|0] now."
 te_debug_monuments.4.flavor:0 "The refresh, or the last option, puts the real picture back."
 te_debug_monuments.4.a:0 "Next picture"
 te_debug_monuments.4.b:0 "Ten pictures on"
 te_debug_monuments.4.c:0 "Back to the real picture"
```

- [ ] **Step 4: Run the tests and audits**

Run the registry test → OK. Run `python3 orphaned_event_audit.py --strict; python3 event_image_audit.py --strict; python3 loc_coverage_audit.py --strict` → exit 0. The debug event needs an `event_image` and the opening-line REVIEWED comment, as `.3` has.

- [ ] **Step 5: Commit**

```bash
git add events/te_debug_monuments_events.txt common/scripted_effects/gm_picture_effects.txt localization/english/ test_grand_monument_registry.py
git commit -m "Grand Monuments: te_debug_monuments.4 sweeps the monument's picture through every code" -m "$TRAILER"
```

---

### Task 9: The art (GPU, then owner review)

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py` (`ICONS["gm_picture"]`: 80 entries)
- Create: `gfx/interface/icons/gm_pictures/*.dds` (80, via `--stage write`)
- Modify: `test_grand_monument_registry.py` (`PictureTests`: every picture has its registry entry and, once accepted, its DDS)

- [ ] **Step 1: The failing test**

```python
    def test_every_picture_has_its_art(self):
        import importlib, sys
        sys.path.insert(0, str(ROOT / "scripts" / "image_pipeline"))
        ip = importlib.import_module("icon_prompts")
        entries = ip.ICONS["gm_picture"]
        self.assertEqual(set(entries), {picture_key(c) for c in PICTURES})
        for key, entry in entries.items():
            self.assertEqual(entry["now"], "gfx/interface/icons/building_icons/building_grand_monument.dds", key)
            if isinstance(entry.get("seed"), int):
                self.assertTrue((ROOT / f"gfx/interface/icons/gm_pictures/{key}.dds").exists(), key)
```

- [ ] **Step 2: Run it to see it fail** → FAILED (`ICONS["gm_picture"]` is empty).

- [ ] **Step 3: The entries**

Every entry is `{"subject": <subject>, "seed": None, "now": f"{_BI}/building_grand_monument.dds"}`. The subjects are below. They are archetypes, not real holy sites, and none of them has lettering.

| Key | Subject |
|---|---|
| undedicated | a tall monument entirely hidden under a huge pale canvas drape tied with ropes, scaffolding poles beside it, a small crowd waiting in the plaza, loosely hand-painted with visible brush strokes |
| generic__column | a tall fluted marble column topped by a bronze statue of a figure, on a stepped pedestal in a city square |
| generic__arch | a massive neoclassical triumphal arch of pale stone with carved reliefs, a wide avenue running through it |
| generic__obelisk | a tall plain white stone obelisk with a pointed pyramid tip, on a low base at the end of a long reflecting pool |
| generic__statue | a colossal bronze statue of a robed figure holding a torch aloft, on a tall granite pedestal |
| generic__gate | a monumental neoclassical city gate of Doric columns with a bronze chariot group on top, at the end of a boulevard |
| generic__hall | a grand neoclassical hall with a long colonnade and wide steps, on a hill above a river |
| generic__mausoleum | a domed neoclassical marble mausoleum with a columned portico, among dark cypress trees |
| heritage_latin__column | a Roman triumphal column wrapped in a spiralling carved frieze, a bronze statue on top, in a paved forum |
| heritage_latin__arch | a Roman triumphal arch with three passages, carved reliefs and a bronze four-horse chariot on top |
| heritage_latin__forum | a Roman forum, a paved open square ringed by temples with Corinthian columns and a long basilica |
| heritage_hebrew__gate | a massive city gate of golden limestone with a pointed arch between two crenellated towers |
| heritage_hebrew__court | a great colonnaded courtyard of golden limestone around a fountain, a grand domed hall at its far end |
| heritage_hebrew__pillar | two tall bronze pillars with lily-shaped capitals before a golden limestone portico |
| heritage_hebrew__menorah | a giant bronze seven-branched menorah sculpture covered in relief panels, on a stone plaza |
| heritage_sanskrit__pillar | a tall polished sandstone pillar crowned by four stone lions back to back, on a stone platform |
| heritage_sanskrit__gate | a richly carved sandstone gateway with three curved crossbeams and carved elephants, before a stone terrace |
| heritage_geez__stele | a towering carved granite stele with false windows and doors carved up its face, among smaller stelae |
| heritage_geez__rock_hewn_church | a cross-shaped church carved down into solid red rock, standing in its own deep trench |
| heritage_slavonic__memorial_church | a white stone memorial church with gilded onion domes |
| heritage_slavonic__column | a tall red granite column topped by a bronze angel, in a vast palace square |
| heritage_slavonic__bell_tower | a tall white tiered bell tower with a golden dome and open arched bell chambers |
| heritage_avestan__gate | a monumental Persian palace gate guarded by huge stone winged bulls, tall columns rising behind it |
| heritage_avestan__hall | a vast Persian columned audience hall on a raised stone terrace, with carved processional stairways |
| heritage_arabic__hall | a great palace hall with rows of red and white striped horseshoe arches under a carved dome |
| heritage_arabic__gate | a monumental gate with a tall pointed arch covered in blue and turquoise tilework, between two slender towers |
| heritage_chinese__hall | a grand Chinese palace hall with a double-eaved golden-yellow tiled roof on a three-tiered white marble terrace |
| heritage_chinese__gate | a tall Chinese ceremonial archway of red lacquered pillars and green-and-gold tiled roofs |
| heritage_chinese__pagoda | a tall nine-storey Chinese pagoda with upturned eaves at every level, beside a lake |
| heritage_greek__pantheon | a Greek Doric temple of white marble with a sculpted pediment, on a rocky hilltop |
| heritage_greek__column | a single tall Ionic marble column bearing a winged victory statue, in a Greek plaza |
| heritage_greek__stoa | a long two-storey Greek stoa colonnade of white marble lining a market square |
| heritage_irish__round_tower | a tall slender Irish stone round tower with a conical stone cap, beside a ruined chapel in green hills |
| heritage_irish__high_cross | a tall carved Celtic stone high cross with a ring around its head, in a green churchyard |
| heritage_nahuatl__pyramid | a stepped Aztec pyramid with twin temples on top and a steep double staircase, in a plaza |
| heritage_nahuatl__sun_stone | a giant round carved stone sun calendar disc standing upright on a plinth in a plaza |
| heritage_norse__rune_stone | a tall rune stone carved with a looping serpent band, on a grassy burial mound by a fjord |
| heritage_norse__hall | a long Viking mead hall with a curved turf roof and carved dragon heads on its gables |
| heritage_gothic__hall_of_fame | a white marble Greek-temple hall of fame on a high terraced hill above a wide river |
| heritage_gothic__tower | a massive dark stone memorial tower with heavy buttresses and colossal carved guardian figures, on a hilltop |
| heritage_mayan__pyramid | a steep Maya temple-pyramid with a roof-comb temple on top, rising from the jungle |
| heritage_mayan__stela | a tall Maya stone stela carved with a richly dressed ruler, beside a round altar stone in a jungle plaza |
| heritage_prussian__hill_shrine | a grassy terraced hill fort with a wooden palisade and a small wooden shrine on its summit |
| heritage_prussian__sacred_oak | an enormous ancient oak tree in a clearing, ringed by carved wooden posts around a stone altar |
| heritage_aramaic__rock_cut | a tall classical temple facade carved straight into a rose-red sandstone cliff |
| heritage_aramaic__colonnade | a long desert colonnade of weathered sandstone columns with a monumental arch, palm trees around it |
| faith_catholic__faith | a great domed basilica with twin bell towers and a colonnaded forecourt |
| faith_protestant__faith | a tall Gothic cathedral of grey stone with a single soaring spire |
| faith_orthodox__faith | a large Orthodox cathedral with five gilded onion domes and white walls |
| faith_oriental_orthodox__faith | an ancient stone church with a tall conical dome on a high plateau |
| faith_sunni__faith | a great mosque with a broad central dome, cascading half-domes and four slender minarets |
| faith_shiite__faith | a shrine mosque with a golden dome and two golden minarets, blue-tiled walls around a courtyard |
| faith_ibadi__faith | a plain whitewashed mosque with a square minaret and a small low dome, beside date palms |
| faith_jewish__faith | a grand domed synagogue in Moorish revival style with two towers and horseshoe arches |
| faith_mahayana__faith | a tall multi-storey wooden Buddhist pagoda with red pillars and upturned eaves among pine trees |
| faith_gelugpa__faith | a vast white and red Tibetan monastery climbing a mountainside, with golden roofs |
| faith_theravada__faith | a huge golden bell-shaped stupa with a tall pointed spire, ringed by smaller shrines |
| faith_confucian__faith | a Confucian temple of red walls and yellow-tiled halls around a courtyard of old cypress trees |
| faith_hindu__faith | a Hindu temple complex with tall carved stone gateway towers and a stepped water tank |
| faith_shinto__faith | a Shinto grand shrine of unpainted cypress wood with a thatched roof, approached through a large torii gate in a cedar forest |
| faith_sikh__faith | a white marble gurdwara with a ribbed central dome and small domed kiosks, beside a large pool |
| faith_animist__faith | a sacred grove of giant trees hung with ribbons, carved wooden totems around a stone circle in a clearing |
| generic__opera_house | a grand Beaux-Arts opera house with a green copper dome and gilded statues on its facade |
| heritage_chinese__opera_house | a Chinese opera stage pavilion with sweeping red and gold roofs, facing a courtyard of seats |
| heritage_greek__opera_house | a great semicircular open-air Greek stone theatre cut into a hillside, a stage building at its foot |
| generic__gardens | botanical gardens with a great Victorian glass and iron palm house among formal flower beds |
| heritage_avestan__gardens | a Persian garden divided into four by long water channels, a pavilion at its centre and rows of cypresses |
| heritage_arabic__gardens | an Andalusian courtyard garden with a long reflecting pool, orange trees and arcades of slender columns |
| heritage_chinese__gardens | a Chinese scholar's garden with a zigzag bridge, rockeries, a pond and a pavilion |
| generic__observatory | a grand domed astronomical observatory on a hilltop, its dome slit open to the sky |
| heritage_sanskrit__observatory | an Indian observatory of huge geometric masonry sundial instruments in pink stone |
| heritage_avestan__observatory | a great curved stone meridian arc descending into a round blue-tiled building |
| heritage_chinese__observatory | an ancient Chinese observatory on a city wall tower, with large bronze armillary spheres |
| heritage_mayan__observatory | a Maya round observatory tower on a stepped stone platform in the jungle |
| generic__exhibition_hall | a vast glass and iron exhibition palace with a barrel-vaulted transept, flags flying |
| generic__stadium | a large modern oval sports stadium with floodlights and a green pitch inside |
| heritage_latin__stadium | a great oval Roman amphitheatre arena of tiered stone arches |
| heritage_greek__stadium | a long horseshoe-shaped white marble stadium with tiered stone seats |
| heritage_nahuatl__stadium | an Aztec ball court shaped like a capital I with stone rings set in its walls, in a plaza |
| heritage_mayan__stadium | a Maya ball court between two long sloping stone walls with stone rings set high on them |

The Column and Obelisk subjects are written to look clearly different (spec §2.2). On the sheet, flag whether they read apart at row size (96 px).

- [ ] **Step 4: Run the test** (entries exist, none accepted) → OK. Then `python3 scripts/image_pipeline/icon_prompts.py --validate | tail -1` → `Errors: 0`. Commit the registry entries:

```bash
git add scripts/image_pipeline/icon_prompts.py test_grand_monument_registry.py
git commit -m "Grand Monuments: the 80 picture subjects (unreviewed)" -m "$TRAILER"
```

- [ ] **Step 5: Render, compose, sheet** (GPU, about 1.5 h at 3 seeds; check `nvidia-smi` first, since a running Victoria 3 holds about 9 GB)

The worktree has no `.venv-img`. Symlink the icon worktree's: `ln -s /home/jakef/src/vic3te-icon-batch3/.venv-img .venv-img` (untracked; never stage it). Then:

```bash
export FLUX_MODEL_DIR=/home/jakef/models/FLUX.1-schnell HF_HUB_OFFLINE=1
export VIC3_BASE_GAME="/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3"
PY="env -u PYTHONPATH .venv-img/bin/python scripts/image_pipeline/generate_icons.py --category gm_picture"
$PY --stage render --seeds 3 && $PY --stage compose && $PY --stage sheet
```

Run it with `run_in_background`, not `nohup &`.

- [ ] **Step 6: Review with the owner**

- **Pick and prepare:** pick a seed per entry. Zoom every pick for lettering, and retouch or reroll any that has some. Mark picks with a gold box. Send each sheet with `SendUserFile` (`display: render`) as it is made.
- **Record:** write the picks as `"seed": n` and apply the owner's overrides. For a reroll, change the subject and render that key again (`--only <key>`).
- **Column against Obelisk:** if the two read alike at 96 px, merge them (spec §2.2). Drop `gm_state_form_fits_obelisk` and Obelisk's `.24` option, and have the commissions ask for Column. Move `obelisk` to `RETIRED_FORMS`; its picture code 12 stays reserved.

- [ ] **Step 7: Write**

Run: `$PY --stage write`, which writes 80 DDS files to `gfx/interface/icons/gm_pictures/`. Check one with `file`, then:
- `python3 scripts/analysis/check_dds_dimensions.py`;
- the registry test → OK.

```bash
git add gfx/interface/icons/gm_pictures/ scripts/image_pipeline/icon_prompts.py
git commit -m "Grand Monuments: the 80 pictures (owner-reviewed picks)" -m "$TRAILER"
```

---

### Task 10: Documentation and the player guide

**Files:**
- Modify: `docs/player_guide/02-timeline.md` (§ "Monument dedications", § "Monument names and forms"); `docs/player_guide/17-reference.md` if it lists forms (`grep -n -i "obelisk\|pagoda\|form" docs/player_guide/17-reference.md`)
- Modify: `Vic3TimelineExtended_Player_Guide.pdf` (rebuilt)
- Modify: `docs/systems/mod_systems.md` (§ Grand Monuments: a Pictures bullet, and the checklist line "Add a form or style: its row in `FORMS`/`BUILDING_SKINS`, then `PICTURES`")
- Modify: `docs/systems/grand_monuments_gui_icons.md` (a line on `gm_pictures/`)
- Modify: `common/scripted_effects/gm_name_effects.txt`'s header comment (skin → style is the player's word; forms list unchanged otherwise)

- [ ] **Step 1: Guide text.** In "Monument names and forms":
  - use *style* where the text says the skin's "form" ("can take the style of your primary cultures' classical heritage …");
  - add that each monument shows a picture of its style and form in its row and on the state card;
  - add that an opera house, gardens, observatory or stadium can take a style where your heritage has one (Roman amphitheatre, Persian garden, …), which changes only its look;
  - name the new forms where the section lists forms.

  In "Monument dedications", add one sentence: the ceremony lists every dedication, and the ones you can't raise yet are greyed out with what they need. Match the chapter's depth (CLAUDE.md, § Keep the player guide current): no per-picture lists.
- [ ] **Step 2: Lint and build.** `python3 scripts/analysis/check_player_guide_style.py --strict` → clean. `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python scripts/build_player_guide.py` (run from this worktree) → PDF rebuilt. `python3 scripts/build_player_guide.py --check` → OK.
- [ ] **Step 3: Commit**

```bash
git add docs/ Vic3TimelineExtended_Player_Guide.pdf common/scripted_effects/gm_name_effects.txt
git commit -m "Grand Monuments: pictures, styles and the greyed ceremony in the player guide and system docs" -m "$TRAILER"
```

---

### Task 12: Grandeur frames (spec §3.5, added 2026-10-11)

**Files:**
- Create: `scripts/image_pipeline/gen_gm_grandeur_frames.py`. It lifts the frame band from `vanilla_template("building_icons", 256)` as `compose_framed` does, widens it, and gradient-maps its luminance to each tier's metal; tier 5 also draws four gem studs. `--sheet <png>` previews the frames over sample pictures at 256 and 96 px; `--write` writes `gfx/interface/icons/gm_pictures/frames/frame_tier_<1-5>.dds` through `icon_dds.write_dds`. It needs the game install.
- Modify: `common/script_values/gm_values.txt`: add `gm_disp_frame_tier`, 0–5 from `gm_state_grandeur` at 5, 15, 35, 75 and 155.
- Modify: `gui/journal_entry_widgets/grand_monuments_widget.gui`: after the 80 picture icons in `gm_picture`, add five frame icons, each `visible` on its tier, at `size = { 100% 100% }`.
- Modify: `test_grand_monument_registry.py` (`PictureTests`), the player guide's "Monument names and forms" (one sentence), and `docs/systems/mod_systems.md`.

**Tests (written first):**
- `gm_disp_frame_tier`'s thresholds equal the first five values in `gm_state_disp_next_step`'s list.
- The type holds one frame icon per tier 1–5, each after every picture icon, so it draws on top.
- Each frame DDS exists.
- RED before the change, GREEN after.

### Task 11: Verify and open the PR

- [ ] **Step 1: The suite and every CI check**

```bash
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/claude-1000/gm_suite.log 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/claude-1000/gm_suite.log
/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' '*.gui')
python3 organize_loc.py --check
python3 scripts/analysis/check_localization_files.py
python3 scripts/analysis/check_gui_lint.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image event_context silent_variable prev_scope container_timed_variable je_immediate_reset empty_effect change_variable_clamp script_argument script_loc_reference loc_coverage gui_reference; do python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"; done
```

Expected: OK; ruff clean; no `FAIL` lines.

- [ ] **Step 2: Every changed `.txt`/`.gui` has exactly one BOM.** `for f in $(git diff --name-only origin/main -- '*.txt' '*.gui'); do head -c6 "$f" | xxd | grep -q 'efbb bfef bbbf' && echo "DOUBLE $f"; head -c3 "$f" | xxd -p | grep -q efbbbf || echo "NO BOM $f"; done` → no output. (`.gui` files that had no BOM before keep none; compare with `git show origin/main:<f> | head -c3`.)

- [ ] **Step 3: Push and open the PR** (base `main`)

PR body:
- a summary per spec section;
- the in-game checklist from spec §7, plus "the card's labels at 258 px don't elide", "the greyed `.2` reasons read as law and technology names" and "`.11`'s tooltips show no `gm_skin_axis` line (`hidden_trigger` in an event option, first use)";
- a "Player guide" line naming `02-timeline.md`;
- the owner's picks note;
- the attribution footer.

Write it to a file first, then run `gh pr create --base main --body-file <file>`.

---

## Self-review notes

- **Spec coverage:**
  - §1 model and words: Tasks 3–4 and 10.
  - §2.2 and §2.3: Task 2. §2.4: Task 3.
  - §3.1: Task 9. §3.2 and §3.3: Task 6. §3.4: Task 7.
  - §4.1: Task 5. §4.2: Tasks 3–4. §4.3: Task 2.
  - §5: Tasks 6–8 and 11. §6: Task 10. §7: the PR body (Task 11).
- **Names used across tasks:**
  - `gm_state_update_picture`, `gm_disp_picture_code`, `gm_picture_code`;
  - `PICTURES` / `picture_key`, `BUILDING_SKINS`, `RETIRED_FORMS`;
  - `gm_state_choose_building_skin`, `gm_state_offer_building_skins`, axis flag `flag:building`;
  - the `gm_picture` GUI type and category.
- **Deviations from the spec:** none, beyond the §3.4 read, which the spec was amended for (a display value, not a raw `Var().GetValue`). The Exhibition Hall's axis resolves to `gm_state_offer_skins_none` (no style offered), as §2.4 says.
