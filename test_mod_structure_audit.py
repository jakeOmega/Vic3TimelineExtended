"""Unit tests for mod_structure_audit's collision check and report rendering.

Run: python3 test_mod_structure_audit.py
"""
import os
import tempfile
import unittest

from mod_structure_audit import AuditResult, Flag, audit, render_report


class _NoVanilla:
    """A mod state with no vanilla parse: the collision check reads only files."""
    base_parsers = {}


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class CollisionTests(unittest.TestCase):
    def _collisions(self, files):
        with tempfile.TemporaryDirectory() as root:
            for rel, text in files.items():
                _write(root, rel, text)
            result = audit(_NoVanilla(), mod_path=root)
        return [f for f in result.flags if f.kind == "collision"]

    def test_named_colors_blocks_merge(self):
        """Every named_colors file opens its own top-level `colors = {` and the
        engine merges them (vanilla 1.15 ships seven such files), so two in the
        mod are not a collision (#1423)."""
        flags = self._collisions({
            "common/named_colors/extra_goods_colors.txt":
                "colors = {\n\tte_goods_a = hsv360 { 0 0 38 }\n}\n",
            "common/named_colors/te_journal_map_colors.txt":
                "# header\ncolors = {\n\tte_jmap_no_data = hsv360 { 0 0 38 }\n}\n",
        })
        self.assertEqual(flags, [])

    def test_same_name_twice_elsewhere_is_a_collision(self):
        """The same two-file shape in a directory whose keys don't merge still
        flags, on the second file, naming the first."""
        flags = self._collisions({
            "common/laws/a.txt": "law_x = {\n\tgroup = lawgroup_y\n}\n",
            "common/laws/b.txt": "# header\nlaw_x = {\n\tgroup = lawgroup_y\n}\n",
        })
        self.assertEqual([(f.file, f.line) for f in flags],
                         [(os.path.join("common", "laws", "b.txt"), 2)])
        self.assertIn("(also at `" + os.path.join("common", "laws", "a.txt") + ":1`)",
                      flags[0].detail)


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line numbers, neither its own nor the
        ones its detail cites, and Coverage no file count, so the report
        changes only when the findings do. Unreviewed flags keep their lines."""
        result = AuditResult(
            flags=[
                Flag("collision", "common/laws/b.txt", 30,
                     "Duplicate top-level `law_x = { ... }` in `common/laws/` "
                     "(also at `common/laws/a.txt:5`); engine drops all but one silently."),
                Flag("inject", "common/buildings/c.txt", 44,
                     "`INJECT:building_y` targets a mod-only entity defined at "
                     "`common/buildings/d.txt:12`. Edit the definition directly.",
                     exemption={"date": "2026-06-01", "rationale": "load order checked"}),
            ],
            files_audited=366,
        )
        report = render_report(result)
        self.assertIn(
            "- `common/buildings/c.txt` — `INJECT:building_y` targets a mod-only entity "
            "defined at `common/buildings/d.txt`. Edit the definition directly. — "
            "**2026-06-01**: load order checked", report)
        self.assertNotIn("c.txt:44", report)
        self.assertNotIn("d.txt:12", report)
        self.assertIn("- `common/laws/b.txt:30` — Duplicate top-level", report)
        self.assertIn("(also at `common/laws/a.txt:5`)", report)
        self.assertNotIn("files audited", report)
        self.assertNotIn("366", report)
        self.assertIn("  - inject: 1", report)


if __name__ == "__main__":
    unittest.main()
