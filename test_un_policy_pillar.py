"""The UN authority target's Policy pillar and the credibility ledger's slower fade.

Policy is read from the world, not booked: every country's
country_un_authority_target_add modifier, times its weight (un_actor_weight),
summed and held to -25..+25. Only a member in good standing (in the UN and not
undermining it) counts in full; anyone else's total counts only when negative.
Credibility keeps a ten-year half-life and a -25..+25 range; delivery and order
keep the four-year half-life. These checks pin the wiring: the modifier is
registered and localized, the pillar is in the target, snapshotted and shown, the
good-standing rule is applied and explained, and no ledger path can write to it.
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
MEMBERSHIP_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_membership_triggers.txt")
MODIFIER = "country_un_authority_target_add"
# The modifier given a value (a grant), not read (`modifier:...`) or defined (`... = {`).
GRANT = re.compile(rf"(?<![:\w]){MODIFIER}\s*=(?!\s*\{{)")

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
        """This change only adds the hook; a grant is a balance decision of its own.

        A grant is the modifier assigned a value in any modifier block, anywhere a
        modifier can live: laws, institutions, technologies, static modifiers,
        production methods, principles, treaty articles, character traits. Reads
        (`modifier:...`) and the type definition (`... = {`) are not grants."""
        grants = []
        paths = glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
        paths += glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True)
        for path in paths:
            if GRANT.search(_strip_comments(_read(path))):
                grants.append(os.path.relpath(path, REPO))
        self.assertEqual(grants, [], "a grant landed; update this test and the docs")

    def test_the_grant_pattern_sees_a_grant(self):
        """The scan above would catch `country_un_authority_target_add = 1.5` and
        ignore the reads and the definition."""
        self.assertRegex(f"modifier = {{\n\t{MODIFIER} = 1.5\n}}", GRANT)
        self.assertRegex(f"\t\t{MODIFIER} = -0.25", GRANT)
        self.assertNotRegex(f"value = modifier:{MODIFIER}", GRANT)
        self.assertNotRegex(f"modifier:{MODIFIER} > 0", GRANT)
        self.assertNotRegex(f"{MODIFIER} = {{\n\tcolor = good", GRANT)


class PillarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)

    def test_the_pillar_sums_each_countrys_contribution(self):
        body = _block(self.values, "un_pillar_policy_value")
        self.assertIn("every_country", body)
        self.assertIn("add = un_policy_contribution", body)
        self.assertNotIn(f"modifier:{MODIFIER}", body,
                         "the pillar must read the gated contribution, not the raw modifier")

    def test_a_contribution_is_the_modifier_times_actor_weight(self):
        body = _block(self.values, "un_policy_contribution")
        self.assertIn(f"value = modifier:{MODIFIER}", body)
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


class GoodStandingTest(unittest.TestCase):
    """Only a member in good standing adds to the pillar; anyone else can only
    take from it. Good conduct from outside the UN, or from a member working
    against it, does not strengthen it; bad conduct from anyone weakens it."""

    @classmethod
    def setUpClass(cls):
        cls.values = _read(VALUES)
        cls.trigger = _block(_read(MEMBERSHIP_TRIGGERS), "un_policy_counts_in_full")

    def test_good_standing_is_a_member_not_undermining(self):
        body = re.sub(r"\s+", " ", self.trigger)
        self.assertIn("je:je_united_nations ?= {", body)
        self.assertIn("has_modifier = un_member_modifier", body)
        self.assertIn("NOT = { has_modifier = un_undermine_order_cost }", body)
        self.assertNotIn("un_champion_order_cost", body,
                         "championing is rewarded by commitment; it must not change policy")

    def test_anyone_else_is_held_at_zero_or_below(self):
        body = re.sub(r"\s+", " ", _block(self.values, "un_policy_contribution"))
        self.assertIn("if = { limit = { NOT = { un_policy_counts_in_full = yes } } max = 0 }", body)
        self.assertNotIn("min = 0", body, "a member in good standing must be able to count against")

    def test_the_clamp_comes_before_the_weight(self):
        """Weight is never negative, so the order does not change the sign, but the
        clamp is on the country's own total, as the tooltip states it."""
        body = _block(self.values, "un_policy_contribution")
        self.assertLess(body.index("max = 0"), body.index("multiply = un_actor_weight"))

    def test_the_rule_as_the_script_states_it(self):
        """A model of un_policy_contribution, from the rulings in §0.10."""
        def contribution(modifier, member, undermining, weight):
            in_full = member and not undermining
            value = modifier if in_full else min(modifier, 0)
            return value * weight

        self.assertEqual(contribution(1.5, True, False, 2), 3)        # member: for
        self.assertEqual(contribution(-2, True, False, 1), -2)        # member: against
        self.assertEqual(contribution(1.5, False, False, 2), 0)       # outsider: good adds nothing
        self.assertEqual(contribution(-2, False, False, 1), -2)       # outsider: bad counts
        self.assertEqual(contribution(1.5, True, True, 2), 0)         # underminer: good adds nothing
        self.assertEqual(contribution(-0.5, True, True, 2), -1)       # underminer: bad counts
        self.assertEqual(contribution(1.5 - 2, False, False, 1), -0.5)  # outsider: offsets, no more

    def test_the_viewer_line_uses_the_same_rule(self):
        display = _read(DISPLAY)
        self.assertIn("value = un_policy_contribution",
                      _block(display, "un_disp_policy_own_contribution"))
        held = re.sub(r"\s+", " ", _block(display, "un_disp_policy_own_held"))
        self.assertIn("NOT = { un_policy_counts_in_full = yes }", held)
        self.assertIn(f"modifier:{MODIFIER} > 0", held)


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
                    "je_un_auth_tbl_policy_detail", "je_un_auth_tbl_policy_value",
                    "je_un_auth_policy_own", "je_un_auth_policy_own_held"):
            self.assertIn(key, self.loc, key)

    def test_the_tooltip_shows_our_own_contribution(self):
        self.assertIn("$je_un_auth_policy_own$", self.loc["je_un_auth_bar_policy_tt"])
        own = self.loc["je_un_auth_policy_own"]
        for v in ("un_disp_policy_own_modifier", "un_actor_weight", "un_disp_policy_own_contribution",
                  "un_disp_policy_own_held"):
            self.assertIn(f"ScriptValue('{v}')", own)
        self.assertIn("'je_un_auth_policy_own_held'", own)

    def test_the_good_standing_rule_is_explained_wherever_policy_is(self):
        """The pillar's tooltip, the help text and the modifier's own description
        each say who can add and who can only take away."""
        self.assertIn("not undermining", self.loc["je_un_auth_tbl_policy_tt"])
        self.assertIn("only take away", self.loc["je_un_auth_tbl_policy_tt"])
        self.assertIn("not undermining", self.loc["je_un_auth_help_3"])
        self.assertIn("not undermining", self.loc[f"{MODIFIER}_desc"])
        self.assertIn("only a negative total counts", self.loc[f"{MODIFIER}_desc"])

    def test_the_tooltips_state_the_new_ranges_and_fade(self):
        self.assertIn("(−25 to +25)", self.loc["je_un_auth_tbl_policy_tt"])
        credibility = self.loc["je_un_auth_tbl_credibility_tt"]
        self.assertIn("(−25 to +25)", credibility)
        self.assertIn("every ten years", credibility)
        self.assertIn("eight pillars", self.loc["je_un_auth_help_1"])


if __name__ == "__main__":
    unittest.main()
