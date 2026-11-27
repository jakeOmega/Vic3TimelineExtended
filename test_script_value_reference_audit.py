"""Tests for script_value_reference_audit (#2021)."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import script_value_reference_audit as audit_mod

DEFINED = {"sr_pers_capacity", "vanilla_value", "te_scripted_trigger"}
ENGINE = {"total_size", "gdp", "root", "this", "prev"} | audit_mod.ENGINE_WORDS


def flags(text, defined=DEFINED, engine=ENGINE):
    found, stale = audit_mod.scan_text(text, "common/x.txt", defined, engine)
    return [(f.line, f.key, f.op, f.name) for f in found], stale


class ScanTextTests(unittest.TestCase):
    def test_an_undefined_name_in_a_value_position_is_flagged(self):
        # The #2020 shape: a cap read from a script value nobody wrote.
        text = ("sr_kill = {\n"
                "\tvalue = sr_pers_state_spacers\n"
                "\tmax = sr_pers_state_spacer_steps\n"
                "\tadd_modifier = { name = x multiplier = sr_missing days = sr_missing_days }\n"
                "}\n")
        self.assertEqual(flags(text)[0], [
            (2, "value", "=", "sr_pers_state_spacers"),
            (3, "max", "=", "sr_pers_state_spacer_steps"),
            (4, "multiplier", "=", "sr_missing"),
            (4, "days", "=", "sr_missing_days"),
        ])

    def test_each_value_key_and_comparison(self):
        for key in sorted(audit_mod.VALUE_KEYS):
            with self.subTest(key=key):
                self.assertEqual(flags(f"x = {{ {key} = nope }}\n")[0], [(1, key, "=", "nope")])
        for op in sorted(audit_mod.COMPARISONS):
            with self.subTest(op=op):
                self.assertEqual(flags(f"x = {{ gdp {op} nope }}\n")[0], [(1, "gdp", op, "nope")])

    def test_what_resolves(self):
        text = ("x = {\n"
                "\tvalue = sr_pers_capacity\n"      # a mod script value
                "\tadd = vanilla_value\n"           # vanilla's
                "\tmultiply = total_size\n"         # an engine trigger used as a value
                "\tvalue = ROOT\n"                  # a scope keyword, any case
                "\tcount = all\n"
                "\tlaw_stance = { law = law_x value < neutral }\n"
                "\tig_approval < happy\n"
                "\tmilitary_wage_level <= low\n"
                "\tvalue = te_scripted_trigger\n"
                "\tsave_scope_value_as = { name = flag value = yes }\n"
                "}\n")
        self.assertEqual(flags(text)[0], [])

    def test_what_is_not_judged(self):
        text = ("x = {\n"
                "\tvalue = scope:saved\n"
                "\tadd = var:te_x\n"
                "\tmultiply = owner.gdp\n"
                "\tmax = define:NPops|MAX\n"
                "\tvalue = $AMOUNT$\n"
                "\tvalue = te_$KIND$_share\n"
                "\tvalue = @constant\n"
                "\tvalue = 12\n"
                "\tadd = -0.5\n"
                "\tvalue = { add = 1 }\n"
                "\tname = not_a_value\n"                       # not a value position
                "\tfactor = appeasement_factor\n"              # change_appeasement's factor names one
                "\tscope:a ?= nope\n"                          # `?=` is no number comparison
                "\tgdp = nope\n"                               # `=` is read only after the value keys
                "\tvalue = sr_x # value = in_a_comment\n"
                "\tdebug_log = \"value = in_a_string\"\n"
                "}\n")
        found, _ = flags(text)
        self.assertEqual(found, [(16, "value", "=", "sr_x")])

    def test_a_tag_suppresses_and_a_tag_with_nothing_to_suppress_is_stale(self):
        text = ("x = {\n"
                "\tvalue = nope # REVIEWED 2026-11-27 (script_value_reference): defined by the engine\n"
                "\tvalue = sr_pers_capacity # REVIEWED 2026-11-27 (script_value_reference): left over\n"
                "\tvalue = other # REVIEWED 2026-11-27 (some_other_check): not ours\n"
                "}\n")
        found, stale = audit_mod.scan_text(text, "common/x.txt", DEFINED, ENGINE)
        self.assertEqual([(f.line, f.name, bool(f.exemption)) for f in found], [(2, "nope", True), (4, "other", False)])
        self.assertEqual([(t.line, t.tag) for t in stale], [(3, "script_value_reference")])

    def test_counts(self):
        result = audit_mod.AuditResult()
        audit_mod.scan_text("x = { value = sr_pers_capacity add = scope:y max = 3 }\n", "c.txt", DEFINED, ENGINE,
                            result)
        self.assertEqual((result.refs_checked, result.chained_skipped), (1, 1))


class AuditTreeTests(unittest.TestCase):
    """The whole audit over a small mod tree: where names are defined, and what it refuses to run without."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def tree(self):
        self.write("vanilla_parsed/common/script_values.json", json.dumps({"vanilla_value": ["=", "1"]}))
        self.write("docs/engine/triggers_summary.txt", "# header\n\npop|total_size|Compares the total size\n")
        self.write("docs/engine/event_targets_summary.txt", "# header\n\n|root||The head of the scope\n")
        self.write("common/script_values/sv.txt", "﻿mod_value = { value = vanilla_value }\n")
        self.write("common/scripted_triggers/t.txt", "﻿mod_trigger = { always = yes }\n")
        self.write("events/e.txt", "﻿e.1 = { immediate = { set_variable = { name = x value = ROOT } } }\n")
        self.write("common/scripted_effects/fx.txt",
                   "﻿fx = {\n\tchange_variable = { name = x add = mod_value }\n"
                   "\tchange_variable = { name = y add = total_size }\n"
                   "\tchange_variable = { name = z add = gone_value }\n}\n")

    def test_a_tree(self):
        self.tree()
        result = audit_mod.audit(self.root)
        self.assertEqual([(f.file, f.line, f.name) for f in result.flags],
                         [("common/scripted_effects/fx.txt", 4, "gone_value")])
        self.assertTrue(result.failed)
        self.assertEqual(result.files_scanned, 4)
        report = audit_mod.render(result)
        self.assertIn("`common/scripted_effects/fx.txt:4`: `add = gone_value`", report)
        self.assertIn("(script_value_reference)", report)

    def test_a_missing_list_raises_rather_than_flagging_everything(self):
        self.tree()
        os.remove(self.root / "docs" / "engine" / "triggers_summary.txt")
        with self.assertRaises(FileNotFoundError):
            audit_mod.audit(self.root)
        self.tree()
        os.remove(self.root / "vanilla_parsed" / "common" / "script_values.json")
        with self.assertRaises(FileNotFoundError):
            audit_mod.audit(self.root)

    def test_the_engine_lists_read_their_second_column(self):
        self.tree()
        self.assertEqual(audit_mod.engine_names(self.root), {"total_size", "root"})

    def test_the_committed_engine_lists_hold_the_names_the_mod_reads(self):
        """The real lists: a regenerated list that lost a column would flag every engine value at once."""
        names = audit_mod.engine_names(Path(__file__).resolve().parent)
        self.assertTrue({"total_size", "state_population", "gdp", "root", "this", "prev", "year"} <= names)


if __name__ == "__main__":
    unittest.main()
