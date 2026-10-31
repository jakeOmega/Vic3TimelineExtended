"""scripts/mod_systems_split.py: the map from the old single `docs/systems/mod_systems.md` to its system files, and
`port`, which carries a pre-split branch's edits of the single file into those files by a three-way merge."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import mod_systems_split as ms  # noqa: E402

SINGLE = """# Key Mod Systems

Reference for all major gameplay systems.

## Judiciary (`lawgroup_judiciary`)

Judges.

Cases.

Defiance.

## Banking Cycle (`je_banking_cycle`)

Intro line.

### Policy Dashboard

Dashboard line.

### Monetary Policy (phase 1)

Rate line.

### Banking Law Modifiers

Laws line, see [the schema](tax_code_schema.md).

## Temporary Amendments (Sunset Clauses)

Sunsets.

## Amendment Petitions (`amendment_petition_events`)

Petitions.
"""


class TestSplit(unittest.TestCase):
    def setUp(self):
        self.files = ms.split(SINGLE, warn=lambda _m: None)

    def test_sections_go_to_their_system_files(self):
        self.assertEqual(sorted(self.files), ["amendments.md", "banking_cycle.md", "judiciary.md", "monetary_policy.md"])
        self.assertIn("## Judiciary (`lawgroup_judiciary`)\n\nJudges.\n\nCases.\n", self.files["judiciary.md"])
        amend = self.files["amendments.md"]
        self.assertLess(amend.index("## Temporary Amendments"), amend.index("## Amendment Petitions"))

    def test_monetary_subsections_leave_the_banking_file(self):
        banking, monetary = self.files["banking_cycle.md"], self.files["monetary_policy.md"]
        self.assertNotIn("Monetary Policy (phase 1)", banking)
        self.assertLess(banking.index("### Policy Dashboard"), banking.index("### Banking Law Modifiers"))
        self.assertIn(ms.MOVED_HEADINGS["monetary_policy.md"] + "\n\n### Monetary Policy (phase 1)\n\nRate line.\n",
                      monetary)

    def test_each_file_has_a_title_and_a_link_back(self):
        for name, text in self.files.items():
            with self.subTest(file=name):
                self.assertTrue(text.startswith(f"# {ms.BY_FILE[name].title}\n\n{ms.BACKLINK}\n\n"))

    def test_relative_links_gain_a_level(self):
        self.assertIn("[the schema](../tax_code_schema.md)", self.files["banking_cycle.md"])
        self.assertEqual(ms.relink("[a](https://x.org/y.md) [b](#anchor)"), "[a](https://x.org/y.md) [b](#anchor)")

    def test_an_unknown_section_gets_a_file_of_its_own_and_a_warning(self):
        warnings = []
        files = ms.split(SINGLE + "\n## Brand New System\n\nNew.\n", warn=warnings.append)
        self.assertIn("brand_new_system.md", files)
        self.assertEqual(len(warnings), 1)

    def test_every_mapped_section_prefix_is_unique_and_every_file_exists(self):
        prefixes = [p for s in ms.SYSTEMS for p in s.sections]
        for p in prefixes:
            with self.subTest(prefix=p):
                self.assertEqual(sum(q.startswith(p) or p.startswith(q) for q in prefixes), 1)
        for s in ms.SYSTEMS:
            with self.subTest(file=s.file):
                self.assertTrue((ms.SPLIT_DIR / s.file).exists())
                self.assertIn(s.category, ms.CATEGORIES)


class TestPort(unittest.TestCase):
    def setUp(self):
        self.current = ms.split(SINGLE, warn=lambda _m: None)
        # main edited the judiciary file after the split, two lines below the branch's edit
        self.current["judiciary.md"] = self.current["judiciary.md"].replace("Defiance.", "Defiance, rare.")

    def test_a_branch_edit_lands_in_its_file_beside_mains(self):
        edited = SINGLE.replace("Judges.", "Judges, appointed.").replace("Rate line.", "Rate line, revised.")
        merged = ms.port_texts(SINGLE, edited, self.current, warn=lambda _m: None)
        self.assertEqual(sorted(merged), ["judiciary.md", "monetary_policy.md"])
        judiciary, conflict = merged["judiciary.md"]
        self.assertFalse(conflict)
        self.assertIn("Judges, appointed.\n\nCases.\n\nDefiance, rare.\n", judiciary)
        self.assertIn("Rate line, revised.", merged["monetary_policy.md"][0])

    def test_both_sides_editing_one_line_is_a_conflict(self):
        edited = SINGLE.replace("Judges.", "Judges, elected.")
        self.current["judiciary.md"] = self.current["judiciary.md"].replace("Judges.", "Judges, appointed.")
        text, conflict = ms.port_texts(SINGLE, edited, self.current, warn=lambda _m: None)["judiciary.md"]
        self.assertTrue(conflict)
        self.assertIn("<<<<<<< main", text)

    def test_an_untouched_single_file_ports_nothing(self):
        self.assertEqual(ms.port_texts(SINGLE, SINGLE, self.current), {})


if __name__ == "__main__":
    unittest.main()
