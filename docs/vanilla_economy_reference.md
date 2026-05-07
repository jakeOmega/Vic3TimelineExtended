# Vanilla Economy Reference (Victoria 3)

A primer on how the **base game's** economic systems work, written for AI agents that need context before touching mod content. This doc covers vanilla mechanics only — mod-specific systems (banking cycle, construction-cost scaling, migration crowding, etc.) live in `docs/mod_systems.md` and `docs/journal_entry_systems.md`.

> **Last verified against vanilla:** 1.13.4 (Hotfix to "The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. **This doc lives in the same repo as the patch runbook (`docs/vanilla_patch_runbook.md`) — that runbook tells you to revisit this file on every vanilla bump.**
>
> **Verify before relying on names.** Building IDs, modifier names, and good IDs cited below should be verified via the mod state server (`/buildings`, `/raw/Building/<id>`, `/modifier-search?q=`, `/goods`) before you reference them in code. Vanilla renames things across patches.
>
> **This doc captures concepts, not exhaustive lists.** For full ID lists, query the server.
>
> **Numeric content is mechanism, not balance.** Where numbers (a +25% trade-advantage bonus, a starting MAPI of 75%, a base ~20% IP capitalist contribution) clarify *how* a system behaves they're included; opaque internal defines (`RADICALS_MONTHLY_FROM_LOW_SOL = …`) are not. Mechanisms tend to survive vanilla patches; balance numbers don't.

## 1. Geographic and political units

Before anything else: the engine layers political and geographic structures that the rest of this doc references constantly.

| Unit | What it is | Notes |
|---|---|---|
| **Province** | Smallest map cell. | Mostly gameplay-irrelevant; relevant for terrain art, devastation visuals, and a handful of triggers. |
| **State** | A collection of provinces inside one country. | The unit buildings attach to. Where pops, infrastructure, arable land, deposits, and most modifiers live. |
| **State region** | The geographic *outline* of what a state could be. | Most state regions correspond 1:1 with a state. Some are split between countries at game start (e.g. a region shared between two empires); each owner gets a separate state inside the same region. If one country comes to own multiple states inside a region, the engine **merges them** into a single state. |
| **Strategic region** | Group of states (e.g. Western Europe, North China). | Used for AI strategy, weather, climate effects, and some script gates. Not an ownership unit. |
| **Country** | A nation-state. Set of owned states + capital. | The political actor. Holds laws, government, treasury, IP, technology, diplomatic relationships. |
| **Market** | Set of states that share a price-setting machine. | A market sums production and consumption across its member states; the resulting **market price** of each good blends with each state's local supply/demand to set the **local price** that pops and buildings actually pay (see § 13). |

By default one country = one market with the country owner as market owner. Trade agreements, customs unions, power-bloc Market Unification, and vassalage all merge markets — once two countries share a market, their states' supply/demand are aggregated; there is no longer "trade between them", just one larger market with prices set across the whole pool.

## 2. Atomic units: pops, buildings, production methods

| Concept | What it is | Where to look |
|---|---|---|
| **Pop** | Group sharing state + culture + religion + profession + workplace. Provides labor, consumes goods, fuels interest groups. | `common/pop_types/`, `/raw/PopType` |
| **Building** | Physical workplace in a state. | `common/buildings/`, `/buildings` |
| **Production Method (PM)** | A toggleable mode for a building. Sets inputs, outputs, employment, and which modifiers stack. | `common/production_methods/`, `common/production_method_groups/`, `/production-methods` |

Buildings hold `production_method_groups = { ... }`. Each group is a **radio choice** between PMs — a building has one active PM per group at any time. Different groups are independent: their effects **sum**. So a textile mill running "Iron Looms" in its main process group plus "Lit Workplaces" in its workplace-conditions group adds the modifiers from both PMs to the building's total.

Costs/benefits live inside each PM as `building_modifiers = { <scaling> = { goods_input_X_add = N goods_output_Y_add = M } }`. Profession mix lives under `level_scaled = { building_employment_<profession>_add = N }`.

### 2.1 Modifier scaling: `unscaled`, `level_scaled`, `workforce_scaled`

A PM's `building_modifiers` block can hold three scaling groups, each with non-obvious semantics:

- **`unscaled`** — values apply at face value, regardless of building level or staffing. Rare; used for fixed per-building effects.
- **`level_scaled`** — values multiply by **building level only**. Per-level employment slots (`building_employment_laborers_add = 4500`) live here: a level-3 building announces 13,500 laborer slots regardless of how many are filled.
- **`workforce_scaled`** — values multiply by the **fraction of the building's max workforce that is actually employed**. Goods inputs and outputs almost always live here: a half-staffed factory consumes half the inputs and produces half the outputs.

This is the silent mechanism behind "factory not making money": if the state can't fill the slots, `workforce_scaled` outputs scale down proportionally, but level-scaled costs (e.g. some maintenance modifiers) don't. The profession-mix line is *desired* employment, not a hard floor — buildings hire toward it; the actual workforce is whatever the state's labor pool fills.

### 2.2 Modifier scope cascade

A core engine pattern: modifiers can apply at **building / state / country** scope, and country modifiers cascade to all that country's states; state modifiers cascade to all that state's buildings.

Throughput is the canonical example. The same modifier name — `building_throughput_mult` — is read at all three scopes:

- A country-level `building_throughput_mult = 0.05` adds 5% throughput to every building in the country.
- A state-level `building_throughput_mult = 0.05` adds 5% to every building in that state.
- A building-level (or per-PM) `building_throughput_mult = 0.05` adds 5% to that building only.

All three sources stack additively into the same per-building bucket. This pattern repeats across many modifiers (`state_construction_mult`, `state_infrastructure_mult`, etc. — the prefix tells you the *target* scope, but the modifier can be applied higher up and cascade down).

### 2.3 Dynamic-modifier registration trap

Vanilla auto-registers dynamic-modifier patterns (`building_<id>_throughput_add`, `goods_output_<good>_mult`, `state_building_<id>_max_level_add`, etc.) only for *specific axis combinations* per entity. When adding a modded building or good, register the required combinations explicitly in `common/modifier_type_definitions/` — see `docs/scripting_best_practices.md` § dynamic modifier validation. Unregistered modifiers silently no-op.

## 3. The goods system

Goods are defined in `common/goods/00_goods.txt`. Every good has:

- A **base `cost`**, a static integer used by AI valuations and by the engine as the price anchor when supply equals demand. Not the price the market actually sees — that's set by supply and demand on the market (see § 13).
- A **`category`**: one of `military`, `staple`, `industrial`, or `luxury`. Categories are mostly UI grouping; the mechanically meaningful behavior comes from explicit flags below.
- A **`traded_quantity`**, defining how many units one trade-route lane moves. Lower for heavier/bulkier goods, higher for staples.
- A **`prestige_factor`** — base prestige awarded for being top of the leaderboard for that good (× 2 for each rank above the minimum). Military and high-end industrial goods carry larger factors than staples.
- A **`consumption_tax_cost`** — per-good Authority cost to enable a consumption tax on the good. Crucially, this is a **flat cost**, *not* a flow scaled to consumption volume: enabling a tax on a good with `consumption_tax_cost = 400` reserves a flat 400 Authority for as long as the tax is on; turning it off frees the 400 back. High-`consumption_tax_cost` goods (services, grain) are expensive to tax; low-cost goods are cheap. This is the design lever that prevents universal consumption taxation — total Authority is finite, and each enabled tax burns a fixed slice of it.
- Optional flags: `local = yes` (services, transportation, electricity — *not tradeable across states*; price equilibrates only via local production), `fixed_price = yes` and `tradeable = no` (gold), `pop_consumption_can_add_infrastructure = yes` (automobiles), `obsession_chance` (luxury/intoxicants — affects pop demand stickiness).

### 3.1 Local goods are special

Because services, transportation, and electricity can't be shipped, their local price is set entirely by *that state's* supply and demand. Building a power plant only depresses electricity prices in *its* state. This is a major reason why placing services-producing or electricity-producing buildings far from your industry is dead weight: there's no cross-state arbitrage to exploit.

### 3.2 Prestige goods

Prestige goods (`common/prestige_goods/`) are *variants* of a base good — Champagne is a Wine variant, Norwegian Fish is a Fish variant. Buy packages consume them identically to the base good (a pop drinking Champagne consumes from the Wine pool). What they add is a multi-layer benefit:

- **Trade Advantage on the global market** for the producer (see § 14).
- A **prestige bonus** to the producing country.
- A **SoL bonus** to pops that consume them.
- A **throughput bonus** to buildings that consume them as inputs, scaled by the proportion of input value that's prestige (`PRESTIGE_GOODS_INPUT_THROUGHPUT_BONUS = 0.2` in defines, i.e. up to +20% throughput when 100% of a building's input value is prestige goods).
- A **modest combat bonus** to military formations consuming prestige goods (small arms, ammunition, artillery, etc.) as supply.

This four-way value (consumer SoL + producer prestige + downstream factory throughput + military combat) is why prestige goods are valuable across consumer goods (luxury food/drinks), industrial goods (steel, paper), and military goods (small arms, artillery) — there's no good category where they're useless.

Prestige goods are emitted by **companies at full Prosperity** with the relevant prestige good configured (see § 15), not by individual buildings.

## 4. Throughput, employment, automation

### 4.1 Throughput

Throughput is a per-building scalar that uniformly scales every PM input and output (and the goods conversion they encode). The modifier name is **always `building_throughput_mult`** — it's the *scope* it's applied at (country / state / building) that varies. All sources stack additively into one per-building throughput bucket; there is no separate base, just a 1× default that modifiers shift.

Throughput is the lever that company bonuses, "industrial expansion" tech, "well-organized" state modifiers, prestige-good inputs, and several power-bloc principles all push on.

### 4.2 Employment

Each level of a building announces a desired employment per profession (`level_scaled = { building_employment_<profession>_add = N }`). The state's labor pool fills toward that target gradually:

- Pops with higher *qualifications* for the profession (see § 5.5) are preferred.
- Buildings paying higher base wages outcompete buildings paying lower wages — this is what makes urban factories drain peasants out of subsistence.
- Hiring rate is capped per tick by a defines default (`DEFAULT_MIN_HIRING_RATE` / `DEFAULT_MAX_HIRING_RATE`) plus per-building overrides (e.g. subsistence farms set `min_raise_to_hire = 0.30`).

When the labor pool is too thin to fill all desired employment, the building runs understaffed and `workforce_scaled` outputs scale down. Unemployment is *not* always near zero — it becomes common once industrialization has eliminated subsistence farms (no buffer left) and especially when minimum-wage modifiers push base wages above what marginal buildings can profitably pay. In those regimes there are unemployed pops *and* unfilled vacancies simultaneously, with the wage-vs-profitability gap as the bottleneck.

### 4.3 Automation

Many industrial PM groups have an "automation" PM family — `pm_automated_*` variants. Crucially: most automation PMs do **not** increase output per *level*. They increase output per *workforce*. The trade is:

- Reduce headcount of low-skill professions (laborers shrink, sometimes machinists too).
- Add high-skill professions (engineers, more machinists at senior PMs).
- Add inputs of automation goods (electricity, engines, tools).
- The same building level produces about the same amount of stuff — but with fewer workers consuming proportionally more capital goods.

This means automation is **only economical when labor is scarce or expensive**. With a large laborer pool and cheap wages, automation just trades cheap inputs (labor) for expensive ones (electricity / engines). With an exhausted laborer pool and high wages, automation lets a building actually run rather than sit understaffed. Late-game industrial economies arrive at automation by necessity, not preference.

## 5. Pop wealth, SoL, social mobility, radicals/loyalists

### 5.1 Wealth and Standard of Living

**Wealth** is a continuous numeric per-pop scalar. **Standard of Living (SoL)** is a derived display value. The link is direct: a pop sits at the highest *wealth tier* (in `common/buy_packages/`) it can afford given the goods prices in its state, plus any flat SoL modifiers (`state_standard_of_living_add`, prestige-good consumption bonus, etc.). There is no smoothed running average — SoL responds immediately to wealth changes.

There are several engine-side breakpoints in `common/defines/00_defines.txt` where SoL crosses thresholds for population growth, mortality, demographic transition, and visual-asset selection (the "rich SoL" model swap that decides whether a building shows poor or wealthy pops in the UI). These are absolute defines.

### 5.2 Pop needs and substitution

Pop needs (`common/pop_needs/00_pop_needs.txt`) are *categories* — basic food, simple clothing, heating, crude items, household items, standard clothing, services, intoxicants, stimulants, several luxury tiers, leisure, free movement, communication, and others. Each category lists multiple **substitutable goods** with three parameters per entry:

- `weight` — the engine's preference weight for that good within the category.
- `max_supply_share` — cap on the fraction of this category's demand that one good can fulfill.
- `min_supply_share` — floor below which this good will always supply at least a slice (used to keep niche-but-cheap goods relevant).

How the substitution actually resolves (this is the part that catches mod authors out):

- The total *value* a pop spends on a need each week is set by its buy package — the `popneed_X = N` numbers in `common/buy_packages/` are amounts of money, expressed in base-price units, not units of any specific good.
- Within that budget, the split across substitutable goods is driven by **market sell-order share × the good's defined weight**, capped between `min_supply_share` and `max_supply_share`.
- If only one good in the category is available on the market, pops buy that one exclusively (subject to max-share caps).
- If *no* good in the category is on the market, pops fall back to the category's `default` good (e.g. `popneed_simple_clothing` defaults to fabric).
- Goods with a `min_supply_share > 0` are always purchased even if not sold on the market — the engine forces a slice through.
- Higher-base-price goods convert spending into fewer *units* (e.g. oil costs 2× wood, so 1.3 wood worth of heating buys 0.65 oil instead).
- Substitution shifts are throttled — relative shares change between 1% and 10% per week, so a sudden market-share swing doesn't immediately rewrite consumption.

The buy-package weighting math is the reason a mod can't just assume "if I produce more clothes, pops will buy clothes". They will buy clothes *in proportion to the clothes-vs-fabric sell-order ratio × clothes' 2× weight*, capped at `max_supply_share`.

### 5.3 Buy packages

Buy packages (`common/buy_packages/00_buy_packages.txt`) bind a tier of wealth to a need-spend bundle plus a `political_strength` weight. Each tier specifies how much *value* (per 10,000 working adults) a pop in that wealth bracket spends on each *need category*. Climbing the wealth ladder unlocks new categories (luxury food, services, communication, free movement) — this is the demand-side ladder the entire economy chases.

Buy packages are scaled by pop *size*, with dependents counting as half a working adult for needs purposes. So a pop with 20,000 working adults buys twice the standard package; a pop where most members are dependents buys less.

`political_strength` is the per-pop political weight contribution. Wealthier pops carry far more political weight than poor ones — this is the structural reason why suffrage laws (which gate which strata can vote) interact so dramatically with economic outcomes.

This file is **mod-owned** in this repo (`pop_needs_curves.py` regenerates it on `/reload`) — see `docs/auto_generated_files.md`. Don't hand-edit.

### 5.4 Social hierarchies and strata

The 1.13 social-hierarchy system (`common/social_hierarchies/`) layers cultural / religious / legal rules on top of profession to assign a pop to a **strata** — `lower`, `middle`, or `upper`. Strata is queryable via `strata = lower/middle/upper` triggers and feeds:

- A few state-scope SoL bonuses (`state_middle_strata_sol_add`, `state_upper_strata_sol_add`).
- Casualty distribution weights (lower strata absorbs disproportionately).
- Loyalist / radical fraction queries (`loyalist_fraction = { strata = upper }`).

Profession is a strong but not absolute proxy for strata. Laborers are *usually* lower; capitalists are *usually* upper — but there are explicit overrides per hierarchy. Edo-Japan's hierarchy, for instance, places capitalists outside the upper strata; certain caste structures shift middle-class professions around. The hierarchies file is the canonical source — assume the default mapping unless your mod work touches one of the hierarchies that overrides it.

### 5.5 Qualifications and social mobility

Each pop type defines a `qualifications` scripted-value block that scores pops as candidates for that profession. **Qualifications are mostly binary** in current vanilla. A pop of (say) 2,000 laborers might have 100 qualifications for engineers — meaning 100 of them can promote to engineers right now. Once those 100 promote, the remaining 1,900 laborers have 0 engineer qualifications until education, wealth, and literacy build the count back up over time.

This is a known coarseness of the system; Paradox has signaled they intend to refine it. For most player countries outside the early game and outside specific lock-in laws (Serfdom hard-locks peasants out of various professions), it's rarely a binding constraint — qualifications do build up naturally as states industrialize and become literate.

The dominant qualification inputs are wealth, literacy, and cultural-acceptance multipliers. Discriminated cultures qualify at a heavily reduced rate.

### 5.6 Radicals and loyalists

The relationship between SoL and political alignment is more dynamic than "low SoL → radicals":

- **Changes in SoL** drive both directions. A pop whose SoL is *rising* generates loyalists; a pop whose SoL is *falling* generates radicals. This means a country with rapidly rising SoL is politically stable even if its institutions are dysfunctional — the rising tide alone produces loyalist bulk. Conversely, a country with high but stagnant or falling SoL shows up as full of radicals.
- **Sustained low SoL** generates a small but constant trickle of radicals on top of the change-driven flow. Starvation (food security at certain thresholds) generates radicals far faster.
- **Loyalists also come from political wins** — when a movement's preferred law passes, a fraction of supporters convert to loyalists. High legitimacy, certain events, and various other triggers also push loyalists.
- Loyalists and radicals **decay slowly** — roughly the country's death rate, since the channel is generational replacement. This is normally a minor effect: a healthy population with stable politics doesn't rapidly age out its loyalists.
- **Movement radicalism** is a separate per-movement scalar (0–1) that unlocks agitation → protest → militancy → civil-war-eligible thresholds. It is not the same variable as pop radical fraction; movement radicalism rises with the *fraction* of the movement's supporters that are radical and falls with loyalist support, but the two values are stored and queried independently.

This three-layer model (pop wealth → pop loyalist/radical bookkeeping → movement radicalism) is why it's possible to run a high-SoL economy with a militant movement: the radicals come from a discriminated minority or a recent SoL drop, not the median pop.

## 6. Wages and the labor market

### 6.1 Base wage and per-profession multipliers

Each building has a single **base wage**. Each profession has a fixed multiplier on top. So if a building's base wage is £1, it pays its laborers £1, machinists £1.5, engineers £3, and so on. The building can adjust *only* the base wage — the ratios between professions are fixed by pop-type definitions.

Acceptance status further modifies pay: depending on Citizenship and Church-and-State laws, accepted pops are paid more (or less) than discriminated pops in the same profession.

### 6.2 Wage adjustment

Buildings raise their base wage when:

- They can't fill empty positions (the dominant case). Higher wages outbid neighboring buildings for the same labor pool.
- They are very profitable *and* their employees are below expected SoL (and are accepted under current laws).

Buildings lower their base wage when they're unprofitable or only moderately profitable. The result is a slow drift toward equilibrium with a per-tick step cap.

States with a large, well-qualified population tend to settle at *lower* wages until full employment is reached; states with limited qualified labor settle at higher wages. There is a price-war element here, but it's gradient-driven and slow rather than oscillatory.

### 6.3 The "stuck building" pathology

It is perfectly possible for a good to be in shortage, ample buildings to exist, ample qualified workers (even unemployed) to be present, and yet the building is *not hiring*, because its base wage is too high relative to the price the building can clear at. The building's options are to wait for prices to rise back into profitability (slow) or for the player to subsidize it (expensive and treats the symptom, not the cause). This is a recurring late-game economy pain point.

### 6.4 Normal wage

The country-wide average of base wages across incorporated states is the **normal wage**. It's used:

- As the base wage for government-funded buildings (which don't compete in the market for labor).
- As the baseline for welfare payments and minimum-wage law thresholds.

### 6.5 Workforce vs Dependents

Each pop type has a `working_adult_ratio`. Adults in the workforce earn wages; dependents (the rest of the household) earn a small `dependent_wage` from the same household. Triggers like `workforce >= N` and `dependents >= N` index into these.

Pops drift toward their `working_adult_ratio` *slowly*, on the order of years — when conditions change (e.g. urbanization shifts a peasant pop into a profession with a higher working-adult ratio), the actual ratio rebalances over a long horizon, not instantly.

### 6.6 Government and military wages

Bureaucrats and clergy are paid via `law_government_wages_*`; soldiers and officers via `law_military_wages_*`. These wage-level laws don't set absolute pay — they shift government/military pay *relative to the country's normal wage*. "High government wages" gives state employees a premium over the private sector; "low" puts them below.

### 6.7 Subsistence wages

Peasants don't receive a wage in the conventional sense. They live off subsistence-farm output (see § 7) and their wealth is sticky against economic shocks — their SoL barely responds to market-price gyrations because they consume so little from the market. This stickiness is structural to the early game.

## 7. Subsistence farms and peasants

Subsistence buildings (`common/buildings/12_subsistence.txt`) are the engine's way of representing pre-industrial agriculture. They're auto-built in every incorporated state, with one of several variants chosen by terrain/climate:

- `building_subsistence_farm` (grain),
- `building_subsistence_orchard` (fruit),
- `building_subsistence_pasture` (meat),
- `building_subsistence_fishing_village` (fish),
- `building_subsistence_rice_farm` (rice).

Their key flags: `buildable = no`, `expandable = no`, `downsizeable = no`, `slaves_role = peasants`, `ownership_type = self`, `can_switch_owner = no`. The player has zero direct control. Crucially, `ownership_type = self` means peasants own the land they farm — *subsistence buildings don't feed the Investment Pool* (see § 10). The wealth they generate stays with the peasants.

### 7.1 Sizing

The subsistence farm's level is straightforward: **state arable land minus the summed levels of all other rural buildings in the state**. Build a corn farm or a livestock ranch on arable land, and the subsistence farm shrinks one-for-one. Demolish the corn farm and the subsistence building grows back. Modifiers like `state_arable_land_mult` adjust the underlying arable-land pool that this subtraction operates on; certain laws and incorporation status set a floor via `state_minimum_incorporated_subsistence_arable_land_add`.

### 7.2 The drain

Peasants leave subsistence by being **preferentially hired** by other buildings as those buildings expand. Build something in a state that wants laborers/farmers/machinists, and peasants drain out of the subsistence farm into the new workforce. The drain is gated by qualifications — peasants have low qualifications for most non-peasant professions, so they flow predominantly into laborer roles. Higher-qualification urban work has to wait for literate, wealthier pops to promote up from the laborer pool.

### 7.3 The literacy malus

Peasants carry a literacy malus on expected SoL — meaning the wage level a subsistence farm could sustain is systematically lower than what an urban factory pays an equivalently-poor laborer. This is what makes the drain unidirectional: peasants are willing to work for less in subsistence than they would demand in an urban factory, but they're also more willing to leave for a better wage.

## 8. Migration economics

Vanilla has two distinct migration flows: **intra-market migration** between states inside the same market, and **mass migration** between countries (often between markets, but always between countries).

### 8.1 Migration attraction

Migration attraction is a per-state score that drives both flows. Pops generally immigrate to high-attraction states and emigrate from low-attraction ones. The base inputs:

| Source | Effect |
|---|---|
| Per point of average state SoL | +2 |
| Per 10,000 available jobs (capped at 200,000 / +30) | +1.5 |
| Per 10,000 available subsistence jobs (capped at 600,000 / +30; subsistence counted at 75%) | +0.5 |
| Per 10,000 unemployed (capped at 500,000 / -50) | −1 |
| State has no pops at all | +100 |

State traits and various modifiers further multiply the sum. The 75% factor on subsistence reflects the fact that a peasant moving into a subsistence farm is not really "employed" the way a wage worker is.

For **intra-market** moves only, attraction is further boosted for a specific pop:

- +50% if the pop is discriminated in its current state and would be accepted in the target.
- +20% if the target is a cultural homeland for the pop.

### 8.2 Migration laws

A country's Migration law gates flows by acceptance:

| Law | Allowed migrants |
|---|---|
| No Migration Controls | Any acceptance |
| Migration Controls | At least 60 cultural acceptance |
| Closed Borders | Fully accepted only |

Both source and target laws are checked when a pop moves between countries.

The **Land Reform law** further gates peasant migration:

| Law | Peasant migration |
|---|---|
| Serfdom | None |
| Tenant Farmers | Mass migration only |
| Others | Any |

### 8.3 Intra-market migration

Most migration is intra-market — pops moving between states inside the same market.

A pop's **migration desire** is the inverse of its job satisfaction, increased by discriminated status. Highly satisfied accepted pops rarely move; poorly-treated discriminated pops move readily.

For an intra-market move to be possible:

- The target state must have a **cultural community** for the pop's culture. Cultural communities exist in any state with one or more pops of that culture, and can spawn organically each month per a long list of conditions (port, trade center, coastal, primary culture, etc.). A community disappears after three weeks empty.
- A target state must have at least 25% higher migration attraction than the market's average; emigration sources must be at least 25% below average.
- Within those, all states above 75% of the most attractive state's score receive some immigration; pops within 5 points of their current state's attraction don't move.

Move *volume* is roughly 5 × (attraction difference) plus 1 per 100,000 pop, with weekly per-state caps based on infrastructure (`500 + 5 × infrastructure`) and a 0.5%-of-population emigration ceiling. Caps shrink in small states. Unemployment increases the immigration cap.

### 8.4 Cross-power-bloc movement

Intra-market migration is normally bounded by the market. Trade-League power blocs and the principles **Market Unification II** and **Freedom of Movement III** allow intra-market migration to flow across bloc-internal borders. Freedom of Movement also adds +25% migration volume (T1) and +50% mass-migration attraction (T2).

### 8.5 Mass migration

Mass migration triggers when a culture experiences enough turmoil in its homeland country to push pops out at scale. The eligibility conditions:

- The country owns a homeland for the culture.
- That culture has at least 15% turmoil in homeland states.
- At least 100,000 potential emigrants exist.
- Pops without a cultural homeland (e.g. Ashkenazi) can never mass migrate.

When a mass migration triggers, the engine searches for an eligible target state across countries: incorporated, 30%+ market access, 10+ arable land, owner has ≤30% turmoil in the migrating culture. Target countries must trade with the source on the world market, and the migrating culture must have ≥30 acceptance under the target's Citizenship laws. Higher acceptance ratios produce up to 5× more migration. Pops arrive in the chosen state and its neighbors.

Each combination of culture and country has a small weekly chance of triggering a mass migration based on cultural turmoil and on how far below SoL 10 / 5 the culture's average SoL sits.

## 9. The construction sector and queue

### 9.1 Vanilla vs this mod

In **vanilla**, "Construction" is not a market good. Each country has a base **+10** construction points (rulers with the *engineer* trait grant another +5), with more added by Construction Sector buildings.

This **mod** turns Construction into a market good — built and consumed like any other. The sections below describe vanilla's behavior; for the mod's variant see `docs/mod_systems.md`.

### 9.2 The Construction Sector building

A single building type (`building_construction_sector`, in `common/buildings/13_construction.txt`) produces construction points. It has tiered PMs, gated by tech:

- **Wooden buildings** (base) — wood + fabric; small construction output per workforce.
- **Iron-frame buildings** — adds iron and tools; larger output and adds machinists.
- **Steel-frame buildings** — adds steel, glass, explosives; larger still and shifts more mix to skilled labor.
- **Arc-welded buildings** — adds electricity, more tools/explosives; largest output and adds engineers.

The construction sector is itself industrialization-relevant: it employs bureaucrats, clerks, laborers, machinists, engineers — and as it tiers up it consumes more of the same industrial goods it enables building. There's a self-bootstrapping dynamic: a country that runs out of construction goes nowhere; expanding construction sector capacity unlocks the rest of the economy.

### 9.3 Two queues, both first-come-first-served

There are **two construction queues**, both global at the country level: one for **government** construction (paid from the treasury) and one for **private** construction (paid from the Investment Pool). Each is its own first-come-first-served list — buildings get points in the order they were queued, capped each week by a per-building max-progress limit.

The split between queues is set by the **Economic System law**'s `country_private_construction_allocation_mult`: Traditionalism is government-heavy, Laissez-faire / Anarchy is private-heavy. If one queue can't use its full allocation in a given week (e.g. private queue is empty, or IP is short), the *other* queue can automatically use the leftover points.

Critically: the **government queue** is reorderable / pausable by the player. The **private queue is not** — what gets built privately is decided autonomously by the game's investment logic, not by the player. This is a meaningful policy difference: Laissez-faire economies route most construction to a queue the player can't directly steer.

If a building is removed from the queue mid-construction, all progress is lost (no refund or transfer).

### 9.4 Costs and waste

Construction costs are paid in two ways. The construction sector's **wages** (paid from the budget under "Government Wages") run regardless of whether all the points are used — the workforce is paid even on idle weeks. The **goods costs** (wood / fabric / steel / glass / explosives / etc., per the active PM) are only consumed when the points are actually used. Excess construction each week is wasted on the goods-cost side but still costs wages.

Private construction draws from the IP for goods costs; the construction sector workforce is still paid by the treasury. If the IP can't cover the goods cost, the private queue stalls.

### 9.5 Construction efficiency

Construction efficiency is a per-state modifier scaling how many *progress* points each construction point delivers. Sources stack additively into a single bucket:

- Local construction sectors (more advanced PMs = more efficiency per level).
- Road Maintenance decree (+10%).
- Construction I principle (+10%).
- Surplus Bureaucracy (up to +10% at 100% surplus).
- State traits (mountains, deserts → negative).
- Unincorporated penalty (varies by building type — heavy industry suffers most; military/agriculture/art academies are exempt).
- Turmoil and devastation (negative, scaling with severity).
- Trade Union "work-to-rule" trait (-15% nationwide).
- Bankruptcy (-75% nationwide).
- Various events and characters.

The minimum is 5% (a state can't go below that, even under bankruptcy + devastation). All sources fold into one additive bucket — there's no nested multiplication of construction-sector output × state efficiency × company efficiency; they all sum.

## 10. Ownership and the investment pool

The pre-1.5 model where capitalists/aristocrats "worked in the factory" via PM categories is **gone**. Ownership is now a separate building dimension.

### 10.1 Owner types per building level

Every building level has exactly one owner:

| Owner | Source | Where dividends flow |
|---|---|---|
| `building_manor_house` | Land-based capital (farms, plantations, mines, logging camps) | Aristocrats employed in the Manor House |
| `building_financial_district` | Urban / industrial capital (factories, urban services, ports) | Capitalists / shopkeepers in the Financial District |
| Worker-owned | Pop class running the building | The workforce directly (under cooperative laws) |
| Country-owned | The state | National treasury |
| Self-owned | Peasants on subsistence farms | Stays with the peasants (see § 7) |

Ownership shifts via privatization (state → owner-building) and nationalization (owner-building → state). Both are gated by economic-system law. Privatization requires sufficient IP funds; nationalization requires sufficient treasury (and may incur radicalization).

### 10.2 The Investment Pool (IP)

A second treasury fed by **a fraction of dividend income** from owner-class pops. The principal feeders:

- **Capitalists** — primary source. Their pop type is configured `paid_private_wage = no` — all their income is dividends, not wages. Roughly 20% of capitalist dividends flow into IP at base; this rate is shifted by per-state per-pop-type modifiers like `state_capitalists_investment_pool_contribution_add` (e.g. +0.05 → ~25% — a meaningful change at scale).
- **Aristocrats** — secondary source, also via the +20%-base / per-state-modifier pattern.
- **Shopkeepers** — feed indirectly via certain ownership types on smaller buildings.
- **Academics** — *do not contribute at baseline* in vanilla. The lever exists (`state_academics_investment_pool_contribution_add`), but it sits at 0 by default; only laws or events that move it positive opt academics in. Easy one to get wrong because the modifier exists in the catalog and looks symmetric with the capitalist lever — but symmetric existence ≠ symmetric activation.

What the IP is used for:

- Building new levels of privately-owned buildings.
- Paying for privatization of state-owned levels.
- Foreign investment into other countries (when allowed by laws / power-bloc principles).

Critically, the player **does not directly control** what the IP builds, where, or in what order. Investment selection is autonomous: the engine picks projects based on profitability scoring. The player influences this only through laws, principles, tariffs, and what ownership types are allowed — never by clicking a build button on the private queue.

### 10.3 Bootstrapping

Small economies receive an IP efficiency boost so industrialization isn't dead-on-arrival. The exact scaling is opaque but the bonus is real and visible on the IP tooltip.

Note that `country_weekly_investment_pool_add` and `country_weekly_investment_pool_mult` are **mod-added** modifiers in this repo — they're driven by on-actions and don't exist in vanilla. Don't reference them when reasoning about base-game IP behavior.

### 10.4 Useful queries

- Who owns what type of building? `/raw/Building/<id>` and look at `building_group` plus the `Manor House` / `Financial District` definitions.
- IP-related triggers/effects: `/engine-docs/triggers?q=investment` and `/engine-docs/effects?q=invest`.
- `investment_pool_gross_income` vs `investment_pool_net_income` triggers — the gap encodes IP-side expenses (which include foreign-investment outflows).

## 11. Capacity resources: Bureaucracy, Authority, Influence

These three are not pooled like money or the Investment Pool. Each is a *flow* — constant monthly generation racing constant monthly usage. Surpluses and deficits scale a benefit/penalty modifier proportional to the relative gap, capped at half-or-less usage (full surplus) or twice-or-more usage (full deficit). Most actions that *spend* a capacity require the full amount currently available; producing a *deficit* doesn't auto-cancel anything — the penalty just leaks while you're under.

All three start at +100 base. Society techs, happy/powerful IGs, certain monuments, and event modifiers add percentage bonuses on top.

### 11.1 Bureaucracy

Generated by **Government Administration** buildings — the dedicated state-level producer. Petite Bourgeoisie's *Middle Managers* trait adds +10% if they're happy or +20% if they're powerful.

Spent on:

- **Incorporated states** — base 10 per state plus 1 per 25,000 population. The cost applies *during* incorporation, before the new state's own bureaucracy contribution kicks in.
- **Institutions** — 1 per institution level per 100,000 population in incorporated states (minimum 10/level).
- **Buildings** — 1 per nationally-owned building level. Privately-owned buildings don't count.
- **Generals and admirals** — base 10, +5 per promotion to a max of 30.
- **Various journal entries / events** (e.g. surveying the Suez Canal).

A surplus ("Efficient Bureaucracy") gives up to **+10% State Construction Efficiency** at full surplus. A deficit ("Administrative Overburden") imposes up to **+100% Government Dividends Waste** and **+100% Tax Waste** at full deficit — meaning a country running half its bureaucracy short loses meaningful tax revenue. This is one of the few places where being deficit-tolerant is actively expensive in money terms.

### 11.2 Authority

Generated mostly by **laws** — more authoritarian / repressive law combinations generate more Authority. The country's **ruler** also adds or subtracts Authority equal to their political popularity (a 50-popularity ruler grants +50, a -30-popularity ruler costs 30). Society techs (Mass Communication, Nationalism, Pan-Nationalism, Political Agitation, Mass Propaganda) add a cumulative +50%; Devout's *Divine Right* trait adds +10% (happy) or +20% (powerful).

The law groups that produce Authority:

- Governance Principles
- Distribution of Power
- Church and State
- Citizenship
- Economic System
- Trade Policy
- Free Speech

Spent on (all of these are **flat-while-active reservations**, not one-shot or metered — Authority is freed back when the feature is turned off):

- **Decrees** — 100 each for most, reserved as long as the decree is on a state. Multiple states each carrying the same decree each pay their own reservation.
- **Bolstering / suppressing political movements** — 200 each, reserved while active.
- **Consumption taxes** — 100–500 per taxed good while the tax is on, set by the good's `consumption_tax_cost`. Reserved up-front, not metered against consumption volume. This is the cost lever from § 3 — taxing the most heavily-consumed goods (services, grain, clothes) is expensive in Authority and forces choices about which goods to tax.
- **Corporate charters above the slot limit** — 100 each while the charter is granted.
- **State monopoly on a building** — 100 while the monopoly is in force.

The *cumulative* nature of Authority spending matters: a country juggling many decrees, a few consumption taxes, an active suppress on an opposing movement, and a couple of monopolies can blow through its Authority budget even though no single decision was expensive. Authority is a portfolio, not a one-time payment.

A surplus ("Legislative Efficiency") gives up to **−25% Enactment Time** at full surplus — laws pass faster. A deficit ("Political Dysfunction") imposes up to **−10 Opposition IG Approval** and **+20% Radicals from Political Movements** at full deficit. So Authority management both speeds law passage and dampens unrest; a country in deep deficit is silently feeding its own opposition.

### 11.3 Influence

Generated mostly by **country rank**:

| Rank | Influence | Diplomatic pact cost mod |
|---|---|---|
| Great Power | 1000 | +100% |
| Major Power (recognized) | 750 | +50% |
| Major Power (unrecognized) | 750 | +0% |
| Minor Power | 600 | +0% |
| Regional Power (unrecognized) | 600 | −25% |
| Insignificant | 500 | +0% |
| Unrecognized | 500 | −50% |

Rivalries, certain monuments, and journal entries also add Influence. Landowners' happy *Family Ties* trait adds +10% (powerful: +20%).

Spent entirely on **establishing and maintaining diplomatic pacts** — alliances, defensive pacts, customs unions, trade agreements, foreign investment rights, etc. Total cost = listed pact cost × the rank multiplier above.

A surplus ("Diplomatic Mitigation") gives up to **+25% Infamy Decay** and **+25% Leverage Generation** at full surplus. A deficit ("Diplomatic Overreach") imposes up to **−50% Prestige** at full deficit — overcommitting to pacts visibly tanks the country's standing on the world stage.

### 11.4 Mod-work implications

Three patterns worth knowing when authoring or auditing mod systems:

- **Per-building bureaucracy stacking is fine — but only because it's `_add`.** A per-PM `country_bureaucracy_add = -10` in a `workforce_scaled` block is bounded by total building count and won't go pathological. The same building authoring `country_bureaucracy_mult = -0.05` per level *would* be pathological — see `CLAUDE.md` § "Modifier stacking is additive across all sources". The same logic applies to `country_authority_add` and `country_influence_add` per-building drains.
- **`consumption_tax_cost` is a flat per-good Authority reservation.** Enabling a consumption tax on a good locks in `consumption_tax_cost` Authority (typically 100–500) for as long as the tax is on; the cost doesn't scale with consumption volume. Mod-added goods that pops consume in volume still need realistic `consumption_tax_cost` values, or they become cheap-to-tax and break the Authority-as-finite-resource design — but the cost is paid up-front, not metered.
- **Influence is rank-pegged, not economy-pegged.** No matter how much money or IP a country has, its diplomatic budget is set by rank and a handful of multipliers. Mod features that lean on diplomatic pacts (treaty articles, custom diplomatic actions) need to fit inside a Great Power's ~1000-point Influence budget if they're meant to be played by majors-and-up. If a mod adds many new pacts, run an Influence accounting check before assuming they're all simultaneously available.

## 12. Taxes and government revenue

### 12.1 The five tax dials

Tax laws in `common/laws/` enable some combination of these levers:

| Dial | Applied to | Modifier |
|---|---|---|
| **Consumption tax** | Per-good purchases by pops; flat per-good Authority enable cost (`consumption_tax_cost`); revenue scales with consumption | `tax_consumption_add` |
| **Income tax** | Wages of employed pops | `tax_income_add` |
| **Dividend tax** | Capitalist / aristocrat dividends | `tax_dividends_add` |
| **Land tax** | Peasants in rural buildings | `tax_land_add` |
| **Per-capita tax** | Non-peasants | `tax_per_capita_add` |

Tax law families decide which dials are nonzero. Tax level (low / medium / high) scales them within a family.

### 12.2 Consumption tax is paid in Authority

Important nuance: when the player enables a consumption tax on a good, the country **reserves a flat Authority cost** equal to the good's `consumption_tax_cost` (typically 100–500). This is *not* metered against consumption volume — it's a fixed reservation that lasts as long as the tax is on, and is freed instantly if the tax is turned off. Authority is a separate country resource (it also gates decrees, edicts, and IG suppression), and it is *finite*. This is the design lever that prevents universal consumption taxation — the ledger isn't measured in money, it's measured in a scarce political resource that the player must allocate per-good.

The tax *revenue* still lands in the treasury as money and *does* scale with consumption volume. Only the *enable cost* is flat.

### 12.3 Tariffs are not a tax dial

Tariffs are a separate revenue stream tied to flows through the trade system; they're not a flat tax. They piggyback on directional good flows — see § 14.

### 12.4 Government dividends

Dividends from nationalized buildings flow to the treasury rather than to a Financial District / Manor House. Two modifiers tune the cut:

- `country_government_dividends_efficiency_add` — fraction of profits collected vs leaked.
- `country_government_dividends_reinvestment_add` — fraction reinvested into building expansion vs banked into the treasury.

A high reinvestment rate makes nationalized buildings into auto-expanding state assets at the cost of revenue.

### 12.5 Expense lines

The treasury pays out:

- **Government wages** — bureaucrats and clergy (scaled by `government_wage_level` relative to the normal wage).
- **Military wages** — soldiers and officers (scaled by `military_wage_level`).
- **Building subsidies** — when the player flags a subsidized building or when a building is `subsidized = yes` by group.
- **Construction Sector wages** — even when construction points sit unused (see § 9.4).
- **Interest on debt** — when running negative.
- **On-action / event flat costs** — diplomatic plays, character upkeep, etc.

## 13. Markets and the pricing engine

A **Market** is a customs union of states (default: one country = one market; trade agreements / power blocs / vassalage merge them). It owns the price-setting machinery.

When two countries' markets merge (Customs Union treaty article, Market Unification T2, vassalage), they become a *single* market: production and consumption from all states sum into one price-setting pool, the larger market sets one market price per good, and there is no more "trade between" the merged markets — they're one market.

### 13.1 Local price vs market price

Every state has its own **local price** for every good. That's what local pops and buildings actually pay/receive. Two inputs determine it:

1. **Market price** — supply/demand averaged across the whole market (sum of all member states' production and consumption).
2. **Isolated state price** — what the state's price would be if it were sealed off (purely local supply/demand).

The blend is gated by **Market Access (MA)** for that state — a per-state percentage driven by infrastructure. Effective access into the market price is further attenuated by **Market Access Price Impact (MAPI)** modifiers:

```
local_price = MAPI × market_price + (1 - MAPI) × isolated_state_price
```

MAPI starts at **75%** (engine default) and increases additively from technology unlocks (Stock Exchange, Telephones, etc.) and economic laws — a +5% MAPI tech brings it to 80%, not 75% × 1.05. **Implication:** local price almost always lags market price, so cross-state shipping silently destroys value. This is the in-engine pressure toward **vertical integration** — colocate inputs and outputs in the same state.

### 13.2 Infrastructure

MA is upstream of infrastructure. Infrastructure is a per-state scalar with two halves:

- **Capacity** — produced by **Railways** and **Ports** (each PM tier of each producer adds more). Capacity is strictly per-state, no spillover.
- **Usage** — consumed by every production building, scaling with level, throughput, and active workforce. Trade Centers consume infrastructure too.

When **usage exceeds capacity**, MA degrades, construction in the state slows, and a visible warning appears. The player's response is to build more railways (or more ports in coastal states) to expand capacity. Some buildings reduce their own infrastructure usage at higher PMs as a kind of efficiency upgrade.

### 13.3 Useful triggers

`market_access`, `infrastructure`, `infrastructure_usage`, `infrastructure_capacity`, `relative_infrastructure`, `world_market_access` — all expose state and country properties for script-side gating.

## 14. Trade between markets

Pre-1.5 manual trade routes are gone. In 1.13, trade between *separate* markets (i.e. countries not in a customs union) is autonomous, driven by Trade Centers and the Trade Advantage formula.

### 14.1 Trade Centers

**Trade Centers** are standalone buildings (in the Private Infrastructure family — `common/buildings/11_private_infrastructure.txt`). They are *not* sub-buildings inside Ports. They:

- **Produce trade capacity** (`state_weekly_trades_add`, `state_trade_capacity_add`) — the state's ability to host trade routes.
- **Consume Merchant Marine** at a rate that scales with their PM tier.
- Stack additively per state, gated by trade laws.

Trade Centers don't pick routes themselves; they make a state *eligible* to host routes the engine creates autonomously.

### 14.2 Trade Advantage

**Trade Advantage** is the per-flow multiplier the engine uses to decide whether a route happens (and at what volume). It's a zero-sum game across the world market: gaining trade advantage on a good means others lose it. At 100% trade advantage, the producer gets a 25% better price than baseline.

The full formula (per the wiki):

| Component | Effect |
|---|---|
| **Base** | 100 |
| Per % of global production *within* the market area | +2 |
| Per % of in-market production controlled by a company with **trade rights** | +0.5 |
| Per % of production that is **prestige goods** (export advantage only) | +1 |
| Per % of trade going to a country with **trade privileges** | +1 |
| Per % of trade going to a Trade Center in a **treaty port** | +2 |
| Per % of trade going to a country lacking interest with the trade-center owner | −0.5 (suppressed by **External Trade III**) |
| Per % of trade with a country at war with the trade-center owner | −0.75 |
| Per % of trade going to a country that is embargoing the trade-center owner | −1 |

Plus flat percentage bonuses:

- **External Trade I** principle: +25%.
- Trade centers in the market capital: +5%.
- Trade-law-dependent: up to +25%.
- Up to +0.5% per 100 trade capacity in the trade center (cap +20%, modified by banking techs).
- Trade Policy law modifies overall trade capacity.

Separately, world-market price has a **monopoly bonus**: if one market controls 100% of exports, the world-market price is 20% higher; this scales with share, so 50% control → 10% higher price. Trade advantage doesn't affect the price under monopoly conditions — the producer just gets the elevated price for being the only seller.

### 14.3 Tariffs and subventions

Both are **per-good per-direction** (import / export), set at the country level:

- **Tariffs** tax the flow and divert revenue to the treasury. They reduce the effective price the buyer/seller sees.
- **Subventions** are inverse tariffs — government pays to encourage the flow, boosting the effective price for the producer or reducing it for the buyer.

Both stack with Trade Advantage; they don't replace it. The exact resolution order — whether tariffs apply to the trade-advantage-multiplied flow or before trade advantage resolves — is one of the open questions in § 19.

### 14.4 Embargoes and treaty articles

Treaty articles can:

- **Block trade flows entirely** between specific market pairs (`prohibit_trade_with_global_market`). Bound by infamy/relations costs and treaty maintenance.
- **Forbid tariffs** between two countries (no-tariffs article).
- **Forbid subventions** between two countries (no-subventions article).

Customs unions (negotiated bilaterally or imposed via Market Unification T2) don't merely block tariffs — they merge the two markets entirely (see § 13). After merge, there is no longer trade *between* the merged countries; their states' supply/demand combine into a single market price.

## 15. Companies, prosperity, prestige goods

A country has a fixed number of **Company Slots** unlocked by society techs. Companies are persistent agents that:

- Specialize in 2–4 building types each (defined in `common/company_types/`).
- Provide throughput / construction-efficiency bonuses to their associated industries.
- Earn **Prosperity** when profitable.

### 15.1 Prosperity

Prosperity is a per-company scalar (`common/script_values/company_values.txt`). Inputs:

- **Productivity** relative to a global benchmark — high-margin companies score high.
- **Employed levels** — how many levels of buildings in the company's roster are staffed.
- **Executive popularity** — if the company has an executive, their popularity feeds prosperity (positive or negative).

Prosperity rises and falls weekly based on these drivers. There is no negative penalty for low prosperity beyond losing the bonus.

### 15.2 Prestige good emission

When a company reaches full Prosperity *and* has a prestige good configured (`possible_prestige_goods` in its company type), it begins emitting that good. The emission persists as long as Prosperity stays at the top — drop below the threshold and the company stops emitting.

The prestige good then provides the four-way bonuses discussed in § 3.2 (consumer SoL + producer prestige + factory throughput + military combat).

### 15.3 Charters

States can grant Charters to companies to expand reach:

| Charter | Effect |
|---|---|
| Industry | Adds extra building types to the company's roster |
| Trade | Enables company-owned Trade Centers to profit from international exports |
| Investment | Allows the company to set up regional HQs in foreign countries; requires Foreign Investment Rights or subjects |
| Colonization | Speed bonus to colonizing a target state. Sustained colonization can convert the state into a "Chartered Company" semi-independent country |
| Monopoly | Permanent variant gated on the company producing prestige goods |

**Companies can have only one industry-expansion Charter active at a time** in current vanilla — granting a new industry charter retires the previous one. (Trade / Investment / Colonization / Monopoly are independent of the industry-expansion slot.) Most charters carry multi-year cooldowns between grants.

Where to look: `common/company_types/`, `common/company_charter_types/`, `/raw/CompanyType`.

## 16. Power Blocs, principles, mandates

Introduced by *Sphere of Influence* and substantially extended in 1.13. A Power Bloc is a group of countries under a single leader.

### 16.1 Mandate flow

Mandates accrue weekly to the leader, scaled by leader rank and member tier composition (Great Power members contribute more than Major / Minor / Unrecognized). Higher-rank leaders generate fewer per-rank-base mandates — there's a leader-tier-mandate tradeoff, so being the leader of a small bloc as a Great Power doesn't print mandates. Leaders spend mandates to unlock principle tier upgrades.

### 16.2 Principle tiers

Each principle group has three tiers. T1 is unlocked as a baseline once the bloc adopts the group. T2 and T3 each cost mandates. Principles bind to the bloc and their `member_modifier` blocks apply to every member; some carry a `power_bloc_modifier` block (bloc-wide) and a `leader_modifier` block (leader only) as well.

### 16.3 Cohesion

Cohesion is the bloc's stability gauge. Members at low cohesion risk defection. The decay drivers — ideology drift, economic divergence, unmet member interests, leader rank changes — are partly engine-side. Cohesion is the source of pressure that keeps blocs from being free passive bonuses; it must be actively maintained.

### 16.4 Economically-relevant principle families

| Group | T1 | T2 | T3 |
|---|---|---|---|
| **Construction** | State-construction bonus | Construction sectors use less infrastructure | Members can form Construction-type companies |
| **Internal Trade** | Port throughput + state infrastructure bonus | Adds company throughput bonus | Cheaper port connections |
| **Market Unification** | Trade-advantage bonus inside bloc + can't embargo bloc members | Customs union (markets merge) | Supply-ship efficiency bonus |
| **Foreign Investment** | Higher leverage from economic dependence | Tiered investment-rights expansion | (further leverage tiers) |
| **External Trade** | Trade-advantage bonuses to bloc-external flows | (tier-specific) | Removes the "lacking interest" trade-advantage penalty |
| **Freedom of Movement** | +25% migration volume; bloc-internal intra-market migration | +50% mass-migration attraction | (further) |

There are also non-economic groups (ideology, military integration, religious unity). The full list lives in `common/power_bloc_principles/00_power_bloc_principles.txt`.

## 17. The Naval Economy (1.13)

In "The Great Wave" the navy was integrated into the economic loop. **Convoys are gone.** Treat the following as the new defaults:

| Resource | Type | Source | Sink |
|---|---|---|---|
| **Merchant Marine** | Market good | Ports (in vanilla) | Trade Centers, overseas state market access |
| **Naval Construction** | Market good | Shipyards (optionally subsidized) | Ship maintenance / refit |
| **Ship Construction** | Market good | Shipyards | Building new ship instances |
| **Supply Ships** | Military asset | Military budget | Overseas formations' supply line |

### 17.1 Merchant Marine (Bulk Transportation in this mod)

In vanilla, **Merchant Marine** is a market good produced by Ports and consumed by Trade Centers and overseas market access. Running short doesn't cause a discrete cliff: the shortage **raises the good's price**, which makes Trade Centers less profitable, which causes them to **downsize their trade routes** and reduce consumption. The system rebalances via the standard supply-and-demand price loop, not a hard cap.

This **mod** relocalizes Merchant Marine to **"Bulk Transportation"** (per `localization/english/replace/timeline_extended_override_l_english.yml`) and broadens **production**: in addition to vanilla Ports, the good is now produced by Railways (all train tiers), Motorways/Highways (all road tiers), Airports, Spaceports, and a handful of trade/logistics flavored company buildings (trading houses, fulfillment centers, shipyards, logistics hubs). Construction sectors and rail-transport extraction PMs (logging, mines, oil rigs, refrigerated agriculture, etc.) **consume** it — they don't produce it. The mod-side rationale is that overseas merchant shipping isn't conceptually separate from rail- and road-haul logistics; the same good models both. The underlying engine ID is still `merchant_marine`. Cross-references: `docs/mod_systems.md` § "Bulk Transportation" for the full producer/consumer inventory.

There's a prestige-good variant (`prestige_good_generic_merchant_marine`) that select shipping companies emit at full Prosperity.

### 17.2 Naval Construction vs Ship Construction

Despite similar names these are different goods:

- **Ship Construction** is the build-time input consumed when building a new ship instance. Shipyards produce it; they consume Engines, Steel, and other industrial goods at higher PMs.
- **Naval Construction** is the maintenance-flow input that keeps existing ships supplied and refit. Also produced by Shipyards, optionally subsidized so it doesn't have to be profitable on its own.

Both are market goods coming out of the shipyard family; they're not the same as the country's military *budget*, though the budget pays for the underlying ships.

### 17.3 Ship instances

Ships are physical assets, not abstract "naval power". They:

- Cost Ship Construction (and various input goods via shipyards) to build.
- Require ongoing Naval Construction maintenance.
- Live inside fleets attached to a country's military formations.

### 17.4 Supply Ships

Supply Ships are a military asset attached to formations operating overseas. Insufficient supply ships → attrition + organization loss → reduced combat effectiveness on the formation. There's no civilian-good production path for Supply Ships specifically; their capacity is a function of naval admin / shipyard capacity and the military budget.

### 17.5 Ship Designer

The Ship Designer is a runtime UI exposed by the engine — it's not data-driven (no PMs configure it). Players tune hull size, armor, armament, and supply capacity per ship type via slot-level choices (low / medium / high, plus wildcard slots).

Costs scale **non-linearly with total modification level**: low = 1, medium = 2, high = 3, wildcard = 1. The sum of these levels across slots, multiplied by the modifications' base costs and an exponential-growth term, drives the final Ship Construction cost. Roughly: an "all medium" ship costs ~2× an "all light" ship of the same type, an "all high" ship costs ~2× an "all medium" — the same exponential curve applies across all axes (armor / firepower / supply / etc.), not a different curve per stat. The Ship Designer UI displays this graph for the player.

When the mod adds new `ship_type_*` entities, register the relevant `ship_battle_against_ship_type_<ship>_<axis>_<add|mult>` combinations explicitly per the rule in `docs/scripting_best_practices.md` — vanilla auto-registration is patchy.

### 17.6 Gunboat diplomacy

During a diplomatic play, navies can threaten **Naval Hostilities**. If the target refuses, the aggressor can conduct **Port Bombardment**, which:

- Inflicts devastation in coastal target states.
- Can physically destroy buildings (particularly ports and shipyards).

This is the canonical pre-war coercion path for naval-heavy nations.

## 18. Cross-references for agents

- **Concrete IDs** (laws, buildings, goods, modifiers): query `mod_state_server` (`/buildings`, `/laws`, `/goods`, `/modifier-search?q=`).
- **Engine syntax & validation rules:** `docs/scripting_best_practices.md`.
- **Mod systems that hook these vanilla mechanics:** `docs/mod_systems.md`, `docs/journal_entry_systems.md`. Banking cycle (IP/dividend pressure), construction-as-a-good (mod's market-mediated construction layer over the vanilla two-FCFS queues), tourism (state-scope dynamic modifiers), wonder buildings (long-build construction-good drains), migration crowding (per-state pull modifiers), Bulk Transportation (Merchant Marine relocalization + broadened production).
- **Vanilla company / charter implementations:** `docs/vanilla_company_buildings_reference.md`.
- **What changed at the last vanilla bump:** `docs/vanilla_patch_runbook.md` § "Engine-doc diff" and § "Known vanilla renames".

## 19. Open questions

A short list of mechanics where the data files alone don't establish the answer and the user hasn't yet confirmed. When these get answered, fold them into the relevant body section and remove the bullet here.

- **Wage adjustment cadence.** Likely weekly, but the engine's wage-update logic is not very transparent. The "expected SoL" anchor each building uses for its raise/lower decisions probably varies per-pop with literacy / culture, but the per-input weighting isn't fully exposed.
- **Tariff timing in trade math.** Does the tariff rate apply *to* the trade-advantage-multiplied flow, or *before* trade advantage resolves? Worth re-checking against in-game behavior; user has flagged this for follow-up in a later draft.

## 20. Maintenance protocol

This doc captures vanilla concepts at a point in time. To keep it useful:

1. **On every vanilla patch:** the runbook in `docs/vanilla_patch_runbook.md` instructs whoever performs the migration to revisit this file. Update the version banner at the top, and edit any section where 1.x semantics changed (new resource types, removed mechanics, new principle families, restructured ownership). Don't fork a separate "1.14 economy" doc — overwrite.
2. **On discovering a new mechanic mid-development:** when an agent learns something generally applicable about how vanilla economics work (e.g. a non-obvious Trade Advantage modifier, a hidden charter constraint, a Market Unification edge case), add it here in the relevant section. Keep additions short — one paragraph, not a treatise. The bar from `CLAUDE.md` § "Recording lessons learned" applies: would the next agent hit the same gap from scratch?
3. **On answering an Open Question:** when § 19 gets answered, fold the answer into the relevant body section and delete the bullet. § 19 is a backlog, not a permanent fixture.
4. **Don't duplicate:** modifier validation rules, scope chain quirks, and engine-syntax gotchas belong in `docs/scripting_best_practices.md`. This file is *concepts*, not *syntax*.
5. **Numbers when they're mechanism, not when they're balance.** Specific defines that drift each patch (radicalization rates, exact wage step caps) should stay out. Numbers that *define the mechanism* (the +2-per-SoL migration coefficient, the 75% MAPI default, the +25% trade-advantage at 100%, the ~20% IP capitalist contribution) are fair game when they make the mechanic clearer.
