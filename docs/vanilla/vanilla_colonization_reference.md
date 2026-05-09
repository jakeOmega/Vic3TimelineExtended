# Vanilla Colonization Reference (Victoria 3)

A primer on how the **base game's** colonization system works — establishing colonies, frontier vs. overseas, colonial claims, malaria gating, colonial-state mechanics, tension and native uprisings, the Colonial Administration subject type, and company colonization. This is a niche but mechanic-rich corner of the game; the mechanics live across `common/laws/00_colonization.txt`, `common/state_traits/`, `common/decisions/`, `common/journal_entries/`, and the Civilizing-Mission JE in `common/journal_entries/`.

> **Last verified against vanilla:** 1.13.4 (Hotfix to "The Great Wave"). Wiki source dates this article 1.10–1.12; native-uprising mechanics, Colonial Administration JE, and company-colonization rights are all 1.10+ content. Verify specific conditions / cooldowns against `common/journal_entries/`, `common/decisions/`, `common/diplomatic_actions/`, and the relevant law file.
>
> **This doc captures concepts, not balance values.** Per-state colonial-growth coefficients, malaria mortality numbers, exact tension thresholds, and per-region colonial-administration starting laws live in data files; reproducing them here would drift. Read this doc for the *shape* of colonization; the parameters belong with the per-region / per-decree definitions.

## 1. The colonization gate

Colonization requires:

1. The **`Colonial Affairs` institution** (any Colonization law except `No Colonial Affairs` enables it).
2. The **`Colonization` technology** (Era 1 Society — researched at start by most recognized powers).
3. **Sufficient Involvement** in the strategic region containing the target state — see `vanilla_diplomacy_reference.md` § 6 for the full Involvement-tier system. Colonizing requires reaching the **Engaged tier or higher** (per the diplomacy doc § 6.3, Engaged is the tier that unlocks colonization, play-starts, defensive pacts, and guarantee-independence).
4. The target state to be **owned by a decentralized nation**.
5. The target state to be **coastal**, OR adjacent to a state already owned by the colonizer.

Once gated, the colonizer pays an upfront cost (a coastal colony auto-builds a level-1 port to prevent immediate isolation) and the colony begins growing province-by-province.

A country can run **any number of simultaneous colonies**, but at most one per state region. Every colony is a separate `colony` state — a special unincorporated subtype that cannot begin incorporation while colonization is ongoing.

> **1.13 Diplomatic Interest rework note.** Older sources (wiki articles dated 1.10 / 1.12, mod docs, Reddit guides) describe a binary "declared interest" system with a per-rank declared-interest pool the player spent like currency. **That system is gone.** Interests now run on a continuous *Involvement* score that buckets into six tiers (None → Observant → Engaged → Influential → Pervasive → Hegemonic), built up by owning states / having subjects / signing treaties / projecting power / patrolling coasts. Colonization specifically requires Engaged tier or above; later actions (alliances, claim-staking, infamy discounts) gate at higher tiers. This doc was updated to reference the tiered system, but **any mod content that still calls `country_max_declared_interests_add` or assumes a binary interest-flag is stale and needs review against the live game**.

### 1.1 Frontier Colonization restriction

The `Frontier Colonization` law restricts new colonies to state regions **contiguous with the colonizer's capital state** — either by direct land bridge or by sharing a sea zone with the capital state's contiguous mass. This effectively prevents most overseas colonization, leaving frontier-style expansion (Russia eastward, the USA westward, Argentina/Brazil into the interior). Transitioning from `Frontier Colonization` to `Colonial Resettlement` or `Colonial Exploitation` opens overseas colonization but is opposed by Rural Folk under most conditions.

### 1.2 Colonial Affairs at game start

Countries that start with Colonial Affairs already enabled get **automatic colonies** in every owned state region that contains a neighboring decentralized nation. These initial colonies bypass colonial-claim rules and are the standard 1836 starting condition for the European powers' overseas territories.

## 2. Colonial claims

A state region can have **claims by one or more countries**. While any claiming country has Engaged-or-higher Involvement in the region, only claiming countries can colonize; once all claiming countries lose the qualifying tier (Involvement falls below Engaged), any other country at Engaged or above can colonize. Once a colony has been *started* in a claimed state, it continues regardless of subsequent Involvement changes.

This is the engine's coordination mechanism for the Scramble for Africa: claims partition the continent; the Engaged-tier Involvement gate determines who's actually committing to an active push; if all claimants drop below Engaged, the region opens to new entrants.

### 2.1 Non-colonization agreements (Colossus of the South DLC)

A diplomatic agreement that prevents starting *new* colonies in a specified strategic region. Existing colonies continue; new ones cannot start while the agreement holds.

## 3. Malaria

Two state traits gate Sub-Saharan Africa and Oceania:

- **Malaria** — heavy colonial-growth penalty + mortality bump for non-homeland cultures.
- **Severe Malaria** — even heavier; **completely blocks colonization** until `Quinine` is researched.

The shape:

- `Quinine` (Society tech) **disables Malaria's effects entirely** and **unlocks colonization in Severe Malaria states**.
- `Malaria Prevention` (Society tech) **disables Severe Malaria's remaining effects** (the colonization-block was already lifted by Quinine; this strips the lingering mortality).
- Both mortality and growth penalties **only apply to cultures without a homeland in the state**. A primary culture with a homeland in a malarial state colonizes at full speed with no mortality penalty.

These two techs are the gates that the wiki frames as "you can't take Africa before late-game"; in practice, most powers research Quinine in Era 3, around the historical 1850s.

## 4. Colonial states — growth mechanics

A colony state is a special unincorporated state that **cannot begin incorporation until colonization completes**. Colonies can be **abandoned** by the player, returning the state to the decentralized nation. Colonization completes when no accessible decentralized nations remain in the state region.

### 4.1 Total colonial growth

Total colonial growth per country = Colonial Affairs institution levels × incorporated population × a base scaling coefficient, capped at a range bounded above and below.

The cap range:

- **Minimum colonial growth** clamps small-population countries up to the floor.
- **Maximum colonial growth** clamps large-population countries down to the ceiling.

Higher Colonial Affairs levels lower the population required to hit the ceiling — at level 5, a country with ≈1M incorporated population can max out colonial growth, vs. ≈5M at level 1. This is why investing in Colonial Affairs is *more* valuable for small colonial powers than for large ones; large powers hit the cap regardless.

Growth is **split equally across all non-isolated colonies** the country runs. Two simultaneous colonies each get half the country's total growth. This is why running too many colonies simultaneously is inefficient — each is undernourished.

### 4.2 Local colonial-growth modifiers

Per-state, the country-wide allocation is then modified by:

- **Province count vs. baseline (≈ 50 provinces)**: each province above 50 adds + growth-speed bonus; each below subtracts. Large state regions colonize faster.
- **Population in the state region** (sum of decentralized-nation population + colonizer's): above 200K starts a scaling penalty (≈ ×0.8 at 200K, ×0.67 at 400K, ×0.5 at 800K). Densely-populated regions resist colonization heavily.
- **Malaria** (severe blocks; non-severe cuts) — see § 3.
- **Ruler's Colonial Administrator trait** — per-tier bonus.
- **Colonial Rights modifier** (won by defeating a native uprising) — doubles colonial growth speed against that decentralized nation for the truce duration (5 years).

The base maximum growth speed per day is small (≈ 2%); doubled with Colonial Rights. Each time the colony reaches 100% growth, one more province is ceded to the colonizer; impassible provinces colonize as a contiguous group.

## 5. Tension and native uprising

Each province colonized adds **tension** with neighboring decentralized nations (per-province bumps in the range [+2.5, +20], depending on conditions). Tension decays at a base rate per year; if growth continues, tension net-rises.

At a tension threshold (≈ 75), the decentralized nation can start a **native uprising** — a special diplomatic play seeking to retake their homeland and expel the colonizers. As a play, other countries can support either side normally.

Outcomes:

- **Decentralized nation wins** — annexes the colonizer's colony states in each state region they own part of.
- **Colonizer wins** — gains the **Colonial Rights** modifier (doubles colonization speed for 5-year truce).

While a native uprising is active, the decentralized nation's states **cannot be colonized by any country** — all simultaneous colonies in the affected regions are paused. After the play ends, paused colonies automatically restart (if they survived).

The system is the engine's way of making rapid colonization expensive and risky: stack colonies fast, generate tension, eat one or more uprisings, and the truce-and-rebuild cycle gates how quickly Africa or Oceania can be partitioned.

## 6. Colonial Administration subject

A specialized **subject type** (not a normal Vassal/Puppet/etc.) created via the *Establish Colonial Administration* journal entry. The JE is available to recognized countries with capital outside Africa, after researching `Civilizing Mission`, when they hold any state in a target Africa-region (Congo, Ethiopia, Niger, Senegal, Southern Africa, Zanj).

### 6.1 Establishment

The button "Establish Colony in [Region]" requires the country to own ≥ 2 incorporated states in the region (each the largest in their state region). Activation:

- Creates a new **Colonial Administration subject** based on this country.
- Cedes all owned states in the region to the new subject.
- Adds a permanent country-wide modifier to the establisher: cuts non-contiguous incorporation speed substantially, doubles contiguous incorporation speed.

The colonial administration starts at **principality tier** with a fixed law profile partially inherited from the establisher and partially fixed (`Colonial Administration` Governance Principles, `Subjecthood` Citizenship, `No Workers' Rights` Labor Rights, `Child Labor Allowed` Children's Rights, `No Health System`, `Migration Controls`). Other laws inherited from the establisher (Trade Policy, Taxation, etc.).

### 6.2 The Nature of Administration event

Immediately after establishment, an event fires for the establisher with **four mutually-exclusive options**, each of which:

- Imposes a different set of **additional starting laws** on the new subject (Distribution of Power: Oligarchy or Autocracy; Economic System: Extraction or Agrarianism; Free Speech: Censorship or Outlawed Dissent; Education System: No Schools or Religious Schools; Slavery: same as establisher or Slave Trade).
- Adds a **20-year region-wide modifier** specific to the chosen path:
  - **Colonial Company** (Chartered Company subject; +plantations / +mines throughput).
  - **Religious Mission** (+conversion).
  - **Colonial Settlement** (+migration attraction; +radicalism penalty for discriminated cultures).
  - **Colonial Extraction** (+plantations / +mines; +mortality; +radicalism penalty).
- Triggers an **IG approval bonus** for endorsing IGs.
- For all options except Colonial Settlement: **swaps Industrialists' Laissez-Faire ideology to Colonialist** in the new subject.

### 6.3 Region-wide consolidation

The "Expand Our Colony in [Region]" button merges multiple colonial-administration subjects in the same region or absorbs the establisher's remaining non-colony states in the region into the existing subject. Used after additional conquests to keep the region's administration unified.

### 6.4 Independence

If a colonial administration becomes independent (revolt, defeat, peace deal), an event fires:

- Some/most pops with European Heritage **evacuate to a homeland state**.
- Substantial radicalization of low-acceptance pops.
- A region-wide "alone" modifier for 10 years.
- Optional alternate path (with `Nationalism` + multiculturalism/council-republic/no-colonial-affairs/cultural-minority-movement-≥10%): all homeland cultures become primary; European Heritage cultures stop being primary.

This is the de-colonization pressure-relief: an independent colonial administration sheds its European elite, possibly in violent depopulation, and the region resets toward pre-colonial demographics.

### 6.5 Six pre-set colonial regions

Each of the six target regions has a fixed flag and name template; while a subject, the administration prefixes its overlord's adjective ("British Congo", "French Senegal", etc.):

- Abyssinia / Abyssinian.
- Congo / Congolese.
- East Africa / East African.
- Niger / Nigerien.
- Senegal / Senegalese.
- South Africa / Southern African.

South Africa as a Cape-Colony-derived subject keeps the British naming until independent.

## 7. Company colonization (Charters of Commerce DLC)

With the **Colonization Rights charter**, a colony gains +20% growth speed; on completion, the company **takes control of the new state** and forms a new country owned by the company — a **Chartered Company subject** of the company's overlord, with a permanent `colonial_administration` modifier.

The new country has:

- Same primary culture and state religion as the overlord.
- Inherited technology and most laws from the overlord, **with overrides** mirroring the Colonial Administration profile (Colonial Administration governance, Oligarchy, Subjecthood, Censorship, Colonial Exploitation colonization, No Workers' Rights, Child Labor Allowed, No Schools, No Health System, No Social Security, Migration Controls).
- **Industrialists with Colonialist ideology** instead of Laissez-Faire.

This is the alternative path to administered colonies: cheaper and faster (the charter does the work) but yielding a Chartered Company instead of a directly-controlled subject. The political cost is liberty desire from the chartered structure; the economic benefit is faster colonization and the throughput modifiers Charter-flavor companies typically carry.

## 8. Cross-references

- **Diplomacy / subject types**: `vanilla_diplomacy_reference.md` § 10. Colonial Administration is one of the subject types listed there.
- **Interests / Involvement tiers**: `vanilla_diplomacy_reference.md` § 6. Engaged-tier Involvement (or higher) is required to start colonies post-1.13.
- **Diplomatic plays (the native uprising special play)**: `vanilla_diplomacy_reference.md` § 11.
- **State mechanics (incorporation, infrastructure, ownership cascade)**: `vanilla_states_reference.md`.
- **Decentralized nations**: see `common/scripted_effects/` and decentralized-nation flavor in `common/country_definitions/`. They're mechanically simpler than full countries — no economy, no laws, no IGs.
- **Colonial-administration starting laws**: `common/scripted_effects/colonial_administration_*.txt` (vanilla); for mod overrides see `common/scripted_effects/extra_effects.txt`.
- **Company charter**: `common/company_charters/`.
- **Civilizing Mission technology**: `common/technology/technologies/00_society.txt`.

## 9. Mod implications

- **Colonial Administration JE is fragile**. Its triggers branch on capital location and DLC presence; when modding region definitions, ensure that strategic-region modifications don't break the JE's `is in Africa` check. The `is_capital_in_africa` test is on `country.capital.region` — re-mapping regions can silently disable the JE.
- **Frontier Colonization is structurally weaker than Colonial Resettlement**. Anytime mod content prods a country toward Frontier, factor in the Rural-Folk-endorsement difference and the lack of overseas colonization.
- **Native uprisings are a real wartime cost**. Mod content that pumps colonization speed should also account for the increased uprising frequency — the tension generation is per-province, not per-completion.
- **Don't reproduce per-region admin starting-law tables**. They're in `common/scripted_effects/` and may be modded; reading the live config beats quoting the wiki.

## 10. Maintenance protocol

1. **On every vanilla patch**: revisit per the patch runbook. Colonial Administration JE has been in active development through 1.10–1.13; expect more changes.
2. **DLC gating**: many features above are DLC-locked (Colossus of the South for non-colonization agreements, Charters of Commerce for company colonization, base game for Civilizing Mission). The mod targets the full DLC stack; specific DLC-required features are noted inline.
3. **Don't reproduce per-region balance values** — colonial growth coefficients, tension thresholds, mortality scaling per malaria tier all live in `common/defines/` and `common/state_traits/`. Reading the file beats quoting it.
