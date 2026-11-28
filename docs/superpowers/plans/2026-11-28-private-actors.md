# Private Actors Implementation Plan

> **For agentic workers:** each task below goes to one Opus subagent, in order, on the branch named under **Where**. Read the spec sections a task names before writing anything; this plan fixes names, storage and the places later tasks extend, and does not repeat the spec's reasons.

**Goal:** Every company in every country becomes a **firm**: an actor with a goal derived from its position, three currencies, holdings it builds and defends, a yearly turn, and five chains of action (the trust, politics at home, the workforce, technology, relief, and the chain abroad). It all runs behind a default-off game rule and shows in a Private Actors tab of the Timeline Extended window.

**Spec:** `docs/superpowers/specs/2026-11-28-actors-firms-design.md` (#2140). Section numbers below (§ N) are the spec's.

**Architecture:** One config-driven generator reads every company type's buildings and production methods, and a hand-written law table, and writes each firm type's sector (building types, outputs, two largest inputs, staffing, technologies, stances on laws) as generated script. Hand-written script runs a monthly country pulse: each firm takes a yearly turn in a month of its own (assess, score eight goals, pick one, take one verb), and every third month the country runs a quarterly step (holdings grow or decay, currencies accrue, yields refresh, declared moves count down). A firm's record lives in company variables. A row container per firm mirrors what the tab shows, because GUI access to a company's variables is unproven and access to a script container's is proven. State yields refresh from the monthly state pulse.

**Tech stack:** Paradox script (Victoria 3 1.15.2), Python 3.11/3.12 generators and tests run under pytest, `organize_loc.py`, `scripts/preflight.py`. No game install in the build environment: nothing here is seen in game before it merges. Every engine fact the spec lists as a probe (§ 16) ships as the preferred version with a `TE_SELF_CHECK` line and a named fallback in the play-test list (`CLAUDE.md`, "In-game checks").

**Who does what** (the owner, 2026-11-28): the coordinating session wrote this plan and reviews each task's diff before dispatching the next. Each task goes to an Opus subagent. Each subagent commits its work by path, pushes, and writes its report (what it built, what it deferred, the self-checks it added, any deviation from this plan and why) to the session's scratch folder before returning, since the report is not part of the repo.

**Where:** the main checkout `/workspace/Vic3TimelineExtended`, branch `claude/fervent-davinci-1dci3e`, one task at a time. `.venv` is set up. There is no `POST /reload` (no server running with game data); run generators and audits by their CLIs and `scripts/preflight.py --changed --jobs 4`. One PR at the end.

**Survey notes:** before writing this plan the coordinator had the GUI surface, the tooling conventions and the engine facts surveyed, with file and line references, into its scratch folder (not committed). What they found is folded into the constraints below.

## Global Constraints

### Names

- Script prefix `te_pa_` (no match in the repo today). Event namespace `te_pa`. Generated script `te_pa_gen_*`.
- Game rule `te_private_actors_rule`: settings `te_private_actors_disabled` (the default, owner § 18.2) and `te_private_actors_enabled`. The rule is read in one place only, `te_pa_on` in `common/scripted_triggers/te_pa_rule_triggers.txt` (`has_game_rule = te_private_actors_enabled`).
- Player-facing name **Private Actors** (working name, § 18 open 1). Write it in one loc key, `te_pa_system_name`, and reference it as `$te_pa_system_name$` wherever text names the system, so a rename is one line. An actor is a **firm**.
- Currency names in text: Funds, Connections, Standing. Holding names: Cartel, Captured Regulator, Concession, Press, Company Town, Laboratory, Foundation.

### Files

| What | Where |
|---|---|
| Generator and its config | `scripts/generators/gen_private_actors.py`; `scripts/generators/private_actors_config.py` (the law table and every hand-set list) |
| Generated script | `common/script_values/te_pa_gen_values.txt`, `common/scripted_triggers/te_pa_gen_triggers.txt`, `common/scripted_effects/te_pa_gen_effects.txt`, `common/customizable_localization/te_pa_gen_custom_loc.txt` (only those it needs) |
| Hand-written script | `common/scripted_effects/te_pa_<area>_effects.txt`, `common/scripted_triggers/te_pa_<area>_triggers.txt`, `common/script_values/te_pa_<area>_values.txt`, areas `core`, `goals`, `ledger`, `trust`, `politics`, `workforce`, `tech`, `relief`, `abroad`, `ai`, `debug` |
| On-actions | `common/on_actions/te_pa_on_actions.txt` (one named on-action per pulse, as `te_company_on_actions.txt`) |
| Modifiers | `common/static_modifiers/te_pa_modifiers.txt`; types `common/modifier_type_definitions/te_pa_modifier_types.txt` |
| Events | `events/te_pa_<area>_events.txt`; self-checks in `events/te_pa_debug_events.txt` |
| GUI | `gui/te_pa_widgets.gui`; scripted GUIs `common/scripted_guis/te_pa_sguis.txt`; the two tab gates in `common/scripted_guis/te_system_tab_sguis.txt` |
| Messages, alerts | `common/messages/te_pa_messages.txt`; `common/alert_types/te_pa_alerts.txt` |
| Docs | `docs/systems/mod_systems/private_actors.md` (one `##` per chain, index row in `docs/systems/mod_systems.md`); `docs/testing/private-actors-playtest.md`; a `## Private Actors` section in `docs/testing/rules-off-midgame-playtest.md` |
| Player guide | One subsection per chain in the chapter Task 3 picks (STYLE.md: a system the player works through gets a subsection) |

### Storage

**A firm is a company.** Its record is company variables (companies hold variables; `te_company_months_failing` and the prestige goods use them). Names:

| Variable | Meaning |
|---|---|
| `te_pa_init` | The record exists (set once) |
| `te_pa_turn_in` | Months to the firm's next yearly turn, 1 to 12; set at random when the record is made, so the world's firms are spread over the year |
| `te_pa_goal` | The goal pursued now, by code (below) |
| `te_pa_p_<g>`, `te_pa_w_<g>`, `te_pa_s_<g>` | Pressure (0–100), weight (0.5–1.5) and score of each goal `<g>` |
| `te_pa_reason` | What caused the goal, by a reason code; `te_pa_reason_val` its figure |
| `te_pa_funds`, `te_pa_conn`, `te_pa_stand` | The three currencies (funds in pounds; the other two 0–100) |
| `te_pa_griev` | Grievance (a count) |
| `te_pa_posture` | −1 Restrained, 0 Tolerated, 1 Favored |
| `te_pa_share` | Owned levels over the country's levels of its building types (0–1), from a ladder of `company_owned_levels` comparisons |
| `te_pa_levels` | The ladder's estimate of its owned levels |
| `te_pa_bold_t`, `te_pa_attach`, `te_pa_force`, `te_pa_patern` | Temperament (§ 5.3), read from the executive at each turn |
| `te_pa_exec` | The executive at the last turn (a character scope), to log a change |
| `te_pa_cond` | Condition: 1 prospering, 0 steady, −1 failing |
| `te_pa_seat` | The seat (a state scope, § 4.5) |
| `te_pa_<holding>` | Each holding's strength 0–100: `te_pa_cartel`, `te_pa_reg`, `te_pa_press`, `te_pa_town` (`te_pa_town_harsh` set for the harsh kind), `te_pa_lab`, `te_pa_found` (`te_pa_found_state` its state). Concessions live on states (below) |
| `te_pa_row` | The firm's row container (below) |

**Goal codes:** 1 Cheaper inputs, 2 A protected market, 3 Security of its assets abroad, 4 A friendly law, 5 Dominance, 6 Labor peace, 7 A technical lead, 8 Survival. `<g>` in variable names is `inputs`, `market`, `abroad`, `law`, `dominance`, `labor`, `tech`, `survival`.

**Rows.** The country list `te_pa_rows` holds one script container per firm, each with `te_pa_r_firm` (the company) and a copy of every figure the tab shows. One effect, `te_pa_row_sync` (company scope), writes the copy; it runs at the end of a firm's turn and of each quarterly step, and every task that adds a displayed figure adds its line there. The list is rebuilt from the companies whenever it is missing (a revolution's winner inherits no lists). A container is destroyed when its firm is cleared. Per-row buttons pass the container (`AddScope('te_pa_row', ScriptContainer.MakeScope)`) and the scripted GUI reaches the firm through `scope:te_pa_row.var:te_pa_r_firm`. If the coordinator later finds `Company.MakeScope.Var` works, the rows can go; until then they are the display path.

**Country variables** hold what belongs to the country: the quarter counter `te_pa_q_in`, the declared move (`te_pa_move_firm`, `te_pa_move_kind`, `te_pa_move_months`, `te_pa_move_last`), the Boldness swing (`te_pa_bold_swing`, signed, with its timer), patronage totals per interest group, the sides on the law being enacted, and the ledger.

**The ledger** is the country list `te_pa_ledger`: script containers, at most 20, each with `te_pa_l_seq`, `te_pa_l_verb` (a verb code), `te_pa_l_actor` (company), `te_pa_l_target` (optional scope), `te_pa_l_size`, `te_pa_l_known` (0 for a secret move not yet exposed) and `te_pa_l_month` (`te_history_month_index`). Eviction as `un_ledger_log`. One writer: `te_pa_ledger_add` (country scope, arguments `VERB` and `KNOWN`, with `scope:te_pa_l_actor`, `scope:te_pa_l_target` and `scope:te_pa_l_size` saved by the caller). Each verb code has a loc line in a generated or hand-written custom localization. Codes are assigned in blocks: 1–19 Task 2 (goal changes, executive changes, thresholds), 20–39 Task 4, 40–59 Task 5, 60–79 Task 6, 80–99 Task 7, 100–119 Task 8, 120–139 Task 9, 140–159 Task 10.

**Concessions** (Task 8) live on the state they sit in, two slots: `te_pa_c<N>_firm`, `_home`, `_protector`, `_str`, `_trouble`. Probe 3 decides whether `_firm` can hold a company scope; the fallback stores the company type's code and the home country. The global list `te_pa_concession_states` indexes them.

### Pulses

- `on_monthly_pulse_country` → `te_pa_monthly` (country scope). With the rule off it runs the teardown once (`te_pa_teardown`) and nothing else. With it on: make records for new firms, count each firm's `te_pa_turn_in` down and run `te_pa_turn` at 0, count `te_pa_q_in` down and run `te_pa_quarter` at 0, count the declared move down.
- `on_monthly_pulse_state` → `te_pa_state_monthly`: refreshes each state modifier the system applies, from state variables the firm's step wrote (`te_pa_st_*`). A state modifier's `multiplier` resolves against ROOT, so it is applied only here, with ROOT the state.
- `on_company_disbanded` → clear the firm: its holdings, its row, its ledger name stays (the ledger records the end).
- Country modifiers are applied from `te_pa_quarter` only, one refresh site each, removed first (the dynamic-modifier pattern).

### Rules that bind every task

- The rule off mid-game: `te_pa_teardown` removes every modifier the system applied (country and state), clears the declared move and the alerts' conditions, and leaves the company variables (switching the rule back on resumes from them). Every task that applies a modifier adds its removal there; `test_rule_off_teardown.py` pins it.
- Every event the system fires checks `te_pa_on` (`event_context_audit`'s `SYSTEMS` table gets a row).
- Numbers are the spec's first guesses, each a named script value in `te_pa_core_values.txt` or its chain's values file, never a bare literal in an effect.
- Money out of the investment pool is capped at what the pool holds (`te_mon_union_exit_pool_hit`'s pattern). Gross income is weekly.
- The verbs a firm takes on a turn: one per turn, chosen in `te_pa_act` (Task 4 writes it) from the chosen goal's ordered list `te_pa_act_<g>`, each verb a `te_pa_can_<verb>` trigger (legal, affordable, applicable) and a `te_pa_do_<verb>` effect. A verb nobody has built yet is simply absent from the list. Holdings' upkeep and growth are the quarter's, not the turn's.
- Declared moves (Task 4 builds the frame): one at a time per country against its own government, none within twelve months of the last, six months' countdown (§ 4.6), the higher goal score first. Each kind of petition answers in the event that ends it, with three options in the shape of § 4.7; a country left to the countdown takes its posture's default. AI countries answer by § 12.1's weights, built with each petition.
- Secrecy: a secret move's effect is visible and its ledger line says the author is unknown until it is exposed (`te_pa_l_known = 0`). A major move is never secret.
- Every modifier the system applies names its firm and holding in its tooltip (a modifier per holding kind, its loc reading from the firm); every country modifier with no duration gets its line in `gen_nation_tab.py`'s registry; every treasury cost joins `gen_budget_breakdown.py`'s sources.
- Script values named in `add_modifier`'s `days`/`months` are bare literals. No `has_variable` guard inside a `NOT` with its read. No tooltip-walked read of a variable set in the same body. No undelayed `trigger_event` on a cycle.
- Tabs in script; exactly one UTF-8 BOM on every `.txt`, `.gui` and loc `.yml`; American English; after loc changes run `python3 organize_loc.py` and commit what it changes. In-game text follows `docs/guides/loc_style_guide.md` (the `event-text` skill); events through the `add-event` skill.
- Never hand-edit a generated file. Commit by path. `scripts/preflight.py --changed --jobs 4` green before each task's last commit.

## Review Focus

1. **A goal that never wins or always wins.** Pressures are on one 0–100 scale and a weight never leaves 0.5–1.5. Pinned in Task 2's value tests (each pressure's formula, bounds, and the +15 for a goal held).
2. **Firms that do nothing because a ladder or a switch matches nothing.** The generated sector must cover every company type, vanilla's and the mod's, and the firm's share must read non-zero for a company with levels. Pinned in Task 1 (coverage test) and Task 2 (`TE_SELF_CHECK firm_share`).
3. **A loop through events.** Petitions end in events that change the variables the turn reads. Pinned in Task 4: the move is cleared before the end event fires.
4. **Money from nowhere or money twice.** Funds come from the pool and go back to it exactly once. Pinned in Task 2 (accrual) and Task 4 onwards (each spend through one helper, `te_pa_spend_funds`).
5. **The rule switched off mid-game.** Pinned in each task's teardown line and `test_rule_off_teardown.py`.
6. **An AI government changed by a hidden switch** (§ 12.2): every effect on another country is a quantity the player can see, named in a ledger line or tooltip. Pinned in Task 9's legibility test.

---

### Task 1: The sector generator and the law table

Spec: § 5.1, § 8.1, § 10.1, § 9.1 (staffing), § 13 (generated rows).

**Files:** create `scripts/generators/gen_private_actors.py`, `scripts/generators/private_actors_config.py`, the generated outputs above, `test_gen_private_actors.py`. Modify `server/post_load.py` (register before `organize_loc`), `docs/auto_generated_files.md`, `docs/guides/python_tools.md`, `scripts/nightly_audit_select.py`, `organize_loc.py` (an early rule sending `te_pa_` keys to one category, as `te_demog_`).

**Produces** (company scope unless noted; names fixed, bodies the generator's):

- `te_pa_gen_sector_levels`: the home country's levels of the type's building types (a sum of `"country_has_building_type_levels(bt:X)"`).
- `te_pa_gen_input_pricier_1`, `_2`, `te_pa_gen_output_pricier`, `te_pa_gen_output_cheaper`: signed price readings of its two largest inputs and its main output in the home market, built as `scripting_best_practices.md` § market prices says (clamped parts, signed sum).
- `te_pa_gen_output_imported`, `te_pa_gen_input_imported_1`, `_2` (0/1) and the export counterparts: the home market's trade in each good.
- `te_pa_gen_jobs_per_level`: staff a level of its buildings employs by the base methods.
- `te_pa_gen_tech_gap`: how many of the technologies that unlock a method of its building types the home country lacks and can research; and a yearly global cache of which of those technologies anyone holds, so the turn need not walk every country.
- `te_pa_gen_stance_<law>` for every law the table covers, and `te_pa_gen_stance_enacting`: the stance (−2 to +2) on the law the home country is enacting, 0 when none.
- `te_pa_gen_is_<flag>` triggers for the sector features the law table and the chains need: `fossil`, `financial`, `automatable`, `manufacturing`, `extraction`, `agriculture`, `infrastructure`, `consumer_good` (one per feature, derived from building groups and outputs).
- Custom loc naming the type's input and output goods for the goal's reason line.
- A yearly per-type branch that rides on one `switch`/`if` chain on `is_company_type`, so a firm's turn pays for one chain, not one per value.

**The law table** (`private_actors_config.py`) is § 8.1's table as data: for each covered law, the sector features it burdens or favors and by how much (1 or 2). Trade policy and tariffs are not in it: they are read from the market (§ 8.1's first bullet), in Task 2's hand-written values. Read every law of each covered group from `vanilla_parsed/` and `common/laws/`, and write each law's row or a reason for none; § 8.1 and § 9.2 and § 10.3 say "first reading, check against the laws": read each law's modifiers before signing it, and record in the config's comments what in the law the sign rests on.

**Tests:** every company type (merged vanilla and mod) gets a sector; every covered law group's every law has a row or a written reason (a new law can't slip past); the committed outputs are current (`--check`); a synthetic company type gets the expected branch. Run `scripts/check_post_load_rosters.py` and the generator's `--check`.

### Task 2: The chassis

Spec: §§ 4.1–4.3, 4.5, 4.7 (posture as a stored value only; the buttons are Task 3's), 5.2, 5.2a, 5.3, 5.4, 13, § 16 probes 7, 8, 11.

**Files:** the rule (`common/game_rules/extra_game_rules.txt`, `te_pa_rule_triggers.txt`, loc); `te_pa_on_actions.txt`; `te_pa_core_*`, `te_pa_goals_*`, `te_pa_ledger_*`, `te_pa_debug_*`; `docs/systems/mod_systems/private_actors.md` (first sections) and its index row; `docs/testing/private-actors-playtest.md`; the rules-off section; `docs/systems/mod_systems/game_rules.md` rows and every rule count (`README.md`, `01-introduction.md`, `game_rules.md`: twenty-three becomes twenty-four).

**Builds:**

- The monthly pulse, the record (including `te_pa_turn_in` at random), the quarter, the turn's skeleton: assess (share, condition, temperament, seat), score eight goals, choose with the +15 for the goal held, log a change of goal with its reason, `te_pa_row_sync`. No verbs.
- Funds accrue quarterly at a quarter of § 4.3's yearly 10% of estimated dividends, capped at five years' accrual; none under Command Economy or Cooperative Ownership. Connections and Standing accrue from § 4.3's sources that exist in this task (years established, the executive's group in government, posture); later tasks add theirs.
- The eight pressures from the generated readings and § 5.2's table. Security abroad reads 0 until Task 8. Dominance reads share only until Task 8 adds the rival. A friendly law reads the law table: a law in force that burdens the sector, the law being enacted, or a law in a covered group the country could move to that would favor it. Labor peace reads radicals and turmoil at the seat (0–1 scales), a burdening labor law being enacted, and `has_journal_entry = je_strike`. Survival reads prosperity and its weekly change, `te_company_months_failing`, the Banking Cycle phase behind `te_banking_cycle_running`, and the laws that end private ownership or remove the sector's buildings.
- Weights from temperament and condition, each 0.5–1.5. AI posture derived each turn (§ 12.1's first bullet).
- The ledger ring and `te_pa_ledger_add`. Threshold notices (§ 4.6) as messages, once per crossing: this task posts "is failing" and "controls 40% of its sector" (the latter Task 4 acts on).
- The teardown; the clear on `on_company_disbanded`.
- Self-checks: `firm_share` (a company with levels reads a share above 0), `firm_executive` (probe 7: the executive exists and a trait test runs), `firm_hq` (probe 11: whether a headquarters state is reachable; the seat falls back to the state with most levels of its types), `firm_revolution` (probe 8, armed when a revolution wins: the winner's firms keep `te_pa_init`).

**Tests:** pressures and weights bounded; the score formula; the hysteresis; the rule read only through `te_pa_on`; the teardown removes what the task applies; every variable the rows show is written by `te_pa_row_sync`.

### Task 3: The tab

Spec: § 14 (roster, firm detail, ledger; the Politics and Abroad sections are added by Tasks 5 and 8), § 4.7 (the posture control), § 12.2 rule 4 (public in National Info).

**Files:** `gui/te_pa_widgets.gui`, `te_pa_sguis.txt`, the tab line and `NI_ORDER` in `gen_te_systems_window.py` and its two generated files, the gates in `te_system_tab_sguis.txt`, the Help page (`gui/te_popups.gui`, loc, `test_te_help_pages.py` `PAGES`), the tab tests that list tabs by hand (`test_te_systems_window.py` `STRIP_ORDER`, `FULL_NAMES`, the tab count, `RULES`; `test_te_system_tab_bodies.py` `WINDOW_BODIES`), a layout test with `assert_wide_matches_narrow`, `gui_modding_guide.md`'s GUI files table and count, the player guide.

**The strips are full** (6, 5, 5). Make room on strip 2 or 3, whichever holds the economy tabs, with `te_tab_buttons_six` as strip 1 has, and update the full-screen and National Info layouts that read the strip sizes. Power Grids is the template: no journal entry, public, a Help page. The tab is gated on `te_pa_on`; its grayed checklist says the rule is off.

**Builds:** the roster (one row a firm from `te_pa_rows`: name and icon through `Var('te_pa_r_firm').GetCompany`, executive, goal and reason, condition, three currency bars, holdings as chips, any declared move with its countdown, the posture control under `te_own_country_only`), a firm's detail on expanding its row (holdings, eight goal scores with pressure and weight, its stance on the law being enacted), the ledger (collapsed by default; "author unknown" lines). The panel reads `Country`, never `GetPlayer`. The posture buttons' scripted GUI sets `te_pa_posture` on the firm and logs it. The player guide's subsection for the system as Task 3 leaves it: what a firm is, what it wants, the tab, the posture, the rule.

**Tests:** the tab tests above; `check_gui_lint.py`; `gui_reference_audit.py --strict`; `test_gui_*`.

### Task 4: The trust and the foundation

Spec: § 5.5, § 6, the declared-move frame of § 4.6, the alerts of § 14, § 16 probe 2.

**Builds:** the verb dispatch `te_pa_act` and `te_pa_spend_funds`; the cartel (open or secret by § 6.2's table, strength, rents as a country modifier on the sector's `building_<type>_throughput_add` from the quarter, funds faster); buyers as actors (§ 6.3: paying for exposure, petition to bring suit, routine only until Task 5's law petition exists); the trust's defence (§ 6.4: stall the law, capture the regulator, a foundation; campaign money and the press are Task 5's and join the list then); the charter petition (§ 6.5) as the first declared move, with the frame every later petition uses (the move, the countdown, the alert, the end event's three answers, the posture default, the AI weights); the state's actions (§ 6.6) as buttons on the firm's detail, each a scripted GUI with its cost scaled by Standing; the foundation (§ 5.5) and its state modifier through the state pulse; exposure (a yearly roll per secret holding, from § 4.6's sources) and its costs. The alerts file with the yellow and red alerts. Ties of § 6.7 that are one line each (Judicial Independence in a case; National Champion Exemption; "Too Large to Break" raised by the largest cartel's firm; Wealth Concentration's economy term if it reads a sum this can add to). Self-check `cartel_rents` (probe 2).

**Docs and guide:** the trust's `##` in the system doc; the guide's subsection on the trust and the state's actions; play-test lines.

### Task 5: Politics at home

Spec: §§ 8.1–8.5, 8.7, probes 9, 10, 13, 14.

**Builds:** sides on the law being enacted (§ 8.2) and their settlement when it ends; stall and speed (§ 8.3; probe 10's fallback named); campaign money in both forms and under each Electoral Finance law (patronage as a country modifier per interest group from the quarter, capped at 20%, decaying over three years); the petition for a law or a tariff (§ 8.4) on Task 4's frame, with an AI country's pledge started by `start_enactment` when it enacts nothing (probe 13) and a tariff by `set_import_tariff_level` (probe 14); the press (§ 8.5) under the speech laws; the state's actions of § 8.7; the tab's Politics section. Add campaign money and the press to the trust's defence list.

### Task 6: The workforce

Spec: § 9, probe 15. Welfare and strikebreaking under the Labour Associations laws, the company town of both kinds (state modifiers through the state pulse), bloodshed, the state's actions of § 9.4, the tie to vanilla's Strike entry (read it, never run a second strike). Self-check `strike_read` (probe 15).

### Task 7: Technology

Spec: § 10. Research through generated literal `add_technology_progress` ladders (one firm at most 5% of a technology's cost a year), the laboratory, espionage on covert tech theft's pattern, § 10.3's table, the Favored posture's aim. Gate the technology rules behind A technical lead being worth scoring.

### Task 8: Relief

Spec: § 11, probe 12. Retrenchment in § 11.1's order, the petition for relief on Task 4's frame, the relief line as § 11.2 proposes it (a `country_expenses_add` modifier joined to the Budget breakdown; funds credited and the pool with them; the throughput lift at the seat through the state pulse; the failing count reset), Rescue's and Let it fail's Boldness swing, the slump's queue. The owner has not ruled on the lift at the seat (§ 18 open 2): build it as proposed, in one modifier the owner can drop, and say so in the PR.

### Task 9: Concessions abroad

Spec: §§ 7.1–7.3, the Abroad section and the map of § 14, probes 1 and 3. The concession (opening cost by § 7.1's soft caps, two slots a state, strength, funds, output of its type, Involvement each quarter by `add_involvement`), rivalry, Trouble and the firm's routine answers (bribes, hired force), the host's Expel move, the index list, the Map Room map, the Abroad section. Security of its assets abroad and Dominance's rival term now read real values. Self-checks `involvement_added` (probe 1) and `state_holds_company` (probe 3).

### Task 10: Pulled abroad

Spec: §§ 7.4, 7.5, 8.6, 12, probes 5 and 6. The petition for protection with Back, Stand aside and Forbid; Back on the frontier starts the colony (probe 5's fallback the growth modifier); the ladder after Forbid with Boldness and the protector; campaign money abroad; AI answers; the legibility rules of § 12.2 with a test that every effect on another country is logged or tooltipped. Self-checks `colony_from_script` (probe 5) and `play_from_script` (probe 6).

### Task 11: Telemetry, review and the PR

Spec: § 17 phase 7's offline part. Extend the AI telemetry probe (`ai.md`) to count moves by tier and goals by kind. An independent review of the whole branch against the spec and this plan, with fixes. Full `scripts/preflight.py`. The superpowers README rows (this plan's, and the spec's status). The PR body: what was built per phase, the open calls (the name, the relief lift), the self-checks, the player guide chapters.
