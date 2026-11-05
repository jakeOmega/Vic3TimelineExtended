"""The hover on the reading in each banking overview cell.

The cell's own tooltip explains the reading; the word under the caption has one
of its own, saying what THAT reading does (the phase's modifiers in the
country's economy, the band's crash risk, the price band's modifier). Each
effect text is chosen by a customizable localization that must pick by the same
tests as the block that names the band, and the claims in the prose must hold
against the script they describe.
"""
import os
import re
import unittest

from test_banking_layout import (CUSTOM_LOC, DASH, REPO, _block_from, _loc, _read,
                                 _type_body)

PHASES = ["panic", "downturn", "stagnation", "expansion", "boom", "frenzy"]
# The word in each overview cell, and the tooltip it carries.
WORD_TIPS = {f"banking_dash_phase_{p}_value": "banking_dash_phase_word_tt"
             for p in PHASES + ["stable"]}
WORD_TIPS.update({
    "banking_dash_momentum_value": "banking_dash_momentum_word_tt",
    "banking_dash_bubble_value": "banking_dash_bubble_word_tt",
    "banking_dash_budget_used": "banking_dash_budget_used_tt",
    "banking_dash_budget_value": "banking_dash_budget_free_tt",
    "banking_dash_mon_stance_value": "banking_dash_mon_stance_word_tt",
    "banking_dash_mon_band_value": "banking_dash_mon_band_word_tt",
})
# (the effect custom, the custom that names the band it must follow)
FOLLOWS = [
    ("banking_dash_momentum_effect", "banking_dash_momentum_band"),
    ("banking_dash_bubble_effect", "banking_dash_bubble_band"),
    ("banking_dash_stance_pool_effect", "te_mon_stance_band_name"),
    ("banking_dash_price_band_effects", "te_mon_inflation_band_cost"),
]


def _custom(name):
    """A customizable localization's branches: [(trigger text, key)]."""
    text = _read(CUSTOM_LOC)
    m = re.search(rf"(?m)^{name} = \{{", text)
    assert m, f"no customizable localization {name}"
    body = _block_from(text, m.end() - 1)
    out = []
    for t in re.finditer(r"\btext = \{", body):
        block = _block_from(body, t.end() - 1)
        trig = re.search(r"trigger = (\{.*?\})\s*localization_key", block, re.S)
        key = re.search(r"localization_key = (\w+)", block).group(1)
        out.append((" ".join(trig.group(1).split()) if trig else "", key))
    return out


def _static_modifiers():
    names = set()
    folder = os.path.join(REPO, "common", "static_modifiers")
    for f in os.listdir(folder):
        names.update(re.findall(r"(?m)^(\w+) = \{", _read(os.path.join(folder, f))))
    return names


def _words():
    body = _type_body(_read(DASH), "te_banking_overview_panel")
    out = {}
    for m in re.finditer(r"te_banking_ov_word = \{", body):
        block = _block_from(body, m.end() - 1)
        text = re.search(r'\btext = "(\w+)"', block).group(1)
        tip = re.search(r'\btooltip = "(\w+)"', block)
        out[text] = (tip.group(1) if tip else None, block)
    return out


class WordTipTest(unittest.TestCase):
    def test_each_reading_has_its_own_hover(self):
        words, loc = _words(), _loc()
        for text, tip in WORD_TIPS.items():
            with self.subTest(word=text):
                self.assertIn(text, words)
                self.assertEqual(words[text][0], tip)
                self.assertIn(tip, loc)
                # not underlined, as vanilla's readings aren't (style guide rule 3)
                self.assertNotIn("#tooltippable", words[text][1])

    def test_the_not_started_cell_keeps_the_cell_tooltip_only(self):
        words = _words()
        for text in ("banking_dash_not_started_value", "banking_dash_not_started_conditions"):
            self.assertIsNone(words[text][0], text)

    def test_every_hover_key_is_in_loc(self):
        loc = _loc()
        keys = set()
        for name, _ in FOLLOWS + [("banking_dash_phase_effects", None)]:
            keys.update(k for _, k in _custom(name))
        for k in keys:
            with self.subTest(key=k):
                self.assertIn(k, loc)


class FollowsBandTest(unittest.TestCase):
    def test_each_effect_picks_by_its_bands_tests(self):
        for effect, band in FOLLOWS:
            with self.subTest(effect=effect):
                a, b = _custom(effect), _custom(band)
                self.assertEqual([t for t, _ in a], [t for t, _ in b])
                self.assertEqual(len({k for _, k in a}), len(a), "one text per branch")


class PhaseTest(unittest.TestCase):
    ECONOMY = {"": "", "_cmd": "has_law = law_type:law_command_economy",
               "_coop": "has_law = law_type:law_cooperative_ownership"}

    def _applied(self):
        """The modifier banking_cycle_apply_phase_modifiers adds, by economy
        and phase: command, cooperative, then the market's else-branch."""
        text = _read(os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt"))
        start = text.index("banking_cycle_apply_phase_modifiers = {")
        body = _block_from(text, start)
        body = body[body.index("# Phase modifier by economic law type"):]
        names = re.findall(r"name = (financial_cycle_phase_\w+)", body)
        self.assertEqual(len(names), 18)
        return {suffix: dict(zip(PHASES, names[i * 6:(i + 1) * 6]))
                for i, suffix in enumerate(("_cmd", "_coop", ""))}

    def test_each_economy_shows_the_modifier_it_gets(self):
        loc = _loc()
        branches = _custom("banking_dash_phase_effects")
        applied = self._applied()
        seen = set()
        for trig, key in branches:
            m = re.fullmatch(r"banking_dash_phase_fx_(\w+?)(_cmd|_coop)?", key)
            if not m:
                continue
            phase, suffix = m.group(1), m.group(2) or ""
            seen.add((phase, suffix))
            with self.subTest(key=key):
                self.assertIn(f"banking_cycle_is_{phase} = yes", trig)
                # the economy's own law is tested, and no other economy's
                for other, law in self.ECONOMY.items():
                    if law:
                        self.assertEqual(law in trig, other == suffix and phase != "stable", other)
                if phase == "stable":
                    self.assertNotIn("GetStaticModifier", loc[key])   # no modifier in any economy
                    continue
                mod = applied[suffix][phase]
                self.assertEqual(set(re.findall(r"GetStaticModifier\('(\w+)'\)", loc[key])), {mod})
                self.assertIn(".GetName", loc[key])
                self.assertIn(".GetDesc", loc[key])
        self.assertEqual(seen, {(p, s) for p in PHASES for s in self.ECONOMY} | {("stable", "")})

    def test_a_specific_economy_is_tested_before_the_market(self):
        order = [k for _, k in _custom("banking_dash_phase_effects")]
        for phase in PHASES:
            market = order.index(f"banking_dash_phase_fx_{phase}")
            for suffix in ("_cmd", "_coop"):
                self.assertLess(order.index(f"banking_dash_phase_fx_{phase}{suffix}"), market)

    def test_every_named_modifier_exists(self):
        known = _static_modifiers()
        loc = _loc()
        for key, value in loc.items():
            if key.startswith(("banking_dash_phase_fx_", "banking_dash_stance_pool_",
                               "banking_dash_price_band_fx_")):
                for mod in re.findall(r"GetStaticModifier\('(\w+)'\)", value):
                    with self.subTest(key=key):
                        self.assertIn(mod, known)

    def test_the_phase_modifiers_read_are_the_ones_each_band_applies(self):
        loc = _loc()
        stance = _custom("banking_dash_stance_pool_effect")
        for n, (_, key) in enumerate(stance[1:], 1):
            if n == 3:
                self.assertNotIn("GetStaticModifier", loc[key])    # banking_stance_band_3 is empty
            else:
                self.assertIn(f"banking_stance_band_{n}", loc[key])
        price = dict((k, loc[k]) for _, k in _custom("banking_dash_price_band_effects")
                     if k.startswith("banking_dash_price_band_fx_"))
        self.assertEqual(
            {k.removeprefix("banking_dash_price_band_fx_"):
             (re.search(r"GetStaticModifier\('(\w+)'\)", v) or [None, None])[1] for k, v in price.items()},
            {"dollarised": "te_mon_dollarised_modifier", "command": None, "deflation": "te_inflation_band_deflation",
             "comfort": None, "elevated": "te_inflation_band_elevated", "high": "te_inflation_band_high",
             "very_high": "te_inflation_band_very_high", "hyper": "te_inflation_band_hyper"})


class CrashClaimsTest(unittest.TestCase):
    """The prose names bubble bands where the crash roll starts to read, so the
    roll's thresholds must sit where the prose puts them."""

    def _roll(self):
        text = _read(os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt"))
        body = _block_from(text, text.index("banking_cycle_check_and_execute_crash = {"))
        found = re.findall(r"limit = \{ var:finance_cycle_value >= (\d+) \} # (\w+)\s*subtract = (\d+)", body)
        by_phase = {name: int(sub) for _, name, sub in found}
        by_phase["low"] = int(re.search(r"else = \{[^{}]*?subtract = (\d+)", body, re.S).group(1))
        return by_phase

    def _edges(self):
        edges = [int(n) for n in re.findall(r"var:bubble_pressure < (\d+)",
                                            "\n".join(t for t, _ in _custom("banking_dash_bubble_band")))]
        self.assertEqual(len(edges), 4)
        return dict(zip(("building", "elevated", "high", "severe"), edges))

    def test_thresholds_match_the_band_words(self):
        k, e = self._roll(), self._edges()
        self.assertEqual(k["frenzy"], e["building"])                     # "from a Building bubble"
        self.assertTrue(e["building"] <= k["boom"] <= e["elevated"])     # "from an Elevated bubble"
        self.assertEqual(k["expansion"], e["high"])                      # "a High bubble or worse"
        self.assertEqual(k["stable"], e["severe"])                       # "only a Severe bubble"
        self.assertGreaterEqual(k["low"], 100 - 10)                      # next to nothing

    def test_prose_names_those_bands(self):
        loc = _loc()
        for phase, band in (("frenzy", "Building"), ("boom", "Elevated"),
                            ("expansion", "High"), ("stable", "Severe")):
            self.assertIn(band, loc[f"banking_dash_phase_crash_{phase}"])
        # the phase, in the order of the roll: the higher the phase, the lower
        # the bubble at which the roll starts
        k = self._roll()
        self.assertTrue(k["frenzy"] < k["boom"] < k["expansion"] < k["stable"] < k["low"])

    def test_the_momentum_warning_is_a_boom_with_surging_momentum(self):
        triggers = _read(os.path.join(REPO, "common", "scripted_triggers", "market_triggers.txt"))
        risk = _block_from(triggers, triggers.index("banking_cycle_bubble_risk_high = {"))
        self.assertIn("var:finance_cycle_value >= 75 var:finance_cycle_momentum >= 3", " ".join(risk.split()))
        self.assertIn("banking_cycle_is_boom = { var:finance_cycle_value >= 75", triggers)
        surging = [t for t, k in _custom("banking_dash_momentum_band") if k.endswith("_surging")][0]
        self.assertIn(">= 3", surging)
        loc = _loc()
        for band in ("overheating", "surging"):
            self.assertIn("Boom or Frenzy", loc[f"banking_dash_momentum_fx_{band}"])


class BudgetTest(unittest.TestCase):
    def test_the_hover_reads_values_that_exist(self):
        values = _read(os.path.join(REPO, "common", "script_values", "extra_script_values.txt"))
        loc = _loc()
        for key in ("banking_dash_budget_used_tt", "banking_dash_budget_free_tt"):
            for name in re.findall(r"ScriptValue\('(\w+)'\)", loc[key]):
                with self.subTest(key=key, value=name):
                    self.assertRegex(values, rf"(?m)^{name} = \{{")


if __name__ == "__main__":
    unittest.main()
