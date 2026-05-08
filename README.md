# Vic3TimelineExtended

A large content mod for **Victoria 3** (Paradox Clausewitz engine) that extends the timeline well past the vanilla 1936 endpoint and adds a layered set of new gameplay systems on top — banking cycles, climate change, decolonization, nuclear weapons, a UN, a space race, cultural / cyber soft power, social-movement journal entries, treaty articles with entity selection, wonder buildings, a market-driven construction economy, and more. New eras run from 1919 (era 6) through "far future" (era 12), each with their own technologies, laws, buildings, production methods, ideologies, and events.

The repo is both a Paradox-script content mod *and* a Python toolchain that parses the mod (and vanilla) into a queryable HTTP service, regenerates derived files on save, and validates the script against engine constraints. Most of the systems below are layered — they share scripted-effect helpers, on-action wiring, and a common dynamic-modifier pattern documented in `docs/scripting_best_practices.md` and `docs/mod_systems.md`.

## Setting up on a new machine

```bash
git clone <repo-url> Vic3TimelineExtended
cd Vic3TimelineExtended
python3 scripts/setup.py
```

The setup script creates a `.venv`, installs the Python tooling deps, then auto-detects (or prompts for) the Steam install of Victoria 3, your Paradox documents folder, and the deploy target. It writes a gitignored `paths.local.json` with the results and runs a dry-run deploy to verify everything resolves. Re-run any time paths move.

WSL is the supported primary platform — the autodetector reads Steam's `libraryfolders.vdf` and the Windows username via `cmd.exe`. On native Linux or Windows the script falls through to prompts.

For vanilla-vs-mod disambiguation, the tooling expects a vanilla `script_docs` snapshot at the path you give for `vanilla_snapshot_docs_path` (default `~/src/vic3/docs/`). Setup warns if it's missing and prints the manual refresh workflow (launch vanilla unmodded → `script_docs` in the in-game console → copy logs).

Per-path env-var overrides also work, useful for one-off invocations: `VIC3_BASE_GAME`, `VIC3_MOD_DEPLOY_TARGET`, `VIC3_VANILLA_DOCS_SNAPSHOT`, `VIC3_VANILLA_REPO`, `VIC3_VANILLA_DOCS_RUNTIME`, `VIC3_GAME_LOGS`. See `path_constants.py` for the resolution order.

> Most documentation under `docs/` is written for AI coding agents (Claude Code is the primary one). The prose may sound terse or workflow-heavy in places — the project's README index is `docs/README.md`.

---

## Table of contents

- [What's added at a glance](#whats-added-at-a-glance)
- [Game rules (toggleable systems)](#game-rules-toggleable-systems)
- [Gameplay systems](#gameplay-systems)
- [Repository layout](#repository-layout)
  - [Mod data (`common/`, `events/`, `gui/`, `localization/`, `gfx/`, `map_data/`)](#mod-data)
  - [Python tooling (repo root)](#python-tooling-repo-root)
  - [Scripts (`scripts/`)](#scripts-scripts)
  - [Documentation (`docs/`)](#documentation-docs)
- [Developer workflow](#developer-workflow)
- [Credits](#credits)

---

## What's added at a glance

- **7 new eras** (eras 6–12, ~1919 → far future) with ~160 mod-side technologies covering modern industry, computing, biotech, aerospace, AI, post-scarcity manufacturing, and beyond. Tech costs scale aggressively (era 6 = 25k, era 12 = 2M innovation).
- **20+ custom journal entries** (banking cycle, global warming, colonial empire, civil rights, heir education, UN, nuclear program, world war, 9 space-race milestones, 8 social-movement JEs, cultural hegemony, covert warfare, strategic reserve, state collapse, custom religion, …).
- **30+ events files** covering banking crises, decolonization, social movements, modern elections, religious revival, treaty articles, the world war lifecycle, the space race, and more.
- **38 wonder buildings** (real-world monuments + 7 megaprojects: Space Elevator, Solar Collector, Orbital Battlestation, Mind Upload Nexus, Antimatter Facility, Nanofabrication Center, Consciousness Network).
- **~280 vanilla company-flavored buildings** (one per company), plus mod-side companies and charters.
- **132 mod-side laws** spanning new lawgroups (financial regulation, ministries of education / science / culture / environment / intel / urban planning / thought control, modern justice, civil rights, augmentation, women's rights, LGBTQ+ rights, post-scarcity welfare, …).
- **100+ extra goods, PMs, ship types, ship modifications, mobilization options, decrees, treaty articles, diplomatic actions, character traits, ideologies, and political movements.**
- **Engine extensions**: a market-driven construction system (built on the third-party Free Market Construction architecture), construction-cost-scaling vs GDP, migration crowding, dynamic homeland change, tourism, "Bulk Transportation" (relocalized merchant marine), pollution, SoL-expectation lag, formable countries, and dynamic country/treaty naming.

The toggleable subset of these (banking cycle, world war, etc.) is gated on per-game *game rules*; see the next section.

---

## Game rules (toggleable systems)

Thirteen mod systems can be turned on or off at game setup. Defaults below; full list in `common/game_rules/extra_game_rules.txt`. Disabled systems hide their journal entry, bypass their on-actions, and skip their events — but baseline content (laws, techs, buildings, modifiers) still applies.

| Rule | Default | What it gates |
|---|---|---|
| `banking_system_rule` | enabled | Banking cycle JE, crash contagion, fiscal-policy modifier |
| `global_warming_rule` | enabled | CO₂ tracking, climate JE, warming modifiers |
| `cultural_hegemony_rule` | enabled | Soft-power JE and on-action |
| `covert_warfare_rule` | enabled | Cyber operations, digital sovereignty JE, 9 covert diplomatic actions |
| `heir_education_rule` | enabled | Heir education JE and focus modifiers |
| `united_nations_rule` | enabled | UN JE, vote events, specialized agencies |
| `nuclear_weapons_rule` | enabled | Nuclear program JE, strike events, nuclear-disarmament treaty article |
| `decolonization_rule` | enabled | Decolonization events, colonial-collapse absorption |
| `space_race_rule` | enabled | Space race JEs and events |
| `social_movements_rule` | enabled | 8 social-movement JEs and event chains |
| `world_war_rule` | **disabled** | World War JE leadup → active → post-war lifecycle |
| `custom_religions_allowed_rule` | **disabled** | Custom-religion creator JE and events |
| `universal_aptitude_traits_rule` | **disabled** | Assigns admin/diplo/military aptitude traits to *all* adult characters, not just rulers/politicians/agitators/officers |

Loc keys for each rule live in `localization/english/te_game_rules_l_english.yml`. The gating pattern (`is_shown_when_inactive`, on-action `return = yes` guards, etc.) is documented in `docs/mod_systems.md` § Game Rules.

---

## Gameplay systems

This section is a high-level catalog. Each system has a more detailed entry in `docs/mod_systems.md` and (for journal-entry-driven systems) `docs/journal_entry_systems.md`. File-path pointers below cover the *script* side; localization is split across `localization/english/te_*_l_english.yml` (auto-organized by `organize_loc.py` — never hand-edit categorization, only keys).

### Economy & finance

- **Banking cycle (`je_banking_cycle`)** — 7-tier phase economy (panic → frenzy) with momentum, bubble pressure, asymmetric crash detection, and contagion via trade ties. 60+ scripted buttons spanning market, command-economy, and cooperative-ownership tool sets. Two `script_only` modifiers (`country_banking_random_momentum_mult`, `country_banking_crash_chance_mult`) let laws and techs tune volatility and crash chance.
  - Files: `common/journal_entries/je_banking.txt`, `common/scripted_effects/banking_cycle_effects.txt`, `common/scripted_buttons/banking_alt_economy_buttons.txt`, `common/scripted_progress_bars/extra_progress_bars.txt`, `events/banking_cycle_events.txt` (~77 events).
- **Construction as a market good (FMC architecture)** — replaces the monolithic country-construction resource with a three-layer chain: vanilla construction sector produces a `construction` good → market clears it → an auto-placed `fmc_building_construction_site` consumes it and produces vanilla `country_construction_add` for the FCFS queues. Buildings consume the construction good as ongoing maintenance; richer countries pay more (see below).
  - Files: `common/buildings/te_construction_market_site.txt`, `common/production_methods/te_construction_market_pms.txt`, `common/scripted_effects/te_construction_market_*.txt`, `common/script_values/te_construction_market_*.txt`, `events/te_construction_market_*.txt`.
- **Construction cost scaling** — `goods_input_construction_mult` scales with GDP-per-capita, making construction more expensive for richer countries (linear from 1× at the floor to 10× at the ceiling). Wired through `on_yearly_pulse_country`. Files: `common/static_modifiers/extra_modifiers.txt`, `common/script_values/extra_script_values.txt`, `common/on_actions/extra_on_actions.txt`.
- **Excess private construction penalty** — same pattern, multiplier-scaled static modifier reapplied yearly when private construction exceeds capacity.
- **Strategic reserve (`je_strategic_reserve`)** — national stockpile system for grain, ammunition, and oil. Storing/withdrawing interacts with the market through transient hub-building modifiers; per-good signed weekly rate plus a shared step size, decay continuously. Skill `add-strategic-reserve-good` walks through extending it.
  - Files: `common/journal_entries/je_strategic_reserve.txt`, `common/buildings/strategic_reserve.txt`, `common/scripted_buttons/st_res_buttons.txt`, `common/scripted_effects/st_res_effects.txt`, `common/script_values/st_res_script_values.txt`, `common/static_modifiers/extra_modifiers.txt` (search `sr_`), `common/modifier_type_definitions/st_res_modifier_types.txt`, `gui/journal_entry_widgets/strategic_reserve_widget.gui`, `docs/strategic_reserve_system.md`.
- **Bulk Transportation** — vanilla `merchant_marine` engine ID is preserved but relocalized to "Bulk Transportation"; producers expand from Ports to railways, motorways, airports, spaceports, trading houses, and modern logistics PMs. 91 consumer PMs. See `docs/mod_systems.md` § Bulk Transportation.
- **Resource deposits** — `deposits_config.json` + `resources.py` regenerate map state-region files with mod-tuned deposits.
- **Pop needs curves & buy packages** — `pop_needs_curves.py` regenerates `common/buy_packages/00_buy_packages.txt`; covers convenience, services, and luxury good consumption against SoL/strata.
- **SoL Expectations System** — adaptive expectation lag: when SoL rises suddenly, expectations follow with a configurable half-life (default 5 years), creating contentment-then-correction dynamics. Vanilla `state_expected_sol_*` modifiers from techs/laws/IG traits are converted to `country_sol_expectations_target_add` via `INJECT:` files. Files: `common/scripted_effects/sol_expectations_effects.txt`, `common/static_modifiers/sol_expectations_modifiers.txt`, `common/on_actions/sol_expectations_on_actions.txt`, plus `sol_expectations_vanilla_injections.txt` under `technologies/`, `laws/`, `interest_group_traits/`.

### Diplomacy & geopolitics

- **United Nations (`je_united_nations`)** — full UN simulation: founding, membership, authority bar (0–100) with drift mechanics, Security Council with veto power, expulsion votes, 16 vote topics, 8 specialized agencies (WHO, UNESCO, ICJ, UNHRC, IAEA, UNEP, UNHCR, UNOOSA), graduated-binding-resolution model, and a `join_united_nations` treaty article.
  - Files: `common/journal_entries/je_united_nations.txt`, `common/scripted_buttons/un_buttons.txt`, `common/scripted_effects/un_vote_effects.txt`, `common/scripted_progress_bars/un_progress_bars.txt`, `common/script_values/un_script_values.txt`, `common/scripted_triggers/un_permanent_member_triggers.txt`, `common/on_actions/un_on_actions.txt`, `events/un_events.txt`, `events/un_vote_events.txt`. Generator `gen_un_button_descs.py` keeps loc in sync with effect bodies.
- **Decolonization (`je_colonial_empire`)** — stability progress bar (0–100), 8 policy buttons, 21 events covering negotiations, crackdowns, releases, GP stances, the Suez-crisis model, and post-independence partition / strongman / non-alignment events. Designed so most colonial powers except top GPs lose most colonies after the `decolonization` tech.
  - Files: `common/journal_entries/je_colonial_empire.txt`, `common/scripted_progress_bars/extra_progress_bars.txt`, `common/scripted_buttons/colonial_empire_buttons.txt`, `common/script_values/colonial_empire_values.txt`, `common/scripted_triggers/colonial_empire_triggers.txt`, `common/scripted_effects/decolonization.txt`, `common/scripted_effects/colonial_collapse_effects.txt`, `events/decolonization_events.txt`. Reviewed in `docs/decolonization_review.md`.
- **Colonial collapse** — separate from the JE; tiny non-player AI remnants are absorbed by neighbors or revert to decentralized once decolonization tech is widespread (see `colonial_collapse_effects.txt`).
- **Nuclear program (`je_nuclear_program`)** — Great Power-only progress bar; first-mover bonuses, stockpile, world-first detection. Diplomatic actions: `nuke_diplo_action`, `tactical_nuke_diplo_action`. Treaty articles: `nuclear_disarmament`, `nuclear_program_aid`, `nuclear_program_pause`. Files: `common/journal_entries/timeline_extended_journal_entries.txt`, `common/scripted_effects/nuclear_weapon_effects.txt`, `common/scripted_triggers/nuke_triggers.txt`, `common/diplomatic_actions/nuke.txt`, `events/nuclear_weapon_events.txt`.
- **World War (`je_world_war`)** — leadup → active → post-war lifecycle; ideology classification (democratic/communist/fascist/authoritarian/non-aligned); rearm/appease/lend-lease leadup buttons; total-war-economy / propaganda / rationing wartime buttons; strain & exhaustion at 2y / 4y; peace conference + war crimes + new order + new rivalry events. **Disabled by default.** Files: `common/journal_entries/world_war_je.txt`, `common/scripted_buttons/world_war_buttons.txt`, `common/scripted_triggers/world_war_triggers.txt`, `common/script_values/world_war_values.txt`, `events/world_war_events.txt`.
- **Treaty articles with entity selection** — extends vanilla treaty system with articles that target *companies*, states, goods, laws, etc. Implemented articles include corporate (`seize_company`, `disband_company`, `enforce_privatization`, `corporate_concessions`, `free_port_concession`), humanitarian (`minority_protection`, `cultural_exchange`, `religious_mission_rights`, `population_transfer`), military (`dmz_and_disarmament`, `nuclear_disarmament`, `nuclear_program_pause`, `intelligence_sharing_pact`, `joint_military_exercises`), aid/influence (`request_influence`, `extend_influence`, `crisis_resolution`, `education_aid`, `healthcare_aid`, `security_aid`, `science_aid`), environmental (`enforce_emissions_reduction`), and more.
  - Files: `common/treaty_articles/*.txt`, `common/scripted_effects/treaty_article_effects.txt`, `common/dynamic_treaty_names/te_dynamic_treaty_names.txt`, GUI hooks in `gui/right_click_menu.gui` / `gui/treaty_draft_panel.gui` / `gui/treaty_panel.gui`, `events/treaty_article_events.txt`. Design doc: `docs/treaty_articles_reference.md`.
- **Diplomatic-play escalation** — additional events and script values modeling mounting tensions during diplo plays. Files: `common/scripted_effects/dp_escalation_effects.txt`, `common/script_values/dp_escalation_script_values.txt`, `events/dp_escalation_events.txt`.
- **Modern elections** — events covering modern campaign dynamics, debates, and results in advanced suffrage countries. Files: `events/modern_election_events.txt`, `common/on_actions/modern_election_on_actions.txt`.
- **International relations** — assorted bilateral events tied to character interactions, diplo plays, and power blocs. Files: `events/international_relations_events.txt`.
- **Cultural hegemony (`je_cultural_hegemony`)** — share-based soft-power score from art production, prestige, SoL delta, recent tech firsts, monuments, megaprojects, and modifier hooks. Drives migration attraction, foreign-country expectation pressure, and legitimacy reduction on rivals. Player controls: cultural-program funding, world expositions, cultural institutes, global media campaign, cultural protectionism.
  - Files: `common/journal_entries/je_cultural_hegemony.txt`, `common/script_values/cultural_hegemony_script_values.txt`, `common/scripted_effects/cultural_hegemony_effects.txt`, `common/scripted_buttons/cultural_hegemony_buttons.txt`, `common/static_modifiers/extra_modifiers.txt` (search `cultural_hegemony`), `common/modifier_type_definitions/cultural_hegemony_modifier_types.txt`, `common/on_actions/cultural_hegemony_on_actions.txt`, `events/cultural_hegemony_events.txt`, `events/international_relations_events.txt` (events 2/3).
- **Covert / cyber warfare (`je_covert_warfare`)** — pact-based diplomatic actions for election interference, financial subversion, industrial / military espionage, influence campaigns, ideological subversion, destabilization, and (wartime) infrastructure sabotage / comms disruption. Intelligence Capacity (literacy + GDP + rank + modifiers), 4 funding levels, monthly detection rolls, electoral-confidence reduction on `on_election_campaign_end`. Defensive Digital Sovereignty score sourced from techs/laws/institutions.
  - Files: `common/journal_entries/je_covert_warfare.txt`, `common/diplomatic_actions/covert_operations.txt`, `common/scripted_effects/covert_warfare_effects.txt`, `common/scripted_buttons/covert_warfare_scripted_buttons.txt`, `common/script_values/covert_warfare_script_values.txt`, `common/static_modifiers/extra_modifiers.txt` (search `iw_` / `covert_`), `common/modifier_type_definitions/covert_warfare_modifier_types.txt`, `common/on_actions/covert_warfare_on_actions.txt`, `events/covert_warfare_events.txt`.

### Climate & environment

- **Global warming (`je_global_warming`)** — persistent JE tracking `temperature_anomaly_display` against a 4°C goal. 6 status tiers (negligible → catastrophic). Dynamic `global_warming` modifier scaled by current anomaly. 16 climate-policy buttons (carbon tax, renewables, climate adaptation, emission standards, reforestation, public transit, fossil fuel divestment, green building codes). Threshold + reversal events at 0.5°C / 1.0°C / 2.0°C / 3.0°C and (cooling) recovery events at the same milestones.
  - Files: `common/journal_entries/je_global_warming.txt`, `common/scripted_buttons/timeline_extended_scripted_buttons.txt` (search `gw_`), `events/environmentalism_events.txt`. The `enforce_emissions_reduction` treaty article (`common/treaty_articles/109_enforce_emissions_reduction.txt`) forces a market leader to keep all major mitigation policies active.
- **Pollution per state** — `pollution_on_action` (monthly state pulse) drives state-scoped pollution modifiers; consumed by GW and several event flows.
- **Environmental crisis JE (`je_environmental_crisis`)** — social-movement JE tracking environmental policy adoption. See `events/environmental_events.txt`.

### Society, culture & demographics

Eight **social-movement journal entries** model major modern movements. Each has a `modifiers_while_active` modifier, monthly pulse events, AI-tuned three-option choices, and a fail-state event. Documented at `docs/mod_systems.md` § Social Movement Journal Entries.

| JE | Trigger tech | Lawgroup / win condition | Events file |
|---|---|---|---|
| LGBTQ+ Rights | `LGBTQ_rights_movement` | `law_full_equality_and_protection` | `events/lgbtq_events.txt` |
| Second-wave feminism | `second_wave_feminism` | `law_protected_class` | `events/feminist_events.txt` |
| Human augmentation | `biohacking_and_human_augmentation` / `brain_computer_interfaces` | `law_regulated_augmentation_market` / `law_mandatory_augmentation` | `events/augmentation_events.txt` |
| Environmental crisis | `environmental_movement` / `pollution_control` | `law_ministry_of_the_environment` + investment ≥ 3 | `events/environmental_events.txt` |
| Digital rights | `automated_surveillance` / `cybersecurity` | `law_strong_privacy_rights` | `events/surveillance_events.txt` |
| Post-scarcity | `universal_basic_income` | `law_post-scarcity` | `events/post_scarcity_events.txt` |
| Mental health | `mental_health_awareness` | `law_rehabilitation_focused_criminal_justice` + social_security ≥ 4 | `events/mental_health_events.txt` |
| Decline of religion | `decline_of_organized_religion` | `law_no_ministry_of_religion` | `events/secular_events.txt` |

Plus:

- **Civil rights (`je_civil_rights`)** — minority-rights movement, status tiers from minority-rights law, monthly events. `common/journal_entries/je_civil_rights.txt`, `common/scripted_effects/civil_rights_effects.txt`, `events/movement_events_te.txt`.
- **Religious revival** — 7 events (television, pop culture, social media, civil rights, globalization, sexual revolution, social-justice movements) counterbalance Devout-IG decline; per-religion variant text (Islamic, Dharmic, Jewish, default). `events/religious_revival_events.txt`, `common/static_modifiers/extra_modifiers.txt` (`rre_*`).
- **Custom religion (`je_create_new_religion`)** — player-only multi-stage wizard for creating a custom religion (ideologies, traits, name, religious group). `common/journal_entries/timeline_extended_journal_entries.txt`, `common/religions/custom_religion.txt`, `common/customizable_localization/zzz_extra_custom_loc.txt`, `common/scripted_buttons/timeline_extended_scripted_buttons.txt`.
- **Political lobbies extension** — additional lobby types beyond vanilla. `common/political_lobbies/01_extended_lobbies.txt`, `common/political_lobby_appeasement/01_extended_appeasement.txt`, `common/scripted_effects/extended_lobby_effects.txt`. Design doc: `docs/political_lobbies_design.md`.
- **Modern political movements & parties** — three new parties (`green_party`, `populist_party`, `technocratic_party`), modifications to vanilla movements, new ideological movements. `common/parties/`, `common/political_movements/`, `common/political_movement_pop_support/`.
- **Heir education (`je_heir_education`)** — EU4/CK3-style heir mentorship: 8 focus toggles across attribute / ideology / IG axes, monthly probabilistic gain, 5-tier trait resolution, hidden intelligence stat, rebel-child mechanic. 15 ruler aptitude traits. `common/journal_entries/je_heir_education.txt`, `common/scripted_effects/heir_education_effects.txt`, `common/scripted_buttons/heir_education_buttons.txt`, `common/character_traits/ruler_aptitude_traits.txt`, `events/heir_education_events.txt`. Monte Carlo sim at `sim_heir_education.py` (project root, when present).
- **State collapse (`je_state_collapse`)** — failed-state mechanic: when average SoL drops below ~4, infrastructure degrades weekly and at 52 weeks all institutions reset and `failed_state_modifier` applies. `common/journal_entries/timeline_extended_journal_entries.txt`, `common/scripted_effects/extra_effects.txt`.
- **Migration crowding** — density-based (`state_population / arable_land`) reduction in migration pull, scaled quadratically up to a 10× density knee then linearly. Counter-modifier `state_migration_crowding_density_mult` from `institution_ministry_of_urban_planning`.
- **Dynamic homelands** — yearly state-pulse mechanic that creates / removes homelands based on cultural acceptance and population thresholds.
- **Cultural acceptance** — extended yearly cultural-acceptance accumulation tied to homeland status and policies.
- **Tourism** — per-state tourism modifier scaled by city ranks, ports, transit, art production, parks, and monuments. ~3000 lines of state-region script values in `common/script_values/tourism.txt`. Re-applied via `on_yearly_pulse_state`.
- **City rank tiering** — city tier updates monthly, used in tourism and cultural displays.
- **Pop ideology / IG-feminism** — `apply_ideologies.py` regenerates `common/ideologies/modified.txt` from `ideology_modifications.py`; `ig_feminism.py` rewrites the 8 `common/interest_groups/00_*.txt` files to add or adjust female leader/commander/agitator probability.

### Military & defense

- **Combined arms** — barracks composition (mix of unit types in formations) drives a country-scope bonus when `country_combined_arms_bonus_enabled_bool` is set. `common/scripted_effects/combined_arms_effects.txt`, `common/scripted_triggers/combined_arms_triggers.txt`, `common/character_traits/combined_arms_traits.txt`. Wired in `extra_on_actions.txt` via `on_building_built` / `on_character_recruitment` / `on_military_formation_created`.
- **New combat unit types** — modern formations (mechanized, aviation, missile, drones, etc.). `common/combat_unit_types/extra_combat_units.txt`, `common/combat_unit_groups/extra_combat_unit_groups.txt`, `common/mobilization_options/extra_mobilization_options.txt`.
- **Ship types & modifications** — extended naval roster (modern ship classes) with utility modifications. `common/ship_types/`, `common/ship_modifications/`.
- **Resettlement** — special government program to relocate populations between states. `common/buildings/resettlement.txt`, `common/production_methods/resettlement_pms.txt`, `common/scripted_effects/extra_effects.txt`.

### Space & post-scarcity

- **Space race (`je_space_race_*`)** — 9 milestones (suborbital → orbital → moon landing / outer-system probe → moon base / Mars landing → interstellar probe (with passive 11-year transit JE) and repeatable Solar System Colonization with 34 globally-claimed colonies across 5 stages). Per-JE Safe vs Ambitious approach, 0–3 funding levels, "The First" bonuses, decaying-failure modifiers. Cross-system tied to UN, SpaceX company, Aerospace Industry, Space Elevator, Space Mine, and tourism. The Interstellar Probe lands one of 30 results across 4 categories (dead worlds, astrophysical wonders, biological discovery, intelligence/tech-signatures).
  - Files: `common/journal_entries/je_space_race.txt`, `common/scripted_buttons/space_race_buttons.txt`, `common/scripted_effects/space_race_effects.txt`, `common/scripted_triggers/space_race_triggers.txt`, `common/script_values/space_race_values.txt`, `common/static_modifiers/space_race_modifiers.txt`, `common/on_actions/space_race_on_actions.txt`, `events/space_race_events.txt`, `events/space_race_colony_events.txt`, `events/probe_result_events.txt`.
- **Wonder buildings & megaprojects** — 38 buildings, two-phase construction (buildable construction site → completed building via scripted effect on accumulated progress). Includes 7 megaprojects (Space Elevator, Solar Collector hub + receivers, Orbital Battlestation, Mind Upload Nexus, Antimatter Facility, Nanofabrication Center, Consciousness Network). `common/buildings/wonders.txt`, `common/scripted_effects/extra_effects.txt`, `common/scripted_triggers/wonder_triggers.txt`, `common/on_actions/wonder_events_on_actions.txt`, `events/wonder_events.txt`. Design pattern documented in `docs/wonder_buildings_reference.md`.
- **Vanilla company buildings** — every vanilla company gets a flagship building/PM cluster. `common/buildings/company_buildings.txt`, `common/company_types/extra_companies_vanilla_updates.txt`, `common/scripted_effects/company_building_cleanup_effects.txt` (cleanup on company disband). Reference: `docs/vanilla_company_buildings_reference.md`.

### Country shape

- **Formable countries** — additional formable nations with optional government-flavored dynamic names. `common/country_definitions/te_formable_countries.txt`, `common/country_formation/te_formable_countries.txt`, `common/dynamic_country_names/te_formable_countries.txt`, `common/geographic_regions/te_formable_regions.txt`, `common/diplomatic_plays/te_unification_plays.txt`. Skill `add-formable-country` automates additions.
- **Power blocs** — extra principles, principle groups, identities, and names. `common/power_bloc_*/`. The `gen_pb_principle_unlock_descs.py` generator keeps unlock-boolean loc descriptions in sync.
- **Government types** — additions for modern political forms. `common/government_types/timeline_extended_governments.txt`.
- **Country ranks** — revised rank thresholds. `common/country_ranks/extra_country_ranks.txt`.

### UI / GUI extensions

The `gui/` folder contains overrides for vanilla panels (treaty draft, market panel, military formation panel, power-bloc panel, states panel, production methods, building details, building browser, …), plus mod-specific additions:

- **States panel** — extra status widgets (Homeland Dynamics, Arable Land, Migration Crowding, Solar Collector slots, Antimatter Facility slots), plus a tourism breakdown.
- **Treaty draft / right-click menu** — entity-selection plumbing for treaty articles that target companies / states / goods / laws.
- **Power bloc formation / panel** — formation flow extensions and principle selection window.
- **Strategic Reserve widget** — `gui/journal_entry_widgets/strategic_reserve_widget.gui`.
- **Construction panel** — FMC integration (visualizes the construction-good market).

GUI modding patterns are documented in `docs/gui_modding_guide.md`.

---

## Repository layout

### Mod data

The Clausewitz engine reads only these top-level entries (everything else stays in the repo):

| Path | Contents |
|---|---|
| `common/` | All Paradox entity types — laws, technologies, buildings, journal entries, events triggers / effects / buttons, static modifiers, modifier-type definitions, treaty articles, decrees, decisions, ideologies, interest groups, …. The mod uses every vanilla entity type plus a few mod-only directories. |
| `events/` | One event file per system (banking_cycle, decolonization, world_war, space_race, …). 35+ files. |
| `gui/` | Overridden / extended panels and widgets. Many vanilla panels are copied wholesale and then patched. |
| `localization/english/` | YAML loc files. The 26 `te_*_l_english.yml` files are auto-categorized by `organize_loc.py`. The `replace/` subfolder contains overrides for vanilla loc keys (e.g. `merchant_marine` → "Bulk Transportation"). |
| `gfx/` | Event pictures, interface icons, portraits, unit illustrations. |
| `map_data/state_regions/` | Per-region resource deposits, regenerated from `deposits_config.json` by `resources.py`. |
| `.metadata/metadata.json` | Mod metadata. (Vic3 uses `.metadata/` instead of a top-level `descriptor.mod`; the deploy script copies the directory.) |
| `thumbnail.png` | Mod thumbnail. |

The `common/` directory is the bulk of the mod. Highlights of less-obvious subdirectories:

- `common/_meta/` — repo-side metadata: `modifier_patterns.yml` (catalog seed for the mod-state-server's pattern engine), `duplicate_image_allowlist.yml` (allowlist for the `/duplicate-images` validator).
- `common/script_values/` — keep big systems' math in their own files (`tourism.txt`, `colonial_empire_values.txt`, `un_script_values.txt`, `world_war_values.txt`, `dp_escalation_script_values.txt`, `te_construction_market_*.txt`, `space_race_values.txt`, `cultural_hegemony_script_values.txt`, `covert_warfare_script_values.txt`, `st_res_script_values.txt`, `gui_chart_script_values.txt`); the catch-all is `extra_script_values.txt`.
- `common/scripted_effects/` and `common/scripted_triggers/` — same per-system split. Cross-cut helpers live in `extra_effects.txt`, `ig_approval_effects.txt`, `build_effects.txt`, etc.
- `common/scripted_buttons/` — per-system button files (banking, colonial empire, covert warfare, cultural hegemony, heir education, space race, strategic reserve, UN, world war) plus a catch-all `timeline_extended_scripted_buttons.txt`.
- `common/scripted_progress_bars/` — per-system bars (`extra_progress_bars.txt`, `heir_education_progress_bars.txt`, `st_res_progress_bars.txt`, `un_progress_bars.txt`).
- `common/static_modifiers/` — `extra_modifiers.txt` is the catch-all (large); per-system files for SOL expectations, space race, heir education, law / ministry-law enactment, FMC.
- `common/modifier_type_definitions/` — every dynamic modifier type registered for mod entities. `extra_modifier_types.txt`, plus per-system files. Note the per-entity registration requirement for `building_*`, `goods_output_*`, `state_building_*`, and `ship_battle_against_ship_type_*` axes (see `docs/scripting_best_practices.md`).
- `common/on_actions/` — 20 files; the spine is `extra_on_actions.txt`, which wires monthly/yearly pulses, immediate triggers (on_company_disbanded, on_building_built, on_law_activated, …), and FMC market hooks. Pulse routing for every system is enumerated in `docs/mod_systems.md` § On-Actions Reference.
- `common/customizable_localization/` — custom loc functions (e.g. dynamic strategic-reserve labels, lobby naming).
- `common/game_concepts/` — concept definitions (`extra_concepts.txt`) used in tooltip cross-links.
- `common/_institutions.info`, `common/diplomatic_plays/_diplomatic_plays.info`, etc. — Paradox `.info` schema files (informational, not loaded by the engine).

A few directories are owned by **generators** — never hand-edit:

- `common/buy_packages/00_buy_packages.txt` ← `pop_needs_curves.py`
- `common/ideologies/modified.txt` ← `apply_ideologies.py` (input: `ideology_modifications.py`)
- `common/interest_groups/00_*.txt` ← `ig_feminism.py`
- `common/scripted_effects/extra_law_consistency_generated.txt` ← `gen_law_consistency.py`
- `localization/english/te_*_l_english.yml` ← `organize_loc.py` (categorization)
- `localization/english/te_un_button_effects_l_english.yml` ← `gen_un_button_descs.py` (effect descs)
- `localization/english/te_power_bloc_unlocks_l_english.yml` (`*_pb_principles_bool_desc` keys) ← `gen_pb_principle_unlock_descs.py`
- `map_data/state_regions/*.txt` ← `resources.py` (input: `deposits_config.json`)
- Cost-comment headers in `common/production_methods/extra_pms.txt` and `unique_pms.txt` ← `pm_costs.py`

A machine-readable map of file → owning generator is at `/auto-generated` on the mod-state server, and as documentation in `docs/auto_generated_files.md`.

### Python tooling (repo root)

Files at the repo root form the data-server spine plus a handful of one-shot generators that auto-run as post-load passes when the server reloads.

| File | Role |
|---|---|
| `paradox_file_parser.py` | Tokenizer + recursive-descent parser for Paradox `.txt`. Handles `REPLACE:` / `INJECT:` directives, BOM, brace nesting, comments. |
| `mod_state.py` | `ModState` class — loads vanilla + mod data via the parser, builds reverse-localization index, exposes `localize` / `unlocalize` / `search_localization`. |
| `mod_state_server.py` | Long-running HTTP service over `ModState` (port 8950). Logs to console (INFO) and `mod_state_server.log` (DEBUG). Auto-runs the post-load generators below on startup and `POST /reload`. |
| `mod_state_client.py` | CLI client over the server. `python mod_state_client.py <command> [args]`. |
| `mod_state_script.py` | Regenerates `docs/laws.txt`, `docs/technologies.txt`, `docs/buildings.txt`, `docs/goods.txt`, `docs/combat_units.txt` from parsed mod state. Auto-runs on server startup/reload. |
| `engine_docs_render.py` | Renders engine-doc logs into grep-able reference files in `docs/` (`vic3_triggers_effects_reference.md`, `triggers_summary.txt`, `effects_summary.txt`, `modifiers_summary.txt`, `country_triggers.txt`, …). |
| `event_magnitude_audit.py` | Detects hardcoded delta values in events for fast-scaling resources (prestige, treasury, bureaucracy, construction). Powers `/event-magnitude-audit`. |
| `game_log_reader.py` | Parses Vic3 runtime `error.log` / `debug.log` / `game.log` / `gui.log`. Powers `/logs`, generates `docs/error_log_digest.md`. |
| `pm_balance_lib.py` | Library: parses cost-comment annotations on PMs, computes balance flags (HIGH-PROFIT / DEEP-LOSS / THROUGHPUT / etc.). Used by the `balance` annotator. |
| `tech_unlocks_lib.py` | Library: walks every `common/<dir>/*.txt`, builds a tech → entities inverted index. Used by `/tech-unlocks` and `/unlocked-by`. |
| `annotators.py` | Tiny annotator registry — enriches entity-listing endpoint responses with audit-derived metadata via `?annotate=<name>` post-processing. |
| `path_constants.py` | Single source of truth for repo and Paradox install paths. Imported almost everywhere. |
| `pop_needs_curves.py`, `apply_ideologies.py`, `ig_feminism.py`, `pm_costs.py`, `resources.py`, `gen_pb_principle_unlock_descs.py`, `gen_un_button_descs.py`, `gen_law_consistency.py`, `organize_loc.py` | Idempotent transformers. Each exposes a `regenerate(mod_state=None)` entry point and runs as a post-load pass on every full server `/reload` (skip via `VIC3_SKIP_POST_LOAD_GENERATORS=1`); each also has a standalone CLI with `--dry-run` where applicable. |
| `ideology_modifications.py` | Plain Python data file: ideology attitude modifications consumed by `apply_ideologies.py`. |
| `deposits_config.json` | Resource-deposit declarations consumed by `resources.py`. |
| `vanilla_companies.txt` | Reference list of vanilla companies (input to company-building generators). |
| `test_*.py` | Unit / integration tests (parser, event balance, engine-coverage validator, post-load generators, pm-balance lib, pattern engine, annotators, tech-unlocks lib, duplicate-image detection, engine-log parsers, engine-docs renderer, event magnitude audit, game-log reader). Each module has a runnable `__main__`. |
| `requirements.txt` | Core deps: `requests`, `pyyaml`, `regex`, `numpy`. Image-generation deps (`torch`/`diffusers`/etc.) are commented out. Use `.venv/bin/python` for server-touching commands. |

### Scripts (`scripts/`)

| Path | Role |
|---|---|
| `scripts/deploy.sh` | rsync the engine-required top-level entries (`common/`, `events/`, `gui/`, `gfx/`, `localization/`, `map_data/`, `.metadata/`, `descriptor.mod`, `thumbnail.png`) into the Paradox mod folder. Dry-run by default; pass `--apply` to actually copy. Override target via `VIC3_MOD_DEPLOY_TARGET=...`. |
| `scripts/watch_deploy_on_edit.sh` | Continuous deploy watcher (inotifywait with polling fallback). Auto-started by VS Code via `.vscode/tasks.json`. |
| `scripts/format_paradox_tabs.py` | Re-tabs brace-based Paradox `.txt` files from inferred brace depth. Only safe for brace-format `.txt` — *never* on YAML / JSON / Python. `--check` for CI-style verification. |
| `scripts/snapshot_balance.py` | Snapshots PM balance metrics into `docs/balance_snapshot.json` for diff-based reviews. |
| `scripts/analysis/pm_balance.py` | Newton-Raphson solver for PM input amounts given target outputs and profit. |
| `scripts/analysis/pm_balance_audit.py` | Audits PM costs/profits across the catalog; emits the balance review under `docs/pm_building_balance_review.md`. |
| `scripts/analysis/pop_growth.py` | Pop-growth model (birthrate / mortality vs SoL). `--plot` for charts. |
| `scripts/analysis/combat_unit_balance_audit.py` | Combat-unit balance audit; output in `docs/combat_unit_balance_review.md`. |
| `scripts/analysis/tech_balance_audit.py` | Tech-tree balance audit; output in `docs/tech_tree_balance_review.md`. |
| `scripts/generators/gen_event.py` | Event scaffolder. `next-id` / `batch` / `scaffold` subcommands. Generates Paradox event boilerplate + loc keys from compact JSON specs. |
| `scripts/generators/gen_event_inventory.py` | Builds `docs/event_image_inventory.md` mapping events to their images / videos. |
| `scripts/generators/gen_loc_files.py` | Generates loc YAML for `extra_law_events` and `ministry_law_events`. |
| `scripts/generators/gen_banking_events.py` | Generator for banking-cycle event templates. |
| `scripts/generators/gen_vanilla_company_buildings.py`, `gen_vanilla_company_injects.py` | Generates the vanilla-company-building cluster (one building/PM set per vanilla company) and the corresponding `INJECT:` blocks for vanilla company definitions. |
| `scripts/generators/gen_company_building_cleanup.py` | Generates the on-disband cleanup mapping in `common/scripted_effects/company_building_cleanup_effects.txt`. |
| `scripts/generators/add_tech_modifiers.py` | Bulk-adds tech modifier blocks. |
| `scripts/generators/assimilation_cultures.py` | Generator related to cultural assimilation tunings. |
| `scripts/image_pipeline/` | AI-image / DDS / video pipeline for event art and PM / law / aptitude icons. `gen_image.py` (FLUX.1-schnell), `convert_event_image.py`, `create_event_video.py`, `gen_pm_icons.py`, `gen_law_icons.py`, `gen_aptitude_icons.py`, `gen_batch_pm_icons.py`, `event_image_prompts.py` (prompts), `generate_event_images.py` (3-phase orchestrator). Optional GPU/CUDA dependencies, normally commented out. |

### Documentation (`docs/`)

`docs/README.md` is the index — start there. The rest of the folder contains design docs, generated reference files, and per-system notes. Selected highlights:

**Reference (auto-generated, do not hand-edit):**
- `laws.txt`, `technologies.txt`, `buildings.txt`, `goods.txt`, `combat_units.txt` — flat reference of every entity, regenerated on server reload.
- `vic3_triggers_effects_reference.md`, `vic3_modifier_type_definitions_reference.md`, `triggers_summary.txt`, `effects_summary.txt`, `modifiers_summary.txt`, `country_triggers.txt`, `triggers_parsed.txt`, `event_targets_summary.txt`, `on_actions_summary.txt`, `custom_localization_summary.txt`, `modifier_patterns.md` — engine docs rendered for grep.
- `engine_coverage_report.md` — output of `/validate/engine-coverage`.
- `error_log_digest.md` — game-log digest (gitignored, machine-local).
- `event_magnitude_report.md` — fast-scaling-resource audit.
- `event_image_inventory.md` — events ↔ image/video map.

**Design docs (hand-written):**
- `mod_systems.md` — every gameplay system's files and mechanics. The single most useful design reference.
- `journal_entry_systems.md` — detailed reference for the 20+ JE-driven systems.
- `python_tools.md` — full mod-state-server endpoint list and AI-agent workflow.
- `scripting_best_practices.md` — engine quirks, scope-chain rules, modifier validation, scripted-trigger/effect catalog. Read first when scripting modifiers or effects.
- `event_creation_guide.md` — event boilerplate, image/video inventory, IG approval modifiers, AI-weight pitfalls, option-balance verification.
- `gui_modding_guide.md` — comprehensive GUI modding (widgets, layout, data binding, scripted GUIs, format specifiers, GetVariableSystem, workshop patterns).
- `vanilla_economy_reference.md` — concept primer on vanilla Vic3 economy. Read before touching mod content that hooks the vanilla economy.
- `treaty_articles_reference.md`, `wonder_buildings_reference.md`, `vanilla_company_buildings_reference.md`, `strategic_reserve_system.md`, `dynamic_country_naming_feasibility.md`, `political_lobbies_design.md`, `future_journal_entry_ideas.md` — per-system design references.
- `auto_generated_files.md` — file-ownership map (also at `/auto-generated`).
- `vanilla_patch_runbook.md`, `vanilla_known_bugs.md` — playbook for absorbing vanilla updates and known vanilla bugs.
- `quick_reference_ids.md` — vanilla law / IG / pop / strata IDs and modifier-duration cheatsheet.
- `script_parameterization_audit.md` — refactor patterns and helper inventory.
- `decolonization_review.md`, `combat_unit_balance_review.md`, `pm_building_balance_review.md`, `tech_tree_balance_review.md` — system-level balance reviews.
- `open_issues.md`, `todos.md` — running task lists.
- `wsl_migration_plan.md`, `wsl_cutover_checklist.md` — repo-side migration history (legacy reference).

---

## Developer workflow

This is a brief operations summary; canonical instructions live in `CLAUDE.md` and `docs/python_tools.md`.

### Mod state server (the primary lookup)

Start manually:
```bash
.venv/bin/python mod_state_server.py
```
Loads in ~60–110 s, then listens on `http://127.0.0.1:8950`. The server **auto-starts** when VS Code opens the workspace (`.vscode/tasks.json`).

Common operations:
- `curl http://localhost:8950/status` — verify alive.
- `curl -X POST http://localhost:8950/reload` — re-parse files from disk after editing (runs the post-load generators).
- `curl -X POST 'http://localhost:8950/reload?engine_only=true'` — refresh only the engine-doc snapshot after regenerating logs in-game (skips the slow ModState rebuild and the post-load generators).
- `python mod_state_client.py <command> [args]` — CLI client.
- See `docs/python_tools.md` for the full endpoint list (entity data, vocabularies, modifier patterns, engine docs, validation, event balance, game logs, search).

### Auto-deploy

`scripts/deploy.sh --apply` rsyncs only engine-required files into the Paradox mod folder (Python, docs, tests, `.git`, logs stay in the repo). The watcher (`scripts/watch_deploy_on_edit.sh`) runs continuously while VS Code is open and re-syncs on save. Manual edits made outside the editor still need a manual `./scripts/deploy.sh --apply`.

The deploy target defaults to `/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended`; override via `VIC3_MOD_DEPLOY_TARGET=...`.

### Editing conventions

- Brace-based Paradox files use **tab** indentation. After large edits, run `python scripts/format_paradox_tabs.py <files>` (or `--check`).
- Don't hand-edit auto-generated files (see § Mod data ownership map). Edit the generator's input and re-run.
- Localization: prefer adding to existing `*_l_english.yml` files; `organize_loc.py` will sort and re-categorize on the next server reload. Add a new prefix to its `categorize_key` when introducing a new content family.
- After editing mod files, `POST /reload` (the watcher rsync runs independently). After editing Python tooling, restart the server.
- The Clausewitz engine **silently ignores invalid modifier names**. Validate via `/modifier-search?q=` or `/engine-docs/modifiers?q=` before introducing one. Boolean modifier types must be explicitly declared in `common/modifier_type_definitions/` — there is no auto-registration. See `docs/scripting_best_practices.md` for the full set of validation rules.

### Dependencies

```bash
.venv/bin/pip install -r requirements.txt
```
Core deps (`requests`, `pyyaml`, `regex`, `numpy`) are required for the server plus its post-load generators. Always run server-touching commands through `.venv/bin/python` so the post-load generators can resolve their deps.

---

## Credits

The construction-market subsystem (files prefixed `te_construction_market_*` in `common/` and `events/`, plus the integration in `gui/construction_panel.gui`) is based on the third-party **Free Market Construction** mod. Credit and thanks to that mod's author.

Vanilla event picture / icon assets are © Paradox Interactive, used under their modding terms. AI-generated event art produced by the `scripts/image_pipeline/` toolchain.
