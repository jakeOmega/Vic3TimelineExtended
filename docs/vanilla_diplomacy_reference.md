# Vanilla Diplomacy Reference (Victoria 3)

A primer on how the **base game's** diplomacy systems work, written for AI agents that need context before touching mod content that hooks the diplomatic layer (formables and unification plays, infamy/relations modifiers, power-bloc principles, treaty articles, subject mechanics). Mod-specific systems (Pan-X unification plays, formable candidacy, covert warfare, etc.) live in `docs/mod_systems.md` and `docs/journal_entry_systems.md`. Diplomatic *plays* themselves are covered in detail in `docs/vanilla_war_reference.md` § 1; this doc focuses on everything that surrounds and feeds into a play.

> **Last verified against vanilla:** 1.13 ("The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. **Revisit this file on every vanilla bump per `docs/vanilla_patch_runbook.md`.** Wiki sources for this doc are tagged at versions ranging from 1.9 to 1.13; verify any specific name or number via the server before relying on it.
>
> **Verify before relying on names.** Modifier names, war goal IDs, treaty article IDs, principle IDs, subject type IDs, and trigger names cited below should be confirmed via the mod state server (`/modifier-search?q=`, `/engine-docs/modifiers`, `/raw/SubjectType/<id>`, `/raw/PowerBlocPrinciple/<id>`, `/raw/DiplomaticPlay/<id>`) before referencing them in code. Vanilla renames things across patches.
>
> **This doc captures concepts, structure, and gameplay shape — not numerical truth.** It is *not* a source of accurate values. Specific costs, rates, tier thresholds, multiplier values, and modifier defaults change between vanilla patches and even between hotfixes; treat any number you see here as **illustrative only**. When a balance number actually matters, pull it from the source: `common/defines/`, `common/static_modifiers/<base>_modifier.txt` and similar `base_values` blocks, `common/country_ranks/`, the relevant `common/diplomatic_actions/` / `common/treaty_articles/` / `common/power_bloc_principles/` file, or the live tooltip in-game. The structural claims (ranks gate this, infamy works like this, locality determines that) are what this doc is designed to be reliable about — not the numbers attached to them.

## 1. Country rank

Rank determines almost every diplomatic gate in the game: who can subjugate whom, what infamy a war goal generates, whether a power bloc can be created or led, how much {{influence}} is generated, how much locality each owned state contributes to a region (see § 6), how many maneuvers are available in plays. **Read § 1 of this doc before § anything else** — most of the rest of the diplomatic surface is rank-conditional.

### 1.1 The seven ranks

In descending order:

| Rank | Recognized? | Typical role |
|------|-------------|--------------|
| Great power | yes | Global presence; can lead a power bloc; can subjugate weaker states |
| Major power | yes | Regional powerhouse; eligible to lead a bloc |
| Unrecognized major power | no | Same as major power for prestige, but locked out of subjugation, alliances at full strength, and (sometimes) recognition gates |
| Minor power | yes | Regional player |
| Unrecognized regional power | no | Same prestige threshold as minor power but with recognition penalties |
| Insignificant power | yes | Local-only relevance |
| Unrecognized power | no | Lowest rank for a playable country |

A non-playable eighth rank, **decentralized nation**, exists for tribal/uncolonized states and is irrelevant for diplomacy beyond being a colonization target.

Rank is **dynamic and computed against global prestige**, not fixed. For each tier the threshold is the higher of (a) some multiplier of the *global average* prestige, or (b) some fraction of the *current highest* prestige (great > major > minor uses progressively smaller multipliers and fractions). Pulling current values requires reading `common/country_ranks/00_country_ranks.txt`.

Because the cutoff is relative, the prestige number that bought a great-power slot in 1840 won't necessarily hold it in 1900 — global GDP and population growth lift the curve. Promotion is instantaneous; demotion fires only after a grace period if prestige sits below the rank's threshold.

### 1.2 Recognition

Recognition is a separate flag. Unrecognized countries are capped at unrecognized-major-power as their highest rank — even with great-power-tier prestige they cannot become a great power until recognized. Recognition is gained by completing the `je_earn_recognition` journal entry (research Colonization, then accumulate progress through GDP/SoL/literacy/voting metrics, lose progress for slavery/serfdom/isolationism/illiteracy). Enforcing wargoals against major or great powers also moves the bar.

The Ottomans are the only country that can *lose* recognition (failing the Sick Man journal entry). Otherwise recognition is sticky — but a recognized country that ceases to exist and is later released or formed comes back unrecognized.

### 1.3 What rank gates

Verify the current numbers via `/raw/CountryRank/<id>`, but the *kinds* of effects each rank shifts:

- **Influence capacity** — the pool diplomatic pacts and ongoing actions are paid out of. Larger at higher ranks.
- **Maneuvers** in diplomatic plays — see `vanilla_war_reference.md` § 1.2.
- **Locality footprint** in strategic regions (see § 6). Locality is computed from owned states, population, and GDP share — all of which correlate with rank but are not *directly* rank-set. Other countries can leech involvement off your locality via treaties.
- **Interest-rate modifier** on loans — recognized ranks get progressively cheaper credit; unrecognized ranks pay penalties.
- **Migration attraction**, **leverage resistance**, **diplomatic-pact cost multiplier**, **support-independence weekly liberty desire impact** — all rank-keyed.
- **Infamy multipliers** (see § 5) — both the multiplier paid by an attacker for infamy generation, and the multiplier baked into infamy when the country is the *target*.
- **Subject pairing** — most subject types require the overlord to be a higher rank than the subject; no subject can be a great power or major power.
- **Subjugation** (power bloc Sovereign Empire action) requires the leader to have ≥5× the target's prestige and the target below major power.

The mechanically meaningful split is therefore: *recognized vs unrecognized* (caps the ceiling), *great vs not* (gates power-bloc leadership and subjugation), and *insignificant or below vs above* (gates whether you can be annexed in one step).

## 2. Prestige

Prestige is the input to rank. It comes from a small fixed-source set summed each tick:

- **Country tier** (city-state through hegemony — a flat per-tier value, larger at higher tiers). Tier upgrades on unification or a tier-promoting decision permanently bump prestige.
- **Total GDP** — own country contributes more per £1M than subjects do, but subject GDP still counts.
- **Power projection** from army and navy — navy contributes more per unit than army; subject contributions are heavily discounted versus own-army contributions.
- **Goods production leadership** — being top-3 globally for a good gives prestige scaled by that good's `prestige_factor` (defined in `common/goods/`). Prestige-good variants (Champagne, Norwegian Fish, etc.) typically carry larger factors than their base good.
- **Monuments and major canals** (Suez, Panama, Eiffel Tower, etc.) — flat per-monument bonus while they exist on owned territory.
- **Society technologies** — many add a +% modifier to total prestige.
- **Events** — temporary modifiers (`prestige_*` static modifier prefix) for South Pole / Source of the Nile / world-fair-style achievements.

There is no hard cap, but prestige is *relative* — what matters is your fraction of global average and the highest country's score, not your absolute number.

## 3. Relations

Relations are a bilateral integer in [−100, +100] grouped into seven bands: Hostile / Cold / Poor / Neutral / Cordial / Amicable / Friendly. Many actions gate on band thresholds:

- Most diplomatic plays cannot be started against **cordial-or-better** relations (or against an outstanding obligation, an active truce, or a current subject/overlord pair).
- Improve / Damage Relations (ongoing actions) each have their own per-source cap; reaching higher requires multiple sources stacking.
- Embargo requires Poor or worse; Improve Relations stops at Amicable.
- AI acceptance of pacts and sway proposals scales with relations and attitude; relations is the floor, attitude is the slope.

The primary movers are the Improve Relations and Damage Relations ongoing actions. Most other actions and pacts also nudge relations as side effects — pacts that build trust (alliance, defensive pact, guarantee independence) drift relations up over time toward a per-pact ceiling; rivalry and embargo drift them down. Specific rates and ceilings are tunable balance numbers — read `common/diplomatic_actions/` and `common/treaty_articles/` for current values.

Diplomatic incidents (§ 5.3) hit relations with all *interested* third parties of the targeted region — not just the target. This is how a single unhinged grab can poison a colonial neighborhood.

## 4. Attitudes

**Attitudes are AI-only.** They describe how an AI evaluates another country and bias its action probabilities. Player countries don't have an attitude toward anyone; player decisions are explicit. The attitude system is therefore relevant to mod design when:

- Triggering events conditional on AI behavior (e.g. "if any neighbor's attitude toward us is Belligerent, raise war-warning").
- Tuning AI strategy modifiers (`country_diplomatic_pact_*`, `country_*_attitude_*` weights).
- Predicting which AI countries will side which way in a play.

Attitudes are computed from the AI's strategic interests plus the target's relations, infamy, military size, and pact density. There are four families:

| Family | Attitudes (least → most) |
|--------|--------------------------|
| Positive | Conciliatory → Cooperative → Genial → Protective |
| Neutral | Cautious / Disinterested / Human (Human is the AI placeholder for the *player* country, not a behavior class) |
| Negative | Wary → Antagonistic → Belligerent → Domineering |
| Subject-only | Loyal → Aloof → Defiant → Rebellious (only present on subjects toward their overlord) |

Behavior implications: Protective AIs offer subject status and side with the target in plays; Genial improve relations and seek defensive pacts; Domineering subjugate or integrate; Belligerent target the country in plays; Rebellious subjects seek independence (and can be targets for *Liberate Subject* sways — see `vanilla_war_reference.md` § 1.4). Cautious / Disinterested / Human all have no behavioral effect on their own.

## 5. Infamy

Infamy is the engine's brake on aggressive expansion: every conquest, annexation, regime-change, or sovereignty violation ratchets it up; it decays slowly; at high levels it makes every diplomatic action more expensive and unlocks the *Cut Down to Size* war goal against you.

### 5.1 Range and decay

Infamy ranges roughly 0–1000 (the upper bound is a soft ceiling — most countries never approach it). It decays continuously over time at a base rate set in defines, with a faster rate when the country has positive influence balance. Modifiers can multiply decay further; the *Repudiated Obligation* modifier (gained by rejecting a proposal where someone called in an obligation) cuts decay for 5 years. Pull current rates from `common/defines/` and the relevant static modifier files.

### 5.2 Levels

Infamy is bucketed into four levels: **Reputable → Infamous → Notorious → Pariah**. Each higher level raises pact-upkeep costs, increases the infamy attached to peace-deal demands made *against* you, raises subject liberty desire, and inflates radicals from conquered states. The breakpoints between levels are tunable balance numbers — see `common/defines/` for current thresholds.

**Pariah is the special level.** Any great power can target a pariah with the *Cut Down to Size* play, which (if won) returns conquests and releases subjects from a recent window and nullifies all of the pariah's war-goal claims in active wars. Pariah is the engine's "the world will gang up on you" state, not just a sticker.

### 5.3 Infamy gain — the shape of the formula

For most diplomatic demands (war goals, sovereignty violations, expel-diplomats), infamy is computed as a base value scaled by a chain of multiplicative factors. The *factors* are the durable mechanism; the specific values move between patches.

The factor chain conceptually looks like:

```
Infamy ≈ Base × (1 + PopMult) × StateMult × (1 + InitiatorRankMod + TargetRankMod)
            × SubjectMult × UnrecognizedTargetMod × OtherModifiers
```

What each factor means:

- **Base** — set per war goal / action. Annexation is the largest; sovereignty violations and minor goals are smaller.
- **Pop multiplier** — scales by the *population* of the targeted state(s), with per-state and total caps. Targeting a high-population state is dramatically more expensive than a low-population one of equivalent strategic value.
- **State multiplier** — discounts apply per state for unincorporated targets and primary-culture-homeland targets of the initiator (these stack). So reclaiming your own primary-culture homeland is cheaper than grabbing a foreign incorporated state.
- **Initiator / target rank modifiers** — high-rank initiators and high-rank targets both inflate infamy; unrecognized targets are discounted for recognized initiators (with progressive discounts from Colonization → Civilizing Mission → the *Colonial Offices* principle).
- **Subject multiplier** — heavily discounts annexing your own docile subject (low liberty desire or opposing you in a play).
- **Other modifiers** — tech (Multilateral Alliances), ruler traits (Cautious / Reckless), and event-applied country modifiers.

Pull the actual numbers from `common/diplomatic_plays/`, `common/defines/`, and the relevant tech / trait files. Two practical implications survive any specific rebalance:

1. **Conquering one big incorporated state is much costlier than conquering several small unincorporated states** with the same total population, because pop multiplier is per-state-capped.
2. **Sovereignty violations and regime changes are also infamy-bearing** — not just war goals. Expel-diplomats has its own scaled infamy charge by target rank.

### 5.4 Diplomatic incidents

When an action generates infamy, it usually also generates a **diplomatic incident** localized to a specific strategic region. Every country with an interest in that region takes a relations penalty toward the actor, scaled by the infamy generated. This is how a single conquest in the Balkans poisons relations with every great power that has interests there, even though they weren't the target. Incidents are the engine that makes "great-power consensus" mechanically real.

Some events and a handful of effects can also create incidents directly (regime change pulses, late-game decolonization events). Search for `create_diplomatic_incident` effects in vanilla and mod scope to find them.

## 6. Interests

Interests represent diplomatic engagement with a strategic region of the world. They are *the gate* on most diplomatic actions: most plays, most pacts, and most actions require interest in the region they target. **Lacking interest in a region is a meaningful tool**, not just a default — when targeting a multi-region empire, picking a region your rivals are not engaged in keeps them out of the play.

The system is **tiered**, not binary. A country's interest in a region sits at one of six levels (None → Observant → Engaged → Influential → Pervasive → Hegemonic) based on a continuous **involvement** score that builds up through diplomacy, military presence, subjects, and outright conquest. The old declared-interest *pool* — a small per-rank slot count you spent like a currency — no longer exists; the binary "I declare interest" button is gone. Verify this against the live game's tooltip if anything reads ambiguously: the wiki, older code comments, and any mod docs that talk about a "declared interest pool" or `country_max_declared_interests_add` are stale.

### 6.1 Locality

Every country is either **local** or **non-local** to a given strategic region. Locality is the engine's way of saying "this country is part of this neighborhood":

- A country is local if **any** of: its capital is in the region, a substantial fraction of its locality score is in the region, or a substantial fraction of its incorporated states are in the region (specific thresholds in `common/defines/`).
- A country's locality *score* in a region is computed from its share of owned states, population, and GDP in that region — so a country with one tiny state in a region has very little locality there, while a country with most of its empire in that region has very high locality.

Locality matters because it controls **how much involvement another country can leech from it**. Non-local countries gain involvement primarily by signing treaties with local countries; the involvement generated scales with the local partner's locality. Signing a treaty with a low-locality fringe country in a region barely moves the needle; signing the same treaty with the regional hegemon gives a lot.

### 6.2 How involvement is gained

Involvement is built up by *doing things* in or to the region:

- **Owning states** in the region (most direct path — natural locality).
- **Having subjects** that own states in the region.
- **Treaties with local countries** — investment rights, military assistance, defensive pact, embassy, alliance, etc. each contribute, scaled by the partner's locality.
- **Power-bloc embassies** in local countries.
- **Projecting power** with fleets off the region's coast.
- **Conquest** (post-play, the new owner inherits or builds locality from the conquered states).

In-progress colonies do *not* by themselves keep involvement up — once a colony state finishes colonizing it counts as owned territory and contributes locality; while it is still being colonized it is a goal, not an asset.

Note: 1.13 also **consolidated the strategic-region map**, generally reducing the number of regions worldwide (South America was the template; the rest of the map was made denser-per-region to match). Any mod content that hardcodes pre-1.13 strategic-region IDs (including in script triggers, custom JEs, or events with `region = sr:...` clauses) needs verification on patch upgrade — region IDs may have been merged or renamed.

### 6.3 Tiers and what they gate

The six tiers, in order of increasing involvement, are: **None → Observant → Engaged → Influential → Pervasive → Hegemonic**. Each tier loosens what's possible in the region. Conceptually:

- **None / Observant**: foreigner with little to no presence. Trade advantage is penalized (export-only at lower tiers); wargoal infamy is inflated; plays cannot be started.
- **Engaged**: can colonize, can start plays, can sign defensive pacts and guarantee-independence treaties; some infamy inflation remains.
- **Influential**: alliances and support-independence allowed; missions accessible; can stake claims (decentralized only).
- **Pervasive**: can stake claims anywhere in the region.
- **Hegemonic**: wargoal infamy in the region is *discounted* (the infamy curve flips at this tier); decree cost is reduced; full pact and play access. Hegemonic actors also generate **colonial claims** automatically — when a colony in the region grows past a threshold of a state region's size, the engine grants a claim on it. A slow, soft form of expansion.

This is what makes great-power competition in popular regions (Balkans, China, India, Africa) feel adversarial — Pervasive actors can stake claims and start plays anywhere, and Hegemonic actors get an infamy discount on top. Specific involvement thresholds and the per-tier modifier values are tuning numbers — read `common/defines/`, `common/diplomatic_actions/`, and any "interest" / "involvement" related files for current numbers.

### 6.4 Trade implications

Trade routes between countries with no interest overlap suffer trade-advantage penalties (see `vanilla_economy_reference.md` § 14). The penalty scales by tier: None penalizes exports, Engaged is roughly neutral, Hegemonic *adds* trade advantage. Lacking interest in a foreign market is a real cost on imports/exports — the tier system does not just gate plays, it gates economic reach.

## 7. Diplomatic actions

Two big classes:

- **Instant actions** happen at the moment of acceptance and are done.
- **Ongoing actions** are paid for in {{influence}} per tick and apply effects continuously until manually broken or a condition auto-breaks them.

Some actions also appear as **sways** during diplomatic plays (offered to potential participants for support — see `vanilla_war_reference.md` § 1.4) or as **treaty articles** (see § 8). When offered as a sway or article, they cannot be broken for 10 years.

The catalog of vanilla actions is in `common/diplomatic_actions/`. The 1.13 set, grouped by category:

### 7.1 Instant actions

- **Expel Diplomats** — costs the actor a flat infamy charge scaled by target rank, blocks the target from improving relations for a multi-year window, reduces their leverage generation if they're a power bloc leader, cancels any *Support Separatism* targeting the actor.
- **Redeem Obligation** — gain a relations bonus and absolve a held obligation.
- **Trade States** — both sides exchange a state. Mutually consensual; the targeted state must not be the capital, a colony, or in the same state region as a state owned by the other party.
- **Violate Sovereignty** — wartime tool to drag a neutral country into the war. Generates an incident either way; on accept the target joins the actor's side and the actor pays a moderate infamy charge; on decline the target joins the *enemy's* side and the actor still pays a smaller infamy charge. Use carefully.
- **Orchestrate Coup** *(1.13 new)* — orchestrate a regime change in a weaker target through a friendly Lobby in that country. Conditions and effects depend on the target's lobby landscape. Note that as of 1.13, **coups in general now require a reason** (e.g. failed law enactment, failed Commitment, failed Petition, *Orchestrate Coup* itself, *Depose Ruling Dynasty*, certain ruler traits) — the engine no longer fires unprompted coups.
- **Join Power Bloc / Invite to Power Bloc** — see § 9.
- **Subjugate / Force Regime Change / Impose State Religion / Spread Primary Culture / Impose Education System / Impose Colonization / Impose Policing / Impose Same Army Model / Impose Citizenship / Impose Church and State** — power-bloc-leader actions, gated on identity and cohesion. See § 9.

### 7.2 Ongoing actions

All of these cost {{influence}} per tick (modified by target's rank, actor's infamy, lobby clout). All auto-break when their conditions become false.

- **Improve Relations** — drifts relations up over time toward a per-source ceiling. Highest-cost ongoing action; blocked at Amicable and above.
- **Damage Relations** — drifts relations down toward a per-source floor. Cheaper than Improve.
- **Rivalry** — tags the target as a rival, shifts lobby appeasement on both sides, drifts relations down slowly, and **generates a positive influence pool for the actor** scaled by overlapping interests and rank gap. Also cuts the actor's leverage generation on the target if the actor leads a bloc. Locked for 1 year minimum once started.
- **Embargo** — disables all trade routes between the two countries, drifts relations down slowly, cuts leverage generation if target is a bloc leader. Gated on Poor-or-worse relations.
- **Fund Lobbies** *(Sphere of Influence DLC)* — pays accepted pops in the target a fraction of actor income (capped). Biases pop attraction in the target toward pro-actor lobbies; can spawn new pro-actor or pro-overlord lobbies.
- **Support Separatism** — increases minority movement attraction and activism for the actor's primary cultures inside the target. Drifts relations down slowly.

Rivalry is the pivotal one for power balance: as a great power, rivalrying weaker neighbors is a baseline source of free influence — the influence gain scales with overlapping interests, rank gap, and lobby clout, so even with rank-mismatch penalties it usually pays. Specific costs and rates are tuning balance numbers; read `common/diplomatic_actions/` for current values.

### 7.3 Subject-only actions and pacts

A separate cluster of pacts and one-shot actions only available between subject and overlord (or, for some, between bloc leader and member). The full table is in the wiki; the *categories* of mechanics they expose are:

- **Income / payment levers**: Raise Payments (more income, +liberty desire), Decrease Payments (less income, −liberty desire). Mutually exclusive.
- **Loyalty / autonomy management**: Support Regime (+legitimacy, −LD weekly, −actor legitimacy), Increase / Decrease Autonomy (changes subject type up or down), Knowledge Sharing (tech spread, −LD weekly).
- **Service obligations**: Exempt from Service (subject doesn't auto-join overlord plays; small −LD), Enforce Military Access (drags subject into all overlord wars; +LD).
- **Religious / cultural levers**: Evangelize (+conversion in subject, ±LD by IG composition), Change Language of Administration, Appoint / Request Colonial Governor.
- **Land transfers**: Grant State (overlord → subject, −LD), Take State (overlord ← subject, +LD + incident infamy), Demand State (subject ← overlord, asked-for transfer).
- **Annexation**: overlord can demand annexation of puppet/colony/vassal subjects (with a heavy infamy discount if the subject is in the Low LD band or is in rebellion).
- **Empire-flavored**: East India's *Invoke Doctrine of Lapse* on princely-state vassals.

Most subject-side actions have an ongoing influence cost (paid by the overlord), a year-scale break lockout, and produce an LD penalty if manually broken.

## 8. Treaties, articles, obligations

Treaties are bilateral binding agreements signed for a fixed period (5 / 10 / 15 / 25 / 99 years). They contain one or more **articles** — individual commitments. The treaty machinery is documented in detail in `docs/treaty_articles_reference.md`; this section gives the diplomatic-side concepts.

### 8.1 Treaty mechanics

- **Binding period.** Withdrawing before binding ends costs infamy, relations, and triggers a truce. After binding, either party can withdraw freely.
- **Renegotiation.** Either party can propose changes; if accepted, a new binding period starts (potentially shorter than the original).
- **Counteroffers.** When receiving a treaty proposal, you can send a counter-offer instead of accepting/declining.
- **Enforcement.** A treaty can be enforced via the *Enforce Treaty* war goal — the only formal way to make non-fulfillment costly beyond simple breach penalties.

### 8.2 Article shapes

Articles split into:

- **Mutual articles** — affect both sides equally (Alliance, Defensive Pact). Both pay influence upkeep.
- **Directional articles** — have a *source* and *target*. Either party can propose either direction. Some require an input (transfer goods needs the good name and amount; state transfer needs the state).

Influence upkeep is paid asymmetrically — for example, an *Investment Rights* article's 50 influence is paid by the *target* (the country granting investment rights), not the source (the country receiving them). Verify which side pays before designing a custom treaty pattern.

The current full list (1.13): Alliance, Defensive Pact, Guarantee Independence, Investment Rights, Military Assistance, Money Transfer, State Transfer, Treaty Port, Power Bloc Embassy, Join Power Bloc, Military Access, Trade Privileges, Transit Rights, Goods Transfer, Support Independence, Take on Debt, Law Commitment, Non-Colonization Agreement, Company Monopoly, Prohibit Trade with World Market, No Tariffs, No Subventions. Most non-DLC ones gate on International Relations or Central Banking tech. Two notes specific to 1.13:

- **Military Access** no longer requires strategic land adjacency between the two countries; the old adjacency gate was removed in 1.13.
- **The Great Wave (1.13)** added several naval-themed articles: **Ship Transfer** (transfer named ships from one country to another), **Strait** articles (forbid a country from closing a strait, or grant exemption from strait closure), and an article enforcing **abandonment of Piracy**. There is also a **Naval Hostilities** treaty option — "gunboat diplomacy" — where the offerer threatens to conduct hostile naval activities for 180 days if the treaty is declined, blurring the peace/war boundary without formally entering a play.

### 8.3 AI acceptance

The AI computes an acceptance score per article. Above some always-accept threshold the AI takes the deal automatically; below an always-decline threshold it refuses; between, it's chance-based. **Offering an obligation, calling in an existing one, or holding a relevant pact** all push acceptance up by tunable bumps; **demanding an obligation** pushes it down. The default thresholds and bump sizes are balance numbers; what matters structurally is that obligations are the chief lever for swinging deals you would otherwise lose.

### 8.4 Obligations

An **obligation** is a one-shot promise that the holder can spend later. They are gained from:

- Sway proposals during plays (offering an obligation to a third party as a sway).
- Treaty articles that create them (typically gained when the binding period ends, or after a hard-coded expiration window, whichever comes first).
- Several events.

Once held, an obligation can be:

- **Called in** to add a substantial acceptance bump to a diplomatic-action proposal or sway during a play.
- **Absolved** voluntarily for a relations bonus.
- **Refused** by the obligated country — but doing so costs them a multi-year *Repudiated Obligation* modifier (prestige and infamy-decay penalties), large relations losses with the proposer and with everyone else they owe an obligation to. While owing an obligation, a country *cannot oppose* the obligation-holder in a play.

Obligations expire after a fixed window if unspent.

For mod design, this means: any system that creates obligations is creating long-lived political capital, more durable than relations and more flexible than treaty articles. Use sparingly.

## 9. Power blocs

A power bloc is an international organization with a leader and members. The leader pays a continuous 500 {{influence}} cost (only one country pays; if leadership shifts via power struggle, the new leader pays). Power blocs are documented in detail on the wiki and via `/raw/PowerBloc*`; this section is the conceptual map.

### 9.1 Creating and joining

- Only **great**, **major**, and **unrecognized major powers** can create a bloc (cost: 500 {{influence}}; not allowed under Isolationism / Canton System).
- The first **mandate** (free at creation) selects one of the central identity's two primary principles.
- Subjects of all kinds **automatically join and leave with their overlord** — they cannot make independent bloc choices.
- Without DLC, only the Trade League identity is selectable for new blocs. Sphere of Influence DLC unlocks the other four (Sovereign Empire, Ideological Union, Military Treaty, Religious Convocation). Iberian Twilight unlocks Cultural Commonwealth.

### 9.2 Central identities

| Identity | Headline mechanic |
|----------|-------------------|
| Trade League | Customs union (single market across the bloc); leader gets a trade-capacity bonus; non-leader members contribute Merchant Marine to the leader (was "convoy contribution" pre-1.13 — see `vanilla_war_reference.md` § 10.1) |
| Sovereign Empire | Leader can subjugate bloc members via the Subjugate action; weak liberty-desire reduction across the bloc's subjects |
| Ideological Union | Leader can impose Governance Principles + Distribution of Power laws + force regime change; faster law enactment for the leader |
| Military Treaty | Leader gets a prestige bonus from power projection; can attach a free wargoal when supporting members; all members get a training-rate bonus |
| Religious Convocation | Leader can impose state religion; clergy IP contribution efficiency bonus for the leader; conversion / birth-rate / Devout-strength bonuses across all members |
| Cultural Commonwealth | Leader can impose Citizenship law and *Spread Primary Culture* on members |

Identity also conditions which **principles** are selectable as primary, and which laws the leader cannot enact (e.g. Military Treaty cannot enact Peasant Levies; Religious Convocation cannot enact Total Separation or State Atheism).

### 9.3 Principles and mandates

Each bloc has up to four principle slots; slot count gates on prestige rank and member count. Without SoI DLC, only one principle is allowed and only Internal/External Trade are selectable. With SoI, all four slots are possible; the third and fourth gate on the bloc reaching a high prestige rank and a minimum member count.

Principles tier from I → III. Each tier costs **mandates** to enact: a tier-III principle from scratch costs more than upgrading an existing tier-II to III. Mandates accumulate from a per-week progress pool, capped at a small number of stored mandates (so a passive bloc can never sit on an indefinite mandate stockpile). Once a slot is filled, the slot persists even if the unlocking conditions later become false.

**Mandate generation** is roughly:

- A per-week progress trickle from each non-leader member, scaled by the member's rank — high-rank members contribute more than insignificant ones, and insignificant / unrecognized-power members typically contribute zero.
- A small base trickle from the bloc's prestige rank itself.
- Multiplied by the current **cohesion level** — mandate progress at Fractured cohesion is a fraction of the same bloc's progress at Orchestrated.

The principle catalog has two layers:

- **Primary principles** (one per identity, must hold at least one or eat a cohesion penalty): Internal/External Trade (Trade League), Vassalization (Sovereign Empire), Creative Legislature (Ideological Union), Defensive Cooperation (Military Treaty), Sacred Civics (Religious Convocation), Freedom of Movement (Cultural Commonwealth). Plus a second identity-locked option per identity (External Trade vs Internal Trade, Exploitation of Members, Ideological Truth, Aggressive Coordination, Divine Economics, Shared Canon).
- **General principles** available across identities: Advanced Research, Colonial Offices, Construction, Food Standardization, Foreign Investment, Market Unification, Militarized Industry, Police Coordination, Transportation Infrastructure, Companies (CoC DLC), Maritime Supremacy (Great War DLC).

Primary principles also each carry a small flat cohesion bonus at higher tiers, but the bonus only applies once per identity (you cannot double up by enacting both primary principles for the same identity). The mod adds custom power-bloc-side modifiers that ride on top of vanilla principles; see `common/power_bloc_principles/extra_power_bloc_principles.txt` and the `tech_gate_modifier_types.txt` registry.

### 9.4 Cohesion

Cohesion is the bloc's "is this functional?" score (0–100), bucketed into five bands: **Fractured → Divided → Stable → Controlled → Orchestrated**. The bands modify leverage generation and mandate progress in either direction relative to Stable. Cohesion drifts toward a target value derived from identity-specific factors.

The factor *patterns* (durable across patches):

- **Per non-leader member**: each independent non-leader member subtracts cohesion. The size of the per-member penalty is identity-specific — Trade Leagues lose less per member than Sovereign Empires. Big blocs are intrinsically less cohesive.
- **Worst-case member effects**: relations, infamy, government difference, religion, autocracy gap — taken from the *worst* member, so a single antagonistic member can pull the entire bloc down. Most are scaled by the bad member's rank.
- **Leader-dominance bonuses**: leader's share of bloc GDP / prestige / power projection adds cohesion (which factor depends on identity — Trade League: GDP share; Sovereign Empire: prestige; Military Treaty: power projection).
- **Identity-specific "alignment" factors**: Religious Convocation rewards Devout in government and members of the same faith; Cultural Commonwealth rewards a high-clout PB+Intelligentsia and high primary-culture acceptance; Ideological Union rewards leader legitimacy and law alignment.
- **Anti-identity laws**: National Militia in a Military Treaty, Total Separation / State Atheism in a Religious Convocation, Multiculturalism in a Cultural Commonwealth all eat cohesion per offending member.
- **Non-great-power leader**: a flat-multiplier penalty applies across the board, making small-power-led blocs intrinsically harder to keep cohesive.

Practical implication: a bloc's cohesion ceiling is set by *who* leads, *how aligned* members are with the identity, and *how many* members exist. Adding a fifth member usually feels worse than adding the first. Specific per-factor weights are in `common/power_bloc_identities/` and the script values referenced from there.

### 9.5 Leverage

Leverage is the mechanism that lets a power bloc *invite* a country to join (and that gives mod systems a hook into who-influences-whom).

The model is fixed-pool: each country has a finite leverage pool, divided among itself and all power blocs generating leverage on it, weighted by each one's **leverage factor**. The country's own self-leverage is its **leverage resistance**, which scales with rank (high-rank countries are intrinsically harder to leverage) and with laws like trade policy / migration / free speech.

A bloc needs a meaningful leverage advantage over any other bloc *and* over the country itself to extend an invitation. So influence over a great power requires either (a) a single overwhelming source — alliance + investment rights + treaty port + economic dependence stacking — or (b) suppressing other blocs' leverage on the same target.

**Leverage factor sources** are additive into the share calculation. The full list lives in `common/script_values/01_power_block_values.txt`; conceptually the factors fall into a few buckets:

- **Baseline**: leader has interest in target's region (required to generate any leverage at all); already-member sticky bonus.
- **Diplomatic depth**: alliances, defensive pacts, guarantee independence, military assistance, power-bloc embassy, trade privileges, investment rights — each contributes a chunk; alliances are the heaviest single source.
- **Geographic / proximity**: treaty port in target, direct or strategic adjacency.
- **Economic**: economic dependence per point (boosted by the Foreign Investment principle).
- **Wartime**: at-war-together with the target adds leverage.
- **Identity / cultural**: Religious Convocation same-religion bonus; per-shared-trait cultural-overlap bonuses.
- **Lobby clout**: pro-leader lobbies in the target add leverage proportional to their clout; anti-leader lobbies subtract.

**Leverage multipliers** (multiplicative penalties — applied once across all sources):

- Diplomats expelled (penalty grows with target's rank).
- Cultural status of any of target's primary cultures in the leader — discrimination tiers cut leverage, with violent hostility being the worst (worst-only is what counts).
- State religion clash with no Freedom of Conscience in the target — extra penalty for Religious Convocation blocs.
- Leader has no interest in target's *capital* region (vs the targeted region only).
- Leader at war with the target.
- Leader infamy at Infamous / Notorious / Pariah levels — penalty stacks at higher infamy.
- Leader unrecognized while target is recognized.

This is the mechanism behind why a hostile relationship is so hard to "diplomatically sphere": expelled diplomats + unrecognized status + war drive the multiplier chain so low that even a stack of strong factor sources can't reach an inviteable advantage.

### 9.6 Power struggle

A power bloc member with significantly more prestige than the current leader, sustained over a multi-month challenge window, becomes the new leader. The original bloc founder gets a faster reclaim window than a generic challenger. This is the primary in-game mechanism by which leadership turns over without a bloc dissolution.

### 9.7 Leaving and ejecting

A member can leave a bloc only when the bloc's leverage on it has dropped to a low threshold, and not before a minimum membership tenure has passed. Leaders can unilaterally eject members; doing so costs relations, creates a truce, and reduces cohesion.

## 10. Subjects

Subjects are a diplomatic-pact relationship: one country (overlord) maintains another (subject) at an ongoing influence cost. They are documented exhaustively on the wiki and in `common/subject_types/00_subject_types.txt`; this section is the concept map.

### 10.1 Subject types (1.13)

| Type | Autonomous? | Annex path | Income transfer |
|------|-------------|------------|-----------------|
| Puppet | no | direct | yes |
| Vassal | no | direct | yes |
| Colony | no | direct | yes |
| Crown Land | no | direct | yes (smaller) |
| Personal Union | no (special) | special | — |
| Protectorate | yes | needs autonomy reduction | — |
| Tributary | yes | needs autonomy reduction | yes (smaller) |
| Dominion | semi (auto-joins overlord plays) | needs autonomy reduction | — |
| Chartered Company | semi | needs autonomy reduction | — |

(Specific income-transfer percentages, convoy contribution rates, and the influence upkeep are tunable balance numbers in `common/subject_types/00_subject_types.txt` — pull them from there when they matter for a calculation.)

The two big functional axes are:

- **Recognition pairing**: vassal/tributary are unrecognized-overlord types; puppet/colony/protectorate/dominion are recognized-overlord types. Crossing recognition transfers convert types as in the wiki's transfer table.
- **Autonomy axis**: puppet ↔ protectorate, vassal ↔ tributary, colony ↔ dominion. *Decrease Autonomy* moves toward annexation; *Increase Autonomy* moves toward independence.

Personal unions and chartered companies are special: PUs require Nationalism tech to change autonomy and end if either side leaves Monarchy; chartered companies require Civilizing Mission tech and have unique throughput / construction bonuses applied to government-owned buildings via the overlord's company.

### 10.2 Liberty desire

Liberty desire (LD) is per-subject in [0–100], bucketed into three bands: **Low / Moderate / High**. Low LD makes discriminated-pop radicalism softer and produces more loyalists from movements; High LD does the opposite and unlocks the subject's ability to demand independence in a play. Specific band thresholds and per-band modifier values are tuning balance numbers in `common/defines/`.

Weekly LD movement is the sum of:

- **Flat sources**: relations band (worse relations push LD up), overlord infamy (a high-infamy overlord drives LD up sharply), per-pact bumps (Knowledge Sharing / Support Regime / Decrease Payments / Exempt from Service push down; Raise Payments and new pacts push up), market isolation, zero-prestige edge cases.
- **Scaling sources**: prestige ratio between subject and overlord (subject approaching overlord prestige → higher LD; subject types vary in steepness — protectorates/tributaries have softer scaling, annexable subjects have steeper), army-power-projection ratio, overlord's alliance density (more/stronger allies → lower LD), economic dependence.
- **Lobby clout multipliers**: pro-overlord lobbies in government cut LD; anti-overlord lobbies in government raise it.

Then a chain of multipliers applies: a **self-correcting scaling** (positive LD movement weakens as LD approaches the ceiling; negative movement weakens as LD approaches the floor — LD has a natural pull toward the middle of its range), modifier multipliers from active country modifiers, and a halving multiplier on positive LD while the subject is in truce with the overlord.

The engine also enforces a small **floor on the absolute weekly LD movement** (you can't ever drift LD by less than a tiny amount/week in either direction once it has a non-zero target), which means subject management is always in motion — you can never lock a subject at 0 or 100 LD permanently without active pact maintenance.

### 10.3 What LD gates

- **Low band**: overlord can *decrease autonomy*. Annexation infamy is heavily discounted.
- **High band**: subject can request *increase autonomy*. Subject can demand increase-autonomy or independence in a play. Protectorates and tributaries can demand independence at any time.
- **Top of band**: highest-LD subjects can rebel by initiating a play themselves. When a subject rebels, overlord wargoals against it get a heavy infamy discount.

### 10.4 What overlords get

- **Income transfer**: a fraction of the subject's tax / minting / non-tariff income, varying by subject type (vassals/puppets/colonies on the higher end, crown lands and tributaries lower; protectorates and dominions don't transfer income).
- **Merchant Marine**: a fraction of the subject's Merchant Marine capacity contributes to the overlord (renamed from "convoys" in 1.13).
- **Prestige cascade**: a substantial fraction of subject GDP, plus smaller fractions of subject army and navy power projection, contribute to overlord prestige.
- **Market access**: subjects auto-join overlord's market as junior members.
- **Auto-call to war**: non-autonomous and semi-autonomous subjects auto-join their overlord's plays. Autonomous subjects do not.
- **Law imposition**: overlord can initiate any law-change in any non-protectorate / non-tributary subject (subject still has to enact it through normal mechanics; chartered companies / colonies / crown lands / puppets get an enactment-success bonus on imposed laws).

### 10.5 Subject transfer

Two paths:

- **War goal**: *Transfer Subject* moves a subject between overlords. Cannot target personal unions.
- **Cascade**: when a country with subjects becomes a non-autonomous subject itself, all its subjects transfer to the new top-level overlord.

Recognition mismatch on transfer auto-converts the subject type per the table in the wiki (puppet → vassal under unrecognized overlord, vassal → puppet under recognized, etc.).

## 11. Diplomatic plays

The diplomatic-play system — phases, escalation, maneuvers, sways, war goals — is documented in detail in `docs/vanilla_war_reference.md` § 1. **Read that section before adding a play-related event or modifier.** This section only adds the diplomacy-side framing not covered there.

Plays are *the* mechanism by which infamy is generated. Almost every infamy-bearing action (annexation, conquest, dominion, regime change, humiliation) flows through a play and applies infamy when the wargoal is enforced — either at backdown / give-in (for primary demands) or at peace deal (for secondary demands). Wargoals dropped from the final peace deal refund their infamy partially or fully.

Plays interact with everything in this doc:

- **Rank** caps maneuvers and gates which goals are usable (subjugation requires major-or-better target; *Cut Down to Size* requires a pariah target).
- **Recognition** gates the subject types you can demand (recognized overlord ↔ puppet/colony/protectorate; unrecognized overlord ↔ vassal/tributary).
- **Interests** gate participation — the play is locked to its starting region's participants, plus countries with interests there.
- **Relations** floor: cordial-or-better blocks new plays.
- **Obligations** held by the *target* of the play prevent them from opposing the obligation-holder; obligations held by the initiator can be called in to bump sway acceptance.
- **Power blocs**: bloc leader can be called in via *Defensive Cooperation* / *Aggressive Coordination* sways depending on identity; *Defensive Cooperation* (Military Treaty primary I) blocks plays *between* bloc members entirely.
- **Subjects**: subjects auto-join overlord plays unless *Exempt from Service* or otherwise restricted. Wargoals against your own subject get a heavy infamy discount if the subject is in the Low LD band or is in rebellion.

The mod's unification plays (Pan-X major-unify, X-Leadership candidate-suppression) live in `common/diplomatic_plays/te_unification_plays.txt` and are designed to interact with these vanilla mechanics rather than override them. If a unification play feels broken, check whether the targets have the right rank, recognition, and culture overlap — most issues are gating.

## 12. Diplomatic catalysts

Catalysts are vanilla's diplomatic-event hook system (`common/diplomatic_catalysts/`). Various occurrences — relations crossing a threshold, an action taken between two countries, certain internal political events — fire a catalyst, which can then:

- Prompt a political lobby to form or change activism.
- Cause an AI to recompute its attitude toward another country.
- Trigger event chains.

For mod design, catalysts are how you wire "X happened, also do Y" without writing a custom on-action. The `common/diplomatic_catalysts/` directory is the canonical list; cross-reference with `/raw/DiplomaticCatalyst/<id>` to see which events the mod relies on.

## 13. Where to look in the codebase

- `common/diplomatic_actions/` — action definitions (Improve Relations, Embargo, Subjugate, etc.).
- `common/diplomatic_plays/` — play definitions (war goal IDs, infamy/maneuver costs, conditions). Mod's unification plays in `te_unification_plays.txt`.
- `common/diplomatic_catalysts/` — catalysts that fire on diplomatic events.
- `common/treaty_articles/` + `docs/treaty_articles_reference.md` — article definitions and the engine constraints around them. Mod articles in `extra_treaty_articles.txt`.
- `common/subject_types/00_subject_types.txt` — subject type definitions and their per-type pacts/actions.
- `common/power_blocs/`, `common/power_bloc_identities/`, `common/power_bloc_principles/` — bloc identity and principle definitions.
- `common/power_bloc_names/00_power_bloc_names.txt` — name selection conditions.
- `common/script_values/01_power_block_values.txt` — leverage factor source values; many cohesion factors live here too.
- `common/country_ranks/00_country_ranks.txt` — rank thresholds and per-rank modifiers.
- `defines/` — `WAR_GOAL_INFAMY_*` constants, `LIBERTY_DESIRE_*`, `LEVERAGE_*` thresholds, prestige thresholds.
- `localization/english/` — UI strings; many concepts are easier to find by their displayed string than by their script ID.

## 14. Modifier names that touch diplomacy

Verify the current set with `/modifier-search?q=<term>` before referencing. Common ones, grouped:

- **Influence and pacts**: `country_influence_add`, `country_influence_mult`, `country_diplomatic_pact_cost_mult`, `country_<pact>_cost_mult`.
- **Infamy**: `country_infamy_generation_mult`, `country_infamy_decay_mult`, `country_infamy_generation_against_unrecognized_mult`. The mod-side script-only modifier `country_banking_intervention_max_add` and similar are *not* infamy modifiers — they're cross-system gates; see `docs/scripting_best_practices.md`.
- **Plays**: `country_diplomatic_play_maneuvers_add`, `country_diplomatic_play_maneuvers_mult`. `country_war_exhaustion_casualties_mult` is the war-support side (see `vanilla_war_reference.md` § 13).
- **Power bloc**: `country_leverage_generation_mult`, `country_leverage_generation_add` (against named target), `country_leverage_resistance_add`, `country_leverage_resistance_mult`, `country_mandate_progress_mult`, `country_cohesion_*` (verify exact suffix).
- **Subject**: `country_subject_income_transfer_mult`, `country_liberty_desire_*`, `country_subject_liberty_desire_*` (subject-scope vs overlord-scope — verify which variant the engine reads in your scope).
- **Interests / involvement**: the names in this family churn between patches and the binary declared-interest model is obsolete (see § 6). Search via `/modifier-search?q=involvement` and `/modifier-search?q=interest` to find the current set; expect generation/tier modifiers rather than pool-size ones.

When introducing a new diplomacy-touching modifier name, **always** verify via `/engine-docs/modifiers` that it exists. The engine silently no-ops invalid names (see `docs/scripting_best_practices.md` § "Modifier validation").

## 15. Notes for mod design

- **Don't double-tax infamy.** Mod events that "punish aggression" via `country_infamy_generation_mult = +X` stack multiplicatively with vanilla infamy. The vanilla pop multiplier already makes high-pop-target conquests very expensive — adding a further multiplier on top can vault a single annexation past Pariah threshold. Audit the cumulative effect on a high-population-target annexation before shipping.
- **Subject income transfer caps the overlord's economic leverage.** Income-transfer percentages are meaningful when the subject is small and a wash when the subject is comparable to the overlord. Subject-scaling rebalances should multiply the *transfer rate* (game lever in `common/subject_types/`) rather than adding flat country income (leaks out of the system).
- **Power bloc cohesion is fragile near non-great-power leaders.** The flat-multiplier cohesion penalty for non-great-power leaders is severe; designing a small-power-led bloc system needs to either remove that penalty in script or accept that the bloc will sit at low cohesion most of its life.
- **Liberty desire is a scope trap.** Some `country_subject_liberty_desire_*` modifiers apply to the *subject* scope; others apply to the overlord. Read the modifier's signature in `/engine-docs/modifiers` and verify which scope you're applying it from. Don't paste from another modifier without checking.
- **Don't grant interest, grant involvement.** With the tiered system (§ 6), there is no interest "slot" to hand out. Mod events that want to push a country into a region should add involvement through the existing levers (subject grant, treaty article, fleet projection, owned-state grant) rather than inventing a flat-tier-up effect. Bumping a country from None straight to Hegemonic via event skips the whole mechanic and kills the gameplay loop the system is built around.
- **Treaty articles are bilateral.** Articles that "punish breakage with infamy on the breaker" already exist in vanilla — don't re-implement that as a custom event. See `docs/treaty_articles_reference.md` for the engine-supported article shapes.
- **Recognition is sticky.** When designing events that hand recognition out (or strip it away), use vanilla precedent: only the Sick Man path strips it, and only because that JE is gated on extreme conditions. Mass-stripping recognition through events would invalidate decades of player diplomacy.
- **Wargoal infamy cost is a *weak* gate at low pop densities and a *very strong* one at high.** The pop multiplier can blow up the cost by 50× for a high-pop target. When designing a play that creates wargoals programmatically, check the actual generated infamy on a representative target; don't assume the base value is what'll show up in-game.
