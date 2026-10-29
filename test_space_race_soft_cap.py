"""Funding past the cap (lunar colonization design § 5.1; owner, call 12).

The funding cap, sr_max_funding_level, is soft. A milestone may be funded up to
six levels past it, and each level past it adds less pace than the one before:
the first 1/2 of a level, the second 1/3, up to the sixth 1/7. Every level still
costs in full and still adds the full +25% Space Program throughput, so the one
funding modifier split in two: sr_funding_progress (the pace) takes
sr_funding_<m>_effective, sr_funding_throughput takes the level itself. The AI
stays within the cap (owner, § 15.6).

The script values are parsed and evaluated here, in the engine's fixed point,
for every milestone, cap and level the ladder covers.
"""
import glob
import math
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "space_race_buttons.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "space_race_on_actions.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "space_race_sguis.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "space_race_modifiers.txt")
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
NATION_TAB = os.path.join(REPO, "scripts", "generators", "gen_nation_tab.py")
LOC_DIR = os.path.join(REPO, "localization", "english")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
              "interstellar_probe", "solar_colonization")
STEPS = 6
# The design's table: effective levels past the cap after 1..6 levels past it.
TABLE = (0.50, 0.83, 1.08, 1.28, 1.45, 1.59)
CAP_MODIFIER = "modifier:country_space_race_max_funding_add"


def _read(path, comments=False):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return text if comments else re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    assert m, f"{name} not found"
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError("unclosed block")


def _parse(text):
    tokens = iter(t.strip() for t in ParadoxFileParser().tokenize(text))

    def body():
        out = []
        for key in tokens:
            if key == "}":
                return out
            op, value = next(tokens), next(tokens)
            out.append((key, op, body() if value == "{" else value))
        return out

    return body()


def _cut(x):
    """The engine's fixed point: five decimals, toward zero."""
    return math.trunc(round(x * 100000, 6)) / 100000


class Script:
    """A fail-closed evaluator for the script values this test reads.

    `owner = { }` is transparent: the multiplier runs in the entry's scope and
    reads the country through it, and here the country is the one context."""

    COMPARE = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b,
               ">=": lambda a, b: a >= b, "=": lambda a, b: a == b}

    def __init__(self):
        self.values = {}
        for path in (VALUES, DISPLAY):
            for key, _, body in _parse(_read(path)):
                self.values[key] = body
        self.triggers = {key: body for key, _, body in _parse(_read(TRIGGERS))}

    def number(self, token, ctx):
        if isinstance(token, list):
            return self.evaluate(token, ctx)
        try:
            return float(token)
        except ValueError:
            pass
        if token.startswith("var:"):
            name = token[4:]
            assert name in ctx["vars"], f"unguarded read of {token}"
            return float(ctx["vars"][name])
        if token == CAP_MODIFIER:
            return float(ctx["cap_modifier"])
        assert token in self.values, f"unknown value {token}"
        return self.evaluate(self.values[token], ctx)

    def check(self, body, ctx):
        for key, op, value in body:
            if key == "has_variable":
                ok = value in ctx["vars"]
            elif key in self.triggers and value in ("yes", "no"):
                ok = self.check(self.triggers[key], ctx) == (value == "yes")
            elif key == "modifier:country_sr_solar_colonization_program_bool":
                ok = ctx.get("solar_method", False) == (value == "yes")
            elif key == "NOT":
                ok = not self.check(value, ctx)
            elif key == "OR":
                ok = any(self.check([item], ctx) for item in value)
            else:
                ok = self.COMPARE[op](self.number(key, ctx), self.number(value, ctx))
            if not ok:
                return False
        return True

    def evaluate(self, body, ctx, result=0.0):
        done = False
        for key, op, value in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    done = False
                if done:
                    continue
                limit = next((v for k, _, v in value if k == "limit"), [])
                if key == "else" or self.check(limit, ctx):
                    done = True
                    result = self.evaluate([p for p in value if p[0] != "limit"], ctx, result)
                continue
            if key == "owner":
                result = self.evaluate(value, ctx, result)
                continue
            x = self.number(value, ctx)
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
                result = max(result, x)  # a lower bound
            elif key == "max":
                result = min(result, x)  # an upper bound
            else:
                raise AssertionError(f"unsupported step {key}")
            result = _cut(result)
        return result

    def value(self, name, ctx):
        return self.evaluate(self.values[name], ctx)


def _ctx(milestone, level, cap, billed=True):
    """A country whose cap is `cap` (3 plus the technology modifier), funding
    `milestone` at `level` (None: the variable is absent)."""
    ctx = {"vars": {}, "cap_modifier": cap - 3}
    if level is not None:
        ctx["vars"][f"sr_funding_{milestone}"] = level
    if billed:
        ctx["vars"][f"sr_active_{milestone}"] = 1
        if milestone == "solar_colonization":
            ctx["vars"]["sr_completed_moon_base"] = 1
            ctx["vars"]["sr_completed_mars_landing"] = 1
            ctx["solar_method"] = True
    return ctx


def _ladder(k):
    """Effective levels past the cap after k levels past it: 1/2 + ... + 1/(k+1)."""
    return sum(1 / (j + 1) for j in range(1, min(k, STEPS) + 1))


SCRIPT = Script()


class EffectiveLevelTest(unittest.TestCase):
    def test_up_to_the_cap_a_level_counts_in_full(self):
        for m in MILESTONES:
            for cap in (3, 10, 22):
                for level in range(cap + 1):
                    with self.subTest(milestone=m, cap=cap, level=level):
                        ctx = _ctx(m, level, cap)
                        self.assertEqual(SCRIPT.value(f"sr_funding_{m}_effective", ctx), level)
                        self.assertEqual(SCRIPT.value(f"sr_funding_{m}_past_cap", ctx), 0)

    def test_past_the_cap_each_level_adds_the_next_share(self):
        for m in MILESTONES:
            for cap in (3, 10, 22):
                for k in range(1, STEPS + 1):
                    with self.subTest(milestone=m, cap=cap, past=k):
                        ctx = _ctx(m, cap + k, cap)
                        self.assertEqual(SCRIPT.value(f"sr_funding_{m}_within_cap", ctx), cap)
                        self.assertEqual(SCRIPT.value(f"sr_funding_{m}_past_cap", ctx), k)
                        self.assertTrue(math.isclose(SCRIPT.value(f"sr_funding_{m}_past_cap_effective", ctx),
                                                     _ladder(k), abs_tol=1e-4))
                        self.assertTrue(math.isclose(SCRIPT.value(f"sr_funding_{m}_effective", ctx),
                                                     cap + _ladder(k), abs_tol=1e-4))

    def test_the_design_table(self):
        for k, shown in enumerate(TABLE, start=1):
            with self.subTest(past=k):
                got = SCRIPT.value("sr_funding_orbital_past_cap_effective", _ctx("orbital", 7 + k, 7))
                self.assertEqual(round(got, 2), shown)
                # this level's pace, 0.5 a level: +0.25, +0.17, +0.13, +0.10, +0.08, +0.07
                self.assertTrue(math.isclose(0.5 * (_ladder(k) - _ladder(k - 1)), 0.5 / (k + 1)))

    def test_a_cap_that_falls_leaves_the_level_standing(self):
        """A lost principle drops the cap below the level: nothing clamps the
        level, the excess counts past the cap, and a level past the sixth step
        adds nothing (the ladder's end, which only a falling cap reaches)."""
        ctx = _ctx("mars_landing", 14, 5)
        self.assertEqual(SCRIPT.value("sr_funding_mars_landing_past_cap", ctx), 9)
        self.assertTrue(math.isclose(SCRIPT.value("sr_funding_mars_landing_effective", ctx),
                                     5 + _ladder(STEPS), abs_tol=1e-4))
        self.assertEqual(SCRIPT.value("sr_funding_mars_landing_level", ctx), 14)

    def test_no_variable_reads_zero(self):
        for m in MILESTONES:
            ctx = _ctx(m, None, 7)
            for suffix in ("within_cap", "past_cap", "past_cap_effective", "effective", "level"):
                with self.subTest(milestone=m, value=suffix):
                    self.assertEqual(SCRIPT.value(f"sr_funding_{m}_{suffix}", ctx), 0)

    def test_the_entry_scoped_value_reads_the_country_through_owner(self):
        """The multiplier runs in the journal entry's scope: every read of the
        country (the variable, the cap's modifier) sits inside owner = { }."""
        values = _read(VALUES)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                body = _block(values, f"sr_funding_{m}_effective")
                self.assertEqual(re.sub(r"\s+", " ", body).strip(),
                                 f"value = 0 owner = {{ add = sr_funding_{m}_within_cap "
                                 f"add = sr_funding_{m}_past_cap_effective }}")


class ThroughputAndCostTest(unittest.TestCase):
    def test_the_modifier_is_split(self):
        mods = _read(MODIFIERS)
        progress = _block(mods, "sr_funding_progress")
        throughput = _block(mods, "sr_funding_throughput")
        self.assertIn("country_space_race_progress_add = 0.5", progress)
        self.assertNotIn("throughput", progress)
        self.assertIn("building_space_program_throughput_add = 0.25", throughput)
        self.assertNotIn("progress", throughput)

    def test_the_pace_takes_the_effective_level_and_the_throughput_the_level(self):
        body = _block(_read(EFFECTS), "sr_apply_milestone_cost_modifiers_base")
        pairs = dict(re.findall(r"name = (\w+)\s+multiplier = (\S+)", body))
        self.assertEqual(pairs["sr_funding_progress"], "sr_funding_$MILESTONE$_effective")
        self.assertEqual(pairs["sr_funding_throughput"], "sr_funding_$MILESTONE$_level")
        self.assertEqual(pairs["sr_space_program_cost"], "sr_$MILESTONE$_cost")

    def test_the_throughput_multiplier_is_the_raw_level_past_the_cap(self):
        for m in MILESTONES:
            for k in range(STEPS + 1):
                with self.subTest(milestone=m, past=k):
                    self.assertEqual(SCRIPT.value(f"sr_funding_{m}_level", _ctx(m, 7 + k, 7)), 7 + k)

    def test_every_level_costs_in_full(self):
        """The cost reads the variable itself, not the effective level."""
        values = _read(VALUES)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                body = _block(values, f"sr_{m}_cost")
                self.assertIn(f"add = var:sr_funding_{m}", body)
                self.assertNotIn("effective", body)

    def test_both_are_removed_before_they_are_added(self):
        recalc = _block(_read(EFFECTS), "sr_recalculate_cost")
        self.assertLess(recalc.index("sr_clear_milestone_cost_modifiers_base"),
                        recalc.index("sr_apply_milestone_cost_modifiers_base"))
        clear = _block(_read(EFFECTS), "sr_clear_milestone_cost_modifiers_base")
        for name in ("sr_space_program_cost", "sr_funding_progress", "sr_funding_throughput"):
            self.assertIn(f"if = {{ limit = {{ has_modifier = {name} }} remove_modifier = {name} }}",
                          re.sub(r" +", " ", clear))

    def test_an_old_save_picks_the_split_up(self):
        """Its entries carry sr_funding_progress and no sr_funding_throughput:
        the monthly repair recalculates them."""
        check = _block(_read(TRIGGERS), "sr_cost_modifiers_missing_base")
        self.assertRegex(check, r"sr_funding_\$MILESTONE\$_level > 0\s*NOT = \{ has_modifier = sr_funding_throughput \}")
        self.assertRegex(check, r"sr_funding_\$MILESTONE\$_effective > 0\s*NOT = \{ has_modifier = sr_funding_progress \}")

    def test_the_nation_tab_places_both(self):
        text = _read(NATION_TAB)
        for name in ("sr_funding_progress", "sr_funding_throughput"):
            self.assertRegex(text, rf'"{name}": "the running milestone\'s entry"')


class EverySiteTest(unittest.TestCase):
    """Every definition that handles sr_funding_progress handles
    sr_funding_throughput as well; a missed site leaks or never applies the
    throughput half, and the engine says nothing."""

    def test_every_site(self):
        files = [p for sub in ("common", "events", "gui")
                 for p in glob.glob(os.path.join(REPO, sub, "**", "*.*"), recursive=True)
                 if p.endswith((".txt", ".gui"))]
        seen = 0
        for path in files:
            if os.path.samefile(path, MODIFIERS):
                continue
            text = _read(path)
            if "sr_funding_progress" not in text:
                continue
            for m in re.finditer(r"(?m)^([\w.:]+)\s*=\s*\{", text):
                body = _block(text, m.group(1))
                if re.search(r"\bsr_funding_progress\b", body):
                    seen += 1
                    with self.subTest(file=os.path.relpath(path, REPO), definition=m.group(1)):
                        self.assertRegex(body, r"\bsr_funding_throughput\b")
        self.assertGreaterEqual(seen, 3)  # clear, apply, the repair trigger


class CeilingTest(unittest.TestCase):
    def test_the_ceiling_is_six_past_the_cap(self):
        for cap in (3, 7, 13, 26):
            with self.subTest(cap=cap):
                self.assertEqual(SCRIPT.value("sr_max_funding_level_soft", _ctx("probe", 1, cap)), cap + STEPS)
        self.assertEqual(SCRIPT.value("sr_funding_past_cap_steps", _ctx("probe", 1, 3)), STEPS)

    def test_fund_up_tests_the_named_soft_ceiling(self):
        body = _block(_read(TRIGGERS), "sr_possible_fund_up")
        self.assertRegex(body, r"var:sr_funding_\$MILESTONE\$ < sr_max_funding_level_soft\s*\}")

    def test_fund_up_stops_at_the_ceiling(self):
        trigger = _block(_read(TRIGGERS), "sr_possible_fund_up")
        inner = _parse(trigger.replace("$MILESTONE$", "probe"))[0][2]
        compare = [item for item in inner if item[0] != "text"]
        for level, ok in ((8, True), (12, True), (13, False), (14, False)):
            with self.subTest(level=level):
                self.assertEqual(SCRIPT.check(compare, _ctx("probe", level, 7)), ok)

    def test_the_player_reaches_it_and_the_ai_stops_at_the_cap(self):
        sguis = _read(SGUIS)
        buttons = _read(BUTTONS)
        within = _block(_read(TRIGGERS), "sr_possible_fund_up_within_cap")
        self.assertIn("sr_possible_fund_up = { MILESTONE = $MILESTONE$ }", within)
        self.assertRegex(within, r"var:sr_funding_\$MILESTONE\$ < sr_max_funding_level\s*\}")
        for m in MILESTONES:
            with self.subTest(milestone=m):
                self.assertRegex(sguis, rf"limit = \{{ scope:op = 3 \}}\s*sr_possible_fund_up = \{{ MILESTONE = {m} \}}")
                up = _block(buttons, f"sr_btn_fund_up_{m}")
                self.assertIn(f"possible = {{ sr_possible_fund_up_within_cap = {{ MILESTONE = {m} }} }}", up)
                # an AI left past the cap by a falling cap winds back within it
                down = _block(buttons, f"sr_btn_fund_down_{m}")
                self.assertRegex(down, rf"limit = \{{ sr_funding_{m}_past_cap > 0 \}}\s*add = 100")

    def test_nothing_clamps_the_level_to_the_cap(self):
        """The level moves by one a click and is created at 1; no write sets it
        from the cap, so a falling cap leaves it standing."""
        writes = 0
        for sub in ("common", "events"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
                text = _read(path)
                for m in re.finditer(r"(set|change)_variable = \{ name = sr_funding_(?:\$MILESTONE\$|\w+?) ([^}]*)\}", text):
                    writes += 1
                    with self.subTest(file=os.path.relpath(path, REPO), write=m.group(0)):
                        self.assertIn(m.group(2).strip(), ("value = 1", "add = 1", "subtract = 1"))
        self.assertGreaterEqual(writes, 10)  # each entry's creation, the debug seed, the two clicks


class CapCacheTest(unittest.TestCase):
    """The pace multiplier reads the cap, which technologies and Advanced
    Research V move with no button press. sr_recalculate_cost records the cap
    it computed with, and the monthly pulse recalculates when that is missing
    or differs from the live cap, as it does for participation."""

    def test_the_cap_is_recorded_with_the_costs(self):
        recalc = _block(_read(EFFECTS), "sr_recalculate_cost")
        self.assertIn("set_variable = { name = sr_cost_funding_cap value = sr_max_funding_level }", recalc)
        self.assertLess(recalc.index("sr_apply_milestone_cost_modifiers_base"), recalc.index("sr_cost_funding_cap"))

    def test_the_pulse_recalculates_when_the_cap_moves(self):
        pulse = re.sub(r"\s+", " ", _block(_read(ON_ACTIONS), "space_race_on_action"))
        self.assertIn("else_if = { limit = { NOT = { has_variable = sr_cost_funding_cap } } sr_recalculate_cost = yes }",
                      pulse)
        m = re.search(r"else_if = \{ limit = \{ (OR = \{ var:sr_cost_funding_cap < sr_max_funding_level "
                      r"var:sr_cost_funding_cap > sr_max_funding_level \}) \} sr_recalculate_cost = yes \}", pulse)
        self.assertIsNotNone(m, "no recalculation on a cap that moved")
        # in the participants' chain, after the participation check and before
        # the missing-modifier repair
        self.assertGreater(m.start(), pulse.index("NOT = { has_variable = sr_cost_participation }"))
        self.assertLess(m.start(), pulse.index("sr_cost_modifiers_missing = yes"))
        stale = _parse(m.group(1))
        for cached, cap, fires in ((7, 7, False), (7, 8, True), (7, 6, True), (22, 23, True)):
            with self.subTest(cached=cached, cap=cap):
                ctx = _ctx("probe", 9, cap)
                ctx["vars"]["sr_cost_funding_cap"] = cached
                self.assertEqual(SCRIPT.check(stale, ctx), fires)


class PanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = {}
        for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
            cls.loc.update(re.findall(r'^ ([\w.]+):\d* "(.*)"\s*$', _read(path, comments=True), re.M))

    def test_the_stepper_reads_level_cap_and_the_excess_past_the_cap(self):
        gui = _read(GUI)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                override = re.search(r'blockoverride "sr_funding_value" \{\s*text = "([^"]*)"\s*\}',
                                     gui[gui.index(f"je_space_race_widget_funding_{m}") - 400:])
                self.assertEqual(
                    override.group(1),
                    f"[SelectLocalization( GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope."
                    f"ScriptValue('sr_funding_{m}_past_cap'), '(CFixedPoint)0' ), "
                    f"'je_space_race_widget_funding_past_cap_{m}', 'je_space_race_widget_funding_{m}' )]")
                at = self.loc[f"je_space_race_widget_funding_{m}"]
                past = self.loc[f"je_space_race_widget_funding_past_cap_{m}"]
                self.assertTrue(past.startswith(at), "past the cap it reads as at the cap, then the excess")
                self.assertEqual(past[len(at):],
                                 f" (+[JournalEntry.GetCountry.MakeScope.ScriptValue('sr_funding_{m}_past_cap_effective')|1])")

    def test_the_plus_tooltip_gives_the_next_share(self):
        """sr_effect_fund_up's lines past the cap: with n levels already past
        it, the next is the (n+1)th and adds 1/(n+2) of a level."""
        body = _block(_read(EFFECTS), "sr_effect_fund_up")
        outer = [v for k, _, v in _parse(body) if k == "if"]
        self.assertEqual(len(outer), 1)
        limit = next(v for k, _, v in outer[0] if k == "limit")
        self.assertEqual(limit, [("sr_funding_$MILESTONE$_within_cap", ">=", "sr_max_funding_level"),
                                 ("sr_funding_$MILESTONE$_past_cap", "<", "sr_funding_past_cap_steps")])
        # Shown from the cap until the ladder is used up: never past the sixth
        # step, where no share exists (the button is greyed there, or a falling
        # cap left the level further past).
        shown = _parse(re.sub(r"\$MILESTONE\$", "probe", "limit = { " + " ".join(f"{a} {o} {b}" for a, o, b in limit) + " }"))[0][2]
        for level in range(16):
            with self.subTest(level=level):
                self.assertEqual(SCRIPT.check(shown, _ctx("probe", level, 7)), 7 <= level < 7 + STEPS)
        chain = [(k, v) for k, _, v in outer[0] if k in ("if", "else_if", "else")]
        picks = {}
        for past in range(STEPS):
            for key, branch in chain:
                lim = next((v for k, _, v in branch if k == "limit"), None)
                if lim is None or past >= float(lim[0][2]):
                    self.assertEqual(lim and lim[0][:2], lim and ("sr_funding_$MILESTONE$_past_cap", ">="))
                    picks[past] = next(v for k, _, v in branch if k == "custom_tooltip")
                    break
        self.assertEqual(picks, {past: f"SR_FUND_UP_PAST_CAP_{past + 2}" for past in range(STEPS)})
        for past in range(STEPS):
            with self.subTest(past=past):
                self.assertIn(f"+1/{past + 2} of a level of pace, at full cost", self.loc[picks[past]])

    def test_the_greyed_plus_says_why(self):
        self.assertIn("six levels past the cap", self.loc["SR_MAX_FUNDING_NOT_REACHED"])

    def test_the_pace_hover_lists_funding_within_and_past_the_cap(self):
        tip = self.loc["je_space_race_widget_pace_tt"]
        self.assertIn("ScriptValue('sr_disp_funding_within_cap')|0]#! levels within the cap", tip)
        self.assertIn("ScriptValue('sr_disp_funding_past_cap')|1]#! effective levels past it", tip)
        # the figures: the billed milestones only, as the modifiers are
        for m in MILESTONES:
            for level, cap in ((2, 7), (7, 7), (10, 7)):
                with self.subTest(milestone=m, level=level):
                    ctx = _ctx(m, level, cap)
                    self.assertEqual(SCRIPT.value("sr_disp_funding_within_cap", ctx), min(level, cap))
                    self.assertTrue(math.isclose(SCRIPT.value("sr_disp_funding_past_cap", ctx),
                                                 _ladder(max(level - cap, 0)), abs_tol=1e-4))
                    idle = _ctx(m, level, cap, billed=False)
                    self.assertEqual(SCRIPT.value("sr_disp_funding_within_cap", idle), 0)
                    self.assertEqual(SCRIPT.value("sr_disp_funding_past_cap", idle), 0)


if __name__ == "__main__":
    unittest.main()
