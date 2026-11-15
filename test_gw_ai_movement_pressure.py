"""The AI answers a pressing Environmental Movement with the climate policy it is nearest to adopting.

movement_environmental adds 0.1 activism for each of seven climate policies the
country could adopt but hasn't, and each of the seven in force calms it by 0.1
more, so adopting one is a swing of 0.2. The AI's climate wills read the
movement's support only (gw_ai_sig_movement, at most 10 points), never its
activism. Since 2026-11-15 (the owner: enact "when environmentalists want it
and it wants to keep them calm") a pressing movement adds up to
gw_ai_movement_pressure_weight points to ONE policy, the one the country is
nearest to adopting among those it can carry now, at most once a year, and the
repeal of each of the seven reads the pressure the movement would be under
without the policies in force (global_warming_ai_values.txt, "The
Environmental Movement's pressure").

These tests hold the wiring and, on a small offline model of the movement's
activism and the buttons, that the rule answers the movement without an
adopt-repeal cycle.

Run: python3 -m pytest test_gw_ai_movement_pressure.py -q
"""
import os
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/global_warming_ai_values.txt"
BUTTONS = ROOT / "common/scripted_buttons/global_warming_buttons.txt"
AI_TRIGGERS = ROOT / "common/scripted_triggers/global_warming_ai_triggers.txt"
MOVEMENTS = ROOT / "common/political_movements/new_ideological_movements.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
EFFECTS = ROOT / "common/scripted_effects/global_warming_effects.txt"
SGUIS = ROOT / "common/scripted_guis/global_warming_sguis.txt"

# Vanilla's activism thresholds (game/common/defines/00_defines.txt, 1.15.1):
# protesting and militant; a civil war starts organizing at the militant one.
PROTESTING, MILITANT = 0.5, 0.75
SWING = 0.2  # one policy: its +0.1 "could adopt" line goes, its own -0.1 comes
DRIFT = 0.01  # MOVEMENT_WEEKLY_RADICALISM_CHANGE


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, name
    i = j = m.end()
    depth = 1
    while depth:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    return text[i:j - 1]


def _code(text):
    return re.sub(r"#[^\n]*", "", text)


def _wants():
    """The seven policies the movement's "could adopt" lines count."""
    body = _code(_block(_text(MOVEMENTS), "movement_environmental"))
    return sorted(set(re.findall(r"gw_possible_(\w+) = yes", body)))


def _number(name):
    parser = ParadoxFileParser()
    parser.parse_file(str(VALUES), apply_directives=False)
    return float(parser.data[name][1])


class WiringTest(unittest.TestCase):
    def test_the_seven_are_the_movements_lines(self):
        wants = _wants()
        self.assertEqual(len(wants), 7, wants)
        values = _text(VALUES)
        self.assertEqual(sorted(re.findall(r"(?m)^gw_ai_movement_answer_points_(\w+) = \{", values)), wants)
        self.assertEqual(sorted(re.findall(r"(?m)^gw_ai_can_answer_(\w+) = \{", _text(AI_TRIGGERS))), wants)
        modifiers = _text(MODIFIERS)
        for p in wants:
            name = "reforestation_subsidies_modifier" if p == "reforestation" else f"{p}_modifier"
            with self.subTest(policy=p):
                self.assertIn("country_environmental_movement_radicalism_add = -0.10", _block(modifiers, name))

    def test_the_ramp_runs_from_protesting_to_militant(self):
        body = _code(_block(_text(VALUES), "gw_ai_movement_pressure"))
        self.assertIn("add = this.political_movement_radicalism", body)
        self.assertRegex(body, rf"subtract = {PROTESTING}\b")
        self.assertRegex(body, rf"divide = {MILITANT - PROTESTING}\b")
        self.assertIn("min = 0", body)
        self.assertIn("max = 1", body)

    def test_vanilla_thresholds_match_the_installed_game_when_present(self):
        try:
            import path_constants
            base = path_constants.base_game_path
        except Exception:
            self.skipTest("no game paths")
        path = os.path.join(base, "game", "common", "defines", "00_defines.txt")
        if not os.path.exists(path):
            self.skipTest("no installed Victoria 3")
        text = Path(path).read_text(encoding="utf-8-sig")
        for name, value in (("RADICALISM_PROTESTING_THRESHOLD", PROTESTING), ("RADICALISM_MILITANT_THRESHOLD", MILITANT),
                            ("MIN_RADICALISM_FOR_CIVIL_WAR_PROGRESSION", MILITANT), ("MOVEMENT_WEEKLY_RADICALISM_CHANGE", DRIFT)):
            m = re.search(rf"(?m)^\s*{name}\s*=\s*(-?[\d.]+)", text)
            self.assertIsNotNone(m, name)
            self.assertEqual(float(m.group(1)), value, name)

    def test_the_unmasked_pressure_adds_back_what_the_policies_hold(self):
        body = _code(_block(_text(VALUES), "gw_ai_movement_pressure_unmasked"))
        self.assertIn("any_political_movement = { is_political_movement_type = movement_environmental }", body)
        self.assertIn("subtract = modifier:country_environmental_movement_radicalism_add", body)
        self.assertRegex(body, r"value = gw_ai_wants_policies_held\s+multiply = 0.1")
        held = _code(_block(_text(VALUES), "gw_ai_wants_policies_held"))
        self.assertEqual(sorted(re.findall(r"gw_policy_(\w+)_active = yes", held)), _wants())

    def test_the_answer_is_one_policy_the_country_can_carry(self):
        values = _text(VALUES)
        answer = _code(_block(values, "gw_ai_movement_answer"))
        self.assertEqual(sorted(re.findall(r"min = gw_ai_answer_margin_(\w+)", answer)), _wants())
        for p in _wants():
            with self.subTest(policy=p):
                points = _code(_block(values, f"gw_ai_movement_answer_points_{p}"))
                for cond in ("gw_ai_movement_pressure > 0", "NOT = { has_variable = gw_ai_movement_answered }",
                             f"gw_ai_can_answer_{p} = yes", f"gw_ai_answer_margin_{p} >= gw_ai_movement_answer"):
                    self.assertIn(cond, points)
                self.assertIn("multiply = gw_ai_movement_pressure_weight", points)
                margin = _code(_block(values, f"gw_ai_answer_margin_{p}"))
                self.assertIn(f"gw_ai_can_answer_{p} = yes", margin)
                self.assertIn(f"add = gw_ai_base_margin_{p}", margin)

    def test_can_answer_asks_what_the_adopt_button_asks(self):
        buttons = _text(BUTTONS)
        triggers = _text(AI_TRIGGERS)
        for p in _wants():
            with self.subTest(policy=p):
                chance = _block(buttons, f"gw_{p}_button")
                chance = chance[chance.index("ai_chance"):chance.index("possible")]
                asked = re.findall(r"authority >= (\d+)", chance)
                body = _code(_block(triggers, f"gw_ai_can_answer_{p}"))
                self.assertIn(f"gw_possible_{p} = yes", body)
                self.assertEqual(re.findall(r"authority >= (\d+)", body), asked)
        renewables = _code(_block(triggers, "gw_ai_can_answer_renewable_investment"))
        self.assertIn("in_default = no", renewables)
        self.assertIn("scaled_debt < 0.25", renewables)

    def test_the_yearly_answer_is_set_by_the_seven_adopt_buttons_only(self):
        buttons = _text(BUTTONS)
        setters = re.findall(r"(?m)^(gw_\w+_button) = \{", buttons)
        for button in setters:
            body = _code(_block(buttons, button))
            sets = "name = gw_ai_movement_answered value = yes days = 365" in body
            wanted = button in {f"gw_{p}_button" for p in _wants()}
            with self.subTest(button=button):
                self.assertEqual(sets, wanted)
        for path in (EFFECTS, SGUIS):
            self.assertNotIn("gw_ai_movement_answered", _code(_text(path)), path.name)

    def test_only_the_seven_repeal_reads_the_held_pressure(self):
        values = _text(VALUES)
        repeals = re.findall(r"(?m)^gw_ai_repeal_margin_(\w+) = \{", values)
        for p in repeals:
            with self.subTest(policy=p):
                body = _code(_block(values, f"gw_ai_repeal_margin_{p}"))
                self.assertEqual("subtract = gw_ai_movement_hold_points" in body, p in _wants())


class _Country:
    """One AI country on the offline model: the movement's activism drifts
    DRIFT a week toward its target, which each of the seven in force lowers by
    SWING; every week the AI takes every button whose margin passes (the
    fastest the engine could click), the way global_warming_ai_values.txt
    computes the margins."""

    def __init__(self, base, activism, can=None, weight=None, band=None):
        self.base = dict(base)  # {policy: will less threshold}
        self.can = can or {p: True for p in base}
        self.weight = _number("gw_ai_movement_pressure_weight") if weight is None else weight
        self.band = _number("gw_ai_repeal_band") if band is None else band
        self.target0 = activism  # the movement's target with nothing in force
        self.activism = activism
        self.movement = True
        self.held = set()
        self.cooldown = 0
        self.log = []

    @staticmethod
    def pressure(a):
        return max(0.0, min(1.0, (a - PROTESTING) / (MILITANT - PROTESTING)))

    def week(self, n):
        a = self.activism if self.movement else None
        press = self.pressure(a) if self.movement else 0.0
        unmasked = self.pressure(a + SWING * len(self.held)) if self.movement else 0.0
        options = {p: m for p, m in self.base.items() if p not in self.held and self.can[p]}
        nearest = max(options.values()) if options else None
        for p in sorted(self.base):
            if p in self.held:
                if -self.base[p] - self.band - self.weight * unmasked > 0:
                    self.held.discard(p)
                    self.log.append((n, "repeal", p))
                continue
            points = 0.0
            if press > 0 and self.cooldown <= 0 and self.can[p] and self.base[p] >= nearest:
                points = self.weight * press
            if self.can[p] and self.base[p] + points >= 0:
                self.held.add(p)
                self.cooldown = 52
                self.log.append((n, "adopt", p, points > 0))
        self.cooldown -= 1
        if self.movement:
            target = max(0.0, min(1.0, self.target0 - SWING * len(self.held)))
            step = max(-DRIFT, min(DRIFT, target - self.activism))
            self.activism += step

    def run(self, weeks, start=0):
        for n in range(start, start + weeks):
            self.week(n)
        return self


class ModelTest(unittest.TestCase):
    # Will less threshold at about 1 C with no ministry, from the 2026-11-15
    # saves' central case: adaptation and reforestation close, the carbon tax
    # far.
    BASE = {"climate_adaptation": -6, "reforestation": -9, "renewable_investment": -14, "public_transit": -19,
            "emission_standards": -24, "carbon_tax": -30, "fossil_fuel_divestment": -45}

    def test_a_militant_movement_is_answered_nearest_first_once_a_year_and_nothing_lapses(self):
        c = _Country(self.BASE, activism=0.8).run(52 * 6)
        adopts = [e for e in c.log if e[1] == "adopt"]
        self.assertEqual([e[2] for e in adopts][:2], ["climate_adaptation", "reforestation"])
        self.assertFalse([e for e in c.log if e[1] == "repeal"], c.log)
        weeks = [e[0] for e in adopts]
        self.assertTrue(all(b - a >= 52 for a, b in zip(weeks, weeks[1:])), weeks)
        self.assertLess(c.activism, PROTESTING + 1e-9)

    def test_a_calm_movement_adds_nothing(self):
        c = _Country(self.BASE, activism=0.45).run(52 * 3)
        self.assertEqual(c.log, [])

    def test_nothing_the_country_cannot_carry(self):
        can = {p: p == "carbon_tax" for p in self.BASE}
        c = _Country(self.BASE, activism=1.0, can=can).run(52 * 3)
        self.assertEqual([e[2] for e in c.log], ["carbon_tax"])
        far = dict(self.BASE, carbon_tax=-40)
        self.assertEqual(_Country(far, activism=1.0, can=can).run(52 * 3).log, [])

    def test_the_policies_lapse_when_the_movement_goes_only_below_their_band(self):
        base = {p: m - 15 for p, m in self.BASE.items()}
        base.update(climate_adaptation=-10, reforestation=-20)
        c = _Country(base, activism=0.9).run(52 * 3)
        held = set(c.held)
        self.assertEqual(held, {"climate_adaptation", "reforestation"})
        c.movement = False  # the ministry funded to its maximum: the movement disbands
        c.run(4, start=52 * 3)
        # adaptation is within its band (-10 > -15) and stays; reforestation (-20) lapses
        self.assertEqual(c.held, {"climate_adaptation"})

    def test_no_cycle_at_any_activism_or_weight(self):
        for weight in (20, 30, 40):
            for a0 in (0.55, 0.65, 0.75, 0.9, 1.0):
                with self.subTest(weight=weight, activism=a0):
                    c = _Country(self.BASE, activism=a0, weight=weight).run(52 * 10)
                    self.assertFalse([e for e in c.log if e[1] == "repeal"], c.log)
                    adopted = [e[2] for e in c.log]
                    self.assertEqual(len(adopted), len(set(adopted)), c.log)


if __name__ == "__main__":
    unittest.main()
