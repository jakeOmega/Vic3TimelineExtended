"""`docs/systems/mod_systems.md` is an index over `docs/systems/mod_systems/`, one file per system (split 2026-10-31
from a 1.2 MB single file). Every system file has a row that names its `##` sections, so a reference to a section of
the old file ("`mod_systems.md` § Inheritance") still resolves in one hop, and every relative link resolves."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "docs/systems/mod_systems.md"
SYSTEMS = ROOT / "docs/systems/mod_systems"
ROW = re.compile(r"^\| \[[^\]]+\]\(mod_systems/([^)]+\.md)\) \|")
LINK = re.compile(r"\]\((?![a-z]+:|#|/)([^)\s#]+)(?:#[^)\s]*)?\)")


def rows():
    """{system file name: its index row}"""
    out = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            out[m.group(1)] = line
    return out


def section_headings(text):
    out, fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
        elif not fence and line.startswith("## "):
            out.append(line[3:].strip())
    return out


class TestModSystemsIndex(unittest.TestCase):
    def test_every_system_file_has_one_row(self):
        files = sorted(p.name for p in SYSTEMS.glob("*.md"))
        self.assertGreater(len(files), 20)
        listed = [ROW.match(line).group(1) for line in INDEX.read_text(encoding="utf-8").splitlines() if ROW.match(line)]
        self.assertEqual(sorted(listed), files, "a system file with no index row, or a row for a missing file")

    def test_each_row_names_its_files_sections_in_order(self):
        for name, row in rows().items():
            listed = [s.strip() for s in row.rsplit("|", 2)[-2].split("<br>")]
            with self.subTest(file=name):
                self.assertEqual(listed, section_headings((SYSTEMS / name).read_text(encoding="utf-8")),
                                 "the row's last column lists the file's ## headings, in order, joined by <br>")

    def test_each_system_file_opens_with_a_title_and_a_link_back(self):
        for path in sorted(SYSTEMS.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            with self.subTest(file=path.name):
                self.assertTrue(lines[0].startswith("# "))
                self.assertIn("](../mod_systems.md)", lines[2])

    def test_relative_links_resolve(self):
        for path in [INDEX, *sorted(SYSTEMS.glob("*.md"))]:
            for target in LINK.findall(path.read_text(encoding="utf-8")):
                with self.subTest(file=path.name, link=target):
                    self.assertTrue((path.parent / target).exists())


if __name__ == "__main__":
    unittest.main()
