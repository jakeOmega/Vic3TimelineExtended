"""Assimilation cultures: the define, the game rule, the two modifier types and the law lines.

Design: docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md. A pop does not assimilate
into a culture of another heritage group by the engine: one define makes that so for every game, and
a yearly scripted pass (test_assimilation_cultures_pass.py) does the work under a three-setting rule.

- **The define.** ``ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP = yes``. The define it replaced,
  ``ALLOW_ASSIMILATION_ACROSS_HERITAGES``, left the game in 1.12; a line naming it must not come back.
- **The rule** ``assimilation_cultures_rule``: Hybrid Cultures, Unrestricted (the default in the release
  that adds it) and None. Script reads it only through ``te_hc_mode_hybrid`` and ``te_hc_mode_none``,
  each a positive test of its own setting, so a game that names no setting (one begun before the rule)
  takes the Unrestricted branch. The hybrid test also asks that the sentinel hybrid exists: a game begun
  before the hybrid cultures were added has no object for them.
- **The laws.** ``country_cross_heritage_assimilation_add`` is the share of the normal rate at which a
  pop joins a culture of another heritage group: nothing on Natural Form, 50% on Licensed Modification,
  100% on the other three Bodily Autonomy laws. Ancestral Citizenship (``law_ethnostate``) carries
  ``country_cross_heritage_assimilation_blocked_bool``, which stops that under every setting.

Run: python3 -m pytest test_assimilation_cultures_rule.py
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFINES = ROOT / "common/defines/extra_defines.txt"
RULES = ROOT / "common/game_rules/extra_game_rules.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_assimilation_culture_triggers.txt"
TYPES = ROOT / "common/modifier_type_definitions/te_assimilation_culture_modifier_types.txt"
BODILY = ROOT / "common/laws/te_bodily_autonomy_laws.txt"
CITIZENSHIP = ROOT / "common/laws/modified.txt"
LOC_DIR = ROOT / "localization/english"

RULE = "assimilation_cultures_rule"
SETTINGS = ("assimilation_cultures_hybrid", "assimilation_cultures_unrestricted", "assimilation_cultures_none")
SENTINEL = "hc_anglophone_african"
SHARE = "country_cross_heritage_assimilation_add"
BLOCKED = "country_cross_heritage_assimilation_blocked_bool"
LAW_SHARES = {
    "law_licensed_modification": "0.5",
    "law_morphological_freedom": "1",
    "law_clade_citizenship": "1",
    "law_prescribed_form": "1",
}


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def code(path):
    return re.sub(r"#[^\n]*", "", read(path))


def braced(text, header):
    """The body of the first block whose opening line matches `header` (a regex ending in `{`)."""
    m = re.search(header, text, re.M)
    assert m, header
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def words(text):
    return " ".join(text.split())


def loc():
    out = {}
    for path in sorted(LOC_DIR.glob("*.yml")):
        for line in read(path).splitlines():
            m = re.match(r'\s+([\w.]+):\d* "(.*)"\s*$', line)
            if m:
                out.setdefault(m.group(1), m.group(2))
    return out


class DefineTest(unittest.TestCase):
    def test_the_define_requires_the_heritage_group(self):
        pops = braced(code(DEFINES), r"^NPops\s*=\s*\{")
        self.assertRegex(pops, r"(?m)^\s*ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP\s*=\s*yes\b")
        # The stricter define would stop a Pole assimilating in Germany (spec, Approaches 4).
        self.assertNotIn("ALLOW_ASSIMILATION_REQUIRE_HERITAGE_TRAIT", pops)

    def test_the_define_the_game_dropped_is_not_named(self):
        self.assertNotIn("ALLOW_ASSIMILATION_ACROSS_HERITAGES", read(DEFINES))


class RuleTest(unittest.TestCase):
    def test_the_rule_has_three_settings_and_defaults_to_unrestricted(self):
        rule = braced(code(RULES), rf"^{RULE}\s*=\s*\{{")
        self.assertRegex(rule, r"default\s*=\s*assimilation_cultures_unrestricted\b")
        found = re.findall(r"(?m)^\s*(\w+)\s*=\s*\{", rule)
        self.assertEqual(sorted(found), sorted(SETTINGS))
        for setting in SETTINGS:
            with self.subTest(setting=setting):
                self.assertEqual(words(braced(rule, rf"^\s*{setting}\s*=\s*\{{")), f"flag = {setting}")

    def test_each_mode_trigger_is_a_positive_test_of_its_own_setting(self):
        text = code(TRIGGERS)
        hybrid = words(braced(text, r"^te_hc_mode_hybrid\s*=\s*\{"))
        none = words(braced(text, r"^te_hc_mode_none\s*=\s*\{"))
        self.assertEqual(hybrid, f"has_game_rule = assimilation_cultures_hybrid exists = cu:{SENTINEL}")
        self.assertEqual(none, "has_game_rule = assimilation_cultures_none")

    def test_nothing_tests_the_unrestricted_setting(self):
        # Unrestricted is "neither of the other two", so that a game naming no setting lands there.
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            if path == RULES:
                continue
            self.assertNotRegex(code(path), r"has_game_rule\s*=\s*assimilation_cultures_unrestricted", path.name)

    def test_no_other_file_reads_the_rule(self):
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            if path == TRIGGERS:
                continue
            self.assertNotRegex(code(path), r"has_game_rule\s*=\s*assimilation_cultures_", path.name)

    def test_the_rule_and_its_settings_are_named(self):
        text = loc()
        self.assertEqual(text.get(f"rule_{RULE}"), "Assimilation Across Heritages")
        names = {
            "assimilation_cultures_hybrid": "Hybrid Cultures",
            "assimilation_cultures_unrestricted": "Unrestricted",
            "assimilation_cultures_none": "None",
        }
        for setting, name in names.items():
            with self.subTest(setting=setting):
                self.assertEqual(text.get(f"setting_{setting}"), name)
                self.assertTrue(text.get(f"setting_{setting}_desc"))


class LawTest(unittest.TestCase):
    def test_the_law_lines(self):
        text = code(BODILY)
        for law, share in LAW_SHARES.items():
            with self.subTest(law=law):
                modifier = braced(braced(text, rf"^{law}\s*=\s*\{{"), r"^\s*modifier\s*=\s*\{")
                self.assertRegex(modifier, rf"(?m)^\s*{SHARE}\s*=\s*{re.escape(share)}\s*$")

    def test_natural_form_carries_nothing(self):
        natural = braced(code(BODILY), r"^law_natural_form\s*=\s*\{")
        # no modifier block (its ai_enact_weight_modifier is the AI's weight, #1877)
        self.assertNotRegex(natural, r"(?m)^\s*modifier\s*=")
        self.assertNotIn(SHARE, natural)

    def test_no_other_law_opens_the_crossing(self):
        # Four carriers. A fifth source is a design decision: add it here with its reason.
        carriers = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if path == TYPES:
                continue
            carriers += [path.name] * len(re.findall(rf"(?<!modifier:)\b{SHARE}\s*=", code(path)))  # a line that grants it, not a read
        self.assertEqual(carriers, [BODILY.name] * 4)

    def test_ancestral_citizenship_blocks_the_crossing(self):
        law = braced(code(CITIZENSHIP), r"^REPLACE:law_ethnostate\s*=\s*\{")
        modifier = braced(law, r"^\s*modifier\s*=\s*\{")
        self.assertRegex(modifier, rf"(?m)^\s*{BLOCKED}\s*=\s*yes\s*$")

    def test_only_ancestral_citizenship_blocks_it(self):
        carriers = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            if path == TYPES:
                continue
            carriers += [path.name] * len(re.findall(rf"(?<!modifier:)\b{BLOCKED}\s*=", code(path)))  # a line that grants it, not a read
        self.assertEqual(carriers, [CITIZENSHIP.name])


class ModifierTypeTest(unittest.TestCase):
    def test_both_modifier_types_are_script_only(self):
        text = code(TYPES)
        share = words(braced(text, rf"^{SHARE}\s*=\s*\{{"))
        blocked = words(braced(text, rf"^{BLOCKED}\s*=\s*\{{"))
        self.assertIn("script_only = yes", share)
        self.assertIn("percent = yes", share)
        self.assertIn("script_only = yes", blocked)
        self.assertIn("boolean = yes", blocked)

    def test_both_are_named_and_described(self):
        text = loc()
        for key in (SHARE, BLOCKED):
            with self.subTest(key=key):
                self.assertTrue(text.get(key))
                self.assertTrue(text.get(f"{key}_desc"))

    def test_the_share_says_where_it_acts(self):
        # The line does nothing under Unrestricted, and a law's tooltip shows it under every setting.
        desc = loc()[f"{SHARE}_desc"]
        self.assertIn("$setting_assimilation_cultures_hybrid$", desc)
        self.assertIn("$setting_assimilation_cultures_none$", desc)


if __name__ == "__main__":
    unittest.main()
