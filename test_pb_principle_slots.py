"""Power bloc principle slots: count, AI limit, remove dispatch, panel, technologies.

A bloc has te_pb_principle_slot_cap slots (2, rank and members, one per slot
technology). Slot rules 3 and 4 compare it, the panel shows slots 3-8 up to it,
every principle's `possible` calls te_pb_principle_slot_free (the AI's limit),
and the panel's remove button dispatches through te_pb_remove_principle_in_scope.

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


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def entity_block(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}\s*=\s*\{{", text, re.M)
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
                self.assertGreaterEqual(instance.count(threshold), 3)

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


if __name__ == "__main__":
    unittest.main()
