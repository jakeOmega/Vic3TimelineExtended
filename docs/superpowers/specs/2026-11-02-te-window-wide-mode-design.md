# Timeline Extended window: a wide mode and every system tab (2026-11-02)

> **Status: built 2026-11-02** in #1327–#1337, from its
> [plan](../plans/2026-11-02-te-window-wide-mode.md); § 9.9's observer guard in #1325.
> Left: § 9.7 (the hosts' vanilla bases, on the owner's machine) and the play-test list
> (`docs/testing/te-window-wide-playtest.md`). Written against `main` at `62f7200`; the
> text below is the design as scoped.

## 1. The request

The owner, 2026-11-02:
- A button in the Timeline Extended window that switches it between today's
  side-panel width and a full-screen window, as the Census Data window shows its
  Demographics tab.
- Every system tab that now lives in a vanilla panel also shown in the window,
  kept where it is as well, with a narrow and a wide version of each.
- Anything worth standardizing for maintenance along the way, each with a
  recommendation (§ 9).

## 2. Decided by the owner (2026-11-02)

- **The ten tabs to mirror:** Banking, Tax Code and Budget Breakdown (Budget
  panel); Strategic Reserve and Global Warming (Market); Demographics
  (Population); Cultural Hegemony (Society); the United Nations (Diplomacy);
  Nuclear Weapons and Covert Warfare (Military). Budget Breakdown is optional,
  "nice for consistency". With the window's own five, that makes fifteen tabs.
- **The strip:** both options of § 5 are acceptable: rows of tabs when narrow and
  one strip when wide, or grouped tabs. § 5 recommends the rows.
- **The wide layouts cover all fifteen tabs**, the window's own five included,
  since a single 520 column in a full-screen window would waste it.

## 3. What exists today

- **The window** (`gui/te_systems_window.gui`, 1,163 lines) is vanilla's
  `default_block_window`, 540 wide, in a scripted-widget root on
  `layer_ingame_menu` whose vbox starts under the top bar (`margin_top = 85`). One
  strip of five: Nation, Space Race, Grand Monuments, Colonial Empire, Seabed. The
  chosen tab is the client-side `te_systems_window_tab`; the shown tab is "the
  last one chosen while it is open, else Nation", written as hand-made
  `te_systems_window_<tab>_selected` / `_unselected` templates. Every tab's
  content is written inline, including nine near-identical Space Race milestone
  blocks.
- **The ten mirrored tabs** live in six full-file overrides: `budget_panel.gui`,
  `market_panel.gui`, `pops_overview.gui`, `culture_panel.gui`,
  `diplomatic_overview.gui` and `panel_military.gui`. Each journal-entry tab
  mounts the same shape, written out by hand each time: a header, the tab's gate
  (`te_<host>_<system>_tab_sgui`, rooted at `GetPlayer`), a
  `GetPlayerJournalEntry` datacontext on a child of the gate, the system's
  overview, status and reference composers, and an Open Journal Entry button.
- **The Census Data window** (`gui/pop_browser_panel.gui`, an override of vanilla's
  `fullscreen_block_window`) shows `te_demog_browser_sections`: the Population
  tab's sections in three columns of a fixed 520, 30 apart, with a horizontal
  scroll bar for narrow screens (`gui/te_demographics_layout.gui`).
- **Every system is built from section types** (`te_<system>_sec_*`, the overview
  panels, the history panels), composed in one place per system (issue #1029's
  "one layout, every host"). That is what makes this cheap: the window instances
  the same types, and a wide layout is one new composer per system.
- **Nothing a section draws reads its host panel**, except Demographics' Wealth
  strata incomes, which read `PopsOverviewPanel`. The Census window already
  blanks them (the `te_demog_wealth_strata_incomes` block). The hosts' own
  extras that do read the host stay in the host: the Market panel's map-mode
  reset (`MarketPanel.GetMapModeList.SelectDefault`), Global Warming's
  other-market view (`MarketPanel.GetMarket.GetOwner`) and the Reserve's note
  for another market.

## 4. The wide frame and the toggle

### 4.1 The frame

Vanilla's `fullscreen_block_window` wires its Close button to
`InformationPanelBar.ClosePanel` outside any block
([Space Race UI pass](2026-10-31-space-race-ui-pass-design.md) § 11), which does
nothing for a scripted widget. So the wide frame is a copy of the type under the
mod's name, `te_fullscreen_block_window`, with Close and Back clearing
`com_open_window` as the narrow frame's do.

- **Vanilla's file is needed.** `block_windows.gui` isn't in the repository and a
  cloud container has no game. The implementer takes it from the owner's install
  (1.14.x) and commits it as `test_fixtures/vanilla_gui/block_windows.gui`, with a
  test that the copy matches vanilla's type except the close and back blocks
  (the `country_panel.gui` / `gen_nation_tab.py` precedent). A patch that changes
  vanilla's type then fails the suite instead of drifting silently.
- **Where it sits.** Keep the root's `margin_top = 85`, so the frame starts under
  the top bar as the narrow one does (§ 10, item 1).
- **Footer.** Both frames get a `fixed_bottom` for the Tax Code tab's draft and
  bill summary (§ 6). The narrow frame has none today.

### 4.2 The toggle

- **State:** one client-side key, `te_systems_window_wide` (`GetVariableSystem`,
  never saved, per player and session). The root shows the narrow frame without
  it and the wide one with it. The chosen tab is a separate key, so it survives
  the switch, and gotos into the window (the state view's Grand Monument card)
  open whichever width was last used.
- **The button:** in `fixed_top`, in both frames, in the same place, right-aligned
  on a slim row above the strips. The blocks `default_block_window` exposes
  (`gui_modding_guide.md`: the header name, back, close, `fixed_top`, `content`,
  `fixed_bottom`) leave no header slot for it. A small text button, "Full Screen"
  in the narrow frame and "Side Panel" in the wide one, with a tooltip saying what
  it switches to. It needs no art. An icon can replace it later (style guide
  rule 10, listed in `docs/systems/te_systems_window_gui_icons.md`).

### 4.3 How wide

Three columns are 3 × 520 + 2 × 30 = 1,620 px of content, about 1,700 with the
frame and sidebar. Below that effective width (1600 × 900, or a larger UI scale)
the content scrolls sideways, as the Census window does today. Two columns,
1,070 px, fit a 1280-wide screen. This spec assumes three, the Census window's
choice, with two-column systems where the content is short (§ 7). Open question
1 (§ 12).

## 5. The strip and tab selection

Fifteen tabs. Style guide rule 9 (owner, 2026-10-17) allows one strip per window
of up to six tabs, so either option amends it.

### 5.1 Recommended: rows of five, one strip when wide

| Row | Tabs | Where they also live |
|---|---|---|
| 1 | Nation, Space Race, Grand Monuments, Colonial Empire, Seabed | the window only (unchanged) |
| 2 | Banking, Tax Code, Budget Breakdown, Strategic Reserve, Global Warming | Budget, Market |
| 3 | Demographics, Cultural Hegemony, United Nations, Nuclear Weapons, Covert Warfare | Population, Society, Diplomacy, Military |

- **Narrow:** three stacked strips, each vanilla's own five-slot `tab_buttons`, so no
  new strip type. Each slot keeps today's width, 104.8 px.
- **Wide:** the same three strips side by side in one hbox, 1,620 wide over the
  columns: one strip of fifteen with the same slot width as narrow, for free.
- **Selection is unchanged:** one key, today's rule. A system tab shows when it
  is the stored choice and open; Nation shows otherwise. Nation's template ORs
  fourteen terms instead of four, so it grows linearly.
- **Names:** the window shows each system's full name (owner, 2026-09-30,
  `FULL_NAMES`), so two-word names stack on two lines as "Grand Monuments" does
  now, and "Demographics" shrinks toward the 12 pt floor. Global Warming and
  Strategic Reserve take their entries' names, not the Market tabs' "Climate"
  and "Reserve" (open question 2).
- **Cost:** two more strips' height in the narrow window than today's one.
- The developer tax-probes strip stays as it is, below the rest.

### 5.2 Acceptable: grouped tabs

Six category tabs on one strip, each with a sub-strip of its systems:

| Group | Sub-strip |
|---|---|
| Nation | (none) |
| Economy | Banking, Tax Code, Budget Breakdown, Strategic Reserve |
| Society | Demographics, Cultural Hegemony, Grand Monuments |
| World | United Nations, Global Warming, Colonial Empire |
| Security | Nuclear Weapons, Covert Warfare |
| Frontiers | Space Race, Seabed |

Less chrome and a findable grouping. The cost is a second key per group to
remember the last leaf, a "first open leaf" fallback when that one is grayed, a
group grayed when none of its leaves is open, and templates far harder to
write by hand. It also moves the window's four system tabs down a level.

**Recommendation: § 5.1.** One key, vanilla's own strip type, the wide strip for
free, every tab visible at once. Switch to § 5.2 if three rows look heavy in the
play-test; with the registry of § 9.3 the switch is a registry change plus the
group logic.

## 6. The ten mirrored tabs (narrow)

Each system gets one **tab body type**, used by its vanilla host and by the window
(§ 9.1), so the two copies can't drift. The host keeps its outer flowcontainer
(`visible = IsTabSelected(…)`, its fade and position templates) and its own
extras that read the host; the body holds the rest. The edits to the six
overrides stay inside their `### MOD:` / `### TE:` blocks. Gates: the hosts'
own, all rooted at `GetPlayer`, reused as they are; no new scripted GUIs.

| Tab | What its body carries beyond the common shape |
|---|---|
| Banking | The #805 readout branch: two headers, one shown, and the readout with its note for a country with a monetary stance and no entry |
| Tax Code | The full code's sections and the Light code's, as `te_tax_status_sections` switches them. Its draft and bill summary goes in the frame's `fixed_bottom` (§ 4.1), shown only on this tab, and the body drops its own copy (`blockoverride "draft_summary" {}`), as Budget does |
| Budget Breakdown | No entry, no gate, no Open Journal Entry: always open |
| Strategic Reserve | The player's own market only. The window always shows that, so the host keeps its other-market note |
| Global Warming | The own-market view only. The host keeps the other-market branch and its map-mode reset (`MarketPanel` reads) |
| Demographics | No entry. Its sections read the Country in their context, which the Population panel supplies, so the window's body sets `datacontext = "[GetPlayer]"`. The Wealth strata incomes read `PopsOverviewPanel`, which the window lacks, so the window gets its own composer in `te_demographics_layout.gui`: the tab's sections with the `te_demog_wealth_strata_incomes` block blanked, as the Census window's composer does. `test_demographics_layout.py` already holds every host's order. The Population panel keeps its mount as it is |
| Cultural Hegemony | Nothing extra. `society_panel_tab_contents_properties` is a Society template and stays in the host |
| United Nations | Its Status section with its `te_un_tab_status_closed` flag |
| Nuclear Weapons | The goal bar under The Program (`te_je_goal_bar`, gated on `nuclear_program_has_programme_sgui`) |
| Covert Warfare | Nothing extra |

- **Collapse flags stay shared.** They are `GetVariableSystem` keys, so a section
  collapsed in Budget is collapsed in the window too, as the Population tab and
  the Census window share theirs today. Never both on screen at once: the window
  closes vanilla's side panels when it opens.
- **Links stay as they are.** Text that sends players to "the UN tab of the
  Diplomacy panel" (style guide rule 9) is still true. No loc rewrite.

## 7. Wide layouts

Each tab gets a wide composer, `te_<system>_wide_sections`, beside its narrow
composers: the same sections in fixed 520 columns read down then across, as
`te_demog_browser_sections` does, built on one shared column type (§ 9.4). The
overview stays a 520 block at the top of column 1. A true full-width overview
would be a redesign of every system and is out of scope.

Proposed columns. Section types are named without their `te_<system>_` prefix.
They were balanced by each section's GUI line count, which is a poor proxy for
height (tooltips count, collapsed sections don't show), so the play-test
settles them.

| Tab | Column 1 | Column 2 | Column 3 |
|---|---|---|---|
| Nation | overview, governance, society | economy, science and space, international | sources, how |
| Space Race | the milestones under way | Space Powers, Orbit | How the Space Race Works |
| Grand Monuments | overview, commission, decisions, awaiting | archaeology, national, monuments | trophies, abroad, how |
| Colonial Empire | overview, holdings, stability | pressure, programmes | history, how |
| Seabed | overview, policy | basins | how |
| Banking | overview, active | monetary, interventions | history, how |
| Tax Code (full code) | overview, politics, pending, obligations | enacted table, workbench, review | history, how |
| Tax Code (Light code) | overview, light section | light how | (none) |
| Budget Breakdown | income | expenses | how (split out of `te_budget_breakdown_panel` into a type) |
| Strategic Reserve | overview, inventory | how | (two columns) |
| Global Warming | overview, policies | emitters, transition | history, how |
| Demographics | `te_demog_browser_sections`, unchanged | | |
| Cultural Hegemony | overview, board | programmes, breakdown, models | history, how |
| United Nations | overview, Status, assembly | why, missions, programmes, mandates | obligations, dev fund, exposure, authority history, archive, how |
| Nuclear Weapons | overview, programme and goal bar, crisis, strike, world crises | posture, forces, home, reputation | taboo, delivery, powers, how |
| Covert Warfare | overview, operations | funding, networks, counterintel | known, how |

- **The UN's Assembly is the largest section by far** (about 3,500 GUI lines with
  what it instances), so it may need column 1 to itself.
- **The Space Race's planned tabs** ([Space Race UI pass](2026-10-31-space-race-ui-pass-design.md)
  § 11: Mission Control, Fleets, Colonies, Solar System) sit inside Solar System
  Colonization's status and come with it into column 1. The same spec's later
  "full-page window" and its schematic would live in this frame.
- Explanations stay collapsed in wide mode (style guide rule 1); nothing else
  about a section changes.

## 8. Tests, loc and docs

- **`test_te_systems_window.py`** changes the most:
  - `SelectionTest` enumerates every combination of open tabs: 486 cases today
    (3⁴ open and on-strip states times six stored values), about 77 million at
    fourteen system tabs (3¹⁴ times sixteen). Every template reads only the
    stored tab's gates and its own, so enumerating per stored value is enough.
  - `StripTest`'s "one strip holds all five", `FULL_NAMES`, `NAME_WIDTH` and
    `TabContentTest` grow to fifteen tabs and three rows.
  - New checks: the toggle in both frames, the wide frame's close and back, and
    the copy of vanilla's frame (§ 4.1).
- **Each system's layout test** (`test_<system>_layout.py`) gets its wide
  composer's order and widths, through the one shared check of § 9.5.
- **Demographics** gets the Census window's check that nothing the window draws
  reads `PopsOverviewPanel` (`test_demographics_census_window.py`).
- **New GUI files** need a row and the count in `gui_modding_guide.md`'s "This
  Mod's GUI Files" (`test_tax_code_bypass`); a generated one also needs
  `docs/auto_generated_files.md` and `scripts/nightly_audit_select.py`'s
  `EXCLUDED_REGISTRY_GLOBS` (`test_nightly_audit_select`).
- **Loc:** the toggle's label and tooltip; each new tab's name, tooltip and
  grayed checklist header (§ 9.6); the launcher tooltip, which lists the tabs
  (`te_systems_window_launcher_tt`).
- **Docs:**
  - style guide rule 9: the window also mirrors the vanilla-home tabs, and the
    strip rule;
  - `system_panels_feasibility.md`'s status;
  - `gui_modding_guide.md`'s window section (a CRLF file: keep its line endings);
  - `mod_systems/state_and_nation_panels.md`;
  - the icons doc;
  - a play-test list, `docs/testing/te-window-wide-playtest.md` (§ 10);
  - the player guide's window section (`01-introduction.md`), and a PDF rebuild.

## 9. Standardization

Each item says whether it is worth doing as part of this work.

### 9.1 One tab frame and one body type per system: **do it**

The eight journal-entry mounts were each written by hand, and they have drifted:
- **Three fade templates:** `default_content_fade` (Banking, Tax Code, UN),
  `default_fade_in_out` (Nuclear, Covert, Global Warming, Strategic Reserve, the
  window's tabs) and Society's own `society_panel_tab_contents_properties`.
- **The column:** fixed at 520 in five mounts (Tax Code, Nuclear, Covert, Global
  Warming, Strategic Reserve) and left to its content in three (Banking, Cultural
  Hegemony, UN), against style guide rule 8.
- **Open Journal Entry, nineteen copies** (eleven in the window, eight in the
  hosts), in three fonts: `fontsize_large` on Banking's, `te_tax_fontsize_row` on
  Tax Code's, and the button default elsewhere.

Mirroring doubles the mounts, so fix the shape once:
- **`te_system_tab_frame`**, in `gui/te_system_tab_widgets.gui` (the shared tab
  pieces' file): the header, the gate on a parent of the datacontext, the 520
  column, the content, and the Open Journal Entry button, each a block:
  `tab_header`, `tab_before_gate` (Banking's readout), `tab_gate`, `tab_entry`,
  `tab_content`, `tab_open_journal` (emptied where there is no entry) and
  `tab_width` (520, or 1,620 for a wide body).
- **One `te_<system>_tab_body` per system** derives from it with its blocks
  filled, and is used by the host and the window. The host's outer
  flowcontainer keeps its fade, position and host-only extras.

This touches all six overrides, inside their mod blocks, with no visible change
there except the three columns' new fixed width (the play-test confirms nothing
moved). The button font becomes a block (`tab_open_journal_font`) rather than one
font for all: Banking and Tax Code set their row fonts there, since
`test_tax_code_layout.py` holds every Tax Code button to `te_tax_fontsize_row`.

### 9.2 The gate names: **leave them**

The gates are named for their first host (`te_budget_banking_tab_sgui`,
`te_military_nuclear_tab_sgui`), so in the window they read oddly. Renaming them
to `te_tab_<system>_sgui` touches 184 references in 48 files across `gui/`,
`common/`, tests and docs, including archived specs, to fix only a name. The
GUI lint already errors on a scripted GUI that doesn't exist, so a rename would
be safe; it just isn't worth it. Say in the gates file's header that a name
records the tab's first host.

### 9.3 The window's strip, templates and tab mounts from one registry: **do it**

At fifteen tabs the window carries:
- ninety strip blockoverrides, six per tab, each tab's tooltip a three-branch
  `SelectLocalization` (open, met, the checklist);
- thirty selection templates;
- two content mounts per tab, narrow and wide;
- the Space Race's nine milestone blocks.

All of it follows from a table: key, row and slot, label, tooltip keys, open
and unlock gates, body type, wide type. A generator,
`scripts/generators/gen_te_systems_window.py`, writes it to
`gui/te_systems_window_generated.gui` from a registry in the script, and
`test_te_systems_window.py` reads the same registry. The hand-written file
keeps the frames, the launcher and the root. Adding a sixteenth tab becomes one
line.

- **Precedent:** `gen_nation_tab.py`, a manual generator whose test holds the
  committed output current.
- **Cost:** a generator of perhaps 300 lines, its `--check`, and the generated
  file's two registrations (§ 8).
- **Stay manual:** keep it out of `POST_LOAD_REGENERATORS`, so a reload never
  rewrites the window.
- **Without it:** § 5.2's group logic is impractical to write by hand, so the
  generator is what keeps that option open.

### 9.4 One column type for every wide layout: **do it**

The wide layouts would be fifteen copies of "a horizontal flowcontainer, columns
of a fixed 520, 30 apart". Instead:
- **The type:** `te_ui_columns_three` and `te_ui_columns_two` in
  `gui/te_widget_library.gui` (the `te_ui_` shared types' file), with
  `column_1` … `column_3` blocks.
- **Each wide composer** becomes a short instance of it.
- **The Census window's layout:** rebase `te_demog_browser_sections` on it in the
  same PR. Its test reads the composer's structure and needs a small update.

### 9.5 One check that each wide layout matches its narrow one: **do it**

The real drift risk: a section added to `te_banking_status_sections` and
forgotten in the wide composer, so it never shows full-screen.
- **The check:** one shared test helper. For every system, the wide composer
  instances exactly the narrow composers' sections, in the same order read down
  the columns, and every column is a fixed 520. It applies Demographics' Census
  check (`test_demographics_layout.py`) to every system.
- **The helpers:** today 87 test files each define their own `_close`,
  `_block_at`, `_type_body`, `_strip_comments` or the like. Put the shared check
  and the helpers it needs in a `gui_test_helpers.py` module.
- **Existing tests:** move them onto it only when they are next touched, not in
  a sweep.

### 9.6 The new tabs' text points at the hosts' text: **do it**

The window's new tab tooltips would repeat what each host tab's says, so the
registry names the host's own key wherever its text fits the window as written:
one key, no copy to drift. Two don't fit: Global Warming's and the Strategic
Reserve's speak of "another market" and "this tab", so they get window keys.
The names (`te_window_tab_<system>`) are the window's own, since it shows full
names. So are the grayed checklists' headers where the host's tab name differs
(Hegemony, UN, Nuclear, Covert, Climate, Reserve), in rule 9's one shape (WIN-1).

### 9.7 Vanilla bases for the six host overrides: **worth doing, on the owner's machine, after the build**

`pop_browser_panel.gui`, `topbar.gui`, `goods_panel.gui`,
`add_consumption_tax_menu.gui` and `country_panel.gui` have their vanilla base
committed under `test_fixtures/vanilla_gui/`, and tests hold the overrides to it
(`test_demographics_census_window.py`, `test_topbar_banking.py`,
`test_tax_code_bypass.py`; the country panel through `gen_nation_tab.py`). The six
tab hosts have none.
- **Why now:** § 9.1 rewrites all six hosts' mod blocks, which is the moment to
  prove nothing outside them moved.
- **Why after the build:** the next vanilla patch's 3-way merge needs the
  pre-patch base anyway, and a committed one is easier to merge against.
- **Not equally cheap:** `panel_military.gui` and `market_panel.gui` carried mod
  changes before their tabs, perhaps unmarked, so their cost is unknown until
  their diffs are taken. Do the files whose only changes are the tab blocks,
  and leave the others until a patch touches them.
- **One marker:** Market's blocks are marked `### TE:` / `### END TE ###` and
  the rest `### MOD:` / `### END MOD ###`; settle on the latter for the test.

### 9.8 The shared section widgets: **not in this work**

The Space Race UI pass (§ 13) plans `te_ui_*` section headers, subheaders, notes,
value rows and overview cells to replace each system's own copies. That changes
every system's insides and the tests that read their font templates, and the
wide layouts don't need it. Keep it a separate project.

### 9.9 Found in passing: the hosts' tab buttons lack the observer guard

An observer has no `GetPlayer`. Each of a host's tab buttons reads its gate as
`GetScriptedGui(…).IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )`, and
for an observer that logs a null-country error every frame
(`gui_modding_guide.md`'s observer gotcha). The Market panel's tab buttons got
`Not( GetMetaPlayer.IsObserver )` first on 2026-10-25. The tab buttons of
Budget, Society, Military, Diplomacy and Population didn't. It is a separate
fix, outside this work; the window's own root already excludes observers.
The generated strip (§ 9.3) needs no guard for the same reason.

## 10. In-game checks

None gates a merge (`CLAUDE.md`). They go on `docs/testing/te-window-wide-playtest.md`:
1. **The layer.** The window is on `layer_ingame_menu`, vanilla's full-screen
   windows on `layer_ingame_hud`. Do the top bar and the outliner draw over the
   wide frame? The Space Race spec inferred so, unseen. Fallbacks: leave the
   outliner's column free, or raise the layer.
2. **The sidebar and the launcher** beside the wide frame: covered, or covering?
3. **Width:** at 1600 × 900 and a larger UI scale, the sideways scroll works and
   nothing clips.
4. **Behavior:** Escape, Back and Close close the wide frame; a vanilla panel or
   the ledger opening closes it; the toggle keeps the tab; Tax Code's footer
   shows in both frames.
5. **Columns:** each wide layout's balance, and § 9.1's three newly fixed
   columns in their hosts.

## 11. Build order

The steps are in the [implementation plan](../plans/2026-11-02-te-window-wide-mode.md).

| PR | Contents | Size | Depends on |
|---|---|---|---|
| 0 | This spec and the plan | — | — |
| A | The window's tabs from a registry, no visible change: the tab frame type (§ 9.1), body types for today's five tabs, the generator (§ 9.3), the selection test restructured. Needs no game | medium | — |
| B | The full-screen frame (§ 4, with the owner's `block_windows.gui`) and the toggle. The wide frame shows each tab as a single column | medium | A |
| C | The ten hosts' tabs onto body types (§ 9.1), then in the window (§ 6) as strips 2 and 3 (§ 5.1), with loc (§ 9.6) and Tax Code's footer | large | A, B |
| D0 | The column types (§ 9.4) and the shared check (§ 9.5), Demographics' Census layout rebased on them | small | A |
| D1–D3 | The wide composers (§ 7), a few systems per PR, in parallel | medium each | B, D0 |
| later | Vanilla bases for the hosts (§ 9.7), on the owner's machine | small–medium | C |

Each PR carries its own docs, play-test items and player guide changes. Play-test
after B, before the wide layouts are built against the frame.

## 12. Open questions for the owner

1. **Columns:** three, scrolling sideways below about 1,700 px as the Census window
   does, or two, which fit 1280?
2. **Names:** Global Warming and Strategic Reserve (their entries' names), or
   the Market tabs' Climate and Reserve? Budget Breakdown, or Breakdown?
3. **The strip:** § 5.1 unless the play-test finds three rows too heavy.
4. **The columns of § 7:** a first proposal, to be judged in game.
