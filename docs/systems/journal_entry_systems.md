# Journal Entry Systems

Reference for all custom journal entry systems added by the Vic3TimelineExtended mod.

---

## Banking Cycle (`je_banking_cycle`)

**File:** `common/journal_entries/je_banking.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Simulates a realistic financial cycle with boom/bust mechanics, including speculative bubbles, crashes, and economic contagion between trading partners. Requires `stock_exchange` tech + urban centers level 10+.

### Key Mechanics
- **3 progress bars:** `banking_cycle_value_bar` (phase 0-100), `banking_cycle_momentum_bar` (velocity -5 to +5), `banking_bubble_pressure_bar` (speculation 0-100)
- **7-tier economy phases:** panic → downturn → stagnation → stable → expansion → boom → frenzy
- **Momentum system:** Monthly momentum decays (90% retention), modifiers add/subtract momentum, random nudge with bias
- **Crash detection:** Asymmetric — higher probability in frenzy/boom when bubble pressure is high
- **Contagion:** Crash spreads via trade agreements, customs unions, adjacency, economic dependence, market share. Event `minor_events_timelineextended.7` fires to connected countries.
- **Fiscal policy:** `financial_cycle_government_fiscal_policy_effect` recalculated monthly based on budget

### Variables
| Variable | Range | Description |
|----------|-------|-------------|
| `finance_cycle_value` | 0-100 | Current phase position |
| `finance_cycle_momentum` | float | Velocity of change |
| `bubble_pressure` | 0-100 | Speculative pressure |
| `crash` | 0/1 | Temporary crash flag |
| `crash_severity` | int | Crash intensity |
| `banking_points_max_from_law` | int | Law-dependent cap |

### Buttons (28 market + 16 CE + 16 CW)
Central bank policy tools, organized as toggle pairs (market economy only):
- Policy rate (hike/disable), open market ops, countercyclical buffer, deposit guarantee
- Directed credit, emergency liquidity, moral suasion
- Margin requirements, FX devaluation, FX support
- Capital controls (outflow), FX swap lines, export credit facility, asset relief program

**Command Economy planning tools** (16 buttons, visible under `law_command_economy` only):
- Emergency Plan Revision, Resource Allocation, Target Reduction, Strategic Stockpile
- Distribution Upgrade, Admin Campaign, Coordination Protocol, Consolidation Order
- Each has an enable/disable toggle pair. Modifiers use prefix `planning_*`.

**Cooperative Ownership council tools** (16 buttons, visible under `law_cooperative_ownership` only):
- Dividend Restraint, Mutual Aid Fund, Capital Plan, Solidarity Campaign
- Credit Expansion, Consumption Ceiling, Council Directive, Worker Buyout
- Each has an enable/disable toggle pair. Modifiers use prefix `cooperative_*`.

**Budget system:** All tools spend from a shared `country_banking_intervention_max_add` pool. The JE's `progress_desc` shows the economy-appropriate label:
- Market → "Free Intervention Points"
- Command Economy → "Free Planning Budget"
- Cooperative → "Free Council Mandate Points"

### Modifiers
- Phase modifiers: `financial_cycle_phase_{panic|downturn|stagnation|expansion|boom|frenzy}`
- `financial_cycle_government_fiscal_policy_effect` — recalculated monthly
- `banking_capital_controls_out` — removed when conditions normalize
- **Command Economy modifiers** (`planning_*`): 8 mods applied by CE planning-tool buttons
- **Cooperative modifiers** (`cooperative_*`): 8 mods applied by CW council-tool buttons
- **Law-change cleanup:** `on_law_enactment_pass` → `te_banking_law_change_cleanup` (in `extra_on_actions.txt`) removes all economy-type-specific modifiers automatically when the economic law changes. CE → market removes `planning_*`; CW → market removes `cooperative_*`; market → CE/CW removes all 14 `banking_*` CB-tool modifiers.

### Events
- `minor_events_timelineextended.6` — crash announcement (origin country)
- `minor_events_timelineextended.7` — contagion to connected countries
- `banking_cycle_events.txt` — 45 events (1–45) covering financial scenarios
  - Events 1, 4, 6, 10, 15, 16, 17, 20 have dedicated `_command` / `_coop` variants
  - Events 2, 5, 7–9, 11, 18, 21–26, 28, 30–33, 35–37, 40–44 are **market-economy gated** (`trigger = { banking_is_market_economy = yes }` in dispatch block in `banking_cycle_effects.txt`)
  - Events 3, 12–14, 19, 27, 29, 34, 38, 39, 45 fire for all economy types

### Never Completes
Persistent journal entry (always active once unlocked).

---

## Civil Rights (`je_civil_rights`)

**File:** `common/journal_entries/je_civil_rights.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Tracks a civil rights movement for minority populations. Activates when a country has Civil Rights tech and incorporated states with low-acceptance pops. Redesigned away from a passive 20-year timer into a bar-and-buttons system structurally modeled on `je_colonial_empire`.

### Key Mechanics
- **Progress bar:** `civil_rights_support_bar` (0-100), starts at 30. Drift sources include base decay, tech tier (`social_justice_movements`), current minority law, low-acceptance state count (via `cr_low_acceptance_count` SV), radical fraction tier, and active button modifiers.
- **5 phase modifiers** keyed to bar tiers: `civil_rights_phase_marginal/growing/active/pressuring/imminent_modifier`. Imminent (90+) adds `country_law_enactment_success_add = 0.10` so the legal finish line gets a push from the very pressure the bar represents.
- **6 button toggle pairs** (12 buttons total) representing player stance. Pro buttons (`grassroots`, `federal_protection`, `gradualist`) and anti buttons (`suppression`, `segregationist`) are mutually exclusive. Cooptation is cross-compatible with anti buttons (the historical "coopt moderates, jail radicals" stance). Each button increments a months-tracker variable consumed by path-dependent resolution.
- **Cooptation expiry:** after 12 months, `cr_cooptation_expired` marker is added by the JE on_monthly_pulse and the bar bonus stops; remove + re-toggle to reset.
- **No timeout** — bar carries the urgency. Drifts to 0 → `on_fail`; reaches 100 → `on_complete`.

### Threshold tier events (one-shot via `cr_tier_X_seen` flags)
- **Tier 25:** existing `.13` (Refugee networks) under severe discriminatory law, else new `.301` (First Mass Rally)
- **Tier 50:** existing `.15` (Martyrdom) under any discriminatory law, else new `.303` (Trade Union Coalition)
- **Tier 75:** new `.304` (Federal Commission Recommends Action) when `cr_federal_months > 24`, else existing `.16` (Civil Disobedience Campaign)
- **Tier 90:** new `.305` (March on the Capital) — universal cinematic beat

### Path-dependent resolution
- **Complete (`movement_events_te.220-.223`):** dispatches on the months-tracker that led for ≥18 months. Federal Mandate / Grassroots Triumph / Negotiated Settlement / Coopted Reform. Falls through to existing single-option `.200` if no track took clear lead.
- **Fail (`movement_events_te.100/.230/.231`):** existing `.100` (oppressive aftermath) under suppression/segregationist dominance or any discriminatory law. New `.230` (token reform demobilized) under cooptation dominance. New `.231` (gradualist stagnation) otherwise.

### Random pool (slimmed)
- `movement_events_te.1, .2, .3, .4, .14` — kept in JE on_monthly_pulse `random_list` at lower weights (~20% chance per month). Threshold events carry the narrative arc; this pool provides ambient flavor.

### Supporting files
- `common/scripted_progress_bars/extra_progress_bars.txt` — `civil_rights_support_bar`
- `common/scripted_buttons/civil_rights_buttons.txt` — 12 buttons
- `common/script_values/civil_rights_values.txt` — `cr_low_acceptance_count`
- `common/static_modifiers/extra_modifiers.txt` — phase + button + victory modifiers (`civil_rights_phase_*`, `cr_*_modifier`, `civil_rights_triumph_*_modifier`)

### Removed in this redesign
The four sibling "social movement" JEs (`je_lgbtq_rights`, `je_second_wave_feminism`, `je_decline_of_religion`, `je_environmental_crisis`) were deleted. Their events 1-5 still fire monthly via `social_movement_orphans_on_action` in `extra_on_actions.txt` with the same tech/law gates. The `.100` and `.200` capstones plus their JE-shape modifiers (`*_struggle_active`, `*_stagnation`, `*_triumph`, `*_crushed`) are gone.

### When retiring a JE: slice modifiers carefully
Mod JEs of this family bundle two kinds of modifiers in the same `extra_modifiers.txt` section, and they need different fates:
- **JE-shape modifiers** — `*_struggle_active_modifier` (`modifiers_while_active`), `*_stagnation_modifier` (`on_timeout`), `*_triumph_modifier` (`on_complete`), `*_crushed_modifier` (`on_fail` capstone). These are referenced only by the JE file and its `.100`/`.200` capstones. **Delete with the JE.**
- **Event-flavor modifiers** — per-event modifiers like `pride_march_momentum_modifier`, `equal_pay_mandate_modifier`, `pollution_regulations_modifier`. These are referenced from inside the events 1-5 the orphan dispatcher keeps firing. **Keep them.**

`grep -rn '<modifier_name>' common/ events/ --include='*.txt'` before deleting any single modifier block — many sit in interleaved order in the section and the comment header lies about which is JE-only.

---

## Colonial Empire (`je_colonial_empire`)

**File:** `common/journal_entries/je_colonial_empire.txt`
**Group:** `je_group_foreign_affairs`

### Purpose
Models the challenge of maintaining overseas colonies after decolonization tech. Countries balance stability through investment, military presence, or cultural assimilation — or accept planned decolonization.

### Key Mechanics
- **Progress bar:** `colonial_stability_bar` (0-100)
- **5 stability tiers:** collapsing (0-20), crumbling (20-40), strained (40-65), stable (65-90), solidified (90+)
- **GP pressure:** Tracked via `colonial_gp_condemners_count`
- **Phase modifiers:** `colonial_empire_under_pressure_modifier` (<40), `colonial_empire_crumbling_modifier` (<20)

### Buttons (8)
4 toggle pairs:
- `ce_invest_in_development` / `ce_remove_invest_in_development`
- `ce_military_garrison` / `ce_remove_military_garrison`
- `ce_cultural_assimilation` / `ce_remove_cultural_assimilation`
- `ce_release_colonial_territory` / `ce_planned_decolonization`

### Outcomes
- **Complete (100):** Permanent `colonial_empire_solidified_modifier`, grants homeland to primary cultures in colonial states with 4+ acceptance
- **Fail (0):** 3× `form_decolonized_country` from overseas states, `colonial_empire_collapsed_modifier` (decaying)

---

## Global Warming (`je_global_warming`)

**File:** `common/journal_entries/je_global_warming.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Persistent environmental tracker that applies scaled penalties based on global temperature rise. Uses `temperature_anomaly_display` script value against a 4°C threshold.

### Key Mechanics
- **Progress:** `temperature_anomaly_display` / 4.0°C goal
- **6 temperature tiers:** negligible (<0.1°C), slight (0.1-0.5), moderate (0.5-1.0), significant (1.0-2.0), severe (2.0-3.0), catastrophic (3.0+)
- **Dynamic modifier pattern:** `global_warming` modifier × `temperature_anomaly_display` multiplier, reapplied monthly
- **`should_be_involved`:** All countries with `greenhouse_gas_emissions`

### Buttons (16)
8 toggle pairs for climate policies:
- Carbon tax, renewable investment, climate adaptation, emission standards
- Reforestation, public transit, fossil fuel divestment, green building codes

### Events
- `environmentalism_events.txt` — threshold events at 0.5°C, 1.0°C, 2.0°C milestones

### Never Completes
Persistent journal entry. Can be deactivated. Revolution inheritable.

---

## Heir Education (`je_heir_education`)

**File:** `common/journal_entries/je_heir_education.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Allows monarchies to shape their heir's education through active focus choices. The heir gains attribute traits (admin/diplo/military), ideological leanings, and IG affiliation based on selected focuses over ~15 years.

### Key Mechanics
- **Progress bar:** `heir_education_progress_bar` (goal = 20 total points)
- **Monthly pulse:** Each active focus has 5% chance to advance its attribute, increment `heir_ed_total`, apply 30-day cost modifier, and trigger IG reaction
- **Random education events** (2% each, 365-day cooldown): `heir_education_events.1`, `.2`, `.3`
- **Completion:** Heir reaches adulthood + 365-day grace period
- **Safety timeout:** 5475 days (15 years)
- **Invalid:** Not a monarchy

### Variables
| Variable | Description |
|----------|-------------|
| `heir_ed_admin` | Administrative attribute points |
| `heir_ed_diplo` | Diplomatic attribute points |
| `heir_ed_military` | Military attribute points |
| `heir_ed_ideology` | Ideological stance (signed: positive=progressive, negative=conservative) |
| `heir_ed_ig_radical` | Radical IG mentorship investment (Intelligentsia, Rural Folk, Trade Unions) |
| `heir_ed_ig_moderate` | Moderate IG mentorship investment (Industrialists, Petty Bourgeoisie, Armed Forces) |
| `heir_ed_ig_regressive` | Regressive IG mentorship investment (Landowners, Devout) |
| `heir_ed_total` | Total investment points (progress tracker) |
| `heir_ed_focus_*` | Active focus flags |
| `being_educated` | Lock flag on heir character |

### Buttons (16)
8 toggle pairs:
- Administrative / Diplomatic / Military focus
- Progressive / Conservative ideology
- Radical / Moderate / Regressive IG affiliation

### Resolution
- `heir_education_resolve_effect` — maps accumulated points to character traits. IG resolution compares `heir_ed_ig_radical`, `heir_ed_ig_moderate`, and `heir_ed_ig_regressive`; the highest wins, with magnitude (≥4 vs 1-3) affecting probability.
  - **Radical** (Intelligentsia, Rural Folk, rarely Trade Unions)
  - **Moderate** (Industrialists, Petty Bourgeoisie, Armed Forces)
  - **Regressive** (Landowners, Devout)
- `heir_education_cleanup_effect` — removes all variables and modifiers

### Related Files
- Effects: `common/scripted_effects/heir_education_effects.txt`
- Buttons: `common/scripted_buttons/heir_education_buttons.txt`
- Events: `events/heir_education_events.txt`

---

## United Nations (`je_united_nations`)

**File:** `common/journal_entries/je_united_nations.txt`
**Group:** `je_group_foreign_affairs`

### Purpose
Simulates an intergovernmental organization with membership, authority, Security Council mechanics, and specialized agencies. Visible when any country has Intergovernmental Organizations tech OR the UN has been founded.

### Founding Process
The UN must be actively founded by a Great Power with Intergovernmental Organizations tech via the `un_found_button`. Founding costs prestige and bureaucracy (`un_founding_cost_modifier`). The founder becomes the first member, hosts the HQ, and gains a Security Council seat + `un_founding_member_modifier`. Sets `un_founded` global variable. After founding, any recognized non-subject country can join (no tech requirement).

### Key Mechanics
- **Authority bar:** `un_authority_bar` (0-100)
- **Authority drift:** Trends toward 50 (±0.25/month baseline, slowed from ±0.5)
  - Democracy bonus: +0.2/month (GP + humanitarian regulations)
  - Championing order: +0.3/month (+0.2 more if top 3 rank)
  - Undermining order: -0.3/month (-0.2 more if top 3 rank)
  - War penalty: -1/month (at war with another UN member)
- **Authority tiers:** collapsed (0), weak (10-30), moderate (30-60), strong (60-85), dominant (85+)
- **Authority threshold effects:**
  - **≥30:** Membership benefits activated (scaled by authority/50)
  - **≥40:** Major/great powers refusing humanitarian aid face diplomatic penalties (`un_refused_aid_penalty_modifier`)
  - **≥50:** Infamy generation increases for all members (`un_high_authority_infamy_modifier`, scaled by (authority-40)/30)
  - **≥60:** Non-members receive pariah status (`un_nonmember_pariah_modifier`: relations, prestige, influence penalties). NPT blocks `nuclear_program_aid` treaty article (with IAEA).
  - **≥70:** Great powers refusing humanitarian aid face severe domestic penalties (radicals, IG disapproval, extra authority loss)
  - **≥80:** Non-nuclear member powers face NPT disarmament pressure (`un_npt_disarmament_modifier`: `nuclear_disarmament = yes`) (requires IAEA)
- **Security Council & Permanent Members:** 5 permanent seats. Granted to the founder + the next 4 Great Powers that join during a 5-year founding window (`un_founding_window_active` global variable, set on `un_found_button`). After the window closes, no new permanent members are auto-created — the only path to a new seat is via the expulsion-vote mechanism (a 2/3 supermajority can strip a permanent member, opening a slot, but the slot is not auto-refilled). Permanent membership is held until: (a) the country leaves the UN, (b) the country has been below Great Power rank for 10+ continuous years (`un_permanent_subgp_months` country variable counts months sub-GP and resets on regaining GP), or (c) a 2/3 supermajority expulsion vote passes against them.
- **Veto Power (binding resolutions only):** Permanent members can cast a veto on the 5 *binding* topics — sanctions, peacekeeping_request, icc, condemn, reform — via a third option in `un_vote.1`. The veto kills the full binding form and sets `un_vote_veto_cast` global. The GA simple majority can still pass a graduated/weak form (vetoed sanctions → voluntary partial; vetoed peacekeeping → observer mission only; vetoed ICC → symbolic censure; vetoed condemn → non-binding rebuke; vetoed reform → flat block, no graduated fallback). Vetoing costs the country 5 UN authority, applies `un_veto_isolation_modifier` (short-term diplomatic isolation) and `un_veto_authority_drain_modifier` (long-term influence hit), and adds 3 infamy when used to block punitive resolutions (ICC, condemn, peacekeeping_request).
- **Expulsion Vote (`un_propose_expulsion_button`):** Any UN member can call a 2/3 supermajority vote to strip a permanent member that has recently vetoed (`un_veto_isolation_modifier` is the visibility trigger). The vote uses `un_vote_topic_expulsion`; the special pass condition is `un_vote_expulsion_passed >= 0` (i.e., `un_vote_support * 3 >= un_vote_eligible_member_count * 2`). On pass, target loses both `un_permanent_member_modifier` and `un_security_council_modifier`. Non-vetoable.
- **Treaty obligation:** `join_united_nations` treaty article auto-enrolls target via JE monthly pulse when `un_membership_obligation` modifier is active.

### Variables
| Variable | Scope | Description |
|----------|-------|-------------|
| `un_authority` | country | 0-100 legitimacy/strength |
| `un_founded` | global | Flag: UN has been established |
| `un_hq_country` | global | HQ host country |
| `un_vote_active` | global | Flag: vote in progress |
| `un_vote_support` | global | Count of yes votes |
| `un_vote_oppose` | global | Count of no votes |
| `un_vote_net` | global | Net votes (support - oppose), starts at 1 |
| `un_vote_proposer_country` | global | Scope: proposing country |
| `un_vote_target_country` | global | Scope: target country (if applicable) |
| `un_vote_topic_*` | global | Topic flag for current vote |
| `un_agency_*` | global | Specialized agency flags (who, unesco, icj, unhrc, iaea, unep, unhcr, unoosa) |

### Buttons (17+)
- **Founding:** `un_found_button` (GP + tech required)
- **Membership:** `un_join_button`, `un_leave_button`
- **Requests (trigger GA votes):** `un_request_peacekeepers_button`, `un_request_humanitarian_aid_button`, `un_propose_condemn_button`, `un_propose_sanctions_button`
- **Policy (members):** `un_lift_sanctions_button`, `un_peacekeeping_button`, `un_end_peacekeeping_button`, `un_fund_development_button`, `un_defund_development_button`, `un_human_rights_button`, `un_arms_control_button`
- **GP influence:** `un_champion_order_button`, `un_stop_championing_button`, `un_undermine_order_button`, `un_stop_undermining_button`

### Vote Topics (16, of which 5 are *binding* / vetoable)
The 5 binding topics — sanctions, peacekeeping_request, icc, condemn, reform — can be vetoed by [concept_un_permanent_member]s via the third option in `un_vote.1`. Vetoed binding resolutions that still have GA simple-majority pass in graduated/weak form (except reform, which is flat-blocked). All other 10 topics are recommendatory (non-vetoable). The 16th topic, `expulsion`, is recommendatory but uses a 2/3 supermajority threshold instead of simple majority.


| Topic Variable | Triggered By | Description |
|---|---|---|
| `un_vote_topic_condemn` | Event 2 / Propose Condemn button | Condemn military aggressor |
| `un_vote_topic_human_rights` | Event 3 | Universal Declaration of Human Rights |
| `un_vote_topic_reform` | Event 6 | UN institutional reform |
| `un_vote_topic_heritage` | Event 9 | Cultural heritage program (UNESCO) |
| `un_vote_topic_decolonization` | Event 12 | Anti-colonial declaration |
| `un_vote_topic_npt` | Event 14 | Nuclear Non-Proliferation Treaty (IAEA) |
| `un_vote_topic_pandemic` | Event 16 | Global pandemic response (WHO) |
| `un_vote_topic_climate` | Event 17 | Climate accord (UNEP) |
| `un_vote_topic_refugee` | Event 18 | International refugee resolution (UNHCR) |
| `un_vote_topic_space` | Event 19 | Space cooperation (UNOOSA) |
| `un_vote_topic_peacekeeping_request` | Request Peacekeepers button | Deploy peacekeepers to requesting country |
| `un_vote_topic_aid_request` | Request Aid button | Humanitarian aid to requesting country |
| `un_vote_topic_sanctions` | Propose Sanctions button | Economic sanctions against target country |

### Vote System (3-phase)
1. **un_vote.1** (Phase 1): Fires to all UN members. Each country votes yes/no/abstain with topic-adaptive titles, descriptions, and AI logic. Effects applied on vote (e.g., pledging contributions).
2. **un_vote.2** (Phase 2): Fires to the proposer after 90 days. Shows vote counts, applies resolution effects (agency creation, received benefits, authority changes). Cleans up all vote state.
3. **un_vote.3** (Phase 3): Notification fired to all other members showing the vote result (pass/fail with vote counts).

### Cost Architecture
- **Contributor programs** (peacekeeping, development, humanitarian aid) apply TWO modifiers:
  - A gameplay modifier (diplo rep, prestige, bureaucracy cost) — e.g., `un_peacekeeping_contributor_modifier`
  - A GDP-scaled cost modifier with `country_expenses_add = 1` × `un_program_expense_value` (GDP × 0.005) — e.g., `un_peacekeeping_contributor_cost`
- **Received benefits** (peacekeeping/aid) are GDP-weighted via `un_peacekeeping_benefit_scale` and `un_aid_benefit_scale` script values: `sum(contributor_gdp) / recipient_gdp * 0.5`, bounded [0.5, 5.0]. Small recipients get proportionally more from large contributors.
- **Humanitarian aid events** (un_events.7) pass giver GDP via `temp_giver_gdp` variable and apply inline GDP-ratio multiplier to received modifiers (full: [0.5, 3.0]; token: [0.3, 1.0]).

### Modifiers
- Membership: `un_member_modifier`, `un_security_council_modifier`, `un_headquarters_modifier`, `un_founding_member_modifier`
- Founding: `un_founding_cost_modifier`
- Contributor gameplay: `un_peacekeeping_contributor_modifier`, `un_development_contributor_modifier`, `un_humanitarian_aid_modifier`, `un_human_rights_champion_modifier`, `un_arms_control_participant_modifier`
- Contributor costs: `un_peacekeeping_contributor_cost`, `un_development_contributor_cost`, `un_humanitarian_aid_cost`
- Received benefits: `un_peacekeeping_received_modifier`, `un_aid_received_modifier`
- GP influence: `un_champion_order_cost`, `un_undermine_order_cost`
- Vote results: `un_vote_success_reward`, `un_vote_failure_penalty`
- Sanctions: `un_sanctions_enforcer_modifier`, `un_sanctions_target_modifier`
- Authority threshold: `un_high_authority_infamy_modifier` (auth≥50), `un_nonmember_pariah_modifier` (auth≥60), `un_npt_disarmament_modifier` (auth≥80)
- Penalties: `un_refused_aid_penalty_modifier` (prestige, relations speed)
- Cooldown: `un_request_cooldown`
- Scaled membership: `un_membership_benefits_modifier` (scaled by authority)
- Treaty: `un_membership_obligation` (boolean flag from `join_united_nations` treaty article)

### Script Values
- `un_member_count`, `un_total_gdp`, `un_gdp_share`, `un_gp_member_count`, `un_sc_member_count`
- `un_peacekeeping_participants`, `un_development_participants`, `un_arms_control_participants`, `un_human_rights_participants`, `un_heritage_participants`
- `un_program_expense_value` (GDP × 0.005)
- `un_peacekeeping_donor_count`, `un_aid_donor_count`
- `un_peacekeeping_benefit_scale`, `un_aid_benefit_scale` (GDP-weighted, bounded [0.5, 5.0])
- Drift components (per-country): `un_authority_drift_base`, `un_authority_drift_democracy`, `un_authority_drift_champion`, `un_authority_drift_undermine`, `un_authority_drift_wars`, `un_authority_drift_total`

### Treaty Articles
- `join_united_nations`: Directed treaty article (`cost = 200`). Source must be UN member; target must not be. Target receives `un_membership_obligation` modifier, auto-enrolled by JE monthly pulse.

### Events
- **un_events.1-20:** Main UN events (formation charter, condemn, human rights, etc.) — dispatch votes
- **un_events.101-103:** Authority crisis events
- **un_vote.1-3:** GA voting system (vote, results, notification)
- **Monthly dispatch:** `un_on_actions.txt` fires random events (75% nothing, 2-3% each for events 2-20)

### Status Description
Multi-section: membership status, authority tier, authority drift breakdown (per-component ScriptValue display with `[SCOPE.GetRootScope.ScriptValue('name')|2]` decimal formatting), HQ status, General Assembly stats, Security Council status, specialized agencies, active programs/policies.

### Never Completes
Persistent. Revolution inheritable.

---

## Nuclear Program (`je_nuclear_program`)

**File:** `common/journal_entries/timeline_extended_journal_entries.txt`
**Group:** `je_group_foreign_affairs`

### Purpose
Tracks nuclear weapon development and stockpile. Requires Great Power status (or Major Power + ICBMs tech). Progress builds toward producing nuclear weapons.

### Key Mechanics
- **Progress:** `nuclear_weapon_program_progress` / `nuclear_weapon_program_goal_value`
- **Weekly pulse:** Adds `nuclear_weapon_program_monthly_progress / 4` per week
- **Nuke creation:** When progress ≥ goal, increments stockpile, decrements progress, checks for world-first achievement
- **World first detection:** Sets `is_world_first_nuclear_power` + global `world_first_nuclear_weapon`
- **Subsequent nukes:** Cost reduced by `nuclear_weapon_program_additional_nuke_multiplier`
- **Disarmament:** `nuclear_disarmament` modifier blocks progress, resets stockpile

### Variables
| Variable | Description |
|----------|-------------|
| `nuclear_weapon_stockpile` | Number of nukes |
| `nuclear_weapon_program_progress` | Current progress |
| `nuclear_weapons_program_first_nuke_done` | Flag (0/1) |
| `nuclear_weapons_program_funding` | Funding level |
| `is_world_first_nuclear_power` | World-first flag |
| `world_first_nuclear_weapon` | Global — set when first nuke created |

### Buttons (2)
- `increase_funding_nuclear_program`, `decrease_funding_nuclear_program`

### Modifiers
- `nuclear_power` — applied when stockpile > 0
- `nuclear_disarmament` — blocks program growth

### Events
- `nuclear_weapon_events.10` — fired for creating country
- `nuclear_weapon_events.9` — fired (14-day delay) to all other countries

### Never Completes
Persistent journal entry.

---

## State Collapse (`je_state_collapse`)

**File:** `common/journal_entries/timeline_extended_journal_entries.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Models failed state mechanics. When a country's average standard of living drops critically low, infrastructure degrades until total collapse.

### Key Mechanics
- **Trigger:** Average SoL < 5 (shown), SoL < 4 (active). Not decentralized.
- **Progress:** `state_collapse_progress` / 52 (one year of weekly increments)
- **Weekly pulse:** +1 progress per week
- **Collapse at 52:** Resets progress, applies `failed_state_modifier` (decaying, long duration), calls `state_collapse_remove_infrastructure` on all states and `reset_all_institutions_and_ministries`

### Variables
| Variable | Description |
|----------|-------------|
| `state_collapse_progress` | Collapse accumulation (0-52) |

### Related Effects
- `state_collapse_remove_infrastructure` — destroys buildings/infrastructure
- `reset_all_institutions_and_ministries` — resets all institutions to baseline

---

## Create New Religion (`je_create_new_religion`)

**File:** `common/journal_entries/timeline_extended_journal_entries.txt`
**Group:** `je_group_internal_affairs`

### Purpose
Player-only journal entry providing a multi-stage wizard for creating a custom religion with chosen ideologies, traits, name, and religious group.

### Key Mechanics
- **Player-only:** `is_ai = no`
- **Trigger:** No custom religions exist yet + custom religions game rule enabled
- **Multi-stage UI:** Navigated via `custom_religion_back` / `custom_religion_next` buttons
- **Completion:** `country_has_any_custom_religion = yes`

### Variables
| Variable | Description |
|----------|-------------|
| `selected_idelogies` | Ideology selection bitmap |
| `selected_traits` | Trait selection bitmap |
| `selected_name` | Name variant index |
| `selected_religion_group` | Religion group choice |
| `current_stage` | UI stage (1-based) |

### Buttons (76+)
Organized by selection category:
- **Economy ideology:** 6 variants (traditionalist, free market, socialist, social democratic, imperial cult, theocratic)
- **Society ideology:** 6 variants
- **Governance ideology:** 6 variants
- **Outlook ideology:** 6 variants
- **Loyalty traits:** 6 variants
- **Happiness traits:** 6 variants
- **Unhappiness traits:** 6 variants
- **Name:** 20 variants (a through t)
- **Religion group:** 7 variants (christian, muslim, judaism, eastern, animist, buddhist, custom)
- **Navigation:** back, next
- **Submit:** `create_new_religion`

Each category uses select/deselect toggle pairs.

---

## World War (`je_world_war`)

**File:** `common/journal_entries/world_war_je.txt`
**Group:** `je_group_foreign_affairs`

### Purpose
Models a World War lifecycle from rising tensions through active total war to post-war resolution. Great powers track ideological tensions, war phases, and post-war cleanup.

### Key Mechanics
- **Trigger:** Combined Arms tech + Great Power + no `ww_fully_resolved`
- **3 phases:** Leadup → Active War → Post-War
- **Leadup tension tiers:** simmering → rising (30+) → high (50+) → crisis (70+)
- **War duration tracking:** Months counter → years elapsed
- **Strain escalation:** Home front strain at 2+ years, prolonged exhaustion at 4+ years
- **Peace detection:** Checks belligerent status changes, triggers peace conference event, 36-month post-war timer
- **Ideology classification:** democratic, communist, fascist, authoritarian, non-aligned

### Variables
| Variable | Description |
|----------|-------------|
| `ww_active_phase` | War is underway flag |
| `ww_aggressor_side` / `ww_defender_side` | Alignment |
| `ww_years_elapsed` | War duration in years |
| `ww_months_counter` | Month tracker for year increment |
| `ww_peace_concluded` | War ended flag |
| `ww_peace_months` | Post-war timer (36-month goal) |
| `ww_fully_resolved` | JE completion flag |
| `ww_peace_event_fired` | Event control flag |

### Buttons (12+)
- **Leadup phase:** rearm, appease, lend-lease (toggle pairs)
- **War phase:** total war economy, war propaganda, wartime rationing (toggle pairs)
- **Late entry:** `ww_join_war_button`

### Modifiers
- **Leadup:** `ww_rising_tensions_modifier` (≥30 tension, non-belligerent), `ww_rearmament_modifier`, `ww_appeasement_modifier`, `ww_lend_lease_modifier`
- **War:** `ww_total_war_economy_modifier`, `ww_war_propaganda_modifier`, `ww_wartime_rationing_modifier`
- **Strain:** `ww_home_front_strain_modifier` (2+ years), `ww_prolonged_war_exhaustion_modifier` (4+ years)
- **Positive:** `ww_fresh_forces_modifier`, `ww_arsenal_of_democracy_modifier`

### Events
- **Leadup:** `world_war_events.1` (confrontation), `.2` (border incident), `.3` (crisis)
- **Outbreak:** `world_war_events.5` (war breaks out)
- **Active war:** `.10` (rally), `.11` (bombing), `.12` (resistance), `.20` (join opportunity)
- **Prolonged:** `.30` (weariness)
- **Post-war:** `.100` (peace conference), `.103` (war crimes), `.104` (new order), `.105` (new rivalry)

### Related Triggers/Values
- `country_is_ww_belligerent`, `country_has_opposed_ideology`
- `country_is_democratic`, `country_is_communist`, `country_is_fascist`, `country_is_authoritarian`
- `ww_ideological_tension`

### Completion
Completes when `ww_fully_resolved` is set (36 months post-war). Fails if dropped below great power rank.

---

## Space Race (`je_space_race_*`)

**File:** `common/journal_entries/je_space_race.txt`
**Group:** `je_group_foreign_affairs`

### Purpose
Multi-stage competitive space race system with 8 milestones. Great/Major Powers with rocketry tech compete to achieve milestones first. Semi-parallel progression allows pursuing multiple objectives once prerequisites are met.

### Key Mechanics
- **8 Milestones:** Suborbital Flight → Orbital Flight → Moon Landing / Probe (parallel) → Moon Base / Mars Landing (parallel) → Mars Terraforming → Solar System Colonization
- **"The First" Bonus:** Global flags track first achiever per milestone. First nation gets ~2× permanent rewards.
- **Approach Choice:** Safe (slow, ~2-7% failure) vs Ambitious (fast, ~10-22% failure) via scripted buttons.
- **Funding Levels:** 0-3 levels affecting progress speed and innovation drain.
- **Failure:** Halves progress + cooldown period. Does NOT permanently block.
- **Moon Landing Site:** Shackleton Crater (high risk, science) vs Equatorial Plain (low risk, modest).
- **Progress Sources:** Base rate + Aerospace Industry levels + Space Elevator + Space Mine + UN partnership + SpaceX company + funding + tech bonuses.
- **Cross-System:** UN space partnership, SpaceX company, space elevator, space mine, and tourism all provide progress bonuses and/or reduce failure risk.
- **Colony Modifiers (JE-Scoped):** All 68 colony modifiers and `sr_solar_system_trade` are applied to `je:je_space_race_solar_colonization` (not country scope). The colonization JE stays alive indefinitely in passive mode once all 34 colonies are claimed, keeping colony modifiers active. Buttons are hidden when colonization is complete.

### Milestones & Prerequisites
| Milestone | Tech Required | Other Prerequisites |
|-----------|--------------|-------------------|
| Suborbital Flight | rocketry | GP/MP rank |
| Orbital Flight | — | Suborbital complete |
| Moon Landing | space_exploration | Orbital complete |
| Outer Solar System Probe | space_exploration | Orbital complete |
| Moon Base | reusable_rocketry | Moon Landing complete |
| Mars Landing | reusable_rocketry | Orbital complete |
| Mars Terraforming | space_colonization | Mars Landing complete |
| Solar System Colonization | space_colonization | Moon Base + Mars Landing complete |

### Buttons (4 per JE)
- `sr_select_safe_approach` / `sr_select_ambitious_approach` — approach toggle
- `sr_increase_funding` / `sr_decrease_funding` — funding level (0-3)

### Events (34 total)
- `.1`-`.9` — Milestone completion events (1 per milestone + notification)
- `.5` — Moon landing site choice (Shackleton vs Equatorial)
- `.10` — Ambitious approach failure (3 options: investigate/switch to safe/double down)
- `.11` — Safe approach minor setback (2 options)
- `.20` — Rival achievement notification
- `.30`-`.37` — In-progress flavor events (test flights, debris, astronauts, water on Mars, ethical debates, Helium-3, outer planet images, colony ships)
- `.40`-`.49`, `.54` — Hard sci-fi events (radiation shielding, gravity well economics, communication delay, life support, solar flare, gravitational slingshot, ISRU, micrometeorite, crew psychology, orbital fuel depot, heat shield re-entry)
- `.50`-`.53`, `.55` — Cross-system events (SpaceX private company, space tourism, ISS/UN cooperation, extraplanetary base integration, space elevator synergy)

### Related Files
- Effects: `common/scripted_effects/space_race_effects.txt`
- Triggers: `common/scripted_triggers/space_race_triggers.txt`
- Buttons: `common/scripted_buttons/space_race_buttons.txt`
- Values: `common/script_values/space_race_values.txt`
- Modifiers: `common/static_modifiers/space_race_modifiers.txt`
- On Actions: `common/on_actions/space_race_on_actions.txt`
- Localization: Organized into main loc files by `organize_loc.py` (events, JE labels, modifiers, etc.)
