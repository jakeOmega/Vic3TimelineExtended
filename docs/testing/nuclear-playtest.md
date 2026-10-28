# Nuclear Weapons play-test checklist

What the next play-test of the Nuclear Weapons panel should look at: the journal entry `je_nuclear_program` and the Military panel's Nuclear tab, which compose the same types. In-game checks don't gate the merge (CLAUDE.md, "In-game checks"). The console harness is `events/te_debug_nuclear_events.txt` and `events/te_debug_deterrence_events.txt` (`event te_debug_deterrence.3` option d opens a private crisis between two other countries).

## The GUI audit's rework (2026-10-27, #1208)

The panel was reworked from the 2026-10-27 GUI and localization audit (`docs/audits/gui_audit/nuclear.md`, NUC-1 to NUC-21). Nothing here rests on an unverified engine fact in script, so there is no self-check: every item is display, and each fails visibly (a blank cell, a raw key, an empty table, a misplaced child). Where an item uses an accessor or a shape new to this panel, it says so and names the fallback.

### Overview (NUC-21, NUC-4)

1. **Banking's cells.** The overview is a grid of boxes two to a row, each with its icon in an inset box down the left and three lines beside it, the same as the Banking overview's. The cells are `te_banking_ov_cell` itself (`banking_dashboard_widget.gui`), reused for the first time outside Banking. If a cell draws without its background or icon box, define a `te_nuclear_ov_cell` copy as the Seabed and Demographics panels did.
2. **The rows.** In a crisis, a Nuclear Crisis cell alone at the top (its stage, "Deadline: N wk", red from two weeks out). Then Program (state, "Next in N mo" or "Not progressing") and Warheads (the count, "World est. N"). While armed, Doctrine (a short name, "Change in N mo" or "Can change now") and Readiness (its name, "→ X" while moving, else the deterrent's weekly upkeep), then Launch Authority (short name, when it can change) and Credibility (Doubted, Steady or Trusted, "N of 100"). The taboo bar's row last.
3. **Captions are concepts.** Hovering Program, Warheads, Doctrine, Readiness, Launch Authority and Credibility opens the concept; hovering the rest of the cell, its breakdown.
4. **Nothing ends in "...".** At 16 points "Launch Authority" is the longest caption (budgeted 151 of 154). Check every short name ("No First Use", "Compellence", "On Warning") and "Deadline: 10 wk".
5. **Credibility's icon** is the guarantee article's as a placeholder (`docs/systems/nuclear_gui_icons.md` lists the art wanted).
6. **SelectLocalization with JournalEntry data.** The figures that pick between two keys ("Change in N mo" / "Can change now"; the deadline in red or not; readiness moving or its upkeep) read `JournalEntry.GetCountry.MakeScope.ScriptValue` inside the chosen key. Demographics proves the shape with `State`; if a figure is blank here, put the number in the calling key and choose only the words.

### Posture (NUC-3, NUC-4, NUC-5, NUC-6, NUC-1)

7. **One row per axis.** Doctrine, Readiness and Launch Authority each read "Label … value [Change]". The label is a concept and hovers as one (the textbox is not alwaystransparent); the value is underlined and its hover gives the modifier lines in force and when it can next change.
8. **Change opens the list beneath.** Each Change button reads Hide once open and opens that axis's choices directly under its row, a line above them saying when it can change (or that a stand-down holds readiness at Routine). The three open independently.
9. **The option in force is tinted** in the doctrine and authority lists, and the readiness level ordered (not the one in force while moving) in the readiness table, the same tint as Covert's Funding Levels. Its button is the greyed one.
10. **The readiness table.** Four rows under a head: the level (underlined, its hover the level's modifier lines), the weekly upkeep at that level, the survivability a crisis would count there, and Order. The figures match the old tooltips' (`nd_upkeep_weekly_at_readiness_N`, `nd_effective_survivability_at_readiness_N`).
11. **Display modifiers that nothing adds.** Every readiness level's and launch authority's hover prints `GetStaticModifier('nd_readiness_terms_N')` / `('nd_authority_terms_N')`: static modifiers never added to any country, carrying `script_only` display types (`nuclear_deterrence_display_types.txt`). Check that the lines render with their names and colours, the boolean lines (Nothing Can Be Launched…, An Incident Can End in a Launch…) as a line without a number, and that `GetCustom` → `GetStaticModifier` in the axis rows' hovers renders the same lines. `GetStaticModifier` reads a definition, so a modifier nobody holds should print as the UN's and Grand Monuments' previews do; if the lines are blank, write the figures as prose under the existing modifiers' `GetDesc`, which already render.
12. **Choice rows are widgets now.** Every choice row (doctrine, authority, the crisis moves, Lift / Dismantle / Halt) is `nd_choice_row`, a fixed 480 x 32 widget with the name and the button in its blocks. Check no row draws an empty name or a button over the name.

### Crisis (NUC-7 to NUC-10, NUC-2)

13. **The headline.** "Against France · we made the threat · over a war, in public" (as the target: "the threat is against us"). The line is printed at our own scope with the opponent through a temporary scope saved in a nested one (`nd_crisis_opponent_sgui`), the shape World Crises' old rows used. If the opponent's name is blank, print the line inside the opponent's scope and read our words through `ROOT.GetCountry.GetCustom`.
14. **The grid.** Stage (its word, "Week N of 52"), Deadline ("N weeks", then we decide / then they decide), Danger and Pressure (a word over "N of 100"; Pressure reads Firm, Wavering, Yielding or Breaking at 50 / 70 / 85), then Follow-through and Next pressure, shorter. The danger and pressure hovers keep their breakdowns.
15. **Our Moves** sit right under the grid. Each move's only hover is its button's: the conditions, then what it does. The names are not underlined.
16. **Outcomes.** Three rows under a head: They concede / We concede, We back down / They back down, Both stand down, each with what happens and the credibility change. Compare the figures with the outcome notice when the crisis ends: issuer +10 / +15 (public) on a concession, -5 / -15 on backing down, a stand-down +5 or -5 (a public demand traded away); target -5, +10, +5.

### Lists (NUC-14)

17. **The datamodels.** Nuclear Powers and World Crises are tables over `GetGlobalVariable('nd_lists_store').GetList(...)` (proven for Cultural Hegemony's history chart), each item read with `Scope.GetState` (proven by Demographics) and the country with `State.GetOwner`. `State.GetOwner` off a datamodel item is new to the mod (Grand Monuments uses it on a state panel; covert reads `GetState.GetCountry` off a `Var`). If the flags or names are blank, try `State.GetCountry`.
18. **Nuclear Powers.** Up to ten rows, largest first, each a flag (name on hover, a click opens the country), the name, the world's estimate and the public doctrine's icon (its name on hover). Our row is tinted. It appears once the world's monthly step has run after the first warhead (`nd_powers_listed_sgui`).
19. **World Crises.** One row a crisis, most dangerous first: the issuer's flag → the target's (the target through `Var('nd_wc_target_cap').GetState.GetOwner`), the stage, the danger. A crisis of ours is tinted. The row's hover (an `ExecuteTooltip` rooted at `State.GetOwner` from a datamodel item's tooltip) names both and gives the dispute, the clock, talks, a guarantor and a private warning.
20. **`tiny_flag` fits** its 40 x 28 box in a 30-high row.

### Forces, taboo, reputation (NUC-11 to NUC-18)

21. **Warheads held** sits under Arsenal Size, "N (est. M)", with " · treaty: N", " · UN ban: N" or " · dismantling" when they apply.
22. **Chance of a halt** reads "not delegated" under Central Authorization, the figure under the other three.
23. **Incident exposure's hover** ends with four factor lines ("×4.0  Readiness, against Routine", doctrine, crew strain, command reliability) and, in a crisis, the danger's word.
24. **One taboo row**, "62 → 68 · Strong", no green or red on the direction; the overview's bar hover is two sentences.
25. **Credibility** is a concept: the effect lines that name it ("Our credibility falls by 15") underline the word and hover its concept, in events as in the panel.
26. **The Burden of the Bomb** hover prints the modifier's lines, UN Authority Target among them.

### Type sizes (NUC-20)

27. **17 / 20 / 16.** Rows, values, buttons and notes at 17 (EBGaramond), subheadings at 20, the overview at 16 (the tooltip face), all through `te_nuclear_fontsize_*` (`nuclear_deterrence_widget.gui`). Check that the larger rows fit their cells without "..." (Survivability's 94-wide value, the At Home tables, the steppers) and that the taboo history's subsection header reads at 17.

## The crisis rework, phase 1 (2026-10-28)

What `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` phase 1 changed (survivors, launch authority, the chance of a halt, war exposure, the launch under attack, stakes, co-belligerents). The numbers were tuned offline (`scripts/analysis/nuclear_incident_rates.py`, `test_nuclear_incident_risk.TestSpecBands`); the game has to show the mechanisms work.

28. **First-strike survivors.** An armed country with a rival shows "First-strike survivors: N of M" in Forces; the hover names the rival and its three figures are numbers, not blanks. An armed country with no rival, war, crisis or hostile armed neighbor shows no row. Fallback if the rival's name is blank: drop it from the hover header.
29. **Pressure breakdown.** In a crisis between two armed powers, the pressure hover lists "Whether the threatened side could disarm the threatening side first" when the issuer is small, and a crisis over a play lists "What the threatening side demands"; the danger hover lists the vulnerable side's forces when survivability is under 50. The listed parts add up to the total.
30. **Authority hovers.** Each launch-authority choice lists its launch credit and "Survives a Strike on the Capital" (Delegation, Launch on Warning, Automatic Retaliation); the safeguards hover lists −5% launch credit per level.
31. **The launch under attack.** In an Acute crisis with an armed rival at peace, force a warning (`event te_debug_deterrence.2`, or wait): "Give the launch order" is available under every doctrine but No First Use, and greyed with the context line outside a war or an Acute crisis. Ordered at peace, it opens a peacetime exchange, as an unordered launch does.
32. **Co-belligerent cover.** An unarmed country fighting beside an armed one is warned or struck by their common enemy: the armed ally gets "A Promise Called In" with the co-belligerent text, once; walking away costs 5 credibility and the ally gets "We Stand Alone".
33. **The AI's posture.** Over an observer run, AI safeguards spread over 0–3 (not stuck at 2–3), and AI powers that can't make their force survivable move to Delegation, Launch on Warning or Automatic Retaliation, and back to Central once the threat passes. `nuclear_observer_report.py` reports Acute crises, use per Acute crisis, near misses and launches nobody meant; spec §2.1's targets are about 6–10% use per Acute crisis.

## Self-checks

| Line | What it tests | If BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK\|BROKEN nd_stakes_states` (once a game, the first crisis over a play with a state-taking goal) | `is_target_of_wargoal` finds a play's (not only a war's) goal on a state, so stakes count −10 a state | Nothing to swap: stakes already fall back to −10 per state-taking goal type in a play. Drop the per-state count from plays if it never reads OK |

| `TE_SELF_CHECK OK\|BROKEN nd_trigger_temp_scope` (once a game, the first month an armed country has a main rival) | A script value sees a scope a trigger saved with `save_temporary_scope_as` (the GM precedent `gm_state_tr_holds_half` is also unread) | The opening preview's "Their arsenal would survive" and "could disarm ours first" lines never show, and the AI's stake gate never blocks a threat. Fallback: compute the preview's line from the target's stored `nd_survivors_main` when its main rival is the issuer, and drop the stake gate |

The 2026-10-27 GUI rework rests on no engine fact in script; its accessors are GUI facts, listed with their fallbacks above.
