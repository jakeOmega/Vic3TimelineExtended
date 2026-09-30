"""scripts/analysis/check_gui_lint.py: what it flags, on a throwaway repository."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))
import check_gui_lint as lint  # noqa: E402

BOM = "﻿"

BASE_GUI = BOM + """types base {
	type proven_row = flowcontainer {
		direction = vertical
		block "label" {}
		textbox = {
			text = "known_key"
			tooltip = "[GetScriptedGui('known_sgui').IsShown( GuiScope.End )]"
		}
		icon = { texture = "gfx/interface/vanilla_icon.dds" }
	}
}
"""

NEW_GUI = BOM + """types t {
	type te_new_row = proven_row {
		direction = vertical
		fancywidget = {}
		alignment_typo = left
		blockoverride "label" {}
		blockoverride "labl" {}
		textbox = {
			text = "missing_key"
			tooltip = "[GetScriptedGui('missing_sgui').IsShown( GuiScope.End )]"
		}
		textbox = { text = "[SelectLocalization( GetScriptedGui('known_sgui').IsShown( GuiScope.End ), 'known_key', 'gone_key' )]" }
		icon = { texture = "gfx/interface/nope.dds" }
		button = { onclick = "[GetVariableSystem.Toggle('te_new_details')]" }
		widget = { datacontext = "[MarketPanel.GetMarket.GetOwner.GetJournalEntry('je_x')]" }
		widget = { datacontext = "[Market.AccessMarketCapital.AccessOwner.GetJournalEntry('je_x')]" }
	}
"""


def _git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True)


class LintTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        repo = cls.tmp.name
        for d in ("gui", "localization/english", "common/scripted_guis"):
            os.makedirs(os.path.join(repo, d))
        with open(os.path.join(repo, "gui", "base.gui"), "w", encoding="utf-8") as f:
            f.write(BASE_GUI)
        with open(os.path.join(repo, "localization", "english", "x_l_english.yml"), "w", encoding="utf-8-sig") as f:
            f.write('l_english:\n known_key: "Known"\n')
        with open(os.path.join(repo, "common", "scripted_guis", "s.txt"), "w", encoding="utf-8-sig") as f:
            f.write("known_sgui = {\n\tscope = country\n}\n")
        _git(repo, "init", "-q")
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
        with open(os.path.join(repo, "gui", "new.gui"), "w", encoding="utf-8") as f:
            f.write(NEW_GUI)
        with open(os.path.join(repo, "gui", "clean.gui"), "w", encoding="utf-8") as f:
            f.write(BASE_GUI.replace("types base", "types clean").replace("proven_row", "clean_row"))
        linter = lint.Linter(repo, "HEAD")
        cls.changed = linter.changed_gui()
        for p in cls.changed:
            linter.lint_file(p)
        cls.findings = linter.findings

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def msgs(self, path, sev=None):
        return [m for s, p, _, m in self.findings if p == path and (sev is None or s == sev)]

    def test_untracked_files_are_linted(self):
        self.assertEqual(sorted(self.changed), ["gui/clean.gui", "gui/new.gui"])

    def test_clean_file_has_no_findings(self):
        self.assertEqual(self.msgs("gui/clean.gui"), [])

    def test_errors(self):
        errs = " | ".join(self.msgs("gui/new.gui", "ERROR"))
        self.assertIn("unclosed brace", errs)
        self.assertIn("'missing_key'", errs)
        self.assertIn("missing_sgui", errs)
        self.assertIn("'gone_key'", errs)
        self.assertNotIn("known_key", errs)
        self.assertNotIn("known_sgui", errs)
        self.assertEqual(errs.count("GetJournalEntry needs a non-const Country"), 1)

    def test_unproven_warnings(self):
        warns = " | ".join(self.msgs("gui/new.gui", "WARN"))
        self.assertIn("'fancywidget'", warns)
        self.assertIn("'alignment_typo'", warns)
        self.assertIn('"labl"', warns)
        self.assertNotIn('"label"', warns)
        self.assertIn("gfx/interface/nope.dds", warns)
        self.assertNotIn("vanilla_icon", warns)
        self.assertIn("te_new_details should end _open", warns)

    def test_loc_args(self):
        self.assertEqual(lint.loc_args("Localize('te_tt_break')"), ["te_tt_break"])
        expr = ("SelectLocalization( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('v'), "
                "'(CFixedPoint)1' ), 'key_a', 'key_b' )")
        self.assertEqual(lint.loc_args(expr), ["key_a", "key_b"])


if __name__ == "__main__":
    unittest.main()
