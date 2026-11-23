# In-game QA harness results: 2026-11-23, `gui-show` (the GUI preview)

The first live run of `python3 -m game_qa gui-show` and `gui-hide`, the plan's Task 8
(`docs/superpowers/plans/2026-11-23-gui-preview.md`), on the branch of the PR that builds them. It found two bugs
and confirmed the rest; the fixes it led to are listed at the end, and were made after the run, against the fakes.

**Game:** Victoria 3 1.15.2, `-debug_mode`, the harness's fresh save (`te_qa_fixture_d3e3d90e2a0e`, made by this
start), Great Britain on the country-select screen. **Playset:** `mod_only`. **Launch:** one, on the owner's grant
("Feel free to launch the game for the next half hour if you need to test anything", 16:25 MST); `doctor` clean and
the GPU at 7% before it. **Run folder:** `runs/20261123T232850Z/` under the backup root, with every shot and crop.
The session ran from a throwaway worktree whose branch added a probe type to
`gui/journal_entry_widgets/te_tax_overview_widget.gui` (a path the deployed mod has) and a new file
`gui/te_qa_live_probe.gui` (a path it does not). `stop`: `outcome: restored`; `doctor` clean afterwards.

## What ran

| # | Command | Result |
|---|---|---|
| 1 | `gui-show te_qa_marker_probe` (in the file over a deployed path, new to the overlay) | Revision 1 confirmed; the marker drawn. **But below the wrapper's window, outside the crop** (bug 1) |
| 2 | `gui-show te_qa_marker_probe2` (a new file, new path) | Revision 2; drawn, the same way outside the window |
| 3 | `gui-show te_qa_panel_probe --var te_qa_probe=1` (a flowcontainer carrying `Window_Background` round the marker type) | The `--var` line drawn ("VAR IS SET"); the probe's background grew round all its content, while the window again stopped short |
| 4 | the same without `--var` | The line gone: the value was cleared after shot 3 |
| 5 | `--outlines` | Every widget's box drawn; `outlines: true`; the next show had none |
| 6 | `--scale 1` | **Refused `no_scale`**: the owner's `pdx_settings.json` holds `GUI.scale` as the text `"1.5"` (bug 2) |
| 7 | `gui-show te_tax_status_sections --context je:je_tax_code` | `game_gone`: the type reads a Country, which the journal-entry context does not give, so it logged `FetchData failed` every frame (841 lines) and the window stopped answering for over 10 s; the widget stayed up and kept logging until `gui-hide` |
| 8 | `gui-show widget_je_tax_code_status` | Refused `je_root`, hint `[te_je_country, te_tax_status_sections]` |
| 9 | `gui-show te_banking_help_popup` | Refused `popup_shell`, hint `[te_banking_help_body]` |
| 10 | `gui-show te_tax_overview_panel`, during the flood | `not_reloaded` (revision 8 came at 16:35:29, once the flood stopped) |
| 11 | `gui-hide` | Cleared; the flood stopped |
| 12 | `gui-show te_qa_marker_probe2 --context je:je_qa_no_such_entry` | The notice drawn: "je_qa_no_such_entry is not active for the played country". Its `log` held some forty lines of row 7's flood, logged before this show (bug 3) |
| 13 | `gui-show te_tax_status_sections` (player) | Great Britain's tax rates drawn with live figures, again spilling past the window's bottom and right edges |

## What it showed

- **A file new to the overlay mid-game is read**, also over a path the deployed mod already has (rows 1 and 2): the
  plan's Review Focus 1 holds.
- **The revision token works**: every reload logged `Unlocalized text 'te_qa_rev_<n>' at gui/te_qa_preview.gui`
  when the game parsed the file, before the create (rev 1 at 16:31:15, the create at 16:31:17), and with no widget
  open (rev 0 at load).
- **Bug 1: a `window` does not grow with a `resizeparent` flowcontainer whose content lays out late.** The window
  kept the size the flowcontainer had before the type's content laid out, so the type drew below it on the backdrop
  and the crop, walked out from the centre, stopped at the window's edge. A flowcontainer carrying the background
  itself (`using = Window_Background`) grew round all of its content.
- **`Window_Background` draws its background 23 by 17 units inside its widget** (`margin = { -23 -17 }` in vanilla's
  `windows.gui`), so content padded by less overhangs it.
- **Bug 2:** `GUI.scale` is text in the settings file.
- **Bug 3:** `log` took lines logged before the show began.
- **A type shown in a context it cannot read can freeze the game**: one failing binding a frame, in a panel with
  dozens, logged hundreds of lines a second.
- **Every GUI line in `debug.log` was also in `error.log`** (none of the run's 11,432 `debug.log` lines was a GUI
  line missing from `error.log`), so `log` reads `error.log` only.
- The token's own textbox shows `te_qa_rev_<n>` in the panel (left: it tells which revision is on screen).

## Changed after the run (against the fakes, not yet run live)

- The wrapper's panel is a flowcontainer with `using = Window_Background` and `margin = { 43 37 }` (the template's
  inset and 20 units), not a window; `Window_Decoration_Spike` is dropped (its corner icons would be flow items).
- The crop takes in what is drawn within 64 px outside the panel (`pixels.backdrop_box(gap=…)`): on row 2's shot
  it now holds the marker (bottom 1121 → 1173 px).
- `GUI.scale` is read as a number or numeric text.
- The logs are drained before a show collects its lines.
- With the review of the build: a failure after the create clears the widget, or says `preview_left_up` with `next`;
  a failed clear after a good shot keeps the crop and says `preview_left_up`; files synced earlier in the session are
  kept equal to the repo's (one reverted is synced back, one gone is removed from the overlay and listed in
  `removed`).

Not run live yet: `--scale`, `--setup`, `--keep` then `gui-hide`'s value clearing, a file removed from the overlay
mid-game, and the new panel itself.
