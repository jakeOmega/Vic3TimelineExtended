"""gen_covert_tech_theft: amounts, technology catalog, rendered guards, committed output.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_covert_tech_theft as gen  # noqa: E402

LIVE = gen.Constants(share=Decimal("0.05"), full=Decimal("2"), pri2=Decimal("1.35"), pri3=Decimal("1.6"))


class AmountTest(unittest.TestCase):
    def test_era_7_amounts(self):
        self.assertEqual(gen.amounts(65000, LIVE), [3250, 4388, 5200, 6500, 8775, 10400])

    def test_half_rounds_up(self):
        # 17,500 x 0.05 x 2.7 = 2,362.5
        self.assertEqual(gen.amounts(17500, LIVE)[4], 2363)


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.catalog = gen.tech_catalog(cls.state)
        cls.by_key = {tech.key: tech for tech in cls.catalog}

    def test_reads_live_constants(self):
        self.assertEqual(gen.read_constants(self.state), LIVE)

    def test_era_costs(self):
        costs = gen.read_era_costs(ROOT)
        self.assertEqual(sorted(costs), list(range(1, 13)))
        self.assertEqual((costs[1], costs[7], costs[12]), (7500, 65000, 2000000))

    def test_categories_and_eras(self):
        self.assertEqual((self.by_key["railways"].category, self.by_key["railways"].era), ("production", 2))
        self.assertEqual((self.by_key["ICBMs"].category, self.by_key["ICBMs"].era), ("military", 7))
        self.assertEqual({tech.era for tech in self.catalog}, set(range(1, 13)))

    def test_excludes_society_and_unresearchable(self):
        self.assertNotIn("mass_media", self.by_key)  # society: no operation steals it
        self.assertNotIn("sericulture", self.by_key)  # can_research = no

    def test_indices_unique_from_one(self):
        self.assertEqual([tech.index for tech in self.catalog], list(range(1, len(self.catalog) + 1)))


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.catalog = gen.tech_catalog(cls.state)
        cls.production = [tech for tech in cls.catalog if tech.category == "production"]
        cls.steal = gen.render_steal("production", cls.production)
        cls.outputs = gen.plan_outputs(cls.state, ROOT)

    def test_grant_branches_in_scaled_modifier_order(self):
        text = gen.render_grant(7, [3250, 4388, 5200, 6500, 8775, 10400])
        order = [text.index(f"progress = {amount} ") for amount in (10400, 8775, 6500, 5200, 4388, 3250)]
        self.assertEqual(order, sorted(order))
        self.assertLess(text.index("covert_op_is_fully_operational"), text.index("covert_op_is_established"))
        self.assertEqual(text.count("set_variable = { name = iw_stolen_last value = $IDX$ }"), 6)

    def test_ladder_branch_requires_research_and_target(self):
        ladder = self.steal[: self.steal.index("random_list = {")]
        self.assertEqual(ladder.count("is_researching_technology = "), len(self.production))
        self.assertEqual(
            ladder.count("scope:iw_theft_target ?= { has_technology_researched = "), len(self.production)
        )

    def test_random_list_behind_stealable_guard(self):
        guard = self.steal.index("covert_tech_stealable_production = { TARGET = scope:iw_theft_target }")
        self.assertLess(guard, self.steal.index("random_list = {"))

    def test_every_random_entry_checks_can_research(self):
        entries = self.steal[self.steal.index("random_list = {"):]
        self.assertEqual(entries.count("\t1 = {"), len(self.production))
        self.assertEqual(entries.count("can_research = "), len(self.production))

    def test_target_reads_are_guarded(self):
        for text in self.outputs.values():
            self.assertNotIn("scope:iw_theft_target = {", text)
            self.assertNotIn("$TARGET$ = {", text)

    def test_custom_loc_maps_every_index_to_its_key(self):
        text = self.outputs[gen.CUSTOM_LOC_OUT]
        self.assertIn("type = container", text)
        for tech in self.catalog:
            self.assertIn(f"trigger = {{ var:iw_stolen_last = {tech.index} }}\n\t\tlocalization_key = {tech.key}\n", text)

    def test_committed_outputs_are_current(self):
        for relative, text in self.outputs.items():
            self.assertEqual((ROOT / relative).read_text(encoding="utf-8-sig"), text, str(relative))


def _block(path: str, name: str) -> str:
    """The text of top-level block `name` in a Paradox file, comments stripped."""
    import re

    text = re.sub(r"#[^\n]*", "", (ROOT / path).read_text(encoding="utf-8-sig"))
    start = text.index(f"\n{name} = {{") + 1
    depth = 0
    for position in range(start, len(text)):
        if text[position] == "{":
            depth += 1
        elif text[position] == "}":
            depth -= 1
            if depth == 0:
                return text[start : position + 1]
    raise AssertionError(f"unclosed block {name}")


class WiringTest(unittest.TestCase):
    EFFECTS = "common/scripted_effects/covert_warfare_effects.txt"
    ACTIONS = "common/diplomatic_actions/covert_operations.txt"

    def test_steal_loop_sets_target_inside_exists_guard(self):
        loop = _block(self.EFFECTS, "covert_ops_steal_tech_all")
        self.assertIn("covert_op_is_established = yes", loop)
        guard = loop.index("var:iw_target ?= {")
        self.assertLess(guard, loop.index("save_scope_as = iw_theft_target"))
        self.assertLess(loop.index("save_scope_as = iw_theft_target"), loop.index("covert_tech_steal_production = yes"))

    def test_monthly_pass_steals_and_drops_spread(self):
        master = _block(self.EFFECTS, "covert_ops_apply_all_phase_effects")
        self.assertIn("covert_ops_steal_tech_all = yes", master)
        self.assertNotIn("MODIFIER = covert_industrial_espionage }", master)
        self.assertNotIn("covert_military_espionage MONTHS", master)

    def test_actions_use_stealable_check(self):
        industrial = _block(self.ACTIONS, "covert_industrial_espionage_action")
        military = _block(self.ACTIONS, "covert_military_espionage_action")
        self.assertEqual(industrial.count("covert_tech_stealable_production = { TARGET = scope:target_country }"), 2)
        self.assertEqual(military.count("covert_tech_stealable_military = { TARGET = scope:target_country }"), 1)
        for block in (industrial, military):
            self.assertNotIn("techs_researched > ROOT.techs_researched", block)


if __name__ == "__main__":
    unittest.main()
