# GUI preview: see a panel in the running game while designing it

Date: 2026-11-23. Status: design, approved by the owner (2026-11-23). Plan:
`docs/superpowers/plans/2026-11-23-gui-preview.md`.

## 1. Intent

The mod's GUI is written blind. An agent writes a `.gui` file, the audits and tests pass, and nobody sees the
panel until the owner opens it in a play-test; `docs/guides/gui_modding_guide.md` still says "not yet seen in
game" fourteen times. The owner asked for a debugging mode of the QA harness (`game_qa`) that opens the GUI
being designed in the running game, takes a screenshot and hands it back to the caller, so the caller can see
what it looks like and iterate on it with the game's hot reload.

The caller is an agent session (it reads the crop with its image tool); the owner can open the same file.

## 2. Goals, non-goals, anti-goals

Goals:

- One verb shows a named GUI type from the repo's working tree, alone, in the running game, and answers with a
  sharp crop of it at the window's own resolution, plus the lines the game logged about it.
- An edit in the repo is on screen in seconds, with no deploy and no restart.
- The same verb can draw every widget's box (layout debugging) and render at another UI scale (a player's
  larger or smaller UI setting).

Non-goals (this version):

- **The real panel in its real place** (the journal, the Nation tab, a vanilla panel the mod overrides). It
  needs the harness to open panels, by HUD clicks the click verb is not allowed today or by script; the owner
  chose the standalone copy first (2026-11-23). See § 4, approach B.
- **Hover tooltips and clicking inside the preview.** A tooltip needs the cursor held over a widget, which needs
  a cursor verb the harness lacks and a ruling on input scope.
- **Script reload.** Bindings that call a scripted GUI or a script value changed in the working tree see the
  deployed version until a deploy and the game's 40-90 s script reload. The verb says when the working tree has
  such changes; it does not sync them.

Anti-goals (a failure even if it works):

- A crop that does not show the current file. A stale picture is worse than none: the verb confirms the reload
  before it shoots, or refuses.
- Writing to the deployed mod or anywhere in the owner's folders but the harness's own overlay.
- Widening what the harness may click or type without the owner's ruling.

## 3. What the test session showed (2026-11-23)

One session, 15:13-15:22 MST, Victoria 3 1.15.2, Great Britain on the fixture `te_qa_fixture_3c10ebf790b6`
(country-select screen), the deployed mod at `main` plus a variant folder (`--add-mod
D:\vic3te-data\gui-preview-spike-2026-11-23`) holding a wrapper file. Run folder
`/mnt/d/vic3_qa_backups/runs/20261123T221454Z/` (shots and crops 01-18). Stop: `restored`.

1. **`gui.createwidget <file> <widget>` opens a top-level widget from a mod's `.gui` file**, named by its path
   from the mod root and the widget's `name`: `gui.createwidget gui/te_qa_preview.gui te_qa_preview`. The console
   answers nothing (no reply line). `gui.clearwidgets` removes every widget so created.
2. **An edit to the file of an open created widget reloads and rebuilds it in place within a second.** The edit
   at 15:17:17 was logged the same second (the reload's unlocalized-text warning) and the shot two seconds later
   showed it, the window wider as edited.
3. **An edit to a file that defines a type used inside the open widget reloads that file, but does not rebuild
   the widget.** Three seconds after such an edit the widget was unchanged; `gui.clearwidgets` and
   `gui.createwidget` again showed the edit. So the loop recreates the widget every time.
4. **A `.gui` file added mid-game to a loaded mod folder took effect**, at the same path as a deployed file
   (`gui/journal_entry_widgets/te_tax_overview_widget.gui`): its version of `te_tax_overview_panel` drew at
   the next rebuild, and later edits to it reloaded. Seen once.
5. **A `.gui` file with an unclosed brace reloaded silently**: no line in `error.log`, `debug.log` or `gui.log`,
   and the widget still drew. Nothing from the game says a file is broken.
6. **An unlocalized `text =` logs one line per reload**, `pdx_gui_localize.cpp:182 Unlocalized text '<text>'
   at gui/<file>:<line>`, in `error.log`. `raw_text` with a binding (`"[GetPlayer.GetName]"`) resolves and logs
   nothing.
7. **A full-screen magenta backdrop hides the map and side panels, and the console stays above it.** An `icon`
   of `gfx/interface/backgrounds/white.dds` with `color = { 1 0 1 1 }`, `size = { 100% 100% }`, first child of a
   `layer = top` widget. Scanning out from the screen's centre for the first magenta pixel found the window's
   edges exactly: 774 x 555 px for a 560-unit-wide window, 1.38 px per UI unit at 3840x2160 with the owner's
   UI scale.
8. **`gui.debug` then `gui.debug.drawall` outline every widget** in a pink-red line. Each answers `Enabled`
   (`gui.debug` toggles, `Disabled` the second time); `drawall` alone draws nothing.
9. **`gui.setscale <s>` rescales the game's UI live; the console keeps its size.** At 0.5 the 560-unit window
   was 258 px (0.46 px per unit); `gui.setscale 1.5` put it back (inferred from the ratio: 1.38 / 0.46 x 0.5).
   The console answers `Called`.
10. **A cursor resting at the screen's centre left a map tooltip over the preview.** `click --console` moved it
    to the console's input line and the tooltip went.
11. On the country-select screen after `tag GBR`, `GetPlayer` resolved and the Tax Code overview drew its
    Light-mode cells (the save's rule was `te_tax_code_light`).

## 4. Approaches

- **A. A standalone copy (chosen).** The harness writes a small wrapper into its overlay (a full-screen backdrop
  and a centred window that supplies a data context and instances the type), syncs the working tree's `.gui`
  files into the overlay, recreates the widget with the console and crops the shot. Covers the mod's own
  types: the sections of the journal-entry widgets and of the Timeline Extended window, and the popups' bodies.
  No clicks. It does not show the
  panel's neighbours or the host's scrollbars; the wrapper's width can match the host's to catch overflow.
- **B. The real panel in place.** Open the journal or the Nation tab where the player sees it, then shoot.
  Truer, and the only way to see an override of a vanilla panel, but opening a panel needs HUD clicks (outside
  the click verb's scope, the owner's call) or a script route nobody has tried, and the panel's scroll position
  and open sections are more state to control. Later, if A leaves a gap.
- **C. Deploy and look (rejected).** Let the deploy watcher copy the edit into the deployed mod and look at the
  real file. It changes the owner's deployed build during a session, and a deploy copies `common/` too, which
  starts the 40-90 s script reload (and has crashed a live game once, `feedback_deploy_rules`).
- **D. A scripted widget registered at launch (rejected).** `gui/scripted_widgets/` is read at startup, so each
  new type would need a restart; `createwidget` is dynamic.

## 5. Design

### 5.1 The verbs

```bash
python3 -m game_qa gui-show TYPE [--context player|je:KEY|none] [--width N] [--var KEY=VALUE]...
                                 [--outlines] [--scale S] [--setup NAME] [--keep]
python3 -m game_qa gui-hide
```

`gui-show` works in any live session (`start` as today, with no new flag): on the country-select screen of the
fresh save or in an entered game. It types and clicks only what existing verbs do (console commands, and
`click --console`), so the keyboard-latch and presence rules apply as they stand.

### 5.2 What `gui-show` does, in order

1. **Sync.** Every `.gui` file under the repo's `gui/` that the caller's branch changed, committed or not
   (`git diff --name-only` against its merge base with `origin/main`, plus untracked files), is checked (5.4)
   and copied into the overlay at the same relative path. Not "every file that differs from the deployed copy":
   a worktree branched from an older `main` differs in every file `main` changed since, and the sync would lay
   the branch's older copies (full overrides of vanilla HUD files among them) over the deployed build for the
   rest of the session. A file synced earlier in the session is kept equal to the repo's. Nothing else is
   synced. The overlay module does the
   writing (as `add_setup` does), never a hand copy.
2. **Wrapper.** The overlay's `gui/te_qa_preview.gui` is rewritten. `start` writes an empty one (revision 0)
   into the overlay, so the game has loaded and watches the file from launch: a top-level widget `te_qa_preview` holding
   the magenta backdrop (§ 3.7) and a centred window (`Window_Background`, `Window_Decoration_Spike`) that
   sizes to its content, with the context's `datacontext`, a header line naming the type and the revision, and
   `TYPE = {}`. Context: `player` (the default) is `[GetPlayer]`, for the types that read a `Country`;
   `je:KEY` is `[GetPlayerJournalEntry('KEY')]`, as `gui/te_popups.gui` already feeds its bodies; `none` sets
   none. `--width` fixes the content's width, to match the host the type lives in.

   `TYPE` is a type, not a named top-level widget. Two kinds are refused with a hint, since inside the
   wrapper's window they draw nothing or fill the screen:
   - **a journal entry's root widget** (the 44 named widgets that `common/journal_entries/` attaches by file and
     name, such as `widget_je_tax_code_status`): it gates on `JournalEntry.IsActive` and needs the entry's
     context. The hint names the section types inside it (`te_tax_status_sections`), which preview alone.
   - **a popup's full-screen shell** (`te_ui_popup` and the types derived from it: `size = { 100% 100% }`, its
     own dimmed background, gated on `te_popup`). The hint names its body type (`te_banking_help_body`).

   `--var KEY=VALUE` (repeatable) sets a client-side `GetVariableSystem` value before the shot, so the preview
   can show a section opened (`*_open`), a tab picked (`te_systems_window_tab`, `te_ni_tab`, `sr_colony_view`) or
   a chart's range (`te_hist_range`); by default a type shows in its default state. The real panels read the
   same values (`com_open_window` opens the Timeline Extended window), so the verb clears every value it set
   after the shot unless `--keep`, and `gui-hide` clears those kept (`stop` needs nothing: the values are
   the client's, never saved, and go with the game). The wrapper sets them in a `trigger_on_create = yes`
   state's `on_start` (`GetVariableSystem.Set`), as vanilla panels do; a second widget in the same file,
   `te_qa_preview_clear`, clears them the same way when created. Untried live (6).
3. **Reload confirmed.** The wrapper carries a revision token as an unlocalized `text` (§ 3.6), so its reload
   logs a line naming the token. The line comes from parsing the file, not from creating the widget: the
   test session's first one was logged at load (15:15:20), before any `createwidget`. The verb waits for that line (synced files are written before the wrapper, so
   they reload first), up to a limit, then refuses `not_reloaded` with no shot.
4. **Recreate.** `gui.clearwidgets`, then `gui.createwidget gui/te_qa_preview.gui te_qa_preview` (§ 3.3: an edit
   to a type does not rebuild an open widget).
5. **Options on.** `--outlines`: `gui.debug` and `gui.debug.drawall`, tracked by their `Enabled`/`Disabled`
   answers. `--scale S`: `gui.setscale S`, the same number the settings menu stores (`GUI.scale` in the user
   data's `pdx_settings.json`, 1.5 for the owner, which matches § 3.9's reading).
6. **Cursor parked.** `click --console` (§ 3.10), which also gives the keyboard back.
7. **Shot and crop.** A shot at the window's own resolution (the `profiler-roots` path, not the 1600 px one),
   cropped to the non-magenta rectangle around the screen's centre with a small margin, saved in the run folder
   as `gui_<n>_<TYPE>.png` beside the full shot.
8. **Options off.** Outlines are switched off and the scale is set back to the settings file's value, also
   when a step in between failed, so the next verb sees the game as before.
9. **Log.** The `error.log` and `debug.log` lines written since the sync that name a synced file or the wrapper,
   or that are the GUI's known failure lines (`Unlocalized text`, `FetchData failed`, `pdx_data_factory`), each
   once with a count (a failing binding logs every frame).

The reply has `crop`, `crop_size`, `screenshot`, `synced`, `log`, `revision` and `stale_script` (5.5); a
crop that cannot be made (nothing drawn at the centre) is `crop: null` with `crop_error`, never a refusal. `--keep` leaves the widget up for a later `gui-hide`; otherwise the verb clears it.

### 5.3 Data for the preview

The fresh save is 2 January 1836, so most late systems have nothing to show. `--setup NAME` runs a setup
(the existing mechanism) before the shot, to set the variables a panel reads; a dated fixture or an owner's
save (`start --save`) gives real late-game data. With `je:KEY` and an entry the played country does not have,
the header says so instead of showing an empty frame.

### 5.4 Checks before the sync

The game says nothing about a broken file (§ 3.5), so the verb checks the braces of each file it would sync
with the harness's own check (`overlay`'s, which the setups already use: it knows strings and comments) and
refuses `gui_parse_error` (file, what) before copying any. The repo's `gui_tree` reads a `.gui` file but
forgives an unclosed brace, so it is no check. It also refuses
`unknown_type` when `TYPE` is defined in no `.gui` file of the repo or the installed game, since an unknown type
draws nothing and logs nothing that we know of.

### 5.5 What a preview cannot show

Script and localization are not synced. When the caller's branch changed files under
`common/scripted_guis/`, `common/script_values/` or `localization/` (by the same merge-base rule as 5.2), the
reply lists them as `stale_script`, since bindings and keys read the deployed versions. Whether a localization file reloads live,
and whether a `.yml` in the overlay overrides the deployed one, is untested (6).

## 6. Left to the builder

- **Check live: the `--var` mechanism** (§ 5.2). If the `trigger_on_create` state does not set the value,
  `--var` is dropped and the default state is all a preview shows; say so in the docs.
- How the refusals of 5.2 recognise a journal entry's root (the `widget = { gui = ... name = ... }` lines under
  `common/journal_entries/`) and a popup shell (a type derived from `te_ui_popup`), and which inner types each
  hint names.
- Whether localization can be synced the same way (probe: edit a key's text in an overlay copy mid-game, then
  recreate). If it can, sync changed loc files too and drop them from `stale_script`.
- The reload wait's limit, and whether the game's `filewatcher.notificationdelay` needs a margin after the
  wrapper's line for files written just before it.
- The default `--width`: 520, the Tax Code's panel (`te_tax_overview_widget.gui`: "Every row is 480 wide ...
  inside a 520 panel"), until a live run says the journal's is other.
- The backdrop colour if magenta turns out to clash with something drawn (the outlines are pink-red, far enough
  from pure magenta in the test).
- Tests against the fakes, as the harness's other verbs have: the wrapper text, the sync's choice of files, the
  parse refusal, the crop on synthetic images, the log filter and the order of console commands.
- Docs: the `game-qa` skill (the verb list and a "Previewing a GUI" section), a line in `.claude/rules/gui.md`
  pointing to it, and `docs/guides/python_tools.md` § "Driving the game from a session".

## 7. Owner decisions, and the calls made for the owner to check

- Approach A first (owner, 2026-11-23).
- No standing grant for preview sessions (owner, 2026-11-23: "it should keep needing an explicit go ahead for
  now"). Launching follows rule 1 of the `game-qa` skill as it stands: the owner's go-ahead for each session.

Calls made in writing this up (the owner may overrule any):

- The preview takes types only; a journal entry's root widget is refused with a hint naming its sections.
  Hosting a root itself (a copy of its block, with its file's `@constants`, under `je:KEY`) is a later step if
  the sections leave a gap.
- Popups preview by their body type; the full-screen shell is refused.
- `--var` exists, and every value it sets is cleared after the shot.
- The sync takes the files the caller's branch changed, against its merge base with `origin/main`.
- Script and localization are not synced in this version (5.5).
- `--screen WxH` moved to the later steps, and the reply's `px_per_unit` dropped: neither had a measured basis.

## 8. Later steps, not in this version

- The real panel in place (approach B).
- A journal entry's root widget hosted whole.
- Hover tooltips, through a cursor verb the owner rules on.
- `--screen WxH` (how a panel fits another resolution): it needs the engine's link between resolution and UI
  units measured first, which no run has done.
