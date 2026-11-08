"""The mod's fix for vanilla's Caesaropapism lists, and the signal to remove it.

Vanilla names only law_state_religion in six law lists, and the engine doesn't
read the variant law_caesaropapism as its parent there (a Workshop player's
Russia, 2026-11-08). The mod INJECTs each list again with law_caesaropapism
added (common/production_methods/te_vanilla_caesaropapism_fix.txt,
common/laws/te_vanilla_caesaropapism_fix.txt).

Vanilla is read from the committed vanilla_parsed/ snapshot, so after a vanilla
patch (python3 vanilla_parsed.py build) this fails:
- when vanilla lists law_caesaropapism itself: delete the INJECT and its row in
  docs/vanilla/vanilla_known_bugs.md, "Vanilla bugs the mod fixes";
- when vanilla changes one of the lists otherwise: restate the new list.

Run: python3 -m unittest test_vanilla_caesaropapism_fix -v
"""

import json
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
PMS = ROOT / "common/production_methods/te_vanilla_caesaropapism_fix.txt"
LAWS = ROOT / "common/laws/te_vanilla_caesaropapism_fix.txt"
VANILLA = ROOT / "vanilla_parsed/common"
KNOWN_BUGS = ROOT / "docs/vanilla/vanilla_known_bugs.md"
VARIANT = "law_caesaropapism"

FIXED = [
    (PMS, "pms", "pm_state_urban_clergy", "unlocking_laws"),
    (PMS, "pms", "pm_free_urban_clergy", "disallowing_laws"),
    (PMS, "pms", "pm_secular_bureaucrats", "disallowing_laws"),
    (PMS, "pms", "pm_secular_academia", "disallowing_laws"),
    (LAWS, "laws", "law_private_schools", "disallowing_laws"),
    (LAWS, "laws", "law_public_schools", "disallowing_laws"),
]


def ours(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


def vanilla(kind):
    return json.loads((VANILLA / f"{kind}.json").read_text(encoding="utf-8"))


class CaesaropapismFixTest(unittest.TestCase):

    def test_caesaropapism_is_a_state_religion_variant(self):
        self.assertEqual(vanilla("laws")[VARIANT][1]["parent"], ["=", "law_state_religion"])

    def test_the_files_inject_exactly_the_fixed_lists(self):
        for path in (PMS, LAWS):
            expected = {"INJECT:" + name for p, _, name, _ in FIXED if p == path}
            self.assertEqual(set(ours(path)), expected)
            for name, value in ours(path).items():
                self.assertEqual(len(value[1]), 1, f"{name} injects only its list")

    def test_vanilla_still_leaves_the_variant_out(self):
        for _, kind, name, field in FIXED:
            with self.subTest(name=name):
                self.assertNotIn(VARIANT, vanilla(kind)[name][1][field][1],
                                 f"vanilla's {name} now lists {VARIANT}: delete the mod's INJECT of it and its row "
                                 "in vanilla_known_bugs.md")

    def test_each_list_is_vanillas_with_the_variant(self):
        for path, kind, name, field in FIXED:
            with self.subTest(name=name):
                injected = list(ours(path)["INJECT:" + name][1][field][1])
                base = vanilla(kind)[name][1][field][1]
                self.assertEqual(sorted(injected), sorted(base + [VARIANT]),
                                 f"vanilla's {name} {field} changed: restate it with {VARIANT} added")

    def test_the_fix_is_listed_with_the_vanilla_bugs_the_mod_fixes(self):
        doc = KNOWN_BUGS.read_text(encoding="utf-8")
        section = doc[doc.index("## Vanilla bugs the mod fixes"):]
        section = section[:section.index("\n## ", 1)]
        for path in (PMS, LAWS):
            self.assertIn(str(path.relative_to(ROOT)), section)


if __name__ == "__main__":
    unittest.main()
