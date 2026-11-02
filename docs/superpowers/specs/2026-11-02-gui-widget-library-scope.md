# GUI widget library: scope (2026-11-02)

**Status:** scoping, for the owner's calls in § 10. Nothing is built yet beyond
`te_ui_popup`. This expands the Space Race UI pass design's § 13
(`specs/2026-10-31-space-race-ui-pass-design.md`), which named the library and
its first piece.

**The question.** Each system panel defines its own copy of the same pieces: its
section header, subheader, note, value row, panel shell, font sizes, overview
cell, pie and bars. What would it take to build one standard set and have every
panel use it, and what does that buy?

**Short answer.** The duplication is real and nearly exact: about 2,300 lines of
same-role type definitions across 15 systems, most of them identical once the
system prefix is taken off. The engine's GUI language can share structure and
style (types, templates, blocks) but cannot take a string argument, so a
library removes the copies and centralizes the look without removing the
per-instance boilerplate of collapse flags and scripted-GUI calls. The work is
about 22 to 26 PRs in six phases. The first two phases (shared tokens and
primitives, then each system's primitives turned into one-line derivations of
them) carry most of the value at low risk, because derived types are already
proven in game and the panels should draw the same as before. Line savings are
modest (a few thousand lines out of 68,700); the case rests on one place to
change the house style, rules enforced by construction, mod-wide tests in
place of per-system ones, and faster new panels.

## 1. What the panels have in common today

The mod's GUI is 218,000 lines in 81 files:

| Kind | Files | Lines |
|---|---|---|
| Hand-written system widgets (`journal_entry_widgets/`, `te_*`, `gm_*`, `sr_*`) | 44 | 68,669 |
| Generated (`sr_*_generated_rows`, `te_tax_generated_rows`, budget charts, Nation tab, `00_te_*`) | 7 | 70,545 |
| Full-file copies of vanilla panels | 28 | 79,141 |

The library is about the first row. The hand-written widgets define 583 types.

### 1.1 Same-role clones

Measured by taking each type's body, removing comments and the system prefix,
and comparing line sequences (`difflib` ratio against the most typical copy):

| Role | Copies | Lines | Similarity | What differs |
|---|---|---|---|---|
| Font templates (`*_fontsize_row` / `_heading` / `_overview`) | 15 sets | ~180 | identical | nothing: 17, 20, 16 everywhere |
| Section header (`*_section_header`) | 13 | 96 | 1.00 (two at 0.80) | Colonial Empire and Cultural Hegemony add a left-text alignment |
| Subsection header | 5 | 71 | 0.86–1.00 | |
| Subheader (`*_subheader`) | 16 | 364 | 0.86–1.00 | top margin 6 or 10; width 460 or 480 |
| Note (`*_note`) | 15 | 136 | 0.78–1.00 | width 460, 474 or 480 |
| Plain text (`*_text`) | 11 | ~90 | 1.00 | |
| Panel shell (`*_panel`, the boxed section body) | 15 | ~180 | 0.86–1.00 | margin 14 or 20; spacing |
| Value row (`*_value_row`) | 7 | 168 | 0.78–1.00 | the label/value split: 330/130, 190/282, 386/86 |
| Overview pie (`*_ov_pie`) | 5 | 223 | 0.74–1.00 | slice count and textures |
| Overview cell (`*_ov_cell`) | 4 | 184 | 0.69–1.00 | |
| Overview word / figure | 7 | 59 | identical | |
| Icon over a label (`*_ov_icon_label`) | 3 | 60 | 0.72–1.00 | |
| Status / reference composers | 22 | 351 | 0.44–1.00 | the section list (that is the point of them) |
| Steppers | 3 | 140 | 0.50–1.00 | |

The differences are almost all widths: the content column (460, 474, 480) and a
table's column split. They are per-system knobs, not different designs. A few
could be deliberate; none carries a comment saying so (style guide preamble:
an exception says why next to it).

Instances of these types: 96 section headers, 243 subheaders, 251 notes, 129
value rows, 186 collapse toggles.

### 1.2 A library is already forming, under other names

Some types have become shared because they were good, while keeping the name of
the system that wrote them:

| Type | Defined in | Used from |
|---|---|---|
| `te_banking_ov_cell` | `banking_dashboard_widget.gui` | 10 other files: every system's overview |
| `te_banking_ov_word` | the same | 5 other files |
| `te_history_chart` (and its bars, plot and range button) | `te_history_chart.gui` | 8 other files, 41 instances |
| `te_tab_buttons_six` | `te_system_tab_widgets.gui` | Budget, Diplomacy, Market |
| `te_je_scripted_bars`, `te_je_goal_bar`, `te_je_status_desc`, `te_je_scripted_buttons` | `te_system_tab_widgets.gui` | every system tab |
| `un_act_control`, `un_act_slot`, `un_act_row` (the gotcha #43 cure) | `un_chamber_widget.gui` | UN files only |
| `te_ui_popup` | `te_widget_library.gui` | Space Race's four popups |

`test_space_race_labels.py` already reads Banking's file to measure the Space
Race overview, because the cell lives there.

### 1.3 Repeated idioms the library can't absorb on its own

These are in instances rather than types, and they repeat because the GUI
language has no string parameters (§ 2):

- **Collapse flags.** Each section names its flag four times: the header's
  `onclick`, its show-more and show-less arrows' `visible`, and the panel's
  `visible`. 96 sections, 186 flags.
- **Scripted-GUI calls.** 476 hand-written `Execute` onclicks (362 of them
  passing an op through `AddScope`), 421 `IsValidTooltip` reasons and 713
  `IsShown(...)` visibles. Every one spells out its scope, the op-passing ones
  as `GuiScope.SetRoot( <root>.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint)N' ) ).End`.
- **Three scope roots.** The journal-born systems write `JournalEntry.GetCountry`
  (Space Race 357 times by hand, UN 1,890), the window-born ones `GetPlayer`
  (Tax Code, Seabed, Nation), and Demographics and part of Global Warming
  `Country` (gotcha #45).
- **Tables.** 30 table heads, each with its row type restating the same column
  widths (a test per system checks they match).
- **Country names.** 15 row types draw a flag beside a name; gotcha #44
  (`GetNameNoFlag`) was fixed across them one by one (#1216).
- **Colors.** 63 distinct `color = { r g b a }` literals in 95 uses: five
  near-identical greens and reds for good and bad.
- **Pie art.** 36 pie-slice textures in six folders, one set per system; the
  budget charts already borrow Cultural Hegemony's set as a palette.

### 1.4 What the copies have cost

The house-style passes have each had to visit every system:

- **Underlines (rule 3, 2026-10-30).** #1258 for the Space Race, then #1260 for
  the rest: 69 files, 411 `default_format = "#tooltippable"` lines removed from
  34 of them, and the per-system underline toggles (`label_format`,
  `row_format`, `cell_format`, `name_format`) each taken out separately.
- **Rows that drift (gotcha #43, 2026-10-28).** The UN's controls in #1216, then
  Cultural Hegemony, Covert, the Space Race, Nuclear and Banking in #1217, with
  more queued after it. One control-slot type would have been one fix.
- **Font sizes (2026-10-13 and 2026-10-17).** Banking's type moved up a step and
  then to 17/20/16; every other system carries its own copy of the result.
- **One flag per country (#1216).** 33 keys and six systems' rows.

Each of these also needed its own layout-test edits per system.

## 2. What the engine allows

The library has to work within the Jomini GUI language. Its sharing tools are:

- **Types** (`type X = base { }`), global across files, with derivation. Mod
  types deriving from mod types are proven in game: the state view's tiles
  (`te_state_tile_row = te_state_stat_row` and four more) and Demographics'
  family rows.
- **Templates** (`using = X`), property bundles, which can `using` other
  templates: every `*_fontsize_overview` uses vanilla's `tooltip_font`.
- **Blocks and blockoverrides**, which replace whole properties or children.
- **Datacontext**, which stacks by type: a child sees every type set above it
  (`ScriptedGui` set on a control still leaves `Country` and `JournalEntry`
  reachable), except a datamodel item's tooltip, which starts fresh (gotcha
  #24).

What it does not have, and what follows:

1. **No string or number parameters.** A type can't take "the flag name" or "the
   scripted GUI's name" and splice it into an expression. Anything named per
   instance stays a blockoverride, or a generator writes it. So the four
   mentions of a collapse flag stay four blockoverrides; the library can only
   hold the header, the arrows and the panel around them.
2. **No shared numeric tokens.** Brace vectors take literals (gotcha #39) and
   `@` constants are file-local (vanilla repeats them in each file that uses
   them). A width is therefore a block with a library default (a 520 root, a 480
   column), not a named constant. Font sizes and colors can be templates.
3. **Literals a type can bake in.** A type can hold `'(CFixedPoint)0'` itself.
   Where script agrees on a convention, the type needs no override: a stepper
   whose scripted GUI reads `scope:op` 0 as down and 1 as up can carry both
   buttons whole (`covert_cc_funding_stepper` already does this).
4. **One scope root.** For a library control to bake in
   `GuiScope.SetRoot( Country.MakeScope ).End`, its host must provide a
   `Country`. That works in a journal entry (`datacontext =
   "[JournalEntry.GetCountry]"` at the root), under `GetPlayerJournalEntry` in a
   tab, and in a window (`[GetPlayer]`). `Execute` through `Country.MakeScope` is
   proven (Global Warming's policy buttons; Demographics' measure-row and
   pension buttons, which already have the `te_ui_sgui_button` shape of § 3.3).
   Existing `JournalEntry.GetCountry` expressions keep working beside it, so
   nothing outside the library types has to convert.
5. **Global names.** Every type name is global, and the Community Mod Framework
   redefines vanilla ones (gotcha #30, #557), so everything is `te_ui_`.
   Which of two definitions of one name wins between mod files is untested, so
   a name is defined exactly once: a migration renames or derives, never
   redefines.
6. **No game in the cloud container.** Type mechanics are proven, but anything
   new in behavior (a tinted pie, a click-modifier stepper, the popup layer) is
   a play-test item, not a merge gate (`CLAUDE.md`, In-game checks).

## 3. The catalog

What the library would hold, from the bottom up. "Replaces" names what each
system has today. "Rule" is the style-guide rule the type carries, so a panel
built from it follows the rule without anyone remembering to.

### 3.1 Tokens (templates)

| Name | What | Replaces | Rule |
|---|---|---|---|
| `te_ui_fontsize_row`, `_heading`, `_overview` | 17 serif, 20 serif, 16 tooltip face | 15 identical sets | 3 (sizes) |
| `te_ui_color_good`, `_bad`, `_good_soft`, `_bad_soft`, `_neutral`, `_track`, `_threshold`, `_zero` | the panel palette | 63 literals | 5 (green good, red bad; the pale projected segment) |
| `te_ui_inset` | `dark_area` at 0.3, the overview icon's box | each overview's copy | 4 |

Widths are block defaults inside the types below (§ 2, point 2).

### 3.2 Primitives

| Name | What | Replaces | Rule |
|---|---|---|---|
| `te_ui_section_header` | 520 `section_header_button`, centered | 13 | 7 |
| `te_ui_subsection_header` | the smaller nested header (gotcha #26) | 5 | 7 |
| `te_ui_panel` | the boxed section body, 20 × 8 margin, 480 column | 15 | 8 (fixed width) |
| `te_ui_subheader` | `#title` text over a `divider_clean`, `subheader_margin` block | 16 | 7 |
| `te_ui_note` | `#lore`, 480, multiline | 15 | 7 |
| `te_ui_text` | a live line, 480, multiline | 11 | |
| `te_ui_value_row` | label and value, `label_width` and `value_width` blocks, value elides | 7, plus most `*_row` tables | 3, 5 |
| `te_ui_ov_cell`, `te_ui_ov_word`, `te_ui_ov_figure` | Banking's cell: icon in an inset, caption, word, third line, badge | `te_banking_ov_*` (shared by 10), 4 other cells | 4 |
| `te_ui_icon_label` | an icon with a small word beneath | 3 | 4 |
| `te_ui_trend` | up, down and flat arrows, colored by good or bad | Demographics' three, Covert's | 5 |

### 3.3 Composites

| Name | What | Replaces | Rule |
|---|---|---|---|
| `te_ui_section` | header plus panel, the four flag blocks, `section_title`, `section_body` | the shell of 96 sections | 1, 7 |
| `te_ui_how_section`, `te_ui_how_topic` | the collapsed "How X Works" section; a topic is a subheader and its note | 15 How sections, ~1,500 lines | 1 |
| `te_ui_pie` | ring plus up to four stacked slices, a label beneath | 5 overview pies, Demographics' causes pie | 5 |
| `te_ui_bar` | a track with a fill, an optional translucent projected segment, an optional threshold line | Global Warming's temperature bar, the seabed pool, meters | 5 (where it heads, thresholds) |
| `te_ui_signed_bar` | negative fill left, positive right, a zero line | `ch_pull_bar`, `te_history_bar_signed`, Demographics' term rows, Covert's bar line | 5 |
| `te_ui_component_row` | label, fixed-width signed bar, signed value | Cultural Hegemony's pull, Colonial Empire's pillars, the UN's authority pillars | 5 (parts of a total) |
| `te_ui_icon_set` | a row of icons, each lit or dimmed | the UN agencies and seats | 4 |
| `te_ui_table_head`, `te_ui_table_cell` | head and body cells sharing one `cell_size` block | 30 table heads | 8 |
| `te_ui_country_cell` | flag widget and `GetNameNoFlag`, fixed width | 15 flag rows | gotcha #44 |
| `te_ui_control_slot`, `te_ui_control_row` | a fixed-size slot holding controls that take turns; a fixed-width row that hides when empty | `un_act_*`, the two-row cures of #1216 and #1217 | 8 (gotcha #43) |
| `te_ui_sgui_button` | a button whose `ScriptedGui` datacontext gives its `enabled`, `onclick` and the reasons-then-effect tooltip, rooted on `Country` | most of the 476 Execute buttons that pass no op | 6 |
| `te_ui_stepper` | minus, value, plus; op 0 down, op 1 up; optional Shift, Ctrl, Alt and right-click amounts (UI pass § 6) | 3 steppers, the transfer amounts | 6 |
| `te_ui_choice` | one option of a segmented row (the approach-selector look) | `te_sr_posture_choice`, `nd_choice_row`, the reserve policy choice | 6 |
| `te_ui_popup` | already built | | |

### 3.4 Layout and hosts

| Name | What | Replaces |
|---|---|---|
| `te_ui_je_root` | the 520 journal-entry root gated on `IsActive` (gotcha #14) | 49 hand-written roots |
| `te_ui_status_sections`, `te_ui_reference_sections` | vertical composers with the `IsActive` gate; the system lists its sections | 22 composers |
| `te_ui_open_je_button` | the tab's closing "Open Journal Entry" (rule 9) | one per tab |
| `te_ui_tab_strip`, `te_ui_tab_button` | the six-slot strip and a grayed-with-checklist tab | `te_tab_buttons_six`, the Timeline Extended window's per-tab templates |

The existing `te_history_chart`, `te_je_*` and `te_state_stat_row` families stay
where they are under their own names: they are libraries already. The catalog
in the docs (§ 5.4) lists them with the rest.

## 4. Migration

The order that keeps every step small and the panels drawing the same:

1. **Build beside.** Add the library types. Nothing uses them, so nothing can
   break in game.
2. **Derive in place.** In each system file, replace the body of each clone with
   a derivation that keeps its name and its own widths:
   `type gw_note = te_ui_note {}`, `type te_tax_value_row = te_ui_value_row {
   blockoverride "label_width" { … } }`, `template gw_fontsize_row { using =
   te_ui_fontsize_row }`. Every instance, test and generator keeps working
   under the old names. From here a style change edits one file.
3. **Harmonize, by the owner's call.** The 460/474/480 columns and the 6/10
   margins become one value or a named exception with its reason (§ 10, Q2).
   This is the only step that changes how a panel looks.
4. **Rename instances and delete the aliases,** one system per PR, when that
   system is next worked on or in a quiet week. This is where composites
   (`te_ui_section`, `te_ui_how_topic`, pies, bars) replace hand-built shapes.
5. **Generators** emit library types (§ 5.1).

Step 2 alone gives the single place to change style. Steps 4 and 5 can wait as
long as they need to; the aliases cost one line each.

**System order for step 4,** smallest first, so the composites are proven on a
small panel: Seabed (1.6k lines), Strategic Reserve (2.7k), Global Warming
(2.2k), Grand Monuments (3.4k plus 3.0k in `gm_*`), Cultural Hegemony (3.0k),
Colonial Empire (2.9k), Covert (2.7k), Nuclear (3.9k in four files), Tax Code
(5.2k in six), Banking (5.6k in three), UN (8.5k in four), Demographics (7.9k
plus two files), Space Race (9.3k, after its UI pass ends, as § 13 there
said). The state view tiles, Budget breakdown and Nation tab come last; they
have families of their own already.

## 5. The Python side

### 5.1 A shared GUI emitter for the generators

`gen_space_fleets.py` and `gen_solar_sites.py` each define their own `_sv`,
`_eq`, `_ge`, `_override` and `_reasoned` (the reasons-then-effect tooltip
string), and `gen_tax_code.py` builds the same strings again. One module,
`scripts/generators/gui_emit.py`, would hold them: scope expressions, op and
pick scopes, the reasoned tooltip, blockoverride blocks, and helpers that emit a
library instance (`emit_value_row(label=…, value=…)`). Each generator moves to it
with a byte-for-byte `--check` first, then switches its rows to library types
in a second commit. The 70,000 generated lines exist because a row can't take a
slot number at run time (UI pass § 3); the emitter makes each row smaller but
doesn't remove the need for them.

### 5.2 A type resolver for the layout tests

27 test files name 73 of the per-system primitive types, and the width tests
(`test_space_race_labels.py`, `test_banking_layout.py`'s `WidthBudgetTest`,
`test_un_widths.py` and others) read each system's font sizes with a regex over
that system's own file. Once those live in the library, the regexes find
nothing.

`gui_tree.py` has `type_index` and `base_chain` but doesn't apply
blockoverrides or `using`. The enabler is `gui_tree.resolve(instance)`: follow
the type chain, apply each level's blockoverrides and templates, and return the
effective tree, so a test asks "what width and font does this textbox end up
with" whatever file defines them. About 300 lines with its own tests, written
in phase 0 so the alias step can move the tests onto it.

### 5.3 Mod-wide tests in place of per-system ones

With the resolver and the library, several checks can cover every panel at once
instead of being rewritten per system:

- **No elision** (rule 3): every single-line cell of a library row type, its
  longest loc measured against its resolved width and font. Today this is
  written three times (Space Race, Banking, UN).
- **Heads match rows:** a `te_ui_table_head`'s cells against its rows'.
- **One flag per country:** `te_ui_country_cell` is the only place a flag
  meets a name (`test_gui_flag_names.py` already scans every file).
- **Fixed widths** (rule 8): every root and control row resolves to a fixed
  width.
- **No new clones:** a lint that fails on a new `type <sys>_note`,
  `_subheader`, `_section_header`, `_value_row` or `_panel` that doesn't derive
  from the library, and on a new `*_fontsize_*` template. This keeps the next
  system from starting its own copies. It belongs in `check_gui_lint.py` or a
  small audit run in CI.

### 5.4 Docs

- A catalog: one page per type family (blocks, defaults, a minimal instance,
  the rule it carries, proven or not), either a section of
  `gui_modding_guide.md` or its own `docs/guides/gui_widget_library.md`
  (fewer CRLF edits; the guide is CRLF).
- `gui_style_guide.md` examples point at library types instead of
  `un_chamber_value_row` and `te_banking_ov_cell`.
- The file table in `gui_modding_guide.md` (`test_tax_code_bypass` counts it)
  gains a row for any new top-level library file. Keeping the library in the
  one existing file, or a few `te_ui_*.gui` files added in one PR, keeps that
  churn small.

## 6. Phases and size

| Phase | PRs | Contents | Risk in game | Play-test items |
|---|---|---|---|---|
| 0. Foundation | 1 | tokens and primitives in `te_widget_library.gui`; `gui_tree.resolve` and its tests; the catalog doc | none: nothing uses the types | none |
| 1. Derive in place | 1–2 | every system's primitives and font templates become derivations (§ 4 step 2); 27 test files move onto the resolver | low: derived types are proven, output should be identical | one pass over every panel against the player guide's screenshots |
| 2. Composites | 3 | (a) layout: section, How section, JE root, composers, Open Journal Entry; (b) controls: control slot and row, scripted-GUI button, stepper, choice, tab strip; (c) data: pie, bars, component row, icon set, table cells, country cell, promoting `te_banking_ov_*` | medium for (b) and (c), which carry new behavior | the gallery tab (§ 7.3) |
| 3. Harmonize | 1 | the owner's calls on widths and margins (§ 10, Q2) | low, visible | the changed panels |
| 4. Per-system migration | 13–15 | one system per PR (§ 4 order); aliases deleted | low to medium per panel | each panel's existing play-test list |
| 5. Generators and enforcement | 2–3 | `gui_emit.py`; generators on library types; the clone lint in CI; style guide rewritten around the library | low | none new |

About 22 to 26 PRs. Phases 0 and 1 can land in a few days and deliver the single
style point; phase 4 can be spread over whatever schedule suits, since the
aliases keep old and new working side by side.

**Size of the payoff in lines:** the ~2,300 lines of clone definitions in § 1.1
become about 400 of library, and the duplicated composites (pies, signed bars,
steppers, tables) shed perhaps another 1,500 to 2,500. Instance boilerplate (the
flag blocks, the scripted-GUI calls) mostly stays. Call it 3,000 to 5,000 lines
of 68,700. That is not the reason to do it.

## 7. Opportunities beyond removing copies

### 7.1 The style guide, enforced by construction

Rules that are now remembered per panel become properties of a type:
fixed-width roots and control rows (rule 8, gotcha #43), the pie's ring and the
bar's projected segment (rule 5), one flag per country (gotcha #44), the
reasons-then-effect tooltip on every button (rule 6, gotcha #16), the 17/20/16
sizes (rule 3), green for good and red for bad (rule 5), How sections collapsed
and named `_open` (rules 1 and 7). A new rule is then one edit and one test.

### 7.2 New panels faster

A new system's panel today starts by copying another system's 150 lines of
primitives and its font templates, then building its overview cells, pie and
bars from a neighbor. With the library, it starts from the composers and the
section shell. The recent additions (Seabed, the Local Climate tile, the
colony pages) are the kind of work this shortens. A skill like
`add-formable-country`, say `add-system-panel`, could walk through overview,
status and reference roots, the tab, the gate checklist and the play-test list.

### 7.3 A widget gallery tab

The Timeline Extended window already has a debug-only tab (the tax probes,
`te_tp_panel`, shown to an armed country and removed before release). A Widget
Gallery tab beside it, drawing every library type with fixed sample data, turns
the library's play-test into one screen: every bar, pie, stepper state, grayed
button and drifting-row case at once, and a screenshot to compare after each
library change. It is the natural home for the engine questions in § 8.

### 7.4 One palette for pies and colors

Eight named colors in place of 63 literals. For pies, either one shared set of
slice textures in `gfx/interface/icons/te_ui/` (the budget charts already treat
Cultural Hegemony's set that way), or a single white slice tinted by `color`,
which would make a new slice color free. The tint is unproven: no `progresspie`
in the mod or the vanilla fixtures sets `color` (§ 8).

### 7.5 Host-agnostic sections

With library controls rooted on `Country`, a section built for the journal
entry also draws in a tab, a window or a popup without edits, which the style
guide already asks for (rule 9: build each section as a type). Demographics
moved to `Country` to draw for any country in the Census Data window
(gotcha #45); the library makes that the default for every system.

### 7.6 Cheaper style experiments

Because the owner's type passes (Workshop feedback, 2026-10-13; the 2026-10-17
sizes; the 2026-10-30 underlines) become one-file edits, trying a change in game
costs a deploy, not a sweep.

## 8. Engine facts to confirm in game

| Fact | Used by | If it fails |
|---|---|---|
| A `progresspie` with `color` tints a white slice | `te_ui_pie` palette (§ 7.4) | a shared DDS palette |
| `te_ui_popup` on the popups layer, Escape, the panel behind scrolling | already on `docs/testing/solar-colonies-playtest.md` | the inline fallback there |
| A color-only template (`template te_ui_color_good { color = { … } }`) applies through `using` | § 3.1 | colors as block defaults in each type |
| Click modifiers on the stepper's buttons (Shift, Ctrl, Alt, right-click) | `te_ui_stepper` (UI pass § 6) | plain steppers |
| A `Country` datacontext from `JournalEntry.GetCountry` under `GetPlayerJournalEntry` in a tab | § 2 point 4 | `JournalEntry.GetCountry` as the default in a `scope_root` block |

Each goes on the gallery tab and a play-test list; none gates a merge.

## 9. Out of scope

- **Vanilla panel copies** (79,000 lines). The library doesn't shrink them. A
  separate idea, redefining single vanilla types from `00_` files as CMF does
  (gotcha #30), would; it carries its own compatibility questions (#557).
- **A whole-panel generator** (panels written as YAML or Python and compiled to
  `.gui`). It would remove the flag and scripted-GUI boilerplate the library
  can't, but every panel edit would go through a generator, the hand-edit ban
  would cover all of `gui/`, and nothing in the mod does it yet. Worth
  revisiting only if, after phase 4, the remaining boilerplate still slows work.
- **Per-slot generated rows.** They remain; § 5.1 makes them smaller.
- **New panel designs.** The library carries the house style as it is.

## 10. Open questions for the owner

1. **Go ahead with phases 0 and 1?** They are the low-risk half and carry most
   of the value. Phase 4's pace can be decided later.
2. **Harmonize the widths?** Content columns of 460 (Banking), 474 (Cultural
   Hegemony) and 480 (the rest), panel margins of 14 and 20, subheader margins
   of 6 and 10: one standard, or keep each as a named exception?
3. **One library file or several?** `te_widget_library.gui` alone, or a few
   (`te_ui_tokens.gui`, `te_ui_primitives.gui`, `te_ui_controls.gui`,
   `te_ui_data.gui`)? Several are easier to read; each new top-level file adds
   a row to the GUI guide's table.
4. **The scope convention.** Library controls read `Country`, set at each root
   (recommended, § 2 point 4), or keep `JournalEntry.GetCountry` and give
   window hosts a separate variant?
5. **The gallery tab.** Debug-only like the tax probes, or kept in release
   builds behind a game rule for modders?
6. **When the Space Race moves.** After its UI pass (as § 13 there said), or
   in the same pass since that panel is being reworked anyway?
