# -*- coding: utf-8 -*-
"""The tax code's AI layer (plan 2026-10-03, Tasks 18-22). Structural tests.

Spec: docs/superpowers/specs/2026-10-03-tax-code-ai-and-release-design.md §2.
Task 18 lays down the AI's state and signals and the dispatch:

* every te_tax_ai_* token is a schema token: in the schema table with its
  sentinel, initialised by te_tax_init_country (schema version 2), copied at
  the outbreak, never removed, and its bill state reset at the outbreak, the
  win repair and a release;
* the tunables of spec §2.14 and the fiscal reads (R, D, G) are named script
  values; the need and emergency triggers read them;
* the processor's rule 1b updates the fiscal streaks for every migrated
  country and, for an AI country with something due, raises te_tax.8 on its
  bucket day; te_tax.8 re-checks the rule and is_ai and runs the step;
* the commands' own debug_log lines are written for player countries only,
  unless the transitions (processor, watchdog, te_tax.4-7, civil war) also
  reach them; the AI's summary lines replace them.

Run: python3 -m unittest test_tax_code_ai -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_rule import load
from test_tax_code_scheduler import closure, effects, limit_of
from test_tax_code_state import KEYS, block, close, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

AI_EFFECTS = "common/scripted_effects/te_tax_ai_effects.txt"
AI_TRIGGERS = "common/scripted_triggers/te_tax_ai_triggers.txt"
AI_VALUES = "common/script_values/te_tax_ai_values.txt"
AI_FILES = (AI_EFFECTS, AI_TRIGGERS, AI_VALUES)
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
EVENTS = "events/te_tax_internal_events.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
BILL = "common/scripted_effects/te_tax_bill_effects.txt"
OFFER = "common/scripted_effects/te_tax_offer_effects.txt"
OBLIGATION = "common/scripted_effects/te_tax_obligation_effects.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
COMMAND_FILES = (BILL, OFFER, OBLIGATION, GEN_BILL)
SCHEMA_DOC = "docs/systems/tax_code_schema.md"

AI_TOKENS = {
    "te_tax_ai_phase": "-1", "te_tax_ai_def_streak": "0", "te_tax_ai_sur_streak": "0",
    "te_tax_ai_next_month": "-1", "te_tax_ai_tpl": "0", "te_tax_ai_bill_month": "-1",
    "te_tax_ai_noviable": "0", "te_tax_ai_offer_month": "-1", "te_tax_ai_offer_count": "0",
    "te_tax_ai_retry": "0",
}
AI_INSTRUMENT_TOKENS = {"te_tax_ai_last_": "-1", "te_tax_ai_dir_": "0"}
# What te_tax_ai_reset_bill_state writes: no AI bill, offer chain or retry
# survives a civil war or a release. The streaks, the phase and the cooldown
# are the country's own and stay.
RESET = {"te_tax_ai_tpl": "0", "te_tax_ai_bill_month": "-1", "te_tax_ai_offer_month": "-1",
         "te_tax_ai_offer_count": "0", "te_tax_ai_retry": "0", "te_tax_ai_noviable": "0"}
NATIVE_SETTERS = ("add_amendment", "remove_amendment", "set_tax_level", "add_taxed_goods",
                  "remove_taxed_goods", "set_import_tariff_level", "set_export_tariff_level")

# Spec §2.14, first estimates; each a named script value.
TUNABLES = {
    "te_tax_ai_cadence_months": "3", "te_tax_ai_need_months": "3", "te_tax_ai_surplus_months": "6",
    "te_tax_ai_raise_ratio": "0.9", "te_tax_ai_raise_ratio_debt": "1.1",
    "te_tax_ai_cut_ratio": "1.25", "te_tax_ai_cut_ratio_debt": "1.5",
    "te_tax_ai_debt_significant": "0.1", "te_tax_ai_reserves_full": "0.1",
    "te_tax_ai_emergency_debt": "0.5", "te_tax_ai_emergency_weeks": "30",
    "te_tax_ai_cooldown_months": "12", "te_tax_ai_fail_cooldown_months": "6",
    "te_tax_ai_bill_patience": "6", "te_tax_ai_max_offers": "3", "te_tax_ai_levy_sunset": "24",
    "te_tax_ai_reverse_months": "24", "te_tax_ai_max_goods": "4",
    "te_tax_ai_promise_institution_score": "200", "te_tax_ai_enact_lead_months": "1",
}

# The AI's summary lines (spec §2.12): one effect per verb, since debug_log
# cannot print a parameter, and one per reason for withdrawal and no-viable.
LOG_VERBS = {
    "step": "ai_step", "introduced": "ai_introduced", "passed": "ai_passed", "forced": "ai_forced",
    "accepted": "ai_accepted", "released": "ai_released", "rescheduled": "ai_rescheduled",
    "renegotiated": "ai_renegotiated",
    "waiting_legitimacy_native_level": "ai_waiting reason=legitimacy_native_level",
}
LOG_REASONS = ("support", "legitimacy", "slots", "authority", "patience", "draft")
LOG_FIELDS = ("tpl", "R", "D", "G", "def", "sur")
STAMP = ("month=[SCOPE.ScriptValue('te_history_month_index')|0] date=[TimeKeeper.GetCurrentDate.GetString] "
         "country=[THIS.GetCountry.GetNameNoFormatting]")

# Effects in the command files whose debug_log lines stay for every country:
# the transitions reach them too (closure() from the processor, the watchdog,
# te_tax.4-7 and the civil-war effects), and a transition line is written for
# AI countries as well (docs/systems/tax_code_schema.md, "Debug lines").
# closure() expands $SLOT$ only, not $OTHER$; only te_tax_pass_into calls an
# $OTHER$ effect (te_tax_gen_supersede_<s>), and no transition reaches it.
TRANSITION_LOGGED = {
    "te_tax_bill_drop_customs": "processor rule 7: a lost market drops the bill's customs",
    "te_tax_gen_offer_repropose": "processor rule 7: the dropped customs open a new revision, which re-proposes",
    "te_tax_obl_propose": "the same re-proposal records the accepted promises again",
    "te_tax_obl_write": "the same re-proposal writes each promise",
    "te_tax_obl_start_one": "processor rule 3: a commencement starts its bound promises' clocks",
    "te_tax_obl_check_one": "processor rule 4: the monthly check of every binding promise",
    "te_tax_obl_begin_maintenance": "processor rule 4: a promise delivered at the check",
    "te_tax_obl_fulfil": "processor rule 4: a promise kept for its whole term",
    "te_tax_obl_breach": "processor rule 4: a promise missed or failed",
    "te_tax_repair_obligations_after_civil_war": "the civil-war repair reassesses the winner's promises",
}
# Files whose is_ai reads predate the AI layer (te_tax_detect_drift's and the
# customs adoption's first-time-only logging for AI countries), with counts.
PRE_EXISTING_IS_AI = {"te_tax_collection_effects.txt": 3}
PLAYER_LOG_GATE = re.compile(r'if = \{ limit = \{ is_ai = no \} debug_log = "[^"]*" \}')


def flat(text):
    return " ".join(text.split())


def transition_roots(defined):
    """The effects the transitions call: the processor, the watchdog, the
    bodies of te_tax.4 to te_tax.7 and every civil-war effect."""
    roots = {"te_tax_process_month", "te_tax_watchdog_month"}
    events = read(EVENTS)
    for event in ("te_tax.4", "te_tax.5", "te_tax.6", "te_tax.7"):
        roots |= {name for name in re.findall(r"\b(te_tax_\w+) = yes", block(events, event)) if name in defined}
    roots |= set(re.findall(r"(?m)^(\w+) = \{", read(CIVIL_WAR)))
    return roots


def enclosing_brace(text, pos):
    """Offset of the innermost `{` still open at `pos`, or -1 at the top level."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                return i
            depth -= 1
    return -1


def player_gated(text, pos):
    """The innermost block around `pos` is `if = { limit = { is_ai = no } ... }`."""
    brace = enclosing_brace(text, pos)
    if brace < 0 or not text[:brace].rstrip().endswith("if ="):
        return False
    return limit_of(text[brace + 1:close(text, brace)]).strip() == "is_ai = no"


def log_bodies():
    """{effect: body} for every top-level effect with a debug_log in the command files."""
    found = {}
    for path in COMMAND_FILES:
        text = read(path)
        for match in re.finditer(r"(?m)^(\w+) = \{", text):
            body = text[match.end():close(text, match.end() - 1)]
            if "debug_log" in body:
                found[match.group(1)] = body
    return found


class AiTokenTest(unittest.TestCase):
    def test_every_ai_token_is_in_the_schema_table_with_its_sentinel(self):
        country, _ = schema_tokens()
        for name, sentinel in AI_TOKENS.items():
            with self.subTest(name=name):
                self.assertEqual(country.get(name), int(sentinel))
        for key in KEYS:
            for prefix, sentinel in AI_INSTRUMENT_TOKENS.items():
                with self.subTest(key=key, prefix=prefix):
                    self.assertEqual(country.get(f"{prefix}{key}"), int(sentinel))
        # Nothing else in the table carries the prefix.
        listed = {name for name in country if name.startswith("te_tax_ai_")}
        expected = set(AI_TOKENS) | {f"{p}{key}" for p in AI_INSTRUMENT_TOKENS for key in KEYS}
        self.assertEqual(listed, expected)

    def test_scalar_tokens_are_initialised_by_the_init_and_the_per_instrument_ones_generated(self):
        init = flat(block(read(STATE), "te_tax_init_country"))
        for name, sentinel in AI_TOKENS.items():
            with self.subTest(name=name):
                self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {name} }} }} "
                              f"set_variable = {{ name = {name} value = {sentinel} }} }}", init)
        instruments = flat(block(read(GEN_EFFECTS), "te_tax_gen_init_instruments"))
        for key in KEYS:
            for prefix, sentinel in AI_INSTRUMENT_TOKENS.items():
                name = f"{prefix}{key}"
                with self.subTest(name=name):
                    self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {name} }} }} "
                                  f"set_variable = {{ name = {name} value = {sentinel} }} }}", instruments)

    def test_schema_version_two_is_written_after_the_ai_rows(self):
        init = flat(block(read(STATE), "te_tax_init_country"))
        bump = ("if = { limit = { NOT = { has_variable = te_tax_schema } } "
                "set_variable = { name = te_tax_schema value = 2 } } "
                "else_if = { limit = { var:te_tax_schema < 2 } "
                "set_variable = { name = te_tax_schema value = 2 } }")
        self.assertIn(bump, init)
        self.assertTrue(init.rstrip(" }").endswith(bump.rstrip(" }")), "the version is written last")
        for name in AI_TOKENS:
            with self.subTest(name=name):
                self.assertLess(init.index(f"name = {name}"), init.index(bump))

    def test_every_ai_token_is_copied_by_the_generated_outbreak_copy(self):
        copy = read(GEN_EFFECTS)
        body = block(copy, "te_tax_gen_copy_code")
        names = set(re.findall(r"te_tax_copy_token = \{ NAME = (\w+) \}", body))
        for name in set(AI_TOKENS) | {f"{p}{key}" for p in AI_INSTRUMENT_TOKENS for key in KEYS}:
            with self.subTest(name=name):
                self.assertIn(name, names)

    def test_no_file_removes_an_ai_token(self):
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = read(path.relative_to(ROOT).as_posix())
                with self.subTest(path=path.name):
                    self.assertNotRegex(text, r"remove_variable\s*=\s*(?:\{[^}]*?name\s*=\s*)?te_tax_ai_")

    def test_reset_runs_at_outbreak_repair_and_release(self):
        text = read(CIVIL_WAR)
        call = "te_tax_ai_reset_bill_state = yes"
        # Outbreak: on the rebels, after the copy and the backfill, before the
        # copy writes te_tax_migrated last.
        copy = block(text, "te_tax_copy_code")
        self.assertLess(copy.index("te_tax_init_country = yes"), copy.index(call))
        self.assertLess(copy.index(call), copy.index("name = te_tax_migrated value = 1"))
        # Win repair: in the branch that runs when two codes met, not the skip.
        repair = block(text, "te_tax_repair_after_civil_war")
        self.assertIn(call, repair[:repair.index("else_if")])
        # Release: in the copy branch (a migration writes only absent tokens).
        release = block(text, "te_tax_init_released_country")
        self.assertIn(call, release[:release.index("else_if")])

    def test_the_reset_zeroes_the_bill_state_and_keeps_streaks(self):
        reset = block(read(AI_EFFECTS), "te_tax_ai_reset_bill_state")
        self.assertIn("te_tax_code_on = yes", limit_of(reset[reset.index("if = {") + len("if = {"):]))
        writes = dict(re.findall(r"set_variable = \{ name = (\w+) value = (-?\d+) \}", reset))
        self.assertEqual(writes, RESET)
        for kept in ("te_tax_ai_def_streak", "te_tax_ai_sur_streak", "te_tax_ai_phase", "te_tax_ai_next_month"):
            with self.subTest(kept=kept):
                self.assertNotIn(kept, reset)


class AiValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(AI_VALUES)
        cls.text = read(AI_VALUES)

    def test_tunables_match_the_spec_table(self):
        found = {name: value for name, value in self.parsed.items() if name in TUNABLES}
        self.assertEqual(found, TUNABLES)

    def test_the_ratio_is_income_over_expenses_floored_at_one(self):
        self.assertEqual(flat(block(self.text, "te_tax_ai_ratio")),
                         "value = income divide = { value = total_expenses min = 1 }")

    def test_debt_is_principal_over_credit_and_zero_without_credit(self):
        self.assertEqual(flat(block(self.text, "te_tax_ai_debt")),
                         "value = 0 if = { limit = { credit > 0 } value = principal divide = credit }")

    def test_reserves_are_the_scaled_gold_reserves(self):
        self.assertEqual(flat(block(self.text, "te_tax_ai_reserves")), "value = scaled_gold_reserves")

    def test_the_ratio_pairs_follow_significant_debt(self):
        for which in ("raise", "cut"):
            with self.subTest(which=which):
                self.assertEqual(
                    flat(block(self.text, f"te_tax_ai_{which}_ratio_now")),
                    f"value = te_tax_ai_{which}_ratio if = {{ limit = {{ te_tax_ai_debt >= te_tax_ai_debt_significant }} "
                    f"value = te_tax_ai_{which}_ratio_debt }}")

    def test_bucket_and_cadence_position_use_modulo(self):
        bucket = flat(block(self.text, "te_tax_ai_bucket"))
        self.assertIn("value = var:te_tax_ai_phase modulo = 4", bucket)
        self.assertIn("has_variable = te_tax_ai_phase", bucket)
        cadence = flat(block(self.text, "te_tax_ai_cadence_pos"))
        self.assertIn("value = te_history_month_index subtract = var:te_tax_ai_phase "
                      "modulo = te_tax_ai_cadence_months", cadence)

    def test_the_log_wrappers_are_guarded_reads(self):
        for name, var in (("te_tax_ai_view_tpl", "te_tax_ai_tpl"), ("te_tax_ai_view_def_streak", "te_tax_ai_def_streak"),
                          ("te_tax_ai_view_sur_streak", "te_tax_ai_sur_streak")):
            with self.subTest(name=name):
                self.assertEqual(flat(block(self.text, name)),
                                 f"value = 0 if = {{ limit = {{ has_variable = {var} }} value = var:{var} }}")


class AiTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(AI_TRIGGERS)

    def body(self, name):
        return flat(block(self.text, name))

    def test_can_act_needs_the_rule_the_code_the_ai_and_the_carrier(self):
        self.assertEqual(self.body("te_tax_ai_can_act"),
                         "te_tax_code_on = yes te_tax_code_in_force = yes is_ai = yes "
                         "has_law = law_type:law_te_tax_code")

    def test_emergency_is_default_heavy_debt_or_looming_bankruptcy(self):
        self.assertEqual(self.body("te_tax_ai_emergency"),
                         "OR = { in_default = yes te_tax_ai_debt >= te_tax_ai_emergency_debt "
                         "AND = { taking_loans = yes weeks_until_bankruptcy < te_tax_ai_emergency_weeks } }")

    def test_raise_need_is_a_recorded_deficit_in_the_dead_band_or_a_promised_surplus(self):
        self.assertEqual(self.body("te_tax_ai_raise_need"),
                         "OR = { AND = { te_tax_fisc_rec_deficit = yes te_tax_ai_ratio <= te_tax_ai_raise_ratio_now "
                         "te_tax_ai_reserves < te_tax_ai_reserves_full } te_tax_ai_kind4_in_force = yes }")

    def test_cut_need_is_a_recorded_surplus_at_the_cut_ratio(self):
        self.assertEqual(self.body("te_tax_ai_cut_need"),
                         "te_tax_fisc_rec_surplus = yes te_tax_ai_ratio >= te_tax_ai_cut_ratio_now")

    def test_kind4_in_force_is_a_binding_fiscal_promise_in_any_slot(self):
        body = self.body("te_tax_ai_kind4_in_force")
        for n in gen.OBLIGATION_SLOTS:
            with self.subTest(slot=n):
                self.assertIn(f"AND = {{ te_tax_obl_binding = {{ N = {n} }} var:te_tax_o{n}_kind = 4 }}", body)

    def test_initiative_is_due_on_the_phase_of_the_cadence(self):
        self.assertEqual(self.body("te_tax_ai_initiative_due"),
                         "has_variable = te_tax_ai_phase var:te_tax_ai_phase >= 0 te_tax_ai_cadence_pos = 0")

    def test_management_is_a_bill_a_held_package_or_a_promise_in_force(self):
        body = self.body("te_tax_ai_has_management")
        self.assertIn("te_tax_bill_active = yes", body)
        for slot in ("a", "b"):
            with self.subTest(slot=slot):
                self.assertIn(f"AND = {{ has_variable = te_tax_p{slot}_on var:te_tax_p{slot}_on = 1 "
                              f"OR = {{ var:te_tax_p{slot}_state = 2 var:te_tax_p{slot}_state = 3 }} }}", body)
        for n in gen.OBLIGATION_SLOTS:
            with self.subTest(slot=n):
                self.assertIn(f"te_tax_obl_active = {{ N = {n} }}", body)

    def test_a_step_is_due_for_an_ai_that_can_act_with_something_due(self):
        self.assertEqual(self.body("te_tax_ai_step_due"),
                         "te_tax_ai_can_act = yes OR = { te_tax_ai_initiative_due = yes te_tax_ai_emergency = yes "
                         "te_tax_ai_has_management = yes }")


class AiStreakTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(AI_EFFECTS)
        cls.update = flat(block(cls.text, "te_tax_ai_update_streaks"))

    def test_streaks_run_for_every_migrated_country(self):
        self.assertTrue(self.update.startswith("if = { limit = { te_tax_code_on = yes has_variable = te_tax_schema }"))
        self.assertNotIn("is_ai", self.update)

    def test_the_deficit_streak_counts_recorded_deficits_and_resets(self):
        self.assertIn("if = { limit = { te_tax_fisc_rec_deficit = yes } "
                      "change_variable = { name = te_tax_ai_def_streak add = 1 } } "
                      "else = { set_variable = { name = te_tax_ai_def_streak value = 0 } }", self.update)

    def test_the_surplus_streak_needs_the_cut_ratio(self):
        self.assertIn("if = { limit = { te_tax_fisc_rec_surplus = yes te_tax_ai_ratio >= te_tax_ai_cut_ratio_now } "
                      "change_variable = { name = te_tax_ai_sur_streak add = 1 } } "
                      "else = { set_variable = { name = te_tax_ai_sur_streak value = 0 } }", self.update)

    def test_the_phase_is_drawn_once_while_it_holds_the_sentinel(self):
        self.assertIn("if = { limit = { var:te_tax_ai_phase < 0 } te_tax_ai_phase_draw = yes }", self.update)
        self.assertEqual(self.text.count("te_tax_ai_phase_draw = yes"), 1)

    def test_the_draw_is_the_un_stored_random_form_over_twelve_months(self):
        # un_vote_ai_draws (un_dossier_effects.txt): random_list of equal
        # weights, each branch a literal set_variable.
        draw = flat(block(self.text, "te_tax_ai_phase_draw"))
        branches = re.findall(r"(\d+) = \{ set_variable = \{ name = te_tax_ai_phase value = (\d+) \} \}", draw)
        self.assertTrue(draw.startswith("random_list = {"))
        self.assertEqual(sorted(int(value) for _, value in branches), list(range(12)))
        self.assertEqual({weight for weight, _ in branches}, {"1"})
        self.assertEqual(draw.count("set_variable"), 12)


class AiDispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai = read(AI_EFFECTS)
        cls.dispatch = flat(block(cls.ai, "te_tax_ai_dispatch"))

    def test_rule_1b_follows_the_fiscal_record_and_precedes_transitions(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        claim = body.index("set_variable = { name = te_tax_last_month value = var:te_tax_now }")
        record = body.index("te_tax_record_fiscal_month = yes")
        customs = body.index("te_tax_customs_revalidate = yes")
        streaks = body.index("te_tax_ai_update_streaks = yes")
        dispatch = body.index("te_tax_ai_dispatch = yes")
        sunset = body.index("te_tax_gen_sunset_wage = yes")
        self.assertLess(claim, record)
        self.assertLess(record, customs)
        self.assertLess(customs, streaks)
        self.assertLess(streaks, dispatch)
        self.assertLess(dispatch, sunset)
        self.assertEqual(body.count("te_tax_ai_"), 2, "the processor only updates the streaks and dispatches")
        self.assertNotIn("te_tax_ai_", block(read(SCHEDULE), "te_tax_watchdog_month"))

    def test_dispatch_is_ai_only_and_uses_literal_bucket_days(self):
        self.assertTrue(self.dispatch.startswith(
            "if = { limit = { te_tax_code_on = yes is_ai = yes te_tax_ai_step_due = yes }"))
        days = set(re.findall(r"id = te_tax\.8 days = (\d+)", self.dispatch))
        self.assertEqual(days, {"1", "5", "12", "19", "26"})
        self.assertEqual(self.dispatch.count("trigger_event"), 5)

    def test_a_retry_raises_the_step_tomorrow_and_clears_itself(self):
        self.assertIn("if = { limit = { var:te_tax_ai_retry = 1 } "
                      "set_variable = { name = te_tax_ai_retry value = 0 } "
                      "trigger_event = { id = te_tax.8 days = 1 } }", self.dispatch)

    def test_the_bucket_picks_the_day(self):
        for bucket, days in ((0, 5), (1, 12), (2, 19)):
            with self.subTest(bucket=bucket):
                self.assertIn(f"else_if = {{ limit = {{ te_tax_ai_bucket = {bucket} }} "
                              f"trigger_event = {{ id = te_tax.8 days = {days} }} }}", self.dispatch)
        self.assertIn("else = { trigger_event = { id = te_tax.8 days = 26 } }", self.dispatch)

    def test_the_step_event_rechecks_rule_and_ai(self):
        event = load(EVENTS)["te_tax.8"]
        self.assertEqual(event["type"], "country_event")
        self.assertEqual(event["hidden"], "yes")
        self.assertEqual(event["trigger"], {"te_tax_ai_can_act": "yes"})
        self.assertEqual(event["immediate"], {"te_tax_ai_step": "yes"})

    def test_te_tax_8_is_raised_only_by_the_dispatch_the_chain_and_the_console(self):
        mentions = set()
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                if re.search(r"\bte_tax\.8\b", read(path.relative_to(ROOT).as_posix())):
                    mentions.add(path.name)
        self.assertLessEqual(mentions, {"te_tax_ai_effects.txt", "te_tax_internal_events.txt",
                                        "te_tax_debug_events.txt"})
        self.assertLessEqual({"te_tax_ai_effects.txt", "te_tax_internal_events.txt"}, mentions)

    def test_the_step_is_called_only_by_te_tax_8(self):
        callers = []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                if "te_tax_ai_step = yes" in read(path.relative_to(ROOT).as_posix()):
                    callers.append(path.name)
        self.assertEqual(callers, ["te_tax_internal_events.txt"])

    def test_the_step_stub_logs_its_signals(self):
        step = flat(block(self.ai, "te_tax_ai_step"))
        self.assertTrue(step.startswith("if = { limit = { te_tax_code_on = yes } "))
        self.assertIn("te_tax_ai_log_step = yes", step)


class AiLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(AI_EFFECTS)
        cls.values = set(re.findall(r"(?m)^(\w+) = ", read(AI_VALUES)))

    def lines(self, name):
        return re.findall(r'debug_log = "([^"]*)"', block(self.text, name))

    def check(self, name, head):
        lines = self.lines(name)
        self.assertEqual(len(lines), 1, name)
        line = lines[0]
        self.assertTrue(line.startswith(f"TE_TAX {head} "), line[:60])
        fields = re.findall(r"(\w+)=\[SCOPE\.ScriptValue\('(\w+)'\)\|\d\]", line)
        self.assertEqual([field for field, _ in fields][:len(LOG_FIELDS)], list(LOG_FIELDS))
        for _, value in fields[:len(LOG_FIELDS)]:
            self.assertIn(value, self.values)
        self.assertTrue(line.endswith(STAMP), line[-80:])
        self.assertNotIn("$", line)

    def test_one_effect_per_verb(self):
        for verb, head in LOG_VERBS.items():
            with self.subTest(verb=verb):
                self.check(f"te_tax_ai_log_{verb}", head)

    def test_one_effect_per_withdrawal_and_no_viable_reason(self):
        for reason in LOG_REASONS:
            for kind in ("withdrawn", "no_viable"):
                with self.subTest(kind=kind, reason=reason):
                    self.check(f"te_tax_ai_log_{kind}_{reason}", f"ai_{kind} reason={reason}")


class AiGateTest(unittest.TestCase):
    def test_every_ai_trigger_and_effect_entry_starts_from_the_rule(self):
        self.assertIn("te_tax_code_on = yes", block(read(AI_TRIGGERS), "te_tax_ai_can_act"))
        effects_text = read(AI_EFFECTS)
        for name in ("te_tax_ai_update_streaks", "te_tax_ai_dispatch", "te_tax_ai_step", "te_tax_ai_reset_bill_state"):
            with self.subTest(name=name):
                head = flat(block(effects_text, name))[:120]
                self.assertRegex(head, r"^if = \{ limit = \{ te_tax_code_on = yes")
        for path in AI_FILES:
            with self.subTest(path=path):
                self.assertNotRegex(read(path), r"NOT = \{\s*te_tax_code_on")

    def test_no_native_setter_in_the_ai_layer(self):
        for path in AI_FILES:
            text = read(path)
            for setter in NATIVE_SETTERS:
                with self.subTest(path=path, setter=setter):
                    self.assertNotRegex(text, rf"\b{setter}\b")

    def test_is_ai_appears_only_in_the_ai_layer_and_player_log_gates(self):
        found = {}
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("te_tax_*.txt")):
                if path.name.startswith("te_tax_ai_"):
                    continue
                text = PLAYER_LOG_GATE.sub("", flat(read(path.relative_to(ROOT).as_posix())))
                count = len(re.findall(r"\bis_ai\b", text))
                if count:
                    found[path.name] = count
        self.assertEqual(found, PRE_EXISTING_IS_AI)

    def test_command_logs_are_player_only_unless_a_transition_reaches_them(self):
        defined = effects()
        bodies = log_bodies()
        reached = closure(transition_roots(defined), defined) & set(bodies)
        self.assertEqual(reached, set(TRANSITION_LOGGED), "the allowlist is the transitions' closure")
        for name, body in sorted(bodies.items()):
            for match in re.finditer(r"debug_log = ", body):
                with self.subTest(effect=name, at=match.start()):
                    if name in TRANSITION_LOGGED:
                        self.assertFalse(player_gated(body, match.start()), "a transition line is for every country")
                    else:
                        self.assertTrue(player_gated(body, match.start()), "a command line is for players only")


class AiFileTest(unittest.TestCase):
    def test_files_have_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in AI_FILES:
            with self.subTest(path=path):
                raw = (ROOT / path).read_bytes()
                text = raw.decode("utf-8-sig")
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)

    def test_schema_doc_has_the_ai_section_and_rule_1b(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        schema = doc.split("\n## Schema\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("### AI legislation", schema)
        rules = doc.split("### Processor rules", 1)[1].split("\n### ", 1)[0]
        self.assertIn("1b.", rules)
        self.assertIn("te_tax_ai_dispatch", rules)
        self.assertIn("\n## AI legislation\n", doc)


if __name__ == "__main__":
    unittest.main()
