# Vanilla States Reference (Victoria 3)

A primer on how the **base game's** state-level mechanics work — incorporation, infrastructure, market access, capital, turmoil, obstinance, devastation, food security, pollution, harvest conditions, hubs and split states. States are the unit buildings attach to, where pops live, and where most modifiers terminate. This doc covers the per-state state machine; the country-scope economy that aggregates all states lives in `vanilla_economy_reference.md`.

> **Last verified against vanilla:** 1.13.5 (Hotfix to "The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. The patch runbook (`docs/guides/vanilla_patch_runbook.md`) directs whoever performs a vanilla bump to revisit this file.
>
> **This doc captures concepts, not exhaustive lists.** State trait catalogs, per-state-region resource limits, per-decree per-state effect lists drift each patch and live in `common/state_traits/`, `map_data/state_regions/`, `common/decrees/`, `common/static_modifiers/`. Read this doc for the *shape*; query the data files for values.
>
> **Numbers describe mechanism, not balance.** Range bounds (incorporation 2–25 years scaling by cultural homeland, food-security 0–100%), tier names (turmoil Moderate / High / Extreme; starvation Mild / Severe / Famine), and structural ratios stay; specific defines like `LOW_POP_THRESHOLD = 5000` or per-decree decay coefficients do not. Look those up in `common/defines/00_defines.txt` when balancing.

## 1. The state hierarchy

| Unit | What it is | Notes |
|---|---|---|
| **Province** | Smallest map cell. | Mostly gameplay-irrelevant; relevant for terrain, devastation visuals, hub locations, and some triggers. |
| **State region** | The geographic outline. | Defined in `map_data/state_regions/`. Has a fixed set of provinces, fixed traits, fixed arable land and discoverable resources. |
| **State** | A region — or a portion of one — owned by a single country. | The mechanical unit. Pops, buildings, infrastructure, modifiers all live here. |
| **Strategic region** | Group of state regions (e.g. Western Europe). | The unit that interests, fronts, and HQs use. 36 of them in vanilla, ~6–47 state regions each. |

A state region typically maps 1:1 to a state, but split states (§ 1.2) are a routine exception. The state is what pops, buildings, and most modifiers reference; the state region is the geographic outline that resources and traits attach to.

### 1.1 Hubs

A **hub** is a designated province within a state region that visually represents a city / farming district / mine / port / forestry hub, sized by the count of related buildings. The five hub types: City (everything not in another category), Farm (agriculture and plantations), Mine (mines and oil rigs), Port (shipyards, fishing/whaling, ports/naval bases), Wood (logging camps). Hubs can overlap (one province being both Port and City), and not every state has every hub — inland states have no port hub.

Mechanically, hubs are almost entirely cosmetic. The one mechanical exception: **port hubs define treaty-port locations** — subjects ceded as treaty ports use the port-hub province. The road/rail network drawn through hubs is purely visual; it doesn't gate routing or supply.

### 1.2 Split states

A **split state** exists when two or more countries each own part of the same state region. Each owner has a separate state object inside the same region; they share the region's traits and aggregate resource pool, divided proportionally:

```
share = (regular_provinces + 5×prime_provinces) / total_(regular + 5×prime)
```

"Prime" provinces (those holding hubs and key features) count five-times-heavier than regular ones — this is why losing a hub province hurts a split owner disproportionately. **Sea-based resources (fishing, whaling, ports, naval bases) are unavailable to a split-state owner with no coastal province**, but the resources are still apportioned to that owner by share — they reduce other owners' availability without being usable themselves. This is occasionally a balance footgun; the loser of the coast suffers, the rest of the region loses its full sea-resource potential.

Three ways split states get created during gameplay: treaty ports, colonization landing in an existing-state region, or scripted effects (revolutions, releasable countries, events). Two split-state naming conventions:
- A split state owning more than half of the region takes the region's name.
- A split state with only a single hub-province takes the hub's name (so a country owning only the Hudson's Bay portion of an Arctic region gets a state named for the relevant hub).
- A one-state country owning only its split portion typically gets the country's name.

### 1.3 Resource limits and discoverable resources

Each region has fixed **arable land** (caps agriculture/plantation building levels) and resource deposits (caps mines/oil rigs/etc.). Some resources are **discoverable**: gold, rubber, oil — present from game start but locked behind unlocking technologies. The state region UI surfaces "discoverable resource present" before the unlocking tech is researched.

## 2. Incorporation status

A state is in one of three statuses:

- **Incorporated** — full political integration. Pays full bureaucracy cost, full taxation, applies all institutions, contributes to political strength normally.
- **Unincorporated** — owned but lightly administered. Pays no bureaucracy cost, pays no pop taxes (nationally-owned buildings still pay dividends counted as taxes), receives no institution effects, has reduced infrastructure, and pops have severely reduced political strength.
- **Colony** — actively undergoing colonization (§ see `vanilla_colonization_reference.md`). A special unincorporated subtype that cannot begin incorporation while colonization is ongoing.

Unincorporated states carry a substantial penalty package (rough shape, exact magnitudes in `common/defines/`):
- Reduced infrastructure (a flat percentage cut).
- Reduced market-access price impact.
- Reduced conscriptable battalions.
- Reduced pop political strength.
- Reduced expected standard of living.
- Reduced throughput on manufacturing / government / military buildings.
- Reduced construction efficiency, varying by building category — heavy industry hit hardest, infrastructure least.
- Subsistence buildings produce less; starting wages lower.

The penalties remain in full until incorporation completes. **Incorporation is not a binary** — it phases in over the incorporation period, with benefits ramping linearly.

### 2.1 Incorporation time scales by cultural homeland

The base time to incorporate scales by how culturally aligned the state's homelands are with the country's primary cultures. Five tiers (durable across patches; numbers below describe the *shape*, not balance):

- **Primary culture homeland** — fastest (≈ 2 years).
- **Shared heritage and language traits** — ≈ 5 years.
- **Shared heritage or language trait** — ≈ 10 years.
- **Shared heritage or language group** — ≈ 15 years.
- **No shared heritage nor language group** — slowest (≈ 25 years).

Five society technologies further reduce incorporation time additively. The base scales above describe *intent*: states aligned with the country's cultural identity integrate quickly; foreign-culture states integrate slowly.

**Conquering a state with a primary-culture homeland from an existing claim auto-incorporates it.** This is why reclaiming a lost incorporated state is essentially free — the engine treats it as the country's home territory rather than a fresh acquisition.

### 2.2 Incorporation requires bureaucracy surplus

Incorporation cannot begin in a state unless the country's bureaucracy surplus exceeds the state's full administered cost. The cost applies during the incorporation period, before the new state's institutions begin contributing. This is the routine constraint on whether to bother incorporating remote unincorporated states — the bureaucracy is paid up-front against a state that won't return its full benefit until the integration completes.

There is **no way to unincorporate a state by player action**. The two paths back to unincorporated: lose ownership and recapture (which restarts incorporation), or have the state revolt (which can place it back into another country's unincorporated bucket).

## 3. Capital and market capital

Each country has two designated states whose roles are mostly distinct:

- **Capital state** — the seat of government. Provides flat bureaucracy / authority / influence bonuses, grants pops in the state +25% political strength, and is the occupation-target for some war goals (occupying the capital can force capitulation).
- **Market capital** — the state used to compute market access and isolated-state checks. Adds a flat infrastructure bonus and a trade-advantage bonus to its own state.

Both can be moved during peace (not while at war or in a diplomatic play), once per 5 years each, with a 5-year decaying penalty to the relevant capacity (bureaucracy/authority/influence for capital moves; building throughput for market capital moves). Forced-move scenarios — capital occupied or forced by event — auto-incorporate the new capital.

The **market capital** specifically is what overseas states reference for shipping-lane convoy supply (`vanilla_economy_reference.md` § 17). A landlocked country's market capital is also where overseas trade aggregates back to.

## 4. Infrastructure and market access

### 4.1 Infrastructure sources

All states have a small base infrastructure value. Sources stack:

- **Population** — scales with state population once `Urbanization` is researched, expanding with successive society technologies (Urban Planning, Modern Sewerage, Steel-Frame Buildings, Elevators) that raise both the per-100K rate and the cap. Coastal states get an additional per-population bonus on top. Capital state gets a larger per-population coefficient than non-capital. The exact rate per technology is in the wiki and is a balance number; the *cap-and-rate-both-grow-with-tech* shape is the durable mechanism.
- **Automobile consumption** — pops consuming automobiles add per-unit infrastructure; researching `Paved Roads` doubles the rate.
- **State modifiers** — coastal states permit ports; many state traits add or reduce infrastructure (rivers add, mountain ranges and deserts subtract). Unincorporated states take a flat percentage cut. Devastation cuts infrastructure proportionally.
- **Buildings** — Ports add a small amount per level (the *less* efficient source, but useful pre-rail in coastal states). **Railways are the dominant source** — they produce both infrastructure and the `transportation` good consumed by some PMs and as a pop need. Urban Centers add a tiny amount cheaply (no engines/clippers/steamers required, just coal or electricity), useful as a top-up.
- **Decrees** — *Road Maintenance* adds per-population infrastructure; useful as a temporary devastation/turmoil offset, less efficient than rail long-term.
- **Power-bloc principles** — Transportation Infrastructure (T1) adds 33% multiplicatively; Trade League power-bloc statues add 10%.
- **Companies** — several companies' prosperity bonuses provide direct infrastructure additions.

### 4.2 Infrastructure usage

Each building level consumes infrastructure. Typical usage by category:
- Agriculture / plantations / non-mine resource buildings — 1 per level.
- Government Administration / Universities / monuments — 1 per level.
- Mines and oil rigs — 2 per level.
- Light-industry factories — 2 per level.
- Heavy-industry factories — 3 per level.
- Military buildings — 0.2 per level.
- Construction sectors — 2 per level.
- Urban centers — 0 per level (free).

The early-game-to-late-game shift: infrastructure usage starts around 1 per level on average and creeps to 2+ as heavy industry develops, which is why the constant pressure on rail levels never lets up — industrialization eats infrastructure faster than population growth produces it from urbanization alone.

### 4.3 Market access — the shape

Market access is the percentage of `min(infrastructure, infrastructure_usage) / infrastructure_usage`, capped at 100%. If usage exceeds infrastructure, market access drops proportionally.

Two additional gates:

- **Overseas states** require shipping lanes and sufficient convoys (or, post-1.13, sufficient Merchant Marine — see `vanilla_economy_reference.md` § 17.1). Even with adequate infrastructure, an overseas state with insufficient convoy supply takes a market-access cut.
- **Isolated states** have 0 market access. Isolation occurs when no land-and-shipping-lane path to the market capital exists.

Market access has two effects on the local economy:

1. **It scales the state's contributions to the national market** — buy and sell orders entering the national market are multiplied by market access. A state at 50% access contributes only 50% of its theoretical buy/sell.
2. **It scales the Market Access Price Impact (MAPI)** — the percentage of market price (vs. local price) that pops and buildings actually pay. Low MAPI states see prices diverge sharply from market prices; high MAPI states track market prices closely. See `vanilla_economy_reference.md` § 13 for MAPI details.

## 5. Taxation capacity

Incorporated states need **taxation capacity** to actually collect taxes. The mechanism: a state needs 1 point of taxation capacity per 10,000 population for full collection; below that, a percentage of taxes go uncollected (the state taxes proportionally to its capacity ratio).

- Base 100 taxation capacity per state.
- Some technologies raise the base.
- **Government Administration buildings** are the dominant source. More advanced PMs greatly increase capacity per level; throughput and economy-of-scale bonuses apply.

Taxation capacity is **distinct** from tax waste:

- **Taxation capacity shortfall** drops a percentage of taxes from the under-served state.
- **Tax waste** (from country-wide bureaucracy deficit) drops a percentage of total taxes country-wide.

A state can also lose tax collection from external sources: recently-conquered states, obstinance penalties, certain events.

## 6. Cultural communities

A **cultural community** is a per-state per-culture marker that the engine uses to gate *intra-market* migration. A pop cannot migrate to a state lacking a cultural community matching its culture.

Communities form and disappear:

- **Form**: cultural communities present in any culture's pops obviously persist. New communities also appear stochastically each month per state-per-culture, with a small base chance multiplied by many factors (port presence, trade center, coastal status, available arable land, river state-trait, *Greener Grass Campaign* decree, colony status). Multiplicative factors penalize hostile / discriminated cultures, devastated / turmoil-heavy / shortage-suffering / wartime / pre-revolt states. Capped at a low single-percentage base per culture per state per month.
- **Disappear**: a community vanishes after ~3 weeks if the culture has no pops in the state.
- **Local acceptance penalty**: a brand-new community starts with a temporary local acceptance debuff that decays monthly.

The ergonomic implication: opening a new state to immigration from a previously-absent culture is gated by a stochastic process. The *Greener Grass Campaign* decree exists primarily to push this dial.

**Mass migrations bypass the cultural community gate** — they create the community on arrival.

## 7. Turmoil

A state where a high percentage of pops are radicalized enters **turmoil** with three named tiers:

- **Moderate** (≈ 25%+ radical): notable tax-waste / construction / migration penalties.
- **High** (≈ 50%+ radical): substantial penalties.
- **Extreme** (≈ 75%+ radical): extreme penalties.

Each tier scales the penalty: tax waste, construction efficiency cut, migration attraction cut. The exact percentages live in `common/static_modifiers/` (`state_turmoil_*`); they're balance values and drift across patches.

**Turmoil reduction** comes from:
- The **Law Enforcement institution** — each level cuts turmoil's penalty effects by a fixed percentage; *Local Police Force* law adds a slight bonus to that reduction. The reduction ramps up with incorporation when applied to a freshly-incorporating state.
- The **Violent Suppression decree** — large turmoil-effect cut at the cost of state mortality scaling with turmoil.

## 8. Obstinance

Distinct from turmoil. **Obstinance** is generated by **cultural / religious / pan-national movements at 50%+ activism** (see `vanilla_politics_reference.md` § 8.4). It does **not** require radicalized pops; pops can be loyalists *and* contribute to obstinance if they support an obstinate movement.

Obstinance percentage in a state equals the workforce share supporting obstinate movements (capped at a moderate maximum, vanilla ≈ 20%). Each percentage of obstinance applies linearly:
- Reduced tax collection (capped).
- Reduced assimilation and conversion (capped).
- Reduced conscriptable battalions (capped).
- Reduced institution effectiveness (capped).

Foreign powers can amplify obstinance via the *Support Separatism* diplomatic interaction, which boosts movement attraction and radicalism (`vanilla_diplomacy_reference.md` § 7).

## 9. Devastation

States occupied during war or damaged by events accumulate **devastation**. The shape:

- **A constant per-day trickle in occupied states**.
- **Battle-occupation bumps** per battle in the state, scaled by formation devastation modifiers.
- **Per-day decay in unoccupied states** with two compounding multipliers:
  - The built-in `state_region_devastation` static modifier carries `state_devastation_decay_mult = 3.0`, scaled by the state's current devastation level — high-devastation states naturally decay faster than mildly-devastated ones (a self-correcting feedback that prevents states staying devastated indefinitely).
  - **`state_devastation_decay_mult` is a registered modifier** (added in 1.13 — see `common/modifier_type_definitions/00_modifier_types.txt`). External modifiers can speed or slow decay: e.g. the *Brutal Anti-Bandit Campaigns* event modifier sets it to −1 (stops decay outright). Mod content can grant decay-speedup as a reward, or decay-penalty as a flavor cost.

Each point of devastation linearly cuts: infrastructure, construction efficiency, migration attraction, building throughput, and *adds* to pop mortality. Heavy occupation can compound to multi-points-per-week throughput loss + significant mortality.

Devastation applies to the **entire state region**, regardless of which split-state owner caused it. If two split-state owners are at war and one occupies, both feel the devastation.

## 10. Harvest conditions

Despite the name, **harvest conditions are a generic per-state-region timed-event system**, not strictly agricultural. The vanilla type list in `common/harvest_condition_types/00_harvest_condition_types.txt` covers both agricultural conditions (drought, flood, frost, hailstorm, locust swarm, heatwave, optimal sunlight, moderate rainfall, pollinator surge, torrential rains) **and broader regional events** (wildfire, disease outbreak, extreme winds, **tsunami**, **earthquake**). The non-agricultural ones touch infrastructure, market access, urban-center throughput, mortality, and subsistence — not just agriculture buildings.

Each condition fires per-state with a randomized intensity (a discrete level inside the type's defined `range`) and duration. Each state in a region gets its own roll, so a state whose history diverges from siblings (different ownership, different traits) may keep the condition longer or shorter than the others. The full list of effects per condition is in the type definition's `modifier` block; conditions can be positive (optimal sunlight, moderate rainfall, pollinator surge) or negative (the rest).

Harvest conditions are the engine surface used by JEs and event chains for "natural disaster" modeling — Krakatoa's eruption uses the tsunami type, for example. Mod content adding a regional-event flavor can register a new condition type rather than building one-off scripted effects, which gets the engine's intensity-and-duration randomization for free.

## 11. Food security

A per-state value in [0%, 100%] representing how easily pops afford basic food. Two reductions:

- **Basic Food shortage** in the state.
- **Share of pop income spent on Basic Food** at base price.

The starting point is 100%; both reductions subtract toward 0%.

Add-backs:
- **Emergency Relief decree** — flat boost.
- **Charity Hospitals law** — per-Health-System-level boost.
- **Social Security institution** — per-level boost; with `Old Age Pension` the per-level rate is higher.

Three tiers of starvation, each driving birth-rate / mortality penalties:

- **Mild** (food security < 40%) — moderate birth-rate cut + mortality bump.
- **Severe** (food security < 20%) — severe birth-rate cut + mortality bump.
- **Famine** (state-wide threshold of mild + severe shares) — purely a political classification: triggers narrative content, surfaces a UI warning, but doesn't add direct mechanical effects beyond what mild/severe already do.

The famine's narrative purpose is content-hookup, not mechanic-stacking. JEs and decisions branch on famine state.

## 12. Pollution

Most production methods generate **pollution**. The shape of the model:

```
pollution_impact_target = (total_pollution_generation × normalization)
                          / (50 + 1.5 × √(arable land))
```

Pollution impact moves toward the target gradually each day; the target's denominator means pollution is **diluted by arable land** (large rural states absorb pollution better than dense urban regions of the same total industry).

Each percent of pollution impact: reduces migration attraction; reduces standard of living; increases mortality; increases drought / flood / wildfire / heatwave impact.

**Mitigation** comes from `Health System` institution (per-level reduction; higher reduction with `Public Health Insurance`) and the `Modern Sewerage` technology. There is no per-state pollution-cleanup decree; pollution mitigation is country-scope only.

Pollution is region-wide (split-state owners share the pollution impact).

## 13. Slave / Free states under specific laws

Two laws partition states into slavery-allowed / banned subregions:

- **Legacy Slavery** — divides states into Slave States and Free States. Slave states function as if under `Slave Trade` (with a critical exception: **new slaves cannot be imported from abroad**, only born / inherited / converted within). Free states function as if `Slavery Banned`.
- **Colonial Slavery** — unincorporated states function as if `Debt Slavery`; incorporated states function as if `Slavery Banned`.

Free states under Legacy Slavery can convert to slave states via events or via enacting `Slave Trade` (which uniformly converts all states to slave states).

## 14. Decrees on states

State-targeted authority spends; one decree per state slot at a time, with the three industry-encouragement decrees mutually exclusive within a country. See `vanilla_politics_reference.md` § 11 for the politics-side mechanics; `common/decrees/00_decree.txt` for per-decree effects. The state-scope effect is the per-decree modifier; the country-scope cost is the authority reservation.

## 15. Cross-references

- **Pops, infrastructure, market access — country-aggregate side**: `vanilla_economy_reference.md` § 1, § 8, § 13.
- **Turmoil and obstinance feedback into politics**: `vanilla_politics_reference.md` § 5.4 (approval), § 8.6 (obstinance from movements).
- **Devastation and battle effects**: `vanilla_war_reference.md` § 8 (battles), § 10 (supply / attrition).
- **Cultural communities and migration**: `vanilla_economy_reference.md` § 8.
- **Capitulation via capital occupation**: `vanilla_war_reference.md` § 13.
- **State traits + state regions data**: `common/state_traits/`, `map_data/state_regions/`.
- **Static state modifiers** (turmoil bands, devastation per-point, unincorporated penalty package): `common/static_modifiers/00_static_modifiers.txt` / `common/modifiers/00_static_modifiers.txt`. Use `/modifier-search?q=state_` for the per-state modifier catalog.

## 16. Maintenance protocol

1. **On every vanilla patch**: revisit per `docs/guides/vanilla_patch_runbook.md`. Update banner; revise sections where 1.x semantics shifted (devastation rates and pollution coefficient drift each patch — they're balance, not mechanism).
2. **State-trait additions** (mod-side) — `common/state_traits/` registry rules apply. Don't hand-edit a state-region file to add a trait that doesn't exist; register the trait first.
3. **Don't reproduce state-region data here.** The list of state regions, hub provinces, and arable-land values is large and authoritative in `map_data/`. Keep this doc to mechanism.
4. **Per-decree per-state effects belong in `common/decrees/`** — the table of "what each decree does to which state-scope modifiers" is balance content; query `/raw/Decree/<id>` for the live values.
