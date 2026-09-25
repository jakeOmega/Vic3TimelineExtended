# Event Context Report

Events whose text does not match the context they fire in: events about a mod system that ignore it, and events that claim a country acted when it never chose to. Heuristic ranking for a human read — see `event_context_audit.py` for the rules. Suppress a reviewed flag with a check-tagged comment on its own line inside the event block: `# REVIEWED YYYY-MM-DD (<check>): rationale`.

- Events defined: **843**, visible: **825**, dispatch sites traced: **1019**
- `system_ungated`: **0** unreviewed, 11 REVIEWED
- `unchosen_self_action`: **0** unreviewed, 6 REVIEWED
- `imputed_foreign_action`: **0** unreviewed, 8 REVIEWED
- Tags to remove: **0**

## `system_ungated`

The event's text is about a mod system, but the event reads none of the system's state (game rule, journal entry, owned triggers/variables) and at least one dispatch site is not gated on it either. Gate it on the system (or make it the system-disabled fallback, as PR #418 did for `international_relations_events.6`/`.7`), or tie its outcome to the system's real state.

No unreviewed flags. ✅

### REVIEWED

- `modern_election_events.30` — events/modern_election_events.txt:2802 (REVIEWED 2026-09-25: hedged: failures some call a cyberattack; no foreign actor is named or confirmed)
- `modern_election_events.33` — events/modern_election_events.txt:3087 (REVIEWED 2026-09-25: a campaign proposal the voters debate, not an augmentation outcome)
- `movement_events_te.9` — events/movement_events_te.txt:1562 (REVIEWED 2026-09-25: scientists petition for trials; the options are the government deciding)
- `social_tensions_events.1` — events/social_tensions_events.txt:9 (REVIEWED 2026-09-25: a domestic terror attack, not a state covert operation)
- `un_events.2` — events/un_events.txt:135 (REVIEWED 2026-09-25: fired by the nuclear strike itself (extra_effects.txt); the UN condemnation of a real use)
- `un_events.12` — events/un_events.txt:1559 (REVIEWED 2026-09-25: a UN topic raised by a real colonial collapse (docket item 8); UN history, independent of the decolonization JE)
- `un_vote.1` — events/un_vote_events.txt:49 (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `un_vote.1` — events/un_vote_events.txt:49 (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `un_vote.2` — events/un_vote_events.txt:365 (REVIEWED 2026-09-25: the generic result event; the non-proliferation text shows only for that resolution)
- `wonder_events.1` — events/wonder_events.txt:14 (REVIEWED 2026-09-25: the space elevator is a wonder building the country chose to build, not space-race state)
- `wonder_events.6` — events/wonder_events.txt:273 (REVIEWED 2026-09-25: flavour of the space elevator wonder, not space-race state)

## `unchosen_self_action`

The title/description claims the recipient government did something, but the event can reach it without that country having chosen anything (a pulse, a journal-entry tick, or another country's option). Give the recipient the choice, gate the event on the action having happened, or reword it so it no longer claims an action the country never took.

No unreviewed flags. ✅

### REVIEWED

- `international_relations_events.103` — events/international_relations_events.txt:917 (REVIEWED 2026-09-25: "our intelligence operatives" is true: .103 reaches us only through .6.a/.c, and .6 only when the agent we chose to plant in .203.a is caught)
- `international_relations_events.105` — events/international_relations_events.txt:1097 (REVIEWED 2026-09-25: "our military expansion" is true: .105 reaches us only through .1.a, and .1 only through our own .201.a (the buildup we chose))
- `international_relations_events.106` — events/international_relations_events.txt:1127 (REVIEWED 2026-09-25: "our information campaign" is true: .106 reaches us only through .4.a, and .4 only through our own .202.a (the offensive we chose))
- `international_relations_events.107` — events/international_relations_events.txt:1157 (REVIEWED 2026-09-25: "our intelligence operatives" is true: .107 reaches us only through .6.b, and .6 only when the agent we chose to plant in .203.a is caught)
- `modern_election_events.25` — events/modern_election_events.txt:2337 (REVIEWED 2026-09-25: gated on a surveillance apparatus law (te_ea_has_surveillance_apparatus): the government does run the programme)
- `nuclear_crisis.7` — events/nuclear_crisis_events.txt:781 (REVIEWED 2026-09-25: the issuer chose the ultimatum through nd_nuclear_ultimatum_action; the weekly tick only reports that its dispute became a war)

## `imputed_foreign_action`

The event picks another country itself, says that country acted, and applies consequences to it. If that country is a player, it is punished for something it never chose. Tie the premise to real state (e.g. an active covert operation), let that country choose first, or drop the consequence on it.

No unreviewed flags. ✅

### REVIEWED

- `cultural_hegemony.15` — events/cultural_hegemony_events.txt:1470 (REVIEWED 2026-09-25: our reformers cite the hegemon's universities; the hegemon is not said to act)
- `decolonization_events.2` — events/decolonization_events.txt:202 (REVIEWED 2026-09-25: pressuring_power is picked only among great powers carrying gp_anti_colonial_stance, a stance each chose (decolonization_events.14.a, or its yes vote on the UN declaration via un_vote_effects); calling on colonial powers to decolonize is what that stance is.)
- `decolonization_events.11` — events/decolonization_events.txt:1215 (REVIEWED 2026-09-25: condemning_power is picked from great powers carrying gp_anti_colonial_stance, which they chose)
- `decolonization_events.19` — events/decolonization_events.txt:2437 (REVIEWED 2026-09-25: the former colony chose to nationalize (decolonization_events.15))
- `international_relations_events.5` — events/international_relations_events.txt:468 (REVIEWED 2026-09-25: the embargo is our own option; the rival is told what we chose (.102))
- `irredentism.3` — events/irredentism_events.txt:367 (REVIEWED 2026-09-25: false positive: the subject of "have begun" is the voices on both sides; this is the unifier's own proposal)
- `world_war_events.1` — events/world_war_events.txt:8 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `world_war_events.3` — events/world_war_events.txt:279 (REVIEWED 2026-09-25: tracked in #427 — gate on real pressure)
