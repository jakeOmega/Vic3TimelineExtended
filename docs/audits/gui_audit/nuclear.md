# Nuclear weapons — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Slice: `je_nuclear_program` ("Nuclear Weapons") and the Military panel's Nuclear tab. Files read:
`gui/journal_entry_widgets/nuclear_{layout,overview,program,deterrence}_widget.gui`, the Nuclear blocks of
`gui/panel_military.gui` (lines 628-657, 724-807), `common/scripted_guis/nuclear_{program,deterrence}_sguis.txt`,
`common/journal_entries/je_nuclear_program.txt`, the effects/triggers/values/custom loc they call
(`nuclear_deterrence_effects.txt`, `nuclear_crisis_effects.txt`, `nuclear_deterrence_triggers.txt`,
`nuclear_deterrence_values.txt`, `nuclear_{deterrence,program}_custom_loc.txt`, `nuclear_deterrence_modifiers.txt`,
`nuclear_taboo_modifiers.txt`), every loc key those render (all 283 keys the four .gui files name resolve; no raw
keys), the concepts, `test_nuclear_layout.py` and `test_nuclear_deterrence.py`.

The Military tab composes exactly the journal entry's types (`te_nuclear_overview_panel`, `te_nuclear_sec_programme`,
`te_je_goal_bar`, `te_nuclear_status_sections`, `te_nuclear_reference_sections`), so every finding below applies to
both hosts; nothing is reachable in only one of them. The JE status text is empty while active (`nuke_line_empty`),
as rule 1 wants.

All 21 findings are done in the 2026-10-27 GUI audit wave (each finding's Status line says how; play-test list `docs/testing/nuclear-playtest.md`).

## Top priorities

- **Make the hovers findable and stop doubling them.** No row label, choice name or stepper label in the panel is
  `#tooltippable`, although they carry the panel's richest hovers (pressure and danger breakdowns, the taboo's
  breakdown, technology lists, each option's modifier lines); and every choice row has two hovers that say much the
  same (name + button). NUC-1, NUC-2.
- **Posture: one row per axis, the action beside it, and say when it can change.** The current doctrine, readiness
  and authority are shown twice (overview row 2 and Posture rows 1-3), their tooltips restate the concept descs, the
  choices sit in collapsed subsections (one of them mixing two axes), and the "months until next change" values
  already exist in script but are never drawn. NUC-3, NUC-4.
- **Readiness levels as a comparison table, and modifiers instead of prose for Recessed, Routine and the four launch
  authorities** (Heightened and High Alert already render modifier lines; IG reactions are mentioned for some options
  and silently omitted for others). NUC-5, NUC-6.
- **Crisis: compact the eleven stacked lines and bring Our Moves up to them**, label the cryptic "Our stakes"
  numbers, and drop the move-name tooltips that repeat the buttons' effect previews. NUC-7, NUC-8, NUC-9.
- **Remove figures shown twice or three times** (warheads, credibility, the taboo score/target), and fix the taboo
  "Heading toward" row, which colours the change green/red against the system's own neutral-colour rule. NUC-11,
  NUC-12, NUC-13.
- **Lists:** the Nuclear Powers leaderboard and World Crises are fixed slot rows of script-built text; a datamodel
  table (flag, estimate, public doctrine) would read far faster. NUC-14.

## Findings

### NUC-1. No hoverable text in the panel is marked hoverable
- **Status:** Done (the 2026-10-27 wave). `nd_choice_row` is a widget type whose name textbox carries a `name_format` block (`#tooltippable`, overridden empty for the crisis moves, which keep no name hover after NUC-2); the readiness table's level names and the four tooltipped stepper values are underlined too. The row labels were done in #1202.
- **Category:** hidden info
- **Where:** `gui/journal_entry_widgets/nuclear_deterrence_widget.gui:117-144` (`nd_row`: label textbox
  `alwaystransparent = yes`, no `default_format`), `:195-217` (`nd_home_term_row`), every `nd_choice_row` name
  textbox (e.g. `:1050-1058`, `:674-682`), stepper labels (`:1569-1577`, `:1604-1612`, `:1658-1666`);
  `nuclear_program_widget.gui:109-136` (`nuclear_program_row`), `:151-159` (funding label). Only the overview's
  three textboxes carry `default_format = "#tooltippable"` (`nuclear_overview_widget.gui:66,93,239`).
- **Now:** "Pressure on the target 55 / 100", "Danger Tense (45)", "Nuclear taboo 62 — Strong", "Delivery capability
  60%", "No First Use [Adopt]" all have substantial hovers (`nd_w_crisis_pressure_tt` + the
  `nd_crisis_pressure_breakdown_sgui` part list; the taboo target breakdown; the technology lists of
  `je_nuclear_program_widget_delivery_tt`; each doctrine's `GetStaticModifier(...).GetDesc`), but nothing tells the
  player they exist. Sibling panels mark theirs (covert: 16 uses, banking 21, cultural hegemony 24, UN authority 10).
  Rule 3: "Hoverable text is underlined (`#tooltippable`)."
- **Proposed:** add `default_format = "#tooltippable"` to the label textbox of `nd_row`, `nuclear_program_row` and
  `nd_home_term_row` (the row's own tooltip stays on the flowcontainer; the label can stay `alwaystransparent`), to the
  name textbox of every `nd_choice_row` instance (better: give `nd_choice_row` a name-textbox block so the 21
  instances stop repeating `size`/`align`/`using`), and to the four stepper value textboxes that carry a tooltip
  (`nd_w_safeguards_value`, `nd_w_hardening_value`, `nd_taboo_w_ceiling_value`,
  `je_nuclear_program_widget_funding_value`).
- **Effort:** medium (GUI tweak, a few lines in five types). `default_format` is markup, not loc text, so
  `LabelBudgetTest`'s widths are unaffected.
- **Confidence:** high

### NUC-2. Every choice row has two hovers covering the same ground, and the name's hover holds unique content
- **Status:** Done. The readiness names drop their upkeep and survivability lines (the readiness table shows both, NUC-5), Automatic Retaliation drops its Extra upkeep line (the button's preview has it), and the five crisis moves lose their name hovers: each move's one hover is its button's, the conditions and then what it does. The moves' flavour keys are deleted; the previews already said everything in them.
- **Category:** spread-out/redundant, hidden info
- **Where:** Posture choices `nuclear_deterrence_widget.gui:1048-1361`; crisis moves `:671-779`. Loc: `nd_w_doctrine_choice_N_tt`
  vs `nd_tt_doctrine_adopted_N` (`te_miscellaneous_l_english.yml:5371-5379` vs `:5155-5159`); `nd_w_readiness_choice_N_tt`
  vs `nd_tt_readiness_target_N` (`:5404-5410` vs `:5257-5260`); `nd_w_authority_choice_4_tt` vs
  `nd_tt_authority_consequence_automatic` (`:5306` vs `:5121`); `nd_w_crisis_act_*_tt` (`:5319-5331`) vs the button's
  `ExecuteTooltip` of `nd_crisis_act_*` (`nuclear_crisis_effects.txt:1561-2056`).
- **Now:** hovering "No First Use" shows the flavour line plus `[GetStaticModifier('nd_doctrine_mod_1').GetDesc]`;
  hovering its Adopt button shows the same `GetDesc` again inside `nd_tt_doctrine_adopted_1`. For readiness the name
  hover is the **only** place the Heightened/High Alert modifier lines and "Survivability a crisis counts" appear,
  while "Upkeep at this level" is printed in both. For Automatic Retaliation the red warning and the extra upkeep are
  in both. For the crisis moves the name hover is a vaguer paraphrase of the button's concrete preview: "A public
  ultimatum: a clearer signal, a shorter deadline, and a commitment we cannot quietly walk away from" vs the button's
  `nd_tt_go_public_terms` "The crisis becomes a Confrontation with a new deadline 8 weeks from now. From here, backing
  down costs 15 credibility instead of 5...".
- **Proposed:** one job per hover. Name (marked, NUC-1) = what the option *is*: one flavour line + its modifier lines
  + per-option figures. Button = `IsValidTooltip` + what pressing it changes (unchanged; the `nd_tt_*` effect lines
  are shared with events such as `nuclear_taboo_events.txt:80` and `nuclear_incident_events.txt:234`, so they keep
  their `GetDesc`). Concretely: drop the trailing "Upkeep at this level" line from `nd_w_readiness_choice_N_tt` (the
  button and the table of NUC-5 show it), and drop the "Extra upkeep" line from `nd_w_authority_choice_4_tt`. For the
  five crisis moves, remove the name's `tooltip` (the button preview is complete: modifiers such as `nd_exercise_cost`
  render as engine lines there), or fold the one flavour sentence in front of the `IsValidTooltip` so there is a
  single hover per move.
- **Effort:** quick for the loc trims, medium for the GUI (remove five `tooltip =` lines).
- **Confidence:** high (the duplication); medium on which hover should keep the flavour line.

### NUC-3. The posture is shown twice, its tooltips restate the concepts, and its actions are far from it
- **Status:** Done, option (a). Each axis is an `nd_axis_row`: its label a concept (not alwaystransparent, so the concept hovers), what is in force (underlined; its hover the posture's modifier lines in force and when it can next change), and a Change / Hide toggle that opens the axis's choices directly beneath it. Three flags, `nd_doctrine_open`, `nd_readiness_open`, `nd_authority_open`; the mixed subsection is gone. The overview's cells use the same hovers, now live rather than restating the concepts. `FlagTest` pins the three toggles.
- **Category:** spread-out/redundant, over-explaining
- **Where:** overview row 2 `nuclear_overview_widget.gui:257-393` and Posture rows `nuclear_deterrence_widget.gui:934-966`,
  both using `nd_w_doctrine_tt`, `nd_w_readiness_tt`, `nd_w_authority_tt` (`te_miscellaneous_l_english.yml:5383,
  5413, 5309`); concepts `concept_nuclear_doctrine_desc`, `concept_nuclear_readiness_desc`,
  `concept_launch_authority_desc` (`te_concepts_l_english.yml:847, 851, 838`); subsections "Change Doctrine"
  (`:1016-1153`, flag `nd_doctrine_open`) and "Change Readiness or Launch Authority" (`:1156-1362`, `nd_forces_open`).
- **Now:** the three current values appear in the overview (icon + name) and again as the first three Posture rows,
  with the same tooltips. Those tooltips are the concept descs reworded: `nd_w_doctrine_tt` "When we say we will use
  nuclear weapons. It decides which strikes our government may order ... Retaliation is always permitted. A pledge of
  no first use can only be left by repudiating it." vs `concept_nuclear_doctrine_desc` "When a country says it would
  use nuclear weapons ... It decides which strikes its government may order ... Retaliation is always permitted, and a
  pledge of no first use can only be left by repudiating it." The same text a third time in `je_nuclear_how_posture`.
  The row labels "Doctrine", "Readiness", "Launch authority" are plain text, not the concepts (rule 3). To change
  launch authority the player opens a subsection that starts with readiness's four rows and two legends.
- **Proposed:** (a) Posture's first three rows become the axis rows, each "Label: value" with the label a concept
  (`[Concept('concept_nuclear_doctrine','Doctrine')]`, etc.; the label textbox must stop being
  `alwaystransparent` for the concept to hover) and a small "Change" toggle at the right end of the row that opens
  that axis's options directly beneath it (rule 6: the button beside the item). Split the mixed subsection into
  "Readiness" and "Launch Authority" (three flags: `nd_doctrine_open`, `nd_readiness_open`, `nd_authority_open`).
  (b) Cut `nd_w_doctrine_tt` / `_readiness_tt` / `_authority_tt` to what is live (when it can change, NUC-4; the
  readiness step under way) plus the concept, e.g. `nd_w_doctrine_tt`: "#tooltip_header Doctrine#!\n$TOOLTIP_DELIMITER$\nOur
  [concept_nuclear_doctrine] in force. [NUC-4 next-change line]". The overview's cells keep the same hover, so they
  shrink too. (c) Optionally drop the three rows and let each subsection header read "Doctrine: No First Use ▸",
  since the overview already shows the values.
- **Effort:** medium. `test_nuclear_layout.FlagTest.test_subsections_are_nested` pins `nd_doctrine_open` and
  `nd_forces_open`; `LabelBudgetTest.test_table_rows` will re-check the label widths.
- **Confidence:** high (duplication), medium (layout).

### NUC-4. "When can I change it?" is computed but never shown
- **Status:** Done. `nd_display_*_months_left` and `nd_display_readiness_lock_months` now print in a live line above each list (`nd_w_doctrine_legend` and its siblings, a `SelectLocalization` between "can be changed again in N months" and "can be changed now"), in each axis row's hover and in the overview's Doctrine and Launch Authority cells.
- **Category:** hidden info
- **Where:** `common/script_values/nuclear_deterrence_values.txt:1109-1134` (`nd_display_doctrine_months_left`,
  `nd_display_authority_months_left`, `nd_display_readiness_lock_months`) — referenced by no .gui, loc or script.
  Legends `nd_w_doctrine_legend`, `nd_w_readiness_legend`, `nd_w_authority_legend` (`te_miscellaneous_l_english.yml:5382,
  5412, 5308`); trigger lines `nd_tt_doctrine_tenure`, `nd_tt_authority_tenure`, `nd_tt_readiness_locked`
  (`:5162, 5122, 5254`).
- **Now:** "A doctrine can be changed once every two years." and, on every greyed Adopt button, a cross on "Our
  doctrine has been in force at least two years" — but not how long is left. A stand-down lock on readiness likewise
  says neither that it is on nor for how long.
- **Proposed:** make the said-once line above each list (rule 6) live: "Can be changed again in #v N#! months" when
  the value is above 0, "Can be changed now" otherwise (a `SelectLocalization` on
  `GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('nd_display_doctrine_months_left'),
  '(CFixedPoint)0' )` — but see the op-code caveat in NUC-5 — or a two-text custom-loc block). The same line belongs in
  the axis row's tooltip (NUC-3b). Readiness: "Held at Routine or below for #v N#! more months by a stand-down" while
  `nd_display_readiness_lock_months` > 0. Drop the tech sentence from `nd_w_authority_legend` (quick fix below): each
  Adopt button's `IsValidTooltip` already lists it (`nd_tt_need_radar` / `_icbms` / `_computers`,
  `nuclear_deterrence_sguis.txt:105-124`), and rule 6 says per-row reasons belong there.
- **Effort:** medium (custom loc or GUI conditional; values exist).
- **Confidence:** high

### NUC-5. Readiness levels should be a comparison table, and the current option of each list is not marked
- **Status:** Done. Readiness is a four-row table under a head (`nd_readiness_row`: level, weekly upkeep there, the survivability a crisis would count there, Order). Every list tints its option in force, as Covert's Funding Levels do; readiness tints the level ordered (`nd_display_readiness_target_code`, new), the one its Order button greys. The op-code caveat was the test's, not the panel's: `test_nuclear_deterrence.gui_ops` now counts only `AddScope( 'op', … )` literals, so a tint's code is not read as an op, and no display sguis were needed.
- **Category:** list, hidden info
- **Where:** readiness rows `nuclear_deterrence_widget.gui:1188-1271`; doctrine `:1048-1152`; authority `:1278-1361`.
  Figures per level already exist: `nd_upkeep_weekly_at_readiness_N` and `nd_effective_survivability_at_readiness_N`
  (read in `nd_w_readiness_choice_N_tt`).
- **Now:** to compare what Recessed/Routine/Heightened/High Alert cost and how much survivability a crisis would count
  at each, the player hovers four names one after another. In none of the three lists is the option in force
  distinguished, except that its button is greyed with "This is not already our choice" (`nd_tt_already_current`).
- **Proposed:** a four-row table under a header row: Level (name, hover = NUC-2's "what it is") | Upkeep/wk
  (`@money!` + `GetPlayer.MakeScope.ScriptValue('nd_upkeep_weekly_at_readiness_N')|D`) | Survivability counted |
  [Order]. Widths: 150 + 90 + 70 + 110 + gaps ≈ 440 in the 480 column. Tint the row in force, as Covert's Funding
  Levels table does (`covert_operations_widget.gui:278-281`, `row_current`), and do the same for doctrine and
  authority. Caveat recorded in the file header (`:59-64`, `:1416-1418`): a `(CFixedPoint)` literal after the first
  action row is miscounted as an op code by `test_nuclear_deterrence.gui_ops`, so the "is this row current" test must
  go through scope-free display sguis (the pattern of `nd_crisis_we_issued_sgui`) or compare two script values, as
  the survivability bar does.
- **Effort:** medium-large (new row type, 13 small sguis or a parametrised display value pair).
- **Confidence:** medium

### NUC-6. Prose where siblings render modifiers: Recessed, Routine and every launch authority; IG reactions told for some options only
- **Status:** Done. Twelve `script_only` display types (`common/modifier_type_definitions/nuclear_deterrence_display_types.txt`) carried by eight static modifiers nothing adds (`nd_readiness_terms_0..3`, `nd_authority_terms_1..4`; `_terms_`, since `nd_readiness_mod_0` must not exist). Readiness prints custody cost, the everyday incident rate against Routine (x0.5 / x4 / x10, as exact relative factors: the Recessed tooltip already disclosed "half as likely", and a factor is not a probability), crew strain a month, danger in our crises and the pressure our threats exert; launch authority prints its rules as boolean lines, plus the halt chance and custody loss. The doctrine choices keep their own modifiers. No option names the interest groups' reactions any more (option c, dropping them). `TestPostureTerms` holds every figure to the script's.
- **Category:** style, hidden info
- **Where:** `nd_w_readiness_choice_0_tt`, `_1_tt` (`te_miscellaneous_l_english.yml:5404, 5406`) vs `_2_tt`, `_3_tt`
  (`:5408, 5410`, which embed `[GetStaticModifier('nd_readiness_mod_2'/'_3').GetDesc]`);
  `nd_w_authority_choice_1..4_tt` (`:5300-5306`); static modifiers `nuclear_deterrence_modifiers.txt:81-91` (only
  readiness 2 and 3 have one).
- **Now:** Recessed is a paragraph: "custody costs half, incidents are half as likely as at Routine, and a crisis with
  us is less dangerous — and the least usable: nothing can be launched ... A threat we make is taken less seriously.
  Restraint-minded groups approve; the officers do not." Heightened and High Alert show engine-coloured modifier
  lines but describe their real costs (strain, incidents, upkeep) only as "at a manageable cost in money and fatigue".
  IG reactions: No First Use says "popular with those who fear the bomb", Recessed and Automatic Retaliation name the
  groups, but Launch on Warning (which restraint groups also dislike, −1, per `concept_posture_restraint_desc`), High
  Alert (militarist +1, restraint −1), Compellence and Warfighting say nothing.
- **Proposed:** (a) Add display-only `script_only = yes` modifier types for the effects script applies itself, with
  loc in `te_modifiers_l_english.yml`, e.g. `country_nd_custody_cost_mult` (Recessed −50%),
  `country_nd_incident_rate_mult` (Recessed −50%, using the "half as likely" the tooltip already discloses; keep the
  higher levels to the band words if `nuclear_crisis_design.md` §10 "no fake precision about hidden risk" rules out
  figures), `country_nd_crew_strain_monthly_add` (Heightened/High Alert), `country_nd_threat_weight_mult`. Give
  Recessed and Routine their own `nd_readiness_mod_0` / `_1` (Routine may be empty, or carry nothing and say "the
  baseline"), so all four tooltips read: one flavour line + `GetDesc` + the two figures. (b) Launch authority's
  effects are rules, not numbers, so keep them as one red rule line each, but in one shape: flavour line, then the red
  line (`#R An incident can end in a launch without further approval.#!` for 2 and 3, the automatic answer for 4).
  (c) IG reactions: either drop them from every option (At Home and the four `concept_posture_*` descs already list
  them all) or give every option the same last line, e.g. "At home: [Concept('concept_posture_restraint','Restraint')]
  −1, [Concept('concept_posture_militarist','Militarist')] +1". Dropping is simpler and loses nothing.
- **Effort:** medium (modifier types + static modifiers + loc; the new modifiers are display-only, never added).
  Note `test_nuclear_deterrence.py:666-669` pins `ScriptValue('nd_effective_survivability_at_readiness_N')` in each
  readiness tooltip.
- **Confidence:** medium-high

### NUC-7. The crisis is eleven stacked lines, with Our Moves below all of them
- **Status:** Done. A headline printed in our own scope ("Against France · we made the threat · over a war, in public", `nd_crisis_opponent_sgui`); the six readings as a grid of `nd_crisis_cell`s two to a row (Banking's cell shape without the icon box, since six readings have no art: caption, word, figure; the breakdowns on hover); Our Moves directly under the grid; then an Outcomes table (they / we concede, back down, both stand down: what happens and the credibility change, from new `nd_crisis_cred_if_*` blocks that mirror the outcome effects). Pressure gets a word (Firm, Wavering, Yielding, Breaking at its event's 50 / 70 / 85); the stage cell counts the crisis's week.
- **Category:** spread-out/redundant
- **Where:** `te_nuclear_sec_crisis`, `nuclear_deterrence_widget.gui:523-781`.
- **Now:** "Against France" (script line), then ten `nd_row`s: Our side · Over · Stage · Weeks to the deadline ·
  Danger · Pressure on the target · If they concede · Can we carry it out? · Next pressure · Our stakes; then the "Our
  Moves" subheader and up to four move rows. The opponent, our side and the dispute are three lines for one sentence;
  the two outcome rows ("If they concede", "Our stakes") are separated from the moves that produce those outcomes.
- **Proposed:** (1) One headline line from `nd_crisis_opponent_sgui`: "Against **France** · we made the threat · over
  a diplomatic play (private)" (in the opponent scope the line can read our side's words through
  `ROOT.GetCountry.GetCustom('nd_crisis_role_word')` / `'nd_crisis_dispute_word'`, as `nd_tt_bp_accept` reads
  `ROOT.GetCountry`; verify in game). (2) The six readings as a two-up grid in the Banking overview's cell shape
  (`te_banking_ov_cell`: caption, word, figure): Stage | Deadline (weeks); Danger | Pressure; Follow-through | Next
  pressure — breakdowns stay on hover. (3) Our Moves directly under the grid. (4) An "Outcomes" mini-table replacing
  "If they concede" and "Our stakes": If they concede · If we back down · Mutual stand-down, each with what happens
  and the credibility change (the texts already exist: `nd_concession_short_N`, `nd_stakes_long_*`).
- **Effort:** large (new layout; small sgui text change).
- **Confidence:** medium

### NUC-8. "Our stakes" is two bare numbers whose order flips with our side
- **Status:** Done. The stakes row is gone into the Outcomes table, whose Credibility column states each change on its own row, so the order cannot flip; the tooltip's header is "Credibility at Stake". The player guide's "your stakes" is rewritten.
- **Category:** hidden info
- **Where:** row `nuclear_deterrence_widget.gui:654-664`; `nd_stakes_short_target` / `_public` / `_private`
  (`te_miscellaneous_l_english.yml:4967-4969`) via `nd_crisis_stakes_short`.
- **Now:** "Our stakes: +15 / −15" (issuer: they concede / we back down) or "−5 / +10" (target: we concede / they back
  down). Nothing on the row says these are credibility, or which outcome is which, and the bad number comes first for
  a target but second for an issuer.
- **Proposed:** values "Win #G +15#! · Lose #R -15#!" (good outcome first for both sides; quick fixes below; 18
  characters, 170 of the 266 cell by `LabelBudgetTest`'s 8.6 × 1.1), and the label "Credibility at stake" (20
  characters, 189 of 210). The label change also wants `docs/player_guide/14-nuclear.md:47` ("your stakes") touched,
  so it is listed here rather than in Quick fixes.
- **Effort:** quick
- **Confidence:** high

### NUC-9. Crisis tooltips enumerate the general case beside the specific one
- **Status:** Done. The dispute's general case and "Stages are not a ladder to war" moved into How Nuclear Weapons Work → Crises; the headline's hover is the role and the public-ultimatum line; the Stage cell's hover is the next-stage line alone.
- **Category:** over-explaining
- **Where:** `nd_w_crisis_dispute_tt` (`te_miscellaneous_l_english.yml:5345`); `nd_w_crisis_stage_tt` (`:5365`);
  How-it-works crisis note `nd_w_crisis_actions_legend` (`:5332`).
- **Now:** the "Over" row's hover lists all five things any target might give up ("backing down in the diplomatic
  play, a collapse of war support in the war, leaving a guaranteed country alone, a frozen weapons programme, or its
  forces stood down"), two rows above "If they concede: Loses the play", whose hover already states this crisis's
  case (`nd_concession_long_N`). Its second paragraph repeats what the stakes row says about public ultimatums. The
  Stage hover's first sentence "Warning, confrontation, acute. Stages are not a ladder to war..." precedes the useful
  live line (`nd_stage_next_N`).
- **Proposed:** `nd_w_crisis_dispute_tt` → "#tooltip_header The Dispute#!\n$TOOLTIP_DELIMITER$\nWhat the threat is
  about, and whether it was made in public. A public ultimatum is a commitment: abandoning it is noticed at home and
  abroad." and move the five-way list into `nd_w_crisis_actions_legend` (How Nuclear Weapons Work → Crises), e.g.
  append "A crisis is over a diplomatic play, a war, a guarantee, a weapons programme or forces on alert; conceding
  means backing down in the play, losing 35 war support, leaving the protected country alone, a programme frozen for
  ten years or forces stood down for two." `nd_w_crisis_stage_tt` → header + `[...nd_crisis_stage_next]` only, with
  "Stages are not a ladder to war" moved to the same How-it-works note.
- **Effort:** quick (loc-only, two keys each; listed here because the two edits must land together)
- **Confidence:** medium-high

### NUC-10. Crisis move naming: four verbs for one move
- **Status:** Done. Concede's label is "Give them what they demand" (the loc part did Back down).
- **Category:** style
- **Where:** `nd_w_crisis_act_back_down` "Let the threat go", `_btn` "Back down", `_tt` "Abandon the threat",
  `nd_last_outcome_backed_down` "The threat was abandoned", `nd_stakes_long_*` "If we back down"
  (`te_miscellaneous_l_english.yml:5317-5319, 4913, 4964-4966`); player guide `14-nuclear.md:404` "Back down". Also
  "Concede" label + "Concede" button (`:5329-5330`).
- **Proposed:** "Back down" throughout: label "Back down from the threat" (quick fix below). For Concede, label "Give
  them what they demand" so label and button aren't the same word twice (or drop the label column for moves and widen
  the buttons, which NUC-2 makes the only hover).
- **Effort:** quick
- **Confidence:** medium-high

### NUC-11. The taboo score, target and direction are shown twice, and the section colours the direction
- **Status:** Done. One row, "Nuclear taboo: 62 → 68 · Strong" with the breakdown on hover; the Heading toward row, its colourless words and `nd_taboo_heading` are deleted.
- **Category:** spread-out/redundant, style
- **Where:** overview row 3 (`nuclear_overview_widget.gui:415-504`, "Taboo [bar] 62 → 68 (+0.4/mo) ↑") and the
  section's first two rows (`nuclear_program_widget.gui:313-335`, "Nuclear taboo: 62 — Strong", "Heading toward: 68
  (rising)"), all three with the same tooltip (`je_nuclear_program_widget_taboo_score_tt` + `nd_taboo_breakdown_sgui`).
  `nd_taboo_heading_up` "#G (rising)#!", `nd_taboo_heading_down` "#R (falling)#!" (`te_miscellaneous_l_english.yml:5007-5009`).
- **Now:** the overview's bar is deliberately neutral — its comment (`nuclear_overview_widget.gui:404-407`) and
  `je_nuclear_ov_taboo_bar_tt` say "It is pale either way, not green or red, because a stronger taboo is two-sided" —
  while two scrolls down the same movement is green when rising and red when falling.
- **Proposed:** quick fix: drop the colours from the two heading keys (below). Then merge the two section rows into
  one, "Nuclear taboo: 62 → 68 · Strong", or drop both and put the band name into the overview's hover header ("The
  Nuclear Taboo: Strong"); the section then opens with what the taboo costs us, which the overview lacks.
- **Effort:** quick (colours); medium (merge rows)
- **Confidence:** high

### NUC-12. Warheads appear three times, with the estimate explained three times
- **Status:** Done. The Forces section's Warheads held row moved into Arsenal Size, beside the ceiling: "12 (est. 10)" with " · treaty: N", " · UN ban: N" or " · dismantling" when they bind (`nd_taboo_arsenal_status` shortened; our own ceiling is the stepper's value); the old Arsenal status row folded into it. The estimate rule is said in the overview's hover and in How only; "Additional warheads add less and less…" moved to the ceiling's hover.
- **Category:** spread-out/redundant, over-explaining
- **Where:** overview cell + `je_nuclear_ov_warheads_tt` (`te_journal_entries_l_english.yml:606`); Forces row
  "Warheads held" + `nd_w_arsenal_tt` (`te_miscellaneous_l_english.yml:5297-5298`); How-it-works
  `je_nuclear_program_widget_powers_legend` (`te_journal_entries_l_english.yml:628`). Arsenal Size subsection
  (`nuclear_deterrence_widget.gui:1640-1753`).
- **Now:** "Warheads 12" (overview) and "Warheads held 12 (world estimate 10)" (Forces) each explain the yearly
  re-observation; the overview hover adds "Warheads are what a nuclear strike spends, one each; a disarmament
  settlement takes all of them", which is `concept_nuclear_stockpile_desc`. The Forces row sits at the top of Forces,
  while the ceiling and dismantling that act on the count are at its bottom.
- **Proposed:** keep the overview cell (hover trimmed, nesting the concept — quick fix below); move the Forces row
  into Arsenal Size above the ceiling stepper as "Arsenal: 12 (est. 10) · held to 20" by folding it into
  `nd_taboo_w_status_value`, and drop `nd_w_arsenal_tt`'s repeat of the estimate rule (its "Additional warheads add
  less and less to deterrence, and cost upkeep all the same" can move to the ceiling's hover).
- **Effort:** quick (loc) + medium (move a row)
- **Confidence:** high

### NUC-13. Credibility shown twice; it is used everywhere but is not a concept
- **Status:** Done. `concept_nuclear_credibility` ("Nuclear Credibility"), its desc the mechanics, with the pressure rule (every point above 50 adds half a point); 24 effect lines name it as `[Concept('concept_nuclear_credibility','credibility')]`. The Reputation row is dropped; the overview's Credibility cell gives a word (Doubted, Steady, Trusted) and the figure, its hover the figure, the word and what it adds to our threats.
- **Category:** spread-out/redundant, over-explaining
- **Where:** overview meter (`nuclear_overview_widget.gui:229-252`) and Reputation row (`nuclear_deterrence_widget.gui:1871-1881`),
  both `nd_w_credibility_tt` (`te_miscellaneous_l_english.yml:5315`); credibility in `nd_tt_credibility_*`,
  `nd_stakes_long_*`, `nd_w_crisis_stakes_tt`, events.
- **Now:** the same number with the same paragraph-long hover twice. "credibility" is printed as `#v credibility#!`
  in a dozen effect lines with nothing to hover.
- **Proposed:** drop the Reputation row (Reputation keeps the last crisis and Pledges). Add `concept_nuclear_credibility`
  ("Credibility"), its desc = the mechanics now in `nd_w_credibility_tt` ("Achieving what we threatened over,
  honouring guarantees and restraint raise it; ... It drifts back toward the middle"), and write the effect lines as
  `[Concept('concept_nuclear_credibility','credibility')]`. The meter's hover becomes the figure + concept + (if
  wanted) the last change.
- **Effort:** medium (new concept, loc sweep)
- **Confidence:** medium-high

### NUC-14. Leaderboard and World Crises are fixed slot rows of concatenated text
- **Status:** Done. Both lists are datamodels over variable lists of capitals on a parentless global store (`global_var:nd_lists_store`, `nd_lists_store_ensure`), rebuilt where the slots were written (`update_nuclear_powers_ranking`, now monthly from the world's step; `nd_world_crises_refresh`). Rows read the country through `Scope.GetState` → `State.GetOwner`: vanilla's `tiny_flag`, the name and estimate and the doctrine icon for the powers; both flags, the stage and the danger for the crises (the target through `nd_wc_target_cap`, stored on the issuer), their details on hover from an `ExecuteTooltip` rooted at the issuer. Our rows are tinted. The slot sguis, the `nuke_rank_N` and `nd_wc_N` globals and their loc are deleted. `State.GetOwner` off a datamodel item is a play-test item (`docs/testing/nuclear-playtest.md`).
- **Category:** list
- **Where:** `te_nuclear_sec_powers` (`nuclear_program_widget.gui:605-711`, ten `nuclear_program_power_row`s,
  `nuclear_program_powers_sgui` op 1-10, loc `nuclear_program_power_row_1..10`, `te_miscellaneous_l_english.yml:5494-5503`);
  `te_nuclear_sec_world_crises` (`nuclear_deterrence_widget.gui:792-905`, eight slots + "and N more",
  `nd_wc_row_text` `:5451`).
- **Now:** "1. Germany — 120 warheads (estimated)" ten times; "Germany → France · Confrontation (private) · Danger:
  Tense (45)" up to eight times. Our own row is not marked; there are no flags; nothing else a player plans around
  (whose doctrine permits what — "Doctrine is public", `nd_w_crisis_ft_tt`) is shown.
- **Proposed:** build a list once a week where the rows are written now (`update_nuclear_powers_ranking` for the
  powers, `nd_world_crises_refresh` for crises): a variable list of each country's **capital state** on a global
  container (`GetGlobalVariable('…').GetList('…')` works as a datamodel, gotcha #37; a country is reached through a
  state, gotcha #15). Rows as Demographics' `te_demog_state_row`: `datacontext = "[Scope.GetState]"`, a vanilla
  `flag` (name on hover, click opens the country), the estimate, and the doctrine icon from
  `gfx/interface/icons/nuclear_icons/doctrine_*.dds`; our row tinted. Crises: issuer flag → target flag, stage word,
  danger word, details on hover. Caveat: `State.GetCountry` off a datamodel item is not yet proven in this mod
  (covert proves it off a `Var`), so prototype one row first; the Cultural Hegemony leaderboard uses the same slot
  pattern and would benefit equally.
- **Effort:** large
- **Confidence:** medium (value high; one engine step unproven)

### NUC-15. Burden of our arsenal: a modifier told as prose, with one effect left out
- **Status:** Done, as proposed (the modifier's lines, UN Authority Target among them).
- **Category:** style, hidden info
- **Where:** `je_nuclear_program_widget_taboo_burden_tt` (`te_journal_entries_l_english.yml:634`); modifier
  `nd_taboo_possession_cost` (`common/static_modifiers/nuclear_taboo_modifiers.txt:28-33`, applied with
  `multiplier = root.var:nd_taboo_burden_cached`).
- **Now:** "It turns the bomb's prestige against us, takes away the leverage it brought, and sets our
  restraint-minded interest groups against the arsenal itself." The modifier's third field,
  `country_un_authority_target_add = -1` at full burden, is not mentioned anywhere in the panel.
- **Proposed:** "#tooltip_header The Burden of the Bomb#!\n$TOOLTIP_DELIMITER$\nFrom a taboo of 40 up, the larger our
  arsenal (up to fifty warheads), the heavier the burden. Ours is #v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_disp_taboo_burden_pct')|0]%#!
  of the full weight:\n[GetStaticModifier('nd_taboo_possession_cost').GetDesc]\nRestraint groups object as well.
  Hold the arsenal to a ceiling, or give it up, to lighten it." Same pattern as `je_nuclear_program_widget_funding_tt`.
- **Effort:** quick (loc-only; not in Quick fixes only because it introduces a new `GetStaticModifier` name)
- **Confidence:** high

### NUC-16. Bar tooltips explain the design, and the survivability hover is long
- **Status:** Done, as proposed; the technology list stays only in the ceiling line's hover.
- **Category:** over-explaining
- **Where:** `je_nuclear_ov_taboo_bar_tt` (`te_journal_entries_l_english.yml:602`), `nd_w_survivability_bar_tt`
  (`te_miscellaneous_l_english.yml:5429`), `nd_w_survivability_tt` (`:5433`), `nd_w_survivability_cap_tt` (`:5430`).
- **Now:** "...It is pale either way, not green or red, because a stronger taboo is two-sided: it weighs on an arsenal
  and on threats, and shields countries without one. The arrow says which way it is going." / "...More survivability
  is always better for us, so a rise is green and a fall red. The line marks the ceiling." These justify the colour
  choice to the player. The survivability row hover is then four sentences of mechanics + the bar paragraph, and the
  technology list appears in both it and the ceiling line's hover.
- **Proposed:** taboo: "The pale stretch is the change still to come. It is neither green nor red: a stronger taboo is
  two-sided." Survivability bar: "Green: the rise still to come while we pay for hardening. Red: the fall still to come
  without it. The line marks the ceiling." Cut the technology list from `nd_w_survivability_tt` (the ceiling line's
  hover keeps it). Tests pin the words "two-sided" and "green" (`test_nuclear_layout.py:316, 348`) and, in
  `nd_w_survivability_tt`, "half", "four fifths", "nine tenths", "50" and the script value
  (`test_nuclear_deterrence.py:670-675`); the texts above keep them.
- **Effort:** quick
- **Confidence:** medium-high

### NUC-17. Incident exposure: mechanics in the hover, factors as prose
- **Status:** Done. The hover is one line and `nd_risk_breakdown_sgui`'s factors (readiness against Routine, doctrine, crew strain, command reliability; in a crisis, its danger's word), multipliers rather than a probability; the peacetime-exchange rule moved to How Nuclear Weapons Work → Posture. The owner may still want to confirm that showing the factors fits `nuclear_crisis_design.md` §10.
- **Category:** over-explaining, style
- **Where:** `nd_w_risk_tt` (`te_miscellaneous_l_english.yml:5421`); `nd_w_hold_tt` (`:5390`); values
  `nd_incident_*` (`nuclear_deterrence_values.txt:356-443`).
- **Now:** two paragraphs: how incidents are rolled ("checked weekly ... a separate monthly roll"), a prose list of
  what raises exposure, and a general rule about peacetime exchanges ("ends without conventional war only if both
  governments accept the stand-down") that is about launch authority, not this reading.
- **Proposed:** one line + a factor list in the breakdown shape the crisis danger uses (`nd_cd_*_line`): Readiness
  ×N, Doctrine ×1.35, Crew strain ×N, Command reliability ×N, Crisis danger +band — multipliers, not a probability,
  so `nuclear_crisis_design.md` §10 (no fake precision) still holds; confirm with the owner. Move the peacetime-exchange
  sentence to `je_nuclear_how_posture`.
- **Effort:** medium (a display sgui of lines)
- **Confidence:** medium

### NUC-18. "Chance of a halt": shown when it cannot apply, and its hover omits a case where it does
- **Status:** Done, as proposed: "not delegated" under Central Authorization, the figure under the other three, and Automatic Retaliation named in the hover.
- **Category:** other (noise), hidden info
- **Where:** row `nuclear_deterrence_widget.gui:1551-1561`; `nd_w_hold_value`, `nd_w_hold_tt`
  (`te_miscellaneous_l_english.yml:5390`, "Under conditional delegation or launch on warning ..."); the rolls
  `nd_roll_launch_hold` and `nd_system_reads_attack` (`nuclear_deterrence_effects.txt:1689-1700, 2185-2199`).
- **Now:** under Central Authorization the Forces section shows "Chance of a halt: 75%", a figure that never comes
  into play. Under Automatic Retaliation it does come into play (an accident read as an attack: "Someone in the chain
  may still stop it (nd_hold_chance)"), but the hover names only delegation and launch on warning.
- **Proposed:** a two-text custom loc for the value: the figure under authority 2-4, "#lore not delegated#!" under
  Central Authorization (no op-code literal needed in the .gui). Hover: "...under Conditional Delegation or Launch on
  Warning, or an accident Automatic Retaliation reads as an attack, ...".
- **Effort:** quick-medium
- **Confidence:** high

### NUC-19. At Home rows repeat the same tenure sentence
- **Status:** No further change needed: the loc part (#1202) removed the sentence, and the doctrine and readiness rows already nest their concepts.
- **Category:** over-explaining
- **Where:** `nd_home_row_doctrine_tt`, `_readiness_tt`, `_authority_tt`, `_strain_tt` (`te_miscellaneous_l_english.yml:4881-4899`).
- **Now:** each ends "Counted once the groups have had time to judge our doctrine." — up to four times per group
  table, for every group. The footer `nd_home_list_waiting` already prints "Opinions of our doctrine and readiness
  start in N months" exactly while it applies, and every `concept_posture_*_desc` (hoverable in each table's head)
  says it.
- **Proposed:** drop the sentence (quick fixes below); doctrine and readiness rows nest the concept instead.
- **Effort:** quick
- **Confidence:** high

### NUC-20. Smaller style points
- **Status:** Done. Title-case headers on every key listed; Delivery Capability and Home Defense align their headers and labels; "missile defense"; the rate tooltip's jargon was the loc part. Type: the panel's own templates (`te_nuclear_fontsize_row` 17, `_heading` 20, `_overview` 16, at the head of `nuclear_deterrence_widget.gui`) replace `fontsize_small` / `_medium` / `_large` everywhere; `LabelBudgetTest` reads them.
- **Category:** style
- **Where / Now / Proposed:**
  - Tooltip headers are half sentence case ("Launch authority", "Command reliability", "Crew strain", "Incident
    exposure", "Nuclear umbrella", "Programme funding", "Warhead production", "Pressure to concede", "What conceding
    costs", "If a delegated launch begins") and half title case ("The Burden of the Bomb", "Arsenal Ceiling", "Held
    to the Cap", "Survivability Ceiling"); pick title case (the newer keys). `nd_w_crisis_role_tt`,
    `_deadline_tt`, `_next_pressure_tt`, `nd_w_pledge_tt` and the five `nd_w_crisis_act_*_tt` have no header at all
    while their siblings do (four of them in Quick fixes).
  - Row label vs hover header: "Home defence" → "Interception"; "Delivery capability" → "Delivery"
    (`je_nuclear_program_widget_defence_tt` / `_delivery_tt`). Fine as concepts would be; otherwise align.
  - `je_nuclear_program_widget_rate_tt` "the weekly pulse applies a quarter of it" is engine jargon (quick fix below).
  - Spelling: "missile defense" in `je_nuclear_program_widget_defence_tt` beside "missile defence" in
    `nd_w_survivability_cap_tt` (low priority; the mod is otherwise British here).
  - Type ladder: rows and values are `fontsize_medium` (14, OpenSans) and the overview's words `fontsize_small` (12);
    the owner's 2026-10-17 ladder is rows 17, overview 16 (rule 3). Moving rows to the 17-point serif costs no width
    (8.5 a character vs the 8.6 `LabelBudgetTest` assumes); the overview's 112-wide cells would not fit
    "Confrontation" at 16, which is one more reason for NUC-21. Mod-wide (only Banking and Demographics are on the new
    ladder), so mention once.
- **Effort:** quick (loc) / medium (fonts)
- **Confidence:** high

### NUC-21. The overview names states but not what needs attention
- **Status:** Done (owner, 2026-10-27). Banking's `te_banking_ov_cell` as it is, two to a row: the crisis (stage, deadline weeks, red from two out), Program (state, next warhead), Warheads (count, the world's estimate), Doctrine and Launch Authority (short names, when each can change), Readiness (its name, where it is moving or the weekly upkeep), Credibility; the taboo bar keeps its row. Credibility's icon is a placeholder (art need in `docs/systems/nuclear_gui_icons.md`). `OverviewTest` pins the cells and the three figures the owner named.
- **Category:** spread-out/redundant
- **Where:** `te_nuclear_overview_panel` (`nuclear_overview_widget.gui:98-508`).
- **Now:** row 1 "Producing · Warheads 12 · Confrontation · Credibility 55", row 2 the three posture names, row 3 the
  taboo bar. The figures a returning player acts on are one or two hovers or sections away: weeks to the crisis
  deadline (hover), time to the next warhead (Programme), when the doctrine can next change (nowhere, NUC-4), upkeep.
- **Proposed:** the owner's 2026-10-17 overview form (rule 4, Banking's `te_banking_ov_cell`): two-up boxes with icon,
  caption, word and one figure — Programme "Producing / next in ~4 mo"; Warheads "12 / est. 10"; Crisis "Confrontation
  / 6 wk to deadline"; Credibility "Steady / 55"; Doctrine "No First Use / change in 14 mo"; Readiness "Routine /
  @money! 1.2K/wk"; Authority "Central"; the taboo bar keeps its own full-width row. This brings the overview in line
  with a newer rule rather than reversing the round-3 review (2026-09-30), but it does replace that layout, so flag it
  to the owner. `test_nuclear_layout.OverviewTest` / `NuclearIconsTest` / `LabelBudgetTest.test_overview` pin the
  current cells.
- **Effort:** large
- **Confidence:** medium

## Applied in this PR

17 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`je_nuclear_ov_warheads_tt`, `je_nuclear_program_widget_rate_tt`, `nd_home_row_authority_tt`, `nd_home_row_doctrine_tt`, `nd_home_row_readiness_tt`, `nd_home_row_strain_tt`, `nd_stakes_short_private`, `nd_stakes_short_public`, `nd_stakes_short_target`, `nd_taboo_heading_down`, `nd_taboo_heading_up`, `nd_w_authority_legend`, `nd_w_crisis_act_back_down`, `nd_w_crisis_deadline_tt`, `nd_w_crisis_next_pressure_tt`, `nd_w_crisis_role_tt`, `nd_w_pledge_tt`
