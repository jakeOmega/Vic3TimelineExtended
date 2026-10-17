"""Tests for variable_usage (#973): the per-site variable index behind
`GET /variable-usage/<name>`.

Run: python3 test_variable_usage.py
"""
import os
import tempfile
import unittest

import variable_usage as vu

EFFECTS = """\
te_ops_create = {
	add_to_variable_list = { name = te_ops target = scope:op }
	set_variable = { name = te_ops_count value = 1 }
	change_variable = { name = te_ops_count add = var:te_ops_step }
}

te_ops_walk = {
	every_in_list = {
		variable = te_ops
		limit = { te_op_is_hostile = yes }
		set_variable = te_op_seen
	}
	every_in_list = {
		variable = te_ops
		if = {
			limit = { te_op_is_hostile = yes }
			remove_variable = te_op_seen
		}
	}
	random_in_list = {
		variable = te_ops
		limit = { te_op_is_wrapped = yes }
	}
	every_in_list = {  # a temporary list, not a variable
		list = te_ops
	}
	scope:target = {
		every_in_global_list = {
			variable = te_ops
			limit = { has_variable = te_op_seen }
		}
	}
	set_local_variable = { name = te_ops_count value = 2 }
	set_variable = { name = te_$KIND$_stock value = 0 }
	set_variable = { name = $NAME$ value = 0 }
	# set_variable = te_ops_comment
}
"""

TRIGGERS = """\
te_op_is_hostile = {
	NOT = { has_variable = te_op_friendly }
}

te_op_is_wrapped = {
	te_op_is_hostile = yes
}
"""

VALUES = """\
te_ops_value = {
	value = var:te_ops_count
	add = scope:actor.var:te_ops_count
	add = global_var:te_ops_count
}
"""

ACTIONS = """\
te_action = {
	possible = {
		any_in_list = {
			variable = te_ops
			te_op_is_hostile = yes
		}
	}
}
"""

GUI = """\
types te_types {
	type te_list = flowcontainer {
		datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('te_ops')]"
		# datamodel = "[GetList('te_ops')]"
		visible = "[GetGlobalVariable('te_ops_count').IsSet]"
	}
}
"""

LOC = """\
﻿l_english:
 te_ops_label:0 "#b [ROOT.GetCountry.MakeScope.Var('te_ops_count').GetValue]#! ops"
 # te_commented:0 "[MakeScope.Var('te_ops_count')]"
"""


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class VariableUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.tmp.name
        _write(root, "common/scripted_effects/te_ops_effects.txt", EFFECTS)
        _write(root, "common/scripted_triggers/te_ops_triggers.txt", TRIGGERS)
        _write(root, "common/script_values/te_ops_values.txt", VALUES)
        _write(root, "common/diplomatic_actions/te_actions.txt", ACTIONS)
        _write(root, "gui/te_ops.gui", GUI)
        _write(root, "localization/english/te_ops_l_english.yml", LOC)
        cls.index = vu.build_index(root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def sites(self, name, **kw):
        return vu.usage(self.index, name, **kw)["sites"]

    def test_list_sites_by_op(self):
        ops = [(s["entity"], s["op"], s["access"]) for s in self.sites("te_ops")]
        self.assertIn(("te_ops_create", "add_to_variable_list", "write"), ops)
        self.assertEqual(sum(1 for e, op, _a in ops if op == "every_in_list"), 2,
                         "the `list =` walker is a temporary list")
        self.assertIn(("te_action", "any_in_list", "iterate"), ops)
        self.assertIn((None, "gui_GetList", "read"), ops)
        self.assertEqual(sum(1 for _e, op, _a in ops if op == "gui_GetList"), 1,
                         "the commented-out GUI line doesn't count")

    def test_entity_type_and_line(self):
        walk = [s for s in self.sites("te_ops") if s["op"] == "every_in_list"]
        self.assertEqual(walk[0]["entity_type"], "Scripted Effects")
        self.assertEqual(walk[0]["file"], "common/scripted_effects/te_ops_effects.txt")
        self.assertEqual(walk[0]["line"], 8)
        action = [s for s in self.sites("te_ops") if s["op"] == "any_in_list"][0]
        self.assertEqual(action["entity_type"], "Diplomatic Actions")

    def test_limit_text(self):
        walks = {s["line"]: s for s in self.sites("te_ops") if s["access"] == "iterate"}
        self.assertEqual(walks[8]["limit"], "te_op_is_hostile = yes")
        self.assertIsNone(walks[13]["limit"])
        # An any_* trigger takes no limit: its body is the condition.
        action = [s for s in walks.values() if s["op"] == "any_in_list"][0]
        self.assertEqual(action["limit"], "te_op_is_hostile = yes")

    def test_store_kept_apart(self):
        stores = {s["store"] for s in self.sites("te_ops", kind="list")}
        self.assertEqual(stores, {"scope", "global"})
        glob = self.sites("te_ops", store="global")
        self.assertEqual([s["op"] for s in glob], ["every_in_global_list"])
        local = self.sites("te_ops_count", store="local")
        self.assertEqual([s["op"] for s in local], ["set_local_variable"])

    def test_scope_hint(self):
        glob = self.sites("te_ops", store="global")[0]
        self.assertEqual(glob["scope_hint"], "scope:target")
        seen = [s for s in self.sites("te_op_seen") if s["op"] == "set_variable"][0]
        self.assertEqual(seen["scope_hint"], "every_in_list(te_ops)")
        reads = [s for s in self.sites("te_ops_count") if s["op"] == "var_read"]
        hints = sorted(str(s["scope_hint"]) for s in reads)
        self.assertEqual(hints, ["None", "scope:actor"])

    def test_var_reads_and_data_functions(self):
        rows = self.sites("te_ops_count")
        ops = sorted(s["op"] for s in rows)
        self.assertEqual(ops, sorted([
            "set_variable", "change_variable", "set_local_variable",
            "var_read", "var_read", "global_var_read",
            "gui_GetGlobalVariable", "loc_Var",
        ]))
        loc = [s for s in rows if s["op"] == "loc_Var"][0]
        self.assertEqual(loc["entity"], "te_ops_label")
        self.assertEqual(loc["entity_type"], "Localization")
        self.assertEqual(loc["line"], 2)
        step = self.sites("te_ops_step")
        self.assertEqual([(s["op"], s["entity"]) for s in step], [("var_read", "te_ops_create")])

    def test_comment_is_not_a_site(self):
        self.assertIsNone(vu.usage(self.index, "te_ops_comment"))

    def test_parameterized_names(self):
        rows = self.sites("te_steel_stock")
        self.assertEqual([s["pattern"] for s in rows], ["te_$KIND$_stock"])
        self.assertIsNone(vu.usage(self.index, "te_steel_stock", patterns=False))
        # `$NAME$` alone would match everything, so it matches nothing.
        self.assertIsNone(vu.usage(self.index, "anything_at_all"))

    def test_summary(self):
        summary = vu.usage(self.index, "te_ops")["summary"]
        self.assertEqual(summary["iterations"], 5)
        self.assertEqual(summary["iterations_without_limit"], 1)
        self.assertEqual(summary["writes"], 1)

    def test_unfiltered_by_follows_scripted_triggers(self):
        self.assertEqual(vu.trigger_wrappers(self.index, "te_op_is_hostile"),
                         ["te_op_is_wrapped"])
        out = vu.usage(self.index, "te_ops", unfiltered_by="te_op_is_hostile")
        self.assertEqual(out["unfiltered_by"]["wrappers"], ["te_op_is_wrapped"])
        rows = {s["line"]: s for s in out["sites"]}
        # Line 8 (limit names it), the random_in_list (limit names a wrapper)
        # and the action (body is the condition) are filtered.
        self.assertEqual(sorted(rows), [13, 28])
        self.assertTrue(rows[13]["named_in_body"], "an `if` limit inside the loop")
        self.assertFalse(rows[28]["named_in_body"])
        self.assertEqual(out["summary"]["unfiltered"], 2)

    def test_names_listing(self):
        out = vu.names(self.index, prefix="te_ops")
        names = [r["name"] for r in out["names"]]
        self.assertEqual(names, ["te_ops", "te_ops_count", "te_ops_step"])
        ops = [r for r in out["names"] if r["name"] == "te_ops"][0]
        self.assertEqual(ops["kinds"], ["list"])
        self.assertEqual(ops["stores"], ["global", "scope"])
        self.assertEqual([r["name"] for r in vu.names(self.index, prefix="te_*_seen")["names"]],
                         ["te_op_seen"])


if __name__ == "__main__":
    unittest.main()
