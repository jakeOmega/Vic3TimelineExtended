# Vanilla Pops Reference (Victoria 3)

A primer on how the **base game's** pop system works at the *individual* and *cultural* layers — how pops are defined, how culture and religion shape acceptance and assimilation, how the social hierarchies (Base / British Indian Caste / Edo) sort professions into strata, how qualifications gate profession transitions, and how literacy / education access drift over time. The country-aggregate economic side (wages, SoL, employment, migration, IP) lives in `vanilla_economy_reference.md`; the political side (IG attraction, approval, movements) in `vanilla_politics_reference.md`. This doc is the per-pop / per-culture / per-religion / per-profession layer.

> **Last verified against vanilla:** 1.13.5 (Hotfix to "The Great Wave"). Wiki source dates this article 1.9 for the headline pop article, 1.10 for Profession, 1.12 for Standard of Living's loyalist/radicalism subsection, 1.10 for Migration. Any per-profession qualification factor or per-stratum expected-SoL number quoted from the wiki should be cross-checked against `common/pop_types/`, `common/social_hierarchies/`, and `common/defines/`.
>
> **This doc captures concepts, not enumerated tables.** The full per-profession qualification matrices, per-acceptance-status assimilation rates, and per-needs-category goods substitution lists drift each patch and live in `common/pop_types/`, `common/buy_packages/`, `common/needs/`, `common/strata/`. Read this doc for shape; query files for values.

## 1. What a pop is

A **pop** is a group of individuals sharing five characteristics:

- **Culture**
- **Religion**
- **Profession**
- **Workplace** (the building, or the state if unemployed)
- **State of residence**

Each unique combination is its own pop. There are tens of thousands of pops in any given save. Pops have variable size — from handfuls to millions.

When individuals change pop (assimilation, religious conversion, profession change, workplace change), they take a proportional share of the source pop's secondary characteristics with them: wealth, literacy, loyalist/radical share, qualifications. This is the engine's way of preserving "soft" aggregate state through the constant pop-churn of an active simulation.

### 1.1 The defining characteristics in detail

**Culture.** Cultures have *traits* (heritage / language) used by acceptance laws to determine status; cultures may have *obsessions* (good preferences that double demand weight on those goods); cultures have *homelands* — state regions they consider native, used for assimilation, mass migration, formable-country requirements, and several other state-status interactions.

**Religion.** Religions have *taboos* (good preferences that halve demand weight). Taboos are determined by the **default religion of the pop's culture**, not the pop's actual religion — converting individually doesn't shed culture-tied taboos (a Catholic Punjabi pop carries the same taboos as a Sikh Punjabi pop). Each country has a *state religion* with full acceptance under the right Church-and-State law.

**Profession.** The job. There are 15 professions plus an "unemployed" status; each profession has a base SoL, a wage multiplier, a base investment-pool contribution, and a bag of special rules (some ignore proportional hiring, some don't pay wages outside government buildings, peasants' SoL-change loyalty effects are massively dampened, slaves can't migrate or change profession, etc.). See § 4.

**Workplace.** Either a specific building or "the state" (unemployment). When a pop's workplace closes or shrinks (building destroyed, profession cut by PM change), the pop migrates internally to a new workplace, becomes unemployed if no fit, or — for peasants — re-enters the subsistence buffer.

## 2. Acceptance — culture × religion × law

A pop's **acceptance status** is computed from country *Citizenship* and *Church and State* laws, the pop's culture relative to the country's primary cultures, and the pop's religion relative to the country's state religion. The status determines wages, political strength, profession access, and migration eligibility.

The acceptance status tiers (low → high) are stable across patches:

- **Violent Hostility** — typically blocks profession access broadly; assimilation is blocked.
- **Cultural Erasure** — heavy penalties; assimilation possible, eased.
- **Open Prejudice** — moderate penalties; assimilation possible, eased.
- **Second-class Citizen** — light penalties.
- **Full Acceptance** — no penalties.

Each Citizenship law (`Ethnostate`, `National Supremacy`, `Cultural Exclusion`, `Multiculturalism`, `Racial Segregation`, `Subjecthood`) defines which (heritage / language) trait combinations get which status. The exact mapping is in `common/laws/00_citizenship.txt` and adjacent. Church-and-State law similarly affects religious acceptance.

### 2.1 What acceptance gates

Most-impactful gates:

- **Wage multiplier** — discriminated pops are paid less under several laws.
- **Political strength** — discriminated pops generate less clout per individual under most regimes.
- **Profession access** — many professions require a minimum acceptance status (Officers usually require Second-class+, Bureaucrats require Second-class+ for full effectiveness, etc.).
- **Migration** — `Migration Controls` requires at least Second-class acceptance for incoming migrants (60+ raw acceptance value); `Closed Borders` allows none; `No Migration Controls` allows any.
- **Voting** — Citizenship law determines which acceptance statuses can vote at all and may further weight votes per status.
- **Birth rate / mortality** — discriminated pops can take radicalism penalties that compound with low SoL.

## 3. Culture & religion churn — assimilation, conversion, obsessions

### 3.1 Assimilation

Pops can *assimilate* to a more-accepted culture if it would raise their status. Two structural rules:

- Assimilation is **blocked for both Violent Hostility tiers** — radicals from extreme discrimination cannot assimilate out.
- Assimilation requires a **more-accepted culture present in the state** — pops can only assimilate to cultures that already exist in the same state. (This is one of several reasons cultural communities matter for migration; § 6 of `vanilla_states_reference.md`.)

Base assimilation rate is a small per-month percentage; modifiers stack additively:

- *Promote National Values* decree adds a flat boost.
- *Public Schools* law adds per-Education-level boost (incorporated states only).
- *Cultural Erasure* and *Open Prejudice* statuses add small assimilation boosts (counterintuitively — extreme discrimination accelerates capitulation, mild acceptance leaves cultures intact).
- Pops with radicals assimilate slower.

### 3.2 Religious conversion

Pops may *convert* to a higher-acceptance religion; same modifier structure as assimilation (state-religion, Religious Schools, Promote National Values), with:

- *Religious Schools* law adds per-Education-level boost.
- *Religious Convocation* power-bloc statue adds a flat boost.
- **Conversion is reduced ≈ −90% in unincorporated states** (the major asymmetry vs. assimilation).
- Pops with radicals convert slower.

Religion changes do **not** change the pop's underlying culture, so taboos (which follow culture's default religion) persist. A Sunni Punjabi pop converting to Sikhism doesn't shed the cultural-default-religion taboo profile.

### 3.3 Obsessions and taboos

Cultures can hold up to **three obsessions** at once. Obsessions double the demand weight for a specific good in pops of that culture. Some cultures start with obsessions; new obsessions can be gained mid-game via events / culture content. Religions hold **taboos** that halve the demand weight; taboos are tied to the pop's culture's *default* religion, not to its current religion — they don't follow individual conversion.

Both shape pop demand on the local market and indirectly shape what's profitable to produce in regions populated by that culture. Wine producers in obsessed-on-wine cultures see structurally higher local prices, making the industry there more durable.

## 4. The 15 professions

Professions sit in the lowest layer of the pop hierarchy and dominate IG attraction (see `vanilla_politics_reference.md` § 5.3) and pop wealth/SoL. The full list with structural roles:

| Profession | Stratum (Base) | Workforce ratio / wage / IP / specials |
|---|---|---|
| **Aristocrats** | Upper | Reduced (20%) workforce; high wage; baseline IP contribution; **not paid wages outside government-funded buildings** |
| **Capitalists** | Upper | Reduced (20%) workforce; high wage; high IP; **not paid wages outside gov-funded buildings** |
| **Academics** | Middle | High wage; +50% education access |
| **Bureaucrats** | Middle | High wage; +50% education access; baseline IP |
| **Clergymen** | Middle | High wage; +50% education access; baseline IP |
| **Engineers** | Middle | High wage; +25% education access; baseline IP |
| **Officers** | Middle | High wage; **+200% inherent political power**; ignores employment proportionality |
| **Shopkeepers** | Middle | High wage; baseline IP |
| **Farmers** | Middle | Mid wage; baseline IP |
| **Clerks** | Lower | Low-mid wage; +25% education access |
| **Machinists** | Lower | Low-mid wage; baseline IP |
| **Servicemen** | Lower | Low-mid wage; **+50% inherent political power**; ignores employment proportionality; can always be hired |
| **Laborers** | Lower | Low wage; default profession; **can always be hired**; no qualifications |
| **Peasants** | Lower | Very low wage; **SoL-change loyalty effects multiplied by ~×0.01** (peasants barely loyalty-react); consumption reduced; **cannot become unemployed** (revert to Laborers); ignores proportionality |
| **Slaves** | Lower | Zero wage; **needs purchased by workplace**; **cannot change profession**; **cannot migrate**; 50% workforce ratio |

The non-obvious specials matter:

- **Officers and Servicemen ignore employment proportionality** — buildings can hire them out of ratio, and military buildings need this because conscription / mobilization waves don't respect proportional hiring.
- **Peasants can never go unemployed** — they revert to Laborers if they would. This is why "Laborer surplus" appears in industrializing economies: peasants pushed off subsistence farms become Laborers, not unemployed pops.
- **Slaves can't migrate at all**, even under No Migration Controls. The `Slave Trade` law adds a separate import path that bypasses Closed Borders.
- **Aristocrats and Capitalists not paid wages outside government buildings** — they live off ownership dividends. This is why Aristocrats in a serf-dominated economy can have very high wealth: they're the recipient of subsistence-farm dividends.

Per-profession base SoL, wage multiplier, dependent income coefficient, and IP-contribution % live in `common/pop_types/`. Don't hardcode them in script or balance docs — they drift.

## 5. Social hierarchies — three vanilla systems

A **social hierarchy** maps professions to **social classes**, then social classes to **strata**. Modifiers can target any of those three levels (profession / class / stratum).

There are three vanilla hierarchies:

### 5.1 Base Hierarchy — default for most countries

- **Lower stratum**: Clerks, Laborers, Machinists, Peasants, Servicemen, Slaves.
- **Middle stratum**: Academics, Bureaucrats, Clergymen, Engineers, Farmers, Officers, Shopkeepers.
- **Upper stratum**: Aristocrats, Capitalists.

This is the partition the game's strata-targeted modifiers (welfare, expected-SoL by stratum, taxation by stratum) read by default.

### 5.2 British Indian Caste System

Used by East India and Princely States at start. Hindu pops with South Asian Heritage culture use a different partition:

- **Lower (Dalit)**: Slaves.
- **Lower (Shudras)**: Laborers, Machinists, Servicemen, Peasants.
- **Middle (Vaishyas)**: Clerks, Farmers, Shopkeepers.
- **Middle (Kshatriyas)**: Aristocrats, Capitalists, Engineers, Officers.
- **Upper (Brahmins)**: Academics, Bureaucrats, Clergymen.

Critical: **Aristocrats and Capitalists sit in the Middle stratum** under this hierarchy, not Upper. Welfare and tax-bracket logic that targets "upper stratum" lands on Brahmin academics/bureaucrats/clergy, not on the wealthy industrial class. This is occasionally a balance footgun for mod content that assumes Capitalists are always upper-stratum.

A country uses this hierarchy if it has a South Asian Heritage primary culture, ≥50% Hindu pops, **and** is a subject of Great Britain. Loses it if ≤10% Hindu pops. Adds a unique law group: **Caste Hegemony** (`Caste System Enforced` / `Caste System Codified` / `Caste Not Enforced` / `Affirmative Action`).

Non-Hindu / non-South-Asian-Heritage pops in the same country use the Base Hierarchy.

### 5.3 Edo Status System

Used by Japan at start (replaced by Base Hierarchy after the Meiji Restoration JE):

- **Lower (Eta-Hinin)**: Slaves.
- **Lower (Chōnin)**: Capitalists, Clerks, Engineers, Machinists, Shopkeepers.
- **Lower (Hyakusho)**: Farmers, Laborers, Peasants.
- **Middle (Jisha)**: Clergymen.
- **Middle (Lower Samurai)**: Bureaucrats, Servicemen.
- **Upper (Upper Samurai)**: Academics, Aristocrats, Officers.

Note again: **Capitalists are Lower stratum** here. The Edo system's economic implication is severe — the merchant class that drives industrial transition is structurally low-status, which is exactly the historical tension the system models.

## 6. Wealth → SoL → loyalty/radicalism (the inner loop)

The dominant feedback loop in Vic3:

1. **Wealth** accumulates when income > expenses (specifically, > 102% of next buy-package cost) and decays when income < ≈ 98% of expenses. Speeds: 0.2× difference for accumulation, 0.1× difference for decay (asymmetric — wealth accumulates faster than it loses).
2. **SoL** equals wealth absent modifiers; modifiers from events, journal entries, ruler trait (Cruel ruler = −1 country-wide), pollution, the Health-System institution, and power-bloc principles can shift SoL away from wealth.
3. **Each SoL change** generates loyalists (rising) or radicals (falling). Base ≈ 3% of the pop converts; modifiers from laws / institutions / events / character traits stack.
4. **Pops below their expected SoL** radicalize over time at a rate scaled by the gap (capped per-level). Expected SoL has a base by stratum (Lower / Middle / Upper at increasing values) plus a literacy-driven adder that itself scales with researched society techs (Egalitarianism, Labor Movement, Socialism, Political Agitation, Mass Propaganda). Late-game high-literacy populations have substantially higher expected SoL than their early-game equivalents.

The asymmetry that mod work needs to internalize: **dropping SoL produces radicals heavily; raising SoL produces loyalists comparatively weakly**. Most modifiers are applied to *one direction* (a +loyalist law adds loyalists on rising SoL but does nothing on falling SoL), so the net effect of an unstable economy is radical-weighted. Stability is the cheap path to loyalist majorities.

The **first few years** of a campaign apply a scaled-down loyalist/radical generation rate (the "grace period" set by the game-rule selector) so that early-game economic shocks don't immediately spawn revolutions.

Peasants are special-cased: their `sol_change_impact` override drops the loyalist/radical generation by ~×0.01. Subsistence-farm pops are politically inert until they leave subsistence; this is one of the durable mechanisms by which industrialization politicizes a population.

## 7. Birth rate, mortality, demographic transition

Birth and mortality both move with SoL in a curve roughly modeling demographic transition:

- **Below SoL 5**: mortality elevated to model starvation.
- **SoL 5 → 15**: mortality drops sharply.
- **SoL 10 → 25**: birth rates drop sharply.
- **SoL 15 → 25**: mortality decline slows.
- **Above SoL 25**: floors apply (≈ 0.6% birth, 0.45% mortality).

Net pop-growth rate peaks around SoL 15 and tapers above. **The Public Health Insurance institution at level 5 can produce net population *decrease*** because the SoL bump it provides can push pops past peak-growth into the slowing band. This is a non-obvious balance interaction worth flagging when reasoning about long-run population.

Other inputs:

- **Literacy** linearly cuts birth rate (≈ −10% at 100% literacy). High-literacy pops grow slower.
- **Unemployment** in the state cuts birth rate proportionally (capped ≈ −40%).
- **Pollution** raises mortality, mitigated by Health System and `Modern Sewerage`.
- **Sparsely populated state trait** (< 5,000 pops per arable land) adds a scaling birth-rate bonus up to +50%. This is what powers frontier-state population catch-up.

## 8. Literacy and education access

### 8.1 Education access

A per-pop value representing the literacy ceiling the pop drifts toward. Sources:

- **Base**: 0.5% per wealth point.
- **Society techs**: Rationalism (+1%/wealth), Academia (+0.5%/wealth), Empiricism (+0.5%/wealth) — additive, applied per pop's wealth.
- **Profession bonuses**: Clerks / Engineers (+25% each), Academics / Bureaucrats / Clergymen (+50% each).
- **Education institution by establishing law**:
  - `Religious Schools` — flat per-level adder.
  - `Public Schools` — flat per-level adder (largest non-wealth-scaling source).
  - `Private Schools` — per-wealth per-level adder (compounds with wealth, useful for high-SoL populations).
- **Promote Social Mobility decree** — flat boost.
- **Pious Fiction IG trait** (Devout unhappy) — flat penalty.

### 8.2 Literacy drift

Each pop's literacy slowly approaches its current education access. **Above** education access, literacy decays as literate individuals die. **Below**, it grows as new individuals reach literacy via the access pipeline. This is why a sudden boost to schools doesn't immediately raise literacy — it raises *access*, and literacy chases access on a multi-year timescale.

Literacy feeds back into:

- **Innovation cap** (`vanilla_technology_reference.md` § 3.2).
- **Tech spread** (§ 4.2).
- **IG attraction** (Intelligentsia minimum 50% literacy; Devout penalty per literacy point).
- **Expected SoL** via the literacy adder.
- **Country fervor** (cultural fervor caps at 25 from high literacy).
- **Birth-rate cut** (§ 7).

## 9. Qualifications

A **qualification** is a per-pop, per-other-profession score representing how easily individuals can change to that profession. Each month, the workforce gains qualifications scaled by literacy / wealth / acceptance / current profession; qualifications can decay via death or pop-change.

Per-profession qualification factors (the formulas in `common/pop_types/<profession>.txt`) are extensive — Academics scales with literacy and wealth, Aristocrats with wealth and literacy, Engineers with literacy and wealth multiplied by current profession (×5 if Machinists, ×4 if Clerks), etc. The *shape*: qualifications use literacy + wealth as the main inputs, multiplied by acceptance gates (×0.1 for low-acceptance pops; ×0 for Peasants under Serfdom for many transitions).

Universities provide an additional country-wide qualification boost based on PM and throughput.

## 10. Workforce and dependents

By default 25% of a pop is *workforce* (employable) and 75% is *dependents* (subordinate household members; collect a small "odd-jobs" income that doesn't count for income tax). Modifiers shift the ratio:

- **Rights of Women laws** add up to +15% workforce ratio cumulatively.
- **Trade Unions' Solidarity** (loyal trait) adds +5% workforce ratio.
- **Slaves** override to 50% workforce.
- **Aristocrats / Capitalists** override to 20% workforce.

Dependents consume **half** as much as a working pop — a lower workforce-ratio pop consumes less in absolute terms. The country's average workforce ratio drifts back to the ideal (set by laws + traits) when shocks (battle casualties, pop-change cascades) push it off. This is why a war that kills working-age men depresses dependent-to-working ratios temporarily, then recovers.

Politically, dependents are mostly **politically unaligned** — they don't vote unless `Women's Suffrage` or `Old Age Pension` is enacted (which lift specific dependent classes into political alignment). This is the structural reason those two laws produce vote-share shifts that look outsized vs. their direct modifiers.

## 11. Job satisfaction — willingness to find new work

A per-pop scalar representing willingness to find new work. **Two consumers** read it:

1. **Workplace switching within the state** — the primary use. Pops with low job satisfaction are more willing to leave their current employer for a different building inside the same state, gating the in-state hiring churn that fills new factories from existing labor pools.
2. **Migration desire** — the secondary use. The vanilla define `MIGRATION_DESIRE_FROM_JOB_SATISFACTION_FACTOR = -1.0` makes job satisfaction the dominant input to a pop's migration desire (higher satisfaction → lower desire → less migration). It's not the only input — discriminated status raises desire on its own — but it's the main one in `common/defines/`.

So job satisfaction is the unified "I'm content where I am" gauge that gates both intra-state job hopping and cross-state migration; the same score is read at two different decision points.

The signed contributions to the score (mechanism shape, magnitudes drift — verify in `common/defines/00_defines.txt § JOB_SATISFACTION_*`):

- **Base**: large negative (default state is "willing to move on").
- **Employed**: large positive.
- **Government building employment**: additional positive (gov workers are stickier).
- **Recently hired**: very large positive (acclimation period).
- **Income above expenses**: very large positive (`JOB_SATISFACTION_FROM_CAN_AFFORD_EXPENSES`).
- **Income below expenses**: negative.
- **SoL above expected / state-stratum-avg / country-stratum-avg**: per-difference positive (or negative if below).
- **Wage above/below normal wage**: per-percentage point delta.
- **Qualifications for higher stratum**: negative (qualified-but-not-promoted pops are restless).
- **Dividends as percentage of wage**: positive when high (owners are sticky).

The shape: shocks like state-SoL drops or post-war unemployment drop satisfaction, which then propagates into both the in-state churn (workers shop for new jobs) and the migration economics in `vanilla_economy_reference.md` § 8.

## 12. Hiring proportionality

Buildings hire across professions roughly in proportion to their PM-required mix. The rule: a building cannot hire a full slate of one profession unless it can also hire ≥ ~90% of each other required profession. Conversely, losing one profession's pool forces firings across the others to maintain ratio.

Two exceptions:

- **Ownership buildings** (Manor Houses, Financial Districts) ignore proportionality — Aristocrats and Capitalists can be hired solo.
- **Officers, Servicemen, and Peasants** ignore proportionality — military and subsistence buildings staff their special professions independently.

The 90% threshold is in `common/defines/EMPLOYMENT_PROPORTIONALITY_LIMIT`. This is the mechanism behind "factory not hiring despite jobs available" complaints — the missing profession is a non-officer non-serviceman one that proportionality demands before the building can fill its other slots.

## 13. Cross-references

- **Country-aggregate economy (wages, IP, subsistence, migration economics, capacity resources)**: `vanilla_economy_reference.md`.
- **Politics (IG attraction, approval, movements driven by pops)**: `vanilla_politics_reference.md` § 5.3, § 5.4, § 8.
- **State-level mechanics (cultural communities, turmoil, food security, pollution effects on pops)**: `vanilla_states_reference.md` § 6, § 7, § 11, § 12.
- **Technology (literacy → innovation cap and tech spread)**: `vanilla_technology_reference.md` § 3.2, § 4.2.
- **Per-profession definitions**: `common/pop_types/`.
- **Per-strata / per-class definitions**: `common/strata/`, `common/social_hierarchies/`.
- **Per-need-category goods substitution**: `common/needs/`.
- **Per-buy-package SoL → consumption mapping**: `common/buy_packages/`.
- **Acceptance laws**: `common/laws/00_citizenship.txt`, `common/laws/00_church_and_state.txt`.

## 14. Maintenance protocol

1. **On every vanilla patch**: re-verify per-stratum partitioning if a new social hierarchy is introduced (it's been stable since 1.4 — Base, British Indian, Edo — but a future DLC could add another). Update banner.
2. **Per-profession formulas drift**: section § 4 says "high wage" or "baseline IP" rather than specific multipliers because exact values shift. If a vanilla bump adds new specials or changes who-counts-as-Upper-stratum, update the descriptions; **don't add a per-profession value table** here.
3. **The ×0.01 peasant SoL-change override and the Public-Health-Insurance-shrinks-population paradox** are durable, non-obvious mechanics worth keeping prominently flagged. If they ever change, that's a major patch note worth re-anchoring against.
4. **Don't reproduce qualification factor formulas**. They're long and per-profession; query the data file.
