"""The AI answers a pressing Environmental Movement with the climate policy it is nearest to adopting.

movement_environmental adds 0.1 activism for each of seven climate policies the
country could adopt but hasn't, and each of the seven in force calms it by 0.1
more, so adopting one is a swing of 0.2. The AI's climate wills read the
movement's support only (gw_ai_sig_movement, at most 10 points), never its
activism. Since 2026-11-15 (the owner: enact "when environmentalists want it
and it wants to keep them calm") a pressing movement adds up to
gw_ai_movement_pressure_weight points to ONE policy, the one the country is
nearest to adopting among those it can carry now, at most once a year. The
repeal of each of the seven reads the pressure the movement would be under
without that one policy, and while a movement exists at most one of the seven
lapses a year (global_warming_ai_values.txt, "The Environmental Movement's
pressure").

These tests pin the script's bodies (a hold multiplied by 0, or the answer's
seed flipped so the pull is off, would otherwise pass: the review of PR #1841
found five such mutations alive) and, on a small offline model of the
movement's activism and the buttons that reads its constants from the script,
that the rule answers the movement without an adopt-repeal cycle.

Run: python3 -m pytest test_gw_ai_movement_pressure.py -q
"""
import math
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
AI_EFFECTS = ROOT / "common/scripted_effects/global_warming_ai_effects.txt"
SGUIS = ROOT / "common/scripted_guis/global_warming_sguis.txt"
CIVIL_WAR = ROOT / "common/on_actions/te_civil_war_on_actions.txt"
DEMOG_TRIGGERS = ROOT / "common/scripted_triggers/te_demog_measure_triggers.txt"

# Vanilla's activism thresholds (game/common/defines/00_defines.txt, 1.15.1):
# protesting and militant; a civil war starts organizing at the militant one.
PROTESTING, MILITANT = 0.5, 0.75
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


def _flat(text):
    """A body without comments, its whitespace collapsed to single spaces."""
    return " ".join(_code(text).split())


def _debt(name, path=AI_TRIGGERS):
    """A treasury trigger's debt bound, after checking it also asks for no default."""
    body = _flat(_block(_text(path), name))
    assert "in_default = no" in body, name
    return float(re.search(r"scaled_debt < ([\d.]+)", body).group(1))


# One policy's swing, as the script states it (its +0.1 "could adopt" line goes,
# its own -0.1 comes); test_the_swing_is_one_line_and_one_modifier checks it.
SWING = _number("gw_ai_movement_policy_swing")


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

    def test_the_swing_is_one_line_and_one_modifier(self):
        """Repealing one of the seven brings back its +0.1 "could adopt" line and
        takes away its own -0.1 radicalism: 0.2, the same for each."""
        body = _code(_block(_text(MOVEMENTS), "movement_environmental"))
        lines = set(re.findall(r'add = \{ value = ([\d.]+) desc = "POLICY_POSSIBLE_\w+" \}', body))
        self.assertEqual(lines, {"0.1"})
        modifiers = _text(MODIFIERS)
        for p in _wants():
            name = "reforestation_subsidies_modifier" if p == "reforestation" else f"{p}_modifier"
            m = re.search(r"country_environmental_movement_radicalism_add = (-?[\d.]+)", _block(modifiers, name))
            with self.subTest(policy=p):
                self.assertAlmostEqual(0.1 - float(m.group(1)), SWING)

    def test_the_hold_is_one_policy_on_the_same_ramp(self):
        """Pinned: the hold reads the activism plus ONE policy's swing (the hold
        as first built added back every policy in force, and from four held it
        was the full weight whatever the movement's state), on the pressure's
        own ramp, times the weight."""
        values = _text(VALUES)
        self.assertEqual(_flat(_block(values, "gw_ai_movement_activism")),
                         "value = 0 every_political_movement = { limit = { is_political_movement_type = "
                         "movement_environmental } add = this.political_movement_radicalism }")
        ramp = f"subtract = {PROTESTING} divide = {MILITANT - PROTESTING} min = 0 max = 1"
        self.assertEqual(_flat(_block(values, "gw_ai_movement_pressure")),
                         f"value = gw_ai_movement_activism {ramp}")
        self.assertEqual(_flat(_block(values, "gw_ai_movement_pressure_without_one")),
                         f"value = gw_ai_movement_activism add = gw_ai_movement_policy_swing {ramp}")
        self.assertEqual(_flat(_block(values, "gw_ai_movement_hold_points")),
                         "value = gw_ai_movement_pressure_without_one multiply = gw_ai_movement_pressure_weight "
                         "if = { limit = { has_variable = gw_ai_movement_lapsed any_political_movement = { "
                         "is_political_movement_type = movement_environmental } } "
                         "add = gw_ai_movement_lapse_lock_points }")
        self.assertEqual(_flat(_block(values, "gw_ai_movement_hold_points_renewable_investment")),
                         "value = 0 if = { limit = { gw_ai_can_keep_renewable_investment = yes } "
                         "add = gw_ai_movement_hold_points }")
        # Larger than any repeal margin: a will is 0..100 + 15, a threshold 25..70.
        self.assertGreaterEqual(_number("gw_ai_movement_lapse_lock_points"), 1000)
        self.assertNotIn("modifier:country_environmental_movement_radicalism_add", _code(values))

    def test_the_answer_is_seeded_below_every_margin_and_points_read_the_pressure(self):
        values = _text(VALUES)
        answer = _flat(_block(values, "gw_ai_movement_answer"))
        self.assertTrue(answer.startswith("value = -1000 "), answer)
        for p in _wants():
            with self.subTest(policy=p):
                self.assertEqual(_flat(_block(values, f"gw_ai_answer_margin_{p}")),
                                 f"value = -1000 if = {{ limit = {{ gw_ai_can_answer_{p} = yes }} "
                                 f"add = 1000 add = gw_ai_base_margin_{p} }}")
                self.assertEqual(_flat(_block(values, f"gw_ai_movement_answer_points_{p}")),
                                 f"value = 0 if = {{ limit = {{ gw_ai_movement_pressure > 0 "
                                 f"NOT = {{ has_variable = gw_ai_movement_answered }} gw_ai_can_answer_{p} = yes "
                                 f"gw_ai_answer_margin_{p} >= gw_ai_movement_answer }} "
                                 f"add = gw_ai_movement_pressure multiply = gw_ai_movement_pressure_weight }}")

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
        renewables = _flat(_block(triggers, "gw_ai_can_answer_renewable_investment"))
        self.assertEqual(renewables, "gw_possible_renewable_investment = yes "
                                     "gw_ai_can_take_on_renewable_investment = yes")

    def test_renewable_investment_is_taken_on_at_a_quarter_and_kept_to_half(self):
        """Its running cost is money, not authority. The movement takes it on
        only with debt under a quarter of the ceiling and holds it only under
        half, the demographic measures' pair, so a country whose debt sits near
        one line doesn't adopt and repeal it yearly."""
        start, keep = _debt("gw_ai_can_take_on_renewable_investment"), _debt("gw_ai_can_keep_renewable_investment")
        self.assertEqual((start, keep), (_debt("te_demog_ms_ai_money_start", DEMOG_TRIGGERS),
                                         _debt("te_demog_ms_ai_money_keep", DEMOG_TRIGGERS)))
        self.assertLess(start, keep)

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

    def test_the_yearly_lapse_is_set_by_the_seven_repeal_buttons_only(self):
        buttons = _text(BUTTONS)
        for button in re.findall(r"(?m)^(gw_\w+_button) = \{", buttons):
            body = _code(_block(buttons, button))
            sets = "name = gw_ai_movement_lapsed value = yes days = 365" in body
            with self.subTest(button=button):
                self.assertEqual(sets, button in {f"gw_remove_{p}_button" for p in _wants()})
        for path in (EFFECTS, SGUIS):
            self.assertNotIn("gw_ai_movement_lapsed", _code(_text(path)), path.name)

    def test_a_revolutions_winner_starts_both_years_afresh(self):
        """Whether a timed variable keeps its countdown on a revolution's
        winner is unread; without one either lock would never expire."""
        self.assertEqual(_flat(_block(_text(AI_EFFECTS), "gw_ai_repair_after_civil_war")),
                         "if = { limit = { has_variable = gw_ai_movement_answered } "
                         "remove_variable = gw_ai_movement_answered } "
                         "if = { limit = { has_variable = gw_ai_movement_lapsed } "
                         "remove_variable = gw_ai_movement_lapsed }")
        won = _flat(_block(_text(CIVIL_WAR), "te_civil_war_on_won"))
        self.assertIn("gw_ai_repair_after_civil_war = yes", won)
        self.assertLess(won.index("gw_ai_repair_after_civil_war"), won.index("te_civil_war_clear"))

    def test_only_the_seven_repeal_reads_the_held_pressure(self):
        values = _text(VALUES)
        repeals = re.findall(r"(?m)^gw_ai_repeal_margin_(\w+) = \{", values)
        for p in repeals:
            with self.subTest(policy=p):
                body = _code(_block(values, f"gw_ai_repeal_margin_{p}"))
                holds = re.findall(r"subtract = (gw_ai_movement_hold_points\w*)", body)
                if p == "renewable_investment":
                    expected = ["gw_ai_movement_hold_points_renewable_investment"]
                elif p in _wants():
                    expected = ["gw_ai_movement_hold_points"]
                else:
                    expected = []
                self.assertEqual(holds, expected)


class _Country:
    """One AI country on the offline model: the movement's activism drifts
    DRIFT a week toward its target, which each of the seven in force lowers by
    SWING; every week the AI takes every button whose margin passes (the
    fastest the engine could click), the way global_warming_ai_values.txt
    computes the margins. The weight, the band, the swing and Renewable
    Investment's two debt bounds are read from the script; the test above pins
    the bodies that combine them.

    hold="one" is the shipped rule (the activism plus one policy's swing);
    hold="all" is the hold as first built (plus every policy in force), kept
    so a test can show what it did. lock=False drops the one-lapse-a-year lock.
    """

    def __init__(self, base, activism, can=None, weight=None, band=None, held=(), hold="one", lock=True):
        self.base = dict(base)  # {policy: will less threshold}
        self.can = can or {p: True for p in base}
        self.weight = _number("gw_ai_movement_pressure_weight") if weight is None else weight
        self.band = _number("gw_ai_repeal_band") if band is None else band
        self.lock_points = _number("gw_ai_movement_lapse_lock_points")
        self.take_on = _debt("gw_ai_can_take_on_renewable_investment")
        self.keep = _debt("gw_ai_can_keep_renewable_investment")
        self.hold_rule, self.lock = hold, lock
        self.target0 = activism  # the movement's target with nothing in force
        self.debt = 0.0  # scaled_debt
        self.activism = activism
        self.movement = True
        self.held = set(held)
        self.cooldown = 0
        self.lapse_cooldown = 0
        self.log = []

    @staticmethod
    def pressure(a):
        return max(0.0, min(1.0, (a - PROTESTING) / (MILITANT - PROTESTING)))

    def hold(self, p):
        if not self.movement:
            return 0.0
        added = SWING * (len(self.held) if self.hold_rule == "all" else 1)
        points = self.weight * self.pressure(self.activism + added)
        if self.lock and self.lapse_cooldown > 0:
            points += self.lock_points
        if p == "renewable_investment" and not self.debt < self.keep:
            return 0.0
        return points

    def answerable(self, p):
        return self.can[p] and (p != "renewable_investment" or self.debt < self.take_on)

    def week(self, n):
        press = self.pressure(self.activism) if self.movement else 0.0
        options = {p: m for p, m in self.base.items() if p not in self.held and self.answerable(p)}
        nearest = max(options.values()) if options else None
        for p in sorted(self.base):
            if p in self.held:
                if -self.base[p] - self.band - self.hold(p) > 0:
                    self.held.discard(p)
                    self.lapse_cooldown = 52
                    self.log.append((n, "repeal", p))
                continue
            points = 0.0
            if press > 0 and self.cooldown <= 0 and self.answerable(p) and self.base[p] >= nearest:
                points = self.weight * press
            if self.can[p] and self.base[p] + points >= 0:
                self.held.add(p)
                self.cooldown = 52
                self.log.append((n, "adopt", p, points > 0))
        self.cooldown -= 1
        self.lapse_cooldown -= 1
        if self.movement:
            target = max(0.0, min(1.0, self.target0 - SWING * len(self.held)))
            step = max(-DRIFT, min(DRIFT, target - self.activism))
            self.activism += step

    def run(self, weeks, start=0):
        for n in range(start, start + weeks):
            self.week(n)
        return self

    def repeals(self):
        return [e for e in self.log if e[1] == "repeal"]


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

    def test_renewable_investment_lapses_once_the_treasury_cannot_keep_it(self):
        # Held by the movement alone (-20, below its band): it goes once the
        # debt passes half the ceiling, and the movement doesn't bring it back
        # while the debt stays above a quarter.
        base = {"renewable_investment": -20, "carbon_tax": -60}
        c = _Country(base, activism=0.9).run(52)
        self.assertEqual(c.held, {"renewable_investment"})
        c.debt = c.keep + 0.05
        c.run(52 * 3, start=52)
        self.assertEqual(c.held, set())
        self.assertEqual([e[1] for e in c.log if e[2] == "renewable_investment"], ["adopt", "repeal"])
        # Held by its own will (-10, inside the band), it stays, as on main.
        own = _Country({"renewable_investment": -10, "carbon_tax": -60}, activism=0.9).run(52)
        own.debt = own.keep + 0.05
        own.run(52 * 3, start=52)
        self.assertEqual(own.held, {"renewable_investment"})

    def test_a_debt_near_a_quarter_of_the_ceiling_doesnt_cycle_renewable_investment(self):
        # The debt swings 0.20 to 0.30 on a two-year cycle around the line where
        # the movement may take the policy on. Kept to half the ceiling, it stays.
        base = {"renewable_investment": -20, "carbon_tax": -60}
        for keep, cycles in ((None, False), (0.25, True)):
            with self.subTest(keep=keep):
                c = _Country(base, activism=0.9)
                if keep is not None:
                    c.keep = keep  # one threshold for both, as first built
                for n in range(52 * 12):
                    c.debt = 0.25 + 0.05 * math.sin(2 * math.pi * n / 104)
                    c.week(n)
                self.assertEqual(bool(c.repeals()), cycles, c.log)

    def test_a_movement_at_rest_holds_nothing_however_many_are_in_force(self):
        # Six of the seven held, a movement at 0 activism, every will 5 to 29
        # below its band (a treaty that forced them, ended): they lapse, one a
        # year while the movement exists. The hold as first built kept all six.
        six = {"climate_adaptation": -20, "reforestation": -20, "renewable_investment": -30,
               "public_transit": -35, "emission_standards": -40, "carbon_tax": -44, "fossil_fuel_divestment": -70}
        held = [p for p in six if p != "fossil_fuel_divestment"]
        c = _Country(six, activism=0.0, held=held)
        c.target0 = 0.0
        c.run(52 * 7)
        self.assertEqual(c.held, set())
        weeks = [e[0] for e in c.repeals()]
        self.assertEqual(len(weeks), 6)
        self.assertTrue(all(b - a >= 52 for a, b in zip(weeks, weeks[1:])), weeks)
        old = _Country(six, activism=0.0, held=held, hold="all")
        old.target0 = 0.0
        self.assertEqual(old.run(52 * 7).held, set(held))

    def test_four_falling_together_keep_what_the_movement_would_press_for(self):
        # The review's case A (model3.py): four held by their own will, whose
        # wills fall 17 to 34 below threshold at year 2, and a movement that
        # would press without them (0.9) but reads 0.1 with the four in force.
        # Without the lock all four go together, before the reading climbs, and
        # two come back as answers; with it, two go and two stay.
        held = {"climate_adaptation": 3, "reforestation": 2, "renewable_investment": 1, "public_transit": 0}
        after = {"climate_adaptation": -17, "reforestation": -18, "renewable_investment": -34, "public_transit": -20}
        far = {"emission_standards": -60, "carbon_tax": -70, "fossil_fuel_divestment": -85}
        for lock, readopted in ((True, False), (False, True)):
            with self.subTest(lock=lock):
                c = _Country({**held, **far}, activism=0.1, held=list(held), lock=lock)
                c.target0 = 0.9
                c.run(104)
                c.base.update(after)
                c.run(52 * 10, start=104)
                gone = {e[2] for e in c.repeals()}
                back = {e[2] for e in c.log if e[1] == "adopt" and e[2] in gone}
                self.assertEqual(bool(back), readopted, c.log)
                if lock:
                    self.assertEqual((len(gone), len(c.held & set(held))), (2, 2), c.log)

    def test_a_far_answer_lapses_once_nearer_ones_calm_the_movement(self):
        # The rule as written, not a cycle: a militant movement with only the
        # Carbon Tax in reach carries it from 30 points short. Once the cheaper
        # two come into reach and calm it, the movement wouldn't press for the
        # tax any more (its hold, 12, is short of the 15 it needs), so the tax
        # lapses and isn't taken up again. The hold as first built kept it.
        for hold, kept in (("one", False), ("all", True)):
            with self.subTest(hold=hold):
                c = _Country(self.BASE, activism=1.0, can={p: p == "carbon_tax" for p in self.BASE}, hold=hold)
                c.run(52)
                c.can = {p: True for p in self.BASE}
                c.run(52 * 9, start=52)
                self.assertEqual("carbon_tax" in c.held, kept, c.log)
                self.assertEqual([e[2] for e in c.log if e[1] == "adopt"],
                                 ["carbon_tax", "climate_adaptation", "reforestation"])

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
