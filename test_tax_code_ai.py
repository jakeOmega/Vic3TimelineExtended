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

Task 19 gives the step its first work (spec §2.4 steps 1-2, §2.8):

* held packages: a conflicting one is released, a missed one rescheduled when
  it may be, else released, each through its command behind its own trigger;
* promises: at most one at risk a step, slots in order; a kind-1 promise is
  enacted at exactly its target (the one owner-approved institution setter,
  generated, only here), any other is renegotiated through the command;
  never a pending or bound one;
* every country logs obl_deadline met or unmet once per promise, when its
  delivery phase ends; the AI logs ai_obl_enacted;
* the default strategy weights an institution an AI owes, and no political
  agenda strategy is touched.

Task 20 manages the open bill (spec §2.4 step 3, §2.7, §2.10):

* a bill whose due month has come is rescheduled first, then: pass; wait a
  day past the pin when only the native tax level's legitimacy blocks it;
  accept the best offer in a capped chain; force it through in an emergency;
  withdraw it, hopeless or out of patience, with a reason;
* each through its command inside its own trigger, the reverse-window marks
  and the cooldown written before the bill record closes, and the bill state
  reset after; ai_no_viable once per episode.

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
OBLIGATIONS = OBLIGATION
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
OBL_TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
STRATEGY = "common/ai_strategies/edited_default_strategy.txt"
DEFINES = "common/defines/extra_defines.txt"
LEDGER = "docs/testing/tax-code-capability-ledger.md"
GENERATOR = "scripts/generators/gen_tax_code.py"

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
    "waiting_legitimacy_native_level": "ai_waiting reason=legitimacy_native_level",
    # Task 20: the bill's own due month moved on (a package's is ai_rescheduled).
    "bill_rescheduled": "ai_bill_rescheduled",
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
# Generated effects whose whole body is an is_ai branch between two literal
# debug_log lines (Task 19): the deadline line, written for every country,
# prints ai=yes or ai=no, and debug_log cannot print is_ai itself. The only
# is_ai reads outside the AI files and the player log gates; each body must be
# exactly AI_FLAG_LOG, so the allowance cannot widen.
AI_FLAG_LOG_FAMILIES = {
    "te_tax_gen_obl_log_met_": "obl_deadline result=met, before the delivered promise starts maintenance",
    "te_tax_gen_obl_log_unmet_": "obl_deadline result=unmet, before the deadline breach",
}
AI_FLAG_LOG = re.compile(r'if = \{ limit = \{ is_ai = yes \} debug_log = "[^"]*" \} '
                         r'else = \{ debug_log = "[^"]*" \}')
# The levels te_tax_gen_ai_enact_<o> can set, 1 to the mod's
# MAX_INSTITUTION_INVESTMENT (common/defines/extra_defines.txt).
MAX_INSTITUTION_LEVEL = 9
INSTITUTIONS = {1: "institution_schools", 2: "institution_health_system", 3: "institution_social_security"}
# The promise lines' fields and the slot view each prints (te_tax_view_o<o>_<view>): spec §2.8's
# `level`, the measure the verifier reads, is te_tax_view_o<o>_measure (fix round 1).
DEADLINE_FIELDS = (("kind", "kind"), ("arg", "arg"), ("target", "target"), ("level", "measure"),
                   ("baseline", "baseline"), ("deadline", "deadline"))
GRACE = {1: 1, 2: 3, 3: 1, 4: 3}
# Task 20: the reasons an AI bill is withdrawn for, in the order te_tax_ai_withdraw tests them
# (spec §2.4 step 3); `draft` (an introduction refused) is Task 21's and has no bill to withdraw.
WITHDRAW_REASONS = ("legitimacy", "slots", "authority", "support", "patience")
# The AI's template codes (te_tax_ai_tpl, Task 21): raises, the cut, none (a bill it did not introduce).
RAISE_TEMPLATES, CUT_TEMPLATE = (1, 2, 3, 6), 5
# The clout ranking's value for a group the country lacks, or a marginal one: after every other.
RANK_LAST = 8


def promise_fields(o):
    return " ".join(f"{field}=[SCOPE.ScriptValue('te_tax_view_o{o}_{view}')|0]" for field, view in DEADLINE_FIELDS)


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
    # A bare `if =`, never `else_if =`.
    if brace < 0 or not re.search(r"(?<!\w)if =$", text[:brace].rstrip()):
        return False
    return limit_of(text[brace + 1:close(text, brace)]).strip() == "is_ai = no"


def strip_ai_flag_logs(text):
    """`text` without the AI_FLAG_LOG_FAMILIES blocks, each asserted to be
    exactly an is_ai branch between two debug_log lines."""
    pattern = r"(?m)^((?:" + "|".join(AI_FLAG_LOG_FAMILIES) + r")\d+) = \{"
    while True:
        match = re.search(pattern, text)
        if match is None:
            return text
        end = close(text, match.end() - 1)
        body = flat(text[match.end():end])
        if not AI_FLAG_LOG.fullmatch(body):
            raise AssertionError(f"{match.group(1)} is not an is_ai branch between two debug_log lines: {body[:120]}")
        text = text[:match.start()] + text[end + 1:]


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

    def test_the_step_manages_packages_then_promises_when_the_ai_can_act(self):
        step = flat(block(self.ai, "te_tax_ai_step"))
        self.assertTrue(step.startswith("if = { limit = { te_tax_code_on = yes te_tax_ai_can_act = yes } "), step[:90])
        packages = step.index("te_tax_ai_manage_packages = yes")
        promises = step.index("te_tax_ai_manage_promises = yes")
        self.assertLess(packages, promises)
        # The signals line is the console's (Task 22), no longer the step's.
        self.assertNotIn("te_tax_ai_log_step", step)


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
        for name in ("te_tax_ai_update_streaks", "te_tax_ai_dispatch", "te_tax_ai_step", "te_tax_ai_reset_bill_state",
                     "te_tax_ai_manage_packages", "te_tax_ai_manage_promises", "te_tax_ai_manage_bill",
                     "te_tax_ai_withdraw", *(f"te_tax_ai_withdraw_{reason}" for reason in WITHDRAW_REASONS)):
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
                text = PLAYER_LOG_GATE.sub("", flat(strip_ai_flag_logs(read(path.relative_to(ROOT).as_posix()))))
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

    def test_player_gated_accepts_a_bare_if_only(self):
        for text, expected in (('if = { limit = { is_ai = no } debug_log = "x" }', True),
                               ('else_if = { limit = { is_ai = no } debug_log = "x" }', False),
                               ('if = { limit = { is_ai = yes } debug_log = "x" }', False)):
            with self.subTest(text=text[:20]):
                self.assertEqual(player_gated(text, text.index("debug_log")), expected)

    def test_the_ai_flag_logs_are_the_only_generated_is_ai_reads(self):
        text = read(GEN_EFFECTS)
        for prefix in AI_FLAG_LOG_FAMILIES:
            for n in gen.OBLIGATION_SLOTS:
                with self.subTest(effect=f"{prefix}{n}"):
                    self.assertRegex(flat(block(text, f"{prefix}{n}")), AI_FLAG_LOG)
        rest = PLAYER_LOG_GATE.sub("", flat(strip_ai_flag_logs(text)))
        self.assertNotRegex(rest, r"\bis_ai\b")

    def test_the_store_lines_are_player_only_and_reached_only_by_the_pass(self):
        # te_tax_store_package and te_tax_gen_store_<s> run only from te_tax_pass_into
        # (Pass and Force through), never from a transition.
        defined = effects()
        reached = closure(transition_roots(defined), defined)
        bodies = {"te_tax_store_package": block(read(SCHEDULE), "te_tax_store_package")}
        bodies |= {f"te_tax_gen_store_{s}": block(read(GEN_EFFECTS), f"te_tax_gen_store_{s}") for s in gen.SLOTS}
        for name, body in bodies.items():
            with self.subTest(effect=name):
                self.assertNotIn(name, reached)
                found = list(re.finditer(r"debug_log = ", body))
                self.assertTrue(found)
                for match in found:
                    self.assertTrue(player_gated(body, match.start()))

    def test_every_command_the_ai_calls_sits_inside_its_own_trigger(self):
        text = read(AI_EFFECTS)
        calls = list(re.finditer(r"\bte_tax_cmd_(\w+) = (\{[^{}]*\}|yes)", text))
        self.assertTrue(calls)
        for match in calls:
            with self.subTest(call=match.group(0)):
                brace = enclosing_brace(text, match.start())
                self.assertRegex(text[:brace].rstrip(), r"(?<!\w)(?:else_)?if =$")
                self.assertEqual(flat(limit_of(text[brace + 1:close(text, brace)])),
                                 f"te_tax_can_{match.group(1)} = {flat(match.group(2))}")


class AiPromiseTest(unittest.TestCase):
    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.gen = read(GEN_EFFECTS)

    def test_held_packages_release_conflicts_and_reschedule_missed_when_valid(self):
        body = block(self.ai, "te_tax_ai_manage_packages")
        for slot in ("a", "b"):
            self.assertIn(f"te_tax_can_package_release = {{ SLOT = {slot} }}", body)
            self.assertIn(f"te_tax_can_package_reschedule = {{ SLOT = {slot} }}", body)

    def test_enactment_is_kind_1_only_and_never_pending_or_bound(self):
        body = block(self.ai, "te_tax_ai_manage_promises")
        self.assertIn("te_tax_ai_promise_at_risk", body)
        risk = block(read(AI_TRIGGERS), "te_tax_ai_promise_at_risk")
        self.assertNotRegex(risk, r"_state = [17]\b")
        for o in (1, 2, 3, 4):
            enact = block(self.gen, f"te_tax_gen_ai_enact_{o}")
            self.assertIn("set_institution_investment_level", enact)
            self.assertIn(f"var:te_tax_o{o}_kind = 1", enact)

    def test_enactment_targets_exactly_the_promised_level(self):
        enact = block(self.gen, "te_tax_gen_ai_enact_1")
        for level in range(1, 10):
            self.assertIn(f"var:te_tax_o1_target = {level}", enact)
            self.assertIn(f"level = {level}", enact)

    def test_balance_promises_are_renegotiated_through_the_command(self):
        body = block(self.ai, "te_tax_ai_manage_promises")
        self.assertIn("te_tax_can_obl_renegotiate", body)
        self.assertIn("te_tax_cmd_obl_renegotiate", body)

    def test_enactment_appears_only_in_the_ai_layer(self):
        import pathlib
        for f in pathlib.Path(__file__).parent.glob("common/**/*.txt"):
            text = f.read_text(encoding="utf-8-sig")
            if "set_institution_investment_level" in text and "te_tax" in f.name:
                self.assertIn(f.name, {"te_tax_generated_effects.txt"}, f.name)

    # -- beyond the brief's sample ------------------------------------------

    def test_packages_resolve_slot_a_then_b_each_through_its_commands(self):
        body = flat(block(self.ai, "te_tax_ai_manage_packages"))
        self.assertTrue(body.startswith("if = { limit = { te_tax_code_on = yes te_tax_code_in_force = yes } "))
        for slot in ("a", "b"):
            with self.subTest(slot=slot):
                self.assertIn(f"if = {{ limit = {{ te_tax_can_package_reschedule = {{ SLOT = {slot} }} }} "
                              f"te_tax_cmd_package_reschedule = {{ SLOT = {slot} }} te_tax_ai_log_rescheduled = yes }} "
                              f"else_if = {{ limit = {{ te_tax_can_package_release = {{ SLOT = {slot} }} }} "
                              f"te_tax_cmd_package_release = {{ SLOT = {slot} }} te_tax_ai_log_released = yes }}", body)
        self.assertLess(body.index("SLOT = a"), body.index("SLOT = b"))

    def test_at_risk_is_the_next_check_breaching_a_promise_in_force(self):
        # Spec §2.4 step 2: only a promise the next monthly check would breach. A delivering
        # kind-1 promise in a bureaucracy deficit is paused by it, and a kind-4 one a surplus
        # month short of its streak is delivered by it; a maintaining one breaches only one
        # failing check short of its grace (fix round 1).
        self.assertEqual(
            flat(block(read(AI_TRIGGERS), "te_tax_ai_promise_at_risk")),
            "has_variable = te_tax_o$N$_on var:te_tax_o$N$_on = 1 OR = { "
            "AND = { var:te_tax_o$N$_state = 2 "
            "OR = { AND = { var:te_tax_o$N$_kind = 1 var:te_tax_o$N$_deadline <= te_tax_ai_enact_by_month } "
            "AND = { NOT = { var:te_tax_o$N$_kind = 1 } var:te_tax_o$N$_deadline <= te_tax_ai_next_check_month } } "
            "NOT = { te_tax_obl_delivered = { N = $N$ } } "
            "NOT = { AND = { var:te_tax_o$N$_kind = 1 bureaucracy < 0 } } "
            "NOT = { AND = { var:te_tax_o$N$_kind = 4 var:te_tax_o$N$_streak >= te_tax_ai_surplus_streak_last "
            "net_fixed_income > 0 } } } "
            "AND = { var:te_tax_o$N$_state = 3 NOT = { te_tax_obl_holds = { N = $N$ } } "
            "te_tax_ai_grace_next = { N = $N$ } } }")

    def test_the_deficit_pause_matches_the_monthly_check(self):
        # te_tax_obl_check_one pauses exactly this case before testing the deadline.
        check = flat(block(read(OBLIGATIONS), "te_tax_obl_check_one"))
        self.assertIn("else_if = { limit = { var:te_tax_o$N$_kind = 1 bureaucracy < 0 } "
                      "change_variable = { name = te_tax_o$N$_deadline add = 1 }", check)
        # ... and counts the kind-4 streak before testing delivery against te_tax_obl_surplus_months.
        self.assertLess(check.index("te_tax_o$N$_streak add = 1"), check.index("te_tax_obl_delivered"))
        self.assertEqual(flat(block(read(AI_VALUES), "te_tax_ai_surplus_streak_last")),
                         "value = te_tax_obl_surplus_months subtract = 1")

    def test_a_maintained_promise_is_at_risk_one_failing_check_short_of_its_grace(self):
        body = flat(block(read(AI_TRIGGERS), "te_tax_ai_grace_next"))
        self.assertEqual(body, "OR = { " + " ".join(
            f"AND = {{ var:te_tax_o$N$_kind = {kind} var:te_tax_o$N$_fails >= te_tax_ai_grace_short_{kind} }}"
            for kind in GRACE) + " }")
        self.assertNotIn("trigger_if", body)
        values = read(AI_VALUES)
        obligation_values = load("common/script_values/te_tax_obligation_values.txt")
        for kind, grace in GRACE.items():
            with self.subTest(kind=kind):
                self.assertEqual(flat(block(values, f"te_tax_ai_grace_short_{kind}")),
                                 f"value = te_tax_obl_grace_{kind} subtract = 1")
                self.assertEqual(obligation_values[f"te_tax_obl_grace_{kind}"], str(grace))

    def test_the_lead_applies_to_enactment_and_the_next_check_to_the_rest(self):
        values = read(AI_VALUES)
        self.assertEqual(flat(block(values, "te_tax_ai_now")),
                         "value = te_history_month_index if = { limit = { has_variable = te_tax_now "
                         "var:te_tax_now >= 0 } value = var:te_tax_now }")
        self.assertEqual(flat(block(values, "te_tax_ai_next_check_month")), "value = te_tax_ai_now add = 1")
        self.assertEqual(flat(block(values, "te_tax_ai_enact_by_month")),
                         "value = te_tax_ai_now add = te_tax_ai_enact_lead_months")

    def test_one_promise_a_step_in_slot_order(self):
        body = flat(block(self.ai, "te_tax_ai_manage_promises"))
        self.assertTrue(body.startswith("if = { limit = { te_tax_code_on = yes te_tax_code_in_force = yes } "))
        for n in gen.OBLIGATION_SLOTS:
            opener = "if" if n == 1 else "else_if"
            with self.subTest(slot=n):
                self.assertIn(
                    f"{opener} = {{ limit = {{ te_tax_ai_promise_at_risk = {{ N = {n} }} }} "
                    f"if = {{ limit = {{ te_tax_ai_can_enact = {{ N = {n} }} }} "
                    f"te_tax_gen_ai_log_enacted_{n} = yes te_tax_gen_ai_enact_{n} = yes }} "
                    f"else_if = {{ limit = {{ te_tax_can_obl_renegotiate = {{ N = {n} }} }} "
                    f"te_tax_gen_ai_log_renegotiated_{n} = yes te_tax_cmd_obl_renegotiate = {{ N = {n} }} }} }}", body)
        # Each line is written first: the setter's result is not assumed visible later in the
        # block, and the renegotiation frees the slot, after which its views read nothing.
        self.assertNotIn("te_tax_ai_log_renegotiated", body)
        positions = [body.index(f"te_tax_ai_promise_at_risk = {{ N = {n} }}") for n in gen.OBLIGATION_SLOTS]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(body.count("te_tax_ai_promise_at_risk"), len(gen.OBLIGATION_SLOTS))

    def test_only_an_enactable_kind_1_promise_is_enacted(self):
        body = flat(block(read(AI_TRIGGERS), "te_tax_ai_can_enact"))
        self.assertTrue(body.startswith("var:te_tax_o$N$_kind = 1 var:te_tax_o$N$_target >= 1 "
                                        "var:te_tax_o$N$_target <= te_tax_ai_enact_level_max OR = { "), body[:120])
        for arg, institution in INSTITUTIONS.items():
            with self.subTest(arg=arg):
                self.assertIn(f"AND = {{ var:te_tax_o$N$_arg = {arg} has_institution = {institution} "
                              f"var:te_tax_o$N$_target <= te_tax_obl_inst_cap_{arg} "
                              f"var:te_tax_o$N$_target > te_tax_obl_inst_level_{arg} }}", body)

    def test_the_level_bound_is_the_mods_maximum_and_the_generators(self):
        self.assertEqual(load(AI_VALUES)["te_tax_ai_enact_level_max"], str(MAX_INSTITUTION_LEVEL))
        self.assertEqual(gen.OBL_MAX_INSTITUTION_LEVEL, MAX_INSTITUTION_LEVEL)
        self.assertRegex(read(DEFINES), rf"\bMAX_INSTITUTION_INVESTMENT = {MAX_INSTITUTION_LEVEL}\b")

    def test_each_enactment_sets_exactly_the_target_behind_the_institution(self):
        for o in gen.OBLIGATION_SLOTS:
            body = flat(block(self.gen, f"te_tax_gen_ai_enact_{o}"))
            for index, (arg, institution) in enumerate(INSTITUTIONS.items()):
                opener = "if" if index == 0 else "else_if"
                levels = " ".join(
                    f"{'if' if level == 1 else 'else_if'} = {{ limit = {{ var:te_tax_o{o}_target = {level} }} "
                    f"set_institution_investment_level = {{ institution = {institution} level = {level} }} }}"
                    for level in range(1, MAX_INSTITUTION_LEVEL + 1))
                with self.subTest(slot=o, arg=arg):
                    self.assertIn(f"{opener} = {{ limit = {{ has_variable = te_tax_o{o}_on var:te_tax_o{o}_on = 1 "
                                  f"var:te_tax_o{o}_kind = 1 var:te_tax_o{o}_arg = {arg} "
                                  f"has_institution = {institution} }} {levels} }}", body)
            self.assertEqual(body.count("set_institution_investment_level"), MAX_INSTITUTION_LEVEL * len(INSTITUTIONS))
            self.assertNotIn("change_institution_investment_level", body)

    def test_enactment_is_called_only_by_the_promise_manager(self):
        callers = {}
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = read(path.relative_to(ROOT).as_posix())
                for match in re.finditer(r"\bte_tax_gen_ai_enact_\d+ = yes", text):
                    callers.setdefault(path.name, 0)
                    callers[path.name] += 1
        self.assertEqual(callers, {"te_tax_ai_effects.txt": len(gen.OBLIGATION_SLOTS)})
        for n in gen.OBLIGATION_SLOTS:
            self.assertIn(f"te_tax_gen_ai_enact_{n} = yes", block(self.ai, "te_tax_ai_manage_promises"))
        managers = [path.name for path in sorted((ROOT / "common").rglob("*.txt"))
                    if "te_tax_ai_manage_promises = yes" in read(path.relative_to(ROOT).as_posix())]
        self.assertEqual(managers, ["te_tax_ai_effects.txt"])
        self.assertIn("te_tax_ai_manage_promises = yes", block(self.ai, "te_tax_ai_step"))

    def test_the_enactment_and_renegotiation_lines_name_the_promise_and_the_signals(self):
        views = set(re.findall(r"(?m)^(\w+) = ", read(GEN_VALUES)))
        step = re.findall(r'debug_log = "([^"]*)"', block(self.ai, "te_tax_ai_log_step"))[0]
        signals = step[len("TE_TAX ai_step "):]
        for family, head in (("enacted", "ai_obl_enacted"), ("renegotiated", "ai_renegotiated")):
            for o in gen.OBLIGATION_SLOTS:
                body = block(self.gen, f"te_tax_gen_ai_log_{family}_{o}")
                with self.subTest(family=family, slot=o):
                    self.assertEqual(re.findall(r'debug_log = "([^"]*)"', body),
                                     [f"TE_TAX {head} slot={o} {promise_fields(o)} {signals}"])
                    for _, view in DEADLINE_FIELDS:
                        self.assertIn(f"te_tax_view_o{o}_{view}", views)
                    self.assertNotIn("is_ai", body)

    def test_the_bare_renegotiation_line_is_gone(self):
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("te_tax_*.txt")):
                with self.subTest(path=path.name):
                    self.assertNotIn("te_tax_ai_log_renegotiated", read(path.relative_to(ROOT).as_posix()))

    def test_the_measure_is_what_the_verifier_reads(self):
        values = read(GEN_VALUES)
        for o in gen.OBLIGATION_SLOTS:
            inst = " ".join(f"{'if' if arg == 1 else 'else_if'} = {{ limit = {{ var:te_tax_o{o}_kind = 1 "
                            f"has_variable = te_tax_o{o}_arg var:te_tax_o{o}_arg = {arg} }} "
                            f"value = te_tax_obl_inst_level_{arg} }}"
                            for arg in INSTITUTIONS)
            with self.subTest(slot=o):
                self.assertEqual(
                    flat(block(values, f"te_tax_view_o{o}_measure")),
                    f"value = 0 if = {{ limit = {{ has_variable = te_tax_o{o}_on var:te_tax_o{o}_on = 1 "
                    f"has_variable = te_tax_o{o}_kind }} {inst} "
                    f"else_if = {{ limit = {{ var:te_tax_o{o}_kind = 2 bureaucracy >= 0 }} value = 1 }} "
                    f"else_if = {{ limit = {{ var:te_tax_o{o}_kind = 3 te_tax_obl_wages_met = {{ N = {o} }} }} value = 1 }} "
                    f"else_if = {{ limit = {{ var:te_tax_o{o}_kind = 4 has_variable = te_tax_o{o}_streak }} "
                    f"value = var:te_tax_o{o}_streak }} }}")
        # The verifier's own reads (te_tax_obl_holds, te_tax_obl_delivered).
        holds = flat(block(read(OBL_TRIGGERS), "te_tax_obl_holds"))
        for read_ in ("bureaucracy >= 0", "te_tax_obl_wages_met = { N = $N$ }", "te_tax_obl_inst_met_1 = { N = $N$ }"):
            self.assertIn(read_, holds)
        self.assertIn("var:te_tax_o$N$_streak >= te_tax_obl_surplus_months",
                      flat(block(read(OBL_TRIGGERS), "te_tax_obl_delivered")))


class DeadlineLogTest(unittest.TestCase):
    def test_met_and_unmet_lines_once_per_promise(self):
        check = block(read(OBLIGATIONS), "te_tax_obl_check_one")
        self.assertEqual(check.count("te_tax_gen_obl_log_met_$N$ = yes"), 1)
        self.assertEqual(check.count("te_tax_gen_obl_log_unmet_$N$ = yes"), 1)
        self.assertLess(check.index("te_tax_gen_obl_log_met_$N$"), check.index("te_tax_obl_begin_maintenance"))

    def test_the_log_line_prints_views_not_params(self):
        gen_text = read(GEN_EFFECTS)
        for o in (1, 2, 3, 4):
            line = block(gen_text, f"te_tax_gen_obl_log_unmet_{o}")
            self.assertIn("TE_TAX obl_deadline result=unmet", line)
            self.assertIn(f"te_tax_view_o{o}_kind", line)
            self.assertNotIn("$", line)

    # -- beyond the brief's sample ------------------------------------------

    def test_met_at_delivery_and_unmet_at_the_deadline_breach_only(self):
        check = flat(block(read(OBLIGATIONS), "te_tax_obl_check_one"))
        self.assertIn("if = { limit = { te_tax_obl_delivered = { N = $N$ } } te_tax_gen_obl_log_met_$N$ = yes "
                      "te_tax_obl_begin_maintenance = { N = $N$ } }", check)
        self.assertIn("else_if = { limit = { var:te_tax_o$N$_deadline <= var:te_tax_now } "
                      "te_tax_gen_obl_log_unmet_$N$ = yes te_tax_obl_breach = { N = $N$ } }", check)
        # The maintenance breach (grace reached) writes no deadline line.
        maintaining = check[check.index("var:te_tax_o$N$_state = 3"):]
        self.assertNotIn("te_tax_gen_obl_log_", maintaining)
        self.assertEqual(read(OBLIGATIONS).count("te_tax_gen_obl_log_"), 2)

    def test_each_slot_writes_one_line_with_its_views_and_the_ai_flag(self):
        gen_text = read(GEN_EFFECTS)
        for o in gen.OBLIGATION_SLOTS:
            for result in ("met", "unmet"):
                head = f"TE_TAX obl_deadline result={result} slot={o} {promise_fields(o)}"
                with self.subTest(slot=o, result=result):
                    self.assertEqual(
                        flat(block(gen_text, f"te_tax_gen_obl_log_{result}_{o}")),
                        f'if = {{ limit = {{ is_ai = yes }} debug_log = "{head} ai=yes; {STAMP}" }} '
                        f'else = {{ debug_log = "{head} ai=no; {STAMP}" }}')

    def test_the_log_effects_are_called_only_by_the_monthly_check(self):
        callers = set()
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                if re.search(r"\bte_tax_gen_obl_log_(?:met|unmet)_", read(path.relative_to(ROOT).as_posix())):
                    callers.add(path.name)
        self.assertEqual(callers, {"te_tax_obligation_effects.txt", "te_tax_generated_effects.txt"})


class InstitutionHookTest(unittest.TestCase):
    def test_hook_on_schools_and_health_only_and_rule_gated(self):
        text = read(STRATEGY)
        self.assertIn("te_tax_ai_owes_institution = { ARG = 1 }", text)
        self.assertIn("te_tax_ai_owes_institution = { ARG = 2 }", text)
        owes = block(read(AI_TRIGGERS), "te_tax_ai_owes_institution")
        self.assertIn("te_tax_code_on = yes", owes)
        for o in (1, 2, 3, 4):
            self.assertIn(f"var:te_tax_o{o}_kind = 1", owes)

    def test_no_political_strategy_is_injected(self):
        import pathlib
        for f in pathlib.Path(__file__).parent.glob("common/ai_strategies/*.txt"):
            self.assertNotRegex(f.read_text(encoding="utf-8-sig"), r"(INJECT|REPLACE):ai_strategy_\w+_agenda")

    # -- beyond the brief's sample ------------------------------------------

    def test_owing_is_a_binding_kind_1_promise_of_that_institution(self):
        body = flat(block(read(AI_TRIGGERS), "te_tax_ai_owes_institution"))
        slots = " ".join(f"AND = {{ te_tax_obl_binding = {{ N = {o} }} var:te_tax_o{o}_kind = 1 "
                         f"var:te_tax_o{o}_arg = $ARG$ }}" for o in gen.OBLIGATION_SLOTS)
        self.assertEqual(body, f"te_tax_code_on = yes OR = {{ {slots} }}")
        binding = flat(block(read(OBL_TRIGGERS), "te_tax_obl_binding"))
        self.assertEqual(binding, "has_variable = te_tax_o$N$_on var:te_tax_o$N$_on = 1 OR = { "
                                  "var:te_tax_o$N$_state = 7 var:te_tax_o$N$_state = 2 var:te_tax_o$N$_state = 3 }")

    def test_the_boost_adds_the_score_to_the_default_only(self):
        text = read(STRATEGY)
        self.assertEqual(re.findall(r"(?m)^(?:INJECT|REPLACE):(\w+)", text), ["ai_strategy_default"])
        scores = block(text, "INJECT:ai_strategy_default")
        for arg, institution in ((1, "institution_schools"), (2, "institution_health_system")):
            body = flat(block(scores.replace("\n\t\t", "\n"), institution))
            with self.subTest(institution=institution):
                self.assertEqual(body, f"value = 10 if = {{ limit = {{ te_tax_ai_owes_institution = {{ ARG = {arg} }} }} "
                                       f"add = te_tax_ai_promise_institution_score }}")
        self.assertEqual(text.count("te_tax_ai_owes_institution"), 2)
        for path in sorted((ROOT / "common/ai_strategies").glob("*.txt")):
            if path.name != "edited_default_strategy.txt":
                with self.subTest(path=path.name):
                    self.assertNotIn("te_tax", read(path.relative_to(ROOT).as_posix()))

    def test_the_strategy_file_keeps_bom_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        raw = (ROOT / STRATEGY).read_bytes()
        text = raw.decode("utf-8-sig")
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        self.assertEqual(format_paradox_tabs.format_text(text), text)


class PromiseDocTest(unittest.TestCase):
    def test_schema_doc_describes_the_ai_promise_layer(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        ai = doc.split("\n## Policy obligations\n", 1)[1].split("### Obligations and the AI\n", 1)[1].split("\n### ", 1)[0]
        for phrase in ("te_tax_ai_manage_promises", "te_tax_gen_ai_enact_", "te_tax_cmd_obl_renegotiate",
                       "obl_deadline", "edited_default_strategy.txt", "P16", "te_tax_ai_enact_lead_months",
                       "te_tax_ai_grace_next", "te_tax_ai_next_check_month", "te_tax_ai_surplus_streak_last",
                       "bureaucracy deficit", "te_tax_view_o<o>_measure", "level="):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, ai)
        self.assertNotIn("none holds an obligation yet", ai)
        section = doc.split("\n## AI legislation\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_ai_manage_packages", "te_tax_ai_manage_promises", "te_tax_ai_promise_at_risk",
                       "ai_obl_enacted", "obl_deadline", "te_tax_ai_owes_institution",
                       "te_tax_gen_ai_log_renegotiated_<o>"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_the_debug_lines_say_command_lines_are_player_only(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        para = [line for line in doc.splitlines() if line.startswith("**Debug lines.**")]
        self.assertEqual(len(para), 1)
        self.assertIn("The commands' own lines (`introduced`, `passed`, `withdrawn`, `offer_accepted`, `forced_through`, "
                      "`obl_bound`, …) are written for player countries only; the AI writes one summary line per action "
                      "instead", para[0])
        self.assertNotIn("So are the commands' own lines", para[0])
        self.assertIn("`snapshot`, `stored` and `store_refused` are written for player countries only", para[0])

    def test_ledger_has_the_ai_promise_delivery_row(self):
        rows = [line for line in read(LEDGER, strip_comments=False).splitlines()
                if line.startswith("| ") and "AI promise delivery (default-strategy boost; enactment fallback)" in line]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].split(" | ")[2], "static-only")
        self.assertNotIn("te_tax_obl_inst_met_", rows[0])
        self.assertIn("level=", rows[0])

def top_blocks(body):
    """[(name, inner)] for the blocks opened at depth 0 of `body`."""
    found, i = [], 0
    while True:
        match = re.compile(r"([\w:$]+) = \{").search(body, i)
        if match is None:
            return found
        end = close(body, match.end() - 1)
        found.append((match.group(1), body[match.end():end]))
        i = end + 1


def tooltip_conditions(body):
    """{text key: flattened condition} for every `custom_tooltip = { text = X <condition> }` in `body`."""
    found = {}
    for match in re.finditer(r"custom_tooltip = \{", body):
        inner = flat(body[match.end():close(body, match.end() - 1)])
        key, condition = re.fullmatch(r"text = (\w+) (.*)", inner).groups()
        found[key] = condition
    return found


def callers(pattern):
    """{file name: count} of `pattern` matches in common/ and events/, comments stripped."""
    found = {}
    for directory in ("common", "events"):
        for path in sorted((ROOT / directory).rglob("*.txt")):
            count = len(re.findall(pattern, read(path.relative_to(ROOT).as_posix())))
            if count:
                found[path.name] = count
    return found


class AiBillTest(unittest.TestCase):
    """Task 20: the open bill (spec §2.4 step 3, §2.7, §2.10)."""

    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.manage = block(self.ai, "te_tax_ai_manage_bill")
        self.triggers = read(AI_TRIGGERS)
        self.values = read(AI_VALUES)
        self.gen = read(GEN_EFFECTS)
        self.support = read("common/script_values/te_tax_generated_support_values.txt")

    # -- the brief's sample (tightened where it asserted nothing) ---------------

    def test_order_pass_retry_offer_force_withdraw(self):
        order = [self.manage.index(s) for s in (
            "te_tax_can_pass = yes", "te_tax_ai_blocked_by_native_level = yes",
            "te_tax_gen_ai_accept_offer = yes", "te_tax_can_force_through = yes", "te_tax_ai_bill_hopeless = yes")]
        self.assertEqual(order, sorted(order))

    def test_force_through_only_in_an_emergency(self):
        # Of the rule chain's branches (the gate's children), the one whose limit holds
        # te_tax_ai_emergency is the only one with the command, and the file has it once.
        (gate_kind, gate), = top_blocks(self.manage)
        self.assertEqual(gate_kind, "if")
        chain = [(kind, body) for kind, body in top_blocks(gate) if kind in ("if", "else_if", "else")]
        self.assertGreaterEqual(len(chain), 5)
        with_force = [body for _, body in chain if "te_tax_cmd_force_through" in body]
        self.assertEqual(len(with_force), 1)
        self.assertEqual(flat(limit_of(with_force[0])), "te_tax_ai_emergency = yes te_tax_can_force_through = yes")
        self.assertEqual([body for _, body in chain if "te_tax_ai_emergency = yes" in limit_of(body)], with_force)
        self.assertEqual(self.ai.count("te_tax_cmd_force_through = yes"), 1)

    def test_offer_chain_is_capped_and_re_raises_tomorrow(self):
        available = flat(block(self.triggers, "te_tax_ai_offer_available"))
        self.assertIn("te_tax_ai_offer_count < te_tax_ai_max_offers", available.replace("var:", ""))
        self.assertIn("else_if = { limit = { te_tax_ai_offer_available = yes } te_tax_gen_ai_accept_offer = yes }",
                      flat(self.manage))
        # The re-raise is the acceptance's own, not the dispatch's.
        self.assertIn("trigger_event = { id = te_tax.8 days = 1 }", flat(block(self.ai, "te_tax_ai_accept_offer")))

    def test_every_command_runs_behind_its_own_trigger(self):
        for cmd in ("pass", "force_through", "withdraw", "reschedule"):
            found = list(re.finditer(rf"te_tax_cmd_{cmd} = yes", self.ai))
            self.assertTrue(found, cmd)
            for m in found:
                before = self.ai[max(0, m.start() - 300):m.start()]
                self.assertIn(f"te_tax_can_{cmd} = yes", before, cmd)

    def test_no_viable_logs_once_per_episode(self):
        for reason in WITHDRAW_REASONS:
            body = block(self.ai, f"te_tax_ai_withdraw_{reason}")
            call = body.index(f"te_tax_ai_log_no_viable_{reason} = yes")
            guard = enclosing_brace(body, call)
            with self.subTest(reason=reason):
                self.assertRegex(body[:guard].rstrip(), r"(?<!\w)if =$")
                self.assertEqual(flat(limit_of(body[guard + 1:])), "var:te_tax_ai_noviable = 0")
                # The marker is read before the reset (which writes 0) and set after it, so it
                # survives the withdrawal and only a pass or the need ending clears it.
                reset = body.index("te_tax_ai_reset_bill_state = yes")
                marker = body.index("set_variable = { name = te_tax_ai_noviable value = 1 }")
                self.assertLess(guard, reset)
                self.assertLess(reset, marker)
                self.assertEqual(body.count("te_tax_ai_noviable"), 2)

    def test_the_reset_follows_pass_force_and_withdraw(self):
        # Ruling 2: for each, the reset runs in the branch of the command, after it.
        sites = [("pass", self.manage), ("force_through", self.manage)]
        sites += [("withdraw", block(self.ai, f"te_tax_ai_withdraw_{reason}")) for reason in WITHDRAW_REASONS]
        for cmd, text in sites:
            at = text.index(f"te_tax_cmd_{cmd} = yes")
            brace = enclosing_brace(text, at)
            branch = text[brace + 1:close(text, brace)]
            with self.subTest(cmd=cmd):
                self.assertEqual(flat(limit_of(branch)), f"te_tax_can_{cmd} = yes")
                self.assertLess(branch.index(f"te_tax_cmd_{cmd} = yes"), branch.index("te_tax_ai_reset_bill_state = yes"))

    def test_passing_records_the_reverse_window_marks(self):
        marks = block(self.gen, "te_tax_gen_ai_record_marks")
        for key in KEYS:
            self.assertIn(f"te_tax_ai_last_{key}", marks)
            self.assertIn(f"te_tax_ai_dir_{key}", marks)

    # -- beyond the brief's sample ----------------------------------------------

    def test_the_step_manages_the_open_bill_after_the_promises(self):
        step = flat(block(self.ai, "te_tax_ai_step"))
        self.assertIn("te_tax_ai_manage_promises = yes if = { limit = { te_tax_bill_active = yes } "
                      "te_tax_ai_manage_bill = yes }", step)
        self.assertEqual(callers(r"\bte_tax_ai_manage_bill = yes"), {"te_tax_ai_effects.txt": 1})

    def test_the_manager_is_the_rule_chain_exactly(self):
        cooldown = "set_variable = { name = te_tax_ai_next_month value = te_tax_ai_cooldown_after_pass }"
        self.assertEqual(flat(self.manage), (
            "if = { limit = { te_tax_code_on = yes te_tax_code_in_force = yes te_tax_bill_active = yes } "
            # A bill the AI did not introduce (a player's, after a tag switch): its patience starts now.
            "if = { limit = { var:te_tax_ai_bill_month < 0 } "
            "set_variable = { name = te_tax_ai_bill_month value = te_tax_ai_now } } "
            # Its due month came during debate: next month instead, then the chain may pass it.
            "if = { limit = { te_tax_can_reschedule = yes } te_tax_cmd_reschedule = yes "
            "te_tax_ai_log_bill_rescheduled = yes } "
            f"if = {{ limit = {{ te_tax_can_pass = yes }} te_tax_gen_ai_record_marks = yes {cooldown} "
            "te_tax_cmd_pass = yes te_tax_ai_log_passed = yes te_tax_ai_reset_bill_state = yes } "
            "else_if = { limit = { te_tax_ai_blocked_by_native_level = yes } "
            "set_variable = { name = te_tax_ai_retry value = 1 } te_tax_ai_log_waiting_legitimacy_native_level = yes } "
            "else_if = { limit = { te_tax_ai_offer_available = yes } te_tax_gen_ai_accept_offer = yes } "
            "else_if = { limit = { te_tax_ai_emergency = yes te_tax_can_force_through = yes } "
            f"if = {{ limit = {{ te_tax_can_force_through = yes }} te_tax_gen_ai_record_marks = yes {cooldown} "
            "te_tax_cmd_force_through = yes te_tax_ai_log_forced = yes te_tax_ai_reset_bill_state = yes } } "
            "else_if = { limit = { OR = { te_tax_ai_bill_hopeless = yes te_tax_ai_bill_age >= te_tax_ai_bill_patience } } "
            "te_tax_ai_withdraw = yes } }"))

    def test_the_cooldowns_and_the_age_are_named_values(self):
        self.assertEqual(flat(block(self.values, "te_tax_ai_cooldown_after_pass")),
                         "value = te_tax_ai_now if = { limit = { has_variable = te_tax_bl_due } "
                         "value = var:te_tax_bl_due } add = te_tax_ai_cooldown_months")
        self.assertEqual(flat(block(self.values, "te_tax_ai_cooldown_after_withdrawal")),
                         "value = te_tax_ai_now add = te_tax_ai_fail_cooldown_months")
        self.assertEqual(flat(block(self.values, "te_tax_ai_bill_age")),
                         "value = 0 if = { limit = { has_variable = te_tax_ai_bill_month "
                         "var:te_tax_ai_bill_month >= 0 } value = te_tax_ai_now subtract = var:te_tax_ai_bill_month }")

    def test_the_native_level_wait_is_the_pass_less_legitimacy(self):
        # Every line of te_tax_can_pass but legitimacy, with legitimacy short and the native
        # level off medium (spec §2.10): the writer pins it on the 1st, so the step retries on the 2nd.
        body = flat(block(self.triggers, "te_tax_ai_blocked_by_native_level"))
        can_pass = block(read(OBL_TRIGGERS), "te_tax_can_pass")
        lines = tooltip_conditions(can_pass)
        self.assertEqual(lines.pop("te_tax_tt_pass_legitimacy"), "legitimacy >= te_tax_passage_legitimacy")
        lines.pop("te_tax_tt_bill_open")
        self.assertEqual(len(lines), 9)
        for key, condition in lines.items():
            with self.subTest(line=key):
                self.assertIn(condition, body)
        self.assertNotIn("legitimacy >= ", body)
        for extra in ("te_tax_bill_active = yes", "NOT = { tax_level = medium }",
                      "legitimacy < te_tax_passage_legitimacy"):
            with self.subTest(extra=extra):
                self.assertIn(extra, body)
        self.assertLess(body.index("te_tax_bill_active = yes"), body.index("var:te_tax_bl_"))

    def force_lines(self):
        """te_tax_can_force_through's structural lines: the shares, the capacity, the Authority."""
        lines = tooltip_conditions(block(read(OBL_TRIGGERS), "te_tax_can_force_through"))
        return {key: lines[f"te_tax_tt_force_{key}"] for key in ("short", "share", "capacity", "authority")}

    def test_the_authority_reason_is_force_through_short_only_of_capacity_or_authority(self):
        # Ruling 11: only the structural lines, so the reason holds at introduction too, while the
        # debate has just begun (spec §2.4 step 4 lists it there).
        force = self.force_lines()
        self.assertEqual(force["capacity"], '"modifier:country_legislative_override_capacity_add" >= 2')
        self.assertEqual(force["authority"], "produced_authority > forced_law_through_event_authority_cost_medium")
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_force_blocked_by_authority")),
                         f"te_tax_ai_emergency = yes {force['share']} {force['short']} "
                         f"NOT = {{ AND = {{ {force['capacity']} {force['authority']} }} }}")

    def test_a_force_path_is_force_through_possible_in_substance(self):
        # Ruling 11: an emergency, the committed share force-through needs, and its capacity and
        # Authority, read with te_tax_can_force_through's own lines; no line that only time settles.
        force = self.force_lines()
        body = flat(block(self.triggers, "te_tax_ai_force_path"))
        self.assertEqual(body, f"te_tax_ai_emergency = yes {force['share']} {force['capacity']} {force['authority']}")
        for transient in ("te_tax_debate_days_left", "te_tax_bl_due", "te_tax_can_store_package", "legitimacy"):
            with self.subTest(transient=transient):
                self.assertNotIn(transient, body)

    def test_hopeless_is_short_with_no_offer_and_no_force_path(self):
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_bill_hopeless")),
                         "te_tax_bill_active = yes te_tax_view_open_share <= te_tax_passage_share "
                         "NOT = { te_tax_ai_offer_available = yes } NOT = { te_tax_ai_force_path = yes }")

    def test_an_offer_is_available_within_the_budget_while_the_bill_is_short(self):
        groups = " ".join(f"te_tax_ai_offer_acceptable = {{ IG = {ig} }}" for ig in gen.IGS)
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_offer_available")),
                         "OR = { NOT = { var:te_tax_ai_offer_month = te_tax_ai_now } "
                         "var:te_tax_ai_offer_count < te_tax_ai_max_offers } "
                         f"te_tax_committed_share <= te_tax_passage_share OR = {{ {groups} }}")

    def test_the_acceptance_policy_is_the_spec_table(self):
        clauses = (gen.OFFER_CUT, gen.OFFER_AGREL, gen.OFFER_STAPLE)
        self.assertEqual((min(clauses), max(clauses)), (1, 3))
        kind = "var:te_tax_off_$IG$_kind"
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_offer_acceptable")), (
            "te_tax_can_accept_offer = { IG = $IG$ } OR = { "
            f"AND = {{ {kind} >= 1 {kind} <= 3 te_tax_ai_clause_keeps_direction = yes "
            f"NOT = {{ AND = {{ {kind} = {gen.OFFER_AGREL} te_tax_ai_emergency = yes }} }} }} "
            f"AND = {{ {kind} = {gen.OFFER_PROMISE + 1} bureaucracy >= 0 approaching_bureaucracy_shortage = no }} "
            f"AND = {{ {kind} = {gen.OFFER_PROMISE + 2} bureaucracy > 0 approaching_bureaucracy_shortage = no }} "
            f"AND = {{ {kind} = {gen.OFFER_PROMISE + 4} te_tax_dl_revenue > 0 NOT = {{ te_tax_ai_emergency = yes }} }} }}"))
        # Kind 3 (military wages) is never offered, so never accepted.
        self.assertNotIn(f"= {gen.OFFER_PROMISE + 3} ", flat(block(self.triggers, "te_tax_ai_offer_acceptable")))

    def test_a_clause_keeps_the_bill_raising_or_cutting(self):
        raises = " ".join(f"var:te_tax_ai_tpl = {tpl}" for tpl in RAISE_TEMPLATES)
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_clause_keeps_direction")),
                         f"OR = {{ AND = {{ OR = {{ {raises} }} te_tax_dl_revenue > 0 }} "
                         f"AND = {{ var:te_tax_ai_tpl = {CUT_TEMPLATE} te_tax_dl_revenue < 0 }} "
                         "AND = { var:te_tax_ai_tpl = 0 NOT = { te_tax_dl_revenue = 0 } } }")

    def test_persuadable_is_the_open_clout_test(self):
        body = flat(block(self.triggers, "te_tax_ai_persuadable"))
        self.assertEqual(body, "has_variable = te_tax_com_$IG$ var:te_tax_com_$IG$ = 0 "
                               "has_variable = te_tax_sup_$IG$ var:te_tax_sup_$IG$ >= 0")
        open_clout = flat(block(self.support, "te_tax_open_clout"))
        for ig in gen.IGS:
            with self.subTest(ig=ig):
                self.assertIn(body.replace("$IG$", ig), open_clout)

    def test_accepting_counts_the_month_logs_and_re_raises(self):
        self.assertEqual(flat(block(self.ai, "te_tax_ai_accept_offer")), (
            "if = { limit = { te_tax_can_accept_offer = { IG = $IG$ } } te_tax_cmd_accept_offer = { IG = $IG$ } "
            "if = { limit = { NOT = { var:te_tax_ai_offer_month = te_tax_ai_now } } "
            "set_variable = { name = te_tax_ai_offer_count value = 0 } } "
            "change_variable = { name = te_tax_ai_offer_count add = 1 } "
            "set_variable = { name = te_tax_ai_offer_month value = te_tax_ai_now } "
            "te_tax_ai_log_accepted = yes trigger_event = { id = te_tax.8 days = 1 } }"))

    def test_the_withdrawal_reason_follows_the_rule(self):
        self.assertEqual(flat(block(self.ai, "te_tax_ai_withdraw")), (
            "if = { limit = { te_tax_code_on = yes } "
            "if = { limit = { legitimacy < te_tax_passage_legitimacy } te_tax_ai_withdraw_legitimacy = yes } "
            "else_if = { limit = { NOT = { OR = { var:te_tax_pa_on = 0 var:te_tax_pb_on = 0 } } } "
            "te_tax_ai_withdraw_slots = yes } "
            "else_if = { limit = { te_tax_ai_force_blocked_by_authority = yes } te_tax_ai_withdraw_authority = yes } "
            "else_if = { limit = { te_tax_ai_bill_hopeless = yes } te_tax_ai_withdraw_support = yes } "
            # Minor 1: patience only for a bill open that long, so a caller outside the manager
            # never logs patience for a bill that just opened.
            "else_if = { limit = { te_tax_ai_bill_age >= te_tax_ai_bill_patience } te_tax_ai_withdraw_patience = yes } "
            "else = { te_tax_ai_withdraw_support = yes } }"))

    def test_each_withdrawal_closes_cools_down_logs_and_resets(self):
        for reason in WITHDRAW_REASONS:
            with self.subTest(reason=reason):
                self.assertEqual(flat(block(self.ai, f"te_tax_ai_withdraw_{reason}")), (
                    "if = { limit = { te_tax_code_on = yes } if = { limit = { te_tax_can_withdraw = yes } "
                    "te_tax_cmd_withdraw = yes "
                    "set_variable = { name = te_tax_ai_next_month value = te_tax_ai_cooldown_after_withdrawal } "
                    f"te_tax_ai_log_withdrawn_{reason} = yes "
                    f"if = {{ limit = {{ var:te_tax_ai_noviable = 0 }} te_tax_ai_log_no_viable_{reason} = yes }} "
                    "te_tax_ai_reset_bill_state = yes set_variable = { name = te_tax_ai_noviable value = 1 } } }"))

    def test_the_parts_are_called_only_where_the_rules_say(self):
        self.assertEqual(callers(r"\bte_tax_gen_ai_accept_offer = yes"), {"te_tax_ai_effects.txt": 1})
        self.assertEqual(callers(r"\bte_tax_ai_accept_offer = \{"),
                         {"te_tax_ai_effects.txt": 1, "te_tax_generated_effects.txt": 2 * len(gen.IGS) ** 2})
        self.assertEqual(callers(r"\bte_tax_gen_ai_record_marks = yes"), {"te_tax_ai_effects.txt": 2})
        for reason in WITHDRAW_REASONS:
            with self.subTest(reason=reason):
                # support: hopeless, and the fallback.
                self.assertEqual(callers(rf"\bte_tax_ai_withdraw_{reason} = yes"),
                                 {"te_tax_ai_effects.txt": 2 if reason == "support" else 1})
                self.assertIn(f"te_tax_ai_withdraw_{reason} = yes", block(self.ai, "te_tax_ai_withdraw"))
        self.assertIn("te_tax_ai_withdraw = yes", self.manage)

    def test_the_clout_of_a_present_non_marginal_group_or_minus_one(self):
        for ig in gen.IGS:
            with self.subTest(ig=ig):
                self.assertEqual(flat(block(self.support, f"te_tax_ai_clout_{ig}")),
                                 f"value = -1 if = {{ limit = {{ exists = ig:ig_{ig} "
                                 f"ig:ig_{ig} = {{ ig_counts_as_marginal = no }} }} value = ig:ig_{ig}.ig_clout }}")

    def test_the_rank_orders_by_clout_then_igs_with_absent_groups_last(self):
        """Evaluates the generated ranks on clout tables: the eligible groups take 0..k-1 by
        clout, largest first, ties in IGS order; a group the country lacks (-1) takes RANK_LAST."""
        ranks = {}
        for ig in gen.IGS:
            body = flat(block(self.support, f"te_tax_ai_clout_rank_{ig}"))
            head = (f"value = {RANK_LAST} if = {{ limit = {{ te_tax_ai_clout_{ig} >= 0 }} value = 0 ")
            self.assertTrue(body.startswith(head), body[:120])
            terms = re.findall(r"if = \{ limit = \{ te_tax_ai_clout_(\w+) (>=|>) te_tax_ai_clout_(\w+) \} add = 1 \}",
                               body)
            self.assertEqual(len(terms), len(gen.IGS) - 1)
            self.assertEqual({rhs for _, _, rhs in terms}, {ig})
            ranks[ig] = [(other, op) for other, op, _ in terms]
        tables = [
            dict(zip(gen.IGS, (5, 9, 1, 7, 3, 8, 2, 6))),
            dict(zip(gen.IGS, (4, 4, 4, 4, 4, 4, 4, 4))),
            dict(zip(gen.IGS, (-1, 3, -1, 3, 0.5, -1, 9, 3))),
            dict(zip(gen.IGS, (-1,) * 7 + (2,))),
        ]
        for table in tables:
            eligible = sorted((ig for ig in gen.IGS if table[ig] >= 0),
                              key=lambda ig: (-table[ig], gen.IGS.index(ig)))
            expected = {ig: (eligible.index(ig) if ig in eligible else RANK_LAST) for ig in gen.IGS}
            got = {}
            for ig in gen.IGS:
                if table[ig] < 0:
                    got[ig] = RANK_LAST
                    continue
                got[ig] = sum(1 for other, op in ranks[ig]
                              if (table[other] >= table[ig] if op == ">=" else table[other] > table[ig]))
            with self.subTest(table=table):
                self.assertEqual(got, expected)

    def test_the_offer_chain_takes_persuadable_groups_by_clout_then_opposed_ones(self):
        # Locals, not schema tokens, so not te_tax_ai_ (Minor 2; the te_tax_band precedent).
        locals_ = " ".join(f"set_local_variable = {{ name = te_tax_rank_{ig} value = te_tax_ai_clout_rank_{ig} }}"
                           for ig in gen.IGS)
        branches_ = []
        for persuadable in (True, False):
            for rank in range(len(gen.IGS)):
                for ig in gen.IGS:
                    stance = (f"te_tax_ai_persuadable = {{ IG = {ig} }}" if persuadable
                              else f"NOT = {{ te_tax_ai_persuadable = {{ IG = {ig} }} }}")
                    opener = "if" if not branches_ else "else_if"
                    branches_.append(f"{opener} = {{ limit = {{ local_var:te_tax_rank_{ig} = {rank} {stance} "
                                     f"te_tax_ai_offer_acceptable = {{ IG = {ig} }} }} "
                                     f"te_tax_ai_accept_offer = {{ IG = {ig} }} }}")
        self.assertEqual(flat(block(self.gen, "te_tax_gen_ai_accept_offer")), f"{locals_} {' '.join(branches_)}")
        # Every group the offer test can accept has a branch: rule 3 is taken only when one is
        # acceptable (te_tax_ai_offer_available), so the chain always accepts one.
        available = set(re.findall(r"te_tax_ai_offer_acceptable = \{ IG = (\w+) \}",
                                   block(self.triggers, "te_tax_ai_offer_available")))
        self.assertEqual(available, set(gen.IGS))
        self.assertEqual(RANK_LAST, len(gen.IGS))
        # A group with no branch (absent or marginal, rank RANK_LAST) can never be accepted: the
        # Accept button's trigger refuses it (Minor 4). Without this line rule 3 could accept nothing.
        self.assertIn("custom_tooltip = { text = te_tax_tt_offer_not_marginal "
                      "ig:ig_$IG$ ?= { ig_counts_as_marginal = no } }",
                      flat(block(read(OBL_TRIGGERS), "te_tax_can_accept_offer")))
        self.assertNotIn("te_tax_ai_rank_", read(GEN_EFFECTS))

    def test_each_mark_records_the_month_and_the_direction_of_a_change(self):
        marks = flat(block(self.gen, "te_tax_gen_ai_record_marks"))
        expected = " ".join(
            f"if = {{ limit = {{ te_tax_bl_dstep_{key} > 0 }} "
            f"set_variable = {{ name = te_tax_ai_last_{key} value = te_tax_ai_now }} "
            f"set_variable = {{ name = te_tax_ai_dir_{key} value = 1 }} }} "
            f"else_if = {{ limit = {{ te_tax_bl_dstep_{key} < 0 }} "
            f"set_variable = {{ name = te_tax_ai_last_{key} value = te_tax_ai_now }} "
            f"set_variable = {{ name = te_tax_ai_dir_{key} value = -1 }} }}" for key in KEYS)
        self.assertEqual(marks, expected)

    def test_the_generated_bill_parts_read_no_is_ai_and_raise_no_event(self):
        for name in ("te_tax_gen_ai_accept_offer", "te_tax_gen_ai_record_marks"):
            with self.subTest(name=name):
                body = block(self.gen, name)
                self.assertNotIn("is_ai", body)
                self.assertNotIn("trigger_event", body)
                self.assertNotIn("te_tax_cmd_", body)

    def test_schema_doc_has_the_open_bill(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        section = doc.split("\n## AI legislation\n", 1)[1].split("\n## ", 1)[0]
        bill = section.split("\n### The open bill\n", 1)[1].split("\n### ", 1)[0]
        for phrase in ("te_tax_ai_manage_bill", "te_tax_cmd_reschedule", "te_tax_ai_blocked_by_native_level",
                       "te_tax_ai_force_path", "one support refresh per execution",
                       "te_tax_ai_offer_available", "te_tax_gen_ai_accept_offer", "te_tax_ai_clout_rank_<ig>",
                       "te_tax_ai_bill_hopeless", "te_tax_ai_force_blocked_by_authority", "te_tax_gen_ai_record_marks",
                       "te_tax_ai_cooldown_after_pass", "te_tax_ai_cooldown_after_withdrawal",
                       "te_tax_ai_bill_patience", "te_tax_ai_max_offers", "te_tax_ai_noviable",
                       "approaching_bureaucracy_shortage", "ai_bill_rescheduled"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, bill)
        for reason in WITHDRAW_REASONS:
            with self.subTest(reason=reason):
                self.assertIn(f"`{reason}`", bill)
        # The offer policy table: one row per kind the AI may accept.
        rows = [line for line in bill.splitlines() if line.startswith("| ")]
        self.assertGreaterEqual(len(rows), 6)

    def test_ledger_has_the_ai_passage_loop_row(self):
        rows = [line for line in read(LEDGER, strip_comments=False).splitlines()
                if line.startswith("| ") and "| AI passage loop |" in line]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].split(" | ")[2], "static-only")
        self.assertIn("S13", rows[0])


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
        self.assertIn("### AI rows", schema)
        self.assertNotIn("### AI legislation", schema)
        self.assertNotIn("#ai-legislation-1", doc)
        rules = doc.split("### Processor rules", 1)[1].split("\n### ", 1)[0]
        self.assertIn("1b.", rules)
        self.assertIn("te_tax_ai_dispatch", rules)
        self.assertIn("\n## AI legislation\n", doc)


if __name__ == "__main__":
    unittest.main()
