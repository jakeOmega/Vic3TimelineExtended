# Moving System UI Out of the Journal — Feasibility

> **Status: feasibility study, 2026-09-28.** Checked against the vanilla 1.14.4 GUI files, the mod at `6a0a3c06`, and two Workshop mods installed locally: Community Mod Framework (CMF) 1.65.0 and Demography v14.
>
> **Prototypes (PR #567), 2026-09-28.** Each tab is on its panel's strip while its game rule is on, greyed until its journal entry is active, with the unlock conditions in the tooltip. Shared pieces: `gui/te_system_tab_widgets.gui` (a journal entry's bars, status description and button grid; `te_tab_buttons_six`) and the gates in `common/scripted_guis/te_system_tab_sguis.txt`.
> - **Banking as a Budget tab** (`gui/budget_panel.gui`; `mod_systems.md` § Policy Dashboard). **Seen in game the same day:** the tab selects and all three panels render. So custom tab names work (§3.4, §8 test 1), and `GetPlayerJournalEntry` works for an active entry (§3.2). What it returns for an entry the player lacks or holds inactive is still untested (§8 test 2); the tabs never build the datacontext then.
> - **Cultural Hegemony as a Society tab** (`gui/culture_panel.gui`, the fifth slot). Not yet seen in game. CMF redefines `society_panel` (§7.4), so with CMF enabled one side's version is dropped.
> - **Nuclear Weapons as a Military tab** (`gui/panel_military.gui`, the fourth slot; 2026-09-30, the first of phase 2). Not yet seen in game. The Military panel was already a full-file override, so no new vanilla file is replaced. The first tab to draw an entry's goal bar (`te_je_goal_bar`). What the next tabs need: §5.1.
> - **The UN as a Diplomacy tab** (`gui/diplomatic_overview.gui`; `journal_entry_systems.md` § Chamber Widget). Vanilla's five tabs fill `tab_buttons`, so the strip is `te_tab_buttons_six`, a copy with a sixth slot; the only vanilla line changed is that type name. Unlike the other two, the tab draws the entry's scripted buttons (founding, joining and leaving exist only there) and its status description. Seen in game 2026-09-28: six tabs fit. Then round 1 of a visual pass of the UN's panels, in both hosts (`docs/superpowers/specs/2026-09-28-un-gui-pass-design.md`).
>
> Each claim carries a marker. **[verified]**: read in shipping vanilla or mod code. **[precedent]**: a shipping mod or vanilla does it. **[untested]**: plausible, needs an in-game check (§8).

## 1. The question

Most systems are played through their journal entry: widgets under `gui/journal_entry_widgets/` plus scripted buttons. The idea is to give each one a full GUI instead:
- a tab in a vanilla window (Banking in Budget, the UN in Diplomacy, Cultural Hegemony in Society);
- or a new window opened from a new sidebar button.

How possible is that, how hard, and what would it take?

## 2. Short answer

It is possible. It costs much less than a rewrite, because the existing widgets can be shown outside the journal unchanged (§3.2–3.3).
- **The mod's own windows are on solid ground.** They need no vanilla file replaced.
- **Tabs inside vanilla windows work.** Custom tab names are confirmed in game (§3.4). Each host window is another full-file replacement to merge every patch.
- **The journal entry stays** as the state carrier: completion, outliner pin, notifications, and the scripted buttons the AI presses. The window is a second view of the same entry, and no script moves.

## 3. Building blocks

### 3.1 New windows: scripted widgets [precedent]

Vanilla ships `game/gui/scripted_widgets/scripted_widgets.md`. Each line of a `.txt` in `gui/scripted_widgets/` has the form `gui/file.gui = widget_name` and creates that widget at startup. All such files load, so each mod ships its own. Three installed Workshop mods use it. The first two replace no vanilla `.gui` at all:
- **Historical Record** (`3772525185`): a small `sidepanel_button_small` pinned at `parentanchor = top|left position = { 74 93 }` beside the sidebar, and a 980×830 window.
- **Statistics** (`3429587193`): a movable launcher button and a window whose metric selector is a `GetVariableSystem` value (`statistics_selected_metric`).
- **Demography** (`3759720467`): two windows, opened from CMF's sidebar (§7). It also replaces two vanilla panels (§7.1).

Scripted widgets exist from the main menu on, so a window's root must be gated. Historical Record and Demography both use `visible = "[GetMetaPlayer.GetPlayedOrObservedCountry.IsValid]"`, which also hides them in observer mode.

### 3.2 A journal entry as the data source, outside the journal [verified]

`GetPlayerJournalEntry( Arg0 )` is a global promote returning `JournalEntry` (`data_types_uncategorized.txt`, 1.14 digest); `Country.GetJournalEntry( Arg0 )` is the country form. Vanilla uses the global with a literal key at `game/gui/states_panel.gui:1059`:

```
datacontext = "[GetPlayerJournalEntry('je_meiji_restoration')]"
```

Under that datacontext every `JournalEntry.*` expression works, so the widgets need no rewrite:
- they read nothing but `JournalEntry` and objects reached from it: 1,711 `JournalEntry.GetCountry`, 38 `JournalEntry.IsActive`, and the bar calls;
- their loc adds 885 more `JournalEntry.GetCountry`.

The one exception is already handled. A loc string shown as the `tooltip` of a `datamodel` item gets a fresh context holding only the item, with no `JournalEntry`, in the journal just as in a window (gotcha #24 in the GUI guide). The history-chart tooltips were moved off `JournalEntry` for that reason, and `test_history_chart_tooltip_context.py` guards them.

The `JournalEntry` object also exposes `GetScriptedButtons`, `GetScriptedProgressBars`, `GetStatusDesc`, `GetCurrentBarProgress` and `IsActive`. Vanilla's `scripted_journal_entry_button` type (`game/gui/journal_entry.gui:988`) is global. So a window can draw the entry's own scripted buttons (78 in banking) and bars **without converting them to scripted GUIs**.

**Guard it.** Vanilla shows the Meiji block only after a scripted GUI's `is_shown` passes `owner ?= { has_journal_entry = je_meiji_restoration }` (`journal_entry_sguis.txt:110`). Do the same, with the game rule in the same test, and put the datacontext on a *child* of the gated widget, never on the window root. What `GetPlayerJournalEntry` returns for an entry the player lacks, or holds inactive, is **[untested]**.

### 3.3 One layout, two hosts [precedent, in-repo]

A JE widget file is a `types` block plus top-level named widgets, which the entry attaches with `widget = { gui = … name = … container = … }`. `space_race_widget.gui` already splits them.
- *The wrappers.* Its top-level `flowcontainer`s are named wrappers (after the style guide pass: an overview and a live-sections root per milestone and one shared reference root, nearly all `blockoverride`s) around the shared composer types `te_sr_overview_milestone` and `te_sr_status_sections`.
- *Why the shared types still work.* They read `JournalEntry` themselves (18 references), because a type takes the datacontext of the place it is instanced. Under a `GetPlayerJournalEntry` datacontext in a window, the same types would work unchanged. Doing that to every widget lets the journal entry and a window instance the same body. Types are global across `.gui` files; `te_history_chart.gui` and `te_state_panel_widgets.gui` are already used from other files.

Width: every vanilla side panel is `@panel_width = 540`. The widgets are built at 520 (`@panel_width_minus_20`), so they fit any host without relayout.

### 3.4 Tabs inside vanilla windows [verified in game]

**Confirmed 2026-09-28** by the Banking prototype (`gui/budget_panel.gui`): `SelectTab('te_banking')` selects and holds a tab name vanilla does not define. The sidebar button's cycle (below) does not list it, so pressing Budget never lands on it. Adding it to the cycle means replacing `information_panel_bar.gui` (§3.5). The paragraph below is the reasoning from before the test.


Tabs are plain strings. The tab buttons call `InformationPanel.SelectTab('states')` and gate content on `InformationPanel.IsTabSelected('states')`. The sidebar opens panels with a tab cycle, `InformationPanelBar.OpenPanelCycleTabs('budget', 'default|states|assets')`, and `OpenPanelTab( panel, tab )` opens one tab directly. That points to `SelectTab('te_banking')` just working. There is one data point, but it doesn't settle this: an earlier Demography version shipped a fifth Society tab (§7.1), but its file is gone, so whether it used a new tab name is unknown. No mod installed today uses a tab name vanilla does not define: not this mod, not CMF, not Demography v14. **Fallback that certainly works:** the new tab button sets a `GetVariableSystem` flag, vanilla's tab contents are gated on its absence, and vanilla's tab buttons clear it.

| Host | File (vanilla lines) | Tabs today | Room |
|---|---|---|---|
| Budget | `budget_panel.gui` (2,112) | 3 | yes |
| Society | `culture_panel.gui` (1,875), type `society_panel` | 4 | yes; a fifth has shipped before (§7.1) |
| Diplomacy | `diplomatic_overview.gui` (1,827) | 5 | none in `tab_buttons`, which has five slots; the UN prototype uses a six-slot copy |
| Military | `panel_military.gui` | 3 | yes; the Nuclear tab takes the fourth slot |

Before the prototypes (header), this mod replaced none of the three; it now replaces all three. It already replaced the Military panel before its Nuclear tab. Each one added is another file to merge every patch (the 3-way merge in `docs/guides/gui_modding_guide.md`). It also collides with any other mod that replaces it (§7.4): Demography replaces `budget_panel.gui`, and CMF redefines `society_panel`.

### 3.5 A sidebar button

The sidebar (`information_panel_bar.gui`, 790 lines, instanced at `ingame_hud.gui:272`) sits at `position = { 0 200 }` and places each button at a hard-coded offset: politics 0, …, companies 520, map list 580. Three ways to add one:

| Way | Vanilla files replaced | Notes |
|---|---|---|
| Replace `information_panel_bar.gui` and add `@te_position = 620` | 1 (790 lines) | Native look, hover label, hides with the sidebar. Collides with CMF, which redefines the `information_panel_bar` type |
| A scripted-widget button pinned below Map List | 0 | Historical Record's shape. It does not get the sidebar's `_hide` animation or hover label. `using = hud_visibility` (a `topbar.gui` template) hides it on the pause and game-over screens |
| Register with CMF's sidebar registry | 0, but needs CMF | §7.2 |

### 3.6 Behaving like a vanilla panel [precedent]

A scripted-widget window is not in the engine's panel stack, so by default Budget opening does not close it, and it does not close Budget. Demography and CMF show the fix:
- Build the window from vanilla's `default_block_window` type (`game/gui/block_windows.gui:317`): native header, back and close buttons, a scroll area.
- Wrap it in a full-size widget whose `vbox` has `margin_top = 85`, so it sits where vanilla panels do (`demography_cmf_panel.gui`).
- In the window's `blockoverride "animation_state_block"`, the `_show` state runs `on_start = "[InformationPanelBar.ClosePanel]"` and `on_start = "[MapListPanelManager.CloseCurrentPanel]"`.
- A zero-size widget clears the window's flag when a vanilla panel or the ledger opens (CMF `com_gui_sidebar.gui:778-792`):

```
widget = { state = { trigger_when = "[InformationPanelBar.IsAnyPanelOpen]" on_finish = "[GetVariableSystem.Clear('com_open_window')]" } }
widget = { state = { trigger_when = "[MapListPanelManager.IsVisible]"      on_finish = "[GetVariableSystem.Clear('com_open_window')]" } }
```

`shortcut = "close_window"` on the close button gives Escape (68 vanilla uses). The journal entry can link to its window with `GetVariableSystem.Set(…)` or `InformationPanelBar.OpenPanelTab(…)`, and the window back to its entry with `InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)` (vanilla `journal.gui:348`).

## 4. Options, cheapest first

| | What | Vanilla files replaced | Confidence |
|---|---|---|---|
| 0 | A button that opens the journal entry itself (`OpenJournalEntryPanel`) | none or 1 (sidebar) | verified |
| 1 | The mod's own window, one per system or one "Timeline Extended" window with its own tabs, showing the existing widgets under a JE datacontext | none, or 1 (sidebar) | precedent throughout; §8 items 2–3 untested |
| 2 | A tab inside a vanilla window | 1 per host, 1,800–2,100 lines each | custom tab names confirmed in game (§3.4); compat cost §7.4 |
| 3 | A redesign for a wider or two-column layout | as 1 or 2 | new work, not relocation |

## 5. What an implementation needs

- **Per system:** move each top-level widget body into a `type` and leave a named wrapper for the journal entry (§3.3).
- **The window shell** (once): a scripted-widget registration, a `default_block_window` host, a close button with `shortcut = "close_window"`, a tab strip if several systems share it, and the panel-stack handling from §3.6.
- **Gating:**
  - the root on a played country;
  - each system on `has_journal_entry` and its game rule, through a scope-free `is_shown` scripted GUI (gotcha #22 in the GUI guide);
  - the JE datacontext only under that gate.
- **Space race:** `GetPlayerJournalEntry` takes a literal key, so its nine entries need nine gated blocks.
- **The journal entry:** a shorter body and an "open the panel" button, or keep the widgets in both places.
- **Player guide:** this is a player-facing change, so update the chapters, screenshots and PDF.

### 5.1 Adding a tab: the checklist (from the Nuclear pilot, 2026-09-30)

Each later tab is a copy of the Nuclear one (`gui/panel_military.gui`, the two `### MOD: Nuclear tab` blocks). What it took:

- **Gates**, in `common/scripted_guis/te_system_tab_sguis.txt`: `te_<host>_<system>_tab_sgui` (the rule and `has_journal_entry`) and `te_<host>_<system>_tab_unlock_sgui` (`is_shown` the rule; `is_valid` the entry's own unlock test). If that test is an `OR`, or reads through one, wrap it in one `custom_tooltip` in a trigger of its own (`nuclear_program_entry_unlocked` wraps the entry's `possible`), and add that trigger to `UNLOCK_TRIGGERS` in `test_un_layout.py`.
- **The tab button:** six blockoverrides on a free slot of the host's strip (`*_button`, `_tooltip`, `_click` with `enabled` on the gate, `_visibility` and `_visibility_checked` both testing the unlock gate, `_selected`), plus an optional `*_button_icon`.
- **The content:** a header outside the gate; the gate on a parent; the `GetPlayerJournalEntry('<key>')` datacontext on a child with `minimumsize = { 520 -1 }` and `parentanchor = hcenter`. In it, the types the journal roots wrap, in the entry's order, then Open Journal Entry.
- **What the journal draws that no composer does:** the goal bar of an entry with `progressbar = yes` and no bars-on-top marker (`te_je_goal_bar`; only Nuclear so far), scripted bars (`te_je_scripted_bars`, drawn by Banking's overview), the status description (`te_je_status_desc`; drawn only by the UN tab: Banking and Hegemony leave it to the journal, and Nuclear's is empty while the entry is active), and human scripted buttons (`te_je_scripted_buttons`). Every scripted button of the six systems still without a tab is the AI's (`is_ai = yes`), so none needs the grid.
- **Buttons and steppers need nothing more.** The panels' scripted GUIs take `JournalEntry.GetCountry.MakeScope` as their root, and that resolves to the player under the tab's datacontext as it does in the journal.
- **Loc:** the tab name, its tooltip, the locked tooltip (ending `It opens once:\n`, which `check_gui_lint.py` warns about, as for every tab), the Open Journal Entry tooltip, and the unlock line.
- **Tests:** the tab block composes the roots' types in order and ends with the link, the gate sits above the datacontext, the button is greyed on the gate (`MilitaryTabTest` in `test_nuclear_layout.py`).
- **Docs:** the widget table in `gui_modding_guide.md`, the system's "Second host" line in `journal_entry_systems.md`, this file's header, and the player guide's chapter plus the PDF.
- **Per system:** Space Race is nine entries in one file (`je_space_race.txt`), so nine gated blocks. Global Warming, Space Race and the Colonial Empire mount the bars-on-top marker and draw their own progress, so they need no goal bar.

## 6. Size of each system

Widget lines, the entry's scripted buttons, and the number of top-level widgets attached. With reuse (§3.3), work grows with the third column, not the first.

| System | Widget lines | JE buttons | Top-level widgets | Natural host (owner's call) |
|---|---|---|---|---|
| Banking | 4,011 | 78 | 4 | Budget |
| United Nations | 3,369 | 25 | 2 | Diplomacy (crowded) or own window |
| Nuclear | 1,946 | 2 | 4 | Military (tab, 2026-09-30) |
| Cultural Hegemony | 1,434 | 10 | 3 | Society |
| Strategic Reserve | 1,165 | 2 | 1 | own window |
| Space Race | 1,061 | 32 over 9 entries | 9 | own window |
| Global Warming | 819 | 16 | 3 | own window |
| Covert Warfare | 694 | 2 | 3 | own window |
| Colonial Empire | 680 | 9 | 2 | own window |
| Grand Monuments | 293 | 0 | 2 | own window |

The first system carries most of the cost (the shell, gating and button). Each later one is mostly a wrapper, a tab and loc.

## 7. The Community Mod Framework and Demography

### 7.1 What Demography does

**An earlier version had a fifth "Demographics" tab in the Society panel; v14 does not.**
- *The earlier tab.* A screenshot of that version shows the tab next to Statuses, Cultures, Religions and Classes, with the section heading "Country Demographics (all owned states)". It was a `culture_panel.gui` replacement, and the header comment of `demo_country_panel.gui` still describes it.
- *What v14 ships instead.* No `culture_panel.gui`. The tab's loc key `DEMO_C_PANEL_TAB` ("Demographics") still ships, but no `.gui` references it. `DEMO_C_PANEL_HEADER`, the screenshot's heading, is now the title of a `default_block_window` in a scripted widget (`demography_cmf_panel.gui`), opened from CMF's sidebar (§7.2).
- *What that proves.* A mod-added Society tab has worked in-game, and five tabs fit that row. The old file is gone, so it is unknown whether the tab used a new tab name or one vanilla already defines. The latter would be something like `old_default`, which `culture_panel.gui` gates a dead block on.
- The same author later moved the country view to a sidebar window. The reason is not documented.
- Its per-state view is inside a full replacement of `states_panel.gui` (4,874 lines; `demo_demographics_panel` at line 2877).
- Its pension, child-benefit and retirement-age controls are inside a full replacement of `budget_panel.gui` (2,610 lines).

### 7.2 What CMF offers for this

CMF describes itself as a framework for mod inter-operability (GitHub `Victoria-3-Modding-Co-op/Community-Mod-Framework`, wiki "Custom Sidebar Buttons" and "UI Extensions").

**A sidebar registry.**
- *Registering:* CMF redefines the `information_panel_bar` type to add a `custom_sidebar` column below Map List (`com_gui_sidebar.gui`). A mod registers a button by adding `flag:<name>` to the global variable list `custom_button_list_flag`, or the country list of the same name. Demography does it in `common/history/global/`.
- *Defining:* the button's icon and label come from a never-used ideology `<name>` (`show_in_list = no`, `character_ideology = no`), its loc keys `<name>` / `<name>_desc` / `<name>_tooltip`, and a scripted GUI `<name>` for `is_shown` / `is_valid` / `effect`.
- *Clicking:* sets `GetVariableSystem('com_open_window', '<name>')`. The mod's window shows on `HasValue('com_open_window', '<name>')`, and CMF clears the value when a vanilla panel or the ledger opens (§3.6).

**Other pieces that apply here:**
- **A full-screen flag.** `com_fullscreen` hides vanilla's HUD while a full-screen custom window is open.
- **JE extras.** Journal-entry widget injects, styled progress bars, and per-entry variables that hide parts of the journal panel (`com_hide_status_desc`, …).
- **A detection trigger.** `zz_com_detection_trigger.txt` holds `REPLACE_OR_CREATE:community_framework_is_active = { always = yes }`, so a mod can ship its own `always = no` and branch on it.

### 7.3 How CMF changes vanilla

Two techniques:
- **Whole-file replacement:** `eventwindow.gui`, `error_deer.gui`, the 11 vanilla `common/parties/*.txt` files, and three `common/war_goal_types` files. It also applies `REPLACE_OR_CREATE:` to ten vanilla laws.
- **Redefining 29 vanilla GUI types from differently named files.** Examples: `00_MPM_production_methods.gui`, `com_gui_journal_entry.gui`, `com_gui_sidebar.gui`, `com_gui_society_panel.gui`. It replaces one type, not the file.

CMF's contributing guide asks files to be named by whether they must overwrite or be overwritten (`00_`/`com_` vs `ycom_`/`zz_`). Which of two definitions of one GUI type wins is **[untested]**, and two readings fit CMF's naming:
- *First-loaded wins*, with files interleaved alphabetically across vanilla and mods: `com_gui_sidebar.gui` sorts before `information_panel_bar.gui`.
- *Mod files load after vanilla and the last definition wins.*

This mod never redefines a vanilla type from a differently named file, so its own logs say nothing either way.

### 7.4 Collisions with this mod today (with or without adopting CMF)

- **Demography + this mod:** both replace `states_panel.gui` in full. The playset order keeps one and drops the other: the mod's tourism card and state tiles, or Demography's state view. A Banking tab in `budget_panel.gui` (§3.4) would add a second such collision.
- **CMF + this mod:** 11 GUI types are customized by both:
  - `condensed_building_information`, `condensed_building_information_pms` (`building_details_panel.gui`);
  - `building_browser_building_item`, `building_browser_building_type_item` (`building_browser_panel.gui`);
  - `buildings_production_method_item`, `old_buildings_production_method_item` (`production_methods.gui`);
  - `goods_state_panel_input_output_item` (`goods_state_panel.gui`);
  - `journal_entry_panel` (`journal_entry.gui`);
  - `mobilization_widget` (`panel_military.gui`);
  - `state_panel_buildings_content`, `state_panel_buildings_fixed_bottom` (`states_panel_buildings.gui`).

  Whichever reading of §7.3 holds, one side's changes to each type are dropped without a log line. If CMF's win, this mod loses among others its one-line `journal_entry_panel` change, so the banking bars would draw twice. CMF also redefines `society_panel` and `information_panel_bar`, the exact types a Society tab or a sidebar button would change.
- **Any mod that replaces `topbar.gui`:** since the Banking top-bar readings (2026-09-30), this mod replaces vanilla's `topbar.gui` in full, to put three icons after MONEY. Top bars are a common target for UI mods, and the playset order keeps one file. If the other mod's wins, the three icons are gone and nothing else of this mod's breaks; if this mod's wins, the other mod's top bar changes are dropped. The mod's change is one line (`te_banking_topbar_readings = {}`), so a compatibility patch is that line in the other mod's copy. CMF does not replace the file; whether `topbar` is among its 29 redefined types (§7.3) was not checked.
- **CMF + this mod, script:** CMF's `REPLACE_OR_CREATE:` covers ten vanilla laws. This mod `INJECT:`s into eight of them (all but `law_no_schools` and `law_private_schools`), from five files. Tracked in #557. If directives apply in alphabetical file order (assumed, not documented; `scripting_best_practices.md`), `colonial_empire_law_injections.txt` sorts before CMF's `com_distribution_of_power.txt` and `com_governance_principles.txt`. The colonial-stability modifiers it injects into `law_autocracy` and `law_oligarchy` would then be wiped whenever CMF is enabled. The other four files sort after `com_*` and would survive. **[untested]**

### 7.5 Should this mod use CMF?

**Not as a hard dependency.**
- Every player would need CMF, which changes parties, movements, laws and many of the panels this mod also changes.
- CMF is labelled `[1.13]` (`supported_game_version: 1.13.*`) against game 1.14.4. It is actively maintained (repo pushed 2026-09-28), but a dependency ties this mod's releases to its patch cadence.
- The mod state server and the audits would not see CMF's scripted GUIs or ideologies.

**Optional integration is possible and cheap:**
1. Ship `community_framework_is_active = { always = no }`. CMF's `REPLACE_OR_CREATE` overrides it when CMF is present.
2. Register a CMF button as in §7.2. Do it from `on_game_started`, guarded by `is_target_in_global_variable_list`, because `history/global` only runs on a new game. Without CMF, the list and the unused ideology do nothing. The ideology needs excluding from the ideology generator and audits.
3. Key the mod's windows on CMF's own `com_open_window` value. It is a client-side string, so this needs no dependency, and with CMF present the windows close along with every other CMF window.
4. Show the mod's own fallback button only when `community_framework_is_active` is false, through an `is_shown`-only scripted GUI.

Regardless of adoption, §7.4 is worth fixing or documenting for players who run CMF-based mods: a compatibility note, or a CMF-aware copy of the 11 types.

## 8. In-game tests before building

Each fits in one throwaway test file and one launch.

0. **CMF and this mod together:** which of the 11 shared types win (§7.4)? Check the banking entry's bars (drawn once or twice), the production-method rows and the building details; grep `debug.log` for GUI type messages. The same launch answers §7.3.
1. ~~**`InformationPanel.SelectTab('te_test')`** in a copy of `budget_panel.gui`: does the tab select and stay selected?~~ Yes (Banking prototype, 2026-09-28).
2. **`GetPlayerJournalEntry('je_x')`** for an entry the player lacks, and for one inactive with `is_shown_when_inactive`: is it null, is it the entry, and what is logged? (For an active entry it works: Banking prototype, 2026-09-28.)
3. **A hidden scripted widget:** does `visible = no` on the window root stop its children from updating? A JE widget exists only while the journal is open; a scripted widget exists all session. If a hidden 3,000-line body keeps updating, it floods the log like gotcha #14 in the GUI guide, for the whole session.
4. **Law directive order with CMF:** is `country_colonial_stability_drift_add` from `law_autocracy` in the modifier breakdown when CMF is enabled?

## 9. Recommendation

1. Run §8.
2. If custom tabs work, pilot Banking as a Budget tab. It is the headline case and exercises every piece. Note the Demography collision on `budget_panel.gui`.
3. Put systems with no natural vanilla home (space race, covert, global warming, strategic reserve, colonial, monuments) in one mod window with its own tabs, not a sidebar button each. Nuclear went to the Military panel (owner, 2026-09-30).
4. Take CMF as an optional integration (§7.5), not a dependency.
