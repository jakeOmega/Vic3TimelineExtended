"""The regional formables read external pressure from a global variable the
world's monthly pulse sets (te_formable_effects.txt), not from a walk of every
country per call (performance, 2026-11-12). These tests hold the pieces
together: each formation's trigger reads the variable its region's call sets,
the call names the same region the formation's candidacy uses, the pulse runs
it, and the tooltip has its text.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
FORMATIONS = os.path.join(REPO, "common", "country_formation", "te_formable_countries.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "formable_gating_triggers.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_formable_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_formable_on_actions.txt")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 1
    for i in range(m.end(), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _loc_keys():
    keys = set()
    for path in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")):
        with open(path, encoding="utf-8-sig") as f:
            keys.update(re.findall(r"(?m)^ (\w+):\d* ", f.read()))
    return keys


class ExternalPressureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = _read(TRIGGERS)
        cls.formations = _read(FORMATIONS)
        cls.calls = dict(re.findall(r"te_formable_set_external_pressure = \{ KEY = (\w+) REGION = (\w+) \}",
                                    _flat(_block(_read(EFFECTS), "te_formable_refresh_external_pressure"))))

    def test_six_regions(self):
        self.assertEqual(set(self.calls), {"eu", "afu", "una", "inm", "eaf", "dar"})

    def test_each_trigger_reads_its_regions_variable_with_a_tooltip(self):
        keys = _loc_keys()
        for key in self.calls:
            with self.subTest(key=key):
                body = _flat(_block(self.triggers, f"{key}_formation_external_pressure"))
                self.assertEqual(body, f"custom_tooltip = {{ text = {key}_formation_external_pressure_tt "
                                       f"has_global_variable = te_formable_pressure_{key} }}")
                self.assertIn(f"{key}_formation_external_pressure_tt", keys)

    def test_each_region_is_the_one_its_formation_is_led_from(self):
        for tag, body in re.findall(r"(?m)^([A-Z]{3}) = \{(.*?)^\}", self.formations, re.S):
            m = re.search(r"\b(\w+)_formation_external_pressure = yes", body)
            if m is None:
                continue
            key = m.group(1)
            with self.subTest(tag=tag, key=key):
                candidate = _flat(_block(body.replace("\n\t", "\n"), "can_be_formation_candidate"))
                self.assertIn(f"is_major_{self.calls[key]}_power = yes", candidate)
                self.assertIn(f"{key}_formation_external_pressure = yes", _flat(_block(body.replace("\n\t", "\n"), "ai_will_do")))

    def test_the_regions_triggers_exist(self):
        for region in self.calls.values():
            with self.subTest(region=region):
                _block(self.triggers, f"is_major_{region}_power")

    def test_the_worlds_monthly_pulse_runs_it(self):
        on_actions = _flat(_read(ON_ACTIONS))
        self.assertIn("on_monthly_pulse = { on_actions = { te_formable_pressure_on_action } }", on_actions)
        self.assertIn("te_formable_pressure_on_action = { effect = { te_formable_refresh_external_pressure = yes } }",
                      on_actions)


if __name__ == "__main__":
    unittest.main()
