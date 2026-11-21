# Nuclear Delivery and Survivability, Phase 2 (Delivery Projects) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship spec phase 2: ICBMs and missile submarines become hardware a programme builds, not something a technology switches on.
- After the first device, the programme's funding builds whatever its **focus** names: Warheads, ICBMs or Missile Submarines.
- Each project keeps its progress while another is in focus.
- The two delivery triggers read the fielded legs.
- An arms-control ceiling binds warheads only.
- The AI builds range when the countries it must deter are out of bomber reach.
- Every figure a focus choice rests on is shown where it is made.
- Others' fielded legs are public.

(§4, §5.3's Programme focus row, §5.4's Programme, Nuclear Powers and National Info changes, §8, owner calls 1–5, 9, 11 and 12.)

**Architecture:**
- **A focus and three parked slots.**
  - `nd_prog_focus` (2 ICBMs, 3 submarines) is unset for Warheads.
  - The native bar keeps reading `nuclear_weapon_program_progress`, the progress of what is in focus.
  - What isn't in focus waits in `nd_proj_warhead_progress`, `nd_proj_icbm_progress` or `nd_proj_sub_progress`.
  - One effect parks and loads (`nd_focus_set`). The entry's `immediate` parks before it zeroes, and the weekly pulse loads back.
- **A project is the first device's rate toward 100.** At 100 the leg is fielded (`nd_icbms_fielded` / `nd_subs_fielded`, country variables) and the focus returns to Warheads.
- **The two triggers change body only.** `nd_fields_icbms` and `nd_fields_missile_submarines`, introduced in phase 1, read the fielded variables. A bridge reads the technologies until a one-time migration has run, so no country loses a leg in between. Nothing that reads the triggers changes: reach, the factors, the authorities, the incidents and `nd_icbm_force`.
- **Holds:**
  - An arsenal ceiling, our own, a treaty's or the UN ban's, holds only a Warheads focus, and so does the AI's stockpile cap.
  - Everything else that holds the programme holds a project too: freezes, disarmament, dismantling and lost standing.
- **The AI chooses its focus in its posture review** from a range score. Its funding buttons stop treating "at the desired stockpile" as a reason to defund while a project is in focus.
- **Display:**
  - Focus rows in The Programme, with what each grants in figures.
  - A delivery column in Nuclear Powers, and a delivery cell in another country's National Info.
  - Figures the GUI can't afford every frame (reach counts) are stored weekly.

**Tech Stack:** Victoria 3 script, GUI and localization; Python 3.11/3.12 tests.

**Spec:** `docs/superpowers/specs/2026-11-20-nuclear-delivery-and-survivability-design.md`: §4, §5.3–§5.4, §7, §8, and §9 phase 2. It builds on phase 1 (`plans/2026-11-20-nuclear-delivery-phase1.md`, `nuclear_crisis_design.md` §0.18), which introduced the triggers, `nd_icbm_force`, the world's view and the Forces, Posture and Strike figures.

## Global Constraints

- **Two PRs, both `--base main`** (D1). 2a is Tasks 1–5 (the projects); 2b is Tasks 6–7 (what the panel tells). If phase 1's PR 1b hasn't merged when 2a opens, 2a stacks on 1b's tip and is retargeted after it merges (`docs/guides/git_workflow.md`, stacked PRs). A session whose harness assigns its own branch uses that.
- **Engine facts relied on, all probed:**
  - `immediate` runs on every activation, and the bar's goal is fixed then, at `current_value + goal_add_value` (`scripting_best_practices.md` § "`immediate` runs again on every activation").
  - A revolution's rebel starts with no mod variables. The winner merges the loser's variables, keeping its own wherever both hold one, and no modifiers or lists (§ "What a Civil War's Winner Inherits").
  - `add_modifier` / `remove_modifier` aren't visible inside the same effect block, so `nd_taboo_refresh_held` is called at most once a block.
  - A tooltip walk writes nothing, so every handler body that sets and then reads goes behind a click-only marker (`nd_plan_click`'s pattern, `nd_plan_step_enemy`).
  - A declared modifier reaches a `modifier:` read 2–5 days late, and `has_modifier` can't see it.
  - The GUI can't take a scope from a variable (`gui_modding_guide.md` gotchas #11 and #15): rows read countries through stored capitals.
  - `any_*` triggers take no `limit`.
  - A `has_variable` guard never shares a `NOT` with its read; use `?=`.
  - `post_notification` from a global-scope `every_country` reaches each human (`headlines_tech_announce_effect`).
  - Script values sum over `every_country` (`colonial_empire_values.txt`).
- **No new unprobed engine fact.** The one open from phase 1 is `TE_SELF_CHECK nd_icbm_force_sum`; its fallback switch (`nd_icbm_force_declared_reads`) is unchanged by this phase, since both branches read `nd_fields_icbms`. If the play-test reads BROKEN before 2a merges, flip the switch in 2a.
- **Conventions:**
  - Op tables stay in step in three places: the `.gui` header, the sgui header and `journal_entry_systems.md`. The last is CRLF: edit it with `Edit` and confirm with `grep -c $'\r$'`.
  - Numbers live in script values; nothing is restated in `.gui` or loc.
  - A figure in a hover is a numeric display modifier or a script value, never words in a boolean's name.
  - Loc is American English, written through the `event-text` skill (the `add-event` skill for the two notices). Run `organize_loc.py` after adding keys.
  - The audits that apply: `je_immediate_reset_audit`, `tooltip_walk_variable_audit`, `silent_variable_audit`, `variable_guard_audit`, `modifier_field_audit`, `loc_coverage_audit`, `long_tooltip_audit`, `event_image_audit`, `button_reason_audit`, `script_argument_audit` and `trigger_event_cycle_audit`.
  - Each task runs its tests, then `scripts/preflight.py --changed`. Each PR runs the full `scripts/preflight.py` before it opens.
  - The player guide matches the script at its peers' depth, and the PDF is rebuilt in the same commit.

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| D1 | Two PRs. **2a, the projects** (Tasks 1–5): the focus and parking, the legs on the fielded variables with the migration and the removals, a Focus control, the notices, the AI, and the docs. **2b, what the panel tells** (Tasks 6–7): each focus row's grants in figures, the Powers column, the National Info cell, the Help topic and their docs | 2a changes play: delivery stops coming with research. So it must ship a working control for a human (the rows with progress, months and the greyed reason), or a player could never field a leg. 2b only adds information, and is reviewable on its own |
| D2 | `nd_prog_focus`: 2 ICBMs, 3 Missile Submarines, **unset for Warheads**. Triggers `nd_focus_is_warheads` (`NOT = { has_variable = nd_prog_focus }`), `nd_focus_is_icbms` (`var:nd_prog_focus ?= 2`) and `nd_focus_is_submarines` (`?= 3`). The op numbers 1–3 equal the codes | Unset-for-Warheads keeps every save and every activation valid with no write in `immediate`. A rebel never holds a focus (it starts with no variables and no first device), so a winning revolution takes the loser's focus in the merge |
| D3 | **Parking.** `nd_focus_set = { F = 1\|2\|3 }` parks live progress over 0 in the slot of the focus in force, loads the new focus's slot into live progress (else 0) and removes that slot, then sets or removes `nd_prog_focus` and calls `nd_taboo_refresh_held` once. **`immediate`** runs `nd_focus_park_live` before its zeroing: it parks into the focus's own slot, writes behind `has_variable` and `> 0`, and carries a `# REVIEWED` comment. **The weekly pulse** runs `nd_focus_restore` right after `nd_custody_restore_progress`: if the focus's own slot exists, live = the greater of the two, and the slot goes. **Invariant:** the focus's own slot exists only between an activation and the next weekly pulse, so a restore is never ambiguous | Spec §4.1. A re-activation (rank lost and regained) no longer throws away progress toward the next warhead, as it does today: that matches "avoid micromanagement". Raising only, never lowering, makes the custody carry and the restore agree whichever arrives first |
| D4 | **Rate.** `nuclear_weapon_program_monthly_progress`'s ×10 applies only with `nd_focus_is_warheads`, so a project runs at the first device's rate. `nuclear_program_weekly_progress`'s warhead loop gains `nd_focus_is_warheads = yes`. A new branch: a project in focus at ≥ 100 calls `nd_field_leg = { LEG = icbms\|subs }`. That effect sets the variable (value = `year`, for the panel), then sets focus Warheads with the warhead slot loaded, which drops the week's overflow. It refreshes the hold (once), the reach (`nd_reach_refresh`), the upkeep cache (`nd_apply_posture_modifiers`) and the main rival's figures (`nd_refresh_main_rival`), then sends the notices (D12). The progress multipliers apply unchanged | §4.1: 20 months at 5 steps. Program aid, sabotage, inspections and The Bomb Has Been Used already multiply the shared weekly step |
| D5 | **Holds.** `nd_taboo_programme_should_be_held`'s ceiling half (not its dismantling half) and `nuclear_program_ai_at_stockpile_cap` gain `nd_focus_is_warheads = yes`. Those two are every ceiling's hold: our own, Nuclear Arms Limitation's and the UN ban's, through `nd_taboo_effective_ceiling_value`. A freeze article, a crisis freeze, the disarmament bool and lost standing hold a project as they hold warheads, through the pause bool, the disarmament branch and `nuclear_program_has_programme`. `nd_taboo_held_by_own_ceiling_only` is unchanged, since it is true only while the hold is on | §4.1: arms control binds warheads, not delivery. The hold is a modifier carrying the pause bool, which zeroes funding weekly, so it must come off the moment a project is in focus (`nd_focus_set`) and go back on at completion (`nd_field_leg`) |
| D6 | **Availability.** Two triggers, each requirement in its own `custom_tooltip` so a greyed row prints what is missing (`button_reason_audit`). **`nd_proj_icbms_available`:** `nuclear_program_has_programme`, the first device done, the `ICBMs` technology, `nd_icbms_fielded` unset. **`nd_proj_subs_available`:** the same, plus `advanced_submarine_technology`, `guided_missiles`, a coastal state and `nd_subs_fielded` unset. Both join D3's allowlist in `test_nuclear_delivery.py`: a project's prerequisite is knowledge. The weekly pulse returns a focus whose project is no longer available (a lost coast) to Warheads through `nd_focus_set`, which keeps its progress | §4.2, §4.3. A held project is still available: the hold is a pause, not a reason to switch |
| D7 | **The trigger swap, with a bridge.** `nd_fields_icbms = { OR = { has_variable = nd_icbms_fielded  AND = { NOT = { has_global_variable = nd_delivery_migrated }  has_technology_researched = ICBMs } } }`. `nd_fields_missile_submarines` has the same shape with `nd_subs_fielded`, and its `any_scope_state = { is_coastal = yes }` stays outside the `OR`. Both keep their `custom_tooltip`, whose text now says "fielded". The two bridge reads join the allowlist with their reason. The `nd_tt_fields_*` loc is rewritten to name the fielded leg | Until the first monthly pulse after the update, a save's ICBM powers would otherwise lose reach, Launch on Warning (the D10 bind would then demote them) and the force. The bridge closes that gap and reads false for good once the flag is set |
| D8 | **Migration** `nd_delivery_migrate`. It runs from a new on_action on the global `on_monthly_pulse` (in `nuclear_taboo_on_actions.txt`'s style, rule-gated), once, under `nd_delivery_migrated`. It gives `nd_icbms_fielded` to every country with `ICBMs`, and `nd_subs_fielded` to every country with `advanced_submarine_technology` and a coast, armed or not (§4.4). If any leg was migrated, it sets the two headline flags (D12), since the world already had the leg. It logs `TE_NUCLEAR: type=delivery_migrated; icbms=N; subs=M`. No self-check: no engine fact here is unverified. The phase 1 self-check is unaffected (it waits on `nd_fields_icbms`, true on both sides of the migration) | §4.4. A log line lets the play-test confirm the count without a probe |
| D9 | **Submarine upkeep.** `nd_upkeep_units_submarines` = `nd_upkeep_size_factor × 6` while `nd_fields_missile_submarines`, added in `nd_upkeep_units_fixed`. That is the readiness-independent part, so every per-level preview includes it. The clamp in `nd_upkeep_units` rises from 40 to **46**, and the header's unit table gains a row | §4.3, owner call 11. The old cap was exactly the sum of the parts (10 + 12 + 6 + 9 + 3), so at the dearest posture a leg below the cap would cost nothing |
| D10 | **Removal and the authority bind.** `nd_delivery_remove_legs` removes both fielded variables, the parked project slots and an ICBMs/submarines focus. It is called from the Nuclear Disarmament article's `on_entry_into_force` and from `nd_taboo_dismantle_complete`. **`nd_authority_bind_check`** is the single writer: under Launch on Warning without `nd_can_adopt_launch_on_warning`, or Automatic Retaliation without `nd_can_adopt_automatic_retaliation`, it calls `nd_set_authority_1` and puts `nd_authority_months` back as it was (tenure satisfied if missing). A human is told through a new message, `nd_authority_bound_by_delivery`, as `nd_doctrine_bound_by_law` does. It is called by the removal and weekly from `nd_weekly_update`, as a backstop | §4.4, owner call 9. A renounced programme starts over, launchers and projects alike. The No-First-Strike binding is the house pattern: the government didn't choose the change, so its clock isn't restarted |
| D11 | **The Focus rows** (2a's control). They sit in `te_nuclear_sec_programme` under the funding rows, shown from the first device on: three `nd_choice_row`s, the focus in force tinted. Each row prints its progress and its months to finish at current funding, from `nd_display_proj_progress_*` and `nd_display_proj_months_*`. A greyed row prints its requirements through `nuclear_program_focus_sgui`'s `is_valid`. The handler has ops 1 Warheads, 2 ICBMs and 3 Missile Submarines, `ai_is_valid = { always = no }`, and a body behind a click-only marker. The programme's rate and time rows and the native bar's label follow the focus. `nuclear_program_refresh_state_effect` gains status codes for a project in focus (the developing icon). The ceiling stepper's hover now says a ceiling holds warheads only, not a project (phase 1 Task 6 deferred this here) | Spec §5.4. The grants in figures are 2b's (D16); a player in 2a can already see what each choice is, what it costs in time and what blocks it |
| D12 | **The notices.** Two events, `nuclear_weapon_events.35` (ICBMs fielded) and `.36` (missile submarines), each with one option.<br>• **Recipients:** sent from `nd_field_leg` to the fielder at once and, 7 days later, to its rivals in either direction, the countries believed armed and its neighbors.<br>• **Variants:** a `first_valid` gives the fielder's own text and a world-first text.<br>• **The headline:** the first fielder in the world also posts a headline to every human, through new types `headlines_nd_icbms_fielded` and `headlines_nd_subs_fielded` in `extra_messages.txt` and global flags `nd_headline_*_fielded`.<br>• **Images:** `missile_parade.dds` for ICBMs, and an existing naval or launch picture for submarines, chosen with the event-images inventory (`event_creation_guide.md`).<br>• **The taboo:** neither event writes to the taboo's ledger | §4.1: fielding is public, deployment isn't use. The technologies' own headlines stay (§4.2) |
| D13 | **Custody and revolutions need no new code.** A test checks that nothing in `nuclear_custody_*`, `te_civil_war_*` or the custody events writes `nd_icbms_fielded`, `nd_subs_fielded`, `nd_prog_focus` or `nd_proj_*` (owner call 3: warheads arrive without delivery). The ledger keeps recording live progress only: the loser's focus and slots arrive in the merge (D2), and the carry restores the live figure (D3) | §4.4: the winner continues the nation; a rebel and an annexer have their own legs or none |
| D14 | **The AI's range score**, computed in `nd_ai_choose_focus` (called from `nd_ai_review_posture`) with local variables over `every_country`.<br>• **Weights, the highest that applies, one per country:** 3 for a rival in either direction, a war enemy or the crisis opponent; 2 for a country that is antagonistic toward us (`has_attitude`) and believed armed.<br>• **The score:** the weighted share of those countries that `nd_reaches_country` misses, 0 when there are none. It is stored as `nd_ai_range_score` for the log.<br>• **Range** means submarines when `nd_proj_subs_available` holds and every out-of-reach country that matters has a coast, else ICBMs.<br>• **The order** is §4.5's six steps and its tie rule, verbatim. Each review logs `TE_NUCLEAR: type=ai_focus; score=…; focus=…; reason=…`. The log-triage registry gets the new type if it lists `TE_NUCLEAR` types | §4.5, owner call 12. `nd_reaches_country` already counts the legs fielded, so a power with submarines stops scoring coastal enemies as out of reach |
| D15 | **Funding `ai_chance`.** The increase button gains +35 while a project is in focus. **Departure from the spec:** besides the decrease button's two stockpile terms (+35 at, +15 above), the increase button's −45 at the desired stockpile also doesn't count while a project is in focus. The taboo's restraint factor still applies. The AI cap's ×0 no longer bites while a project is in focus (D5) | Without the −45 change an AI at its desired stockpile nets −10 and never funds a project: the failure §4.5's last paragraph warns of |
| D16 | **What a focus grants** (2b). Never-added display modifiers `nd_focus_terms_icbms` and `nd_focus_terms_submarines`:<br>• `country_nd_exposure_mult` (−30% / −50%: the factor, as "share exposed to a first strike");<br>• booleans for rules with no quantity: `country_nd_reach_every_state_bool`, `country_nd_reach_every_coast_bool`, and `country_nd_unlocks_launch_on_warning_bool` / `_automatic_retaliation_bool` for ICBMs.<br>The ICBM row also prints `[GetStaticModifier('nd_icbm_force').GetDesc]`. Each hover then gives the survivability target now and with the leg (`nd_survivability_target_with_icbms` / `_with_submarines`), the countries in reach now and with it, and the warheads the months in focus won't build (`nd_proj_forgone_warheads_*` = months to finish × warheads a month at current funding). **Departure from §5.4:** the submarine leg's upkeep prints as its weekly money (`nd_display_upkeep_submarines_weekly`, from `nd_upkeep_units_submarines`), not as a `country_nd_upkeep_units_add` line. A test holds each display figure to its script value | A unit of 1/100,000 of GDP is no figure the player reads anywhere else; the upkeep breakdown shows money. Owner call 10's lesson applies: a figure is a numeric field or a script value, never words in a name |
| D17 | **Reach counts are stored** by `nd_reach_refresh`, weekly and at fielding: `nd_reach_count` (countries `nd_reaches_country` reaches now), `nd_reach_count_with_subs` (now, plus every country with a coast) and, for ICBMs, the count of every country. Shown only on our own panel | Counting every country through `nd_reaches_country` each frame of a hover is too heavy. The weekly rebuild already walks the list |
| D18 | **Privacy.** The focus and project progress are private: `TRUE_VARS` gains `nd_prog_focus` and `nd_proj_\w+`. The fielded legs are public (§2), read through `nd_display_leg_icbms` / `_subs`, which read only the variables and the coast. `PrivateTest` and `ObserverTest` cover the new cells | What a programme is developing isn't public until it tests; a fielded leg is |
| D19 | **The Nuclear Powers column and the National Info cell** use the technologies' existing icons (`gfx/interface/icons/invention_icons/bombing_aircraft.dds`, `ICBMs.dds`, `advanced_submarine_technology.dds`), shown per leg the row's country fields, with bombers for every armed country. Rows read the country through the capital (`State.GetOwner`), as the authority icons phase 1 added beside the doctrine do. The National Info Row 3 for another country (phase 1, D17) gains the delivery cell | No new art. Every listed country is armed, so bombers always show |

---

## PR 2a: the projects

### Task 1: The focus, parked progress and completion (§4.1; D2–D6)

**Files:**
- `common/scripted_triggers/nuke_triggers.txt`: the focus triggers, `nd_proj_*_available` and `nuclear_program_ai_at_stockpile_cap`;
- `common/scripted_triggers/nuclear_taboo_triggers.txt`: `nd_taboo_programme_should_be_held`;
- `common/script_values/extra_script_values.txt`: `nuclear_weapon_program_monthly_progress`;
- `common/scripted_effects/nuclear_weapon_effects.txt`: `nuclear_program_weekly_progress`, plus `nd_focus_set`, `nd_focus_park_live`, `nd_focus_restore`, `nd_focus_check_available` and `nd_field_leg`, the last setting the variable but sending no notices yet;
- `common/journal_entries/je_nuclear_program.txt`: the park in `immediate`; the restore and the availability check in the weekly pulse;
- `common/scripted_guis/nuclear_program_sguis.txt`: `nuclear_program_focus_sgui` and the header's op table;
- loc: `nd_tt_focus_set_*` and the `nd_tt_proj_*` requirement lines;
- `test_nuclear_projects.py` (new).

**Interfaces:** produces `nd_prog_focus`, `nd_proj_*_progress`, `nd_icbms_fielded` / `nd_subs_fielded` (written, not yet read by the triggers), `nd_focus_set`, `nd_field_leg` and the availability triggers.

- [x] Write `test_nuclear_projects.py`:
  - `TestFocus`: the three triggers and unset-for-Warheads; no `immediate` writes `nd_prog_focus`.
  - `TestParking`:
    - `nd_focus_set` parks over 0, loads and removes the slot, then refreshes the hold once.
    - `immediate`'s park runs before the zeroing, with its `# REVIEWED` comment.
    - The restore runs after `nd_custody_restore_progress` and raises only.
    - Parking covers all three foci.
  - `TestProjectRate`: ×10 only on Warheads; 20 months at 5 steps.
  - `TestCompletion`:
    - the loop's focus gate;
    - ≥ 100 calls `nd_field_leg`;
    - the leg's variable is set, the focus returns to Warheads with the slot loaded and the overflow dropped;
    - the hold, reach, upkeep and main-rival refreshes each run once.
  - `TestHolds`: the ceiling half and the AI cap read the focus. The dismantling half, the pause bool's sources and the disarmament branch don't.
  - `TestAvailability`: each requirement has its own `custom_tooltip`; an unavailable focus returns to Warheads weekly.
  - `TestFocusHandler`: ops 1–3, `ai_is_valid = { always = no }`, the click-only marker, and `is_valid` per op reading availability.

  Run: FAIL.
- [x] Implement. Then run `je_immediate_reset_audit`, `tooltip_walk_variable_audit`, `silent_variable_audit` and `variable_guard_audit`; the nuclear tests; and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear programme: a focus, with each project's progress parked (spec §4.1)`.

**As built (2026-11-21).** As planned, with three additions:
- **Helpers.** `nd_focus_park_into` and `nd_focus_restore_slot` do the slot arithmetic for every focus. Each ops-1–3 click goes through `nd_focus_choose`, behind the click-only marker `nd_focus_click`.
- **A log line.** `nd_field_leg` logs `TE_NUCLEAR: type=leg_fielded; leg=icbms|subs`, so a play-test can see each fielding.
- **Reused key.** The "has a programme" requirement line reuses `nuclear_program_tt_has_programme`.

Left for later tasks:
- **Task 3: the status code.** The click doesn't call `nuclear_program_refresh_state_effect`. Status codes for a project are D11's, and the hold coming off isn't visible in the click's own block anyway. So until the next weekly pulse, a held programme that switches to a project still shows the held status.
- **Task 2: stale slots.** A slot a fielded leg left behind lingers. Say a country has the ICBM project in focus when the migration grants `nd_icbms_fielded`: the weekly availability check returns the focus to Warheads and parks the ICBM progress. The migration and `nd_delivery_remove_legs` should remove the slots of the legs they set or take.

### Task 2: The legs follow the fielded variables (§4.2–§4.4; D7–D10, D13)

**Files:**
- `common/scripted_triggers/nuclear_deterrence_triggers.txt`: `nd_fields_*` with the bridge;
- a new on_action beside `nd_taboo_monthly_on_action` (`common/on_actions/nuclear_taboo_on_actions.txt`, or a new `nuclear_delivery_on_actions.txt`);
- `common/scripted_effects/nuclear_deterrence_effects.txt`: `nd_delivery_migrate`, `nd_delivery_remove_legs`, `nd_authority_bind_check`, and the weekly call in `nd_weekly_update`;
- `common/treaty_articles/extra_treaty_articles.txt`: `nuclear_disarmament`'s `on_entry_into_force`;
- `common/scripted_effects/nuclear_taboo_effects.txt`: `nd_taboo_dismantle_complete`;
- `common/script_values/nuclear_deterrence_values.txt`: `nd_upkeep_units_submarines`, `_fixed`, the clamp, and the unit table;
- the upkeep breakdown's loc line;
- `common/messages/extra_messages.txt` and its loc: `nd_authority_bound_by_delivery`;
- the loc for `nd_tt_fields_*`;
- `scripts/analysis/nuclear_incident_rates.py`: the posture's `icbms` and `submarines` now mean the variables, and the interpreter answers the new `has_variable` reads;
- `test_nuclear_delivery.py`: the trigger bodies, and the allowlist updated for the bridge, the availability triggers and the migration;
- `test_nuclear_projects.py`.

**Interfaces:** after this task, a leg exists only once fielded or migrated. Every phase 1 reader follows.

- [x] Write the tests:
  - `TestFieldedTriggers`: the bodies per D7 and the bridge's flag.
  - `TestMigration`: global, monthly, once under the flag; tech and coast; armed or not; the headline flags; the log line.
  - `TestLegRemoval`: both call sites; the variables, slots and focus cleared; the bind called.
  - `TestAuthorityBind`: Central, months put back, a human told, the weekly backstop.
  - `TestCustodyAndRevolutions` (D13).
  - `TestSubmarineUpkeep`: 6 × the size factor, in `_fixed`, the clamp 46 and the unit table.
  - The D3 allowlist: each new site with its reason.

  Run: FAIL.
- [x] Implement, then the nuclear tests, `test_nuclear_reach.py`, `test_nuclear_basing.py`, `test_nuclear_incident_risk.py`, and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear delivery: legs are fielded, not researched; disarmament takes them (spec §4.2–§4.4)`.

**As built (2026-11-21).** As planned, with these additions:
- **What the migration skips.** It grants no leg to a country that gave its arsenal up and hasn't armed again (`nd_delivery_given_up`: `nd_renounced`, `nd_renounced_locked` or the Nuclear Disarmament article in force). Disarmament takes the launchers (owner call 9), so a country renounced before the update would otherwise get its legs back.
- **The removal and a project focus.** With a project in focus, the live figure is the project's, so the removal loads the warheads' parked progress back to the bar (or 0) as it drops the focus. A warheads slot on a Warheads focus is an activation's park and stays. The disarmament article calls the removal before it zeroes the progress, so the zeroing still clears the warheads.
- **The upkeep cap.** It is a named value, `nd_upkeep_units_cap` (46), at all seven clamps. The ceiling stepper's two previews take the submarines' part at their own size, not the stockpile's.
- **The Upkeep row's hover.** It names the submarines and gives their part while fielded (`nd_upkeep_subs_line`, `nd_display_upkeep_submarines_weekly`). Its cap reads "just under two and a half percent of GDP a year".
- **The interpreter** answers `nd_fields_*` from the posture, as in phase 1, so it needed no `has_variable` answers; only its comments changed.
- **Kept as it was:** the bind's fallback logs as an ordinary `nd_set_authority_1` action line. The disarmament article's `te_nuclear_disarmament_ended_program` still counts only warheads and progress, not legs.

### Task 3: The Focus rows, the notices and the headline (§4.1, §5.4 Programme; D11, D12)

**Files:**
- `gui/journal_entry_widgets/nuclear_program_widget.gui`: the Focus subsection in `te_nuclear_sec_programme`, and the header's op table;
- `docs/systems/journal_entry_systems.md` (CRLF): the op table and the Programme area;
- `common/script_values/extra_script_values.txt`: `nd_display_proj_progress_*` and `_months_*`. The rate and time values follow the focus;
- `common/scripted_effects/nuclear_weapon_effects.txt`: the status codes in `nuclear_program_refresh_state_effect`, and the notices in `nd_field_leg`;
- `common/customizable_localization/nuclear_program_custom_loc.txt`: the status phrases and the bar's label;
- `events/nuclear_weapon_events.txt`: `.35` and `.36`, through the `add-event` skill;
- `common/messages/extra_messages.txt`: the two headline types;
- loc, through the `event-text` skill: the rows, the hovers, the events and the headlines. The ceiling stepper's hover gains "a ceiling holds warheads only, not a project";
- the Help page's programme topic (`te_nuclear_weapons_help_body`);
- `test_nuclear_layout.py`, `test_nuclear_projects.py`.

- [x] Write the tests:
  - `TestFocusRows`:
    - three rows behind the first device, the tint on the focus;
    - progress and months per row from the display values;
    - the op tables in three places;
    - the rows fit (`_fits`).
  - `TestProgrammeFollowsFocus`: the rate, time and bar label, and the status codes.
  - `TestNotices`:
    - the recipients and the 7 days;
    - the fielder's and the world-first variants;
    - the headline, once per leg, and its flags shared with the migration;
    - each event has an `event_image`;
    - no ledger write.
  - `TestCeilingSaysWarheadsOnly`.

  Run: FAIL.
- [x] Implement, then the GUI lint, `organize_loc.py`, `event_image_audit`, `button_reason_audit`, the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear programme: choose what funding builds; the world hears when a leg is fielded (spec §4.1, §5.4)`.

**As built (2026-11-21).** As planned, with these choices where the plan left room:
- **The rows' place and words.** The rows sit at the end of The Programme under "What Funding Builds", named Warheads, ICBMs and Submarines. Each row's name is its progress as a share of the goal and its months to finish at current funding (`nd_display_proj_share_*`, `_months_*`). It falls back to "not progressing" when funding is 0 or a pause or disarmament holds the programme (`nuclear_program_display_progressing`), and reads differently in three cases:
  - Warheads not in focus say "held at our ceiling" when our ceiling would hold them;
  - a project whose requirements fail says "not available", and its greyed button lists why;
  - a fielded leg gives its year.
- **Status codes 9 and 10** (the ICBM and submarine projects, on the developing icon). The hold (4), the freeze (3) and dismantling (5) are now each read from what causes it: `nd_taboo_programme_should_be_held`, a new `nuclear_program_is_frozen` (the freeze article, a crisis freeze, the console's pause) and `nd_taboo_is_dismantling`. The hold's modifier and the pause flag aren't read, since a Focus row's click changes the hold in the same block and neither would see it until the next click. The click then refreshes the status code (`nd_focus_choose`), so a held programme that switches to a project shows "unfunded" at once rather than "held".
- **The bar's label** is the entry's new `progress_desc` (`je_nuclear_program_progress`, through the accessor-free `nd_prog_focus_object`).
- **Notices.** `nd_field_leg` dispatches to `nd_leg_notices_icbms` / `_subs` (`nd_leg_notices_$LEG$`). ICBMs show `missile_parade.dds`. Submarines show `missile_launch_crew.dds`, a launch control room, as no submarine picture exists; a pending picture can replace it.

### Task 4: The AI's focus (§4.5; D14, D15)

**Files:**
- `common/scripted_effects/nuclear_deterrence_effects.txt`: `nd_ai_choose_focus`, called from `nd_ai_review_posture`, and the log line;
- `common/scripted_triggers/nuclear_deterrence_triggers.txt`: `nd_ai_range_means_submarines`, and the out-of-reach test;
- `common/scripted_buttons/nuclear_program_buttons.txt`: the `ai_chance` terms;
- the log-triage registry, if it lists `TE_NUCLEAR` types;
- `test_nuclear_projects.py`.

- [x] Write the tests:
  - `TestRangeScore`: the weights, the highest per country, `nd_reaches_country` as reach, and 0 with none.
  - `TestFocusOrder`:
    - §4.5's six steps in order;
    - the tie rule between steps 3 and 4;
    - never range at 0;
    - submarines as range only when every out-of-reach country that matters has a coast;
    - the focus set through `nd_focus_set`.
  - `TestFundingAiChance`: +35 with a project in focus; the three stockpile terms skipped then; the cap's ×0 focus-aware.
  - `TestAiFocusLog`.

  Run: FAIL.
- [x] Implement, then the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear AI: builds range when the bombers reach nobody who matters (spec §4.5)`.

**As built (2026-11-21).** As planned, with these choices where the plan left room:
- **The submarine test sits in the effect**, not in a trigger `nd_ai_range_means_submarines`: it reads the walk's local variables, and a `local_var` read inside a scripted trigger is still unread in game (`scripting_best_practices.md`, the tax code's pending read).
- **Submarines count as range in one more case:** with no ICBM project open (not researched, or fielded) and at least one country that matters out of reach on a coast, the submarine project is the only range on offer. With neither project open, no step picks range.
- **Weight 2 covers belligerent too**, the attitude past antagonistic, as `nd_plausible_attacker_of` does.
- **Step 4's precision test** reads `nd_main_rival_accuracy_mult` (`nd_refresh_main_rival`), which is above 1 only when we field ICBMs and the rival's precision weapons give it silo penetration. The review refreshes the rival before it chooses.
- **Nothing before the first device**, and the focus is set only when it changes; every review logs. The log's `focus` is the op code (1 Warheads, 2 ICBMs, 3 Missile Submarines) and its `reason` one of `range_first`, `range_urgent`, `warheads_short`, `tie_range`, `tie_submarines`, `range_half`, `submarines_survival`, `range_some` and `warheads`.
- **`nuclear_observer_report.py`** counts the choices, the reasons and the legs fielded (`type=leg_fielded`, Task 1). There is no `TE_NUCLEAR` type registry in the log-triage skill to extend.
- **A stale test retired.** `test_nuclear_incident_risk.py`'s ban on any `$` in a `TE_NUCLEAR` record predates 1.15, which substitutes an argument inside a quoted string (the C19 probe). It now bans one only inside a `[...]` accessor, the unprobed case.

### Task 5: Docs, the play-test list; gate, PR 2a

- [x] `nuclear_crisis_design.md`: a new §0.19, "Delivery projects, phase 2a". It covers what shipped and D1–D15, with the spec's §4 as the reference. Update `mod_systems/nuclear.md`: the focus, the projects, the holds, the migration, the AI, and the new variables in its variable inventory.
- [x] Chapter 14 at its peers' depth:
  - "Who can run a weapons program": the ICBM technology now unlocks a project.
  - "Program funding and warhead production": the focus and the projects, a row each in the stage table, and the holds (a ceiling binds warheads only).
  - "Range and Nuclear Basing": reach from fielded legs, and the migration of an existing save in a sentence.
  - "Delivery capability and home defense": the ICBM force follows the fielded leg.
  - "Nuclear deterrent upkeep": the submarine leg.
  - "Launch authority": Launch on Warning and Automatic Retaliation need fielded ICBMs, and fall back to Central when they go.
  - "Arsenals in civil wars and annexations": warheads arrive without delivery.
  - Wherever the Nuclear Disarmament article and dismantling are described: they take the legs.
  - A sentence on the AI's choice of range.
  - Chapter 17's glossary entries for reach and the ICBM force.
  - Rebuild the PDF.
- [x] Play-test list (`docs/testing/nuclear-playtest.md`), §8's phase-2 items:
  - a focus change mid-project;
  - a re-activation with a project in focus;
  - a project finished under a ceiling;
  - an AI great power at its desired stockpile with a distant rival funds and fields ICBMs;
  - a landlocked country after migration;
  - the submarine upkeep against the other costs (owner call 11);
  - an observer game's `type=ai_focus` lines;
  - the `type=delivery_migrated` line in an old save.
- [x] The spec's status line and the `docs/superpowers/README.md` rows.
- [ ] Full `scripts/preflight.py`. Then PR 2a with `--base main`, the two-reviewer review, one fix pass, and merge on green CI. (Review and fix pass done, 2026-11-21: the PR waits for PR 1b to merge, since this session can push only the branch 1b is on.)

**As built: the review's fixes (2026-11-21).** Two reviewers read Tasks 1–4; one fix pass (`Nuclear phase 2a: review fixes`) changed these, all recorded in design §0.19:
- **D4's 20 months** are 80 weekly pulses, about 18½ calendar months. The weekly step adds a quarter of the monthly figure, and a year has 52 pulses, so the panel's months divide by `nuclear_program_pulse_month_factor` (52 ÷ 48). The rate of play is unchanged; the spec and chapter 14 say so.
- **D5 and D6, lost standing:** the weekly check reads `nd_proj_*_lasting` (no programme or migration line), so lost standing holds a project in focus rather than switching it to Warheads; the AI chooses nothing without a programme.
- **D6, before the migration:** both availability triggers gain a `nd_delivery_migrated` line, and a migrated leg holds 0, printed with no year.
- **D14:** step 2 is skipped while a ceiling would hold a Warheads focus, and the AI's pick goes through `nd_focus_set_core`, leaving the hold to the monthly pass. D11's status 4 follows the hold in force except in a block that just refreshed it (local `nd_focus_hold_refreshed`).
- **D11 and D12, the texts:** months in tenths, the Warheads row held whatever the focus, a lapsed submarine row, no "on alert", the ceiling variant of each fielder's text, `.35`'s flavor split, the Help topic and funding hover, the Upkeep cap from a script value, and a pending submarine picture.

## PR 2b: what the panel tells

### Task 6: What each focus grants, in figures (§5.3's Programme focus row; D16, D17)

**Files:**
- `common/modifier_type_definitions/nuclear_deterrence_display_types.txt`: `country_nd_exposure_mult` and the booleans;
- `common/static_modifiers/nuclear_deterrence_modifiers.txt`: `nd_focus_terms_*`, never added, with the header list;
- `common/script_values/nuclear_deterrence_values.txt`: `nd_survivability_target_with_*`, `nd_proj_forgone_warheads_*` and `nd_display_upkeep_submarines_weekly`;
- `common/scripted_effects/nuclear_deterrence_effects.txt`: `nd_reach_refresh` stores the counts;
- the Focus rows' hovers in the widget and loc;
- `test_nuclear_layout.py`, `test_nuclear_projects.py`.

- [x] Write the tests:
  - `TestFocusHovers`:
    - each row prints its terms and the ICBM row `nd_icbm_force`'s lines;
    - the target now and with the leg;
    - reach now and with it;
    - the warheads not built;
    - the submarine upkeep in money;
    - each hover within the 500-character limit.
  - `TestFocusTermsMatchScript`:
    - −30% and −50% equal 1 − `nd_exposure_factor_icbms` and `_submarines`;
    - the target-with values equal the product with the factor;
    - the forgone-warheads value is the months × the warhead rate;
    - the reach counts are stored weekly and at fielding.

  Run: FAIL.
- [x] Implement, then `modifier_field_audit --strict`, `modifier_name_audit`, `long_tooltip_audit`, the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear programme: each focus shows what fielding it would grant (spec §5.3)`.

**As built (2026-11-21).** As planned, with these choices:
- **Named factors:** the two legs' factors are named values (`nd_exposure_factor_icbms_held` 0.70, `_submarines_held` 0.50), which the factors, the targets with a leg and the terms' test read. The submarine upkeep's figure is `nd_upkeep_units_submarines_fielded`, read by the leg's upkeep and by `nd_display_upkeep_submarines_with_weekly`.
- **The forgone warheads** (`nd_proj_forgone_warheads_2` / `_3`) live beside the rows' months in `extra_script_values.txt`. They are the months to finish × the Warheads focus's warheads a month, capped by the weekly limit's 13 a month and by the room an arsenal ceiling leaves, since a ceiling would stop those warheads anyway.
- **Reach counts** (`nd_reach_count_now`, `_with_subs`, `_every`) are counted in `nd_reach_refresh` on a human's panel only, from the first device on, as `nd_plan_refresh` is: the AI never reads them.
- **Fielded legs:** the hover's figures give way to "these terms are in force", or for submarines with no coastal state, that they are in port.
- **The rate in the hover:** the project rows' hovers no longer say "at the first device's rate": the rate row's note and the Choose button say it, and the hover had to fit 500 characters with the terms' lines.

### Task 7: Others' delivery; docs, gate, PR 2b (§5.4 Nuclear Powers and National Info; D18, D19)

**Files:**
- `gui/journal_entry_widgets/nuclear_program_widget.gui`: the Powers row's delivery cell;
- `gui/journal_entry_widgets/nuclear_overview_widget.gui`: National Info's Row 3 for another country;
- `common/script_values/`: `nd_display_leg_icbms` and `_subs`;
- loc;
- `test_nuclear_layout.py`: `TRUE_VARS` and the public list, plus `PrivateTest` and `ObserverTest`;
- the Help page's forces topic (delivery legs, public);
- the docs.

- [x] Write the tests:
  - `TestOthersDelivery`: the icons per leg, bombers always, and reading only through the capital and public values.
  - `TestProjectsArePrivate`: `TRUE_VARS` gains the focus and the slots; no other country's panel reads them.

  Run: FAIL.
- [x] Implement, then the GUI lint, the nuclear tests and `preflight.py --changed`. PASS.
- [x] Commit `Nuclear Powers and National Info: which legs each country fields (spec §5.4)`.
- [x] Docs:
  - §0.19's second half, D16–D19;
  - `mod_systems/nuclear.md`;
  - `journal_entry_systems.md`;
  - chapter 14: the focus rows' figures, and the Nuclear Powers and National Info delivery cells. Rebuild the PDF;
  - the play-test rows: each focus row's figures against what fielding gives, and the Powers icons after a rival fields;
  - the spec's status line and the README rows.
- [ ] Full `scripts/preflight.py`. Then PR 2b with `--base main`, the two-reviewer review, one fix pass, and merge on green CI.

**As built (2026-11-21).** As planned, with these choices:
- **The Powers row:** the legs sit after the launch authority in three fixed 24 slots (a leg keeps its place), each with its own hover. To fit, the name column narrowed from 240 to 184 and the estimate from 110 to 80 (472 of 480); the head's columns follow (230 and 80) and its Warheads hover names what comes after the estimate.
- **National Info:** the delivery cell is a Row 4 of its own under Row 3's gate, since Row 3's two cells fill the column. Its icon is the farthest-reaching leg, its word the legs (`nd_delivery_word`) and its third line what they reach (`nd_delivery_reach`). The player's own panel gets no cell: Delivery and Defence covers it.
- **Privacy:** `TRUE_VARS` gains `nd_prog_focus` and `nd_proj_\w+`; the reach counts stay off it, since they follow from public legs and the map.
- **The Help page:** the Nuclear Powers topic (`je_nuclear_program_widget_powers_legend`) says the legs are public and a project is not; the forces topic needed nothing.

## Review Focus

1. **Progress is never lost or doubled.** Cases: a focus switch, a re-activation, a revolution's merge with the custody carry, disarmament (which clears it all) and a lost coast mid-project. Tests: Task 1's `TestParking`, Task 2's `TestLegRemoval`.
2. **A project under a ceiling.** It isn't held, and its funding isn't zeroed. At completion the hold returns the same week. Our own ceiling, a treaty's and the UN ban's behave alike. Tests: `TestHolds`, `TestCompletion`.
3. **The migration.** No ICBM power loses reach, an authority or the force between the update and the first monthly pulse (the bridge). A landlocked country loses its submarine leg. The flag makes it a single run. Tests: `TestFieldedTriggers`, `TestMigration`.
4. **An AI at its desired stockpile with a distant rival funds and fields ICBMs,** and one whose rivals are all in bomber reach never builds range. Tests: `TestFundingAiChance`, `TestFocusOrder`; the play-test's observer game.
5. **Disarmament and dismantling.** Each removes the legs and demotes Launch on Warning or Automatic Retaliation to Central, with the tenure clock put back and the player told. Tests: `TestLegRemoval`, `TestAuthorityBind`.
6. **What another country learns.** Its fielded legs, never its focus or a project's progress. Tests: `TestProjectsArePrivate`, `PrivateTest`.
7. **The upkeep.** The submarine leg costs something at every posture, and the clamp still holds the total to the sum of the parts. Test: `TestSubmarineUpkeep`.
