"""Power bloc summits (#1442): spending a spare mandate on a ten-year initiative.

The leader's Convene a Summit button (te_pb_summit_sgui, gui/power_bloc_panel.gui)
opens te_pb_summit.1; an AI leader with two or more mandates gets it from a
monthly roll (te_pb_summit_ai_on_action). Every option but Adjourn spends one
mandate through te_pb_summit_pay and is offered only while the bloc holds one.
Five initiatives are open to every bloc and one more to each bloc identity.
The Mandate Reserve these replace is gone. docs/systems/mod_systems/power_blocs.md.

Run: .venv/bin/python test_pb_summit.py
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC = ROOT / "localization" / "english"
EVENT_FILE = "events/te_power_bloc_summit_events.txt"
MODIFIER_FILE = "common/static_modifiers/te_power_bloc_summit_modifiers.txt"
EFFECT_FILE = "common/scripted_effects/te_power_bloc_summit_effects.txt"
TRIGGER_FILE = "common/scripted_triggers/te_power_bloc_summit_triggers.txt"

# option letter -> [(initiative modifier, where it sits)]; "bloc" is the power
# bloc, "leader" the leader alone, "member" every member through
# te_pb_summit_grant_member_initiative. The first is the one whose running
# copy hides the option.
INITIATIVES = {
    "a": [("te_pb_summit_rally", "bloc")],
    "b": [("te_pb_summit_recruitment", "bloc")],
    "c": [("te_pb_summit_leverage", "bloc")],
    "e": [("te_pb_summit_open_borders", "bloc")],
    "g": [("te_pb_summit_home", "leader")],
    "i": [("te_pb_summit_drills", "member")],
    "j": [("te_pb_summit_council", "member")],
    "k": [("te_pb_summit_customs", "bloc"), ("te_pb_summit_customs_members", "member")],
    "l": [("te_pb_summit_imperial", "leader")],
    "m": [("te_pb_summit_congress", "member")],
    "n": [("te_pb_summit_culture", "member")],
    "o": [("te_pb_summit_ambassadors", "member")],
}
# Offered while running, for its immediate cohesion.
REPEATABLE = {"a"}
# option letter -> the bloc identity it is offered to
IDENTITY_OPTIONS = {
    "i": "identity_military_treaty_organization",
    "j": "identity_religious",
    "k": "identity_trade_league",
    "l": "identity_sovereign_empire",
    "m": "identity_ideological_union",
    "n": "identity_cultural",
    "o": "identity_diplomatic",
}
RELATIONS = {"i": "te_pb_summit_member_relations", "n": "te_pb_summit_member_relations",
             "o": "te_pb_summit_member_relations", "l": "te_pb_summit_leader_relations"}
GRANT = {"bloc": "te_pb_summit_grant_bloc_initiative", "leader": "te_pb_summit_grant_leader_initiative",
         "member": "te_pb_summit_grant_member_initiative"}


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
        out[re.search(r"te_pb_summit\.1\.([a-z])", block).group(1)] = block
    return out


def option_trigger(block: str) -> str:
    """The option's own trigger, not a trigger inside one of its name blocks ("" for none)."""
    at = block.find("\n\t\ttrigger = {")
    return block_at(block, at) if at >= 0 else ""


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
                self.assertIn("te_pb_summit_can_pay = yes", option_trigger(block))

    def test_adjourn_is_free_and_the_default(self):
        block = self.options["h"]
        self.assertIn("default_option = yes", block)
        self.assertNotIn("te_pb_summit_pay", block)
        self.assertNotIn("add_power_bloc_mandate", block)
        self.assertRegex(block, r"ai_chance = \{\s*base = 0\s*\}")

    def test_each_initiative_grants_its_modifiers_through_a_helper(self):
        modifiers = read(MODIFIER_FILE)
        for letter, grants in INITIATIVES.items():
            for modifier, where in grants:
                with self.subTest(option=letter, modifier=modifier):
                    self.assertIn(f"{GRANT[where]} = {{ MODIFIER = {modifier} }}", self.options[letter])
                    self.assertNotIn("add_modifier", self.options[letter])
                    entity_block(modifiers, modifier)   # defined

    def test_grant_helpers_refresh_for_ten_years(self):
        effects = read(EFFECT_FILE)
        for where, helper in GRANT.items():
            with self.subTest(helper=helper):
                grant = entity_block(effects, helper)
                self.assertRegex(grant, r"add_modifier = \{\s*name = \$MODIFIER\$\s*days = long_modifier_time\s*\}")
                # a same-name add_modifier stacks, so a running copy goes first
                self.assertLess(grant.index("remove_modifier = $MODIFIER$"), grant.index("add_modifier"))
                if where == "bloc":
                    self.assertIn("power_bloc = {", grant)
                if where == "member":
                    self.assertIn("every_power_bloc_member = {", grant)
                if where == "leader":
                    self.assertNotIn("power_bloc", grant)

    def test_bloc_grant_line_names_the_bloc(self):
        # Vanilla's add_modifier line prints $SUBJECT_NAME$, empty for a power
        # bloc (" gets Summit: Common Purpose", 2026-11-06), so the bloc helper
        # prints its own line, which must name the bloc and render the modifier.
        grant = entity_block(read(EFFECT_FILE), GRANT["bloc"])
        self.assertRegex(grant, r"custom_tooltip = \{\s*text = \$MODIFIER\$_grant_tt\s*add_modifier = \{")
        years = json.loads((ROOT / "vanilla_parsed/common/script_values.json").read_text())["long_modifier_time"]
        self.assertEqual(years, ["=", "3650"])   # the "10 years" the lines say
        bloc_modifiers = {m for grants in INITIATIVES.values() for m, where in grants if where == "bloc"}
        self.assertEqual(len(bloc_modifiers), 5)
        for modifier in bloc_modifiers:
            with self.subTest(modifier=modifier):
                line = loc_value(f"{modifier}_grant_tt")
                self.assertTrue(line.startswith("[ROOT.GetCountry.GetPowerBloc.GetName] gets "))
                self.assertIn(f"[GetStaticModifier('{modifier}').GetName]", line)
                self.assertIn(f"[GetStaticModifier('{modifier}').GetDesc]", line)
                self.assertIn("for #b 10 years#!", line)

    def test_a_running_initiative_is_not_offered_again(self):
        for letter, grants in INITIATIVES.items():
            modifier, where = grants[0]
            with self.subTest(option=letter):
                trigger = option_trigger(self.options[letter])
                running = f"NOT = {{ has_modifier = {modifier} }}"
                if letter in REPEATABLE:
                    self.assertNotIn(running, trigger)
                    continue
                self.assertIn(running, trigger)
                # a bloc modifier is read on the bloc; a member or leader one on
                # the leader, who is a member
                inside_bloc = re.search(r"power_bloc \?= \{[^{}]*" + re.escape(running), trigger)
                self.assertEqual(bool(inside_bloc), where == "bloc")

    def test_identity_options_are_one_an_identity(self):
        known = set(json.loads(read("vanilla_parsed/common/power_bloc_identities.json")))
        known |= set(re.findall(r"^(identity_\w+) = \{", read("common/power_bloc_identities/extra_power_bloc_identities.txt"), re.M))
        self.assertEqual(set(IDENTITY_OPTIONS.values()), known)   # every identity has one
        for letter, block in self.options.items():
            with self.subTest(option=letter):
                gates = re.findall(r"te_pb_summit_bloc_identity = \{ IDENTITY = (\w+) \}", option_trigger(block))
                self.assertEqual(gates, [IDENTITY_OPTIONS[letter]] if letter in IDENTITY_OPTIONS else [])
        check = entity_block(read(TRIGGER_FILE), "te_pb_summit_bloc_identity")
        self.assertIn("has_identity = identity:$IDENTITY$", check)

    def test_relations_where_promised(self):
        for letter, block in self.options.items():
            with self.subTest(option=letter):
                calls = re.findall(r"(te_pb_summit_(?:member|leader)_relations) = yes", block)
                self.assertEqual(calls, [RELATIONS[letter]] if letter in RELATIONS else [])
        effects = read(EFFECT_FILE)
        members = entity_block(effects, "te_pb_summit_member_relations")
        # each pair is met twice, so each step is half the 20 the tooltip says
        self.assertEqual(re.findall(r"value = (\d+)", members), ["10"])
        self.assertIn("NOT = { this = scope:te_pb_summit_member }", members)
        self.assertEqual(re.findall(r"value = (\d+)", entity_block(effects, "te_pb_summit_leader_relations")), ["20"])
        for key in ("te_pb_summit_relations_tt", "te_pb_summit_leader_relations_tt"):
            self.assertIn("#v 20#!", loc_value(key))

    def test_council_names_cover_the_faiths_and_one_fallback(self):
        block = self.options["j"]
        names = re.findall(r"name = \{\s*trigger = \{(.*?)\}\s*text = (te_pb_summit\.1\.j\w*)\s*\}", block, re.S)
        texts = [text for _, text in names]
        self.assertEqual(texts[-1], "te_pb_summit.1.j")
        self.assertIn("te_pb_summit_named_council = no", names[-1][0])
        named = set(re.findall(r"rel:(\w+)", "".join(trigger for trigger, _ in names[:-1])))
        listed = set(re.findall(r"rel:(\w+)", entity_block(read(TRIGGER_FILE), "te_pb_summit_named_council")))
        self.assertEqual(named, listed)   # so the fallback never shows beside a named council
        religions = set(json.loads(read("vanilla_parsed/common/religions.json")))
        self.assertLessEqual(named, religions)
        for text in texts:
            with self.subTest(name=text):
                self.assertTrue(loc_value(text))

    def test_open_borders_hidden_when_principles_give_both(self):
        self.assertIn("te_pb_summit_has_open_borders = no", option_trigger(self.options["e"]))
        check = entity_block(read(TRIGGER_FILE), "te_pb_summit_has_open_borders")
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

    def test_mandate_at_home_authority(self):
        self.assertIn("country_authority_add = 200", entity_block(read(MODIFIER_FILE), "te_pb_summit_home"))

    def test_ai_weights_use_the_mtth_form(self):
        for letter, block in self.options.items():
            with self.subTest(option=letter):
                chance = block_at(block, block.index("ai_chance = {"))
                self.assertNotIn("if = {", chance)
                self.assertNotIn("limit = {", chance)
                base = int(re.search(r"base = (\d+)", chance).group(1))
                if letter in IDENTITY_OPTIONS:
                    self.assertEqual(base, 15)   # above the general five

    def test_loc(self):
        for key in ["t", "d", "d_none", "f", "h", *(k for k in INITIATIVES if k != "j")]:
            with self.subTest(key=key):
                self.assertTrue(loc_value(f"te_pb_summit.1.{key}"))
        for grants in INITIATIVES.values():
            for modifier, _ in grants:
                with self.subTest(modifier=modifier):
                    self.assertTrue(loc_value(modifier))
                    self.assertTrue(loc_value(f"{modifier}_desc"))
        self.assertIn("[concept_power_bloc_mandate]", loc_value("te_pb_summit_cost_tt"))


class TestSummitPayment(unittest.TestCase):
    def test_pay_spends_exactly_one(self):
        pay = entity_block(read(EFFECT_FILE), "te_pb_summit_pay")
        self.assertEqual(re.findall(r"add_power_bloc_mandate = (\S+)", pay), ["-1"])
        self.assertIn("text = te_pb_summit_cost_tt", pay)

    def test_can_pay_needs_a_mandate_and_the_lead(self):
        can_pay = entity_block(read(TRIGGER_FILE), "te_pb_summit_can_pay")
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
        button = block_at(gui[gui.rindex("button = {", 0, m.start()):], 0)
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


class TestMandateReserveGone(unittest.TestCase):
    def test_no_trace_in_the_mod(self):
        roots = ["common", "events", "gui", "localization/english"]
        for root in roots:
            for path in sorted((ROOT / root).rglob("*")):
                if path.suffix not in {".txt", ".gui", ".yml"}:
                    continue
                with self.subTest(path=str(path.relative_to(ROOT))):
                    self.assertNotIn("unused_mandate_reserve", path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
