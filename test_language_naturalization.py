"""Language Requirement for Naturalization's migration restrictiveness (#1384).

Restrictiveness is an acceptance threshold: a pop whose acceptance is below the
country's total can't migrate there. Under each citizenship law the amendment
allows, a culture sharing no language, heritage or tradition sits at the law's
floor. The amendment's figure must clear the strictest law's floor (National
Supremacy, where it bars every such culture) and stay below the next one's
(Cultural Exclusion, where it bars only pops carrying penalties), so the effect
is graded by law. At 5 it cleared none of them. No game install needed.
"""

import os
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
AMENDMENTS = os.path.join(REPO, "common", "amendments", "extra_amendments.txt")
LAWS = os.path.join(REPO, "common", "laws", "modified.txt")
AMENDMENT = "amendment_language_naturalization_requirement"


def _body(node):
    return node[1] if isinstance(node, tuple) else node


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _law(data, name):
    for key in (name, f"REPLACE:{name}", f"INJECT:{name}"):
        if key in data:
            return _body(data[key])
    raise AssertionError(f"{name} not found in modified.txt")


class LanguageNaturalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        amendment = _body(_parse(AMENDMENTS)[AMENDMENT])
        cls.allowed = list(_body(amendment["allowed_laws"]))
        modifier = _body(amendment["modifier"])
        cls.restrictiveness = float(_body(modifier["country_migration_restrictiveness_add"]))
        laws = _parse(LAWS)
        cls.floor = {}
        for name in cls.allowed:
            law_mod = _body(_law(laws, name)["modifier"])
            cls.floor[name] = sum(
                float(_body(law_mod.get(key, ("=", "0"))))
                for key in (
                    "country_acceptance_no_shared_language_trait_add",
                    "country_acceptance_no_shared_heritage_trait_add",
                    "country_acceptance_no_shared_tradition_trait_add",
                )
            )

    def test_allowed_laws(self):
        self.assertEqual(
            sorted(self.allowed),
            ["law_cultural_exclusion", "law_multicultural", "law_national_supremacy"],
        )

    def test_floors(self):
        self.assertEqual(self.floor["law_national_supremacy"], 20)
        self.assertEqual(self.floor["law_cultural_exclusion"], 40)
        self.assertEqual(self.floor["law_multicultural"], 60)

    def test_bars_the_strictest_floor_only(self):
        # Strictly above: a pop at the threshold is not "below" it.
        self.assertGreater(self.restrictiveness, self.floor["law_national_supremacy"])
        self.assertLess(self.restrictiveness, self.floor["law_cultural_exclusion"])


if __name__ == "__main__":
    unittest.main()
