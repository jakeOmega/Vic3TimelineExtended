"""The AI construction pass (common/scripted_effects/te_ai_build_pass_effects.txt, #1877).

Once a month an AI government whose government queue has stood empty a month gets one level queued, a university
while innovation is under nine-tenths of its cap or else a Government Administration where taxes outrun tax capacity,
if the interest rate allows it the means (te_ai_build_pass_means: reserves above the reserve the rate asks for, plus
the credit allowance not yet used) and it has the surplus the engine's budget AI asks for before it adds spending. The
engine itself queues nothing new for a government in debt. The rate's curve is pinned in
test_construction_market_ai_purchase.py (TheRate); this file holds the pass's own text: its conditions, its order,
the means it reads, and its self-check.

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
                     "te_ai_build_pass_track_kind", "te_ai_build_pass_track_target", "te_ai_build_pass_track_months",
                     "te_ai_build_pass_checked", "te_ai_build_pass_built", "te_ai_build_pass_waiting",
                     "te_ai_build_pass_lost", "te_ai_build_pass_resolved"}
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
        for part in ("is_ai = yes", "NOT = { is_country_type = decentralized }", "te_free_market_construction_on = yes",
                     "in_default = no", "is_at_war = no", "is_construction_paused = no",
                     "has_variable = te_ai_build_pass_idle",
                     "NOT = { construction_queue_num_queued_government_levels > 0 }", "net_fixed_income > 0",
                     "OR = { net_fixed_income >= TE_AI_BUILD_PASS_SURPLUS_MIN "
                     "te_ai_build_pass_surplus_share >= TE_AI_BUILD_PASS_SURPLUS_SHARE }",
                     "te_ai_build_pass_means >= 0"):
            with self.subTest(part=part):
                self.assertIn(part, may)

    def test_a_university_first_then_an_administration_one_level_each(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        university = effect.index("te_ai_build_pass_wants_university = yes")
        administration = effect.index("te_ai_build_pass_wants_administration = yes")
        self.assertLess(effect.index("te_ai_build_pass_may_queue = yes"), university)
        self.assertLess(university, administration)
        self.assertRegex(effect[university:administration], r"\} else_if = \{ limit = \{ $")
        for building, site, order, start, end in (
                ("building_university", "university_site", "state_population", university, administration),
                ("building_government_administration", "administration_site", "te_ai_build_pass_tax_shortfall",
                 administration, len(effect))):
            branch = effect[start:end]
            with self.subTest(building=building):
                self.assertIn(f"ordered_scope_state = {{ limit = {{ te_ai_build_pass_{site} = yes }} "
                              f"order_by = {order} position = 0 check_range_bounds = no "
                              f"start_building_construction = {building} }}", branch)
                self.assertEqual(branch.count("start_building_construction"), 1)
                self.assertIn("set_variable = { name = te_ai_build_pass_recent value = yes days = 45 }", branch)
                self.assertIn("te_ai_build_pass_count_effect = yes", branch)
                self.assertLess(branch.index("te_ai_build_pass_track_start"), branch.index("ordered_scope_state"))
        self.assertEqual(effect.count("start_building_construction"), 2)

    def test_the_month_of_waiting_is_set_after_the_decision_and_cleared_by_a_queue(self):
        effect = _norm(_block(_code(EFFECTS), "te_ai_build_pass_effect"))
        idle = effect.index("if = { limit = { construction_queue_num_queued_government_levels > 0 }")
        self.assertGreater(idle, effect.rindex("start_building_construction"))
        self.assertIn("if = { limit = { construction_queue_num_queued_government_levels > 0 } if = { limit = { "
                      "has_variable = te_ai_build_pass_idle } remove_variable = te_ai_build_pass_idle } } else = { "
                      "set_variable = te_ai_build_pass_idle }", effect)
        self.assertTrue(effect.endswith("te_ai_build_pass_track_tick = yes"))

    def test_what_makes_each_building_worth_queueing(self):
        triggers = _code(TRIGGERS)
        university = _norm(_block(triggers, "te_ai_build_pass_wants_university"))
        for part in ("has_technology_researched = academia", "NOT = { has_variable = poland_universities_closed_var }",
                     "te_ai_build_pass_innovation_share < TE_AI_BUILD_PASS_INNOVATION_SHARE",
                     "any_scope_state = { te_ai_build_pass_university_site = yes }"):
            self.assertIn(part, university)
        administration = _norm(_block(triggers, "te_ai_build_pass_wants_administration"))
        self.assertIn("has_technology_researched = tech_bureaucracy", administration)
        self.assertEqual(_norm(_block(triggers, "te_ai_build_pass_administration_site")),
                         "is_incorporated = yes tax_capacity < tax_capacity_usage")
        self.assertEqual(_norm(_block(triggers, "te_ai_build_pass_university_site")), "is_incorporated = yes")

    def test_the_polish_closure_is_vanillas_university_rule(self):
        path = purchase._game_file("buildings/07_government.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        body = _block(path.read_text(encoding="utf-8-sig"), "building_university")
        self.assertIn("poland_universities_closed_var", _block(body, "\tcan_build_government"))


class TheMeans(unittest.TestCase):
    """te_ai_build_pass_means through the construction market's evaluator."""

    @classmethod
    def setUpClass(cls):
        cls.constants, cls.values = load(VALUES)

    def means(self, c):
        env = c.env()
        env.values.update(self.values)
        return env.value("te_ai_build_pass_means")

    def test_by_rate_reserves_and_debt(self):
        surplus, era = 0.4 * 75817.0, 2.5
        for spread, reserves, debt, has_means in (
                # A high rate asks for a reserve first.
                (9.0, 0.0, 0.0, False), (9.0, 0.05, 0.0, False), (9.0, purchase.RESERVE_MAX, 0.0, True),
                # The middle asks for nothing and allows nothing: no debt.
                (purchase.SPREAD_MID, 0.0, 0.0, True), (purchase.SPREAD_MID, 0.0, 0.01, False),
                # A low rate allows a debt up to the allowance.
                (0.0, 0.0, 0.05, True), (0.0, 0.0, purchase.CREDIT_MAX - 0.001, True), (0.0, 0.0, 0.11, False),
                (3.0, 0.0, 0.04, True), (3.0, 0.0, 0.06, False)):
            c = purchase.Country(75817.0, surplus, 1256.0, reserves, debt, rate=era + spread, era=era)
            with self.subTest(spread=spread, reserves=reserves, debt=debt):
                self.assertEqual(self.means(c) >= 0, has_means)

    def test_in_a_crisis_or_at_war_a_government_in_debt_has_none(self):
        for crisis, at_war in ((True, False), (False, True)):
            c = purchase.Country(75817.0, 30000.0, 1256.0, 0.0, 0.03, rate=2.5, crisis=crisis, at_war=at_war)
            with self.subTest(crisis=crisis, at_war=at_war):
                self.assertLess(self.means(c), 0)

    def test_a_thin_surplus_has_the_means_only_for_a_thin_debt(self):
        # The allowance is what a third of the surplus carries at the high rate: about 0.0044 of a 320-week ceiling
        # for a surplus of 1% of fixed income.
        thin = [purchase.Country(10000.0, 100.0, 1256.0, 0.0, debt, rate=2.5) for debt in (0.004, 0.006)]
        self.assertEqual([self.means(c) >= 0 for c in thin], [True, False])

    def test_the_innovation_share_reads_one_where_the_cap_reads_nothing(self):
        body = _norm(_block(_code(VALUES), "te_ai_build_pass_innovation_share"))
        self.assertEqual(body, "value = 1 if = { limit = { te_ai_build_pass_innovation_cap > 0 } value = "
                               "country_innovation divide = te_ai_build_pass_innovation_cap }")
        self.assertIn("te_ai_build_pass_innovation_cap = { value = modifier:country_weekly_innovation_max_add }",
                      _code(VALUES))


class TheSelfCheck(unittest.TestCase):
    def test_it_follows_one_level_a_country_from_one_more_than_it_had(self):
        start = _norm(_block(_code(EFFECTS), "te_ai_build_pass_track_start"))
        self.assertIn("NOT = { has_global_variable = te_ai_build_pass_checked } "
                      "NOT = { has_variable = te_ai_build_pass_track_kind }", start)
        self.assertIn("set_variable = { name = te_ai_build_pass_track_target value = "
                      "te_ai_build_pass_tracked_levels_after } change_variable = { name = "
                      "te_ai_build_pass_track_target add = 1 }", start)
        for counter in ("built", "waiting", "lost", "resolved"):
            self.assertIn(f"set_global_variable = {{ name = te_ai_build_pass_{counter} value = 0 }}", start)

    def test_after_18_months_built_waiting_or_lost(self):
        tick = _norm(_block(_code(EFFECTS), "te_ai_build_pass_track_tick"))
        self.assertIn("var:te_ai_build_pass_track_months >= 18", tick)
        built = tick.index("te_ai_build_pass_tracked_levels >= var:te_ai_build_pass_track_target")
        waiting = tick.index("te_ai_build_pass_tracked_levels_after >= var:te_ai_build_pass_track_target")
        self.assertLess(built, tick.index("te_ai_build_pass_built add = 1"))
        self.assertLess(built, waiting)
        self.assertLess(waiting, tick.index("te_ai_build_pass_waiting add = 1"))
        self.assertLess(tick.index("te_ai_build_pass_waiting add = 1"), tick.index("te_ai_build_pass_lost add = 1"))
        self.assertEqual(tick.count("te_ai_build_pass_resolved add = 1"), 1)
        for name in ("kind", "target", "months"):
            self.assertIn(f"remove_variable = te_ai_build_pass_track_{name}", tick)

    def test_each_building_is_counted_by_its_own_kind(self):
        values = _code(VALUES)
        for name, field in (("te_ai_build_pass_tracked_levels", "level"),
                            ("te_ai_build_pass_tracked_levels_after", "level_after_queued_constructions")):
            body = _norm(_block(values, name))
            with self.subTest(value=name):
                self.assertEqual(body, f"value = 0 if = {{ limit = {{ var:te_ai_build_pass_track_kind = 1 }} "
                                       f"every_scope_building = {{ limit = {{ is_building_type = building_university }} "
                                       f"add = {field} }} }} else = {{ every_scope_building = {{ limit = {{ "
                                       f"is_building_type = building_government_administration }} add = {field} }} }}")
        effect = _code(EFFECTS)
        self.assertIn("te_ai_build_pass_track_start = { KIND = 1 }", effect)
        self.assertIn("te_ai_build_pass_track_start = { KIND = 2 }", effect)
        self.assertLess(effect.index("KIND = 1"), effect.index("start_building_construction = building_university"))

    def test_the_verdict_once_at_twelve_with_its_thresholds(self):
        check = _norm(_block(_code(ON_ACTIONS), "te_ai_build_pass_selfcheck"))
        self.assertIn("trigger = { NOT = { has_global_variable = te_ai_build_pass_checked } has_global_variable = "
                      "te_ai_build_pass_resolved global_var:te_ai_build_pass_resolved >= 12 }", check)
        effect = check[check.index("effect = {"):]
        self.assertTrue(effect.startswith("effect = { set_global_variable = te_ai_build_pass_checked debug_log = "
                                          "\"TE_SELF_CHECK START ai_build_pass"))
        self.assertLess(effect.index("START"), effect.index("random_country"))
        ok, broken = effect.index("te_ai_build_pass_lost_share <= 0.25"), effect.index("te_ai_build_pass_lost_share >= 0.5")
        self.assertLess(ok, effect.index("TE_SELF_CHECK OK ai_build_pass"))
        self.assertLess(ok, broken)
        self.assertLess(broken, effect.index("TE_SELF_CHECK BROKEN ai_build_pass"))
        self.assertLess(effect.index("TE_SELF_CHECK BROKEN"), effect.index("TE_SELF_CHECK NO_VERDICT ai_build_pass"))

    def test_its_lines_fit_log_triage(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]+)"', ON_ACTIONS.read_text(encoding="utf-8-sig"))
        self.assertEqual(len(lines), 4)
        for line in lines:
            printed = re.sub(r"\[SCOPE\.ScriptValue\('[a-z_]+'\)\|0\]", "999", line)
            printed = printed.replace("[TimeKeeper.GetCurrentDate.GetString]", "September 30, 1947")
            with self.subTest(line=line[:60]):
                self.assertLess(len(printed), 400)

    def test_the_reserve_gates_watch_leaves_out_what_the_pass_queued(self):
        # The pass's mark lasts 45 days, past the watch's month.
        self.assertIn("NOT = { has_variable = te_ai_build_pass_recent }", _norm(_code(GATE_CHECK)))
        self.assertIn("name = te_ai_build_pass_recent value = yes days = 45", _norm(_code(EFFECTS)))

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
