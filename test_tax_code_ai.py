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

Task 21 starts a bill when none is open (spec §2.4 step 4, §2.5, §2.6):

* ready on an initiative month off cooldown with no package waiting, or in
  an emergency, which still waits out the cooldown after a failure
  (Ruling 12), so no introduce-and-withdraw loop;
* the first template that applies, T2, T3, T6, T1 or T5, built in a fresh
  draft with the draft commands only, each behind its own trigger, on the
  instrument the generated pre-score picks; never customs or relief;
* one introduction, judged in the same execution: withdrawn at once when
  hopeless; a refused draft discarded, with ai_no_viable reason=draft once
  per episode.

Run: python3 -m unittest test_tax_code_ai -v
"""

import re
import unittest
from decimal import Decimal
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
# Task 21: the templates in the order te_tax_ai_initiative tries them (te_tax_ai_tpl codes).
TEMPLATE_ORDER = (2, 3, 6, 1, 5)
# te_tax_gen_ai_step_inst's instrument codes: 1 to 5 in INSTRUMENTS order, 0 none.
INSTRUMENT_CODES = {key: code for code, key in enumerate(KEYS, start=1)}
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
# The initiative's generated parts (te_tax_generated_effects.txt).
INITIATIVE_GEN = ("te_tax_gen_ai_pick_raise", "te_tax_gen_ai_pick_cut", "te_tax_gen_ai_step_inst",
                  "te_tax_gen_ai_levy_sunset", "te_tax_gen_ai_tax_luxury")
# The initiative's hand-written effects.
INITIATIVE_EFFECTS = ("te_tax_ai_initiative", "te_tax_ai_open_draft", "te_tax_ai_introduce_and_judge",
                      *(f"te_tax_ai_build_t{n}" for n in TEMPLATE_ORDER))
# The support model's weights the pre-score restates for one step (spec §2.5).
MATERIAL_POINTS, IDEOLOGY_POINTS = 10, 5
# The engine's script values are fixed point to 1e-5; the pre-score's constants are written to it.
FIXED_POINT = Decimal("0.00001")


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


    def test_a_release_also_zeroes_the_fiscal_streaks(self):
        # Final review A-M4: a revived tag must not keep an earlier life's deficit or surplus
        # streak; the outbreak and the repair keep the country's own (the reset does not touch them).
        release = block(read(CIVIL_WAR), "te_tax_init_released_country")
        for name in ("te_tax_ai_def_streak", "te_tax_ai_sur_streak"):
            self.assertIn(f"set_variable = {{ name = {name} value = 0 }}", release)
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
                         "te_tax_ai_reserves < te_tax_ai_reserves_full } "
                         "AND = { te_tax_ai_kind4_in_force = yes NOT = { te_tax_fisc_rec_surplus = yes } } }")

    def test_cut_need_is_a_recorded_surplus_at_the_cut_ratio_and_no_promised_surplus(self):
        # Task 21 (Task 18's hand-off): a fiscal-balance promise in force counts as revenue need
        # (spec §2.3), so it is never also a need to cut.
        self.assertEqual(self.body("te_tax_ai_cut_need"),
                         "te_tax_fisc_rec_surplus = yes te_tax_ai_ratio >= te_tax_ai_cut_ratio_now "
                         "NOT = { te_tax_ai_kind4_in_force = yes }")

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
        self.assertEqual(body.count("te_tax_ai_"), 3,
                         "the processor only updates the streaks, dispatches and writes the yearly summary")
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
        # Final review A-M3: count the raise sites, not mentions. The dispatch raises it five
        # times (the retry and four buckets), the offer chain once, nothing else does.
        raises = {}
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                n = len(re.findall(r"trigger_event = \{ id = te_tax\.8\b", read(path.relative_to(ROOT).as_posix())))
                if n:
                    raises[path.name] = n
        self.assertEqual(raises, {"te_tax_ai_effects.txt": 6})
        self.assertEqual(len(re.findall(r"trigger_event = \{ id = te_tax\.8\b",
                                        block(read(AI_EFFECTS), "te_tax_ai_dispatch"))), 5)

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
                     "te_tax_ai_withdraw", *(f"te_tax_ai_withdraw_{reason}" for reason in WITHDRAW_REASONS),
                     *INITIATIVE_EFFECTS):
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
        para = [line for line in doc.splitlines() if line.startswith("**Debug lines**")]
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
        # The step, and the console's te_tax_debug.2 (Task 22, Ruling 6).
        self.assertEqual(callers(r"\bte_tax_ai_manage_bill = yes"), {"te_tax_ai_effects.txt": 1,
                                                                   "te_tax_debug_events.txt": 1})

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

    def test_hopeless_is_short_with_no_offer_and_no_force_path_or_below_the_legitimacy_line(self):
        # Final review A-M1: below the passage legitimacy at a medium native level, nothing
        # but time lifts it, so the bill is withdrawn at once rather than after its patience.
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_bill_hopeless")),
                         "te_tax_bill_active = yes OR = { AND = { te_tax_view_open_share <= te_tax_passage_share "
                         "NOT = { te_tax_ai_offer_available = yes } NOT = { te_tax_ai_force_path = yes } } "
                         "AND = { legitimacy < te_tax_passage_legitimacy tax_level = medium } }")

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


def tokens(text):
    """`text` flattened into tokens, braces apart."""
    return flat(text).replace("{", " { ").replace("}", " } ").split()


def tree(toks, i=0):
    """[(key, op, value)] read from `toks` at `i` to the closing `}` (or the end), and where it
    stopped; a value is a token or such a list."""
    out = []
    while i < len(toks) and toks[i] != "}":
        key, op = toks[i], toks[i + 1]
        if toks[i + 2] == "{":
            value, i = tree(toks, i + 3)
            i += 1
        else:
            value, i = toks[i + 2], i + 3
        out.append((key, op, value))
    return out, i


class PickSim:
    """Runs a generated te_tax_gen_ai_pick_<direction> body: set_local_variable, if/limit, and
    the comparisons it uses. `costs` stand for te_tax_ai_cost_<key>, `excluded` for the keys
    whose te_tax_ai_excluded_<direction>_<key> holds. Reading a local before it is set fails."""

    def __init__(self, costs, excluded):
        self.costs, self.excluded, self.local = costs, excluded, {}

    def value(self, token):
        if token.startswith("local_var:"):
            return self.local[token.split(":", 1)[1]]
        match = re.fullmatch(r"te_tax_ai_cost_(\w+)", token)
        return self.costs[match.group(1)] if match else Decimal(token)

    def holds(self, condition):
        key, op, value = condition
        if key in ("NOT", "OR", "AND"):
            results = [self.holds(item) for item in value]
            return {"NOT": not all(results), "OR": any(results), "AND": all(results)}[key]
        match = re.fullmatch(r"te_tax_ai_excluded_(?:raise|cut)_(\w+)", key)
        if match:
            assert (op, value) == ("=", "yes"), condition
            return match.group(1) in self.excluded
        left, right = self.value(key), self.value(value)
        return {"=": left == right, "<": left < right, ">": left > right}[op]

    def run(self, statements):
        for key, _, value in statements:
            if key == "set_local_variable":
                fields = {k: v for k, _, v in value}
                self.local[fields["name"]] = self.value(fields["value"])
            elif key == "if":
                limit = [v for k, _, v in value if k == "limit"][0]
                if all(self.holds(c) for c in limit):
                    self.run([s for s in value if s[0] != "limit"])
            else:
                raise AssertionError(f"unexpected statement {key}")
        return self


def expected_picks(costs, excluded, direction):
    """(pick, pick2): the cheapest (raise) or dearest (cut) instruments not excluded, ties in
    INSTRUMENTS order, as codes; 0 where there is none."""
    sign = 1 if direction == "raise" else -1
    ranked = sorted((key for key in KEYS if key not in excluded), key=lambda k: (sign * costs[k], KEYS.index(k)))
    codes = [INSTRUMENT_CODES[key] for key in ranked] + [0, 0]
    return codes[0], codes[1]


class AiInitiativeTest(unittest.TestCase):
    """Task 21: the initiative (spec §2.4 step 4, §2.5, §2.6)."""

    def setUp(self):
        self.ai = read(AI_EFFECTS)
        self.values = read(GEN_SUPPORT) + read(AI_VALUES)
        self.triggers = read(AI_TRIGGERS)
        self.gen_triggers = read(GEN_TRIGGERS)
        self.gen = read(GEN_EFFECTS)

    # -- the brief's sample (adapted where noted) --------------------------------

    def test_template_order_is_emergency_war_goods_raise_cut(self):
        body = block(self.ai, "te_tax_ai_initiative")
        order = [body.index(f"te_tax_ai_build_t{n} = yes") for n in (2, 3, 6, 1, 5)]
        self.assertEqual(order, sorted(order))
        # Ruling 14 (spec §2.5, T1 and T6 compete): the raise pick comes before the choice, and T6
        # applies only when it is the consumption rate, so T6 replaces a rate raise with luxury goods.
        chain = flat(body)
        self.assertLess(chain.index("te_tax_gen_ai_pick_raise = yes"),
                        chain.index("if = { limit = { te_tax_ai_template_2_applies = yes } te_tax_ai_build_t2 = yes"))
        self.assertIn(f"local_var:te_tax_pick = {INSTRUMENT_CODES['cons']}",
                      block(self.triggers, "te_tax_ai_template_6_applies"))

    def test_pre_score_constants_follow_exposure_and_level_steps(self):
        for key in KEYS:
            cost = block(self.values, f"te_tax_ai_cost_{key}")
            for ig in gen.IGS:
                self.assertIn(f"ig:ig_{ig}", cost)
            self.assertIn("ig_counts_as_marginal = no", cost)

    def test_templates_use_only_draft_commands_behind_triggers(self):
        for cmd in ("draft_new", "draft_due", "draft_sunset", "draft_good", "draft_discard", "introduce"):
            for m in re.finditer(rf"te_tax_cmd_{cmd}\b", self.ai):
                self.assertIn(f"te_tax_can_{cmd}", self.ai[max(0, m.start() - 300):m.start()], cmd)

    def test_no_template_touches_customs_or_relief(self):
        parts = self.ai + "".join(block(self.gen, name) for name in INITIATIVE_GEN)
        for name in ("te_tax_cmd_draft_customs", "te_tax_cmd_draft_relief", "te_tax_cmd_draft_relief_state"):
            self.assertNotIn(name, parts)

    def test_one_bill_per_initiative_and_judged_in_the_same_execution(self):
        judge = block(self.ai, "te_tax_ai_introduce_and_judge")
        self.assertEqual(judge.count("te_tax_cmd_introduce = yes"), 1)
        self.assertLess(judge.index("te_tax_cmd_introduce = yes"), judge.index("te_tax_ai_bill_hopeless = yes"))

    def test_reverse_window_excludes_recent_opposite_moves(self):
        # The brief asserts the literal te_tax_ai_reverse_months in each trigger; the window's
        # first month is the one named value te_tax_ai_reverse_since (now - te_tax_ai_reverse_months).
        triggers = self.gen_triggers + self.triggers
        for key in KEYS:
            excl = block(triggers, f"te_tax_ai_excluded_raise_{key}")
            self.assertIn(f"te_tax_ai_dir_{key}", excl)
            self.assertIn("te_tax_ai_reverse_since", excl)
        self.assertEqual(flat(block(read(AI_VALUES), "te_tax_ai_reverse_since")),
                         "value = te_tax_ai_now subtract = te_tax_ai_reverse_months")

    def test_step_levels_are_the_step_over_one_vanilla_tax_level(self):
        levels = gen.ai_step_levels()
        self.assertEqual(levels, {"wage": Decimal("0.5"), "div": Decimal("0.5"), "land": Decimal(1) / Decimal(6),
                                  "head": Decimal(1) / Decimal(3), "cons": Decimal(1)})
        for key, level in levels.items():
            with self.subTest(key=key):
                self.assertIsInstance(level, Decimal)
                instrument = [i for i in gen.INSTRUMENTS if i.key == key][0]
                self.assertEqual(level, instrument.step / gen.LEVEL_STEPS[key])

    # -- the step and readiness ----------------------------------------------------

    def test_the_step_starts_the_initiative_only_without_a_bill(self):
        step = flat(block(self.ai, "te_tax_ai_step"))
        self.assertIn("if = { limit = { te_tax_bill_active = yes } te_tax_ai_manage_bill = yes } "
                      "else_if = { limit = { te_tax_ai_initiative_ready = yes } te_tax_ai_initiative = yes }", step)
        # The step, and the console's te_tax_debug.2 (Task 22, Ruling 6).
        self.assertEqual(callers(r"\bte_tax_ai_initiative = yes"), {"te_tax_ai_effects.txt": 1,
                                                                    "te_tax_debug_events.txt": 1})

    def test_the_step_clears_the_episode_marker_when_the_need_ends(self):
        # Before the managers, so a bill the step withdraws later in the same run starts the new episode.
        step = flat(block(self.ai, "te_tax_ai_step"))
        self.assertTrue(step.startswith(
            "if = { limit = { te_tax_code_on = yes te_tax_ai_can_act = yes } "
            "if = { limit = { te_tax_ai_need_ended = yes } set_variable = { name = te_tax_ai_noviable value = 0 } } "
            "te_tax_ai_manage_packages = yes"), step[:200])
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_need_ended")),
                         "NOT = { te_tax_ai_raise_need = yes } NOT = { te_tax_ai_cut_need = yes } "
                         "NOT = { te_tax_ai_emergency = yes }")

    def test_ready_is_an_initiative_month_off_cooldown_or_an_emergency_not_after_a_failure(self):
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_initiative_ready")), (
            "te_tax_code_in_force = yes NOT = { te_tax_bill_active = yes } OR = { "
            "AND = { te_tax_ai_emergency = yes OR = { "
            "AND = { var:te_tax_ai_noviable = 0 te_tax_ai_now > te_tax_ai_emergency_gate_month } "
            "te_tax_ai_cooldown_over = yes } } "
            "AND = { te_tax_ai_initiative_due = yes te_tax_ai_cooldown_over = yes "
            "NOT = { te_tax_ai_package_awaits = yes } } }"))
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_cooldown_over")),
                         "var:te_tax_ai_next_month <= te_tax_ai_now")
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_package_awaits")), (
            "OR = { AND = { has_variable = te_tax_pa_on var:te_tax_pa_on = 1 var:te_tax_pa_state = 1 } "
            "AND = { has_variable = te_tax_pb_on var:te_tax_pb_on = 1 var:te_tax_pb_state = 1 } }"))

    def test_an_emergency_bill_waits_for_a_record_of_the_last_one(self):
        # Ruling 13 (parent design §10, hysteresis): with no failure this episode, the next emergency
        # bill waits until the fiscal record of the 1st covers a month at the previous AI bill's new
        # rates. After a pass the cooldown is the package's commencement month + te_tax_ai_cooldown_months
        # (te_tax_ai_cooldown_after_pass), so the gate is that commencement month and the step may act
        # from the month after it: a T2 (due now + 2) about every three months. From the sentinel the
        # gate lies in the past.
        values = read(AI_VALUES)
        self.assertEqual(flat(block(values, "te_tax_ai_emergency_gate_month")),
                         "value = -1 if = { limit = { has_variable = te_tax_ai_next_month } "
                         "value = var:te_tax_ai_next_month } subtract = te_tax_ai_cooldown_months")
        self.assertEqual(flat(block(values, "te_tax_ai_cooldown_after_pass")),
                         "value = te_tax_ai_now if = { limit = { has_variable = te_tax_bl_due } "
                         "value = var:te_tax_bl_due } add = te_tax_ai_cooldown_months")

        def gate(next_month):
            return next_month - int(TUNABLES["te_tax_ai_cooldown_months"])

        introduced = 100
        due = introduced + 2                                    # T2: the default due month one earlier
        after_pass = due + int(TUNABLES["te_tax_ai_cooldown_months"])
        first = min(now for now in range(introduced, introduced + 24) if now > gate(after_pass))
        self.assertEqual(first, due + 1)
        self.assertEqual(first - introduced, 3)
        self.assertTrue(0 > gate(-1), "the sentinel always passes")

    def test_a_failure_cooldown_always_marks_the_episode(self):
        # Ruling 12: te_tax_ai_noviable is 1 exactly while te_tax_ai_next_month holds a failure
        # cooldown, so an emergency, which skips the cooldown after a pass, still waits out the one
        # after a withdrawal or a refused draft: no introduce-and-withdraw loop every month. Every
        # failure cooldown is followed in its block by the marker; every pass cooldown by the
        # reset, which clears it.
        failure = "set_variable = { name = te_tax_ai_next_month value = te_tax_ai_cooldown_after_withdrawal }"
        passed = "set_variable = { name = te_tax_ai_next_month value = te_tax_ai_cooldown_after_pass }"
        text = flat(self.ai)
        for write, then, count in ((failure, "set_variable = { name = te_tax_ai_noviable value = 1 }", 6),
                                   (passed, "te_tax_ai_reset_bill_state = yes", 2)):
            found = [m.start() for m in re.finditer(re.escape(write), text)]
            self.assertEqual(len(found), count, write)
            for at in found:
                with self.subTest(write=write, at=at):
                    brace = enclosing_brace(text, at)
                    branch = text[brace + 1:close(text, brace)]
                    self.assertIn(then, branch[branch.index(write):])
        self.assertEqual(RESET["te_tax_ai_noviable"], "0")
        # Nothing else in common/ writes the cooldown (the init's guarded sentinel aside).
        self.assertEqual(callers(r"name = te_tax_ai_next_month value = te_tax_ai_cooldown"),
                         {"te_tax_ai_effects.txt": 8})
        # Plus the console's te_tax_debug.4 (Task 22), which clears the cooldown to the
        # sentinel together with the marker (test_tax_code_console.py).
        self.assertEqual(callers(r"name = te_tax_ai_next_month value"),
                         {"te_tax_ai_effects.txt": 8, "te_tax_state_effects.txt": 1,
                          "te_tax_debug_events.txt": 1})

    # -- templates -----------------------------------------------------------------

    def test_the_initiative_builds_one_template_in_a_fresh_draft(self):
        # Opened only when T2, T1 or T5 applies; T3 and T6 need T1's need, so a branch always takes the
        # draft and te_tax_ai_introduce_and_judge discards it. The raise pick precedes the choice (Ruling 14).
        branches = " ".join(
            f"{'if' if i == 0 else 'else_if'} = {{ limit = {{ te_tax_ai_template_{n}_applies = yes }} "
            f"te_tax_ai_build_t{n} = yes te_tax_ai_introduce_and_judge = {{ TPL = {n} }} }}"
            for i, n in enumerate(TEMPLATE_ORDER))
        self.assertEqual(flat(block(self.ai, "te_tax_ai_initiative")), (
            "if = { limit = { te_tax_code_on = yes te_tax_code_in_force = yes NOT = { te_tax_bill_active = yes } "
            "OR = { te_tax_ai_template_2_applies = yes te_tax_ai_template_1_applies = yes "
            "te_tax_ai_template_5_applies = yes } } "
            "te_tax_ai_open_draft = yes te_tax_gen_ai_pick_raise = yes "
            f"{branches} }}"))
        for n in (3, 6):
            with self.subTest(template=n):
                self.assertIn("te_tax_ai_raise_wanted = yes", block(self.triggers, f"te_tax_ai_template_{n}_applies"))
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_template_1_applies")), "te_tax_ai_raise_wanted = yes")
        # The codes are the ones the open bill's clause rule reads (te_tax_ai_clause_keeps_direction).
        self.assertEqual(set(TEMPLATE_ORDER), set(RAISE_TEMPLATES) | {CUT_TEMPLATE})

    def test_a_fresh_draft_discards_a_stale_one_first(self):
        self.assertEqual(flat(block(self.ai, "te_tax_ai_open_draft")), (
            "if = { limit = { te_tax_code_on = yes } "
            "if = { limit = { te_tax_can_draft_discard = yes } te_tax_cmd_draft_discard = yes } "
            "if = { limit = { te_tax_can_draft_new = yes } te_tax_cmd_draft_new = yes } }"))

    def test_each_template_builds_its_bill(self):
        pick, pick2 = "local_var:te_tax_pick", "local_var:te_tax_pick2"
        step = "te_tax_gen_ai_step_inst = {{ INST = {} DIR = {} }}"
        builds = {
            # T1 to T3 move the raise pick the initiative made before the choice (Ruling 14).
            1: f"{step.format(pick, 1)} {step.format(pick2, 1)}",
            2: (f"{step.format(pick, 1)} {step.format(pick, 1)} "
                "if = { limit = { te_tax_can_draft_due = { DIR = 0 } } te_tax_cmd_draft_due = { DIR = 0 } }"),
            3: f"{step.format(pick, 1)} {step.format(pick, 1)} te_tax_gen_ai_levy_sunset = {{ INST = {pick} }}",
            5: f"te_tax_gen_ai_pick_cut = yes {step.format(pick, 0)}",
            6: "te_tax_gen_ai_tax_luxury = yes",
        }
        for n, body in builds.items():
            with self.subTest(template=n):
                self.assertEqual(flat(block(self.ai, f"te_tax_ai_build_t{n}")),
                                 f"if = {{ limit = {{ te_tax_code_on = yes }} {body} }}")

    def test_template_conditions_follow_spec_2_5(self):
        bodies = {
            2: "te_tax_ai_emergency = yes",
            # A failed T3 or T6 is followed by a T1 in the same episode (Ruling 14).
            3: "var:te_tax_ai_noviable = 0 is_at_war = yes te_tax_ai_raise_wanted = yes",
            # T6 only in place of a consumption-rate raise: the raise pick is cons (Ruling 14).
            6: (f"var:te_tax_ai_noviable = 0 te_tax_ai_raise_wanted = yes "
                f"local_var:te_tax_pick = {INSTRUMENT_CODES['cons']} var:te_tax_en_cons >= 1 "
                "te_tax_ai_taxed_goods < te_tax_ai_max_goods"),
            1: "te_tax_ai_raise_wanted = yes",
            5: "te_tax_ai_cut_wanted = yes",
        }
        for n, body in bodies.items():
            with self.subTest(template=n):
                self.assertEqual(flat(block(self.triggers, f"te_tax_ai_template_{n}_applies")), body)
        # The need with its hysteresis: te_tax_ai_need_months recorded deficits, or a promised surplus,
        # which keeps the AI raising until the surplus delivers (spec §2.8); a cut after
        # te_tax_ai_surplus_months recorded surpluses with the reserves full.
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_raise_wanted")),
                         "te_tax_ai_raise_need = yes OR = { var:te_tax_ai_def_streak >= te_tax_ai_need_months "
                         "te_tax_ai_kind4_in_force = yes }")
        self.assertEqual(flat(block(self.triggers, "te_tax_ai_cut_wanted")),
                         "te_tax_ai_cut_need = yes var:te_tax_ai_sur_streak >= te_tax_ai_surplus_months "
                         "te_tax_ai_reserves >= te_tax_ai_reserves_full")

    def test_the_goods_values(self):
        values = read(AI_VALUES)
        self.assertEqual(flat(block(values, "te_tax_ai_taxed_goods")), "value = te_tax_view_goods_count")
        self.assertEqual(flat(block(values, "te_tax_ai_goods_room")),
                         "value = te_tax_ai_max_goods subtract = te_tax_ai_taxed_goods max = 2 min = 0")

    # -- introduce and judge -------------------------------------------------------

    def test_introduce_and_judge(self):
        self.assertEqual(flat(block(self.ai, "te_tax_ai_introduce_and_judge")), (
            "if = { limit = { te_tax_code_on = yes } "
            # Set before the introduction, so a refused draft's lines name the template (review minor 1).
            "set_variable = { name = te_tax_ai_tpl value = $TPL$ } "
            "if = { limit = { te_tax_can_introduce = yes } te_tax_cmd_introduce = yes } "
            # The bill holds a copy; an AI draft lives for one step (spec §2.4).
            "if = { limit = { te_tax_can_draft_discard = yes } te_tax_cmd_draft_discard = yes } "
            "if = { limit = { te_tax_bill_active = yes } "
            "set_variable = { name = te_tax_ai_bill_month value = te_tax_ai_now } "
            "te_tax_ai_log_introduced = yes "
            "if = { limit = { te_tax_ai_bill_hopeless = yes } te_tax_ai_withdraw = yes } } "
            # Refused: no bill to withdraw; the failure cooldown, a line, and the episode's one no-viable.
            "else = { "
            "set_variable = { name = te_tax_ai_next_month value = te_tax_ai_cooldown_after_withdrawal } "
            "te_tax_ai_log_withdrawn_draft = yes "
            "if = { limit = { var:te_tax_ai_noviable = 0 } te_tax_ai_log_no_viable_draft = yes } "
            "set_variable = { name = te_tax_ai_noviable value = 1 } "
            # No bill: no template.
            "set_variable = { name = te_tax_ai_tpl value = 0 } } }"))

    def test_the_parts_are_called_where_the_templates_say(self):
        # Calls only: a definition starts its line, a call is indented.
        self.assertEqual(callers(r"[ \t]te_tax_ai_introduce_and_judge = \{"), {"te_tax_ai_effects.txt": 5})
        self.assertEqual(callers(r"\bte_tax_ai_open_draft = yes"), {"te_tax_ai_effects.txt": 1})
        for n in TEMPLATE_ORDER:
            with self.subTest(template=n):
                self.assertEqual(callers(rf"\bte_tax_ai_build_t{n} = yes"), {"te_tax_ai_effects.txt": 1})
        for name, count in (("te_tax_gen_ai_pick_raise = yes", 1), ("te_tax_gen_ai_pick_cut = yes", 1),
                            ("te_tax_gen_ai_step_inst = {", 7), ("te_tax_gen_ai_levy_sunset = {", 1),
                            ("te_tax_gen_ai_tax_luxury = yes", 1)):
            with self.subTest(name=name):
                self.assertEqual(callers(r"[ \t]" + re.escape(name)), {"te_tax_ai_effects.txt": count})
        # Withdrawal on introduction is the dispatcher, only behind hopeless (Task 20's hand-off).
        self.assertEqual(flat(self.ai).count("if = { limit = { te_tax_ai_bill_hopeless = yes } te_tax_ai_withdraw = yes }"), 1)

    # -- the pre-score and the picks (generated) ------------------------------------

    def test_the_pre_score_is_the_support_models_cost_of_one_step(self):
        # cost_k = sum over present, non-marginal groups of clout x (10 s_k exposure - 5 sign_k s_k P(ig)):
        # the material and ideology reasons of a +1 step with the sign turned (spec §2.5).
        self.assertEqual((gen.MATERIAL_WEIGHT, gen.IDEOLOGY_WEIGHT), (-MATERIAL_POINTS, IDEOLOGY_POINTS))
        support = read(GEN_SUPPORT)
        levels = gen.ai_step_levels()
        term = re.compile(r"if = \{ limit = \{ exists = ig:ig_(\w+) ig:ig_\1 = \{ ig_counts_as_marginal = no \} \} "
                          r"add = \{ value = te_tax_ideo_p_\1 multiply = (\S+) add = (\S+) "
                          r"multiply = ig:ig_\1\.ig_clout \} \}")
        for key in KEYS:
            cost = flat(block(support, f"te_tax_ai_cost_{key}"))
            terms = list(term.finditer(cost))
            sign = 1 if key in gen.PROGRESSIVE_KEYS else -1
            with self.subTest(key=key):
                self.assertEqual(cost, "value = 0 " + " ".join(m.group(0) for m in terms))
                self.assertEqual([m.group(1) for m in terms], list(gen.IGS))
            for m in terms:
                ig, ideology, material = m.group(1), Decimal(m.group(2)), Decimal(m.group(3))
                with self.subTest(key=key, ig=ig):
                    self.assertLessEqual(abs(material - MATERIAL_POINTS * levels[key] * gen.exposure(ig)[key]),
                                         FIXED_POINT / 2)
                    self.assertLessEqual(abs(ideology + IDEOLOGY_POINTS * sign * levels[key]), FIXED_POINT / 2)
                    self.assertEqual(material, material.quantize(FIXED_POINT))
                    self.assertEqual(ideology, ideology.quantize(FIXED_POINT))

    def test_exclusions(self):
        def window(key, direction):
            return (f"AND = {{ has_variable = te_tax_ai_dir_{key} var:te_tax_ai_dir_{key} = {direction} "
                    f"has_variable = te_tax_ai_last_{key} var:te_tax_ai_last_{key} >= te_tax_ai_reverse_since }}")

        for key in KEYS:
            raise_ = [f"te_tax_dr_eff_{key} >= te_tax_max_{key}"]
            if key in gen.TRADITIONALISM_KEYS:
                raise_.append("has_law = law_type:law_traditionalism")
            if key == "cons":
                raise_.append("te_tax_ai_taxed_goods <= 0")
            raise_.append(window(key, -1))
            cut = [f"te_tax_dr_eff_{key} <= 0", window(key, 1)]
            with self.subTest(key=key):
                self.assertEqual(flat(block(self.gen_triggers, f"te_tax_ai_excluded_raise_{key}")),
                                 f"OR = {{ {' '.join(raise_)} }}")
                self.assertEqual(flat(block(self.gen_triggers, f"te_tax_ai_excluded_cut_{key}")),
                                 f"OR = {{ {' '.join(cut)} }}")
        # "At its maximum" and "at 0" are what the step command tests (te_tax_dr_step_ok_1 / _0).
        commands = read("common/scripted_triggers/te_tax_triggers.txt")
        self.assertIn("te_tax_dr_eff_$KEY$ < te_tax_max_$KEY$", block(commands, "te_tax_dr_step_ok_1"))
        self.assertIn("te_tax_dr_eff_$KEY$ > 0", block(commands, "te_tax_dr_step_ok_0"))
        self.assertIn("has_law = law_type:law_traditionalism", block(commands, "te_tax_draft_ready"))

    def test_the_picks_are_the_cheapest_or_dearest_not_excluded_ties_in_order(self):
        # Every instrument cheapest and dearest once (the rotations), then ties of all and of some.
        base = ("3", "1", "2", "5", "4")
        tables = tuple(dict(zip(KEYS, base[i:] + base[:i])) for i in range(len(base))) + (
            {"wage": "1", "div": "1", "land": "1", "head": "1", "cons": "1"},
            {"wage": "-2.5", "div": "0.4", "land": "-2.5", "head": "0.4", "cons": "-7"},
            {"wage": "0", "div": "0", "land": "0", "head": "0", "cons": "0"},
        )
        exclusions = ((), ("cons",), ("wage", "land"), ("div", "land", "head", "cons"), tuple(KEYS))
        for direction in ("raise", "cut"):
            statements, rest = tree(tokens(block(self.gen, f"te_tax_gen_ai_pick_{direction}")))
            self.assertEqual(rest, len(tokens(block(self.gen, f"te_tax_gen_ai_pick_{direction}"))))
            for table in tables:
                costs = {key: Decimal(value) for key, value in table.items()}
                for excluded in exclusions:
                    with self.subTest(direction=direction, costs=table, excluded=excluded):
                        sim = PickSim(costs, set(excluded)).run(statements)
                        self.assertEqual((sim.local["te_tax_pick"], sim.local["te_tax_pick2"]),
                                         expected_picks(costs, excluded, direction))
            # Each cost is read once, into a local, then compared.
            body = block(self.gen, f"te_tax_gen_ai_pick_{direction}")
            for key in KEYS:
                with self.subTest(direction=direction, key=key):
                    self.assertEqual(body.count(f"te_tax_ai_cost_{key}"), 1)
                    self.assertEqual(body.count(f"te_tax_ai_excluded_{direction}_{key} = yes"), 1)

    def test_a_step_on_the_picked_instrument_runs_behind_its_own_trigger(self):
        expected = " ".join(
            f"{'if' if code == 1 else 'else_if'} = {{ limit = {{ $INST$ = {code} }} "
            f"if = {{ limit = {{ te_tax_can_draft_step = {{ KEY = {key} DIR = $DIR$ }} }} "
            f"te_tax_cmd_draft_step = {{ KEY = {key} DIR = $DIR$ }} }} }}" for key, code in INSTRUMENT_CODES.items())
        self.assertEqual(flat(block(self.gen, "te_tax_gen_ai_step_inst")), expected)

    def test_the_war_levy_walks_the_sunset_ladder_to_the_levy_length(self):
        ladder_1 = block(read(BILL), "te_tax_dr_sunset_1")
        steps = dict((int(a), int(b)) for a, b in re.findall(
            r"var:te_tax_dr_\$KEY\$_sun = (\d+) \} set_variable = \{ name = te_tax_dr_\$KEY\$_sun value = (\d+)",
            flat(ladder_1)))
        ladder = [0]
        while ladder[-1] in steps:
            ladder.append(steps[ladder[-1]])
        self.assertEqual(tuple(ladder), gen.SUNSET_LADDER)
        levy = int(TUNABLES["te_tax_ai_levy_sunset"])
        self.assertIn(levy, ladder, "a levy's sunset is a step of the ladder")
        attempts = len(ladder) - 1
        expected = []
        for key, code in INSTRUMENT_CODES.items():
            attempt = (f"if = {{ limit = {{ has_variable = te_tax_dr_{key}_sun "
                       f"var:te_tax_dr_{key}_sun < te_tax_ai_levy_sunset }} "
                       f"if = {{ limit = {{ te_tax_can_draft_sunset = {{ KEY = {key} DIR = 1 }} }} "
                       f"te_tax_cmd_draft_sunset = {{ KEY = {key} DIR = 1 }} }} }}")
            expected.append(f"{'if' if code == 1 else 'else_if'} = {{ limit = {{ $INST$ = {code} }} "
                            f"{' '.join([attempt] * attempts)} }}")
        self.assertEqual(flat(block(self.gen, "te_tax_gen_ai_levy_sunset")), " ".join(expected))

    def test_luxury_goods_are_taxed_in_a_fixed_order_within_the_room(self):
        definitions = gen.goods_definitions()
        luxuries = [good for good in gen.consumption_catalog() if definitions[good].get("category") == "luxury"]
        self.assertIn("luxury", gen.GOODS_CATEGORY_WEIGHT)
        order = gen.ai_luxury_order()
        self.assertEqual(sorted(order), sorted(luxuries))
        self.assertEqual(list(order), sorted(luxuries, key=lambda g: (
            -Decimal(definitions[g].get("obsession_chance") or "0"), Decimal(definitions[g].get("cost") or "0"), g)))
        # Vanilla history's own taxed luxuries lead (V: common/history/countries).
        self.assertEqual(set(order[:4]), {"liquor", "tobacco", "opium", "wine"})
        expected = "set_local_variable = { name = te_tax_goods_room value = te_tax_ai_goods_room } " + " ".join(
            f"if = {{ limit = {{ local_var:te_tax_goods_room > 0 te_tax_base_dr_g_{good} = 0 }} "
            f"if = {{ limit = {{ te_tax_can_draft_good = {{ GOOD = {good} }} }} "
            f"te_tax_cmd_draft_good = {{ GOOD = {good} }} "
            f"change_local_variable = {{ name = te_tax_goods_room add = -1 }} }} }}" for good in order)
        self.assertEqual(flat(block(self.gen, "te_tax_gen_ai_tax_luxury")), expected)

    def test_the_generated_parts_call_commands_inside_their_own_triggers(self):
        for name in INITIATIVE_GEN:
            body = block(self.gen, name)
            with self.subTest(name=name):
                self.assertNotRegex(body, r"\b(is_ai|trigger_event|set_variable|change_variable|remove_variable)\b")
                for setter in NATIVE_SETTERS:
                    self.assertNotRegex(body, rf"\b{setter}\b")
            for match in re.finditer(r"\bte_tax_cmd_(\w+) = (\{[^{}]*\}|yes)", body):
                with self.subTest(name=name, call=match.group(0)):
                    brace = enclosing_brace(body, match.start())
                    self.assertRegex(body[:brace].rstrip(), r"(?<!\w)if =$")
                    self.assertEqual(flat(limit_of(body[brace + 1:close(body, brace)])),
                                     f"te_tax_can_{match.group(1)} = {flat(match.group(2))}")

    # -- docs ------------------------------------------------------------------------

    def test_schema_doc_has_the_initiative(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        section = doc.split("\n## AI legislation\n", 1)[1].split("\n## ", 1)[0]
        initiative = section.split("\n### The initiative\n", 1)[1].split("\n### ", 1)[0]
        for phrase in ("te_tax_ai_initiative_ready", "te_tax_ai_need_ended", "te_tax_ai_cost_<key>",
                       "te_tax_ai_excluded_raise_<key>", "te_tax_ai_excluded_cut_<key>", "te_tax_gen_ai_pick_raise",
                       "te_tax_gen_ai_pick_cut", "te_tax_gen_ai_step_inst", "te_tax_gen_ai_levy_sunset",
                       "te_tax_gen_ai_tax_luxury", "te_tax_ai_introduce_and_judge", "te_tax_ai_reverse_since",
                       "reason=draft", "Ruling 12", "te_tax_ai_noviable", "obsession_chance",
                       # Fix round 1: the emergency's pacing and T6 in place of a consumption-rate raise.
                       "Ruling 13", "te_tax_ai_emergency_gate_month", "Ruling 14"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, initiative)
        rows = [line for line in initiative.splitlines() if line.startswith("| ")]
        for template in ("T1", "T2", "T3", "T5", "T6"):
            with self.subTest(template=template):
                self.assertTrue(any(row.startswith(f"| {template} ") for row in rows))
        for name in TUNABLES:
            with self.subTest(tunable=name):
                self.assertIn(f"`{name}`", initiative)
        for path in ("Normal raise", "Emergency", "Cut"):
            with self.subTest(path=path):
                self.assertTrue(any(row.startswith(f"| {path} ") for row in rows))

    def test_ledger_has_the_pre_score_row(self):
        rows = [line for line in read(LEDGER, strip_comments=False).splitlines()
                if line.startswith("| ") and "| AI pre-score vs real support |" in line]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].split(" | ")[2], "static-only")


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
