# Decolonization UI: open questions and ideas

The Colonial Holdings pass (2026-10-24) answered two of the owner's asks: the panel shows why the Colonial Empire
entry runs (the overview's "Colonies · Colonial subjects" line, and the two lists under it), and every action that
targets one territory or one subject sits on that target's row and opens a confirmation for it alone. What it
built is described in `mod_systems.md` § Decolonization System → Colonial Holdings and `journal_entry_systems.md`
§ Colonial Stability Widget → Per-target decisions. This file holds what it left for the owner to decide, and ideas
it did not build. Each item says what the change would be and what it costs.

## Decisions for the owner

1. **Should Dominion status steady the bar?** It gives no stability of its own: a dominion stops counting as a
   colonial subject, and the same change through vanilla's Increase Autonomy gives none, so the panel's button and
   vanilla's agree. A small reward (four months of Positive Colonial Development, say) would make it the "managed
   devolution" path it was historically (India and Pakistan in 1947 were dominions first), but would make the panel's
   button strictly better than vanilla's. A cost is the other way to set them apart: the Armed Forces' or the
   Landowners' disapproval, or prestige.
2. **A freed subject's stability boost** is the unilateral territory release's, +1 a month for 8 months. The event
   that offers the same grant to a restless subject (Winds of Change, `.1.c`) gives 150 days. One figure for both
   would be simpler; which?
3. **The AI's single releases still stack Peaceful Decolonization.** A release from a row grants it only when not
   held (`decol_chosen_release_rewards`), because a row at a time would pile up +15% prestige each. The AI's
   Release a Colonial Territory and Round Table (`.400`) still add a copy per release, as do the subject events and
   Planned Full Decolonization. Bringing `.400` and the subject events under the same helper would make the rule
   one rule; it changes AI balance a little.
4. **Should the AI use the per-target paths?** It frees subjects only when an event offers it (`.1`, `.3`) and
   never asks for dominion status. An AI review like the programmes' (monthly, a few gates: a colony at high
   liberty desire under a liberal government → dominion; a subject at 75+ → release) would make AI empires devolve
   more like history did. It needs its own weights and a self-check line.
5. **Font sizes.** The panel still sets its rows in the medium tooltip face (14). The style guide's ladder (rows 17,
   subheadings 20, overview 16; `gui_style_guide.md` rule 3) has not reached this panel. A pass would widen every
   fixed cell, and the territory row is already at its 476 budget with the Release button; it would need two-line
   rows or fewer columns.

## Ideas not built

- **Every territory, not eight.** The lists are eight fixed rows (the shape this widget has shipped and play-tested)
  with the rest named on hover, so a territory beyond the eighth has no button until larger ones go. A datamodel
  over a variable list of states (the tax code's relief rows, `GetList('te_tax_dr_relief_candidates')` →
  `Scope.GetState`) would list them all in a scroll area. Wait for the tax code's play-test (PT-24) to show that
  `Scope.GetState` works in a datamodel first.
- **Sort orders.** By GDP now. Colonies first, worst acceptance first, or (for subjects) highest liberty desire
  first would put the most urgent row on top. A small toggle above each list, client-side (`GetVariableSystem`),
  picking one of several stored orders from the monthly snapshot.
- **A per-territory weight column.** The weight on stability is on the name's hover
  (`colonial_territory_disp_weight`). A signed column, red or green, would show at a glance which colonies cost the
  empire most, but the row has no width left (see item 5 above).
- **Negotiated independence for subjects.** Subjects have only the unilateral grant (and, under Neocolonialism, on
  terms). A Round Table for a subject (its liberty desire falling while talks run, a better relations start, the
  Landowners' displeasure) would mirror the territories' choice.
- **The release region in the popup.** `.402` says how many states go with a territory and which people would form
  the new country, but not which states. An option tooltip that lists the marked states (`.401`'s per-state list
  under a header) would show it.
- **Per-colony programmes.** The three programmes act on every colony at once. Letting the player aim Investment or
  the Garrison at chosen territories (a state modifier per row, its cost per territory) is the deeper version of
  "actions beside their targets". It is a redesign of the programmes, their costs and the AI's review.
- **Liberation contagion on the button.** Each new country gives every other empire a year of Colonial Crisis. The
  Release hover could say so, and name the empires it would reach.
