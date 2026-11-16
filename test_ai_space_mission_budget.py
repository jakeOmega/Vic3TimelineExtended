"""The AI's Space Program budget (docs/systems/mod_systems/ai.md § Space Program Mission Budget).

An AI country's Space Program runs the dearest mission whose weekly bill is within 10% of its
government's fixed income. It is stepped down once its mission's bill has been over 20% for six
monthly reviews in a row, drops to Earth Orbit at once in default or under the bankruptcy
modifier, and waits five years after a step-down before it climbs again. The funding buttons shed
funding first. A Mission Limit group of effect-free, ratcheted methods gates the missions, so the
engine's own method AI (most_productive, which climbs) can't climb back past the ceiling the
monthly pass sets. A player's program is never touched, beyond lifting an AI ceiling from a
country a player has taken over.

The structure tests hold the pieces to each other. The behavior tests run the pass itself
(`sr_ai_mission_budget_monthly`, its values and triggers, as written) in a small fail-closed
evaluator: a construct it doesn't know fails the test rather than reading as false.
"""
import math
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/sr_ai_mission_budget_values.txt"
SR_VALUES = ROOT / "common/script_values/space_race_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/sr_ai_mission_budget_triggers.txt"
SR_TRIGGERS = ROOT / "common/scripted_triggers/space_race_triggers.txt"
EFFECTS = ROOT / "common/scripted_effects/sr_ai_mission_budget_effects.txt"
PMS = ROOT / "common/production_methods/extra_pms.txt"
CEILING_PMS = ROOT / "common/production_methods/sr_mission_ceiling_pms.txt"
CEILING_PMG = ROOT / "common/production_method_groups/sr_mission_ceiling_pmgs.txt"
PMGS = ROOT / "common/production_method_groups/extra_pm_groups.txt"
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
BUTTONS = ROOT / "common/scripted_buttons/space_race_buttons.txt"
DECISIONS = ROOT / "common/decisions/extra_decisions.txt"
ON_ACTIONS = ROOT / "common/on_actions/space_race_on_actions.txt"
MODIFIERS = ROOT / "common/static_modifiers/space_race_modifiers.txt"
LOC = ROOT / "localization/english/te_production_methods_l_english.yml"

# tier: (key, mission method, its technology, units value)
TIERS = {
    1: ("earth_orbit", "pm_earth_orbit", None, "sr_mission_units_earth_orbit"),
    2: ("moon", "pm_moon_mission", "space_exploration", "sr_mission_units_moon"),
    3: ("mars", "pm_mars_mission", "knowledge_economy", "sr_mission_units_mars"),
    4: ("solar", "pm_solar_colonization", "cislunar_infrastructure", "sr_mission_units_solar"),
    5: ("deep_space", "pm_deep_space_exploration", "space_colonization", "sr_mission_units_deep_space"),
    6: ("interstellar", "pm_interstellar_mission", "aneutronic_fusion", "sr_mission_units_interstellar"),
}
MISSION = {t: pm for t, (_, pm, _, _) in TIERS.items()}
DECISION = {2: "te_decision_space_mission_moon", 3: "te_decision_space_mission_mars",
            4: "te_decision_space_mission_solar", 5: "te_decision_space_mission_deep_space",
            6: "te_decision_space_mission_interstellar"}
CEILING = {t: f"pm_sr_mission_ceiling_{key}" for t, (key, _, _, _) in TIERS.items()}
NONE = "pm_sr_mission_ceiling_none"
ALL_TECH = frozenset(tech for _, _, tech, _ in TIERS.values() if tech)
MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "mars_landing", "interstellar_probe",
              "solar_colonization")
BASE_PRICE = 200  # launch_capacity's base price (the methods' cost comments)


def read(path):
    """The file without comments (a `#` inside a quoted string is kept)."""
    text = path.read_text(encoding="utf-8-sig")
    return re.sub(r'"[^"\n]*"|#[^\n]*', lambda m: m.group(0) if m.group(0).startswith('"') else "", text)


def blocks(text):
    """Top-level `name = { body }` entries, as raw body text."""
    out, pos = {}, 0
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        if m.start() < pos:
            continue
        depth = 0
        for i in range(m.end() - 1, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out[m.group(1)] = text[m.end():i]
                    pos = i
                    break
    return out


def scalars(text):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"(?m)^(\w+)\s*=\s*(-?[\d.]+)\s*$", text)}


_OPS = frozenset(("=", "?=", "<", ">", "<=", ">=", "!="))


def parse(text):
    """(key, op, value) triples, a block's value a list of them; a bare list item is (item, None, None)."""
    tokens = ParadoxFileParser().tokenize(text)
    pos = 0

    def body():
        nonlocal pos
        out = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                return out
            if pos >= len(tokens) or tokens[pos] not in _OPS:
                out.append((key, None, None))
                continue
            op, value = tokens[pos], tokens[pos + 1]
            pos += 2
            out.append((key, op, body() if value == "{" else value))
        return out

    return body()


def field(triples, key):
    return next((v for k, _, v in triples if k == key), None)


def cut(x):
    """The engine's fixed point: five decimals, toward zero."""
    return math.trunc(round(x * 100000, 6)) / 100000


class Country:
    """An AI country with a Space Program, as the pass reads it."""

    def __init__(self, income, price=BASE_PRICE, mission=4, ceiling=None, throughput_modifier=0.0,
                 funding=None, techs=ALL_TECH, ai=True, in_default=False, bankrupt=False, program=True):
        self.income = income
        self.price = max(price, BASE_PRICE)   # sr_launch_capacity_unit_price: never below base
        self.throughput_modifier = throughput_modifier
        self.funding = dict(funding or {})    # milestone -> level, all billed
        self.techs = set(techs)
        self.ai = ai
        self.in_default = in_default
        self.modifiers = {"declared_bankruptcy"} if bankrupt else set()
        self.vars = {}       # name -> value
        self.expiry = {}     # timed variable -> months left
        self.pms = {"mission": MISSION[mission], "ceiling": ceiling or NONE} if program else None
        self.colonization_goal = 300.0   # sr_solar_colonization_goal: the Moon's, stage 0
        self.lunar_open = True           # sr_sites_lunar_open
        self.inner_open = True           # sr_colonization_inner_open

    @property
    def mission(self):
        return next(t for t, pm in MISSION.items() if pm == self.pms["mission"])

    @property
    def ceiling(self):
        return 0 if self.pms["ceiling"] == NONE else next(t for t, pm in CEILING.items() if pm == self.pms["ceiling"])

    def tick(self, months=1):
        for name in list(self.expiry):
            self.expiry[name] -= months
            if self.expiry[name] <= 0:
                del self.expiry[name]
                self.vars.pop(name, None)


class Script:
    """A fail-closed evaluator for the pass, its values and triggers."""

    COMPARE = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b,
               ">=": lambda a, b: a >= b, "=": lambda a, b: a == b}

    def __init__(self):
        self.values = {**blocks(read(SR_VALUES)), **blocks(read(VALUES))}
        self.constants = {**scalars(read(SR_VALUES)), **scalars(read(VALUES))}
        self.triggers = {**blocks(read(SR_TRIGGERS)), **blocks(read(TRIGGERS))}
        self.effects = blocks(read(EFFECTS))
        self.globals = set()
        self.log = []
        self.ignore_ceiling_switch = False   # a switch that doesn't take, for the self-check
        self.switches = []                   # (group, method) in the order script switched them
        self._cache = {}

    def body(self, table, name, args=None):
        key = (id(table), name, tuple(sorted((args or {}).items())))
        if key not in self._cache:
            text = table[name]
            for k, v in (args or {}).items():
                text = text.replace(f"${k}$", v)
            assert "$" not in text, f"{name}: unfilled argument"
            self._cache[key] = parse(text)
        return self._cache[key]

    # ---- values ------------------------------------------------------------------------------
    def number(self, token, c):
        if isinstance(token, list):
            return self.evaluate(token, c)
        try:
            return float(token)
        except ValueError:
            pass
        if token.startswith("var:"):
            assert token[4:] in c.vars, f"unguarded read of {token}"
            return float(c.vars[token[4:]])
        if token == "fixed_income":
            return c.income
        if token == "modifier:building_space_program_throughput_add":
            return c.throughput_modifier + self.constants["sr_ai_funding_throughput_per_level"] * sum(c.funding.values())
        if token == "sr_launch_capacity_unit_price":      # its market scopes are the engine's
            return c.price
        if token == "sr_solar_colonization_goal":         # its stage and target are the sites'
            return c.colonization_goal
        m = re.fullmatch(r"sr_funding_(\w+)_level", token)
        if m and m.group(1) in MILESTONES:
            return float(c.funding.get(m.group(1), 0))
        if token in self.constants:
            return self.constants[token]
        assert token in self.values, f"unknown value {token}"
        return self.evaluate(self.body(self.values, token), c)

    def evaluate(self, body, c, result=0.0):
        done = False
        for key, op, value in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    done = False
                if done:
                    continue
                limit = field(value, "limit") or []
                if key == "else" or self.check(limit, c):
                    done = True
                    result = self.evaluate([p for p in value if p[0] != "limit"], c, result)
                continue
            x = self.number(value, c)
            if key == "value":
                result = x
            elif key == "add":
                result += x
            elif key == "subtract":
                result -= x
            elif key == "multiply":
                result *= x
            elif key == "divide":
                result /= x
            elif key == "min":
                result = max(result, x)
            elif key == "max":
                result = min(result, x)
            else:
                raise AssertionError(f"unsupported value step {key}")
            result = cut(result)
        return result

    # ---- triggers ----------------------------------------------------------------------------
    def check(self, body, c):
        for key, op, value in body:
            if not self.condition(key, op, value, c):
                return False
        return True

    def condition(self, key, op, value, c):
        yes = value == "yes"
        if key == "OR":
            return any(self.condition(*item, c) for item in value)
        if key == "NOT":
            return not self.check(value, c)
        if key == "AND":
            return self.check(value, c)
        if key == "has_variable":
            return value in c.vars
        if key == "has_global_variable":
            return value in self.globals
        if key == "has_modifier":
            return value in c.modifiers
        if key == "in_default":
            return c.in_default == yes
        if key == "is_ai":
            return c.ai == yes
        if key == "has_technology_researched":
            return value in c.techs
        if key == "custom_tooltip":
            return self.check([p for p in value if p[0] != "text"], c)
        if key == "has_building":
            assert value == "building_space_program", value
            return c.pms is not None
        if key == "sr_sites_lunar_open":
            return c.lunar_open == yes
        if key == "sr_colonization_inner_open":
            return c.inner_open == yes
        if key == "any_scope_building":
            return c.pms is not None and self.check(value, c)
        if key == "is_building_type":
            assert value == "building_space_program", value
            return True
        if key == "has_active_production_method":
            return value in c.pms.values()
        m = re.fullmatch(r"sr_milestone_billed_(\w+)", key)
        if m:
            return (m.group(1) in c.funding) == yes
        if key in self.triggers:
            args = {k: v for k, _, v in value} if isinstance(value, list) else None
            assert args is not None or value in ("yes", "no"), f"{key} = {value}"
            return self.check(self.body(self.triggers, key, args), c) == (yes or args is not None)
        if op == "?=":
            assert key.startswith("var:"), key
            return key[4:] in c.vars and float(c.vars[key[4:]]) == self.number(value, c)
        assert op in self.COMPARE, f"unknown trigger {key} {op} {value}"
        return self.COMPARE[op](self.number(key, c), self.number(value, c))

    # ---- effects ----------------------------------------------------------------------------
    def run(self, name, c, args=None):
        self.execute(self.body(self.effects, name, args), c)

    def execute(self, body, c):
        done = False
        for key, op, value in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    done = False
                if done:
                    continue
                if key == "else" or self.check(field(value, "limit") or [], c):
                    done = True
                    self.execute([p for p in value if p[0] != "limit"], c)
                continue
            if key == "set_variable":
                name, raw = field(value, "name"), field(value, "value")
                c.vars[name] = raw if raw == "yes" else self.number(raw, c)
                days = field(value, "days")
                if days is not None:
                    c.expiry[name] = int(days) // 30
            elif key == "change_variable":
                name = field(value, "name")
                assert name in c.vars, f"change_variable on unset {name}"
                c.vars[name] = c.vars[name] + self.number(field(value, "add"), c)
            elif key == "remove_variable":
                assert value in c.vars, f"remove_variable on unset {value}"
                del c.vars[value]
                c.expiry.pop(value, None)
            elif key == "set_global_variable":
                self.globals.add(field(value, "name"))
            elif key == "debug_log":
                self.log.append(value.strip('"'))
            elif key == "activate_production_method":
                assert field(value, "building_type") == "building_space_program"
                pm = field(value, "production_method")
                group = "ceiling" if pm.startswith("pm_sr_mission_ceiling_") else "mission"
                assert pm in (CEILING.values() if group == "ceiling" else MISSION.values()) or pm == NONE, pm
                assert pm != c.pms[group], f"a switch to the method already active: {pm}"
                if not (group == "ceiling" and self.ignore_ceiling_switch):
                    c.pms[group] = pm
                    self.switches.append((group, pm))
            elif key == "custom_tooltip":
                self.execute([p for p in value if p[0] != "text"], c)
            elif key == "every_scope_state":   # the one state that matters: the program's
                if self.check(field(value, "limit") or [], c):
                    self.execute([p for p in value if p[0] != "limit"], c)
            elif key == "remove_building":
                assert value == "building_space_program", value
                c.pms = None
            elif key in self.effects and value == "yes":
                self.run(key, c)
            else:
                raise AssertionError(f"unsupported effect {key}")

    def month(self, c, n=1):
        for _ in range(n):
            self.run("sr_ai_mission_budget_monthly", c)
            c.tick()

    def take_decision(self, name, c):
        """A decision's when_taken, as written."""
        decision = parse(blocks(read(DECISIONS))[name])
        self.execute(field(decision, "when_taken"), c)

    def value(self, name, c):
        return self.number(name, c)

    def holds(self, name, c, args=None):
        return self.check(self.body(self.triggers, name, args), c)


def valid(c):
    """The program's mission is one its active Mission Limit method allows (the missions'
    unlocking_production_methods, as test_each_mission_lists_the_ceilings_that_allow_it holds them)."""
    return c.mission == 1 or c.pms["ceiling"] == NONE or c.ceiling >= c.mission


def income_for(share, units, price=BASE_PRICE, throughput=1.0):
    """The fixed income at which a mission of `units` costs `share` of it."""
    return units * throughput * price / share


class StructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pms = blocks(read(PMS))
        cls.ceiling_pms = blocks(read(CEILING_PMS))
        cls.values = blocks(read(VALUES))
        cls.constants = scalars(read(VALUES))

    def test_the_rule_numbers(self):
        # 10% to climb, 20% to step down, six reviews; the anchors are in the values file.
        self.assertEqual(self.constants["sr_ai_mission_share_up"], 0.1)
        self.assertEqual(self.constants["sr_ai_mission_share_down"], 0.2)
        self.assertEqual(self.constants["sr_ai_mission_over_months_limit"], 6)
        self.assertLess(self.constants["sr_ai_mission_share_up"], self.constants["sr_ai_mission_share_down"])

    def test_the_ceiling_group_is_on_the_building(self):
        building = blocks(read(BUILDINGS))["REPLACE_OR_CREATE:building_space_program"]
        self.assertIn("pmg_space_program_mission_ceiling",
                      [k for k, _, _ in field(parse(building), "production_method_groups")])
        group = parse(blocks(read(CEILING_PMG))["pmg_space_program_mission_ceiling"])
        self.assertEqual([k for k, _, _ in field(group, "production_methods")], [NONE, *CEILING.values()])
        self.assertIsNone(field(group, "ai_selection"))

    def test_ceilings_carry_nothing_and_are_ratcheted(self):
        self.assertEqual(set(self.ceiling_pms), {NONE, *CEILING.values()})
        for pm, text in self.ceiling_pms.items():
            with self.subTest(pm=pm):
                body = parse(text)
                keys = {k for k, _, _ in body}
                self.assertLessEqual(keys, {"texture", "is_default", "is_hidden_when_unavailable",
                                            "unlocking_production_methods"})
                self.assertEqual(field(body, "is_hidden_when_unavailable"), "yes")
                self.assertEqual([k for k, _, _ in field(body, "unlocking_production_methods")], [pm])
                self.assertEqual(field(body, "is_default"), "yes" if pm == NONE else None)

    def test_each_mission_lists_the_ceilings_that_allow_it(self):
        for tier, pm in MISSION.items():
            with self.subTest(pm=pm):
                body = parse(self.pms[pm])
                unlocking = field(body, "unlocking_production_methods")
                if tier == 1:
                    # A group's first method needs no gate: Earth Orbit is always there.
                    self.assertIsNone(unlocking)
                    continue
                self.assertEqual({k for k, _, _ in unlocking}, {NONE} | {CEILING[t] for t in CEILING if t >= tier})
                self.assertIsNone(field(body, "replacement_if_valid"))

    def test_under_each_ceiling_the_dearest_valid_mission_is_the_ceilings_own(self):
        # What the engine's most_productive AI can climb to, with every technology.
        for ceiling in [NONE, *CEILING.values()]:
            active = {ceiling}
            valid = [t for t, pm in MISSION.items()
                     if t == 1 or active & {k for k, _, _ in field(parse(self.pms[pm]), "unlocking_production_methods")}]
            with self.subTest(ceiling=ceiling):
                self.assertEqual(max(valid), 6 if ceiling == NONE else next(t for t, p in CEILING.items() if p == ceiling))

    def test_the_mission_group_still_climbs(self):
        # most_profitable would pull every AI program down to Earth Orbit, which no ceiling gates.
        group = parse(blocks(read(PMGS))["REPLACE_OR_CREATE:pmg_base_building_space_program"])
        self.assertEqual(field(group, "ai_selection"), "most_productive")

    def test_tiers_follow_the_methods(self):
        values = {**blocks(read(SR_VALUES)), **self.values}
        for tier, (key, pm, tech, units) in TIERS.items():
            with self.subTest(pm=pm):
                self.assertIn(f"value = {units}", values[f"sr_ai_mission_bill_{key}"])
                self.assertIn(f"subtract = sr_ai_mission_bill_{key}", values[f"sr_ai_mission_room_{key}"])
                body = parse(self.pms[pm])
                techs = field(body, "unlocking_technologies")
                self.assertEqual(tech, techs[0][0] if techs else None)
                if tech:
                    self.assertIn(f"has_technology_researched = {tech}", values["sr_ai_mission_tech_tier"])
                    self.assertIn(f"has_technology_researched = {tech}", values["sr_ai_mission_target_tier"])
                    self.assertIn(f"var:sr_ai_mission_ceiling >= {tier}", values["sr_ai_mission_target_tier"])
                self.assertIn(f"PM = {pm} }}", values["sr_ai_mission_tier_current"])
                self.assertIn(f"PM = {CEILING[tier]} }}", values["sr_ai_mission_ceiling_tier_active"])

    def test_funding_step_is_the_funding_modifier(self):
        modifier = parse(blocks(read(MODIFIERS))["sr_funding_throughput"])
        self.assertEqual(float(field(modifier, "building_space_program_throughput_add")),
                         self.constants["sr_ai_funding_throughput_per_level"])
        funding = self.values["sr_ai_program_funding_levels"]
        for m in MILESTONES:
            with self.subTest(milestone=m):
                self.assertIn(f"sr_milestone_billed_{m} = yes }}\n\t\tadd = sr_funding_{m}_level", funding)

    def test_the_pass_runs_monthly_whatever_the_rule(self):
        on_action = parse(blocks(read(ON_ACTIONS))["space_race_on_action"])
        top = [(k, v) for k, _, v in field(on_action, "effect")]
        self.assertIn(("sr_ai_mission_budget_monthly", "yes"), top)

    def test_five_years_before_climbing_again(self):
        effects = blocks(read(EFFECTS))
        self.assertRegex(effects["sr_ai_mission_start_cooldown"],
                         r"name = sr_ai_mission_cooldown value = yes days = 1825 \}")
        # Started by the rule's two step-downs only, never by a step back to the ceiling.
        self.assertEqual(effects["sr_ai_mission_budget_review"].count("sr_ai_mission_start_cooldown = yes"), 2)
        self.assertNotIn("sr_ai_mission_cooldown value", effects["sr_ai_mission_budget_review"])

    def test_every_mission_decision_lifts_a_players_ceiling_before_the_switch(self):
        decisions = blocks(read(DECISIONS))
        for tier in range(2, 7):
            name = DECISION[tier]
            with self.subTest(decision=name):
                taken = decisions[name][decisions[name].index("when_taken"):decisions[name].index("ai_chance")]
                lift = re.search(r"limit = \{ is_ai = no \}\s*sr_ai_mission_ceiling_lift = yes", taken)
                self.assertIsNotNone(lift)
                self.assertLess(lift.start(), taken.index(f"production_method = {MISSION[tier]}"))

    def test_funding_buttons_follow_the_budget(self):
        buttons = blocks(read(BUTTONS))
        for m in MILESTONES:
            with self.subTest(milestone=m):
                up = buttons[f"sr_btn_fund_up_{m}"]
                self.assertRegex(up, r"limit = \{ sr_ai_space_fund_up_blocked = yes \}\s*multiply = 0")
                down = buttons[f"sr_btn_fund_down_{m}"]
                self.assertRegex(down, r"limit = \{ sr_ai_space_fund_down_due = yes \}\s*add = 100")

    def test_mission_decisions_never_take_an_ai_past_its_ceiling(self):
        decisions = blocks(read(DECISIONS))
        for name, key in (("te_decision_space_mission_moon", "moon"), ("te_decision_space_mission_mars", "mars"),
                          ("te_decision_space_mission_solar", "solar"),
                          ("te_decision_space_mission_deep_space", "deep_space"),
                          ("te_decision_space_mission_interstellar", "interstellar")):
            with self.subTest(decision=name):
                text = decisions[name]
                ai_chance = text[text.index("ai_chance"):]
                self.assertIn(f"sr_ai_mission_ceiling_allows_{key} = yes", ai_chance)
                self.assertIn("sr_ai_space_budget_in_trouble = no", ai_chance)
                self.assertNotIn("net_fixed_income", ai_chance)
                tier = next(t for t, v in TIERS.items() if v[0] == key)
                self.assertIn(f"production_method = {MISSION[tier]}", text[:text.index("ai_chance")])
        found = decisions["te_decision_found_space_program"]
        self.assertIn("sr_ai_may_found_space_program = yes", found[found.index("ai_chance"):])

    def test_an_ai_builds_a_program_only_by_the_means_test(self):
        building = parse(blocks(read(BUILDINGS))["REPLACE_OR_CREATE:building_space_program"])
        can_build = field(building, "can_build_government")
        self.assertEqual(can_build, [("owner", "?=", [("sr_ai_may_build_space_program", "=", "yes")])])
        triggers = blocks(read(TRIGGERS))
        self.assertIn("is_ai = no", triggers["sr_ai_may_build_space_program"])
        self.assertIn("sr_ai_may_found_space_program = yes", triggers["sr_ai_may_build_space_program"])
        self.assertNotIn("sr_ai_should_participate", triggers["sr_ai_may_found_space_program"], "a means test, no rank")
        loc = (ROOT / "localization/english/te_miscellaneous_l_english.yml").read_text(encoding="utf-8-sig")
        self.assertRegex(loc, r'(?m)^ sr_ai_program_means_tt:0 "[^"]+"$')

    def test_the_guard_line_and_the_demolition_count_are_named(self):
        self.assertEqual(self.constants["sr_ai_mission_guard_share"], 0.75)
        self.assertEqual(self.constants["sr_ai_program_unaffordable_months_limit"], 12)
        demolish = blocks(read(EFFECTS))["sr_ai_program_demolish"]
        self.assertRegex(demolish, r"name = sr_ai_program_demolished value = yes days = 1825 \}")
        self.assertIn("remove_building = building_space_program", demolish)

    def test_every_ceiling_has_its_words(self):
        loc = LOC.read_text(encoding="utf-8-sig")
        for key in ["pmg_space_program_mission_ceiling", NONE, f"{NONE}_desc",
                    *CEILING.values(), *(f"{pm}_desc" for pm in CEILING.values())]:
            with self.subTest(key=key):
                self.assertRegex(loc, rf'(?m)^ {key}:0 "[^"]+"$')


class PassTest(unittest.TestCase):
    """The pass as written, month by month."""

    def setUp(self):
        self.script = Script()
        self.solar = TIERS[4][3]

    def units(self, tier):
        return self.script.constants[TIERS[tier][3]]

    def test_climbs_to_the_dearest_mission_within_a_tenth(self):
        for tier in TIERS:
            for share, expect in ((0.099, tier), (0.101, max(tier - 1, 1))):
                if tier == 1 and share > 0.1:
                    continue
                with self.subTest(tier=tier, share=share):
                    c = Country(income_for(share, self.units(tier)), mission=1)
                    self.script.month(c)
                    self.assertEqual((c.mission, c.ceiling), (expect, expect))
                    self.assertEqual(c.vars["sr_ai_mission_ceiling"], expect)

    def test_technology_bounds_the_climb_not_the_ceiling(self):
        c = Country(income_for(0.001, self.units(6)), mission=1, techs={"space_exploration", "knowledge_economy"})
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (3, 6))

    def test_holds_inside_the_band(self):
        # Mars at 15%: over the climbing share, under the step-down one, for years.
        c = Country(income_for(0.15, self.units(3)), mission=3)
        self.script.month(c, 36)
        self.assertEqual((c.mission, c.ceiling), (3, 3))
        self.assertNotIn("sr_ai_mission_over_months", c.vars)

    def test_steps_down_after_six_months_over(self):
        # Solar at 30%: the dearest within 10% is the Moon (1,500 against 10,000: 4.5%), not Mars (15%).
        c = Country(income_for(0.30, self.units(4)), mission=4)
        self.script.month(c, 5)
        self.assertEqual((c.mission, c.ceiling), (4, 4), "held, climbing no further")
        self.assertEqual(c.vars["sr_ai_mission_over_months"], 5)
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        self.assertIn("sr_ai_mission_cooldown", c.vars)

    def test_one_month_under_restarts_the_count(self):
        c = Country(income_for(0.30, self.units(4)), mission=4)
        self.script.month(c, 5)
        c.income *= 2   # 15%
        self.script.month(c)
        c.income /= 2
        self.script.month(c, 5)
        self.assertEqual(c.mission, 4)

    def test_five_years_before_it_climbs_again(self):
        c = Country(income_for(0.30, self.units(4)), mission=4)
        self.script.month(c, 6)
        self.assertEqual(c.mission, 2)
        c.income *= 100   # rich at once
        self.script.month(c, 58)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        self.script.month(c, 3)
        self.assertEqual((c.mission, c.ceiling), (6, 6))

    def test_default_and_bankruptcy_drop_to_earth_orbit_at_once(self):
        for kind in ("in_default", "bankrupt"):
            with self.subTest(kind=kind):
                c = Country(income_for(0.01, self.units(4)), mission=4, funding={"solar_colonization": 3},
                            **{kind: True})
                self.assertTrue(self.script.holds("sr_ai_space_fund_up_blocked", c))
                self.assertTrue(self.script.holds("sr_ai_space_fund_down_due", c))
                self.script.month(c)
                self.assertEqual((c.mission, c.ceiling), (1, 1))
                self.script.month(c, 24)
                self.assertEqual((c.mission, c.ceiling), (1, 1))

    def test_funding_goes_first(self):
        # Mars at 8% unfunded: four levels make it 16%. No fifth level (18% > 10% after it), no cut (under 20%).
        c = Country(income_for(0.08, self.units(3)), mission=3, funding={"mars_landing": 4})
        self.script.month(c)
        self.assertEqual(c.mission, 3)
        self.assertTrue(self.script.holds("sr_ai_space_fund_up_blocked", c))
        self.assertFalse(self.script.holds("sr_ai_space_fund_down_due", c))
        # Eight levels: 24%, cut the funding; the mission itself (8%) is not stepped down.
        c.funding["mars_landing"] = 8
        self.assertTrue(self.script.holds("sr_ai_space_fund_down_due", c))
        self.script.month(c, 12)
        self.assertEqual(c.mission, 3)
        # One level with room: 8% + 2% is within the tenth.
        c.funding["mars_landing"] = 0
        c.income *= 1.01
        self.assertFalse(self.script.holds("sr_ai_space_fund_up_blocked", c))

    def test_a_player_is_never_reviewed(self):
        c = Country(income_for(5.0, self.units(4)), mission=4, ai=False, funding={"solar_colonization": 9})
        self.script.month(c, 12)
        self.assertEqual((c.mission, c.pms["ceiling"]), (4, NONE))
        self.assertEqual(c.vars, {})
        self.assertFalse(self.script.holds("sr_ai_space_fund_up_blocked", c))
        self.assertFalse(self.script.holds("sr_ai_space_fund_down_due", c))

    def test_a_country_the_player_takes_over_loses_the_ceiling(self):
        c = Country(income_for(0.30, self.units(4)), mission=4)
        self.script.month(c, 6)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        c.ai = False
        self.script.month(c)
        self.assertEqual((c.mission, c.pms["ceiling"]), (2, NONE), "the mission is the player's to change")
        self.assertEqual(c.vars, {})

    def test_a_players_begin_decision_lifts_the_ceiling_first(self):
        # A player takes over an AI country held at the Moon, with the technology to Mars, and
        # takes Begin the Mars Mission before the monthly pass has lifted the ceiling.
        # The Moon at 9%, Mars at 30%: the AI is held at the Moon.
        c = Country(income_for(0.09, self.units(2)), mission=1, techs={"space_exploration", "knowledge_economy"})
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        c.ai = False
        self.script.switches.clear()
        self.script.take_decision(DECISION[3], c)
        self.assertEqual(self.script.switches, [("ceiling", NONE), ("mission", MISSION[3])])
        self.assertTrue(valid(c), "the engine would switch the program off a mission past its ceiling")

    def test_an_ai_begin_decision_leaves_its_ceiling(self):
        c = Country(income_for(0.001, self.units(6)), mission=1, techs={"space_exploration"})
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 6))
        c.techs.add("knowledge_economy")
        self.script.switches.clear()
        self.script.take_decision(DECISION[3], c)
        self.assertEqual(self.script.switches, [("mission", MISSION[3])])
        self.assertTrue(valid(c))

    def test_a_climb_past_the_ceiling_is_stepped_back_at_the_next_review(self):
        # Mars chosen (Solar would cost 15%, in the band); the engine jumps to Solar regardless.
        c = Country(income_for(0.15, self.units(4)), mission=1)
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (3, 3))
        c.pms["mission"] = MISSION[4]
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (3, 3))
        self.assertTrue(self.script.log[0].startswith("TE_SELF_CHECK BROKEN sr_ai_mission_ceiling "))
        self.assertNotIn("sr_ai_mission_cooldown", c.vars, "a step back starts no five years' wait")
        self.script.month(c, 24)
        self.assertEqual((c.mission, c.ceiling), (3, 3))
        c.income *= 2   # Solar at 7.5%: it climbs at once
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (4, 4))

    def test_a_climb_past_the_ceiling_into_the_red_is_stepped_back_at_once(self):
        # The Moon chosen (Solar at 30%); the engine jumps to Solar: back at the next review,
        # not after six.
        c = Country(income_for(0.30, self.units(4)), mission=1)
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        c.pms["mission"] = MISSION[4]
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        self.assertNotIn("sr_ai_mission_cooldown", c.vars)
        self.script.month(c)
        self.assertNotIn("sr_ai_mission_over_months", c.vars, "the Moon itself is within the band")

    # ---- the milestone guard ----------------------------------------------------------------
    def over_on_solar(self, **kw):
        """Solar at 30%: over the step-down share; the dearest within 10% is the Moon."""
        return Country(income_for(0.30, self.units(4)), mission=4, **kw)

    def run_milestone(self, c, milestone, share):
        goal = c.colonization_goal if milestone == "solar_colonization" else self.script.value(f"sr_{milestone}_goal", c)
        c.vars[f"sr_active_{milestone}"] = "yes"
        c.vars[f"sr_progress_{milestone}"] = goal * share

    def test_the_guard_holds_the_step_at_76_percent(self):
        c = self.over_on_solar()
        self.run_milestone(c, "solar_colonization", 0.76)
        self.script.month(c, 12)
        self.assertEqual((c.mission, c.ceiling), (4, 4))
        self.assertGreaterEqual(c.vars["sr_ai_mission_over_months"], 6, "the count stays at its limit")
        self.assertNotIn("sr_ai_mission_cooldown", c.vars)

    def test_the_guard_lets_the_step_go_at_74_percent(self):
        c = self.over_on_solar()
        self.run_milestone(c, "solar_colonization", 0.74)
        self.script.month(c, 6)
        self.assertEqual((c.mission, c.ceiling), (2, 2))

    def test_default_steps_past_the_guard_at_once(self):
        c = self.over_on_solar(in_default=True)
        self.run_milestone(c, "solar_colonization", 0.90)
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (1, 1))

    def test_the_step_comes_at_the_first_review_after_the_milestone_ends(self):
        c = self.over_on_solar()
        self.run_milestone(c, "solar_colonization", 0.80)
        self.script.month(c, 9)
        self.assertEqual(c.mission, 4)
        del c.vars["sr_active_solar_colonization"]   # founded its colony, or failed
        del c.vars["sr_progress_solar_colonization"]
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (2, 2))
        self.assertIn("sr_ai_mission_cooldown", c.vars)

    def test_the_guard_steps_only_as_far_as_the_milestone_allows(self):
        # A Mars Landing at 80% on Solar Colonization: down to the Mars Mission, not the Moon.
        c = self.over_on_solar()
        self.run_milestone(c, "mars_landing", 0.80)
        self.script.month(c, 6)
        self.assertEqual((c.mission, c.ceiling), (3, 3))
        self.assertIn("sr_ai_mission_cooldown", c.vars)
        self.assertIn("sr_ai_mission_over_months", c.vars, "the rest of the step waits on the landing")

    def test_a_holders_colonization_only_pauses_so_it_is_not_guarded(self):
        c = self.over_on_solar()
        c.vars["sr_colony_count"] = 1
        self.run_milestone(c, "solar_colonization", 0.90)
        self.script.month(c, 6)
        self.assertEqual(c.mission, 2)

    def test_outer_worlds_only_guard_deep_space(self):
        c = Country(income_for(0.30, self.units(5)), mission=5)
        c.lunar_open = c.inner_open = False
        self.run_milestone(c, "solar_colonization", 0.80)
        self.script.month(c, 6)
        self.assertEqual(c.mission, 5)
        c.inner_open = True
        self.script.month(c)
        self.assertEqual(c.mission, 4, "Solar Colonization carries it again")

    # ---- a program even Earth Orbit is too dear for ------------------------------------------------
    def test_a_year_over_on_earth_orbit_pulls_the_program_down(self):
        c = Country(income_for(0.25, self.units(1)), mission=1)
        self.script.month(c, 11)
        self.assertIsNotNone(c.pms)
        self.assertEqual(c.vars["sr_ai_program_unaffordable_months"], 11)
        self.script.month(c)
        self.assertIsNone(c.pms)
        self.assertEqual(set(c.vars), {"sr_ai_program_demolished"})
        # Five years (60 months) from the review, which the month's tick then counts down.
        self.assertEqual(c.expiry["sr_ai_program_demolished"], 59, "five years before it founds one again")
        self.assertTrue(self.script.log[-1].startswith("TE_SR_AI_PROGRAM demolished "))

    def test_one_review_under_ends_the_count(self):
        c = Country(income_for(0.25, self.units(1)), mission=1)
        self.script.month(c, 11)
        c.income *= 2   # 12.5%
        self.script.month(c)
        self.assertNotIn("sr_ai_program_unaffordable_months", c.vars)
        c.income /= 2
        self.script.month(c, 11)
        self.assertIsNotNone(c.pms)

    def test_a_player_never_counts_and_a_takeover_stops_the_count(self):
        c = Country(income_for(0.25, self.units(1)), mission=1, ai=False)
        self.script.month(c, 24)
        self.assertIsNotNone(c.pms)
        self.assertNotIn("sr_ai_program_unaffordable_months", c.vars)
        c = Country(income_for(0.25, self.units(1)), mission=1)
        self.script.month(c, 8)
        c.ai = False
        self.script.month(c)
        self.assertNotIn("sr_ai_program_unaffordable_months", c.vars)
        c.ai = True
        self.script.month(c, 11)
        self.assertIsNotNone(c.pms, "the count started again from zero")

    def test_founding_waits_five_years_after_a_demolition(self):
        c = Country(income_for(0.25, self.units(1)), mission=1)
        self.script.month(c, 12)
        c.income *= 10   # Earth Orbit at 2.5%: affordable at once
        self.assertFalse(self.script.holds("sr_ai_may_found_space_program", c))
        c.tick(58)   # 59 months of the 60 gone
        self.assertFalse(self.script.holds("sr_ai_may_found_space_program", c))
        c.tick(1)
        self.assertTrue(self.script.holds("sr_ai_may_found_space_program", c))
        self.assertTrue(self.script.holds("sr_ai_may_build_space_program", c))

    def test_founding_asks_earth_orbit_within_the_climbing_share(self):
        units = self.units(1)
        for share, may in ((0.099, True), (0.10, True), (0.101, False)):
            with self.subTest(share=share):
                c = Country(income_for(share, units), program=False)
                self.assertEqual(self.script.holds("sr_ai_may_found_space_program", c), may)
                self.assertEqual(self.script.holds("sr_ai_may_build_space_program", c), may)
        for kind in ("in_default", "bankrupt"):
            with self.subTest(kind=kind):
                c = Country(income_for(0.01, units), program=False, **{kind: True})
                self.assertFalse(self.script.holds("sr_ai_may_found_space_program", c))
        c = Country(income_for(5.0, units), program=False, ai=False)
        self.assertTrue(self.script.holds("sr_ai_may_build_space_program", c), "a player's government always may")

    def test_a_lost_program_leaves_no_record(self):
        c = Country(income_for(0.05, self.units(4)), mission=1)
        self.script.month(c)
        c.pms = None
        self.script.month(c)
        self.assertEqual(c.vars, {})

    def test_the_self_check_reads_ok_after_a_year_held_below_the_technology(self):
        c = Country(income_for(0.30, self.units(4)), mission=4)
        self.script.month(c, 6 + 12)
        self.assertEqual(c.mission, 2)
        self.assertEqual(len(self.script.log), 1)
        self.assertTrue(self.script.log[0].startswith("TE_SELF_CHECK OK sr_ai_mission_ceiling "))

    def test_the_self_check_reads_broken_when_the_engine_climbs_past(self):
        c = Country(income_for(0.05, self.units(2)), mission=1)
        self.script.month(c)
        self.assertEqual(c.mission, 2)
        c.pms["mission"] = MISSION[4]   # the engine's AI, past the Moon ceiling
        self.script.month(c)
        self.assertTrue(self.script.log[0].startswith("TE_SELF_CHECK BROKEN sr_ai_mission_ceiling "))

    def test_a_climb_within_the_ceiling_after_a_new_technology_is_not_broken(self):
        # Rich, with the technology to Mars: ceiling 6, mission 3. Cislunar Infrastructure arrives
        # between reviews and the engine's AI (or Begin Solar Colonization) climbs within the ceiling.
        c = Country(income_for(0.001, self.units(6)), mission=1, techs={"space_exploration", "knowledge_economy"})
        self.script.month(c)
        self.assertEqual((c.mission, c.ceiling), (3, 6))
        c.techs.add("cislunar_infrastructure")
        c.pms["mission"] = MISSION[4]
        self.script.month(c, 3)
        self.assertEqual(self.script.log, [])
        self.assertEqual((c.mission, c.ceiling, c.vars["sr_ai_mission_target"]), (4, 6, 4))

    def test_the_self_check_reads_broken_when_the_mission_falls_below_the_pass(self):
        c = Country(income_for(0.06, self.units(3)), mission=1)   # Solar would be 12%
        self.script.month(c)
        self.assertEqual(c.mission, 3)
        c.pms["mission"] = MISSION[2]   # moved down by something other than the pass
        self.script.month(c)
        self.assertEqual(len(self.script.log), 1)
        self.assertTrue(self.script.log[0].startswith("TE_SELF_CHECK BROKEN sr_ai_mission_ceiling "))

    def test_the_self_check_reads_broken_when_the_ceiling_never_takes(self):
        self.script.ignore_ceiling_switch = True
        c = Country(income_for(0.05, self.units(2)), mission=1)
        self.script.month(c, 2)
        self.assertEqual(self.script.log, [], "a program on Any Mission at one review after a ceiling may be new")
        self.script.month(c)
        self.assertEqual(len(self.script.log), 1)
        self.assertIn("still on Any Mission at two monthly reviews in a row", self.script.log[0])

    def test_nothing_reads_a_variable_it_has_not_set(self):
        # The evaluator fails on an unguarded var: read; a fresh program, a player's and a
        # lost one each run every branch's first month.
        for c in (Country(1e9, mission=1), Country(1.0, mission=6), Country(1e6, ai=False),
                  Country(1e6, program=False), Country(1e6, mission=3, in_default=True)):
            self.script.month(c, 2)


# The owner's Singapore game, 1958.2.27 (the 2026-11-15 save study's fiscal extract). Own revenue
# is every income line but the investment pool's transfer, the stand-in for fixed_income; the price
# is the market's, as the building paid it; throughput and funding as the save holds them.
#   tag: (own revenue, Launch Capacity price index, throughput, funding levels, mission, trouble)
CASES_1958 = {
    "GER": (9_242_000, 1.70, 2.56, 7, 4, None),
    "UNA": (2_952_000, 1.62, 1.18, 0, 3, None),
    "ITA": (622_000, 1.21, 1.18, 0, 4, "bankrupt"),
    "G20": (1_187_000, 1.21, 1.18, 0, 4, None),
    "MEX": (361_000, 1.21, 1.18, 0, 4, "bankrupt"),
    "IDN": (567_000, 1.21, 1.18, 0, 4, "bankrupt"),
    "SCA": (557_000, 1.20, 1.18, 0, 4, "bankrupt"),
    "SIN": (2_616_000, 1.86, 1.15, 0, 4, None),
    "MUG": (731_000, 1.19, 1.18, 0, 4, "bankrupt"),
    "GBR": (1_912_000, 1.06, 1.03, 0, 1, None),
    "OYO": (19_000, 1.21, 1.17, 0, 4, "in_default"),
}
# Pulled down after a year: Earth Orbit's bill over 20% of own revenue at twelve reviews in a row.
DEMOLISHED_1958 = {"ITA", "MEX", "IDN", "SCA", "OYO"}
# What the rule picks: (after the first review, after six).
PICKS_1958 = {
    "GER": (4, 2), "UNA": (3, 1), "ITA": (1, 1), "G20": (4, 1), "MEX": (1, 1), "IDN": (1, 1),
    "SCA": (1, 1), "SIN": (4, 1), "MUG": (1, 1), "GBR": (1, 1), "OYO": (1, 1),
}


def country_1958(revenue, index, throughput, funding, mission, trouble):
    techs = {TIERS[t][2] for t in range(2, mission + 1)}
    return Country(revenue, price=BASE_PRICE * index, mission=mission, throughput_modifier=throughput - 1 - 0.25 * funding,
                   funding={"solar_colonization": funding} if funding else None, techs=techs,
                   in_default=trouble == "in_default", bankrupt=trouble == "bankrupt")


class Singapore1958Test(unittest.TestCase):
    def test_the_nine_solar_programs_and_their_neighbors(self):
        script = Script()
        for tag, case in CASES_1958.items():
            with self.subTest(country=tag):
                c = country_1958(*case)
                script.month(c)
                first = c.mission
                script.month(c, 5)
                self.assertEqual((first, c.mission), PICKS_1958[tag])
                script.month(c, 6)
                self.assertEqual(c.pms is None, tag in DEMOLISHED_1958)


if __name__ == "__main__":
    unittest.main()
