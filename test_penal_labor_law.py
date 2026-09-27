"""Penal Labor Camps (law_penal_labor_camps), the Criminal Justice group's
authoritarian end.

What the engine would never report:

- An ideology with a stance on the other Criminal Justice laws but none on the
  camps is silently neutral on them, so an interest group that should oppose
  the camps doesn't. Every ideology with a stance on a Criminal Justice law
  must have one on the camps: in ideology_modifications.py (the input), in the
  generated common/ideologies/modified.txt, and in the hand-written mod
  ideologies (extra_ideologies.txt).
- unlocking_laws matches exact keys, so leaving out an Autocracy variant would
  lock Bakufu and Neo-Absolutism out of the law and make the consistency sweep
  treat their holders as violating it.
- The UN human-rights violator test lists the repressive laws by hand.

No game install needed.
"""

import glob
import os
import re
import unittest

import ideology_modifications
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
LAW = "law_penal_labor_camps"
GROUP = "lawgroup_criminal_justice"
SIBLINGS = (
    "law_punishment_focused_criminal_justice",
    "law_restorative_justice",
    "law_rehabilitation_focused_criminal_justice",
)
GATE = {
    "law_autocracy",
    "law_bakufu",
    "law_neo_absolutism",
    "law_single_party_state",
    "law_outlawed_dissent",
}
IDEOLOGY_FILES = sorted(glob.glob(os.path.join(REPO, "common", "ideologies", "*.txt")))
LAWS = os.path.join(REPO, "common", "laws", "extra_laws.txt")
CONSISTENCY = os.path.join(
    REPO, "common", "scripted_effects", "extra_law_consistency_generated.txt"
)
UN_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_regime_triggers.txt")
LAW_LOC = os.path.join(REPO, "localization", "english", "te_laws_l_english.yml")


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _body(node):
    """The parser stores `key = { ... }` as ('=', body); unwrap it."""
    return node[1] if isinstance(node, tuple) else node


def _read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _slice(path, start_marker, end_marker):
    """The text of `path` from `start_marker` to the next `end_marker`."""
    text = _read(path)
    start = text.index(start_marker)
    return text[start : text.index(end_marker, start + len(start_marker))]


def _script_ideology_stances():
    """{(file, ideology key): {law: stance}} for every Criminal Justice block in
    the mod's ideology files, REPLACE:/INJECT: prefixes kept in the key."""
    out = {}
    for path in IDEOLOGY_FILES:
        for key, node in _parse(path).items():
            body = _body(node)
            if not isinstance(body, dict) or GROUP not in body:
                continue
            block = _body(body[GROUP])
            out[(os.path.basename(path), key)] = {
                law: _body(stance) for law, stance in block.items()
            }
    return out


class IdeologyStanceTests(unittest.TestCase):
    def test_every_criminal_justice_list_stances_the_camps(self):
        for ideology, groups in ideology_modifications.modifications.items():
            pairs = dict(groups.get(GROUP, ()))
            if any(law in pairs for law in SIBLINGS):
                with self.subTest(ideology=ideology):
                    self.assertIn(LAW, pairs)

    def test_every_criminal_justice_block_stances_the_camps(self):
        stances = _script_ideology_stances()
        self.assertTrue(stances, "no Criminal Justice ideology block found")
        for where, block in stances.items():
            if any(law in block for law in SIBLINGS):
                with self.subTest(where=where):
                    self.assertIn(LAW, block)

    def test_generated_file_is_current(self):
        generated = {
            key.split(":", 1)[-1]: block
            for (fname, key), block in _script_ideology_stances().items()
            if fname == "modified.txt"
        }
        for ideology, groups in ideology_modifications.modifications.items():
            pairs = dict(groups.get(GROUP, ()))
            if LAW in pairs:
                with self.subTest(ideology=ideology):
                    self.assertEqual(generated.get(ideology, {}).get(LAW), pairs[LAW])

    def test_camps_never_outrank_the_ordinary_prison_for_its_backers(self):
        # A regressive group must prefer Punishment-Focused to the camps, or it
        # would push to enact them on its own. Only the ideologies that
        # strongly approve the camps (fascist, totalitarian) should.
        order = ["strongly_disapprove", "disapprove", "neutral", "approve", "strongly_approve"]
        for where, block in _script_ideology_stances().items():
            punishment = block.get("law_punishment_focused_criminal_justice")
            camps = block.get(LAW)
            if punishment in ("approve", "strongly_approve") and camps:
                with self.subTest(where=where):
                    self.assertLessEqual(order.index(camps), order.index(punishment))
            if punishment in ("disapprove", "strongly_disapprove"):
                with self.subTest(where=where):
                    self.assertEqual(camps, "strongly_disapprove")


class LawDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        laws = _parse(LAWS)
        cls.law = _body(laws[LAW])
        cls.siblings = {name: _body(laws[name]) for name in SIBLINGS}

    def test_group(self):
        self.assertEqual(_body(self.law["group"]), GROUP)

    def test_gate_lists_autocracy_variants(self):
        self.assertEqual(set(_body(self.law["unlocking_laws"])), GATE)

    def test_tech(self):
        self.assertEqual(_body(self.law["unlocking_technologies"]), ["mass_surveillance"])

    def test_least_progressive_in_group(self):
        own = float(_body(self.law["progressiveness"]))
        for name, sibling in self.siblings.items():
            with self.subTest(sibling=name):
                self.assertLess(own, float(_body(sibling.get("progressiveness", ("=", "0")))))

    def test_extractive_boost_is_small_and_flat(self):
        # Flat by design: a plain modifier value, never scripted, and small.
        modifier = _body(self.law["modifier"])
        throughput = {
            key: float(_body(value))
            for key, value in modifier.items()
            if key.endswith("_throughput_add")
        }
        self.assertEqual(
            set(throughput),
            {
                "building_group_bg_mining_throughput_add",
                "building_group_bg_logging_throughput_add",
                "building_group_bg_plantations_throughput_add",
                "building_group_bg_rubber_throughput_add",
            },
        )
        for key, value in throughput.items():
            with self.subTest(modifier=key):
                self.assertGreater(value, 0)
                self.assertLessEqual(value, 0.05)

    def test_costs_legitimacy(self):
        self.assertLess(float(_body(_body(self.law["modifier"])["country_legitimacy_base_add"])), 0)

    def test_consistency_falls_back_to_punishment_focused(self):
        text = _read(CONSISTENCY)
        start = text.index(f"te_fix_inconsistent_{GROUP} = {{")
        block = text[start : text.index("\n}\n", start)]
        self.assertIn(f"has_law = law_type:{LAW}", block)
        for gate in GATE:
            with self.subTest(gate=gate):
                self.assertIn(f"has_law = law_type:{gate}", block)
        self.assertIn("activate_law = law_type:law_punishment_focused_criminal_justice", block)
        self.assertIn(f"te_fix_inconsistent_{GROUP} = yes", text)

    def test_loc(self):
        text = _read(LAW_LOC)
        for key in (LAW, f"{LAW}_desc"):
            with self.subTest(key=key):
                self.assertRegex(text, rf"(?m)^ {key}:0 \"[^\"]+\"$")
        self.assertNotIn("[b]", text)


class HumanRightsTests(unittest.TestCase):
    def test_violator_test_lists_the_camps_beside_outlawed_dissent(self):
        text = _read(UN_TRIGGERS)
        start = text.index("un_regime_human_rights_violator = {")
        block = text[start : text.index("\n}\n", start)]
        self.assertIn("has_law = law_type:law_outlawed_dissent", block)
        self.assertIn(f"has_law = law_type:{LAW}", block)

    def test_every_outlawed_dissent_weight_in_un_human_rights_code_has_a_camps_twin(self):
        # The human-rights vote lean, refusal and withdrawal weights read
        # Outlawed Dissent; the camps must weigh the same wherever it does.
        # Each file is cut to its human-rights block, so an Outlawed Dissent
        # check added elsewhere in these files for another reason doesn't count.
        blocks = {
            "un_dossier_values.txt (human-rights lean)": _slice(
                os.path.join(REPO, "common", "script_values", "un_dossier_values.txt"),
                "has_tag = un_topic_human_rights } }",
                "\telse_if = {",
            ),
            "un_events.txt (un_events.3 option c)": _slice(
                os.path.join(REPO, "events", "un_events.txt"),
                "name = un_events.3.c",
                "custom_tooltip",
            ),
            "un_buttons.txt (withdraw from human rights)": _slice(
                os.path.join(REPO, "common", "scripted_buttons", "un_buttons.txt"),
                "un_withdraw_human_rights_button = {",
                "\n}\n",
            ),
        }
        for where, block in blocks.items():
            dissent = re.findall(r"has_law = law_type:law_outlawed_dissent \}\s*add = (-?\d+)", block)
            camps = re.findall(rf"has_law = law_type:{LAW} \}}\s*add = (-?\d+)", block)
            with self.subTest(block=where):
                self.assertTrue(dissent, "no Outlawed Dissent weight found")
                self.assertEqual(camps, dissent)


class CulturalHegemonyTests(unittest.TestCase):
    def test_hegemonic_pressure_never_picks_the_camps(self):
        # cultural_hegemony.16.a adopts the hegemon's law with activate_law,
        # which skips the camps' gate. Each place the event scans the Criminal
        # Justice group must exclude the camps: the outer trigger (or the event
        # fires with no valid pick), tier 2's trigger and its random pick.
        text = _slice(
            os.path.join(REPO, "events", "cultural_hegemony_events.txt"),
            "cultural_hegemony.16 = {",
            "\n}\n",
        )
        scans = text.count("is_same_law_group_as = law_type:law_punishment_focused_criminal_justice")
        self.assertEqual(scans, 3)
        self.assertEqual(text.count(f"NOT = {{ law_type = law_type:{LAW} }}"), scans)

if __name__ == "__main__":
    unittest.main()
