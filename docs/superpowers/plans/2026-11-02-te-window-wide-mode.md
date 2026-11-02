# Timeline Extended window: wide mode and mirrored tabs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A toggle between the Timeline Extended window's side-panel width and a full-screen frame; the ten system tabs that live in vanilla panels also shown in the window; a wide layout for all fifteen tabs; and the shared pieces that keep the hosts from drifting apart.

**Architecture:** Four PRs (A–D below), each from `main`. A is a refactor with no visible change: a shared tab frame type, a body type per tab, and the window's strip, selection templates and tab mounts generated from one registry (`scripts/generators/gen_te_systems_window.py`). B adds the full-screen frame (a copy of vanilla's `fullscreen_block_window`) and the toggle. C moves the ten vanilla-panel tabs onto body types, which both their host and the window use, and adds them to the registry as strips 2 and 3. D adds shared column types and a wide composer per tab, guarded by one narrow-versus-wide check. The window reads every system through the same `GetPlayerJournalEntry` datacontexts as today.

**Tech Stack:** Victoria 3 1.14.5 Paradox GUI, Python 3.11/3.12 generator and `unittest` structural tests.

**Spec:** [docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md](../specs/2026-11-02-te-window-wide-mode-design.md) (§ numbers below are its sections). House style: `docs/guides/gui_style_guide.md`. Engine and GUI gotchas: `docs/guides/gui_modding_guide.md`. The window today: `docs/systems/system_panels_feasibility.md` §§ 3.1–3.6 and `gui/te_systems_window.gui`'s header.

## Global Constraints

- **One PR per section, each from `origin/main`.** On the owner's machine use a sparse worktree: `git -C ~/src/Vic3TimelineExtended worktree add --no-checkout -b <branch> ~/src/vic3te-<name> origin/main`, then `git sparse-checkout set --no-cone '/*' '!/gfx/'` and `git checkout <branch>`. In a cloud session, the session's own checkout on its branch. Never `POST /reload` from a worktree.
- **Order:** A, then B and C (C needs A; its footer task needs B's wide frame, so C goes after B or adds the wide footer in a follow-up), then D0, then D1–D3 in parallel. The owner merges every PR. No self-merge.
- **Python:** the main checkout's venv (`~/src/Vic3TimelineExtended/.venv/bin/python`; in a cloud container `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-docs.txt`). Tests: `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent <venv python> -m pytest -q -p xdist -n 8 <files>`. Run each task's named tests. Run the full suite once before opening the PR.
- **The generated file is never hand-edited.** Edit the registry or the renderers in `gen_te_systems_window.py` and run it. `--check` must exit 0 before every commit.
- **Files:** exactly one UTF-8 BOM on every `.gui`, `.txt` and `.yml` (a script that writes one must decode with `utf-8-sig`); tab indentation. `docs/guides/gui_modding_guide.md` is CRLF: edit it with Edit, then confirm `grep -c $'\r$'` equals `wc -l`.
- **GUI rules that bite here:**
  - `And` and `Or` take exactly two arguments: build longer ones as binary trees.
  - `@panel_width_*` variables are file-local: write literals (`554`, `540`, `520`, `480`) in files that don't define them.
  - One `visible` per widget (`test_te_systems_window.py`'s `test_one_visible_per_widget`): where a template is `using`d, put any further condition on a child.
  - A gate sits on a parent of a `GetPlayerJournalEntry` datacontext, never on the widget that carries it (gotcha #29).
  - A body type exposes what a host varies as a named block declared inside its own blockoverride (vanilla's `diplo_actions_button` declares `icon_texture` inside its override of `button_icon_round`'s `icon`; the Space Race's `sr_debris` the same way). An instance never overrides a block the body type itself already overrode.
- **Loc:** American English. The window's keys go in `localization/english/te_miscellaneous_l_english.yml` beside `te_window_tab_nation`; run `python3 organize_loc.py` and commit everything it moves.
- **Players are sent to the tab** (style guide rule 9). Text naming "the UN tab of the Diplomacy panel" stays true and is not rewritten.
- **Every PR's body** carries a "Player guide" line. A and D0 are no player-facing change. B and C update `docs/player_guide/01-introduction.md`'s window section, then `<venv python> scripts/build_player_guide.py`, committing chapter and PDF together.
- **Gate before each PR:**
  - `scripts/analysis/check_gui_lint.py`;
  - `gui_reference_audit.py --strict`, `loc_coverage_audit.py --strict`, `concept_reference_audit.py --strict`;
  - `organize_loc.py --check`, `scripts/analysis/check_loc_spelling.py --check`, `scripts/analysis/check_localization_files.py`;
  - `.venv/bin/ruff check .`, and `gen_te_systems_window.py --check`;
  - `test_tax_code_bypass.py`, `test_nightly_audit_select.py`, `test_test_files_main_block.py` (a new test file ends with the `unittest.main()` block);
  - the suite.
- **In-game checks never gate a merge.** Each PR adds its own to `docs/testing/te-window-wide-playtest.md` (created in PR B).

## Review Focus

1. **The same tab in two hosts.** Expected: identical sections, order, gates and link. Pinned by `test_te_system_tab_bodies.py`'s `test_every_host_instances_its_body` (PR C) and each layout test reading the body type, not the host.
2. **A body that reads its host panel.** Expected: none. `InformationPanel.`, `MarketPanel`, `PopsOverviewPanel`, `BudgetPanel`, `SocietyPanel` and `MilitaryPanel` appear only in host files. Pinned by `test_no_body_reads_a_host_panel` (PRs A and C). Global Warming's market switch and map-mode reset, and the Reserve's other-market note, stay in `market_panel.gui`.
3. **The shown tab.** Expected: the last one chosen while it is open, else Nation; one half of each slot on the strip shows. The toggle keeps the tab. Pinned by `SelectionTest`, rebuilt per stored value (PR A, extended in C), and `test_the_toggle_keeps_the_tab` (B).
4. **Banking with a monetary stance and no entry** (#805). Expected: in the window too, the tab opens on the readout under Monetary Policy. Pinned by the Banking registry entry's open expression and `te_banking_tab_body`'s two headers (PR C).
5. **Demographics in the window.** Expected: the player's census, no Wealth strata incomes (they read `PopsOverviewPanel`). Pinned by `te_demog_window_sections` in `test_demographics_layout.py`'s hosts and the window copy of `test_demographics_census_window.py`'s context check (PR C).
6. **A section added to a narrow composer.** Expected: the wide layout fails its test until it places it. Pinned by `gui_test_helpers.assert_wide_matches_narrow` (PR D0).

---

## PR A: the window's tabs from a registry (no visible change)

Branch `feat/te-window-registry`. Spec §§ 9.1, 9.3.

### Task A1: the shared tab frame

**Files:**
- Modify: `gui/te_system_tab_widgets.gui` (type `te_system_tab_frame` in `types te_system_tab_widgets`)
- Create: `test_te_system_tab_bodies.py`

**Interfaces:**
- Produces: `type te_system_tab_frame = flowcontainer` with blocks `tab_header`, `tab_before_gate`, `tab_gate`, `tab_entry`, `tab_content`, `tab_open_journal`, `tab_open_journal_font`, `tab_open_journal_tooltip`.

- [ ] **Step 1: Write `test_te_system_tab_bodies.py`** with `FrameTest`:
  - `test_the_frame_shape`: the type's body holds, in order, `block "tab_header"`, `block "tab_before_gate"`, then a flowcontainer whose own properties (before its first child) hold `block "tab_gate"` and no `datacontext`, and inside it a flowcontainer with `block "tab_entry"`, `minimumsize = { 520 -1 }`, `block "tab_content"`, and `block "tab_open_journal"` wrapping the button.
  - `test_the_link`: the button has `visible = "[JournalEntry.IsActive]"`, `text = "te_system_tab_open_journal"`, `size = { 480 32 }`, `onclick = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"`, and the font and tooltip blocks.
- [ ] **Step 2: Run it.** Expected: FAIL (no type).
- [ ] **Step 3: Add the type** at the end of `types te_system_tab_widgets`, with a header comment naming the spec and the blocks:

```
	type te_system_tab_frame = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 10

		block "tab_header" {}
		block "tab_before_gate" {}

		flowcontainer = {
			block "tab_gate" {}
			parentanchor = hcenter
			direction = vertical
			ignoreinvisible = yes

			flowcontainer = {
				block "tab_entry" {}
				parentanchor = hcenter
				direction = vertical
				ignoreinvisible = yes
				spacing = 10
				minimumsize = { 520 -1 }

				block "tab_content" {}

				block "tab_open_journal" {
					button = {
						visible = "[JournalEntry.IsActive]"
						using = default_button
						block "tab_open_journal_font" {}
						parentanchor = hcenter
						size = { 480 32 }
						text = "te_system_tab_open_journal"
						block "tab_open_journal_tooltip" {}
						onclick = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"
					}
				}
			}
		}
	}
```

- [ ] **Step 4: Run the test and `check_gui_lint.py`.** Expected: PASS.
- [ ] **Step 5: Commit.**

### Task A2: body types for the window's five tabs

**Files:**
- Modify:
  - `gui/journal_entry_widgets/grand_monuments_widget.gui` (`te_gm_tab_body`);
  - `gui/journal_entry_widgets/colonial_empire_widget.gui` (`te_ce_tab_body`);
  - `gui/te_seabed_widgets.gui` (`te_seabed_tab_body`);
  - `gui/journal_entry_widgets/space_race_widget.gui` (`te_sr_tab_body`).
- Modify: `test_te_system_tab_bodies.py` (`BodyTest`)

**Interfaces:**
- Consumes: `te_system_tab_frame` (A1); `te_sr_window_milestones` (A3, generated).
- Produces:
  - Each frame-based body declares its layout block inside its `tab_content` override: `te_gm_tab_layout`, `te_ce_tab_layout`, `te_seabed_tab_layout`. PR D's wide mounts override them.
  - Nation's body is `te_nation_tab_sections` itself (no frame: no entry, no gate).
  - The Space Race's is a plain flowcontainer, since it holds nine entries: `te_sr_tab_layout` around the milestones and the summary.

- [ ] **Step 1: Extend the test.** `BodyTest.test_window_bodies` checks each body against today's tab content in `gui/te_systems_window.gui`, which the frame replaces:

  | Body | Header text | Gate | Entry | Composers | Link tooltip |
  |---|---|---|---|---|---|
  | `te_gm_tab_body` | `te_window_tab_grand_monuments` | `te_window_grand_monuments_tab_sgui` | `je_grand_monuments` | overview, status, reference | `te_window_grand_monuments_open_journal_tt` |
  | `te_ce_tab_body` | `je_colonial_empire` | `te_window_colonial_empire_tab_sgui` | `je_colonial_empire` | overview, status, reference | `te_window_colonial_empire_open_journal_tt` |
  | `te_seabed_tab_body` | `te_seabed_tab_header` | `te_window_seabed_tab_sgui` | none (`tab_entry` and `tab_open_journal` emptied) | the four seabed panels | none |

  `te_sr_tab_body` holds `te_sr_window_milestones = {}`, then the summary (`te_sr_sec_powers`, `te_sr_sec_orbit`) and the reference (`te_sr_sec_how`), each under `te_window_space_race_tab_sgui`, with today's names (`te_systems_window_space_race_summary`, `te_systems_window_space_race_reference`), widths and spacings.
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Write the four types.** Move each tab's content from `te_systems_window.gui` (the blocks named `te_systems_window_<tab>_tab`) into its body, keeping each header's `using = default_list_position`. The headers go in `tab_header`, the gate's `visible` in `tab_gate` and the datacontext in `tab_entry`. The composers go in `tab_content`, wrapped in `block "<layout>" { … }`. Leave `te_systems_window.gui` as it is until A4.
- [ ] **Step 4: Run the test.** Expected: PASS. Leave `check_gui_lint.py` until A3: `te_sr_tab_body` names `te_sr_window_milestones`, which A3 generates.
- [ ] **Step 5: Commit.**

### Task A3: the generator

**Files:**
- Create: `scripts/generators/gen_te_systems_window.py`
- Create (generated): `gui/te_systems_window_generated.gui`
- Modify: `docs/auto_generated_files.md` (a "Timeline Extended window (explicit regeneration)" section with the file's row)
- Modify: `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS` gains the generated file)
- Modify: `docs/guides/gui_modding_guide.md` (CRLF): a row in "This Mod's GUI Files" for the generated file; the count becomes 51 files (28 replacements, 23 additive)

**Interfaces:**
- Produces `TABS: list[Tab]` and `SR_MILESTONES`. The `Tab` dataclass:
  - `key`, `row`;
  - `label`, `tooltip`, `locked` and `met` (loc keys);
  - `open_` and `strip` (expressions; `None` means always);
  - `unlock` (the scripted GUI whose `IsValid` and `IsValidTooltip` make the grayed tab's checklist);
  - `body` (type) and `layout` (its layout block, or `None`);
  - `wide` (`None` until PR D);
  - `tooltip_expr` (an override).
- Expression helpers: `shown(sgui)`, `valid(sgui)`, `stored(key)`, `and_(a, b)`, `or_all(terms)` (a balanced binary tree), `not_(a)`, each rendering the exact GUI text today's templates use. For example, `shown(s)` renders `GetScriptedGui('<s>').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )`.
- Produces the generated file:
  - the templates `te_systems_window_<key>_selected` / `_unselected` for every tab, and `te_systems_window_tax_probes_selected`;
  - `type te_systems_window_strips_narrow` (a vbox: one vanilla `tab_buttons` per strip in use, then the tax-probes strip);
  - `type te_systems_window_tabs_narrow` (the column: `te_tp_panel`, then a mount per tab);
  - `type te_sr_window_milestones` (the idle note, then one `te_system_tab_frame` per milestone).
- `main(argv)`: no argument writes the file; `--check` exits 1 if it is stale.

- [ ] **Step 1: The registry.** The five tabs of today, strip 1, in today's order:

```python
TABS = [
    Tab("nation", 1, label="te_window_tab_nation", tooltip="te_window_tab_nation_tt",
        open_=None, strip=None, body="te_nation_tab_sections", layout=None),
    Tab("space_race", 1, label="te_window_tab_space_race", tooltip="te_window_tab_space_race_tt",
        locked="te_window_tab_space_race_locked_tt",
        open_=shown("te_window_space_race_tab_sgui"), strip=shown("te_window_space_race_tab_unlock_sgui"),
        unlock="te_window_space_race_tab_unlock_sgui", body="te_sr_tab_body", layout="te_sr_tab_layout"),
    # grand_monuments, colonial_empire: the same shape (te_window_<key>_tab_sgui / _unlock_sgui)
    # seabed: the same, with met="te_window_tab_seabed_met_tt"
]
```

  `unlock` names the scripted GUI whose `IsValid` and `IsValidTooltip` give the checklist. Nation is the fallback: `nation` is always the first entry, and the generator asserts it.
- [ ] **Step 2: The templates.**
  - `T = and_(stored("tax_probes"), shown("te_tp_tab_sgui"))`.
  - A system tab: `selected = and_(not_(T), and_(stored(key), open_))` (`and_(not_(T), stored(key))` when `open_` is `None`), and `unselected = and_(strip, not_(selected))` (`not_(selected)` when `strip` is `None`).
  - Nation: `selected = and_(not_(T), not_(V))` and `unselected = or_(T, V)`, where `V = or_all([and_(stored(k), open_k) …])` over every other tab.

  The five rendered templates must evaluate as today's for every case (Step 6), and the existing test's evaluator should parse them unchanged.
- [ ] **Step 3: The strip.**
  - Per tab on a strip, slot `first` … `fifth` in registry order: `<slot>_button` and `<slot>_button_selected` set `text = "<label>"`.
  - `<slot>_button_tooltip` is the three-branch `SelectLocalization( open, '<tooltip>', SelectLocalization( valid(unlock), '<met>', Concatenate( Localize( '<locked>' ), …IsValidTooltip… ) ) )`, or `tooltip = "<tooltip>"` for an always-open tab, or `tooltip_expr`.
  - `<slot>_button_click` sets `enabled = "[<open>]"` (left out when always open) and `onclick = "[GetVariableSystem.Set('te_systems_window_tab', '<key>')]"`.
  - `<slot>_button_visibility` and `_visibility_checked` are `using =` the two templates.
  - Then the tax-probes strip, copied from today's file.

  The output for strip 1 should match today's blockoverrides line for line.
- [ ] **Step 4: The mounts.** Per tab, in registry order:

```
		flowcontainer = {
			name = "te_systems_window_<key>_tab"
			using = te_systems_window_<key>_selected
			using = default_fade_in_out
			parentanchor = hcenter
			direction = vertical
			ignoreinvisible = yes
			margin_top = 10
			margin_bottom = 15

			<body> = {}
		}
```

  `te_tp_panel = { using = te_systems_window_tax_probes_selected }` comes first, as today. `te_sr_window_milestones` renders each `SR_MILESTONES` entry as a `te_system_tab_frame`:
  - the milestone's gate, `te_window_space_race_<m>_sgui`, on the frame instance's own `visible`, so its header shows only with it, as today. `tab_gate` stays empty; the frame's root has no `visible` of its own;
  - `tab_header`: `je_space_race_<m>`;
  - `tab_entry`: `je_space_race_<m>`;
  - `tab_content`: `te_sr_<m>_overview = {}` then `te_sr_<m>_status = { blockoverride "sr_debris" {} }`, or `te_sr_overview_transit = {}` for `interstellar_results`;
  - the link tooltip `te_window_space_race_open_journal_tt`.

  Before them comes today's idle block (`te_systems_window_space_race_idle`).
- [ ] **Step 5: Write the file** with a BOM and a header (`### AUTO-GENERATED by scripts/generators/gen_te_systems_window.py from its TABS registry. Do not edit.`). Run the generator.
- [ ] **Step 6: Test the generator** in `test_te_systems_window.py`, importing it as `test_nation_tab.py` does (`from scripts.generators import gen_te_systems_window as gen`):
  - `test_generated_file_is_current`;
  - `test_nation_is_first_and_the_fallback`;
  - `test_templates_are_binary` (no `And(`/`Or(` with three arguments).
- [ ] **Step 7: Register the file** in `docs/auto_generated_files.md`, `scripts/nightly_audit_select.py` and `gui_modding_guide.md`. Run `test_nightly_audit_select.py` and `test_tax_code_bypass.py`. Expected: PASS.
- [ ] **Step 8: Commit.**

### Task A4: the window instances the generated pieces

**Files:**
- Modify: `gui/te_systems_window.gui`

- [ ] **Step 1: Delete the hand-written templates** (today's lines 50–105).
- [ ] **Step 2: In `te_systems_window_panel`:**
  - `fixed_top` keeps its vbox and now holds `te_systems_window_strips_narrow = {}`.
  - `scrollarea_content`'s `te_systems_window_content` flowcontainer keeps its name, `using = default_list_position` and `minimumsize = { 540 -1 }`, and holds `te_systems_window_tabs_narrow = {}`.
- [ ] **Step 3: Rewrite the header comment** for the new split: the registry is in the generator, and the frames, the launcher and the root stay here.
- [ ] **Step 4: Run** `test_te_systems_window.py`, `test_grand_monuments_layout.py` (`StateCardTest` reads the tab key) and `check_gui_lint.py`. Expected: what A5 hasn't yet rewritten fails; nothing else does.
- [ ] **Step 5: Commit.**

### Task A5: the window's tests read the registry

**Files:**
- Modify: `test_te_systems_window.py`

- [ ] **Step 1:**
  - `ALL_TABS`, `FULL_NAMES` and `NAME_WIDTH` come from `gen.TABS`.
  - `_template` reads `gui/te_systems_window_generated.gui`.
  - `_evaluate`'s atom regex also accepts `.IsValid(` (PR C's Demographics needs it): model each gate as two atoms, `<sgui>:shown` and `<sgui>:valid`.
- [ ] **Step 2: `SelectionTest._cases`, per stored value.** For each stored value (`None`, `"nation"`, `"tax_probes"`, every key):
  - the stored tab's open and on-strip states, in its three combinations;
  - every other tab in one shared state, also three combinations;
  - for `tax_probes`, the probe gate on and off.

  That makes nine cases per stored value (eighteen for `tax_probes`), about 150 at fifteen tabs, against 486 for today's four by full enumeration and about 77 million at fifteen. It is enough because each template reads only its own tab's gates and the stored tab's, which `test_templates_read_only_their_gates` asserts from the rendered text.
- [ ] **Step 3:**
  - `StripTest`: strip 1 holds today's five, in registry order.
  - `TabContentTest`: read each body type (A2) and the mount that instances it, not the old inline blocks.
- [ ] **Step 4: Run** `test_te_systems_window.py test_te_system_tab_bodies.py test_grand_monuments_layout.py test_space_race_layout.py test_colonial_empire_layout.py test_seabed_layout.py test_nation_tab.py`. Expected: PASS.
- [ ] **Step 5:** `BodyTest.test_no_body_reads_a_host_panel` (Review Focus 2) over every `te_*_tab_body` type. Commit.

### Task A6: docs and PR

- [ ] `docs/systems/mod_systems/state_and_nation_panels.md` and `gui_modding_guide.md`'s window section: the registry, the generator, the frame type, how to add a tab (one `Tab` line, a body type, then run the generator).
- [ ] The gate list in Global Constraints. Open the PR with "Player guide: no player-facing change (a refactor)".

---

## PR B: the full-screen frame and the toggle

Branch `feat/te-window-wide-frame`. Spec §§ 4, 10. **Needs vanilla's `gui/block_windows.gui` (1.14.x) from the owner's install.**

### Task B1: the frame

**Files:**
- Create: `test_fixtures/vanilla_gui/block_windows.gui` (vanilla, byte for byte, its BOM kept)
- Modify: `gui/te_system_tab_widgets.gui` or a new `gui/te_window_frames.gui` (`te_fullscreen_block_window`); a new file needs its row and the count in `gui_modding_guide.md`
- Create: `test_te_fullscreen_frame.py`

- [ ] **Step 1: Read vanilla's `fullscreen_block_window`** and list its blocks, its close and back buttons' `onclick`, its size and margins, and whether it has `fixed_top` and `fixed_bottom`. Record them in the test's docstring.
- [ ] **Step 2: Write the test.** The mod's type equals vanilla's, after removing these allowed differences:
  - the type's name;
  - the close button's and the back button's `onclick` (vanilla's `InformationPanelBar.ClosePanel` and its back call), which become `GetVariableSystem.Clear('com_open_window')`;
  - only if vanilla has no `fixed_top`, one added `block "fixed_top" {}` above the scroll area.

  `shortcut = "close_window"` stays on the close button.
- [ ] **Step 3: Copy the type** under the new name with those changes and run the test. Expected: PASS.
- [ ] **Step 4: Commit.**

### Task B2: the wide panel, the root and the toggle

**Files:**
- Modify: `gui/te_systems_window.gui`; `scripts/generators/gen_te_systems_window.py` (`te_systems_window_strips_wide`, `te_systems_window_tabs_wide`); `localization/english/te_miscellaneous_l_english.yml`; `test_te_systems_window.py`

**Interfaces:**
- Produces: the client-side key `te_systems_window_wide`; `type te_systems_window_panel_wide = te_fullscreen_block_window`.
- Produces in the generated file:
  - `te_systems_window_strips_wide`: an hbox of `expand`, then each strip's `tab_buttons` at `minimumsize = { 540 -1 } maximumsize = { 540 -1 }` side by side (the Census window's strip precedent, `pop_browser_panel.gui`), then `expand`, and the tax-probes strip below.
  - `te_systems_window_tabs_wide`: per tab, the same mount as narrow, holding `<body> = {}`. Once a tab has `wide`, it holds `<body> = { blockoverride "<layout>" { <wide> = {} } }`, or `<wide> = {}` in place of the body for a tab with no layout block (Nation, Budget Breakdown).

- [ ] **Step 1: Tests first.**
  - `WideTest.test_the_root_switches`: the root holds two full-size children, `visible = "[Not( GetVariableSystem.Exists('te_systems_window_wide') )]"` (the narrow panel in today's vbox and hbox, `margin_top = 85`) and `visible = "[GetVariableSystem.Exists('te_systems_window_wide')]"` (the wide panel in a `margin_widget`, `margin_top = 85`).
  - `test_the_toggle_keeps_the_tab`: neither toggle button writes `te_systems_window_tab`.
  - `test_both_frames_close_alike`.
  - `test_the_wide_strip_is_the_narrow_strips_side_by_side`.
- [ ] **Step 2: The root.** Replace the window root's single vbox:

```
	widget = {
		size = { 100% 100% }
		visible = "[Not( GetVariableSystem.Exists('te_systems_window_wide') )]"

		vbox = {
			parentanchor = top|left
			layoutpolicy_horizontal = expanding
			layoutpolicy_vertical = expanding
			margin_top = 85

			widget = {
				layoutpolicy_horizontal = expanding
				layoutpolicy_vertical = expanding

				hbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = expanding

					te_systems_window_panel = {}
					expand = {}
				}
			}
		}
	}

	margin_widget = {
		size = { 100% 100% }
		margin_top = 85
		visible = "[GetVariableSystem.Exists('te_systems_window_wide')]"

		te_systems_window_panel_wide = {}
	}
```

  The `margin_widget` (vanilla's, as `construction_panel.gui` uses it) insets a child sized `100%`, which a full-screen type usually is, so the frame starts under the top bar without running 85 px off the bottom. If B1 Step 1 finds vanilla's type laid out by its parent instead, use the narrow branch's vbox shape. The root's `_show` state stays on the root, so switching width doesn't rerun it.
- [ ] **Step 3: The toggle** is a slim row first in each frame's `fixed_top`, a text button right-aligned (spec § 4.2; an icon can replace it later):

```
				hbox = {
					layoutpolicy_horizontal = expanding
					layoutpolicy_vertical = fixed
					margin_right = 10

					expand = {}

					button = {
						using = default_button
						size = { 140 26 }
						text = "te_systems_window_wide_on"
						tooltip = "te_systems_window_wide_on_tt"
						onclick = "[GetVariableSystem.Set('te_systems_window_wide', 'yes')]"
					}
				}
```

  The wide frame's row has `te_systems_window_wide_off` / `_off_tt` and `GetVariableSystem.Clear('te_systems_window_wide')`. Loc:
  - `te_systems_window_wide_on`: "Full Screen"
  - `te_systems_window_wide_on_tt`: "Show this window across the screen, with each tab in columns."
  - `te_systems_window_wide_off`: "Side Panel"
  - `te_systems_window_wide_off_tt`: "Show this window at the width of the other side panels."
- [ ] **Step 4: The wide panel.** `te_systems_window_panel_wide` repeats the narrow panel's header name and close blocks. Its `fixed_top` holds the toggle row and `te_systems_window_strips_wide = {}`. Its scroll area holds the column flowcontainer at `minimumsize = { 1620 -1 }`, `parentanchor = hcenter`, holding `te_systems_window_tabs_wide = {}`. The scroll area also needs a horizontal scroll bar (`scrollbar_horizontal = { using = horizontal_scrollbar }`, the Census window's), if vanilla's type doesn't give one.
- [ ] **Step 5: Run** `test_te_systems_window.py`, `test_te_fullscreen_frame.py`, `check_gui_lint.py` and `loc_coverage_audit.py --strict`. Expected: PASS. Then commit.

### Task B3: play-test list, docs, player guide

- [ ] **Create `docs/testing/te-window-wide-playtest.md`** with spec § 10's items 1–4, each a checkbox: what to do, what to see, the fallback named.
- [ ] **Docs:**
  - `gui_modding_guide.md`'s window section: the two frames, the key, the toggle.
  - `system_panels_feasibility.md`'s status: one line.
- [ ] **Player guide:** a paragraph in `01-introduction.md`'s window section on the Full Screen / Side Panel button. Rebuild the PDF. Commit. Open the PR with "Player guide: 01-introduction (the window's Full Screen button)".

---

## PR C: the ten mirrored tabs

Branch `feat/te-window-mirrored-tabs`. Spec §§ 5.1, 6, 9.1, 9.6.

### Task C1–C6: one body per system, its host moved onto it

One task per host file, each the same five steps:
- [ ] **Step 1: Point the layout test at the body.** Its "tab region" helper (`_tab_block` in `test_banking_layout.py`, `self.region` in `test_tax_code_layout.py` and so on) reads the new body type. Add a check that the host's tab instances it, inside the host's outer flowcontainer (which keeps its `name`, its `visible = "[InformationPanel.IsTabSelected('…')]"`, its fade and position templates and its margins).
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Write the body** in the system's layout file and **move the host's content** into it, as in the table below.
- [ ] **Step 4: Run** that system's layout tests, `test_te_system_tab_bodies.py` and `check_gui_lint.py`. Expected: PASS.
- [ ] **Step 5: Commit.**

| Task | Host file | Body (file) | What the host keeps; what the body's blocks hold |
|---|---|---|---|
| C1 | `budget_panel.gui` | `te_banking_tab_body` (`banking_layout_widget.gui`) | `tab_header`: both headers, each with its readout gate. `tab_before_gate`: the readout flowcontainer, moved verbatim. `tab_open_journal_font`: `using = fontsize_large`. Layout block `te_banking_tab_layout` |
| C1 | `budget_panel.gui` | `te_tax_tab_body` (`te_tax_layout_widget.gui`) | `tab_content`: `te_tax_status_sections = { blockoverride "draft_summary" {} }` as today. `tab_open_journal_font`: `using = te_tax_fontsize_row`. Budget keeps its `fixed_bottom`. Layout block `te_tax_tab_layout` |
| C1 | `budget_panel.gui` | none: Budget Breakdown's body is `te_budget_breakdown_panel` | unchanged |
| C2 | `market_panel.gui` | `te_gw_tab_body` (`global_warming_widget.gui`) | Host keeps its `_show` map-mode reset. `tab_content` declares `block "te_gw_tab_layout" { block "te_gw_tab_market_view" { te_gw_overview_panel = {} te_gw_status_sections = {} } te_gw_reference_sections = {} }`. A block nested in another's default is vanilla's shape: `default_block_window`'s `header_back_button` sits inside `entire_back_button`. The host overrides `te_gw_tab_market_view` with its two branches (own market, another market) moved verbatim. The window uses the default, and its wide mount overrides the whole `te_gw_tab_layout` |
| C2 | `market_panel.gui` | `te_st_res_tab_body` (`strategic_reserve_widget.gui`) | `tab_before_gate` declares `block "te_st_res_tab_elsewhere" {}`, which the host fills with its other-market note. `tab_gate` declares `block "te_st_res_tab_gate" { visible = "[<tab sgui shown>]" }`, which the host overrides with `And( <tab sgui shown>, MarketPanel.GetMarket.IsSame( GetPlayer.GetCapital.GetMarket ) )` |
| C3 | `pops_overview.gui` | none in the host; see C7 | unchanged |
| C4 | `culture_panel.gui` | `te_ch_tab_body` (`cultural_hegemony_widget.gui`) | Host keeps `using = society_panel_tab_contents_properties` |
| C5 | `diplomatic_overview.gui` | `te_un_tab_body` (`un_layout_widget.gui`) | `tab_content`: the overview, the Status section with `te_un_tab_status_closed` (verbatim), then status and reference |
| C6 | `panel_military.gui` | `te_nuclear_tab_body` (`nuclear_layout_widget.gui`), `te_covert_tab_body` (`covert_operations_widget.gui`) | Nuclear's `tab_content` keeps the goal bar under The Program, under `nuclear_program_has_programme_sgui` |

Every frame-based body fills `tab_header` (its `default_header`), `tab_gate` (the host's gate), `tab_entry` (`GetPlayerJournalEntry('<je>')`), `tab_content` (its composers, inside `block "te_<system>_tab_layout" { … }`) and `tab_open_journal_tooltip` (the host's key today).

Banking, Cultural Hegemony and the UN gain the frame's fixed 520 column, which they lack today (spec § 9.1). Add each to the play-test list's columns item.

### Task C7: Demographics for the window

**Files:**
- Modify: `gui/te_demographics_layout.gui` (`te_demog_window_sections`, `te_demog_window_body`)
- Modify: `test_demographics_layout.py` (its `hosts` dict), `test_demographics_census_window.py` or a new `DemogWindowTest` in `test_te_system_tab_bodies.py`

- [ ] **Step 1: Tests:**
  - `te_demog_window_sections` holds `te_demog_tab_sections`' sections in the same order, with `te_demog_sec_wealth = { blockoverride "te_demog_wealth_strata_incomes" {} }`, as `te_demog_browser_sections` does.
  - Nothing the window draws for Demographics reads `PopsOverviewPanel`: the census window test's check, run over the window's types.
- [ ] **Step 2: Write the two types.**
  - `te_demog_window_sections` copies `te_demog_tab_sections`, pending line and fixed 520 included, with the wealth override.
  - `te_demog_window_body` is a `te_system_tab_frame`:
    - `tab_gate`: `te_pops_demog_tab_sgui` shown;
    - `tab_entry`: `datacontext = "[GetPlayer]"`;
    - `tab_open_journal`: emptied;
    - `tab_content`: `block "te_demog_tab_layout" { te_demog_window_sections = {} }`.
- [ ] **Step 3: Run** `test_demographics_layout.py` and `test_demographics_census_window.py`. Expected: PASS. Then commit.

### Task C8: the registry's strips 2 and 3, and loc

**Files:**
- Modify: `scripts/generators/gen_te_systems_window.py`, `gui/te_systems_window_generated.gui` (regenerated), `localization/english/te_miscellaneous_l_english.yml`, `test_te_systems_window.py`

- [ ] **Step 1: Add ten `Tab` entries** (spec § 5.1's rows), keys and names per spec open question 2 (defaults below):

  | Key | Strip | Label (new) | Tooltip | Locked | Open | On the strip | Body |
  |---|---|---|---|---|---|---|---|
  | `banking` | 2 | "Banking" | `te_budget_tab_banking_tt` | `te_budget_tab_banking_locked_tt` | `or_(shown("te_budget_banking_tab_sgui"), shown("te_budget_banking_readout_sgui"))` | `shown("te_budget_banking_tab_unlock_sgui")` | `te_banking_tab_body` |
  | `tax_code` | 2 | "Tax Code" | `te_tax_tab_tt` | `te_tax_tab_locked_tt` | `te_budget_tax_tab_sgui` | `te_budget_tax_tab_unlock_sgui` | `te_tax_tab_body` |
  | `budget_breakdown` | 2 | "Budget Breakdown" | `te_budget_chart_tab_tt` | none | always | always | `te_budget_breakdown_panel` |
  | `strategic_reserve` | 2 | "Strategic Reserve" | new `te_window_tab_strategic_reserve_tt` | new | `te_market_strategic_reserve_tab_sgui` | `…_unlock_sgui` | `te_st_res_tab_body` |
  | `global_warming` | 2 | "Global Warming" | new `te_window_tab_global_warming_tt` | new | `te_market_global_warming_tab_sgui` | `…_unlock_sgui` | `te_gw_tab_body` |
  | `demographics` | 3 | "Demographics" | `te_pops_tab_demog_tt` | `te_pops_tab_demog_locked_tt` | `and_(shown("te_pops_demog_tab_sgui"), valid("te_pops_demog_tab_unlock_sgui"))` | `shown("te_pops_demog_tab_unlock_sgui")` | `te_demog_window_body` |
  | `cultural_hegemony` | 3 | "Cultural Hegemony" | `te_society_tab_ch_tt` | new | `te_society_ch_tab_sgui` | `…_unlock_sgui` | `te_ch_tab_body` |
  | `united_nations` | 3 | "United Nations" | `te_diplomacy_tab_un_tt` | new | `te_diplomacy_un_tab_sgui` | `…_unlock_sgui` | `te_un_tab_body` |
  | `nuclear_weapons` | 3 | "Nuclear Weapons" | `te_military_tab_nuclear_tt` | new | `te_military_nuclear_tab_sgui` | `…_unlock_sgui` | `te_nuclear_tab_body` |
  | `covert_warfare` | 3 | "Covert Warfare" | `te_military_tab_covert_tt` | new | `te_military_covert_tab_sgui` | `…_unlock_sgui` | `te_covert_tab_body` |

  - **Gates:** a bare scripted GUI name in the Open and On the strip columns means `shown(<name>)`, and `unlock` is the `_unlock_sgui`.
  - **Tooltips:** a host's key is reused as written, so the two hosts can't drift (spec § 9.6). Global Warming's and the Reserve's own talk of "another market" and "this tab". Their window tooltips: "The world's temperature, the countries emitting most and the history, your climate policies and your Fossil Transition." and "Your hub, each good's stock, status and policy, and its fill history."
  - **New locked keys** take the window's shape: `#b $te_window_tab_<key>$#!\nNot open yet. It opens once:\n`.
  - **Banking** sets `tooltip_expr` to its host's two-branch form: tab, readout `te_budget_tab_banking_readout_tt`, else locked. That form has no checklist.
  - **Labels:** new `te_window_tab_<key>` keys.
- [ ] **Step 2: Extend the tests.**
  - `SelectionTest` gains the `valid` atoms.
  - `StripTest`: three strips of five, in spec § 5.1's order.
  - `LocTest`: every key the generated file names exists.
  - `test_each_tab_shows_its_full_name` takes the new names.
- [ ] **Step 3: Regenerate**, then run `test_te_systems_window.py`, `loc_coverage_audit.py --strict` and `organize_loc.py` (commit what it moves). Expected: PASS.
- [ ] **Step 4: The launcher tooltip** (`te_systems_window_launcher_tt`) no longer lists the tabs: "Your nation's lasting scores and modifiers, and a tab for each of the mod's systems." Commit.

### Task C9: Tax Code's footer in both frames

**Files:**
- Modify: `gui/te_systems_window.gui`, `test_te_systems_window.py`

- [ ] **Step 1: Test** that each frame's `fixed_bottom` shows `te_tax_draft_summary` and `te_tax_bill_summary` only on the Tax Code tab: the outer widget `using = te_systems_window_tax_code_selected`, its child `visible = "[Or( <te_tax_show_draft_sgui shown>, <te_tax_show_bill_sgui shown> )]"`.
- [ ] **Step 2: Copy Budget's footer** (its `fixed_bottom`): a `divider_clean` sized `{ 554 4 }` in the narrow frame (Budget's `@panel_width_plus_14`), a `dark_area` background, and the two summaries. The wide frame gets the same, with the divider at the frame's width. If vanilla's full-screen type has no `fixed_bottom` (B1 Step 1), add it there as the one more allowed difference in `test_te_fullscreen_frame.py`.
- [ ] **Step 3: Run the tests.** Expected: PASS. Then commit.

### Task C10: docs and player guide

- [ ] **Style guide rule 9:**
  - The window also shows every tab that lives in a vanilla panel.
  - The window's strips are up to three of five each, side by side when wide (the owner's 2026-11-02 call). Other windows keep one strip of up to six.
- [ ] **`system_panels_feasibility.md`'s status** and **`gui_modding_guide.md`'s window section** (CRLF).
- [ ] **The play-test list:**
  - each mirrored tab matches its host;
  - Banking's readout case;
  - Global Warming in the window shows the player's own market;
  - Tax Code's footer;
  - the three newly fixed columns.
- [ ] **Player guide:** `01-introduction.md`'s window section says the window also carries the tabs of Budget, Market, Population, Society, Diplomacy and Military. `17-reference.md`'s rows that name a vanilla tab gain "and the Timeline Extended window". Rebuild the PDF. Commit and open the PR.

---

## PR D0: the column types and the shared check

Branch `feat/te-window-wide-columns`. Spec §§ 7, 9.4, 9.5.

### Task D0.1: the column types

**Files:** Modify `gui/te_widget_library.gui`; create `test_te_widget_library.py` or extend `test_te_popups.py`.

- [ ] **Step 1: Test** that `te_ui_columns_three` is a horizontal flowcontainer, `spacing = 30`, `parentanchor = hcenter`, `ignoreinvisible = yes`. It holds three vertical flowcontainers (`ignoreinvisible = yes`, `spacing = 10`, `minimumsize = { 520 -1 }`, `maximumsize = { 520 -1 }`) holding `block "column_1"`, `"column_2"`, `"column_3"`. `te_ui_columns_two` is the same with two.
- [ ] **Step 2: Write the two types** in `types te_widget_library_types`, with a header comment entry. Run the test. Expected: PASS. Then commit.

### Task D0.2: the shared check

**Files:** Create `gui_test_helpers.py` (not a test file: no `test_` prefix, so neither pytest nor unittest collects it).

- [ ] **Step 1: Write the helpers**, moving the shared ones out of `test_te_systems_window.py` (`_read`, `_close`, `_block_at`, `_type_body`, `_strip_comments`). Then `assert_wide_matches_narrow(test, wide_type, narrow_types, *, extra=())`:
  - expands each narrow composer into its section types in order (one level: the composer's direct `te_*` children);
  - reads the wide composer's `column_1`, `column_2` and `column_3` in order;
  - asserts the two lists are equal (`extra` lists wide-only wrappers it may skip);
  - asserts every section a narrow composer gates (its own `visible`, `JournalEntry.IsActive` or Global Warming's `And`) sits in the wide composer under a wrapper with that same `visible`, or the wide composer's root carries it.
- [ ] **Step 2: Rebase `te_demog_browser_sections` on `te_ui_columns_three`** (its pending line stays outside) and call the helper from `test_demographics_layout.py`. Run it. Expected: PASS. Commit and open the PR ("Player guide: no player-facing change").

## PR D1–D3: the wide composers (in parallel once D0 has merged)

Each system, in its layout file:
- the wide composer `te_<system>_wide_sections`, on `te_ui_columns_three` or `te_ui_columns_two`, with the spec § 7 columns;
- the registry's `wide` field set;
- the generator rerun;
- `assert_wide_matches_narrow` called from its layout test;
- its row on the play-test list's columns item.

Wrap each column's run of status or reference sections in a vertical flowcontainer with its narrow composer's `visible` and spacing (`spacing = 4`, Banking's `2`).

| PR | Systems | Notes |
|---|---|---|
| D1 | Nation, Space Race, Grand Monuments, Colonial Empire, Seabed, Budget Breakdown | Space Race: column 1 is `te_sr_window_milestones`, 2 the summary, 3 the reference. Breakdown: split its "How" block out of `te_budget_breakdown_panel` into `te_budget_sec_how` first, keeping the panel's order. Nation and Breakdown have no layout block; their wide mount names the wide composer in place of the body, with the registry saying so |
| D2 | Banking, Tax Code, Strategic Reserve, Global Warming | Tax Code switches between the full code's and the Light code's columns, as `te_tax_status_sections` does, under the same gates. Reserve: two columns. Global Warming: the window's view only (own market) |
| D3 | Cultural Hegemony, United Nations, Nuclear Weapons, Covert Warfare | UN: if the Assembly makes column 1 far taller, the Assembly gets column 1 alone and the rest move right; the check only fixes the order. Nuclear: the goal bar goes with The Program |

Each PR's body: "Player guide: below the guide's level of detail" (the guide describes the toggle, not each layout).

## Later: vanilla bases for the hosts (spec § 9.7)

On the owner's machine, after C: for each host whose diff from vanilla is only its tab blocks, commit vanilla's file under `test_fixtures/vanilla_gui/` and a test that the override changes it only inside `### MOD:` blocks. Retag `market_panel.gui`'s `### TE:` markers as `### MOD:` in the same PR.

## Self-review against the spec

- § 4 → B1, B2; § 5.1 → A3, C8; § 6 → C1–C7; § 7 → D1–D3; § 8 → each task's tests and C10; § 9.1 → A1, A2, C1–C6; § 9.3 → A3–A5; § 9.4 → D0.1; § 9.5 → D0.2; § 9.6 → C8; § 9.7 → Later; § 10 → B3, C10.
- **Not covered here:**
  - § 9.8 (the shared section widgets): a separate project.
  - § 9.9 (the observer guard on the hosts): a separate fix.
- **Owner calls still open** (spec § 12), with this plan's defaults, each a one-line change if decided otherwise:
  - three columns (D0.1);
  - the entries' names (C8);
  - § 5.1's strips (C8).
