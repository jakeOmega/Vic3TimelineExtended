# -*- coding: utf-8 -*-
"""The Colonial Empire's Military Garrison angers the interest groups that
oppose colonial exploitation, not a fixed pair (#2060).

The garrison's country modifier used to carry `interest_group_ig_intelligentsia_
pol_str_mult` and `interest_group_ig_trade_unions_pol_str_mult`, whatever the
groups' leaders thought. The anger is now `colonial_garrison_ig_modifier`, added
by `colonial_garrison_ig_refresh` to each interest group whose stance on
`law_colonial_exploitation` is disapprove or worse (`sr_ig_anticolonial`, the
rule the space colonies' hold reads), at the programme's level, from the
entry's monthly pulse, and removed when the entry ends. These tests hold that
wiring, and its one call site.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def _flat(text):
    return " ".join(text.split())


STATIC = _strip(_raw("common", "static_modifiers", "extra_modifiers.txt"))
EFFECTS = _strip(_raw("common", "scripted_effects", "decolonization.txt"))
JE = _strip(_raw("common", "journal_entries", "je_colonial_empire.txt"))
TRIGGERS = _strip(_raw("common", "scripted_triggers", "sr_fleet_triggers.txt"))
IG_MODIFIER = "colonial_garrison_ig_modifier"
FIXED_PAIR = ("interest_group_ig_intelligentsia_pol_str_mult",
              "interest_group_ig_trade_unions_pol_str_mult")


class ModifierTest(unittest.TestCase):
    def test_the_country_modifier_names_no_fixed_group(self):
        body = _block(STATIC, "colonial_military_garrison_modifier")
        for field in FIXED_PAIR:
            self.assertNotIn(field, body)
        self.assertNotIn("interest_group_", body)

    def test_the_group_modifier_is_political_strength_only(self):
        fields = re.findall(r"(?m)^\s*(\w+) = (\S+)", _block(STATIC, IG_MODIFIER))
        self.assertEqual([f for f in fields if f[0] != "icon"],
                         [("interest_group_pol_str_mult", "-0.05")])

    def test_it_is_on_the_nation_tabs_interest_group_list(self):
        import sys
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_nation_tab
        self.assertEqual(gen_nation_tab.NOT_ON_COUNTRY.get(IG_MODIFIER), "interest groups")

    def test_it_has_a_name_and_a_description(self):
        for f, key in (("te_miscellaneous_l_english.yml", IG_MODIFIER),
                       ("te_concepts_l_english.yml", IG_MODIFIER + "_desc")):
            self.assertRegex(_raw("localization", "english", f), rf"(?m)^ {key}:0 \"[^\"]+\"")


class RuleTest(unittest.TestCase):
    def test_the_rule_is_the_space_colonies_stance_test(self):
        self.assertEqual(_flat(_block(TRIGGERS, "sr_ig_anticolonial")),
                         "law_stance = { law = law_type:law_colonial_exploitation value < neutral }")

    def test_the_refresh_reads_that_rule_and_nothing_fixed(self):
        refresh = _flat(_block(EFFECTS, "colonial_garrison_ig_refresh"))
        self.assertIn("limit = { sr_ig_anticolonial = yes }", refresh)
        self.assertNotIn("is_interest_group_type", refresh)
        self.assertNotIn("ig_intelligentsia", refresh)
        self.assertNotIn("ig_trade_unions", refresh)


class RefreshTest(unittest.TestCase):
    def test_it_removes_from_every_group_then_adds_at_the_programmes_scale(self):
        refresh = _flat(_block(EFFECTS, "colonial_garrison_ig_refresh"))
        off = refresh.index(f"remove_modifier = {IG_MODIFIER}")
        on = refresh.index(f"add_modifier = {{ name = {IG_MODIFIER}")
        self.assertLess(off, on)
        self.assertIn("limit = { colonial_garrison_level_value >= 1 }", refresh)
        self.assertIn("value = colonial_garrison_modifier_scale", refresh)
        self.assertIn(f"add_modifier = {{ name = {IG_MODIFIER} multiplier = local_var:colonial_garrison_ig_scale }}",
                      refresh)

    def test_one_call_site_in_the_monthly_pulse(self):
        callers = [os.path.join(root, f) for p in ("common", "events")
                   for root, _, files in os.walk(os.path.join(REPO, p))
                   for f in files if f.endswith(".txt")
                   and re.search(r"colonial_garrison_ig_refresh\s*=\s*yes",
                                 _strip(_raw(os.path.relpath(os.path.join(root, f), REPO))))]
        self.assertEqual([os.path.basename(c) for c in callers], ["je_colonial_empire.txt"])
        self.assertEqual(len(re.findall(r"colonial_garrison_ig_refresh\s*=\s*yes", JE)), 1)
        pulse = _block(JE, "on_monthly_pulse")
        self.assertIn("colonial_garrison_ig_refresh = yes", pulse)

    def test_only_the_refresh_adds_it(self):
        adders = [os.path.basename(os.path.join(root, f)) for p in ("common", "events")
                  for root, _, files in os.walk(os.path.join(REPO, p))
                  for f in files if f.endswith(".txt")
                  and f"name = {IG_MODIFIER}" in _strip(_raw(os.path.relpath(os.path.join(root, f), REPO)))]
        self.assertEqual(adders, ["decolonization.txt"])

    def test_the_entrys_end_removes_it(self):
        cleanup = _flat(_block(EFFECTS, "colonial_empire_je_cleanup_effect"))
        self.assertIn(f"limit = {{ has_modifier = {IG_MODIFIER} }} remove_modifier = {IG_MODIFIER}", cleanup)

    def test_the_level_ladder_is_the_programmes(self):
        values = _strip(_raw("common", "script_values", "colonial_empire_values.txt"))
        ladder = _flat(_block(values, "colonial_garrison_modifier_scale"))
        for share in ("value = 1", "value = 0.667", "value = 0.333"):
            self.assertIn(share, ladder)


if __name__ == "__main__":
    unittest.main()
