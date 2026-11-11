"""The mod's extra diplomatic-play escalation runs only on the days the play escalates (owner, 2026-11-11).

Vanilla pauses a play's escalation for some days after each demand or sway, and the mod's weekly add used to run
straight through the pause. Script can't read the pause, but the engine adds a point on each unpaused day, so the
play's own rise since the last tick (net of what the mod added then) counts the days it escalated:
common/scripted_effects/dp_escalation_effects.txt. These tests pin that shape; whether a play keeps a variable and
whether the `escalation` comparator reads in a script value are the self-check dp_esc_pause's
(docs/testing/diplomatic-play-escalation-playtest.md).
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = "common/scripted_effects/dp_escalation_effects.txt"
VALUES = "common/script_values/dp_escalation_script_values.txt"
PLAYTEST = "docs/testing/diplomatic-play-escalation-playtest.md"


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def code(rel):
    return re.sub(r"#[^\n]*", "", read(rel))


def block(text, key):
    m = re.search(r"^" + re.escape(key) + r"\s*=\s*\{", text, re.M)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def squash(text):
    return " ".join(text.split())


class TickTest(unittest.TestCase):
    def setUp(self):
        self.text = code(EFFECTS)
        self.country = squash(block(self.text, "st_dp_country_apply_weekly_escalation"))
        self.play = squash(block(self.text, "st_dp_play_apply_weekly_escalation"))

    def test_one_tick_per_play_its_initiator_s(self):
        # a second tick in the week would split the play's unpaused days between two marks
        self.assertEqual(self.country,
                         "if = { limit = { is_diplomatic_play_initiator = yes } save_temporary_scope_as = mover "
                         "every_diplomatic_play = { limit = { initiator_is = scope:mover is_war = no } "
                         "st_dp_play_apply_weekly_escalation = yes } }")

    def test_every_role_counts_at_that_tick(self):
        self.assertIn("set_local_variable = { name = te_dp_week value = "
                      "scope:mover.country_aggressor_dp_escalation_weekly_total }", self.play)
        self.assertIn("limit = { scope:te_dp_play = { target_is = scope:te_dp_member } } "
                      "change_local_variable = { name = te_dp_week add = country_defender_dp_escalation_weekly_total }",
                      self.play)
        self.assertIn("limit = { is_diplomatic_play_committed_participant = yes } "
                      "change_local_variable = { name = te_dp_week add = country_participant_dp_escalation_weekly_total }",
                      self.play)

    def test_the_days_are_the_engine_s_rise_since_the_mark(self):
        self.assertIn("set_local_variable = { name = te_dp_now value = te_dp_escalation_now }", self.play)
        self.assertIn("value = { value = local_var:te_dp_now subtract = var:te_dp_esc_mark min = 0 max = 10 }",
                      self.play)
        # a first tick reads the days since the play began, a week at most
        self.assertIn("else = { set_local_variable = { name = te_dp_days value = { value = local_var:te_dp_now "
                      "max = 7 } } }", self.play)
        # the self-check's fallback: the flat weekly add of before
        self.assertIn("limit = { has_global_variable = te_dp_esc_flat } "
                      "set_local_variable = { name = te_dp_days value = 7 }", self.play)

    def test_the_add_is_the_week_s_share_with_a_carry(self):
        self.assertIn("value = { value = local_var:te_dp_week multiply = local_var:te_dp_days divide = 7 }", self.play)
        self.assertIn("change_local_variable = { name = te_dp_add add = var:te_dp_esc_carry }", self.play)
        self.assertIn("value = { value = local_var:te_dp_add floor = yes }", self.play)
        self.assertIn("while = { count = local_var:te_dp_whole add_escalation = 1 }", self.play)
        # the literal form vanilla uses, never a computed add_escalation
        self.assertEqual(set(re.findall(r"add_escalation\s*=\s*(\S+)", self.text)), {"1"})

    def test_the_mark_is_set_from_the_reading_not_read_again(self):
        mark = self.play[self.play.index("name = te_dp_esc_mark"):]
        self.assertIn("value = { value = local_var:te_dp_now add = local_var:te_dp_whole max = 100 }", mark)
        self.assertLess(self.play.index("while ="), self.play.index("name = te_dp_esc_mark"))

    def test_the_ladder_counts_every_point(self):
        ladder = squash(block(code(VALUES), "te_dp_escalation_now"))
        found = [int(n) for n in re.findall(r"if = \{ limit = \{ escalation >= (\d+) \} add = 1 \}", ladder)]
        self.assertEqual(found, list(range(1, 101)))
        self.assertTrue(ladder.startswith("value = 0 "))


class ArithmeticTest(unittest.TestCase):
    """The tick's arithmetic, replayed: a week's extra spread over the days the engine escalated."""

    @staticmethod
    def run_ticks(week, engine_days, start=0):
        """engine_days: the days unpaused between ticks. Returns the mod's adds."""
        esc, mark, carry, adds = start, None, 0.0, []
        for k in engine_days:
            esc = min(100, esc + k)
            days = min(esc, 7) if mark is None else max(0, min(10, esc - mark))
            add = week * days / 7 + carry
            whole = int(add // 1)
            carry = add - whole
            esc = min(100, esc + whole)
            mark = esc
            adds.append(whole)
        return adds

    def test_a_paused_week_adds_nothing(self):
        self.assertEqual(self.run_ticks(7, [7, 0, 7]), [7, 0, 7])

    def test_a_part_paused_week_adds_its_share(self):
        # three paused days of seven: four-sevenths of the week's 7
        self.assertEqual(self.run_ticks(7, [7, 4]), [7, 4])
        # a fraction is carried, not lost
        self.assertEqual(sum(self.run_ticks(3, [7, 3, 3, 1])), 6)

    def test_the_mod_s_own_add_isn_t_read_as_days(self):
        self.assertEqual(self.run_ticks(10, [7, 7, 7, 7]), [10, 10, 10, 10])


class DocsTest(unittest.TestCase):
    def test_the_self_check_is_on_the_play_test_list(self):
        check = squash(block(code(EFFECTS), "te_dp_esc_pause_self_check"))
        for line in ("TE_SELF_CHECK OK dp_esc_pause", "TE_SELF_CHECK BROKEN dp_esc_pause ladder",
                     "TE_SELF_CHECK BROKEN dp_esc_pause mark", "set_global_variable = te_dp_esc_flat"):
            self.assertIn(line, check)
        self.assertIn("dp_esc_pause", read(PLAYTEST))
        self.assertIn("te_dp_esc_pause_self_check = yes", squash(block(code(EFFECTS),
                                                                         "st_dp_play_apply_weekly_escalation")))


if __name__ == "__main__":
    unittest.main()
