# -*- coding: utf-8 -*-
"""No modifier takes authority away with a negative country_authority_add (owner, 2026-10-21).

A negative add lowers *produced* authority, and once that reaches zero the penalties for using more
authority than the country has stop applying, so a heavy enough drain stops hurting a low-authority
country. It is also scaled by country_authority_mult, so the same modifier bites harder the more
multiplier a country has. Authority a modifier takes is a country_authority_cost_add, which counts as
usage and is flat. A positive country_authority_add (a law, institution or building that grants
capacity) is fine. scripting_best_practices.md, "Authority/Bureaucracy/Influence Costs".

Run: python3 -m unittest test_authority_cost_modifiers -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
SCANNED = ("common", "events", "gui")
NEGATIVE_ADD = re.compile(r"\bcountry_authority_add\s*=\s*-")
ANY_ADD = re.compile(r"\bcountry_authority_add\s*=")


def _scripts():
    for top in SCANNED:
        for root, _, names in os.walk(os.path.join(REPO, top)):
            for name in sorted(names):
                if name.endswith((".txt", ".gui")):
                    yield os.path.join(root, name)


def _code_lines(path):
    """(line number, text) for each line of the file with its comment cut off."""
    with open(path, encoding="utf-8-sig") as f:
        for number, line in enumerate(f, 1):
            yield number, line.split("#", 1)[0]


class NoNegativeAuthorityAddTests(unittest.TestCase):
    def test_the_pattern_reads_a_negative_add_and_only_that(self):
        for text in ("country_authority_add = -50", "\tcountry_authority_add=-3", "country_authority_add = -0.5"):
            self.assertTrue(NEGATIVE_ADD.search(text), text)
        for text in ("country_authority_add = 50", "country_authority_cost_add = 50", "country_authority_cost_add = -750"):
            self.assertFalse(NEGATIVE_ADD.search(text), text)

    def test_the_scan_reads_the_mods_positive_adds(self):
        """A path error would pass the next test with nothing scanned."""
        found = sum(1 for path in _scripts() for _, line in _code_lines(path) if ANY_ADD.search(line))
        self.assertGreater(found, 50)

    def test_no_script_takes_authority_with_a_negative_country_authority_add(self):
        found = [f"{os.path.relpath(path, REPO)}:{number}: {line.strip()}"
                 for path in _scripts() for number, line in _code_lines(path) if NEGATIVE_ADD.search(line)]
        self.assertEqual(found, [], "use country_authority_cost_add = <N> (positive) for an authority cost")


if __name__ == "__main__":
    unittest.main()
