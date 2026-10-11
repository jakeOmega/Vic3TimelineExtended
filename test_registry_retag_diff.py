"""Tests for scripts/analysis/registry_retag_diff.py (#873)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))

import registry_retag_diff as rrd  # noqa: E402

STACK = (
    "[00:00:0{n}][jomini_script_system.cpp:304]: Script system error!\n"
    "  Error: Event target link 'capital' returned an invalid object\n"
    "  Script location: common/scripted_triggers/00_scripted_triggers.txt:1065 <- {frames}"
    "common/ai_strategies/00_default_strategy.txt:6513\n"
)


def _registry(root: str, body: str) -> str:
    for rel, text in ((rrd.VANILLA_DOC, body), (rrd.MOD_NOISE_DOC, ""), (rrd.OPEN_ISSUES_DOC, "")):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return root


class RegistryRetagDiffTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        logs = os.path.join(self.tmp, "run_a")
        os.makedirs(logs)
        engine = STACK.format(n=1, frames="")
        mod = STACK.format(n=2, frames="common/on_actions/un_on_actions.txt:88 <- ")
        # Two copies of one rotation: each line must count once.
        for name in ("error.log", "error.1.log"):
            with open(os.path.join(logs, name), "w", encoding="utf-8") as fh:
                fh.write(engine + mod + engine)
        with open(os.path.join(logs, "game.log"), "w", encoding="utf-8") as fh:
            fh.write(engine)
        self.mod_root = os.path.join(self.tmp, "mod")
        os.makedirs(os.path.join(self.mod_root, "common", "on_actions"))
        with open(os.path.join(self.mod_root, "common", "on_actions", "un_on_actions.txt"), "w") as fh:
            fh.write("")
        self.rows = rrd.build_corpus([logs])
        heading = "## Script errors observed\n\n### `common/ai_strategies/00_default_strategy.txt` — capital\n"
        self.old = _registry(os.path.join(self.tmp, "old"),
                             heading + "\n```\n00_default_strategy.txt:6513\n```\n")
        self.new = _registry(os.path.join(self.tmp, "new"), heading + "- stack: vanilla only\n\n"
                             "```\nEvent target link 'capital' returned an invalid object\n```\n")

    def test_corpus_counts_each_line_once_and_skips_other_logs(self):
        counts = sorted(r["count"] for r in self.rows)
        self.assertEqual(counts, [1, 2])  # the engine-only line twice per file, not four times
        self.assertEqual({tuple(r["runs"]) for r in self.rows}, {("run_a",)})

    def test_corpus_round_trips(self):
        path = os.path.join(self.tmp, "c.json.gz")
        rrd.save_corpus(self.rows, path)
        self.assertEqual(rrd.load_corpus(path), self.rows)

    def test_diff_reports_the_mod_framed_line_the_old_path_signature_hid(self):
        old = rrd.tag(self.rows, self.old, self.mod_root)
        new = rrd.tag(self.rows, self.new, self.mod_root)
        self.assertTrue(all(old))  # the bare path caught both lines
        result = rrd.diff(self.rows, old, new, self.mod_root)
        self.assertEqual(result["tagged"], {"old": 3, "new": 2})
        (lost,) = result["lost"]["capital"]
        self.assertTrue(lost["mod_frame"])
        self.assertIsNone(lost["new"])
        self.assertEqual(dict(result["gained"]), {})


if __name__ == "__main__":
    unittest.main()
