# Event Context Report

Events whose text does not match the context they fire in: events about a mod system that ignore it, and events that claim a country acted when it never chose to. Heuristic ranking for a human read — see `event_context_audit.py` for the rules. Suppress a reviewed flag with a check-tagged comment on its own line inside the event block: `# REVIEWED YYYY-MM-DD (<check>): rationale`.

- `system_ungated`: **0** unreviewed, 11 REVIEWED
- `unchosen_self_action`: **0** unreviewed, 5 REVIEWED
- `imputed_foreign_action`: **0** unreviewed, 6 REVIEWED
- Tags to remove: **0**

## `system_ungated`

The event's text is about a mod system, but the event reads none of the system's state (game rule, journal entry, owned triggers/variables) and at least one dispatch site is not gated on it either. Gate it on the system (or make it the system-disabled fallback, as PR #418 did for `international_relations_events.6`/`.7`), or tie its outcome to the system's real state.

No unreviewed flags. ✅

### REVIEWED

- `arch_events.1` — events/archaeology_events.txt (REVIEWED 2026-10-16: the World War it mentions is a date in the Sutton Hoo historical note (gm_arch_site_sutton_hoo_history), not the world war system; the event reads its own system (gm_system_enabled, the Grand Monuments rule))
- `arch_events.2` — events/archaeology_events.txt (REVIEWED 2026-10-16: the World War it mentions is a date in the Sutton Hoo historical note (gm_arch_site_sutton_hoo_history), not the world war system; the event reads its own system (gm_system_enabled, the Grand Monuments rule))
- `extra_law_events.32` — events/extra_law_events.txt (REVIEWED 2026-11-12: the two descriptions that name nuclear weapons show only under te_ea_no_first_strike_pledge_available, which reads the nuclear rule and the technology)
- `modern_election_events.30` — events/modern_election_events.txt (REVIEWED 2026-09-25: hedged: failures some call a cyberattack; no foreign actor is named or confirmed)
- `modern_election_events.33` — events/modern_election_events.txt (REVIEWED 2026-09-25: a campaign proposal the voters debate, not an augmentation outcome)
- `movement_events_te.9` — events/movement_events_te.txt (REVIEWED 2026-09-25: scientists petition for trials; the options are the government deciding)
- `un_vote.1` — events/un_vote_events.txt (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `un_vote.1` — events/un_vote_events.txt (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `un_vote.1` — events/un_vote_events.txt (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `un_vote.1` — events/un_vote_events.txt (REVIEWED 2026-09-25: the generic vote event names every resolution topic; each topic is raised by its own gated docket item)
- `wonder_events.6` — events/wonder_events.txt (REVIEWED 2026-09-25: flavour of the space elevator wonder, not space-race state)

## `unchosen_self_action`

The title/description claims the recipient government did something, but the event can reach it without that country having chosen anything (a pulse, a journal-entry tick, or another country's option). Give the recipient the choice, gate the event on the action having happened, or reword it so it no longer claims an action the country never took.

No unreviewed flags. ✅

### REVIEWED

- `international_relations_events.105` — events/international_relations_events.txt (REVIEWED 2026-09-25: "our military expansion" is true: .105 reaches us only through .1.a, and .1 only through our own .201.a (the buildup we chose))
- `modern_election_events.25` — events/modern_election_events.txt (REVIEWED 2026-09-25: gated on a surveillance apparatus law (te_ea_has_surveillance_apparatus): the government does run the programme)
- `nuclear_crisis.7` — events/nuclear_crisis_events.txt (REVIEWED 2026-09-25: the issuer chose the ultimatum through nd_nuclear_ultimatum_action; the weekly tick only reports that its dispute became a war)
- `nuclear_loose.9` — events/nuclear_loose_events.txt (REVIEWED 2026-09-26: "Our agents" is d_covert's, shown only for nd_loose_recovered_how = 2, which only the recipient's own covert operation sets (covert_secure_material_action, which it launched); inspection, the article and the convention have their own texts)
- `un_vote.1` — events/un_vote_events.txt (REVIEWED 2026-10-25: "our veto record" shows only to an expulsion motion's target, which must carry un_veto_isolation_modifier (un_expulsion_candidate), added only in its own veto option (un_vote_cast_effects))

## `imputed_foreign_action`

The event picks another country itself, says that country acted, and applies consequences to it. If that country is a player, it is punished for something it never chose. Tie the premise to real state (e.g. an active covert operation), let that country choose first, or drop the consequence on it.

No unreviewed flags. ✅

### REVIEWED

- `decolonization_events.2` — events/decolonization_events.txt (REVIEWED 2026-09-25: pressuring_power is picked only among great powers carrying gp_anti_colonial_stance, a stance each chose (decolonization_events.14.a, or its yes vote on the UN declaration via un_vote_effects); calling on colonial powers to decolonize is what that stance is.)
- `decolonization_events.11` — events/decolonization_events.txt (REVIEWED 2026-09-25: condemning_power is picked from great powers carrying gp_anti_colonial_stance, which they chose)
- `decolonization_events.19` — events/decolonization_events.txt (REVIEWED 2026-09-25: the former colony chose to nationalize (decolonization_events.15))
- `international_relations_events.5` — events/international_relations_events.txt (REVIEWED 2026-09-25: the embargo is our own option; the rival is told what we chose (.102))
- `irredentism.3` — events/irredentism_events.txt (REVIEWED 2026-09-25: false positive: the subject of "have begun" is the voices on both sides; this is the unifier's own proposal)
- `te_judiciary_events.31` — events/te_judiciary_events.txt (REVIEWED 2026-10-25: the demanding power is an AI great power (is_ai), so no player is blamed for a demand it never made; the relations change follows our answer to it)
