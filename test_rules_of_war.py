"""The Rules of War law group (lawgroup_rules_of_war), one identity per law.

The 2026-10-09 redesign made each law best at one thing instead of a single
dial from Total War to Limited War: Total War mobilizes the nation, Traditional
keeps a free hand and a steady officer corps, War Crimes Forbidden governs
occupation, Humanitarian Regulations makes a trusted partner, Limited War keeps
wars small. What these checks pin, none of which the engine would report:

- every law keeps a modifier no sibling carries, so the group can't drift back
  into one dial;
- the default law has an upside, and no law can close a ministry (the Ministry
  of War law's cap is 3, Foreign Affairs' 2);
- the nuclear strike bans live on the laws as two registered booleans, the
  strike gates read the booleans, and the law descriptions say so;
- the AI weighs a war footing (ai_enact_weight_modifier: Total War for a
  serious war, back down at peace);
- the stance lists keep the new backers;
- social_tensions_events.7's reform option can actually appear.

No game install needed.
"""

import os
import re
import unittest

import ideology_modifications
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
GROUP = "lawgroup_rules_of_war"
TOTAL = "law_total_war"
TRADITIONAL = "law_traditional_rules_of_war"
WCF = "law_war_crimes_forbidden"
HUMANITARIAN = "law_humanitarian_regulations"
LIMITED = "law_limited_war"
LAWS_IN_GROUP = (TOTAL, TRADITIONAL, WCF, HUMANITARIAN, LIMITED)
STRATEGIC_BAN = "country_strategic_nuclear_strikes_forbidden_bool"
TACTICAL_BAN = "country_tactical_nuclear_strikes_forbidden_bool"

LAWS = os.path.join(REPO, "common", "laws", "extra_laws.txt")
NUCLEAR_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "nuclear_deterrence_triggers.txt")
ROW_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "rules_of_war_triggers.txt")
MODIFIER_TYPES = os.path.join(
    REPO, "common", "modifier_type_definitions", "nuclear_program_modifier_types.txt"
)
SOCIAL_EVENTS = os.path.join(REPO, "events", "social_tensions_events.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")


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


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    """The body of the first top-level `name = {` in `text`."""
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"{name} not found")
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]
    raise AssertionError(f"{name} is unbalanced")


def _loc():
    out = {}
    for fname in os.listdir(LOC_DIR):
        if not fname.endswith(".yml"):
            continue
        for line in _read(os.path.join(LOC_DIR, fname)).splitlines():
            m = re.match(r'^\s+([\w.]+):\d*\s+"(.*)"\s*$', line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


class LawIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = _parse(LAWS)
        cls.laws = {name: _body(data[name]) for name in LAWS_IN_GROUP}
        cls.modifiers = {
            name: {key: _body(value) for key, value in _body(law["modifier"]).items()}
            for name, law in cls.laws.items()
        }

    def test_all_five_laws_are_in_the_group(self):
        for name, law in self.laws.items():
            with self.subTest(law=name):
                self.assertEqual(_body(law["group"]), GROUP)

    def test_every_law_has_a_modifier_no_sibling_carries(self):
        # The old group was one dial at x1/x2/x3; a signature effect per law
        # keeps each one a choice of its own.
        for name, mods in self.modifiers.items():
            others = set()
            for other, other_mods in self.modifiers.items():
                if other != name:
                    others |= set(other_mods)
            with self.subTest(law=name):
                self.assertTrue(set(mods) - others, f"{name} has no signature modifier")

    def test_signatures(self):
        self.assertLess(float(self.modifiers[WCF]["country_radicals_from_conquest_mult"]), 0)
        self.assertGreater(float(self.modifiers[HUMANITARIAN]["unit_recovery_rate_add"]), 0)
        self.assertLess(float(self.modifiers[LIMITED]["unit_occupation_mult"]), 0)
        self.assertGreater(
            float(self.modifiers[TOTAL]["military_formation_mobilization_speed_mult"]), 0
        )

    def test_humanitarian_regulations_has_the_best_reputation(self):
        rep = {
            name: float(mods.get("country_diplomatic_reputation_add", 0))
            for name, mods in self.modifiers.items()
        }
        self.assertEqual(max(rep, key=rep.get), HUMANITARIAN)

    def test_limited_war_slows_escalation_most(self):
        key = "country_aggressor_diplomatic_play_escalation_weekly_mult"
        esc = {name: float(mods.get(key, 0)) for name, mods in self.modifiers.items()}
        self.assertEqual(min(esc, key=esc.get), LIMITED)

    def test_traditional_has_an_upside_and_no_malus(self):
        mods = self.modifiers[TRADITIONAL]
        self.assertLess(float(mods["unit_morale_loss_mult"]), 0)
        self.assertGreater(float(mods["unit_experience_gain_mult"]), 0)
        self.assertNotIn("state_pop_support_movement_anti_war_mult", mods)

    def test_no_law_cuts_a_ministry_cap_by_more_than_one(self):
        # law_ministry_of_war gives a cap of 3 and law_ministry_of_foreign_affairs
        # 2, so -1 always leaves at least one level.
        for name, mods in self.modifiers.items():
            for key, value in mods.items():
                if key.endswith("_max_investment_add"):
                    with self.subTest(law=name, modifier=key):
                        self.assertGreaterEqual(float(value), -1)

    def test_total_war_arrives_with_chemical_warfare(self):
        self.assertEqual(_body(self.laws[TOTAL]["unlocking_technologies"]), ["chemical_warfare"])

    def test_every_law_carries_an_ai_weight(self):
        for name, law in self.laws.items():
            with self.subTest(law=name):
                self.assertIn("ai_enact_weight_modifier", law)
                self.assertNotIn("ai_will_do", law)

    def test_the_ai_weights_a_war_footing(self):
        text = _strip_comments(_read(LAWS))
        total = _block(text, TOTAL)
        self.assertIn("te_row_serious_war = yes", total)
        for name in (TRADITIONAL, WCF, HUMANITARIAN, LIMITED):
            body = _block(text, name)
            with self.subTest(law=name):
                self.assertIn("has_law = law_type:law_total_war", body)
                self.assertIn("is_at_war = no", body)

    def test_serious_war_trigger_exists(self):
        text = _strip_comments(_read(ROW_TRIGGERS))
        body = _block(text, "te_row_serious_war")
        self.assertIn("is_at_war = yes", body)
        self.assertIn("rank_value:major_power", body)
        self.assertIn("nd_fighting_for_existence = yes", body)


class NuclearBanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = _parse(LAWS)
        cls.modifiers = {
            name: {key: _body(value) for key, value in _body(_body(data[name])["modifier"]).items()}
            for name in LAWS_IN_GROUP
        }
        cls.triggers = _strip_comments(_read(NUCLEAR_TRIGGERS))
        cls.loc = _loc()

    def test_bans_are_registered_booleans(self):
        types = _parse(MODIFIER_TYPES)
        for ban in (STRATEGIC_BAN, TACTICAL_BAN):
            body = _body(types[ban])
            with self.subTest(ban=ban):
                self.assertEqual(_body(body["boolean"]), "yes")
                self.assertEqual(_body(body["script_only"]), "yes")

    def test_which_laws_carry_the_bans(self):
        carriers = {
            ban: {name for name, mods in self.modifiers.items() if mods.get(ban) == "yes"}
            for ban in (STRATEGIC_BAN, TACTICAL_BAN)
        }
        self.assertEqual(carriers[STRATEGIC_BAN], {HUMANITARIAN, LIMITED})
        self.assertEqual(carriers[TACTICAL_BAN], {LIMITED})

    def test_strike_gates_read_the_booleans_not_the_laws(self):
        for gate, ban in (
            ("nd_war_law_permits_strategic_strike", STRATEGIC_BAN),
            ("nd_war_law_permits_tactical_strike", TACTICAL_BAN),
        ):
            body = _block(self.triggers, gate)
            with self.subTest(gate=gate):
                self.assertIn(f"modifier:{ban} = yes", body)
                self.assertNotIn("has_law", body)
                self.assertIn("nd_war_law_exception = yes", body)

    def test_exception_keeps_the_existential_war(self):
        body = _block(self.triggers, "nd_war_law_exception")
        self.assertIn("nd_fighting_for_existence = yes", body)
        self.assertIn("nd_covered_country_struck = yes", body)
        goals = _block(self.triggers, "nd_fighting_for_existence")
        for goal in ("annex_country", "make_protectorate", "te_reunify_country"):
            with self.subTest(goal=goal):
                self.assertIn(f"has_war_goal = {goal}", goals)

    def test_bans_are_localized(self):
        for ban in (STRATEGIC_BAN, TACTICAL_BAN):
            for key in (ban, f"{ban}_desc"):
                with self.subTest(key=key):
                    self.assertTrue(self.loc.get(key))

    def test_descriptions_name_the_bans(self):
        self.assertIn("strategic nuclear strikes", self.loc[f"{HUMANITARIAN}_desc"].lower())
        limited = self.loc[f"{LIMITED}_desc"].lower()
        self.assertIn("nuclear strike", limited)
        self.assertIn("tactical", limited)
        for name in (TOTAL, TRADITIONAL, WCF):
            with self.subTest(law=name):
                self.assertNotIn("forbidden unless", self.loc[f"{name}_desc"].lower())

    def test_no_power_bloc_principle_concept_for_the_plain_word(self):
        keys = [f"{name}_desc" for name in LAWS_IN_GROUP]
        keys += ["concept_rules_of_war_system_desc", "extra_law_events.11.a"]
        for key in keys:
            with self.subTest(key=key):
                self.assertNotIn("concept_power_bloc_principle", self.loc[key])


class StanceTests(unittest.TestCase):
    def test_lists_name_every_law(self):
        for ideology, groups in ideology_modifications.modifications.items():
            if GROUP in groups:
                with self.subTest(ideology=ideology):
                    self.assertEqual({law for law, _ in groups[GROUP]}, set(LAWS_IN_GROUP))

    def test_backers(self):
        stance = {
            ideology: dict(groups[GROUP])
            for ideology, groups in ideology_modifications.modifications.items()
            if GROUP in groups
        }
        for ideology in ("ideology_traditionalist", "ideology_theocrat"):
            with self.subTest(ideology=ideology):
                self.assertEqual(stance[ideology][TRADITIONAL], "strongly_approve")
        # Liberals back both humane statutes strongly; Limited War stays strongly
        # approved so their nuclear posture class (Limited War over Total War,
        # nd_stance_restraint_full) is unchanged.
        for ideology in ("ideology_liberal", "ideology_liberal_modern",
                         "ideology_market_liberal", "ideology_humanitarian"):
            with self.subTest(ideology=ideology):
                self.assertEqual(stance[ideology][HUMANITARIAN], "strongly_approve")
                self.assertEqual(stance[ideology][LIMITED], "strongly_approve")
        for ideology in ("ideology_pacifist", "ideology_anarchist"):
            with self.subTest(ideology=ideology):
                self.assertEqual(stance[ideology][HUMANITARIAN], "approve")
                self.assertEqual(stance[ideology][LIMITED], "strongly_approve")


class WarCrimeScandalTests(unittest.TestCase):
    """social_tensions_events.7 once required Total War or Traditional while its
    reform option required one of the humane laws, so the option never showed."""

    @classmethod
    def setUpClass(cls):
        text = _strip_comments(_read(SOCIAL_EVENTS))
        cls.event = _block(text, "social_tensions_events.7")

    def _laws_in(self, text):
        return set(re.findall(r"has_law = law_type:(\w+)", text))

    def test_fires_under_every_law_but_the_two_strictest(self):
        trigger = _block(self.event, "\ttrigger")
        self.assertEqual(self._laws_in(trigger), {HUMANITARIAN, LIMITED})
        self.assertIn("NOR", trigger)

    def test_reform_option_is_reachable(self):
        options = re.split(r"\n\toption = \{", self.event)[1:]
        reform = next(o for o in options if "social_tensions_events.7.c" in o)
        laws = self._laws_in(_block(reform, "\t\ttrigger"))
        self.assertEqual(laws, {TRADITIONAL, WCF})


if __name__ == "__main__":
    unittest.main()
