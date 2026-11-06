"""Power bloc summits (#1442): spending a spare mandate on a ten-year initiative.

The leader's Convene a Summit button (te_pb_summit_sgui, gui/power_bloc_panel.gui)
opens te_pb_summit.1; an AI leader with two or more mandates gets it from a
monthly roll (te_pb_summit_ai_on_action). Every option but Adjourn spends one
mandate through te_pb_summit_pay and is offered only while the bloc holds one.
The Mandate Reserve these replace is no longer applied.
docs/systems/mod_systems/power_blocs.md.

Run: .venv/bin/python test_pb_summit.py
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC = ROOT / "localization" / "english"
EVENT_FILE = "events/te_power_bloc_summit_events.txt"
MODIFIER_FILE = "common/static_modifiers/te_power_bloc_summit_modifiers.txt"

# option letter -> (initiative modifier, scope it sits on, hidden while running)
INITIATIVES = {
    "a": ("te_pb_summit_rally", "bloc", False),
    "b": ("te_pb_summit_recruitment", "bloc", True),
    "c": ("te_pb_summit_leverage", "bloc", True),
    "e": ("te_pb_summit_open_borders", "bloc", True),
    "g": ("te_pb_summit_home", "leader", True),
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def loc_value(key: str) -> str:
    for path in sorted(LOC.rglob("*_l_english.yml")):
        m = re.search(rf'^ {re.escape(key)}:0? ?"(.*)"$', path.read_text(encoding="utf-8-sig"), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"loc key {key} not found")


def block_at(text: str, start: int) -> str:
    """The brace block whose `{` is the first one at or after start."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise AssertionError("unbalanced braces")


def entity_block(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}\s*=\s*\{{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    return block_at(text, m.start())


def options(event: str) -> dict:
    """{option letter: option block} of te_pb_summit.1."""
    out = {}
    for m in re.finditer(r"^\toption = \{", event, re.M):
        block = block_at(event, m.start())
        name = re.search(r"name = te_pb_summit\.1\.(\w+)", block)
        out[name.group(1)] = block
    return out


class TestSummitEvent(unittest.TestCase):
    def setUp(self):
        self.event = entity_block(read(EVENT_FILE), "te_pb_summit.1")
        self.options = options(self.event)

    def test_options_are_the_initiatives_and_adjourn(self):
        self.assertEqual(sorted(self.options), sorted([*INITIATIVES, "h"]))

    def test_each_initiative_spends_one_mandate_and_needs_one(self):
        for letter in INITIATIVES:
            with self.subTest(option=letter):
                block = self.options[letter]
                self.assertEqual(len(re.findall(r"te_pb_summit_pay = \{ KIND = \w+ \}", block)), 1)
                self.assertNotIn("add_power_bloc_mandate", block)   # only through the pay effect
                trigger = block_at(block, block.index("trigger = {"))
                self.assertIn("te_pb_summit_can_pay = yes", trigger)

    def test_adjourn_is_free_and_the_default(self):
        block = self.options["h"]
        self.assertIn("default_option = yes", block)
        self.assertNotIn("te_pb_summit_pay", block)
        self.assertNotIn("add_power_bloc_mandate", block)
        self.assertRegex(block, r"ai_chance = \{\s*base = 0\s*\}")

    def test_each_initiative_grants_its_modifier_for_ten_years(self):
        for letter, (modifier, scope, _) in INITIATIVES.items():
            with self.subTest(option=letter):
                block = self.options[letter]
                if scope == "bloc":
                    self.assertIn(f"te_pb_summit_grant_bloc_initiative = {{ MODIFIER = {modifier} }}", block)
                else:
                    self.assertRegex(block, rf"add_modifier = \{{\s*name = {modifier}\s*days = long_modifier_time\s*\}}")
        grant = entity_block(read("common/scripted_effects/te_power_bloc_summit_effects.txt"),
                             "te_pb_summit_grant_bloc_initiative")
        self.assertIn("power_bloc = {", grant)
        self.assertRegex(grant, r"add_modifier = \{\s*name = \$MODIFIER\$\s*days = long_modifier_time\s*\}")
        # a same-name add_modifier stacks, so a running copy goes first
        self.assertLess(grant.index("remove_modifier = $MODIFIER$"), grant.index("add_modifier"))

    def test_a_running_initiative_is_not_offered_again(self):
        for letter, (modifier, scope, hidden) in INITIATIVES.items():
            with self.subTest(option=letter):
                trigger = block_at(self.options[letter], self.options[letter].index("trigger = {"))
                running = f"NOT = {{ has_modifier = {modifier} }}"
                if hidden:
                    self.assertIn(running, trigger)
                    if scope == "bloc":
                        self.assertIn("power_bloc ?= {", trigger)
                else:
                    self.assertNotIn(running, trigger)

    def test_open_borders_hidden_when_principles_give_both(self):
        trigger = block_at(self.options["e"], self.options["e"].index("trigger = {"))
        self.assertIn("te_pb_summit_has_open_borders = no", trigger)
        check = entity_block(read("common/scripted_triggers/te_power_bloc_summit_triggers.txt"),
                             "te_pb_summit_has_open_borders")
        for tier in (3, 4, 5):
            self.assertIn(f"principle:principle_navy_{tier}", check)
            self.assertIn(f"principle:principle_freedom_of_movement_{tier}", check)
        # the principles it names really give the two abilities
        principles = read("common/power_bloc_principles/extra_power_bloc_principles.txt")
        for tier in (4, 5):
            self.assertIn("power_bloc_allow_port_access_bool = yes", entity_block(principles, f"principle_navy_{tier}"))
            self.assertIn("power_bloc_allow_wider_migration_area_bool = yes",
                          entity_block(principles, f"principle_freedom_of_movement_{tier}"))
        modifier = entity_block(read(MODIFIER_FILE), "te_pb_summit_open_borders")
        self.assertIn("power_bloc_allow_port_access_bool = yes", modifier)
        self.assertIn("power_bloc_allow_wider_migration_area_bool = yes", modifier)

    def test_ai_weights_use_the_mtth_form(self):
        for letter, block in self.options.items():
            with self.subTest(option=letter):
                chance = block_at(block, block.index("ai_chance = {"))
                self.assertNotIn("if = {", chance)
                self.assertNotIn("limit = {", chance)

    def test_loc(self):
        for key in ["t", "d", "d_none", "f", *INITIATIVES, "h"]:
            with self.subTest(key=key):
                self.assertTrue(loc_value(f"te_pb_summit.1.{key}"))
        for modifier, _, _ in INITIATIVES.values():
            with self.subTest(modifier=modifier):
                self.assertTrue(loc_value(modifier))
                self.assertTrue(loc_value(f"{modifier}_desc"))
        self.assertIn("[concept_power_bloc_mandate]", loc_value("te_pb_summit_cost_tt"))


class TestSummitPayment(unittest.TestCase):
    def test_pay_spends_exactly_one(self):
        pay = entity_block(read("common/scripted_effects/te_power_bloc_summit_effects.txt"), "te_pb_summit_pay")
        self.assertEqual(re.findall(r"add_power_bloc_mandate = (\S+)", pay), ["-1"])
        self.assertIn("text = te_pb_summit_cost_tt", pay)

    def test_can_pay_needs_a_mandate_and_the_lead(self):
        can_pay = entity_block(read("common/scripted_triggers/te_power_bloc_summit_triggers.txt"),
                               "te_pb_summit_can_pay")
        self.assertIn("is_power_bloc_leader = yes", can_pay)
        self.assertIn("power_bloc ?= { num_mandates >= 1 }", can_pay)


class TestSummitButton(unittest.TestCase):
    def test_sgui_gates_and_opens_the_event(self):
        sgui = entity_block(read("common/scripted_guis/te_power_bloc_sguis.txt"), "te_pb_summit_sgui")
        valid = block_at(sgui, sgui.index("\tis_valid = {"))   # not ai_is_valid
        self.assertIn("te_pb_summit_can_pay = yes", valid)
        self.assertIn("custom_tooltip = {", valid)
        self.assertRegex(sgui, r"ai_is_valid = \{\s*always = no\s*\}")
        self.assertIn("trigger_event = { id = te_pb_summit.1 popup = yes }", sgui)
        self.assertNotIn("add_power_bloc_mandate", sgui)   # the button itself spends nothing

    def test_panel_button(self):
        gui = read("gui/power_bloc_panel.gui")
        m = re.search(r"text = \"te_pb_summit_button\"", gui)
        self.assertIsNotNone(m)
        button = gui[gui.rindex("button = {", 0, m.start()):]
        button = block_at(button, 0)
        scope = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
        self.assertIn(f"GetScriptedGui('te_pb_summit_sgui').IsValid( {scope} )", button)
        self.assertIn(f"GetScriptedGui('te_pb_summit_sgui').Execute( {scope} )", button)
        self.assertIn(f"GetScriptedGui('te_pb_summit_sgui').IsValidTooltip( {scope} )", button)
        # it sits in the leader-only AVAILABLE MANDATES row
        row = gui[gui.rindex("# AVAILABLE MANDATES", 0, m.start()):m.start()]
        self.assertIn('visible = "[PowerBloc.IsLeader(GetPlayer.Self)]"', row)


class TestSummitAI(unittest.TestCase):
    def test_monthly_roll_from_two_mandates_rising_with_the_count(self):
        text = read("common/on_actions/te_power_bloc_summit_on_actions.txt")
        self.assertRegex(entity_block(text, "on_monthly_pulse_country"), r"te_pb_summit_ai_on_action")
        body = entity_block(text, "te_pb_summit_ai_on_action")
        gate = block_at(body, body.index("limit = {"))
        self.assertIn("is_ai = yes", gate)
        self.assertIn("is_power_bloc_leader = yes", gate)
        self.assertIn("power_bloc ?= { num_mandates >= 2 }", gate)
        rungs = [int(n) for n in re.findall(r"num_mandates >= (\d+) \} \}", body)]
        chances = [int(n) for n in re.findall(r"chance = (\d+)", body)]
        self.assertEqual(rungs, [5, 4, 3])          # then an else for two
        self.assertEqual(len(chances), 4)
        self.assertEqual(chances, sorted(chances, reverse=True))   # more mandates, likelier
        self.assertEqual(len(re.findall(r"trigger_event = \{ id = te_pb_summit\.1 \}", body)), 4)


class TestMandateReserveRetired(unittest.TestCase):
    def test_nothing_applies_it(self):
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotRegex(text, r"add_modifier = \{\s*name = sm_te_unused_mandate_reserve")

    def test_kept_defined_for_old_saves_and_stripped(self):
        self.assertIn("sm_te_unused_mandate_reserve = {", read("common/static_modifiers/extra_modifiers.txt"))
        strip = entity_block(read("common/on_actions/extra_on_actions.txt"), "te_unused_mandate_reserve_on_action")
        self.assertIn("remove_modifier = sm_te_unused_mandate_reserve", strip)


if __name__ == "__main__":
    unittest.main()
