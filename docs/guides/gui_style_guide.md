# GUI Style Guide

What the mod's panels should look like. This is the default for every new or reworked system panel, whether it is a journal entry, a tab in a vanilla window or a window of its own. The owner set these rules over two in-game reviews of the UN panels (PR #567, September 2026) and endorsed them as the house style. Three play-test rounds of the other system panels (PRs #573–#583) added the rules marked *(play-test)*.

They are defaults, not laws. Break one when a panel has a real reason to, and say why in a comment next to the exception. That should be rare.

How to build each piece (widget types, data binding, scripted GUIs, the engine's gotchas) is in [`gui_modding_guide.md`](gui_modding_guide.md). This guide says what to aim for and points there for the how. Banking and Cultural Hegemony got their tabs before these rules were written down. The owner was happy with both, so they only need bringing in line when they are reworked for other reasons.

## Who a panel is for

A player who already knows the system and has opened the panel to check on it. Did the credibility pillar go up? Is the resolution passing? Which conventions bind us? Every choice below follows from that reader.

The walls of text still matter, but for players learning the mod. They stay in the panel, collapsed, where the experienced player never has to scroll past them.

## The rules

The rules run roughly from the most to the least important.

### 1. Dynamic content is visual and open; explanations are collapsed

- Anything that changes from month to month gets a visual where one fits (a bar, a pie, an icon, a table) and is **open by default**. Examples are missions in the field, the resolution in session, the authority pillars and why authority is moving.
- Anything that explains how the system works goes into **one collapsed "How X Works" section** at the bottom of the panel, with a subheading per topic. Don't sprinkle explanatory notes through the live sections. `long_tooltip_audit.py` lists live text and tooltips over 500 rendered characters.
- The overview at the top is always shown and cannot be collapsed.
- *(play-test)* A **history chart** is open by default. A **list of past items** (an archive, a ledger, ended missions) starts collapsed. A **live list** (rivals, pressure, networks) is open.
- *(play-test)* The journal entry's own **status text must not repeat the overview.** When the overview shows everything it said, it is empty while the entry is active. It keeps one line for the inactive entry, which draws no overview.

Example: `te_un_status_sections` (open, dynamic) and `te_un_reference_sections` → `te_un_sec_how` (collapsed) in `gui/journal_entry_widgets/un_layout_widget.gui`.

### 2. Nothing is lost

When an icon or a short label replaces a sentence, the sentence moves into that element's tooltip. A shorter panel must not hide information; it moves it one hover away.

### 3. Brief labels, the detail on hover

- Lines read **"Label: value"**, as in "Represented: 82", "Tier: Established", "Passage Rule: Majority", "Weight: ×3.08" and "Target: Germany".
- A game term in the label is a **concept** (`[concept_x]`), so hovering it explains the term. Add the concept when the term is new (`common/game_concepts/extra_concepts.txt` plus a name and a `_desc` key).
- The reason behind a value goes in a tooltip: a breakdown of a number, the reason a list is empty ("Target: None" gives why on hover), or what a title means. Hoverable text is underlined (`#tooltippable`). In a row type whose tooltip comes from a `row_tooltip` block, put the label's `default_format = "#tooltippable"` in a `label_format` block, which a row without a tooltip overrides empty (`nd_row`, `nuclear_program_row`). Where most rows sit under one shared hover, as the state view's tiles do, the block defaults off and a row with a hover of its own turns it on (`te_state_stat_row`; `test_vanilla_panel_additions.py` holds rows and hovers in step). The 2026-10-27 audit found whole panels with no underline at all (`docs/audits/gui_localization_audit.md`, finding 6). `unmarked_hover_audit.py` lists every hover whose text isn't underlined.
- Trim what the reader already knows. "Great-power commitment" became "Commitment", with the rest in its tooltip.
- *(play-test)* **Nothing a player reads ends in "...".** A fixed-width cell elides text too long for it. In order of preference:
  1. drop words a heading already says ("Infrastructure" under a Directed Credit heading);
  2. use a shorter label with the full name on hover;
  3. narrow a neighbouring column (a status word becomes an icon);
  4. use a smaller font;
  5. widen the cell.

  Budget about 0.5 GUI units per point of type per character for the serif row font (10 at 20, 8.5 at 17) and 8.6 for the 16-point tooltip face of the Banking overview, plus 10%. The overview's figure was measured from an in-game screenshot (2026-10-17): its long lines ran 7.1 to 8.5 a character, and short words run wider ("Momentum" 11.5) but rarely fill a cell. Check the longest dynamic name a cell can show, too.
- *(Steam Workshop feedback, 2026-10-13; the owner, 2026-10-17)* **Rows, values, buttons and notes are 17, subheadings 20, and the overview 16; nothing a player reads to decide something is smaller.** The Banking panels had their rows in medium and their overview in small, and a player found them hard to read, so the 2026-10-13 pass moved everything up a step (rows large, overview medium). The owner's pass of 2026-10-17 then brought the rows down to vanilla's body size and the overview up, which read cleaner. Vanilla's ladder is not one typeface: `fontsize_medium` (14), `fontsize_small` (12) and `fontsize_xsmall` (10) are the OpenSans tooltip face, while plain text is EBGaramond 17 and `fontsize_large` (20) and `fontsize_xl` (22) keep that serif. Put a panel's sizes in templates of its own (Banking's `banking_dash_fontsize_row`, `_heading` and `_overview`, at the head of `banking_dashboard_widget.gui`), so a pass on type edits numbers, not every textbox. A bigger type needs wider cells, so size a table from the longest label first (176 for Banking's label column, with its two-up rows split 176 and 144). Shorten a label, or let a long value wrap (`multiline = yes`), before squeezing a neighbour. `test_banking_layout.py`'s `WidthBudgetTest` reads each cell's font from the markup and each template's size, so it follows a change of type.

### 4. Icons first, with a small word beneath

- A status reads as an icon with a small label under it (membership, tier, a crisis), not as a sentence.
- *(owner, 2026-10-17)* **An overview of readings is a grid of boxes, two to a row.** Each box has its icon in an inset box of its own down the left, and beside it three lines: the caption, the reading's word, and a figure (next month's range, points free, the rate). Three to a row at 16 crowded the captions. Example: `te_banking_ov_cell` in `banking_dashboard_widget.gui`, `entry_bg_simple` with a `dark_area` inset at alpha 0.3.
- A set of things that each exist or not (agencies founded, seats filled) is a row of icons. Each icon is lit at full colour when the thing exists and dimmed when it doesn't.
- Prefer a vanilla widget that brings its behaviour with it. Vanilla's `flag` type shows the country's name on hover and opens the country on click, for free.

Example: the overview's first row and the agency icons in `gui/journal_entry_widgets/un_overview_widget.gui`.

### 5. Numbers: tables, bars and pies

- **Several related figures form a table**, not a sentence: label on the left, value on the right (`un_chamber_value_row`). Our Record's case strength and its six terms were a paragraph and are now a table.
- **A share is a pie**, framed with a ring so it reads as a dial (`round_frame_dec.dds` behind a stacked `progresspie`; the pie recipe is "Pie charts of script-held data" in the GUI guide).
- **Progress towards a target is a bar**, and the headline says where it is heading: "62 → 68 (+0.4/mo)".
- *(owner, 2026-10-17)* **A bar spends its width where the value plays differently.** It starts at the first value that changes anything, and the figure beside it carries a value past either end. Legislative Override Capacity's bar gave 6 of its 14 points to values below 0, which all play the same; it now runs from 0.
- *(play-test)* **Where a bar is heading is a translucent segment, not a marker.** The solid fill runs to the lower of the current and projected values, and the segment runs to the higher. So a rise extends past the fill, and a fall shows as the tail about to be lost.
  - The segment is **green when the change is good for the player, red when it is bad**, and the bar's own colour, pale, when it is neither. Warming is red; cooling is green.
  - A fixed threshold on the bar is a thin vertical line with its own hover.
  - Vanilla's eye-shaped `progressbar_marker` read as ambiguous, so it is not used for either.
  - The layers: Global Warming's temperature bar (`global_warming_widget.gui`, PR #575).
- **Related figures sit together.** Our dues belong next to the whole budget, not on the other side of the conventions.
- A good or bad number is coloured (`#G`/`#R`), and a trend gets an arrow icon rather than a sentence. The same convention holds everywhere: green is good for the player and red is bad, whatever the direction.
- *(play-test)* **The parts of a total are bars**, like the UN's authority pillars: one row per component, with a label, a fixed-width bar over an approximate range and a signed value. Examples are the parts of cultural pull and the terms moving colonial stability.

### 6. Buttons carry their own reasons

- A button sits **beside the item it acts on** or **centred** under it, never flush left under a wide block.
- A button that can't be pressed is greyed, and its tooltip lists the failing condition (`IsValidTooltip`, concatenated with the effect preview, gotcha #16). The row's text does not repeat that reason. `button_reason_audit.py` flags a button with no `IsValidTooltip`, and a condition that would print as raw script.
- Something true of every row is said **once, above the rows**. For example, "another delegation holds the floor" greys all eighteen proposal buttons but is printed once.

### 7. Sections

- Default open or collapsed by rule 1, and name the section's collapse flag after its default: `_open` for a section that starts collapsed, `_closed` for one that starts open (`FlagTest` in `test_un_layout.py` enforces this for the UN).
- Content that only matters in one state is a **subsection shown only in that state**. Delegations and the recorded ballot appear while a resolution is in session, and "Table a Resolution" appears when none is. A long subsection starts collapsed.
- Centre a group heading that sits over centred content (Security Council, Agencies, "Championing the order").
- Keep to one text style per job. Explanations use the smaller `#lore` note under a ruled subheading (`un_chamber_note` under `un_chamber_subheader`). Live lines use the section's own text type.

### 8. Tidiness

- No section starts with an empty line or an empty block. If the first builder can print nothing, gate it or reorder.
- No tooltip ends in a blank line. Don't end a loc line with `\n`, because a script-built list already separates its lines.
- No element may widen its row. Give each cell in a row of cells a fixed width, so a long label or a bar can't push its neighbours off-centre (the standing bar once pushed the pies out of line).
- *(play-test)* **Give every root a fixed width** (`minimumsize = { 520 -1 }` for a journal-entry root, with its rows in a 480 column). A wrapper sized by its content is centred once, at its first width. Rows that appear later then drift off-centre and clip, as the Global Warming and Nuclear overviews did in round 1.
- Scripted text needs no leading spaces when each line is its own row. Keep indentation for a sub-item under a heading line, such as a convention's terms under its name.

### 9. Where a system's panel goes

- **A system with a natural vanilla home becomes a tab in that window:** Banking in Budget, Cultural Hegemony in Society, the UN in Diplomacy. The system doesn't need a new window. Systems with no vanilla home go in one mod window rather than scattered tabs (`docs/systems/system_panels_feasibility.md` §9, item 3).
- The tab is **greyed until the system's journal entry is active**, and its tooltip lists the unlock conditions with ticks and crosses (the gates in `common/scripted_guis/te_system_tab_sguis.txt`).
- *(2026-10-27 audit, WIN-1)* **Every greyed tab's checklist has one shape.** The header is the tab's own name, spliced from the tab's key (`#b $te_market_tab_global_warming$#!`, not the entry's name). The lead-in is `Not open yet. It opens once:` on every tab. Each condition is one second-person clause with no full stop ("You have a coastal state", "You hold an overseas colony or a colonial subject"); a world condition names who ("Any country has researched …"). An OR stays one `custom_tooltip` line, since a bare OR prints an empty "All of these:". When every condition passes but the tab is still greyed, the tooltip is the shared `te_system_tab_met_tt`; a system whose timing differs keeps its own (the Seabed's `te_window_tab_seabed_met_tt`, "at the next seabed sharing").
- *(owner, 2026-10-17)* **An entry every country holds, whose system starts later, opens its tab from the start.** Banking's entry is every country's, dormant until its financial cycle starts. The overview then shows what the system needs (a Not Started cell, its checklist on hover), the readings that already exist (Monetary Policy) still show, and each control is greyed with the start as its tooltip's first line and said once above its rows (rule 6). Sections that only mean something once the system runs (Active Policies, the history) wait for it. Banking's early read-only readout (#805) now serves only a country without the entry: the game's first fortnight, and the rebels of a running revolution.
- *(owner, 2026-10-17)* **The Timeline Extended window's Nation tab is the one tab with no system behind it**: always open and first, never greyed, so the window opens there unless an open system tab was the last chosen.
- *(owner, 2026-10-17)* **One tab strip per window, up to six tabs**, as vanilla's panels hold five and the mod's Budget, Diplomacy and Market panels six. A two-word name that wraps or shrinks on a full strip, as vanilla's "Nation Formation" does, is no reason for a second strip: the Timeline Extended window had one for two of its five tabs.
- *(play-test, 2026-09-30)* **System tabs in vanilla panels, and in the mod's own window, carry no icon**, as vanilla's tabs don't; the tab's place after vanilla's and its greyed-until-unlocked checklist mark it as the mod's.
- The tab reads the entry through `GetPlayerJournalEntry('<key>')` (gotcha #29) and ends with an **"Open Journal Entry"** button, placed below everything else.
- **Build each section as a type**, so the journal entry and the tab compose the same pieces. The journal entry stays and may shrink to a stub once the tab carries everything.
- *(owner, 2026-10-09)* **Send players to the tab, not the journal entry.** Where a system has both, text that tells the player where to look or act (a tooltip, an event, a concept, a notification, a goto) names the tab: "on the UN tab of the Diplomacy panel", "the Grand Monuments tab of the Timeline Extended window". A goto into the Timeline Extended window sets `te_systems_window_tab`, then `com_open_window` (the state view's Grand Monument card). Text about the entry itself, such as when it opens, the modifiers it carries or its goal, still names the entry, and the tab's own Open Journal Entry button stays.

### 10. Placeholder art is fine

A new icon can start as any vanilla texture, so a layout can be judged in game before the art exists. List every placeholder in one doc, stating where it is set, what the final art should show (written as an icon-pipeline subject) and its proposed path. The UN's list was the model (now `docs/systems/un_gui_icons.md`, which records the finished set). Swapping one in should then be one path change, with a test holding each path to its code (`UnIconsTest`).

## Hover recipes

All proven in game:

| To show on hover | Write | Example |
|---|---|---|
| Any text, on a widget | `tooltip = "<key>"`. The loc may read `JournalEntry.GetCountry.MakeScope.ScriptValue(...)`, since it renders in the widget's datacontext. | the pillar rows' `je_un_auth_bar_credibility_tt` |
| What a term means | `[concept_x]`, or `[Concept('concept_x','Other words')]` for different words | `je_un_chamber_binding_not_vetoed` |
| A modifier's effects, in loc | `[GetStaticModifier('<name>').GetDesc]` | `scripting_best_practices.md`, "Render Static Modifier Effects in Loc" |
| Why a button is greyed, and what it does | `Concatenate( IsValidTooltip(...), Localize('te_tt_break'), ExecuteTooltip(...) )` | gotcha #16; the Propose buttons |
| A word inside a line printed by a scripted GUI's `ExecuteTooltip`, when the tooltip is plain text | `#tooltippable;tooltip:<key> Word#!` | the proposal rows' "None" (confirmed 2026-09-29), "No Case", "In Force", "On Cooldown" |
| The same, when the tooltip reads data such as `GetStaticModifier(...)` | `#tooltippable;tooltip:[GetPlayer.GetTooltipTag],<key> Word#!`, the form vanilla uses whenever the tooltip reads data | Our Obligations' conventions and terms (confirmed 2026-09-29); gotcha #32 |
