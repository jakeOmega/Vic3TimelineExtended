# Space Race UI pass (PRs 2–8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the rest of the owner's 2026-10-31 Space Race review: a reusable centred popup and the pickers on it (colony target, fleet destination, Transfer), posture and target button rows, the Extraplanetary Base cell, the Earth alert, fleet upkeep that no yard method changes, and tabs.

**Architecture:** Seven PRs, each from `main` in its own sparse worktree, in the spec's § 14 order. The popup is one scripted widget root (`te_popups`), drawn on `layer = popups`, that instances a library type (`te_ui_popup`) once per picker body. A client-side `GetVariableSystem` key (`te_popup`) says which body is open. The bodies' content sits under a `GetPlayerJournalEntry` datacontext, as the Timeline Extended window's Space Race tab does, so the existing `JournalEntry.GetCountry` rows draw unchanged. Per-world and per-slot rows come from the existing generators (`gen_solar_sites.py`, `gen_space_fleets.py`).

**Tech Stack:** Victoria 3 1.14.5 Paradox script and GUI, Python 3.11/3.12 generators and `unittest` structural tests.

**Spec:** [docs/superpowers/specs/2026-10-31-space-race-ui-pass-design.md](../specs/2026-10-31-space-race-ui-pass-design.md). System reference: `docs/systems/mod_systems/space_race.md`. House style: `docs/guides/gui_style_guide.md`.

## Global Constraints

- **One PR per section below, each from `origin/main`** in a sparse worktree: `git -C ~/src/Vic3TimelineExtended worktree add --no-checkout -b <branch> ~/src/vic3te-sr-<name> origin/main`, then `git sparse-checkout set --no-cone '/*' '!/gfx/'` and `git checkout <branch>`. Never `POST /reload` from a worktree.
- **The owner merges every implementation PR.** No self-merge.
- **Python:** `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`. Tests: `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent <venv python> -m pytest -q -p xdist -n 8 <files>`. Run the touched system's tests per task. Leave the full suite to CI.
- **Generated files are never hand-edited.** Edit `scripts/generators/gen_solar_sites.py` or `gen_space_fleets.py` and run it (`<venv python> scripts/generators/gen_solar_sites.py`). `--check` must exit 0 before commit.
- **Files:** exactly one UTF-8 BOM on every `.txt`, `.gui` and `.yml`; tab indentation (`scripts/format_paradox_tabs.py` on `.txt`). `docs/systems/journal_entry_systems.md` and `docs/guides/gui_modding_guide.md` are CRLF; edit them with Edit, then confirm `grep -c $'\r$'` equals `wc -l`.
- **Loc:** American English. New `je_space_race_widget_*` keys go in `localization/english/te_journal_entries_l_english.yml`; run `python3 organize_loc.py` and commit what it moves. A new label needs a cell in `test_space_race_labels.py`'s table.
- **Buttons:** a greyed button gives its reason. The tooltip is `_reasoned(sgui, scope)` (IsValidTooltip, `te_tt_break`, ExecuteTooltip), as in `gen_solar_sites.py`.
- **The popup key:** `te_popup` (client-side). One popup is open at a time. Values: `sr_target`, `sr_dest_<n>`, `sr_xfer_<n>`, `sr_ftarget_<n>`, `sr_icpt_<n>` (n = fleet slot 1–9).
- **Every PR** updates `docs/player_guide/16-space.md` where players see the change (then `<venv python> scripts/build_player_guide.py`, and commit chapter and PDF together), adds a section to `docs/testing/solar-colonies-playtest.md`, updates `docs/systems/mod_systems/space_race.md`, and its body carries a "Player guide" line.
- **Gate before each PR:** `check_gui_lint.py`, `gui_reference_audit.py --strict`, `loc_coverage_audit.py --strict`, `organize_loc.py --check`, `scripts/analysis/check_loc_spelling.py --check`, `scripts/analysis/check_localization_files.py`, `scripts/format_paradox_tabs.py --check` on changed `.txt`, `.venv/bin/ruff check .`, the generators' `--check`, `test_test_files_main_block.py`, and the audits each PR names.
- **Review:** one whole-branch review per PR (the owner's lean rule). PRs 4, 6 and 7 carry novel script logic and also get one review of their script task.

## Review Focus

1. **A popup whose subject goes away while it is open.** The fleet is destroyed or merged, colonization ends, or the entry closes. Expected: the body shows an empty-state line and nothing acts on a stale slot. Pinned by each body's `visible`, and by the PR 3 and PR 4 tests that a body's buttons read the slot's `sr_fl_<n>_exists`.
2. **The same popup opened from the Timeline Extended window and from the journal entry.** Expected: identical rows and figures. Pinned by `PopupHostTest.test_bodies_read_the_entry_through_get_player_journal_entry` (PR 2): every body sits under the scope-free gate and a `GetPlayerJournalEntry` child.
3. **Transfer amounts left stale by a fight or a repair under an open popup.** Expected: Transfer never moves more than the fleet has. Pinned by `TransferTest.test_amounts_are_clamped_before_moving` (PR 4).
4. **A war declared while a hostile fleet is already bound for Earth.** Expected: the quiet notice fires then, once. Our own and allied fleets never alert. Pinned by `EarthAlertTest.test_only_powers_at_war_count` and `test_once_per_leg_and_volume` (PR 6).
5. **A Space Command in an occupied state, or a country whose only Space Command is at zero levels.** Expected: no departures, posture changes, refits or repairs, with the reason on the button. Pinned by `NoSpaceCommandTest.test_operational_needs_a_held_level` (PR 7).

---

## PR 2: the popup shell and the colony target picker (spec §§ 3, 5)

Branch `feat/sr-popup-target-picker`, worktree `~/src/vic3te-sr-popup`.

### Task 2.1: the popup shell and its root

**Files:**
- Create: `gui/te_widget_library.gui` (types `te_widget_library_types`, type `te_ui_popup`)
- Create: `gui/te_popups.gui` (the root widget `te_popups`)
- Modify: `gui/scripted_widgets/te_systems_window.txt` (add `gui/te_popups.gui = te_popups`)
- Modify: `test_te_systems_window.py` (`RegistrationTest`'s expected list gains `te_popups`)
- Create: `test_te_popups.py`
- Modify: `docs/guides/gui_modding_guide.md` (CRLF): two rows in "This Mod's GUI Files", the count to 50 (28 replacements plus 22 additive), `default_popup`'s file at lines 60 and 591 (`gui/block_windows.gui:97`), and one paragraph after the `te_systems_window.gui` section on `te_popups`, the `te_popup` key and its values

**Interfaces:**
- Produces: `type te_ui_popup = widget`, full size, with blocks `popup_visible` (on the root), `popup_title` (the header's text), `popup_size` (the body's size; default `size = { 640 620 }`), `popup_list` (inside the scrollarea's scrollwidget) and `popup_footer` (under the scrollarea; empty by default). Both closes are fixed in the type: `GetVariableSystem.Clear('te_popup')`.
- Produces: the root `te_popups`, `layer = popups`, `visible = "[And( And( GetMetaPlayer.GetPlayedOrObservedCountry.IsValid, Not( GetMetaPlayer.IsObserver ) ), GetVariableSystem.Exists('te_popup') )]"`. Later tasks add one `te_ui_popup = { … }` instance each.

- [ ] **Step 1: Write `test_te_popups.py`** with `PopupTypeTest` and `PopupRootTest`:
  - `test_the_shell_dims_and_closes_on_a_click_outside`: `te_ui_popup`'s body contains `using = Background_Full_Dim`. A `button_normal` or `button` with `size = { 100% 100% }` and `onclick = "[GetVariableSystem.Clear('te_popup')]"` comes before the centred body. The body has `parentanchor = center` and `alwaystransparent = no`.
  - `test_the_header_closes_on_escape`: the body instances `header_pattern` with `blockoverride "button_close"` holding `onclick = "[GetVariableSystem.Clear('te_popup')]"` (vanilla's close button carries `shortcut = "close_window"`, `frontend/shared/buttons.gui:415-421`).
  - `test_the_blocks`: `block "popup_visible"`, `"popup_title"`, `"popup_size"`, `"popup_list"` and `"popup_footer"` each occur once. `popup_list` is inside a `scrollarea`.
  - `test_the_root_is_gated_and_on_the_popup_layer`: the root `te_popups` has `layer = popups` and exactly the `visible` above.
  - `test_the_files_carry_one_bom`: both new `.gui` files start with exactly one BOM.
- [ ] **Step 2: Run it** (`test_te_popups.py test_te_systems_window.py`). Expected: FAIL (no files; the registration list).
- [ ] **Step 3: Write the two files and the registration line.** Copy the shell from vanilla's `gui/principle_selection_window.gui:1-45` (the mod's override is the same): `Animation_ShowHide_Quick`, `Background_Full_Dim`, the full-size `button_normal` with `close_button_sound`, the centred `widget` with `Window_Background`, `Window_Decoration_Spike`, `Window_Margins` and `header_pattern`. Then a `scrollarea` (`scrollbaralign_vertical = right`, the scrollwidget a vertical `flowcontainer` holding `block "popup_list"`) and `block "popup_footer"`. Header comment on each file: what it is, the key, the play-test checks.
- [ ] **Step 4: Run the tests and `check_gui_lint.py`.** Expected: PASS, no lint errors.
- [ ] **Step 5: Docs.** Edit `gui_modding_guide.md` as listed. Then run `test_tax_code_bypass.py` (the table and count). Expected: PASS.
- [ ] **Step 6: Commit** `gui/te_widget_library.gui gui/te_popups.gui gui/scripted_widgets/te_systems_window.txt test_te_popups.py test_te_systems_window.py docs/guides/gui_modding_guide.md`.

### Task 2.2: the colony target popup

**Files:**
- Modify: `scripts/generators/gen_solar_sites.py` (`_site_row`, `render_gui`, `render_display`)
- Modify: `gui/journal_entry_widgets/space_race_widget.gui` (`te_sr_site_row` gains `block "site_window" {}`; new types `te_sr_target_popup_body` and `te_sr_target_popup = te_ui_popup`)
- Modify: `gui/te_popups.gui` (instances `te_sr_target_popup = {}`)
- Regenerate: `gui/journal_entry_widgets/sr_sites_generated_rows.gui`, `common/script_values/sr_sites_display_generated.txt`
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_solar_sites.py` (`PanelTest`), `test_te_popups.py`, `test_space_race_labels.py`

**Interfaces:**
- Consumes: `te_ui_popup`, `te_popups` (Task 2.1).
- Produces: `_site_row(site: Site, *, picker: bool) -> list[str]`; type `te_sr_target_picker_rows` (generated); display values `sr_disp_tp_shown_<key>` (1 while `sr_disp_site_target_<key> >= 1`), `sr_disp_tp_count_<loc>` and `sr_disp_tp_count`; the client key `sr_popup_target_all` (the popup's Show all).

- [ ] **Step 1: Write the failing tests.**
  - In `test_solar_sites.PanelTest`, change `test_the_solar_system_rows_follow_the_table`. Solar System's rows no longer name `sr_colony_target_sgui`, and each one's `blockoverride "site_target_button"` is `visible = no`.
  - Add `test_the_target_picker_rows_follow_the_table`. `te_sr_target_picker_rows` holds one `te_sr_site_row` per site in `panel_order()`. Each row:
    - passes only its own index (the `MakeScopeValue` set equals `{site.index}`);
    - calls `sr_colony_target_sgui`'s `IsValid`, `Execute` and the `_reasoned` tooltip;
    - is visible on `GetVariableSystem.Exists('sr_popup_target_all')` or `sr_disp_tp_shown_<key>` (read here, as Solar System's row reads `sr_disp_ss_shown_<key>`: `DisplayValuesTest` wants every display value read by the GUI or loc);
    - fills `block "site_window"` from `sr_disp_win_state_<transit_body(site)>`, with `win_wait` and `win_paid` absent for the Moon and Mercury, as `_window_row` does.
  - Add `test_the_target_picker_counts`. `sr_disp_tp_count_<loc>` adds `sr_disp_tp_shown_<key>` for exactly the sites at `loc`. Each location's subheader in the picker reads `sr_disp_tp_count_<loc>` and `sr_popup_target_all`.
  - In `test_te_popups.py` add `PopupHostTest`:
    - `test_the_target_popup`: `type te_sr_target_popup = te_ui_popup` sets `popup_visible` to `GetVariableSystem.HasValue('te_popup', 'sr_target')` and holds `te_sr_target_popup_body = {}`. The root `te_popups` instances `te_sr_target_popup = {}`. Beside the gated parent sits a `te_sr_note` (`je_space_race_widget_tp_gone`, "Solar System Colonization isn't running.") on the gate's negation, so an entry that closes under an open popup leaves a line, not an empty frame.
    - `test_bodies_read_the_entry_through_get_player_journal_entry`: in every `te_sr_*_popup` type, the body is under a parent whose `visible` is `GetScriptedGui('te_window_space_race_solar_colonization_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )`, and under a child with `datacontext = "[GetPlayerJournalEntry('je_space_race_solar_colonization')]"` (gotchas #22 and #29). This is how the generated rows' `JournalEntry.GetCountry` reads resolve in a popup, so `_site_scope` is reused as it is.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Generator.**
  - `_site_row(site, *, picker)`: Solar System (`picker=False`) keeps today's overrides, but `site_target_button` becomes `visible = no`. The picker (`picker=True`) sets `site_visible` to `Or( GetVariableSystem.Exists('sr_popup_target_all'), {_eq(f"sr_disp_tp_shown_{k}", 1)} )` and keeps today's target-button overrides. It adds `site_window`: a vertical stack of the four window textboxes `_window_row` uses (`je_space_race_widget_win_any`, `_open`, `_wait_<body>`, `_paid_<body>`) on `sr_disp_win_state_<body>`, `max_width = 108`, tooltip `je_space_race_widget_tp_window_tt`.
  - `render_gui` emits `te_sr_target_picker_rows` after `te_sr_solar_system_rows`, with the same per-location subheaders.
  - `render_display` emits the three count values next to `sr_disp_ss_filtered_*`.
  - Run the generator.
- [ ] **Step 4: GUI.**
  - In `te_sr_site_row`'s first line, put `block "site_window" {}` between the inbound cell and the button. Fix the width comment: 477 in Solar System, 477 + 108 + 3 = 588 in the picker.
  - New `type te_sr_target_popup_body` (vertical flowcontainer, `minimumsize = { 600 -1 }`):
    - an intro `te_sr_note` (`je_space_race_widget_tp_intro`);
    - the count line and the Show all toggle, copied from `te_sr_sec_solar_system`'s with the key `sr_popup_target_all` and the text `SelectLocalization( GetVariableSystem.Exists('sr_popup_target_all'), 'je_space_race_widget_tp_all', 'je_space_race_widget_tp_count' )`;
    - `te_sr_target_picker_rows = {}`;
    - a `te_sr_note` `je_space_race_widget_tp_none`, visible while `sr_disp_tp_count` is 0 and the toggle is off.
  - `type te_sr_target_popup = te_ui_popup` (title `je_space_race_widget_tp_title`): `popup_list` holds the gate parent, the datacontext child and `te_sr_target_popup_body = {}`. In `te_popups.gui`, instance it. Each later popup is a `te_sr_*_popup` type the same way, so the root stays a list of instances.
- [ ] **Step 5: Loc** (American English):
  - `je_space_race_widget_tp_title` "Colony Target"
  - `je_space_race_widget_tp_intro` "Where our next colony fleet goes. Hover a site's name for what it offers and our transit there."
  - `je_space_race_widget_tp_count` "#v [GetPlayer.MakeScope.ScriptValue('sr_disp_tp_count')|0]#! of [GetPlayer.MakeScope.ScriptValue('sr_sites_world_count')|0] sites can be targeted"
  - `je_space_race_widget_tp_all` "All [GetPlayer.MakeScope.ScriptValue('sr_sites_world_count')|0] sites shown"
  - `je_space_race_widget_tp_none` "No site can be targeted this month. Show all lists every site with the reason on its button."
  - `je_space_race_widget_tp_window_tt` "The launch window toward this site: open now, the months until it opens, or with propellant depots the premium to leave now."

  Add the new keys' cells to `test_space_race_labels.py` (the note, the count line, the window cell) and run `organize_loc.py`.
- [ ] **Step 6: Run** `test_solar_sites.py test_te_popups.py test_space_race_labels.py test_space_race_layout.py`, `gen_solar_sites.py --check` and `check_gui_lint.py`. Expected: PASS.
- [ ] **Step 7: Commit** the generator, both regenerated files, the GUI files, loc and tests.

### Task 2.3: Colony Fleets opens the picker; Solar System is a list to read

**Files:**
- Modify: `gui/journal_entry_widgets/space_race_widget.gui` (`te_sr_sec_colony_fleets`, `te_sr_cf_dest_row`, comments on `te_sr_sec_solar_system` and `te_sr_site_row`)
- Modify: `common/scripted_guis/sr_colony_sguis.txt` (`sr_colony_target_sgui`'s header comment)
- Modify: loc, `test_space_race_layout.py`, `test_space_race_labels.py`
- Modify: `docs/systems/mod_systems/space_race.md` (the Targets bullet, line ~150), `docs/player_guide/16-space.md` (lines ~465 and ~515, and "Choosing a colony's site"), `docs/testing/solar-colonies-playtest.md`

- [ ] **Step 1: Write `ColonyTargetOpenerTest` in `test_space_race_layout.py`**.
  - `test_each_destination_row_opens_the_picker`: each of `te_sr_sec_colony_fleets`'s three `te_sr_cf_dest_row` instances has a button with `onclick = "[GetVariableSystem.Set('te_popup', 'sr_target')]"`. The target row's text is `je_space_race_widget_cf_change`, and it keeps Clear. The two automatic rows' text is `je_space_race_widget_cf_choose`.
  - `test_the_row_fits`: `te_sr_cf_dest_row`'s `dest_value` width plus label, two 66-wide buttons, spacing and margins comes to at most 480.
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Build it.**
  - `dest_value` 250 → 184 (110 + 184 + 66 + 66 + 3 × 4 + 2 × 4 = 446), with the comment fixed.
  - Change sits before Clear on the target row. Choose sits on the two automatic rows.
  - Loc: `je_space_race_widget_cf_change` "Change", `je_space_race_widget_cf_choose` "Choose", `je_space_race_widget_cf_change_tt` "Pick the site our next colony fleet goes to, from every site we can target this month."
  - Fix the comments that say Target sits in Solar System.
  - If `test_space_race_labels.py` says a target name no longer fits 184, shrink the label column (110), not the buttons.
- [ ] **Step 4: Run** `test_space_race_layout.py test_space_race_labels.py test_solar_sites.py test_te_popups.py`. Expected: PASS.
- [ ] **Step 5: Docs.**
  - **System doc:** targets are set from the Colony Target popup (Change or Choose in Colony Fleets), and Solar System is read-only.
  - **Player guide:** the same in player terms, then rebuild the PDF.
  - **Play-test section** "The owner's UI pass: the popup and the colony target (PR 2)":
    - the popup draws over the journal panel and the Timeline Extended window;
    - Escape closes the popup, not the window behind it;
    - a click outside closes it;
    - the panel behind can scroll while it is open;
    - rows read the same from both hosts.
    - Fallback: the body inline under Colony Fleets.
- [ ] **Step 6: The PR gate** (Global Constraints), then commit and push, and open the PR (`--base main`), with the body in a file and a "Player guide" line.
- [ ] **Step 7: Whole-branch review** by one reviewer subagent. Fix what it finds as commits on the branch.

---

## PR 3: the destination picker, and posture and target rows (spec §§ 4, 7)

Branch `feat/sr-fleet-orders-popup`. Depends on PR 2 (merged).

Facts this PR rests on (from the code, 2026-10-31):
- **The slot rows.** They come from `gen_space_fleets._fleet_row(n)` (gen:1693). Every helper (`_sv`, `_eq`, `_op`, `_reasoned`) roots on `JournalEntry.GetCountry`, which works in a popup under PR 2's datacontext.
- **The destination pick.** It is the country variable `sr_fl_dest_pick_<n>`. `sr_fl_step_pick_at` sets it, and `sr_fl_go_at` and `sr_fl_dispatch` read it.
- **Posture.** It lives in `sr_fl_<n>_posture`: 1 Station, 2 Stand off, 3 Close in, 4 Interdict. `sr_fl_step_posture_at` (`sr_fleet_combat_effects.txt:1110`) runs each landing posture's side effects.
- **The target button.** One button, `sr_fleet_target_sgui`, serves both the target and the interdiction target. Its effect branches on posture 4.
- **The scripted GUI count.** `test_space_fleets.FullColoniesGateTest` counts 12 scripted GUIs in `sr_fleet_sguis.txt`. `SlotTest.test_every_do_a_caller_passes_is_an_action` requires every `DO` to be in `SLOT_ACTIONS`.

### Task 3.1: the destination popup

**Files:**
- Modify: `scripts/generators/gen_space_fleets.py` (`SLOT_ACTIONS`, the slot effects, the display values, `render_gui`)
- Modify: `common/scripted_guis/sr_fleet_sguis.txt` (new `sr_fleet_set_dest_sgui`)
- Modify: `gui/journal_entry_widgets/space_race_widget.gui` (types `te_sr_dest_row` and `te_sr_dest_popup = te_ui_popup`; `fl_pick_button` opens it)
- Modify: `gui/te_popups.gui` (instances `te_sr_dest_popup = {}`)
- Regenerate: `sr_fleets_generated_rows.gui`, `sr_fleets_generated.txt` (effects, values, display)
- Test: `test_space_fleets.py`, `test_te_popups.py`, `test_space_race_labels.py`

**Interfaces:**
- Produces:
  - **The action** `set_pick`: `sr_fl_set_pick_at = { N }` sets `sr_fl_dest_pick_<N>` to `scope:pick`, a location code from `glw.LOCATIONS`.
  - **The scripted GUI** `sr_fleet_set_dest_sgui`, saved scopes `op` and `pick`, `is_valid`:
    - `sr_fl_op_check = { TEST = at_location }`;
    - the pick isn't the fleet's own location (a `custom_tooltip`, `sr_fl_req_other_location_tt`);
    - `DO = set_pick`.
  - **Per-slot display value** `sr_disp_fl_<n>_why`: 0 may go, 1 refitting, 2 below the minimum strength, 3 Earth's launches barred. These are `may_depart`'s slot-wide terms. The per-leg term, delta-v, is drawn per row.
  - **Generated type** `te_sr_dest_popup` (below): nine bodies, body `n` visible on `GetVariableSystem.HasValue('te_popup', 'sr_dest_<n>')`. A body's content shows on the same test as slot `n`'s `fl_visible`; otherwise its only line is `je_space_race_widget_dp_gone` ("This fleet is gone."). Each holds the fleet line (where, strength, delta-v, supply: the same textboxes as `fl_where`, `fl_strength`, `fl_dv`, `fl_supply`), the reason note on `sr_disp_fl_<n>_why`, and one `te_sr_dest_row` per location.
  - **`te_sr_dest_row`.** It is shown unless the location is the fleet's own. Its cells:
    - the location's name;
    - the leg's months (`sr_fl_<n>_leg_months_<loc>`);
    - the leg's delta-v against `sr_fl_<n>_dv_value`, red when short;
    - for a fleet at Earth, the window (`sr_window_months_to_next_<body>`; open or the months to it; blank for other legs);
    - our worlds there and the hostile strength there (`sr_loc_ai_enemy_fleets_<loc>`);
    - a button with `onclick` = Execute `sr_fleet_set_dest_sgui` (`op` n, `pick` code) **and** `GetVariableSystem.Clear('te_popup')`, with the `_reasoned` tooltip.
- Consumes: `te_ui_popup` and the host pattern (PR 2).

- [ ] **Step 1: Write the failing tests.**
  - In `test_space_fleets.py`, add `DestinationPopupTest`:
    - `test_one_body_per_slot_and_one_row_per_location`;
    - `test_each_row_passes_its_slot_and_location`: the set of `op` literals is `{n}`, the set of `pick` literals is `{loc.code}`;
    - `test_picking_closes_the_popup`;
    - `test_a_body_for_an_empty_slot_shows_only_its_note`: the content's visible is the slot row's `fl_visible` test, and the gone note's is its negation;
    - `test_the_why_value_covers_may_depart_s_slot_terms`: the body of `sr_disp_fl_<n>_why` names `refitting`, `sr_fl_minimum_strength` and `sr_launches_barred`.
  - Update the scripted GUI count to 13 and add `set_pick` to `SLOT_ACTIONS`' test.
  - In `test_te_popups.py`, extend `test_bodies_read_the_entry_through_get_player_journal_entry` to `te_sr_dest_popup`.
  - Add `test_the_pick_button_opens_the_popup`: `fl_pick_button`'s override sets `te_popup` to `sr_dest_<n>`, and its `enabled` and tooltip stay `sr_fleet_pick_sgui`'s, which now explains only why a fleet can't pick.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build it.**
  - Generator: the action, the values and the rows. The row gets our worlds at the location from a new generated value, `sr_loc_ours_count_<loc>` (none exists).
  - The scripted GUI.
  - The GUI types. The popup body is 600 wide. The generator writes the whole `type te_sr_dest_popup = te_ui_popup` into `sr_fleets_generated_rows.gui`: `popup_visible` is the OR of the nine `HasValue`s, and `popup_list` holds the gate, the datacontext and the nine bodies. `space_race_widget.gui` holds only `te_sr_dest_row`.
  - `sr_fl_step_pick_at` stays for the AI and the console.
  - Loc:
    - `je_space_race_widget_dp_title` "Fleet Destination"
    - the column heads
    - the four `why` notes ("Refitting: it can pick now and leave when the refit ends.", …)
    - `sr_fl_req_other_location_tt`
- [ ] **Step 4: Run** `test_space_fleets.py test_te_popups.py test_space_race_labels.py test_space_race_layout.py`, `gen_space_fleets.py --check` and `check_gui_lint.py`. Expected: PASS.
- [ ] **Step 5: Commit.**

### Task 3.2: posture buttons and the target popup

**Files:**
- Modify: `scripts/generators/gen_space_fleets.py`, `common/scripted_effects/sr_fleet_combat_effects.txt` (`sr_fl_set_posture_at`), `common/scripted_guis/sr_fleet_sguis.txt` (`sr_fleet_set_posture_sgui`, `sr_fleet_set_target_sgui`), `space_race_widget.gui` (`te_sr_fleet_row`'s posture line; `te_sr_ftarget_popup`), `gui/te_popups.gui`
- Test: `test_space_fleets.py` (`InterdictionTest`, `LunarAtEarthTest`, new `PostureRowTest`)

**Interfaces:**
- Produces:
  - **`sr_fl_set_posture_at = { N }`.** It reads `scope:pick` (1–4) and does what `sr_fl_step_posture_at`'s branch landing on that posture does:
    - 3: needs `has_hostile_world`, steps to a hostile target unless the target is hostile, then `sr_fl_charge_free_at`.
    - 4: needs `has_interdict_world`, removes `_destroy`, steps to an interdictable target unless the target is one, then `sr_fl_charge_icpt_at`.
    - 1 or 2: removes `_destroy` and `_icpt`.
    - Always: `sr_icpt_rebuild`.
  - **`sr_fleet_set_posture_sgui`** (`op`, `pick`, `DO = set_posture`). Valid on `at_location`, on the pick not being the current posture, and on the pick's rule:
    - 2 is not at Earth;
    - 3 is `has_hostile_world` (at Earth, against a lunar world);
    - 4 is `has_interdict_world`, not at Earth.

    Each rule is its own `custom_tooltip` line.
  - **`sr_fleet_set_target_sgui`** (`op`, `pick` = a world's index in `gen_solar_sites.SITES`, `DO = set_target`). It is valid when the world is at the fleet's location and is a hostile target (posture 3) or an interdictable one (posture 4).
  - **`sr_fl_set_target_at = { N }`**: the target step's set and charge, for the picked world.
  - **The popup key** `sr_ftarget_<n>`: per slot, a world list of the location's worlds (`gen_solar_sites` sites by `location`). Each row is visible while its world is at that location and the fleet's location matches.
- Consumes: Task 3.1's body pattern.

- [ ] **Step 1: Failing tests.**
  - `PostureRowTest.test_four_buttons_lit_on_the_current_posture`.
  - `test_set_posture_repeats_the_steps_side_effects`: `sr_fl_set_posture_at` names `sr_fl_charge_free_at`, `sr_fl_charge_icpt_at`, `sr_icpt_rebuild`, and the two target steps.
  - `test_earth_offers_station_and_close_in_only`: rewrite `LunarAtEarthTest.test_the_earth_posture_options` for the set scripted GUI.
  - `test_the_target_button_opens_the_world_list`.
  - The scripted GUI count goes to 15; `set_posture` and `set_target` go into `SLOT_ACTIONS`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build it.**
  - **The posture buttons:** a second line under the orders while the fleet is at a location. Four `te_sr_action_button`s (approach selector shape, `space_race_widget.gui:250`), 4 × 104 + 3 × 4 = 428.
  - **The target button** sets `te_popup` to `sr_ftarget_<n>` in place of stepping. The step scripted GUIs (`sr_fleet_posture_sgui`, `sr_fleet_target_sgui`) stay for the console and as the hover's text. The GUI stops calling their `Execute`.
  - Fix the width comment and `test_space_race_labels.py`'s posture cells.
- [ ] **Step 4: Run** the PR 3 tests. Expected: PASS.
- [ ] **Step 5: Docs, gate, PR, whole-branch review** as PR 2's Steps 5–7.
  - Player guide: Space Fleets (picking a destination, posture buttons).
  - Play-test checks: nine bodies switch with the slot; picking closes the popup and Go then works; a posture's price is charged once.

---

## PR 4: Transfer (spec § 6)

Branch `feat/sr-fleet-transfer`. Depends on PR 2 (merged). **Task 4.2 gets its own review** (novel script, engine-silent if wrong).

Facts this PR rests on:
- **Merge:** `sr_fl_merge = { N M }` (gen:772) adds every `sr_fl_<N>_<role>` and `_<role>_full` into M through `sr_fl_add_role_part`. Roles are war, rapid, siege, carrier and tender. It sums marines, takes the lower drive and the later `refit_until`, and refills M's delta-v and supply to the lower fill share.
- **Detach:** `sr_fl_detach` halves every role and the marines.
- **Strength floor:** `sr_fl_minimum_strength` is 0.05. `can_detach` needs four times that.

**My call, changing the spec:** `sr_fl_detach` and `sr_fl_merge` keep their bodies, so the AI paths don't change. `sr_fl_transfer` is new and shares their helpers, rather than turning them into wrappers. That is less risk for the same player result.

### Task 4.1: the Transfer popup

**Files:**
- Modify: `gen_space_fleets.py` (rows, display values), `sr_fleet_sguis.txt`, `space_race_widget.gui` (`fl_merge_button` and `fl_detach_button` become one `fl_transfer_button`; `te_sr_xfer_popup`), `gui/te_popups.gui`, loc
- Test: `test_space_fleets.py` (`TransferPopupTest`), `test_space_race_labels.py`

**Interfaces:**
- Produces:
  - **The amounts:** country variables `sr_det_amt_<role>` for role in `war`, `rapid`, `siege`, `carrier`, `tender` and `marines`.
  - **Where to:** `sr_det_to`. 0 means a new fleet in the lowest empty slot; m means slot m.
  - **Display values:** `sr_disp_det_amt_<role>` (the amount clamped to the slot's current role), `sr_disp_det_after_<role>_<from|to>`.
  - **Scripted GUIs:**
    - `sr_fleet_xfer_open_sgui` (`op`): sets each amount to the role ÷ 2 (`round = yes`) and `sr_det_to` to 0.
    - `sr_fleet_xfer_step_sgui` (`op`, `pick` = role code 1–6, `step` = the signed change). `change_variable` the amount, then clamp it to 0 and the role's current value.
    - `sr_fleet_xfer_to_sgui` (`op`, `pick` = 0 or a slot at N's location).
    - `sr_fleet_transfer_sgui` (`op`): runs Task 4.2's `sr_fl_<n>_transfer_now`. Its `is_valid` is the spec's refusals, each a `custom_tooltip` line: something moves; N keeps `sr_fl_minimum_strength` unless all of N goes into an existing fleet; a new fleet gets at least that; the target's marines fit its capacity; an empty slot exists for a new fleet.
  - **The keys:** click `step` ±1; Shift ±10; Ctrl ±100; Alt ±1,000; right-click ±100,000, which the clamp turns into all or none.
    - The `−` button: `onclick` −1, `onshift` −10, `onctrl` −100, `onalt` −1,000, `onrightclick` −100,000.
    - The `+` button: the same, signed +.
    - Tooltips list them, as `TE_CM_INCREASE_TT` and `TE_CM_DECREASE_TT` do.
    - Three chained `AddScope`s (`op`, `pick`, `step`). Two are proven; the third goes on the play-test list, and the fallback is `pick` = role × 100 + step code.
  - **The open button:** `fl_transfer_button`'s `onclick` runs `sr_fleet_xfer_open_sgui` and sets `te_popup` to `sr_xfer_<n>`. It is enabled while the slot `can_detach` or `can_merge`.
- Delete: `sr_fleet_detach_sgui`, `sr_fleet_merge_sgui` (the GUI was their only caller; `ai_is_valid = no`).

- [ ] **Step 1: Failing tests.**
  - `TransferPopupTest.test_each_role_row_steps_its_own_amount`.
  - `test_the_keys_match_the_construction_market`: the five handlers with these signs.
  - `test_opening_resets_the_amounts`.
  - `test_the_target_buttons_list_the_new_slot_and_fleets_at_the_location`.
  - `test_a_body_for_an_empty_slot_shows_only_its_note`, as in Task 3.1. Transfer's `is_valid` also starts with `sr_fl_op_check = { TEST = at_location }`.
  - The scripted GUI count: +4 −2.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build** the GUI and scripted GUIs.
  - Loc: `je_space_race_widget_xf_title` "Transfer", the role names (reuse `je_space_race_widget_fl_role_*` if present), `je_space_race_widget_xf_new` "New fleet", `je_space_race_widget_xf_into` "Into fleet [n]", the refusal lines.
- [ ] **Step 4: Run** the tests. Expected: PASS. **Commit.**

### Task 4.2: `sr_fl_transfer` (reviewed)

**Files:**
- Modify: `gen_space_fleets.py` (`render_merge_detach`), regenerated effects
- Test: `test_space_fleets.py` (`TransferTest`)

**Interfaces:**
- Produces:
  - `sr_fl_<n>_transfer_now`: reads `sr_det_to`. 0 picks the first empty slot, as `_detach_now` does; else m.
  - It calls `sr_fl_transfer = { N = n M = m }`, which:
    - takes each role's share as `sr_disp_det_amt_<role>` ÷ the role's current value (0 when the role is empty);
    - moves that share of the role and of its `_full`, so the damage ratio holds, through `sr_fl_add_role_part`;
    - moves marines by amount.
  - **Into an empty slot, as detach does:** M copies N's location, drive, posture, refit and supply. Both fleets' delta-v is set to capacity × N's delta-v share.
  - **Into an existing fleet, as merge does:** M's delta-v and supply refill to the lower fill share, the lower drive and the later refit.
  - All of N into an existing fleet clears N (`sr_fl_clear_at N`). Then `sr_loc_rebuild`.

- [ ] **Step 1: Failing tests.**
  - `TransferTest.test_amounts_are_clamped_before_moving`: shares read the clamped display value, never the raw variable.
  - `test_full_and_current_move_by_one_share`.
  - `test_all_into_an_existing_fleet_clears_the_source`.
  - `test_a_new_fleet_copies_location_posture_drive_and_refit`.
  - `test_each_slot_pair_is_generated_once` (9 × 8 into existing, plus 9 new).
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Generate it.** Keep `sr_fl_detach` and `sr_fl_merge` unchanged for the AI.
- [ ] **Step 4: Run them, plus** `test_space_fleets.py` whole. Expected: PASS. **Commit.**
- [ ] **Step 5: Task review** by one reviewer on this task's diff (the role and share math, the refusals against the effect). Fix, then run PR 2's Steps 5–7 (docs, gate, PR, whole-branch review).
  - Player guide: the Transfer popup replaces Detach and Merge.
  - Play-test checks: Shift, Ctrl, Alt and right-click on a scripted-GUI button; the three-scope call; a damaged role keeps its ratio.

---

## PR 5: the Extraplanetary Base cell and the on-completion refresh (spec § 8)

Branch `feat/sr-ebase-cell`. Independent of PRs 2–4.

Facts:
- **`sr_ebase_refresh`** (`sr_colony_module_effects.txt:374-418`) runs from `space_race_on_action` monthly. It sets `var:sr_ebase_room`, `var:sr_ebase_grade` and `var:sr_ebase_units` through the generated `sr_ebase_fill` (`render_module_effects`, gen_solar_sites:2244-2266).
- **Levels:** `sr_ebase_levels` and `sr_ebase_queued_levels` (built plus queued) are at `sr_colony_module_values.txt:94` and `:104`.
- **Room:** `sr_ebase_room_total` is generated.
- **Past the room:** −75% is `OVERFLOW_GRADE` (gen:313), written inline.
- **The overview grid** (`space_race_widget.gui:7183`) has two `te_banking_ov_cell`s a row. Row 2 is Modules and Next Window.
- **The building hook:** `te_on_building_built` (`extra_on_actions.txt:625-643`) is the mod's own on_action on `on_building_built`. Never add `effect = {}` to a vanilla on_action itself.
- **Free event ids:** `space_race_events` next is 110. Coordinate with PR 6, which takes 111.

### Task 5.1: next-grade fill and the cell

**Files:**
- Modify: `gen_solar_sites.py` (`render_module_effects`: a second fill pass writing the next grade), `sr_colony_module_effects.txt` (`sr_ebase_refresh` sets `var:sr_ebase_next_grade`), `space_race_display_values.txt` (`sr_disp_ebase_queued`, `sr_disp_ebase_next_grade`), `space_race_widget.gui` (row 3 of the grid; the Modules view's Extraplanetary Base row), loc
- Test: `test_solar_sites.py` (`EbaseCellTest`), `test_space_race_layout.py` (`DisplayValuesTest` reads them), `test_space_race_labels.py`

**Interfaces:**
- Produces:
  - **`sr_ebase_next_fill`** (generated): walks `ebase_tiers()` best first with built **plus queued** levels and stores the first unfilled tier's grade in `var:sr_ebase_next_grade`, or `OVERFLOW_GRADE` past all the room.
  - **`sr_disp_ebase_queued`:** `sr_ebase_queued_levels` − `sr_ebase_levels`, floored at 0.
  - **`sr_disp_ebase_next_grade`:** `var:sr_ebase_next_grade`, guarded.

- [ ] **Step 1: Failing tests.**
  - `EbaseCellTest.test_next_fill_walks_the_tiers_with_queued_levels`: the generated effect reads `sr_ebase_queued_levels` and every tier's room in `ebase_tiers()` order, and ends at `OVERFLOW_GRADE`.
  - `test_the_cell`: a `te_banking_ov_cell` in grid row 3 with caption `je_space_race_widget_ovc_ebase_cap`. The word reads levels, queued and room, red past the room. The figure reads `sr_disp_ebase_next_grade`. The hover is `je_space_race_widget_ovc_ebase_tt`.
  - `test_the_modules_row_shows_queued`: the row's text is a `SelectLocalization` on `sr_disp_ebase_queued` > 0.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build it.** Visible under `sr_disp_colonies_contested`, as the Modules cell.
  - Loc:
    - word "[levels] (+[queued]) / [room]"
    - figure "next at [grade]%", with a true minus
    - the hover gives the average now, the room by colony (reuse `je_space_race_widget_bases_tt_<key>` lines or a summary), and the best-room-first rule
- [ ] **Step 4: Run** them and `gen_solar_sites.py --check`. Expected: PASS. **Commit.**

### Task 5.2: refresh when a base is built

**Files:**
- Modify: `common/on_actions/extra_on_actions.txt` (an arm in `te_on_building_built`'s effect, and the same for `on_building_expanded` through a mod on_action), `events/space_race_events.txt` (`space_race_events.110`, hidden `country_event`, `immediate = { sr_ebase_refresh = yes }`), `sr_colony_module_effects.txt` (the self-check)
- Test: `test_solar_sites.py` (`EbaseRefreshTest`)

- [ ] **Step 1: Failing tests.**
  - `test_the_hooks_fire_a_hidden_country_event_on_the_owner`: an `is_building_type = building_space_mine` limit, then `owner = { trigger_event = { id = space_race_events.110 } }`, in both hooks, and no `effect` on a vanilla on_action.
  - `test_the_event_is_hidden_and_refreshes`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build it.**
  - Self-check `TE_SELF_CHECK OK|BROKEN ebase_on_complete`, with the levels before and after, once a game. Pattern: the `module_fabrication` check (`sr_colony_module_effects.txt:428-447`).
  - Add it to the playtest Self-checks table. The monthly refresh stays.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Docs, gate, PR, whole-branch review.**
  - Player guide: Extraplanetary Bases (the cell, "next at").
  - Play-test checks: the cell's live `ScriptValue` loops don't stutter with the panel open (fallback: read the refresh's copies); `.110` fires on completion.

---

## PR 6: the Earth alert (spec § 9)

Branch `feat/sr-earth-alert`. Independent of PRs 2–5. **Task 6.1 gets its own review.**

Facts:
- **`.100` has no once-per-leg marker:** it fires from `sr_fl_dispatch_alert` at dispatch only. For Earth it never fires (`sr_loc_held_earth = { always = no }`), so there is no Earth arm to remove.
- **In flight** means `sr_fl_<n>_dest` is set and `sr_fl_<n>_loc` is not. `sr_fl_<n>_arrive` is the landing month.
- **Inbound records** (`sr_loc_inbound_*`) don't separate hostile from friendly and carry no strength.
- **The template:** `sr_fl_ai_threatened_<loc>` (gen:625-639) already uses `any_in_global_list = { variable = sr_fleet_powers has_war_with = prev sr_fl_any_bound = { CODE } }`. It is generated for every location but Earth.
- **Notices without options** are `common/messages/` entries (`notification_type = feed`). Their loc is `notification_<name>_name`, `_desc` and `_tooltip` in `te_notifications_l_english.yml`.
- **The loud notice** takes `.106`'s shape (`events/space_race_events.txt:5198-5230`; pinned by `test_space_fleets.py:758-772`).

### Task 6.1: the values and the notices (reviewed)

**Files:**
- Modify: `gen_space_fleets.py` (values per location; `sr_earth_alert_step`; the per-slot lists in the slot-clear), `common/messages/extra_messages.txt` (`sr_earth_hostile_notice`, `color = bad`), `events/space_race_events.txt` (`.111`, the `.106` shape), `common/on_actions/space_race_on_actions.txt` (call the step beside `sr_earth_notice_step`, same gate), loc
- Test: `test_space_fleets.py` (`EarthAlertTest`)

**Interfaces:**
- Produces:
  - **Per location** (country scope, the viewer), generated:
    - `sr_loc_hostile_inbound_strength_<loc>`: the sum of `sr_fl_<n>_strength` over powers in `sr_fleet_powers` at war with the viewer, for slots bound for `<loc>` and in flight;
    - `sr_loc_hostile_inbound_first_<loc>`: the earliest `sr_fl_<n>_arrive`.
  - **Trigger** `sr_earth_alert_loud`: hostile strength inbound to Earth is above 0, and either we have no `sr_fl_at_earth` or the inbound strength exceeds it.
  - **`sr_earth_alert_step`** (the viewer's monthly pulse). For every power at war with the viewer and every slot of it in flight to Earth:
    - When loud and the viewer isn't on that slot's `sr_fl_<n>_warned_loud` list: fire `.111` (the power saved for the loc), and add the viewer to both lists.
    - Else, when the viewer isn't on `sr_fl_<n>_warned_quiet`: `post_notification = sr_earth_hostile_notice` and add the viewer to it.
  - **The lists** are cleared when the slot is dispatched or lands. Add them to the slot-clear (`test_a_cleared_slot_clears_every_variable`).
  - Because the lists sit on the moving fleet, a war declared mid-flight notices the next month, and our own or allied fleets never count.

- [ ] **Step 1: Failing tests.**
  - `EarthAlertTest.test_only_powers_at_war_count`: the generated values and the step filter on `has_war_with`.
  - `test_once_per_leg_and_volume`: the step tests and adds to each list; dispatch and arrival clear them.
  - `test_loud_replaces_quiet_in_the_same_month`.
  - `test_the_loud_notice_has_106_s_shape`.
  - `test_the_step_runs_beside_the_blockade_notice`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build** the generator and the script, then regenerate.
  - Loc:
    - quiet: "A Hostile Fleet Is Bound for Earth" / "A fleet of a power at war with us is on its way to Earth."
    - loud `.111`: "Earth Is Threatened", with the power's name, the landing month and both strengths
- [ ] **Step 4: Run them.** Expected: PASS. **Commit.**
- [ ] **Step 5: Task review** by one reviewer on the step's logic: lists, war mid-flight, loud versus quiet, the slot-clear.

### Task 6.2: the overview cell

**Files:**
- Modify: `space_race_display_values.txt` (`sr_disp_earth_hostile` 0 none / 1 quiet / 2 loud, `sr_disp_earth_hostile_months`, `sr_disp_earth_hostile_strength`, `sr_disp_earth_our_strength`), `space_race_widget.gui` (a `te_banking_ov_cell` in grid row 3, visible while `sr_disp_earth_hostile` ≥ 1 under Full Colonies), loc
- Test: `test_space_race_layout.py`, `test_space_race_labels.py`

- [ ] **Step 1: Failing test** `EarthAlertCellTest.test_the_cell_reads_the_alert_values`: red word on 2.
- [ ] **Step 2: Build it.**
  - The word is "Earth in [months] mo" and the figure "[theirs] vs [ours]".
  - The hover gives the hostile fleets' count, total, earliest landing and our strength at Earth.
  - **My call, narrowing the spec:** no per-fleet list in the hover, since a loc line can't loop.
- [ ] **Step 3: Run** the tests. Expected: PASS.
- [ ] **Step 4: Docs, gate, PR, whole-branch review.**
  - Player guide: Space Fleets (the Earth alert).
  - Play-test checks: the notice's feed type; the loud event once; a war declared mid-flight.

---

## PR 7: fleet upkeep, and no fleet orders without a Space Command (spec § 10)

Branch `feat/sr-fleet-upkeep`. Independent. **Both tasks get a task review.**

Facts:
- **Today's upkeep:** `sr_fleet_upkeep_goods` (`space_race_modifiers.txt:367-372`) multiplies Launch Capacity, Advanced Materials and electricity by 0.01 a unit. `sr_fl_upkeep_apply` puts it on every `building_space_command` at `multiplier = root.var:sr_fleet_upkeep_units`.
- **The yard methods:** the four in `sr_space_command_pms.txt` have no `unscaled` block today.
- **Registration:**
  - `goods_input_radios_mult` is vanilla's (`01_building_modifier_types.txt:2668`). **Correction to the spec:** three mults need registering, not four: `telephones`, `digital_assets` and `robotics`.
  - `electronic_components` and `fertilizer` are registered.
  - Check every `goods_input_<good>_add` of the six too: the mod registers `electronic_components`, `digital_assets` and `robotics`.
- **The AI sets posture directly** in `sr_fl_ai_lunar_assault`, `sr_cb_check_target`, `sr_fl_end_icpt`, `sr_fl_gather_at` and on arrival. Only the voluntary one (the lunar assault) is an order; the rest are the combat model's own fallbacks and stay.
- **Refit, repair and refill** all run in `sr_fl_month_at` (`sr_fleet_effects.txt:201-255`).
- **Template:** `sr_sc_qualifies` (`sr_fleet_triggers.txt:60-66`) is the shape for the new trigger.

### Task 7.1: the maintenance line (reviewed)

**Files:**
- Modify: `common/production_methods/sr_space_command_pms.txt` (an identical `unscaled` block in all four methods: `goods_input_electronic_components_add = 20`, `goods_input_telephones_add = 20`, `goods_input_radios_add = 20`, `goods_input_digital_assets_add = 10`, `goods_input_robotics_add = 20`, `goods_input_fertilizer_add = 40`), `common/static_modifiers/space_race_modifiers.txt` (`sr_fleet_upkeep_goods`: the six `goods_input_<good>_mult = 9`, the three old ones removed), `common/modifier_type_definitions/mod_entity_modifier_types.txt` (the three mults, in the `electronic_components` block's shape: `color = bad`, `percent = yes`, `ai_value = -250`), `sr_fleet_effects.txt` (self-check), loc (the three places that say 1%: `te_concepts_l_english.yml:2663-2665`, `te_journal_entries_l_english.yml:1676-1678`, `te_miscellaneous_l_english.yml:6450`)
- Test: `test_space_fleets.py` (`UpkeepTest`), `test_space_race_labels.py` (`FLEET_UPKEEP_PCT`)

- [ ] **Step 1: Rewrite `UpkeepTest`.**
  - `test_the_upkeep_goods_are_the_maintenance_line`: the static modifier's goods equal the six. Every method's `unscaled` block is identical, with the base values above. No other input of any method names one of the six.
  - `test_every_mult_and_add_is_registered`: in the mod's or vanilla's modifier type files.
  - Keep `test_the_upkeep_is_on_the_building_and_refreshed_once`.
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Build it.**
  - Self-check `TE_SELF_CHECK OK|BROKEN fleet_upkeep_line`: a week after the first apply, a Space Command's `modifier:goods_input_robotics_mult` equals 9 × units.
  - Loc gives the rule ("+900% of Space Command's maintenance goods for every 10 points of strength, the reserve's included") and the base a week on hover.
- [ ] **Step 4: Run** `test_space_fleets.py test_space_race_labels.py`. Expected: PASS. **Commit.**

### Task 7.2: no fleet orders without a Space Command (reviewed)

**Files:**
- Modify: `common/scripted_triggers/sr_fleet_triggers.txt` (`sr_sc_operational`), `gen_space_fleets.py` (into every `sr_fl_<n>_may_depart_<loc>`), `sr_fleet_sguis.txt` (posture and target orders' `is_valid`, both step and set), `sr_fleet_effects.txt` (`sr_fl_month_at`: a refit doesn't start; one under way pauses by pushing `refit_until` a month; repair waits; refill stays), the generated `sr_fl_ai_lunar_assault` (needs it), `space_race_display_values.txt` (`sr_disp_sc_operational`), `space_race_widget.gui` (Space Fleets' note above its rows), loc
- Test: `test_space_fleets.py` (`NoSpaceCommandTest`)

**Interfaces:**
- Produces: `sr_sc_operational = { any_scope_state = { sr_state_held_by_owner = yes any_scope_building = { is_building_type = building_space_command level >= 1 } } }` (country scope). Its `custom_tooltip` line is `sr_fl_req_space_command_tt`.

- [ ] **Step 1: Failing tests.**
  - `NoSpaceCommandTest.test_operational_needs_a_held_level`.
  - `test_every_may_depart_needs_it`.
  - `test_posture_and_target_orders_need_it`: the set scripted GUIs, if PR 3 has merged; the step ones otherwise.
  - `test_refit_pauses_and_repair_waits`.
  - `test_refill_still_runs`.
  - `test_the_ai_lunar_assault_needs_it`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build** it and regenerate.
- [ ] **Step 4: Run** `test_space_fleets.py`. Expected: PASS. **Commit.**
- [ ] **Step 5: Task review** of both tasks' diff. Then docs (player guide `16-space.md:1003-1026`, `:1157`; the method table gains no column; the upkeep paragraph gives the six goods, the base and +900%), the gate, the PR and the whole-branch review.

---

## PR 8: tabs (spec § 11)

Branch `feat/sr-colonization-tabs`. Independent. Rebase over whatever of PRs 2–7 has merged.

Facts:
- **The tabs go inside `te_sr_solar_colonization_status`**, around its sections, not in the window or the journal wrapper. `test_te_systems_window.TabContentTest` wants the window's instances to equal the journal root's.
- **`ColoniesTest.test_the_colonization_panel_order`** (`test_space_race_layout.py:465-480`) matches `^\t\t(te_sr_sec_\w+) = \{\}`, so the wrappers break it.
- **`FlagTest`** counts `Toggle` flags, so the tab key uses Set, Clear and HasValue, as `sr_colony_view` does.

### Task 8.1: the tab row and the four tabs

**Files:**
- Modify: `space_race_widget.gui` (type `te_sr_tab_button`, copied from `te_sr_colony_view_button`; the row and four wrappers in `te_sr_solar_colonization_status`), loc, `test_space_race_layout.py`, `test_space_race_labels.py`

**Interfaces:**
- Produces: the client key `sr_tab`, which is absent for Mission Control or `fleets`, `colonies` or `system`. The wrappers:
  - **Mission Control:** `te_sr_status_sections`.
  - **Fleets:** `te_sr_sec_colony_fleets`, `te_sr_sec_space_command`, `te_sr_sec_space_fleets`.
  - **Colonies:** `te_sr_sec_colonies`.
  - **Solar System:** `te_sr_sec_solar_system`, `te_sr_sec_how_colonies`.

- [ ] **Step 1: Failing tests.**
  - `TabTest.test_each_tab_holds_its_sections`: depth-agnostic, in order.
  - `test_the_default_tab_is_mission_control`: the first wrapper's visible is `Not( GetVariableSystem.Exists('sr_tab') )`.
  - `test_each_button_sets_its_tab_and_greys_on_it`.
  - `test_the_tab_row_shows_while_the_entry_runs`.
  - Rewrite `test_the_colonization_panel_order` to read the sections across the wrappers.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build it.** Four buttons of 112 make 448 + 3 × 4 = 460. Loc: `je_space_race_widget_tab_mission`, `_fleets`, `_colonies`, `_system`.
- [ ] **Step 4: Run** `test_space_race_layout.py test_te_systems_window.py test_space_race_labels.py`. Expected: PASS.
- [ ] **Step 5: Docs, gate, PR, whole-branch review.**
  - Player guide: the panel's tabs, and the screenshot caption at `16-space.md:144`.
  - Play-test checks: the tab is remembered while the session runs; both hosts.
