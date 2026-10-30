# -*- coding: utf-8 -*-
"""Every modifier type the mod defines starts with a category word vanilla's types use.

The engine files a modifier type under a category read off its name's first word (country_,
state_, building_, ...). A name it can't file logs `Invalid category prefix for modifier <name>`
(modifier_types.cpp) at every load. The Grand Monuments policy types were named gm_monument_*
(GM-2, #1215) and logged five such lines a launch until they became country_gm_monument_*
(log triage, 2026-10-29). scripting_best_practices.md, "A Modifier Type's Name Starts With Its
Category".

Run: python3 -m unittest test_modifier_type_category_prefix -v
"""

import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
TYPES_DIR = os.path.join(REPO, "common", "modifier_type_definitions")
VANILLA_TYPES = os.path.join(REPO, "vanilla_parsed", "common", "modifier_types.json")
DEFINITION = re.compile(r"^(?:[A-Z_]+:)?([A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE)


def vanilla_categories():
    with open(VANILLA_TYPES, encoding="utf-8") as f:
        return {name.split("_", 1)[0] for name in json.load(f)}


def mod_type_names():
    for name in sorted(os.listdir(TYPES_DIR)):
        if name.endswith(".txt"):
            with open(os.path.join(TYPES_DIR, name), encoding="utf-8-sig") as f:
                for m in DEFINITION.finditer(f.read()):
                    yield name, m[1]


class TestModifierTypeCategoryPrefix(unittest.TestCase):
    def test_every_mod_modifier_type_starts_with_a_vanilla_category(self):
        categories = vanilla_categories()
        bad = [f"{path}: {name}" for path, name in mod_type_names()
               if name.split("_", 1)[0] not in categories]
        self.assertEqual(bad, [], "start the name with its category (country_, state_, building_, ...)")

    def test_the_check_sees_what_it_rejects(self):
        categories = vanilla_categories()
        self.assertIn("country", categories)
        self.assertNotIn("gm", categories)
        names = [m[1] for m in DEFINITION.finditer("REPLACE:state_x_add = {\n}\ngm_y_mult = {\n\tcolor = good\n}\n")]
        self.assertEqual(names, ["state_x_add", "gm_y_mult"])
        self.assertGreater(len(list(mod_type_names())), 900)


if __name__ == "__main__":
    unittest.main()
