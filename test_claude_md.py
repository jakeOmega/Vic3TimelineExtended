"""CLAUDE.md loads in every session: keep it short, and keep its pointers alive."""
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(ROOT, ".claude", "rules")

# CLAUDE.md was 57 KB before its area rules moved to .claude/rules/ (2026-11-09).
# Raise this only on purpose: a rule for one kind of file belongs in that area's
# rules file, and a lesson a machine can check belongs in preflight or an audit.
BUDGET_BYTES = 26_000


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class ClaudeMdTests(unittest.TestCase):
    def test_stays_within_its_budget(self):
        size = len(read("CLAUDE.md").encode("utf-8"))
        self.assertLessEqual(
            size, BUDGET_BYTES,
            f"CLAUDE.md is {size} bytes, over its {BUDGET_BYTES}-byte budget. Move area-specific "
            "text to .claude/rules/ or a guide (see its § Recording lessons learned).",
        )

    def test_paths_it_names_exist(self):
        text = read("CLAUDE.md")
        named = set(re.findall(r"`((?:\.claude|docs|scripts|\.github)/[\w./-]+\.(?:md|py|sh|yml))`", text))
        named |= set(re.findall(r"`(\w+\.py)`", text))
        self.assertGreater(len(named), 25)
        missing = sorted(p for p in named if not os.path.exists(os.path.join(ROOT, p)))
        self.assertEqual(missing, [], "CLAUDE.md names files that do not exist")

    def test_every_rules_file_is_in_the_table(self):
        text = read("CLAUDE.md")
        for name in sorted(os.listdir(RULES)):
            self.assertIn(f".claude/rules/{name}", text, f"{name} is missing from § Rules by area")


class RulesFileTests(unittest.TestCase):
    def test_each_is_scoped_to_paths_that_match_something(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=True,
        ).stdout.split("\n")
        for name in sorted(os.listdir(RULES)):
            text = read(".claude", "rules", name)
            match = re.match(r"---\npaths:\n((?:  - \".+\"\n)+)---\n", text)
            self.assertIsNotNone(match, f"{name}: no `paths:` frontmatter, so it would load in every session")
            for glob in re.findall(r'  - "(.+)"', match.group(1)):
                prefix = glob.split("*")[0]
                suffix = glob.rsplit("*", 1)[-1]
                self.assertTrue(
                    any(p.startswith(prefix) and p.endswith(suffix) for p in tracked),
                    f"{name}: `{glob}` matches no tracked file",
                )

    def test_they_are_tracked(self):
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", ".claude/rules/script.md"], cwd=ROOT,
        ).returncode
        self.assertEqual(ignored, 1, ".gitignore hides .claude/rules/")


if __name__ == "__main__":
    unittest.main()
