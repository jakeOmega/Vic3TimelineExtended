# -*- coding: utf-8 -*-
"""Tradition of Free Elections under Anarchy.

The mod counts Anarchy as an electoral law: vanilla's tradition attaches to
it, no longer lowers the chance of enacting it, and comes back when Anarchy is
enacted, as it does for the four voting laws. Two pieces carry that:

- REPLACE:amendment_tradition_of_free_elections, a byte copy of vanilla's
  amendment with law_anarchy added to allowed_laws and the Anarchy enactment
  penalty removed. The copy test fails when the committed vanilla_parsed/
  snapshot drifts from it, so a vanilla change to the amendment is caught on
  the next snapshot rebuild instead of being silently overwritten.
- te_free_elections_inherit_under_anarchy, called from on_law_activated and
  once per country from the monthly pulse.

Run: python3 -m unittest test_free_elections_anarchy -v
"""

import glob
import json
import os
import re
import unittest

import vanilla_parsed
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
AMENDMENT = "amendment_tradition_of_free_elections"
AMENDMENT_FILE = os.path.join(REPO, "common", "amendments", "te_tradition_of_free_elections.txt")
EFFECTS_FILE = os.path.join(REPO, "common", "scripted_effects", "te_free_elections_effects.txt")
ON_ACTIONS_FILE = os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt")
VANILLA_AMENDMENTS = os.path.join(REPO, "vanilla_parsed", "common", "amendments.json")

ANARCHY_PENALTY = "country_enactment_success_chance_law_anarchy_add"


def _body(node):
    """The parser stores `key = { ... }` as ('=', body); unwrap it."""
    return node[1] if isinstance(node, tuple) else node


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _code(path):
    """Script text with comments stripped."""
    with open(path, encoding="utf-8-sig") as fh:
        return re.sub(r"#[^\n]*", "", fh.read())


def _block(text, name):
    """The body of the top-level `name = { ... }` block."""
    m = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class AmendmentCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _body(_parse(AMENDMENT_FILE)[f"REPLACE:{AMENDMENT}"])
        with open(VANILLA_AMENDMENTS, encoding="utf-8") as fh:
            cls.vanilla = _body(vanilla_parsed.decode(json.load(fh))[AMENDMENT])

    def test_anarchy_is_an_allowed_law(self):
        self.assertEqual(_body(self.mod["allowed_laws"]),
                         _body(self.vanilla["allowed_laws"]) + ["law_anarchy"])

    def test_only_the_anarchy_penalty_is_removed(self):
        vanilla = dict(_body(self.vanilla["modifier"]))
        self.assertIn(ANARCHY_PENALTY, vanilla, "vanilla dropped the line; re-copy the amendment")
        del vanilla[ANARCHY_PENALTY]
        self.assertEqual(_body(self.mod["modifier"]), vanilla)

    def test_everything_else_is_vanilla(self):
        self.assertEqual(sorted(self.mod), sorted(self.vanilla))
        for key in self.mod:
            if key in ("allowed_laws", "modifier"):
                continue
            with self.subTest(key=key):
                self.assertEqual(self.mod[key], self.vanilla[key])

    def test_no_other_mod_file_touches_the_amendment(self):
        # A second REPLACE or an INJECT elsewhere would win over, or be dropped
        # by, this one with no log line.
        pattern = re.compile(rf"^\S*{AMENDMENT}\s*=", re.M)
        for path in glob.glob(os.path.join(REPO, "common", "amendments", "*.txt")):
            if os.path.samefile(path, AMENDMENT_FILE):
                continue
            with self.subTest(path=os.path.basename(path)):
                self.assertIsNone(pattern.search(_code(path)))


class AnarchyInheritTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _code(EFFECTS_FILE)
        cls.on_actions = _code(ON_ACTIONS_FILE)

    def test_effect_attaches_only_to_anarchy_without_the_tradition(self):
        body = _block(self.effects, "te_free_elections_inherit_under_anarchy")
        self.assertIn("active_law:lawgroup_distribution_of_power ?=", body)
        self.assertIn("type = law_type:law_anarchy", body)
        self.assertIn(f"NOT = {{ has_amendment = amendment_type:{AMENDMENT} }}", body)
        # inherit_free_elections_effect reads scope:relevant_voting_law and
        # sponsors with PREV.ig:..., so it must run in the country, after the save.
        save = body.index("save_scope_as = relevant_voting_law")
        call = body.index("inherit_free_elections_effect = yes")
        self.assertLess(save, call)
        self.assertIn("owner = {", body[save:call])

    def test_hooks_are_wired(self):
        self.assertIn("te_free_elections_from_law_scope",
                      _block(self.on_actions, "on_law_activated"))
        self.assertIn("te_free_elections_country_pulse",
                      _block(self.on_actions, "on_monthly_pulse_country"))

    def test_law_hook_runs_for_anarchy(self):
        body = _block(self.on_actions, "te_free_elections_from_law_scope")
        self.assertIn("type = law_type:law_anarchy", body)
        self.assertIn("te_free_elections_inherit_under_anarchy = yes", body)

    def test_pulse_runs_once_per_country(self):
        # A standing re-attach would undo a repeal: free_elections_var outlives it.
        body = _block(self.on_actions, "te_free_elections_country_pulse")
        self.assertIn("NOT = { has_variable = te_free_elections_anarchy_checked }", body)
        self.assertIn("set_variable = te_free_elections_anarchy_checked", body)
        self.assertIn("te_free_elections_inherit_under_anarchy = yes", body)

    def test_files_have_one_bom(self):
        for path in (AMENDMENT_FILE, EFFECTS_FILE):
            with self.subTest(path=os.path.basename(path)):
                with open(path, "rb") as fh:
                    head = fh.read(6)
                self.assertTrue(head.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(head[3:].startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
