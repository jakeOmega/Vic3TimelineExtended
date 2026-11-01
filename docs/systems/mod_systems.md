# Key Mod Systems

<!-- mod_systems index -->

Reference for the gameplay systems the mod adds, one file per system in [`mod_systems/`](mod_systems/). Each covers its system's purpose, file locations and key mechanics. Before redesigning, rebalancing or extending a system, read its file.

- **Finding a section an older reference names.** Until 2026-10-31 this was one 1.2 MB file, and references from then name its sections ("`mod_systems.md` § Inheritance"). The tables list every file's `##` sections. A `###` subsection is a grep away: `grep -rn '^#.*Fast mode' docs/systems/mod_systems/`.
- **Adding a system or a `##` section.** A new system gets a file here and a row below; a new `##` section in a file gets named in that file's row. `test_mod_systems_index.py` fails on a file the index doesn't link or a `##` section it doesn't name.
- **A branch that edited the old single file.** After `git merge origin/main`, run `python3 scripts/mod_systems_split.py port`: it moves the branch's edits into the system files and puts this index back (details in the script's docstring).

## Conventions and cross-system references

| System | Covers | `##` sections |
|---|---|---|
| [Dynamic Modifier Pattern](mod_systems/dynamic_modifier_pattern.md) | Scaling a static modifier with `add_modifier`'s `multiplier`, and which pulse may refresh it | Dynamic Modifier Pattern (`add_modifier` with `multiplier`) |
| [On-Actions Reference](mod_systems/on_actions.md) | Which on-action file wires what; pulse and immediate hooks; the scope-chain limitation | On-Actions Reference |
| [Game Rules](mod_systems/game_rules.md) | Every game rule, its flag and default, and how a disabled system is gated | Game Rules |
| [AI Weights and Company AI](mod_systems/ai.md) | AI weight conventions for entries, buttons, actions and articles; how the AI picks companies | AI Weights Guidelines<br>Company AI |
| [History Store and Charts](mod_systems/history_charts.md) | The save-persistent store of monthly samples and the reusable column chart | History Store and Charts |
| [State Panel and Nation Tab](mod_systems/state_and_nation_panels.md) | The state panel's mod tiles and the Timeline Extended window's Nation tab | State Panel GUI Enhancements<br>Nation Tab |
| [Legacy Narrative Events](mod_systems/legacy_narrative_events.md) | Older narrative events that now defer to, or feed, the banking, covert and space systems | Legacy narrative event integration |

## Economy, construction and infrastructure

| System | Covers | `##` sections |
|---|---|---|
| [Production Methods](mod_systems/production_methods.md) | PM group icons, drugs and pharmaceuticals, barracks training, deep-sea and extraplanetary logistics, Aneutronic Fusion's methods | Production Methods (PMs) |
| [Construction](mod_systems/construction.md) | Construction cost scaling, excess private construction, and construction as a market good | Construction Cost Scaling<br>Excess Private Construction<br>Construction as a Market Good (FMC architecture) |
| [Transport Goods](mod_systems/transport_goods.md) | Transportation inside a state and Merchant Marine between markets | Transport goods: Transportation and Merchant Marine (#1050) |
| [Power Grids](mod_systems/power_grids.md) | Grid Transfer Stations and the monthly balancing of Electricity between states | Power Grids (`building_grid_transfer_station`) |
| [Banking Cycle](mod_systems/banking_cycle.md) | The boom-and-bust cycle, the policy dashboard and its tools, the simplified rule, banking laws | Banking Cycle (`je_banking_cycle`) |
| [Monetary Policy](mod_systems/monetary_policy.md) | The central bank: rates, mandates, the delegated bank, currencies and pegs (phases 1 to 6) | Monetary Policy (part of `je_banking_cycle`) |
| [Global Warming and Resource Transition](mod_systems/global_warming.md) | Emissions, carbon capture, climate policy, geoengineering and the fossil-fuel transition laws | Global Warming (`je_global_warming`)<br>Geoengineering (Stratospheric Aerosol Injection)<br>Resource Transition (`lawgroup_resource_transition`, #660) |
| [Automation Policy](mod_systems/automation_policy.md) | Robots and AI in place of workers: the automated share, Human Labor Quotas' withdrawn methods, the Robot Tax and the Automation Dividend | Automation Policy (`lawgroup_automation_policy`) |
| [Wonder Buildings](mod_systems/wonder_buildings.md) | The megaprojects' construction-site pattern | Wonder Buildings (Construction Site Pattern) |

## Politics and law

| System | Covers | `##` sections |
|---|---|---|
| [Judiciary](mod_systems/judiciary.md) | The judiciary law group, defying the court, its amendments and landmark cases | Judiciary (`lawgroup_judiciary`) |
| [Amendments](mod_systems/amendments.md) | Temporary amendments (sunset clauses), amendment petitions, First Past the Post | Temporary Amendments (Sunset Clauses)<br>Amendment Petitions (`amendment_petition_events`)<br>First Past the Post (`amendment_first_past_the_post`) |
| [Legislated Tax Code](mod_systems/tax_code.md) | The experimental rule that replaces the taxation laws with a legislated code | Legislated Tax Code (`je_tax_code`, `te_tax_code_rule`) |
| [Governance, Bureaucracy and Policing Laws](mod_systems/governance_laws.md) | Collective Governance, the bureaucracy laws, machine administration and rule, liquid democracy, policing, penal labor, Frontier AI Control | Collective Governance (`law_direct_democracy`)<br>Bureaucracy Laws: Who Staffs the Administration (`law_contracted_administration`, `law_communal_administration`, `amendment_spoils_system`)<br>Machine Administration and Machine Rule (`law_automated_bureaucracy`, `law_algorithmic_governance`)<br>Liquid Democracy (`law_liquid_democracy`, `te_continuous_vote`)<br>Policing: Private Policing and Its Amendments (`law_private_policing`, `amendment_corporate_security_powers`, `amendment_civilian_police_oversight`, #628)<br>Penal Labor Camps (`law_penal_labor_camps`)<br>Frontier AI Control (`lawgroup_frontier_ai_control`) |
| [Inheritance](mod_systems/inheritance.md) | The inheritance laws and what they do through script | Inheritance: Who Inherits (`lawgroup_inheritance`) |
| [Heir Education](mod_systems/heir_education.md) | Educating the heir: tiers, traits, intelligence and the rebel child | Heir Education System (`je_heir_education`) |
| [Social Movements and Religious Revival](mod_systems/social_movements.md) | The social-movement journal entries, where the retired ones' content went, the Bodily Autonomy laws and their debate, religious revival events | Social Movement Journal Entries (history)<br>Morphological Freedom Debate and Bodily Autonomy<br>Religious Revival Events |

## Population, culture and society

| System | Covers | `##` sections |
|---|---|---|
| [Demographics](mod_systems/demographics.md) | The census by age and sex, Wealth Concentration, births and deaths, the workforce, the late game | Demographics (`demographics_rule`): the census (phase 1; phase 2 steps 1, 2 and 4; phase 3: event wave, late game and Family Limitation) |
| [Pops, Migration and Resettlement](mod_systems/pops_and_migration.md) | Migration crowding and Public Housing, unemployment as a workforce share, homelands, resettlement, population transfer | Migration Crowding<br>Public Housing<br>Unemployment as a Share of the Workforce<br>Dynamic Homeland Progress<br>Internal Resettlement (Settlement Authority)<br>Population Transfer (Treaty Article) |
| [Standard of Living Expectations](mod_systems/sol_expectations.md) | Adaptive standard-of-living expectations and their loyalist and radical effects | SoL Expectations System |
| [Cultural Hegemony](mod_systems/cultural_hegemony.md) | Global cultural influence and the ideology drift it drives abroad | Cultural Hegemony System |
| [Grand Monuments](mod_systems/grand_monuments.md) | Monuments as political instruments: raising them, their legacy, archaeology, trophies | Grand Monuments (Political Instrument) |

## Diplomacy, war and intelligence

| System | Covers | `##` sections |
|---|---|---|
| [Nuclear Weapons](mod_systems/nuclear.md) | The nuclear program, deterrence and crisis diplomacy, the Nuclear Program Pause article | Nuclear Weapons (`je_nuclear_program`)<br>Nuclear Deterrence and Crisis Diplomacy (part of `je_nuclear_program`)<br>Nuclear Program Pause (Treaty Article) |
| [Covert Warfare](mod_systems/covert_warfare.md) | Covert operations, networks, tradecraft, backlash, counterintelligence; the intelligence-sharing shield | Covert Warfare System<br>Intelligence Sharing Defense Shield |
| [Treaty Articles](mod_systems/treaties.md) | Treaty articles with entity selection, Enforce Emissions Reduction, dynamic treaty names | Treaty Articles with Entity Selection<br>Dynamic Treaty Names |
| [War](mod_systems/war.md) | The Rules of War laws, war support feeds, wartime munitions demand | Rules of War (`lawgroup_rules_of_war`)<br>War Support Feeds (1.14 hook)<br>Wartime Munitions Demand |

## Colonies, space and the global commons

| System | Covers | `##` sections |
|---|---|---|
| [Decolonization](mod_systems/decolonization.md) | The colonial empire entry, the colony test, wars of independence, nationalization, colonial collapse | Decolonization System (`je_colonial_empire`)<br>Independence Nationalization Event (`decolonization_events.15`)<br>Colonial Collapse (`colonial_collapse_effect`) |
| [Space Race](mod_systems/space_race.md) | Milestones, the space program, colonies and their fleets, Space Command, orbital debris | Space Race (`je_space_race_*`) |
| [Global Commons](mod_systems/global_commons.md) | Seabed licences and claims, and the UN's Law of the Sea, Antarctica and anti-satellite terms | Global Commons (`global_commons_rule`): seabed licences<br>Global Commons: the UN layer |
