"""Guard training injection, engine references and scaling across barracks sizes."""

import unittest
from pathlib import Path

import vanilla_parsed
from mod_state import VANILLA_COMMON_DIRS, ModState
from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
METHODS = ROOT / "common/production_methods/te_barracks_training.txt"


class BarracksTrainingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = vanilla_parsed.load().data
        categories = ("PMs", "PM Groups", "Buildings", "Technologies", "Goods",
                      "Laws", "Modifier Types")
        mod = {key: str(ROOT / "common" / VANILLA_COMMON_DIRS[key])
               for key in categories}
        cls.state = ModState({key: "/nonexistent" for key in categories}, mod,
                             vanilla_data=cls.vanilla)
        # Vanilla icons are supplied by the game; CI omits the mod's gfx tree.
        cls.known_textures = {
            entry[1]["texture"][1]
            for category in ("PMs", "Technologies")
            for entry in cls.vanilla[category].values()
            if "texture" in entry[1]
        }
        cls.known_textures.update(
            entry[1]["texture"][1]
            for entry in cls.state.get_data("Technologies").values()
            if "texture" in entry[1]
        )
        parser = ParadoxFileParser()
        parser.parse_file(str(METHODS))
        cls.methods = parser.data

    def test_training_appends_without_changing_vanilla_or_conscription(self):
        groups = self.state.get_data("PM Groups")
        before = self.vanilla["PM Groups"]["pmg_training"][1]
        after = groups["pmg_training"][1]
        self.assertEqual(after["production_methods"][1],
                         before["production_methods"][1] + list(self.methods))
        self.assertEqual(after["ai_selection"], before["ai_selection"])
        self.assertEqual(groups["pmg_training_conscription"],
                         self.vanilla["PM Groups"]["pmg_training_conscription"])
        barracks = self.state.get_data("Buildings")["building_barrack"][1]
        self.assertIn("pmg_training", barracks["production_method_groups"][1])

    def test_references_exist_and_ratios_use_unit_manpower(self):
        self.assertFalse(self.state.parse_failures)
        goods = self.state.get_data("Goods")
        types = self.state.get_data("Modifier Types")
        for key, (_, method) in self.methods.items():
            with self.subTest(method=key):
                for tech in method["unlocking_technologies"][1]:
                    technology = self.state.get_data("Technologies")[tech][1]
                    era = int(technology["era"][1].removeprefix("era_"))
                    self.assertGreaterEqual(era, 6, "new training belongs in mod eras")
                for law in method["disallowing_laws"][1]:
                    self.assertIn(law, self.state.get_data("Laws"))
                self.assertIn("law_warrior_caste", method["disallowing_laws"][1])
                ratios = method["profession_ratio"][1]
                self.assertEqual(set(ratios), {"soldiers", "officers"})
                self.assertEqual(sum(float(v[1]) for v in ratios.values()), 100)
                for target in ("building_modifiers", "state_modifiers"):
                    for _, block in method.get(target, ["=", {}])[1].values():
                        for modifier in block:
                            self.assertFalse(modifier.startswith("building_employment_"))
                            if modifier.startswith("goods_input_"):
                                self.assertIn(modifier[len("goods_input_"):-len("_add")], goods)
                            else:
                                self.assertIn(modifier, types)
                self.assertIn(method["texture"][1], self.known_textures)

    def test_no_unverified_unit_effects_or_countrywide_spillover(self):
        for key, (_, method) in self.methods.items():
            with self.subTest(method=key):
                self.assertNotIn("country_modifiers", method)
                for target in ("building_modifiers", "state_modifiers"):
                    for scaling, (_, modifiers) in method.get(target, ["=", {}])[1].items():
                        for modifier in modifiers:
                            self.assertFalse(modifier.startswith("unit_"),
                                             "unit propagation from barracks is unverified")
                            if modifier.startswith("goods_input_"):
                                self.assertEqual(target, "building_modifiers")
                                self.assertEqual(scaling, "workforce_scaled")

    def test_state_spillover_scales_with_staffing_and_stays_small(self):
        sources = []
        for key, (_, method) in self.methods.items():
            state = method.get("state_modifiers", ["=", {}])[1]
            if not state:
                continue
            sources.append(key)
            self.assertEqual(set(state), {"workforce_scaled"})
            modifiers = state["workforce_scaled"][1]
            self.assertEqual(set(modifiers), {"state_pop_qualifications_mult"})
            value = float(modifiers["state_pop_qualifications_mult"][1])
            self.assertGreater(value, 0)
            # At 100 staffed barracks levels, at most one scholastic university's boost.
            university = self.vanilla["PMs"]["pm_scholastic_education"][1]
            baseline = university["state_modifiers"][1]["workforce_scaled"][1]
            self.assertLessEqual(value * 100, float(baseline["state_pop_qualifications_mult"][1]))
        self.assertEqual(sources, ["pm_te_cadre_training"])


if __name__ == "__main__":
    unittest.main()
