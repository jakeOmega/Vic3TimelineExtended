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

### Policy Dashboard (journal-entry widget)
Two custom widgets, wired from `je_banking.txt` into the vanilla panel's `custom_widget_container_1` and `_2`, are the player-facing surface; the scripted-button grid stays below them.

- **File:** `gui/journal_entry_widgets/banking_dashboard_widget.gui`
- **Handlers:** `common/scripted_guis/banking_dashboard_scripted_gui.txt`
- **Shared helpers:** `common/scripted_triggers/banking_policy_triggers.txt` (`banking_possible_<button>`), `common/scripted_effects/banking_policy_effects.txt` (`banking_effect_<button>`), plus the `banking_tool_*_active` family in `market_triggers.txt`
- **Display-only reads:** `banking_display_value_monthly_add`, `banking_display_momentum_monthly_add`, `banking_display_momentum_decay`, `banking_display_bubble_monthly_add`, `banking_display_points_free` in `extra_script_values.txt`

Areas:
1. **Current Conditions** — cycle phase (named from `banking_cycle_is_*`), momentum, bubble pressure, free intervention budget. Each tooltip explains the reading and lists its current drivers from the `banking_display_*` script values.
2. **Active Policies** — one row per intervention currently in force, gated on `banking_tool_*_active` only (no economic-system gate), each with a working Disable action.
3. **Available Interventions** — only the current economic system's policies, in collapsible categories. Ineligible policies stay visible but disabled, with the reason in the action tooltip.

Editing rules: change a policy's cost, eligibility or effect in the **helper**, not in the button or the scripted GUI. Never delete a `scripted_button = …` line from `je_banking.txt` — those `ai_chance` blocks are the AI's only path to banking policy.

### History Charts (journal-entry widget)
A third custom widget in `custom_widget_container_3`, collapsed by default.

- **File:** `gui/journal_entry_widgets/banking_history_widget.gui` (chart types: `gui/journal_entry_widgets/te_history_chart.gui`)
- **Series:** cycle value and bubble pressure (0–100 indices) and momentum (signed monthly delta) — three separate charts, because the units differ.
- **Sampling:** `te_history_record_banking_samples` from the JE's own `on_monthly_pulse`, after `banking_cycle_check_and_execute_crash`. Gated on `has_game_rule = banking_system_enabled` + `has_journal_entry = je_banking_cycle` and on `te_history_country_is_tracked` (player, or major power and above).
- **Markers:** policy adopted / withdrawn, recorded inside each `banking_effect_<button>` helper so the AI's buttons and the dashboard both hit it; plus `crash` and `crash_contagion` from the crash subsystem. Hovering a bar shows the date, the reading and — via `te_history_marker_tooltip` — each marker's own policy name, description and static-modifier effect list.
- **Ranges:** 1 / 5 / 10 years, held in the GUI variable system only. Retention is 120 monthly samples.
- **No gameplay effect.** Recording is additive and `hidden_effect`-wrapped; the widget's only clicks write GUI variables. Full data model, caps and the "how to add a series" recipe: `docs/systems/mod_systems.md` → **History Store and Charts**.

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
- **Law-change cleanup:** `on_law_enactment_pass` → `te_banking_law_change_cleanup` (in `extra_on_actions.txt`) removes all economy-type-specific modifiers automatically when the economic law changes. CE → market removes `planning_*`; CW → market removes `cooperative_*`; market → CE/CW removes all 14 `banking_*` CB-tool modifiers. The dashboard's Active Policies area deliberately does **not** apply an economic-system gate, so if that cleanup ever misses a case (a law swapped by something other than `on_law_enactment_pass`) the stale policy still shows up with a working Disable action.

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
The four sibling "social movement" JEs (`je_lgbtq_rights`, `je_second_wave_feminism`, `je_decline_of_religion`, `je_environmental_crisis`) were deleted, and so were their dedicated event files (`events/lgbtq_events.txt`, `feminist_events.txt`, `secular_events.txt`, `environmental_events.txt`). There is **no** `social_movement_orphans_on_action` — that dispatcher never shipped. The surviving content was folded into shared event files instead: LGBTQ+ → `society_technology_events.7`–`.8` and feminism → `society_technology_events.1`–`.2`, both dispatched from `society_technology_events_on_action` in `extra_on_actions.txt`; decline of religion → `social_tensions_events.13` (plus `events/religious_revival_events.txt`), dispatched from `common/on_actions/social_tensions_on_actions.txt`; environmental crisis → `events/environmentalism_events.txt`, fired on temperature thresholds under `je_global_warming`. The `.100` and `.200` capstones plus their JE-shape modifiers (`*_struggle_active`, `*_stagnation`, `*_triumph`, `*_crushed`) are gone. Full table: `docs/systems/mod_systems.md` § Social Movement Journal Entries.

### When retiring a JE: slice modifiers carefully
Mod JEs of this family bundle two kinds of modifiers in the same `extra_modifiers.txt` section, and they need different fates:
- **JE-shape modifiers** — `*_struggle_active_modifier` (`modifiers_while_active`), `*_stagnation_modifier` (`on_timeout`), `*_triumph_modifier` (`on_complete`), `*_crushed_modifier` (`on_fail` capstone). These are referenced only by the JE file and its `.100`/`.200` capstones. **Delete with the JE.**
- **Event-flavor modifiers** — per-event modifiers like `pride_march_momentum_modifier`, `equal_pay_mandate_modifier`, `pollution_regulations_modifier`. These are still referenced from inside the surviving events in their new homes (see above). **Keep them.**

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
- **Veto Power (binding resolutions only):** Permanent members can cast a veto on the 5 *binding* topics — sanctions, peacekeeping_request, icc, condemn, reform — via a third option in `un_vote.1`. The veto kills the full binding form and tags the resolution `un_res_vetoed`. The GA simple majority can still pass a graduated/weak form (vetoed sanctions → voluntary partial; vetoed peacekeeping → observer mission only; vetoed ICC → symbolic censure; vetoed condemn → non-binding rebuke; vetoed reform → flat block, no graduated fallback). Vetoing costs the country 5 UN authority, applies `un_veto_isolation_modifier` (short-term diplomatic isolation) and `un_veto_authority_drain_modifier` (long-term influence hit), and adds 3 infamy when used to block punitive resolutions (ICC, condemn, peacekeeping_request).
- **Expulsion Vote (`un_propose_expulsion_button`):** Any UN member can call a 2/3 supermajority vote to strip a permanent member that has recently vetoed (`un_veto_isolation_modifier` is the visibility trigger). The resolution is tagged `un_topic_expulsion`; the special pass condition is `un_vote_expulsion_passed >= 0` (i.e., `un_res_support * 3 >= un_vote_eligible_member_count * 2`). On pass, target loses both `un_permanent_member_modifier` and `un_security_council_modifier`. Non-vetoable.
- **Treaty obligation:** `join_united_nations` treaty article auto-enrolls target via JE monthly pulse when `un_membership_obligation` modifier is active.

### Variables
| Variable | Scope | Description |
|----------|-------|-------------|
| `un_authority` | global | 0-100 legitimacy/strength |
| `un_founded` | global | Flag: UN has been established |
| `un_hq_country` | global | HQ host country |
| `un_vote_active` | global | Vote lock: a resolution (or a proposer event's reservation) holds the General Assembly |
| `un_vote_reservation` | global | Flag: a proposer event holds the lock before choosing whether to propose |
| `un_active_resolution` | global | Scope: the open resolution container |
| `un_resolution_history` | global list | Closed resolution containers, capped at `un_resolution_history_cap` (25) |
| `un_resolution_seq` | global | Counter behind each resolution's `un_res_seq` |
| `un_mandate_seq` | global | Counter behind each mandate's `un_mnd_seq` |
| `un_mandate_registry` | global list | Every authorized military mandate, live and closed, capped at `un_mandate_registry_cap` (12) |
| `un_mandate_current` | country | The actor's live mandate container — the "one at a time" rule and an O(1) index in one |
| `un_standing` | country | 0-100 national record of delivered commitments and compliance — see § UN Standing |
| `un_standing_last_reason` | country | numeric code of the most recent standing change, for the chamber panel |
| `un_standing_suspended` | country | timed; while it exists the positive standing tiers grant nothing |
| `un_agency_*` | global | Specialized agency flags (who, unesco, icj, unhrc, iaea, unep, unhcr, unoosa) |

### Buttons (17+)
- **Founding:** `un_found_button` (GP + tech required)
- **Membership:** `un_join_button`, `un_leave_button`
- **Requests (trigger GA votes):** `un_request_peacekeepers_button`, `un_request_humanitarian_aid_button`, `un_propose_condemn_button`, `un_propose_sanctions_button`, `un_propose_mandate_button`
- **Policy (members):** `un_lift_sanctions_button`, `un_peacekeeping_button`, `un_end_peacekeeping_button`, `un_fund_development_button`, `un_defund_development_button`, `un_human_rights_button`, `un_arms_control_button`
- **GP influence:** `un_champion_order_button`, `un_stop_championing_button`, `un_undermine_order_button`, `un_stop_undermining_button`

### Vote Topics (17, of which 6 are *binding* / vetoable)
The 6 binding topics — sanctions, peacekeeping_request, icc, condemn, reform, military_mandate — can be vetoed by [concept_un_permanent_member]s via the third option in `un_vote.1`. Vetoed binding resolutions that still have GA simple-majority pass in graduated/weak form, except the two that have **no** graduated form and are flat-blocked: reform (charter changes really do need P5 unanimity) and military_mandate (there is no weaker version of a licence to use force). All other 10 topics are recommendatory (non-vetoable). `expulsion` is recommendatory but uses a 2/3 supermajority threshold instead of simple majority.


| Resolution Tag | Triggered By | Description |
|---|---|---|
| `un_topic_condemn` | Event 2 / Propose Condemn button | Condemn military aggressor |
| `un_topic_human_rights` | Event 3 | Universal Declaration of Human Rights |
| `un_topic_reform` | Event 6 | UN institutional reform |
| `un_topic_heritage` | Event 9 | Cultural heritage program (UNESCO) |
| `un_topic_decolonization` | Event 12 | Anti-colonial declaration |
| `un_topic_npt` | Event 14 | Nuclear Non-Proliferation Treaty (IAEA) |
| `un_topic_pandemic` | Event 16 | Global pandemic response (WHO) |
| `un_topic_climate` | Event 17 | Climate accord (UNEP) |
| `un_topic_refugee` | Event 18 | International refugee resolution (UNHCR) |
| `un_topic_space` | Event 19 | Space cooperation (UNOOSA) |
| `un_topic_law_of_sea` | Event 21 | Convention on the Law of the Sea (ITLOS) |
| `un_topic_icc` | Event 22 | International Criminal Court |
| `un_topic_peacekeeping_request` | Request Peacekeepers button | Deploy peacekeepers to requesting country |
| `un_topic_aid_request` | Request Aid button | Humanitarian aid to requesting country |
| `un_topic_sanctions` | Propose Sanctions button | Economic sanctions against target country |
| `un_topic_expulsion` | Propose Expulsion button | Strip a permanent member's seat (2/3 supermajority) |
| `un_topic_military_mandate` | Propose Military Mandate button | Authorize one member to recover one claimed state region from one censured state — see § Military Mandates |

### Resolutions (script containers, 1.13.10+)
Every General Assembly resolution is a script container. Tags, variables and the lifecycle effects are documented in the header of `common/scripted_effects/un_vote_effects.txt`; checks live in `common/scripted_triggers/un_resolution_triggers.txt`.

- **Tags:** `un_resolution`, `un_topic_<topic>`, and a status: `un_res_voting` while open, then `un_res_passed` / `un_res_failed` / `un_res_lapsed`. `un_res_vetoed` marks a permanent-member veto; `un_res_target_accepted` marks a target that voted for its own censure.
- **Variables:** `un_res_proposer`, `un_res_target`, `un_res_support` (starts at 1, the proposer), `un_res_oppose`, `un_res_seq`, `un_res_months`, `un_res_vetoer`, `un_res_promoted` (expulsion), `un_res_mandate_region` / `un_res_mandate_beneficiary` (military_mandate). Voters are in the `un_res_yes` / `un_res_no` lists.
- **Lifecycle:** `un_resolution_open = { TOPIC = x }` creates the container, takes the lock, fires `un_vote.1` and schedules `un_vote.2`. `un_vote.2`'s immediate runs `un_resolution_decide` and `un_resolution_archive` (topic cooldown, history, lock release). Proposer events hold the lock with `un_vote_reserve` in their immediate and give it back with `un_vote_release` if they don't propose.
- **Scope passing:** the vote events get the resolution as `scope:un_resolution` through `trigger_event` and never read `un_active_resolution`, so a resolution stays readable after a newer one opens.
- **Cooldowns:** a closed resolution carries the timed `un_res_cooldown` variable (5 years, 10 for expulsion); `un_resolution_topic_on_cooldown = { TOPIC = x }` checks `un_resolution_history` for it. History eviction skips entries still on cooldown.
- **Watchdog:** `un_resolutions_monthly_update` (global monthly pulse) lapses a resolution still voting after 14 months (its `un_vote.2` never fired: the proposer stopped existing or left the UN, which used to lock the General Assembly for good), and frees a lock that neither a resolution nor a reservation holds.
- **Lobbying state:** resolution lobbying adds four lists (`un_res_lobbied`, `un_res_committed_yes`, `un_res_commit_kept`, `un_res_commit_broken`) and two variables (`un_res_commit_count`, `un_res_commit_pending`) to the same container. They need nothing from the lifecycle above — they are archived with the resolution and destroyed with it. See *Resolution lobbying (proof of concept)* below.

**Decisions (#275):**
- **One vote at a time: kept.** The `un_vote_active` lock is unchanged, so proposal frequency and balance are unchanged. The vote events already take the resolution as a scope, so lifting the lock later means replacing the lock gates (on-actions, buttons, proposer-event triggers) with a per-topic or capacity check; the watchdog would then need to walk a list of open resolutions instead of `un_active_resolution`.
- **History: the last 25 closed resolutions** (`un_resolution_history_cap`), no parent. A resolution must outlive a proposer annexed mid-vote, so the history cap is what destroys containers. The chamber widget below renders it.
- **Old saves: documented break.** A vote in progress when the mod updates is dropped: its queued `un_vote.1`/`.2` events carry no `scope:un_resolution` and fail their triggers, and the watchdog frees the lock on the next monthly pulse. Topic cooldowns from before the update are forgotten (they were global timed variables), and the legacy `un_vote_*` globals are left inert. Migrating would have meant reading ~25 variable names the code no longer sets, which logs "used but never set" on every load.

### Chamber Widget (display-only)
`gui/journal_entry_widgets/un_chamber_widget.gui`, wired into `custom_widget_container_2` of `je_united_nations`. It shows our own standing (member / permanent member / outsider), the resolution currently before the Assembly — topic, proposer, target, tally, the passage rule with a live projection of it, veto exposure or the recorded vetoer, months in session, and what carrying or falling would do — a collapsible ballot of the recorded yes/no voters, a collapsible register of authorized military mandates (`un_chamber_mandates_sgui`, § Military Mandates — actor, target, territory, beneficiary, status, months to expiry, plus the case we could table if we hold none), and a collapsible archive of the closed resolutions in `un_resolution_history`, newest first. Every empty state is spelled out ("No resolution is currently before the Assembly", "No resolutions have been recorded yet", "The Assembly has authorized no military mandate").

It is strictly a reader. Nothing in it creates, votes on, decides, archives or prunes a resolution — that all stays with the events, buttons and `un_vote_effects.txt`. Its text is built in script by `common/scripted_guis/un_chamber_sguis.txt` (five `scope = country` tooltip builders) over the line helpers in `common/scripted_effects/un_chamber_display_effects.txt`, and rendered through `[GetScriptedGui('...').ExecuteTooltip(...)]` — vanilla's documented "Using SGUIs to build lists in loc" pattern (`game/common/scripted_guis/scripted_guis.md`). It reads `global_var:un_active_resolution` and the `un_resolution_history` list in place: no country-side copy of either is kept, and no index, length or cap is assumed, so archive pruning is invisible to it.

- **Why script-built text rather than a GUI datamodel over the containers.** The containers hold *countries* (`un_res_proposer` / `un_res_target` / `un_res_vetoer`, and the `un_res_yes` / `un_res_no` lists), and `Var('x').GetCountry.GetName` is the chain this mod records as not working (`docs/guides/gui_modding_guide.md` gotcha #11) — the covert-operations widget stores a *state* (`iw_target_capital`) precisely to dodge it. Iterating a country variable list in script and printing `[THIS.GetCountry.GetName]` is the shape vanilla ships for exactly this case (`je_hispanoamerica_not_recognized_countries_sgui` + `HISPANOAMERICA_RECOGNITION_COUNTRIES_LIST_ENTRY`).
- **Annexed / missing countries.** Every country read is guarded twice: `exists = var:X` in script catches a reference that no longer resolves, and `AddLocalizationIf(THIS.GetCountry.Exists, ...)` in the loc line catches a country object that survives as a dead tag. Both fall back to "a former member" rather than an empty name.
- **Passage rule.** Mirrored from `un_resolution_decide`: `un_topic_expulsion` evaluates `un_vote_expulsion_passed >= 0` (2/3 of all current members), every other topic `un_res_margin >= 1` (simple majority of votes cast). The projection line runs those same two script values, so it cannot drift from the rule.
- **Outcomes.** A veto is orthogonal to pass/fail (`un_resolution_decide` has no veto branch), so the archive distinguishes carried, carried-but-vetoed (graduated form), carried-but-vetoed reform (blocked outright — charter reform has no graduated fallback), fell, fell-and-vetoed, and lapsed, naming the vetoing country whenever `un_res_vetoer` was recorded.
- **Consequences.** Reuses the `un_vote_<topic>_passed_tt` / `..._passed_vetoed_tt` / `un_vote_failed_tt` / `un_vote_expulsion_failed_tt` tooltips `un_vote.2` itself shows, so the figures can never drift from the ones the event applies.
- **Timing.** Only what the containers store: `un_res_months` (months in session / months it sat) and `un_res_seq` ("Resolution No. N"). A closed resolution still carrying `un_res_cooldown` gets a qualitative "cannot be tabled again" note — the variable is a timed one, and no date precision is claimed.
- **Expand/collapse state** lives in `GetVariableSystem` (client-side, never saved, never gameplay state): `un_chamber_votes`, `un_chamber_history`, `un_chamber_history_details`. Toggles are per *section*, not per row — a script container exposes no stable string id to the GUI (`ScriptContainer` has no `GetIDString`, and `GetVariableValue` returns a `CFixedPoint` that `Concatenate` cannot take), so a per-row toggle key cannot be built.
- **Cost.** `ExecuteTooltip` re-renders every frame the widget is visible, so the archive and its voting details each sit behind their own collapsed-by-default toggle.

### Military Mandates (authorized military mandates)

A **mandate** is the General Assembly's written authorization for **one** actor to recover **one** state region from **one** target, and nothing else. It is the only thing that makes the mod's `te_un_mandate_restore_state` war goal selectable, and the only thing that makes it free. Stage 1 of the mandates / standing / lobbying arc; the two standing hooks below are the seam stage 2 fills in.

**Files:** `common/scripted_effects/un_mandate_effects.txt` (state machine + the two hooks), `common/scripted_triggers/un_mandate_triggers.txt` (every gate), `common/war_goal_types/te_un_mandate_restore_state.txt`, `common/diplomatic_plays/te_un_mandate_play.txt`, `common/on_actions/un_mandate_on_actions.txt`, `events/un_mandate_events.txt`, `common/ai_strategies/other.txt` (`ai_strategy_un_mandate`), plus the mandate branches in `un_buttons.txt`, `un_vote_events.txt`, `un_chamber_display_effects.txt`, `un_chamber_sguis.txt` and `un_chamber_widget.gui`.

#### The objective, and why this one

`kind = return_state`: recover a named state region the actor holds a `has_claim_by` claim on from the state that holds it. Everything about the goal except `possible` and `infamy` is vanilla `return_state` — same kind, contestion, execution priority, maneuvers, `mirrored_wargoal`. Two settings differ: `can_add_for_other_country` is **absent** (so holder ≡ creator: the mandate names one actor, and 1.14 does not document which of the two the engine charges for a goal added on another country's behalf), and `requires_interest` is **absent** (the Assembly's authorization is what licenses the intervention; an interest marker is not additionally required).

**v1 beneficiary = the actor.** `un_mnd_beneficiary` is a real field on the container and is read wherever the beneficiary is displayed or validated, but the propose button always sets it to the proposer. Widening it to a third party needs `can_add_for_other_country`, a beneficiary that is a participant in the play, and an answer to the infamy-attribution question above — all of which are v2, and none of which need a save migration, because the field already exists.

#### Where the discount lives

Zero infamy is **computed, not declared**. `infamy` adds the full vanilla `return_state` formula only when `un_mandate_covers_goal = no`, so a goal reachable without a mandate (a future version, a path `possible` does not cover) costs exactly what vanilla charges. Nothing anywhere adds a country-wide infamy modifier, which is what makes "only the authorized goal is discounted" true by construction: a plain `return_state` on the very same province, added in the same play, still costs full price.

`un_mandate_covers_goal` accepts both `un_mandate_active` and `un_mandate_bound` on purpose. The infamy block is re-read whenever the play panel redraws, and a goal whose price jumped from 0 to the full figure the instant it was added would be unreadable.

#### State model

Container tags: `un_mandate`, plus exactly one lifecycle tag —

| Tag | Meaning |
|---|---|
| `un_mandate_active` | issued, not yet exercised |
| `un_mandate_bound` | exercised: the war goal is in a play |
| `un_mandate_complied` | the authorized goal was enforced |
| `un_mandate_violated` | a prohibited objective was taken against the same target |
| `un_mandate_abandoned` | the actor backed down from the bound play |
| `un_mandate_expired` | lapsed unused after `un_mandate_expiry_months` (60) |
| `un_mandate_void` | preconditions failed (`un_mandate_still_valid`), or the bound play ended without enforcement |
| `un_mandate_forfeit` | set *alongside* `bound`: the actor left the UN mid-play. Compliance still happens but pays nothing and routes to the violation hook instead |

Container variables: `un_mnd_seq`, `un_mnd_actor`, `un_mnd_beneficiary`, `un_mnd_target`, `un_mnd_region` (a `state_region`, which unlike a state never stops existing), `un_mnd_resolution` (a back-reference; may dangle once the resolution is evicted from `un_resolution_history` — nothing reads it), `un_mnd_months`, `un_mnd_grace` (timed, 60 days, set on binding), `un_mnd_closed_months`.

Globals: `un_mandate_seq` (counter), `un_mandate_registry` (every mandate, live and closed, capped at `un_mandate_registry_cap` = 12; closed entries retire after `un_mandate_closed_retention_months` = 60, one per month).

Country side: `un_mandate_current` on the actor. This is simultaneously the "one live mandate per country" rule and an O(1) index, so the war goal's `possible` and `infamy` never scan the container pool. Every gate reads it through `un_mandate_has_live_mandate`, which tests the container's tags rather than the variable's mere presence, so a dangling index can never lock a country out; the monthly country pulse drops one if it finds it.

#### Lifecycle

| Step | Trigger site | Effect |
|---|---|---|
| propose | `un_propose_mandate_button` | `un_resolution_open = { TOPIC = military_mandate }`, then stores `un_res_mandate_region` / `un_res_mandate_beneficiary` on the resolution |
| grant | `un_vote.2`, passed and not vetoed | `un_mandate_create` (re-validates first) |
| bind | `on_wargoal_added`, monthly sweep | `un_mandate_try_bind` |
| comply | the war goal's own `on_enforced` | `un_mandate_record_enforcement` |
| violate | `on_wargoal_added`, monthly sweep | `un_mandate_check_prohibited` |
| abandon | `on_diplo_play_back_down` | `un_mandate_on_back_down` |
| expire / void / prune | monthly sweep | `un_mandate_tick`, `un_mandate_prune_registry` |

Every on_action hook is mirrored by the monthly sweep, which is the safety net if one fails to fire; the hooks exist so the state is right *immediately*, closing the window in which a mandate still reads `active` after its goal is already in a play.

**One-play binding.** `un_mandate_authorizes_new_goal` lists the goal when the mandate is `active` (first and only exercise), or when it is `bound` **and the play already carries the goal type** — which is the binding rule expressed as a trigger, because a fresh play cannot answer `has_play_goal`. Re-adding in a second play is therefore impossible, and a second *copy* in the same play is blocked by `validate_conflicts_war_goals_holder` plus the fact that a (state region, owner) pair is a single state. Compliance can pay out only once because `un_mandate_close` clears the actor's index before calling the hooks.

**Prohibited objectives** are an explicit list (`un_mandate_has_prohibited_goal`) of every further *territorial* or *subjugation* demand, checked in both the play and the war forms: annex_country, conquer_state, **return_state**, take_treaty_port, liberate_country, secession, unification, te_reunify_country; make_protectorate / make_tributary / make_dominion / make_personal_union / make_crown_land / make_chartered_company / release_as_subject / transfer_subject; plus the punitive regime_change and humiliation. `return_state` is on the list on purpose — a second, fully-priced claim recovered from the same state in the same war is still more territory than the resolution named, and matching is by type key so the mandate's own goal cannot collide with it. Goals that take nothing for the holder (liberate_subject, independence, revoke_claim) and the non-territorial demands (open_market, ban_slavery, the demand_* group, force_nationalization, …) are deliberately allowed: a mandate holder may still bargain, it may not take more land or more subjects. The list is explicit because the engine offers no way to enumerate a play's war goals from script — `*_has_war_goal_of_type_against` names one type at a time. Keep it in step with `common/war_goal_types/`.

The check acts on a **bound** mandate only. A country that fights an ordinary, fully-priced war against the same state while holding an *unexercised* authorization has abused nothing — it paid for every goal it took. The violation is taking more than the Assembly licensed *while using* the licence. `on_wargoal_added` binds before it checks, so a play opened with the authorized goal and a conquest in the same breath is caught on whichever addition completes the pair. **Known v1 limitation:** goals added after the authorized one has already been enforced are not seen, because the mandate is closed by then — "breaking the settlement" is the part of the brief marked *if detectable*, and this is the part that is not.

#### Edge cases

| Situation | Outcome | Hook |
|---|---|---|
| Expires unused (60 months `active`) | `un_mandate_expired` | none |
| Expires while `bound` | stays valid for that play: `un_mnd_months` keeps counting but only the `active` branch checks it against expiry | — |
| Target no longer holds the region, or claim revoked, while `active` | `un_mandate_void` | none |
| Target / beneficiary ceases to exist while `active` | `un_mandate_void` | none |
| Actor leaves or is annexed while `active` | `un_mandate_void` | none |
| Actor leaves the UN while `bound` | keeps the mandate (stripping it would delete a war in progress) and adds `un_mandate_forfeit`; a later compliance is recorded but routed to the violation hook | `un_mandate_on_violated`, on completion |
| Actor annexed while `bound` | `un_mandate_void` — checked first in the bound branch, because every later check needs a live actor and the pruner only retires *closed* entries |  none |
| Bound play ends with the goal never enforced | `un_mandate_void` after the 60-day grace — deliberately *not* a violation, because the goal can vanish for reasons outside the actor's control | none |
| Actor backs down from a play in which it holds the authorized goal (`active` or `bound`) | `un_mandate_abandoned` | `un_mandate_on_violated` |
| Prohibited objective added against the same target | `un_mandate_violated` | `un_mandate_on_violated` |
| Authorized goal enforced | `un_mandate_complied` | `un_mandate_on_complied` |
| UN game rule disabled | `un_mandate_still_valid` fails (`has_game_rule = united_nations_enabled`) → `un_mandate_void` on the next sweep | none |

Void and closed mandates stay on the register for five years so the chamber panel can show them, then the monthly pruner destroys one per month. Nothing leaks: every terminal transition goes through `un_mandate_close`, which clears the actor's index, and the pruner only ever retires entries that `un_mandate_is_closed`.

#### Standing hooks (stage 2)

`un_mandate_on_complied` and `un_mandate_on_violated` are called from **container scope**, with the outcome tag already stamped, so a standing implementation can branch on `has_tag = un_mandate_abandoned` vs `un_mandate_violated` without new plumbing. They fire **exactly once per mandate**. v1 contents, built only from effects and modifiers the UN system already ships: complied → `un_authority +5` and `un_vote_success_reward` on the actor; violated / abandoned / complied-while-forfeit → `un_authority −5` and `un_condemned_modifier` on the actor. Stage 2 should *add* to these, not replace them, and the relations/catalyst pair for a third-party beneficiary belongs in `un_mandate_on_complied` once `un_mnd_beneficiary` can differ from the actor.

#### Proposal, eligibility and AI

Proposing needs: UN membership, `un_authority` ≥ 40, no live mandate of our own, no `un_ga_resolution_modifier` / `un_request_cooldown`, no vote in session, no mandate proposal of ours in the last five years (`un_mandate_proposal_cooldown`), and an eligible case. A case is a country that is not a subject, not decentralized, **already censured by this Assembly or notorious in its own right** (`un_mandate_target_is_notorious`: infamy ≥ 25, or `un_condemned_modifier` / `un_non_binding_rebuke_modifier` / `un_sanctions_target_modifier` / `un_sanctions_partial_modifier`), and holding a state we have a claim on. That gate is what keeps the topic from becoming a general-purpose land-grab licence, and it ties the mandate into the existing condemn / sanctions machinery.

**The button picks the case**; a scripted button cannot prompt. `un_mandate_select_case` takes the highest-scoring target by `un_mandate_case_score` (already condemned > sanctioned > merely notorious, rival > stranger, weaker > stronger) and its largest claimed state. `un_mandate_case_exists` mirrors the same filter for the gate — **the two must be kept in step**. The chamber panel renders the same pick through the same effect *before* the button is pressed, so the preview cannot drift from the proposal.

**Cooldown divergence, deliberate.** `un_resolution_topic_on_cooldown` is topic-wide: one member's mandate vote would bar every other member for five years and leave the feature dead on a busy map. The mandate topic opts out and throttles per country instead. `un_resolution_archive` still stamps `un_res_cooldown` on the closed resolution (that is what keeps it in the history), but nothing consults it for this topic.

**Veto = flat block.** `military_mandate` joins `reform` as a binding topic with no graduated form: there is no coherent weaker version of "you may go to war over this", so a veto blocks it outright and `un_vote.2` applies no effect. Vetoing one is deliberately **not** on the infamy-on-veto list (ICC / condemn / peacekeeping) — charging infamy for restraint would read as the system punishing peace.

**AI.** `ai_strategy_un_mandate` is picked up only by a country that holds a live mandate, its `aggression` fires only at the named target, and `wargoal_weights` puts the authorized goal ahead of the alternatives. The AI faces exactly the player's gates: the war goal's `possible`, the play type's `possible` and `selectable_in_lens` all read the same mandate.

### UN Standing (international standing)

A member's own **record** in the organisation: what it has delivered and what it has complied with. Stage 2 of the mandates / standing / lobbying arc, built on the two hooks stage 1 left in `un_mandate_effects.txt`.

Standing is **not** `global_var:un_authority`. Authority is one global number measuring how much the institution itself is worth; standing is a per-country number measuring how much *this* member is worth to it. Nothing in the standing system reads or writes `un_authority`, and nothing in the authority system reads standing.

**Files:** `common/script_values/un_standing_values.txt` (every tuning number, once), `common/scripted_triggers/un_standing_triggers.txt` (tiers, suspension, the five `un_standing_program_active_*` definitions, the proposal gate), `common/scripted_effects/un_standing_effects.txt` (the only writers, the monthly pulse, the tier-modifier refresh), the four `un_standing_*_modifier` entries in `common/static_modifiers/extra_modifiers.txt`, the display block in `common/scripted_effects/un_chamber_display_effects.txt` + `common/scripted_guis/un_chamber_sguis.txt` + `gui/journal_entry_widgets/un_chamber_widget.gui`, plus the hook sites listed below.

#### The score

| | |
|---|---|
| Variable | `un_standing` — country, 0–100 |
| Neutral seed | **50**, written once on a member's first monthly UN pulse |
| Written by | `un_standing_gain = { AMOUNT REASON }`, `un_standing_loss = { AMOUNT REASON }`, and `un_standing_init` (seed only). **Nothing else writes it.** |
| Clamped by | `un_standing_clamp`, called from both helpers straight after the write (`change_variable` has no clamp argument — same shape as the `un_authority` clamp) |
| Reason | `un_standing_last_reason`, a numeric code stamped by both helpers; mapped back to words by `un_standing_reason_line` for the chamber panel. A variable holds a number, not a string, so the code table at the top of `un_standing_effects.txt` and the `je_un_standing_reason_*` keys must be kept in step. |

**Both helpers are a no-op for a country with no `un_standing` variable.** That is what makes standing a record *of membership*: a country that has never joined has no standing and cannot acquire one by being censured, and every country in a save made before this feature simply has none until it next pulses as a member. It also removes any ordering dependency — `un_leave_button` can charge a loss without worrying about whether the variable exists.

**Tiers** are derived from the one variable by scripted triggers; nothing caches a tier. A country with no variable reads as Neutral.

| Tier | Range | Trigger |
|---|---|---|
| Disgraced | < 20 | `un_standing_tier_disgraced` |
| Poor | 20–39 | `un_standing_tier_poor` |
| Neutral | 40–59 | `un_standing_tier_neutral` (also the no-variable case) |
| Respected | 60–79 | `un_standing_tier_respected` |
| Exemplary | ≥ 80 | `un_standing_tier_exemplary` |

#### Tuning table

Every figure below is a script value in `common/script_values/un_standing_values.txt` and is defined exactly once. Two places restate them in words and must be edited alongside a re-tune: `je_un_standing_help_sources` / `_losses` / `_limits`, and the `un_standing_*_tt` **loss** tooltips. Gains are deliberately stated without a figure, because diminishing returns mean the delivered amount is almost never the nominal one.

| Script value | Value | What it does |
|---|---|---|
| `un_standing_min` / `un_standing_max` | 0 / 100 | bounds |
| `un_standing_neutral_start` | 50 | seed for a new member |
| `un_standing_tier_poor_floor` … `_exemplary_floor` | 20 / 40 / 60 / 80 | tier boundaries |
| `un_standing_dr_divisor` | 50 | gains × clamp((100 − standing)/50, floor, 1) |
| `un_standing_dr_floor` | 0.1 | a gain is never worth less than a tenth of face value |
| `un_standing_program_min_months` | 24 | continuous months before an ongoing programme pays anything |
| `un_standing_program_monthly_gain` | 0.3 | nominal, per qualifying programme, per month |
| `un_standing_program_yearly_cap` | 6 | nominal programme accrual per rolling 12 pulses, **across all five programmes together** |
| `un_standing_months_per_year` | 12 | rolling-year length |
| `un_standing_early_withdrawal_loss` | 2 | abandoning a programme before the minimum |
| `un_standing_undermine_monthly_loss` | 0.15 | per month while undermining |
| `un_standing_undermine_suspend_months` | 24 | sustained undermining suspends the benefits |
| `un_standing_aid_delivered_gain` | 3 | real humanitarian aid delivered |
| `un_standing_peacekeeping_delivered_gain` | 3 | a real peacekeeping deployment |
| `un_standing_request_contribution_gain` | 2 | taking on a share of an aid/peacekeeping programme the Assembly voted through |
| `un_standing_compliance_gain` | 2 | complying with a binding decision at a real cost |
| `un_standing_mandate_complied_gain` | 6 | an authorized military mandate discharged as written |
| `un_standing_delivery_relations` | 5 | one-off relations with the country that asked for the aid / peacekeepers |
| `un_standing_mandate_violated_loss` | 12 | mandate violated, abandoned, or complied-while-forfeit |
| `un_standing_defiance_loss` | 5 | refusing a binding resolution, sanctions busting, court defiance |
| `un_standing_condemned_loss` | 8 | censured by the Assembly |
| `un_standing_rebuked_loss` | 3 | non-binding rebuke (a vetoed censure); also an *accepted* censure |
| `un_standing_sanctioned_loss` | 6 | placed under sanctions |
| `un_standing_sanctioned_partial_loss` | 3 | partial sanctions; also *accepted* sanctions |
| `un_standing_leave_loss` | 5 | withdrawing from the UN |
| `un_standing_seat_stripped_loss` | 5 | a permanent seat voted away |
| `un_standing_mandate_floor` | 20 | standing floor on the propose-mandate button |

Suspension durations are literals, not script values: `set_variable`'s `days` argument is not documented to take one. 3650 days (10 years) for a broken mandate, 1825 (5 years) for a stripped seat.

#### Sources — reward delivery, not toggling

**Ongoing programmes.** Five of them. "Running" is a scripted trigger per programme — `un_standing_program_active_*` — not a bare marker test. Peacekeeping and development require **both** the marker and the GDP-scaled cost modifier on the journal entry (`un_peacekeeping_contributor_modifier` + `un_peacekeeping_contributor_cost`, `un_development_contributor_modifier` + `un_development_contributor_cost`); human rights, arms control and championing the order require only their marker (`un_human_rights_champion_modifier`, `un_arms_control_participant_modifier`, `un_champion_order_cost`), because that marker *is* the cost bundle. The distinction is load-bearing: `un_vote_apply_resolution_compliance` pledges a country to peacekeeping by adding only the marker — `un_vote.2`'s levy already ran before `un_vote.3` fires, so the pledger pays nothing until the *next* request carries — and a cost-free pledge must neither start a standing clock (a free marker accruing 0.3/month is exactly the token-for-rewards the brief forbids) nor be charged an early-exit fee when `un_vote.2`'s failed/vetoed branches revoke precisely those cost-free markers. Each programme is ticked by `un_standing_program_tick` from the monthly pulse into its own continuous-month counter (`un_standing_months_peacekeeping`, `…_development`, `…_human_rights`, `…_arms_control`, `…_champion`). A programme pays **nothing** until its counter reaches 24, and the counter is **discarded** the month the programme ends — so enable → disable → enable starts again from zero and yields nothing. Accrual is `count × 0.3` nominal per month, trimmed to what is left of the year's 6-point nominal budget (`un_standing_year_gain`, reset every twelfth pulse), and then scaled by diminishing returns inside `un_standing_gain`.

**One-off deliveries.** Each is paid at the single site where the delivery actually happens, and none of them draws on the programme yearly cap — each is structurally single-payout behind its own multi-year cooldown, so there is nothing to farm. The cap exists to stop programme toggling, not to ration genuine deliveries.

| Delivery | Site | Amount | Why it cannot pay twice |
|---|---|---|---|
| Humanitarian aid delivered | `events/un_events.txt:789` (`un_events.7` option A) | 3 | One option runs per event firing; the event's own trigger requires the country to carry neither `un_humanitarian_aid_modifier` nor `un_humanitarian_token_modifier`, and it has a five-year `cooldown`. Option B (a token contribution) pays **0** by design. |
| Peacekeepers deployed | `events/un_events.txt:427` (`un_events.4` option A) | 3 | Same shape: one option per firing, five-year cooldown, and the target must not already carry `un_peacekeeping_deployed_modifier`. Option B (observers only) pays **0**. |
| Share of a voted-through aid / peacekeeping programme | `common/scripted_effects/un_vote_effects.txt:560, 577` via `un_vote_standing_request_contribution` | 2 (+5 relations with the requester) | `un_vote.2` fires `un_vote.3` **once per member per resolution**; an event runs exactly one option, and the only two options that reach `un_vote_apply_resolution_compliance` (A and B) are mutually exclusive by their own triggers. It sits in the same branch that books `un_aid_contribution_count` / `un_peacekeeping_contribution_count`. |
| Complied with a binding decision we voted against | `un_vote.3` option B, `events/un_vote_events.txt` | 2 | Same once-per-member-per-resolution argument. Gated on `un_resolution_is_binding` — yielding on a recommendation costs nothing, so it earns nothing — and **excluding `un_topic_peacekeeping_request`**, the one topic that is both binding and a pledge topic: `un_vote_apply_resolution_compliance` has just paid this same country the contribution award, and paying compliance on top would make a no-voter who complies worth twice a yes-voter doing the same thing. |
| Enforced a sanctions regime | `events/un_events.txt:537` (`un_events.5` option A) | 2 | One option per firing; the event requires `un_sanctions_enforcer_modifier` and not `un_sanctions_enforcement_modifier`, plus a five-year cooldown. Option B (token compliance) pays **0**. |
| Accepted a court ruling against us | `events/un_events.txt:969` (`un_events.8` option A) | 2 | One option per firing; the event requires neither court modifier be present, plus a five-year cooldown. Option B (contest the jurisdiction) pays and costs **0** — arguing a case is legitimate. |
| Mandate discharged as written | `common/scripted_effects/un_mandate_effects.txt:230` (`un_mandate_on_complied`) | 6 | `un_mandate_close` clears the actor's `un_mandate_current` index **before** calling the hook, so no path can re-enter for the same mandate; the hook fires exactly once per mandate. |

**Voting is never a delivery.** Voting with the majority, voting yes, and casting a veto all pay nothing. A veto is a lawful act of a permanent member and costs nothing either.

**Relations gains** are implemented only where an existing site already knows both countries. That is the request-contribution site (the contributor and `scope:un_vote_proposer`, the country that asked) and the aid / peacekeeping events, which already grant +30 / +20 relations with the recipient in the vanilla-of-this-mod option body. The mandate beneficiary case is **not** implemented: `un_mnd_beneficiary` is always the actor in v1, and the documented gate for it stays where stage 1 left it, in `un_mandate_on_complied`.

#### Losses

| Loss | Site | Amount |
|---|---|---|
| Programme abandoned before 24 months | `common/scripted_effects/un_standing_effects.txt:217` (`un_standing_program_tick`, counter-discard branch) | 2 |
| Undermining the order | `common/scripted_effects/un_standing_effects.txt:235` (`un_standing_undermine_tick`) | 0.15/month |
| Censured by the Assembly | `events/un_vote_events.txt:2239` (`un_vote.2`, condemn passed, not vetoed) | 8 |
| — having accepted the censure | `events/un_vote_events.txt:2248` | 3 |
| Rebuked (vetoed censure, graduated form) | `events/un_vote_events.txt:2280` | 3 |
| Sanctioned | `events/un_vote_events.txt:2532` | 6 |
| — having accepted the sanctions | `events/un_vote_events.txt:2538` | 3 |
| Partial sanctions (vetoed form) | `events/un_vote_events.txt:2557` | 3 |
| Defied a binding resolution | `events/un_vote_events.txt:2899` (`un_vote.3` option C) | 5 |
| Sanctions busting | `events/un_events.txt:582` (`un_events.5` option C) | 5 |
| Court defiance | `events/un_events.txt:1011` (`un_events.8` option C) | 5 |
| Mandate violated / abandoned / complied-while-forfeit | `common/scripted_effects/un_mandate_effects.txt:268` (`un_mandate_on_violated`) | 12 **+ 10-year suspension** |
| Permanent seat voted away | `events/un_vote_events.txt:2175` (`un_vote.2`, expulsion passed) | 5 **+ 5-year suspension** |
| Withdrawing from the UN | `common/scripted_buttons/un_buttons.txt:396` (`un_leave_button`) | 5, then **frozen** |

**Early withdrawal is charged from the pulse, not from the withdraw buttons.** One site then covers every voluntary exit path — the four withdraw buttons, `un_stop_championing_button`, and anything added later — treats the AI exactly like the player, and needs no edit to the button effect blocks that `gen_un_button_descs.py` generates tooltips from. (Verified: `gen_un_button_descs.py --dry-run` reports "no changes" against this branch.) It does **not** charge for a cost-free peacekeeping pledge revoked by `un_vote.2`, because the `un_standing_program_active_*` trigger never opened a clock for one. The trade-off: a withdraw button's own tooltip does not name the standing cost. The chamber's "How standing works" panel does.

**Leaving freezes, it does not reset.** `un_standing_clear_counters` drops only the duration counters; the score, the last-reason code, the rolling-year variables and any suspension are left alone. Resetting to neutral would make resignation a way for a disgraced member to launder its record by rejoining. Leaving is charged once (5) and the per-programme early-withdrawal charges are skipped — the pulse's non-member branch discards counters without billing them, or walking out mid-programme would cost up to 5 × 2 on top.

**"Expulsion" in this mod is seat-stripping only.** The `expulsion` topic strips `un_permanent_member_modifier` / `un_security_council_modifier`; it does not remove `un_member_modifier`. (`un_expelled_cooldown` is defined in `extra_modifiers.txt` and checked by `un_join_button`, but nothing ever applies it.) So there is no "expelled from the UN" standing case to write.

**"Successful mediation" has no source.** The UN system ships no mediation mechanic — `un_walkout_mediator_modifier` is a one-shot event outcome in `un_events.20`, not a mediation *process* with a success condition. Nothing was invented for it; it is a future source once a mediation mechanic exists.

**Refusing to volunteer aid costs nothing.** `un_events.7` option C already carries `un_refused_aid_penalty_modifier` and an authority hit. Declining to volunteer is not a broken commitment, a defied resolution or an exceeded mandate, so it is deliberately outside the loss list.

#### Benefits — modest, capped, suspended on serious violation

Four discrete country-scoped static modifiers, not one dynamically scaled family: the effects are small enough that a continuous multiplier would be unreadable in the modifier list, and a discrete tier is what the player is told they have. Applied at **country** scope (not on the journal entry) so they appear in the country's own modifier list with their own name and description.

| Tier | Modifier | Effects |
|---|---|---|
| Exemplary | `un_standing_exemplary_modifier` | `country_diplomatic_reputation_add = 4`, `country_infamy_decay_mult = 0.10`, `country_improve_relations_speed_mult = 0.05` |
| Respected | `un_standing_respected_modifier` | `country_diplomatic_reputation_add = 2`, `country_infamy_decay_mult = 0.05` |
| Neutral | *(none)* | — |
| Poor | `un_standing_poor_modifier` | `country_diplomatic_reputation_add = -2` |
| Disgraced | `un_standing_disgraced_modifier` | `country_diplomatic_reputation_add = -4`, `country_infamy_decay_mult = -0.10` |

**Scale evidence.** `country_diplomatic_reputation_add`: `law_war_crimes_forbidden` +2, `law_humanitarian_regulations` +4, `law_limited_war` +6, `law_total_war` −20, each `principle_multilateral_institutions_*` level +5, `mandate_system_modifier` +5. A top tier worth +4 is one good law, not a new pillar. `country_infamy_decay_mult`: `un_condemnation_leader_modifier` +0.15, `un_arms_control_participant_modifier` +0.10, `un_condemned_modifier` −0.20, vanilla `diplomatic_mitigation` +0.25 — a top tier of +0.10 sits below all of them. `country_improve_relations_speed_mult`: `un_member_modifier` already grants +0.10 and `un_membership_benefits_modifier` another +0.10, so +0.05 is a quarter of what membership itself is worth. No tier grants prestige, influence or leverage: those belong to the membership and Security Council modifiers, and standing must not become a second copy of them.

**One refresh site.** `un_standing_refresh_tier_modifier`, called once per country per month from `un_standing_country_pulse`, which is itself called from exactly one place: `je_united_nations`' `on_monthly_pulse` (`common/journal_entries/je_united_nations.txt:472`). It sits *outside* the member-only block, because a country that has left still needs its counters dropped and its tier modifier removed. The swap only writes when the tier actually changes (`NOT = { has_modifier = X }` probe first), so an unchanged tier churns nothing.

**Suspension** withholds the two positive tiers only; a suspended Exemplary member carries no tier modifier at all, and a suspended Disgraced one still carries its penalty. `un_standing_benefits_suspended` reads two sources, deliberately different in shape: the timed `un_standing_suspended` variable stamped by a single serious violation (broken mandate, stripped seat), which runs out on its own; and sustained undermining (`un_standing_months_undermine >= 24`), which is a *state* and lifts the month the country stops, because the counter is discarded then.

#### AI parity

There is **no `is_ai` branch anywhere in the standing system**. Accrual, losses, suspension and the tier modifier all run from the same monthly pulse for every holder of the journal entry, and every hook site is in an effect block both the player and the AI reach. The one AI-specific piece is the vote lean below, which reads the *proposer's* standing and is therefore symmetric between a human proposer and an AI one.

#### The AI vote hook

Four `modifier` blocks with **literal adds**, one per non-neutral standing tier — Exemplary **+5**, Respected **+2**, Poor **−2**, Disgraced **−5** — sit together at the top of `un_vote.1` option A's `ai_chance` in `events/un_vote_events.txt` (search `SHARED PROPOSER-STANDING LEAN`), against a base of 40 and next to the existing alliance (+20), bloc (+15) and rivalry (−30) terms. It is a lean, never a guarantee. Option B is untouched: raising A already lowers B's share of the roll, and a symmetric penalty would double a deliberately modest nudge. Nothing else in any `ai_chance` was changed.

Each block reads `scope:un_vote_proposer ?= { un_standing_tier_<tier> = yes }`: the `?=` covers a proposer annexed mid-vote, and the tier triggers treat a country with no recorded standing (a founder's first month, a pre-feature save) as Neutral, so at most one block ever applies.

> **Why literals.** No vanilla or mod event uses a **named script value** as an `ai_chance` modifier's `add`, and a rejected value would fail silently — the lean would simply never apply. The first draft used one shared script value; it was replaced with tier-keyed literal adds, which is the form every existing block in that `ai_chance` already uses.

#### Gates

`un_propose_mandate_button`'s `possible` gained one line (`common/scripted_buttons/un_buttons.txt:543`): `un_standing_at_least = { VALUE = un_standing_mandate_floor }`, i.e. not Disgraced. A member that has done nothing at all sits at the neutral 50, so this cannot make the mandate unreachable for an ordinary member — it bars only a country whose record the Assembly has already wrecked, and `un_standing_at_least` passes for a country with no variable.

It was deliberately **not** added to `un_mandate_actor_in_good_standing`. That trigger is also read by `un_mandate_still_valid`, so a floor there would **void a mandate already in the field** the moment the actor's standing dipped — deleting a war the player is fighting over a score movement. The gate belongs on the proposal, not on the authorization.

#### Display

The chamber widget's status panel (`un_chamber_status_sgui`, `common/scripted_guis/un_chamber_sguis.txt:45`) gained `un_standing_status_block`: the tier and the score, why benefits are suspended if they are, what the current tier is doing (quoted from the static modifier's own `$name$` and `$name_desc$` loc, so the line cannot drift from `extra_modifiers.txt`), this rolling year's programme accrual against the cap, and the most recent reason for a change. A member whose first pulse has not run yet reads as "not yet recorded" rather than printing a missing variable; a non-member gets one line saying standing is a record of membership.

A new collapsed-by-default section, "How International Standing Works" (`un_chamber_standing_help_sgui`, toggle key `un_chamber_standing`), carries the sources, the losses and the limits in plain language. Split into its own SGUI for the same reason the archive is: `ExecuteTooltip` re-renders every frame the panel is visible.

Every line is `custom_tooltip` text built in script, in the same read-only file as the rest of the chamber's display effects, and no country other than the scoped one is referenced anywhere in it — so there is nothing an annexation can break.

#### Save compatibility

Nothing assumes any standing variable exists. A save that predates the feature loads with no `un_standing` anywhere; each member is seeded with the neutral 50 on its first monthly UN pulse, non-members get nothing, and every trigger treats "no variable" as Neutral / gate-passes. Nothing existing was renamed, and no existing variable, modifier or effect changed meaning. The only new tooltip text on existing buttons is one line on `un_leave_button` and one gate line on `un_propose_mandate_button`.

#### History-chart hook (not implemented here)

PR #308 adds a history store. Once both are merged, national standing should be sampled monthly from the UN country pulse with `te_history_record_sample = { METRIC = un_standing VALUE = var:<un_standing> }`, placed at the end of `un_standing_country_pulse` inside the member branch. That effect is **not** referenced anywhere in this branch's script — it does not exist in this checkout.

#### Notes for the lobbying stage (stage 3, now built — see *Resolution lobbying* below)

- **Helpers to call:** `un_standing_gain = { AMOUNT = <points> REASON = <code> }` and `un_standing_loss = { AMOUNT = <points> REASON = <code> }`, both country-scoped, both no-ops for a country with no standing. Add your reason codes to the table at the top of `un_standing_effects.txt`, the chain in `un_standing_reason_line`, and matching `je_un_standing_reason_<code>` keys. Use the 30+ range to stay clear of this stage's 1–6 and 20–29.
- **A broken lobbying promise** is a broken commitment: call `un_standing_loss` once, at the single site where the promise is detected as broken, and put the tuning figure in `un_standing_values.txt` next to the rest. If it is meant to be a *serious* violation, also call `un_standing_suspend = { DAYS = <literal> }` — `set_variable`'s `days` argument will not take a script value.
- **A fulfilled promise** is a delivery: call `un_standing_gain` once, at the site where the thing promised actually happens, not where it is promised. Diminishing returns are applied inside the helper — do not pre-scale. Decide explicitly whether it should draw on the programme yearly cap; nothing outside `un_standing_program_award` does today, and the simplest correct answer is that it should not.
- **The AI vote hook** is in `events/un_vote_events.txt`, `un_vote.1` option A's `ai_chance`, marked `<-- LOBBYING STAGE: ADD YOURS HERE`. Add your own `modifier` block(s) there with **literal** adds (see *Why literals* above); do not fold lobbying into the standing blocks. The two must stay separately tunable and separately attributable.
- **Do not write `un_standing` directly.** The clamp, the diminishing returns and the reason stamp all live in the two helpers, and the "no other code writes the variable" rule is what makes the score auditable.


### Resolution lobbying (proof of concept)

One lobbying action, deliberately. While a resolution is open, its **proposer** may ask one other member to undertake to vote in favour; in exchange the proposer immediately owes that member a vanilla **diplomatic obligation**. The undertaking is recorded on the resolution *separately from the ballot*, and it is settled — honoured or broken — exactly once, at the moment the recipient's vote is booked. Stage 3 of the mandates / standing / lobbying arc, and the last of them.

Everything else in the original lobbying brief is **not built**; the list is at the end of this section.

#### The vehicle: a diplomatic action, not a journal-entry button

`un_secure_commitment_action`, in `common/diplomatic_actions/un_lobbying.txt`. A scripted button cannot prompt for a free choice of country, so the alternative would have been the mandate button's "deterministically target the single best candidate" shape (`un_mandate_select_case`, `un_mandate_effects.txt:69`) — a worse fit for an action whose whole point is *which* member you go to. Three engine capabilities decided it:

- **Targeting.** A diplomatic action is aimed through the ordinary diplomacy UI at whichever member the proposer likes.
- **`requires_approval = yes`** gives a human recipient the engine's own accept/decline request, which is the "human-controlled recipients receive a choice" requirement satisfied with no popup event of our own (`game/common/diplomatic_actions/diplomatic_action.md`, "Whether this action requires the approval of the target").
- **`ai.accept_score` is itemised**: every `add` carries a `desc`, and the engine renders the list as the acceptance tooltip. That is "display the main reasons for support or opposition" for free, and permanently in step with the numbers the AI actually uses. Template: vanilla's pactless approval action `game/common/diplomatic_actions/03_violate_sovereignty.txt` (no `pact` block ⇒ no pact is created). Conventions — `groups`, `custom_tooltip`'d `possible` clauses, loc key families — follow the mod's own nine covert-warfare actions in `common/diplomatic_actions/covert_operations.txt`. Diplomatic actions need no GUI or category registration.

#### The obligation is real, and script can both create and remove it

`set_owes_obligation_to = { country = <country> setting = yes|no }`, **scoped to the country that owes**. Verified in vanilla at `game/common/history/diplomacy/00_favors.txt:3` (the historical favour setup), `game/common/decisions/france_savoy.txt:97` (granted), and `game/common/diplomatic_actions/02_obligation_actions.txt:27` (`redeem_obligation` clears it with `setting = no`). The matching triggers are `owes_obligation_to = <country>` and `is_owed_obligation_by = <country>`. The engine's own `redeem_obligation` action is how the recipient cashes the favour in, so the mod adds no redemption path of its own.

The action sets `can_use_obligations = no`. The engine's built-in obligation mechanic lets the *proposer spend a favour the target already owes* to force a deal through; this deal is the mirror of that, and running both at once would let a proposer cash in one favour to buy another.

#### State model — all of it on the resolution container

Nothing is copied onto a country. The resolution container already outlives an annexed proposer, is already archived by `un_resolution_archive` and is already destroyed by its eviction step, so the lobbying record is archived, shown in history and pruned *with* the resolution for free.

| On the resolution container | Meaning |
| --- | --- |
| list `un_res_lobbied` | every member approached, accepted or declined — the one-attempt rule |
| list `un_res_committed_yes` | **pending** commitments; a recipient leaves this list the instant its vote is booked |
| list `un_res_commit_kept` | settled: voted as pledged |
| list `un_res_commit_broken` | settled: did not |
| var `un_res_commit_count` | commitments accepted, ever. Only goes up; this is what the cap reads |
| var `un_res_commit_pending` | unsettled commitments, for the chamber's tally line |

> **Why lists and not one container per commitment.** A per-commitment container would have to be destroyed when its resolution is evicted from `un_resolution_history` — and that eviction is `scope:un_res_evicted = { destroy_container = yes }` (`un_vote_effects.txt`), which destroys the resolution and nothing else. Every commitment would leak unless each were created with `parent = <the resolution>` and that cascade verified in game, which could not be verified without running it. Four lists and two counters on the resolution itself cannot leak by construction and carry everything this POC records. If lobbying ever grows a per-commitment payload (a sum of money, a dated pledge, a counter-offer), a parented container is the right next step.

> **Why the proposer only, and only for "yes".** Opposition lobbying is not as symmetric as it looks: there is no single "opponent" to hold the obligation, no obvious holder of the cap, and no proposer-shaped seat in the chamber for a second lobbyist. There is therefore no `un_res_committed_no` list. If opponent lobbying is added, it gets its own mirrored lists and its own cap.

`un_res_commit_pending` is a variable rather than a list size because localization can print a variable (`[THIS.Var('un_res_commit_pending').GetValue|0]`) and cannot print a list size.

#### Limits

- **One attempt per (resolution, recipient)**, accepted *or* declined — both branches call `un_lobby_record_attempt`. A request the recipient never answers records nothing and may be made again; no effect of ours runs on an expiry.
- **Cap**: `un_lobby_commitment_cap = 2` accepted commitments per resolution (`un_script_values.txt`). `un_res_commit_count` only ever rises, so a slot cannot be recycled by lobbying somebody who then votes early.
- **Cannot lobby** the resolution's target, a member that has already voted either way, a non-member, a decentralized country, yourself (the proposer is already in `un_res_yes`, so `un_lobby_has_voted` excludes it), or a member we already owe an obligation to.
- **Only while the resolution is `un_res_voting`**, and **only the proposer** (`var:un_res_proposer ?= ROOT`).
- **A permanent member's veto right is never bound.** The veto option's own trigger is untouched — a committed P5 may always veto. But a veto books a **no** vote (`un_resolution_record_veto`), so it settles the commitment as **broken**: a member that pledged its yes and then killed the resolution outright has defeated the entire purpose of the pledge. The AI is leaned away from it (`add = -100` on the veto `ai_chance`); a human is told the cost in the option tooltip.

#### The 30-day window

`un_vote.1` reaches every other member 30 days after a resolution opens, and an AI answers it on arrival. **An AI recipient can therefore only be lobbied inside those first 30 days.** A human recipient can be lobbied right up until it answers its own popup. This is a property of the existing vote timeline, not something lobbying changes, and it is stated in the action's own description so the player is not left guessing.

#### AI acceptance — six factors, each a line in the tooltip

`ai.accept_score`, where **ROOT is the recipient** and **`scope:actor` is the lobbyist** (`diplomatic_action.md`: "the AI country is always root"). Positive means accept.

| Factor | Value | `desc` key |
| --- | --- | --- |
| Pledging a vote away in advance | −20 | `UN_LOBBY_ACCEPT_BASE` |
| The obligation offered | +40 | `UN_LOBBY_ACCEPT_OBLIGATION` |
| Relations with the lobbyist | −30 / +10 / +25 / +40 by threshold | `UN_LOBBY_ACCEPT_RELATIONS` |
| Rivalry with the lobbyist | −60 | `UN_LOBBY_ACCEPT_RIVALRY` |
| Ties to the resolution's **target** — ally / same bloc / rival | −60 / −30 / +25 | `UN_LOBBY_ACCEPT_TARGET_*` |
| The lobbyist's standing tier | +15 / +8 / −8 / −15 | `UN_LOBBY_ACCEPT_STANDING` |

The three target-tie tests are written from the *target's* side with `ROOT` as the other end (`var:un_res_target ?= { has_treaty_alliance_with = { TARGET = ROOT } }`) because all three relationships are symmetric, and that avoids chaining a scope through a container variable inside a script value.

**AI lobbyists** use the same rules — there is no `is_ai` branch anywhere in the feature. They simply reach for it rarely: `evaluation_chance` 0.05 and only while they are themselves the proposer of an open resolution; `will_propose` adds "not a rivalry, diplomatically relevant, relations at least cordial"; `propose_score` 10.

Not used, because it is not cheaply knowable: **the recipient's existing lean on the topic**. The per-topic reasoning lives in `un_vote.1`'s `ai_chance` blocks, which are event option weights and cannot be read from a diplomatic action.

#### Honouring the vote

In `un_vote.1`, a committed AI is pushed to its pledged side by **literal adds** in the marked `ai_chance` spot, keyed on `un_lobby_holds_pending_commitment` — option A **+150** against a base of 40 (the largest other term in that block is ±30), option B **−100**, the veto option **−100**. It is a weight, not a bypass: the AI still runs the event, and no option is ever removed. A human recipient keeps a completely free choice, and both option tooltips say what it costs: `UN_VOTE_COMMITMENT_KEEP_TT` on A, `UN_VOTE_COMMITMENT_BREAK_TT` on B and on the veto. Those `custom_tooltip`s sit **outside** the `custom_tooltip = { text = … }` wrapper around the vote-recording call, because that wrapper replaces the recorded effects' own tooltip with one line.

#### The single settlement site, and why it cannot pay twice

`un_lobby_settle_commitment` (`common/scripted_effects/un_lobby_effects.txt`) is called from `un_resolution_record_vote` and `un_resolution_record_veto` — between them the only two places in the mod that ever book a vote onto a resolution — immediately after the vote goes onto its list and **inside the same `has_tag = un_res_voting` guard**, so a ballot cast after the vote closed settles nothing.

The no-double-settlement argument is one sentence: everything the effect does is inside a single `if` whose condition is *"the voter is on the pending list `un_res_committed_yes`"*, and the **first statement inside that `if` removes the voter from that list**. Any re-entry on any path — a second call in the same option, a queued `un_vote.1` answered twice, a veto followed by a vote — finds the condition false and does nothing. A voter that never pledged falls straight through. Which way they voted is read back off `un_res_yes`, which the caller wrote one line earlier; reading a variable back inside the same effect block is the established shape here (`un_standing_clamp` reads `var:un_standing` immediately after `un_standing_gain`'s `change_variable`) — it is only `add_modifier` / `remove_modifier` whose results are deferred.

A commitment still pending when the resolution is decided, lapses, or loses its recipient is **never settled**: no site fires, nothing is paid either way, and the chamber shows it as still pledged. That is the "void, no penalty" case, and it costs no extra code because there is no extra site. The obligation the lobbyist already handed over stands in that case — the recipient did nothing wrong, and the favour bought a pledge that circumstances, not bad faith, made moot.

#### Consequences

Every figure is defined once in `common/script_values/un_standing_values.txt`, next to the rest of the standing scale (complying with a binding resolution +2, defiance −5, a violated mandate −12).

| | Recipient's standing | Relations with the lobbyist | The obligation |
| --- | --- | --- | --- |
| **Honoured** | `un_standing_commitment_kept_gain` = **+1** nominal, reason code **30** | `un_standing_commitment_kept_relations` = **+10** | stands; redeemed through vanilla's `redeem_obligation` whenever the recipient likes |
| **Broken** | `un_standing_commitment_broken_loss` = **−4**, reason code **31** | `un_standing_commitment_broken_relations` = **−20** | struck off (`setting = no`) |
| **Void** | nothing | nothing | stands |

Deliberately modest. Four points is under the defiance loss and a third of a broken mandate: going back on a bilateral pledge is bad faith, not a violation of a binding decision of the Assembly. It is **not** a serious violation and carries **no** `un_standing_suspend`. The gain runs through `un_standing_gain`, so diminishing returns apply inside the helper — a pledge delivered by an already-Exemplary member is worth almost nothing, which is exactly the point: you cannot farm standing by promising votes you were going to cast anyway. **Neither figure draws on the programme yearly cap** — nothing outside `un_standing_program_award` does.

`setting = no` on an obligation the recipient has already redeemed is a harmless no-op, which is the behaviour we want: a favour already called in cannot be un-called.

#### Display

The chamber's ballot block (`un_chamber_ballot_lines`, called by both `un_chamber_active_voters_sgui` and `un_chamber_history_details_sgui`, so it covers the resolution in session *and* the archive's voting details) gained `un_chamber_commitment_lines`: a **Commitments** sub-list, headed "undertakings, not votes", printing pending / delivered / broken as three disjoint groups with the same guarded flag-and-name accessor the ballot uses. The whole block is hidden unless a commitment was ever made on that resolution, which is also what keeps it invisible on every resolution in a pre-feature save.

`un_chamber_tally_line` gained one conditional line naming how many further members have pledged but not yet voted. **`un_chamber_projection_line` is untouched** — it still evaluates the real passage rule (`un_res_margin` / `un_vote_expulsion_passed`) on votes actually cast, and commitments are never counted as votes. A second "if all commitments hold" projection line was considered and **not** built: the requirement made it optional, and there is no way to express it without restating the passage rule in a second script value, which is precisely the drift the existing comment on that effect warns about.

#### Save compatibility

Nothing assumes any lobbying list or counter exists. Every read is guarded by `has_variable_list` / `has_variable` in `common/scripted_triggers/un_lobby_triggers.txt`, so a resolution already in session when the mod updated simply has no lobbying state: the Commitments block stays hidden, the tally line prints as before, `un_lobby_holds_pending_commitment` is false for everyone, and the settlement call is a no-op. Nothing was renamed and no existing variable, list, effect or trigger changed meaning; the only additions to existing files are the two settlement calls, three conditional option tooltips, three `ai_chance` modifier blocks and the display lines.

#### Known limitations

- **A late acceptance binds the current resolution.** `un_lobby_accept_commitment` reads `global_var:un_active_resolution` at answer time, because the engine does not re-run `possible` when a human finally answers a standing request. If the same proposer opens a *second* resolution while an unanswered request from the first is still outstanding, a late yes commits the recipient to the new one. It needs a request to outlive a full twelve-month vote plus the gap to the next proposal, and the deal struck is still a real one — open resolution, honest lists, obligation paid — just not the one the recipient was asked about.
- **Every precondition is therefore re-checked inside the accept path** against the live resolution, and the commitment and the obligation are created in the same `if`, so the recipient can never be committed without the lobbyist paying, nor the lobbyist pay for a commitment that was not recorded.
- **The obligation cancelled on a broken pledge is assumed to be ours.** Lobbying refuses to start if we already owe the recipient one, so the obligation in force at settlement is the one we granted — unless some third source granted another in the meantime, in which case the cancellation strikes that one off instead.

#### Not yet built (mapped to the original scope)

| In the original brief | Status |
| --- | --- |
| Diplomatic outreach / public endorsements / funded aid pledges as separate approaches | **Not built.** One action, one currency: an obligation. |
| "Expressed support" as a third category beside commitments and cast votes | **Not built.** The chamber distinguishes two: commitments and votes cast. |
| Lobbying for a **no** vote by a resolution's opponents | **Not built.** See "why the proposer only" above. |
| Counter-lobbying, coalitions | **Not built.** |
| A reasons display beyond the acceptance tooltip | **Not built.** The itemised `accept_score` is the whole of it — six factors, and it is the same list the AI decides on. |
| The recipient's existing lean on the topic as an acceptance factor | **Not built.** Not cheaply knowable from a diplomatic action. |
| Money or a dated pledge attached to a commitment | **Not built.** Would be the trigger to move commitments to parented containers. |
| An "if all commitments hold" projection line | **Not built,** by choice — it cannot be written without restating the passage rule. |

### Vote System (3-phase)
1. **un_vote.1** (Phase 1): Fires to all other UN members 30 days after opening. Each country votes yes/no (permanent members may veto binding topics) with topic-adaptive titles, descriptions, and AI logic. Votes are recorded on the resolution; a vote cast after it closed is ignored.
2. **un_vote.2** (Phase 2): Fires to the proposer 365 days after opening. The immediate closes the vote; the option shows vote counts and applies resolution effects (agency creation, received benefits, authority changes), then notifies the other members.
3. **un_vote.3** (Phase 3): Notification fired to all other members showing the vote result (pass/fail with vote counts). Members who voted no on a passed resolution choose to comply or refuse.

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
- War support (1.14): `un_condemned_modifier` −0.5 / `un_non_binding_rebuke_modifier` −0.25 per beat on the holder, +0.25 for fighting a condemned enemy — `common/script_values/zz_te_war_support_injections.txt` (see `mod_systems.md` § War Support Feeds)
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
- War support (1.14): an enemy with `nuclear_power` costs a non-nuclear country −0.25 per beat — `common/script_values/zz_te_war_support_injections.txt` (see `mod_systems.md` § War Support Feeds)

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
- **War support (1.14):** the two strain modifiers are read from the JE (`je:je_world_war ?= { has_modifier = … }`) by `common/script_values/zz_te_war_support_injections.txt` for −0.5 per beat each (see `mod_systems.md` § War Support Feeds)

### Events
- **Leadup:** `world_war_events.1` (confrontation), `.2` (border incident), `.3` (crisis)
- **Outbreak:** `world_war_events.5` (war breaks out)
- **Active war:** `.10` (rally), `.11` (bombing), `.12` (resistance), `.20` (join opportunity)
- **Prolonged:** `.30` (weariness), `.31` (stalemate on the front — 1.14 war reads `war_duration_months`, `num_significant_battles`, `has_stalled_wargoal_held_by`; one-off `add_war_war_support` ±)
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
