# Demographics, Nation tab, Timeline Extended window chrome & system-tab gates — GUI & localization audit

> **Status (2026-10-27 wave):** every finding below is done or needs no change; each one's Status line says what changed. Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

## Top priorities
- **DEM-1:** both fertility tooltips point at "the figures above" (mean age at childbirth, births to women of 50 and over), but no GUI shows them any more. Their keys sit in `te_unused_l_english.yml` and their gates are unreferenced. Put them back in the tooltip or delete the sentence. (hidden info, high)
- **NAT-1:** the country panel's Modifiers list drops 249 Nation-tab modifiers and nothing says where they went. Add one generated line, "Lasting modifiers: N on the Nation tab", with rule 9's goto into the window. (hidden info)
- **DEM-3 + DEM-2:** How Demographics Works has no Work and Retirement or Longevity topic, so the pension-linking, youth-bulge, sex-balance, longevity-care and uploaded-minds rules are written only in live tooltips. Meanwhile the fertility tooltip repeats How's fertility text over the table that itemises it. Two new How subsections let those tooltips shrink to title + line + figures. (over-explaining)
- **WIN-1 + WIN-2:** the thirteen greyed-tab checklists use four lead-ins and three grammatical persons, and every journal-backed tab's tooltip (twelve keys, plus the launcher's) ends in the same "These are the journal entry's own panels…" sentence. Mostly loc-only, in Quick fixes. (style / over-explaining)
- **DEM-5 + DEM-4:** the pension buttons hand-type their interest-group reactions where `[GetStaticModifier('te_demog_pension_pos_*').GetDesc]` exists (the measures beside them already do this), and the Causes of Death pie's hover repeats the table next to it. Quick fixes.
- **DEM-6:** "4 of our states have a youth bulge … each state's subtab shows its own" (and the same for Metropolises) should be a short list in the States table's own pattern (a `te_dg_yb_states` list built in `te_demog_country_lists`). (list)
- **NAT-3 / NAT-4:** the Nation overview's tooltips define the term (already a concept on the caption) and say "see below", instead of the cause Banking's cells give. Each score is explained three times (concept, row tooltip, How). (spread-out / duplication)

## Findings

### WIN-1. The thirteen greyed-tab checklists read thirteen different ways
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). Every greyed tab's header is the tab's own name spliced from its key, the lead-in is "Not open yet. It opens once:" on all thirteen (the Space Race's and the Seabed's too; the Seabed's timing stays in its own met line), and the condition lines are second-person clauses with no stop: the Tax Code tab got its own line (`te_tax_tt_unlock_code`, "Your taxation law has been carried over into a tax code"), so the ~30 tax tooltips that print `te_tax_tt_code_in_force` keep their sentence; the nuclear line lost its parentheses; the mass-media and urban-center lines say who. The shape is written into `gui_style_guide.md` rule 9.
- **Category:** style
- **Where:** every `*_locked_tt` lead-in plus the condition lines the unlock triggers print through `IsValidTooltip` (gates in `common/scripted_guis/te_system_tab_sguis.txt`). Lead-ins: `te_window_tab_space_race_locked_tt`, `te_window_tab_grand_monuments_locked_tt`, `te_window_tab_colonial_empire_locked_tt`, `te_window_tab_seabed_locked_tt` (`te_miscellaneous_l_english.yml:8560-8573`), `te_society_tab_ch_locked_tt` (:8517), `te_market_tab_global_warming_locked_tt` / `te_market_tab_strategic_reserve_locked_tt` (:8045/:8049), `te_military_tab_covert_locked_tt` / `_nuclear_locked_tt` (:8056/:8059), `te_pops_tab_demog_locked_tt` (:8285), `te_budget_tab_banking_locked_tt` (:6605), `te_diplomacy_tab_un_locked_tt` (`te_diplomacy_l_english.yml:113`), `te_tax_tab_locked_tt` (`te_tax_l_english.yml:527`).
- **Now:** the header, the lead-in and the condition lines each vary:
  - **Header** is sometimes the tab's name (`#b Banking#!`, `#b Hegemony#!`, `#b Space Race#!`, `#b Seabed#!`, `#b Demographics#!`), sometimes the journal entry's (`#b $je_global_warming$#!` over the *Climate* tab, `$je_strategic_reserve$` over *Reserve*, `$je_covert_warfare$` over *Covert*, `$je_nuclear_program$` over *Nuclear*, `$je_grand_monuments$` = "Monuments" over *Grand Monuments*).
  - **Lead-in**: "Not open yet. It opens once:" (9 tabs), "It opens once you have:" (Reserve), "It opens at the first seabed sharing after:" (Seabed), "It opens with our first milestone and stays open from then on. The first, Suborbital Flight, starts once:" (Space Race); Banking has no checklist at all, just a sentence.
  - **Condition lines** (the trigger keys): second person "You hold an overseas colony…" (`ce_unlock_colonies_tt`), "You are a [concept_great_power]…" (`sr_unlock_rank_tt`); first person "We have researched $abyssal_plain_mining$" / "We have a coastal state" (`te_seabed_unlock_tech_tt`/`_coast_tt`), "…or we hold [law]" (`gw_entry_unlock_tt`); impersonal "Some country has researched $mass_media$" (`ch_unlock_any_mass_media_tt`); bare noun phrases "A $building_strategic_reserve_hub$" (`st_res_entry_unlock_tt`), "An $building_urban_center$ at level 5 or higher"; full sentences with a stop "The tax code is in force." (`te_tax_tt_code_in_force`) and two sentences "The first census has been taken. It is taken at the turn of each year." (`te_demog_tab_first_census_tt`); one 230-character line with a parenthesis (`nuclear_program_unlock_tt`).
- **Proposed:** one shape for every tab, written down once in `gui_style_guide.md` rule 9:
  - header: the **tab's own name** (what the player just hovered), so `#b Climate#!`, `#b Reserve#!`, `#b Covert#!`, `#b Nuclear#!`, `#b Grand Monuments#!`, `#b UN#!` (or keep the entry names everywhere, but pick one);
  - lead-in: `Not open yet. It opens once:` everywhere, with the system's timing (Seabed's "at the next seabed sharing", Space Race's "with the first milestone") moved into the `_met_tt` or a final line;
  - condition lines: one second-person clause each, no full stop, as most already read ("You hold…", "Your … runs …", "You have researched …"). `te_demog_tab_first_census_tt` → `Your first census has been taken (at the start of the game, or within a new country's first year)` (its current "at the turn of each year" is also wrong, DEM-7); the Seabed and Global Warming lines to "You"; `te_tax_tt_code_in_force` loses its stop (it is used by ~30 tax tooltips, so change it with the Tax Code's tooltips).
  - Long single lines (`nuclear_program_unlock_tt`, `gm_unlock_tt`, `covert_warfare_unlock_tt`) stay one line each. The one-line form is deliberate: a bare `OR` printed an empty "All of these:" (`un_entry_unlocked`'s comment, owner 2026-09-29), and `test_the_checklist_is_the_entrys_own_test_in_one_line` pins it for Nuclear, Global Warming and the Reserve; `nuclear_program_unlock_tt` must keep "$nuclear_weapons$", "$ICBMs$", "warheads" and "crisis". They can still lose their parentheses, since the concepts carry those details.
- **Effort:** quick for the lead-ins and the first-person / full-stop / noun-phrase lines (Quick fixes below); `te_tax_tt_code_in_force` is shared with ~30 tax tooltips, so it's left for the Tax Code work.
- **Confidence:** high (each string quoted from the file).

### WIN-2. "These are the journal entry's own panels: a change made here shows there too" on every journal-backed tab's tooltip and the launcher's
- **Status:** **Done in #1202; no change needed since.** No tab tooltip carries the sentence, and every Open Journal Entry button says the journal shows the same panels.
- **Category:** over-explaining
- **Where:** `te_window_tab_colonial_empire_tt` (:8561), `te_window_tab_grand_monuments_tt` (:8564), `te_window_tab_space_race_tt` (:8574), `te_systems_window_launcher_tt` (:8550) in `te_miscellaneous_l_english.yml`; the same sentence ends `te_diplomacy_tab_un_tt`, `te_budget_tab_banking_tt`, `te_market_tab_global_warming_tt`, `te_market_tab_strategic_reserve_tt`, `te_military_tab_covert_tt`, `te_military_tab_nuclear_tt`, `te_society_tab_ch_tt`, `te_tax_tab_full_tt`, `te_tax_tab_light_tt`.
- **Now:** every system tab's hover spends its second sentence on an implementation reassurance. On the Space Race tab it is "The milestones are the journal entries' own panels: a change made here shows there too."
- **Proposed:** cut it from every tab tooltip, and say it once where it matters, on the tab's **Open Journal Entry** button: `te_window_colonial_empire_open_journal_tt` → "Opens $je_colonial_empire$ in the journal, which shows these same panels." (and likewise for the other `*_open_journal_tt`). Banking's button already does this ("which adds the entry's description and status text"). This PR applied it to all of them: the window's four and the eight vanilla-panel tabs (nine keys; Tax has two).
- **Effort:** quick
- **Confidence:** high

### WIN-3. The launcher's tooltip lists the tab strip in prose
- **Status:** **Done in #1202; no change needed since.**
- **Category:** over-explaining
- **Where:** `te_systems_window_launcher_tt` (`te_miscellaneous_l_english.yml:8550`), shown by `sidebar_tooltip_area_small` (`gui/te_systems_window.gui:1093`).
- **Now:** "Nation: what your country carries for good, in one place. Then a tab each for the Space Race, Grand Monuments and the Colonial Empire, the journal entries' own panels (a change made here shows there too), and one for the Seabed." It's three clauses, and the strip says the same once the window is open.
- **Proposed:** "#b Timeline Extended#!\nYour nation's lasting scores and modifiers, and a tab each for the Space Race, Grand Monuments, the Colonial Empire and the Seabed." (The panels sentence moves to the Open Journal Entry buttons, WIN-2.)
- **Effort:** quick
- **Confidence:** high

### WIN-4. The Grand Monuments tab is headed "Monuments"
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The window's header reads `te_window_tab_grand_monuments`; the entry keeps its short "Monuments" in the journal, and the button's "Opens Monuments in the journal" names the entry, which is right.
- **Category:** style (naming)
- **Where:** `gui/te_systems_window.gui:778-784` (`default_header` `text = "je_grand_monuments"`), loc `je_grand_monuments:0 "Monuments"` (`te_journal_entries_l_english.yml:389`); also `te_window_tab_grand_monuments_locked_tt` (header `$je_grand_monuments$`) and `te_window_grand_monuments_open_journal_tt` ("Opens Monuments in the journal").
- **Now:** the tab reads "Grand Monuments"; its own header, its greyed checklist header and its button tooltip read "Monuments". Every other window tab's header equals its tab name ("Colonial Empire" / `je_colonial_empire`).
- **Proposed:** point the window header at `te_window_tab_grand_monuments` instead (GUI, one line), or rename the entry to "Grand Monuments" if the journal has room (the journal entry's name is also its row title in the journal, so check the owner wanted the short form there).
- **Effort:** quick (GUI one-liner) / medium if renaming the JE
- **Confidence:** medium (the short JE name may be deliberate for the journal list; the tab header mismatch is not)

### WIN-5. Three identical "conditions met" keys
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The window's three tabs and the Market panel's two use `te_system_tab_met_tt`; the two copies are deleted and the tests that named them updated. The Demographics tab's unreachable met branch is left, as the finding says.
- **Category:** other (redundant loc)
- **Where:** `te_system_tab_met_tt` (:8547), `te_window_tab_met_tt` (:8565), `te_market_tab_met_tt` (:8047), all "#b Not open yet#!\nIts conditions are met, but its journal entry is not running. It opens at the journal's next check, unless it has already run its course."
- **Proposed:** the window and Market tabs point at `te_system_tab_met_tt` and the two copies go, so a later wording pass edits one string. Tests pin the names (`test_te_systems_window.py:301-306`, `test_global_warming_layout.py`), so update them in the same change. Also, the Demographics tab's tooltip carries the met branch although `pops_overview.gui:168` notes it can't be reached; harmless.
- **Effort:** medium (GUI + tests)
- **Confidence:** high

### NAT-1. The country panel drops 249 modifiers with no word about where they went
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). `gen_nation_tab.py` writes a third MOD block under the list: "Lasting modifiers not listed: N" while the count is above 0, with a `button_icon_goto` (the tab, then the window) for `Country.IsLocalPlayer`; another country's line has no goto and its own hover, since vanilla's Modifiers tab is shown only for the player. The header keeps vanilla's test (the list or the line shows whenever the country has a modifier). The hover also names the Budget panel's Breakdown tab, since the money carriers are hidden there, not on the Nation tab.
- **Category:** hidden info
- **Where:** `gui/00_te_country_panel_information.gui:1004-1032` (the `### MOD: Nation tab` blocks, written by `scripts/generators/gen_nation_tab.py`), filter `te_nation_hidden_filter` (`gui/te_nation_generated.gui:8`, 249 names), count `gui_country_hidden_modifier_count`.
- **Now:** the Information tab's MODIFIERS list skips every modifier the Nation tab shows, and the header goes too when nothing else is left. A player who remembers a space-race reward in that list ("First on the Moon", `sr_first_moon_landing`) finds it gone, and nothing on the panel says the Nation tab exists. The launcher is a small sidebar button. For a foreign country the same modifiers show nowhere but in breakdowns. The spec accepted that ("until a later version lets the tab show the viewed country", spec § 3), so this finding doesn't reverse it.
- **Proposed:** one generated line under the list, in the same MOD block, shown while `gui_country_hidden_modifier_count` > 0:
  - viewing your own country: a `#tooltippable` line "Lasting modifiers: [count] on the Nation tab", whose onclick sets `te_systems_window_tab` to `nation` and then `com_open_window` (rule 9's goto, as the state view's Grand Monument card does). Tooltip: "Your permanent rewards, memberships and policies are summed by kind on the Nation tab of the Timeline Extended window."
  - viewing another country: the same line without the button, "Lasting modifiers: [count], in the breakdowns of the Modifiers tab".
  The header's `visible` would then keep the header up whenever either line shows. That way the list stays tidy and nothing disappears without a trace.
- **Effort:** medium (generator block + two loc keys; `test_nation_tab.py` checks the MOD blocks, so extend it)
- **Confidence:** high on the fact, medium on the wording

### NAT-2. The tab's own list of what the country holds sits collapsed, with no count
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The header reads `te_nation_sources_header_count` ("Where These Come From: N", spliced); the tab's hover is reworded as proposed.
- **Category:** hidden info
- **Where:** `te_nation_sources_panel` (`gui/te_nation_tab.gui:622-735`), header `te_nation_sources_header` "Where These Come From" (`te_miscellaneous_l_english.yml:8231`); tab tooltip `te_window_tab_nation_tt` (:8567).
- **Now:** the tab's hover promises "the permanent rewards, memberships and policies the country panel's modifier list leaves out", but the only place that names them (icon + name, the modifier's own tooltip) is a collapsed section at the foot. Two of them carry no field and so are in no type row's breakdown either: `cr_cooptation_expired` ("Cooptation Has Run Its Course") and `te_inflation_band_comfort` ("Inflation: Stable Prices"). The collapsed default is the owner's ruling (spec § 10, 2026-10-18: "Keep them, collapsed, in one panel at the bottom"), so this finding doesn't propose reopening it.
- **Proposed:** keep it collapsed, but give the header its count, in "Label: value" form: a new key `te_nation_sources_header_count` "Where These Come From: [GetPlayer.MakeScope.ScriptValue('te_nation_lists_count')|0]" on the `section_header_button` (`te_nation_sources_header` stays for its two `$…$` uses in How). The count is already computed for the panel's gate. Then reword the tab tooltip to promise what the open part shows: "Your standing scores, and what your permanent rewards, memberships and policies add up to, kind by kind. The country panel's modifier list leaves these out."
- **Effort:** medium (one GUI line, one new key) + quick (tooltip)
- **Confidence:** medium

### NAT-3. The overview's tooltips define the term and point down, instead of giving the reading's cause
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The five hovers take Banking's shape with the cause under the divider: the capacity's breakdown (plus the authority shortfall when it applies), the ceiling's sources (and a line before the score starts), where the target's terms are (the Demographics tab under its rule, else the terms named), the GDP part and the share that applies, and the spread. The caption "Global Tech" stays, as a short label with the full name now on hover (rule 3, option 2).
- **Category:** spread-out / style
- **Where:** `te_nation_ov_override_tt`, `te_nation_ov_wc_tt`, `te_nation_ov_construction_tt`, `te_nation_ov_tech_tt`, `te_nation_ov_jud_tt` (`te_miscellaneous_l_english.yml:8194-8213`), on `te_nation_ov_cell` (`gui/te_nation_tab.gui:240-325`).
- **Now:** each cell's hover is a definition plus a pointer: "How freely the courts can rule without fear of the government, and the ceiling your court law sets. The Governance section below has the ceiling's sources and what the courts give now." Three of the five captions are already concept links (`[Concept('concept_judicial_independence','Judiciary')]`…), so the definition is there twice. Every cell then repeats its section's first row word for word ("Judiciary / Gaining / 45 → 70" over "Judicial Independence: 45 → 70"), so the overview adds no information that isn't already one screen down. Banking's cells, the exemplar, read `#header Name#!` + one line + `$TOOLTIP_DELIMITER$` + what is pushing the figure (`banking_dash_momentum_tt`, `banking_dash_budget_tt`).
- **Proposed:** give each cell Banking's shape, with the cause in place of "see below" (every expression below already renders in the Nation rows, in the same GetPlayer context):
  - Judiciary: `#header $concept_judicial_independence$#!\nRises 4 a year toward its ceiling, falls 10 a year above it.\n$TOOLTIP_DELIMITER$\n[SelectLocalization( GreaterThan_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_nation_jud_paper'), '(CFixedPoint)0' ), 'te_nation_jud_ceiling_paper_row', 'te_nation_jud_ceiling_row' )]`
  - Construction: `#header Construction Cost#!\n` + the first sentence of `te_nation_construction_row_tt` ("Each construction point costs X of its base: Y from $construction_cost_scaling$ × Z from your other construction-cost modifiers.")
  - Override: `#header $concept_legislative_override_capacity$#!\nThe strongest $minor_events_timelineextended.2.t$ option open to you now.\n$TOOLTIP_DELIMITER$\n$te_nation_override_row$` (and `te_nation_override_short` when it applies)
  - Wealth: `#header $concept_inheritance_concentration$#!\nMoves toward its target each year.` + the target terms' pointer that `te_nation_wc_row_demog_tt` already carries
  - Global Tech: `#header $global_technological_development$#!\n` + the figure line. That also fixes the cell's caption "Global Tech", which is the only place the system goes by that name.
  Optional, and a bigger change: with the overview carrying each score's cause, the score's own "Label: value" row in its section could go, leaving the section's bar, ceiling line and list. That would reverse part of the spec's layout (owner, 2026-10-17), so only mention it.
- **Effort:** medium (loc only, but new composition: play-test the nested breakdown inside a cell tooltip)
- **Confidence:** medium

### NAT-4. Each score is explained three times: concept, row tooltip, How
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The Judicial Independence row lost its hover; How's Judiciary, Override and Wealth subsections point at their concepts and keep only what the concept lacks; the Global Tech row's hover keeps its figures and the overview's its reading. **No change** to the Algorithmic Mandate: its label has no concept, so the row's hover is the only live place its rule is written, and How's line is one sentence.
- **Category:** over-explaining (duplication)
- **Where:** `te_nation_jud_row_tt` (:8183) vs `concept_judicial_independence_desc` (`te_concepts_l_english.yml:836`) vs `te_nation_how_jud` (:8160); `te_nation_mandate_row_tt` (:8187) vs `algorithmic_mandate_desc` (`te_concepts_l_english.yml:233`) vs `te_nation_how_mandate` (:8162); `te_nation_how_override` (:8163) vs `concept_legislative_override_capacity_desc` + the three `te_nation_override_line_*_tt`; `te_nation_how_wc` (:8176) vs `concept_inheritance_concentration_desc`; `te_nation_tech_row_tt` (:8235) vs `te_nation_how_tech` (:8175) vs `te_nation_ov_tech_tt` (:8208).
- **Now:** e.g. `te_nation_how_jud`'s second sentence, "In proportion to the score the courts add [concept_legitimacy], lower the [concept_banking_credit_standing] premium, make Capitalists invest more and calm movements that lose a law change", is the concept's second paragraph word for word. The row tooltip's "rises 4 a year … falls 10 a year" is the concept's first paragraph. That concept sits on the row's own label. "Once any great power has researched certain modern technologies" appears in all three of the Global Tech texts.
- **Proposed:** let the concept on each label carry the definition (rule 3), and have the live tooltip say only what the label's concept can't: the reading.
  - `te_nation_jud_row_tt`: drop it (GUI: remove the `tooltip`), since the label's concept says all of it and the ceiling line sits right under the row. Or, as a loc-only step, cut it to its last sentence, "Forcing a law through spends some of it."
  - `te_nation_tech_row_tt` keeps its figures ("+20 for each of the first nine … +200 for each of the last nine, 54 in all"), and `te_nation_ov_tech_tt` is cut to the figure (NAT-3).
  - In How, each score subsection becomes one or two lines that add to the concept rather than repeat it (`te_nation_how_jud` → "Hover [concept_judicial_independence] for each court law's ceiling and what the courts give. The score is seeded at the first monthly update."). That is the "one line plus a nested concept" pattern the owner asked for.
- **Effort:** quick (loc), but it changes How text the owner may want self-contained, so it's not in Quick fixes
- **Confidence:** medium

### NAT-5. "Private Construction: excess in force"
- **Status:** **Done in #1202; no change needed since.**
- **Category:** style
- **Where:** `te_nation_private_row` (`te_miscellaneous_l_english.yml:8224`), `gui/te_nation_tab.gui:540-550`.
- **Now:** the value is a lowercase phrase that doesn't read as a value, and the list right under it names the modifier again ("Excess [concept_private_construction]", `too_much_private_construction`; or "Overinvestment").
- **Proposed:** "[concept_private_construction]: #v Excess#!". The label becomes the vanilla concept (rule 3), and the value is one word, like the overview's.
- **Effort:** quick
- **Confidence:** high

### DEM-1. The fertility tooltips promise figures the panel no longer shows
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The line is back in both hovers, under the capital's (the state's) terms, on `te_demog_lx_mab_sgui` / `te_demog_lx_state_mab_sgui`; the five keys left `te_unused`.
- **Category:** hidden info
- **Where:** `te_demog_ov_tfr_tt` (Fertility cell, `gui/te_demographics_widgets.gui:1127`) and `te_demog_st_tfr_tt` (the state's), both in `te_miscellaneous_l_english.yml`; the orphaned keys `te_demog_ov_tfr_mab` / `te_demog_st_tfr_mab` / `te_demog_ov_tfr_b50` sit in `te_unused_l_english.yml:683-685`; their gates `te_demog_lx_mab_sgui`, `te_demog_lx_state_mab_sgui`, `te_demog_lx_b50_sgui` (`common/scripted_guis/te_demog_lx_sguis.txt:149-180`) are referenced by no GUI or loc.
- **Now:** both tooltips say "…the figures above also show mean age at childbirth and births to women aged 50 and over". No figure above (or anywhere) shows them. `te_dg_mab` and `te_dg_lx_b50` are still computed every census, and their loc and gates still exist, but nothing reads them.
- **Proposed:** put the line back. In `te_demog_ov_tfr_tt`, between the capital block and the births line, add `[SelectLocalization( GetScriptedGui('te_demog_lx_mab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ), 'te_demog_ov_tfr_mab', 'te_demog_tfr_mab_pending' )]` (it chains `te_demog_ov_tfr_b50` itself), and the state's the same with `te_demog_lx_state_mab_sgui` / `te_demog_st_tfr_mab`. The "figures above" sentence then reads "Mean age at childbirth, below, follows the body under longevity care." Or, if dropping them was deliberate, delete the sentence and the orphaned keys and gates. Either way `organize_loc` moves the revived keys (all five, with `te_demog_tfr_mab_pending`) out of `te_unused`, so commit what it rewrites.
- **Effort:** quick-medium (loc + organize_loc churn)
- **Confidence:** high

### DEM-2. The fertility tooltip is the How section's Fertility text again, over the table that itemises it
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). Both hovers keep a title, one line (with "late marriage" and "birth spacing") and the figures; How's Fertility text gained family limitation's spread, births on top of the census and births following the body.
- **Category:** over-explaining
- **Where:** `te_demog_ov_tfr_tt` (1,816 characters) and `te_demog_st_tfr_tt` (1,606) vs `te_demog_how_fertility` (`te_miscellaneous_l_english.yml`); the term tables `te_demog_ov_tfr_capital` / `te_demog_st_tfr_terms` under them.
- **Now:** the cell's hover opens with a nine-sentence model ("Wealth sets how many children couples would have with nothing holding them back. Women's legal standing moves that, and two customs lower it: late marriage, … birth spacing, …"). Its first five sentences are `te_demog_how_fertility` almost word for word. Under it, the capital's table lists each of the same terms with its multiplier ("Wealth alone 4.1 / Women's legal standing ×0.95 / Late marriage ×0.88 …"). So the reader gets the model twice before reaching the numbers.
- **Proposed:** the tooltip keeps its title, one line and the tables:
  `#b Children per Woman#! [prev]\nThe children a woman would have over her life at this year's rates, weighted by the states' women aged 15 to 49. Each line below multiplies what wealth alone would give; late marriage and birth spacing are the two customs that hold births down.\n\n[capital block]\n\n[births line]`
  The four sentences How lacks (family policy and the hegemon's pull; family limitation's spread; births on top of the census) move into `te_demog_how_fertility`. **Test:** `test_demographics_registry.py:3927` requires "late marriage" and "birth spacing" (lower case) in all three keys and no "who marries"; the line above keeps both.
- **Effort:** quick (loc) but test-pinned, so not in Quick fixes
- **Confidence:** high

### DEM-3. How Demographics Works has no Work and Retirement or Longevity topic, so their rules live in the live tooltips
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). Both hosts' How gained Work and Retirement (three notes: the workforce, the pensions, and the fighting-age, youth-bulge and sex-balance rules spliced from their keys) and Longevity (three notes: care and the health laws, the augmentation laws and the gap's politics, backups and uploaded minds), after Causes of Death. Pension Age, Workforce, the Pension Bill, Fighting-Age Men, Youth, the Sex Balance's effects, Longevity Care, the Longevity Gap, Biological Age, Backed Up and Uploaded Minds now keep their title, a line and their figures.
- **Category:** over-explaining / structure
- **Where:** `te_demog_sec_how` (`gui/te_demographics_widgets.gui:4724-4845`): ten subsections (`te_demog_how_sub_census` … `_sources`), none for phases 2-3. The rules sit instead in `te_demog_wk_pension_age_tt` (its second paragraph, on linked pensions), `te_demog_wk_workforce_tt` ("in the game's units: the share of working age times…"), `te_demog_youth_rule`, `te_demog_sex_rule`, the `#lore` lines of `te_demog_ov_lx_care_tt` (which health law covers whom, the three augmentation laws), `te_demog_ov_lx_gap_tt` (the unions' reaction), `te_demog_ov_lx_bio_tt` (body vs calendar age) and `te_demog_ov_um_tt` ("Each Nexus level hosts a million minds…").
- **Now:** a player hovering Pension Age gets 680 characters on how Linked to Average differs from Linked to Common. Hovering Youth gets the bulge formula ("how far the young pass 18% of the people, full at 24%, times how far unemployment goes toward 20%…"), and hovering Sex Balance its whole schedule. These are How-it-works texts (rule 1), and they're the only place the rules are written.
- **Proposed:** add two subsections to both hosts' How (`te_demog_sec_how`, `te_state_demog_how`), each a new `te_demog_how_sub_*` / `te_demog_how_*` pair:
  - **Work and Retirement**: the workforce's units, the five pension positions and how the linked two follow old age, the pension and health bills, fighting-age men, the youth-bulge rule (`$te_demog_youth_rule$`), the sex-balance rule (`$te_demog_sex_rule$`);
  - **Longevity**: who reaches care under each health law, the market's price, the augmentation laws, biological vs calendar age, the gap's consequences, uploaded minds.
  The live tooltips then keep title + one line + their figures, so `te_demog_wk_pension_age_tt` becomes "#b Pension Age#!\nOur people may draw an old-age pension from this age; a setting holds for five years. Linked settings are heading for #v […link_target…]#! now."
- **Effort:** medium (new loc keys + two subsections in each How type; `test_demographics_layout.py` holds the How order)
- **Confidence:** high on the gap, medium on the split

### DEM-4. The Causes of Death pie's hover repeats the table beside it
- **Status:** **Done in #1202; no change needed since** (the estimation note is on the Deaths column head).
- **Category:** redundant
- **Where:** `te_demog_cd_pie_tt` / `te_demog_st_pie_tt` (pie at `gui/te_demographics_widgets.gui:1274`, state at :5439) vs the legend rows `te_demog_cause_row` beside the pie (deaths and share per cause) and the Deaths column head `te_demog_dc_head_deaths_tt`.
- **Now:** hovering the pie lists the seven shares ("Infection and Hunger: 41% …"), which the table 8 px to its right shows with deaths as well. Its `#lore` note on estimation is the Deaths column head's tooltip again.
- **Proposed:** the pie says only what the table doesn't, the total: see Quick fixes. The estimation note stays on the Deaths column head, one hover away.
- **Effort:** quick
- **Confidence:** high

### DEM-5. The pension buttons hand-write their interest-group reactions
- **Status:** **Done in #1202; no change needed since.** The `custom_tooltip` around each setting's effect is the setting change, not the modifier, and the hover now prints the modifier's own lines above it, so nothing is hidden. Play-test item 8 in `docs/testing/demographics-playtest.md` checks the lines render.
- **Category:** style (prose vs engine modifier lines)
- **Where:** `te_demog_pension_early_tt`, `_raised_tt`, `_linked_average_tt`, `_linked_common_tt` (`te_miscellaneous_l_english.yml:7291-7309`); the reactions are the static modifiers `te_demog_pension_pos_early` … `_linked_common` (`common/static_modifiers/te_demog_modifiers.txt:77-99`), applied by `te_demog_pension_ig_refresh`. The scripted GUIs' effects wrap the change in `custom_tooltip = { text = te_demog_pension_*_effect_tt … }`, so ExecuteTooltip never shows the modifier either.
- **Now:** "Trade Unions #G +2#! approval, Industrialists #R -1#!." is typed into each tooltip, in a format the engine's lines don't use. The Family Policy measures in the same panel use `[GetStaticModifier('te_demog_ms_child_allowance').GetDesc]`.
- **Proposed:** replace each hand-written line with the modifier's own: `[GetStaticModifier('te_demog_pension_pos_early').GetDesc]` (and so on), as the measures do. Then a change to the static modifier can't leave the tooltip stale. Standard's "No interest group reacts." stays. See Quick fixes.
- **Effort:** quick
- **Confidence:** high

### DEM-6. "N of our states have a youth bulge … each state's subtab shows its own": a list, not a hunt
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`), the full version. `te_demog_country_lists` builds `te_dg_yb_states` (the Youth count's own test, strongest first) and `te_dg_mt_states` (the Metropolis line, largest share first), up to ten each, so the civil-war repair redraws them too; Work and Retirement and Where People Live draw them under their rows on a new `te_demog_state_link_row`, which opens the state as the States table's rows do. The Metropolises count stays live, so it can run ahead of the list by up to a year (play-test item 5).
- **Category:** list
- **Where:** `te_demog_ov_youth_tt` (the Youth row, `gui/te_demographics_widgets.gui:4995-5005`), `te_demog_mt_pl_tt` / `te_demog_mt_pl_value` (Metropolises "3 of 21", :2995), `te_demog_wc_top` / `te_demog_wc_bottom` (one state each).
- **Now:** the Youth row gives a count ("#v 4#! of our states have a youth bulge") and sends the player to open states one by one ("Each state's Demographics subtab shows its own"). Metropolises does the same with four counts by label ("Each state's share … is on its Demographics subtab"). The States table, the exemplar this panel already has, solves exactly that.
- **Proposed:** a short list under each row, in the States table's form (`te_demog_state_row`'s button: click opens the state on its subtab):
  - **Youth bulge**: in `te_demog_country_lists` (`common/scripted_effects/te_demog_effects.txt:1675`), next to `te_dg_states_top`, build `te_dg_yb_states` with `ordered_scope_state = { limit = { te_demog_youth_bulge_shown > 0 } order_by = te_demog_youth_bulge_shown max = 10 … }`; rows: state, aged 20–29 share (`te_demog_youth_share`), strength (`te_demog_youth_bulge_shown`). The Youth row's tooltip then drops its pointer sentence.
  - **Metropolises**: the same with `limit = { has_variable = te_dg_mt var:te_dg_mt >= te_demog_k_mt_metropolis }` (the test `te_demog_mt_count_metropolis` already uses, `te_demog_metro_values.txt:459`), ordered by `var:te_dg_mt`; rows: state, its largest city's share.
  A cheaper version with no new script: a datamodel over the existing `te_dg_states` (40 largest) with each item gated on the state-scoped `te_demog_state_youth_sgui`. That misses a bulge outside the 40, so say "of the 40 largest". Variable lists aren't inherited by a revolution's winner, but `te_demog_country_lists` is already in the civil-war repair (`test_the_civil_war_repair_redraws_the_lists`).
- **Effort:** medium (one list in an existing refresh + a datamodel each) / large for both with a new row type
- **Confidence:** medium (the youth list is the clear win)

### DEM-7. When the census is taken is told three ways, one of them wrong
- **Status:** **Done in #1202; no change needed since** (checked: game start, then each country's and each state's yearly pulse).
- **Category:** style / accuracy
- **Where:** `te_demog_tab_first_census_tt` (the greyed tab's checklist line, `te_miscellaneous_l_english.yml:7696`), `te_demog_ov_census_tt`, `te_demog_pending`, `te_demog_st_pending`.
- **Now:** the checklist says "It is taken at the turn of each year"; the overview says "at the start of the game and then once a year, each country on a day of its own" (the yearly pulse, `te_demog_effects.txt:1747`, and game start, :505); the state says "on a day of its own". The census overview line's tooltip also opens with the count method ("Each state counts its people by single year of age and by sex, scaled to the state's real population…"), which is `te_demog_how_census`'s text.
- **Proposed:** see Quick fixes. The checklist line becomes "Your first census has been taken (at the start of the game, or within a new country's first year)", also a WIN-1 fix. A country that appears mid-game is first counted at its yearly pulse. The census line's tooltip drops the method sentence, which is in How → The Census.
- **Effort:** quick
- **Confidence:** high

### DEM-8. Small consistency points
- **Status:** **Done** (2026-10-27 wave, branch `wave/gui-demog`). The first two points were #1202's. The largest cities' rows are built on `te_demog_state_link_row` (a button with the States table's onclicks, highlight and menu, the figure now `|K`); Most and Least Concentrated have a goto in their trend slot, its datacontext under the rows' gate. The Gini's dash note shows only on the pending branch. The youth-bulge and more-men lines print radicals and turmoil red, and the state's lines name the modifier its Modifiers section lists.
- **Category:** style / redundant
- **Where / Now / Proposed:**
  - `te_demog_ov_wc_tt` is the hover of the "Score → Target" row **inside** the Wealth section (`gui/te_demographics_widgets.gui:2684`), yet ends "Wealth, below, shows what sets the target." The terms are the very next block. Quick fix: "The terms below set the target."
  - `te_demog_state_row_tt` repeats the row's own Life column ("Life expectancy: … years"). The comment over the type says the tooltip is for "the sex balance and Wealth Concentration the table's columns gave up". Quick fix: drop the line.
  - The Largest Cities rows (`te_demog_city_row`) and Most / Least Concentrated (`te_demog_wc_top` / `_bottom`) name a state but can't be clicked, while every States-table row opens its state. Make `te_demog_city_row` a `button` with `te_demog_state_row`'s two onclicks and map highlight (GUI only).
  - `te_demog_gini_tt` always ends "#grey A dash means this country has no Gini yet…", including once a Gini exists. Pick it by `te_demog_gini_ready_sgui` as the value already is.
  - The census-driven effect lines `te_demog_ov_sex_more`, `te_demog_ov_sex_fewer`, `te_demog_youth_effects`, `te_demog_st_youth_effects` print "radicals from movements +#v 12%#!, effects of turmoil +#v 8%#!" in the neutral value colour. Rule 5 wants a bad figure red. On the state subtab the same effects render properly, coloured, in its Modifiers list ("Census: Youth Bulge"), so the state's line can point there instead of restating them.
- **Effort:** quick (first two in Quick fixes) to medium
- **Confidence:** high

## Applied in this PR

41 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`gw_entry_unlock_tt`, `st_res_entry_unlock_tt`, `te_budget_tab_banking_tt`, `te_demog_cd_pie_tt`, `te_demog_ov_census_tt`, `te_demog_ov_wc_tt`, `te_demog_pension_early_tt`, `te_demog_pension_linked_average_tt`, `te_demog_pension_linked_common_tt`, `te_demog_pension_raised_tt`, `te_demog_st_pie_tt`, `te_demog_state_row_tt`, `te_demog_tab_first_census_tt`, `te_diplomacy_tab_un_tt`, `te_diplomacy_un_open_journal_tt`, `te_market_global_warming_open_journal_tt`, `te_market_strategic_reserve_open_journal_tt`, `te_market_tab_global_warming_tt`, `te_market_tab_strategic_reserve_locked_tt`, `te_market_tab_strategic_reserve_tt`, `te_military_covert_open_journal_tt`, `te_military_nuclear_open_journal_tt`, `te_military_tab_covert_tt`, `te_military_tab_nuclear_tt`, `te_nation_private_row`, `te_seabed_unlock_coast_tt`, `te_seabed_unlock_tech_tt`, `te_society_ch_open_journal_tt`, `te_society_tab_ch_tt`, `te_systems_window_launcher_tt`, `te_tax_open_journal_tt`, `te_tax_tab_full_tt`, `te_tax_tab_light_tt`, `te_window_colonial_empire_open_journal_tt`, `te_window_grand_monuments_open_journal_tt`, `te_window_space_race_open_journal_tt`, `te_window_tab_colonial_empire_tt`, `te_window_tab_grand_monuments_tt`, `te_window_tab_seabed_locked_tt`, `te_window_tab_space_race_locked_tt`, `te_window_tab_space_race_tt`
