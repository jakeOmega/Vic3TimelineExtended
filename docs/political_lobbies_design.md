# Political Lobbies — Design Proposals

> **Status (2026-05-06): DEFERRED.** Two lobby pairs (Colonial/Anti-Colonial and Environmental/Fossil-Fuel, both `category = foreign` / domestic) were implemented in this branch and then reverted. Adding a single domestic-lobby history seed (one `lobby_colonial` for GBR with `ig_landowners`) caused the game to **crash on starting a new game** — load-from-save was unaffected. Logs were inconclusive (no script_parse_error, the `01_extended_lobbies.txt` file produced only a benign UTF-8 BOM warning), but the failure was specifically gated on history execution, which only runs on new-game start. Rather than ship a half-broken system, the entire lobby framework — definitions, appeasement factors, customizable_localization, scripted effects, event hooks, and localization keys — was removed in commit-ready state. This document preserves the design proposals and engine-level findings for a future re-attempt. See [Re-implementation Notes](#re-implementation-notes) below.

## Table of Contents
1. [Re-implementation Notes](#re-implementation-notes)
2. [Vanilla System Analysis](#vanilla-system-analysis)
3. [Engine Capabilities Reference](#engine-capabilities-reference)
4. [Design Proposals](#design-proposals)
5. [Implementation Considerations](#implementation-considerations)
6. [Open Questions](#open-questions)

---

## Re-implementation Notes

### What was tried (and removed)

Two pairs of domestic lobbies (`category = foreign` per the engine's vanilla template doc):

- **Proposal #3 — Colonial / Anti-Colonial:** `lobby_colonial` + `lobby_anti_colonial`, gated on `any_subject_or_below = { exists = this }`. Decolonization events 1a/1b/1c/1d hooked appeasement on negotiate / crackdown / independence / neocolonialism options.
- **Proposal #8 — Environmental / Fossil Fuel:** `lobby_environmental` + `lobby_fossil_fuel`, gated on `has_technology_researched = environmental_movement` (era 8). Environmental events 1a/1b/2a/2b/4a/4b/4c/5a/5b hooked appeasement on green vs. industry options.

Supporting infrastructure (also removed):
- `common/political_lobbies/01_extended_lobbies.txt` — lobby type definitions
- `common/political_lobby_appeasement/01_extended_appeasement.txt` — six custom appeasement factors (`appeasement_colonial_concession/crackdown`, `appeasement_environmental_regulation/deregulation`, `appeasement_fossil_expansion`, `appeasement_green_investment`)
- `common/customizable_localization/01_extended_lobby_naming.txt` — flavored name pools per lobby type (Society/Committee/Council/League/etc.)
- `common/scripted_effects/extended_lobby_effects.txt` — `extended_initialize_lobby_custom_name`, `add_colonial_lobby_appeasement`, `add_environmental_lobby_appeasement` helpers
- Localization keys under `te_concepts_l_english.yml` (display names + descriptions + appeasement factor labels) and `te_unused_l_english.yml` (engine-convention `<lobby>_name` / `<lobby>_icon` keys — `organize_loc.py` flags those as unused because it can't see engine-convention lookups, but the engine still loads them since all `te_*_l_english.yml` files are loaded by filename pattern)

### The crash blocker

After the four lobby files were in place and parse-clean, a single domestic history seed was added:

```
# common/history/lobbies/01_extended_lobbies.txt
LOBBIES = {
    c:GBR ?= {
        create_political_lobby = {
            type = lobby_colonial
            target = c:GBR
            add_interest_group = ig:ig_landowners
        }
    }
}
```

The user reported the game crashing on new-game start (load-from-save was fine, which strongly suggests the crash is in history execution).

What we ruled out from the logs of the crashed session:
- No `script_parse_error` referencing the seed file, the lobby type, or the appeasement factors.
- No `inject_to_missing` / `duplicated_key` / `Unknown trigger` / `Unknown effect` entries against any lobby file.
- The only `01_extended_lobbies.txt` log entry was a benign `should be in utf8-bom encoding` warning.
- `debug.log` cleanly progresses through the standard load sequence and stops at main-menu file enumeration; no lobby-related output.
- `game.log` continues briefly past main-menu but writes only repeated `Event target link 'region' returned an invalid object` from `common/ai_strategies/00_default_strategy.txt:4388` — a vanilla bug, unrelated to lobbies.
- No `.dmp`, `callstacks.log`, or fatal-assertion entries.

What we can't rule out from logs alone:
- Engine asserts that don't flush log buffers before terminating.
- Crashes inside the C++ political-lobby creation path with no script-side error surfaced.
- A semantic mismatch in how a `category = foreign` lobby handles `target = c:<self>` at history-creation time. The vanilla template doc (`common/political_lobbies/political_lobbies.md` in the install) says the engine sets `scope:target_country = scope:country` automatically for domestic lobbies, but the `create_political_lobby` effect signature still requires `target = <country scope>`. Vanilla has no domestic-lobby history seed to compare against — all four vanilla seeded lobbies are foreign-category.

### How to re-attempt safely

Suggested order of investigation, before re-adding any of the deleted files:

1. **Confirm the lobby type definitions themselves are loadable without crash.** Re-add only `01_extended_lobbies.txt` (no appeasement file, no scripted_effects helpers, no event hooks, no history seed). Launch a new game. If it crashes with just the type definitions present, the failure is in `category = foreign` lobby handling, the `on_created` block, or the `requirement_to_maintain` clauses — not in history at all.
2. **If the type definitions load cleanly, add appeasement + scripted_effects + customizable_localization** without any history seed and without event hooks calling `change_appeasement` from outside. Launch a new game. Open the political lobby UI — domestic lobbies should be empty (no catalyst has fired yet) but the panel should not crash when opened.
3. **Wire the event-side appeasement hooks.** Trigger one of the affected events via console (`event decolonization_events.1`). Confirm `change_appeasement` works against a *not-yet-existing* domestic lobby (it should silently no-op since the helper iterates `every_political_lobby` with a type filter).
4. **Last: try to seed a lobby via history.** This is where the crash hit. Try in this order:
   - **Vanilla-shape sanity check:** seed a *foreign* `lobby_pro_country` for any country (e.g., GBR → FRA) with our existing infrastructure intact. If even that crashes, the issue is something we changed beyond the type definitions.
   - **Domestic seed without `target`:** the engine signature requires `target`, but try `target = root` (rather than `c:<self>`) — `root` resolves to the iterating country in history scope and may interact better with the engine's automatic `scope:target_country = scope:country` logic for `category = foreign`.
   - **Domestic seed with on_created stripped:** temporarily remove the `extended_initialize_lobby_custom_name` call from `on_created` and the `change_appeasement = { factor = appeasement_diplomatic_status_quo }` line. If that fixes it, the crash is in one of those calls during history-time execution.
5. **If the history path is fundamentally broken for domestic lobbies** (and we can't get a vanilla-equivalent seed working), accept that the only formation path is engine catalyst — which is sparse but not crashing — and ship without seeds. Document loudly that lobbies will not appear until a diplomatic catalyst happens to roll formation.

### Where the engine docs actually live

Vanilla template doc with the full effect / trigger / scope reference for political lobbies: `common/political_lobbies/political_lobbies.md` in the Steam install (path: `/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/political_lobbies/political_lobbies.md`). This is the canonical answer for what `category` strings the engine accepts (`foreign_pro_country`, `foreign_anti_country`, `foreign`), which scopes are available in each block (`can_create`, `on_created`, `requirement_to_maintain`, `available_for_interest_group`, `join_weight`), and how `scope:target_country` resolves for domestic lobbies.

Vanilla seed examples (foreign-only): `common/history/lobbies/00_lobbies.txt` in the Steam install. ~30 entries; useful template for the seed-file shape, but no domestic precedent.

### What lessons were already absorbed

- `category = foreign` is the engine's domestic-lobby category, with `scope:target_country` auto-set to `scope:country`. Vanilla doesn't ship any but the engine supports them.
- Hardcoded clout event targets (`lobby_foreign_pro_clout:<country>`, `lobby_foreign_anti_clout:<country>`, plus the `_in_government` variants) sum lobbies in foreign categories only — domestic lobbies don't contribute to those buckets, so don't expect domestic lobby clout to modify pact / treaty article costs the way vanilla foreign lobbies do.
- Several vanilla appeasement factors (`appeasement_alliance_formed`, `appeasement_rivalry_declared`, `appeasement_relations_increased`, `appeasement_trade_agreement_formed`, etc.) are fired by the engine's diplomatic catalyst pipeline against lobbies whose `target_country` matches the catalyst's other party. Domestic lobbies (target = self) may never receive these — listed-but-dormant factors don't error, but the lobby's appeasement will be driven entirely by mod-side `change_appeasement` calls.
- The mod's `organize_loc.py` will flag engine-convention loc keys (`<lobby>_name`, `<lobby>_icon`) as unused because the references aren't visible in script. This is benign — all `te_*_l_english.yml` files are loaded by filename pattern, so the keys still resolve. Don't try to "fix" by registering them somewhere.
- Custom name flavoring works via `customizable_localization` blocks that key on `lobby_custom_name_var_<N>` variables set in an `on_created` scripted effect. The mod's removed `extended_initialize_lobby_custom_name` is a working pattern (see git history pre-revert) — copy from there when re-implementing.

---

## Vanilla System Analysis

### Architecture

Political lobbies are **groups of interest groups** within a country that share a stance toward a **target country**. Each lobby has:

- **`category`** — Determines stance type: `foreign_pro_country`, `foreign_anti_country`, or `foreign`. The dev docs explicitly state that `scope:target_country` equals `scope:country` "for domestic lobbies," confirming the engine supports domestic lobby categories even though vanilla doesn't define any.
- **`target`** — A country scope. For foreign lobbies, a different country; for domestic lobbies, the owning country itself.
- **`appeasement`** — A satisfaction score (-10 to +10) that tracks whether the lobby's goals are being met. Each point translates to 1.0 approval for member IGs. Decays toward baseline (0) over ~1025 days per point.
- **`join_weight`** — A script value evaluated per IG to determine how likely it is to join/stay. Threshold: 50 = chance to join, 100 = guaranteed.
- **`requirement_to_maintain`** — Multiple conditions that, if failed, disband the lobby or swap its type (e.g., pro_country ↔ pro_overlord when subject status changes).
- **`appeasement_factors_pro/anti`** — Named events that increase or decrease appeasement.
- **Lobby demands/proposals** — Journal entry + event system where lobbies request the player take diplomatic actions (form alliance, declare war, embargo, leave power bloc, etc.). Ignoring demands decreases appeasement; fulfilling them increases it.

### Vanilla Lobby Types

| Type | Category | Purpose |
|---|---|---|
| `lobby_pro_country` | `foreign_pro_country` | IGs favoring closer relations with a foreign power |
| `lobby_anti_country` | `foreign_anti_country` | IGs opposing a foreign power |
| `lobby_pro_overlord` | `foreign_pro_country` | Loyalist IGs in subject nations |
| `lobby_anti_overlord` | `foreign_anti_country` | Independence-minded IGs in subject nations |

### Formation Reasons

Lobbies form around **catalysts** — diplomatic events that trigger lobby creation. The engine supports these formation reasons:

| Reason | Description |
|---|---|
| `aggression` | Military threats, diplomatic plays, wars |
| `defense` | Need for protection, military alliance |
| `diplomacy` | General diplomatic engagement |
| `ideology` | Shared/opposed political ideology |
| `economy` | Trade, investment, economic ties |
| `technology` | Technological admiration or opposition |
| `religion` | Shared/opposed state religion |
| `funded` | Direct lobby funding via diplomatic action |

### What Lobbies Affect in Vanilla

1. **IG Approval** — Appeasement directly converts to approval for member IGs (1:1).
2. **Diplomatic Pact Costs** — Pro/anti lobby clout modifies influence cost of maintaining pacts (±0.5 max via DIPLOMATIC_PACT_COST_LOBBY_CLOUT_MULT).
3. **Treaty Article Costs** — Same mechanism for treaty articles.
4. **Rivalry Influence** — Lobby clout scales rivalry influence gains (via RIVALRY_SCALING_LOBBY_CLOUT_MULT).
5. **War Exhaustion** — `lobby_war_support` and `lobby_war_opposition` clout directly modify war exhaustion rate (±1.0 at 100% clout).
6. **Leverage Generation** — Pro/anti overlord lobbies affect leverage gain (LEVERAGE_LOBBY_CLOUT_FACTOR = 500).
7. **Diplomatic Catalysts** — Friendly/hostile lobbies in government trigger diplomatic catalysts.

### How Join Weight Works

Join weight is calculated per IG and considers:
- **Stickiness**: IGs already in a lobby get +50 base weight
- **Formation reasons**: Ideology-based multipliers (jingoist, pacifist, etc.) keyed to the formation reason
- **Same IG in target government**: +10 if same IG type is in target's government
- **Law alignment**: ±5 per aligned/misaligned law in target country (capped ±100), ×1.5 for ideology formation reason
- **Cultural similarity**: ±15 based on shared primary culture, heritage, language
- **Religious alignment**: ±15 based on shared religion; ×2 for religion formation reason
- **Ideological alignment**: Matching progressive/liberal/conservative/reactionary IGs in target government
- **Specific ideology bonuses**: Communist solidarity, republican solidarity, Bonapartist revanchism, etc.
- **Country rank**: Weight multiplied by rank comparison (×0.1 for lower rank targets, ×1.5 for great powers)
- **Relations**: ×0.5/×1.05 based on relations for pro; inverted for anti
- **Attitude**: Friendly/hostile attitudes multiply weight ×1.25
- **Power bloc membership**: Same bloc ×1.1, bloc leader ×1.25
- **Pacts**: Fund lobbies pact ×1.25; rival funding ×0.75/1.25

### Appeasement Factors (Vanilla)

Each factor has a `duration_to_show` (typically 60 months) and optionally `is_always_usable = yes`. Factors include:
- Diplomatic: relations changes, trade agreements, alliances, defensive pacts, military assistance, foreign investment, rivalry, embargo
- Demands: lobby request accepted/ignored/failed
- Subject: autonomy changes, independence, became subject
- Law imposition: imposed law enacted/rejected
- Generic: special events positive/negative, lobby pleased/displeased

---

## Engine Capabilities Reference

### Effects (political_lobby scope)
| Effect | Description |
|---|---|
| `add_lobby_member` | Add an IG to lobby |
| `remove_lobby_member` | Remove an IG from lobby |
| `change_appeasement` | Change appeasement with amount + factor |
| `disband_political_lobby` | Disband the lobby |

### Effects (country scope)
| Effect | Description |
|---|---|
| `create_political_lobby` | Create lobby with type, target, IGs, formation_reason |
| `every/random/ordered_political_lobby` | Iterate lobbies in country |

### Triggers
| Trigger | Scope | Description |
|---|---|---|
| `appeasement` | political_lobby | Compare appeasement value |
| `is_member_of_any_lobby` | interest_group | Is IG in any lobby? |
| `is_member_of_lobby` | interest_group | Is IG in specific lobby type? |
| `is_political_lobby_type` | political_lobby | Check lobby type |
| `lobby_clout` | political_lobby | Compare total clout of member IGs |
| `lobby_formation_reason` | political_lobby, diplomatic_catalyst | Check formation reason |
| `num_political_lobbies` | country, interest_group | Count lobbies |

### Event Targets / Scope Accessors
| Target | Description |
|---|---|
| `lobby_type:<key>` | Global link to lobby type |
| `lobby_foreign_pro_clout:<country>` | Total clout of pro-country lobbies targeting country |
| `lobby_foreign_anti_clout:<country>` | Total clout of anti-country lobbies targeting country |
| `lobby_in_government_foreign_pro_clout:<country>` | Same but only governing IGs |
| `lobby_in_government_foreign_anti_clout:<country>` | Same but only governing IGs |
| `lobby_war_support:<war>` | Clout of lobbies supporting a war |
| `lobby_war_opposition:<war>` | Clout of lobbies opposing a war |
| `lobby_join_weight:<lobby>` | IG's join weight for a lobby |
| `target` | The lobby's target country |

### Modifier
| Modifier | Description |
|---|---|
| `country_lobby_leverage_generation_mult` | Multiplier for leverage generation from aligned lobbies |

---

## Design Proposals

### Feasibility Assessment Framework

Before detailing proposals, it's important to understand what the lobby system **can and cannot** do mechanically:

**What the engine supports natively:**
- Creating lobbies with custom types, categories, targets, and formation reasons
- Custom appeasement factors with custom durations
- Custom join_weight logic referencing any trigger/scope
- Custom `requirement_to_maintain` with swap types
- Custom `available_for_interest_group` restrictions
- Custom `on_created` effects
- The `target` is always a country scope (even for domestic lobbies, where target = self)

**What requires workarounds:**
- Domestic lobbies: While the dev docs confirm the concept, vanilla has no domestic categories. We'd need to discover or test which category strings the engine accepts, or use `foreign_pro_country`/`foreign_anti_country` with target = self. **Testing required.**
- Lobby-specific modifiers: The only hardcoded modifier is `country_lobby_leverage_generation_mult`. Any other gameplay effects must be achieved through events, journal entries, decisions, or scripted modifiers keyed to lobby existence/appeasement.
- Custom demands: The demand system (journal entries + proposal events) is entirely scripted, not hardcoded. New demand types are fully feasible.
- UI: The lobby panel is largely hardcoded UI with data-bound widgets. Custom lobby types will appear in the existing panel but we can't fundamentally change the UI layout without GUI overrides.

---

### Proposal 1: Protectionist / Free Trade Lobbies

**Concept:** Domestic lobbies representing economic policy factions. The Protectionist Lobby wants tariffs, domestic industry preference, and opposes free trade agreements. The Free Trade Lobby wants open markets, trade agreements, and investment liberalization.

**Why it fits the lobby system:**
- Formation reasons already include `economy`
- Join weight can reference existing ideology checks (`ideology_protectionist`, `ideology_laissez_faire`, `ideology_market_liberal`)
- Appeasement can be tied to: enacting tariff laws, signing/breaking trade agreements, establishing/ending embargoes
- Demands could include: raise/lower tariffs, sign trade privileges, embargo a competitor

**Implementation sketch:**
```
lobby_protectionist = {
    category = foreign_pro_country  # Target = self (domestic)
    # Or test "domestic" category if engine supports it
    
    can_create = {
        NOT = { is_country_type = decentralized }
        has_technology_researched = international_trade  # or similar threshold
    }
    
    join_weight = {
        # Industrialists with protectionist ideology: high weight
        # Landowners in countries with high import dependence: high weight  
        # Petty bourgeoisie: moderate weight
        # Trade unions concerned about foreign competition: moderate weight
        # Intelligentsia with laissez_faire: negative weight
    }
    
    appeasement_factors_pro = {
        appeasement_tariff_raised
        appeasement_embargo_declared
        appeasement_domestic_industry_subsidized
    }
    
    appeasement_factors_anti = {
        appeasement_tariff_lowered
        appeasement_trade_agreement_formed
        appeasement_foreign_investment_agreement_formed
    }
}
```

**Gameplay value:** Creates domestic tension between economic factions. Players must balance protectionist IG approval against free trade economic benefits. Ties into existing trade mechanics. Particularly relevant for the extended timeline's later eras (globalization vs. protectionism).

**Feasibility: HIGH** — Uses existing formation reasons, ideology checks, and diplomatic events. Appeasement factors largely overlap with existing ones.

---

### Proposal 2: War Hawks / Peace Lobby

**Concept:** Domestic lobbies that form during wartime or in response to military threats. The War Hawk Lobby pushes for military action, expansion, and increased military spending. The Peace Lobby demands de-escalation, diplomacy, and disarmament.

**Why it fits:**
- `lobby_war_support` and `lobby_war_opposition` event targets already exist for exactly this purpose
- Formation reasons `aggression` and `defense` are directly applicable
- War exhaustion is already modified by lobby clout
- Natural complement to the existing political movement system for war/peace

**Implementation sketch:**
```
lobby_war_hawks = {
    category = foreign_anti_country  # Target = the enemy country
    
    can_create = {
        # Exists during/before wars or when claims exist
        OR = {
            is_at_war = yes
            any_scope_state = { has_claim_by = scope:target_country }
            has_diplomatic_pact = { who = scope:target_country type = rivalry }
        }
    }
    
    join_weight = {
        # Armed forces, jingoist IGs: very high
        # Patriotic/military_absolutist ideologies: high
        # Industrialists (military-industrial complex): moderate in late game
        # Pacifist/liberal IGs: strongly negative
    }
    
    appeasement_factors_pro = {
        appeasement_diplomatic_play_started
        appeasement_war_declared
        appeasement_territory_conquered
        appeasement_military_spending_increased
    }
}

lobby_peace = {
    category = foreign_pro_country  # Target = the enemy (wants peace WITH them)
    
    join_weight = {
        # Trade unions, intelligentsia: high
        # Pacifist leaders: very high
        # Rural folk (sons in the army): moderate during long wars
        # Devout (depending on religion/ideology): context-dependent
    }
    
    appeasement_factors_pro = {
        appeasement_peace_signed
        appeasement_diplomatic_demand_conceded
        appeasement_military_spending_decreased
    }
}
```

**Gameplay value:** Adds domestic political costs to warmongering. Long wars naturally generate peace lobbies that push for settlement. Creates a "stab-in-the-back" dynamic where the peace lobby can undermine war support — historically resonant (WWI, Vietnam). War hawks can push for conflicts the player might not want, adding constraint.

**Feasibility: HIGH** — The engine already tracks war support/opposition via lobby clout. Formation is natural during wars. Just needs custom events and appeasement factors.

---

### Proposal 3: Colonial / Anti-Colonial Lobbies

**Concept:** Lobbies that form around the question of colonial expansion and subjects. The Colonial Lobby pushes for maintaining/expanding colonial holdings. The Anti-Colonial Lobby demands decolonization, self-determination, and humanitarian reform of colonial administration.

**Why it fits:**
- The overlord lobby types already partially implement this (pro/anti overlord in subjects)
- This is the **metropolitan perspective** — lobbies WITHIN the imperial power
- Ties into existing decolonization events (the mod already uses `add_lobby_appeasement_from_diplomacy_unidirectional` extensively in decolonization events)
- Subject management mechanics (autonomy, liberty desire, leverage) provide rich appeasement triggers

**Implementation sketch:**
```
lobby_colonial = {
    category = foreign_pro_country  # Target = specific subject/colony
    
    can_create = {
        any_subject_or_below = { exists = this }
        has_technology_researched = colonization  # or appropriate tech
    }
    
    join_weight = {
        # Landowners (plantation interests): very high
        # Armed forces (prestige, strategic bases): high
        # Industrialists (resource extraction): high
        # Devout (missionary activity): moderate
        # Intelligentsia: context-dependent (Kipling vs. anti-imperialism)
    }
    
    requirement_to_maintain = {
        trigger = { any_subject_or_below = { this = scope:target_country } }
        on_failed = { }  # Disband if colony is lost
    }
    
    appeasement_factors_pro = {
        appeasement_colony_acquired
        appeasement_autonomy_decreased
        appeasement_colonial_resources_extracted  # custom
    }
    appeasement_factors_anti = {
        appeasement_autonomy_increased
        appeasement_gained_independence
        appeasement_colonial_reform_enacted  # custom
    }
}

lobby_anti_colonial = {
    category = foreign_anti_country  # Target = specific subject (wants to let them go)
    
    join_weight = {
        # Trade unions (humanitarian concerns): moderate
        # Intelligentsia (Enlightenment values, abolitionism): high
        # Rural folk (why are our boys dying overseas): moderate
        # Liberal/progressive leaders: high
    }
    
    appeasement_factors_pro = {
        appeasement_autonomy_increased
        appeasement_gained_independence
        appeasement_colonial_reform_enacted
    }
}
```

**Gameplay value:** Transforms colonialism from a purely strategic decision into one with domestic political consequences. A Scramble-for-Africa push pleases the Colonial Lobby but antagonizes liberals. Decolonization becomes a political process, not just a button press. Very relevant for the extended timeline's 20th century.

**Feasibility: HIGH** — Overlaps significantly with existing overlord lobby mechanics. Appeasement factors for autonomy and independence already exist.

---

### Proposal 4: Temperance / Vice Lobby

**Concept:** The Temperance Movement lobby pushes for prohibition of alcohol (and potentially other vices — opium, gambling). The Vice Lobby (distillers, tavern owners, etc.) opposes regulation.

**Why it fits:**
- Directly references specific goods and production methods
- Ties into existing law system (could demand liquor prohibition laws)
- Formation reason `ideology` or `economy` both work
- Historical significance spans the entire extended timeline (1830s-2030s: temperance → prohibition → drug wars)

**Implementation sketch:**
```
lobby_temperance = {
    category = foreign_pro_country  # Target = self (domestic)
    
    can_create = {
        # Exists when religious/moralist sentiment is strong enough
        any_interest_group = {
            OR = {
                is_interest_group_type = ig_devout
                leader = { has_ideology = ideology:ideology_moralist }
            }
        }
        # Country has significant liquor production/consumption
    }
    
    join_weight = {
        # Devout: very high (especially Protestant nations)
        # Rural folk (social conservatism): moderate
        # Trade unions (worker welfare): moderate
        # Women's suffrage movement overlap: context
        # Industrialists (want sober workers): mild positive
        # Petty bourgeoisie (tavern owners): strongly negative
    }
    
    appeasement_factors_pro = {
        appeasement_prohibition_enacted  # custom
        appeasement_vice_regulation_passed  # custom
    }
    appeasement_factors_anti = {
        appeasement_vice_deregulated  # custom
        appeasement_liquor_trade_expanded  # custom
    }
}
```

**Demands:** Enact consumption-restriction laws, close certain building types, ban specific goods trade.

**Gameplay value:** Adds a domestic social issue that doesn't map neatly to the left-right spectrum. Creates interesting cross-IG coalitions. Economically, choosing prohibition has real costs (lost tax revenue, crime?). Historically flavorful — ties into Prohibition era in the US, temperance movements in Scandinavia, UK, etc.

**Feasibility: MEDIUM** — Requires custom appeasement factors and possibly custom triggers for specific law enactments. The lobby itself is straightforward; the demand/proposal events need careful design around specific laws. Might require a custom law or using existing consumption/trade laws.

---

### Proposal 5: Religious Lobbies (Denominational)

**Concept:** Lobbies organized around specific religious interests. A Catholic Lobby might push for papal relations, Catholic education, anti-secularism. A Protestant/Evangelical Lobby might push temperance, work ethic laws, mission funding. An Islamic Lobby might demand Sharia-aligned laws. A Secular Lobby might oppose all religious influence in government.

**Why it fits:**
- Formation reason `religion` already exists and has special ×2 multiplier for Devout IGs
- Join weight already considers religious alignment between countries
- Natural extension of the existing Devout IG system
- Can reference the mod's custom religions system

**Implementation sketch:**
```
lobby_religious_establishment = {
    category = foreign_pro_country  # Target = self (domestic)
    
    can_create = {
        NOT = { has_law = law_type:law_total_separation }  # Not in fully secular state
    }
    
    join_weight = {
        # Devout: very high (base)
        # Landowners (traditional alliance with church): moderate
        # Rural folk (traditional piety): moderate
        # Multiplied by whether state religion matches IG cultural religion
        # Intelligentsia: strongly negative
        # Trade unions: negative (anti-clerical tradition)
    }
    
    appeasement_factors_pro = {
        appeasement_religious_law_enacted
        appeasement_church_funding_increased
        appeasement_secular_law_repealed
    }
    appeasement_factors_anti = {
        appeasement_secular_law_enacted
        appeasement_church_funding_decreased
        appeasement_religious_freedom_expanded
    }
}

lobby_secularist = {
    category = foreign_pro_country  # Target = self (domestic)
    
    join_weight = {
        # Intelligentsia: very high
        # Trade unions (anti-clerical): moderate
        # Positivist/radical leaders: high
        # Devout: very negative
    }
    
    appeasement_factors_pro = {
        appeasement_secular_law_enacted
        appeasement_church_state_separation
    }
    appeasement_factors_anti = {
        appeasement_religious_law_enacted
        appeasement_theocratic_influence_increased
    }
}
```

**Demands:** Change church-state laws (church and state, state atheism, freedom of conscience), fund/defund religious institutions, enact/repeal specific laws (education, marriage, censorship aligned with religious values).

**Gameplay value:** Makes religion a domestic political issue beyond just the Devout IG's law preferences. Creates a secularism vs. theocracy axis that intersects with but doesn't duplicate the reform axis. Historically, battles over secular education, separation of church and state, etc. were massive political issues throughout the 19th-20th centuries.

**Feasibility: MEDIUM** — The lobby structure is straightforward. Complexity lies in creating meaningful demands and appeasement events that reference specific law groups (church_and_state, education, etc.).

---

### Proposal 6: Ethno-Nationalist / Pan-Nationalist Lobbies

**Concept:** Lobbies based on cultural/ethnic affinity with another country. Pan-Slavism, Pan-Germanism, Pan-Turkism, Pan-Arabism, Négritude, etc. These lobby for closer ties with culturally related nations and potentially for unification or against culturally alien powers.

**Why it fits:**
- Join weight already considers cultural similarity (shared heritage, language, tradition traits)
- The vanilla pro/anti country lobbies already get bonuses for cultural alignment with ethno-nationalist leaders
- Ties directly into the unification/cultural union systems
- Formation reasons `ideology` and `aggression` directly apply

**Implementation sketch:**
```
lobby_pan_nationalist = {
    category = foreign_pro_country  # Target = culturally related country
    
    can_create = {
        NOT = { is_country_type = decentralized }
        scope:target_country = {
            any_primary_culture = {
                OR = {
                    shares_heritage_trait_group_with_any_primary_culture = root
                    shares_language_trait_group_with_any_primary_culture = root
                }
            }
        }
    }
    
    requirement_to_maintain = {
        trigger = {
            scope:target_country = {
                any_primary_culture = {
                    shares_heritage_trait_group_with_any_primary_culture = root
                }
            }
        }
    }
    
    join_weight = {
        # Ethno-nationalist / fascist leaders: very high
        # Patriotic / jingoist IGs: high  
        # Devout (if shared religion): moderate
        # Liberal / internationalist: negative
        # Based on discrimination status of shared culture in own country
    }
}
```

**Demands:** Form alliances with culturally related nations, support their diplomatic plays, oppose enemies of the pan-national group, pursue unification.

**Gameplay value:** Makes pan-nationalism a political force rather than just a unification mechanic. Pan-Slavic lobbies in Russia push for intervention in Balkans. Pan-German lobbies in Austria push for Anschluss. Pan-Arabism drives Middle Eastern politics in the extended timeline. Creates realistic pressure for wars of national unification that the player may not want.

**Feasibility: HIGH** — Mostly reuses existing join weight logic from vanilla pro/anti country lobbies. The cultural similarity checks already exist. Only needs the cultural filtering in `can_create` and `available_for_interest_group`.

---

### Proposal 7: Industrial / Labor Lobbies

**Concept:** Lobbies representing concentrated economic interests. The Industrial Lobby (representing factory owners, magnates) pushes for deregulation, low taxes on business, anti-union laws. The Labor Lobby (representing workers' interests) pushes for labor protections, minimum wages, worker rights.

**Why it fits:**
- Formation reason `economy` directly applies
- IG type filtering (`ig_industrialists`, `ig_trade_unions`) is natural
- Ties into existing law system (labor rights, economic policy)
- Can reference the mod's existing banking/economic systems

**Implementation sketch:**
The mod already simulates some of this via events (`corporate_lobbying_accepted_modifier`, `corporate_lobbying_restricted_modifier`, `fossil_lobby_concessions_modifier`, `finreg_bankers_lobby_advance`). The lobby system would formalize this.

```
lobby_industrial = {
    category = foreign_pro_country  # Target = self (domestic)
    
    join_weight = {
        # Industrialists: very high (core constituency)
        # Petty bourgeoisie: moderate (aspiring capitalists)
        # Landowners (if monetized agriculture): moderate in late game
        # Trade unions: strongly negative
        # Market liberal / laissez_faire leaders: bonus
    }
    
    appeasement_factors_pro = {
        appeasement_business_deregulated
        appeasement_tax_on_capital_reduced
        appeasement_anti_union_law_enacted
        appeasement_subsidy_granted
    }
    appeasement_factors_anti = {
        appeasement_labor_protection_enacted
        appeasement_progressive_tax_enacted
        appeasement_union_rights_expanded
    }
}

lobby_labor = {
    category = foreign_pro_country  # Target = self (domestic)
    
    join_weight = {
        # Trade unions: very high
        # Intelligentsia (progressive): moderate
        # Rural folk (agrarian populism): moderate
        # Communist/socialist leaders: bonus
        # Industrialists: strongly negative
    }
}
```

**Demands:** Change labor laws, taxation, minimum wage, worker safety regulations, nationalization/privatization.

**Gameplay value:** Formalizes the class struggle as an ongoing political dynamic rather than just IG clout competition. Creates a lobbying system where economic interests explicitly push for specific policies. The mod's existing corporate lobbying events could be integrated into this framework. A powerful industrial lobby might block environmental regulation (ties into global warming system).

**Feasibility: HIGH** — Straightforward use of IG types and law stances. Events already exist in the mod for corporate lobbying. Main work is creating the lobby definition and corresponding appeasement events.

---

### Proposal 8: Environmental / Fossil Fuel Lobbies

**Concept:** The Fossil Fuel Lobby resists environmental regulation, renewable energy, and carbon taxes. The Environmental Lobby pushes for regulation, conservation, emissions reduction. Directly ties into the mod's global warming system.

**Why it fits:**
- The mod already has `fossil_lobby_concessions_modifier` in events
- Global warming is a major mod system — lobbies would give it a political dimension
- Formation would be technology-gated to relevant eras
- Can reference building types (oil rigs, coal mines vs. solar, wind, nuclear)

**Implementation sketch:**
```
lobby_fossil_fuel = {
    category = foreign_pro_country  # Target = self (domestic)
    
    can_create = {
        has_technology_researched = petroleum_refining  # or appropriate tech
        # Country has significant fossil fuel production
    }
    
    join_weight = {
        # Industrialists: high (especially if country has fossil buildings)
        # Petty bourgeoisie (fuel-dependent small business): moderate
        # Trade unions (jobs in fossil industries): context-dependent
        # Devout: slightly positive (status quo bias)
        # Intelligentsia: negative
        # Weighted by how much of economy is fossil-dependent
    }
    
    appeasement_factors_pro = {
        appeasement_fossil_subsidy_granted
        appeasement_environmental_regulation_blocked
        appeasement_carbon_tax_reduced
    }
    appeasement_factors_anti = {
        appeasement_environmental_law_enacted
        appeasement_renewable_investment
        appeasement_carbon_tax_enacted
    }
}

lobby_environmental = {
    # Mirror structure, opposite appeasement factors
}
```

**Gameplay value:** Creates a political cost for environmental action. Even if the player knows global warming is a threat, the fossil fuel lobby's impact on IG approval makes action politically difficult — mirroring reality. The environmental lobby provides political reward for green policies. This makes climate policy feel like a genuine political struggle rather than a menu selection.

**Feasibility: HIGH** — The mod already has the global warming system, fossil fuel events, and even a `fossil_lobby_concessions_modifier`. This proposal essentially formalizes what already exists as ad-hoc modifiers into the structured lobby system.

---

### Proposal 9: Military-Industrial Lobby

**Concept:** A lobby representing the arms industry, military establishment, and their political allies. Pushes for military spending, arms exports, hawkish foreign policy, and opposes disarmament.

**Why it fits:**
- Formation reasons `aggression` and `defense` directly apply
- Armed forces IG is a natural member
- Ties into military spending, army/navy size, arms trade
- Relevant across the entire timeline (from 19th century militarism to the Cold War military-industrial complex)

**Implementation sketch:**
```
lobby_military_industrial = {
    category = foreign_pro_country  # Target = self (domestic)
    
    can_create = {
        # Country has significant military industry
        any_scope_building = {
            is_building_type = building_arms_industry  # or similar
            level >= 3
        }
    }
    
    join_weight = {
        # Armed forces: very high
        # Industrialists (arms manufacturers): high
        # Jingoist/military_absolutist IGs: high
        # Petty bourgeoisie: moderate (military contracts)
        # Pacifist / liberal leaders: strongly negative
    }
    
    appeasement_factors_pro = {
        appeasement_military_spending_increased
        appeasement_arms_export_signed
        appeasement_military_technology_researched
        appeasement_war_declared
    }
    appeasement_factors_anti = {
        appeasement_disarmament_treaty
        appeasement_military_spending_cut
        appeasement_peace_treaty_signed
    }
}
```

**Demands:** Increase military spending, research military technology, export arms, refuse disarmament treaties, mobilize, declare war.

**Gameplay value:** The military-industrial complex is one of the defining political phenomena of the late 19th-20th centuries. Eisenhower warned about it. This creates ongoing pressure for militarization that makes peace politically costly — a fascinating inversion of the vanilla war exhaustion mechanic.

**Feasibility: MEDIUM** — Lobby structure is simple. The "military spending" appeasement trigger may need custom events since there's no single "military budget" variable to track. Can reference army/navy expansion, military building construction, military tech research.

---

### Proposal 10: Landed / Agrarian Lobby

**Concept:** A lobby representing agricultural interests — large landowners, tenant farmers, agricultural workers. Pushes for agricultural subsidies, land reform (or against it, depending on who dominates), tariffs on imported food, opposition to urbanization/industrialization.

**Why it fits:**
- The Landowners and Rural Folk IGs are natural constituencies
- Formation reason `economy` applies
- Tensions between agriculture and industry are central to the game's economic model
- Historically, agrarian lobbies were enormously powerful (Junkers in Prussia, Southern planters in the US, etc.)

**Implementation sketch:**
```
lobby_agrarian = {
    category = foreign_pro_country  # Target = self (domestic)
    
    can_create = {
        # Significant agricultural sector relative to total economy
    }
    
    join_weight = {
        # Landowners: very high
        # Rural folk: high
        # Devout (rural base): moderate
        # Petty bourgeoisie (agricultural traders): moderate
        # Industrialists: negative (competing for labor/capital)
        # Trade unions (urban focus): slightly negative
    }
    
    appeasement_factors_pro = {
        appeasement_agricultural_subsidy
        appeasement_food_tariff_enacted
        appeasement_land_reform_blocked  # or enacted, depending on composition
    }
    appeasement_factors_anti = {
        appeasement_food_tariff_removed
        appeasement_urbanization_incentive
        appeasement_industrial_subsidy
    }
}
```

**Demands:** Impose food tariffs, subsidize agriculture, block urbanization policies, resist industrialization of farming.

**Gameplay value:** Creates a political force opposing rapid industrialization. Players who want to modernize fast face resistance from the agrarian lobby, which represents real political dynamics. The "Corn Laws" debate in Britain, agrarian populism in the US, agricultural vs. industrial policy in developing nations — all are represented.

**Feasibility: HIGH** — IG composition is straightforward. Appeasement can be tied to tariff laws, building construction priorities (farms vs. factories), and trade goods (food vs. manufactured goods).

---

### Proposal 11: Monarchist / Republican Lobbies

**Concept:** Lobbies organized around the form of government itself. A Monarchist Lobby in a republic pushes for restoration. A Republican Lobby in a monarchy pushes for democratization. A Restoration Lobby in a post-revolutionary state pushes to bring back the ancien régime.

**Why it fits:**
- Formation reason `ideology` directly applies
- Vanilla already gives special join_weight bonuses for communist solidarity, republican anti-monarchism, etc.
- Ties into the governance law groups
- Historical significance: entire 19th century is shaped by this tension

**Implementation sketch:**
```
lobby_monarchist_restoration = {
    category = foreign_pro_country  # Target = a monarchist country (model to emulate)
    
    can_create = {
        NOT = { has_law = law_type:law_monarchy }
        # Country was recently a monarchy (within last 20 years?) or has monarchist tradition
    }
    
    join_weight = {
        # Landowners: high (traditional aristocratic alliance)
        # Devout: high (divine right, traditional order)
        # Armed forces: moderate (depends on ideology)
        # Reactionary/conservative leaders: very high
        # Republican / radical leaders: very negative
    }
    
    appeasement_factors_pro = {
        appeasement_monarchy_restored
        appeasement_aristocratic_privilege_enacted
        appeasement_conservative_law_passed
    }
}

lobby_republican = {
    category = foreign_pro_country  # Target = a republican country (model to emulate)
    
    can_create = {
        has_law = law_type:law_monarchy
        any_interest_group = {
            OR = {
                has_ideology = ideology:ideology_republican
                leader = { has_ideology = ideology:ideology_republican_leader }
            }
        }
    }
    
    join_weight = {
        # Intelligentsia: very high
        # Trade unions: high
        # Republican / radical / positivist leaders: very high
        # Landowners: negative
        # Devout: context-dependent
    }
}
```

**Demands:** Change governance type, enact constitutional reforms, expand/restrict suffrage, establish/abolish hereditary offices.

**Gameplay value:** Makes government-type transitions a political process with ongoing pressure rather than just a law change. A restored monarchy faces perpetual republican lobbying. A new republic faces monarchist restoration pressure. This is THE defining political question of the 19th century.

**Feasibility: HIGH** — This is essentially a specialized version of the ideology-based pro/anti country lobby, focused on governance. The vanilla model country targeting works perfectly here (pro = aspire to be like this country's government).

---

### Proposal 12: Diaspora / Cultural Minority Lobbies

**Concept:** Lobbies representing diaspora communities or cultural minorities lobbying for the interests of their homeland or cultural group. The Irish Lobby in the US pushing for Irish independence. The Jewish Lobby in various countries pushing for Zionist goals or against antisemitism. German-Americans opposing entry into WWI.

**Why it fits:**
- The vanilla system already considers cultural similarity in join weights
- `scope:target_country` would be the diaspora's homeland
- Formation reasons `ideology`, `religion`, and `defense` all apply
- Can reference cultural acceptance levels and discrimination triggers

**Implementation sketch:**
```
lobby_diaspora = {
    category = foreign_pro_country  # Target = homeland
    
    can_create = {
        NOT = { is_country_type = decentralized }
        scope:target_country = {
            NOT = { this = root }
            any_primary_culture = {
                culture_is_discriminated_in = root  # or just "exists in country"
            }
        }
    }
    
    join_weight = {
        # IGs with significant pops of the diaspora culture
        # Devout (if shared religion with target): bonus
        # Ethno-nationalist leaders: multiplier
        # Weighted by size of diaspora population in country
        # Reduced if diaspora is well-integrated (high acceptance)
    }
}
```

**Demands:** Improve relations with homeland, support homeland in diplomatic plays, reduce discrimination against diaspora culture, support independence movements.

**Gameplay value:** Adds a realistic domestic political dimension to immigration and cultural diversity. Diaspora lobbies can create foreign policy pressures (the US-Ireland-Britain triangle, Jewish diaspora influence on Middle Eastern policy, overseas Chinese communities). Also creates incentives to assimilate or accommodate minorities.

**Feasibility: MEDIUM** — The concept is sound, but identifying which cultures count as "diaspora" in a given country and what their "homeland" is requires careful scripting. May need culture-specific scripted triggers or use the existing `is_homeland` accessor.

---

### Proposal 13: Technology / Luddite Lobbies

**Concept:** Lobbies organized around attitudes toward technological progress. A Modernization Lobby pushes for technology adoption, industrialization, and scientific investment. A Traditionalist/Luddite Lobby opposes mechanization, automation, and disruption of traditional livelihoods.

**Why it fits:**
- Formation reason `technology` already exists
- `ideology_positivist`, `ideology_luddite`, `ideology_modernizer` exist
- Can reference technology research progress and building types

**Implementation sketch:**
```
lobby_modernization = {
    category = foreign_pro_country  # Target = technologically advanced country (model)
    
    can_create = {
        scope:target_country = {
            # Has more advanced technology / higher innovation rate
        }
    }
    
    join_weight = {
        # Intelligentsia: very high
        # Industrialists: high (efficiency gains)
        # Positivist / modernizer leaders: high
        # Luddite leaders: very negative
        # Rural folk: negative (threatened by mechanization)
    }
}

lobby_traditionalist = {
    category = foreign_anti_country  # Target = same advanced country (opposes influence)
    
    join_weight = {
        # Rural folk: high (anti-mechanization)
        # Devout: moderate (traditional values)
        # Luddite leaders: very high
        # Petty bourgeoisie (artisans threatened by factories): high
        # Industrialists: negative
    }
}
```

**Demands:** Research/block specific technologies, build/demolish specific building types, adopt/reject foreign innovations.

**Gameplay value:** Makes technology adoption a political issue, not just a tech tree click. Rapid industrialization provokes Luddite backlash. A traditionalist lobby in an unrecognized country can block modernization reforms. The technology formation reason is already baked into the vanilla system but underutilized — this gives it a home.

**Feasibility: MEDIUM** — The foreign-targeting version (model country) works well. A purely domestic version may need the domestic lobby category to function cleanly. Technology-specific appeasement triggers would need custom events.

---

### Proposal 14: Abolitionist / Slavery Lobbies

**Concept:** Lobbies organized around the slavery question. An Abolitionist Lobby pushes for emancipation and opposes slave trade. A Planter/Slavery Lobby defends the institution. Relevant for the early timeline (1836 start through Civil War era).

**Why it fits:**
- Directly references existing law group (slavery laws)
- Clear IG alignment (Landowners pro-slavery, Intelligentsia/Devout abolitionist)
- Can reference the abolition diplomatic action and international pressure
- Foreign-targeting: US abolitionists look to Britain as a model; British abolitionists pressure other nations

**Implementation sketch:**
```
lobby_abolitionist = {
    category = foreign_pro_country  # Target = country that has abolished slavery (model)
    
    can_create = {
        OR = {
            has_law = law_type:law_slave_trade
            has_law = law_type:law_legacy_slavery
            has_law = law_type:law_debt_slavery
        }
        scope:target_country = {
            has_law = law_type:law_no_slavery
        }
    }
    
    join_weight = {
        # Intelligentsia: very high
        # Devout (evangelical abolitionism): high
        # Trade unions (free labor ideology): high
        # Landowners (slaveholding class): very negative
    }
}
```

**Demands:** Enact abolition laws, support abolition diplomatic pressure against other nations, sign anti-slavery treaties.

**Gameplay value:** Makes the abolition question a dynamic political struggle with ongoing lobby pressure, not just a law change. The Abolitionist Lobby's foreign-model targeting (pointing to Britain or Haiti) is historically accurate. Creates political tension in slaveholding nations that escalates over time.

**Feasibility: HIGH** — Clean mapping to existing laws and IGs. Time-limited relevance (1836-1870s mostly, though debt slavery persists longer). Could integrate with the `law_type:law_no_slavery` law enactment events.

---

### Proposal 15: Nuclear Lobby (Pro-Nuclear / Anti-Nuclear)

**Concept:** Given the mod's nuclear weapons system, lobbies around nuclear policy: the Nuclear Lobby (military-industrial interests pushing for nuclear arms, nuclear power) vs. the Anti-Nuclear/Disarmament Lobby (pushing for nuclear disarmament, test ban treaties, peaceful alternatives).

**Why it fits:**
- The mod already has a comprehensive nuclear weapons system
- Ties into the mod's existing diplomatic and military systems
- Cold War politics were dominated by nuclear policy debates
- Formation reasons `defense`, `technology`, and `aggression` all apply

**Implementation sketch:**
```
lobby_nuclear = {
    category = foreign_anti_country  # Target = nuclear rival
    
    can_create = {
        has_technology_researched = nuclear_fission  # or whatever mod tech
        scope:target_country = {
            # Is a nuclear power or potential nuclear threat
        }
    }
    
    join_weight = {
        # Armed forces: very high
        # Industrialists (nuclear industry): high
        # Jingoist / military_absolutist: high
        # Pacifist leaders: very negative
    }
}

lobby_disarmament = {
    category = foreign_pro_country  # Target = nuclear rival (wants détente)
    
    join_weight = {
        # Intelligentsia: high
        # Trade unions: moderate
        # Pacifist leaders: very high
        # Rural folk (fear of nuclear war): moderate in high-tension periods
    }
    
    appeasement_factors_pro = {
        appeasement_nuclear_test_ban_signed
        appeasement_disarmament_treaty_signed
        appeasement_nuclear_arsenal_reduced
    }
    appeasement_factors_anti = {
        appeasement_nuclear_test_conducted
        appeasement_nuclear_arsenal_expanded
        appeasement_nuclear_threat_made
    }
}
```

**Demands:** Conduct/ban nuclear tests, expand/reduce nuclear arsenal, sign/break disarmament treaties, pursue/abandon nuclear power.

**Gameplay value:** Makes nuclear policy a political dynamic, not just a strategic choice. The anti-nuclear movement was one of the largest political movements of the Cold War era. Creates tension between security hawks wanting nuclear supremacy and peace advocates wanting disarmament. Integrates directly with the mod's nuclear system for immersive Cold War gameplay.

**Feasibility: MEDIUM-HIGH** — Lobby structure is clean. Needs custom appeasement factors tied to the mod's nuclear system events. Given the nuclear system already exists with rich event infrastructure, integration is mostly about connecting the two systems.

---

## Implementation Considerations

### Technical Questions Requiring Testing

1. **Domestic Lobby Categories** — partially answered. `category = foreign` is the engine's domestic-lobby category per `common/political_lobbies/political_lobbies.md` in the vanilla install; engine sets `scope:target_country = scope:country` automatically. The lobby type definitions parse and load fine. **Open**: domestic-lobby creation via `create_political_lobby` from history may crash on new-game start — see [Re-implementation Notes → The crash blocker](#the-crash-blocker). Also caveats: hardcoded `lobby_foreign_pro_clout` / `lobby_foreign_anti_clout` event targets are foreign-category only and do NOT sum domestic lobbies.

2. **Maximum Lobby Count**: Vanilla doesn't seem to have a per-country lobby limit, but at what point does performance or UI clutter become an issue?

3. **Lobby-to-Lobby Interaction**: Can lobbies conflict? If an IG is in both a protectionist lobby and a free trade lobby (impossible per `available_for_interest_group`, but what about different lobby types?), how is this handled?

4. **IG Membership Limits**: An IG can be in multiple lobbies of different types. At POLITICAL_LOBBY_JOIN_WEIGHT_REPLACEMENT_THRESHOLD = 1.25, new lobbies can replace old ones of the **same type**. Different types don't compete this way.

### Recommended Implementation Priority

| Priority | Proposals | Rationale |
|---|---|---|
| **Phase 0 (Crash investigation)** | Resolve the new-game crash on domestic history seeding — see [Re-implementation Notes → How to re-attempt safely](#how-to-re-attempt-safely). Until that's understood, no further lobby work ships. | Blocker for all downstream work |
| **Phase 1 (Re-add deferred lobbies)** | #3 Colonial/Anti-Colonial, #8 Environmental/Fossil Fuel — re-add the four removed files, then resolve the crash. The branch immediately before revert (see git history) has working type definitions, appeasement factors, custom name flavoring, and event hooks ready to restore. | Highest-readiness future work; previously authored, then removed pending crash fix |
| **Phase 2 (Visibility)** | Add `common/history/lobbies/01_extended_lobbies.txt` with 5–10 thematic 1836 seeds — only after the crash is resolved | Engine catalyst-driven formation is sparse; seeds make the system visible at game start |
| **Phase 3 (High-impact, low-risk)** | #1 Protectionist/Free Trade, #7 Industrial/Labor | Build on existing mod systems |
| **Phase 4 (Historical flavor)** | #6 Pan-Nationalist, #14 Abolitionist | Major historical forces with clear IG mappings |
| **Phase 5 (Domestic politics)** | #2 War Hawks/Peace, #5 Religious/Secular, #11 Monarchist/Republican | Deepen domestic political gameplay |
| **Phase 6 (Specialized)** | #9 Military-Industrial, #10 Agrarian, #15 Nuclear, #4 Temperance, #12 Diaspora, #13 Technology | Specialized lobbies for specific eras or mechanics |

### Appeasement Design Principles

1. **Appeasement factors should be specific and actionable.** "You enacted a protectionist tariff" is better than "you did something the lobby likes."
2. **Use `is_always_usable = yes`** sparingly — only for factors that genuinely apply to all lobby types (like request accepted/ignored).
3. **Match durations to political timescales.** Major events (war, independence) should last 60+ months. Routine actions (trade agreement) 24-36 months.
4. **Add both pro AND anti factors for balance.** Every lobby should have clear ways to both please and displease it.

### Event Infrastructure

Each new lobby type ideally needs:
- **Formation events** — How/when the lobby forms (or use automatic formation via `can_create` + `join_weight`)
- **Flavor events** — `lobby_yearly_events`-style events that fire periodically (5-10 per lobby type)
- **Demand/proposal events** — What the lobby demands the player do (integrate into existing `lobby_proposal` framework)
- **Consequence events** — What happens when the lobby is very pleased or very displeased (defection, withdrawal, radical action)

### Interaction with Existing Mod Systems

| Mod System | Relevant Lobbies | Integration Points |
|---|---|---|
| Global Warming | #8 Environmental/Fossil Fuel | GW events trigger appeasement; fossil lobby blocks regulation |
| Nuclear Weapons | #15 Nuclear/Disarmament | Nuclear events trigger appeasement; disarmament lobby demands treaties |
| Banking Cycles | #7 Industrial/Labor | Financial regulation events feed appeasement; banking crises empower labor lobby |
| Construction Cost Scaling | #10 Agrarian | Agrarian lobby opposes urban construction priority |
| Custom Religions | #5 Religious/Secular | Religious lobby strength varies by denomination |
| Decolonization | #3 Colonial/Anti-Colonial | Existing decolonization events already feed lobby appeasement |
| Treaty Articles | All foreign-targeting lobbies | Lobby clout already affects treaty article costs |

### Naming System Extension

Vanilla's `initialize_lobby_custom_name` effect assigns flavor names via variables (Union, Association, Society, League, etc.). Each new lobby type would need thematic name pools:
- Protectionist: "Tariff League", "Domestic Industry Society", "National Commerce Union"
- Environmental: "Conservation League", "Green Society", "Earth First Society"
- Labor: "Workers' Federation", "Labor Alliance", "People's Committee"
- etc.

---

## Open Questions

1. **Domestic lobby new-game crash** — BLOCKER. Adding any single domestic-lobby (`category = foreign`) history seed via `create_political_lobby` from `common/history/lobbies/` crashed the game on new-game start. Logs were silent. This needs to be diagnosed before *any* of the deferred lobby work ships. See [Re-implementation Notes → The crash blocker](#the-crash-blocker) for what's known and ruled out.

2. **Domestic lobby caveats** — `category = foreign` is the engine's domestic category (confirmed by vanilla template doc). But hardcoded clout event targets (`lobby_foreign_pro_clout` / `lobby_foreign_anti_clout` and their `_in_government` variants) are foreign-category-only and won't sum domestic lobbies — so domestic lobby clout doesn't drive pact / treaty article costs. Some vanilla appeasement factors driven by foreign-country diplomatic catalysts may also be dormant for domestic lobbies. Surface area for re-attempt to verify.

3. **Lobby cap / UI concerns**: With 15+ potential lobby types, a country could theoretically have dozens of active lobbies. Should there be a scripted cap? Should some lobbies be mutually exclusive?

4. **DLC gating**: Vanilla gates all lobby features behind `has_dlc_feature = lobbies` (DLC = dlc010, Sphere of Influence). The mod should decide whether to gate new lobbies behind this DLC check or make them available to all players. If DLC-gated, players without SoI can't use any of these features.

5. **AI behavior**: The existing lobby system has AI handling for demands (on_actions check for journal entries). New lobby types need AI logic for responding to demands.

6. **Balance**: Lobby appeasement directly converts to IG approval. Too many lobbies = too many ways to gain/lose approval. Need to ensure total approval swings from lobbies don't dominate other sources.
