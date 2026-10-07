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
- Anything that explains how the system works goes into **one collapsed "How X Works" section** at the bottom of the panel, with a subheading per topic. Don't sprinkle explanatory notes through the live sections.
- The overview at the top is always shown and cannot be collapsed.
- *(play-test)* A **history chart** is open by default. A **list of past items** (an archive, a ledger, ended missions) starts collapsed. A **live list** (rivals, pressure, networks) is open.
- *(play-test)* The journal entry's own **status text must not repeat the overview.** When the overview shows everything it said, it is empty while the entry is active. It keeps one line for the inactive entry, which draws no overview.

Example: `te_un_status_sections` (open, dynamic) and `te_un_reference_sections` → `te_un_sec_how` (collapsed) in `gui/journal_entry_widgets/un_layout_widget.gui`.

### 2. Nothing is lost

When an icon or a short label replaces a sentence, the sentence moves into that element's tooltip. A shorter panel must not hide information; it moves it one hover away.

### 3. Brief labels, the detail on hover

- Lines read **"Label: value"**, as in "Represented: 82", "Tier: Established", "Passage Rule: Majority", "Weight: ×3.08" and "Target: Germany".
- A game term in the label is a **concept** (`[concept_x]`), so hovering it explains the term. Add the concept when the term is new (`common/game_concepts/extra_concepts.txt` plus a name and a `_desc` key).
- The reason behind a value goes in a tooltip: a breakdown of a number, the reason a list is empty ("Target: None" gives why on hover), or what a title means. Hoverable text is underlined (`#tooltippable`).
- Trim what the reader already knows. "Great-power commitment" became "Commitment", with the rest in its tooltip.
- *(play-test)* **Nothing a player reads ends in "...".** A fixed-width cell elides text too long for it. In order of preference:
  1. drop words a heading already says ("Infrastructure" under a Directed Credit heading);
  2. use a shorter label with the full name on hover;
  3. narrow a neighbouring column (a status word becomes an icon);
  4. use a smaller font;
  5. widen the cell.

  Budget about 10 GUI units per character for the large row font and 8.6 for the medium table font, plus 10%. Check the longest dynamic name a cell can show, too.

### 4. Icons first, with a small word beneath

- A status reads as an icon with a small label under it (membership, tier, a crisis), not as a sentence.
- A set of things that each exist or not (agencies founded, seats filled) is a row of icons. Each icon is lit at full colour when the thing exists and dimmed when it doesn't.
- Prefer a vanilla widget that brings its behaviour with it. Vanilla's `flag` type shows the country's name on hover and opens the country on click, for free.

Example: the overview's first row and the agency icons in `gui/journal_entry_widgets/un_overview_widget.gui`.

### 5. Numbers: tables, bars and pies

- **Several related figures form a table**, not a sentence: label on the left, value on the right (`un_chamber_value_row`). Our Record's case strength and its six terms were a paragraph and are now a table.
- **A share is a pie**, framed with a ring so it reads as a dial (`round_frame_dec.dds` behind a stacked `progresspie`; the pie recipe is "Pie charts of script-held data" in the GUI guide).
- **Progress towards a target is a bar**, and the headline says where it is heading: "62 → 68 (+0.4/mo)".
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
- A button that can't be pressed is greyed, and its tooltip lists the failing condition (`IsValidTooltip`, concatenated with the effect preview, gotcha #16). The row's text does not repeat that reason.
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
- The tab is **greyed until the system's journal entry is active**, and its tooltip lists the unlock conditions with ticks and crosses (the gates in `common/scripted_guis/te_system_tab_sguis.txt`). The one exception is Banking (#805): a country whose central bank already sets a rate, or whose currency is tied to another's, gets the tab early with a read-only readout of that state, because it can meet a peg crisis without the entry.
- *(play-test, 2026-09-30)* **System tabs in vanilla panels, and in the mod's own window, carry no icon**, as vanilla's tabs don't; the tab's place after vanilla's and its greyed-until-unlocked checklist mark it as the mod's.
- The tab reads the entry through `GetPlayerJournalEntry('<key>')` (gotcha #29) and ends with an **"Open Journal Entry"** button, placed below everything else.
- **Build each section as a type**, so the journal entry and the tab compose the same pieces. The journal entry stays and may shrink to a stub once the tab carries everything.

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
