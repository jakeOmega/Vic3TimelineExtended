"""Script finds a company headquarters by its building group, never by the template type.

The engine makes a building type for each company type, `building_<company type>`
(`building_company_basic_fabrics`, `building_regional_company_hbc` ...), from the two
headquarters templates in vanilla's `common/buildings/14_companies.txt`. So
`has_building = building_company_headquarter` and `is_building_type =
building_company_headquarter` match no headquarters in a game, silently: a 1890 save held 61
headquarters and no building of either template type, and the Map Room's Company Headquarters
map painted every state grey (2026-11-08). The groups hold: `is_building_group =
bg_company_headquarter` / `bg_company_regional_headquarter`, as vanilla's own count does
(`08_tsarpoints_buttons.txt`). docs/guides/scripting_best_practices.md has the background.

GUI files are not checked: vanilla's own `Building.IsBuildingType('building_company_headquarter')`
lines sit in the building panel, and the mod's overrides copy them as they are.
"""

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SCRIPT_GLOBS = ("common/**/*.txt", "events/**/*.txt")
_COMMENT = re.compile(r"#[^\n]*")
_TYPE_TEST = re.compile(
    r"\b(has_building|is_building_type)\s*=\s*(building_company_headquarter|building_company_regional_headquarter)\b"
)


def type_tests(root):
    """(path, line, text) of every headquarters test by template type under ``root``'s script folders."""
    found = []
    seen = set()
    for pattern in SCRIPT_GLOBS:
        for path in sorted(Path(root).glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for number, line in enumerate(text.split("\n"), 1):
                match = _TYPE_TEST.search(_COMMENT.sub("", line))
                if match:
                    found.append((path.relative_to(root).as_posix(), number, match.group(0)))
    return found


class CompanyHeadquartersTests(unittest.TestCase):
    def test_no_script_tests_a_headquarters_by_its_template_type(self):
        found = type_tests(ROOT)
        self.assertEqual(
            found, [],
            "test company headquarters with is_building_group = bg_company_headquarter (or "
            "bg_company_regional_headquarter), inside any_scope_building where a state is in scope: %s" % found,
        )

    def test_the_check_sees_the_forms_it_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "common", "scripted_triggers", "x.txt")
            path.parent.mkdir(parents=True)
            path.write_text(
                "a = { has_building = building_company_headquarter }\n"
                "b = { any_scope_building = { is_building_type = building_company_regional_headquarter } }\n"
                "# c = { has_building = building_company_headquarter }\n"
                "d = { any_scope_building = { is_building_group = bg_company_headquarter } }\n",
                encoding="utf-8-sig",
            )
            self.assertEqual([line for _, line, _ in type_tests(tmp)], [1, 2])


if __name__ == "__main__":
    unittest.main()
