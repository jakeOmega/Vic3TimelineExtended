# Nuclear Deterrence and Crisis Diplomacy — Design

> Status: proposed design; no gameplay implementation in this PR.
> Written 2026-09-24. Baseline: main at 4fbb27c67ce517dc9236233244548eecf6cb4f12.
> Companion work: [UN redesign, PR #411](https://github.com/jakeOmega/Vic3TimelineExtended/pull/411).
> The nuclear system must function with the UN, covert-warfare, and world-war systems disabled.

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
