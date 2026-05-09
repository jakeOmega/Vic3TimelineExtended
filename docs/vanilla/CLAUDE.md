# Vanilla Vic3 Mechanics — What You Need To Know

A condensed "must-know" cheat sheet for vanilla Victoria 3, surfacing the **non-obvious** mechanics that bite mod work. Each entry below has a deep-dive doc — read those for the *why*; this is the *what*.

> **Last verified against vanilla:** 1.13.4 ("The Great Wave"). Numbers are absent on purpose — they drift each patch and live in `common/defines/`. The *mechanism shape* in this doc is durable.

> **Companion source — what *changed* per patch:** [Modding-Digests](https://github.com/Victoria-3-Modding-Co-op/Modding-Digests/) (cloned locally to `vic3_modding_digests_path`, auto-pulled on `mod_state_server` cold start). Per-version folders (1.8.7 … 1.13.4) hold `changes_breaking.md`, `changes_script_docs.md`, `changes_data_types.md`, and `changes_files.md`. **The docs in this directory describe what mechanics *are* in 1.13.4; the digests describe how each mechanic *got here*.** Hit the digests before manually diffing `~/src/vic3` between version commits.

---

## Pops, culture, society → `vanilla_pops_reference.md`

- **A pop is a unique tuple of (culture, religion, profession, workplace, state).** Every combination gets its own pop; tens of thousands per save.
- **Five acceptance tiers** (Violent Hostility → Cultural Erasure → Open Prejudice → Second-class → Full). Acceptance gates wage, political strength, profession access, migration eligibility, voting.
- **Assimilation is blocked at both Violent Hostility tiers.** It also requires a more-accepted culture to *already be present in the state* — pops can't assimilate to a culture with no community yet.
- **Religious conversion is reduced ≈ −90% in unincorporated states.** Big asymmetry vs. assimilation, which works fine in unincorporated.
- **Three social hierarchies** (Base / British Indian Caste / Edo). The non-obvious one: **Capitalists are Middle stratum under British Indian Caste, Lower stratum under Edo** — strata-targeted modifiers (welfare, expected SoL, taxation) land on different professions in those countries.
- **Peasants' SoL-change loyalty effect is ×0.01.** Subsistence pops are politically inert; industrialization is what politicizes them.
- **Slaves cannot migrate at all** under any law except `Slave Trade` (which bypasses Closed Borders for slave imports).
- **Public Health Insurance level 5 can produce net population *decrease*** because the SoL boost pushes pops past peak-growth into the slowing band.
- **Workforce/dependents ratio defaults 25/75**. `Women's Suffrage` and `Old Age Pension` lift portions of dependents into political alignment — that's the structural reason those laws produce outsized vote-share shifts.
- **Job satisfaction has two consumers**: in-state workplace switching (primary) and cross-state migration desire (via `MIGRATION_DESIRE_FROM_JOB_SATISFACTION_FACTOR = -1.0`).
- **Hiring proportionality** — buildings can't hire one profession without ≥ 90% fill on the others. Officers, Servicemen, Peasants ignore this; ownership buildings (Manor Houses, Financial Districts) ignore this.

---

## Economy → `vanilla_economy_reference.md`

- **Wealth → SoL → loyalty/radicalism is the inner loop.** Most modifiers apply to *one direction*; rising-SoL adders don't help on falling SoL. Net of an unstable economy is radical-weighted.
- **PMs are radio toggles per group.** Different groups stack additively; same group, only one active. Effects scale by `unscaled` / `level_scaled` / `workforce_scaled`.
- **Modifier scope cascade**: country → state → building. Same modifier name (`building_throughput_mult`) applied at any scope sums into the same per-building bucket.
- **Vanilla auto-registers dynamic modifier patterns** for specific axis combinations only. Mod-added buildings/goods need explicit registration in `common/modifier_type_definitions/`. Unregistered modifiers silently no-op.
- **Local goods (services, transport, electricity) don't ship.** Their price is set by the state's own supply/demand. Building services-buildings far from your industry is dead weight.
- **Authority is a flat reservation, not metered**. Every active decree, every active suppress, every active consumption tax, every monopoly, every excess corporate charter reserves a flat chunk for as long as it's active. Authority is a portfolio, not a one-time payment.
- **Bureaucracy deficit drives tax waste up to +100%.** Half-deficit can lose 50% of taxes country-wide. The most expensive thing to be deficit on.
- **Influence scales with rank, not economy.** Pact budgets are ~1000 for Great Powers regardless of how rich they are.
- **Investment Pool is where Aristocrat/Capitalist dividends go.** Subsistence farms (`ownership_type = self`) don't feed the IP — peasant wealth stays with peasants.
- **Migration: cultural community gates intra-market migration.** Mass migration creates communities on arrival; intra-market migration requires a pre-existing one.
- **Naval rework (1.13)**: convoys are gone, replaced by **Merchant Marine** as a market good. Shortages raise its price, which makes Trade Centers downsize routes — supply/demand rebalancing, not a hard cap.

---

## Politics → `vanilla_politics_reference.md`

- **Removing an IG from government radicalizes 25% of its pops** — *except* in the 6-month grace window after an election. That window is the cleanest moment to reshuffle.
- **Illegitimate government cannot enact ANY law** except those backed by a non-passive (≥ 25 activism) movement. Below 25 legitimacy = enactment freeze.
- **Ideology penalty counts only the LARGEST disagreement**, not a sum across all laws. Three IGs differing 2 steps on one law and 1 step on three others incur the 2-step penalty once.
- **Per-law-group ideology multipliers**: Governance Principles, Distribution of Power, Slavery amplify the penalty; Bureaucracy, Education System, Policing dampen it.
- **Party whip mechanic**: highest-clout IG in a party counts full ideological weight; secondaries count half. This is why parties exist — to halve the penalty.
- **6-month free reform window after elections** — first reform within doesn't radicalize.
- **Movements**: <25 passive / 25–49 active / 50+ obstinate / 75+ revolutionary. **While a law a movement has stance on is being enacted, its activism cannot drop below 25**. Re-mobilization on enactment is automatic.
- **Cultural / religious / pan-national movements at 50%+ activism contribute to state obstinance** — pops *don't need to be radical*, just supporters.
- **Powerful IG**: trait magnitudes ×2 (positive AND negative). Marginalized IG: traits do NOT activate. In-government but sub-marginalization-clout: ×0.5.
- **In-government IGs cannot be marginalized** even with low clout (safety net).
- **Leader ideology overrides core IG ideology** on conflicts — but it's temporary, ending with leader death/exile/retirement. Event-added core ideologies (Feminism research → Feminist) are durable.
- **Annual character death pulse**: 50% chance to kill a random IG leader (10-yr cooldown per IG); 20% chance to kill an agitator (5-yr cooldown); 20% chance an executive (7-yr cooldown).
- **Eight base IGs** (Armed Forces, Devout, Industrialists, Intelligentsia, Landowners, Petite Bourgeoisie, Rural Folk, Trade Unions) — names rename per country/culture/religion (Junkers, Samurai, Theravada Monks, etc.).

---

## War → `vanilla_war_reference.md`

- **Combat width is per-state, set by `(5 + infrastructure/2) × terrain_multiplier`**. Mountain provinces cap battle size hard, neutralizing numerical advantage.
- **War support drains from**: base trickle, war-goal control, **radicals (per-pop %)**, casualties, cultural casualties, **lobby clout**, occupation tiers. Capital/war-goal occupation produces large escalating bumps.
- **A country cannot fall below 0 war support unless an enemy occupies all its war goals or its capital state.** Subjects don't capitulate independently.
- **Naval rework (1.13)**: ships are objects, not abstractions. Convoys removed; Merchant Marine + Naval Construction + Ship Construction are separate market goods now.
- **Battle conditions** roll per side at battle start; rerolled with rising probability after 10 days. Terrain multiplies condition weights; commander traits multiply per-condition.
- **Mobilization tiers**: standing army active immediately, mobilized formations train up over weeks, conscripts ramp via Conscription Centers slowly. Mass-conscription doctrines have hard caps on conscript pool.
- **Power projection** (army + navy) feeds prestige separately from production prestige.

---

## Diplomacy → `vanilla_diplomacy_reference.md`

- **Seven ranks**: Insignificant → Unrecognized Power → Regional → Minor → Major → Great → Hegemony. Recognition matters for subject types.
- **Diplomatic Interest rework (1.13)**: binary "declared interest" is gone. Now a **continuous Involvement score in six tiers** (None → Observant → Engaged → Influential → Pervasive → Hegemonic). Each tier loosens what's possible.
- **Engaged tier or higher gates: colonization, starting plays, defensive pacts, guarantee-independence.**
- **Hegemonic tier flips infamy curve**: wargoal infamy in the region is *discounted* and decree cost is reduced.
- **Strategic-region map was consolidated in 1.13** — fewer, denser regions. Pre-1.13 hardcoded region IDs in mod scripts may be stale.
- **Power blocs**: six identities (Trade League, Sovereign Empire, Ideological Union, Military Treaty, Religious Convocation, Cultural Commonwealth — varies by DLC). Cohesion (Fractured → Orchestrated) gates mandate progress and leverage generation.
- **Leverage**: fixed pool. To invite a country, your bloc needs significantly more leverage on it than its self-resistance + any rival blocs. Alliances + investment rights + economic dependence are the heaviest factors.
- **Subjects: type × autonomy axes**. Puppet ↔ Protectorate; Vassal ↔ Tributary; Colony ↔ Dominion. Decrease/Increase Autonomy moves between paired types.
- **Liberty desire bands** (Low / Moderate / High) — high LD unlocks independence demands and stiffens overlord cost.
- **Treaty articles** are atomic clauses; treaties bundle them with obligations. Articles vs. pacts differ on "modifies what" vs "moves resources continually".
- **Diplomatic plays**: declaration → maneuvers → war or backdown. Sways add wargoals + force allies; primary vs secondary demands resolve separately.
- **Subject "Support Regime" pact** trades −10 overlord legitimacy for +20 subject legitimacy. Useful diplomatic-prop-up tool.

---

## States → `vanilla_states_reference.md`

- **Three statuses**: Incorporated / Unincorporated / Colony. Colony is a special unincorporated subtype that can't begin incorporation.
- **Incorporation time scales by cultural-homeland match** — primary culture homeland ≈ 2 years; no shared heritage/language ≈ 25 years. Conquering a primary-culture-homeland claim auto-incorporates.
- **There is no way to unincorporate a state** by player action. The only paths back: lose ownership and recapture, or revolt.
- **Capital state**: +25% pop political strength + capacity bonuses. Occupying it can force capitulation.
- **Market capital**: separate from capital. Sets reference for market access / overseas convoy supply.
- **Cultural communities** gate intra-market migration. ~3-week empty timeout. Max ~4% formation chance per culture per state per month, dampened heavily in hostile/devastated/turmoil states.
- **Turmoil tiers** (Moderate / High / Extreme) from radical pop %.
- **Obstinance** from cultural/religious/pan-national movements at 50%+ activism. *Doesn't require radicals* — just supporters.
- **Devastation decay is moddable in 1.13** via `state_devastation_decay_mult`. The built-in 3.0× scaling on the static modifier means high-devastation states naturally decay faster.
- **Food security** is `100% − basic-food-shortage − share-of-income-on-basic-food`. Three tiers: Mild (< 40%) / Severe (< 20%) / Famine (state-wide threshold combining the two).
- **Pollution dilutes by arable land** (`generation / (50 + 1.5×√arable_land)`). Big rural states absorb pollution better than dense urban regions of equal industry.
- **Harvest conditions are NOT just agricultural** despite the name. The vanilla type list includes **tsunami, earthquake, wildfire, disease outbreak** — they hit infrastructure, market access, urban centers, mortality.
- **Hubs are almost entirely cosmetic** — only port hubs are mechanical (treaty-port location). Road/rail visual rendering is purely cosmetic.

---

## Technology → `vanilla_technology_reference.md`

- **Three trees**: Production, Military, Society. Independent — unresearched techs in one tree don't penalize another.
- **Five eras (I–V)**. Base innovation cost rises with era; **ahead-of-time penalty** inflates later-era costs by a fraction-per-unresearched-earlier-tech-in-same-tree. Late-game rushes are expensive without filling earlier eras.
- **Power-bloc *Advanced Research* principle reduces ahead-of-time penalty per Education-institution level.**
- **Innovation cap ≈ base + literacy × coefficient**. National literacy = average literacy across **incorporated** states only.
- **Innovation generated above the cap spills into technology spread** (at reduced efficiency).
- **Tech spread requires another country to have researched it**. Catch-up mechanism for laggards.
- **Free Speech laws gate spread** — Outlawed Dissent / Censorship cut, Protected Speech boosts.
- **Slingshot strategy**: don't research a currently-spreading tech, research an alternate; spread runs free, alternate accumulates progress, when spread completes the alternate is finishable.
- **Many techs unlock invisibly** — leader ideologies, JEs, formable-country candidacies, decrees. Read the tech file, not just the modifier list.

---

## Colonization → `vanilla_colonization_reference.md`

- **Three gates**: Colonial Affairs institution + Colonization tech + Engaged-tier Involvement (post-1.13). Frontier Colonization additionally restricts to capital-contiguous regions.
- **Malaria** state trait blocks Sub-Saharan colonization until **Quinine** is researched. **Severe Malaria** flat-blocks until Quinine; remaining mortality stripped by **Malaria Prevention**. Effects don't apply to homeland cultures.
- **Tension accumulates per province colonized**, decays per year. At threshold (≈ 75), the decentralized nation can launch a **native uprising** special diplomatic play.
- **Native uprising loss = annexation** of all colonizer-state in the region. Win = Colonial Rights modifier doubling colonization speed for 5-year truce.
- **Colonial Administration JE** (Civilizing Mission tech, capital outside Africa) — creates a Colony-typed subject with one of four flavor profiles (Colonial Company / Religious Mission / Colonial Settlement / Colonial Extraction), each with different starting laws + 20-year regional modifiers.
- **Independence event for a Colonial Administration**: European-Heritage pops evacuate, low-acceptance pops radicalize heavily, optional path drops European Heritage from primary cultures entirely.
- **Company colonization (Charters of Commerce DLC)**: Colonization Rights charter + 20% growth speed; on completion the colony becomes a **Chartered Company subject** with `Colonialist` Industrialists ideology.
- **Colonial growth is split equally across all non-isolated colonies** — running too many simultaneously starves each.

---

## Formable countries → `vanilla_formable_countries_reference.md`

- **Three formation paths**: minor (control %), major (candidacy + plays), special (extra JEs).
- **Minor unification**: control X% of target states (or cultural-homelands), country tier *lower* than the formable's. Subjects sharing primary culture auto-annex on formation.
- **Major unification**: candidacy-based. Up to 3 candidates from most-prestigious eligible great powers. Leadership plays disqualify rivals; unification plays force-cede primary-demand states. **Successful unification plays generate no infamy** — the high-risk-high-reward path.
- **Five major formables**: Federation of the Andes (1.13), Germany, Italy, Scandinavia, Yugoslavia.
- **Special unifications**: Iberia, China, Arabia, Ethiopia, India, Indonesia, Romania, Peru-Bolivia, Canada, Australia, North/South German Federation — JE-driven assists.
- **`add-formable-country` skill** (`.claude/skills/add-formable-country/SKILL.md`) is the canonical lookup for adding new formables — including dynamic-name government-conditional variants.

---

## Cross-cutting non-obvious facts

- **Modifier validation is silent** — invalid modifier names and unregistered dynamic patterns are silently ignored. Always verify via `/modifier-search?q=` or `/engine-docs/origin/<name>` before referencing in script.
- **Top-level entity collisions are silently dropped** (`Duplicated key X will not be created`). Use `INJECT:X = { ... }` to extend rather than redeclare.
- **`add_modifier` / `remove_modifier` results are not visible inside the same effect block.** Store the prior contribution as a variable and subtract from the `modifier:X` read.
- **`short_modifier_time` / `normal_modifier_time` / `long_modifier_time` / `very_long_modifier_time` are days, not months** (off by 30×). And `any_*` triggers don't accept `limit = { }`.
- **Vanilla auto-registration of dynamic modifier patterns is patchy**. Mod-added buildings, goods, ship types, etc. usually need explicit registration in `common/modifier_type_definitions/`.

---

## When to read which deep doc

| You're touching... | Start with |
|---|---|
| Pops, acceptance, assimilation, qualifications, social hierarchies | `vanilla_pops_reference.md` |
| PMs, wages, goods, IP, capacity, taxes, market pricing, naval economy | `vanilla_economy_reference.md` |
| Laws, IGs, parties, ideologies, movements, characters, institutions, decrees | `vanilla_politics_reference.md` |
| Battles, formations, mobilization, war support, naval combat | `vanilla_war_reference.md` |
| Rank, infamy, interests, plays, treaties, subjects, power blocs | `vanilla_diplomacy_reference.md` |
| Incorporation, infrastructure, capital, turmoil/obstinance/devastation, food/pollution, harvest conditions | `vanilla_states_reference.md` |
| Tech trees, eras, innovation, spread, slingshot | `vanilla_technology_reference.md` |
| Colonies, malaria, native uprising, Colonial Administration, company colonization | `vanilla_colonization_reference.md` |
| Minor / major / special unifications | `vanilla_formable_countries_reference.md` |
| Treaty article designs (existing) | `treaty_articles_reference.md` |
| Wonder buildings (two-phase pattern) | `wonder_buildings_reference.md` |
| Vanilla company building implementations | `vanilla_company_buildings_reference.md` |
| Engine quirks, scope rules, time units, modifier validation | `../guides/scripting_best_practices.md` |
| Engine API reference (data types, scope, file formats) | `modding-reference.md` |
| Vanilla bugs the mod cannot fix | `vanilla_known_bugs.md` |
