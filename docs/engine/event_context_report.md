# Event Context Report

Events whose text does not match the context they fire in: events about a mod system that ignore it, and events that claim a country acted when it never chose to. Heuristic ranking for a human read — see `event_context_audit.py` for the rules. Suppress a reviewed flag with a check-tagged comment on its own line inside the event block: `# REVIEWED YYYY-MM-DD (<check>): rationale`.

- Events defined: **824**, visible: **806**, dispatch sites traced: **995**
- `system_ungated`: **0** unreviewed, 16 REVIEWED
- `unchosen_self_action`: **0** unreviewed, 7 REVIEWED
- `imputed_foreign_action`: **0** unreviewed, 21 REVIEWED
- Tags to remove: **0**

## `system_ungated`

The event's text is about a mod system, but the event reads none of the system's state (game rule, journal entry, owned triggers/variables) and at least one dispatch site is not gated on it either. Gate it on the system (or make it the system-disabled fallback, as PR #418 did for `international_relations_events.6`/`.7`), or tie its outcome to the system's real state.

No unreviewed flags. ✅

### REVIEWED

- `international_relations_events.2` — events/international_relations_events.txt:175 (REVIEWED 2026-09-25: tracked in #427 — becomes the covert-disabled fallback)
- `international_relations_events.4` — events/international_relations_events.txt:404 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.101` — events/international_relations_events.txt:893 (REVIEWED 2026-09-25: tracked in #427 — follows .2)
- `modern_election_events.30` — events/modern_election_events.txt:2802 (REVIEWED 2026-09-25: hedged: failures some call a cyberattack; no foreign actor is named or confirmed)
- `modern_election_events.33` — events/modern_election_events.txt:3087 (REVIEWED 2026-09-25: a campaign proposal the voters debate, not an augmentation outcome)
- `movement_events_te.9` — events/movement_events_te.txt:1458 (REVIEWED 2026-09-25: scientists petition for trials; the options are the government deciding)
- `social_tensions_events.1` — events/social_tensions_events.txt:9 (REVIEWED 2026-09-25: a domestic terror attack, not a state covert operation)
- `social_tensions_events.2` — events/social_tensions_events.txt:119 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `society_technology_events.14` — events/society_technology_events.txt:1258 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
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

- `international_relations_events.2` — events/international_relations_events.txt:175 (REVIEWED 2026-09-25: tracked in #427)
- `international_relations_events.103` — events/international_relations_events.txt:952 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.105` — events/international_relations_events.txt:1127 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.106` — events/international_relations_events.txt:1157 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.107` — events/international_relations_events.txt:1187 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `modern_election_events.25` — events/modern_election_events.txt:2337 (REVIEWED 2026-09-25: gated on a surveillance apparatus law (te_ea_has_surveillance_apparatus): the government does run the programme)
- `nuclear_crisis.7` — events/nuclear_crisis_events.txt:781 (REVIEWED 2026-09-25: the issuer chose the ultimatum through nd_nuclear_ultimatum_action; the weekly tick only reports that its dispute became a war)

## `imputed_foreign_action`

The event picks another country itself, says that country acted, and applies consequences to it. If that country is a player, it is punished for something it never chose. Tie the premise to real state (e.g. an active covert operation), let that country choose first, or drop the consequence on it.

No unreviewed flags. ✅

### REVIEWED

- `banking_cycle_events.45` — events/banking_cycle_events.txt:4636 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `cultural_hegemony.15` — events/cultural_hegemony_events.txt:1470 (REVIEWED 2026-09-25: our reformers cite the hegemon's universities; the hegemon is not said to act)
- `decolonization_events.2` — events/decolonization_events.txt:196 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `decolonization_events.5` — events/decolonization_events.txt:572 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `decolonization_events.6` — events/decolonization_events.txt:656 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `decolonization_events.11` — events/decolonization_events.txt:1178 (REVIEWED 2026-09-25: condemning_power is picked from great powers carrying gp_anti_colonial_stance, which they chose)
- `decolonization_events.12` — events/decolonization_events.txt:1289 (REVIEWED 2026-09-25: tracked in #427)
- `decolonization_events.19` — events/decolonization_events.txt:2391 (REVIEWED 2026-09-25: the former colony chose to nationalize (decolonization_events.15))
- `decolonization_events.20` — events/decolonization_events.txt:2560 (REVIEWED 2026-09-25: tracked in #427 — pass the real intervener from .19)
- `decolonization_events.21` — events/decolonization_events.txt:2706 (REVIEWED 2026-09-25: tracked in #427)
- `international_relations_events.1` — events/international_relations_events.txt:9 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.4` — events/international_relations_events.txt:404 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.5` — events/international_relations_events.txt:490 (REVIEWED 2026-09-25: the embargo is our own option; the rival is told what we chose (.102))
- `international_relations_events.6` — events/international_relations_events.txt:584 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `international_relations_events.8` — events/international_relations_events.txt:770 (REVIEWED 2026-09-25: tracked in #427 — tie to a real dispute)
- `irredentism.3` — events/irredentism_events.txt:367 (REVIEWED 2026-09-25: false positive: the subject of "have begun" is the voices on both sides; this is the unifier's own proposal)
- `movement_events_te.4` — events/movement_events_te.txt:325 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `social_tensions_events.2` — events/social_tensions_events.txt:119 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `society_technology_events.14` — events/society_technology_events.txt:1258 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `world_war_events.1` — events/world_war_events.txt:8 (REVIEWED 2026-09-25: tracked in #427 — the accused country gets the choice first)
- `world_war_events.3` — events/world_war_events.txt:279 (REVIEWED 2026-09-25: tracked in #427 — gate on real pressure)
