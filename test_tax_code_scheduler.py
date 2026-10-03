"""The legislated tax code's scheduler: approved-package slots, sunsets and history.

Structural checks on the committed script (no game install needed). The probe
this replaces commenced and expired a package in one call, because the
country pulse it hung off is a 30-day timer that skipped February
(docs/guides/scripting_best_practices.md, "`on_monthly_pulse_country` Is a
30-Day Timer, Not a Calendar Month"). These tests pin the rules that make
that impossible:

* transitions dispatch from the global `on_monthly_pulse` (the 1st), gated on
  the rule, through a country event; the country pulse is only a watchdog
  that never commences and never claims the month;
* the processor claims the month (`te_tax_last_month`) before any transition;
* a sunset runs only when the provision has been operative since an earlier
  month (`_since < now`), and a commencement only in its own month
  (`_due = now`, never `>=`); a late commencement holds as missed;
* a package can be stored only when every sunset falls at least one month
  after commencement, and the store computes the sunset as due + offset;
* nothing removes a schema token, and every processor branch logs.

Run: python3 -m unittest test_tax_code_scheduler -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_rule import load
from test_tax_code_state import KEYS, block, catalog, close, gen, read, schema_tokens

ROOT = Path(__file__).resolve().parent

ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
EVENTS = "events/te_tax_internal_events.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
PROBE_RUNBOOK = "docs/testing/tax-code-probes.md"

SLOTS = ("a", "b")
HAND_WRITTEN = (ON_ACTIONS, EVENTS, SCHEDULE)
SCHEDULER_FILES = HAND_WRITTEN + (TRIGGERS, GEN_EFFECTS, GEN_TRIGGERS)

# History kinds (brief): the scheduler itself writes the first four.
KIND_COMMENCED, KIND_SUNSET, KIND_HELD_CONFLICT, KIND_HELD_MISSED = 1, 2, 3, 4

# The month and date every debug line carries (research A §3.9). In a country
# event ROOT = THIS = the country; the probe printed month=22032 through this
# exact accessor, and 1.14.5's own election lines print the date through
# TimeKeeper ("January 8, 2069").
MONTH = "month=[SCOPE.ScriptValue('te_history_month_index')|0]"
DATE = "date=[TimeKeeper.GetCurrentDate.GetString]"

BRANCH_OPENER = re.compile(r"\b(if|else_if|else) = \{")


def effects():
    """{name: body} for every scripted effect the tax code defines (not the probe)."""
    defined = {}
    for path in sorted((ROOT / "common/scripted_effects").glob("te_tax_*.txt")):
        text = read(path.relative_to(ROOT).as_posix())
        for match in re.finditer(r"(?m)^(\w+) = \{", text):
            defined[match.group(1)] = text[match.end():close(text, match.end() - 1)]
    return defined


def calls(body, defined):
    """The scripted effects `body` calls, with `$SLOT$` names expanded to both slots."""
    found = set()
    for name in re.findall(r"\b(te_tax_[\w$]+) = (?:yes|\{)", body):
        for expanded in ({name.replace("$SLOT$", slot) for slot in SLOTS} if "$SLOT$" in name else {name}):
            if expanded in defined:
                found.add(expanded)
    return found


def closure(roots, defined):
    """Every effect reachable from `roots`, the roots included."""
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(calls(defined[name], defined) - seen)
    return seen


def branches(text):
    """[(kind, body)] for every if / else_if / else block anywhere in `text`."""
    found = []
    for match in BRANCH_OPENER.finditer(text):
        found.append((match.group(1), text[match.end():close(text, match.end() - 1)]))
    return found


def limit_of(body):
    match = re.match(r"\s*limit = \{", body)
    if match is None:
        return ""
    return body[match.end():close(body, match.end() - 1)]


def direct(body):
    """`body` without the if / else_if / else blocks nested in it."""
    out, i = [], 0
    while True:
        match = BRANCH_OPENER.search(body, i)
        if match is None:
            out.append(body[i:])
            return "".join(out)
        out.append(body[i:match.start()])
        i = close(body, match.end() - 1) + 1


def logs(body):
    """The debug_log lines `body` writes directly or through a nested human-player gate."""
    lines = re.findall(r'debug_log = "([^"]*)"', direct(body))
    for kind, nested in branches(body):
        if kind == "if" and limit_of(nested).strip() == "is_ai = no":
            lines += re.findall(r'debug_log = "([^"]*)"', direct(nested))
    return lines


class DispatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(ON_ACTIONS)

    def test_processor_hangs_off_the_global_pulse_not_the_country_pulse(self):
        self.assertEqual(self.parsed["on_monthly_pulse"]["on_actions"], ["te_tax_monthly_dispatch"])
        self.assertNotIn("te_tax_monthly_dispatch", self.parsed["on_monthly_pulse_country"]["on_actions"])

    def test_dispatch_is_gated_on_the_rule_and_reaches_migrated_countries(self):
        effect = self.parsed["te_tax_monthly_dispatch"]["effect"]
        self.assertEqual(set(effect), {"if"})
        gate = effect["if"]
        self.assertEqual(gate["limit"], {"te_tax_code_on": "yes"})
        # Two fan-outs: the processor for migrated countries, then the migration
        # self-heal (te_tax.3, Task 5; test_tax_code_migration.py) for the rest.
        fan_out, self_heal = gate["every_country"]
        self.assertEqual(fan_out["limit"], {"has_variable": "te_tax_migrated", "var:te_tax_migrated": "0"})
        self.assertEqual(fan_out["trigger_event"], {"id": "te_tax.1"})
        self.assertEqual(self_heal["trigger_event"], {"id": "te_tax.3"})
        text = read(ON_ACTIONS)
        self.assertRegex(text, r"var:te_tax_migrated > 0")

    def test_dispatch_logs_the_date(self):
        body = block(read(ON_ACTIONS), "te_tax_monthly_dispatch")
        self.assertIn(f'debug_log = "TE_TAX dispatch {DATE}"', body)

    def test_watchdog_hangs_off_the_country_pulse_and_is_gated(self):
        self.assertEqual(self.parsed["on_monthly_pulse_country"]["on_actions"], ["te_tax_watchdog_on_action"])
        gate = self.parsed["te_tax_watchdog_on_action"]["effect"]["if"]
        self.assertEqual(gate["trigger_event"], {"id": "te_tax.2"})
        limit = block(read(ON_ACTIONS), "te_tax_watchdog_on_action")
        for condition in ("te_tax_code_on = yes", "var:te_tax_migrated > 0",
                          "var:te_tax_last_month < te_history_month_index",
                          "var:te_tax_next_month >= 0",
                          "var:te_tax_next_month <= te_history_month_index"):
            with self.subTest(condition=condition):
                self.assertIn(condition, limit)

    def test_only_the_dispatch_and_the_watchdog_raise_the_scheduler_events(self):
        raisers = []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = read(path.relative_to(ROOT).as_posix())
                # Both forms: `trigger_event = { id = X }` and the bare `trigger_event = X`.
                for event in re.findall(r"trigger_event = (?:\{ id = )?(te_tax\.[12])\b", text):
                    raisers.append((path.relative_to(ROOT).as_posix(), event))
        self.assertEqual(sorted(raisers), [(ON_ACTIONS, "te_tax.1"), (ON_ACTIONS, "te_tax.2")])


class EventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(EVENTS)

    def test_namespace_and_two_hidden_rule_gated_country_events(self):
        self.assertEqual(self.parsed["namespace"], "te_tax")
        for event, effect in (("te_tax.1", "te_tax_process_month"), ("te_tax.2", "te_tax_watchdog_month")):
            with self.subTest(event=event):
                body = self.parsed[event]
                self.assertEqual(body["type"], "country_event")
                self.assertEqual(body["hidden"], "yes")
                self.assertEqual(body["trigger"], {"te_tax_code_on": "yes"})
                self.assertEqual(body["immediate"], {effect: "yes"})

    def test_no_ck3_only_keyword(self):
        # Vanilla 1.14.5 never uses is_triggered_only; the mod's hidden events omit it.
        self.assertNotIn("is_triggered_only", read(EVENTS))


class ProcessorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(SCHEDULE)
        cls.body = block(cls.text, "te_tax_process_month")

    def test_processor_is_gated_on_the_rule_and_an_initialised_country(self):
        gate = limit_of(self.body[self.body.find("if = {") + len("if = {"):])
        self.assertIn("te_tax_code_on = yes", gate)
        self.assertIn("has_variable = te_tax_schema", gate)

    def test_now_is_read_once_before_the_guard(self):
        reads = re.findall(r"set_variable = \{ name = te_tax_now value = te_history_month_index \}", self.body)
        self.assertEqual(len(reads), 1)
        self.assertLess(self.body.find("name = te_tax_now"), self.body.find("var:te_tax_last_month"))
        code = re.sub(r'debug_log = "[^"]*"', "", self.body)
        self.assertEqual(code.count("te_history_month_index"), 1, "compare only against te_tax_now")

    def test_guard_skips_a_month_already_processed(self):
        skip = re.search(r"if = \{\s*limit = \{ var:te_tax_last_month >= var:te_tax_now \}", self.body)
        self.assertIsNotNone(skip)
        opener = skip.start() + len("if = {") - 1
        skip_body = self.body[opener + 1:close(self.body, opener)]
        for effect in ("te_tax_gen_sunset_", "te_tax_gen_commence_", "te_tax_sync_collection", "set_variable"):
            self.assertNotIn(effect, direct(skip_body))
        self.assertTrue(any(line.startswith("TE_TAX skip") for line in logs(skip_body)))

    def test_month_is_claimed_before_any_transition(self):
        claim = self.body.find("set_variable = { name = te_tax_last_month value = var:te_tax_now }")
        self.assertGreater(claim, 0)
        self.assertEqual(self.body.count("name = te_tax_last_month"), 1)
        for transition in ("te_tax_gen_sunset_", "te_tax_gen_commence_", "te_tax_sync_collection",
                           "te_tax_recompute_next_month"):
            with self.subTest(transition=transition):
                self.assertGreater(self.body.find(transition), claim)

    def test_sunsets_then_commencements_in_seq_order_then_one_sync_then_next_month(self):
        order = [self.body.find(f"te_tax_gen_sunset_{key} = yes") for key in KEYS]
        self.assertTrue(all(position > 0 for position in order))
        first_commence = self.body.find("te_tax_gen_commence_")
        self.assertGreater(first_commence, max(order))
        seq = re.search(r"if = \{\s*limit = \{ var:te_tax_pb_seq < var:te_tax_pa_seq \}\s*"
                        r"te_tax_gen_commence_b = yes\s*te_tax_gen_commence_a = yes\s*\}\s*"
                        r"else = \{\s*te_tax_gen_commence_a = yes\s*te_tax_gen_commence_b = yes\s*\}",
                        self.body)
        self.assertIsNotNone(seq, "lower seq commences first; a on a tie")
        self.assertEqual(self.body.count("te_tax_sync_collection = yes"), 1)
        self.assertGreater(self.body.find("te_tax_sync_collection = yes"), seq.end())
        self.assertGreater(self.body.find("te_tax_recompute_next_month = yes"),
                           self.body.find("te_tax_sync_collection = yes"))

    def test_processor_backfills_tokens_first(self):
        self.assertLess(self.body.find("te_tax_init_country = yes"), self.body.find("name = te_tax_now"))


class SunsetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(GEN_EFFECTS)

    def sunset(self, key):
        return block(self.text, f"te_tax_gen_sunset_{key}")

    def test_a_sunset_runs_only_after_its_operative_month(self):
        for key in KEYS:
            body = self.sunset(key)
            executes = [nested for kind, nested in branches(body)
                        if f"name = te_tax_en_{key} value = var:te_tax_en_{key}_succ" in direct(nested)]
            with self.subTest(key=key):
                self.assertEqual(len(executes), 1)
                self.assertIn(f"var:te_tax_en_{key}_since < var:te_tax_now", limit_of(executes[0]))
                self.assertNotRegex(body, rf"var:te_tax_en_{key}_since (<=|>=|>|=) ")

    def test_a_due_sunset_is_one_whose_month_has_come(self):
        for key in KEYS:
            outer = limit_of(self.sunset(key)[self.sunset(key).find("if = {") + len("if = {"):])
            with self.subTest(key=key):
                self.assertIn(f"var:te_tax_en_{key}_exp >= 0", outer)
                self.assertIn(f"var:te_tax_en_{key}_exp <= var:te_tax_now", outer)

    def test_a_sunset_writes_the_successor_and_clears_itself(self):
        for idx, key in enumerate(KEYS, start=1):
            body = self.sunset(key)
            executes = [nested for _, nested in branches(body)
                        if "var:te_tax_en_%s_since < var:te_tax_now" % key in limit_of(nested)][0]
            with self.subTest(key=key):
                self.assertRegex(executes, rf"set_variable = \{{ name = te_tax_en_{key} value = var:te_tax_en_{key}_succ \}}"
                                           rf"\s*set_variable = \{{ name = te_tax_en_{key}_since value = var:te_tax_now \}}"
                                           rf"\s*set_variable = \{{ name = te_tax_en_{key}_exp value = -1 \}}"
                                           rf"\s*set_variable = \{{ name = te_tax_en_{key}_succ value = -1 \}}")
                self.assertIn("change_variable = { name = te_tax_code_version add = 1 }", executes)
                self.assertIn(f"te_tax_gen_history_write = {{ KIND = {KIND_SUNSET} SLOT = none INST = {idx} }}",
                              executes)

    def test_a_sunset_without_a_successor_is_dropped_not_deferred(self):
        # Deferring it would leave te_tax_next_month <= now forever.
        for key in KEYS:
            dropped = [nested for _, nested in branches(self.sunset(key))
                       if limit_of(nested).strip() == f"var:te_tax_en_{key}_succ < 0"]
            with self.subTest(key=key):
                self.assertEqual(len(dropped), 1)
                self.assertIn(f"set_variable = {{ name = te_tax_en_{key}_exp value = -1 }}", dropped[0])
                self.assertNotIn("te_tax_code_version", dropped[0])

    def test_a_deferred_sunset_changes_nothing_and_logs(self):
        for key in KEYS:
            deferred = [nested for kind, nested in branches(self.sunset(key)) if kind == "else"]
            with self.subTest(key=key):
                self.assertEqual(len(deferred), 1)
                self.assertNotIn("set_variable", deferred[0])
                self.assertTrue(any(line.startswith("TE_TAX sunset_deferred") for line in logs(deferred[0])))


class CommencementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(GEN_EFFECTS)

    def test_commencement_only_in_the_due_month(self):
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_commence_{slot}")
            gate = limit_of(body[body.find("if = {") + len("if = {"):])
            with self.subTest(slot=slot):
                self.assertIn(f"var:te_tax_p{slot}_due = var:te_tax_now", gate)
                self.assertIn(f"var:te_tax_p{slot}_on = 1", gate)
                self.assertIn(f"var:te_tax_p{slot}_state = 1", gate)
                self.assertNotRegex(body, rf"var:te_tax_p{slot}_due (>=|<=|>) ")

    def test_apply_runs_only_inside_the_due_month_branch_when_current(self):
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_commence_{slot}")
            applies = [nested for kind, nested in branches(body) if f"te_tax_gen_apply_{slot} = yes" in direct(nested)]
            with self.subTest(slot=slot):
                self.assertEqual(body.count("te_tax_gen_apply_"), 1)
                self.assertEqual(len(applies), 1)
                self.assertEqual(limit_of(applies[0]).strip(), f"te_tax_gen_package_current_{slot} = yes")
                self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_on value = 0 }}", applies[0])
                self.assertIn("change_variable = { name = te_tax_code_version add = 1 }", applies[0])
                self.assertIn(f"te_tax_gen_history_write = {{ KIND = {KIND_COMMENCED} SLOT = {slot} INST = 0 }}",
                              applies[0])

    def test_a_conflict_holds_the_whole_package(self):
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_commence_{slot}")
            held = [nested for kind, nested in branches(body)
                    if f"name = te_tax_p{slot}_state value = 2" in direct(nested)]
            with self.subTest(slot=slot):
                self.assertEqual(len(held), 1)
                self.assertNotIn("te_tax_en_", held[0])
                self.assertNotIn("te_tax_code_version", held[0])
                self.assertIn(f"te_tax_gen_history_write = {{ KIND = {KIND_HELD_CONFLICT} SLOT = {slot} INST = 0 }}",
                              held[0])

    def test_a_missed_commencement_holds(self):
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_hold_missed_{slot}")
            gate = limit_of(body[body.find("if = {") + len("if = {"):])
            with self.subTest(slot=slot):
                self.assertIn(f"var:te_tax_p{slot}_due < var:te_tax_now", gate)
                self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_state value = 3 }}", body)
                self.assertNotIn("te_tax_en_", body)
                self.assertIn(f"te_tax_gen_history_write = {{ KIND = {KIND_HELD_MISSED} SLOT = {slot} INST = 0 }}",
                              body)
                self.assertIn(f"te_tax_gen_hold_missed_{slot} = yes", block(self.text, f"te_tax_gen_commence_{slot}"))

    def test_current_means_every_touched_provision_kept_its_external_version(self):
        triggers = read(GEN_TRIGGERS)
        for slot in SLOTS:
            body = block(triggers, f"te_tax_gen_package_current_{slot}")
            with self.subTest(slot=slot):
                for key in KEYS:
                    self.assertRegex(body, rf"OR = \{{\s*var:te_tax_p{slot}_{key} < 0\s*"
                                           rf"var:te_tax_p{slot}_xver_{key} = var:te_tax_xver_{key}\s*\}}")
                self.assertRegex(body, rf"OR = \{{\s*NOT = \{{ te_tax_gen_package_touches_goods_{slot} = yes \}}\s*"
                                       rf"var:te_tax_p{slot}_xver_goods = var:te_tax_xver_goods\s*\}}")
                self.assertIn(f"var:te_tax_p{slot}_xver_relief = var:te_tax_xver_relief", body)
                self.assertNotIn("has_law", body, "held_conflict is an external-version mismatch only")
            touches = block(triggers, f"te_tax_gen_package_touches_goods_{slot}")
            self.assertEqual(sorted(re.findall(rf"var:te_tax_p{slot}_g_(\w+) >= 0", touches)), sorted(catalog()))

    def test_apply_copies_every_touched_field(self):
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_apply_{slot}")
            with self.subTest(slot=slot):
                for key in KEYS:
                    self.assertRegex(
                        body,
                        rf"if = \{{\s*limit = \{{ var:te_tax_p{slot}_{key} >= 0 \}}\s*"
                        rf"if = \{{\s*limit = \{{ var:te_tax_p{slot}_{key}_exp >= 0 \}}\s*"
                        rf"if = \{{\s*limit = \{{\s*OR = \{{\s*var:te_tax_en_{key}_exp < 0\s*"
                        rf"var:te_tax_en_{key}_succ < 0\s*\}}\s*\}}\s*"
                        rf"set_variable = \{{ name = te_tax_en_{key}_succ value = var:te_tax_en_{key} \}}\s*\}}\s*\}}\s*"
                        rf"else = \{{\s*set_variable = \{{ name = te_tax_en_{key}_succ value = -1 \}}\s*\}}\s*"
                        rf"set_variable = \{{ name = te_tax_en_{key} value = var:te_tax_p{slot}_{key} \}}\s*"
                        rf"set_variable = \{{ name = te_tax_en_{key}_since value = var:te_tax_now \}}\s*"
                        rf"set_variable = \{{ name = te_tax_en_{key}_exp value = var:te_tax_p{slot}_{key}_exp \}}\s*\}}")
                for good in catalog():
                    self.assertIn(f"if = {{ limit = {{ var:te_tax_p{slot}_g_{good} >= 0 }} "
                                  f"set_variable = {{ name = te_tax_en_g_{good} value = var:te_tax_p{slot}_g_{good} }} }}",
                                  body)
                self.assertIn(f"name = te_tax_en_agrel value = var:te_tax_p{slot}_agrel", body)
                self.assertIn(f"name = te_tax_en_regrel value = var:te_tax_p{slot}_regrel", body)
                self.assertIn(f"var:te_tax_p{slot}_regrel_states_set = 1", body)
                # The slot's own list replaces the enacted one, filtered by the keep
                # rule, and is consumed (Task 11 fix round 1).
                self.assertIn(f"variable = te_tax_p{slot}_relief_states", body)
                self.assertIn("limit = { te_tax_relief_listed_state_kept = yes }", body)
                self.assertIn(f"clear_variable_list = te_tax_p{slot}_relief_states", body)
                self.assertNotIn("te_tax_sync_collection", body, "the processor syncs once, after every slot")

    def test_supersession_and_successor_happen_at_commencement(self):
        # Controller ruling (Task 4 fix round 2). The package replaces the enacted value and
        # its sunset when it commences, never at approval. No sunset in the package: the
        # change is permanent and clears any pending sunset. A sunset in the package: the
        # provision reverts to the underlying permanent rate, i.e. a still-pending sunset's
        # successor (this month's sunsets have run) or else the rate in force, captured
        # before the overwrite. The package's stored _succ is a review preview, never read.
        for slot in SLOTS:
            body = block(self.text, f"te_tax_gen_apply_{slot}")
            for key in KEYS:
                with self.subTest(slot=slot, key=key):
                    touched = [nested for kind, nested in branches(body)
                               if kind == "if" and limit_of(nested).strip() == f"var:te_tax_p{slot}_{key} >= 0"]
                    self.assertEqual(len(touched), 1)
                    provision = touched[0]
                    # Sunset or not, the package's own _exp replaces the enacted one,
                    # unconditionally: -1 when the package has none.
                    self.assertIn(f"set_variable = {{ name = te_tax_en_{key}_exp value = var:te_tax_p{slot}_{key}_exp }}",
                                  direct(provision))
                    # No sunset in the package: _succ cleared too.
                    cleared = [nested for kind, nested in branches(provision)
                               if kind == "else" and f"name = te_tax_en_{key}_succ value = -1" in direct(nested)]
                    self.assertEqual(len(cleared), 1)
                    # With a package sunset: the rate in force only when no pending sunset
                    # with a successor exists; otherwise the pending successor stays.
                    with_sunset = [nested for kind, nested in branches(provision)
                                   if limit_of(nested).strip() == f"var:te_tax_p{slot}_{key}_exp >= 0"]
                    self.assertEqual(len(with_sunset), 1)
                    self.assertNotIn(f"name = te_tax_en_{key}_succ", direct(with_sunset[0]),
                                     "a pending successor is kept, not rewritten")
                    fallback = [nested for _, nested in branches(with_sunset[0])
                                if f"name = te_tax_en_{key}_succ value = var:te_tax_en_{key} " in direct(nested)]
                    self.assertEqual(len(fallback), 1)
                    self.assertRegex(limit_of(fallback[0]), rf"^\s*OR = \{{\s*var:te_tax_en_{key}_exp < 0\s*"
                                                            rf"var:te_tax_en_{key}_succ < 0\s*\}}\s*$")
                    self.assertEqual(provision.count(f"name = te_tax_en_{key}_succ"), 2)
                    # Captured before anything is overwritten.
                    first_overwrite = min(provision.find(f"name = te_tax_en_{key} value"),
                                          provision.find(f"name = te_tax_en_{key}_exp value"))
                    self.assertLess(provision.rfind(f"name = te_tax_en_{key}_succ"), first_overwrite)
                    self.assertNotIn(f"te_tax_p{slot}_{key}_succ", body)
            self.assertNotRegex(body, r"te_tax_p[ab]_\w+_succ")

    def test_commencement_runs_after_the_months_sunsets(self):
        # The captured successor is the post-sunset value.
        body = block(read(SCHEDULE), "te_tax_process_month")
        last_sunset = max(body.find(f"te_tax_gen_sunset_{key} = yes") for key in KEYS)
        self.assertGreater(body.find("te_tax_gen_commence_"), last_sunset)

    def test_no_public_apply_entry_point(self):
        # te_tax_gen_apply_<slot> reads te_tax_now, which only the processor sets.
        self.assertNotIn("te_tax_apply_package", effects())
        callers = [name for name, body in effects().items()
                   if re.search(r"te_tax_gen_apply_(a|b|\$SLOT\$) = yes", body)]
        self.assertEqual(sorted(callers), ["te_tax_gen_commence_a", "te_tax_gen_commence_b"])


class WatchdogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.defined = effects()
        cls.reach = closure({"te_tax_watchdog_month"}, cls.defined)

    def test_watchdog_never_commences(self):
        for forbidden in ("te_tax_process_month", "te_tax_store_package",
                          *(f"te_tax_gen_commence_{slot}" for slot in SLOTS),
                          *(f"te_tax_gen_apply_{slot}" for slot in SLOTS)):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.reach)

    def test_watchdog_never_claims_the_month(self):
        # The country pulse can land on the 1st before the global pulse; claiming the
        # month there would make the dispatch skip that month's commencements.
        for name in self.reach:
            with self.subTest(name=name):
                self.assertNotRegex(self.defined[name], r"name = te_tax_last_month value = (?!-1 )")

    def test_watchdog_runs_sunsets_marks_missed_syncs_and_logs(self):
        body = self.defined["te_tax_watchdog_month"]
        for key in KEYS:
            self.assertIn(f"te_tax_gen_sunset_{key} = yes", body)
        for slot in SLOTS:
            self.assertIn(f"te_tax_gen_hold_missed_{slot} = yes", body)
        self.assertEqual(body.count("te_tax_sync_collection = yes"), 1)
        # Sync only if a sunset ran: every executed sunset bumps te_tax_code_version, so on
        # the 1st (country pulse before the global one) the tick is not synced twice.
        record = body.find("set_local_variable = { name = te_tax_wd_version value = var:te_tax_code_version }")
        self.assertGreater(record, 0)
        self.assertLess(record, body.find("te_tax_gen_sunset_wage = yes"))
        synced = [nested for _, nested in branches(body) if "te_tax_sync_collection = yes" in direct(nested)]
        self.assertEqual(len(synced), 1)
        self.assertEqual(limit_of(synced[0]).strip(), "var:te_tax_code_version > local_var:te_tax_wd_version")
        self.assertGreater(body.find("te_tax_sync_collection = yes"), body.find("te_tax_gen_hold_missed_b = yes"))
        acting = [nested for _, nested in branches(body) if "te_tax_gen_sunset_wage = yes" in direct(nested)]
        self.assertEqual(len(acting), 1)
        for condition in ("var:te_tax_last_month < var:te_tax_now", "var:te_tax_next_month >= 0",
                          "var:te_tax_next_month <= var:te_tax_now"):
            self.assertIn(condition, limit_of(acting[0]))
        self.assertTrue(any(line.startswith("TE_TAX watchdog") for line in logs(acting[0])))

    def test_processor_reaches_every_transition(self):
        reach = closure({"te_tax_process_month"}, self.defined)
        for name in ("te_tax_sync_collection", "te_tax_recompute_next_month",
                     *(f"te_tax_gen_sunset_{key}" for key in KEYS),
                     *(f"te_tax_gen_commence_{slot}" for slot in SLOTS),
                     *(f"te_tax_gen_apply_{slot}" for slot in SLOTS),
                     *(f"te_tax_gen_hold_missed_{slot}" for slot in SLOTS)):
            with self.subTest(name=name):
                self.assertIn(name, reach)

    def test_only_the_processor_claims_the_month(self):
        writers = [name for name, body in self.defined.items()
                   if re.search(r"name = te_tax_last_month value = (?!-1 )", body)]
        self.assertEqual(writers, ["te_tax_process_month"])


class StoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schedule = read(SCHEDULE)
        cls.generated = read(GEN_EFFECTS)
        cls.triggers = read(TRIGGERS)
        cls.gen_triggers = read(GEN_TRIGGERS)

    def test_store_is_wrapped_by_its_validation_trigger(self):
        body = block(self.schedule, "te_tax_store_package")
        self.assertRegex(body, r"^\s*if = \{\s*limit = \{ te_tax_can_store_package = \{ SLOT = \$SLOT\$ \} \}")
        self.assertIn("te_tax_gen_store_$SLOT$ = yes", body)
        self.assertIn("save_scope_as = te_tax_country", body)
        self.assertGreater(body.find("te_tax_recompute_next_month = yes"), body.find("te_tax_gen_store_$SLOT$"))
        refused = [nested for kind, nested in branches(body) if kind == "else"]
        self.assertEqual(len(refused), 1)
        self.assertTrue(any(line.startswith("TE_TAX store_refused") for line in logs(refused[0])))

    def test_validation_needs_the_rule_a_free_slot_a_future_due_and_valid_sunsets(self):
        body = block(self.triggers, "te_tax_can_store_package")
        for condition in ("te_tax_code_on = yes", "has_variable = te_tax_schema",
                          "var:te_tax_p$SLOT$_on = 0", "has_variable = te_tax_bl_due",
                          "var:te_tax_bl_due > te_history_month_index",
                          "te_tax_gen_bill_sunsets_valid = yes"):
            with self.subTest(condition=condition):
                self.assertIn(condition, body)

    def test_a_sunset_offset_below_one_month_is_rejected(self):
        # _exp = _due + _sun (store), so _exp >= _due + 1 exactly when _sun >= 1.
        body = block(self.gen_triggers, "te_tax_gen_bill_sunsets_valid")
        for key in KEYS:
            with self.subTest(key=key):
                self.assertRegex(body, rf"OR = \{{\s*var:te_tax_bl_{key} < 0\s*var:te_tax_bl_{key}_sun = 0\s*"
                                       rf"var:te_tax_bl_{key}_sun >= 1\s*\}}")
        self.assertEqual(body.count("OR = {"), len(KEYS))

    def test_store_computes_the_sunset_as_due_plus_offset_only_for_a_valid_offset(self):
        for slot in SLOTS:
            body = block(self.generated, f"te_tax_gen_store_{slot}")
            for key in KEYS:
                sunsets = [nested for kind, nested in branches(body)
                           if f"name = te_tax_p{slot}_{key}_exp value = var:te_tax_bl_due" in direct(nested)]
                with self.subTest(slot=slot, key=key):
                    self.assertEqual(len(sunsets), 1)
                    gate = limit_of(sunsets[0])
                    self.assertIn(f"var:te_tax_bl_{key} >= 0", gate)
                    self.assertIn(f"var:te_tax_bl_{key}_sun >= 1", gate)
                    self.assertIn(f"change_variable = {{ name = te_tax_p{slot}_{key}_exp add = var:te_tax_bl_{key}_sun }}",
                                  sunsets[0])
                    self.assertRegex(body, rf"else = \{{\s*set_variable = \{{ name = te_tax_p{slot}_{key}_exp value = -1 \}}"
                                           rf"\s*set_variable = \{{ name = te_tax_p{slot}_{key}_succ value = -1 \}}\s*\}}")

    def test_store_successor_preview_follows_the_commencement_rule(self):
        # A review preview only ("reverts to X"); commencement never reads it.
        for slot, other in (("a", "b"), ("b", "a")):
            body = block(self.generated, f"te_tax_gen_store_{slot}")
            for key in KEYS:
                with self.subTest(slot=slot, key=key):
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{key}_succ value = var:te_tax_en_{key} }}", body)
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{key}_succ value = var:te_tax_en_{key}_succ }}",
                                  body)
                    # The other slot, only while it awaits an earlier due month; its payload
                    # is read in a nested branch, after its header says it exists.
                    earlier = [nested for _, nested in branches(body)
                               if f"var:te_tax_p{other}_due < var:te_tax_bl_due" in limit_of(nested)
                               and f"var:te_tax_p{other}_{key} >= 0" in nested]
                    self.assertEqual(len(earlier), 1)
                    self.assertIn(f"var:te_tax_p{other}_on = 1", limit_of(earlier[0]))
                    self.assertIn(f"var:te_tax_p{other}_state = 1", limit_of(earlier[0]))
                    self.assertNotIn(f"var:te_tax_p{other}_{key} ", limit_of(earlier[0]))
                    self.assertIn(f"name = te_tax_p{slot}_{key}_succ value = var:te_tax_p{other}_{key} ", earlier[0])
                    self.assertIn(f"name = te_tax_p{slot}_{key}_succ value = var:te_tax_p{other}_{key}_succ ", earlier[0])
            # Apply's rule: a pending sunset keeps its successor whatever its month, so the
            # preview does not compare sunset months with the due month.
            self.assertNotIn("_exp <= var:te_tax_bl_due", body)

    def test_store_copies_every_bill_field_and_activates_the_slot_last(self):
        for slot in SLOTS:
            body = block(self.generated, f"te_tax_gen_store_{slot}")
            with self.subTest(slot=slot):
                self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_due value = var:te_tax_bl_due }}", body)
                for key in KEYS:
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{key} value = var:te_tax_bl_{key} }}", body)
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_xver_{key} value = var:te_tax_bl_xver_{key} }}",
                                  body)
                for good in catalog():
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_g_{good} value = var:te_tax_bl_g_{good} }}", body)
                for field in ("xver_goods", "agrel", "regrel", "xver_relief"):
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{field} value = var:te_tax_bl_{field} }}", body)
                self.assertIn("has_variable_list = te_tax_bl_relief_states", body)
                self.assertIn("variable = te_tax_bl_relief_states", body)
                self.assertIn(f"scope:te_tax_country = {{ add_to_variable_list = {{ name = te_tax_p{slot}_relief_states "
                              "target = PREV } }", body)
                self.assertIn(f'debug_log = "TE_TAX stored slot={slot};', body)
                last = body.rstrip().splitlines()[-1].strip()
                self.assertEqual(last, f"set_variable = {{ name = te_tax_p{slot}_on value = 1 }}")
                self.assertLess(body.find(f"name = te_tax_p{slot}_state value = 1"), body.rfind(f"name = te_tax_p{slot}_on"))

    def test_store_seq_is_above_both_slots(self):
        for slot, other in (("a", "b"), ("b", "a")):
            body = block(self.generated, f"te_tax_gen_store_{slot}")
            with self.subTest(slot=slot):
                self.assertRegex(body, rf"if = \{{\s*limit = \{{ var:te_tax_p{other}_seq > var:te_tax_p{slot}_seq \}}\s*"
                                       rf"set_variable = \{{ name = te_tax_p{slot}_seq value = var:te_tax_p{other}_seq \}}\s*\}}\s*"
                                       rf"change_variable = \{{ name = te_tax_p{slot}_seq add = 1 \}}")

    def test_store_never_touches_the_enacted_code_or_collection(self):
        for slot in SLOTS:
            body = block(self.generated, f"te_tax_gen_store_{slot}")
            with self.subTest(slot=slot):
                self.assertNotRegex(body, r"name = te_tax_en_")
                self.assertNotIn("te_tax_sync_collection", body)
                self.assertNotIn("te_tax_code_version", body)
                self.assertNotIn("te_tax_gen_history_write", body, "Task 6's pass records kind 6")


class NextMonthTest(unittest.TestCase):
    def test_next_month_is_the_earliest_sunset_or_awaiting_due(self):
        body = block(read(GEN_EFFECTS), "te_tax_gen_next_month")
        self.assertTrue(body.strip().startswith("set_variable = { name = te_tax_next_month value = -1 }"))
        for key in KEYS:
            self.assertRegex(body, rf"var:te_tax_en_{key}_exp >= 0\s*OR = \{{\s*var:te_tax_next_month < 0\s*"
                                   rf"var:te_tax_en_{key}_exp < var:te_tax_next_month\s*\}}")
        for slot in SLOTS:
            self.assertRegex(body, rf"var:te_tax_p{slot}_on = 1\s*var:te_tax_p{slot}_state = 1\s*OR = \{{\s*"
                                   rf"var:te_tax_next_month < 0\s*var:te_tax_p{slot}_due < var:te_tax_next_month\s*\}}")
        self.assertIn("te_tax_gen_next_month = yes", block(read(SCHEDULE), "te_tax_recompute_next_month"))


class HistoryTest(unittest.TestCase):
    def test_ring_of_eight_with_a_cycling_head(self):
        body = block(read(GEN_EFFECTS), "te_tax_gen_history_write")
        self.assertRegex(body, r"if = \{\s*limit = \{\s*var:te_tax_h_head >= 1\s*var:te_tax_h_head < 8\s*\}\s*"
                               r"change_variable = \{ name = te_tax_h_head add = 1 \}\s*\}\s*"
                               r"else = \{\s*set_variable = \{ name = te_tax_h_head value = 1 \}\s*\}")
        for n in range(1, 9):
            with self.subTest(n=n):
                self.assertIn(f"limit = {{ var:te_tax_h_head = {n} }}", body)
                for field, value in (("month", "te_history_month_index"), ("kind", "$KIND$"),
                                     ("slot", "te_tax_slot_id_$SLOT$"), ("inst", "$INST$"),
                                     ("version", "var:te_tax_code_version")):
                    self.assertIn(f"set_variable = {{ name = te_tax_h{n}_{field} value = {value} }}", body)
        self.assertNotIn("te_tax_h9_", body)

    def test_public_push_takes_kind_and_slot(self):
        body = block(read(SCHEDULE), "te_tax_history_push")
        self.assertIn("te_tax_gen_history_write = { KIND = $KIND$ SLOT = $SLOT$ INST = 0 }", body)

    def test_slot_ids(self):
        values = read(GEN_VALUES)
        for name, value in (("none", 0), ("a", 1), ("b", 2)):
            self.assertRegex(values, rf"(?m)^te_tax_slot_id_{name} = {value}$")


class SchemaTest(unittest.TestCase):
    def test_slot_history_and_clock_tokens_are_in_the_schema(self):
        country, state = schema_tokens()
        expected = {"te_tax_now": -1, "te_tax_h_head": 0}
        for slot in SLOTS:
            expected.update({f"te_tax_p{slot}_on": 0, f"te_tax_p{slot}_due": -1,
                             f"te_tax_p{slot}_state": 0, f"te_tax_p{slot}_seq": 0})
        for n in range(1, 9):
            expected.update({f"te_tax_h{n}_month": -1, f"te_tax_h{n}_kind": 0, f"te_tax_h{n}_slot": 0,
                             f"te_tax_h{n}_inst": 0, f"te_tax_h{n}_version": -1})
        for token, sentinel in expected.items():
            with self.subTest(token=token):
                self.assertEqual(country.get(token, "missing"), sentinel)
        for slot in SLOTS:
            self.assertNotIn(f"te_tax_pending_relief_{slot}", state)    # Task 11 fix round 1: a slot list
            # Package payload: written in full by the store, read only while _on = 1.
            for key in KEYS:
                for suffix in ("", "_exp", "_succ"):
                    self.assertIn(f"te_tax_p{slot}_{key}{suffix}", country)
                    self.assertIsNone(country[f"te_tax_p{slot}_{key}{suffix}"])
                self.assertIsNone(country[f"te_tax_p{slot}_xver_{key}"])
            for good in catalog():
                self.assertIsNone(country[f"te_tax_p{slot}_g_{good}"])

    def test_init_calls_the_schedule_init_before_the_schema_version(self):
        init = block(read("common/scripted_effects/te_tax_state_effects.txt"), "te_tax_init_country")
        self.assertIn("te_tax_gen_init_schedule = yes", init)
        self.assertLess(init.find("te_tax_gen_init_schedule = yes"), init.find("name = te_tax_schema"))

    def test_doc_carries_the_processor_rules_and_the_dispatch(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        section = doc.split("## Scheduler", 1)[1].split("\n## ", 1)[0]
        for phrase in ("Sunsets first", "te_tax_last_month", "_since < now", "_due = now",
                       "held_missed", "held_conflict", "_exp ≥ _due + 1", "on_monthly_pulse",
                       "watchdog", "te_tax_store_package", "te_tax_history_push"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_probe_runbook_points_to_the_global_pulse_retest(self):
        runbook = read(PROBE_RUNBOOK, strip_comments=False)
        self.assertIn("tax-code-capability-ledger.md", runbook)
        self.assertRegex(runbook, r"global .*on_monthly_pulse")


class SafetyTest(unittest.TestCase):
    def test_no_scheduler_file_removes_a_variable(self):
        for path in SCHEDULER_FILES:
            with self.subTest(path=path):
                self.assertNotIn("remove_variable", read(path))

    def test_no_schema_token_is_removed_anywhere_in_the_tax_code(self):
        country, state = schema_tokens()
        tokens = set(country) | set(state)
        pattern = re.compile(r"remove_variable\s*=\s*(?:\{[^}]*?name\s*=\s*)?([\w$]+)")
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("te_tax_*.txt")):
                for name in pattern.findall(read(path.relative_to(ROOT).as_posix())):
                    with self.subTest(path=path.name, name=name):
                        self.assertNotIn(name, tokens)

    def test_scheduler_never_reads_root(self):
        for path in SCHEDULER_FILES:
            with self.subTest(path=path):
                self.assertNotRegex(read(path), r"\bROOT\b|\broot\b")

    def test_every_processor_branch_that_changes_state_logs(self):
        state_write = re.compile(
            r"name = te_tax_(last_month|en_\w+|p[ab]_state|p[ab]_on|code_version) "
            r"|te_tax_gen_history_write"
        )
        defined = effects()
        family = ["te_tax_process_month", "te_tax_watchdog_month", "te_tax_store_package",
                  *(f"te_tax_gen_sunset_{key}" for key in KEYS),
                  *(f"te_tax_gen_commence_{slot}" for slot in SLOTS),
                  *(f"te_tax_gen_hold_missed_{slot}" for slot in SLOTS)]
        for name in family:
            for kind, nested in branches(defined[name]):
                if state_write.search(direct(nested)):
                    with self.subTest(name=name, branch=direct(nested)[:60]):
                        lines = logs(nested)
                        self.assertTrue(lines, "branch changes schedule state without a debug_log")
                        for line in lines:
                            self.assertTrue(line.startswith("TE_TAX "))
                            self.assertIn(MONTH, line)
                            self.assertIn(DATE, line)

    def test_debug_lines_carry_no_parameters_or_root(self):
        for path in SCHEDULER_FILES:
            for line in re.findall(r'debug_log = "([^"]*)"', read(path)):
                with self.subTest(path=path, line=line[:50]):
                    self.assertNotIn("$", line)
                    self.assertNotIn("ROOT", line)

    def test_files_have_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in HAND_WRITTEN + (TRIGGERS,):
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)

    def test_generated_names_are_registered_with_the_generator(self):
        self.assertIn(GEN_EFFECTS, gen.OUTPUTS)
        names = set(re.findall(r"(?m)^(\w+) = \{", read(GEN_EFFECTS)))
        for name in ("te_tax_gen_init_schedule", "te_tax_gen_next_month", "te_tax_gen_history_write",
                     *(f"te_tax_gen_sunset_{key}" for key in KEYS),
                     *(f"te_tax_gen_{part}_{slot}" for part in ("commence", "hold_missed", "apply", "store")
                       for slot in SLOTS)):
            with self.subTest(name=name):
                self.assertIn(name, names)


if __name__ == "__main__":
    unittest.main()
