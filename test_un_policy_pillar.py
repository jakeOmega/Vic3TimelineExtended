"""The UN authority target's Policy pillar and the credibility ledger's slower fade.

Policy is read from the world, not booked: every country's
country_un_authority_target_add modifier, times its weight (un_actor_weight),
summed and held to -25..+25. Credibility keeps a ten-year half-life and a
-25..+25 range; delivery and order keep the four-year half-life. These checks pin
the wiring: the modifier is registered and localized, the pillar is in the
target, snapshotted and shown, and no ledger path can write to it.
"""
import glob
import math
import os
import re
import unittest

from test_un_overview_data import _block, _read, _strip_comments

REPO = os.path.dirname(os.path.abspath(__file__))
VALUES = os.path.join(REPO, "common", "script_values", "un_authority_values.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "un_overview_display_values.txt")
AUTH_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_authority_effects.txt")
LADDER_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_ladder_effects.txt")
MODIFIER_TYPES = os.path.join(REPO, "common", "modifier_type_definitions", "un_membership_modifier_types.txt")
WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "un_authority_widget.gui")
MODIFIER = "country_un_authority_target_add"

_LOC_LINE = re.compile(r'^ ([\w.]+):\d* "(.*)"')


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")):
        for line in _read(path).splitlines():
            m = _LOC_LINE.match(line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _number(text, name):
    """The literal in `name = { value = N }`."""
    m = re.search(rf"(?m)^{name} = \{{ value = (-?[\d.]+) \}}", _strip_comments(text))
    assert m, f"{name} is not a one-line script value"
    return float(m.group(1))


class ModifierTest(unittest.TestCase):
    def test_the_modifier_is_registered_and_signed(self):
        body = _block(_read(MODIFIER_TYPES), MODIFIER)
        self.assertIsNotNone(body, f"{MODIFIER} is not defined")
        self.assertIn("script_only = yes", body)
        self.assertIn("percent = no", body)
        self.assertNotIn("boolean", body, "the value must be able to be negative and fractional")

    def test_the_modifier_is_localized(self):
        loc = _loc()
        self.assertIn(MODIFIER, loc)
        self.assertIn(f"{MODIFIER}_desc", loc)

    def test_nothing_grants_it_yet(self):
        """This change only adds the hook; a grant is a balance decision of its own."""
        grants = []
        for folder in ("laws", "static_modifiers", "technology", "institutions", "buildings",
                       "production_methods", "decrees", "power_bloc_principles"):
            for path in glob.glob(os.path.join(REPO, "common", folder, "**", "*.txt"), recursive=True):
                if MODIFIER in _read(path):
                    grants.append(os.path.relpath(path, REPO))
        self.assertEqual(grants, [], "a grant landed; update this test and the docs")


class PillarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)

    def test_the_pillar_sums_the_modifier_weighted_by_actor_weight(self):
        body = _block(self.values, "un_pillar_policy_value")
        self.assertIn("every_country", body)
        self.assertIn(f"modifier:{MODIFIER}", body)
        self.assertIn("multiply = un_actor_weight", body)

    def test_the_pillar_is_held_to_plus_minus_25(self):
        body = _block(self.values, "un_pillar_policy_value")
        self.assertIn("min = un_policy_floor", body)
        self.assertIn("max = un_policy_cap", body)
        self.assertEqual(_number(self.values, "un_policy_cap"), 25)
        self.assertEqual(_number(self.values, "un_policy_floor"), -25)

    def test_the_target_adds_the_snapshot(self):
        body = _block(self.values, "un_authority_target_value")
        self.assertIn("add = global_var:un_pillar_policy", body)

    def test_the_monthly_update_snapshots_it_before_the_target(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        snap = body.index("name = un_pillar_policy value = un_pillar_policy_value")
        target = body.index("name = un_authority_target value")
        self.assertLess(snap, target, "the target would read last month's policy")

    def test_a_dissolved_un_forgets_it(self):
        self.assertIn("NAME = un_pillar_policy }", _read(LADDER_EFFECTS))

    def test_no_ledger_path_writes_it(self):
        """Policy is not a ledger: a PILLAR = policy entry would book into a stock
        nothing reads."""
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
            self.assertNotRegex(_strip_comments(_read(path)), r"PILLAR\s*=\s*policy", path)
        for path in glob.glob(os.path.join(REPO, "events", "*.txt")):
            self.assertNotRegex(_strip_comments(_read(path)), r"PILLAR\s*=\s*policy", path)

    def test_the_bar_is_scaled_by_the_pillars_own_cap(self):
        display = _read(DISPLAY)
        for side in ("pos", "neg"):
            self.assertIn("divide = un_policy_cap", _block(display, f"un_disp_pillar_policy_{side}"))


class CredibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)

    def test_range_is_plus_minus_25_and_the_bar_follows_it(self):
        self.assertEqual(_number(self.values, "un_credibility_cap"), 25)
        self.assertEqual(_number(self.values, "un_credibility_floor"), -25)
        body = _block(self.values, "un_pillar_credibility_value")
        self.assertIn("min = un_credibility_floor", body)
        self.assertIn("max = un_credibility_cap", body)
        display = _read(DISPLAY)
        for side in ("pos", "neg"):
            self.assertIn("divide = un_credibility_cap",
                          _block(display, f"un_disp_pillar_credibility_{side}"))

    def test_credibility_halves_every_ten_years_the_others_every_four(self):
        slow = _number(self.values, "un_credibility_decay_factor")
        fast = _number(self.values, "un_ledger_decay_factor")
        self.assertAlmostEqual(slow ** 120, 0.5, places=2)
        self.assertAlmostEqual(fast ** 48, 0.5, places=2)
        self.assertGreater(slow, fast)

    def test_each_ledger_fades_by_its_own_factor(self):
        body = _strip_comments(_block(_read(AUTH_EFFECTS), "un_authority_monthly_update"))
        for ledger, factor in (("credibility", "un_credibility_decay_factor"),
                               ("delivery", "un_ledger_decay_factor"),
                               ("order", "un_ledger_decay_factor")):
            self.assertRegex(
                body,
                rf"name = un_ledger_{ledger} multiply = {factor} \}}",
                f"the {ledger} ledger is not decayed by {factor}")

    def test_the_slower_fade_does_not_outgrow_the_cap_in_a_quiet_world(self):
        """§0.1 ruling 5: a quiet world fed ~0.1 a month settled at about +7 on a
        four-year half-life. The same feed on ten years must still sit inside the
        cap, with room for the Assembly to have a good decade."""
        slow = _number(self.values, "un_credibility_decay_factor")
        settles = 0.1 / (1 - slow)
        self.assertLess(settles, 25 * 0.8)
        self.assertTrue(math.isfinite(settles))


class GuiAndLocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(WIDGET)
        cls.loc = _loc()

    def test_the_row_reads_the_policy_display_values(self):
        for v in ("un_disp_pillar_policy_neg", "un_disp_pillar_policy_pos", "un_disp_pillar_policy_trend"):
            self.assertIn(f"ScriptValue('{v}')", self.gui)
        self.assertIn('tooltip = "je_un_auth_bar_policy_tt"', self.gui)

    def test_every_key_the_row_names_exists(self):
        for key in ("je_un_auth_bar_policy_tt", "je_un_auth_tbl_policy_label", "je_un_auth_tbl_policy_tt",
                    "je_un_auth_tbl_policy_detail", "je_un_auth_tbl_policy_value"):
            self.assertIn(key, self.loc, key)

    def test_the_tooltips_state_the_new_ranges_and_fade(self):
        self.assertIn("(−25 to +25)", self.loc["je_un_auth_tbl_policy_tt"])
        credibility = self.loc["je_un_auth_tbl_credibility_tt"]
        self.assertIn("(−25 to +25)", credibility)
        self.assertIn("every ten years", credibility)
        self.assertIn("eight pillars", self.loc["je_un_auth_help_1"])


if __name__ == "__main__":
    unittest.main()
