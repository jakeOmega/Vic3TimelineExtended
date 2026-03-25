# New Treaty Articles — Design & Implementation Plan

## Overview

This document plans new treaty articles for the Vic3TimelineExtended mod. Each article includes historical motivation, mechanical design, implementation details (required inputs, modifiers, effects, AI weights), and feasibility analysis against known engine constraints. Articles marked with design uncertainty may be deferred or cut.

### Engine Constraints Reference

- **`source_modifier` / `target_modifier`** in treaty articles are **country-scoped** — they apply flat country modifiers for the treaty's duration. There is no built-in mechanism for a treaty article to apply a persistent state-scoped modifier to a specific `input_state`.
- **State-scoped effects** must be done via `on_entry_into_force` → `add_modifier` on the state, with a corresponding `on_break` / `on_withdrawal` → `remove_modifier`. This requires tracking which state the modifier was applied to.
- **`required_inputs`** supports: `state`, `country`, `company`, `goods`, `law_type`, `building_type`, `strategic_region`, `text`. The mod already has generic `company` GUI support. `state` input uses the existing state picker.
- **Vanilla state-targeting articles**: `treaty_port` (cedes state control), `transfer_state` (transfers ownership). Both use `input_state` in `scope:article_options`.
- **`non_fulfillment`** can enforce conditions with `consequences = freeze` (treaty frozen if violated).
- **`source_modifier` / `target_modifier` are automatically applied and removed** by the engine when the treaty is active/broken — no manual cleanup needed. But they only accept country-scope modifiers.
- **For state-scoped effects that persist while the treaty is active**, the cleanest pattern is: `on_entry_into_force` adds a modifier to the state + sets a variable on the state, and `on_break`/`on_withdrawal` removes them. An `on_action` (yearly/monthly) can reapply if needed.
- **Company throughput**: `country_company_throughput_bonus_add` (country scope) boosts all companies. There is no per-company modifier — company benefits are country-wide or via building-level effects.

---

## Article 1: Minority Protection Treaty

### Historical Context
Russia's claims to protect Orthodox Christians in the Ottoman Empire; Austria's protection of Catholics in the Balkans; League of Nations minority treaties after WWI; modern UN minority rights frameworks. A Great Power forces a weaker nation to guarantee rights of a cultural or religious minority, reducing assimilation pressure on that group.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `state` |
| **Cost** | 100 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `international_relations` |

### Effects

**On the target state** (applied via `on_entry_into_force` on `input_state`, removed on `on_break`/`on_withdrawal`):
- `state_assimilation_mult = -0.5` — Halves assimilation rate in that state (minorities keep their culture)
- `state_conversion_mult = -0.5` — Halves religious conversion rate
- `state_migration_pull_mult = 0.1` — Slight migration pull (minorities feel safer coming there)

**On the source country** (the conceding side, via `source_modifier`):
- `country_legitimacy_base_add = -10` — Legitimacy hit: the government looks weak for ceding sovereignty over internal affairs
- `country_authority_add = -200` — Authority drain: enforcing foreign-imposed protections is costly

**On the target country** (the protector, via `target_modifier`):
- `country_prestige_mult = 0.05` — Modest prestige for championing minority rights

### Non-Fulfillment
No non-fulfillment conditions - the treaty is enforced via the state modifier.

### AI Design
- `article_ai_usage = { request }` — AI demands this from others
- AI Great Powers with `protective` or `domineering` attitude request this from countries that discriminate against shared heritage cultures
- Source reluctance scales with: primary culture pop fraction in the target state (higher = more reluctance), number of discriminated cultures (more = more reluctance), country rank difference
- Target benefit: prestige, relations with minorities

### Implementation Notes
- Define static modifier `minority_protection_state_modifier` in `extra_modifiers.txt` with the state-scoped effects
- In `on_entry_into_force`: apply modifier to `input_state`, set variable `has_minority_protection` on the state
- In `on_break`/`on_withdrawal`: remove modifier and variable from the state
- The state variable can be used by events (e.g., "Minority group appeals to protecting power after pogrom")
- **Localization**: Need loc keys for the modifier, its desc, the article name, desc, effects_desc, article_short_desc

### Event Hooks
Consider companion events:
- **Minority Appeal** — If a country with this treaty enacts a discriminatory law, the protecting power gets an event to respond (diplomatic incident, generate war goal, etc.)
- **Cultural Festival** — Periodic positive event in the protected state about minority cultural flourishing

---

## Article 2: Free Port Concession

### Historical Context
The Canton System restricted foreign trade to a single port (Guangzhou). The Treaty of Nanking opened Shanghai, Ningbo, Fuzhou, Amoy, and Canton as "treaty ports." Hamburg, Singapore, Hong Kong, and Danzig operated as free ports. The Open Door Policy demanded equal trade access in China. Free port status eliminates tariffs in a specific location, boosting trade at the cost of sovereignty.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `state` |
| **Cost** | 75 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile`, `giftable` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `international_trade` |
| **Relations** | `relations_progress_per_day = -0.25`, `relations_improvement_min = 0` |

### Effects

**On the target state** (via `on_entry_into_force` modifier on `input_state`):
- `state_tariff_import_add = -1.0` — Eliminates import tariffs in that state (the `-1.0` should override any tariff rate, effectively zeroing it; needs testing for edge cases with compounding modifiers)
- `state_tariff_export_add = -1.0` — Eliminates export tariffs
- `state_trade_capacity_add = 10` — Massive boost to trade capacity (more trade routes can pass through)
- `state_trade_quantity_mult = 0.5` — 50% more goods flow through trade routes here
- `state_migration_pull_add = 10` — Attracts merchants and settlers
- `state_assimilation_mult = -0.25` — Cosmopolitan trading hub preserves cultural diversity

**On the source country** (conceding tariff sovereignty):
- `country_authority_add = -100` — Authority cost for ceding fiscal control over a state
- No prestige/legitimacy penalty if `giftable` — sometimes countries voluntarily open ports

**On the target country** (the one whose traders benefit):
- `country_prestige_mult = 0.03` — Minor prestige for forcing open a port

### Visibility / Possible
- Target state must be coastal (`is_coastal = yes`)
- Source country must not have `law_isolationism` (exception: `law_canton_system` — historically this is how the Canton system gets broken)
- Should NOT be usable if the state already has a treaty port (`is_treaty_port = no`) — free port is a distinct concept, but stacking with treaty port would be weird

### State Valid Trigger
```
state_valid_trigger = {
    scope:input = {
        is_coastal = yes
        owner = root  # Must be source country's state
    }
}
```

### Non-Fulfillment
The source country must maintain trade laws permitting trade (not `law_isolationism`):
```
non_fulfillment = {
    consequences = freeze
    conditions = {
        monthly = {
            scope:article = {
                source_country = {
                    NOT = { has_law = law_type:law_isolationism }
                }
            }
        }
    }
}
```

### AI Design
- `article_ai_usage = { request offer }` — AI can demand it from weaker nations OR offer it as a concession
- Evaluation: Commercial-minded AI (high trade, `laissez_faire`) more likely to request. Source reluctance based on state GDP (rich ports hurt more to give away tariff-free)
- Nations with `law_free_trade` already have no tariffs — AI should deprioritize requesting this from free-trade nations

### Implementation Notes
- Define `free_port_state_modifier` in `extra_modifiers.txt`
- Apply/remove via `on_entry_into_force` / `on_break` / `on_withdrawal` on `input_state`
- Consider: should this affect the vanilla tariff system mechanically, or just use modifier approximations? The `state_tariff_import_add = -1.0` approach may not perfectly zero out tariffs if other modifiers stack. Test in-game.

---

## Article 3: Corporate Tax Exemption / Corporate Concessions

### Historical Context
European companies in colonial Africa and Asia operated under favorable terms — the British East India Company, Belgian concessions in the Congo, United Fruit Company in Central America, modern Special Economic Zones, Export Processing Zones where labor and environmental laws are relaxed. Multinational corporations lobby for regulatory exemptions as a condition of investment.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `company` |
| **Cost** | 100 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `corporate_charters` |

### Effects

**On the source country** (the one granting concessions to the foreign company):
- `country_company_throughput_bonus_add = 0.15` — 15% throughput bonus for all companies (engine limitation: this is country-wide, not per-company; see Design Alternatives below)

**Problem**: There is no per-company modifier in the engine. `country_company_throughput_bonus_add` is country-scoped and affects ALL companies in that country.

### Design Alternatives

**Option A: Country-wide modifier (simple but imprecise)**
Apply `country_company_throughput_bonus_add` to the source country. Every company benefits, not just the targeted one. This is mechanically weak — it doesn't feel targeted enough.

**Option B: Building-targeted via `on_entry_into_force` (complex but precise)**
In `on_entry_into_force`, iterate the company's buildings and apply throughput modifiers directly to each building's state:
```
scope:article_options = {
    input_company = { save_scope_as = target_company }
    source_country = {
        every_scope_state = {
            every_scope_building = {
                limit = {
                    exists = owning_company
                    owning_company = scope:target_company
                }
                state = {
                    add_modifier = {
                        name = corporate_concession_state_modifier
                        # No days = permanent until removed
                    }
                }
            }
        }
    }
}
```
**Problem**: Buildings can change ownership, new buildings can be built by the company, etc. This is a snapshot at treaty time, not a living effect. Would require periodic on_action updates.

**Option C: Country-wide throughput + political costs**
Accept the country-wide nature and balance with significant political costs. The concession represents a general weakening of labor/environmental standards to attract foreign investment. This is historically accurate to how concessions worked — they degraded conditions country-wide, not just in one factory.

**Option D: Building-specific throughput with general penalty (recommended)**
Use building-specific country modifiers (e.g., `building_textile_mills_throughput_add`) to target the concession company's industry. Combine with a general throughput penalty so that granting a concession is a net negative for non-concession industries. For example: reduce all building throughput by 10% but add 20% to the specific industry → net +10% for the concession company's building type, -10% for everything else. This makes stacking multiple concessions increasingly painful, since each one adds another -10% general penalty.

The `company` input tells us which company is targeted; the company's `building_types` block identifies which building-specific modifiers to apply. This requires per-company-type logic in `on_entry_into_force` (a switch on the company's building types).

### Recommended Design (Option D)

**Source modifier** (country granting concessions):
- `building_throughput_mult = -0.1` — General throughput penalty (represents regulatory degradation)
- `state_radicals_from_political_movements_mult = 0.25` — Workers radicalize against exploitative conditions
- `country_authority_add = -200` — Governance cost of enforcing foreign corporate privileges

**On entry into force** (applied to source country based on the selected company's building types):
- Building-specific throughput bonus (e.g., `building_textile_mills_throughput_add = 0.2`) via a modifier determined by the company type
- This creates a net +10% for the concession industry and -10% for everything else

**Target modifier** (country whose company benefits):
- `country_prestige_mult = 0.03` — Prestige from economic imperialism
- `country_company_construction_efficiency_bonus_add = 0.1` — Company constructs more efficiently

### Non-Fulfillment
Source country must not have `law_command_economy` or `law_cooperative_ownership` (collectivized economies don't grant corporate concessions):
```
non_fulfillment = {
    consequences = freeze
    conditions = {
        monthly = {
            scope:article = {
                source_country = {
                    NOR = {
                        has_law = law_type:law_command_economy
                        has_law = law_type:law_cooperative_ownership
                    }
                }
            }
        }
    }
}
```

### AI Design
- `article_ai_usage = { request }` — Great powers demand concessions from weaker nations
- Source reluctance: high if trade unions or intelligentsia are in government, low if industrialists dominate
- Target benefit: commercial interest, trade volume with source country

### Event Hooks
- **Labor Unrest** — Workers in the concession country strike against foreign corporate privileges
- **Environmental Scandal** — Foreign company's negligence causes pollution/disaster, source country must decide whether to crack down

---

## Article 4: Enforce Privatization

### Historical Context
IMF structural adjustment programs requiring privatization of state enterprises; post-Soviet privatization; colonial powers forcing open markets; Washington Consensus conditionality. A stronger nation forces the weaker to privatize state-owned buildings.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | None (country-wide effect) |
| **Cost** | 150 |
| **Flags** | `can_be_enforced`, `hostile` |
| **Usage Limit** | `once_per_side` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `stock_exchange` or `central_banking` |

### Effects

The engine has a built-in `country_force_privatization_bool` modifier (used by `law_laissez_faire`). This is the most direct approach.

**Source modifier** (country being forced to privatize):
- `country_force_privatization_bool = yes` — Forces all government-owned buildings to be privatized (vanilla mechanic)
- `country_authority_add = -200` — Massive authority drain from losing control of state enterprises

**Target modifier** (the country demanding privatization):
- `country_prestige_mult = 0.05` — Prestige from imposing economic ideology

### Possible / Can Ratify
```
possible = {
    # Only makes sense if the source has state-owned buildings
    scope:other_country = {
        NOT = {
            has_law = law_type:law_laissez_faire  # Already privatized
        }
    }
}

can_ratify = {
    scope:source_country = {
        NOR = {
            has_law = law_type:law_laissez_faire  # Already forced
            has_law = law_type:law_command_economy  # Would require law change first
        }
    }
}
```

### Non-Fulfillment
Should always be fulfilled unless they change to command economy, I think.

### AI Design
- `article_ai_usage = { request }` — AI demands from weaker nations
- Nations with `law_laissez_faire` or `law_interventionism` + `ig_industrialists` in power are most likely to demand this
- Source reluctance: extremely high for `law_command_economy` countries, moderate for `law_interventionism`, low for countries already trending toward privatization

### Implementation Notes
- This is relatively simple since `country_force_privatization_bool` already exists as a modifier
- Consider pairing with `law_commitment` to `law_laissez_faire` for a more comprehensive "structural adjustment" package — but that's a diplomatic play design question, not an article implementation question
- The `country_disable_non_company_privatization_bool` modifier could also be relevant (prevents privatization EXCEPT to companies)

---

## Article 5: Arms Licensing Agreement

### Historical Context
Lend-Lease programs; Soviet arms exports to client states; French Mirage jet sales; modern US Foreign Military Sales (FMS) program; licensed production of foreign weapons (e.g., Japan producing F-15s under license). One country grants another access to its military technology in exchange for economic benefits to its arms industry.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `company` (arms company in the source/provider country) |
| **Cost** | 200 |
| **Flags** | `can_be_renegotiated`, `friendly` |
| **Usage Limit** | `once_per_side` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `military_statistics` (era 3+) |
| **Relations** | `relations_progress_per_day = 0.5`, `relations_improvement_max = 30` |

### Direction Convention
- **Source country** = the arms provider (their company benefits from exports)
- **Target country** = the one receiving arms technology

The company input selects one of the source country's companies (the arms manufacturer). Since this is a benefit to the source, they "offer" it — so `article_ai_usage = { offer }`.

### Effects

**Source modifier** (arms provider):
- `country_military_goods_cost_mult = 0.05` — Slight domestic military cost increase (production capacity diverted to exports)
- Consider adding a throughput bonus for the specific arms company's building types (similar to Corporate Concessions Option D), but this may be unnecessary — the main benefit to the source is diplomatic influence and the arms company is a flavor input rather than a mechanical target

**Target modifier** (arms recipient):
- `country_military_tech_spread_mult = 0.15` — Faster military tech adoption from using foreign weapons
- `unit_experience_gain_mult = 0.1` — Training benefits from modern equipment
- `country_military_goods_cost_mult = -0.1` — Cheaper military goods (foreign supplier subsidizes)

**Stacking guard:** The `once_per_side` usage limit means each pair of countries can only have one arms deal. However, a target could have arms deals with multiple different source countries. To prevent abuse (e.g., stacking 5 deals for -50% military goods cost), consider adding a `can_ratify` check that limits the target to at most one active arms licensing article, similar to the `science_aid` duplicate check.

### Company Valid Trigger
The selected company should be in the arms industry. Use an explicit list of arms-related company types:
```
company_valid_trigger = {
    OR = {
        # Country-specific arms companies
        is_company_type = company_type:company_krupp
        is_company_type = company_type:company_rheinmetall
        is_company_type = company_type:company_armstrong_whitworth
        is_company_type = company_type:company_schneider_creusot
        is_company_type = company_type:company_skoda
        is_company_type = company_type:company_manfred_weiss
        is_company_type = company_type:company_hanyang_arsenal
        is_company_type = company_type:company_foochow_arsenal
        is_company_type = company_type:company_imperial_arsenal
        is_company_type = company_type:company_izhevsk_arms_plant
        is_company_type = company_type:company_putilov_company
        is_company_type = company_type:company_famae
        is_company_type = company_type:company_colt_firearms
        is_company_type = company_type:company_william_cramp
        is_company_type = company_type:company_ansaldo
        is_company_type = company_type:company_john_brown
        is_company_type = company_type:company_trubia
        is_company_type = company_type:company_zastava
        is_company_type = company_type:company_fcm
        is_company_type = company_type:company_saint_etienne
        is_company_type = company_type:company_mitsubishi
        is_company_type = company_type:company_fundicao_ipanema
        is_company_type = company_type:company_rossi
        is_company_type = company_type:company_secn
        is_company_type = company_type:company_hispano_suiza
        is_company_type = company_type:company_stabilimento_tecnico_di_fiume
        is_company_type = company_type:company_wadia_shipbuilders
        # Generic arms/munitions companies
        is_company_type = company_type:company_basic_munitions
        is_company_type = company_type:company_basic_shipyards
    }
}
```
**Note:** This list should be verified at implementation time against all company types that have `building_arms_industry`, `building_artillery_foundry`, `building_munition_plant`, or `building_military_shipyard` in their `building_types` block.

### Possible
The source country (arms provider) should be militarily more advanced than the target:
```
possible = {
    # Source must have arms companies
    scope:other_country = {
        any_company = { owner = prev }
    }
    NOT = { has_war_with = scope:other_country }
    # Source should be more militarily advanced (science_aid pattern)
    root.techs_researched > scope:other_country.techs_researched
}
```
Alternatively, could check specifically for military tech count rather than total techs. The `science_aid` article uses `root.techs_researched > scope:other_country.techs_researched` plus `root.country_rank > scope:other_country.country_rank` as the pattern.

### AI Design
- `article_ai_usage = { offer }` — Source country offers arms deals to build influence
- Evaluation: Military-focused AI more likely to request. Nations at war or with rivals evaluate higher.
- Source wants: allies, influence, money. Target wants: military edge.
- Should deprioritize if countries are rivals or have poor relations

### Event Hooks
- **Technology Transfer Scandal** — Arms secrets leak to a third country
- **Arms Embargo Violation** — If the target goes to war with a country friendly to the source, the source faces pressure to cancel the deal

---

## Article 6: Religious Mission Rights

### Historical Context
Missionary activity in colonial territories; the "Christianization" of Africa, Asia, and the Americas; Jesuit missions in Japan and China; Ottoman Capitulations granting religious privileges to foreign powers; the French protectorate over Catholics in the Levant. A foreign power secures the right to send missionaries to convert populations.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `state` |
| **Cost** | 50 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `colonization` or `pan_national_agitation` |
| **Relations** | `relations_progress_per_day = -0.25` |

### Effects

**On the target state** (via `on_entry_into_force` modifier):
- `state_conversion_mult = 1.0` — Doubles conversion rate (missionaries actively proselytizing)

The conversion direction in V3 is toward the state religion of the owning country. This article is interesting because the *target* power wants the population converted to THEIR religion, but the conversion mechanic pushes toward the source country's state religion. 

**Design Challenge**: V3's conversion mechanic converts pops to the country owner's religion — not to a specific foreign religion. We can't directly make pops convert to the *target country's* religion via the `state_conversion_mult` modifier.

**Workaround approaches:**

**Option A: Boost conversion rate in source country's state (simple but wrong direction)**
The modifier boosts conversion speed. Since conversion pushes toward the source country's state religion, meaning the source country's own pops convert faster. This doesn't match the fantasy of missionaries going abroad.

**Option B: Periodic `convert_population` effect (recommended)**
Use an `on_yearly_pulse_state` on_action to check for states with a `religious_mission_rights` variable, then use the `convert_population` effect to shift pops toward the target country's religion. This is the same effect used by vanilla decisions (Oman ibadi conversion, Japan Shinto conversion, power bloc force state religion).

Syntax: `convert_population = { target = <religion_scope> value = <fraction> }` (state-scoped)

The on_action would:
1. Check if the state has a `religious_mission_rights` variable
2. Scope to the variable's stored target country to get their religion
3. Call `convert_population = { target = scope:mission_country.religion value = 0.05 }` (5% of pops per year)

**Option C: Reduce conversion + boost migration (simpler alternative)**
Rather than actively converting, the article:
- Reduces conversion resistance by majority religion: `state_conversion_mult = -0.5`
- Adds `state_migration_pull_add = 5` to attract co-religionists from the target country

### Recommended Design (Option B + state modifier)

**On entry into force:**
- Set `religious_mission_rights` variable on the state, storing the target country as scope
- Apply a state modifier with `state_conversion_mult = -0.25` (slow down counter-conversion)
- Apply a state modifier with `state_migration_pull_add = 5` (draw co-religionists)

**Periodic effect** (via `on_yearly_pulse_state`):
- Check for `has_variable = religious_mission_rights`
- `convert_population = { target = scope:mission_country.religion value = 0.05 }` — 5% of pops shift toward the missionary power's religion each year

**On break/withdrawal:**
- Remove the state variable and modifier

**Source modifier** (government granting mission rights):
- `country_authority_add = -100` — Political cost of allowing foreign religious influence
- `country_legitimacy_base_add = -5` — Looks weak to domestic devout population
- Consider adding `ig_approval_negative_modifier` on `ig_devout` via `on_entry_into_force` for IG reaction

**Target modifier** (the missionary power):
- `country_prestige_mult = 0.03` — Prestige from spreading the faith

### Non-Fulfillment
Source country must not have `law_state_atheism` (which bans religion entirely):
```
non_fulfillment = {
    consequences = freeze
    conditions = {
        monthly = {
            scope:article = {
                source_country = {
                    NOT = { has_law = law_type:law_state_atheism }
                }
            }
        }
    }
}
```

### AI Design
- `article_ai_usage = { request }` — Religious powers demand mission rights
- Priority scales with: devout IG political strength, `law_state_religion` active, cultural/religious mismatch with target state
- Source reluctance: high if devout IG is in government and state religion differs

### Event Hooks
- **Religious Tension** — Local clergy clash with foreign missionaries
- **Mass Conversion** — A community converts, causing social upheaval
- **Missionary Expelled** — Source country throws out missionaries, triggering diplomatic incident

---

## Article 7: Extradition Treaty / Extraterritoriality

### Historical Context
Extraterritoriality in China and Japan (foreign citizens judged by foreign courts); Ottoman Capitulations; modern extradition treaties; diplomatic immunity; Status of Forces Agreements (SOFA). Two distinct but related concepts that could be separate articles:

### Article 7A: Extradition Treaty

**Design:** `mutual` article. Both sides agree to return fugitives. Reduces crime (turmoil), boosts law enforcement effectiveness.

| Property | Value |
|---|---|
| **Kind** | `mutual` |
| **Required Inputs** | None |
| **Cost** | 50 |
| **Flags** | `can_be_renegotiated`, `friendly` |
| **Usage Limit** | `once_per_side` |
| **Unlock Tech** | `international_relations` |
| **Relations** | `relations_progress_per_day = 0.25`, `relations_improvement_max = 20` |

**First modifier** (both sides receive):
- `country_authority_add = 25` — Better enforcement from cooperation
- `state_turmoil_effects_mult = -0.05` — Slightly less turmoil (fugitives can't flee across borders)
- `country_bureaucracy_mult = -0.05` — Administrative overhead of processing extradition requests

**Possible / flavor tie-in:** Could require both countries to have `institution_police` at level 1+ (or a dedicated police law like `law_dedicated_police` or `law_militarized_police`). This gates the article behind having a functioning law enforcement system and adds flavor — you can't extradite criminals if neither side has a police force to catch them.

**Second modifier:**
- Same as first (mutual)

### Article 7B: Extraterritoriality Rights

**Design:** `directed` article. Foreign citizens in the source country are subject to the target country's laws, not local laws. Humiliating but historically common for weaker nations.

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | None (country-wide) or `state` (per-state) |
| **Cost** | 100 |
| **Flags** | `can_be_enforced`, `hostile` |
| **Usage Limit** | `once_per_side` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `international_trade` |
| **Relations** | `relations_progress_per_day = -0.5` |

**Source modifier** (humiliated nation granting extraterritoriality):
- `country_prestige_mult = -0.1` — National humiliation
- `country_legitimacy_base_add = -15` — Government looks weak
- `country_authority_add = -200` — Can't enforce own laws on foreigners

**Target modifier** (nation whose citizens enjoy extraterritoriality):
- `country_prestige_mult = 0.05` — Imperial prestige
- `country_treaty_leverage_generation_add = 200` — Leverage from controlling legal jurisdiction

### AI Design (7B)
- `article_ai_usage = { request }` — Only demanded by significantly stronger nations
- Rank difference matters enormously — this is a tool of imperialist humiliation
- Source extremely reluctant; multiplied by prestige concern

---

## Article 8: Demilitarized Zone

### Historical Context
The Rhineland DMZ after WWI; the Korean DMZ; the Sinai Peninsula after Camp David; the Åland Islands; naval limitations in the Black Sea (Treaty of Paris 1856). A treaty forbids military buildings in a specific state. Violation during war gives the other side a bonus.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `state` |
| **Cost** | 75 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `international_relations` |
| **Relations** | `relations_progress_per_day = -0.25` |

### Effects

**On the target state** (via `on_entry_into_force` modifier):
- `state_conscription_rate_mult = -1.0` — No conscription in the DMZ (effectively disables military recruitment)
- `state_building_barrack_max_level_add = -1000` — Prevents construction of barracks (effectively caps at 0)
- `state_building_naval_base_max_level_add = -1000` — Prevents construction of naval bases

**Source modifier** (country forced to demilitarize):
- `country_authority_add = -25` — Sovereignty cost
- `country_prestige_add = -5` — National humiliation

**Note:** Existing barracks/naval bases in the state at the time of the treaty would need to be handled. The max level cap should prevent expansion and cause existing buildings to become over-capacity (the engine should auto-downsize them over time). If not, an `on_entry_into_force` effect could forcibly remove levels. The `non_fulfillment` block below provides a secondary enforcement mechanism.

### Non-Fulfillment (Secondary Enforcement)
```
non_fulfillment = {
    consequences = freeze
    max_consecutive_contraventions = 3
    conditions = {
        monthly = {
            scope:article = {
                input_state = {
                    OR = {
                        any_scope_building = {
                            is_building_type = building_barracks
                            level >= 1
                        }
                        any_scope_building = {
                            is_building_type = building_naval_base
                            level >= 1
                        }
                    }
                }
            }
        }
    }
}
```
**Note**: Need to verify if `scope:article.input_state` works in `non_fulfillment` conditions. If not, use variable tracking.

### DMZ Violation Event
When a war breaks out between the two parties, the target country (the one that imposed the DMZ) gets a temporary combat advantage specifically in the demilitarized state. This represents the strategic value of the DMZ — the enemy cannot pre-fortify or pre-position troops there, giving the enforcing power an initial window of advantage.

**Event trigger** (wired to `on_war_started` or `on_diplomatic_play_started`): Check if the source country has a demilitarized state.

**Effect:** The target country receives a short-term combat modifier applied to the DMZ state:
- `battle_offense_owned_province_mult = 0.15` and `battle_defense_owned_province_mult = 0.15` for `short_modifier_time`
- Applied to the target country's forces fighting in the DMZ state
- Represents the strategic advantage of the enemy having to rush troops into an unfortified position

### State Valid Trigger
```
state_valid_trigger = {
    scope:input = {
        owner = root
        is_capital = no
        # Ideally: should border the target country or be coastal
        OR = {
            scope:other_country = { is_adjacent_to_state = prev }
            is_coastal = yes
        }
    }
}
```

### AI Design
- `article_ai_usage = { request }` — Demanded after wars or in diplomatic plays
- Evaluation: AI demands this for border states, especially after a defensive war
- Source reluctance: scales with military strength, strategic importance of the state

---

## Article 9: Climate Accords

> **Design uncertainty:** This article may not be mechanically interesting enough to justify implementation. The existing Global Warming journal entry system already handles climate policy via scripted buttons. A treaty article would need to add something meaningfully different from what the JE provides. Consider whether this should be kept or folded into the JE system.

### Historical Context
Kyoto Protocol, Paris Agreement, Montreal Protocol. Nations commit to reducing greenhouse gas emissions. Integrates with the mod's existing Global Warming system.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `mutual` |
| **Required Inputs** | None |
| **Cost** | 100 |
| **Flags** | `can_be_renegotiated`, `friendly` |
| **Usage Limit** | `once_per_side` |
| **Unlock Tech** | `environmentalism` (or a late-game tech) |
| **Relations** | `relations_progress_per_day = 0.25`, `relations_improvement_max = 20` |

### Effects

**First modifier** (both countries):
- `country_greenhouse_gas_emissions_mult = -0.1` — 10% reduction in greenhouse gas emissions (integrates with existing Global Warming system)
- `state_pollution_generation_mult = -0.05` — 5% reduction in pollution generation (already wired up to on_actions)

**Second modifier**: Same as first.

**On entry into force**: Both countries get a variable `climate_accord_partner` pointing to the other. This integrates with the existing Global Warming journal entry system — countries with active climate accords could get bonus progress toward emissions targets or unlock additional scripted buttons.

### Integration with Global Warming System
The Global Warming JE already uses scripted buttons (`gw_*`) for climate policies. The climate accord could:
- Unlock a new scripted button pair: "Fulfill Climate Accord" / "Withdraw from Climate Accord"
- Grant a modifier reducing `greenhouse_gas_emissions` by a percentage while active
- Could check `temperature_anomaly_display` and apply escalating pressure to maintain the accord

### Non-Fulfillment
Could track if either country's emissions are increasing (via script value comparison over time). Complex to implement — may be better as an event chain than a `non_fulfillment` block.

### AI Design
- `article_ai_usage = { offer request }` — Both sides can propose
- Environmentally progressive nations (high literacy, environmental laws) more likely
- Nations with heavy industry and low environmental regulation reluctant
- Great powers committed to climate leadership request this from major emitters

---

## ~~Article 10: Special Economic Zone~~ (Removed)

Removed — too much overlap with the Free Port Concession (Article 2). The Free Port already covers the core fantasy of a trade-privileged zone in a specific state.

---

## Article 11: No-Fly Zone / Airspace Control

> **Design uncertainty:** This concept may not fit well as a long-term treaty article. No-fly zones are typically short-term military enforcement actions, not standing bilateral agreements. Consider whether this is better modeled as a diplomatic play war goal or a temporary modifier from a peace deal, rather than a treaty article.

### Historical Context
Post-Gulf War no-fly zones over Iraq; NATO enforcement over Bosnia and Libya; Cold War ADIZ (Air Defense Identification Zones). A military power imposes airspace restrictions on another country.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `strategic_region` |
| **Cost** | 150 |
| **Flags** | `can_be_enforced`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `military_aviation` or `jet_fighter` (requires air power tech) |

### Effects

**Source modifier** (country under the no-fly zone):
- `country_military_goods_cost_mult = 0.15` — Military costs increase (can't use air assets freely)
- `country_prestige_mult = -0.1` — National humiliation (foreign jets patrol your skies)

**Target modifier** (enforcing power):
- `country_military_goods_cost_mult = 0.1` — Cost of enforcement operations
- `country_prestige_mult = 0.05` — Projection of power

### Design Notes
- This is a prestige/humiliation article more than a mechanically deep one
- Could also reduce `unit_experience_gain_mult` for the source country (can't train air forces)
- Pairs well with Demilitarized Zone — one restricts ground forces, the other restricts air

---

## Article 12: Maritime Exclusion Zone / Territorial Waters

> **Design uncertainty:** Maritime exclusion zones are typically either unilateral declarations or part of multilateral international law, not bilateral treaties. This concept may not work well as a two-party agreement. Consider whether it should be reworked as a power bloc principle or a unilateral decision instead.

### Historical Context
Law of the Sea; Exclusive Economic Zones; British blockade of Argentina during the Falklands War; Chinese claims in the South China Sea; Russian claims in the Arctic. A power asserts control over maritime resources and shipping lanes in a strategic region.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `directed` |
| **Required Inputs** | `strategic_region` (ocean/coastal region) |
| **Cost** | 100 |
| **Flags** | `can_be_enforced`, `can_be_renegotiated`, `hostile` |
| **Usage Limit** | `once_per_side_with_same_inputs` |
| **Maintenance** | `target_country` |
| **Unlock Tech** | `ocean_liner` or `modern_navy` |

### Effects

**Source modifier** (country whose waters are restricted):
- `country_prestige_mult = -0.05` — Sovereignty violation
- `state_trade_capacity_mult = -0.1` — Trade disruption in coastal states of that region

**Target modifier** (enforcing naval power):
- `country_prestige_from_navy_power_projection_mult = 0.1` — Naval prestige
- `country_treaty_leverage_generation_add = 200` — Leverage from maritime dominance

### Design Notes
- The `strategic_region` input makes this geographically meaningful
- Enforcement makes most sense for naval powers (check `navy_power_projection > X`)
- Could tie into fishing/whaling building group throughput for the enforcing power

---

## Article 13: Space Cooperation Treaty

> **Design uncertainty:** This article may not be mechanically interesting enough to justify its own treaty article. The effects are essentially generic tech spread + prestige modifiers. Consider whether the wonder building integration (space elevator/solar collector bonuses) would be enough to make this feel unique, or if the concept is better handled by the existing `science_aid` article.

### Historical Context
International Space Station agreements; Apollo-Soyuz; European Space Agency partnerships; Outer Space Treaty (1967); Artemis Accords. Nations cooperate on space programs for mutual benefit.

### Mechanical Design

| Property | Value |
|---|---|
| **Kind** | `mutual` |
| **Required Inputs** | None |
| **Cost** | 200 |
| **Flags** | `can_be_renegotiated`, `friendly` |
| **Usage Limit** | `once_per_side` |
| **Unlock Tech** | A late-game space technology |
| **Relations** | `relations_progress_per_day = 0.5`, `relations_improvement_max = 40` |

### Effects

**First modifier** (both countries):
- `country_prestige_mult = 0.05` — Prestige from space cooperation
- `country_tech_spread_mult = 0.05` — Technology exchange from joint programs
- `country_military_goods_cost_mult = 0.05` — Cost of space program support (minor)

**Second modifier**: Same as first.

### Integration with Wonder Buildings
If both countries have space elevator or solar collector buildings, could provide bonus throughput or accelerated construction. Check via `on_entry_into_force`:
```
on_entry_into_force = {
    scope:article_options = {
        first_country = {
            any_scope_state = {
                any_scope_building = {
                    OR = {
                        is_building_type = building_space_elevator
                        is_building_type = building_solar_collector
                    }
                }
            }
            # Apply space cooperation bonus modifier
        }
    }
}
```

### AI Design
- `article_ai_usage = { offer request }` — Cooperative, both sides benefit
- Very attractive to technologically advanced nations
- Prestige benefit makes it appealing to Great Powers

---

## Additional Article Ideas (Simple Modifiers, No Complex Scripting)

### Forced Disarmament
Similar to Demilitarized Zone but country-wide: source must reduce military spending. Punitive post-war article.
- `source_modifier`: `country_military_wages_mult = -0.25`, `state_conscription_rate_mult = -0.5`
- Very hostile, high cost, enforceable

### Cultural Exchange Program
Mutual article boosting cultural acceptance between both countries.
- Both sides get: `state_yearly_cultural_acceptance_add = 1`, positive relations
- Friendly, low cost, good for allied nations
- Uses cultural acceptance rather than assimilation — represents mutual appreciation without forcing cultural identity loss

---

## Implementation Checklist (Per Article)

For each article implemented, these files need changes:

### Required Files
1. **`common/treaty_articles/<filename>.txt`** — Article definition (BOM-encoded)
2. **`common/static_modifiers/extra_modifiers.txt`** — Any new state-scoped modifiers applied via `on_entry_into_force`
3. **`localization/english/te_diplomacy_l_english.yml`** — Article loc keys:
   - `<name>:0 "Display Name"`
   - `<name>_desc:0 "Description"`
   - `<name>_effects_desc:0 "• Effect description"`
   - `<name>_article_short_desc:0 "[SOURCE_COUNTRY.GetNameNoFormatting] will ..."`
4. **`localization/english/te_modifiers_l_english.yml`** — Modifier name + desc loc keys (if new modifiers)
5. **`localization/english/te_concepts_l_english.yml`** — If new modifiers are defined in `extra_modifiers.txt`

### Conditional Files (if article uses state input + `on_entry_into_force` state modifiers)
6. **`common/scripted_effects/extra_effects.txt`** — Scripted effects for apply/remove state modifiers (reusable across break/withdrawal)
7. **`common/on_actions/extra_on_actions.txt`** — If periodic effects are needed (e.g., DMZ violation checks)
8. **`common/messages/extra_messages.txt`** — If violation/notification messages are needed
9. **`events/`** — Companion events (violation events, flavor events)

### GUI Files (only if new input types are used)
- Articles using `state`, `company`, `goods`, `law_type`, `strategic_region` — **no GUI changes needed** (already supported)
- Articles using `building_type` + `company` combination — would need GUI updates per the instructions in `copilot-instructions.md`

### After Implementation
- Run `python organize_loc.py` to sort localization
- Verify BOM encoding on all new `.txt` files
- Test in-game: check `debug.log` for parse errors, `error.log` for runtime errors
- If mod state server is running: `POST /reload` to pick up new articles

---

## Priority & Dependency Order

| Priority | Article | Complexity | Dependencies |
|---|---|---|---|
| **1** | Demilitarized Zone | Medium | State input, building max level modifiers, companion event |
| **2** | Free Port Concession | Medium | State input, state modifier, tariff testing |
| **3** | Minority Protection | Medium | State input, state modifier |
| **4** | Enforce Privatization | Low | Uses existing `country_force_privatization_bool` |
| **5** | Extradition Treaty | Low | Mutual, simple modifiers, police institution gate |
| **6** | Extraterritoriality | Low-Medium | Country modifiers only, prestige mechanics |
| **7** | Corporate Concessions | Medium | Company input (existing GUI), building-specific throughput design |
| **8** | Arms Licensing | Medium | Company input, arms company type filter, tech gate |
| **9** | Forced Disarmament | Low-Medium | Country modifiers, hostile/punitive |
| **10** | Cultural Exchange | Low | Mutual, cultural acceptance modifier |
| **11** | Religious Mission Rights | High | `convert_population` periodic effect, on_action integration |
| **12** | Climate Accords | High | Integration with Global Warming JE system, design uncertainty |
| **13** | No-Fly Zone | Low | Strategic region input, design uncertainty |
| **14** | Maritime Exclusion | Low | Strategic region input, design uncertainty |
| **15** | Space Cooperation | Medium | Integration with wonder buildings, design uncertainty |

Simpler articles (Privatization, Extradition, Extraterritoriality, Cultural Exchange) can serve as warm-up implementations. State-targeting articles (DMZ, Free Port, Minority Protection) share common patterns and should be built on a shared scripted effect template. The Religious Mission Rights article requires an `on_yearly_pulse_state` on_action for periodic `convert_population` effects. The Global Warming integration (Climate Accords) is the most complex due to cross-system dependencies. Articles marked with "design uncertainty" may not make it to implementation — they need further evaluation of whether they genuinely add to gameplay.
