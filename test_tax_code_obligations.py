# -*- coding: utf-8 -*-
"""Policy obligations of the legislated tax code (plan Task 12; spec §7.2,
"Policy commitment catalog and lifecycle", and §8 steps 2-6).

A promise accepted in a bargain becomes a typed obligation in one of four
slots (te_tax_o1 .. te_tax_o4). These tests pin, structurally:

* each kind's verifier reads the measure the brief names: (1) the delivered
  institution level, `institution:<x>.investment` through the guarded
  te_tax_obl_inst_level_<arg>, compared as `var:target <= level` behind
  `has_institution` (capability ledger: pending P16); (2) `bureaucracy >= 0`;
  (3) `military_wage_level` at or below the promised level; (4)
  `net_fixed_income > 0` for six consecutive monthly checks;
* a bureaucracy deficit never breaches an institution promise: no kind-1
  verifier reads `bureaucracy`, and a deficit month moves a delivering kind-1
  promise's deadline a month later before the deadline is tested;
* maintenance breaches only after te_tax_obl_grace_<kind> consecutive failing
  checks (1 for kinds 1 and 3, 3 for kinds 2 and 4);
* renegotiation is open only once a promise is in force and costs trust;
  a maintenance promise earns no trust when kept; trust fades toward 0;
* fulfilment, breach and renegotiation each write their state exactly once,
  inside a branch guarded by the state they leave, so each consequence applies
  once per transition;
* nothing in the tax code sets an institution's level
  (`set_institution_investment_level`, `change_institution_investment_level`),
  except the AI's enactment of a kind-1 promise it is about to miss (plan
  2026-10-03 Task 19, owner-approved): the generated te_tax_gen_ai_enact_<o>,
  called only by the AI layer;
* the lifecycle links: proposed (1) obligations belong to the bill and are
  released by a new debate or the bill closing; passage binds them (7) to the
  package slot; commencement starts them (2); a package's release or
  emptying supersession releases its bound ones; the monthly check runs from
  the processor only, after commencements and before the sync;
* a civil war: the outbreak copies the binding obligations, never a pending
  one; the win repair reassesses and never fulfils.

Run: python3 -m unittest test_tax_code_obligations -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_scheduler import branches, closure, direct, effects, limit_of
from test_tax_code_state import block, close, gen, read, schema_tokens, top_level_names

ROOT = Path(__file__).resolve().parent

OBL_EFFECTS = "common/scripted_effects/te_tax_obligation_effects.txt"
OBL_VALUES = "common/script_values/te_tax_obligation_values.txt"
OBL_MODIFIERS = "common/static_modifiers/te_tax_obligation_modifiers.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
GEN_CUSTOM_LOC = "common/customizable_localization/te_tax_generated_custom_loc.txt"
BILL = "common/scripted_effects/te_tax_bill_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
CIVIL_WAR = "common/scripted_effects/te_tax_civil_war_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
SGUIS = "common/scripted_guis/te_tax_sguis.txt"
POLITICS = "gui/journal_entry_widgets/te_tax_politics_widget.gui"
OVERVIEW = "gui/journal_entry_widgets/te_tax_overview_widget.gui"
LAYOUT = "gui/journal_entry_widgets/te_tax_layout_widget.gui"
TAX_LOC = "localization/english/te_tax_l_english.yml"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
LEDGER = "docs/testing/tax-code-capability-ledger.md"
GENERATOR = "scripts/generators/gen_tax_code.py"

SLOTS = (1, 2, 3, 4)
PACKAGE_SLOTS = ("a", "b")
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# Kind 1: the institution each _arg names.
INSTITUTIONS = {1: "institution_schools", 2: "institution_health_system", 3: "institution_social_security"}
# Kind 3: the military wage level each _arg names.
WAGE_LEVELS = {1: "very_low", 2: "low", 3: "medium", 4: "high", 5: "very_high"}
# States (docs/systems/tax_code_schema.md, "Policy obligations").
PENDING, DELIVERING, MAINTAINING, FULFILLED, BREACHED, RENEGOTIATED, BOUND = 1, 2, 3, 4, 5, 6, 7
# History kinds the obligations add to the ring.
KIND_FULFILLED, KIND_BREACHED, KIND_RENEGOTIATED, KIND_RELEASED = 11, 12, 13, 14
HEADER = ("on", "state")


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def trigger_branches(body):
    """[(limit, rest)] for every trigger_if / trigger_else_if in `body`, normalised."""
    found = []
    for match in re.finditer(r"\btrigger_(?:else_)?if = \{", body):
        inner = body[match.end():close(body, match.end() - 1)]
        lim = re.match(r"\s*limit = \{", inner)
        if lim is None:
            continue
        end = close(inner, lim.end() - 1)
        found.append((norm(inner[lim.end():end]), norm(inner[end + 1:])))
    return found


def all_tax_text(directories=("common", "events")):
    """{path: text} for every te_tax_* script file."""
    out = {}
    for directory in directories:
        for path in sorted((ROOT / directory).rglob("te_tax_*.txt")):
            out[path.relative_to(ROOT).as_posix()] = read(path.relative_to(ROOT).as_posix())
    return out


def loc():
    keys = {}
    for path in sorted((ROOT / "localization/english").glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if match:
                keys[match.group(1)] = match.group(2)
    return keys


class FilesTest(unittest.TestCase):
    def test_new_files_have_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in (OBL_EFFECTS, OBL_VALUES, OBL_MODIFIERS):
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)

    def test_debug_lines_carry_the_stamp_and_no_parameters(self):
        lines = re.findall(r'debug_log = "([^"]*)"', read(OBL_EFFECTS))
        self.assertTrue(lines)
        for line in lines:
            with self.subTest(line=line[:50]):
                self.assertTrue(line.startswith("TE_TAX obl_"))
                self.assertNotIn("$", line)
                self.assertIn("date=[TimeKeeper.GetCurrentDate.GetString]", line)

    def test_never_reads_root(self):
        self.assertNotRegex(read(OBL_EFFECTS), r"\bROOT\b|\broot\b")

    def test_every_tooltip_key_is_localised(self):
        table = loc()
        keys = set(re.findall(r"custom_tooltip = (te_tax_tt_\w+)", read(OBL_EFFECTS)))
        keys |= set(re.findall(r"text = (te_tax_tt_obl_\w+)", read(TRIGGERS)))
        self.assertIn("te_tax_tt_cmd_obl_renegotiate", keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertTrue(table.get(key), key)

    def test_nothing_sets_an_institution_level(self):
        """A promise is verified against the delivered level; setting it would
        bypass native expansion time (research E §C). The one exception is the
        owner's (plan 2026-10-03 Task 19): an AI country's kind-1 promise the
        native AI is about to miss is set to its target, by the generated
        te_tax_gen_ai_enact_<o> alone, which only the AI layer calls."""
        texts = all_tax_text()
        enact = re.compile(r"(?m)^te_tax_gen_ai_enact_\d+ = \{")
        self.assertEqual(len(enact.findall(texts[GEN_EFFECTS])), len(SLOTS))
        for path, text in texts.items():
            with self.subTest(path=path):
                if path == GEN_EFFECTS:
                    for match in enact.finditer(text):
                        text = text[:match.start()] + " " * (close(text, match.end() - 1) + 1 - match.start()) \
                            + text[close(text, match.end() - 1) + 1:]
                self.assertNotIn("set_institution_investment_level", text)
                self.assertNotIn("change_institution_investment_level", text)
        generator = (ROOT / GENERATOR).read_text(encoding="utf-8")
        self.assertNotIn("change_institution_investment_level", generator)
        self.assertEqual(generator.count("set_institution_investment_level"), 1)
        emitter = generator.split("set_institution_investment_level", 1)[0].rsplit("\ndef ", 1)[1]
        self.assertTrue(emitter.startswith("_ai_obligation_effects("), emitter[:40])


class VerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = read(TRIGGERS)
        cls.holds = block(cls.triggers, "te_tax_obl_holds")
        cls.delivered = block(cls.triggers, "te_tax_obl_delivered")

    def test_kind_1_reads_the_delivered_institution_level_behind_has_institution(self):
        for arg, institution in INSTITUTIONS.items():
            body = norm(block(self.triggers, f"te_tax_obl_inst_met_{arg}"))
            with self.subTest(institution=institution):
                self.assertIn(f"trigger_if = {{ limit = {{ has_institution = {institution} }} "
                              f"var:te_tax_o$N$_target <= te_tax_obl_inst_level_{arg} }}", body)
                self.assertNotIn(".investment", body)
                self.assertTrue(body.endswith("trigger_else = { always = no }"))
                self.assertNotIn("expanding_institution", body)
        # The kind-1 branch of the monthly condition dispatches on the institution.
        kind_1 = [rest for lim, rest in trigger_branches(self.holds) if lim == "var:te_tax_o$N$_kind = 1"]
        self.assertEqual(len(kind_1), 1)
        for arg in INSTITUTIONS:
            self.assertIn(f"trigger_if = {{ limit = {{ var:te_tax_o$N$_arg = {arg} }} "
                          f"te_tax_obl_inst_met_{arg} = {{ N = $N$ }} }}"
                          if arg == 1 else
                          f"trigger_else_if = {{ limit = {{ var:te_tax_o$N$_arg = {arg} }} "
                          f"te_tax_obl_inst_met_{arg} = {{ N = $N$ }} }}", kind_1[0])

    def test_kind_2_reads_the_bureaucracy_balance(self):
        kind_2 = [rest for lim, rest in trigger_branches(self.holds) if lim == "var:te_tax_o$N$_kind = 2"]
        self.assertEqual(kind_2, ["bureaucracy >= 0"])

    def test_kind_3_samples_the_military_wage_level(self):
        kind_3 = [rest for lim, rest in trigger_branches(self.holds) if lim == "var:te_tax_o$N$_kind = 3"]
        self.assertEqual(kind_3, ["te_tax_obl_wages_met = { N = $N$ }"])
        wages = block(self.triggers, "te_tax_obl_wages_met")
        found = {lim: rest for lim, rest in trigger_branches(wages)}
        for arg, level in WAGE_LEVELS.items():
            with self.subTest(level=level):
                self.assertEqual(found[f"var:te_tax_o$N$_arg = {arg}"], f"military_wage_level <= {level}")
        self.assertTrue(norm(wages).endswith("trigger_else = { always = no }"))

    def test_kind_4_needs_six_consecutive_surplus_months(self):
        kind_4 = [rest for lim, rest in trigger_branches(self.holds) if lim == "var:te_tax_o$N$_kind = 4"]
        self.assertEqual(kind_4, ["net_fixed_income > 0"])
        delivered = {lim: rest for lim, rest in trigger_branches(self.delivered)}
        self.assertEqual(delivered["var:te_tax_o$N$_kind = 4"], "var:te_tax_o$N$_streak >= te_tax_obl_surplus_months")
        self.assertIn("te_tax_obl_holds = { N = $N$ }", norm(self.delivered))
        self.assertEqual(read(OBL_VALUES).count("te_tax_obl_surplus_months = 6"), 1)

    def test_unknown_kinds_fail_closed(self):
        for body in (self.holds, self.delivered):
            self.assertTrue(norm(body).endswith("trigger_else = { always = no }"))

    def test_a_bureaucracy_deficit_never_breaches_an_institution_promise(self):
        for arg in INSTITUTIONS:
            self.assertNotIn("bureaucracy", block(self.triggers, f"te_tax_obl_inst_met_{arg}"))
        kind_1 = [rest for lim, rest in trigger_branches(self.holds) if lim == "var:te_tax_o$N$_kind = 1"]
        self.assertNotIn("bureaucracy", kind_1[0])
        # The check reads bureaucracy only to pause a kind-1 deadline (LifecycleTest), and through
        # te_tax_obl_holds' kind-2 branch; never to breach.
        effects = read(OBL_EFFECTS).replace("te_tax_obl_deadline_bureaucracy", "")
        self.assertEqual(re.findall(r"bureaucracy [<>=]+ \d+", effects), ["bureaucracy < 0"])

    def test_never_trigger_if_inside_an_or(self):
        for name in ("te_tax_obl_holds", "te_tax_obl_delivered", "te_tax_obl_wages_met",
                     *(f"te_tax_obl_inst_met_{arg}" for arg in INSTITUTIONS)):
            body = block(self.triggers, name)
            for match in re.finditer(r"\bOR = \{", body):
                inner = body[match.end():close(body, match.end() - 1)]
                with self.subTest(name=name):
                    self.assertNotIn("trigger_if", inner)


class FeasibilityTest(unittest.TestCase):
    """Task 13 asks these before it offers a promise (brief: kind 1 needs the
    institution, a target within its cap, and a deadline within 60 months)."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = read(TRIGGERS)
        cls.values = read(OBL_VALUES)

    def test_one_feasibility_trigger_per_kind(self):
        names = set(top_level_names(self.triggers))
        for kind in (1, 2, 3, 4):
            self.assertIn(f"te_tax_obl_feasible_{kind}", names)

    def test_kind_1_needs_the_institution_its_cap_and_a_deadline_within_the_horizon(self):
        self.assertIn("te_tax_obl_inst_feasible_$ARG$ = { TARGET = $TARGET$ }",
                      norm(block(self.triggers, "te_tax_obl_feasible_1")))
        for arg, institution in INSTITUTIONS.items():
            body = norm(block(self.triggers, f"te_tax_obl_inst_feasible_{arg}"))
            with self.subTest(institution=institution):
                self.assertIn(f"has_institution = {institution}", body)
                self.assertIn(f"te_tax_obl_inst_cap_{arg} >= $TARGET$", body)
                self.assertIn(f"te_tax_obl_inst_reach_{arg} >= $TARGET$", body)
                level = norm(block(self.values, f"te_tax_obl_inst_level_{arg}"))
                self.assertIn(f"limit = {{ has_institution = {institution} }}", level)
                self.assertIn(f"institution:{institution} = {{ add = investment }}", level)
                cap = norm(block(self.values, f"te_tax_obl_inst_cap_{arg}"))
                self.assertIn(f"institution:{institution} = {{ add = investment_max }}", cap)
                reach = norm(block(self.values, f"te_tax_obl_inst_reach_{arg}"))
                self.assertIn(f"value = te_tax_obl_inst_level_{arg} add = te_tax_obl_max_levels", reach)

    def test_the_horizon_gives_four_levels(self):
        # 12 x (target - level) + 6 <= 60  <=>  target - level <= 4.
        self.assertIn("te_tax_obl_horizon = 60", self.values)
        self.assertIn("te_tax_obl_months_per_level = 12", self.values)
        self.assertIn("te_tax_obl_inst_grace = 6", self.values)
        body = norm(block(self.values, "te_tax_obl_max_levels"))
        self.assertEqual(body, "value = te_tax_obl_horizon subtract = te_tax_obl_inst_grace "
                               "divide = te_tax_obl_months_per_level floor = yes")

    def test_is_maintenance_for_task_13(self):
        self.assertEqual(norm(block(self.triggers, "te_tax_obl_is_maintenance")),
                         "te_tax_obl_is_maintenance_$KIND$ = { ARG = $ARG$ TARGET = $TARGET$ }")
        # The two budget kinds read the fiscal record of the 1st (final review A-I2).
        # Kinds that need neither argument name them where they never run: the
        # dispatcher passes both to every kind, and the engine refuses a call
        # that passes an argument the body never names (2026-10-05 log).
        unused = "trigger_if = { limit = { always = no } $TARGET$ >= $ARG$ }"
        for kind, body in ((1, "te_tax_obl_inst_level_$ARG$ >= $TARGET$"),
                           (2, f"te_tax_fisc_rec_bur_ok = yes {unused}"),
                           (3, "NOT = { te_tax_obl_wages_above_$ARG$ = yes } "
                               "trigger_if = { limit = { always = no } $TARGET$ >= 0 }"),
                           (4, f"te_tax_fisc_rec_surplus = yes {unused}")):
            with self.subTest(kind=kind):
                helper = norm(block(self.triggers, f"te_tax_obl_is_maintenance_{kind}"))
                self.assertEqual(helper, body)
                self.assertIn("$ARG$", helper)
                self.assertIn("$TARGET$", helper)

    def test_kind_3_is_a_cut_not_a_restraint(self):
        body = norm(block(self.triggers, "te_tax_obl_feasible_3"))
        self.assertIn("te_tax_obl_wages_above_$ARG$ = yes", body)
        for arg, level in WAGE_LEVELS.items():
            above = norm(block(self.triggers, f"te_tax_obl_wages_above_{arg}"))
            with self.subTest(level=level):
                self.assertEqual(above, "always = no" if arg == 5 else f"military_wage_level > {level}")


class ProposeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(OBL_EFFECTS)
        cls.triggers = read(TRIGGERS)
        cls.propose = block(cls.text, "te_tax_obl_propose")
        cls.write = block(cls.text, "te_tax_obl_write")

    def test_propose_runs_only_when_allowed_and_fills_the_lowest_free_slot(self):
        self.assertRegex(self.propose, r"^\s*if = \{\s*limit = \{ te_tax_can_obl_propose = "
                                       r"\{ KIND = \$KIND\$ ARG = \$ARG\$ \} \}")
        for n in SLOTS:
            self.assertRegex(self.propose, rf"limit = \{{ var:te_tax_o{n}_on = 0 \}}\s*te_tax_obl_write = "
                                           rf"\{{ N = {n} KIND = \$KIND\$ ARG = \$ARG\$ TARGET = \$TARGET\$ "
                                           rf"IG = \$IG\$ \}}")
        self.assertIn('debug_log = "TE_TAX obl_propose_refused', self.propose)

    def test_the_write_is_whole_and_turns_the_slot_on_last(self):
        names = re.findall(r"set_variable = \{ name = te_tax_o\$N\$_(\w+) value = ([^}]+?) \}", self.write)
        fields = dict(names)
        for field, value in (("kind", "$KIND$"), ("arg", "$ARG$"), ("target", "$TARGET$"), ("ig", "$IG$"),
                             ("rev", "var:te_tax_bl_rev"), ("slot", "0"), ("deadline", "-1"),
                             ("maint_end", "-1"), ("streak", "0"), ("fails", "0"), ("state", str(PENDING)),
                             ("on", "1")):
            with self.subTest(field=field):
                self.assertEqual(fields.get(field), value)
        self.assertIn("te_tax_obl_record_baseline = { N = $N$ }", self.write)
        # Existing provision is labelled maintenance (spec 7.2): what it asks for already holds,
        # by the test the offer was priced with (final review A-I2: the budget kinds read the
        # fiscal record of the 1st, not the live budget).
        self.assertIn("if = { limit = { te_tax_obl_is_maintenance = { KIND = $KIND$ ARG = $ARG$ TARGET = $TARGET$ } } "
                      "set_variable = { name = te_tax_o$N$_maint_only "
                      "value = 1 } } else = { set_variable = { name = te_tax_o$N$_maint_only value = 0 } }",
                      norm(self.write))
        self.assertLess(self.write.find("te_tax_obl_record_baseline"), self.write.find("te_tax_o$N$_maint_only"))
        last = self.write[self.write.rfind("set_variable"):]
        self.assertTrue(last.startswith("set_variable = { name = te_tax_o$N$_on value = 1 }"))

    def test_the_trigger_refuses_duplicates_and_full_slots_with_a_line_each(self):
        body = norm(block(self.triggers, "te_tax_can_obl_propose"))
        self.assertIn("custom_tooltip = { text = te_tax_tt_code_in_force te_tax_code_in_force = yes }", body)
        self.assertIn("custom_tooltip = { text = te_tax_tt_bill_open te_tax_bill_active = yes }", body)
        self.assertIn("text = te_tax_tt_obl_not_duplicate NOR = {", body)
        for n in SLOTS:
            # The same kind and argument; two military wage promises never coexist.
            self.assertIn(f"AND = {{ has_variable = te_tax_o{n}_on var:te_tax_o{n}_on = 1 "
                          f"has_variable = te_tax_o{n}_kind var:te_tax_o{n}_kind = $KIND$ "
                          f"OR = {{ var:te_tax_o{n}_arg = $ARG$ var:te_tax_o{n}_kind = 3 }} }}", body)
        self.assertIn("text = te_tax_tt_obl_slot_free OR = { " + " ".join(
            f"var:te_tax_o{n}_on = 0" for n in SLOTS) + " }", body)


class LifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(OBL_EFFECTS)
        cls.defined = effects()

    def test_a_new_debate_and_a_closing_bill_release_pending_promises(self):
        bill = read(BILL)
        # Task 13: a new debate opens its revision first (te_tax_bill_open_revision).
        self.assertIn("te_tax_bill_open_revision = yes", block(bill, "te_tax_bill_start_debate"))
        self.assertIn("te_tax_obl_release_pending = yes", block(bill, "te_tax_bill_open_revision"))
        self.assertIn("te_tax_obl_release_pending = yes", block(bill, "te_tax_bill_close"))
        release = block(self.text, "te_tax_obl_release_pending")
        for n in SLOTS:
            self.assertIn(f"te_tax_obl_release_pending_one = {{ N = {n} }}", release)
        pending = norm(block(self.text, "te_tax_obl_release_pending_one"))
        self.assertIn(f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {PENDING} }} "
                      "te_tax_obl_release_one = { N = $N$ }", pending)
        # The bill's own lifecycle: no history entry, nothing binding touched.
        reach = closure({"te_tax_obl_release_pending"}, self.defined)
        self.assertNotIn("te_tax_history_push", reach)
        one = block(self.text, "te_tax_obl_release_one")
        self.assertIn("set_variable = { name = te_tax_o$N$_on value = 0 }", one)
        self.assertIn("set_variable = { name = te_tax_o$N$_state value = 0 }", one)

    def test_passage_binds_this_revisions_promises_to_the_package_slot(self):
        into = block(read(BILL), "te_tax_pass_into")
        order = [into.find(step) for step in ("te_tax_store_package = { SLOT = $SLOT$ }",
                                               "te_tax_obl_bind = { SLOT = $SLOT$ }",
                                               "te_tax_gen_oppose_approval = yes", "te_tax_bill_close = yes")]
        self.assertTrue(all(position >= 0 for position in order))
        self.assertEqual(order, sorted(order))
        one = norm(block(self.text, "te_tax_obl_bind_one"))
        self.assertIn(f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {PENDING}", one)
        self.assertIn("var:te_tax_o$N$_rev = var:te_tax_bl_rev", one)
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {BOUND} }}", one)
        self.assertIn("set_variable = { name = te_tax_o$N$_slot value = te_tax_slot_id_$SLOT$ }", one)

    def test_commencement_starts_the_slots_bound_promises(self):
        generated = read(GEN_EFFECTS)
        for slot in PACKAGE_SLOTS:
            body = block(generated, f"te_tax_gen_commence_{slot}")
            applies = [nested for kind, nested in branches(body) if f"te_tax_gen_apply_{slot} = yes" in direct(nested)]
            with self.subTest(slot=slot):
                self.assertEqual(len(applies), 1)
                self.assertIn(f"te_tax_obl_start = {{ SLOT = {slot} }}", direct(applies[0]))
        callers = sorted(name for name, body in self.defined.items()
                         if re.search(r"te_tax_obl_start = \{", body))
        self.assertEqual(callers, ["te_tax_gen_commence_a", "te_tax_gen_commence_b"])

    def test_start_sets_each_kinds_clock_from_this_month(self):
        one = norm(block(self.text, "te_tax_obl_start_one"))
        self.assertIn(f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {BOUND} "
                      "var:te_tax_o$N$_slot = te_tax_slot_id_$SLOT$", one)
        self.assertIn("te_tax_obl_record_baseline = { N = $N$ }", one)
        # Kind 1: now + 12 x (target - delivered level, at least 0) + 6.
        for step in ("set_variable = { name = te_tax_o$N$_deadline value = var:te_tax_o$N$_target }",
                     "change_variable = { name = te_tax_o$N$_deadline subtract = var:te_tax_o$N$_baseline }",
                     "change_variable = { name = te_tax_o$N$_deadline multiply = te_tax_obl_months_per_level }",
                     "change_variable = { name = te_tax_o$N$_deadline add = te_tax_obl_inst_grace }"):
            self.assertIn(step, one)
        self.assertIn("limit = { var:te_tax_o$N$_deadline < 0 } set_variable = { name = te_tax_o$N$_deadline "
                      "value = 0 }", one)
        for constant in ("te_tax_obl_deadline_bureaucracy", "te_tax_obl_deadline_wages",
                         "te_tax_obl_deadline_fiscal"):
            self.assertIn(f"value = {constant}", one)
        self.assertIn("change_variable = { name = te_tax_o$N$_deadline add = var:te_tax_now }", one)
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {DELIVERING} }}", one)
        values = read(OBL_VALUES)
        for line in ("te_tax_obl_deadline_bureaucracy = 12", "te_tax_obl_deadline_wages = 1",
                     "te_tax_obl_deadline_fiscal = 24", "te_tax_obl_maint_months = 24",
                     "te_tax_obl_maint_months_fiscal = 12"):
            self.assertIn(line, values)

    def test_releasing_or_emptying_a_package_releases_its_bound_promises(self):
        self.assertIn("te_tax_obl_release_slot = { SLOT = $SLOT$ }", block(read(BILL), "te_tax_cmd_package_release"))
        generated = read(GEN_BILL)
        for slot in PACKAGE_SLOTS:
            body = block(generated, f"te_tax_gen_supersede_{slot}")
            emptied = [nested for kind, nested in branches(body)
                       if f"te_tax_gen_package_empty_{slot} = yes" in limit_of(nested)]
            with self.subTest(slot=slot):
                self.assertEqual(len(emptied), 1)
                self.assertIn(f"te_tax_obl_release_slot = {{ SLOT = {slot} }}", emptied[0])
        release = norm(block(self.text, "te_tax_obl_release_slot"))
        self.assertIn(f"te_tax_history_push = {{ KIND = {KIND_RELEASED} SLOT = $SLOT$ }}", release)
        one = norm(block(self.text, "te_tax_obl_release_bound"))
        self.assertIn(f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {BOUND} "
                      "var:te_tax_o$N$_slot = te_tax_slot_id_$SLOT$", one)
        # No breach, no approval: the bargain lapsed with its package.
        reach = closure({"te_tax_obl_release_slot"}, self.defined)
        for name in reach:
            self.assertNotIn("ig_approval_effect", self.defined[name])
            self.assertNotIn("te_tax_trust_", self.defined[name])

    def test_the_monthly_check_runs_from_the_processor_after_commencements_before_the_sync(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        check = body.find("te_tax_obl_check_month = yes")
        self.assertGreater(check, body.rfind("te_tax_gen_commence_"))
        self.assertLess(check, body.find("te_tax_sync_collection = yes"))
        callers = sorted(name for name, text in self.defined.items() if "te_tax_obl_check_month = yes" in text)
        self.assertEqual(callers, ["te_tax_process_month"])
        self.assertNotIn("te_tax_obl_check_month", block(read(SCHEDULE), "te_tax_watchdog_month"))
        for directory, pattern in (("gui", "*.gui"), ("common/scripted_guis", "*.txt")):
            for path in sorted((ROOT / directory).rglob(pattern)):
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                with self.subTest(path=path.name):
                    for name in ("te_tax_obl_check", "te_tax_obl_fulfil", "te_tax_obl_breach", "te_tax_obl_start"):
                        self.assertNotIn(name, text)
        month = block(self.text, "te_tax_obl_check_month")
        for n in SLOTS:
            self.assertIn(f"te_tax_obl_check_one = {{ N = {n} }}", month)

    def test_a_deficit_pauses_an_institution_deadline_before_it_is_tested(self):
        one = block(self.text, "te_tax_obl_check_one")
        delivering = [nested for kind, nested in branches(one)
                      if norm(limit_of(nested)) == f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {DELIVERING}"][0]
        pauses = [nested for kind, nested in branches(delivering)
                  if norm(limit_of(nested)) == "var:te_tax_o$N$_kind = 1 bureaucracy < 0"]
        self.assertEqual(len(pauses), 1)
        self.assertIn("change_variable = { name = te_tax_o$N$_deadline add = 1 }", pauses[0])
        self.assertNotIn("te_tax_obl_breach", pauses[0])
        self.assertTrue(any(line.startswith("TE_TAX obl_paused") for line in re.findall(r'debug_log = "([^"]*)"',
                                                                                         pauses[0])))
        d = norm(delivering)
        self.assertLess(d.find("te_tax_obl_delivered"), d.find("bureaucracy < 0"))
        self.assertLess(d.find("bureaucracy < 0"), d.find("var:te_tax_o$N$_deadline <= var:te_tax_now"))
        self.assertRegex(d, r"else_if = \{ limit = \{ var:te_tax_o\$N\$_kind = 1 bureaucracy < 0 \} .*"
                            r"\} else_if = \{ limit = \{ var:te_tax_o\$N\$_deadline <= var:te_tax_now \}")

    def test_maintenance_grace_by_kind(self):
        values = read(OBL_VALUES)
        for kind, grace in ((1, 1), (2, 3), (3, 1), (4, 3)):
            self.assertIn(f"te_tax_obl_grace_{kind} = {grace}", values)
        reached = {lim: rest for lim, rest in trigger_branches(read(TRIGGERS).split("te_tax_obl_grace_reached = {", 1)[1]
                                                              .split("\n}\n", 1)[0])}
        for kind in (1, 2, 3, 4):
            self.assertEqual(reached[f"var:te_tax_o$N$_kind = {kind}"],
                             f"var:te_tax_o$N$_fails >= te_tax_obl_grace_{kind}")

    def test_trust_fades_toward_zero_after_24_months(self):
        month = block(self.text, "te_tax_obl_check_month")
        self.assertLess(month.find("te_tax_gen_trust_recover = yes"), month.find("te_tax_obl_check_one"))
        self.assertIn("te_tax_obl_trust_recover_months = 24", read(OBL_VALUES))
        recover = norm(block(read(GEN_BILL), "te_tax_gen_trust_recover"))
        trust = norm(block(read(GEN_BILL), "te_tax_gen_obl_trust"))
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"limit = {{ has_variable = te_tax_trust_{ig} has_variable = te_tax_trust_{ig}_month "
                              f"var:te_tax_trust_{ig}_month <= te_tax_obl_trust_recover_before }}", recover)
                self.assertIn(f"if = {{ limit = {{ var:te_tax_trust_{ig} > 0 }} change_variable = {{ name = "
                              f"te_tax_trust_{ig} add = -1 }}", recover)
                self.assertIn(f"else_if = {{ limit = {{ var:te_tax_trust_{ig} < 0 }} change_variable = {{ name = "
                              f"te_tax_trust_{ig} add = 1 }}", recover)
                self.assertIn(f"set_variable = {{ name = te_tax_trust_{ig}_month value = te_history_month_index }}",
                              trust)

    def test_check_delivers_maintains_fulfils_or_breaches(self):
        one = block(self.text, "te_tax_obl_check_one")
        delivering = [nested for kind, nested in branches(one)
                      if norm(limit_of(nested)) == f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {DELIVERING}"]
        maintaining = [nested for kind, nested in branches(one)
                       if norm(limit_of(nested)) == f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {MAINTAINING}"]
        self.assertEqual((len(delivering), len(maintaining)), (1, 1))
        d = norm(delivering[0])
        # Kind 4 counts consecutive surplus months first; a deficit month resets it.
        self.assertIn("limit = { var:te_tax_o$N$_kind = 4 } if = { limit = { net_fixed_income > 0 } "
                      "change_variable = { name = te_tax_o$N$_streak add = 1 } } else = { set_variable = "
                      "{ name = te_tax_o$N$_streak value = 0 } }", d)
        self.assertLess(d.find("net_fixed_income"), d.find("te_tax_obl_delivered"))
        # The deadline line (plan 2026-10-03 Task 19, obl_deadline met or unmet) is written just before
        # the delivered promise starts maintenance, and just before the deadline breach.
        self.assertIn("limit = { te_tax_obl_delivered = { N = $N$ } } te_tax_gen_obl_log_met_$N$ = yes "
                      "te_tax_obl_begin_maintenance = { N = $N$ }", d)
        self.assertIn("limit = { var:te_tax_o$N$_deadline <= var:te_tax_now } te_tax_gen_obl_log_unmet_$N$ = yes "
                      "te_tax_obl_breach = { N = $N$ }", d)
        m = norm(maintaining[0])
        # A month that holds resets the failing count and, at the end of the term, fulfils.
        self.assertIn("if = { limit = { te_tax_obl_holds = { N = $N$ } } set_variable = { name = te_tax_o$N$_fails "
                      "value = 0 } if = { limit = { var:te_tax_o$N$_maint_end <= var:te_tax_now } "
                      "te_tax_obl_fulfil = { N = $N$ } } }", m)
        # A failing month counts; the kind's grace in consecutive failures breaches.
        self.assertIn("else = { change_variable = { name = te_tax_o$N$_fails add = 1 } if = { limit = { "
                      "te_tax_obl_grace_reached = { N = $N$ } } te_tax_obl_breach = { N = $N$ } }", m)
        begin = norm(block(self.text, "te_tax_obl_begin_maintenance"))
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {MAINTAINING} }}", begin)
        self.assertIn("set_variable = { name = te_tax_o$N$_fails value = 0 }", begin)
        self.assertIn("value = te_tax_obl_maint_months_fiscal", begin)
        self.assertIn("value = te_tax_obl_maint_months", begin)


class ConsequenceTest(unittest.TestCase):
    """Fulfilment and breach apply once (brief: +3 / -5 through ig_approval_effect,
    trust +-1); renegotiation costs -2 and frees the slot."""

    @classmethod
    def setUpClass(cls):
        cls.text = read(OBL_EFFECTS)
        cls.all = "\n".join(all_tax_text().values())

    def guarded(self, name, guard):
        body = block(self.text, name)
        self.assertRegex(body, r"^\s*if = \{\s*limit = \{ " + re.escape(guard) + r" \}")
        opener = body.find("if = {") + len("if = {") - 1
        self.assertEqual(body[close(body, opener) + 1:].strip(), "", f"{name}: nothing outside the guard")
        return body

    def test_each_outcome_state_is_written_once_in_the_whole_tax_code(self):
        for state in (FULFILLED, BREACHED, RENEGOTIATED, BOUND, DELIVERING, MAINTAINING):
            writes = re.findall(rf"set_variable = \{{ name = te_tax_o[\w$]+_state value = {state} \}}", self.all)
            with self.subTest(state=state):
                self.assertEqual(len(writes), 1)

    def test_fulfilment_is_guarded_by_maintenance_and_rewards_once(self):
        body = norm(self.guarded("te_tax_obl_fulfil", f"var:te_tax_o$N$_on = 1 var:te_tax_o$N$_state = {MAINTAINING}"))
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {FULFILLED} }}", body)
        self.assertIn("set_variable = { name = te_tax_o$N$_on value = 0 }", body)
        self.assertIn("te_tax_gen_obl_approval = { N = $N$ MODIFIER = te_tax_obl_kept_modifier }", body)
        # A maintenance promise kept earns approval only.
        self.assertIn("if = { limit = { has_variable = te_tax_o$N$_maint_only var:te_tax_o$N$_maint_only = 0 } "
                      "te_tax_gen_obl_trust = { N = $N$ DELTA = 1 } }", body)
        self.assertIn(f"te_tax_history_push = {{ KIND = {KIND_FULFILLED} SLOT = none }}", body)
        self.assertLess(body.find(f"value = {FULFILLED}"), body.find("te_tax_gen_obl_approval"))

    def test_breach_is_guarded_by_a_binding_state_and_penalises_once(self):
        body = norm(self.guarded(
            "te_tax_obl_breach",
            f"var:te_tax_o$N$_on = 1 OR = {{ var:te_tax_o$N$_state = {DELIVERING} "
            f"var:te_tax_o$N$_state = {MAINTAINING} }}"))
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {BREACHED} }}", body)
        self.assertIn("set_variable = { name = te_tax_o$N$_on value = 0 }", body)
        self.assertIn("te_tax_gen_obl_approval = { N = $N$ MODIFIER = te_tax_obl_broken_modifier }", body)
        self.assertIn("te_tax_gen_obl_trust = { N = $N$ DELTA = -1 }", body)
        self.assertIn(f"te_tax_history_push = {{ KIND = {KIND_BREACHED} SLOT = none }}", body)

    def test_renegotiation_is_a_command_costing_two_approval_and_trust(self):
        body = norm(self.guarded("te_tax_cmd_obl_renegotiate", "te_tax_can_obl_renegotiate = { N = $N$ }"))
        self.assertIn("custom_tooltip = te_tax_tt_cmd_obl_renegotiate", body)
        self.assertIn(f"set_variable = {{ name = te_tax_o$N$_state value = {RENEGOTIATED} }}", body)
        self.assertIn("set_variable = { name = te_tax_o$N$_on value = 0 }", body)
        self.assertIn("te_tax_gen_obl_approval = { N = $N$ MODIFIER = te_tax_obl_renegotiated_modifier }", body)
        self.assertIn("te_tax_gen_obl_trust = { N = $N$ DELTA = -1 }", body)
        self.assertIn(f"te_tax_history_push = {{ KIND = {KIND_RENEGOTIATED} SLOT = none }}", body)
        trigger = norm(block(read(TRIGGERS), "te_tax_can_obl_renegotiate"))
        self.assertIn("custom_tooltip = { text = te_tax_tt_code_in_force te_tax_code_in_force = yes }", trigger)
        # Only once in force: a bound promise lapses only with its package.
        self.assertIn("custom_tooltip = { text = te_tax_tt_obl_active te_tax_obl_active = { N = $N$ } }", trigger)
        self.assertNotIn("te_tax_obl_binding", trigger)
        active = norm(block(read(TRIGGERS), "te_tax_obl_active"))
        self.assertEqual(active, f"has_variable = te_tax_o$N$_on var:te_tax_o$N$_on = 1 OR = {{ "
                                 f"var:te_tax_o$N$_state = {DELIVERING} var:te_tax_o$N$_state = {MAINTAINING} }}")
        binding = norm(block(read(TRIGGERS), "te_tax_obl_binding"))
        self.assertEqual(binding, f"has_variable = te_tax_o$N$_on var:te_tax_o$N$_on = 1 OR = {{ "
                                  f"var:te_tax_o$N$_state = {BOUND} var:te_tax_o$N$_state = {DELIVERING} "
                                  f"var:te_tax_o$N$_state = {MAINTAINING} }}")

    def test_dedicated_modifiers_kept_broken_renegotiated(self):
        from test_tax_code_rule import load
        modifiers = load(OBL_MODIFIERS)
        want = {"te_tax_obl_kept_modifier": ("3", "Kept Tax Promise"),
                "te_tax_obl_broken_modifier": ("-5", "Broken Tax Promise"),
                "te_tax_obl_renegotiated_modifier": ("-2", "Renegotiated Tax Promise")}
        self.assertEqual(set(modifiers), set(want))
        table = loc()
        for name, (value, label) in want.items():
            with self.subTest(name=name):
                self.assertEqual(modifiers[name]["interest_group_approval_add"], value)
                self.assertIn("icon", modifiers[name])
                self.assertEqual(table.get(name), label)
                self.assertTrue(table.get(f"{name}_desc"))
        self.assertNotRegex(read(OBL_EFFECTS), r"ig_approval_(positive|very_negative)_modifier")

    def test_approval_goes_through_the_shared_macro_for_the_beneficiary(self):
        body = block(read(GEN_BILL), "te_tax_gen_obl_approval")
        for n, ig in enumerate(IGS, start=1):
            with self.subTest(ig=ig):
                self.assertIn(f"limit = {{ var:te_tax_o$N$_ig = {n} }} ig_approval_effect = {{ IG = ig_{ig} "
                              "MODIFIER = $MODIFIER$ DAYS = te_tax_obl_approval_days }", norm(body))
        self.assertIn("te_tax_obl_approval_days = 180", read(OBL_VALUES))

    def test_trust_moves_one_step_and_is_clamped_both_ways(self):
        body = norm(block(read(GEN_BILL), "te_tax_gen_obl_trust"))
        for n, ig in enumerate(IGS, start=1):
            with self.subTest(ig=ig):
                self.assertIn(f"limit = {{ var:te_tax_o$N$_ig = {n} }} change_variable = {{ name = te_tax_trust_{ig} "
                              f"add = $DELTA$ }} clamp_variable = {{ name = te_tax_trust_{ig} min = -4 max = 4 }}", body)

    def test_trust_feeds_the_support_reason_ten_points_a_promise(self):
        refresh = norm(block(read(GEN_BILL), "te_tax_gen_refresh_support"))
        values = read(GEN_SUPPORT)
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"set_variable = {{ name = te_tax_sr_{ig}_trust value = te_tax_trust_reason_{ig} }}",
                              refresh)
                reason = norm(block(values, f"te_tax_trust_reason_{ig}"))
                self.assertEqual(reason, f"value = 0 if = {{ limit = {{ has_variable = te_tax_trust_{ig} }} "
                                         f"value = var:te_tax_trust_{ig} multiply = 10 }} min = -40 max = 40")


class FiscalRecordTest(unittest.TestCase):
    """Final review A-I2: the fiscal reason and the budget promises' maintenance
    test read the budget as the processor recorded it on the 1st, never the
    live figure a player can tip into deficit for a few days."""

    RECORD = {"te_tax_fisc_deficit": "net_fixed_income < 0", "te_tax_fisc_surplus": "net_fixed_income > 0",
              "te_tax_fisc_bur_ok": "bureaucracy >= 0"}

    @classmethod
    def setUpClass(cls):
        cls.snapshot = read("common/scripted_effects/te_tax_snapshot_effects.txt")
        cls.triggers = read(TRIGGERS)
        cls.effects = effects()

    def test_the_record_writes_each_field_both_ways(self):
        body = norm(block(self.snapshot, "te_tax_record_fiscal_month"))
        self.assertTrue(body.startswith("if = { limit = { te_tax_code_on = yes has_variable = te_tax_schema }"))
        for name, test in self.RECORD.items():
            with self.subTest(name=name):
                self.assertIn(f"if = {{ limit = {{ {test} }} set_variable = {{ name = {name} value = 1 }} }} "
                              f"else = {{ set_variable = {{ name = {name} value = 0 }} }}", body)

    def test_only_the_processor_records_it_once_before_any_transition(self):
        callers = sorted(name for name, body in self.effects.items() if "te_tax_record_fiscal_month = yes" in body)
        self.assertEqual(callers, ["te_tax_process_month"])
        body = self.effects["te_tax_process_month"]
        self.assertEqual(body.count("te_tax_record_fiscal_month = yes"), 1)
        at = body.find("te_tax_record_fiscal_month = yes")
        self.assertGreater(at, body.find("set_variable = { name = te_tax_last_month value = var:te_tax_now }"))
        for later in ("te_tax_gen_sunset_wage = yes", "te_tax_gen_commence_", "te_tax_obl_check_month = yes",
                      "te_tax_refresh_support = yes"):
            with self.subTest(later=later):
                self.assertLess(at, body.find(later))
        # Never from a panel.
        for path in (*(ROOT / "gui").rglob("*.gui"), *(ROOT / "common" / "scripted_guis").glob("*.txt")):
            with self.subTest(path=path.name):
                self.assertNotIn("te_tax_record_fiscal_month", path.read_text(encoding="utf-8-sig"))

    def test_readers_use_the_record_never_the_live_budget(self):
        self.assertEqual(norm(block(self.triggers, "te_tax_fisc_rec_deficit")),
                         "has_variable = te_tax_fisc_deficit var:te_tax_fisc_deficit = 1")
        # No record yet: no deficit, and a budget promise counts as maintenance.
        self.assertEqual(norm(block(self.triggers, "te_tax_fisc_rec_surplus")),
                         "OR = { NOT = { has_variable = te_tax_fisc_surplus } var:te_tax_fisc_surplus = 1 }")
        self.assertEqual(norm(block(self.triggers, "te_tax_fisc_rec_bur_ok")),
                         "OR = { NOT = { has_variable = te_tax_fisc_bur_ok } var:te_tax_fisc_bur_ok = 1 }")
        support = read("common/script_values/te_tax_support_values.txt")
        readers = {"te_tax_fiscal_reason": block(support, "te_tax_fiscal_reason"),
                   "te_tax_obl_is_maintenance_2": block(self.triggers, "te_tax_obl_is_maintenance_2"),
                   "te_tax_obl_is_maintenance_4": block(self.triggers, "te_tax_obl_is_maintenance_4"),
                   "te_tax_obl_record_baseline": block(read(OBL_EFFECTS), "te_tax_obl_record_baseline"),
                   "te_tax_obl_write": block(read(OBL_EFFECTS), "te_tax_obl_write")}
        for name, body in readers.items():
            with self.subTest(name=name):
                self.assertNotIn("net_fixed_income", body)
                self.assertNotRegex(body, r"\bbureaucracy [<>=]")
        baseline = norm(readers["te_tax_obl_record_baseline"])
        self.assertIn("var:te_tax_o$N$_kind = 2 te_tax_fisc_rec_bur_ok = yes", baseline)
        self.assertIn("var:te_tax_o$N$_kind = 4 te_tax_fisc_rec_surplus = yes", baseline)

    def test_the_record_is_a_cache_not_schema_tokens(self):
        country, _ = schema_tokens()
        for name in self.RECORD:
            with self.subTest(name=name):
                self.assertNotIn(name, country)
                self.assertNotRegex("\n".join(all_tax_text().values()), rf"remove_variable = (\{{ name = )?{name}\b")


class CivilWarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defined = effects()
        cls.civil = read(CIVIL_WAR)
        cls.generated = read(GEN_EFFECTS)

    def test_the_tokens_are_schema_tokens(self):
        country, _ = schema_tokens()
        for n in SLOTS:
            self.assertEqual(country[f"te_tax_o{n}_on"], 0)
            self.assertEqual(country[f"te_tax_o{n}_state"], 0)
            self.assertIsNone(country[f"te_tax_o{n}_kind"])
        for ig in IGS:
            self.assertEqual(country[f"te_tax_trust_{ig}"], 0)
            self.assertEqual(country[f"te_tax_trust_{ig}_month"], -1)
        for field in ("fails", "maint_only"):
            self.assertIsNone(country[f"te_tax_o1_{field}"])

    def test_the_outbreak_copies_binding_promises_never_pending_ones(self):
        copy = block(self.civil, "te_tax_copy_code")
        self.assertLess(copy.index("te_tax_init_country = yes"), copy.index("te_tax_obl_release_pending = yes"))
        self.assertIn("te_tax_gen_copy_obligations = yes", copy)
        body = block(self.generated, "te_tax_gen_copy_obligations")
        write = block(read(OBL_EFFECTS), "te_tax_obl_write")
        payload = set(re.findall(r"name = te_tax_o\$N\$_(\w+) value", write)) - set(HEADER)
        payload |= {"baseline"}    # te_tax_obl_record_baseline writes it
        for n in SLOTS:
            gate = (f"scope:te_tax_source = {{ te_tax_obl_binding = {{ N = {n} }} }}")
            match = re.search(r"if = \{\s*limit = \{ " + re.escape(gate) + r" \}", body)
            with self.subTest(slot=n):
                self.assertIsNotNone(match)
                inner = body[match.end():close(body, body.index("{", match.start()))]
                copied = set(re.findall(rf"te_tax_copy_token = \{{ NAME = te_tax_o{n}_(\w+) \}}", inner))
                self.assertEqual(copied, payload)

    def test_the_win_repair_reassesses_and_never_fulfils(self):
        repair = block(self.civil, "te_tax_repair_after_civil_war")
        self.assertIn("te_tax_repair_obligations_after_civil_war = yes", repair)
        self.assertLess(repair.index("te_tax_bill_close = yes"),
                        repair.index("te_tax_repair_obligations_after_civil_war = yes"))
        reach = closure({"te_tax_repair_obligations_after_civil_war"}, self.defined)
        for name in reach:
            body = self.defined[name]
            with self.subTest(name=name):
                self.assertNotRegex(body, rf"_state value = ({FULFILLED}|{BREACHED}|{RENEGOTIATED}|{DELIVERING}) ")
                self.assertNotIn("ig_approval_effect", body)
                self.assertNotIn("te_tax_gen_obl_approval", body)
                self.assertNotIn("te_tax_gen_obl_trust", body)
        one = norm(block(read(OBL_EFFECTS), "te_tax_obl_reassess_one"))
        self.assertIn(f"var:te_tax_o$N$_state = {PENDING}", one)
        self.assertIn("te_tax_gen_obl_slot_gone = { N = $N$ }", one)
        self.assertIn("NOT = { te_tax_gen_obl_ig_exists = { N = $N$ } }", one)

    def test_a_released_country_starts_with_no_promises_and_no_trust(self):
        self.assertIn("te_tax_gen_clear_obligations = yes", block(self.civil, "te_tax_init_released_country"))
        body = norm(block(self.generated, "te_tax_gen_clear_obligations"))
        for n in SLOTS:
            self.assertIn(f"set_variable = {{ name = te_tax_o{n}_on value = 0 }}", body)
            self.assertIn(f"set_variable = {{ name = te_tax_o{n}_state value = 0 }}", body)
        for ig in IGS:
            self.assertIn(f"set_variable = {{ name = te_tax_trust_{ig} value = 0 }}", body)


class DisplayTest(unittest.TestCase):
    def test_slot_views_read_the_payload_only_while_the_slot_is_on(self):
        text = read(GEN_VALUES)
        for n in SLOTS:
            for name in top_level_names(text):
                if not name.startswith(f"te_tax_view_o{n}_") or name == f"te_tax_view_o{n}_on":
                    continue
                with self.subTest(name=name):
                    self.assertIn(f"var:te_tax_o{n}_on = 1", block(text, name))
        for field in ("state", "kind", "arg", "target", "ig", "deadline_y", "deadline_mo", "maint_end_y",
                      "maint_end_mo", "streak", "fails", "maint_only", "grace"):
            self.assertIn(f"te_tax_view_o1_{field}", top_level_names(text))

    def test_the_panels_show_a_row_per_slot_with_renegotiate(self):
        politics = read(POLITICS, strip_comments=False)
        self.assertIn("type te_tax_obligations_section = flowcontainer", politics)
        self.assertIn("te_tax_obligations_section = {}", read(LAYOUT, strip_comments=False))
        for n in SLOTS:
            with self.subTest(slot=n):
                self.assertIn(f"GetPlayer.GetCustom('te_tax_obl_state_{n}')", politics)
                self.assertIn(f"[GetPlayer.GetCustom('te_tax_obl_mode_{n}')] [GetPlayer.GetCustom('te_tax_obl_what_{n}')]",
                              politics)
                # Renegotiate only once the promise is in force (state 2 or 3).
                self.assertIn(f"visible = \"[Or( EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue("
                              f"'te_tax_view_o{n}_state'), '(CFixedPoint)2' ), EqualTo_CFixedPoint( "
                              f"GetPlayer.MakeScope.ScriptValue('te_tax_view_o{n}_state'), '(CFixedPoint)3' ) )]\"",
                              politics)
                self.assertIn(f"GetPlayer.GetCustom('te_tax_obl_ig_{n}')", politics)
                self.assertIn(f"GetScriptedGui('te_tax_cmd_obl_renegotiate_sgui').Execute( GuiScope.SetRoot( "
                              f"GetPlayer.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint){n}' ) ).End )",
                              politics)
        overview = read(OVERVIEW, strip_comments=False)
        self.assertIn("te_tax_show_obligations_sgui", overview)
        self.assertIn('"te_tax_ov_obligations_value"', overview)

    def test_the_custom_loc_covers_every_state_and_kind(self):
        custom = read(GEN_CUSTOM_LOC)
        table = loc()
        import json
        vanilla = json.loads((ROOT / "vanilla_parsed/localization_english.json").read_text(encoding="utf-8"))
        for n in SLOTS:
            for name in (f"te_tax_obl_ig_{n}", f"te_tax_obl_what_{n}", f"te_tax_obl_inst_{n}",
                         f"te_tax_obl_state_{n}", f"te_tax_obl_mode_{n}"):
                body = block(custom, name)
                with self.subTest(name=name):
                    self.assertNotRegex(body, r"var:|has_variable")
                    for key in re.findall(r"localization_key = (\w+)", body):
                        self.assertTrue(key in table or key in vanilla, key)
            state = block(custom, f"te_tax_obl_state_{n}")
            for value in (PENDING, BOUND, DELIVERING, MAINTAINING):
                self.assertIn(f"te_tax_view_o{n}_state = {value}", state)
            self.assertLess(state.find(f"te_tax_view_o{n}_fails > 0"), state.find(f"te_tax_obl_st_maint_{n}"))
            self.assertIn(f"localization_key = te_tax_obl_st_failing_{n}", state)
            mode = norm(block(custom, f"te_tax_obl_mode_{n}"))
            self.assertIn(f"trigger = {{ te_tax_view_o{n}_maint_only = 1 }} localization_key = te_tax_obl_mode_maintain", mode)
            self.assertIn("localization_key = te_tax_obl_mode_reach", mode)
            for n_ig, ig in enumerate(IGS, start=1):
                self.assertIn(f"te_tax_view_o{n}_ig = {n_ig} }}\n\t\tlocalization_key = ig_{ig}",
                              block(read(GEN_CUSTOM_LOC, strip_comments=False), f"te_tax_obl_ig_{n}"))

    def test_history_lines_for_the_obligation_kinds(self):
        table = loc()
        for key in ("te_tax_hist_kind_obl_fulfilled", "te_tax_hist_kind_obl_breached",
                    "te_tax_hist_kind_obl_renegotiated", "te_tax_hist_kind_obl_released"):
            self.assertTrue(table.get(key), key)
        self.assertEqual(gen.HISTORY_KIND_KEYS[KIND_FULFILLED], "te_tax_hist_kind_obl_fulfilled")
        self.assertEqual(gen.HISTORY_KIND_KEYS[KIND_RELEASED], "te_tax_hist_kind_obl_released")


class DocTest(unittest.TestCase):
    def test_schema_doc_has_the_obligations_section(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        self.assertIn("\n## Policy obligations\n", doc)
        section = doc.split("\n## Policy obligations\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_obl_propose", "te_tax_obl_start", "te_tax_obl_feasible_1", "te_tax_obl_bind",
                       "te_tax_obl_release_slot", "te_tax_obl_check_month", "te_tax_cmd_obl_renegotiate",
                       "te_tax_repair_obligations_after_civil_war", "institution:", "P16",
                       "te_tax_obl_kept_modifier", "te_tax_obl_broken_modifier",
                       "te_tax_obl_renegotiated_modifier", "te_tax_trust_", "te_tax_obl_grace_",
                       "_maint_only", "te_tax_obl_is_maintenance", "te_tax_gen_trust_recover", "obl_paused"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_relief_holder_row_says_only_the_rebuild_stamps(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        row = [line for line in doc.splitlines() if line.startswith("| state var `te_tax_relief_holder`")]
        self.assertEqual(len(row), 1)
        self.assertNotIn("package", row[0])
        self.assertIn("te_tax_rebuild_relief_marks", row[0])

    def test_ledger_marks_institution_verification_pending_p16(self):
        ledger = read(LEDGER, strip_comments=False)
        rows = [line for line in ledger.splitlines() if "te_tax_obl_inst_met_" in line]
        self.assertEqual(len(rows), 1)
        self.assertIn("pending P16", rows[0])


if __name__ == "__main__":
    unittest.main()
