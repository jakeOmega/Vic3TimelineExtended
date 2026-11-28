"""Private Actors, the petition for a law or a tariff and the tariffs (docs/systems/mod_systems/private_actors.md
§ Politics at Home; plan Task 5b).

What is pinned here:

- kind law (3) is on the frame with every piece test_private_actors_moves.KindTest asks of a kind, its end event in
  the politics events file, and its ledger lines for every ask;
- every goal that can petition maps to a law or a tariff: te_pa_pt_can_ask's goals are te_pa_pt_pick's, and each
  ask writes its law, or its good and level;
- the broken-pledge check runs once a pledge: te_pa_pledge_break drops the pledge before it pays the refusal, and is
  reached only through te_pa_pledge_monthly's walk of the firms that hold one;
- the tariffs are read (the generated readings feed Cheaper Inputs, A Protected Market and A Friendly Law, whose +10
  stand-in is gone), set only behind te_pa_tariffs_settable, which defers to the Tax Code's customs option, and set
  the way the customs sync sets one;
- the record closes in every answer, the teardown and the clear take the petition and the pledges, and the two
  self-checks have their play-test rows.

The generated readings themselves (one a good a sector reads) are test_gen_private_actors.py's TariffTest.

Run: .venv/bin/python -m pytest test_private_actors_petition.py -q
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
POLITICS_EFFECTS = "common/scripted_effects/te_pa_politics_effects.txt"
POLITICS_TRIGGERS = "common/scripted_triggers/te_pa_politics_triggers.txt"
POLITICS_VALUES = "common/script_values/te_pa_politics_values.txt"
GOALS_VALUES = "common/script_values/te_pa_goals_values.txt"
MOVES_EFFECTS = "common/scripted_effects/te_pa_moves_effects.txt"
MOVES_VALUES = "common/script_values/te_pa_moves_values.txt"
CUSTOM_LOC = "common/customizable_localization/te_pa_custom_loc.txt"
EVENTS = "events/te_pa_politics_events.txt"
PLAYTEST = "docs/testing/private-actors-playtest.md"


def text(rel) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def parse(rel) -> dict:
    p = ParadoxFileParser()
    return p.parse_object(p.tokenize("{" + text(rel) + "}"))[0]


def items(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (_op, value) in part.items():
                yield key, value


def walk(node):
    for key, value in items(node):
        yield key, value
        if isinstance(value, (dict, list)):
            yield from walk(value)


def block(rel: str, name: str) -> str:
    """The text of a top-level block, for order checks."""
    body = text(rel)
    start = body.index(f"\n{name} = {{")
    end = body.index("\n}", start)
    return body[start:end]


def te_pa(folder: str) -> dict:
    out = {}
    for path in sorted((ROOT / folder).glob("te_pa_*.txt")):
        out.update(parse(path.relative_to(ROOT)))
    return out


class KindTest(unittest.TestCase):
    def test_kind_law_is_code_3(self):
        self.assertRegex(text(MOVES_VALUES), r"(?m)^te_pa_move_code_law = 3$")
        self.assertRegex(block(MOVES_EFFECTS, "te_pa_move_end"),
                         r"var:te_pa_move_kind \?= 3 \}\s*te_pa_move_close = \{ KIND = law EVENT = te_pa\.4 \}")

    def test_the_end_event_checks_the_rule_and_names_the_sides(self):
        event = dict(items(parse(EVENTS)["te_pa.4"][1]))
        self.assertEqual(dict(items(event["trigger"])).get("te_pa_on"), "yes")
        self.assertIn("te_pa_pt_save_sides", dict(items(event["immediate"])))
        options = [v for k, v in items(parse(EVENTS)["te_pa.4"][1]) if k == "option"]
        with_sides = [o for o in options if "te_pa_pt_sides_tt" in dict(items(o))]
        self.assertEqual(len(with_sides), 2, "Take it up and Refuse show who stood for and against it")

    def test_every_ask_has_its_four_ledger_lines(self):
        custom = parse(CUSTOM_LOC)
        lines = set()
        for k, v in items(custom["te_pa_ledger_move"][1]):
            if k == "text":
                trig = dict(items(dict(items(v)).get("trigger", {})))
                lines.add((trig.get("var:te_pa_l_verb"), trig.get("var:te_pa_l_kind"), trig.get("var:te_pa_l_ask")))
        for verb in ("30", "31", "32", "33"):
            for ask in ("1", "2", "3", "4", None):
                with self.subTest(verb=verb, ask=ask):
                    self.assertIn((verb, "3", ask), lines)

    def test_the_frame_copies_the_ask_onto_each_entry(self):
        log = block(MOVES_EFFECTS, "te_pa_move_log_from")
        self.assertIn("te_pa_move_note_ask = yes", log)
        note = block(MOVES_EFFECTS, "te_pa_move_note_ask")
        for var in ("ask", "law", "good", "level"):
            self.assertIn(f"name = te_pa_l_{var} value = scope:te_pa_mv_ask_firm.var:te_pa_move_{var}", note)
        # an ask left from a nomination that lost goes at the firm's next turn, unless its move is under way
        turn = block(POLITICS_EFFECTS, "te_pa_politics_turn")
        self.assertIn("te_pa_move_ask_clear = yes", turn)
        self.assertIn("te_pa_is_move_firm = no", turn)
        self.assertIn("var:te_pa_move_firm = scope:te_pa_firm", block(POLITICS_TRIGGERS, "te_pa_is_move_firm"))


class AskTest(unittest.TestCase):
    """Every goal that can petition maps to a law or a tariff (§ 8.4)."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = parse(POLITICS_TRIGGERS)
        cls.effects = parse(POLITICS_EFFECTS)

    def test_the_goals_that_ask_and_what_each_asks_for(self):
        can_ask = block(POLITICS_TRIGGERS, "te_pa_pt_can_ask")
        goals = {int(g) for g in re.findall(r"var:te_pa_goal \?= (\d)", can_ask)}
        self.assertEqual(goals, {1, 2, 4})
        pick = block(POLITICS_EFFECTS, "te_pa_pt_pick")
        branches = re.findall(r"var:te_pa_goal \?= (\d)\s*(te_pa_pt_ask_\w+) = yes\s*\}\s*"
                              r"set_variable = \{ name = te_pa_move_ask value = (\d) \}", pick)
        self.assertEqual({(int(g), ask, int(code)) for g, ask, code in branches}, {
            (1, "te_pa_pt_ask_input_tariff", 3), (1, "te_pa_pt_ask_antitrust", 4),
            (2, "te_pa_pt_ask_output_tariff", 2), (4, "te_pa_pt_ask_law", 1)})
        # each ask the trigger allows is one the pick writes
        for _g, ask, _c in branches:
            self.assertIn(f"{ask} = yes", can_ask)
        # Labor peace's labor law is Task 6's, with its branch marked in both
        self.assertIn("Task 6", can_ask)
        self.assertIn("Task 6", pick)

    def test_each_ask_writes_its_law_or_its_good_and_level(self):
        pick = block(POLITICS_EFFECTS, "te_pa_pt_pick")
        parts = re.split(r"name = te_pa_move_ask value = ", pick)[1:]
        writes = {}
        for part in parts:
            code = int(part[0])
            writes[code] = set(re.findall(r"name = te_pa_move_(law|good|level) ", part.split("else_if")[0]))
        self.assertEqual(writes[1], {"law"})
        self.assertEqual(writes[4], {"law"})
        self.assertEqual(writes[2], {"good", "level"})
        self.assertEqual(writes[3], {"good", "level"})
        self.assertIn("te_pa_gen_law_index_law_trust_busting", pick)

    def test_the_petition_needs_70_and_40_connections(self):
        values = parse(POLITICS_VALUES)
        self.assertEqual(float(values["te_pa_pt_score"][1]), 70)
        self.assertEqual(float(values["te_pa_pt_conn"][1]), 40)
        can = block(POLITICS_TRIGGERS, "te_pa_can_declare_law")
        self.assertTrue(can.split("{", 1)[1].strip().startswith("te_pa_move_open = yes"))
        for line in ("te_pa_goal_score_value >= te_pa_pt_score", "te_pa_v_conn >= te_pa_pt_conn",
                     "NOT = { has_variable = te_pa_pl_kind }", "te_pa_wait_over = { VAR = te_pa_law_again }"):
            self.assertIn(line, can)

    def test_the_declaring_verb_sits_in_the_goals_that_ask(self):
        effects = te_pa("common/scripted_effects")
        for name in ("te_pa_act_inputs", "te_pa_act_market", "te_pa_act_law"):
            with self.subTest(list=name):
                calls = [k for k, _ in walk(effects[name][1])]
                self.assertIn("te_pa_do_declare_law", calls)


class PledgeTest(unittest.TestCase):
    def test_a_broken_pledge_is_dropped_before_it_is_paid(self):
        body = block(POLITICS_EFFECTS, "te_pa_pledge_break")
        drop = body.index("te_pa_pledge_drop = yes")
        for later in ("name = te_pa_griev add = 1", "te_pa_conn_after_pt_refuse", "te_pa_pledge_line"):
            self.assertLess(drop, body.index(later), later)
        self.assertIn("te_pa_drop = { VAR = te_pa_pl_kind }", block(POLITICS_EFFECTS, "te_pa_pledge_drop"))

    def test_the_check_runs_once_a_pledge_from_one_walk(self):
        effects = te_pa("common/scripted_effects")
        callers = {name for name, (_op, body) in effects.items()
                   if any(k == "te_pa_pledge_break" for k, _ in walk(body))}
        self.assertEqual(callers, {"te_pa_pledge_law_monthly", "te_pa_pledge_tariff_monthly"})
        monthly = block(POLITICS_EFFECTS, "te_pa_politics_monthly")
        self.assertRegex(monthly, r"limit = \{ has_variable = te_pa_pl_kind \}\s*te_pa_pledge_monthly = yes")
        # one branch a month: the law's and the tariff's checks are if / else_if chains, so a month breaks a
        # pledge at most once, and the drop removes the kind the walk needs
        for name in ("te_pa_pledge_law_monthly", "te_pa_pledge_tariff_monthly"):
            body = block(POLITICS_EFFECTS, name)
            self.assertEqual(body.count("te_pa_pledge_break"), 1, name)

    def test_the_pledge_terms(self):
        values = parse(POLITICS_VALUES)
        self.assertEqual(float(values["te_pa_pl_law_months"][1]), 24)
        self.assertEqual(float(values["te_pa_pl_tariff_months"][1]), 60)
        self.assertEqual(float(values["te_pa_pt_refuse_conn"][1]), 10)
        self.assertEqual(float(values["te_pa_pt_other_conn"][1]), 5)
        # an AI government enacting nothing starts the pledged law from script, and arms probe 13
        start = block(POLITICS_EFFECTS, "te_pa_pledge_start")
        self.assertLess(start.index("te_pa_debug_enact_arm"), start.index("te_pa_gen_law_start"))
        take = block(POLITICS_EFFECTS, "te_pa_pt_take_law")
        self.assertIn("is_ai = yes", take)
        self.assertIn("NOT = { enacting_any_law = yes }", take)

    def test_the_free_speed_keeps_its_own_count(self):
        speed = block(POLITICS_EFFECTS, "te_pa_pledge_speed")
        self.assertIn("add_law_progress = te_pa_speed_progress", speed)
        self.assertIn("te_pa_pl_speed_month", speed)
        for limit in ("te_pa_speed_month", "te_pa_speed_law_month", "te_pa_conn"):
            self.assertNotRegex(speed, rf"name = {limit} ")

    def test_every_answer_closes_the_record(self):
        for shape in ("grant", "stand", "refuse"):
            body = block(POLITICS_EFFECTS, f"te_pa_answer_law_{shape}")
            with self.subTest(shape=shape):
                self.assertIn("hidden_effect = { scope:te_pa_home = { te_pa_pt_close = yes } }", body)
                self.assertNotIn("te_pa_griev", body)  # the frame's refusal gives Grievance
        refuse = block(POLITICS_EFFECTS, "te_pa_answer_law_refuse")
        self.assertIn("te_pa_conn_after_pt_refuse", refuse)
        self.assertIn("te_pa_conn_after_pt_other", refuse)


class TariffTest(unittest.TestCase):
    def test_the_pressures_read_the_tariffs(self):
        inputs = block(GOALS_VALUES, "te_pa_p_inputs_value")
        self.assertIn("add = te_pa_p_inputs_tariff", inputs)
        market = block(GOALS_VALUES, "te_pa_p_market_value")
        self.assertIn("add = te_pa_p_market_tariff", market)
        self.assertIn("te_pa_v_out_tariff <= 0", block(GOALS_VALUES, "te_pa_p_market_tariff"))
        # Task 2's +10 for any imported output is replaced by the stance on the tariffs in force
        want = block(GOALS_VALUES, "te_pa_p_law_tariff_want")
        self.assertIn("te_pa_v_out_tariff <= 0", want)
        self.assertIn("te_pa_tariff_on_inputs", want)
        self.assertIn("max = te_pa_p_law_tariff_max", want)
        for reader in ("te_pa_v_in1_tariff", "te_pa_v_in2_tariff", "te_pa_v_out_tariff"):
            body = block(GOALS_VALUES, reader)
            self.assertIn("te_pa_tariffs_bite = yes", body, reader)

    def test_the_stake_reads_the_tariffs_not_the_trade_policy(self):
        pick = block(POLITICS_EFFECTS, "te_pa_stake_pick")
        first, second = pick.split("else_if", 2)[:2]
        self.assertIn("te_pa_tariff_on_inputs > 0", first)
        self.assertIn("te_pa_v_out_tariff <= 0", second)
        self.assertNotIn("te_pa_trade_protective", first + second)

    def test_a_tariff_is_set_in_one_place_behind_the_customs_option(self):
        sets = []
        for path in sorted((ROOT / "common").rglob("te_pa_*.txt")):
            body = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            if re.search(r"\bset_(?:import|export)_tariff_level\b", body):
                sets.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(sets, [POLITICS_EFFECTS])
        setter = block(POLITICS_EFFECTS, "te_pa_tariff_set_good")
        self.assertEqual(len(re.findall(r"set_import_tariff_level = \{ goods = g:\$GOOD\$ level = \w+ \}", setter)), 4)
        code = re.sub(r"#[^\n]*", "", text(POLITICS_EFFECTS))
        self.assertEqual(code.count("set_import_tariff_level"), 4, "te_pa_tariff_set_good's four levels, nowhere else")
        settable = block(POLITICS_TRIGGERS, "te_pa_tariffs_settable")
        self.assertIn("NOT = { te_tax_customs_on = yes }", settable)
        self.assertIn("te_tax_owns_market = yes", settable)
        # each caller of the generated set is behind it
        self.assertIn("te_pa_tariffs_settable = yes", block(POLITICS_TRIGGERS, "te_pa_pt_tariff_takeable"))
        self.assertIn("te_pa_tariffs_settable = yes", block(POLITICS_TRIGGERS, "te_pa_pl_tariff_reassert"))
        take = block(POLITICS_EFFECTS, "te_pa_pt_take_tariff")
        self.assertLess(take.index("te_pa_pt_tariff_takeable = yes"), take.index("te_pa_gen_tariff_set"))
        monthly = block(POLITICS_EFFECTS, "te_pa_pledge_tariff_monthly")
        self.assertLess(monthly.index("te_pa_tariffs_settable = no"), monthly.index("te_pa_pl_tariff_reassert"))
        self.assertLess(monthly.index("te_pa_pl_tariff_reassert = yes"), monthly.index("te_pa_gen_tariff_set"))


class SelfCheckTest(unittest.TestCase):
    def test_the_two_probes_have_their_lines_and_rows(self):
        debug = text("common/scripted_effects/te_pa_debug_effects.txt")
        playtest = text(PLAYTEST)
        for name in ("ai_keeps_enactment", "tariff_from_script"):
            with self.subTest(check=name):
                self.assertIn(f"TE_SELF_CHECK OK {name}", debug)
                self.assertIn(f"TE_SELF_CHECK BROKEN {name}", debug)
                self.assertIn(f"| `{name}`", playtest)
        # probe 14's read comes before any pledge's re-assert in the month
        monthly = block(POLITICS_EFFECTS, "te_pa_politics_monthly")
        self.assertLess(monthly.index("te_pa_debug_tariff_read"), monthly.index("te_pa_pledge_monthly"))

    def test_task_5bs_codes_have_their_lines(self):
        custom = text(CUSTOM_LOC)
        for code in range(50, 58):
            with self.subTest(code=code):
                self.assertIn(f"var:te_pa_l_verb ?= {code} }}", custom)
        self.assertIn("te_pa_ai_lean_law", parse(POLITICS_VALUES))
        self.assertIn("te_pa_ai_why_law", parse(POLITICS_VALUES))


if __name__ == "__main__":
    unittest.main()
