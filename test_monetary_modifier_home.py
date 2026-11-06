# -*- coding: utf-8 -*-
"""Every managed monetary modifier is stripped on a change of home (#1427).

``te_monetary_settle_modifier_home`` (common/scripted_effects/
te_monetary_effects.txt) moves the managed modifiers when a country gains or
loses its Banking entry: it strips each from the country and the entry, and the
month's steps re-add them on the new home. A managed modifier its strip list
leaves out keeps its old copy, and the step that finds it missing on the new
home (``te_mon_mod_has`` looks only there) adds a second one, so the effect
applies twice until the next change of home. The engine logs nothing. The union
step's banking union, reserve and seigniorage were missed that way.

So: every name the managed helpers add (``te_mon_mod_add``,
``te_mon_mod_add_scaled``, ``te_monetary_apply_fx_one``) is in the strip list.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_monetary_effects.txt")
ADDERS = ("te_mon_mod_add", "te_mon_mod_add_scaled", "te_monetary_apply_fx_one")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth = 0
    for k in range(m.end() - 1, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():k]
    raise AssertionError(f"{name} is unbalanced")


def _managed_names():
    pattern = re.compile(r"\b(" + "|".join(ADDERS) + r")\s*=\s*\{\s*NAME\s*=\s*([A-Za-z0-9_]+)")
    names = set()
    for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True) + \
            glob.glob(os.path.join(REPO, "events", "*.txt")):
        for _adder, name in pattern.findall(_read(path)):
            names.add(name)
    return names


class ModifierHomeStripTests(unittest.TestCase):
    def test_every_managed_modifier_is_stripped(self):
        settle = _block(_read(EFFECTS), "te_monetary_settle_modifier_home")
        stripped = set(re.findall(r"te_mon_mod_strip\s*=\s*\{\s*NAME\s*=\s*([A-Za-z0-9_]+)", settle))
        managed = _managed_names()
        self.assertGreater(len(managed), 20, "the managed-add scan found too few names")
        missing = sorted(managed - stripped)
        self.assertEqual(missing, [], "managed modifiers the change-of-home strip leaves out: "
                         + ", ".join(missing))

    def test_the_union_modifiers_are_stripped(self):
        settle = _block(_read(EFFECTS), "te_monetary_settle_modifier_home")
        for name in ("te_mon_union_adopter", "te_mon_union_pressure", "te_mon_union_banking_union",
                     "te_mon_union_reserve", "te_mon_union_seigniorage"):
            self.assertIn(f"te_mon_mod_strip = {{ NAME = {name} }}", settle)


if __name__ == "__main__":
    unittest.main()
