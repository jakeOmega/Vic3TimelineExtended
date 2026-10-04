# Policing: private enforcement, corporate powers and public accountability — design

## Context

Issue #628 scoped the Policing law group (`lawgroup_policing`): who provides ordinary enforcement, who finances it, and
to whom it answers. It listed one law candidate the owner favours (Private Policing, for its fit with the Corpocrat
ideology), one weaker law candidate (Community Accountability), three amendment candidates and a review of the existing
laws and the group's name. This spec records what shipped and the decision on every other candidate.

Vanilla's four laws all keep `institution_police`, which the mod displays as **Ministry of Public Safety**
(`localization/english/replace/`):

| Law | Progressiveness | Effects (per institution level unless flat) |
|---|---|---|
| No Police | 0 | No institution |
| Local Police Force | −50 | Landowners +5% clout, turmoil effects −5% (`tech_bureaucracy`) |
| Dedicated Police Force | 25 | +2 max investment (flat), radicals from movements −5% (`law_enforcement`) |
| Militarized Police Force | −100 | +2 max investment (flat), radicals −5%, radicalism-to-discrimination −5% ×3, Armed Forces +10% clout, mortality per turmoil +0.4% (`mass_surveillance`) |

The institution itself gives turmoil effects −10% a level (vanilla) and the mod adds +5% colonial garrison effectiveness
and +0.1 Legislative Override Capacity a level. The mod's Legislative Override Capacity for the laws is −0.5 / 0 / +0.5
/ +1.

## Decisions (owner, 2026-10-04)

| Question | Decision |
|---|---|
| Scope | **Private Policing**, plus the highest-value additions: **Corporate Security Powers** and **Civilian Oversight** (amendments) and **description rewrites** for the group and its four vanilla laws. Every other candidate is decided below (§5) |
| Who favours Private Policing | **Only Corpocrats.** Corporate Rule (custom religion) approves too; market ideologies stay neutral |
| Institution | **Kept**, with a smaller bureaucracy cost: **−40%**, the value vanilla gives Private Schools and Private Health Insurance (Religious Schools and Charitable Health System: −20%) |
| Owners' funding | **Services diverted**: −1% Services output per institution level. A cut to capitalists' and aristocrats' investment-pool efficiency was rejected: it hits hardest the corporate economies most likely to enact the law |
| Mechanics depth | **Aggregate only.** Coverage follows money *within* states (wealthy communities are policed, and every state has some), not as a per-state modifier. No events |
| Unlock | **Computer Networks** (era 8): alarm networks and monitored CCTV; private guards came to outnumber public police in the US and Britain in the 1970s and 1980s |
| Per-level package | Upper strata +0.25 and middle strata +0.1 standard of living, +5% turmoil effects, as proposed |
| Corporate Security Powers' unlock | **Corporate Charters** (era 2): the Pinkerton Agency (1850), Pennsylvania's Coal and Iron Police (1865–1931) |

## 1. Private Policing (`law_private_policing`, `common/laws/extra_laws.txt`)

Licensed private firms carry out most ordinary police work, hired and directed by property owners, businesses and
residents' associations; a smaller public force licenses and backs them up.

| Field | Value |
|---|---|
| Group, unlock | `lawgroup_policing`, `computer_networks`; `unlocking_laws` Laissez-Faire, Interventionism (Contracted Administration's list, which excludes Command Economy and Cooperative Ownership); `disallowing_laws` Council Republic |
| Institution | `institution_police`, `country_institution_cost_institution_police_mult = -0.4` |
| `institution_modifier` | `state_upper_strata_standard_of_living_add` +0.25, `state_middle_strata_standard_of_living_add` +0.1, `state_turmoil_effects_mult` +0.05, `goods_output_services_mult` −0.01 |
| `modifier` (flat) | `interest_group_ig_trade_unions_pol_str_mult` −0.1, `state_pop_support_movement_labor_mult` +0.15, `country_legislative_override_capacity_add` −0.5 |
| Progressiveness | 25 (§6) |
| AI | `ai_will_do`: a Corpocrat ruler (Neocameralism's rule); enact weight 10, +750 under the JE weight trigger |
| `can_impose` | Vanilla's power-bloc pattern (`country_can_impose_same_lawgroup_policing_in_power_bloc_bool`) |
| Icon | `private_policing.dds`: a police shield badge with a star cut through it and Contracted Administration's price tag tied to its corner (`draw_badge_tag`, `scripts/image_pipeline/gen_law_icons.py`) |

**How the aggregate model reads.** The institution's investment is the size of the private force. Each level guards
the districts that pay (upper and middle strata standard of living) and costs the owners who pay for it: the guards are
service workers, so each level takes 1% of the country's Services output, and Urban Center owners and Services buyers,
mostly the better-off, pay through prices. Turmoil comes from the unguarded poor, so the institution's turmoil cover is
halved (−10% → −5% a level). With 40% less bureaucracy per level, a country can run a larger force for the same
administrative cost, which buys more wealthy-district coverage but not more turmoil cover per level than half a public
force.

**Labor conflict and accountability.** Guards break strikes: Trade Unions −10% clout, and the strikes turn political
(Labor Movement pop attraction +15%, the magnitude `common/laws/movement_attraction_modifiers.txt` uses). The force
answers to its clients, not the legislature: No Police's −0.5 Legislative Override Capacity; the institution's own +0.1 a
level still applies.

**Not used:** an Industrialist clout bonus per level (the issue warned against moving Local Police's landowner bonus to
the Industrialists; the Corpocrat stance and the union cut already shift power), `state_political_strength_from_wealth_mult`
and `country_company_throughput_bonus_add` (Neocameralism's levers, so stacking the two laws would double them), and a
max-investment bonus (Local Police has none either).

## 2. Corporate Security Powers (`amendment_corporate_security_powers`)

Companies police their own mines, mills and company towns beside a public force, commissioned by the state and paid by
the companies. The narrow form of Private Policing.

| Field | Value |
|---|---|
| `parent` | `law_private_policing`, so interest groups take the same stance: only Corpocrat and Corporate Rule favour it |
| `allowed_laws` | Local, Dedicated, Militarized Police Force. Not Private Policing, which already delegates the whole force |
| `possible` | `corporate_charters`, and not Command Economy, Cooperative Ownership or Industry Banned |
| `modifier` | Police institution cost −10%, Trade Unions −10% clout, Labor Movement pop attraction +15% |
| `sponsor_modifier` | `interest_group_pol_str_mult = 0.1`: whoever commands the guards gains |
| `would_sponsor` | The Industrialists, or any IG approving the parent. Before Mutual Funds no Corpocrat exists, so the Industrialists carry it |
| Revoke, repeal | `ai_will_revoke` when an IG in government disapproves of the parent; `can_repeal` on the legitimacy define; activism multiplier 0.5 (the mod's amendment pattern) |

## 3. Civilian Oversight (`amendment_civilian_police_oversight`)

Civilian review boards hear complaints against police officers and licensed providers and can discipline them (New
York's Civilian Complaint Review Board, 1953 and 1966).

| Field | Value |
|---|---|
| `parent` | `law_guaranteed_liberties` |
| `allowed_laws` | Local Police Force, Dedicated Police Force, Private Policing. Not Militarized: a force built to carry out the government's will does not answer to the public |
| `possible` | `civil_rights_movement` (era 7) |
| `modifier` | Police institution cost +10%, Civil Rights Movement pop attraction −15%, Legislative Override Capacity −0.5 |
| `would_sponsor` | The Intelligentsia, or any IG approving the parent |

Distinct from Guaranteed Liberties (what home affairs may investigate; −2 override), Dedicated Police (a professional
force; radicals from movements) and Restorative Justice (what follows a conviction; loyalists from movements): this is
who the street-level force answers to. The civil-rights lever is the political movement's pop attraction
(`movement_civil_rights`), not the Civil Rights journal entry's support bar.

## 4. Descriptions and the group's name

Vanilla's descriptions were one line each and mixed organization (Local, Dedicated) with doctrine (Militarized: "giving
your police force military equipment"). The overrides in `localization/english/replace/timeline_extended_override_l_english.yml`
describe all five by organization, financing and accountability:

| Key | Says |
|---|---|
| `lawgroup_policing_desc` | Who provides ordinary law enforcement, who pays for it, and to whom it answers |
| `law_no_police_desc` | No structured force; communities, landlords and the army keep order |
| `law_local_police_desc` | Town and county constables paid from local rates, overseen by magistrates and notables: public, but local elites decide what it does. This is the boundary with Private Policing's commercial financing |
| `law_dedicated_police_desc` | A national force of career officers, paid from the national budget and answerable to the government |
| `law_militarized_police_desc` | A national police organized along military lines, answering to the government as an instrument of its will |
| `institution_police_desc` | The public agencies that police the country or, under Private Policing, license and back up the firms that do |

**Name: Policing, kept.** The group still answers one question, who provides the street-level force; "Law Enforcement"
would suggest it also covers punishment and regime protection. Internal Security (regime protection) and Criminal
Justice (punishment, rehabilitation, reintegration) stay separate. The player guide's Criminal Justice row now says
"sentencing" where it said "policing".

## 5. Candidates not added

| Candidate (issue score) | Decision and reason |
|---|---|
| Community Accountability as a law (4/10) | **Not a law.** It modifies a police force rather than replacing one, so it cannot be the group's one active answer. It ships as the Civilian Oversight amendment |
| Universal Coverage Obligations (amendment on Private Policing) | **Not added.** It attaches only to an already rare, Corpocrat-only law, and it would cancel that law's defining tradeoff (coverage follows money). Its floor would also want an `institution_modifier` on an amendment, which no vanilla amendment uses (untested in the engine) |
| Rename to Law Enforcement | **Kept as Policing** (§4) |
| Mechanical rework of No, Local, Dedicated, Militarized | **None.** Their effects are distinct (no institution / landowner clout and turmoil / professional radicals cut / Armed Forces and violence). Only the descriptions change (§4) |
| Regional variation (a per-state coverage modifier) | **Not built** (owner call): every state has wealthy and poor communities, so coverage that follows money is modelled within states, through strata |
| Strike-breaking event, company withdrawal (`on_company_disbanded`) | **Not built**: aggregate only. Labor conflict is the union clout cut and the Labor Movement attraction |
| Company-concentration gating (antitrust laws, company count) | **Not used.** Corporate Security Powers needs Corporate Charters and an economy with private owners; the antitrust laws already price company power |

## 6. Transitions and the consistency walk

- **Losing the market economy, or a Council Republic.** Progressiveness 25 equals Dedicated Police Force, so the
  generated `te_fix_inconsistent_lawgroup_policing` moves the country to Dedicated (nationalization), or to No Police
  (0, the terminal fallback) without Law Enforcement. Local Police (−50) is never nearer. All three public police laws
  share `institution_police`, so the investment carries over.
- **Repealing Corporate Security Powers** is the standard amendment repeal (an IG in government must oppose Private
  Policing, which most do). No nationalization event: aggregate only.
- **Criminal Justice.** Restorative and Rehabilitation-Focused Criminal Justice raise police institution cost (+25%,
  +50%) and cut max investment; under Private Policing the costs add (−40% + 50% = +10%).

## 7. Ideology stances

| Stance on Private Policing | Ideologies |
|---|---|
| Strongly approve | Corpocrat (`ideology_corporate`) |
| Approve | Corporate Rule (`ideology_custom_religion_corporate_governance`) |
| Neutral (explicit) | `ideology_custom_religion_meritocratic_society` |
| Disapprove | `ideology_socialist` (+ movement), `ideology_social_democrat`, `ideology_proletarian` (+ movement), `ideology_vanguardist` (+ movement), `ideology_radical` (+ movement), `ideology_humanitarian`, `ideology_egalitarian_modern`; `ideology_paternalistic`, `ideology_republican_paternalistic`, `ideology_scholar_paternalistic`, `ideology_junker_paternalistic`, `ideology_papal_paternalistic`; `ideology_patriotic`, `ideology_jingoist`, `ideology_jingoist_leader`, `ideology_fascist` (+ movement), `ideology_integralist`, `ideology_authoritarian`; the traditionalist, inclusive, imperial-cult and theocratic custom-religion society ideologies |
| Strongly disapprove | `ideology_anarchist` (+ movement), `ideology_communist` (+ movement), the totalitarian custom-religion society ideology |

The left opposes a force hired by property owners, paternalists the notables' constabularies it displaces, and
nationalists and militarists any force outside the state's monopoly. Market ideologies (`ideology_laissez_faire`,
`ideology_plutocratic`, `ideology_market_liberal`) stay neutral, so only Corpocrat leaders push the law.

**Gap:** vanilla ideologies `apply_ideologies` doesn't REPLACE stay neutral, among them the landowners' country variants
`ideology_magnatial`, `ideology_japan_paternalistic`, `ideology_carlist_ig` and `ideology_moderantist`. Vanilla gives
them a Policing block, so a stance would flip them from INJECT to REPLACE, which needs the game files (§8). Add their
disapproval on a machine with the game.

## 8. Generated files without the game

Built in a container without Victoria 3, as the bureaucracy PR was
(`docs/superpowers/specs/2026-10-01-bureaucracy-laws-design.md` §5):

- **`gen_law_consistency`** ran against a synthetic `<root>/game/common/{laws,ideologies}` serialized from
  `vanilla_parsed/`. On unchanged `main` it reproduced `extra_law_consistency_generated.txt` byte for byte; the change
  adds `te_fix_inconsistent_lawgroup_policing` and its dispatcher line.
- **`apply_ideologies`** copies raw vanilla text, so its edit was replayed with the generator's own `modify_entries`
  over the committed bodies, after checking the parse of `modified.txt` round-trips exactly. That equals a real run only
  for an ideology's **last** sub-entry, so each `lawgroup_policing` entry is last in its dict. Two cases: a line
  inserted at the top of vanilla's own Policing block (10 ideologies, whose "Forced REPLACE" comment gains
  `lawgroup_policing` when it listed fewer than three reasons), and a new block before the first `lawgroup_` (17).
- **The icon** is uncompressed BGRA with mips (`scripts/image_pipeline/icon_dds.py`), the layout vanilla's icon folders
  use, because texconv (BC7) is Windows-only.

The owner's next `/reload` on a machine with the game should leave `modified.txt` and the consistency file unchanged.

## 9. In-game checks

- Private Policing shows in the Policing group from Computer Networks, greyed out under Command Economy, Cooperative
  Ownership, Traditionalism or Agrarianism, and in a Council Republic. The icon renders.
- Under it the Ministry of Public Safety's cost is 40% lower, and the per-level lines (upper and middle strata standard
  of living, State Penalties from Turmoil, Building Services output) scale with investment.
- A Corpocrat-led Industrialists group approves the law and the amendment; a socialist-led Trade Unions group opposes
  both.
- Corporate Security Powers is offered while enacting Local, Dedicated or Militarized Police Force after Corporate
  Charters, and the Industrialists sponsor it. Civilian Oversight is offered on Local, Dedicated and Private Policing
  after Civil Rights Movement.
- A country under Private Policing that switches to Command Economy lands on Dedicated Police Force the next month,
  keeping its institution investment.
