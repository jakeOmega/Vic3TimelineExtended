"""The legislated tax code's draft, bill and passage lifecycle (plan Task 6).

Structural checks on the committed script (no game install needed):

* every command `te_tax_cmd_<c>` has a same-named validation trigger
  `te_tax_can_<c>` and runs only inside `if = { limit = { te_tax_can_<c> ... } }`,
  and says what it does with a `custom_tooltip`;
* draft commands write only draft variables (`te_tax_dr_*`), following every
  helper they dispatch to with its `$KEY$` / `$DIR$` / `$GOOD$` expanded, and
  never touch the enacted code, a package slot or the collection writer;
* the bill record is written in full: every `te_tax_bl_*` field
  `te_tax_store_package` reads is written by the copy from the draft;
* `te_tax_cmd_pass` supersedes only the other approved slot, then bumps the
  planned versions, stores, records history kind 6; nothing it reaches writes
  an enacted provision or its sunset;
* the passage trigger holds every brief condition, each inside a
  `custom_tooltip`, and includes `te_tax_can_store_package`;
* the support model's numbers equal the brief's tables, ported here
  independently (not read back from the generator), and marginal interest
  groups are left out of both sums of the committed share.

Run: python3 -m unittest test_tax_code_bill -v
"""

import json
import re
import unittest
from decimal import Decimal
from itertools import product
from pathlib import Path

from test_tax_code_rule import load
from test_tax_code_scheduler import branches, direct, limit_of
from test_tax_code_state import KEYS, block, catalog, close, gen, read, schema_tokens, top_level_names

ROOT = Path(__file__).resolve().parent

BILL = "common/scripted_effects/te_tax_bill_effects.txt"
GEN_BILL = "common/scripted_effects/te_tax_generated_bill_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
SCHEDULE = "common/scripted_effects/te_tax_schedule_effects.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
SUPPORT = "common/script_values/te_tax_support_values.txt"
GEN_VALUES = "common/script_values/te_tax_generated_support_values.txt"
LOC = "localization/english/te_tax_l_english.yml"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
AUTO_GENERATED_DOC = "docs/auto_generated_files.md"
NIGHTLY_SELECT = "scripts/nightly_audit_select.py"

SLOTS = ("a", "b")

# The brief's tables, ported by hand. A change to the model changes both.
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# Exposure (0-1) of each interest group to each tax channel.
EXPOSURE = {
    "trade_unions": {"wage": "1.0", "div": "0.0", "land": "0.0", "head": "0.8", "cons": "0.8"},
    "rural_folk": {"wage": "0.4", "div": "0.1", "land": "1.0", "head": "0.3", "cons": "0.8"},
    "petty_bourgeoisie": {"wage": "0.6", "div": "0.4", "land": "0.1", "head": "0.5", "cons": "0.6"},
    "intelligentsia": {"wage": "0.6", "div": "0.2", "land": "0.0", "head": "0.3", "cons": "0.4"},
    "devout": {"wage": "0.4", "div": "0.3", "land": "0.3", "head": "0.4", "cons": "0.5"},
    "armed_forces": {"wage": "0.3", "div": "0.2", "land": "0.1", "head": "0.3", "cons": "0.4"},
    "industrialists": {"wage": "0.2", "div": "1.0", "land": "0.0", "head": "0.1", "cons": "0.2"},
    "landowners": {"wage": "0.1", "div": "0.8", "land": "0.3", "head": "0.1", "cons": "0.2"},
}
# One vanilla tax level, per channel.
LEVEL_STEP = {"wage": "0.05", "div": "0.05", "land": "0.15", "head": "0.15", "cons": "0.05"}
# Vanilla 1.14.5 taxation laws and their progressiveness.
PROGRESSIVENESS = {
    "law_consumption_based_taxation": -100,
    "law_land_based_taxation": -50,
    "law_per_capita_based_taxation": 0,
    "law_proportional_taxation": 50,
    "law_graduated_taxation": 100,
}
# law_stance buckets: the comparison each branch tests, and the stance it scores.
STANCE_BRANCHES = (("value > approve", 2), ("value > neutral", 1),
                   ("value < disapprove", -2), ("value < neutral", -1))
PASSAGE_VALUES = {
    "te_tax_passage_legitimacy": "25",
    "te_tax_passage_share": "0.5",
    "te_tax_commit_threshold": "20",
    "te_tax_redline_threshold": "-40",
    "te_tax_debate_days_major": "30",
    "te_tax_debate_days_minor": "15",
}
SUNSET_LADDER = (0, 6, 12, 24, 36, 60)
KIND_APPROVED, KIND_SUPERSEDED, KIND_RESCHEDULED, KIND_RELEASED = 6, 8, 9, 10
# A held_missed package may be rescheduled when the delay since its approved due
# month is at most this many months (controller ruling, Task 6 fix round 1).
RESCHEDULE_MAX_DELAY = 3

# Commands and their parameters, in the order the effect passes them on.
COMMANDS = {
    "draft_new": (),
    "draft_step": ("KEY", "DIR"),
    "draft_sunset": ("KEY", "DIR"),
    "draft_due": ("DIR",),
    "draft_good": ("GOOD",),
    # Relief in a bill (Task 11); draft_relief_state reads its state from the
    # saved scope te_tax_st, so it takes no parameter.
    "draft_relief": ("KEY", "DIR"),
    "draft_relief_choose": (),
    "draft_relief_state": (),
    "draft_discard": (),
    "draft_rebase": ("KEY",),
    "introduce": (),
    "revise": (),
    "withdraw": (),
    "pass": (),
    "reschedule": (),
    "package_reschedule": ("SLOT",),
    "package_release": ("SLOT",),
}
DRAFT_COMMANDS = tuple(name for name in COMMANDS if name.startswith("draft_"))
# The values each parameter takes for each command.
DOMAINS = {
    "draft_step": {"KEY": KEYS, "DIR": ("0", "1", "2", "3", "4")},
    "draft_sunset": {"KEY": KEYS, "DIR": ("0", "1")},
    "draft_due": {"DIR": ("0", "1")},
    "draft_good": {"GOOD": None},           # the catalog, filled in lazily
    "draft_relief": {"KEY": ("agrel", "regrel"), "DIR": ("0", "1", "2", "3", "4")},
    "draft_rebase": {"KEY": KEYS + ("goods", "relief")},
    "package_reschedule": {"SLOT": SLOTS},
    "package_release": {"SLOT": SLOTS},
}

WRITE = re.compile(r"\b(?:set_variable|change_variable|clamp_variable|add_to_variable_list|remove_list_variable)"
                   r" = \{ name = ([\w$]+)|\bremove_variable = ([\w$]+)|\bclear_variable_list = ([\w$]+)")
CALL = re.compile(r"\b(te_tax_[\w$]+|ig_approval_effect) = (?:yes|\{)")
FORBIDDEN_IN_DRAFTS = ("te_tax_store_package", "te_tax_sync_collection", "te_tax_history_push",
                       "te_tax_refresh_support", "te_tax_recompute_next_month")


def definitions(*paths):
    """{name: body} for every top-level definition in the files."""
    defined = {}
    for path in paths:
        text = read(path)
        for match in re.finditer(r"(?m)^(\w+) = \{", text):
            defined[match.group(1)] = text[match.end():close(text, match.end() - 1)]
    return defined


def all_effects():
    return definitions(*sorted(p.relative_to(ROOT).as_posix()
                               for p in (ROOT / "common/scripted_effects").glob("te_tax_*.txt")))


def expand(name, assignment):
    """`name` with each `$P$` replaced from `assignment`."""
    for param, value in assignment.items():
        name = name.replace(f"${param}$", value)
    return name


def reach(root, assignment, defined):
    """{name: body} reachable from `root` with the parameters of `assignment` substituted.

    Helpers are dispatched by name (`te_tax_dr_step_$DIR$ = { KEY = $KEY$ }`), and
    every level passes its parameters on under the same names, so substituting
    the command's own assignment into each body follows the real call graph.
    """
    seen, todo = {}, [root]
    while todo:
        name = todo.pop()
        if name in seen or name not in defined:
            continue
        body = expand(defined[name], assignment)
        seen[name] = body
        for call in CALL.findall(body):
            if "$" not in call:
                todo.append(call)
    return seen


def assignments(command):
    domains = dict(DOMAINS.get(command, {}))
    if "GOOD" in domains:
        domains["GOOD"] = catalog()
    params = COMMANDS[command]
    for values in product(*(domains[param] for param in params)):
        yield dict(zip(params, values))


def written(bodies):
    names = set()
    for body in bodies:
        for groups in WRITE.findall(body):
            names.update(group for group in groups if group)
    return names


def custom_tooltip_bodies(text):
    """The bodies of every `custom_tooltip = { ... }` block in `text`."""
    found = []
    for match in re.finditer(r"custom_tooltip = \{", text):
        found.append(text[match.end():close(text, match.end() - 1)])
    return found


def loc_entries():
    entries = {}
    for line in read(LOC, strip_comments=False).splitlines():
        match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
        if match:
            entries[match.group(1)] = match.group(2)
    return entries


def value_number(text):
    return Decimal(text)


class CommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bill = read(BILL)
        cls.triggers = read(TRIGGERS)
        cls.defined = all_effects()

    def test_every_command_has_a_same_named_trigger(self):
        commands = {name for name in top_level_names(self.bill) if name.startswith("te_tax_cmd_")}
        self.assertEqual(commands, {f"te_tax_cmd_{name}" for name in COMMANDS})
        triggers = set(top_level_names(self.triggers))
        for name in COMMANDS:
            with self.subTest(command=name):
                self.assertIn(f"te_tax_can_{name}", triggers)

    def test_every_command_runs_only_when_its_trigger_holds(self):
        for name, params in COMMANDS.items():
            body = block(self.bill, f"te_tax_cmd_{name}")
            args = "yes" if not params else "{ " + " ".join(f"{p} = ${p}$" for p in params) + " }"
            with self.subTest(command=name):
                self.assertRegex(body, r"^\s*if = \{\s*limit = \{ " + re.escape(f"te_tax_can_{name} = {args}") + r" \}")
                opener = body.find("if = {") + len("if = {") - 1
                self.assertEqual(body[close(body, opener) + 1:].strip(), "", "nothing runs outside the guarded if")

    def test_every_command_says_what_it_does(self):
        for name in COMMANDS:
            for assignment in assignments(name):
                bodies = reach(f"te_tax_cmd_{name}", assignment, self.defined)
                keys = [key for body in bodies.values()
                        for key in re.findall(r"custom_tooltip = (te_tax_tt_cmd_\w+)", body)]
                with self.subTest(command=name, **assignment):
                    self.assertTrue(keys, "a command needs a custom_tooltip describing it")

    def test_draft_commands_write_only_the_draft(self):
        for name in DRAFT_COMMANDS:
            for assignment in assignments(name):
                bodies = reach(f"te_tax_cmd_{name}", assignment, self.defined)
                with self.subTest(command=name, **assignment):
                    names = written(bodies.values())
                    self.assertTrue(names)
                    self.assertEqual({n for n in names if not n.startswith("te_tax_dr_")}, set())
                    for forbidden in FORBIDDEN_IN_DRAFTS:
                        self.assertNotIn(forbidden, bodies)
                    self.assertFalse([n for n in bodies if re.match(r"te_tax_gen_(store|apply|sync|commence|"
                                                                    r"supersede|bump_pver|history_write)", n)])

    def test_bill_commands_never_touch_the_enacted_code_or_a_package(self):
        for name in ("introduce", "revise", "withdraw", "reschedule"):
            bodies = reach(f"te_tax_cmd_{name}", {}, self.defined)
            with self.subTest(command=name):
                names = written(bodies.values())
                self.assertFalse({n for n in names if re.match(r"te_tax_(en_|p[ab]_|pver_|xver_|code_version)", n)})
                for forbidden in ("te_tax_store_package", "te_tax_sync_collection", "te_tax_history_push"):
                    self.assertNotIn(forbidden, bodies)

    def test_draft_step_ops_and_sunset_ladder(self):
        for direction in range(5):
            self.assertIn(f"te_tax_dr_step_{direction}", self.defined)
        step = block(self.bill, "te_tax_cmd_draft_step")
        self.assertIn("te_tax_dr_step_$DIR$ = { KEY = $KEY$ }", step)
        sunset = block(self.bill, "te_tax_cmd_draft_sunset")
        self.assertIn("te_tax_dr_sunset_$DIR$ = { KEY = $KEY$ }", sunset)
        up = self.defined["te_tax_dr_sunset_1"]
        down = self.defined["te_tax_dr_sunset_0"]
        for low, high in zip(SUNSET_LADDER, SUNSET_LADDER[1:]):
            with self.subTest(low=low, high=high):
                self.assertRegex(up, rf"var:te_tax_dr_\$KEY\$_sun = {low} \}}\s*"
                                     rf"set_variable = \{{ name = te_tax_dr_\$KEY\$_sun value = {high} \}}")
                self.assertRegex(down, rf"var:te_tax_dr_\$KEY\$_sun = {high} \}}\s*"
                                       rf"set_variable = \{{ name = te_tax_dr_\$KEY\$_sun value = {low} \}}")

    def test_first_touch_records_the_planned_version(self):
        touch = self.defined["te_tax_dr_touch"]
        self.assertRegex(touch, r"limit = \{ var:te_tax_dr_\$KEY\$ < 0 \}\s*"
                                r"set_variable = \{ name = te_tax_dr_\$KEY\$_pver value = var:te_tax_pver_\$KEY\$ \}")
        for direction in range(4):
            with self.subTest(direction=direction):
                body = self.defined[f"te_tax_dr_step_{direction}"]
                self.assertTrue(body.strip().startswith("custom_tooltip = te_tax_tt_cmd_draft_step_"))
                self.assertLess(body.find("te_tax_dr_touch = { KEY = $KEY$ }"),
                                body.find("name = te_tax_dr_$KEY$ value"))
        rebase = block(self.bill, "te_tax_cmd_draft_rebase")
        self.assertIn("set_variable = { name = te_tax_dr_$KEY$_pver value = var:te_tax_pver_$KEY$ }", rebase)

    def test_introduce_and_revise_start_the_debate(self):
        introduce = block(self.bill, "te_tax_cmd_introduce")
        revise = block(self.bill, "te_tax_cmd_revise")
        self.assertIn("te_tax_gen_bill_from_draft = yes", introduce)
        self.assertIn("te_tax_gen_bill_from_draft = yes", revise)
        self.assertIn("set_variable = { name = te_tax_bl_rev value = 1 }", introduce)
        self.assertIn("change_variable = { name = te_tax_bl_rev add = 1 }", revise)
        for body in (introduce, revise):
            self.assertGreater(body.find("te_tax_bill_start_debate = yes"), body.find("te_tax_bl_rev"))
        start = self.defined["te_tax_bill_start_debate"]
        self.assertIn("set_variable = { name = te_tax_bl_day value = game_date }", start)
        reset = start.find("te_tax_gen_reset_commitments = yes")
        on = start.find("set_variable = { name = te_tax_bl_on value = 1 }")
        refresh = start.find("te_tax_refresh_support = yes")
        self.assertTrue(0 <= reset < refresh and 0 <= on < refresh)
        self.assertLess(start.find("te_tax_bill_set_minor = yes"), refresh)

    def test_a_draft_must_be_reconciled_before_it_becomes_the_bill(self):
        ready = block(self.triggers, "te_tax_draft_ready")
        for condition in ("te_tax_gen_draft_touches_any = yes", "te_tax_gen_draft_baseline_current = yes",
                          "var:te_tax_dr_due >= te_tax_due_earliest", "var:te_tax_dr_due <= te_tax_due_latest"):
            with self.subTest(condition=condition):
                self.assertTrue(any(condition in tip for tip in custom_tooltip_bodies(ready)))
        for name in ("introduce", "revise"):
            self.assertIn("te_tax_draft_ready = yes", block(self.triggers, f"te_tax_can_{name}"))
        self.assertIn("te_tax_gen_draft_differs_from_bill = yes", block(self.triggers, "te_tax_can_revise"))

    def test_reschedule_moves_the_bill_to_next_month(self):
        body = block(self.bill, "te_tax_cmd_reschedule")
        self.assertIn("set_variable = { name = te_tax_bl_due value = te_tax_due_earliest }", body)
        can = block(self.triggers, "te_tax_can_reschedule")
        self.assertIn("NOT = { var:te_tax_bl_due > te_history_month_index }", can)
        earliest = load(SUPPORT)["te_tax_due_earliest"]
        self.assertEqual(earliest, {"value": "te_history_month_index", "add": "1"})

    def test_reschedule_restarts_debate_only_when_the_class_changes(self):
        body = block(self.bill, "te_tax_cmd_reschedule")
        restart = [nested for _, nested in branches(body)
                   if "set_variable = { name = te_tax_bl_day value = game_date }" in direct(nested)]
        self.assertEqual(len(restart), 1)
        gate = re.sub(r"\s+", " ", limit_of(restart[0]))
        self.assertIn("AND = { var:te_tax_bl_minor = 1 NOT = { te_tax_bill_is_minor = yes } }", gate)
        self.assertIn("AND = { var:te_tax_bl_minor = 0 te_tax_bill_is_minor = yes }", gate)
        positions = [body.find(step) for step in ("name = te_tax_bl_due value = te_tax_due_earliest",
                                                  "name = te_tax_bl_day value = game_date",
                                                  "te_tax_bill_set_minor = yes", "te_tax_refresh_support = yes")]
        self.assertTrue(all(position >= 0 for position in positions))
        self.assertEqual(positions, sorted(positions), "new due, then the class test, then the new class")
        self.assertNotIn("te_tax_bl_rev", body, "a reschedule is not a revision")

    def test_withdraw_and_discard_leave_the_code_alone(self):
        withdraw = reach("te_tax_cmd_withdraw", {}, self.defined)
        self.assertIn("te_tax_bill_close", withdraw)
        close_names = written([withdraw["te_tax_bill_close"], withdraw["te_tax_gen_bill_clear"]])
        self.assertIn("te_tax_bl_on", close_names)
        self.assertFalse({n for n in close_names if not n.startswith(("te_tax_bl_", "te_tax_com_"))})


class PassTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bill = read(BILL)
        cls.generated = read(GEN_BILL)
        cls.defined = all_effects()
        cls.body = block(cls.bill, "te_tax_cmd_pass")

    def test_pass_picks_slot_a_if_free_else_b(self):
        self.assertRegex(self.body, r"if = \{\s*limit = \{ var:te_tax_pa_on = 0 \}\s*"
                                    r"te_tax_pass_into = \{ SLOT = a OTHER = b \}\s*\}\s*"
                                    r"else = \{\s*te_tax_pass_into = \{ SLOT = b OTHER = a \}\s*\}")

    def guarded_pass(self):
        """The body of te_tax_pass_into's branch that runs when the store will accept the bill."""
        into = self.defined["te_tax_pass_into"]
        self.assertRegex(into, r"^\s*if = \{\s*limit = \{ te_tax_can_store_package = \{ SLOT = \$SLOT\$ \} \}")
        opener = into.find("if = {") + len("if = {") - 1
        self.assertTrue(into[close(into, opener) + 1:].strip().startswith("else = {"))
        return into[opener + 1:close(into, opener)]

    def test_pass_supersedes_bumps_stores_and_records_in_order(self):
        body = self.guarded_pass()
        order = [body.find(step) for step in ("te_tax_gen_supersede_$OTHER$ = yes", "te_tax_gen_bump_pver = yes",
                                              "te_tax_store_package = { SLOT = $SLOT$ }",
                                              f"te_tax_history_push = {{ KIND = {KIND_APPROVED} SLOT = $SLOT$ }}")]
        self.assertTrue(all(position >= 0 for position in order))
        self.assertEqual(order, sorted(order))

    def test_nothing_runs_unless_the_store_accepts_the_bill(self):
        # te_tax_store_package checks exactly te_tax_can_store_package, and nothing
        # between this check and the store changes what it reads (supersession
        # writes only the other slot, the bump only te_tax_pver_*), so history,
        # reactions and closing the bill run only when the package is stored.
        into = self.defined["te_tax_pass_into"]
        opener = into.find("if = {") + len("if = {") - 1
        refused = into[close(into, opener) + 1:]
        self.assertNotRegex(refused, r"set_variable|change_variable|te_tax_(history_push|bill_close|gen_)")
        self.assertIn('debug_log = "TE_TAX pass_refused', refused)
        for step in ("te_tax_history_push", "te_tax_gen_oppose_approval", "te_tax_bill_close",
                     "te_tax_draft_close", "te_tax_gen_supersede_", "te_tax_gen_bump_pver"):
            self.assertNotIn(step, self.body, "runs only inside te_tax_pass_into's guarded branch")

    def test_pass_then_reacts_discards_an_identical_draft_and_closes_the_bill(self):
        body = self.guarded_pass()
        steps = [body.find(step) for step in ("te_tax_store_package", "te_tax_gen_oppose_approval = yes",
                                              "te_tax_draft_close = yes", "te_tax_bill_close = yes")]
        self.assertTrue(all(position >= 0 for position in steps))
        self.assertEqual(steps, sorted(steps))
        discard = [nested for _, nested in branches(body) if "te_tax_draft_close = yes" in direct(nested)]
        self.assertEqual(len(discard), 1)
        self.assertIn("NOT = { te_tax_gen_draft_differs_from_bill = yes }", limit_of(discard[0]))

    def test_nothing_pass_reaches_writes_an_enacted_provision_or_its_sunset(self):
        for slot, other in (("a", "b"), ("b", "a")):
            bodies = reach("te_tax_cmd_pass", {"SLOT": slot, "OTHER": other}, self.defined)
            with self.subTest(slot=slot):
                self.assertIn("te_tax_store_package", bodies)
                self.assertIn(f"te_tax_gen_supersede_{other}", bodies)
                self.assertNotIn(f"te_tax_gen_supersede_{slot}", bodies)
                names = written(bodies.values())
                self.assertFalse({n for n in names if n.startswith("te_tax_en_")})
                for forbidden in ("te_tax_sync_collection", "te_tax_gen_apply_a", "te_tax_gen_apply_b",
                                  "te_tax_gen_commence_a", "te_tax_gen_commence_b"):
                    self.assertNotIn(forbidden, bodies)

    def test_supersession_touches_only_the_other_slot_due_on_or_after(self):
        for slot in SLOTS:
            body = block(self.generated, f"te_tax_gen_supersede_{slot}")
            gate = limit_of(body[body.find("if = {") + len("if = {"):])
            with self.subTest(slot=slot):
                self.assertIn(f"var:te_tax_p{slot}_on = 1", gate)
                self.assertIn(f"var:te_tax_p{slot}_due >= var:te_tax_bl_due", gate)
                self.assertNotIn("te_tax_en_", body)
                self.assertNotRegex(body, rf"te_tax_p{gen._other(slot)}_")
                for key in KEYS:
                    stripped = [nested for _, nested in branches(body)
                                if f"name = te_tax_p{slot}_{key} value = -1" in direct(nested)]
                    self.assertEqual(len(stripped), 1, key)
                    self.assertIn(f"var:te_tax_bl_{key} >= 0", limit_of(stripped[0]))
                    self.assertIn(f"var:te_tax_p{slot}_{key} >= 0", limit_of(stripped[0]))
                    for suffix in ("_exp", "_succ"):
                        self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_{key}{suffix} value = -1 }}",
                                      stripped[0])
                for good in catalog():
                    self.assertIn(f"var:te_tax_bl_g_{good} >= 0 var:te_tax_p{slot}_g_{good} >= 0", body)
                self.assertIn(f"te_tax_history_push = {{ KIND = {KIND_SUPERSEDED} SLOT = {slot} }}", body)
                emptied = [nested for _, nested in branches(body)
                           if limit_of(nested).strip() == f"te_tax_gen_package_empty_{slot} = yes"]
                self.assertEqual(len(emptied), 1)
                self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_on value = 0 }}", emptied[0])

    def test_planned_versions_move_for_every_provision_the_bill_touches(self):
        body = block(self.generated, "te_tax_gen_bump_pver")
        for key in KEYS:
            self.assertRegex(body, rf"limit = \{{ var:te_tax_bl_{key} >= 0 \}}\s*"
                                   rf"change_variable = \{{ name = te_tax_pver_{key} add = 1 \}}")
        self.assertIn("change_variable = { name = te_tax_pver_goods add = 1 }", body)
        self.assertIn("change_variable = { name = te_tax_pver_relief add = 1 }", body)

    def test_opposed_groups_disapprove_through_the_shared_macro(self):
        body = block(self.generated, "te_tax_gen_oppose_approval")
        for ig in IGS:
            pattern = (rf"var:te_tax_sup_{ig} < 0.*?"
                       rf"ig_approval_effect = \{{ IG = ig_{ig} MODIFIER = ig_approval_negative_modifier "
                       rf"DAYS = te_tax_opposed_approval_days \}}")
            with self.subTest(ig=ig):
                self.assertRegex(body, re.compile(pattern, re.S))
                self.assertIn(f"var:te_tax_com_{ig} = 1 var:te_tax_com_{ig}_rev = var:te_tax_bl_rev", body)
        self.assertEqual(load(SUPPORT)["te_tax_opposed_approval_days"], "180")


class PackageCommandTest(unittest.TestCase):
    """Resolving a held package (Task 6 fix round 1): reschedule a missed one, release either kind."""

    @classmethod
    def setUpClass(cls):
        cls.bill = read(BILL)
        cls.triggers = read(TRIGGERS)
        cls.defined = all_effects()

    def tips(self, name):
        return [re.sub(r"\s+", " ", tip) for tip in custom_tooltip_bodies(block(self.triggers, name))]

    def test_reschedule_needs_a_missed_package_delayed_at_most_three_months(self):
        tips = self.tips("te_tax_can_package_reschedule")
        for condition in ("var:te_tax_p$SLOT$_on = 1", "var:te_tax_p$SLOT$_state = 3",
                          "var:te_tax_p$SLOT$_due0 >= te_tax_package_reschedule_floor",
                          "te_tax_gen_package_unsuperseded_$SLOT$ = yes"):
            with self.subTest(condition=condition):
                self.assertTrue(any(condition in tip for tip in tips))
        body = block(self.triggers, "te_tax_can_package_reschedule")
        self.assertNotRegex(body, r"_state = [12]\b", "held_conflict and awaiting packages are refused")
        self.assertIn("has_variable = te_tax_p$SLOT$_due0", body)
        values = load(SUPPORT)
        self.assertEqual(Decimal(values["te_tax_reschedule_max_delay"]), RESCHEDULE_MAX_DELAY)
        # earliest - due0 <= 3  <=>  due0 >= earliest - 3
        self.assertEqual(values["te_tax_package_reschedule_floor"],
                         {"value": "te_tax_due_earliest", "subtract": "te_tax_reschedule_max_delay"})
        self.assertIn("te_tax_tt_package_delay", body)

    def test_release_needs_a_held_package(self):
        tips = self.tips("te_tax_can_package_release")
        self.assertTrue(any("var:te_tax_p$SLOT$_on = 1" in tip for tip in tips))
        self.assertTrue(any("OR = { var:te_tax_p$SLOT$_state = 2 var:te_tax_p$SLOT$_state = 3 }" in tip
                            for tip in tips))
        self.assertNotRegex(block(self.triggers, "te_tax_can_package_release"), r"_state = 1\b")

    def test_reschedule_moves_the_due_month_and_reawaits_without_accepting_conflicts(self):
        body = block(self.bill, "te_tax_cmd_package_reschedule")
        for line in ("set_variable = { name = te_tax_p$SLOT$_due value = te_tax_due_earliest }",
                     "set_variable = { name = te_tax_p$SLOT$_state value = 1 }",
                     f"te_tax_history_push = {{ KIND = {KIND_RESCHEDULED} SLOT = $SLOT$ }}",
                     "te_tax_recompute_next_month = yes"):
            self.assertIn(line, body)
        self.assertNotIn("xver", body, "a missed package has no conflict to accept")
        self.assertNotIn("_due0", re.sub(r"var:te_tax_p\$SLOT\$_due0", "", body), "the approved month stays")

    def test_release_frees_the_slot_and_its_relief_marks(self):
        body = block(self.bill, "te_tax_cmd_package_release")
        for line in ("set_variable = { name = te_tax_p$SLOT$_on value = 0 }",
                     "set_variable = { name = te_tax_p$SLOT$_state value = 0 }",
                     f"te_tax_history_push = {{ KIND = {KIND_RELEASED} SLOT = $SLOT$ }}",
                     "te_tax_recompute_next_month = yes"):
            self.assertIn(line, body)
        self.assertRegex(body, r"every_scope_state = \{\s*limit = \{ has_variable = te_tax_pending_relief_\$SLOT\$ \}"
                               r"\s*set_variable = \{ name = te_tax_pending_relief_\$SLOT\$ value = 0 \}")

    def test_neither_touches_the_enacted_code_or_the_writer(self):
        for name in ("package_reschedule", "package_release"):
            for slot in SLOTS:
                bodies = reach(f"te_tax_cmd_{name}", {"SLOT": slot}, self.defined)
                names = written(bodies.values())
                with self.subTest(command=name, slot=slot):
                    self.assertIn(f"te_tax_cmd_{name}", bodies)
                    self.assertIn(f"te_tax_p{slot}_state", names)
                    self.assertFalse({n for n in names if re.match(r"te_tax_(en_|pver_|xver_|code_version|bl_|dr_)", n)})
                    self.assertFalse({n for n in names if n.startswith(f"te_tax_p{gen._other(slot)}_")})
                    for forbidden in ("te_tax_sync_collection", "te_tax_store_package", "te_tax_gen_apply_a",
                                      "te_tax_gen_apply_b", "te_tax_gen_commence_a", "te_tax_gen_commence_b"):
                        self.assertNotIn(forbidden, bodies)

    def test_store_records_the_approved_month_and_planned_versions(self):
        for slot in SLOTS:
            body = block(read(GEN_EFFECTS), f"te_tax_gen_store_{slot}")
            with self.subTest(slot=slot):
                self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_due0 value = var:te_tax_bl_due }}", body)
                for group in KEYS + ("goods", "relief"):
                    self.assertIn(f"set_variable = {{ name = te_tax_p{slot}_pver_{group} value = var:te_tax_pver_{group} }}",
                                  body)
            current = block(read(GEN_TRIGGERS), f"te_tax_gen_package_unsuperseded_{slot}")
            for key in KEYS:
                self.assertRegex(current, rf"OR = \{{\s*var:te_tax_p{slot}_{key} < 0\s*AND = \{{ has_variable = "
                                          rf"te_tax_p{slot}_pver_{key} var:te_tax_p{slot}_pver_{key} = var:te_tax_pver_{key} \}}")

    def test_doc_lists_the_new_history_kinds_and_fields(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        self.assertIn("9 rescheduled, 10 released", doc)
        country, _ = schema_tokens()
        for slot in SLOTS:
            self.assertIn(f"te_tax_p{slot}_due0", country)
            self.assertIsNone(country[f"te_tax_p{slot}_due0"])
            for group in KEYS + ("goods", "relief"):
                self.assertIsNone(country[f"te_tax_p{slot}_pver_{group}"])
        self.assertIn("held_conflict package can only be released", doc)


class PassageTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = read(TRIGGERS)
        cls.body = block(cls.triggers, "te_tax_can_pass")

    def test_every_condition_is_a_tooltip_line(self):
        tips = custom_tooltip_bodies(self.body)
        for condition in ("te_tax_code_in_force = yes",
                          "te_tax_committed_share > te_tax_passage_share",
                          "legitimacy >= te_tax_passage_legitimacy",
                          "te_tax_debate_days_left <= 0",
                          "var:te_tax_bl_due > te_history_month_index",
                          "OR = { var:te_tax_pa_on = 0 var:te_tax_pb_on = 0 }",
                          "te_tax_gen_bill_current = yes",
                          "te_tax_gen_bill_sunsets_valid = yes",
                          "te_tax_can_store_package = { SLOT = a }",
                          "te_tax_can_store_package = { SLOT = b }"):
            with self.subTest(condition=condition):
                self.assertTrue(any(condition in re.sub(r"\s+", " ", tip) for tip in tips))

    def test_the_bill_must_be_open_and_payload_reads_wait_for_it(self):
        start = self.body.find("trigger_if = {")
        self.assertGreaterEqual(start, 0)
        opener = start + len("trigger_if = {") - 1
        inner = self.body[opener + 1:close(self.body, opener)]
        self.assertEqual(limit_of(inner).strip(), "te_tax_bill_active = yes")
        leftover = inner
        for match in re.finditer(r"(limit|custom_tooltip) = \{", inner):
            leftover = leftover.replace(inner[match.start():close(inner, match.end() - 1) + 1], "")
        self.assertEqual(leftover.strip(), "", "every condition inside is a custom_tooltip line")
        self.assertRegex(self.body, r"trigger_else = \{\s*custom_tooltip = \{ text = te_tax_tt_bill_open always = no \}")
        active = block(self.triggers, "te_tax_bill_active")
        self.assertIn("var:te_tax_bl_on = 1", active)

    def test_code_in_force_needs_the_rule_and_a_migrated_code(self):
        body = block(self.triggers, "te_tax_code_in_force")
        for condition in ("te_tax_code_on = yes", "has_variable = te_tax_schema", "var:te_tax_migrated >= 1"):
            self.assertIn(condition, body)

    def test_bill_currency_compares_external_versions(self):
        body = block(read(GEN_TRIGGERS), "te_tax_gen_bill_current")
        for key in KEYS:
            self.assertRegex(body, rf"OR = \{{\s*var:te_tax_bl_{key} < 0\s*var:te_tax_bl_xver_{key} = var:te_tax_xver_{key}\s*\}}")
        self.assertIn("var:te_tax_bl_xver_goods = var:te_tax_xver_goods", body)
        self.assertIn("var:te_tax_bl_xver_relief = var:te_tax_xver_relief", body)

    def test_passage_values(self):
        values = load(SUPPORT)
        for name, value in PASSAGE_VALUES.items():
            with self.subTest(name=name):
                self.assertEqual(value_number(values[name]), value_number(value))


class SupportModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = read(GEN_VALUES)
        cls.support = read(SUPPORT)
        cls.parsed = {**load(GEN_VALUES), **load(SUPPORT)}

    def test_level_steps(self):
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(value_number(self.parsed[f"te_tax_level_step_{key}"]), value_number(LEVEL_STEP[key]))
                body = block(self.values, f"te_tax_dl_{key}")
                self.assertIn(f"value = te_tax_bl_dstep_{key}", body)
                self.assertIn(f"multiply = te_tax_step_{key}", body)
                self.assertIn(f"divide = te_tax_level_step_{key}", body)

    def test_material_reason_uses_the_exposure_table(self):
        for ig in IGS:
            body = block(self.values, f"te_tax_mat_{ig}")
            terms = dict(re.findall(r"add = \{ value = te_tax_dl_(\w+) multiply = ([\d.]+) \}", body))
            expected = {key: value for key, value in EXPOSURE[ig].items() if Decimal(value)}
            # The bill's goods count on the consumption channel (Task 11).
            expected["goods"] = EXPOSURE[ig]["cons"]
            with self.subTest(ig=ig):
                self.assertEqual({k: Decimal(v) for k, v in terms.items()},
                                 {k: Decimal(v) for k, v in expected.items()})
                # Relief points (test_tax_code_goods_relief.py) sit between the
                # weight and the clamp.
                self.assertRegex(body, r"multiply = -10\s*(add = \{ value = te_tax_bl_dstep_(agrel|regrel) "
                                       r"multiply = -?\d+ \}\s*)+min = -40\s*max = 40\s*$")

    def test_progressiveness_matches_vanilla(self):
        with open(ROOT / "vanilla_parsed" / "common" / "laws.json", encoding="utf-8") as handle:
            laws = json.load(handle)
        group = {name for name, body in laws.items() if "lawgroup_taxation" in json.dumps(body)}
        self.assertEqual(group, set(PROGRESSIVENESS))
        for law, value in PROGRESSIVENESS.items():
            self.assertIn(f"'progressiveness': ['=', '{value}']", str(laws[law]))

    def test_ideology_reason_scores_each_law_stance(self):
        for ig in IGS:
            body = block(self.values, f"te_tax_ideo_p_{ig}")
            with self.subTest(ig=ig):
                for law, progressiveness in PROGRESSIVENESS.items():
                    if progressiveness == 0:
                        self.assertNotIn(law, body)
                        continue
                    for comparison, stance in STANCE_BRANCHES:
                        weight = Decimal(stance * progressiveness) / 100
                        pattern = (rf"ig:ig_{ig} \?= \{{ law_stance = \{{ law = law_type:{law} {comparison} \}} \}} \}}"
                                   rf"\s*add = (-?[\d.]+)")
                        found = re.search(pattern, body)
                        self.assertIsNotNone(found, f"{law} {comparison}")
                        self.assertEqual(Decimal(found.group(1)), weight)
                # Strongly before mildly, so each stance scores once.
                self.assertLess(body.find("value > approve"), body.find("value > neutral"))
                self.assertLess(body.find("value < disapprove"), body.find("value < neutral"))
            reason = block(self.values, f"te_tax_ideo_{ig}")
            self.assertRegex(reason, rf"value = te_tax_ideo_p_{ig}\s*multiply = te_tax_dl_prog\s*multiply = 5\s*"
                                     r"min = -40\s*max = 40")
        prog = block(self.values, "te_tax_dl_prog")
        self.assertRegex(prog, r"value = te_tax_dl_wage\s*add = te_tax_dl_div\s*subtract = te_tax_dl_land\s*"
                               r"subtract = te_tax_dl_head\s*subtract = te_tax_dl_cons")

    def test_fiscal_and_government_reasons(self):
        fiscal = self.parsed["te_tax_fiscal_reason"]
        self.assertEqual(fiscal["if"]["limit"], {"net_fixed_income": "0"})
        self.assertIn("net_fixed_income < 0", block(self.support, "te_tax_fiscal_reason"))
        deficit, surplus = fiscal["if"], fiscal["else"]
        self.assertEqual((deficit["if"]["value"], deficit["else_if"]["value"]), ("8", "-8"))
        self.assertEqual((surplus["if"]["value"], surplus["else_if"]["value"]), ("-4", "4"))
        self.assertIn("te_tax_dl_total > 0", block(self.support, "te_tax_fiscal_reason"))
        for ig in IGS:
            gov = block(self.values, f"te_tax_gov_{ig}")
            self.assertRegex(gov, rf"ig:ig_{ig} \?= \{{ is_in_government = yes \}} \}}\s*value = 10")

    def test_refresh_clamps_and_commits(self):
        body = block(read(GEN_BILL), "te_tax_gen_refresh_support")
        for ig in IGS:
            with self.subTest(ig=ig):
                for reason in ("mat", "ideo", "fisc", "gov", "prom", "trust"):
                    self.assertIn(f"name = te_tax_sr_{ig}_{reason} value", body)
                    self.assertIn(f"change_variable = {{ name = te_tax_sup_{ig} add = var:te_tax_sr_{ig}_{reason} }}"
                                  if reason != "mat" else
                                  f"set_variable = {{ name = te_tax_sup_{ig} value = var:te_tax_sr_{ig}_mat }}", body)
                self.assertIn(f"clamp_variable = {{ name = te_tax_sup_{ig} min = -100 max = 100 }}", body)
                self.assertIn(f"NOT = {{ AND = {{ var:te_tax_com_{ig} = 1 var:te_tax_com_{ig}_rev = var:te_tax_bl_rev }} }}",
                              re.sub(r"\s+", " ", body))
                self.assertIn(f"var:te_tax_sup_{ig} >= te_tax_commit_threshold", body)
                self.assertIn(f"var:te_tax_sup_{ig} <= te_tax_redline_threshold", body)
                self.assertIn(f"set_variable = {{ name = te_tax_com_{ig} value = -1 }}", body)

    def test_marginal_groups_are_left_out_of_both_sums(self):
        for name in ("te_tax_eligible_clout", "te_tax_committed_clout"):
            body = block(self.values, name)
            blocks = [nested for kind, nested in branches(body) if kind == "if"]
            with self.subTest(name=name):
                self.assertEqual(len(blocks), len(IGS))
                for ig in IGS:
                    own = [nested for nested in blocks if f"add = ig:ig_{ig}.ig_clout" in nested]
                    self.assertEqual(len(own), 1, ig)
                    gate = limit_of(own[0])
                    self.assertIn(f"exists = ig:ig_{ig}", gate)
                    self.assertIn(f"ig:ig_{ig} = {{ ig_counts_as_marginal = no }}", gate)
                    if name == "te_tax_committed_clout":
                        self.assertIn(f"var:te_tax_com_{ig} = 1", gate)
                        self.assertIn(f"var:te_tax_com_{ig}_rev = var:te_tax_bl_rev", gate)
        share = self.parsed["te_tax_committed_share"]
        self.assertEqual(share["value"], "0")
        self.assertEqual(share["if"]["limit"], {"te_tax_eligible_clout": "0"})
        self.assertIn("te_tax_eligible_clout > 0", block(self.support, "te_tax_committed_share"))
        self.assertEqual(share["if"]["value"], "te_tax_committed_clout")
        self.assertEqual(share["if"]["divide"], "te_tax_eligible_clout")

    def test_debate_days_count_from_the_last_material_revision(self):
        elapsed = block(self.support, "te_tax_debate_days_elapsed")
        self.assertRegex(elapsed, r"value = game_date\s*subtract = var:te_tax_bl_day\s*min = 0")
        left = block(self.support, "te_tax_debate_days_left")
        self.assertRegex(left, r"value = te_tax_debate_days_required\s*subtract = te_tax_debate_days_elapsed\s*min = 0")
        required = self.parsed["te_tax_debate_days_required"]
        self.assertEqual(required["value"], "te_tax_debate_days_major")
        self.assertEqual(required["if"]["value"], "te_tax_debate_days_minor")

    def test_minor_bill_rule(self):
        self.assertIn("te_tax_bill_is_minor = yes", block(read(BILL), "te_tax_bill_set_minor"))
        body = block(read(TRIGGERS), "te_tax_bill_is_minor")
        for condition in ("te_tax_bl_provisions <= 2", "te_tax_gen_bill_small_steps = yes",
                          "NOT = { te_tax_gen_bill_touches_goods = yes }", "var:te_tax_bl_agrel < 0",
                          "var:te_tax_bl_regrel < 0"):
            self.assertIn(condition, body)
        small = block(read(GEN_TRIGGERS), "te_tax_gen_bill_small_steps")
        for key in KEYS:
            self.assertIn(f"te_tax_bl_dstep_{key} <= 2", small)
            self.assertIn(f"te_tax_bl_dstep_{key} >= -2", small)

    def test_support_values_never_write_or_sweep(self):
        names = [name for name in top_level_names(self.values)
                 if name.startswith(("te_tax_base_", "te_tax_dr_eff_", "te_tax_bl_", "te_tax_dl_", "te_tax_mat_",
                                     "te_tax_ideo_", "te_tax_gov_", "te_tax_eligible_", "te_tax_committed_"))]
        self.assertTrue(names)
        bodies = [block(self.values, name) for name in names] + [block(self.support, name)
                                                                  for name in top_level_names(self.support)]
        forbidden = re.compile(r"\b(set_variable|change_variable|remove_variable|save_scope_as|"
                               r"every_\w+|random_\w+|ordered_\w+)\b")
        for body in bodies:
            self.assertIsNone(forbidden.search(body))

    def test_every_variable_read_in_a_support_value_is_guarded(self):
        for path in (SUPPORT, GEN_VALUES):
            text = read(path)
            for name in top_level_names(text):
                if not name.startswith(("te_tax_base_", "te_tax_dr_eff_", "te_tax_bl_", "te_tax_dl_",
                                        "te_tax_committed", "te_tax_eligible", "te_tax_debate")):
                    continue
                body = block(text, name)
                for var in set(re.findall(r"var:(\w+)", body)):
                    with self.subTest(name=name, var=var):
                        self.assertIn(f"has_variable = {var}", body)


class RecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = read(GEN_BILL)
        cls.store = block(read(GEN_EFFECTS), "te_tax_gen_store_a")

    def test_the_bill_is_written_in_full(self):
        # Every bill field the store reads is written by the copy from the draft.
        read_by_store = set(re.findall(r"var:te_tax_bl_(\w+)", self.store))
        copy = block(self.generated, "te_tax_gen_bill_from_draft")
        written_by_copy = {name[len("te_tax_bl_"):] for name in written([copy]) if name.startswith("te_tax_bl_")}
        self.assertTrue(read_by_store)
        self.assertEqual(read_by_store - written_by_copy, set())
        self.assertIn("te_tax_bl_relief_states", self.store)
        self.assertIn("clear_variable_list = te_tax_bl_relief_states", copy)
        for key in KEYS:
            self.assertIn(f"set_variable = {{ name = te_tax_bl_xver_{key} value = var:te_tax_xver_{key} }}", copy)
        self.assertIn("set_variable = { name = te_tax_bl_xver_goods value = var:te_tax_xver_goods }", copy)
        self.assertIn("set_variable = { name = te_tax_bl_xver_relief value = var:te_tax_xver_relief }", copy)

    def test_the_draft_holds_every_field_the_copy_reads(self):
        copy = block(self.generated, "te_tax_gen_bill_from_draft")
        read_from_draft = set(re.findall(r"var:(te_tax_dr_\w+)", copy))
        init = written([block(self.generated, "te_tax_gen_draft_init")]) | {"te_tax_dr_due"}
        prefill = written([block(self.generated, "te_tax_gen_draft_from_bill")])
        self.assertEqual(read_from_draft - init, set())
        self.assertEqual(read_from_draft - prefill, set())

    def test_clearing_removes_exactly_the_payload(self):
        bill_payload = written([block(self.generated, "te_tax_gen_bill_from_draft")]) | {
            "te_tax_bl_rev", "te_tax_bl_day", "te_tax_bl_minor"}
        removed = set(re.findall(r"remove_variable = (\w+)", block(self.generated, "te_tax_gen_bill_clear")))
        removed.add("te_tax_bl_relief_states")
        self.assertEqual(removed, bill_payload)
        draft_payload = written([block(self.generated, "te_tax_gen_draft_init")]) | {"te_tax_dr_due"}
        clear = block(self.generated, "te_tax_gen_draft_clear")
        # Variables are removed, the draft's two lists (Task 11) cleared.
        removed = set(re.findall(r"remove_variable = (\w+)", clear)) | set(
            re.findall(r"clear_variable_list = (\w+)", clear))
        self.assertEqual(removed, draft_payload)

    def test_only_the_generated_bill_file_removes_variables(self):
        for path in (BILL, TRIGGERS, SUPPORT):
            with self.subTest(path=path):
                self.assertNotIn("remove_variable", read(path))
        country, state = schema_tokens()
        removed = set(re.findall(r"remove_variable = ([\w$]+)", self.generated))
        self.assertFalse({name for name in removed if "$" in name})
        self.assertFalse(removed & (set(country) | set(state)))

    def test_draft_and_bill_tokens_are_schema_tokens(self):
        country, _ = schema_tokens()
        self.assertEqual(country.get("te_tax_dr_on"), 0)
        self.assertEqual(country.get("te_tax_bl_on"), 0)

    def test_commitments_reset_for_every_group(self):
        body = block(self.generated, "te_tax_gen_reset_commitments")
        for ig in IGS:
            self.assertIn(f"set_variable = {{ name = te_tax_com_{ig} value = 0 }}", body)
            self.assertIn(f"set_variable = {{ name = te_tax_com_{ig}_rev value = -1 }}", body)


class RefreshWiringTest(unittest.TestCase):
    def test_processor_refreshes_support_monthly_while_a_bill_is_open(self):
        body = block(read(SCHEDULE), "te_tax_process_month")
        refreshes = [nested for _, nested in branches(body) if "te_tax_refresh_support = yes" in direct(nested)]
        self.assertEqual(len(refreshes), 1)
        self.assertEqual(limit_of(refreshes[0]).strip(), "te_tax_bill_active = yes")
        self.assertGreater(body.find("te_tax_refresh_support = yes"), body.find("te_tax_recompute_next_month = yes"))

    def test_refresh_is_gated_and_never_reachable_from_a_gui(self):
        body = block(read(BILL), "te_tax_refresh_support")
        self.assertIn("te_tax_code_on = yes", body)
        self.assertIn("te_tax_bill_active = yes", body)
        self.assertIn("te_tax_gen_refresh_support = yes", body)
        for directory, pattern in (("gui", "*.gui"), ("common/scripted_guis", "*.txt")):
            for path in sorted((ROOT / directory).rglob(pattern)):
                with self.subTest(path=path.name):
                    self.assertNotIn("te_tax_refresh_support", path.read_text(encoding="utf-8-sig", errors="replace"))
        callers = [name for name, text in all_effects().items() if "te_tax_refresh_support = yes" in text]
        self.assertEqual(sorted(callers), ["te_tax_bill_start_debate", "te_tax_cmd_reschedule", "te_tax_process_month"])


class LocTest(unittest.TestCase):
    def test_every_tooltip_key_is_localised(self):
        entries = loc_entries()
        keys = set()
        for path in (BILL, GEN_BILL, TRIGGERS):
            text = read(path)
            keys |= set(re.findall(r"custom_tooltip = (te_tax_tt_\w+)", text))
            keys |= set(re.findall(r"text = (te_tax_tt_\w+)", text))
        self.assertTrue(keys)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.assertTrue(entries.get(key))
                self.assertNotIn("[b]", entries[key])


class FilesTest(unittest.TestCase):
    def test_bom_lf_tabs_and_formatter_parity(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import format_paradox_tabs
        finally:
            sys.path.pop(0)
        for path in (BILL, GEN_BILL, SUPPORT, TRIGGERS, GEN_TRIGGERS, GEN_VALUES):
            raw = (ROOT / path).read_bytes()
            text = raw.decode("utf-8-sig")
            with self.subTest(path=path):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertNotIn(b"\r", raw)
                self.assertNotRegex(text, r"(?m)^ +\S")
                self.assertEqual(format_paradox_tabs.format_text(text), text)
        for path in (GEN_BILL, GEN_VALUES):
            self.assertIn(gen.HEADER, read(path, strip_comments=False).splitlines()[:3])

    def test_generated_files_are_registered_everywhere(self):
        for path in (GEN_BILL, GEN_VALUES):
            with self.subTest(path=path):
                self.assertIn(path, gen.OUTPUTS)
                self.assertIn(path, read(AUTO_GENERATED_DOC, strip_comments=False))
                self.assertIn(f'"{path}"', read(NIGHTLY_SELECT, strip_comments=False))

    def test_no_root_and_no_parameters_in_debug_lines(self):
        for path in (BILL, GEN_BILL, TRIGGERS, SUPPORT):
            text = read(path)
            with self.subTest(path=path):
                self.assertNotRegex(text, r"\bROOT\b|\broot\b")
                for line in re.findall(r'debug_log = "([^"]*)"', text):
                    self.assertNotIn("$", line)

    def test_schema_doc_describes_the_lifecycle(self):
        doc = read(SCHEMA_DOC, strip_comments=False)
        self.assertIn("\n## Draft, bill and passage\n", doc)
        section = doc.split("\n## Draft, bill and passage\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_cmd_pass", "te_tax_can_pass", "te_tax_refresh_support", "game_date",
                       "ig_counts_as_marginal", "Supersession at approval", "te_tax_committed_share",
                       "te_tax_bl_relief_states"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)
        for ig, row in EXPOSURE.items():
            cells = " | ".join(row[key] for key in KEYS)
            self.assertIn(f"| {ig} | {cells} |", section)


if __name__ == "__main__":
    unittest.main()
