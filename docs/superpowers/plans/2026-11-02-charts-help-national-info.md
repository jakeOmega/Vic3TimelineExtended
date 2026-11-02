# System panels: full-screen charts, Help pages and other countries' panels — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Help popup per system in place of each collapsed "How X Works" section, opened with a "?"; a full-screen viewer for each of the 33 history charts; and the Census Data window, renamed National Info, showing another country's public panels, with its controls only for the player's own country.

**Architecture:** Nine PRs in three tracks, each from `main`.
- **Help (H1, H2):** each "How X Works" section's content moves into a help body type, shown by a popup in `te_popups` on `te_popup = help_<system>`. The section stays where it is as a one-line link to its page, and a shared `te_help_button` ("?") sits in each tab's header.
- **Charts (C1, C2):** a registry and generator (`gen_te_history_charts.py`) write each chart as two wrapper types, the panel's size and the viewer's, so no chart is written twice by hand. C1 changes nothing visible; C2 adds the viewer popups and the buttons that open them.
- **Other countries (F0–F5):** F0 makes every mount supply a `Country`, adds the own-country guard and the tests, and changes nothing visible. F1 turns the Census Data window into National Info, its strip and mounts generated from the TABS registry, with Pops and Demographics. F2–F5 bind each public system to `Country` and flip its `public` flag.

**Tech Stack:** Victoria 3 1.14.5 Paradox GUI, Python 3.11/3.12 generators and `unittest` structural tests.

**Spec:** [docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md](../specs/2026-11-02-charts-help-national-info-design.md) (§ numbers below are its sections). It builds on the wide-mode work: [spec](../specs/2026-11-02-te-window-wide-mode-design.md), [plan](2026-11-02-te-window-wide-mode.md). House style: `docs/guides/gui_style_guide.md`. GUI gotchas: `docs/guides/gui_modding_guide.md` (#24, #29, #35, #37 and #45 bite here).

## Global Constraints

- **One PR per section, each from `origin/main`.** On the owner's machine, a sparse worktree: `git -C ~/src/Vic3TimelineExtended worktree add --no-checkout -b <branch> ~/src/vic3te-<name> origin/main`, then `git sparse-checkout set --no-cone '/*' '!/gfx/'` and `git checkout <branch>`. In a cloud session, the session's own checkout on its branch. Never `POST /reload` from a worktree.
- **Order:**
  - H1, then H2.
  - C1, then C2. The two tracks are independent and can run in parallel.
  - F0 after H2 (so the How sections are moved, not rebound) and C1 (so the charts are rebound once, in the registry).
  - F1 after F0 and C2.
  - F2–F5 after F1, in parallel.
  - The owner merges every PR. No self-merge.
- **Python:** the main checkout's venv (`~/src/Vic3TimelineExtended/.venv/bin/python`; in a cloud container `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-docs.txt`). Tests: `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent <venv python> -m pytest -q -p xdist -n 8 <files>`. Run each task's named tests, and the full suite once before opening the PR.
- **Generated files are never hand-edited.** Edit the generator's registry or renderers and run it; `--check` exits 0 before every commit. The generators this plan touches:
  - `gen_te_systems_window.py` (the window, and from F1 National Info);
  - `gen_te_history_charts.py` (new in C1);
  - `gen_nation_tab.py`, `gen_tax_code.py`, `gen_budget_breakdown.py`;
  - `gen_solar_sites.py`, `gen_space_fleets.py`.
- **Files:** exactly one UTF-8 BOM on every `.gui`, `.txt` and `.yml` (a script that writes one must decode with `utf-8-sig`); tab indentation. `docs/guides/gui_modding_guide.md` is CRLF: edit it with Edit, then confirm `grep -c $'\r$'` equals `wc -l`.
- **GUI rules that bite here:**
  - `And` and `Or` take exactly two arguments: build longer ones as binary trees (`or_all`).
  - One `visible` per widget (`test_one_visible_per_widget`): where a template is `using`d, put any further condition on a child.
  - A gate sits on a parent of a `GetPlayerJournalEntry` datacontext, never on the widget that carries it (gotcha #29).
  - No `.GetJournalEntry(` anywhere (gotcha #35; `check_gui_lint.py` errors). Another country is a `Country` datacontext.
  - A chart's plot blocks go on the `te_history_chart` instance, never on a type derived from `te_history_plot` (gotcha #37). A wrapper type that holds a chart instance, as each system's history section does today, is the shape that draws.
  - A tooltip on a `datamodel` item has only the item's context (gotcha #24), so loc it reaches can't read `Country`. A vanilla key that reads its own panel renders only in that panel (gotcha #45).
  - A control that changes a country shows only for the player's own (`Country.IsLocalPlayer`, gotcha #45), through `te_own_country_only` from F0.
- **Loc:** American English. Text another country's panel shows says "the country's", never "our" or "your" (gotcha #45, spec § 6.8). New keys for the window go in `localization/english/te_miscellaneous_l_english.yml`; run `python3 organize_loc.py` and commit everything it moves.
- **Popups:** one at a time, on the client key `te_popup`. A popup reads the player (`GetPlayer`), or a journal entry through `GetPlayerJournalEntry` under a scope-free gate on a parent, as the Space Race's do.
- **Every PR's body** carries a "Player guide" line: the chapters updated, or why none needed it.
- **Gate before each PR:**
  - `scripts/analysis/check_gui_lint.py`;
  - `gui_reference_audit.py --strict`, `loc_coverage_audit.py --strict`, `concept_reference_audit.py --strict`, `long_tooltip_audit.py --strict`, `button_reason_audit.py --strict`;
  - `organize_loc.py --check`, `scripts/analysis/check_loc_spelling.py --check`, `scripts/analysis/check_localization_files.py`;
  - `.venv/bin/ruff check .`, and every touched generator's `--check`;
  - `test_tax_code_bypass.py`, `test_nightly_audit_select.py`, `test_test_files_main_block.py` (a new test file ends with the `unittest.main()` block);
  - the suite.
- **In-game checks never gate a merge.** Each PR adds its own section to `docs/testing/charts-help-national-info-playtest.md` (created in H1): a table of Check, Expect and If it fails, as `docs/testing/te-window-wide-playtest.md` has.

## Owner calls this plan assumes

The spec's open questions (§ 11), with the recommended answers. Each is a small change if decided otherwise:
1. The host is the Census Data window, named **National Info** (F1.3: one loc line).
2. **`POP_BROWSER` is replaced**, renaming the window and both buttons (F1.3). The other answer adds an override of `country_politics_panel.gui` and its vanilla fixture.
3. **The player's own country in National Info** shows the same view with the player's controls (F1.1's own-country mounts). The other answer drops those mounts and keeps Pops and Demographics for the player.
4. **The public list** is § 6.4's (F2–F5). Each system is one `public` flag and its PR.
5. **Grand Monuments** keeps the open opportunity and the interest groups' ledgers private (F3).
6. **Wording:** neutral labels and `SelectLocalization` on `Country.IsLocalPlayer` (each F PR).
7. **The viewer's plot is 1200 wide** for every chart (C1's `LARGE`). The alternative is 960 monthly and 800 annual, two constants.
8. **Help is a popup per system** (H1, H2).

## Review Focus

1. **A Help page opened from anywhere** (a tab, the journal entry, National Info for another country) shows the rules as they stand for the player. Expected: the same body in every case, read through `GetPlayer`, and no `*_how_open` flag left for a moved system. Pinned by `test_te_help_pages.py` (H1, extended in H2).
2. **A chart is one registry entry, drawn at two sizes.** Expected: no hand-written `te_history_chart` instance left in `gui/`, and the panel's charts unchanged by C1. Pinned by `test_te_history_charts.py`'s `test_every_chart_is_generated` and `test_the_small_size_is_todays` (C1).
3. **Another country's figures, not the player's.** Expected: no `JournalEntry` or `GetPlayer` read in a public system's body closure outside `te_own_country_only`, except a marked world read. Pinned by `test_te_system_tab_bodies.py`'s `BindingTest` (F0; each F PR takes its system off `UNBOUND`).
4. **No control for another country.** Expected: every `Execute` in a public body's closure sits under `te_own_country_only`. Pinned by `GuardTest` (F0, same allowlist).
5. **F0 changes nothing visible.** Expected: `Country` is the player in every host before F2 (the frame's root, the window's mounts, the journal roots). Pinned by `MountContextTest` (F0).
6. **National Info's shown tab.** Expected: the last one chosen while it is open for that country, else Pops; switching countries never shows a tab that isn't running there. The Census window stays vanilla's outside its mod blocks. Pinned by `test_national_info.py`'s `SelectionTest` and `test_demographics_census_window.py`'s `OverrideTest` (F1).
7. **Private parts stay private.** Expected, for another country:
   - Banking: no control;
   - Tax Code: no draft, offers or workbench;
   - Grand Monuments: no opportunity or ledgers;
   - Space Race: a band, not exact progress;
   - Nuclear Weapons: the public estimate, not the stockpile.

   Pinned by each system's `PrivateTest` in its layout test (F2–F5).

---

## PR H1: the Help popup, the "?" and the first three pages

Branch `feat/te-help-pages`. Spec §§ 5.2, 7.5.

**The shape.** Each system's `te_<system>_sec_how` keeps its name and its place in every composer, so the composers, the wide layouts and their order tests stay as they are. It shrinks to its header alone, which opens the Help popup instead of expanding. The section's content moves into `te_<system>_help_body`, which only the popup instances. The `*_how_open` flags retire.
- Each frame-based tab also gets a "?" in its header: a `te_help_button` added as a child of the body's `default_header`, `parentanchor = right|vcenter`. That is vanilla's own shape for a button in a header (`states_panel_buildings.gui:180`'s list toggle). It sits in `tab_header`, outside the layout block that `assert_wide_matches_narrow` walks.
- The body's and the popup's names carry a `help` token, so `gui_tree.how_named` still exempts the text from `long_tooltip_audit`'s 500-character cap.

**The 18 sections become 15 pages:**

| Page (`help_<key>`) | Section type(s), file | Header key | Content's reads today, and in the help body |
|---|---|---|---|
| `budget_breakdown` | `te_budget_sec_how`, `gui/te_budget_breakdown.gui:103` | `te_budget_chart_how` (generated by `gen_budget_breakdown.py`) | none |
| `demographics` | `te_demog_sec_how` (`te_demographics_widgets.gui:4797`) and the state's `te_state_demog_how` (`:7723`), one page with the state's own topics under their own subheading | `te_demog_sec_how` | `te_demog_fam_rule` reads `GetPlayer` already |
| `nation` | `te_nation_how_panel`, `gui/te_nation_tab.gui:740` | `te_nation_how_header` | none |
| `banking` | `te_banking_sec_how`, `banking_layout_widget.gui:36` | `banking_dash_how_header` | the monetary topics' gate, `banking_mon_system_shown` on `JournalEntry.GetCountry` (`:107`): rooted on `GetPlayer` |
| `cultural_hegemony` | `te_ch_sec_how`, `cultural_hegemony_widget.gui:2852` | `je_ch_how_header` | none |
| `tax_code` | `te_tax_how_section` (`te_tax_layout_widget.gui:81`) and the Light code's `te_tax_light_how_section` (`te_tax_light_widget.gui:275`), one page, the Light text while `te_tax_show_light_sgui` is shown, the full text otherwise | `te_tax_how_header`, or `te_tax_lt_how_header` under the Light code (a `SelectLocalization` on the same gate) | `GetPlayer` already: the customs gate and 8 loc keys |
| `united_nations` | `te_un_sec_how`, `un_layout_widget.gui:566`, with its nested `te_un_help_authority` and `te_un_help_standing` | `je_un_how_header` | none |
| `nuclear_weapons` | `te_nuclear_sec_how`, `nuclear_layout_widget.gui:61` | `je_nuclear_how_header` | none |
| `grand_monuments` | `te_gm_sec_how`, `grand_monuments_widget.gui:3209` | `gm_je_how_header` | none |
| `space_race` | `te_sr_sec_how` (`space_race_widget.gui:7451`) and `te_sr_sec_how_colonies` (`:7548`), one page, the colony topics under their own subheading | `je_space_race_widget_how_header` | the colonies' root `JournalEntry.IsActive` drops (the topics' own gates decide); their ten gates read `sr_disp_colonies_*` on `GetPlayer` |
| `global_warming` | `te_gw_sec_how` (`global_warming_widget.gui:1736`), and the Fossil Transition's inline How (`:2104`, flag `rt_how_open`) under its own subheading | `gw_how_header` | none in the type. Its composer's rule gate (`:2186`) stays on the link |
| `strategic_reserve` | `te_st_res_sec_how`, `strategic_reserve_widget.gui:2526` | `je_strategic_reserve_how_header` | none |
| `seabed` | `te_seabed_how_panel`, `gui/te_seabed_widgets.gui:1514` | `te_seabed_how_header` | `GetPlayer` already, 5 loc keys |
| `covert_warfare` | `te_covert_sec_how`, `covert_operations_widget.gui:2507` | `je_iw_how_header` | 7 loc keys, about 30 `JournalEntry.GetCountry` script values: `GetPlayer` |
| `colonial_empire` | `te_ce_sec_how`, `colonial_empire_widget.gui:2788` | `je_colonial_empire_how_header` | 3 loc keys (`je_colonial_empire_how_bar_1`, `_bar_2`, `_decolonization`): `GetPlayer` |

A help body reads only `GetPlayer`, never `JournalEntry`. The page then works from any host, a foreign country's panel included, and needs no entry and no gate, so it opens whether or not the player holds the entry. A loc key that some other text also renders, where only `JournalEntry` is in context, is split rather than rewritten (check each with `grep -rn '<key>' gui/ common/`).

Left out: the Construction Market's one-textbox How in vanilla's construction panel (`construction_panel.gui:1344`), which is no system tab, and the debug tax probes' (`te_tp_help_open`).

### Task H1.1: the shared pieces

**Files:**
- Modify: `gui/te_widget_library.gui` (`te_ui_help_popup`, with a header-comment entry), `gui/te_system_tab_widgets.gui` (`te_help_button`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_help_button_tt`, `te_help_link_tt`)
- Create: `test_te_help_pages.py`
- Create: `docs/testing/charts-help-national-info-playtest.md`

**Interfaces:**
- `type te_ui_help_popup = te_ui_popup` with `popup_size { size = { 640 820 } }`: the sections' 480–520 content, plus the window's margins (2 × 35), the list's (2 × 10) and a scrollbar. A page is `type te_<key>_help_popup = te_ui_help_popup`, filling `popup_visible` (`GetVariableSystem.HasValue('te_popup', 'help_<key>')`), `popup_title` (the section's header key) and `popup_list` (`te_<key>_help_body = {}`).
- `type te_help_button = button_icon_round`: 29 × 29, `parentanchor = right|vcenter`, `position = { -10 0 }`, `tooltip = "te_help_button_tt"`. Its icon is vanilla's `gfx/interface/buttons/button_icons/vickypedia.dds`, the button that opens vanilla's own encyclopedia, as a placeholder (style guide rule 10). An instance adds its `onclick`.
- The link: each `te_<key>_sec_how` keeps its system's section header, with `onclick = "[GetVariableSystem.Set('te_popup', 'help_<key>')]"`, both arrows (`onclick_showmore`, `onclick_showless`) set to `visible = no`, and `tooltip = "te_help_link_tt"`.
- Loc:
  - `te_help_button_tt`: "How this system works: the rules behind each figure and button."
  - `te_help_link_tt`: "Opens the Help page."

- [ ] **Step 1: Tests** (`test_te_help_pages.py`), over a `PAGES` table holding the H1 rows (H2 adds the rest):
  - `test_the_shells`: both types' shape and blocks.
  - `test_every_page_is_in_the_root`: each `te_<key>_help_popup = {}` once in `te_popups`.
  - `test_every_page_opens`: something sets `help_<key>` (the link at least), and nothing sets a key with no page.
  - `test_the_link_replaces_the_section`: each `te_<key>_sec_how` holds the header only, with the onclick and no flag.
  - `test_no_flag_is_left`: no `<flag>` of a moved section anywhere in `gui/`.
  - `test_the_body_reads_the_player`: no `JournalEntry.` in a help body's type closure or in the loc it reaches.
  - `test_each_header_has_its_button`: each frame body's `tab_header` holds `te_help_button` with its page's `onclick`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Write the two types and the loc.** Run `test_te_popups.py` and `check_gui_lint.py`. Expected: PASS for them.
- [ ] **Step 4: Create the play-test list** with spec § 9 item 1, for the Help popup:
  - it draws above the TE window in both widths, the vanilla side panels, the journal and the Census window;
  - Escape closes the popup and leaves the window under it open.

  The fallback: instance the pages at window level in each full-screen host.
- [ ] **Step 5: Commit.**

### Task H1.2: Banking, Grand Monuments and the Colonial Empire

The first three: the longest page (Banking, 18.6k characters, with its monetary gate), one with no reads, and one whose loc reads the entry.

**Files:**
- Modify: `banking_layout_widget.gui`, `grand_monuments_widget.gui`, `colonial_empire_widget.gui` (the link, the body, the popup); `gui/te_popups.gui` (the three popups); the three tab bodies' `tab_header` (Banking has two headers, both get the button)
- Modify: `localization/english/te_journal_entries_l_english.yml` (Colonial Empire's three keys, on `GetPlayer`)
- Modify: `test_banking_layout.py`, `test_grand_monuments_layout.py`, `test_colonial_empire_layout.py`, `test_banking_always_on.py` (`:372`)

- [ ] **Step 1: Point the tests at the new shape.** In each layout test:
  - `FlagTest`'s "How starts collapsed" becomes "How is a link" (the system's header, the `te_popup` key, no flag);
  - `HowItWorksTest` and Banking's `GateTest` (`:243`) read `te_<key>_help_body`;
  - `REFERENCE` and the wide tests keep `te_<key>_sec_how`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Move each section.** Cut the panel's children into `te_<key>_help_body` (a vertical flowcontainer, `spacing = 4`), and rewrite its reads to `GetPlayer`. Leave the header behind as the link, and add the popup.
- [ ] **Step 4: Run** the three layout tests, `test_te_help_pages.py`, `test_te_popups.py`, `test_te_system_tab_bodies.py`, `test_long_tooltip_audit.py`, `long_tooltip_audit.py --strict` and `check_gui_lint.py`. Expected: PASS. Commit.

### Task H1.3: docs and player guide

- [ ] **Style guide rule 1:** an explanation of how the system works lives on its Help page, opened by the link at the foot of the panel and the "?" in the tab's header. The rule's example becomes Banking's (`te_banking_sec_how` and `te_banking_help_body`); the UN's moves in H2.
- [ ] **`gui_modding_guide.md`** (CRLF), "This mod's popups": the help pages, `te_ui_help_popup`, how to add one. **`gui_tree.py`'s docstring** (`opens_how_section`): a moved section has no toggle; its names carry the token.
- [ ] **Icons:** `docs/systems/te_systems_window_gui_icons.md` gains the "?" placeholder, with the final art's subject ("a question mark on a parchment disc").
- [ ] **Player guide:**
  - `01-introduction.md`: the "?" and the Help pages, where it describes the panels;
  - `02-timeline.md:799`, `04-banking.md:265` and `:558`, `12-decolonization.md:101`: the table rows that say "Collapsed" now say the section opens the Help page.

  Rebuild the PDF. Commit and open the PR ("Player guide: 01, 02, 04, 12").

---

## PR H2: the other twelve pages

Branch `feat/te-help-pages-2`. Spec § 5.2. **After H1.**

One task per row of H1's table not yet moved, each the steps of H1.2: point the layout test at the link and the body, move the content, rewrite the reads to `GetPlayer`, add the popup and the button. Systems with their own work:
- **Budget Breakdown:** its loc is generated: edit `gen_budget_breakdown.py`, then rerun it. No header, so the link alone (`test_budget_breakdown.py:651`, `:662`).
- **Demographics:** one page for both sections. The state subtab's `te_state_demog_how` becomes a link to it. `test_demographics_layout.py`'s `HOW` and its `added_gates=("te_demog_sec_how",)` keep the section's name. `FlagTest.test_the_hosts_keep_their_own_flags` drops the How flags. The window body's header gets the button.
- **Nation:** no header, so the link alone (`test_nation_tab.py:426`, `:433`).
- **Tax Code:** one page with both texts. The two links keep their own gates (the Light one gates itself at `te_tax_light_widget.gui:280`; the full one sits under `Not(light)` wrappers at `te_tax_layout_widget.gui:215`, `:340`), and both open `help_tax_code`. Covers `FlagTest` (`:1051`, `:1054`, `:1072`) and `LayoutTest` (`:414`, `:418`).
- **The UN:** its nested `te_un_help_authority` and `te_un_help_standing` move with the content (`HowStyleTest`, `test_un_layout.py:538`).
- **The Space Race:**
  - one page;
  - `te_sr_sec_how_colonies` becomes a second link to it, still only on the `sr_tab = system` tab (`:9194`);
  - the milestones' generated headers (`gen_te_systems_window.py`'s `_milestone`) get the button, through the generator;
  - covers `ColoniesTest` (`:490`), `TabTest` and `test_te_systems_window.py`'s `TabContentTest` (`:797`).
- **Global Warming:** the Fossil Transition's How joins the page, and `rt_how_open` retires (`test_global_warming_layout.py:30`).

Then:
- [ ] **`test_te_help_pages.py`'s `PAGES`** holds all fifteen, and `test_every_system_with_a_tab_has_a_page` reads `gen.TABS`.
- [ ] **Player guide:** the rows and sentences in `01-introduction.md:146`, `03-economy.md:596` and `:647`, `05-tax-code.md:190`, `08-states.md:468`, `10-united-nations.md:1139`, `11-influence.md:54` and `:264`, `14-nuclear.md:42` and `:59`, `15-climate.md:151`, `:195` and `:237`, and `16-space.md:223`. Rebuild the PDF. Commit and open the PR ("Player guide: 01, 03, 05, 08, 10, 11, 14, 15, 16").

---

## PR C1: the chart registry and generator (no visible change)

Branch `feat/te-history-chart-registry`. Spec §§ 4.3, 7.4.

**The shape.** Each chart becomes two generated wrapper types, `te_hist_<id>` (today's size) and `te_hist_<id>_large` (the viewer's). Each is a plain `flowcontainer` holding one `te_history_chart` instance with its blockoverrides inline. That is the shape that draws today: every history section is a type holding its charts inline (gotcha #37 was a type derived from `te_history_plot`, which this is not). The sections stay hand-written and instance the small wrapper where the chart was, so the diagnostic of spec § 4.3 isn't needed.

**The 33 charts:**

| System | Charts | Where today | Kind |
|---|---|---|---|
| Banking | 8: `bank_value`, `bank_momentum`, `bank_bubble`, `mon_policy`, `mon_policy_digital`, `mon_rate_paid`, `mon_inflation`, `mon_fx` | `te_banking_history_charts` (`banking_history_widget.gui:174`) | monthly |
| Strategic Reserve | 8: `st_res_<good>` (grain, ammunition, oil, small_arms, artillery, aeroplanes, tanks, fertilizer) | each `te_st_res_good_row`'s `row_history` in `te_st_res_sec_inventory` (`strategic_reserve_widget.gui:1355`) | monthly |
| Demographics | 8: `demog_births_deaths`, `demog_migration`, `demog_e0`, `demog_tfr`, `demog_median`, `demog_causes`, `demog_gini`, `demog_wc` | `te_demog_sec_history` (`te_demographics_widgets.gui:3294`) | annual, with a pip lane |
| Cultural Hegemony | 1: `ch_models` | `te_ch_sec_history` (`cultural_hegemony_widget.gui:2413`) | annual, global |
| Nuclear Weapons | 2: `nd_taboo`, `nd_taboo_tgt` | `te_nuclear_sec_taboo` (`nuclear_program_widget.gui:373`) | monthly |
| United Nations | 2: `un_auth`, `un_target` | `te_un_sec_auth_history` (`un_authority_widget.gui:813`) | monthly |
| Global Warming | 2: `gw_temp`, `gw_share` | `te_gw_sec_history` (`global_warming_widget.gui:1580`) | monthly |
| Colonial Empire | 2: `ce_stability`, `ce_drift` | `te_ce_sec_history` (`colonial_empire_widget.gui:2612`) | monthly |

**The sizes** (`SMALL` is today's; `LARGE` is owner call 7):

| | Monthly, small | Monthly, large | Annual, small | Annual, large |
|---|---|---|---|---|
| Plot | 480 | 1200 | 400, plus 48 for the axis labels | 1200, plus 48 |
| Frame (`plot_size`) | 496 × 96 | 1216 × 348 | 456 × 180 (Cultural Hegemony), 456 × 132 (Demographics: a 96 box and a 36 pip lane) | 1256 × 348, 1256 × 384 |
| Bars per range | 40 / 8 / 2 × 84 | 100 / 20 / 5 × 336 | 80 / 20 / 4 × 168 (CH), × 84 (Demographics) | 240 / 60 / 12 × 336 |
| Title and legend | 484 | 1204 | 484 | 1244 |
| Empty state | 420 | 1000 | 420 | 1000 |
| Hand-placed zero lines | `{ 0 -23 }`, `{ 0 -27 }` (`banking_history_widget.gui:451`, `:585`: 6 + 0.2 × 84, 6 + 0.25 × 84) | `{ 0 -73 }`, `{ 0 -90 }` | — | — |

The others sit at `vcenter` and need nothing. **Thin caps** are in axis units, not pixels (`banking_history_widget.gui:354`, `:359`: a floor of 2 and a cap of 4 out of 100), so the large size divides each by the height ratio, or the cap would draw 13 px tall.

### Task C1.1: size blocks on the chart type

**Files:**
- Modify: `gui/journal_entry_widgets/te_history_chart.gui` (`te_history_chart`)
- Create: `test_te_history_charts.py`

**Interfaces:**
- Produces `te_history_chart` blocks `chart_text_width` (default `max_width = 484`, on the title and the legend) and `empty_width` (default `max_width = 420`). `plot_size`, `plot_layouts` and the plot's `bar_size` are blocks already.

- [ ] **Step 1: Test** (`ChartTypeTest`): both new blocks, their defaults today's literals, and no other literal width left in the type.
- [ ] **Step 2: Write them.** Run the test, `test_demographics_layout.py` (`WidthTest` reads the title's `max_width`: point its regex at the block) and `check_gui_lint.py`. Expected: PASS. Commit.

### Task C1.2: the registry and generator

**Files:**
- Create: `scripts/generators/gen_te_history_charts.py`
- Create: `scripts/generators/te_history_charts/<system>.gui.in` (one fragment file per system: each chart's instance text, cut from its section)
- Create (generated): `gui/te_history_charts_generated.gui`
- Modify: `docs/auto_generated_files.md` (a "History charts (explicit regeneration)" section), `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS`; the fragments under `INTENTIONALLY_NOT_EXCLUDED`), `docs/guides/gui_modding_guide.md` (a row in "This Mod's GUI Files" and the count, 52)

**Interfaces:**
- `CHARTS: list[Chart]`. A `Chart` has:
  - `id`, `system`, `kind` (`monthly`, `annual`, `annual_pips`);
  - `fragment`: its name in the system's fragment file;
  - `params`: names the fragment substitutes (the Reserve's eight share one fragment, `${good}`);
  - `entry`: the journal entry its viewer reads (`je_banking_cycle`, …; `None` for Demographics, which reads `Country`);
  - `gate`: the viewer's scope-free gate (the tab's scripted GUI);
  - `range`: its range variable (`te_hist_range`, `ch_model_hist_range`, `te_demog_hist_range`).
- **A fragment is the instance's text as it stands today**, with each size a placeholder: `${frame}`, `${bars_<range>}`, `${bar_h}`, `${text_w}`, `${empty_w}`, `${zero_y}`, and `${thin:<value>}` for a thickness in axis units. No GUI file in these systems holds a `$`, so `string.Template`-style names can't collide.
- The generated file holds `te_hist_<id>` and `te_hist_<id>_large` for every chart. `main(argv)` writes it; `--check` exits 1 if it is stale.

- [ ] **Step 1: Cut the fragments mechanically.** A one-off script in the scratchpad copies each of the 33 instances, byte for byte, into its system's fragment file, then replaces each size literal with its placeholder. Keep the script's output diff in the PR description, not the script.
- [ ] **Step 2: Tests** (`RegistryTest`):
  - `test_the_small_size_is_todays`: `SMALL` holds today's literals (496 × 96, 84, 40 / 8 / 2, 484, 420, the zero lines' 23 and 27), so rendering a chart at `SMALL` gives back today's instance. Step 1's script checks that once, byte for byte, before the instances are cut.
  - `test_no_size_literal_in_a_fragment`: no number left in a fragment's `size`, `position`, `max_width` or `plot_size`, and no thin cap or floor outside `${thin:…}`.
  - `test_the_bars_fill_the_plot`: for every kind and size, bars × samples = plot width for each range.
  - `test_the_large_caps_scale`: every `${thin:x}` renders x at small and x × small height / large height at large.
  - `test_generated_file_is_current`.
- [ ] **Step 3: Write the generator** on `gen_te_systems_window.py`'s pattern: a BOM, the `AUTO-GENERATED` header, kept out of `POST_LOAD_REGENERATORS`. Run it and the tests. Expected: PASS.
- [ ] **Step 4: Register the file.** Run `test_nightly_audit_select.py` and `test_tax_code_bypass.py`. Expected: PASS. Commit.

### Task C1.3: the sections instance the wrappers

**Files:**
- Modify: the eight section files above
- Modify: the tests that read charts inline (point each at the generated wrapper, or at the registry):
  - `test_history_chart_tooltip_context.py` (its glob, `:87`, covers only `gui/journal_entry_widgets/`: add the generated file);
  - `test_cultural_hegemony_history.py` (`:248`, `:279`);
  - `test_demographics_layout.py` (`HistoryTest`, `FontTest`, `WidthTest`, `PieTest`);
  - `test_demographics_life_tail.py` (`:196`), `test_demographics_census_window.py` (`:394`);
  - `test_strategic_reserve_layout.py` (`HistoryTest`), `test_nuclear_taboo.py` (`:794`), `test_banking_layout.py`, `test_banking_tool_roster.py`.
- Modify: `.claude/skills/add-strategic-reserve-good/references/per_good_templates.md` (`:707`: a new good is a registry line, not an inline chart)

- [ ] **Step 1: Replace each instance** with its wrapper, keeping the instance's own `visible` on the wrapper's instance: `te_hist_mon_policy_digital = { visible = "[…banking_mon_is_digital…]" }`. The section keeps its range buttons, its "since" line and its pip legend.
- [ ] **Step 2: Rewrite the tests** to read the wrapper bodies. Each keeps its assertion; only where it reads changes.
- [ ] **Step 3: Run** every test above, `test_te_history_charts.py` (`test_every_chart_is_generated`: no `te_history_chart = {` left in a hand-written file) and `check_gui_lint.py`. Expected: PASS. Commit.

### Task C1.4: docs and PR

- [ ] `docs/systems/mod_systems/history_charts.md`: the registry, the two sizes, how to add a chart (a fragment, a `Chart` line, the generator). Fix its four stale lines while there:
  - `:20`, three banking charts on `custom_widget_container_2`: eight, on container 3;
  - `:62`, an `hbox` with expanding items: a flowcontainer of fixed widths;
  - `:70`, "Collapsed by default": the charts open by default;
  - `:86`, 120 containers: the cap is 240.
- [ ] Open the PR with "Player guide: no player-facing change".

---

## PR C2: the chart viewer

Branch `feat/te-history-chart-viewer`. Spec §§ 4.2, 4.4. **After C1.**

### Task C2.1: the open button

**Files:**
- Modify: `gui/journal_entry_widgets/te_history_chart.gui` (the title row; the type `te_chart_open_button`), `scripts/generators/gen_te_history_charts.py`, `test_te_history_charts.py`, `test_demographics_layout.py` (`WidthTest`)
- Modify: `docs/systems/te_systems_window_gui_icons.md` (the placeholder)

**Interfaces:**
- The title textbox and a new `block "chart_open" {}` share a horizontal flowcontainer; the legend stays below at the full width.
- `type te_chart_open_button = button_icon_round`: 24 × 24, `tooltip = "te_chart_open_tt"`, a placeholder icon, vanilla's `gfx/interface/buttons/button_icons/areacharts.dds` (style guide rule 10), listed in the icons doc with the final art's subject ("two arrows pointing out from a corner").
- The small wrapper fills `chart_open` with the button, `onclick = "[GetVariableSystem.Set('te_popup', 'chart_<id>')]"`, and its title width is 456 (484 less the button and its gap). The large wrapper leaves both at their defaults.

- [ ] **Step 1: Tests:** every small wrapper's button and key; no large wrapper has one; `WidthTest` checks the eight Demographics titles at 456.
- [ ] **Step 2: Write it,** regenerate, run the tests. Expected: PASS. Commit.

### Task C2.2: the viewer popups

**Files:**
- Modify: `scripts/generators/gen_te_history_charts.py`, `gui/te_history_charts_generated.gui` (regenerated), `gui/te_popups.gui` (instances `te_chart_popups`), `test_te_popups.py`, `test_te_history_charts.py`
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_chart_open_tt`: "See this chart at full size."; `te_chart_gone`: "This chart's system is no longer running.")

**Interfaces:**
- The generator writes `type te_chart_popups = widget { size = { 100% 100% } … }`, holding one `te_chart_<id>_popup = te_ui_popup` per chart:
  - `popup_visible`: `GetVariableSystem.HasValue('te_popup', 'chart_<id>')`;
  - `popup_title`: the chart's title key;
  - `popup_size`: the large frame plus the window's margins (2 × 35), the list's (2 × 10) and a scrollbar: 1320 monthly, 1360 annual, by about 600 tall;
  - `popup_list`: a flowcontainer `datacontext = "[GetPlayer]"`, then one `visible` on the chart's `gate`, then one `datacontext = "[GetPlayerJournalEntry('<entry>')]"` where the chart has an entry (gotcha #29), holding the range row and `te_hist_<id>_large = {}`, then the section's pip legend where it has one (Banking's `te_history_marker_legend`, `banking_history_widget.gui:236`; Demographics', `te_demographics_widgets.gui:3367`).
- **The range row:** the generator writes `te_chart_range_row_<range>`, the three `te_history_range_button`s the sections use for that variable, so the viewer and the panel share one range.
- An entry that closes under an open viewer leaves one line (`te_chart_gone`), as the Space Race's popups do.

- [ ] **Step 1: Tests:**
  - `test_te_popups.py`: `te_chart_popups = {}` is in the root once; every chart popup derives from the shell; the gate on a parent of the entry's datacontext.
  - `test_te_history_charts.py`: one popup per chart; the range rows set the same variable and values as the sections' buttons.
- [ ] **Step 2: Write it,** regenerate, run the tests, `check_gui_lint.py` and `loc_coverage_audit.py --strict`. Expected: PASS. Commit.

### Task C2.3: docs, play-test, player guide

- [ ] `history_charts.md`: the viewer. `gui_modding_guide.md`'s popups section (CRLF): the chart popups.
- [ ] **Play-test** (spec § 9, items 1 and 2): the viewer above each host in both widths; bars 5, 20 and 100 px, each hovering; the two zero lines at 0; the popup fits 1600 × 900 at UI scale 1; Escape closes it and leaves the window open.
- [ ] **Player guide:** `01-introduction.md` gains a sentence on the chart button, where the guide first describes the charts. Rebuild the PDF. Commit and open the PR ("Player guide: 01-introduction").

---

## PR F0: every mount supplies a Country (no visible change)

Branch `feat/te-country-binding`. Spec §§ 6.3, 6.5, 7.1, 7.2.

### Task F0.1: the guard and the shared test helpers

**Files:**
- Modify: `gui/te_system_tab_widgets.gui` (the template `te_own_country_only`, before `types te_system_tab_widgets`, with a header-comment entry)
- Modify: `gui_test_helpers.py` (move in `load_loc`, `gui_keys`, `loc_closure` and `type_bodies` from `test_demographics_census_window.py`; add `type_closure`)
- Modify: `test_demographics_census_window.py` (import them)

**Interfaces:**
- Produces: `template te_own_country_only { visible = "[Country.IsLocalPlayer]" }`.
- Produces: `gui_test_helpers.type_closure(names, types) -> set[str]`: every mod type the named types instance, transitively (`te_*` children and blockoverride contents), given a dict of type bodies from every `.gui` file.

- [ ] **Step 1: Move the helpers.** Run `test_demographics_census_window.py`. Expected: PASS, unchanged.
- [ ] **Step 2: Test `type_closure`** in a new `GuardTemplateTest` in `test_te_system_tab_bodies.py`:
  - the template's text;
  - `type_closure({"te_gm_wide_sections"})` holds `te_gm_sec_commission` and `te_gm_overview_panel` and no `te_ce_*` type.
- [ ] **Step 3: Write both.** Run the test. Expected: PASS. Commit.

### Task F0.2: the mounts supply the player's Country

**Files:**
- Modify: `gui/te_system_tab_widgets.gui` (`te_system_tab_frame`: `block "tab_country" { datacontext = "[GetPlayer]" }` on its root, and the type `te_je_country`)
- Modify: `scripts/generators/gen_te_systems_window.py` (`_mount`: `datacontext = "[GetPlayer]"` on every mount), `gui/te_systems_window_generated.gui` (regenerated)
- Modify: every system's journal roots, the private systems' included, since F0.3 moves the shared chart type onto `Country` and Global Warming, the UN and the Strategic Reserve draw charts in their entries: `banking_layout_widget.gui`, `te_tax_layout_widget.gui`, `grand_monuments_widget.gui`, `colonial_empire_widget.gui`, `cultural_hegemony_widget.gui`, `nuclear_layout_widget.gui`, `space_race_widget.gui`, `global_warming_widget.gui`, `un_layout_widget.gui`, `strategic_reserve_widget.gui`, `covert_operations_widget.gui`
- Modify: `test_te_system_tab_bodies.py` (`MountContextTest`)

**Interfaces:**
- Produces: `type te_je_country = flowcontainer { datacontext = "[JournalEntry.GetCountry]" parentanchor = hcenter direction = vertical ignoreinvisible = yes }`. A journal root wraps its composer in it, on a child, so the root's own `visible = "[JournalEntry.IsActive]"` keeps reading the entry.
- `Country` then resolves to the player in every host, as it already does in the Population panel (`AccessPlayer`) and the Census window (`PopBrowserPanel.GetCountry`).

- [ ] **Step 1: Test first.** `MountContextTest`:
  - `test_the_frame_supplies_the_player`: the frame's root holds `block "tab_country" { datacontext = "[GetPlayer]" }` before `tab_header`.
  - `test_every_window_mount_supplies_the_player`: every generated mount carries `datacontext = "[GetPlayer]"`.
  - `test_every_journal_root_supplies_its_country`: every `widget_je_*` root in `gui/journal_entry_widgets/` holds its composer inside `te_je_country = {`.
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Write it.** The Seabed has no journal entry; Nation and Budget Breakdown have no frame, so their mount's datacontext is the one they get. Demographics' window body sets `datacontext = "[GetPlayer]"` already (`te_demog_window_body`'s `tab_entry`).
- [ ] **Step 4: Run** `test_te_system_tab_bodies.py`, `test_te_systems_window.py`, every `test_*_layout.py` and `check_gui_lint.py`. Expected: PASS. Commit.

### Task F0.3: the charts and the gates take the shown country

**Files:**
- Modify: `gui/journal_entry_widgets/te_history_chart.gui` (three defaults that read the entry: `sample_datamodel` `:253`, `sample_visible` `:270`, `empty_visible` `:423`)
- Modify: `scripts/generators/gen_te_systems_window.py` (the root as a parameter)

The sections' own reads around their charts stay for their system's PR: Banking's "since" line and pip legend (`banking_history_widget.gui:224`, `:237`) and the four gates on its charts (`:397`, `:440`, `:574`, `:637`) are F2's.

- [ ] **Step 1: The chart reads** become `Country`:
  - `sample_datamodel` and `empty_visible`: `Country.MakeScope.GetList('te_hist')`;
  - `sample_visible` reads `te_history_month_index`, the same for every country: `GetPlayer` on a `# world:` line, as Demographics' charts already read the year.

  Every chart host now has a `Country` (F0.2; C2's popups set `GetPlayer` above their entry). Regenerate, then run `test_te_history_charts.py` and the history tests. Expected: PASS.
- [ ] **Step 2: The gates' root.** `_root`, `shown`, `valid` and `valid_tooltip` take `root: str = PLAYER_ROOT` (`"GetPlayer.MakeScope"`), and the renderers pass it through. The window renders exactly as before: `--check` exits 0 with no diff. F1 passes `COUNTRY_ROOT` (`"Country.MakeScope"`).
- [ ] **Step 3: Commit.**

### Task F0.4: the binding and guard tests

**Files:**
- Modify: `scripts/generators/gen_te_systems_window.py` (`Tab.public: bool = False`; `True` for Demographics only)
- Modify: `test_te_system_tab_bodies.py` (`BindingTest`, `GuardTest`)

**Interfaces:**
- `PUBLIC = [t for t in gen.TABS if t.public]`; each test runs over `type_closure({t.wide})` of each, and the loc closure of the keys they name.
- `UNBOUND`: the systems § 6.4 shows that are not yet bound (every one but Demographics). A system on it is skipped; one that passes while still on it fails `test_unbound_is_honest`, so the list only shrinks.
- **A world read** (spec § 6.7) is marked on its own line, `# world: <why>`, in GUI, and listed in `WORLD_LOC = {key: why}` for loc. Demographics' kept reads (`te_history_current_year`, `te_demog_fam_rule`) move to these markers.

- [ ] **Step 1: The tests.**
  - `BindingTest.test_no_entry_or_player_read`: in each public closure, no `JournalEntry.` and no `GetPlayer`/`AccessPlayer` outside a `te_own_country_only` subtree or a `# world:` line; the same for the loc closure, less `WORLD_LOC`.
  - `GuardTest.test_every_control_is_the_players`: every `Execute` (a scripted GUI's, in an `onclick`) sits in a `te_own_country_only` subtree. So does a popup opener whose popup holds controls (the Space Race's pickers). The "?", the Help links and the chart buttons don't: what they open only reads.
  - `test_unbound_is_honest`.
  - `test_the_text_is_not_the_players`: no "our", "your", "we" or "you" in a public loc closure, outside a `SelectLocalization` branch on `Country.IsLocalPlayer` (the census test's `PERSONAL` rule, moved here).
- [ ] **Step 2: Run them.** Expected: PASS for Demographics. Then commit.

### Task F0.5: the rebinding tool

**Files:**
- Create: `scripts/analysis/te_rebind_country.py`, `test_te_rebind_country.py`
- Modify: `docs/guides/python_tools.md` (one entry)

**Interfaces:**
- `te_rebind_country.py <tab key>` reads the tab's wide composer from the registry, takes its type closure and loc closure, and prints each read by class:
  - **mechanical:** `JournalEntry.GetCountry.` → `Country.`, and `GetPlayer.` → `Country.`;
  - **entry-only:** `JournalEntry.IsActive`, `te_je_scripted_bars`, `JournalEntry.GetGoalProgress…`, the Open Journal Entry button;
  - **shared with the entry's own text:** a loc key that the entry's `status_desc`, `desc` or a `scripted_progress_bar` also renders, where only `JournalEntry` is in context. These are split, not rewritten.
- `--write` rewrites the mechanical class only, inside the closure's type bodies and loc keys, and leaves every other file alone.

- [ ] **Step 1: Test** on a fixture of two types and three keys: the mechanical rewrite, an entry-only read reported and untouched, a key shared with a `status_desc` reported and untouched.
- [ ] **Step 2: Write the tool.** Run the test. Expected: PASS.
- [ ] **Step 3: Docs and PR.** `docs/guides/gui_modding_guide.md` (CRLF): gotcha #45 gains a line on `te_own_country_only`, `te_je_country` and the tool. Open the PR with "Player guide: no player-facing change".

---

## PR F1: National Info

Branch `feat/te-national-info`. Spec §§ 6.1, 6.2, 6.6, 7.3. **After F0 and C2.**

### Task F1.1: the generator writes National Info

**Files:**
- Modify: `scripts/generators/gen_te_systems_window.py`
- Create (generated): `gui/te_national_info_generated.gui`
- Create: `test_national_info.py`
- Modify: `docs/auto_generated_files.md` (the file's row, in the "Timeline Extended window" section), `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS`), `docs/guides/gui_modding_guide.md` (a row in "This Mod's GUI Files" and the count)

**Interfaces:**
- `NI_STORED = "te_ni_tab"`, `NI_FALLBACK = "pops"`, `NI_ORDER`: Pops, Demographics, Nation, Banking, Tax Code, then Grand Monuments, Colonial Empire, Seabed, Cultural Hegemony, the Space Race, then Nuclear Weapons. A tab is in National Info while its registry entry is `public`; F1 ships Pops and Demographics.
- The generated file:
  - **Templates** `te_ni_<key>_selected` / `_unselected`, and `te_ni_pops_selected`, by the window's rule (the last tab chosen while it is open, else Pops), every gate rooted on `Country.MakeScope`.
  - **`te_ni_strips`:** an hbox, `expand`, one vanilla `tab_buttons` per five tabs at 540 (the wide frame's `WIDE_STRIP`), `expand`. A tab's `enabled` is its open gate for the window's country.
  - **Tooltips:** open, `SelectLocalization( Country.IsLocalPlayer, '<tab tooltip>', 'te_ni_tab_other_tt' )`. Grayed, the window's checklist for the player, `te_ni_tab_not_running_tt` for another.
  - **`te_ni_tabs`:** per tab, one flowcontainer `using = te_ni_<key>_selected`, holding two mounts:
    - **the player's:** `visible = "[Country.IsLocalPlayer]"`, holding the window's wide mount (the body with its layout override, so its gate, its entry and its controls);
    - **another country's:** `visible = "[Not( Country.IsLocalPlayer )]"`, holding the tab's header (its label and its "?"), then `<wide> = {}` under the window's own `Country`, with no journal entry.
- The Census window's strip shows whenever a public tab other than Pops could: `or_all` of their strip gates, or always once one of them has none (Nation, F2).

- [ ] **Step 1: The tests** (`test_national_info.py`):
  - `SelectionTest`: the window's evaluator, rebuilt over `NI_ORDER`'s public tabs, Pops the fallback.
  - `StripTest`: strips of five, in `NI_ORDER`; every gate reads `Country.MakeScope`, none `GetPlayer`.
  - `MountTest`: each tab's two mounts, as above; the foreign mount holds no `GetPlayerJournalEntry` and no frame.
  - `test_generated_file_is_current`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Refactor the selection renderers** to take a window (`stored`, `root`, `tabs`, `fallback`), so `selected`, `unselected`, `_any_system_shown` and `_tooltip` serve both windows. `te_systems_window_generated.gui` stays byte for byte (`--check`).
- [ ] **Step 4: Write the National Info renderers** and `render_ni()`. `main` writes both files; `--check` checks both.
- [ ] **Step 5: Register the file.** Run the tests, `test_nightly_audit_select.py` and `test_tax_code_bypass.py`. Expected: PASS. Commit.

### Task F1.2: the Census window instances them

**Files:**
- Modify: `gui/pop_browser_panel.gui`, `test_demographics_census_window.py`

- [ ] **Step 1: Point the tests at the new blocks.**
  - `MOD_OPEN` becomes `### MOD: National Info`; `OverrideTest` keeps holding the override to vanilla's file outside those blocks.
  - `FLAG` becomes `te_ni_tab` with the value `demographics`; `StripTest` reads the generated strip.
  - `test_the_window_keeps_its_country` is unchanged.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Rewrite the mod blocks.**
  - The header comment names National Info and the generator.
  - The strip's hbox holds `te_ni_strips = {}` and the generated gate.
  - Vanilla's two pops hboxes carry `using = te_ni_pops_selected` in place of the hand-written `Not( And( … ) )`.
  - The census scroll area becomes `te_ni_content` (`visible = "[Not( <te_ni_pops_selected's expression> )]"`, the generator also writes it as `te_ni_content_shown`), holding `te_ni_tabs = {}`.
  - The `_show` state gains `on_start = "[GetVariableSystem.Clear('te_ni_chart')]"`, so a viewer left open never reopens with the window (the Colonial Empire's self-check uses `on_start` with `GetVariableSystem`).
  - `te_pop_browser_demog` retires. `grep -rn te_pop_browser_demog` finds nothing outside `docs/` history.
- [ ] **Step 4: Run** `test_demographics_census_window.py`, `test_national_info.py`, `test_demographics_layout.py` and `check_gui_lint.py`. Expected: PASS. Commit.

### Task F1.3: the name and its loc

**Files:**
- Modify: `localization/english/replace/timeline_extended_override_l_english.yml`, `localization/english/te_miscellaneous_l_english.yml`

- [ ] **Step 1: The rename.** `POP_BROWSER:0 "[AddLocalizationIf(Not(Country.IsLocalPlayer), Concatenate(Country.GetAdjective, ' '))]National Info"`, vanilla's splice kept, under a comment naming the spec. It renames the window's title, the Population panel's button and the Politics tab's.
- [ ] **Step 2: The new keys:**
  - `te_ni_tab_other_tt`: "#b $<label>$#!\nWhat [Country.GetName] shows the world: its figures, without its controls." (one per tab through the label, or one key with the tab named in a splice; whichever `loc_coverage_audit` reads more simply);
  - `te_ni_tab_not_running_tt`: "Not running in [Country.GetName]."
  - `te_pop_browser_tab_pops` stays "Pops".
- [ ] **Step 3:** `organize_loc.py`, `loc_coverage_audit.py --strict`, `check_loc_spelling.py --check`. Commit.

### Task F1.4: the foreign chart viewer

**Files:**
- Modify: `scripts/generators/gen_te_history_charts.py`, `gui/te_history_charts_generated.gui` (regenerated), `gui/te_widget_library.gui` (`te_ui_popup`'s close as a block), `gui/pop_browser_panel.gui` (the viewer at window level), `test_te_history_charts.py`, `test_te_popups.py`

**Interfaces:**
- `te_ui_popup` gains `block "popup_close" { onclick = "[GetVariableSystem.Clear('te_popup')]" }` in both close buttons, the default unchanged.
- The generator writes `te_ni_chart_viewers`: one `te_ui_popup` per chart, `popup_visible` on `GetVariableSystem.HasValue('te_ni_chart', '<id>')`, `popup_close` clearing `te_ni_chart`, the large chart under the window's `Country`. National Info instances it once, at the end of the window type, outside the scroll area, inside a `### MOD: National Info` block.
- The open button becomes two in one slot: `visible = "[Country.IsLocalPlayer]"` sets `te_popup`, the other sets `te_ni_chart`. Outside National Info `Country` is always the player, so only the first ever shows.

- [ ] **Step 1: Tests:** every chart has a foreign viewer; the two buttons; the default close unchanged (`test_te_popups.py`).
- [ ] **Step 2: Write it,** regenerate, run the tests. Expected: PASS. Commit.

### Task F1.5: history for another country

**Files:**
- Modify: `common/on_actions/te_old_save_repairs.txt` (an `# OLD-SAVE REPAIR` block), `scripts/analysis/check_save_history_order.py`, `test_check_save_history_order.py`, `test_old_save_repairs.py`, `docs/systems/mod_systems/history_charts.md`
- Modify: `common/scripted_guis/` (`te_history_tracked_sgui`, from Demographics' `te_demog_hist_tracked_sgui`), the chart type's empty state, `test_te_history_charts.py`

**What is out of order.** A store that stops recording is already sorted: every eviction re-sorts (`te_history_prune_samples` calls `te_history_sort_samples`, `common/scripted_effects/te_history_effects.txt:109`, `:125`). The only stores out of order are ones scrambled before that sort existed and never touched since (`history_charts.md:43`). A foreign view makes them reachable for the first time.

- [ ] **Step 1: The repair.** An `# OLD-SAVE REPAIR` block on the monthly pulse list (`te_old_save_repairs.txt:13`, its conventions at `:1–11`): `every_country` with `has_variable_list = te_hist` runs `te_history_sort_samples = yes` once, then sets a done flag.
  - It is safe for every country: a list under the cap can't be out of order (`te_history_effects.txt:41–49`), and the sort's own gate (`:172`) never clears a short list.
  - The flag only saves the 2 × 240 iterations a month.
- [ ] **Step 2: The checker.** `check_save_history_order.py` fails on a `frozen` store out of order (`:169–173`) instead of labeling it, and scans `te_dg_hist` too (`:60`). Its tests change to match.
- [ ] **Step 3: The empty state.** The chart type's empty text becomes `SelectLocalization( <te_history_tracked_sgui on Country>, '<empty>', 'te_history_untracked' )`, "No history is kept below major power". Demographics' charts already say this (`te_demog_hist_untracked`), and move onto the shared key and gate.
  - It shows only for an empty list, so a former major power's last recorded years still draw.
- [ ] **Step 4: Tests:**
  - the repair's block and its flag (`test_old_save_repairs.py`'s markers);
  - the checker on a frozen out-of-order store and on `te_dg_hist`;
  - the empty state's two branches, and Demographics on the shared gate.

  Run them. Expected: PASS. Commit.

### Task F1.6: docs, play-test, player guide

- [ ] **Docs:**
  - `gui_modding_guide.md` (CRLF): the National Info window, under "This mod's popups" and the window section;
  - `docs/systems/mod_systems/state_and_nation_panels.md`: National Info's tabs and how a system joins (one `public` flag, after its binding PR);
  - the style guide's rule 9: National Info is the second window with more than one strip.
- [ ] **Play-test list** (spec § 9, items 3, 5, 6 and 7, for Pops and Demographics).
- [ ] **Player guide:**
  - `01-introduction.md`: National Info, opened from a country's Politics tab or the Population panel;
  - `08-states.md`: the Census Data window's new name.

  Rebuild the PDF. Commit and open the PR ("Player guide: 01-introduction, 08-states").

---

## PRs F2–F5: each public system

Each system in one task, the same steps; a PR holds the systems in its row of the table below, and the four PRs run in parallel once F1 has merged.

- [ ] **Step 1: Make it public.** Set the tab's `public = True`, take it off `UNBOUND`, regenerate. Run `BindingTest`, `GuardTest` and `test_national_info.py`. Expected: FAIL, listing the reads and controls to fix.
- [ ] **Step 2: Bind.** Run `scripts/analysis/te_rebind_country.py <key>`, then `--write` for the mechanical reads. Fix the rest by hand:
  - **Entry-only gates:** a composer's `JournalEntry.IsActive` becomes the tab's own gate rooted on `Country` (`GetScriptedGui('<tab sgui>').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )`, which tests `has_journal_entry` for any country).
  - **Entry-only parts** go under `te_own_country_only`, or read the variable behind them (the table's notes).
  - **Keys shared with the entry's own text** are split: a `_ni` copy for the panel, the entry's left as it is.
  - **Generated rows** change in their generator.
- [ ] **Step 3: Guard and hide.** Every control under `te_own_country_only`, on a wrapper where the widget has its own `visible`. The private parts (spec § 6.4's Hidden column) too.
- [ ] **Step 4: World lists** (spec § 6.7). A list written only for players that describes the world reads the player's copy on a `# world:` line; a viewer-relative one is hidden for another country.
- [ ] **Step 5: Wording** (spec § 6.8). Labels go neutral; a sentence that needs its subject takes `SelectLocalization( Country.IsLocalPlayer, … )`.
- [ ] **Step 6: `PrivateTest`** in the system's layout test: each Hidden item from the table sits under `te_own_country_only`.
- [ ] **Step 7: Run** `test_te_system_tab_bodies.py`, `test_national_info.py`, `test_te_systems_window.py`, the system's layout and widget tests, the generator's `--check`, `check_gui_lint.py` and the loc audits. Expected: PASS. Commit.
- [ ] **Step 8: Play-test items** (spec § 9, item 3, for this system) and **the player guide:** a line in the system's chapter on what another country's National Info shows.

| PR | System (key) | Reads to bind (spec § 6.3) | Its own work |
|---|---|---|---|
| F2 | Nation (`nation`) | 31 + 142 generated `GetPlayer` | The modifier list reads `Country.GetTimedModifiers` (`te_nation_tab.gui:164`), in `gen_nation_tab.py`. The UN lines: membership, standing and dues arrears, from `un_standing` and the `<modifier>_on` mirrors (`un_state_effects.txt:71–83`), as rows in `gen_nation_tab.py`'s registry. The Information tab's goto (`te_nation_panel_line`, `gen_nation_tab.py:846`): for another country, `InformationPanelBar.OpenPopBrowserPanel( Country.Self )` and `te_ni_tab = nation`, with its own tooltip. The tab's lasting modifiers, which the country panel hides for another country today: the strip shows them (owner call 4) |
| F2 | Banking (`banking`) | 303 entry, 17 player; 72 "you" keys | The bloc-leader row (`banking_dashboard_widget.gui:2793`): its `visible` and loc key read the panel's country, so they read the shown `Country` from a block outside the row's datacontext. The four bars from their country variables. The interventions from `market_triggers.txt`'s `je:` triggers. Every Monetary Policy control guarded; the readout for a country with no entry stays |
| F2 | Tax Code (`tax_code`) | about 560 hand-written and 3,500 generated `GetPlayer` (`gen_tax_code.py`) | The interest-group cards iterate `AccessPlayer.AccessAllInterestGroups`: `Country.AccessAllInterestGroups` needs a non-const country (gotcha #35's `requires non const promote`), so check `error.log` once; the fallback hides the cards for another country. Hidden: the draft (`te_tax_dr_*`), the offers and promises (`te_tax_off_*`), the workbench, the bargaining |
| F3 | Grand Monuments (`grand_monuments`) | 149 entry, 35 player; 145 entry keys | Hidden: the open opportunity, the interest groups' ledgers |
| F3 | Colonial Empire (`colonial_empire`) | 142 entry, 8 player; 40 entry keys | The stability bar reads `colonial_empire_live_bar` through `je:`. World lists: the blocs, subject capitals and great-power rows (`colonial_empire_display_effects.txt:213`) |
| F3 | Seabed (`seabed`) | 111 player | The claimant rankings are a world list; the own row's `flag_context` is already a block |
| F4 | Cultural Hegemony (`cultural_hegemony`) | 155 entry, 3 player; 56 entry keys | The programs from `je:` reads. World lists: the leader flags and the board (`cultural_hegemony_effects.txt:43`, `:1029`). The models stay one world |
| F4 | Nuclear Weapons (`nuclear_weapons`) | 272 entry, 5 player; 97 entry keys | Another country sees the public estimate (`nd_believed_stockpile`, `nd_display_public_estimate`), crises and guarantees, and nothing before its first test. Hidden: the true stockpile, progress, funding, readiness, custody. The goal bar is the player's |
| F5 | Space Race (`space_race`) | 363 entry and 17 player hand-written; about 22,000 entry reads and 4,800 controls in the generated site and fleet rows (`gen_solar_sites.py`, `gen_space_fleets.py`); 417 entry keys | Another country sees the milestones reached, program icons, colonies, and a progress band from `sr_fuzz_<m>` (`space_race_display_values.txt:881`), as the Rivals rows show. Hidden: exact progress, funding, approach, setbacks, fleets. The rival estimates and powers list are viewer-relative: hidden for another country. Each milestone frame's entry: the foreign mount reads its milestone gate on `Country` |

The Space Race is a PR of its own: its two generators hold most of the reads, and its milestones are nine frames, not one.

## Self-review against the spec

- **Coverage:**
  - § 4.2 → C2.2; § 4.3 → C1; § 4.4 → C2.2 (the player's charts), F1.4 (another country's);
  - § 5.2 → H1, H2;
  - §§ 6.1, 6.2 → F1.1–F1.3; § 6.3 → F0.2, F0.5, F2–F5; § 6.4 → F2–F5; § 6.5 → F0.1, F0.4; § 6.6 → F1.5; § 6.7 → F2–F5 Step 4; § 6.8 → F2–F5 Step 5;
  - § 7.1 → F0.4; § 7.2 → F0.1; § 7.3 → F1.1; § 7.4 → C1; § 7.5 → H1, H2; § 7.6 → F1.5;
  - § 8 → each task's tests and docs; § 9 → each PR's play-test items; § 10 → Global Constraints' order.
- **Where this plan departs from the spec,** each found while writing it. The spec is updated to match:
  - **The charts are wrapper types,** not whole generated sections (§ 4.3). A wrapper holding the chart inline is the shape that already draws, so § 4.3's diagnostic isn't needed, and the sections stay hand-written.
  - **Each "How X Works" section stays in place as a link** to its page (§ 5.2). The composers, the wide layouts and their order tests need no change. The journal entry gets the link where the section was, and the state subtab and the headerless tabs (Nation, Budget Breakdown) too. The "?" is a child of each frame's header, vanilla's shape, rather than a block in the frame.
  - **The popup is 640 wide,** the sections' own widths plus margins (§ 5.2 said 760 with a 680 column). Rewidening every textbox can follow if the play-test asks for it.
  - **The 18 sections make 15 pages,** and the Fossil Transition's How joins Global Warming's.
  - **The history fix is an old-save repair** (§ 6.6). A store that stops recording is already sorted; only stores scrambled before the sort existed are out of order. The checker also scans `te_dg_hist`.
  - **The binding test has no lint twin** (§ 7.1). The test runs in CI, so a `check_gui_lint.py` warning would only repeat it.
  - **The Information tab's goto moves to Nation's PR** (F2), since it opens the Nation tab, which F1 doesn't yet show.
  - **The Space Race is a PR of its own** (F5), so § 10's F2–F4 becomes F2–F5.
- **Not built here** (spec § 7.7, and its own "later"):
  - a topic list for the long Help pages (§ 5.3);
  - year ticks on the large charts (§ 4.2);
  - Budget Breakdown, the Strategic Reserve, Global Warming, the UN and Covert Warfare for another country;
  - vanilla's tutorial lessons.
- **Owner calls still open** (spec § 11): the defaults above, each named where it lands.
