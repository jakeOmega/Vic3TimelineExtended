# -*- coding: utf-8 -*-
"""The reserve-currency cut where the credit floor swallows it (#1812, item 2; owner, 2026-11-16).

monetary_policy_design.md § 0.16, ruling L17. An anchor's reserve-currency cut
(te_mon_reserve_currency_cut: 0.1 points per 5% of world GDP pegged to its
money) is credit standing, and standing is floored (te_mon_standing_floor).
Before this change a country already on its floor gained nothing from it: eight
of the nine plain treaty anchors in the owner's three saves. Now the part the
floor swallows is paid as a cut in risk premium (te_mon_reserve_currency_premium,
step 9b), the way #1810 pays a union leader's issuer cut, and a leader's own
issuer cut is netted so nothing is paid twice.

These tests run the real script in test_monetary_union_leader's interpreter:
the structural half of step 5 (where the floor is applied and what it swallows
is now recorded) and step 9b's two applications (the standing modifier, then
the floor's cut after the union's update), month by month, so the one-month lag
of every modifier-borne term is in them.

* an anchor above its floor is unchanged; on it, the whole cut is risk premium;
  part-way, the standing cut down to the floor and the rest as risk premium.
  In each case the country pays max(floor, standing before the cut) - the cut;
* the floor read is the step's own (te_mon_standing_floor, through the variable
  step 5 writes where it applies it), not a second copy of the law and the two
  technologies that move it;
* a union leader's issuer cut is netted: it gets the larger of the two, never
  the sum; Singapore 1958's issuer cut covers its whole reserve cut;
* the modifier comes off when the country stops anchoring, leaves its floor, or
  the banking rule leaves Full;
* te_monetary_apply_fx_one's 0.01 cutoff applies to it too: a cut under 0.01
  points is paid in neither form, as before (six of the nine anchors);
* an imposed peg counts, as it does toward the standing cut (ruling C1, L18);
* the modifier, its one refresh site, its strip, its tracker, and the text that
  describes the benefit.
"""

import re
import unittest
from pathlib import Path

from test_monetary_union_leader import WORLD_M, Country, Script, definitions, english, field, union

ROOT = Path(__file__).resolve().parent
MODIFIER = "te_mon_reserve_currency_premium"
STANDING = "te_mon_arrangement_standing"
ISSUER = "te_mon_union_issuer_premium"
PTS, APPLIED = "te_mon_reserve_floor_pts", "te_mon_reserve_floor_applied"
SWALLOWED = "te_premium_floor_swallowed"
VALUE = "te_mon_reserve_floor_value"
EFFECT = "te_monetary_apply_reserve_floor_premium"
MON_EFFECTS = "common/scripted_effects/te_monetary_effects.txt"
ARR_EFFECTS = "common/scripted_effects/te_monetary_arrangement_effects.txt"
ARR_VALUES = "common/script_values/te_monetary_arrangement_script_values.txt"
UNION_EFFECTS = "common/scripted_effects/te_monetary_union_effects.txt"
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
ACCESS = 0.0        # the capital-market access term: every finance technology, a stock exchange


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def block(text, name):
    """The body of the top-level `name = { ... }` block, comments stripped."""
    text = strip_comments(text)
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def apply_calls(body, name):
    """Every te_monetary_apply_fx_one call in a parsed body that steps `name`, as parsed items."""
    found = []
    for key, op, val in body:
        if key == "te_monetary_apply_fx_one" and isinstance(val, list) and field(val, "NAME") == name:
            found.append((key, op, val))
        elif isinstance(val, list):
            found.extend(apply_calls(val, name))
    return found


class FloorScript(Script):
    """The union harness, taught the monthly update's step 5 and the arrangement effects."""

    def __init__(self):
        super().__init__(world_gdp_m=WORLD_M)
        effects = definitions(MON_EFFECTS)
        effects.update(definitions(ARR_EFFECTS))
        effects.update(self.effects)            # the union's and the fx file's own win, as loaded
        self.effects = effects


def anchor(before_cut, share=0.05, floor_add=0.0, name="anchor"):
    """A country with treaty peggers worth `share` of world GDP, whose credit standing would
    be `before_cut` points without the reserve currency's cut (its other terms summed)."""
    c = Country(name, 50_000_000_000)
    c.vars.update(te_mon_anchor_kind=0, te_mon_anchored_gdp_m=share * WORLD_M)
    c.before_cut = before_cut
    c.sums["country_credit_standing_floor_add"] = floor_add
    return c


class Pulse:
    """One country's month, in the monthly update's order: step 5's structural sum and floor,
    then step 9b's standing modifier, the union's update and the floor's cut. Step 5 reads
    the standing modifier the last pulse left, as the engine's modifier sum does."""

    def __init__(self, test):
        self.s = FloorScript()
        self.s.stub_values["te_mon_access_premium"] = ACCESS
        premium = self.s.effects["te_monetary_update_premium"]
        end = next(i for i, (key, _, val) in enumerate(premium)
                   if key == "set_variable" and field(val, "name") == "te_premium_cyclical")
        self.structural = premium[:end]
        arrangements = self.s.effects["te_monetary_apply_arrangement_modifiers"]
        (self.standing_call,) = apply_calls(arrangements, STANDING)
        union_body = self.s.effects["te_monetary_update_union"]
        after = next(i for i, (key, _, val) in enumerate(union_body)
                     if key == "set_variable" and field(val, "name") == "te_mon_union_q_state")
        self.union_tail = union_body[after + 1:]
        test.assertIn(EFFECT, self.s.effects, f"{EFFECT} is not defined")

    def seed(self, c):
        # The phase-1 and phase-4 seeds the arrangement seeds copy from.
        c.vars.setdefault("te_policy_rate", 3)
        c.vars.setdefault("te_fx_index", 100)
        self.s.run("te_monetary_init_arrangement_variables", c)
        for name in ("te_mon_work", "te_mon_work2"):
            c.vars.setdefault(name, 0)
        c.vars["te_mon_work_gdp"] = c.gdp

    def month(self, c):
        self.seed(c)
        before = getattr(c, "before_cut", None)
        if before is not None:
            on = c.mods.get(STANDING, 0)
            c.sums["country_credit_standing_add"] = (before - ACCESS) / 100 - on / 100
        self.s.pulse(self.structural, c)
        c.vars["te_mon_arr_standing_pts"] = self.s.number("te_mon_arr_standing_value", c, c)
        self.s.pulse([self.standing_call, *self.union_tail, (EFFECT, "=", "yes")], c)

    def cut(self, c):
        return self.s.number("te_mon_reserve_currency_cut", c, c)


def paid(c):
    """What the country's structural and modifier-borne cyclical premium come to, in points:
    the floored standing, less the risk premium the floor's cut and the issuer's cut take off."""
    return c.vars["te_premium_structural"] - c.mods.get(MODIFIER, 0) - c.mods.get(ISSUER, 0)


class FloorTest(unittest.TestCase):
    """Above, on and part-way through the floor: the cut always counts, once."""

    def setUp(self):
        self.p = Pulse(self)

    def settle(self, c, months=3):
        for _ in range(months):
            self.p.month(c)

    def test_above_the_floor_nothing_changes(self):
        c = anchor(before_cut=1.0)
        self.settle(c)
        self.assertAlmostEqual(c.mods[STANDING], 0.1)
        self.assertAlmostEqual(c.vars["te_premium_structural"], 0.9)
        self.assertEqual(c.vars[SWALLOWED], 0)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertEqual(c.vars[APPLIED], 0)

    def test_on_the_floor_the_whole_cut_is_risk_premium(self):
        c = anchor(before_cut=0.2)
        self.settle(c)
        self.assertAlmostEqual(c.vars["te_premium_structural"], 0.5, msg="standing sits on its floor")
        self.assertAlmostEqual(c.vars[SWALLOWED], 0.4, msg="0.2 less the cut's 0.1, up to the floor's 0.5")
        self.assertAlmostEqual(c.mods[MODIFIER], 0.1)
        self.assertAlmostEqual(c.vars[APPLIED], c.mods[MODIFIER])
        self.assertAlmostEqual(paid(c), 0.4)

    def test_part_way_the_standing_cut_down_to_the_floor_and_the_rest_as_risk_premium(self):
        c = anchor(before_cut=0.55)
        self.settle(c)
        self.assertAlmostEqual(c.mods[STANDING], 0.1, msg="the standing cut is unchanged")
        self.assertAlmostEqual(c.vars["te_premium_structural"], 0.5)
        self.assertAlmostEqual(c.mods[MODIFIER], 0.05)
        self.assertAlmostEqual(paid(c), 0.45)

    def test_the_cut_always_counts_once(self):
        # Whatever the standing before the cut, the country pays the higher of it and the floor,
        # less the cut: B is the cut taken off after the floor (§ 0.16).
        for share in (0.05, 0.2):
            for before in (-1.0, 0.0, 0.3, 0.45, 0.52, 0.56, 0.62, 0.9, 2.0):
                with self.subTest(share=share, before=before):
                    c = anchor(before_cut=before, share=share)
                    self.settle(c)
                    cut = self.p.cut(c)
                    self.assertAlmostEqual(paid(c), max(0.5, before) - cut)

    def test_the_first_month_is_a_month_late_like_every_modifier_borne_term(self):
        # Month 1: the standing modifier is put on in 9b, after step 5 summed without it; the
        # floor's cut sees only what step 5 saw. From month 2 both are in force.
        c = anchor(before_cut=0.55)
        self.p.month(c)
        self.assertAlmostEqual(c.mods[STANDING], 0.1)
        self.assertNotIn(MODIFIER, c.mods, "0.55 is above the floor until the standing cut lands")
        self.p.month(c)
        self.assertAlmostEqual(c.mods[MODIFIER], 0.05)

    def test_the_floor_is_the_steps_own(self):
        # Central Bank Independence and the two late technologies: a floor of 0.05, read through
        # te_mon_standing_floor from the modifier sum, as step 5 applies it.
        c = anchor(before_cut=-0.5, floor_add=-0.0045)
        self.settle(c)
        self.assertAlmostEqual(c.vars["te_premium_structural"], 0.05)
        self.assertAlmostEqual(c.vars[SWALLOWED], 0.65)
        self.assertAlmostEqual(c.mods[MODIFIER], 0.1)
        c = anchor(before_cut=0.12, floor_add=-0.0045)
        self.settle(c)
        self.assertAlmostEqual(c.mods[MODIFIER], 0.03, msg="0.12 - 0.1 = 0.02, up to 0.05")
        self.assertAlmostEqual(paid(c), 0.02)

    def test_the_figure_is_stepped_like_every_premium_term(self):
        # te_monetary_apply_fx_one rewrites a figure only when it has moved 0.05 points. In the
        # first month the standing cut is not yet in step 5's sum, so an anchor that was on its
        # floor by less than the cut is first paid what the floor took then; the next month's
        # figure is the whole cut, and it is rewritten only if that is 0.05 or more away.
        for before, first, settled in ((0.48, 0.02, 0.1), (0.46, 0.04, 0.1), (0.44, 0.06, 0.06)):
            with self.subTest(before=before):
                c = anchor(before_cut=before)
                self.p.month(c)
                self.assertAlmostEqual(c.mods[MODIFIER], first)
                self.settle(c)
                self.assertAlmostEqual(c.mods[MODIFIER], settled)
                self.assertAlmostEqual(c.vars[PTS], 0.1)
                self.assertLess(c.vars[PTS] - c.mods[MODIFIER], 0.05, "never further off than the step")


class LeaderTest(unittest.TestCase):
    """A union leader's issuer cut (#1810) answers the same floor: nobody is paid twice."""

    def setUp(self):
        self.p = Pulse(self)

    def leader(self, tier, anchored_m, **kw):
        c = union(tier, **kw)
        c.vars["te_mon_anchored_gdp_m"] = anchored_m
        c.before_cut = 0.0
        c.sums["country_credit_standing_floor_add"] = 0.0
        return c

    def test_the_issuer_gets_the_larger_of_the_two_never_the_sum(self):
        # Tier II: the issuer's base is its adopters (1bn beside its own 10bn: reach 0.4, a cut of
        # 0.2), while 30bn of the world is anchored on its money: a reserve cut of 0.36.
        c = self.leader(2, 30_000, adopters=(1e9,))
        for _ in range(3):
            self.p.month(c)
        cut = self.p.cut(c)
        self.assertAlmostEqual(cut, 30_000 / WORLD_M / 0.05 * 0.1)
        self.assertAlmostEqual(c.mods[ISSUER], 0.2)
        self.assertAlmostEqual(c.mods[MODIFIER], cut - 0.2)
        self.assertAlmostEqual(c.mods[ISSUER] + c.mods[MODIFIER], cut)
        self.assertAlmostEqual(paid(c), 0.5 - cut)

    def test_an_issuer_cut_larger_than_the_reserve_cut_leaves_nothing_to_pay(self):
        # The owner's Singapore 1958: the reserve cut is 0.09 points, the issuer's 0.42.
        from test_monetary_union_leader import SGP_ADOPTERS_M, SGP_ANCHORED_M, SGP_GDP
        c = self.leader(5, SGP_ANCHORED_M, leader_gdp=SGP_GDP, adopters=(SGP_ADOPTERS_M * 1e6,))
        for _ in range(3):
            self.p.month(c)
        self.assertLess(self.p.cut(c), c.mods[ISSUER])
        self.assertAlmostEqual(c.mods[ISSUER], 0.4248, places=3)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertEqual(c.vars[PTS], 0)

    def test_a_leader_whose_union_stops_paying_gets_the_reserve_cut_back(self):
        # The last adopter leaves: the issuer's cut goes, and the floor's cut is the whole reserve cut.
        c = self.leader(2, 30_000, adopters=(1e9,))
        for _ in range(2):
            self.p.month(c)
        for member in c.bloc.members[1:]:
            member.vars["te_mon_anchor_kind"] = 0
        for _ in range(2):
            self.p.month(c)
        self.assertNotIn(ISSUER, c.mods)
        self.assertAlmostEqual(c.mods[MODIFIER], self.p.cut(c))


class RemovalTest(unittest.TestCase):
    """The modifier goes when the country stops anchoring or leaves its floor."""

    def setUp(self):
        self.p = Pulse(self)

    def on_the_floor(self):
        c = anchor(before_cut=0.2)
        for _ in range(2):
            self.p.month(c)
        self.assertIn(MODIFIER, c.mods)
        return c

    def test_an_anchor_that_stops_anchoring(self):
        c = self.on_the_floor()
        c.vars["te_mon_anchored_gdp_m"] = 0         # the global pass, after the last peg ended
        self.p.month(c)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertEqual(c.vars[APPLIED], 0)
        self.assertNotIn(STANDING, c.mods)

    def test_an_anchor_that_leaves_its_floor(self):
        c = self.on_the_floor()
        c.before_cut = 1.5                           # a law, a rank, a premium of its own
        self.p.month(c)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertIn(STANDING, c.mods)

    def test_a_missing_modifier_is_put_back(self):
        # A revolution's winner inherits no modifier; a change of the modifiers' home strips it.
        c = self.on_the_floor()
        del c.mods[MODIFIER]
        self.p.month(c)
        self.assertAlmostEqual(c.mods[MODIFIER], 0.1)

    def test_the_rule_switch_strips_it(self):
        settle = block(read(MON_EFFECTS), "te_monetary_settle_modifier_home")
        self.assertIn(f"te_mon_mod_strip = {{ NAME = {MODIFIER} }}", settle)
        leave = block(read("common/scripted_effects/te_monetary_rule_switch_effects.txt"), "te_monetary_leave_full_system")
        self.assertIn("set_variable = { name = te_mon_mod_home value = -1 }", leave)

    def test_it_is_refreshed_only_under_the_full_system(self):
        update = block(read(MON_EFFECTS), "te_monetary_monthly_update")
        gated = re.search(r"if = \{\s*limit = \{ te_mon_full_system = yes \}\s*te_monetary_apply_fx_modifiers = yes\s*"
                          r"te_monetary_apply_arrangement_modifiers = yes", update)
        self.assertIsNotNone(gated, "step 9b's arrangement half runs only under the full system")
        self.assertLess(update.index("te_monetary_update_premium = yes"),
                        update.index("te_monetary_apply_arrangement_modifiers = yes"),
                        "step 5 writes what the floor swallowed before 9b reads it")


class CutoffTest(unittest.TestCase):
    """te_monetary_apply_fx_one never applies a figure under 0.01 points, this one included."""

    def setUp(self):
        self.p = Pulse(self)

    def test_a_cut_under_a_hundredth_is_paid_in_neither_form(self):
        # 0.45% of world GDP pegged: 0.009 points, the North American Union's in the 2020 save.
        c = anchor(before_cut=0.2, share=0.0045)
        for _ in range(3):
            self.p.month(c)
        self.assertAlmostEqual(self.p.cut(c), 0.009)
        self.assertNotIn(STANDING, c.mods)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertAlmostEqual(c.vars[PTS], 0.009, msg="the figure is computed, and not applied")
        self.assertAlmostEqual(paid(c), 0.5)

    def test_a_swallowed_part_under_a_hundredth_is_lost(self):
        # Part-way, with the floor taking 0.005 of a 0.1 cut: the standing gives 0.095, the rest
        # is under the cutoff, and the country pays 0.005 more than the cut would say.
        c = anchor(before_cut=0.595)
        for _ in range(3):
            self.p.month(c)
        self.assertAlmostEqual(c.vars[SWALLOWED], 0.005)
        self.assertNotIn(MODIFIER, c.mods)
        self.assertAlmostEqual(paid(c), 0.5)

    def test_one_step_size_and_cutoff_for_every_premium_term(self):
        calls = re.findall(r"te_monetary_apply_fx_one = \{ NAME = " + MODIFIER + r" ([^}]*)\}",
                           strip_comments(read(ARR_EFFECTS)))
        self.assertEqual(calls, [f"VALUE = var:{PTS} APPLIED = {APPLIED} STEP = 0.05 STEP_NEG = -0.05 "])
        fx = block(read("common/scripted_effects/te_monetary_fx_effects.txt"), "te_monetary_apply_fx_one")
        self.assertIn("var:te_mon_work < 0.01", fx)


class ImposedPegTest(unittest.TestCase):
    """An imposed peg counts toward the cut, chosen or not (ruling C1; owner, 2026-11-16, L18):
    so where the floor swallows the standing cut, an imposed peg now pays its anchor too."""

    def test_the_anchored_sum_counts_every_peg(self):
        refresh = block(read(ARR_EFFECTS), "te_monetary_refresh_anchored_gdp")
        self.assertIn("var:te_mon_anchor_kind < 3", refresh)
        self.assertNotIn("te_mon_is_imposed_pegger", refresh)
        self.assertNotIn("te_mon_is_imposed_pegger", block(read(ARR_VALUES), VALUE))
        self.assertNotIn("te_mon_is_imposed_pegger", block(read(ARR_VALUES), "te_mon_reserve_currency_cut"))


class WiringTest(unittest.TestCase):
    """One modifier, one refresh site, one tracker, the step's own floor."""

    def test_one_unit_of_risk_premium(self):
        static = definitions(MODIFIERS)
        effects = [(k, v) for k, _, v in static[MODIFIER] if k != "icon"]
        self.assertEqual(effects, [("country_risk_premium_add", "-0.01")])

    def test_one_refresh_site_after_the_union_update(self):
        sites = []
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").glob("*.txt")):
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            for m in re.finditer(r"(te_monetary_apply_fx_one|te_mon_mod_add_scaled|te_mon_mod_add|add_modifier)"
                                 r"\s*=\s*\{\s*(?:NAME|name)\s*=\s*" + MODIFIER + r"\b", text):
                sites.append((path.name, m.group(1)))
        self.assertEqual(sites, [("te_monetary_arrangement_effects.txt", "te_monetary_apply_fx_one")])
        body = block(read(ARR_EFFECTS), "te_monetary_apply_arrangement_modifiers")
        self.assertLess(body.index("te_monetary_update_union = yes"), body.index(f"{EFFECT} = yes"),
                        "the issuer's cut is this month's when it is netted")
        self.assertEqual(len(re.findall(rf"\b{EFFECT} = yes", strip_comments(
            "\n".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "common").rglob("*.txt"))))), 1)
        effect = block(read(ARR_EFFECTS), EFFECT)
        self.assertIn("root ?= this", effect, "a scaled add reads root.var")

    def test_the_tracker_is_seeded_and_classified(self):
        seeds = block(read(ARR_EFFECTS), "te_monetary_init_arrangement_variables")
        for name in (PTS, APPLIED):
            self.assertIn(f"has_variable = {name} }}", seeds)
        init = block(read(MON_EFFECTS), "te_monetary_init_variables")
        self.assertIn(f"has_variable = {SWALLOWED} }}", init)

    def test_what_the_floor_swallowed_is_written_only_where_the_floor_is_applied(self):
        writes = []
        for path in sorted((ROOT / "common").rglob("*.txt")):
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            writes += [path.name for _ in re.finditer(r"(?:set|change)_variable = \{ name = " + SWALLOWED + r"\b", text)]
        self.assertEqual(writes, ["te_monetary_effects.txt"] * 4, "the seed, the reset, and the floor's two lines")
        premium = block(read(MON_EFFECTS), "te_monetary_update_premium")
        floor_if = re.search(r"if = \{\s*limit = \{ var:te_premium_structural < te_mon_standing_floor \}(.*?)\n\t\}",
                             premium, re.S)
        self.assertIsNotNone(floor_if)
        self.assertIn(f"name = {SWALLOWED} value = te_mon_standing_floor", floor_if.group(1))
        self.assertIn(f"name = {SWALLOWED} subtract = var:te_premium_structural", floor_if.group(1))

    def test_the_value_has_no_copy_of_the_floor(self):
        value = block(read(ARR_VALUES), VALUE)
        self.assertIn(f"var:{SWALLOWED}", value)
        self.assertIn("te_mon_reserve_currency_cut", value)
        self.assertIn("var:te_mon_union_issuer_cut_pts", value)
        for copy in ("te_mon_standing_floor", "country_credit_standing_floor_add", "law_central_bank_independence",
                     "machine_learning", "universal_digital_identity", "0.5"):
            self.assertNotIn(copy, value)


class TextTest(unittest.TestCase):
    """What the text says the reserve currency pays is what the script pays."""

    @classmethod
    def setUpClass(cls):
        cls.loc = english()
        cls.values = definitions("common/script_values/te_monetary_arrangement_script_values.txt")

    def test_the_modifier_is_named_and_described(self):
        self.assertTrue(MODIFIER in self.loc, f"{MODIFIER} has no name")
        self.assertLessEqual(len(self.loc[MODIFIER]), 70)
        self.assertNotRegex(self.loc[MODIFIER], r"\d")
        desc = self.loc[f"{MODIFIER}_desc"]
        self.assertIn("[concept_banking_credit_standing]", desc, "why: the standing it would have earned is at its best")
        self.assertLess(len(re.sub(r"\[concept_\w+\]", "xx", desc).split()), 20, "one sentence, under 20 words")

    def test_the_anchor_row_says_why(self):
        self.assertIn("[Country.GetCustom('te_mon_reserve_floor_note')]", self.loc["banking_dash_mon_anchor_tt"])
        custom = block(read("common/customizable_localization/banking_dash_custom_loc.txt"), "te_mon_reserve_floor_note")
        keys = re.findall(r"localization_key = (\w+)", custom)
        self.assertEqual(keys[-1], "banking_dash_mon_anchor_floor_note_none")
        self.assertEqual(self.loc["banking_dash_mon_anchor_floor_note_none"], "")
        for key in keys[:-1]:
            self.assertIn("te_mon_reserve_floor_display", self.loc[key])
            self.assertIn("[concept_banking_risk_premium]", self.loc[key])
        self.assertIn("te_mon_reserve_floor_display > 0", custom)

    def test_the_anchors_figures_are_the_script_values(self):
        text = self.loc["currency_peg_effects_desc"]
        anchor_part = text.split("#b Anchor:#!")[1]
        self.assertIn(f"#G {self.values['te_mon_reserve_currency_per_step'][0][2]} percentage points#! per "
                      f"#v {round(float(self.values['te_mon_reserve_currency_step_share'][0][2]) * 100)}%#!", anchor_part)
        self.assertIn(f"#v {self.values['te_mon_reserve_currency_cap'][0][2]}#!", anchor_part)
        self.assertIn(f"#v {self.values['te_mon_reserve_currency_cap_tier_5'][0][2]}#!", anchor_part)

    def test_every_text_of_the_anchors_benefit_says_what_the_floor_does(self):
        for key in ("currency_peg_effects_desc", "banking_dash_how_anchor"):
            with self.subTest(key=key):
                self.assertRegex(self.loc[key], r"floor[^.]*risk premium|risk premium[^.]*floor")
        self.assertRegex(self.loc["imposed_currency_peg_effects_desc"].split("#b Anchor:#!")[1],
                         r"risk premium")

    def test_the_guide_says_so(self):
        guide = read("docs/player_guide/04-banking.md")
        row = next(line for line in guide.splitlines() if line.startswith("| Currency Peg | A small economy"))
        self.assertRegex(row, r"floor")


if __name__ == "__main__":
    unittest.main()
