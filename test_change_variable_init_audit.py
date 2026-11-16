"""Unit tests for change_variable_init_audit.

`change_variable` on a variable nothing has set does nothing and logs an error
each time it runs. The audit flags a change whose variable has no initialising
`set_variable` of that exact name anywhere: none at all, each one behind a
`has_variable` check or a `var:` read of the same variable (the UN cease-fire
order's debit, #1818), or only the flag form. It must not flag the mod's
ordinary shapes: a set at creation in another file, the guard-and-initialise
idiom, a set through a helper's parameter, a variable vanilla sets.

The cases added after the review of PR #1850 are marked "review": a name passed
on under the same parameter, a part-parameter set that used to clear every
name with its prefix, `exists = var:x`, an all-parameter change followed to
its callers, and the three loud false flags (a caller in a file that writes no
variable, a quoted name, a parameter not in upper case). `KnownLimitTests`
pins what the audit does not see, so the docs and the code say the same.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import audit_registry
import change_variable_init_audit
from change_variable_init_audit import audit, judge, render_report, vanilla_sets

ROOT = os.path.dirname(os.path.abspath(__file__))
EFFECTS = "common/scripted_effects/x_effects.txt"
# Scope links the tests use; the real catalog is docs/engine/event_targets_summary.txt.
LINKS = {"owner", "capital", "overlord"}


def _judge(*texts: str, vanilla=None, **named: str):
    files = {f"common/scripted_effects/f{i}_effects.txt": t for i, t in enumerate(texts)}
    files.update({path.replace("__", "/") + ".txt": t for path, t in named.items()})
    return judge(files, links=LINKS, vanilla=vanilla)


def _names(result):
    return [(f.file.rsplit("/", 1)[-1], f.line, f.kind, f.name) for f in result.flags]


class DetectionTests(unittest.TestCase):
    def test_reproduces_the_ceasefire_debit_bug(self):
        # un_order_effects.txt before the fix: the month adds one, and the only
        # set is the reset after a booking, behind has_variable.
        result = _judge(
            "un_ceasefire_order_month = {\n"
            "\tchange_variable = { name = un_cf_order_months add = -1 }\n"
            "\tchange_variable = { name = un_cf_debit_months add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { var:un_cf_debit_months >= un_cf_order_debit_batch_months }\n"
            "\t\tun_ceasefire_book_accrued_debit = yes\n"
            "\t}\n"
            "}\n"
            "un_ceasefire_book_accrued_debit = {\n"
            "\tif = {\n"
            "\t\tlimit = {\n"
            "\t\t\thas_variable = un_cf_debit_months\n"
            "\t\t\tvar:un_cf_debit_months > 0\n"
            "\t\t}\n"
            "\t\tset_variable = { name = un_cf_debit_months value = 0 }\n"
            "\t}\n"
            "}\n"
            "un_ceasefire_order_impose = {\n"
            "\tset_variable = { name = un_cf_order_months value = un_cf_order_length }\n"
            "}\n"
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 3, "var", "un_cf_debit_months")])
        flag = result.flags[0]
        self.assertEqual(flag.guarded_sets, [("common/scripted_effects/f0_effects.txt", 15)])
        self.assertIn("every `set_variable` of it sits behind a `has_variable` check", flag.message)
        self.assertIn("f0_effects.txt:15", flag.message)

    def test_a_change_with_no_set_at_all(self):
        result = _judge("e = {\n\tchange_variable = { name = x add = 1 }\n}\n")
        self.assertEqual(_names(result), [("f0_effects.txt", 2, "var", "x")])
        self.assertIn("no `set_variable` of it in the mod or in vanilla's `common/`", result.flags[0].message)

    def test_every_change_site_of_the_name_is_flagged(self):
        result = _judge(
            "e = {\n\tchange_variable = { name = x add = 1 }\n}\n",
            events__y="e.1 = {\n\timmediate = {\n\t\tchange_variable = {\n\t\t\tname = x\n\t\t\tadd = 2\n\t\t}\n\t}\n}\n",
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 2, "var", "x"), ("y.txt", 3, "var", "x")])

    def test_a_reset_behind_a_read_of_the_variable_does_not_initialise(self):
        # The batch shape: count up, reset at N. The limit's read is false
        # (and logs) while the variable is unset.
        result = _judge(
            "e = {\n"
            "\tchange_variable = { name = months add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { var:months >= 12 }\n"
            "\t\tset_variable = { name = months value = 0 }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 2, "var", "months")])

    def test_exists_and_a_read_on_the_right_guard_too(self):
        # review, item 3: the mod writes `exists = var:x` some 645 times.
        for limit in ("exists = var:x", "5 < var:x", "this.var:x >= 3", "var:x ?= 3",
                      "AND = { is_ai = yes exists = var:x }"):
            with self.subTest(limit=limit):
                result = _judge(
                    "e = {\n"
                    "\tchange_variable = { name = x add = 1 }\n"
                    "\tif = {\n"
                    f"\t\tlimit = {{ {limit} }}\n"
                    "\t\tset_variable = { name = x value = 0 }\n"
                    "\t}\n"
                    "}\n"
                )
                self.assertEqual(_names(result), [("f0_effects.txt", 2, "var", "x")])
        result = _judge(
            "e = {\n"
            "\tchange_global_variable = { name = g add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { exists = global_var:g }\n"
            "\t\tset_global_variable = { name = g value = 0 }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 2, "global_var", "g")])

    def test_the_flag_form_of_a_set_starts_no_counter(self):
        # review, item 6: `set_variable = x` stores a boolean. Whether
        # change_variable can count on one is unknown; nothing in the mod
        # relies on it, so it is not taken as a start.
        for flag_set in ("set_variable = x", "set_variable = { name = x }", "set_variable = { name = x days = 30 }"):
            with self.subTest(flag_set=flag_set):
                result = _judge(f"e = {{\n\t{flag_set}\n\tchange_variable = {{ name = x add = 1 }}\n}}\n")
                self.assertEqual(_names(result), [("f0_effects.txt", 3, "var", "x")])
                self.assertEqual(result.flags[0].flag_sets, [("common/scripted_effects/f0_effects.txt", 2)])
                self.assertIn("its only `set_variable` is the flag form", result.flags[0].message)
        # A value in a block counts, and so does a value beside a duration.
        for value_set in ("set_variable = { name = x value = { value = 1 add = 2 } }",
                          "set_variable = { name = x value = 0 days = 30 }"):
            with self.subTest(value_set=value_set):
                result = _judge(f"e = {{\n\t{value_set}\n\tchange_variable = {{ name = x add = 1 }}\n}}\n")
                self.assertEqual(_names(result), [])

    def test_a_quoted_name_is_read(self):
        # review, item 5: strings are blanked before the scan, so a quoted
        # name used to vanish: a quoted set flagged its plain change, and a
        # quoted change was never judged.
        quoted_set = _judge(
            'e = {\n\tset_variable = { name = "x" value = 0 }\n\tchange_variable = { name = x add = 1 }\n}\n')
        self.assertEqual(_names(quoted_set), [])
        quoted_change = _judge('e = {\n\tchange_variable = { name = "x" add = 1 }\n}\n')
        self.assertEqual(_names(quoted_change), [("f0_effects.txt", 2, "var", "x")])
        self.assertEqual(quoted_change.judged, 1)
        # A quoted string that is no variable name is left alone.
        other = _judge('e = {\n\tcustom_tooltip = "name = x"\n\tadd_modifier = { name = "a modifier" }\n}\n')
        self.assertEqual((other.flags, other.judged), ([], 0))

    def test_a_guard_under_AND_and_in_a_nested_if_still_guards(self):
        result = _judge(
            "e = {\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { AND = { has_variable = x is_ai = yes } }\n"
            "\t\tif = {\n"
            "\t\t\tlimit = { is_at_war = yes }\n"
            "\t\t\tset_variable = { name = x value = 0 }\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(result.flags), 1)

    def test_an_iterators_limit_guards_the_objects_it_visits(self):
        result = _judge(
            "e = {\n"
            "\tevery_country = {\n"
            "\t\tlimit = { has_variable = x }\n"
            "\t\tchange_variable = { name = x add = 1 }\n"
            "\t\tset_variable = { name = x value = 0 }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(result.flags), 1)

    def test_global_and_local_forms(self):
        result = _judge(
            "e = {\n"
            "\tchange_global_variable = { name = g add = 1 }\n"
            "\tchange_local_variable = { name = l add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { has_global_variable = g }\n"
            # A global has no scope: the guard holds behind a scope change.
            "\t\towner = { set_global_variable = { name = g value = 0 } }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 2, "global_var", "g"),
                                          ("f0_effects.txt", 3, "local_var", "l")])

    def test_the_three_kinds_do_not_initialise_one_another(self):
        result = _judge(
            "e = {\n"
            "\tset_global_variable = { name = x value = 0 }\n"
            "\tset_local_variable = { name = x value = 0 }\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "}\n"
        )
        self.assertEqual(_names(result), [("f0_effects.txt", 4, "var", "x")])


class NotFlaggedTests(unittest.TestCase):
    def assertClean(self, result):
        self.assertEqual(_names(result), [])

    def test_a_set_anywhere_in_the_mod_initialises(self):
        self.assertClean(_judge(
            "monthly = {\n\tchange_variable = { name = x add = 1 }\n}\n",
            events__start="s.1 = {\n\timmediate = {\n\t\tset_variable = { name = x value = 0 }\n\t}\n}\n",
        ))

    def test_the_guard_and_initialise_idiom(self):
        self.assertClean(_judge(
            "e = {\n"
            "\tif = {\n"
            "\t\tlimit = { NOT = { has_variable = x } }\n"
            "\t\tset_variable = { name = x value = 0 }\n"
            "\t}\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "}\n"
        ))

    def test_a_set_in_the_else_of_a_guard(self):
        self.assertClean(_judge(
            "e = {\n"
            "\tif = {\n"
            "\t\tlimit = { has_variable = x }\n"
            "\t\tchange_variable = { name = x add = 1 }\n"
            "\t}\n"
            "\telse = {\n"
            "\t\tset_variable = { name = x value = 1 }\n"
            "\t}\n"
            "}\n"
        ))

    def test_a_guard_under_OR_proves_nothing(self):
        self.assertClean(_judge(
            "e = {\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { OR = { has_variable = x is_ai = yes } }\n"
            "\t\tset_variable = { name = x value = 0 }\n"
            "\t}\n"
            "}\n"
        ))

    def test_a_guard_does_not_reach_another_object(self):
        # The limit tested our variable; the set is on our overlord.
        self.assertClean(_judge(
            "e = {\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { has_variable = x }\n"
            "\t\toverlord = { set_variable = { name = x value = 0 } }\n"
            "\t}\n"
            "}\n"
        ))

    def test_a_read_of_another_objects_variable_is_no_guard(self):
        self.assertClean(_judge(
            "e = {\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { scope:other.var:x > 0 }\n"
            "\t\tset_variable = { name = x value = 0 }\n"
            "\t}\n"
            "}\n"
        ))

    def test_a_variable_vanilla_sets(self):
        text = "e = {\n\tchange_variable = { name = great_reforms_var add = 1 }\n}\n"
        self.assertEqual(len(_judge(text).flags), 1)
        self.assertClean(_judge(text, vanilla={("var", "great_reforms_var")}))
        # Kind for kind: vanilla's global of that name would not do.
        self.assertEqual(len(_judge(text, vanilla={("global_var", "great_reforms_var")}).flags), 1)

    def test_comments_and_strings_are_ignored(self):
        self.assertClean(_judge(
            "e = {\n"
            "\t# change_variable = { name = x add = 1 }\n"
            "\tcustom_tooltip = \"change_variable = { name = y add = 1 }\"\n"
            "}\n"
        ))


class KnownLimitTests(unittest.TestCase):
    """What the audit does not see (review, items 3 and 6), pinned so that the
    module's docstring, the registry note and the code agree. Each of these is
    a re-set that can only run with the variable set, and each counts as a
    start: a guard is read only from a `limit` in the set's own body."""

    CHANGE = "\tchange_variable = { name = x add = 1 }\n"

    def assertNotSeen(self, *texts, **named):
        self.assertEqual(_names(_judge(*texts, **named)), [])

    def test_a_guard_held_by_the_helpers_caller(self):
        self.assertNotSeen(
            "e = {\n" + self.CHANGE + "\tif = {\n\t\tlimit = { has_variable = x }\n\t\treset_x = yes\n\t}\n}\n"
            "reset_x = {\n\tset_variable = { name = x value = 0 }\n}\n")

    def test_a_guard_inside_a_scripted_trigger(self):
        self.assertNotSeen(
            "e = {\n" + self.CHANGE + "\tif = {\n\t\tlimit = { x_is_set = yes }\n"
            "\t\tset_variable = { name = x value = 0 }\n\t}\n}\n")

    def test_an_events_trigger_and_a_random_list_entrys(self):
        self.assertNotSeen(
            "e = {\n" + self.CHANGE + "}\n",
            events__a="a.1 = {\n\ttrigger = { has_variable = x }\n\timmediate = {\n"
                      "\t\tset_variable = { name = x value = 0 }\n\t}\n}\n")
        self.assertNotSeen(
            "e = {\n" + self.CHANGE + "\trandom_list = {\n\t\t10 = {\n\t\t\ttrigger = { has_variable = x }\n"
            "\t\t\tset_variable = { name = x value = 0 }\n\t\t}\n\t}\n}\n")

    def test_the_else_of_a_negated_guard_and_a_saved_scope(self):
        self.assertNotSeen(
            "e = {\n" + self.CHANGE + "\tif = {\n\t\tlimit = { NOT = { has_variable = x } }\n\t\tadd_treasury = 1\n\t}\n"
            "\telse = {\n\t\tset_variable = { name = x value = 0 }\n\t}\n}\n")
        self.assertNotSeen(
            "e = {\n\tsave_scope_as = me\n" + self.CHANGE + "\tif = {\n\t\tlimit = { has_variable = x }\n"
            "\t\tscope:me = { set_variable = { name = x value = 0 } }\n\t}\n}\n")

    def test_what_a_set_stores_and_on_which_object(self):
        self.assertNotSeen("e = {\n\tset_variable = { name = x value = scope:foo }\n" + self.CHANGE + "}\n")
        self.assertNotSeen(
            "e = {\n\tset_variable = { name = x value = 0 }\n\tevery_scope_state = {\n\t" + self.CHANGE + "\t}\n}\n")

    def test_a_helper_called_through_a_parameter_name_is_not_followed(self):
        # The one known shape that is flagged though it is sound: the call's
        # own name is a parameter, so the name the helper sets is not credited.
        result = _judge(
            "sr_grain_seed = {\n\tset_variable = { name = sr_$K$_n value = 0 }\n}\n",
            "seed = {\n\tsr_$KIND$_seed = { K = grain }\n}\n",
            "e = {\n\tseed = { KIND = grain }\n\tchange_variable = { name = sr_grain_n add = 1 }\n}\n",
        )
        self.assertEqual(_names(result), [("f2_effects.txt", 3, "var", "sr_grain_n")])

    def test_clamp_and_round_are_not_read(self):
        result = _judge("e = {\n\tclamp_variable = { name = x min = 0 max = 5 }\n"
                        "\tround_variable = { name = x nearest = 1 }\n}\n")
        self.assertEqual((result.flags, result.judged, result.unjudged), ([], 0, 0))


class HelperParameterTests(unittest.TestCase):
    HELPER = "te_set_sqrt = {\n\tset_variable = { name = $OUT$ value = $IN$ }\n}\n"

    def test_a_helper_sets_the_name_its_caller_passes(self):
        # decol_iw_value_arms_offer: te_set_sqrt = { … OUT = decol_iw_offer_with }.
        result = _judge(
            self.HELPER,
            "offer = {\n"
            "\tte_set_sqrt = { IN = var:sum OUT = decol_iw_offer_with }\n"
            "\tchange_variable = { name = decol_iw_offer_with multiply = 2 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [])

    def test_only_the_name_passed_is_initialised(self):
        result = _judge(
            self.HELPER,
            "offer = {\n"
            "\tte_set_sqrt = { IN = var:sum OUT = other }\n"
            "\tchange_variable = { name = mine multiply = 2 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 3, "var", "mine")])

    def test_through_a_helper_that_passes_the_name_on(self):
        result = _judge(
            self.HELPER,
            "wrap = {\n\tte_set_sqrt = { IN = $X$ OUT = $TO$_root }\n}\n",
            "use = {\n"
            "\twrap = { X = 4 TO = arms }\n"
            "\tchange_variable = { name = arms_root add = 1 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [])

    def test_a_call_in_a_file_that_writes_no_variable(self):
        # The caller's file has no set_variable or change_variable of its own,
        # so it is parsed only because it names the variable in question.
        result = _judge(
            self.HELPER,
            "e = {\n\tchange_variable = { name = far add = 1 }\n}\n",
            events__caller="c.1 = {\n\timmediate = {\n\t\tte_set_sqrt = { IN = 9 OUT = far }\n\t}\n}\n",
        )
        self.assertEqual(_names(result), [])

    def test_a_call_behind_a_guard_of_the_name_it_passes(self):
        result = _judge(
            self.HELPER,
            "e = {\n"
            "\tchange_variable = { name = x add = 1 }\n"
            "\tif = {\n"
            "\t\tlimit = { has_variable = x }\n"
            "\t\tte_set_sqrt = { IN = 9 OUT = x }\n"
            "\t}\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 2, "var", "x")])
        self.assertEqual(result.flags[0].guarded_sets, [("common/scripted_effects/f1_effects.txt", 5)])

    def test_a_part_parameter_set_clears_only_the_names_its_callers_pass(self):
        # review, item 2: as a pattern, `sr_$KEY$_stock` used to clear every
        # `sr_…_stock`, and `te_dg_m$S$` every variable starting `te_dg_m`.
        store = "store = {\n\tset_variable = { name = sr_$KEY$_stock value = 0 }\n}\n"
        draw = ("draw = {\n"
                "\tchange_variable = { name = sr_grain_stock subtract = 1 }\n"
                "\tchange_variable = { name = sr_steel_stock subtract = 1 }\n"
                "}\n")
        self.assertEqual(_names(_judge(store, draw)),
                         [("f1_effects.txt", 2, "var", "sr_grain_stock"), ("f1_effects.txt", 3, "var", "sr_steel_stock")])
        seeded = _judge(store, draw, "seed = {\n\tstore = { KEY = grain }\n}\n")
        self.assertEqual(_names(seeded), [("f1_effects.txt", 3, "var", "sr_steel_stock")])

    def test_a_pattern_set_does_not_swallow_an_unrelated_name(self):
        # review, item 2: un_ledger_$PILLAR$ beside the counter un_ledger_seq.
        result = _judge(
            "book = {\n\tset_global_variable = { name = un_ledger_$PILLAR$ value = 0 }\n}\n",
            "log = {\n"
            "\tbook = { PILLAR = order }\n"
            "\tchange_global_variable = { name = un_ledger_order add = 1 }\n"
            "\tchange_global_variable = { name = un_ledger_seq add = 1 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 4, "global_var", "un_ledger_seq")])

    def test_an_unresolved_parameter_change_is_matched_as_a_pattern(self):
        # No caller passes GOOD, so the change's own name is all there is to
        # go on: a set written with the same parameters clears it.
        result = _judge(
            "store = {\n\tset_variable = { name = sr_$KEY$_stock value = 0 }\n}\n",
            "draw = {\n"
            "\tchange_variable = { name = sr_$GOOD$_stock add = 1 }\n"
            "\tchange_variable = { name = sr_$GOOD$_price add = 1 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 3, "var", "sr_$GOOD$_price")])
        self.assertEqual((result.judged, result.unjudged), (2, 0))

    def test_a_parameter_change_matches_a_literal_set(self):
        result = _judge(
            "seed = {\n\tset_variable = { name = te_tax_rate_low value = 0 }\n}\n",
            "bump = {\n"
            "\tchange_variable = { name = te_tax_rate_$BAND$ add = 1 }\n"
            "\tchange_variable = { name = te_tax_base_$BAND$ add = 1 }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 3, "var", "te_tax_base_$BAND$")])

    def test_a_name_passed_on_under_the_same_parameter(self):
        # review, item 1: the mod's usual pass-on form, `OUT = $OUT$`. The
        # wrapper's substitution gives the template back unchanged, which used
        # to read as "this call passes nothing".
        wrapper = "w = {\n\tte_set_sqrt = { IN = 4 OUT = $OUT$ }\n}\n"
        use = "e = {\n\tw = { OUT = x }\n\tchange_variable = { name = x add = 1 }\n}\n"
        self.assertEqual(_names(_judge(self.HELPER, wrapper, use)), [])
        # Part parameter, short literal part, same name passed on.
        result = _judge(
            "h = {\n\tset_variable = { name = a_$P$ value = 0 }\n}\n",
            "w = {\n\th = { P = $P$ }\n}\n",
            "e = {\n\tw = { P = x }\n\tchange_variable = { name = a_x add = 1 }\n}\n",
        )
        self.assertEqual(_names(result), [])

    def test_a_call_that_passes_none_of_the_parameters_credits_nothing(self):
        # The other half of item 1: `IN` is no part of the name `$OUT$`.
        result = _judge(
            self.HELPER,
            "e = {\n\tte_set_sqrt = { IN = x }\n\tchange_variable = { name = x add = 1 }\n}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 3, "var", "x")])

    def test_a_long_chain_of_helpers_in_any_file_order(self):
        # Callers before their callees, so each pass resolves one level.
        chain = ["e = {\n\tw7 = { A7 = x }\n\tchange_variable = { name = x add = 1 }\n}\n"]
        for i in range(7, 0, -1):
            chain.append(f"w{i} = {{\n\tw{i - 1} = {{ A{i - 1} = $A{i}$ }}\n}}\n")
        chain += ["w0 = {\n\tte_set_sqrt = { IN = 1 OUT = $A0$ }\n}\n", self.HELPER]
        self.assertEqual(_names(_judge(*chain)), [])

    def test_a_caller_that_holds_only_part_of_the_name(self):
        # review, item 5: the event writes no variable and never spells the
        # variable's name, only the argument that completes it.
        result = _judge(
            "h = {\n\tset_variable = { name = $P$_ct value = 0 }\n}\n",
            "e = {\n\tchange_variable = { name = abc_ct add = 1 }\n\tchange_variable = { name = xy_ct add = 1 }\n}\n",
            events__c="c.1 = {\n\timmediate = {\n\t\th = { P = abc }\n\t}\n}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 3, "var", "xy_ct")])

    def test_a_wrapper_in_a_file_that_writes_no_variable(self):
        # The wrapper's file is read because it calls the helper, and the
        # event's because it calls the wrapper.
        result = _judge(
            self.HELPER,
            "e = {\n\tchange_variable = { name = far add = 1 }\n}\n",
            common__scripted_effects__wrap_effects="wrap = {\n\tte_set_sqrt = { IN = 2 OUT = $TO$ }\n}\n",
            events__caller="c.1 = {\n\timmediate = {\n\t\twrap = { TO = far }\n\t}\n}\n",
        )
        self.assertEqual(_names(result), [])

    def test_a_parameter_not_in_upper_case(self):
        # review, item 5. The mod writes every parameter in capitals.
        for param in ("out", "Out"):
            with self.subTest(param=param):
                result = _judge(
                    f"h = {{\n\tset_variable = {{ name = ${param}$ value = 0 }}\n}}\n",
                    f"e = {{\n\th = {{ {param} = x }}\n\tchange_variable = {{ name = x add = 1 }}\n}}\n",
                )
                self.assertEqual(_names(result), [])

    def test_an_all_parameter_change_is_judged_for_each_name_a_caller_passes(self):
        # review, item 4: the flag goes on the call that passes the name.
        result = _judge(
            "bump = {\n\tchange_variable = { name = $C$ add = 1 }\n}\n",
            "e = {\n"
            "\tset_variable = { name = started value = 0 }\n"
            "\tbump = { C = started }\n"
            "\tbump = { C = never_set }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 4, "var", "never_set")])
        flag = result.flags[0]
        self.assertEqual(flag.via, ("common/scripted_effects/f0_effects.txt", 2, "$C$"))
        self.assertIn("passes `never_set` to the `change_variable` of `$C$` at "
                      "`common/scripted_effects/f0_effects.txt:2`", flag.message)
        self.assertEqual((result.judged, result.unjudged), (1, 0))

    def test_a_change_reached_through_a_wrapper_and_from_another_file(self):
        result = _judge(
            "bump = {\n\tchange_global_variable = { name = $C$ add = 1 }\n}\n",
            "tick = {\n\tbump = { C = $C$ }\n}\n",
            events__m="m.1 = {\n\timmediate = {\n\t\ttick = { C = world_clock }\n\t}\n}\n",
        )
        self.assertEqual(_names(result), [("m.txt", 3, "global_var", "world_clock")])

    def test_a_part_parameter_change_resolved_by_a_caller_needs_that_exact_name(self):
        result = _judge(
            "draw = {\n\tchange_variable = { name = sr_$GOOD$_stock subtract = 1 }\n}\n",
            "e = {\n"
            "\tset_variable = { name = sr_grain_stock value = 0 }\n"
            "\tdraw = { GOOD = grain }\n"
            "\tdraw = { GOOD = steel }\n"
            "}\n",
        )
        self.assertEqual(_names(result), [("f1_effects.txt", 4, "var", "sr_steel_stock")])

    def test_a_name_passed_to_a_helper_is_suppressed_on_the_call(self):
        result = _judge(
            "bump = {\n\tchange_variable = { name = $C$ add = 1 }\n}\n",
            "e = {\n\tbump = { C = theirs } # REVIEWED 2026-11-15 (variable_init): a vanilla event sets it\n}\n",
        )
        self.assertEqual(result.unreviewed, [])
        self.assertEqual(len(result.exemptions), 1)
        self.assertEqual(result.stale, [])

    def test_an_all_parameter_name_no_caller_resolves_is_counted_not_judged(self):
        result = _judge(
            "bump = {\n"
            "\tchange_variable = { name = $COUNTER$ add = 1 }\n"
            "\tchange_variable = { name = $PX$f0 add = 1 }\n"
            "}\n"
        )
        self.assertEqual(_names(result), [])
        self.assertEqual((result.judged, result.unjudged), (0, 2))

    def test_an_all_parameter_set_initialises_nothing_by_itself(self):
        # `$OUT$` as a pattern would match every name in the mod.
        result = _judge(self.HELPER, "e = {\n\tchange_variable = { name = x add = 1 }\n}\n")
        self.assertEqual(len(result.flags), 1)


class ExemptionTests(unittest.TestCase):
    def test_tagged_comment_on_the_change_line(self):
        result = _judge(
            "e = {\n\tchange_variable = { name = x add = 1 } "
            "# REVIEWED 2026-11-15 (variable_init): set by a vanilla event\n}\n"
        )
        self.assertEqual(result.unreviewed, [])
        self.assertEqual(result.exemptions[0].exemption["rationale"], "set by a vanilla event")
        self.assertFalse(result.failed)

    def test_tagged_comment_on_a_multi_line_blocks_opening_line(self):
        result = _judge(
            "e = {\n"
            "\tchange_variable = { # REVIEWED 2026-11-15 (variable_init): why\n"
            "\t\tname = x\n"
            "\t\tadd = 1\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(result.exemptions), 1)

    def test_the_plain_form_belongs_to_the_clamp_audit(self):
        # change_variable_clamp_audit reads `# REVIEWED date: why` on the same
        # line, so this audit takes the tagged form only.
        result = _judge("e = {\n\tchange_variable = { name = x add = 1 } # REVIEWED 2026-11-15: why\n}\n")
        self.assertEqual(len(result.unreviewed), 1)

    def test_a_tag_that_suppresses_nothing_is_stale(self):
        result = _judge(
            "e = {\n"
            "\tset_variable = { name = x value = 0 }\n"
            "\tchange_variable = { name = x add = 1 } # REVIEWED 2026-11-15 (variable_init): why\n"
            "}\n",
            # A file the scan never parses still has its comments read.
            common__script_values__v="v = { value = 1 } # REVIEWED 2026-11-15 (variable_init): why\n",
        )
        self.assertEqual(result.flags, [])
        self.assertEqual([(t.file.rsplit("/", 1)[-1], t.line, t.tag) for t in result.stale],
                         [("v.txt", 1, "variable_init"), ("f0_effects.txt", 3, "variable_init")])
        self.assertTrue(result.failed)


class VanillaSnapshotTests(unittest.TestCase):
    def test_reads_every_form_from_the_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "vanilla_parsed", "common")
            os.makedirs(base)
            with open(os.path.join(base, "journal_entries.json"), "w", encoding="utf-8") as fh:
                # A parser tuple is an operator-first array; a repeated key is a list of them.
                fh.write('{"je": ["=", {"immediate": ["=", {'
                         '"set_variable": [["=", {"name": ["=", "block_form"], "value": ["=", "0"]}], ["=", "flag_form"]],'
                         '"set_global_variable": ["=", {"name": ["=", "a_global"]}]}]}]}')
            self.assertEqual(vanilla_sets(tmp), {("var", "block_form"), ("var", "flag_form"),
                                                 ("global_var", "a_global")})

    def test_no_snapshot_is_no_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(vanilla_sets(tmp), set())

    def test_the_committed_snapshot_has_the_great_reforms_counter(self):
        # te_tax_vanilla_je_overrides.txt adds to vanilla's great_reforms_var.
        self.assertIn(("var", "great_reforms_var"), vanilla_sets(ROOT))


class AuditAndReportTests(unittest.TestCase):
    def _mod(self, tmp: str) -> None:
        for rel, text in {
            "common/scripted_effects/a_effects.txt": "e = {\n\tchange_variable = { name = x add = 1 }\n}\n",
            "events/b.txt": "b.1 = {\n\timmediate = {\n\t\tchange_variable = { name = y add = 1 } "
                            "# REVIEWED 2026-11-15 (variable_init): why\n\t}\n}\n",
            "common/readme.md": "change_variable = { name = z add = 1 }\n",
        }.items():
            path = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(text)

    def test_audit_walks_common_and_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._mod(tmp)
            result = audit(mod_path=tmp)
        self.assertEqual([(f.file, f.name, bool(f.exemption)) for f in result.flags],
                         [("common/scripted_effects/a_effects.txt", "x", False), ("events/b.txt", "y", True)])
        self.assertEqual(result.files_audited, 2)

    def test_regenerate_writes_the_report_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._mod(tmp)
            with mock.patch("path_constants.mod_path", tmp):
                summary = change_variable_init_audit.regenerate()
            self.assertEqual((summary["unreviewed"], summary["exempted"], summary["judged"]), (1, 1, 2))
            with open(os.path.join(tmp, "docs", "engine", "change_variable_init_report.md"), encoding="utf-8") as fh:
                report = fh.read()
        self.assertIn("`common/scripted_effects/a_effects.txt:2`: `change_variable` of `x`", report)
        self.assertIn("# REVIEWED YYYY-MM-DD (variable_init): why", report)

    def test_report_carries_no_volatile_numbers(self):
        # How many changes were judged moves with unrelated mod content.
        with tempfile.TemporaryDirectory() as tmp:
            self._mod(tmp)
            report = render_report(audit(mod_path=tmp))
        self.assertNotIn("judged", report)
        self.assertNotIn("files", report.split("## Coverage")[1])

    def test_the_registry_names_this_audits_tag_and_report(self):
        entry = audit_registry.BY_NAME["change_variable_init_audit"]
        self.assertEqual(entry.tags, (change_variable_init_audit.CHECK,))
        self.assertEqual(entry.report_path, change_variable_init_audit.REPORT_PATH.replace(os.sep, "/"))


class TheModTests(unittest.TestCase):
    def test_every_changed_variable_in_the_mod_has_an_initialising_set(self):
        result = audit(mod_path=ROOT)
        self.assertEqual([(f.file, f.line, f.message) for f in result.unreviewed], [])
        self.assertEqual(result.stale, [])
        # The scan saw the mod: thousands of changes, a handful not judged.
        self.assertGreater(result.judged, 5000)
        self.assertLess(result.unjudged, 100)


if __name__ == "__main__":
    unittest.main()
