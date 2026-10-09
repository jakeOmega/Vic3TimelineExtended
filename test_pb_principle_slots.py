"""Power bloc principle slots: count, AI limit, remove dispatch, panel, technologies, game rule.

A bloc has te_pb_principle_slot_cap slots (2, rank and members, one per slot
technology). Slot rules 3 and 4 compare it, the panel locks slots 3-8 above it
(slots 5-8 shown only under the eight-slot rule) with a tooltip listing its
sources, every principle's `possible` calls te_pb_principle_slot_free (the AI's
limit), and the panel's remove button dispatches through
te_pb_remove_principle_in_scope.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_pb_principle_slots.py
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_pb_principle_slots as gen  # noqa: E402

SLOT_TECHS = {
    "intergovernmental_organizations": "era_6.txt",
    "containerization": "era_8.txt",
    "globalization": "era_9.txt",
    "universal_digital_identity": "era_11.txt",
}
CAP_EXPR = "PowerBloc.GetLeader.MakeScope.ScriptValue('te_pb_bloc_principle_slot_cap')"
MAX_EXPR = "PowerBloc.GetLeader.MakeScope.ScriptValue('te_pb_principle_slots_max')"
LOC = ROOT / "localization" / "english"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def loc_value(key: str) -> str:
    for path in sorted(LOC.rglob("*_l_english.yml")):
        m = re.search(rf'^ {re.escape(key)}:0? ?"(.*)"$', path.read_text(encoding="utf-8-sig"), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"loc key {key} not found")


def entity_block(text: str, name: str, nested: bool = False) -> str:
    """The `name = { ... }` block: a top-level entity, or with nested=True the first at any depth."""
    m = re.search(rf"{'' if nested else '^'}\b{re.escape(name)}\s*=\s*\{{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 0, m.end() - 1
    while True:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1]
        i += 1


class GeneratedCodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, cls.vanilla = gen.load_state(ROOT)
        cls.rows = gen.grouped_principles(cls.state)
        cls.principles = cls.state.get_data("Principles")

    def test_committed_outputs_are_current(self):
        for relative, text in gen.plan_outputs(self.state, self.vanilla, ROOT).items():
            with self.subTest(file=str(relative)):
                self.assertEqual(
                    (ROOT / relative).read_bytes(), text.encode("utf-8-sig"),
                    f"{relative} is stale: run python3 scripts/generators/gen_pb_principle_slots.py",
                )

    def test_every_grouped_principle_carries_the_ai_limit(self):
        missing = []
        for principle, group in self.rows:
            possible = gen._unwrap(gen._unwrap(self.principles[principle]).get("possible"))
            call = gen._unwrap((possible or {}).get("te_pb_principle_slot_free")) if isinstance(possible, dict) else None
            if not isinstance(call, dict) or gen._unwrap(call.get("GROUP")) != group:
                missing.append(principle)
        self.assertEqual(missing, [], "add te_pb_principle_slot_free = { GROUP = <group> } to their `possible`")

    def test_remove_dispatch_covers_every_grouped_principle_once(self):
        text = read(str(gen.REMOVE_OUT))
        removed = re.findall(r"remove_principle = (principle_\w+)", text)
        self.assertEqual(sorted(removed), sorted(p for p, _ in self.rows))
        self.assertEqual(len(removed), len(set(removed)))

    def test_every_group_has_five_tiers(self):
        # concept_power_bloc_principle_group_desc (replace/ override) says five
        counts = {}
        for _, group in self.rows:
            counts[group] = counts.get(group, 0) + 1
        self.assertEqual({g: n for g, n in counts.items() if n != 5}, {})
        self.assertIn("five tiers", loc_value("concept_power_bloc_principle_group_desc"))

    def test_principles_outside_every_group_are_only_the_orphaned_sacred_civics(self):
        grouped = {p for p, _ in self.rows}
        self.assertEqual(
            sorted(set(self.principles) - grouped),
            ["principle_sacred_civics_1", "principle_sacred_civics_2", "principle_sacred_civics_3"],
        )

    def test_vanilla_possible_blocks_the_inject(self):
        rows = [("principle_x_1", "principle_group_x")]
        vanilla = {"principle_x_1": ("=", {"possible": ("=", {"always": ("=", "yes")})})}
        with self.assertRaises(ValueError):
            gen.gate_targets(rows, vanilla, touched=set())
        self.assertEqual(gen.gate_targets(rows, vanilla, touched={"principle_x_1"}), [])


class WiringTest(unittest.TestCase):
    def test_max_principles_is_eight(self):
        self.assertRegex(read("common/defines/extra_defines.txt"), r"\n\tMAX_PRINCIPLES = 8\b")

    def test_slot_rules_three_and_four_compare_the_count(self):
        rules = read("common/scripted_rules/00_scripted_rules.txt")
        for slot in (3, 4):
            block = entity_block(rules, f"unlock_power_bloc_principle_slot_{slot}")
            with self.subTest(slot=slot):
                self.assertIn(f"te_pb_principle_slot_cap >= {slot}", block)
                self.assertIn(f"used_principle_slots >= {slot}", block)

    def test_panel_has_eight_slots_and_caps_three_to_eight(self):
        gui = read("gui/power_bloc_panel.gui")
        for index in range(8):
            m = re.search(
                rf"principle_slot = \{{\n\t+datacontext = \"\[PowerBlocPanel\.GetPrincipleSlot\( '\(int32\){index}' \)\]\"",
                gui,
            )
            self.assertIsNotNone(m, f"slot index {index} missing from the panel")
            if index < 2:
                continue
            instance = gui[m.start():gui.index("\n\t\t\t\t\t\t}\n", m.end())]
            threshold = f"GreaterThan_CFixedPoint({CAP_EXPR}, '(CFixedPoint){index}')"
            with self.subTest(slot=index + 1):
                for block in ("te_new_slot_visible", "te_unlocked_empty_slot_visible", "te_locked_slot_visible"):
                    self.assertIn(f'blockoverride "{block}"', instance)
                # the three empty-slot states compare the count; the slot itself never hides on it
                self.assertEqual(instance.count(threshold), 3)
                self.assertRegex(
                    instance,
                    rf'blockoverride "te_locked_slot_tooltip" \{{\n\t+tooltip = "te_pb_locked_slot_{index + 1}_tt"',
                )
                if index >= 4:
                    # slots 5-8 are on the panel from the start under the eight-slot rule, locked
                    # until the count reaches them, and hidden under the four-slot rule
                    self.assertIn(
                        "visible = \"[Or(PowerBlocPrincipleSlot.IsActive, And(HasDlcFeature('power_bloc_features'), "
                        f"GreaterThan_CFixedPoint({MAX_EXPR}, '(CFixedPoint){index}')))]\"",
                        instance,
                    )

    def test_locked_slot_tooltip_is_a_block_of_the_slot_type(self):
        gui = read("gui/power_bloc_panel.gui")
        slot_type = gui[gui.index("type principle_slot = "):gui.index("type principle_slot_formation = ")]
        locked = slot_type[slot_type.index("locked_principle_slot = {"):]
        self.assertRegex(
            locked,
            r'blockoverride "slot_tooltip" \{\n\t+block "te_locked_slot_tooltip" \{\n\t+tooltip = "TOOLTIP_LOCKED_PRINCIPLE_SLOT"',
        )

    def test_locked_slot_tooltips_name_their_slot_and_list_the_sources(self):
        for slot in range(3, 9):
            with self.subTest(slot=slot):
                text = loc_value(f"te_pb_locked_slot_{slot}_tt")
                self.assertIn(f"#v {slot}#!", text)
                self.assertIn("$te_pb_locked_slot_sources_tt$", text)
        sources = loc_value("te_pb_locked_slot_sources_tt")
        self.assertIn("ScriptValue('te_pb_bloc_principle_slot_cap')", sources)
        self.assertIn(
            "GetScriptedGui('te_pb_principle_slot_sources_sgui').IsValidTooltip( GuiScope.SetRoot( PowerBloc.GetLeader.MakeScope ).End )",
            sources,
        )

    def test_sources_checklist_matches_the_count(self):
        sgui = entity_block(read("common/scripted_guis/te_power_bloc_sguis.txt"), "te_pb_principle_slot_sources_sgui")
        valid = entity_block(sgui, "is_valid", nested=True)
        self.assertIn("power_bloc ?= { te_pb_rank_5_principle_slot = yes }", valid)
        self.assertIn("power_bloc ?= { te_pb_rank_3_principle_slot = yes }", valid)
        techs = entity_block(valid, "trigger_if", nested=True)
        self.assertIn("NOT = { has_game_rule = te_principle_slots_four }", techs)
        self.assertEqual(sorted(re.findall(r"has_technology_researched = (\w+)", valid)), sorted(SLOT_TECHS))
        self.assertEqual(sorted(re.findall(r"has_technology_researched = (\w+)", techs)), sorted(SLOT_TECHS))
        values = read("common/script_values/te_power_bloc_principle_slot_values.txt")
        cap = entity_block(values, "te_pb_principle_slot_cap")
        for trigger in ("te_pb_rank_5_principle_slot", "te_pb_rank_3_principle_slot"):
            self.assertIn(f"limit = {{ {trigger} = yes }}", cap)
        triggers = read("common/scripted_triggers/te_power_bloc_principle_slot_triggers.txt")
        self.assertIn("power_bloc_rank <= 5\n\tnum_power_bloc_members >= 5", entity_block(triggers, "te_pb_rank_5_principle_slot"))
        self.assertIn("power_bloc_rank <= 3\n\tnum_power_bloc_members >= 10", entity_block(triggers, "te_pb_rank_3_principle_slot"))

    def test_slot_tooltips_do_not_warn_about_the_game_rule(self):
        keys = [f"te_pb_locked_slot_{n}_tt" for n in range(3, 9)] + [
            "te_pb_locked_slot_sources_tt", "te_pb_slot_3_unlock_tt", "te_pb_slot_4_unlock_tt",
            "TOOLTIP_LOCKED_PRINCIPLE_SLOT_DURING_FORMATION",
            "TOOLTIP_LOCKED_PRINCIPLE_SLOT_3_DURING_FORMATION", "TOOLTIP_LOCKED_PRINCIPLE_SLOT_4_DURING_FORMATION",
        ]
        for key in keys:
            with self.subTest(key=key):
                self.assertNotIn("$rule_te_principle_slots_rule$", loc_value(key))
        for key in keys[-3:]:
            with self.subTest(key=key):
                self.assertIn("'te_pb_slot_techs_sentence'", loc_value(key))
                self.assertIn("ScriptValue('te_pb_principle_slots_max')", loc_value(key))

    def test_remove_button_runs_the_dispatch(self):
        sgui = read("common/scripted_guis/te_power_bloc_sguis.txt")
        self.assertIn("te_pb_remove_principle_in_scope = yes", entity_block(sgui, "te_pb_remove_principle_sgui"))
        self.assertIn("GetScriptedGui('te_pb_remove_principle_sgui').Execute", read("gui/power_bloc_panel.gui"))

    def test_four_technologies_add_one_slot_each(self):
        granted = {}
        for path in sorted((ROOT / "common/technology/technologies").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            for m in re.finditer(r"^(\w+) = \{", text, re.M):
                block = entity_block(text, m.group(1))
                n = re.findall(r"country_te_pb_principle_slots_add = (\S+)", block)
                if n:
                    granted[m.group(1)] = (path.name, n)
        self.assertEqual(granted, {tech: (era, ["1"]) for tech, era in SLOT_TECHS.items()})
        values = read("common/script_values/te_power_bloc_principle_slot_values.txt")
        self.assertIn("max = 4", entity_block(values, "te_pb_tech_principle_slots"))
        self.assertIn("max = 8", entity_block(values, "te_pb_principle_slot_cap"))

    def test_game_rule_four_drops_the_technology_slots(self):
        rule = entity_block(read("common/game_rules/extra_game_rules.txt"), "te_principle_slots_rule")
        self.assertIn("default = te_principle_slots_eight", rule)
        self.assertEqual(
            sorted(re.findall(r"^\t(te_principle_slots_\w+) = \{", rule, re.M)),
            ["te_principle_slots_eight", "te_principle_slots_four"],
        )
        values = read("common/script_values/te_power_bloc_principle_slot_values.txt")
        slots_max = entity_block(values, "te_pb_principle_slots_max")
        self.assertRegex(slots_max, r"(?m)^\tvalue = 8$")
        self.assertRegex(slots_max, r"limit = \{ has_game_rule = te_principle_slots_four \}\s*value = 4")
        tech = entity_block(values, "te_pb_tech_principle_slots")
        self.assertRegex(tech, r"(?m)^\tvalue = 0$")
        self.assertRegex(
            tech,
            r"NOT = \{ has_game_rule = te_principle_slots_four \}\s*\}\s*add = modifier:country_te_pb_principle_slots_add",
        )


if __name__ == "__main__":
    unittest.main()
