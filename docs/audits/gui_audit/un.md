# United Nations — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Slice: `je_united_nations` and the Diplomacy panel's UN tab. Files read: `gui/journal_entry_widgets/un_{layout,overview,chamber,authority}_widget.gui`, the UN tab block of `gui/diplomatic_overview.gui` (lines 182-357), `common/scripted_guis/un_{chamber,authority}_sguis.txt`, `common/scripted_effects/un_{chamber,authority}_display_effects.txt`, `un_economy_effects.txt` (display lines), `common/scripted_buttons/un_buttons.txt`, `un_economy_buttons.txt`, `common/journal_entries/je_united_nations.txt`, and the loc they render (`te_journal_entries`, `te_concepts`, `te_miscellaneous`, `te_un_button_effects`, `te_diplomacy`). Tests read for pins: `test_un_layout.py`, `test_un_terms_tooltips.py`, `test_un_overview_data.py`, `test_un_vote_lobbying.py`, `test_un_membership.py`.

The panels follow the style guide's older rules well (open/collapsed defaults, How-it-works gathered, Our Record as a table, buttons beside proposals). Where they fall short is the owner's newer criteria: the overview shows the UN's state but not ours (what needs a vote or action), actions live in a button grid at the bottom far from what they act on, the live session card restates the strip above it and teaches mechanics, and the per-proposal tooltips carry ~240 words of identical boilerplate each.

## Top priorities

- **The overview should say what needs us** (UN-1, UN-2): a returning player can't see at the top whether a resolution needs our vote, how we voted, whether our dues are withheld or whether any motion is ready to table. Our own ballot isn't shown anywhere outside the greyed buttons' tooltips.
- **Put actions beside their figures and drop the duplicate buttons** (UN-9): 39 journal-entry buttons sit in an "Actions" grid below every status section. 17 of them duplicate the chamber's Propose rows for a human. The rest (join/leave, dues, grain pledge, programmes, development fund, championing) act on lines several sections above, and one line even tells the player to go and find "the Pledge Grain button on the UN tab". Banking's AI-only-button pattern is proven.
- **Trim the session card to what the strip doesn't show, and lift the vote buttons under the strip** (UN-3, UN-4, UN-6): the tally, passage rule and months appear twice (three times with Delegations). "Our position" is an 11-line open breakdown with a mechanics sentence.
- **Cut the per-proposal tooltip boilerplate** (UN-5): each topic's title hover is 280–510 words, of which 198 are the identical `je_un_terms_common` and 40 the identical `je_un_terms_scaled`. Move them into one concept that each tooltip nests.
- **Make the proposal list findable** (UN-7, UN-8): all 34 rows always show, in-force conventions included. The player can't see our own tabling cooldown or which topics are ready without opening and scanning the list.
- **Modifier lines, not prose, for button and membership effects** (UN-10, UN-11): 14 programme/membership buttons wrap `add_modifier` in `custom_tooltip` and splice in a generated parenthetical prose list. The non-member's "Join to gain…" line is hand-typed and has already drifted from the modifier.
- **The font ladder** (UN-18): the UN uses 20/14/12 where the house style is now 17 (rows) / 20 (subheadings) / 16 (overview), and the pillar table mixes three sizes in one row.

## Findings

### UN-1. The overview shows the UN's state, not ours: nothing says what needs a vote or an action
- **Category:** spread-out/redundant
- **Where:** `gui/journal_entry_widgets/un_overview_widget.gui:113-719` (`te_un_overview_panel`)
- **Now:** Row 1 is membership, tier, crisis and a standing meter. Below it come the authority bar, three pies, the Security Council flags, 17 agency icons and the HQ. Everything a returning player acts on sits in sections further down: whether a resolution is in session and needs our ballot (General Assembly), our dues and Article 19 clock (Our Obligations, 6th status section), whether we can table anything now (inside the collapsed "Propose a Resolution"), a mandate case open to us (Mandates), missions we could join, and whether our record supports action against us (Our Record, last). The overview also predates the owner's 2026-10-17 rule "an overview of readings is a grid of boxes, two to a row" (guide rule 4).
- **Proposed:** Rebuild the overview's top as Banking-style two-up cells (`te_banking_ov_cell`: icon inset, caption, word, one figure, breakdown on hover). Keep the pies, council and agencies below them.
  - **Membership:** member icon / "Member" / tier word. Hover: today's status line.
  - **Session:** topic icon / "Vote needed", "Voted for", "Voted against", "Vetoed", "Our motion" or "No resolution" / "Month 7 of 12". Hover: the topic title. Red word when our ballot is due.
  - **Dues:** "Paid", "Withheld" or "Vote lost" / "0.2% of GDP" or "Vote lost in 9 mo". Hover: `un_chamber_dues_lines`.
  - **Standing:** tier word (Respected) / score. Hover: `un_standing_status_block`.
  - **Floor:** "2 motions ready", "Next motion in 31 mo" or "Not a member". Hover: the ready topics' names (see UN-7, UN-8).
  - **Our Record:** case strength / "Sanctions possible" in red when it reaches a threshold. Hover: the Our Record table's terms.
  - New `un_disp_*` codes are needed for the session state (UN-2), dues state, floor count and record threshold. The rest already exist.
- **Effort:** large (new section, 4-5 display values)
- **Confidence:** high (that the gap exists); medium on the exact cell set
- Pins: `test_un_overview_data.py` (`test_every_membership_state_and_tier_has_an_icon`, `test_rows_below_membership_wait_for_the_first_update`), `test_un_layout.py` order tests. Spec §2 (owner-approved round 1) defined the current overview, so this extends an owner decision rather than reversing one.

### UN-2. Our own ballot is hidden; the vote buttons sit below ~20 lines of card text
- **Category:** hidden info
- **Where:** `un_chamber_widget.gui:389-505` (`te_un_sec_assembly_core`); `common/scripted_guis/un_chamber_sguis.txt:1139-1141`, whose comment says "the direction is otherwise only visible by opening the Recorded Ballot section"
- **Now:** After we vote, all three buttons grey out, and only their IsValidTooltip ("Our delegation has already voted in favour of this resolution.", `je_un_chamber_vote_already_yes_tt`) says how we voted, beside the Recorded Ballot (collapsed by default). The buttons come after the session card (`un_chamber_active_sgui`: topic, proposer, target, mandate terms, tally, rule, projection, veto, months, consequences, grounds) and the position block (UN-4). So the action is the last thing in the section.
- **Proposed:** Add `un_disp_our_vote_code` (0 not cast, 1 for, 2 against, 3 veto, 4 proposer, 5 no vote: non-member, Article 19 or suspended). Show `Our Vote: Not cast` (or `In favour`, `Against`, `Veto`, `Proposer`), with `#R` when not cast, as a row directly under the tally/time strip, with the three buttons centred beside or under it (rule 6). The card text then follows. The same code feeds the overview's Session cell (UN-1).
- **Effort:** medium (one display value, GUI reorder)
- **Confidence:** high

### UN-3. The session card restates the strip above it: tally, passage rule and months, twice each
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** spread-out/redundant
- **Where:** `un_layout_widget.gui:243-325` (strip) vs `un_chamber_sguis.txt:186-211` (`un_chamber_active_sgui`)
- **Now:** The strip shows `je_un_tally_counts` "12 for · 9 against of 40" (`te_journal_entries:2486`), `je_un_tally_rule_simple` "Passes with more votes for than against." (2487) and `je_un_session_months` "Month 7 of 12" (2424). The card directly below shows `je_un_chamber_tally` "In favour 12, opposed 9." (2033), `je_un_chamber_rule_majority` "Passage Rule: Majority" (2000) and `je_un_chamber_months` "In session for 7 months. The proposer reports back at twelve; an unreported resolution lapses at fourteen." (1723). These are the same values (`un_disp_res_yes` reads `var:un_res_support`; `un_overview_display_values.txt:495-560`). `je_un_chamber_deleg_summary` (1612) repeats "Votes cast so far" a third time.
- **Proposed:** In `un_chamber_active_sgui` only, drop `un_chamber_tally_line`'s tally and rule lines (keep `je_un_chamber_tally_committed`) and drop `je_un_chamber_months`. The archive entry (`un_chamber_history_entry`, display effects:848) keeps them, since it has no strip. Make the strip's rule line a `[concept_un_passage_majority]` / `[concept_un_passage_two_thirds]` label ("Passage Rule: Majority", as the card words it now), and put the 12/14-month report-back rule on the time bar's tooltip. Loc-only stopgaps are in Quick fixes (`je_un_chamber_months`, `je_un_chamber_deleg_summary`).
- **Effort:** quick (sgui lines) + quick (GUI tooltip)
- **Confidence:** high

### UN-4. "How the Assembly reads our position" is an open 11-line breakdown that also teaches the AI's vote rule
- **Category:** over-explaining
- **Where:** `un_chamber_widget.gui:395-398`; `un_chamber_display_effects.txt:2085-2131`; loc `je_un_chamber_position_total` (`te_journal_entries:1753`), `je_un_chamber_position_*` (1741-1752)
- **Now:** "**How the Assembly reads our position:** a lean of +12. An AI member in our place votes in favour when its lean, give or take up to 20 points of chance, is above 0 — and a permanent member vetoes a binding resolution at −30 or below." Then up to ten indented terms ("the case against the target: +8", "our ties to the proposer: −3", …) and a consensus line with a `#lore (every member)` aside.
- **Proposed:** One row, `Our Lean: +12`, `#tooltippable`, whose hover is the term list (rule 3: the breakdown of a number goes on hover). The sentence about the AI's threshold and the veto at −30 moves to How the UN Works › Delegations and Lobbying, or into a new `concept_un_lean` (see UN-12) that the label nests: `[concept_un_lean]: +12`.
- **Effort:** medium (sgui split into row + hover builder, one concept)
- **Confidence:** high

### UN-5. Each proposal title's hover is 280–510 words, about 240 of them identical on every topic
- **Category:** over-explaining
- **Where:** `je_un_chamber_propose_topic_<key>_tt` (`te_journal_entries:1866-1910`) → `$je_un_terms_<topic>_tt$` = `$je_un_terms_<topic>$\n\n$je_un_terms_common$`; `je_un_terms_common` (2504, 198 words), `je_un_terms_scaled` (2560, 40 words, appended to every topic's terms). The same `_tt` is the session card's "Its terms" hover (`je_un_chamber_conseq_*`).
- **Now:** Measured by expanding the loc: peacekeepers 507 words, law of the sea 494, reform I 490 … narcotics 278. Every one ends with the same "Every resolution but an expulsion: Carried in full, the proposer gains… If it falls… A proposer that leads a power bloc… Once it carries, every other member is asked to accept it… cannot be tabled again for five years" paragraph, plus "Shown at ×1. A term marked scaled is multiplied by UN Enforcement: ×0.5 at Contested…". The scaled table also repeats `concept_un_enforcement_desc` (`te_concepts:952`) and the tier concepts.
- **Proposed:** A new concept, `concept_un_resolution` ("Resolution"), whose `_desc` is today's `je_un_terms_common` (it already holds `GetStaticModifier('un_vote_success_reward'/'un_vote_failure_penalty').GetDesc`, which renders in a concept desc as well). Each `je_un_terms_<topic>_tt` becomes `$je_un_terms_<topic>$\n\nAnd what every [concept_un_resolution] brings its proposer and the members.` Fold `je_un_terms_scaled`'s one fact the enforcement concept lacks (convention party terms fall to ×0.01 at Moribund) into `concept_un_enforcement_desc`. Then replace `$je_un_terms_scaled$` in every terms key with `#lore Shown at ×1; terms marked scaled follow [concept_un_enforcement].#!`. That leaves a topic's own terms with its modifier lines, about 60-250 words. While there, the prose sentences inside some terms that restate a modifier the same key already renders could go (e.g. `je_un_terms_cultural_diversity`, "Its minorities assimilate more slowly and their homelands fade more slowly", under `un_cultural_diversity_modifier`'s own lines).
- **Effort:** medium (one concept, ~40 `_tt` keys edited mechanically)
- **Confidence:** high. `test_un_terms_tooltips.py` requires `$je_un_terms_<topic>_tt$` in each title hover and card line, which still holds. `test_terms_read_no_scope` forbids scope reads in the terms, which a concept respects.

### UN-6. "If it carries" on the live card is the outcome event's prose paragraph, with a boilerplate credibility clause on every topic
- **Category:** over-explaining / style
- **Where:** `un_chamber_consequences_line` (display effects:417-662) → `je_un_chamber_conseq_<topic>` (`te_journal_entries:1494-1535`) → `$un_vote_<topic>_passed_tt$` (`te_miscellaneous:9011-9071`)
- **Now:** E.g. the mandate card prints `un_vote_military_mandate_passed_tt` (~110 words of rules), the ceasefire card ~120 words, and the development fund's ~150. Every passed text carries "#G UN credibility +1, moving UN Authority's target.#!", and the "Its terms" hover beside it then states the same effects again. Some of these paragraphs carry hand-typed modifier figures as prose (narcotics: "#R −15%#! Opium Plantation throughput, #G +5%#! Pharmaceutical Industries throughput and #G +3%#! prestige", which is exactly `un_narcotics_control_modifier`).
- **Proposed:** Give the card its own one-clause keys (`je_un_chamber_conseq_<topic>`: "If it carries: Germany is condemned for ten years. *Its terms*"). Keep `un_vote_*_passed_tt` for `un_vote.2`, the outcome event that also uses them. Where a passed text states a modifier's numbers, render `[GetStaticModifier('…').GetDesc]` there instead.
- **Effort:** medium (~45 short keys)
- **Confidence:** medium. The display effect's comment says it reuses the event's text "so the numbers here can never drift". A one-clause line with the numbers only in the terms hover keeps that guarantee.

### UN-7. The proposal list always shows all 34 topics at 3–5 lines each; the few that can be tabled are hard to find
- **Category:** list / spread-out
- **Where:** `un_chamber_widget.gui:2839-3327` (`te_un_sec_propose`), row renderers `un_chamber_display_effects.txt:1214-1830`
- **Now:** Every row prints its title, "Binding Resolution — Vetoable" or "Recommendatory Resolution", "Passage Rule: Majority", then "Target: X" or "Target: None" / "No Case" / "In Force" / "Requires: Charter Reform I". In-force conventions keep their row (button hidden) though their status already shows as a lit agency icon and under Our Obligations. Late in a game, more than half the rows are in force or have no case, so a player scans ~120 lines to find the one or two that can be tabled.
- **Proposed:**
  1. Hide a row whose topic is in force (a `visible` per op through an op-taking scripted GUI's `IsValid`, the mission rows' pattern), and say once under the heading: "In force: 9 conventions (the lit agencies above)."
  2. Put rows with a case ("ready") first, under an open "Ready to Table" subheading. The rest go in a collapsed "No Case Now" subsection. Two passes over the same row list, gated on `un_propose_<key>_available`.
  3. Show the ready count on the collapsed header, e.g. "Propose a Resolution (2 ready)", from a new `un_disp_propose_ready_count`.
  4. Optionally fold the type and rule into one line ("Binding · Vetoable · Majority"). This reverses the owner's 2026-09-28 shortening (`ProposeTextTest` docstring: "the type, the passage rule and the target on a line each") and needs `test_type_lines_are_brief` / `test_passage_rules_are_concepts` updated, so ask first.
- **Effort:** large (two-pass layout, display value); item 1 medium
- **Confidence:** high on 1-3, low on 4

### UN-8. Our tabling cooldown is never shown; the list's intro teaches the rule instead
- **Category:** hidden info / over-explaining
- **Where:** `un_chamber_sguis.txt:1966-2001` (`un_chamber_propose_intro_sgui`); `je_un_chamber_propose_intro` (`te_journal_entries:1772`); `je_un_chamber_docket_intro` (1630)
- **Now:** The intro says "After tabling on our own motion we must wait before tabling again: ten years, halved for a Great Power, and lengthened or shortened by our International Standing." It never says how long *we* still wait. While `un_ga_resolution_modifier` runs, every one of the 34 Propose buttons greys out and each tooltip repeats the reason (rule 6: "something true of every row is said once, above the rows", which the held floor already follows). The Docket subsection opens with a mechanics paragraph ("The Assembly takes up real situations as they arise, the gravest first…") in a live list.
- **Proposed:** An intro line "**Our next motion:** in #v 31#! months" or "**Our next motion:** #G ready#!". The modifier is timed, so mirror its expiry as a month count when it is added (`un_propose_effects.txt:455-…`, beside the `add_modifier`) and count it down in the monthly pulse, as `un_reform_cooldown_months_left` does. Trim the intro (Quick fixes). Move `je_un_chamber_docket_intro` to How the UN Works, keeping the docket's live "last taken up" and "next in N months" lines.
- **Effort:** medium (one variable and display value) + quick (loc)
- **Confidence:** high

### UN-9. The Actions grid: actions far from their figures, and 17 buttons that duplicate the chamber for a human
- **Category:** spread-out/redundant
- **Where:** `common/journal_entries/je_united_nations.txt:45-102` (39 `scripted_button`s); the tab's Actions section `gui/diplomatic_overview.gui:315-339` (after every status section); the JE's own grid between `custom_widget_container_2` and `_3` (`gui/journal_entry.gui:207-236`)
- **Now:**
  - The 17 `un_propose_*_button` and `un_request_*_button` have `visible = { un_propose_<key>_available = yes }`, so a human member sees "Propose Condemnation" both in the grid and in Propose a Resolution, with different tooltips (the grid's long `UN_PROPOSE_*_DESC` prose, `te_miscellaneous:1108-1143`).
  - The rest each act on a figure shown elsewhere:
    - Join/Leave, on the overview's membership cell;
    - Withhold/Pay Dues, on Our Obligations › Dues;
    - Pledge/Withdraw Grain, on the Food Reserve line, which says "with the Pledge Grain button on the UN tab of the Diplomacy panel" (`je_un_chamber_food_reserve_can_pledge`, 1664);
    - Fund/Raise/Reduce/Defund Development, on the Development Fund section and the `je_un_chamber_dev_fund_could_contribute` line ("On the UN tab of the Diplomacy panel we could Fund Development Programs");
    - the peacekeeping/human-rights/arms-control toggles, on Programmes and Conventions;
    - Champion/Undermine, on Champions, Underminers and Outsiders.
- **Proposed:**
  - Give the propose/request buttons `is_ai = yes` in their `visible`. That is the Banking precedent, `common/scripted_buttons/banking_alt_economy_buttons.txt:8-14`, where the AI kept using them in play-testing (2026-09-18). `scripting_best_practices.md` §"keep every scripted_button" warns against `is_ai = no`, not this.
  - For the others, add scripted-GUI buttons beside their lines: membership in the overview cell's row; Pay/Withhold under Dues; Pledge/Withdraw under the Food Reserve line; the four development buttons under the Dev Fund section's first row; Champion/Undermine centred under "Championing the order"; the programme toggles beside a new "Ours" column in Programmes (UN-13). The `is_valid` reuses each button's `possible`.
  - Then make those JE buttons AI-only too. The tab's Actions section then holds only Found/Convene, which could move under the overview's "No UN" cell, so the section goes.
- **Effort:** large (≈12 scripted GUIs, GUI rows); the `is_ai` part quick
- **Confidence:** high. Spec §1 put Actions in the tab (round 1); this supersedes that layout but no later owner decision. Opening Programmes for the toggles reverses the comment at `un_chamber_widget.gui:2461-2464` ("collapsed by default: world counts, not the player's own business"). Flag it.

### UN-10. Programme and membership effects are prose, and `custom_tooltip` hides the engine's modifier lines
- **Category:** style
- **Where:** 14 buttons in `common/scripted_buttons/un_buttons.txt` wrap `add_modifier` in `custom_tooltip = { text = "UN_*_DESC" … }` (lines 82, 88, 145, 522, 643, 687, 904, 934, 995, 1024, 1072, 1098, 1139, 1165). Their descs splice in the generated `UN_*_EFFECTS` (`te_un_button_effects_l_english.yml`, generator `gen_un_button_descs.py`), and `je_un_status_not_member` (`te_journal_entries:2485`) and `UN_JOIN_DESC` (`te_concepts:187`) are hand-typed.
- **Now:** `UN_PEACEKEEPING_EFFECTS`: "Applies $un_peacekeeping_contributor_modifier$ (+5% $country_leverage_generation_mult$, +5% $country_prestige_mult$, +5% $country_military_goods_cost_mult$, +10% $unit_experience_gain_mult$, +100 $country_influence_cost_add$)." That is one uncoloured line, with an influence cost shown as an unmarked "+100". The overview's non-member tooltip reads "Join to gain #bold +5 Leverage#!, #bold +10% relations improvement speed#!, #bold +3% Prestige#!, #bold +3% Influence#!…", which omits `un_member_privileges_modifier`'s −5% defender escalation (`extra_modifiers.txt:3483-3490`). It has drifted already.
- **Proposed:** Take the `add_modifier` calls out of the `custom_tooltip` wrapper, so the engine prints coloured, bulleted lines, and keep each desc to one purpose sentence. Retire `gen_un_button_descs.py`, or have it emit `[GetStaticModifier('x').GetDesc]`. Rewrite `je_un_status_not_member` as `#v Not a member.#! Joining brings, and access to UN programmes:\n[GetStaticModifier('un_member_privileges_modifier').GetDesc]`. Do the same for `UN_JOIN_DESC`'s first half; its authority-scaled part could name the scaled modifier the same way.
- **Effort:** medium (script and generator; `docs/auto_generated_files.md` row)
- **Confidence:** high

### UN-11. The standing tooltip shows the modifier's flavour text, not its effects
- **Category:** style
- **Where:** `un_standing_effects_line` (display effects:1039-1073) → `je_un_standing_effects_{exemplary,respected,poor,disgraced}` (`te_journal_entries:2425-2429`)
- **Now:** "In force: #G Respected#! — This country has kept the commitments it made at the United Nations, and is treated as a serious partner for it…" (`$un_standing_respected_modifier_desc$`). The +2 diplomatic reputation and +5% infamy decay never show.
- **Proposed:** `  In force: #G $un_standing_respected_modifier$#!\n[GetStaticModifier('un_standing_respected_modifier').GetDesc]`, and likewise for the other three.
- **Effort:** quick (loc), but the data function is new to this sgui, so not in the Quick fixes table
- **Confidence:** high

### UN-12. The UN's own core terms have no concept: International Standing, case strength, lean, docket
- **Category:** over-explaining / style
- **Where:** overview label `je_un_ov_standing_label` "Standing 62" (2358); Our Record `je_un_record_case` "Case strength" (2388), `je_un_record_expulsion` (2392); `je_un_chamber_propose_intro` "our International Standing"; delegations "lean"; `je_un_chamber_sub_docket` "The Docket". The explanations live only in How-it-works notes: `je_un_standing_help_intro` (2431) holds the only statement of the standing tiers (Disgraced <20 … Exemplary 80+), `je_un_chamber_exposure_help` (1662), `je_un_chamber_deleg_intro` (1598), `je_un_chamber_docket_intro` (1630).
- **Now:** A player meets "Standing", "Case strength 47 / 100", "a lean of +12" and "loses 8 standing" in tooltips, with no hover explaining the term (guide rule 3: "A game term in the label is a concept"). Meanwhile 22 existing UN concepts cover the institution's terms.
- **Proposed:** Add `concept_un_standing` ("International Standing"; desc: what it is, the 0-100 scale, the five tiers and their effect on the tabling wait, from `je_un_standing_help_intro`), `concept_un_case` ("Case Strength"; from `je_un_chamber_exposure_help`), `concept_un_lean` ("Lean"; from the deleg intro and the position sentence, UN-4) and `concept_un_docket`. Use them in the labels: `[concept_un_standing] 62`, `#bold [concept_un_case]#!`. The How-it-works notes keep their sections but can open with the concept, and the `UN_PROPOSE_*_DESC` "(see Our Record in the chamber for how a record is built)" asides become `[concept_un_case]`.
- **Effort:** medium (4 concepts, label edits)
- **Confidence:** high

### UN-13. Our Obligations' budget line is a seven-figure sentence that repeats the Development Fund section
- **Category:** spread-out/redundant / list
- **Where:** `un_chamber_sguis.txt:660-668` → `je_un_chamber_dues_budget` (1653), `un_economy_budget_lines` (`un_economy_effects.txt:847-889`) → `je_un_chamber_budget_dev_fund*` (1473-1476), `_force` (1477), `_free` (1478); the Dev Fund table `un_chamber_widget.gui:2674-2720`
- **Now:** "The World Development Fund takes 5% of it, ¤1.2k a week, and the 4 members funding Development Programs add ¤300: ¤1.5k a week, shared by 7 members below ¤310 of GDP per head (25% of the members' average)." The Development Fund section, two sections away, shows the cutoff, the members' average, the members qualifying and the weekly payout as a table. Our own grant or contribution is a third copy, a `je_un_chamber_dev_fund_*` line under Dues (1614-1629), while the Fund's recipient list has its own "(us)" row.
- **Proposed:** Render the budget as `un_chamber_value_row`s (rule 5): All members' dues ¤/wk · In arrears N% of members' GDP (Funding −x) · Standing Force N% (¤/wk) · Development Fund N% (¤/wk) · Lending facility ¤/wk, max loan ¤. Drop the Fund's internals from it. Move our Dev Fund position (receive, contribute, withheld, above the line) to the Dev Fund section's first row, with its buttons (UN-9). Under Dues, keep at most one "Development Fund: see below" pointer.
- **Effort:** medium
- **Confidence:** high. `ObligationsTest.test_our_dues_sit_beside_the_budget` pins the order dues → budget → conventions. That order is kept.

### UN-14. Delegations: the same estimate caveat on all 24 rows, and the summary hidden by the collapse
- **Category:** over-explaining / hidden info / list
- **Where:** `un_chamber_widget.gui:523-554`; `un_chamber_deleg_member_lines` (display effects:2734-2745) → `je_un_chamber_deleg_reading_estimate` "  #lore The Assembly's estimate, off by up to 10 points.#!" / `_reading_true` (1609-1610)
- **Now:** Each member row prints the name and band, then a lore line explaining the estimate, so up to 24 copies of one caveat. That fact is also in `je_un_chamber_deleg_intro` in How it works. The summary line (firm for/against, with the names on hover) sits inside the collapsed block, so the live count is hidden until the player opens it. The collapse itself is for performance (the comment at 515-522).
- **Proposed:** Mark the band word instead: `Germany: #G leaning for#! #lore (est.)#!` or `(true)`, with the hover on the marker. Then say the caveat once, as the first line above the rows. Move the summary `un_chamber_text` above the subsection toggle, so the counts show while the rows stay collapsed. Later, the names could be flags (a capital-state mirror per row, as `un_p5_seat_N` does).
- **Effort:** quick (loc + moving one text box) for the first two; large for flags
- **Confidence:** high

### UN-15. Missions: progress as a sentence, country-wide refusals on every row, contributors as indented names
- **Category:** list / style
- **Where:** `un_chamber_widget.gui:2282-2417` (8 fixed slot rows); `je_un_chamber_mission_active` "In the field, month 14: 62% of the way, at strength ×1.30." (1695); join gate `un_mission_slot_can_volunteer` (`un_mission_triggers.txt:287-327`)
- **Now:** A minor power, a non-member or a sanctioned member sees a greyed "Send a Contingent" under every mission, each with the same failing line ("needs major power rank"). Electoral missions say "no member sends a contingent", yet show the greyed button below that line. Progress, the thing a mission row tracks, is a number inside prose (rule 5: progress towards a target is a bar). Contributors are a "Contributors:" line plus up to eight indented names.
- **Proposed:**
  - Hide the join button on electoral and host rows (it can never apply there).
  - When the refusal is country-wide (member, represented, rank, sanctions), hide every row's button and say it once above the rows: "We can send no contingent: only a member of Major Power rank can."
  - Add a 0-100 bar per row from a per-slot display value (`un_disp_msn_progress_<slot>`), with "Month 14 · ×1.30" beside it.
  - Round 2 of the 2026-09-28 spec (§0, "one visual row per item for missions in the field, authorized mandates and the archive") is now feasible: gotcha #37 proved `GetGlobalVariable('<x>').GetList('<list>')` as a datamodel. Mirroring `un_mission_registry` onto a global container gives datamodel rows with contributor flags.
- **Effort:** medium (gates, bars); large (datamodel)
- **Confidence:** high on the button noise; medium on the datamodel route

### UN-16. The archive prints 5–7 lines per resolution, and detail mode repeats the ballot caveat on every row
- **Category:** list
- **Where:** `un_chamber_widget.gui:3383-3575`; `un_chamber_history_entry` (display effects:848-860); `un_chamber_ballot_lines` prints `je_un_chamber_ballot_intro` (line 752) inside each of the 30 detail rows
- **Now:** Each archived resolution prints its topic, proposer, target, outcome, tally, passage rule, "Sat for N months" and cooldown. Detail mode adds "#lore Every ballot on the record, side by side with any pledged vote. A pledge is an undertaking, not a vote — it is never counted in the tally above.#!" (1471) under every resolution. That repeats `je_un_chamber_tally_committed`.
- **Proposed:** Print `je_un_chamber_ballot_intro` once, from `un_chamber_ballot_lines_active` only (the live ballot), and not from the archive rows. Longer term, give the archive a table row per resolution (topic icon · year · outcome word coloured · "54–31" · proposer), with the card lines on hover, over a datamodel of a mirrored list (as in UN-15). The archive stays collapsed (rule 1).
- **Effort:** quick (one line out of a shared effect: add a parameter or split it); large (table)
- **Confidence:** high

### UN-17. The authority reading appears three times in a row, its tooltip adds nothing, and the target tick is the eye marker
- **Category:** spread-out/redundant / style
- **Where:** overview bar `un_overview_widget.gui:292-339` (tooltip `je_un_auth_tbl_headline`); "Why UN Authority Is Moving" first line `un_authority_widget.gui:157-159` (also `je_un_auth_tbl_headline`, 1446); the pillar table's Target row (592-618)
- **Now:** "UN Authority 62 → 68 (+0.4/mo)" sits beside the bar, its tooltip says "UN Authority 62.0 → 68.0 (+0.40/mo)", the next section opens with the same line, and the table ends with "Target 68.0". The target is marked with `progressbar_marker.dds` (36×20). The guide's play-test rule says this eye-shaped marker "read as ambiguous, so it is not used". The tally's two-thirds mark also uses it, squashed to 3×22, with no hover of its own.
- **Proposed:**
  - Drop the headline line from Why: the overview sits directly above it in both hosts.
  - Give the bar a tooltip that answers why: "Target 68 = Base 15 + Participation +18.2 + …", from the existing `un_disp_pillar_*` values, or the two largest movers since last month.
  - Draw the target as the translucent segment between current and target, in the bar's own colour, pale (authority isn't good or bad for every player).
  - Draw the two-thirds mark as a thin line with its own hover ("Two thirds of N members").
- **Effort:** medium
- **Confidence:** high on the redundancy, medium on the segment colour

### UN-18. The font sizes are off the house ladder: rows at 20 or 14, buttons and overview labels at 12, three sizes inside one table
- **Category:** style
- **Where:** `un_chamber_text` and `un_auth_text` `using = fontsize_large` (20) for every script-built live row (`un_chamber_widget.gui:56-63`, `un_authority_widget.gui:32-39`); `un_chamber_row_text`, `un_chamber_value_row` and `un_chamber_note` `fontsize_medium` (14) (lines 118-185); buttons `fontsize_small` (12) (191-368); overview `te_un_ov_icon_label` 12 and pies 14 (`un_overview_widget.gui:15-78`). In the pillar table, labels are 14, values default (17) and the headline and Weight rows 20 (`un_authority_widget.gui:157-640`).
- **Now:** Guide rule 3 (owner, 2026-10-17): "Rows, values, buttons and notes are 17, subheadings 20, and the overview 16; nothing a player reads to decide something is smaller." The UN's live text is the size of its subheadings, while its tables, notes and buttons are smaller than vanilla body text.
- **Proposed:** Font templates of the UN's own, as Banking has (`un_fontsize_row` 17, `_heading` 20, `_overview` 16). Apply them per job, then re-budget the fixed cells from the longest label (guide rule 3's 0.5 units per point per character): the 112-wide delegation buttons, the 110-wide overview cells, the 170-wide pillar labels and the 360/100 value rows.
- **Effort:** medium (templates + width pass; no UN width test pins sizes)
- **Confidence:** high

### UN-19. An overview label is always elided, another nearly so
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** hidden info
- **Where:** `te_un_ov_icon_label` (`un_overview_widget.gui:15-33`: `max_width = 108`, `elide = right`, `fontsize_small`); `je_un_ov_member_5` "Suspended, seat carried" (2350), `je_un_ov_member_4` "Permanent member" (2349)
- **Now:** At the guide's budget for the 12-point tooltip face (~6.45 per character + 10%), "Suspended, seat carried" needs ~163 units in a 108 cell, so it always reads "Suspended, se…". "Permanent member" needs ~113, which is borderline. At 16 points (UN-18) "Supranational" won't fit either.
- **Proposed:** "Seat carried" (Quick fixes; the full state stays in the cell's hover, `je_un_chamber_status_suspended_carried`). If the overview moves to 16 points, widen the cells to ~140, or use the two-up cells of UN-1, whose word line is wider.
- **Effort:** quick
- **Confidence:** high for member_5, medium for member_4

### UN-20. The entry's status text repeats the overview's subject in a section of its own; its reason text is a stale second "How it works"
- **Category:** spread-out/redundant / over-explaining
- **Where:** `je_united_nations.txt:144-196` (`status_desc`: `je_un_statistics*`, 2479-2481); the tab's "Status" section `diplomatic_overview.gui:278-311`; `je_united_nations_reason` (2572), which the journal draws under everything else (`gui/journal_entry.gui:749`)
- **Now:** Between the overview and the General Assembly, the tab shows a collapsible "Status" holding "Represented: 82 of 150 eligible / Great Powers: 6 of 8". That is membership, which the overview's pies cover. The play-test rule says the status text "must not repeat the overview… it is empty while the entry is active". In the journal, `je_united_nations_reason` (~350 words) prints open below How the UN Works and has gone stale: "a base plus six pillars" (Policy is missing; `je_un_auth_help_1` says eight with the base), "#bold Great-power commitment#!" (the label is "Commitment", the owner's trim cited in the guide), "ten" agencies (17 exist), "The permanent members are named in the chamber" (they are flags in the overview).
- **Proposed:**
  - Move the statistics into the overview as one line under the pies: `[concept_un_represented]: 82 of 150 · [Concept('concept_great_power','Great Powers')]: 6 of 8`, with suspended members on hover. `status_desc` then keeps only the conference and dissolved states (the entry's no-UN case), and the tab's Status section shows only then. `test_un_overview_data.test_what_only_it_says_stays` pins `je_un_statistics` in `status_desc` and needs updating. This keeps the owner's 2026-09-28 "nothing the journal says is lost" by moving the lines, not dropping them.
  - Cut the reason to the purpose lines of `je_united_nations_desc`. First move its one unique fact, the authority-scaled membership benefits ("÷ 50… +1% research speed"), into the membership hover (UN-10).
- **Effort:** medium
- **Confidence:** high on the staleness, medium on the move

### UN-21. "Available to us" lines sit far from the button that acts on them; the vacant seat sends the player elsewhere
- **Category:** spread-out/redundant
- **Where:** Mandates › Our Case `un_chamber_widget.gui:3366-3379` (`je_un_chamber_mandate_case`, 1678: "An authorization is available to us. The Assembly could be moved to authorize…"); `te_un_ov_vacant_seat` tooltip `je_un_ov_vacant_tt` (2365): "A vacant permanent seat. Hover over the Security Council label to see who is in line."
- **Now:** Tabling the mandate means scrolling up to General Assembly, opening the collapsed proposal list and finding row 4. The vacant seat's hover tells the player to hover something else.
- **Proposed:** Put a `un_chamber_action_button` "Propose the Mandate" under Our Case, bound to `un_chamber_propose_sgui` with `op = 3` (the same `IsValid`/`Execute`/tooltip concatenation as the proposal row). Set the vacant seat's `tooltip` to `un_chamber_council_sgui`'s ExecuteTooltip, as the label has, and retire `je_un_ov_vacant_tt`.
- **Effort:** quick (GUI)
- **Confidence:** high

### UN-22. Text sends players to "the chamber", which no longer exists as a place, and counts have drifted
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** style
- **Where:** `je_un_auth_reform_ripe` (1417) "can be tabled in the chamber"; `un_vote_decide_later_tt` (`te_miscellaneous:9032`) "vote from the chamber"; `notification_un_mission_opened_notice_desc` (`te_notifications:819`) "the chamber's register of missions"; `UN_PROPOSE_{ARMS_EMBARGO,CEASEFIRE,CONDEMN,CREDENTIALS,MANDATE}_DESC` (`te_miscellaneous:1108-1133`) "see Our Record in the chamber for how a record is built" (Our Record shows the record; How the UN Works › Our Record explains it); `un_vote.1.d_expulsion_target` (`te_events:6715`) "The Delegations list in the chamber"; `concept_un_specialized_agencies_desc` (`te_concepts:973`) "Fifteen are founded…", which omits COPUOS (16 convention agencies + the ICJ: `un_agency_count`, `un_script_values.txt:483-501`); naming "share of world power" (`je_un_auth_power_line`, `_participation_detail`) vs "share of world prestige" (`je_un_auth_tbl_participation_tt`, `_weight_tt`) for the same measure.
- **Proposed:** Guide rule 9 (owner, 2026-10-09): name the section and the UN tab of the Diplomacy panel. Fixes for four keys are in Quick fixes. The `UN_PROPOSE_*_DESC` asides become `[concept_un_case]` once UN-12 lands. Pick one of "world power" or "world prestige" (the weight concept says prestige) and use it in the powers list and the participation row.
- **Effort:** quick
- **Confidence:** high

### UN-23. Gate conditions are compound sentences, so one tick covers four conditions
- **Category:** list
- **Where:** `un_chamber_propose_sgui` `is_valid` (`un_chamber_sguis.txt:1274-1712`) → `je_un_chamber_propose_need_*` (`te_journal_entries:1773-1806`)
- **Now:** e.g. `je_un_chamber_propose_need_arms_embargo`: "A rival, or a country at war with a member, that is not our ally, overlord or subject has a record that supports an arms embargo (case strength 40 or more) and is not already under one". This is one ✓/✗ line. A player whose button is greyed can't tell which part fails, and the `_no_case_<key>_tt` hover on the row restates the same sentence negated.
- **Proposed:** For the targeted topics, show the best candidate's failing part rather than a compound clause. E.g. "Best candidate: Germany. Case 34 (needs 40)" as the row's target-line hover, from the selector the row already runs (`un_propose_<key>_select_target`). Or split the clause where the parts are independent of one candidate (`need_observer_request`: elections held / delegation seated / no observers present).
- **Effort:** medium
- **Confidence:** medium. Some clauses are one `any_country` and can't be ticked separately; the candidate preview is the practical form.

### UN-24. Live sections still carry `#lore` explanations
- **Category:** over-explaining
- **Where:** `je_un_chamber_reasons_intro` (1952, Recorded Ballot); `je_un_chamber_reasons_pending` (1953); `je_un_chamber_projection_pending` (1766, live card); `je_un_chamber_position_consensus` "(every member)" (1743); `je_un_chamber_mandate_status_active` (1685), which restates the one-demand rule on every mandate in force (the same rule is in `je_un_terms_mandate` and `UN_PROPOSE_MANDATE_DESC`); `je_un_auth_log_intro` (1405, in the collapsed log)
- **Now:** Guide rule 1: "Don't sprinkle explanatory notes through the live sections." `test_un_layout.HowItWorksTest` guards five keys, not these.
- **Proposed:** Move the reasons and log intros to How the UN Works › Delegations and › UN Authority. Shorten the projection caveat (Quick fixes). Cut the mandate's "In force" line to "#G In force#!: one demand only (hover)", with the rule on hover. Keep `_status_bound`'s red warning, since it's actionable while the play runs.
- **Effort:** quick
- **Confidence:** medium (some owners like the in-place caveat; these are short)

### UN-25. The standing meter shows for countries that hold no standing
- **Category:** hidden info / other
- **Where:** `un_overview_widget.gui:256-279` (`visible` = member code ≠ 0)
- **Now:** Codes 1 ("Cannot join") and 2 ("Not a member") draw a 0-100 bar and "Standing 0", or a frozen score after leaving, while the hover says "We hold no standing: it is a record of membership" (`je_un_standing_nonmember`).
- **Proposed:** Show the meter for codes 3-6 only. For a former member, show the frozen score with a "(frozen)" word, since `je_un_standing_help_losses` says the score waits for a return. Check that `un_standing` survives leaving before relying on it.
- **Effort:** quick
- **Confidence:** medium

### UN-26. How the UN Works restates concept descriptions
- **Status:** its loc-only part is applied in this PR (see "Applied in this PR" at the end); the rest is open.
- **Category:** over-explaining (duplication inside How-it-works)
- **Where:** `je_un_auth_help_6` (1401) vs `concept_un_tier_*_desc` + `concept_un_enforcement_desc` (`te_concepts:952, 976-980`); `je_un_chamber_obligations_help` (1729) vs `concept_un_dues_desc` (950); `je_un_auth_help_7` (1402) vs `concept_un_charter_desc` / `concept_un_authority_cap_desc` (942, 945)
- **Now:** The tier table (ranges and ×0/×0.5/×1/×1.5/×2.5) is written out in the How-it-works note, in five tier concepts, in the enforcement concept, in the authority concept and in `je_un_terms_scaled`. The dues rates appear in both the note and the dues concept.
- **Proposed:** Have the notes name the concepts and keep only what no concept says (the four-point hysteresis; re-assessment timing). Quick fixes for `help_6` and `obligations_help`. `help_7`'s reform clock (24 months within 5 points, 5-year gap) isn't fully in the charter concept, so check before trimming.
- **Effort:** quick
- **Confidence:** high

## Applied in this PR

18 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`concept_un_specialized_agencies_desc`, `je_un_auth_help_6`, `je_un_auth_reform_ripe`, `je_un_chamber_deleg_summary`, `je_un_chamber_months`, `je_un_chamber_obligations_help`, `je_un_chamber_projection_pending`, `je_un_chamber_propose_intro`, `je_un_chamber_propose_nonmember`, `je_un_chamber_tally_committed`, `je_un_ov_agencies_label`, `je_un_ov_member_5`, `je_un_standing_help_intro`, `je_un_standing_help_limits`, `je_un_standing_help_losses`, `je_un_standing_help_sources`, `notification_un_mission_opened_notice_desc`, `un_vote_decide_later_tt`
