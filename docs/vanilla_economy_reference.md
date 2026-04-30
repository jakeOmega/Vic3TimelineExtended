# Vanilla Economy Reference (Victoria 3)

A primer on how the **base game's** economic systems work, written for AI agents that need context before touching mod content. This doc covers vanilla mechanics only — mod-specific systems (banking cycle, construction-cost scaling, migration crowding, etc.) live in `docs/mod_systems.md` and `docs/journal_entry_systems.md`.

> **Last verified against vanilla:** 1.13 ("The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. **This doc lives in the same repo as the patch runbook (`docs/vanilla_patch_runbook.md`) — that runbook tells you to revisit this file on every vanilla bump.**
>
> **Verify before relying on names.** Building IDs, modifier names, and good IDs cited below should be verified via the mod state server (`/buildings`, `/raw/Building/<id>`, `/modifier-search?q=`, `/goods`) before you reference them in code. Vanilla renames things across patches.
>
> **This doc captures concepts, not exhaustive lists.** For full ID lists, query the server.

## 1. Atomic units: pops, buildings, production methods

| Concept | What it is | Where to look |
|---|---|---|
| **Pop** | Group sharing state + culture + religion + profession + workplace. Provides labor, consumes goods, fuels interest groups. | `common/pop_types/`, `/raw/PopType` |
| **Building** | Physical workplace in a state (Urban / Rural / Extraction / Military / Development / Government). | `common/buildings/`, `/buildings` |
| **Production Method (PM)** | A toggleable mode for a building. Sets inputs, outputs, employment, and which modifiers stack. Each building exposes several PM groups; each group is a radio choice between PMs. | `common/production_methods/`, `common/production_method_groups/`, `/production-methods` |

Buildings hold `production_method_groups = { ... }`. PM groups hold `production_methods = { ... }`. Costs/benefits live inside each PM as `building_modifiers = { workforce_scaled = { goods_input_X_add = N goods_output_Y_add = M } }`. Profession mix lives under `level_scaled = { building_employment_<profession>_add = N }`.

**Common pitfall:** vanilla auto-registers dynamic-modifier patterns (`building_<id>_throughput_add`, `goods_output_<good>_mult`, `state_building_<id>_max_level_add`, etc.) only for *specific axis combinations* per entity. When adding a modded building or good, register required combinations explicitly in `common/modifier_type_definitions/` — see `docs/scripting_best_practices.md` § dynamic modifier validation.

## 2. Pop wealth, social hierarchies, consumption

- **Wealth** is a numeric per-pop value. **Standard of Living (SoL)** is a derived display value. Wealth rises when income (wages + dividends + interest, minus investment-pool contribution and taxes) > expenses.
- **Social hierarchies** (1.13) determine **Lower / Middle / Upper strata** by combining profession, culture, religion, and law. See `common/social_hierarchies/` and `/raw/SocialHierarchy`.
- **Buy packages** (`common/buy_packages/00_buy_packages.txt`) define the per-need goods volume for each wealth level (per 10k working adults). Need categories include staple food, intoxicants, luxury items, services, etc. As wealth climbs, demand shifts from staple goods (grain, fabric) toward luxuries (wine, luxury clothes, porcelain, radios).
- This file is **mod-owned** (`pop_needs_curves.py` regenerates it on `/reload`) — see `docs/auto_generated_files.md`. Don't hand-edit.

## 3. Construction, ownership, the investment pool

The pre-1.5 model where capitalists/aristocrats "worked in the factory" via PM categories is **gone**. Ownership is now a separate building dimension.

### 3.1 Owner types per building level

Every building level has exactly one owner:

| Owner | Source | Where dividends flow |
|---|---|---|
| `building_manor_house` | Land-based capital (farms, plantations, mines, logging camps) | Aristocrats employed in the Manor House |
| `building_financial_district` | Urban / industrial capital (factories, urban services, ports) | Capitalists / shopkeepers in the Financial District |
| Worker-owned | Pop class running the building | The workforce directly (under cooperative laws) |
| Country-owned | The state | National treasury |

Ownership shifts via privatization (state → owner-building) and nationalization (owner-building → state). Both are gated by economic-system law and by available investment-pool funds (for privatization).

### 3.2 The Investment Pool (IP)

A second treasury fed by **a fraction of dividend income** from owner-class pops (typically capitalists and aristocrats) **before taxes**. Used for:

- Building new levels of privately-owned buildings
- Paying for privatization of state-owned levels
- Foreign investment into other countries (when allowed by laws / power bloc principles)

In small economies the IP receives an efficiency bonus to bootstrap industrialization. The **mod-side** "excess private construction" / "construction cost scaling" systems hook the IP indirectly via construction-good costs — see `docs/mod_systems.md`.

### 3.3 Useful queries

- Who owns what type of building? `/raw/Building/<id>` and look at `building_group` plus the `Manor House` / `Financial District` definitions.
- IP-related triggers/effects: `/engine-docs/triggers?q=investment` and `/engine-docs/effects?q=invest`.

## 4. Markets and the pricing engine

A **Market** is a customs union of states (default: one country = one market; trade agreements / power blocs / vassalage merge them). It owns the price-setting machinery.

### 4.1 Local price vs. market price

Every state has its own **local price** for every good. That's what local pops and buildings actually pay/receive. Two inputs determine it:

1. **Market price** — supply/demand averaged across the whole market.
2. **Isolated state price** — what the state's price would be if it were sealed off (purely local supply/demand).

The blend is gated by **Market Access (MA)** for that state — a per-state percentage driven by infrastructure. Effective access into the market price is further attenuated by **Market Access Price Impact (MAPI)** modifiers:

```
local_price = MAPI × market_price + (1 - MAPI) × isolated_state_price
```

MAPI starts ~75% and increases with technology (Stock Exchange, Telephones, etc.) and economic laws. **Implication:** local price almost always lags market price, so cross-state shipping silently destroys value. This is the in-engine pressure toward **vertical integration** — colocate inputs and outputs in the same state.

### 4.2 Trade between markets (autonomous)

Pre-1.5 manual trade routes are **gone**. In 1.13, trade between markets is autonomous:

- **Trade Centers** (sub-buildings inside Ports, scaling with port level + trade laws) scan the world market for opportunities.
- They consume **Merchant Marine** (a market good produced by ports) to move goods.
- Routing decisions key off **Trade Advantage**: price gaps, prestige-good bonuses, diplomatic agreements, tariffs, subventions.
- Players influence (not control) trade via:
  - **Tariffs** — discourage flows on a good (per-good directional setting).
  - **Subventions** — encourage import or export of a good.
  - **Embargo / treaty articles** — block flows entirely between specific market pairs.

`Convoys` (the pre-1.13 trade-capacity good) **no longer exist**. Civilian trade and overseas connections consume Merchant Marine (market good); overseas military forces consume **Supply Ships** (military asset, see § 7).

## 5. Companies, prosperity, prestige goods

A country has a fixed number of **Company Slots** unlocked by society techs. Companies are persistent agents that:

- Specialize in 2–4 building types each (defined in `common/company_types/`).
- Provide throughput / construction-efficiency bonuses to their associated industries.
- Earn **Prosperity** when profitable. At 100 Prosperity they activate a national bonus and start producing a **Prestige Good** — a high-quality variant of a regular good (e.g. Champagne instead of Wine).

**Prestige goods** confer Trade Advantage on the global market plus prestige for the producer. They're tracked separately from the underlying good but consumed identically by buy packages.

### 5.1 Charters

States can grant Charters to companies to expand reach:

| Charter | Effect |
|---|---|
| Industry | Adds extra building types to the company's roster (deeper vertical integration) |
| Trade | Enables company-owned Trade Centers to profit from international exports |
| Investment | Allows the company to set up regional HQs in foreign countries |
| Colonization | Speed bonus to colonizing a target state. Sustained colonization can convert the state into a "Chartered Company" semi-independent country |

Where to look: `common/company_types/`, `common/company_charter_types/`, `/raw/CompanyType`.

## 6. Power Blocs, principles, transnational integration

Introduced by *Sphere of Influence* and substantially extended in 1.13. A Power Bloc is a group of countries under a single leader. Members earn **Mandates** over time, spent to unlock **Principles** that apply modifiers to all members.

Economically relevant principle families:

| Principle | Effect |
|---|---|
| Market Unification (T1–T3) | Tier 3 merges all member markets into one customs union with the leader as market owner |
| Foreign Investment (tiered) | Higher tiers grant the leader's owner-pops investment rights inside lower-ranked members |
| Trade & tariff principles | Modify intra-bloc trade efficiency, tariff rates, and trade-advantage modifiers |

`common/power_bloc_principle_groups/`, `common/power_bloc_principles/`, `/raw/PowerBlocPrinciple`.

## 7. The Naval Economy (1.13)

In "The Great Wave" the navy was integrated into the economic loop. **Convoys are gone.** Treat the following as the new defaults:

| Resource | Type | Source | Sink |
|---|---|---|---|
| **Ship Construction** | Building output (port / shipyard family) | Shipyards | Constructing new ship instances |
| **Naval Construction** | Maintenance flow | Same | Keeping existing ships supplied / refit |
| **Merchant Marine** | Market good | Ports + Trade Centers | Civilian trade routes, market access for overseas states |
| **Supply Ships** | Military asset (unit-like) | Naval admin / shipyards | Overseas military formations' supply line |

### 7.1 Ship instances

Ships are physical assets, not abstract "naval power". They:

- Cost input goods (steel, engines, etc.) to build.
- Require ongoing Naval Construction maintenance.
- Live inside fleets attached to a country's military formations.

### 7.2 Ship Designer

Players customize ship hull / armament / armor / supply capacity per type. **Costs scale non-linearly** for higher-tier modifications — reflected in `common/ship_types/` and `common/combat_unit_groups/`. When the mod adds new `ship_type_*` entities, register the relevant `ship_battle_against_ship_type_<ship>_<axis>_<add|mult>` combinations explicitly (see `docs/scripting_best_practices.md` for the per-type/per-axis registration rule).

### 7.3 Gunboat diplomacy

During a diplomatic play, navies can threaten **Naval Hostilities**. If the target refuses, the aggressor can conduct **Port Bombardment**, which:

- Inflicts devastation in coastal target states.
- Can physically destroy buildings (particularly ports and shipyards).

This is the canonical pre-war coercion path for naval-heavy nations.

## 8. Cross-references for agents

- **Concrete IDs** (laws, buildings, goods, modifiers): query `mod_state_server` (`/buildings`, `/laws`, `/goods`, `/modifier-search?q=`).
- **Engine syntax & validation rules:** `docs/scripting_best_practices.md`.
- **Mod systems that hook these vanilla mechanics:** `docs/mod_systems.md`, `docs/journal_entry_systems.md`. Banking cycle (IP/dividend pressure), construction-cost scaling (IP burn rate), tourism (state-scope dynamic modifiers), wonder buildings (long-build construction-good drains), etc.
- **Vanilla company / charter implementations:** `docs/vanilla_company_buildings_reference.md`.
- **What changed at the last vanilla bump:** `docs/vanilla_patch_runbook.md` § "Engine-doc diff" and § "Known vanilla renames".

## 9. Maintenance protocol

This doc captures vanilla concepts at a point in time. To keep it useful:

1. **On every vanilla patch:** the runbook in `docs/vanilla_patch_runbook.md` instructs whoever performs the migration to revisit this file. Update the version banner at the top, and edit any section where 1.x semantics changed (new resource types, removed mechanics, new principle families, restructured ownership). Don't fork a separate "1.14 economy" doc — overwrite.
2. **On discovering a new mechanic mid-development:** when an agent learns something generally applicable about how vanilla economics work (e.g. a non-obvious Trade Advantage modifier, a hidden charter constraint, a Market Unification edge case), add it here in the relevant section. Keep additions short — one paragraph, not a treatise. The bar from `CLAUDE.md` § "Recording lessons learned" applies: would the next agent hit the same gap from scratch?
3. **Don't duplicate:** modifier validation rules, scope chain quirks, and engine-syntax gotchas belong in `docs/scripting_best_practices.md`. This file is *concepts*, not *syntax*.
