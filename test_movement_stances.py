"""Tests for movement_stances (#838): which movements back which laws."""
import os
import tempfile
import unittest

from mod_state import ModState

import movement_stances as mvs

MOVEMENTS = """\
movement_pacifist = {
	category = movement_category_ideological
	ideology = ideology_pacifist
	creation_trigger = {
		has_technology_researched = anti_war_movement
		NOT = { has_technology_researched = total_war_doctrine }
		NAND = { has_technology_researched = a_tech has_technology_researched = b_tech }
		OR = { has_technology_researched = pacifism has_law = law_type:law_limited_war }
	}
}
movement_modernizer = {
	category = movement_category_ideological
	ideology = ideology_modern_1
	on_weekly = {
		if = { limit = { always = yes } set_core_ideology = ideology_modern_2 }
	}
	creation_trigger = { }
}
movement_lost = {
	category = movement_category_cultural
	ideology = ideology_missing
}
"""

IDEOLOGIES = """\
ideology_pacifist = {
	lawgroup_rules_of_war = {
		law_total_war = strongly_disapprove
		law_limited_war = approve
	}
}
ideology_modern_1 = {
	lawgroup_rules_of_war = {
		law_limited_war = disapprove
		law_total_war = neutral
	}
}
ideology_modern_2 = {
	lawgroup_rules_of_war = {
		law_total_war = strongly_approve
	}
}
"""

LAWS = """\
law_total_war = { group = lawgroup_rules_of_war }
law_limited_war = { group = lawgroup_rules_of_war }
law_humane_war = { group = lawgroup_rules_of_war }
law_limited_war_variant = { group = lawgroup_rules_of_war parent = law_limited_war }
law_carrier = { group = lawgroup_rules_of_war }
law_privacy_a = { group = lawgroup_privacy }
law_privacy_b = { group = lawgroup_privacy }
"""


def _state(root):
    dirs = {}
    for et, sub, text in (
        ("Political Movements", "political_movements", MOVEMENTS),
        ("Ideologies", "ideologies", IDEOLOGIES),
        ("Laws", "laws", LAWS),
    ):
        d = os.path.join(root, sub)
        os.makedirs(d)
        with open(os.path.join(d, "x.txt"), "w", encoding="utf-8-sig") as fh:
            fh.write(text)
        dirs[et] = d
    return ModState({}, dirs)


class MovementStancesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        ms = _state(self.tmp.name)
        self.movements = ms.get_data("Political Movements")
        self.ideologies = ms.get_data("Ideologies")
        self.laws = ms.get_data("Laws")

    def stances(self, **kw):
        return mvs.lawgroup_stances("lawgroup_rules_of_war", self.movements, self.ideologies,
                                    self.laws, carriers={"law_carrier"}, **kw)

    def test_tech_gate_skips_negated_techs(self):
        row = mvs.movement_summary("movement_pacifist", self.movements["movement_pacifist"])
        self.assertEqual(row["tech_gate"], ["anti_war_movement", "pacifism"])
        self.assertEqual(row["creation_trigger_keys"], ["has_technology_researched", "NOT", "NAND", "OR"])

    def test_catalog_lists_set_core_ideology_and_unknown_ideologies(self):
        rows = {r["name"]: r for r in mvs.movement_catalog(self.movements, self.ideologies)}
        self.assertEqual(rows["movement_modernizer"]["ideology"], "ideology_modern_1")
        self.assertEqual(rows["movement_modernizer"]["alternate_ideologies"], ["ideology_modern_2"])
        self.assertEqual(rows["movement_lost"]["unknown_ideologies"], ["ideology_missing"])
        self.assertNotIn("unknown_ideologies", rows["movement_pacifist"])

    def test_variant_takes_parent_stance_and_unnamed_law_is_neutral(self):
        out = self.stances()
        pacifist = next(r for r in out["movements"] if r["movement"] == "movement_pacifist")
        self.assertEqual(pacifist["stances"]["law_limited_war_variant"], "approve")
        self.assertEqual(pacifist["stances"]["law_humane_war"], "neutral")
        # The variant reads its parent's explicit line, so it isn't implicit.
        self.assertEqual(pacifist["implicit_neutral"], ["law_carrier", "law_humane_war"])
        self.assertEqual(out["variants"], {"law_limited_war_variant": "law_limited_war"})

    def test_one_row_per_ideology_a_movement_can_hold(self):
        out = self.stances()
        rows = [(r["movement"], r["ideology"], r["via"]) for r in out["movements"]]
        self.assertEqual(rows, [
            ("movement_modernizer", "ideology_modern_1", "ideology"),
            ("movement_modernizer", "ideology_modern_2", "set_core_ideology"),
            ("movement_pacifist", "ideology_pacifist", "ideology"),
        ])

    def test_unbacked_laws_leave_out_carriers(self):
        out = self.stances()
        # total_war: modern_2 strongly approves; limited_war (+variant): pacifist approves.
        self.assertEqual(out["unbacked_laws"], ["law_humane_war"])
        self.assertEqual(out["carriers"], ["law_carrier"])
        self.assertNotIn("mode", out)

    def test_comparative_mode_lists_laws_rated_above_current(self):
        out = self.stances(current="law_total_war")
        self.assertEqual(out["mode"], "comparative")
        backs = {(r["movement"], r["ideology"]): r["backs"] for r in out["movements"]}
        self.assertEqual(backs[("movement_pacifist", "ideology_pacifist")],
                         ["law_carrier", "law_humane_war", "law_limited_war", "law_limited_war_variant"])
        self.assertEqual(backs[("movement_modernizer", "ideology_modern_2")], [])
        # modern_1 rates total_war neutral and limited_war disapprove.
        self.assertEqual(backs[("movement_modernizer", "ideology_modern_1")], [])
        self.assertEqual(out["unbacked_laws"], [])

    def test_current_outside_the_group_is_an_error(self):
        with self.assertRaises(ValueError):
            self.stances(current="law_privacy_a")

    def test_unknown_lawgroup_returns_none(self):
        self.assertIsNone(mvs.lawgroup_stances("lawgroup_nope", self.movements,
                                               self.ideologies, self.laws))

    def test_gaps(self):
        out = mvs.stance_gaps(self.movements, self.ideologies, self.laws, {"law_carrier"},
                              vanilla_lawgroups={"lawgroup_rules_of_war"})
        self.assertEqual(out["lawgroups_without_stance"], [
            {"lawgroup": "lawgroup_privacy", "origin": "mod",
             "laws": ["law_privacy_a", "law_privacy_b"]},
        ])
        self.assertEqual(out["unbacked_laws"], [
            {"lawgroup": "lawgroup_rules_of_war", "origin": "vanilla", "laws": ["law_humane_war"]},
        ])


class SnapshotTests(unittest.TestCase):
    """The committed snapshot carries vanilla's movements, and the mod's join
    them."""

    def test_vanilla_and_mod_movements_load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        ms, vanilla = mvs.load_state(here)
        self.assertIn("movement_modernizer", vanilla.get("Political Movements", {}))
        catalog = {r["name"]: r for r in mvs.movement_catalog(
            ms.get_data("Political Movements"), ms.get_data("Ideologies"))}
        self.assertIn("ideology_modernizer_movement_2", catalog["movement_modernizer"]["alternate_ideologies"])
        self.assertIn("movement_environmental", catalog)
        self.assertEqual([r["name"] for r in catalog.values() if r.get("unknown_ideologies")], [])


if __name__ == "__main__":
    unittest.main()
