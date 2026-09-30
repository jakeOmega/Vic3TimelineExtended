"""The Standard approach and what each approach costs (owner's play-test, round 2).

"Since the approaches increase funding cost, we should make that clear and maybe
add a 'basic' approach that has no modifiers that you can switch to." Standard is
the approach with neither sr_safe_<m> nor sr_ambitious_<m>: every milestone starts
on it, it moves at the programme's pace and rolls against the base risk, with no
modifier and no cost, and the player can switch back to it (scripted GUI op 4).
The drift state it replaced (a flat 0.5 a month, no roll) is gone. Safe and
Ambitious print their weekly innovation cost in their tooltips and beside the
approach in the overview.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "space_race_sguis.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "space_race_modifiers.txt")
JE = os.path.join(REPO, "common", "journal_entries", "je_space_race.txt")
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
              "interstellar_probe", "solar_colonization")
# The cost factors sr_<m>_cost multiplied by before they became named values.
FACTORS = {"suborbital": "1", "orbital": "1.5", "moon_landing": "2", "probe": "2", "moon_base": "5",
           "mars_landing": "6", "interstellar_probe": "12", "solar_colonization": "8"}


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


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path, comments=True), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


class NoDriftTest(unittest.TestCase):
    def test_the_drift_state_is_gone(self):
        for sub in ("common", "events"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
                self.assertNotIn("sr_progress_drift", _read(path), path)

    def test_every_running_milestone_moves_and_rolls(self):
        pulse = _block(_read(EFFECTS), "sr_monthly_progress_update_effect")
        self.assertNotIn("has_variable = sr_safe_$MILESTONE$", pulse)
        self.assertRegex(pulse, r"limit = \{ sr_ai_should_participate = yes \}\s*"
                                r"change_variable = \{ name = sr_progress_\$MILESTONE\$ add = sr_progress \}")
        self.assertIn("chance = sr_risk_pct_$MILESTONE$", pulse)
        solar = _block(_read(JE), "je_space_race_solar_colonization")
        self.assertRegex(solar, r"limit = \{ sr_ai_should_participate = yes \}\s*"
                                r"change_variable = \{ name = sr_progress_solar_colonization add = sr_progress \}")

    def test_pace_and_risk_shown_follow_the_roll(self):
        values = _read(VALUES)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                self.assertEqual(_block(values, f"sr_pace_rate_{m}").split(),
                                 ["value", "=", "sr_progress", "min", "=", "0.5"])
                risk = _block(values, f"sr_risk_shown_{m}")
                self.assertNotIn("sr_safe_", risk)
                self.assertIn("NOT = { sr_has_failure_cooldown = yes }", risk)

    def test_standard_has_its_own_status_codes(self):
        body = _block(_read(EFFECTS), "sr_set_milestone_status_base")
        self.assertIn("set_variable = { name = sr_$MILESTONE$_last_status value = 5 }", body)
        self.assertIn("set_variable = { name = sr_$MILESTONE$_last_status value = 0 }", body)


class StandardControlTest(unittest.TestCase):
    def test_op_4_selects_standard_on_every_milestone(self):
        sguis = _read(SGUIS)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                body = _block(sguis, f"sr_milestone_{m}_sgui")
                self.assertRegex(body, rf"limit = \{{ scope:op = 3 \}}\s*sr_possible_fund_up = \{{ MILESTONE = {m} \}}")
                self.assertRegex(body, rf"trigger_else = \{{\s*sr_possible_standard = \{{ MILESTONE = {m} \}}")
                self.assertRegex(body, rf"limit = \{{ scope:op = 3 \}}\s*sr_effect_fund_up = \{{ MILESTONE = {m} \}}")
                self.assertRegex(body, rf"else = \{{\s*sr_effect_standard = \{{ MILESTONE = {m} \}}")

    def test_standard_clears_both_approaches(self):
        effect = _block(_read(EFFECTS), "sr_effect_standard")
        for v in ("sr_safe_$MILESTONE$", "sr_ambitious_$MILESTONE$"):
            self.assertIn(f"remove_variable = {v}", effect)
        for mod in ("sr_safe_approach", "sr_ambitious_approach"):
            self.assertIn(f"remove_modifier = {mod}", effect)
        self.assertIn("sr_recalculate_cost = yes", effect)
        possible = _block(_read(TRIGGERS), "sr_possible_standard")
        self.assertIn("has_variable = sr_safe_$MILESTONE$", possible)
        self.assertIn("has_variable = sr_ambitious_$MILESTONE$", possible)

    def test_the_panel_offers_standard(self):
        control = re.search(r"type te_sr_sec_control = \w+ \{", _read(GUI, comments=True))
        self.assertTrue(control)
        gui = _read(GUI, comments=True)[control.end():]
        gui = gui[:gui.index("type te_sr_sec_rivals")]
        standard = gui[gui.index('text = "je_space_race_widget_standard_label"'):]
        standard = standard[:standard.index("te_sr_action_button = {")]
        self.assertEqual(standard.count("MakeScopeValue( '(CFixedPoint)4' )"), 5)  # visible, enabled, onclick, 2× tooltip
        self.assertEqual(_loc("je_space_race_widget_standard_label"), "Standard")


class CostTest(unittest.TestCase):
    def test_cost_factors_are_the_old_multipliers(self):
        values = _read(VALUES)
        for m, factor in FACTORS.items():
            with self.subTest(milestone=m):
                self.assertEqual(_block(values, f"sr_cost_factor_{m}").split(), ["value", "=", factor])
                self.assertIn(f"multiply = sr_cost_factor_{m}", _block(values, f"sr_{m}_cost"))

    def test_one_cost_level_is_the_modifier_s_innovation(self):
        modifier = _block(_read(MODIFIERS), "sr_space_program_cost")
        drain = re.search(r"country_weekly_innovation_add = -(\d+)", modifier).group(1)
        level = _block(_read(VALUES), "sr_innovation_per_cost_level").split()
        self.assertEqual(level, ["value", "=", drain])

    def test_display_costs(self):
        display = _read(DISPLAY)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                self.assertEqual(_block(display, f"sr_disp_cost_safe_{m}").split(),
                                 ["value", "=", "sr_innovation_per_cost_level", "multiply", "=", f"sr_cost_factor_{m}"])
                self.assertEqual(_block(display, f"sr_disp_cost_ambitious_{m}").split(),
                                 ["value", "=", f"sr_disp_cost_safe_{m}", "multiply", "=", "2"])

    def test_each_approach_prints_its_cost(self):
        effects = _read(EFFECTS)
        for kind in ("safe", "ambitious"):
            body = _block(effects, f"sr_effect_{kind}")
            # outside the wrapper, so it prints
            self.assertTrue(body.rstrip().endswith(f"custom_tooltip = sr_approach_cost_{kind}_$MILESTONE$"), kind)
            for m in MILESTONES:
                self.assertIn(f"ScriptValue('sr_disp_cost_{kind}_{m}')", _loc(f"sr_approach_cost_{kind}_{m}"))
        self.assertTrue(_block(effects, "sr_effect_standard").rstrip().endswith("custom_tooltip = SR_APPROACH_COST_STANDARD"))

    def test_the_overview_shows_the_cost_beside_the_approach(self):
        gui = _read(GUI, comments=True)
        for m in MILESTONES:
            root = gui[gui.index(f'name = "widget_je_space_race_{m}_overview"'):]
            root = root[:root.index("\nflowcontainer = {")]
            for kind in ("safe", "ambitious"):
                with self.subTest(milestone=m, approach=kind):
                    self.assertRegex(root, rf'blockoverride "sr_label_{kind}" \{{\s*text = "je_space_race_widget_ov_{kind}_{m}"')
                    self.assertIn(f"ScriptValue('sr_disp_cost_{kind}_{m}')", _loc(f"je_space_race_widget_ov_{kind}_{m}"))


if __name__ == "__main__":
    unittest.main()
