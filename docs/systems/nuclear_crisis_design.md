# Nuclear Deterrence and Crisis Diplomacy — Design

> **Status: phases 1–3 implemented, phases 4–5 partly implemented (2026-09-25), all pending in-game verification.**
> Read [§0](#0-implementation-as-shipped) first: it is what the code does, the deviations from §1–§14, and the in-game checklist.
> Sections 1–14 remain the design (written 2026-09-24, baseline main at 4fbb27c67ce517dc9236233244548eecf6cb4f12); where they disagree with §0, §0 is what shipped.
> Companion work: [UN redesign, PR #411](https://github.com/jakeOmega/Vic3TimelineExtended/pull/411).
> The nuclear system must function with the UN, covert-warfare, and world-war systems disabled.
> **2026-09-25:** posture and crises no longer have their own journal entry. `je_nuclear_deterrence` was merged into `je_nuclear_program`, shown as "Nuclear Weapons", to spend one journal slot instead of two; §0.1 and §0.7 say how the separation §2 and §10 asked for is kept.

## 0. Implementation as shipped

Built on 2026-09-25 in one pass from §1–§14. None of it has run in a game yet; §0.9 is the in-game checklist. Every number below is a first tuning value, and §0.8 says where they live.

### 0.1 Where it lives

| Piece | File |
|---|---|
| Journal entry `je_nuclear_program` ("Nuclear Weapons"): the programme, posture and crises in one entry, active with a programme, while armed, or in a crisis (`nuclear_program_entry_applies`). Posture and crises had their own entry, `je_nuclear_deterrence`, until 2026-09-25 | `common/journal_entries/je_nuclear_program.txt` |
| Posture, upkeep, capabilities, domestic stance, incidents, launch dispatch | `common/scripted_effects/nuclear_deterrence_effects.txt` |
| Crisis lifecycle, settlements, credibility, native-outcome observation, guarantor acts | `common/scripted_effects/nuclear_crisis_effects.txt` |
| Doctrine gates, eligibility, AI judgement, dispute tests, panel eligibility | `common/scripted_triggers/nuclear_deterrence_triggers.txt` |
| Tuning constants, costs, capability targets, danger, pressure, incident odds, display values | `common/script_values/nuclear_deterrence_values.txt` |
| Private warning, public ultimatum, repudiating a pledge | `common/diplomatic_actions/nuclear_crisis_actions.txt` |
| Guarantee treaty article `nuclear_guarantee` | `common/treaty_articles/115_nuclear_guarantee.txt` |
| Crisis events (`nuclear_crisis.*`) | `events/nuclear_crisis_events.txt` |
| Incident chains (`nuclear_incident.*`) | `events/nuclear_incident_events.txt` |
| Back-down hook; monthly clean-up after the entry closes | `common/on_actions/nuclear_crisis_on_actions.txt` |
| Posture and crisis panels | `gui/journal_entry_widgets/nuclear_deterrence_widget.gui`, `common/scripted_guis/nuclear_deterrence_sguis.txt`, `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (op table: `journal_entry_systems.md` § Nuclear Deterrence Widget) |
| Static modifiers | `common/static_modifiers/nuclear_deterrence_modifiers.txt` |
| Console harness (`event te_debug_deterrence.1`–`.5`) | `events/te_debug_deterrence_events.txt` |
| Consistency tests (panel ops, fired events, loc keys, modifier families) | `test_nuclear_deterrence.py` |
| Existing strike actions, now doctrine-gated and recorded | `common/diplomatic_actions/nuke.txt` |

Every country variable carries the `nd_` prefix. Posture, upkeep and incidents are gated on `nuclear_weapons_enabled` and on holding at least one warhead (`nd_is_armed`), so a country with no arsenal gets nothing. The shared entry is also active for a programme that has not built a warhead yet; every `nd_*` pulse effect is a no-op for such a country.

### 0.2 Posture (phase 1)

There are three independent axes, stored separately: `nd_doctrine` 1–5, `nd_readiness` 1–3 with `nd_readiness_target`, and `nd_authority` 1–3. Two investment steppers sit alongside them, `nd_safeguards` 0–3 and `nd_hardening` 0–3. Humans set all of these in the posture panel. The AI sets them in `nd_ai_review_posture`, which runs every sixth month from the entry's monthly pulse and again whenever a crisis opens (hidden event `nuclear_crisis.99`, so the AI's own country is ROOT). The AI review is scored, with inertia and a `random_list` tie-break. It does not use JE scripted buttons, because one weighted roll over a dozen posture buttons would turn the AI's doctrine into a lottery.

| Doctrine | First use is permitted against an enemy we are at war with when… |
|---|---|
| 1 No first use | never; retaliation only. Leaving it counts as a **repudiation**: credibility −20, infamy +10, a 10-year decaying `nd_pledge_broken_mod`, and dovish groups disapprove |
| 2 Existential deterrence (default) | their side holds an annexation or subjugation goal against us (annex, reunify, protectorate, dominion, tributary, personal union, crown land, chartered company), or holds goals on our incorporated states while we are losing to them |
| 3 Flexible first use | any of the above, or we are losing to them, or they hold goals on any of our incorporated states |
| 4 Nuclear compellence | any of the above, or they defied a public ultimatum of ours (`nd_defied_us`), or they are the target of our crisis at stage 2 or higher |
| 5 Nuclear warfighting | always, in any war |

Retaliation against a country that struck us (`nuked_by_country`) is permitted under every doctrine. A bilateral non-use pledge, created by a reciprocal stand-down and held in the `nd_nonuse_pledges` list, blocks strikes on that partner until one side repudiates it with `nd_repudiate_pledge_action`. The humanitarian and limited-war law gates in `nuke.txt` still apply on top, so a strike needs both the law's permission and the doctrine's. An offensive doctrine (4 or 5) costs +5 infamy when adopted and −10 relations with every rival.

Doctrine changes need 24 months' tenure, and authority changes need 12. Readiness moves one step every two weeks toward its target, so going from routine to high alert takes a month. Strain only recovers month by month. Launch authority 2, conditional delegation, needs `radar`. Authority 3, launch on warning, needs `radar` and `ICBMs`. The tooltip for either one warns that an incident can then end in a launch with no player approval.

Capabilities run 0–100 and are updated monthly in `nd_monthly_update`:
- **Survivability** climbs toward a cap set by technology (`nd_survivability_cap`): 25 for bombers, +15 for `radar`, +20 for `ICBMs`, +25 for `advanced_submarine_technology` and +10 for `missile_defense_systems`, to a maximum of 95. Each hardening level closes 2 % of the remaining gap per month. With no hardening, survivability decays 1 % of the excess per month toward 30 % of the cap.
- **Reliability** moves a quarter of the way each month toward `55 + 12×safeguards + 5 (satellite_communications) − 0.4×strain`, minus 10 each for a punished sceptic, a concealed incident, and an enemy comms-disruption operation, clamped to 5–98.
- **Strain** rises 5 a month at high alert. At heightened readiness it rises 1.5, or falls 1 if it is above 40. At routine it falls 6.
- **Credibility** starts at 50 and drifts 2 % of the gap back toward 50 each month. Crises, pledges and guarantees move it.

Upkeep is a single JE-scoped modifier, `nd_upkeep_cost` (`country_expenses_add = 1`), multiplied by `nd_upkeep_weekly_cached`, which is refreshed monthly and after every panel change. The cost is counted in units of 1/100,000 of GDP per week:

| Component | Units |
|---|---|
| Custody | 0.2 per warhead, counting at most 50 |
| Heightened readiness | 4 × size factor |
| High alert | 12 × size factor |
| Safeguards | 2 per level |
| Hardening | 3 per level |

The size factor runs from 0.4 to 1.0 with arsenal size, and the total is capped at 40 units, about 2 % of GDP a year. Every armed country pays it, whatever the funding or rank of its programme, because the entry is gated on the arsenal.

Domestic stance (§7) is refreshed in one place, `nd_refresh_domestic_stance`. It gives each interest group at most one of four modifiers (`nd_posture_approval_plus_2`, `plus_1`, `minus_1`, `minus_2`), and only once the doctrine has been held for six months. Groups fall into four classes:
- **Warfighting**: a jingoist, fascist or ethno-nationalist leader, or the Armed Forces of a fascist state. It wants compellence or warfighting and high alert.
- **Professional officers**: the Armed Forces under any other leader. They want flexible deterrence at heightened readiness, and dislike no first use, warfighting, routine readiness against a plausible attacker, and a high alert with strain of 50 or more.
- **Doves**: a pacifist or humanitarian leader, or the Intelligentsia under a leader who is not a hawk. They reward no first use and punish compellence, warfighting, high alert and launch on warning.
- **Business**: the Industrialists. They dislike a high alert held three months or more, and any crisis at stage 2 or higher.

Groups are judged on a posture held for months, not on a toggle, so the approval can't be farmed. The modifiers come off in `nd_country_monthly_cleanup` (`on_monthly_pulse_country`) once the entry is inactive.

### 0.3 Crises (phase 2)

A crisis is one pair of countries with one dispute. The record lives on the **issuer**, the country that warned, which is the only one that updates it. The target keeps a mirror: `nd_crisis_opponent`, `nd_crisis_role` 1 or 2, and a shared `nd_crisis_id` drawn from the global counter `nd_crisis_counter`. A country can be in only one crisis at a time, but different pairs run at the same time. Each target's monthly pulse runs a watchdog, `nd_crisis_target_watchdog`, that drops the mirror if its issuer's record has gone.

A crisis opens with `nd_nuclear_warning_action` (private: relations −5) or `nd_nuclear_ultimatum_action` (public: infamy +5, relations −20, and audience costs later). Both need:
- an arsenal;
- neither side already in a crisis;
- no crisis between the same pair in the last 24 months (waived in war);
- no non-use pledge between them;
- a **dispute**, classified by `nd_crisis_classify_dispute` in the order shown:

| Code | Dispute | The target's concession if it yields |
|---|---|---|
| 2 | We are at war | −35 war support in that war |
| 1 | We are enemies in a diplomatic play | `resolve_play_for` our side |
| 3 | The target is in a play or war against a country we guarantee (`nuclear_guarantee`) | as for 1 or 2, for the beneficiary's side |
| 4 | The target is proliferating and is our rival, or we are antagonistic, belligerent or domineering toward it | `nd_crisis_programme_freeze`: 10 years of `country_nuclear_program_pause_bool` |
| 5 | The target is our rival, is armed, and is at heightened alert or higher | readiness to routine, locked for 24 months |

One crisis opens without an action. When a peacetime launch is recalled (§0.4), the country it was aimed at gets `nuclear_incident.5`, and its option c, "warn them privately", opens a private crisis with itself as issuer. The option needs an arsenal, both sides free and no non-use pledge; it skips the dispute test and the 24-month cooldown, because the recalled launch is the grievance. With no weightier dispute it classifies as code 5. Nothing opens a crisis on a country's behalf.

A crisis has three stages: 1, a private warning; 2, confrontation (a public ultimatum, a rejected warning or a counter-threat); and 3, acute (from stage 2: danger of 70 or more, or the issuer at high alert while the target is at heightened readiness or higher; or the issuer holding firm past its deadline, a play that became a war, or an intercepted launch). Each week the issuer's entry runs `nd_crisis_weekly_tick`:
- revalidate the parties and the dispute;
- convert a play that became a war;
- compute `nd_crisis_danger` (0–100) and the target's `nd_yield_pressure` (0–100, the explanation the AI and the player both see);
- fire the issuer's deadline event (10 weeks private, 8 public);
- send the target a pressure event every six weeks from stage 2 on, unless talks are open;
- expire the crisis after 52 weeks.

Every decision event is keyed to the crisis it was sent for. The sender writes `nd_crisis_event_token = nd_crisis_id` on the recipient, the event's `trigger` requires the token to still match, and every option re-checks it (`nd_crisis_event_valid`), because a popup that has already fired is never re-triggered. The crisis buttons in the panel and the event options call the same effects, `nd_crisis_act_*`.

`nd_crisis_close = { OUTCOME = N }` applies an outcome once and cleans up both sides. The outcomes are:

| Code | Outcome |
|---|---|
| 1 | The target yielded |
| 2 | The issuer backed down |
| 3 | Reciprocal stand-down |
| 4 | The target backed down natively: a play back-down, a programme stopped, an alert stood down |
| 5 | The issuer's side backed down natively |
| 6 | The war ended |
| 7 | Nuclear use |
| 8 | Expired |
| 9 | Invalid: a party vanished. The record is dropped without consequences |
| 10 | The dispute ended with no clear winner |

Native outcomes come from `on_diplo_play_back_down` (`nd_crisis_on_back_down`), which reports who backed down. The weekly revalidation catches everything else, including a play that ended without the hook firing, a war ending, and a disarmed issuer.

Credibility and audience costs:
- The issuer achieves its objective (1 or 4): +10, plus 5 more if the crisis was public; the target loses 5.
- The issuer backs down (2 or 5): −15 if public, −5 if private; the target gains 10 for facing it down.
- Reciprocal stand-down: +5 for both sides. Exception: an issuer that made a public, non-defensive demand loses 5 instead.
- A public ultimatum left to expire: −10.
- Extending a deadline: −3. Declining to honour a guarantee: −15.

Domestic rewards are one-off decaying IG modifiers plus native lobby appeasement. The appeasement goes through `every_political_lobby` of type `lobby_anti_country` or `lobby_pro_country` whose `target` is the opponent, with factor `appeasement_special_events_*`. An IG in an anti-opponent lobby is paid through the lobby only. Opening a crisis earns nothing by itself.

### 0.4 Incidents (phase 3)

Each armed country gets one roll per month, in `nd_monthly_update`, never one per crisis. The chance is `nd_incident_permille`: 1 ‰ at routine, 4 ‰ at heightened and 10 ‰ at high alert, × (1 + strain/100) × (0.5 + (100 − reliability)/100) × (1 + 0.5 × own crisis danger band), capped at 30 ‰. The roll has two stages (10 % × permille %) so that the inner `chance` never needs a fraction. The family is then drawn by weight from those the country qualifies for:

| Family | Weight | Eligible when | Inspiration |
|---|---|---|---|
| The Unconfirmed Warning (`.1`–`.5`) | 40, +20 in a stage-2 crisis | `radar`, readiness ≥ 2, and some country believed armed is our crisis opponent, enemy, rival, or antagonistic or belligerent toward us | Petrov 1983; Thule moonrise 1960; NORAD training tape 1979; 46-cent chip 1980; Fylingdales test tape 1965; solar storm 1967; Norwegian rocket 1995; Suez 1956; SAC relay failure 1961 |
| The Exercise They Mistook (`.10`) | 25 | crisis at stage 2 or higher, readiness ≥ 2 | Able Archer 1983 |
| Silence from the Capital (`.20`) | 30 | authority ≥ 2, and at war or in a crisis at stage 3 | Arkhipov and B-59 1962; the Okinawa order 1962 |
| The Cost of Permanent Alert (`.30`) | 35 | high alert held six months or more, or strain ≥ 60 | Goldsboro 1961; Palomares 1966; Thule 1968; Damascus 1980; Minot 2007 |
| A Routine Mishap (`.40`) | 20 | always | Duluth bear and Volk Field 1962; Kincheloe 1973; Mars Bluff 1958 |

In The Exercise They Mistook, the other side's alert is its own choice: an AI opponent goes to high alert at once, and a player opponent is asked (`.11`). Telling them in advance opens talks on our own record if we issued the crisis; if they did, the invitation goes to them (`.12`) and they decide whether to open talks.

Which branches can launch depends on launch authority:
- **Central authority:** the Unconfirmed Warning goes to the government (`.1`), and nothing launches unless it is explicitly ordered.
- **Launch on warning, or delegated authority in a war:** the outcome is rolled against `nd_hold_chance`, with no veto: reliability, +5 per safeguards level, −15 after punishing a sceptic, −10 under launch on warning, clamped to 20–97. A held launch leads to `.2`. An unheld one goes through `nd_launch_or_intercept`, then `.4` and the inquiry `.3`.

Every launch goes through the fenced dispatch helpers, `nd_dispatch_strategic_strike` and `nd_dispatch_tactical_strike`. They revalidate the stockpile and the war, consume the weapon once through the existing strike effects, and record the use once in `nd_record_nuclear_use`. That call handles:
- a breached pledge (credibility −25, infamy +15);
- a no-first-use breach;
- the snapped public estimate;
- closing the crisis with outcome 7;
- spurring the programmes of proliferating countries;
- notifying the victim's guarantors.

**Outside a war, the launch branch becomes an intercepted order** (§8.3's boundary). The launch is recalled at the last moment and the suspect sees the preparations (`.5`). The result is infamy +10 and relations −50. A crisis the two are already in turns acute; otherwise an armed victim that is free to may answer with a private warning from `.5` (a crisis with itself as issuer), which the AI does most of the time. Nothing opens a crisis on the victim's behalf. Nothing is struck, because a peacetime strike has no war context for the existing strike effects.

The Monopoly Window (`nuclear_incident.50`) is not an incident. It is a separate monthly 8 % check for a country with a compellence or warfighting doctrine that is at war with an enemy that is not armed and has no armed ally in that war, and whose doctrine and pledges permit a strike. It can fire at most once a year. A concealed incident can come out at 3 % a month (`.60`).

**Expected rates.** `scripts/analysis/nuclear_incident_rates.py` works out the model's expectations for one country over ten years of peace. It assumes no crisis, a plausible attacker, `satellite_communications` researched, and incidents that don't feed back into strain. "Launch orders not held" become intercepted orders in peacetime, and strikes only in a war.

| Readiness | Safeguards | Authority | Strain / reliability after 10 y | ‰ per month (end) | P(any incident, 10 y) | Warnings | Launch orders not held |
|---|---|---|---|---|---|---|---|
| Routine | 0 | Central | 0 / 60 | 0.9 | 10% | 0.00 | 0.00 |
| Routine | 3 | Central | 0 / 96 | 0.5 | 6% | 0.00 | 0.00 |
| Heightened | 0 | Central | 40 / 44 | 5.9 | 50% | 0.45 | 0.00 |
| Heightened | 0 | Launch on warning | 40 / 44 | 5.9 | 50% | 0.45 | 0.29 |
| Heightened | 3 | Central | 40 / 80 | 3.9 | 36% | 0.30 | 0.00 |
| Heightened | 3 | Launch on warning | 40 / 80 | 3.9 | 36% | 0.30 | 0.04 |
| High alert | 0 | Central | 100 / 20 | 26.0 | 95% | 1.23 | 0.00 |
| High alert | 0 | Launch on warning | 100 / 20 | 26.0 | 95% | 1.23 | 0.97 |
| High alert | 3 | Central | 100 / 56 | 18.8 | 88% | 0.89 | 0.00 |
| High alert | 3 | Launch on warning | 100 / 56 | 18.8 | 88% | 0.89 | 0.33 |

Routine readiness under central control almost never produces more than a mishap. A decade at high alert under launch on warning with no safeguards expects about one launch order that no one halts. Safeguards cut that to a third. These figures are for a single country; the world-level simulation §13 asks for (1, 2, 8 and 20 powers, clustered crises) has not been run.

### 0.5 Guarantees (phase 4, partial)

`nuclear_guarantee` is a directed treaty article. The source is the guarantor, who must be armed and pays the maintenance, and the target is the beneficiary. It is modelled on vanilla `guarantee_independence`: `country_treaty_leverage_generation_add` sits on the beneficiary's `target_modifier`. While it is in force:
- the beneficiary is spared the nuclear-shadow war-support drain (`zz_te_war_support_injections.txt`);
- AI strike decisions treat the beneficiary as covered by the guarantor's arsenal;
- the guarantor may open a dispute-3 crisis against the beneficiary's attacker;
- when the beneficiary is put under a nuclear warning or struck, the guarantor gets `nuclear_crisis.20`.

That event has three options:
- **Honour**: credibility +5; the target is backed, or a public crisis opens against the attacker.
- **Retaliate**: credibility +10; in a war, it strikes back.
- **Abandon**: credibility −15, a 5-year `nd_guarantee_abandoned`, beneficiary relations −30 and every other beneficiary −10.

The beneficiary hears the answer through `.21`. Programme freezes and disarmament stay in the existing articles, and they can sit in the same treaty. Inspections and a breach lifecycle beyond the article's own are not built.

### 0.6 Intelligence (phase 5, partial)

`nd_public_estimate` is re-observed every year for every armed country. The value is the true stockpile times a random factor of 0.6, 0.8, 1, 1.25 or 1.5. It snaps to the true count after a test or a strike, and is never rerolled on load or when a panel opens. The nuclear-powers leaderboard ranks and shows these estimates, marked "(estimated)", for every country including the viewer's own. The rival comparisons in the programme (`extra_script_values.txt`, `nuclear_program_buttons.txt`, `nuclear_weapon_events.txt`) read the estimate rather than the true stockpile. The posture panel shows the true count for our own arsenal. Espionage that reveals a rival's true count, exercise misreads beyond `.10`, and deeper covert integration are not built.

### 0.7 Deviations from §1–§14

- There is one crisis per country, stored in country variables rather than script containers (§11). Different pairs run concurrently, but a guarantor with two threatened clients can defend only one at a time.
- Crisis offers are fixed menus in events and panel buttons, not a free-form offer builder.
- Plays are settled with `resolve_play_for = <side>`. The engine documents it, but no vanilla script uses it (**verify in game**). Wars end natively after a war-support shock; there is no forced white peace.
- A peacetime launch branch never strikes (§8.3's own boundary).
- The Unconfirmed Warning is always a false alarm; the genuine-warning variant is not built. Nothing in its text says "false alarm" before the inquiry.
- Exercises exist as an incident (`.10`) and as a crisis act, not as a standing action.
- Posture and crises share the programme's journal entry (§2 and §10 kept them apart). The separations those sections care about are kept without a second entry: arsenal ownership is still separate from programme eligibility — the entry's `possible` admits anyone armed, while the programme half of its weekly pulse runs only under `nuclear_program_has_programme`, so a demoted power keeps its posture, upkeep and accidents and stops building — and production still does not share a bar with the crisis: the native bar is warhead progress, and the crisis has its own panel.
- The AI's first use in `nuke.txt` used to test `scope:country` (the actor) and so probably never passed. It now tests `scope:target_country` and goes through `nd_ai_nuclear_use_justified`, so an AI warfighting monopolist **can** use weapons in an ordinary war, as §9 requires. Expect more AI nuclear use than before.

### 0.8 Tuning constants

The tenures, deadlines, cooldowns and locks sit in the top block of `common/script_values/nuclear_deterrence_values.txt`. The costs, capability rates, incident odds, danger and pressure formulas follow in that file, each commented with the rule it implements.

### 0.9 In-game checklist

1. On a **new game**, "Nuclear Weapons" activates for a great power with the `nuclear_weapons` tech; the posture panel and the upkeep event appear the week its first warhead exists. A demoted power holding warheads keeps the entry and its upkeep, but its programme panel disappears and its funding (and the funding modifier) drops to zero. A non-nuclear crisis target gets the entry for the crisis and loses it when the crisis ends. The entry goes away on disarmament unless the country is in a crisis. In a save that had the old `je_nuclear_deterrence` entry, the posture modifiers (and upkeep) are back on the merged entry within a week (`nd_rebuild_posture_modifiers`), and in a save older than that, an armed country with the programme entry is put under a posture for the first time. The three container-4 panels (posture, crisis, delivery and defence) draw in that order.
2. The posture panel's buttons work, grey out with the right reason, and show the upkeep a change would cost.
3. The weekly figure on `nd_upkeep_cost` matches `nd_upkeep_weekly_cached` and follows a readiness change within the same month.
4. AI nuclear powers settle on varied postures, not all warfighting and not all routine.
5. A private warning over a diplomatic play reaches the target, and "yield" ends the play in our favour through `resolve_play_for`. **This is the one engine hook here with no vanilla precedent.**
6. `on_diplo_play_back_down` closes a play crisis with the right winner, and a play that turns into a war asks the issuer to honour a public ultimatum (`.7`).
7. A reciprocal stand-down locks both sides' readiness and records the pledge. A strike on a pledge partner is greyed out until the pledge is repudiated.
8. Doctrine gates: an existential-deterrence country cannot strike in an ordinary war, but a warfighting monopolist can, human or AI.
9. With the forced odds from `te_debug_deterrence.2`, an incident fires every month. Without them, it fires within a few years at high alert and rarely at routine.
10. Under launch on warning, the Unconfirmed Warning resolves with no option to cancel. Under central authority it launches only if ordered.
11. Silence from the Capital strikes only in a war; outside a war it produces an intercepted order. The country it was aimed at gets `nuclear_incident.5`, and a crisis opens only if that country picks "warn them privately" (`.5` option c, offered when it is armed, both sides are free and no pledge binds them). A crisis the two were already in turns acute instead.
12. `nuclear_guarantee` can be proposed, removes the war-support shadow from the beneficiary, and gives the guarantor the honour-or-abandon event when the beneficiary is threatened.
13. The leaderboard shows estimates that differ from the true counts, and they change only once a year.
14. `error.log` stays quiet while a crisis action's confirmation box is open, even though its tooltip re-walks `accept_effect` every frame.
15. The Exercise They Mistook (`.10`): an AI opponent's readiness target goes to High Alert at once. A player opponent that could raise its alert gets `.11` instead, and its readiness moves only if it picks "go to our highest alert"; `.10`'s text says it is deciding. An unarmed or locked opponent gets the variant with no alert claim.
16. In `.10`, "send them the schedule" from the crisis **target** sends the issuer `.12` (only while its talks flag is 0). Talks open, and the pressure events stop, only if the issuer accepts; from the issuer's side the option opens talks on its own record as before.

## 1. Intent and owner requirements

Make nuclear possession change peacetime bargaining, domestic politics, and conventional wars. The central decision is how much risk to accept for a specific objective, and what settlement is preferable to escalation.

The owner selected this ahead of a climate rework and requested:
- Meaningful doctrine, readiness, security guarantees, intelligence, and negotiated exits.
- Aggressive postures with tangible international AND domestic benefits: an anti-rival lobby or influential Armed Forces can reward a hard line.
- Event chains around dangerous postures, including a Petrov-inspired false alarm; some occur during crises, others during prolonged peacetime alert.
- A real possibility of things going wrong, including nuclear use. Risk must not be cosmetic or invariably rescued by a final veto.
- Alternate history as a first-class case. A fascist nuclear monopolist may regard nuclear weapons as usable in ordinary wars, rather than reserve them for national survival.

All mechanisms, numbers, and phase boundaries below are proposed defaults. The requirements above are accepted direction; this document is not evidence that any proposed engine hook exists.

### Desired experience

A threat can extract a concession, reassure allies, and satisfy domestic supporters while making the next crisis harder to control. Restraint can preserve security and political support when it achieves the stated objective. Greater caution has opportunity costs; greater aggression has consequences beyond a generic infamy bill.

Success is not measured by how often bombs fall. It is measured by varied, understandable decisions before use, with rare but consequential failures and deliberate first-use paths.

## 2. Existing implementation and seams

Read [mod_systems.md](mod_systems.md) and [journal_entry_systems.md](journal_entry_systems.md) before implementation.

| Existing component | Evidence / reuse |
|---|---|
| Programme, funding, first weapon, stockpile, programme and deterrence widgets | `common/journal_entries/je_nuclear_program.txt`, `common/scripted_buttons/nuclear_program_buttons.txt`, `gui/journal_entry_widgets/nuclear_program_widget.gui` |
| Eligibility and treaty gates | `common/scripted_triggers/nuke_triggers.txt`: great powers, majors with ICBMs, or programme-aid recipients; disarmament excludes eligibility |
| Strategic and tactical strike actions | `common/diplomatic_actions/nuke.txt`, `common/scripted_effects/nuclear_weapon_effects.txt`, `events/nuclear_weapon_events.txt` |
| AI severe-threat, personality, and retaliation checks | `enemy_has_existential_war_goal`, `is_losing_war_against`, `was_nuked_by_enemy`; current AI strike actions require severe threats |
| Play escalation | `common/scripted_effects/dp_escalation_effects.txt` and `common/script_values/dp_escalation_script_values.txt`; verified existing pattern adds escalation, not pauses or reverses it |
| Covert networks and programme sabotage | `common/scripted_effects/covert_warfare_effects.txt`, `common/diplomatic_actions/covert_operations.txt` |
| Nuclear aid, pause, disarmament articles | Existing treaty system; new agreements should share its lifecycle where feasible |
| UN response | #411 introduces nuclear-use authority-ledger hooks; call the eventual shared interface once per qualifying incident |
| Domestic political channels | Vanilla foreign pro-/anti-country lobbies and IG approval; see [politics reference](../vanilla/vanilla_politics_reference.md) |

Preserve current programme progression and stockpiles initially. Separate arsenal ownership from programme eligibility: a rank loss can deactivate production without deleting existing weapons or making their owner immune to upkeep and incidents.

The current AI severe-threat requirement is a baseline to replace, not a permanent universal restriction. Existing humanitarian/limited-war law gates must be reconciled explicitly with new doctrine permissions on both human and AI surfaces.

Custom domestic lobby definitions are not a dependency. Their previous implementation was reverted after a new-game crash; see [archived lobby design](../archive/political_lobbies_design.md).

## 3. Three independent policy choices

Do not put minimum deterrence, no first use, and launch on warning on one upgrade ladder. They answer different questions. Show recommended combinations as presets, but store the three choices separately.

### 3.1 Doctrine: when we say we will use nuclear weapons

| Doctrine | International benefit | Domestic constituency | Costs and limits |
|---|---|---|---|
| Assured retaliation / no first use | Reassures neighbors; strengthens reciprocal restraint and defensive guarantees | Restraint-oriented IG leaders, peace constituencies, pro-partner lobbies | Weak coercion in ordinary conventional disputes; breaking the pledge carries a distinct credibility cost |
| Existential deterrence | Credible defense against annexation, imposed subjugation, and regime-destroying threats | Security-oriented coalitions without a blanket offensive commitment | Does not promise nuclear rescue for peripheral wars |
| Flexible first use | May deter a superior conventional attacker or support limited coercion | Hawkish Armed Forces and anti-target lobbies | Alarm, arms racing, and escalation exposure; limited use never guarantees a limited response |
| Nuclear compellence | Stronger threats over explicit concessions, backed by willingness to initiate use | Militarist or expansionist coalitions | High reputational and alliance costs; opponents may resist, proliferate, or seek protection |
| Nuclear warfighting | Nuclear use is an available instrument in any otherwise legally eligible war | Highly militarized/expansionist regimes; particularly attractive during a monopoly | No severe-threat prerequisite, but still weighs retaliation, military utility, political costs, and scarce weapons |

No doctrine is exclusive to a tag, ideology, or historical bloc. Fascist/expansionist leadership strongly increases warfighting preference, especially without an opposing nuclear arsenal; it does not force every fascist government to launch. Democracies can choose first use, and dictatorships can rationally exercise restraint.

“No first use” is a political commitment, not a magical protection. Deliberate breach requires an explicit repudiation/violation choice, subject to binding laws and treaties. AI uses the same gate and pays the same costs. An unauthorized incident can violate a pledge and causes consequences even if the government did not order it.

### 3.2 Readiness: how quickly forces can respond

| Readiness | Benefit | Recurring cost / risk |
|---|---|---|
| Routine | Low expense and crew strain | Slower crisis response; weaker immediate threat |
| Heightened | Stronger immediate credibility and prepared response | Additional upkeep; manageable fatigue and incident exposure |
| High alert | Best short-term response and perceived survivability | High upkeep, fatigue accumulation, heightened misinterpretation and accident exposure |

Readiness transitions take time. Raising alert is observable only to the extent justified by intelligence and signaling; public alerts are clearer signals and stronger domestic commitments. Standing down starts recovery rather than instantly clearing strain.

Use GDP-scaled costs with arsenal-size/capability components and affordability caps to be calibrated. All annual budget shares must be converted to the engine's weekly expense units consistently. Show the actual budget cost before confirmation.

Readiness changes do not silently create a universal combat bonus. Their benefit acts through crisis threat credibility, response preparedness, and defined survivability abstractions.

### 3.3 Launch authority: who may act under uncertainty

| Authority | Benefit | Failure mode |
|---|---|---|
| Central authorization | Strongest political control; lowest unauthorized-use risk | Vulnerability to disrupted command and delayed decisions |
| Conditional delegation | Retaliation remains more credible when communications are disrupted | Local commanders may misread whether authorization conditions are met |
| Launch on warning | Strong response credibility for vulnerable forces with suitable warning technology | False warning can become an authorized mistaken launch under standing orders |

Launch on warning requires appropriate warning/delivery capabilities; it is not available to an early bomber-only arsenal. Conditional delegation can have an earlier, technologically appropriate variant.

Choosing delegated or warning-based authority explicitly authorizes the game's possibility of a subsequent launch without another player confirmation. Display that consequence, affected circumstances, and current risk before adoption. Central control can still produce accidents, breakdowns, and deliberate mistaken decisions, but does not spontaneously delegate launch authority.

## 4. Capabilities, upkeep, and intelligence

Track a small number of abstract capabilities:
- Arsenal size, reusing the existing stockpile.
- Delivery capability, derived from relevant researched technology and paid capacity.
- Survivability, developed through sustained investment with diminishing returns.
- Command reliability, improved by safeguards/training and eroded by fatigue, institutional disruption, or relevant sabotage.

A small survivable arsenal can deter better than a larger vulnerable one. Additional warheads have diminishing deterrence returns but real upkeep. Readiness and safeguards compete with production for resources; minimum deterrence is a viable spending strategy, not a required doctrine.

Avoid detailed targeting or a separate nuclear combat simulation. Use capability bands and verified existing strike outcomes. Distinguish what the simulation knows from what each decision-maker believes.

The owner sees its exact stocks and internal condition. Opponents normally see estimated bands, confidence, and last observation date. Integrate existing covert networks when enabled; use public tests, visible deployments, known strikes, and coarse diplomatic estimates when disabled. AI must use the same information model rather than read hidden true stockpiles.

Audit existing public nuclear-power rankings/widgets so they do not disclose exact arsenals while this feature claims uncertainty. Debug views may reveal truth and must be clearly marked. Incomplete estimates cannot reveal whether an event warning is genuine through a tooltip or option condition.

Bluffing can influence beliefs temporarily. Repeated unsupported threats reduce credibility. Uncertainty must not mean arbitrary random facts: observations update persistent estimates; opening a panel or reloading a save never rerolls intelligence.

## 5. Crises belong to disputes

A crisis references principal opponents, participants/guarantors, a cause, stated objectives, and the originating play or war when resolvable. Nuclear monopoly produces an asymmetric coercion crisis; two nuclear states produce a reciprocal escalation problem.

Entry conditions include:
- A nuclear warning during a diplomatic play.
- An existential or major conventional defeat involving a nuclear state.
- An attack on a country covered by a relevant nuclear guarantee.
- An exposed programme or sabotage incident followed by an explicit ultimatum.
- An alert incident that develops into a diplomatic confrontation.

Possession alone does not open a crisis for every small dispute. Warfighting doctrine can enable deliberate use in ordinary wars without waiting for a crisis severity threshold.

### 5.1 State and timing

Proposed lifecycle: **warning → confrontation → acute crisis → settlement / stand-down / conventional war / nuclear use → aftermath**.

These are states, not an automatic ladder. Conventional war can remain non-nuclear or host continuing negotiation. Nuclear use enters aftermath and reassessment; it does not cause every power to launch automatically.

Each side has its own:
- Stakes and declared red line.
- Resolve and domestic pressure.
- Threat credibility and perceived opposing retaliation.
- Readiness and available settlement offers.

A shared escalation assessment describes danger; reaching a number does not automatically fire weapons. Resolve is willingness to bear costs, not the probability of an accident.

Use weekly updates for active crises and monthly upkeep elsewhere. Event narration can describe minutes of deliberation without pretending the engine provides a real-time command simulation. No unverified promise to freeze a diplomatic play while a popup is open.

### 5.2 Player actions

| Action | Benefit | Exposure |
|---|---|---|
| Private warning naming a red line | Signals resolve while retaining room to compromise | Less domestic reward; may be dismissed |
| Public ultimatum | Stronger bargaining signal and anti-target political support | Creates an audience cost if abandoned without achieving the objective |
| Heighten readiness | Makes the warning credible and improves response preparedness | Expense, fatigue, reciprocal alert |
| Conduct a demonstration/exercise | Clarifies capability and may reassure a protected state | Misinterpretation incident; consumes actual resources |
| Open a hotline / request verification | Reduces misperception | Staff/resources and possible political criticism; does not reduce true enemy resolve |
| Offer reciprocal stand-down | Exchanges costly readiness for reduced risk | Opponent can refuse; terms must apply to both sides on acceptance |
| Seek mediation | Access to additional settlement options | Diplomatic concessions; no guarantee a mediator can impose terms |
| Hold position | Preserves the demand without a new signal | Ongoing costs and risk; not a free pause button |

Every ultimatum records what counts as fulfillment, the intended target, expiry, and any promised response. The player sees these before committing. Do not infer that a new war goal against a different state fulfills an old threat.

## 6. Settlements and guarantees

A settlement must transfer something the game can actually enforce. Initial options: reciprocal readiness reduction, a bounded non-use pledge, an existing programme-pause or disarmament agreement, and existing diplomatic concessions where verified.

For demand withdrawal, white peace, or forced play termination, first prove the specific engine hook and both-side semantics. If unsupported, keep the native play/peace interaction and recognize its observed outcome; do not show a “settled” badge while the war continues. A reciprocal readiness agreement can reduce nuclear danger without resolving the underlying territorial dispute; label that distinction.

Both parties explicitly accept. Revalidate all terms on acceptance, apply once, and log success/failure. A delayed event cannot settle an ended war or spend an arsenal twice.

Credibility follows objectives and commitments:
- Achieving the defensive objective through compromise can be a success.
- Honoring reciprocal restraint improves reliability with relevant observers.
- Abandoning an unfulfilled public ultimatum can disappoint its supporters.
- Aggression has a separate reputation from reliability: successful bullying can demonstrate resolve while making others form a coalition.
- A defensive pledge does not obligate support for unrelated offensive demands.

### Extended deterrence

Guarantees name beneficiary, guarantor, covered threats, duration, and termination terms. Begin with defense against annexation/subjugation, with broader coverage later. Threats are checked against the actual beneficiary and actual attacker.

A guarantee increases perceived response risk; it is not invulnerability or an automatic declaration of war. The guarantor must choose whether and how to honor it. A beneficiary may become more assertive, while an unsupported offensive adventure gets no automatic protection.

Abandoning a covered commitment affects other beneficiaries' confidence. Nuclear disarmament for a guarantee is an exchange with ongoing verification and breach consequences. Multiple guarantors must not grant additive unlimited deterrence.

## 7. Domestic incentives that matter

Use current political actors and their actual targets. An anti-Soviet lobby is one instance of an anti-country lobby; localization names whichever rival exists in this campaign.

| Constituency / condition | May reward | May punish |
|---|---|---|
| Strong, hawkish Armed Forces | Funded readiness, delivery investment, credible commitments | Hollow threats, underfunding, an embarrassing retreat |
| Anti-target foreign lobby | A credible warning or achieved concession against its target | Unreciprocated concession to that same target |
| Pro-target foreign lobby | Hotline, détente, verified settlement | Threatening its partner |
| Restraint-oriented IG leaders | Safeguards, reciprocal restraint, avoided war | Pledge-breaking or unnecessary first use |
| Economic interests exposed to mobilization/trade disruption | Timely settlement, predictable policy | Sustained alerts and economic losses |

Armed Forces preferences depend on ideology, leadership, resources, and outcomes. They need not always prefer maximum danger. A successful defensive compromise can satisfy professional officers, while a warfighting faction demands more.

Concrete initial reward channels are bounded, temporary IG approval and existing lobby appeasement where engine support is verified. These already affect domestic politics; do not add an unexplained universal legitimacy bonus. A real domestic incentive can make a player tolerate higher costs and risks.

Avoid double-paying the same IG through direct approval and lobby membership for one action. Keep per-actor reward records and caps. Rewards accrue for maintaining a credible funded commitment or achieving an objective, not every time posture is toggled. Cooldowns, minimum policy tenure, decaying audience pressure, and target-specific memory prevent farming.

Native lobby membership/appeasement hooks require a runtime probe. Fallback: clearly labeled temporary approval effects on verified relevant IGs. Do not pretend that this fallback changed a lobby's actual appeasement, and do not revive the crashing custom domestic-lobby framework.

## 8. Incidents: real risk, legible causes

Separate incident frequency from catastrophic outcome probability. High alert produces more incidents; poor command reliability, ambiguous information, acute crises, and delegated authority make an incident harder to contain.

Prototype model, not final balance:
- One incident budget per country per month, shared across all crises; a weekly crisis update must not multiply the monthly rate by four.
- Illustrative incident probabilities: routine 0.1%, heightened 0.4%, high alert 1.0% per month before risk modifiers.
- Strain, capability maturity, institutional disruption, and crisis exposure adjust risk within explicit caps.
- Most incidents end in expense, temporary readiness loss, injury, diplomatic alarm, or scandal.
- Unauthorized/mistaken use is a conditional terminal branch, requiring eligible weapons, delivery, targets, and prior authority choices or a documented loss-of-control chain.

At 1% monthly incident probability, twelve months imply about 11.4% chance of at least one incident. This is NOT an 11.4% chance of nuclear use. Show incident and use risks separately; simulate global campaign incidence before selecting final numbers. Do not assign a flat independent launch roll to every country every month.

Safeguards reduce risk but cost money and can reduce rapid-response benefits. Peacetime high alert carries risk without a crisis. A monopolist can suffer mishaps and command failures even when it has no plausible nuclear attacker.

### 8.1 Event chain: The Unconfirmed Warning

Historical inspiration: Stanislav Petrov's handling of a Soviet warning-system false alarm in September 1983. The adaptation models uncertainty and institutional judgment, not an assertion that Petrov personally controlled a launch button. See §14.

Eligibility: appropriate early-warning capability, operational arsenal, heightened/high alert, and a plausibly capable opposing actor according to available intelligence. Crisis tension increases weight. An early bomber-era force gets different incidents.

1. **Conflicting indications.** Reports suggest an attack; another channel has not corroborated it. Present evidence, confidence, and current authorization policy without labeling the event a false alarm.
2. **The officer's objection.** A duty officer or command staff questions the interpretation. Options: demand independent verification, maintain alert while using the hotline, or execute existing warning-response orders. Verification risks a temporary preparedness disadvantage if the threat is genuine; it must not invent a real enemy launch solely to punish caution.
3. **Resolution.** A false alarm can be contained, trigger a costly scramble, or lead to a mistaken launch through risky orders. A genuine attack variant must be backed by an actual incoming incident/action if the engine supports linking it. Otherwise ship this as an ambiguous false-alarm family without falsely claiming a simulated incoming attack.
4. **Inquiry.** Reward professional skepticism, conceal the failure, or punish disobedience. Each changes reliability, political support, or future reporting behavior. Concealment risks later exposure; dismissal of competent staff can worsen future incidents.

A launch-on-warning or delegated choice can resolve into a launch without another last-second veto. Under central authorization, the player must explicitly order the mistaken launch. AI evaluates the same evidence and its standing doctrine.

### 8.2 Event chain: The Exercise They Mistook

Eligibility: public exercise/high alert during an active confrontation, with a named opponent.

The opponent interprets the exercise as preparation for attack and responds. Choices include advance notification, observers, scaling back, or continuing for domestic/strategic benefit. A hotline can uncover the mismatch; deliberately exploiting the confusion may win concessions but raises incident exposure. Ending the exercise does not immediately erase the other side's alarm.

### 8.3 Event chain: The Isolated Commander

Eligibility: conditional delegation, an eligible deployed force abstraction, and disrupted communications during war/crisis.

Local command believes a red line has been crossed. Prior safeguards determine whether orders are held, verification attempted, or weapons used. A launch is possible after the player knowingly delegated authority; attribution and responsibility remain with the owning country. The aftermath includes opponent reassessment, command reform, and domestic blame.

Until peacetime launch/war-transition hooks are proven, restrict launch-capable outcomes of this chain to an existing war. Outside war, use an attempted-launch/intercepted-order outcome with material costs and confrontation. This is an implementation boundary, not a claim that unauthorized use is impossible.

### 8.4 Event chain: The Cost of Permanent Alert

Eligibility: prolonged high alert, including peacetime and monopoly worlds.

Fatigued crews, maintenance failures, budget demands, or a weapons-handling accident force choices between temporary stand-down, costly replacement/training, and accepting degraded reliability. Consequences can include stockpile loss, local damage where supported, and scandal; never fabricate a foreign attacker merely because no rival exists.

### 8.5 Event chain: The Monopoly Window

Eligibility: warfighting/compellence doctrine, a nuclear monopoly or credible local monopoly without effective opposing guarantees, and an ordinary war.

Military leaders argue for nuclear use to end the war or demonstrate supremacy. Alternatives: maintain conventional operations, issue a costly warning, seek a settlement, or authorize first use. A fascist expansionist government with strong military support is especially receptive. The non-nuclear opponent can resist, concede, or seek external protection.

Actual use pays all existing weapon, damage, diplomatic, and later UN consequences. It can stimulate foreign proliferation and balancing; it is not free victory.

## 9. AI and alternate-history rules

Evaluate each decision using:
1. Binding law/treaty eligibility and available capabilities.
2. Doctrine and the specific objective.
3. Perceived retaliation, including relevant guarantors.
4. Conventional position and expected military utility.
5. Domestic support, leadership, and ideology.
6. Diplomatic reputation, costs, and settlement alternatives.
7. Uncertainty and current incident/command condition.

Use a shared decision explanation for AI and player tooltips. Personality adjusts decisions; it does not bypass every constraint.

A warfighting monopolist is allowed to choose use while winning an ordinary war. Remove the current mandatory existential/losing-core-territory gate for this branch. Keep stricter gates for other doctrines. Conversely, nuclear possession by an opponent is not an absolute no-use rule.

Monopoly is a strategic assessment, not a permanent flag awarded to the first builder. Recompute it when arsenals, intelligence, guarantees, or reach change. An unseen second arsenal can make perceived monopoly wrong; do not give the AI privileged access to that secret.

No hardcoded USA/USSR, NATO/Warsaw Pact, 1945/1983 trigger, mandatory bipolar world, or inevitable liberal international order. Reputation and nuclear taboo emerge from use, pledges, opposition, and institutions, with configurable decay. No first-use immunity merely because the UN has not formed.

## 10. UI and player agency

Extend the existing nuclear programme interface with:
- Doctrine, readiness, authority, change restrictions, and current recurring costs.
- Domestic supporters/opponents, named lobby targets, and why they care.
- Capability bands, reliability, fatigue, and investment choices.
- Incident exposure, catastrophic-use conditions, and available safeguards.
- Active crises, red lines, offers, deadlines, relevant guarantees, and action history.
- Observed foreign capability with confidence and observation date.

Keep production funding separate. The next warhead and the current crisis should not compete for the same progress bar.

Before a risky authority change, state plainly that an incident may cause use without further approval. Every incident explains the relevant choices and conditions in the aftermath. Avoid fake precision in hidden-risk estimates.

Human and AI actions share effect/eligibility helpers. Retain JE scripted buttons as the AI path where required by the current architecture; GUI-only controls must not silently exclude the AI.

## 11. Implementation architecture and capability gates

Suggested new files: `nuclear_crisis_*` scripted values, triggers, effects, events, and widget; names are proposals, not registered engine APIs.

Country state: doctrine, readiness/current transition, authority, reliability, strain, investment, cost cache, cooldowns, and incident ownership. Persistent crises/guarantees use script containers and country lists where validated, following covert-network patterns.

One canonical crisis record owns each dispute. Participants reference it; they do not independently roll duplicate incidents or apply settlement effects. Deterministically choose one update owner. Keep pair/dispute identity, offer revision, consumed-outcome flag, and event generation/version. Revalidate scopes and generation on every delayed response.

Phase 0 must prove:
| Question | Existing evidence | Required fallback / boundary |
|---|---|---|
| Can a play/war be persistently identified, including its target and goals? | Current scripts iterate plays and test roles; direct target hopping has restrictions | Verify container references/lifetime; otherwise use a country-pair crisis with one selected dispute and explicit revalidation |
| Can script pause/reverse a play or remove a demand? | Existing code only adds escalation | Do not depend on it; native settlement observation and nuclear-only stand-down |
| Can guarantee/treaty terms and native lobby appeasement be changed safely? | Existing articles and vanilla lobby channels | Probe exact scopes; use bounded agreements/IG effects only where honestly labeled |
| Can a peacetime mistaken launch create the proper war and response context? | Existing launch actions require wartime targets | Gate launch-capable accident branches to war until proven; retain costly peacetime near misses |
| Can incoming attacks support a genuine-warning event variant? | Not established by this design | False-alarm family only, without invented incoming attacks |
| Can doctrine govern every launch entry point? | Strategic/tactical actions and effect helpers already exist | Enumerate events, UI, AI, retaliation, and incident calls; route through one authorization/dispatch layer |
| Can covert intelligence hide exact stockpiles consistently? | Existing networks plus public ranking widget | Audit all ordinary UI/loc surfaces; use an explicit public-information first phase if hiding is not yet complete |

Do not promise nuclear alerts will change vanilla war-declaration or backdown AI without a proven modifier/hook. Scripted crisis offer AI can respond to deterrence independently; extending native AI behavior is a separate verified integration.

All actual launches reuse one dispatch path: revalidate ownership/stock, consume once, apply existing strike outcome, record attacker/victim, notify response systems once, and log the incident. Failed dispatch cannot consume a second weapon or award political success. Existing effect ordering must be audited before factoring it.

Bound automatic retaliation by available stock, valid enemies, incident IDs, and response cooldowns; no recursive effect loop that instantly empties world arsenals. A retaliatory decision can still escalate severely.

Handle annexation, civil war, rank changes, regime changes, capitulation, and removed targets explicitly. No automatic duplication of arsenals into both civil-war successors. A disappearing guarantor ends or invalidates the guarantee; a regime change reevaluates policy after initialization rather than resetting stockpile.

Old saves retain arsenals and gain conservative defaults: existential deterrence, routine readiness, central authority, no unresolved incidents. Start upkeep after initialization with a visible notice. Disarmament removes armed readiness and pending launch eligibility directly, even if the programme JE deactivates before its pulse.

Keep persistent armed-country upkeep outside the production JE. If the nuclear rule is disabled, stop new crises/incidents and clear this system's costs and temporary effects safely; do not destroy saved stockpiles or duplicate existing rule cleanup.

Cache display values on pulses. Iterate active records, not all possible country pairs. Safely clean orphaned containers, offers, and pending incident tokens. UN events are conditional hooks, not a requirement; world-war mechanics are optional; no covert network is required to open a crisis.

## 12. Delivery phases

| Phase | Deliverable | Exit condition |
|---|---|---|
| 0 — engine probes | Validate §11 capabilities in console harnesses; record supported effects and limitations | Working dispute identity, one valid offer lifecycle, launch-call inventory, and political-hook evidence |
| 1 — posture and incentives | Three policy axes, upkeep, domestic rewards/costs, AI choices, doctrine-aware launch eligibility, migration | Same rules for human/AI; monopolist ordinary-war use possible; posture toggles cannot farm rewards |
| 2 — bilateral crisis | One existing play/war, named objective, warning, reciprocal stand-down, native outcome observation, UI | A complete playable crisis can de-escalate, continue conventionally, or reach use without unsupported settlement promises |
| 3 — dangerous posture chains | Unconfirmed Warning, Cost of Permanent Alert, and an in-war delegated-command failure; shared launch dispatch | Costly near misses and genuine adverse branches work, with clear prior authorization and no duplicated launch |
| 4 — guarantees and arms control | Defined defensive coverage, programme freeze/security exchange, inspections and breach lifecycle | Small-state gameplay; guarantor refusal and agreement expiry have coherent consequences |
| 5 — intelligence and wider incidents | Consistent uncertain arsenals, exercise misinterpretation, monopoly event, covert and UN integration | No exact-information leaks or mandatory UN/covert dependencies; global campaign risk calibrated |

Phases are implementation slices, not reasons to postpone the owner's risk requirement indefinitely: do not call the posture rework complete before phase 3. Phase 1 must already advertise the limited implemented behavior honestly; dormant incident-risk UI must not claim actual hazards.

Doctrine/capability decisions precede adding dozens of events. First prototype one full crisis and one full failure chain, then expand.

## 13. Validation and balance acceptance

Implementation requires in-game verification; this documentation PR does not claim it.

Required scenario matrix:
- Two cautious nuclear peers settle a crisis without loss of credibility for fulfilled objectives.
- A militarist/fascist sole nuclear power chooses first use in an ordinary war; another declines because costs outweigh utility.
- A democratic monopolist can adopt first use; a fascist power facing assured retaliation can exercise restraint.
- A conventionally weak state with a small survivable arsenal deters a stronger aggressor.
- A non-nuclear beneficiary is protected against a covered threat but receives no automatic offensive guarantee.
- A strong anti-target lobby rewards credible pressure only against its named target; a pro-target lobby objects.
- Strong Armed Forces produce meaningful posture incentives without universal maximum-alert preference.
- A verified compromise satisfies some hawks; repeated empty ultimatums lose credibility.
- High-alert peacetime produces maintenance/false-alarm chains; routine countries are not constantly interrupted.
- Central authorization contains a false alarm; warning/delegated authority can produce actual use under eligible conditions.
- A failed incident can occur without a crisis; a nuclear monopolist never receives a nonsensical known-rival missile alert.
- No UN, no covert system, no world-war system, no native lobby, and technologically early nuclear games remain playable.
- Annexation, civil war, disarmament, save/reload, simultaneous crises, duplicate event responses, and destroyed targets leave no orphan costs or duplicate arsenals.
- Human and AI legality match; paused/funding-zero programmes cannot evade armed-country upkeep.

Simulate peace decades and clustered crises for worlds with 1, 2, 8, and 20 nuclear powers. Report incident frequency, near-miss/use branches, first-use reasons, time at each posture, political rewards, costs, and successful settlements. Calibrate the world's aggregate risk, not just a single country's monthly chance.

Acceptance goals: no posture dominates across threat and domestic conditions; routine central control has very low catastrophic risk; prolonged risky postures have measurable risk and useful benefits; informed investments reduce risk; no launch from an empty arsenal; no guaranteed compliance merely because an ultimatum is nuclear.

Run existing CI/audits for implementation, add meaningful lifecycle/dispatch and probability checks, and use dedicated in-game harnesses for scope behavior. Record observed outcomes, not just parse-clean status.

## 14. Historical inspiration and remaining design choices

Historical references inform event structure, not tag/date requirements:
- Geoffrey Forden, [False Alarms on the Nuclear Front, PBS NOVA](https://www.pbs.org/wgbh/nova/missileers/falsealarms.html): the 1983 warning incident and other warning failures suggest independent corroboration, professional judgment, and institutional follow-up. The game branches are fictional; historical near misses are not proof a launch was inevitable.
- [US Office of the Historian, document 91, FRUS 1981–1988 volume I](https://history.state.gov/historicaldocuments/frus1981-88v01/d91): contemporary discussion illustrates the changing credibility of nuclear threats and competing response doctrines. Game mechanics are abstractions, not a reproduction of a national war plan.

Implementation decisions to settle through phase 0/prototyping:
- Exact supported settlement and peacetime-launch hooks.
- Final numerical upkeep, approval, fatigue, credibility, and risk values.
- Whether capability investment uses a dedicated programme allocation or existing buildings/modifiers.
- The first viable uncertain-intelligence model and public ranking migration.
- Scope of guarantee chains and maximum concurrent crises.

Until resolved, the conservative fallbacks in §11 govern. Do not silently replace actual accident risk with harmless flavor, hardcode historical blocs, or restore the universal severe-threat gate that excludes the requested monopoly scenario.
