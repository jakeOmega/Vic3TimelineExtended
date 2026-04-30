# Decolonization Mechanics Review

## Status: implemented

All 10 proposed changes below were implemented as a session deliverable
(see decolonization-related changes in `common/journal_entries/`,
`common/scripted_buttons/`, `common/scripted_effects/decolonization.txt`,
`common/scripted_progress_bars/`, `common/static_modifiers/`,
`common/on_actions/`, `common/technology/technologies/era_6.txt` &
`era_7.txt`, `events/decolonization_events.txt`, and the corresponding
localization files). This document is preserved as the design rationale.

A note for future audits — two of my original concerns turned out to be
based on incomplete inspection rather than missing implementation:

- **GP-condemners pressure:** I claimed it was display-only. It was not —
  it already drained the bar at -0.6 per condemner. The implementation
  added *escalating tier-based* pressure on top of the linear baseline
  (extra -1.0 at 4+, extra -2.0 at 6+). The original claim "wired or
  display-only" should have been answered by reading the bar's
  `monthly_progress` block first.

- **Event firing density:** I claimed the writing wasn't being seen. The
  random_list weights in `decolonization_events_on_action` actually
  produce ~10 events per playthrough already. Only minor weight tuning
  was applied (event #2 bumped 10→15).

The remaining concerns (status-band modifiers, path-dependent resolutions,
metropole-side pressure, successor-state legacies, the Round Table
decision, button rewording, tech era) all required real implementation.

## Scope of this review

The mod's decolonization system is more developed than a quick scan suggests:

| Component | File | Size |
|---|---|---|
| Journal entry | `common/journal_entries/je_colonial_empire.txt` | 164 lines |
| Events | `events/decolonization_events.txt` | 2900 lines, 23 events |
| Scripted effects | `common/scripted_effects/decolonization.txt` | 251 lines |
| Buttons | `common/scripted_buttons/colonial_empire_buttons.txt` | 5 buttons (invest/garrison/assimilate/release/planned) |
| Tech gate | `decolonization` (era 7) | |
| Game rule | `decolonization_rule` (toggleable) | |

The 23 events are not just `200` (success) and `201` (failure) — there
is a substantive event chain (events 1–21) covering thematic beats:

- 1 "Winds of Change", 2 "The World is Watching", 3 "The Price of Empire"
- 4 "Whose Language Do We Dream In?", 5 "Old Ties, New Terms"
- 6 "Debts of Empire", 7 "Year One", 8 "These Dark Satanic Mills of Empire"
- 9 "Trouble in [colony]", 10 "Common Bonds", 11 "Judged by New Standards"
- 12 "Powerful Friends", 13 "Blood in the Colonies", 14 "The Colonial Question"
- 15 "The Nationalization Question", 16 "The Partition Question"
- 17 "Whose Country Is This?", 18 "The Strongman's Promise"
- 19 "The Crisis", 20 "Gunboats in the Harbor", 21 "The Non-Aligned Path"

This review evaluates the system against three criteria the user named:
**interesting**, **fun**, **realistic**.

---

## Component-by-component review

### Journal entry triggers

**Shown when:** game rule + tech `decolonization` researched. (Era 7,
roughly the 1960s in mod time.)

**Possible:** country has at least one overseas colonial state.

> *Concern:* The tech gate at era 7 means decolonization simply doesn't
> exist before then. Historically the wave starts with India (1947) and
> the British/French withdrawals through the early 60s — that maps to
> era 6 in vanilla / mod chronology. **Era 7 is late.**
>
> *Recommendation:* Move the `decolonization` tech to era 6 so the JE
> can fire from roughly the historical start of the wave rather than
> the late-1960s ceiling era 7 implies.

### Progress bar (`colonial_stability_bar`) — 5 status bands

| Bar value | Status | Modifier |
|---|---|---|
| ≥90 | Solidified | (none) |
| 65–89 | Stable | (none) |
| 40–64 | Strained | (none) |
| 20–39 | Crumbling | `colonial_empire_under_pressure_modifier` |
| <20 | Collapsing | `colonial_empire_crumbling_modifier` |

The bar accumulates from button policies (invest/garrison/assimilate
push it up; do-nothing lets pressure events push it down) and from
event outcomes (positive / negative `colonial_stability_*_event`
modifiers, mostly 60–240 days each).

> *Concern:* The two modifiers (Stable / Solidified) at the top end have
> **no associated mechanical effects** — they're status-only. The
> modifiers fire only at `crumbling` and `collapsing`. So 65% of the
> bar's range produces no in-game change other than the displayed text.
>
> *Recommendation:* Add at least a small positive modifier at the
> Solidified band (e.g. `state_loyalists_from_political_movements_mult`,
> small `country_authority_add` from "the empire holds together") so the
> player sees a reason to push toward the top, not just stay above 40.

### Civil rights movement coupling

The JE applies `colonial_pressure_movement_radicalism` (at <40%) and
`colonial_crumbling_movement_radicalism` (at <20%) **specifically to
the civil rights political movement**. This is a clean idea — the
empire collapsing radicalizes the civil rights movement at home.

> *Recommendation:* Keep this. It's the best mechanical idea in the
> system. Maybe extend it: at the Crumbling band, also pull pop support
> *toward* the civil rights movement (using
> `state_pop_support_movement_civil_rights_mult` from Task 8) — the
> empire visibly collapsing is itself a recruiting argument.

### The 5 buttons

| Button | Effect | Bar push | Cost |
|---|---|---|---|
| Invest in development | development modifier on colonial states | + | money / influence |
| Military garrison | garrison modifier (stability) | + | military supplies / morale |
| Cultural assimilation | assimilation modifier (cultural pull) | + | bureaucracy / authority |
| Release colonial territory | one state independent | (one-shot) | infamy reduction? |
| Planned decolonization | controlled withdrawal | (one-shot) | (gradual) |

> *Concern (overlap):* "Invest in development" and "cultural
> assimilation" both push the bar up via similar narrative levers.
> Mechanically distinct (one is `colonial_development_investment_modifier`,
> the other `colonial_cultural_assimilation_modifier`) but from the
> player's seat they answer the same question — "I'll spend resources
> to keep them quiet."
>
> *Recommendation:* Differentiate them more sharply by intended outcome:
> - "Invest in development" → improves the colony's economy and reduces
>   liberty desire from poverty. Slow, sustained effect.
> - "Cultural assimilation" → cultural acceptance of the colonized
>   over time, but **raises radicalism** in pops opposed to assimilation.
>   A risk/reward play: succeeds gradually, but if you fail, you create
>   the very nationalism that decolonizes you.
>
> The current incentives don't push the player to choose between them
> based on circumstance — they all "push the bar up". Adding side
> effects (radicalism, GP condemners, etc.) gates them per situation.

> *Concern (rebrand):* "Cultural assimilation" as a *button* the player
> clicks is more uncomfortable than the historical reality is, which is
> already plenty uncomfortable. Vanilla buries the same mechanic in
> homeland-acceptance triggers and rarely puts it on a button. The
> button isn't necessarily wrong, but the loc deserves a careful pass.

### "GP condemners" pressure axis

The status_desc displays a separate pressure track based on
`colonial_gp_condemners_count` — Great Powers condemning your colonial
empire. Five tiers (none / low / moderate / high / extreme).

> *Concern:* This is *displayed* but I see no mechanical link to the
> stability bar or to the events themselves. It's purely flavor text.
>
> *Recommendation:* Wire it. A simple coupling: at "high" pressure,
> add a passive monthly drain on the bar; at "extreme", trigger
> diplomatic events (Suez-style ultimatums). The display promises the
> player something the system isn't delivering.

### Events 1–21 themes

The event chain has good thematic coverage:

- **Cultural / linguistic identity:** ev 4 ("Whose Language Do We
  Dream In?"), ev 8 ("Dark Satanic Mills"), ev 10 ("Common Bonds"),
  ev 17 ("Whose Country Is This?")
- **Economic decolonization:** ev 6 ("Debts of Empire"),
  ev 8 (factories), ev 15 ("Nationalization Question")
- **Geopolitical pressure:** ev 12 ("Powerful Friends"),
  ev 20 ("Gunboats"), ev 21 ("Non-Aligned Path"), ev 11 ("Judged by New Standards")
- **Violence and unrest:** ev 9 ("Trouble in [colony]"),
  ev 13 ("Blood in the Colonies"), ev 19 ("The Crisis")
- **Specific political moments:** ev 1 ("Winds of Change"),
  ev 2 ("The World is Watching"), ev 3 ("Price of Empire"),
  ev 14 ("Colonial Question"), ev 16 ("Partition Question"),
  ev 18 ("Strongman's Promise"), ev 5 ("Old Ties, New Terms")

This is genuinely good thematic range. Macmillan's "Wind of Change"
speech and Suez and Algerian-style violence are all represented.

> *Concern (frequency):* I haven't traced the firing rules, but with
> 21 events total spread across the entire decolonization arc, an empire
> with several colonies might see only 2–3 events before resolution.
> The work that went into the writing isn't being seen.
>
> *Recommendation:* Audit firing weights and cooldowns when implementing.
> Aim for ~6–10 events visible per playthrough of the JE.

> *Concern (path differentiation):* Without tracing all 21, it's
> unclear whether the player sees a coherent arc or a random shuffle.
> Realism suggests early events should be agitation/tension and later
> events should be open crisis — a soft narrative arc, not random.
>
> *Recommendation:* If not already, gate later-numbered events on
> bar value below some threshold, or on prior events having fired.

### Resolution events 200 / 201

- **200 ("The Empire Endures"):** bar reaches 100. The empire stays.
- **201 ("The Empire Crumbles"):** bar reaches 0. Colonies independence-cascade.

> *Concern:* Two outcomes. The historical record offers more textures:
> negotiated transition (Commonwealth / Francophonie), bloody
> withdrawal (Algeria / Vietnam), partition (India / Palestine),
> economic-only retreat (Suez), and "we left a generation later than
> we should have" (Portuguese colonies).
>
> *Recommendation:* Split the success / fail outcomes by the path the
> player took:
> - **Bar reaches 100 with high "investment" button usage** → "The
>   Commonwealth Path" (lasting cultural ties, soft power retention).
> - **Bar reaches 100 with high "garrison" button usage** → "The
>   Iron Fist" (succeeded but at cost of pariah status; high infamy).
> - **Bar reaches 0 from invest+assimilate path** → "Negotiated
>   Withdrawal" (cleanish exit, friendly successor states).
> - **Bar reaches 0 from garrison-only path** → "The Empire Bleeds Out"
>   (current ev 201 — bloody, hostile successor states).

### Realism check (1947–1990 wave)

The system models the "managed decline" pole well — buttons capture
British / French postwar policy choices. It under-models:

- **Internal politics of the metropole.** In reality, decolonization
  was driven by domestic taxpayer fatigue, conscription unrest,
  intelligentsia pressure (Sartre, Hannah Arendt), and the rise of
  the welfare state competing for budget. The mod's intelligentsia /
  civil rights coupling exists but is light.
- **Cold War alignment as a forcing function.** The US and USSR both
  pressured European empires to decolonize for their own reasons.
  "Powerful Friends" (ev 12) hints at this but it's one event.
- **Successor-state governance.** When a colony becomes independent
  it's spawned via `form_decolonized_country` — but the choice of
  *what kind of state it becomes* (democratic / authoritarian /
  socialist) appears scripted (random HSV color, default ideology).
  The historical record shows liberation movements often pre-determined
  the post-independence regime.

> *Recommendation list:*
> 1. Add 2–3 metropole-side events ("Conscription Crisis", "The
>    Treasury Says No", "The Intelligentsia Petition") that move the bar
>    *down* based on domestic conditions, not colonial ones.
> 2. Cold War coupling: bar drains faster when the player is rivaled
>    by a different-bloc Great Power that is currently sponsoring
>    anti-colonial movements.
> 3. `form_decolonized_country` should choose the new country's
>    initial laws/ideology based on the path that led to independence
>    (post-violence → ethnostate, post-negotiation → multicultural,
>    post-nationalization → command economy).

### Fun check

What does the player do moment-to-moment?

- Watch a bar.
- Click 3 maintenance buttons every few years.
- Read 2–3 events and pick A or B (typically: stand firm / give in).
- Eventually win or lose.

> *Concern:* The current loop is closer to "watch a system" than
> "play a system". The buttons are mostly fire-and-forget toggles, and
> events present binary choices.
>
> *Recommendation:* Add at least one **proactive** mechanic the player
> reaches for in response to specific situations:
> - A scripted decision "Convene the Round Table Conference" (one-time
>   per colony, expensive in influence/authority, locks in a
>   negotiated-transition path that gives more bar but accelerates
>   eventual independence). Lets the player play **for** independence
>   strategically, not just against it.
> - The five colonial empire buttons could become exclusive (only one
>   active at a time per state, not per country). Forces meaningful
>   geographic prioritization.

---

## Open questions for the back-and-forth phase

1. **Tech era:** the `decolonization` tech is currently era 7 — should
   it move to era 6 to match the historical start of the wave?
2. **GP-condemners pressure track:** wired or display-only by design?
3. **Event firing density:** how many events do you typically see
   in one playthrough? Is the writing being seen?
4. **Successor-state archetype:** does
   `form_decolonized_country` already pick laws/ideology by path, or
   is it random?
5. **Solidified vs Stable vs Strained:** intentional that the top
   3 bands have no mechanical effects?

---

## Findings summary

**Strong points:**
- The 21-event chain has genuinely good thematic coverage.
- Civil rights movement coupling is a clean idea.
- The 5 status × 5 GP-pressure matrix gives the system rich state.

**Concrete proposed changes (no code yet — for follow-up):**

1. **Lower the `decolonization` tech from era 7 to era 6.**
2. **Add modifiers to top 3 status bands** (Solidified / Stable / Strained).
3. **Wire GP-condemners pressure** to the bar (passive drain at high tiers).
4. **Differentiate "Invest in Development" and "Cultural Assimilation"** with
   real tradeoffs (cultural assimilation increases radicalism in opposed pops).
5. **Audit event firing weights** so 6–10 events fire per playthrough.
6. **Add metropole-side bar pressure** (intelligentsia / treasury / conscription
   events that drain the bar from domestic conditions).
7. **Path-dependent resolution**: split events 200/201 into 4 outcomes by the
   button mix the player used.
8. **Path-dependent successor states**: `form_decolonized_country` picks
   ideology / laws based on the path that led there.
9. **Optional fun-loop addition**: a "Round Table Conference" decision per
   colony for a negotiated-transition path.
10. **Reword "Cultural assimilation" button text** with care for the
    historical sensitivity, even if mechanic stays.

These are listed in roughly increasing implementation cost. Items 1–3 are
small (couple-dozen-line changes). Items 7–8 are large (event re-architecture
+ effect refactor).
