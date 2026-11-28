"""Private Actors, declared moves and the state's actions (docs/systems/mod_systems/private_actors.md § Declared Moves
and § The State's Actions; plan Task 4b).

What is pinned here:

- the frame: one move at a time and the twelve-month gap (te_pa_move_slot_open, which every kind's
  te_pa_can_declare_<kind> opens with), six months' countdown, and the clear before the fire: in every end path the
  move's variables (or the case's mark) go before any trigger_event or AI answer (plan Review Focus 3);
- every kind of petition (a te_pa_move_code_<token>) has its trigger, its declaring effect in a goal's list, its three
  answers, a branch in te_pa_move_end naming an end event with the four options (the posture's default the default
  option), an AI weight block, and its ledger, row and notice lines; the posture's default covers all three postures,
  and only a refusal raises Grievance;
- every state action's scripted GUI has an is_valid and a cost (Lift the Levy excepted), and a button in the tab;
- the alerts' valid blocks read the rule and country variables only, and walk no list;
- the teardown reaches the move's clear and the actions' modifiers; the ledger codes sit in Task 4b's block, 30-39.

Run: .venv/bin/python -m pytest test_private_actors_moves.py -q
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
MOVES_EFFECTS = "common/scripted_effects/te_pa_moves_effects.txt"
ACTIONS_EFFECTS = "common/scripted_effects/te_pa_actions_effects.txt"
MOVES_VALUES = "common/script_values/te_pa_moves_values.txt"
ALERTS = "common/alert_types/te_pa_alerts.txt"
SGUIS = "common/scripted_guis/te_pa_sguis.txt"
CUSTOM_LOC = "common/customizable_localization/te_pa_custom_loc.txt"
EVENTS = "events/te_pa_trust_events.txt"
# Every file of the namespace: a kind's end event sits in its chain's file (Task 5b's te_pa.4 in the politics events).
EVENT_FILES = ("events/te_pa_trust_events.txt", "events/te_pa_politics_events.txt")
WIDGETS = "gui/te_pa_widgets.gui"


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


def te_pa(folder: str) -> dict:
    out = {}
    for path in sorted((ROOT / folder).glob("te_pa_*.txt")):
        out.update(parse(path.relative_to(ROOT)))
    return out


def block(rel: str, name: str) -> str:
    """The text of a top-level block, for order checks."""
    body = text(rel)
    start = body.index(f"\n{name} = {{")
    end = body.index("\n}", start)
    return body[start:end]


def kinds() -> dict[str, int]:
    return {m.group(1): int(m.group(2))
            for m in re.finditer(r"^te_pa_move_code_(\w+) = (\d+)$", text(MOVES_VALUES), re.M)}


class FrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = parse(MOVES_VALUES)
        cls.triggers = te_pa("common/scripted_triggers")
        cls.effects = te_pa("common/scripted_effects")

    def test_six_months_and_a_twelve_month_gap(self):
        self.assertEqual(self.values["te_pa_move_countdown"][1], "6")
        self.assertEqual(self.values["te_pa_move_gap"][1], "12")
        self.assertIn("set_variable = { name = te_pa_move_months value = te_pa_move_countdown }",
                      block(MOVES_EFFECTS, "te_pa_move_declare"))
        self.assertIn("set_variable = { name = te_pa_move_last value = te_history_month_index }",
                      block(MOVES_EFFECTS, "te_pa_move_clear"))

    def test_one_move_at_a_time(self):
        slot = dict(items(self.triggers["te_pa_move_slot_open"][1]))
        self.assertEqual(dict(items(slot["NOT"])), {"has_variable": "te_pa_move_firm"})
        self.assertIn(("te_pa_move_since", ">=", "te_pa_move_gap"),
                      [(k, op, v) for k, (op, v) in self.triggers["te_pa_move_slot_open"][1].items()])
        # The settlement declares only into an open slot.
        self.assertIn("te_pa_move_slot_open = yes", block(MOVES_EFFECTS, "te_pa_move_settle"))

    def test_every_kind_opens_with_the_slot(self):
        for token in kinds():
            with self.subTest(kind=token):
                first = next(items(self.triggers[f"te_pa_can_declare_{token}"][1]))
                self.assertEqual(first, ("te_pa_move_open", "yes"))

    def test_the_higher_goal_score_goes_first(self):
        nominate = block(MOVES_EFFECTS, "te_pa_move_nominate")
        self.assertIn("te_pa_v_move_cand_score < scope:te_pa_nom_firm.var:te_pa_move_nom_score", nominate)
        # Turns, then the countdown, then the month's settlement.
        monthly = block("common/scripted_effects/te_pa_core_effects.txt", "te_pa_monthly")
        self.assertLess(monthly.index("te_pa_turn = yes"), monthly.index("te_pa_move_monthly = yes"))
        self.assertLess(monthly.index("te_pa_move_monthly = yes"), monthly.index("te_pa_move_settle = yes"))

    def test_the_move_is_cleared_before_its_event_fires(self):
        close = block(MOVES_EFFECTS, "te_pa_move_close")
        cleared = close.index("te_pa_move_clear = yes")
        self.assertLess(cleared, close.index("trigger_event"))
        self.assertLess(cleared, close.index("te_pa_move_ai_answer"))
        end = block(MOVES_EFFECTS, "te_pa_move_end")
        self.assertNotIn("trigger_event", end)
        self.assertIn("te_pa_move_close", end)

    def test_every_trigger_event_in_the_system_follows_its_clear(self):
        # Each effect that fires an event closes what the event reads first (the move's variables, the case's mark).
        clears = {
            "te_pa_move_close": "te_pa_move_clear = yes",
            "te_pa_case_verdict": "remove_variable = te_pa_case_end",
        }
        fired = set()
        for rel in sorted((ROOT / "common/scripted_effects").glob("te_pa_*.txt")):
            for name, (_op, body) in parse(rel.relative_to(ROOT)).items():
                if any(k == "trigger_event" for k, _ in walk(body)):
                    fired.add(name)
                    self.assertIn(name, clears, f"{name} fires an event: pin what it clears first")
                    whole = block(str(rel.relative_to(ROOT)), name)
                    self.assertLess(whole.index(clears[name]), whole.index("trigger_event"), name)
        self.assertEqual(fired, set(clears))

    def test_the_posture_default_covers_every_posture(self):
        default = block(MOVES_EFFECTS, "te_pa_move_default")
        self.assertRegex(default, r"var:te_pa_posture \?= 1 \}\s*te_pa_move_grant")
        self.assertRegex(default, r"var:te_pa_posture \?= -1 \}\s*te_pa_move_refuse")
        self.assertRegex(default, r"else = \{\s*te_pa_move_stand")

    def test_only_a_refusal_raises_grievance(self):
        for name in ("te_pa_move_grant", "te_pa_move_stand", "te_pa_move_refuse"):
            raises = "name = te_pa_griev add = 1" in block(MOVES_EFFECTS, name)
            self.assertEqual(raises, name == "te_pa_move_refuse", name)
        for token in kinds():
            for shape in ("grant", "stand", "refuse"):
                name = f"te_pa_answer_{token}_{shape}"
                self.assertNotIn("te_pa_griev", block(KindTest._file_of(None, name), name))

    def test_a_major_move_is_never_secret(self):
        for rel in (MOVES_EFFECTS, ACTIONS_EFFECTS):
            self.assertNotIn("KNOWN = 0", text(rel))

    def test_the_player_setting_a_posture_marks_it_by_hand(self):
        cmd = block("common/scripted_effects/te_pa_core_effects.txt", "te_pa_cmd_set_posture")
        self.assertIn("set_variable = { name = te_pa_posture_hand value = 1 }", cmd)
        self.assertIn("set_variable = { name = te_pa_move_hand value = 1 }", cmd)


class KindTest(unittest.TestCase):
    """A later task adds a kind by its code and these pieces (te_pa_moves_effects.txt's header)."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = te_pa("common/scripted_triggers")
        cls.effects = te_pa("common/scripted_effects")
        cls.values = te_pa("common/script_values")
        cls.events = {}
        for rel in EVENT_FILES:
            cls.events.update(parse(rel))
        cls.custom = parse(CUSTOM_LOC)
        cls.end = block(MOVES_EFFECTS, "te_pa_move_end")

    def test_the_kinds_built_so_far(self):
        # Task 4b's two and Task 5b's petition for a law or a tariff (3); 4 relief and 5 protection are reserved
        self.assertEqual(kinds(), {"charter": 1, "suit": 2, "law": 3})

    def test_each_kind_has_its_pieces(self):
        for token, code in kinds().items():
            with self.subTest(kind=token):
                self.assertIn(f"te_pa_can_declare_{token}", self.triggers)
                self.assertIn(f"te_pa_do_declare_{token}", self.effects)
                for shape in ("grant", "stand", "refuse"):
                    self.assertIn(f"te_pa_answer_{token}_{shape}", self.effects)
                self.assertIn(f"te_pa_ai_lean_{token}", self.values)
                self.assertIn(f"te_pa_ai_why_{token}", self.values)
                self.assertIn(f"te_pa_move_nominate = {{ KIND = {token} }}",
                              block(self._file_of(f"te_pa_do_declare_{token}"), f"te_pa_do_declare_{token}"))

    def _file_of(self, name: str) -> str:
        for rel in sorted((ROOT / "common/scripted_effects").glob("te_pa_*.txt")):
            if f"\n{name} = {{" in rel.read_text(encoding="utf-8-sig"):
                return str(rel.relative_to(ROOT))
        raise AssertionError(name)

    def test_each_declaring_verb_is_in_a_goals_list(self):
        listed = set()
        for name, (_op, body) in self.effects.items():
            if name.startswith("te_pa_act_"):
                listed |= {k for k, _ in walk(body) if k.startswith("te_pa_do_declare_")}
        self.assertEqual(listed, {f"te_pa_do_declare_{t}" for t in kinds()})

    def test_each_kind_ends_in_its_event_with_the_four_answers(self):
        for token, code in kinds().items():
            with self.subTest(kind=token):
                m = re.search(r"var:te_pa_move_kind \?= %d \}\s*te_pa_move_close = \{ KIND = %s EVENT = (\S+) \}"
                              % (code, token), self.end)
                self.assertIsNotNone(m, "te_pa_move_end has no branch for the kind")
                event = self.events[m.group(1)][1]
                trigger = dict(items(dict(items(event))["trigger"]))
                self.assertEqual(trigger.get("te_pa_on"), "yes")
                options = [v for k, v in items(event) if k == "option"]
                self.assertEqual(len(options), 4)
                calls = [[k for k, _ in walk(o)] for o in options]
                for shape in ("te_pa_move_grant", "te_pa_move_stand", "te_pa_move_refuse", "te_pa_move_default"):
                    self.assertEqual(sum(shape in c for c in calls), 1, shape)
                defaults = [o for o in options if dict(items(o)).get("default_option") == "yes"]
                self.assertEqual(len(defaults), 1)
                self.assertIn("te_pa_move_default", [k for k, _ in walk(defaults[0])])
                self.assertNotIn("trigger", dict(items(defaults[0])))
                image = dict(items(event)).get("event_image")
                self.assertTrue(image, "a visible event needs its picture")

    def test_each_kind_has_its_lines(self):
        def keyed(key: str, var: str) -> set:
            out = set()
            for k, v in items(self.custom[key][1]):
                if k == "text":
                    trig = dict(items(dict(items(v)).get("trigger", {})))
                    out.add(trig.get(var))
            return out

        moves = []
        for k, v in items(self.custom["te_pa_ledger_move"][1]):
            if k == "text":
                trig = dict(items(dict(items(v)).get("trigger", {})))
                moves.append((trig.get("var:te_pa_l_verb"), trig.get("var:te_pa_l_kind")))
        for token, code in kinds().items():
            with self.subTest(kind=token):
                for verb in ("30", "31", "32", "33"):
                    self.assertIn((verb, str(code)), moves)
                self.assertIn(str(code), keyed("te_pa_row_move_kind", "var:te_pa_r_move_kind"))
                self.assertIn(str(code), keyed("te_pa_move_kind_now", "var:te_pa_move_kind"))

    def test_every_firm_type_has_its_charter(self):
        gen = block("common/scripted_effects/te_pa_gen_effects.txt", "te_pa_gen_charter_grant")
        types = re.findall(r"is_company_type = company_type:(\w+)", gen)
        grants = re.findall(r"add_company_monopoly = bt:(building_\w+)", gen)
        self.assertGreater(len(types), 300)
        self.assertEqual(len(types), len(grants))
        held = block("common/scripted_triggers/te_pa_gen_triggers.txt", "te_pa_gen_charter_held")
        self.assertEqual(re.findall(r"company_has_building_type_monopoly = bt:(building_\w+)", held), grants)

    def test_the_ai_answers_with_its_reason(self):
        answer = block(MOVES_EFFECTS, "te_pa_move_ai_answer")
        self.assertIn("te_pa_ai_lean_posture", answer)
        self.assertIn("te_pa_ai_lean_$KIND$", answer)
        why = block(MOVES_EFFECTS, "te_pa_move_ai_why")
        self.assertIn("te_pa_ai_why_$KIND$", why)
        # The reason reaches the ledger entry.
        self.assertIn("name = te_pa_l_why", block(MOVES_EFFECTS, "te_pa_move_log_from"))


class StateActionsTest(unittest.TestCase):
    ACTIONS = ("inquiry", "suit", "audit", "levy", "lift", "charter", "close_press")
    # Task 5a's Close the Press costs through te_pa_sa_close_press_cost (te_pa_sa_cost, or nothing for a Restrained
    # firm's press under Censorship)
    COSTS = ("te_pa_sa_cost", "te_pa_charter_cost", "te_pa_sa_close_press_cost")

    @classmethod
    def setUpClass(cls):
        cls.sguis = parse(SGUIS)
        cls.gui = text(WIDGETS)

    def test_every_action_has_a_scripted_gui_with_is_valid_and_its_cost(self):
        for action in self.ACTIONS:
            name = f"te_pa_sa_{action}_sgui"
            with self.subTest(action=action):
                body = dict(items(self.sguis[name][1]))
                self.assertIn("is_valid", body)
                self.assertEqual(dict(items(body["ai_is_valid"])), {"always": "no"})
                costs = [k for k, _ in walk(body["effect"]) if k in self.COSTS]
                if action == "lift":
                    self.assertEqual(costs, [], "lifting the levy costs nothing")
                else:
                    self.assertEqual(len(costs), 1, "an action's cost")
                self.assertIn("custom_tooltip", [k for k, _ in items(body["effect"])])
                self.assertIn(f"GetScriptedGui('{name}')", self.gui)

    def test_the_buttons_sit_under_the_own_country_guard(self):
        actions = self.gui[self.gui.index("type te_pa_actions = widget {"):]
        self.assertIn("using = te_own_country_only", actions[:200])
        self.assertIn("Not( GetMetaPlayer.IsObserver )", actions[:400])

    def test_the_costs_scale_with_standing_and_are_bounded(self):
        values = parse("common/script_values/te_pa_actions_values.txt")
        self.assertEqual(values["te_pa_sa_backers_max"][1], "4")
        self.assertLessEqual(float(values["te_pa_sa_radicals_max"][1]), 0.05)  # vanilla's medium_radicals
        share = dict(items(values["te_pa_sa_cost_share"][1]))
        self.assertEqual(share["value"], "te_pa_v_stand")
        self.assertEqual((share["min"], share["max"]), ("0", "1"))
        cost = block(ACTIONS_EFFECTS, "te_pa_sa_cost")
        self.assertIn("multiplier = te_pa_sa_backers_$SIZE$", cost)
        self.assertIn("add_loyalists_in_state", cost)  # a hated firm is popular to break

    def test_actions_on_a_holding_need_one_the_state_knows_of(self):
        triggers = te_pa("common/scripted_triggers")
        for name in ("te_pa_sa_suable", "te_pa_sa_can_levy", "te_pa_sa_can_charter"):
            keys = [k for k, _ in walk(triggers[name][1])]
            self.assertIn("te_pa_holds_known_cartel", keys, name)
            self.assertNotIn("te_pa_holds_cartel", keys, name)

    def test_the_inquiry_is_a_term_in_the_exposure_hook(self):
        hook = block("common/script_values/te_pa_trust_values.txt", "te_pa_expose_hook_value")
        self.assertIn("add = te_pa_inquiry_term", hook)

    def test_the_levy_moves_money_once(self):
        levy = block(ACTIONS_EFFECTS, "te_pa_levy_quarter")
        take, spend, pay = (levy.index("te_pa_levy_take value = te_pa_levy_take_value"),
                            levy.index("te_pa_spend_funds = { AMOUNT = te_pa_levy_quarter_value }"),
                            levy.index("add_treasury = var:te_pa_levy_take"))
        self.assertLess(take, spend)
        self.assertLess(spend, pay)

    def test_the_ai_acts_once_a_quarter(self):
        quarter = block("common/scripted_effects/te_pa_core_effects.txt", "te_pa_quarter")
        self.assertIn("te_pa_sa_ai_quarter = yes", quarter)
        ai = block(ACTIONS_EFFECTS, "te_pa_sa_ai_quarter")
        self.assertIn("is_ai = yes", ai)
        self.assertIn("te_pa_sa_ai_done", ai)


class AlertsTest(unittest.TestCase):
    LIST_KEYS = re.compile(r"^(?:any|every|ordered|random)_|_list$|^has_variable_list$|^is_target_in_variable_list$")

    def test_two_alerts_yellow_and_red(self):
        alerts = parse(ALERTS)
        self.assertEqual(set(alerts), {"te_pa_move_pending", "te_pa_move_due"})
        self.assertEqual(dict(items(alerts["te_pa_move_pending"][1]))["color"], "yellow")
        self.assertEqual(dict(items(alerts["te_pa_move_due"][1]))["color"], "red")

    def test_valid_reads_variables_only_and_walks_no_list(self):
        values = te_pa("common/script_values")
        for name, (_op, body) in parse(ALERTS).items():
            valid = dict(items(body))["valid"]
            with self.subTest(alert=name):
                first = next(items(valid))
                self.assertEqual(first, ("te_pa_on", "yes"))
                for key, _value in walk(valid):
                    self.assertIsNone(self.LIST_KEYS.search(key), key)
                    self.assertIn(key, {"te_pa_on", "has_variable", "OR", "var:te_pa_move_hand",
                                        "te_pa_v_move_months"}, key)
                reader = [k for k, _ in walk(values["te_pa_v_move_months"][1])]
                self.assertFalse([k for k in reader if self.LIST_KEYS.search(k)])

    def test_the_teardown_clears_the_alerts_condition(self):
        teardown = block(ACTIONS_EFFECTS, "te_pa_actions_teardown")
        self.assertIn("te_pa_move_clear = yes", teardown)
        self.assertIn("te_pa_actions_teardown = yes", block("common/scripted_effects/te_pa_core_effects.txt",
                                                             "te_pa_teardown"))
        clear = block(MOVES_EFFECTS, "te_pa_move_clear")
        for var in ("te_pa_move_firm", "te_pa_move_months", "te_pa_move_hand", "te_pa_move_kind"):
            self.assertIn(f"VAR = {var} }}", clear)

    def test_the_icons_are_listed_as_placeholders_to_paint(self):
        prompts = (ROOT / "scripts/image_pipeline/icon_prompts.py").read_text(encoding="utf-8")
        for name, (_op, body) in parse(ALERTS).items():
            texture = dict(items(body))["texture"].strip('"')
            with self.subTest(alert=name):
                self.assertIn(f'"now": f"{{_GI}}/{texture.removeprefix("gfx/interface/icons/")}"', prompts)


class LedgerTest(unittest.TestCase):
    def test_task_4bs_codes_sit_in_its_block(self):
        for rel in (MOVES_EFFECTS, ACTIONS_EFFECTS):
            verbs = {int(v) for v in re.findall(r"\bVERB = (\d+)", text(rel))}
            self.assertTrue(verbs)
            self.assertLessEqual(verbs, set(range(30, 40)), rel)

    def test_the_charter_self_check_has_its_row(self):
        playtest = (ROOT / "docs/testing/private-actors-playtest.md").read_text(encoding="utf-8")
        self.assertIn("| `charter_monopoly`", playtest)
        debug = text("common/scripted_effects/te_pa_debug_effects.txt")
        self.assertIn("TE_SELF_CHECK OK charter_monopoly", debug)
        self.assertIn("TE_SELF_CHECK BROKEN charter_monopoly", debug)


if __name__ == "__main__":
    unittest.main()
