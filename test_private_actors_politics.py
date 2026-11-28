"""Private Actors, politics at home (docs/systems/mod_systems/private_actors.md § Politics at Home; plan Task 5a).

What is pinned here:

- a patronage modifier for every interest group type the game has (vanilla's and the mod's, merged), each carrying
  its group's political strength at the cap, every one removed by the teardown, and applied from the quarter only;
- every Electoral Finance law has its campaign-money rule (one of te_pa_ef_*'s triggers names it, or it is the
  group's "none" law), and every speech law has its press rule;
- the sides' settlement runs once for an ended law: it is called only behind has_variable = te_pa_side_law, and its
  body reads whether the law passed and then removes te_pa_side_law before it pays any firm;
- campaign money is spent only through te_pa_spend_funds, from te_pa_campaign_spend, which every money verb calls;
- the verbs: A Friendly Law's list, campaign money in Cheaper Inputs', A Protected Market's and Dominance's, the press
  in the cartel firm's lists, the side spend and the press after the goal's verb, stall widened (the quarter's stays
  the cartel's);
- the presses' terms in the exposure hook, beside the inquiry's; the election's end hooked; ledger codes in 40-49;
  the two self-checks with their play-test rows.

Run: .venv/bin/python -m pytest test_private_actors_politics.py -q
"""

import re
import sys
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_private_actors as gen  # noqa: E402

POLITICS_EFFECTS = "common/scripted_effects/te_pa_politics_effects.txt"
POLITICS_TRIGGERS = "common/scripted_triggers/te_pa_politics_triggers.txt"
POLITICS_VALUES = "common/script_values/te_pa_politics_values.txt"
TRUST_EFFECTS = "common/scripted_effects/te_pa_trust_effects.txt"
ON_ACTIONS = "common/on_actions/te_pa_on_actions.txt"
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


def te_pa(folder: str, generated: bool = True) -> dict:
    out = {}
    for path in sorted((ROOT / folder).glob("te_pa_*.txt")):
        if generated or "_gen_" not in path.name:
            out.update(parse(path.relative_to(ROOT)))
    return out


def block(rel: str, name: str) -> str:
    body = text(rel)
    start = body.index(f"\n{name} = {{")
    end = body.index("\n}", start)
    return body[start:end]


def callers(callee: str) -> set:
    out = set()
    for folder in ("common/scripted_effects", "common/on_actions", "common/scripted_guis"):
        for path in sorted((ROOT / folder).glob("*.txt")):
            body = path.read_text(encoding="utf-8-sig", errors="replace")
            if callee not in body:
                continue
            for top, (_op, value) in parse(path.relative_to(ROOT)).items():
                if any(k == callee for k, _ in walk(value)):
                    out.add(top)
    return out


_PLAN = None


def plan():
    global _PLAN
    if _PLAN is None:
        _PLAN = gen.build_plan(gen.load_state())
    return _PLAN


class PatronageTest(unittest.TestCase):
    """§ 8.3: patronage is a country modifier per interest group, capped, from one refresh site, off with the rule."""

    @classmethod
    def setUpClass(cls):
        cls.modifiers = parse(gen.STATIC_MODIFIERS_OUT)
        cls.state = gen.load_state()

    def test_every_interest_group_type_has_its_modifier(self):
        groups = set(self.state.get_data("Interest Groups") or {})
        self.assertGreaterEqual(len(groups), 8)
        self.assertEqual(set(plan().igs), groups)
        for ig in sorted(groups):
            with self.subTest(ig=ig):
                name = f"{gen.PATRONAGE_PREFIX}{ig}"
                self.assertIn(name, self.modifiers)
                body = dict(items(self.modifiers[name][1]))
                self.assertEqual(body[f"interest_group_{ig}_pol_str_mult"],
                                 gen._fmt(gen.cfg.NUMBERS["patronage_cap"]))

    def test_the_cap_is_twenty_percent(self):
        self.assertEqual(gen.cfg.NUMBERS["patronage_cap"], 0.2)
        # the multiplier never passes 1 (te_pa_pat_quarter_one clamps it)
        self.assertIn("clamp_variable = { name = te_pa_pm_$IG$ max = 1 min = 0 }",
                      block(POLITICS_EFFECTS, "te_pa_pat_quarter_one"))

    def test_the_teardown_removes_every_patronage_modifier(self):
        effects = {**te_pa("common/scripted_effects")}
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
        self.assertIn("te_pa_politics_teardown", seen)
        self.assertIn("te_pa_gen_patronage_remove_all", seen)
        wanted = {name for name in self.modifiers if name.startswith(gen.PATRONAGE_PREFIX)}
        self.assertTrue(wanted)
        self.assertEqual(wanted - removed, set())

    def test_applied_from_the_quarter_only(self):
        self.assertEqual(callers("te_pa_gen_patronage_quarter"), {"te_pa_politics_quarter"})
        self.assertEqual(callers("te_pa_politics_quarter"), {"te_pa_quarter"})
        adds = {dict(items(v))["name"] for k, v in walk(parse(gen.EFFECTS_OUT)["te_pa_gen_patronage_quarter"][1])
                if k == "add_modifier"}
        self.assertEqual(adds, {f"{gen.PATRONAGE_PREFIX}{ig}" for ig in plan().igs})

    def test_the_nation_tab_lists_them(self):
        nation = (ROOT / "scripts/generators/gen_nation_tab.py").read_text(encoding="utf-8")
        self.assertIn('"te_pa_patronage_*"', nation)


class LawRulesTest(unittest.TestCase):
    """§ 8.3's and § 8.5's tables: every Electoral Finance law and every speech law has its rule."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = parse(POLITICS_TRIGGERS)
        cls.laws = plan().laws
        state = gen.load_state()
        cls.all_laws = state.get_data("Laws") or {}

    def group(self, name: str) -> list[str]:
        return sorted(k for k, v in self.all_laws.items() if gen._unwrap(gen._body(self.all_laws, k).get("group")) == name)

    def test_every_electoral_finance_law_has_a_campaign_money_rule(self):
        laws = self.group("lawgroup_electoral_finance")
        self.assertEqual(len(laws), 4)
        named = set()
        for trigger in ("te_pa_ef_none", "te_pa_ef_open", "te_pa_ef_limits", "te_pa_ef_public"):
            named |= {v.removeprefix("law_type:") for k, v in walk(self.triggers[trigger][1]) if k == "has_law"}
        # te_pa_ef_none is the law with no other rule (No Campaign Finance Laws): it names the other three, negated
        for law in laws:
            with self.subTest(law=law):
                self.assertTrue(law in named or law == "law_no_campaign_finance_laws", law)
        self.assertEqual(named, set(laws) - {"law_no_campaign_finance_laws"})
        # each rule is read where the money is split (te_pa_cm_open_value / _hidden_value) or the form chosen
        values = text(POLITICS_VALUES)
        for trigger in ("te_pa_ef_limits", "te_pa_ef_public"):
            self.assertIn(f"{trigger} = yes", values)
        self.assertIn("te_pa_ef_none = no", block(POLITICS_TRIGGERS, "te_pa_cm_momentum_form"))

    def test_every_speech_law_has_a_press_rule(self):
        laws = self.group("lawgroup_free_speech")
        self.assertEqual(set(laws), {"law_outlawed_dissent", "law_censorship", "law_right_of_assembly",
                                     "law_protected_speech"})
        rules = text(POLITICS_TRIGGERS) + text(POLITICS_EFFECTS)
        # Outlawed Dissent: none founded (te_pa_press_allowed), one that exists closes (te_pa_press_quarter)
        self.assertIn("has_law = law_type:law_outlawed_dissent", block(POLITICS_TRIGGERS, "te_pa_press_allowed"))
        self.assertIn("has_law = law_type:law_outlawed_dissent", block(POLITICS_EFFECTS, "te_pa_press_quarter"))
        # Censorship: Favored and Tolerated only; a Restrained firm's closed at no cost
        self.assertIn("has_law = law_type:law_censorship", block(POLITICS_TRIGGERS, "te_pa_press_allowed"))
        self.assertIn("has_law = law_type:law_censorship", block(POLITICS_TRIGGERS, "te_pa_press_close_free"))
        # Right of Assembly and Protected Speech: free, and closing takes a suit won (the court's bar)
        self.assertIn("te_pa_v_cartel_barred_until > te_history_month_index",
                      block(POLITICS_TRIGGERS, "te_pa_sa_can_close_press"))
        for law in ("law_right_of_assembly", "law_protected_speech"):
            # neither is named: the default, free, is theirs, and the suit is their way to close one
            self.assertNotIn(f"law_type:{law}", rules, law)


class SettlementTest(unittest.TestCase):
    """§ 8.2: the sides are settled once when the turn or the quarter finds their law no longer enacted."""

    def test_the_settlement_runs_once_per_ended_law(self):
        self.assertEqual(callers("te_pa_sides_settle"), {"te_pa_sides_check"})
        check = parse(POLITICS_EFFECTS)["te_pa_sides_check"][1]
        branches = [v for k, v in items(check) if k == "if"]
        guarded = [b for b in branches if ("te_pa_sides_settle", "yes") in list(items(b))]
        self.assertEqual(len(guarded), 1)
        limit = list(items(dict(items(guarded[0]))["limit"]))
        self.assertIn(("has_variable", "te_pa_side_law"), limit)
        self.assertIn(("te_pa_side_law_enacting", "no"), limit)
        body = block(POLITICS_EFFECTS, "te_pa_sides_settle")
        read = body.index("te_pa_gen_law_n_in_force = { VAR = te_pa_side_law }")
        removed = body.index("remove_variable = te_pa_side_law")
        paid = body.index("every_company")
        self.assertLess(read, removed)
        self.assertLess(removed, paid)
        # the sides are opened only while none are
        opener = [b for b in branches if b is not guarded[0]][0]
        self.assertIn(("NOT", {"has_variable": ("=", "te_pa_side_law")}), list(items(dict(items(opener))["limit"])))

    def test_the_check_runs_at_the_turn_and_the_quarter(self):
        self.assertEqual(callers("te_pa_sides_check"), {"te_pa_politics_turn", "te_pa_politics_quarter_start"})
        self.assertEqual(callers("te_pa_politics_turn"), {"te_pa_turn"})
        self.assertEqual(callers("te_pa_politics_quarter_start"), {"te_pa_quarter"})

    def test_winners_gain_and_losers_lose_five(self):
        values = parse(POLITICS_VALUES)
        self.assertEqual(values["te_pa_side_conn_win"][1], "5")
        self.assertEqual(values["te_pa_side_conn_lose"][1], "5")

    def test_the_election_is_settled_once_a_month_after_its_end(self):
        hooks = text(ON_ACTIONS)
        hook = hooks[hooks.index("on_election_campaign_end = {"):]
        self.assertIn("te_pa_election_end_on_action", hook[:hook.index("}")])
        self.assertIn("te_pa_on = yes", block(POLITICS_EFFECTS, "te_pa_election_end"))
        settle = block(POLITICS_EFFECTS, "te_pa_election_settle")
        self.assertLess(settle.index("remove_variable = te_pa_elect_end"), settle.index("every_company"))
        monthly = block(POLITICS_EFFECTS, "te_pa_politics_monthly")
        self.assertIn("te_history_month_index > var:te_pa_elect_end", monthly)


class MoneyTest(unittest.TestCase):
    """Money from nowhere or money twice (plan Review Focus 4): campaign money goes through te_pa_spend_funds."""

    def test_campaign_money_is_spent_only_through_te_pa_spend_funds(self):
        spend = block(POLITICS_EFFECTS, "te_pa_campaign_spend")
        self.assertIn("te_pa_spend_funds = { AMOUNT = te_pa_cm_spend_value }", spend)
        # the money's effects only once it is spent
        self.assertLess(spend.index("te_pa_spend_funds"), spend.index("var:te_pa_spent ?= 1"))
        self.assertLess(spend.index("var:te_pa_spent ?= 1"), spend.index("add_momentum"))
        self.assertEqual(callers("te_pa_campaign_spend"), {"te_pa_do_campaign", "te_pa_do_back_side"})
        # nothing else in the area touches the funds or the pool
        for rel in (POLITICS_EFFECTS,):
            body = text(rel)
            self.assertNotIn("name = te_pa_funds ", body)
            self.assertNotIn("add_investment_pool", body)
            self.assertNotIn("add_treasury", body)
        for m in re.finditer(r"te_pa_spend_funds = \{ AMOUNT = (\S+) \}", text(POLITICS_EFFECTS)):
            self.assertRegex(m.group(1), r"^te_pa_\w+_value$")

    def test_the_secret_part_is_what_the_law_forbids(self):
        values = text(POLITICS_VALUES)
        hidden = block(POLITICS_VALUES, "te_pa_cm_hidden_value")
        self.assertIn("te_pa_v_bold >= te_pa_cm_secret_bold", hidden)
        self.assertIn("te_pa_ef_limits = yes", hidden)
        self.assertIn("te_pa_ef_public = yes", hidden)
        self.assertIn("multiply = te_pa_cm_secret_public_mult", block(POLITICS_VALUES, "te_pa_cm_secret_units_value"))
        self.assertIn("te_pa_cm_limit_share = 0.01", values)


class VerbsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = te_pa("common/scripted_effects")

    def verbs(self, name: str) -> list[str]:
        return [k.removeprefix("te_pa_do_") for k, _ in walk(self.effects[name][1]) if k.startswith("te_pa_do_")]

    def test_a_friendly_law_list(self):
        self.assertEqual(self.verbs("te_pa_act_law"), ["stall", "speed", "campaign"])

    def test_campaign_money_and_the_press_in_the_lists(self):
        self.assertEqual(self.verbs("te_pa_act_inputs")[-1], "campaign")
        for name in ("te_pa_act_market", "te_pa_act_dominance"):
            with self.subTest(list=name):
                verbs = self.verbs(name)
                self.assertIn("found_press", verbs)
                self.assertEqual(verbs[-1], "campaign")
                self.assertLess(verbs.index("capture_reg"), verbs.index("found_press"))

    def test_the_side_and_the_press_follow_the_goals_verb(self):
        act = [k for k, _ in walk(self.effects["te_pa_act"][1])]
        self.assertLess(act.index("te_pa_act_law"), act.index("te_pa_do_back_side"))
        self.assertLess(act.index("te_pa_do_endow"), act.index("te_pa_do_back_side"))
        self.assertLess(act.index("te_pa_do_back_side"), act.index("te_pa_do_found_press"))
        turn = [k for k, _ in items(self.effects["te_pa_turn"][1])]
        self.assertLess(turn.index("te_pa_choose_goal"), turn.index("te_pa_politics_turn"))
        self.assertLess(turn.index("te_pa_politics_turn"), turn.index("te_pa_act"))

    def test_stall_is_widened_and_the_quarter_keeps_the_cartels(self):
        stall = block(POLITICS_TRIGGERS, "te_pa_can_stall")
        self.assertIn("te_pa_gen_stance_enacting < 0", stall)
        self.assertIn("te_pa_law_threatens_cartel = yes", stall)
        self.assertIn("te_pa_law_setback_open = yes", stall)
        self.assertIn("te_pa_can_stall_cartel = yes", block(TRUST_EFFECTS, "te_pa_trust_quarter"))
        self.assertNotIn("te_pa_can_stall = {", text("common/scripted_triggers/te_pa_trust_triggers.txt"))
        # one setback and one progress a year a law from all firms together
        self.assertIn("te_pa_stall_law_month", block(TRUST_EFFECTS, "te_pa_do_stall"))
        self.assertIn("te_pa_speed_law_month", block(POLITICS_EFFECTS, "te_pa_do_speed"))
        self.assertIn("te_pa_law_progress_open = yes", block(POLITICS_TRIGGERS, "te_pa_can_speed"))

    def test_speed_adds_a_tenth_of_the_checkpoint(self):
        self.assertIn("add_law_progress = te_pa_speed_progress", block(POLITICS_EFFECTS, "te_pa_do_speed"))
        self.assertEqual(parse(POLITICS_VALUES)["te_pa_speed_progress"][1], "0.1")


class PressTest(unittest.TestCase):
    def test_the_presses_terms_sit_in_the_hook_beside_the_inquiry(self):
        hook = block("common/script_values/te_pa_trust_values.txt", "te_pa_expose_hook_value")
        for term in ("te_pa_inquiry_term", "te_pa_press_own_term", "te_pa_press_rival_term"):
            self.assertIn(f"add = {term}", hook)
        # the rolled firm is saved for the rival term wherever a roll is made
        self.assertIn("save_scope_as = te_pa_expose_firm", block(TRUST_EFFECTS, "te_pa_expose_rolls"))
        self.assertIn("save_scope_as = te_pa_expose_firm",
                      block("common/scripted_effects/te_pa_actions_effects.txt", "te_pa_sa_audit"))

    def test_an_exposure_discredits_the_press_and_costs_it_half_the_standing(self):
        self.assertIn("te_pa_press_discredit = yes", block(TRUST_EFFECTS, "te_pa_exposure_costs"))
        self.assertIn("te_pa_press_discredit = yes", block(POLITICS_EFFECTS, "te_pa_expose_cm"))
        self.assertIn("multiply = te_pa_press_stand_factor",
                      block("common/script_values/te_pa_trust_values.txt", "te_pa_stand_after_exposure"))
        values = parse(POLITICS_VALUES)
        self.assertEqual(values["te_pa_press_discredit"][1], "30")
        self.assertEqual(values["te_pa_press_growth_year"][1], "8")

    def test_the_press_applies_no_modifier(self):
        for rel in (POLITICS_EFFECTS,):
            self.assertNotIn("add_modifier", text(rel).replace("te_pa_gen_patronage", ""))


class LedgerAndChecksTest(unittest.TestCase):
    def test_task_5as_codes_sit_in_its_block(self):
        verbs = {int(v) for v in re.findall(r"\bVERB = (\d+)", text(POLITICS_EFFECTS))}
        self.assertTrue(verbs)
        self.assertLessEqual(verbs, set(range(40, 50)))
        # the OPEN argument carries 43 and 44 to te_pa_cm_line's VERB
        self.assertIn("OPEN = 43", text(POLITICS_EFFECTS))
        self.assertIn("OPEN = 44", text(POLITICS_EFFECTS))
        custom = text("common/customizable_localization/te_pa_custom_loc.txt")
        for code in range(40, 50):
            self.assertIn(f"var:te_pa_l_verb ?= {code} }}", custom)

    def test_the_self_checks_have_their_rows(self):
        playtest = text(PLAYTEST)
        debug = text("common/scripted_effects/te_pa_debug_effects.txt")
        for name in ("law_progress", "momentum_from_pulse"):
            with self.subTest(check=name):
                self.assertIn(f"| `{name}`", playtest)
                self.assertIn(f"TE_SELF_CHECK OK {name}", debug)
                self.assertIn(f"TE_SELF_CHECK BROKEN {name}", debug)


if __name__ == "__main__":
    unittest.main()
