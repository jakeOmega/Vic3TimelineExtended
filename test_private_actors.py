"""Private Actors, the chassis (docs/systems/mod_systems/private_actors.md; plan Task 2).

What is pinned here:

- each goal's pressure is clamped to 0-100 and each weight to 0.5-1.5, and Survival passes 80 only when prosperity is
  low and falling (spec § 5.2a);
- the score is pressure times weight, with the +15 for the goal held only while it has a pressure, and the goal held
  is weighed first so a tie keeps it (§ 4.2, § 5.2a);
- the game rule is read only through te_pa_on;
- every te_pa_r_ variable read anywhere (the tab, its loc) is one te_pa_row_sync writes;
- the teardown removes every static modifier the system applies (none yet; the test holds later tasks to it);
- every ledger verb and every reason code has its loc line.

Run: .venv/bin/python -m pytest test_private_actors.py -q
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
CORE = "common/scripted_effects/te_pa_core_effects.txt"
GOALS = "common/scripted_effects/te_pa_goals_effects.txt"
LEDGER = "common/scripted_effects/te_pa_ledger_effects.txt"
CORE_VALUES = "common/script_values/te_pa_core_values.txt"
GOAL_VALUES = "common/script_values/te_pa_goals_values.txt"
CUSTOM_LOC = "common/customizable_localization/te_pa_custom_loc.txt"
RULE_TRIGGERS = "common/scripted_triggers/te_pa_rule_triggers.txt"

GOAL_CODES = {"inputs": 1, "market": 2, "abroad": 3, "law": 4, "dominance": 5, "labor": 6, "tech": 7, "survival": 8}


def parse(rel: str) -> dict:
    p = ParadoxFileParser()
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    return p.parse_object(p.tokenize("{" + text + "}"))[0]


def items(node):
    """A block's (key, value) pairs in order: the parser gives a list of one-key dicts where a key repeats."""
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (_op, value) in part.items():
                yield key, value


def walk(node):
    for key, value in items(node):
        yield key, value
        if isinstance(value, (dict, list)):
            yield from walk(value)


def te_pa_files(*dirs: str, generated: bool = False) -> list[Path]:
    out = []
    for d in dirs:
        for path in sorted((ROOT / d).glob("te_pa_*.txt")):
            if generated or "_gen_" not in path.name:
                out.append(path)
    return out


def number(values: dict, name: str) -> float:
    return float(values[name][1])


class PressureAndWeightTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = parse(GOAL_VALUES)

    def test_the_scale_constants(self):
        self.assertEqual(number(self.values, "te_pa_pressure_max"), 100)
        self.assertEqual(number(self.values, "te_pa_weight_min"), 0.5)
        self.assertEqual(number(self.values, "te_pa_weight_max"), 1.5)

    def test_every_pressure_ends_clamped_to_0_100(self):
        for goal in GOAL_CODES:
            with self.subTest(goal=goal):
                ops = list(items(self.values[f"te_pa_p_{goal}_value"][1]))
                if goal == "abroad":
                    # Task 9 replaces it; until then it reads 0 and nothing else
                    self.assertEqual(ops, [("value", "0")])
                    continue
                self.assertEqual(ops[-2:], [("min", "0"), ("max", "te_pa_pressure_max")])

    def test_every_weight_ends_clamped_to_half_and_one_and_a_half(self):
        for goal in GOAL_CODES:
            with self.subTest(goal=goal):
                ops = list(items(self.values[f"te_pa_w_{goal}_value"][1]))
                self.assertEqual(ops[-2:], [("min", "te_pa_weight_min"), ("max", "te_pa_weight_max")])
                # each starts from 1: value = 1, or (Labor peace) the shift then add = 1
                self.assertTrue(ops[0] == ("value", "1") or ("add", "1") in ops, ops)

    def test_survival_passes_80_only_when_low_and_falling(self):
        v = self.values
        low = number(v, "te_pa_p_surv_low_line") * number(v, "te_pa_p_surv_low_per")
        others = number(v, "te_pa_p_surv_months_max") + number(v, "te_pa_p_surv_slump") + number(v, "te_pa_p_surv_law")
        self.assertLessEqual(low + others, 80, "without the fall the parts must stay at 80 or under")
        self.assertGreater(low + others + number(v, "te_pa_p_surv_falling"), 80)
        self.assertLessEqual(number(v, "te_pa_p_surv_falling") + others, 80, "a fall without low prosperity counts nothing")
        body = v["te_pa_p_survival_value"][1]
        ops = list(items(body))
        self.assertEqual(ops[0], ("value", "0"))
        # every addition sits inside the one branch for a firm that is not prosperous
        guarded = [val for key, val in ops if key == "if"]
        self.assertEqual(len(guarded), 1)
        limit = dict(items(guarded[0]))["limit"]
        self.assertIn(("company_is_prosperous", "no"), list(items(limit)))
        self.assertNotIn("add", [key for key, _ in ops])
        # the fall is counted only below the line
        inner = [val for key, val in items(guarded[0]) if key == "if"]
        falling = next(b for b in inner if ("add", "te_pa_p_surv_falling") in list(items(b)))
        conditions = list(items(dict(items(falling))["limit"]))
        self.assertIn("company_prosperity", [k for k, _ in conditions])
        self.assertIn("te_pa_prosperity_change", [k for k, _ in conditions])

    def test_dominance_reads_0_where_no_verb_serves_it(self):
        ops = list(items(self.values["te_pa_p_dominance_value"][1]))
        branch = next(val for key, val in ops if key == "if")
        self.assertIn(("value", "0"), list(items(branch)))
        self.assertIn("te_pa_dominance_illegal", str(dict(items(branch))["limit"]))
        illegal = parse("common/scripted_triggers/te_pa_core_triggers.txt")["te_pa_dominance_illegal"][1]
        text = str(illegal)
        self.assertIn("te_pa_private_ownership_ended", text)
        self.assertIn("law_type:law_command_cooperative_economy", text)
        ended = str(parse("common/scripted_triggers/te_pa_core_triggers.txt")["te_pa_private_ownership_ended"][1])
        self.assertIn("law_type:law_command_economy", ended)
        self.assertIn("law_type:law_cooperative_ownership", ended)


class ScoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = parse(GOALS)
        cls.core_values = parse(CORE_VALUES)

    def test_the_held_goal_bonus_is_15(self):
        self.assertEqual(number(self.core_values, "te_pa_goal_held_bonus"), 15)

    def test_score_is_pressure_times_weight_plus_the_bonus_for_the_goal_held(self):
        ops = list(items(self.effects["te_pa_score_one"][1]))
        sets = [dict(items(val)) for key, val in ops if key == "set_variable"]
        self.assertEqual([(s["name"], s["value"]) for s in sets], [
            ("te_pa_p_$G$", "te_pa_p_$G$_value"),
            ("te_pa_w_$G$", "te_pa_w_$G$_value"),
            ("te_pa_s_$G$", "var:te_pa_p_$G$"),
        ])
        changes = [dict(items(val)) for key, val in ops if key == "change_variable"]
        self.assertEqual(changes, [{"name": "te_pa_s_$G$", "multiply": "var:te_pa_w_$G$"}])
        bonus = next(val for key, val in ops if key == "if")
        limit = list(items(dict(items(bonus))["limit"]))
        self.assertIn(("var:te_pa_goal", "$CODE$"), limit)  # ?= : the goal held
        self.assertIn(("var:te_pa_p_$G$", "0"), limit)       # > 0 : a goal with no pressure gets no bonus
        self.assertEqual(dict(items(dict(items(bonus))["change_variable"])),
                         {"name": "te_pa_s_$G$", "add": "te_pa_goal_held_bonus"})
        text = (ROOT / GOALS).read_text(encoding="utf-8-sig")
        self.assertIn("var:te_pa_goal ?= $CODE$", text)
        self.assertIn("var:te_pa_p_$G$ > 0", text)

    def test_every_goal_is_scored_with_its_code(self):
        known = dict(items(self.effects["te_pa_score_goals"][1]))["if"]
        calls = [dict(items(val)) for key, val in items(known) if key == "te_pa_score_one"]
        self.assertEqual({c["G"]: int(c["CODE"]) for c in calls}, GOAL_CODES)

    def test_the_held_goal_is_weighed_first_and_must_be_beaten(self):
        ops = [key for key, _ in items(self.effects["te_pa_choose_goal"][1])]
        held = [i for i, k in enumerate(ops) if k == "te_pa_choose_held"]
        others = [i for i, k in enumerate(ops) if k == "te_pa_choose_one"]
        self.assertEqual(len(held), 8)
        self.assertEqual(len(others), 8)
        self.assertLess(max(held), min(others))
        for name in ("te_pa_choose_held", "te_pa_choose_one"):
            calls = [dict(items(val)) for key, val in items(self.effects["te_pa_choose_goal"][1]) if key == name]
            self.assertEqual({c["G"]: int(c["CODE"]) for c in calls}, GOAL_CODES)
        text = (ROOT / GOALS).read_text(encoding="utf-8-sig")
        for name, test in (("te_pa_choose_one", "var:te_pa_s_$G$ > local_var:te_pa_best_s"),
                           ("te_pa_choose_held", "var:te_pa_s_$G$ > 0")):
            body = text[re.search(rf"^{name} = {{", text, re.M).start():]
            self.assertIn(test, body[:body.index("\n}\n")], name)

    def test_a_simulated_choice_keeps_the_goal_held_on_a_tie_and_drops_it_when_beaten(self):
        """The choice as written, run in Python on a few cases."""
        bonus = number(self.core_values, "te_pa_goal_held_bonus")

        def choose(pressures, weights, held):
            scores = {g: pressures[g] * weights[g] + (bonus if GOAL_CODES[g] == held and pressures[g] > 0 else 0)
                      for g in GOAL_CODES}
            best_s, best_g = 0, 0
            for g, code in GOAL_CODES.items():
                if code == held and scores[g] > 0:
                    best_s, best_g = scores[g], code
            for g, code in GOAL_CODES.items():
                if scores[g] > best_s:
                    best_s, best_g = scores[g], code
            return best_g

        flat = {g: 1.0 for g in GOAL_CODES}
        zero = {g: 0.0 for g in GOAL_CODES}
        self.assertEqual(choose({**zero, "inputs": 40, "market": 50}, flat, 1), 1)  # 40 + 15 beats 50
        self.assertEqual(choose({**zero, "inputs": 40, "market": 56}, flat, 1), 2)  # 56 beats 55
        self.assertEqual(choose({**zero, "inputs": 40, "market": 55}, flat, 1), 1)  # a tie keeps it
        self.assertEqual(choose({**zero, "market": 10}, flat, 3), 2)                # no pressure, no bonus
        self.assertEqual(choose(zero, flat, 4), 0)                                  # nothing presses: no goal


class RuleTest(unittest.TestCase):
    def test_the_rule_is_read_only_through_te_pa_on(self):
        files = set()
        for root in ("common", "events", "gui"):
            for path in (ROOT / root).rglob("*"):
                if path.suffix in (".txt", ".gui") and path.is_file():
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                    if re.search(r"has_game_rule\s*=\s*te_private_actors_", text):
                        files.add(str(path.relative_to(ROOT)))
        self.assertEqual(files, {RULE_TRIGGERS})
        trigger = list(items(parse(RULE_TRIGGERS)["te_pa_on"][1]))
        self.assertEqual(trigger, [("has_game_rule", "te_private_actors_enabled")])

    def test_the_rule_and_its_settings(self):
        rules = parse("common/game_rules/extra_game_rules.txt")["te_private_actors_rule"][1]
        body = dict(items(rules))
        self.assertEqual(body["default"], "te_private_actors_disabled")
        self.assertEqual({k for k in body if k != "default"}, {"te_private_actors_disabled", "te_private_actors_enabled"})

    def test_the_monthly_pulse_runs_the_teardown_alone_when_the_rule_is_off(self):
        monthly = list(items(parse(CORE)["te_pa_monthly"][1]))
        first = dict(items(monthly[0][1]))
        self.assertEqual(monthly[0][0], "if")
        self.assertEqual(list(items(first["limit"])), [("te_pa_on", "no")])
        inner = dict(items(first["if"]))
        self.assertEqual([k for k in inner if k != "limit"], ["te_pa_teardown"])


class RowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core = parse(CORE)
        sync = core["te_pa_row_sync"][1]
        cls.written = set()
        for key, value in walk(sync):
            if key in ("te_pa_copy_from", "te_pa_copy_scope"):
                cls.written.add(dict(items(value))["TO"])
            elif key == "set_variable":
                cls.written.add(dict(items(value))["name"])

    def test_every_row_variable_read_is_written_by_the_sync(self):
        roots = ["common", "events", "gui", "localization/english"]
        reads = {}
        for root in roots:
            for path in (ROOT / root).rglob("*"):
                if path.suffix not in (".txt", ".gui", ".yml") or not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8-sig", errors="replace")
                for m in re.finditer(r"(?:var:|Var\('|GetVariableValue\('|HasVariable\(')(te_pa_r_\w+)", text):
                    reads.setdefault(m.group(1), str(path.relative_to(ROOT)))
        self.assertTrue(reads, "the custom loc reads row variables")
        missing = {name: where for name, where in reads.items() if name not in self.written}
        self.assertEqual(missing, {}, "a row variable the tab reads that te_pa_row_sync never writes")

    def test_the_sync_copies_the_firm_and_the_figures_task_3_shows(self):
        for name in ("te_pa_r_firm", "te_pa_r_goal", "te_pa_r_reason", "te_pa_r_reason_val", "te_pa_r_reason_good",
                     "te_pa_r_reason_law", "te_pa_r_cond", "te_pa_r_funds", "te_pa_r_conn", "te_pa_r_stand",
                     "te_pa_r_posture", "te_pa_r_share", "te_pa_r_seat", "te_pa_r_stance_enacting",
                     "te_pa_r_cartel", "te_pa_r_reg", "te_pa_r_press", "te_pa_r_town", "te_pa_r_lab",
                     "te_pa_r_found"):
            self.assertIn(name, self.written)
        for goal in GOAL_CODES:
            for kind in ("p", "w", "s"):
                self.assertIn(f"te_pa_r_{kind}_{goal}", self.written)


class TeardownTest(unittest.TestCase):
    """te_pa_teardown removes every static modifier the system applies, country and state alike (none in Task 2;
    each later task's add_modifier is held to a removal here)."""

    def effects(self) -> dict:
        out = {}
        for path in te_pa_files("common/scripted_effects"):
            out.update(parse(str(path.relative_to(ROOT))))
        return out

    def test_every_applied_modifier_is_removed_by_the_teardown(self):
        added = set()
        for path in (*te_pa_files("common/scripted_effects", "common/on_actions", "common/scripted_guis"),
                     *te_pa_files("events")):
            for key, value in walk(parse(str(path.relative_to(ROOT)))):
                if key == "add_modifier":
                    name = dict(items(value)).get("name") if isinstance(value, (dict, list)) else value
                    if name:
                        added.add(name)
        effects = self.effects()
        removed, seen = set(), set()

        def visit(name):
            if name in seen or name not in effects:
                return
            seen.add(name)
            for key, value in walk(effects[name][1]):
                if key == "remove_modifier":
                    removed.add(value)
                elif key in effects:
                    visit(key)

        visit("te_pa_teardown")
        self.assertEqual(added - removed, set(), "a modifier the system applies that the teardown leaves")

    def test_the_teardown_leaves_the_records(self):
        removed = {v for k, v in walk(self.effects()["te_pa_teardown"][1]) if k == "remove_variable"}
        self.assertFalse(removed & {"te_pa_init", "te_pa_goal", "te_pa_funds", "te_pa_conn", "te_pa_stand",
                                    "te_pa_posture", "te_pa_turn_in"})
        self.assertIn("te_pa_q_in", removed)  # the marker the monthly pulse's latch reads


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.custom = parse(CUSTOM_LOC)
        cls.loc = {}
        for path in (ROOT / "localization" / "english").glob("*.yml"):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r"\s*([\w.]+):\d*\s", line)
                if m:
                    cls.loc[m.group(1)] = line

    def lines(self, key: str, var: str) -> dict[str, str]:
        out = {}
        for k, value in items(self.custom[key][1]):
            if k != "text":
                continue
            body = dict(items(value))
            trigger = dict(items(body["trigger"])) if "trigger" in body else {}
            out[trigger.get(f"var:{var}", "fallback")] = body["localization_key"]
        return out

    def test_every_verb_used_has_a_line(self):
        verbs = set()
        for path in (*te_pa_files("common/scripted_effects", "common/scripted_guis", "common/on_actions"),
                     *te_pa_files("events")):
            text = path.read_text(encoding="utf-8-sig")
            verbs.update(int(v) for v in re.findall(r"\bVERB = (\d+)", text))
        self.assertTrue(verbs)
        lines = self.lines("te_pa_ledger_line", "te_pa_l_verb")
        for verb in sorted(verbs):
            with self.subTest(verb=verb):
                self.assertLessEqual(verb, 159, "plan § Storage: codes run 1-159")
                self.assertIn(str(verb), lines)
                self.assertIn(lines[str(verb)], self.loc)
        self.assertIn(lines["fallback"], self.loc)

    def test_task_2s_codes_sit_in_its_block(self):
        for path in (ROOT / CORE, ROOT / GOALS, ROOT / LEDGER):
            for verb in re.findall(r"\bVERB = (\d+)", path.read_text(encoding="utf-8-sig")):
                self.assertTrue(1 <= int(verb) <= 19, verb)

    def test_every_reason_code_has_a_line(self):
        codes = set(re.findall(r"name = te_pa_reason value = (\d+)", (ROOT / GOALS).read_text(encoding="utf-8-sig")))
        codes.discard("0")
        self.assertGreater(len(codes), 15)
        lines = self.lines("te_pa_reason_text", "te_pa_r_reason")
        for code in sorted(codes):
            with self.subTest(code=code):
                self.assertIn(code, lines)
                self.assertIn(lines[code], self.loc)

    def test_names_have_lines(self):
        for key, var in (("te_pa_goal_name", "te_pa_r_goal"), ("te_pa_cond_name", "te_pa_r_cond"),
                         ("te_pa_posture_name", "te_pa_r_posture")):
            for loc in self.lines(key, var).values():
                self.assertIn(loc, self.loc)

    def test_eviction_at_20(self):
        text = (ROOT / LEDGER).read_text(encoding="utf-8-sig")
        self.assertIn("any_in_list = { variable = te_pa_ledger count >= 21 has_tag = te_pa_ledger }", text)
        self.assertIn("order_by = te_pa_ledger_age_order", text)
        values = (ROOT / "common/script_values/te_pa_ledger_values.txt").read_text(encoding="utf-8-sig")
        self.assertIn("subtract = te_pa_ledger_recency_order", values)  # oldest first at position 0


if __name__ == "__main__":
    unittest.main()
