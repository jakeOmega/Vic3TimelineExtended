"""A company that lists one building in both `building_types` and
`extension_building_types`.

Extensions are the buildings an industry charter can add to a company's
roster, so an extension the roster already holds is a dead entry: the charter
has nothing to add. Airbus listed the aerospace industry in both.

Companies are judged on merged vanilla + mod data (vanilla from the committed
`vanilla_parsed/` snapshot), because most of the mod's extensions are
`INJECT:`ed into vanilla companies whose roster lives in vanilla.
"""
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser
from prestige_good_roster_audit import _names, _unwrap, load_state

ROOT = Path(__file__).resolve().parent


def roster_overlaps(companies: dict) -> dict:
    """{company: [building in both its roster and its extensions]}."""
    found = {}
    for name, entry in companies.items():
        body = _unwrap(entry)
        if not isinstance(body, dict):
            continue
        both = set(_names(body.get("building_types"))) & set(_names(body.get("extension_building_types")))
        if both:
            found[name] = sorted(both)
    return found


def _merged(mod_companies: str, vanilla_companies: str = "") -> dict:
    """Merged company data for a throwaway mod tree over parsed vanilla text."""
    tmp = tempfile.TemporaryDirectory()
    try:
        companies_dir = os.path.join(tmp.name, "common", "company_types")
        os.makedirs(companies_dir)
        with open(os.path.join(companies_dir, "test.txt"), "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(mod_companies))
        parser = ParadoxFileParser()
        vanilla = parser.parse_object(parser.tokenize("{" + vanilla_companies + "}"))[0]
        return load_state(tmp.name, vanilla_data={"Company Types": vanilla}).get_data("Company Types")
    finally:
        tmp.cleanup()


class CompanyRosterTests(unittest.TestCase):
    def test_no_company_lists_a_building_as_both_roster_and_extension(self):
        companies = load_state(str(ROOT)).get_data("Company Types") or {}
        self.assertGreater(len(companies), 300)
        self.assertEqual(roster_overlaps(companies), {},
                         "an extension the roster already holds is a dead entry; drop it from one list")

    def test_overlap_in_one_definition_is_found(self):
        companies = _merged("""
            company_m = {
                building_types = { building_a building_b }
                extension_building_types = { building_a building_c }
            }
        """)
        self.assertEqual(roster_overlaps(companies), {"company_m": ["building_a"]})

    def test_overlap_made_by_an_inject_is_found(self):
        companies = _merged(
            "INJECT:company_v = {\n\textension_building_types = { building_a }\n}\n",
            vanilla_companies="company_v = { building_types = { building_a building_b } }",
        )
        self.assertEqual(roster_overlaps(companies), {"company_v": ["building_a"]})

    def test_disjoint_lists_are_clean(self):
        companies = _merged("""
            company_m = {
                building_types = { building_a }
                extension_building_types = { building_b }
            }
        """)
        self.assertEqual(roster_overlaps(companies), {})


if __name__ == "__main__":
    unittest.main()
