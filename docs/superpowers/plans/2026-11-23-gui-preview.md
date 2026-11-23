# GUI Preview (`gui-show`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `game_qa` verb that shows one GUI type from the caller's working tree, alone, in the running game, and answers with a full-resolution crop of it and the GUI lines the game logged.

**Architecture:** A new pure module, `game_qa/gui_preview.py`, picks the files to sync (git, against the merge base with `origin/main`), checks the type, writes the wrapper's text and filters the log. `overlay.py` gains the writes into the overlay (the wrapper, written at build so the game watches it from launch, and the synced `.gui` copies). `pixels.py` gains the backdrop crop. `Session.gui_show` / `gui_hide` run the sequence through the console and the existing click, and the server and client gain the two verbs.

**Tech Stack:** Python 3.11+, stdlib only in `game_qa/` (as now), `unittest`/pytest with the harness's fakes, the repo's `gui_tree.py`.

**Spec:** `docs/superpowers/specs/2026-11-23-gui-preview-design.md` (read it first; § 3 has the engine facts every task rests on).

## Global Constraints

- The harness writes only inside its overlay folder, through `overlay.py`; never the deployed mod or any other user-data file (skill rule 2).
- Every verb that types refuses `keyboard_away` before it types **or writes anything** (`Session._require_game()`).
- Console commands are ASCII, at most 64 characters (`console.CLEAR_BACKSPACES`).
- `.gui` files the harness writes start with one UTF-8 BOM and are indented with tabs (`overlay._txt`).
- A preview session is launched only with the owner's go-ahead for that session (owner, 2026-11-23). Tasks 1-7 need no game; Task 8 does.
- No new third-party dependency in `game_qa/` (it runs under the system `python3`).
- Default content width 520 (`te_tax_overview_widget.gui`: "Every row is 480 wide ... inside a 520 panel").
- Backdrop: `gfx/interface/backgrounds/white.dds`, `color = { 1 0 1 1 }` (pure magenta, 255/0/255).

## Review Focus

1. **A synced type file that the game has not reloaded yet** when the widget is recreated: the crop would show the old type. The wrapper is written last, so its reload line comes after the synced files' (Task 6 test `test_synced_files_are_written_before_the_wrapper`); Task 8 checks it live with a file new to the overlay.
2. **The keyboard latched away** after a click: `gui-show` must refuse before syncing or writing the wrapper (Task 6 test `test_keyboard_away_refuses_before_any_write`).
3. **Nothing drawn at the screen's centre** (the type's gate is shut, the entry inactive, a zero-size type): the reply carries the full shot, `crop: null` and `crop_error`, plus the log, and exits 0 (Task 4 test `test_a_centre_on_the_backdrop_raises`, Task 6 test `test_nothing_drawn_still_answers_with_the_shot_and_log`).
4. **A failure after outlines or scale were switched on** leaves the owner's game outlined or rescaled: both are put back in a `finally` (Task 7 test `test_outlines_and_scale_are_put_back_after_a_failure`).
5. **A caller outside a git checkout, or one with no `origin/main`**: `not_a_repo` with what was tried, nothing written (Task 1 test `test_no_upstream_is_not_a_repo`).

---

### Task 1: Which files a preview syncs

**Files:**
- Create: `game_qa/gui_preview.py`
- Test: `test_game_qa_gui_preview.py`

**Interfaces:**
- Produces:
  - `class PreviewError(Exception)` with `code: str`, `detail: str`, `info: dict` (same shape as `SessionError`).
  - `SCRIPT_DIRS = ("common/scripted_guis/", "common/script_values/", "localization/")`
  - `@dataclass(frozen=True) class BranchChanges: base: str; gui: list[str]; script: list[str]` (repo-relative POSIX paths, sorted).
  - `branch_changes(repo: Path, upstream: str = "origin/main") -> BranchChanges`

- [ ] **Step 1: Write the failing tests** (each builds a throwaway git repo in a `TemporaryDirectory`: `git init`, a commit on `main`, `git update-ref refs/remotes/origin/main HEAD`, then a branch)

```python
class BranchChangesTest(unittest.TestCase):
    def test_committed_uncommitted_and_untracked_gui_files_are_taken(self):
        # branch commits gui/a.gui, edits gui/b.gui uncommitted, adds untracked gui/sub/c.gui
        ch = gui_preview.branch_changes(repo)
        self.assertEqual(ch.gui, ["gui/a.gui", "gui/b.gui", "gui/sub/c.gui"])
        self.assertEqual(ch.base, merge_base_sha)

    def test_files_main_changed_after_the_branch_point_are_not_taken(self):
        # main moves on (gui/main_only.gui changed), origin/main follows it; the branch never touched it
        self.assertNotIn("gui/main_only.gui", gui_preview.branch_changes(repo).gui)

    def test_deleted_and_non_gui_files_are_left_out(self):
        # branch deletes gui/old.gui, adds gui/notes.txt and gfx/x.dds
        self.assertEqual(gui_preview.branch_changes(repo).gui, [])

    def test_script_side_changes_are_listed_apart(self):
        # branch edits common/scripted_guis/x.txt, common/script_values/y.txt, localization/english/z.yml, events/e.txt
        self.assertEqual(gui_preview.branch_changes(repo).script, [
            "common/script_values/y.txt", "common/scripted_guis/x.txt", "localization/english/z.yml"])

    def test_no_upstream_is_not_a_repo(self):
        # a repo without refs/remotes/origin/main, and a plain folder
        for path in (repo_without_upstream, plain_folder):
            with self.assertRaises(gui_preview.PreviewError) as caught:
                gui_preview.branch_changes(path)
            self.assertEqual(caught.exception.code, "not_a_repo")
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q -k BranchChanges`
Expected: FAIL, `ModuleNotFoundError: game_qa.gui_preview`

- [ ] **Step 3: Implement `branch_changes(repo: Path, upstream: str = "origin/main") -> BranchChanges`**

`git -C repo merge-base HEAD <upstream>`; then the union of `git diff --name-only <base>` (working tree against the base: commits and uncommitted edits) and `git ls-files --others --exclude-standard`; keep only paths that exist now; `gui` is those under `gui/` ending `.gui`, `script` those under a `SCRIPT_DIRS` prefix. Any failed git call is `PreviewError("not_a_repo", <the command and its stderr>)`.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q -k BranchChanges`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add game_qa/gui_preview.py test_game_qa_gui_preview.py
git commit -m "game_qa gui preview: the files a preview syncs, against the merge base"
```

### Task 2: Which types a preview takes

**Files:**
- Modify: `game_qa/gui_preview.py`
- Test: `test_game_qa_gui_preview.py`

**Interfaces:**
- Consumes: `PreviewError` (Task 1); `gui_tree.parse_file`, `gui_tree.type_index`, `gui_tree.base_chain` (repo root module).
- Produces:
  - `@dataclass class GuiIndex: types: dict[str, gui_tree.Node]; je_roots: dict[str, str]` (root widget name -> its `.gui` path as the journal entry names it).
  - `gui_index(repo: Path, base_game: Path | None) -> GuiIndex`: vanilla types from `base_game/game/gui` and `base_game/jomini/gui` (when present) first, then the repo's `gui/`, so the mod's definition wins; `je_roots` from every `widget = { gui = "..." name = "..." }` under the repo's `common/journal_entries/`.
  - `check_type(name: str, idx: GuiIndex) -> None`, raising `PreviewError` with `info["hint"]: list[str]`.

- [ ] **Step 1: Write the failing tests** (a temporary repo with a few `.gui` files and one `common/journal_entries/je_x.txt`)

```python
class CheckTypeTest(unittest.TestCase):
    def test_a_mod_type_passes(self):
        gui_preview.check_type("te_x_section", idx)            # no raise

    def test_a_vanilla_type_passes(self):
        gui_preview.check_type("vanilla_only_type", idx)       # defined under base_game/game/gui

    def test_an_unknown_type_is_refused(self):
        self.assertEqual(code_of("te_nothing"), "unknown_type")

    def test_a_name_that_cannot_be_typed_is_refused(self):
        for bad in ("", "a b", "x;y", "x'y", "1abc"):
            self.assertEqual(code_of(bad), "bad_argument")

    def test_a_journal_entrys_root_is_refused_with_its_sections(self):
        e = error_of("widget_je_x_status")      # je_x.txt: widget = { gui = "gui/x.gui" name = "widget_je_x_status" }
        self.assertEqual(e.code, "je_root")
        self.assertEqual(e.info["hint"], ["te_x_section", "te_x_table"])   # the mod types it instances, in order

    def test_a_popup_shell_is_refused_with_its_body(self):
        e = error_of("te_x_help_popup")         # = te_ui_help_popup { blockoverride "popup_list" { te_x_help_body = {} } }
        self.assertEqual(e.code, "popup_shell")
        self.assertEqual(e.info["hint"], ["te_x_help_body"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q -k CheckType`
Expected: FAIL, `AttributeError: ... has no attribute 'gui_index'`

- [ ] **Step 3: Implement `gui_index` and `check_type`**

Order of checks: `bad_argument` (not `[A-Za-z_][A-Za-z0-9_]*`), `je_root` (name in `idx.je_roots`: the hint is the mod types instanced under that root's node, first level of instances, in source order, at most 8), `popup_shell` (`"te_ui_popup" in gui_tree.base_chain(name, idx.types)`: the hint is the types instanced in its `blockoverride "popup_list"`), `unknown_type` (not in `idx.types`). A vanilla type has no base chain into `te_ui_popup`, so it passes.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q -k CheckType`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add game_qa/gui_preview.py test_game_qa_gui_preview.py
git commit -m "game_qa gui preview: refuse unknown types, journal entry roots and popup shells, with hints"
```

### Task 3: The wrapper's text and the log filter

**Files:**
- Modify: `game_qa/gui_preview.py`
- Test: `test_game_qa_gui_preview.py`

**Interfaces:**
- Consumes: `PreviewError` (Task 1).
- Produces:
  - `PREVIEW_FILE = "gui/te_qa_preview.gui"`, `PREVIEW_WIDGET = "te_qa_preview"`, `CLEAR_WIDGET = "te_qa_preview_clear"`, `REV_PREFIX = "te_qa_rev_"`, `BACKDROP = (255, 0, 255)`, `DEFAULT_WIDTH = 520`.
  - `wrapper_text(type_name: str | None, context: str, width: int, revision: int, variables: Mapping[str, str]) -> str` (no BOM; `overlay` adds it). `type_name=None` is the empty wrapper `overlay.build` writes (revision 0).
  - `parse_context(context: str) -> str` (validates `player`, `none`, `je:<key>`; returns it; `bad_argument` otherwise).
  - `parse_var(text: str) -> tuple[str, str]` (`KEY=VALUE`, both `[A-Za-z0-9_]+`; `bad_argument` otherwise).
  - `rev_in(line_text: str) -> int | None`: the revision an `Unlocalized text 'te_qa_rev_<n>' at gui/te_qa_preview.gui:<line>` line names.
  - `GUI_FAILURES = ("Unlocalized text", "FetchData failed", "pdx_data_factory", "pdx_gui_factory")`
  - `gui_log(lines: Sequence[str], files: Sequence[str]) -> list[dict]`: `[{"text": ..., "count": n}]` in first-seen order.

- [ ] **Step 1: Write the failing tests**

```python
class WrapperTest(unittest.TestCase):
    def test_the_wrapper_holds_the_backdrop_the_window_the_token_and_the_type(self):
        t = gui_preview.wrapper_text("te_x_section", "player", 520, 7, {})
        for piece in ('name = "te_qa_preview"', "layer = top", 'texture = "gfx/interface/backgrounds/white.dds"',
                      "color = { 1 0 1 1 }", "using = Window_Background", 'datacontext = "[GetPlayer]"',
                      'text = "te_qa_rev_7"', "te_x_section = {}", "minimumsize = { 520 -1 }"):
            self.assertIn(piece, t)
        self.assertEqual(t.count("{"), t.count("}"))              # no brace sits inside a string here
        self.assertNotIn("    ", t)                               # tabs, never spaces

    def test_contexts(self):
        self.assertNotIn("datacontext", gui_preview.wrapper_text("t", "none", 520, 1, {}))
        je = gui_preview.wrapper_text("t", "je:je_x", 520, 1, {})
        self.assertIn("datacontext = \"[GetPlayerJournalEntry('je_x')]\"", je)
        self.assertIn('visible = "[JournalEntry.IsActive]"', je)          # around the type
        self.assertIn('visible = "[Not( JournalEntry.IsActive )]"', je)   # the notice in its place

    def test_variables_are_set_on_create_and_cleared_by_the_clear_widget(self):
        t = gui_preview.wrapper_text("t", "player", 520, 1, {"te_ni_tab": "economy"})
        self.assertIn("trigger_on_create = yes", t)
        self.assertIn("on_start = \"[GetVariableSystem.Set( 'te_ni_tab', 'economy' )]\"", t)
        self.assertIn('name = "te_qa_preview_clear"', t)
        self.assertIn("on_start = \"[GetVariableSystem.Clear( 'te_ni_tab' )]\"", t)

    def test_the_empty_wrapper_is_revision_0_with_no_type(self):
        t = gui_preview.wrapper_text(None, "none", 520, 0, {})
        self.assertIn('text = "te_qa_rev_0"', t)

    def test_bad_contexts_and_vars(self):
        for bad in ("je:", "je:a b", "country", "je:x')"):
            self.assertEqual(code_of(gui_preview.parse_context, bad), "bad_argument")
        for bad in ("k", "=v", "k=", "k=v w", "k='v'", "k=v)"):
            self.assertEqual(code_of(gui_preview.parse_var, bad), "bad_argument")

class LogTest(unittest.TestCase):
    TOKEN = "[15:17:17][pdx_gui_localize.cpp:182]: Unlocalized text 'te_qa_rev_3' at gui/te_qa_preview.gui:31, either localize it or use the raw_text property instead of text"

    def test_rev_in_reads_only_the_wrappers_token(self):
        self.assertEqual(gui_preview.rev_in(self.TOKEN.split("]: ", 1)[1]), 3)
        self.assertIsNone(gui_preview.rev_in("Unlocalized text 'te_qa_rev_3' at gui/other.gui:1"))

    def test_gui_log_keeps_failures_and_lines_naming_a_synced_file_once_with_counts(self):
        lines = [self.TOKEN,
                 "[15:17:18][pdx_gui_data_manager.cpp:233]: FetchData failed for 'X' - gui/x.gui:5",
                 "[15:17:18][pdx_gui_data_manager.cpp:233]: FetchData failed for 'X' - gui/x.gui:5",
                 "[15:17:18][jomini_effect_impl.cpp:9]: unrelated",
                 "[15:17:19][something.cpp:1]: problem in gui/y.gui:2"]
        self.assertEqual(gui_preview.gui_log(lines, ["gui/y.gui"]), [
            {"text": "[pdx_gui_data_manager.cpp:233]: FetchData failed for 'X' - gui/x.gui:5", "count": 2},
            {"text": "[something.cpp:1]: problem in gui/y.gui:2", "count": 1}])   # the token line left out
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q -k "Wrapper or Log"`
Expected: FAIL, `AttributeError: ... 'wrapper_text'`

- [ ] **Step 3: Implement**

`wrapper_text` writes this shape (the spike's working file, § 3.7 of the spec, plus the token, the context and the variables). `HEADER` is `raw_text = "<type> - <context>"`; `WIDTH` is `width`:

```
widget = {
	name = "te_qa_preview"
	size = { 100% 100% }
	layer = top
	state = { name = te_qa_vars trigger_on_create = yes on_start = "[GetVariableSystem.Set( 'k', 'v' )]" ... }   # only with variables
	icon = { size = { 100% 100% } texture = "gfx/interface/backgrounds/white.dds" color = { 1 0 1 1 } }
	window = {
		parentanchor = center
		movable = no
		using = Window_Background
		using = Window_Decoration_Spike
		datacontext = "..."                                   # player / je:KEY only
		flowcontainer = {
			direction = vertical
			position = { 20 20 }
			spacing = 10
			resizeparent = yes
			ignoreinvisible = yes
			minimumsize = { WIDTH -1 }
			textbox = { size = { WIDTH 24 } HEADER default_format = "#header" align = left|nobaseline }
			textbox = { size = { WIDTH 18 } text = "te_qa_rev_N" align = left|nobaseline }
			TYPE = {}                                         # je:KEY: in a flowcontainer visible on IsActive, beside the notice
		}
	}
}
widget = { name = "te_qa_preview_clear" size = { 0 0 } state = { ... trigger_on_create = yes on_start = "[GetVariableSystem.Clear( 'k' )]" ... } }   # only with variables
```

One element per line, tabs, the `### generated by game_qa ...` comment first. `gui_log` strips the leading `[hh:mm:ss]`, drops `rev_in` lines, keeps a line containing one of `GUI_FAILURES` or a `files` path, and counts repeats.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_gui_preview.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add game_qa/gui_preview.py test_game_qa_gui_preview.py
git commit -m "game_qa gui preview: the wrapper's text, its revision token, and the GUI log filter"
```

### Task 4: The backdrop crop

**Files:**
- Modify: `game_qa/pixels.py`
- Test: `test_game_qa_pixels.py`

**Interfaces:**
- Produces:
  - `backdrop_box(image: tuple[int, int, bytes], colour: tuple[int, int, int] = (255, 0, 255), tolerance: int = 40, run: int = 3) -> tuple[int, int, int, int]`: pixel box (left, top, right, bottom; right and bottom exclusive) of the drawn rectangle around the image's centre. Raises `PixelsError("nothing drawn at the centre")` when the centre pixel is the backdrop.
  - `cut(image, box: tuple[int, int, int, int]) -> tuple[int, int, bytes]`: the pixels inside a pixel box.

- [ ] **Step 1: Write the failing tests** (synthetic images: a magenta field with a grey rectangle)

```python
def test_the_box_is_the_drawn_rectangle_around_the_centre(self):
    img = field(400, 300, rect=(120, 80, 290, 230))            # grey from x 120..289, y 80..229
    self.assertEqual(pixels.backdrop_box(img), (120, 80, 290, 230))

def test_stray_backdrop_pixels_inside_the_panel_do_not_end_it(self):
    img = field(400, 300, rect=(120, 80, 290, 230), dots=[(150, 150), (151, 150)])  # two magenta pixels in a row
    self.assertEqual(pixels.backdrop_box(img), (120, 80, 290, 230))

def test_a_near_magenta_within_the_tolerance_counts_as_backdrop(self):
    img = field(400, 300, rect=(120, 80, 290, 230), backdrop=(250, 10, 245))
    self.assertEqual(pixels.backdrop_box(img), (120, 80, 290, 230))

def test_a_centre_on_the_backdrop_raises(self):
    with self.assertRaises(pixels.PixelsError):
        pixels.backdrop_box(field(400, 300, rect=None))

def test_cut(self):
    img = field(400, 300, rect=(120, 80, 290, 230))
    self.assertEqual(pixels.cut(img, (120, 80, 290, 230))[:2], (170, 150))
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_pixels.py -q`
Expected: FAIL, `AttributeError: ... 'backdrop_box'`

- [ ] **Step 3: Implement**

From the centre, walk left, right, up and down along the centre row and column; each edge is the first pixel of the first run of `run` consecutive backdrop pixels (each channel within `tolerance` of `colour`), or the image's edge.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_pixels.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add game_qa/pixels.py test_game_qa_pixels.py
git commit -m "game_qa pixels: the drawn rectangle on a backdrop, and a pixel-box cut"
```

### Task 5: The overlay's preview files

**Files:**
- Modify: `game_qa/overlay.py`
- Test: `test_game_qa_overlay.py`

**Interfaces:**
- Consumes: `gui_preview.PREVIEW_FILE`, `gui_preview.wrapper_text` (Task 3).
- Produces:
  - `build(..., preview_gui: str | None = None)`: when given, written (with the BOM) to `PREVIEW_FILE` in the new overlay.
  - `Overlay.preview_file: Path | None = None`, `Overlay.preview_revision: int = 0`, `Overlay.synced: dict[str, str]` (rel path -> sha256 of what was written).
  - `write_preview(ov: Overlay, text: str, revision: int) -> None`
  - `sync_gui(ov: Overlay, rel: str, data: bytes) -> bool` (True when it wrote).
  - `brace_problem(body: str) -> str | None` (today's `_brace_problem`, made public; `_clean_body` calls it).

- [ ] **Step 1: Write the failing tests**

```python
class PreviewFilesTest(unittest.TestCase):
    def test_build_writes_the_empty_wrapper_so_the_game_watches_it_from_launch(self):
        ov = build_overlay(preview_gui=gui_preview.wrapper_text(None, "none", 520, 0, {}))
        self.assertTrue(ov.preview_file.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertIn("te_qa_rev_0", ov.preview_file.read_text(encoding="utf-8-sig"))

    def test_write_preview_rewrites_in_place_and_records_the_revision(self):
        overlay.write_preview(ov, "widget = { }\n", 4)
        self.assertEqual((ov.preview_revision, ov.preview_file.read_text(encoding="utf-8-sig")), (4, "widget = { }\n"))

    def test_sync_gui_writes_under_gui_and_skips_unchanged(self):
        self.assertTrue(overlay.sync_gui(ov, "gui/journal_entry_widgets/x.gui", b"\xef\xbb\xbfa = {}\n"))
        self.assertFalse(overlay.sync_gui(ov, "gui/journal_entry_widgets/x.gui", b"\xef\xbb\xbfa = {}\n"))
        self.assertEqual((ov.dir / "gui/journal_entry_widgets/x.gui").read_bytes(), b"\xef\xbb\xbfa = {}\n")

    def test_sync_gui_refuses_paths_outside_gui_and_the_harness_own_files(self):
        for rel in ("common/x.txt", "gui/../events/x.gui", "/gui/x.gui", "gui/x.txt",
                    overlay.PREVIEW_FILE, overlay.PROFILER_GUI_FILE):
            with self.subTest(rel=rel), self.assertRaises(overlay.OverlayError):
                overlay.sync_gui(ov, rel, b"a = {}\n")

    def test_writes_into_a_folder_that_is_no_longer_ours_are_refused(self):
        (ov.dir / overlay.METADATA_FILE).unlink()
        with self.assertRaises(overlay.OverlayError):
            overlay.write_preview(ov, "x", 5)
        with self.assertRaises(overlay.OverlayError):
            overlay.sync_gui(ov, "gui/x.gui", b"a")
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_overlay.py -q -k PreviewFiles`
Expected: FAIL, `TypeError: build() got an unexpected keyword argument 'preview_gui'`

- [ ] **Step 3: Implement** as `add_setup` writes: check `_is_overlay(ov.dir)` first, rewrite in place, put the old bytes back if the write fails. `PREVIEW_FILE = gui_preview.PREVIEW_FILE` re-exported for the session.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_overlay.py -q`
Expected: all passed (the existing overlay tests too)

- [ ] **Step 5: Commit**

```bash
git add game_qa/overlay.py test_game_qa_overlay.py
git commit -m "game_qa overlay: the preview wrapper from launch, and synced .gui copies"
```

### Task 6: `Session.gui_show`, the core sequence

**Files:**
- Modify: `game_qa/session.py` (the verb, its constants, the `SessionError` codes list in the class docstring; `start` passes `preview_gui` to `overlay.build`)
- Test: `test_game_qa_session.py` (new `GuiShowTest(SessionTestCase)`)

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces:
  - Constants: `CLEAR_WIDGETS = "gui.clearwidgets"`, `PREVIEW_CREATE = "gui.createwidget %s %s" % (gui_preview.PREVIEW_FILE, gui_preview.PREVIEW_WIDGET)`, `GUI_RELOAD_WAIT_S = 15.0`, `GUI_RELOAD_POLL_S = 0.25`, `GUI_SETTLE_S = 0.5` (after the create, before the shot).
  - `Session.gui_show(self, type_name: str, repo: str, context: str = "player", width: int = gui_preview.DEFAULT_WIDTH, variables: Mapping[str, str] | None = None, outlines: bool = False, scale: float | None = None, setup: str | None = None, keep: bool = False) -> dict` (this task ignores `variables` beyond writing them, and `outlines`, `scale`, `setup`, `keep`: Task 7).
  - Reply keys: `type`, `context`, `revision`, `synced` (rel paths written this call), `crop`, `crop_size`, `screenshot`, `log`, `stale_script`, and on a crop failure `crop: None` with `crop_error`.
  - New codes: `gui_parse_error`, `unknown_type`, `je_root`, `popup_shell`, `not_a_repo` (from `PreviewError`, `info` kept), and `not_reloaded` for the wrapper (its `info`: `revision`, `seen`).

- [ ] **Step 1: Write the failing tests** in a `GuiShowTestBase(SessionTestCase)` whose `setUp` makes `self.repo` (a temporary git repo as in Task 1, its branch adding `gui/x.gui` with `types t { type te_x_section = widget {} }`), starts the session (`self.started()`), opens the console (`self.session.events()`), patches `overlay.write_preview` with a wrapper that also calls `self.game.error("Unlocalized text 'te_qa_rev_<n>' at gui/te_qa_preview.gui:9, ...")` (the reload's line), and makes the fake's screenshots a magenta field with a grey rectangle (170 x 150 at the centre, as in Task 4). Helpers: `self.overlay_dir` (`self.paths.overlay_dir`), `self.input_line_px()` (`session.CONSOLE_INPUT_LINE` times the client size). `GuiShowTest(GuiShowTestBase)`:

```python
class GuiShowTest(SessionTestCase):
    def test_it_syncs_writes_waits_recreates_parks_and_crops(self):
        reply = self.session.gui_show("te_x_section", str(self.repo))
        cmds = self.typed()
        i = cmds.index(session.PREVIEW_CREATE)
        self.assertEqual(cmds[i - 1], session.CLEAR_WIDGETS)
        self.assertEqual(reply["synced"], ["gui/x.gui"])
        self.assertEqual(self.game.clicks[-1], self.input_line_px())      # click --console parked the cursor
        self.assertEqual(self.game.screenshots[-1][2], self.game.client[2]) # full width, not 1600
        self.assertEqual(reply["crop_size"], [170, 150])
        self.assertEqual(reply["revision"], 1)

    def test_synced_files_are_written_before_the_wrapper(self):
        # record the order of overlay.sync_gui and overlay.write_preview calls
        self.assertEqual(order, ["sync gui/x.gui", "preview 1"])

    def test_a_brace_problem_refuses_before_any_write(self):
        # gui/x.gui gets an unclosed brace
        e = self.session_error(self.session.gui_show, "te_x_section", str(self.repo))
        self.assertEqual((e.code, e.info["file"]), ("gui_parse_error", "gui/x.gui"))
        self.assertFalse((self.overlay_dir / "gui/x.gui").exists())

    def test_keyboard_away_refuses_before_any_write(self):
        self.session.click(0.6, 0.6)
        self.assertEqual(self.session_error(self.session.gui_show, "te_x_section", str(self.repo)).code, "keyboard_away")
        self.assertFalse((self.overlay_dir / "gui/x.gui").exists())

    def test_no_token_line_is_not_reloaded_and_no_shot(self):
        # write_preview not patched: nothing logs the token
        e = self.session_error(self.session.gui_show, "te_x_section", str(self.repo))
        self.assertEqual(e.code, "not_reloaded")
        self.assertNotIn(session.PREVIEW_CREATE, self.typed())

    def test_nothing_drawn_still_answers_with_the_shot_and_log(self):
        # screenshots are all magenta; error.log has a FetchData line naming gui/x.gui
        reply = self.session.gui_show("te_x_section", str(self.repo))
        self.assertIsNone(reply["crop"])
        self.assertIn("nothing drawn", reply["crop_error"])
        self.assertEqual(reply["log"][0]["count"], 1)

    def test_type_refusals_come_through_with_their_hints(self):
        e = self.session_error(self.session.gui_show, "te_nothing", str(self.repo))
        self.assertEqual(e.code, "unknown_type")

    def test_stale_script_lists_the_branchs_script_side_files(self):
        # branch also edits common/scripted_guis/x.txt
        self.assertEqual(self.session.gui_show("te_x_section", str(self.repo))["stale_script"], ["common/scripted_guis/x.txt"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_session.py -q -k GuiShow`
Expected: FAIL, `AttributeError: 'Session' object has no attribute 'gui_show'`

- [ ] **Step 3: Implement `gui_show`** in this order, inside one `self._step("gui_show", ...)`:
  1. `self._require_game()` (refuses `keyboard_away` before anything).
  2. `gui_preview.parse_context`, `parse_var` for each variable, `width` an int from 100 to 3000 (`bad_argument`).
  3. `branch_changes(Path(repo))`; read each `gui` file; `overlay.brace_problem` on its text → `gui_parse_error` (`file`, `detail`) before any write.
  4. `check_type(type_name, gui_index(Path(repo), self._paths.base_game))` (cache the vanilla half on the session).
  5. `self._errors_seen = []`; `overlay.sync_gui` for each file; then `overlay.write_preview(ov, wrapper_text(...), ov.preview_revision + 1)`.
  6. Poll `self._new_lines()` every `GUI_RELOAD_POLL_S` until a line of `self._errors_seen` has `rev_in(...) == revision`, up to `GUI_RELOAD_WAIT_S` → `not_reloaded`.
  7. `self._console.run(CLEAR_WIDGETS)`, `self._console.run(PREVIEW_CREATE)`; `self._sleep(GUI_SETTLE_S)`.
  8. `self.click(console=True)` (parks the cursor and gives the keyboard back; its own shot is a by-product).
  9. Full-width shot as `profiler_roots` takes it (`self._shot(max_width=client width)`); `pixels.backdrop_box` and `pixels.cut` into `gui_<nn>_<type>.png` beside it; on `PixelsError` or `OSError`, `crop: None` and `crop_error`.
  10. `self._new_lines()` once more; `log = gui_preview.gui_log(self._errors_seen, synced + [PREVIEW_FILE])`; `self._errors_seen = None` in a `finally`.
  11. Unless `keep` (Task 7), `self._console.run(CLEAR_WIDGETS)`.
  `PreviewError` becomes `SessionError(e.code, e.detail, **e.info)`.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_session.py -q -k GuiShow`
Expected: 8 passed

- [ ] **Step 5: Run the whole harness suite**

Run: `.venv/bin/python -m pytest test_game_qa_*.py -q -n auto`
Expected: all passed (start's overlay now carries the wrapper; any start test that lists the overlay's files is updated to include it)

- [ ] **Step 6: Commit**

```bash
git add game_qa/session.py test_game_qa_session.py
git commit -m "game_qa: gui_show, the sync, the confirmed reload, the recreate and the crop"
```

### Task 7: Options, `gui-hide`, the server and client verbs, the docs

**Files:**
- Modify: `game_qa/session.py`, `game_qa/server.py` (`_verbs` table and its docstring's verb list), `game_qa/client.py` (usage block, `cmd_gui_show`, `cmd_gui_hide`, parsers)
- Modify: `.claude/skills/game-qa/SKILL.md` (verb list; a "Previewing a GUI" paragraph), `.claude/rules/gui.md` (one line: see a type in game with `game_qa gui-show`, with the owner's go-ahead), `docs/guides/python_tools.md` § "Driving the game from a session" (the verb and its reply)
- Test: `test_game_qa_session.py`, `test_game_qa_server.py`

**Interfaces:**
- Consumes: Task 6.
- Produces:
  - Constants: `GUI_DEBUG = "gui.debug"`, `GUI_DRAWALL = "gui.debug.drawall"`, `SET_SCALE = "gui.setscale %s"`, `CLEAR_CREATE = "gui.createwidget %s %s" % (gui_preview.PREVIEW_FILE, gui_preview.CLEAR_WIDGET)`, `SETTINGS_FILE = "pdx_settings.json"`.
  - `Session.gui_hide(self) -> dict` (`{"cleared": True, "variables_cleared": [...]}`).
  - Client: `python3 -m game_qa gui-show TYPE [--context C] [--width N] [--var KEY=VALUE]... [--outlines] [--scale S] [--setup NAME] [--keep]` posts `repo` = `git rev-parse --show-toplevel` of the caller's working directory; `python3 -m game_qa gui-hide`.
  - New code: `no_scale` (the settings file has no `GUI.scale`).

- [ ] **Step 1: Write the failing tests**

```python
class GuiShowOptionsTest(GuiShowTestBase):
    # self.toggles(*commands): an `on_step` hook that flips each command's `self.game.on` reply between
    # Enabled and Disabled after every Enter of it, starting at Enabled.
    # self.session_setup_event(name): the event id the overlay gave that setup (self.session's overlay record).
    # setUp writes {"GUI": {"scale": 1.5}} to <user data>/pdx_settings.json; test_no_scale_... deletes it.
    def test_outlines_are_switched_on_for_the_shot_and_off_after(self):
        self.toggles(session.GUI_DEBUG, session.GUI_DRAWALL)   # each answers Enabled, then Disabled, alternately
        self.session.gui_show("te_x_section", str(self.repo), outlines=True)
        cmds = self.typed()
        self.assertLess(cmds.index("gui.debug"), cmds.index(session.PREVIEW_CREATE) + 1)
        self.assertEqual(cmds[-3:-1], ["gui.debug.drawall", "gui.debug"])   # off again, in reverse

    def test_scale_is_set_for_the_shot_and_put_back_from_the_settings_file(self):
        # user data pdx_settings.json: {"GUI": {"scale": 1.5}}
        self.session.gui_show("te_x_section", str(self.repo), scale=1.0)
        self.assertEqual([c for c in self.typed() if c.startswith("gui.setscale")],
                         ["gui.setscale 1", "gui.setscale 1.5"])

    def test_no_scale_in_the_settings_refuses_before_anything_is_typed(self):
        self.assertEqual(self.session_error(self.session.gui_show, "te_x_section", str(self.repo), scale=1.0).code, "no_scale")

    def test_outlines_and_scale_are_put_back_after_a_failure(self):
        self.toggles(session.GUI_DEBUG, session.GUI_DRAWALL)
        with mock.patch.object(self.session, "click", side_effect=session.SessionError("click_refused", "x")):
            self.assertEqual(self.session_error(self.session.gui_show, "te_x_section", str(self.repo),
                                                outlines=True, scale=1.0).code, "click_refused")
        self.assertEqual(self.typed()[-1:], ["gui.setscale 1.5"])
        self.assertEqual(self.typed().count("gui.debug") % 2, 0)

    def test_variables_are_cleared_after_the_shot_unless_kept_then_by_gui_hide(self):
        self.session.gui_show("te_x_section", str(self.repo), variables={"te_ni_tab": "economy"})
        self.assertEqual(self.typed()[-3:], [session.CLEAR_WIDGETS, session.CLEAR_CREATE, session.CLEAR_WIDGETS])
        self.session.gui_show("te_x_section", str(self.repo), variables={"te_ni_tab": "economy"}, keep=True)
        self.assertNotEqual(self.typed()[-1], session.CLEAR_WIDGETS)
        self.assertEqual(self.session.gui_hide()["variables_cleared"], ["te_ni_tab"])

    def test_a_setup_runs_before_the_create(self):
        # this test's session is started with setups={"fill": "set_variable = te_x"}
        self.session.gui_show("te_x_section", str(self.repo), setup="fill")
        cmds = self.typed()
        self.assertLess(cmds.index("event " + self.session_setup_event("fill")), cmds.index(session.PREVIEW_CREATE))

class ServerGuiVerbsTest(...):          # test_game_qa_server.py, as the other verbs' routing tests
    def test_gui_show_and_gui_hide_route_to_the_session(self):
        # as the other verbs' routing tests: a fake session records the call; the reply and code come back
        self.assertEqual(self.post("gui-show", {"type": "te_x", "repo": "/r", "context": "player"})["code"], 0)
        self.assertEqual(self.fake_session.calls[-1][0], "gui_show")
        self.assertEqual(self.post("gui-hide", {})["code"], 0)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m pytest test_game_qa_session.py test_game_qa_server.py -q -k "GuiShowOptions or GuiVerbs"`
Expected: FAIL

- [ ] **Step 3: Implement.** Outlines: send `GUI_DEBUG` until its reply says `Enabled`, then `GUI_DRAWALL` until `Enabled`; afterwards each until `Disabled` (at most two sends each; a third answer that is neither is `bad_reply`). Scale: read `GUI.scale` from `<user data>/pdx_settings.json` (BOM-tolerant JSON) before anything is typed; `SET_SCALE % format(scale, "g")` before the create, the read value after. Both put back in a `finally`. Variables: after the shot, unless `keep`, `CLEAR_WIDGETS`, `CLEAR_CREATE`, `CLEAR_WIDGETS`; with `keep`, the session remembers them for `gui_hide`. Setup: `self.run_setup(setup)` after the reload and before the create.

- [ ] **Step 4: Run them to see them pass**

Run: `.venv/bin/python -m pytest test_game_qa_*.py -q -n auto`
Expected: all passed

- [ ] **Step 5: Write the docs** (the three files above; the skill paragraph says: what the verb does in a sentence, the reply's keys, the refusals with what to do for each, that the preview shows types not journal-entry roots or popup shells, that script and localization are not synced (`stale_script`), and that a session needs the owner's go-ahead)

- [ ] **Step 6: Run preflight on the diff**

Run: `.venv/bin/python scripts/preflight.py --changed`
Expected: every check passed

- [ ] **Step 7: Commit**

```bash
git add game_qa/session.py game_qa/server.py game_qa/client.py test_game_qa_session.py test_game_qa_server.py \
        .claude/skills/game-qa/SKILL.md .claude/rules/gui.md docs/guides/python_tools.md
git commit -m "game_qa: gui-show options (outlines, scale, vars, setup, keep), gui-hide, and the verbs' docs"
```

### Task 8: Live check (needs the owner's go-ahead to launch)

**Files:**
- Create: `docs/testing/game-qa-results-<date>-gui-preview.md`
- Modify: `.claude/skills/game-qa/SKILL.md` and `docs/guides/gui_modding_guide.md` § "Seeing a GUI in the Running Game" with what ran live; `game_qa/gui_preview.py` if the wrapper needs a change the run shows

**Interfaces:**
- Consumes: the finished verbs.

- [ ] **Step 1: Ask the owner for the go-ahead** for one session, naming what it will run. Do not launch without it.

- [ ] **Step 2: `python3 -m game_qa start --permission "<the owner's words>" --as GBR`**, from a worktree whose branch changed `gui/journal_entry_widgets/te_tax_overview_widget.gui` (a visible marker added, as the spike did).

- [ ] **Step 3: Run and record each, with the crop's path:**
  1. `gui-show te_tax_overview_panel`: the crop shows the marker (a file new to the overlay mid-game: Review Focus 1); `log` empty.
  2. Edit the marker again, `gui-show te_tax_overview_panel`: the new marker, revision 2.
  3. `gui-show te_tax_overview_panel --outlines`, then a plain `gui-show`: outlines, then none.
  4. `gui-show te_tax_overview_panel --scale 1`: smaller crop; afterwards a plain one is the original size (scale put back).
  5. `gui-show te_tax_status_sections --context je:je_tax_code`: drawn, or the not-active notice.
  6. `gui-show <a type gated on a client value> --var <its key>=<value>`, then `gui-show` without it: the gated part drawn, then not (the `--var` probe of spec § 6). If it is not drawn, remove `--var` from the client, the session and the docs, and say so in the results.
  7. `gui-show widget_je_tax_code_status` and a popup shell: refused with their hints.
  8. `stop`: `outcome: restored`; `doctor` clean.

- [ ] **Step 4: Write the results file and update the two docs** with what ran live (dates, the run id) and anything that differed.

- [ ] **Step 5: Commit**

```bash
git add docs/testing/game-qa-results-*-gui-preview.md .claude/skills/game-qa/SKILL.md docs/guides/gui_modding_guide.md game_qa/gui_preview.py
git commit -m "game_qa gui-show: run live, results and docs"
```
