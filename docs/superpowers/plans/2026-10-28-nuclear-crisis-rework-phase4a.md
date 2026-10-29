# Nuclear Crisis Rework, Phase 4a (Range and Basing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first half of spec phase 4: a nuclear power reaches only the countries its delivery can, a new Nuclear Basing article extends that reach and protects the host, weapons based next to a country cut its warning time, and a host takes some of its guest's weapons accidents (§7, §14.6).

**Architecture:** Each armed country without ICBMs keeps a weekly list of the countries its bombers reach (`nd_reach`), from its own states and its hosts'. One state trigger, `nd_state_in_reach_of = { COUNTRY }`, answers every "can this state be struck" question (ICBMs: all; the list; submarines: any coastal state). Every launch picker, the strike actions, the planner and the AI read it, and a crisis threat at a country out of reach is a bluff (follow-through reason 8). The article is directed (guest → host) and is read live like `nuclear_guarantee`. A second weekly list, `nd_based_near`, holds the guests based in a country next to us, and the survivors and counterforce values take 10 off our effective survivability against them. A weapons accident with a site may fall in a host's state, and the host gets its own event.

**Tech Stack:** Victoria 3 script and GUI; Python 3.11/3.12 tests.

**Spec:** `docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md` (§7, §10's Reach row, §14.6). Phases 1–3 shipped as #1222, #1223, #1225 (`nuclear_crisis_design.md` §0.12–§0.14). Phase 4b (codes 7–10 of §8.5, §8.6) follows in its own plan and PR.

## Global Constraints

- Worktree `~/src/vic3te-nuclear-p4` (sparse, no `gfx/`), branch `feat/nuclear-rework-p4`, base `294e946`. No `POST /reload` from here.
- Owner answer §14.6 (2026-10-28): a host takes **incident exposure** (some of the guest's sited weapons accidents happen in one of its states, with the damage and the politics there) and **no custody risk** (warheads have no location; a war between host and guest ends the article).
- Probed engine facts only (spec §12): `has_strategic_adjacency = <country>` is land and sea-coast neighbors plus war-goal adjacency, not distant coasts; `is_adjacent_to_country` covers sea-coast neighbors; `every_country_strategic_region` (effect) is used in `extra_effects.txt`; `is_land_adjacent_to_state` exists (vanilla's war-goal infamy value) but is not needed here. No `any_country_strategic_region` trigger: the reach is built by effects.
- `variable_list_size` doesn't load: count with `any_in_list`; guard reads with `has_variable_list`; don't edit a list while iterating it.
- `withdraw = { country = X }` leaves a whole treaty (no per-article removal; monetary design ruling G14).
- `debug_log` strings take no `$PARAM$`; a tooltip walk writes nothing (click-only markers where a body sets then reads).
- Op tables stay in step in the widget header, the sgui header and `journal_entry_systems.md` (CRLF: edit bytes). Every loc key American, `#b X#!`. The player guide matches the script, at the depth of its peers.

## Decisions this plan makes where the spec leaves room

| # | Decision | Why |
|---|---|---|
| R1 | Phase 4 ships as two PRs: 4a (this plan) and 4b (codes 7–10, trades) | Phase 4 is twice phase 3's size; 4b's deployment dispute reads this plan's article. Cost: a second review |
| R2 | Delivery comes from the arsenal: every armed country has bomber reach whether or not it researched `nuclear_weapons` (custody or a loose arsenal) | A country holding warheads can deliver them somehow; the alternative strands warheads |
| R3 | `nd_reach` (on the attacker, countries): rebuilt weekly in `nd_weekly_update` for an armed country without `ICBMs`, and from the article's `on_entry_into_force` for the guest. Members: every country `has_strategic_adjacency` to us or to a host; every owner of a state in a strategic region where we or a host own a state (`every_country_strategic_region` → `every_scope_state` → `owner`). With ICBMs the list is cleared and not read | The strike action reads it live; weekly keeps it fresh at a small cost (a few armed countries × their regions' states) |
| R4 | `nd_state_in_reach_of = { COUNTRY }` (state scope): `$COUNTRY$` has ICBMs; or the owner is in its `nd_reach`; or `$COUNTRY$` has `advanced_submarine_technology` and the state `is_coastal`. `nd_reaches_country = { TARGET }` (country scope, the attacker): any state of `$TARGET$` passes | Submarine reach is per state, so no second list; one trigger keeps every reader identical |
| R5 | Readers: both strike actions' `possible` (a `nd_tt_in_reach` line) and `second_state_trigger` and the AI's `will_select_as_second_state`; every `nd_salvo_pick_target` branch; `nd_planner_candidate`; both dispatchers' state pickers; the `.1`/`.11` retaliation ladders and `nd_salvo_fire_first`; the guarantor's `.22`; `nd_retaliation_permitted` (a tooltip line); `nd_ai_nuclear_use_justified`. One test enumerates them | A reach that one path ignores isn't a reach |
| R6 | Leadership needs the capital in reach: the mission row greys with a reason (`nd_plan_can_set_mission = { M = 3 }`), `nd_can_order_salvo` refuses mission 3 without it, and the AI's mission value never picks 3 without it. Forces and Cities pick among reachable states only | The capital can be inland of a submarine-only reach |
| R7 | An unordered launch (incident, commander, Automatic Retaliation) at a country out of reach ends in the dispatcher's existing invalid-context branch: nothing flies, one `TE_NUCLEAR: type=action; action=out_of_reach` line | Narrating a strike that can't happen would lie |
| R8 | `nd_plausible_attacker_of` is unchanged: a warning may still name a country that can't reach us | Keeps phase 1's incident calibration; a false alarm needn't be plausible to a planner. Cost: a bomber-era warning can name a distant rival |
| R9 | Follow-through reason 8 ("they can't reach us": bluff, −25 through the existing `>= 5` band) classified after 7 and 6, before 1. `nd_threat_backed` and `nd_threat_uncertain` gain `nd_reaches_country`, so the AI never bluffs in public over reach | A bluff is a bluff whatever the war says; the AI's no-public-bluff rule must hold |
| R10 | Nuclear Basing (`nuclear_basing`, `common/treaty_articles/125_nuclear_basing.txt`): directed, source = guest (the weapons' owner), target = host; `maintenance_paid_by = source_country`; leverage on the target (115's side); `usage_limit = once_per_side`; `possible` and `requirement_to_maintain` mirror 115 (guest armed and believed armed, not at war with each other, relations not poor, host not the guest's direct subject); no ties or outgun test. AI: a guest offers when the host extends its reach to a rival it can't reach now; a host accepts for protection against an armed rival, less with a high taboo and when it holds warheads itself | §7.3; the guarantee's shape, so the readers and audits already know it |
| R11 | The icon has its own path, `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_basing.dds`, staged in the sparse worktree with `git update-index --add --cacheinfo` pointing at 115's texture | Same picture for now; real art later replaces a file, not the article |
| R12 | Basing counts as a ready guarantee at full weight: a branch in `nd_has_armed_guarantor_against` and `nd_has_ready_guarantor_against` that does not test the guest's `nd_forces_assembled` (the weapons are forward). This also brings the war-support exemption, `nd_faces_retaliation_from` and danger dampening. A strike on the host licenses the guest's answer (`nd_covered_country_struck_by`). Not in 4a: dispute 3, `.20` | §7.3 "the protector term at full weight"; the guest's forces were struck |
| R13 | Warning time: `nd_based_near` (on the country, the guests whose host `is_adjacent_to_country` us), rebuilt weekly. Three penalty values (`nd_warning_penalty_saved/_issuer/_target`: 10 when that scope's enemy is in the list) and three exposure variants subtract it from effective survivability before the divide; the survivors values and both counterforce `_raw` values read them. Mirror: `based_near` in `nuclear_survivors.py`, a `based_near` Posture field | §7.4; the same exposure for the same pair everywhere |
| R14 | Host accidents: only sited kinds (1 bomber, 2 silo) can fall abroad; with any host, a third of them do (a random host, a random incorporated state). Kind 4 (lost warhead) stays on the guest's stockpile: no custody risk. `.30` gains `_abroad` texts naming the host's state; its conceal option (`.e`) is hidden when the site is abroad. The host gets `nuclear_incident.31`: order the weapons out (withdraw from the treaty holding the article), protest (−30 relations), or accept quietly (a small timed legitimacy cost) | §14.6; the host's choice is the politics |
| R15 | Reach row: display only (no op), in the Forces section after Survivors, shown while armed without ICBMs (`nd_reach_limited_sgui`): a word for the delivery (bombers, bombers and submarines) and the count of countries reached, the hover listing them and the hosts | §10 |
| R16 | Self-check `TE_SELF_CHECK OK|BROKEN nd_reach` once a game, at the first weekly rebuild of an armed country without ICBMs that has a strategic-adjacent country: that country is in its list (OK) or not (BROKEN: `add_to_variable_list` from a nested owner scope failed) | The list's build is effect-only and unprobed as a whole |

---

### Task 1: Nuclear Basing and its cover (§7.3)

**Files:** `common/treaty_articles/125_nuclear_basing.txt` (new), the icon path (index only), `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_has_armed_guarantor_against`, `nd_has_ready_guarantor_against`, `nd_covered_country_struck_by`, new `nd_hosts_weapons_of = { GUEST }`, `nd_is_basing_guest = yes`), loc (`te_concepts` article keys; `te_miscellaneous` tooltips and AI descs), `test_nuclear_basing.py` (new).

**Interfaces:** Produces article type `nuclear_basing` (source guest, target host); `nd_hosts_weapons_of = { GUEST }` (host scope); a guest walks its hosts with `every_scope_treaty = { every_scope_article = { limit = { has_type = nuclear_basing source_country = <guest> } target_country = { … } } }`.

- [ ] Write `TestBasingArticle` (keys and shape per R10: `kind = directed`, `maintenance_paid_by = source_country`, `usage_limit = once_per_side`, the gates' tooltips, `on_entry_into_force` calls `nd_reach_refresh` on the source; loc suffixes `""`, `_desc`, `_effects_desc`, `_article_short_desc`; the icon path tracked) and `TestBasingCover` (both guarantor triggers have a `nuclear_basing` branch with the host as target, the ready one without `nd_forces_assembled`; `nd_covered_country_struck_by` has one). Run: FAIL.
- [ ] Implement; add `nuclear_basing` to `test_nuclear_deterrence.test_diplomatic_actions_and_article`'s list. Run the tests, `treaty_leverage_side_audit --strict`, `treaty_evaluation_scope_audit --strict`, `texture_reference_audit --strict`. PASS.
- [ ] Commit `Nuclear range: the Nuclear Basing article and the cover it gives (spec §7.3)`.

### Task 2: Reach (§7.1, §7.2, §7.5)

**Files:** `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_reach_refresh`, `nd_reach_add_from = { FROM }`, called in `nd_weekly_update`), `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_state_in_reach_of`, `nd_reaches_country`, `nd_reach_limited`), the self-check, `test_nuclear_reach.py` (new).

**Interfaces:** Consumes Task 1's host walk. Produces R3's list, R4's triggers, `nd_reach_limited = yes` (armed, no ICBMs).

- [ ] Write `TestReachList` (weekly call for an armed country; cleared with ICBMs; both loops from us and from each host; `has_list` guards; no edit of `nd_reach` inside a loop over it), `TestReachTriggers` (R4's three branches in order; `nd_reaches_country` is `any_scope_state` over `nd_state_in_reach_of`), `test_reach_self_check` (R16). Run: FAIL.
- [ ] Implement. Run tests and the audit gate. PASS.
- [ ] Commit `Nuclear range: who a nuclear power can reach (spec §7.1, §7.2)`.

### Task 3: Reach's readers (§7.5, R5–R9)

**Files:** `common/diplomatic_actions/nuke.txt`, `common/scripted_effects/nuclear_deterrence_effects.txt` (salvo picks, dispatchers, fire-first, planner), `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_planner_candidate`, `nd_can_order_salvo`, `nd_plan_can_set_mission`, `nd_retaliation_permitted`, `nd_ai_nuclear_use_justified`, `nd_threat_backed`, `nd_threat_uncertain`), `common/script_values/nuclear_deterrence_values.txt` (`nd_ai_salvo_mission_value`), `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_classify_follow_through`, `nd_crisis_preview`), `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (`nd_crisis_ft_reason`), `events/nuclear_weapon_events.txt` (`.1`, `.11` ladders), `events/nuclear_crisis_events.txt` (`.22`), loc, `test_nuclear_reach.py`, `test_nuclear_deterrence.py` (`range(1, 9)`, `PREVIEW_PINS`).

- [ ] Write `TestReachReaders.test_every_picker_reads_reach` (each R5 site names `nd_state_in_reach_of` or `nd_reaches_country`), `test_leadership_needs_the_capital_in_reach` (R6, three sites), `test_out_of_reach_launch_flies_nothing` (R7), `test_reason_8` (classifier order 7, 6, 8, 1…; `nd_ft_reason_8` loc; `nd_tt_open_bluff_reach` in the preview; reach in `nd_threat_backed`/`_uncertain`); update `test_classification_writes_every_reason_once` to `range(1, 9)`. Run: FAIL.
- [ ] Implement. Run tests and the audit gate. PASS.
- [ ] Commit `Nuclear range: strikes, salvos, answers and threats stop at reach (spec §7.5)`.

### Task 4: Warning time (§7.4, R13)

**Files:** `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_based_near_refresh` in the weekly block), `common/script_values/nuclear_deterrence_values.txt` (penalties, exposure variants, the survivors and counterforce values), `scripts/analysis/nuclear_survivors.py`, `scripts/analysis/nuclear_incident_rates.py`, `test_nuclear_survivors.py`.

- [ ] Write `TestWarningTime` (each survivors value and both counterforce `_raw` values read the exposure variant for their enemy scope; the penalty is 10 and only for a listed enemy; the mirror and the script agree with and without `based_near`). Run: FAIL.
- [ ] Implement. Run tests and the gate. PASS.
- [ ] Commit `Nuclear range: weapons based next door cut warning time (spec §7.4)`.

### Task 5: The host's accidents (§14.6, R14)

**Files:** `events/nuclear_incident_events.txt` (`.30` site pick and texts, `.e` trigger; new `.31`), `common/static_modifiers/nuclear_deterrence_modifiers.txt` (the quiet host's modifier), loc, `test_nuclear_basing.py`.

- [ ] Write `TestHostAccidents` (only kinds 1 and 2 go abroad; the share; the site is a host's incorporated state; `_abroad` texts; `.e` hidden abroad; `.31` sent to the host with its three options and an `event_image`; kind 4 untouched). Run: FAIL.
- [ ] Implement. Run tests and the gate (event_image, event_context, empty_effect, loc audits). PASS.
- [ ] Commit `Nuclear range: a host shares its guest's accidents (spec §14.6)`.

### Task 6: The Reach row, docs, the play-test list; gate, PR, review

- [ ] Reach row (R15) with its display sgui and loc; `test_nuclear_layout.py` keeps passing; GUI lint clean.
- [ ] Design §0.15 (what shipped, R1–R16, what 4b consumes: the article type, the host walk, `nd_reach`, "next to us" = `is_adjacent_to_country`; war-goal adjacency makes bomber reach nearly universal in a war, so range bites in peacetime crises); `mod_systems.md`; `journal_entry_systems.md` (CRLF); chapter 14 (Nuclear strikes gain reach; the article where its peers sit; the host's accidents under incidents) and the PDF; play-test items from 47 and the `nd_reach` self-check row; `scripting_best_practices.md`: the Modding-Digests trigger list is incomplete, search `vanilla_parsed/` before calling a trigger missing; the spec's status line and its §7.1 provenance slip.
- [ ] Full gate; PR with `--base main`; the two-reviewer final review; one fix pass; merge on green CI.

## Review Focus

1. **A country with no strategic neighbors and no hosts, at war.** War-goal adjacency usually makes its enemy adjacent; when it doesn't, the strike actions show the reach line and no state, and the AI doesn't propose a strike. Test: Task 3's `test_every_picker_reads_reach`.
2. **Submarine-only reach on an inland capital.** Leadership greys with its reason; Forces and Cities pick only coastal states. Test: Task 3's `test_leadership_needs_the_capital_in_reach`.
3. **The basing article ends** (war between them, the guest disarmed). The next weekly rebuild drops the host's reach and cover; nothing reads a stale host. Test: Task 2's `TestReachList` (rebuilt from scratch each week).
4. **An accident abroad with the host's AI.** The host's event fires once with a default, and ordering the weapons out ends only that treaty. Test: Task 5's `TestHostAccidents`.
5. **A crisis threat at a country out of reach.** Reason 8 shows in the preview and the panel, and the AI never issues it publicly. Test: Task 3's `test_reason_8`.
