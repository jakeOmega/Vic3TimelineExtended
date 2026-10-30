# GUI and Localization Audit (2026-10-27)

An audit of every mod panel and the loc it renders, against the owner's five concerns (the owner's request, 2026-10-27):

1. **Over-explaining** outside the collapsed "How X Works" sections. Tooltips should be short, and may nest concepts for depth (a colony's Defences tooltip linking a fleet concept, which links a ship-role concept, which links Space Command).
2. **Things that should be lists** and aren't, now that the mod has a proven list pattern (the Demographics tab's States table).
3. **Redundant or spread-out information.** The path should be (1) summary, then (2) action, as in the Banking overview, not a hunt across sections.
4. **Unintended hidden information.**
5. **Stylistic inconsistency**, above all prose where the engine's coloured, bulleted modifier lines belong (Global Warming's Carbon Removal Support row was the owner's example).

It covers 248 findings in ten slices. This PR applies about 330 loc-only fixes and four small GUI and script fixes. The rest is the work list below. Each slice has a detail file in [`gui_audit/`](gui_audit/) with the evidence for every finding: file and line, the current text, the proposed change, its effort, and the tests that pin it.

**How it was done.** Each slice was read in full (the `.gui` files, the scripted GUIs and effects behind their tooltips, the journal entries and every loc key they render) and checked against [`../guides/gui_style_guide.md`](../guides/gui_style_guide.md). Every finding was traced to the markup and loc it cites. Nothing was play-tested. Where a finding would reverse a recorded owner decision, it says so.

## Contents

- [The follow-up wave (2026-10-27)](#the-follow-up-wave-2026-10-27)
- [What this PR changes](#what-this-pr-changes): #1202's own fixes
- [Cross-cutting findings](#cross-cutting-findings): the patterns that recur across systems, best fixed as one pass or one shared type
- [Work list by system](#work-list-by-system): the open findings, a table per slice
- [Decisions for the owner](#decisions-for-the-owner)
- [Tests that pin what would change](#tests-that-pin-what-would-change)
- [Tooling that would keep this from coming back](#tooling-that-would-keep-this-from-coming-back)

| Slice | Detail file | Findings | Loc fixes in #1202 | Follow-up wave | Issue |
|---|---|---|---|---|---|
| Banking, Budget Breakdown, top bar | [`banking_budget.md`](gui_audit/banking_budget.md) | 21 | 14 | 19 done, 2 needed no more | #1203 |
| Legislated Tax Code | [`tax_code.md`](gui_audit/tax_code.md) | 26 | 30 | 23 done, TAX-21 in part, 2 needed no more | #1204 |
| United Nations | [`un.md`](gui_audit/un.md) | 26 | 18 | 25 done, UN-15 in part | #1205 |
| Cultural Hegemony, Covert Warfare | [`hegemony_covert.md`](gui_audit/hegemony_covert.md) | 29 | 39 | all done | #1206 |
| Global Warming, Strategic Reserve, Market panel | [`climate_reserve_market.md`](gui_audit/climate_reserve_market.md) | 32 | 40 | all done (GW-12 on placeholder art) | #1207 |
| Nuclear Weapons | [`nuclear.md`](gui_audit/nuclear.md) | 21 | 17 | 20 done, 1 needed no more | #1208 |
| Space Race and colonies, orbital debris, Seabed | [`space_seabed.md`](gui_audit/space_seabed.md) | 25 | 73 | all done | #1209 |
| Grand Monuments, Colonial Empire | [`monuments_colonial.md`](gui_audit/monuments_colonial.md) | 28 | 29 | all done | #1210 |
| Demographics, Nation tab, the window, tab gates | [`demog_nation_window.md`](gui_audit/demog_nation_window.md) | 18 | 41 | all done or needed no more | #1211 |
| Additions to vanilla panels, entries with no panel | [`vanilla_panels_other_jes.md`](gui_audit/vanilla_panels_other_jes.md) | 22 | 27 | 21 done, JE-8 in part | #1212 |

## The follow-up wave (2026-10-27)

After the owner answered the [decisions](#decisions-for-the-owner), one agent per slice implemented that slice's open findings, quick, medium and large, and a twelfth built the four audits of #1213. The work tables below and each detail file give every finding's status. What is still open:

- **UN-15:** mission contributors as flag rows. It needs a second copy of the mission register, kept in step on every mission path, and a list read not yet proven in game, for at most eight names. The owner wanted it only if it was straightforward, so it waits.
- **TAX-21:** history rows show the code version and the promise's group, but not what each entry changed, which would need more stored fields.
- **JE-8 (b):** whether a journal entry's `_desc` renders anywhere needs the game (its play-test list, item 14).
- **Art:** placeholders stand in for a credibility icon (Nuclear), two Global Warming policy icons, a warship icon and the Defense and Modules cells' icons (Space). The player guide's screenshots of the Nuclear, UN, Cultural Hegemony, Covert, Global Warming, Strategic Reserve and solar-colonization panels show the old layouts.

The owner also settled four points the wave raised. The Banking tools that paid the treasury monthly (BNK-14) are charged weekly in the budget, at a quarter of the monthly cost; FX Surrender stays monthly, since its payment is the gold it buys. Open-Market Operations stays in both places (BNK-11). The Covert network rows became a table (COV-12). Seabed claimants are a list per basin, and each ship role has a short concept (SEA-3, SPC-3). One request came in mid-wave: once the viewing player has researched Abyssal Plain Mining, every coastal state shows its ocean basin (VAN-8b).

Everything the wave built rests on the offline checks only. Each slice added what only the game can show to its system's play-test list in `docs/testing/`, and `TE_SELF_CHECK` lines mark the list reads that nothing had proven before (`ce_subject_row`, `ch_board_rows`, `gw_top_emitters_list`, `sr_powers_list`, `seabed_claimant_list`).

## What this PR changes

This section and the cross-cutting findings describe #1202 as it merged. The follow-up wave's status is in the table above and the work tables.

**Loc text rewritten in place (about 330 keys, no key renamed or added).** Every `[...]` data expression a new value keeps or adds is copied from the key itself or from a sibling that renders in the same context. Two tests pinned an old value and are updated with it (`test_cultural_hegemony_layout`, `test_grand_monument_trophies`). The kinds:

- **Boilerplate cut where the same fact sits one line or one hover away.** Global Warming's "Applies to your own country. Available at 0.5 °C…" under every policy, whose Adopt button already ticks those conditions. "These are the journal entry's own panels…" on twelve tab tooltips, now said once on each Open Journal Entry button. The click instructions on every Tax Code row, now in the intro above the rows. The estimate caveat on every interest-group offer. "Counted once the groups have had time to judge our doctrine" on four At Home rows.
- **Engine-rendered modifier lines in place of prose**: the 15 Grand Monument boon tooltips, the four pension buttons and Carbon Removal Support now print `[GetStaticModifier(...).GetDesc]`. The Tax Code's Pass, Force Through and Renegotiate tooltips no longer restate the approval modifiers printed under them.
- **Stale or wrong text corrected**: the Defences and Spaceport modules ("Space fleets are not in the game yet"); three Global Warming repeal texts that contradicted their own modifier; the agencies concept, which said fifteen and missed COPUOS; "economic-system laws" granting intervention points; "half the levels" on trophies; "5 levels" for an opportunity; the decolonization concept's "three decisions"; the census date; five concepts' stage, threshold and milestone lists.
- **One name per thing**: solar-colonization stage names, "Back down", influence tiers, the Seabed basins ("the Indian Ocean"), the greyed-tab checklists' lead-ins and person.
- **Hover markers**: 29 Space Race labels and column heads that carry a tooltip are now underlined (`#tooltippable`).
- **Small structured texts**: Strategic Reserve presets as "Label: value" lines, the Grand Monument opportunity moments and the Heir Education reason as bullets, State Collapse's reason now says what the collapse does.

The rewrites left four keys unused: `organize_loc.py` filed `te_demog_st_e0_n` in `te_unused_l_english.yml`, and the three Grand Monument ones are deleted, since `test_grand_monument_registry` keeps every `gm_` key in `te_miscellaneous`.

**Beyond loc (four changes):**

- **Global Warming, Carbon Removal Support** (the owner's example): its tooltip is a flavour line plus `[GetStaticModifier('carbon_removal_modifier').GetDesc]`, as its siblings'. The Environmental Movement note moved into How Global Warming Works.
- **Cultural Hegemony, CH-1 (bug)**: the Standard of Living pull row was shown only when positive, so a country below the world average lost pull with no line for it, and the value was hard-coded green. It now shows for either sign, signed and coloured (`cultural_hegemony_sguis.txt` op 3, `je_ch_widget_bd_sol_value`; `test_cultural_hegemony_layout.ValueColourTest` updated).
- **Market panel, MKT-2 (bug)**: the Exports by Value hover priced goods at base price while its slice used the market price. It now uses the market price, as Imports by Value does.
- **Nuclear, NUC-1**: no label in the Nuclear panel was underlined, though they carry its richest hovers. `nd_row`, `nd_home_term_row` and `nuclear_program_row` now underline the label through a `label_format` block, which the one row without a tooltip (First Device) overrides empty.

**For the play-test before release** (nothing here was seen in game):

- Boon tooltips (Grand Monuments' Opportunities Seized) and the pension buttons (Demographics' Work and Retirement) now call `GetStaticModifier(...).GetDesc` in contexts whose siblings already do. Check that the lines render.
- The covert row buttons (Stand down, priority − / +) root their tooltips on `GetPlayer` instead of `JournalEntry` (COV-9a): check that a greyed one now says why.
- The underlines in the Nuclear panel and on Space Race labels.

## Cross-cutting findings

These recur across systems. Most are cheaper fixed once, as a shared type or a single pass, than slice by slice.

### 1. Overviews say what the system is, not what needs the player

The Banking overview answers "what needs me", and few others do. The proposed fix is the same everywhere: Banking's two-up cells (`te_banking_ov_cell`: icon, caption, word, one figure, breakdown on hover), each with a status word that turns red when action is due.

| Panel | What a returning player can't see at the top | Finding |
|---|---|---|
| Tax Code | whether the bill can pass, a failing promise, a blocked draft, an offer waiting | TAX-1 |
| UN | whether a resolution needs our vote, how we voted, dues withheld, motions ready to table | UN-1, UN-2 |
| Nuclear | weeks to the crisis deadline, time to the next warhead, when the doctrine can next change | NUC-21, NUC-4 |
| Space colonization | which colony is restless, under assault or blockaded, an idle module queue, the next window | SPC-6 |
| Strategic Reserve | goods Blocked or full, what the reserve spends | SR-9 |
| Cultural Hegemony | the programmes and funding (the only actions) | CH-9 |
| Grand Monuments | the contested monuments' decisions, flagged at the top but acted on far below | GM-3 |

### 2. Actions sit far from the figures they act on

- **Tax Code:** Pass, Revise and Force Through sit below up to eight interest-group cards. The fix is to move them under the Conditions table and pin a bill footer on the Budget tab, like the draft's (TAX-2). A blocked draft's Accept buttons are only inside the collapsed Review (TAX-3).
- **UN:** 39 journal-entry buttons sit in an Actions grid below everything. Seventeen of them duplicate the chamber's Propose rows for a human (UN-9). Banking's `is_ai = yes` precedent applies, plus scripted-GUI buttons beside each figure.
- **Grand Monuments:** the contested choices and the policy buttons sit below dozens of National Effects rows. The proposal is an "Awaiting a Decision" section near the top (GM-3).
- **Space:** the Target button for the next colony fleet is in the collapsed Solar System list, the last section (SPC-7).
- **Nuclear:** the posture's choices sit in collapsed subsections, one of which mixes two axes (NUC-3). Our Moves comes after eleven crisis lines (NUC-7).
- **Covert:** deciding a launch takes four places (COV-2).

### 3. Fixed slots and prose that should be lists

The Demographics States table (a variable list built in script, drawn by a `datamodel` with `datacontext = "[Scope.GetState]"`) answers most of these. A country is reached through its capital state. `State.GetCountry` from a datamodel item is not yet proven in this mod, so prototype one row with a `TE_SELF_CHECK` first (gotcha #15, the Self-checks pattern in CLAUDE.md).

| List | Today | Finding |
|---|---|---|
| Colonial territories and subjects | 8 fixed slots each, then names only in a "+N more" hover, with no Release button | CE-1 |
| Great powers pressing the colonial empire | a script-built text block | CE-2 |
| Top Cultural Powers board | ten two-line prose rows | CH-2 |
| Nuclear powers, world crises | 10 and 8 fixed slots of script-built text | NUC-14 |
| Space Race rivals, Space Powers | 5 and 8 fixed slots, "+N more" | SPC-9 |
| Seabed claimants | sentences under a column table, six slots per basin | SEA-3 |
| Top Emitters | five slots and a five-way ladder in script | GW-11 |
| Top Trade Partners | five 47-line copies over fifteen rank variables | MKT-1 |
| UN missions, the archive | 8 slots; 5–7 lines per archived resolution | UN-15, UN-16 |
| Tax Code taxed goods, relief states | a count only; the lists exist in script but aren't drawn | TAX-12 |
| Youth bulge and metropolis states | a count, with "each state's subtab shows its own" | DEM-6 |
| Monetary Union holdouts, backstops | counts and sums | BNK-13 |
| Construction market read-out | six sentences | VAN-2 |

### 4. Prose where engine modifier lines belong

The order of preference: a static modifier rendered with `[GetStaticModifier('x').GetDesc]`; an `add_modifier` left visible in an effect, not wrapped in `custom_tooltip = { text = … }`, which hides its lines; or a `script_only = yes` modifier type for an effect script applies itself, so it still prints as a coloured line.

- **Done here:** Carbon Removal Support, the Grand Monument boons, the pension buttons.
- **Need `script_only` display types:**
  - Global Warming's Environmental Movement radicalism line on every policy (GW-3);
  - Seabed policies (SEA-2) and Grand Monument policies (GM-2);
  - Nuclear readiness levels and launch authority (NUC-6);
  - Banking's external tools, the monetisation step and the mandate's loosening cost (BNK-6).
- **Need the `custom_tooltip` wrapper removed:**
  - UN programme and membership buttons (UN-10), whose "Join to gain…" line has already drifted from its modifier;
  - Create New Religion's Proclaim button, which hides conversions and exiles (JE-2);
  - Grand Monuments' contested choices (GM-4);
  - Renewable Investment's running cost (GW-4);
  - Heir Education's innovation cost (JE-5).
  A scan found 22 `custom_tooltip` blocks that wrap an `add_modifier`; 12 of them render no modifier line.
- **Repeal texts** (Global Warming) are a design question; see [Decisions](#decisions-for-the-owner).

### 5. Greyed buttons that don't say why

Rule 6 asks every greyed button to list its failing condition.

- **Space colonies and fleets:** about 470 generated buttons render only `ExecuteTooltip`, so the reasons their scripted GUIs already hold never show. The fix belongs in the two generators. About 16 of those reasons are worded as failure messages and need rewording as requirements before they read right beside a tick (SPC-1).
- **Raw script in the condition list:**
  - Banking's five external tools print raw trigger names (BNK-3);
  - World War's buttons print bare `has_variable` and script-value comparisons (JE-3);
  - Create New Religion's trait buttons print variable names (JE-2).
- **Vanilla Budget controls:** under the Tax Code they are greyed and still show vanilla's tooltip (TAX-11).
- **Condition lines that read as complaints** beside a tick (CH-10, quick fix applied). Covert's implementation guards are always ticked (COV-9b).

### 6. Hovers nobody can find

A label whose row carries a tooltip should be underlined (rule 3).

*Superseded 2026-10-30:* the owner rewrote rule 3 to follow vanilla, which underlines a hoverable word in running text, not a hover's label or value. The Space Race's underlines went in #1258 and every other panel's on the same day; `test_gui_underlines.py` holds the panels to the new rule.

- **Done here:** Nuclear (NUC-1) and the Space Race labels and heads (SPC-12).
- **Open:**
  - the state view's tile rows (VAN-10, one `label_format` block in `te_state_stat_row`);
  - the Top Trade Partners figures (MKT-4);
  - the All Goods label (MKT-5);
  - the Space Race value-row type, which should gain the block so new rows get it.

### 7. Live tooltips that teach, and How sections with gaps

- **The size of it:** 303 loc keys referenced from `.gui` files, outside How-it-works keys, run over 300 characters; 132 run over 500. There were 321 and 136 before this PR. The longest are Banking's Monetary Policy row tooltips, 900 to 3,850 characters each, most opening with a verbatim copy of the label's own concept (BNK-1, BNK-2). The fix there is a test-pinned rewrite, so it isn't in this PR.
- **How sections missing a topic,** so the rules live only in live tooltips:
  - Banking has no Prices, Exchange Rate, Gold, Arrangements or Mandates topic (BNK-1);
  - Demographics has no Work and Retirement or Longevity topic (DEM-3);
  - Space has nothing on colonization (SPC-4); seven live colony sections open with a paragraph instead;
  - Grand Monuments has no Archaeology topic (GM-14).
- **The same rule in three to five places:** UN tiers (UN-26), Global Warming's treaty (GW-9), the colonial definitions, which have drifted apart (CE-4), each Nation-tab score (NAT-4), the Tax Code's supersession rule (TAX-9), and the construction market (VAN-1, VAN-3).

### 8. Concepts to add, so tooltips can nest

The owner's example chain is the model. Proposed families:

- **Solar colonization:** module, space fleet, ship role, Space Command, drive, launch window, colony autonomy, free colony, blockade, integrity, marines, plus the programme estimate (SPC-3, SPC-10).
- **UN:** resolution (UN-5: about 240 identical words on every proposal's hover), International Standing, case strength, lean, docket (UN-12).
- **Colonial Empire:** colonial territory, colony, colonial subject (CE-4).
- **Single concepts:** nuclear credibility (NUC-13), the tax code's static estimate (TAX-19), the emissions-reduction treaty (GW-9), anti-satellite strike (SPC-18), seabed regime (SEA-1), the construction queue cap (VAN-3).

### 9. Type sizes

Rule 3 (the owner, 2026-10-17): rows, values, buttons and notes at 17, subheadings at 20, the overview at 16, each through a panel's own font templates.

- **On the ladder:** Banking, Demographics, the Nation tab and the Seabed tab.
- **Rows at 14 and overview words at 12:** Tax Code (TAX-15), UN (UN-18), Nuclear (NUC-20), Space (SPC-11), Cultural Hegemony (CH-15), Covert (COV-14), Global Warming (GW-15), Strategic Reserve (SR-10), Grand Monuments (GM-17), Colonial Empire (CE-11) and the Breakdown tab (BNK-20). The UN instead draws its live text at 20.

One pass, panel by panel, with the width tests each panel already has, is cheaper than ten. Cultural Hegemony is exempt until reworked (the guide's grandfather clause).

### 10. One thing, several names

- Covert operations carry up to three names each: the diplomatic action, our row, and the Known row (COV-3).
- Banking has "Price Pressure" and "Inflationary Pressure", and "Reference Rate" beside "World Rate" (BNK-15).
- Space uses "Fleets" for colony fleets and warships alike (SPC-16).
- The Strategic Reserve says "Withdrawing" and "Releasing" (SR-5).
- Grand Monuments mixes construction site, undedicated and "Being Built" (GM-7).
- Spelling is mixed mod-wide, British (programme, defence, licence) beside American (program, defense, stabilize). `docs/player_guide/STYLE.md` asks for American in the guide, as the base game uses. The loc needs one rule; see Decisions. **Done:** American (Decision 10); `scripts/analysis/check_loc_spelling.py` swept the loc and the guide, and `--check` lists stragglers.

## Work list by system

Each table lists every finding in the slice. "(loc part done)" means this PR applied the finding's loc-only part and the rest is open; the detail file says what remains. Effort: quick is loc-only or a line of markup; medium is a GUI change, a concept or a small script change; large is a new script list, a new section or a generator change. Findings are numbered in each slice's own order of discovery, so read each slice's **Top priorities** first.

### Banking, Budget Breakdown and the top bar ([detail](gui_audit/banking_budget.md), #1203)

Top priorities: the Monetary Policy row tooltips are essays that open with their label's concept word for word; the rules belong in five new How topics (BNK-1). Each mandate button should say what its mandate does (BNK-2). Five external tools print raw triggers when greyed (BNK-3). History markers print a tool's whole current tooltip (BNK-4). The Breakdown tab's tooltips are generic or repeat pool figures on every row (BNK-17–19).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| BNK-1 | Monetary Policy row tooltips: definitions duplicated from the label's concept, mechanics taught in live tooltips | over-explaining / spread-out | large | done |
| BNK-2 | The mandate buttons don't say what their mandate does | spread-out | medium | done |
| BNK-3 | Five external tools: the greyed Enable tooltip prints raw trigger internals | hidden info / style | medium | done |
| BNK-4 | History chart tooltips: full current tool tooltips per marker (five with broken accessors); cycle bars show no reading | over-explaining / hidden info / possible bug | medium | done |
| BNK-5 | Intervention descriptions restate the lines printed under them; Open-Market Operations states its requirement and its inflation cost twice (loc part done) | over-explaining / style | quick | done |
| BNK-6 | Effect prose where engine modifier lines are preferred | style | medium | done (display-only modifiers) |
| BNK-7 | The JE's progress line repeats the overview's Budget cell, with a different total, and shows while dormant | spread-out/redundant | quick | done |
| BNK-8 | Budget tooltip and concept credit "economic-system laws" with points they don't grant (loc part done) | other | quick | no change needed (#1202 did it) |
| BNK-9 | The rate-drift rule is stated in three tooltips and two concepts (loc part done) | over-explaining / redundant | quick–medium | done |
| BNK-10 | The top bar's phase tooltip says "The bar shows…" and "(see below)" (loc part done) | style / context | quick | no change needed (#1202 did it) |
| BNK-11 | Active Policies: in-force tools named as orders, no time left on timed tools, OMO listed twice | style / hidden info / redundant | quick–medium | done |
| BNK-12 | Available Interventions: "no points free" is said 40 times, never once above the rows | style | medium | done |
| BNK-13 | Lists: Monetary Union holdouts and Backstops are counts and sums, not lists | list | large | done |
| BNK-14 | Monthly treasury payments of three tools appear nowhere in the Budget panel | hidden info | medium–large | done (weekly charges; FX Surrender's purchase stays monthly) |
| BNK-15 | One thing, several names (loc part done) | style | quick–medium | done |
| BNK-16 | The JE's description paragraph is a how-to, shown under the panel in the JE only | over-explaining | quick | done |
| BNK-17 | Breakdown: one generic tooltip on 29 rows describes other rows | over-explaining / hidden info | medium | done |
| BNK-18 | Breakdown: each institution row repeats seven pool-level figures and a formula | over-explaining / redundant | medium | done |
| BNK-19 | Breakdown: the same mechanics sentence on every source, group, arrow and pie | over-explaining | quick | done |
| BNK-20 | Breakdown: "How the Breakdown Works" is one text block, smaller than the house type, and mixes UI help with accounting | style / over-explaining | medium | done |
| BNK-21 | Breakdown mirror line in every cost modifier: shorter label | style | quick | done |

### Legislated Tax Code ([detail](gui_audit/tax_code.md), #1204)

Top priorities: an overview of each process's status (TAX-1); the bill's buttons under its conditions, with a pinned footer on the Budget tab (TAX-2); a blocked draft's fix shown where the player is (TAX-3); the revenue estimate in the draft summary and as a table (TAX-4); the held data never drawn: taxed goods, relief states, "in force since" (TAX-12, TAX-20); greyed native Budget controls saying why (TAX-11).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| TAX-1 | Overview lists metadata, not the actionable state of each process | spread-out/redundant, hidden info, style | large | done |
| TAX-2 | Pass / Revise / Withdraw / Force Through sit below every interest-group card | spread-out/redundant | medium | done |
| TAX-3 | "Changed Since Drafted" and its Accept buttons are only in the collapsed Review | hidden info | medium | done (Changed Since Drafted at the top of the workbench) |
| TAX-4 | Revenue: no figure in the summary, and the estimate is written as sentences | spread-out/redundant, list | medium | done |
| TAX-5 | The committed share is shown twice, one above the other | spread-out/redundant | medium | done |
| TAX-6 | Interest-group cards: full cards for marginal groups, zero rows, no icon | spread-out/redundant, style | medium | done (a–d; d folds committed and marginal groups) |
| TAX-7 | Live Bill section: teaching notes and a disclaimer repeated on every card | over-explaining | quick–medium | done |
| TAX-8 | The offer's hover is a six-sentence paragraph that duplicates How it works | over-explaining | quick | done in #1202 |
| TAX-9 | Command tooltips restate the modifier lines the engine prints under them | over-explaining, style | quick | done (#1202 and the passed-bill hover) |
| TAX-10 | Click instructions repeated on every row's hover, under an intro that already says them | over-explaining | quick | done in #1202 |
| TAX-11 | Greyed vanilla Budget controls don't say why | hidden info | medium | done (Budget, goods panel, right-click menu) |
| TAX-12 | Held data never drawn: taxed goods, enacted relief states, a passed bill's relief | hidden info, list | medium | done |
| TAX-13 | Goods Catalog is 39 ungrouped rows in key order, with no icons | list, style | medium | done |
| TAX-14 | Section order puts the long editing workbench above the bill under debate | spread-out/redundant | medium | done |
| TAX-15 | The whole UI is set a step below the house type ladder | style | large | done |
| TAX-16 | The same thing named differently across panel, tooltip and button | style | quick | done |
| TAX-17 | Review: static mechanics lines in the live entries | over-explaining | medium | done |
| TAX-18 | The overview's Economy Snapshot row, and its developer-facing hover | over-explaining, other | medium | done |
| TAX-19 | The estimate's assumptions are written out twice; make them one concept | over-explaining | medium | done |
| TAX-20 | The Enacted Code doesn't show since when a rate holds | hidden info | medium | done |
| TAX-21 | History rows say what kind of thing happened, not what changed | hidden info | medium–large | done (version and group; no per-entry summaries) |
| TAX-22 | A promise's "what" cell can elide | hidden info | quick | done |
| TAX-23 | Light code: one sentence said three times; reaction text on every step button | over-explaining, style | quick | done |
| TAX-24 | The interest-group view modifiers explain both codes in one description | style | quick–medium | done (one sentence) |
| TAX-25 | Force Through is drawn, greyed, when the bill can pass on its own | other | quick | done |
| TAX-26 | Customs levels are words where vanilla uses tariff icons | style | medium | done |

### United Nations ([detail](gui_audit/un.md), #1205)

Top priorities: an overview of what needs us, and our own vote under the tally (UN-1, UN-2); the Actions grid replaced by AI-only buttons plus inline controls (UN-9); the session card trimmed to what the strip doesn't show (UN-3, UN-4); the proposal hovers' shared boilerplate moved into one concept (UN-5); a findable proposal list with our own tabling wait (UN-7, UN-8); modifier lines for programmes and membership (UN-10).

| ID | Finding | Kind | Effort |
|---|---|---|---|
| UN-1 | The overview shows the UN's state, not ours: nothing says what needs a vote or an action **Done.** | spread-out/redundant | large |
| UN-2 | Our own ballot is hidden; the vote buttons sit below ~20 lines of card text **Done.** | hidden info | medium |
| UN-3 | The session card restates the strip above it: tally, passage rule and months, twice each **Done.** | spread-out/redundant | quick |
| UN-4 | "How the Assembly reads our position" is an open 11-line breakdown that also teaches the AI's vote rule **Done.** | over-explaining | medium |
| UN-5 | Each proposal title's hover is 280–510 words, about 240 of them identical on every topic **Done.** | over-explaining | medium |
| UN-6 | "If it carries" on the live card is the outcome event's prose paragraph, with a boilerplate credibility clause on every topic **Done.** | over-explaining / style | medium |
| UN-7 | The proposal list always shows all 34 topics at 3–5 lines each; the few that can be tabled are hard to find **Done.** | list / spread-out | medium–large |
| UN-8 | Our tabling cooldown is never shown; the list's intro teaches the rule instead **Done.** | hidden info / over-explaining | quick–medium |
| UN-9 | The Actions grid: actions far from their figures, and 17 buttons that duplicate the chamber for a human **Done.** | spread-out/redundant | quick–large |
| UN-10 | Programme and membership effects are prose, and `custom_tooltip` hides the engine's modifier lines **Done.** | style | medium |
| UN-11 | The standing tooltip shows the modifier's flavour text, not its effects **Done.** | style | quick |
| UN-12 | The UN's own core terms have no concept: International Standing, case strength, lean, docket **Done.** | over-explaining / style | medium |
| UN-13 | Our Obligations' budget line is a seven-figure sentence that repeats the Development Fund section **Done.** | spread-out/redundant / list | medium |
| UN-14 | Delegations: the same estimate caveat on all 24 rows, and the summary hidden by the collapse **Done.** | over-explaining / hidden info / list | quick–large |
| UN-15 | Missions: progress as a sentence, country-wide refusals on every row, contributors as indented names **Partly done:** contributors as flag rows (datamodel) deferred. | list / style | medium–large |
| UN-16 | The archive prints 5–7 lines per resolution, and detail mode repeats the ballot caveat on every row **Done.** | list | quick–large |
| UN-17 | The authority reading appears three times in a row, its tooltip adds nothing, and the target tick is the eye marker **Done.** | spread-out/redundant / style | medium |
| UN-18 | The font sizes are off the house ladder: rows at 20 or 14, buttons and overview labels at 12, three sizes inside one table **Done.** | style | medium |
| UN-19 | An overview label is always elided, another nearly so **Done.** | hidden info | quick |
| UN-20 | The entry's status text repeats the overview's subject in a section of its own; its reason text is a stale second "How it works" **Done.** | spread-out/redundant / over-explaining | medium |
| UN-21 | "Available to us" lines sit far from the button that acts on them; the vacant seat sends the player elsewhere **Done.** | spread-out/redundant | quick |
| UN-22 | Text sends players to "the chamber", which no longer exists as a place, and counts have drifted **Done.** | style | quick |
| UN-23 | Gate conditions are compound sentences, so one tick covers four conditions **Done.** | list | medium |
| UN-24 | Live sections still carry `#lore` explanations **Done.** | over-explaining | quick |
| UN-25 | The standing meter shows for countries that hold no standing **Done.** | hidden info / other | quick |
| UN-26 | How the UN Works restates concept descriptions **Done.** | over-explaining | quick |

### Cultural Hegemony and Covert Warfare ([detail](gui_audit/hegemony_covert.md), #1206)

Top priorities: the pull breakdown's order (CH-3; CH-1 is fixed here); the leaderboard as a one-line table (CH-2); a programmes cell in the overview (CH-9); each running operation's effect shown as modifier lines (COV-1); the launch decision in one place (COV-2); one name per operation (COV-3); the Tradecraft bar's retired eye marker (COV-6).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| CH-1 | A negative Standard of Living contribution is hidden from "Where Our Pull Comes From" (the bug is **fixed in this PR**; a rank-factor line in its hover remains) | hidden info | quick–medium | done: the bug in #1202; the row's hover now says the rank factor it is counted at (`ch_sol_rank_factor`) |
| CH-2 | The Top Cultural Powers board is ten copy-pasted two-line prose rows; make it a one-line table | list | large | done: a datamodel table (rank, flag, country, share, change, model swatch) over rows `ch_board_rebuild` writes; each country's own change; `TE_SELF_CHECK ch_board_rows` |
| CH-3 | The Pull Multiplier row sits *below* the Raw Score it is already part of | style / confusing structure | medium | done: the multiplier closes the components, signed; Raw Score alone under the rule |
| CH-4 | Where the funding cap comes from is shown nowhere | hidden info | medium | done: the level's hover gives the maximum, the institution, the two technologies and the modifier breakdown |
| CH-5 | Influence tier: three names per tier, a clash with vanilla's "Major Power", no thresholds anywhere (loc part done) | style + hidden info | quick–medium | done: the hover names the next tier and its threshold; one copy of the floors (`ch_tier_N_floor`) |
| CH-6 | Three concept descriptions still describe a "parenthetical" the panel no longer has (loc part done) | over-explaining | quick | done (#1202) |
| CH-7 | The board's hover says "yearly recount"; everything else says about twice a year (loc part done) | style | quick–medium | done: wording in #1202; a row's hover lists every non-zero component, adding up to its Raw Score |
| CH-8 | Live overview tooltips re-teach what the concept and How already say (loc part done) | over-explaining | quick | done (#1202) |
| CH-9 | The overview has no actionable reading; programme state lives two sections down | spread-out | medium | done: a programs cell in Banking's `te_banking_ov_cell`; the leader flags stay |
| CH-10 | Programme-condition lines read as complaints next to a tick (loc part done) | style | quick | done (#1202) |
| CH-11 | The funding tooltip is prose where its siblings are "Label: value" (loc part done) | style | quick | done (#1202) |
| CH-12 | Two colour keys for the same fifteen models, under different names (loc part done) | style / redundant | quick–medium | done: short names with the full name on hover, in two columns (three don't fit at 17) |
| CH-13 | "Program" and "Programme" for the same things (spelling, mentioned once) | style | quick | done: American ("Program") in the panel's text and its concepts, the owner's call |
| CH-14 | Duplicate model explanation between How and the concept | over-explaining | quick | done: `je_ch_how_models` cut to what the concept doesn't say |
| CH-15 | Type sizes predate the 17 / 20 / 16 ladder | style | medium | done: `ch_fontsize_row` / `_heading` / `_overview`, width-tested |
| COV-1 | A running operation never says what it is doing; the caught-operation hovers are prose, not modifiers | hidden info + style | medium | done: each row title's hover lists the operation's modifier lines; the caught-operation hovers too |
| COV-2 | Deciding a launch needs four places; the launch tooltip has none of the target-specific numbers | spread-out | medium–large | done: the launch tooltip gives our network and head start there and the upkeep added; one phase line and `concept_operation_phase` |
| COV-3 | Each operation has up to three names | style | quick | done: one name per operation (`iw_op_name_<type>`), spliced by the actions and the rows |
| COV-4 | Row titles are coloured red / yellow / green by an unstated rule that the exposure tiers contradict | style / hidden info | medium | done: plain titles and an Exposure line (`iw_exposure_tier`) |
| COV-5 | An operation's detection risk is a sentence, not the breakdown the shared block promises | list / style | medium | done: the risk's hover is a table of its terms that adds up to it (`iw_det_*`); Funding Stealth in points |
| COV-6 | The Tradecraft bar uses the eye-shaped marker the guide retired, and its "→" means something else | style | medium | done: threshold lines on both bars (`covert_bar_line`), headline `42 · next 60` |
| COV-7 | The Tradecraft hover is How-it-works, and drops one tier's unlocks (loc part done) | over-explaining + inconsistency | quick–medium | done: the hover is this month's reading; the rules are in How |
| COV-8 | The standing verdicts have no figure, no next threshold, and one shouts (loc part done) | hidden info / style | quick | done (#1202) |
| COV-9 | Row-button tooltips: the root they read may not exist there, and guard checks show as ticks (loc part done) | hidden info + over-explaining | quick–medium | done: (a) in #1202; (b) guards print only when they fail, the priority-3 gate only on that step |
| COV-10 | Tooltips that repeat How, and one that points at a panel that no longer exists (loc part done) | over-explaining / stale | quick | done (#1202) |
| COV-11 | "Funding is zero" is said in three places; the running state line explains (loc part done) | redundant / over-explaining | quick | done: the Funding state line shows only while funded with nothing running |
| COV-12 | Operation rows lack the target's flag; network rows spend two lines saying "nothing yet" | style / list compactness | medium | done: the flag; the network rows as a one-line table (flag, country, strength, ops, head start, report), the owner's call of 2026-10-27 |
| COV-13 | Launch-tooltip wording out of step with the panel (loc part done) | style | quick | done (#1202) |
| COV-14 | Type sizes predate the 17 / 20 / 16 ladder | style | medium | done: `covert_fontsize_row` / `_heading` / `_overview`, width-tested |

### Global Warming, Strategic Reserve and the Market panel ([detail](gui_audit/climate_reserve_market.md), #1207)

Top priorities: repeal tooltips rendered from the modifier (GW-5; the corrected prose is applied meanwhile); the movement-radicalism line as a `script_only` type (GW-3); the reserve rows' rate beside its buttons, and per-cell hovers in place of the 17-line row hover (SR-1, SR-2, SR-3); Top Emitters and Top Trade Partners as lists (GW-11, MKT-1); the trade charts' units and the hard-coded English (MKT-2, MKT-3).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| GW-1 | Policy tooltips: the "Applies to your own country. Available at 0.5 °C…" boilerplate (and Carbon Removal Support) (loc part done) | over-explaining / style | quick | done |
| GW-2 | Fossil-Fuel Tariffs' tooltip is a paragraph in front of its own modifier lines (loc part done) | over-explaining / style | quick | done |
| GW-3 | Policies move Environmental Movement radicalism: How now says so, the policy rows still don't (loc part done) | hidden info / style | quick–medium | done |
| GW-4 | Renewable Investment's money cost is invisible before adopting (hidden info) (loc part done) | hidden info | quick–medium | done |
| GW-5 | Repeal tooltips are prose that has drifted from the modifiers; render the modifier instead (loc part done) | style / hidden info | quick | done |
| GW-6 | Stale "market" framing on another market's Climate tab (loc part done) | hidden info / style | quick | done |
| GW-7 | Stale market-era wording in emissions tooltips and How (loc part done) | hidden info | quick | done |
| GW-8 | The penalty tooltip says the same thing twice, and the overview shows the anomaly twice (loc part done) | over-explaining / redundant | quick–medium | done |
| GW-9 | The same rules repeated across concept, How, overview and row tooltips (loc part done) | redundant / over-explaining | medium | done |
| GW-10 | The journal entry's reason text is an always-open explanation at the foot of the panel (loc part done) | over-explaining / redundant | quick | done |
| GW-11 | Top Emitters is five copy-pasted slots; a datamodel over a list would do it | list | medium | done |
| GW-12 | Two pairs of policy rows share an icon | style | medium | done; two policy icons are placeholders (art need) |
| GW-13 | Cooling is printed blue, not green (loc part done) | style | quick | done |
| GW-14 | Live tooltips teach accounting that belongs in How | over-explaining | quick–medium | done |
| GW-15 | Type sizes predate the 2026-10-17 ladder | style | medium | done |
| GW-16 | Minor points (always-ticked first conditions, identical role keys, degree spacing) | style / tidiness | quick–medium | done; Adoption Around the World kept (owner, 2026-09-29) |
| SR-1 | A collapsed row has rate buttons but no rate | spread-out / hidden info | medium | done |
| SR-2 | The row-wide hover repeats everything, and pops over the expanded figures | redundant / over-explaining | medium | done |
| SR-3 | The policy icon doesn't say which policy | hidden info | medium | done; per-policy icons optional (art need) |
| SR-4 | Preset tooltips are tables written as sentences (loc part done) | list / style | quick | done |
| SR-5 | One action, two words; one cap, four names (loc part done) | style | quick–medium | done |
| SR-6 | Concept descriptions read like design notes (loc part done) | over-explaining / style | quick | done |
| SR-7 | Rate-button hovers: filler, and no before/after (loc part done) | over-explaining / hidden info | quick–medium | done |
| SR-8 | The entry's reason text repeats How at the foot of the panel (loc part done) | over-explaining / redundant | quick | done |
| SR-9 | The overview has no "what needs attention" and only half the money | spread-out | large | done |
| SR-10 | Policy Settings are set in the smallest type, and the selected policy looks unavailable | style | medium | done |
| SR-11 | Minor points (status line vs overview, Status heading vs How, undefined "lane") | style | quick | done |
| MKT-1 | Top Trade Partners is five copy-pasted rows over fifteen rank variables | list | medium | done |
| MKT-2 | Three measures of trade on one tab, two of them unlabelled (the price bug is **fixed in this PR**; the labels remain) | style / hidden info | quick–medium | done |
| MKT-3 | The additions' text is hard-coded English | style / other | medium | done |
| MKT-4 | The table hides its best hover and uses an off-ladder size | hidden info / style | quick–medium | done |
| MKT-5 | All Goods tariffs: the cooldown has no end date, and the label's hover is unmarked | hidden info | quick–medium | done |

### Nuclear Weapons ([detail](gui_audit/nuclear.md), #1208)

All 21 findings are done (the GUI audit wave, 2026-10-27; play-test list `docs/testing/nuclear-playtest.md`). Top priorities were: one hover per choice row (NUC-2; NUC-1 is fixed here); the posture shown once with its change controls beside it (NUC-3), and when it can next change, which script already computes (NUC-4); readiness as a comparison table, with modifier lines for every level and authority (NUC-5, NUC-6); a compact crisis with Our Moves beside it (NUC-7); the leaderboard and world crises as lists (NUC-14).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| NUC-1 | No hoverable text in the panel is marked hoverable (row labels **fixed in this PR**; choice names and stepper values remain) | hidden info | medium | done: choice names, readiness levels and the tooltipped stepper values underlined |
| NUC-2 | Every choice row has two hovers covering the same ground, and the name's hover holds unique content | spread-out/redundant, hidden info | quick–medium | done: one hover per row; the crisis moves' only hover is the button |
| NUC-3 | The posture is shown twice, its tooltips restate the concepts, and its actions are far from it | spread-out/redundant, over-explaining | medium | done: one row per axis, a concept label, a Change toggle opening its choices beneath (three flags) |
| NUC-4 | "When can I change it?" is computed but never shown (loc part done) | hidden info | medium | done: a live line above each list, in each axis hover and in the overview |
| NUC-5 | Readiness levels should be a comparison table, and the current option of each list is not marked | list, hidden info | medium–large | done: readiness as a table; the option in force tinted in all three lists |
| NUC-6 | Prose where siblings render modifiers: Recessed, Routine and every launch authority; IG reactions told for some options only | style, hidden info | medium | done: twelve script_only display types, never-added display modifiers; no group reactions |
| NUC-7 | The crisis is eleven stacked lines, with Our Moves below all of them | spread-out/redundant | large | done: a headline, the readings as cells, Our Moves under them, an Outcomes table |
| NUC-8 | "Our stakes" is two bare numbers whose order flips with our side (loc part done) | hidden info | quick | done: the Outcomes table's Credibility column |
| NUC-9 | Crisis tooltips enumerate the general case beside the specific one | over-explaining | quick | done |
| NUC-10 | Crisis move naming: four verbs for one move (loc part done) | style | quick | done |
| NUC-11 | The taboo score, target and direction are shown twice, and the section colours the direction (loc part done) | spread-out/redundant, style | quick–medium | done: one row |
| NUC-12 | Warheads appear three times, with the estimate explained three times (loc part done) | spread-out/redundant, over-explaining | quick–medium | done: the count moved into Arsenal Size |
| NUC-13 | Credibility shown twice; it is used everywhere but is not a concept | spread-out/redundant, over-explaining | medium | done: Nuclear Credibility concept, nested in 24 effect lines; shown once |
| NUC-14 | Leaderboard and World Crises are fixed slot rows of concatenated text | list | large | done: datamodel tables over lists of capitals, with flags |
| NUC-15 | Burden of our arsenal: a modifier told as prose, with one effect left out | style, hidden info | quick | done |
| NUC-16 | Bar tooltips explain the design, and the survivability hover is long | over-explaining | quick | done |
| NUC-17 | Incident exposure: mechanics in the hover, factors as prose | over-explaining, style | medium | done: factor lines (multipliers, not a probability) |
| NUC-18 | "Chance of a halt": shown when it cannot apply, and its hover omits a case where it does | other, hidden info | quick–medium | done |
| NUC-19 | At Home rows repeat the same tenure sentence (loc part done) | over-explaining | quick | done (the loc part was all of it) |
| NUC-20 | Smaller style points (loc part done) | style | quick–medium | done: title-case headers, aligned names, the 17/20/16 ladder through the panel's templates |
| NUC-21 | The overview names states but not what needs attention | spread-out/redundant | large | done: Banking's cells |

### Space Race, Solar Colonization, Orbital Debris and Seabed ([detail](gui_audit/space_seabed.md), #1209)

Top priorities: reasons on about 470 greyed buttons (SPC-1); the concept family the owner described (SPC-3); a collapsed How Solar Colonization Works in place of seven live paragraphs (SPC-4); one Colonies table with a view switch (SPC-5); alerts in the overview (SPC-6); Target beside the destination (SPC-7); the Seabed overview's hovers about ours, and policies as modifier lines (SEA-1, SEA-2).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| SPC-1 | Greyed buttons in every colony, fleet and Space Command row hide their reason | hidden info | medium | done |
| SPC-2 | Defences and Spaceport tooltips still say fleets are not in the game (loc part done) | other, over-explaining | quick | done |
| SPC-3 | No concepts for solar colonization; the same rules are explained inline, often twice | over-explaining, style | medium | done (a concept per role added; the posture hover kept) |
| SPC-4 | Explanatory paragraphs open seven live colony sections; How the Space Race Works covers none of colonization | over-explaining, style | medium | done |
| SPC-5 | A colony's facts are spread over six sections; the colony name appears six times | spread-out/redundant | large | done |
| SPC-6 | The colonization overview shows the programme, not what needs attention | spread-out/redundant | medium–large | done |
| SPC-7 | Target sits far from the destination it changes; world rows give no hover on what a world offers | spread-out/redundant, hidden info | medium | done |
| SPC-8 | The Space Race tab buries our milestone under the other powers, and shows debris twice | spread-out/redundant | medium | done, as the owner revised it (Rivals kept in the tab) |
| SPC-9 | Rivals (5 slots) and Space Powers (8 slots) are fixed rows with "+N more" on hover; a list would show everyone | list | large | done; `TE_SELF_CHECK sr_powers_list` |
| SPC-10 | The rival and power estimate hovers repeat a four-sentence explanation in nine keys | over-explaining | medium | done |
| SPC-11 | The Space Race panel is off the house type ladder (rows 14, cells and the overview 12) | style | large | done |
| SPC-12 | Labels and column heads with a hover are not marked hoverable (loc part done) | hidden info | quick | done |
| SPC-13 | Stage names differ between the panel, the stage profile and the concept; the concept lists stages that don't exist (loc part done) | style, other | quick | done |
| SPC-14 | Mission Profile restates the approach the overview shows; "Approach" means two things (loc part done) | spread-out/redundant, style | quick | done |
| SPC-15 | Every colony row's autonomy drift hover shows the generic table, not that colony's terms | hidden info | medium | done |
| SPC-16 | "Fleets" names two different things; the same icon marks colony and war fleets | style | quick–medium | done (placeholder icon) |
| SPC-17 | How the Space Race Works restates the concepts it links | over-explaining | quick–medium | done |
| SPC-18 | Orbit's strike hovers teach the action's rules inline | over-explaining | medium | done |
| SPC-19 | Our Colonies is 1,100 hand-copied lines the generator could own | other, list | medium | done |
| SEA-1 | The overview's Policy and Regime hovers teach every option instead of ours | over-explaining, spread-out/redundant | medium | done |
| SEA-2 | Seabed policies describe their effects in prose, not modifier lines | style | medium | done |
| SEA-3 | The claimant rows are sentences under a table of columns | list, style | medium–large | done (columns, then a claimant list per basin; `TE_SELF_CHECK seabed_claimant_list`) |
| SEA-4 | Basin names read "in the Indian" / "in the Southern" (loc part done) | style | quick | done |
| SEA-5 | The +1 licence caveat is repeated in five basin hovers | over-explaining | quick | done |
| SEA-6 | The Pool column head restates the legend under the table | spread-out/redundant | quick | done |

### Grand Monuments and Colonial Empire ([detail](gui_audit/monuments_colonial.md), #1210)

Top priorities: colonial holdings and great-power pressure as lists (CE-1, CE-2); monument policies as modifier lines (GM-2; the boons are done here); an "Awaiting a Decision" section near the top (GM-3); figures for the three contested choices (GM-4); the colonial definitions as three concepts (CE-4).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| GM-1 | Opportunity boons hand-write their modifier instead of rendering it (loc part done) | style | quick | done (in #1202) |
| GM-2 | Monument policies are prose. Their shared boilerplate is repeated on four buttons | style / over-explaining | quick–medium | done |
| GM-3 | What needs a decision is far below the overview that flags it | spread-out/redundant | medium | done |
| GM-4 | The three contested choices say what happens in prose, with no figures | hidden info / style | medium–large | done |
| GM-5 | The world-wealth level rate sits in National Effects and repeats on every site row | spread-out/redundant | medium | done |
| GM-6 | Contested is explained in five places, two of them on the same row | over-explaining | quick–medium | done |
| GM-7 | "Undedicated", "Being Built", "under construction", "construction site", "Awaiting Dedication": one icon, stale text | style / other | quick–medium | done |
| GM-8 | Every upheld row carries three naming buttons, one usually greyed | spread-out/redundant | quick–medium | done (the quick form) |
| GM-9 | Trophy tooltips: stale "half the levels", and the same sentence on every hover of the state card (loc part done) | over-explaining / other | quick | done |
| GM-10 | Held Abroad repeats the section's "ways home" paragraph on every row; Trophies does the same with "what it counts for" | spread-out/redundant | quick–medium | done |
| GM-11 | Carrying off a trophy on display or a secondary monument hides its infamy cost | hidden info / style | medium | done |
| GM-12 | Opportunity section: the levels still needed are hidden, the How text says levels where the panel says grandeur, and two hovers repeat each other (loc part done) | hidden info / other / over-explaining | quick–medium | done |
| GM-13 | All eight IG approval rows share one generic paragraph and none says where its total comes from | over-explaining / hidden info | quick–medium | done |
| GM-14 | Archaeology has no How subsection, its mechanics sit in a live hover, and its terms aren't hoverable | over-explaining / hidden info / list | medium | done |
| GM-15 | How it Works: a nine-item list written as one sentence, and the step rules told twice and inconsistently (loc part done) | list / over-explaining | quick–medium | done |
| GM-16 | Smaller items in National Effects and the row | style | quick | done |
| GM-17 | Type sizes below the house ladder | style | medium | done |
| CE-1 | Colonial Holdings: territories and subjects are 8 fixed slots plus a "+N more" hover. Make them datamodels | list | large | done |
| CE-2 | International Pressure is a script-built text block. Make it a table of great powers | list / spread-out/redundant | medium–large | done |
| CE-3 | The live lists open with #lore captions that restate their own column-head hovers (loc part done) | over-explaining | quick–medium | done |
| CE-4 | The definitions of territory, colony and colonial subject are written out five times, and have drifted | over-explaining / style | medium | done |
| CE-5 | Pillar-row tooltips end in the same two boilerplate lines | over-explaining | quick | done |
| CE-6 | Programme rows: a 12-pt cost line packs four figures, the stability figure appears three times, and the hover's prose repeats its own modifier lines (loc part done) | style / spread-out/redundant / over-explaining | quick–medium | done |
| CE-7 | The overview carries an explanatory note, and the same rule is written four times | over-explaining | quick–medium | done |
| CE-8 | The Release button's hover repeats the row name's hover (loc part done) | over-explaining | quick | done (in #1202) |
| CE-9 | Every subject row repeats the band rule in its liberty-desire hover (loc part done) | over-explaining | quick | done (in #1202) |
| CE-10 | Stale text: the decolonization concept and both tab tooltips (loc part done) | other / hidden info | quick | done (in #1202) |
| CE-11 | Smaller style points | style | quick–medium | done |

### Demographics, the Nation tab, the Timeline Extended window and the system-tab gates ([detail](gui_audit/demog_nation_window.md), #1211)

Top priorities: the fertility tooltips promise figures no longer drawn (DEM-1); Work and Retirement and Longevity topics in How (DEM-3, DEM-2); the country panel's Modifiers list says nothing about the 249 modifiers it hands to the Nation tab (NAT-1); the Nation overview's hovers give each reading's cause, not a definition (NAT-3); one shape for every greyed-tab checklist (WIN-1, mostly done here).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| WIN-1 | The thirteen greyed-tab checklists read thirteen different ways (loc part done) | style | quick | done (2026-10-27 wave) |
| WIN-2 | "These are the journal entry's own panels: a change made here shows there too" on every journal-backed tab's tooltip and the launcher's (loc part done) | over-explaining | quick | done in #1202 |
| WIN-3 | The launcher's tooltip lists the tab strip in prose (loc part done) | over-explaining | quick | done in #1202 |
| WIN-4 | The Grand Monuments tab is headed "Monuments" | style | quick–medium | done (wave) |
| WIN-5 | Three identical "conditions met" keys | other | medium | done (wave) |
| NAT-1 | The country panel drops 249 modifiers with no word about where they went | hidden info | medium | done (wave) |
| NAT-2 | The tab's own list of what the country holds sits collapsed, with no count | hidden info | quick–medium | done (wave) |
| NAT-3 | The overview's tooltips define the term and point down, instead of giving the reading's cause | spread-out / style | medium | done (wave) |
| NAT-4 | Each score is explained three times: concept, row tooltip, How | over-explaining | quick | done (wave); the Algorithmic Mandate needs no change |
| NAT-5 | "Private Construction: excess in force" (loc part done) | style | quick | done in #1202 |
| DEM-1 | The fertility tooltips promise figures the panel no longer shows | hidden info | quick–medium | done (wave) |
| DEM-2 | The fertility tooltip is the How section's Fertility text again, over the table that itemises it | over-explaining | quick | done (wave) |
| DEM-3 | How Demographics Works has no Work and Retirement or Longevity topic, so their rules live in the live tooltips | over-explaining / structure | medium | done (wave) |
| DEM-4 | The Causes of Death pie's hover repeats the table beside it (loc part done) | redundant | quick | done in #1202 |
| DEM-5 | The pension buttons hand-write their interest-group reactions (loc part done) | style | quick | done in #1202 |
| DEM-6 | "N of our states have a youth bulge … each state's subtab shows its own": a list, not a hunt | list | medium–large | done (wave), the full version |
| DEM-7 | When the census is taken is told three ways, one of them wrong (loc part done) | style / accuracy | quick | done in #1202 |
| DEM-8 | Small consistency points (loc part done) | style / redundant | quick–medium | done (wave) |

### Additions to vanilla panels, and journal entries with no panel ([detail](gui_audit/vanilla_panels_other_jes.md), #1212)

Top priorities: State Collapse's status and goal line (JE-1; its reason is done here); World War's tension shown, and its buttons' conditions phrased (JE-3); Civil Rights' policy months shown (JE-4); Create New Religion's Proclaim effects made visible (JE-2); the construction market's read-out as a table, with one explainer (VAN-1–3); the state tiles' row hovers underlined (VAN-10).

| ID | Finding | Kind | Effort | Status |
|---|---|---|---|---|
| VAN-1 | Construction Market: an always-open intro paragraph, and the explainer written twice (loc part done) | over-explaining / spread-out/redundant | quick–medium | done |
| VAN-2 | Construction Market read-out: six sentences that should be a label/value table | style / list | medium | done |
| VAN-3 | Construction Market tooltips: the same three rules restated in five or six tooltips | spread-out/redundant / over-explaining | quick–medium | done |
| VAN-4 | Direct Construction section: an always-open paragraph that ends with a developer note | over-explaining / other | quick | done (a Site from the panel: play-test) |
| VAN-5 | Migration Crowding tile: the hover is a lesson in the curve, and repeats the tile (loc part done) | over-explaining | quick | done (#1202) |
| VAN-6 | Homeland Dynamics tile: rules in prose, rate units that disagree, and a tile that is always there (loc part done) | over-explaining / style / spread-out | quick–medium | done (c by owner decision) |
| VAN-7 | Solar Collector / Antimatter tiles: country-wide figures repeated in every state, and again on hover | spread-out/redundant | medium | done |
| VAN-8 | Seabed Licences tile: a five-basin table written as text, in every coastal state | list / spread-out/redundant | quick | done |
| VAN-9 | UN Mission tile: every kind's success rule in one sentence, though the state has one kind (loc part done) | over-explaining / list | quick–medium | done |
| VAN-10 | State tiles' per-row hovers are not marked hoverable | hidden info | medium | done |
| VAN-11 | Tourism card: headers inline their concept's description, and two tooltip pairs repeat each other (loc part done) | over-explaining / list | quick | done (#1202) |
| VAN-12 | Arable Land tile hover: repeats the rows, then explains the split-state accounting | over-explaining | quick | done |
| VAN-13 | Power bloc: the locked principle slots are a model; one small inconsistency | other / style | quick | done |
| JE-1 | State Collapse: the entry never says what the collapse does, and frames it as a goal (loc part done) | hidden info / over-explaining | quick–medium | done |
| JE-2 | Create New Religion: the Proclaim button hides everything it does, and the builder has no "where am I" | hidden info / style | quick–medium | done |
| JE-3 | World War: the number that drives everything is never shown, and greyed buttons print raw script | hidden info / style | quick–medium | done |
| JE-4 | Civil Rights: the endings depend on months nobody can see | hidden info | medium | done |
| JE-5 | Heir Education: a manual in the description, button text that repeats the engine's lines, one hidden cost (loc part done) | over-explaining / spread-out/redundant / hidden info | quick–medium | done |
| JE-6 | The four "debate" entries: status lines restate the law, and don't say what is still missing | hidden info / style | quick–medium | done |
| JE-7 | Human Augmentation's reason links the power-bloc concept by mistake (loc part done) | style / other | quick | done (#1202) |
| JE-8 | Mental Health's fail condition reads in days, and `_desc` keys shadow `_reason` | other | medium | partly done: (b) needs the game |
| JE-9 | Tax-code overrides of vanilla entries: three goal lines that can never be met under the rule | other | quick | done |

## Decisions for the owner

The owner answered all eleven on 2026-10-27, and the follow-up wave (every slice's open findings, plus the four audits of #1213) implements them:

1. **Global Warming repeal tooltips (GW-5):** render the modifier. Each repeal text is a plain "Ends:" header over the policy's own `GetStaticModifier(...).GetDesc`, accepting that the lines keep adopting's colours.
2. **Banking-style cell overviews:** yes, for all five (Tax Code, UN, Nuclear, space colonization, Strategic Reserve), replacing the earlier rounds' overviews. The owner asked that they not read as a formula: no "What needs you: you need to X, Y and Z", just X, Y and Z.
3. **UN Actions grid (UN-9):** the full version. Journal-entry buttons AI-only, scripted-GUI controls beside each figure, the Actions section gone, and Programmes open by default.
4. **UN proposal list (UN-7):** hide topics in force, put ready topics first, and show the ready count. Type, passage rule and target stay a line each (the 2026-09-28 shortening stands).
5. **Tax Code section order (TAX-14):** monitoring first (Bill Under Debate, Passed Bills, Promises), then Enacted Code, Draft Reform and Review.
6. **Grand Monuments "Awaiting a Decision" (GM-3):** as proposed, with Awaiting Dedication beside it and the Monument Policy buttons at the top of National Effects.
7. **Covert operation names (COV-3):** the diplomatic action's name, everywhere.
8. **Homeland tile (VAN-6c):** hidden where nothing can change; still shown for the paused cases.
9. **Space Race tab order (SPC-8):** our milestones first, then Space Powers, Orbit and How, with debris shown once. **Revised from the proposal: Rivals stays in each milestone's block.** The owner pointed out that it's actionable. It's each power's progress on this milestone, which says whether someone is close on our heels. Space Powers shows each power's furthest milestone, so the two agree only when a rival races the same one.
10. **Spelling:** American, as the player guide and the base game use. The wave sweeps the existing loc and the player guide.
11. **The type-size pass:** in this wave, every panel, Cultural Hegemony included (the wave reworks it, which ends its grandfathering).

## Tests that pin what would change

Each detail file names the test beside its finding. The ones most proposals touch:

- **Layout and order tests:** `test_tax_code_layout.py` (`STATUS`), `test_un_layout.py`, `test_nuclear_layout.py` (`FlagTest`, `OverviewTest`, `LabelBudgetTest`), `test_space_race_layout.py` (`HowItWorksTest`, which covers only the older sections), `test_grand_monuments_layout.py` (`STATUS`), `test_colonial_empire_layout.py` (the eight holdings slots), `test_cultural_hegemony_layout.py` (the board's ten hints).
- **Loc text tests:**
  - `test_monetary_*` pin sentences in the Monetary Policy tooltips;
  - `test_tax_code_estimates.py` and `test_tax_code_sguis.py` pin "release it", the snapshot row and the estimate wording;
  - `test_household_emissions.py` and `test_gw_top_emitters.py` pin two climate tooltips;
  - `test_demographics_registry.py` pins the fertility wording;
  - `test_un_terms_tooltips.py` pins the proposal hovers' splice.
- **Width budgets** follow the font templates where a panel has them (`test_banking_layout.py`'s `WidthBudgetTest` is the model). Panels without templates need them before a type-size pass.

## Tooling that would keep this from coming back

Four checks the audit ran by hand (#1213), now built as read-only audits in `POST_LOAD_AUDITS`. Each writes `docs/engine/<name>_report.md`, takes a check-tagged `# REVIEWED YYYY-MM-DD (<check>): rationale` suppression and fails `--strict` on an untagged flag or a stale tag. The base still held the backlog below when they landed (2026-10-27, main 2d92e98); once the slices and the backlog pass had fixed or reviewed every flag, all four joined CI's `--strict` steps (2026-10-27).

- **Long live tooltips** (`long_tooltip_audit.py`, check `long_tooltip`, tag trailing on the key's loc line): loc keys referenced from `.gui` files, outside How sections, over 500 rendered characters, the scan behind finding 7. 500 is above all but 9 of vanilla's 4,722 tooltip keys. On the base: 120 keys (289 over 300).
- **Hidden modifier lines** (`hidden_modifier_audit.py`, check `hidden_modifier`, tag on the `custom_tooltip = {` line): a `custom_tooltip` whose block holds an `add_modifier` and whose text renders no `GetStaticModifier` for it. On the base: 14 of the 26 such blocks.
- **Unmarked hovers** (`unmarked_hover_audit.py`, check `unmarked_hover`, tag on the tooltip's line or a row type's opening line): a hover of the mod's whose text has no `#tooltippable`, a row type's instance tooltips reported once at the type. On the base: 110. *Retired 2026-10-30:* vanilla underlines only 1 to 4% of its own text hovers (`gui_style_guide.md` rule 3), so the owner dropped the rule it enforced.
- **Greyed buttons without reasons** (`button_reason_audit.py`, checks `missing_reason` on the `enabled` line and `raw_condition` on the `is_valid = {` / `possible = {` line): a button enabled by `ScriptedGui.IsValid` whose tooltip has no `IsValidTooltip`, and a rendered `is_valid` or a scripted button's `possible` with a raw variable or script value test. On the base: 492 `missing_reason` (460 of them the generated Space rows, SPC-1) and 169 `raw_condition` blocks (144 of them Create New Religion's trait buttons, JE-2).
