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
