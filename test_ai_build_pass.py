"""The AI construction pass (common/scripted_effects/te_ai_build_pass_effects.txt, #1877).

Once a month an AI government whose government queue has stood empty a month gets one level queued, if the interest
rate allows it the means (te_ai_build_pass_means: reserves above the reserve the rate asks for, plus the debt it may
hold at its rate, less its debt) and it has the surplus the engine's budget AI asks for before it adds spending. What
it queues, in order of what does most good (owner, 2026-11-16): a Government Administration while net bureaucracy is
under 2% of its usage; else a university while innovation is under nine-tenths of its cap and bureaucracy is not
short; each only where the surplus pays for the level within two years; else nothing. It follows the level until it
is built or gone, queues nothing more meanwhile, and none of a kind for a year after one of that kind was lost. The
engine itself queues nothing new for a government in debt. The rate's curve is pinned in
test_construction_market_ai_purchase.py (TheRate); this file holds the pass's own text and values: its conditions,
its order, the means it reads, the follow, the back-off, and its self-check.

Run: python3 -m pytest test_ai_build_pass.py -q
"""
import re
import unittest
from pathlib import Path

import test_construction_market_ai_purchase as purchase
from test_construction_market_budget_step import load

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/te_ai_build_pass_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_build_pass_triggers.txt"
VALUES = ROOT / "common/script_values/te_ai_build_pass_values.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_ai_build_pass_on_actions.txt"
GATE_CHECK = ROOT / "common/on_actions/te_ai_reserve_gate_selfcheck_on_actions.txt"
FILES = (EFFECTS, TRIGGERS, VALUES, ON_ACTIONS)
AI_DOC = ROOT / "docs/systems/mod_systems/ai.md"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text(encoding="utf-8-sig").splitlines())


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _block(text, name):
    """The body of the top-level block `name = { ... }`, by brace count."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if m is None:
        raise KeyError(name)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class Files(unittest.TestCase):
    def test_one_bom_and_tabs(self):
        for path in FILES:
            raw = path.read_bytes()
            with self.subTest(path=path.name):
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
                self.assertEqual([n for n, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1)
                                  if re.match(r"^ +\S", line)], [])

    def test_every_te_ai_build_pass_name_it_reads_is_defined(self):
        defined = set()
        for path in FILES:
            defined |= set(re.findall(r"(?m)^(te_ai_build_pass_[a-z_]+) = ", _code(path)))
        variables = {"te_ai_build_pass_idle", "te_ai_build_pass_recent", "te_ai_build_pass_count",
                     "te_ai_build_pass_on_actions", "te_ai_build_pass_effects",
                     "te_ai_build_pass_pending_kind", "te_ai_build_pass_pending_base", "te_ai_build_pass_pending_months",
                     "te_ai_build_pass_sampled", "te_ai_build_pass_backoff_university",
                     "te_ai_build_pass_backoff_administration",
                     "te_ai_build_pass_checked", "te_ai_build_pass_built", "te_ai_build_pass_waiting",
                     "te_ai_build_pass_lost"}
        used = set()
        for path in FILES:
            used |= set(re.findall(r"\b(te_ai_build_pass_[a-z_]+)\b", _code(path)))
        self.assertEqual(sorted(used - defined - variables), [])


class Wiring(unittest.TestCase):
    def test_an_ai_country_runs_it_monthly_and_the_world_reads_the_verdict(self):
        code = _code(ON_ACTIONS)
        self.assertIn("on_actions = { te_ai_build_pass_on_action }",
                      _norm(_block(code, "on_monthly_pulse_country")))
        self.assertIn("on_actions = { te_ai_build_pass_selfcheck }", _norm(_block(code, "on_monthly_pulse")))
        self.assertEqual(_norm(_block(code, "te_ai_build_pass_on_action")),
                         "trigger = { is_ai = yes } effect = { te_ai_build_pass_effect = yes }")

    def test_it_queues_only_where_the_engine_has_not_and_the_budget_ai_would(self):
        may = _norm(_block(_code(TRIGGERS), "te_ai_build_pass_may_queue"))
        self.assertTrue(may.startswith("is_country_alive = yes is_ai = yes"))
        for part in ("NOT = { is_country_type = decentralized }", "te_free_market_construction_on = yes",
                     "in_default = no", "is_at_war = no", "is_construction_paused = no",
                     "has_variable = te_ai_build_pass_idle",
                     "NOT = { has_variable = te_ai_build_pass_pending_kind }",
                     "NOT = { construction_queue_num_queued_government_levels > 0 }",
                     "has_variable = te_construction_market_price_stabilizer", "net_fixed_income > 0",
                     "OR = { net_fixed_income >= TE_AI_BUILD_PASS_SURPLUS_MIN "
                     "te_ai_build_pass_surplus_share >= TE_AI_BUILD_PASS_SURPLUS_SHARE }",
                     "te_ai_build_pass_means >= 0"):
            with self.subTest(part=part):
                self.assertIn(part, may)

    def test_an_administration_first_then_a_university_one_level_each(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        administration = effect.index("te_ai_build_pass_wants_administration = yes")
        university = effect.index("te_ai_build_pass_wants_university = yes")
        self.assertLess(effect.index("te_ai_build_pass_may_queue = yes"), administration)
        self.assertLess(administration, university)
        self.assertRegex(effect[administration:university], r"\} else_if = \{ limit = \{ $")
        idle = effect.index("# Next") if "# Next" in effect else effect.rindex("if = { limit = { "
                                                                              "construction_queue_num_queued")
        for building, site, order, kind, start, end in (
                ("building_government_administration", "administration_site", "te_ai_build_pass_tax_shortfall", 2,
                 administration, university),
                ("building_university", "university_site", "state_population", 1, university, idle)):
            branch = effect[start:end]
            with self.subTest(building=building):
                self.assertIn(f"ordered_scope_state = {{ limit = {{ te_ai_build_pass_{site} = yes }} "
                              f"order_by = {order} position = 0 check_range_bounds = no "
                              f"start_building_construction = {building} }}", branch)
                self.assertEqual(branch.count("start_building_construction"), 1)
                self.assertIn("set_variable = { name = te_ai_build_pass_recent value = yes days = 45 }", branch)
                self.assertIn("te_ai_build_pass_count_effect = yes", branch)
                self.assertLess(branch.index(f"te_ai_build_pass_pending_start = {{ KIND = {kind} }}"),
                                branch.index("ordered_scope_state"))
        self.assertEqual(effect.count("start_building_construction"), 2)

    def test_the_follow_comes_first_and_the_month_of_waiting_last(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        self.assertTrue(effect.startswith("te_ai_build_pass_follow = yes if = { limit = { "
                                          "te_ai_build_pass_may_queue = yes }"))
        self.assertTrue(effect.endswith(
            "if = { limit = { construction_queue_num_queued_government_levels > 0 } if = { limit = { "
            "has_variable = te_ai_build_pass_idle } remove_variable = te_ai_build_pass_idle } } else = { "
            "set_variable = te_ai_build_pass_idle }"))
        self.assertGreater(effect.index("if = { limit = { construction_queue_num_queued_government_levels > 0 }"),
                           effect.rindex("start_building_construction"))

    def test_what_makes_each_building_worth_queueing(self):
        triggers = _code(TRIGGERS)
        administration = _norm(_block(triggers, "te_ai_build_pass_wants_administration"))
        for part in ("has_technology_researched = tech_bureaucracy",
                     "NOT = { has_variable = te_ai_build_pass_backoff_administration }",
                     "bureaucracy < te_ai_build_pass_bureaucracy_margin",
                     "te_ai_build_pass_administration_weeks <= TE_AI_BUILD_PASS_MAX_WEEKS",
                     "any_scope_state = { te_ai_build_pass_administration_site = yes }"):
            with self.subTest(part=part):
                self.assertIn(part, administration)
        self.assertNotIn("tax_capacity", administration)
        university = _norm(_block(triggers, "te_ai_build_pass_wants_university"))
        for part in ("has_technology_researched = academia", "NOT = { has_variable = poland_universities_closed_var }",
                     "NOT = { has_variable = te_ai_build_pass_backoff_university }", "bureaucracy >= 0",
                     "te_ai_build_pass_innovation_share < TE_AI_BUILD_PASS_INNOVATION_SHARE",
                     "te_ai_build_pass_university_weeks <= TE_AI_BUILD_PASS_MAX_WEEKS",
                     "any_scope_state = { te_ai_build_pass_university_site = yes }"):
            with self.subTest(part=part):
                self.assertIn(part, university)
        for site in ("te_ai_build_pass_administration_site", "te_ai_build_pass_university_site"):
            self.assertEqual(_norm(_block(triggers, site)), "is_incorporated = yes")

    def test_the_polish_closure_is_vanillas_university_rule(self):
        path = purchase._game_file("buildings/07_government.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        body = _block(path.read_text(encoding="utf-8-sig"), "building_university")
        self.assertIn("poland_universities_closed_var", _block(body, "\tcan_build_government"))


class Env(unittest.TestCase):
    """The pass's values through the construction market's evaluator."""

    @classmethod
    def setUpClass(cls):
        cls.constants, cls.values = load(VALUES)

    def value(self, c, name, **names):
        env = c.env()
        env.values = dict(env.values, **self.values)
        env.names.update(names)
        return env.value(name)


class TheMeans(Env):
    def means(self, c):
        return self.value(c, "te_ai_build_pass_means")

    def test_by_rate_reserves_and_debt(self):
        surplus, era = 0.4 * 75817.0, 2.5
        for spread, reserves, debt, has_means in (
                # A high rate asks for a reserve first.
                (9.0, 0.0, 0.0, False), (9.0, 0.05, 0.0, False), (9.0, purchase.RESERVE_MAX, 0.0, True),
                # The middle asks for nothing and tolerates nothing: no debt.
                (purchase.SPREAD_MID, 0.0, 0.0, True), (purchase.SPREAD_MID, 0.0, 0.01, False),
                # A low rate tolerates a debt up to DEBT_MAX.
                (0.0, 0.0, 0.05, True), (0.0, 0.0, purchase.PASS_DEBT_MAX - 0.001, True), (0.0, 0.0, 0.11, False),
                (3.0, 0.0, 0.04, True), (3.0, 0.0, 0.06, False)):
            for constants in (None, purchase.NO_CREDIT):
                c = purchase.Country(75817.0, surplus, 1256.0, reserves, debt, rate=era + spread, era=era,
                                     constants=constants)
                with self.subTest(spread=spread, reserves=reserves, debt=debt, credit_switch=constants):
                    # The credit's switch at 0 leaves the pass reaching a debtor at a low rate.
                    self.assertEqual(self.means(c) >= 0, has_means)

    def test_with_its_own_number_at_zero_it_reaches_no_debtor(self):
        c = purchase.Country(75817.0, 30000.0, 1256.0, 0.0, 0.01, rate=2.5, constants={"TE_AI_BUILD_PASS_DEBT_MAX": 0.0})
        self.assertLess(self.means(c), 0)

    def test_in_a_crisis_at_war_or_in_a_bubble_a_government_in_debt_has_none(self):
        for crisis, at_war, bubble in ((True, False, None), (False, True, None), (False, False, 60.0)):
            c = purchase.Country(75817.0, 30000.0, 1256.0, 0.0, 0.03, rate=2.5, crisis=crisis, at_war=at_war,
                                 bubble=bubble)
            with self.subTest(crisis=crisis, at_war=at_war, bubble=bubble):
                self.assertLess(self.means(c), 0)

    def test_a_thin_surplus_has_the_means_only_for_a_thin_debt(self):
        # The tolerance is what a third of the surplus carries at the high rate: about 0.0044 of a 320-week ceiling
        # for a surplus of 1% of fixed income.
        thin = [purchase.Country(10000.0, 100.0, 1256.0, 0.0, debt, rate=2.5) for debt in (0.004, 0.006)]
        self.assertEqual([self.means(c) >= 0 for c in thin], [True, False])

    def test_the_innovation_share_reads_one_where_the_cap_reads_nothing(self):
        body = _norm(_block(_code(VALUES), "te_ai_build_pass_innovation_share"))
        self.assertEqual(body, "value = 1 if = { limit = { te_ai_build_pass_innovation_cap > 0 } value = "
                               "country_innovation divide = te_ai_build_pass_innovation_cap }")
        self.assertIn("te_ai_build_pass_innovation_cap = { value = modifier:country_weekly_innovation_max_add }",
                      _code(VALUES))


class WhatItQueues(Env):
    def test_two_years_of_the_surplus_pays_for_the_level(self):
        # A sixth of fixed income at 1,250 a point: a university's 400 points from 28,800 a week, an administration's
        # 100 from 7,200.
        for name, income in (("te_ai_build_pass_university_weeks", 28800.0),
                             ("te_ai_build_pass_administration_weeks", 7200.0)):
            for scale, fits in ((1.02, True), (0.98, False)):
                c = purchase.Country(income * scale, income * scale / 6, 1250.0)
                with self.subTest(value=name, income=income * scale):
                    self.assertEqual(self.value(c, name) <= purchase.PASS_MAX_WEEKS, fits)

    def test_close_to_net_zero_is_two_hundredths_of_usage(self):
        c = purchase.Country(30000.0, 6000.0)
        self.assertAlmostEqual(self.value(c, "te_ai_build_pass_bureaucracy_margin", bureaucracy_usage=4000.0),
                               purchase.PASS_BUREAUCRACY_MARGIN * 4000.0, delta=0.001)

    def test_the_numbers_it_reads_are_the_values_files(self):
        triggers = _code(TRIGGERS)
        for name in ("TE_AI_BUILD_PASS_MAX_WEEKS", "TE_AI_BUILD_PASS_INNOVATION_SHARE"):
            self.assertIn(name, triggers)
        self.assertIn("multiply = TE_AI_BUILD_PASS_BUREAUCRACY_MARGIN",
                      _norm(_block(_code(VALUES), "te_ai_build_pass_bureaucracy_margin")))
        for name, points in (("te_ai_build_pass_university_weeks", "construction_cost_medium"),
                             ("te_ai_build_pass_administration_weeks", "construction_cost_very_low")):
            self.assertTrue(_norm(_block(_code(VALUES), name)).startswith(f"value = {points} "))


class TheFollow(unittest.TestCase):
    """What became of each level the pass queued: the back-off, the reserve gate's mark and the self-check read it."""

    def test_it_starts_from_the_built_levels_of_the_kind(self):
        start = _norm(_block(_code(EFFECTS), "te_ai_build_pass_pending_start"))
        self.assertTrue(start.startswith(
            "set_variable = { name = te_ai_build_pass_pending_kind value = $KIND$ } set_variable = { name = "
            "te_ai_build_pass_pending_base value = te_ai_build_pass_tracked_levels } set_variable = { name = "
            "te_ai_build_pass_pending_months value = 0 }"))
        self.assertIn("if = { limit = { NOT = { has_global_variable = te_ai_build_pass_checked } "
                      "te_ai_build_pass_in_sample = yes }", start)
        for counter in ("built", "waiting", "lost"):
            self.assertIn(f"set_global_variable = {{ name = te_ai_build_pass_{counter} value = 0 }}", start)
        self.assertTrue(start.endswith("set_variable = te_ai_build_pass_sampled }"))

    def test_the_sample_is_a_government_the_engine_would_not_queue_for(self):
        self.assertEqual(_norm(_block(_code(TRIGGERS), "te_ai_build_pass_in_sample")),
                         "OR = { scaled_debt > 0 scaled_gold_reserves < 0.02 }")
        self.assertEqual(purchase.MOD_NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"], 0.02)

    def test_built_lost_or_waiting_with_the_base_following_a_downsizing(self):
        follow = _norm(_block(_code(EFFECTS), "te_ai_build_pass_follow"))
        down = follow.index("te_ai_build_pass_tracked_levels < var:te_ai_build_pass_pending_base")
        built = follow.index("te_ai_build_pass_tracked_levels > var:te_ai_build_pass_pending_base")
        lost = follow.index("te_ai_build_pass_tracked_queued <= 0")
        waiting = follow.index("var:te_ai_build_pass_pending_months >= 18")
        self.assertLess(down, built)
        self.assertLess(built, lost)
        self.assertLess(lost, waiting)
        self.assertLess(built, follow.index("te_ai_build_pass_built add = 1"))
        self.assertLess(follow.index("te_ai_build_pass_built add = 1"), lost)
        self.assertLess(lost, follow.index("te_ai_build_pass_lost add = 1"))
        self.assertLess(follow.index("te_ai_build_pass_lost add = 1"), waiting)
        self.assertLess(waiting, follow.index("te_ai_build_pass_waiting add = 1"))
        # Each counts only a sampled level, and only until the verdict.
        self.assertEqual(follow.count("has_variable = te_ai_build_pass_sampled NOT = { has_global_variable = "
                                      "te_ai_build_pass_checked }"), 2)
        self.assertEqual(follow.count("te_ai_build_pass_pending_clear = yes"), 2)
        clear = _norm(_block(_code(EFFECTS), "te_ai_build_pass_pending_clear"))
        for name in ("kind", "base", "months"):
            self.assertIn(f"remove_variable = te_ai_build_pass_pending_{name}", clear)
        self.assertIn("remove_variable = te_ai_build_pass_sampled", clear)

    def test_a_lost_level_backs_its_kind_off_for_a_year(self):
        follow = _norm(_block(_code(EFFECTS), "te_ai_build_pass_follow"))
        lost = follow[follow.index("te_ai_build_pass_tracked_queued <= 0"):]
        days = int(purchase.PASS_BACKOFF_DAYS)
        self.assertIn(f"if = {{ limit = {{ var:te_ai_build_pass_pending_kind = 1 }} set_variable = {{ name = "
                      f"te_ai_build_pass_backoff_university value = yes days = {days} }} }} else = {{ set_variable = "
                      f"{{ name = te_ai_build_pass_backoff_administration value = yes days = {days} }} }}", lost)
        # The literal is the values file's number.
        self.assertEqual(purchase._parsed()["constants"]["TE_AI_BUILD_PASS_BACKOFF_DAYS"], days)

    def test_each_building_is_counted_by_its_own_kind(self):
        values = _code(VALUES)
        for name, field in (("te_ai_build_pass_tracked_levels", "level"),
                            ("te_ai_build_pass_tracked_queued", "te_construction_market_building_queued_levels")):
            body = _norm(_block(values, name))
            with self.subTest(value=name):
                self.assertEqual(body, f"value = 0 if = {{ limit = {{ var:te_ai_build_pass_pending_kind = 1 }} "
                                       f"every_scope_building = {{ limit = {{ is_building_type = building_university }} "
                                       f"add = {field} }} }} else = {{ every_scope_building = {{ limit = {{ "
                                       f"is_building_type = building_government_administration }} add = {field} }} }}")
        self.assertIn("te_construction_market_building_queued_levels = { value = level_after_queued_constructions "
                      "subtract = level }",
                      _norm(_code(ROOT / "common/script_values/te_construction_market_ai_values.txt")))

    def test_the_reserve_gates_check_leaves_out_what_the_pass_queued(self):
        gate = _norm(_code(GATE_CHECK))
        # The watch: the 45-day mark, or a level still followed; the control: a level still followed.
        self.assertIn("NOT = { has_variable = te_ai_build_pass_recent } NOT = { has_variable = "
                      "te_ai_build_pass_pending_kind }", gate)
        self.assertIn("construction_queue_num_queued_government_levels > 0 NOT = { has_variable = "
                      "te_ai_build_pass_pending_kind } }", gate)
        self.assertIn("name = te_ai_build_pass_recent value = yes days = 45", _norm(_code(EFFECTS)))


class TheSelfCheck(unittest.TestCase):
    def test_the_verdict_once_on_twelve_decided_or_thirty_six_in_all(self):
        check = _norm(_block(_code(ON_ACTIONS), "te_ai_build_pass_selfcheck"))
        self.assertIn("trigger = { NOT = { has_global_variable = te_ai_build_pass_checked } has_global_variable = "
                      "te_ai_build_pass_built OR = { te_ai_build_pass_decided_g >= 12 te_ai_build_pass_sampled_g >= 36 "
                      "} }", check)
        effect = check[check.index("effect = {"):]
        self.assertTrue(effect.startswith("effect = { set_global_variable = te_ai_build_pass_checked debug_log = "
                                          "\"TE_SELF_CHECK START ai_build_pass"))
        ok = effect.index("te_ai_build_pass_built_g >= 6 te_ai_build_pass_lost_share <= 0.25")
        broken = effect.index("te_ai_build_pass_decided_g >= 6 te_ai_build_pass_lost_share >= 0.5")
        self.assertLess(effect.index("START"), effect.index("random_country"))
        self.assertLess(ok, effect.index("TE_SELF_CHECK OK ai_build_pass"))
        self.assertLess(ok, broken)
        self.assertLess(broken, effect.index("TE_SELF_CHECK BROKEN ai_build_pass"))
        self.assertLess(effect.index("TE_SELF_CHECK BROKEN"), effect.index("TE_SELF_CHECK NO_VERDICT ai_build_pass"))

    def test_lost_is_judged_on_the_levels_whose_fate_is_known(self):
        values = _code(VALUES)
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_decided_g")),
                         "value = global_var:te_ai_build_pass_built add = global_var:te_ai_build_pass_lost")
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_lost_share")),
                         "value = global_var:te_ai_build_pass_lost divide = { value = te_ai_build_pass_decided_g "
                         "min = 1 }")
        self.assertEqual(_norm(_block(values, "te_ai_build_pass_sampled_g")),
                         "value = te_ai_build_pass_decided_g add = global_var:te_ai_build_pass_waiting")

    def test_its_lines_fit_log_triage(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]+)"', ON_ACTIONS.read_text(encoding="utf-8-sig"))
        self.assertEqual(len(lines), 4)
        for line in lines:
            printed = re.sub(r"\[SCOPE\.ScriptValue\('[a-z_]+'\)\|0\]", "999", line)
            printed = printed.replace("[TimeKeeper.GetCurrentDate.GetString]", "September 30, 1947")
            with self.subTest(line=line[:60]):
                self.assertLess(len(printed), 400)

    def test_the_docs_and_the_play_test_list_carry_it(self):
        doc = AI_DOC.read_text(encoding="utf-8")
        self.assertIn("te_ai_build_pass_effects.txt", doc)
        self.assertIn("ai_build_pass", doc)
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("TE_SELF_CHECK … ai_build_pass", playtest)
        for field in ("rate", "cm_reserve", "cm_credit", "cm_pass"):
            self.assertIn(f"`{field}`", playtest)


if __name__ == "__main__":
    unittest.main()
