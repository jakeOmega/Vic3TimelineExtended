"""The legislated tax code's action handlers and the panels that call them (plan Task 8).

Structural checks on the committed script and GUI (no game install needed):

* every action scripted GUI is one of the Task 6 commands behind its own
  trigger: `is_valid` is `te_tax_can_<c>` and `effect` is `te_tax_cmd_<c>`
  with the same parameters, so a button's tooltip and its click cannot
  disagree; an op-coded handler branches on `scope:op` in both, with the same
  op table, every branch guarded by `exists = scope:op`, and fails closed
  (`trigger_else = { always = no }`, no default effect);
* every command and every value of its parameters is reachable from a handler;
* the per-instrument step handlers and the per-good toggles are generated and
  cover INSTRUMENTS and the consumption catalog exactly;
* every button that runs a handler shows `IsValidTooltip`, a break and
  `ExecuteTooltip` for the op its click runs, and is enabled by that op;
* the passage condition rows test exactly the conditions te_tax_can_pass does;
* the interest-group card values read the owner's snapshot through an
  `is_interest_group_type` chain, guarded, without iterating or writing;
* the draft's minor/major class and "reverts to" preview follow the bill's
  and the scheduler's rules.

Run: python3 -m unittest test_tax_code_sguis -v
"""

import re
import unittest
from pathlib import Path

from test_tax_code_layout import gui, mod_block, raw, type_body, uncomment, value_bodies
from test_tax_code_state import KEYS, block, close, gen, read, top_level_names

ROOT = Path(__file__).resolve().parent

TAX_SGUIS = "common/scripted_guis/te_tax_sguis.txt"
GEN_SGUIS = "common/scripted_guis/te_tax_generated_sguis.txt"
GEN_ROWS = "gui/journal_entry_widgets/te_tax_generated_rows.gui"
WORKBENCH = "gui/journal_entry_widgets/te_tax_workbench_widget.gui"
REVIEW = "gui/journal_entry_widgets/te_tax_review_widget.gui"
POLITICS = "gui/journal_entry_widgets/te_tax_politics_widget.gui"
OVERVIEW = "gui/journal_entry_widgets/te_tax_overview_widget.gui"
LAYOUT = "gui/journal_entry_widgets/te_tax_layout_widget.gui"
BUDGET = "gui/budget_panel.gui"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
GEN_VALUES = "common/script_values/te_tax_generated_values.txt"
GEN_SUPPORT = "common/script_values/te_tax_generated_support_values.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
TAX_GUI = (OVERVIEW, LAYOUT, WORKBENCH, REVIEW, POLITICS, GEN_ROWS)

IGS = ("armed_forces", "devout", "industrialists", "intelligentsia",
       "landowners", "petty_bourgeoisie", "rural_folk", "trade_unions")
# "offer_arg": the card's revenue line picks the instrument an offer cuts (Task 14).
IG_VALUES = ("stance", "score", "mat", "ideo", "fisc", "gov", "trust", "prom", "offer", "offer_arg")
WORLD = re.compile(r"\b(every_\w+|any_\w+|random_\w+|ordered_\w+)\b")
WRITES = re.compile(r"\b(set_variable|change_variable|remove_variable|clamp_variable|save_scope_as|"
                    r"save_temporary_scope_as|add_modifier|remove_modifier|trigger_event|set_local_variable)\b")

# Handlers with no saved scope: te_tax_cmd_<c>_sgui runs te_tax_cmd_<c> when te_tax_can_<c> holds.
SIMPLE = ("draft_new", "draft_discard", "introduce", "revise", "withdraw", "pass", "reschedule",
          "draft_relief_choose", "force_through")
# Handlers whose saved scope is an object, not an op (Task 11): sgui -> (command, saved scope).
SCOPED = {"te_tax_relief_state_sgui": ("draft_relief_state", "te_tax_st")}
RELIEF_KEYS = ("agrel", "regrel")
# Instrument codes as the history ring stores them (te_tax_h<n>_inst): 1 wage ... 5 cons.
INST = {idx: key for idx, key in enumerate(KEYS, start=1)}


def op_tables():
    """{sgui: {op: (command, params)}}: every op-coded handler's contract."""
    tables = {
        "te_tax_due_sgui": {0: ("draft_due", "DIR = 0"), 1: ("draft_due", "DIR = 1")},
        "te_tax_cmd_draft_rebase_sgui": {**{idx: ("draft_rebase", f"KEY = {key}") for idx, key in INST.items()},
                                         6: ("draft_rebase", "KEY = goods"), 7: ("draft_rebase", "KEY = relief")},
        "te_tax_cmd_package_reschedule_sgui": {1: ("package_reschedule", "SLOT = a"),
                                               2: ("package_reschedule", "SLOT = b")},
        "te_tax_cmd_package_release_sgui": {1: ("package_release", "SLOT = a"),
                                            2: ("package_release", "SLOT = b")},
        # Policy obligations (Task 12): op = the obligation slot.
        "te_tax_cmd_obl_renegotiate_sgui": {n: ("obl_renegotiate", f"N = {n}") for n in (1, 2, 3, 4)},
    }
    for key in KEYS:
        ops = {op: ("draft_step", f"KEY = {key} DIR = {op}") for op in range(5)}
        ops[10] = ("draft_sunset", f"KEY = {key} DIR = 0")
        ops[11] = ("draft_sunset", f"KEY = {key} DIR = 1")
        tables[f"te_tax_step_{key}_sgui"] = ops
    for key in RELIEF_KEYS:
        tables[f"te_tax_relief_{key}_sgui"] = {op: ("draft_relief", f"KEY = {key} DIR = {op}") for op in range(5)}
    return tables


def plain_handlers():
    """{sgui: (command, params)} for the handlers with no saved scope."""
    handlers = {f"te_tax_cmd_{name}_sgui": (name, "") for name in SIMPLE}
    handlers.update({f"te_tax_good_{good}_sgui": ("draft_good", f"GOOD = {good}")
                     for good in gen.consumption_catalog()})
    return handlers


def sgui_text():
    return read(TAX_SGUIS) + "\n" + read(GEN_SGUIS)


def call(command, params, kind):
    """`te_tax_can_<c> = yes` or `te_tax_cmd_<c> = { P = v }`, whitespace-normalised."""
    args = f"{{ {params} }}" if params else "yes"
    return f"te_tax_{kind}_{command} = {args}"


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def sub_block(body, field):
    """The `{ ... }` body of `field = {` inside `body` (first match, at any depth)."""
    match = re.search(rf"\b{field} = \{{", body)
    assert match, f"no {field}"
    return body[match.end():close(body, match.end() - 1)]


def branches(body, opener):
    """[(op, rest)] for each `<opener> = { limit = { exists = scope:op scope:op = N } rest }`."""
    found = []
    for match in re.finditer(rf"\b{opener} = \{{", body):
        inner = body[match.end():close(body, match.end() - 1)]
        limit = re.match(r"\s*limit = \{ exists = scope:op scope:op = (\d+) \}(.*)$", inner, re.S)
        found.append((int(limit.group(1)), norm(limit.group(2))) if limit else (None, norm(inner)))
    return found


class HandlerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = sgui_text()
        cls.names = top_level_names(cls.text)
        cls.actions = [name for name in cls.names if not name.startswith("te_tax_show_")]

    def test_the_handler_set(self):
        # Task 13: the offer handler dispatches on its group's type (test_tax_code_offers.py).
        self.assertEqual(sorted(self.actions), sorted(set(op_tables()) | set(plain_handlers()) | set(SCOPED)
                                                      | {"te_tax_cmd_accept_offer_sgui"}))
        self.assertEqual(len(self.names), len(set(self.names)), "a handler is defined twice")

    def test_every_handler_is_for_the_player_only_and_scope_free_when_shown(self):
        for name in self.actions:
            body = block(self.text, name)
            with self.subTest(name=name):
                self.assertIn("scope = country", body)
                self.assertRegex(body, r"ai_is_valid = \{ always = no \}")
                self.assertRegex(body, r"is_shown = \{ te_tax_code_in_force = yes \}")
                self.assertIsNone(WORLD.search(sub_block(body, "is_valid")))

    def test_plain_handlers_call_their_command_behind_its_trigger(self):
        for name, (command, params) in plain_handlers().items():
            body = block(self.text, name)
            with self.subTest(name=name):
                self.assertNotIn("saved_scopes", body)
                self.assertEqual(norm(sub_block(body, "is_valid")), call(command, params, "can"))
                self.assertEqual(norm(sub_block(body, "effect")), call(command, params, "cmd"))

    def test_scoped_handlers_call_their_command_behind_its_trigger(self):
        """The saved scope is the row's object (a state); the trigger fails closed without it."""
        for name, (command, scope) in SCOPED.items():
            body = block(self.text, name)
            with self.subTest(name=name):
                self.assertRegex(body, rf"saved_scopes = \{{ {scope} \}}")
                self.assertEqual(norm(sub_block(body, "is_valid")), call(command, "", "can"))
                self.assertEqual(norm(sub_block(body, "effect")), call(command, "", "cmd"))
                trigger = norm(block(read(TRIGGERS), f"te_tax_can_{command}"))
                self.assertIn(f"custom_tooltip = {{ text = te_tax_tt_relief_state_given exists = scope:{scope} }}",
                              trigger)

    def test_op_coded_handlers_fail_closed_with_one_op_table(self):
        for name, table in op_tables().items():
            body = block(self.text, name)
            valid, effect = sub_block(body, "is_valid"), sub_block(body, "effect")
            with self.subTest(name=name):
                self.assertRegex(body, r"saved_scopes = \{ op \}")
                tests = branches(valid, "trigger_if") + branches(valid, "trigger_else_if")
                self.assertEqual({op: rest for op, rest in tests},
                                 {op: call(c, p, "can") for op, (c, p) in table.items()})
                self.assertEqual(len(tests), len(table))
                self.assertRegex(valid, r"trigger_else = \{ always = no \}\s*$")
                runs = branches(effect, "if") + branches(effect, "else_if")
                self.assertEqual({op: rest for op, rest in runs},
                                 {op: call(c, p, "cmd") for op, (c, p) in table.items()})
                self.assertEqual(len(runs), len(table))
                self.assertNotRegex(effect, r"\belse = \{", "an unknown op must do nothing")

    def test_every_command_and_parameter_value_has_a_handler(self):
        reached = set()
        for table in op_tables().values():
            reached |= {call(c, p, "cmd") for c, p in table.values()}
        reached |= {call(c, p, "cmd") for c, p in plain_handlers().values()}
        reached |= {call(c, "", "cmd") for c, _ in SCOPED.values()}
        wanted = {call(name, "", "cmd") for name in SIMPLE}
        wanted |= {call("draft_step", f"KEY = {k} DIR = {d}", "cmd") for k in KEYS for d in range(5)}
        wanted |= {call("draft_sunset", f"KEY = {k} DIR = {d}", "cmd") for k in KEYS for d in (0, 1)}
        wanted |= {call("draft_due", f"DIR = {d}", "cmd") for d in (0, 1)}
        wanted |= {call("draft_good", f"GOOD = {g}", "cmd") for g in gen.consumption_catalog()}
        wanted |= {call("draft_rebase", f"KEY = {k}", "cmd") for k in KEYS + ("goods", "relief")}
        wanted |= {call("draft_relief", f"KEY = {k} DIR = {d}", "cmd") for k in RELIEF_KEYS for d in range(5)}
        wanted |= {call("draft_relief_state", "", "cmd")}
        wanted |= {call(c, f"SLOT = {s}", "cmd") for c in ("package_reschedule", "package_release")
                   for s in ("a", "b")}
        wanted |= {call("obl_renegotiate", f"N = {n}", "cmd") for n in (1, 2, 3, 4)}
        self.assertEqual(reached, wanted)

    def test_generated_handlers_cover_instruments_and_catalog(self):
        generated = set(top_level_names(read(GEN_SGUIS)))
        self.assertEqual(generated, {f"te_tax_step_{key}_sgui" for key in KEYS}
                         | {f"te_tax_good_{good}_sgui" for good in gen.consumption_catalog()}
                         | {f"te_tax_relief_{key}_sgui" for key in RELIEF_KEYS})
        self.assertEqual(len(gen.consumption_catalog()), 39)
        self.assertIn(gen.HEADER, raw(GEN_SGUIS).splitlines()[:3])

    def test_display_gates_stay_inert(self):
        for name in self.names:
            if not name.startswith("te_tax_show_"):
                continue
            body = block(self.text, name)
            with self.subTest(name=name):
                self.assertNotIn("saved_scopes", body)
                self.assertRegex(body, r"(?m)^\tis_valid = \{ always = no \}")
                self.assertRegex(body, r"effect = \{ \}")


class PassageGateTest(unittest.TestCase):
    """Each condition row of the passage panel tests what te_tax_can_pass tests."""

    GATES = {
        "te_tax_show_pass_support_sgui": "te_tax_committed_share > te_tax_passage_share",
        "te_tax_show_pass_legitimacy_sgui": "legitimacy >= te_tax_passage_legitimacy",
        "te_tax_show_pass_debate_sgui": "te_tax_debate_days_left <= 0",
        "te_tax_show_pass_due_sgui": "var:te_tax_bl_due > te_history_month_index",
        "te_tax_show_pass_slot_sgui": "OR = { var:te_tax_pa_on = 0 var:te_tax_pb_on = 0 }",
        "te_tax_show_pass_current_sgui": "te_tax_gen_bill_current = yes",
    }

    def test_each_gate_is_a_line_of_can_pass(self):
        sguis = read(TAX_SGUIS)
        can_pass = norm(block(read(TRIGGERS), "te_tax_can_pass"))
        for name, condition in self.GATES.items():
            shown = norm(sub_block(block(sguis, name), "is_shown"))
            with self.subTest(name=name):
                self.assertTrue(shown.startswith("te_tax_code_in_force = yes te_tax_bill_active = yes"), shown)
                self.assertTrue(shown.endswith(condition), shown)
                self.assertIn(condition, can_pass)

    def test_each_gate_has_a_row(self):
        politics = gui(POLITICS)
        for name in self.GATES:
            with self.subTest(name=name):
                self.assertIn(f"GetScriptedGui('{name}')", politics)


# A button's tooltip: the checklist for the op its click runs, a break, what it does.
TOOLTIP = re.compile(
    r"tooltip = \"\[Concatenate\( (?P<a>[\w.()' ]*?)\.IsValidTooltip\( (?P<args>.+?) \), "
    r"Concatenate\( Localize\( 'te_tt_break' \), (?P<b>[\w.()' ]*?)\.ExecuteTooltip\( (?P<args2>.+?) \) \) \)\]\"")
ENABLED = re.compile(r"enabled = \"\[(?P<a>[\w.()' ]*?)\.IsValid\( (?P<args>.+?) \)\]\"")
CLICK = re.compile(r"(?:onclick|ondefault) = \"\[(?P<a>[\w.()' ]*?)\.Execute\( (?P<args>.+?) \)\]\"")
OP = re.compile(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)")


def handler_calls(text):
    """[(handler, method, args)] for every `GetScriptedGui('x').M( args )` and
    `ScriptedGui.M( args )` call, args with balanced parentheses."""
    found = []
    for match in re.finditer(r"(GetScriptedGui\('\w+'\)|\bScriptedGui)\.(\w+)\(", text):
        depth, j = 1, match.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        found.append((match.group(1), match.group(2), text[match.end():j - 1]))
    return found


def own_lines(body):
    """`body` with its child blocks removed, except click_modifiers (part of the button)."""
    out, i = [], 0
    for match in re.finditer(r"\b(\w+) = \{", body):
        if match.start() < i:
            continue
        end = close(body, match.end() - 1)
        if match.group(1) == "click_modifiers":
            continue
        out.append(body[i:match.start()])
        i = end + 1
    out.append(body[i:])
    return "".join(out)


class ButtonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {path: gui(path) for path in TAX_GUI}
        regions = mod_block(raw(BUDGET))
        cls.texts[BUDGET] = uncomment(regions[2]) if len(regions) > 2 else ""
        cls.found = []
        for path, text in cls.texts.items():
            for match in re.finditer(r"\b(\w+) = \{", text):
                if match.group(1) in ("click_modifiers", "blockoverride"):
                    continue
                body = text[match.end():close(text, match.end() - 1)]
                own = own_lines(body)
                if ".Execute(" in own:
                    cls.found.append((path, match.group(1), body, own))

    def test_there_are_buttons(self):
        self.assertGreaterEqual(len(self.found), 20)

    def test_every_button_explains_the_op_it_runs(self):
        for path, widget, body, own in self.found:
            clicks = CLICK.findall(body)
            with self.subTest(path=path, widget=widget, click=clicks[:1]):
                self.assertTrue(clicks, "no default click")
                handler, args = clicks[0]
                enabled = ENABLED.search(own)
                self.assertIsNotNone(enabled, "the button is not enabled by its handler")
                self.assertEqual((enabled.group("a"), enabled.group("args")), (handler, args))
                tooltip = TOOLTIP.search(own)
                self.assertIsNotNone(tooltip, "tooltip is not IsValidTooltip + te_tt_break + ExecuteTooltip")
                self.assertEqual((tooltip.group("a"), tooltip.group("args")), (handler, args))
                self.assertEqual((tooltip.group("b"), tooltip.group("args2")), (handler, args))

    def test_every_op_is_in_its_handlers_table(self):
        tables = op_tables()
        for path, text in self.texts.items():
            for handler, method, args in handler_calls(text):
                if handler == "ScriptedGui":
                    continue  # a row type's call; its instance sets the handler (below)
                name = re.match(r"GetScriptedGui\('(\w+)'\)", handler).group(1)
                ops = OP.findall(args)
                with self.subTest(path=path, name=name, method=method):
                    if name in tables:
                        self.assertEqual(len(ops), 1, "an op-coded handler needs exactly one op")
                        self.assertIn(int(ops[0]), tables[name])
                    else:
                        self.assertEqual(ops, [], "a plain handler takes no op")

    def test_rows_that_use_a_datacontext_handler_use_its_ops(self):
        """The instrument and expiry rows call `ScriptedGui.` on the step handler
        their instance sets as datacontext."""
        workbench = gui(WORKBENCH)
        step_ops = set(op_tables()["te_tax_step_wage_sgui"])
        for name in ("te_tax_instrument_row", "te_tax_sunset_row"):
            body = type_body(workbench, name)
            ops = {int(op) for op in OP.findall(body)}
            with self.subTest(type=name):
                self.assertTrue(ops)
                self.assertLessEqual(ops, step_ops)
                self.assertNotIn("GetScriptedGui(", body)
        self.assertEqual({int(op) for op in OP.findall(type_body(workbench, "te_tax_instrument_row"))},
                         {0, 1, 2, 3, 4})
        self.assertEqual({int(op) for op in OP.findall(type_body(workbench, "te_tax_sunset_row"))}, {10, 11})
        for key in KEYS:
            with self.subTest(key=key):
                self.assertEqual(workbench.count(f"datacontext = \"[GetScriptedGui('te_tax_step_{key}_sgui')]\""), 2)

    def test_shift_goes_to_the_limit_and_right_click_reverts(self):
        body = type_body(gui(WORKBENCH), "te_tax_instrument_row")
        for button, default, shift in (("button_icon_minus_action", 0, 2), ("button_icon_plus_action", 1, 3)):
            match = re.search(rf"\b{button} = \{{", body)
            inner = body[match.end():close(body, match.end() - 1)]
            modifiers = sub_block(inner, "click_modifiers")
            with self.subTest(button=button):
                self.assertEqual([int(op) for op in OP.findall(re.search(r"ondefault = \"[^\"]+\"", modifiers).group(0))],
                                 [default])
                self.assertEqual([int(op) for op in OP.findall(re.search(r"onshift = \"[^\"]+\"", modifiers).group(0))],
                                 [shift])
                self.assertEqual([int(op) for op in OP.findall(re.search(r"onrightclick = \"[^\"]+\"", inner).group(0))],
                                 [4])
                self.assertNotRegex(own_lines(inner), r"\bonclick =", "click_modifiers replaces onclick")


class GoodsRowsTest(unittest.TestCase):
    """The generated per-good rows: one toggle per catalog good, and one review line."""

    @classmethod
    def setUpClass(cls):
        cls.rows = gui(GEN_ROWS)

    def test_generated_and_registered(self):
        self.assertIn(gen.HEADER, raw(GEN_ROWS).splitlines()[:3])
        for path in (GEN_ROWS, GEN_SGUIS):
            with self.subTest(path=path):
                self.assertIn(path, gen.OUTPUTS)
                self.assertIn(path, raw("docs/auto_generated_files.md"))
                self.assertIn(f'"{path}"', raw("scripts/nightly_audit_select.py"))
        self.assertTrue(raw(GEN_ROWS).startswith("﻿") or (ROOT / GEN_ROWS).read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_each_good_has_its_toggle_and_its_review_line(self):
        workbench_rows = type_body(self.rows, "te_tax_wb_goods_rows")
        review_rows = type_body(self.rows, "te_tax_rv_goods_rows")
        catalog = gen.consumption_catalog()
        self.assertEqual(re.findall(r"te_tax_good_(\w+)_sgui", workbench_rows), list(catalog))
        for good in catalog:
            with self.subTest(good=good):
                self.assertIn(f"datacontext = \"[GetScriptedGui('te_tax_good_{good}_sgui')]\"", workbench_rows)
                self.assertIn(f'text = "{good}"', workbench_rows)
                self.assertIn(f"te_tax_view_dr_g_{good}_on", review_rows)
                self.assertIn(f"te_tax_view_dr_g_{good}'", review_rows)
        self.assertEqual(len(re.findall(r"\bte_tax_good_row = \{", workbench_rows)), len(catalog))
        self.assertEqual(len(re.findall(r"\bte_tax_review_good_line = \{", review_rows)), len(catalog))


class InterestGroupValueTest(unittest.TestCase):
    """The actor cards' numbers: interest-group scope, read from the owner's snapshot."""

    @classmethod
    def setUpClass(cls):
        cls.values = value_bodies()

    def test_each_value_covers_every_group_through_its_type(self):
        for value in IG_VALUES:
            body = self.values[f"te_tax_disp_ig_{value}"]
            with self.subTest(value=value):
                self.assertEqual(set(re.findall(r"is_interest_group_type = ig_(\w+)", body)), set(IGS))
                self.assertIsNone(WORLD.search(body))
                self.assertIsNone(WRITES.search(body))
                for var in set(re.findall(r"var:(\w+)", body)):
                    self.assertIn(f"has_variable = {var}", body, f"var:{var} unguarded")
                self.assertIn("owner = {", body)
                # a stale snapshot (bill closed) is never shown
                self.assertIn("var:te_tax_bl_on = 1", body)

    def test_reasons_read_their_snapshot_variable(self):
        for value in ("mat", "ideo", "fisc", "gov", "trust"):
            body = self.values[f"te_tax_disp_ig_{value}"]
            for ig in IGS:
                with self.subTest(value=value, ig=ig):
                    self.assertIn(f"var:te_tax_sr_{ig}_{value}", body)
        score = self.values["te_tax_disp_ig_score"]
        for ig in IGS:
            self.assertIn(f"var:te_tax_sup_{ig}", score)

    def test_stance_codes(self):
        body = self.values["te_tax_disp_ig_stance"]
        # 1 committed, 2 persuadable, 3 opposed, 4 red line, 5 marginal (not counted)
        self.assertEqual(set(re.findall(r"value = (\d)\b", body)), {"0", "1", "2", "3", "4", "5"})
        self.assertIn("ig_counts_as_marginal = yes", body)
        for ig in IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"var:te_tax_com_{ig}_rev = var:te_tax_bl_rev", body)

    def test_cards_read_them_only_through_the_group(self):
        from test_tax_code_layout import loc
        politics = gui(POLITICS)
        self.assertIn('datamodel = "[AccessPlayer.AccessAllInterestGroups]"', politics)
        text = politics + "\n" + "\n".join(loc().values())
        reads = re.findall(r"(\w+)\.MakeScope\.ScriptValue\('(te_tax_disp_ig_\w+)'\)", text)
        self.assertTrue(reads)
        self.assertEqual({scope for scope, _ in reads}, {"InterestGroup"})
        self.assertEqual({name for _, name in reads}, {f"te_tax_disp_ig_{v}" for v in IG_VALUES})


class DraftClassTest(unittest.TestCase):
    """The workbench's minor/major class is the bill's rule applied to the draft."""

    def test_draft_is_minor_mirrors_bill_is_minor(self):
        triggers = read(TRIGGERS)
        bill = norm(block(triggers, "te_tax_bill_is_minor"))
        draft = norm(block(triggers, "te_tax_draft_is_minor"))
        self.assertEqual(draft, bill.replace("te_tax_bl_", "te_tax_dr_").replace("_bill_", "_draft_"))

    def test_draft_small_steps_mirror_the_bills(self):
        triggers = read(GEN_TRIGGERS)
        bill = norm(block(triggers, "te_tax_gen_bill_small_steps"))
        draft = norm(block(triggers, "te_tax_gen_draft_small_steps"))
        self.assertEqual(draft, bill.replace("te_tax_bl_", "te_tax_dr_"))
        support = read(GEN_SUPPORT)
        for key in KEYS:
            bill_step = norm(block(support, f"te_tax_bl_dstep_{key}"))
            with self.subTest(key=key):
                self.assertEqual(norm(block(support, f"te_tax_dr_dstep_{key}")),
                                 bill_step.replace("te_tax_bl_", "te_tax_dr_").replace("te_tax_base_bl_", "te_tax_base_dr_"))
        self.assertEqual(norm(block(support, "te_tax_dr_provisions")),
                         norm(block(support, "te_tax_bl_provisions")).replace("te_tax_bl_", "te_tax_dr_"))


class SuccessorPreviewTest(unittest.TestCase):
    """The review's "then reverts to X" for the draft: the scheduler's rule 3 at
    the draft's due month (docs/systems/tax_code_schema.md, Storing a package)."""

    def test_preview_follows_the_store_rule(self):
        support = read(GEN_SUPPORT)
        for key in KEYS:
            body = norm(block(support, f"te_tax_succ_dr_{key}"))
            with self.subTest(key=key):
                # the enacted value, or its successor if any sunset is pending
                self.assertTrue(body.startswith(f"value = 0 if = {{ limit = {{ has_variable = te_tax_en_{key} }} "
                                                f"value = var:te_tax_en_{key} }}"), body)
                self.assertIn(f"var:te_tax_en_{key}_exp >= 0 var:te_tax_en_{key}_succ >= 0", body)
                self.assertNotIn(f"var:te_tax_en_{key}_exp <= var:te_tax_dr_due", body)
                # then each earlier awaiting package, in commencement order
                for slot in ("a", "b"):
                    self.assertIn(f"te_tax_slot_awaits_before = {{ SLOT = {slot} DUE = te_tax_dr_due }}", body)
                    self.assertIn(f"value = var:te_tax_p{slot}_{key}_succ", body)
                    self.assertNotIn(f"var:te_tax_p{slot}_{key}_exp <= var:te_tax_dr_due", body)
                self.assertIn("te_tax_slot_b_first = yes", body)
                self.assertIsNone(WRITES.search(body))
                self.assertIsNone(WORLD.search(body))

    def test_a_held_passed_bill_says_so_in_the_timeline(self):
        """A held package (state 2 conflict, 3 missed) will not commence as
        shown, so its Existing Law line carries the state."""
        from test_tax_code_layout import loc
        review, table = gui(REVIEW), loc()
        for slot in ("a", "b"):
            state = f"GetPlayer.MakeScope.ScriptValue('te_tax_view_p{slot}_state')"
            for key in KEYS:
                with self.subTest(slot=slot, key=key):
                    self.assertIn(f"SelectLocalization( EqualTo_CFixedPoint( {state}, '(CFixedPoint)2' ), "
                                  f"'te_tax_pk_{slot}_{key}_conflict', SelectLocalization( EqualTo_CFixedPoint( "
                                  f"{state}, '(CFixedPoint)3' ), 'te_tax_pk_{slot}_{key}_missed', ", review)
                    self.assertIn("held: conflict, will not commence; release it",
                                  table[f"te_tax_pk_{slot}_{key}_conflict"])
                    self.assertIn("held: missed", table[f"te_tax_pk_{slot}_{key}_missed"])

    def test_review_says_then_reverts_and_collections_wait(self):
        from test_tax_code_layout import loc
        table = loc()
        for key in KEYS:
            with self.subTest(key=key):
                self.assertIn(f"te_tax_view_dr_{key}_succ_rate", table[f"te_tax_rv_bill_sun_{key}"])
                self.assertIn("then reverts to", table[f"te_tax_rv_bill_sun_{key}"])
        self.assertEqual(table["te_tax_rv_unchanged"], "Present collections remain unchanged until commencement.")
        self.assertIn('text = "te_tax_rv_unchanged"', gui(REVIEW))


if __name__ == "__main__":
    unittest.main()
