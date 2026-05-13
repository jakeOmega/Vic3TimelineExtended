# Vanilla Politics Reference (Victoria 3)

A primer on how the **base game's** political systems work, written for AI agents that need context before touching mod content. This doc covers vanilla mechanics only — mod-specific systems (banking-cycle politics, civil-rights JEs, decolonization rework, combined-arms IG traits, the dormant `te_map_mode_*` survey, etc.) live in `docs/systems/journal_entry_systems.md` and `docs/systems/mod_systems.md`.

> **Last verified against vanilla:** 1.13.5 (Hotfix to "The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. The patch runbook (`docs/guides/vanilla_patch_runbook.md`) directs whoever performs a vanilla bump to revisit this file.
>
> **Verify before relying on names.** Law IDs, IG IDs, ideology IDs, party IDs, movement IDs, character-trait IDs and modifier names cited below should be verified via the mod state server (`/laws`, `/raw/InterestGroup/<id>`, `/raw/Ideology/<id>`, `/modifier-search?q=`) before referencing them in code. Vanilla renames things across patches.
>
> **This doc captures concepts, not exhaustive lists.** Per-law approval matrices, per-IG attraction tables, per-party formation conditions, per-character-trait modifier lists, and per-movement formation triggers are voluminous and drift each patch — they live in `common/laws/`, `common/interest_groups/`, `common/parties/`, `common/political_movements/`, `common/character_traits/`, `common/ideologies/`. Read this doc for the *shape*, then read those files for the *values*.
>
> **Numbers describe mechanism, not balance.** Range bounds (legitimacy 0–100, popularity ±100), tier *names* (Marginalized / Influential / Powerful; Angry / Unhappy / Neutral / Happy / Loyal; Illegitimate → Righteous), and structural ratios (movement support = ⅓ population + ⅓ military + ⅓ raw political strength) clarify *how* the system behaves and tend to survive vanilla patches. Specific thresholds (the exact clout % at which an IG becomes powerful, the exact authority cost of suppressing a movement, exact base enactment days per law group) drift and are looked up via `common/defines/` or the relevant `common/<folder>/` file when they actually matter.
>
> **Wiki-source provenance.** This doc is initially seeded from a `scratch/wikis.txt` extract whose articles are individually dated 1.8–1.13. The Interest Groups article in particular is tagged 1.8 — predating the 1.10 IG-attraction rework — so § 5 (especially the per-profession attraction matrix) is the most drift-prone. Cross-check against `common/interest_groups/` and `/raw/InterestGroup/<id>` before quoting attraction values.

## 1. Politics overview: the layered loop

Vic3's politics layer is a feedback loop with five tightly-coupled mechanisms; touching any one of them perturbs the others. Reading order — outer → inner:

| Layer | Question it answers | Where it lives |
|---|---|---|
| **Pops** | Who wants what, and how strongly? | `common/pop_types/`, state-level demographics |
| **Interest groups (IGs)** | How do pop preferences aggregate into political weight? | `common/interest_groups/`, `common/ideologies/` |
| **Government & legitimacy** | Which IGs are in power, and is that arrangement stable enough to act? | `common/government_types/`, `common/laws/00_governance_principles.txt`, `common/laws/00_distribution_of_power.txt` |
| **Laws** | What policies the government can change, and how hard the change is. | `common/laws/`, `common/law_groups/`, `common/institutions/`, `common/decrees/` |
| **Movements** | Pressure from below: pops mobilizing for or against a law, possibly tipping into civil war. | `common/political_movements/`, `common/political_movement_categories/`, `common/political_lobbies/` |
| **Characters** | The named connectors: rulers, IG leaders, agitators, executives, magnates, commanders — each binds part of the loop to a face. | `common/character_traits/`, `common/character_interactions/` |

The loop in motion: pops attract to IGs by profession × wealth × literacy × acceptance × leader popularity → IG **clout** scales with pop political strength → clout & votes set government **legitimacy** → legitimacy gates law **enactment** → enacted laws change pop SoL / acceptance / strata weighting → pops re-attract; meanwhile, dissatisfied pops feed political **movements** that pressure laws independently of which IGs are in government, and at high activism, become **revolutionary**. **Characters** carry ideologies that override or amplify each step.

Three vanilla refs adjacent to this one cover layers this doc deliberately leaves alone:

- **Authority** — the country-scope flow that pays for decrees, IG suppression, consumption taxes, monopolies. See `vanilla_economy_reference.md` § 11.2 for production/consumption mechanics; § 11 below for the politics-side spends.
- **Power blocs / lobbies / leverage** — how foreign politics feeds into domestic IG approval. See `vanilla_diplomacy_reference.md` § 9; § 5.6 below points the lobby → IG-approval connection.
- **War support** — radicals and lobby clout drain wartime stamina. See `vanilla_war_reference.md` § 13.

## 2. Government and the legitimacy gauge

### 2.1 Government composition

The **government** is the set of IGs in power. All other non-marginalized IGs are the **opposition**. Both states are exclusive: an IG is either in government or out. There is no per-IG portfolio — it's a binary inclusion gate that scales legitimacy and law-support for the country.

Two exclusions are worth knowing because they're how the engine *prevents* certain coalitions:

- **Marginalized IGs** (clout below the marginalization threshold) **cannot be added to government**. They can stay in if they fall below threshold while already in government, but they can't be invited fresh.
- **Insurrectionary IGs** — IGs supporting a revolutionary movement — **cannot be added to government**. The engine considers them already in armed opposition.

Removing an IG from government immediately **radicalizes a fixed fraction of its supporting pops** — except in a six-month grace window after an election, where the first reform within that window radicalizes nobody. This grace window is the cleanest non-disruptive moment to reshuffle a government; after it expires (or after the first reform inside it lands), removing IGs goes back to being radicalization-on-touch.

A *quick reform* UI option suggests three highest-legitimacy government compositions, but it does not factor radicalization-from-removal into its ranking. Manual reform via the UI lets the player walk every non-marginalized combination.

### 2.2 The legitimacy gauge

**Legitimacy** is a single 0–100 country-scope value, bucketed into five named tiers (low → high): **Illegitimate**, **Unacceptable**, **Contested**, **Legitimate**, **Righteous**. The bucket boundaries themselves matter much less than which mechanic each tier gates:

- **Illegitimate** is the only bucket that *blocks* law enactment outright. Already-running enactments freeze (resume when legitimacy climbs); new enactments cannot start. The single exception is laws backed by a non-passive movement — pop pressure can override an illegitimate government.
- **Unacceptable** allows enactment but with an enactment-time penalty.
- **Contested** is the neutral baseline.
- **Legitimate** and **Righteous** add favorable enactment-time and scaling loyalist-generation modifiers.
- All five tiers also drive a per-tier opposition-IG approval delta and a per-tier pop loyalist/radical generation rate that compounds over time.

The mod-relevant takeaway: the only *binary* gate is "Illegitimate vs. above". Everything else is a smooth modifier that mod content can additionally push on (event modifiers like `Enacted an Imposed Law` add direct legitimacy chunks).

### 2.3 Sources of legitimacy

Legitimacy is not stored — it's recomputed continuously from a set of additive contributions. The big four:

1. **Clout share of government IGs.** A government holding 60% of total clout produces more legitimacy than one holding 30%, multiplied by the country's *clout-from-government* law setting.
2. **Vote share of government parties.** In countries with voting laws, parties that won votes contribute legitimacy proportional to their vote share, multiplied by the country's *legitimacy-from-votes* law setting.
3. **Ruler interest group inclusion.** Several Governance Principles laws (Monarchy, Theocracy, Presidential Republic, Autocracy) award flat legitimacy when the ruler's IG is in government. These are conditional on having the right governance principle; a Parliamentary Republic doesn't care about ruler-in-government.
4. **Government size penalty.** A flat per-IG penalty applies for each government slot occupied above the *government size allowance* (defaults to 1; some Distribution-of-Power and Governance-Principles laws raise it). Parties count as a single slot regardless of how many IGs comprise them — this is the primary reason parties exist as a concept.

A fifth, mechanism-shaping source — the **ideology penalty** — deserves its own subsection because it has a non-obvious cap rule.

### 2.4 The ideology penalty

When IGs in government disagree on a law's stance, the engine assesses a legitimacy penalty proportional to the disagreement. The base is *steps of difference* on the 5-point endorse↔oppose scale: a step of disagreement on one law produces a flat penalty per step.

The non-obvious rule: **only the largest disagreement counts** across all laws, not a sum across every disagreed-on law. Three IGs differing 2 steps on one law and 1 step on three others incur the 2-step penalty once, not the 2-step + 3×1-step total. This is why coalitions with one ideologically-aligned outlier feel surprisingly cheap; it's also why moving an outlier off the worst law disagreement produces a discrete legitimacy cliff.

Each law group then multiplies that base penalty by a group-specific factor — the **Governance Principles** and **Distribution of Power** groups carry the highest multipliers (because they're the foundational political laws), Slavery is similarly high, Bureaucracy/Education-System/Policing are low. The exact multipliers live in `common/law_groups/00_laws.txt` (`ideological_opinion_impact`); read them when balancing.

Two more wrinkles:

- **Parties halve the secondary IGs' contribution.** The party's *whip* (highest-clout member IG) has its stances counted at full weight; every other IG in the party has its stances counted at half. This is the structural argument for forming parties even when the ideological alignment isn't perfect — the mathematical penalty halves.
- **Tax level can directly add or subtract** legitimacy per law group via event modifiers and the tax-level setting itself; it's a small but ever-present contribution.

### 2.5 Reforming government

Government composition is mutable at any time outside of war / diplomatic-play windows. The radicalization-on-removal rule (§ 2.1) is the only mechanical cost; otherwise reform is a free action.

The *Support Regime* subject pact (`vanilla_diplomacy_reference.md` § 10) is the diplomacy-side lever for a foreign legitimacy bump: a subject below a legitimacy threshold can request the pact, which transfers a flat legitimacy chunk from overlord to subject. Mod content that wants to prop up a low-legitimacy subject without conquering it should reach for this pact rather than a mod-side scripted effect.

## 3. Laws and the enactment process

### 3.1 Three categories, three groups apiece

Vanilla has **three law categories**, each with eight law groups, each with three to nine specific laws — list and detail in `docs/engine/laws.txt` (auto-generated dump) and `common/laws/`:

- **Power Structure** — Governance Principles, Distribution of Power, Citizenship, Caste Hegemony, Church and State, Bureaucracy, Army Model, Internal Security. (Some sources also list Navy Model here in 1.13.)
- **Economy** — Economic System, Trade Policy, Taxation, Land Reform, Colonization, Policing, Education System, Health System.
- **Human Rights** — Free Speech, Labor Rights, Children's Rights, Rights of Women, Welfare, Migration, Slavery, Labor Associations.

Each country always has exactly one active law per active law group (some groups gate on culture or DLC — Caste Hegemony only exists for British-Indian-system countries; Navy Model only with the appropriate DLC). Many laws are mutually-exclusive across groups — `Multiculturalism` cannot coexist with any non-banned slavery law, for example. **Law variants** (e.g. `Canton System` replacing `Isolationism` for Han Chinese countries) inherit ideological stances from the parent but can change effects significantly.

### 3.2 Sources of enactment support

A law cannot enter enactment unless **at least one of**:

- An interest group **currently in government** endorses the change (its ideology stance on the proposed law is higher than its stance on the current one), OR
- The **ruler** endorses it (their personal ideology gives a higher stance), OR
- A **non-passive political movement** (≥ 25 activism) endorses it.

The illegitimate-government rule from § 2.2 layers on top: even with a legal endorsement, an Illegitimate government cannot start (or progress) any law enactment **except** one supported by a non-passive movement.

### 3.3 The three-phase enactment process

Once enactment starts, the law walks **three phases** at a checkpoint cadence (default per-law-group, longer for foundational groups — Governance Principles, Distribution of Power, Economic System, and Slavery — than for everyday human-rights laws; read `base_enactment_days` from `common/law_groups/`). Surplus authority and high legitimacy shorten the cadence; deficit authority and low legitimacy lengthen it. Each checkpoint resolves to one of four outcomes:

- **Success** — phase advances; on phase 3 success, the law passes.
- **Advance** — fires a positive event with a usually-unconditional success-chance bump.
- **Debate** — fires an ambiguous event; usually a tradeoff option.
- **Stall** — fires a negative event; usually reduces success chance and may add a setback.

The success / stall odds at each checkpoint are recomputed from scratch each time:

- **Base success chance** = sum of clout of endorsing IGs in government + sum of support of endorsing non-passive movements + ruler endorsement (±5% per stance step).
- **Base stall chance** = a weighted sum of opposing IGs' clout (neutral/happy opposers count half; angry opposers count 1.5×) + opposing-movement support + ruler opposition.
- **Advance chance** = 2 × success − stall.
- **Debate chance** = whatever's left to make 100%.

The weighting of opposing IGs by approval is the mod-relevant lever: an angry opposing IG creates substantially more resistance to law enactment than a neutral one of the same clout. This is why proposing approval-shifting "easy law" gestures before a hard law (§ 5.4) is a real strategy, not flavor.

### 3.4 Setbacks, cancellation, cooldowns

The law accumulates **setbacks** — usually from Stall events or from success chance reaching 0%. **Three setbacks fail the law**, and a failed-or-cancelled law cannot be re-proposed for two years. Cancelling an in-progress law triggers the same two-year cooldown.

Approval effects from proposing a change last while the change is on the docket and **decay over five years afterwards**, multiplied by the law-group multiplier from § 2.4 and capped at a flat ±20 approval. Mod content that uses "propose a law to placate an IG, then cancel" needs to factor in the cooldown.

### 3.5 Imposing laws on subjects

An overlord can **impose** a law on a non-autonomous subject — Puppets, Colonies, Crown Lands, Chartered Companies — starting a normal enactment in the subject with a small success-chance bonus (the subject's IGs/ruler still need to support the law for it to succeed normally; the overlord just kicks it off). The subject receives the **Foreign Legal Imposition** journal entry with two button options: accept (begin enactment) or reject (cancels imposition, hits relations and — if it's a subject — bumps liberty desire).

Power-bloc identities and principles add additional impose-paths: Ideological Union and Cultural Commonwealth blocs let the leader impose Governance Principles + Distribution of Power and Citizenship laws respectively on members. Treaty articles can also commit a country to enact a specific law (`Law Commitment`); see `treaty_articles_reference.md`.

### 3.6 Treaty Law Commitments as enactment booster

A Law Commitment from a higher-rank counterparty grants the committing country a per-rank-difference bonus to the committed law's success chance during enactment. This is a meaningful design surface: a great-power-to-minor-power Law Commitment is a substantial enactment accelerator and shows up frequently in diplomacy-driven reform play.

## 4. Elections and voting laws

### 4.1 The election cycle

Elections happen **only in countries whose Distribution of Power law enables voting**. Cycle length is fixed at 4 years with a 6-month campaigning runup; the **only way to call a non-scheduled election is by scripted effect** (an event or JE, not a player decision). Switching from a non-voting Distribution-of-Power law to a voting one immediately starts a campaign.

During the campaign, each party is assigned a **momentum** value that fluctuates with random factors, events, and IG-leader popularity (high-popularity leaders nudge their party's momentum each tick). Final vote share is the integration of the per-week momentum into a vote tally on election day. The player's main lever is event choices that nudge momentum, plus the standing momentum effect of leader popularity.

Elections **do not** automatically reform government. They reset clout-from-votes (which moves legitimacy) and they re-evaluate party affiliations (§ 6); any government composition change is still a separate manual action. The exception is the **Presidential Elective** transfer of power: in that government type, the leader of the highest-clout IG **automatically becomes ruler at each election**, even if their IG is in opposition — flipping ruler ideology on a 4-year tick.

The post-election **6-month free-reform window** (§ 2.1) is the cleanest moment to reshuffle government in a voting country.

### 4.2 The five voting laws

Names only — exact strength multipliers per voter class drift; read them from `common/laws/00_distribution_of_power.txt` when a balance change matters:

- **Landed Voting** — only Aristocrats, Capitalists, Clergy, and Officers vote; the rest are disenfranchised.
- **Wealth Voting** — voting gated on a wealth threshold (high cutoff).
- **Census Suffrage** — voting gated on a lower wealth threshold; pop political strength scales with literacy.
- **Universal Suffrage** — wealth gating removed.
- **Single-Party State** — votes reduce to a single legal party; legitimacy-from-votes is high (large flat reward) but the field is constrained.

The structural pattern: the *legitimacy-from-votes* coefficient rises moving down the list (Universal Suffrage gives the largest legitimacy-from-votes contribution); the *clout-from-votes* coefficient correspondingly falls (Universal Suffrage downweights non-vote clout sources). This is why a country with Wealth Voting and one with Universal Suffrage feel very different at the same demographics — the legitimacy machine is reading different inputs.

### 4.3 Disenfranchisement

Three additional axes prevent pops from voting independently of voting law:

- **Discrimination** — the country's Citizenship law determines which acceptance statuses can vote at all, and may further weight votes by status.
- **Unincorporated residence** — pops in unincorporated states never vote, regardless of acceptance.
- **Politically unaligned status** — pops not aligned with any IG don't vote. Most dependents are politically unaligned; **`Women's Suffrage` and `Old Age Pension` are the two laws that lift portions of dependents into political alignment**, which is why those laws produce visible vote-share shifts that look disproportionate to their direct modifiers.

### 4.4 Party affiliation churn

Each campaign start, all non-marginalized IGs **re-evaluate which party (if any) to join**. Joining or switching parties produces a "wants to join [Party] on next reform" deferred state if it would cross the government/opposition line — that IG is excluded from voting until the player either reforms government to honor the move or the next cycle re-shuffles.

The structural effect: parties are most volatile across elections, and unaffiliated IGs (those who couldn't find a fit) gain *no* clout-from-votes — only their pop-political-strength clout counts. This is why an IG marked "wants to join" is a tactically interesting beat: leaving it parked through the campaign weakens its destination party relative to its current party; reforming during the campaign maximizes the destination party's vote take.

### 4.5 Single-Party State chooses the ruler's party

When `Single-Party State` is enacted, the engine selects the legal party based on what already exists: if the country has parties, it picks the **ruler's current party**; if there are no parties yet, it picks the **ruler's preferred party** (the one their IG would have joined). The choice is sticky even if the ruler later changes — the law preserves the original choice until repealed.

## 5. Interest groups

### 5.1 The eight base IGs

There are **eight** IGs (plus a non-IG bucket of *politically unaligned* pops):

- **Armed Forces**
- **Petite Bourgeoisie**
- **Devout**
- **Industrialists**
- **Intelligentsia**
- **Landowners**
- **Rural Folk**
- **Trade Unions**

Names rename per country / culture / religion: Theravada Monks (Devout in Theravada countries), Junkers (Landowners in Prussia), Gentry Assembly (Landowners in Russia), Samurai (Armed Forces in Japan), Confucian Scholars (Devout in Confucian countries), Literati (Intelligentsia in China). The IG identity is the same; the localization, traits, and starting ideologies vary. The full per-country flavor table is in `common/interest_groups/` and `common/ideologies/00_ig_ideologies.txt`.

### 5.2 Clout — the zero-sum political weight

**Clout is zero-sum**: all IGs' clout sums to 100% of the country. An IG's clout share comes from the political strength of its supporting pops (most of the time the dominant source) plus, in voting countries, its share of the party-vote tally.

Three named tiers gate clout-derived behavior:

- **Marginalized** — clout below the marginalization threshold. Marginalized IGs cannot be added to government, their traits do not activate, their characters are heavily downweighted in random-affiliation rolls (×0.1 across roles).
- **Influential** — the default tier. Hysteresis applies (the threshold to *return* to influential from marginalized is slightly higher than the threshold to fall *into* marginalized; same for falling out of powerful).
- **Powerful** — clout above the powerful threshold. Powerful IGs have **doubled** trait magnitudes (negative *and* positive — a powerful angry IG hurts twice as much; a powerful happy IG helps twice as much) and a larger random-character-affiliation weight.

A safety-net rule: **IGs in government, or whose leader is the ruler's IG, cannot become marginalized** even if their clout falls below threshold. They stay influential, but with halved trait magnitudes (the "in-government but sub-marginalization-clout" case). This prevents a degenerate regime where a tiny ruler IG has its leader exiled, etc.

### 5.3 Attraction — who supports whom

Each pop divides its political strength across IGs proportionally to per-IG **attraction weights**. The mechanism shape:

- **Profession is the dominant axis** — Aristocrats overwhelmingly attract to Landowners, Capitalists to Industrialists, Officers to Armed Forces, Servicemen to Armed Forces (with smaller weights to Trade Unions in some regimes), etc. The full per-profession × per-IG attraction matrix is in the wiki and largely encoded in `common/interest_groups/` (`pop_potential` blocks).
- **Discrimination zeroes attraction** for many IG/profession combinations. A discriminated culture's pops are politically inactive in many configurations regardless of profession.
- **Literacy gates two IGs.** *Intelligentsia* has zero base attraction below ~50% pop literacy and scales linearly above. *Devout* loses attraction with rising literacy — historical secularization, mechanically modeled.
- **Law / law-group switches** add structural multipliers. `State Religion` boosts Devout attraction; `State Atheism` flattens it. `Peasant Levies` re-routes some servicemen weight. `Hereditary Bureaucrats` boosts Aristocrats attraction for Bureaucrats. Per-profession × per-law multipliers in `common/interest_groups/` are extensive.
- **Leader popularity scales attraction** for an IG by ±25% across the popularity range (full ±100 popularity = ±25% attraction shift). This is the single largest "soft" lever a player has on an IG's clout without legal change.
- **In-government IGs** get a small bonus to attraction from loyalist pops; **opposition IGs** get the same from radical pops. This is the loop that lets a popular reformer's IG continue gaining clout from happy pops while in government, and a radicals-driven opposition gain clout from unhappy ones.

The takeaway for mod work: clout is mostly an *emergent* readout of demographics + laws + leader. Direct clout modifiers are rare and usually mod-side; lifting clout durably means lifting the underlying attraction inputs.

### 5.4 Approval — the soft state machine

Each IG carries an **approval** value (capped roughly ±20) that drives a five-state machine:

| State | Trigger (approval band) | Mechanical effect |
|---|---|---|
| **Angry** | well below 0 | Cannot be added to government; IF in government, do not leave but contribute to radical movements supporting them. |
| **Unhappy** | mildly below 0 | Negative trait active. |
| **Neutral** | small band around 0 | No traits active. |
| **Happy** | mildly above 0 | First positive trait active; backs no movements. |
| **Loyal** | well above 0 | Both positive traits active. |

The exact band edges have hysteresis (deactivating a trait requires moving back across a slightly inner threshold than activating it). Read `common/defines/00_defines.txt` § NPolitics for the current numerical bands when balancing.

Approval is a sum of:

- **Law-stance approval** — the IG's stances on currently-enacted laws (5-point scale, capped at ±5 contribution from this source).
- **Law-change approval** — proposing a change gives a transient approval delta scaled by step distance on the IG's stance, with per-law-group multipliers (Governance Principles, Slavery, and Land Reform amplify; Bureaucracy / Education-System / Policing dampen — verify in `common/law_groups/`). Decays over multiple years; cancelling the proposal removes the delta instantly. The approval-up-then-cancel "fake reform" tactic is real but the re-propose cooldown (§ 3.4) limits abuse.
- **Pop loyalist/radical political-strength share** — up to roughly ±15 contribution. The share read is among pops *that support this IG*; loyalists nudge approval up, radicals nudge it down. This is the tightest feedback loop in politics: SoL changes → loyalist/radical generation → IG approval → IG trait activation → economy modifiers → SoL changes.
- **Government / military wages** — small approval delta per step above or below normal wage, applied to specific IGs (Government wages → Intelligentsia and PB; Military wages → Armed Forces).
- **Powerful-opposition** — a small approval debuff if an IG is both Powerful and in Opposition.
- **Lobby appeasement** — the IG's lobby (if any) carries an appeasement value; the value flows into approval.
- **Event-driven temporary modifiers** — common, scoped to country or IG, decay-over-N-years.

### 5.5 Traits — three per IG

Every IG has **three traits**: one negative (Unhappy/Angry tiers), one first-positive (Happy), one second-positive (Loyal). The traits encode the IG's ideological character as gameplay modifiers — *Materiel Waste* and *Patriotic Fervor* for Armed Forces, *Pious Fiction* and *Be Fruitful and Multiply* for Devout, and so on (per-IG list in `common/interest_groups/` and surfaced via `/raw/InterestGroup/<id>`).

The activation rules:

- **Powerful IG**: trait magnitudes are doubled, positive AND negative. A powerful happy IG's positive trait amplifies its benefit; a powerful angry IG's negative trait similarly amplifies its drag. This is the largest *single* modifier amplifier the politics layer offers.
- **Marginalized IG**: traits **do not activate at all**. Marginalizing a problematic IG genuinely shuts off its mechanical contribution.
- **In-government but sub-marginalization-clout**: traits activate at half magnitude (the safety-net case from § 5.2).

Country-flavor traits (Brazilian *Coronelismo*, Austrian *Wiener Walzer*, Punjab *Khalsa*, French *Élan Vital*, German *Biedermänner*, Russian *Velvet Book / Obshchina*, etc.) replace the generic trait at the corresponding tier — see the long flavor table in the wiki source for the catalog.

### 5.6 Lobbies — the diplomatic-to-domestic IG channel

A **lobby** is a coalition of IGs that supports (pro-country) or opposes (anti-country) friendly diplomacy with a specific foreign country. Each lobby carries an **appeasement** value in roughly ±10. Member IGs' approval moves with the lobby's appeasement: a country pursuing diplomacy that satisfies a pro-country lobby raises member-IG approval; antagonizing it lowers approval. **An IG can sit in at most one lobby at a time.**

Lobbies are how the wider diplomacy system (`vanilla_diplomacy_reference.md` § 9.5 leverage) feeds back into domestic politics. Power-bloc leverage factors include lobby clout in the target — pro-leader lobbies boost leverage, anti-leader lobbies subtract — and the appeasement signal returns from the diplomatic outcome to IG approval. War support also reads lobby clout (`vanilla_war_reference.md` § 13).

The mod's archived `archive/political_lobbies_design.md` documents a deferred lobby-system extension; this section describes vanilla-only behavior. When mod work touches lobbies, check the archive and the live game state both.

## 6. Political parties

### 6.1 What parties are mechanically

A **political party** is an alliance of IGs that exists only in countries with voting laws. Three things change when an IG is in a party:

- **Clout-from-votes flows to the party**, then redistributes to member IGs. Unaffiliated IGs get nothing from votes. (Their pop-political-strength clout still works.)
- **Party counts as one government slot.** Adding or removing a party adds or removes *all* its member IGs at once. This is the structural reason parties exist — they trade off ideological flexibility for relief from the government-size legitimacy penalty (§ 2.3).
- **The party whip's stances count full; secondary IGs' count half** for the ideology penalty (§ 2.4). This is the largest soft mechanism for keeping legitimacy high in a multi-IG government.

**Bloc add/remove semantics.** The government cannot be reformed in a way that leaves a party split between government and opposition. If an IG marked "wants to join [Party]" is currently on the wrong side, the only legal reform action is to unify the party in either government or opposition. This produces non-obvious situations where reform is temporarily blocked until the campaign cycle resolves the affiliation.

### 6.2 The eleven archetypes

Vanilla has 11 party archetypes; any combination can exist in a country at a time, including none. Names:

- **Agrarian** — natural home: Rural Folk
- **Anarchist Society** — leader-ideology-driven (Anarchist)
- **Communist** — leader-ideology-driven (Communist / Vanguardist)
- **Conservative** — natural home: Devout, Landowners, Petite Bourgeoisie
- **Fascist** — leader-ideology-driven (Fascist / Corporatist / Integralist / Ethno-Nationalist)
- **Faith** — leader-ideology-driven (Theocrat) or natural home for Devout
- **Free Trade** — natural home: Industrialists; or Market Liberal leader
- **Liberal** — natural home: Intelligentsia
- **Patriotic** — natural home: Armed Forces
- **Radical** — leader-ideology-driven (Radical)
- **Social Democratic** — natural home: Trade Unions; or Social Democrat leader

Per-party formation prerequisites (`common/parties/`) couple to technologies (Anarchism, Socialism, Mass Propaganda, Stock Exchange, Empiricism, Labor Movement, Egalitarianism), to specific IGs being non-marginalized, and to leader ideologies. The per-party **attraction tables** (long; many additive and a handful of multiplicative modifiers per archetype) live in the wiki and `common/parties/`; this doc deliberately doesn't reproduce them — the values drift and a mod-work query against `common/parties/` is more reliable than a stale copy.

The mechanical-difference rule: **the eleven archetypes have no mechanical differences from each other** beyond their attraction logic. There is no "Liberal Party gives +X to Y"; the parties are pure clout containers whose only effect is the whip / government-slot / vote-clout machinery in § 6.1. The character of a party is entirely the IGs that comprise it.

### 6.3 Cross-election clout volatility

Each campaign start, an IG considering a new party leaves its old party first, *then* re-evaluates. The transient state — "between parties" — affects clout: while affiliated to a party that's about to disband, the IG still gets votes from the disbanding party until elections finalize, but new vote tallies redirect. **A party disbanding and reforming with the same membership produces a temporary legitimacy dip**, because vote-derived clout briefly resets. Mod content that fires events around elections needs to factor this — events that flip leader ideologies during a campaign can push IGs into "wants to join" states with multi-month consequences.

## 7. Ideologies

### 7.1 Five ideology buckets

Vanilla's ideologies fall into five categories — you'll see them attached to different scopes in the data:

- **Standard ideologies** — the default catalog (Liberal, Conservative-by-many-names, Patriotic, Plutocratic, Egalitarian, Moralist, etc.). Held by IGs as their core ideology set; held by characters as personal ideology.
- **Leader ideologies** — held only by characters; many resemble standard ideologies but with character-only suffixes (`*_leader`). The leader's ideology layered onto the IG's core ideologies is what determines the IG's law stances at any moment.
- **Movement ideologies** — held only by political movements; usually (not always) one-to-one with a standard ideology. Determines what laws the movement endorses or opposes.
- **Event ideologies** — added/removed by JE or event chains. Examples: `Feminist` and `Modern Patriarchal` (Call for Women's Suffrage JE), `Modernizer` (Populist Unrest JE in Brazil), `Elitist` (Stamp Out Monarchism JE), `Caudillismo` (Age of Caudillos JE in Latin America), `Constitutionalist` (Practical Learning event in Japan), `Technocratic` (The New Machine JE), `Utilitarian` (Imperialism of Promise JE in East India), `Military Absolutist` (To Save the Empire JE in Austria). The catalog is broader than this list — the wiki section *Event ideologies* enumerates them.
- **Flavor ideologies** — country/culture/religion-specific variants of standard ideologies (Confucian, Hindu Moralist, Orthodox Patriarchy, Pontifical, Sikh Militancy, Junker, Jeffersonian, Ilustrado, etc.). Flavor ideologies *replace* a standard ideology on the relevant IG in the right country, often with subtly different law stances (e.g. the Russian Orthodox Patriarchy has different Distribution-of-Power stances than the generic Patriarchal it replaces).

### 7.2 The 5-point stance scale

Each ideology has a stance per law on a 5-point scale: **Strongly Disapprove → Disapprove → Neutral → Approve → Strongly Approve**. This drives:

- **IG law approval** (§ 5.4) — sum of stances on enacted laws, capped at ±5 contribution.
- **Law support** for enactment (§ 3.3) — IGs in government endorsing the proposed law contribute to base success chance; IGs opposing contribute to base stall chance, with magnitude weighted by current approval state (angry opposers count 1.5×).
- **Movement activism** (§ 8.4) — movements gain or lose activism per enacted-law step relative to their movement ideology's preference, with a smaller weight for proposed-law-changes.

The stance scale is the unit of currency the system trades in; everything else in politics ultimately reduces to *whose stance counts how much, where*.

### 7.3 Leader ideology overrides core

The most important rule about ideologies in motion: **a character leading an IG layers their personal ideology on top of the IG's core ideologies, and the leader's stance takes precedence on conflicts.** A Landowners IG with a Market-Liberal leader will support free-trade reform despite Landowners typically opposing it — until the next leader-change rolls back the override.

This is the design surface for ideology-shift events: replacing a core ideology (e.g. via Stamp Out Monarchism replacing `Paternalistic` with `Elitist` for Landowners) is permanent; relying on a leader's idiosyncratic ideology is temporary and ends with leader death/exile/retirement. Events that **add** an ideology to an IG's core (Feminism research → `Feminist` for Intelligentsia and Trade Unions) are the durable lever; event-driven leader changes are the temporary one.

### 7.4 Where defaults live

Per-IG default core ideologies are in `common/ideologies/00_ig_ideologies.txt`. Per-country flavor overrides for the per-IG defaults are in the same file, keyed by country / culture / religion conditions. Always verify against the live data — the wiki extract is dated 1.12 and several flavor ideologies (Heavenly Kingdom's `God Worshipper`, Egyptian `Effendi`, Spanish `Pious`) read straight from current files but the conditions for them appearing have shifted across patches.

## 8. Political movements

### 8.1 Five categories

A **political movement** is an organized expression of pop discontent that pressures laws independent of which IGs are in government. Five categories — durable across patches:

| Category | Identity-based? | Relative formation cost |
|---|---|---|
| **Ideological** | no | low — most common type |
| **Pan-national** | no | low — keyed to nationality clusters (German, Italian, Indian, Yugoslav, Dominican) |
| **Cultural minority** | yes | high (identity-based costs more) |
| **Cultural majority** | no (the non-identity variant) | low |
| **Religious (majority/minority)** | yes | high |

Identity-based movements (cultural / religious) are pricier to form because they're keyed to specific culture / religion identity in the country; ideological and pan-national movements are pop-attitude-driven and form more freely. Per-movement triggers and disband conditions are in `common/political_movements/`; the wiki source enumerates ~30 movement types across the five categories.

### 8.2 Lifecycle: formation, support, disband

Movements have a periodic chance to form, modulated by the support they would have at formation time (more support → higher formation chance) and damped by the count of *already-active* movements (the chance is divided down each time another movement is in play). A movement needs at least a small floor of starting support to form at all; below the floor, the chance is zero.

Once formed, a movement persists for at least a year before any disband-from-low-support check applies. After year 1, a base monthly disband chance applies (small) but is divided by a function of current support — high-support movements are very sticky. Revolutionary movements **never** auto-disband; the only way out is to defeat the revolution or accommodate the demanded law.

Some movements have additional disband conditions tied to the law they advocate: an Abolitionist movement disbands when slavery is banned; a Modernization movement disbands when all of its trigger laws have been replaced; a Bonapartist/Legitimist/Orleanist movement disbands when the country has stamped out monarchy. Read `common/political_movements/` per movement.

### 8.3 Support — the three-thirds rule

A movement's **support** value is the sum of three equally-weighted contributions:

- **⅓** from the percentage of the country's *population* that supports the movement.
- **⅓** from the percentage of the country's *military personnel* that supports the movement.
- **⅓** from raw *political strength* of supporting pops.

This is the structural reason a movement supported by a small but politically-active urban population can match a movement supported by many disenfranchised peasants — the political-strength third compensates for the pop third. It's also why a movement that captures military personnel (especially Officers, with their high political-strength multiplier) carries far more weight than a movement with only civilian support: the military third counts strongly in two of the three buckets.

### 8.4 Activism — the four-tier behavioral state

Activism is the movement's "intensity" gauge, separate from support. Four named behavioral states by activism band:

- **Below 25 ("passive")**: the movement does not influence law enactment chances at all — neither boosting (when it endorses) nor stalling (when it opposes). It's still visible in the UI; it's just inert.
- **25–49 ("active, non-passive")**: contributes its support to base success or stall chance for laws it has stances on; can support law enactment in an Illegitimate government (the only override).
- **50+ ("obstinate")**: same as above, plus contributes per-state **obstinance** in cultural/religious/pan-national categories (§ 8.6) and starts radicalizing pops monthly.
- **75+ ("revolutionary")**: starts a revolution — see § 8.5.

Activism changes by 1% per week towards a target value, computed from the movement's stances on enacted laws (each enacted law contributes ±, scaled by stance step), recently-enacted laws (a transient ±25 multiplier), supporting-pop loyalist/radical share (radicals heavy positive, loyalists heavy negative). The non-obvious mechanic: **while a law the movement has a stance on is being enacted, its activism cannot drop below 25**. This is why a movement gone passive can suddenly re-mobilize the moment a relevant law begins enactment — even if the enactor is the movement's *opponent*.

Starting or cancelling a relevant law enactment **immediately applies half the new activism delta**; the rest ticks in over time.

### 8.5 Revolution — civil war from inside

A **revolutionary movement** (≥75 activism) starts organizing toward a civil war. The progress is a 0–100% bar that ticks toward the movement's *radicalism* value at periodic checkpoints (every ~8 weeks); checkpoint events can nudge progress. A movement with low radicalism never reaches 100% on its own — events have to push it over.

When progress hits 100%, the engine creates a **revolutionary country** (cloned from the original — same primary cultures, religion, technologies, and laws, *plus* the movement's preferred law and up to two more laws favored by the supporting IGs) and starts a **revolution diplomatic play**. Two open-faced choices:

- The player can switch sides during the opening-moves phase to play the revolution.
- Other countries can join the play and select sides as in any diplomatic play.

State selection for the revolutionary country: the engine picks a fraction of states proportional to 1.5× the movement's support, capped at 75% of total states. Within that fraction, the engine biases toward states with high local clout for the supporting IGs and toward state adjacency (avoiding patchwork). All characters affiliated with the revolutionary IGs switch country.

**Civil war end state**: half of all radicals neutralize on civil war start; further fractions normalize on victor identity at the end of the play (50% on the victor's pops, additional 25% on the loser's). Losing IGs eat a steep, multi-year political-strength penalty (the durable cost of having backed the wrong side).

### 8.6 Obstinance — the politics → state crossloop

When a **cultural / religious / pan-national** movement reaches the obstinate (50+ activism) tier, it starts contributing per-state **obstinance** in states where its supporting pops live. Obstinance is a state-level modifier that accumulates from the workforce share supporting obstinate movements; it caps at a moderate ceiling.

What obstinance does to the state: linear scaling penalties to tax collection, assimilation, conversion, conscript supply, and institution effectiveness. Foreign powers can also bump obstinance via the diplomatic *Support Separatism* action — this is the fully-qualified path from foreign-policy meddling to internal state-level dysfunction.

This is one of the more cross-system effects: politics-driven activism feeds state economics directly through obstinance. Mod content touching state penalties or per-state taxation needs to consider whether obstinance is or isn't a contributor.

### 8.7 Bolster and suppress

A movement can be **bolstered** or **suppressed** — both spend authority and run continuously while active. Bolster increases pop attraction to the movement (ramps support up over time); suppress decreases it. Whether either is available depends on the country having a non-zero *bolster* or *suppress impact* — Free Speech laws and the Home Affairs institution gate the impact value, so a country with `Protected Speech` cannot suppress, and a country with `Outlawed Dissent` has the highest available impact.

The authority cost for bolster/suppress is constant while active; the pop-attraction effect compounds over time. This is the design knob for governments to actively shape the movement landscape rather than only react to it.

## 9. Characters

### 9.1 Six roles

Characters are named individuals tied to a country and an IG. Six roles, mostly mutually-exclusive but with a few overlaps allowed (commanders + politicians is the common one):

- **Ruler** — head of state. Authority bonus = +1 per popularity point; ideology adds ±5%/step support to law enactment for proposed changes; trait set affects the country broadly.
- **Heir** — successor in monarchies. Generated daily after the ruler reaches age 20 if absent.
- **IG Leader** — every IG has exactly one. Ideology layers on IG core (§ 7.3); traits affect IG attraction and political strength; popularity affects IG attraction.
- **Commander (General / Admiral)** — leads formations. Trait set primarily affects military, but commander's IG gains political strength per rank, and commanders may **back a revolution** with their formations rather than the government if their IG is part of the revolutionary movement.
- **Executive** — leads a company. Popularity adds to the company's prosperity target; traits affect company-owned buildings; the executive's IG gains political strength scaled by total company-owned building levels.
- **Magnate** — wealthy character tied to a specific holding (Manor House or Financial District). Prominence scales with the holding's revenue relative to GDP; the magnate's IG gains political strength via prominence.
- **Agitator** — supports a political movement. Adds a flat-plus-popularity-scaled contribution to movement pop attraction; contribution is further scaled by literacy and IG membership %.

Rulers, heirs, and IG leaders are collectively *politicians*. A male ruler in a monarchy or dictatorship can simultaneously be a general (the *Grant Command* interaction enables this).

### 9.2 Popularity and prominence

**Popularity** is the political-temperature gauge in [-100, +100]. It comes mainly from traits and is consumed differently per role:

- **Ruler**: 1:1 into Authority (+50 popularity = +50 Authority).
- **IG Leader**: 0.25%-per-point into IG attraction; 0.05%-per-point into party momentum during campaigns.
- **Agitator**: 0.15%-per-point into movement attraction.
- **Executive**: 0.2-per-point into company prosperity target.
- **Commander**: gates *Popular Commander* (≥10) and *Celebrity Commander* (≥30) traits; can swing temporarily from battle outcomes.

**Prominence** is in [0, 100], with **rulers always at 100**. A character above the *Significant* threshold contributes scaling political strength to their IG, capping at a defined share of IG strength at full prominence. Magnates get prominence from their holding's revenue scaled relative to GDP (so politically-active oligarchs *do* require both wealth and economic presence — wealth alone outside a Manor House / Financial District doesn't move politics).

### 9.3 Lifespan and the death pulse

Average life expectancy is ~75 years; **character health** is in [0%, 200%] with a 100% baseline, modulated by traits and modifiers, and is the main longevity input.

Two non-natural-death paths matter for mod work:

- **Annual pulse**: a 50% chance per year to attempt to kill a *random* IG leader (cannot target the ruler, heir, or otherwise immune characters; cannot target the same IG within ~10 years). A 20% chance per year to kill an agitator (cooldown ~5 years), and a 20% chance per year to kill an executive (cooldown ~7 years; never historical executives).
- **Event-driven death** — many JE/event chains kill named characters. Several character interactions (Arrange Accident, Imprison Agitator) carry death rolls.

The pulse is the primary engine for IG-leader churn — ideology-shift events that hinge on a leader's specific ideology have a finite half-life, set by this pulse.

### 9.4 Generated character IG affiliation

For generated rulers/heirs (in hereditary governments), agitators, executives, magnates, and commanders, the IG affiliation is **rolled with weights**. The structural rule: per-IG base weight × clout-shape multipliers (marginalized ×0.1, powerful ×2). The per-IG base weight differs by role (Armed Forces is heavily weighted for commanders and rulers under autocracy laws; Trade Unions is weak for rulers but normal for agitators; Devout shifts with State Religion / State Atheism; Industrialists requires Currency Standards research before ever being affiliated).

This means clout shifts ripple into character generation: a marginalized IG slowly stops generating new characters of all roles, which over time atrophies its ideology pool, which deepens the marginalization. Recovering a marginalized IG is harder than the clout numbers suggest because the character flywheel has spun down.

### 9.5 Trait categories

**Personality traits** persist for life; one is assigned at character generation (or replaces *Child* at age 16) and a second can be acquired with experience. Examples: Direct, Persistent, Cautious, Arrogant, Bigoted, Reckless, Tactful, Ambitious, Imperious, Wrathful, Cruel, Meticulous, Charismatic, Brave, Innovative, Pious, Aesthete, Honorable.

**Condition traits** are usually negative, acquired during life (often via events at age 26+). Cancer, Tuberculosis, Wounded → Scarred, Senile, Syphilis, Shell Shock, Psychological Affliction, Alcoholic, Opium/Cocaine Addict, Kidney Stones, Sickly. War Criminal and Beetle Eared are event-only.

**Skill traits** are generally positive and level up over time. Commander-only families: Artillery / Defensive / Offensive / Naval Commander (each with three tiers); Convoy Raider; Stalwart Defender → Trench Rat → Defense in Depth Specialist (tech-gated); Surveyor; Pillager; Woodland / Open Terrain / Mountain Combat Expert; Dockyard Organizer. Multi-role families: Diplomat tiers (any role), Political Operator tiers (politicians), Inspirational Orator → Demagogue → Firebrand (any), Basic → Experienced → Expert Entrepreneur, Master Bureaucrat, Engineer, Erudite, Literary, Bandit / Social Bandit, Elder, Explorer, Colonial Administrator tiers (rulers).

**Unique traits** are tied to historical figures: President Pedro (Brazil), Napoleon of the Americas (Solano López), El Excelentísimo (Carlos López), Tsar-Liberator (Aleksandr II option), German Unifier (any unifier of Germany), Restitutor Orbis (French dynasty cement), The Man from the River Lena (Lenin), This Glorious Endeavor (John Brown), Professional Revolutionary (Blanqui), Reactionary Icon (Maurras), Napoleonic Return (Louis-Napoleon), Popular Radical (Mazzini), Spirit of San Francisco (Joshua Norton), Nightingale Pledge (Florence Nightingale), Général Revanche (Boulanger), Passionate Theorist (Sorel), Agent of the Sovereign (Lassalle), Curly-Haired Orpheuse (Luís Gama), Untamed Revolutionary (Rosa Luxemburg).

**Colonial Administrator traits** apply only to the appointed heads of *Colonial Administration* subjects (Influential Planter, Local Appointee, Experienced Extractor, Prominent Businessman, Military Governor).

The full trait list (well over 100 entries) lives in `common/character_traits/`. Look up specific traits via `/raw/CharacterTrait/<id>` or grep the folder.

### 9.6 Character interactions

A medium-length list of interactions (`common/character_interactions/`) lets players act on individual characters. Most carry a 5- or 2.5- year **per-country** cooldown — not per-character — which is a frequent surprise.

Interactions worth knowing for mod design (full list in the wiki source and the file):

- **Exile Dissident** (politician/agitator) — converts character to agitator, exiles, radicalizes a fraction of their IG; if exiling an IG leader, the IG eats a 5-year decaying leadership penalty.
- **Arrange Accident** (politician/agitator/commander) — gated on `Secret Police` law; carries a 25% kill chance, 50% nothing, 25% backlash (radicals + a multi-year movement modifier).
- **Invite Exile / Repatriate Agitator** — diplomatic-political joins, generates catalysts.
- **Imprison Agitator** — Pivot of Empire DLC; conditional on the country not having `Guaranteed Liberties`.
- **Grant Leadership** — Voice of the People DLC; promotes an agitator to IG leader if alignment conditions hold.
- **Abdicate the Throne / Resign from Office** — VotP DLC; convoluted preconditions tied to age, popularity, IG state, and ruler trait set.

Mod content should not reach for new character interactions casually — the cooldown machinery, role-availability check, and trait/popularity preconditions are tightly coupled to engine-side UX expectations. Add interactions only when an existing one isn't expressively close enough.

## 10. Institutions

### 10.1 Seven institutions, set by laws

An **institution** is a level-1-to-5 country-scope investment that activates only when a specific law enables it. Seven institutions in vanilla — the law group that gates each is the institution's "establishing" law:

| Institution | Established by | Base effect (level 1; scales linearly with level) |
|---|---|---|
| **Home Affairs** | Internal Security | −% revolution / secession progression speed |
| **Education** | Education System | (per-law variance: Religious / Public / Private Schools) |
| **Health System** | Health System | (per-law variance: Charity / Private / Public Insurance) |
| **Workplace Safety Office** | Labor Rights | −% dangerous working conditions |
| **Colonial Affairs** | Colonization | +% colonial growth |
| **Law Enforcement** | Policing | −% state penalties from turmoil |
| **Social Security** | Welfare | +% welfare payments, +% food security |

The level applies linearly to both effect and bureaucracy cost: a level-3 institution has 3× the effect *and* 3× the bureaucracy spend of level 1. **Effects only apply in incorporated states** — uninc states neither pay institution bureaucracy nor receive institution effects.

Some laws inside the establishing law group raise the **maximum level** the institution can reach (`Public Schools` allows 5; `Religious Schools` caps at 3); other laws and *technologies* inside the group also raise the cap. The full per-law per-institution effect table is in `common/institutions/00_institutions.txt` — including the per-establishing-law extra effects (e.g. Home Affairs with `National Guard` adds conscription + morale reduction *per level* on top of the base revolution-progress effect).

Power-bloc principles can also modify time-to-change and bureaucracy cost for specific institutions.

### 10.2 Level-change semantics

Increasing or decreasing a level **takes ~1 year per level**, during which:

- The bureaucracy cost ramps proportionally (so the player pays incrementally, not all-at-once at completion).
- The effect does **not** apply until the level is fully implemented at year-end.
- If the country goes into a bureaucracy deficit during the change, the level-up pauses until bureaucracy recovers.

A few non-obvious consequences:

- Institutions that reduce dynamic state values (turmoil, revolution progress) have a 1-year delay before they bite.
- Institution levels do not pause during war — bureaucracy spend continues, level continues to build, but the eventual benefit may arrive after the war is over. This is a hidden cost of opportunistic institution-stacking before a war.

## 11. Decrees

### 11.1 What a decree is

A **decree** is a per-state effect costing a flat reservation of country-scope authority while active. Multi-state countries can run different decrees in different states; one decree per state slot at a time, except three industry-encouragement decrees (*Encourage Agricultural*, *Encourage Manufacturing*, *Encourage Resource*) are mutually exclusive within a country.

Most decrees require a specific technology to be researched. The vanilla list (eleven entries):

- **Emergency Relief** — temporary food-security boost (cheaper than the others — half the standard authority cost).
- **Encourage Agricultural Industry** / **Manufacturing Industry** / **Resource Industry** — sector-specific throughput / migration boosters; mutually exclusive within a country.
- **Enlistment Efforts** — military recruitment.
- **Establish Missions** — religious conversion.
- **Greener Grass Campaign** — migration attraction.
- **Promote National Values** — assimilation and conversion accelerator.
- **Promote Social Mobility** — education access boost.
- **Road Maintenance** — infrastructure boost (most useful as a temporary devastation/turmoil offset, less efficient than rail long-term).
- **Violent Suppression** — turmoil reduction at a +mortality-per-turmoil cost.

The exact effects vary patch-to-patch; read `common/decrees/00_decree.txt` when modeling.

### 11.2 Authority is the primary lever

Decrees, **bolster/suppress** of movements, **consumption taxes**, **monopolies**, and **excess corporate charters** all draw on the same pool. Authority is finite and recharges only when the country's law-set produces it (Authority production is detailed in `vanilla_economy_reference.md` § 11.2). The strategic frame:

- **Few-state countries** (≤5 states) get high decree-per-state coverage; decrees are very efficient there.
- **Many-state countries** find consumption taxes (revenue-positive) more efficient than decrees (revenue-neutral).
- **Liberalizing legal regimes** (e.g. reducing Free Speech restrictions) cut Authority production — many decrees become unaffordable later in a campaign as laws modernize. Modeling decree-driven mod systems for late-game players means anticipating this Authority compression.

The ruler-trait reductions (*Ambitious* −% decree cost, *Imperious* −% decree cost) are durable but capped against a floor — decree cost cannot drop below 10% of base regardless of stacked modifiers.

## 12. The NPolitics defines block

`common/defines/00_defines.txt § NPolitics` is the canonical home for politics-related tunables. The block is dense; the worth-knowing-it-exists groups:

- **Movement support floors and decay**: minimum support to create, support split between population/military/wealth fractions, monthly radical-attraction thresholds.
- **Movement radicalism factors**: per-percentage radical rate from enactment, from active laws, from supporting radicals, from supporting loyalists.
- **IG approval thresholds**: the band edges for Angry / Unhappy / Neutral / Happy / Loyal; per-source approval contributions (loyalist / radical / movement / lobby / wages).
- **IG influence on movements**: maximum number of movements an IG can simultaneously back (default 3); stickiness factor.
- **Character pulse cadence**: leader-prominence-and-role factor for how leader ideology flows into movement pressure.
- **Leadership generation**: factors for character ideology rolls; chance for a commander to become an IG leader.

When a balance question turns on "what *is* the cost / threshold / coefficient", the file is the source of truth. This doc deliberately doesn't reproduce values from there — they drift, and the file is searchable.

## 13. Cross-references

- **Authority production / Bureaucracy / Influence**: `vanilla_economy_reference.md` § 11. Decrees, suppress, consumption taxes, and monopolies all draw on the production side.
- **Power blocs, leverage, lobby clout in leverage math, subjects, Support Regime pact**: `vanilla_diplomacy_reference.md` § 9, § 10.
- **War support exhaustion (radicals → exhaustion; lobby clout → exhaustion)**: `vanilla_war_reference.md` § 13.
- **Treaty Law Commitment article**: `vanilla/treaty_articles_reference.md`.
- **Auto-generated full law list**: `docs/engine/laws.txt`.
- **Engine triggers and effects relevant to politics**: `docs/engine/vic3_triggers_effects_reference.md`, `docs/engine/triggers_summary.txt`, `docs/engine/effects_summary.txt`.
- **On-action hooks for politics**: `docs/engine/on_actions_summary.txt`. Particularly: `on_law_enactment_started`, `on_law_checkpoint_*`, the entire `00_on_actions_election.txt` file in vanilla.
- **Modifier validation gotchas (politics-touching modifiers must register dynamic patterns)**: `docs/guides/scripting_best_practices.md`.
- **On-disk vanilla data** — primary references for shape:
  - `common/laws/`, `common/law_groups/`
  - `common/interest_groups/`, `common/ideologies/`
  - `common/parties/`, `common/government_types/`
  - `common/political_movements/`, `common/political_movement_categories/`, `common/political_lobbies/`
  - `common/character_traits/`, `common/character_interactions/`
  - `common/institutions/`, `common/decrees/`
  - `common/defines/00_defines.txt § NPolitics`
- **Mod-side deferred lobby redesign**: `docs/archive/political_lobbies_design.md` — held for re-attempt after a new-game-crash regression. The vanilla lobby behavior in § 5.6 above is the current truth; the archive describes a design that was reverted.

## 14. Open questions

A short list of mechanics where the data files alone don't establish the answer cleanly. When these are answered, fold the answer into the relevant body section and remove the bullet.

- **Approval-from-loyalist/radical contribution scope.** The wiki says "each ~6% loyalist = +1, each ~6% radical = −1, capped ~±15", but the contribution is normalized over *pops supporting the IG*. The exact denominator (just supporting pops, or all clout-relevant pops?) isn't explicit; verify against `common/defines/`.
- **Movement-formation random factor.** The wiki has "base X% chance per period", with the X concealed. Likely lives under `MOVEMENT_FORMATION_*` defines; cross-check.
- **Election momentum pop-leader-popularity coefficient.** The 0.05% per popularity figure for party momentum is a stable mechanic *shape*, but the exact rate has shifted across patches. Re-verify on the next vanilla bump.
- **Powerful IG cluster stability.** Whether two simultaneously-Powerful IGs of opposing ideology produce hysteresis on the legitimacy-vs-clout calculation isn't documented; suspect there's a per-frame recompute that doesn't smooth, but the user has flagged this for empirical follow-up.

## 15. Maintenance protocol

This doc captures vanilla concepts at a point in time. To keep it useful:

1. **On every vanilla patch:** the runbook in `docs/guides/vanilla_patch_runbook.md` instructs whoever performs the migration to revisit this file. Update the version banner at the top, and edit any section where 1.x semantics changed (new IG, new movement category, restructured laws, new institution, ideology rework). Don't fork a separate "1.14 politics" doc — overwrite.
2. **Post-1.10 IG-rework drift.** § 5 carries the largest patch-drift risk because the wiki source for that article was 1.8. On any vanilla bump, re-cross-check § 5 (interest-group attraction and approval mechanics) against the live data; minor wording shifts in attraction modifiers are common.
3. **On discovering a new mechanic mid-development:** when an agent learns something generally applicable about how vanilla politics works (a non-obvious ideology-shift trigger, a hidden IG attraction conditional, a new character-interaction quirk), add it here in the relevant section. Keep additions short — one paragraph or a bullet. The bar from `CLAUDE.md` § "Recording lessons learned" applies: would the next agent hit the same gap from scratch?
4. **On answering an Open Question:** when § 14 gets answered, fold the answer into the relevant body section and delete the bullet.
5. **Don't duplicate.** Modifier validation rules, scope chain quirks, and engine-syntax gotchas belong in `docs/guides/scripting_best_practices.md`. This file is *concepts*, not *syntax*.
6. **Numbers when they're mechanism, not when they're balance.** Range bounds (legitimacy 0–100, popularity ±100), tier names, and structural ratios stay; specific defines and per-entry values do not.
7. **Don't reproduce per-IG / per-movement / per-party / per-trait full tables** even when the wiki source has them. Pointer-to-`common/<folder>/` is more durable; rebuilding the tables here would be ~2,000 lines of drift-prone material.
