"""The shot manifest (`scripts/image_pipeline/guide_shots.py`) and the staleness report beside it (#2056).

The manifest is the guide's shot list: every picture a chapter shows and every `<!-- screenshot: -->` spot has an
entry, and each entry `game_qa capture` takes has a view the harness accepts.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "scripts" / "image_pipeline"))
import guide_shots as gs  # noqa: E402
import guide_shots_stale as stale  # noqa: E402


class ManifestTest(unittest.TestCase):
    def test_the_manifest_is_valid(self):
        self.assertEqual(gs.validate(), [])

    def test_every_guide_picture_and_placeholder_has_an_entry(self):
        listed = {shot["out"] for shot in gs.SHOTS.values()}
        for image in gs.guide_images():
            if not image.endswith("pop_spending_by_wealth.png"):
                self.assertIn(image, listed)
        self.assertEqual(len(gs.guide_placeholders()),
                         sum(1 for s in gs.SHOTS.values() if s["status"] == "placeholder"))

    def test_a_missing_entry_and_a_bad_view_are_problems(self):
        shots = dict(gs.SHOTS)
        shots.pop("banking_tab")
        broken = dict(gs.SHOTS["nuclear_tab_armed"], view=[["ExecuteConsoleCommand('save')"]])
        shots["nuclear_tab_armed"] = broken
        with mock.patch.object(gs, "SHOTS", shots):
            problems = gs.validate()
        self.assertTrue(any("banking_tab.png, which no shot lists" in p for p in problems), problems)
        self.assertTrue(any(p.startswith("shot nuclear_tab_armed: view") for p in problems), problems)

    def test_needs(self):
        self.assertEqual(gs.parse_need("nd_stockpile > 0"), ("nd_stockpile", ">", 0.0))
        self.assertEqual(gs.parse_need("temperature_anomaly_display >= 1.5"),
                         ("temperature_anomaly_display", ">=", 1.5))
        trigger = "c:{tag} = { has_journal_entry = je_x }"
        self.assertEqual(gs.parse_need(trigger), (trigger, None, None))

    def test_the_view_helpers(self):
        steps = gs.te_window("banking", keys={"te_bank_open": "yes"})
        self.assertEqual(steps[0][-1], "set:com_open_window=te_systems_window", "the window opens last, its tab set")
        self.assertIn("clear:te_systems_window_wide", steps[0])
        self.assertIn("set:te_systems_window_wide=yes", gs.te_window("banking", wide=True)[0])
        self.assertEqual(gs.side_panel("budget", "te_banking"), [["panel:budget:te_banking"]])
        self.assertEqual(gs.market_tab("te_global_warming"), [["market:te_global_warming"]])

    def test_the_te_window_keys_are_the_windows_own(self):
        text = "".join((HERE / "gui" / name).read_text(encoding="utf-8-sig")
                       for name in ("te_systems_window.gui", "te_systems_window_generated.gui"))
        for key in gs.TE_WINDOW_KEYS:
            self.assertTrue("GetVariableSystem.Set('%s'" % key in text, key)

    def test_the_popup_keys_are_the_mods_own(self):
        gui = "".join(p.read_text(encoding="utf-8-sig") for p in (HERE / "gui").rglob("*.gui"))
        for key in gs.POPUP_KEYS:
            self.assertIn("GetVariableSystem.Set('%s'" % key, gui, key)

    def test_the_capture_key_is_the_harness_one(self):
        from game_qa import capture_gui
        self.assertEqual(gs.CAPTURE_KEY, capture_gui.CAPTURE_KEY)

    def test_the_mod_tabs_the_side_panel_helper_names_exist(self):
        gui = "".join(p.read_text(encoding="utf-8-sig") for p in (HERE / "gui").glob("*.gui"))
        for shot in gs.SHOTS.values():
            for step in shot.get("view") or []:
                for action in step:
                    if action.startswith(("panel:", "market:")) and action.count(":") >= 1:
                        tab = action.rsplit(":", 1)[1]
                        if tab.startswith("te_"):
                            self.assertTrue("InformationPanel.SelectTab('%s')" % tab in gui, action)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                                   GIT_COMMITTER_EMAIL="t@t")).stdout.strip()


class StaleTest(unittest.TestCase):
    """The report on a scratch repository: a picture is stale once a file it depends on changes after it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        (self.repo / "gui").mkdir()
        (self.repo / "img").mkdir()
        (self.repo / "gui" / "a.gui").write_text("a")
        (self.repo / "gui" / "b.gui").write_text("b")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "gui")
        (self.repo / "img" / "a.png").write_bytes(b"png")
        (self.repo / "img" / "b.png").write_bytes(b"png")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "pictures")
        self.shots = {
            "a": dict(out="img/a.png", status="pilot", depends_on=["gui/a*.gui"]),
            "b": dict(out="img/b.png", status="assisted", depends_on=["gui/b.gui"]),
            "c": dict(out="img/c.png", status="placeholder"),
        }

    def run_report(self, taken=None):
        with mock.patch.object(stale, "REPO", str(self.repo)), mock.patch.object(gs, "SHOTS", self.shots), \
                mock.patch.object(stale, "taken", lambda: taken or {}):
            return stale.report()

    def test_fresh_until_a_dependency_changes(self):
        found = self.run_report()
        self.assertEqual(found["stale"], {})
        self.assertEqual(sorted(found["fresh"]), ["a", "b"])
        (self.repo / "gui" / "a.gui").write_text("a2")
        git(self.repo, "commit", "-q", "-am", "a moves")
        found = self.run_report()
        self.assertEqual(list(found["stale"]), ["a"])
        self.assertEqual(found["stale"]["a"]["files"], ["gui/a.gui"])
        self.assertEqual(found["fresh"], ["b"])

    def test_an_uncommitted_edit_counts(self):
        (self.repo / "gui" / "b.gui").write_text("b2")
        self.assertEqual(list(self.run_report()["stale"]), ["b"])

    def test_a_captures_record_is_the_baseline(self):
        (self.repo / "gui" / "a.gui").write_text("a2")
        git(self.repo, "commit", "-q", "-am", "a moves")
        head = git(self.repo, "rev-parse", "HEAD")
        found = self.run_report({"a": {"commit": head}})
        self.assertNotIn("a", found["stale"], "taken after the change")
        found = self.run_report({"a": {"commit": "0" * 40}})
        self.assertIn("a", found["unknown"])



class InputStepTest(unittest.TestCase):
    def test_each_kind_with_its_arguments(self):
        for step in (("click", 0.5, 0.4), ("wheel", 0.5, 0.5, -40), ("drag", 0.1, 0.2, 0.3, 0.4), ("advance", 1),
                     ("event", "te_debug_colonial_empire.1", 5)):
            with self.subTest(step=step):
                self.assertTrue(gs._input_ok(step))

    def test_anything_else_is_refused(self):
        for step in (("press", "esc"), ("click", 1.5, 0.4), ("click", 0.5), ("wheel", 0.5, 0.5, 41),
                     ("wheel", 0.5, 0.5, 0.5), ("advance", 0), ("advance", 32), ("advance", True),
                     ("event", "save", 0), ("event", "a.1", -1), ("event", "a.1", "0"), (), "click"):
            with self.subTest(step=step):
                self.assertFalse(gs._input_ok(step))


if __name__ == "__main__":
    unittest.main()
