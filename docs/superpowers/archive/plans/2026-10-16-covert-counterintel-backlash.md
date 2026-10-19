# Covert Warfare: Watching, Backlash, Counterintelligence Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a defender quietly watch a caught foreign operation (growing a network inside the attacker) and expose it later from a new panel section; add domestic backlash to exposures; replace the relations block with consequences; add a defensive Counterintelligence Support operation.

**Architecture:** All script lives in the existing covert files. Watching adds two container flags on the attacker's operation (`iw_known`, `iw_catch_pending`) and a per-watch record container on the defender (`iw_known_ops` list). Exposure keeps today's `covert_warfare.1` → burn → `.2` chain; a new defender decision event (`.3`) and a hidden order event (`.4`) feed it. Backlash is two scripted effects called from `.1`. Counterintelligence Support is a 15th registry operation excluded from every hostile consumer.

**Tech Stack:** Paradox script (Vic3 1.14), `.gui`, YAML loc, Python `unittest` structural tests.

**Spec:** `docs/superpowers/archive/specs/2026-10-16-covert-counterintel-backlash-design.md` (read it first; it carries the why and the owner's decisions).

## Global Constraints

- Tab indentation in `.txt`/`.gui`; exactly one UTF-8 BOM on every changed `.txt`, `.gui`, `.yml`.
- `*_modifier_time` are days. `short_modifier_time` = 913 days (2.5 years).
- `any_*` triggers take no `limit`. `every_in_list` / `random_in_list` do.
- `add_modifier` `multiplier` must be a literal or a constant script value (re-evaluated against ROOT later).
- Every new loc key in an existing `localization/english/*_l_english.yml`; then `python3 organize_loc.py` and commit what it moves.
- No `is_ai` branches for outcomes; AI *choices* run under `is_player = no` (precedent `covert_ai_manage_priorities`).
- `change_variable`/`set_variable` in an option need a `custom_tooltip` (`silent_variable_audit`).
- Container rules (header of `covert_warfare_effects.txt`): never read `parent`; `remove_list_variable` before `destroy_container`; do every "network for target X" lookup's work inside its `random_in_list`.
- Never `POST /reload` from this worktree. Run tests with the main checkout's venv and dummy env:
  `export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`;
  `PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.
- Read test results with `grep -E '^(Ran |OK|FAILED)'`, never `| tail`.
- Commits: stage by path (never `git commit -a`), end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01MmCh1wYJA2AGDDAQmnUzsA`.

## Review Focus

1. **Two exposures of one attacker inside `.1`'s 3-day window** (roll + decision + Expose clicks + AI): the second must wait, not vanish. Test in Task 3 (lockout trigger used at every `.1` trigger site).
2. **The watched operation ends while a row/decision is open** (stand-down, pact lapse, attacker annexed): no row survives its operation; Expose and `.3` do nothing harmful. Test in Task 3 (record removed in `covert_op_destroy`).
3. **Counterintelligence Support leaking into hostile machinery** (network inside the ally, detection roll, Tradecraft, tier-2 count). Test in Task 5 (every `iw_ops` walker in the listed effects filters `covert_op_is_hostile`).
4. **AI starts running the six formerly blocked operations against friends.** Test in Task 1 (their `will_propose` names `covert_is_friend`).
5. **Backlash multipliers reading a variable** (falls to zero when `iw_burned_type_code` is removed). Test in Task 2 (no `multiplier = var:` / script-value-reading-`iw_burned` in the backlash effects).

---

### Task 1: The friend trigger; the relations block becomes a cost

**Files:**
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (new `covert_is_friend`)
- Modify: `common/diplomatic_actions/covert_operations.txt` (six actions)
- Modify: `localization/english/te_concepts_l_english.yml` (preview line; remove or keep `iw_no_good_relations_tt` / `iw_no_cordial_relations_tt` per use)
- Create: `test_covert_friend.py`

**Interfaces:**
- Produces: `covert_is_friend = { TARGET = <country scope ref> }`, country scope. True when (relations ≥ `relations_threshold:cordial` AND a tie) OR relations ≥ `relations_threshold:amicable`. Tie = `has_treaty_alliance_with = $TARGET$` OR `has_treaty_defensive_pact_with = $TARGET$` OR (`is_in_power_bloc = yes` AND `is_in_same_power_bloc = $TARGET$`) OR `is_subject_of = $TARGET$` OR `$TARGET$ = { is_subject_of = PREV }` (write the last with a saved temporary scope if `PREV` reads badly). Relations read as `$TARGET$.relations:root` from the country, as the existing gates do (`scope:target_country.relations:root >= relations_threshold:amicable`). Engine triggers verified in `vic3-engine-docs/1.14.5/docs/triggers.log`.
- Produces: loc key `covert_friend_target_warning_tt` — the launch-preview line ("[target] is a friend. If this operation is caught, the lobby at home that favours them will be angered and the government will lose legitimacy.").

- [ ] **Step 1: Write the failing test** `test_covert_friend.py`

```python
FORMERLY_GATED = ("election_interference", "financial_subversion", "infrastructure_sabotage",
                  "comms_disruption", "ideological_subversion", "destabilization")

class FriendTrigger(unittest.TestCase):
    def test_trigger_defined_with_both_thresholds(self):
        body = scripted_trigger("covert_is_friend")      # helper: regex the block
        self.assertIn("relations_threshold:cordial", body)
        self.assertIn("relations_threshold:amicable", body)
        for tie in ("has_treaty_alliance_with", "has_treaty_defensive_pact_with",
                    "is_in_same_power_bloc", "is_subject_of", "is_in_power_bloc = yes"):
            self.assertIn(tie, body)

class RelationsBlockRemoved(unittest.TestCase):
    def test_no_relations_threshold_in_possible_or_maintain(self):
        for typ in TYPES:                                 # from test_covert_op_registry
            for block in ("possible", "requirement_to_maintain"):
                for b in blocks(action(typ), block):      # every such block
                    self.assertNotIn("relations_threshold", b, f"{typ} {block}")

    def test_formerly_gated_ai_avoids_friends(self):
        for typ in FORMERLY_GATED:
            wp = blocks(action(typ), "will_propose")[0]
            self.assertRegex(wp, r"NOT = \{\s*covert_is_friend = \{ TARGET = scope:target_country \}")

    def test_launch_preview_warns_on_friend(self):
        for typ in TYPES:
            self.assertIn("covert_friend_target_warning_tt", blocks(action(typ), "accept_effect")[0], typ)
```

- [ ] **Step 2: Run, expect FAIL** — `$PY -m unittest test_covert_friend -v` → trigger missing, thresholds still present.
- [ ] **Step 3: Add `covert_is_friend`** to `covert_warfare_triggers.txt` with a header comment (consumers listed in spec § "The definition of a friend").
- [ ] **Step 4: Remove the block** — delete the `iw_no_good_relations_tt` custom_tooltips (5 actions) and `iw_no_cordial_relations_tt` (destabilization) from `possible`, and destabilization's `requirement_to_maintain` relations clause (~line 1558). Keep `iw_no_intel_sharing_tt` everywhere.
- [ ] **Step 5: AI** — add `NOT = { covert_is_friend = { TARGET = scope:target_country } }` to the six actions' `will_propose`; for the four whose `will_break` is not `always = no`, add an `OR` branch breaking when the target is a friend, behind the same `covert_ai_op_settled` wait the other break reasons use. Leave the two wartime operations' `will_break = { always = no }`.
- [ ] **Step 6: Launch preview** — in every hostile action's `accept_effect` preview (after `covert_op_preview_header_tt`'s lines), `if = { limit = { covert_is_friend = { TARGET = scope:target_country } } custom_tooltip = covert_friend_target_warning_tt }`. Write the loc key (use `[SCOPE.sCountry('target_country').GetName]`, never `TARGET_COUNTRY`, per `scripting_best_practices.md`). Delete `iw_no_good_relations_tt`/`iw_no_cordial_relations_tt` loc if nothing uses them.
- [ ] **Step 7: Run tests** — `$PY -m unittest test_covert_friend test_covert_op_registry test_covert_launch_preview test_covert_ai_targets -v` → OK. Fix any existing test that pinned the old gates (update it to the new rule, say so in the commit).
- [ ] **Step 8: Commit** — "Covert Warfare: one definition of a friend; relations block becomes a cost".

---

### Task 2: Domestic backlash

**Files:**
- Modify: `events/covert_warfare_events.txt` (`.1` immediate/options/after; `.2` desc)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (two new effects; record cleanup)
- Modify: `common/script_values/covert_warfare_script_values.txt` (friend relations factor in the two relations values)
- Modify: `common/static_modifiers/extra_modifiers.txt` (two modifiers)
- Create: `common/political_lobby_appeasement/te_covert_appeasement.txt`
- Modify: loc (`te_events_l_english.yml` for event text, `te_modifiers` file the other covert modifiers use for modifier names — find with `grep -l covert_counterintelligence_alert localization/english`)
- Modify: `common/on_actions/covert_warfare_on_actions.txt` or wherever `iw_last_exposed_age` clears the record (clear the new `iw_last_exposed_public` with it)
- Create: `test_covert_backlash.py`

**Interfaces:**
- Consumes: `covert_is_friend` (Task 1).
- Produces:
  - Operator variable `iw_burned_friend` (1/0), written in `.1` `immediate` beside `iw_burned_type_code` (`covert_is_friend = { TARGET = scope:detected_by_country }`), removed in `.1` `after` with the others.
  - `covert_backlash_home = { SHARE = full|half }` — operator scope; needs `scope:detected_by_country`; does nothing unless `var:iw_burned_friend = 1` and `NOT = { covert_exposure_is_costless = yes }`. Tier via the `covert_code_tier_*` triggers on `iw_burned_type_code` (war tier = severe values when not costless). Effects, constants only:

    | tier | appeasement full / half | legitimacy multiplier full / half |
    |---|---|---|
    | mild | −3 / −2 | 3 / 2 |
    | moderate | −5 / −3 | 5 / 3 |
    | severe (and pre-war war tier) | −8 / −4 | 8 / 4 |

    Appeasement: `every_political_lobby = { limit = { OR = { is_political_lobby_type = lobby_pro_country is_political_lobby_type = lobby_pro_overlord } target = scope:detected_by_country } change_appeasement = { amount = <n> factor = appeasement_covert_spying_exposed } }`. Legitimacy: `add_modifier = { name = covert_friend_spying_scandal days = short_modifier_time is_decaying = yes multiplier = <n> }`. When no such lobby exists, a `custom_tooltip = covert_backlash_no_lobby_tt` line instead of the appeasement line.
  - `covert_backlash_public = yes` — **defender** scope, ROOT = operator (reads `ROOT.var:iw_burned_type_code`, `ROOT.var:iw_burned_friend`); skipped when costless. For every lobby in the defender with type pro_country/pro_overlord and `target = ROOT`: `every_lobby_member = { add_modifier = { name = covert_foreign_ties_discredited days = short_modifier_time is_decaying = yes multiplier = <m> } }` with m = 1 / 2 / 3 by tier (mild/moderate/severe), ×1.5 → 1.5 / 3 / 4.5 when friend. Sets defender var `iw_last_exposed_public = 1` when any group was hit (else removes it).
  - Static modifiers: `covert_friend_spying_scandal` (`country_legitimacy_base_add = -1`), `covert_foreign_ties_discredited` (interest-group scope, `interest_group_pol_str_mult = -0.05`). Icons from the existing negative timed-modifier icons. Names + `_desc` loc.
  - Appeasement factor `appeasement_covert_spying_exposed = { duration_to_show = { months = 60 } }` + loc (check how vanilla localizes factors: grep `appeasement_special_events_negative` in vanilla loc and mirror the key shape).
  - `covert_exposure_relations_acknowledge` / `_deny`: × `covert_exposure_friend_relations_mult` (= 1.5) when `var:iw_burned_friend = 1`.

- [ ] **Step 1: Write the failing test** `test_covert_backlash.py`

```python
class Backlash(unittest.TestCase):
    def test_options_call_home_backlash_with_shares(self):
        ev = event(".1")
        self.assertIn("covert_backlash_home = { SHARE = full }", option(ev, "covert_warfare.1.a"))
        self.assertIn("covert_backlash_home = { SHARE = half }", option(ev, "covert_warfare.1.b"))

    def test_friend_flag_copied_and_cleared(self):
        ev = event(".1")
        self.assertIn("iw_burned_friend", block(ev, "immediate"))
        self.assertIn("remove_variable = iw_burned_friend", block(ev, "after"))

    def test_public_backlash_runs_in_after_not_in_event_2(self):
        self.assertIn("covert_backlash_public = yes", block(event(".1"), "after"))
        self.assertNotIn("covert_backlash_public", event(".2"))

    def test_constant_multipliers_only(self):
        for name in ("covert_backlash_home", "covert_backlash_public"):
            body = scripted_effect(name)
            for m in re.findall(r"multiplier = (\S+)", body):
                self.assertRegex(m, r"^\d+(\.\d+)?$", f"{name}: {m}")

    def test_appeasement_amounts(self):
        body = scripted_effect("covert_backlash_home")
        for n in ("-3", "-5", "-8", "-2", "-4"):
            self.assertIn(f"amount = {n}", body)

    def test_friend_relations_factor(self):
        self.assertIn("covert_exposure_friend_relations_mult = 1.5", script_values())
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the modifiers, appeasement factor file (BOM), script values, the two effects (parameter dispatch `SHARE = full|half` via `$SHARE$`-named branches, e.g. two internal effects `covert_backlash_home_full` / `_half`, or a `if = { limit = { always = $IS_FULL$ } }` flag — implementer's choice), `.1` wiring (both options, after the infamy/relations lines, so the tooltip reads abroad then home), `.1` `after`: `scope:detected_by_country = { covert_backlash_public = yes }` straight after the `covert_op_burn` dispatch, inside the same `exists` guard and **before** `iw_burned_type_code` is removed.
- [ ] **Step 4: `.2` text** — wrap `.2`'s `desc` so a `triggered_desc` on `has_variable = iw_last_exposed_public` appends `covert_warfare.2.d_public` ("At home, public anger has turned on [SCOPE.sCountry('iw_exposed_by').GetName]'s friends."). If the jomini desc block can't concatenate here, put the line into `.2`'s `flavor` chain instead; add a play-test line either way. Clear `iw_last_exposed_public` wherever the exposure record is cleared.
- [ ] **Step 5: Run** — `$PY -m unittest test_covert_backlash test_covert_exposure_tiers test_covert_op_registry -v` → OK.
- [ ] **Step 6: Commit** — "Covert Warfare: domestic backlash for exposures".

---

### Task 3: Watching caught operations (script)

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt`
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt`
- Modify: `common/script_values/covert_warfare_script_values.txt`
- Modify: `events/covert_warfare_events.txt` (`.1` hooks; new `.3`, `.4`)
- Modify: `common/journal_entries/je_covert_warfare.txt` (monthly pulse: call `covert_watch_monthly` after `covert_nets_sync`)
- Modify: loc (event text in the file `.1`/`.2` use)
- Create: `test_covert_watch.py`

**Interfaces:**
- Consumes: `covert_is_friend` (Task 1).
- Produces (later tasks rely on these exact names):
  - Op container flags: `iw_known` (1 while watched), `iw_catch_pending` (1 while `.3` is open).
  - Record container: tags `iw_known_rec` + `iw_known_<TYPE>` (TYPE = the registry short name); parent = defender; in defender list `iw_known_ops`. Vars: `iw_attacker` (country), `iw_attacker_capital` (state), `iw_type_code`, `iw_watch_months`, optional `iw_expose_ordered` (1).
  - `covert_can_watch` (country trigger): `has_game_rule = covert_warfare_enabled` + `has_journal_entry = je_covert_warfare`.
  - `covert_exposure_in_flight` (country trigger, attacker): `OR = { has_variable = iw_burned_type_code has_variable = iw_expose_inflight }`.
  - `covert_op_is_hostile` (container trigger): `NOT = { has_tag = iw_op_counterintel_support }` (true for every type until Task 5 adds the type; add it now so Task 5 only wires it further).
  - `covert_watch_start` (defender scope; needs `scope:iw_caught_op`): sets `iw_known`, clears `iw_catch_pending`, creates the record through a 14-branch dispatch on the op's `iw_op_<TYPE>` tag (`covert_watch_record_create = { TYPE = x }`), ensures the defender's network in the attacker (`covert_net_create = { TARGET = <attacker> }`).
  - `covert_watch_forget = { ATTACKER = <country> CODE = <n> }` (defender scope): removes and destroys the matching record.
  - `covert_watch_expose_record` (defender scope; needs `scope:iw_expose_rec`): if the attacker is `covert_exposure_in_flight`, leave `iw_expose_ordered = 1` for a retry; else find the live op (`random_in_list = { variable = iw_ops limit = { var:iw_target ?= ROOT var:iw_type_code = <rec code> has_variable = iw_known } save_scope_as = iw_burned_op }` on the attacker), set `iw_expose_inflight = 1` on the attacker, `trigger_event = { id = covert_warfare.1 }` on the attacker.
  - `covert_watch_monthly` (defender scope, journal-entry pulse only): reap dead records; `iw_watch_months` +1; retry `iw_expose_ordered`; AI (`is_player = no`) monthly expose roll with chance `covert_ai_watch_expose_chance` (staged on the record or defender).
  - Events: `covert_warfare.3` (visible, defender decision; `event_image` = the espionage dead-drop picture `.1` uses; options `.3.a` Expose (default) / `.3.b` Let it run, `.b` with `custom_tooltip` saying what watching does); `covert_warfare.4` (`hidden = yes`; immediate: every record with `iw_expose_ordered` → `covert_watch_expose_record`).
  - Script values (starting tuning, constants): `covert_net_watch_gain_p1 = 4`, `_p2 = 5.4`, `_p3 = 6.4`; `covert_ai_watch_chance` (60 mild/moderate/war, 15 severe, +20 friend, = 10 when the defender's network in the attacker ≥ 75); `covert_ai_watch_expose_chance` (2 + 0.1 × network strength; 25 at ≥ 75; +5 severe).

- [ ] **Step 1: Write the failing test** `test_covert_watch.py`

```python
class Roll(unittest.TestCase):
    def test_roll_skips_known_pending_and_friendly(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        for s in ("has_variable = iw_known", "has_variable = iw_catch_pending", "covert_op_is_hostile = yes"):
            self.assertIn(s, body)

    def test_every_event_1_trigger_checks_lockout(self):
        # every trigger_event id = covert_warfare.1 outside the debug harness sits under covert_exposure_in_flight
        for path, ctx in trigger_sites("covert_warfare.1"):
            self.assertIn("covert_exposure_in_flight", ctx, path)

    def test_defender_branch(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        self.assertIn("covert_can_watch = yes", body)
        self.assertIn("covert_warfare.3", body)
        self.assertIn("is_player = no", body)

class Records(unittest.TestCase):
    def test_destroy_forgets_record(self):
        self.assertIn("covert_watch_forget", scripted_effect("covert_op_destroy"))
        self.assertIn("covert_watch_forget", scripted_effect("covert_op_sync"))

    def test_record_dispatch_covers_every_hostile_type(self):
        body = scripted_effect("covert_watch_start")
        for t in HOSTILE_TYPES:                # TYPES minus counterintel_support
            self.assertIn(f"iw_op_{t}", body)

    def test_events_exist(self):
        self.assertTrue(event(".3") and event(".4"))
        self.assertIn("hidden = yes", event(".4"))
        self.assertIn("event_image", event(".3"))

class Growth(unittest.TestCase):
    def test_nets_sync_counts_watched_ops(self):
        body = scripted_effect("covert_nets_sync")
        self.assertIn("iw_known_ops", body)
        self.assertIn("iw_net_watch_gain", body)

    def test_monthly_called_from_journal_pulse_after_nets_sync(self):
        pulse = je_pulse()
        self.assertLess(pulse.index("covert_nets_sync = yes"), pulse.index("covert_watch_monthly = yes"))
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Triggers and values** (`covert_can_watch`, `covert_exposure_in_flight`, `covert_op_is_hostile`, the script values).
- [ ] **Step 4: Roll** — `covert_ops_roll_detection_all`: `limit` the roll to hostile, not known, not pending. If ROOT is `covert_exposure_in_flight`, do nothing this month. For the picked op, read the target (`var:iw_target`): if the target is `covert_can_watch` → player target: set `iw_catch_pending`, `trigger_event = { id = covert_warfare.3 }` on the target (scope `iw_burned_op` carries); AI target: `random = { chance = covert_ai_watch_chance … }` → `covert_watch_start` on the target (save the op as `iw_caught_op` first), else today's `.1` on ROOT. Target without a service → today's `.1`.
- [ ] **Step 5: `.3`** — `immediate`: `scope:iw_burned_op ?= { save_scope_as = iw_caught_op }`, save the attacker as `iw_catcher_attacker` for loc. Options guard `exists = scope:iw_caught_op`; `.a` exposes through `covert_watch_expose_record`'s path (or, if locked, starts the watch with `iw_expose_ordered = 1` so the monthly pass exposes it); `.b` → `covert_watch_start`. `after`: clear `iw_catch_pending` on the op if it still exists. Desc names attacker and operation type (custom loc `covert_burned_type_name` needs `iw_burned_type_code` on ROOT — copy the code onto the defender as `iw_caught_type_code` in `immediate` and add a matching custom-loc block, or reuse `covert_last_exposed_type_name` by writing to a defender variable it reads; implementer's choice, keep it to one new block).
- [ ] **Step 6: `.1` hooks** — `after` removes `iw_expose_inflight`. `immediate`: if the burned op had `iw_known`, log once per game `debug_log = "TE_SELF_CHECK OK covert_watch_expose …"` (global flag `te_selfcheck_covert_watch_done`).
- [ ] **Step 7: Records** — `covert_watch_record_create`, `covert_watch_forget`; hook `covert_watch_forget` into `covert_op_destroy` and `covert_op_sync`'s direct reap when the dying op has `iw_known` (call on `var:iw_target` with ATTACKER = the operator, CODE = `var:iw_type_code`).
- [ ] **Step 8: Network growth** — `covert_nets_sync` step 2: zero `iw_net_watch_gain` on every network; walk `iw_known_ops` records; for each live one add `covert_net_watch_gain_p<priority>` of its op (read the op's `iw_priority` inside the attacker's `random_in_list`, stage on the defender) to the network whose `iw_target` = record's attacker. Step 3: a network with `iw_net_watch_gain > 0` counts as active (no decay) and gains `iw_net_watch_gain × iw_net_tc_mult` through `covert_net_gain` (UN multiplier too if `covert_net_tick_gain` applies it; mirror that). Step 4 reap must not reap a network with watch gain.
- [ ] **Step 9: Monthly** — `covert_watch_monthly` as in Interfaces; self-check: a record with `iw_expose_ordered` whose attacker is **not** in flight and whose op is still alive one month after the order → `debug_log = "TE_SELF_CHECK BROKEN covert_watch_expose …"` once per game, then retry.
- [ ] **Step 10: Run** — `$PY -m unittest test_covert_watch test_covert_networks test_covert_detection_roll test_covert_op_registry -v` → OK. Then `$PY empty_effect_audit.py --strict`, `silent_variable_audit.py --strict`, `event_image_audit.py --strict`, `orphaned_event_audit.py --strict`, `script_argument_audit.py --strict`, `event_context_audit.py --strict` (paths: `ls *_audit.py scripts/analysis/*audit*`) → exit 0.
- [ ] **Step 11: Commit** — "Covert Warfare: a defender can watch a caught operation".

---

### Task 4: Known Foreign Operations panel section

**Files:**
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui` (new type `te_covert_sec_known`, instanced in the `widget_je_covert_status` composer after `te_covert_sec_counterintel = {}`)
- Modify: `common/scripted_guis/covert_warfare_sguis.txt` (`covert_expose_known_sgui`, `covert_known_any_sgui` is_shown helper if needed)
- Modify: loc (`je_iw_known_*` keys beside the other `je_iw_*`)
- Modify: `test_covert_layout.py`

**Interfaces:**
- Consumes: record container shape and `covert_warfare.4` (Task 3), `covert_exposure_in_flight`.
- Produces: `covert_expose_known_sgui` — `scope = country`, `saved_scopes = { iw_known }`; `is_valid`: `exists = scope:iw_known`, `scope:iw_known = { has_tag = iw_known_rec }`, it is in ROOT's `iw_known_ops`, and its attacker is not `covert_exposure_in_flight` (custom_tooltip reasons for each); `effect`: `scope:iw_known = { set_variable = { name = iw_expose_ordered value = 1 } }`, `trigger_event = { id = covert_warfare.4 }`. Button: `AddScope( 'iw_known', ScriptContainer.MakeScope )`, exactly the priority stepper's pattern.

- [ ] **Step 1: Failing test** — in `test_covert_layout.py`: the composer instances `te_covert_sec_known`; the section's row datamodel is `GetList('iw_known_ops')`; for every hostile type there is a row `visible` on `ScriptContainer.HasTag('iw_known_<type>')` with its action icon; the button calls `covert_expose_known_sgui` with `AddScope( 'iw_known', ScriptContainer.MakeScope )`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Build the section** to `docs/guides/gui_style_guide.md` (collapsible header with a `GetVariableSystem` toggle like `covert_counterintel_closed`; hidden when the list is empty — `HasVariableList`/a scripted-GUI `is_shown` per the Counterintelligence "caught" pattern; flag + attacker name via `ScriptContainer.MakeScope.Var('iw_attacker_capital').GetState.GetCountry`; months watched; network strength on hover; Expose button with `IsValidTooltip` + `ExecuteTooltip` hover as `je_iw_priority_step_up_tooltip` does).
- [ ] **Step 4: Run** — `$PY -m unittest test_covert_layout test_covert_stand_down -v` → OK; `$PY scripts/analysis/check_gui_lint.py` → no errors; `$PY gui_reference_audit.py --strict` → 0.
- [ ] **Step 5: Commit** — "Covert Warfare: Known Foreign Operations section with Expose".

---

### Task 5: Counterintelligence Support operation

**Files:** every site in `mod_systems.md` § "Adding an operation type" (actions, tier trigger, `is_covert_operation_pact`, `covert_ops_sync_all` row, apply block, `.1` burn chain, custom-loc type names/descs, stand-down handler, widget row + icon + stand-down, static modifier, launch preview, loc), plus `test_covert_op_registry.py` (`OPS` row), `test_covert_tech_gates.py` (`UNGATED`), `test_covert_layout.py`, `test_covert_stand_down.py`; icon: reuse an existing covert action icon path (`gfx/` is not checked out here; pick one that `git ls-files gfx/interface/icons/diplomatic_action_icons/` lists, e.g. the cultivate-assets icon) and note it for a later icon pass.

**Interfaces:**
- Consumes: `covert_is_friend`, `covert_op_is_hostile` (Tasks 1, 3).
- Produces: registry row `("counterintel_support", 14, "ideological", "mild", "covert_counterintel_support")`; action `covert_counterintel_support_action`; static modifier `covert_counterintel_support` (`country_covert_defense_economic_add = 8`, `_military_add = 8`, `_ideological_add = 8`), applied on the target via `covert_op_add_scaled_modifier`; target variable `iw_cis_protector` (country) set on create, removed on destroy.

- [ ] **Step 1: Failing tests** — add the `OPS` row (registry tests then fail at every missing site); `UNGATED` gains it; new `test_covert_counterintel_support.py`:

```python
def test_action_shape(self):
    a = action("counterintel_support")
    self.assertIn("is_hostile = no", a)
    self.assertIn("covert_is_friend = { TARGET = scope:target_country }", blocks(a, "possible")[0])
    self.assertNotIn("iw_no_intel_sharing_tt", a)
    self.assertIn("cost = 25", a)
    self.assertTrue(any("covert_is_friend" in b for b in blocks(a, "requirement_to_maintain")))

def test_excluded_from_hostile_machinery(self):
    for name in ("covert_ops_roll_detection_all", "covert_nets_sync", "covert_tradecraft_monthly",
                 "covert_net_refresh_intel"):
        self.assertIn("covert_op_is_hostile", scripted_effect(name), name)
    self.assertIn("covert_op_is_hostile", scripted_effect("covert_op_create"))  # head start + net create skipped

def test_one_protector(self):
    self.assertIn("iw_cis_protector", blocks(action("counterintel_support"), "possible")[0])
```

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the action (`requires_approval = no`, `is_hostile = no`, `should_notify_third_parties = no`, `show_confirmation_box = yes`; `possible`: rule, journal entry, funding ≥ 1, free slot, `covert_ops_type_below_cap`, `covert_is_friend`, target not ROOT, target has no `iw_cis_protector` other than ROOT; pact `cost = 25`, maintain: funding ≥ 1 and `covert_is_friend`; AI `will_propose`: friend, slot, funding, `in_default = no`, target `intelligence_capacity_total` < ours, target is a bloc member we lead / our subject / `has_treaty_alliance_with`, `covert_ai_can_spare_influence`, and we run no other Counterintelligence Support; `will_break = { always = no }`), then every registry site. Detection: `covert_op_refresh_detection` still runs for display plumbing, but the roll filters it out and the row shows "—" instead of a percentage (gate the row's detection text on the type tag).
- [ ] **Step 4: Exclusions** — `covert_op_is_hostile` filters in: `covert_ops_roll_detection_all`; `covert_nets_sync` steps 1–2; `covert_op_create` (skip the head-start lookup and `covert_net_create` for this type); Tradecraft's operation count; `covert_net_refresh_intel`'s count of operations against us; `covert_ai_manage_priorities` (wanted level 1 for this type). Grep every other `variable = iw_ops` walker and decide; list each in the commit body.
- [ ] **Step 5: Run** — `$PY -m unittest test_covert_counterintel_support test_covert_op_registry test_covert_tech_gates test_covert_layout test_covert_stand_down test_covert_launch_preview test_covert_new_ops -v` → OK.
- [ ] **Step 6: Commit** — "Covert Warfare: Counterintelligence Support operation".

---

### Task 6: Console harness

**Files:** `events/te_debug_covert_events.txt` (`te_debug_covert.7`), `common/scripted_effects/te_debug_covert_effects.txt`, loc.

- [ ] **Step 1:** `te_debug_covert.7` (header comment with `# REVIEWED 2026-10-16:` like its siblings) options: (a) every foreign operation against us is caught now (player: `.3` for the first, the rest watched); (b) expose every watched operation (sets `iw_expose_ordered`, fires `.4`); (c) relations +60 with every country running operations against us (makes friends, to see backlash); (d) start Counterintelligence Support on our strongest friend from a random friend of theirs.
- [ ] **Step 2:** `$PY orphaned_event_audit.py --strict`, `event_image_audit.py --strict` → 0. Commit — "Covert Warfare: console harness for watching and backlash".

---

### Task 7: Docs, player guide, play-test list

**Files:** `docs/systems/mod_systems.md` (§ Covert Warfare: new bullets for watching, backlash, friend, Counterintelligence Support; "Adding an operation type" list gains the hostile filter); `docs/systems/journal_entry_systems.md` (CRLF; Panels: the new section); `docs/guides/scripting_best_practices.md` (pacts/articles have no visibility field — § D summary, 3–4 lines); `docs/guides/gui_modding_guide.md` (CRLF; where other countries' pacts render: `country_panel.gui` types, 2–3 lines); `docs/player_guide/11-influence.md` (+ `17-reference.md`/appendix if it lists covert operations); `docs/testing/covert-counterintel-playtest.md` (new); rebuild `Vic3TimelineExtended_Player_Guide.pdf`.

- [ ] **Step 1:** Edit docs. CRLF files: edit with the Edit tool and confirm `grep -c $'\r$' <file>` equals `wc -l` afterwards.
- [ ] **Step 2:** Play-test list: the Expose button's `AddScope` link; `.3` firing and both options; `.1` firing from `.4` (self-check lines `TE_SELF_CHECK … covert_watch_expose`); the appeasement factor's tooltip line; `.2`'s public line; Counterintelligence Support's defence rows; whether a covert operation's target gets a launch toast (§ D).
- [ ] **Step 3:** `$PY scripts/build_player_guide.py` then `$PY scripts/build_player_guide.py --check` → OK; `$PY scripts/analysis/check_player_guide_style.py --strict` → 0.
- [ ] **Step 4:** Commit — "Covert Warfare: docs, player guide and play-test list".

---

### Task 8: Whole-branch verification

- [ ] **Step 1:** `python3 organize_loc.py` (commit what it moves); `python3 organize_loc.py --check` → exit 0; `python3 scripts/analysis/check_localization_files.py` → 0.
- [ ] **Step 2:** `python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' '*.gui')` → clean (exclude the two generator-owned files).
- [ ] **Step 3:** BOM check on every changed `.txt`/`.gui`/`.yml`: exactly one (`head -c3 | xxd` = `efbbbf`, and not followed by another).
- [ ] **Step 4:** Full suite: `$PY -m unittest discover -s . -p 'test_*.py' > $SCRATCH/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' $SCRATCH/suite.txt` → OK. `/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .` → clean.
- [ ] **Step 5:** Every CI audit in its CI mode (list in `.github/workflows/ci.yml`; run that file's exact commands) → exit 0; `loc_coverage_audit --strict` and `pm_employment_audit --strict` build a ModState from `vanilla_parsed/` (~7 s each).
- [ ] **Step 6:** Whole-branch review: two fresh read-only reviewers (script; docs/GUI/loc), severity-ranked. Fix what's real, re-run Steps 4–5, commit.
